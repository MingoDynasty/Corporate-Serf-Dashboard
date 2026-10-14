# The Run History page's run list under NVDA

Date: 2026-10-13
Author: claude-opus-5-5 · effort: xhigh
Source revision: `63c8051` on pull request #371's branch. The list's code last changed in `1b92d82`

This is the record of what the NVDA screen reader said on the run list of the
Run History page, as built. The page's proposal
([PR #356](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/356))
makes this record a condition of the page going public, and names the five
tasks walked here. It is a measurement, not a decision. The proposal requires
the walk and not a repair: a task that fails goes to the maintainer.

**Run the walk again before the page goes public if the list has changed** in
what a screen reader is told about a row, in which key does what, or in where
focus goes. A change to how the list looks does not need it.

**It was run again on 2026-10-14,** when the list gained a second view, All
scenarios. That walk has its own section,
[the last in this file](#2026-10-14-the-walk-again-with-the-all-scenarios-tree).
Everything before it is the first record, as it was written.

## Summary

- **All five tasks can be done in Firefox, Chrome, and Edge.** None failed.
- **The walk was run twice, and every quote below is from the second.** The
  first, at `b0d9908`, found eight things that did not work well. Two had a
  cheap fix, and `1b92d82` made both. The second walk, at `63c8051`, ran
  every walk again on the list with those fixes in it.
- **Four fixes that had never been tried under a screen reader all work, in
  all three browsers.** Two are the ones the proposal named: a session row
  opened or closed from the keyboard is announced, and a run that lands
  leaves keyboard focus on the same run. Two are the ones the first walk led
  to: a session row's parts no longer run together, and Expand all is said.
- **Six things still do not work well.** None stops a task. They are listed
  under [What still does not work](#what-still-does-not-work), each with
  whether a fix is known.
- **Not covered:** Narrator, JAWS, and a person listening. NVDA ran muted, so
  every quote here is the text it sent to its synthesizer, read from its own
  log.

## How it was run

| | |
|---|---|
| Screen reader | NVDA 2026.2, an unpacked copy, muted, started and stopped by the script |
| Browsers | Firefox 157.0, Chrome 155.0.8059.40, Edge 155.0.4283.45, visible and maximized, at 1.5x scaling |
| App | The pull request's build at `63c8051`, on a scratch copy of five scenarios' stats files, 1,051 runs. The page showed VT DotTS Intermediate S5 |
| Keys | Real key presses to the foreground window: 184 in Firefox and 185 in each of Chrome and Edge, over six walks, then 37 steps of a seventh |
| Runs landed | Eight, each a stats file written to the scratch stats folder: two before the walks, and two in each browser's landing walk |
| Checks | The script checked where focus was, and what the live region was given, against a rehearsal without NVDA. All 96 checks held in each browser |

The walks are one per task, a pass of NVDA's browse mode by line, and a pass
of its table keys. Each starts from a fresh load of the page. In the quotes
below NVDA's items are joined by two spaces, as its log has them.

## The five tasks

### 1. Finding a session, and hearing whether it is open

**It works, with one more key than it should need.** Down from the column
headings reaches the current session's row, and Down again each session
under it. NVDA reads a session row's date, length, and counts. It does not
say whether the row is open until focus is on the row's button, or until the
row is toggled.

| Key | Firefox | Chrome |
|---|---|---|
| Down from the headings | `Session Oct 13, 4:26 AM In progress 1 min · 2 of 2 runs  row  not selected  row 2  2 of 33` | `Session Oct 13, 4:26 AM In progress 3 min · 4 of 4 runs  row` |
| Down to an older session | `Session Feb 13, 10:50 PM 9 of 9 runs  row  not selected  row 2  2 of 31` | `Session Feb 13, 10:50 PM 9 of 9 runs  row` |
| Tab, to the row's button | `Session  button  collapsed` | the same |

Edge said what Chrome said. The current session's length and counts differ
between the browsers because each walk landed runs.

**Opening and closing from the row is announced.** The row writes one word
to a live region, and NVDA spoke it once each time, in all three browsers:

| Key on the row | NVDA |
|---|---|
| Right | `Expanded` |
| Left | `Collapsed` |
| Enter | `Expanded` |
| Space | `Collapsed` |
| Left on a row already closed | nothing |

- **All 11 toggles from a row were spoken,** in each browser's log.
- **From the row's button,** Enter said `expanded` and Space said `collapsed`.
  That is the button's own state, and not the live region's word.
- **In browse mode,** Enter on a session row said `collapsed` twice when it
  closed and `expanded` once when it opened.

### 2. Reading a session's runs

**It works.** Every cell is read with its column heading, in focus mode and
with NVDA's table keys in browse mode.

| Key | Firefox | Chrome and Edge |
|---|---|---|
| Right, to the Score cell | `1,180  row 3  Score  column 3` | `1,180  row 4  Score  column 3` |
| Right, to the Marks cell | `Threshold passed  row 3  Marks  column 4` | `Threshold passed  row 4  Marks  column 4` |
| Browse mode, the table key across a run | `Time  column 2  clickable  11:08 PM`, then `Score  column 3  clickable  1,164` | the same |

**Which session a run is in is heard by moving up to the session's row.**
Nothing on a run's own cell names its session. In focus mode Up reaches the
session row from any column. In browse mode the table key reaches it down or
up the first column only: see the list below.

### 3. Reaching a row beyond the ones on screen

**It works.** With every session open, PageDown reached the last row in 14
presses in Firefox and 15 in Chrome and Edge, about 475 rows down. The grid
draws only the rows near the window, and NVDA read each row focus arrived on.

| Key | Firefox | Chrome |
|---|---|---|
| Enter on Expand all, to open every session | `Expanded`, then `Collapse all` | `Expanded` |
| PageDown, the last press | `Show older sessions  row  not selected  row 475  475 of 475` | `Show older sessions  row  row 477` |
| Enter on it | `Session Aug 31, 2025, 6:21 PM 9 of 9 runs  row  not selected  row 475  475 of 478` | `Session Aug 31, 2025, 6:21 PM 9 of 9 runs  row  row 477` |

After Enter on Show older sessions, focus was on the first of the sessions it
loaded, and NVDA read it. Edge said what Chrome said, two rows later.

### 4. Telling a check, a star, and a run with neither apart

**It works.** The Marks cell is read as words, and the four cases differ.

| Cell | NVDA, in focus mode |
|---|---|
| A check | `Threshold passed  row 3  Marks  column 4` |
| Neither | `Below threshold  row 9  Marks  column 4` |
| A check and a star | `Threshold passed New PB  row 10  Marks  column 4` |
| A run that is not judged | `Not judged. A scenario's first run, and the first run at a new sensitivity, aren't judged against the score threshold.  row 408  Marks  column 4` |

Those are Firefox's lines. Chrome and Edge said the same words with other row
numbers. In browse mode each mark is a graphic with its name:
`row 10  Marks  column 4  clickable  graphic  Threshold passed  graphic  New PB`.

### 5. Staying on the same run when a new run lands

**It works.** With focus in a run's Score cell, two runs were landed one
after the other. In each browser, after each landing, keyboard focus was in
the same row, by its id, and in the same column. The row had moved one place
down each time.

- **NVDA did not read the cell again.** Asked where focus was, it read the
  same value one row later: `1,180  cell  focused  row 4`, then
  `1,180  cell  focused  row 5`, in Firefox.
- **What NVDA said at a landing was the app's own toast:**
  `alert  Threshold passed`, then
  `VT DotTS Intermediate S5: 1180.00, 96.7% of PB.`, then `button`, at both
  landings in all three browsers.

## What the first walk led to

The first walk, at `b0d9908`, found two things with a cheap fix. Both are
fixed in `1b92d82`, and the second walk heard the difference.

| | First walk | Second walk |
|---|---|---|
| A session row read in browse mode, in Chrome and Edge | `Oct 13, 2:22 AMIn progress` and `Feb 13, 10:50 PM9 of 9 runs`: its parts run together | `Oct 13, 4:26 AM In progress` and `Feb 13, 10:50 PM 9 of 9 runs` |
| Enter on Expand all, in Chrome and Edge | nothing | `Expanded` |
| The same in Firefox | `Collapse all`, the button's new name | `Expanded`, then `Collapse all` |

- **A space between the row's parts would not have fixed the first.** That
  is the fix the first walk's record inferred. The row is a flex container,
  and the browser drops a space between its items, or at the end of one,
  before a screen reader is given the text. The space that reaches it is
  inside a part, kept by the stylesheet, and sized to nothing, so no part of
  the row moved. This was found by reading Chrome's and Edge's accessibility
  tree through the DevTools protocol, with no screen reader.
- **Firefox read a session row's parts as separate lines both times,** and
  gained no blank line from the fix.
- **Expand all reuses the live region's two words.** In Firefox NVDA now says
  the word and then the button's new name.

## What still does not work

None of these stops one of the five tasks. The first two were on this list
before either walk: the proposal names both as having no known fix.

| | What | Where | Fix |
|---|---|---|---|
| 1 | A row's depth is never said. A session row and a run row are told apart only by their words | All three | None known in AG Grid's free edition |
| 2 | The current session's row and the first row under it are both "row 2". NVDA counts 40 rows where Chrome and Edge count 41, and each later row is one lower than there | Firefox | None known. It is AG Grid's markup for a pinned row |
| 3 | A spoken row number is one more than the row's `aria-rowindex` near the top (`row 3` on index 2, `row 4` on index 3) and equal to it further down (`row 33` on index 33). Where it changes was not measured | Chrome, Edge | Not looked for |
| 4 | A session row does not say whether it is open when focus arrives on it. Its button says so, and so does toggling it | All three | None tried. The open state is on the button by design |
| 5 | In browse mode, the table key going up from a session's newest run lands on the heading row, past the session row, in every column but the first. In Chrome: `row 4  clickable  45.0 cm/360`, then `row 1  clickable  Sensitivity` | All three | None known. A session row is one cell, in the first column |
| 6 | Noise in browse mode. Every cell says "clickable". The list's name is said twice on a jump to it. Firefox reads a session row as five lines | As named | Not looked for |

Row 3 may have the same cause as row 2, a row index that two rows share. That
is an inference.

## Not captured

- **Why Firefox spoke no toast at one landing of the first walk.** It spoke
  the toast at the second landing there, and at both in the second walk.
  Chrome and Edge spoke it at every landing of both walks.
- **Where Chrome's and Edge's row numbers change** from one more than the row
  index to equal to it.
- **A voice.** NVDA ran muted.
- **Narrator, JAWS, and a person listening.** No screen-reader user has tried
  the list.

## What went wrong on the way

All of it was the harness's, in the first walk, and none of it changes a
result above. Nothing went wrong in the second.

- **A screen saver stopped the first attempt,** before NVDA started. A screen
  saver has a desktop of its own, so the test window could not take the
  keyboard. The script now checks the desktop before it opens a browser.
- **The browse-mode walk presses NVDA's table keys from outside a cell,** and
  NVDA answers `Not in a table cell`. The seventh walk presses the same keys
  from inside the first cell, and its lines are the ones quoted.

## Where the raw output is

Not in the repository. The walk's scripts, each browser's console output for
both walks, a file of every step per walk, and NVDA's own logs are scratch
files on the maintainer's machine, under
`ignore/scripts/run-history-page-pr2/nvda/`. Pull request #371's description
says how to run the walk again.

## 2026-10-14: The walk again, with the All scenarios tree

Date: 2026-10-14
Author: claude-opus-5-5 · effort: xhigh
Source revision: `8ba57a2` on pull request #378's branch

The run list gained a second view, All scenarios: each session whole, a
scenario row for each visit to a scenario, and its runs under it. Its
proposal ([PR #375](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/375))
changes what a screen reader is told about a row, which key does what, and
where focus goes, so R4's rule required the walk again before the change
merges. The proposal names eight tasks for the tree. The walk takes them, and
R4's five again, because a session row under This scenario gains a button.
As before, it is a measurement and not a decision, and a task that fails goes
to the maintainer.

### Summary of the second walk

- **All thirteen tasks can be done in Firefox, Chrome, and Edge:** the
  tree's eight, and R4's five again. None failed.
- **The three pieces never tried under a screen reader all work, in all
  three browsers.** A scenario row opened or closed from the keyboard says
  `Expanded` or `Collapsed`. A press on a scenario's name says
  `Selected scenario: Whisphere Viscose` and leaves focus on the button, now
  `current`. A session's count, followed from This scenario, puts focus on
  that session's row in the tree, and NVDA reads the row.
- **Two things only NVDA could decide went as rehearsed.** Right and Left on
  the view switch reach the page, because NVDA turns focus mode on when
  Shift+Tab lands on the switch. Escape closes the Columns menu.
- **R4's five tasks say what they said on 2026-10-13,** apart from the count
  this pull request made a button, and a run's toast, which an earlier change
  made plain.
- **The tree adds seven things that do not work well.** None stops a task.
  They are under
  [What still does not work in the tree](#what-still-does-not-work-in-the-tree),
  each with whether a fix is known.
- **Not covered,** as before: Narrator, JAWS, and a person listening.

### How the second walk was run

| | |
|---|---|
| Screen reader | NVDA 2026.2, the same unpacked copy, muted, started and stopped by the script |
| Browsers | Firefox 157.0, Chrome 155.0.8059.79, Edge 155.0.4283.45, visible and maximized, at 1.5x scaling |
| App | The pull request's build at `8ba57a2`, on a scratch copy of five scenarios' stats files, 1,051 runs. The page showed VT DotTS Intermediate S5 |
| Keys | Real key presses to the foreground window: 418 in Firefox and 419 in each of Chrome and Edge, over fourteen walks, then 35 in a fifteenth |
| Runs landed | Five in each browser, each a stats file written to the scratch stats folder: two before the walks, two in R4's landing walk, and one of another scenario in the tree's |
| Checks | The script checked where focus was, what the live region was given, and which view the list held, against a rehearsal without NVDA. All 284 checks held in each browser, and every key went where the rehearsal said it would |

The walks are one per task, a pass of NVDA's browse mode by line, and a pass
of its table keys. Each starts from a fresh load of the page with what the
browser remembers for the app forgotten, so on This scenario. A walk on the
tree turns the switch from the keyboard. Each browser took about nine and a
half minutes. Nothing went wrong on the way.

### The tree's eight tasks

#### 1. Switching the list to All scenarios and back, and hearing which view it is in

**It works.** The switch is a group of two radio buttons. The view is heard
on the switch, and in the list's name when focus enters the list. Nothing
else is said when the list changes. All three browsers said the same:

| Key | NVDA |
|---|---|
| Shift+Tab from Expand all | `Run list view  grouping`, then `This scenario  radio button  checked  1 of 2`, then `Focus mode` |
| Right | `All scenarios  radio button  checked  2 of 2` |
| Tab into the list, past Expand all and Columns | `Runs of all scenarios, by session  table`, then `#  column header  row 1  column 1` |
| Left, back on the switch | `This scenario  radio button  checked  1 of 2` |
| Tab into the list again | `Runs of VT DotTS Intermediate S5, by session  table` |

#### 2. Telling a session row, a scenario row, and a run row apart, and hearing whether a scenario row is open

**It works, with one more key than it should need.** Each kind of row begins
differently. A scenario row does not say whether it is open until focus is on
its button, or until it is toggled, as a session row does not.

| Key | Chrome and Edge | Firefox |
|---|---|---|
| Down from the headings, to the current session | `Session Oct 14, 6:42 AM In progress 1 min · 2 runs · 1 scenario Hide all runs  row` | The same, then `not selected  row 2  2 of 34` |
| Down, to its scenario row | `Scenario 1. Show VT DotTS Intermediate S5 2 runs  row` | `Scenario 1. Show VT DotTS Intermediate S5 VT DotTS Intermediate S5 2 runs  row  not selected  row 2  2 of 34` |
| Down, to a run | `2  row 4  #  column 1` | `2  row 3  #  column 1` |
| Tab from the scenario row, to its button | `Scenario  button  expanded` | The same |

An open session row in the tree is read with its **Show all runs** or **Hide
all runs** button, and a closed one with neither:
`Session Oct 9, 4:49 PM 1 min · 1 run · 1 scenario  row`.

**Opening and closing a scenario row is announced** as a session row's is.
In all three browsers:

| Key on the row | NVDA |
|---|---|
| Left | `Collapsed` |
| Right | `Expanded` |
| Enter | `Collapsed` |
| Space | `Expanded` |
| Right on a row already open | nothing |

From the row's button, Enter said `collapsed` and Space said `expanded`, the
button's own state. A closed scenario row's button says
`Scenario  button  collapsed`.

#### 3. Hearing which scenario and which session a run belongs to

**It works, by moving up.** A run's cells say their values and headings and
nothing else, such as `16,360  row 7  Score  column 3` in Chrome. Up from the
run reaches its scenario row, then the session's other scenario rows, then the
session row:

| Key, from run 8 of Whisphere Viscose in the session Oct 8, 2:07 PM | Chrome and Edge |
|---|---|
| Up | `Scenario 1. Show Whisphere Viscose 8 runs  row` |
| Up | `Scenario 2. Show VT Controlsphere Viscose 8 runs  row` |
| Up | `Session Oct 8, 2:07 PM 39 min · 16 runs · 2 scenarios Show all runs  row` |

Firefox said the same, with each scenario's name twice and each row's
position. In browse mode, NVDA's table key going up from the run's
Sensitivity cell said `Edge of table` four times and did not move, in all
three browsers.

#### 4. Selecting a scenario from its row, and hearing that it was selected

**It works.** Tab from a scenario row reaches its toggle, then its name.
Enter on the name selects the scenario for the page, says so through the live
region, and leaves focus on the button, now the current one. NVDA said
nothing when the tree was drawn again. All three browsers said the same:

| Key | NVDA |
|---|---|
| Tab, Tab from the row of the selected scenario | `Scenario  button  expanded`, then `Show VT DotTS Intermediate S5  button  current` |
| Tab, Tab from a row of Whisphere Viscose, in an older session | `Scenario  button  collapsed`, then `Show Whisphere Viscose  button` |
| Enter | `Selected scenario: Whisphere Viscose`, then `current` |
| Insert+Tab, NVDA's report of focus, after the tree was drawn again | `Show Whisphere Viscose  button  focused  current` |
| Back up to the row of VT DotTS Intermediate S5, Tab, Tab | `Scenario  button  expanded`, then `Show VT DotTS Intermediate S5  button` |

#### 5. Following a session's count, and arriving on that session in the tree

**It works.** Under This scenario, Tab from a session row reaches its toggle,
then its count. Enter switches the list to All scenarios, and focus lands on
that session's row, which NVDA reads at once, in focus mode. The live region
says nothing, and nothing names the view.

| Key | Chrome and Edge | Firefox |
|---|---|---|
| Tab, Tab from the session row Feb 13, 10:50 PM | `Session  button  collapsed`, then `9 of 9 runs  button  Show the whole session` | The same |
| Enter | `Session Feb 13, 10:50 PM 20 min · 9 runs · 1 scenario Hide all runs  row  row 49`, then `Focus mode` | The same, with `not selected  row 49  49 of 60` |
| Down | `Scenario 1. Show VT DotTS Intermediate S5 9 runs New PB  row  row 50` | The same, with the name twice |
| Down | `9  row 51  #  column 1` | The same |

#### 6. Opening one session's runs with Show all runs, and hearing that they opened

**It works.** On an open session row in the tree, Tab reaches its toggle,
then **Show all runs**. Enter opens every scenario row of the session, and
focus stays on the button. It says what **Expand all** says:

| Key | Chrome and Edge | Firefox |
|---|---|---|
| Tab, Tab from the session row Oct 8, 2:07 PM | `Session  button  expanded`, then `Show all runs  button` | The same |
| Enter | `Expanded` | `Expanded`, then `Hide all runs` |
| Enter on Hide all runs, later | `Collapsed` | `Collapsed`, then `Show all runs` |

#### 7. Staying on the same run when a new run lands and adds a scenario row above it

**It works.** With Follow off and focus in a run's Score cell in the current
session, a run of another scenario was landed. In each browser, keyboard focus
stayed in the same row, by its id, and in the same column. The new scenario
row and its run came in above it, so the row moved two places down: Chrome
said `1,180  cell  focused  row 6` for the cell that had been row 4.

- **Up from the run** reached its own scenario row, then the new run, then the
  new scenario row, `Scenario 2. Show VT Raw Control Intermediate S5 1 run  row`,
  then the session row, now `9 min · 5 runs · 2 scenarios`.
- **At the landing,** Firefox and Chrome read the app's run toast:
  `alert  New run detected`, the scenario's name, and
  `Open in Run History  link`. Edge read nothing.

#### 8. Hearing a row's two figures with Median and best on

**It works.** Enter on Columns opens its menu, Tab reaches **Median and
best**, Space checks it, and Escape closes the menu and puts focus back on
Columns. A row's figures are read with the row, after its counts. All three
browsers said the same words:

| Row | NVDA, in Chrome and Edge |
|---|---|
| A session under This scenario | `Session Feb 13, 10:50 PM 9 of 9 runs Median 1,178 · Best 1,220  row` |
| A scenario row of eight runs | `Scenario 2. Show VT Controlsphere Viscose 8 runs Median 3,036 · Best 3,126  row` |
| A scenario row of one run | `Scenario 1. Show Whisphere Viscose 1 run Score 17,340  row` |

In the menu, Enter said `Columns  dialog`, the first checkbox, and
`Columns  dialog` again. Space on Median and best said `checked`. Escape said
`button  Columns`, then `Columns  button`.

### R4's five tasks again

**All five can still be done, and NVDA said what it said on 2026-10-13, in
all three browsers.** Each step's speech was compared with the first
record's, with the current session's time and counts set aside. Three things
differ, and none is a failure:

- **Tab from a session row's toggle reaches its count first,**
  `9 of 9 runs  button  Show the whole session`, and a second Tab the first
  cell of the newest run. In browse mode a session row reads its count as a
  button: `Feb 13, 10:50 PM   button  9 of 9 runs`.
- **The toast at a landing is the plain run toast,**
  `alert  New run detected`, the scenario's name, and
  `Open in Run History  link`, where the first record heard
  `Threshold passed`. That change is the
  [plain run toast](../decision_log/2026/2026-10-13-a-run-toast-is-plain-and-shows-on-every-page.md),
  already on this pull request's base. Focus stayed on the same run at both
  landings, as before.
- **Rows sit at other numbers,** because each browser's walk landed other
  runs.

### What still does not work in the tree

None of these stops one of the thirteen tasks. The six things under
[What still does not work](#what-still-does-not-work) still hold. The tree
adds these:

| | What | Where | Stops a task | Fix |
|---|---|---|---|---|
| 1 | A row's depth is never said, now over three levels. A run names neither its scenario nor its session: Up reaches the scenario row, and Up again, past the session's other scenario rows, the session row | All three | No. Task 3 is done by moving up | None known in AG Grid's free edition |
| 2 | A scenario row does not say whether it is open when focus arrives on it, as a session row does not | All three | No. Task 2 takes one more key, Tab to the row's button | None tried. The open state is on the button by design |
| 3 | A scenario row is read with its name button's name, so it says `Show` before the scenario: `Scenario 1. Show Whisphere Viscose 8 runs`. Firefox then says the name a second time | All three. The second name, Firefox | No | Not tried. The second name is most likely the hover on the part around the name, which holds the whole name. That is an inference |
| 4 | A scenario row does not say that it is the selected scenario's. Its name's button says `current` | All three | No | None tried. The mark is on the button by design |
| 5 | After a jump, nothing names the view. NVDA reads the session row focus lands on, whose words are the tree's: `9 runs · 1 scenario`, where This scenario said `9 of 9 runs` | All three | No | None tried |
| 6 | In browse mode, NVDA's table key going up from a run under a scenario row, in the Sensitivity column, says `Edge of table` and does not move | All three | No. In focus mode Up reaches the scenario row and the session row | Not looked for. It is most likely the first record's fifth item again: a group row is one cell, in the first column |
| 7 | Noise. Firefox reads a session row again after it is opened or closed in the tree, because the row gains or loses Show all runs. Asked where focus is, NVDA calls the switch's radio buttons `off screen`. The Columns menu is announced as a dialog twice when it opens. In Firefox, Down from a group row, after a Tab to its button and back, went to the Score or Time column, where Chrome and Edge went to the first | As named | No | Not looked for |

### Not captured in the second walk

- **Why Edge spoke no toast at the landing in task 7.** It spoke the toast at
  both of R4's landings, and Firefox and Chrome spoke it at all three.
- **Browse mode over the tree, by line.** The browse-mode walk runs under This
  scenario. The tree was walked in focus mode, with one pass of the table
  keys in task 3.
- **A voice, Narrator, JAWS, and a person listening,** as before.

### Where the second walk's raw output is

Not in the repository. The walk's scripts, each browser's console output, a
file of every step per walk, and NVDA's own logs are scratch files on the
maintainer's machine, under `ignore/scripts/run-history-all-scenarios/impl/nvda/`,
with a README that says how to run the walk again.
