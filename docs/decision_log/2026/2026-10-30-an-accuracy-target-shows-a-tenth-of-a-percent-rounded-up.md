# 2026-10-30: An Accuracy Target Shows A Tenth Of A Percent, Rounded Up

Status: Accepted

An accuracy target always shows one decimal, rounded up to the next tenth,
such as 39.2% for a rank that needs 39.16%. Rounding up means a run with the
median run's shots that reaches the figure reaches the rank. A rank whose
target would be above 100% shows no figure.

**Ruling.** AT2 of
[proposal #449](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/449),
ratified by the maintainer on 2026-10-30 ("I ratify"). Before that, their
direction, 2026-10-29: "Keep rounding up, but also we should have at least
1 decimal of precision. There can be a huge difference in saying "50.1%" vs
"51%"." Their choice, 2026-10-30, between a bare figure and one marked `≈`:
"Bare, 39.2%". Shipped in
[#452](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/452).
What the chart does today is in
[run_history.md](../../specs/run_history.md#the-chart).

**The rule** (`accuracy_target` in `source/kovaaks/accuracy_target.py`):

- The threshold over the
  [score at 100%](2026-10-30-accuracy-targets-are-estimated-from-the-players-own-runs-where-at-least-5-agree.md),
  times 100, rounded up to the next tenth, and written with one decimal and
  a percent sign: `{target:.1f}%`. No approximation mark.
- Float noise is stripped before rounding up, as `format_percent` does
  (`round(…, 6)` inside `math.ceil`): 28.8 over 60 is exactly 48%, and reads
  48.0%, not 48.1%.
- A target above 100% gets no figure; exactly 100% reads `100.0%`. That
  says the rank is out of reach at the median run's shots, not that no run
  can reach it: a run that fires more than the median can reach a rank
  estimated a little above 100%, and may already have.
- A threshold at or below zero reads `0.0%`. Seven bundled ranks have a
  threshold of 0, and a run with no hits reaches them; a figure below zero
  would mean nothing. The proposal didn't foresee this case.
- Each rank is worked out on its own, so a ladder out of order upstream
  doesn't matter.

**Why.**

- **Up.** A run with the median run's shots that reaches the figure
  reaches the rank, where a figure rounded down could leave it a little
  short. The first mockup's whole percent, also rounded up, read 42% for
  Jade on VT EddieTS Intermediate S5, where the PB reached Jade at 41.09%;
  a tenth reads 41.1%.
- **Not two decimals,** as a run's accuracy has
  ([2026-10-18](2026-10-18-a-runs-accuracy-shows-two-decimals.md), which
  stands). The runs behind a target spread by up to 2%, 0.8 point at 40%,
  so a second decimal would claim more than the runs agree on.
- **No approximation mark,** such as `≈39.2%`. The switch's help text says
  the figures are estimates, the player turns the switch on to see them,
  and a mark on each of up to nine lines adds back clutter.
