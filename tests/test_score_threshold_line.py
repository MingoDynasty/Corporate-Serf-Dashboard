"""Where the chart draws the score threshold line on a time-scored scenario.

The Run History chart callback asks ``score_threshold_line`` for the line's
height and labels the line with it. These tests drive that callback with the
figure builder stood in for, so what they hold is the height: 95% of the
personal best's pace where pace can be measured, and 95% of its score
everywhere else. The same answers from real files on disk are
``tests/test_time_scored_surfaces.py``.
"""

import json
from datetime import datetime

import dash
import plotly.graph_objects as go

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.components import score_threshold  # noqa: E402
from source.kovaaks.data_models import RunData  # noqa: E402
from source.kovaaks.time_scored_service import PaceBasis  # noqa: E402
from source.pages import run_history  # noqa: E402

_LINE_HASH = "0123456789abcdef0123456789abcdef"


def _personal_best(score: float, scenario_hash: str) -> RunData:
    return RunData(
        datetime_object=datetime(2026, 7, 6, 12),
        score=score,
        sens_scale="cm/360",
        horizontal_sens=40.8,
        scenario="Scenario A",
        accuracy=0.5,
        scenario_hash=scenario_hash,
    )


def _threshold_line_annotation(monkeypatch, *, basis, pb_hash) -> str:
    """Draw Scenario A's threshold line at 95% and return what the chart says."""
    personal_best = _personal_best(896.2, pb_hash)
    monkeypatch.setattr(run_history, "is_scenario_in_database", lambda _scenario: True)
    monkeypatch.setattr(
        run_history,
        "build_run_history_figure",
        lambda *_args, **_switches: (go.Figure(), True),
    )
    monkeypatch.setattr(run_history, "get_high_score", lambda _scenario: 896.2)
    monkeypatch.setattr(
        score_threshold, "get_personal_best_run", lambda _scenario: personal_best
    )
    monkeypatch.setattr(score_threshold, "get_pace_basis", lambda _scenario: basis)

    plot_json = run_history.generate_graph(
        None,
        "Scenario A",
        None,
        "score_vs_run",
        "100",
        "90",
        "2026-07-06",
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        True,
        95,
    )

    plot = json.loads(plot_json)
    (annotation,) = plot["layout"]["annotations"]
    (line,) = plot["layout"]["shapes"]
    # The label is the line's own height, rounded for display.
    assert annotation["text"] == f"Score threshold ({line['y0']:.2f})"
    return annotation["text"]


def test_the_threshold_line_on_a_time_scored_scenario_sits_at_95_percent_of_pb_pace(
    monkeypatch,
):
    # 103.8 s at 95% of the pace is 109.26 s, which is a score of 890.74. The
    # annotation still names a score.
    annotation = _threshold_line_annotation(
        monkeypatch,
        basis=PaceBasis(1000.0, _LINE_HASH),
        pb_hash=_LINE_HASH,
    )

    assert annotation == "Score threshold (890.74)"


def test_the_threshold_line_with_no_constant_sits_at_95_percent_of_the_pb_score(
    monkeypatch,
):
    annotation = _threshold_line_annotation(monkeypatch, basis=None, pb_hash=_LINE_HASH)

    assert annotation == "Score threshold (851.39)"


def test_the_threshold_line_keeps_score_math_for_a_pb_from_another_version(
    monkeypatch,
):
    annotation = _threshold_line_annotation(
        monkeypatch,
        basis=PaceBasis(1000.0, _LINE_HASH),
        pb_hash="ffffffffffffffffffffffffffffffff",
    )

    assert annotation == "Score threshold (851.39)"


def test_the_threshold_line_keeps_score_math_where_pace_is_undefined(monkeypatch):
    # A PB at the constant took no time, so there is no pace to take 95% of.
    personal_best = _personal_best(1000.0, _LINE_HASH)
    monkeypatch.setattr(
        score_threshold, "get_personal_best_run", lambda _scenario: personal_best
    )
    monkeypatch.setattr(
        score_threshold,
        "get_pace_basis",
        lambda _scenario: PaceBasis(1000.0, _LINE_HASH),
    )

    assert score_threshold.score_threshold_line("Scenario A", 1000.0, 95.0) == 950.0
