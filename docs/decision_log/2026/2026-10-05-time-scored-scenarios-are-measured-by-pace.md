# 2026-10-05: Time-Scored Scenarios Are Measured By Pace

Status: Accepted

Some scenarios score the time left on a countdown when the task is done, and
on those the app now measures by pace: how fast a run finishes compared with
the personal best. A percentage of such a score understates a real
improvement many times over, so these scenarios looked closer to the next
rank and easier to pass than they were. A player sees "faster" in the Next
Rank column and "PB pace" in a run's verdict wherever pace applies. Where the
app can't tell whether a scenario is time-scored, everything reads as it did
before.

**Ruling.** Ratified (user) 2026-10-04 as a whole, after three review waves
on the proposal (PR #329, merged as `3efebe5`; the P1 and P2 rulings recorded
at `72eec3e`, the ratification at `18174de`). P1 and P2 were ruled together,
each as recommended, and P8 was ruled as a deferral. The author-owned rows
P3, P6, P7, P9, and P10 were reviewed and settled by the ratification. The
maintainer had already set three constraints: it is a bug fixed on its own
track (2026-09-28); the app detects such a scenario from the player's own
runs, accepts any constant, and falls back whenever it is unsure
(2026-09-28); and it adds no run length to the run record (2026-10-04).

**Supersedes in part**, for time-scored scenarios only, D1 of the
[2026-09-27 entry](2026-09-27-benchmark-tables-show-each-scenarios-rank-and-the-gap-to-the-next-one.md)
and the verdict formula of the
[2026-07-08 entry](2026-07-08-judge-score-threshold-notifications-against-the-previous-pb.md).
Each keeps its text and gains a note. Every other scenario keeps both
unchanged.

**What a time-scored scenario is.** It has no fixed length. It ends when the
player finishes a task, such as killing six bots, and its score is the time
left on a clock that counts down from a constant. So the score is the
constant minus the completion time, and one point is one second. A
percentage of a score assumes the score starts at zero, and this one starts
at the constant. For a small change, the percentage of the score understates
the percentage of pace by the score divided by the run's time, a factor of 4
to 16 across the maintainer's 99 runs of ten such scenarios (2026-10-04).

**The pace formulas.** With constant `C`, a score `s` took `C − s` seconds.
`T` is the next rank's threshold, `g` the goal percentage, and `prev` the PB
before the run. Each percentage that divided one score by another divides
the other way round on times, and nothing else in its formula changes:

| Surface | Score math | Pace math |
|---|---|---|
| Next Rank gap | `(T − PB) / PB × 100` | `((C − PB) / (C − T) − 1) × 100` |
| Threshold line | `PB × g / 100` | `C − (C − PB) × 100 / g` |
| Verdict passes when | `s × 100 ≥ prev × g` | `(C − prev) × 100 ≥ g × (C − s)` |
| Verdict shows | `s / prev × 100` | `(C − prev) / (C − s) × 100` |
| Personal best gain | `(s / prev − 1) × 100` | `((C − prev) / (C − s) − 1) × 100` |

**Pace applies only when it is defined.** A surface uses pace when the
scenario is recognized, every score in the comparison is eligible, and both
times are positive. Otherwise it runs the code it ran before, with that
code's own `N/A` and unjudged rules. One consequence is deliberate: a
time-scored PB of zero or less still gets a pace percentage, because only
the times have to be positive. The verdict converts each score and the
constant to decimals before subtracting and compares the cross-multiplied
form, so a run exactly at the goal passes, as the 2026-07-08 entry requires.
Display rounding is unchanged. The gap rounds up with a floor of 0.1, and a
verdict keeps both of its caps: a miss prints at most one tenth below the
goal, and a run below the previous best prints at most 99.9%. The second cap
needs no change, because a run's pace is below the previous best's exactly
when its score is.

**Why pace and not time: both are a percentage of throughput.** On a
fixed-length scenario the time is fixed and the score is the work done in
it, so score divided by PB score is a ratio of throughput. On a time-scored
scenario the work is fixed and the time varies, so throughput is one over
the time, and its ratio to the PB's is the PB's time divided by the run's.
That is pace. So the one global threshold setting keeps one meaning, a
higher setting still demands more, and a pace gap and a score gap can share
one sorted column. It also lets every formula carry over with only the ratio
replaced, so the rounding, capping, and boundary rules needed nothing new.

**P1: the Next Rank gap on a time-scored scenario is a pace gap.** It is how
much faster the PB run has to finish to reach the next rank. D1's three
reasons all survive: the gap is defined below the first rank, it states the
target to beat, and it still matches the score threshold, which P2 moves the
same way. The ladder walk, the Rank column, the round-up and its floor, the
unrounded sort key, Top rank's precedence, and the tooltip in points are
unchanged, because a higher score is always a faster finish. One rule
narrows: D1's `N/A` for a PB of zero or less now applies to a time-scored
row only where pace is undefined. Rejected: keeping D1, which understated
these gaps 9 to 12 times on the maintainer's Viscose rows and floated all
four to the top of an ascending sort; the gap in seconds, which is exact but
can't be compared across scenarios and already sits in the tooltip; percent
less time, which is not what "faster" means and would measure differently
from P2; and `N/A`, which drops the one answer the column exists for.

**P2: the score threshold on a time-scored scenario is a percentage of PB
pace.** At 95%, a run passes when it is at least 95% as fast as the PB,
which means finishing within the PB's time divided by 0.95. The chart line
sits at the score that finishes exactly then, from the current PB, and the
verdict judges against the previous PB, as before. A goal above 100% puts
the line above the PB. The setting stays one global percentage. Judged
after the fact on the maintainer's six time-scored scenarios with at least
five runs, the score form passed 86 of 86 runs and the pace form 59.
Rejected: keeping a percentage of the score; reading the percentage as
time, which taken literally demands a run 5% faster than the PB and
otherwise needs a translation of the setting that no other scenario uses;
turning the threshold off on these scenarios; and a separate or
per-scenario percentage, which is a Run History question.

**Detection: one performance file answers one of three ways (P9).**
KovaaK's writes a performance file beside each run's stats file. The check
reads the header's `schema_version` and `scenario_hash`, its challenge
profile's `time_limit` and `timescale`, and each event's `timestamp` and
score delta.

- *Time-scored:* the file has at least two score events, and after every
  one the running score is within 0.5 of
  `time_limit − timescale × timestamp`. The constant is the file's
  `time_limit`, and the scenario version is its `scenario_hash`.
- *Not time-scored:* any other file that can answer.
- *Can't answer:* the bytes do not parse, or `schema_version` is not 1. The
  proposal left four header cases open, and each also can't answer: no
  header, no scenario hash, a time limit that is missing, not positive, or
  not a finite number, and a timescale that is any of those three. No file
  in the maintainer's folder has any of them.

**Which file decides.** The scenario's newest run names the version. That
run and the older runs of the same hash are tried newest first, and the
first whose performance file can answer decides. A file that can't answer
is skipped, so a damaged file, or a schema change in the game, doesn't turn
a recognized scenario back. A file that answers "not time-scored" is not
skipped: every ordinary scenario's newest file answers that, and skipping
it would read that scenario's whole history. No file that can answer means
the app can't tell. So does a newest run with no hash, which names no
version. One file can decide because how a scenario scores belongs to its
definition, which the hash identifies. A scenario's first run on a current
build therefore flips it to pace, and it flips back only if a newer run's
file can answer and shows no countdown.

**The tolerance absorbs a start lag, not noise.** From the maintainer's
1,764 performance files on 2026-10-04: the 84 countdown files, across 10
scenarios, stay within 0.02 of the line at every event, and the nearest of
the other 1,680 is off by 42. Every tolerance from 0.02 to 40 recognizes
the same 84. The distance is set at the first score event and barely moves
after it. On the other paired files that first event's timestamp falls up
to 72 ms short of one second, with a 99th percentile of 31 ms. Every run in
the data was played at 407 to 988 FPS, so a slower machine may lag more,
and a missed file is silent. Half a point is seven times the largest lag
seen. `timescale` is the scenario's own game speed: the time limit counts
game time and the timestamps count real time, so a slowed time-scored
scenario should lose `timescale` points per real second. No such run is in
the data, and if the game does otherwise the check fails and the scenario
falls back.

**The file facts the app relies on.** KovaaK's publishes the format, a
protobuf schema, at <https://wiki.kovaaks.com/performance.proto>, and the
app reads it by hand, with no protobuf dependency. Game builds from 3.9.0
write the files, into the `performances` folder beside the stats folder. A
run's file is found by name: the stats file's name with ` Stats.csv`
replaced by ` Performance.perf`. Of the 1,757 stats files written since the
first performance file, 1,756 have one of the same name, and on all 1,756
the header's hash equals the stats file's `Hash:`. The game writes the
performance file within 10 ms of the stats file, and the watchdog already
waits a second before reading a new stats file. Every file in the folder is
schema version 1. There is no new setting, and the app only reads the
folder.

**Eligibility is by hash (P10).** A run record keeps the stats file's
`Hash:` and the stats file's own name, and no run length. A score is
eligible for a pace comparison only when its run's hash equals the deciding
file's. That covers the row's PB, the chart's PB, the verdict's and the
celebration's previous best, and the new run. A rank threshold comes from
the benchmark file and counts as eligible. A stats file with no `Hash:`
still loads, and its score is never eligible. So a PB from an older version
of the scenario keeps the score math until a run on the current version
beats it: the constant was read from one version, and nothing shows that
another scores the same way. Of the maintainer's 866 scenarios, 15 have
more than one hash, and none of the ten time-scored ones do.

**The constant travels with the run.** The watchdog works the constant out
before it queues a run's message, with the landed run judged by its own
file, and the message and the batch record carry it as a fact, like the
previous best. It is absent when the scenario isn't recognized, when the
new run or the previous best isn't eligible, and on a scenario's first run,
which nothing judges or celebrates. So the toast agrees with the chart,
which rebuilds after the run lands, and neither the drain nor the page
reads the stores for it.

**Cost and memory.** Startup lists the `performances` folder once and
parses nothing. A run that lands adds its file to that listing, so the
table and the chart see the file the watchdog read. A file is parsed only
when a surface asks about its scenario, and each answer is remembered by
file name, because a written file never changes. A file that can't be read
is not remembered, so the next look tries again. Reading one costs about
0.6 ms in plain Python for a median file of 4.7 KB. Nothing is written to
disk. A missing, unreadable, or malformed performance file costs only the
detection, never the run. The stores are read on the terms of the
[2026-07-09 entry](2026-07-09-accept-unsynchronized-in-memory-stores-single-writer.md).

**Five surfaces.** Next Rank reads "{gap}% faster to {rank name}" and sorts
by the unrounded pace gap, on all three row paths. The Score threshold line
draws at the pace line, and its annotation still shows a score. The
threshold verdict says "% of PB pace". The New personal best toast says
"Finished {pct}% faster than your previous best of {previous}." The session
debug log judges by pace at its fixed 95%, because left on score it would
pass every run the toast fails. Anything that orders or places scores is
unchanged: the chart's points and axis, the Average score line, the PB
line, the rank lines, the Rank column, top-N placement, and the
celebration's strictly-greater test. The Next Rank header tooltip and the
Score threshold percentage help text name both measures, in wording that
stays true in every fallback. No completion time is shown anywhere.

**Rejected: inferring it from the stats files.** A stats file gives a run's
length only as its name's time stamp less its start time and pause
duration, precise to about a second, and a detector can fit score plus
length to a constant across a scenario's runs. The proposal's first design
did. It needs five runs, and four of the ten scenarios have fewer. A fit
through noisy lengths can't establish one point per second. Its constant
came out 0.3 to 0.5 s low, which distorts a short run's percentages. And
the stats file can't see a slowed scenario: its time dilation field reads
1.0 on all 363 runs whose performance file records another timescale.
Keeping the inference as a fallback was rejected too, since on the
maintainer's data it recognizes nothing the file doesn't. Also rejected: a
hand-kept list of scenarios, which can't cover what public users play; the
header alone, since a time limit says how long a run may last and not how
it scores; requiring a time limit of exactly 1,000, which would hard-code
the constant; and parsing every file at startup, which grows with every
run.

**P8: the Aim Training Journey graph keeps its score ratios.** That graph
averages each scenario's best score so far as a share of its PB, the same
ratio corrected here. The page was ruled shelved on 2026-09-28, as recorded
in
[#327](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/327),
so leaving it alone is a deferral under that ruling, separable from this
fix. On a playlist that holds time-scored scenarios the graph keeps
overstating how close earlier runs were to the PB. A plan that revives the
page carries this fix with it.

**Checked in the game before the merge.** Two cases had no run in the
data, so the maintainer played one of each on 2026-10-05, on Air Pure
Easier No UFO and game build 3.9.10. A run paused for 15 s partway through
was recognized, with a largest distance of 0.011. Its file carries one
pause event, and its timestamps leave the paused time out: the run took
about 102 s by the clock, and its last event is stamped 87.2 s. So a file
with a pause event needs no special case. A run at a 60 FPS cap was
recognized with a largest distance of 0.027, where that scenario's six
earlier files sit at 0.006 to 0.008. That is one run, so it shows the
typical lag and not its tail, and half a point is about nineteen times
it. The debug log records each parsed file's largest distance from the
countdown, which is the number to read if a scenario is ever not
recognized.

**Out of scope.** Run History, including a run length field and a
per-scenario threshold. A per-bot breakdown. Anything else the performance
file holds. A scenario whose score isn't the time left on its clock, and
one with no performance file: both keep the score math.

**Superseded in part (2026-10-05).** A pace row's Next Rank cell now leads
with the sign a score row carries, at the maintainer's direction:
"+{gap}% faster to {rank name}", such as "+2.8% faster to Lavender". Without
it, one sorted column read "+1.4% to Cerulean" on one row and "1.4% faster to
Cerulean" on the next, and the missing sign said nothing that "faster"
doesn't. The sign went onto both rows instead of coming off both because a
score row needs it: it marks growth still needed, where a bare "85.0% to
Gold" can read as progress through the band, the measure D1 of the
[2026-09-27 entry](2026-09-27-benchmark-tables-show-each-scenarios-rank-and-the-gap-to-the-next-one.md)
rejected, under which higher is closer. The accepted cost is that the sign
and "faster" mark direction twice. "Faster" still names the measure, so the
header tooltip holds as written, and the gap's formula, rounding, sort, and
tooltip are unchanged. The string was author-owned copy, not a ruled row,
and P1 and everything else here stand. Shipped in PR #348.

**Superseded in part (2026-10-12).** The watchdog's session lines in the
debug log leave the list of surfaces above. They were removed when the Run
History page went public, in PR #373, because that page's run list is
the record they stood in for. The run list's check and the latest-run card
join the list. A past run's check is judged under its own version of the
scenario, not under the version the scenario's newest run names, so a later
run on another version changes no earlier check. The pace rule stands. See
[A Past Run's Check Is Judged Against The PB It Was Chasing, Under Its Own Version](2026-10-12-a-past-runs-check-is-judged-against-the-pb-it-was-chasing-under-its-own-version.md).

**Provenance.** Proposal by `claude-opus-5-5` (PR #329), reviewed by
`gpt-6-astra` and `claude-fable-5-1`. Shipped in PR #343.
