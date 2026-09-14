import json
import logging
from datetime import datetime
from pathlib import Path

import pytest
from sortedcontainers import SortedList

from source.kovaaks import data_service
from source.kovaaks.data_models import RunData, ScenarioStats
from source.my_watchdog import file_watchdog

extract_data_from_file = data_service.extract_data_from_file

SCENARIO_NAME = "1w4ts"

SUB_CSV_HEADER = (
    "Weapon,Shots,Hits,Damage Done,Damage Possible,,Sens Scale,Horiz Sens,Vert Sens,"
    "FOV,Hide Gun,Crosshair,Crosshair Scale,Crosshair Color,ADS Sens,ADS Zoom Scale,"
    "Avg Target Scale,Avg Time Dilation"
)


DAMAGE_SUB_CSV_ROW = "Rifle,100,50,75,100,,Overwatch,2.3456,0,0,0,0,0,0,0,0,0,0"


def _write_stats_file(
    file_path: Path,
    sub_csv_row: str,
    *,
    sens_scale: str = "Overwatch",
    horizontal_sens: str = "2.3456",
    sens_increment: str | None = None,
    dpi: str | None = None,
    extra_line: str | None = None,
    scenario: str = SCENARIO_NAME,
) -> None:
    """Write a synthetic stats file in the key-value order KovaaK's uses.

    ``Sens Increment:`` comes before ``Horiz Sens:`` and ``DPI:`` after it, as real
    post-2024 files have them, so a conversion really has to wait for the
    whole key-value tail instead of running inline on the sensitivity line.
    Omitting both optional fields writes a legacy (2019-2021) file.
    ``extra_line`` appends one raw line verbatim, for the malformed shapes a
    mid-write file has.
    """
    lines = ["Score:,123.45", f"Sens Scale:,{sens_scale}"]
    if sens_increment is not None:
        lines.append(f"Sens Increment:,{sens_increment}")
    lines.append(f"Horiz Sens:,{horizontal_sens}")
    lines.append(f"Vert Sens:,{horizontal_sens}")
    if dpi is not None:
        lines.append(f"DPI:,{dpi}")
    if extra_line is not None:
        lines.append(extra_line)
    lines += [f"Scenario:,{scenario}", SUB_CSV_HEADER, sub_csv_row, ""]
    file_path.write_text("\n".join(lines), encoding="utf-8")


def _extract_written_file(name: str, **fields) -> RunData | None:
    """Write one synthetic stats file, parse it, and clean it up."""
    fixtures_dir = Path(__file__).resolve().parent / "fixtures" / "generated"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    file_path = fixtures_dir / f"{name} - Challenge - 2025.01.01-10.00.00 Stats.csv"
    try:
        _write_stats_file(file_path, DAMAGE_SUB_CSV_ROW, **fields)
        return extract_data_from_file(str(file_path))
    finally:
        file_path.unlink(missing_ok=True)


def test_load_csv_replaces_scenario_stats_object(monkeypatch) -> None:
    first_run = RunData(
        datetime_object=datetime(2026, 7, 1, 12, 0, 0),
        score=100,
        sens_scale="cm/360",
        horizontal_sens=40,
        scenario="1w4ts",
        accuracy=0.5,
    )
    second_run = RunData(
        datetime_object=datetime(2026, 7, 2, 12, 0, 0),
        score=150,
        sens_scale="cm/360",
        horizontal_sens=40,
        scenario="1w4ts",
        accuracy=0.6,
    )
    runs = iter([first_run, second_run])
    monkeypatch.setattr(data_service, "extract_data_from_file", lambda _f: next(runs))
    monkeypatch.setattr(data_service, "kovaaks_database", {})
    monkeypatch.setattr(
        data_service,
        "run_database",
        SortedList(key=lambda run: run.datetime_object),
    )

    assert data_service.load_csv_file_into_database("first.csv")
    stats_before = data_service.get_scenario_stats("1w4ts")

    assert data_service.load_csv_file_into_database("second.csv")
    stats_after = data_service.get_scenario_stats("1w4ts")

    # Concurrent readers bind the stats object once; updates must replace it
    # so a bound object never shows a torn mid-update field combination.
    assert stats_after is not stats_before
    assert stats_before.number_of_runs == 1
    assert stats_before.high_score == 100
    assert stats_after.number_of_runs == 2
    assert stats_after.high_score == 150
    assert stats_after.date_last_played == datetime(2026, 7, 2, 12, 0, 0)


def test_get_scenario_stats_snapshot_maps_every_scenario(monkeypatch) -> None:
    stats = ScenarioStats(
        date_last_played=datetime(2026, 7, 1, 12, 0, 0),
        number_of_runs=3,
        high_score=500,
    )
    monkeypatch.setattr(
        data_service,
        "kovaaks_database",
        {"1w4ts": {"scenario_stats": stats}},
    )

    snapshot = data_service.get_scenario_stats_snapshot()

    assert snapshot == {"1w4ts": stats}
    assert snapshot["1w4ts"] is stats


def test_extract_data_from_file_parses_valid_file() -> None:
    fixtures_dir = Path(__file__).resolve().parent / "fixtures" / "generated"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    file_path = fixtures_dir / "1w4ts - Challenge - 2025.01.01-10.00.00 Stats.csv"
    try:
        _write_stats_file(file_path, DAMAGE_SUB_CSV_ROW)

        run = extract_data_from_file(str(file_path))

        assert run is not None
        assert run.score == 123.45
        assert run.sens_scale == "Overwatch"
        assert run.horizontal_sens == 2.35
        assert run.scenario == "1w4ts"
        assert run.accuracy == 0.5
        assert run.damage_accuracy == 0.75
    finally:
        file_path.unlink(missing_ok=True)


def test_extract_data_from_file_tolerates_missing_damage_columns() -> None:
    fixtures_dir = Path(__file__).resolve().parent / "fixtures" / "generated"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    file_path = (
        fixtures_dir / "short-damage - Challenge - 2025.01.01-10.00.00 Stats.csv"
    )
    try:
        _write_stats_file(file_path, "Rifle,100,50")

        run = extract_data_from_file(str(file_path))

        assert run is not None
        assert run.accuracy == 0.5
        assert run.damage_accuracy is None
    finally:
        file_path.unlink(missing_ok=True)


def test_extract_data_from_file_returns_none_for_truncated_sub_csv_row() -> None:
    fixtures_dir = Path(__file__).resolve().parent / "fixtures" / "generated"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    file_path = fixtures_dir / "truncated - Challenge - 2025.01.01-10.00.00 Stats.csv"
    try:
        _write_stats_file(file_path, "Rifle,100")

        assert extract_data_from_file(str(file_path)) is None
    finally:
        file_path.unlink(missing_ok=True)


def test_extract_data_from_file_returns_none_for_unreadable_file() -> None:
    """An unopenable CSV — locked or deleted mid-scan — drops the run, not the app."""
    fixtures_dir = Path(__file__).resolve().parent / "fixtures" / "generated"
    file_path = fixtures_dir / "gone - Challenge - 2025.01.01-10.00.00 Stats.csv"
    assert not file_path.exists()

    assert extract_data_from_file(str(file_path)) is None


def test_extract_data_from_file_returns_none_for_mid_write_line() -> None:
    """A "Score:" line with no value column yet is what a mid-write file looks like."""
    fixtures_dir = Path(__file__).resolve().parent / "fixtures" / "generated"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    file_path = fixtures_dir / "midwrite - Challenge - 2025.01.01-10.00.00 Stats.csv"
    try:
        file_path.write_text("Score:\n", encoding="utf-8")

        assert extract_data_from_file(str(file_path)) is None
    finally:
        file_path.unlink(missing_ok=True)


def test_extract_data_from_file_returns_none_when_shots_is_zero() -> None:
    fixtures_dir = Path(__file__).resolve().parent / "fixtures" / "generated"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    file_path = fixtures_dir / "zero-shots - Challenge - 2025.01.01-10.00.00 Stats.csv"
    try:
        _write_stats_file(file_path, "Rifle,0,0,0,0")

        assert extract_data_from_file(str(file_path)) is None
    finally:
        file_path.unlink(missing_ok=True)


def test_load_csv_file_into_database_reports_success(monkeypatch) -> None:
    run = RunData(
        datetime_object=datetime(2026, 7, 6, 12),
        score=123.45,
        sens_scale="Overwatch",
        horizontal_sens=2.0,
        scenario="Test Scenario",
        accuracy=0.5,
    )
    monkeypatch.setattr(data_service, "extract_data_from_file", lambda _path: run)
    monkeypatch.setattr(data_service, "kovaaks_database", {})
    monkeypatch.setattr(
        data_service,
        "run_database",
        SortedList([], key=lambda item: item.datetime_object),
    )

    assert data_service.load_csv_file_into_database("run.csv") is True
    assert data_service.get_scenario_stats("Test Scenario").number_of_runs == 1


def test_load_csv_file_into_database_reports_extract_failure(
    monkeypatch,
    caplog,
) -> None:
    monkeypatch.setattr(data_service, "extract_data_from_file", lambda _path: None)

    assert data_service.load_csv_file_into_database("broken.csv") is False
    assert "Failed to get run data for CSV file: broken.csv" in caplog.messages


def test_initialize_kovaaks_data_logs_loaded_and_failed_counts(
    monkeypatch,
    tmp_path,
    caplog,
) -> None:
    # Real files through the real loader: stubbing load_csv_file_into_database
    # would stub out the very helper a future refactor could move the toast
    # into, leaving the queue assertion below unable to fail.
    _write_stats_file(
        tmp_path / "1w4ts - Challenge - 2025.01.01-10.00.00 Stats.csv",
        "Rifle,10,5,50,100",
    )
    # A "Score:" line with no value column -- what a mid-write file looks like,
    # the failure that motivated the watchdog-side toast.
    (tmp_path / "1w4ts - Challenge - 2025.01.01-11.00.00 Stats.csv").write_text(
        "Score:\n",
        encoding="utf-8",
    )
    (tmp_path / "ignored.txt").touch()
    monkeypatch.setattr(data_service, "kovaaks_database", {})
    monkeypatch.setattr(
        data_service,
        "run_database",
        SortedList([], key=lambda item: item.datetime_object),
    )
    file_watchdog.run_import_failure_queue.clear()

    with caplog.at_level(logging.DEBUG, logger=data_service.__name__):
        data_service.initialize_kovaaks_data(str(tmp_path))

    assert any(
        message.startswith(
            "CSV startup load complete: 2 scanned, 1 loaded, 1 failed in "
        )
        and message.endswith(" seconds.")
        for message in caplog.messages
    )
    # The good file really landed, so "1 loaded" counts a genuine store write.
    assert data_service.get_scenario_stats("1w4ts").number_of_runs == 1
    # Startup failures are batch information -- the counted log line above is
    # the whole report. Only the watchdog's live path toasts, so a rescan of a
    # directory full of unreadable CSVs must not queue a toast per file.
    assert file_watchdog.drain_run_import_failures() == []


# --- Scenario names ----------------------------------------------------------


@pytest.fixture
def empty_store(monkeypatch):
    monkeypatch.setattr(data_service, "kovaaks_database", {})
    monkeypatch.setattr(
        data_service,
        "run_database",
        SortedList([], key=lambda item: item.datetime_object),
    )


def _load_scenario_files(stats_dir: Path, *scenarios: str) -> None:
    """Write one stats file per scenario, named the way KovaaK's names them."""
    for scenario in scenarios:
        _write_stats_file(
            stats_dir / f"{scenario} - Challenge - 2025.01.01-10.00.00 Stats.csv",
            DAMAGE_SUB_CSV_ROW,
            scenario=scenario,
        )
    data_service.initialize_kovaaks_data(str(stats_dir))


def test_a_hyphenated_scenario_is_listed_in_full(empty_store, tmp_path) -> None:
    _load_scenario_files(tmp_path, "Anti-Centering Easy")

    names = data_service.get_scenario_names()

    assert names == ["Anti-Centering Easy"]
    assert "Anti" not in names


def test_scenarios_sharing_a_stem_stay_distinct(empty_store, tmp_path) -> None:
    _load_scenario_files(
        tmp_path,
        "Reflex Flick - Easy",
        "Reflex Flick - Fair",
        "Reflex Flick Wide - Easy",
    )

    assert data_service.get_scenario_names() == [
        "Reflex Flick - Easy",
        "Reflex Flick - Fair",
        "Reflex Flick Wide - Easy",
    ]


def test_every_listed_scenario_has_local_runs(empty_store, tmp_path) -> None:
    # The defect was a list entry the store could not resolve, which the page
    # reported as "No local runs found" for a scenario that had runs.
    _load_scenario_files(
        tmp_path,
        "Anti-Centering Easy",
        "Reflex Flick - Easy",
        "cA x-axis",
        "1w4ts",
    )

    names = data_service.get_scenario_names()

    assert len(names) == 4
    assert all(data_service.is_scenario_in_database(name) for name in names)


def test_a_scenario_with_no_parseable_run_is_not_listed(
    empty_store,
    tmp_path,
) -> None:
    broken_file = tmp_path / "Broken - Challenge - 2025.01.01-11.00.00 Stats.csv"
    broken_file.write_text("Score:\n", encoding="utf-8")
    _load_scenario_files(tmp_path, "1w4ts")

    assert data_service.get_scenario_names() == ["1w4ts"]


def test_an_empty_store_lists_no_scenarios(empty_store) -> None:
    assert data_service.get_scenario_names() == []


# --- Sensitivity normalization to cm/360 -------------------------------------


@pytest.fixture
def one_decimal_place(monkeypatch):
    """Round sensitivities to one place, the way the shipped config does.

    ``example.toml`` ships ``sens_round_decimal_places = 1``, so one place is what
    the axis labels and the PB cm/360 cells really show. The suite-wide config
    fixture uses two, which would hide that rounding here.
    """
    monkeypatch.setattr(data_service.get_config(), "sens_round_decimal_places", 1)


def test_a_cm360_file_keeps_the_value_it_recorded(one_decimal_place):
    # A run already on the cm/360 scale is the one case the conversion must not
    # touch, even though its file carries the same two fields.
    run = _extract_written_file(
        "native-cm360",
        sens_scale="cm/360",
        horizontal_sens="40",
        sens_increment="0.204107",
        dpi="1600",
    )

    assert run is not None
    assert run.horizontal_sens == 40.0
    assert run.sens_scale == "cm/360"


@pytest.mark.parametrize(
    ("name", "raw_sens", "increment", "dpi", "expected_cm360"),
    [
        # Every row is a real (sens, increment, DPI) triple from the stats
        # corpus, with the cm/360 KovaaK's itself shows for it.
        ("valorant-0.2-1600", "0.2", "0.199886", "1600", 40.8),
        # The same increment at the DPI 368 runs were misrecorded under: the
        # recorded DPI is trusted as-is, so this really is 163.4.
        ("valorant-0.2-400", "0.2", "0.199886", "400", 163.4),
        ("valorant-0.16-1600", "0.16", "0.159909", "1600", 51.1),
        ("valorant-0.25-1600", "0.25", "0.249857", "1600", 32.7),
        ("valorant-0.3-1600", "0.3", "0.299829", "1600", 27.2),
    ],
)
def test_a_game_scale_run_converts_to_cm360(  # noqa: PLR0913
    one_decimal_place,
    name,
    raw_sens,
    increment,
    dpi,
    expected_cm360,
):
    run = _extract_written_file(
        name,
        sens_scale="Valorant",
        horizontal_sens=raw_sens,
        sens_increment=increment,
        dpi=dpi,
    )

    assert run is not None
    assert run.horizontal_sens == expected_cm360
    assert run.sens_scale == "cm/360"


def test_converted_runs_leave_the_group_raw_rounding_collapsed_them_into(
    one_decimal_place,
):
    # Rounding the raw sensitivity to one decimal place put 0.16, 0.2, and 0.25
    # Valorant in one "0.2 Valorant" group. Converting first separates them,
    # because one decimal place is the right precision for centimeters.
    keys = set()
    for name, raw_sens, increment in [
        ("split-0.16", "0.16", "0.159909"),
        ("split-0.2", "0.2", "0.199886"),
        ("split-0.25", "0.25", "0.249857"),
    ]:
        run = _extract_written_file(
            name,
            sens_scale="Valorant",
            horizontal_sens=raw_sens,
            sens_increment=increment,
            dpi="1600",
        )
        assert run is not None
        keys.add(f"{run.horizontal_sens} {run.sens_scale}")

    assert keys == {"51.1 cm/360", "40.8 cm/360", "32.7 cm/360"}


def test_the_conversion_is_derived_from_the_increment_not_the_raw_sensitivity():
    # Rounded expectations cannot pin the mechanism: recomputing from the raw
    # sensitivity with the community yaw (0.07 rather than KovaaK's Valorant
    # 0.06996) gives 40.8214, which also rounds to 40.8. It is a relative
    # 5.7e-4 from the increment-derived value, so this tolerance fails it.
    assert data_service._cm360_from_increment(0.199886, 1600) == pytest.approx(
        40.8447, rel=1e-5
    )


def test_the_conversion_matches_kovaaks_own_valorant_formula():
    # ``resources/sensitivity converter/response.json`` is a capture of
    # kovaaks.com/webapp-backend/game-settings. Pinning the formula string
    # first makes the provenance of the constant part of the assertion.
    capture = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "resources"
            / "sensitivity converter"
            / "response.json"
        ).read_text(encoding="utf-8")
    )
    valorant = next(
        entry
        for entry in capture["SensitivityAndFov"]
        if entry["ScaleName"] == "Valorant"
    )

    assert valorant["Sens"]["IncrementFormula"] == "Sens * 0.06996"

    # The capture's own numbers for 0.2 Valorant at 1600 DPI, within the
    # precision the six-decimal ``Sens Increment`` field can record.
    assert data_service._cm360_from_increment(0.199886, 1600) == pytest.approx(
        2.54 * 360 / (0.2 * 0.06996 * 1600), rel=1e-5
    )


@pytest.mark.parametrize(
    ("name", "expected_cm360", "unrounded"),
    [
        # in/360 at sens 16 and counts/360 at sens 25600 both record increment
        # 360 / (16 * 1600) / 0.07, and both are 2.54 * 16 cm at 1600 DPI.
        ("in360", 40.6, 40.64),
        ("counts360", 40.6, 40.64),
    ],
)
def test_an_already_normalized_scale_converts_to_the_same_centimeters(
    one_decimal_place,
    name,
    expected_cm360,
    unrounded,
):
    # The corpus has no in/360 or counts/360 runs, so these are synthetic,
    # derived from the capture's own formulas for those two scales.
    run = _extract_written_file(
        name,
        sens_scale="in/360" if name == "in360" else "counts/360",
        horizontal_sens="16" if name == "in360" else "25600",
        sens_increment="0.200893",
        dpi="1600",
    )

    assert run is not None
    assert run.horizontal_sens == expected_cm360
    assert run.sens_scale == "cm/360"
    assert data_service._cm360_from_increment(0.200893, 1600) == pytest.approx(
        unrounded, rel=1e-5
    )


@pytest.mark.parametrize(
    ("name", "fields"),
    [
        ("no-dpi", {"sens_increment": "0.199886"}),
        ("no-increment", {"dpi": "1600"}),
        ("neither", {}),
        ("empty-dpi", {"sens_increment": "0.199886", "dpi": ""}),
        ("empty-increment", {"sens_increment": "", "dpi": "1600"}),
        ("zero-dpi", {"sens_increment": "0.199886", "dpi": "0"}),
        ("zero-increment", {"sens_increment": "0", "dpi": "1600"}),
        ("malformed-dpi", {"sens_increment": "0.199886", "dpi": "abc"}),
        ("malformed-increment", {"sens_increment": "abc", "dpi": "1600"}),
        # ``float()`` accepts these, so "parses as a number" is not the test.
        # An infinite increment would otherwise convert to 0.0 cm/360 and be
        # stored as if it were a real reading.
        ("infinite-dpi", {"sens_increment": "0.199886", "dpi": "inf"}),
        ("infinite-increment", {"sens_increment": "inf", "dpi": "1600"}),
        ("nan-dpi", {"sens_increment": "0.199886", "dpi": "nan"}),
        ("nan-increment", {"sens_increment": "nan", "dpi": "1600"}),
        # Finite and positive, but ``0.07 * increment * dpi`` underflows to zero
        # and the division raises outside the parser's exception handler.
        ("underflowing-increment", {"sens_increment": "5e-324", "dpi": "1600"}),
        ("underflowing-dpi", {"sens_increment": "0.199886", "dpi": "5e-324"}),
        # The same product overflowing the other way returns 0.0 centimeters.
        ("overflowing-increment", {"sens_increment": "1e308", "dpi": "1e308"}),
        # Finite, positive, and convertible, but 0.0130 cm rounds away at the
        # shipped one decimal place. Storing that would invent a 0.0 cm/360
        # group rather than keep the run's recorded sensitivity.
        ("rounds-to-zero", {"sens_increment": "1000", "dpi": "1000"}),
    ],
)
def test_an_unusable_conversion_field_costs_the_conversion_not_the_run(
    one_decimal_place,
    name,
    fields,
):
    # Neither field joins the required-field check: a run is worth more than
    # its normalization, and the 2019-2021 files carry neither.
    run = _extract_written_file(
        name,
        sens_scale="Valorant",
        horizontal_sens="0.2",
        **fields,
    )

    assert run is not None
    assert run.horizontal_sens == 0.2
    assert run.sens_scale == "Valorant"
    assert run.score == 123.45


def test_a_mid_write_dpi_line_costs_the_conversion_not_the_run(one_decimal_place):
    # "DPI:" with no value column yet is what a half-written file looks like.
    # The required fields' own IndexError drops the run there; an optional
    # field's must not.
    run = _extract_written_file(
        "midwrite-dpi",
        sens_scale="Valorant",
        horizontal_sens="0.2",
        sens_increment="0.199886",
        extra_line="DPI:",
    )

    assert run is not None
    assert run.horizontal_sens == 0.2
    assert run.sens_scale == "Valorant"


def test_an_unusable_conversion_field_cannot_abort_the_startup_scan(
    monkeypatch,
    tmp_path,
    one_decimal_place,
):
    """A run the formula cannot use costs that conversion, not the whole scan.

    ``initialize_kovaaks_data`` has no guard of its own around
    ``extract_data_from_file``, so an exception raised past the parser's own
    handler ends the scan and every run after the bad file is lost, not just
    the one that provoked it.
    """
    _write_stats_file(
        tmp_path / "underflow - Challenge - 2025.01.01-10.00.00 Stats.csv",
        DAMAGE_SUB_CSV_ROW,
        sens_scale="Valorant",
        horizontal_sens="0.2",
        sens_increment="5e-324",
        dpi="1600",
    )
    _write_stats_file(
        tmp_path / "good - Challenge - 2025.01.01-11.00.00 Stats.csv",
        DAMAGE_SUB_CSV_ROW,
        sens_scale="Valorant",
        horizontal_sens="0.2",
        sens_increment="0.199886",
        dpi="1600",
    )
    monkeypatch.setattr(data_service, "kovaaks_database", {})
    monkeypatch.setattr(
        data_service,
        "run_database",
        SortedList([], key=lambda item: item.datetime_object),
    )

    data_service.initialize_kovaaks_data(str(tmp_path))

    # Both runs land: the unusable one keeps its recorded sensitivity.
    assert data_service.get_scenario_stats(SCENARIO_NAME).number_of_runs == 2
    keys = set(data_service.get_sensitivities_vs_runs(SCENARIO_NAME))
    assert keys == {"0.2 Valorant", "40.8 cm/360"}


def test_the_guarded_conversion_reports_unusable_inputs_as_none():
    # The pure helper still divides; the guard is what turns an arithmetic
    # failure, or a result that cannot be stored, into "no conversion".
    assert data_service._converted_cm360(0.199886, 1600, 1) == 40.8
    assert data_service._converted_cm360(5e-324, 1600, 1) is None
    assert data_service._converted_cm360(1e308, 1e308, 1) is None
    # Rounds inside the guard, so a result that rounds away is rejected rather
    # than stored as a real 0.0 cm/360 reading.
    assert data_service._converted_cm360(1000, 1000, 1) is None
    # The same inputs are usable at a precision that can represent them.
    assert data_service._converted_cm360(1000, 1000, 3) == 0.013


@pytest.mark.parametrize("raw_value", ["inf", "-inf", "nan", "0", "-1", "abc", ""])
def test_an_optional_field_only_accepts_a_finite_positive_number(raw_value):
    assert data_service._parse_optional_positive(raw_value) is None
