"""Home says so, and lists no scenarios, when no stats directory is pinned."""

import dash
import dash_mantine_components as dmc
import pytest

from source.config import settings_service

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.pages import home  # noqa: E402

HINT_TEXT = "No stats directory configured — set it in "
RESTART_HINT_TEXT = "Settings saved — restart the dashboard to apply them."


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


def _component_by_id(page, component_id):
    return next(
        (
            component
            for component in _walk_components(page)
            if getattr(component, "id", None) == component_id
        ),
        None,
    )


@pytest.fixture(autouse=True)
def quiet_playlists(monkeypatch):
    monkeypatch.setattr(home, "get_visible_playlist_selector_options", lambda: [])


def test_hint_is_absent_while_the_pinned_directory_is_usable(monkeypatch):
    """The autouse fixtures pin the fixture stats folder, as startup would."""
    monkeypatch.setattr(home, "get_unique_scenarios", lambda _stats_dir: ["All"])

    page = home.layout()

    assert _component_by_id(page, "stats-dir-hint") is None
    assert _component_by_id(page, "scenario-dropdown-selection").data == ["All"]


@pytest.mark.parametrize("stored", [None, "", "no-such-stats-dir"])
def test_hint_replaces_the_scenario_list_without_a_usable_directory(
    monkeypatch,
    stored,
):
    settings_service.save_settings(
        {} if stored is None else {settings_service.STATS_DIR_KEY: stored}
    )
    settings_service.resolve_stats_dir()
    monkeypatch.setattr(
        home,
        "get_unique_scenarios",
        lambda _stats_dir: pytest.fail("scanned a directory the app cannot use"),
    )

    page = home.layout()

    hint = _component_by_id(page, "stats-dir-hint")
    assert hint is not None
    text, link = hint.children
    assert text == HINT_TEXT
    # The repair surface exists now, so the hint points straight at it.
    assert isinstance(link, dmc.Anchor)
    assert link.children == "Settings"
    assert link.href == "/settings"
    assert _component_by_id(page, "scenario-dropdown-selection").data == []


def test_hint_defers_to_the_restart_after_a_post_boot_save(monkeypatch, tmp_path):
    """A saved-but-unapplied directory must not read as "not configured"."""
    settings_service.save_settings({})
    settings_service.resolve_stats_dir()
    settings_service.save_settings({settings_service.STATS_DIR_KEY: str(tmp_path)})
    monkeypatch.setattr(
        home,
        "get_unique_scenarios",
        lambda _stats_dir: pytest.fail("scanned a directory the app cannot use"),
    )

    page = home.layout()

    hint = _component_by_id(page, "stats-dir-hint")
    assert hint is not None
    assert hint.children == RESTART_HINT_TEXT


def test_select_playlist_lists_nothing_without_a_usable_directory(monkeypatch):
    settings_service.save_settings({})
    settings_service.resolve_stats_dir()
    monkeypatch.setattr(
        home,
        "get_unique_scenarios",
        lambda _stats_dir: pytest.fail("scanned a directory the app cannot use"),
    )

    assert home.select_playlist(None) == []
