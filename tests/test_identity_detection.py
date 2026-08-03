"""Verifying this machine's Steam accounts against KovaaK's profiles.

No test reads the real registry or the real API: the roots come from a fixture
that replaces the registry walk, every ``loginusers.vdf`` is a real file under
``tmp_path``, and the profile lookup is replaced by a fake whose answers each
test declares.
"""

import logging

import pytest
import requests

from source.config import identity_detection as detection

PERSONA = "MingoDynasty"
STEAM_ID = "76561198000000001"
ALT_STEAM_ID = "76561198000000002"


def _account_block(
    steam_id: str,
    persona_name: str,
    *,
    account_name: str = "account",
    timestamp: int = 1690000000,
    most_recent: str = "0",
) -> str:
    """Render one account the way Steam writes it."""
    return f"""\t"{steam_id}"
\t{{
\t\t"AccountName"\t\t"{account_name}"
\t\t"PersonaName"\t\t"{persona_name}"
\t\t"RememberPassword"\t\t"1"
\t\t"MostRecent"\t\t"{most_recent}"
\t\t"Timestamp"\t\t"{timestamp}"
\t}}"""


def _write_login_users(root, blocks: list[str]) -> None:
    """Write one root's ``config/loginusers.vdf`` from rendered blocks."""
    path = root / "config" / "loginusers.vdf"
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(blocks)
    path.write_text(f'"users"\n{{\n{body}\n}}\n', encoding="utf-8")


def _profile(
    steam_id: str = STEAM_ID,
    username: str = "MingoDynasty",
    last_access: str = "2026-07-20T12:00:00.000Z",
) -> dict:
    """Render the fields the pipeline reads out of a profile response."""
    return {
        "steamId": steam_id,
        "webapp": {"username": username, "profileImage": "https://example.test/a"},
        "lastAccess": last_access,
        "steamAccountName": "account",
    }


@pytest.fixture
def roots(monkeypatch):
    """Let a test declare the Steam roots the registry would have reported."""

    def set_roots(*paths) -> None:
        monkeypatch.setattr(detection, "_steam_roots", lambda: [str(p) for p in paths])

    return set_roots


@pytest.fixture
def profiles(monkeypatch):
    """Let a test declare what KovaaK's answers, and count the probes."""

    def set_profiles(answers: dict) -> list[str]:
        probed: list[str] = []

        def lookup(username: str):
            probed.append(username)
            answer = answers.get(username)
            if isinstance(answer, Exception):
                raise answer
            return answer

        monkeypatch.setattr(detection, "get_user_profile_by_username", lookup)
        return probed

    return set_profiles


def test_every_account_in_the_file_is_discovered(roots, tmp_path):
    root = tmp_path / "Steam"
    _write_login_users(
        root,
        [
            _account_block(STEAM_ID, PERSONA, account_name="mingo"),
            _account_block(ALT_STEAM_ID, "Alt", account_name="alt"),
        ],
    )
    roots(root)

    accounts, complete = detection.discover_steam_accounts()

    assert complete
    assert accounts == [
        detection.SteamAccount(
            steam_id=STEAM_ID,
            persona_name=PERSONA,
            account_name="mingo",
            timestamp=1690000000,
        ),
        detection.SteamAccount(
            steam_id=ALT_STEAM_ID,
            persona_name="Alt",
            account_name="alt",
            timestamp=1690000000,
        ),
    ]


def test_a_signed_out_steam_has_no_accounts_and_is_still_complete(roots, tmp_path):
    """An empty account list is an answer, not a failure."""
    root = tmp_path / "Steam"
    _write_login_users(root, [])
    roots(root)

    assert detection.discover_steam_accounts() == ([], True)


def test_no_file_on_any_root_has_no_accounts_and_is_still_complete(roots, tmp_path):
    roots(tmp_path / "Steam", tmp_path / "OtherSteam")

    assert detection.discover_steam_accounts() == ([], True)


def test_no_steam_at_all_has_no_accounts(roots):
    roots()

    assert detection.discover_steam_accounts() == ([], True)


def test_accounts_merge_across_roots_keeping_the_newest_persona(roots, tmp_path):
    """Both registry views can name different installs, one of them stale."""
    stale_root = tmp_path / "Steam"
    active_root = tmp_path / "D" / "Steam"
    _write_login_users(
        stale_root,
        [_account_block(STEAM_ID, "OldName", timestamp=1600000000)],
    )
    _write_login_users(
        active_root,
        [
            _account_block(STEAM_ID, "NewName", timestamp=1700000000),
            _account_block(ALT_STEAM_ID, "Alt", timestamp=1650000000),
        ],
    )
    roots(stale_root, active_root)

    accounts, complete = detection.discover_steam_accounts()

    assert complete
    assert [(account.steam_id, account.persona_name) for account in accounts] == [
        (STEAM_ID, "NewName"),
        (ALT_STEAM_ID, "Alt"),
    ]


def test_a_newer_entry_does_not_lose_to_a_later_root(roots, tmp_path):
    """Merge order must not decide the winner; the timestamp does."""
    fresh_root = tmp_path / "Steam"
    stale_root = tmp_path / "D" / "Steam"
    _write_login_users(
        fresh_root,
        [_account_block(STEAM_ID, "NewName", timestamp=1700000000)],
    )
    _write_login_users(
        stale_root,
        [_account_block(STEAM_ID, "OldName", timestamp=1600000000)],
    )
    roots(fresh_root, stale_root)

    accounts, _complete = detection.discover_steam_accounts()

    assert [account.persona_name for account in accounts] == ["NewName"]


def test_one_root_reached_two_ways_is_read_once(roots, tmp_path):
    """Two registry spellings of one install must not double its accounts."""
    root = tmp_path / "Steam"
    _write_login_users(root, [_account_block(STEAM_ID, PERSONA)])
    roots(root, str(root).replace("\\", "/"))

    accounts, complete = detection.discover_steam_accounts()

    assert complete
    assert [account.steam_id for account in accounts] == [STEAM_ID]


def test_an_unreadable_file_warns_and_marks_discovery_incomplete(
    roots,
    tmp_path,
    caplog,
):
    root = tmp_path / "Steam"
    # A directory where the file belongs: read_text raises an OSError subclass,
    # standing in for any unreadable account list.
    (root / "config" / "loginusers.vdf").mkdir(parents=True)
    roots(root)

    with caplog.at_level(logging.WARNING):
        accounts, complete = detection.discover_steam_accounts()

    assert accounts == []
    assert not complete
    assert "Could not read" in caplog.text


def test_a_file_in_an_unknown_format_is_not_read_as_an_empty_list(
    roots,
    tmp_path,
    caplog,
):
    """Reporting no accounts is a claim; an unknown format cannot make it."""
    root = tmp_path / "Steam"
    path = root / "config" / "loginusers.vdf"
    path.parent.mkdir(parents=True)
    path.write_text("this is not a vdf file\n", encoding="utf-8")
    roots(root)

    with caplog.at_level(logging.WARNING):
        accounts, complete = detection.discover_steam_accounts()

    assert accounts == []
    assert not complete
    assert "does not look like a Steam account list" in caplog.text


def test_an_account_without_a_persona_cannot_be_probed_and_is_not_hidden(
    roots,
    tmp_path,
    caplog,
):
    root = tmp_path / "Steam"
    _write_login_users(
        root,
        [
            _account_block(STEAM_ID, PERSONA),
            f'\t"{ALT_STEAM_ID}"\n\t{{\n\t\t"AccountName"\t\t"alt"\n\t}}',
        ],
    )
    roots(root)

    with caplog.at_level(logging.WARNING):
        accounts, complete = detection.discover_steam_accounts()

    assert [account.steam_id for account in accounts] == [STEAM_ID]
    assert not complete
    assert "Skipped 1 unreadable account entry" in caplog.text


def test_a_persona_with_quotes_and_unicode_is_parsed(roots, tmp_path):
    root = tmp_path / "Steam"
    _write_login_users(root, [_account_block(STEAM_ID, 'Ming\\"o ✿ 日本')])
    roots(root)

    accounts, complete = detection.discover_steam_accounts()

    assert complete
    assert [account.persona_name for account in accounts] == ['Ming"o ✿ 日本']


def test_an_unreadable_timestamp_loses_to_a_readable_one(roots, tmp_path):
    root = tmp_path / "Steam"
    other_root = tmp_path / "D" / "Steam"
    undated = (
        f'\t"{STEAM_ID}"\n\t{{\n\t\t"PersonaName"\t\t"Undated"\n'
        '\t\t"Timestamp"\t\t"not-a-number"\n\t}'
    )
    _write_login_users(root, [undated])
    _write_login_users(
        other_root,
        [_account_block(STEAM_ID, "Dated", timestamp=1600000000)],
    )
    roots(root, other_root)

    accounts, _complete = detection.discover_steam_accounts()

    assert [account.persona_name for account in accounts] == ["Dated"]


def test_three_local_accounts_collapse_to_the_one_that_verifies(
    roots,
    tmp_path,
    profiles,
):
    """The live-probed shape on the dev machine: one hit, two confirmed absent."""
    root = tmp_path / "Steam"
    _write_login_users(
        root,
        [
            _account_block("76561198000000003", "AltOne"),
            _account_block(STEAM_ID, PERSONA),
            _account_block(ALT_STEAM_ID, "AltTwo"),
        ],
    )
    roots(root)
    probed = profiles({PERSONA: _profile()})

    result = detection.detect_identity_candidates()

    assert result == detection.IdentityDetectionResult(
        candidates=(
            detection.IdentityCandidate(
                username="MingoDynasty",
                steam_id=STEAM_ID,
                persona_name=PERSONA,
                last_access="2026-07-20T12:00:00.000Z",
            ),
        ),
        unchecked_count=0,
        discovery_complete=True,
    )
    assert sorted(probed) == ["AltOne", "AltTwo", PERSONA]


def test_the_canonical_username_wins_over_the_persona_that_found_it(
    roots,
    tmp_path,
    profiles,
):
    """Persona and webapp username are distinct namespaces that often coincide."""
    root = tmp_path / "Steam"
    _write_login_users(root, [_account_block(STEAM_ID, "mingodynasty")])
    roots(root)
    profiles({"mingodynasty": _profile(username="MingoDynasty")})

    result = detection.detect_identity_candidates()

    assert [candidate.username for candidate in result.candidates] == ["MingoDynasty"]
    assert [candidate.persona_name for candidate in result.candidates] == [
        "mingodynasty"
    ]


def test_a_profile_owned_by_another_steam_id_is_discarded(roots, tmp_path, profiles):
    """A persona that names someone else's KovaaK's account is a coincidence."""
    root = tmp_path / "Steam"
    _write_login_users(root, [_account_block(STEAM_ID, PERSONA)])
    roots(root)
    profiles({PERSONA: _profile(steam_id="76561198999999999")})

    result = detection.detect_identity_candidates()

    assert result.candidates == ()
    assert result.unchecked_count == 0
    assert result.discovery_complete


def test_a_confirmed_absence_is_not_an_unchecked_account(roots, tmp_path, profiles):
    root = tmp_path / "Steam"
    _write_login_users(root, [_account_block(STEAM_ID, PERSONA)])
    roots(root)
    profiles({PERSONA: None})

    result = detection.detect_identity_candidates()

    assert result == detection.IdentityDetectionResult((), 0, True)


@pytest.mark.parametrize(
    "failure",
    [
        requests.ConnectionError("connection dropped"),
        requests.ReadTimeout("read timed out"),
        requests.HTTPError("HTTP 500"),
        ValueError("Expecting value: line 1 column 1 (char 0)"),
    ],
    ids=["connection", "timeout", "http-error", "malformed-json"],
)
def test_a_probe_that_fails_leaves_the_account_unchecked(
    roots,
    tmp_path,
    profiles,
    failure,
):
    root = tmp_path / "Steam"
    _write_login_users(root, [_account_block(STEAM_ID, PERSONA)])
    roots(root)
    profiles({PERSONA: failure})

    result = detection.detect_identity_candidates()

    assert result == detection.IdentityDetectionResult((), 1, True)


@pytest.mark.parametrize(
    "profile",
    [
        pytest.param("not an object", id="not-an-object"),
        pytest.param(
            {"webapp": {"username": "x"}, "lastAccess": "2026-07-20"}, id="no-steam-id"
        ),
        pytest.param({"steamId": STEAM_ID, "lastAccess": "2026-07-20"}, id="no-webapp"),
        pytest.param(
            {"steamId": STEAM_ID, "webapp": {}, "lastAccess": "2026-07-20"},
            id="no-username",
        ),
        pytest.param(
            {"steamId": STEAM_ID, "webapp": {"username": "x"}},
            id="no-last-access",
        ),
        pytest.param(
            {
                "steamId": STEAM_ID,
                "webapp": {"username": "x"},
                "lastAccess": "not a timestamp",
            },
            id="invalid-last-access",
        ),
    ],
)
def test_a_profile_the_pipeline_cannot_use_leaves_the_account_unchecked(
    roots,
    tmp_path,
    profiles,
    profile,
):
    """Schema drift degrades like an outage instead of claiming no match."""
    root = tmp_path / "Steam"
    _write_login_users(root, [_account_block(STEAM_ID, PERSONA)])
    roots(root)
    profiles({PERSONA: profile})

    result = detection.detect_identity_candidates()

    assert result == detection.IdentityDetectionResult((), 1, True)


def test_candidates_are_ranked_by_last_access_newest_first(roots, tmp_path, profiles):
    root = tmp_path / "Steam"
    _write_login_users(
        root,
        [
            _account_block(STEAM_ID, "Older"),
            _account_block(ALT_STEAM_ID, "Newer"),
        ],
    )
    roots(root)
    profiles(
        {
            "Older": _profile(
                steam_id=STEAM_ID,
                username="Older",
                last_access="2026-01-02T03:04:05.000Z",
            ),
            "Newer": _profile(
                steam_id=ALT_STEAM_ID,
                username="Newer",
                last_access="2026-07-20T12:00:00.000Z",
            ),
        }
    )

    result = detection.detect_identity_candidates()

    assert [candidate.username for candidate in result.candidates] == [
        "Newer",
        "Older",
    ]


def test_one_persona_shared_by_two_accounts_is_probed_once(roots, tmp_path, profiles):
    """The profile's steamId decides which account it verifies, if any."""
    root = tmp_path / "Steam"
    _write_login_users(
        root,
        [
            _account_block(STEAM_ID, PERSONA),
            _account_block(ALT_STEAM_ID, PERSONA),
        ],
    )
    roots(root)
    probed = profiles({PERSONA: _profile(steam_id=ALT_STEAM_ID)})

    result = detection.detect_identity_candidates()

    assert probed == [PERSONA]
    assert [candidate.steam_id for candidate in result.candidates] == [ALT_STEAM_ID]


def test_incomplete_discovery_survives_into_the_result(roots, tmp_path, profiles):
    """A verified pair from a partial account list is not a conclusive answer."""
    readable_root = tmp_path / "Steam"
    broken_root = tmp_path / "D" / "Steam"
    _write_login_users(readable_root, [_account_block(STEAM_ID, PERSONA)])
    (broken_root / "config" / "loginusers.vdf").mkdir(parents=True)
    roots(readable_root, broken_root)
    profiles({PERSONA: _profile()})

    result = detection.detect_identity_candidates()

    assert len(result.candidates) == 1
    assert not result.discovery_complete


def test_no_persona_reaches_the_log(roots, tmp_path, profiles, caplog):
    """debug.log ships with bug reports; probed personas never appear in it."""
    root = tmp_path / "Steam"
    _write_login_users(
        root,
        [
            _account_block(STEAM_ID, "VerifiedPersona"),
            _account_block(ALT_STEAM_ID, "AbsentPersona"),
            _account_block("76561198000000003", "UnreachablePersona"),
            _account_block("76561198000000004", "DriftedPersona"),
        ],
    )
    roots(root)
    profiles(
        {
            "VerifiedPersona": _profile(),
            "AbsentPersona": None,
            "UnreachablePersona": requests.ConnectionError(
                "HTTPSConnectionPool(host='kovaaks.com', port=443): Max retries "
                "exceeded with url: /webapp-backend/user/profile/by-username"
                "?username=UnreachablePersona (Caused by NewConnectionError())"
            ),
            "DriftedPersona": {"steamId": "76561198000000004"},
        }
    )

    with caplog.at_level(logging.DEBUG):
        result = detection.detect_identity_candidates()

    assert result.unchecked_count == 2
    logged = "\n".join(record.getMessage() for record in caplog.records)
    for persona in (
        "VerifiedPersona",
        "AbsentPersona",
        "UnreachablePersona",
        "DriftedPersona",
    ):
        assert persona not in logged
    # The lines still say which account failed, by position.
    assert "3 of 4" in logged
