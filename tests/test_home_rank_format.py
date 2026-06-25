import dash

from source.kovaaks.api_models import ScenarioRankInfo, ScenarioRankStatus

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.pages import home  # noqa: E402

format_scenario_rank = home.format_scenario_rank


def _find_component_by_id(component, component_id):
    if getattr(component, "id", None) == component_id:
        return component

    children = getattr(component, "children", None)
    if children is None:
        return None
    if not isinstance(children, list | tuple):
        children = [children]

    for child in children:
        match = _find_component_by_id(child, component_id)
        if match is not None:
            return match

    return None


def test_home_playlist_filter_dropdown_scrollbar_is_always_visible(monkeypatch):
    monkeypatch.setattr(home, "get_playlists", lambda: ["Voltaic Benchmarks"])
    monkeypatch.setattr(home, "get_unique_scenarios", lambda *_args: ["1wall6targets"])

    playlist_filter = _find_component_by_id(
        home.layout(),
        "playlist-dropdown-selection",
    )

    assert playlist_filter.scrollAreaProps == {"type": "always"}


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
