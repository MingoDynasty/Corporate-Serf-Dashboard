"""Cover the optional build-label prefix on browser tab titles."""

import dash
import pytest

from source.config import config_service
from source.config.config_service import ConfigData, get_config
from source.utilities.build_info import BuildInfo

dash.Dash(__name__, use_pages=True, pages_folder="")

# Imported for the side effect that fills ``dash.page_registry``.
from source.pages import (  # noqa: E402, F401
    aim_training_journey,
    home,
    playlist_scenarios,
    playlists,
    settings,
)
from source.pages import page_title as page_title_module  # noqa: E402
from source.pages.page_title import page_title  # noqa: E402

# One per branch of ``BuildInfo.release_label``: an install names its tag, a
# checkout is "dev", and a build that identified nothing is "unknown".
TAGGED_BUILD = BuildInfo(
    sha="0123456789abcdef",
    commit_date="2026-08-09",
    tag="v2026.08.09.9",
    source="manifest",
)
CHECKOUT_BUILD = BuildInfo(
    sha="0123456789abcdef",
    commit_date="2026-08-09",
    tag=None,
    source="git",
)
UNIDENTIFIED_BUILD = BuildInfo(sha=None, commit_date=None, tag=None, source="unknown")


def _set_flag(monkeypatch: pytest.MonkeyPatch, enabled: bool) -> None:
    """Point the cached config at one carrying the given flag value."""
    config = ConfigData(port=8050, show_version_in_title=enabled)
    monkeypatch.setattr(config_service, "load_config", lambda: config)
    get_config.cache_clear()


def _set_build(monkeypatch: pytest.MonkeyPatch, build_info: BuildInfo) -> None:
    """Report the given build identity to the title helper."""
    monkeypatch.setattr(page_title_module, "get_build_info", lambda: build_info)


def test_titles_are_unchanged_while_the_flag_is_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The default is off, so ordinary users never see a marker."""
    _set_flag(monkeypatch, False)
    _set_build(monkeypatch, TAGGED_BUILD)

    assert page_title("Playlists")() == "Playlists"


@pytest.mark.parametrize(
    ("build_info", "expected"),
    [
        (TAGGED_BUILD, "v2026.08.09.9 - Playlists"),
        (CHECKOUT_BUILD, "dev - Playlists"),
        # Verbatim: an opted-in operator would rather see "unknown" than a
        # release identity this build cannot prove.
        (UNIDENTIFIED_BUILD, "unknown - Playlists"),
    ],
    ids=["tag", "dev", "unknown"],
)
def test_the_flag_prefixes_the_release_label(
    monkeypatch: pytest.MonkeyPatch,
    build_info: BuildInfo,
    expected: str,
) -> None:
    """The marker's content is derived, so instances self-label."""
    _set_flag(monkeypatch, True)
    _set_build(monkeypatch, build_info)

    assert page_title("Playlists")() == expected


def test_a_callable_title_keeps_its_dynamic_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Wrapping must not flatten a per-request title into a constant."""
    _set_flag(monkeypatch, False)

    wrapped = page_title(lambda playlist_code=None, **_: f"{playlist_code} - Scenarios")

    assert wrapped(playlist_code="ABC") == "ABC - Scenarios"
    assert wrapped() == "None - Scenarios"


def test_a_callable_title_is_prefixed_too(monkeypatch: pytest.MonkeyPatch) -> None:
    """The prefix lands ahead of the dynamic part, not inside it."""
    _set_flag(monkeypatch, True)
    _set_build(monkeypatch, CHECKOUT_BUILD)

    wrapped = page_title(lambda playlist_code=None, **_: f"{playlist_code} - Scenarios")

    assert wrapped(playlist_code="ABC") == "dev - ABC - Scenarios"


def test_registration_does_not_read_the_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pages register before ``main`` loads the config, so wrapping must not read it.

    Reading it here would turn a missing or unparseable config.toml into an
    import-time traceback, bypassing the startup path that reports it.
    """

    def _explode() -> ConfigData:
        raise AssertionError("the config was read at registration time")

    monkeypatch.setattr(page_title_module, "get_config", _explode)

    page_title("Playlists")


@pytest.mark.parametrize(
    ("module", "expected"),
    [
        ("source.pages.home", "Scenario Performance"),
        ("source.pages.playlists", "Playlists"),
        ("source.pages.settings", "Settings"),
        ("source.pages.aim_training_journey", "Aim Training Journey"),
    ],
)
def test_every_static_page_resolves_its_own_title(
    monkeypatch: pytest.MonkeyPatch,
    module: str,
    expected: str,
) -> None:
    """All five registration sites go through the helper, prefix included."""
    _set_flag(monkeypatch, True)
    _set_build(monkeypatch, CHECKOUT_BUILD)

    title = dash.page_registry[module]["title"]

    assert title() == f"dev - {expected}"


def test_the_templated_page_resolves_its_playlist_title(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The fifth site keeps the playlist name Dash passes it per request."""
    _set_flag(monkeypatch, True)
    _set_build(monkeypatch, CHECKOUT_BUILD)
    monkeypatch.setattr(
        "source.pages.playlist_scenarios.get_playlist_display_label",
        lambda code: f"Playlist {code}",
    )

    title = dash.page_registry["source.pages.playlist_scenarios"]["title"]

    assert title(playlist_code="ABC") == "dev - Playlist ABC - Playlist Scenarios"
    assert title() == "dev - Playlist Scenarios"
