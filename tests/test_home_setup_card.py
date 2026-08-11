"""The landing page asks once for the setup the app could not do by itself.

The card is keyed on key *absence*, so these tests spell the store out key by
key: a key that exists -- with any value -- has been asked about already and
must never bring the card back.
"""

from pathlib import Path
from types import SimpleNamespace

import dash
import dash_mantine_components as dmc
import pytest
from dash import no_update

from source.config import settings_service
from source.kovaaks import percentile_warmup_service

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.pages import home  # noqa: E402

USERNAME_KEY = settings_service.KOVAAKS_USERNAME_KEY
STATS_DIR_KEY = settings_service.STATS_DIR_KEY
STEAM_ID_KEY = settings_service.STEAM_ID_KEY


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


def _texts(component):
    return [
        child.children
        for child in _walk_components(component)
        if isinstance(child, dmc.Text)
    ]


def _button_labels(component):
    return [
        child.children
        for child in _walk_components(component)
        if isinstance(child, dmc.Button)
    ]


@pytest.fixture(autouse=True)
def quiet_home(monkeypatch):
    """Keep the rest of the page out of the way of the card."""
    monkeypatch.setattr(home, "get_visible_playlist_selector_options", lambda: [])
    monkeypatch.setattr(home, "get_unique_scenarios", lambda _stats_dir: ["All"])


@pytest.fixture
def stats_dir():
    """The fixture stats folder, the same one a real startup would pin."""
    return Path(__file__).resolve().parent / "fixtures" / "stats"


def _store(**values):
    """Save exactly these keys and pin the directory the way startup would."""
    settings_service.save_settings(values)
    settings_service.resolve_stats_dir()


def _card(page):
    """Return the rendered card, or None when the container is empty."""
    container = _component_by_id(page, home.SETUP_CARD_ID)
    assert container is not None, "the card's container must always be rendered"
    return container.children[0] if container.children else None


def test_the_card_asks_for_the_account_when_only_identity_is_unasked(
    stats_dir,
):
    _store(**{STATS_DIR_KEY: str(stats_dir)})

    card = _card(home.layout())

    assert card is not None
    assert _texts(card) == [
        home.SETUP_CARD_IDENTITY_TITLE,
        home.SETUP_CARD_IDENTITY_BODY,
        home.SETUP_CARD_SKIP_FINE_PRINT,
    ]
    assert _button_labels(card) == [
        home.SETUP_CARD_OPEN_SETTINGS_LABEL,
        home.SETUP_CARD_SKIP_LABEL,
    ]
    settings_link = next(
        child for child in _walk_components(card) if isinstance(child, dmc.Anchor)
    )
    assert settings_link.href == "/settings"


@pytest.mark.parametrize(
    "identity",
    [{}, {USERNAME_KEY: ""}, {USERNAME_KEY: "MingoDynasty"}],
)
def test_a_never_configured_stats_folder_wins_and_offers_no_skip(identity):
    """Without runs there is nothing to plot, so this state is not dismissible."""
    _store(**identity)

    card = _card(home.layout())

    assert card is not None
    assert _texts(card) == [
        home.SETUP_CARD_STATS_DIR_TITLE,
        home.SETUP_CARD_STATS_DIR_BODY,
    ]
    assert _button_labels(card) == [home.SETUP_CARD_OPEN_SETTINGS_LABEL]


@pytest.mark.parametrize("stats_dir_value", ["", "no-such-stats-dir"])
@pytest.mark.parametrize(
    "username_value",
    ["", "MingoDynasty"],
)
def test_a_key_that_exists_never_brings_the_card_back(
    stats_dir_value,
    username_value,
):
    """Deliberately empty and stored-but-vanished are the hints' business."""
    _store(**{STATS_DIR_KEY: stats_dir_value, USERNAME_KEY: username_value})

    assert _card(home.layout()) is None


def test_a_configured_install_shows_no_card(stats_dir):
    _store(
        **{
            STATS_DIR_KEY: str(stats_dir),
            USERNAME_KEY: "MingoDynasty",
            STEAM_ID_KEY: "76561197986713986",
        }
    )

    assert _card(home.layout()) is None


def test_the_card_stands_aside_while_a_stats_folder_change_awaits_a_restart(
    stats_dir,
):
    """The restart hint owns that moment; two banners for one action is noise."""
    _store()
    settings_service.save_settings({STATS_DIR_KEY: str(stats_dir)})
    assert settings_service.is_stats_dir_change_pending() is True

    page = home.layout()

    assert _card(page) is None
    assert _component_by_id(page, "stats-dir-hint") is not None


def test_skip_records_the_decline_and_takes_the_card_away(monkeypatch, stats_dir):
    monkeypatch.setattr(
        home, "ctx", SimpleNamespace(triggered_id=home.SETUP_CARD_SKIP_ID)
    )
    _store(**{STATS_DIR_KEY: str(stats_dir), STEAM_ID_KEY: "76561197986713986"})

    assert home.skip_identity_setup(1) == []

    assert settings_service.get_settings() == {
        STATS_DIR_KEY: str(stats_dir),
        STEAM_ID_KEY: "76561197986713986",
        USERNAME_KEY: "",
    }
    assert _card(home.layout()) is None


def test_skip_leaves_a_missing_stats_folder_for_the_next_boot_to_find(monkeypatch):
    """The decline is identity-only: the bootstrap must keep retrying."""
    monkeypatch.setattr(
        home, "ctx", SimpleNamespace(triggered_id=home.SETUP_CARD_SKIP_ID)
    )
    _store()

    home.skip_identity_setup(1)

    assert settings_service.get_settings() == {USERNAME_KEY: ""}


def test_skip_starts_no_warmup_worker_and_needs_no_restart(monkeypatch, stats_dir):
    """There is no username to warm anything for, and nothing pins on a decline."""
    monkeypatch.setattr(
        home, "ctx", SimpleNamespace(triggered_id=home.SETUP_CARD_SKIP_ID)
    )
    monkeypatch.setattr(
        percentile_warmup_service,
        "start_percentile_warmup_worker",
        lambda *_args: pytest.fail("the decline started the warmup worker"),
    )
    # A module-level alias would call straight past the patch above, so the page
    # must reach the worker through nothing at all.
    assert not hasattr(home, "start_percentile_warmup_worker")
    _store(**{STATS_DIR_KEY: str(stats_dir)})

    home.skip_identity_setup(1)

    assert settings_service.is_restart_pending() is False


@pytest.mark.parametrize(
    ("n_clicks", "triggered_id"),
    [(None, "setup-card-skip"), (1, None)],
)
def test_a_skip_nobody_clicked_declines_nothing(monkeypatch, n_clicks, triggered_id):
    """The DashProxy initial-call hazard, on a callback that writes to disk."""
    monkeypatch.setattr(home, "ctx", SimpleNamespace(triggered_id=triggered_id))
    monkeypatch.setattr(
        home,
        "decline_identity",
        lambda: pytest.fail("a page load answered the identity ask"),
    )

    assert home.skip_identity_setup(n_clicks) is no_update
