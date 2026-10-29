# 2026-10-12: The Run List Is A Second Column Beside The Chart

Status: Superseded in part, 2026-10-14, by the
[All scenarios entry](2026-10-14-the-run-list-has-a-second-view-all-scenarios-that-shows-each-session-whole.md),
[the count's link](2026-10-14-a-sessions-count-jumps-to-it-in-the-tree-and-an-open-session-row-has-show-all-runs.md), and
[Median and best](2026-10-14-the-run-lists-columns-menu-offers-median-and-best-off-to-start.md):
"Version 1 has one view" no longer holds, and the list's two levels become
three in the second view. A session row's count under This scenario is a link
and no longer plain text. "The first row alone gives a session's length"
holds under This scenario only. The Columns menu gained a third checkbox.
Superseded in part again, 2026-10-22, by
[the width rule](2026-10-22-the-run-list-grows-to-fit-the-columns-it-shows.md)
and [the three new columns](2026-10-22-the-run-lists-columns-menu-offers-reloads-fov-and-avg-fps-off-to-start.md):
the list is 500px at least and as wide as its shown columns need, a run row
has seven columns by default and up to ten, and the Columns menu has six
checkboxes. R3, the list as a second column beside the chart, and every
other rule of the list under This scenario stand.
Superseded in part again, 2026-10-23, by
[the inline session summaries entry](2026-10-23-this-scenario-session-rows-keep-their-score-summaries-inline.md):
This scenario no longer shows the newest session's length. All scenarios
continues to show every session's length.
Superseded in part again, 2026-10-29, by
[Shots Fired starts hidden](2026-10-29-the-run-lists-shots-fired-column-starts-hidden.md):
Shots Fired starts hidden, so a run row has six columns by default.

Run History lists the selected scenario's runs in a column of its own, to the
right of the chart and always shown. The chart is narrower than the old
page's, and narrower again while the Chart options panel is open beside it.
The list and the panel are not stacked in one column because the panel is
opened now and then to tune something, while the list is what the page is
for. In a narrow window the list drops under the top row, above the chart.

**Superseded in part (2026-10-15).** [T1 of the top-row cards](2026-10-14-run-historys-top-row-has-one-card-per-kind-of-information.md)
replaces the top row's order and the latest-run card filling its remaining
width: the dropdowns are stacked, Scenario Stats and PB occupy the first
column, and the latest-run card sits over the run list in their shared
500px column. The amended Follow switch sits under the scenario dropdown.
The list's width, its relation to the chart, and the rest of this entry stand.

**Superseded in part (2026-10-18).** [The heading line's entry](2026-10-18-the-run-lists-heading-line-is-for-screen-readers-only.md)
takes the list's heading off the screen, in both views, and keeps it for
screen readers. So it no longer sits on a line of its own above the buttons:
the switch and the buttons are the header's first line. The heading's words
and every other rule of the list stand.

**Superseded in part (2026-10-22).** [The width rule](2026-10-22-the-run-list-grows-to-fit-the-columns-it-shows.md)
and [the three new columns](2026-10-22-the-run-lists-columns-menu-offers-reloads-fov-and-avg-fps-off-to-start.md)
replace R3's "500 px wide", the 2026-10-15 note's "their shared 500px
column", "A run row has seven columns", and "The Columns menu shows or hides
Shots Fired and Sensitivity". The list is 500px at least and as wide as its
shown columns need, up to a 480px floor for the chart. A run row has seven
columns by default and up to ten, and the menu also shows or hides Reloads,
FOV and Avg FPS, each off to start. The list's place beside the chart, its
narrow-window rules, and every rule of what it shows stand.

**Rulings.** By the maintainer, 2026-10-12, on
[PR #356](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/356):
"I ratify the proposal." This entry is row R3, ratified as recommended.
Before it, the row stood on the maintainer's lean in the design discussion of
2026-10-06 and 2026-10-07, from a full-size mockup. The ratification also
covered the author-owned rules below: the narrow-window rules and what the
list shows. The layout was built in
[#370](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/370) and
the list in
[#371](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/371).
The rules as the app applies them are in
[run_history.md](../../specs/run_history.md). This entry holds the reasons,
the measured boxes, and the layouts set aside. How the list is built is in
[its own entry](2026-10-12-the-run-list-is-built-on-ag-grid-community-and-nvda-is-run-on-the-built-list.md).

**The page at a glance.**

```
┌─ top row ─────────────────────────────────────────────────────────────────┐
│ Playlist filter      Selected scenario      Last played:   ┌ latest-run ─┐│
│ Open scenario table  [x] Follow newly...    Number of runs:│ card        ││
│                                             Position:      └─────────────┘│
├───────────────────────────────────────────┬───────────────────────────────┤
│ [Score vs Run|Time|Sensitivity] [Range ▾] │ {scenario} · 33 runs          │
│ [Chart options]                           │        [Expand all] [Columns] │
│                                           │ #  Time  Score   Accuracy ... │
│                                           │ ▼ Oct 4, 9:45 PM  In progress │
│        chart: every run in the range      │        1 hr 6 min · 7 of 47   │
│        PB score and Score threshold lines │ 7 10:50 PM 3,324 ✓   55% ...  │
│        rank lines, New PB stars           │ 6 10:49 PM 3,422 ✓★  57% ...  │
│                                           │   10 runs on 3 other scenarios│
│                                           │ 5 10:47 PM 3,417 ✓★  57% ...  │
│                                           │ ▶ Oct 2, 11:18 PM   6 of 26   │
│                                           │ ▶ Oct 1, 8:04 PM    6 of 12   │
│                                           │ [Show older sessions]         │
└───────────────────────────────────────────┴───────────────────────────────┘
```

The page's subject is one scenario, and with Follow on it follows the
scenario being played. Follow is the **Follow newly played scenario** switch.
The session is context around the scenario. The page fills the window's
height as the old one did: the chart and the list take the room under the top
row, and the list scrolls inside its own box.

The top row keeps the old page's blocks, in this order: the Playlist filter
with its Open scenario table link, the Selected scenario select with the
Follow switch under it, and the Scenario Stats block with Last played, Number
of runs, and Position. The latest-run card follows and fills the rest of the
row. The chart mode and the Chart options button moved into the chart's
header.

**R3, a second column.** The latest-run card sits in the top row, the chart
is below it on the left, and the run list is below it on the right, 500 px
wide and always shown. Chart options stays a panel that opens beside the
chart, between the chart and the list.

The
[2026-08-09 naming entry](2026-08-09-the-graph-page-is-scenario-performance-its-panel-is-chart-options.md)
expected the opposite and left the question to this work: "Run History
composes into this column rather than adding a second one. If a run history
tied to Scenario Performance arrives, how the two share the space is the
run-history proposal's question." The answer is that they don't share a
column.

- **The two have opposite lifetimes.** Chart options starts closed on every
  visit and is opened to tune something. The run list is what the page is
  for. In one column, opening the options would cover the list or push it
  down.
- **They need different widths.** The list's seven columns need about
  480 px, added up from the column widths of the technical trial. The
  options panel is 20rem, 320 px.
- **The list is on the right because the newest runs are.** The newest
  points sit at the chart's right edge, beside the newest rows.
- **The same entry allowed for it.** Its fourth ruling says the panel's
  column "claims no exclusive tenancy of the page's right side. It is a
  page-local column a later design may share, stack with, or re-host."

**What it costs is chart width.** In the mockup at 1600 by 900 the chart was
about 830 by 600 and the list about 500 by 600, and with Chart options open
the chart was about 500 px wide. The maintainer accepts the narrower chart
until the panel is reworked after shipping. The proposal had only the mockup
and arithmetic. PR #370 measured the real app on 2026-10-12, in headless
Edge 155 and Firefox 157.0.1, with the window 900 px tall. The graph box is
the graph's own element, and the plot area is what plotly's margins leave
inside it.

| Window | Chart options | Page area | Graph box | Plot area | Panel |
|---|---|---|---|---|---|
| 1400 | closed | 1,143 | 627 by 542 | 467 wide | |
| 1400 | open | 1,143 | 627 by 320 | 467 wide | stacked above, 627 by 415 |
| 1600 | closed | 1,343 | 827 by 590 | 667 wide | |
| 1600 | open | 1,343 | 491 by 590 | 331 wide | beside, 320 wide |
| 1920 | closed | 1,663 | 1,147 by 590 | 987 wide | |
| 1920 | open | 1,663 | 811 by 590 | 651 wide | beside, 320 wide |

- **These are Edge's boxes.** Firefox read the same widths and one pixel less
  of height.
- **Against the proposal's arithmetic:** it expected about 830 px at 1600
  closed, about 500 open, and 631 at 1400. Measured: 827, 491, and 627. The
  4 px at 1400 is the gap, which is 16 px in the app and 12 in the mockup.
- **The list's column was 500 px in every row,** with no sideways overflow.
- **At 1400 with the panel open the page scrolls,** by 194 px. The stacked
  panel is 415 px tall and the graph stops at its 20rem floor. PR #370
  measured with scrollbars hidden. With a 15 px scrollbar on the page the
  chart there is 612 px wide.
- **No box moved when the list and the card filled their places.** PR #371
  and PR #372 each measured all six again and read the same numbers.
- **The top row is one line at all three widths.** Each dropdown is 211 px
  wide at 1400, 291 at 1600, and 400 at 1920. The card is 385, 425, and
  527 px wide, and 132 px tall in every state.

**Layouts set aside.**

- **One shared column,** as PR #351 proposed, with Chart options stacked
  above the list. It would have to be the list's width, so the chart would be
  no wider than it is, and the list and the options would take turns in it.
- **The list below the chart.** Even a panel of five rows there would leave
  the chart about 2.95 to 1, by PR #351's arithmetic from the boxes the
  [2026-08-09 panel entry](2026-08-09-chart-options-live-in-a-collapsible-panel-beside-the-graph.md)
  measured. That is flatter than the 2.76 to 1 that entry rejected as "wide
  and shallow".
- **A page of its own.** In session the player would choose between the list
  and the chart.

**Chart options is kept as it was,** as a panel beside the chart, with its
controls, their defaults, and its closed-on-arrival rule. Whether it is open
is still not remembered. Reworking it, such as into a strip under the chart's
header, is left until after shipping.

**Narrow windows.** Two rules. Both measure the page's own boxes and never
the window, because the navbar takes 225 px without changing the window's
width
([2026-08-03](2026-08-03-homes-controls-row-measures-the-content-area-not-the-window.md)).
The build moved neither threshold.

- **The list drops under the top row when the page area is 900 px or
  narrower.** The order is then the top row, the card, the list at up to
  600 px tall, and the chart. The page scrolls.
- **Chart options sits beside the chart only while the chart's own area is
  wider than 48em,** 768 px. At that width or less it stacks above the
  chart. The old page's threshold was 62em on the chart row. The chart's
  area is now the window less the navbar and the list, so 62em would have
  stacked the panel in every window narrower than about 1,760 px. At 48em a
  1600 px window opens the panel beside a chart 491 px wide, and a 1400 px
  window stacks it. Beside the chart at 1400 it would have left about
  300 px.

The first rule as measured by PR #371, with the list in its column:

| Window | Page area | Layout |
|---|---|---|
| 1400 by 900 | 1,143 px | The chart at 627 px beside the list at 500 px. The page does not scroll |
| 1100 by 900 | 843 px, and 828 in Edge beside the page's 15 px scrollbar | Stacked: the top row, the list at 600 px tall, then the chart. The page scrolls |
| 375 by 812 | 343 px, and 328 in Edge beside the scrollbar | Stacked. The list is 568 px tall, 70% of the window, and scrolls sideways inside its own box. The page does not scroll sideways |

At the two stacked widths the card takes a line of its own, the whole width
of the page and 132 px tall, with the list 16 px under it (PR #372).

The 48em rule supersedes one clause of the 2026-08-09 panel entry, its 62em
threshold. That entry's other rules bind the new page: the panel beside the
chart, the container query, the clipping row, `.home-graph` as the resize
hook, and the toggle's guard.

**There is no phone design.** At phone width the list's seven columns need
about 480 px and scroll sideways. With Shots Fired and Sensitivity hidden
they need about 305 px and would fit. The maintainer wanted a phone layout
only if it is cheap, and agreed to one cheap stacking rule.

**Built differently from the mockup.**

- **The card's slot starts from 380 px and grows,** where the mockup's starts
  from 500 px. In the real app the Scenario Stats block is 300 px wide, and
  the mockup's was about 180. Starting from 500 px, the slot wrapped under
  the dropdowns in a 1400 px window, which would have cost the chart there
  about 144 px of height. 380 px is the mockup's own minimum for the card.
  The dropdowns grow twice as fast as the slot, so a row with room to spare
  gives it to the scenario's name first.
- **The list's heading is on a line of its own, above its two buttons.** On
  one line with them it had about 240 px and cut the scenario's name short
  before its run count.

Seen in the build and left alone: at 1400 px the chart's header takes two
lines and each dropdown is 211 px wide, which cuts a long scenario name
short. Without a KovaaK's username the Scenario Stats block is five lines
tall, 150 px, so it and not the 132 px card sets the top row's height.

**What the list shows, and how it behaves.** These rules are author-owned
design that the ratification covered, and this is the entry that holds their
reasons. Version 1 has one view, the selected scenario's runs. A view of the
session across every scenario, and the switch between the two, belong to a
later proposal, All scenarios.

- **Two levels:** sessions, newest first, and under each the scenario's runs
  in that session, newest first. Only sessions that hold a run of the
  scenario are listed.
- **A session row is named by when it started,** as `Oct 4, 9:45 PM`, with
  the year only in an earlier year. Its right side reads how many of the
  session's runs were on this scenario, such as `7 of 47 runs`, as plain
  text. The session in progress carries an `In progress` badge.
- **The current session is always the first row,** and stays in view under
  the column headings while the list scrolls. It is there even when the
  selected scenario has not been played in it. With no session in progress
  the first row is the last session, without the badge.
- **The first row alone gives a session's length,** as
  `1 hr 6 min · 7 of 47 runs`. The session being played is the one whose
  length matters at a glance. When the selected scenario has no run in it
  the row reads `1 hr 6 min · 0 of 47 runs`, on purpose: it gives the
  session's size and says none of it was on this scenario. Opened, that row
  reads `Not played in this session`. The length's hover says why the figure
  stands still between runs: `The length runs from the first run to the last
  run. It doesn't count the time since your last run.` How a length is
  rounded is in
  [the rounding entry](2026-10-13-a-measured-time-rounds-to-the-nearest-minute.md).
- **A run row has seven columns:** the run's number in its session, its time
  of day, its score, its marks, its accuracy, the shots fired, and its
  sensitivity. Runs are numbered per session, counting this scenario's runs
  only. The marks are in
  [their own entry](2026-10-12-a-past-runs-check-is-judged-against-the-pb-it-was-chasing-under-its-own-version.md).
- **A run's time has no date and no seconds,** as `10:50 PM`. The session's
  name carries the date, and the chart's hover stays the one place that
  keeps seconds. Accuracy is shown to the whole percent, where the chart's
  hover keeps two decimals. *(Superseded 2026-10-18: the list shows accuracy
  to two decimals. See
  [A Run's Accuracy Shows Two Decimals](2026-10-18-a-runs-accuracy-shows-two-decimals.md).)*
  A score is formatted as the playlist scenario
  table formats PB Score
  ([2026-09-27](2026-09-27-the-scenario-table-drops-trailing-zeros-from-pb-score-and-pb-cm360.md)),
  by one function both now call.
- **A divider marks where the scenario was left and returned to,** such as
  `10 runs on 3 other scenarios`. Returns are common: 66 of 321 sessions in
  the maintainer's history held a scenario that was left and returned to, 26
  of them in 2026 (2026-10-05, on 8,937 runs over 866 scenarios).
- **A date header names the date of any listed run that is not on the date
  its session started.** A run row shows a time of day alone, and the
  session's name gives only the date it started on. A run's date is the date
  it ended on, the time its row shows. So where any of a session's runs of
  the scenario has another date than the session's start, each date among
  those runs gets a header that names it, the start date included, and each
  date's runs sit under theirs. Two cases have only one date among the
  listed runs and still get its header: a scenario played only after
  midnight in a session that started before it, and a single run that
  started before midnight and ended after it. Where every listed run is on
  the session's start date, there is no header. Where a header and a divider
  fall between the same two runs, the divider comes first, and the header
  sits directly above the runs it names.
- **Shots fired is shown on every scenario.** The run record gained the
  field. The parser already read shots and hits, to work out accuracy, and
  discarded them, where PR #351 had said it does not read shots. It reads
  the first weapon's row only, for shots and for accuracy alike, and 123 of
  the maintainer's 9,135 stats files list two weapons.
- **The Columns menu shows or hides Shots Fired and Sensitivity,** both
  shown to start. It is the menu the playlist tables use
  ([2026-10-05](2026-10-05-a-columns-menu-shows-and-hides-table-columns-and-kovaaks-ids-are-optional-ones.md)),
  so its choices are remembered in the browser. The maintainer, asked
  whether they should be: "Yes."
- **It loads 30 sessions at a time,** and **Show older sessions** adds 30. A
  change of scenario does not reset the count, and a reload starts from 30.
- **A row opens and closes on a click,** with no request to the server.
  **Expand all** opens every loaded session and reads **Collapse all** once
  they are all open, so the one button reads what a click would do.
- **Which rows are open is not remembered.** On arrival the first row is
  open and the rest are closed.
- **A run that lands shows as a new row with nothing lost.** Opened rows
  stay open, and keyboard focus stays on the same run. The first row opens
  for the run, once per run, so a row the player closed is not reopened by a
  later change of scenario. With Follow on, the list scrolls back to the
  top. As built, the newest run opens the first row whatever scenario it is
  on, so with Follow off a run on another scenario opens it too. That is one
  rule for arrival and for every landing, and the row's counts did change.
  One consequence is left as it is: with Follow on, the scroll to the top
  can leave the focused run off screen until the next arrow key.
- **Columns don't sort.** A sort would scatter each session's rows.
- **The heading reads `{scenario} · {n} runs`.** It says what the list is
  filtered to, and the list has no name of its own. It counts every run of
  the scenario in the run store, the figure Scenario Stats shows as Number
  of runs. A count of the loaded runs would grow with Show older sessions
  and read as the scenario gaining runs.
- **With no run in the store the list says `No runs yet`,** and only then
  `No scenario selected`. The chart checks the selection first. The list
  sides with the card.

**"In progress" clears without a run.** A session is in progress until 30
minutes after its last run
([2026-10-11](2026-10-11-a-session-ends-after-a-break-of-more-than-30-minutes.md)),
and nothing arrives when it ends. That entry left the timer to this page.
The page asks the app again on its existing 30-second tick, the one that
keeps Last played current, and when a run lands. A server callback writes a
store only when the answer changes, and the list and the card take that
store as an input. So the badge, and the card's "this session", change with
no run landing and no new polling. The app works the state out from its own
clock, never the browser's. This answers the connector's
[comment on PR #351](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/351#discussion_r4191712545)
that a list redrawn only by a new run could read "in progress" forever. In
PR #371's check, with the app's clock moved 31 minutes on and nothing else
touched, the badge cleared after about 17 seconds, with one list request and
no chart rebuild. A session that ends between two ticks reads `In progress`
for up to 30 seconds more. A late run can reopen a session, under the
sessions rule, and the list and the card follow because both rebuild when a
run lands.

**The timestamp format gains three short uses.** Session names and the card
drop the year while it is this year's, and a run row shows a time of day
alone. The format and its rules are unchanged
([2026-07-11](2026-07-11-humanize-the-absolute-timestamp-format.md)).

**Carried from the earlier Run History proposal.** The proposal file
replaced one written when the feature was far off. That text described two
views: (1) the current session across scenarios, and (2) one scenario's full
history. Two of its durable decisions were already marked superseded. They
are kept here with their text, which answers the connector's
[comment on PR #351](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/351#discussion_r4191712535)
that a rewrite left them only in git history.

- **Raw timestamps first; sessions are a later quality-of-life layer.** With
  timestamps visible, the user can eyeball the session boundary. Sessions
  automate that, but the views work without them.
  - **Superseded** by row D4 of
    [PR #327](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/327):
    sessions are built first, as the foundation the history views and later
    features share, not as a later layer.
- **Sequencing within the feature:** ship view (2), the per-scenario
  history, first. It needs no sessionization. View (1), the current-session
  view, arrives with the sessionization layer, since "current session" is
  precisely what requires a session boundary to exist.
  - **Superseded** by row D4 of PR #327: sessions come before either view,
    so "it needs no sessionization" no longer sets the order. Which view
    ships first was left open for the rewrite to decide.
  - **Decided by the page proposal, and ratified on 2026-10-12:** view (2)
    shipped first, on sessions, as version 1's run list. View (1) is the All
    scenarios proposal's.

The old file's three positions on sessions are not superseded: gap-based
sessions, a fixed gap, and no SQLite migration. The 2026-10-11 sessions entry
carries them. Its open question about the navigation surface is answered by
R3.

Proposed in
[PR #356](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/356),
which merged as `a65f72d`. Shipped in
[#370](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/370),
[#371](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/371), and
[#372](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/372),
hidden, and made public in
[#373](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/373).
The proposal file, `docs/proposals/run_history_proposal.md`, is deleted, and
git history keeps it.
