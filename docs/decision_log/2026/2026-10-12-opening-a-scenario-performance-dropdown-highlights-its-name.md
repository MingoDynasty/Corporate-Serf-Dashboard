# 2026-10-12: Opening A Scenario Performance Dropdown Highlights Its Name

Status: Accepted

Clicking the playlist filter or the scenario dropdown used to empty the
field, so the selected name could not be copied. The field now keeps the name
and highlights it, and the first keystroke still replaces it with a search.
One click and a copy takes the whole name, and a drag takes part of it.

**What changed.** Both of Home's `dmc.Select`s drop `clearSearchOnFocus` and
mark their input with `SELECT_HIGHLIGHT_ON_OPEN_CLASS`.
`assets/selectHighlightOnOpen.js` highlights the name in any input carrying
that class when its list opens. No copy changed: the placeholder still shows
when nothing is selected.

**Why not only drop the prop.** With the name left in and a cursor in it,
typing inserts into the name and matches nothing, so every search would start
with clearing the field by hand. Search is the common action here and copying
the rare one. Keeping the name costs browsing nothing: Mantine filters only
while the text differs from the selected option's label, so an untouched name
still lists every option.

**What the script catches.** Mantine opens the list on focus, on a click, on
an arrow key, and on an edit, and reports none of them to Dash, so each is
handled at the document:

- A primary press on a closed field. When the button comes up, a cursor
  becomes a highlight of the whole name, and a range is left alone, which is
  what keeps a drag. Whether the list was closed is read at `mousedown`,
  because the press itself opens it. The check runs in a zero timeout:
  Chromium collapses a click on highlighted text only after the click event
  (measured in Edge on 2026-10-12, where the selection was still whole in the
  click handler and a cursor in the timeout), and Firefox collapses it before.
- A primary press on a closed field's label. It highlights the whole name
  whatever the selection, because no drag can start there.
- Focus arriving by any route but a press on the field: its label, a
  right-click, Tab, the window coming back to the front. `focusin` highlights
  the whole name, in a zero timeout because the browser restores its own
  selection after the event.
- An edit in a focused field whose list is closed, the state a pick or Escape
  leaves, with the cursor after the name. `beforeinput` highlights the name
  first, so the edit replaces it.
- ArrowDown or ArrowUp in that same state.
- A right-click in that same state, which opens no list. A cursor becomes a
  highlight of the whole name, and a range showing there is left alone.

A second click while the list is open is left to the browser, so it places a
cursor.

**A selection left over from an earlier visit.** An unfocused input keeps its
last selection, and Chromium brings it back when focus returns by any route
but a press on the field. A partial one then takes the next keystroke and
leaves the rest of the name in the search: with "10 Sphere H" left selected
in "10 Sphere Hipfire Extra Small", typing "zq" searched for "zqipfire Extra
Small". The first version of the script kept any range it found after a
press, taking it for a drag, and had no rule for focus. Review
on [PR #360](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/360)
found the label case. The right-click and the returning window have the same
cause and failed the same way. So a range is kept only after a press on the
field itself, the one place a drag can start, and every other way in
highlights the whole name. Firefox highlights the whole field on label focus
and did not show the label case.

**Rejected: highlight when the list closes.** A `MutationObserver` on the
open-list attribute could highlight a freshly picked name. The name reaches
the input one render after the list closes, because dmc controls the value
and Mantine then sets the text from an effect. A zero timeout landed after
that render in Edge and before it in Firefox, where the highlight was lost.
The event-time rules depend on no render order.

**Upstream coupling.** The script tells an open list from a closed one by
`data-expanded` on the input, which Mantine sets only while the list is open
(it sets no `aria-expanded` on an input target). Without it every field reads
as closed, and each keystroke of a search replaces the one before.
`tests/test_select_highlight_on_open.py` fails if the bundled build stops
writing the attribute, and if `clearSearchOnFocus` comes back beside the
class, which would empty the field before the script could highlight it.

**Also fixed.** `clearSearchOnFocus` emptied the field on every open,
including the open caused by the first keystroke after a pick, so that
keystroke was lost ("sphere" searched for "phere").

**Left alone.** Searching for the option that is already selected and picking
it again leaves the typed text in the field until focus leaves. The value did
not change, so Mantine's effect never runs. It did the same before this
change.

**Verified.** Headless Edge, Chrome, and the installed Firefox, both
dropdowns on the real page. A first set of 36 checks passes in each: click,
copy, drag, a second click, typing, mouse and keyboard picks, an arrow key,
Tab, the label, a keyboard pick after a right-click, and the highlight
outlasting the page's one-second updates. A second set of 30 passes in each,
all starting from a partial selection left behind: the label, a click inside
and outside the old range, a fresh drag, Tab, a right-click, focus handed
back by script, and a right-click and a label click on a focused field with
its list closed. The script as first written failed 14 of those 30 in Edge.
The automation cannot double-click in Firefox, so double-click word selection
was automated in Edge only. The maintainer tried the page by hand in Firefox
the same day, before the focus and right-click rules were added, and
confirmed it works.
