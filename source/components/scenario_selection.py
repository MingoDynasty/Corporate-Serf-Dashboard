"""Wire a page's playlist filter and scenario dropdown to its ids.

A page that hosts the two dropdowns fills in a ``ScenarioSelectionIds``,
builds the four components in its layout, and calls
``register_scenario_selection`` with the ids once, at import. Its layout takes
the deep-link store's data from ``deep_link_selection``, the playlist filter's
first list from ``playlist_filter_options``, and the scenario dropdown's first
list from ``initial_scenario_options``. The callbacks are plain functions here
and are registered once per page.
"""

from typing import NamedTuple

import dash_mantine_components as dmc
from dash import Input, Output, callback, no_update

from source.config.settings_service import get_usable_stats_dir
from source.kovaaks.data_service import (
    get_playlist_by_code,
    get_playlist_selector_options,
    get_scenario_names,
    get_scenarios_from_playlist_code,
)
from source.kovaaks.playlist_visibility_service import (
    get_visible_playlist_selector_options,
)

PLAYLIST_TABLE_LINK_LABEL = "Open scenario table"


class ScenarioSelectionIds(NamedTuple):
    """The component ids one page gives its playlist filter and scenario dropdown.

    The page's layout builds all four components. Two pages need two sets:
    the callbacks are registered once per set, and Dash allows one callback
    per output. The browser stores each dropdown's value under its id, so
    changing ``playlist_filter`` or ``scenario_dropdown`` on a page that
    already uses it resets that selection for every user.

    ``deep_link`` is a ``dcc.Store`` holding this visit's ``?scenario=`` and
    ``?playlist_code=``, carried as layout-bound state rather than read from
    the URL by a callback. Dash Pages rebuilds the page on a route change and
    then this store triggers exactly one write, which keeps the deep link out
    of the router's own callback graph.

    ``playlist_table_link`` is the holder under the playlist filter for the
    link to that playlist's scenario table. It is always in the layout so
    ``select_playlist`` has an output to write to; the link itself comes and
    goes with the selection.
    """

    playlist_filter: str
    scenario_dropdown: str
    deep_link: str
    playlist_table_link: str


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


def playlist_filter_options(held_playlist: str | None) -> list[dict[str, str]]:
    """List the playlist filter's options: the visible playlists, plus the one it holds.

    A hidden playlist still loads, and a scenario link from its table selects
    it here, so the filter can hold a playlist the visible list lacks. A Select
    shows no name for a value its options lack, and goes on showing the
    previous name when a callback writes such a value. Listing the held
    playlist is what lets the filter name it.

    The held playlist is listed only while it is held: the next pick or clear
    builds the list without it, so a hidden playlist still cannot be picked
    from the dropdown. A code no loaded playlist has adds nothing.

    The layout calls this with ``?playlist_code=`` and ``select_playlist``
    with the filter's value.
    """
    options = get_visible_playlist_selector_options()
    if not held_playlist or any(option["value"] == held_playlist for option in options):
        return options
    listed = {option["value"] for option in options} | {held_playlist}
    # Filtered from the full list rather than appended, so the held playlist
    # sits where the list's own order puts it.
    return [
        option
        for option in get_playlist_selector_options()
        if option["value"] in listed
    ]


def select_playlist(selected_playlist, _deep_link):
    """List the selected playlist's scenarios, link to its table, and list the filter.

    With no playlist selected, or a remembered code that no longer resolves,
    the scenario list is every local scenario and there is no link.

    The filter's own options are written here because only this callback sees
    the value on every mount and every change. The layout sees a value the URL
    names and never one the browser restored.
    """
    options = playlist_filter_options(selected_playlist)
    if not selected_playlist or get_playlist_by_code(selected_playlist) is None:
        return _local_scenario_options(), None, options
    return (
        get_scenarios_from_playlist_code(selected_playlist),
        _playlist_table_link(selected_playlist),
        options,
    )


def deep_link_selection(
    scenario: str | None,
    playlist_code: str | None,
) -> dict[str, str | None]:
    """Resolve a page's query parameters into the selections this visit applies.

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


def initial_scenario_options(playlist_code: str | None) -> list[str]:
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


def register_scenario_selection(ids: ScenarioSelectionIds) -> None:
    """Register the block's callbacks for one page's ids.

    Call once per page, at import, with the ids its layout is built from.
    """
    callback(
        Output(ids.scenario_dropdown, "data"),
        Output(ids.playlist_table_link, "children"),
        # The Select drops a value its new options lack, and the browser then
        # stores the empty filter. So the list written here has to hold the
        # playlist the filter holds: the visible list alone would clear a
        # hidden selection for good. That drop is also what empties the filter
        # of a remembered code no playlist has.
        Output(ids.playlist_filter, "data"),
        Input(ids.playlist_filter, "value"),
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
        Input(ids.deep_link, "data"),
    )(select_playlist)
    callback(
        Output(ids.playlist_filter, "value"),
        Output(ids.scenario_dropdown, "value", allow_duplicate=True),
        Input(ids.deep_link, "data"),
        # Not ``True``: applying the deep link *is* the mount's job, but Dash
        # refuses an ``allow_duplicate`` output without one of the
        # ``prevent_initial_call`` forms.
        prevent_initial_call="initial_duplicate",
    )(apply_deep_link)
