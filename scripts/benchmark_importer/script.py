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
    FailureEntry,
    FailureLedger,
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
BUNDLED_DIR = REPO_ROOT / "resources" / "benchmarks"
GENERATED_DIR = SCRIPT_DIR / "generated"
MANIFEST_FILE = GENERATED_DIR / "manifest.json"
FAILURES_FILE = GENERATED_DIR / "failures.json"
# Importer state that shares the output directory with playlists but is not one.
RESERVED_GENERATED_FILENAMES = frozenset({"manifest.json", "failures.json"})
EVXL_BENCHMARKS_URL = "https://evxl.app/data/benchmarks"
EVXL_PLAYLIST_BY_CODE_URL = "https://api.evxl.app/kovaaks/playlist-by-code"
# Bumped whenever the generated playlist schema changes, so a plain run
# regenerates pre-change outputs through the benchmark cache instead of needing
# --force (which would refetch every payload live). It is folded into each
# file's `generated_from` provenance, so `should_skip_generation` treats a file
# written under an older schema as stale. Bumped to 2 for embedded
# `leaderboard_id` fields.
GENERATOR_SCHEMA_VERSION = 2
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
    known_bad: dict[str, str] = field(default_factory=dict)
    conflicts: dict[str, list[DuplicateClaimant]] = field(default_factory=dict)

    @property
    def exit_code(self) -> int:
        # Known-bad skips are informational: the failure was already reported by
        # the run that recorded it.
        return int(bool(self.failed or self.conflicts))


@dataclass
class CheckSummary:
    identical: list[str] = field(default_factory=list)
    drifted: dict[str, list[str]] = field(default_factory=dict)
    failed: dict[str, str] = field(default_factory=dict)
    not_checked: list[str] = field(default_factory=list)
    # Bundled filename per key. A file with no usable sharecode is keyed by
    # its filename, and an unbundled --only code has no entry.
    filenames: dict[str, str] = field(default_factory=dict)

    @property
    def exit_code(self) -> int:
        # Zero only when every visited file was rebuilt and matched, so a run
        # the breaker cut short never reads as clean.
        return int(bool(self.drifted or self.failed or self.not_checked))


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


def _is_deterministic_failure(exc: BaseException) -> bool:
    """Report whether a failure stems from bad upstream data rather than a bad day.

    Deterministic failures recur on every attempt, so they are recorded and skipped
    instead of counting toward the transient-error circuit breaker.
    """
    if isinstance(exc, (BenchmarkDataMismatchError, ValidationError)):
        return True
    if isinstance(exc, requests.HTTPError):
        response = exc.response
        if response is None:
            return False
        # 429 is rate limiting: the same request succeeds once we back off.
        return 400 <= response.status_code < 500 and response.status_code != 429
    return False


def _ledger_entry_matches_evxl(entry: FailureEntry, item: EvxlDatabaseItem) -> bool:
    """Report whether a recorded failure still describes the current Evxl metadata.

    A deterministic failure is a statement about specific upstream data. Once that
    data changes the verdict is stale, so the item is attempted again instead of
    being skipped forever.
    """
    if entry.kovaaks_benchmark_id is None or entry.rank_colors is None:
        return False
    return (
        entry.kovaaks_benchmark_id == item.kovaaksBenchmarkId
        and entry.rank_colors == _ordered_rank_colors(item)
    )


def load_failure_ledger(path: Path = FAILURES_FILE) -> dict[str, FailureEntry]:
    """Load known-bad state, treating missing or malformed state as empty."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return FailureLedger.model_validate(payload).root
    except (OSError, UnicodeError, json.JSONDecodeError, ValidationError) as exc:
        logger.warning(
            "Failure ledger is missing or malformed; starting empty: %s", exc
        )
        return {}


def write_failure_ledger(
    ledger: dict[str, FailureEntry],
    path: Path = FAILURES_FILE,
) -> None:
    """Atomically persist known-bad state."""
    payload = {
        sharecode: entry.model_dump(mode="json") for sharecode, entry in ledger.items()
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
        "schema_version": GENERATOR_SCHEMA_VERSION,
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
        if key in RESERVED_GENERATED_FILENAMES:
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
    if f"{stem}.json".casefold() in RESERVED_GENERATED_FILENAMES:
        # Importer state is excluded from the ownership scan, so without this a
        # playlist named "manifest" or "failures" would overwrite it silently.
        logger.warning(
            "Playlist name for %s collides with importer state %s.json; "
            "suffixing sharecode",
            sharecode,
            stem,
        )
        stem = f"{stem}_{sharecode}"
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
            scenario_list.append(
                Scenario(
                    name=scenario_name.strip(),
                    ranks=ranks,
                    # Embed the leaderboard ID from the payload we already hold,
                    # so the shipped corpus can seed the name->ID mapping cache.
                    leaderboard_id=benchmark_scenario.leaderboard_id,
                )
            )

    # An upstream benchmark can go empty (no categories, or categories whose
    # scenario dicts are all empty) while still declaring a rank ladder. The
    # per-scenario guard above never runs in that case, so without this the
    # merge would "succeed" and write a playlist with no scenarios at all.
    if not scenario_list:
        message = (
            "No scenarios returned by KovaaK's Benchmark API for benchmark "
            f"{evxl_database_item.kovaaksBenchmarkId}"
        )
        logger.error(message)
        raise BenchmarkDataMismatchError(message)

    return scenario_list


def build_playlist(
    sharecode: str,
    evxl_database_item: EvxlDatabaseItem,
    *,
    use_cache: bool,
) -> PlaylistData:
    """Fetch and merge one benchmark playlist without writing it.

    Evxl is always queried live; ``use_cache`` governs only the KovaaK's
    benchmark cache, which every live fetch rewrites.
    """
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
    return PlaylistData(
        name=playlist.playlist_name.strip(),
        code=playlist.playlist_code.strip(),
        scenarios=build_scenarios(benchmark_response, evxl_database_item),
    )


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
    playlist_data = build_playlist(sharecode, evxl_database_item, use_cache=use_cache)

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
        "schema_version": GENERATOR_SCHEMA_VERSION,
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
    ledger_path = generated_dir / "failures.json"
    ledger = load_failure_ledger(ledger_path)
    # Naming a *recorded* sharecode is retry intent (see retry_intent below).
    # Naming a healthy one keeps --only's ordinary meaning of restricting the
    # sweep, so an intact current output is still skipped.
    explicitly_requested = set(only or ())
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
        ledger_entry = ledger.get(sharecode)
        # Naming a recorded sharecode is retry intent, so it overrides both the
        # manifest skip and the benchmark cache. Either one alone would replay
        # the state that produced the failure and re-record the same verdict.
        retry_intent = ledger_entry is not None and sharecode in explicitly_requested

        if not retry_intent and should_skip_generation(
            sharecode,
            database_item,
            manifest.get(sharecode),
            generated_dir,
            force=force,
        ):
            logger.info("Skipping current generated playlist: %s", sharecode)
            summary.skipped.append(sharecode)
            continue

        if (
            ledger_entry is not None
            and not force
            and not retry_intent
            and _ledger_entry_matches_evxl(ledger_entry, database_item)
        ):
            logger.info(
                "Skipping known-bad sharecode %s (recorded %s): %s",
                sharecode,
                ledger_entry.recorded_at,
                ledger_entry.error,
            )
            summary.known_bad[sharecode] = ledger_entry.error
            continue

        if retry_intent:
            logger.info(
                "Retrying known-bad sharecode %s: named explicitly, so the "
                "manifest skip and benchmark cache are bypassed",
                sharecode,
            )
        elif ledger_entry is not None and not _ledger_entry_matches_evxl(
            ledger_entry, database_item
        ):
            logger.info(
                "Evxl metadata changed since %s was recorded as known-bad; retrying",
                sharecode,
            )

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
                use_cache=not force and not retry_intent,
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
            if _is_deterministic_failure(exc):
                # Bad upstream data: retrying cannot help, and letting it feed the
                # breaker would abort sweeps that are otherwise healthy.
                logger.error(
                    "Recording %s as known-bad; later sweeps skip it unless it is "
                    "named with --only or the run uses --force",
                    sharecode,
                )
                ledger[sharecode] = FailureEntry(
                    error=str(exc),
                    recorded_at=datetime.now(UTC).isoformat(),
                    kovaaks_benchmark_id=database_item.kovaaksBenchmarkId,
                    rank_colors=_ordered_rank_colors(database_item),
                )
                write_failure_ledger(ledger, ledger_path)
                continue
            consecutive_failures += 1
            if consecutive_failures >= max_consecutive_failures:
                logger.error(
                    "Aborting after %d consecutive transient failures",
                    consecutive_failures,
                )
                break
            continue

        logger.info("Generated %s at %s", sharecode, path)
        summary.generated.append(sharecode)
        consecutive_failures = 0
        if ledger.pop(sharecode, None) is not None:
            logger.info("Clearing known-bad record for %s", sharecode)
            write_failure_ledger(ledger, ledger_path)

    return summary


def log_summary(summary: RunSummary) -> None:
    """Log end-of-run result buckets and conflict details."""
    logger.info(
        "Run summary: generated=%d, skipped=%d, failed=%d, known_bad=%d, conflicts=%d",
        len(summary.generated),
        len(summary.skipped),
        len(summary.failed),
        len(summary.known_bad),
        len(summary.conflicts),
    )
    logger.info("Generated sharecodes: %s", summary.generated or "none")
    logger.info("Skipped sharecodes: %s", summary.skipped or "none")
    logger.info("Failed sharecodes: %s", list(summary.failed) or "none")
    logger.info("Known-bad sharecodes: %s", list(summary.known_bad) or "none")
    for sharecode, reason in summary.known_bad.items():
        logger.info("  %s: %s", sharecode, reason)
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


def _quoted(names: Sequence[str]) -> str:
    # Scenario names can contain commas, so a bare comma join is ambiguous.
    return ", ".join(repr(name) for name in names)


def describe_drift(shipped: PlaylistData, rebuilt: PlaylistData) -> list[str]:
    """Explain how a rebuilt playlist differs from the shipped one.

    Explanation only, never the drift test: scenarios are matched by name, so
    a repeated name, or a field this does not compare, can leave two different
    models with nothing to say. Lines come in a fixed order and only for the
    differences present.
    """
    lines: list[str] = []
    if rebuilt.name != shipped.name:
        lines.append(f"name changed: {shipped.name!r} -> {rebuilt.name!r}")
    if rebuilt.code != shipped.code:
        lines.append(f"code changed: {shipped.code!r} -> {rebuilt.code!r}")

    shipped_scenarios = {scenario.name: scenario for scenario in shipped.scenarios}
    rebuilt_scenarios = {scenario.name: scenario for scenario in rebuilt.scenarios}
    added = [name for name in rebuilt_scenarios if name not in shipped_scenarios]
    removed = [name for name in shipped_scenarios if name not in rebuilt_scenarios]
    if added:
        lines.append(f"scenarios added: {_quoted(added)}")
    if removed:
        lines.append(f"scenarios removed: {_quoted(removed)}")
    kept = [name for name in shipped_scenarios if name in rebuilt_scenarios]
    if kept != [name for name in rebuilt_scenarios if name in shipped_scenarios]:
        lines.append("scenario order changed")

    changed: dict[str, list[str]] = {
        "thresholds": [],
        "leaderboard IDs": [],
        "rank ladder": [],
    }
    for name in kept:
        before = shipped_scenarios[name]
        after = rebuilt_scenarios[name]
        before_ranks = before.ranks or []
        after_ranks = after.ranks or []
        if [rank.threshold for rank in before_ranks] != [
            rank.threshold for rank in after_ranks
        ]:
            changed["thresholds"].append(name)
        if before.leaderboard_id != after.leaderboard_id:
            changed["leaderboard IDs"].append(name)
        if [(rank.name, rank.color) for rank in before_ranks] != [
            (rank.name, rank.color) for rank in after_ranks
        ]:
            changed["rank ladder"].append(name)
    for label, names in changed.items():
        if names:
            lines.append(
                f"{label} changed in {len(names)} of {len(kept)} scenarios: "
                f"{_quoted(names)}"
            )
    return lines


def _bundled_sharecode(payload: Any) -> str | None:
    generated_from = (
        payload.get("generated_from") if isinstance(payload, dict) else None
    )
    if not isinstance(generated_from, dict):
        return None
    sharecode = generated_from.get("sharecode")
    return sharecode if isinstance(sharecode, str) and sharecode else None


def run_check(
    database: dict[str, EvxlDatabaseItem],
    conflicts: dict[str, list[DuplicateClaimant]],
    *,
    only: Sequence[str] | None = None,
    max_consecutive_failures: int = 3,
    bundled_dir: Path = BUNDLED_DIR,
) -> CheckSummary:
    """Rebuild each bundled benchmark live and compare it with the shipped file.

    Files are keyed by their ``generated_from.sharecode``, never by ``code`` or
    filename, which can differ from it in casing. Nothing under ``generated/``
    is read or written; the only write is the KovaaK's benchmark cache that
    every live fetch refreshes. A file that cannot be rebuilt lands in
    ``failed`` whatever the cause, because a bundled file that no longer builds
    is stale either way.
    """
    summary = CheckSummary()
    requested = set(only or ())
    visits: list[tuple[str, Any, str | None]] = []
    for path in sorted(bundled_dir.glob("*.json"), key=lambda path: path.name):
        payload: Any = None
        problem: str | None = None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            problem = f"not readable as JSON: {exc}"
        sharecode = _bundled_sharecode(payload)
        if requested and sharecode not in requested:
            continue
        if problem is None and sharecode is None:
            problem = "no generated_from.sharecode"
        key = sharecode or path.name
        if key in summary.filenames:
            # Keying by sharecode would otherwise drop one of the two results.
            problem = f"sharecode {key} is also stamped on {summary.filenames[key]}"
            key = path.name
        summary.filenames[key] = path.name
        visits.append((key, payload, problem))

    for sharecode in sorted(requested - summary.filenames.keys()):
        logger.error("Requested sharecode is not bundled: %s", sharecode)
        summary.failed[sharecode] = "no bundled file carries this sharecode"

    consecutive_failures = 0
    made_network_request = False
    for index, (key, payload, problem) in enumerate(visits, start=1):
        if problem is None and key in conflicts:
            problem = "sharecode is a conflicting duplicate in the Evxl snapshot"
        elif problem is None and key not in database:
            problem = "sharecode is not in the Evxl snapshot"
        if problem is None:
            try:
                shipped = PlaylistData.model_validate(payload)
            except ValidationError as exc:
                problem = f"not a valid playlist: {exc}"
        if problem is not None:
            logger.error("Cannot check %s: %s", key, problem)
            summary.failed[key] = problem
            continue

        if made_network_request:
            time.sleep(POLITENESS_DELAY_SECONDS)
        logger.info("Checking (%d/%d) for sharecode: %s", index, len(visits), key)
        made_network_request = True
        try:
            # Bypass the benchmark cache: it can hold the very payload the
            # bundled file was built from, and a rebuild from that matches the
            # file by construction.
            rebuilt = build_playlist(key, database[key], use_cache=False)
        except (
            requests.RequestException,
            ValidationError,
            BenchmarkDataMismatchError,
        ) as exc:
            deterministic = _is_deterministic_failure(exc)
            kind = "deterministic" if deterministic else "transient"
            logger.error("Failed to rebuild %s (%s): %s", key, kind, exc)
            summary.failed[key] = f"{kind} failure: {exc}"
            if deterministic:
                continue
            consecutive_failures += 1
            if consecutive_failures >= max_consecutive_failures:
                logger.error(
                    "Aborting after %d consecutive transient failures",
                    consecutive_failures,
                )
                summary.not_checked = [remaining for remaining, *_ in visits[index:]]
                break
            continue

        consecutive_failures = 0
        # Whole-model equality, not a field-by-field diff: a diff silently
        # passes any field added to the models later, and scenarios matched by
        # name collapse when a name repeats.
        if rebuilt == shipped:
            logger.info("Identical: %s", key)
            summary.identical.append(key)
        else:
            logger.warning("Drifted: %s", key)
            summary.drifted[key] = describe_drift(shipped, rebuilt) or [
                "differs in a field this description does not cover"
            ]

    return summary


def _check_label(summary: CheckSummary, key: str) -> str:
    filename = summary.filenames.get(key, key)
    return key if filename == key else f"{key} ({filename})"


def log_check_summary(summary: CheckSummary) -> None:
    """Log the check's result buckets and, when files drifted, a paste line."""
    logger.info(
        "Check summary: identical=%d, drifted=%d, failed=%d, not_checked=%d",
        len(summary.identical),
        len(summary.drifted),
        len(summary.failed),
        len(summary.not_checked),
    )
    for sharecode, lines in summary.drifted.items():
        logger.warning("Drifted: %s", _check_label(summary, sharecode))
        for line in lines:
            logger.warning("  %s", line)
    for key, reason in summary.failed.items():
        logger.error("Failed: %s: %s", _check_label(summary, key), reason)
    logger.info("Not checked: %s", summary.not_checked or "none")
    if summary.drifted:
        # Failures and unchecked files stay off this line: regenerating
        # cannot fix a file that does not build or was never compared.
        only_flags = " ".join(f"--only {sharecode}" for sharecode in summary.drifted)
        logger.info("Regenerate the drifted files with:")
        logger.info(
            "uv run python scripts/benchmark_importer/script.py --offline --force %s",
            only_flags,
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
        help=(
            "abort after this many consecutive transient item failures "
            "(default: 3); deterministic failures never count toward it"
        ),
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
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "rebuild every bundled benchmark from live KovaaK's data and report "
            "drift, writing nothing but the benchmark cache; compares against "
            "the committed Evxl snapshot, so it implies --offline"
        ),
    )
    args = parser.parse_args(argv)
    if args.check and args.force:
        parser.error("--check cannot be combined with --force: the check never writes")
    if args.check and args.limit is not None:
        parser.error(
            "--check cannot be combined with --limit: a partial check would read "
            "as clean"
        )
    if args.check and args.accept_removals:
        parser.error(
            "--check cannot be combined with --accept-removals: the check never "
            "refreshes the Evxl snapshot"
        )
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.check:
        logger.info("Check mode: using the committed Evxl snapshot")
    elif args.offline:
        logger.info("Offline mode: using the local Evxl snapshot")
    else:
        refresh_evxl_snapshot(accept_removals=args.accept_removals)
    database, conflicts = load_evxl_data()
    logger.info(
        "Found %d unique Evxl benchmarks and %d conflicting sharecodes.",
        len(database),
        len(conflicts),
    )
    if args.check:
        check_summary = run_check(
            database,
            conflicts,
            only=args.only,
            max_consecutive_failures=args.max_consecutive_failures,
        )
        log_check_summary(check_summary)
        return check_summary.exit_code
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
