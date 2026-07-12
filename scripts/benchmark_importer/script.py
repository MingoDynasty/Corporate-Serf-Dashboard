import argparse
import json
import logging
import os
import re
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence

import requests
from pydantic import ValidationError

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(REPO_ROOT))
os.chdir(REPO_ROOT)

from source.kovaaks.api_models import BenchmarksAPIResponse  # noqa: E402
from source.kovaaks.api_service import (  # noqa: E402
    _get_with_retry,
    get_benchmark_json,
)
from source.kovaaks.data_models import PlaylistData, Rank, Scenario  # noqa: E402
from source.utilities.atomic_write import replace_with_retry  # noqa: E402

from scripts.benchmark_importer.models import (  # noqa: E402
    EvxlData,
    EvxlDatabaseItem,
    EvxlPlaylist,
    EvxlPlaylistByCodeResponse,
    Manifest,
    ManifestEntry,
)

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

EVXL_BENCHMARKS_JSON_FILE = REPO_ROOT / "resources" / "evxl" / "benchmarks.json"
GENERATED_DIR = SCRIPT_DIR / "generated"
MANIFEST_FILE = GENERATED_DIR / "manifest.json"
EVXL_BENCHMARKS_URL = "https://evxl.app/data/benchmarks"
EVXL_PLAYLIST_BY_CODE_URL = "https://api.evxl.app/kovaaks/playlist-by-code"
RETRY_ATTEMPTS = 4
RETRY_BACKOFF_SECONDS = (2, 4, 8)
POLITENESS_DELAY_SECONDS = 0.5

WINDOWS_RESERVED_BASENAMES = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{number}" for number in range(1, 10)),
    *(f"lpt{number}" for number in range(1, 10)),
}
WINDOWS_ILLEGAL_FILENAME_CHARACTERS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


class BenchmarkDataMismatchError(Exception):
    """Report incompatible Evxl and KovaaK's benchmark rank data."""


@dataclass(frozen=True)
class DuplicateClaimant:
    benchmark: str
    difficulty: str
    benchmark_id: int
    rank_ladder: tuple[tuple[str, str], ...]


@dataclass
class RunSummary:
    generated: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)
    conflicts: dict[str, list[DuplicateClaimant]] = field(default_factory=dict)

    @property
    def exit_code(self) -> int:
        return int(bool(self.failed or self.conflicts))


def _ordered_rank_colors(item: EvxlDatabaseItem) -> list[tuple[str, str]]:
    return list(item.rankColors.items())


def _atomic_write_json(path: Path, payload: Any) -> None:
    """Write JSON through a sibling temporary file and atomically replace the target."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(payload, temporary_file, indent=2)
            temporary_file.write("\n")
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        replace_with_retry(temporary_path, path, logger=logger)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def load_manifest(path: Path = MANIFEST_FILE) -> dict[str, ManifestEntry]:
    """Load local resume state, treating missing or malformed state as empty."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return Manifest.model_validate(payload).root
    except (OSError, UnicodeError, json.JSONDecodeError, ValidationError) as exc:
        logger.warning("Manifest is missing or malformed; starting empty: %s", exc)
        return {}


def write_manifest(
    manifest: dict[str, ManifestEntry],
    path: Path = MANIFEST_FILE,
) -> None:
    """Atomically persist local resume state."""
    payload = {
        sharecode: entry.model_dump(mode="json")
        for sharecode, entry in manifest.items()
    }
    _atomic_write_json(path, payload)


def _resolve_manifest_file(
    entry: ManifestEntry,
    generated_dir: Path,
) -> Path | None:
    """Resolve a manifest path only when it remains inside generated_dir."""
    generated_root = generated_dir.resolve()
    candidate = (generated_dir / entry.file).resolve()
    if not candidate.is_relative_to(generated_root) or candidate == generated_root:
        logger.warning(
            "Rejected manifest path outside generated directory: %s", entry.file
        )
        return None
    return candidate


def _expected_generated_from(
    sharecode: str,
    entry: ManifestEntry,
) -> dict[str, Any]:
    return {
        "sharecode": sharecode,
        "kovaaks_benchmark_id": entry.kovaaks_benchmark_id,
        "rank_colors": [list(pair) for pair in entry.rank_colors],
        "generated_at": entry.generated_at,
        "generator": "benchmark_importer",
    }


def _has_intact_generated_file(
    sharecode: str,
    entry: ManifestEntry,
    generated_dir: Path,
) -> bool:
    path = _resolve_manifest_file(entry, generated_dir)
    if path is None:
        return False
    try:
        raw_payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        logger.warning(
            "Generated file is missing or malformed for %s: %s", sharecode, exc
        )
        return False
    if not isinstance(raw_payload, dict):
        return False

    # Read provenance from raw JSON before PlaylistData validation, which drops it.
    if raw_payload.get("generated_from") != _expected_generated_from(sharecode, entry):
        logger.warning("Generated file provenance does not match manifest: %s", path)
        return False
    try:
        playlist = PlaylistData.model_validate(raw_payload)
    except ValidationError as exc:
        logger.warning("Generated playlist is invalid for %s: %s", sharecode, exc)
        return False
    return playlist.code == sharecode and playlist.name == entry.playlist_name


def should_skip_generation(
    sharecode: str,
    item: EvxlDatabaseItem,
    entry: ManifestEntry | None,
    generated_dir: Path,
    *,
    force: bool = False,
) -> bool:
    """Return whether manifest state and its output are current and intact."""
    if force or entry is None:
        return False
    return (
        entry.kovaaks_benchmark_id == item.kovaaksBenchmarkId
        and entry.rank_colors == _ordered_rank_colors(item)
        and _has_intact_generated_file(sharecode, entry, generated_dir)
    )


def _freeze_json(value: Any) -> Any:
    if isinstance(value, dict):
        return tuple((key, _freeze_json(item)) for key, item in sorted(value.items()))
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)
    return value


def _evxl_entry_signatures(data: EvxlData) -> dict[str, tuple]:
    """Represent complete Evxl entries without losing rank-color order."""
    signatures: dict[str, list[Any]] = {}
    for benchmark in data.root:
        benchmark_payload = benchmark.model_dump(
            mode="json",
            exclude={"difficulties"},
        )
        for difficulty in benchmark.difficulties:
            difficulty_payload = difficulty.model_dump(mode="json")
            difficulty_payload["rankColors"] = list(difficulty.rankColors.items())
            signatures.setdefault(difficulty.sharecode, []).append(
                _freeze_json(
                    {
                        "benchmark": benchmark_payload,
                        "difficulty": difficulty_payload,
                    }
                )
            )
    return {
        sharecode: tuple(sorted(claims, key=repr))
        for sharecode, claims in signatures.items()
    }


def refresh_evxl_snapshot(
    path: Path = EVXL_BENCHMARKS_JSON_FILE,
    *,
    accept_removals: bool = False,
) -> bool:
    """Refresh the Evxl snapshot when a complete, accepted candidate differs."""
    try:
        response = _get_with_retry(
            EVXL_BENCHMARKS_URL,
            attempts=RETRY_ATTEMPTS,
            backoff_seconds=RETRY_BACKOFF_SECONDS,
        )
        candidate_payload = response.json()
        candidate = EvxlData.model_validate(candidate_payload)
    except (requests.RequestException, ValidationError, ValueError, TypeError) as exc:
        logger.warning("Failed to refresh Evxl data; using snapshot: %s", exc)
        return False

    current_payload = json.loads(path.read_text(encoding="utf-8"))
    current = EvxlData.model_validate(current_payload)
    current_entries = _evxl_entry_signatures(current)
    candidate_entries = _evxl_entry_signatures(candidate)
    removed = sorted(current_entries.keys() - candidate_entries.keys())
    if removed and not accept_removals:
        logger.warning(
            "Rejected Evxl candidate because it removes %d sharecodes: %s",
            len(removed),
            removed,
        )
        return False

    added = candidate_entries.keys() - current_entries.keys()
    changed = {
        sharecode
        for sharecode in current_entries.keys() & candidate_entries.keys()
        if current_entries[sharecode] != candidate_entries[sharecode]
    }
    if not added and not changed and not removed:
        logger.info("Evxl data unchanged")
        return False

    _atomic_write_json(path, candidate_payload)
    logger.info(
        "Evxl data changed: %d entries added/%d changed/%d removed",
        len(added),
        len(changed),
        len(removed),
    )
    return True


def load_evxl_data(
    path: Path = EVXL_BENCHMARKS_JSON_FILE,
) -> tuple[dict[str, EvxlDatabaseItem], dict[str, list[DuplicateClaimant]]]:
    """Load Evxl entries and classify duplicate sharecodes before collapsing them."""
    evxl_data = EvxlData.model_validate_json(path.read_text(encoding="utf-8"))
    claims: dict[str, list[tuple[EvxlDatabaseItem, DuplicateClaimant]]] = {}

    for benchmark in evxl_data.root:
        for difficulty in benchmark.difficulties:
            database_item = EvxlDatabaseItem(
                kovaaksBenchmarkId=difficulty.kovaaksBenchmarkId,
                rankColors=difficulty.rankColors,
            )
            claimant = DuplicateClaimant(
                benchmark=benchmark.benchmarkName,
                difficulty=difficulty.difficultyName,
                benchmark_id=difficulty.kovaaksBenchmarkId,
                rank_ladder=tuple(difficulty.rankColors.items()),
            )
            claims.setdefault(difficulty.sharecode, []).append(
                (database_item, claimant)
            )

    database: dict[str, EvxlDatabaseItem] = {}
    conflicts: dict[str, list[DuplicateClaimant]] = {}
    for sharecode, sharecode_claims in claims.items():
        payloads = {
            (
                claim.kovaaksBenchmarkId,
                tuple(claim.rankColors.items()),
            )
            for claim, _ in sharecode_claims
        }
        if len(payloads) > 1:
            conflicts[sharecode] = [claimant for _, claimant in sharecode_claims]
            continue

        database[sharecode] = sharecode_claims[0][0]
        if len(sharecode_claims) > 1:
            logger.info(
                "Deduplicated %d identical entries for sharecode %s",
                len(sharecode_claims),
                sharecode,
            )

    return database, conflicts


def get_evxl_playlist(sharecode: str) -> EvxlPlaylist:
    """Resolve one playlist through Evxl's exact sharecode endpoint."""
    response = _get_with_retry(
        EVXL_PLAYLIST_BY_CODE_URL,
        params={"shareCode": sharecode},
        attempts=RETRY_ATTEMPTS,
        backoff_seconds=RETRY_BACKOFF_SECONDS,
    )
    return EvxlPlaylistByCodeResponse.model_validate(response.json()).playlist


def sanitize_playlist_name(playlist_name: str, sharecode: str) -> str:
    """Return a Windows-safe filename stem for one playlist."""
    sanitized = WINDOWS_ILLEGAL_FILENAME_CHARACTERS.sub("", playlist_name)
    sanitized = sanitized.rstrip(" .")
    if not sanitized:
        return sharecode

    basename, separator, extension = sanitized.partition(".")
    if basename.casefold() in WINDOWS_RESERVED_BASENAMES:
        return f"{basename}_{sharecode}{separator}{extension}"
    return sanitized


def scan_generated_ownership(
    generated_dir: Path = GENERATED_DIR,
) -> tuple[dict[str, str], set[str]]:
    """Build case-insensitive filename ownership from existing playlist files."""
    ownership: dict[str, str] = {}
    unowned: set[str] = set()
    if not generated_dir.exists():
        return ownership, unowned

    for path in generated_dir.glob("*.json"):
        key = path.name.casefold()
        if key == "manifest.json":
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            logger.warning(
                "Treating unreadable generated file as unowned: %s (%s)", path, exc
            )
            unowned.add(key)
            continue

        code = payload.get("code") if isinstance(payload, dict) else None
        if not isinstance(code, str) or not code:
            logger.warning("Treating code-less generated file as unowned: %s", path)
            unowned.add(key)
            continue
        ownership[key] = code

    return ownership, unowned


def choose_generated_path(
    playlist_name: str,
    sharecode: str,
    ownership: dict[str, str],
    unowned: set[str],
    generated_dir: Path = GENERATED_DIR,
) -> Path:
    """Choose a collision-safe output path and warn before replacing junk."""
    stem = sanitize_playlist_name(playlist_name, sharecode)
    candidate = generated_dir / f"{stem}.json"
    owner = ownership.get(candidate.name.casefold())

    if owner is not None and owner.casefold() != sharecode.casefold():
        logger.warning(
            "Filename collision for %s: %s is owned by %s; suffixing sharecode",
            sharecode,
            candidate.name,
            owner,
        )
        candidate = generated_dir / f"{stem}_{sharecode}.json"
        suffix = 2
        while (
            owner := ownership.get(candidate.name.casefold())
        ) is not None and owner.casefold() != sharecode.casefold():
            candidate = generated_dir / f"{stem}_{sharecode}_{suffix}.json"
            suffix += 1

    if candidate.name.casefold() in unowned:
        logger.warning(
            "Overwriting unowned generated file for %s: %s",
            sharecode,
            candidate,
        )
    return candidate


def build_scenarios(
    benchmark_response: BenchmarksAPIResponse,
    evxl_database_item: EvxlDatabaseItem,
) -> list[Scenario]:
    """Merge KovaaK's scenario thresholds with Evxl's ordered rank ladder."""
    evxl_rank_data = list(evxl_database_item.rankColors.items())
    scenario_list: list[Scenario] = []
    for category in benchmark_response.categories.values():
        for scenario_name, benchmark_scenario in category.scenarios.items():
            if len(benchmark_scenario.rank_maxes) != len(evxl_rank_data):
                message = (
                    f"Rank-count mismatch for {scenario_name!r}: "
                    f"Evxl has {len(evxl_rank_data)}, whereas KovaaK's "
                    f"Benchmark API has {len(benchmark_scenario.rank_maxes)}"
                )
                logger.error(message)
                raise BenchmarkDataMismatchError(message)

            ranks = [
                Rank(
                    name=rank_name,
                    color=rank_color,
                    threshold=benchmark_scenario.rank_maxes[index],
                )
                for index, (rank_name, rank_color) in enumerate(evxl_rank_data)
            ]
            # Strip the KovaaK's scenario key: CSV run import strips the
            # `Scenario:` value, so padded names would never match run/PB/rank
            # lookups (all exact-match) once the benchmark is unhidden.
            scenario_list.append(Scenario(name=scenario_name.strip(), ranks=ranks))
    return scenario_list


def generate_playlist(
    sharecode: str,
    evxl_database_item: EvxlDatabaseItem,
    ownership: dict[str, str],
    unowned: set[str],
    generated_dir: Path = GENERATED_DIR,
    *,
    use_cache: bool = True,
    manifest: dict[str, ManifestEntry] | None = None,
    manifest_path: Path | None = None,
) -> Path:
    """Fetch, merge, and write one benchmark playlist."""
    playlist = get_evxl_playlist(sharecode)
    logger.debug("Resolved %s as playlist: %s", sharecode, playlist.playlist_name)

    response_json = get_benchmark_json(
        evxl_database_item.kovaaksBenchmarkId,
        None,
        use_cache,
        attempts=RETRY_ATTEMPTS,
        backoff_seconds=RETRY_BACKOFF_SECONDS,
    )
    benchmark_response = BenchmarksAPIResponse.model_validate(response_json)
    playlist_data = PlaylistData(
        name=playlist.playlist_name.strip(),
        code=playlist.playlist_code.strip(),
        scenarios=build_scenarios(benchmark_response, evxl_database_item),
    )

    generated_dir.mkdir(parents=True, exist_ok=True)
    generated_path = choose_generated_path(
        playlist_data.name,
        sharecode,
        ownership,
        unowned,
        generated_dir,
    )
    generated_at = datetime.now(UTC).isoformat()
    rank_colors = _ordered_rank_colors(evxl_database_item)
    generated_from = {
        "sharecode": sharecode,
        "kovaaks_benchmark_id": evxl_database_item.kovaaksBenchmarkId,
        "rank_colors": [list(pair) for pair in rank_colors],
        "generated_at": generated_at,
        "generator": "benchmark_importer",
    }
    output_payload = playlist_data.model_dump(mode="json")
    output_payload["generated_from"] = generated_from
    _atomic_write_json(generated_path, output_payload)
    ownership[generated_path.name.casefold()] = playlist_data.code
    unowned.discard(generated_path.name.casefold())

    if manifest is not None:
        previous_entry = manifest.get(sharecode)
        if previous_entry is not None:
            previous_path = _resolve_manifest_file(previous_entry, generated_dir)
            if (
                previous_path is not None
                and previous_path != generated_path.resolve()
                and previous_path.exists()
            ):
                previous_path.unlink()
                ownership.pop(previous_path.name.casefold(), None)
                unowned.discard(previous_path.name.casefold())

        relative_path = generated_path.resolve().relative_to(generated_dir.resolve())
        manifest[sharecode] = ManifestEntry(
            file=relative_path.as_posix(),
            playlist_name=playlist_data.name,
            kovaaks_benchmark_id=evxl_database_item.kovaaksBenchmarkId,
            rank_colors=rank_colors,
            generated_at=generated_at,
        )
        write_manifest(
            manifest,
            manifest_path or generated_dir / "manifest.json",
        )
    return generated_path


def _selected_sharecodes(
    database: dict[str, EvxlDatabaseItem],
    conflicts: dict[str, list[DuplicateClaimant]],
    only: Sequence[str] | None,
) -> tuple[
    dict[str, EvxlDatabaseItem],
    dict[str, list[DuplicateClaimant]],
    list[str],
]:
    if not only:
        return database, conflicts, []

    requested = set(only)
    missing = sorted(requested - database.keys() - conflicts.keys())
    for sharecode in missing:
        logger.error("Requested sharecode was not found in Evxl data: %s", sharecode)
    return (
        {code: item for code, item in database.items() if code in requested},
        {code: claims for code, claims in conflicts.items() if code in requested},
        missing,
    )


def run_importer(
    database: dict[str, EvxlDatabaseItem],
    conflicts: dict[str, list[DuplicateClaimant]],
    *,
    only: Sequence[str] | None = None,
    limit: int | None = None,
    max_consecutive_failures: int = 3,
    generated_dir: Path = GENERATED_DIR,
    force: bool = False,
) -> RunSummary:
    """Generate selected playlists while containing expected per-item failures."""
    known_sharecodes = database.keys() | conflicts.keys()
    database, selected_conflicts, missing = _selected_sharecodes(
        database, conflicts, only
    )
    summary = RunSummary(
        failed={
            sharecode: "Requested sharecode was not found in Evxl data"
            for sharecode in missing
        },
        conflicts=selected_conflicts,
    )
    ownership, unowned = scan_generated_ownership(generated_dir)
    manifest_path = generated_dir / "manifest.json"
    manifest = load_manifest(manifest_path)
    for sharecode in sorted(manifest.keys() - known_sharecodes):
        logger.warning(
            "Manifest contains removed Evxl sharecode %s; leaving its file untouched",
            sharecode,
        )
    consecutive_failures = 0
    made_network_request = False

    for index, (sharecode, database_item) in enumerate(database.items(), start=1):
        if limit is not None and len(summary.generated) >= limit:
            break
        if should_skip_generation(
            sharecode,
            database_item,
            manifest.get(sharecode),
            generated_dir,
            force=force,
        ):
            logger.info("Skipping current generated playlist: %s", sharecode)
            summary.skipped.append(sharecode)
            continue
        if made_network_request:
            time.sleep(POLITENESS_DELAY_SECONDS)

        logger.info(
            "Generating (%d/%d) for sharecode: %s",
            index,
            len(database),
            sharecode,
        )
        made_network_request = True
        try:
            path = generate_playlist(
                sharecode,
                database_item,
                ownership,
                unowned,
                generated_dir,
                use_cache=not force,
                manifest=manifest,
                manifest_path=manifest_path,
            )
        except (
            requests.RequestException,
            ValidationError,
            BenchmarkDataMismatchError,
        ) as exc:
            logger.error("Failed to generate %s: %s", sharecode, exc)
            summary.failed[sharecode] = str(exc)
            consecutive_failures += 1
            if consecutive_failures >= max_consecutive_failures:
                logger.error(
                    "Aborting after %d consecutive failures",
                    consecutive_failures,
                )
                break
            continue

        logger.info("Generated %s at %s", sharecode, path)
        summary.generated.append(sharecode)
        consecutive_failures = 0

    return summary


def log_summary(summary: RunSummary) -> None:
    """Log end-of-run result buckets and conflict details."""
    logger.info(
        "Run summary: generated=%d, skipped=%d, failed=%d, conflicts=%d",
        len(summary.generated),
        len(summary.skipped),
        len(summary.failed),
        len(summary.conflicts),
    )
    logger.info("Generated sharecodes: %s", summary.generated or "none")
    logger.info("Skipped sharecodes: %s", summary.skipped or "none")
    logger.info("Failed sharecodes: %s", list(summary.failed) or "none")
    logger.info("Conflicting sharecodes: %s", list(summary.conflicts) or "none")
    for sharecode, claimants in summary.conflicts.items():
        logger.error("Conflicting Evxl entries for %s:", sharecode)
        for claimant in claimants:
            logger.error(
                "  benchmark=%r difficulty=%r benchmark_id=%d rank_ladder=%s",
                claimant.benchmark,
                claimant.difficulty,
                claimant.benchmark_id,
                list(claimant.rank_ladder),
            )


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate benchmark playlists.")
    parser.add_argument(
        "--only",
        action="append",
        metavar="SHARECODE",
        help="generate only this sharecode; may be repeated",
    )
    parser.add_argument(
        "--limit",
        type=_positive_int,
        help="stop after generating this many playlists",
    )
    parser.add_argument(
        "--max-consecutive-failures",
        type=_positive_int,
        default=3,
        help="abort after this many consecutive item failures (default: 3)",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="skip the live Evxl refresh and use the local snapshot",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="regenerate without manifest or KovaaK's benchmark cache reuse",
    )
    parser.add_argument(
        "--accept-removals",
        action="store_true",
        help="accept a live Evxl snapshot that removes sharecodes",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.offline:
        logger.info("Offline mode: using the local Evxl snapshot")
    else:
        refresh_evxl_snapshot(accept_removals=args.accept_removals)
    database, conflicts = load_evxl_data()
    logger.info(
        "Found %d unique Evxl benchmarks and %d conflicting sharecodes.",
        len(database),
        len(conflicts),
    )
    summary = run_importer(
        database,
        conflicts,
        only=args.only,
        limit=args.limit,
        max_consecutive_failures=args.max_consecutive_failures,
        force=args.force,
    )
    log_summary(summary)
    return summary.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
