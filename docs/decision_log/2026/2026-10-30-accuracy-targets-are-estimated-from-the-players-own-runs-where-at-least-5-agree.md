# 2026-10-30: Accuracy Targets Are Estimated From The Player's Own Runs, Where At Least 5 Agree

Status: Accepted

Each rank line on the Run History chart can show the hit accuracy that rank
needs, worked out from the player's own runs of the scenario since its last
update. A run's score over its accuracy is the score it would have made at
100%, and when at least 5 runs agree on that figure, their median turns each
rank's threshold into a target. A target is an estimate for a run with the
fire button held throughout, so a scenario whose runs disagree, or that the
app knows is scored by completion time, gets none.

**Ruling.** AT1 of
[proposal #449](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/449),
ratified by the maintainer on 2026-10-30 ("I ratify"), as amended in review.
Before that, their choice of source, between the player's own runs and the
leaderboard's: "Yes, own runs". Their direction on what a target assumes: "I
think we should simplify this and assume that Mouse 1 is held for the
duration of the run." Their choice between keeping the agreement test and a
rule with none: "Keep the 5-run test". The 5-run minimum, the agreement test
and the time-scored exclusion were the author's. Shipped in
[#452](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/452).
What the chart does today is in
[run_history.md](../../specs/run_history.md#the-chart).

**The rule** (`full_accuracy_score` in `source/kovaaks/accuracy_target.py`):

- **Time-scored first.** A version the app recognizes as time-scored has no
  score at 100%, whatever its runs, by
  [the per-version recognition](2026-10-05-time-scored-scenarios-are-measured-by-pace.md).
  A version it can't tell about is judged by the test alone.
- **The runs.** The scenario's runs whose `Hash:` matches its newest run's,
  with a hit accuracy above zero and a score above zero. Files with no
  `Hash:` line count as one version.
- **Each run's figure.** Its score over its hit accuracy: the score it would
  have made at 100% with the same shots.
- **The test.** At least 5 such runs, and at least 90% of their figures
  within 2% of their median, counted in whole runs (`10 × agreeing ≥ 9 ×
  runs`): 5 to 9 runs must all agree, 10 to 19 may have one outside, 20 to
  29 two. Passing, the median is the score at 100%, and a rank's target is
  its threshold over it ([AT2's entry](2026-10-30-an-accuracy-target-shows-a-tenth-of-a-percent-rounded-up.md)
  rounds it).
- **The reason when there is none,** the first that applies: time-scored;
  fewer than 5 runs and no runs of an older version; fewer than 5 with runs
  of an older version; 5 or more that don't agree. Each has its note
  ([AT5's entry](2026-10-30-with-accuracy-targets-on-a-chart-with-none-says-why.md)).
- **Worked out on every chart build,** over the scenario's whole history in
  the chart's own snapshot of the store, never the plotted range, so the
  figures don't move as the range does. Nothing is stored, and a run that
  lands redraws the chart. The time-scored check asks
  `get_version_pace_basis` about the snapshot's newest version. The
  proposal named `get_pace_basis`, which gives the same answer for the
  current version but reads the store again, where a run landing mid-build
  could make it answer for a version the snapshot doesn't hold.

**What a target promises.**

- An estimate for a run with the median run's shots, assuming the fire
  button is held for the whole run, as on tracking. The assumption changes
  how a target is described, not how it is worked out.
- The test checks for steady shots, the nearest the stats file comes to
  showing held fire. It doesn't prove held fire: a player who clicks at a
  pace steady enough to pass gets figures for that pace.
- Shots vary a little even with the button held. A run that fires fewer
  than the median run needs more accuracy than its target, and one that
  fires more needs less. Over the 3,437 runs behind the maintainer's 90
  scenarios with targets (2026-10-30), a run cleared a rank's target and
  missed the rank 20 times, on 16 scenarios, and reached a rank under its
  target 69 times, on 25.

**Why.**

- **The player's runs, not a list of scenario types.** Whether a score
  follows accuracy depends on how the fire button is used, not on the
  genre. Held-fire switching agrees: within 0.45% on VT EddieTS Intermediate
  S5 and 1.5% on VT Ground Intermediate S5. A player who lets go between
  bots fires fewer shots on some runs than others, so their runs disagree
  and they get none.
- **5 runs.** Over the maintainer's 148 scenario versions whose runs
  disagree, judged on 8 or more runs, 15 passed the test on their first 3
  runs and 5 on their first 5. On the 123 whose runs agree, a 5-run window
  failed 2.0% of the time.
- **2% and 90%.** The tightest held-fire switching scenario measured, VT
  Ground Intermediate S5 at 1.5%, passes, and the click scenarios measured
  fail: VT ww5t Intermediate S5 spreads 5.2%. The loosest that passes, VT
  Penta Bounce Intermediate S5, spreads 2.6% with 90% of its runs within 2%
  of the median.
- **Since the last update.** An update can change a scenario's length, and
  so its shots.
- **Never time-scored.** A countdown's score can agree across a steady
  player's runs without following accuracy. Of the 10 time-scored versions
  the app recognizes on the maintainer's stats, Air CELESTIAL No UFO Medium
  passes on 2 of its 33 five-run windows, and Air Pure Medium on 1 of 18.
- **Coverage,** with the bundled ladders on the maintainer's stats
  (2026-10-30): of 659 ranked scenarios with runs, 90 get targets, 426 have
  fewer than 5 runs, 8 more have fewer than 5 since their last update, 125
  have runs that disagree, and 10 are time-scored.

**Rejected.**

- **The leaderboard's runs.** They would work on scenarios the player never
  played, but need KovaaK's to answer before the chart can draw, rely on a
  field the app has only observed, and measure how others fire.
- **The rank data, or Damage Possible.** A ladder holds scores only. Damage
  Possible is one run's shots times its damage per shot, so it is a run
  figure in damage, not score: on VT EddieTS Intermediate S5, which scores
  10 points per point of damage, Jade's 1,020 over it reads 410.9%.
- **One run's ratio.** One run can't show steady shots, so on a click
  scenario it would draw a figure that means nothing.
- **A 3-run minimum,** which would give 129 scenarios targets rather than
  90, many of them briefly. **A higher minimum or a tighter test,** to make
  the targets exact: neither shows how a scenario scores, because no file
  says.
