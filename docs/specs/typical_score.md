# Typical score

The typical score defines what a player's runs on a scenario usually score.
It uses the median of the last twenty runs, with a minimum before the value
is known and a separate test of how recent its runs are.
The definition and its display rounding are pure functions, and the Run
History chart draws the value on Score vs Run, and Scenario Stats leads
with it, each faded or dimmed where it isn't recent.
Stats files with non-finite scores are skipped during import so malformed
scores cannot stop a calculation.

## Supporting runs and existence

- A scenario is its name. Every sensitivity, scenario version and warm-up
  run counts, including a run with no version hash. Versions are treated as
  comparable even when a rework changes the scoring scale.
- The CSV parser skips a stats file whose score is NaN or infinite, including
  numeric overflow to infinity. It never enters the run store or a supporting
  window. Finite scores, including zero and negative scores, are retained.
- After each run, the supporting window is that scenario's last 20 runs up
  to and including it, or all of its runs if it has fewer, at any age.
- Runs follow `play_sessions.in_play_order`: end time, then start time,
  then scenario name, then stats file name. A run with no usable start uses
  its end for that tie break.
- A value is known when its window has at least 10 runs from at least 2 play
  sessions, or 20 runs from any number of sessions.
- Sessions are split over every scenario's runs. Runs on other scenarios
  can join two runs of this scenario into one session, but are never scores
  in this scenario's window.
- Once known, a value stays known without a stored flag: below 20 runs the
  whole history stays in the window, and every full 20-run window qualifies.
- Before the minimum, the run and session counts and dates are available,
  `known` is false, and the score statistics are `None`. Unknown is never
  read as weak. An empty history returns no values.

## Unrounded statistics

- The value is the supporting scores' median. An even count uses the mean
  of its two middle scores.
- P25 and P75 are the first and third values of
  `statistics.quantiles(scores, n=4, method="inclusive")`.
- P10 and P90 are the first and last values of its `n=10` counterpart.
  Both sets interpolate between scores.
- Calculations use `Decimal(str(run.score))` and return unrounded floats.
  Decimal arithmetic keeps a decimal half intact for display rounding:
  the median of 2.3 and 2.4 is 2.35 rather than 2.3499999999999996.
- No display rounding changes these statistics. There is no age cutoff in
  the value and no previously known value carried in place of a new one.

## Recency and holds

- At a supplied moment, a known value is recent when at least 10 of its
  supporting runs ended in the 30 days up to and including that moment.
  A run exactly 30 days old counts. A run after the moment does not count.
- Recency also returns the number of recent supporting runs and how many
  sessions they belong to, including zero counts. Sessions impose no
  recency minimum. An unknown value cannot be recent.
- A recent value can still hold up to 10 older runs in its 20-run window.
  An old value remains known even when none of its runs are recent.
- For a hold at or after its newest run, the recency boundary is the end
  of its tenth-newest supporting run plus 30 days. The value is recent at
  the boundary itself and not recent strictly after it. An already old
  value's boundary is in the past; an unknown value has no boundary.
- Times are local wall-clock times from the stats files, with the judging
  moment supplied by the caller. The module reads no clock.

## Display rounding

- `format_typical_score` in `source/kovaaks/typical_score.py` formats a
  median or percentile using the most decimal places of any score in its
  supporting window, capped at two. Whole-number scores have zero decimal
  places, including scores held as floats ending in `.0`.
- It quantizes `Decimal(str(score))` with `ROUND_HALF_UP`, then uses the
  shared `format_score` formatting for thousands separators and removal of
  trailing zeros. A whole-score window's median of 2140.5 reads `2,141`;
  a one-decimal window's 1.25 reads `1.3`; a six-decimal window's 2.145
  reads `2.15`.
- Only the current supporting window chooses precision. Empty supporting
  runs are rejected with `ValueError`.
- How many decimal places a score was recorded with is remembered by score,
  for the life of the process and up to 4,096 scores, because the chart
  formats several statistics over the same runs at every point.

## API and snapshot ownership

- `build_typical_scores(runs, play_sessions)` returns one frozen
  `TypicalScore` per scenario run, in play order. It retains each window's
  runs and parallel build-local session IDs, its statistics, run and
  session counts, and first and last run-end dates. It changes neither input.
- `typical_score_recency(value, moment)` returns a frozen
  `TypicalScoreRecency` with `recent`, `run_count` and `session_count` for
  the recent subset. The value itself is unchanged.
- `typical_score_fade_time(value)` returns the inclusive boundary above,
  or `None` for an unknown value.
- The caller takes one copy of the whole run store, splits that copy with
  `split_into_play_sessions`, and takes the scenario's runs from the same
  copy. A run missing from the supplied sessions is rejected with
  `ValueError`; the module never invents a session for it.
- The fixed constants are `TYPICAL_SCORE_WINDOW_RUNS` (20),
  `TYPICAL_SCORE_MIN_RUNS` (10), `TYPICAL_SCORE_MIN_SESSIONS` (2), and
  `TYPICAL_SCORE_RECENT_AGE` (30 days). There are no settings for them.
- No value is cached or persisted.
- The Run History chart is a caller: on Score vs Run it builds
  every value of the scenario's history, keeps the plotted runs' values, and
  judges each at its own run. What it draws is in
  [run_history.md](run_history.md#the-chart).
- Scenario Stats builds the scenario's newest value from one whole-store
  snapshot and judges its recency as of now, on scenario changes, arriving
  runs and the page's 30-second tick. Its lead and hover use this module's
  rounding and both bands, independently of the chart's switches. The
  card is specified in [run_history.md](run_history.md#scenario-stats).
