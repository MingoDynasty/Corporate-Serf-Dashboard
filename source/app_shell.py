"""Build the shared Dash application shell and navigation."""

import tomllib
from datetime import datetime
from typing import Any, TypedDict

import dash
import dash_mantine_components as dmc
from dash import Input, Output, State, callback, clientside_callback, dcc, no_update
from pydantic import ValidationError

from source.components.local_icon import local_icon
from source.config.config_service import ConfigData, get_config
from source.my_queue.message_queue import NewFileMessage, message_queue
from source.utilities.notifications import (
    CELEBRATION_NOTIFICATION_ID,
    NOTIFICATION_CONTAINER_ID,
    TOAST_LIFETIME_STORE_ID,
    toast,
    upsert_sticky_toast,
)

# The batch the shell's drain publishes for every page, and the interval that
# drives it. Both live in the shell because the drain is app-wide: a personal
# best is worth announcing whatever page happens to be open.
RUN_EVENTS_BATCH_STORE_ID = "run-events-batch"
PB_CELEBRATION_INTERVAL_ID = "pb-celebration-interval"

# How old a run may be and still count as news. Freshness needs no drain
# bookkeeping -- every drain empties the queue, so a message a drain finds was
# never seen by an earlier one -- and this wall-clock cap is all that remains.
# It sits two orders of magnitude above the default poll interval and
# comfortably above Chromium's intensive throttling, which slows a hidden tab's
# interval to about one tick per minute; the tab is occluded during play, so a
# tighter window would drop the mid-session personal bests this exists for. It
# also bounds replay: a queue that accumulated with no tab open announces
# nothing older than the cap on the next visit.
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
    nth_score: int
    score: float
    scenario_previous_best: float | None
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


def _run_event_data(message: NewFileMessage, now: datetime) -> RunEventData:
    """Project one queued message into the batch, stamping its liveness."""
    age_seconds = (now - message.datetime_created).total_seconds()
    return {
        "run_id": message.run_id,
        "scenario_name": message.scenario_name,
        "sensitivity": message.sensitivity,
        "nth_score": message.nth_score,
        "score": message.score,
        "scenario_previous_best": message.scenario_previous_best,
        "is_new_sensitivity": message.is_new_sensitivity,
        "is_live": age_seconds <= RUN_EVENT_FRESHNESS_CAP_SECONDS,
    }


def _drain_message_queue(now: datetime) -> list[RunEventData]:
    """Empty the run-event queue into one ordered batch."""
    runs: list[RunEventData] = []
    while True:
        try:
            message = message_queue.popleft()
        except IndexError:
            return runs
        runs.append(_run_event_data(message, now))


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
    """Build the personal best toast, sticky and green with a trophy."""
    previous_best = run["scenario_previous_best"]
    # Guaranteed by _celebrated_run: a run with no previous best is never
    # celebrated, so there is always a figure to report here.
    assert previous_best is not None
    headline = f"{run['scenario_name']}: {run['score']:.2f}."
    if previous_best > 0:
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
        CELEBRATION_NOTIFICATION_ID,
        "New personal best",
        message,
        color="green",
        icon=local_icon("material-symbols:trophy"),
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
    Input(PB_CELEBRATION_INTERVAL_ID, "n_intervals"),
    State(RUN_EVENTS_BATCH_STORE_ID, "data"),
    prevent_initial_call=True,
)
def publish_run_events(_n_intervals, previous_batch):
    """Drain the run-event queue and publish one batch for the whole app.

    The single consumer of ``message_queue``. Facts travel and only this
    callback decides: it stamps each run's liveness and names at most one
    celebrated run, and the pages read those stamps instead of re-deriving
    them. A page callback triggered by the batch store necessarily runs after
    this one wrote it, so there is no race to coordinate.
    :param _n_intervals: poll tick. Its actual value is not used.
    :param previous_batch: the batch this client last received, for its
        animation sequence.
    :return: the new batch, and the celebration toast when one is earned
    """
    runs = _drain_message_queue(datetime.now())
    if not runs:
        return no_update, no_update

    celebrated = _celebrated_run(runs)
    batch: RunEventBatch = {
        "runs": runs,
        "celebrated_run_id": celebrated["run_id"] if celebrated else None,
        "animation_sequence": _next_animation_sequence(previous_batch, celebrated),
    }
    if celebrated is None:
        return batch, no_update
    return batch, upsert_sticky_toast(_celebration_toast(celebrated))


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
        **{"aria-label": "Toggle color scheme"},
    ),
    label="Toggle light and dark theme",
)


def nav_link(label: str, href: str, icon: str) -> dmc.NavLink:
    """Build a single-anchor Dash-native navbar link."""
    return dmc.NavLink(
        label=label,
        leftSection=dmc.ThemeIcon(
            local_icon(icon, height=36),
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
                    # Beside the container on purpose: a toast outlives the
                    # page that emitted it, so the counter that keeps its
                    # replacement lifetimes honest has to outlive it too.
                    dcc.Store(id=TOAST_LIFETIME_STORE_ID, data=0),
                    # The app-wide run-event channel. The drain and its batch
                    # live here rather than on Scenario Performance so a run
                    # reaches the screen whatever page is open; that page
                    # listens to the store instead of popping the queue.
                    dcc.Store(id=RUN_EVENTS_BATCH_STORE_ID),
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
                                                **{"aria-label": "Toggle navigation"},
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
                        children=[
                            nav_link(
                                "Scenario Performance",
                                "/",
                                "bi:house-door-fill",
                            ),
                            nav_link(
                                "Playlists",
                                "/playlists",
                                "material-symbols:playlist-play",
                            ),
                            nav_link(
                                "Settings",
                                "/settings",
                                "clarity:settings-line",
                            ),
                        ],
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
