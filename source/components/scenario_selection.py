"""Wire a page's playlist filter and scenario dropdown to its ids.

A page that hosts the two dropdowns fills in a ``ScenarioSelectionIds``,
builds the four components in its layout, and registers the block with the
ids once, at import. Its layout takes the deep-link store's data from
``deep_link_selection``, the playlist filter's first list from
``playlist_filter_options``, and the scenario dropdown's first list from
``initial_scenario_options``. The callbacks are plain functions here and are
registered once per page.

When a link, a new run, or a scenario's name in the page's run list names a
scenario the playlist filter does not list, the filter is cleared and the
scenario is selected.

While the page's scenario note has unsaved changes, the selection callback
moves nothing on its own: a run that lands waits, and a name pressed in the
list asks first. The note card's script answers with a request this callback
carries out, so one callback still writes both dropdowns.
"""

from typing import Any, NamedTuple

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


class NoteSelectionIds(NamedTuple):
    """The ids of the scenario note's pieces the selection callback reads and writes.

    ``editor`` is the store of the open editor, ``{"scenario", "opened"}``, or
    nothing while it is closed, and ``draft`` the text box whose ``value`` is
    the text being typed. Together they say whether the note has unsaved
    changes. ``waiting`` is the store of the scenario a held run would move
    the page to, which this callback alone writes. ``held`` is the store this
    callback writes a name pressed in the list to, instead of selecting it,
    for the note card to ask about. ``go`` is the store the note card's
    script writes the player's answer to (``note_request``).
    """

    go: str
    editor: str
    draft: str
    waiting: str
    held: str


class SelectionProps(NamedTuple):
    """The ``id.prop`` of each input that tells the selection callback what called."""

    list_asked: str
    run_events: str
    go: str
    follow: str
    deep_link: str


def has_unsaved_changes(editor: dict[str, Any] | None, draft: str | None) -> bool:
    """Tell whether the note's editor is open on a text other than the one it opened with.

    Typing a word and deleting it again leaves no unsaved changes.
    """
    if not editor or draft is None:
        return False
    return draft != editor["opened"]


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

    The caller passes a summary only for a call a run triggered, and none for
    the page's first call, which applies the link. With Follow off the summary
    is for the scenario already selected and moves nothing. The switch is
    still read here, so that a selection the user changes while a batch is on
    its way is not undone.

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


def _called_with(triggered: list[dict], prop_id: str) -> bool:
    """Tell whether the input ``prop_id`` called, holding a value.

    Every store this reads is in the layout from the start, with no value
    until something writes one, and a page's first call can name every input
    as a trigger. So a trigger with no value is not a call.
    """
    return any(
        trigger["prop_id"] == prop_id and trigger["value"] for trigger in triggered
    )


def _named(triggered: list[dict], prop_id: str) -> bool:
    return any(trigger["prop_id"] == prop_id for trigger in triggered)


def _first_call(triggered: list[dict]) -> bool:
    """Tell whether no input called: Dash then reports one trigger named ``.``."""
    return all(trigger["prop_id"] == "." for trigger in triggered)


def _select(
    scenario: str | None, selected_playlist: str | None, selected_scenario: str | None
) -> tuple[Any, Any]:
    """Select ``scenario`` and clear a playlist filter in its way, or change nothing."""
    if not scenario or scenario == selected_scenario:
        return no_update, no_update
    return (
        None if _filter_leaves_out(selected_playlist, scenario) else no_update,
        scenario,
    )


def note_request(
    request: dict[str, Any],
    waiting: str | None,
    selected_playlist: str | None,
    selected_scenario: str | None,
) -> tuple[Any, Any, Any]:
    """Carry out the note card's answer: the filter, the scenario, and the wait.

    The card's script writes one of four requests, each once the editor is
    closed or its answer is final, so none of them looks at unsaved changes:

    - ``release`` moves the page to the scenario of the run that waited, as
      Follow would have, and ends the wait. Save, Cancel, and undoing every
      change send it, so with nothing waiting it changes nothing.
    - ``select`` moves the page to a scenario the dialog was asked about, a
      name in the list or a run toast's link, and drops the run that waited:
      the player chose where to go.
    - ``restore`` writes back the filter and the scenario the note was edited
      on, which Keep editing asks for after a pick or a filter change has
      already moved them. A run that waited goes on waiting.
    - ``drop`` ends the wait and moves nothing: after a pick or a filter
      change the page is already where the player asked.
    """
    restore = request.get("restore")
    if restore is not None:
        return (
            no_update
            if restore["playlist"] == selected_playlist
            else restore["playlist"],
            no_update
            if restore["scenario"] == selected_scenario
            else restore["scenario"],
            no_update,
        )
    target = waiting if request.get("release") else request.get("select")
    return (
        *_select(target, selected_playlist, selected_scenario),
        no_update if waiting is None else None,
    )


def _hold_run(run_events, follow_newly_played, editor, waiting) -> tuple[Any, Any, Any]:
    """Hold a run that lands while the note has unsaved changes: nothing moves.

    The run on another scenario becomes the one the page will move to, the
    newest replacing any before it. A run on the edited scenario ends the
    wait, since the page is where Follow would take it. Against the edited
    scenario, not the dropdown, which a pick held behind the dialog has
    already moved. With Follow off a run asks for nothing.
    """
    if not follow_newly_played:
        return no_update, no_update, no_update
    played = run_events["latest"]["scenario_name"]
    if played == editor["scenario"]:
        return no_update, no_update, no_update if waiting is None else None
    return no_update, no_update, no_update if played == waiting else played


def reach_the_scenario_asked_for(  # noqa: PLR0913
    triggered,
    props: SelectionProps,
    selection,
    run_events,
    list_scenario,
    request,
    follow_newly_played,
    selected_playlist,
    selected_scenario,
    editor,
    draft,
    waiting,
):
    """Select the scenario a link, a new run, the list or the note card names.

    Returns the filter, the scenario, the scenario a held run waits on, and a
    name in the list held for the note card to ask about.

    A press on a scenario's name in the run list's tree is a third way to
    reach a scenario, beside the two ``reach_scenario`` takes: the list's
    script writes the name to a store. The scenario is selected, and a
    playlist filter that does not list it is cleared. The list writes no
    dropdown itself, because this is the one callback that writes either
    value. The note card's answers are a fourth (``note_request``).

    While the note has unsaved changes nothing here moves the page on its
    own. A run that lands waits (``_hold_run``), and a press is held for the
    note card, which asks the player and answers with a request. Turning
    Follow off ends a wait, and turning it on brings none back.

    Which input called is read from ``triggered``, never from the values. The
    summary store replays its last batch to every later call, and the list's
    store its last name, so on a press ``run_events`` can still hold a run
    from minutes ago, and on a run that lands ``list_scenario`` the name
    pressed before it. Read from the values, a press would follow that run,
    the run would select that name again, and a flip of Follow would follow
    a run already handled.
    """
    unsaved = has_unsaved_changes(editor, draft)
    if _called_with(triggered, props.go):
        return (
            *note_request(request, waiting, selected_playlist, selected_scenario),
            no_update,
        )
    if _called_with(triggered, props.list_asked):
        if unsaved and list_scenario and list_scenario != selected_scenario:
            return no_update, no_update, no_update, {"to": list_scenario}
        return (
            *_select(list_scenario, selected_playlist, selected_scenario),
            no_update,
            no_update,
        )
    playlist: Any = no_update
    scenario: Any = no_update
    held_on: Any = no_update
    if _called_with(triggered, props.run_events):
        if unsaved:
            playlist, scenario, held_on = _hold_run(
                run_events, follow_newly_played, editor, waiting
            )
        else:
            playlist, scenario = reach_scenario(
                None,
                run_events,
                follow_newly_played,
                selected_playlist,
                selected_scenario,
            )
            # A wait outlives its unsaved changes only for a moment, and a run
            # that moves the page ends it.
            if waiting is not None and scenario is not no_update:
                held_on = None
    elif _named(triggered, props.deep_link) or _first_call(triggered):
        playlist, scenario = reach_scenario(
            selection,
            None,
            follow_newly_played,
            selected_playlist,
            selected_scenario,
        )
    if _named(triggered, props.follow) and not follow_newly_played:
        held_on = no_update if waiting is None else None
    return playlist, scenario, held_on, no_update


def register_scenario_selection_clearing_filter(  # noqa: PLR0913
    ids: ScenarioSelectionIds,
    *,
    run_events: str,
    follow_switch: str,
    run_landed: str,
    scenario_asked: str,
    note: NoteSelectionIds,
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

    ``scenario_asked`` is the id of a store a script on the page writes a
    scenario's name to, which selects it. The page keeps it in its layout at
    all times: the selection callback's outputs are always there, so each of
    its inputs has to be too. The same holds for every piece of the note card
    ``note`` names.
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
    props = SelectionProps(
        list_asked=f"{scenario_asked}.data",
        run_events=f"{run_events}.data",
        go=f"{note.go}.data",
        follow=f"{follow_switch}.checked",
        deep_link=f"{ids.deep_link}.data",
    )

    def reach_scenario_or_the_one_asked_for(*values):
        return reach_the_scenario_asked_for(ctx.triggered, props, *values)

    callback(
        Output(ids.playlist_filter, "value"),
        Output(ids.scenario_dropdown, "value"),
        Output(note.waiting, "data"),
        Output(note.held, "data"),
        Input(ids.deep_link, "data"),
        Input(run_events, "data"),
        Input(scenario_asked, "data"),
        # Written by the note card's controller with ``set_props``, never as
        # its declared output: the controller takes the scenario dropdown this
        # callback writes as an Input, and the two declared edges would close
        # a loop the renderer refuses.
        Input(note.go, "data"),
        # An Input, so that turning Follow off ends a wait at once. The value
        # still decides only whether a run is followed.
        Input(follow_switch, "checked"),
        State(ids.playlist_filter, "value"),
        State(ids.scenario_dropdown, "value"),
        State(note.editor, "data"),
        State(note.draft, "value"),
        State(note.waiting, "data"),
    )(reach_scenario_or_the_one_asked_for)
