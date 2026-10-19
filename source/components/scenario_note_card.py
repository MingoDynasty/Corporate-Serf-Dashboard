"""Build the Run History page's scenario note card and wire it to the page's ids.

The card shows the selected scenario's note, the player's own plain text, and
edits it in place with explicit Save and Cancel. A page that hosts it fills in
a ``NoteCardIds``, puts ``scenario_note_card`` and ``scenario_note_dialog`` in
its layout, and calls ``register_scenario_note_card`` with the ids once, at
import. The selection callback takes the card's stores too
(``note_selection_ids``), since it holds runs and names while the note has
unsaved changes.

Who does what:

- The server reads the note (``show_note``) and saves it
  (``save_from_editor``). It draws the card for the scenario in the
  ``shown`` store, which only the card's controller writes, so nothing else
  redraws it.
- The controller, ``scenario_notes.controller`` in
  ``assets/scenarioNotes.js``, runs in the browser. It opens and closes the
  editor, decides when a change of scenario asks first, and answers the
  dialog. It decides there, at the moment a change lands, because the text
  box is typed into there: a decision taken on the server could be a round
  trip out of date.
- The same script stops a link or a history move that would leave the page
  while the note has unsaved changes, and sets the browser's unload prompt.

Every string the card shows is here or comes from the store; the script holds
no copy.
"""

import logging
from typing import Any, NamedTuple

import dash_mantine_components as dmc
from dash import (
    ClientsideFunction,
    Input,
    Output,
    State,
    callback,
    clientside_callback,
    ctx,
    dcc,
    html,
    no_update,
)

from source.components.chart_options import TOOLTIP_EVENTS
from source.components.latest_run_card import (
    AGE_SCRIPT,
    TIME_CLASS,
    TIME_TARGET_CLASS,
)
from source.components.scenario_selection import NoteSelectionIds
from source.kovaaks.scenario_notes_service import (
    MAX_NOTE_CHARACTERS,
    read_scenario_note,
    save_scenario_note,
)
from source.utilities.store_schema import (
    SchemaPayloadError,
    StoreState,
    UnsupportedSchemaError,
)

logger = logging.getLogger(__name__)

NOTE_LABEL = "Scenario note"
EDIT_LABEL = "Edit"
EDIT_ACCESSIBLE_NAME = "Edit scenario note"
ADD_LABEL = "Add a scenario note"
PLACEHOLDER = "Note for this scenario"
SAVE_LABEL = "Save"
CANCEL_LABEL = "Cancel"
# The count shows from this many characters, as the text box counts them.
COUNT_FROM = 1800
COUNT_TEMPLATE = f"{{count}} of {MAX_NOTE_CHARACTERS:,} characters"
SAVE_FAILED_MESSAGE = "Couldn't save the scenario note. See data/logs/debug.log."
DIALOG_TITLE = "Your scenario note isn't saved"
# The line under the buttons while a run waits, which the controller fills in
# as the run is held, as it does the dialog's questions: ``{scenario}`` is
# where the page will go.
WAITING_LINE: list[Any] = [
    "A run on {scenario} is waiting. Press ",
    {"control": SAVE_LABEL},
    " or ",
    {"control": CANCEL_LABEL},
    " to show it.",
]
# The dialog's questions, which the controller fills in as the dialog opens:
# ``{from}`` is the note's scenario and ``{to}`` where the player asked to go,
# and a part in a dict is a control's name, drawn bold as ``control_name``
# draws it. Filled in the browser so a question is never a round trip behind
# the dialog, which would show the last one asked. A pick, a name in the list
# and a toast's link name where the page would go. A filter change names
# none: the player chose a playlist, not a scenario. Leaving the page, by a
# link or the browser's buttons, names no place either.
DIALOG_QUESTIONS: dict[str, list[Any]] = {
    "switch": ["Save your changes to the note on {from} before you switch to {to}?"],
    "filter": [
        "The ",
        {"control": "Selected scenario"},
        " list no longer holds {from}. Save your changes to its note first?",
    ],
    "leave": ["Save your changes to the note on {from} before you leave the page?"],
}
KEEP_EDITING_LABEL = "Keep editing"
DISCARD_LABEL = "Discard"

CARD_CLASS = "run-history-note-card"
READ_CLASS = "run-history-note-read"
HEADING_CLASS = "run-history-note-heading"
LABEL_CLASS = "run-history-note-label"
LINK_CLASS = "run-history-note-link"
# Mantine's keyboard focus ring, which a dmc button would have brought. Without
# it the ring is the browser's own, near-black in Chromium on the dark theme.
FOCUS_CLASS = "mantine-focus-auto"
TEXT_CLASS = "run-history-note-text"
SCROLL_CLASS = "run-history-note-scroll"
EDITOR_CLASS = "run-history-note-editor"
TEXT_BOX_CLASS = "run-history-note-text-box"
FOOTER_CLASS = "run-history-note-footer"
BUTTONS_CLASS = "run-history-note-buttons"
LINES_CLASS = "run-history-note-lines"
WAITING_CLASS = "run-history-note-waiting"
COUNT_CLASS = "run-history-note-count"
ERROR_CLASS = "run-history-note-error"
DIALOG_CLASS = "run-history-note-dialog"


class NoteState:
    """What the card shows for its scenario: the four store states, and no scenario.

    Each value is also the card's class modifier and what the controller reads
    to open the editor: a note opens on its text, a missing note and a broken
    file on an empty box, and a file from a newer build not at all.
    """

    NONE = "none"
    MISSING = "missing"
    NOTE = "note"
    ERROR = "error"
    FUTURE = "future"


class NoteCardIds(NamedTuple):
    """The component ids one page gives its scenario note card.

    The card's own pieces:

    - ``card`` is the card's box. The server writes its class, which carries
      what it shows, and the controller its ``data-`` attributes, which carry
      the editor's state for the stylesheet and the page script.
    - ``shown`` holds the scenario the card shows. ``note`` holds what the
      server last read for it, and ``edited_at`` when its text last changed,
      in epoch seconds, which ``label``, ``time`` and ``time_tooltip`` word.
    - ``text`` holds the note, or the message of a file that can't be read.
      ``edit`` and ``add`` open the editor.
    - ``editor`` holds the open editor, ``draft`` is its text box, and
      ``save``, ``cancel``, ``waiting_line``, ``char_count`` and ``error`` are its
      buttons and the lines under them. ``save_result`` holds what the last
      save did.
    - ``dialog`` is the modal that asks before a change of scenario or a
      departure. ``dialog_state`` holds what it asks about, ``question``
      its question, and ``keep``, ``discard`` and ``dialog_save`` its answers.
    - ``held``, ``go`` and ``waiting`` are shared with the selection callback
      (``note_selection_ids``). ``filter_history`` holds the last two values
      of the playlist filter, for Keep editing. ``config`` holds the ids and
      the strings the controller needs, and ``fade_sink`` is the output of a
      script that writes nothing.

    The page's own: ``scenario_dropdown``, ``playlist_filter``, and
    ``relative_time_interval``, the tick that rewords the age.
    """

    card: str
    shown: str
    note: str
    edited_at: str
    label: str
    time: str
    time_tooltip: str
    text: str
    edit: str
    add: str
    editor: str
    draft: str
    save: str
    cancel: str
    waiting_line: str
    char_count: str
    error: str
    save_result: str
    dialog: str
    dialog_state: str
    question: str
    keep: str
    discard: str
    dialog_save: str
    held: str
    go: str
    waiting: str
    filter_history: str
    config: str
    fade_sink: str
    scenario_dropdown: str
    playlist_filter: str
    relative_time_interval: str


def note_selection_ids(ids: NoteCardIds) -> NoteSelectionIds:
    """Name the card's stores the selection callback reads and writes."""
    return NoteSelectionIds(
        go=ids.go,
        editor=ids.editor,
        draft=ids.draft,
        waiting=ids.waiting,
        held=ids.held,
    )


def card_class(state: str) -> str:
    """Return the card's class for what it shows."""
    return f"{CARD_CLASS} {CARD_CLASS}-{state}"


def _controller_config(ids: NoteCardIds) -> dict[str, Any]:
    """Build what the controller reads besides its inputs: the ids, and the templates it fills in."""
    return {
        "ids": ids._asdict(),
        "count": COUNT_TEMPLATE,
        "countFrom": COUNT_FROM,
        "questions": DIALOG_QUESTIONS,
        "waiting": WAITING_LINE,
    }


def _age_label(ids: NoteCardIds) -> html.Span:
    """Build the words between ``Scenario note`` and the end of the first line.

    Hidden with no edit time, as the PB card's age is: a broken file has none.
    """
    return html.Span(
        [
            " · edited ",
            dmc.Tooltip(
                dmc.Text(
                    className=TIME_CLASS,
                    id=ids.time,
                    inherit=True,
                    span=True,
                    tabIndex=0,
                ),
                # dmc wraps the tooltip's target in a block box, which would
                # break the line round it.
                boxWrapperProps={"className": TIME_TARGET_CLASS},
                events=TOOLTIP_EVENTS,
                id=ids.time_tooltip,
                label="",
            ),
        ],
        hidden=True,
        id=ids.label,
    )


def _read_view(ids: NoteCardIds) -> html.Div:
    """Build what the card shows while reading: the first line, the note, or the link."""
    edit_name: dict[str, Any] = {"aria-label": EDIT_ACCESSIBLE_NAME}
    return html.Div(
        className=READ_CLASS,
        children=[
            # Not a flex item list of words: the label is one item, so the
            # spaces either side of the age stay with it.
            html.Div(
                className=HEADING_CLASS,
                children=[
                    html.Span([NOTE_LABEL, _age_label(ids)], className=LABEL_CLASS),
                    html.Button(
                        EDIT_LABEL,
                        className=f"{LINK_CLASS} {FOCUS_CLASS}",
                        id=ids.edit,
                        type="button",
                        **edit_name,
                    ),
                ],
            ),
            # Mantine draws this scrollbar itself, so it shows whenever the
            # note is longer than the card. The browser's own would be an
            # overlay in Firefox on Windows 11, gone a second after the page
            # draws, and a note cut inside a run of blank lines would look
            # whole. The browsers make the viewport a tab stop only while it
            # scrolls; the region role is what lets it carry a name.
            dmc.ScrollArea(
                html.Div(className=TEXT_CLASS, id=ids.text),
                className=SCROLL_CLASS,
                type="auto",
                scrollbars="y",
                offsetScrollbars="y",
                scrollbarSize=8,
                attributes={"viewport": {"role": "region", "aria-label": NOTE_LABEL}},
            ),
            html.Button(
                ADD_LABEL,
                className=f"{LINK_CLASS} {LINK_CLASS}-add {FOCUS_CLASS}",
                id=ids.add,
                type="button",
            ),
        ],
    )


def _editor(ids: NoteCardIds) -> html.Div:
    """Build the editor: the text box over Save and Cancel and the lines beside them."""
    # A polite live region, in the page while it is empty too: a region
    # that arrives with its text already in it may not be announced.
    live_region: dict[str, Any] = {"aria-live": "polite"}
    return html.Div(
        className=EDITOR_CLASS,
        children=[
            html.Div(NOTE_LABEL, className=HEADING_CLASS),
            dmc.Textarea(
                # The browser stops typing at the cap and cuts a paste there.
                attributes={"input": {"maxLength": MAX_NOTE_CHARACTERS}},
                className=TEXT_BOX_CLASS,
                id=ids.draft,
                placeholder=PLACEHOLDER,
                value="",
                **{"aria-label": NOTE_LABEL},
            ),
            html.Div(
                className=FOOTER_CLASS,
                children=[
                    html.Div(
                        [
                            dmc.Button(SAVE_LABEL, id=ids.save, size="compact-sm"),
                            dmc.Button(
                                CANCEL_LABEL,
                                id=ids.cancel,
                                size="compact-sm",
                                variant="default",
                            ),
                        ],
                        className=BUTTONS_CLASS,
                    ),
                    html.Div(
                        className=LINES_CLASS,
                        children=[
                            html.Div(
                                className=WAITING_CLASS,
                                id=ids.waiting_line,
                                **live_region,
                            ),
                            html.Div(className=COUNT_CLASS, id=ids.char_count),
                            html.Div(className=ERROR_CLASS, id=ids.error, role="alert"),
                        ],
                    ),
                ],
            ),
        ],
    )


def scenario_note_card(ids: NoteCardIds, *, toast_link_class: str) -> html.Div:
    """Build the card with nothing in it yet.

    The page's callbacks write what it shows. Every piece is in the layout
    from the start and only shown or hidden, so the text box a player types
    into is never drawn again under them. ``toast_link_class`` is the class
    of the run toast's link, which the page script tells apart from a link
    that leaves the page.
    """
    # Read by the stylesheet and the page script, and written by the
    # controller. The last two tell the script where to ask and which link
    # is the toast's.
    attributes: dict[str, Any] = {
        "data-editing": "false",
        "data-unsaved": "false",
        "data-dialog": "false",
        "data-scenario": "",
        "data-note-held-store": ids.held,
        "data-note-toast-link-class": toast_link_class,
    }
    return html.Div(
        className=card_class(NoteState.NONE),
        id=ids.card,
        children=[
            dcc.Store(id=ids.shown),
            dcc.Store(id=ids.note),
            dcc.Store(id=ids.edited_at),
            dcc.Store(id=ids.editor),
            dcc.Store(id=ids.save_result),
            dcc.Store(id=ids.dialog_state),
            dcc.Store(id=ids.held),
            dcc.Store(id=ids.go),
            dcc.Store(id=ids.waiting),
            dcc.Store(id=ids.filter_history),
            dcc.Store(id=ids.config, data=_controller_config(ids)),
            dcc.Store(id=ids.fade_sink),
            _read_view(ids),
            _editor(ids),
        ],
        **attributes,
    )


def scenario_note_dialog(ids: NoteCardIds) -> dmc.Modal:
    """Build the dialog that asks before unsaved changes are left behind.

    Its three answers are the ways out, so it has no close button. Escape and
    a click outside it mean Keep editing, which takes keyboard focus first, so
    Enter can't throw text away. Focus is put back by the controller, not by
    the modal: Keep editing returns it to the text box.
    """
    return dmc.Modal(
        children=dmc.Stack(
            gap="md",
            children=[
                dmc.Text(id=ids.question, size="sm"),
                dmc.Group(
                    justify="flex-end",
                    gap="sm",
                    children=[
                        dmc.Button(
                            KEEP_EDITING_LABEL,
                            id=ids.keep,
                            variant="default",
                            **{"data-autofocus": True},
                        ),
                        dmc.Button(DISCARD_LABEL, id=ids.discard, variant="default"),
                        dmc.Button(SAVE_LABEL, id=ids.dialog_save),
                    ],
                ),
            ],
        ),
        className=DIALOG_CLASS,
        id=ids.dialog,
        opened=False,
        returnFocus=False,
        title=DIALOG_TITLE,
        withCloseButton=False,
    )


class NoteCardContent(NamedTuple):
    """What the server writes to the card for one scenario, one field per prop."""

    card_class: str
    text: str | None
    edited_at: float | None
    note: dict[str, Any]


def note_card_content(scenario: str | None) -> NoteCardContent:
    """Read ``scenario``'s note and build what the card shows for it.

    A broken file's message and a newer build's take the note's place, and
    neither has an edit time to show.
    """
    if not scenario:
        return _content(scenario, NoteState.NONE)
    document = read_scenario_note(scenario)
    if document.state is StoreState.MISSING:
        return _content(scenario, NoteState.MISSING)
    if document.state is StoreState.SUPPORTED:
        note = document.value
        return _content(
            scenario,
            NoteState.NOTE,
            text=note.text,
            edited_at=note.edited_at.timestamp(),
        )
    state = NoteState.FUTURE if document.state is StoreState.FUTURE else NoteState.ERROR
    return _content(scenario, state, message=document.message)


def _content(
    scenario: str | None,
    state: str,
    *,
    text: str | None = None,
    edited_at: float | None = None,
    message: str | None = None,
) -> NoteCardContent:
    return NoteCardContent(
        card_class=card_class(state),
        text=text if message is None else message,
        edited_at=edited_at,
        note={"scenario": scenario, "state": state, "text": text},
    )


def save_note(scenario: str, text: str) -> str | None:
    """Save ``text`` as ``scenario``'s note, and return the error to show, or None.

    A file from a newer build refuses the save with the schema machinery's
    own message, which says what to do. Any other failure is the generic
    line, and the log has the cause.
    """
    try:
        save_scenario_note(scenario, text)
    except UnsupportedSchemaError as exc:
        return str(exc)
    except (OSError, SchemaPayloadError) as exc:
        logger.warning('Couldn\'t save the scenario note for "%s": %s', scenario, exc)
        return SAVE_FAILED_MESSAGE
    return None


def show_note(shown: str | None) -> NoteCardContent:
    """Draw the card for the scenario it shows."""
    return note_card_content(shown)


def save_from_editor(
    via: str | None,
    editor: dict[str, Any] | None,
    draft: str | None,
) -> tuple[Any, ...]:
    """Save the editor's text, and draw the card from the file again if it worked.

    ``via`` names the Save that was pressed, the card's or the dialog's, or is
    None for a call no press made. Returns what the save did, then the card's
    class, its text, the edit time and what was read. The save goes to the
    scenario the editor opened on. One that failed leaves the card as it is:
    the editor stays open over it, with the error under the buttons. Drawn in
    the same answer as the result, so the controller closes the editor over
    the saved text, never over the text it replaced.
    """
    if via is None or not editor:
        return (no_update,) * 5
    text = draft or ""
    error = save_note(editor["scenario"], text)
    result = {"ok": error is None, "error": error, "via": via, "text": text}
    if error is not None:
        return result, no_update, no_update, no_update, no_update
    return (result, *note_card_content(editor["scenario"]))


def register_scenario_note_card(ids: NoteCardIds) -> None:
    """Register the card's callbacks for one page's ids.

    Call once per page, at import, with the ids its layout is built from.
    """
    callback(
        Output(ids.card, "className"),
        Output(ids.text, "children"),
        Output(ids.edited_at, "data"),
        Output(ids.note, "data"),
        # The scenario the card shows, and nothing else of the page's: a run,
        # the filter, the tick and a pick the dialog holds never redraw it.
        Input(ids.shown, "data"),
    )(show_note)

    def save(save_clicks, dialog_save_clicks, editor, draft):
        # Read from the press, never from the counts alone. With duplicate
        # outputs this can be called once as the page is drawn, with neither
        # button pressed.
        pressed = {ids.save: save_clicks, ids.dialog_save: dialog_save_clicks}
        via = None
        if ctx.triggered_id in pressed and pressed[ctx.triggered_id]:
            via = "dialog" if ctx.triggered_id == ids.dialog_save else "card"
        return save_from_editor(via, editor, draft)

    callback(
        Output(ids.save_result, "data"),
        # The drawing callback's outputs again. The controller takes this
        # result as an Input and writes the store that callback takes, so a
        # save that called that callback would close a loop the renderer
        # refuses.
        Output(ids.card, "className", allow_duplicate=True),
        Output(ids.text, "children", allow_duplicate=True),
        Output(ids.edited_at, "data", allow_duplicate=True),
        Output(ids.note, "data", allow_duplicate=True),
        Input(ids.save, "n_clicks"),
        Input(ids.dialog_save, "n_clicks"),
        State(ids.editor, "data"),
        State(ids.draft, "value"),
        prevent_initial_call=True,
    )(save)
    clientside_callback(
        AGE_SCRIPT,
        Output(ids.label, "hidden"),
        Output(ids.time, "children"),
        Output(ids.time_tooltip, "label"),
        Input(ids.edited_at, "data"),
        Input(ids.relative_time_interval, "n_intervals"),
    )
    # Fades the note's bottom line while more of it is below, and starts a
    # newly drawn note at its top. Whether it overflows depends on the card's
    # width, which the server never knows.
    clientside_callback(
        ClientsideFunction(namespace="scenario_notes", function_name="fade"),
        Output(ids.fade_sink, "data"),
        Input(ids.text, "children"),
        State(ids.config, "data"),
    )
    clientside_callback(
        ClientsideFunction(namespace="scenario_notes", function_name="controller"),
        Output(ids.editor, "data"),
        Output(ids.shown, "data"),
        Output(ids.dialog_state, "data"),
        Output(ids.dialog, "opened"),
        Output(ids.draft, "value"),
        Output(ids.card, "data-editing"),
        Output(ids.card, "data-unsaved"),
        Output(ids.card, "data-scenario"),
        Output(ids.card, "data-dialog"),
        Output(ids.error, "children"),
        Output(ids.char_count, "children"),
        Output(ids.filter_history, "data"),
        Output(ids.question, "children"),
        Output(ids.waiting_line, "children"),
        # The dropdown's and the filter's values first: a pick, or a filter
        # change that drops the edited scenario, has already happened when
        # the controller hears of it. The other Inputs are written by no
        # callback, which also keeps the renderer from pruning the first call
        # on a visit where the selection callback writes neither dropdown.
        Input(ids.scenario_dropdown, "value"),
        Input(ids.playlist_filter, "value"),
        Input(ids.edit, "n_clicks"),
        Input(ids.add, "n_clicks"),
        Input(ids.cancel, "n_clicks"),
        Input(ids.draft, "value"),
        Input(ids.save_result, "data"),
        Input(ids.held, "data"),
        Input(ids.keep, "n_clicks"),
        Input(ids.discard, "n_clicks"),
        # Escape and a click outside close the modal by this prop alone.
        Input(ids.dialog, "opened"),
        # A run held for a moment while the text was dirty, then answered
        # once it was clean again, is let through at once.
        Input(ids.waiting, "data"),
        State(ids.editor, "data"),
        State(ids.shown, "data"),
        State(ids.dialog_state, "data"),
        State(ids.filter_history, "data"),
        State(ids.note, "data"),
        State(ids.config, "data"),
    )
