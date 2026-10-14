# 2026-10-12: The Run List Is Built On AG Grid Community, And NVDA Is Run On The Built List

Status: Accepted

The run list on Run History is built on the grid the app's other tables use,
in its free edition, with session rows the app draws itself. The free edition
has no tree, so the list is a grid made to behave like one, and it tells a
screen reader less than a real tree would. Because of that, the NVDA screen
reader was run on the finished list before the page went public, and all five
tasks it was given can be done. Any later change to what a screen reader
hears, to the keys, or to where focus goes repeats that walk.

**Rulings.** By the maintainer, 2026-10-12, on
[PR #356](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/356):
"I ratify the proposal." This entry is row R4, ratified as recommended, with
the check on the built list that was added at the direction checkpoint.
Before it, the maintainer, 2026-10-10, after trying both prototypes in
Firefox and reading the library research: "let's go with AG Grid". Asked how
to record that: "Take it as lean". That lean predates the NVDA result on the
prototypes. On 2026-10-12, with that result read, the maintainer agreed to
the check. The row was contested in review, and the alternative not taken is
recorded below as prototype C. The list was built in
[#371](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/371).
What the list does today is in
[run_history.md](../../specs/run_history.md#the-run-list), and what NVDA said
is in
[run_history_list_nvda_walk.md](../../research/run_history_list_nvda_walk.md).
This entry holds the argument, the numbers, the library facts, and the rule
the check leaves behind. What the list shows, and why, is in
[the second-column entry](2026-10-12-the-run-list-is-a-second-column-beside-the-chart.md).

**R4, the library.** The list is built on dash-ag-grid 35.3.0 in its free
edition, AG Grid Community. A session row is a full-width row drawn by the
app's own script, and opening a session is a filter over the rows. Before
the page went public, NVDA was run on the built list and what it said was
recorded.

**Two prototypes.** A technical trial on 2026-10-10 built the list six ways
against `main`. Two worked: this one, called A, and a list the app's own
script draws as an ARIA treegrid, called C. The trial recommended C. The
maintainer leaned to A.

For A:

- **One table library for the whole app.** It shares the playlist tables'
  theme variables, and the shared Columns menu already talks to its API.
- **It does not care how many rows are loaded.** It keeps about 39 row
  elements in the page whatever is open. C slows once thousands of rows are
  open at once: 935 ms in Edge with all 12,129 rows of the whole history
  open, against 46 ms for A. Version 1 loads 30 sessions of one scenario at
  a time, 36 to 484 rows in the trial, so this is a fact about scale and not
  a reason for version 1.
- **NVDA can read it and work it.** The pass on the prototypes found nothing
  that makes A unusable where C works. A also reads every cell of a run row
  with its column heading, which C does not.
- **No free library does more.** The research found none that pairs a free
  licence, a released treegrid, a pinned row, row virtualization, and a
  build that runs on the app's React 18.3 without a new toolchain.

Against A:

- **It is a grid made to look like a tree,** through nine pieces of
  grid-specific work, listed below. Each is a place an AG Grid upgrade can
  break.
- **That risk has a concrete case.** AG Grid 36.0.0 replaced its row
  containers, and 36.0.1 fixed regressions in two of the options A relies
  on. The Dash wrapper had only a release candidate for 36. Every workaround
  was checked on AG Grid 35.3.1 only, so moving to 36 means checking all of
  them again.
- **It tells a screen reader less, and NVDA bore that out.** Its root role
  is `grid`, and a row's depth is never announced. The open state sits on a
  button inside the row. In Firefox the pinned row and the first body row
  are both announced as "row 2", and NVDA counts 40 rows where there are 41.
  Tab stops at every cell, seven to a row. AG Grid sets the `treegrid` role
  only through its paid features, at $999 a developer, under terms that read
  as needing a further licence for an app handed to its users.
- **A landed run moved the keyboard user to another run.** The prototype
  held focus by grid position, so when the rows shifted, the cell under it
  became a different run's. C keeps focus on the same run. The ninth piece
  of work below is the fix, built for the first time in PR #371.

**What NVDA said of the prototypes.** NVDA 2026.2 was run on both on
2026-10-11, in Firefox 157.0.1 and Edge 155: 633 recorded steps, read from
NVDA's own log by a script. Both lists can be read and worked, and neither
is clean.

- **C does what the trial said it would.** NVDA announces each row's depth
  and whether it is open, and says "collapsed" and "expanded" when a row
  changes. That settled, for NVDA, a doubt the library research had raised:
  the newest evidence it found of a screen reader announcing those was from
  2020.
- **C has failures of its own.** In Firefox its list is two tab stops when
  it scrolls, and the first reads all 41 rows aloud. A fix for that was
  measured. It also reads a run row as one string, with no column headings.
- **A's prototype had three defects with a cheap fix.** The grid had no
  accessible name. A session row's button repeated the row's visible name,
  so the name was read twice. Opening or closing a row with Enter, Left, or
  Right said nothing, and only the button spoke.

This was evidence for the row, not a verdict on it. It removed the worry
that A can't be used with a screen reader, and it confirmed that C says
more.

**The numbers, on the prototypes.** 30 sessions loaded, 888 rows, medians in
milliseconds. "Run lands" is from the batch reaching the browser to the new
row painted. Both passes were headless, and the trial's chart was a
stand-in. The maintainer tried both prototypes by hand in Firefox.

| | A, Edge | C, Edge | A, Firefox | C, Firefox |
|---|---|---|---|---|
| Open one session | 6.8 | 3.2 | 10 | 2.9 |
| Run lands | 31 | 23 | 51 | 23 |
| Run lands, every row open | 35 | 43 | 60 | 25 |

Speed does not separate them at the planned size: neither takes more than
15 ms to open a session or more than 60 ms to show a landed run. Version 1's
view is smaller than the table's, 36 rows for the last-played scenario and
484 for the most-played one. The row model the server sends was 5 KB for 36
rows, 72 KB for 484, and 142 KB for 888, and sending all of it on every
landing was fast enough that neither prototype needed a smarter update.

**The numbers, as built.** PR #371 measured the real page, with the real
chart beside the list, 30 sessions loaded and about 480 rows, in headless
Edge 155 and Firefox 157.0.1. Two figures differ from the prototype's.

| Medians | Edge | Firefox |
|---|---|---|
| Open one session of 24 rows, to painted | 11 ms | 14 ms |
| A run lands: the batch reaching the browser, to the list painted | 106 ms | 109 ms |
| The script's own share of that | 6 ms | 10 ms |
| The same, to the chart drawn | 125 ms | 158 ms |
| A run lands with every row open, to the list painted | 106 ms | 115 ms |

- **A landing reaches the screen later than the prototype's did.** Over four
  rounds it read between 106 and 182 ms in Edge and between 109 and 246 ms
  in Firefox, where the prototype measured 31 ms. The prototype made one
  request. The page makes three in a row, which is what keeps the list to
  one draw per batch. The machine was not otherwise idle.
- **The model is larger.** 163 KB for the most-played scenario at 30
  sessions, 481 rows, where the trial measured 72 KB for 484. A row is keyed
  by its stats file's name, which is also a run event's id, so the
  latest-run card can find the latest run's row. That name is about 70
  characters, twice per row. It still needed no smarter update.
- **The server's part is small.** Over the maintainer's 9,135 runs: 3.6 ms
  to say whether a session is in progress, and 7.4 ms to build the
  most-played scenario's rows.
- **With every row open the grid still draws about 40 row elements,** 36 for
  474 rows in Edge.

**Library facts.**

- **Tree data and row grouping are paid features** in the installed AG Grid.
  A grid given `treeData` logs error #200 and shows the rows flat.
- **Rows sent as Dash components are ruled out.** Dash took 32 to 36 seconds
  to draw 30 sessions' rows, 887 rows and about 7,000 elements. A bare Dash
  4.4.1 app took 27.8 seconds for 1,000 rows of seven cells, and the cost
  per component doubles each time the count doubles.

**How it is built.**

- **One Python function builds the rows.** Its inputs are the run store, the
  selected scenario, and how many sessions to load. It returns a flat list
  of row records: session rows, run rows, dividers, and date headers. It
  also names the newest run and the rows that run forces open. A session's
  row is keyed by the session's first run, since a session has no stored
  identity.
- **The list rebuilds from the run store, not from the batch.** The batch of
  new runs only triggers it. Two open tabs race for each batch, and a list
  built from batches would miss runs in one of them.
- **The rows reach the grid as data,** through a store and a script,
  `assets/runHistoryList.js`, never as Dash components.
- **What is open never leaves the browser.** A row opens and closes with no
  request to the server.
- **Every string the script shows comes from Python,** with the rows or
  through the grid's `context`. The script holds no copy, and a test fails
  if one appears in it.
- **The script is not run by CI,** as no script in the repository is. Its
  source is pinned by text. Three tests tie it to Python so neither can
  drift alone: every function and renderer the grid names is defined in the
  script, the script reads no row field the rows do not carry, and it reads
  nothing from `context` that Python did not put there.

**The nine pieces of grid-specific work.** Each needs a recheck on an AG
Grid upgrade. The first eight were built in the prototype. The ninth came
from the NVDA pass and was first built in PR #371. All nine were checked in
Edge and Firefox there.

1. A session row is a full-width row with its own renderer. A full-width row
   has no cells, so its `gridcell` role is added by hand. Its `aria-colspan`
   is the number of columns shown, which the Columns menu changes.
2. Opening and closing is an external filter over a set of open row ids kept
   in script.
3. The current session is a pinned top row. The pinned row and the body rows
   have to change together, so rows go in through the grid's API and not the
   `rowData` prop the other tables use.
4. `embedFullWidthRows` and `ensureDomOrder` put the two kinds of row in
   reading order.
5. Enter, Space, Left, and Right are handled by a key listener.
6. Tab into a session row's button needs a listener that runs before the
   grid's own.
7. Sorting is off on every column.
8. The fixed column widths leave room for the scrollbar.
9. After new rows are applied, focus goes back to the cell of the same row
   id. The grid holds focus by position, so a landed run otherwise leaves a
   keyboard user on a different run.

One variation could have removed items 1, 4, and 6: ordinary rows whose
first cell spans every column. The proposal allowed it as a first try, and
PR #371 did not try it. NVDA was run on full-width rows, and R4 was ratified
on what it said. A spanned cell is a real cell of the `#` column, so a
session's name would be read with that column's heading, and the Columns
menu changes how many columns there are to span. It would not have changed
the `grid` role or the missing row levels.

**How a landing reaches the list.** The first row counts every scenario's
runs, and a divider counts runs on other scenarios, so the list has to be
rebuilt for a run the page does not show. The page's batch consumer writes
two stores in one answer: a summary, for a run on the scenario the page
shows, and the id of the batch's newest run, on whatever scenario. The list
takes the second and the scenario dropdown as inputs. Dash holds a callback
back only for a writer that is already queued. Written together, the
callback that moves the selection is queued for the summary at the moment
the list is queued for the run, and the list reads the dropdown, which is
that callback's plain output. So the list waits, and is built once, for the
scenario the page ends up on. A callback on the shell's batch itself would
have run before the selection callback was queued, and drawn the list twice.
The callback that tracks "In progress" takes the same store, so a run that
starts or reopens a session is one list request and not two. The rest of
that chain is in
[the filter-clearing entry](2026-10-12-follow-and-a-scenario-link-clear-a-playlist-filter-that-does-not-list-the-scenario.md).

**What the build did for a screen reader.** Five fixes, all in PR #371. The
first three answer the NVDA pass on the prototype, and the last two answer
the first walk on the built list.

- **The grid has an accessible name,** `Runs of {scenario}, by session`.
- **A session row's button is named `Session`.** The row reads its own name,
  so the button names what kind of row it is.
- **Opening or closing a row from the keyboard is announced,** through a
  live region with `role="status"`, as `Expanded` or `Collapsed`, the words
  a screen reader says itself for the same change. The other fix the pass
  inferred was to keep focus on the button inside the row. That would take
  the arrow keys away, since the grid moves between rows only while the row
  itself has focus.
- **A session row's parts each end with a space that takes no room.**
  Chrome and Edge read the parts run together in browse mode. A space
  between the parts does nothing: the row is a flex container, which drops
  it before a screen reader is given the text. The space that reaches it is
  inside a part, kept by `white-space: pre`, at `font-size: 0`. No part
  moved by a pixel.
- **Expand all is said,** through the same live region and the same two
  words. A button's changed name is not reported in Chrome and Edge.

**The check on the built list.** NVDA had been run on prototypes. Two of the
fixes that pass led to had never been tried: keeping focus on the same run
when a run lands, and announcing a row that is opened or closed from the
keyboard. A scripted keyboard walk shows where focus is, and can't show what
NVDA says. So NVDA was run again on the list as built, in Firefox, Chrome,
and Edge. Chrome was new to the walk. It shares Edge's engine, and the walk
checked that it says the same and did not assume it.

The walk was run twice on 2026-10-13, each time on the maintainer's "go":
NVDA 2026.2 in Firefox 157.0, Chrome 155, and Edge 155. The first walk found
two things with a cheap fix, the last two of the five above. The second ran
every walk again on the list with those fixes in it. **All five tasks can be
done in all three browsers. None failed.**

| Task | Result |
|---|---|
| Finding a session, and hearing whether it is open | Works, with one more key than it should need. A session row reads its date, length, and counts. It says whether it is open only from its button, or when it is toggled |
| Reading a session's runs: each value with its column heading, and which session the run is in | Works. Every cell is read with its column heading. Which session a run is in is heard by moving up to the session's row |
| Reaching a row beyond the ones on screen | Works. PageDown reached the last of about 475 rows in 14 or 15 presses, and Enter on Show older sessions left focus on the first session it loaded |
| Telling a check, a star, and a run with neither apart | Works: `Threshold passed`, `Below threshold`, `Threshold passed New PB`, and the whole reason for a run that is not judged |
| Staying on the same run when a new run lands | Works. Focus was in the same row, by its id, and the same column after each of two landings |

Six things still do not work well, and none stops a task. The first two had
no known fix before either walk.

1. A row's depth is never said. No fix is known in the free edition.
2. Firefox calls the current session's row and the first row under it both
   "row 2". No fix is known: it is AG Grid's markup for a pinned row.
3. Chrome's and Edge's spoken row numbers are one more than the row index
   near the top, and equal to it further down.
4. A session row does not say whether it is open when focus arrives on it.
   Its button says so, and so does toggling it.
5. In browse mode, NVDA's table key going up from a session's newest run
   skips the session row, in every column but the first.
6. Noise in browse mode: every cell says "clickable", and the list's name is
   said twice.

Not covered: Narrator, JAWS, and a person listening. No screen-reader user
has tried the list. NVDA ran muted, so the record is the text it sent to its
synthesizer. The walk takes the keyboard and the foreground window for about
four and a half minutes a browser, so it runs on the maintainer's word. Its
scripts are untracked, on the maintainer's machine.

**The rule the check leaves.** The record has to describe the list that is
public. A change to what a screen reader is told about a row, which key does
what, or where focus goes repeats the walk first. A change to how the list
looks does not. The rule has been applied once: PR #372 highlights the row
of the last run played with a class and two declarations, a background and a
weight, so the walk was not repeated, and the list's accessibility tree read
the same as before.

**A failed task is the maintainer's to decide.** It does not by itself hold
a release. They decide then: repair it first, ship with the failure
recorded, or rebuild the list's last step. The app's accessibility work is
best effort. The maintainer, 2026-10-12: "The app has never promised
screen-reader usability", and "Perhaps we can cross that bridge when we get
there." Making a repair a condition of going public was considered and not
taken. In the worst case it would have held the release on a promise the app
has not made. No task failed, so nothing went to the maintainer.

**What being wrong costs.** Both prototypes share one row model, a Python
function. Only the last step differs: about 370 lines of script for A and
500 for C. If that step is rebuilt, because a walk shows the list unusable,
for another screen reader, or because an AG Grid upgrade breaks the group
rows, nothing else moves. What it is rebuilt as is chosen then. Prototype C
is one candidate, and NVDA reads it as a tree. The other is a plain table
with disclosure buttons, which the library research found practitioners
prefer and neither prototype builds.

**If the maintainer had chosen the treegrid:** the repository would own the
rendering, the keyboard model, and a second table idiom with no library
under it, and the list would have no row virtualization.

**Seen in the build and left alone.**

- **A browser's find-in-page cannot reach a row that is not drawn,** because
  the list keeps the grid's row virtualization. R4 counts the virtualization
  for the grid. Both playlist tables gave it up for that reason on
  2026-10-12
  ([that entry](2026-10-12-both-playlist-tables-draw-every-row-so-a-browser-search-reaches-them.md)).
  With every session open the list holds about 500 rows at 30 sessions,
  which the grid could draw.
- **The marks column can read long to a screen reader.** A run nothing
  judges reads its whole reason.

The trial's scripts and results, the mockup, and the design notes are
untracked, in the maintainer's main checkout.

Proposed in
[PR #356](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/356),
which merged as `a65f72d`. Shipped in
[#371](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/371),
hidden, with the row highlight in
[#372](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/372),
and made public in
[#373](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/373).
The proposal file, `docs/proposals/run_history_proposal.md`, is deleted, and
git history keeps it.
