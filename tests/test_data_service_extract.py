from datetime import datetime
from pathlib import Path

from sortedcontainers import SortedList

from source.kovaaks import data_service
from source.kovaaks.data_models import RunData

extract_data_from_file = data_service.extract_data_from_file

SUB_CSV_HEADER = (
    "Weapon,Shots,Hits,Damage Done,Damage Possible,,Sens Scale,Horiz Sens,Vert Sens,"
    "FOV,Hide Gun,Crosshair,Crosshair Scale,Crosshair Color,ADS Sens,ADS Zoom Scale,"
    "Avg Target Scale,Avg Time Dilation"
)


def _write_stats_file(file_path: Path, sub_csv_row: str) -> None:
    file_path.write_text(
        "\n".join(
            [
                "Score:,123.45",
                "Sens Scale:,Overwatch",
                "Horiz Sens:,2.3456",
                "Scenario:,1w4ts",
                SUB_CSV_HEADER,
                sub_csv_row,
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_extract_data_from_file_parses_valid_file() -> None:
    fixtures_dir = Path(__file__).resolve().parent / "fixtures" / "generated"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    file_path = fixtures_dir / "1w4ts - Challenge - 2025.01.01-10.00.00 Stats.csv"
    try:
        _write_stats_file(
            file_path,
            "Rifle,100,50,75,100,,Overwatch,2.3456,0,0,0,0,0,0,0,0,0,0",
        )

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
