from dataclasses import replace
from datetime import datetime, timedelta
from itertools import permutations

import pytest

from source.kovaaks.data_models import RunData
from source.kovaaks.play_sessions import in_play_order, split_into_play_sessions
from source.kovaaks.typical_score import (
    build_typical_scores,
    format_typical_score,
    typical_score_fade_time,
    typical_score_recency,
)

START = datetime(2026, 5, 1, 10)


def _run(end: datetime, score: float = 100, **fields) -> RunData:
    return RunData(
        datetime_object=end,
        score=score,
        scenario="1w4ts",
        sens_scale="cm/360",
        horizontal_sens=40,
        accuracy=0.5,
        run_start=end - timedelta(seconds=60),
        run_length=timedelta(seconds=60),
        **fields,
    )


def _sitting(count: int, start: datetime = START) -> list[RunData]:
    return [
        _run(start + timedelta(minutes=index * 2), score=index + 1)
        for index in range(count)
    ]


def _values(runs: list[RunData]):
    return build_typical_scores(runs, split_into_play_sessions(runs))


@pytest.mark.parametrize(
    ("first_count", "second_count", "known"),
    [
        (9, 0, False),
        (10, 0, False),
        (5, 4, False),
        (5, 5, True),
        (19, 0, False),
        (20, 0, True),
    ],
)
def test_existence_minimums(first_count, second_count, known) -> None:
    runs = _sitting(first_count) + _sitting(second_count, START + timedelta(days=1))

    value = _values(runs)[-1]

    assert value.known is known
    assert value.run_count == first_count + second_count
    assert value.session_count == (2 if second_count else 1)
    assert value.first_date == runs[0].datetime_object
    assert value.last_date == runs[-1].datetime_object
    if not known:
        assert (value.median, value.p25, value.p75, value.p10, value.p90) == (
            None,
            None,
            None,
            None,
            None,
        )


def test_no_runs_has_no_values() -> None:
    assert build_typical_scores([], []) == []


def test_value_after_each_run_uses_all_runs_below_twenty_at_any_age() -> None:
    runs = [_run(START + timedelta(days=index * 40), index + 1) for index in range(19)]

    values = _values(runs)

    assert len(values) == len(runs)
    assert [value.known for value in values] == [False] * 9 + [True] * 10
    for index, value in enumerate(values, start=1):
        assert value.runs == tuple(runs[:index])
        assert value.run_count == value.session_count == index
        if value.known:
            assert value.median == (index + 1) / 2
    assert not typical_score_recency(values[-1], runs[-1].datetime_object).recent


def test_twenty_run_window_drops_only_the_oldest_run() -> None:
    runs = [_run(START + timedelta(days=index * 40), index + 1) for index in range(25)]

    values = _values(runs)

    assert values[19].median == 10.5
    assert values[20].median == 11.5
    assert values[-1].median == 15.5
    assert values[-1].runs == tuple(runs[-20:])
    assert values[-1].run_count == values[-1].session_count == 20
    assert values[-1].first_date == runs[-20].datetime_object
    assert values[-1].last_date == runs[-1].datetime_object


def test_known_stays_known_when_a_long_sitting_replaces_every_earlier_run() -> None:
    runs = _sitting(5) + _sitting(30, START + timedelta(days=100))

    values = _values(runs)

    assert not values[8].known
    assert all(value.known for value in values[9:])
    assert values[-1].session_count == 1
    assert values[-1].run_count == 20


@pytest.mark.parametrize(
    ("count", "median", "p25", "p75", "p10", "p90"),
    [
        (10, 5.5, 3.25, 7.75, 1.9, 9.1),
        (11, 6, 3.5, 8.5, 2, 10),
        (20, 10.5, 5.75, 15.25, 2.9, 18.1),
    ],
)
def test_median_and_inclusive_percentiles_against_hand_worked_values(
    count, median, p25, p75, p10, p90
) -> None:
    # Scores are 1..count; an inclusive percentile's zero-based position is
    # (count - 1) * p, so it interpolates between those adjacent scores.
    runs = [
        _run(START + timedelta(days=index), score=index + 1) for index in range(count)
    ]

    value = _values(runs)[-1]

    assert (value.median, value.p25, value.p75, value.p10, value.p90) == pytest.approx(
        (median, p25, p75, p10, p90)
    )


def test_percentiles_sort_by_score_while_the_window_keeps_play_order() -> None:
    scores = [100, 0, 40, 10, 90, 20, 80, 30, 70, 60]
    runs = [
        _run(START + timedelta(days=index), score) for index, score in enumerate(scores)
    ]

    value = _values(runs)[-1]

    assert value.runs == tuple(runs)
    assert (value.median, value.p25, value.p75, value.p10, value.p90) == pytest.approx(
        (50, 22.5, 77.5, 9, 91)
    )


def test_other_scenarios_join_target_runs_into_one_play_session() -> None:
    target = _sitting(5) + _sitting(5, START + timedelta(hours=1))
    bridge = replace(_run(START + timedelta(minutes=35)), scenario="another")
    all_runs = target + [bridge]

    value = build_typical_scores(target, split_into_play_sessions(all_runs))[-1]

    assert len(split_into_play_sessions(target)) == 2
    assert value.run_count == 10
    assert value.session_count == 1
    assert not value.known
    assert bridge not in value.runs


def test_every_sensitivity_version_and_warm_up_counts() -> None:
    runs = [
        replace(
            _run(START + timedelta(days=index), score=index * 10),
            horizontal_sens=20 + index,
            sens_scale="cm/360" if index % 2 else "some scale",
            scenario_hash=(None, "old", "new")[index % 3],
        )
        for index in range(10)
    ]

    value = _values(runs)[-1]

    assert value.known
    assert value.runs == tuple(runs)
    assert value.median == 45
    assert value.session_count == 10


def test_same_second_runs_follow_session_play_order_in_every_input_order() -> None:
    earlier = _sitting(19, START - timedelta(days=1))
    first = replace(_run(START, 100), run_start=START - timedelta(minutes=2))
    second = _run(START, 200, stats_file_name="a.csv")
    third = _run(START, 300, stats_file_name="z.csv")
    expected = in_play_order(earlier + [first, second, third])

    for tied_runs in permutations([first, second, third]):
        handed_over = list(reversed(earlier)) + list(tied_runs)
        sessions = split_into_play_sessions(handed_over)

        values = build_typical_scores(handed_over, sessions)

        assert [value.runs[-1] for value in values] == expected
        assert values[-3].runs == tuple(expected[-22:-2])
        assert values[-2].runs == tuple(expected[-21:-1])
        assert values[-1].runs == tuple(expected[-20:])
        assert values[-3].median == 10.5
        assert values[-2].median == 11.5
        assert values[-1].median == 12.5


def test_builder_consumes_iterables_without_changing_inputs() -> None:
    runs = _sitting(20)
    sessions = split_into_play_sessions(runs)
    before = list(runs)

    values = build_typical_scores(iter(runs), iter(sessions))

    assert values[-1].runs == tuple(runs)
    assert runs == before
    assert sessions == split_into_play_sessions(before)


def test_a_run_missing_from_the_session_snapshot_is_rejected() -> None:
    runs = _sitting(20)

    with pytest.raises(ValueError, match="same run snapshot"):
        build_typical_scores(runs, split_into_play_sessions(runs[:-1]))


@pytest.mark.parametrize("recent_count", [0, 1, 9, 10, 14, 20])
def test_recency_counts_every_supporting_run_and_its_sessions(recent_count) -> None:
    old_count = 20 - recent_count
    runs = _sitting(old_count) + _sitting(recent_count, START + timedelta(days=100))
    now = START + timedelta(days=100, hours=1)
    value = _values(runs)[-1]

    recency = typical_score_recency(value, now)

    assert value.known
    assert recency.recent is (recent_count >= 10)
    assert recency.run_count == recent_count
    assert recency.session_count == (1 if recent_count else 0)


def test_ten_recent_runs_can_span_two_sessions() -> None:
    runs = _sitting(5) + _sitting(5, START + timedelta(days=1))
    value = _values(runs)[-1]

    recency = typical_score_recency(value, runs[-1].datetime_object)

    assert recency.recent
    assert recency.run_count == 10
    assert recency.session_count == 2


def test_known_below_twenty_needs_no_recent_session_minimum() -> None:
    runs = _sitting(1) + _sitting(10, START + timedelta(days=100))
    value = _values(runs)[-1]

    recency = typical_score_recency(value, runs[-1].datetime_object)

    assert value.known
    assert value.session_count == 2
    assert recency.recent
    assert recency.run_count == 10
    assert recency.session_count == 1


def test_unknown_value_does_not_become_recent_with_ten_runs_in_one_session() -> None:
    runs = _sitting(10)
    value = _values(runs)[-1]

    recency = typical_score_recency(value, runs[-1].datetime_object)

    assert not value.known
    assert not recency.recent
    assert recency.run_count == 10
    assert recency.session_count == 1
    assert typical_score_fade_time(value) is None


@pytest.mark.parametrize(
    ("after_boundary", "recent_count", "recent"),
    [
        (timedelta(seconds=-1), 10, True),
        (timedelta(0), 10, True),
        (timedelta(microseconds=1), 9, False),
        (timedelta(seconds=1), 9, False),
    ],
)
def test_thirty_day_boundary_is_inclusive(after_boundary, recent_count, recent) -> None:
    runs = [_run(START + timedelta(days=index), index) for index in range(20)]
    value = _values(runs)[-1]
    fade_time = START + timedelta(days=40)

    recency = typical_score_recency(value, fade_time + after_boundary)

    assert typical_score_fade_time(value) == fade_time
    assert recency.run_count == recent_count
    assert recency.recent is recent


def test_future_runs_are_not_counted_at_an_earlier_moment() -> None:
    runs = [_run(START + timedelta(days=index), index) for index in range(20)]
    value = _values(runs)[-1]

    recency = typical_score_recency(value, START + timedelta(days=8))

    assert recency.run_count == recency.session_count == 9
    assert not recency.recent


def test_fade_is_tenth_newest_run_plus_thirty_days_even_with_tied_dates() -> None:
    runs = [_run(START + timedelta(days=index), index) for index in range(10)]
    runs += [
        _run(START + timedelta(days=25), 100, stats_file_name=f"{index}.csv")
        for index in range(10)
    ]
    value = _values(runs)[-1]
    boundary = START + timedelta(days=55)

    assert typical_score_fade_time(value) == boundary
    assert typical_score_recency(value, boundary).run_count == 10
    assert typical_score_recency(value, boundary).recent
    assert typical_score_recency(value, boundary + timedelta(seconds=1)).run_count == 0
    assert not typical_score_recency(value, boundary + timedelta(seconds=1)).recent


def test_chart_value_can_be_recent_at_run_but_card_not_a_day_later() -> None:
    runs = [_run(START + timedelta(days=index), index) for index in range(11)]
    runs += _sitting(9, START + timedelta(days=39))
    value = _values(runs)[-1]
    at_run = value.last_date

    assert value.known
    assert typical_score_recency(value, at_run).recent
    assert typical_score_recency(value, at_run).run_count == 10
    assert typical_score_fade_time(value) == START + timedelta(days=40)
    assert not typical_score_recency(value, at_run + timedelta(days=1)).recent


@pytest.mark.parametrize(
    ("scores", "shown", "expected"),
    [
        ([2140.0, 2141.0], 2140.5, "2,141"),
        ([1.2, 1.3], 1.25, "1.3"),
        ([2.14, 2.15], 2.145, "2.15"),
        ([2.123456, 2.166544], 2.145, "2.15"),
        ([100.0, 100.0], 100.0, "100"),
        ([0.000001, 0.000002], 0.0000015, "0"),
        ([10.0, 10.01], 10.005, "10.01"),
        ([1.2, 1.8], 1.5, "1.5"),
        ([1.0, 2.0], 1.9, "2"),
    ],
)
def test_display_precision_comes_from_runs_and_half_rounds_up(scores, shown, expected):
    runs = [
        _run(START + timedelta(days=index), score) for index, score in enumerate(scores)
    ]

    assert format_typical_score(shown, iter(runs)) == expected


def test_rounding_keeps_the_definition_exact_and_uses_only_the_current_window() -> None:
    runs = [_run(START, 1.123456)] + [
        _run(START + timedelta(days=index + 1), 2140 + index % 2) for index in range(20)
    ]
    values = _values(runs)
    previous = values[-2]
    current = values[-1]

    assert current.median == 2140.5
    assert format_typical_score(current.median, current.runs) == "2,141"
    assert current.median == 2140.5
    assert previous.p25 is not None
    assert format_typical_score(previous.p25, previous.runs) == "2,140"


def test_rounding_without_supporting_runs_is_rejected() -> None:
    with pytest.raises(ValueError, match="supporting runs"):
        format_typical_score(1.25, [])


@pytest.mark.parametrize(
    ("low", "high", "expected"),
    [(2.3, 2.4, "2.4"), (2.14, 2.15, "2.15"), (2140, 2141, "2,141")],
)
def test_calculated_medians_keep_decimal_halves_for_display(
    low, high, expected
) -> None:
    runs = [
        _run(START + timedelta(days=index), score)
        for index, score in enumerate([low] * 5 + [high] * 5)
    ]
    value = _values(runs)[-1]

    assert value.median is not None
    assert format_typical_score(value.median, value.runs) == expected


def test_calculated_quartile_keeps_its_decimal_half_for_display() -> None:
    scores = [2.1, 2.2, 2.3, 2.5, 2.6, 2.7, 2.8, 2.9, 3.0, 3.1]
    runs = [
        _run(START + timedelta(days=index), score) for index, score in enumerate(scores)
    ]
    value = _values(runs)[-1]

    assert value.p25 == 2.35
    assert format_typical_score(value.p25, value.runs) == "2.4"
