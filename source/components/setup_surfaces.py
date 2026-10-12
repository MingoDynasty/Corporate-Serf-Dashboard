"""Build the setup card and the stats-folder hint for a page that hosts them.

The two surfaces explain why a page has no runs to show. The card speaks for
a setting that was never written, or for a settings file the app cannot read.
The hint speaks for a stats folder that is set and cannot be used. A page
puts ``stats_dir_hint`` and a container holding ``setup_card_children`` in its
layout. Nothing here registers a callback: the Skip button is answered by the
page that offers it.
"""

import dash_mantine_components as dmc

from source.components.local_icon import local_icon
from source.config.settings_service import (
    KOVAAKS_USERNAME_KEY,
    STATS_DIR_KEY,
    get_settings,
    get_settings_store_state,
    get_usable_stats_dir,
    is_stats_dir_change_pending,
)
from source.utilities.store_schema import StoreState

SETUP_CARD_SKIP_ID = "setup-card-skip"
SETUP_CARD_IDENTITY_TITLE = "Add your KovaaK's account"
SETUP_CARD_IDENTITY_BODY = (
    "See your leaderboard position and percentiles for every scenario."
)
SETUP_CARD_SKIP_FINE_PRINT = (
    "Skipping keeps position lookups off. You can add your username anytime in "
    "Settings."
)
SETUP_CARD_STATS_DIR_TITLE = "Finish setting up"
SETUP_CARD_STATS_DIR_BODY = (
    "No KovaaK's stats folder was found, so this app can't read your runs yet. "
    "Set it in Settings."
)
# Shown when the settings file exists but cannot be used. The key-absence
# states below cannot speak for it: an unusable store reads as no keys at all,
# so they would claim a fresh install when a configured one is sitting on disk.
SETUP_CARD_STORE_TITLE = "Your settings can't be read"
SETUP_CARD_STORE_BODY = (
    "A settings file exists, but this version of the app can't use it, so the "
    "app started without your settings. Open Settings to see what's wrong and "
    "how to fix it."
)
SETUP_CARD_OPEN_SETTINGS_LABEL = "Open Settings"
SETUP_CARD_SKIP_LABEL = "Skip"
# The primary action navigates, so it ships as one link wearing the button's
# styling. A ``dmc.Button`` inside a ``dmc.Anchor`` renders a focusable
# ``<button>`` inside a focusable ``<a>``: two tab stops with the same name,
# and interactive content nested where HTML does not allow it. Mantine's own
# escape hatch (``component="a"``) is not exposed by the dmc 2.8.0 wrapper, so
# the styling lives in ``assets/stylesheet.css`` instead.
SETUP_CARD_CTA_CLASS = "setup-card-cta"
# The card wears the shared alert anatomy on the ``dmc.Paper`` it already is.
# Blue is the informational default; the caution modifier swaps in the yellow
# tokens for the stats-folder state, which blocks every plot on the page and
# cannot be dismissed.
SETUP_CARD_CLASS = "alert-panel setup-card"
SETUP_CARD_CAUTION_CLASS = f"{SETUP_CARD_CLASS} alert-panel-caution"
SETUP_CARD_CAUTION_ICON = "material-symbols:warning-outline"
SETUP_CARD_INFO_ICON = "material-symbols:info-outline"
# The stats-folder hint wears the caution panel in both of its branches: each
# one leaves every plot on the page empty, the same reason the card's
# stats-folder state is yellow.
STATS_DIR_HINT_CLASS = "alert-panel alert-panel-caution stats-dir-hint"


def stats_dir_hint() -> list:
    """Say so, persistently, when the app booted without a stats directory.

    Unset and unusable read the same to the user, and both are repaired in the
    same place, so the hint carries one link to the settings page.

    A save this process has not applied yet is neither: a directory is
    configured, so claiming nothing is would tell the user the save failed. The
    hint defers to the restart instead, the same pin-versus-store
    reconciliation the settings page's notice derives from.

    What that branch must not do is confirm the save. It renders on every visit
    while the change is pending, so a user returning days later would be told
    they had just saved. It names the restart and what the restart applies, in
    the settings page's vocabulary: "the app", never "the dashboard", which a
    user reads as the browser page they would merely reload.

    That deferral is doubly narrow, because the restart copy carries no link
    and whatever it displaces has to be worth displacing. The pending change
    has to be to the *stats directory*: an identity change leaves the directory
    as unconfigured as it was, and no restart will configure it. And it has to
    leave one *set*: clearing the field is a pending change too -- rightly so
    for the settings page's notice, since this process serves the old directory
    until it restarts -- but what the restart would then apply is nothing
    configured, which is what the plain hint below already says, and it says it
    with the link.

    The plain hint is narrower still: it speaks only for a ``stats_dir`` key
    that *exists* and cannot be used -- deliberately emptied, or a stored path
    that has since vanished. A key that was never written is the never-asked
    case, which the setup card owns, so each condition is explained by exactly
    one surface instead of two stacked lines saying the same thing.
    """
    settings = get_settings()
    if get_usable_stats_dir() is not None:
        return []
    if is_stats_dir_change_pending() and settings.get(STATS_DIR_KEY):
        return [_stats_dir_hint_panel("Restart the app to apply your saved settings.")]
    if STATS_DIR_KEY not in settings:
        return []
    return [
        _stats_dir_hint_panel(
            [
                "No stats folder configured. Set it in ",
                dmc.Anchor("Settings", href="/settings", refresh=False),
                ".",
            ]
        )
    ]


def _stats_dir_hint_panel(sentence: str | list) -> dmc.Paper:
    """Wrap one hint sentence in the caution panel: the icon beside it, no title.

    A ``dmc.Paper`` rather than a ``dmc.Alert`` because the unconfigured
    sentence holds a link, and both branches share the one slot and its id.
    """
    return dmc.Paper(
        dmc.Group(
            [
                local_icon(SETUP_CARD_CAUTION_ICON, className="alert-panel-icon"),
                dmc.Text(sentence),
            ],
            # ``dmc.Group`` defaults to ``wrap="wrap"``, which sizes the text at
            # its one-line width and drops a sentence too wide for the space
            # beside the icon whole onto the row under it instead of wrapping it
            # there.
            wrap="nowrap",
            gap="xs",
            align="flex-start",
        ),
        className=STATS_DIR_HINT_CLASS,
        id="stats-dir-hint",
        withBorder=True,
    )


def _setup_card(
    title: str,
    body: str,
    *,
    offer_skip: bool,
    caution: bool,
) -> dmc.Paper:
    """Build one state of the setup card: a heading, a reason, and a way out.

    Navigation and dismissal only. The primary action is a link to the settings
    page, where detection and Save already live, so the card never grows a
    second detection UI and opening it costs no KovaaK's request. Skip comes
    with the fine print that says what it gives up, because a dismissal the
    user cannot interpret is worse than the question.

    The two actions are deliberately different elements: one navigates and is a
    link, the other acts on this page and is a button.

    ``caution`` picks the severity treatment rather than being read off
    ``offer_skip``: the two happen to agree today, but one is about how loud the
    card is and the other about whether it can be dismissed. It stays a
    ``dmc.Paper`` wearing the alert anatomy through CSS, because the card holds
    a link and a button and ``role="alert"`` is for text content.
    """
    actions = [
        dmc.Anchor(
            SETUP_CARD_OPEN_SETTINGS_LABEL,
            href="/settings",
            refresh=False,
            className=SETUP_CARD_CTA_CLASS,
            underline="never",
        )
    ]
    if offer_skip:
        actions.append(
            dmc.Button(
                SETUP_CARD_SKIP_LABEL,
                id=SETUP_CARD_SKIP_ID,
                # Secondary to the one action that finishes the setup.
                variant="subtle",
            )
        )
    children = [
        dmc.Group(
            [
                local_icon(
                    SETUP_CARD_CAUTION_ICON if caution else SETUP_CARD_INFO_ICON,
                    className="alert-panel-icon",
                ),
                dmc.Text(title, className="alert-panel-title"),
            ],
            gap="xs",
            align="center",
        ),
        dmc.Text(body),
        dmc.Group(actions, gap="sm"),
    ]
    if offer_skip:
        children.append(
            dmc.Text(SETUP_CARD_SKIP_FINE_PRINT, className="setup-card-fine-print")
        )
    return dmc.Paper(
        dmc.Stack(children, gap="xs"),
        className=SETUP_CARD_CAUTION_CLASS if caution else SETUP_CARD_CLASS,
        withBorder=True,
    )


def setup_card_children() -> list:
    """Ask, once, for whatever setup the app could not do on the user's behalf.

    Read from the stored view rather than the pinned accessors, and keyed on
    key *absence*: the card is the "never asked" surface, so a key that exists
    -- with any value, ``""`` included -- retires it permanently. A degraded
    setting that does exist is explained where it bites instead, by the hints
    above and beside the values it affects.

    The missing stats directory wins when both are missing: without it the app
    has nothing to plot, so it is not dismissible and the identity ask can wait
    for a page that shows something.

    Nothing renders while a saved stats-directory change is waiting on a
    restart. The user is mid-setup, the restart hint owns that moment, and
    stacking the identity ask on top of it would be two banners for one
    unfinished action. The card comes back after the restart if identity is
    still unasked.

    Key absence only means "never asked" for a store the app can read. An
    unusable one -- a hand-edited typo, or a file stamped by a newer build --
    yields no keys either, and startup detection declines to run against it, so
    the key-absence states below would report a fresh install and a search that
    never happened. That state gets its own card, which does nothing but route
    to the Settings page, where the store alert already names the real problem
    and distinguishes the two ways a store can be unusable.
    """
    if is_stats_dir_change_pending():
        return []
    if get_settings_store_state() in (StoreState.ERROR, StoreState.FUTURE):
        return [
            _setup_card(
                SETUP_CARD_STORE_TITLE,
                SETUP_CARD_STORE_BODY,
                offer_skip=False,
                caution=True,
            )
        ]
    settings = get_settings()
    if STATS_DIR_KEY not in settings:
        return [
            _setup_card(
                SETUP_CARD_STATS_DIR_TITLE,
                SETUP_CARD_STATS_DIR_BODY,
                offer_skip=False,
                caution=True,
            )
        ]
    if KOVAAKS_USERNAME_KEY not in settings:
        return [
            _setup_card(
                SETUP_CARD_IDENTITY_TITLE,
                SETUP_CARD_IDENTITY_BODY,
                offer_skip=True,
                caution=False,
            )
        ]
    return []
