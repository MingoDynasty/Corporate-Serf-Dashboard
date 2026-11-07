import random
from datetime import datetime, timedelta

import pytest

from source.kovaaks.data_models import RunData
from source.kovaaks.play_sessions import split_into_play_sessions
from source.kovaaks.typical_score import (
    RunBand,
    TypicalScore,
    band_at_session_start,
    typical_score_at_session_start,
    typical_score_recency,
)

START = datetime(2026, 5, 1, 10)


def _run(end: datetime, score: float) -> RunData:
    return RunData(
        datetime_object=end,
        score=score,
        scenario="1w4ts",
        sens_scale="cm/360",
        horizontal_sens=40,
        accuracy=0.5,
        run_start=end - timedelta(seconds=60),
        run_length=timedelta(seconds=60),
    )


def _sitting(scores: list[float], start: datetime) -> list[RunData]:
    return [
        _run(start + timedelta(minutes=index * 2), score)
        for index, score in enumerate(scores)
    ]


def _value_at_next_session(*sittings: list[float], gap_days: int = 1):
    """Return a session played after ``sittings`` and its typical score at its start.

    Each sitting is played on its own day, and the session ``gap_days`` after
    the last of them. The value comes first.
    """
    runs = [
        run
        for day, scores in enumerate(sittings)
        for run in _sitting(scores, START + timedelta(days=day))
    ]
    runs += _sitting([0], START + timedelta(days=len(sittings) - 1 + gap_days))
    sessions = split_into_play_sessions(runs)
    session = sessions[-1]
    return typical_score_at_session_start(runs, sessions, session), session


def _edges(value: TypicalScore | None) -> tuple:
    assert value is not None
    return value.p10, value.p25, value.p75, value.p90


def test_the_bands_are_named_as_the_screen_names_them() -> None:
    assert [band.value for band in RunBand] == [
        "Top 10%",
        "Top 25%",
        "Middle 50%",
        "Bottom 25%",
        "Bottom 10%",
    ]


@pytest.mark.parametrize(
    ("score", "band"),
    [
        (1000, RunBand.TOP_10),
        (181.01, RunBand.TOP_10),
        (181, RunBand.TOP_25),
        (180.99, RunBand.TOP_25),
        (152.51, RunBand.TOP_25),
        (152.5, RunBand.MIDDLE_50),
        (152.49, RunBand.MIDDLE_50),
        (100, RunBand.MIDDLE_50),
        (57.51, RunBand.MIDDLE_50),
        (57.5, RunBand.MIDDLE_50),
        (57.49, RunBand.BOTTOM_25),
        (29.01, RunBand.BOTTOM_25),
        (29, RunBand.BOTTOM_25),
        (28.99, RunBand.BOTTOM_10),
        (0, RunBand.BOTTOM_10),
        (-5, RunBand.BOTTOM_10),
    ],
)
def test_each_band_at_above_and_below_every_edge(score, band) -> None:
    """A score on an edge belongs to the inner band, as a point on a drawn band."""
    value, _ = _value_at_next_session([10 * index for index in range(1, 21)])

    assert _edges(value) == (29, 57.5, 152.5, 181)
    assert band_at_session_start(score, value) is band


def test_a_window_of_ten_runs_over_two_sessions_has_bands() -> None:
    value, _ = _value_at_next_session([1, 2, 3, 4, 5], [6, 7, 8, 9, 10])

    assert value is not None
    assert (value.run_count, value.session_count) == (10, 2)
    assert _edges(value) == (1.9, 3.25, 7.75, 9.1)
    assert band_at_session_start(9.2, value) is RunBand.TOP_10
    assert band_at_session_start(9.1, value) is RunBand.TOP_25
    assert band_at_session_start(5, value) is RunBand.MIDDLE_50
    assert band_at_session_start(1.9, value) is RunBand.BOTTOM_25
    assert band_at_session_start(1.8, value) is RunBand.BOTTOM_10


def test_only_the_last_twenty_runs_before_the_session_make_the_edges() -> None:
    """Five older runs of 1,000 have left the window, so 25 tops it."""
    value, _ = _value_at_next_session([1000] * 5, list(range(1, 21)))

    assert value is not None
    assert value.run_count == 20
    assert band_at_session_start(25, value) is RunBand.TOP_10
    assert band_at_session_start(999, value) is RunBand.TOP_10


def test_every_run_of_a_session_meets_the_edges_it_began_with() -> None:
    """No run meets edges it helped make, so a steady session stays Top 10%."""
    before = _sitting(list(range(1, 21)), START)
    session_runs = _sitting([19.5] * 10, START + timedelta(days=1))
    runs = before + session_runs
    sessions = split_into_play_sessions(runs)
    session = sessions[-1]

    bands = [
        band_at_session_start(
            run.score,
            typical_score_at_session_start(
                runs[: len(before) + end], sessions, session
            ),
        )
        for end, run in enumerate(session_runs, start=1)
    ]

    assert bands == [RunBand.TOP_10] * 10


@pytest.mark.parametrize(
    ("score", "band"),
    [
        (201, RunBand.TOP_10),
        (200, RunBand.MIDDLE_50),
        (150, RunBand.MIDDLE_50),
        (100, RunBand.MIDDLE_50),
        (99, RunBand.BOTTOM_10),
    ],
)
def test_integer_scores_tied_on_an_edge_belong_to_the_inner_band(score, band) -> None:
    """Ten runs of 100 and ten of 200 put P10 on P25 and P75 on P90."""
    value, _ = _value_at_next_session([100] * 10 + [200] * 10)

    assert _edges(value) == (100, 100, 200, 200)
    assert band_at_session_start(score, value) is band


@pytest.mark.parametrize(
    ("score", "band"),
    [(151, RunBand.TOP_10), (150, RunBand.MIDDLE_50), (149, RunBand.BOTTOM_10)],
)
def test_a_window_of_one_score_has_only_its_middle_and_outer_bands(score, band) -> None:
    value, _ = _value_at_next_session([150] * 20)

    assert _edges(value) == (150, 150, 150, 150)
    assert band_at_session_start(score, value) is band


@pytest.mark.parametrize(
    ("sittings", "edge", "score", "band"),
    [
        (
            ([1.55, 1.62, 1.62, 1.71, 1.83], [1.83, 1.93, 2.0, 2.01, 2.11]),
            "p90",
            2.02,
            RunBand.TOP_25,
        ),
        (
            ([3.95, 3.98, 4.07, 4.19, 4.21], [4.22, 4.39, 4.39, 4.42, 4.45]),
            "p25",
            4.1,
            RunBand.MIDDLE_50,
        ),
    ],
)
def test_a_decimal_score_on_an_edge_belongs_to_the_inner_band(
    sittings, edge, score, band
) -> None:
    """The edge is worked out in decimals, so the run sits on it exactly.

    In binary floats the P90 is 2.0199999999999996, under 2.02, and the P25
    is 4.1000000000000005, over 4.1, which would put each run in the outer band.
    """
    value, _ = _value_at_next_session(*sittings)

    assert getattr(value, edge) == score
    assert band_at_session_start(score, value) is band


def test_a_first_session_has_no_band() -> None:
    assert band_at_session_start(1000, None) is None
    assert band_at_session_start(-1000, None) is None


@pytest.mark.parametrize(
    "sittings",
    [
        pytest.param(([1, 2, 3, 4, 5], [6, 7, 8, 9]), id="nine runs in two sessions"),
        pytest.param((list(range(1, 16)),), id="one session of fifteen"),
        pytest.param((list(range(1, 20)),), id="one session of nineteen"),
    ],
)
def test_an_unknown_typical_score_gives_no_band_high_or_low(sittings) -> None:
    """Unknown is not weak, so not even a score far below every run is banded."""
    value, _ = _value_at_next_session(*sittings)

    assert value is not None
    assert not value.known
    assert band_at_session_start(1000, value) is None
    assert band_at_session_start(-1000, value) is None


def test_an_old_window_still_gives_a_band() -> None:
    """A known window counts at any age. Marking it as not recent is the caller's."""
    value, session = _value_at_next_session(list(range(1, 21)), gap_days=100)

    assert value is not None
    assert not typical_score_recency(value, session.start).recent
    assert band_at_session_start(25, value) is RunBand.TOP_10
    assert band_at_session_start(0, value) is RunBand.BOTTOM_10


def test_a_new_pb_is_always_in_the_top_band() -> None:
    """A new PB beats every run in its window, so it is above the window's P90."""
    rng = random.Random(471)
    for _ in range(300):
        size = rng.randint(10, 20)
        if rng.random() < 0.5:
            scores = [float(rng.randint(90, 110)) for _ in range(size)]
            step = 1.0
        else:
            scores = [rng.randint(150, 260) / 100 for _ in range(size)]
            step = 0.01
        split = rng.randint(1, size - 1)
        value, _ = _value_at_next_session(scores[:split], scores[split:])
        new_pb = round(max(scores) + step, 2)

        assert band_at_session_start(new_pb, value) is RunBand.TOP_10, scores
