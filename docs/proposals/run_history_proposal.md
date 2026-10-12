# Run History Page Proposal

Status: Proposed
Date: 2026-10-11

## TL;DR

The page that charts a scenario's scores plots only each day's top few runs,
and a finished run is reported by a toast that disappears, so the app has
nowhere to look back at the runs just played. This proposal replaces that
page with one called Run History, where the chart plots every run and sits
beside a list of the scenario's runs grouped by session, under a card for the
latest run. The new page gets an address of its own, and the app's landing
address becomes a small Home page that holds first-time setup. It is built
beside the old page and stays hidden until it can replace it in one release.

## Decisions needed

**Nothing in this proposal is ratified.** Seven rows need the maintainer's
judgment, R1 to R7. Each is the maintainer's lean or agreement in chat on
2026-10-10, quoted where the row has their words, and argued here. A lean is
not a ruling: reviewers are invited to contest any row, and any author-owned
choice in [Design](#design).

This is piece 4 of 5 of the Run History work. The groundwork, three refactor
PRs with no proposal, has merged. Sessions is ratified and built: its
proposal was [PR #355](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/355),
and [PR #359](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/359)
built it with nothing on screen. The
[Run toasts proposal](run_toasts_proposal.md) is ratified and waits on this
page. All scenarios is a later proposal. Two things cross between them:

- **This page takes what a session is from the
  [sessions spec](../specs/sessions.md):** when one ends, when it is in
  progress, and a visit, the consecutive runs on one scenario within a
  session. The functions exist, and this page is their first caller.
- **The Run toasts proposal takes this page's name and address, and R7's
  rule for its link.** Its three rows were ratified leaning on R1, R2, and
  R7 here, which are still open. If one of them goes another way, the
  toast's link follows.

**Already decided, and binding here.** The proposal is held to these and
doesn't reopen them:

- **The three skill-judgment principles** in the roadmap's
  [Guiding principles](../roadmap.md#guiding-principles), ratified on
  2026-10-04
  ([decision log](../decision_log.md#2026-10-04-skill-is-judged-by-the-typical-run-with-honest-uncertainty-in-verdicts-not-advice)).
  The check and the star this page draws are verdicts against a bar the
  player set or a record they hold. The page gives no advice.
- **Sessions come before the history views** (row D4 of the same entry).
- **What a session is, and when one is in progress:** rows S1 to S3 of the
  Sessions proposal, ratified on 2026-10-11
  ([decision log](../decision_log.md#2026-10-11-a-session-ends-after-a-break-of-more-than-30-minutes)).
  Its row S4 takes the typical score out of this milestone.
- **The run toast:** rows T1 to T3 of the
  [Run toasts proposal](run_toasts_proposal.md), ratified on 2026-10-11. A
  plain toast on every page, built by the app shell, replaces the verdict
  toast. Top N placement is retired, the **Score threshold verdict** switch
  is dropped, and the **Run notifications** switch moves to the Settings
  page.
- **What a new PB is**
  ([2026-10-05](../decision_log.md#2026-10-05-the-score-vs-time-chart-marks-each-new-pb-with-a-star)).
  R6 changes where stars are drawn, not which runs earn one.
- **Pace** on a time-scored scenario
  ([2026-10-05](../decision_log.md#2026-10-05-time-scored-scenarios-are-measured-by-pace)).
- **One active tab** is the supported way to use the app
  ([2026-07-06](../decision_log.md#2026-07-06-coalesce-pending-home-run-events)).
  The maintainer on 2026-10-07: "Keep the one-active-tab model as it is."
- **The two rules for a remembered control**
  ([2026-09-19](../decision_log.md#2026-09-19-a-query-parameter-selects-a-control-it-does-not-suspend-its-memory)):
  its layout default never varies per visit, and a callback that writes it
  only on some visits must not starve the callbacks that depend on it.

### R1. The page is named Run History

Status: Open. The maintainer, 2026-10-10: "I agree to reverse this decision."

**Recommendation: the navbar link, the page name, and the browser tab read
"Run History".** This reverses one of the four rulings of the
[2026-08-09 naming entry](../decision_log.md#2026-08-09-the-graph-page-is-scenario-performance-its-panel-is-chart-options),
"The graph page's product name is 'Scenario Performance'". The other three
stand: the panel is Chart options, Settings keeps its name, and the panel's
column claims no exclusive tenancy.

- **The page stops being only a chart.** Version 1 adds a list of every run
  and a card for the latest one. "Scenario Performance" names the chart
  alone.
- **It is the name the work already has.** The roadmap has called the
  milestone Run history since it was planned, and the ratified run toast's
  link reads "Open in Run History".
- **The reasoning of 2026-08-09 still holds.** That entry gave the page a
  product name apart from its address. Only the name moves.

Considered and not recommended:

- **"Runs".** Shorter, but it reads as the list alone, or as a count.
- **"Scenarios",** which `gpt-6-astra` suggested. The roadmap's Future list
  already holds a Scenarios page for scenario-first navigation.
- **Keeping "Scenario Performance".**

The cost is a rename: "Scenario Performance" appears on 75 lines in 20
tracked files on `main` at `4272fbb`. 24 of those lines are in the decision
log, where history keeps the old name.

**If the maintainer keeps the old name:** nothing is renamed, the page's
largest new part has no name pointing at it, and the run toast's link, which
was ratified as "Open in Run History", has to be worded again.

### R2. Run History gets its own address, and `/` becomes Home

Status: Open. The maintainer, 2026-10-10: "Does it make sense to create a
placeholder Home page for now? Eventually this will become the Overview page,
which I plan to design/propose/ship after Run History page. This way the
first time setup cards can live on its proper page."

**Recommendation: Run History is served at `/run-history`. `/` serves a new
Home page, and `/home` and `/index` still redirect to it. Home holds the
setup card and the stats-folder hint when they apply, and one line of stats.
It lists no links and forwards nowhere. The navbar reads Home, Run History,
Playlists, Settings.**

- **The 2026-08-09 entry deferred exactly this.** "Reserving `/` for a future
  Overview page and giving this page a durable `/scenario` route waits until
  an Overview has concrete plans." An Overview is now planned after Run
  History.
- **The page is moving anyway.** It is a new module with new control ids
  (see [Remembered controls](#remembered-controls)), so its address can
  change in the release where everything else about it does. Moving it later
  would be a second change, for users and for every link.
- **Two new links need an address that won't move again:** the run toast's,
  and the Playlists pages' scenario links.
- **Setup belongs to the app,** not to one scenario's history.
- **`/run-history`, not `/scenario`.** The address follows the page's name,
  as `/playlists`, `/settings`, and `/aim-training-journey` do. `/scenario`
  stays free for the scenario-first page in the roadmap's Future list.

On what Home shows, the maintainer: "I think 'plain links' is not necessary;
that's already the job of the left navbar. Instead just show some simple
stats that we already collect, such as 'Detected 10,000 runs across 1,000
scenarios.' Or even have a blank home page, if needed." On forwarding `/` to
Run History once setup is done: "Disagree, because eventually the Home
page/Overview page will have things for the user to look at. So we would be
putting in logic that we will soon remove."

What it costs:

- **Each launch lands on Home.** The launcher opens `/`, so until the
  Overview ships the player is one click from Run History at every start.
- **An old bookmark of `/?scenario=...` lands on Home,** which ignores the
  parameters. The Playlists pages' own links are rebuilt for the new address.

What follows from this row is in [Home](#home).

**If Run History stays at `/`:** there is no Home, the setup card stays on
Run History, and the address moves when the Overview arrives, taking the
toast's link, the Playlists links, and bookmarks with it then. **If Home
forwards to Run History:** the launch click goes away, and the forwarding is
removed again when the Overview ships.

### R3. The run list is a second column

Status: Open. The maintainer's lean in the design discussion of 2026-10-06
and 2026-10-07, from a full-size mockup.

**Recommendation: the latest-run card sits in the top row, the chart is
below it on the left, and the run list is below it on the right, about
500 px wide and always shown. Chart options stays a panel that opens beside
the chart.**

The 2026-08-09 naming entry expected the opposite and left the question
here: "Run History composes into this column rather than adding a second
one. If a run history tied to Scenario Performance arrives, how the two
share the space is the run-history proposal's question." The answer
proposed is that they don't share a column.

- **The two have opposite lifetimes.** Chart options starts closed on every
  visit and is opened to tune something. The run list is what the page is
  for. In one column, opening the options would cover the list or push it
  down.
- **They need different widths.** The list's seven columns need about
  480 px (added up from the trial's column widths). The options panel is
  20rem, 320 px.
- **The list is on the right because the newest runs are.** The newest
  points sit at the chart's right edge, beside the newest rows.
- **The same entry allowed for it.** Its fourth ruling says the panel's
  column "claims no exclusive tenancy of the page's right side. It is a
  page-local column a later design may share, stack with, or re-host."

What it costs is chart width. In the mockup at 1600 by 900 the chart is
about 830 by 600 and the list about 500 by 600. With Chart options open the
chart is about 500 px wide, which the maintainer accepts until the panel is
reworked after shipping. None of this has been measured in the real app. See
[Narrow windows](#narrow-windows).

Not recommended:

- **One shared column,** as PR #351 proposed, with Chart options stacked
  above the list.
- **The list below the chart.** Even a panel of five rows there would leave
  the chart about 2.95 to 1, by PR #351's arithmetic from the boxes the
  2026-08-09 panel entry measured. That is flatter than the 2.76 to 1 that
  entry rejected as "wide and shallow".
- **A page of its own.** In session the player would choose between the list
  and the chart.

**If the maintainer chooses one shared column:** it has to be the list's
width, so the chart is no wider than proposed here, and the list and the
options take turns in it.

### R4. The run list is built on AG Grid Community, with hand-built group rows

Status: Open. **Both prototypes were checked with NVDA on 2026-10-11.** The
maintainer, 2026-10-10, after trying both prototypes in Firefox and reading
the library research: "let's go with AG Grid". Asked how to record that:
"Take it as lean". That lean predates the NVDA result below.

**Recommendation: build the list on the grid the app's other tables use,
dash-ag-grid 35.3.0 in its free edition. A session row is a full-width row
drawn by the app's own script, and opening a session is a filter over the
rows.**

A technical trial on 2026-10-10 built the list six ways against `main`. Two
worked: this one, called A below, and a list the app's own script draws as
an ARIA treegrid, called C. The trial recommended C. The maintainer leans to
A. Both numbers and both arguments are here so reviewers can weigh them.

For A:

- **One table library for the whole app.** It shares the playlist tables'
  theme variables, and the shared Columns menu already talks to its API.
- **It does not care how many rows are loaded,** which no state of version
  1 tests. It keeps about 39 row elements in the page whatever is open. C
  slows once thousands of rows are open at once: 935 ms in Edge with all
  12,129 rows of the whole history open, against 46 ms for A. Version 1
  loads 30 sessions of one scenario at a time, 36 to 484 rows in the
  trial, so this is a fact about scale and not a reason for version 1.
- **NVDA can read it and work it.** The pass found nothing that makes A
  unusable where C works. A also reads every cell of a run row with its
  column heading, which C does not.
- **No free library does more.** The research found none that pairs a free
  licence, a released treegrid, a pinned row, row virtualization, and a
  build that runs on the app's React 18.3 without a new toolchain.

Against A:

- **It is a grid made to look like a tree,** through nine pieces of
  grid-specific work, listed in [The run list](#the-run-list). Each is a
  place an AG Grid upgrade can break.
- **That risk has a concrete case.** AG Grid 36.0.0 replaced its row
  containers, and 36.0.1 fixed regressions in two of the options A relies
  on. The Dash wrapper has only a release candidate for 36. Moving to 36
  means checking all of them again.
- **It tells a screen reader less, and NVDA bore that out.** Its root role
  is `grid`, and a row's depth is never announced. The open state sits on a
  button inside the row, so opening or closing a row with Enter, Left, or
  Right says nothing, and only the button speaks. In Firefox the pinned row
  and the first body row are both announced as "row 2", and NVDA counts 40
  rows where there are 41. Tab stops at every cell, seven to a row. AG Grid
  sets the `treegrid` role only through its paid features, at $999 a
  developer, under terms that read as needing a further licence for an app
  handed to its users.
- **A landed run moves the keyboard user to another run.** The prototype
  holds focus by grid position, so when the rows shift, the cell under it
  becomes a different run's. C keeps focus on the same run. The list needs
  a ninth piece of work to do the same, and that fix was not tried.

**What NVDA says.** NVDA 2026.2 was run on both prototypes on 2026-10-11, in
Firefox 157 and Edge 155: 633 recorded steps, read from NVDA's own log by a
script. Both lists can be read and worked, and neither is clean.

- **C does what the trial said it would.** NVDA announces each row's depth
  and whether it is open, and says "collapsed" and "expanded" when a row
  changes. That settles, for NVDA, a doubt the library research had raised:
  the newest evidence it found of a screen reader announcing those was from
  2020.
- **C has failures of its own.** In Firefox its list is two tab stops when
  it scrolls, and the first reads all 41 rows aloud. A fix for that was
  measured. It also reads a run row as one string, with no column headings.
- **Not covered:** Narrator, JAWS, and a person listening. No screen-reader
  user tried either list.

This is evidence for the row, not a verdict on it. It removes the worry
that A can't be used with a screen reader, and it confirms that C says
more.

Speed does not separate them at the planned size. With 30 sessions loaded,
neither takes more than 15 ms to open a session or more than 60 ms to show a
landed run, in Edge and in Firefox.

**What being wrong costs.** Both prototypes share one row model, a Python
function. Only the last step differs: about 370 lines of script for A and
500 for C. NVDA did not show A unusable. If another screen reader does, or
an AG Grid upgrade breaks the group rows, that step is rebuilt and nothing
else moves. What it is rebuilt as is chosen then. Prototype C is one
candidate, and NVDA reads it as a tree. The other is a plain table with
disclosure buttons, which the library research found practitioners prefer
and neither prototype builds.

**If the maintainer chooses the treegrid:** the repository owns the
rendering, the keyboard model, and a second table idiom with no library
under it, and the list has no row virtualization.

### R5. The chart plots every run

Status: Open. The maintainer, 2026-10-07: "ship Run History without the
Median line", and "Average score line - we'll drop this".

**Recommendation: the chart plots every run in its range. The Top N scores
control, the Oldest date to consider picker, and the Average score line go.
Version 1 draws no summary line in any mode.**

Today the chart keeps the top N scores per sensitivity, or per day, and
draws a line through each group's average.

- **A list of every run beside a chart of the best few would contradict
  each other.** The row a player just watched land would have no point.
- **Top N hides the order of play.** Score vs Time keeps each day's best and
  puts them at one position, so it shows neither how a day went nor all of
  it.
- **The Average score line averages what Top N kept.** On a busy day it is
  the average of that day's best, which the 2026-10-05 stars entry already
  notes.
- **A new summary line would be a second definition of the typical run.**
  The typical score has left this milestone (row S4 of the Sessions
  proposal, ratified). A median drawn now would have to agree with it later
  or be replaced.

What is lost, and where it hurts most: **Score vs Sensitivity loses both of
its summaries.** Top N per sensitivity and the Average score line were how
that chart compared one sensitivity with another. Without them it shows
every run at each sensitivity and nothing that sums a sensitivity up. The
maintainer, 2026-10-10: "In that case we may need to redesign that
chart/feature", and "Score vs Sensitivity should not affect the launch. We
can redesign it afterward." So version 1 ships that mode as every run per
sensitivity, and its redesign is a later piece of work.

What a player will see first there is overplotting. Every run at a
sensitivity shares one position along the axis, so a well-played scenario
draws a dense vertical strip per sensitivity, and the spread inside a
strip can't be read. The maintainer's largest scenario had 463 runs on
2026-10-04. That is the first thing the redesign has to answer.

Also lost: a start date of the player's own choosing. The range becomes a
choice from a list (see [The chart](#the-chart)).

**If the maintainer keeps Top N and the Average score line in Score vs
Sensitivity alone:** that mode keeps its comparison until the redesign. The
control, its help text, and an empty state survive for one mode, and the
chart disagrees with the list there. **If a median line ships now:** the
page has a summary, and the later typical score has to match it or replace
it.

### R6. Stars are drawn on Score vs Run

Status: Open. The maintainer, 2026-10-10, on stars in Score vs Run and Score
vs Time and not in Score vs Sensitivity: "Agreed."

**Recommendation: Score vs Run stars each plotted run that was a new PB, as
Score vs Time does. Score vs Sensitivity still has none.** This extends the
[2026-10-05 ruling](../decision_log.md#2026-10-05-the-score-vs-time-chart-marks-each-new-pb-with-a-star),
"Only Score vs Time is marked".

- **The ruling's own reason covers it.** "Along the date axis the stars read
  left to right as the history of the PB, and along the sensitivity axis
  they have no order." Score vs Run is in play order too.
- **It answers a cost that ruling accepted.** "The chart opens on Score vs
  Sensitivity and remembers the choice per browser, so a fresh browser shows
  no stars until the reader switches." The new chart opens on Score vs Run.
- **The star in the list and the star on the chart are the same runs.** The
  list marks a new PB by the same rule, so the default mode should too.

Stars become a smaller share of the points. Under Top N scores of 5, 666 of
the year's 2,220 plotted points were stars (measured 2026-10-04). With every
run of the year plotted, about one point in five would be: 691 new PBs
against 3,272 runs, two counts taken a day apart.

Score vs Sensitivity stays unmarked for the first of the ruling's two
reasons. The second, that the chart kept only the top scores at each
sensitivity, stops applying under R5.

**If the maintainer keeps stars to Score vs Time:** the page opens on a
chart with no stars beside a list that has them.

### R7. Follow and a `?scenario=` link clear a Playlist filter that does not list the scenario

Status: Open. The maintainer, 2026-10-10, on Follow: "For now if this
happens, we can simply unfilter the playlist, as it probably implies that
the user is not playing the playlist anymore." On the link: "I initially
lean yes, but what is your take?"

**Recommendation: when Follow lands on a scenario the Playlist filter does
not list, or a `?scenario=` link names one, the filter is cleared and the
scenario is selected. The scenario must have local runs.** The author's
take on the link is yes, for one reason: one rule then covers every way of
reaching such a scenario.

- **Today neither way works well.** A `?scenario=` link keeps the filter and
  drops the scenario, leaving nothing selected
  ([Identity](../specs/scenario_performance.md#identity)). Follow's callback
  writes the scenario without looking at the filter. What the dropdown then
  shows was not checked for Follow. On this app's playlist filter, the same
  component kept the previous option's name on screen when a callback wrote
  a value its list lacked (headless Edge, 2026-10-11). So Follow most likely
  leaves the old scenario's name in the dropdown while the chart and
  Scenario Stats show the new one.
- **The list makes it more visible.** A run that lands is a new row and a
  new card. A page still filtered to a playlist that run isn't in would
  show a selection its own dropdown can't name.
- **The same rule will cover a click in the All scenarios tree** (row A1 of
  that proposal), and it covers the scenario link on the latest-run card.
- **The ratified run toast's link depends on it.** That link names the
  scenario and carries no playlist, because the app shell doesn't know what
  the page's filter holds.

What it costs: clearing the filter takes away the rank lines and the Open
scenario table link, and the cleared filter is what the browser then
remembers. One run outside a playlist means picking the playlist again. The
filter empties in view and no toast says so. The Follow switch's help text
gains a sentence about it (see [Copy](#copy)).

The 2026-09-19 entry's statement that `?scenario=` alone leaves the filter
alone gains this one exception. Its two rules for remembered controls bind
the new page unchanged.

**If the maintainer keeps today's link rule:** a link to a scenario outside
the filtered playlist selects nothing, while Follow on the same scenario
clears the filter. A run toast for such a scenario then opens the page with
nothing selected. **If Follow should keep the filter too:** it has to stop
following such a run, or the dropdown has to show a scenario its playlist
doesn't list, and the card then reports a run the rest of the page ignores.

### The build approach, a stated lean and not a row

The page is built as a new page beside the old one, at its own address with
no navbar entry and no link to it, until it can replace the old page in one
release. It reuses the old page's working parts and does not rewrite them.

The maintainer has leaned to this three times. On 2026-10-07: "If a whole
page rewrite will result in a cleaner and more efficient implementation,
then I'll vote for that. I can accept the additional releases that the user
won't see until the page fully ships. The final swap can be derisked if I am
part of the verification process while the new page is being built." On
2026-10-10: "I agree on this approach. My thinking is that this approach
will lead to a cleaner implementation and less-risky shipping process; at
any time we can rollback by simply deleting the new page." And of many
changes landing in one release: "I think this is a non-issue."

`claude-fable-5-1` first recommended changing the page in place, in shipped
slices. Its breakdown of 2026-10-10 no longer contests the new page: the
smaller version 1 gives most of what changing in place offered, and the
groundwork is the same work either way. It settles when this proposal is
ratified.

## Problem

### What the page does today

The app is a Dash web app that watches the KovaaK's stats folder and plots
each scenario's scores. Its landing page, Scenario Performance, shows a
finished run in three ways
([spec](../specs/scenario_performance.md#the-graph)):

- **A point on the chart,** if the run is among the top N scores at its
  sensitivity, or of its day in Score vs Time. N defaults to 5.
- **A toast,** when the run passed or missed the score threshold or placed
  in the top N at its sensitivity. It is on screen for a few seconds.
- **Lines in the debug log.** The watchdog (the thread that imports each new
  stats file) logs every run's distance from the PB and whether it passed a
  fixed 95%. The log is developer-facing.

So the app can't answer what the player asks between runs: what did I score
on the runs just before this one, and how many have I played this session.
The maintainer, in the brainstorm note of 2026-09-28 that PR #351 quotes:

> Most common use case is looking at a scenarios run history and using that
> data to help influence the next run. But I also want to understand where
> the run fits into a session.

### Why this shape, and why now

Run history and sessions is the roadmap's only Upcoming milestone. It was
first written as one proposal,
[PR #351](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/351),
whose design a two-day discussion then moved away from. The maintainer on
2026-10-10: "One of my main concerns about the Run History proposal is
trying to ship too many things at once." The work was split, and the
maintainer agreed the split that day: "Merged breakdown is a go." That
agreed the outline and ratified no row.

Version 1 is the smallest page worth making public. The maintainer: "I want
to ship the MVP version of the Run History page first; additional
functionality can come later unless it blocks version 1." It has four parts:
the rebuilt chart, the run list for the selected scenario, the latest-run
card, and the old page's kept parts. Two of them cannot wait for a later
release:

- **The chart changes.** A list of every run beside a chart of the top N
  would contradict each other.
- **The card.** Once the run toast goes plain, the card is the only place a
  run's percentage of the PB appears.

### Verified facts

Measured on the maintainer's stats folder unless a line says otherwise. It
is one player's history: 8,937 runs over 866 scenarios, which make 321
sessions at a 30-minute gap (2026-10-05). Nothing was measured again for
this proposal. The folder grows daily, and the Sessions proposal counted a
later snapshot: 322 sessions on 2026-10-08.

- **A time axis bunches recent play.** On Smoothsphere Viscose at All time,
  half of the 61 runs sit in the right-hand 10% of a time axis. In run order
  they spread evenly.
- **Returns are common.** 66 of 321 sessions contain a scenario that was
  left and returned to, 26 of them in 2026. The list's divider is for those.
- **The parser already reads shots and hits,** to compute accuracy, and
  discards them. PR #351 said it does not read shots.
- **Rows sent as Dash components are ruled out.** Dash took 32 to 36 seconds
  to draw 30 sessions' rows, 887 rows and about 7,000 elements. A bare Dash
  4.4.1 app took 27.8 seconds for 1,000 rows of seven cells, and the cost
  per component doubles each time the count doubles.
- **Tree data and row grouping are paid features** in the installed AG Grid.
  A grid given `treeData` logs error #200 and shows the rows flat.
- **NVDA reads both prototypes.** NVDA 2026.2, in Firefox 157.0.1 and Edge
  155, on both views: 633 recorded steps on 2026-10-11. What it said is
  under R4.
- **The two working prototypes, 30 sessions loaded** (888 rows, medians in
  milliseconds). "Run lands" is from the batch reaching the browser to the
  new row painted.

  | | A, Edge | C, Edge | A, Firefox | C, Firefox |
  |---|---|---|---|---|
  | Open one session | 6.8 | 3.2 | 10 | 2.9 |
  | Run lands | 31 | 23 | 51 | 23 |
  | Run lands, every row open | 35 | 43 | 60 | 25 |

  Version 1's view is smaller: 36 rows for the last-played scenario and 484
  for the most-played one.
- **The row model the server sends** is 5 KB for 36 rows, 72 KB for 484, and
  142 KB for 888. Sending all of it on every landing was fast enough that
  neither prototype needed a smarter update.
- **The old page was large.** `source/pages/home.py` was 2,630 lines and
  `tests/test_home_*.py` totalled 5,657, at `4272fbb`. The three groundwork
  PRs have since moved the kept blocks into modules both pages can import,
  and `home.py` is 1,214 lines.
- **Every hidden PR is a public release.** A push cuts one unless every
  changed path is documentation, tests, or repository tooling
  (`scripts/release_job.py`). The maintainer accepts releases that change
  nothing a user can see.

The trial's scripts and results, the mockup, and the design notes are
untracked, under `ignore/` in the maintainer's main checkout. This proposal
carries what a reviewer needs from them.

### Not checked

- **Narrator and JAWS, and a person listening.** NVDA's output was read by
  a script, on the two prototypes. No screen-reader user tried either list,
  and the list this proposal builds does not exist yet.
- **The layout in the real app.** Every size here is from the mockup or the
  trial's stand-in pages.
- **A visible browser.** Both trial passes were headless. The maintainer
  tried both prototypes by hand in Firefox.
- **The real chart beside the list.** A run landing also rebuilds the chart,
  on the same thread. The trial's chart was a stand-in.
- **AG Grid 36.** Every workaround under A was checked on 35.3.1 only.
- **The zoom script on a numeric axis.** Score vs Run is the first.
- **Two pages sharing a control id, in this app.** A scratch Dash 4.4.1 app
  on 2026-10-11 showed the rule is narrower than the list assumed. A page
  may hold an id that is only an input of another page's callback. It breaks
  when it holds a callback's output without all of that callback's inputs.
  That was not tried under `DashProxy`, which the app uses. Nothing here
  depends on it: the new page keeps its own ids either way.
- **Other players' data.**

## Design

Every choice in this section is author-owned unless it names a row. Each is
open to challenge.

### The page at a glance

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
scenario being played. The session is context around it. The page fills the window's
height as the old one does: the chart and the list take the room under the
top row, and the list scrolls inside its own box.

### Home

What follows from R2.

- **`home.py` shrinks into Home.** The old page's controls, chart, and
  callbacks are deleted from it when the page goes public. The setup card
  and the stats-folder hint keep their place on the page. Their builders
  move to a shared module, as the groundwork moved the other kept blocks,
  so Run History draws its own copies without importing the Home page's
  module. Its page name becomes "Home".
- **What Home shows,** top to bottom: the stats-folder hint and the setup
  card when they apply, exactly as the old page shows them
  ([Hosted setup surfaces](../specs/scenario_performance.md#hosted-setup-surfaces)),
  then one line of stats.
- **The stats line** counts the runs and the scenarios in the run store. It
  is drawn only while the app has a usable stats folder, because the hint
  already speaks for the other case. It is worked out when the page is
  drawn and does not tick.
- **The navbar** reads Home, Run History, Playlists, Settings. Home keeps
  the house icon and Run History gets one of its own. Home has an entry
  because the launcher lands there on every start, and a landing page
  missing from the navbar would highlight nothing. The header title still
  leads to `/`, which is now Home.
- **The Playlists pages' scenario links** point at
  `/run-history?playlist_code=...&scenario=...`. One function builds them.
- **Run History with no runs to read** explains itself in place. It shows
  what Home shows in that case, above its top row: the stats-folder hint,
  and the setup card's two yellow states, "Your settings can't be read"
  and "Finish setting up". Each is as it is today, and neither has Skip.
  The hint alone would not cover it: it speaks only for a stats folder
  that is set and can't be used, so with no folder set, or with a settings
  file the app can't read, the page would be empty with no reason given.
  Its chart and list keep their ordinary empty states. The card's blue
  account offer is Home's alone: it is the app's first-run offer, and it
  explains nothing about an empty page.
- **Failed run imports and startup playlist warnings** reach the screen
  today only while the old page is open
  ([Run delivery](../specs/scenario_performance.md#run-delivery)). Home and
  Run History both host them, so a warning raised at startup still shows on
  the page the launcher opens. Whichever page is open empties the queue.
- **The launcher is unchanged.** It opens `/`.

Not proposed: a `/?scenario=` link forwarding from Home to Run History. It
is listed under [Optional, beyond the outline](#optional-beyond-the-outline).

### The top row

Kept from the old page, in this order: the Playlist filter with its Open
scenario table link, the Selected scenario select with the Follow newly
played scenario switch under it, and the Scenario Stats block with Last
played, Number of runs, and Position. The latest-run card follows and fills
the rest of the row. Top N scores and the date picker are gone (R5), and the
chart mode and the Chart options button move into the chart's header.

`?scenario=` and `?playlist_code=` select the two dropdowns on the new
address as they do today, by callback and never as a layout default, with
R7's one change.

The page's layout also accepts parameters it doesn't name, as the old page's
does. The ratified run toast's link carries `run=` beside `?scenario=`. The
page never reads it. It is there only so each toast's address is new,
because a link to the address the page already holds does nothing.

### The latest-run card

The card reports the last run played, whatever scenario is selected. It
updates on every batch of new runs.

- **First line:** "Latest run", the run's time, and its scenario. When
  another scenario is selected, the scenario's name is a link that selects
  it, under R7's rule. The time is a time of day for a run played today and
  carries the date otherwise.
- **The score,** large, with one badge beside it. A new PB shows New PB,
  whether or not the run was judged. Otherwise a judged run shows Threshold
  passed or Below threshold, and an unjudged run shows no badge. The
  maintainer agreed the card keeps a worded "Below threshold": "Yes."
- **Second line:** the run's percentage of the PB it was chasing, and its
  accuracy. A new PB says how far it beat the previous best instead. The
  percentage is a fact about the run, so it shows whether or not the run
  was judged, and an empty threshold doesn't hide it. Two kinds of run
  have none, and show the accuracy alone: a scenario's first run, and a
  run that is not a new PB and is compared by score with a PB of zero or
  less.
- **Third line:** which run of the scenario this is in its session, and the
  clock time spent on the scenario in that session. Once the session has
  ended the line says "last session". Where that time can't be known, the
  line says so and keeps the run's number.
- **One height through every state,** so the page doesn't jump.
- **With no run in the store** it says so, at the same height.

The percentage follows the toast's rules today: the same PB, the same pace
rule, and the same two display caps
([Run notifications](../specs/notifications.md#run-notifications)). The
badge follows [Marks](#marks-the-check-and-the-star). The page works out the
run's number and the time on the scenario from what the
[sessions spec](../specs/sessions.md) defines: the session, and a visit,
which is consecutive runs on one scenario within it. The time is the sum of
the scenario's visits in the session, each from its first run's start to its
last run's end, so it includes the breaks between a visit's runs.

The time is unknown when the first run of any of those visits has no usable
start. The sessions spec then counts that visit from the run's end, so a
visit of one long run would add nothing and the card would read `<1 min`.
The card never shows a number in that case. When a run has no usable start
is in the
[sessions spec](../specs/sessions.md#run-start-and-run-length).

The card and the marks are worked out from the run store, never from the
message a new run arrives in. So the card is right on a page load with no
new run, and a past run's check needs nothing that was not kept. The Run
toasts proposal left that choice to this one.

Not in version 1, both dashed in the mockup: "Better than 19 of your last
20", and a percentage against the typical score.

### The chart

- **Three modes:** Score vs Run, Score vs Time, and Score vs Sensitivity.
  The control is in the chart's header.
- **Score vs Run is the default.** It plots the scenario's runs in the order
  they were played, evenly spaced. Its axis labels are dates, one at the
  first run of a day, thinned so they don't collide. It is the mode that
  shows every run of a session apart, which is why the page opens on it.
  The order is the one the
  [sessions spec](../specs/sessions.md#sessions) sets: by when a run ended,
  with its rule for runs that ended in the same second. So the chart and
  the list never disagree about which run came first.
- **Score vs Time** plots each run at its own timestamp. The day no longer
  shares one position.
- **Two runs can still share a position in Score vs Time.** A run's
  timestamp is in whole seconds, so runs that ended in the same second
  with the same score sit on one point. The chart keeps today's rule for
  points at one position: a new PB comes last among them in the run trace,
  so the hover shown under a star is the hover of the run that set the PB.
- **Score vs Sensitivity** plots every run in the range at its sensitivity
  (R5).
- **Ranges.** Score vs Run counts runs: the last 50, 100, or 200, or all of
  them. The other two modes count days: the last 7, 14, 30, or 90 days, the
  last 12 months, or all time.
- **A range of N days is N calendar dates, counting today.** It starts at
  local midnight N minus 1 days before today. On October 11 the last 7 days
  are October 5 to 11. So the label and the chart agree, and a point leaves
  the chart at midnight and not in the middle of a day. The last 12 months
  are 365 days, counted the same way.
- **The chart opens on the last 100 runs,** or the last 90 days in the other
  two modes. The maintainer: "I think those are reasonable defaults".
- **The mode and the range are remembered** by the browser, with one
  remembered range for runs and one for days. The maintainer: "Yes agreed."
  The two ranges are two selects, one shown at a time, because a remembered
  control's layout default can't vary.
- **Kept from today:** the PB score line, the Score threshold line, the rank
  lines, the New PB stars with their look and their Point size rule, the
  point hover, the legend, the empty and placeholder figures, the zoom fit,
  and plotly's own toolbar with Download plot as a PNG and Share chart.
- **The plot title is the scenario's name alone.** The maintainer: "Keep the
  title for now, since it's possible that the user will export the chart",
  and "Remove the timestamp; its timestamp is no longer useful."
- **The hover** shows the run's timestamp with seconds, its score, its
  sensitivity, and its accuracy, in every mode. The day line Score vs Time
  shows today is dropped, since the timestamp above it says the same. In
  Score vs Sensitivity the sensitivity is the axis and is not repeated, as
  today. Nothing new goes into the hover.
- **Rank lines redraw at once when the Playlist filter changes.** The
  maintainer: "Otherwise it would look like a bug to the user; when they
  switch playlists, they would expect to see the new rank lines."
- **The latest run is ringed.** While the selected scenario is the one last
  played and that run is in range, its point carries a ring and its row in
  the list is highlighted, so the card, the row, and the point read as one
  run. The ring has no legend entry and no hover of its own.

Plotting every run widens the score range downward, so more of a playlist's
rank ladder falls inside it without **Show all ranks**.

**Not carried from the mockup: the 2 px nudge in Score vs Time.** The mockup
spreads a session's runs 2 px apart so they can be counted, and the
maintainer leaned to keeping that. plotly places a point by its data value.
The author knows of no per-point pixel offset for a scatter trace and found
none in the documentation searched. A nudge would mean moving points off
their real times by an amount that depends on the chart's width and zoom,
recomputed in the browser after every draw. Over 90 days at 830 px, 2 px is
about five hours. Score vs Run is the mode for counting a session's runs,
and zooming Score vs Time separates them. This departs from a lean, so it is
called out in the PR description too.

### The run list

Version 1 has one view, the selected scenario's runs. All scenarios, and the
switch between the two, are a later proposal.

**What it shows.**

- **Two levels:** sessions, newest first, and under each the scenario's runs
  in that session, newest first. Only sessions that hold a run of the
  scenario are listed.
- **A session row** is named by when it started. The session in progress
  carries an "In progress" badge. The row's right side reads how many of the
  session's runs were on this scenario, such as "7 of 47 runs". In version 1
  that is plain text. Row A2 of the All scenarios proposal makes it a link.
- **The current session is always the first row,** and stays in view under
  the column headings while the list scrolls. It is there even when the
  selected scenario has not been played in it. Its right side also gives the
  session's length. With no session in progress the first row is the last
  session, without the badge.
- **A run row** has seven columns: the run's number in its session, its time
  of day, its score, its marks, its accuracy, the shots fired, and its
  sensitivity. Runs are numbered per session, counting this scenario's runs
  only.
- **A divider** marks where the scenario was left and returned to, such as
  "10 runs on 3 other scenarios".
- **A date header** names each calendar date in a session that crosses
  midnight. A run row shows a time of day alone, and the session's name
  gives only the date it started on. So where a session's runs of the
  scenario fall on more than one date, each date's runs sit under a header
  that names it. A session on one date has none. Where a header and a
  divider fall between the same two runs, the divider comes first, and the
  header sits directly above the runs it names.
- **Shots fired is shown on every scenario.** The run record gains the
  field. The parser already reads it.

**How it behaves.**

- **A row opens and closes on a click,** with no request to the server.
  **Expand all** opens every loaded session and reads Collapse all once they
  are all open.
- **The Columns menu** shows or hides Shots fired and Sensitivity, both
  shown to start. It is the menu the playlist tables use
  ([2026-10-05](../decision_log.md#2026-10-05-a-columns-menu-shows-and-hides-table-columns-and-kovaaks-ids-are-optional-ones)),
  so its choices are remembered in the browser. The maintainer, asked
  whether they should be: "Yes."
- **It loads 30 sessions at a time.** **Show older sessions** adds 30.
- **Which rows are open is not remembered.** On arrival the first row is
  open and the rest are closed.
- **A run that lands** shows as a new row with nothing lost: opened rows
  stay open, and keyboard focus stays on the same run. The prototype did
  not do the second: it held focus by grid position, so the focused cell
  became another run's. Item 9 below is the fix. The current session
  opens for it, once per run, so a row the player closed is not reopened by
  a later change of scenario. With Follow on, the list scrolls back to the
  top.
- **"In progress" clears without a run.** The sessions spec has the rule:
  a session is in progress until 30 minutes after its last run. The
  badge, and the card's "this session", change on the page's existing
  30-second tick, the one that keeps Last played current. No new polling is
  added. The app works the state out, never the browser's clock, as that
  spec requires. This answers the connector's
  [comment on PR #351](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/351#discussion_r4191712545)
  that a list redrawn only by a new run could read "in progress" forever.
- **A late run can reopen a session.** Under the sessions spec's rule a run
  with a usable start that began inside the 30 minutes joins its session
  when it finishes, even after the session has read as ended. The list and
  the card follow, because both rebuild when a run lands.
- **Columns don't sort.** A sort would scatter each session's rows.

**How it is built (R4).**

- **One Python function builds the rows.** Its inputs are the run store, the
  selected scenario, and how many sessions to load. It returns a flat list
  of row records: session rows, run rows, dividers, and date headers. It
  also names the
  newest run and the rows that run forces open. A session's row is keyed by
  the session's first run, since a session has no stored identity.
- **The list rebuilds from the run store, not from the batch.** The batch of
  new runs only triggers it. Two open tabs race for each batch, and a list
  built from batches would miss runs in one of them.
- **The rows reach the grid as data,** through a store and a script, never
  as Dash components.
- **What is open never leaves the browser.**

The nine pieces of grid-specific work. The first eight were built in the
prototype and checked on AG Grid 35.3.1. The ninth comes from the NVDA
pass and was not built:

1. A session row is a full-width row with its own renderer. A full-width row
   has no cells, so its `gridcell` role is added by hand.
2. Opening and closing is an external filter over a set of open row ids kept
   in script.
3. The current session is a pinned top row. The pinned row and the body rows
   have to change together, so rows go in through the grid's API and not the
   `rowData` prop the other tables use.
4. `embedFullWidthRows` and `ensureDomOrder` put the two kinds of row in
   reading order.
5. Enter, Space, Left, and Right are handled by a key listener.
6. Tab into a session row's links needs a listener that runs before the
   grid's own.
7. Sorting is off on every column.
8. The fixed column widths leave room for the scrollbar.
9. After new rows are applied, focus goes back to the cell of the same row
   id. The grid holds focus by position, so a landed run otherwise leaves a
   keyboard user on a different run.

One variation was not tried and could remove items 1, 4, and 6: ordinary
rows whose first cell spans every column. The implementing PR may try it
first. It would not change the `grid` role or the missing row levels.

The NVDA pass found three more things on the prototype that the list's PR
fixes, because each is cheap. The grid had no accessible name, and the Copy
block gives it one. A session row's button repeated the row's visible name,
so the name was read twice. And opening or closing a row from the keyboard
was silent: the PR announces the change, a fix the pass inferred and did not
try. Two things it found have no known fix in the free edition: a row's
depth, and Firefox's numbering of the pinned row.

### Marks: the check and the star

Two facts about a run are drawn beside its score, in the run list and as the
card's badge. This carries the Marks section of PR #351, less its line about
a switch.

- **Threshold passed,** a check. The run met the score threshold, judged as
  the toast judges it today: against the PB the run was chasing, which is
  the scenario's best score before it at any sensitivity
  ([2026-07-08](../decision_log.md#2026-07-08-judge-score-threshold-notifications-against-the-previous-pb)).
  It is judged by pace where the app measures pace on the run's own
  version of the scenario. See [A past run's pace basis](#a-past-runs-pace-basis).
- **New PB,** a star: the rule the chart's stars use. A run can carry both.

Three consequences, which the maintainer worked through on 2026-10-10:

- **A later PB removes no check.** A check means "passed when it was
  played", the way a star means "was the PB when it was played". "I think
  that is a good rule." The cost: the chart's threshold line is drawn at the
  current PB, so an old run can carry a check and sit below today's line.
- **A change to the percentage re-marks every run, at once.** The percentage
  in force when an old run was played was never recorded. It lives only in
  the browser, and the watchdog can't read it. "Sounds good." So checks are
  per browser, as toasts are today.
- **No switch gates a mark.** An empty percentage is the one way to turn
  checks off.

The maintainer's worked example. The PB is 100. Runs A to E are played in
order at one sensitivity.

| Run | Score | Chasing | At 90% | At 99% |
|---|---|---|---|---|
| A | 85 | 100 | no check | no check |
| B | 95 | 100 | check | no check |
| C | 120 | 100 | check and star | check and star |
| D | 100 | 120 | no check | no check |
| E | 110 | 120 | check | no check |

Raising the percentage to 99 takes the check from B and E, and setting it
back returns both. C's new PB never touches B's check, because B is compared
with 100, not 120. The field has no maximum. Above 100 percent a run has to
beat the PB it was chasing by that margin, so every check then sits on a run
that is also a new PB: at 110 percent C keeps its check and no other run has
one.

#### A past run's pace basis

The pace rule
([Time-scored scenarios](../specs/scenario_performance.md#time-scored-scenarios))
lets a scenario's newest run name the version that every comparison is
judged under. That fits a toast, which only ever judges the newest run.
Applied as it stands to an old run, it would let a later run on another
version change the old run's check. An old run that missed by pace would
stop counting as a pace comparison, be judged by score, and pass, with no
change to the run, to the PB it was chasing, or to the percentage. So a
past run is judged under its own version:

- **The version is the run's own:** the one its stats file names in
  `Hash:`.
- **Whether that version is time-scored, and its constant, is decided once
  for the version,** from the newest performance file of that version that
  can answer. For the scenario's current version that is today's rule
  unchanged.
- **The comparison is by pace** only when the PB the run was chasing was set
  on the same version and both times are positive. Otherwise it is by
  score.
- **A run is judged by score** when its file names no version, or when no
  performance file of its version can answer.

So a run on a later version changes no earlier check. One thing can still
move an old check, once: the first performance file of a version that can
answer turns that version's earlier runs to pace. The app's other pace
surfaces move at that same moment, and the spec already says of it that
"its numbers move then". That is a correction toward the right measure,
not a verdict taken back. The latest run is judged exactly as its toast
was, because the newest run has always named its own version.

Judging each run by what the app knew on the day it was played was
considered and not taken. It would keep score verdicts on runs the app now
knows were time-scored, beside pace verdicts on later runs of the same
version, and it would parse one performance file per listed run.

**Not judged.** Three kinds of run get no verdict, as today:

- every run, while the Score threshold percentage is empty;
- a scenario's first run, and the first run at a new sensitivity;
- a run compared by score whose PB before it was zero or less, which leaves
  no percentage to judge by.

That is about the threshold only. A star never depends on it: the first run
at a new sensitivity can be a new PB and carry one. A row with no verdict
has no check, and neither does a judged run that missed. The column shows
both as blank, and the cell's hover and accessible text give the one reason
that applies, taking the first that fits in the order above. The glance
answers "which runs passed", and the reason is one hover away.

The card has room, so it words a miss. Its badge is New PB whenever the run
is one, judged or not. Otherwise a judged run shows its verdict, and an
unjudged run shows no badge.

Every state together. The last column is the card's percentage of the PB
the run was chasing.

| The run | Check | Star | Card badge | Card percentage |
|---|---|---|---|---|
| Judged, and passed | check | if a new PB | New PB if one, else Threshold passed | shown |
| Judged, and missed | none, "Below threshold" | if a new PB | New PB if one, else Below threshold | shown |
| Any run while the percentage is empty | none, no percentage is set | if a new PB | New PB if one, else none | shown where one exists |
| A scenario's first run | none, a first run | never | none | none |
| The first run at a new sensitivity | none, a first run | if a new PB | New PB if one, else none | shown |
| Compared by score, with a PB before it of zero or less | none, no percentage to judge by | if a new PB | New PB if one, else none | none. A new PB names the previous best |

A judged miss can be a new PB only with the percentage above 100. A
comparison by pace needs only positive times, so a time-scored PB of zero or
less is still judged, as today.

**The percentage field.** It sends every keystroke today, so typing 90 over
95 passes through 9, and every check on the page would flicker through it.
The list's PR sets the field to send on Enter or on leaving it. That option
was read in the component's documentation and not tried, so the PR checks it
in a browser. The threshold line then moves on Enter too.

### Run delivery and live updates

The app shell already drains new runs on every page and publishes one batch
per poll. The new page consumes that batch as the old one does: one chart
rebuild and at most one change of scenario per batch. Three things are new.
The card updates on every batch. The list rebuilds from the run store. And
under R7, Follow clears a filter that doesn't list the scenario just played.

While both pages exist, each consumes the batch on its own. Only one is open
at a time.

### Chart options

Kept as a panel beside the chart, with its controls, their defaults, and its
closed-on-arrival rule. It opens between the chart and the list, as the
mockup has it. The maintainer accepts the narrower chart until the panel is
reworked after shipping.

Two things change, both from R5: the Top N help text goes with its control,
and the Score threshold percentage help text loses its claim that only
notifications judge a run (see [Copy](#copy)).

The panel has four groups today, and two of its controls are notification
switches. The ratified Run toasts proposal settles both: **Score threshold
verdict** is dropped, and **Run notifications** moves to the Settings page
with its group. This page carries both switches as they are until that
change lands. After it the panel has three groups and no notification
control.

### Narrow windows

Two rules, both measuring the page's own boxes and never the window, because
the navbar takes 225 px without changing the window's width
([2026-08-03](../decision_log.md#2026-08-03-homes-controls-row-measures-the-content-area-not-the-window)).

- **The list drops under the top row when the page area is 900 px or
  narrower.** The order is then the top row, the card, the list at up to
  600 px tall, and the chart. The page scrolls. The trial measured this rule
  on stand-in pages:

  | Window | Page area | Layout |
  |---|---|---|
  | 1400 by 900 | 1,143 px | Chart 631 px beside the list at 500 px |
  | 1100 by 900 | 828 px | Stacked: the list, then the chart |
  | 375 by 812 | 328 px | Stacked. The list scrolls sideways |

- **Chart options sits beside the chart only while the chart's own area is
  48em or wider,** 768 px. Below that it stacks above the chart, as it does
  today below 62em. The chart's area is now the window less the navbar and
  the list, so today's 62em would stack the panel in every window narrower
  than about 1,760 px. By arithmetic, a 1600 px window leaves the chart's
  area about 830 px, so at 48em the panel opens beside a chart about 500 px
  wide, as the lean has it. A 1400 px window leaves 631 px, so the panel
  stacks there. Beside the chart it would leave about 300 px.

Both figures are arithmetic and the mockup, not the real app. The first
implementation PR measures the chart at 1400, 1600, and 1920 px wide, with
Chart options open and closed, and reports the boxes. It may move either
threshold and says so.

There is no phone design. At phone width the list's seven columns need about
480 px and scroll sideways. With Shots fired and Sensitivity hidden they
need about 305 px and would fit. The maintainer wanted a phone layout only
if it is cheap, and agreed to one cheap stacking rule.

### Remembered controls

- **The new page keeps its own control ids,** while hidden and after it goes
  public. Dash stores a remembered value under the control's id, so every
  browser sees the defaults once on the day the page goes public: a
  threshold of 95, **Run notifications** on, the default point size and
  color, and no playlist or scenario until Follow picks one up.
- **The maintainer accepts the reset.** "I can accept the user browser
  settings reset. It's only a one time reset, and the page would look and
  feel like a new page anyways."
- **That release's notes say so,** in one line.
- **Remembered on the new page:** the Playlist filter, the Selected
  scenario, Follow, the chart mode, the two ranges, the Chart options
  controls, and the Columns menu's two checkboxes. Chart options has nine
  controls while both notification switches are carried, and seven once the
  Run toasts change lands.
- **Not remembered:** whether Chart options is open, as today, and which
  session rows are open.

The 2026-08-09 panel entry says "Ids and defaults survive verbatim". This
sets that aside once, for the move to a new page. The rule itself stands
for every later change.

### Copy

Every string on the page. They follow the nine copy rules in
[AGENTS.md](../../AGENTS.md#styling-conventions). The mockup's strings were
placeholders. Scores are formatted as the playlist scenario table formats PB
Score: thousands separators, at most two decimals, trailing zeros dropped
([2026-09-27](../decision_log.md#2026-09-27-the-scenario-table-drops-trailing-zeros-from-pb-score-and-pb-cm360)).
Durations use the app's existing form: `<1 min`, `9 min`, `1 hr 6 min`.

**Navigation and Home**

| Where | String | Why |
|---|---|---|
| Navbar link, page name, browser tab | `Home` | The landing page. One word, as Playlists and Settings. |
| Navbar link, page name, browser tab | `Run History` | R1. Title Case, as a page title. |
| Home, the stats line | `Found {runs} runs across {scenarios} scenarios in your stats folder.` | It answers a new user's first question after setup: did the app find my runs. "Found" is the setup card's own word on the same page ("No KovaaK's stats folder was found"), and "stats folder" is the app's term. The maintainer's example read "Detected 10,000 runs across 1,000 scenarios." |
| Home, the stats line, a count of one | `1 run`, `1 scenario` | Singular where the count is one. |
| Home, a stats folder with no runs in it | `No runs found in your stats folder yet. Play a scenario in KovaaK's and your runs will appear in Run History.` | What happened, then what to do. The page name is plain, as a page name is. |

**The latest-run card**

| Where | String | Why |
|---|---|---|
| First line | `Latest run · {time} · {scenario}` | A readout. "Latest" and not "Last", which reads as final. |
| `{time}`, a run played today | `10:50 PM` | The date would be noise. |
| `{time}`, an earlier day | `Oct 4, 10:50 PM`, or `Dec 30, 2025, 10:50 PM` in an earlier year | The app's timestamp shape, with the year left out while it is this year's. |
| The scenario link, accessible name | `Show {scenario}` | The link text alone is a scenario name. |
| Badge | `New PB` | The chart legend's entry, word for word. |
| Badge | `Threshold passed`, `Below threshold` | The two verdicts as the glossary and today's toasts word them. |
| Second line, judged or not | `{pct}% of PB · Accuracy {accuracy}%` | The toast's own wording for the percentage. One decimal, with the toast's two caps. |
| Second line, judged by pace | `{pct}% of PB pace · Accuracy {accuracy}%` | The one word that says which measure was used, as in today's toast. |
| Second line, a new PB | `Up {pct}% on your previous best of {previous} · Accuracy {accuracy}%` | The celebration toast's sentence, as a readout fragment. |
| Second line, a new PB by pace | `{pct}% faster than your previous best of {previous} · Accuracy {accuracy}%` | The same toast's pace wording. |
| Second line, a new PB over a previous best of zero or less | `Your previous best was {previous} · Accuracy {accuracy}%` | No percentage exists. The toast's own fallback. |
| Second line, no percentage | `Accuracy {accuracy}%` | For a scenario's first run, which has nothing to compare with, and for a run that is not a new PB and is compared by score with a previous best of zero or less. |
| Third line, session in progress | `Run {n} this session · {duration} on this scenario` | Matches the list's number column. |
| Third line, session ended | `Run {n} last session · {duration} on this scenario` | "This session" would be untrue. The latest run's session is always the last one. |
| Third line, the time is unknown | `Run {n} this session · Time on this scenario unknown`, or the same after `Run {n} last session` | For a visit whose first run has no usable start. A number there could turn a long run into `<1 min`. The run's number stays. |
| No run in the store | `No runs yet`, over `Play a scenario in KovaaK's and your latest run will show here.` | A title and one sentence, as the chart's empty states. |

Accuracy is shown to the whole percent on the card and in the list. The
chart's hover keeps its two decimals.

**The chart**

| Where | String | Why |
|---|---|---|
| Mode control | `Score vs Run`, `Score vs Time`, `Score vs Sensitivity` | "Score vs Run" names what the axis counts, beside two names that already do. Title Case, as named chart modes. |
| Mode control, accessible name | `Chart mode` | Plain. |
| Range, in runs | `Last 50 runs`, `Last 100 runs`, `Last 200 runs`, `All runs` | The unit is in the option, so the select needs no visible label. |
| Range, in days | `Last 7 days`, `Last 14 days`, `Last 30 days`, `Last 90 days`, `Last 12 months`, `All time` | The same. |
| Range, accessible name | `Range` | Plain. |
| Plot title | `{scenario}` | The maintainer's answer on the title. |
| Axis title, Score vs Run | `Run` | Beside `Date` and `Sensitivity`, which stay. |
| Empty state, the two day-based modes | `No runs in this range`, over `Choose a longer range or play more runs.` | Was "No runs in this date range" and "Choose an older date or play more runs." There is no date to choose. |
| Empty state, an unexpected mode | `Unsupported graph option`, over `Choose <b>Score vs Run</b>, <b>Score vs Time</b>, or <b>Score vs Sensitivity</b>.` | Names three modes. |

**The run list**

| Where | String | Why |
|---|---|---|
| Heading line | `{scenario} · {n} runs`, or `{scenario} · 1 run` | Says what the list is filtered to. The list has no name of its own. Singular where the count is one. |
| Buttons | `Expand all`, `Collapse all` | Sentence case. One button, reading what a click would do. |
| Button and menu | `Columns` | The shared menu's own label. |
| Column headers | `#`, `Time`, `Score`, `Accuracy`, `Shots Fired`, `Sensitivity` | Title Case, as grid headers. The Columns menu's two checkboxes carry the headers they show. |
| The marks column, accessible name | `Marks` | It has no visible header. |
| A session row's name | `Oct 4, 9:45 PM`, or `Dec 30, 2025, 9:45 PM` in an earlier year | The session's start. |
| Badge | `In progress` | A status, in sentence case. |
| A session row, right side | `{n} of {m} runs`, such as `7 of 47 runs`, `1 of 1 run` | This scenario's runs out of the session's. |
| The first row, right side | `{length} · {n} of {m} runs`, such as `1 hr 6 min · 7 of 47 runs` | The session being played is the one whose length matters at a glance. When the selected scenario has no run in it, the row reads `1 hr 6 min · 0 of 47 runs`, on purpose: it gives the session's size and says none of it was on this scenario. |
| The first row's length, hover | `The length runs from the first run to the last run. It doesn't count the time since your last run.` | Says why the figure stands still between runs. |
| The first row, opened, scenario not played in it | `Not played in this session` | "This" is the row's session, in progress or ended. |
| Divider | `{n} runs on {k} other scenarios`, or `1 run on 1 other scenario` | Says what happened between two rows. |
| Date header | `Oct 12`, or `Jan 1, 2027` in another year than this one | Names the date of the runs under it, only in a session that crosses midnight. The year follows the session name's rule. |
| A run's time | `10:50 PM` | The session's name carries the date, or a date header does where the session crosses midnight. No seconds: the chart's hover stays the one place that keeps them. |
| A check, hover and accessible name | `Threshold passed` | The verdict's own words. |
| A star, hover and accessible name | `New PB` | The legend's entry. |
| No check, a judged run, hover and accessible text | `Below threshold` | The verdict's own words. |
| No check, the percentage is empty, hover and accessible text | `Not judged. No score threshold percentage is set.` | Says the checks are off, and why. It is the reason given when more than one applies. |
| No check, a first run, hover and accessible text | `Not judged. A scenario's first run, and the first run at a new sensitivity, aren't judged against the score threshold.` | Unknown isn't a miss, and it says why. It names the threshold and not the personal best, because such a run can still be a new PB and carry a star in the same cell. |
| No check, a previous best of zero or less, hover and accessible text | `Not judged. Your personal best before this run was zero or less, so there is no percentage to judge by.` | Rare, and unexplained otherwise. It applies only where the comparison is by score. |
| Button | `Show older sessions` | Loads 30 more. |
| The grid, accessible name | `Runs of {scenario}, by session` | Plain. |
| No scenario selected | `No scenario selected` | The chart's own empty-state title. |
| No run in the store | `No runs yet` | The card's title. |

**Help text that changes**

| Where | String | Why |
|---|---|---|
| Follow newly played scenario, help | `Automatically selects the scenario you just played when a new run is detected. If the **Playlist filter** doesn't list that scenario, the filter is cleared.` | R7. The second sentence is new. It is the one place that explains a filter that emptied itself. |
| Score threshold percentage, help, last sentence | `A run is judged against the personal best you had before the run.` | Was "Notifications judge a run against the personal best you had before the run." The check and the card judge too. The ratified Run toasts proposal words the sentence the same way, and it is true whichever change lands first. |

**Kept as today, word for word**

- The top row: `Playlist filter`, `Open scenario table`, `Selected scenario`
  with its placeholder `Select a scenario`, `Follow newly played scenario`,
  and `Last played:`, `Number of runs:`, `Position:` with every Position
  string in the rank spec.
- The chart: `Chart options`, the legend entries `Run data point` and
  `New PB`, the annotations `PB score ({value})` and
  `Score threshold ({value})`, the hover's labels, and the empty states
  `No scenario selected` and `No local runs found` with their messages.
- Chart options: its four group headings, every control label and
  placeholder, and every help text but the two above. That includes the
  **Score threshold verdict** and **Run notifications** switches and their
  help, until the Run toasts change takes both out of the panel.
- Home: the stats-folder hint's two sentences, and the setup card's three
  states with their buttons and fine print.

**Removed:** `Top N scores` and its help text, `Oldest date to consider`,
the legend entry and hover label `Average score`, and the empty state
`Graph settings incomplete` with its message.

### Terms

Each entry is written as [docs/glossary.md](../glossary.md) would hold it.
The PR that makes the page public moves them in.

New entries:

- **Run History.** The page that shows one scenario's runs: a chart of its
  scores, a list of its runs grouped by session, and the latest run played.
  With Follow on, it follows the scenario being played.
  - In code: `run_history`.
  - Not Home, the page the app opens on.
- **Score vs Run.** The chart mode that plots a scenario's runs in the order
  they were played, evenly spaced, so a busy day and a quiet month each take
  the room their runs need. Score vs Time plots the same runs by when they
  were played.
- **Latest-run card.** The panel at the top of Run History that reports the
  last run played, on whatever scenario, with its verdict.
  - On screen it has no title. Its first line starts "Latest run".

Entries the same PR corrects, because the change makes them untrue:

- **Top-N placement** says the same N bounds what the chart plots. It no
  longer does. The Run toasts proposal removes the entry.
- **New PB** names the chart legend as where it shows. The list and the card
  show it too.
- **Score threshold** points at the notifications spec for how a run is
  judged. The page's spec holds the rule for a check.
- **Sensitivity** says a scenario's runs are compared within one sensitivity
  on the Score vs Sensitivity chart and in top-N placement.

The glossary already holds Session, Session length, Run length, and Visit,
from the Sessions work.

### The contract for going public

The new page replaces the old one when this holds: **every statement in
[docs/specs/scenario_performance.md](../specs/scenario_performance.md) on
`main` at `4272fbb` is true of the new page, except the rows below.**

The rows come from a keep, change, or drop list the maintainer answered on
2026-10-10. It has one row per statement in that spec, 121 of them, and 23
more for what other pages and the user-facing docs rely on: 99 keep, 32
change, 13 drop. The 45 changed and dropped rows are carried here in full,
because the list is untracked. A row's id is the list's own with `L-` in
front, so `L-R4` can't be read as decision row R4.

Seven of the 45 were the Run toasts proposal's to decide. It was ratified on
2026-10-11, and those rows say what it settled. Each stays as it is today
until that proposal's change lands, which is with this page going public or
after.

**The 32 changes**

| Row | The old page | Version 1 |
|---|---|---|
| L-A1 | The spec's opening summary describes the kept runs plotted over sensitivity or time | Rewritten for every run, three modes, the run list, and the card |
| L-I2 | The product name is "Scenario Performance" | "Run History" (R1) |
| L-I3 | The name is labels only. The module and route keep their old names | A new module at a new address (R2). `home.py` keeps `/` and becomes Home |
| L-I6 | Two chart modes keep their capitals as names | "Score vs Run" is a third. `AGENTS.md` copy rule 3 lists the modes and gains it |
| L-C9 | The "Oldest date to consider" date picker | A range select in the chart's header. A start date of the player's own choosing is gone |
| L-C10 | The date defaults to January 1 of the current year | The last 100 runs, or the last 90 days, until the browser remembers a choice |
| L-C12 | A radio offers two modes, in the controls row | Three modes, in the chart's header |
| L-C13 | The chart opens on Score vs Sensitivity | It opens on Score vs Run |
| L-C17 | The oldest date is remembered | The range is, one for runs and one for days |
| L-C20 | The row measures the content area, and the dropdowns narrow from 400 px toward 200 px before it wraps | The row is rebuilt around the stats and the card. It still measures the content area. The widths are new |
| L-G1 | Each kept run is a point | Every run in the range is. The legend entry is unchanged |
| L-G4 | The date range includes the selected date | A range is a count of runs, or a number of calendar dates that counts today |
| L-G5 | The plot title reads `{scenario} (updated: {timestamp})` | `{scenario}` |
| L-G8 | A new PB that Top N or the date leaves off the chart gets no star and still counts | Only the range can leave one off |
| L-G19 | Runs at one position share one hover, and a new PB is ordered last where it shares a position with a same-day tie | The rule is kept, for a rarer case. In Score vs Time only runs that ended in the same second with the same score share a position, and a new PB is still ordered last among them. Score vs Run gives every run its own position. Score vs Sensitivity still shares positions and has no stars |
| L-G24 | The rank lines lag a change of playlist until the next rebuild | They redraw at once |
| L-G30 | "No runs in this date range" | Reworded for a range, and reachable only in the two day-based modes |
| L-G31 | "Unsupported graph option" names two modes | It names three |
| L-O4 | The panel stacks above the chart when the chart row is narrower than 62em | A new threshold, on the chart's own area (see Narrow windows) |
| L-O5 | Four groups with their defaults, the verdict switch among them | Unchanged here. **Run toasts, ratified:** the verdict switch is dropped (T3) and the Notifications group moves to the Settings page, which leaves three groups |
| L-O8 | The percentage's help text says notifications judge a run | It says a run is judged (see Copy) |
| L-O10 | The page hosts two notification switches | Unchanged here. **Run toasts, ratified:** none stays on the page. The verdict switch is dropped (T3), and **Run notifications** moves to the Settings page |
| L-R4 | The chart rebuilds on a Chart options control, a scenario change, and the date and mode controls | The mode, the two ranges, and the Playlist filter. Top N and the date are gone |
| L-X4 | The navbar's first entry is "Scenario Performance", and it and the header title lead to `/` | Home, then Run History. The header title leads to Home |
| L-X5 | Run toasts are built by this page, so they show only while it is open | **Run toasts, ratified (T1):** the app shell builds a plain toast, on every page. Until that lands the new page builds today's toasts |
| L-X6b | A run that is neither judged nor placed gets no toast | **Run toasts, ratified (T1):** a new run gets the plain toast. A run the celebration announces keeps the celebration alone, and runs detected together share one toast |
| L-X7 | A run is judged against the PB it was chasing, and the toast words the result | The rule stays and also decides the check and the card's badge. The toast stops wording it under T1, ratified |
| L-X14 | The user guide names the page five times | The name changes in all five. One is the sentence about the Open scenario table link, which the list holds as X15, a keep row: its statement holds and only the page's name in it changes. The pace paragraph gains the check and the card |
| L-X17 | The README's first screenshot is this page | Retaken |
| L-X18 | The README's Features line names two chart modes | It gains Score vs Run. The run list may add one line, no more |
| L-X19 | The README's install steps 3 and 4 name the page that shows the setup card | They name Home |
| L-X20 | The README says a toast compares a run with the personal best | **Run toasts, ratified.** True until its change lands |

**The 13 drops**

| Row | The old page | Why dropping it is safe |
|---|---|---|
| L-C8 | The "Top N scores" input | Every run is plotted, so N has nothing to trim (R5) |
| L-C19 | Its help tooltip, the one place that says a top-N run earns a notification | Goes with L-C8. The maintainer: "I think this is probably fine." |
| L-G2 | The "Average score" line | R5. No summary line in version 1 |
| L-G3 | The top N scores are kept per sensitivity, or per day | R5 |
| L-G9 | A later run the same day with the same score has no star | It can't arise. No run is left out, so a tie is never plotted without the new PB it tied |
| L-G17 | The Average score hover | Goes with L-G2 |
| L-G28 | The empty state "Graph settings incomplete" | Both controls it names are gone, and a range can't be empty |
| L-G34 | The Average score line's fixed color | Goes with L-G2 |
| L-O7 | The Top N help's "or per day in Score vs Time" | Goes with L-C8 |
| L-T2 | The watchdog's per-run lines in the debug log, judged at a fixed 95% | The run list is the record they stood in for. Dropped when the page goes public |
| L-X6 | Top-N placement in a run toast | **Run toasts, ratified (T2):** retired. If this page goes public first, N is fixed at 5 until then |
| L-X9b | The "Score threshold verdict" switch | **Run toasts, ratified (T3):** dropped |
| L-X28 | What each browser remembers for the kept controls | A one-time reset, accepted (see Remembered controls) |

**Rows the list marks keep that R2 and R7 change.** The list was answered
before Home was proposed.

| Row | The old page | Version 1 |
|---|---|---|
| L-I1 | The page is at `/`, and `/home` and `/index` redirect to it | Run History is at `/run-history`. `/` and both redirects are Home's (R2) |
| L-I10 | `?scenario=` alone keeps the filter, and a scenario the filter doesn't list is dropped | The filter is cleared and the scenario selected (R7) |
| L-I13 | The navbar link and the header title lead to the page with no parameters | The navbar link does. The header title leads to Home (R2) |
| L-R1 | The page lands on the scenario just played when Follow is on | It also clears a filter that doesn't list that scenario (R7) |
| L-R6, L-X10 | Failed run imports and startup playlist warnings reach the screen only on this page | On Home and on Run History (R2) |
| L-X1 | A scenario name in a playlist's table links to `/?playlist_code=...&scenario=...` | To `/run-history?...` (R2) |
| L-X13 | The settings spec says the setup card and the hint belong to this page's spec | To Home's (R2) |
| L-H1 to L-H9 | The setup card and the stats-folder hint show above the controls row | Every statement holds on Home. The hint and the card's two yellow states also show on Run History. The account offer is Home's alone (R2) |

The other 82 kept rows hold as the spec states them, read against the new
layout.

### Decisions this changes

The PR that makes the page public keeps each entry and adds a dated
"Superseded in part" note, as the 2026-09-14 copy entry did to the naming
entry. It erases nothing.

| Entry | What changes | What stands |
|---|---|---|
| [2026-08-09, the naming entry](../decision_log.md#2026-08-09-the-graph-page-is-scenario-performance-its-panel-is-chart-options) | The page's name (R1). "The route restructure is deferred" is resolved, with `/run-history` in place of `/scenario` (R2). "Run History composes into this column" is answered with a second column (R3) | Chart options' name, Settings' name, no exclusive tenancy, and the rule that copy is checked against the app's own words |
| [2026-08-09, the panel entry](../decision_log.md#2026-08-09-chart-options-live-in-a-collapsible-panel-beside-the-graph) | The 62em threshold. "Ids and defaults survive verbatim", set aside once | The panel beside the chart, the container query, the clipping row, `.home-graph` as the resize hook, and the toggle's guard |
| [2026-10-05, the stars](../decision_log.md#2026-10-05-the-score-vs-time-chart-marks-each-new-pb-with-a-star) | "Only Score vs Time is marked" (R6). The clauses about Top N, the oldest date, the kept tie, and the Average score trace stop applying (R5). The hover order at a shared position narrows from a same-day tie to a same-second one | What a new PB is, no stars on Score vs Sensitivity, a new PB ordered last among points at one position, the look, Point size, and no control |
| [2026-09-19, query parameters](../decision_log.md#2026-09-19-a-query-parameter-selects-a-control-it-does-not-suspend-its-memory) | "`?scenario=` alone leaves the playlist filter on the restored value" gains one exception (R7) | The invariant and its corollary, which bind the new page. An unknown playlist code still clears the filter, and the URL is still not rewritten |
| [2026-07-11, timestamps](../decision_log.md#2026-07-11-humanize-the-absolute-timestamp-format) | The plot title's `updated:` use ends. Session names and the card drop this year's year, and a run row shows a time of day alone | The format and its rules |
| [2026-10-05, pace](../decision_log.md#2026-10-05-time-scored-scenarios-are-measured-by-pace) | The watchdog's session lines leave its list of surfaces. The check and the card join it, and a past run is judged under its own version, not the newest run's | The pace rule |
| [2026-09-12, Share chart](../decision_log.md#2026-09-12-charts-keep-plotlyjs-4s-share-chart-button) | The figure shared holds every run in the range and no Average score line | The button stays |

The Run toasts proposal carries the entries its own rows change.

### Earlier positions, kept for the record

This file replaces a proposal written when the feature was far off. That
text described two views: (1) the current session across scenarios, and (2)
one scenario's full history. Two of its durable decisions were already
marked superseded. They stay marked here, with their text, which answers the
connector's
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
  - **Superseded** by row D4 of
    [PR #327](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/327):
    sessions come before either view, so "it needs no sessionization" no
    longer sets the order. Which view ships first was left open for the
    rewrite to decide.
  - **Decided here, if this proposal is ratified:** view (2) ships first, on
    sessions, as version 1's run list. View (1) is the All scenarios
    proposal's.

The old file's three positions on sessions are not superseded: gap-based
sessions, a fixed gap, and no SQLite migration. The sessions decision
([2026-10-11](../decision_log.md#2026-10-11-a-session-ends-after-a-break-of-more-than-30-minutes))
carries them forward. Its open question about the navigation surface is
answered by R3.

### Optional, beyond the outline

None of these is proposed. Each is a small addition a reviewer or the
maintainer may want, with what it would cost.

- **Home forwards a `/?scenario=` or `/?playlist_code=` link to Run
  History.** Old bookmarks keep working. It is forwarding logic on Home,
  which the maintainer declined in general, though for a different reason.
- **The NVDA walk repeated on the built list before the page goes public.**
  It would check the real thing and not a prototype. The walk's scripts and
  an unpacked NVDA are already on the maintainer's machine. It takes over
  the foreground window while it runs.
- **The Score threshold percentage stops at 100.** Above 100 every check
  sits on a run that is also a new PB. The spec allows a goal above 100
  today, so this would remove something a user may have set.
- **Home's stats line updates when a run lands.** One small callback on the
  shell's batch. Without it the count is as old as the page load.
- **The two queue flushes move to the app shell,** so failed imports and
  startup warnings reach every page. It changes the notifications spec's
  delivery rule and is a change of its own.

## Delivery plan

Four implementation PRs. The page is hidden until the last. This is intent,
not a contract: a boundary that moves is noted in that PR's description.

Each hidden PR names the contract rows it makes true, and the maintainer
tries it in their own Firefox at `/run-history` before it merges. The page
is registered at its final address from the first PR, with no navbar entry
and nothing linking to it, so nothing moves when it goes public.

1. **The skeleton, the moved top row, and the rebuilt chart.** The new
   module and its address. The top row from the groundwork's shared modules,
   with the new page's ids. The chart: three modes, the two ranges, every
   run, stars on Score vs Run, the title, and rank lines that redraw at
   once. Chart options. Deep links, R7, and a layout that accepts a
   parameter it doesn't name. The stats-folder hint and the setup card's two
   yellow states.
   - Needs this proposal ratified. The three groundwork PRs it also needed
     have merged.
   - Measures and reports: the chart's box at 1400, 1600, and 1920 px with
     Chart options open and closed, and the zoom fit on Score vs Run's axis.
   - Recommended: `claude-opus-5-5` at xhigh. It carries the persistence
     rules of 2026-09-19 onto a new page and sets the layout every later PR
     sits in.
2. **The run list.** The row model, the grid with its nine items, the
   Columns menu, Expand all, the pinned session, the divider, 30 sessions at
   a time, the marks, shots fired on the run record, the list's narrow rule,
   and the percentage field's change.
   - Needs PR 1. The Sessions implementation it also needed has merged.
   - Reports the accessibility tree and a scripted keyboard walk, as the
     trial did.
   - Recommended: `claude-opus-5-5` at xhigh.
3. **The latest-run card.** The card in every state, the ring on the latest
   point, and the row highlight.
   - Needs PR 1. The Sessions implementation has merged. It can run beside
     PR 2. The row highlight lands with whichever merges second.
   - Recommended: `claude-opus-5-5` at high.
4. **Going public.** `home.py` shrinks into Home with its stats line. The
   navbar. The Playlists links. The watchdog's per-run log lines and the
   comment that points at this file. Then the docs, by the
   [Shipping a proposal](../../AGENTS.md#shipping-a-proposal-docs-definition-of-done)
   checklist: the decision-log entries and the supersession notes above, the
   page's spec rewritten and renamed for the new page, a short spec for
   Home, the glossary, `AGENTS.md` copy rule 3, the README and its
   screenshot, the user guide, `architecture.md`, the roadmap, `product.md`,
   and this file deleted with every pointer to it fixed. One line in the
   release notes about the reset.
   - Needs PRs 1 to 3.
   - Recommended: `claude-opus-5-5` at high.

PRs 2 and 3 each depend only on PR 1. Whichever of the two merges first also
rewrites the "Not on screen yet" section of the
[sessions spec](../specs/sessions.md), which goes untrue once a page draws a
session. The Run toasts PR lands with PR 4 or after it.

### Fallbacks

- **The Run toasts change is not built when PR 4 is ready.** Its proposal is
  ratified, so this is now only about build order. The page goes public with
  today's toast, built by Run History as the old page builds it, with N
  fixed at 5 and no control. Nothing in this proposal waits on that change:
  the marks are never gated by a switch, and both notification switches are
  carried unchanged. The Run toasts proposal names the cost. A browser's
  stored "off" for **Run notifications** is lost once whenever its change
  lands. Landing with PR 4, that is part of the one-time reset. Landing
  later, it is a second reset, for that one switch.
- **R4 stalls review.** The run list and the card split into a proposal of
  their own, which depends on this one and never the reverse. That lets the
  rest be ratified and its first PR start. It changes nothing about what
  goes public: the old page stays public until the list and the card have
  shipped too. Going public with the chart alone would drop the surfaces
  that hold a run's verdict, which the ratified Run toasts proposal depends
  on. That would need a direction decision of its own.
- **The built list proves unusable with a screen reader.** NVDA was run on
  the prototypes, and Narrator and JAWS were not run at all. If the built
  list fails where the prototype passed, the cost is the list's last step,
  about 370 to 500 lines of script.

## Out of scope

Each with where it is tracked. The local notes are under `ignore/` in the
maintainer's main checkout.

- **All scenarios:** the view switch, the "7 of 47 runs" jump, **Show all
  runs**, and Median and best. Its own proposal, written once this one
  settles the list's library. Rows A1 to A3.
- **The run toast,** and the **Run notifications** switch's move to the
  Settings page. The [Run toasts proposal](run_toasts_proposal.md), rows T1
  to T3, ratified.
- **What a session is.** Ratified and built. The rules are in the
  [sessions spec](../specs/sessions.md).
- **The typical score, a median line, the card's two dashed readouts, and
  the trend verdict.** Later proposals. The roadmap's Future list holds the
  trend verdict.
- **Score vs Sensitivity's redesign.**
  `ignore/prompts/icebox/score-vs-sensitivity-redesign-prompt.md`.
- **Warm-up runs,** and four ideas from the session-gap discussion: a pause
  divider, warm-up keyed on a pause, "in progress" on its own timer, and a
  session as one game launch. `ignore/design-notes/session-gap.md`.
- **The Overview page.** The roadmap's Future list. Home is its placeholder.
- **Chart options reworked,** such as a strip under the chart's header.
  After shipping.
- **The 2 px nudge in Score vs Time.** See The chart.
- **Reset files, and Statistics Export set to Always.**
  `ignore/design-notes/stats-export-always.md`, parked.
- **Stray CSV copies in the stats folder.**
  `ignore/prompts/ignore-stray-stats-csvs-prompt.md`.
- **The personal best celebration.** It stays as it is. The maintainer's
  later idea, playing it only on first opening Run History, is not this
  work.
- **Run detail and a per-bot breakdown, a Sessions navbar entry, month
  dividers, a PB link from Scenario Stats, a chart point that opens its row,
  seconds on a row's time, remembered open rows, a phone design, the
  two-tab model, and the gap as a setting.**
- **The principle "keep related information together, and link to what
  can't be kept together".** The maintainer wants it recorded. A docs change
  of its own.
- **The Aim Training Journey page.**

## Testing

- **The row model,** as a pure function over plain run records: which
  sessions are listed, the pinned session with and without runs of the
  scenario, per-session run numbers, a divider's two counts, 30 sessions and
  the next 30, and which rows a new run forces open. Also a session that
  crosses midnight and one that crosses a year, each with a header per
  date, and a header and a divider between the same two runs.
- **The marks,** on the maintainer's example: runs A to E at 90, 99, and 110
  percent, an empty percentage, the percentage cleared and then restored,
  a scenario's first run, the first run at a new sensitivity, a new PB at
  a new sensitivity, which has its star and no check, a run that is not a
  new PB against a previous best of zero, with the reason each blank cell
  gives, a time-scored scenario judged by pace, and a run on an
  older version of a scenario. The mark on a scenario's newest run agrees
  with the toast's verdict on it, and every star agrees with the chart's.
  A replay on real stats and performance files: an old run that missed by
  pace keeps that verdict after a run on a newer version lands, and a run
  played before its version could be recognized turns to pace once, when
  a file of that version first answers.
- **The chart's queries and figures:** every run in each range, the range's
  midnight edge, stars in Score vs Run and Score vs Time and none in Score
  vs Sensitivity, no Average score trace, the title, and each empty state.
  Also two runs that ended in the same second with the same score, one of
  them a new PB, handed over in both orders: the new PB is last in the run
  trace either way.
- **The card,** in each state in the Copy block, with the toast's two caps.
  Also a visit whose first run has no usable start, which reads as time
  unknown and never as a number.
- **Deep links and R7:** each combination of the two parameters against a
  filter that lists the scenario and one that doesn't, with Follow on and
  off. The structural test from the 2026-09-19 entry, which fails when a
  callback's inputs are all written only on some visits, is carried to the
  new page. The browser check asserts the dropdown's visible text as well
  as its value: the two can disagree for a round trip when the scenario
  lands before the cleared filter's list does, and a test on the value
  alone passes through that.
- **Home:** the stats line with many runs, one run, and none, and its
  absence with no stats folder. On Run History, the hint and the card's two
  yellow states, and no account offer. The hint and the card in each state, by the
  tests that cover them today.
- **Layout tests** in the style of the existing ones: the hidden page has no
  navbar entry, then Home and Run History have theirs.
- **The kept blocks keep their tests,** which the groundwork moves with
  them.
- **The script is not run by CI,** as no script in the repository is. Its
  source is pinned by text, as `tests/test_home_layout.py` pins
  `assets/homeGraphResize.js`.
- **In a browser, by each PR.** The trial's scripts are the starting point.
  They already assert the click targets, alignment, the keyboard walk, and
  what survives a run landing.
  - PR 1: the measurements above, a run landing with no reload, and both
    pages open in turn.
  - PR 2: the nine grid items, light and dark, the narrow layouts, and a
    run landing with rows open and with focus in a run row, which must
    stay on the same run.
  - PR 4: every link, a launch, and a browser that holds the old page's
    remembered values.
- **The maintainer's own Firefox,** at the hidden address, before each
  merge.
- **The docs test** holds this file's sections and its links.
