"""Build the Home page, the page the app opens on.

Home holds first-time setup and one line that says how many runs the app
found. It shows the stats-folder hint and the setup card when they apply,
and it is the only page that offers the account, so it answers the card's
Skip button. It reads no query parameter.
"""

import logging

import dash
import dash_mantine_components as dmc
from dash import Input, Output, State, callback, ctx, dcc, no_update

from source.components.local_icon import local_icon
from source.components.queued_notices import (
    register_run_import_failure_flush,
    register_startup_playlist_warning_flush,
)
from source.components.setup_surfaces import (
    SETUP_CARD_SKIP_ID,
    setup_card_children,
    stats_dir_hint,
)
from source.config.config_service import get_config
from source.config.settings_service import decline_identity, get_usable_stats_dir
from source.kovaaks.data_service import get_scenario_stats_snapshot
from source.pages.page_title import page_title
from source.utilities.notifications import (
    TOAST_CHANNEL_REGISTRY_STORE_ID,
    channel_toast,
    toast,
)
from source.utilities.store_schema import UnsupportedSchemaError

logger = logging.getLogger(__name__)

# The two intervals the queued notices are delivered on. A failed run import
# waits for the next tick of the first, and the second ticks once, shortly
# after the page mounts, for the playlists that did not load at startup.
POLLING_INTERVAL_ID = "home-polling-interval"
STARTUP_PLAYLIST_WARNING_INTERVAL_ID = "home-startup-playlist-warning-interval"
# The first-run setup card. Its container is always in the layout so the Skip
# callback has an output to write to; the card itself is what comes and goes.
SETUP_CARD_ID = "setup-card"
STATS_DIR_HINT_ID = "stats-dir-hint"
STATS_LINE_ID = "home-stats-line"
# Shown when Skip cannot be recorded, either because the settings file belongs
# to a newer build or because the write itself failed. The card has to stay up
# (nothing was written), so the toast is what explains why the click appeared
# to do nothing. The two outcomes are mutually exclusive answers to the same
# click, so they share one channel: a second attempt replaces whatever the
# first one said instead of stacking a contradiction beside it.
SETUP_CARD_SKIP_PROBLEM_CHANNEL = "setup-card-skip-problem"
SETUP_CARD_SKIP_REFUSED_TITLE = "Skip wasn't saved"
SETUP_CARD_SKIP_REFUSED_MESSAGE = (
    "The settings file was written by a newer version of this app. Update the "
    "app to change settings."
)
SETUP_CARD_SKIP_FAILED_MESSAGE = (
    "Nothing was written. Try again. See data/logs/debug.log."
)
NO_RUNS_FOUND_MESSAGE = (
    "No runs found in your stats folder yet. Play a scenario in KovaaK's and "
    "your runs will appear in Run History."
)

dash.register_page(
    __name__,
    path="/",
    name="Home",
    title=page_title("Home"),
    redirect_from=["/home", "/index"],
)

register_run_import_failure_flush(POLLING_INTERVAL_ID)
register_startup_playlist_warning_flush(STARTUP_PLAYLIST_WARNING_INTERVAL_ID)


@callback(
    Output(SETUP_CARD_ID, "children"),
    Output("notification-container", "sendNotifications", allow_duplicate=True),
    Output("notification-container", "hideNotifications", allow_duplicate=True),
    Output(TOAST_CHANNEL_REGISTRY_STORE_ID, "data", allow_duplicate=True),
    # ``allow_optional``: Skip renders only in the identity state, while the
    # container it writes to is always mounted. Without it, every other state
    # of the page -- the stats-folder card, and every configured install --
    # logs "ID not found in layout" for this input on each load.
    Input(SETUP_CARD_SKIP_ID, "n_clicks", allow_optional=True),
    State(TOAST_CHANNEL_REGISTRY_STORE_ID, "data"),
    prevent_initial_call=True,
)
def skip_identity_setup(n_clicks, toast_channels):
    """Record the declined identity ask and take the card away.

    The write goes through the settings service's decline operation rather than
    a read-merge-write here: this callback's page was rendered at some earlier
    moment, and a settings save made since must not be undone by a card click.

    Nothing else follows from it. The warmup worker is not started -- there is
    no username to warm anything for -- and nothing pins, because the identity
    pin freezes only on a read that sees a configured username, so the click
    produces no restart notice either.

    Guard on ``n_clicks`` and the trigger: under DashProxy a callback can fire
    once on page load with nothing having triggered it, and a page load must
    never answer a question the user has not been asked yet.

    Two things can stop the write. A settings file stamped by a newer build
    refuses it, and the write itself can fail on an unwritable ``data/``. Both
    leave the card up -- taking it away would claim a decline that was never
    recorded, and it would be back on the next load anyway -- so the toast is
    what explains why the click appeared to do nothing. Without the ``OSError``
    guard the callback 500s instead, and the click reads as nothing at all.

    Both report on one channel, so a second Skip click re-pops the current
    answer instead of clicking into silence, and a retry that fails differently
    replaces the first explanation rather than sitting beside it.
    """
    if not n_clicks or ctx.triggered_id != SETUP_CARD_SKIP_ID:
        return no_update, no_update, no_update, no_update
    try:
        decline_identity()
    except UnsupportedSchemaError:
        logger.warning("Refused to record the declined identity ask")
        notification = toast(
            SETUP_CARD_SKIP_PROBLEM_CHANNEL,
            SETUP_CARD_SKIP_REFUSED_TITLE,
            SETUP_CARD_SKIP_REFUSED_MESSAGE,
            color="red",
            icon=local_icon("material-symbols:warning-outline"),
        )
        return no_update, *channel_toast(notification, toast_channels)
    except OSError:
        # A locked, full, or read-only ``data/`` leaves the store exactly as it
        # was: the write is a temp file plus an atomic replace, so there is
        # nothing to clean up and nothing to undo. Separate from the refusal
        # above because the remedy is the opposite -- retrying, not updating
        # the app.
        logger.exception("Failed to record the declined identity ask")
        notification = toast(
            SETUP_CARD_SKIP_PROBLEM_CHANNEL,
            SETUP_CARD_SKIP_REFUSED_TITLE,
            SETUP_CARD_SKIP_FAILED_MESSAGE,
            color="red",
            icon=local_icon("material-symbols:warning-outline"),
        )
        return no_update, *channel_toast(notification, toast_channels)
    return [], no_update, no_update, no_update


def _counted(count: int, noun: str) -> str:
    """Word a count with its noun, singular where the count is one."""
    return f"{count:,} {noun}" if count == 1 else f"{count:,} {noun}s"


def stats_line() -> list:
    """Say how many runs the app found, and across how many scenarios.

    Empty without a usable stats folder: the hint and the setup card already
    say why the app has no runs, and a count of none beside them would read
    as a second problem. The counts are the run store's as the page is
    drawn, so the line is as old as the page load.
    """
    if get_usable_stats_dir() is None:
        return []
    # One snapshot for both counts, so a run landing between two reads cannot
    # give a scenario the line does not count a run for.
    stats = get_scenario_stats_snapshot().values()
    runs = sum(scenario.number_of_runs for scenario in stats)
    if not runs:
        return [dmc.Text(NO_RUNS_FOUND_MESSAGE, id=STATS_LINE_ID)]
    return [
        dmc.Text(
            f"Found {_counted(runs, 'run')} across "
            f"{_counted(len(stats), 'scenario')} in your stats folder.",
            id=STATS_LINE_ID,
        )
    ]


def layout(**_kwargs):
    """Build the Home page.

    ``**_kwargs`` takes every query parameter, which Dash would otherwise
    refuse, and the page reads none of them. A link written for the page that
    once lived at this address, with ``?scenario=`` or ``?playlist_code=``,
    draws Home and selects nothing.
    """
    return dmc.Box(
        children=[
            dcc.Interval(
                id=STARTUP_PLAYLIST_WARNING_INTERVAL_ID,
                interval=250,
                n_intervals=0,
                max_intervals=1,
            ),
            dcc.Interval(
                id=POLLING_INTERVAL_ID,
                interval=get_config().polling_interval,
                n_intervals=0,
            ),
            *stats_dir_hint(STATS_DIR_HINT_ID),
            dmc.Box(
                id=SETUP_CARD_ID,
                children=setup_card_children(offer_account=True),
            ),
            *stats_line(),
        ],
    )
