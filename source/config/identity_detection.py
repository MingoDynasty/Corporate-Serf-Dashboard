"""Find the KovaaK's identity behind this machine's Steam accounts.

Steam records every account that has signed in on this machine in
``<root>/config/loginusers.vdf``: a SteamID64 and the persona name that went
with it. KovaaK's webapp usernames live server-side only and there is no
reverse lookup from a Steam ID, so detection has to work the other way round --
guess with each persona, then verify. A persona that resolves to a profile
whose ``steamId`` equals that account's ID64 is a tested fact; a persona that
merely happens to name someone else's KovaaK's account is a coincidence, and
the equality check is what tells the two apart.

Every Steam root the registry knows about is read, not just the first: the
32-bit and 64-bit views can point at different installs, and neither is
guaranteed to be the active client. Accounts merge across those files and
deduplicate by SteamID64, keeping the newest ``Timestamp`` -- the most recently
used client holds the freshest persona.

Nothing here is fatal and nothing here writes. No Steam, no file, or no
accounts is an ordinary zero-candidate answer; a file that exists and cannot be
used marks discovery incomplete, which is a different fact from reading cleanly
and finding nobody. Probe failures and unusable payloads are counted rather
than raised, so schema drift degrades exactly like an outage. The caller (the
settings page's Detect button) is the only thing that decides what to do with
the result -- these are pure functions, never called at import or startup.

The persona names probed here belong to accounts the user may never save,
including other people's on a shared machine, so they must not reach
``data/logs/debug.log``: the API call marks itself sensitive, and the log lines
below name counts and positions only.
"""

import logging
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import requests

from source.config.stats_dir_detection import _steam_roots
from source.kovaaks.api_service import get_user_profile_by_username
from source.kovaaks.request_logging import request_exception_summary

logger = logging.getLogger(__name__)

_LOGIN_USERS_SUBPATH = Path("config/loginusers.vdf")

# A SteamID64 as both Steam's files and KovaaK's spell it: 17 digits. ASCII
# only -- ``\d`` would otherwise accept digit forms no endpoint would take.
_STEAM_ID64 = r"\d{17}"
_STEAM_ID64_PATTERN = re.compile(_STEAM_ID64, re.ASCII)
# One account block: a SteamID64 key followed by its brace-delimited body. The
# bodies hold no nested braces, so excluding braces from the body keeps one
# malformed block from swallowing the next. Regex rather than a real parser,
# like the stats-directory detector: the upstream ``vdf`` package is
# unmaintained, and this file is read once per Detect press.
#
# The key pattern requires the opening brace as well, so it counts only what is
# syntactically an account key: a 17-digit *value* (a numeric persona or
# account name is legal) must not read as an account the block scan missed.
_ACCOUNT_KEY_PATTERN = re.compile(rf'"{_STEAM_ID64}"\s*\{{', re.ASCII)
_ACCOUNT_BLOCK_PATTERN = re.compile(rf'"({_STEAM_ID64})"\s*\{{([^{{}}]*)\}}', re.ASCII)
# A file with no users section at all is a format we do not recognize, which
# must not read as "nobody is signed in".
_USERS_SECTION_PATTERN = re.compile(r'"users"\s*\{', re.IGNORECASE)
# VDF escapes backslashes and quotes inside values, so a persona may legally
# carry an escaped quote.
_VDF_STRING = r'"((?:[^"\\]|\\.)*)"'
_VDF_ESCAPE_PATTERN = re.compile(r"\\(.)")


@dataclass(frozen=True)
class SteamAccount:
    """One local Steam account, as ``loginusers.vdf`` describes it."""

    steam_id: str
    persona_name: str
    account_name: str
    timestamp: int


@dataclass(frozen=True)
class IdentityCandidate:
    """One local Steam account with a verified KovaaK's profile.

    ``username`` is the profile's canonical ``webapp.username``, never the
    persona that found it: the two are distinct namespaces that merely often
    coincide, and only the canonical spelling works against the rest of the
    API. ``persona_name`` and ``last_access`` are display metadata.
    """

    username: str
    steam_id: str
    persona_name: str
    last_access: str


@dataclass(frozen=True)
class IdentityDetectionResult:
    """What one detection run learned. Consumed by the settings page.

    ``candidates`` are verified pairs, newest ``lastAccess`` first.
    ``unchecked_count`` counts accounts whose KovaaK's profile could not be
    established either way -- a transport failure, an unexpected status, or a
    2xx payload the pipeline cannot use. ``discovery_complete`` is False when
    an account list existed on disk and could not be read or understood.

    Both failure facts exist so the UI can refuse to present an incomplete
    result as a conclusive one: a sole candidate from a run with anything
    unresolved could be hiding a second answer.
    """

    candidates: tuple[IdentityCandidate, ...]
    unchecked_count: int
    discovery_complete: bool


@dataclass(frozen=True)
class _Probe:
    """One persona's answer from KovaaK's, cached so duplicates probe once."""

    checked: bool
    profile: object | None


def _unescape(value: str) -> str:
    """Undo the VDF escapes inside one quoted value."""
    return _VDF_ESCAPE_PATTERN.sub(r"\1", value)


def _block_value(block: str, key: str) -> str | None:
    """Read one key out of an account block, or None when it is not there."""
    match = re.search(rf'"{key}"\s*{_VDF_STRING}', block)
    return None if match is None else _unescape(match.group(1))


def _parse_accounts(text: str) -> tuple[list[SteamAccount], int]:
    """List the accounts one ``loginusers.vdf`` describes, and the unusable ones.

    Two things make an account unusable: a block with no persona name, which
    cannot be probed, and a SteamID64 whose block did not parse at all -- a
    file caught half-written, or a value carrying a brace. Both are counted
    rather than dropped, because the count is what marks discovery incomplete:
    an account nobody could read must not pass for an account that is not
    there.
    """
    accounts = []
    unusable = 0
    for match in _ACCOUNT_BLOCK_PATTERN.finditer(text):
        steam_id, block = match.group(1), match.group(2)
        persona_name = _block_value(block, "PersonaName")
        if not persona_name:
            unusable += 1
            continue
        raw_timestamp = _block_value(block, "Timestamp") or ""
        accounts.append(
            SteamAccount(
                steam_id=steam_id,
                persona_name=persona_name,
                account_name=_block_value(block, "AccountName") or "",
                # Tie-break material only: an unreadable timestamp loses to any
                # readable one rather than failing the account.
                timestamp=int(raw_timestamp) if raw_timestamp.isdigit() else 0,
            )
        )
    # Every account opens with exactly one SteamID64 key, so a key the block
    # scan did not consume is an account this file failed to describe. Counting
    # the difference is what keeps an unmatched block from vanishing into a
    # file that then looks cleanly read.
    unmatched = len(_ACCOUNT_KEY_PATTERN.findall(text)) - len(accounts) - unusable
    return accounts, unusable + max(unmatched, 0)


def _read_login_users(path: Path) -> tuple[list[SteamAccount], bool]:
    """Read one root's account list, reporting whether it could be understood."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        # A root whose Steam never signed anyone in, or no Steam at all.
        return [], True
    except OSError, UnicodeDecodeError:
        logger.warning("Could not read %s; skipping it.", path, exc_info=True)
        return [], False

    if _USERS_SECTION_PATTERN.search(text) is None:
        logger.warning(
            "%s does not look like a Steam account list; skipping it.",
            path,
        )
        return [], False

    accounts, unusable = _parse_accounts(text)
    if unusable:
        logger.warning(
            "Skipped %d unreadable account entr%s in %s.",
            unusable,
            "y" if unusable == 1 else "ies",
            path,
        )
    return accounts, not unusable


def discover_steam_accounts() -> tuple[list[SteamAccount], bool]:
    """Collect this machine's Steam accounts, and whether discovery was complete.

    Accounts are merged across every root's file and deduplicated by SteamID64,
    keeping the entry with the newest ``Timestamp``. Order is first-seen, which
    only decides probe order -- the result is ranked by the profiles instead.
    """
    merged: dict[str, SteamAccount] = {}
    complete = True
    seen_files = set()
    for root in _steam_roots():
        path = Path(root) / _LOGIN_USERS_SUBPATH
        # Two registry spellings of one install name the same file; read it once.
        key = os.path.normcase(os.path.normpath(path))
        if key in seen_files:
            continue
        seen_files.add(key)

        accounts, readable = _read_login_users(path)
        complete = complete and readable
        for account in accounts:
            existing = merged.get(account.steam_id)
            if existing is None or account.timestamp > existing.timestamp:
                merged[account.steam_id] = account
    return list(merged.values()), complete


def _profile_candidate(
    profile: object,
    account: SteamAccount,
) -> tuple[IdentityCandidate, datetime]:
    """Build the candidate one profile payload describes, with its sort key.

    Raises ``ValueError`` when the payload is missing anything the pipeline
    needs, which the caller counts as unchecked.
    """
    if not isinstance(profile, dict):
        raise ValueError("profile response was not an object")

    steam_id = profile.get("steamId")
    # The shape KovaaK's documents and returns live: a 17-digit string. Nothing
    # else may reach the equality check below, because a value that cannot be
    # a SteamID64 is schema drift, and drift must count as unchecked rather
    # than clear an account as "belongs to somebody else". A JSON *number* is
    # rejected for the same reason rather than coerced: 17 digits do not
    # survive a float round-trip, so a numeric ID could arrive already wrong
    # and would then read as a confident mismatch.
    if not isinstance(steam_id, str) or not _STEAM_ID64_PATTERN.fullmatch(steam_id):
        raise ValueError("profile response has no usable steamId")

    webapp = profile.get("webapp")
    username = webapp.get("username") if isinstance(webapp, dict) else None
    if not isinstance(username, str) or not username.strip():
        raise ValueError("profile response has no usable webapp username")

    last_access = profile.get("lastAccess")
    parsed_last_access = (
        _parse_last_access(last_access) if isinstance(last_access, str) else None
    )
    if not isinstance(last_access, str) or parsed_last_access is None:
        raise ValueError("profile response has no usable lastAccess")

    return (
        IdentityCandidate(
            username=username,
            steam_id=steam_id,
            persona_name=account.persona_name,
            last_access=last_access,
        ),
        parsed_last_access,
    )


def _parse_last_access(last_access: str) -> datetime | None:
    """Read one profile's last-access stamp, or None when it is not a stamp."""
    try:
        parsed = datetime.fromisoformat(last_access)
    except ValueError:
        return None
    # KovaaK's sends UTC stamps; a naive one still has to sort against them.
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _probe_persona(persona_name: str, position: str) -> _Probe:
    """Ask KovaaK's about one persona, turning every failure into a fact.

    ``position`` names the account by its place in the list ("2 of 3"): the
    persona itself must not reach the log.
    """
    try:
        profile = get_user_profile_by_username(persona_name)
    except requests.RequestException as exc:
        logger.warning(
            "Could not check Steam account %s against KovaaK's: %s",
            position,
            request_exception_summary(exc, redact_query=True),
        )
        return _Probe(checked=False, profile=None)
    except ValueError:
        logger.warning(
            "KovaaK's returned an unreadable profile for Steam account %s.",
            position,
        )
        return _Probe(checked=False, profile=None)
    return _Probe(checked=True, profile=profile)


def detect_identity_candidates() -> IdentityDetectionResult:
    """Verify this machine's Steam accounts against KovaaK's profiles.

    Probes run sequentially -- one to three accounts, behind an explicit user
    action -- and once per distinct persona: the profile's ``steamId`` decides
    which account it belongs to, if any.
    """
    accounts, discovery_complete = discover_steam_accounts()
    logger.info(
        "Checking %d local Steam account(s) against KovaaK's profiles.",
        len(accounts),
    )

    probes: dict[str, _Probe] = {}
    ranked: list[tuple[datetime, IdentityCandidate]] = []
    unchecked = 0
    for index, account in enumerate(accounts, start=1):
        position = f"{index} of {len(accounts)}"
        probe = probes.get(account.persona_name)
        if probe is None:
            probe = _probe_persona(account.persona_name, position)
            probes[account.persona_name] = probe

        if not probe.checked:
            unchecked += 1
            continue
        if probe.profile is None:
            logger.debug("Steam account %s has no KovaaK's profile.", position)
            continue

        try:
            candidate, last_access = _profile_candidate(probe.profile, account)
        except ValueError as exc:
            logger.warning(
                "Could not use the KovaaK's profile for Steam account %s: %s",
                position,
                exc,
            )
            unchecked += 1
            continue

        if candidate.steam_id != account.steam_id:
            # The persona names a KovaaK's account belonging to someone else.
            logger.debug(
                "Steam account %s matched a profile owned by another Steam ID.",
                position,
            )
            continue

        ranked.append((last_access, candidate))

    ranked.sort(key=lambda entry: entry[0], reverse=True)
    logger.info(
        "Identity detection found %d verified account(s); %d unchecked, "
        "account discovery %s.",
        len(ranked),
        unchecked,
        "complete" if discovery_complete else "incomplete",
    )
    return IdentityDetectionResult(
        candidates=tuple(candidate for _stamp, candidate in ranked),
        unchecked_count=unchecked,
        discovery_complete=discovery_complete,
    )
