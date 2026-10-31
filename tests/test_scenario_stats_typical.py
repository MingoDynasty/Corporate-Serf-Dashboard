"""Hold the Scenario Stats lead to its copy, snapshot and ticking contracts."""

import json
from datetime import datetime, timedelta

import dash_mantine_components as dmc
import pytest
from dash import html, no_update
from plotly.io.json import to_json_plotly

from source.components import run_history_chart, scenario_stats
from source.kovaaks.data_models import RunData
from source.kovaaks.play_sessions import split_into_play_sessions
from source.kovaaks.typical_score import build_typical_scores, format_typical_score

NOW = datetime(2026, 10, 21, 12)


def _run(end, score=100, scenario="Test"):
    return RunData(
        datetime_object=end,
        score=score,
        scenario=scenario,
        sens_scale="cm/360",
        horizontal_sens=40,
        accuracy=0.5,
        run_start=end - timedelta(seconds=60),
        run_length=timedelta(seconds=60),
    )


def _sitting(count, start=NOW - timedelta(days=1)):
    return [_run(start + timedelta(minutes=i * 2), i + 100) for i in range(count)]


def _text(component):
    if isinstance(component, (list, tuple)):
        return "".join(_text(child) for child in component)
    if isinstance(component, str):
        return component
    return _text(getattr(component, "children", []))


def _json(component):
    return json.loads(to_json_plotly(component))


@pytest.fixture
def store(monkeypatch):
    runs = []
    clock = [NOW]

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return clock[0]

    monkeypatch.setattr(scenario_stats, "datetime", Clock)
    monkeypatch.setattr(scenario_stats, "get_all_runs", lambda: list(runs))
    return runs, clock


def test_empty_selection_does_not_read_runs(monkeypatch):
    monkeypatch.setattr(
        scenario_stats, "get_all_runs", lambda: pytest.fail("no selection")
    )
    assert scenario_stats.get_scenario_typical_score(None, None, 0) == ([], "", True)


def test_no_local_runs_and_too_few_runs(store):
    runs, _clock = store
    lead, readout, hidden = scenario_stats.get_scenario_typical_score(None, "Test", 0)
    assert _text(lead) == "No runs yet"
    assert (readout, hidden) == ("", False)
    runs.extend(_sitting(18))
    lead, readout, hidden = scenario_stats.get_scenario_typical_score(None, "Test", 1)
    assert _text(lead).strip() == "Too few runs"
    assert lead.label == (
        "A typical score needs 10 runs across 2 or more sessions, or 20 in one "
        "session. You have 18 runs in 1 session."
    )
    assert (readout, hidden) == ("", False)


@pytest.mark.parametrize(
    ("n", "sessions", "expected"),
    [(1, 1, "1 run in 1 session"), (2, 2, "2 runs in 2 sessions")],
)
def test_too_few_hover_pluralizes_its_counts(store, n, sessions, expected):
    runs, _ = store
    runs.extend(_run(NOW - timedelta(days=i + 1)) for i in range(n))
    lead, _, _ = scenario_stats.get_scenario_typical_score(None, "Test", 0)
    assert lead.label.endswith(f"You have {expected}.")


@pytest.mark.parametrize(
    ("recent_count", "dimmed"),
    [(20, False), (19, False), (14, False), (10, False), (9, True), (0, True)],
)
def test_first_line_and_dimming_show_the_actual_mixture(store, recent_count, dimmed):
    runs, _ = store
    runs.extend(_sitting(20 - recent_count, NOW - timedelta(days=60)))
    runs.extend(_sitting(recent_count))
    lead, readout, hidden = scenario_stats.get_scenario_typical_score(None, "Test", 0)
    assert (scenario_stats.DIMMED_CLASS in lead.children.className) is dimmed
    assert readout == (
        "" if recent_count == 20 else f" · {recent_count} of 20 recent runs"
    )
    assert hidden is False
    assert f"Recent: {recent_count} of 20 from the last 30 days" in _text(lead.label)


def test_tick_fades_at_the_inclusive_boundary_and_unchanged_ticks_keep_the_tooltip(
    store,
):
    runs, clock = store
    runs.extend(_sitting(10, NOW - timedelta(days=60)))
    runs.append(_run(NOW - timedelta(days=30)))
    runs.extend(_sitting(9))
    lead, readout, hidden = scenario_stats.get_scenario_typical_score(None, "Test", 0)
    assert "scenario-stats-dimmed" not in lead.children.className
    assert readout == " · 10 of 20 recent runs"
    assert scenario_stats.get_scenario_typical_score(
        None, "Test", 1, _json(lead), readout
    ) == (no_update, no_update, hidden)
    clock[0] += timedelta(seconds=1)
    faded, changed, _ = scenario_stats.get_scenario_typical_score(
        None, "Test", 2, _json(lead), readout
    )
    assert "scenario-stats-dimmed" in faded.children.className
    assert changed == " · 9 of 20 recent runs"
    assert scenario_stats.get_scenario_typical_score(
        None, "Test", 3, _json(faded), changed
    )[:2] == (no_update, no_update)


def test_a_landing_run_and_a_scenario_change_update_the_lead(store):
    runs, _ = store
    runs.extend(_sitting(19))
    before, readout, _ = scenario_stats.get_scenario_typical_score(None, "Test", 0)
    runs.append(_run(NOW, score=200))
    after, _, _ = scenario_stats.get_scenario_typical_score(
        {"new_runs": 1}, "Test", 0, _json(before), readout
    )
    assert _text(after).strip() == "110"
    switched, _, _ = scenario_stats.get_scenario_typical_score(
        None, "Unplayed", 0, _json(after), ""
    )
    assert _text(switched) == "No runs yet"


def test_one_whole_store_snapshot_includes_other_scenarios_session_bridges(
    store, monkeypatch
):
    runs, _ = store
    runs.extend(_sitting(5, NOW - timedelta(hours=3)))
    runs.extend(_sitting(5, NOW - timedelta(hours=2)))
    known, _, _ = scenario_stats.get_scenario_typical_score(None, "Test", 0)
    assert _text(known).strip() != "Too few runs"
    runs.extend(
        _run(NOW - timedelta(hours=3) + timedelta(minutes=i), scenario="Bridge")
        for i in (25, 45)
    )
    calls = []

    def snapshot():
        calls.append(True)
        assert len(calls) == 1
        return list(runs)

    monkeypatch.setattr(scenario_stats, "get_all_runs", snapshot)
    unknown, _, _ = scenario_stats.get_scenario_typical_score(None, "Test", 0)
    assert _text(unknown).strip() == "Too few runs"
    assert unknown.label.endswith("You have 10 runs in 1 session.")


@pytest.mark.parametrize("count", [10, 20, 21])
def test_value_matches_the_chart_last_point_and_rounding(store, monkeypatch, count):
    runs, _ = store
    runs.extend(
        _run(NOW - timedelta(days=i + 1), score=2140 + i % 2) for i in range(count)
    )
    monkeypatch.setattr(run_history_chart, "get_all_runs", lambda: list(runs))
    figure, _ = run_history_chart.build_run_history_figure(
        run_history_chart.SCORE_VS_RUN,
        "Test",
        "all",
        "all",
        False,
        False,
        None,
        NOW.date(),
        typical_score_switch=True,
        middle_50_switch=True,
        middle_80_switch=True,
        accuracy_targets_switch=False,
    )
    line = next(trace for trace in figure.data if trace.name == "Typical score")
    value = build_typical_scores(runs, split_into_play_sessions(runs))[-1]
    lead, _, _ = scenario_stats.get_scenario_typical_score(None, "Test", 0)
    assert line.y[-1] == value.median
    assert _text(lead).strip() == format_typical_score(line.y[-1], value.runs)
    assert _text(lead.label).startswith(
        f"The median of your {'last ' if count > 20 else ''}{min(count, 20)} runs."
    )
    assert all(label in _text(lead.label) for label in ("Middle 50%:", "Middle 80%:"))
    assert all(isinstance(row.children[0], html.B) for row in lead.label.children[1:])


@pytest.mark.parametrize("year", [2025, 2026])
def test_hover_dates_use_one_date_and_only_show_another_year(store, year):
    runs, _ = store
    runs.extend(_sitting(20, datetime(year, 5, 1, 10)))
    lead, _, _ = scenario_stats.get_scenario_typical_score(None, "Test", 0)
    assert (
        _text(lead.label.children[1])
        == f"Runs: 20 in 1 session · on May 1{', 2025' if year == 2025 else ''}"
    )


def test_hover_date_span_and_small_window_count(store):
    runs, _ = store
    runs.extend(_sitting(5, datetime(2025, 12, 31, 10)))
    runs.extend(_sitting(5, datetime(2026, 1, 1, 10)))
    lead, readout, _ = scenario_stats.get_scenario_typical_score(None, "Test", 0)
    assert readout == " · 0 of 10 recent runs"
    assert (
        _text(lead.label.children[1])
        == "Runs: 10 in 2 sessions · Dec 31, 2025 to Jan 1"
    )


def test_help_copy_accessible_name_and_focus():
    ids = scenario_stats.ScenarioStatsIds(
        *(f"test-{f}" for f in scenario_stats.ScenarioStatsIds._fields)
    )
    help_tip = scenario_stats.scenario_stats_panel(ids).children[0].children[1]
    assert isinstance(help_tip, dmc.Tooltip)
    assert getattr(help_tip.children, "aria-label") == "About the typical score"
    assert help_tip.events == {"hover": True, "focus": True, "touch": True}
    assert [_text(p) for p in help_tip.label.children] == [
        (
            "Your typical score is the median of your last 20 runs of this scenario, or of "
            "all your runs if you have fewer. Runs count regardless of age."
        ),
        (
            "On the chart, the darker band shows the middle 50% of those scores, and the "
            "lighter band the middle 80%. Narrower bands mean more consistent scores. Turn "
            "the line and bands on or off in Chart options."
        ),
        (
            "A faded line, or a dimmed number on this card, means fewer than 10 of the runs "
            "behind your typical score are from the last 30 days, so it may be out of date."
        ),
        "The card shows how recent it is today, and the chart how recent it was at each run.",
    ]
