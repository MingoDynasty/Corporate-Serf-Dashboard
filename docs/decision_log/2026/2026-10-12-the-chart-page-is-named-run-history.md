# 2026-10-12: The Chart Page Is Named Run History

Status: Accepted

The page that charts a scenario's scores is now called Run History, in the
navbar, on the page, and in the browser tab. It used to be called Scenario
Performance, which named a chart, and the page now also holds a list of every
run and a card for the latest one. The new name is the one the work had
carried since it was planned. A user sees the new name everywhere in the app,
and the old one survives only in the history of earlier decisions.

**Rulings.** By the maintainer, 2026-10-12, on
[PR #356](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/356):
"I ratify the proposal." That settled the proposal's seven rows, R1 to R7,
each as recommended, and the author-owned design with them. Both review seats
had endorsed all seven. This entry is row R1. Before the ratification, on
2026-10-10, the maintainer on reversing the earlier naming ruling: "I agree
to reverse this decision." What the page does today is in
[run_history.md](../../specs/run_history.md), and the term is in the
[glossary](../../glossary.md). This entry holds the reasons, the names set
aside, and why the page exists.

**R1, the name.** The navbar link, the page name, and the browser tab read
"Run History". This reverses one of the four rulings of the
[2026-08-09 naming entry](2026-08-09-the-graph-page-is-scenario-performance-its-panel-is-chart-options.md),
"The graph page's product name is 'Scenario Performance'". The other three
stand: the panel is Chart options, Settings keeps its name, and the panel's
column claims no exclusive tenancy of the page's right side. So does the rule
that entry carries, that proposed copy is checked against the app's own
words.

- **The page stopped being only a chart.** It gained a list of every run and
  a card for the latest one. "Scenario Performance" names the chart alone.
- **It is the name the work already had.** The roadmap called the milestone
  Run history from the time it was planned, and the ratified run toast's link
  reads "Open in Run History".
- **The reasoning of 2026-08-09 still holds.** That entry gave the page a
  product name of its own, apart from its place as the page the app opens on.
  This row moves the name. The address is a separate row, in
  [its own entry](2026-10-12-run-history-has-its-own-address-and-the-landing-address-is-home.md).

**Names considered and not taken.**

- **"Runs".** Shorter, but it reads as the list alone, or as a count.
- **"Scenarios",** which `gpt-6-astra` suggested. The roadmap's Future list
  already holds a Scenarios page for scenario-first navigation.
- **Keeping "Scenario Performance".** Nothing would have been renamed. The
  page's largest new part would have had no name pointing at it, and the run
  toast's link, ratified as "Open in Run History", would have had to be
  worded again.

**What it cost.** A rename. "Scenario Performance" appeared on 75 lines in 20
tracked files on `main` at `4272fbb`. 24 of those lines are in the decision
log, where history keeps the old name. In code the page is `run_history`.

**Why the page exists.** The old page showed a finished run in three ways,
and none of them lasted:

- **A point on the chart,** if the run was among the top N scores at its
  sensitivity, or of its day in Score vs Time. N defaulted to 5.
- **A toast,** when the run passed or missed the score threshold or placed
  in the top N at its sensitivity. It was on screen for a few seconds.
- **Lines in the debug log.** The watchdog, the thread that imports each new
  stats file, logged every run's distance from the PB and whether it passed
  a fixed 95%. The log is developer-facing.

So the app could not answer what a player asks between runs: what did I score
on the runs just before this one, and how many have I played this session.
The maintainer, in a brainstorm note of 2026-09-28 that
[PR #351](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/351)
quotes:

> Most common use case is looking at a scenarios run history and using that
> data to help influence the next run. But I also want to understand where
> the run fits into a session.

**Version 1 is the smallest page worth making public.** Run history and
sessions was the roadmap's only Upcoming milestone. It was first written as
one proposal, PR #351, whose design a two-day discussion then moved away
from. The maintainer on 2026-10-10: "One of my main concerns about the Run
History proposal is trying to ship too many things at once." The work was
split into five pieces, and the maintainer agreed the split that day: "Merged
breakdown is a go." That agreed the outline and ratified no row. The pieces:
three refactor PRs with no proposal, which moved the old page's kept blocks
into modules two pages can import, then Sessions, Run toasts, this page as
piece 4, and All scenarios, a later proposal. On the page's size, the
maintainer: "I want to ship the MVP version of the Run History page first;
additional functionality can come later unless it blocks version 1."

Version 1 has four parts: the rebuilt chart, the run list for the selected
scenario, the latest-run card, and the old page's kept parts. Two of them
could not wait for a later release:

- **The chart changes.** A list of every run beside a chart of the top N
  would contradict each other.
- **The card.** Once the run toast goes plain, under the
  [Run toasts proposal](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/blob/2c5c072d0670c7c6d4873eb9e77f676dca1f6d43/docs/proposals/run_toasts_proposal.md), the card is
  the only place a run's percentage of the PB appears.

**Decisions the page was held to.** The proposal reopened none of these:

- The three skill-judgment principles of
  [2026-10-04](2026-10-04-skill-is-judged-by-the-typical-run-with-honest-uncertainty-in-verdicts-not-advice.md),
  and its row D4, that sessions come before the history views. The check and
  the star the page draws are verdicts against a bar the player set or a
  record they hold. The page gives no advice.
- What a session is, and when one is in progress
  ([2026-10-11](2026-10-11-a-session-ends-after-a-break-of-more-than-30-minutes.md)).
  That entry's row S4 took the typical score out of this milestone.
- What a new PB is
  ([2026-10-05](2026-10-05-the-score-vs-time-chart-marks-each-new-pb-with-a-star.md)),
  and pace on a time-scored scenario
  ([2026-10-05](2026-10-05-time-scored-scenarios-are-measured-by-pace.md)).
- One active tab is the supported way to use the app
  ([2026-07-06](2026-07-06-coalesce-pending-home-run-events.md)). The
  maintainer on 2026-10-07: "Keep the one-active-tab model as it is."
- The two rules for a remembered control
  ([2026-09-19](2026-09-19-a-query-parameter-selects-a-control-it-does-not-suspend-its-memory.md)):
  its layout default never varies per visit, and a callback that writes it
  only on some visits must not starve the callbacks that depend on it.
- The run toast, rows T1 to T3 of the Run toasts proposal, ratified on
  2026-10-11. Those rows were ratified leaning on three rows here: this
  page's name, its address, and the rule for a link to a scenario the
  Playlist filter does not list. That change had not been built when the
  page went public, so the page carries the old toast until it lands.

**The page's other decisions.** Each row of the proposal, and each
author-owned part of its design that is a decision, has an entry:

- [Run History Has Its Own Address, And The Landing Address Is Home](2026-10-12-run-history-has-its-own-address-and-the-landing-address-is-home.md),
  with how the page was built and made public.
- [The Run List Is A Second Column Beside The Chart](2026-10-12-the-run-list-is-a-second-column-beside-the-chart.md),
  with what the list shows.
- [The Run List Is Built On AG Grid Community, And NVDA Is Run On The Built List](2026-10-12-the-run-list-is-built-on-ag-grid-community-and-nvda-is-run-on-the-built-list.md).
- [The Run History Chart Plots Every Run And Draws No Summary Line](2026-10-12-the-run-history-chart-plots-every-run-and-draws-no-summary-line.md).
- [Score vs Run Stars Each New PB](2026-10-12-score-vs-run-stars-each-new-pb.md).
- [Follow And A Scenario Link Clear A Playlist Filter That Does Not List The Scenario](2026-10-12-follow-and-a-scenario-link-clear-a-playlist-filter-that-does-not-list-the-scenario.md).
- [A Past Run's Check Is Judged Against The PB It Was Chasing, Under Its Own Version](2026-10-12-a-past-runs-check-is-judged-against-the-pb-it-was-chasing-under-its-own-version.md),
  with the latest-run card.
- [Run History Keeps Its Own Control Ids, So Every Browser Saw The Defaults Once](2026-10-12-run-history-keeps-its-own-control-ids-so-every-browser-saw-the-defaults-once.md).
- [A Measured Time Rounds To The Nearest Minute](2026-10-13-a-measured-time-rounds-to-the-nearest-minute.md),
  ruled a day later.

**Superseded in part (2026-10-13).** The run toast has gone plain. So "once
the run toast goes plain" is now: the latest-run card is the only place a
run's percentage of the PB appears. See
[A Run Toast Is Plain And Shows On Every Page](2026-10-13-a-run-toast-is-plain-and-shows-on-every-page.md).

Proposed in
[PR #356](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/356),
which merged as `a65f72d`. The page was built hidden in
[#370](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/370),
[#371](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/371), and
[#372](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/372),
and took the name in
[#373](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/373),
which made it public. The proposal file,
`docs/proposals/run_history_proposal.md`, is deleted, and git history keeps
it.
