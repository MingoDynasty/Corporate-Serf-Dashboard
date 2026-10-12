# 2026-10-05: The Score vs Time Chart Marks Each New PB With A Star

Status: Accepted

The Score vs Time chart now draws a gold star on each plotted run that beat
the scenario's personal best when it was played. Every run used to be the same
dot, and a day's runs share one position, so the runs that set each best could
only be found by comparing every dot with all the ones before it. The stars
need no setting, and the Score vs Sensitivity chart is drawn exactly as
before. They record what the player reached and when, and they don't judge
whether the player is improving.

**Ruling.** Ruled (user) 2026-10-05, on PR #337: the maintainer ratified the
whole proposal after two review waves, with every reviewer endorsing every
row. That settled the rule, the chart it applies to, and the absence of a
control as recommended. It also covered the author-owned look, build, copy,
and term, and with them one exception to an earlier entry, named under
**Point size sizes the stars**.

**The rule.** A new PB is a run whose score is strictly above every earlier
run of its scenario. It is the rule the personal best celebration applies to
one new run
([2026-09-02](#2026-09-02-a-new-personal-best-celebrates-on-every-page)), so a
star and a celebration judge a run the same way.

- One pass over the scenario's runs from oldest to newest, at every
  sensitivity, including the runs older than the page's oldest date. A star
  then means one thing whatever the chart's filters are set to: this run was
  the PB when it was played.
- A tie is not a new PB, so the earliest run to reach a score holds the star.
  The playlist tables' PB Date already reads a tied PB that way.
- The scenario's first run sets the baseline and is not one.
- Nothing is stored. The pass runs when the chart is rebuilt, and the
  maintainer's largest scenario had 463 runs on 2026-10-04.
- A higher score is better on every scenario, time-scored ones included, so
  pace doesn't change the rule.

Rejected:

- **Mark only the current PB.** One star per chart, on the point the PB score
  line already touches. It adds nothing the line doesn't show, and it can't
  say when the earlier PBs happened.
- **Judge against the plotted window only,** restarting the comparison at the
  oldest date. The star's meaning would move with a chart control, and it
  would mark runs that were never a PB: 86 of them, across 45 of the 188
  scenarios with runs older than the window.
- **Count the first run.** Every scenario would open with a star that says
  nothing. The celebration skips it for the same reason.
- **One star per day,** on the run that held the PB when the day ended: 421
  stars where the rule draws 666. A star would stop matching the celebration's
  rule one to one, and its meaning would depend on the chart drawing its axis
  in days. The 245 stars it drops are the ones a reader couldn't find before,
  because a day's runs share one position.

**Only Score vs Time is marked.** Score vs Sensitivity keeps its two traces.
The chart opens on Score vs Sensitivity and remembers the choice per browser,
so a fresh browser shows no stars until the reader switches. Along the date
axis the stars read left to right as the history of the PB, and along the
sensitivity axis they have no order. That chart also keeps only the top scores
at each sensitivity, which are mostly the latest new PBs. About four in ten of
its points would be stars (584 of 1,355), and on the 75 scenarios with 20 or
more runs it would draw only 172 of the 255 new PBs, with nothing to show
which are missing. Rejected: marking both charts at that cost, and marking
only the current PB on Score vs Sensitivity, where the PB score line already
touches that point and the star would mean something different on each chart.

**A star belongs to the run, not to a position.** A star is drawn on a plotted
run that is a new PB.

- A new PB the chart doesn't plot gets no star, whether the Top N filter
  dropped it or it is older than the oldest date. It still counts in the
  comparison. By this rule 666 of the year's 691 new PBs get a star.
- A later run the same day with the same score sits at the same position, and
  it is not a new PB.
- **A kept tie doesn't inherit the star.** The day's filter keeps the later of
  two equal scores, so with Top N low enough it drops a new PB and keeps the
  run that tied it. That day then has a point at the PB's score and no star.
  A match on the position would star it: 4 stars on runs that never beat the
  PB.
- A chart where no plotted point is a new PB has no New PB trace and no legend
  entry.

**The hover names the run that set the PB.** When a new PB and a later
same-day tie are both plotted, their points coincide: 26 of the 666 stars. The
chart shows one hover for the pair. Among points at one position plotly.js
shows the hover of the one that comes last in the trace, and in time order
that is the later run, which never beat the PB. So the run trace places a new
PB after the runs that share its position, and its hover is the one shown.
Only the order of points within the trace changes: the same runs are plotted
at the same positions, and the Average score line is unchanged.

That order is an observed behavior of the bundled plotly.js 4, not a
documented one. A unit test pins the order within the trace. Which point
plotly.js answers with can only be seen in a browser, and the implementation's
scripted check does that: on a real shared star it read the new PB's own time
and accuracy at six cursor positions across the star. A plotly.js upgrade is
where it could change.

**The look.** One color for both themes, with no theme logic.

| Property | Value |
|---|---|
| Symbol | plotly's `star` |
| Fill | `#fab005`, Mantine yellow 6 |
| Outline | `#5f3d00`, 1 px |
| Size | 12 with Point size on Default, 9 on Small, 16 on Large |

- **Gold,** the usual color of an award. Yellow is also one of the four color
  families the Point color swatches leave out, so no swatch can match it.
- **An outline, because gold alone fails on white.** Gold has 1.86:1 against
  the light plot background and 8.34:1 against the dark one. The outline has
  9.75:1 against white and 5.24:1 against the gold. The
  [2026-08-20 entry](#2026-08-20-run-points-get-a-size-preset-and-a-color-and-the-chart-stops-there)
  dropped yellow from the swatches for the same contrast reason.
- **A shape as well as a color.** Point color accepts any hex value, so a
  player can set the run points to this exact gold. The star and its outline
  still stand apart then, and the mark never depends on color alone.
- **About twice the run point's size.** A star reads smaller than a circle of
  the same size. The run points are 4, 6, and 10 px at the three presets. The
  Large star is 16 and not 20, so stars on neighboring days don't crowd.

The values were chosen from a prototype built through the app's own plot
functions on the maintainer's runs, in both themes, at the three sizes, and
with gold run points.

**How it is built.** A third trace named New PB, added after Average score so
that it is drawn on top.

- The run trace keeps every run, so hiding the stars from the legend leaves an
  ordinary point where each star was.
- The star trace sets `hoverinfo` to `skip`, so hovering a star shows the run
  trace's hover for that point.
- Share chart and Download plot as a PNG carry the stars, as they carry
  everything plotted. The figure holds no new data: each star repeats a
  plotted run's date and score.
- The zoom fit is unchanged. It reads every visible trace, and the stars sit
  on run points, so the fitted range is the same with the stars shown or
  hidden.
- The legend's three entries were 364 px wide and on one row at the narrowest
  chart the open Chart options panel leaves, where the plot area was 497 px
  wide (headless Edge, 2026-10-05).
- A star on a recent PB can sit under the PB score label, which is drawn at
  the right end of its line. Where the overlay labels go is a separate
  question, and this entry doesn't move them.

**Point size sizes the stars, an exception to the 2026-08-20 entry.** That
entry
([Run Points Get A Size Preset And A Color, And The Chart Stops There](#2026-08-20-run-points-get-a-size-preset-and-a-color-and-the-chart-stops-there))
says "Nothing else on the chart became customizable", and its point
preferences restyle only the run trace. Point size now sizes the New PB trace
too: 9 on Small, 16 on Large, and the generated 12 on Default. Point color
still restyles only the run trace. The set of controls doesn't change, but one
control now restyles two traces, so that entry is superseded in part, for that
one sentence and nothing else.

The same entry says when to look at symbols again: "reconsider marker symbols
only if the graph ever carries multiple semantic point categories". This is
that case, since a new PB is a second category of point. The outcome is a
symbol the app fixes, and still no symbol control.

**No control.** Nothing in the Chart options panel changed: no switch, no
color or shape setting, and no new persisted id.

- Clicking New PB in the legend hides the stars, as it hides any trace. That
  choice is not remembered. A new figure brings the stars back, because
  plotly.js keeps a legend click across figures only when the figure sets
  `uirevision`, and this chart sets none on purpose. The chart gets a new
  figure from a new run on the scenario, a control that rebuilds it, or an
  appearance change: Point size, Point color, or the theme.
- The celebration accepted the same density of new PBs on a lightly played
  scenario with its setting as the way out. The stars have no equivalent: in
  session, a legend click lasts until the next run on the scenario.
- No workflow asks for a control yet. The 2026-08-20 entry asks that a chart
  control answer a recognizable user goal, and keeps "nothing else until a
  real workflow demands it".
- A star costs little to ignore. It sits on a point that is drawn anyway, so
  the axes cover the same runs with or without it. An overlay line differs: it
  can stretch the score axis, as the full rank ladder does.

Rejected:

- **A New PB switch in Overlays.** Hiding the stars would persist like the
  other switches, at the cost of a fourth control in a group of three, one
  more persisted id, and one more input that rebuilds the chart. It can be
  added later without migrating anything, so waiting to see whether the stars
  bother anyone loses nothing.
- **Letting the PB score switch hide the stars too.** No new control, and the
  choice would persist. But the switch is named for the line, and the line
  stretches the score axis where the stars don't. A player who turns the line
  off to see recent runs closer would lose the stars with it.
- **A color or shape setting.** The 2026-08-20 entry stops chart customization
  at the run points' size and color, and nothing here needs it moved.

**Achievements, not a trend.** The
[2026-10-04 direction entry](#2026-10-04-skill-is-judged-by-the-typical-run-with-honest-uncertainty-in-verdicts-not-advice)
moves judgments about skill toward the typical run and keeps the personal best
as the achievement. The stars sit on the achievement side of that line.

- They record what the player reached and when, as the celebration does. They
  are not a judgment of skill, and they are not a trend.
- A PB only rises, so a row of stars can't show a decline, and after one lucky
  run it reads as a plateau. Whether the player is improving stays the trend
  verdict's question, answered from session medians.
- This chart has no typical-run read of its own. Its Average score line
  averages only the runs each day plots, the top N, so on a busy day it is the
  average of that day's best.
- The cost accepted is emphasis: gold stars draw the eye to the best runs, on
  a chart that already plots each day's best, in an app whose reading of skill
  is moving toward the typical run.
- A star is a fact about a run, with no estimate in it and no advice, so that
  entry's other two rules ask nothing of it.

**Measured.** On the maintainer's stats folder on 2026-10-04: 8,880 runs over
866 scenarios, at the page defaults of Top N scores 5 and an oldest date of
January 1. The folder has grown since, so it no longer gives these counts.

- 480 scenarios have a run this year, so they have a chart. 691 runs this year
  were new PBs, and 284 of the 480 charts show at least one star.
- 666 of the 2,220 plotted points are stars (30%). The share falls as a
  scenario is played more: 240 of 1,195 (20%) on the 75 scenarios with 20 or
  more runs, and 24 of 208 (12%) on the 9 with 100 or more.
- 245 of the 666 stars (37%) are on a run that a later run the same day beat,
  and 174 of the 830 plotted days carry two or more stars. Those 245 are what
  the stars add over reading each day's top point, and a third of their
  density.

**Copy and term.** The legend entry is `New PB`, the short form of the
celebration toast's New personal best that the chart already uses in PB score.
The glossary gains New PB, with `new_high_score` as its code word. "PB run"
was taken: it is the one run that holds the PB now.

**Out of scope.** A hover line on a marked run, such as the PB it beat.
Keeping a new PB that the Top N filter drops, which would change which runs
the chart plots and the Average score line with them. A minimum run count or
margin before a run counts, which the celebration declined. New PBs anywhere
else: the playlist tables, the Aim Training Journey graph, or a list of them.
A trend or a verdict read from the stars.

Design in [#337](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/337),
implementation in [#346](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/346).
