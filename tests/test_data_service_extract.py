from pathlib import Path

from source.kovaaks.data_service import extract_data_from_file

SUB_CSV_HEADER = (
    "Weapon,Shots,Hits,Damage Done,Damage Possible,,Sens Scale,Horiz Sens,Vert Sens,"
    "FOV,Hide Gun,Crosshair,Crosshair Scale,Crosshair Color,ADS Sens,ADS Zoom Scale,"
    "Avg Target Scale,Avg Time Dilation"
)


def test_extract_data_from_file_parses_valid_file() -> None:
    fixtures_dir = Path(__file__).resolve().parent / "fixtures" / "generated"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    file_path = fixtures_dir / "1w4ts - Challenge - 2025.01.01-10.00.00 Stats.csv"
    try:
        file_path.write_text(
            "\n".join(
                [
                    "Score:,123.45",
                    "Sens Scale:,Overwatch",
                    "Horiz Sens:,2.3456",
                    "Scenario:,1w4ts",
                    SUB_CSV_HEADER,
                    "Rifle,100,50,0,0,,Overwatch,2.3456,0,0,0,0,0,0,0,0,0,0",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        run = extract_data_from_file(str(file_path))

        assert run is not None
        assert run.score == 123.45
        assert run.sens_scale == "Overwatch"
        assert run.horizontal_sens == 2.35
        assert run.scenario == "1w4ts"
        assert run.accuracy == 0.5
    finally:
        file_path.unlink(missing_ok=True)
