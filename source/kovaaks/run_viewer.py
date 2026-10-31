"""Read one run whole, and work out what the run viewer shows of it.

``read_run_file`` reads a stats file's three parts as KovaaK's wrote them: its
kill table, its weapon rows and its ``Key:,value`` fields. ``view_run`` works
out everything the run viewer shows of one run from a copy of the run store:
the figures that measure it against its typical runs, its settings, and By
Bot. Its typical runs are the runs behind its typical score at session start.

The run's stats file and its typical runs' files are read each time a run is
viewed. Nothing is kept, and the stats folder is only ever read. The rules
are the run viewer's decision-log entries of 2026-10-30, in
``docs/decision_log/2026/``, and its statements in
``docs/specs/run_history.md``.
"""

import logging
import math
import re
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import time, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from statistics import median

from source.config.settings_service import get_usable_stats_dir
from source.kovaaks.data_models import RunData, run_id
from source.kovaaks.data_service import get_all_runs, parse_pause_duration
from source.kovaaks.play_sessions import (
    PlaySession,
    in_play_order,
    split_into_play_sessions,
)
from source.kovaaks.time_scored_service import (
    PaceBasis,
    eligible_pace_constant,
    get_version_pace_basis,
    has_performance_file,
)
from source.kovaaks.typical_score import TypicalScore, typical_score_at_session_start
from source.utilities.utilities import (
    format_decimal,
    fov_text,
    recorded_sensitivity_suffix,
    sensitivity_text,
)

logger = logging.getLogger(__name__)

_KILL_TABLE_HEADER_START = "Kill #,"
_WEAPON_HEADER_START = "Weapon,"

# Kill times are times of day with no date. A gap this far below zero crossed
# midnight; one nearer zero means the file's times disagree.
_MIDNIGHT_GAP_SECONDS = -12 * 60 * 60
_DAY_SECONDS = 24 * 60 * 60
# KovaaK's 1.0.8 put a colon before the milliseconds.
_KILL_TIME = re.compile(r"(\d{1,2}):(\d{2}):(\d{2})[.:](\d+)")


# --- The file as written -------------------------------------------------------


@dataclass(frozen=True)
class RunTable:
    """One of a stats file's tables as written: its header, then its rows.

    Every cell is a string, stripped of the spaces around it.
    """

    header: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class RunFile:
    """A stats file's three parts, as KovaaK's wrote them.

    ``fields`` is every line outside the two tables, in file order, as its
    key without the colon and everything after the first comma, which is
    ``""`` on a line that has none. Everything, because a scenario's name can
    hold a comma. KovaaK's 2.0.3 to 2.0.5 wrote ``Resolution``,
    ``Resolution Scale`` and ``Avg FPS`` with no colon, and they read like the
    rest. A key the game adds in an update is kept like any other.
    ``weapons`` keeps only the columns the weapon rows fill: the header goes
    on to name settings columns that the rows leave empty. ``kills`` keeps
    every column, and has no rows when the run recorded no kill.
    """

    fields: tuple[tuple[str, str], ...]
    weapons: RunTable
    kills: RunTable

    def field(self, key: str) -> str | None:
        """Return the value of the first line with ``key``, or None with no such line.

        A line with no value returns ``""``, which a reader that tells a
        missing line from an empty one needs.
        """
        return next((value for name, value in self.fields if name == key), None)

    def value(self, key: str) -> str | None:
        """Return the value of ``key``, or None when the line is missing or empty."""
        return self.field(key) or None


def _cells(line: str) -> tuple[str, ...]:
    return tuple(cell.strip() for cell in line.split(","))


def _filled(table: RunTable) -> RunTable:
    """Cut a weapon table to the columns its rows fill, padding every row to them.

    Rows nearly always stop at Damage Possible, but some files of KovaaK's
    2.0.1 fill the settings columns too, and those cells must not be lost.
    """
    width = max(
        (
            max((index + 1 for index, cell in enumerate(row) if cell), default=0)
            for row in table.rows
        ),
        default=0,
    )

    def padded(cells: tuple[str, ...]) -> tuple[str, ...]:
        return cells[:width] + ("",) * (width - len(cells))

    return RunTable(padded(table.header), tuple(padded(row) for row in table.rows))


def _parse_run_file(text: str) -> RunFile:
    """Split a stats file's text into its kill table, weapon rows and fields.

    A blank line ends a table, and a line outside one is a field. Never
    raises: a file cut short mid-write reads as the parts it has.
    """
    fields: list[tuple[str, str]] = []
    tables: dict[str, tuple[tuple[str, ...], list[tuple[str, ...]]]] = {}
    rows: list[tuple[str, ...]] | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            rows = None
        elif line.startswith((_KILL_TABLE_HEADER_START, _WEAPON_HEADER_START)):
            rows = []
            tables[line[: line.index(",")]] = (_cells(line), rows)
        elif rows is not None:
            rows.append(_cells(line))
        else:
            key, _, value = line.partition(",")
            fields.append((key.strip().removesuffix(":"), value.strip()))

    def table(name: str) -> RunTable:
        header, table_rows = tables.get(name, ((), []))
        return RunTable(header, tuple(table_rows))

    return RunFile(
        fields=tuple(fields),
        weapons=_filled(table("Weapon")),
        kills=table("Kill #"),
    )


def read_run_file(path: str | Path) -> RunFile | None:
    """Read a stats file whole, or return None when it can't be read.

    A file that is missing, locked or not text is logged and returns None:
    it costs the view of one run, never the page.
    """
    try:
        # ``utf-8-sig``: a byte-order mark would otherwise hide the kill table
        # header on the first line.
        text = Path(path).read_text(encoding="utf-8-sig")
    except OSError as exc:
        logger.warning('Failed to read run file "%s": %s', path, exc)
        return None
    except UnicodeDecodeError:
        logger.warning('Run file is not UTF-8 text: "%s"', path, exc_info=True)
        return None
    return _parse_run_file(text)


# --- Typicals ------------------------------------------------------------------


@dataclass(frozen=True)
class Typical:
    """A figure's median over the typical runs that have it.

    ``count`` is how many typical runs the median took, at least one.
    """

    value: float
    count: int


def _median_of(values: Iterable[float | None]) -> Typical | None:
    known = [value for value in values if value is not None]
    if not known:
        return None
    return Typical(value=median(known), count=len(known))


# --- Tiles ---------------------------------------------------------------------


@dataclass(frozen=True)
class Tile:
    """One tile's figure: the run's, and its typical.

    ``run`` is None when the run has no such figure. ``typical`` is None when
    there are no typical runs, or none has the figure.
    """

    run: float | None
    typical: Typical | None


@dataclass(frozen=True)
class Tiles:
    """The run's tiles.

    ``accuracy`` is KovaaK's hits over shots, a fraction. ``time`` is the
    completion time in seconds, and None when the run's own version isn't
    known to be time-scored, which leaves the run with no Time tile. Its
    typical exists only when every typical run is of that version too.
    """

    score: Tile
    accuracy: Tile
    shots_fired: Tile
    reloads: Tile
    time: Tile | None


def _completion_time(constant: float, run: RunData) -> float | None:
    """Return the seconds a score took on a time-scored version, or None.

    A time of zero or less isn't a time.
    """
    seconds = constant - run.score
    return seconds if seconds > 0 else None


def _tiles(
    run: RunData,
    typical_score: TypicalScore | None,
    typical_runs: Sequence[RunData],
    basis: PaceBasis | None,
) -> Tiles:
    # The score's typical is the typical score itself, not a median worked
    # out again here: the two would differ in the last float digit.
    score_typical = (
        Typical(typical_score.median, len(typical_runs))
        if typical_runs
        and typical_score is not None
        and typical_score.median is not None
        else None
    )
    time_tile = None
    constant = eligible_pace_constant(basis, run)
    if constant is not None:
        typical_constant = eligible_pace_constant(basis, *typical_runs, run)
        time_tile = Tile(
            run=_completion_time(constant, run),
            typical=(
                None
                if typical_constant is None
                else _median_of(
                    _completion_time(typical_constant, typical_run)
                    for typical_run in typical_runs
                )
            ),
        )
    return Tiles(
        score=Tile(run.score, score_typical),
        accuracy=Tile(run.accuracy, _median_of(r.accuracy for r in typical_runs)),
        shots_fired=Tile(
            run.shots_fired, _median_of(r.shots_fired for r in typical_runs)
        ),
        reloads=Tile(run.reloads, _median_of(r.reloads for r in typical_runs)),
        time=time_tile,
    )


# --- Settings ------------------------------------------------------------------


class Setting(Enum):
    """The settings cards, in the order they are drawn: the aim setup, then the rest."""

    SENSITIVITY = "sensitivity"
    VERTICAL_SENSITIVITY = "vertical_sensitivity"
    DPI = "dpi"
    FOV = "fov"
    CROSSHAIR = "crosshair"
    CROSSHAIR_SCALE = "crosshair_scale"
    HIDE_GUN = "hide_gun"
    RESOLUTION = "resolution"
    RESOLUTION_SCALE = "resolution_scale"
    FRAME_CAP = "frame_cap"
    INPUT_LAG = "input_lag"


SAME_AS_HORIZONTAL_TEXT = "Same as horizontal"
YES_TEXT = "Yes"
NO_TEXT = "No"


@dataclass(frozen=True)
class SettingTypical:
    """A setting's most common value over the typical runs that have one.

    ``count`` is how many typical runs used it.
    """

    value: str
    count: int


@dataclass(frozen=True)
class SettingCard:
    """One setting of the run, as its card shows it.

    ``value`` is None when the stats file doesn't have the setting, or has it
    with no value. ``typical`` is None when there are no typical runs, or
    none has the setting.
    """

    setting: Setting
    value: str | None
    typical: SettingTypical | None

    @property
    def marked(self) -> bool:
        """Return whether the run's value differs from its typical one."""
        return (
            self.value is not None
            and self.typical is not None
            and self.value != self.typical.value
        )


def _number(raw: str) -> float | None:
    try:
        number = float(raw)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def _plain_number(raw: str) -> str:
    """Write a number without a trailing ``.0``, or return text that isn't one as written."""
    return raw if _number(raw) is None else str(format_decimal(Decimal(raw)))


def _vertical_sensitivity(file: RunFile) -> str | None:
    vertical = file.value("Vert Sens")
    if vertical is None:
        return None
    horizontal = file.value("Horiz Sens")
    if horizontal is not None:
        # Equal as numbers too, so ``45`` and ``45.0`` read as the same.
        vertical_number = _number(vertical)
        if vertical == horizontal or (
            vertical_number is not None and vertical_number == _number(horizontal)
        ):
            return SAME_AS_HORIZONTAL_TEXT
    scale = file.value("Sens Scale")
    return f"{vertical} {scale}" if scale else vertical


def _hide_gun(file: RunFile) -> str | None:
    raw = file.value("Hide Gun")
    if raw is None:
        return None
    # Any other word is shown as written, so a game update never hides it.
    return {"true": YES_TEXT, "false": NO_TEXT}.get(raw.lower(), raw)


def _resolution_scale(file: RunFile) -> str | None:
    raw = file.value("Resolution Scale")
    if raw is None or _number(raw) is None:
        return raw
    return f"{_plain_number(raw)}%"


def _setting_value(  # noqa: PLR0911  (one return per card)
    setting: Setting, run: RunData, file: RunFile
) -> str | None:
    """Return a setting's value as its card shows it, or None when the file lacks it.

    Sensitivity and FOV are the run list's text for the run, so the two
    never read differently. The rest come from the stats file.
    """
    match setting:
        case Setting.SENSITIVITY:
            suffix = recorded_sensitivity_suffix(run.recorded_sensitivity)
            return f"{sensitivity_text(run)}{suffix}"
        case Setting.VERTICAL_SENSITIVITY:
            return _vertical_sensitivity(file)
        case Setting.DPI:
            return file.value("DPI")
        case Setting.FOV:
            return fov_text(run) or None
        case Setting.CROSSHAIR:
            crosshair = file.value("Crosshair")
            return crosshair.removesuffix(".png") if crosshair else None
        case Setting.CROSSHAIR_SCALE:
            return file.value("Crosshair Scale")
        case Setting.HIDE_GUN:
            return _hide_gun(file)
        case Setting.RESOLUTION:
            return file.value("Resolution")
        case Setting.RESOLUTION_SCALE:
            return _resolution_scale(file)
        case Setting.FRAME_CAP:
            frame_cap = file.value("Max FPS (config)")
            return _plain_number(frame_cap) if frame_cap else None
        case Setting.INPUT_LAG:
            return file.value("Input Lag")


def _most_common(values_oldest_first: Sequence[str | None]) -> SettingTypical | None:
    """Return the most common value, a tie going to the one used last."""
    counts = Counter(value for value in values_oldest_first if value is not None)
    if not counts:
        return None
    top = max(counts.values())
    latest = next(
        value
        for value in reversed(values_oldest_first)
        if value is not None and counts[value] == top
    )
    return SettingTypical(value=latest, count=top)


def _settings(
    run: RunData,
    file: RunFile,
    typical: Sequence[tuple[RunData, RunFile | None]],
) -> tuple[SettingCard, ...]:
    cards = []
    for setting in Setting:
        cards.append(
            SettingCard(
                setting=setting,
                value=_setting_value(setting, run, file),
                typical=_most_common(
                    [
                        # A typical run whose file can't be read still has the
                        # two settings its run record holds.
                        _setting_value(setting, typical_run, typical_file or _NO_FILE)
                        for typical_run, typical_file in typical
                    ]
                ),
            )
        )
    return tuple(cards)


_NO_FILE = RunFile(fields=(), weapons=RunTable((), ()), kills=RunTable((), ()))


# --- By Bot --------------------------------------------------------------------


class ByBotKind(Enum):
    """What By Bot's figure is, from how the run's kill table names its bots."""

    # Any bot has two kill rows or more: the figure is the time per kill.
    MANY_KILLS = "many_kills"
    # Each bot is one kill, on a version known to be time-scored: the figure
    # is each bot's time, the run's split.
    TIME_SCORED = "time_scored"
    # Each bot is one kill on any other run: accuracy alone. The app can't
    # tell a phase of fixed length from a split, so a time could mean nothing.
    ACCURACY_ONLY = "accuracy_only"


class TimesUnknown(Enum):
    """Why a run's kill times are unknown."""

    # The file has no ``Challenge Start:`` the run record could use.
    NO_START = "no_start"
    # A gap since the kill before is below zero, short of crossing midnight,
    # or a kill's time can't be read.
    TIMES_DISAGREE = "times_disagree"
    # ``Pause Duration:`` is above zero or can't be read: the file gives the
    # paused time but not which gap it fell in.
    PAUSED = "paused"


@dataclass(frozen=True)
class BotFigures:
    """One bot's figures in one run.

    ``accuracy`` is its kill rows' hits over their shots, None when they
    hold no shot or a count can't be read. The kill table leaves out shots
    fired after the last kill, so it is not the tile's accuracy. ``time`` is
    the sum of its kills' gaps since the kill before each, the first kill's
    from the run's start, in seconds; None when the run's times are unknown.
    """

    kills: int
    accuracy: float | None
    time: float | None

    @property
    def time_per_kill(self) -> float | None:
        """Return the bot's time over its kills, or None with no time."""
        return None if self.time is None else self.time / self.kills


@dataclass(frozen=True)
class BotRow:
    """One bot of the run, with the typical of each of its figures.

    Each typical is the median over the typical runs that name the bot and
    have that figure, and is None when none does.
    """

    name: str
    run: BotFigures
    kills: Typical | None
    accuracy: Typical | None
    time: Typical | None
    time_per_kill: Typical | None


@dataclass(frozen=True)
class ByBot:
    """Every bot the run's kill table names, in the order each was first killed.

    ``kind`` decides what the table shows, and is None with no bot: a run
    whose kill table is empty. One bot gets a row too. ``times_unknown`` says
    why the run's times are unknown, and is None when they are known.
    """

    kind: ByBotKind | None
    times_unknown: TimesUnknown | None
    rows: tuple[BotRow, ...]


@dataclass(frozen=True)
class _RunBots:
    bots: dict[str, BotFigures]
    times_unknown: TimesUnknown | None


_NO_BOTS = _RunBots({}, None)


def _seconds_of_day(moment: time) -> float:
    return (
        moment.hour * 3600 + moment.minute * 60 + moment.second
    ) + moment.microsecond / 1_000_000


def _kill_time(raw: str) -> float | None:
    """Read a kill's time of day as seconds, or None when it isn't one."""
    match = _KILL_TIME.fullmatch(raw)
    if match is None:
        return None
    hours, minutes, seconds = (int(part) for part in match.groups()[:3])
    if hours > 23 or minutes > 59 or seconds > 59:
        return None
    return hours * 3600 + minutes * 60 + seconds + float(f"0.{match.group(4)}")


def _gap(earlier: float, later: float) -> float | None:
    """Return the seconds from one time of day to the next, or None when they disagree."""
    gap = later - earlier
    if gap < _MIDNIGHT_GAP_SECONDS:
        return gap + _DAY_SECONDS
    return gap if gap >= 0 else None


def _kill_gaps(
    run: RunData, file: RunFile, kill_times: Sequence[str]
) -> tuple[list[float], TimesUnknown | None]:
    """Return each kill's gap since the kill before, or why they are unknown.

    The start is the run record's, which ``_run_start_and_length`` in the
    data service judged usable: a start it refused, such as one left over
    from an earlier run, would give the first bot a wrong time. A pause is
    checked before the start because an unreadable pause also costs the run
    record its start, when the file does have one.
    """
    paused = parse_pause_duration(file.field("Pause Duration"))
    if paused is None or paused > timedelta(0):
        return [], TimesUnknown.PAUSED
    if run.run_start is None:
        return [], TimesUnknown.NO_START
    previous = _seconds_of_day(run.run_start.time())
    gaps = []
    for raw in kill_times:
        kill_time = _kill_time(raw)
        gap = None if kill_time is None else _gap(previous, kill_time)
        if kill_time is None or gap is None:
            return [], TimesUnknown.TIMES_DISAGREE
        gaps.append(gap)
        previous = kill_time
    return gaps, None


def _count(raw: str) -> int | None:
    try:
        count = int(raw)
    except ValueError:
        return None
    return count if count >= 0 else None


def _run_bots(run: RunData, file: RunFile) -> _RunBots:
    """Work out each bot's figures in one run from its kill table."""
    header = file.kills.header
    try:
        columns = [header.index(name) for name in ("Bot", "Timestamp", "Shots", "Hits")]
    except ValueError:
        return _NO_BOTS
    width = max(columns) + 1
    # A row cut short mid-write can't name its bot, so it is left out, and the
    # gaps around it would be wrong.
    rows = [row for row in file.kills.rows if len(row) >= width]
    if not rows:
        return _NO_BOTS
    bot, timestamp, shots, hits = columns
    gaps, times_unknown = _kill_gaps(run, file, [row[timestamp] for row in rows])
    if len(rows) < len(file.kills.rows) and times_unknown is None:
        gaps, times_unknown = [], TimesUnknown.TIMES_DISAGREE

    kills: Counter[str] = Counter()
    shot_counts: dict[str, int | None] = {}
    hit_counts: dict[str, int | None] = {}
    times: dict[str, float] = {}
    for index, row in enumerate(rows):
        name = row[bot]
        kills[name] += 1
        for counts, raw in ((shot_counts, row[shots]), (hit_counts, row[hits])):
            count, total = _count(raw), counts.get(name, 0)
            counts[name] = None if count is None or total is None else total + count
        if times_unknown is None:
            times[name] = times.get(name, 0.0) + gaps[index]

    def accuracy(name: str) -> float | None:
        shot_count, hit_count = shot_counts[name], hit_counts[name]
        if not shot_count or hit_count is None:
            return None
        return hit_count / shot_count

    return _RunBots(
        bots={
            name: BotFigures(kills=count, accuracy=accuracy(name), time=times.get(name))
            for name, count in kills.items()
        },
        times_unknown=times_unknown,
    )


def _by_bot(
    run: RunData,
    file: RunFile,
    typical: Sequence[tuple[RunData, RunFile | None]],
    time_scored: bool,
) -> ByBot:
    figures = _run_bots(run, file)
    if not figures.bots:
        return ByBot(kind=None, times_unknown=figures.times_unknown, rows=())
    if any(bot.kills >= 2 for bot in figures.bots.values()):
        kind = ByBotKind.MANY_KILLS
    else:
        kind = ByBotKind.TIME_SCORED if time_scored else ByBotKind.ACCURACY_ONLY
    typical_bots = [
        _run_bots(typical_run, typical_file).bots
        for typical_run, typical_file in typical
        if typical_file is not None
    ]
    rows = []
    for name, bot in figures.bots.items():
        named = [bots[name] for bots in typical_bots if name in bots]
        rows.append(
            BotRow(
                name=name,
                run=bot,
                kills=_median_of(other.kills for other in named),
                accuracy=_median_of(other.accuracy for other in named),
                time=_median_of(other.time for other in named),
                time_per_kill=_median_of(other.time_per_kill for other in named),
            )
        )
    return ByBot(kind=kind, times_unknown=figures.times_unknown, rows=tuple(rows))


# --- The view ------------------------------------------------------------------


@dataclass(frozen=True)
class RunFigures:
    """Everything the run viewer works out from a run's stats file and its typical runs.

    ``typical_score`` is the scenario's typical score when the run's session
    began, None when the scenario has no run before the session.
    ``typical_runs`` are the runs behind it while it is known, in play
    order, and empty otherwise. ``pace_basis`` is what the run's own version
    says of its pace. ``performance_file_found`` is whether the game's
    performance file for the run is in the listing.
    """

    file: RunFile
    performance_file_found: bool
    typical_score: TypicalScore | None
    typical_runs: tuple[RunData, ...]
    pace_basis: PaceBasis | None
    tiles: Tiles
    settings: tuple[SettingCard, ...]
    by_bot: ByBot


@dataclass(frozen=True)
class RunView:
    """One run as the run viewer shows it.

    ``session`` is the play session the run is in, and ``number`` the run's
    number in it among its scenario's runs, as the run list numbers it.
    ``figures`` is None when the run's stats file can't be read.
    """

    run: RunData
    session: PlaySession
    number: int
    figures: RunFigures | None


def _file_path(stats_dir: str | Path, run: RunData) -> Path | None:
    if run.stats_file_name is None:
        return None
    return Path(stats_dir) / run.stats_file_name


def _read(stats_dir: str | Path, run: RunData) -> RunFile | None:
    path = _file_path(stats_dir, run)
    return None if path is None else read_run_file(path)


def view_run(
    all_runs: Iterable[RunData],
    viewed_run_id: str,
    stats_dir: str | Path,
    version_pace_basis: Callable[[str, str | None], PaceBasis | None],
    performance_file_found: Callable[[RunData], bool],
) -> RunView | None:
    """Work out what the run viewer shows of one run, or None when it isn't in ``all_runs``.

    ``all_runs`` is a copy of every run in the run store, on every scenario,
    which the sessions are split from as the run list splits them.
    ``viewed_run_id`` is the run's id, as the list keys its row.
    ``version_pace_basis`` answers for one version of one scenario, and
    ``performance_file_found`` for one run. The run's stats file is read, and
    then its typical runs' files.
    """
    runs = list(all_runs)
    run = next((run for run in runs if run_id(run) == viewed_run_id), None)
    if run is None:
        return None
    sessions = split_into_play_sessions(runs)
    session = next(session for session in sessions if run in session.runs)
    number = [r for r in session.runs if r.scenario == run.scenario].index(run) + 1

    file = _read(stats_dir, run)
    if file is None:
        return RunView(run=run, session=session, number=number, figures=None)

    scenario_runs = in_play_order(r for r in runs if r.scenario == run.scenario)
    typical_score = typical_score_at_session_start(scenario_runs, sessions, session)
    typical_runs = (
        typical_score.runs if typical_score is not None and typical_score.known else ()
    )
    typical = [
        (typical_run, _read(stats_dir, typical_run)) for typical_run in typical_runs
    ]
    basis = version_pace_basis(run.scenario, run.scenario_hash)
    return RunView(
        run=run,
        session=session,
        number=number,
        figures=RunFigures(
            file=file,
            performance_file_found=performance_file_found(run),
            typical_score=typical_score,
            typical_runs=typical_runs,
            pace_basis=basis,
            tiles=_tiles(run, typical_score, typical_runs, basis),
            settings=_settings(run, file, typical),
            by_bot=_by_bot(
                run,
                file,
                typical,
                time_scored=eligible_pace_constant(basis, run) is not None,
            ),
        ),
    )


def view_run_from_store(viewed_run_id: str) -> RunView | None:
    """Work out what the run viewer shows of one run in the run store, or None.

    None also when no stats folder was scanned, as the store is then empty.
    """
    stats_dir = get_usable_stats_dir()
    if stats_dir is None:
        return None
    return view_run(
        get_all_runs(),
        viewed_run_id,
        stats_dir,
        get_version_pace_basis,
        has_performance_file,
    )
