"""
Provides business logic for managing Kovaaks data.
"""

import logging
import os
import re
import threading
import time
from collections import Counter, deque
from datetime import date, datetime
from pathlib import Path

import numpy as np
from pydantic import ValidationError
from sortedcontainers import SortedDict, SortedList

from source.config.config_service import get_config
from source.kovaaks.api_service import (
    CACHE_REPLACE_RETRY_DELAYS_SECONDS,
    get_playlist_data,
)
from source.kovaaks.data_models import (
    PlaylistData,
    Rank,
    RunData,
    Scenario,
    ScenarioStats,
)
from source.utilities.stopwatch import Stopwatch

# The bundled root is the full benchmark library (every committed file
# carries rank data — CI-enforced); which of them the user sees is the
# show/hide preference in playlist_visibility_service, not file state.
BUNDLED_PLAYLIST_DIRECTORY = "resources/benchmarks"
USER_PLAYLIST_DIRECTORY = "data/playlists"
BUNDLED_PLAYLIST_DIRECTORY_PATH = Path(BUNDLED_PLAYLIST_DIRECTORY).resolve()
USER_PLAYLIST_DIRECTORY_PATH = Path(USER_PLAYLIST_DIRECTORY).resolve()
POSSIBLE_SUB_CSV_HEADERS = [
    # Latest CSV header
    "Weapon,Shots,Hits,Damage Done,Damage Possible,,Sens Scale,Horiz Sens,Vert Sens,FOV,Hide Gun,Crosshair,Crosshair Scale,Crosshair Color,ADS Sens,ADS Zoom Scale,Avg Target Scale,Avg Time Dilation",  # noqa: E501
    # Old CSV header
    "Weapon,Shots,Hits,Damage Done,Damage Possible,,Sens Scale,Horiz Sens,"
    "Vert Sens,FOV,Hide Gun,Crosshair,Crosshair Scale,Crosshair Color,"
    "ADS Sens,ADS Zoom Scale",
]
logger = logging.getLogger(__name__)

# Deliberately unsynchronized: after startup the watchdog thread is the only
# writer, and raced reads self-heal on re-render (the home page's polling
# tick, or the next interaction on pages without a data-driving interval).
# See the 2026-07-09 "Unsynchronized In-Memory Stores" entry in
# docs/decision_log.md for the revisit triggers and why file-backed (WAL) is
# the chosen shape for an eventual SQLite migration.
kovaaks_database: dict = {}

run_database: SortedList = SortedList(
    [],
    key=lambda item: item.datetime_object,
)


playlist_database: dict[str, PlaylistData] = {}
# Codes whose winning file came from data/playlists/ (or arrived via import).
# Feeds the visibility first-run seed: user-root playlists must never be
# hidden by the preference file's introduction.
_user_root_playlist_codes: set[str] = set()
# The actual file backing each winning user-root code, so delete unlinks the
# real file instead of reconstructing a name that only matches import-written
# files (a hand-dropped file with an arbitrary name would be missed).
_user_root_playlist_files: dict[str, Path] = {}
# User-root files skipped at load because a bundled benchmark already served
# their code (the pre-#90 copy-to-activate leftovers). Each entry is the dead
# file plus the code it duplicated; the overview offers to clean them up.
_superseded_user_playlist_files: list[tuple[Path, str]] = []
playlist_startup_warning_queue: deque[str] = deque()
_PLAYLIST_IO_LOCK = threading.RLock()


def _sanitize_playlist_file_component(value: str, label: str) -> str:
    sanitized_value = re.sub(r"[^A-Za-z0-9 ._()-]+", "_", value).strip()
    sanitized_value = sanitized_value.rstrip(". ")
    if not sanitized_value:
        msg = f"Invalid playlist {label}: {value!r}"
        raise ValueError(msg)
    return sanitized_value


def get_playlist_file_path(playlist_name: str, playlist_code: str) -> Path:
    """Build a safe file path for a playlist JSON file."""
    sanitized_name = _sanitize_playlist_file_component(playlist_name, "name")
    sanitized_code = _sanitize_playlist_file_component(playlist_code, "code")

    file_path = (
        USER_PLAYLIST_DIRECTORY_PATH / f"{sanitized_name} [{sanitized_code}].json"
    ).resolve()
    file_path.relative_to(USER_PLAYLIST_DIRECTORY_PATH)
    return file_path


def _playlist_file_sort_key(file_path: Path) -> tuple[str, str]:
    return (file_path.name.casefold(), file_path.name)


def _iter_playlist_files(root: Path, *, missing_ok: bool) -> list[Path]:
    if not root.exists():
        if missing_ok:
            return []
        _record_startup_playlist_warning(f"Playlist directory is missing: {root}")
        return []

    return sorted(
        [
            entry
            for entry in root.iterdir()
            if entry.is_file() and entry.suffix == ".json"
        ],
        key=_playlist_file_sort_key,
    )


def _record_startup_playlist_warning(message: str) -> None:
    logger.warning(message)
    playlist_startup_warning_queue.append(message)


def drain_startup_playlist_warnings() -> list[str]:
    """Drain startup playlist warnings for UI delivery after Dash mounts."""
    warnings = []
    while True:
        try:
            warnings.append(playlist_startup_warning_queue.popleft())
        except IndexError:
            return warnings


def _is_code_validation_error(exc: ValidationError) -> bool:
    return any(error.get("loc") == ("code",) for error in exc.errors())


def _playlist_display_labels(playlists: list[PlaylistData]) -> dict[str, str]:
    name_counts = Counter(playlist.name for playlist in playlists)
    return {
        playlist.code: (
            f"{playlist.name} ({playlist.code})"
            if name_counts[playlist.name] > 1
            else playlist.name
        )
        for playlist in playlists
    }


def get_playlist_display_label(playlist_code: str) -> str:
    """Return the same disambiguated label used by playlist selectors."""
    labels = _playlist_display_labels(list(playlist_database.values()))
    return labels.get(playlist_code, playlist_code)


def filter_known_playlist_codes(playlist_codes: list[str]) -> list[str]:
    """Drop stale persisted playlist values while preserving selection order."""
    return [code for code in playlist_codes if code in playlist_database]


def get_aim_training_checkpoints(checkpoint_threshold: int) -> dict[datetime, int]:
    """Map run timestamps to cumulative training-hour checkpoints."""
    checkpoints = {}
    threshold = checkpoint_threshold * 60
    counter = 0
    for idx, run_data in enumerate(run_database):
        if idx % threshold != 0:
            continue
        checkpoints[run_data.datetime_object] = checkpoint_threshold * counter
        counter += 1
    return checkpoints


def get_aim_training_journey_for_playlists(
    playlist_codes: list[str],
) -> dict[str, dict[datetime, float]]:
    """Build aim-training journeys for the selected playlists."""
    journey_data: dict[str, dict[datetime, float]] = {}
    for playlist_code in filter_known_playlist_codes(playlist_codes):
        journey_data[playlist_code] = get_aim_training_journey_for_playlist(
            playlist_code,
        )
    return journey_data


def get_aim_training_journey_for_playlist(playlist_code: str) -> dict[datetime, float]:
    """Track a playlist's average scenario progress over time."""
    scenarios = get_scenarios_from_playlist_code(playlist_code)

    # get the high scores for each scenario
    high_scores = dict.fromkeys(scenarios, 0)
    for run_data in run_database:
        if run_data.scenario not in scenarios:
            continue
        high_scores[run_data.scenario] = max(
            high_scores[run_data.scenario],
            run_data.score,
        )

    journey_data: dict[datetime, float] = {}
    current_scores = dict.fromkeys(scenarios, 0)
    for run_data in run_database:
        if run_data.scenario not in scenarios:
            continue
        if run_data.score <= current_scores[run_data.scenario]:
            continue
        current_scores[run_data.scenario] = max(
            current_scores[run_data.scenario],
            run_data.score,
        )

        # wait until we have at least one score per scenario
        if any(value == 0 for value in current_scores.values()):
            continue

        # Calculate the percentages of the current score vs max score. Each is treated as a data point.
        # TODO: instead of doing percentages, we should calculate the rank, which is more useful and accurate.
        percentages = []
        for scenario in scenarios:
            percentages.append(current_scores[scenario] / high_scores[scenario])
        journey_data[run_data.datetime_object] = float(np.average(percentages))
    return journey_data


def is_scenario_in_database(scenario_name: str) -> bool:
    """Check if a scenario is in the database."""
    return scenario_name in kovaaks_database


def get_scenario_stats(scenario_name: str) -> ScenarioStats:
    """Get scenario statistics for a scenario."""
    return kovaaks_database[scenario_name]["scenario_stats"]


def get_scenario_stats_snapshot() -> dict[str, ScenarioStats]:
    """Get one consistent scenario-to-stats mapping for callback-wide reads.

    The list() over the items view is a single C-level operation, so a
    concurrent watchdog insert cannot break the iteration; each bound
    ScenarioStats object is consistent because updates replace it.
    """
    return {
        scenario_name: scenario_data["scenario_stats"]
        for scenario_name, scenario_data in list(kovaaks_database.items())
    }


def get_sensitivities_vs_runs(scenario_name: str) -> dict[str, list[RunData]]:
    """Get sensitivities vs runs for a scenario."""
    return kovaaks_database[scenario_name]["sensitivities_vs_runs"]


def get_high_score(scenario_name: str) -> float:
    """Return the stored high score for a scenario."""
    return get_scenario_stats(scenario_name).high_score


def get_personal_best_run(scenario_name: str) -> RunData | None:
    """Return the highest-score local run for a scenario, if it has local runs."""
    if scenario_name not in kovaaks_database:
        return None

    runs = kovaaks_database[scenario_name]["time_vs_runs"]
    return max(runs, key=lambda item: item.score, default=None)


def get_sensitivities_vs_runs_filtered(
    scenario_name: str,
    top_n_scores: int,
    oldest_date: datetime,
) -> dict[str, list[RunData]]:
    """
    Get sensitivities vs runs for a scenario, filtered by top N scores, and oldest date.
    :param scenario_name: the name of the scenario to filter by.
    :param top_n_scores: the number of top scores to filter by.
    :param oldest_date: oldest date to filter by (inclusive).
    """
    # TODO: dictionary comprehension is technically Pythonic, but I'm too lazy to figure out the optimal syntax.
    #  Besides, this logic might get blown away if/when we migrate to SQLite.
    filtered_data: dict[str, list[RunData]] = {}
    for key, runs_data in kovaaks_database[scenario_name][
        "sensitivities_vs_runs"
    ].items():
        filtered_data[key] = []

        # RunData list is already sorted by score, so we can simply iterate backwards.
        for run_data in reversed(runs_data):
            if run_data.datetime_object < oldest_date:
                continue
            filtered_data[key].append(run_data)
            if len(filtered_data[key]) >= top_n_scores:
                break

        # avoid issues with empty arrays in the dictionary
        if not filtered_data[key]:
            del filtered_data[key]
    return filtered_data


def get_time_vs_runs(
    scenario_name: str,
    top_n_scores: int,
    oldest_date: datetime,
) -> dict[date, list[RunData]]:
    """Group a scenario's top runs by date within the selected time range."""
    # TODO: dictionary comprehension is technically Pythonic, but I'm too lazy to figure out the optimal syntax.
    #  Besides, this logic might get blown away if/when we migrate to SQLite.

    # 1. Build a dictionary with <Date, [RunData]>
    data: dict[date, list[RunData]] = {}
    for run_data in kovaaks_database[scenario_name]["time_vs_runs"]:
        if run_data.datetime_object < oldest_date:
            continue

        date_obj = run_data.datetime_object.date()
        if date_obj not in data:
            data[date_obj] = []
        data[date_obj].append(run_data)

    # 2. Filter the data down to the Top N Scores
    filtered_data = {}
    for date_obj, runs_data in data.items():
        sorted_list = sorted(runs_data, key=lambda item: item.score)
        filtered_data[date_obj] = sorted_list[-top_n_scores:]
    return filtered_data


def get_playlist_selector_options() -> list[dict[str, str]]:
    """Get playlist dropdown options with finished display labels and codes."""
    # One snapshot for both label counting and sorting: an import callback on
    # another server thread can insert into playlist_database mid-iteration.
    snapshot = list(playlist_database.values())
    display_labels = _playlist_display_labels(snapshot)
    playlists = sorted(
        snapshot,
        key=lambda playlist: (
            playlist.name.casefold(),
            playlist.name,
            playlist.code,
        ),
    )
    return [
        {
            "label": display_labels[playlist.code],
            "value": playlist.code,
        }
        for playlist in playlists
    ]


def get_playlist_by_code(playlist_code: str) -> PlaylistData | None:
    """Find a locally imported playlist by its KovaaK's playlist code."""
    return playlist_database.get(playlist_code)


def get_user_root_playlist_codes() -> set[str]:
    """Get the codes loaded from the user root or imported this session."""
    return set(_user_root_playlist_codes)


def get_superseded_user_playlist_files() -> list[tuple[Path, str]]:
    """Get the user-root files skipped because a bundled code already won.

    Each entry is ``(file path, duplicated code)``. Refreshed on every
    ``load_playlists()`` run; the overview surfaces these as cleanup targets.
    """
    return list(_superseded_user_playlist_files)


def get_scenarios_from_playlist_code(playlist_code: str) -> list[str]:
    """Get scenario names from a playlist selected by URL playlist code."""
    playlist = get_playlist_by_code(playlist_code)
    if playlist is None:
        return []
    return [item.name for item in playlist.scenarios]


def get_rank_data_from_playlist_code(
    playlist_code: str,
    scenario_name: str,
) -> list[Rank]:
    """Return configured rank thresholds for a playlist scenario."""
    playlist = get_playlist_by_code(playlist_code)
    if playlist is None:
        logger.warning(
            "Failed to get rank data for playlist code (%s), scenario (%s)",
            playlist_code,
            scenario_name,
        )
        return []
    scenarios = playlist.scenarios
    for scenario in scenarios:
        if scenario.name != scenario_name:
            continue
        return scenario.ranks or []
    logger.warning(
        "Failed to get rank data for playlist code (%s), scenario (%s)",
        playlist_code,
        scenario_name,
    )
    return []


def initialize_kovaaks_data(stats_dir: str) -> None:
    """
    Initialize the Kovaaks database.
    :param stats_dir: stats directory to read data from.
    :return: None.
    """
    stopwatch = Stopwatch()
    stopwatch.start()
    csv_files = []
    with os.scandir(stats_dir) as entries:
        for entry in entries:
            if entry.is_file() and entry.name.endswith(".csv"):
                csv_files.append(entry.path)

    for csv_file in csv_files:
        load_csv_file_into_database(csv_file)
    stopwatch.stop()
    logger.debug(
        "Loaded %d CSV files in %.2f seconds.",
        len(csv_files),
        round(stopwatch.elapsed(), 2),
    )


def load_csv_file_into_database(csv_file: str) -> bool:
    """
    Loads a CSV file into the database.
    :param csv_file: CSV to load.
    :return: True when the run was added, otherwise False.
    """
    run_data = extract_data_from_file(csv_file)
    if not run_data:
        logger.warning("Failed to get run data for CSV file: %s", csv_file)
        return False

    run_database.add(run_data)

    sensitivity_key = f"{run_data.horizontal_sens} {run_data.sens_scale}"
    if run_data.scenario not in kovaaks_database:
        kovaaks_database[run_data.scenario] = {
            "scenario_stats": ScenarioStats(
                date_last_played=run_data.datetime_object,
                number_of_runs=1,
                high_score=run_data.score,
            ),
            "time_vs_runs": SortedList(
                [run_data],
                key=lambda item: item.datetime_object,
            ),
            "sensitivities_vs_runs": SortedDict(
                lambda item: float(item.split(" ")[0]),
                {
                    sensitivity_key: SortedList(
                        [run_data],
                        key=lambda item: item.score,
                    ),
                },
            ),
        }
    else:
        # Replace (never mutate) the stats object: readers on other server
        # threads bind it once and then see one consistent snapshot of all
        # three fields, instead of a torn mid-update combination.
        scenario_stats = kovaaks_database[run_data.scenario]["scenario_stats"]
        kovaaks_database[run_data.scenario]["scenario_stats"] = ScenarioStats(
            date_last_played=max(
                scenario_stats.date_last_played,
                run_data.datetime_object,
            ),
            number_of_runs=scenario_stats.number_of_runs + 1,
            high_score=max(scenario_stats.high_score, run_data.score),
        )

        # Add to sensitivities_vs_runs
        sens_vs_runs = kovaaks_database[run_data.scenario]["sensitivities_vs_runs"]
        if sensitivity_key not in sens_vs_runs:
            sens_vs_runs[sensitivity_key] = SortedList(
                key=lambda item: item.score,
            )
        sens_vs_runs[sensitivity_key].add(run_data)

        # Add to time_vs_runs
        kovaaks_database[run_data.scenario]["time_vs_runs"].add(run_data)
    return True


# TODO: simply pull this from the database instead of rescanning files again.
def get_unique_scenarios(_dir: str) -> list:
    """
    Gets the list of unique scenarios from a directory.
    :param _dir: directory to search for scenarios.
    :return: list of unique scenarios
    """
    unique_scenarios = set()
    files = [
        file for file in os.listdir(_dir) if os.path.isfile(os.path.join(_dir, file))
    ]
    csv_files = [file for file in files if file.endswith(".csv")]
    for file in csv_files:
        scenario_name = file.split("-")[0].strip()
        unique_scenarios.add(scenario_name)
    return sorted(unique_scenarios)


def extract_data_from_file(full_file_path: str) -> RunData | None:  # noqa: PLR0912
    """
    Extracts data from a scenario CSV file.
    :param full_file_path: full file path of the file to extract data from.
    :return: RunData object
    """
    accuracy = None
    damage_accuracy = None
    horizontal_sens = None
    scenario = None
    score = None
    sens_scale = None

    try:
        splits = Path(full_file_path).stem.split(" Stats")[0].split(" - ")
        datetime_object = datetime.strptime(splits[-1], "%Y.%m.%d-%H.%M.%S")

        with open(full_file_path, encoding="utf-8") as file:
            lines_list = file.readlines()  # Read all lines into a list

        sub_csv_line = False
        for raw_line in lines_list:
            line = raw_line.strip()
            # If we encounter this specific line, then the next line is a specific CSV line
            if line in POSSIBLE_SUB_CSV_HEADERS:
                sub_csv_line = True
                continue
            if sub_csv_line:
                values = [item.strip() for item in line.split(",")]
                if len(values) >= 3:
                    shots = int(values[1])
                    hits = int(values[2])
                    if shots > 0:
                        accuracy = hits / shots

                # Damage columns are useful for PB metadata, but keep them
                # optional so older/shorter CSV rows still parse hit accuracy.
                if len(values) >= 5:
                    try:
                        damage_done = float(values[3])
                        damage_possible = float(values[4])
                    except ValueError:
                        pass
                    else:
                        if damage_possible > 0:
                            damage_accuracy = damage_done / damage_possible
                sub_csv_line = False
                continue

            if line.startswith("Score:"):
                score = float(line.split(",")[1].strip())
            elif line.startswith("Sens Scale:"):
                sens_scale = line.split(",")[1].strip()
            elif line.startswith("Horiz Sens:"):
                str_horizontal_sens = line.split(",")[1].strip()
                # sometimes the sens looks like 20.123456789, so round it to look cleaner
                horizontal_sens = round(
                    float(str_horizontal_sens),
                    get_config().sens_round_decimal_places,
                )
            elif line.startswith("Scenario:"):
                scenario = line.split(",", 1)[1].strip()
    except ValueError:
        logger.warning("Failed to parse file: %s", full_file_path, exc_info=True)
        return None

    if (
        datetime_object is None
        or accuracy is None
        or horizontal_sens is None
        or scenario is None
        or score is None
        or sens_scale is None
    ):
        logger.warning("Missing data from file: %s", full_file_path)
        return None

    return RunData(
        datetime_object=datetime_object,
        score=score,
        sens_scale=sens_scale,
        horizontal_sens=horizontal_sens,
        scenario=scenario,
        accuracy=accuracy,
        damage_accuracy=damage_accuracy,
    )


def load_playlists() -> None:
    """Load valid playlist JSON files into the in-memory database."""
    playlist_database.clear()
    playlist_startup_warning_queue.clear()
    _user_root_playlist_codes.clear()
    _user_root_playlist_files.clear()
    _superseded_user_playlist_files.clear()
    playlist_sources: dict[str, Path] = {}
    for root, missing_ok in (
        (BUNDLED_PLAYLIST_DIRECTORY_PATH, False),
        (USER_PLAYLIST_DIRECTORY_PATH, True),
    ):
        for playlist_file in _iter_playlist_files(root, missing_ok=missing_ok):
            try:
                with open(playlist_file, encoding="utf-8") as file:
                    json_data = file.read()
                playlist_data = PlaylistData.model_validate_json(json_data)
            except OSError:
                _record_startup_playlist_warning(
                    f"Failed to read playlist file: {playlist_file}"
                )
                continue
            except ValidationError as exc:
                if _is_code_validation_error(exc):
                    _record_startup_playlist_warning(
                        "Skipping playlist file "
                        f"{playlist_file}: missing or blank playlist code; "
                        "add a `code` field."
                    )
                else:
                    _record_startup_playlist_warning(
                        f"Invalid JSON format in playlist file: {playlist_file}"
                    )
                continue

            if playlist_data.code in playlist_database:
                winning_source = playlist_sources[playlist_data.code]
                _record_startup_playlist_warning(
                    "Skipping playlist file "
                    f"{playlist_file}: playlist code {playlist_data.code} "
                    f"already loaded from {winning_source}."
                )
                # A user-root file whose code is already served by a bundled
                # benchmark is a dead pre-#90 copy-to-activate leftover: record
                # it as a cleanup target. A user file shadowed by another user
                # file is a plain duplicate, not "superseded by bundled", so it
                # is left out of the alert.
                if (
                    root == USER_PLAYLIST_DIRECTORY_PATH
                    and winning_source.is_relative_to(BUNDLED_PLAYLIST_DIRECTORY_PATH)
                ):
                    _superseded_user_playlist_files.append(
                        (playlist_file, playlist_data.code)
                    )
                continue
            playlist_database[playlist_data.code] = playlist_data
            playlist_sources[playlist_data.code] = playlist_file
            if root == USER_PLAYLIST_DIRECTORY_PATH:
                _user_root_playlist_codes.add(playlist_data.code)
                _user_root_playlist_files[playlist_data.code] = playlist_file


def load_playlist_from_code(input_playlist_code: str) -> tuple[str | None, str | None]:
    """Import the single playlist matching a KovaaK's playlist code.

    Returns ``(error_message, canonical_playlist_code)``. The second element
    is the canonical ``playlistCode`` from KovaaK's — the imported code on a
    successful import, or the conflicting existing code on a duplicate-code
    refusal (so callers can, for example, ask whether that existing playlist
    is hidden). It is None only when there is no canonical code to report:
    the search returned nothing, was ambiguous, or the write failed. The
    canonical code is what the store, the user-root tracking, and the
    visibility show-list are keyed by; it can differ from the pasted input
    (case normalization, non-exact search matches), so it must never be
    derived from ``input_playlist_code``.
    """
    response = get_playlist_data(input_playlist_code)
    if not response or not response.data:
        message = (
            f"Failed to load playlist data for playlist code: {input_playlist_code}"
        )
        logger.warning(message)
        return message, None

    if len(response.data) > 1:
        message = f"Found more than one playlist from code: {input_playlist_code}"
        logger.warning(message)
        return message, None

    playlist_data = PlaylistData(
        name=response.data[0].playlistName,
        code=response.data[0].playlistCode,
        scenarios=[
            Scenario(name=item.scenarioName) for item in response.data[0].scenarioList
        ],
    )

    if playlist_data.code in playlist_database:
        existing_playlist = playlist_database[playlist_data.code]
        message = (
            "Playlist code already exists: "
            f"{playlist_data.code} is already imported as "
            f"{existing_playlist.name} ({existing_playlist.code})."
        )
        logger.warning(message)
        # Duplicate refusal carries the conflicting existing code so the page
        # layer can check its visibility without importing the visibility
        # service (which would create an import cycle through data_service).
        return message, playlist_data.code
    try:
        write_playlist_data_to_file(playlist_data)
    except ValueError:
        message = (
            "Invalid playlist data returned by API: "
            f"{playlist_data.name} ({playlist_data.code})"
        )
        logger.warning(message)
        return message, None
    except OSError:
        message = (
            f"Failed to save playlist data: {playlist_data.name} ({playlist_data.code})"
        )
        logger.warning(message)
        return message, None
    playlist_database[playlist_data.code] = playlist_data
    _user_root_playlist_codes.add(playlist_data.code)
    # Record the file just written so a later delete unlinks the real path
    # (write_playlist_data_to_file builds it from the same helper).
    _user_root_playlist_files[playlist_data.code] = get_playlist_file_path(
        playlist_data.name, playlist_data.code
    )
    return None, playlist_data.code


def delete_user_playlist(playlist_code: str) -> str | None:
    """Delete a user playlist's file and store entry.

    Only user-root playlists are deletable — bundled benchmarks cannot be
    removed (hiding is the equivalent), so a code absent from the user-root
    tracking is refused with a user-visible message in the import flow's style.
    Unlinks the recorded file (tolerating an already-missing file); any other
    ``OSError`` is reported without touching the store. On success the store
    entry and user-root tracking are dropped under ``_PLAYLIST_IO_LOCK``.
    Returns an error message, or ``None`` on success.
    """
    with _PLAYLIST_IO_LOCK:
        file_path = _user_root_playlist_files.get(playlist_code)
        if file_path is None:
            message = (
                f"Playlist code cannot be deleted: {playlist_code} is not a "
                "user playlist."
            )
            logger.warning(message)
            return message
        try:
            file_path.unlink()
        except FileNotFoundError:
            # Already gone on disk (manual delete or a prior partial run):
            # fall through and clean up the in-memory state anyway.
            logger.warning("Playlist file already missing on delete: %s", file_path)
        except OSError:
            message = f"Failed to delete playlist file: {file_path}"
            logger.warning(message, exc_info=True)
            return message
        playlist_database.pop(playlist_code, None)
        _user_root_playlist_codes.discard(playlist_code)
        _user_root_playlist_files.pop(playlist_code, None)
    return None


def delete_superseded_user_playlist_files() -> str | None:
    """Delete every recorded superseded user-root playlist file.

    These files were skipped at load because a bundled benchmark already
    served their code, so they hold no store entry — deletion only touches the
    filesystem and the recorded list. Already-missing files are tolerated and
    dropped; a file that fails to unlink for another reason is kept in the list
    and its error reported. Returns an error message when any file failed, or
    ``None`` when all recorded files are gone.
    """
    with _PLAYLIST_IO_LOCK:
        remaining: list[tuple[Path, str]] = []
        error_message: str | None = None
        for file_path, code in _superseded_user_playlist_files:
            try:
                file_path.unlink()
            except FileNotFoundError:
                logger.warning(
                    "Superseded playlist file already missing on delete: %s",
                    file_path,
                )
            except OSError:
                error_message = f"Failed to delete playlist file: {file_path}"
                logger.warning(error_message, exc_info=True)
                remaining.append((file_path, code))
        _superseded_user_playlist_files[:] = remaining
    return error_message


def write_playlist_data_to_file(playlist_data: PlaylistData) -> None:
    """Persist imported playlist metadata as formatted JSON."""
    file_path = get_playlist_file_path(playlist_data.name, playlist_data.code)
    json_string = playlist_data.model_dump_json(indent=2, exclude_none=True)
    with _PLAYLIST_IO_LOCK:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        temp_file = file_path.with_name(
            f".{file_path.name}.{os.getpid()}.{threading.get_ident()}.tmp"
        )
        try:
            with open(temp_file, "w", encoding="utf-8") as file:
                file.write(json_string)
                file.write("\n")
                file.flush()
                os.fsync(file.fileno())
            for retry_delay in (*CACHE_REPLACE_RETRY_DELAYS_SECONDS, None):
                try:
                    os.replace(temp_file, file_path)
                    break
                except PermissionError:
                    if retry_delay is None:
                        raise
                    logger.warning(
                        "Retrying playlist replace after PermissionError: %s",
                        file_path,
                    )
                    time.sleep(retry_delay)
        finally:
            if temp_file.exists():
                temp_file.unlink()
