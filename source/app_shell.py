"""Build the shared Dash application shell and navigation."""

import tomllib
from datetime import datetime
from typing import Any, TypedDict

import dash
import dash_mantine_components as dmc
from dash import (
    Input,
    Output,
    State,
    callback,
    clientside_callback,
    dcc,
    html,
    no_update,
)
from pydantic import ValidationError

from source.components.local_icon import local_icon
from source.config.config_service import ConfigData, get_config
from source.kovaaks.pace import percent_faster
from source.kovaaks.playlist_scenarios_service import scenario_run_history_href
from source.my_queue.message_queue import NewFileMessage, message_queue
from source.utilities.notifications import (
    CELEBRATION_CHANNEL,
    NOTIFICATION_CONTAINER_ID,
    RUN_VERDICT_CHANNEL,
    TOAST_CHANNEL_REGISTRY_STORE_ID,
    channel_toasts,
    toast,
)

# The batch the shell's drain publishes for every page, and the interval that
# drives it. Both live in the shell because the drain is app-wide: a run is
# worth announcing whatever page happens to be open.
RUN_EVENTS_BATCH_STORE_ID = "run-events-batch"
PB_CELEBRATION_INTERVAL_ID = "pb-celebration-interval"

# The celebration setting itself: one browser-local string, "off" or a style
# name. It is the authoritative value rather than a mirror of the Settings
# control, so the control initializes from it and writes to it and carries no
# persistence of its own. Shell-hosted because both readers are here -- the
# drain and the animation -- and because the setting is app-wide.
PB_CELEBRATION_STYLE_STORE_ID = "pb-celebration-style"
CELEBRATION_STYLE_OFF = "off"
CELEBRATION_STYLE_CONFETTI = "confetti"
# Only the exact off value silences the celebration. Every other reading of the
# store -- a value this build does not know, a browser that cleared its site
# data -- falls through to celebrating, which is the direction browser-local
# storage should fail in.
DEFAULT_CELEBRATION_STYLE = CELEBRATION_STYLE_CONFETTI

# The Run notifications setting: one browser-local string, on or off. Like
# the celebration style it is the authoritative value and not a mirror of the
# Settings switch, and it is here because the drain reads it on every page.
# Only the exact off value silences the run toast, for the same reason. The
# browser stores the value under this id, so changing the id or the off value
# turns run toasts back on for everyone who had turned them off.
RUN_NOTIFICATIONS_STORE_ID = "run-notifications"
RUN_NOTIFICATIONS_ON = "on"
RUN_NOTIFICATIONS_OFF = "off"

# The stylesheet draws the link in a run toast as the app draws a link.
RUN_TOAST_LINK_CLASS = "run-toast-link"

# A clientside callback needs an output, and the animation has nothing to
# write: this store is that output and never holds anything.
PB_CELEBRATION_SIGNAL_STORE_ID = "pb-celebration-signal"

# How much older than one delivery a run may be and still count as news.
# Freshness needs no drain bookkeeping -- every drain empties the queue, so a
# message a drain finds was never seen by an earlier one -- and this wall-clock
# cap is all that remains. It sits two orders of magnitude above the default
# poll interval and comfortably above Chromium's intensive throttling, which
# slows an interval in a tab hidden over five minutes to one tick per minute
# (https://developer.chrome.com/blog/timer-throttling-in-chrome-88); a tab can
# stay hidden through a whole session, minimized or behind another tab, so a
# tighter window would drop the mid-session personal bests this exists for. It
# also bounds replay: a queue that accumulated with no tab open announces
# nothing older than the window on the next visit.
RUN_EVENT_FRESHNESS_CAP_SECONDS = 120

APP_INDEX_STRING = """<!DOCTYPE html>
<html lang="en">
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        <script>
            (() => {
                const colorSchemeKey = "mantine-color-scheme-value";
                const legacySwitchKey =
                    "_dash_persistence.color-scheme-switch.checked.true";
                let colorScheme = "light";

                try {
                    const storedColorScheme =
                        window.localStorage.getItem(colorSchemeKey);

                    if (
                        storedColorScheme === "dark" ||
                        storedColorScheme === "light"
                    ) {
                        colorScheme = storedColorScheme;
                    } else {
                        const persistedSwitch = JSON.parse(
                            window.localStorage.getItem(legacySwitchKey)
                        );
                        colorScheme =
                            Array.isArray(persistedSwitch) &&
                            persistedSwitch[0] === true
                                ? "dark"
                                : "light";
                        window.localStorage.setItem(
                            colorSchemeKey,
                            colorScheme
                        );
                    }
                    window.localStorage.removeItem(legacySwitchKey);
                } catch (_error) {
                    // Local storage can be unavailable; light is the safe default.
                }

                document.documentElement.setAttribute(
                    "data-mantine-color-scheme",
                    colorScheme
                );
            })();
        </script>
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
"""


class RunEventData(TypedDict):
    """One drained run, as JSON-safe facts plus the drain's liveness stamp."""

    run_id: str
    scenario_name: str
    sensitivity: str
    score: float
    scenario_previous_best: float | None
    pace_constant: float | None
    is_new_sensitivity: bool
    is_live: bool


class RunEventBatch(TypedDict):
    """One drain's runs, in order, with the decision the drain made on them."""

    runs: list[RunEventData]
    celebrated_run_id: str | None
    animation_sequence: int


def _drain_interval_ms() -> int:
    """Return the drain's poll period without making a bad config fatal here.

    This layout is built while ``source.app`` is imported, which is before
    startup validates the config file and exits with one actionable line. A
    config problem has to reach that path, not surface as an import traceback,
    so an unloadable file falls back to the field's own default and startup
    reports it a moment later.
    """
    try:
        return get_config().polling_interval
    except OSError, UnicodeDecodeError, tomllib.TOMLDecodeError, ValidationError:
        return ConfigData.polling_interval


def _run_event_freshness_seconds() -> float:
    """Return the freshness window: the cap plus one poll period.

    A run can be a whole poll period old through nothing but the drain's
    cadence, so a window shorter than that period would stamp every run stale
    and silently retire the toasts liveness gates. Adding the period says what
    the cap means -- how much staleness is tolerated *beyond* one delivery --
    and leaves the default 1000 ms interval at an indistinguishable 121 s.
    """
    return RUN_EVENT_FRESHNESS_CAP_SECONDS + _drain_interval_ms() / 1000


def _run_event_data(
    message: NewFileMessage,
    now: datetime,
    freshness_seconds: float,
) -> RunEventData:
    """Project one queued message into the batch, stamping its liveness."""
    age_seconds = (now - message.datetime_created).total_seconds()
    return {
        "run_id": message.run_id,
        "scenario_name": message.scenario_name,
        "sensitivity": message.sensitivity,
        "score": message.score,
        "scenario_previous_best": message.scenario_previous_best,
        "pace_constant": message.pace_constant,
        "is_new_sensitivity": message.is_new_sensitivity,
        "is_live": age_seconds <= freshness_seconds,
    }


def _drain_message_queue(now: datetime, freshness_seconds: float) -> list[RunEventData]:
    """Empty the run-event queue into one ordered batch."""
    runs: list[RunEventData] = []
    while True:
        try:
            message = message_queue.popleft()
        except IndexError:
            return runs
        runs.append(_run_event_data(message, now, freshness_seconds))


def _celebrated_run(runs: list[RunEventData]) -> RunEventData | None:
    """Name the newest live run that beat its scenario's personal best.

    Strictly greater, so a tie never celebrates, and a scenario's first run
    (no previous best at all) only sets the baseline. An older qualifying run
    in the same batch is not named: one drain decides one celebration, because
    one response drives one animation.
    """
    for run in reversed(runs):
        previous_best = run["scenario_previous_best"]
        if (
            run["is_live"]
            and previous_best is not None
            and run["score"] > previous_best
        ):
            return run
    return None


def _celebration_toast(run: RunEventData) -> dict[str, Any]:
    """Build the personal best toast, sticky and green with a trophy.

    ``auto_close=False`` is passed explicitly because ``channel_toast`` carries
    the payload's lifetime through untouched. The celebration is a channel like
    any other -- a later personal best replaces the one on screen -- it is just
    the one channel with no timer, because the run that earned it was played in
    a fullscreen game and the news should still be there on alt-tab.
    """
    previous_best = run["scenario_previous_best"]
    # Guaranteed by _celebrated_run: a run with no previous best is never
    # celebrated, so there is always a figure to report here.
    assert previous_best is not None
    headline = f"{run['scenario_name']}: {run['score']:.2f}."
    pace_constant = run["pace_constant"]
    pace_gain = (
        percent_faster(pace_constant, previous_best, run["score"])
        if pace_constant is not None
        else None
    )
    if pace_gain is not None:
        # A time-scored run reports how much faster it finished. Its gain as a
        # percentage of the score would understate that many times over, and
        # it needs no positive previous best, only positive times.
        message = (
            f"{headline} Finished {pace_gain:.1f}% faster than your previous "
            f"best of {previous_best:.2f}."
        )
    elif previous_best > 0:
        gain = (run["score"] / previous_best - 1) * 100
        message = (
            f"{headline} Up {gain:.1f}% on your previous best of {previous_best:.2f}."
        )
    else:
        # A previous best of zero has no percentage to give and a negative one
        # would read backwards -- the same division the threshold verdict
        # declines, for the same reason.
        message = f"{headline} Your previous best was {previous_best:.2f}."
    return toast(
        CELEBRATION_CHANNEL,
        "New personal best",
        message,
        color="green",
        icon=local_icon("material-symbols:trophy"),
        auto_close=False,
    )


def _newest_live_run(runs: list[RunEventData]) -> RunEventData | None:
    """Name the batch's newest live run, the one run its toast can be about.

    A batch's other runs earn no toast of their own: one channel shows one
    toast, so theirs would be replaced in the instant they were shown.
    """
    return next((run for run in reversed(runs) if run["is_live"]), None)


def _run_toast(run: RunEventData) -> dict[str, Any]:
    """Build the plain toast for a run: its scenario, and a link to it.

    It says that the app saw the run and where to look. It carries no score
    and no verdict, which Run History shows beside the run for as long as the
    run exists.

    The link is a ``dcc.Link``. A ``dmc.Anchor`` decodes its address, which
    cuts a scenario name holding ``&`` short, and an ``html.A`` reloads the
    app, which takes the toast with it. The address names the run as well as
    the scenario, so that two runs of one scenario link to two addresses.
    """
    return toast(
        RUN_VERDICT_CHANNEL,
        "New run detected",
        [
            html.Div(run["scenario_name"]),
            dcc.Link(
                "Open in Run History",
                href=scenario_run_history_href(
                    run["scenario_name"], run_id=run["run_id"]
                ),
                className=RUN_TOAST_LINK_CLASS,
            ),
        ],
        color="blue",
        icon=local_icon("fontisto:line-chart"),
    )


def _next_animation_sequence(
    previous_batch: RunEventBatch | None,
    celebrated: RunEventData | None,
) -> int:
    """Advance the animation sequence only when this batch celebrates.

    Monotonic so two identical personal bests back to back both play, and
    unchanged otherwise so a batch that celebrates nothing plays nothing.
    """
    previous = previous_batch["animation_sequence"] if previous_batch else 0
    return previous + 1 if celebrated is not None else previous


@callback(
    Output(RUN_EVENTS_BATCH_STORE_ID, "data"),
    Output(NOTIFICATION_CONTAINER_ID, "sendNotifications", allow_duplicate=True),
    Output(NOTIFICATION_CONTAINER_ID, "hideNotifications", allow_duplicate=True),
    Output(TOAST_CHANNEL_REGISTRY_STORE_ID, "data", allow_duplicate=True),
    Input(PB_CELEBRATION_INTERVAL_ID, "n_intervals"),
    State(RUN_EVENTS_BATCH_STORE_ID, "data"),
    State(TOAST_CHANNEL_REGISTRY_STORE_ID, "data"),
    State(PB_CELEBRATION_STYLE_STORE_ID, "data"),
    State(RUN_NOTIFICATIONS_STORE_ID, "data"),
    prevent_initial_call=True,
)
def publish_run_events(
    _n_intervals,
    previous_batch,
    toast_channels,
    celebration_style,
    run_notifications,
):
    """Drain the run-event queue and publish one batch for the whole app.

    The single consumer of ``message_queue``, and the one sender of both run
    toasts. Facts travel and only this callback decides: it stamps each run's
    liveness and names at most one celebrated run, and the pages read those
    stamps instead of re-deriving them. A page callback triggered by the batch
    store necessarily runs after this one wrote it, so there is no race to
    coordinate.

    The batch's newest live run gets the plain run toast, unless it is the
    run the celebration announces: that run keeps the celebration as its one
    toast. So one response can carry both toasts, about two different runs.
    Each rides the channel mechanism every replaceable toast uses, on its own
    channel, so a run toast lands beside a celebration and never replaces it.

    ``previous_batch`` is the batch this client last received, read for its
    animation sequence, and ``toast_channels`` is this client's channel
    registry. The two settings are this browser's. Either one set to off
    sends no toast of its kind and leaves the other alone, and the batch is
    published either way, because the page is every run's record whatever
    the settings say. Both are ``State``: changing a setting must not send a
    toast for a batch already drained.
    """
    runs = _drain_message_queue(datetime.now(), _run_event_freshness_seconds())
    if not runs:
        return no_update, no_update, no_update, no_update

    celebrated = (
        None if celebration_style == CELEBRATION_STYLE_OFF else _celebrated_run(runs)
    )
    batch: RunEventBatch = {
        "runs": runs,
        "celebrated_run_id": celebrated["run_id"] if celebrated else None,
        "animation_sequence": _next_animation_sequence(previous_batch, celebrated),
    }
    toasts = [] if celebrated is None else [_celebration_toast(celebrated)]
    newest = (
        None if run_notifications == RUN_NOTIFICATIONS_OFF else _newest_live_run(runs)
    )
    if newest is not None and newest["run_id"] != batch["celebrated_run_id"]:
        toasts.append(_run_toast(newest))
    if not toasts:
        return batch, no_update, no_update, no_update
    return batch, *channel_toasts(toasts, toast_channels)


# The animation, driven entirely in the browser: the burst is a canvas effect
# with nothing to tell the server, so a round trip here would only add latency
# to the one moment that is supposed to feel immediate. ``celebrate`` holds
# every guard -- the decision, the monotonic sequence that stops one payload
# playing twice, Off, reduced motion, and the hidden-tab hold -- in
# ``assets/pbCelebration.js``. The style is ``State``: changing the setting
# must not replay the batch already on screen.
clientside_callback(
    """
    (batch, style) => {
        if (window.pbCelebration) {
            window.pbCelebration.celebrate(batch, style);
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output(PB_CELEBRATION_SIGNAL_STORE_ID, "data"),
    Input(RUN_EVENTS_BATCH_STORE_ID, "data"),
    State(PB_CELEBRATION_STYLE_STORE_ID, "data"),
    prevent_initial_call=True,
)


discord_component = dmc.Tooltip(
    dmc.Anchor(
        local_icon(
            "logos:discord-icon",
            width=40,
        ),
        href="https://discordapp.com/users/222910150636339211",
    ),
    label="Contact me via Discord: MingoDynasty",
)


github_component = dmc.Tooltip(
    dmc.Anchor(
        local_icon("ion:logo-github", width=40),
        href="https://github.com/MingoDynasty/Corporate-Serf-Dashboard",
    ),
    # Plain again: the build identity is the settings page's to show, not a
    # thing to be found by hovering a repo link.
    label="View this app on GitHub",
)


theme_switch_component = dmc.Tooltip(
    dmc.ColorSchemeToggle(
        lightIcon=local_icon(
            "radix-icons:sun",
            width=25,
            color=dmc.DEFAULT_THEME["colors"]["yellow"][8],
        ),
        darkIcon=local_icon(
            "radix-icons:moon",
            width=25,
            color=dmc.DEFAULT_THEME["colors"]["yellow"][6],
        ),
        id="color-scheme-switch",
        color="gray",
        size="lg",
        mr="xl",
        **{"aria-label": "Switch between light and dark mode"},
    ),
    label="Switch between light and dark mode",
)


# The navbar's entries, in order: id, label, address, icon. Kept as one list
# because the callback that marks the open page writes to every link, so an
# entry added here is marked with no second edit.
NAVBAR_LINKS = (
    ("navbar-home", "Home", "/", "bi:house-door-fill"),
    ("navbar-run-history", "Run History", "/run-history", "fontisto:line-chart"),
    ("navbar-playlists", "Playlists", "/playlists", "material-symbols:playlist-play"),
    ("navbar-settings", "Settings", "/settings", "clarity:settings-line"),
)

# Read by the callback that marks the open page, and written by nothing.
NAVBAR_LOCATION_ID = "navbar-location"


def nav_link(link_id: str, label: str, href: str, icon: str) -> dmc.NavLink:
    """Build a single-anchor Dash-native navbar link."""
    return dmc.NavLink(
        id=link_id,
        label=label,
        leftSection=dmc.ThemeIcon(
            # Both sizes, so a file that is wider than tall is scaled to fit
            # the box. Sized by its height alone it hangs out of both sides.
            local_icon(icon, width=36, height=36),
            size="lg",
            variant="outline",
        ),
        href=href,
        refresh=False,
    )


# Per Dash documentation, we should include **kwargs in case the layout receives unexpected query strings.
def layout(**kwargs):  # noqa: ARG001
    """Build the shared application shell around the active Dash page."""
    return dmc.MantineProvider(
        id="mantine-provider",
        defaultColorScheme="light",
        children=[
            dmc.AppShell(
                children=[
                    dmc.NotificationContainer(id=NOTIFICATION_CONTAINER_ID),
                    dcc.Location(id=NAVBAR_LOCATION_ID, refresh=False),
                    # Beside the container on purpose: a toast outlives the
                    # page that emitted it, so the registry that knows which
                    # instance to replace has to outlive it too. The shell's
                    # own two channels are written from here as well.
                    dcc.Store(id=TOAST_CHANNEL_REGISTRY_STORE_ID, data={}),
                    # The app-wide run-event channel. The drain and its batch
                    # live here rather than on Run History so a run reaches
                    # the screen whatever page is open; that page listens to
                    # the store instead of popping the queue.
                    dcc.Store(id=RUN_EVENTS_BATCH_STORE_ID),
                    # The celebration setting, and the output the animation's
                    # clientside callback needs but never writes. The setting
                    # is browser-local rather than a key in the app's settings
                    # store: a cosmetic preference should not be the thing
                    # that forces that file's first schema migration.
                    dcc.Store(
                        id=PB_CELEBRATION_STYLE_STORE_ID,
                        storage_type="local",
                        data=DEFAULT_CELEBRATION_STYLE,
                    ),
                    dcc.Store(id=PB_CELEBRATION_SIGNAL_STORE_ID),
                    # The Run notifications setting, browser-local for the
                    # reason the celebration setting is.
                    dcc.Store(
                        id=RUN_NOTIFICATIONS_STORE_ID,
                        storage_type="local",
                        data=RUN_NOTIFICATIONS_ON,
                    ),
                    dcc.Interval(
                        id=PB_CELEBRATION_INTERVAL_ID,
                        interval=_drain_interval_ms(),
                        n_intervals=0,
                    ),
                    dmc.AppShellHeader(
                        dmc.Grid(
                            children=[
                                dmc.GridCol(
                                    dmc.Group(
                                        children=[
                                            dmc.Burger(
                                                id="burger",
                                                size="sm",
                                                opened=True,
                                                persisted_props=["opened"],
                                                persistence=True,
                                                persistence_type="local",
                                                **{
                                                    "aria-label": "Show or hide navigation"
                                                },
                                            ),
                                            dmc.Anchor(
                                                children=[
                                                    dmc.Title(
                                                        "Corporate Serf Dashboard",
                                                        className="app-header-title",
                                                    ),
                                                ],
                                                href="/",
                                                target="_self",
                                                underline="never",
                                                className="app-header-title-anchor",
                                            ),
                                        ],
                                        h="100%",
                                        px="md",
                                        wrap="nowrap",
                                    ),
                                    className="app-header-title-col",
                                    span="auto",
                                ),
                                dmc.GridCol(
                                    dmc.Group(
                                        children=[
                                            discord_component,
                                            github_component,
                                            theme_switch_component,
                                        ],
                                        h="100%",
                                        px="md",
                                        justify="flex-end",
                                        wrap="nowrap",
                                    ),
                                    span="content",
                                ),
                            ],
                        ),
                        pt="0.5em",
                    ),
                    dmc.AppShellNavbar(
                        id="navbar",
                        children=[nav_link(*entry) for entry in NAVBAR_LINKS],
                        p="md",
                    ),
                    dmc.AppShellMain(dash.page_container),
                ],
                header={"height": "4em"},
                padding="md",
                navbar={
                    "width": 225,
                    "breakpoint": "sm",
                    # Mirrors the burger's `opened` default. The clientside
                    # callback below derives this from the burger on every
                    # load, so a mismatch here would paint the navbar
                    # collapsed for a frame before the callback opens it.
                    "collapsed": {
                        "mobile": False,
                        "desktop": False,
                    },
                },
                id="appshell",
            ),
        ],
    )


clientside_callback(
    """
    (opened, navbar) => ({
        ...navbar,
        collapsed: {
            mobile: !opened,
            desktop: !opened,
        },
    })
    """,
    Output("appshell", "navbar"),
    Input("burger", "opened"),
    State("appshell", "navbar"),
)


# Marks the open page. ``aria-current`` is the whole mechanism: a screen
# reader announces it, and the bundled Mantine stylesheet draws a link that
# carries it exactly as it draws an active one. The component's own ``active``
# matching looks like the simpler way and is left unset on purpose: it draws
# the same mark but never sets the attribute, so a second matcher would be
# needed for the attribute, and the two could disagree where nobody looking
# at the screen would see it. A link is marked when the address is its own or
# lies under it, which keeps Playlists marked on a playlist's scenario table.
# The addresses come from the links themselves, so none is written twice.
clientside_callback(
    """
    (pathname, ...hrefs) => {
        // The router serves a page with or without a trailing slash.
        const path =
            pathname.length > 1 && pathname.endsWith("/")
                ? pathname.slice(0, -1)
                : pathname;
        return hrefs.map((href) =>
            path === href || path.startsWith(href + "/") ? "page" : null
        );
    }
    """,
    [Output(link_id, "aria-current") for link_id, *_ in NAVBAR_LINKS],
    Input(NAVBAR_LOCATION_ID, "pathname"),
    [State(link_id, "href") for link_id, *_ in NAVBAR_LINKS],
)
