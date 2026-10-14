# 2026-10-12: Score vs Run Stars Each New PB

Status: Accepted

The Score vs Run chart draws a gold star on each plotted run that was a new
personal best, as Score vs Time already did. Run History opens on Score vs
Run, so a fresh browser now sees stars at once, beside a run list that marks
the same runs. Score vs Sensitivity still has none, because stars along a
sensitivity axis have no order.

**Ruling.** By the maintainer, 2026-10-12, on
[PR #356](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/356):
"I ratify the proposal." This entry is row R6, ratified as recommended.
Before it, the maintainer, 2026-10-10, on stars in Score vs Run and Score vs
Time and not in Score vs Sensitivity: "Agreed." Built in
[#370](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/370).
The rule as the app applies it is in
[run_history.md](../../specs/run_history.md#the-chart).

**R6.** Score vs Run stars each plotted run that was a new PB, as Score vs
Time does. Score vs Sensitivity still has none. A new PB is a run whose
score is strictly above every earlier run of its scenario. This extends one
ruling of the
[2026-10-05 stars entry](2026-10-05-the-score-vs-time-chart-marks-each-new-pb-with-a-star.md),
"Only Score vs Time is marked", and changes nothing about which runs earn a
star.

- **That ruling's own reason covers it.** "Along the date axis the stars
  read left to right as the history of the PB, and along the sensitivity
  axis they have no order." Score vs Run is in play order too.
- **It answers a cost that ruling accepted.** "The chart opens on Score vs
  Sensitivity and remembers the choice per browser, so a fresh browser shows
  no stars until the reader switches." The new chart opens on Score vs Run.
- **The star in the list and the star on the chart are the same runs.** The
  list marks a new PB by the same rule, so the default mode should too.

**Stars are a smaller share of the points.** Under Top N scores of 5, 666 of
the year's 2,220 plotted points were stars (measured 2026-10-04). With every
run of the year plotted, about one point in five is: 691 new PBs against
3,272 runs, two counts taken a day apart, on the maintainer's history alone.

**Score vs Sensitivity stays unmarked** for the first of the 2026-10-05
ruling's two reasons, that stars have no order along that axis. The second,
that the chart kept only the top scores at each sensitivity, stopped applying
when the chart began to plot every run
([the chart's entry](2026-10-12-the-run-history-chart-plots-every-run-and-draws-no-summary-line.md)).

**What else of the 2026-10-05 entry moves,** all of it from plotting every
run:

- **Only the range can leave a new PB off the chart.** Top N and the oldest
  date used to as well. Such a run still counts in the comparison.
- **A tie is never plotted without the new PB it tied.** Under Top N the
  day's filter could drop a new PB and keep a later run with the same score,
  and that entry ruled the kept tie gets no star. No run is left out now, so
  the case can't arise.
- **The hover order at a shared position narrows from a same-day tie to a
  same-second one.** In Score vs Time only runs that ended in the same
  second with the same score share a position, and a new PB is still
  ordered last among them. Score vs Run gives every run its own position.
  Score vs Sensitivity still shares positions and has no stars.

What stands: what a new PB is, no stars on Score vs Sensitivity, a new PB
ordered last among points at one position, the look, Point size, and no
control.

**New PBs are judged in play order.** The rule's function is unchanged. The
chart hands it the scenario's runs in the order sessions are split in, so
the star lands on the same run of a same-second pair that the axis puts
first. The old page judged such a pair in the order its files were loaded.
This is PR #370's choice, and it keeps the ruled outcome.

**If the maintainer had kept stars to Score vs Time:** the page would open
on a chart with no stars beside a list that has them.

Proposed in
[PR #356](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/356),
which merged as `a65f72d`. Shipped in
[#370](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/370),
hidden, and made public in
[#373](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/373).
The proposal file, `docs/proposals/run_history_proposal.md`, is deleted, and
git history keeps it.
