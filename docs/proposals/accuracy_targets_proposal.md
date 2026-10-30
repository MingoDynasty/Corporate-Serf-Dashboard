# Accuracy Targets Beside The Chart's Rank Lines

Status: Proposed
Date: 2026-10-30

## TL;DR

On a tracking scenario a run's score is its hit accuracy times a fixed
amount, so every rank threshold on the chart is also an accuracy the run
needs, but the chart shows only the score. This proposal adds an Accuracy
targets switch to Chart options, off to start, that writes each rank's
accuracy target in the chart's right margin beside its line, such as 39.2%
beside Saffron (2350). The app works out the targets from the player's own
runs and shows them only where those runs prove that the score follows
accuracy, which holds for tracking and for switching scenarios played with
the fire button held, and the chart says why when a scenario gets none.

## Decisions needed

Six rows, AT1 to AT6. **Nothing is ratified.** AT2 to AT4 carry the
maintainer's direction from the design discussion of 2026-10-29 and
2026-10-30, worked out on two versions of a live copy of the app run on
their own stats. A third version, built while this proposal was written,
adds AT5's note and AT1's 5-run minimum. AT1's source of the targets is the
maintainer's choice of 2026-10-30. The rest of AT1, and AT5 and AT6, are the
author's recommendations, which the maintainer saw listed before asking for
this proposal, with a 3-run minimum that the measurements here raised to 5.
A direction or a choice is not a ruling, and reviewers may challenge any
row, and anything in [Design](#design), which is author-owned.

### AT1. Targets come from the player's own runs, where at least 5 agree

Status: open. The maintainer's choice of source, 2026-10-30, between the
player's own runs and the leaderboard's: "Yes, own runs". The 5-run minimum
and the agreement test are the author's.

The material consequence: a scenario shows targets only after 5 runs since
its last update, and never on a scenario whose runs disagree. On the
maintainer's stats, 90 of the 659 ranked scenarios they have played get
targets, 438 have fewer than 5 runs since their last update, and the other
131 have runs that disagree.

**Recommendation: a scenario's targets come from its runs since its last
update. A run's score over its hit accuracy is the score it would have made
at 100%. When at least 5 runs have a hit accuracy above zero, and at least
90% of them land within 2% of their median, that median is the scenario's
score at 100%, and a rank's target is its threshold over it. Otherwise the
scenario has none.**

- **Why the player's runs, and not a list of scenario types.** Whether a
  score follows accuracy depends on how the fire button is used, not on the
  scenario's genre. On a multi-bot switching scenario played with the button
  held through the gaps between bots, shots keep counting, so the targets
  stay exact and 100% just becomes out of reach: the runs agree within 0.5%
  on VT EddieTS Intermediate S5 and 1.5% on VT Ground Intermediate S5. A
  player who lets go in the gaps fires fewer shots on some runs than on
  others, so their runs disagree and they get none, which is right for them.
  A list of tracking scenarios would miss the first case and wrongly include
  the second, and nothing would keep it current.
- **Why not the rank data or Damage Possible.** A ladder holds scores only.
  Turning one into an accuracy needs the score at 100%, which no file but a
  run's stats file holds. Damage Possible is one run's shots times its
  damage per shot, so it is a run figure too, and it is in damage, not
  score: on VT EddieTS Intermediate S5, which scores 10 points per point of
  damage, Jade's 1,020 over Damage Possible reads 410.9%.
- **Why not the leaderboard.** Other players' runs carry a score and a hit
  accuracy, so the same test could run on them and work on scenarios the
  player has never played. It would need KovaaK's to answer before a chart
  could show targets, rely on a field the app has only observed, and
  measure how others fire. The maintainer chose the player's own runs.
- **Why 5 runs.** Over the maintainer's 127 scenario versions whose runs
  disagree, judged on 8 or more runs, 15 passed the test on their first 3
  runs and 5 on their first 5: a passing short streak shows targets that
  later vanish, on a scenario where they mean nothing. On the 119 versions
  whose runs agree, a 5-run window failed 2.0% of the time, so the wait is
  rarely longer than 5 runs. With 3 runs, 129 scenarios would get targets
  today rather than 90.
- **Why since the last update.** An update can change a scenario's length,
  and so its shots. The stats file's `Hash:` names the version, as it does
  for a run's check today.

### AT2. Targets show a tenth of a percent, rounded up

Status: open. The maintainer's direction, 2026-10-29: "Keep rounding up, but
also we should have at least 1 decimal of precision. There can be a huge
difference in saying "50.1%" vs "51%"."

The material consequence: a run up to 0.1 point under a target can still
reach its rank, and a target shows one decimal where a run's accuracy shows
two.

**Recommendation: a target is its exact value rounded up to the next tenth,
always with one decimal: Saffron's 39.16% reads 39.2%, and an exact 40%
reads 40.0%.**

- **Why up.** A run at or above the figure reaches the rank, as long as it
  fired as many shots as the median run. The first mockup's whole percent,
  also rounded up, read 42% for Jade on VT EddieTS Intermediate S5, where the
  PB reached Jade at 41.09%. A tenth reads 41.1%.
- **Why not two decimals,** as a run's accuracy has. The runs behind a
  target spread by up to 2%, which is 0.8 point at 40%, and 0.2 point at
  41% on VT EddieTS Intermediate S5, whose runs spread 0.45%. A second
  decimal would claim more than the runs agree on.

### AT3. The figures sit in the chart's right margin

Status: open. The maintainer's choice, 2026-10-30, between the two
placements of the second mockup: "Right margin".

The material consequence: while figures show, the plot loses 64 px of
width, which is 4% of it at 2,560 px and 10% at 1,536 px, and a figure is
read across from its line's label rather than inside it.

**Recommendation: each drawn rank line gets its figure just outside the
plot's right edge, level with the line, in the chart's normal text color.
The line's label is unchanged. The margin widens only while at least one
figure is drawn.**

- **Why the margin.** It adds no text inside the plot. The first mockup, and
  the second's other placement, put the figure in each label,
  `Saffron (2350 · 39.2% accuracy)`, which doubled every label's length.
- **Why not the rank's color.** The second mockup drew each figure in its
  rank's color, and the pale ones (Lavender, Celadon, Diamond) could not be
  read on the light theme. The line beside the figure carries the color.
- **Zoomed,** Plotly drops a figure whose line leaves the view, so only the
  lines in view keep their figures.

### AT4. An Accuracy targets switch in Chart options, off to start

Status: open. The maintainer's direction, 2026-10-29: "Accuracy Thresholds
should not show by default; it should be toggle-able via a setting. In most
cases it's something I would toggle a few times just to gauge the numbers,
but probably not something I would leave on all the time, mostly because of
graph clutter (unless we can manage that clutter somehow)." The author put
the switch in Chart options, where the maintainer saw it in the second
mockup.

The material consequence: the default is hard to change later. A remembered
control's stored value is reset when its default changes, so switching it
on by default in a later release would turn it on in every browser,
including those that had turned it off.

**Recommendation: an `Accuracy targets` switch in Chart options' Overlays,
after Show all ranks, off, and remembered like its neighbors. While it is
off the chart is exactly as it is today.**

- **Why Chart options.** The switch is flipped a few times while looking at
  the chart, and the rank lines' own switches are there. The Settings page
  is a page away from the chart.
- **Why off, even with the margin.** The maintainer's direction. AT3 is what
  would let a later release consider turning it on, and AT4's consequence is
  the price of doing so.

### AT5. With the switch on, a chart with no figures says why

Status: open. No lean recorded.

The material consequence: while the switch is on and the scenario has no
targets, a quiet line of text sits under the chart, and the plot is 32 px
shorter.

**Recommendation: one quiet line under the x axis's title, right-aligned,
naming the reason: fewer than 5 runs, fewer than 5 since the scenario was
last updated, or a score that depends on more than accuracy. Nothing shows
when no rank line is drawn.**

- **Why say anything.** With no note, the switch looks broken on most click
  scenarios. The reason also tells the player whether playing more will
  bring targets.
- **Why under the axis title.** Beside it, the longest note ran into the
  title on a 1,536 px window. Score vs Time's dates take two lines and push
  its title lower, so the note drops 82 px below the plot and the bottom
  margin grows from Plotly's 80 px to 112 px while it shows.
- **Why not in Chart options,** as the switch's description. Chart options
  starts closed on every visit, so the note would be hidden whenever the
  player moves to another scenario with the panel shut.

### AT6. Rank lines only

Status: open. No lean recorded.

The material consequence: the PB line and the score threshold line show no
accuracy.

**Recommendation: only rank lines get figures.**

- **The PB line:** the PB card already shows the PB run's accuracy.
- **The score threshold line:** the same rule would work, but the line moves
  with the PB and the percentage, and the maintainer asked about rank
  thresholds. A later change can add it with nothing here in its way.

## Problem

### What the chart shows today

- **Rank lines.** With Rank thresholds on and a benchmark playlist selected,
  each chart mode draws the ranks around the plotted scores, or the whole
  ladder with Show all ranks on, as dashed lines in their ladder colors,
  each labeled `{rank} ({threshold})` at its right end
  ([run_history.md](../specs/run_history.md#the-chart),
  [2026-10-12](../decision_log/2026/2026-10-12-the-run-history-chart-plots-every-run-and-draws-no-summary-line.md)).
- **A run's accuracy** is its hit accuracy, hits over shots, as KovaaK's
  shows it
  ([2026-10-18](../decision_log/2026/2026-10-18-pb-accuracy-shows-hit-accuracy-as-the-game-does.md)),
  to two decimals
  ([2026-10-18](../decision_log/2026/2026-10-18-a-runs-accuracy-shows-two-decimals.md)):
  in the run list's Accuracy column, and on the last lines of the
  [latest-run card](../specs/run_history.md#the-latest-run-card) and the
  [PB card](../specs/run_history.md#the-pb-card).
- So a player sees their accuracy and a rank's score, never the accuracy the
  rank needs.

### The idea

The maintainer's note, 2026-10-29, proposed accuracy targets in place of
score targets for ranks, "although more applicable to Tracking than Clicking
or Switching", and asked for them beside the rank line's threshold, "e.g.
"Saffron (9300, 35% accuracy)"". They expected the idea to work where the
fire button is held for the whole run, and to get "muddier" on multi-bot
tracking scenarios, with about a second between bots, and on switching
scenarios. AT1 answers that concern from the runs.

### Verified facts

Measured on the maintainer's stats folder (9,280 stats files on 2026-10-29)
at `22894be`, with a read-only survey of the files and, for coverage and the
mockups, the app's own data code and bundled ladders. A scenario's spread is
the standard deviation of its runs' scores at 100% over their mean; AT1's
test, within 2% of the median, is a separate measure.

- **On tracking scenarios, score follows accuracy exactly.** Of the 82
  scenarios with 8 or more runs and no kills (2,598 runs), score per hit is
  constant within 1% on all 82, and shots within 1% on 78. A run's score
  over its hit accuracy agrees within 1% across runs on 78, within 3% on 3,
  and within 10% on 1, and score and accuracy correlate at 1.00 (median).
- **Held-fire switching agrees too:** VT DotTS Intermediate S5 0.26%, VT FlyTS
  Intermediate S5 0.30%, VT EddieTS Intermediate S5 0.45%, VT PGT
  Intermediate S5 0.61%, VT Ground Intermediate S5 1.5% (spread of the score
  at 100% across runs).
- **Click and most switching don't.** Score is a fixed multiple of hits on
  107 of the 163 scenarios with kills, but shots vary with speed: VT ww5t
  Intermediate S5 spreads 5.2%, VT Popcorn Intermediate S5 6.3%, VT Pasu
  Intermediate S5 6.9%. 92 of the 163 spread 3% to 10%.
- **Damage figures.** Damage Done over Damage Possible is within half a
  point of hit accuracy on 2,590 of the 2,598 tracking runs, and Damage
  Possible is the score at 100% on scenarios that score their damage (VT
  Controlsphere Viscose, 6,001 both ways). Score equals Damage Done on only
  1,606 of the 2,598; VT EddieTS Intermediate S5 and VT ww5t Intermediate S5
  score 10 points per point of damage.
- **The minimum,** measured on 246 scenario versions with 8 or more runs,
  each judged on all its runs and then on every window of consecutive runs:

  | Runs in the window | Disagreeing versions passing on their first runs | Windows failing on agreeing versions |
  |---|---|---|
  | 2 | 63 of 127 | 0.2% |
  | 3 | 15 of 127 | 1.4% |
  | 4 | 10 of 127 | 1.5% |
  | 5 | 5 of 127 | 2.0% |

- **Coverage under AT1,** with the bundled ladders: of 659 ranked scenarios
  with runs, 90 get targets; 430 have fewer than 5 runs, and 8 more have
  fewer than 5 since their last update; 131 have 5 or more whose scores
  depend on more than accuracy. VT Penta Bounce Intermediate S5 is the
  loosest that passes: its runs spread 2.6%, yet at least 90% of them land
  within 2% of their median.
- **The most-played scenarios with targets,** each rank's target under AT1
  and AT2:

  | Scenario | Runs | Spread | Targets |
  |---|---|---|---|
  | VT DotTS Intermediate S5 | 463 | 0.26% | Platinum 48.4%, Diamond 51.5%, Jade 53.7%, Master 55.8% |
  | VT Raw Control Intermediate S5 | 174 | 0.16% | Bronze 37.5%, Silver 43.4%, Gold 49.2%, Platinum 55.0%, Diamond 60.9% |
  | VT Snake Track Intermediate S5 | 160 | 0.29% | Bronze 29.2%, Silver 37.6%, Gold 41.7%, Platinum 50.1%, Diamond 58.4% |
  | VT Controlsphere Viscose | 147 | 0.06% | Cinnabar 24.2%, Vermillion 33.0%, Saffron 39.2%, Celadon 45.5%, Viridian 51.3%, Cerulean 56.7%, Lavender 61.7%, Indigo 67.5%, Fuchsia 73.2% |
  | VT EddieTS Intermediate S5 | 105 | 0.45% | Platinum 35.5%, Diamond 38.3%, Jade 41.1%, Master 43.6% |

- **Checked against the runs themselves.** On VT Controlsphere Viscose the
  latest run, 3,133 at 52.21%, sits above Viridian (3,075, 51.3%), and the PB,
  3,653 at 60.87%, below Lavender (3,700, 61.7%). On VT EddieTS Intermediate
  S5 the PB of 1,020 at 41.09% reached Jade (1,020, 41.1%).
- **The live copy** (the app with its rank-line code patched, on the
  maintainer's stats, headless Edge, light and dark, at 2,560 and 1,536 px):
  the switch starts off and the chart matches today's; turned on, all three
  chart modes draw the figures; a zoom that leaves a line out of view drops
  its figure; each of the three notes shows on a real scenario (VT ww5t
  Intermediate S5, Aimerz+ VAS Easy S1, Air Voltaic Easy) and clears the
  axis title on Score vs Run, and the longest on Score vs Time too; turning
  the switch off restores today's chart.

### Not checked

- **Other players' runs.** One player's stats. A player who lets go in the
  gaps is predicted to get no targets, not observed.
- **Firefox, and 3,840 and 1,920 px.** The mockups were checked in headless
  Edge at 2,560 and 1,536 px.
- **Screen readers.** The figures and the note are chart text, as the rank
  labels are, and weren't probed.
- **Time-scored scenarios.** Their score is the time left, not their hits,
  so their runs are expected to disagree and get the third note; none was
  checked.

## Design

### What the player sees

| State | Chart |
|---|---|
| Switch off (the default) | Today's chart, unchanged |
| On, the scenario has targets | Each drawn rank line gets its figure in the right margin, such as `39.2%` beside `Saffron (2350)` |
| On, no targets | The rank lines as today, and one quiet note under the axis title saying why |
| On, no rank line drawn | Today's chart, unchanged |

### The score at 100%

- **The runs:** the scenario's runs whose `scenario_hash` matches its newest
  run's, with a hit accuracy above zero and a score above zero. Files with
  no `Hash:` line count as one version.
- **Each run's figure:** its score over its hit accuracy.
- **The test:** at least 5 such runs, and at least 90% of their figures
  within 2% of their median. Passing, the median is the score at 100%.
- **The reason when it fails:** fewer than 5 runs and no runs of an older
  version, fewer than 5 runs with runs of an older version, or 5 or more
  that don't agree.
- **A time-scored scenario** scores the time left, not its hits, so its runs
  are expected to disagree and get the third note (not checked).
- **Worked out on every chart build,** from the same snapshot of the store
  the chart's runs come from. Nothing is stored. A run that lands redraws
  the chart, so the figures and the note follow it.
- **The numbers 5, 2% and 90% are author-owned,** set on the measurements in
  [Verified facts](#verified-facts). The tightest held-fire switching
  scenario passes (VT Ground Intermediate S5, 1.5%), and the click scenarios
  measured fail.

### The target

- `threshold / score at 100% × 100`, rounded up to the next tenth, guarded
  against float noise the way `format_percent` is, and written with one
  decimal and a percent sign.
- A rank whose target would be above 100% gets no figure: the player's shots
  can't reach it.
- Each rank is worked out on its own, so a ladder out of order upstream
  doesn't matter.

### The figures

- One per drawn rank line, whichever lines the app draws today: the ranks
  around the plotted scores, or the whole ladder with Show all ranks on. The
  lines and their labels don't change.
- Placed at the plot's right edge, 6 px out, level with the line, in the
  chart's text color for the theme.
- The right margin is 64 px while at least one figure is drawn, and Plotly's
  default otherwise.
- All three chart modes, since they share the rank lines.

### The note

- Under the x axis's title, right-aligned with the plot, 12 px and slightly
  faded, in the chart's text color.
- Only while the switch is on, at least one rank line is drawn, and the
  scenario has no score at 100%. The bottom margin is 112 px then.
- A scenario that has a score at 100% but no rank under 100% shows neither
  figures nor a note.

### The switch

- `dmc.Switch`, id `run-history-accuracy-targets-switch`, in Overlays after
  Show all ranks, `checked=False`, `persistence=True`. Its id and default
  never change, as every remembered control's
  ([2026-10-12](../decision_log/2026/2026-10-12-run-history-keeps-its-own-control-ids-so-every-browser-saw-the-defaults-once.md)).
- An Input of the chart rebuild, as Show all ranks is, threaded through
  `build_run_history_figure` and the three plot functions to the code that
  draws the rank lines. `ChartOptionsIds` gains its id.
- Off, or with Rank thresholds off, it changes nothing.

### Where it lives

Suggested; the implementer owns the shape. A small pure module in
`source/kovaaks/` holds the score at 100%, the reason when there is none, and
the target's rounding, tested on its own. The plot code calls it from the
function that draws the rank lines.

### Copy

Every string this proposal adds. Nothing existing changes.

- The switch: `Accuracy targets`.
- Its help text: `Shows the accuracy each rank needs beside its line, on
  scenarios where your score depends only on your accuracy, such as
  tracking. Needs **Rank thresholds** turned on.` The bold name is built
  with `control_name()`, as Show all ranks' is.
- A figure: `{target}%` with one decimal, such as `39.2%` or `40.0%`.
- The notes:
  - `Accuracy targets show after 5 runs of this scenario.`
  - `Accuracy targets show after 5 runs of this scenario since it was last
    updated.`
  - `This scenario has no accuracy targets, because its score depends on
    more than accuracy.`

The notes name no version: the app shows no scenario version anywhere, so
"since it was last updated" says what changed in the player's words.

### Terms

For [docs/glossary.md](../glossary.md), under Benchmark ranks, after Rank
overlay:

**Accuracy target.** The hit accuracy a run needs to reach a rank's
threshold, on a scenario where the player's score depends only on their
accuracy: the threshold over the score their runs would make at 100%,
rounded up to a tenth of a percent. Known once at least 5 of the scenario's
runs since its last update agree on that score, and unknown otherwise.
- On screen: the figure beside a rank line in the chart's right margin,
  while the Accuracy targets switch is on.
- In code: `accuracy_target`; the score at 100% is `full_accuracy_score`.
- Not the accuracy guideline on the [roadmap](../roadmap.md), which is the
  accuracy top leaderboard players reach.

### Decisions this changes

None is superseded.

- **Extended:** the chart's rank lines
  ([2026-10-12](../decision_log/2026/2026-10-12-the-run-history-chart-plots-every-run-and-draws-no-summary-line.md))
  gain their figures, and the Chart options panel
  ([2026-08-09](../decision_log/2026/2026-08-09-chart-options-live-in-a-collapsible-panel-beside-the-graph.md))
  gains a switch, its eleventh control.
- **Applied:** hit accuracy as the game shows it
  ([2026-10-18](../decision_log/2026/2026-10-18-pb-accuracy-shows-hit-accuracy-as-the-game-does.md)),
  the fixed ids and defaults of remembered controls
  ([2026-10-12](../decision_log/2026/2026-10-12-run-history-keeps-its-own-control-ids-so-every-browser-saw-the-defaults-once.md)),
  and the copy rules
  ([2026-09-14](../decision_log/2026/2026-09-14-app-copy-follows-one-set-of-rules-and-the-em-dash-is-gated-out.md)).
- **Kept as is:** a run's accuracy keeps its two decimals
  ([2026-10-18](../decision_log/2026/2026-10-18-a-runs-accuracy-shows-two-decimals.md));
  a target has one (AT2).

### Alternatives rejected

- **Plotting accuracy instead of score,** the note's first idea. On a
  scenario where score follows accuracy it is the same line with other
  numbers on its axis; on the rest it plots something that doesn't decide
  the rank.
- **Threshold over Damage Possible.** Right where a scenario scores its
  damage, ten times off on VT EddieTS Intermediate S5, and still a run
  figure. It would also bring back the damage parse the 2026-10-18 entry
  removed.
- **A list of scenario types,** **the leaderboard's runs** and **a 3-run
  minimum:** under AT1.
- **Whole percent, nearest rounding, two decimals:** under AT2.
- **In the label, in the rank's color:** under AT3.
- **A second y axis** with ticks at the thresholds: the same place as the
  margin figures, but it needs its range kept matched to the score axis's
  through every zoom, where an annotation tied to the score axis needs
  nothing.
- **The Settings page, and the note as the switch's description:** under
  AT4 and AT5.

## Out of scope

- **The accuracy guideline,** the [roadmap](../roadmap.md)'s accuracy top
  leaderboard players reach. The leaderboard's runs, rejected as AT1's
  source, may serve it.
- **The PB line and the score threshold line** (AT6).
- **The rank labels printing over the PB and score threshold labels** when
  their values are close, as Jade and the PB do at 1,020 on VT EddieTS
  Intermediate S5. It happens today, with or without the figures.
- **Targets anywhere else:** the run list, the cards, the PB card's next
  rank, the playlist's scenario table.
- **Click and switching scenarios played without held fire,** which by
  AT1 get no targets.

## Delivery plan

Stated intent, not a contract; a PR that moves a boundary says so in its
description.

- **One PR, gated on AT1 to AT6:** the module and its tests, the switch, the
  figures and the note on all three chart modes, and the shipping checklist:
  the Run History spec's chart and Chart options sections, a decision-log
  entry per durable decision, the glossary entry from Terms, the roadmap,
  product.md, and deleting this proposal.
- **Why one.** The switch is all a player sees of the rule, and the rule is
  small; a split would ship a switch with nothing behind it, or a rule with
  no way to see it.

## Testing

- **Unit, the score at 100%:** agreeing runs give their median; one run in
  ten outside 2% still passes, two don't; 4 runs give the first reason, 4
  since an update with older runs the second, 5 that disagree the third;
  zero accuracy and zero score are skipped; files with no hash count as one
  version.
- **Unit, the target:** rounding up to the next tenth, an exact tenth kept
  (`40.0`), float noise at a tenth's edge, a target above 100% left out.
- **Unit, the figure:** switch off adds nothing and leaves the margins
  alone; on, one figure per drawn rank line and none for undrawn ones, the
  right margin set; Show all ranks gives every rank one; no score at 100%
  gives the note with its reason and the bottom margin; no rank line drawn
  gives neither; each chart mode.
- **The callback and panel:** the switch is an Input of the chart rebuild,
  starts off, and persists; Chart options lists it after Show all ranks.
- **Browser** (headless Edge, then the maintainer's Firefox), both themes, at
  3,840, 2,560, 1,920 and 1,536 px: figures level with their lines and
  inside the figure's edge; the note clear of the axis title in Score vs Run
  and Score vs Time; a zoom drops out-of-view figures.
- **Gates:** pytest, ruff format and lint, mypy, compileall, as AGENTS.md
  lists.
