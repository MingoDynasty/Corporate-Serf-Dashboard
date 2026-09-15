"""Home says so, and lists no scenarios, when no stats directory is pinned.

The hint speaks for a ``stats_dir`` key that exists and cannot be used. A key
that was never written is the setup card's case (``test_home_setup_card.py``),
so the two surfaces never explain the same condition twice.
"""

import dash
import dash_mantine_components as dmc
import pytest

from source.config import settings_service

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.pages import home  # noqa: E402

HINT_TEXT = "No stats folder configured. Set it in "
RESTART_HINT_TEXT = "Restart the app to apply your saved settings."
# Spelled out rather than imported: the caution modifier is what makes the
# panel yellow, so a constant that lost it must fail here.
HINT_CLASS = "alert-panel alert-panel-caution stats-dir-hint"


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


def _hint_sentence(hint):
    """Return the hint's sentence children after checking the panel around them.

    Every branch wears the same caution panel: the warning icon beside the
    sentence, no title above it.
    """
    assert isinstance(hint, dmc.Paper)
    assert hint.className == HINT_CLASS
    group = hint.children
    assert isinstance(group, dmc.Group)
    # Invisible to every other assertion: without it a sentence wider than the
    # space beside the icon drops whole onto the row under the icon.
    assert group.wrap == "nowrap"
    icon, text = group.children
    assert icon.className == "alert-panel-icon"
    assert "material-symbols-warning-outline.svg" in icon.style["mask"]
    assert isinstance(text, dmc.Text)
    return text.children


@pytest.fixture(autouse=True)
def quiet_playlists(monkeypatch):
    monkeypatch.setattr(home, "get_visible_playlist_selector_options", lambda: [])


def test_hint_is_absent_while_the_pinned_directory_is_usable(monkeypatch):
    """The autouse fixtures pin the fixture stats folder, as startup would."""
    monkeypatch.setattr(home, "get_scenario_names", lambda: ["All"])

    page = home.layout()

    assert _component_by_id(page, "stats-dir-hint") is None
    assert _component_by_id(page, "scenario-dropdown-selection").data == ["All"]


@pytest.mark.parametrize("stored", ["", "no-such-stats-dir"])
def test_hint_replaces_the_scenario_list_without_a_usable_directory(
    monkeypatch,
    stored,
):
    settings_service.save_settings({settings_service.STATS_DIR_KEY: stored})
    settings_service.resolve_stats_dir()
    monkeypatch.setattr(
        home,
        "get_scenario_names",
        lambda: pytest.fail("listed scenarios without a usable stats directory"),
    )

    page = home.layout()

    hint = _component_by_id(page, "stats-dir-hint")
    assert hint is not None
    text, link, period = _hint_sentence(hint)
    assert text == HINT_TEXT
    # The repair surface exists now, so the hint points straight at it.
    assert isinstance(link, dmc.Anchor)
    assert link.children == "Settings"
    assert link.href == "/settings"
    # Its own child, so the period does not render underlined inside the link.
    assert period == "."
    assert _component_by_id(page, "scenario-dropdown-selection").data == []


def test_hint_cedes_the_never_configured_case_to_the_setup_card(monkeypatch):
    """One condition, one surface: an absent key has never been asked about."""
    settings_service.save_settings({})
    settings_service.resolve_stats_dir()
    monkeypatch.setattr(
        home,
        "get_scenario_names",
        lambda: pytest.fail("listed scenarios without a usable stats directory"),
    )

    page = home.layout()

    assert _component_by_id(page, "stats-dir-hint") is None
    assert _component_by_id(page, home.SETUP_CARD_ID).children != []
    assert _component_by_id(page, "scenario-dropdown-selection").data == []


def test_hint_defers_to_the_restart_after_a_post_boot_save(monkeypatch, tmp_path):
    """A saved-but-unapplied directory must not read as "not configured"."""
    settings_service.save_settings({})
    settings_service.resolve_stats_dir()
    settings_service.save_settings({settings_service.STATS_DIR_KEY: str(tmp_path)})
    monkeypatch.setattr(
        home,
        "get_scenario_names",
        lambda: pytest.fail("listed scenarios without a usable stats directory"),
    )

    page = home.layout()

    hint = _component_by_id(page, "stats-dir-hint")
    assert hint is not None
    # Yellow like the unconfigured branch: nothing plots until the restart.
    assert _hint_sentence(hint) == RESTART_HINT_TEXT


def test_hint_keeps_its_link_when_only_the_identity_changed(monkeypatch):
    """A restart cannot repair a directory whose stored path does not exist."""
    settings_service.save_settings(
        {
            settings_service.STATS_DIR_KEY: "no-such-stats-dir",
            settings_service.KOVAAKS_USERNAME_KEY: "First",
        }
    )
    settings_service.resolve_stats_dir()
    # Freeze the identity pin, as a boot-time consumer would.
    settings_service.get_identity()
    settings_service.save_settings(
        {
            settings_service.STATS_DIR_KEY: "no-such-stats-dir",
            settings_service.KOVAAKS_USERNAME_KEY: "Second",
        }
    )
    assert settings_service.is_restart_pending() is True
    assert settings_service.is_stats_dir_change_pending() is False
    monkeypatch.setattr(
        home,
        "get_scenario_names",
        lambda: pytest.fail("listed scenarios without a usable stats directory"),
    )

    page = home.layout()

    hint = _component_by_id(page, "stats-dir-hint")
    assert hint is not None
    text, link, period = _hint_sentence(hint)
    assert text == HINT_TEXT
    assert isinstance(link, dmc.Anchor)
    assert period == "."


def test_hint_keeps_its_link_when_the_directory_was_cleared(monkeypatch):
    """A restart cannot apply a directory the user just emptied."""
    settings_service.save_settings(
        {settings_service.STATS_DIR_KEY: "no-such-stats-dir"}
    )
    settings_service.resolve_stats_dir()
    settings_service.save_settings({settings_service.STATS_DIR_KEY: ""})
    assert settings_service.is_stats_dir_change_pending() is True
    monkeypatch.setattr(
        home,
        "get_scenario_names",
        lambda: pytest.fail("listed scenarios without a usable stats directory"),
    )

    page = home.layout()

    hint = _component_by_id(page, "stats-dir-hint")
    assert hint is not None
    text, link, period = _hint_sentence(hint)
    assert text == HINT_TEXT
    assert isinstance(link, dmc.Anchor)
    assert period == "."


def test_hint_stacks_above_the_account_offer_when_a_detected_folder_vanished(
    monkeypatch,
):
    """Both surfaces speak, each for its own key, and the blocker comes first.

    Startup detection writes only ``stats_dir``, so a detected folder that is
    later removed leaves a present-but-unusable path beside a username key that
    was never written: the hint's case and the account offer's case at once.
    """
    settings_service.save_settings(
        {settings_service.STATS_DIR_KEY: "no-such-stats-dir"}
    )
    settings_service.resolve_stats_dir()
    monkeypatch.setattr(
        home,
        "get_scenario_names",
        lambda: pytest.fail("listed scenarios without a usable stats directory"),
    )

    page = home.layout()

    hint = _component_by_id(page, "stats-dir-hint")
    assert hint is not None
    text, link, period = _hint_sentence(hint)
    assert text == HINT_TEXT
    assert isinstance(link, dmc.Anchor)
    assert period == "."
    card_box = _component_by_id(page, home.SETUP_CARD_ID)
    (card,) = card_box.children
    # The blue account offer, not a second stats-folder surface.
    assert card.className == home.SETUP_CARD_CLASS
    order = [id(component) for component in _walk_components(page)]
    assert order.index(id(hint)) < order.index(id(card_box))


def test_select_playlist_lists_nothing_without_a_usable_directory(monkeypatch):
    settings_service.save_settings({})
    settings_service.resolve_stats_dir()
    monkeypatch.setattr(
        home,
        "get_scenario_names",
        lambda: pytest.fail("listed scenarios without a usable stats directory"),
    )

    assert home.select_playlist(None) == []
