"""Wire a page's playlist filter and scenario dropdown to its ids.

A page that hosts the two dropdowns fills in a ``ScenarioSelectionIds``,
builds the four components in its layout, and registers the block with the
ids once, at import. Its layout takes the deep-link store's data from
``deep_link_selection``, the playlist filter's first list from
``playlist_filter_options``, and the scenario dropdown's first list from
``initial_scenario_options``. The callbacks are plain functions here and are
registered once per page.

When a link, a new run, the page's scenario button, or a scenario's name in
the page's run list names a scenario the playlist filter does not list, the
filter is cleared and the scenario is selected.
"""

from typing import NamedTuple

import dash_mantine_components as dmc
from dash import Input, NoUpdate, Output, State, callback, ctx, no_update

from source.config.settings_service import get_usable_stats_dir
from source.kovaaks.data_service import (
    get_playlist_by_code,
    get_playlist_selector_options,
    get_scenario_names,
    get_scenarios_from_playlist_code,
    is_scenario_in_database,
)
from source.kovaaks.playlist_visibility_service import (
    get_visible_playlist_selector_options,
)

PLAYLIST_TABLE_LINK_LABEL = "Open scenario table"
# Marks a dropdown's input for ``assets/selectHighlightOnOpen.js``, which
# highlights the selected name when the list opens. dmc's
# ``clearSearchOnFocus`` buys the same click-and-type search by emptying the
# field instead, which leaves no name on screen to copy; setting it beside
# this class empties the field before the script can highlight anything.
SELECT_HIGHLIGHT_ON_OPEN_CLASS = "select-highlight-on-open"


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

    ``playlist_table_link`` is the holder beside the playlist filter's label
    for the link to that playlist's scenario table. It is always in the layout so
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


def select_playlist(selected_playlist, _deep_link, _run_landed):
    """List the selected playlist's scenarios, link to its table, and list the filter.

    With no playlist selected, or a remembered code that no longer resolves,
    the scenario list is every local scenario and there is no link.

    The filter's own options are written here because only this callback sees
    the value on every mount and every change. The layout sees a value the URL
    names and never one the browser restored.

    ``_run_landed`` is the store the page's run delivery writes for every
    batch of new runs. It is read for nothing but its change: the local list
    is read again, so it holds a scenario whose first run has just landed.
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


def _filter_leaves_out(playlist_code: str | None, scenario: str) -> bool:
    """Tell whether a playlist filter keeps a scenario with local runs off the list.

    Only a scenario with local runs counts. With the filter cleared the list
    is the scenarios that have runs, so clearing it for any other would empty
    the filter and still select nothing. A code no playlist has filters
    nothing, so it leaves nothing out.
    """
    if not playlist_code or get_playlist_by_code(playlist_code) is None:
        return False
    return scenario not in get_scenarios_from_playlist_code(
        playlist_code
    ) and is_scenario_in_database(scenario)


def reach_scenario(
    selection,
    run_events,
    follow_newly_played,
    selected_playlist,
    selected_scenario,
):
    """Select the scenario a link or a new run names, and clear a filter in its way.

    Two things reach a scenario. A visit's query parameters do, through the
    deep-link store, and a control the URL did not name is left alone. And a
    run that lands does while the page follows the scenario just played:
    ``run_events`` is the page's summary of the batch, whose latest run is on
    that scenario. Either way, a playlist filter that does not list the
    scenario is cleared in the same write, so the dropdown can name what the
    rest of the page shows. The cleared filter is then what the browser
    remembers.

    A link's values arrive here, by callback, and never as the layout's
    ``value``. A remembered control's layout default has to be the same on
    every visit, or the browser discards the stored value instead of
    restoring it. Written here, a link's selection is an ordinary one, which
    the browser then remembers like any other.

    ``run_events`` is empty until a batch lands, and the deep-link store only
    changes when the page is drawn again, which also empties ``run_events``.
    So a summary means a run triggered this call, and none means the page has
    just been drawn. With Follow off the summary is for the scenario already
    selected and moves nothing. The switch is still read here, so that a
    selection the user changes while a batch is on its way is not undone.

    One callback writes either dropdown's value, and this is what it runs for
    a link and for a run. A second writer would need ``allow_duplicate``, and
    Dash does not hold a callback back for an output written that way: the
    scenario list could then be built for the filter as it was, land after
    the scenario was selected, and drop it.
    """
    playlist: str | None | NoUpdate
    scenario: str | None | NoUpdate
    if run_events is not None:
        scenario = run_events["latest"]["scenario_name"]
        if not follow_newly_played or scenario == selected_scenario:
            return no_update, no_update
        playlist = no_update
    elif not selection:
        return no_update, no_update
    else:
        playlist = selection.get("playlist", no_update)
        scenario = selection.get("scenario", no_update)

    if isinstance(scenario, str) and scenario:
        held_playlist = (
            selected_playlist if isinstance(playlist, NoUpdate) else playlist
        )
        if _filter_leaves_out(held_playlist, scenario):
            playlist = None
    return playlist, scenario


def _button_was_clicked(triggered: list[dict]) -> bool:
    """Tell whether a click on the page's scenario button is what called.

    ``triggered`` is ``ctx.triggered``. The button is the callback's one
    ``n_clicks`` input. Its count is read as well, because a call that
    nothing triggered names no input, and a button just drawn has no clicks.
    """
    return any(
        trigger["prop_id"].endswith(".n_clicks") and trigger["value"]
        for trigger in triggered
    )


def _list_asked(triggered: list[dict], list_asked_prop: str) -> bool:
    """Tell whether a press on a scenario's name in the run list is what called.

    ``list_asked_prop`` is the ``id.data`` of the store the list's script
    writes the scenario to. The store is in the layout from the start, with
    no value until a name is pressed, so a value is read as well.
    """
    return any(
        trigger["prop_id"] == list_asked_prop and trigger["value"]
        for trigger in triggered
    )


def reach_the_scenario_asked_for(  # noqa: PLR0913
    triggered,
    list_asked_prop,
    selection,
    run_events,
    _button_clicks,
    list_scenario,
    follow_newly_played,
    selected_playlist,
    selected_scenario,
    button_scenario,
):
    """Select the scenario a link, a new run, the scenario button, or the list names.

    The page's scenario button is a third way to reach a scenario, beside the
    two ``reach_scenario`` takes: its ``value`` names a scenario, and a click
    selects it. A press on a scenario's name in the run list's tree is the
    fourth: the list's script writes the name to a store. Either way the
    scenario is selected, and a playlist filter that does not list it is
    cleared. Neither writes a dropdown itself, because this is the one
    callback that writes either value.

    Which of the four called is read from ``triggered``, what triggered the
    call, never from the values. The summary store replays its last batch to
    every later call, and the list's store its last name, so on a click
    ``run_events`` can still hold a run from minutes ago, and on a run that
    lands ``list_scenario`` the name pressed before it. Read from the values,
    a click would follow that run, and the run would select that name again.
    """
    if _button_was_clicked(triggered):
        asked_scenario = button_scenario
    elif _list_asked(triggered, list_asked_prop):
        asked_scenario = list_scenario
    else:
        return reach_scenario(
            selection,
            run_events,
            follow_newly_played,
            selected_playlist,
            selected_scenario,
        )
    if not asked_scenario or asked_scenario == selected_scenario:
        return no_update, no_update
    return (
        None if _filter_leaves_out(selected_playlist, asked_scenario) else no_update,
        asked_scenario,
    )


def register_scenario_selection_clearing_filter(  # noqa: PLR0913
    ids: ScenarioSelectionIds,
    *,
    run_events: str,
    follow_switch: str,
    run_landed: str,
    scenario_button: str,
    scenario_asked: str,
) -> None:
    """Register the block's callbacks for one page's ids.

    Call once per page, at import, with the ids its layout is built from.
    ``run_events`` is the id of the store the page's run delivery writes its
    summary to, and ``follow_switch`` the id of its Follow switch. The page's
    run delivery must not write the scenario dropdown itself: ``reach_scenario``
    does, from the summary.

    ``run_landed`` is the id of the store the same delivery writes for every
    batch, in the same answer as the summary. It has the scenario list read
    again, so that a scenario whose first run has just landed is in it. The
    summary cannot do that alone: it is written only for a batch the page
    shows, so a first run landing while Follow is off would leave its
    scenario out of the list until the filter next changed.

    ``scenario_button`` is the id of a button on the page whose ``value``
    names a scenario and whose click selects it. ``scenario_asked`` is the id
    of a store a script on the page writes a scenario's name to, which
    selects it. The page keeps both in its layout at all times: the selection
    callback's outputs are always there, so each of its inputs has to be too.
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
        # above is an output of the callback that applies a visit's query
        # parameters, and the renderer prunes a ready callback whose every
        # Input is a declared output of a group member that already ran and
        # whose none was actually written. On a visit with no
        # ``?playlist_code=`` that callback returns ``no_update``, so without a
        # second Input nothing writes these outputs: the scenario dropdown
        # keeps the layout's full local set while the filter names a playlist,
        # and that playlist's link never appears. Nothing writes this store, so
        # the prune's "every Input covered" test fails and the initial call
        # survives. See the 2026-09-19 decision-log entry.
        Input(ids.deep_link, "data"),
        # A run can be the first of its scenario, which the list drawn before
        # it lacks. ``reach_scenario`` then selects a scenario the dropdown
        # cannot name, and a Select goes on showing the previous name for a
        # value its options lack. With no filter to clear, nothing else would
        # write the list again. The same answer that writes this store writes
        # the summary that triggers ``reach_scenario``, whose plain output is
        # the filter's value, so Dash holds this call until the selection has
        # moved and the list is never built for a filter about to be cleared.
        Input(run_landed, "data"),
    )(select_playlist)
    list_asked_prop = f"{scenario_asked}.data"

    def reach_scenario_or_the_one_asked_for(*values):
        return reach_the_scenario_asked_for(ctx.triggered, list_asked_prop, *values)

    callback(
        Output(ids.playlist_filter, "value"),
        Output(ids.scenario_dropdown, "value"),
        Input(ids.deep_link, "data"),
        Input(run_events, "data"),
        Input(scenario_button, "n_clicks"),
        Input(scenario_asked, "data"),
        State(follow_switch, "checked"),
        State(ids.playlist_filter, "value"),
        State(ids.scenario_dropdown, "value"),
        State(scenario_button, "value"),
    )(reach_scenario_or_the_one_asked_for)
