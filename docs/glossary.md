# Glossary

The words the app uses for its own concepts, and what each one means, for
anyone writing the app's copy, its docs, or its code. An entry gives the
meaning first, then the on-screen label and the word the code uses, wherever
they differ from the term. It says nothing about how the app computes or lays
anything out; that lives in the capability specs, and an entry links the one
that holds its mechanics.
Which words may appear on screen is copy rule 7 in
[AGENTS.md](../AGENTS.md#styling-conventions); this file says what they mean.

A term is here only once the app, or [product.md](product.md), has its
concept. Words for work still being designed stay in that work's proposal,
whose **Terms** block the shipping PR moves here
([Shipping a proposal](../AGENTS.md#shipping-a-proposal-docs-definition-of-done)).
Any PR that makes an entry untrue corrects it in the same PR
([Documentation Habits](../AGENTS.md#documentation-habits)).

## Play

### Scenario

A KovaaK's aim-training exercise, identified by its name. Runs, PBs,
positions, and ranks each belong to one scenario.

### Time-scored scenario

A scenario scored by the time left on its clock when the task is done, so a
faster finish scores higher. On one, the app measures by pace instead of
score wherever it can measure pace reliably
([2026-10-05](decision_log.md#2026-10-05-time-scored-scenarios-are-measured-by-pace)).
How it recognizes one, and when it can't measure pace, is in
[scenario_performance.md](specs/scenario_performance.md#time-scored-scenarios).

- On screen: a scenario scored by completion time.

### Run

One finished attempt at a scenario, recorded as one stats file in the stats
folder. Play that writes no stats file isn't a run.

- On screen, a run's stats file is a run file.

### Stats folder

The KovaaK's folder of stats files that the app reads runs from.

- In code: `stats_dir`.

### Performance file

The file KovaaK's writes beside a run's stats file, recording the run's
events second by second. The app reads it only to tell whether a scenario is
time-scored
([2026-10-05](decision_log.md#2026-10-05-time-scored-scenarios-are-measured-by-pace)).

- Not a run on its own: an abandoned attempt can leave a performance file and
  no stats file.
- In code: `.perf`, the file's extension.

### Sensitivity

The mouse sensitivity a run was played at: a value on a scale, such as 34.6
cm/360. A scenario's runs are compared within one sensitivity, on the Score vs
Sensitivity chart and in top-N placement.

### cm/360

The scale the app shows sensitivity in: centimeters of mouse travel per full
360-degree turn, so higher is slower. How runs recorded on a game's own scale
are converted, and which ones can't be, is in
[scenario_performance.md](specs/scenario_performance.md#the-graph).

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
covers benchmarks too. Where the two must be told apart, a playlist is the
kind without rank data
([2026-07-03](decision_log.md#2026-07-03-import-benchmarks-from-evxl-and-kovaaks)).

### Benchmark

A playlist whose scenarios carry rank ladders, so a scenario's PB earns a Rank
([2026-07-03](decision_log.md#2026-07-03-import-benchmarks-from-evxl-and-kovaaks)).

### Playlist code

KovaaK's identifier for a playlist, which the app also uses as the playlist's
identity, because names aren't unique
([2026-07-07](decision_log.md#2026-07-07-use-playlist-codes-as-playlist-identity)).

- Also called share code, KovaaK's own name for it.
- In code: `code` on a playlist, and `playlist_code` elsewhere.

### Benchmark ID

KovaaK's numeric identifier for a benchmark. It is not the playlist code,
which identifies the same benchmark as a playlist. Only a bundled benchmark
carries one
([2026-10-05](decision_log.md#2026-10-05-a-columns-menu-shows-and-hides-table-columns-and-kovaaks-ids-are-optional-ones)).
Where it is shown is in [playlists.md](specs/playlists.md#the-overview).

- In code: `kovaaks_benchmark_id` in a bundled file, and `benchmark_id`
  elsewhere.

### Stalest

Of the scenarios in a playlist that the player has played, the one played
longest ago ([playlists.md](specs/playlists.md#the-overview)).

- Not From cache, which the code calls `stale`.

## Leaderboard standing

### Position

The player's placement on a scenario's global KovaaK's leaderboard, such as
11,290 of 63,892. A player with no leaderboard entry is Unranked, KovaaK's own
word
([2026-07-06](decision_log.md#2026-07-06-one-word-per-concept-in-leaderboard-verbiage)).
How it is fetched and cached is in [scenario_rank.md](specs/scenario_rank.md).

- In code: `rank`, except in the scenario table's row fields, which say
  `position`.
- Not Rank, which is the benchmark tier.

### Total players

How many players a scenario's leaderboard holds, the denominator of the
percentile.

- In code: `total_players`, or `total` for short, as in the scenario table's
  row fields, and `leaderboard_total` where the count is handled on its own.

### Percentile

The share of a scenario's leaderboard the player places above, as a
percentage, so higher is better. It comes from position and total players; how
it is derived is in [scenario_rank.md](specs/scenario_rank.md#domain-model).

### Leaderboard ID

KovaaK's numeric identifier for a scenario's global leaderboard. Position,
total players, and percentile all come from that leaderboard
([2026-10-05](decision_log.md#2026-10-05-a-columns-menu-shows-and-hides-table-columns-and-kovaaks-ids-are-optional-ones)).
Where it is shown is in
[playlists.md](specs/playlists.md#the-per-playlist-scenario-table).

- In code: `leaderboard_id`.

### From cache

Marks a value shown from the app's local cache because fetching a fresh one
failed, such as a position shown while KovaaK's is unreachable. A value read
from the cache routinely carries no mark
([scenario_rank.md](specs/scenario_rank.md#failure-handling)).

- In code: `stale`, as in a result served stale.
- Not Stalest, which is about when a scenario was last played.

### Last updated

When the app last stored a read of the player's position from KovaaK's
leaderboard
([2026-10-04](decision_log.md#2026-10-04-the-position-value-says-when-it-was-last-updated)).
Where it appears is in [scenario_rank.md](specs/scenario_rank.md#caching).

- In code: `fetched_at`.
- Not when the app last tried: a failed attempt leaves it as it was.
- Not when the position last moved: a read that finds the same position still
  counts.

## Benchmark ranks

### Rank

The benchmark tier a scenario's PB has reached, such as Gold. Each benchmark
scenario has a ladder of ranks, each with a name, a color, and a score
threshold, and a PB below the first one has No rank
([2026-07-06](decision_log.md#2026-07-06-one-word-per-concept-in-leaderboard-verbiage)).
How a PB is placed on the ladder is in
[playlists.md](specs/playlists.md#the-per-playlist-scenario-table).

- In code: `tier` in the scenario table's row fields, and `rank` in the ladder
  data.
- Not Position. No rank is not Unranked: No rank is below the first tier, and
  Unranked is no leaderboard entry.

### Next Rank gap

How much a benchmark scenario's PB has to improve to reach its next rank: as
a percentage of the PB, such as +4.8% to Gold, or of its pace where the app
measures a time-scored scenario by pace, such as +2.8% faster to Lavender.
With every rank reached, it reads Top rank
([2026-09-27](decision_log.md#2026-09-27-benchmark-tables-show-each-scenarios-rank-and-the-gap-to-the-next-one),
[2026-10-05](decision_log.md#2026-10-05-time-scored-scenarios-are-measured-by-pace)).
How the gap is computed and shown is in
[playlists.md](specs/playlists.md#the-per-playlist-scenario-table).

- On screen: the Next Rank column.
- In code: `next_tier`.

### Rank overlay

The chart's lines for a scenario's rank thresholds
([scenario_performance.md](specs/scenario_performance.md#the-graph)).

- On screen: the Rank thresholds switch.

## Scores and notifications

### PB

Personal best: the highest score among a scenario's runs, whatever their
sensitivity. It's the player's own record, not their leaderboard score
([2026-07-06](decision_log.md#2026-07-06-one-word-per-concept-in-leaderboard-verbiage)).

- On screen: PB, also as the prefix of the PB run's stats, as in PB Score.
  Prose says personal best.
- In code: `high_score` for the score, or `pb_score` in the scenario table's
  row fields, and `personal_best` or `pb` for the run that set it and that
  run's stats. The PB a run was chasing is its previous best.

### New PB

A run that beat its scenario's PB when it was played. It held the PB until a
later run beat it, and the latest one is the PB run. A scenario's first run
sets the PB without beating one, so it isn't a new PB. Where the chart marks
them is in
[scenario_performance.md](specs/scenario_performance.md#the-graph).

- On screen: New PB in the chart legend. The celebration toast's title says
  New personal best.
- In code: `new_high_score`.
- Not the PB run, the one run that holds the PB now.

### Accuracy

The share of a run's shots that hit. PB Accuracy on a scenario table means
damage accuracy instead, the share of possible damage done, when the run
records it, so one run can show two different accuracies
([playlists.md](specs/playlists.md#the-per-playlist-scenario-table)).

### Pace

How fast a run finishes a time-scored scenario, set against another run: the
other run's time divided by this one's. A run at 95% of PB pace takes the PB's
time divided by 0.95
([2026-10-05](decision_log.md#2026-10-05-time-scored-scenarios-are-measured-by-pace)).

- On screen: PB pace in a verdict, and faster in the Next Rank column and the
  New personal best toast.

### Score threshold

A score goal set as a percentage of the PB, or of the PB's pace where the app
measures a time-scored scenario by pace
([2026-07-08](decision_log.md#2026-07-08-judge-score-threshold-notifications-against-the-previous-pb),
[2026-10-05](decision_log.md#2026-10-05-time-scored-scenarios-are-measured-by-pace)).
How a run is judged against it is in
[notifications.md](specs/notifications.md#run-notifications).

- On screen, the verdict reads Threshold passed or Below threshold.
- Not a rank's threshold, which comes from a benchmark file.

### Top-N placement

Where a new run's score places among the scenario's runs at the same
sensitivity: first is best, and the rest are Nth-best, such as 2nd-best. A
placement within Top N scores earns a run notification
([notifications.md](specs/notifications.md#run-notifications)). The same N
bounds what the chart plots
([scenario_performance.md](specs/scenario_performance.md#the-graph)).

- On screen: the Top N scores control, and toasts such as New 2nd-best score.
- In code: `nth_score` and `top_n_scores`.

### Run notification

The one toast a run can earn, carrying a score threshold verdict, a top-N
placement, or both
([2026-08-03](decision_log.md#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)).
When a run earns one is in
[notifications.md](specs/notifications.md#run-notifications).

- In code: `run-verdict`, the toast channel's name.
- Not the personal best celebration, a separate response to a new PB.

### Personal best celebration

The response to a run that beats its scenario's previous PB: a short
animation and a New personal best toast that stays until dismissed, on
whatever page is open
([2026-09-02](decision_log.md#2026-09-02-a-new-personal-best-celebrates-on-every-page)).
Not every such run gets one: which run in a batch celebrates, and how recent
it must be, is in [notifications.md](specs/notifications.md#run-notifications).

- On screen: the Personal best celebration setting, which picks the animation
  or turns the celebration off, toast included.
- In code: `pb-celebration`, the toast channel's name.
