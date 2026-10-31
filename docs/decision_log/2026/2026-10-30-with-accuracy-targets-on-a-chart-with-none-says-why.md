# 2026-10-30: With Accuracy Targets On, A Chart With None Says Why

Status: Accepted

When the Accuracy targets switch is on and the chart draws rank lines but no
target, a quiet line under the chart's x axis title says why. It names one of
five reasons, from a scenario scored by completion time to every rank being
estimated above 100%. The chart grows its bottom margin to hold the note, so
the plot is 32 px shorter while it shows.

**Ruling.** AT5 of
[proposal #449](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/449),
ratified by the maintainer on 2026-10-30 ("I ratify"), as amended in
review. No lean was recorded before that. Review added the time-scored note
and the above-100% note, and moved the notes from diagnosing the scenario to
stating what the app measured. Shipped in
[#452](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/452).
What the chart does today is in
[run_history.md](../../specs/run_history.md#the-chart).

**The note** (`_add_accuracy_targets_note` in `source/plot/plot_service.py`):

- Shows only while the switch is on and at least one rank line is drawn,
  and either the scenario has no
  [score at 100%](2026-10-30-accuracy-targets-are-estimated-from-the-players-own-runs-where-at-least-5-agree.md)
  or every drawn rank's target is above 100%. Nothing shows when no rank
  line is drawn.
- One note at a time, in the order the reasons are checked:
  - "This scenario has no accuracy targets, because it's scored by
    completion time."
  - "Accuracy targets need at least 5 runs of this scenario."
  - "Accuracy targets need at least 5 runs of this scenario since it was
    last updated."
  - "This scenario has no accuracy targets, because your scores here don't
    follow your accuracy closely enough."
  - "Every rank on the chart has an estimated accuracy target above 100%."
- An annotation at `x=1`, `xref="paper"`, `xanchor="right"`, `y=0`,
  `yref="paper"`, `yanchor="top"`, `yshift=-82`, font size 12, opacity 0.8,
  in the theme's text color, and the figure's bottom margin is 112 px, from
  Plotly's default 80, while it shows.

**Why.**

- **Say anything.** With no note, the switch looks broken on most click
  scenarios. The reason also tells the player whether playing more could
  bring targets.
- **What the notes claim.** What the app measured, not what the scenario
  is. The count notes state a minimum, since a fifth run can still
  disagree. The disagreement note is about the player's scores, since a
  player who fires differently can get targets on the same scenario. The
  above-100% note says "estimated": a run that fires more than the median
  can reach such a rank. The notes name no version, since the app shows no
  scenario version anywhere, and "scored by completion time" is the phrase
  Chart options' help text already uses.
- **Under the axis title.** Beside it, the longest note ran into the title
  in a 1,536 px window. Score vs Time's dates take two lines and push its
  title lowest, so the note drops 82 px below the plot on every mode.
- **Not in Chart options,** as the switch's description. Chart options
  starts closed on every visit, so the note would be hidden whenever the
  player moves to another scenario with the panel shut.
