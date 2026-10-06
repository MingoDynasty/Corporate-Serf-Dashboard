# Run History Proposal

Status: Proposed
Date: 2026-10-05

## TL;DR

A finished run is reported by a toast that disappears, and the app has no
view of the session it belonged to or of the runs around it. This proposal
splits the runs the app already holds into sessions and visits, shows the
session in progress and the scenario's earlier visits beside the chart, and
adds a Sessions page for looking back. It also sets the definition of the
typical score, which the product direction asks later features to judge
skill by, and reports each run by where it falls among the player's recent
runs. Every choice in it is open for review.

## Decisions needed

**Nothing in this proposal is ratified.** Six rows need the maintainer's
judgment, H1 to H6. Each states a recommendation, the evidence behind it, and
what changes if the maintainer chooses differently. The IDs start with H so
they can't be confused with D1 to D5 of
[PR #327](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/327).

**Already decided, and binding here.** The proposal is held to these and
doesn't reopen them:

- **The three skill-judgment principles,** ratified on 2026-10-04 and
  recorded in the roadmap's
  [Guiding principles](../roadmap.md#guiding-principles) and the
  [decision log](../decision_log.md#2026-10-04-skill-is-judged-by-the-typical-run-with-honest-uncertainty-in-verdicts-not-advice).
  - Judgments about skill "move toward" the typical run, and "The personal
    best stays the achievement". What counts as the typical run "(the
    window, the run count, the warm-up rule) is the Run History proposal's to
    set". H4 sets it.
  - "unknown rows form a group of their own and are never ranked among the
    known ones". "A figure that can only be a minimum is labelled one
    wherever it's shown". "An estimate is shown no more precisely than it's
    known."
  - "the app doesn't say what to play or when to stop", and "A result
    measured against something the player set is still a verdict."
- **Sessions come first.** "Sessions, and the visits inside them, are built
  before either history view". "Which view ships first is open, for the
  proposal's rewrite to decide." H1 decides it.
- **The two moments** in
  [product.md](../product.md#when-they-ask-them): the player uses the app in
  session, at a glance between runs, or between sessions. "Whether the live
  and the finished session are one view or two is a design choice for the
  feature that builds them." H6 makes that choice.
- **Pace.** A percentage on a time-scored scenario is measured by pace
  wherever the app can measure it
  ([2026-10-05](../decision_log.md#2026-10-05-time-scored-scenarios-are-measured-by-pace)).
  The one percentage this proposal shows follows that rule.

Author-owned choices are in [Design](#design), each tagged as one. Reviewers
are invited to challenge those too, and to propose a row for any choice here
that is costly to reverse and isn't listed.

### H1. The first slice is the Run history panel, then the Sessions page

Status: Open.

**Recommendation: ship the session in progress and the scenario's earlier
visits first, in one panel beside the chart on Scenario Performance (PRs 1
and 2 of the [Delivery plan](#delivery-plan)). Ship the Sessions page
second. The milestone is complete when both have shipped, with whatever H4
and H5 add to them.**

The roadmap names three views: the session in progress, recent sessions, and
a scenario's history over weeks. The panel holds the first and the third.
The Sessions page is the second.

Why this order:

- **It is what gets used most.** The maintainer keeps Scenario Performance
  open on a second monitor during play, and wrote that looking at a
  scenario's run history is the "Most common use case". The roadmap's
  principle is "Daily-use features come before occasional-insight
  features". The panel would be looked at after every run. The Sessions
  page would be opened between sessions, and the maintainer plays about two
  a day.
- **The two halves are one component.** A visit drawn as one row of scores
  is the unit of both. The session block lists the visits of one session.
  The scenario block lists the visits of one scenario. Building the second
  after the first is a filter, not a second feature.
- **The panel pays the page-space cost once.** Shipping one block first
  would take the chart's width for half a panel.
- **Sessions still come first, in the sense that was ratified.** Both blocks
  are built on sessions and visits from the first PR. Nothing ships on raw
  timestamps.

Where this differs from the leans on record:

| Lean | Its order | This proposal |
|---|---|---|
| The maintainer (2026-09-28) | Scenario Performance is open in play. See where a run sits in its session. Review a past session in play order. | Both, in that order. |
| The three seats of #317 | Build the cross-scenario session review first, live and recent. | The live session ships first. The recent ones ship second, after the scenario's rows. |
| `gpt-6-astra` on #327 | One coherent slice of the live and recent session, with the foundation. | The foundation ships with the live session. The recent sessions follow. |
| `claude-fable-5-1` on #327 | The session so far on whatever page is open in play, then a between-sessions page. | The live session first and the page second, as here. On Scenario Performance only, not on every page: see H6. |
| The brainstorm's Claude take | Scenario Performance becomes the in-session page, then a Sessions page. | The same. |

**If the maintainer chooses the session review first instead:** the order
becomes the session block, the Sessions page, then the scenario block. The
scenario's earlier visits wait one PR longer, and the panel ships with one
block. **If "complete" means the session views only:** the scenario's
history becomes an Upcoming entry of its own, and the trend verdict could
start one PR sooner.

### H2. A session ends after 30 minutes without a run, and 30 is fixed

Status: Open.

**Recommendation: a run belongs to the same session as the run before it
unless more than 30 minutes pass between that run's end and this run's
start. The 30 is a constant in the code, not a setting. A session is in
progress until 30 minutes have passed since its last run.**

This carries forward two of the old proposal's positions, gap-based sessions
and a fixed constant, and corrects the claim the second one rested on.

- **Gap-based, not per calendar day, holds.** At 30 minutes the maintainer's
  8,937 runs make 321 sessions. 22 of them cross midnight. Of the 168 dates
  a session started on, 85 hold two or more sessions, and the most on one
  date is six.
- **"Insensitive across 15 to 60 minutes" does not hold.** There are 374
  sessions at 15 minutes, 321 at 30, and 293 at 60. Moving the limit across
  that range removes 81 boundaries, about one in five. The gaps have no
  natural break to put the limit in: 26 gaps of 15 to 20 minutes, 27 of 20
  to 30, 18 of 30 to 45, 10 of 45 to 60, and 26 of 60 to 90.
- **So 30 is a convention, with one thing in its favor.** After a gap of 5
  to 30 minutes the next run is on the same scenario 52% of the time (143 of
  273). After 30 to 180 minutes it is 34% (31 of 92). A break under half an
  hour more often resumes what was being played. The maintainer's training
  notes have also used 30 since September.
- **Fixed, because most gaps aren't near the limit.** 93% of the 8,936 gaps
  are under five minutes and 3% are over an hour. The limit decides 81 gaps
  in seven years, 25 of them in 2026. Sessions are computed, never stored,
  so changing the constant later re-splits the history with no migration.

**If the maintainer chooses another value:** every session count, session
length, and typical score (H4) shifts with it. At 15 minutes the 2026
history gains 16 sessions, and at 60 it loses 9. **If it becomes a
setting:** it needs a settings surface and its copy, and two installs stop
agreeing on what a session is. A `config.toml` key could be added later
without breaking anything. Removing a shipped setting would.

### H3. A visit is an unbroken stretch on one scenario, and its first run is the warm-up run

Status: Open.

**Recommendation: a visit is an unbroken stretch of runs on one scenario
inside one session. Switching scenarios ends it, and coming back later in
the session starts a new one. The warm-up run is the first run of each
visit.**

The roadmap already uses this meaning of visit. One design note uses the
other meaning, all of a scenario's runs in one session.

- **The two meanings usually agree.** Of 2,698 scenario-in-session pairs,
  94% are a single stretch. The player came back to a scenario later in the
  same session 196 times in 2,894 visits.
- **Only the stretch can be drawn in play order.** A view that lists a
  session as it was played can't show two separate stretches as one row.
- **The first run is lower.** Over 605 visits of four or more runs, the
  first run sits a median 3.3% below the median of the rest (90% interval
  −3.7% to −2.8%), and is the lower one in 72% of visits. Runs 2 and 3 sit
  0.7% and 0.5% below, and runs 4 to 10 are within half a percent.
- **The evidence is weaker for a return visit.** Its first run sits 1.2%
  below the rest, on 56 visits, with an interval of −2.2% to +0.6%. That
  doesn't separate it from no dip at all.
- **The choice barely moves the typical score.** The two warm-up rules give
  the same typical score in 85% of 255 comparisons and differ by more than
  1% in 4%.

So the recommendation rests on display and on having one rule, not on
accuracy. A change of sensitivity inside a visit doesn't end the visit and
doesn't make a warm-up run: the run after one sits 0.5% below the visit's
other runs (266 runs, interval −1.3% to 0.0%).

**If the maintainer chooses the other meaning of visit:** the session views
can't draw a visit as one row, and need a second word for a stretch. **If
the warm-up run is the first run of a scenario in a session instead:** 196
fewer runs are marked, every mark has the stronger evidence behind it, and
the views need a rule that isn't "the first run of the row".

### H4. The typical score is in this milestone, defined as below

Status: Open.

**Recommendation: name it the typical score. Define it as the median of a
scenario's last 20 runs from the 14 days up to the end of the player's last
finished session, leaving out warm-up runs. With fewer than 8 such runs it
is unknown. Show it in one place in this milestone, beside the scenario's
other stats, and rank or judge nothing by it yet.**

"Taken at the end of a session" makes two of the brainstorm's ideas one
rule. A session in progress is measured against the level the player came in
with, which is the maintainer's lean L2. Time off doesn't empty the window,
because the window ends at the last session and not at today.

The definition was tested on one question: taken as it stood when a session
began, how close is it to the level the scenario was then played at? The
level is the median of the scenario's runs in that session, first runs of
visits left out. There are 597 such cases over 252 scenarios. "Miss" below
is the median distance between the two after removing the average offset.
Each comparison uses the cases where both sides had at least 8 runs: 255
of them, unless the row gives another count.

| Choice | Finding | Kept or changed |
|---|---|---|
| 20 runs | The last 10, 30, and 50 miss by 3.5%, 3.6%, and 3.6%. The last 20 misses by 3.2%. | Kept. |
| 14 days | A sample whose runs are all from the 14 days before the session misses by 2.5%. With over half of them older, it misses by 5.3%. When even the newest run is 14 to 30 days old it misses by 9.6%, on 20 cases. | Kept. |
| No warm-up runs | 3.2% without them against 3.6% with them. The interval on the difference is −0.7 to +0.1 points, so the gain is small and unproven. | Kept, for the reason in H3. |
| At least 8 | No cliff at 8. The miss is about 7.5% with 2 to 5 runs, about 5% with 6 to 19, and 2.6% with a full 20. | Kept as a convention. |
| All sensitivities together | Runs at the session's own sensitivity only: 2.8%, against 2.6% for all of them, on 202 cases. | Kept. |
| A cap on one session's share | A cap of 8 runs per session: 3.4% against 3.2%. | Not added. |
| Session medians instead | The median of the last five session medians: 3.7%. | Not used. |

Three things the test shows about the figure itself:

- **It is unknown most of the time.** In 2026 it was known for 20% of the
  scenarios played in a session (935 pairs), which is 32% of the runs. That
  is the principle "unknown isn't weak" at work, and it is why H5 doesn't
  build the per-run readout on this figure.
- **Players return a little above it.** The level in the session is a
  median 1.6% above the typical score taken before it.
- **Within one scenario the personal best tracks level as well.** Its miss
  is 3.1% once its offset of −5.9% is removed. That matches the direction
  entry's own evidence, where the two tied within a scenario. The entry's
  case for the typical score is ordering scenarios against each other,
  which this test doesn't measure.

Why in this milestone: the direction entry hands the definition here, every
Future entry that needs it waits on it, and one visible figure lets the
definition be checked against real play before any ranking depends on it.

**If the maintainer leaves it out:** this milestone shows no figure, the
readout in H5 is unaffected, and the definition is set by the first feature
that ranks by it. **If the typical score follows each run instead of
holding for the session (against L2):** a run's readout depends on the
order of play, and in a long visit the reference becomes that visit's own
runs. The measured difference is in [Evidence](#evidence).

### H5. Every finished run is reported in place, by a count

Status: Open.

**Recommendation: a finished run joins its visit's row in the panel, marked
when it passed the score threshold or set a new PB. The newest run also
gets one readout, "Better than 15 of your last 20". The run toasts stay as
they are.**

- **Every run is reported, without a toast for every run.** On 2026-09-13
  the maintainer raised notifying on every run as a candidate for this
  proposal. Today a run that is
  neither judged nor placed gets no toast, by the
  [2026-08-03 ruling](../decision_log.md#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy).
  A row that keeps every run answers the question and leaves that ruling
  alone.
- **The toasts stay,** which is the maintainer's lean L4. Nothing in this
  work removes or rewords one.
- **A count, not a percentage of the typical score.** The maintainer's
  preference on record is percentages against the PB and the typical score.
  The count is recommended instead for three reasons.
  - It has something to say far more often. In 2026 a count had at least
    three earlier runs to compare against on 61% of 3,272 runs. A percentage
    of the typical score would have been blank on more than two runs in
    three (H4).
  - It carries its own sample. "Better than 3 of your last 4" shows how
    little is behind it. A percentage of an estimate doesn't.
  - It needs no pace arithmetic. A higher score is a faster finish, so a
    count is right on a time-scored scenario as it stands.
- **The percentage of the PB stays where it is:** in the threshold toast,
  and in a run's hover in the new views.

The count is a fact about the runs it names, so it compares against the
scenario's last 20 whatever their age. The typical score is a claim about
the player's level now, so it needs recent runs. That is why the two use
different samples.

**If the maintainer chooses percentages:** the readout is blank on about
two runs in three until a scenario has eight recent runs, and it needs the
pace rule. **If both:** the readout line doubles, and the percentage half
is usually blank. **If no readout:** PR 4 of the
[Delivery plan](#delivery-plan) carries the typical score alone.

### H6. Run history lives beside the chart, and sessions get a page

Status: Open.

**Recommendation: a Run history panel on Scenario Performance, in the
column beside the chart that Chart options uses, open by default. A new
Sessions page in the navbar. The Sessions page is one view for the session
in progress and for any finished one.**

- **One column, shared.** The
  [2026-08-09 decision](../decision_log.md#2026-08-09-the-graph-page-is-scenario-performance-its-panel-is-chart-options)
  left this question to this proposal and promised the column had no
  exclusive tenant: "Run History composes into this column rather than
  adding a second one." The panel takes the column, and Chart options
  stacks above it when opened.
- **Beside the chart, not below it.** The same decision measured the chart
  at 1600×900: 1002×639 beside an open panel, a shape of 1.57 to 1. A panel
  of five rows below the chart would leave about 1318×447, which is 2.95 to
  1, flatter than the 2.76 to 1 that decision rejected as "wide and
  shallow". This is arithmetic from those measurements, not a browser run.
- **One view for live and finished.** The newest session in the Sessions
  list is the one in progress, and it updates as runs land. A session
  watched live is the same row once it ends.
- **The three tiers of the brainstorm.** With no click: the panel. With a
  click or a hover on the page: a run's details, an earlier visit of the
  session, older visits of the scenario. By navigating: the Sessions page.

Not recommended, each with its cost:

- **One consolidated Run History page.** In session the player would choose
  between it and the chart.
- **The session in the app's header, on every page.** It would follow the
  player to a playlist table, which the maintainer opens to pick the next
  scenario. It would also sit on Settings, and a header line has no room
  for a visit's runs.
- **A toggle between by-session and by-scenario.** Whichever isn't selected
  needs a click, and both fit.
- **No sidebar at all,** the old proposal's position. It argued that a
  sidebar plus a page are two surfaces onto the same data. Here they are
  one row component at two sizes, and the column is page-local.

**If the maintainer chooses the header:** the session line reaches every
page and loses the visit rows. **If below the chart:** the panel's rows
have room for a long visit on one line, and the chart loses about a third
of its height at 1600×900.

## Problem

### What the app does today

The app (a Dash web app that watches the KovaaK's stats folder and plots
each scenario's scores) holds every run in memory and shows a run's place
among the others in three ways:

- **A toast,** when the run passed or missed the score threshold or placed
  in the top N at its sensitivity. It leaves after eight seconds.
- **A point on the chart.** Score vs Sensitivity is the default mode. Score
  vs Time has one position per date and keeps only the top N scores of each
  date, so it shows neither the order of a day's runs nor all of them.
- **Lines in the debug log.** The watchdog (the thread that imports each new
  stats file) logs every run's distance from the high score and whether it
  passed a fixed 95%. The log is developer-facing, and it rotates.

So the app can't answer what the player asks between runs: what did I
score on the runs just before this one, how many have I played, which
scenarios, and for how long. It can't answer what they ask afterwards
either: what did I play last Tuesday, and in what order.

### Who asks, and where they look

[product.md](../product.md#when-they-ask-them) names two in-session
questions: *how did that run go?* and *how is this session going?* The
second "serves a decision: keep pushing this scenario (and whether to push
for speed or for accuracy), switch to another, or stop."

The maintainer stated on 2026-09-28 where they look. During play the second
monitor almost always shows Scenario Performance, because the chart is the
only view of a scenario's history. They sometimes open a playlist's scenario
table to pick the next scenario.

Their own words in the brainstorm note of the same day:

> Most common use case is looking at a scenarios run history and using that
> data to help influence the next run. But I also want to understand where
> the run fits into a session. [...] if I'm currently not in a session, and I
> want to reflect on a past session; can I see what I played in last week's
> session, in the order that I played that session's scenarios?

### What the foundation is missing

- **No session, visit, or warm-up run exists in the code.** The
  [glossary](../glossary.md#session) says so: "The app has no rule yet for
  where one session ends; the first feature that needs one sets it."
- **A run has an end and no start.** `RunData.datetime_object` comes from
  the stats file's name, in whole seconds. Nothing under `source/` reads the
  file's `Challenge Start:` or `Pause Duration:` lines.
- **The typical run has no definition.** The roadmap's principle uses the
  words, and the decision log leaves the window, the run count, and the
  warm-up rule to this proposal.

### Why now

Run history and sessions is the only Upcoming milestone in the roadmap.
Nearly every Future entry stands on it: the trend verdict on session
medians, weakness by the typical run, the rank-up chance, and time spent.

## Evidence

Everything here was measured on 2026-10-05 on the maintainer's stats folder:
8,937 stats files, all of which the app's own parser accepts, covering 866
scenarios from 2019-07-14 to 2026-10-04. The scripts are untracked, in
`ignore/scripts/run-history/` of the main checkout. The run set comes from
the app's `extract_data_from_file`, so it is the set the app holds.

It is one player's history. It shows what the rules do on that history. It
doesn't show what other players' histories look like.

### Run length

A run's length is the time in its file name, minus `Challenge Start:`,
minus `Pause Duration:`.

- **Every run since 2024 has one:** 8,367 runs. Across all years it is
  8,428 of 8,937.
- **463 files have no `Challenge Start:`,** 12 from 2019 and 451 from 2020.
  They have an end and no start.
- **46 lengths come out negative,** all from 2021. One is half a second
  short, the file the
  [Aimcurve survey](../research/aimcurve_learnings_opus.md#4-a-reset-can-write-a-stats-file-that-looks-like-a-run)
  calls reset-shaped. The other 45 are from 2021-07-19 and 2021-07-20. On
  those two days the game wrote `Pause Count:` and `Pause Duration:` as
  running totals for the whole time it was open. On the second day the
  count climbs from 1 to 55 across 50 files, while each run still spans
  about 60 seconds. The one file opened reports game version 2.0.5.2.
- **Since 2024 the pause is per run.** Ten runs were paused. In the nine
  whose scenario has other runs to compare with, the span minus the pause
  is within a second of the scenario's usual length. One spans 269 seconds
  with 209 paused.
- **13 runs crossed midnight.** `Challenge Start:` is a time of day with no
  date, so a start later than the end means the day before.
- **Lengths are steady.** Of 324 scenarios with five or more timed runs, 318
  have a fixed length: 287 at 59 or 60 seconds, 23 at 29 or 30, and 8
  between 39 and 50. Six vary from run to run, and all six are time-scored.
  Five runs in the fixed-length scenarios are more than five seconds off,
  one of them since 2021.
- **Runs fill about half a session.** In the 104 sessions of 2026 with five
  or more runs and ten or more minutes, runs fill a median 49% of the
  session's length, with a middle half of 41% to 56%.

### Sessions

| Limit, minutes | 5 | 10 | 15 | 20 | 30 | 45 | 60 | 90 | 120 |
|---|---|---|---|---|---|---|---|---|---|
| Sessions | 594 | 434 | 374 | 348 | 321 | 303 | 293 | 267 | 244 |

- **Gaps:** 8,936 between consecutive runs. 8,341 are under 5 minutes, 220
  are 5 to 15, 81 are 15 to 60, and 292 are an hour or more. Two are
  negative.
- **At 30 minutes:** 321 sessions, 15 of them a single run. The median
  session has 22 runs. Among those of two or more runs, the median lasts 40
  minutes and the longest 242.
- **Measuring to the next run's start or to its end** changes 2 boundaries
  of 320.
- **In 2026:** 117 sessions. The median has 5 visits, a third have more
  than 8, a fifth have more than 10, and the largest has 71.
- **Cost:** one pass that splits all 8,937 runs into sessions and visits
  takes 5.9 ms in plain Python on the maintainer's machine.

### Visits and warm-up runs

- **2,894 visits.** The median visit is 2 runs and the longest is 70. 41%
  of visits are a single run, and they hold 13% of the runs. 40 visits of 21
  or more runs hold 14% of the runs.
- **First runs are a third of all runs:** 32.4%.
- **A single-run visit scores like a warmed-up run.** Against the
  scenario's level before it, it sits a median 3.4% above (76 cases). The
  later runs of longer visits sit 2.1% above. Why isn't known. One guess
  is that the player moves on after a good first run.
- **No scenario with five or more runs is played only in single-run
  visits,** so leaving out warm-up runs never hides a well-played scenario.

### The typical score

The test is described under H4. Two of its curves in full, for the last 20
runs of any age with warm-up runs left out.

By how many runs the sample held:

| Runs in the sample | 1 | 2 | 3 | 4-5 | 6-7 | 8-11 | 12-19 | 20 |
|---|---|---|---|---|---|---|---|---|
| Cases | 36 | 32 | 22 | 53 | 40 | 54 | 59 | 172 |
| Miss | 4.6% | 7.7% | 7.2% | 7.5% | 5.0% | 4.6% | 5.3% | 2.6% |

The full samples are the well-played scenarios, which are also the
freshest, so the last column mixes size with age. The first column has no
explanation.

By the age of the sample's newest run when the session began, for samples
of 8 or more:

| Days | Under 1 | 1-3 | 3-7 | 7-14 | 14-30 | 30-90 | Over 90 |
|---|---|---|---|---|---|---|---|
| Cases | 103 | 89 | 30 | 15 | 20 | 19 | 9 |
| Miss | 2.4% | 2.8% | 3.6% | 4.1% | 9.6% | 4.4% | 4.7% |
| Level above the sample | +2.0% | +2.4% | +3.8% | +3.3% | +10.9% | +4.9% | +7.4% |

- **One session often fills the sample.** Of 172 full samples, one session
  supplies all 20 runs in 17% and 15 or more in 27%. A full sample spans a
  median 5 days and 3 sessions.
- **The definition against the same sample with no age limit:** on the 167
  cases both cover, they miss by 2.8% and 2.6%. The 14 days decide which
  cases are known, not what the known ones read.
- **How often it is known,** as a share of the 935 scenario-in-session
  pairs of 2026: 20% under the definition, 36% with no age limit, and 43%
  with no age limit and warm-up runs kept.

### The readout's reference

Each run of 2026 was compared with the scenario's most recent runs from
before its session, warm-up runs left out. The share of the 3,272 runs with
a reference of that size:

| At least | 1 run | 3 runs | 5 runs | 8 runs | 20 runs |
|---|---|---|---|---|---|
| Share of runs | 70% | 61% | 55% | 47% | 30% |

Holding the reference for the session, against moving it with every run:

- **The two counts are usually close.** On 2,255 runs with a full reference
  of 20 either way, they are equal on 48% and within 2 on 80%.
- **They part in a long visit.** After 21 to 40 earlier runs of the scenario
  in the session, they differ by a mean 3.7 of 20. A run then reads 15 or
  more against the held reference 43% of the time, and 32% against the
  moving one.

### Scenario versions

A stats file's `Hash:` names the version of the scenario, and the run
record has kept it since the pace work. 15 of 866 scenarios have runs under
more than one. Three version changes have five or more runs on each side.
The median score moved by +19.4%, +10.9%, and −1.7% across them.

### Ingestion

The app's surviving debug logs cover 2026-07-27 to 2026-10-05 and record 960
new-file detections.

- **No file was detected twice.**
- **No import failure was logged.**
- **No stats file sits between two detected runs under ten minutes apart
  without being detected itself.**

The logs include agents' test runs, and the last check can't see a miss at
the start or end of a stretch.

### Not checked

- **Nothing was run in a browser.** The panel's geometry is arithmetic from
  the boxes the 2026-08-09 decision measured.
- **No other player's data.**
- **Whether the typical score orders scenarios better than the personal
  best.** That is the re-check due around 2026-10-09. The test here is
  within one scenario.
- **Whether practicing by any of these figures causes learning.**
- **Reset files,** which are out of scope.
- **Game builds between 2.0.5 and 3.7.** The folder has 87 runs from 2021
  and none until December 2024, so the build where the pause fields changed
  meaning isn't known.
- **Daylight-saving changes.** Reasoned about below, not tested.
- **Time-scored scenarios in the score ratios.** The six were left out of
  every ratio and kept in every count.

## Design

### The foundation

No user sees this layer. Every view below reads it.

**Run length (author-owned).** The run record gains a start and a length,
both optional. The parser reads two more lines from a file it already
reads.

- The start is the file's date with `Challenge Start:` as the time, moved
  back a day when that lands after the end.
- The length is the end minus the start, minus `Pause Duration:`.
- The length is unknown outside 1 to 600 seconds, and the start with it.
  That covers the 46 negative lengths. It also covers a run across a
  daylight-saving change, which comes out an hour or a day off.
- A file with no `Challenge Start:` has neither. It still joins a session
  by its end.
- The 2021 files with running-total pauses are not special-cased. Where the
  subtraction leaves a length in range it is too short, never too long.
  Time in runs is labelled a minimum, so the label stays true.

**Sessions and visits (H2, H3).** One pure function over the runs in time
order.

- The idle time between two runs is the next run's start minus this run's
  end, or the next run's end when it has no start.
- More than 30 minutes of idle time starts a new session.
- Inside a session, a change of scenario starts a new visit. A scenario is
  its name, as everywhere else in the app.
- A session's length runs from its first run's start to its last run's
  end. When the first run has no start, it runs from that run's end.
- Time in runs is the sum of the known lengths.

**Computed, not stored (author-owned).** The old proposal's position that
"No SQLite migration is required" holds. Sessions and visits are derived
from the run store on demand. The store is rebuilt from the stats folder at
every start, and the pass costs 5.9 ms. The typical score "as it stood when
a session ended" is also derivable at any time, because it depends only on
runs before that moment. Nothing new is written to disk.

**The typical score (H4).** At the end of a session, for a scenario:

1. Take its runs that ended in the 14 days up to that session's last run.
2. Keep the runs on the scenario's current version, the `Hash:` of its
   newest run. A run with no `Hash:` counts only when the newest has none.
   This follows the pace rule, where the newest run names the version.
   Author-owned.
3. Drop the warm-up runs.
4. Keep the newest 20.
5. With 8 or more, the typical score is their median. With fewer, it is
   unknown.

The figure the app shows is the one taken at the end of the last finished
session. It is computed over every run, never the chart's top N per day.

**The readout's reference (H5).** For a run, the scenario's 20 most recent
runs from before the run's session, on the current version, warm-up runs
left out, whatever their age. The readout counts those with a lower score.
It needs at least 3. A warm-up run gets a label in place of a count.

**Marks (author-owned).** Three facts about a run are drawn on its score:

- **Warm-up run:** the first run of its visit.
- **Threshold passed:** the run met the score threshold, judged as the
  toast judges it: against the PB the run was chasing, by pace where the
  app measures pace, and not at all for a scenario's first run at a
  sensitivity. The mark uses the percentage set today, because the one in
  force when an old run was played was never recorded. With **Score
  threshold verdict** off, no run is marked.
- **New PB:** the rule the chart's stars use.

The threshold percentage lives in the browser, on a Scenario Performance
control. The Sessions page needs it too. The recommended mechanism is a
browser-local store in the app shell that mirrors the control, as the
celebration setting already works. A browser that opens the Sessions page
before Scenario Performance has ever loaded reads the defaults, 95% and on.

**Live updates (author-owned).** The app shell already publishes one batch
per poll when runs land, on every page
([Run delivery](../specs/scenario_performance.md#run-delivery)). The panel
and the Sessions page redraw from that batch. No new polling is added. The
panel's heading changes from "This Session" to "Last Session" on the page's
existing 30-second tick.

**Clock changes (author-owned).** Every time in a stats file is local wall
clock. A session that spans a daylight-saving change can gain a false
boundary or lose a real one, at most twice a year. Accepted and written in
the spec.

### Terms

Each entry is written as [docs/glossary.md](../glossary.md) would hold it.
The PR that ships a term moves its entry in.

Changed entry:

- **[Session](../glossary.md#session).** One stretch of play, including the
  pauses between runs: a run belongs to the session of the run before it
  unless more than 30 minutes separate them. A session can cross midnight,
  and one day can hold several. It is in progress until 30 minutes have
  passed since its last run. How the break is measured goes in the spec.
  - Not an app session, which the specs use for one run of the server
    process.
  - In code: `play_session`, because `session` already names an HTTP
    session.

New entries:

- **Session length.** How long a session lasted, from the start of its
  first run to the end of its last. It includes the time between runs.
- **Visit.** An unbroken stretch of runs on one scenario within a session.
  Switching to another scenario ends the visit, and coming back later in
  the session starts a new one.
- **Warm-up run.** The first run of a visit. It usually scores below the
  runs that follow it, so the typical score leaves it out.
  - On screen: a faded score, named Warm-up run in its hover.
- **Run length.** How long a run took to play, with paused time left out.
  Some old runs have none, because their files don't record a start.
- **Time in runs.** The run lengths of a session added up. It is always a
  minimum: it leaves out the time between runs, any attempt that left no
  stats file, and any run with no run length.
  - On screen: At least 20 min in runs.
- **Typical score.** What a player's recent runs on a scenario usually
  score: the median of the most recent ones, warm-up runs left out. It is
  taken when a session ends and holds until the next one ends, so a session
  in progress is measured against the level the player came in with. It is
  Unknown when too few recent runs exist. How many, and how recent, goes in
  the spec.
  - Not the PB, which is the best run and stays the achievement.

**Naming (author-owned).** The roadmap and the decision log say "typical
run" as a working word, and the brainstorm says "typical score". This
proposal picks typical score: the thing named is a score, not a run, and on
screen it sits beside PB score and Score threshold. The PR that ships the
term changes the roadmap's wording to match.

### The views

#### Scenario Performance, with the Run history panel

```
┌─ controls row, as today ──────────────────────────────────────────────────┐
│ Playlist filter   Selected scenario   Top N   Oldest date   Scenario      │
│                   [x] Follow newly…                         Stats         │
│                                          [Chart options] [Run history]    │
├───────────────────────────────────────────┬───────────────────────────────┤
│                                           │ This Session                  │
│                                           │ Started 9:14 PM · 42 min ·    │
│                                           │ 17 runs         Open session  │
│                                           │                               │
│                                           │ Air Voltaic Invincible 4      │
│                                           │ Medium · 3 runs · 5 min       │
│          chart, as today                  │ 3,120 · 3,380 ✓ · 3,455 ✓     │
│                                           │ Latest run: better than 15    │
│                                           │ of your last 20               │
│                                           │ Whisphere Viscose · 6 runs    │
│                                           │ VT Controlsphere Viscose ·    │
│                                           │ 8 runs                        │
│                                           │───────────────────────────────│
│                                           │ This Scenario                 │
│                                           │ Oct 4, 2026, 9:58 PM ·        │
│                                           │ 5 runs                        │
│                                           │ 3,050 · 3,300 · 3,410 ·       │
│                                           │ 3,390 · 3,500 ✓               │
│                                           │ Oct 2, 2026, 5:20 PM ·        │
│                                           │ 6 runs                        │
│                                           │ …                             │
│                                           │ ✓ Threshold passed ·          │
│                                           │ ★ New PB · Faded: warm-up run │
└───────────────────────────────────────────┴───────────────────────────────┘
```

The scores are illustrative. The first score of each row is a warm-up run
and is drawn faded, which the sketch can't show.

**With no click, the panel shows:**

- When the session started, its length, and its run count.
- The newest visit: its scenario, run count, length, every run's score in
  play order, and each run's marks. The newest run is bold.
- The newest run's readout (H5).
- The session's other visits, newest first, one line each.
- The selected scenario's other visits, newest first, each with its scores.
- The scenario's typical score, in the Scenario Stats block (H4).

**With a click or a hover on the page:**

- Hovering a score shows the run's time, its percentage of the PB it was
  chasing, its run length, its accuracy, and its sensitivity.
- A visit's line in the session block is a link that selects that scenario.
- **Show all visits** opens the session's visits past the newest six.
- **Show older visits** opens the scenario's visits past the newest twenty.
- The **Run history** button closes the panel, and the browser remembers
  the choice.

**By navigating:** **Open session** leads to the Sessions page.

Behavior, all author-owned:

- **Between sessions the panel shows the last session.** The heading reads
  "Last Session" and the first line gives its date. The record a player
  watched live stays where they watched it.
- **The scenario block leaves out the visit the session block has open,**
  so no visit is drawn twice.
- **The panel takes the column the Chart options panel uses.** Open, it
  leaves the chart the box it has today with Chart options open. Chart
  options stacks above it when opened, and the column scrolls. The column's
  constraints in the
  [2026-08-09 entry](../decision_log.md#2026-08-09-chart-options-live-in-a-collapsible-panel-beside-the-graph)
  all still apply: the container query, the animated track, the clipping
  row, and `.home-graph` as the resize hook.
- **On a narrow window** the column stacks, as Chart options does today. The
  recommendation is Chart options above the chart and Run history below it,
  so the chart stays first on a phone.
- **With no run in the store,** the panel and its button aren't drawn.
- **Scores are formatted as the playlist scenario table formats PB Score:**
  thousands separators, at most two decimals, trailing zeros dropped.

#### The Sessions page

```
SESSIONS
┌──────────────────────────────┬───────────────────────────────────────────────┐
│ Oct 5, 2026, 9:14 PM       ◀ │ Oct 5, 2026, 9:14 PM · 42 min · 17 runs       │
│ 42 min · 17 runs ·           │ At least 17 min in runs                       │
│ 3 scenarios · In progress    │                                               │
│                              │ 1. VT Controlsphere Viscose                   │
│ Oct 4, 2026, 9:46 PM         │    8 runs · 13 min                            │
│ 1 hr 30 min · 57 runs ·      │    2,610 · 2,745 · 2,690 · 2,880 ✓ · 2,700 ·  │
│ 9 scenarios                  │    2,655 · 2,790 · 2,905 ✓ ★                  │
│                              │ 2. Whisphere Viscose                          │
│ Oct 2, 2026, 11:19 PM        │    6 runs · 10 min                            │
│ 40 min · 26 runs ·           │    14,100 · 14,620 · 14,890 ✓ · 14,410 ·      │
│ 3 scenarios                  │    14,700 · 14,950 ✓                          │
│ …                            │ 3. Air Voltaic Invincible 4 Medium            │
│                              │    3 runs · 5 min                             │
│                              │    3,120 · 3,380 ✓ · 3,455 ✓                  │
│                              │                                               │
│                              │ ✓ Threshold passed · ★ New PB ·               │
│                              │ Faded: warm-up run                            │
└──────────────────────────────┴───────────────────────────────────────────────┘
```

**With no click, the page shows:**

- Every session, newest first: when it started, its length, its runs, and
  how many scenarios it held. The session in progress says so.
- The newest session opened on the right: its visits in play order, each
  with its scenario, run count, length, and every run's score and marks.
- The session's time in runs, labelled as a minimum.

**With a click or a hover:** clicking a session opens it. Hovering a score
shows what it shows in the panel.

**By navigating:** a visit's scenario name leads to Scenario Performance
with that scenario selected.

Behavior, all author-owned:

- **The session in progress updates as runs land,** and it is the same row
  once it ends.
- **The selected session is kept in the page URL,** so Back and a reload
  restore it, as the playlist scenario table keeps its sort
  ([2026-09-27](../decision_log.md#2026-09-27-the-playlist-scenario-table-keeps-its-sort-in-the-page-url)).
- **The route is `/sessions`.**
- **Nothing on the page is a total across scenarios except time and
  counts.** Scores from different scenarios aren't comparable, and accuracy
  means different things on clicking and tracking scenarios, so neither is
  averaged.

### Copy

Every string this design adds. They follow the nine copy rules in
AGENTS.md. A readout takes no period and chains with ` · `. Headings and
the page title keep Title Case, and everything else is sentence case.

| Where | String | Why |
|---|---|---|
| Scenario Performance, button beside **Chart options** | `Run history` | Names the panel by what it holds, in the roadmap's words. Sentence case, as its neighbor. |
| Panel heading, session in progress | `This Session` | A section heading. "This" says it is the one being played. |
| Panel heading, no session in progress | `Last Session` | The same block, once the session has ended. |
| Panel, first line, in progress | `Started {time} · {length} · {n} runs`, such as `Started 9:14 PM · 42 min · 17 runs` | A readout. The date is left out because it is today or last night. |
| Panel, first line, ended | `{start} · {length} · {n} runs`, such as `Oct 4, 2026, 9:46 PM · 1 hr 30 min · 57 runs` | The start, in the app's timestamp format. |
| Panel, link | `Open session` | Mirrors **Open scenario table** on the same page. |
| Newest visit, heading line | `{scenario} · {n} runs · {length}` | The scenario leads, as it does in every run toast. |
| Other visits of the session | `{scenario} · {n} runs` | One line each. The line is a link. |
| A count of one | `1 run`, `1 scenario` | Singular where the count is one. |
| Panel, past the newest six visits | `Show all {n} visits`, then `Show fewer visits` | Buttons. The one place the word visit is on screen outside a hover. |
| Readout under the newest visit | `Latest run: better than {k} of your last {m}` | A fact, with its own sample size. `{m}` is at most 20. |
| Readout, the latest run is a warm-up run | `Latest run: warm-up run` | Says why there is no count. |
| Readout, fewer than three earlier runs | `Latest run: not enough earlier runs to compare` | Says so instead of going blank. |
| Readout, hover | `Compares the run with your {m} most recent runs of this scenario from before the session it was played in. Warm-up runs are left out.` | "Your last 20" needs its exact meaning within reach. The wording holds for a session that has ended too. |
| Panel heading, scenario block | `This Scenario` | A section heading, paired with This Session. |
| Scenario block, a visit | `{start} · {n} runs` | The start of the visit. |
| Scenario block, no other visits | `No earlier visits` | A readout, in place of an empty block. |
| Scenario block, past the newest twenty | `Show older visits` | A button. |
| Marks legend | `✓ Threshold passed · ★ New PB · Faded: warm-up run` | The first two are the toast's title and the chart's legend entry, word for word. The ✓ entry is left out while no run can be marked. |
| A score, hover, first line | `{time with seconds}`, such as `Oct 4, 2026, 9:58:12 PM` | Seconds kept, as the chart's hover keeps them. |
| A score, hover | `{pct}% of PB`, or `{pct}% of PB pace`, or `New PB` | The toast's own wording. Left out for a scenario's first run. |
| A score, hover | `Run length: {length}`, such as `Run length: 59 s` or `Run length: 2 min 1 s` | Left out when the run has none. The app's durations already say `min` and `hr`, and `s` is new beside them. |
| A score, hover | `Accuracy: {accuracy}%` and `Sensitivity: {sensitivity}` | The chart hover's labels. |
| A faded score, hover, last line | `Warm-up run` | Names the mark. |
| A score, accessible name | `{score}`, then `, warm-up run`, `, threshold passed`, `, new PB` for each mark it carries | Plain, as accessible names are. |
| Scenario Stats, new row | `Typical score:` then `{score} · {n} runs`, such as `3,343 · 20 runs` | The sample size sits beside the figure. |
| Scenario Stats, unknown | `Unknown · {n} recent runs`, or `Unknown · 1 recent run`, or `Unknown · no recent runs` | "Unknown isn't weak": it says so, and why. |
| Typical score, hover, known | `What your recent runs usually score. It's the median of your last {n} runs from the two weeks up to your last finished session, with warm-up runs left out.` | The definition in the player's terms. |
| Typical score, hover, unknown | `The app needs at least 8 recent runs to tell what you usually score. It counts runs from the two weeks up to your last finished session and leaves out warm-up runs.` | Says what would make it known. |
| Navbar link, page title, browser tab | `Sessions` | One word, as Playlists and Settings. |
| Sessions list, a session | `{start}`, then `{length} · {n} runs · {k} scenarios` | Scenarios, not visits: the count a player would ask for. |
| Sessions list, the session in progress | `In progress`, as a last fragment | A status word. |
| Session detail, heading | `{start} · {length} · {n} runs` | The panel's line, in full. |
| Session detail, second line | `At least {duration} in runs`, such as `At least 57 min in runs` | The minimum is labelled where it is shown. |
| Time in runs, hover | `Adds up the runs you finished. It leaves out the time between runs and any attempt that left no run file.` | Says what makes it a minimum. "Run file" is the on-screen word. |
| Session detail, a visit | `{k}. {scenario}`, then `{n} runs · {length}` | Numbered, because the order is the point. |
| A visit's scenario link, accessible name | `Open {scenario} in Scenario Performance` | The link text alone is a scenario name. |
| Sessions page, no runs | `No sessions yet`, over `Play a scenario in KovaaK's and your session will appear here.` | Title and one sentence, as the chart's empty states. |

Reused, unchanged: the stats-folder hint, "No stats folder configured. Set
it in Settings.", shows on the Sessions page as it does on Scenario
Performance.

Unchanged on purpose: every run toast, the New personal best toast, and
every Chart options label.

### The open questions and carried items

The brainstorm left eight questions for this proposal.

| Question | Where it went |
|---|---|
| Sensitivity: a typical score per sensitivity? | H4. All sensitivities together. Measured: no gain from splitting. |
| The run readout: percentages, a count, or both? | H5. A count. |
| The bar: one global percentage, or per scenario? | Out of scope. The threshold stays one global percentage. The count gives the fact a per-scenario bar would have read, "better than 15 of your last 20", without a rule. A rule the player writes is a product decision of its own under "What would move D3". |
| Siblings of a plateaued scenario | Out of scope. It needs the categories of [PR #338](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/338) and a plateau verdict, which is the Future trend entry. |
| Fixed values or settings? | Fixed. H2 for the 30 minutes, H4 for the 20 runs and the 14 days. |
| One long session filling the window | H4. Measured and left alone. One session supplies 15 or more of the 20 in 27% of full samples, and those miss by 3.4% against 2.3%. A cap of 8 per session doesn't recover it. The sample does not overstate the next session: the player comes in 2.0% above it. |
| Warm-up exclusion per visit | H3. Per visit. |
| The "known" threshold of 8 | H4. Kept as a convention, with the measured curve beside it. |

The maintainer's three statements, and the carry lists of #317 and #327:

| Item | Where it went |
|---|---|
| Notify on every run (2026-09-13) | H5. Every run is reported in its row. No new toast. |
| Feedback against all runs or the session, such as a session PB (2026-09-13) | H5. The row shows the visit's runs in order, so its best is visible. No "session PB" label: the maintainer's review of 2026-09-25 demoted the session comparison. |
| A rolling median in place of the per-day Average line (2026-09-26) | Out of scope, to the Future trend entry and its chart. H4 defines the figure that line would draw, over all runs. |
| Where they look (2026-09-28) | H1 and H6. |
| A highlighted row in place of a toast (an idea, not a lean) | Taken in part. The newest run is bold until the next one lands, with no acknowledged state to store. The toast stays. |
| Define "complete" | H1. |
| Ship the foundation with a useful slice | H1. PR 1 ships the foundation with the session block. |
| A minimum's label survives every surface | Time in runs is shown in one place, always as "At least". |
| Reset files before medians drive verdicts | Out of scope, by the maintainer's word. See [Out of scope](#out-of-scope). |
| Compute the typical run before the Top N filter | H4. It reads every run. |
| Scenario revisions | The typical score and the readout read the current version only. |
| Chart inputs from the surveys | Out of scope, to the trend entry. One is taken: a stated sample count where the window isn't full. |
| Run length is Run History's to build | The foundation. |
| The in-session reading works on a phone | The panel stacks under the chart on a narrow window. Not run in a browser. |
| Bare "session" in the specs | PR 1 changes it to "app session": five lines in `docs/specs/playlists.md` and two in `docs/specs/notifications.md`. |
| The four design checks of #317 | Below. |

The four checks, against the three layouts weighed in H6:

| Check | Panel and a Sessions page | One Run History page | Session in the header |
|---|---|---|---|
| A quick check after a run | Yes, on the page open in play. A player on a playlist table sees the toast only. | No. The player picks this page or the chart. | The session line only, with no scores. |
| Choosing today's focus before any run | Not this milestone's job. The playlist tables stay the planner. | The same. | The same. |
| An immediate session recap | Yes. The panel keeps the session as Last Session, and the page opens on it. | Yes. | Yes, on its page. |
| A scenario over several sessions | Yes, beside the chart. | Yes, away from the chart. | Not until a later slice. |

### Other author-owned choices

- **The ingestion bugs: none is taken on.** `docs/tech_debt.md` lists four
  under [Bugs](../tech_debt.md#bugs). A live run count would show a doubled
  run as two and a missed run as none until a restart, which rebuilds the
  store. In ten weeks of logs neither happened. The parked ingestion
  proposal owns them, and `RunData.stats_file_name` now gives it the file
  identity its fix plan asked for first.
- **The debug-log lines retire with the Sessions page.** That is the PR
  where a session's runs can be reviewed with their marks. It removes
  `_log_run_against_high_score`, `SESSION_LOG_SCORE_THRESHOLD_PCT`, and the
  first-run threshold line. The "Detected new file" line stays: it is
  ingestion evidence, and this proposal used it.
- **Columns per view,** the old proposal's open question. A run shows its
  score and marks, with its time, percentage of PB, run length, accuracy,
  and sensitivity one hover away. Shots fired isn't shown: the parser
  doesn't read it.
- **No percentage across scenarios.** The old proposal normalized the
  session view on the percentage of the PB, so that scenarios could share a
  column. Here a visit's scores sit in one row and are compared only with
  each other, and the percentage stays one hover away. The direction moved
  judgments off the PB, and the typical score is unknown too often to take
  its place (H4).
- **No rule is added anywhere.** The panel shows which run of a visit this
  is and which runs passed the threshold. It doesn't say how many runs to
  play or when to move on.

## Delivery plan

Four implementation PRs. This is intent, not a contract: a boundary that
moves is noted in that PR's description. Each PR updates the specs and the
glossary for what it ships. The last one runs the rest of the Shipping a
proposal checklist and deletes this file.

1. **The foundation and the session block.** Run length on the run record.
   Sessions, visits, and warm-up runs as pure functions. The Run history
   panel with its button, the This Session block, the marks, and the score
   hover. The spec's "app session" wording. Needs H2, H3, and H6.
   Recommended: `claude-opus-5-5` at xhigh. The column's layout has to be
   measured in a browser at 1600×900 and on a narrow window, and reported in
   the PR.
2. **The scenario block.** This Scenario in the same panel, with its paging.
   Needs PR 1 and H1. Recommended: `claude-opus-5-5` at high.
3. **The Sessions page.** The route, the navbar link, the list and the
   detail, time in runs, the mirrored threshold setting, and the retirement
   of the debug-log lines. Needs PR 1 and H6. Recommended:
   `claude-opus-5-5` at high.
4. **The typical score and the readout.** The Scenario Stats row and the
   readout line. Needs PR 1, H4, and H5. Recommended: `claude-opus-5-5` at
   high.

PRs 2, 3, and 4 each depend only on PR 1. The order above is the
recommended one. PRs 3 and 4 touch different pages and can overlap. Two
strings in the session block arrive with the PR that gives them a target:
**Open session** with PR 3, and the readout line with PR 4.

If H1 is ruled the other way, PRs 2 and 3 swap. If H4 or H5 is ruled out,
PR 4 shrinks to the other one, or is dropped.

Each PR gets a fresh-session review. PR 1 sets terms every later feature
inherits, so its author proposes the heavy lane.

## Out of scope

- **Reset files,** by the maintainer's word on 2026-10-05. A KovaaK's
  setting can write a stats file when a run is reset
  ([finding 4](../research/aimcurve_learnings_opus.md#4-a-reset-can-write-a-stats-file-that-looks-like-a-run)
  of the Aimcurve survey). It is an ingestion question, independent of this
  design. The reliable test is a run length under a second, and this work
  makes run length available.
- **Stray CSV copies in the stats folder,** by the maintainer's word on
  2026-10-05. A separate fix is deferred.
- **The four ingestion bugs,** which stay with the parked ingestion
  proposal.
- **The Future entries of the roadmap:** the trend verdict and its chart,
  the rank-up chance, weakness by the typical run, the overview, KovaaK's
  own log, the accuracy guideline, and the per-bot breakdown.
- **Anything that ranks or judges by the typical score.** This milestone
  shows the figure and nothing else.
- **A typical score line on the chart.** It belongs with the trend entry's
  chart.
- **The rank a session's scores reached.** A scenario's ranks come from a
  benchmark, a scenario can sit in several, and a session has no playlist
  selected. The chart's rank lines keep answering for the selected scenario.
- **Speed against accuracy.** product.md lists it as a question the player
  asks. Nothing here answers it.
- **A recommender, or any advice.**
- **A per-scenario score threshold.**
- **Chart interactions,** such as clicking a point to find its row. A design
  note parks them until this milestone ships.
- **Shots fired and kills as run fields.**
- **Whether KovaaK's is open.** A session is defined by runs. The game's own
  log is a Future entry.
- **The Aim Training Journey page.**

## Testing

- **Unit tests for the pure functions,** with the runs given as plain
  records:
  - a gap of exactly 30 minutes, one second under, and one second over;
  - a session across midnight, and two sessions in one day;
  - a run with no start beside runs that have one;
  - a return to a scenario later in the session;
  - a visit of one run;
  - a change of sensitivity inside a visit.
- **Parser tests** on small stats files: a start after the end's time of
  day, a pause, a pause larger than the span, a missing `Challenge Start:`,
  and a length over the limit.
- **The typical score:** 7 and 8 runs, 21 runs, a run 14 days old to the
  second, a run from the session in progress, a mix of versions, and a
  scenario with no `Hash:` at all.
- **The readout:** ties, 2 and 3 earlier runs, a warm-up run, and a
  time-scored scenario.
- **Marks:** each agrees with the toast's verdict and the chart's stars on
  the same runs, with the verdict switch on and off.
- **Page tests** in the style of the existing ones: the panel absent with
  an empty store, the heading on each side of the 30 minutes, the scenario
  block leaving out the open visit, and the Sessions page's empty state.
- **In a browser, by the implementing PR:** the chart's box with the panel
  open at 1600×900, the stacked layout on a narrow window, the panel
  updating when a run lands with no reload, and Chart options opening above
  it.
- **The docs test** holds this file's sections and its links.
- **The scripts under `ignore/scripts/run-history/`** reproduce every
  number in Evidence against the stats folder.
