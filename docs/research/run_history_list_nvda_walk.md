# The Run History page's run list under NVDA

Date: 2026-10-13
Author: claude-opus-5-5 · effort: xhigh
Source revision: `b0d9908`, the head of pull request #371 when the walk ran

This is the record of what the NVDA screen reader said on the run list of the
Run History page, as built. The page's proposal
([PR #356](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/356))
makes this record a condition of the page going public, and names the five
tasks walked here. It is a measurement, not a decision. The proposal requires
the walk and not a repair: a task that fails goes to the maintainer.

**Run the walk again before the page goes public if the list has changed** in
what a screen reader is told about a row, in which key does what, or in where
focus goes. A change to how the list looks does not need it.

## Summary

- **All five tasks can be done in Firefox, Chrome, and Edge.** None failed.
- **The two fixes that had never been tried both work, in all three.** A
  session row opened or closed from the keyboard is announced, once. A run
  that lands leaves keyboard focus on the same run.
- **Eight things still do not work well.** None stops a task. They are listed
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
| App | The pull request's build at `b0d9908`, on a scratch copy of five scenarios' stats files, 1,051 runs. The page showed VT DotTS Intermediate S5 |
| Keys | Real key presses to the foreground window: 184 in Firefox and 185 in each of Chrome and Edge, over six walks, then 37 steps of a seventh |
| Runs landed | Eight, each a stats file written to the scratch stats folder: two before the walks, and two in each browser's landing walk |
| Checks | The script checked where focus was after each key against a rehearsal without NVDA. All 88 checks held in each browser |

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
| Down from the headings | `Session Oct 13, 2:22 AM In progress 1 min · 2 of 2 runs  row  not selected  row 2  2 of 33` | `Session Oct 13, 2:22 AM In progress 3 min · 4 of 4 runs  row` |
| Down to an older session | `Session Feb 13, 10:50 PM 9 of 9 runs  row  not selected  row 2  2 of 31` | `Session Feb 13, 10:50 PM 9 of 9 runs  row` |
| Tab, to the row's button | `Session  button  collapsed` | the same |

Edge said what Chrome said. The current session's length and counts differ
between the browsers because each walk landed runs.

**Opening and closing from the row is announced.** This fix had not been
tried. The row writes one word to a live region, and NVDA spoke it once each
time, in all three browsers:

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

**It works.** With every session open, PageDown reached the last row in 12
presses in Firefox and 13 in Chrome and Edge, about 475 rows down. The grid
draws only the rows near the window, and NVDA read each row focus arrived on.

| Key | Firefox | Chrome |
|---|---|---|
| PageDown, the last press | `Show older sessions  row  not selected  row 475  475 of 475` | `Show older sessions  row  row 477` |
| Enter on it | `Session Aug 31, 2025, 6:21 PM 9 of 9 runs  row  not selected  row 475  475 of 478` | `Session Aug 31, 2025, 6:21 PM 9 of 9 runs  row  row 477` |

After Enter, focus was on the first of the sessions it loaded, and NVDA read
it. Edge said what Chrome said, two rows later.

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

**It works.** This fix had not been tried either. With focus in a run's Score
cell, two runs were landed one after the other. In each browser, after each
landing, keyboard focus was in the same row, by its id, and in the same
column. The row had moved one place down each time.

- **NVDA did not read the cell again.** Asked where focus was, it read the
  same value one row later: `1,180  cell  focused  row 4`, then
  `1,180  cell  focused  row 5`, in Firefox.
- **What NVDA said at a landing was the app's own toast:**
  `alert  Threshold passed`, then
  `VT DotTS Intermediate S5: 1180.00, 96.7% of PB.`, then `button`.
- **Firefox said nothing at its first landing,** and spoke the toast at the
  second. Chrome and Edge spoke it at both. Why was not captured.

## What still does not work

None of these stops one of the five tasks. The first two were on this list
before the walk ran: the proposal names both as having no known fix.

| | What | Where | Fix |
|---|---|---|---|
| 1 | A row's depth is never said. A session row and a run row are told apart only by their words | All three | None known in AG Grid's free edition |
| 2 | The current session's row and the first row under it are both "row 2". NVDA counts 40 rows where Chrome and Edge count 41, and each later row is one lower than there | Firefox | None known. It is AG Grid's markup for a pinned row |
| 3 | A spoken row number is one more than the row's `aria-rowindex` near the top (`row 3` on index 2, `row 10` on index 9) and equal to it further down (`row 33` on index 33). Where it changes was not measured | Chrome, Edge | Not looked for |
| 4 | A session row does not say whether it is open when focus arrives on it. Its button says so, and so does toggling it | All three | None tried. The open state is on the button by design |
| 5 | In browse mode, read by line, a session row's parts run together: `Oct 13, 2:22 AMIn progress`, `Feb 13, 10:50 PM9 of 9 runs` | Chrome, Edge | Inferred, not tried: a space the browser keeps between the parts |
| 6 | In browse mode, the table key going up from a session's newest run lands on the heading row, past the session row, in every column but the first. In Chrome: `row 4  clickable  45.0 cm/360`, then `row 1  clickable  Sensitivity` | All three | None known. A session row is one cell, in the first column |
| 7 | Pressing Expand all says nothing. Firefox reads the button's new name, `Collapse all` | Chrome, Edge | Inferred, not tried: say it through the live region |
| 8 | Noise in browse mode. Every cell says "clickable". The list's name is said twice on a jump to it. Firefox reads a session row as five lines | As named | Not looked for |

Row 3 may have the same cause as row 2, a row index that two rows share. That
is an inference.

## Not captured

- **Why Firefox's first landing had no toast spoken.** NVDA's log for that run
  holds two alerts: one while the first two runs were landed, before the
  walks, and one after the second landing. Whether the toast was on screen at
  the first was not recorded.
- **Where Chrome's and Edge's row numbers change** from one more than the row
  index to equal to it.
- **A voice.** NVDA ran muted.
- **Narrator, JAWS, and a person listening.** No screen-reader user has tried
  the list.

## What went wrong on the way

Both were the harness's, and neither changes a result above.

- **A screen saver stopped the first attempt,** before NVDA started. A screen
  saver has a desktop of its own, so the test window could not take the
  keyboard. The script now checks the desktop before it opens a browser.
- **The first browse-mode walk pressed NVDA's table keys from outside a
  cell,** and NVDA answered `Not in a table cell`. The seventh walk presses
  the same keys from inside the first cell, and its lines are the ones quoted.

## Where the raw output is

Not in the repository. The walk's scripts, each browser's console output, a
file of every step per walk, and NVDA's own logs are scratch files on the
maintainer's machine, under `ignore/scripts/run-history-page-pr2/nvda/`.
Pull request #371's description says how to run the walk again.
