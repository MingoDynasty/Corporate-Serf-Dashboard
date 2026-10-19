# 2026-10-18: Unsaved Note Text Is Never Lost To A Change Of Scenario Or Page

Status: Accepted

While a scenario note has unsaved changes, nothing the page does on its own
moves it: Follow waits, and the card names the scenario of the run that
waits. Every change of scenario the player makes, and every way of leaving
the page the app can catch, asks first in a dialog. A reload, a closed tab or another site gets the browser's own prompt,
so only a crash or a killed browser loses unsaved text without a question.

**Ruling and delivery.** SN3 of the scenario notes proposal
([#390](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/390)),
ratified by the maintainer on 2026-10-18 as amended: "I ratify the scenario
notes proposal, SN1 to SN8, as at 88aa8b0." Their agreements in the design
discussion: explicit buttons ("Having explicit buttons also means it trivial
for the user to copy and paste the notes without editing"), protection from
Follow ("there is always the possibility of a delay between the run
finishing, CSV file getting created, and CSV file getting ingested"), and the
dialog for a change they make themselves, which "really encourages the user
to settle the issue as soon as possible". After the first review they chose
that leaving the page asks first, and that the run toast's link is stopped
and selects in place. Built in
[#PRTWO](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/PRTWO).
Current behavior is in
[run_history.md](../../specs/run_history.md#editing-a-note).

**The rules.**

1. **Edit** opens a text box with Save and Cancel. Reading never opens the
   editor.
2. The editor has unsaved changes while its text differs from the text it
   opened with. Typing a word and deleting it leaves none.
3. **Follow waits** while the note has unsaved changes. The run's toast still
   shows, and the card names where the page will go: `A run on {scenario} is
   waiting. Press **Save** or **Cancel** to show it.` Save, Cancel or undoing
   every change moves the page once, to the newest waiting run's scenario,
   with the filter clearing Follow does. A run on the edited scenario ends
   the wait, and so does turning Follow off; turning it on brings none back.
4. **A change the player makes asks:** a pick in the Selected scenario
   dropdown, the run toast's link, a name in the run list's All scenarios
   view, and a Playlist filter change that leaves the edited scenario off the
   list. Keep editing puts the old selection back. A toast's link to the
   edited scenario itself is stopped, with no dialog. While the dialog is
   open its destination is fixed: a run waits in the card and a toast's link
   does nothing.
5. An editor with no unsaved changes just closes when the scenario changes.
6. A save goes to the scenario the editor opened on.
7. Escape does nothing in the editor. In the dialog, Escape and a click
   outside mean Keep editing.
8. **Leaving the page asks:** the navbar, the header title and **Open
   scenario table** open the same dialog, and so do the browser's back and
   forward buttons. Save or Discard then goes. A reload, a closed tab or
   another site gets the browser's prompt.
9. A failed save keeps the editor open, with its error under the buttons, and
   every protection above. From the dialog a failed save acts as Keep
   editing.

**The dialog.** Title `Your scenario note isn't saved`, no close button, and
focus starts on Keep editing so Enter can't throw text away. Its question
names the note's scenario and where the player asked to go, or that the
filter's list no longer holds it, or that the player is leaving the page.
Discard and Save drop a waiting run: the player chose where to go.

| Route | What has already happened | Keep editing |
|---|---|---|
| A pick in the dropdown | The dropdown moved, and the chart and the other cards redraw behind the dialog. The note card does not. | The selection callback writes the old scenario back, and the browser remembers it, so a reload opens on it. |
| A filter change dropping the edited scenario | The Select dropped it. | The old filter and scenario are written back. |
| The run toast's link | Nothing: the click is stopped before the page is drawn again. Save or Discard selects the scenario in place, clearing a filter in its way; the address stays. | Nothing to undo. |
| A name in the All scenarios view | Nothing: the selection callback holds it. | Nothing to undo. |
| A link that leaves the page | Nothing: the click is stopped. Save or Discard clicks the link again, past the guard. | Nothing to undo. |
| Back or Forward | The address moved. The guard keeps the event from Dash Pages and puts the address back at once. Save or Discard moves again and lets it through. | Nothing to undo. |

**How it is built, and why so.**

- **The editor's controller runs in the browser**
  (`scenario_notes.controller` in `assets/scenarioNotes.js`). Whether a change
  of scenario asks is decided where the text box is typed into, when the
  change lands. A server callback would decide on a text a round trip old: a
  character typed while Follow's move was on its way would be closed over.
  Measured at the build by holding that move in the page while a character
  was typed: the dialog asks, and Keep editing keeps the text.
- **The card is drawn only from the scenario it shows,** a store the
  controller alone writes when it lets a change through. A run, the 30-second
  tick, the filter, the Score threshold and a pick the dialog holds never
  redraw it, and the text box is never drawn again under the player.
- **The selection callback stays the one writer of both dropdowns.** It holds
  a run (a store of its own, since the run summary replays its last value to
  every later call) and a name in the list, and it carries out the
  controller's four answers: release the wait, select a scenario, put the old
  values back, drop the wait. The controller writes that request with
  `set_props`. Declared as its output, the store would close a loop through
  the dropdown the controller takes as an input, which the renderer refuses;
  a test walks the page's callback graph for loops.
- **The guard listens on `window` in the capture phase,** so it runs before
  React's root listener and before Dash Pages. For a link it calls
  `preventDefault` and `stopImmediatePropagation`. For a history move it
  stamps each entry's place into its state, so it knows how far a `popstate`
  moved and can move back. It reads the card's `data-unsaved` attribute from
  the page, so a page that is gone guards nothing.
- **The browser's prompt** comes from a `beforeunload` listener added only
  while the note has unsaved changes: a page with one is kept out of the
  back-forward cache. The browser draws it, so it has no app copy, and it
  shows only after a user gesture, which typing is.
- The dialog's question and the waiting line are filled in by the controller
  from templates the card's Python module owns, so neither is a round trip
  behind what it describes, and no copy lives in the script.

**Save errors.** A file from a newer build refuses the save with the schema
machinery's own message, which says to update the app. Any other failure
shows `Couldn't save the scenario note. See data/logs/debug.log.`, and the
log has the cause. That is the proposal's Copy block read as written; the
store's PR had suggested the one line for every failure.

**Measured at the build,** in headless Edge and Firefox on a scratch state
root with the maintainer's stats copied in and runs copied into its stats
folder as they landed: every rule and route above, each answer from each
route, a failed save, a file from a newer build, a broken file, the count
and the cap, the unload prompt with and without unsaved changes, and the
typing-and-run race. The PR's description has the list.

**Set aside.** Saving as you type; closing the editor when it loses focus;
Escape undoing the edit; asking in the card instead of a dialog; locking the
dropdown; pausing Follow whenever an editor is open; keeping the editor on
the old scenario while the page shows the new one; losing unsaved text when
the player leaves; leaving the back and forward buttons to discard; keeping
the draft in session storage and restoring it on return.

**What this changes in older entries.** Each keeps its text and gains a dated
note.

- [2026-10-12, Follow and a scenario link](2026-10-12-follow-and-a-scenario-link-clear-a-playlist-filter-that-does-not-list-the-scenario.md):
  Follow selects the scenario just played except while a note has unsaved
  changes, and the selection callback gains the note card's answers and the
  Follow switch as inputs.
- [2026-10-13, the run toast](2026-10-13-a-run-toast-is-plain-and-shows-on-every-page.md):
  on Run History, while a note has unsaved changes, its link asks and selects
  the scenario in place.
- [2026-10-14, the All scenarios view](2026-10-14-the-run-list-has-a-second-view-all-scenarios-that-shows-each-session-whole.md):
  a name pressed in the tree asks first while a note has unsaved changes.

Proposed in
[#390](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/390).
