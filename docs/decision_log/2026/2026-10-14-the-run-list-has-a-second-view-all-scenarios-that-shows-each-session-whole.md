# 2026-10-14: The Run List Has A Second View, All Scenarios, That Shows Each Session Whole

Status: Accepted

The run list on Run History has a second view, All scenarios, which lists
each session whole: the scenarios played in it, in the order they were
played, with each one's runs under it. A switch above the list chooses the
view, the list starts on This scenario, and the browser remembers the switch.
A click on a scenario's name in the new view selects that scenario for the
whole page, by the rule Follow and a scenario link already follow. What a
player notices is that the order of a session is on screen, where before it
was a count on a row.

**Rulings.** By the maintainer, 2026-10-14, on
[PR #375](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/375):
"I ratify the proposal." Row A1, the scenario name's click, was ratified as
recommended. Before it, the maintainer, 2026-10-10: "Agree, tree click should
take the same rule as Follow." The view itself was not a row: its shape was
leaned to on 2026-10-07 from a full-size mockup, the outline the maintainer
agreed on 2026-10-10 ("Merged breakdown is a go.") listed the rows and not
the view, and the ratification covers it as author-owned. Four readings of
the view were agreed in chat on 2026-10-13, "1-4: agree with all four", and
are marked below. Built in
[#378](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/378).
What the list does today is in
[run_history.md](../../specs/run_history.md#the-run-list). The count's link
and **Show all runs** are
[the A2 entry](2026-10-14-a-sessions-count-jumps-to-it-in-the-tree-and-an-open-session-row-has-show-all-runs.md),
and **Median and best** is
[the A3 entry](2026-10-14-the-run-lists-columns-menu-offers-median-and-best-off-to-start.md).

**A1 is folded in here.** Its entry would have repeated
[R7's](2026-10-12-follow-and-a-scenario-link-clear-a-playlist-filter-that-does-not-list-the-scenario.md)
with one more way in, and R7's entry already said "so will a click in the
All scenarios view". R7's entry carries a dated note instead.

**Why a second view.** The list showed one scenario's runs by session. What
else was played in a session was a count, `7 of 47 runs`, and a divider,
`10 runs on 3 other scenarios`, that named nothing. The order of play was
nowhere on screen, and the product record left "how is this session going?"
answered for the scenario on screen and not across scenarios. On the
maintainer's history a session's median is 22 runs on 5 scenarios, one in ten
holds 20 scenarios or more, and 72 of 325 are one scenario from start to end.
The record also left open whether the live and the finished session are one
view or two: the tree shows both the same way.

**The switch.**

- A segmented control, This scenario and All scenarios, on the list's second
  line at the left, with **Expand all** and **Columns** at the right. Its
  accessible name is `Run list view`. The heading keeps the line of its own
  the build gave it.
- The list starts on This scenario, and the browser remembers the switch
  (reading 4). The page's subject is one scenario, and a browser that has
  never seen the switch shows the list every user had.
- Its id and default are chosen once: `run-history-list-view`, the values
  `scenario` and `all`, `scenario` the default. A renamed id or a changed
  default resets the stored view in every browser.
- Pressing it shows the other view from its top. Keyboard focus stays on the
  switch.
- With runs and no scenario selected, This scenario reads `No scenario
  selected` with the switch still above it, where the text used to take the
  whole header's place. The tree needs no selection, and without the switch
  it could not be reached.

**What the tree lists.**

- Every session, newest first; the Playlist filter does not narrow it. The
  newest session is the first row and stays in view under the column
  headers, as built.
- A session row reads its name, the `In progress` badge on the first row
  while its session is in progress, then `{length} · {n} runs · {k}
  scenarios`. Every session row gives its length here; in the tree a session
  is the subject. Only the first row's length keeps its hover. `{k}` counts
  scenarios, not rows.
- Under a session, a row per visit (reading 1): a scenario that is left and
  returned to gets a second row. One row per scenario would put two blocks
  of runs an hour apart under one number, and the order of play is what the
  view adds. The word visit stays off the screen.
- Scenario rows are numbered in play order and listed newest first, as runs
  are. A row reads `{number}. {scenario}`, its run count, and a star where a
  new PB was set in it. The name is a button drawn as a link and is cut short
  with an ellipsis before the count is; the hover on the part around it
  gives the whole name.
- Run rows keep the built list's seven columns and marks. `#` is the run's
  number among its scenario's runs in the session and carries on into a
  second visit, so one run has one number in both views and on the
  latest-run card. Every listed scenario's runs are marked, one scenario at
  a time over its whole history, by the function that marks the selected
  scenario; a run's check and star are the same in both views.
- No dividers: the rows between two visits say the scenario was left. Date
  headers are the built list's rule asked of one scenario row at a time.
  A header between scenario rows was set aside, because a visit can span
  midnight.

**What the tree marks.** A band down the left edge of every row of the
selected scenario, its scenario rows and the runs under them; nothing with no
selection. The name's button carries `aria-current` on those rows. The last
run's row keeps its highlight. The tree never goes looking for the selected
scenario: it does not scroll to it or load older sessions to reach it.

**A1: a click on a scenario's name.** It selects that scenario for the whole
page, the dropdown, the chart, Scenario Stats, and the band, and a Playlist
filter that does not list it is cleared in the same step (R7). The view stays
on All scenarios (reading 3), the row does not open or close, and the list
does not scroll. A press on the selected scenario's own name changes nothing.
From the keyboard, focus stays on the name's button and the live region says
`Selected scenario: {scenario}`, because the chart is not near focus.

- **The cost is R7's.** Clearing the filter takes away the rank lines and
  **Open scenario table**, and the cleared filter is what the browser then
  remembers. The tree makes that easier to do without meaning to than Follow
  does.
- **The tree's rows are drawn by a script, so the click can't be a Dash
  input.** The script writes the scenario's name to a store that is always in
  the layout, and the one callback that writes either dropdown takes that
  store as its fourth input, with plain outputs, so the scenario list and the
  chart still wait for it.
- **Which of the four asked is read from what triggered the call.** The store
  replays its last name into every later call, as the run summary replays
  its last batch. Read from the values, a run landing after a click would
  select the clicked scenario again. Two tests hold both directions.

**Opening and closing.**

- A session row and a scenario row each open and close on a click, with no
  request to the server, and take the same four keys.
- On arrival the first session is open, and so is the scenario row of the
  last run played. **Expand all** opens every loaded session down to its
  scenario rows and opens no runs; **Collapse all** leaves the scenario rows'
  own state alone (reading 2).
- Each view keeps its own open rows, and neither set is remembered across a
  reload.
- **Each view keeps a mark, the newest run whose rows it has opened.** The
  shell hands the page runs in batches, and a batch can hold runs on two
  scenarios; runs also land while the other view is on screen. When a view's
  rows arrive, the script opens the rows of every run newer than that
  view's mark, then moves the mark. In the tree those are each run's session
  row and scenario row, found by walking the run rows from the top down to
  the mark; under This scenario it is the first row, as built. One mark for
  both views would leave the tree's rows shut for runs that landed while
  This scenario was on screen. This was the Codex seat's must-fix F1 on
  PR #375.
- **The first time a view's rows arrive in a visit, it also opens the rows of
  the run at its mark.** Both marks start at the run the visit's first model
  names, and every model names the store's newest run, even one with nothing
  to list. A model with nothing to list is not that first time: with no
  scenario selected, This scenario's first row still arrives open once a
  scenario is chosen.
- A row the player closed stays closed until a newer run lands in it.

**Sessions loaded.** Each view loads 30 and counts its own: This scenario the
30 newest sessions that hold the scenario, the tree the 30 newest sessions.
**Show older sessions** adds 30 to the view it is pressed in. One count for
both would have made three presses under This scenario load 120 whole
sessions on the next press of the switch. On the maintainer's history the
tree's 30 sessions are three weeks of play.

**The grid work.** Four of the nine pieces of grid-specific work in
[the R4 entry](2026-10-12-the-run-list-is-built-on-ag-grid-community-and-nvda-is-run-on-the-built-list.md)
change: a scenario row is a second kind of full-width group row with the
`gridcell` role (item 1); the filter shows a row under a scenario row only
while its session row and its scenario row are open (item 2); a scenario row
takes the four keys (item 5); and focus goes back to the same button in the
row, not only the same row, because a press on a name rebuilds the tree and
the row's first button is its toggle (item 9). The script holds one set of
open rows and one mark per view. On a run row the band is a row class rule,
as the highlight is, because the grid never takes off a class it gave a row
by function. On a scenario row the script draws it, as part of item 1: the
grid does not work its row class rules out again when a full-width row's
data changes, so the rule's band stayed on the scenario selected before.
This was the Codex seat's must-fix F1 on PR #378.

**A row's depth is never said.** The grid's root has the role `grid`, and a
row's level belongs to a `treegrid`, which AG Grid sets only through its paid
features. Each kind of row begins differently instead: a session row reads
`Session` and a date, a scenario row `Scenario`, a number, and a name, and a
run row is read a cell at a time. A run row does not say which scenario it
is under; that is heard by moving up. NVDA was run on the built tree on
2026-10-14, in Firefox, Chrome, and Edge, and the tree's eight tasks and R4's
five can all be done. What it said is in
[run_history_list_nvda_walk.md](../../research/run_history_list_nvda_walk.md).

**Measured.** On the maintainer's history, 9,135 runs, by the app's own
functions: the tree's 30 sessions are 1,040 rows and 421 KB, built in 66 ms
the first time, when every listed scenario's performance files are read, and
in 12 ms after. This scenario's rows for the most-played scenario are 481 rows
and 161 KB, built in 6 ms. The browser figures are in the PR.

**Alternatives not taken.** One row per scenario with its runs merged, which
loses the order of play. All scenarios as the view the list starts on. A
scenario's name drawn as plain text on the selected scenario's rows, the
card's rule, which would drop keyboard focus in the middle of the list at
every selection. A date header between scenario rows. A page of its own for
sessions.

**Left alone.** A closed scenario row moving focus to its session on Left,
the `treegrid` role set by hand, a scenario row that closes when the next
starts, and **Show all runs** on a closed session row were offered as
optional and not taken. Opened rows still pile up over a long session, and
which rows are open is still never remembered.

Proposed in
[PR #375](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/375),
which merged as `ded93f2`. Shipped in
[#378](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/378). The
proposal file, `docs/proposals/all_scenarios_proposal.md`, is deleted, and git
history keeps it.
