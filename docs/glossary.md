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
([2026-10-05](decision_log/2026/2026-10-05-time-scored-scenarios-are-measured-by-pace.md)).
How it recognizes one, and when it can't measure pace, is in
[run_history.md](specs/run_history.md#time-scored-scenarios).

- On screen: a scenario scored by completion time.

### Run

One finished attempt at a scenario, recorded as one stats file in the stats
folder. Play that writes no stats file isn't a run.

- On screen, a run's stats file is a run file.

### Run length

How long a run took to play, with paused time left out. Some runs have none,
because their stats files give no usable start. Which runs those are is in
[sessions.md](specs/sessions.md#run-start-and-run-length).

### Run number

A run's place among the same scenario's runs in its play session, at every
sensitivity and version and across returning visits. The list's `#` column
and the chart tooltip's `run 7 of 12` show this number. The total counts the
scenario's imported runs in that whole session. Changing the chart range
changes neither number.

- On screen: `Session: Oct 12, 6:40 PM · run 7 of 12`.
- Distinct from Score vs Run's underlying axis position, which counts the
  scenario's whole history.
- Contract: [Run History](specs/run_history.md#the-chart).

### Runs ago

The number of newer imported runs of the selected scenario after a run,
counted in play order across all sensitivities and versions. Score vs Run's
point tooltip shows it independently of chart range and zoom. It changes as
new runs of that scenario are imported.

- On screen: `57 runs ago`, `1 run ago` or `Latest run`.
- Contract: [Run History](specs/run_history.md#the-chart).

### Stats folder

The KovaaK's folder of stats files that the app reads runs from.

- In code: `stats_dir`.

### Performance file

The file KovaaK's writes beside a run's stats file, recording the run's
events second by second. The app reads it only to tell whether a scenario is
time-scored
([2026-10-05](decision_log/2026/2026-10-05-time-scored-scenarios-are-measured-by-pace.md)).

- Not a run on its own: an abandoned attempt can leave a performance file and
  no stats file.
- In code: `.perf`, the file's extension.

### Sensitivity

The mouse sensitivity a run was played at: a value on a scale, such as 34.6
cm/360. The Score vs Sensitivity chart plots each run at its sensitivity, and
the first run at a sensitivity isn't judged against the score threshold.

### cm/360

The scale the app shows sensitivity in: centimeters of mouse travel per full
360-degree turn, so higher is slower. How runs recorded on a game's own scale
are converted, and which ones can't be, is in
[run_history.md](specs/run_history.md#the-chart).

### FOV

The field of view a run was played at: a number on a scale, such as 103 on
the Overwatch scale. The same number is a different width on different
scales, so 103 on Overwatch is narrower than 103 on Apex Legends. The app
shows the FOV and the scale as the run's stats file records them and
converts nothing.

- On screen: the run list's FOV column, as `103 Overwatch`.
- In code: `fov` and `fov_scale`, from the stats file's `FOV:` and
  `FOVScale:` lines.

### Session

One stretch of play, including the breaks between runs, as
[product.md](product.md#when-they-ask-them) defines it. A break of more than
30 minutes between runs ends it, so a session can cross midnight and one day
can hold several. It is in progress while no more than 30 minutes have passed
since its last run. How a break is measured is in
[sessions.md](specs/sessions.md).

- Not an app session, which the specs use for one run of the server process.
- In code: `play_session`, because `session` already names an HTTP session
  and an app session.

### Session length

How long a session lasted, from the start of its first run to the end of its
last. It includes the time between runs. How it is worked out is in
[sessions.md](specs/sessions.md#sessions).

### Visit

Consecutive runs on one scenario within a session, with no other scenario
between them. Switching to another scenario ends the visit, and coming back
later in the session starts a new one. The rules are in
[sessions.md](specs/sessions.md#visits).

- Not a visit to a page, which the docs also say in the everyday sense.
- In code: `scenario_visit`.
- Not on screen as a word. Under All scenarios each visit is a row, named by
  its scenario and numbered by its place in the session.

### In session and between sessions

The two moments the app is used in
([product.md](product.md#when-they-ask-them)). In session, the player glances
at the app between runs while KovaaK's runs fullscreen, so an answer has to
work at a glance. Between sessions, before or after one, they look back at how
they're doing and ahead to what to train, usually with more attention to give.

## The Run History page

### Run History

The page that shows one scenario's runs: a chart of its scores, a list of its
runs grouped by session, and its latest run. With Follow on, it
follows the scenario being played
([run_history.md](specs/run_history.md)). The list has a second view, All
scenarios, of each session across every scenario played in it.

- In code: `run_history`.
- Not Home, the page the app opens on.

### Score vs Run

The chart mode that plots a scenario's runs in the order they were played,
evenly spaced, so a busy day and a quiet month each take the room their runs
need. Score vs Time plots the same runs by when they were played
([run_history.md](specs/run_history.md#the-chart)).

### Latest-run card

The card at the right end of Run History's top row, over the run list, that
reports the selected scenario's latest run with its verdict, and measures it
against the typical score at session start and the PB it was chasing
([run_history.md](specs/run_history.md#the-latest-run-card)).

- On screen it has no title. Its first line reads `Latest run · {age}`, or
  `Latest run` alone with no run to report. It doesn't name the scenario,
  which the Selected scenario field names.

### Scenario Stats

The card in Run History's top row about the selected scenario: its typical
score, benchmark category and total run count
([run_history.md](specs/run_history.md#scenario-stats)).

- On screen its first line reads `Typical score`, the figure it leads with.
- In code: `scenario_stats`.

### PB card

The card in Run History's top row about the selected scenario's personal best
as this app records it: its score and rank, the next rank and its threshold,
and the PB run's sensitivity and accuracy. Under it, sourced apart from the
local record, the player's leaderboard standing, shown while there is a local
PB ([run_history.md](specs/run_history.md#the-pb-card)).

- On screen it has no title. Its first line reads `PB · set {age}`.
- In code: `pb_card`.

### Scenario note

The player's own plain-text note about one scenario, such as a reminder about
technique, shown in Run History's top row while the scenario is selected
([run_history.md](specs/run_history.md#the-scenario-note-card)). Each scenario
has at most one, rewritten in place. It belongs to the scenario's name as the
app holds it, so every version of the scenario shares it.

- On screen: `Scenario note`.
- In code: `scenario_notes`, the store and its folder.
- Not a session note, a possible later idea that would belong to a session.

### This scenario

The run list's view of the selected scenario alone: the sessions that hold a
run of it, and under each its runs. It is the view the list starts on
([run_history.md](specs/run_history.md#this-scenario)).

- In code: `VIEW_SCENARIO`, the switch's value `scenario`.

### All scenarios

The run list's view of each session whole: under a session the scenarios
played in it, one row for each visit in the order they were played, and under
each its runs ([run_history.md](specs/run_history.md#all-scenarios)).

- Not the Playlist filter left empty, which is about the scenario dropdown.
- In code: `VIEW_ALL`, the switch's value `all`, and `build_session_tree`.

### Median and best

Two figures the run list can show on a row that stands for several runs of
one scenario: the middle score and the highest score of the runs under that
row. They count every run under the row and compare nothing
([run_history.md](specs/run_history.md#both-views)).

- Not the typical score, which is what a player's runs on a scenario usually
  score.
- In code: `figures`, and the Columns menu's choice `median_best`.

### Run viewer

The view of one run that takes the place of Run History's chart until it is
closed: the run's score against its typical runs, By Bot, its settings,
and everything its stats file recorded
([run_history.md](specs/run_history.md#the-run-viewer)).

- On screen: no name of its own. Its sections are By Bot, Settings and
  Everything Recorded, and its button is Close.
- In code: `run_viewer`, and `run_viewer_panel` for what draws it.

## Playlists

### Playlist

A named, ordered list of scenarios, identified by its playlist code. The word
covers benchmarks too. Where the two must be told apart, a playlist is the
kind without rank data
([2026-07-03](decision_log/2026/2026-07-03-import-benchmarks-from-evxl-and-kovaaks.md)).

### Benchmark

A playlist whose scenarios carry rank ladders, so a scenario's PB earns a Rank
([2026-07-03](decision_log/2026/2026-07-03-import-benchmarks-from-evxl-and-kovaaks.md)).

### Playlist code

KovaaK's identifier for a playlist, which the app also uses as the playlist's
identity, because names aren't unique
([2026-07-07](decision_log/2026/2026-07-07-use-playlist-codes-as-playlist-identity.md)).

- Also called share code, KovaaK's own name for it.
- In code: `code` on a playlist, and `playlist_code` elsewhere.

### Benchmark ID

KovaaK's numeric identifier for a benchmark. It is not the playlist code,
which identifies the same benchmark as a playlist. Only a bundled benchmark
carries one
([2026-10-05](decision_log/2026/2026-10-05-a-columns-menu-shows-and-hides-table-columns-and-kovaaks-ids-are-optional-ones.md)).
Where it is shown is in [playlists.md](specs/playlists.md#the-overview).

- In code: `kovaaks_benchmark_id` in a bundled file, and `benchmark_id`
  elsewhere.

### Category

One of the groups a benchmark's author sorts its scenarios into, such as
Clicking or Tracking. Only a benchmark from the bundled library has
categories
([2026-10-06](decision_log/2026/2026-10-06-benchmark-scenario-tables-group-scenarios-by-category-and-subcategory.md)).
How the table draws them is in
[playlists.md](specs/playlists.md#categories-and-subcategories-on-a-benchmarks-table).

- Not the `Category` of KovaaK's benchmark payload. KovaaK's has one level
  of groups, which is this app's categories on some benchmarks and its
  subcategories on others.

### Subcategory

A group within a category, such as Dynamic within Clicking. A benchmark
with one level of grouping has categories and no subcategories
([playlists.md](specs/playlists.md#categories-and-subcategories-on-a-benchmarks-table)).

### Stalest

Of the scenarios in a playlist that the player has played, the one played
longest ago ([playlists.md](specs/playlists.md#the-overview)).

- Not From cache, which the code calls `stale`.

## Leaderboard standing

### Position

The player's placement on a scenario's global KovaaK's leaderboard, such as
11,290 of 63,892. A player with no leaderboard entry is Unranked, KovaaK's own
word
([2026-07-06](decision_log/2026/2026-07-06-one-word-per-concept-in-leaderboard-verbiage.md)).
How it is fetched and cached is in [scenario_rank.md](specs/scenario_rank.md).
On Run History it is in the PB card's leaderboard line: under the percentile
when a percentile exists, and on the line itself otherwise.

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
([2026-10-05](decision_log/2026/2026-10-05-a-columns-menu-shows-and-hides-table-columns-and-kovaaks-ids-are-optional-ones.md)).
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
([2026-10-04](decision_log/2026/2026-10-04-the-position-value-says-when-it-was-last-updated.md)).
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
([2026-07-06](decision_log/2026/2026-07-06-one-word-per-concept-in-leaderboard-verbiage.md)).
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
([2026-09-27](decision_log/2026/2026-09-27-benchmark-tables-show-each-scenarios-rank-and-the-gap-to-the-next-one.md),
[2026-10-05](decision_log/2026/2026-10-05-time-scored-scenarios-are-measured-by-pace.md)).
How the gap is computed and shown is in
[playlists.md](specs/playlists.md#the-per-playlist-scenario-table).

- On screen: the Next Rank column.
- In code: `next_tier`.

### Typical Rank

The benchmark tier a scenario's typical score reaches on its ladder, found
the way Rank is found from the PB, with how far the typical score sits
toward the next tier. It is never a rank the player has earned: KovaaK's
ranks the PB. It is unknown while the typical score is, which is never read
as weak
([2026-10-22](decision_log/2026/2026-10-22-typical-rank-sorts-by-rank-position-and-reads-the-rank-and-a-percent.md)).

- On screen: the Typical Rank column, such as `Celadon · 7%`.
- In code: `typical_tier`; its sort key is the rank position, the ranks
  reached plus that fraction.
- Not Rank.

### Rank overlay

The chart's lines for a scenario's rank thresholds
([run_history.md](specs/run_history.md#the-chart)).

- On screen: the Rank thresholds switch.

### Accuracy target

An estimate of the hit accuracy a run needs to reach a rank's threshold when
the fire button is held for the whole run: the threshold over the score the
player's runs would make at 100%, rounded up to a tenth of a percent. Shown
once at least 5 of the scenario's runs since its last update agree on that
score, and never on a scenario the app recognizes as time-scored. Shots vary
a little even with the button held, so a run can clear it and still miss the
rank, or reach a rank estimated above 100%
([run_history.md](specs/run_history.md#the-chart)).

- On screen: the figure beside a rank line in the chart's right margin,
  while the Accuracy targets switch is on.
- In code: `accuracy_target`; the score at 100% is `full_accuracy_score`.
- Not the accuracy guideline on the [roadmap](roadmap.md), which is the
  accuracy top leaderboard players reach.

## Scores and notifications

### PB

Personal best: the highest score among a scenario's runs, whatever their
sensitivity. It's the player's own record, not their leaderboard score
([2026-07-06](decision_log/2026/2026-07-06-one-word-per-concept-in-leaderboard-verbiage.md)).

- On screen: PB, also as the prefix of the PB run's stats, as in PB Score.
  Prose says personal best.
- In code: `high_score` for the score, or `pb_score` in the scenario table's
  row fields, and `personal_best` or `pb` for the run that set it and that
  run's stats. The PB a run was chasing is its previous best.

### Typical score

What a player's runs on a scenario usually score: the median of its last 20
runs, or of all its runs when it has fewer, whatever their age. It is known
once those runs number at least 10 from at least 2 sessions, or 20, and before
that it is unknown, which is never read as weak. It is drawn at full strength
when recent and faded when not. The rules are in
[the typical score's spec](specs/typical_score.md).

- The roadmap and the decision log call it the typical run.
- Not Median and best, which describe the runs under one row of the run list,
  with no minimum.
- Not the median KovaaK's leaderboard shows, which is the median player's PB.
- In code: `typical_score`.

### Recent

The state of a typical score at least 10 of whose runs are from the 30 days
up to a moment, from any number of sessions. Scenario Stats judges it as of
now, and the chart at each point. A recent value can still hold runs older
than 30 days, up to half of them.

- On the chart: a full-strength stretch; not recent, a faded one.
- On Scenario Stats: an undimmed lead number; not recent, a dimmed one.
  Whenever some of the value's runs are older than 30 days, recent or not,
  `{k} of {n} recent runs` follows `Typical score`.
- On the scenario table: judged once, as the page opens. Not recent, a
  muted grey with a clock after the value in both typical cells, and
  `Not recent` for a screen reader, explained in the cells' hovers.
- On the latest-run card: a typical score at session start, judged when the
  session began. Not recent, a clock after its phrase and `Not recent` for a
  screen reader, explained in the phrase's hover.
- In code: `recent`; the table's row field is `typical_not_recent`, and the
  card's is `TypicalPhrase.not_recent`.

### Typical at session start

The typical score as it stood when a session began: the value after the
scenario's last run before that session. The latest-run card measures a run
against it, so every run of a session meets the same value, and a run never
meets a value it helped make. Unknown when the scenario had no known typical
score before the session. Its recency is judged at the session's start, not
when the card is read
([2026-10-25](decision_log/2026/2026-10-25-the-latest-run-card-measures-the-run-against-the-typical-score-at-session-start.md)).

- On screen: the latest-run card's `3.6% above typical at session start`,
  with the value in its hover, and a clock after it when the value wasn't
  recent.
- Not the Typical score card's value, which follows every run.
- In code: `typical_score_at_session_start`.

### Typical runs

A run's typical runs are the runs behind its typical at session start: up to
20 runs of the scenario before the run's session. A figure's typical is its
median over the ones that have the figure, and a setting's is its most
common value among them. A run has none while its typical at session start
is unknown ([run_history.md](specs/run_history.md#what-it-shows)).

- On screen: `Typical` on the run viewer's tiles, cards and By Bot
  columns, and `your typical runs` in its copy.
- Not the runs behind the Typical score card's value, which moves on with
  every run: a run's typical runs stay the ones before its session.
- In code: `typical_runs`.

### Middle 50%

The range the middle half of the runs behind a typical score fell in: from the
first quartile to the third, P25 to P75. Run History draws it as a band around
the typical score while its switch is on.

- On screen: `Middle 50%`.

### Middle 80%

The range the middle 80% of the runs behind a typical score fell in: from the
10th percentile to the 90th, P10 to P90. Run History draws it as a lighter band
while its switch is on.

- On screen: `Middle 80%`.

### New PB

A run that beat its scenario's PB when it was played. It held the PB until a
later run beat it, and the latest one is the PB run. A scenario's first run
sets the PB without beating one, so it isn't a new PB. Where the chart marks
them is in
[run_history.md](specs/run_history.md#the-chart), and how the run list and
the latest-run card mark them is in
[run_history.md](specs/run_history.md#marks-the-check-and-the-star).

- On screen: New PB in the chart legend, on stars beside runs and scenario
  visits in the run list, and as the latest-run card's badge. A session
  star's hover says a new PB was set in that session, limited to the selected
  scenario under This scenario. The celebration toast's title says New personal best.
- In code: `new_high_score`.
- Not the PB run, the one run that holds the PB now.

### Accuracy

The share of a run's shots that hit, the figure KovaaK's shows for a run.
Every place this app shows a run's accuracy shows this one, PB Accuracy on a
scenario table included
([playlists.md](specs/playlists.md#the-per-playlist-scenario-table)). It is
not the share of possible damage done, which KovaaK's stats file calls
Efficiency and this app does not show.

### Pace

How fast a run finishes a time-scored scenario, set against another run: the
other run's time divided by this one's. A run at 95% of PB pace takes the PB's
time divided by 0.95
([2026-10-05](decision_log/2026/2026-10-05-time-scored-scenarios-are-measured-by-pace.md)).

- On screen: PB pace on the latest-run card, and faster in the Next Rank
  column, the New personal best toast, the card's line for a new PB, and the
  card's `faster than typical at session start`, with slower its opposite.

### Score threshold

A score goal set as a percentage of the PB, or of the PB's pace where the app
measures a time-scored scenario by pace
([2026-07-08](decision_log/2026/2026-07-08-judge-score-threshold-notifications-against-the-previous-pb.md),
[2026-10-05](decision_log/2026/2026-10-05-time-scored-scenarios-are-measured-by-pace.md)).
How a run is judged against it is in
[run_history.md](specs/run_history.md#marks-the-check-and-the-star).

- On screen, the latest-run card's badge reads Threshold passed or Below
  threshold, and a check beside a run's score in the run list says the run
  passed.
- Not a rank's threshold, which comes from a benchmark file.

### Run notification

The toast that says the app detected a new run. It names the run's scenario
and links to it on the Run History page, and it carries no verdict on the
run
([2026-10-13](decision_log/2026/2026-10-13-a-run-toast-is-plain-and-shows-on-every-page.md)).
When a run earns one is in
[notifications.md](specs/notifications.md#run-notifications).

- On screen: New run detected.
- In code: `run-verdict`, the toast channel's name.
- Not the personal best celebration, a separate response to a new PB.

### Personal best celebration

The response to a run that beats its scenario's previous PB: a short
animation and a New personal best toast that stays until dismissed, on
whatever page is open
([2026-09-02](decision_log/2026/2026-09-02-a-new-personal-best-celebrates-on-every-page.md)).
Not every such run gets one: which run in a batch celebrates, and how recent
it must be, is in [notifications.md](specs/notifications.md#run-notifications).

- On screen: the Personal best celebration setting, which picks the animation
  or turns the celebration off, toast included.
- In code: `pb-celebration`, the toast channel's name.
