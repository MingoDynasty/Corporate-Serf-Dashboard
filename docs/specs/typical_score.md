# Typical score

The typical score defines what a player's runs on a scenario usually score.
It uses the median of the last twenty runs, with a minimum before the value
is known and a separate test of how recent its runs are.
The definition and its display rounding are pure functions; the Run History
chart draws the value, Scenario Stats leads with it, and the playlist
scenario table ranks by it, each marking it where it isn't recent.
Stats files with non-finite scores are skipped during import so malformed
scores cannot stop a calculation.

## Supporting runs and existence

- A scenario is its name. Every sensitivity, scenario version and warm-up
  run counts, including a run with no version hash. Versions are treated as
  comparable even when a rework changes the scoring scale
  ([TS1][typical-definition]).
- The CSV parser skips a stats file whose score is NaN or infinite, including
  numeric overflow to infinity. It never enters the run store or a supporting
  window. Finite scores, including zero and negative scores, are retained.
- After each run, the supporting window is that scenario's last 20 runs up
  to and including it, or all of its runs if it has fewer, at any age
  ([TS1][typical-definition]).
- Runs follow `play_sessions.in_play_order`: end time, then start time,
  then scenario name, then stats file name. A run with no usable start uses
  its end for that tie break.
- A value is known when its window has at least 10 runs from at least 2 play
  sessions, or 20 runs from any number of sessions
  ([TS1][typical-definition]).
- Sessions are split over every scenario's runs. Runs on other scenarios
  can join two runs of this scenario into one session, but are never scores
  in this scenario's window
  ([TS1][typical-definition]).
- Once known, a value stays known without a stored flag: below 20 runs the
  whole history stays in the window, and every full 20-run window qualifies
  ([TS1][typical-definition]).
- Before the minimum, the run and session counts and dates are available,
  `known` is false, and the score statistics are `None`. Unknown is never
  read as weak. An empty history returns no values
  ([TS1][typical-definition]).

## Unrounded statistics

- The value is the supporting scores' median. An even count uses the mean
  of its two middle scores
  ([TS1][typical-definition]).
- P25 and P75 are the first and third values of
  `statistics.quantiles(scores, n=4, method="inclusive")`
  ([TS4][typical-bands]).
- P10 and P90 are the first and last values of its `n=10` counterpart.
  Both sets interpolate between scores
  ([TS4][typical-bands]).
- Calculations use `Decimal(str(run.score))` and return unrounded floats.
  Decimal arithmetic keeps a decimal half intact for display rounding:
  the median of 2.3 and 2.4 is 2.35 rather than 2.3499999999999996.
- No display rounding changes these statistics. There is no age cutoff in
  the value and no previously known value carried in place of a new one
  ([TS1][typical-definition], [TS6][typical-recency]).

## Recency and holds

- At a supplied moment, a known value is recent when at least 10 of its
  supporting runs ended in the 30 days up to and including that moment.
  A run exactly 30 days old counts. A run after the moment does not count
  ([TS6][typical-recency]).
- Recency also returns the number of recent supporting runs and how many
  sessions they belong to, including zero counts. Sessions impose no
  recency minimum. An unknown value cannot be recent
  ([TS6][typical-recency]).
- A recent value can still hold up to 10 older runs in its 20-run window.
  An old value remains known even when none of its runs are recent
  ([TS6][typical-recency]).
- For a hold at or after its newest run, the recency boundary is the end
  of its tenth-newest supporting run plus 30 days. The value is recent at
  the boundary itself and not recent strictly after it. An already old
  value's boundary is in the past; an unknown value has no boundary
  ([TS3][typical-chart], [TS6][typical-recency]).
- Times are local wall-clock times from the stats files, with the judging
  moment supplied by the caller. The module reads no clock.

## Display rounding

- `format_typical_score` in `source/kovaaks/typical_score.py` formats a
  median or percentile using the most decimal places of any score in its
  supporting window, capped at two. Whole-number scores have zero decimal
  places, including scores held as floats ending in `.0`
  ([TS1][typical-definition]).
- It quantizes `Decimal(str(score))` with `ROUND_HALF_UP`, then uses the
  shared `format_score` formatting for thousands separators and removal of
  trailing zeros. A whole-score window's median of 2140.5 reads `2,141`;
  a one-decimal window's 1.25 reads `1.3`; a six-decimal window's 2.145
  reads `2.15`
  ([TS1][typical-definition]).
- Only the current supporting window chooses precision. Empty supporting
  runs are rejected with `ValueError`
  ([TS1][typical-definition]).
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
  `TYPICAL_SCORE_RECENT_AGE` (30 days). There are no settings for them
  ([TS1][typical-definition], [TS6][typical-recency]).
- No value is cached or persisted.
- The Run History chart is a caller. On Score vs Run and Score vs Time it
  builds every value of the scenario's history, keeps the plotted runs'
  values, and judges each at its own run. On Score vs Time it also holds
  each value to the next run and splits the hold at
  `typical_score_fade_time` ([TS3][typical-chart]). What it draws is in
  [run_history.md](run_history.md#the-chart).
- Scenario Stats builds the scenario's newest value from one whole-store
  snapshot and judges its recency as of now, on scenario changes, arriving
  runs and the page's 30-second tick. Its lead and hover use this module's
  rounding and both bands, independently of the chart's switches
  ([TS5][typical-card-value], [TS8][typical-card-lead]). The card is specified
  in [run_history.md](run_history.md#scenario-stats).
- `typical_score_hover(value, total, moment)` and `below_minimum_text(value)`
  word a value's hover: the opening sentence and the Runs, Recent, Middle 50%
  and Middle 80% lines, or what an unknown value needs. Scenario Stats and the
  scenario table both draw from them, so the two hovers can't drift apart.
- The playlist scenario table is a caller. Each table build takes one
  whole-store snapshot, builds every listed scenario's newest value from it,
  and judges recency once, at the moment it was taken; the cells don't change
  until the page reopens. It ranks the value on a benchmark's ladder and
  marks one that isn't recent with a clock
  ([2026-10-22][typical-table]). The columns are specified in
  [playlists.md](playlists.md#the-per-playlist-scenario-table).

[typical-table]: ../decision_log/2026/2026-10-22-the-scenario-table-shows-the-typical-score-beside-the-pb-columns.md

[typical-definition]: ../decision_log/2026/2026-10-15-typical-score-uses-the-last-twenty-runs-and-counts-every-version.md

[typical-chart]: ../decision_log/2026/2026-10-18-the-typical-score-is-drawn-after-each-run.md

[typical-bands]: ../decision_log/2026/2026-10-18-two-percentile-bands-show-the-typical-scores-spread.md

[typical-card-value]: ../decision_log/2026/2026-10-18-scenario-stats-shows-the-newest-typical-score-at-any-age.md

[typical-recency]: ../decision_log/2026/2026-10-20-a-typical-score-is-recent-with-ten-runs-from-the-last-thirty-days.md

[typical-card-lead]: ../decision_log/2026/2026-10-20-scenario-stats-leads-with-the-typical-score.md
