"""Tests for the run viewer's reader and figures, on stats files built in each era's shape.

Every run is written as a stats file and loaded through the app's own parser,
so a run record always agrees with its file, as it does in the app.
"""

import logging
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timedelta
from pathlib import Path
from statistics import median

import pytest

from source.kovaaks.data_models import RunData, run_id
from source.kovaaks.data_service import extract_data_from_file
from source.kovaaks.run_viewer import (
    ByBotKind,
    RunView,
    Setting,
    SettingTypical,
    TimesUnknown,
    Typical,
    read_run_file,
    view_run,
)
from source.kovaaks.time_scored_service import PaceBasis

SCENARIO = "VT PGT Intermediate S5"
HASH = "80d20fae0c9af3e09c781cfc2175545f"
OTHER_HASH = "0123456789abcdef0123456789abcdef"

KILL_HEADER = (
    "Kill #,Timestamp,Bot,Weapon,TTK,Shots,Hits,Accuracy,Damage Done,"
    "Damage Possible,Efficiency,Cheated,OverShots"
)
# KovaaK's 1.0.8, 2019: no OverShots column, and a colon before the milliseconds.
OLD_KILL_HEADER = (
    "Kill #,Timestamp,Bot,Weapon,TTK,Shots,Hits,Accuracy,Damage Done,"
    "Damage Possible,Efficiency,Cheated"
)
WEAPON_HEADER = (
    "Weapon,Shots,Hits,Damage Done,Damage Possible,,Sens Scale,Horiz Sens,Vert Sens,"
    "FOV,Hide Gun,Crosshair,Crosshair Scale,Crosshair Color,ADS Sens,ADS Zoom Scale,"
    "Avg Target Scale,Avg Time Dilation"
)
OLD_WEAPON_HEADER = (
    "Weapon,Shots,Hits,Damage Done,Damage Possible,,Sens Scale,Horiz Sens,Vert Sens,"
    "FOV,Hide Gun,Crosshair,Crosshair Scale,Crosshair Color,ADS Sens,ADS Zoom Scale"
)

# A 2026 file's fields, in the order KovaaK's 3.9.6 writes them. ``None``
# stands for the blank line between the two blocks. ``{start}`` is filled in
# with the run's start.
FIELDS: tuple[tuple[str, str] | None, ...] = (
    ("Kills", "3"),
    ("Deaths", "0"),
    ("Fight Time", "59.778"),
    ("Time Remaining", "0.0"),
    ("Avg TTK", "19.998415"),
    ("Damage Done", "0.285499"),
    ("Total Overshots", "0"),
    ("Damage Taken", "0.0"),
    ("Hit Count", "2855"),
    ("Miss Count", "3012"),
    ("Midairs", "0"),
    ("Midaired", "0"),
    ("Directs", "0"),
    ("Directed", "0"),
    ("Reloads", "0"),
    ("Distance Traveled", "0.0"),
    ("MBS Points", "0.0"),
    ("Score", "1000.0"),
    ("Scenario", SCENARIO),
    ("Hash", HASH),
    ("Game Version", "3.9.6.2026-07-31-12-50-24-a7b77b8ec22f"),
    ("Challenge Start", "{start}"),
    ("Pause Count", "0"),
    ("Pause Duration", "0"),
    ("Avg Target Scale", "1.0"),
    ("Avg Time Dilation", "1.0"),
    None,
    ("Input Lag", "0"),
    ("Max FPS (config)", "999.0"),
    ("Sens Scale", "cm/360"),
    ("Sens Increment", "0.181429"),
    ("Horiz Sens", "45.0"),
    ("Vert Sens", "45.0"),
    ("DPI", "1600"),
    ("FOV", "103.0"),
    ("FOVScale", "Overwatch"),
    ("Hide Gun", "false"),
    ("Crosshair", "0snowi_nicedot.png"),
    ("Crosshair Scale", "1.6"),
    ("Crosshair Color", "000100FF"),
    ("Resolution", "3840x2160"),
    ("Avg FPS", "957.859253"),
    ("Resolution Scale", "100.0"),
)
FIELD_KEYS = [field[0] for field in FIELDS if field is not None]

# A 2019 file's fields: no start, no pause, no DPI, Resolution, Resolution
# Scale or FOVScale.
OLD_FIELDS: tuple[tuple[str, str] | None, ...] = (
    ("Kills", "3"),
    ("Deaths", "0"),
    ("Fight Time", "7.12"),
    ("Avg TTK", "0.049"),
    ("Damage Done", "145.0"),
    ("Damage Taken", "0.0"),
    ("Midairs", "0"),
    ("Midaired", "0"),
    ("Directs", "0"),
    ("Directed", "0"),
    ("Distance Traveled", "0.0"),
    ("Score", "122.953217"),
    ("Scenario", SCENARIO),
    ("Hash", "3e50391f3c3f484c10a4b8fb362ded17"),
    ("Game Version", "1.0.8.0"),
    None,
    ("Input Lag", "0"),
    ("Max FPS (config)", "300.0"),
    ("Sens Scale", "Overwatch"),
    ("Horiz Sens", "3.9"),
    ("Vert Sens", "3.9"),
    ("FOV", "103.0"),
    ("Hide Gun", "false"),
    ("Crosshair", "plus.png"),
    ("Crosshair Scale", "1.0"),
    ("Crosshair Color", "FFFFFF"),
)

DAY_ONE = datetime(2026, 8, 4, 22, 0, 0)
VIEWED_END = DAY_ONE + timedelta(days=2)

# (timestamp, bot, shots, hits)
Kill = tuple[str, str, int, int]


def _clock(moment: datetime) -> str:
    return moment.strftime("%H:%M:%S.%f")[:-3]


def _kill_rows(kills: Sequence[Kill], old: bool) -> list[str]:
    rows = []
    for number, (timestamp, bot, shots, hits) in enumerate(kills, start=1):
        cheated = "false" if old else "0,0"
        rows.append(
            f"{number},{timestamp},{bot},Rifle,0.5s,{shots},{hits},"
            f"{hits / shots:.6f},{hits},{shots},{hits / shots:.6f},{cheated}"
        )
    return rows


def _stats_text(
    *,
    start: datetime,
    kills: Sequence[Kill],
    fields: Mapping[str, str | None],
    weapon_rows: Sequence[str],
    old: bool,
    raw_lines: Sequence[str],
) -> str:
    lines = [OLD_KILL_HEADER if old else KILL_HEADER, *_kill_rows(kills, old), ""]
    lines += [OLD_WEAPON_HEADER if old else WEAPON_HEADER, *weapon_rows, ""]
    for field in OLD_FIELDS if old else FIELDS:
        if field is None:
            lines.append("")
            continue
        key, value = field
        value = fields.get(key, value)
        if value is not None:
            lines.append(f"{key}:,{value.format(start=_clock(start))}")
    for key, value in fields.items():
        if key not in FIELD_KEYS and value is not None:
            lines.append(f"{key}:,{value}")
    lines += raw_lines
    return "\r\n".join(lines) + "\r\n" if old else "\n".join(lines) + "\n"


def _write_run(  # noqa: PLR0913
    stats_dir: Path,
    end: datetime,
    *,
    score: float = 1000.0,
    shots: int = 100,
    hits: int = 50,
    kills: Sequence[Kill] = (),
    fields: Mapping[str, str | None] | None = None,
    weapon_rows: Sequence[str] | None = None,
    old: bool = False,
    raw_lines: Sequence[str] = (),
) -> RunData:
    """Write one run's stats file, and load it as the app does."""
    path = stats_dir / f"{SCENARIO} - Challenge - {end:%Y.%m.%d-%H.%M.%S} Stats.csv"
    path.write_text(
        _stats_text(
            start=end - timedelta(seconds=60),
            kills=kills,
            fields={"Score": str(score), **(fields or {})},
            weapon_rows=weapon_rows or [f"Rifle,{shots},{hits},0.5,1.0,"],
            old=old,
            raw_lines=raw_lines,
        ),
        encoding="utf-8",
        newline="",
    )
    run = extract_data_from_file(str(path))
    assert run is not None
    return run


def _typical_ends() -> list[datetime]:
    """Ten run ends across two sessions: enough for a known typical score."""
    return [DAY_ONE + timedelta(minutes=2 * index) for index in range(5)] + [
        DAY_ONE + timedelta(days=1, minutes=2 * index) for index in range(5)
    ]


def _view(
    stats_dir: Path,
    runs: Sequence[RunData],
    viewed: RunData,
    bases: Mapping[str, PaceBasis] | None = None,
    performance_files: Callable[[RunData], bool] = lambda _run: False,
) -> RunView:
    view = view_run(
        runs,
        run_id(viewed),
        stats_dir,
        lambda _scenario, version: (bases or {}).get(version or ""),
        performance_files,
    )
    assert view is not None
    return view


def _scenario(
    stats_dir: Path,
    typical: Callable[[int], dict] = lambda _index: {},
    **viewed,
) -> tuple[list[RunData], RunData]:
    """Write ten typical runs, each with ``typical(index)``'s fields, then the viewed run."""
    runs = [
        _write_run(stats_dir, end, **typical(index))
        for index, end in enumerate(_typical_ends())
    ]
    viewed_run = _write_run(stats_dir, VIEWED_END, **viewed)
    return [*runs, viewed_run], viewed_run


@pytest.fixture
def stats_dir(tmp_path) -> Path:
    folder = tmp_path / "stats"
    folder.mkdir()
    return folder


# --- The reader ------------------------------------------------------------------


def test_every_field_is_read_in_file_order_as_written(stats_dir) -> None:
    run = _write_run(stats_dir, VIEWED_END, fields={"Future Counter": "7"})

    file = read_run_file(stats_dir / run.stats_file_name)

    assert file is not None
    assert [key for key, _ in file.fields] == [*FIELD_KEYS, "Future Counter"]
    assert file.field("Score") == "1000.0"
    assert file.field("Challenge Start") == "21:59:00.000"
    assert file.field("Max FPS (config)") == "999.0"
    assert file.field("Future Counter") == "7"


def test_a_line_with_no_value_is_empty_and_a_missing_line_is_none(stats_dir) -> None:
    run = _write_run(stats_dir, VIEWED_END, fields={"Reloads": "", "DPI": None})

    file = read_run_file(stats_dir / run.stats_file_name)

    assert file is not None
    assert file.field("Reloads") == ""
    assert file.value("Reloads") is None
    assert file.field("DPI") is None
    assert file.value("DPI") is None


def test_weapon_rows_keep_the_columns_they_fill(stats_dir) -> None:
    run = _write_run(
        stats_dir,
        VIEWED_END,
        weapon_rows=["Rifle,100,50,0.5,1.0,", "Pistol,20,5,5.0,20.0,"],
    )

    file = read_run_file(stats_dir / run.stats_file_name)

    assert file is not None
    assert file.weapons.header == (
        "Weapon",
        "Shots",
        "Hits",
        "Damage Done",
        "Damage Possible",
    )
    assert file.weapons.rows == (
        ("Rifle", "100", "50", "0.5", "1.0"),
        ("Pistol", "20", "5", "5.0", "20.0"),
    )


def test_the_kill_table_keeps_every_column_as_written(stats_dir) -> None:
    run = _write_run(
        stats_dir,
        VIEWED_END,
        kills=[("21:59:19.000", "Bounce 1 Bot", 1900, 684)],
    )

    file = read_run_file(stats_dir / run.stats_file_name)

    assert file is not None
    assert file.kills.header == tuple(KILL_HEADER.split(","))
    assert file.kills.rows == (
        (
            "1",
            "21:59:19.000",
            "Bounce 1 Bot",
            "Rifle",
            "0.5s",
            "1900",
            "684",
            "0.360000",
            "684",
            "1900",
            "0.360000",
            "0",
            "0",
        ),
    )


def test_a_2019_file_reads_whole(stats_dir) -> None:
    run = _write_run(
        stats_dir,
        VIEWED_END,
        old=True,
        kills=[
            ("21:59:01:128", "target", 1, 1),
            ("21:59:02:853", "target", 2, 1),
        ],
    )

    file = read_run_file(stats_dir / run.stats_file_name)

    assert file is not None
    assert [key for key, _ in file.fields] == [
        field[0] for field in OLD_FIELDS if field is not None
    ]
    assert file.kills.header == tuple(OLD_KILL_HEADER.split(","))
    assert [row[1] for row in file.kills.rows] == ["21:59:01:128", "21:59:02:853"]
    assert file.weapons.header[-1] == "Damage Possible"


def test_a_value_after_the_first_comma_is_read_whole(stats_dir) -> None:
    run = _write_run(
        stats_dir,
        VIEWED_END,
        fields={"Scenario": "Controlsphere Far, Far Larger 90%"},
    )

    file = read_run_file(stats_dir / run.stats_file_name)

    assert file is not None
    assert file.field("Scenario") == "Controlsphere Far, Far Larger 90%"


def test_a_2021_file_reads_the_fields_written_with_no_colon(stats_dir) -> None:
    viewed = _write_run(
        stats_dir,
        VIEWED_END,
        old=True,
        raw_lines=[
            "Resolution,2560x1440",
            "Avg FPS,298.433838",
            "Resolution Scale,100.0",
        ],
    )

    view = _view(stats_dir, [viewed], viewed)
    cards = _cards(view)

    assert view.figures.file.field("Avg FPS") == "298.433838"
    assert cards[Setting.RESOLUTION][0] == "2560x1440"
    assert cards[Setting.RESOLUTION_SCALE][0] == "100%"
    assert cards[Setting.DPI][0] is None


def test_a_weapon_row_that_fills_the_settings_columns_keeps_them(stats_dir) -> None:
    # As KovaaK's 2.0.1 wrote some rows in July 2020.
    row = "ADSable Hitscan Cone,36338,15103,14208.0,33060.0,,,,,,false,plus.png,1.0,00FF00,0.7,0.5,"
    viewed = _write_run(
        stats_dir,
        VIEWED_END,
        old=True,
        weapon_rows=[row, "BB Gun,10,5,5.0,10.0,"],
    )

    file = read_run_file(stats_dir / viewed.stats_file_name)

    assert file is not None
    assert file.weapons.header == tuple(OLD_WEAPON_HEADER.split(","))
    assert file.weapons.rows == (
        tuple(row.split(",")[:16]),
        ("BB Gun", "10", "5", "5.0", "10.0", *[""] * 11),
    )


def test_a_run_with_no_kills_has_an_empty_kill_table_and_no_by_bot(stats_dir) -> None:
    runs, viewed = _scenario(stats_dir)

    view = _view(stats_dir, runs, viewed)

    assert view.figures is not None
    assert view.figures.file.kills.header == tuple(KILL_HEADER.split(","))
    assert view.figures.file.kills.rows == ()
    assert view.figures.by_bot.kind is None
    assert view.figures.by_bot.rows == ()


def test_a_file_that_cannot_be_read_is_reported_not_raised(stats_dir, caplog) -> None:
    runs, viewed = _scenario(stats_dir)
    (stats_dir / viewed.stats_file_name).unlink()

    with caplog.at_level(logging.WARNING):
        view = _view(stats_dir, runs, viewed)

    assert view.run == viewed
    assert view.figures is None
    assert "Failed to read run file" in caplog.text


def test_a_file_that_is_not_text_cannot_be_read(stats_dir, caplog) -> None:
    path = stats_dir / "not text Stats.csv"
    path.write_bytes(b"Kill #,\xff\xfe\n")

    with caplog.at_level(logging.WARNING):
        assert read_run_file(path) is None

    assert "not UTF-8" in caplog.text


def test_a_byte_order_mark_does_not_hide_the_kill_table(stats_dir) -> None:
    run = _write_run(stats_dir, VIEWED_END, kills=[("21:59:19.000", "Bot", 10, 5)])
    path = stats_dir / run.stats_file_name
    path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())

    file = read_run_file(path)

    assert file is not None
    assert len(file.kills.rows) == 1


def test_an_unknown_run_has_no_view(stats_dir) -> None:
    runs, _viewed = _scenario(stats_dir)

    assert view_run(runs, "nope", stats_dir, lambda *_: None, lambda _: False) is None


def test_the_view_names_the_runs_session_and_number(stats_dir) -> None:
    first = _write_run(stats_dir, VIEWED_END - timedelta(minutes=2))
    second = _write_run(stats_dir, VIEWED_END)

    view = _view(stats_dir, [first, second], second)

    assert view.session.runs == (first, second)
    assert view.number == 2


def test_the_performance_file_answer_is_passed_through(stats_dir) -> None:
    runs, viewed = _scenario(stats_dir)

    view = _view(stats_dir, runs, viewed, performance_files=lambda run: run == viewed)

    assert view.figures is not None
    assert view.figures.performance_file_found is True


# --- Typical runs ----------------------------------------------------------------


def test_the_typical_runs_are_the_runs_behind_the_typical_score(stats_dir) -> None:
    runs, viewed = _scenario(stats_dir)

    figures = _view(stats_dir, runs, viewed).figures

    assert figures is not None
    assert figures.typical_score is not None
    assert figures.typical_score.known
    assert figures.typical_runs == tuple(runs[:-1])


def test_a_first_session_has_no_typical_runs(stats_dir) -> None:
    viewed = _write_run(stats_dir, VIEWED_END)

    figures = _view(stats_dir, [viewed], viewed).figures

    assert figures is not None
    assert figures.typical_score is None
    assert figures.typical_runs == ()
    assert figures.tiles.score.typical is None
    assert not any(card.marked for card in figures.settings)


def test_too_few_runs_before_the_session_give_no_typical_runs(stats_dir) -> None:
    before = [_write_run(stats_dir, end) for end in _typical_ends()[:9]]
    viewed = _write_run(stats_dir, VIEWED_END, fields={"Crosshair Scale": "2.0"})

    figures = _view(stats_dir, [*before, viewed], viewed).figures

    assert figures is not None
    assert figures.typical_score is not None
    assert not figures.typical_score.known
    assert figures.typical_score.run_count == 9
    assert figures.typical_runs == ()
    assert figures.tiles.accuracy.typical is None
    assert not any(card.marked for card in figures.settings)


# --- Tiles -----------------------------------------------------------------------


def test_each_tile_is_the_median_over_the_typical_runs_that_have_it(stats_dir) -> None:
    def typical(index: int) -> dict:
        # Reloads 4 to 9 on the six newest; the four oldest have no line.
        reloads = None if index < 4 else str(index)
        return {
            "score": 100.0 * (index + 1),
            "shots": 100 + index,
            "hits": 41 + index,
            "fields": {"Reloads": reloads},
        }

    runs, viewed = _scenario(
        stats_dir, typical, score=480.0, shots=110, hits=55, fields={"Reloads": "3"}
    )

    tiles = _view(stats_dir, runs, viewed).figures.tiles

    assert tiles.score.run == 480.0
    assert tiles.score.typical == Typical(550.0, 10)
    assert tiles.accuracy.run == 0.5
    assert tiles.accuracy.typical == Typical(
        median((41 + index) / (100 + index) for index in range(10)), 10
    )
    assert tiles.shots_fired.run == 110
    assert tiles.shots_fired.typical == Typical(104.5, 10)
    assert tiles.reloads.run == 3
    assert tiles.reloads.typical == Typical(6.5, 6)


def test_a_missing_line_is_missing_never_zero(stats_dir) -> None:
    runs, viewed = _scenario(
        stats_dir, lambda _index: {"fields": {"Reloads": None}}, fields={"Reloads": ""}
    )

    tiles = _view(stats_dir, runs, viewed).figures.tiles

    assert tiles.reloads.run is None
    assert tiles.reloads.typical is None


def test_time_is_the_constant_less_the_score_on_the_runs_own_version(stats_dir) -> None:
    def typical(index: int) -> dict:
        # Scores 10 to 18, and one of 75: a time below zero, which isn't one.
        return {"score": 75.0 if index == 9 else 10.0 + index}

    runs, viewed = _scenario(stats_dir, typical, score=12.5)

    tiles = _view(stats_dir, runs, viewed, {HASH: PaceBasis(70.0, HASH)}).figures.tiles

    assert tiles.time is not None
    assert tiles.time.run == 57.5
    assert tiles.time.typical == Typical(median(60.0 - i for i in range(9)), 9)


def test_a_run_on_a_version_with_no_pace_basis_has_no_time(stats_dir) -> None:
    runs, viewed = _scenario(stats_dir, score=12.5, fields={"Hash": OTHER_HASH})

    figures = _view(stats_dir, runs, viewed, {HASH: PaceBasis(70.0, HASH)}).figures

    assert figures.pace_basis is None
    assert figures.tiles.time is None


def test_typical_runs_on_another_version_give_time_no_typical(stats_dir) -> None:
    runs, viewed = _scenario(
        stats_dir,
        lambda _index: {"score": 10.0, "fields": {"Hash": OTHER_HASH}},
        score=12.5,
    )

    tiles = _view(stats_dir, runs, viewed, {HASH: PaceBasis(70.0, HASH)}).figures.tiles

    assert tiles.time is not None
    assert tiles.time.run == 57.5
    assert tiles.time.typical is None


def test_a_time_of_zero_or_less_is_no_time(stats_dir) -> None:
    viewed = _write_run(stats_dir, VIEWED_END, score=70.0)

    tiles = _view(stats_dir, [viewed], viewed, {HASH: PaceBasis(70.0, HASH)})

    assert tiles.figures.tiles.time is not None
    assert tiles.figures.tiles.time.run is None


# --- Settings ----------------------------------------------------------------------


def _cards(view: RunView) -> dict[Setting, tuple[str | None, SettingTypical | None]]:
    assert view.figures is not None
    return {card.setting: (card.value, card.typical) for card in view.figures.settings}


def test_each_card_shows_its_value_as_the_app_words_it(stats_dir) -> None:
    viewed = _write_run(stats_dir, VIEWED_END, fields={"Input Lag": "2"})

    view = _view(stats_dir, [viewed], viewed)

    assert [card.setting for card in view.figures.settings] == list(Setting)
    assert {setting: value for setting, (value, _) in _cards(view).items()} == {
        Setting.SENSITIVITY: "45.0 cm/360",
        Setting.VERTICAL_SENSITIVITY: "Same as horizontal",
        Setting.DPI: "1600",
        Setting.FOV: "103 Overwatch",
        Setting.CROSSHAIR: "0snowi_nicedot",
        Setting.CROSSHAIR_SCALE: "1.6",
        Setting.HIDE_GUN: "No",
        Setting.RESOLUTION: "3840x2160",
        Setting.RESOLUTION_SCALE: "100%",
        Setting.FRAME_CAP: "999",
        Setting.INPUT_LAG: "2",
    }


def test_a_converted_sensitivity_carries_the_setting_it_was_played_at(
    stats_dir,
) -> None:
    viewed = _write_run(
        stats_dir,
        VIEWED_END,
        fields={
            "Sens Scale": "Valorant",
            "Sens Increment": "6.5",
            "Horiz Sens": "0.16",
            "Vert Sens": "0.2",
            "Hide Gun": "true",
            "Resolution Scale": "66.5",
            "Max FPS (config)": "240.5",
        },
    )

    cards = _cards(_view(stats_dir, [viewed], viewed))

    assert cards[Setting.SENSITIVITY][0] == (
        f"{viewed.horizontal_sens} cm/360 (0.16 Valorant at 1600 DPI)"
    )
    assert cards[Setting.VERTICAL_SENSITIVITY][0] == "0.2 Valorant"
    assert cards[Setting.HIDE_GUN][0] == "Yes"
    assert cards[Setting.RESOLUTION_SCALE][0] == "66.5%"
    assert cards[Setting.FRAME_CAP][0] == "240.5"


def test_a_2019_file_has_no_dpi_resolution_or_resolution_scale(stats_dir) -> None:
    viewed = _write_run(stats_dir, VIEWED_END, old=True)

    cards = _cards(_view(stats_dir, [viewed], viewed))

    assert cards[Setting.DPI][0] is None
    assert cards[Setting.RESOLUTION][0] is None
    assert cards[Setting.RESOLUTION_SCALE][0] is None
    assert cards[Setting.FOV][0] == "103"
    assert cards[Setting.SENSITIVITY][0] == "3.9 Overwatch"
    assert cards[Setting.VERTICAL_SENSITIVITY][0] == "Same as horizontal"
    assert cards[Setting.CROSSHAIR][0] == "plus"


def test_a_settings_typical_is_its_most_common_value(stats_dir) -> None:
    runs, viewed = _scenario(
        stats_dir,
        lambda index: {"fields": {"Crosshair": "dot.png" if index < 7 else "x.png"}},
        fields={"Crosshair": "x.png"},
    )

    view = _view(stats_dir, runs, viewed)
    card = next(c for c in view.figures.settings if c.setting is Setting.CROSSHAIR)

    assert card.value == "x"
    assert card.typical == SettingTypical("dot", 7)
    assert card.marked


def test_a_tie_goes_to_the_value_the_latest_typical_run_used(stats_dir) -> None:
    def typical(index: int) -> dict:
        # Crosshair Scale: 1.6 on the five oldest, 1.5 on the five newest.
        # DPI: 1600 on two, 400 on the next two, then no line at all.
        dpi = ("1600", "1600", "400", "400")[index] if index < 4 else None
        scale = "1.6" if index < 5 else "1.5"
        return {"fields": {"Crosshair Scale": scale, "DPI": dpi}}

    runs, viewed = _scenario(stats_dir, typical, fields={"Crosshair Scale": "1.5"})

    cards = _cards(_view(stats_dir, runs, viewed))

    assert cards[Setting.CROSSHAIR_SCALE] == ("1.5", SettingTypical("1.5", 5))
    assert cards[Setting.DPI] == ("1600", SettingTypical("400", 2))


def test_a_card_is_marked_only_when_the_run_has_a_value_that_differs(
    stats_dir,
) -> None:
    runs, viewed = _scenario(
        stats_dir, fields={"DPI": None, "Crosshair Scale": "2.0", "Input Lag": "0"}
    )

    view = _view(stats_dir, runs, viewed)
    marked = {card.setting for card in view.figures.settings if card.marked}

    assert marked == {Setting.CROSSHAIR_SCALE}
    assert _cards(view)[Setting.DPI] == (None, SettingTypical("1600", 10))


def test_a_typical_run_whose_file_is_gone_keeps_its_run_records_settings(
    stats_dir,
) -> None:
    runs, viewed = _scenario(stats_dir)
    for typical_run in runs[:-1]:
        (stats_dir / typical_run.stats_file_name).unlink()

    cards = _cards(_view(stats_dir, runs, viewed))

    assert cards[Setting.SENSITIVITY][1] == SettingTypical("45.0 cm/360", 10)
    assert cards[Setting.FOV][1] == SettingTypical("103 Overwatch", 10)
    assert cards[Setting.DPI][1] is None


# --- By Bot ------------------------------------------------------------------------

# A PGT run that started at 21:59:00.000: three bots, one kill each.
PGT_KILLS: list[Kill] = [
    ("21:59:19.000", "Bounce 1 Bot", 1900, 684),
    ("21:59:39.500", "Bounce 2 Bot", 1975, 1013),
    ("21:59:59.750", "Float 3 Bot", 1972, 1158),
]


def _rows(view: RunView) -> dict:
    assert view.figures is not None
    return {row.name: row for row in view.figures.by_bot.rows}


def test_one_kill_per_bot_with_no_pace_basis_is_accuracy_only(stats_dir) -> None:
    viewed = _write_run(stats_dir, VIEWED_END, kills=PGT_KILLS)

    view = _view(stats_dir, [viewed], viewed)
    by_bot = view.figures.by_bot

    assert by_bot.kind is ByBotKind.ACCURACY_ONLY
    assert by_bot.times_unknown is None
    assert [row.name for row in by_bot.rows] == [
        "Bounce 1 Bot",
        "Bounce 2 Bot",
        "Float 3 Bot",
    ]
    first, second, third = by_bot.rows
    assert first.run.kills == 1
    assert first.run.accuracy == 684 / 1900
    assert first.run.time == pytest.approx(19.0)
    assert second.run.time == pytest.approx(20.5)
    assert third.run.time == pytest.approx(20.25)
    assert third.run.time_per_kill == pytest.approx(20.25)


def test_one_kill_per_bot_on_a_time_scored_version_is_time_scored(stats_dir) -> None:
    viewed = _write_run(stats_dir, VIEWED_END, score=10.0, kills=PGT_KILLS)

    view = _view(stats_dir, [viewed], viewed, {HASH: PaceBasis(70.0, HASH)})

    assert view.figures.by_bot.kind is ByBotKind.TIME_SCORED


def test_any_bot_with_two_kills_makes_many_kills_per_bot(stats_dir) -> None:
    kills: list[Kill] = [
        ("21:59:01.000", "Popcorn 1 Bot", 3, 2),
        ("21:59:02.500", "Popcorn 2 Bot", 4, 2),
        ("21:59:03.000", "Popcorn 1 Bot", 2, 2),
        ("21:59:05.000", "Popcorn 1 Bot", 5, 2),
    ]
    viewed = _write_run(stats_dir, VIEWED_END, kills=kills)

    rows = _rows(_view(stats_dir, [viewed], viewed, {HASH: PaceBasis(70.0, HASH)}))

    assert _view(stats_dir, [viewed], viewed).figures.by_bot.kind is (
        ByBotKind.MANY_KILLS
    )
    popcorn = rows["Popcorn 1 Bot"].run
    assert popcorn.kills == 3
    assert popcorn.accuracy == 6 / 10
    # Gaps 1.0 (from the start), 0.5 and 2.0.
    assert popcorn.time == pytest.approx(3.5)
    assert popcorn.time_per_kill == pytest.approx(3.5 / 3)
    assert rows["Popcorn 2 Bot"].run.time == pytest.approx(1.5)


def test_a_bots_typical_is_its_median_over_the_typical_runs_that_name_it(
    stats_dir,
) -> None:
    def typical(index: int) -> dict:
        # Float 3 Bot takes 20.0 + index / 10 seconds; Rare Bot only on run 3.
        last = "Rare Bot" if index == 3 else "Float 3 Bot"
        end = _typical_ends()[index]
        last_kill = end - timedelta(seconds=60) + timedelta(seconds=59.5)
        return {
            "kills": [
                (_clock(end - timedelta(seconds=41)), "Bounce 1 Bot", 100, 40 + index),
                (
                    _clock(last_kill - timedelta(seconds=20 + index / 10)),
                    "Bounce 2 Bot",
                    100,
                    50,
                ),
                (_clock(last_kill), last, 200, 100),
            ]
        }

    kills = [*PGT_KILLS, ("21:59:59.900", "Rare Bot", 10, 5)]
    kills.append(("21:59:59.950", "Never Bot", 10, 1))
    runs, viewed = _scenario(stats_dir, typical, kills=kills)

    rows = _rows(_view(stats_dir, runs, viewed))

    assert rows["Bounce 1 Bot"].accuracy == Typical(
        median((40 + i) / 100 for i in range(10)), 10
    )
    assert rows["Bounce 1 Bot"].kills == Typical(1, 10)
    assert rows["Bounce 1 Bot"].time == Typical(pytest.approx(19.0), 10)
    # 20.5 down to 19.6 seconds: the median of 20.1 and 20.0.
    assert rows["Bounce 2 Bot"].time == Typical(pytest.approx(20.05), 10)
    # 20.0 to 20.9 seconds, less run 3's 20.3: the fifth of nine is 20.5.
    assert rows["Float 3 Bot"].accuracy == Typical(0.5, 9)
    assert rows["Float 3 Bot"].time == Typical(pytest.approx(20.5), 9)
    assert rows["Float 3 Bot"].time_per_kill == Typical(pytest.approx(20.5), 9)
    assert rows["Rare Bot"].accuracy == Typical(0.5, 1)
    assert rows["Rare Bot"].time == Typical(pytest.approx(20.3), 1)
    never = rows["Never Bot"]
    assert (never.kills, never.accuracy, never.time, never.time_per_kill) == (
        None,
        None,
        None,
        None,
    )


@pytest.mark.parametrize(
    ("fields", "reason"),
    [
        ({"Challenge Start": None}, TimesUnknown.NO_START),
        ({"Pause Duration": "2.5", "Pause Count": "1"}, TimesUnknown.PAUSED),
        ({"Pause Duration": ""}, TimesUnknown.PAUSED),
        ({"Pause Duration": "later"}, TimesUnknown.PAUSED),
    ],
)
def test_times_are_unknown_without_a_start_or_after_a_pause(
    stats_dir, fields, reason
) -> None:
    viewed = _write_run(stats_dir, VIEWED_END, kills=PGT_KILLS, fields=fields)

    by_bot = _view(stats_dir, [viewed], viewed).figures.by_bot

    assert by_bot.times_unknown is reason
    assert [row.run.time for row in by_bot.rows] == [None, None, None]
    assert [row.run.time_per_kill for row in by_bot.rows] == [None, None, None]
    assert by_bot.rows[0].run.accuracy == 684 / 1900


def test_a_kill_after_midnight_gains_a_day(stats_dir) -> None:
    end = datetime(2026, 8, 7, 0, 0, 30)
    viewed = _write_run(
        stats_dir,
        end,
        kills=[
            ("23:59:42.000", "Plink 1 Bot", 10, 5),
            ("00:00:10.000", "Plink 2 Bot", 10, 5),
        ],
        fields={"Challenge Start": "23:59:30.000"},
    )

    by_bot = _view(stats_dir, [viewed], viewed).figures.by_bot

    assert by_bot.times_unknown is None
    assert [row.run.time for row in by_bot.rows] == [
        pytest.approx(12.0),
        pytest.approx(28.0),
    ]


@pytest.mark.parametrize(
    "kills",
    [
        # The first kill 10 seconds before Challenge Start, as on a B180
        # Voltaic run from December 2020.
        [("21:58:50.000", "B180 1 Bot", 10, 5), ("21:59:20.000", "B180 2 Bot", 10, 5)],
        # A later kill before the one ahead of it.
        [("21:59:20.000", "B180 1 Bot", 10, 5), ("21:59:15.000", "B180 2 Bot", 10, 5)],
        # A kill time that can't be read.
        [("21:59:20.000", "B180 1 Bot", 10, 5), ("soon", "B180 2 Bot", 10, 5)],
    ],
)
def test_times_that_disagree_are_unknown(stats_dir, kills) -> None:
    viewed = _write_run(stats_dir, VIEWED_END, kills=kills)

    by_bot = _view(stats_dir, [viewed], viewed).figures.by_bot

    assert by_bot.times_unknown is TimesUnknown.TIMES_DISAGREE
    assert [row.run.time for row in by_bot.rows] == [None, None]
    assert [row.run.accuracy for row in by_bot.rows] == [0.5, 0.5]


def test_a_2019_file_reads_its_kill_times_and_has_no_start(stats_dir) -> None:
    viewed = _write_run(
        stats_dir,
        VIEWED_END,
        old=True,
        kills=[("21:59:01:128", "target", 1, 1), ("21:59:02:853", "target", 2, 1)],
    )

    by_bot = _view(stats_dir, [viewed], viewed).figures.by_bot

    assert by_bot.kind is ByBotKind.MANY_KILLS
    assert by_bot.times_unknown is TimesUnknown.NO_START
    (row,) = by_bot.rows
    assert (row.name, row.run.kills, row.run.accuracy) == ("target", 2, 2 / 3)


def test_a_typical_run_with_unknown_times_counts_toward_accuracy_only(
    stats_dir,
) -> None:
    def typical(index: int) -> dict:
        end = _typical_ends()[index]
        paused = {"Pause Duration": "1.0"} if index < 4 else {}
        return {
            "kills": [(_clock(end - timedelta(seconds=40)), "Solo Bot", 10, 5)],
            "fields": paused,
        }

    runs, viewed = _scenario(
        stats_dir, typical, kills=[("21:59:20.000", "Solo Bot", 10, 5)]
    )

    (row,) = _view(stats_dir, runs, viewed).figures.by_bot.rows

    assert row.accuracy == Typical(0.5, 10)
    assert row.time == Typical(pytest.approx(20.0), 6)
