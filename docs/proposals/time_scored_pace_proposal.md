# Time-Scored Scenarios Are Measured By Pace

Status: Proposed
Date: 2026-09-30

## TL;DR

Some scenarios score the time left on a countdown when the task is done, so a
percentage of the score understates a real improvement many times over. Four
shipped features divide by the score, and they make these scenarios look
closer to the next rank and easier to pass than they are. This proposal
recognizes such a scenario from the performance file KovaaK's writes for each
run, which shows the score counting down, and measures its percentages by
pace: how fast a run finishes compared with the personal best. When the app
can't tell whether a scenario is time-scored, every feature keeps today's
behavior.

## Decisions needed

The maintainer's part of this proposal is in three states:

- **Settled, and not review targets.** The maintainer agreed on 2026-09-28
  that the behavior is a bug and set the constraints listed under
  [Settled by the maintainer](#settled-by-the-maintainer).
- **Ruled.** P8, on 2026-10-04.
- **Open.** P1 and P2. P1 changes a ratified decision, so it needs an
  explicit ruling. The two should be ruled together: the ratified decision's
  own rationale is that the gap and the threshold measure the same way, and
  accepting one alone breaks that.

Everything else is author-owned and open to challenge. Design tags each such
choice with its row ID: P3, P6, P7, P9, and P10. No row is ratified.

### P1 — The Next Rank gap on a time-scored scenario is a pace gap

Status: Open. Amends a ratified decision, #320's D1, in part.

**Recommendation: on a time-scored scenario, the gap is how much faster the
PB run has to finish to reach the next rank.** It is
`(PB time ÷ rank time − 1) × 100`, where each time is the scenario's constant
minus the score. Ground Plaza Sparky V3's PB of 896.17 against Lavender at
899 reads "2.8% faster to Lavender" instead of "+0.4% to Lavender". Every
other row keeps D1 unchanged.

D1 ([2026-09-27](../decision_log.md#2026-09-27-benchmark-tables-show-each-scenarios-rank-and-the-gap-to-the-next-one),
ratified in [#320](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/320))
defines the gap as `(next threshold - PB) / PB * 100`. It gives three
reasons, and this amendment keeps all three:

- It is defined below the first rank. The pace gap is too, as long as both
  times are positive.
- It states the target to beat. "2.8% faster" is that target, in the measure
  the scenario is actually scored on.
- It "matches the Scenario Performance score threshold, which is also a
  percentage of the PB". P2 moves the threshold to pace on the same
  scenarios, so the two still match.

A pace gap and a score gap can share one sorted column because both are a
percentage of the same thing, the PB's throughput
([Why pace and not time](#the-pace-formulas)). The superseding entry should
carry that argument.

Everything else D1's entry fixed stays as it is: the ladder walk, the Rank
column, rounding the display up with a floor of 0.1, the unrounded sort key,
Top rank's precedence, and the tooltip in points. The walk needs no change
because a higher score is always a faster finish, so a threshold's rank
order is the same in pace. One rule narrows: D1 reads `N/A` for a PB of zero
or less, because no percentage of it means anything. A pace gap needs only
positive times, so on a time-scored row that rule applies only when pace is
undefined ([The pace formulas](#the-pace-formulas)). The shipping PR records
the change as a new decision-log entry that supersedes D1 in part. D1's own
text stays as written, with a supersession note.

Choosing differently:

- **Keep D1 as ruled.** The Next Rank column keeps understating these gaps 9
  to 12 times on the maintainer's Viscose rows (table in
  [Problem](#what-goes-wrong)). Sorting ascending, which D1 promises lists
  "the scenarios closest to ranking up", keeps floating all four time-scored
  rows to the top.
- **The gap in seconds** ("2.83 s to Lavender"). It's exact, because on
  these scenarios a point is a second. But it can't be compared across
  scenarios, which is why D1 rejected raw points, and it's already in the
  cell tooltip as "2.83 to go".
- **The gap in percent less time** (`1 − rank time ÷ PB time`, 2.7% for the
  example). It is close at small gaps, but it is not what "faster" means,
  and it would measure differently from P2's percentage of pace.
- **`N/A` on time-scored rows.** Honest, but it drops the one answer the
  column exists for.

### P2 — The Score Threshold on a time-scored scenario is a percentage of PB pace

Status: Open.

**Recommendation: at 95%, a run passes when it is at least 95% as fast as
the PB, which means finishing within the PB's time divided by 0.95.** The
chart line sits at the score that finishes exactly then:
`constant − (constant − PB) × 100 ÷ goal`. The verdict toast reads "88.8% of
PB pace (need 95.0%)" instead of "98.5% of PB". The setting stays one global
percentage, and every scenario that isn't time-scored keeps today's meaning.

The effect on the maintainer's data, as a retrospective: judge every run
after the first, on the six time-scored scenarios with at least five runs,
against the best before it, ignoring the verdict's skip of a sensitivity's
first run. Today's 95% passes 86 of 86 runs. By pace, it
passes 59, or 69%, ranging from 58% to 100% per scenario. On Ground Plaza
Sparky V3 the line moves from 851.37, just above the ladder's first rank, to
890.71, just below Cerulean's threshold of 892.5, the rank the PB holds.

Choosing differently:

- **Keep a percentage of the score.** The verdict keeps passing every run on
  these scenarios, and the line keeps sitting five ranks below the PB.
- **Read the percentage as time.** Taken literally, 95% of the PB's time
  demands a run 5% faster than the PB, the opposite of what the setting
  means. A slack reading, where 95 allows 5% more time, works (a limit of
  109.0 s instead of 109.3 s on Sparky's 103.8 s PB). But it needs a
  translation of the setting that no other scenario uses, and it measures
  differently from P1's "faster".
- **Turn the threshold off on time-scored scenarios.** It loses the verdict
  on exactly the scenarios where the player can't judge it by eye.
- **A separate percentage for time-scored scenarios, or one per scenario.**
  Whether the setting becomes per-scenario is an open Run History question
  and stays out of this proposal.

### P8 — The Aim Training Journey graph keeps its score ratios

Status: Ruled (user), 2026-10-04: defer.

**Ruling: the Aim Training Journey graph is left as it is.** That graph
averages each scenario's best score so far as a share of its PB, the same
ratio this proposal corrects on four other surfaces. The maintainer ruled
the page shelved on 2026-09-28, as recorded in
[#327](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/327):
its code stays, it is reachable only by its URL, and no work on it is
planned. Leaving its ratio alone is a deferral under that ruling. It is
separable from this fix and doesn't block it.

The material consequence: on a playlist that holds time-scored scenarios,
the graph keeps overstating how close earlier runs were to the PB. A plan
that revives the page carries this fix with it.

Rejected:

- **Apply the pace ratio to the graph in this fix.** It would design, build,
  and test work on a page that is ruled shelved.
- **Make the page's removal a prerequisite.** Whether to delete the page's
  code is a separate question that is still open, and a bug fix on four
  live surfaces shouldn't wait on it.

## Problem

### What a time-scored scenario is

A time-scored scenario has no fixed length. It ends when the player finishes
a task, such as killing six bots, and its score is the time left on a clock
that counts down from a constant. So the score is the constant minus the
completion time, and the constant is 1,000 on every such scenario the
maintainer plays.

KovaaK's states this in a file the app doesn't read today. Beside each stats
file, game builds from 3.9.0 write a performance file, a `.perf`, to the
`performances` folder next to the stats folder. KovaaK's publishes its
format, a protobuf schema, at <https://wiki.kovaaks.com/performance.proto>.
Two community tools already read these files, RefleK's and
[Aimcurve](https://github.com/voidfill/aimcurve). The repo's research notes
survey both: the [RefleK's survey](../research/refleks_learnings.md) lists
the file's fields, and an
[Aimcurve survey](../research/aimcurve_learnings_opus.md) found the
time-scored signal used here. The file's header carries the scenario's time
limit, and its events carry the score second by second:

| | Ground Plaza Sparky V3 | VT Controlsphere Intermediate S5 |
|---|---|---|
| Header `time_limit` | 1000 | 60 |
| First score event | +998.999 at 0.994 s | +73 at 0.993 s |
| Later score events | −1.000 each second | gains: +27, +53, +72 |
| Last score event | −0.983 at 116.975 s | +19 at 59.993 s |

On the time-scored run the first event grants the limit minus the time
elapsed, and each later event takes away the time since the one before. The
running score is the time left at every event. On the fixed-length run the
events are points gained.

The maintainer's `performances` folder holds 1,764 files, dated 2026-04-30
to 2026-10-03. Of those, 84 show the countdown, across 10 scenarios: Air
CELESTIAL No UFO Medium and Easier, four Air Pure variants, Air Spectral
Easy and its 85% variant, and Ground Plaza Sparky V3 and its Easy variant.
Ten more scenarios look time-scored from a single older run each, such as
Air CELESTIAL No UFO Easy: that run's score and length sum to about 1,000.
They were last played before performance files existed. Among scenarios with
at least five runs, every other one runs a fixed length, and its score has a
natural zero. One scenario ever scored below zero (VT Quadpulse Entry, −900 in one of
4 runs). None of the 4,384 bundled ladders has a negative threshold.

### What goes wrong

A percentage of a score assumes the score starts at zero. A time-scored
score starts at the constant and falls one point per second. So a change of
a few points is a few seconds, which is a large share of the run's time but
a tiny share of the score. For a small change, the percentage of the score
understates the percentage of pace by a factor of the score divided by the
run's time. That factor runs from 4 to 16 across the 99 runs of the ten
scenarios above.

Five places divide by the score:

| Surface | Code | Today on Ground Plaza Sparky V3 | By pace |
|---|---|---|---|
| Next Rank gap | `benchmark_rank_fields` in `source/kovaaks/playlist_scenarios_service.py` | "+0.4% to Lavender" | "2.8% faster to Lavender" |
| Score threshold chart line, at 95% | `generate_graph` in `source/pages/home.py`, drawn by `add_score_threshold_overlay` in `source/plot/plot_service.py` | 851.37 | 890.71 |
| Threshold verdict toast | `_threshold_verdict` and `_build_live_run_notification` in `source/pages/home.py` | the last run, 883.02, reads "98.5% of PB" and passes | 88.8% of PB pace, below the goal |
| New personal best toast | `_celebration_toast` in `source/app_shell.py` | 884.41 → 896.17 reads "Up 1.3% on your previous best" | 11.3% faster |
| Session debug log | `SESSION_LOG_SCORE_THRESHOLD_PCT` in `source/my_watchdog/file_watchdog.py` | logs the same 95%-of-score pass | the same pace judgment as the toast |

The Next Rank column shows the effect worst, because it sorts across
scenarios. These are the maintainer's time-scored rows on Viscose Benchmark
S2 - Medium:

| Scenario | PB | Next rank | Next Rank shows | By pace, as displayed | Unrounded |
|---|---|---|---|---|---|
| Ground Plaza Sparky V3 | 896.17 | Lavender 899 | +0.4% | 2.8% faster | 2.798% |
| Air CELESTIAL No UFO Medium | 898.17 | Lavender 900 | +0.3% | 1.9% faster | 1.832% |
| Air Spectral Easy | 923.51 | Cerulean 925 | +0.2% | 2.0% faster | 1.982% |
| Air Pure Medium | 914.37 | Cerulean 915.5 | +0.2% | 1.4% faster | 1.343% |

Sorting Next Rank ascending, "closest first", puts these four in the top
four places of the benchmark's 39 rows with a next rank. By pace they would
sit 3rd, 7th, 11th, and 14th on 2026-10-04. The display rounds up, as D1
requires.

### The ratified decisions this amends

- **#320's D1**, quoted under P1. Its rationale ties the gap to the score
  threshold, so the two change together.
- **The verdict formula** of
  [2026-07-08](../decision_log.md#2026-07-08-judge-score-threshold-notifications-against-the-previous-pb):
  `score >= previous_high_score * score_threshold_percentage / 100`. P2
  replaces it on time-scored scenarios only. Its reasons stand: the verdict
  still judges against the previous PB, and still compares exactly rather
  than through the rounded ratio it displays.

### Settled by the maintainer

- **It's a bug, fixed on its own track** (2026-09-28), not as part of the Run
  History proposal.
- **Detect from the player's own runs, not from a hand-kept list**
  (2026-09-28). Accept any constant, not a hard-coded 1,000, because public
  users play scenarios the maintainer doesn't. Fall back to today's behavior
  whenever detection is unsure.
- **Run length is not built here** (2026-10-04). The 2026-09-28 direction was
  to add run length to the run record so Run History could reuse it.
  Detection from the performance file doesn't need it, so it leaves this
  fix, and Run History adds its own when it needs one.

## Design

### The pace formulas

Let `C` be the scenario's constant, read from its performance file
([Detection](#detection-p9)), so a score `s` took `C − s` seconds. Every
percentage that today divides one score by another divides the other way
round on times, and nothing else in the formula changes:

| Surface | Today | Time-scored |
|---|---|---|
| Next Rank gap | `(T − PB) / PB × 100` | `((C − PB) / (C − T) − 1) × 100` |
| Threshold line | `PB × g / 100` | `C − (C − PB) × 100 / g` |
| Verdict passes when | `s × 100 ≥ prev × g` | `(C − prev) × 100 ≥ g × (C − s)` |
| Verdict shows | `s / prev × 100` | `(C − prev) / (C − s) × 100` |
| Personal best gain | `(s / prev − 1) × 100` | `((C − prev) / (C − s) − 1) × 100` |

`T` is the next rank's threshold, `g` the goal percentage, and `prev` the PB
before the run. The chart line keeps using the current PB and the verdict
the previous PB, as today.

**Pace applies only when it is defined.** A surface uses pace when all
three hold:

- the scenario is recognized as time-scored;
- every score in the comparison is eligible, meaning its run belongs to the
  scenario version the constant was read from
  ([What a run record keeps](#what-a-run-record-keeps-p10));
- both times, `C` minus each score, are positive.

Otherwise the surface runs exactly today's code, including today's own `N/A`
and unjudged rules. A time of zero or less needs a score at or above the
constant, which no real run reaches. One consequence is deliberate: on a
time-scored scenario a PB of zero or less still gets a pace percentage,
because only the times have to be positive.

**The exact-boundary rule carries over.** The verdict converts each score
and the constant to decimals before subtracting, then compares the
cross-multiplied form, not the rounded ratio it displays. So a run exactly
at the goal passes, as the 2026-07-08 entry requires. The displayed
percentages keep today's rounding. The gap rounds up with a floor of 0.1. A
verdict keeps both of its caps: a failing one prints at most one tenth below
the goal, and a run below the previous best prints at most 99.9%. The second
cap needs no change, because a run's pace is below the previous best's
exactly when its score is.

**Why pace and not time.** Three reasons, in order of weight:

- A percentage of the PB is a percentage of its throughput on both kinds of
  scenario. On a fixed-length scenario the time is fixed and the score is
  the work done in it, so score ÷ PB score is a ratio of throughput. On a
  time-scored scenario the work is fixed and the time varies, so throughput
  is one over the time, and its ratio to the PB's is the PB's time divided by
  the run's. That is pace. So one global setting keeps one meaning, and a
  pace gap and a score gap can share a sort.
- A higher setting still demands more, and 95% still reads as "95% of my
  best". A time-based reading would need a translation of the setting
  ([P2](#p2--the-score-threshold-on-a-time-scored-scenario-is-a-percentage-of-pb-pace)).
- Every existing formula carries over with the score's ratio replaced by the
  pace's, so the rounding, capping, and boundary rules need nothing new.

**No completion times on screen.** The copy shows scores and percentages
only. The constant is exact, so a completion time could be shown, and it is
left out of scope. These surfaces compare across scenarios, which a
percentage does and a time doesn't.

### What doesn't change

Anything that orders or places scores stays as it is, because a higher score
is always a faster finish. That covers the chart's points and axis, the
Average score line, the PB line, the rank lines, the Rank column, the top-N
placement and `nth_score`, and the celebration's "strictly greater" test.
Only ratios of scores were wrong.

### Detection (P9)

**A scenario is time-scored when the performance file of its newest run that
has one shows the score counting down from the file's time limit.** One run
is enough.

The check reads these fields, by their names in KovaaK's schema: the
header's `schema_version` and `scenario_hash`, its challenge profile's
`time_limit` and `timescale`, and each event's `timestamp` and `score`
delta. The file passes when all three hold:

1. `schema_version` is 1.
2. It has at least two score events.
3. After every score event, the running score is within 0.05 of
   `time_limit − timescale × timestamp`.

The constant `C` is then the file's `time_limit`, and the scenario version
is its `scenario_hash`. If the file fails any condition, or can't be read or
parsed, the app can't tell, and every surface keeps today's behavior.

**What each condition is for:**

- **Condition 3 is the property itself,** checked at every second of the
  run: the score is the time left. A scenario that loses 1.5 points per
  second is half a point off after one second, and fails. So does a
  scenario with no time limit whose score accumulates.
- **Condition 2** is there because one event can't show a score falling.
  The shortest countdown file in the data has 60.
- **Condition 1** turns a format change into "can't tell" instead of a
  misread. All 1,764 files are version 1.
- **`timescale`** is the scenario's own game speed. On the 363 files where
  it isn't 1.0, the time limit counts game time and the timestamps count
  real time: a limit of 54 at 0.9 ends at 60.0 s. So a slowed time-scored
  scenario should lose `timescale` points per real second. No such run is in
  the data, where all 84 countdown files are at 1.0. If the game does
  otherwise, condition 3 fails and the scenario falls back. The pace math
  doesn't depend on it either way: `C − s` is in the score's own clock, and
  a ratio of two times is the same in any clock.

**Which file decides.** The app looks at the scenario's newest run that has
a performance file. That file is found by name: the run's stats file name
with ` Stats.csv` replaced by ` Performance.perf`, in the `performances`
folder beside the stats folder. One file can decide because how a scenario
scores belongs to its definition, which the hash identifies. No scenario in
the data has files of both kinds, and each of the ten has one hash.

**The evidence,** from the maintainer's folders on 2026-10-04:

- **The countdown is unmistakable.** The 84 countdown files stay within
  0.02 of the line at every event. The nearest of the other 1,680 files is
  off by 42.
- **Every countdown file has a time limit of exactly 1,000, and no other
  file does.** Aimcurve, a community tool that reads the same files, reads
  1,000 as KovaaK's value for "no time limit". That reading isn't verified
  here, and the rule doesn't need it.
- **The files pair with the stats files.** Of the 1,757 stats files written
  since the first performance file, 1,756 have one of the same name. The
  last one's performance file is stamped a second later. Eight performance
  files have no stats file: six are attempts of 2 to 22 s that wrote none,
  one is that second-late file, and one is a full run whose stats file is
  missing.
- **The header agrees with the stats file.** On all 1,756 pairs the
  header's hash equals the stats file's `Hash:` and its name equals
  `Scenario:`. The score events sum to the stats file's `Score:` within
  0.004.
- **Scenarios that end early aren't mistaken for time-scored.** VT Plaza
  Viscose ends after six kills, 77 s into a run that could last 120 s, and
  its score events are gains.
- **Performance files start with game build 3.9.0.** The first is dated
  2026-04-30. The 862 runs on build 3.8.7 earlier that month have none.
- **Reading one costs about 0.6 ms** in plain Python, for a median file of
  4.7 KB. The game writes it within 10 ms of the stats file.

**When the app can't tell.** Each of these keeps today's behavior:

- the stats folder has no `performances` folder beside it, as when the
  setting points at a copy of the stats files;
- none of the scenario's runs has a performance file, which is every
  scenario not played since build 3.9.0, the ten older single-run scenarios
  above among them;
- the newest file fails the check, or can't be read or parsed.

A file that can't be read costs only the detection, never the run, and isn't
remembered, so the next look tries again.

**When a run lands.** The watchdog already waits a second before it reads a
new stats file, and by then the performance file is written. The new run's
file is the scenario's newest, so the run is judged by its own file. If that
file is missing, the scenario's newest paired file decides, as on every
other surface. A scenario's first run on a current build therefore flips it
to pace, and its numbers jump then. It flips back only if a newer run's file
fails the check.

**Paused runs.** No countdown file has a pause event, so a paused
time-scored run is untested. The timestamps appear to leave paused time out:
a fixed-length run paused for 7 s still ends at 60.0, and so does one paused
for 2 s. That is an inference from those two runs. The live check adds a
paused
time-scored run, expecting it to be recognized. If it isn't, the scenario
reads "can't tell" until its next unpaused run, and the shipping PR says so.

**Cost and memory.** The app lists the `performances` folder once at
startup and parses nothing then. It parses a file only when a surface asks
about that file's scenario, and remembers the result by file name, because a
written file never changes. A 60-row benchmark table costs about 35 ms the
first time it opens and nothing after. Nothing is written to disk. The run
list it walks is the one `get_personal_best_run` already reads, under the
same accepted concurrency terms
([2026-07-09](../decision_log.md#2026-07-09-accept-unsynchronized-in-memory-stores-single-writer)).

#### Alternatives rejected for detection

- **A hand-kept list of time-scored scenarios.** Settled against: public
  users play scenarios the maintainer doesn't.
- **Inferring it from the stats files.** A stats file gives a run's length
  only as its name's time stamp minus `Challenge Start:` minus
  `Pause Duration:`, precise to about a second. A detector can then fit
  score plus length to a constant across a scenario's runs. This proposal's
  first design did, and it has four weaknesses the performance file doesn't:
  - It needs five runs with a length. Four of the ten recognized scenarios
    have fewer.
  - A fit through noisy lengths can't establish one point per second. A
    steeper slope, or one odd run among tightly clustered ones, can pass.
  - Its constant came out 0.3 to 0.5 s low, which distorts a short run's
    percentages.
  - The stats file can't see a slowed scenario. `Avg Time Dilation:` reads
    1.0 on all 363 runs whose performance file records another timescale.
- **Keeping that inference as a fallback** for scenarios with no performance
  file. On the maintainer's data it would recognize nothing the file
  doesn't, and it would bring a second detector with every weakness above.
- **Other stats-file fields.** `Fight Time:` jumps between several values
  within a scenario. `Time Remaining:` reads 0.0 on every run that carries
  it. `Kills:` is constant on the time-scored scenarios but also on 163
  others.
- **The header alone.** `time_limit` says how long a run may last, not how
  it scores.
- **Requiring a time limit of exactly 1,000.** Aimcurve requires it beside
  the countdown. Here it would hard-code the constant, which is settled
  against, and condition 3 already ties the header to the events.
- **Parsing every file at startup.** It takes a second today and grows with
  every run.

### What a run record keeps (P10)

`RunData` gains two optional fields, read by `extract_data_from_file`: the
scenario's `Hash:` and the stats file's name. It gains no run length. The
field names are the implementer's call.

- **`Hash:`** is on all 8,880 of the maintainer's stats files, back to 2019.
  A file without one still loads, and its score is never eligible.
- **The file name** is how the run's performance file is found.
- **A score is eligible for a pace comparison only when its run's hash
  equals the recognized file's hash.** That covers the row's PB, the chart's
  PB, the verdict's and the celebration's previous best, and the new run. A
  rank threshold comes from the benchmark file and counts as eligible.
- **A PB from an older version of the scenario therefore keeps today's
  numbers** until a run on the current version beats it. The constant was
  read from one version, and nothing shows that another version scores the
  same way. Of the maintainer's 866 scenarios, 15 have more than one hash,
  and none of the ten time-scored ones do.
- **The `performances` folder** is found as the sibling of the stats
  folder. There is no new setting. The app only reads it.

### The surfaces

Each surface below runs pace only under the rule in
[The pace formulas](#the-pace-formulas). Otherwise it runs today's code.

1. **Next Rank (P1).** `benchmark_rank_fields` takes the scenario's constant
   as a new input, where `None` means today's math. The row builder
   computes it where it reads the row's PB, from the local store, so all
   three row paths carry it: phase 1, the fill, and a cancelled fill's
   rebuild. A time-scored row's cell reads "2.8% faster to Lavender". Its
   sort key is the unrounded pace gap, so pace and score gaps sort together
   in one column. The header tooltip gains one sentence (Copy). The cell
   tooltip is unchanged, and "2.83 to go" stays true. Like PB Score, the
   cell stays as it was until the table reopens.
2. **The Score threshold line (P2).** `generate_graph` asks for the selected
   scenario's constant and draws the line at `C − (C − PB) × 100 / g` from
   the current PB. A goal above 100% puts the line above the PB, as today.
   The annotation `Score threshold ({value})` still shows a score.
3. **The threshold verdict (P2).** The watchdog stamps the constant on the
   run's message, and `_threshold_verdict` applies the pace formulas to
   `scenario_previous_best`. On a time-scored scenario, the requirement of a
   positive previous best becomes the requirement that pace be defined. The
   toast says "% of PB pace" (Copy).
4. **The New personal best toast (P3).** `_celebration_toast` reads the same
   stamp and reports the gain as "Finished 11.3% faster than your previous
   best of 884.41." (Copy). What counts as a new PB doesn't change: a
   strictly higher score.
5. **The session debug log (P6).** The watchdog already holds the constant
   for the message on the same code path. So the log's pass or fail line and
   its percentage use the same pace formulas, at the log's fixed 95%. It's
   developer-facing and is retired when Run History ships, but it is the one
   per-run record the maintainer reviews after a session. Left on score, it
   would contradict the toast on exactly these scenarios. Its fixed 95% stays
   a known limit. Log lines aren't copy, so their wording is the
   implementer's.

**The constant travels with the run.** `NewFileMessage` and `RunEventData`
gain the constant as a fact. It is `None` when the scenario isn't
recognized, or when the new run or the previous best isn't eligible. The
watchdog works it out before the message is queued, so the toast agrees with
the chart, which rebuilds after the run lands. Stamping follows the queue's
"facts travel" rule, like `scenario_previous_best`. It also spares the drain
and the page callback a store read of their own. A scenario's first run
carries `None`, because nothing judges or celebrates it.

### Copy (P7)

Every string this design adds or changes. Each is shown only where pace
applies, unless noted. They follow AGENTS.md's nine copy rules.

| Where | String | Why |
|---|---|---|
| Next Rank cell | `{gap}% faster to {rank name}`, such as `2.8% faster to Lavender` | "Faster" names the measure in one word. Keeping "+2.8%" would let a pace number read as a score number, the misreading this fixes. With the tooltip's "2.83 to go" beside it, "+2.8%" would also look like the percentage of those points. A readout, so no period. The gap formats and rounds as D1's does. |
| Next Rank header tooltip, every benchmark table | `How much your PB score has to grow to reach the next rank. When the app can tell a scenario is scored by completion time, it's how much faster you have to finish than your PB. Lower is closer.` | The column holds two measures, and the header names both. The first sentence states the default, so a time-scored scenario the app can't recognize is still described truthfully. "Scored by completion time" describes the scenario in the player's terms instead of introducing the term *time-scored*. |
| Threshold passed | `{scenario}: {score:.2f}, {pct:.1f}% of PB pace. Also your {best\|Nth-best} at {sensitivity}.`, or `... Ready to move on.` when not placed | One added word keeps the sentence the player already reads. |
| Below threshold | `{scenario}: {score:.2f}, {pct:.1f}% of PB pace (need {goal:.1f}%).`, then ` Still your {best\|Nth-best} at {sensitivity}.` when placed | As above. The goal keeps its shape because it is the same setting. |
| New personal best | `{scenario}: {score:.2f}. Finished {pct:.1f}% faster than your previous best of {previous:.2f}.` | "Finished" pairs "faster" with a verb, where "Up" describes a score. The previous best stays a score, the number the player sees in the game. |
| Score threshold percentage help text, on every scenario | `Sets the score goal as a percentage of your personal best. When the app can tell a scenario is scored by completion time, it's a percentage of your personal best's pace instead. The overlay line tracks your current personal best. Notifications judge a run against the personal best you had before the run.` | The setting's meaning changes on these scenarios, and this is where the setting explains itself. The second sentence is the only change, and it promises pace only where the app recognizes the scenario. |

Unchanged on purpose:

- The toast titles "Threshold passed", "Below threshold", and "New personal
  best".
- The chart annotation `Score threshold ({value})`, which still shows a
  score.
- The Next Rank cell tooltip `{rank name} at {threshold} · {points} to go`.
- The Score threshold overlay's help text, "Shows a score goal line based on
  the selected percentage of your current personal best.", which stays true.

### Terms

Each entry below is written as [docs/glossary.md](../glossary.md) would hold
it. The shipping PR moves the three new ones in and replaces the two changed
ones.

New entries:

- **Time-scored scenario.** A scenario scored by the time left on its clock
  when the task is done, so a faster finish scores higher. On one, the app's
  percentages compare pace, not score. How the app recognizes one goes in
  the Scenario Performance spec.
  - On screen: a scenario scored by completion time.
- **Pace.** How fast a run finishes a time-scored scenario, set against
  another run: the other run's time divided by this one's. A run at 95% of
  PB pace takes the PB's time divided by 0.95.
  - On screen: PB pace in a verdict, and faster in the Next Rank column and
    the New personal best toast.
- **Performance file.** The file KovaaK's writes beside a run's stats file,
  recording the run's events second by second. The app reads it only to tell
  whether a scenario is time-scored.
  - Not a run on its own: an abandoned attempt can leave a performance file
    and no stats file.
  - In code: `.perf`, the file's extension.

Changed entries:

- **[Next Rank gap](../glossary.md#next-rank-gap).** How much a benchmark
  scenario's PB has to improve to reach its next rank: as a percentage of the
  PB, such as +4.8% to Gold, or of its pace on a time-scored scenario, such
  as 2.8% faster to Lavender. With every rank reached, it reads Top rank. The
  links and the two bullets stay.
- **[Score threshold](../glossary.md#score-threshold).** A score goal set as
  a percentage of the PB, or of the PB's pace on a time-scored scenario. The
  links and the two bullets stay.

## Out of scope

- **Run History:** sessions, visits, the typical score, the run readout, a
  run length field, and whether the threshold becomes per-scenario.
- **A per-bot breakdown** for time-scored kill scenarios.
- **Showing completion times anywhere.**
- **Anything else the performance file holds,** such as plots of a run's
  score from second to second.
- **The Aim Training Journey graph,** deferred under P8.
- **Scenarios the app can't recognize.** A scenario whose score isn't the
  time left on its clock isn't recognized, whatever else its score does.
  Neither is one with no performance file. Both keep today's behavior.
- **The roadmap entry.** The parallel product-direction PR lists this fix
  under Upcoming. The shipping PR moves it, and this PR doesn't touch the
  roadmap.

## Delivery plan

One implementation PR, after P1 and P2 are ruled and this proposal merges.
It has no other dependency and can run beside the Run History work.
Recommended implementer: `claude-opus-5-5` at high. Once the rows are ruled,
the change is specified down to its strings, and unit tests plus one live
check verify it.

- **Code:**
  - a reader for the performance file and the countdown check, as pure
    functions in a small Dash-free module with no new dependency;
  - the two new fields on the run record, and the `performances` folder
    lookup;
  - the constant on `NewFileMessage` and `RunEventData`, stamped by the
    watchdog;
  - the four surfaces and the debug log;
  - the two copy changes to help and header text.
- **Tests:** listed under Testing.
- **Shipping docs, in the same PR:**
  - a decision-log entry, opening with its layer-1 summary. It supersedes in
    part #320's D1 and the 2026-07-08 verdict formula, for time-scored
    scenarios. Each of those entries gains a supersession note after its
    summary, and its text stays as written. The entry also records the file
    facts the app relies on, with the schema's address.
  - `docs/specs/playlists.md` for Next Rank, `docs/specs/scenario_performance.md`
    for the threshold line and for how a scenario is recognized, and
    `docs/specs/notifications.md` for the verdict, the New personal best
    toast, and the constant the message carries. `docs/specs/settings.md`
    owns the stats folder and gains the `performances` folder beside it. Each
    spec's summary is checked against its payload change.
  - `docs/glossary.md`: the Terms block above.
  - `docs/user_guide.md`: the "faster" reading in the Next Rank paragraph,
    and when the app can tell, which is after one run of the scenario on a
    current KovaaK's build.
  - `docs/architecture.md`: the new module, the run record's fields, the
    message's new fact, and `benchmark_rank_fields`'s new input.
  - the rest of the Shipping a proposal checklist in AGENTS.md: the product
    inventory, the roadmap entry moved to Shipped, references to this file,
    and deleting this file.
  - the interim-log comment on `SESSION_LOG_SCORE_THRESHOLD_PCT`, which
    should say the log judges time-scored scenarios by pace.
- **New copy:** any string this proposal didn't foresee is listed under "New
  copy" in the PR body.

## Testing

Each surface gets a time-scored case, an unchanged score case, and a
"can't tell" fallback. The existing tests for the score cases stay as they
are. They are the "unchanged" half.

- **The reader and the check,** on small real files kept as fixtures plus
  files a test helper builds:
  - a real countdown file returns its time limit and its hash;
  - a real fixed-length file returns nothing;
  - a scenario losing 1.5 points per second, built as 250 − 1.5 × t, returns
    nothing;
  - a file whose first event grants the limit and whose later events are
    gains returns nothing;
  - a slowed countdown, built to lose 0.9 points per second at a timescale
    of 0.9, returns its limit, and the same file at a timescale of 1.0
    returns nothing;
  - a short countdown of seven events returns its limit;
  - one score event, no score events, a `schema_version` of 2, truncated
    bytes, and an empty file each return nothing and never raise.
- **The scenario's answer:** the newest run with a file decides; a newest
  run with no file falls to the next; a stats folder with no `performances`
  folder beside it recognizes nothing; a file that can't be read isn't
  remembered.
- **Eligibility:** a PB whose hash differs from the file's keeps today's
  numbers on the row and the chart; a previous best whose hash differs keeps
  today's verdict and toast; a stats file with no `Hash:` still loads.
- **The pace helpers:** each formula in the table, and "undefined" when
  either time is zero or less. A PB of 999 against a threshold of 999.25 at a
  constant of 1,000 reads "33.4% faster".
- **Next Rank** (`tests/test_playlist_scenarios_service.py`): a PB of 896.2
  against Lavender 899 at a constant of 1,000 reads "2.8% faster to
  Lavender" (unrounded 2.772), with the unrounded sort key. A constant of
  `None` reads "+0.4% to Lavender". The round-up and the floor apply to a
  pace gap. A pace gap that is undefined falls back to D1. The Rank column
  is the same with and without a constant. The three row paths carry the
  same Next Rank for a time-scored scenario.
- **The threshold line:** a PB of 896.2 at 95% with a constant of 1,000
  draws at 890.74. With no constant, it draws at 851.39 as today.
- **The verdict** (`tests/test_home_run_events.py`): a pass and a fail by
  pace, with "% of PB pace" in the message. A run of 900 against a previous
  best of 905 at 95% passes exactly at the goal. A run just short of the
  previous best reads "99.9% of PB pace", never "100.0%". With no constant,
  the message reads "% of PB". A time-scored previous best of zero or less is
  still judged when pace is defined.
- **The New personal best toast** (`tests/test_app_shell_run_events.py`):
  "Finished 11.3% faster than your previous best of 884.41." for 884.41 →
  896.17 at a constant of 1,000; with no constant, today's "Up 1.3% on your
  previous best of 884.41."
- **The watchdog:** the message carries the constant read from the new
  run's own file. It carries `None` on a scenario's first run, and when the
  previous best isn't eligible. The debug log judges a time-scored run by
  pace.
- **Gates:** AGENTS.md's five local checks, including the docs test and the
  em-dash guard.
- **Live check:** on the maintainer's stats folder, open Viscose Benchmark
  S2 - Medium and sort Next Rank ascending. The four time-scored rows read
  "faster" and no longer fill the top four places. Open Ground Plaza Sparky
  V3 on Scenario Performance and check that the threshold line sits near
  890.7. Play a time-scored run and read the toast. Then pause one partway
  through and confirm the scenario is still recognized.
