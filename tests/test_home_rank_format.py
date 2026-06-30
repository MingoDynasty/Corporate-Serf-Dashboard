import dash
from dash import dcc

from source.kovaaks.api_models import ScenarioRankInfo, ScenarioRankStatus

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.pages import home  # noqa: E402

format_scenario_rank = home.format_scenario_rank


def _walk_components(component):
    yield component
    children = getattr(component, "children", None)
    if children is None:
        return
    if isinstance(children, (list, tuple)):
        for child in children:
            yield from _walk_components(child)
        return
    yield from _walk_components(children)


def test_format_scenario_rank_with_total_players():
    rank_info = ScenarioRankInfo(
        status=ScenarioRankStatus.RANKED,
        rank=11266,
        total_players=18342,
        percentile=38.58,
    )

    assert format_scenario_rank(rank_info) == "11,266 of 18,342 (38.58% Percentile)"


def test_format_scenario_rank_without_total_players():
    rank_info = ScenarioRankInfo(
        status=ScenarioRankStatus.RANKED,
        rank=11266,
    )

    assert format_scenario_rank(rank_info) == "11,266"


def test_format_scenario_rank_unranked_with_total_players():
    rank_info = ScenarioRankInfo(
        status=ScenarioRankStatus.UNRANKED,
        total_players=63870,
    )

    assert format_scenario_rank(rank_info) == "Unranked (63,870 ranked)"


def test_format_scenario_rank_unranked_and_unknown():
    assert (
        format_scenario_rank(ScenarioRankInfo(status=ScenarioRankStatus.UNRANKED))
        == "Unranked"
    )
    assert (
        format_scenario_rank(ScenarioRankInfo(status=ScenarioRankStatus.UNKNOWN))
        == "N/A"
    )


def test_get_scenario_rank_queries_kovaaks_for_unplayed_local_scenario(monkeypatch):
    queried_scenarios = []

    def fail_is_scenario_in_database(*_args, **_kwargs):
        raise AssertionError("rank lookup should not require local scenario data")

    def fake_get_scenario_rank_info(selected_scenario, *_args, **_kwargs):
        queried_scenarios.append(selected_scenario)
        return ScenarioRankInfo(
            status=ScenarioRankStatus.UNRANKED,
            total_players=54702,
        )

    monkeypatch.setattr(home, "is_scenario_in_database", fail_is_scenario_in_database)
    monkeypatch.setattr(home, "get_scenario_rank_info", fake_get_scenario_rank_info)

    assert home.get_scenario_rank(None, "Unplayed Scenario") == (
        "Unranked (54,702 ranked)"
    )
    assert queried_scenarios == ["Unplayed Scenario"]


def test_scenario_rank_loading_has_show_delay(monkeypatch):
    monkeypatch.setattr(home, "get_playlists", lambda: [])
    monkeypatch.setattr(home, "get_unique_scenarios", lambda _stats_dir: [])

    page = home.layout()
    rank_loading = next(
        (
            component
            for component in _walk_components(page)
            if isinstance(component, dcc.Loading)
            and getattr(component.children, "id", None) == "scenario_rank"
        ),
        None,
    )

    assert rank_loading is not None
    assert rank_loading.delay_show == home.SCENARIO_RANK_LOADING_DELAY_MS == 250
