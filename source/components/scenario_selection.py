"""Resolve a page's playlist and scenario selection and list its scenarios."""

import dash_mantine_components as dmc
from dash import Input, Output, callback, no_update

from source.config.settings_service import get_usable_stats_dir
from source.kovaaks.data_service import (
    get_playlist_by_code,
    get_scenario_names,
    get_scenarios_from_playlist_code,
)

# This visit's ``?scenario=`` and ``?playlist_code=``, carried as layout-bound
# state rather than read from the URL by a callback. Dash Pages rebuilds the
# page on a route change and then this store triggers exactly one write, which
# keeps the deep link out of the router's own callback graph.
HOME_DEEP_LINK_STORE_ID = "home-deep-link"
# The holder under the playlist filter for the link to that playlist's
# scenario table. It is always in the layout so ``select_playlist`` has an
# output to write to; the link itself comes and goes with the selection.
PLAYLIST_TABLE_LINK_ID = "playlist-table-link"
PLAYLIST_TABLE_LINK_LABEL = "Open scenario table"


def _local_scenario_options() -> list:
    """List the scenarios with local runs, or none without a usable stats directory.

    The directory check stays even though the names come from the store. The
    pin is restart-scoped and the store is only ever filled behind a usable
    pin, so today the check never trims a populated list; it makes "no usable
    directory, no local list" a property of this function rather than of the
    startup order.
    """
    return get_scenario_names() if get_usable_stats_dir() else []


def _playlist_table_link(playlist_code: str) -> dmc.Text:
    """Build the link from the playlist filter to that playlist's scenario table."""
    return dmc.Text(
        dmc.Anchor(
            PLAYLIST_TABLE_LINK_LABEL,
            # The bare path, with no ``?sort=``: the table opens in playlist
            # order, as it does from the Playlists page.
            href=f"/playlists/{playlist_code}",
            inherit=True,
            refresh=False,
        ),
        # The spacing rides on the link, not on a gap in the column, so the
        # holder takes no room while it is empty.
        mt="xs",
        size="sm",
    )


@callback(
    Output("scenario-dropdown-selection", "data"),
    Output(PLAYLIST_TABLE_LINK_ID, "children"),
    Input("playlist-dropdown-selection", "value"),
    # Scheduling, not data: this Input looks removable and is not. The value
    # above is an output of ``apply_deep_link``, and the renderer prunes a
    # ready callback whose every Input is a declared output of a group member
    # that already ran and whose none was actually written. On a visit with no
    # ``?playlist_code=`` that callback returns ``no_update``, so without a
    # second Input nothing writes these outputs: the scenario dropdown keeps
    # the layout's full local set while the filter names a playlist, and that
    # playlist's link never appears. Nothing writes this store, so the prune's
    # "every Input covered" test fails and the initial call survives. See the
    # 2026-09-19 decision-log entry.
    Input(HOME_DEEP_LINK_STORE_ID, "data"),
)
def select_playlist(selected_playlist, _deep_link):
    """List the selected playlist's scenarios and link to its scenario table.

    With no playlist selected, or a remembered code that no longer resolves,
    the list is every local scenario and there is no link.
    """
    if not selected_playlist or get_playlist_by_code(selected_playlist) is None:
        return _local_scenario_options(), None
    return (
        get_scenarios_from_playlist_code(selected_playlist),
        _playlist_table_link(selected_playlist),
    )


def _home_deep_link(
    scenario: str | None,
    playlist_code: str | None,
) -> dict[str, str | None]:
    """Resolve Home's query params into the selections this visit applies.

    A key is present only for a parameter the URL actually carried, because
    the two dropdowns are set independently: ``?scenario=`` alone must leave
    the playlist filter on whatever the browser restored. An unknown playlist
    code is present with no value, which clears the filter rather than leaving
    a code the app cannot resolve standing.
    """
    selection: dict[str, str | None] = {}
    if playlist_code is not None:
        selection["playlist"] = (
            playlist_code if get_playlist_by_code(playlist_code) is not None else None
        )
    if scenario is not None:
        selection["scenario"] = scenario or None
    return selection


def _home_scenario_options(playlist_code: str | None) -> list[str]:
    """List the scenarios the first paint shows, before any callback runs.

    ``select_playlist`` owns this list from then on. Resolving the query
    parameter here too means a deep-linked visit paints its playlist's
    scenarios immediately instead of the whole local list.
    """
    selected_playlist = (
        playlist_code
        if playlist_code and get_playlist_by_code(playlist_code) is not None
        else None
    )
    if selected_playlist:
        return get_scenarios_from_playlist_code(selected_playlist)
    return _local_scenario_options()


@callback(
    Output("playlist-dropdown-selection", "value"),
    Output("scenario-dropdown-selection", "value", allow_duplicate=True),
    Input(HOME_DEEP_LINK_STORE_ID, "data"),
    # Not ``True``: applying the deep link *is* the mount's job, but Dash
    # refuses an ``allow_duplicate`` output without one of the
    # ``prevent_initial_call`` forms.
    prevent_initial_call="initial_duplicate",
)
def apply_deep_link(selection):
    """Set the two dropdowns from this visit's query parameters.

    The values arrive by callback rather than as the layout's ``value`` so
    that Dash persistence records them: a persisted control's layout default
    has to be the same on every visit, or the stored edit is discarded instead
    of restored. Writing them here makes a Playlists grid click an ordinary
    selection, which the browser then remembers like any other.

    Under DashProxy an ``allow_duplicate`` callback can fire once on load with
    nothing triggering it. Re-emitting the same values is harmless -- Dash
    skips a persistence write when the value is unchanged -- so this needs no
    guard beyond the empty payload every non-deep-linked visit carries.

    Returning ``no_update`` for a control the URL did not name leaves that
    control's dependents unwritten, which is why ``select_playlist`` carries a
    second Input.
    """
    if not selection:
        return no_update, no_update
    return (
        selection.get("playlist", no_update),
        selection.get("scenario", no_update),
    )
