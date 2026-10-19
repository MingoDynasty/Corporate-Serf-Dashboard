"""The scenario note card on Run History: what it reads, what a save does, its wiring.

The rules that move the page while a note has unsaved changes are the
selection callback's, in ``tests/test_scenario_selection.py``. The editor's
state machine runs in the browser (``assets/scenarioNotes.js``); these tests
hold what Python owns of it: the strings it fills in, the ids it is given,
and a callback graph the renderer accepts.
"""

import json
import re
from datetime import UTC, datetime
from pathlib import Path

import dash
import dash_mantine_components as dmc
import pytest
from dash import dcc, html, no_update
from dash._callback import GLOBAL_CALLBACK_LIST

dash.Dash(__name__, use_pages=True, pages_folder="")

from source.components import scenario_note_card as card  # noqa: E402
from source.kovaaks import scenario_notes_service as notes  # noqa: E402
from source.pages import run_history  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "assets" / "scenarioNotes.js"
IDS = run_history.NOTE_CARD_IDS
SCENARIO = "SmoothBot Perfected"


def _walk(component):
    yield component
    children = getattr(component, "children", None)
    if children is None:
        return
    if isinstance(children, (list, tuple)):
        for child in children:
            yield from _walk(child)
        return
    yield from _walk(children)


def _by_id(tree, component_id):
    return next(c for c in _walk(tree) if getattr(c, "id", None) == component_id)


def _write(payload: dict, scenario: str = SCENARIO, raw: str | None = None) -> Path:
    path = notes.scenario_note_path(scenario)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(raw if raw is not None else json.dumps(payload), encoding="utf-8")
    return path


def _note(text: str, scenario: str = SCENARIO, version: int = 1) -> Path:
    return _write(
        {
            "schema_version": version,
            "scenario": scenario,
            "text": text,
            "edited_at": "2026-10-09T17:24:00Z",
        },
        scenario,
    )


# --- What the card shows ------------------------------------------------------------


def test_with_no_scenario_the_room_holds_nothing():
    content = card.note_card_content(None)

    assert content.card_class == card.card_class(card.NoteState.NONE)
    assert content.text is None
    assert content.edited_at is None
    assert content.note == {"scenario": None, "state": "none", "text": None}


def test_a_scenario_with_no_note_shows_the_link():
    content = card.note_card_content(SCENARIO)

    assert content.card_class == "run-history-note-card run-history-note-card-missing"
    assert content.note == {"scenario": SCENARIO, "state": "missing", "text": None}


def test_a_note_shows_its_text_and_when_it_was_edited():
    _note("aim lower\nand slower")

    content = card.note_card_content(SCENARIO)

    assert content.card_class.endswith("-note")
    assert content.text == "aim lower\nand slower"
    assert content.edited_at == datetime(2026, 10, 9, 17, 24, tzinfo=UTC).timestamp()
    assert content.note == {
        "scenario": SCENARIO,
        "state": "note",
        "text": "aim lower\nand slower",
    }


def test_a_broken_file_shows_its_error_in_place_of_the_note():
    path = _write({}, raw="{not json")

    content = card.note_card_content(SCENARIO)

    assert content.card_class.endswith("-error")
    assert content.text == f"The scenario note file isn't valid JSON. File: {path}"
    assert content.edited_at is None
    # The editor opens on an empty box, not on the message.
    assert content.note["text"] is None


def test_a_file_from_a_newer_build_shows_its_message_and_offers_no_edit():
    _note("from later", version=2)

    content = card.note_card_content(SCENARIO)

    assert content.card_class.endswith("-future")
    assert "written by a newer version of this app" in content.text
    assert content.note["state"] == "future"


def test_the_card_is_drawn_from_the_shown_store_alone():
    """What redraws the note card: a change the rules let through, and a save.

    The drawing callback's one Input is the store the controller writes when
    it lets a change of scenario through. A run, the tick, the filter, the
    threshold and a pick the dialog holds never reach it.
    """
    (drawing,) = [
        entry
        for entry in GLOBAL_CALLBACK_LIST
        if entry["output"].startswith(f"..{IDS.card}.className...")
    ]
    assert [f"{dep['id']}.{dep['property']}" for dep in drawing["inputs"]] == [
        f"{IDS.shown}.data"
    ]


# --- Saving -------------------------------------------------------------------------

EDITOR = {"scenario": SCENARIO, "opened": "aim lower"}


def test_a_call_no_press_made_saves_nothing():
    """With duplicate outputs the save can be called as the page is drawn."""
    _note("aim lower")

    assert card.save_from_editor(None, EDITOR, "aim higher") == (no_update,) * 5
    assert card.save_from_editor("card", None, "aim higher") == (no_update,) * 5
    assert json.loads(notes.scenario_note_path(SCENARIO).read_text())["text"] == (
        "aim lower"
    )


def test_a_save_writes_the_text_and_draws_the_card_from_the_file():
    result, card_class, text, edited_at, read = card.save_from_editor(
        "card", EDITOR, "aim higher"
    )

    assert result == {"ok": True, "error": None, "via": "card", "text": "aim higher"}
    assert card_class.endswith("-note")
    assert text == "aim higher"
    assert edited_at is not None
    assert read["text"] == "aim higher"
    assert notes.read_scenario_note(SCENARIO).value.text == "aim higher"


def test_a_save_goes_to_the_scenario_the_editor_opened_on():
    """Whatever the page shows by then: the editor's own scenario."""
    card.save_from_editor("dialog", {"scenario": "Other", "opened": ""}, "theirs")

    assert notes.read_scenario_note("Other").value.text == "theirs"
    assert notes.read_scenario_note(SCENARIO).value is None


def test_saving_empty_text_deletes_the_note_and_shows_the_link():
    path = _note("aim lower")

    result, card_class, *_ = card.save_from_editor("card", EDITOR, "  \n ")

    assert result["ok"]
    assert card_class.endswith("-missing")
    assert not path.exists()


def test_a_save_over_a_broken_file_copies_it_aside_first():
    path = _write({}, raw="{not json")

    result, card_class, text, *_ = card.save_from_editor(
        "card", {"scenario": SCENARIO, "opened": ""}, "fresh"
    )

    assert result["ok"]
    assert (card_class, text) == (card.card_class("note"), "fresh")
    assert list(path.parent.glob(f"{path.name}.corrupt-*.bak"))


def test_a_save_refused_by_a_newer_file_says_so_in_its_own_words(monkeypatch):
    _note("from later", version=2)

    result, *rest = card.save_from_editor("card", EDITOR, "aim higher")

    assert not result["ok"]
    assert "written by a newer version of this app" in result["error"]
    assert result["error"].endswith(f"File: {notes.scenario_note_path(SCENARIO)}")
    # The card is left as it is: the editor stays open over it.
    assert rest == [no_update] * 4


@pytest.mark.parametrize(
    "failure",
    [OSError("disk full"), notes.SchemaPayloadError("holds more than 2,000.")],
)
def test_any_other_failed_save_is_the_generic_line(monkeypatch, failure, caplog):
    def fail(_scenario, _text):
        raise failure

    monkeypatch.setattr(card, "save_scenario_note", fail)

    result, *rest = card.save_from_editor("dialog", EDITOR, "aim higher")

    assert result == {
        "ok": False,
        "error": "Couldn't save the scenario note. See data/logs/debug.log.",
        "via": "dialog",
        "text": "aim higher",
    }
    assert rest == [no_update] * 4
    assert f'Couldn\'t save the scenario note for "{SCENARIO}"' in caplog.text


# --- The card's strings -------------------------------------------------------------


def _filled(parts: list, names: dict) -> str:
    """Fill a template as the controller does, with a control's name as ``**name**``."""
    text = ""
    for part in parts:
        if isinstance(part, str):
            words = part
            for key, value in names.items():
                words = words.replace("{" + key + "}", value)
            text += words
        else:
            text += f"**{part['control']}**"
    return text


def test_the_dialog_asks_in_the_copy_block_words():
    questions = card.DIALOG_QUESTIONS
    names = {"from": "SmoothBot Perfected", "to": "Smoothsphere Viscose"}

    assert card.DIALOG_TITLE == "Your scenario note isn't saved"
    assert _filled(questions["switch"], names) == (
        "Save your changes to the note on SmoothBot Perfected before you switch "
        "to Smoothsphere Viscose?"
    )
    assert _filled(questions["filter"], names) == (
        "The **Selected scenario** list no longer holds SmoothBot Perfected. Save "
        "your changes to its note first?"
    )
    assert _filled(questions["leave"], names) == (
        "Save your changes to the note on SmoothBot Perfected before you leave the "
        "page?"
    )
    assert (card.KEEP_EDITING_LABEL, card.DISCARD_LABEL, card.SAVE_LABEL) == (
        "Keep editing",
        "Discard",
        "Save",
    )


def test_the_waiting_line_and_the_count_read_as_the_copy_block_has_them():
    assert _filled(card.WAITING_LINE, {"scenario": "Air Voltaic Invincible 4"}) == (
        "A run on Air Voltaic Invincible 4 is waiting. Press **Save** or "
        "**Cancel** to show it."
    )
    assert card.COUNT_TEMPLATE.replace("{count}", "1,850") == (
        "1,850 of 2,000 characters"
    )
    assert card.COUNT_FROM == 1800
    assert card.SAVE_FAILED_MESSAGE == (
        "Couldn't save the scenario note. See data/logs/debug.log."
    )


def test_the_card_and_the_editor_carry_the_copy_block_words():
    page_card = card.scenario_note_card(IDS, toast_link_class="toast-link")
    edit = _by_id(page_card, IDS.edit)
    draft = _by_id(page_card, IDS.draft)

    assert isinstance(edit, html.Button)
    assert (edit.children, getattr(edit, "aria-label")) == (
        "Edit",
        "Edit scenario note",
    )
    assert _by_id(page_card, IDS.add).children == "Add a scenario note"
    assert isinstance(draft, dmc.Textarea)
    assert draft.placeholder == "Note for this scenario"
    assert getattr(draft, "aria-label") == "Scenario note"
    # The browser stops typing at the store's cap and cuts a paste there.
    assert draft.attributes == {"input": {"maxLength": notes.MAX_NOTE_CHARACTERS}}
    assert _by_id(page_card, IDS.save).children == "Save"
    assert _by_id(page_card, IDS.cancel).children == "Cancel"
    # The waiting line is announced as it appears.
    assert getattr(_by_id(page_card, IDS.waiting_line), "aria-live") == "polite"


def test_the_dialog_has_no_close_button_and_keep_editing_takes_focus_first():
    dialog = card.scenario_note_dialog(IDS)
    keep = _by_id(dialog, IDS.keep)

    assert dialog.title == card.DIALOG_TITLE
    assert dialog.withCloseButton is False
    # Focus is put back by the controller: Keep editing returns it to the box.
    assert dialog.returnFocus is False
    assert getattr(keep, "data-autofocus") is True
    assert [b.id for b in _walk(dialog) if isinstance(b, dmc.Button)] == [
        IDS.keep,
        IDS.discard,
        IDS.dialog_save,
    ]


# --- The stylesheet -------------------------------------------------------------------

STYLESHEET = REPO_ROOT / "assets" / "stylesheet.css"


def _css_block(css: str, selector: str) -> str:
    """Return the body of the top-level rule for ``selector`` alone."""
    match = re.search(
        rf"(?m)(?<!,\n)^{re.escape(selector)} \{{(.*?)^\}}", css, re.DOTALL
    )
    assert match, f"no {selector} rule in the stylesheet"
    return match.group(1)


def test_the_card_takes_the_room_from_240_to_800px_and_reading_never_sizes_it():
    """While reading, what the card shows is out of the flow: its box is the row's.

    So the chart under the row never moves between a note, none, a broken
    file and no scenario. The floor gives a card alone on a wrapped line
    five lines.
    """
    css = STYLESHEET.read_text(encoding="utf-8")
    box = _css_block(css, ".run-history-note-card")
    read = _css_block(css, ".run-history-note-read")

    assert "flex: 1 1 240px;" in box
    assert "max-width: 800px;" in box
    assert "min-width: min(240px, 100%);" in box
    assert "min-height: 132px;" in box
    assert "position: relative;" in box
    # The frame is always there, transparent with no note, so no state
    # changes the box by its border.
    assert "border: 1px solid transparent;" in box
    assert "position: absolute;" in read
    assert "inset: 0;" in read


def test_the_text_box_never_shows_less_than_three_lines():
    """Its height starts from nothing, so the row decides the card's height."""
    css = STYLESHEET.read_text(encoding="utf-8")
    box = _css_block(css, ".run-history-note-text-box textarea")

    assert "min-height: 69px;" in box
    assert "height: 0;" in box
    assert "resize: none;" in box


# --- The page script and the callback graph -------------------------------------------


def test_the_controller_is_given_every_id_and_string_it_fills_in():
    page_card = card.scenario_note_card(IDS, toast_link_class="toast-link")
    config = _by_id(page_card, IDS.config)

    assert isinstance(config, dcc.Store)
    assert config.data["ids"] == IDS._asdict()
    assert config.data["questions"] == card.DIALOG_QUESTIONS
    assert config.data["waiting"] == card.WAITING_LINE
    assert config.data["count"] == card.COUNT_TEMPLATE
    # The page script finds the card, where to ask, and the toast's link.
    assert getattr(page_card, "data-note-held-store") == IDS.held
    assert getattr(page_card, "data-note-toast-link-class") == "toast-link"


def test_the_script_defines_the_two_functions_the_page_registers():
    script = SCRIPT.read_text(encoding="utf-8")
    registered = {
        (
            entry["clientside_function"]["namespace"],
            entry["clientside_function"]["function_name"],
        )
        for entry in GLOBAL_CALLBACK_LIST
        if (entry.get("clientside_function") or {}).get("namespace") == "scenario_notes"
    }

    assert registered == {("scenario_notes", "controller"), ("scenario_notes", "fade")}
    assert "window.dash_clientside.scenario_notes = {" in script
    assert "controller: controller," in script
    assert "fade: fade," in script
    # It listens before React's root and Dash Pages do.
    assert 'window.addEventListener("click", onClick, true);' in script
    assert 'window.addEventListener("popstate", onPopState, true);' in script


def test_the_page_puts_the_card_and_the_dialog_in_its_layout():
    page = run_history.layout()

    assert _by_id(page, IDS.card).className == card.card_class("none")
    assert isinstance(_by_id(page, IDS.dialog), dmc.Modal)


def _keys(deps) -> set[str]:
    return {f"{dep['id']}.{dep['property']}" for dep in deps}


def _outputs(entry) -> set[str]:
    return {output.split("@")[0] for output in entry["output"].strip(".").split("...")}


def test_the_page_callbacks_form_no_loop_the_renderer_refuses():
    """A chain of callbacks that leads back to its start is refused in the browser.

    The note card nearly closes two: the controller takes the scenario
    dropdown and writes what the selection callback answers, and it takes the
    save's result and writes what the drawing callback takes. Each is broken
    on purpose, so a later edit that closes one fails here first. A callback
    that writes one of its own Inputs is allowed.
    """
    edges: dict[str, set[str]] = {}
    for entry in GLOBAL_CALLBACK_LIST:
        inputs = _keys(entry["inputs"])
        outputs = _outputs(entry)
        for source in inputs:
            edges.setdefault(source, set()).update(outputs - inputs)

    def loop_from(start):
        seen, stack = set(), [(start, [start])]
        while stack:
            node, path = stack.pop()
            for nxt in edges.get(node, ()):
                if nxt == start:
                    return path + [nxt]
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append((nxt, path + [nxt]))
        return None

    loops = [loop for loop in map(loop_from, list(edges)) if loop]
    assert loops == []


def test_the_selection_callback_is_the_controllers_input_but_never_its_output():
    """The controller writes the selection's request with ``set_props``."""
    (controller,) = [
        entry
        for entry in GLOBAL_CALLBACK_LIST
        if (entry.get("clientside_function") or {}).get("function_name") == "controller"
    ]

    assert f"{IDS.go}.data" not in _outputs(controller)
    assert {
        f"{run_history.SCENARIO_SELECTION_IDS.scenario_dropdown}.value",
        f"{run_history.SCENARIO_SELECTION_IDS.playlist_filter}.value",
    } <= _keys(controller["inputs"])
    # It isn't pruned on a visit where the selection callback writes neither
    # dropdown: it has Inputs that callback never writes.
    (selection,) = [
        entry for entry in GLOBAL_CALLBACK_LIST if f"{IDS.held}.data" in _outputs(entry)
    ]
    assert not _keys(controller["inputs"]) <= _outputs(selection)
