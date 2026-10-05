# The Score vs Time Chart Marks Each New PB

Status: Proposed
Date: 2026-10-04

## TL;DR

On the Scenario Performance chart every run is the same dot, so the runs that
set a personal best can only be found by comparing each dot with everything
before it. This proposal draws a gold star on each plotted run that beat the
scenario's personal best when it was played, on the Score vs Time chart. The
stars need no setting, and nothing else about the chart changes.

## Decisions needed

Nothing in this proposal is ratified. Three choices need the maintainer's
product judgment: M1, M2, and M3. Each carries a recommendation and what
follows from choosing differently.

Everything else is author-owned and open to challenge. Design tags those
choices M4 (the look and how it is built) and M5 (the copy and the term).

### M1 — A star marks every run that set a new PB, not only the current one

Status: Open

The material consequence: the chart works out which of the scenario's runs
beat the PB when they were played and marks each one it plots, so a
well-played scenario shows several stars and not one.

**Recommendation: mark every plotted run whose score was strictly above every
earlier run of the scenario.** This is the rule the personal best celebration
already uses
([2026-09-02](../decision_log.md#2026-09-02-a-new-personal-best-celebrates-on-every-page)):
a tie doesn't count, and a scenario's first run only sets the baseline. The
comparison covers the scenario's whole history, at every sensitivity, whatever
the page's oldest date is. A star then means one thing, whatever the chart's
filters are set to: this run was the PB when it was played. It marks an
achievement and judges nothing
([The direction this is held to](#the-direction-this-is-held-to)).

Choosing differently:

- **Mark only the current PB.** One star per chart, on the point the PB score
  line already touches. It adds nothing the line doesn't show, and it can't
  answer when the earlier PBs happened.
- **Judge against the plotted window only,** restarting the comparison at the
  oldest date. The star's meaning would then move with a chart control, and
  it would mark runs that were never a PB: 86 of them, across 45 of the
  maintainer's 188 scenarios that have runs older than the window.
- **Count the first run.** It is the PB by definition when it is played, so
  every scenario would open with a star that says nothing. The celebration
  skips it for the same reason.

### M2 — Only Score vs Time is marked

Status: Open

The material consequence: Score vs Sensitivity is drawn exactly as it is
today.

**Recommendation: draw the stars on Score vs Time and leave Score vs
Sensitivity alone.** Along the date axis the stars read left to right as the
history of the PB. Along the sensitivity axis they have no order. That chart
also keeps only the top scores at each sensitivity. Those are mostly the
latest new PBs, and the older ones are filtered out. The numbers are in
[What the data shows](#what-the-data-shows): about four in ten points would be
stars, and on well-played scenarios a third to half of the new PBs wouldn't
be drawn.

Choosing differently:

- **Mark both charts.** One rule everywhere, at the cost above. Nothing on
  the sensitivity chart would show which PBs are missing.
- **On Score vs Sensitivity, mark only the current PB.** It would show which
  sensitivity holds the PB. The PB score line already touches that point, and
  the star would mean something different on each chart.

### M3 — The stars have no Chart options control

Status: Open

The material consequence: the stars are always drawn on Score vs Time, and
the Chart options panel stays as it is.

**Recommendation: no switch, and no color or shape setting.** Clicking New PB
in the legend hides the stars, as it hides any trace. That choice is not
remembered. The stars are expected back when the chart is next redrawn by a
new run, a control change, or a theme change: plotly.js keeps a legend click
across a new figure only when the figure sets `uirevision`, and this chart
sets none. The live check verifies it.

Two reasons:

- **No workflow asks for a control yet.** The 2026-08-20 entry that gave the
  run points a size and a color
  ([Run Points Get A Size Preset And A Color, And The Chart Stops There](../decision_log.md#2026-08-20-run-points-get-a-size-preset-and-a-color-and-the-chart-stops-there))
  asks that a chart control answer a recognizable user goal. It keeps three
  levels: a strong default, a small set of controls for the primary data
  marks, and "nothing else until a real workflow demands it".
- **A star costs little to ignore.** It sits on a point that is drawn anyway,
  so the axes cover the same runs with or without it. An overlay line
  differs: it can stretch the score axis, as the full rank ladder does.

Choosing differently:

- **Add a New PB switch to Overlays.** Hiding the stars would persist in the
  browser like the other switches. It costs a fourth control in a group of
  three, one more persisted id, and one more input that rebuilds the chart.
  The 2026-08-20 entry asks for a rethink before one visual object's group
  passes roughly three controls. Overlays is not one object's group, so that
  guideline applies only by analogy. The switch can be added later without
  migrating anything, so waiting to see whether the stars bother anyone
  loses nothing.
- **Let the PB score switch hide the stars too.** No new control, and the
  choice persists. But the switch is named for the line, and the line
  stretches the score axis where the stars don't. A player who turns the line
  off to see recent runs closer would lose the stars with it.
- **A color or shape setting.** The 2026-08-20 entry stops chart
  customization at the run points' size and color. Nothing here needs it
  moved.

## Problem

### The chart can't show when the PBs happened

The Scenario Performance chart
([spec](../specs/scenario_performance.md#the-graph)) plots each kept run as
one point of the trace named Run data point, with an Average score line
through each group. The current [PB](../glossary.md#pb) appears as a dashed
PB score line. Nothing marks the runs that were PBs when they were played.

To find them, a reader has to carry a running maximum across the chart: a
point is a past PB only if it is higher than every point to its left. On
Score vs Time a whole day's runs share one x position, so the order within a
day is not visible at all. The second-highest point of a day may have been a
PB for ten minutes, or may have come after the day's best.

A new PB is an achievement, and the app treats it as one: the personal best
celebration marks it at the moment of the run. Nothing marks it afterwards.
A player looking back at a scenario between sessions
([product.md](../product.md#when-they-ask-them)) can't see when they reached
each best. The playlist tables' PB Date column gives the date of the current
PB only.

### What the data shows

Measured on the maintainer's stats folder on 2026-10-04: 8,880 runs over 866
scenarios. The chart filters are the page defaults, Top N scores of 5 and an
oldest date of January 1. A run counts as a new PB under M1's rule, and it
gets a star when the chart plots it
([Where a star is drawn](#where-a-star-is-drawn-m2)).

- 480 scenarios have at least one run this year, so they have a chart.
- 691 runs this year were new PBs.
- 284 of the 480 charts would show at least one star on Score vs Time.

How many plotted points would be stars:

| Scenarios | Score vs Time | Score vs Sensitivity |
|---|---|---|
| All 480 | 666 of 2,220 (30%) | 584 of 1,355 (43%) |
| The 75 with 20 or more runs | 240 of 1,195 (20%) | 172 of 413 (42%) |
| The 9 with 100 or more runs | 24 of 208 (12%) | 13 of 41 (32%) |

How many of this year's new PBs get a star, after the Top N filter:

| Scenarios | Score vs Time | Score vs Sensitivity |
|---|---|---|
| All 480 | 666 of 691 (96%) | 584 of 691 (85%) |
| The 75 with 20 or more runs | 240 of 255 (94%) | 172 of 255 (67%) |
| The 9 with 100 or more runs | 24 of 24 | 13 of 24 (54%) |

The four busiest charts would show 9 stars among 64 points, 5 among 62, 8
among 55, and 9 among 55 on Score vs Time. The same four scenarios on Score
vs Sensitivity would show 3 among 9, 5 among 10, 3 among 5, and 4 among 10.

Two readings:

- **The share falls as a scenario is played more.** A new scenario's runs are
  mostly PBs, and a practiced scenario's rarely are. The celebration's entry
  accepted the same pattern and declined a minimum run count.
- **Score vs Time keeps nearly every new PB, and Score vs Sensitivity
  doesn't.** A day's filter drops a new PB only when five runs at or above
  its score follow it the same day. A sensitivity's filter drops every new PB
  that five later runs at that sensitivity have since beaten.

### The decision this touches

The 2026-08-20 entry
([Run Points Get A Size Preset And A Color, And The Chart Stops There](../decision_log.md#2026-08-20-run-points-get-a-size-preset-and-a-color-and-the-chart-stops-there))
made the run points' size and color customizable and nothing else. It also
says when to look again: "reconsider marker symbols only if the graph ever
carries multiple semantic point categories".

This proposal is that case. A new PB is a second category of point. The
outcome proposed here is a symbol the app fixes, and still no symbol control.
The entry stands as written, and the shipping entry links it.

### The direction this is held to

The 2026-10-04 entry
([Skill Is Judged By The Typical Run, With Honest Uncertainty, In Verdicts Not Advice](../decision_log.md#2026-10-04-skill-is-judged-by-the-typical-run-with-honest-uncertainty-in-verdicts-not-advice))
holds every later proposal to three rules. The first is the one that matters
here. Judgments about skill, whether the player is improving among them, move
toward the typical run, and the personal best stays the achievement.

The stars sit on the achievement side of that line. They record what the
player reached and when, as the celebration does. They are not a judgment of
skill, and they are not a trend. A PB only rises, so a row of stars can't
show a decline, and after one lucky run it reads as a plateau. Whether the
player is improving stays the trend verdict's question, answered from session
medians.

This chart has no typical-run read of its own. Its Average score line
averages only the runs each day plots, the top N, so on a busy day it is the
average of that day's best.

The cost to weigh under M1 is emphasis. Gold stars draw the eye to the best
runs, on a chart that already plots each day's best, in an app whose reading
of skill is moving toward the typical run.

The other two rules need nothing from this design. A star is a fact about a
run, with no estimate in it and no advice.

## Design

### The rule (M1)

One pass over the scenario's runs from oldest to newest, keeping the best
score so far. A run strictly above that best is a new PB. The scenario's
first run sets the baseline and is not one.

- **Whole history.** The pass covers every run the app holds for the
  scenario, including runs older than the page's oldest date and runs at
  every sensitivity. This matches the PB's own meaning, the highest score
  among a scenario's runs whatever their sensitivity.
- **Ties.** A run that equals the best is not a new PB, so the earliest run
  to reach a score holds the star. The playlist tables' PB Date already reads
  a tied PB that way.
- **Nothing is stored.** The pass runs when the chart is rebuilt. The
  maintainer's largest scenario has 463 runs.
- **Time-scored scenarios.** A higher score is better on every scenario,
  those included, so the pace proposal
  ([#329](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/329))
  doesn't change this rule.

### Where a star is drawn (M2)

- **Score vs Time only.**
- **On the run that set it.** A star is drawn on a plotted run that is a new
  PB. The match is on the run, not on its position on the chart. A later run
  the same day with the same score sits at the same position, and it is not a
  new PB.
- **A new PB the chart doesn't plot gets no star.** That happens when the Top
  N filter dropped it, or when it is older than the oldest date. Such a run
  still counts in the comparison.
- **A kept tie doesn't inherit the star.** With Top N low enough, the day's
  filter can drop a new PB and keep a later run that tied it, because it
  keeps the later of two equal scores. That day then has a point at the PB's
  score and no star. Matching on the position would star it: on the
  maintainer's data, 4 stars on runs that never beat the PB.
- **A star's hover names the run that set the PB.** When a new PB and a later
  same-day tie are both plotted, their points coincide: 26 of the 666 stars
  on the maintainer's data. The chart shows one hover for the pair, and today
  it is the later run's, which never beat the PB. So the new PB is placed
  last among the run points at its position, and its hover is the one shown
  ([How it is built](#how-it-is-built-m4)). Nothing else moves: the same runs
  are plotted at the same positions, and the Average score line is unchanged.
- **No stars, no trace.** A chart where no plotted point is a new PB has no
  New PB legend entry.
- **Several new PBs on one day stack in that day's column,** as its other
  runs do.

### The look (M4)

| Property | Value |
|---|---|
| Symbol | plotly's `star` |
| Fill | `#fab005`, Mantine yellow 6 |
| Outline | `#5f3d00`, 1 px |
| Size | 12 with Point size on Default, 9 on Small, 16 on Large |

- **Gold.** It is the usual color of an award. Yellow is also one of the four
  color families the Point color swatches leave out, so no swatch can match
  it.
- **An outline, because gold alone fails on white.** Gold has 1.86:1 against
  the light plot background and 8.34:1 against the dark one. The outline has
  9.75:1 against white and 5.24:1 against the gold. The 2026-08-20 entry
  dropped yellow from the swatches for the same contrast reason.
- **A shape as well as a color.** Point color accepts any hex value, so a
  player can set the run points to this exact gold. The star and its outline
  still stand apart then, and the mark never depends on color alone.
- **One color for both themes,** as with the swatches. No theme logic is
  added.
- **About twice the run point's size.** A star reads smaller than a circle of
  the same size. The run points are 4, 6, and 10 px at the three presets. The
  Large star is 16 and not 20, so stars on neighboring days don't crowd.

The values were chosen from a prototype built through the app's own plot
functions on the maintainer's runs. It covered both themes, the three sizes,
and gold run points.

### How it is built (M4)

- **A third trace named New PB,** added after Average score, so it is drawn
  on top. The run trace keeps every run. Hiding the stars from the legend
  therefore leaves an ordinary point where each star was.
- **The star takes no hover.** The trace sets `hoverinfo` to `skip`, so
  hovering a star shows the run trace's hover for that point. On a shared
  point plotly shows the run trace's hover even when the star trace has one,
  observed in the prototype on the bundled plotly.js.
- **The run trace orders a new PB after the runs that share its position.**
  Among points at one position, plotly shows the hover of the one that comes
  last in the trace, also observed in the prototype. With the new PB last,
  hovering its star shows that run's own time, sensitivity, and accuracy.
  Only the order of points within the trace changes.
- **Point size sizes the stars too.** `apply_point_appearance` sets 9 or 16
  on the New PB trace for Small or Large, and leaves the generated 12 on
  Default. Point color still selects only the run trace.
- **The zoom fit needs no change.** It reads every visible trace, and the
  stars sit on run points, so the fitted range is the same. Its comment names
  the traces it fits and is updated.
- **The legend gains a third entry.** The three entries are about 340 px wide
  in the prototype. The live check covers the narrowest chart.
- **A star on a recent PB can sit under the PB score label.** The label is
  drawn at the right end of its line, and that run's point sits under it
  today. The star is larger, so more of it is covered. Where the overlay
  labels go is a separate open question, and this proposal doesn't move them.
- **Share chart and Download plot as a PNG carry the stars,** as they carry
  everything plotted. The spec's list of what the figure holds gains them.
  The figure holds no new data: each star repeats a plotted run's date and
  score.
- **Score vs Sensitivity keeps its two traces.**

### Copy (M5)

One string is added. It follows AGENTS.md's nine copy rules.

| Where | String | Why |
|---|---|---|
| Chart legend, Score vs Time | `New PB` | It is the celebration toast's title, New personal best, in the short form the chart already uses beside it in PB score. Sentence case, like Run data point and Average score. "PB run" is taken: the glossary uses it for the one run that holds the PB now. |

Unchanged on purpose:

- The run points' hover text. Which run's hover shows at a starred point
  that a tie shares does change, as Where a star is drawn says.
- The legend entries Run data point and Average score.
- The chart annotation `PB score ({value})`.
- Every Chart options label and help text.

### Terms (M5)

The entry below is written as [docs/glossary.md](../glossary.md) would hold
it. The shipping PR moves it in, under Scores and notifications.

- **New PB.** A run that beat its scenario's PB when it was played. It was
  the PB until a later run beat it, so a scenario's new PBs are the history
  of its PB. Where the chart marks them goes in the Scenario Performance
  spec.
  - On screen: New PB in the chart legend. The celebration toast's title
    says New personal best.
  - In code: `new_high_score`.
  - Not the PB run, the one run that holds the PB now.

No existing entry changes. The
[personal best celebration](../glossary.md#personal-best-celebration) entry's
"a run that beats its scenario's previous PB" is this term's meaning in other
words, and it stays as written.

## Out of scope

- **Stars on Score vs Sensitivity,** under M2.
- **Any Chart options control for the stars,** under M3.
- **A hover line on a marked run,** such as the PB it beat. It would go in
  the run trace's own hover data, because that trace's hover is the one
  shown.
- **Keeping a new PB that the Top N filter drops.** It would change which
  runs the chart plots, and the Average score line with them.
- **A minimum run count or margin before a run counts.** The celebration
  declined one, and the star follows the celebration's rule.
- **New PBs anywhere else:** the playlist tables, the Aim Training Journey
  graph, or a list of them. Run History is the place for a list.
- **A trend or a verdict read from the stars.** Whether the player is
  improving is the trend verdict's question
  ([The direction this is held to](#the-direction-this-is-held-to)).
- **The roadmap.** This is a small chart feature beside the milestones, so
  this PR adds no Upcoming entry. The shipping PR adds the Shipped entry.

## Delivery plan

One implementation PR. It starts once M1, M2, and M3 are ruled and this
proposal has merged. It has no other dependency and can run beside the Run
History and pace work. Recommended implementer: `claude-opus-5-5` at high, in
a fresh session. The change is specified down to its one string, and unit
tests plus one live check verify it.

- **Code:**
  - the rule, as a function over a scenario's runs, named for the glossary's
    code word;
  - the New PB trace on the Score vs Time figure;
  - the run trace's point order at a position a new PB shares;
  - the star size in `apply_point_appearance`;
  - the comment in the zoom-fit asset.
- **Tests:** listed under Testing.
- **Shipping docs, in the same PR:**
  - a decision-log entry, opening with its layer-1 summary. It links the
    2026-08-20 and 2026-09-02 entries and supersedes neither.
  - `docs/specs/scenario_performance.md`: the trace, the rule, and where a
    star is drawn in The graph; the star size beside the Point size
    statement; the stars in the list of what a shared figure holds. The
    summary is checked against the payload change.
  - `docs/glossary.md`: the Terms block above.
  - `docs/product.md`: the inventory entry and the problem it solves.
  - `docs/architecture.md`: the sentence on `apply_point_appearance`, which
    now restyles two traces.
  - the rest of the Shipping a proposal checklist in AGENTS.md: the roadmap's
    Shipped entry, references to this file, and deleting this file.
  - The README's Scenario plots line and the user guide stay as they are.
    Neither describes the chart's marks.
- **New copy:** any string this proposal didn't foresee is listed under "New
  copy" in the PR body.

## Testing

- **The rule:**
  - a run above every earlier run is a new PB, and one below isn't;
  - a tie isn't, and the earlier run keeps it;
  - the first run isn't;
  - runs are judged in time order, whatever order they are held in;
  - a run at one sensitivity is judged against earlier runs at another.
- **The figure:**
  - Score vs Time gains a third trace named New PB, after Average score,
    with the symbol, colors, size, and hover setting above, on the right
    points;
  - a run older than the oldest date counts in the comparison and isn't
    drawn;
  - a new PB the Top N filter dropped has no star;
  - with Top N at 1 and a later same-day tie, the tie is the run kept and
    no star is drawn;
  - with a new PB and a later same-day tie both plotted, the trace holds one
    star, and the new PB comes after the tie in the run trace;
  - a chart with no new PB among its points has two traces;
  - Score vs Sensitivity has two traces.
- **The appearance callback:**
  - Small and Large set the star to 9 and 16, and Default leaves 12;
  - a Point color changes the run trace and not the star;
  - a figure with no New PB trace passes through.
- **Existing tests** that pin the figure to two traces are updated for Score
  vs Time.
- **Live check,** in both themes:
  - the stars at the three Point size presets;
  - Point color set to `#fab005`;
  - a legend click hides the stars and leaves the run points, and the stars
    return on the next redraw;
  - an x zoom still refits the score axis, with the stars shown and hidden;
  - the three-entry legend clears the title at the narrowest chart, with the
    Chart options panel open just above its stacking width;
  - a run that beats the PB gains its star when the chart rebuilds;
  - a star whose point a later same-day tie shares, the two runs differing in
    sensitivity or accuracy: the hover shows the new PB's time and values.
