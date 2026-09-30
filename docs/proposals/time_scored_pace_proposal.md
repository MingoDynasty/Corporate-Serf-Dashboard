# Time-Scored Scenarios Are Measured By Pace

Status: Proposed
Date: 2026-09-30

## TL;DR

Some scenarios score a constant minus the completion time, so a percentage of
the score understates a real improvement many times over. Four shipped
features divide by the score, and they make these scenarios look closer to
the next rank and easier to pass than they are. This proposal recognizes such
scenarios from the player's own runs, where the score plus the run's length
stays constant, and measures their percentages by pace: how fast a run
finishes compared with the personal best. When the runs can't settle whether
a scenario is time-scored, every feature keeps today's behavior.

## Decisions needed

Two rulings. Nothing in this proposal is ratified. The maintainer agreed on
2026-09-28 that the behavior is a bug and settled three constraints, listed
under [Settled](#settled-maintainer-2026-09-28). Every design choice below is
open. P1 changes a ratified decision, so it needs an explicit ruling. P1 and
P2 should be ruled together: the ratified decision's own rationale is that
the gap and the threshold measure the same way, and accepting one alone
breaks that. Everything else, including the detection rule and the Copy
block, is author-owned and open to challenge. Design tags each author-owned
choice with its row ID, P3 to P7.

### P1 — The Next Rank gap on a time-scored scenario is a pace gap

Status: Open. Amends a ratified decision, #320's D1, in part.

**Recommendation: on a time-scored scenario, the gap is how much faster the
PB run has to finish to reach the next rank.** It is
`(PB time ÷ rank time − 1) × 100`, where each time is the scenario's constant
minus the score. Ground Plaza Sparky V3's PB of 896.17 against Lavender at
899 reads "2.9% faster to Lavender" instead of "+0.4% to Lavender". Every
other row keeps D1 unchanged.

D1 ([2026-09-27](../decision_log.md#2026-09-27-benchmark-tables-show-each-scenarios-rank-and-the-gap-to-the-next-one),
ratified in [#320](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/320))
defines the gap as `(next threshold - PB) / PB * 100`. It gives three
reasons, and this amendment keeps all three:

- It is defined below the first rank. The pace gap is too, as long as both
  times are positive.
- It states the target to beat. "2.9% faster" is that target, in the measure
  the scenario is actually scored on.
- It "matches the Scenario Performance score threshold, which is also a
  percentage of the PB". P2 moves the threshold to pace on the same
  scenarios, so the two still match.

Everything else D1's entry fixed stays as it is: the ladder walk, the Rank
column, rounding the display up with a floor of 0.1, the unrounded sort key,
Top rank's precedence, and the tooltip in points. The walk needs no change
because a higher score is always a faster finish, so a threshold's rank
order is the same in pace. One rule narrows: D1 reads `N/A` for a PB of zero
or less, because no percentage of it means anything. A pace gap needs only
positive times, so on a time-scored row that rule applies only when pace is
undefined ([The pace formulas](#the-pace-formulas)). The shipping PR records the
change as a new decision-log entry that supersedes D1 in part. D1's own text
stays as written, with a supersession note.

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
`constant − (constant − PB) × 100 ÷ goal`. The verdict toast reads "88.7% of
PB pace (need 95.0%)" instead of "98.5% of PB". The setting stays one global
percentage, and every scenario that isn't time-scored keeps today's meaning.

The effect on the maintainer's data: replay every run after the first on
the six detected scenarios against the best before it, ignoring the
verdict's skip of a sensitivity's first run. Today's 95% passes 78 of 78
runs. By pace, it passes 55, or 71%, ranging from 58% to 100% per scenario.
On Ground Plaza Sparky V3 the line moves from 851.37, just above the
ladder's first rank, to 890.73, just below Cerulean's threshold of 892.5,
the rank the PB holds.

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

## Problem

### What a time-scored scenario is

A time-scored scenario ends when the player finishes a task, such as killing
six bots, and scores a constant minus the time it took. KovaaK's writes no
scoring type anywhere the app can read. It keeps a scenario's `.sce` file on
disk only when the player edited that scenario locally.

The runs show the shape. Run length, meaning the time stamp in the stats
file's name minus the file's `Challenge Start:` minus its `Pause Duration:`,
was checked against all 866 scenarios in the maintainer's stats folder on
2026-09-28 and again on 2026-09-30. Every scenario whose lengths vary across
its runs, and not through one odd run, fits score + run length ≈ 1,000:

| Scenario | Runs with a length | Median of score + length | Largest distance from it | Lengths span | Correlation of score and length |
|---|---|---|---|---|---|
| Air CELESTIAL No UFO Medium | 37 | 999.56 | 0.53 s | 36.8 s | −0.999 |
| Air Pure Easier No UFO | 6 | 999.56 | 0.41 s | 8.2 s | −0.997 |
| Air Pure Intermediate | 8 | 999.71 | 0.39 s | 29.5 s | −1.000 |
| Air Pure Intermediate Slower No UFO | 4 | 999.53 | 0.44 s | 8.6 s | −0.999 |
| Air Pure Medium | 6 | 999.48 | 0.43 s | 15.9 s | −0.999 |
| Air Spectral Easy | 5 | 999.48 | 0.49 s | 13.1 s | −0.999 |
| Ground Plaza Sparky V3 | 11 | 999.58 | 0.53 s | 22.9 s | −0.999 |

The first survey reported six such scenarios because it required five runs
with a length. Air Pure Intermediate Slower No UFO is a seventh, with four.
Thirteen more have a single run each whose score and length sum to about
1,000 at a length that is neither 30 nor 60 s, such as Air CELESTIAL No UFO
Easy. They are likely time-scored too, but one run can't show it. Among
scenarios with at least 5 runs, every other one runs a fixed length, 60 s for
most and 30 s or 39–50 s for the rest, and its score has a natural zero. One
scenario ever scored below zero (VT Quadpulse Entry, −900 in one of 4 runs).
None of the 4,384 bundled ladders has a negative threshold.

### What goes wrong

A percentage of a score assumes the score starts at zero. A time-scored
score starts at the constant and falls one point per second. So a change of
a few points is a few seconds, which is a large share of the run's time but
a tiny share of the score. For a small change, the percentage of the score
understates the percentage of pace by a factor of the score divided by the
run's time. That factor runs from 6 to 16 across the runs of the seven
scenarios above.

Five places divide by the score:

| Surface | Code | Today on Ground Plaza Sparky V3 | By pace |
|---|---|---|---|
| Next Rank gap | `benchmark_rank_fields` in `source/kovaaks/playlist_scenarios_service.py` | "+0.4% to Lavender" | "2.9% faster to Lavender" |
| Score threshold chart line, at 95% | `generate_graph` in `source/pages/home.py`, drawn by `add_score_threshold_overlay` in `source/plot/plot_service.py` | 851.37 | 890.73 |
| Threshold verdict toast | `_threshold_verdict` and `_build_live_run_notification` in `source/pages/home.py` | the last run, 883.02, reads "98.5% of PB" and passes | 88.7% of PB pace, below the goal |
| Personal best toast | `_celebration_toast` in `source/app_shell.py` | 884.41 → 896.17 reads "Up 1.3% on your previous best" | 11.4% faster |
| Session debug log | `SESSION_LOG_SCORE_THRESHOLD_PCT` in `source/my_watchdog/file_watchdog.py` | logs the same 95%-of-score pass | the same pace judgment as the toast |

The Next Rank column shows the effect worst, because it sorts across
scenarios. These are the maintainer's time-scored rows on Viscose Benchmark
S2 - Medium:

| Scenario | PB | Next rank | Next Rank shows | By pace, as displayed | Unrounded, detected constant | Unrounded, constant 1,000 |
|---|---|---|---|---|---|---|
| Ground Plaza Sparky V3 | 896.17 | Lavender 899 | +0.4% | 2.9% faster | 2.809% | 2.798% |
| Air CELESTIAL No UFO Medium | 898.17 | Lavender 900 | +0.3% | 1.9% faster | 1.840% | 1.832% |
| Air Spectral Easy | 923.51 | Cerulean 925 | +0.2% | 2.0% faster | 1.996% | 1.982% |
| Air Pure Medium | 914.37 | Cerulean 915.5 | +0.2% | 1.4% faster | 1.351% | 1.343% |

Sorting Next Rank ascending, "closest first", puts these four in the top
four places of the benchmark's 39 rows with a next rank. By pace they would
sit 2nd, 5th, 6th, and 10th. The two unrounded columns differ because the
app measures the constant from the runs, and the measured constant sits
about 0.4 s below 1,000 ([The constant](#the-constant)). The display rounds
up, as D1 requires, so 2.809% reads 2.9%.

### The ratified decisions this amends

- **#320's D1**, quoted under P1. Its rationale ties the gap to the score
  threshold, so the two change together.
- **The verdict formula** of
  [2026-07-08](../decision_log.md#2026-07-08-judge-score-threshold-notifications-against-the-previous-pb):
  `score >= previous_high_score * score_threshold_percentage / 100`. P2
  replaces it on time-scored scenarios only. Its reasons stand: the verdict
  still judges against the previous PB, and still compares exactly rather
  than through the rounded ratio it displays.

### Settled (maintainer, 2026-09-28)

- **It's a bug, fixed on its own track,** not as part of the Run History
  proposal.
- **Detect from the runs, not from a hand-kept list.** Accept any constant,
  not a hard-coded 1,000, because public users play scenarios the maintainer
  doesn't. Fall back to today's behavior whenever detection is unsure.
- **Build run length so Run History can reuse it,** as a field on the run
  record. Sessions, visits, and typical scores are not designed here.

## Design

### Terms

The glossary's convention for new terms is still under review in a parallel
PR. This block follows it either way. The PR that ships this proposal moves
these terms into the glossary if it exists by then.

- **Time-scored scenario:** a scenario whose score is a constant minus the
  run's length, so a faster finish scores higher. The app recognizes one only
  from the player's own runs ([Detection](#detection-p4)). The constant is
  1,000 on every one the maintainer plays, but the app doesn't assume it.
  Most scenarios run for a fixed time and score what the player does in it.
  A time-scored one runs until the task is done.
- **Run length:** how long one run took, in seconds. It is the time stamp in
  the stats file's name, which is the run's end, minus `Challenge Start:`,
  minus `Pause Duration:`. It is precise to about a second. It is unknown for
  a run whose file lacks those fields and for runs from game builds 2.0.3 to
  2.0.5.
- **Pace:** how fast a run finishes, the inverse of its time. On a
  time-scored scenario, the app's percentages compare paces. A run's
  percentage of PB pace is the PB's time divided by the run's time, times
  100. "2.9% faster" means a pace 2.9% higher.

### The pace formulas

Let `C` be the scenario's detected constant, so a score `s` took `C − s`
seconds. Every percentage that today divides one score by another divides
the other way round on times, and nothing else in the formula changes:

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

**Pace applies only when it is defined.** A surface uses pace when the
scenario is detected as time-scored and both of its times, `C` minus each
score, are positive. Otherwise it runs exactly today's code, including
today's own `N/A` and unjudged rules. A time of zero or less needs a score
at or above the constant, which no real run reaches. The guard exists so a
misdetected constant can only fall back, never divide wrong. One consequence
is deliberate: on a time-scored scenario a PB of zero or less still gets a
pace percentage, because only the times have to be positive.

**The exact-boundary rule carries over.** The verdict compares the
cross-multiplied form, not the rounded ratio it displays, so a run exactly
at the goal passes, as the 2026-07-08 entry requires. The displayed
percentages keep today's rounding: the gap rounds up with a floor of 0.1, and
a failing verdict is capped one tenth below the goal as printed.

**Why pace and not time.** Three reasons, in order of weight:

- A higher setting still demands more, and 95% still reads as "95% of my
  best". A time-based reading would need a translation of the setting
  ([P2](#p2--the-score-threshold-on-a-time-scored-scenario-is-a-percentage-of-pb-pace)).
- Every existing formula carries over with the score's ratio replaced by the
  pace's, so the rounding, capping, and boundary rules need nothing new.
- It is the measure the maintainer's own training research uses: pace is PB
  time divided by run time, and the bar is `1000 − (1000 − PB) / 0.95`.

**No seconds on screen.** The copy shows scores and percentages only. The
constant is measured, and a time shown to the player would carry its error
in full ([The constant](#the-constant)). Percentages barely feel it.

### What doesn't change

Anything that orders or places scores stays as it is, because a higher score
is always a faster finish. That covers the chart's points and axis, the
Average score line, the PB line, the rank lines, the Rank column, the top-N
placement and `nth_score`, and the celebration's "strictly greater" test.
Only ratios of scores were wrong.

### Detection (P4)

**A scenario is time-scored when its runs with a known length meet all four
conditions:**

1. There are at least 5 of them.
2. For every one, the score plus the run length is within 2 s of the median
   of those sums. That median is the constant `C`.
3. Their lengths span at least 5 s, from the shortest to the longest.
4. Their scores and lengths correlate at −0.9 or below (Pearson).

Otherwise detection is unsure, and every surface keeps today's behavior. The
inputs are all of the scenario's stored runs at every sensitivity, because
the constant doesn't depend on sensitivity. A run without a known length
counts neither for nor against: Ground Plaza Sparky V3 has 22 runs, 11 of
them from 2020 files with no `Challenge Start`, and it is detected from the
other 11.

**What each condition excludes.** The false positive to design out is a
fixed-length scenario whose scores barely vary: its lengths and scores are
both nearly constant, so their sum is too. Condition 2 alone doesn't stop
it. Condition 3 does.

- The fixed-length scenarios with the tightest scores, among those with 5+
  runs with a length, are tamTargetSwitch Smooth Easy (score SD 1.1 over 5
  runs) and Controlswitch Intermediate (SD 1.3 over 7). All 5 of the first
  one's sums lie within 2 s of their median, so it passes condition 2
  outright, and 6 of the second one's 7 do. Their lengths span 0.6 s and
  0.75 s, and condition 3 rejects both.
- Correlation alone doesn't stop it either. VT 1w2ts Vertical Small
  correlates at −0.93 over 8 runs whose lengths span 0.9 s: noise lining up.
  So the span is what separates the shapes. The correlation keeps one
  odd-length run from lending the whole set its slope, which the span alone
  would allow.
- The only non-time-scored scenario whose lengths vary by more than a few
  seconds is VT ww5t Novice S5. One unexplained 128 s run sits among its
  60 s runs, and its sums stray as far as 168 points from their median, so
  condition 2 rejects it.
- As a check against chance, every window of 5 consecutive runs with a
  length was tested in each of the 312 other scenarios with at least 5 such
  runs. None of the 5,970 windows passes.

**The values are margins, not fitted boundaries.** A tolerance of 1.5 s, a
span of 3 s, or a correlation of −0.8 each gives the same result on this
corpus. Lowering the minimum to 3 or 4 runs adds only the seventh scenario,
which really is time-scored. The margins are set for players and scenarios
outside the maintainer's library:

- **Tolerance, 2 s.** Each of the two whole-second fields, the file name's
  time stamp and `Pause Duration`, adds under a second of error, so together
  they stay under 2 s. That is about four times the largest distance seen,
  0.53 s over the 77 runs above.
- **Span, 5 s.** On the 312 other scenarios, lengths span a median of 0.9 s.
  The widest fixed-length span is 3.3 s, from a single 56.6 s run among the
  121 of VT DotTS Intermediate S5 Hard. Five seconds clears it, and every
  time-scored scenario above spans at least 8.2 s.
- **Minimum runs, 5.** Fewer runs make it likelier that some public
  scenario whose length varies lines up by chance. The cost is that a
  time-scored scenario keeps today's numbers until its fifth run with a
  length. That covers Air Pure Intermediate Slower No UFO and the thirteen
  single-run scenarios that look time-scored.

**Every run must fit, not a share of them.** One run off the line turns
detection off for that scenario for as long as its file stays in the stats
folder. A share, say 90%, would tolerate a glitch. But it would also accept
a scenario whose shape changed partway through its history, and then the PB
could come from the old shape, where pace math means nothing. No such glitch
appears in the 77 runs, and falling back is the settled answer to doubt.

**The scenario's hash is ignored.** Each stats file carries a `Hash:` of the
scenario's definition. 15 of the maintainer's 866 scenarios have more than
one, and none of the time-scored ones do. Detection pools every version
under the name, as the PB, the ladder, and the chart already do. A version
change that moves the constant or the scoring shape puts later runs off the
line, so detection falls back. Detecting per hash was rejected: it would
compute the constant from one version and apply it to a PB that may come
from another.

**No cache.** Detection runs on demand over the in-memory runs. Over the
whole library, 810 scenarios with up to 463 runs each, a plain-Python version
takes about 1 ms. A cache would need clearing on every new run and buy
nothing measurable. It reads the same per-scenario run list
`get_personal_best_run` already reads, under the same accepted concurrency
terms
([2026-07-09](../decision_log.md#2026-07-09-accept-unsynchronized-in-memory-stores-single-writer)).

**When detection flips.** A scenario becomes detected on its fifth run with
a length, if the runs fit, and its numbers jump from score to pace then. It
flips back only if a later run lands off the line. Next Rank updates when
the table reopens, as PB Score does. The chart updates on its next rebuild,
and each verdict uses the state at its own run.

#### The constant

`C` is the median of score + run length, not a rounded or corrected value.
The measured medians sit 0.29 to 0.52 s below 1,000. The file name's whole
seconds are the likely cause, but that is an inference, not a verified
mechanism. The error barely moves a percentage. On Sparky, using 999.58
instead of 1,000 moves the gap by 0.011 percentage points and the 95% line
by 0.02 points. Rounding the median to an integer was rejected: it would
assume the constant is an integer, and 999.48 rounds to 999. Adding half a
second first would build the unverified mechanism into the math.

#### Alternatives rejected for detection

- **A hand-kept list of time-scored scenarios.** Settled against: public
  users play scenarios the maintainer doesn't.
- **`Fight Time:` as the length.** Every file since 2019 carries it, and
  score + `Fight Time` is often constant to the hundredth. But within a
  scenario it jumps between several values. On Air CELESTIAL's last 8 runs
  it ranges over 2.28 points, from 995.90 to 998.18, where the file-name
  length ranges over 0.88. So it measures something narrower than the scored
  time. It might be the time a target is alive, but that is unverified. Run
  History also wants wall-clock length, which `Fight Time` isn't.
- **Fitting a regression slope of −1.** It gives the same answer on this data
  as conditions 2 and 4, but it is harder to explain. The constant sum states
  the property directly.
- **Any slope other than −1.** A scenario scoring, say, 10 points per second
  fails condition 2 and falls back. None appears in the data, and
  generalizing would add a parameter to detect.

### Run length on the run record (P5)

`RunData` gains an optional field, `run_length_seconds: float | None`, parsed
by `extract_data_from_file`. Run History reuses it. Its only consumer here is
detection. The name is the implementer's call.

- **Inputs.** The run's end is the time in the file's name (whole seconds,
  local time). `Challenge Start:` is the local time of day with
  milliseconds, such as `18:02:30.895`. `Pause Duration:` is whole seconds.
  `Game Version:` names the build.
- **Formula.** The end's time of day minus `Challenge Start`, plus 24 hours
  if that is negative, because the run crossed midnight. Then minus
  `Pause Duration`.
- **Unknown (`None`)** when `Challenge Start` or `Pause Duration` is missing
  or doesn't parse, when the build is 2.0.3, 2.0.4, or 2.0.5, or when the
  result isn't positive.
- **It never costs the run.** A bad length field loses only the length, as
  a bad `Sens Increment` or `DPI` loses only the sensitivity conversion.
- **Clock changes.** Both times are local wall-clock time, so a run that
  spans a daylight-saving change reads an hour off. Detection then falls
  back for that scenario. That is rare, and the fallback is today's
  behavior.

The evidence for the unknown cases, from the maintainer's 8,682 parseable
files:

- **No `Challenge Start`:** 463 files, all from builds 1.0.8, 2.0.1, and
  2.0.2 (2019–2020).
- **2.0.3 and 2.0.4** (51 files) carry `Challenge Start` but no
  `Pause Duration`. One 2.0.3 run would compute as 86,399.5 s, a false
  midnight wrap.
- **2.0.5** (56 files) records spans of about 60 s from `Challenge Start`
  to the file's time, but a `Pause Duration` of 21 to 207 s. So its pause
  field can't be the run's own pause, and subtracting it gives a median of
  −542 s. Some of these runs still come out positive, so the positive-result
  check alone would miss them and the build check stays.
- **Every 3.x file** (December 2024 on) has all three fields, and their
  lengths run from 29 to 238 s. The data holds no files from builds 2.1 to
  3.6. A bad length from one of those builds would fail condition 2, so
  detection would fall back rather than misfire.

### The surfaces

Each surface below runs pace only under the rule in
[The pace formulas](#the-pace-formulas). Otherwise it runs today's code.

1. **Next Rank (P1).** `benchmark_rank_fields` takes the scenario's constant
   as a new input, where `None` means today's math. The row builder
   computes it where it reads the row's PB, from the local store, so all
   three row paths carry it: phase 1, the fill, and a cancelled fill's
   rebuild. A time-scored row's cell reads "2.9% faster to Lavender". Its
   sort key is the unrounded pace gap, so pace and score gaps sort together
   in one column, each measuring the scenario on its own scoring. The
   header tooltip gains one sentence (Copy). The cell tooltip is unchanged,
   and "2.83 to go" stays true.
2. **The Score threshold line (P2).** `generate_graph` asks for the selected
   scenario's constant and draws the line at `C − (C − PB) × 100 / g` from
   the current PB. A goal above 100% puts the line above the PB, as today.
   The annotation `Score threshold ({value})` still shows a score.
3. **The threshold verdict (P2).** The watchdog stamps the constant on the
   run's message, and `_threshold_verdict` applies the pace formulas to
   `scenario_previous_best`. On a time-scored scenario, the requirement of a
   positive previous best becomes the requirement that pace be defined. The
   toast says "% of PB pace" (Copy).
4. **The personal best toast (P3).** `_celebration_toast` reads the same
   stamp and reports the gain as "Finished 11.4% faster than your previous
   best of 884.41." (Copy). What counts as a new PB doesn't change: a
   strictly higher score.
5. **The session debug log (P6).** The watchdog already computes the
   constant for the message on the same code path. So the log's pass or fail
   line and its percentage use the same pace formulas, at the log's fixed
   95%. It's developer-facing and is retired when Run History ships, but it
   is the one per-run record the maintainer reviews after a session. Left on
   score, it would contradict the toast on exactly these scenarios. Log
   lines aren't copy, so their wording is the implementer's.

**The constant travels with the run.** `NewFileMessage` and `RunEventData`
gain the constant as a fact, `None` when the scenario isn't detected. The
watchdog judges it over the scenario's stored runs plus the new one, before
the message is queued. That makes the toast agree with the chart, which
rebuilds after the run lands. Stamping follows the queue's "facts travel"
rule, like `scenario_previous_best`. It also spares the drain and the page
callback a store read of their own. A scenario's first run carries `None`,
because nothing judges or celebrates it.

### Copy (P7)

Every string this design adds or changes, all shown only on a time-scored
scenario unless noted. They follow AGENTS.md's nine copy rules.

| Where | String | Why |
|---|---|---|
| Next Rank cell | `{gap}% faster to {rank name}`, such as `2.9% faster to Lavender` | "Faster" names the measure in one word. Keeping "+2.9%" would let a pace number read as a score number, the misreading this fixes. With the tooltip's "2.83 to go" beside it, "+2.9%" would also look like the percentage of those points. A readout, so no period. The gap formats and rounds as D1's does. |
| Next Rank header tooltip, every benchmark table | `How much your PB score has to grow to reach the next rank. On a scenario scored by completion time, it's how much faster you have to finish than your PB. Lower is closer.` | The column now holds two measures, and the header names both. "Scored by completion time" describes the scenario in the player's terms instead of introducing the term *time-scored*. |
| Threshold passed | `{scenario}: {score:.2f}, {pct:.1f}% of PB pace. Also your {best\|Nth-best} at {sensitivity}.`, or `... Ready to move on.` when not placed | One added word keeps the sentence the player already reads. |
| Below threshold | `{scenario}: {score:.2f}, {pct:.1f}% of PB pace (need {goal:.1f}%).`, then ` Still your {best\|Nth-best} at {sensitivity}.` when placed | As above. The goal keeps its shape because it is the same setting. |
| New personal best | `{scenario}: {score:.2f}. Finished {pct:.1f}% faster than your previous best of {previous:.2f}.` | "Finished" pairs "faster" with a verb, where "Up" describes a score. The previous best stays a score, the number the player sees in the game. |
| Score threshold percentage help text, on every scenario | `Sets the score goal as a percentage of your personal best. On a scenario scored by completion time, it's a percentage of your personal best's pace instead. The overlay line tracks your current personal best. Notifications judge a run against the personal best you had before the run.` | The setting's meaning changes on these scenarios, and this is where the setting explains itself. The second sentence is the only change. |

Unchanged on purpose:

- The toast titles "Threshold passed", "Below threshold", and "New personal
  best".
- The chart annotation `Score threshold ({value})`, which still shows a
  score.
- The Next Rank cell tooltip `{rank name} at {threshold} · {points} to go`.
- The Score threshold overlay's help text, "Shows a score goal line based on
  the selected percentage of your current personal best.", which stays true.

## Out of scope

- **Run History:** sessions, visits, the typical score, the run readout, and
  whether the threshold becomes per-scenario.
- **A per-bot breakdown** for time-scored kill scenarios.
- **Showing completion times anywhere.** The constant's error would show in
  full ([The constant](#the-constant)).
- **The Aim Training Journey graph,** which also averages percentages of
  scores. The maintainer leans toward retiring that page, so it isn't
  touched here.
- **Scenarios that lose some other number of points per second, and
  time-dilated scenarios.** Both fail condition 2 and keep today's behavior.
  Every file in the data records a time dilation of 1.0 or none at all.
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
  - the run length field and its parse;
  - detection and the pace helpers, as pure functions in a small Dash-free
    module, with an accessor on the store;
  - the constant on `NewFileMessage` and `RunEventData`, stamped by the
    watchdog;
  - the four surfaces and the debug log;
  - the two copy changes to help and header text.
- **Tests:** listed under Testing.
- **Shipping docs, in the same PR:**
  - a decision-log entry, opening with its layer-1 summary. It supersedes in
    part #320's D1 and the 2026-07-08 verdict formula, for time-scored
    scenarios. Each of those entries gains a supersession note after its
    summary, and its text stays as written.
  - `docs/specs/playlists.md` for Next Rank, `docs/specs/scenario_performance.md`
    for the threshold line, and `docs/specs/notifications.md` for the
    verdict, the personal best toast, and the constant the message carries.
    Each spec's summary is checked against its payload change.
  - `docs/user_guide.md`: one sentence in the Next Rank paragraph for the
    "faster" reading.
  - `docs/architecture.md`: the run length field, the message's new fact,
    and `benchmark_rank_fields`'s new input.
  - the Shipping a proposal checklist in AGENTS.md: the product inventory,
    the roadmap entry moved to Shipped, the Terms block moved into the
    glossary if the glossary exists, references to this file, and deleting
    this file.
  - the interim-log comment on `SESSION_LOG_SCORE_THRESHOLD_PCT`, which
    should say the log judges time-scored scenarios by pace.
- **New copy:** any string this proposal didn't foresee is listed under "New
  copy" in the PR body.

## Testing

Each surface gets a time-scored case, an unchanged score case, and an unsure
fallback. The existing tests for the score cases stay as they are. They are
the "unchanged" half.

- **Run length** (`tests/test_data_service_extract.py`): the end minus the
  start minus the pauses; a run across midnight; unknown with no
  `Challenge Start`, with no `Pause Duration`, and on builds 2.0.3 to 2.0.5;
  unknown when the result isn't positive; and a malformed length field that
  costs the length, not the run.
- **Detection**, table-driven:
  - a time-scored set at a constant of 1,000 and another at 250, returning
    the median sum;
  - the false positive: fixed 60 s lengths with scores within a point, which
    is unsure;
  - four runs, which is unsure, and five, which is detected;
  - one run off the line, which is unsure;
  - lengths spanning under 5 s, which is unsure;
  - one odd-length run carrying an otherwise flat set, which fails the
    correlation;
  - runs with no known length, which count neither way.
- **The pace helpers:** each formula in the table, and "undefined" when
  either time is zero or less.
- **Next Rank** (`tests/test_playlist_scenarios_service.py`): a PB of
  896.17 against Lavender 899 at a constant of 1,000 reads "2.9% faster to
  Lavender" (unrounded 2.802), with the unrounded sort key. A constant of
  `None` reads "+0.4% to Lavender". The round-up and the floor apply to a
  pace gap. A pace gap that is undefined falls back to D1. The Rank column is the same with and
  without a constant. The three row paths carry the same Next Rank for a
  time-scored scenario.
- **The threshold line**: PB 896.17 at 95% with a constant of 1,000 draws
  at 890.71. With no constant, it draws at 851.36 as today.
- **The verdict** (`tests/test_home_run_events.py`): a pass and a fail by
  pace, with "% of PB pace" in the message. A run exactly at the pace goal
  passes. With no constant, the message reads "% of PB". A time-scored
  previous best of zero or less is still judged when pace is defined.
- **The personal best toast** (`tests/test_app_shell_run_events.py`): "Finished
  11.3% faster than your previous best of 884.41." for 884.41 → 896.17 at a
  constant of 1,000; with no constant, today's "Up 1.3% on your previous
  best of 884.41."
- **The watchdog:** the message carries the constant computed with the new
  run included. A scenario's first run carries `None`. The debug log judges a
  time-scored run by pace.
- **Gates:** AGENTS.md's five local checks, including the docs test and the
  em-dash guard.
- **Live check:** on the maintainer's stats folder, open Viscose Benchmark
  S2 - Medium and sort Next Rank ascending. The four time-scored rows read
  "faster" and sit 2nd, 5th, 6th, and 10th rather than in the top four,
  unless new runs have moved them. Open Ground Plaza Sparky V3 on Scenario
  Performance and check that the threshold line sits near 890.7. Then play
  or copy in a run and read the toast.
