"""The settings page: form rendering, the save flow, and the restart notice."""

from collections import deque
from types import SimpleNamespace

import dash
import pytest
from dash import no_update

from source.config import settings_service

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.pages import settings as settings_page  # noqa: E402

SAVE_BUTTON_ID = "app-settings-save-button"


@pytest.fixture(autouse=True)
def quiet_warmup(monkeypatch):
    """Never start the real worker; record whether the page asked for it."""
    calls = []
    monkeypatch.setattr(
        settings_page,
        "start_percentile_warmup_worker",
        lambda: calls.append(True),
    )
    return calls


@pytest.fixture
def clicked(monkeypatch):
    """Report the save button as the trigger, the way a real click does."""
    monkeypatch.setattr(
        settings_page,
        "ctx",
        SimpleNamespace(triggered_id=SAVE_BUTTON_ID),
    )


def _component_by_id(root, component_id):
    components = deque([root])
    while components:
        component = components.popleft()
        if getattr(component, "id", None) == component_id:
            return component
        children = getattr(component, "children", None)
        if children is None:
            continue
        if isinstance(children, (list, tuple)):
            components.extend(children)
        else:
            components.append(children)
    raise AssertionError(f"Component not found: {component_id}")


def _save(stats_dir="", username="", steam_id="", n_clicks=1):
    return settings_page.save_user_settings(n_clicks, stats_dir, username, steam_id)


def test_the_form_shows_what_is_stored(tmp_path):
    settings_service.save_settings(
        {
            "stats_dir": str(tmp_path),
            "kovaaks_username": "MingoDynasty",
            "steam_id": "76561197986713986",
        }
    )

    page = settings_page.layout()

    assert _component_by_id(page, "app-settings-stats-dir").value == str(tmp_path)
    assert _component_by_id(page, "app-settings-username").value == "MingoDynasty"
    assert _component_by_id(page, "app-settings-steam-id").value == "76561197986713986"


def test_the_steam_id_field_is_never_a_number_input():
    """A SteamID64 exceeds JavaScript's exact-integer range."""
    field = _component_by_id(settings_page.layout(), "app-settings-steam-id")

    assert type(field).__name__ == "TextInput"


def test_unset_settings_render_empty_fields():
    settings_service.save_settings({})

    page = settings_page.layout()

    assert _component_by_id(page, "app-settings-stats-dir").value == ""
    assert _component_by_id(page, "app-settings-username").value == ""
    assert _component_by_id(page, "app-settings-steam-id").value == ""


def test_an_untouched_page_saves_nothing(quiet_warmup, tmp_path):
    """The initial-call hazard is real, and this callback writes to disk."""
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})

    assert (
        _save(stats_dir=str(tmp_path), username="", n_clicks=None) == (no_update,) * 6
    )
    assert settings_service.get_settings() == {"kovaaks_username": "MingoDynasty"}
    assert quiet_warmup == []


def test_a_save_triggered_by_anything_else_writes_nothing(monkeypatch, tmp_path):
    monkeypatch.setattr(settings_page, "ctx", SimpleNamespace(triggered_id=None))
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})

    assert _save(stats_dir=str(tmp_path))[0] is no_update
    assert settings_service.get_settings() == {"kovaaks_username": "MingoDynasty"}


def test_a_valid_save_writes_all_three_keys(clicked, quiet_warmup, tmp_path):
    stats_dir_error, steam_id_error, status, status_class, _notice, _class = _save(
        stats_dir=f"  {tmp_path}  ",
        username="  MingoDynasty  ",
        steam_id="76561197986713986",
    )

    assert (stats_dir_error, steam_id_error) == (None, None)
    assert status == settings_page.SAVED_STATUS
    assert status_class == settings_page.SAVE_STATUS_CLASS
    assert settings_service.get_settings() == {
        "stats_dir": str(tmp_path),
        "kovaaks_username": "MingoDynasty",
        "steam_id": "76561197986713986",
    }
    assert quiet_warmup == [True]


def test_cleared_fields_are_stored_as_empty_strings(clicked, quiet_warmup):
    """Written, not omitted: cleared and never-set stay distinguishable."""
    _save(stats_dir="", username="", steam_id="")

    assert settings_service.get_settings() == {
        "stats_dir": "",
        "kovaaks_username": "",
        "steam_id": "",
    }
    assert quiet_warmup == []


@pytest.mark.parametrize(
    ("steam_id", "expected_error"),
    [
        ("76561197986713986", None),
        ("", None),
        ("not-digits", settings_page.STEAM_ID_ERROR),
        ("7656 1197", settings_page.STEAM_ID_ERROR),
        # ``str.isdigit`` alone accepts these; no endpoint would.
        ("٧٦٥٦١", settings_page.STEAM_ID_ERROR),
        ("7656²", settings_page.STEAM_ID_ERROR),
        # The realistic paste mistakes: an account ID and a SteamID3 fragment.
        ("26448258", settings_page.STEAM_ID_ERROR),
        ("[U:1:26448258]", settings_page.STEAM_ID_ERROR),
        # Right length, below the universe-1 base -- not an account.
        ("10000000000000000", settings_page.STEAM_ID_ERROR),
        # The base itself is the first real SteamID64.
        ("76561197960265728", None),
        # One digit short and one digit long.
        ("7656119798671398", settings_page.STEAM_ID_ERROR),
        ("765611979867139866", settings_page.STEAM_ID_ERROR),
    ],
)
def test_steam_id_accepts_only_a_steam_id64(clicked, steam_id, expected_error):
    assert _save(steam_id=steam_id)[1] == expected_error


def test_a_missing_stats_directory_is_refused(clicked, quiet_warmup, tmp_path):
    settings_service.save_settings({"kovaaks_username": "Stored"})

    stats_dir_error, steam_id_error, status, status_class, notice, notice_class = _save(
        stats_dir=str(tmp_path / "no-such-directory"),
        username="MingoDynasty",
    )

    assert stats_dir_error == settings_page.STATS_DIR_ERROR
    assert steam_id_error is None
    # A refusal clears any status a previous save left behind.
    assert status == ""
    assert status_class == settings_page.SAVE_STATUS_CLASS
    assert (notice, notice_class) == (no_update, no_update)
    # All-or-nothing: the valid username in the same submit is not written.
    assert settings_service.get_settings() == {"kovaaks_username": "Stored"}
    assert quiet_warmup == []


def test_one_invalid_field_blocks_the_whole_save(clicked, quiet_warmup, tmp_path):
    settings_service.save_settings({})

    stats_dir_error, steam_id_error, *_ = _save(
        stats_dir=str(tmp_path / "no-such-directory"),
        username="MingoDynasty",
        steam_id="not-digits",
    )

    assert stats_dir_error == settings_page.STATS_DIR_ERROR
    assert steam_id_error == settings_page.STEAM_ID_ERROR
    assert settings_service.get_settings() == {}
    assert quiet_warmup == []


def test_a_failed_write_says_so_instead_of_failing_the_request(
    clicked,
    quiet_warmup,
    monkeypatch,
    tmp_path,
):
    """An antivirus lock exhausts the atomic replace's retries and re-raises.

    Letting that escape would fail the Dash request silently: the form would
    keep whatever it was already showing, including a stale "Settings saved."
    """

    def refuse_to_write(_values):
        raise PermissionError("locked by another process")

    settings_service.save_settings({"kovaaks_username": "Stored"})
    monkeypatch.setattr(settings_page, "save_settings", refuse_to_write)

    stats_dir_error, steam_id_error, status, status_class, notice, notice_class = _save(
        stats_dir=str(tmp_path),
        username="MingoDynasty",
    )

    assert (stats_dir_error, steam_id_error) == (None, None)
    assert status == settings_page.SAVE_FAILED_STATUS
    assert status_class == settings_page.SAVE_STATUS_FAILED_CLASS
    # The store is untouched, so the notice still describes the process.
    assert (notice, notice_class) == (no_update, no_update)
    assert settings_service.get_settings() == {"kovaaks_username": "Stored"}
    assert quiet_warmup == []


def test_a_first_time_identity_needs_no_restart(clicked, tmp_path):
    """The live-apply path: the pin is unfrozen, so nothing has been consumed."""
    settings_service.save_settings({"stats_dir": str(tmp_path)})
    settings_service.resolve_stats_dir()

    *_, notice, notice_class = _save(stats_dir=str(tmp_path), username="MingoDynasty")

    assert notice == ""
    assert notice_class == settings_page.RESTART_NOTICE_HIDDEN_CLASS


def test_changing_a_consumed_identity_shows_the_restart_notice(clicked, tmp_path):
    settings_service.save_settings(
        {"stats_dir": str(tmp_path), "kovaaks_username": "First"}
    )
    settings_service.resolve_stats_dir()
    # A consumer reading the identity is what freezes it for this process.
    settings_service.get_identity()

    *_, notice, notice_class = _save(stats_dir=str(tmp_path), username="Second")

    assert notice == settings_page.RESTART_NOTICE
    assert notice_class == settings_page.RESTART_NOTICE_CLASS


def test_moving_the_stats_directory_shows_the_restart_notice(clicked, tmp_path):
    booted = tmp_path / "booted"
    booted.mkdir()
    moved = tmp_path / "moved"
    moved.mkdir()
    settings_service.save_settings({"stats_dir": str(booted)})
    settings_service.resolve_stats_dir()

    *_, notice, notice_class = _save(stats_dir=str(moved))

    assert notice == settings_page.RESTART_NOTICE
    assert notice_class == settings_page.RESTART_NOTICE_CLASS


def test_the_notice_survives_a_page_revisit(clicked, tmp_path):
    """Derived, never stored: it stands until the restart actually happens."""
    booted = tmp_path / "booted"
    booted.mkdir()
    moved = tmp_path / "moved"
    moved.mkdir()
    settings_service.save_settings({"stats_dir": str(booted)})
    settings_service.resolve_stats_dir()
    _save(stats_dir=str(moved))

    notice = _component_by_id(settings_page.layout(), "app-settings-restart-notice")

    assert notice.children == settings_page.RESTART_NOTICE
    assert notice.className == settings_page.RESTART_NOTICE_CLASS


def test_a_settled_process_renders_no_notice(tmp_path):
    settings_service.save_settings({"stats_dir": str(tmp_path)})
    settings_service.resolve_stats_dir()

    notice = _component_by_id(settings_page.layout(), "app-settings-restart-notice")

    assert notice.children == ""
    assert notice.className == settings_page.RESTART_NOTICE_HIDDEN_CLASS
