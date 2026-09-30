# Glossary

The words the app uses for its own concepts, and what each one means, for
anyone writing the app's copy, its docs, or its code. An entry gives the
meaning first, then the on-screen wording and the code name wherever they
differ from the term. Which words may appear on screen is copy rule 7 in
[AGENTS.md](../AGENTS.md#styling-conventions); this file says what they mean.

A term is here only once the app, or [product.md](product.md), has its
concept. Words for work still being designed stay in that work's proposal,
whose **Terms** block the shipping PR moves here
([Shipping a proposal](../AGENTS.md#shipping-a-proposal-docs-definition-of-done)).
Any PR that makes an entry untrue corrects it in the same PR
([Documentation Habits](../AGENTS.md#documentation-habits)).

## Play

### Scenario

A KovaaK's aim-training exercise, identified by its exact name. Runs, PBs,
positions, and ranks each belong to one scenario.

### Run

One finished attempt at a scenario. The app knows a run by its stats file:
each `.csv` file KovaaK's writes to the stats folder is one run, and play that
writes no file never reaches the app.

- On screen: run file for the stats file, as in the Run not recorded toast.

### Stats folder

The KovaaK's folder of stats files that the app reads every run from
([2026-08-02](decision_log.md#2026-08-02-restart-scoped-settings-are-pinned-at-boot-and-the-stats-folder-finds-itself)).

- In code: `stats_dir`.

### Sensitivity

The mouse sensitivity a run was played at, read from its stats file. A
scenario's runs are grouped by it: the Score vs Sensitivity chart and top-N
placement both compare runs within one sensitivity.

- In code: a value and a scale, `horizontal_sens` and `sens_scale`. A group's
  key joins the two, such as `34.6 cm/360`.

### cm/360

The scale the app shows sensitivity in: centimeters of mouse travel per full
360-degree turn, so higher is slower. A run recorded on a game's own scale is
converted when its file is read. A run whose file lacks fields the conversion
can use, as the oldest files do, keeps its game's scale and the number as
recorded
([2026-09-11](decision_log.md#2026-09-11-sensitivities-normalize-to-cm360-at-parse-time-from-the-files-own-increment-and-dpi),
[2026-09-27](decision_log.md#2026-09-27-sensitivity-precision-is-fixed-per-scale-and-its-config-knob-is-retired)).

### Session

One stretch of play, including the pauses between runs, as
[product.md](product.md#when-they-ask-them) defines it. The app has no rule
yet for where one session ends; the first feature that needs one sets it.

- Not an app session, which the specs use for one run of the server process.

### In session and between sessions

The two moments the app is used in
([product.md](product.md#when-they-ask-them)). In session, the player glances
at the app between runs while KovaaK's runs fullscreen, so an answer has to
work at a glance. Between sessions, before or after one, they look back at how
they're doing and ahead to what to train, usually with more attention to give.

## Playlists

### Playlist

A named, ordered list of scenarios, identified by its playlist code. The word
covers benchmarks too: the Playlists page, the Playlist filter, and
`PlaylistData` hold both kinds. Where the two must be told apart, a playlist
is the kind without rank data, and the Playlists page's Type column reads
Playlist or Benchmark
([2026-07-03](decision_log.md#2026-07-03-import-benchmarks-from-evxl-and-kovaaks)).

### Benchmark

A playlist whose scenarios carry rank ladders, so a scenario's PB earns a
rank. The app ships its benchmarks as the bundled library that the benchmark
importer generates, while a playlist imported by playlist code carries no rank
data
([2026-07-03](decision_log.md#2026-07-03-import-benchmarks-from-evxl-and-kovaaks)).

- In code: `is_benchmark_playlist`, true when any scenario has `ranks`.

### Playlist code

KovaaK's identifier for a playlist. The app uses it as the playlist's
identity, because names aren't unique: imports, duplicate checks, and the
`/playlists/{code}` address all key on it
([2026-07-07](decision_log.md#2026-07-07-use-playlist-codes-as-playlist-identity)).

- On screen: playlist code. KovaaK's own name for it, share code, appears in
  the import help.
- In code: `code` on `PlaylistData`, and `playlist_code` elsewhere.

## Leaderboard standing

### Position

The player's placement on a scenario's global KovaaK's leaderboard, such as
11,290. Fetching it is a position lookup. A player with no leaderboard
entry is Unranked, KovaaK's own word
([2026-07-06](decision_log.md#2026-07-06-one-word-per-concept-in-leaderboard-verbiage)).

- In code: `rank`, as in `ScenarioRankInfo.rank`, the `rank_display` and
  `rank_sort` row fields, the rank cache, and its
  `scenario_rank_cache_ttl_hours` setting. The 2026-07-06 rename changed
  labels only, so identifiers kept the old word.
- Not Rank, which is the benchmark tier.

### Total players

How many players a scenario's leaderboard holds, the denominator of the
percentile. The Position readout gives it after "of", as in 11,290 of 63,892.

### Percentile

The share of a scenario's leaderboard the player places above, as a
percentage, so higher is better. It's derived from position and total players
by the midpoint formula (total players − position + 0.5) ÷ total players ×
100, so first of one reads 50.00%, and it's never stored
([2026-04-27](decision_log.md#2026-04-27-use-the-midpoint-percentile-formula)).

### From cache

Marks a value on screen that came from the app's local cache because fetching
a fresh one failed, such as a position shown while KovaaK's is unreachable.
Values are served from the cache routinely without the label; it marks only a
failed fetch
([2026-07-12](decision_log.md#2026-07-12-rank-fetch-failure-degrades-to-the-last-cached-rank)).

- On screen: the ` · from cache` hint on the Position field, a playlist's
  `4 of 40 positions from cache · KovaaK's unreachable`, and the Refresh
  toasts.
- In code: `served_stale`, and the fill's `stale_count`.

## Benchmark ranks

### Rank

The benchmark tier a scenario's PB has reached, such as Gold. Each benchmark
scenario has a ladder of ranks, each with a name, a color, and a score
threshold. The PB has reached a rank when it meets that rank's threshold and
every threshold below it, and below the first rank it reads No rank. Ranks
come from the bundled benchmark files and the local PB, so they need no
username or network
([2026-07-06](decision_log.md#2026-07-06-one-word-per-concept-in-leaderboard-verbiage),
[2026-09-27](decision_log.md#2026-09-27-benchmark-tables-show-each-scenarios-rank-and-the-gap-to-the-next-one)).

- On screen: the Rank column on a benchmark's scenario table.
- In code: the row fields are `tier_display` and `tier_sort`, because `rank_*`
  already holds the position. The ladder is `Scenario.ranks`, a list of `Rank`
  models, and there *rank* does mean the tier.
- Not Position, and No rank is not Unranked: No rank is below the first tier,
  Unranked is no leaderboard entry, and one row can show both.

### Next Rank gap

How much a benchmark scenario's PB has to grow to reach its next rank, as a
percentage of the PB, such as +4.8% to Gold. It's rounded up, so a gap that
remains never reads as reached, and its hover gives the next threshold and the
points still needed. With every rank reached it reads Top rank
([2026-09-27](decision_log.md#2026-09-27-benchmark-tables-show-each-scenarios-rank-and-the-gap-to-the-next-one)).

- On screen: the Next Rank column.
- In code: `next_tier_display`, `next_tier_sort` (the unrounded gap), and
  `next_tier_tooltip`.

### Rank overlay

The chart's rank threshold lines for the selected scenario, when the selected
playlist has rank data. By default it draws only the ranks around the plotted
scores; Show all ranks draws the whole ladder.

- On screen: the Rank thresholds switch in the Overlays group of Chart
  options, with the Show all ranks switch under it.
- In code: `rank-overlay-switch`.

## Scores and notifications

### PB

Personal best: the highest score among a scenario's runs, whatever their
sensitivity. It's the player's own record from the stats folder, not their
leaderboard score
([2026-07-06](decision_log.md#2026-07-06-one-word-per-concept-in-leaderboard-verbiage)).

- On screen: PB, as the prefix of the PB run's stats (PB Score, PB Date, PB
  cm/360, PB Accuracy) and in a run notification's `% of PB`. Prose says
  personal best.
- In code: `high_score`, as in `ScenarioStats.high_score` and the
  `high_score_*` row fields. A run's `scenario_previous_best` is the PB it was
  chasing.

### Accuracy

The share of a run's shots that hit, which is what the chart's point hover
shows. PB Accuracy on a scenario table is damage accuracy instead, damage done
over damage possible, whenever the run's file records it, so one run can show
two different accuracies.

- In code: `accuracy` (hits over shots) and `damage_accuracy` on `RunData`.

### Score threshold

A score goal set as a percentage of the PB, 95% by default. Its chart line
follows the current PB, while a run notification judges a run against the PB
it was chasing, so a goal above 100% can pass
([2026-07-08](decision_log.md#2026-07-08-judge-score-threshold-notifications-against-the-previous-pb)).

- On screen: the Score Threshold group in Chart options, and the Threshold
  passed and Below threshold toasts.
- Not a rank's threshold, which comes from a benchmark file.

### Top-N placement

Where a new run's score places among the scenario's runs at the same
sensitivity: first place is best, and the rest are Nth-best, such as 2nd-best.
A placement within the Top N scores value earns a run notification.

- On screen: the Top N scores control and toasts such as New 2nd-best score.
  The control also sets how many of the best scores in the selected date
  range the chart plots: per sensitivity in Score vs Sensitivity, and per
  day, across sensitivities, in Score vs Time.
- In code: `nth_score` and `top_n_scores`.

### Run notification

The one toast a run can earn on Scenario Performance: a score threshold
verdict, a top-N placement, or both in one toast. A run that earns neither
shows up only as its point on the chart. The run the personal best
celebration picks, if any, gets that instead
([2026-08-03](decision_log.md#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy),
[2026-08-21](decision_log.md#2026-08-21-run-notifications-have-a-master-switch-and-the-threshold-switch-is-renamed)).

- On screen: the Run notifications switch in Chart options.
- In code: the `run-verdict` toast channel and `run-notification-switch`.

### Personal best celebration

The response to a new PB: a short animation and a New personal best toast
that stays until dismissed, on whatever page is open and for any scenario. It
picks at most one run from each delivery of new runs: the newest one that beat
its scenario's previous PB and landed no more than about two minutes before
the delivery. An older PB in the same delivery gets at most an ordinary run
notification, and a PB delivered later than that gets no toast. A tie doesn't
celebrate, and neither does a scenario's first run
([2026-09-02](decision_log.md#2026-09-02-a-new-personal-best-celebrates-on-every-page),
[notifications.md](specs/notifications.md#run-notifications)).

- On screen: the Personal best celebration control under Celebrations on the
  Settings page, which picks the animation, or turns the celebration off,
  toast included.
- In code: the `pb-celebration` toast channel.
