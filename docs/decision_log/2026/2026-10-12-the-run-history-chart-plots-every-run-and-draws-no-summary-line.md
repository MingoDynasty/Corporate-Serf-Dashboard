# 2026-10-12: The Run History Chart Plots Every Run And Draws No Summary Line

Status: Accepted

The chart on Run History plots every run in its range, where the old chart
kept only the top few scores of each day or each sensitivity. A list of every
run beside a chart of the best few would have contradicted each other. The
two controls that trimmed the chart are gone with its Average score line, and
the chart opens on a new mode that spaces runs evenly in the order they were
played. Score vs Sensitivity now shows every run at each sensitivity with
nothing that sums one up, until that mode is redesigned.

**Rulings.** By the maintainer, 2026-10-12, on
[PR #356](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/356):
"I ratify the proposal." This entry is row R5, ratified as recommended, and
the author-owned design of the chart, which the ratification covered. Before
it, the maintainer, 2026-10-07: "ship Run History without the Median line",
and "Average score line - we'll drop this". The chart was built in
[#370](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/370) and
the ring on the latest run in
[#372](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/372).
What the chart does today is in
[run_history.md](../../specs/run_history.md#the-chart). This entry holds the
reasons, what was lost, and what the build added to the proposal's letter.

**R5, every run.** The chart plots every run in its range. The **Top N
scores** control, the **Oldest date to consider** picker, and the Average
score line are gone, and no mode draws a summary line. The old chart kept the
top N scores per sensitivity, or per day, and drew a line through each
group's average.

- **A list of every run beside a chart of the best few would contradict
  each other.** The row a player just watched land would have no point.
- **Top N hid the order of play.** Score vs Time kept each day's best and
  put them at one position, so it showed neither how a day went nor all of
  it.
- **The Average score line averaged what Top N kept.** On a busy day it was
  the average of that day's best, which the
  [2026-10-05 stars entry](2026-10-05-the-score-vs-time-chart-marks-each-new-pb-with-a-star.md)
  already notes.
- **A new summary line would be a second definition of the typical run.**
  The typical score left this milestone, by row S4 of the
  [2026-10-11 sessions entry](2026-10-11-a-session-ends-after-a-break-of-more-than-30-minutes.md).
  A median drawn now would have to agree with it later or be replaced.

**What is lost, and where it hurts most.**

- **Score vs Sensitivity lost both of its summaries.** Top N per sensitivity
  and the Average score line were how that chart compared one sensitivity
  with another. Without them it shows every run at each sensitivity and
  nothing that sums a sensitivity up. The maintainer, 2026-10-10: "In that
  case we may need to redesign that chart/feature", and "Score vs Sensitivity
  should not affect the launch. We can redesign it afterward." So that mode
  shipped as every run per sensitivity, and its redesign is a later piece of
  work.
- **What a player sees first there is overplotting.** Every run at a
  sensitivity shares one position along the axis, so a well-played scenario
  draws a dense vertical strip per sensitivity, and the spread inside a
  strip can't be read. The maintainer's largest scenario had 463 runs on
  2026-10-04. That is the first thing the redesign has to answer.
- **A start date of the player's own choosing.** The range is a choice from
  a list.
- **The Top N help tooltip,** the one place that said a top-N run earns a
  notification. The maintainer: "I think this is probably fine."
- **The empty state `Graph settings incomplete`.** Both controls it named
  are gone, and a range can't be empty.
- **The Average score line's legend entry, hover, and fixed color** went
  with the line.

Top N survives in one place for now. The run toast still places a run
against the top scores at its sensitivity, against a fixed 5 with no
control, until the
[Run toasts proposal](../../proposals/run_toasts_proposal.md)'s change
retires placement.

**If the maintainer had chosen otherwise.** With Top N and the Average score
line kept in Score vs Sensitivity alone, that mode keeps its comparison until
the redesign. The control, its help text, and an empty state survive for one
mode, and the chart disagrees with the list there. With a median line
shipped now, the page has a summary, and the later typical score has to
match it or replace it.

**Three modes.** Score vs Run, Score vs Time, and Score vs Sensitivity,
chosen in the chart's header. The old page had two, on a radio in its
controls row, and opened on Score vs Sensitivity.

- **Score vs Run is the default, and a new term.** It plots the scenario's
  runs in the order they were played, evenly spaced, so a busy day and a
  quiet month each take the room their runs need. It is the mode that shows
  every run of a session apart, which is why the page opens on it. A time
  axis bunches recent play: on Smoothsphere Viscose at All time, half of the
  61 runs sat in the right-hand 10% of a time axis, and in run order they
  spread evenly (the maintainer's folder, 2026-10-05).
- **The order is the one sessions are split in:** by when a run ended, with
  the sessions rule for runs that ended in the same second. So the chart and
  the list never disagree about which run came first.
- **Score vs Time plots each run at its own timestamp.** A day no longer
  shares one position. Two runs can still share one: a timestamp is in whole
  seconds, so runs that ended in the same second with the same score sit on
  one point. The chart keeps the rule for points at one position, that a new
  PB comes last among them in the run trace, so the hover shown under a star
  is the hover of the run that set the PB.
- **Score vs Sensitivity plots every run in the range at its sensitivity.**
- **The name "Score vs Run" names what the axis counts,** beside two names
  that already do. It keeps its capitals as a named chart mode, and copy
  rule 3 in `AGENTS.md` lists it with the other two.

**The Score vs Run axis, as built.** The proposal said the labels are dates,
one at the first run of a day, thinned so they don't collide. PR #370 chose
the rest.

- **A run's x value is its number in the scenario's whole history,** so a
  run keeps its place when the range changes. The axis title is `Run`.
- **The server writes the ticks:** a date at the first plotted run of each
  day, thinned from the newest back so the day being played always keeps its
  label. The label reads `Oct 12`, or `Dec 7, 2025` in another year than
  this one. The proposal gave no format, and this is its own shape for a
  date header in the list.
- **The labels are spaced for a plot 330 px wide.** The server never learns
  the chart's width, and 330 px is the plot in a 1600 px window with Chart
  options open. On a narrower plot plotly tilts them, as seen at 247 px.
- **Left as it is:** a zoomed chart can show few date labels, or none,
  because the labels are thinned once for the whole range. The hover still
  gives every run's timestamp. The first plotted day can also lose its label
  to the next day though there is room for both. Thinning in the browser
  would be the fix if it ever matters.
- **The zoom fit works on the numeric axis unchanged.** The proposal listed
  it as not checked, since Score vs Run is the first numeric axis the zoom
  script met. In PR #370 a drag across the run axis refit the score axis to
  the runs in view, in Edge and Firefox, and the script needed no change
  because it reads the axis through plotly's converters. The maintainer
  made the real double-click in Firefox by hand.
- **The figure is always drawn as SVG.** The new builders use `go.Scatter`
  directly, where `px.scatter` switches to WebGL above 1,000 points.

**Ranges.**

- **Score vs Run counts runs:** the last 50, 100, or 200, or all of them.
  **The other two modes count days:** the last 7, 14, 30, or 90 days, the
  last 12 months, or all time.
- **A range of N days is N calendar dates, counting today.** It starts at
  local midnight N minus 1 days before today. On October 11 the last 7 days
  are October 5 to 11. So the label and the chart agree, and a point leaves
  the chart at midnight and not in the middle of a day. The last 12 months
  are 365 days, counted the same way.
- **The chart opens on the last 100 runs,** or the last 90 days in the other
  two modes. The maintainer: "I think those are reasonable defaults". The
  old page's date defaulted to January 1 of the current year.
- **The mode and the range are remembered** by the browser, with one
  remembered range for runs and one for days. The maintainer: "Yes agreed."
- **The two ranges are two selects, one shown at a time,** because a
  remembered control's layout default can't vary
  ([2026-09-19](2026-09-19-a-query-parameter-selects-a-control-it-does-not-suspend-its-memory.md)).
  A single select would need one default for runs and another for days, and
  Dash discards a stored value when a later visit draws a different default.
  The unit is in each option, such as `Last 100 runs`, so the select needs
  no visible label.
- **A consequence of the default, left as it is:** switching to Score vs
  Time on a scenario last played more than 90 days ago opens on `No runs in
  this range`.

**A chart left open past midnight is redrawn.** The proposal said a point
leaves the chart at midnight. On a page that is left open nothing called the
chart then, and both review seats filed it on PR #370. The fix is a server
callback on the page's 30-second tick, the one that keeps Last played
current. It reads the app's date and writes it to a store,
`run-history-today`, only when the date has moved on. The store is an input
of the chart callback.

- **The server's date, and not the browser's.** It is the clock the range is
  counted from, so the trigger and the range cannot disagree about the day.
  A clientside callback was the other shape. It would send no request, but
  its rule could not be tested in pytest.
- **The cost:** one small request every 30 seconds while the page is open,
  and a chart that can be up to 30 seconds late after midnight.
- **The layout draws the store with the date already in it,** so the load
  writes nothing and the first tick rebuilds nothing. The chart still reads
  the clock for itself, and the store's value is read only for its change.
- **Measured:** with the app's date moved on by a day and nothing touched,
  one chart request followed after 15.0 s in Edge and 14.8 s in Firefox,
  triggered by that store alone, with no toast.

**What else the chart keeps and changes.**

- **Kept:** the PB score line, the Score threshold line, the rank lines, the
  New PB stars with their look and their Point size rule, the point hover,
  the legend, the empty and placeholder figures, the zoom fit, and plotly's
  own toolbar with Download plot as a PNG and Share chart.
- **The plot title is the scenario's name alone.** It was `{scenario}
  (updated: {timestamp})`. The maintainer: "Keep the title for now, since
  it's possible that the user will export the chart", and "Remove the
  timestamp; its timestamp is no longer useful."
- **The hover** shows the run's timestamp with seconds, its score, its
  sensitivity, and its accuracy, in every mode. The day line Score vs Time
  showed is dropped, since the timestamp above it says the same. In Score vs
  Sensitivity the sensitivity is the axis and is not repeated. Nothing new
  went into the hover.
- **Rank lines redraw at once when the Playlist filter changes.** They used
  to lag until the next rebuild. The maintainer: "Otherwise it would look
  like a bug to the user; when they switch playlists, they would expect to
  see the new rank lines." The filter is an input of the chart callback.
- **Plotting every run widens the score range downward,** so more of a
  playlist's rank ladder falls inside it without **Show all ranks**.
- **The empty state for a range** reads `No runs in this range`, over
  `Choose a longer range or play more runs.` There is no date to choose any
  more, and it is reachable only in the two modes that count days. The
  empty state for an unexpected mode names three modes.

**The latest run is ringed.** While the selected scenario is the one last
played and that run is in range, its point carries a ring and its row in the
list is highlighted, so the card, the row, and the point read as one run.
The ring has no legend entry and no hover of its own. How it is shown was
PR #372's to choose.

- **The figure rings its own scenario's newest run, and does not decide
  whether the ring shows.** The builders add one trace round that run when
  the range holds it, tagged with the run's id. So the chart callback takes
  no new input.
- **The card's callback writes the id of the newest run on any scenario to a
  store,** only when it is another run than the one held. The graph's one
  callback, the one that already styles the cached figure for the theme and
  the point size, takes that store and shows the ring while the two ids are
  the same run.
- **The ring is shown and hidden by its opacity, never by `visible`.**
  plotly.js leaves a trace that is not visible out of its axis ranges, and
  the ring is wider than a run point. Hidden that way, every point would
  move a few pixels when the ring went.
- **The figure has one writer, and no duplicate output.** A second callback
  that patched the figure would not be held back for the chart, so a patch
  could land on the old figure and be overwritten by the new one, with the
  ring wrong.
- **A run on another scenario with Follow off takes the ring off with a
  patch:** the ring's opacity and nothing else. The chart is not rebuilt, and
  a zoom on it is kept. A whole new figure would have undone the zoom. The
  cost is one small request where there was none. It carries the cached
  figure up, 15,101 characters at the default range, and brings back about
  100 bytes. The ring was gone 147 ms after the batch reached the page in
  Edge and 209 ms in Firefox.
- **The look.** The app's blue, `#1c7ed6` on the light background and
  `#74c0fc` on the dark one, 18 px wide. Point size makes it 14 or 22 px,
  wide enough to clear the star at the same setting.
- **The row's highlight follows the selection and not the range.** The
  proposal's sentence puts "that run is in range" over both the ring and the
  row. As built, the row is highlighted while the selected scenario is the
  one last played, whatever the chart's range: a point outside the range
  cannot be ringed, and the row is in the list either way. Following the
  sentence to the letter would have made the chart's mode and both ranges
  inputs of the list. The maintainer, 2026-10-13: "the reading is fine."

**Not carried from the mockup: the 2 px nudge in Score vs Time.** The mockup
spread a session's runs 2 px apart so they could be counted, and the
maintainer leaned to keeping that. plotly places a point by its data value.
The proposal's author knew of no per-point pixel offset for a scatter trace
and found none in the documentation searched. A nudge would mean moving
points off their real times by an amount that depends on the chart's width
and zoom, recomputed in the browser after every draw. Over 90 days at
830 px, 2 px is about five hours. Score vs Run is the mode for counting a
session's runs, and zooming Score vs Time separates them. This departs from
a lean, and the ratification covered it.

**What this changes in older entries.** Each keeps its text and gains a
dated note.

- The 2026-10-05 stars entry: its clauses about Top N, the oldest date, the
  kept tie, and the Average score trace stop applying. The rest is in
  [the stars entry for Score vs Run](2026-10-12-score-vs-run-stars-each-new-pb.md).
- [2026-09-12, Share chart](2026-09-12-charts-keep-plotlyjs-4s-share-chart-button.md):
  the figure shared holds every run in the range and no Average score line,
  and its title no longer carries a render time. The button stays.
- [2026-07-11, timestamps](2026-07-11-humanize-the-absolute-timestamp-format.md):
  the plot title's `updated:` use ends. The format and its rules stand.

**Evidence and its limits.** The counts above are from the maintainer's
stats folder, one player's history: 8,937 runs over 866 scenarios on
2026-10-05. Nothing was measured on other players' data.

Proposed in
[PR #356](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/356),
which merged as `a65f72d`. Shipped in
[#370](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/370) and
[#372](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/372),
hidden, and made public in
[#373](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/373),
which deleted the old chart. The proposal file,
`docs/proposals/run_history_proposal.md`, is deleted, and git history keeps
it.
