"""Define typical scores and their recency from one snapshot of runs.

The caller supplies one scenario's runs and the play sessions split from the
same snapshot of every scenario's runs. Nothing reads the run store, holds a
clock, or persists a value. The contract is in ``docs/specs/typical_score.md``.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from statistics import median, quantiles

from source.kovaaks.data_models import RunData
from source.kovaaks.play_sessions import PlaySession, in_play_order
from source.utilities.utilities import format_score

TYPICAL_SCORE_WINDOW_RUNS = 20
TYPICAL_SCORE_MIN_RUNS = 10
TYPICAL_SCORE_MIN_SESSIONS = 2
TYPICAL_SCORE_RECENT_AGE = timedelta(days=30)


@dataclass(frozen=True)
class TypicalScore:
    """One scenario's supporting window and its unrounded score statistics.

    Statistics are ``None`` until the window meets the existence minimum.
    ``runs`` is nonempty and in play order. Each parallel ``session_ids``
    entry names that run's session within this build, not a persisted ID.
    """

    runs: tuple[RunData, ...]
    session_ids: tuple[int, ...]
    median: float | None
    p25: float | None
    p75: float | None
    p10: float | None
    p90: float | None

    @property
    def known(self) -> bool:
        """Return whether the supporting window meets the existence minimum."""
        return self.median is not None

    @property
    def run_count(self) -> int:
        """Return how many runs support this value."""
        return len(self.runs)

    @property
    def session_count(self) -> int:
        """Return how many play sessions the supporting runs belong to."""
        return len(set(self.session_ids))

    @property
    def first_date(self) -> datetime:
        """Return when the oldest supporting run ended."""
        return self.runs[0].datetime_object

    @property
    def last_date(self) -> datetime:
        """Return when the newest supporting run ended."""
        return self.runs[-1].datetime_object


@dataclass(frozen=True)
class TypicalScoreRecency:
    """A value's recency and its recent run and session counts at one moment."""

    recent: bool
    run_count: int
    session_count: int


def build_typical_scores(
    runs: Iterable[RunData], play_sessions: Iterable[PlaySession]
) -> list[TypicalScore]:
    """Return the typical score after each run of one scenario, in play order.

    Count every sensitivity, version and warm-up run. ``play_sessions`` must
    have been split across every scenario in the same run snapshot; a missing
    run raises ``ValueError`` rather than inventing its session membership.
    Empty input returns no values. Neither input is changed.
    """
    session_by_run = {
        run: session_id
        for session_id, session in enumerate(play_sessions)
        for run in session.runs
    }
    ordered = in_play_order(runs)
    try:
        ordered_session_ids = [session_by_run[run] for run in ordered]
    except KeyError:
        msg = "Runs and play sessions must come from the same run snapshot."
        raise ValueError(msg) from None
    # Binary arithmetic can turn the median of 2.3 and 2.4 into
    # 2.3499999999999996, losing a half before display rounding.
    # Decimal arithmetic preserves it without quantizing the value.
    ordered_scores = [Decimal(str(run.score)) for run in ordered]
    values: list[TypicalScore] = []
    for end in range(1, len(ordered) + 1):
        start = max(0, end - TYPICAL_SCORE_WINDOW_RUNS)
        window = tuple(ordered[start:end])
        session_ids = tuple(ordered_session_ids[start:end])
        known = len(window) == TYPICAL_SCORE_WINDOW_RUNS or (
            len(window) >= TYPICAL_SCORE_MIN_RUNS
            and len(set(session_ids)) >= TYPICAL_SCORE_MIN_SESSIONS
        )
        middle = p25 = p75 = p10 = p90 = None
        if known:
            scores = ordered_scores[start:end]
            middle = float(median(scores))
            quartiles = quantiles(scores, n=4, method="inclusive")
            p25, p75 = float(quartiles[0]), float(quartiles[-1])
            deciles = quantiles(scores, n=10, method="inclusive")
            p10, p90 = float(deciles[0]), float(deciles[-1])
        values.append(TypicalScore(window, session_ids, middle, p25, p75, p10, p90))
    return values


def typical_score_recency(value: TypicalScore, moment: datetime) -> TypicalScoreRecency:
    """Judge a value at ``moment`` and count its recent runs and their sessions.

    A run exactly ``TYPICAL_SCORE_RECENT_AGE`` old counts; one after the
    judging moment does not. Session counts describe the recent runs but
    impose no extra minimum. An unknown value cannot be recent. Times are
    local wall-clock times, as the stats files wrote them.
    """
    cutoff = moment - TYPICAL_SCORE_RECENT_AGE
    session_ids = [
        session_id
        for run, session_id in zip(value.runs, value.session_ids, strict=True)
        if cutoff <= run.datetime_object <= moment
    ]
    return TypicalScoreRecency(
        recent=value.known and len(session_ids) >= TYPICAL_SCORE_MIN_RUNS,
        run_count=len(session_ids),
        session_count=len(set(session_ids)),
    )


def typical_score_fade_time(value: TypicalScore) -> datetime | None:
    """Return a held value's inclusive recency boundary, or None if unknown.

    For a hold at or after its newest run, a known value is recent through
    this moment and not recent strictly after it. The boundary is its tenth
    newest run's end plus ``TYPICAL_SCORE_RECENT_AGE``. It can already be in
    the past when the value is built, in which case the hold starts faded.
    """
    if not value.known:
        return None
    return (
        value.runs[-TYPICAL_SCORE_MIN_RUNS].datetime_object + TYPICAL_SCORE_RECENT_AGE
    )


def format_typical_score(score: float, runs: Iterable[RunData]) -> str:
    """Format a median or percentile to its supporting runs' score precision.

    Use the most decimal places of any supporting score, capped at two,
    with a half rounded up. Thousands separators and trailing-zero removal
    follow ``format_score``. Empty supporting runs raise ``ValueError``.
    This display step never changes a ``TypicalScore``'s statistics.
    """
    places = max(
        (
            max(0, -int(Decimal(str(run.score)).normalize().as_tuple().exponent))
            for run in runs
        ),
        default=None,
    )
    if places is None:
        msg = "A typical score needs supporting runs to choose its display precision."
        raise ValueError(msg)
    quantum = Decimal(1).scaleb(-min(places, 2))
    # Quantize before the shared formatter: its format spec rounds a half to
    # even, which would show a whole-score median of 2140.5 as 2,140.
    rounded = Decimal(str(score)).quantize(quantum, rounding=ROUND_HALF_UP)
    return format_score(float(rounded))
