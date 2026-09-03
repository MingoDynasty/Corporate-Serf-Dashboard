"""The settings page: form rendering, the save flow, and the restart notice."""

import json
from collections import deque
from datetime import UTC, datetime
from types import SimpleNamespace

import dash
import pytest
from dash import no_update
from dash._callback import GLOBAL_CALLBACK_LIST

from source.config import settings_service
from source.config.identity_detection import (
    IdentityCandidate,
    IdentityDetectionResult,
)
from source.utilities.build_info import BuildInfo
from source.utilities.paths import log_dir
from source.utilities.utilities import format_absolute_timestamp

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.pages import settings as settings_page  # noqa: E402

SAVE_BUTTON_ID = "app-settings-save-button"
DETECT_BUTTON_ID = "app-settings-detect-button"
PICKER_ID = "app-settings-identity-picker"


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


@pytest.fixture(autouse=True)
def candidates(monkeypatch):
    """Declare what the machine's Steam holds; no test reads the real registry.

    Autouse because ``layout`` detects on every visit, and a dev machine with
    KovaaK's installed would otherwise leak its own paths into every render
    assertion. Mutate the returned list to change what detection reports.
    """
    found = [r"S:\SteamLibrary\steamapps\common\FPSAimTrainer\FPSAimTrainer\stats"]
    monkeypatch.setattr(
        settings_page,
        "detect_stats_dir_candidates",
        lambda: list(found),
    )
    return found


@pytest.fixture
def clicked(monkeypatch):
    """Report the save button as the trigger, the way a real click does."""
    monkeypatch.setattr(
        settings_page,
        "ctx",
        SimpleNamespace(triggered_id=SAVE_BUTTON_ID),
    )


@pytest.fixture
def detect_clicked(monkeypatch):
    """Report the Detect button as the trigger, the way a real click does."""
    monkeypatch.setattr(
        settings_page,
        "ctx",
        SimpleNamespace(triggered_id=DETECT_BUTTON_ID),
    )


@pytest.fixture
def picked(monkeypatch):
    """Report the picker as the trigger, the way choosing a row does."""
    monkeypatch.setattr(settings_page, "ctx", SimpleNamespace(triggered_id=PICKER_ID))


@pytest.fixture
def detects(monkeypatch):
    """Declare what one Detect press finds; the real engine never runs.

    Every outcome past "exactly one verified account" is unreachable on this
    machine — its three Steam accounts collapse to a single verified pair — so
    the several-candidate, unchecked, and failed-discovery paths exist here or
    nowhere.
    """

    def declare(*candidates, unchecked=0, complete=True):
        monkeypatch.setattr(
            settings_page,
            "detect_identity_candidates",
            lambda: IdentityDetectionResult(tuple(candidates), unchecked, complete),
        )

    return declare


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


MAIN_ACCOUNT_ID = "76561197986713986"
OTHER_ACCOUNT_ID = "76561198000000001"


def _candidate(
    username="MingoDynasty",
    steam_id=MAIN_ACCOUNT_ID,
    persona_name=None,
    last_access="2026-08-02T14:56:42.919Z",
):
    """One verified pair, as the engine hands it over."""
    return IdentityCandidate(
        username=username,
        steam_id=steam_id,
        # Usually the same string; the two are distinct namespaces that merely
        # often coincide, so tests that care say so.
        persona_name=username if persona_name is None else persona_name,
        last_access=last_access,
    )


def _detect(n_clicks=1):
    """Press Detect, naming the seven outputs the callback answers with."""
    username, steam_id, status, picker, picker_class, picker_value, stored = (
        settings_page.detect_identity(n_clicks)
    )
    return SimpleNamespace(
        username=username,
        steam_id=steam_id,
        status=status,
        rows=picker.children,
        picker_class=picker_class,
        picker_value=picker_value,
        stored=stored,
    )


def _offered(outcome):
    """The picker rows a detection produced, as (label, value) pairs."""
    return [(row.label, row.value) for row in outcome.rows]


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


def test_detected_directories_are_offered_as_suggestions(candidates, tmp_path):
    """Suggestions never disturb the stored value: they sit under the field."""
    candidates[:] = [str(tmp_path / "primary"), str(tmp_path / "second")]
    settings_service.save_settings({"stats_dir": str(tmp_path / "typed")})

    field = _component_by_id(settings_page.layout(), "app-settings-stats-dir")

    assert type(field).__name__ == "Autocomplete"
    assert field.data == candidates
    assert field.value == str(tmp_path / "typed")


def test_a_prefilled_field_still_offers_the_other_libraries(candidates, tmp_path):
    """The wrong-library repair is the whole point, and it starts prefilled.

    Mantine's default filter matches options against the input text, so the
    seeded path would hide every alternative — the one case the suggestions
    exist for. Pinned at the prop because the behavior lives in Mantine.
    """
    candidates[:] = [str(tmp_path / "primary"), str(tmp_path / "second")]
    settings_service.save_settings({"stats_dir": str(tmp_path / "primary")})

    field = _component_by_id(settings_page.layout(), "app-settings-stats-dir")

    assert field.filter == settings_page.SHOW_EVERY_CANDIDATE


def test_the_field_says_it_has_folders_to_offer(candidates, tmp_path):
    """An Autocomplete looks like a text box, so the suggestions say they exist.

    Both signs are the fix for the same blind spot: a prefilled field gave no
    hint that the other libraries were one click away.
    """
    candidates[:] = [str(tmp_path / "primary"), str(tmp_path / "second")]
    settings_service.save_settings({"stats_dir": str(tmp_path / "primary")})

    field = _component_by_id(settings_page.layout(), "app-settings-stats-dir")

    assert field.rightSection is not None
    assert settings_page.STATS_DIR_SUGGESTIONS_HINT in field.description


def test_detecting_nothing_leaves_a_plain_text_field(candidates):
    """A machine without Steam gets exactly the field that shipped.

    Its signs included: a chevron over an empty list invites a click at a
    dropdown with nothing to open.
    """
    candidates.clear()

    field = _component_by_id(settings_page.layout(), "app-settings-stats-dir")

    assert field.data == []
    assert field.rightSection is None
    assert field.description == settings_page.STATS_DIR_DESCRIPTION


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
        _save(stats_dir=str(tmp_path), username="", n_clicks=None) == (no_update,) * 8
    )
    assert settings_service.get_settings() == {"kovaaks_username": "MingoDynasty"}
    assert quiet_warmup == []


def test_a_save_triggered_by_anything_else_writes_nothing(monkeypatch, tmp_path):
    monkeypatch.setattr(settings_page, "ctx", SimpleNamespace(triggered_id=None))
    settings_service.save_settings({"kovaaks_username": "MingoDynasty"})

    assert _save(stats_dir=str(tmp_path))[0] is no_update
    assert settings_service.get_settings() == {"kovaaks_username": "MingoDynasty"}


def test_a_valid_save_writes_all_three_keys(clicked, quiet_warmup, tmp_path):
    stats_dir_error, steam_id_error, status, status_class, *_rest = _save(
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

    stats_dir_error, steam_id_error, status, status_class, *_rest = _save(
        stats_dir=str(tmp_path / "no-such-directory"),
        username="MingoDynasty",
    )

    assert stats_dir_error == settings_page.STATS_DIR_ERROR
    assert steam_id_error is None
    # A refusal clears any status a previous save left behind.
    assert status == ""
    assert status_class == settings_page.SAVE_STATUS_CLASS
    # Nothing was written, so neither the store alert nor the notice moves.
    assert _rest == [no_update] * 4
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

    stats_dir_error, steam_id_error, status, status_class, *_rest = _save(
        stats_dir=str(tmp_path),
        username="MingoDynasty",
    )

    assert (stats_dir_error, steam_id_error) == (None, None)
    assert status == settings_page.SAVE_FAILED_STATUS
    assert status_class == settings_page.SAVE_STATUS_FAILED_CLASS
    # The store is untouched, so the alert and the notice still describe it.
    assert _rest == [no_update] * 4
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


def test_the_page_names_the_running_build(monkeypatch):
    """Straight off ``BuildInfo``: the page re-derives no part of the identity.

    Patched on this module rather than on ``build_info``: the resolver is
    ``@cache``d, so the source module's copy may already have answered.
    """
    monkeypatch.setattr(
        settings_page,
        "get_build_info",
        lambda: BuildInfo(
            sha="0123456789abcdef",
            commit_date="2026-08-02",
            tag="v2026.08.02.1",
            source="release-file",
        ),
    )

    page = settings_page.layout()

    assert _component_by_id(page, "app-settings-version").children == (
        "Version v2026.08.02.1"
    )
    assert _component_by_id(page, "app-settings-build").children == (
        "Commit 0123456 (2026-08-02)"
    )


def test_the_bug_report_link_names_the_form_and_the_version():
    url = settings_page.bug_report_url("v2026.08.02.1")

    assert url == (
        "https://github.com/MingoDynasty/Corporate-Serf-Dashboard/issues/new"
        "?template=bug_report.yml&version=v2026.08.02.1"
    )


def test_a_bug_report_link_escapes_the_label_it_carries():
    """The tag comes from JSON the app did not write, so it is encoded, not
    pasted: an unescaped ``&`` or space would truncate or split the param."""
    url = settings_page.bug_report_url("v1.0 rc&1")

    assert "version=v1.0+rc%261" in url
    assert url.count("&") == 1


@pytest.mark.parametrize(
    ("build", "expected_label"),
    [
        (
            BuildInfo(sha="0" * 40, commit_date="2026-08-02", tag=None, source="git"),
            "dev",
        ),
        (BuildInfo(sha=None, commit_date=None, tag=None, source="unknown"), "unknown"),
    ],
)
def test_an_unreleased_build_still_prefills_the_version(
    monkeypatch, build, expected_label
):
    """Never suppressed: the field is required and the user can correct it, so
    a placeholder beats an empty box the reporter has to guess at."""
    monkeypatch.setattr(settings_page, "get_build_info", lambda: build)

    anchor = _component_by_id(settings_page.layout(), "app-settings-bug-report")

    assert anchor.href == settings_page.bug_report_url(expected_label)
    assert f"version={expected_label}" in anchor.href


def test_the_page_offers_a_prefilled_report_and_says_where_the_log_is(monkeypatch):
    """The two failure points of a user-driven report: a wrong version and a
    log nobody can find."""
    monkeypatch.setattr(
        settings_page,
        "get_build_info",
        lambda: BuildInfo(
            sha="0123456789abcdef",
            commit_date="2026-08-02",
            tag="v2026.08.02.1",
            source="release-file",
        ),
    )

    page = settings_page.layout()

    anchor = _component_by_id(page, "app-settings-bug-report")
    assert anchor.children == "Report a bug"
    assert anchor.href == settings_page.bug_report_url("v2026.08.02.1")
    assert anchor.target == "_blank"
    assert _component_by_id(page, "app-settings-log-dir").children == (
        f"Logs {log_dir()}"
    )


def test_a_settled_process_renders_no_notice(tmp_path):
    settings_service.save_settings({"stats_dir": str(tmp_path)})
    settings_service.resolve_stats_dir()

    notice = _component_by_id(settings_page.layout(), "app-settings-restart-notice")

    assert notice.children == ""
    assert notice.className == settings_page.RESTART_NOTICE_HIDDEN_CLASS


def test_opening_the_page_never_calls_kovaaks(monkeypatch):
    """Detection is split by cost: local candidates render, probes wait.

    The picker ships empty and hidden, which is also what says the page did not
    detect anything on its way in.
    """

    def never():
        raise AssertionError("identity detection ran while rendering the page")

    monkeypatch.setattr(settings_page, "detect_identity_candidates", never)

    picker = _component_by_id(settings_page.layout(), PICKER_ID)

    assert picker.children == []
    assert picker.className == settings_page.PICKER_HIDDEN_CLASS


def test_detect_explains_itself_before_it_is_pressed():
    """The status line ships holding the hint, not empty.

    A bare "Detect" beside three empty boxes named neither what it detects nor
    that pressing it is free, and the line that would have said so only earned
    its copy after the press.
    """
    page = settings_page.layout()

    button = _component_by_id(page, DETECT_BUTTON_ID)
    status = _component_by_id(page, "app-settings-detect-status")

    assert button.children == "Detect my accounts"
    assert status.children == settings_page.DETECT_HINT


def test_one_certain_account_fills_the_identity_fields(detect_clicked, detects):
    """The only outcome allowed to fill by itself: nothing was left unresolved."""
    detects(_candidate(username="MingoDynasty", persona_name="mingo"))

    outcome = _detect()

    # The canonical webapp username, never the persona that found it.
    assert outcome.username == "MingoDynasty"
    assert outcome.steam_id == MAIN_ACCOUNT_ID
    assert "MingoDynasty" in outcome.status
    assert "Save" in outcome.status
    # Nothing to choose between, so nothing is offered.
    assert _offered(outcome) == []
    assert outcome.picker_class == settings_page.PICKER_HIDDEN_CLASS


def test_several_accounts_are_offered_instead_of_filled(detect_clicked, detects):
    """A wrong identity fills caches with someone else's ranks; the user picks."""
    detects(
        _candidate(username="Newest"),
        _candidate(username="Older", steam_id=OTHER_ACCOUNT_ID),
    )

    outcome = _detect()

    assert (outcome.username, outcome.steam_id) == (no_update, no_update)
    # Engine order is display order: newest last-access first, never re-sorted.
    assert _offered(outcome) == [
        ("Newest", MAIN_ACCOUNT_ID),
        ("Older", OTHER_ACCOUNT_ID),
    ]
    assert outcome.picker_class == settings_page.PICKER_CLASS
    assert outcome.stored == [
        {"username": "Newest", "steam_id": MAIN_ACCOUNT_ID},
        {"username": "Older", "steam_id": OTHER_ACCOUNT_ID},
    ]
    assert "2" in outcome.status


@pytest.mark.parametrize(
    ("unchecked", "complete"),
    [
        # An account nobody could check may be the second verified account.
        (1, True),
        # So may an account the unreadable account list never yielded.
        (0, False),
    ],
)
def test_a_sole_account_from_an_unfinished_run_is_never_filled(
    detect_clicked,
    detects,
    unchecked,
    complete,
):
    detects(_candidate(), unchecked=unchecked, complete=complete)

    outcome = _detect()

    assert (outcome.username, outcome.steam_id) == (no_update, no_update)
    assert _offered(outcome) == [("MingoDynasty", MAIN_ACCOUNT_ID)]
    assert outcome.picker_class == settings_page.PICKER_CLASS


def test_a_picker_row_names_the_steam_account_behind_the_name(
    detect_clicked,
    detects,
):
    """Two accounts are told apart by their Steam login, not their KovaaK's name."""
    detects(
        _candidate(persona_name="mingo", last_access="2026-08-02T14:56:42"),
        unchecked=1,
    )

    (row,) = _detect().rows

    assert row.label == "MingoDynasty"
    assert "mingo" in row.description
    assert "Aug 2, 2026, 2:56 PM" in row.description


def test_finding_nothing_with_nothing_unresolved_is_conclusive(
    detect_clicked,
    detects,
):
    """Everything was checked and nobody matched: manual entry is all that is left."""
    detects()

    outcome = _detect()

    assert outcome.status == settings_page.NO_MATCH_STATUS
    assert _offered(outcome) == []
    assert outcome.picker_class == settings_page.PICKER_HIDDEN_CLASS


def test_an_unreadable_account_list_never_reads_as_no_match(detect_clicked, detects):
    """A detection that could not enumerate accounts has ruled out nothing."""
    detects(complete=False)

    outcome = _detect()

    assert settings_page.DISCOVERY_FAILED_STATUS in outcome.status
    assert settings_page.NO_MATCH_STATUS not in outcome.status


def test_the_status_names_how_many_accounts_went_unchecked(detect_clicked, detects):
    detects(unchecked=2)

    outcome = _detect()

    assert "2 Steam accounts could not be checked" in outcome.status
    assert settings_page.NO_MATCH_STATUS not in outcome.status


def test_choosing_a_detected_account_fills_both_fields(picked):
    stored = [
        {"username": "Newest", "steam_id": MAIN_ACCOUNT_ID},
        {"username": "Older", "steam_id": OTHER_ACCOUNT_ID},
    ]

    assert settings_page.use_detected_identity(OTHER_ACCOUNT_ID, stored) == (
        "Older",
        OTHER_ACCOUNT_ID,
    )


@pytest.mark.parametrize(
    ("n_clicks", "triggered_id"),
    [(None, DETECT_BUTTON_ID), (1, None)],
)
def test_a_detection_nobody_asked_for_never_calls_kovaaks(
    monkeypatch,
    n_clicks,
    triggered_id,
):
    """The initial-call hazard, on the one callback here that hits the network."""

    def never():
        raise AssertionError("identity detection ran without a Detect press")

    monkeypatch.setattr(
        settings_page, "ctx", SimpleNamespace(triggered_id=triggered_id)
    )
    monkeypatch.setattr(settings_page, "detect_identity_candidates", never)

    assert settings_page.detect_identity(n_clicks) == (no_update,) * 7


@pytest.mark.parametrize(
    ("value", "triggered_id"),
    [(None, PICKER_ID), (MAIN_ACCOUNT_ID, None)],
)
def test_a_pick_nobody_made_fills_nothing(monkeypatch, value, triggered_id):
    """Clearing the picker after a fresh detection arrives as a value change too."""
    monkeypatch.setattr(
        settings_page, "ctx", SimpleNamespace(triggered_id=triggered_id)
    )
    stored = [{"username": "MingoDynasty", "steam_id": MAIN_ACCOUNT_ID}]

    assert settings_page.use_detected_identity(value, stored) == (
        no_update,
        no_update,
    )


def test_a_last_seen_stamp_is_shown_in_the_house_format():
    assert settings_page._format_last_seen("2026-08-02T14:56:42") == (
        "Aug 2, 2026, 2:56 PM"
    )


def test_a_utc_stamp_is_shown_in_local_time():
    """Whatever this machine's timezone is, one instant has one rendering."""
    shown = settings_page._format_last_seen("2026-08-02T14:56:42.919Z")

    assert shown == settings_page._format_last_seen("2026-08-02T16:56:42+02:00")
    assert shown == format_absolute_timestamp(
        datetime(2026, 8, 2, 14, 56, 42, tzinfo=UTC).astimezone()
    )


def test_an_unreadable_last_seen_stamp_is_shown_as_it_arrived():
    """A decorative field must not cost the user a candidate they could pick."""
    assert settings_page._format_last_seen("last tuesday") == "last tuesday"


# --- schema_version: what the page says when the store cannot be used ---


def _write_store(text):
    """Put arbitrary text in the store the fixture pointed the service at."""
    path = settings_service.SETTINGS_FILE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    settings_service.clear_settings_cache()


def test_a_usable_store_hides_the_alert(tmp_path):
    settings_service.save_settings({"stats_dir": str(tmp_path)})

    alert = _component_by_id(settings_page.layout(), "app-settings-store-alert")

    assert alert.children == ""
    assert alert.className == settings_page.STORE_ALERT_HIDDEN_CLASS


def test_a_missing_store_hides_the_alert():
    """A first run is empty fields and nothing else: there is nothing to warn about."""
    settings_service.SETTINGS_FILE_PATH.unlink(missing_ok=True)
    settings_service.clear_settings_cache()

    alert = _component_by_id(settings_page.layout(), "app-settings-store-alert")

    assert alert.className == settings_page.STORE_ALERT_HIDDEN_CLASS


def test_an_unusable_store_is_named_beside_the_empty_form():
    """Without this the page renders a blank form, exactly like a first run."""
    _write_store(json.dumps({"kovaaks_username": "MingoDynasty"}))

    page = settings_page.layout()

    alert = _component_by_id(page, "app-settings-store-alert")
    assert alert.className == settings_page.STORE_ALERT_CLASS
    assert '"schema_version": 1' in alert.children
    assert _component_by_id(page, "app-settings-username").value == ""


def test_a_newer_store_says_the_data_is_intact():
    _write_store(json.dumps({"schema_version": 2, "kovaaks_username": "Future"}))

    alert = _component_by_id(settings_page.layout(), "app-settings-store-alert")

    assert alert.className == settings_page.STORE_ALERT_CLASS
    assert "newer version of this app" in alert.children


def test_a_save_against_a_newer_store_is_refused_distinctly(clicked, quiet_warmup):
    """A refusal is not an I/O failure: the remedy is updating, not retrying."""
    _write_store(json.dumps({"schema_version": 2, "kovaaks_username": "Future"}))

    (
        _dir_error,
        _id_error,
        status,
        status_class,
        alert,
        alert_class,
        notice,
        notice_class,
    ) = _save(username="MingoDynasty")

    assert status == settings_page.SAVE_REFUSED_STATUS
    assert status != settings_page.SAVE_FAILED_STATUS
    assert status_class == settings_page.SAVE_STATUS_FAILED_CLASS
    assert (notice, notice_class) == (no_update, no_update)
    # Nothing was written, so the alert still describes the file on disk.
    assert (alert, alert_class) == (no_update, no_update)
    assert json.loads(
        settings_service.SETTINGS_FILE_PATH.read_text(encoding="utf-8")
    ) == {"schema_version": 2, "kovaaks_username": "Future"}
    assert quiet_warmup == []


def test_a_save_against_an_unusable_store_recovers_it(clicked):
    """Self-service repair: the page can always rewrite a file it cannot read."""
    _write_store("not json")

    _dir_error, _id_error, status, status_class, *_ = _save(username="MingoDynasty")

    assert status == settings_page.SAVED_STATUS
    assert status_class == settings_page.SAVE_STATUS_CLASS
    assert settings_service.get_settings()["kovaaks_username"] == "MingoDynasty"
    assert (
        _component_by_id(settings_page.layout(), "app-settings-store-alert").className
        == settings_page.STORE_ALERT_HIDDEN_CLASS
    )


def test_a_recovery_save_clears_the_alert_without_a_reload(clicked):
    """Dash never rebuilds the layout after a callback, so the save must.

    Otherwise "Settings saved." renders directly under a warning saying the
    settings are not being used, until the user navigates away.
    """
    _write_store("not json")
    # The page was rendered while the store was unusable: the alert is visible.
    assert (
        _component_by_id(settings_page.layout(), "app-settings-store-alert").className
        == settings_page.STORE_ALERT_CLASS
    )

    *_, alert, alert_class, _notice, _notice_class = _save(username="MingoDynasty")

    assert alert == ""
    assert alert_class == settings_page.STORE_ALERT_HIDDEN_CLASS


# --- the Celebrations section ------------------------------------------

# What the Save button writes. The celebration controls sit outside the form,
# so nothing here may appear among their outputs, and none of theirs here.
FORM_OUTPUT_IDS = (
    "app-settings-stats-dir",
    "app-settings-steam-id",
    "app-settings-save-status",
    "app-settings-store-alert",
    "app-settings-restart-notice",
)


def _callback_output(fragment: str) -> str:
    """Return the one registered callback id whose output list holds this."""
    (spec,) = [spec for spec in GLOBAL_CALLBACK_LIST if fragment in str(spec["output"])]
    return str(spec["output"])


def _callback_spec(fragment: str):
    (spec,) = [spec for spec in GLOBAL_CALLBACK_LIST if fragment in str(spec["output"])]
    return spec


def test_the_switch_writes_a_style_name_to_the_store():
    # A style name from the start, not a boolean: the follow-up that turns this
    # switch into a style select then only adds values to the same contract.
    assert settings_page.set_celebration_style(True, 1) == "confetti"
    assert settings_page.set_celebration_style(False, 1) == "off"


def test_mounting_the_page_never_writes_the_switch_default_over_the_store():
    """Opening Settings must not turn the celebration back on.

    Mounting the page fires this callback with the switch's layout default
    despite ``prevent_initial_call``, and the triggering id is the switch
    itself, so the initializing tick is what tells the two apart: before it,
    the control is still showing a default nobody chose.
    """
    assert settings_page.set_celebration_style(True, 0) is no_update
    assert settings_page.set_celebration_style(True, None) is no_update


def test_the_switch_shows_the_stored_setting():
    assert settings_page.show_stored_celebration_style(1, "off") is False
    assert settings_page.show_stored_celebration_style(1, "confetti") is True


def test_a_store_this_build_cannot_read_still_shows_as_on():
    """Browser-local storage fails towards the celebration, never into silence.

    A cleared store reads as nothing, and a style name a later build wrote
    means nothing here; both leave the switch on, which is what the store's own
    default says.
    """
    assert settings_page.show_stored_celebration_style(1, None) is True
    assert settings_page.show_stored_celebration_style(1, "fireworks") is True


def test_the_switch_carries_no_persistence_of_its_own():
    """The store is the setting; the control is a view of it.

    Two persisted values for one preference is how a switch and the select that
    replaces it end up disagreeing.
    """
    switch = _component_by_id(
        settings_page.layout(), settings_page.CELEBRATION_SWITCH_ID
    )

    assert not hasattr(switch, "persistence")
    assert switch.checked is True


def test_the_section_renders_its_heading_control_and_preview():
    layout = settings_page.layout()
    switch = _component_by_id(layout, settings_page.CELEBRATION_SWITCH_ID)
    preview = _component_by_id(layout, settings_page.CELEBRATION_PREVIEW_BUTTON_ID)
    headings = [
        component.children
        for component in _titles(layout)
        if component.children == settings_page.CELEBRATIONS_HEADING
    ]

    assert headings == [settings_page.CELEBRATIONS_HEADING]
    assert switch.label == settings_page.CELEBRATION_LABEL
    assert switch.description == settings_page.CELEBRATION_DESCRIPTION
    assert preview.children == settings_page.PREVIEW_LABEL


def test_preview_plays_in_the_browser_and_says_nothing():
    """The same clientside path a real celebration takes, minus the toast.

    The toast reports a run and there is no run here, so Preview writes only
    its own dead-end output: no notification container, no server round trip.
    """
    spec = _callback_spec(settings_page.CELEBRATION_PREVIEW_SIGNAL_ID)

    assert spec["clientside_function"] is not None
    assert "sendNotifications" not in str(spec["output"])
    assert [(dep["id"], dep["property"]) for dep in spec["state"]] == [
        ("pb-celebration-style", "data")
    ]


def test_the_celebrations_section_stands_outside_the_save_form():
    """It applies the moment it is flipped, and Save owns none of it.

    The restart notice and the store alert speak for the three keys the form
    writes to disk; a browser-local preference must not be able to disturb
    either.
    """
    saved = _callback_output("app-settings-save-status.children")
    celebration_ids = (
        settings_page.CELEBRATION_SWITCH_ID,
        settings_page.CELEBRATION_PREVIEW_SIGNAL_ID,
        "pb-celebration-style",
    )

    for component_id in celebration_ids:
        assert component_id not in saved
    for component_id in celebration_ids:
        written = _callback_output(f"{component_id}.")
        assert not any(form_id in written for form_id in FORM_OUTPUT_IDS)


def _titles(root):
    """Every ``dmc.Title`` in a built layout, in no particular order."""
    found = []
    components = deque([root])
    while components:
        component = components.popleft()
        if type(component).__name__ == "Title":
            found.append(component)
        children = getattr(component, "children", None)
        if children is None:
            continue
        if isinstance(children, (list, tuple)):
            components.extend(children)
        else:
            components.append(children)
    return found
