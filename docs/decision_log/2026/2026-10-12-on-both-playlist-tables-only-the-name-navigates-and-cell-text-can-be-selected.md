# 2026-10-12: On Both Playlist Tables Only The Name Navigates, And Cell Text Can Be Selected

Status: Accepted

A click anywhere in a row of the Playlists table opened that playlist, while
on a playlist's scenario table only the scenario's name did anything, and on
both tables almost no text could be selected. Now one cell in each row
navigates on both tables, the name, and the text of every other cell can be
selected and copied. Dragging across a name to select it does not open it.
A Ctrl+click anywhere in a name's cell opens it in a new tab.

**Ruling.** By the maintainer, in chat on 2026-10-12: "Agreed on R1,R2,R3."
R1 was name-only clicks on both tables, and R3 was selectable text in every
cell but the merged ones, with a guard against a drag counting as a click.
The investigating session and a second-opinion consult had each recommended
both. There was no proposal. R1 reverses the full-row click target that the
[2026-07-03 entry](2026-07-03-playlists-routes-are-stable-the-bare-route-selector-is-transitional.md)
asked for. R2, the browser search, is
[its own entry](2026-10-12-both-playlist-tables-draw-every-row-so-a-browser-search-reaches-them.md).

**What a click does now.**

- A click anywhere in the Playlist name cell opens that playlist's scenario
  table. A click anywhere in a table's Scenario cell opens that scenario on
  the Scenario Performance page. That was already so on the scenario table.
- No other cell navigates. The eye and delete icons act as before.
- The name cell shows the pointer cursor across its whole width, because the
  whole cell is the target. A row no longer does. The hover tint stays on
  both tables.
- A modified click on a name's text is still the browser's own, as on any
  link: a new tab on Ctrl, a new window on Shift. Enter on a focused name
  still opens it.
- A modified click in a name cell beside the text never navigates the
  current tab. With Ctrl or Meta it opens the name in a new tab, and with
  Shift or Alt alone it opens nothing.

**Why the row stopped being the target.**

- Selecting text and clicking a row cannot share a cell. Measured with
  selection switched on: a drag inside one cell of the Playlists table opened
  that playlist, in Edge and in Firefox, and so did a double-click.
- The full-row target already carried three exceptions, the Benchmark ID cell
  and the two icon cells, and a click that missed an icon opened a playlist.
- The 2026-07-03 entry asked for a full-row target when a row click was the
  only way into a playlist. The name became a real link ten days later, on
  2026-07-13, so the row was no longer the only affordance.
- The two tables are consecutive steps of one drill-down, and they now answer
  a click the same way.

**Selectable text.** One stylesheet rule makes every cell's text selectable on
both grids. It replaces the class that did it for the two ID columns alone.
AG Grid's own switch, `enableCellTextSelection`, stays unused: the grid
refuses it on a table with merged cells, which a benchmark's scenario table
has. The merged Category and Subcategory cells stay unselectable, as the grid
leaves them. Cells keep the grid's arrow cursor. The text cursor the ID cells
had was there to override the pointer a row handed them, and that pointer is
gone.

A name is the one text a double-click cannot select. Its cell navigates on
a click, so the first click of a double-click opens it. A name is selected
by dragging across it from beside its text, which is the drag the guard
protects.

**The guard.** `assets/gridSelectionGuard.js` is one capture listener on the
document. A browser sends a click when a drag ends on the element it began
on, and a name cell navigates on a click anywhere in it, so dragging across a
name to select it would open it. The listener swallows a click inside either
grid when the pointer moved more than 3 px during the press and text is
selected. It lets three kinds of click through:

- A click with no movement. A selection made earlier and still on screen
  therefore never blocks a plain click on a name or a header.
- A modified click on a name's link, which keeps opening a new tab or
  window, and a modified click in a cell that does not navigate.
- A click from the keyboard.

The same listener handles a modified click in a name cell beside the link,
as the section on that click says. It finds a grid by its class and a name
cell by its column's class, so tests tie those class names in the script to
the layouts and the column definitions.

**Verified on the built branch,** in headless Edge and Firefox, 26 checks in
each, on the Playlists table and on a grouped scenario table:

- A plain click, a double-click, and a drag inside another cell all stay on
  the page. In Edge the double-click selected text in the cell.
- A plain click on a name opens it, on the link's text and in the cell's
  empty part, and also with a selection already on screen.
- A drag across a name from the cell's empty part stays on the page, and in
  Edge it selects the name. With the guard script blocked, that same drag
  opened the page on both tables, and no other behavior check changed.
- Ctrl+click opens a new tab and leaves the page. Enter on a focused name
  opens it. With a selection on screen, a header click still sorts. The eye
  icon still hides a row.
- The name cell has the pointer, and the row and the cell checked beside it
  do not. Cell text computes as selectable, and the merged cells as not.

**Checked by hand.** The automation delivers a double-click to Firefox as
two single clicks, and its Firefox drags selected text from other cells and
rows, on the old build as on the new one. So the maintainer tried the built
branch by hand in Firefox on 2026-10-12, and reported each of these as
working:

- A double-click selects a value, and it can be copied.
- A drag across the text of one cell selects that text.
- A drag across a name, from the empty space beside it, selects the name
  and does not open it. A click on the name afterwards still opens it.
- A merged cell's label does not select.
- A click on any other cell does nothing, and a click on a name or in the
  empty part of its cell opens it.

**A modified click beside a name.** The hand test found a defect. A
Ctrl+click on a name's text opened a new tab, and a Ctrl+click in the same
cell beside the text navigated the current tab. The link is only as wide as
its text, and a click beside it reached the grid's own route, which runs on
the server and cannot see modifier keys. It predated this change: the link
and the scenario route were as they had been, and before it the Playlists
table's whole row behaved this way. It was first recorded as a minor defect,
and a second change the same day fixed it, at the maintainer's request.

The fix is in the guard script alone. The link, the stylesheet and both
routes are as they were, so nothing moves and every plain click and drag
behaves as the hand test found it. The capture listener now also swallows a
modified click that lands in a name cell outside the link, so the grid never
sees it:

- With Ctrl or Meta it opens the link's address in a new tab, through
  `window.open`. Both browsers open that tab the way the held key asks. In
  Firefox it opened in the background, as the tab from a Ctrl+click on the
  name's text does.
- With Shift or Alt alone it opens nothing. A Shift+click there still
  extends a text selection, which is the browser's own use of that click.
- A modified click that ends a drag that selected text opens nothing, as a
  plain one navigates nowhere. Before the fix a Ctrl+drag across a name
  navigated the current tab.

On the name's own text a modified click stays the browser's, as it is on
any link, and the fix does not touch it. Measured there: Ctrl opens a new
tab and Shift a new window in both browsers, Alt downloads the page in Edge
and does nothing in Firefox, and Meta alone does nothing in Firefox. Edge on
Windows reads a click with Meta alone as a plain click, so on the name's
text it navigates the current tab, as it does on every link.

**Verified for the modified click,** in headless Edge 155 and Firefox 157,
126 checks in each, on the Playlists table and on a scenario table with
one-line and with two-line names:

- A Ctrl+click beside a name opens one new tab at the name's address and
  leaves the page. The points tried were the gap right of the text, each
  side padding, and the strip above the text. A two-line name's link fills
  its cell but for the side padding, so there the padding was the test.
- In Firefox that tab opens in the background with no opener, as the tab
  from the name's text does. Edge reports it as a tab of the same window,
  as it does the tab from the name's text.
- Shift, Alt and Meta at those points leave the page. Shift and Alt open
  nothing, and Meta opens one new tab.
- A plain click at every point still opens the name in the current tab.
- A Ctrl+drag and a Shift+drag across a name from the padding stay on the
  page and open nothing. With a selection already on screen, a Ctrl+click
  beside a name still opens its tab.
- Every name, link and cell sits where it did and is styled as it was, on
  all 110 rows at two window widths, and a clipped name still ends in an
  ellipsis.
- The 26 checks of the first verification pass again in both browsers.
- With the guard script put back as it was before the fix, on the same
  build, the same run failed 59 checks in each browser. Every one of them
  was a modified click or drag beside a name, and no other check changed.

**The modified click, checked by hand.** Every check above was scripted, in
a headless browser. The maintainer then tried the fix by hand in Firefox on
2026-10-12. A Ctrl+click in the empty space beside a name opened a new tab
and left the page, on the Playlists table and on a scenario table, so the
browser's pop-up blocker did not stop it. A Shift+click there opened
nothing. A plain click there still opened the name, and a drag across a
name from the empty space still selected it without opening it.

**Not verified.**

- Whether Edge opens the tab from a Ctrl+click beside a name behind the
  current one. Headless Edge reports every page as visible.
- Cmd on a Mac.
- A drag across several cells and rows in Firefox. The hand test reported
  no problem with one, without saying what it selected.
- A drag down several rows after a sort. In Edge it picked up text from 14
  rows for 4 dragged over, because the grid leaves rows in the page in their
  old order. `ensureDomOrder` fixes that and is left for a change of its own,
  for the reason the browser-search entry gives.
- One console line. The first of four Firefox runs logged a bare "Error"
  with every check passing. The three runs after it were clean, and it was
  not traced. One Firefox run of the modified-click checks logged it too, on
  the Scenario Performance page after a plain click on a name had opened
  it, and 40 scripted repeats of that step did not bring it back.

**Rejected.**

- Full-row clicks on both tables. The first click of a double-click
  navigates, so a value could never be selected that way.
- Leaving the two tables different, with the reason written down.
- A link that navigates only from its text. It needs no guard, and no
  modified click could miss it, but it shrinks the target the scenario table
  has always had.
- For the modified click, a link that fills its cell. A block link with
  link dragging switched off fixed the Ctrl+click in both browsers. In Edge
  it broke the drag that selects a name: a press in the link's empty part
  started no selection, and the click that ended the drag opened the name.
- For the modified click, handing the click on to the link as a scripted
  click with the same keys held. Both browsers treated it as a click on the
  link, which was right for Ctrl. It also repeated beside the name
  everything a browser does with a link. In Edge a click with Meta alone
  navigated the current tab and an Alt+click downloaded the page, and in
  both browsers a Shift+click opened the name as well, on the click that
  extends a selection.

**Unchanged.** The routes, the two icon cells, sorting, the filter boxes, and
the Columns menu. A click that closes the Columns menu still acts on what it
lands on, which now matters only on a name cell.

**Provenance.** Requested by the maintainer on 2026-10-12, with no proposal.
Shipped in
[PR #364](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/364).
The fix for the modified click beside a name followed in
[PR #365](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/365).
