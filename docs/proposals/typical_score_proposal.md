# Typical Score Proposal

Status: Proposed
Date: 2026-10-15

## TL;DR

The app's stated direction is to judge skill by what a player's recent runs
usually score, but it has never defined that figure, so no page shows it and
the Run History chart draws no line for it. This proposal defines the typical
score as the median of a scenario's last 20 runs, whatever their age, drawn at
full strength where enough of those runs are recent and faded where they are
not. The chart draws it after every run as a gray line inside two bands, the
middle half and the middle 80% of the runs, and each of the three has a switch
of its own. Scenario Stats leads with the figure as its large number, dimmed
when it isn't recent.

## Decisions needed

Eight rows, TS1 to TS8. **TS1, TS3, TS4 and TS5 are ruled. TS2 is pivoted
to TS6, and TS6, TS7 and TS8 are proposed and open.** Each row began as the
maintainer's lean or agreement from the design discussion of 2026-10-14 to
2026-10-19, worked out over measurements and eight versions of a live
prototype on their own stats, and each quotes what they said. A lean is not a
ruling: reviewers are invited to challenge any row, and any author-owned
choice in [Design](#design). The first review wave endorsed TS2 to TS5 and
contested one point of TS1, whether runs of different versions of a scenario
count together. The maintainer ruled TS1 on 2026-10-15, as recommended: every
version counts, the assumption stated. On 2026-10-18 they ratified TS3, TS4
and TS5 as recommended, and left TS2 open.

**What changed on 2026-10-19.** Working through TS2 on prototypes v7 and v8,
the maintainer leaned toward an option neither review wave saw: no limit's
line, faded where its runs aren't recent. TS6 carries it. Two more leans
followed from it, and they change ruled rows: a switch each for the line and
both bands, all on (TS7, which would amend TS4), and Scenario Stats led by the
typical score (TS8, which would amend TS5). TS6 also amends TS1: the 30 days
leave the value and decide only how it is drawn. **Each ruled row stands as
ruled until the maintainer rules on the row that would amend it.** The three
are pivots of TS2, TS4 and TS5 and ask no new question, so the scope freeze
holds. The maintainer, on the new rows: "I have leans so far, but I still want
things to be open for debate until I get other reviewers' opinions."

**The third review wave** endorsed TS7 and TS8 and split on TS6. Two readers
proposed drawing a value at full strength only when every run behind it is
recent, and one endorsed D's test with the older runs shown. TS6 weighs the
two with their measured costs, and still recommends D's test, now with a
value's older runs shown on the card. After the wave the maintainer took the
sessions out of that test, keeping them only for a scenario's first value,
and chose the help's wording, all put to review. They named the goals the
review is to weigh: the typical score as accurate as possible, simple for a
player to understand, and appealing on the chart.

**The fourth review wave** judged the amended TS6 by those goals. Two
readers endorsed the amended test, and one kept its proposal to draw a value
at full strength only when every run behind it is recent. All three agreed
that the sessions belong only to a scenario's first value, and that the help's
sentence says enough under the amended test. TS7 and TS8 were endorsed again.
What is left is a trade-off for the maintainer: fewer faded values, with the
older runs shown, against a promise that every run behind a full-strength
value is recent.

Already ratified, and not reopened here: D1 to D3 of the
[2026-10-04 entry](../decision_log/2026/2026-10-04-skill-is-judged-by-the-typical-run-with-honest-uncertainty-in-verdicts-not-advice.md)
(skill is judged by the typical run, unknown is not weak, verdicts not
advice); S1 to S4 of the
[2026-10-11 sessions entry](../decision_log/2026/2026-10-11-a-session-ends-after-a-break-of-more-than-30-minutes.md),
whose S4 sends this definition to a proposal of its own; R1 to R7 of the Run
History page; A1 to A3 of All scenarios; and T1 to T4 of the top row
cards, shipped in #380, #383 and #384
([2026-10-14 entry](../decision_log/2026/2026-10-14-run-historys-top-row-has-one-card-per-kind-of-information.md)).

The evidence below is one player's history: the maintainer's 9,135 runs over
866 scenarios in 325 play sessions, last run 2026-10-09 22:03, and for TS6 the
same history to 2026-10-16, 9,212 runs in 328 sessions. It shows what the
rules do on that history and nothing about other players'.

### TS1. The definition

Status: Ruled (user), 2026-10-15: "TS1: accept recommendation, pool every
version with the assumption stated." That settles the row as recommended
below, the version question included. **TS6, proposed 2026-10-19, would amend
it:** the value would count the last 20 runs at any age, the 30 days would
decide only how it is drawn, and no value would be carried. The session rule
would decide only whether a value is known: a value would be drawn at full
strength once 10 of its runs are recent, from any number of sessions. The
minimums, the versions, sensitivities and warm-up runs, and the fixed
constants would stand. Until the maintainer rules on TS6, this row stands. Before that, the maintainer's lean,
built up over the discussion: "I agree
with all leans" (2026-10-14, including fixed numbers and every sensitivity);
"Version 1 counts every run, and the warm-up rule comes later. This keeps the
design of Typical Score simple, at the tradeoff that its score will likely
shift if/when we decide to ship the warm-up rule."; "at least two sessions,
and at least 10 runs, using up to a maximum of 20 runs"; "carry the last known
typical score forward after a break, marked as of in the stats and dotted on
the chart, until the new window meets the minimums" (faded later replaced
dotted, under TS2); "Yes: use a 30-day window, with as of after 30 days
without a run."; "Use the narrower rule: fresh with 10 runs from 2 sessions,
or a full window of 20 runs whatever its sessions."

The material consequence: every later feature that judges skill by the
typical run reads this figure. A number changed later moves every reader at
once, and the warm-up rule, when it ships, will move the figure.

**Recommendation: a scenario's typical score after a run is the median score
of its last 20 runs or fewer, counting only runs that ended in the 30 days up
to and including that run. It is fresh when those runs number at least 10 from
at least 2 sessions, or fill the window with 20 runs whatever their sessions.
After a fresh value exists, a window that fails the rule carries the last fresh
value forward, shown "as of" its newest run. Before any fresh value it is
unknown. Every run counts: every sensitivity, every version of the scenario,
and warm-up runs. The numbers are fixed constants, not settings.**

- **The median, because one run can't move it far.** A spike PB or a botched
  run moves a mean; the median is the score the middle run reached. The
  maintainer's own notes read P50 as "typical performance".
- **20 runs, because shorter and longer samples did worse.** PR #351's test,
  at commit `6177dd3`, on its definition then (14 days, warm-up runs left
  out), put the last 10, 30, and 50 runs at 3.5%, 3.6%, and 3.6% from the
  level of the session that followed, after removing the average offset, and
  the last 20 at 3.2%. It is also the maintainer's hand method.
- **30 days** is argued in TS2.
- **10 runs from 2 sessions, so one sitting is never called typical.** A
  session's median moves with the day's form, about 3% on this history, and
  scenarios in one session move together. Refleks's docs say the same: look
  across a few sessions, not one.
- **Or a full 20, so a long grind stays known.** Without the exception, a
  sitting that fills all 20 runs leaves one session in the window, and the
  value carries for the rest of the grind: 529 runs in 2025 and 2026 (6.2%),
  30 in 2026. The carried value protected nothing. In 26 of 29 grinds it
  already held 10 to 19 runs of the grind itself, frozen at its 19th run. A
  long sitting did not overstate the player either: its value sat 1.6% below
  the next session on average, and above it in 10 of 29. With the exception,
  accuracy is unchanged within noise: 3.82% against 3.93% from the next
  session's median, at 30 days.
- **The maintainer's "two sessions only until established" measured the
  same.** It also fixes the grind, and the two rules differ on 71 runs of
  8,529. This one is recommended because it reads off the window alone: the
  other's "established" flag reads the whole history, so one stray run months
  earlier satisfies it.
- **Carried forward, because a break should not erase a known level.**
  Carried values stayed within 3% to 5% of the next session for up to four
  months on a plateau, and ran 10% to 14% low after a fast-improvement phase
  or a five-to-eight-month break. That is why a carried value is always
  labelled "as of".
- **Unknown before any fresh value,** which D2 requires: unknown is never
  read as weak. A value once fresh is never unknown again, so after the first
  known value the line has no gaps.
- **Every sensitivity counts.** PR #351 measured runs at the session's own
  sensitivity alone at 2.8% from the session's level, against 2.6% for all
  of them.
- **Every version counts, treated as comparable,** as the PB line, the New
  PB stars and the rank lines treat a scenario's versions. A run whose stats
  file has no `Hash:` counts too, as it does for the PB. The version rule of
  the
  [2026-10-12 marks entry](../decision_log/2026/2026-10-12-a-past-runs-check-is-judged-against-the-pb-it-was-chasing-under-its-own-version.md)
  covers a time-scored run's pace only. The assumption has a cost if a rework
  changes the scoring, set out under Versions below. PR #351's row
  H4 kept the current version alone; this departs from it.
- **Warm-up runs count in version 1,** as the maintainer chose, so the
  figure will shift if a warm-up rule ships.
- **Fixed constants,** as the 30-minute session limit is (S2): a setting
  would ask each player to tune numbers the app can't recommend values for,
  two installs would stop agreeing on what typical means, and a setting is
  costly to remove.
- **A session is a play session** as the app already splits them across all
  scenarios: a break of more than 30 minutes ends it (S1).

Changed from the maintainer's September hand method: the window runs up to the
run itself, not "the 14 days before the most recent session"; it is 30 days,
not 14; 10 runs from two sessions replace 8 runs; and warm-up runs count.

**Versions: every version counts, ruled 2026-10-15.** KovaaK's names a
scenario's version in each stats file's `Hash:`, and a rework can change the
scoring. The definition treats every version as comparable, and accepts what
that costs if a rework does change the scoring:

- **A fresh value can blend two versions,** for up to 19 runs within 30
  days. A worked example: 10 runs scoring 40 on a 100-second clock, then 10
  scoring 140 on a 200-second clock, every one a 60-second finish, give a
  fresh value of 90, which neither version's runs scored.
- **A carried value can be another version's.** After a break, the first run
  on a new version carries the old version's value, labelled "as of" its old
  dates, until the new version's runs meet the minimum.

On the maintainer's history: 17 version changes in 9,135 runs, 15 of them
after breaks of 63 days or more, which the window had already cleared; 19
runs whose window holds two versions (0.21%), 7 of them fresh, all in one
scenario in October 2025 and none in 2026. None of the changes can be shown
to have changed the scale. The scores do step at some, by up to 40%, but
almost all came after breaks long enough for practice or rust to explain the
step. The one close to its last run, a 16-day gap, sits inside the 2025
climb.

- **Why pooling.** The hash is a poor proxy for a scoring change: it changes
  with any edit to the scenario, so scoping by it would have reset the value
  17 times on this history to guard against something that never happened.
  Every other surface on the chart treats the scenario as its name across
  versions: the PB line, the New PB stars and the rank lines.
- **How it squares with D2,** which asks that the runs be comparable: the
  definition treats versions as comparable on this history's evidence, as it
  treats sensitivities, and states the assumption, so every later reader
  knows what the figure assumes. Nothing is stored, so if a rework that
  changes the scale turns up, scoping can be added and the whole history is
  worked out again at once.
- **Rejected: scope by hash.** No value from runs of two versions and none
  carried into a new version. After any version change the value would be
  unknown until the new version's runs met the minimum, the carried value
  dropped at the boundary, and the line broken there while the PB line runs
  on.
- **Rejected: break only where the app knows the scale changed,** a
  time-scored scenario whose countdown differs between versions. It catches
  the worked example's case and no other, and couples a pure definition to
  the performance files.

This answers the two comments on PR #351 that S4 handed to this proposal. The
figure
[staying known from an arbitrarily old session](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/351#discussion_r4191712540)
is the "as of" state: it stays known, and says how old it is. Holding a run's
[comparison set fixed for its session](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/351#discussion_r4191712550)
is TS3: the chart draws the value after every run, and the session freeze
belongs to the comparisons that come later.

### TS2. Window and staleness on the chart

Status: **Pivoted to TS6** on 2026-10-19, on the maintainer's lean, not a
ruling. The row is kept below as both review waves read it. Before that it was
open, for heavy scrutiny. The maintainer, 2026-10-15: "Let's go
with the 30 day window for now, but I'd like for this to be heavily
scrutinized during proposal review. On paper it seems like it's the best
approach to keep a consistent definition and to make future proposals
smoother. But from a user perspective, seeing the continuous line with No
Limits looks much more appealing than the 30 day option with gaps everywhere;
i.e. with these many gaps, I wonder if it's even worth showing at all." Then,
asked whether "as of" stretches should be drawn faded or dotted, they chose
faded. That answer chose between the two styles of the 30-day line; it did
not choose 30 days over no limit.

The question: should a value built from runs more than 30 days before it count
as current, and how should the chart draw a value that no longer does? And is
the line worth drawing at all?

The material consequence: the answer fixes what "current" means for every
later feature that reads the typical score, and what the chart looks like on
every scenario.

**Recommendation: keep the 30-day window of TS1, and draw "as of" stretches
faded: the line and both bands kept, at about a third of their strength, each
stretch joined to the fresh run that ends it, so a known value reads as one
continuous line. Draw the line.**

What a player sees under each, on the maintainer's 2026 runs:

| | 30 days, faded (recommended) | No limit (the alternative) |
|---|---|---|
| Runs under a full-strength line | 43.1% | about 63% |
| Runs under a faded line | 8.2% | almost none |
| Runs with no line | 48.8% | 36.6% |
| What says a value is old | the faded stretch on the chart, and "as of" in Scenario Stats | the dates in the hover, and the gaps on the Score vs Time axis |

The 30-day column is measured with TS1's rules, over 3,470 runs. The no-limit
column was measured under the earlier session rule, with no full-20
exception, which left 1.4% of runs carried by a one-session window. Under
TS1's rule those runs are fresh, so its first two rows are derived (62.0%
plus 1.4%), not measured, and its third may fall by about half a point, as
the 30-day figure did.

**The case for 30 days, faded.**

1. **"Fresh" means recent.** With a window in the definition, the chart, the
   stats line and later readers share one meaning of fresh and of "as of".
   A no-limit value served by one helper with its dates and counts would
   still be one definition, but its "fresh" would say nothing about how
   recent its runs are, so no page could say whether a value is current
   without a rule of its own. The window licenses no later judgment either:
   each later feature still sets the evidence it needs, as S4 said.
2. **It doesn't call old runs current after a break.** No limit never says
   "as of". After a break of 21 days or more, its first value back is built
   mostly from pre-break runs, every time: in all 133 returns to an
   established scenario, a median of 18 of the 20 runs. At 30 days, 12 of 41
   first values back held any pre-break run, a median of 5. On the 39 returns
   every window covered, the first session back was missed by the same 4.8%
   either way. No limit's own figure, 7.7% against 5.3% at 30 days, is worse
   because of the returns only it calls known, with values months old.
3. **It costs little in regular play.** The 20-run cap binds before any time
   limit does. 30 days gives the same value as 14 days on 97% of 2026's
   targets where both are fresh, and no limit the same as 14 days on 76%, a
   fifth of a point less accurate.
4. **The faded style answers "gaps everywhere".** The gaps the maintainer saw
   were the dotted style, which dropped the bands. Faded keeps them, and a
   known value never becomes unknown, so after the first known run the line
   is continuous on every scenario. What is still missing is a scenario's
   first runs, before it has ever had 10 runs from two sessions within 30
   days. Most of that absence is history, not the window: 545 of 1,066
   session targets from 2025 on (201 of 468 in 2026) came with fewer than 10
   earlier runs of the scenario, which no window can fill.
5. **Its weakness is shared.** During the Voltaic S5 Intermediate climb of
   September to November 2025 the 30-day values ran about 10% low while
   labelled current. 14 days showed the same sessions as "as of", 11.6% off,
   against 30 days' 10.4%: the same lag, labelled differently. Every rolling
   window lags a fast climb, no limit included. That picture, on VT
   Controlsphere Intermediate S5, is what moved the window from 14 to 30
   days: at 14 the line held a flat "as of" 2,320 under runs of 3,000 and
   more, and at 30 it draws the climb.

**The case for no limit, at its strongest.**

1. **It looks finished.** One continuous, full-strength line on about 63% of
   2026's runs, against 43% at full strength and 8% faded. Scenarios played
   lightly, a few runs a month, get a line at all: about 12 points of 2026's
   runs have one under no limit and none under 30 days. The maintainer found
   it "much more appealing".
2. **It costs little where the player trains.** In regular play the two
   mostly give the same value, and the difference in accuracy, 0.1 to 0.2
   points, is within noise. They part after returns and on light play.
3. **The age can be shown without a window.** The hover's dates say when the
   runs behind a value were played, Score vs Time shows a break as a gap on
   its axis, and Scenario Stats could still say "as of" by a display rule. A
   player knows when they last played.
4. **Each later feature needs its own recency rule anyway.** S4 said so:
   "What the window and the minimum should be depends on what the figure is
   used for." The trend verdict is planned on session medians, not this
   figure. The rank-up chance will weigh recent form by a model not yet
   designed. Weakness ranking has its own bar for unknown. A window chosen
   for a chart is a guess for features nobody has designed, and leaving
   recency to each reader is honest about that.
5. **It is simpler.** One constant fewer, no "as of" state on the chart, no
   faded drawing, and no joins.

**Weighing them.** Point 4 is the alternative's strongest, and it is the
reason the window must be argued and not assumed. A no-limit value is not a
second definition by itself: each reader would add an eligibility rule to
one shared value. What decides it is that without a window "fresh" says
nothing about recency, so no page could say whether a value is current, and
the stats line's "as of", which the alternative's point 3 relies on, would
be a second rule after all, calling a value old while the chart drew it at
full strength. The coverage in the alternative's point 1 is real, but the
runs it adds are the values the measurement found weakest: months-old
medians labelled current. So the recommendation stands, and the faded style
is how it keeps the picture whole. The window is a descriptive rule for
"recent", not proof that 30 days predicts best.

**Is the line worth showing at all?** The honest case against: the previous
session's median predicts the next session as well as the typical score does
(3.96% overall; 0.3 points better where both exist in 2025 and 2026, and level
in 2026 alone), and it covers more scenarios. The typical score does not earn
its place by prediction. It earns it by steadiness: a session's median moves about 2.6%
from one visit to the next and the move reverses at the visit after, while
the typical score moves only when its 20 runs move, which is what a judgment
can lean on. The band shows what a PB never does: how consistent the runs
are, and a raised floor. A figure in Scenario Stats with no picture of its
history can't be checked by eye before later judgments depend on it, and the
roadmap plans the trend verdict "with a chart of the typical run over time".
A third option, the stats figure now and the line with the trend verdict,
would be cheaper, and is rejected for that reason: the definition would get no
visual check before features rank by it.

**A user-chosen window** was asked about and set aside: the maintainer did not
press it. One definition is the point of this proposal, the failure modes of
other windows are measured (7 days loses accurate values, 60 days and no limit
call old values current after a return), and a shipped setting is costly to
remove.

If the maintainer chooses no limit: TS1 drops its 30 days, the chart draws
every known value at full strength, Scenario Stats needs its own rule for
"as of", and each later feature writes a recency rule. If they choose no line:
TS3 and TS4 move to the trend verdict's proposal, and Scenario Stats ships
alone.

### TS3. The line is drawn after every run

Status: Ruled (user), 2026-10-18: "For simplicity, I'll ratify the other
decisions TS3, TS4, and TS5." That settles the row as recommended below.
Before that, the maintainer: "Agreed: draw the typical score per run on the
chart (held flat between runs in Score vs Time). The session freeze stays a
rule for comparisons, which come later."

The material consequence: the line moves after every run, during a session as
well, and so does the Scenario Stats figure.

**Recommendation: the chart draws the value after each run, at that run. On a
time axis each value holds flat until the next run, so days off are flat. A
value held fixed through a session is a rule for comparisons ("better than 15
of your last 20", a percentage against the typical score), which come later
and are out of scope.**

- **Per run is the same definition, evaluated more often.** Prototype v1
  drew the value frozen for each session, which made a staircase of the same
  statistic sampled once per session.
- **Held flat on a time axis,** because a session's runs are minutes apart:
  joined with straight lines they draw a vertical scribble, and the line
  slopes across days off.
- **The freeze belongs to comparisons.** A run compared against a value its
  own session has already moved is partly compared against itself, so a
  comparison needs the value as it stood coming into the session. A line
  that shows the level compares nothing, so it can move after every run.
- **On Score vs Time the line ends at the newest plotted run.** The
  prototype held the newest value until the moment the figure was built.
  This proposal does not, which is the author's reading, and the
  [Score vs Time](#score-vs-time) design says why.

Rejected: steps once per session (prototype v1); session values joined
(prototype v2).

### TS4. The bands

Status: Ruled (user), 2026-10-18, with TS3 and TS5. That settles the row as
recommended below; how an "as of" stretch draws its bands follows TS2, now
pivoted to TS6. **TS7, proposed 2026-10-19, would amend it:** the middle 50%
would get a switch of its own, and the Middle 80% switch would start on. P10
and P90 would stand. Until the maintainer rules on TS7, this row stands. Before that, the maintainer: "Yes: include the P10 to P90 band
as a Chart options switch, off by default, lighter shade."; "I think P10 and
P90 are the better metrics than min/max."

The material consequence: the chart gains a shaded band on every known
stretch, and Chart options gains a switch.

**Recommendation: the middle 50%, the first to third quartile of the same
runs, is always drawn. The middle 80%, the 10th to 90th percentile, is a
Chart options switch, off to start, in a lighter shade. P10 and P90 replace
the rolling minimum and maximum of the maintainer's older notes as floor and
ceiling.**

- **The middle 50% is the spread at a glance:** half the window's runs
  landed inside it. The maintainer's notes read P25 as an off day, P75 as
  locked in, and the gap between them as consistency.
- **P90, not the maximum.** The maximum rises with the number of runs: for
  normally spread scores, the best of 10 sits about 1.54 standard deviations
  above the median, the best of 20 about 1.87. One lucky run then sets it for
  20 runs. The minimum records the worst accident. P10 and P90 move only when
  several runs do.
- **The middle 80% is behind a switch,** so the chart a player meets first
  holds one band, and the floor and ceiling are there for the player who
  wants them, such as for reading a rank line against the ceiling.
- **Percentiles interpolate between runs,** as a spreadsheet's inclusive
  percentile does, so a 10-run window still has a P10.
- **An "as of" stretch keeps both bands, faded,** per TS2.

Rejected: the rolling maximum and minimum; a band between the median and the
maximum (the 2026-08-01 plan); a carried stretch drawn dotted with no band
(prototypes v3 to v5).

### TS5. The figure on the page

Status: Ruled (user), 2026-10-18, with TS3 and TS4. That settles the row as
recommended below, except what TS2, now pivoted to TS6, decides for it: the
30 days after which a value reads "as of", and what a value that isn't fresh
shows. **TS8, proposed 2026-10-19, would amend it:** the card would lead with
the typical score instead of giving it a line. Until the maintainer rules on
TS8, this row stands.
Before that, the maintainer: "Ship it first in today's Scenario Stats; the
cards proposal can move it later."; "keep as no limit. '2,140 · as of Mar 3,
2020' is still useful information, even if it is outdated."

The material consequence: Scenario Stats gains a line. On the card as it
ships today, the top row keeps its height.

**Recommendation: a "Typical score" line in Scenario Stats, showing the value
after the scenario's newest run, with "as of {date}" when that value is
carried or its newest run is more than 30 days old, and no limit on how old an
"as of" date may be.**

- **The value after the newest run is the one the chart ends on,** worked out
  by the same function, so the two never disagree.
- **No age limit,** as the maintainer chose: an old value with its date is
  information, and D2's honesty is served by the date, not by hiding it.
- **The unknown state names its count,** so a player grinding a new scenario
  sees how far it is from known (see [Copy](#copy)).

**Written against the Scenario Stats card as it ships today.** The top row
cards shipped after the maintainer's lean, in #380, #383 and #384, and two
PRs have changed the row since. #391 moved Last played to the latest-run card
and made the card's first line plain text
([2026-10-18](../decision_log/2026/2026-10-18-last-played-leaves-scenario-stats-and-its-first-line-is-plain-text.md)),
and #396 put the scenario note card beside it
([2026-10-18](../decision_log/2026/2026-10-18-run-historys-top-row-shows-the-selected-scenarios-note.md)).
The card now holds Category, while the Playlist filter holds a benchmark that
groups the selected scenario, then Number of runs, at one weight, in a 270 px
frame
([T2](../decision_log/2026/2026-10-14-scenario-stats-names-the-selected-benchmarks-category.md),
[T4](../decision_log/2026/2026-10-14-a-cards-lines-follow-their-role-in-the-players-next-action.md)).
With no scenario selected it reads "No scenario selected" in place of its
lines. Position moved to the PB card. T4 lists a card's facts in importance
order when it has no lead fact, so **the line goes second, after Category**,
or first when no benchmark is selected. The typical score is the fact D1 makes
the measure of skill; Number of runs is lookup context. Moving it to the PB
card, beside the PB, is a later change that neither proposal makes.

**The cost, measured on today's row** (headless Edge at 2560 and 1920 px, the
maintainer's stats, no username, with a benchmark selected and without, on
2026-10-19 at `1dc9413`): the row is 143 px without a benchmark and 164 px
with one, set by the PB card. Prototype v8, which leads the card with the
typical score as a large number (TS8), leaves both heights unchanged, so a
line of ordinary text fits too. The "as of" and unknown values may wrap to a
second line in the 270 px card, and the card's height absorbs it.

**Ordered against the top row cards' PRs 2 and 3: neither waited for the
other.** Asked whether the line ships before or after them, the maintainer,
2026-10-15: "I'll go with your recommendation." Both have since shipped, so
the line lands in the finished card. The definition and the chart don't
touch the top row.

### TS6. No limit's line, faded where its runs aren't recent

Status: Proposed, 2026-10-19, on the maintainer's lean, not a ruling. It would
replace TS2's answer and amend TS1, as TS1's status says. The maintainer,
2026-10-18, after TS2's options were laid out: "I think it is the opposite.
"No Limit" looks much better on the graph, and "Faded" is the alternative."
and "I would have expected that the "Faded" option keeps the same shape as the
"No Limits" option on the graph, just that the "unknown" area is faded to show
uncertainty". On 2026-10-19, with this option built and measured: "I am also
leaning toward option D." On its cost after a return, for weakness ranking:
"In the worst case situation, a scenario will appear weaker than it actually
is. But this serves as a small encouragement to the user to play that
scenario, which then updates its typical score."

After the third review wave, on 2026-10-19, the maintainer took the sessions
out of the recency test, kept them for a scenario's first value, and chose
the help's wording, all put to review and none ruled: "Let's go with that
option and put it to review." They set the goals the row is to be judged by:
"I'm trying to find the right balance with the Typical Score calculation
formula and copy that: 1. Keeps the Typical Score as accurate as possible 2.
While still being simple for a user to understand 3. While still being
visually appealing on the chart".

The material consequence: the value stops depending on the 30 days, and
"recent" becomes a test every surface reads beside it. Right after a return,
a value drawn at full strength can still hold up to 10 runs from before the
break, and every later reader sees that value. It reads low if the player has
improved since the break and high if they have declined, so a scenario can
look stronger than it is right after a return, not only weaker. The 2
sessions now guard only a scenario's first value.

**Recommendation: the typical score after a run is the median of the
scenario's last 20 runs, or of all its runs when it has fewer, whatever their
age. It is known once those runs number at least 10 from at least 2 sessions,
or 20. It is recent, and drawn at full strength, when at least 10 of them are
from the 30 days up to that moment, from any number of sessions. Otherwise it
is drawn faded, on a scenario that has never been recent too. Scenario Stats
judges recency as of now, and the chart as of each point's time. Whenever
some of a value's runs are older than 30 days, Scenario Stats says how many
are recent, faded or not. Every run counts, as TS1 says.**

- **It is the line the maintainer expected:** no limit's shape, with what
  isn't recent faded. Prototype v8 draws it.
- **One way to work out the value, one test for how it is drawn.** TS2's
  recommendation (A, v6) and v7's blend (C) both take the median of the recent
  runs alone while the test passes and of other runs when it doesn't, so their
  line steps where a faded stretch turns recent. After VT Pasu Intermediate
  S5's April 2026 return, C zigzags between its two values. At the 49 runs of
  2025 and 2026 where a faded stretch turned recent, A stepped by a median
  5.6% of the value (40% at worst) and C by 3.9% (31%), while D moved 0.7%
  (4%), an ordinary run's move.
- **"Recent" keeps one meaning.** TS2's deciding argument stands: the chart,
  Scenario Stats and later readers share one test for current. D moves the 30
  days from the value into that test, where no limit drops them.
- **Its cost is a lag right after a return, at full strength.** The test
  passes at 10 recent runs, so for at most the next 10 runs a full-strength
  value still holds older ones: up to 10 of its 20 right after a break, where
  no limit's first values back held a median of 18 of 20 (TS2, point 2).
  Measured at the start of each session in 2025 and 2026, with recency judged
  at that start, against the median of the session that followed:
  - Over every full-strength value with a value of A's beside it, D is 0.3
    points less accurate than A, 3.84% against 3.56% (95% interval +0.04 to
    +0.47, 322 targets).
  - On the 227 whose runs were all recent at the start, D's value is A's. On
    the other 95, of mixed age, D is about 1 point worse: 4.59% against
    3.61% (+0.25 to +1.76), with A closer on 56% and D on 18%. 71 of those 95
    windows span a break of 21 days or more, and 22 of the other 24 are from
    2025, when the player was climbing fast. In 2026, 51 of 53 span a break.
  - Run by run against the next 10 runs, the gap grows with the old runs: 0.3
    points with 1 to 4 of them, 1.25 with 5 to 9, 2.6 with all 10. D misses
    low: this player came back better than before the break.
  - In 2026 alone the median gap between the two values, where they differ,
    is 0.8%.
- **The lag runs either way.** This player came back better than before each
  break, so D's mixed values ran low: 20% of them were above the next
  session's median, and 4% by 5% or more, against 30% and 8% of the values
  whose runs were all recent. A player who comes back rusty sees the other direction:
  10 old scores of 200 and 10 recent ones of 100 make a full-strength 150.
  One player's history can't bound that. The maintainer's view of the worst
  case, quoted above, covers the first direction only.
- **Where the lag matters is in judgments made right after a return.** Of the
  features that will read the figure, weakness ranking and the rank-up chance
  are the ones that judge right then; run comparisons such as "better than 15
  of your last 20" read naturally under D, whose 20 runs are literally the
  last 20. A later feature can choose not to judge on a faded value, or ask
  for more than the drawing's test, such as every run recent: the definition
  hands it how many of a value's runs are recent.
- **A faded value is no worse than a held one.** On 2026's 54 session starts
  where A held a carried value, D's value, which C draws too, missed the next
  session by 3.18% against A's 3.87% (interval −0.91 to +0.50 for the
  difference). Holding a value flat has no accuracy case.
- **Coverage.** Of 2026's 3,547 runs, A draws 44.2% at full strength, 8.0%
  faded and 47.7% with no line; D 46.0%, 18.2% and 35.7%; no limit 64.3% at
  full strength and 35.7% with no line. Where D draws a line and A doesn't,
  it is light play.
- **Light play keeps its faded value.** A scenario that has never had 10
  recent runs shows its value faded once it has 10 runs from 2 sessions, or
  20, at any age. Where A had no value, D's values ran about 8.5% below the
  next session in 2026, a median error of 9.1% over 46 session starts, 3 of
  which D draws at full strength: the price of drawing them. Drawing nothing
  until a first recent value would make the value
  depend on the scenario's whole history, the kind of flag TS1 rejected,
  where one stray run months earlier satisfies it. D2 is met by the fade: the
  value shows as not recent, never as weak.
- **The judging moment.** Scenario Stats judges recency as of now, so it fades
  the moment the test stops passing. Score vs Run judges each point at its
  run. Score vs Time holds a value until the next run (TS3) and fades the hold
  when fewer than 10 of its runs are recent: with no run in between they only
  age out, so the moment is exact, when its 10th-newest run turns 30 days
  old. The line ends at the
  newest run (TS3), so the card can be faded while the chart's last point is
  solid: the card can first fade within 30 days of the scenario's last run,
  and the two then disagree until the next run. The explainer says so (Copy).
- **The alternative is every run recent, the stricter test review proposed.**
  A value is drawn at full strength only when every run behind it ended in
  the 30 days up to the moment; its values, its line and where the line is
  drawn are D's. It never draws runs from before a break at full strength, so
  it can't overstate after a decline, and its rule is one sentence. Its cost
  is fading: in 2026 full strength falls from 46.0% of runs to 30.9% and
  faded rises from 18.2% to 33.4%, so faded outnumbers full. After a long
  break the line turns solid at the 20th run back, not the 10th, and a
  scenario played 10 to 19 times a month whose last 20 runs reach past 30
  days stays faded. As of the newest run in the data, 31 scenarios played in
  the last 30 days have a value: D draws 27 at full strength, this test 16.
  Of the 11 it fades, 6 are returns still holding runs 159 or more days old,
  and 5 were played 14 to 19 times in the month, their oldest runs 30 to 49
  days old.
- **A 90-day ceiling on the oldest run, on top of D's test,** fades those 6
  returns and keeps the 5 at full strength. Over 2026 it costs nearly as much
  as every run recent, 32.9% of runs at full strength, because most of the
  difference there is returns, and it puts a second age in the rule.
- **Why D's test, and not every run recent.** The values that only every run
  recent fades predict nearly as well as the values both draw at full
  strength, and far better than the values D fades. At session starts in 2025
  and 2026 those 98 missed the next session by 4.58%, the 227 whose runs were
  all recent by 3.56%, and the 199 that D fades by 7.69%; in 2026 alone,
  3.57%, 3.18% and 5.14%. So D's fade marks the values that are clearly
  worse, where every run recent also fades a third of 2026's full-strength
  line. Its test is one number a player can check against the card's count,
  10 runs from the last 30 days. Its mixture is shown on the card, and a
  feature that judges can ask for every run recent. If the maintainer would
  rather bound the overstatement than show it, every run recent is coherent:
  the choice is whether "recent" means enough recent runs or only recent
  runs.
- **The 2 sessions guard only a scenario's first value.** A first session is
  one day's form, which moves a scenario's median by about 3% for this
  player, and on a new scenario the scores are still climbing: 434 of the
  691 PBs of 2026 came on scenarios with fewer than 10 earlier runs (both
  measured 2026-10-08). Once a value exists its 20 runs span other days, and
  asking 2 recent sessions as well added nothing measurable. D's first test
  did ask it: dropping it draws 2026's full strength at 46.0% of runs instead
  of 44.2%, and moves 6 session starts of 2025 and 2026 to full strength, too
  few to compare (4.05% against 3.83%). Two other cuts were measured and set
  aside. Dropping the sessions everywhere gives a new scenario's first
  session a full-strength value, 0.9% of 2026's runs. Dropping only "or 20 in
  one session" from both rules erases values a scenario already had, after
  long sessions of it: 547 runs of 2025 and 2026 on 26 scenarios. Dropping it
  from the full-strength test alone faded the values that predicted best,
  2.35% against 3.95% over 30 session starts.
- **Two simpler tests were set aside.** "At least 20 runs across 2 sessions",
  the maintainer's question, removes the lag but would cut 2026's
  full-strength runs from 46% to 28% and leave 57% with no line instead of
  36%: a scenario with 10 to 19 runs loses its value. "At least 15 of the 20
  recent" would cap the lag at 5 old runs, about 0.3 points, but leaves a
  scenario played 10 to 14 times a month faded for good; it was not measured.

Rejected: A, TS2's recommendation, a carried value held flat (v6); C, A's
value with faded stretches drawn from the last 20 runs at any age (v7); no
limit at full strength; every run recent and the 90-day ceiling, above; D's
first test, which asked 2 recent sessions or 20; dropping the sessions, or
the 20 in one session, everywhere; the two simpler tests above; and no line
before a scenario's first recent value.

The measurements are in the maintainer's scratch folder, the D evaluation and
its script, checked against the rules evaluation: on the runs to 2026-10-09
the two agree exactly. Its figures at a session start judge D's recency at
that start, as TS6 does; its first version judged it by A's rule there, which
kept 29 values at full strength that TS6 fades. Its figures for D use the
test above, with D's first test measured beside it, and the cuts to the
sessions come from a companion script on the same runs.

### TS7. The line and both bands, each with a switch

Status: Proposed, 2026-10-19, on the maintainer's lean, not a ruling. It would
amend TS4, as TS4's status says. The maintainer: "If it's a switch then the
user has the option to not always draw it. But if it's purely a legend, then
it will always be drawn and the user has to manually disable it every time
they change scenarios."; then "My current lean is to enable all 3 metrics by
default (i.e. encouraging users to see and use everything), but allow users to
turn each metric off individually. While it may be uncommon to do so, it
doesn't seem like it's very difficult to implement, and it gives more
customization to the user."

The material consequence: Chart options grows from seven controls to ten, and
a player meets both bands at once, not one.

**Recommendation: three switches in Chart options' Overlays group, after PB
score: Typical score for the line, Middle 50%, and Middle 80%, all on to start
and remembered as every Chart options control is. Each hides its faded
stretches with it. Scenario Stats doesn't follow them.**

- **Every other overlay has one.** Rank thresholds, Show all ranks, PB score
  and Score threshold overlay are switches. As TS4 is ruled, the line and the
  middle 50% would be the chart's only overlays a player can't turn off,
  except by a legend click the chart forgets when it next redraws, at a new
  run or another scenario.
- **On to start, so a player meets all three,** "encouraging users to see and
  use everything". The Middle 80% switch starting on reverses the
  maintainer's 2026-10-14 lean, off to start, which TS4 ruled.
- **The defaults are chosen once.** A switch remembers each player's choice,
  and changing a remembered switch's default later discards those choices
  ([2026-09-19](../decision_log/2026/2026-09-19-a-query-parameter-selects-a-control-it-does-not-suspend-its-memory.md)).
- **The cost is a busier first chart.** Both bands, the rank lines, the PB
  line and the threshold line can show at once. With Chart options open, the
  legend's five entries wrap onto a second line over the chart's title; PR 2
  lays the legend out so they don't ([The legend](#the-legend)).

Rejected: TS4 as ruled, the middle 50% always drawn and the middle 80% off to
start; one switch for the line and the middle 50% together, which leaves no
way to keep the line without the band; legend clicks alone; and one band
chooser in place of two switches, a control unlike every other overlay's.

### TS8. Scenario Stats leads with the typical score

Status: Proposed, 2026-10-19, on the maintainer's lean, not a ruling. It would
amend TS5, as TS5's status says. The maintainer: "I think the typical score
value should be emphasized as it is the Scenario stats card's defining
metric, compared to the PB card's PB score, and Latest Run card's latest run
score."; on the card's count: "I'm concerned that the "Number of runs" metric
may get confused by the runs for the Typical score; i.e. the user might think
all 169 runs are used for the Typical Score calculation."

The material consequence: the card's first line, which #391 shipped as
"Scenario stats", names its lead figure, and "Number of runs" is renamed.
The row keeps its height.

**Recommendation: the card leads with the typical score as the PB card leads
with the PB. Its first line reads "Typical score", with a help icon, then how
recent the value is when it isn't. The value follows in the large number the
PB and latest-run cards use, dimmed when it isn't recent. Category and "Total
runs" follow it.**

- **It is the card's defining figure,** as the PB is the PB card's and the
  latest run's score the latest-run card's, so it takes the same place and
  size. The card had no lead fact, which is why TS5 placed the line by T4's
  importance order.
- **"Total runs" keeps the count apart from the runs behind the typical
  score,** which are at most 20.
- **The first line says how many of the value's runs are recent** whenever
  some are older than 30 days, dimmed or not (Copy).
- **No height cost.** Measured at `1dc9413` (TS5) with v8's first line
  `· as of Aug 6`, the row stays 143 px without a benchmark and 164 px with
  one, the scenario note card beside it. The longest first line in the Copy
  block, `Typical score ⓘ · 19 of 20 recent runs`, measures about 198 px
  with its icon at the heading's 12 px, inside the 246 px the 270 px card
  leaves its text, so it doesn't wrap; PR 3 measures the row with it.
- **Beyond TS5 it changes** the first line that the
  [2026-10-18 entry](../decision_log/2026/2026-10-18-last-played-leaves-scenario-stats-and-its-first-line-is-plain-text.md)
  shipped, still plain text, and the glossary's Scenario Stats entry. The card
  keeps its name, Scenario Stats, in the docs and the code.

Rejected: TS5 as ruled, a line second after Category; and a first line kept
as "Scenario stats" over a smaller "Typical score" label, which costs a line
and breaks the cards' pattern of a first line naming the lead figure.

## Problem

### What the app shows today

- **The chart draws runs and nothing that sums them up.** Run History plots
  every run of a scenario in a range, with stars on new PBs, a ring on the
  latest run, and the PB score, Score threshold and rank lines
  ([run_history.md](../specs/run_history.md#the-chart)). The
  [2026-10-12 chart entry](../decision_log/2026/2026-10-12-the-run-history-chart-plots-every-run-and-draws-no-summary-line.md)
  dropped the old Average score line and drew no median, because "A new
  summary line would be a second definition of the typical run." This
  proposal is that definition.
- **Scenario Stats shows Category and Number of runs,** the PB card the
  personal best and the leaderboard position, and the latest-run card when
  the scenario was last played
  ([run_history.md](../specs/run_history.md#scenario-stats)). Nothing on any
  page shows how a scenario usually plays.
- **The run list's Median and best is not it.** That checkbox, off to start,
  shows the median and best of the runs under one row, with no window, no
  minimum, and no comparison
  ([2026-10-14](../decision_log/2026/2026-10-14-the-run-lists-columns-menu-offers-median-and-best-off-to-start.md)).
  Its [glossary entry](../glossary.md#median-and-best) says: "Not the typical
  run [...] A later proposal defines that."
- **The roadmap's principles judge skill by the typical run** (D1), and three
  Future entries wait on a definition: the score trend verdict, shown "with a
  chart of the typical run over time"; weakness by the typical run; and the
  rank-up chance, which weighs recent form
  ([roadmap](../roadmap.md#future-briefly)).

### Why now

- **S4 asks for it "before the first feature that judges by it".** Nothing
  can be ranked by the typical run until it is defined, and the definition
  should be seen on real play first. The chart is where a player, and the
  maintainer, can check it by eye.
- **The maintainer already plans training by it, by hand.** Their September
  2026 session plans used a hand-computed typical score (median of the last
  20 runs from 14 days, warm-ups out, unknown below 8), worked out in
  scripts. Checked on 2026-10-14, ordering a session's scenarios by it still
  tracked the next visit better than ordering by PB: a rank correlation of
  0.59 against 0.38 over 11 sessions, with an interval for the difference of
  −0.02 to +0.43. That evidence is thin, and it belongs to weakness ranking,
  later, not to this proposal.

### The evidence

All from the maintainer's history (see
[Decisions needed](#decisions-needed) for its size), measured 2026-10-14 and
2026-10-15. A value's error is its distance from the median of the
scenario's runs in the next session, as a share of that median.

- **Inside regular play the window barely matters.** Where two windows from
  7 to 60 days both give a fresh value, they give the same one about 90% of
  the time; the 20-run cap decides first. No limit agrees with them less
  often, 70% to 76%. Fresh values miss the next session by about 3%,
  close to how much one session's median varies on its own.
- **What longer windows add is old values labelled current.** See TS2, points
  2 and 5.
- **Carried values** hold within 3% to 5% for up to four months on a plateau,
  and run 10% to 14% low after a fast-improvement phase or a break of five to
  eight months. Every age bucket's bias is negative: an old value understates
  the player.
- **The session rule** fixes the long single-session grind at no accuracy
  cost (TS1).
- **The previous session's median predicts the next session as well** as the
  typical score (TS2). The typical score's case is steadiness for judgments.
- **Coverage is limited by history, not the window** (TS2, point 4).
- **Taking the 30 days out of the value and into the drawing** costs 0.3
  points of accuracy at full strength, all of it on values that still hold
  runs from before a break or a fast climb, and removes the step where a
  faded stretch turns recent (TS6).

The measurements, their method and their caveats are in the maintainer's
scratch folder: the window evaluation, its 30-day rerun, the session-rule
comparison, and the D evaluation, with their scripts. The caveats that matter most: one player; a
steep improvement phase in 2025 and a plateau in 2026, where the windows part
in the first and not the second; targets from sessions of three to five runs
are noisy; and many cells about returns and grinds come from a handful of
sessions.

### Verified facts

Checked at `1dc9413` on 2026-10-19. They were first checked at `1799df0`,
then at `dcc4cba`. Between them the top row cards (#380, #383, #384) took
Position out of Scenario Stats, #391 took Last played out of it, and #396
added the scenario note card to the top row. Nothing else listed here
changed. The branch has since merged `main` at `97c9cd4`, whose #397 lets a
long note scroll inside its card, which keeps its box: nothing listed here,
and not the row's height.

- **The chart's builders.** `build_run_history_figure` in
  `source/components/run_history_chart.py` reads the scenario's runs in play
  order, judges new PBs over the whole history, then applies the range.
  `generate_score_vs_run_plot` and `generate_score_vs_time_plot` in
  `source/plot/plot_service.py` build the run trace first, then the New PB
  trace, then the ring (`RUN_DATA_POINT_TRACE_NAME`, `NEW_PB_TRACE_NAME`,
  `LATEST_RUN_TRACE_NAME`).
- **The run points' color depends on the run trace coming first.**
  `generated_point_color` reads the template's first colorway entry, the one
  plotly gives the first trace that sets no color. Three test files read the
  run trace as `figure.data[0]`: `test_plot_service.py`,
  `test_chart_options.py`, `test_chart_point_appearance.py`.
- **Theme and appearance are a cheap presentation step.**
  `apply_graph_appearance` in `source/components/chart_options.py` applies the
  template, then the point size and color by trace name, and
  `show_latest_run_ring` recolors the ring per theme.
- **The PB score switch is an input of the chart rebuild,** in
  `generate_graph` in `source/pages/run_history.py`, and remembered under its
  id.
- **The zoom fit reads every visible trace.** `assets/homeGraphZoomFit.js`
  loops over `gd._fullData` and fits the score axis to each visible trace's
  points inside the x window.
- **Sessions.** `split_into_play_sessions` in
  `source/kovaaks/play_sessions.py` splits a list of runs at breaks of more
  than `PLAY_SESSION_BREAK_LIMIT` (30 minutes). `get_all_runs` and
  `get_runs_in_play_order` in `source/kovaaks/data_service.py` each return a
  copy of the run store.
- **Scenario Stats.** `scenario_stats_panel` and `register_scenario_stats` in
  `source/components/scenario_stats.py`. With no scenario selected the card
  shows `NO_SCENARIO_TEXT`, "No scenario selected", in place of its lines. It
  has no interval of its own since #391; the PB card's ids carry the page's
  30-second `relative_time_interval`.
- **Formatting.** `format_score` gives thousands separators and at most two
  decimals; `format_short_date` gives `Oct 12`, or `Mar 3, 2020` in another
  year.
- **Scores' precision.** Of the 9,135 runs, 7,137 scored a whole number, and
  1,611 carry five or six decimals.

Measured: the cost, the size and the draw order on 2026-10-15 at `1799df0`,
whose chart code `dcc4cba` leaves unchanged, and the row on 2026-10-18 at
`dcc4cba`:

- **Cost.** The largest scenario is VT DotTS Intermediate S5, 463 runs.
  Working out the value after each of its runs takes 3.9 ms, of which 2.9 ms
  is splitting all 9,135 runs into sessions. Today's chart build for it takes
  4.4 ms at the last 100 runs and 6.8 ms at all runs.
- **Figure size.** The cached figure at the default range grows from 14,553
  characters to about 33,000 with stand-in traces of the same shape, and at
  all runs from 39,443 to about 123,000. The ring's patch carries the cached
  figure up to the server once per run on another scenario.
- **Draw order.** On the served chart (plotly.js 4.1.1, the version Dash
  serves here), a filled band appended after the run trace with `zorder` set
  to −1 drew under the run points, and the run points kept their color,
  `#228be6`. With `zorder` 0 the band drew over them.
- **Row height and width,** under TS5.

## Design

The design below is TS6, TS7 and TS8, the recommendation, and the ruled rows
where those leave them standing. Where a ruled row's text says otherwise, the
new row is what is recommended, and the ruled row stands until the maintainer
rules.

### What the player sees

Scenario Stats, in each state, with a benchmark selected (the Category line
is absent without one). The lead number is the large number the PB card and
the latest-run card use; `(dimmed)` marks it drawn in the theme's dimmed
color:

```
| Typical score ⓘ            |  | Typical score ⓘ · 0 of 20 recent runs |  | Typical score ⓘ            |
| 2,999                      |  | 763.55                       (dimmed) |  | Too few runs               |
| Category: Tracking · Smooth|  | Category: Clicking · Dynamic          |  | Category: Clicking · Static|
| Total runs: 147            |  | Total runs: 91                        |  | Total runs: 8              |
          recent                              not recent                           too few runs
```

Whenever some of a value's runs are older than 30 days, the first line says
how many are recent, at full strength or not:
`Typical score ⓘ · 14 of 20 recent runs` over a full-strength value, and
`Typical score ⓘ · 6 of 20 recent runs` over a dimmed one. The number has a
dotted underline and a hover that says what it is from; the ⓘ explains the
line, the bands and the fading (see [Copy](#copy)).

The chart, Score vs Run, on VT ww5t Intermediate S5 around its return on
2026-02-14, after 82 days away. Under D the line keeps no limit's shape, and
the 30 days decide only how strongly it is drawn:

| Runs | Recent runs | Drawn | Value |
|---|---|---|---|
| 54 to 56, before the break | 20 of 20 | full strength | 1,240 |
| 57 to 65, back | 1 to 9 of 20 | faded | 1,240, bending to 1,260 as new runs replace old |
| 66 to 70 | 10 to 14 of 20 | full strength | 1,260, 1,275, 1,285, 1,290 |
| 76 on | 20 of 20 | full strength | 1,300, the same as A's |

Under A the faded stretch holds 1,240 flat and the line steps to 1,290 at run
66; under C it bends to 1,260 and steps to 1,290. D has no step: runs 66 to 70
are its lag, at most 30 points under A here.

The line's hover, on a point at full strength and one faded:

```
Typical score: 1,350                                 Typical score: 686.98
Runs: 20 in 4 sessions · Mar 2 to Apr 12             Runs: 20 in 5 sessions · Aug 20, 2025 to Apr 17
Recent: 14 of 20 in the 30 days up to this run       Recent: 6 of 20 in the 30 days up to this run
Middle 50%: 1,330 to 1,362                           Middle 50%: 622.44 to 729.86
Middle 80%: 1,310 to 1,385                           Middle 80%: 593.92 to 800.92
```

Score vs Time holds each value flat until the next run. A hold fades from the
moment fewer than 10 of its runs are recent, when its 10th-newest run turns
30 days old: a value whose 10th-newest run is 25 days old, with no run for 10
days after it, holds at full strength for 5 days and faded for the other 5.
The line ends at the newest run (TS3), so this happens only between two runs.
v8 holds the newest value to now and so draws it at the right end too: on
Flower 50cm, whose last run was on 2026-10-01, it turns faded on 2026-10-16.

Chart options, the Overlays group:

```
Overlays
 (●) Rank thresholds  ⓘ
 ( ) Show all ranks   ⓘ
 (●) PB score         ⓘ
 (●) Typical score    ⓘ
 (●) Middle 50%       ⓘ
 (●) Middle 80%       ⓘ
```

### The definition, exactly

- **The runs after a run** are the scenario's last 20 runs up to and including
  it, in play order, or all of them when it has fewer. Play order sorts by
  when a run ended.
- **Known** when those runs number at least 10 from at least 2 play sessions,
  or 20. A run's session is the play session it belongs to, split over every
  scenario's runs. Before that the value is unknown; once known, it is never
  unknown again.
- **The value** is their median, with P25 and P75 (the middle 50%) and P10
  and P90 (the middle 80%) interpolated between runs, the "inclusive" method:
  `statistics.quantiles(scores, n=4, method="inclusive")` and its `n=10`
  twin. An even count's median is the mean of the two middle scores.
- **Recent at a moment** when at least 10 of the value's runs ended in the 30
  days up to that moment, a run ended exactly 30 days before counting, from
  any number of sessions. Because the value counts the last 20 runs, "10 of
  them in the 30 days" is the same as "10 runs in the 30 days". Sessions
  decide only whether a value is known.
- **The moment** is now for Scenario Stats, a point's run for Score vs Run,
  and every moment of a hold for Score vs Time. With no run in between, a
  value's recent runs only age out, oldest first, so a hold that is recent at
  its run stops being recent once, at a moment worked out from their ages.
- **Every run counts,** at every sensitivity and on every version of the
  scenario, warm-up runs included, and runs of every version are treated as
  comparable (TS1, Versions). A run with no `Hash:` counts.
- **A time-scored scenario needs no special case within one version:** there
  a higher score is always a faster finish, so medians and percentiles order
  correctly, and nothing here is a percentage. Across versions whose
  countdowns differ that no longer holds, and the definition makes no
  comparability claim beyond TS1's assumption.
- **The constants** are 20 runs, 10 runs, 2 sessions, and 30 days, named
  once in the code.

### The chart

#### Score vs Run

- **The line has a point at each plotted run whose value is known,** at that
  run's place, joined by straight lines. A run before the scenario's first
  known value has no point.
- **The value at a plotted run counts the runs before it whether or not the
  range shows them,** as the New PB stars are judged over the whole history.
  So the line at the left edge of `Last 100 runs` is already the value that
  run had.
- **A point is drawn at full strength when its value was recent at its run,
  and faded when it wasn't.** A faded stretch starts at the last full-strength
  point before it and ends at the first after it, so the line and the bands
  are continuous, and since both sides are worked out the same way the line
  has no step where a stretch fades or turns recent.
- **A run axis has no time passing,** so a point's strength never changes
  after its run; how recent the value is now is Scenario Stats' to say.

#### Score vs Time

- **Each value holds flat from its run to the next plotted run,** a step at
  each run. The line ends at the newest plotted run (TS3).
- **A hold is at full strength while its value is recent,** and fades at the
  moment fewer than 10 of its runs are recent, when its 10th-newest run turns
  30 days old; a value that wasn't recent at its run holds faded throughout.
  The faded part ends where the next run's value begins, so the two meet.
- **Why the line ends at the newest run, and not now,** as TS3 ruled and v8
  does not: held to now, the time axis stretches to today. A scenario last
  played in 2020 would then draw its runs at the left edge of six empty years
  at All time, where today's axis spans its runs. Ending at the newest run also
  keeps the figure free of the clock, so a chart left open draws nothing new
  as days pass, and how recent the value is now is Scenario Stats', as on
  Score vs Run.

#### Score vs Sensitivity

No line and no bands, until that mode is redesigned: a rolling value has no
order along a sensitivity axis. The three switches change nothing there.

#### Traces, order and color

- **Up to six traces are added** after the run trace, the stars and the ring:
  the faded middle 80%, the faded middle 50%, the middle 80%, the middle 50%,
  the faded line, and the line, each only when its switch is on and it has a
  point to draw.
- **They draw under the runs by `zorder` −1,** not by coming first. So
  `figure.data[0]` stays the run trace, `generated_point_color` stays right,
  and the tests that read the run trace by position don't change. Inside
  their layer, data order draws the line over the bands, and full strength
  over faded. The prototype put its traces first and set the run color in
  the theme step to make up for it; this does neither.
- **One legend group per metric.** The legend reads `Run data point`,
  `New PB`, `Typical score`, `Middle 50%`, `Middle 80%`, ordered by legend
  rank. A faded trace sits in its metric's group with no entry of its own,
  unless the figure holds only its faded stretch, so a click on an entry hides
  the metric whole, faded stretches included. As with the stars, a legend
  click is not remembered; the switches are.
- **Gray in both themes, with no color setting,** themed in the presentation
  step by trace name, as the ring is. Light: the line `#343a40`, the middle
  50% that gray at 14% opacity, the middle 80% at 7%. Dark: `#dee2e6` at the
  same strengths. The figure is built with the light colors, as it is with
  the ring's. A faded trace is drawn at 35% opacity. The line is 2.5 px wide.
- **No customization beyond the switches.** The
  [2026-08-20 points entry](../decision_log/2026/2026-08-20-run-points-get-a-size-preset-and-a-color-and-the-chart-stops-there.md)
  keeps everything but the run points' size and color fixed. A switch shows
  or hides a metric, as the PB score switch shows a line; none styles
  anything.

#### Hover

- **The run points' hover doesn't change.** The bands take no hover. The line
  has its own, with the lines in [Copy](#copy): the value, its runs and their
  dates, how many are recent, and each band while its switch is on.
- On Score vs Time a hold has a point at each end, both with its value's
  hover, and the faded part of a hold that outlives its runs says so.

#### The zoom fit

**The line and the bands take part in the fit, as wanted.** The script already
fits every visible trace, so a refit keeps the band inside the view instead of
clipping it, and a hidden band leaves the fit as today. The script's
comment, which names only the runs, the stars and the ring, is updated, and
so is the spec's sentence. One case is left: on Score vs Time a flat hold that
spans the whole zoomed window has no point inside it, so it doesn't widen the
fit; the line is a median of runs and almost always sits among them.

#### The switches

- **In the Overlays group, after PB score:** `Typical score`, `Middle 50%`
  and `Middle 80%`, each with a help icon, all on to start, remembered in the
  browser like every Chart options control.
- **Their ids and defaults are chosen once:**
  `run-history-typical-score-overlay-switch`,
  `run-history-middle-50-overlay-switch` and
  `run-history-middle-80-overlay-switch`, all checked by default. Dash
  discards a stored value when a later visit draws a different default
  ([2026-09-19](../decision_log/2026/2026-09-19-a-query-parameter-selects-a-control-it-does-not-suspend-its-memory.md)),
  so neither may change.
- **They are inputs of the chart rebuild,** as the PB score switch is, so the
  figure holds a metric's traces, and the hover its line, only while its
  switch is on. A band may show without the line.

#### The legend

With Chart options open, the five entries no longer fit on one line beside the
chart's title and wrap onto a second line over it (v8, 1,800 px window). The
Backlog already holds the same wrap for three entries on a narrow chart. PR 2
lays the legend out so that it never covers the title, measured at the
narrowest chart the Backlog item names, a 657 px graph with Chart options
open. The labels stay: shorter ones would say less and still wrap on a
narrower chart. Where the legend goes, under the title on a line of its own
or under the plot, is PR 2's to choose and show.

### The Scenario Stats lead

- **The first line** reads `Typical score` and a help icon, then, whenever
  some of the value's runs are older than 30 days, how many are recent (see
  [Copy](#copy)). It stays plain text, as the 2026-10-18 entry made it.
- **The lead** is the value in the PB and latest-run cards' lead number,
  with a dotted underline for its hover, and in the theme's dimmed color when
  it isn't recent. The lead number is large text, so PR 3 checks the dimmed
  color against the 3:1 that large text needs, in both themes.
- **Under it,** `Category:` with a benchmark selected, then `Total runs:`.
- **With no scenario selected** the card reads `No scenario selected` in
  place of its lead and lines, as it does today. With no local runs, the lead
  reads `No runs yet` and `Total runs: 0` follows. Below the minimum, it
  reads `Too few runs`.
- **It is worked out again when a run lands on the selected scenario, when
  the scenario changes, and on the page's 30-second tick,** so it dims within
  30 seconds of the test failing. The card has no tick of its own since #391;
  it takes the page's, which the PB card already reads. The time is the app's
  own clock. A run costs at most the 3.9 ms measured above.
- **Its value is the chart's last point's,** from the same function; its
  recency is as of now.

### Rounding

A shown value is rounded to the most decimal places any run in its window
scored, at most two, with a half rounding up, then formatted as a score is.
So a window of whole-number scores whose median is 2,140.5 shows `2,141`,
never `2,140.5`, a scenario scored to one decimal shows one, and a tracking
scenario's six decimals show two. The half-up step is a `Decimal` quantize
with `ROUND_HALF_UP`: `round()` and
`format_score`'s format spec both round a half to even, so `round(2140.5)`
is 2140. A median or a percentile is shown no more
precisely than the runs it comes from, as the roadmap's honesty principle
asks. Rounding is for display only: the definition keeps the exact values.

### How it is built

- **One pure module, `source/kovaaks/typical_score.py`,** takes a scenario's
  runs in play order and the play sessions, and returns the value after each
  run: its median, quartiles, P10 and P90, run and session counts, first and
  last dates, and whether it is known. A second function answers whether a
  value is recent at a moment handed in, with its recent runs and their
  sessions counted, and a third the moment a held value stops being recent.
  Nothing reads the run store inside it.
- **One copy of the run store per build.** The scenario's runs are taken from
  the same copy the sessions are split from, so a run that lands mid-build
  can't be in one and not the other. A plotted run that copy doesn't hold
  gets no point, and the rebuild its landing triggers draws it.
- **Nothing is stored.** The value is worked out from the runs whenever the
  chart or the card asks, as sessions are.
- **The prototype is read for behavior, not copied.** It is a patch over the
  app; the build writes the module and the traces afresh.
- **The cost was about 4 ms at worst per chart build** under TS2's rule, on
  top of today's 4 to 7 ms, and the figure about doubles in size at the
  default range. D adds a recency test at each point; PR 2 measures it again.

### Where prototype v8 differs

So these don't read as open questions:

- **v8 holds Score vs Time's newest value to now,** which TS3 rejects, so it
  draws a fade at the right end that this design shows only between runs. Its
  explainer's last sentence says the card and Score vs Time judge as of now,
  which holds only there; the [Copy](#copy) here fits TS3.
- **v8 puts its traces first** and sets the run color in the theme step, as
  earlier prototypes did.
- **v8's switches carry prototype ids,** and its panel at the bottom right
  offers the options TS6 compares.

### Beside Median and best

The two answer different questions and keep different words. Median and best,
in the run list, describe the runs under one row: a session's or a visit's,
all of them, with no window and no minimum, and they compare nothing. The
typical score is a rolling figure over the last 20 runs, with a minimum,
worked out after each run, and it is what later judgments read. A session
row's median and the typical score after that session's last run will often
differ, and that is correct. The labels keep them apart: `Median` never says
typical, and `Typical score` never says median. The glossary's Median and best
entry changes its pointer from "a later proposal" to the Typical score entry.

### Copy

Every string this proposal adds or changes. They follow the nine copy rules in
[AGENTS.md](../../AGENTS.md#styling-conventions). They were drafted in
prototype v8 with the maintainer, redlined in an advisory consult with
`gpt-6.1-sol` on 2026-10-19, and revised after the third review wave. `{n}`
is the number of runs behind a value, at most 20; `{k}` its recent runs;
`{s}` its sessions. `1 run` and `1 session` take the singular;
`{k} of {n} recent runs` stays plural, its noun counting the `{n}`. Dates
are the run list's short date, with the year only when it isn't this year,
and a span on one date reads `on {date}`. `**…**` is bold through
`control_name()`.

| Where | String | Why |
|---|---|---|
| Scenario Stats, first line | `Typical score`, alone when every run behind the value is recent | Names the lead figure, as `PB` opens the PB card's first line and `Latest run` the latest-run card's (TS8). |
| First line, some of the value's runs older than 30 days | `Typical score · {k} of {n} recent runs`, `0 of {n}` included | Shows the mixture whether the value is at full strength or dimmed: how far along a return is, and that a full-strength value still holds older runs. No date: under TS6 it would always be the newest run's, which the hover's Runs line and the latest-run card already show. |
| First line's help icon, accessible name | `About the typical score` | Not `Typical score help`: the Typical score switch's help icon has that name, as `settings_help_label` names every one `{label} help`. |
| Lead, value | `{score}`, such as `2,999` | Rounded as [Rounding](#rounding) says, formatted as a score is; dimmed when not recent. |
| Lead, too few runs | `Too few runs` | No "recent": this minimum has no age limit. |
| Lead, no local runs | `No runs yet` | As the latest-run card's empty state says it. |
| No scenario selected | `No scenario selected` | The card's shipped empty state, unchanged. |
| The count line | `Total runs: {n}` | Replaces `Number of runs:`, so the count isn't read as the runs behind the typical score (TS8). |
| Lead hover | `The median of your last {n} runs.`, or `The median of your {n} runs.` when those are all of them; then `**Runs:** {n} in {s} sessions · {first} to {last}`, `**Recent:** {k} of {n} from the last 30 days`, `**Middle 50%:** {p25} to {p75}`, `**Middle 80%:** {p10} to {p90}`, one line each | A sentence, then readouts with bold labels, as the chart's hover has them. Recency counts no sessions, so the Recent line names none. |
| Lead hover, too few runs | `A typical score needs 10 runs across 2 or more sessions, or 20 in one session. You have {n} runs in {s} sessions.` | The existence minimum, the only rule that counts sessions, with no 30 days in it, and the count behind the lead. Two sentences and no list; shown only on a scenario with no value, where it says what to play. |
| First line's help | `Your typical score is the median of your last 20 runs of this scenario, or of all your runs if you have fewer. Runs count regardless of age.` / `On the chart, the darker band shows the middle 50% of those scores, and the lighter band the middle 80%. Narrower bands mean more consistent scores. Turn the line and bands on or off in **Chart options**.` / `A faded line, or a dimmed number on this card, means fewer than 10 of the runs behind your typical score are from the last 30 days, so it may be out of date.` / `The card shows how recent it is today, and the chart how recent it was at each run.` | Four paragraphs: what the figure is, what the bands mean, when it fades and why that matters, and why the card and the chart's last point can differ. The help opens from the card, over a number that dims, so it names both. The third paragraph is the maintainer's choice of 2026-10-19, put to review. It states the whole recency rule in one sentence, with no term for the opposite state: "full strength" stays a word of this document. It says what fading means for the player, "may be out of date", and leaves room for an older value that is still right. It shows a full-strength value's mixture by implication, since a value with 10 recent runs isn't faded while up to half of its runs can be older, and the card's count shows it outright. "The runs behind your typical score" holds for a scenario with fewer than 20 runs. The fourth paragraph, reworded by the author on the same day, says the card and chart difference without "judges recency". No lesson on what a median is, and nothing the chart shows by itself, as the maintainer asked; "consistent" is the word players use. |
| Chart legend | `Typical score`, `Middle 50%`, `Middle 80%` | Sentence case, the switches' words. |
| Line hover | `**Typical score**: {score}`, `**Runs**: {n} in {s} sessions · {first} to {last}`, `**Recent**: {k} of {n} in the 30 days up to this run`, `**Middle 50%**: {p25} to {p75}`, `**Middle 80%**: {p10} to {p90}`, one line each | The card hover's lines. "Up to this run" because each point is judged at its run. A band's line shows while its switch is on. The percentile names are dropped: they add terms and no information. |
| Line hover, a hold faded after its runs aged out | `**Recent**: too few · last run {date}` | Score vs Time only; the count changes along the hold, so it isn't given. |
| Chart options switch labels | `Typical score`, `Middle 50%`, `Middle 80%` | The legend's words, as the PB score switch takes its line's. |
| Typical score switch help | `Draws your typical score: the median of your last 20 runs, or of all your runs if you have fewer. It's faded where too few of them are recent. **Score vs Sensitivity** doesn't show the line or bands.` | What it draws and where it doesn't. |
| Middle 50% switch help | `Shades the middle 50% of the runs behind your typical score. A narrower band means more consistent scores. **Score vs Sensitivity** doesn't show this band.` | As the explainer says it; each help names the mode it doesn't apply to, since each is read alone. |
| Middle 80% switch help | `Shades the middle 80% of the runs behind your typical score, in a lighter shade than the middle 50%. **Score vs Sensitivity** doesn't show this band.` | |
| Switch help icons, accessible names | `Typical score help`, `Middle 50% help`, `Middle 80% help` | `settings_help_label`'s `{label} help`, plain text, as an accessible name stays. |

### Terms

Each entry is written as [docs/glossary.md](../glossary.md) would hold it,
under "Scores and notifications", beside PB. Each implementation PR moves in
what it ships, so the glossary never describes a surface the app doesn't
draw yet: PR 1 Typical score and Recent without their on-screen lines, with
the Median and best correction; PR 2 Middle 50% and Middle 80%, and Recent's
chart line; PR 3 Recent's Scenario Stats line and the Scenario Stats
correction.

- **Typical score.** What a player's runs on a scenario usually score: the
  median of its last 20 runs, or of all its runs when it has fewer, whatever
  their age. It is known once those runs number at least 10 from at least 2
  sessions, or 20, and before that it is unknown, which is never read as weak.
  It is drawn at full strength when recent and faded when not. The rules are
  in the typical score's spec.
  - The roadmap and the decision log call it the typical run.
  - Not Median and best, which describe the runs under one row of the run
    list, with no minimum.
  - Not the median KovaaK's leaderboard shows, which is the median player's
    PB.
  - In code: `typical_score`.
- **Recent.** The state of a typical score at least 10 of whose runs are from
  the 30 days up to a moment, from any number of sessions. Scenario Stats
  judges it as of now, and the chart at each point. A recent value can still
  hold runs older than 30 days, up to half of them.
  - On the chart: a full-strength stretch; not recent, a faded one.
  - On Scenario Stats: an undimmed lead number; not recent, a dimmed one.
    Whenever some of the value's runs are older than 30 days, recent or not,
    `{k} of {n} recent runs` follows `Typical score`.
  - In code: `recent`.
- **Middle 50%.** The range the middle half of the runs behind a typical
  score fell in: from the first quartile to the third, P25 to P75. Run
  History draws it as a band around the typical score while its switch is on.
  - On screen: `Middle 50%`.
- **Middle 80%.** The range the middle 80% of the runs behind a typical score
  fell in: from the 10th percentile to the 90th, P10 to P90. Run History draws
  it as a lighter band while its switch is on.
  - On screen: `Middle 80%`.

Entries the same PRs correct: **Median and best** says "Not the typical run,
which is what a player's recent runs usually score. A later proposal defines
that." It becomes "Not the typical score, which is what a player's runs on a
scenario usually score." **Scenario Stats** says "On screen its first line
reads `Scenario stats`." It becomes "On screen its first line reads
`Typical score`, the figure it leads with."

### Decisions this changes

The shipping PRs keep each entry and add a dated "Superseded in part" note.
They erase nothing.

- [2026-10-12, the chart plots every run and draws no summary line](../decision_log/2026/2026-10-12-the-run-history-chart-plots-every-run-and-draws-no-summary-line.md):
  "no mode draws a summary line", and its reason that a summary line "would
  be a second definition of the typical run". The typical score is that
  definition, so Score vs Run and Score vs Time draw it. Score vs Sensitivity
  still draws no summary.
- [2026-10-04, skill is judged by the typical run](../decision_log/2026/2026-10-04-skill-is-judged-by-the-typical-run-with-honest-uncertainty-in-verdicts-not-advice.md):
  its Terms paragraph calls the typical run a working word that the proposal
  shipping it names. It is named the typical score on screen, in the glossary
  and in code. D1, D2 and D3 stand.
- [2026-10-14, Scenario Stats names the selected benchmark's category](../decision_log/2026/2026-10-14-scenario-stats-names-the-selected-benchmarks-category.md)
  and
  [2026-10-14, a card's lines follow their role in the player's next action](../decision_log/2026/2026-10-14-a-cards-lines-follow-their-role-in-the-players-next-action.md):
  Scenario Stats was a card with no lead fact, its lines at one weight in
  importance order. Under TS8 it leads with the typical score, and Category
  and Total runs follow at one weight. T4's rule stands for cards with no lead.
- [2026-10-18, Last played leaves Scenario Stats and its first line is plain text](../decision_log/2026/2026-10-18-last-played-leaves-scenario-stats-and-its-first-line-is-plain-text.md):
  the first line stays plain text and reads `Typical score` instead of
  `Scenario stats`, and `Number of runs:` becomes `Total runs:`.

Statements in the specs that go untrue, which the same PRs rewrite:

- [run_history.md, The chart](../specs/run_history.md#the-chart): "No mode
  draws a summary line"; the zoom fit's "the run points inside the x window"
  and its note that the stars and the ring are the only other traces; and the
  list of what the Share chart figure holds, which gains the typical score's
  line and bands with their hover.
- [run_history.md, Chart options panel](../specs/run_history.md#chart-options-panel):
  "Three groups in order, holding seven controls" becomes ten, with
  `Typical score`, `Middle 50%` and `Middle 80%` on in Overlays.
- [run_history.md, Scenario Stats](../specs/run_history.md#scenario-stats):
  the first line "Scenario stats", and "Category:" and "Number of runs:" at
  one weight under it, become the typical score's first line and lead over
  "Category:" and "Total runs:"; `Number of runs: 0` becomes `Total runs: 0`.
- [run_history.md, Time-scored scenarios](../specs/run_history.md#time-scored-scenarios):
  the list of surfaces that order or place scores, unchanged on a
  time-scored scenario, gains the typical score.
- [sessions.md, Where sessions show](../specs/sessions.md#where-sessions-show):
  "The Run History page is the one page that shows a session, in two places:
  its run list and its latest-run card." The typical score's hovers count the
  sessions behind a value, a third place.
- [glossary.md, Median and best](../glossary.md#median-and-best) and
  [Scenario Stats](../glossary.md#scenario-stats), as above.

Untouched: the 2026-10-14 Median and best entry, whose label rule this keeps,
and the 2026-08-20 points entry (see Traces, order and color).

### Alternatives rejected

Each was drawn in a prototype or measured, on the maintainer's stats.

- **Steps once per session** (v1). The same statistic sampled once per
  session; it drew a staircase that hid the runs' effect inside a session.
- **Session values joined** (v2). It mixes the per-session freeze into the
  line, which belongs to comparisons (TS3).
- **A carried stretch dotted, with no band** (v3 to v5). It read as gaps
  everywhere; fading keeps the band and the continuity.
- **A carried value held flat and faded** (v6), TS2's recommendation. TS6.
- **A's value while recent, the last 20 at any age while not** (v7). TS6.
- **No limit at full strength.** TS6, and TS2's case against it.
- **7, 14 and 60 days as the window.** Measured under TS2's rule: 7 days loses
  fresh values that 14 and 30 days get right; 14 equalled 30 in 2026 and held
  flat "as of" values under the 2025 climb; 60 days, like no limit, called
  months-old values current after a return. TS6 keeps 30 days for the test.
- **2 recent sessions in the full-strength test,** D's first test, and
  **sessions dropped from both rules, or "or 20 in one session" dropped from
  both.** TS6.
- **At least 20 recent runs from 2 sessions, and at least 15 of 20 recent,**
  as the test. TS6.
- **No line before a scenario's first recent value.** TS6.
- **A window the player chooses.** TS2.
- **The rolling maximum and minimum** as ceiling and floor. TS4.
- **The line drawn lighter until its window is full,** as Aimcurve draws its
  median. The minimum already does that job: below it there is no line, and
  above it the hover says how many runs and sessions are behind the value.
- **Two sessions only until a scenario is established,** the maintainer's own
  variant. TS1.
- **Runs at the current sensitivity, or on the current version, only.** TS1;
  the version alternatives under its Versions.
- **Holding the newest value until now on Score vs Time,** as the prototypes
  do. [Score vs Time](#score-vs-time).
- **The traces first in the figure,** as the prototype put them. It moves
  the run trace off index 0, so the run points take another colorway entry
  unless their color is set, and every test that reads `figure.data[0]`
  changes. `zorder` draws them under the runs from the end of the list.
- **One switch for the line and the middle 50%, legend clicks alone, or one
  band chooser.** TS7.
- **A "Typical score:" line second in Scenario Stats,** TS5 as ruled, and a
  smaller label under a "Scenario stats" first line. TS8.

## Delivery plan

Three implementation PRs. This is intent, not a contract: a boundary that
moves is noted in that PR's description.

1. **The definition.** `source/kovaaks/typical_score.py` with its pure
   functions and tests, a new capability spec, `docs/specs/typical_score.md`,
   and `architecture.md`. Nothing on screen, as the Sessions implementation
   shipped. Needs nothing.
2. **The chart.** The line, the bands and the faded stretches on Score vs Run
   and Score vs Time, their order, colors, legend groups and hover, the three
   switches, the legend's layout, the zoom fit's comment, and the Run History
   spec's chart and panel sections. Needs PR 1. It doesn't touch the top row.
3. **The Scenario Stats lead.** The first line, its help, the lead and its
   hover, Total runs, its updates, and the spec's Scenario Stats section.
   Needs PR 1.

**Why three.** The definition is the contract later features read, and a PR
of its own keeps its review on the boundaries rather than on plotly. The
Scenario Stats lead is another module, with its own live checks of the top
row. If the maintainer prefers fewer PRs, PR 1 can fold into PR 2, or PR 3
into PR 2, each at the cost of one larger review.

Each PR updates the specs and the glossary entries its own behavior changes,
as it ships ([Terms](#terms) says which entry goes with which PR). The last
of them to merge ships the proposal, by the
[Shipping a proposal](../../AGENTS.md#shipping-a-proposal-docs-definition-of-done)
checklist: a decision-log entry for each row, the notes in
[Decisions this changes](#decisions-this-changes), the user guide, the
roadmap, `product.md`, the vault Backlog bullet named in
[Out of scope](#out-of-scope), and this file deleted.

**Recommended:** `claude-opus-5-5`, at high for PRs 1 and 3 and at xhigh for
PR 2, which walks each state through two chart modes, the themes, the
switches, the legend's layout and the zoom fit. The maintainer looks at PRs 2
and 3 in their own Firefox before each merges.

### Fallbacks

- **PR 2 grows too large.** Ship Score vs Run first and Score vs Time after,
  or the legend's layout as a PR of its own before the line.

## Out of scope

Each with where it is tracked.

- **Comparisons and the session freeze:** "better than 15 of your last 20",
  a percentage against the typical score, and the value held fixed through a
  session for them. The vault Backlog's Post-Run Analysis items 3 and 6.
- **The score trend verdict.** The roadmap's Future list; its chart is the
  one this proposal draws.
- **Weakness by the typical run.** The roadmap's Future list. Whether it
  judges on a value that isn't recent is its own proposal's to decide.
- **The rank-up chance.** The roadmap's Future list, as difficulty measured
  against the player's own runs; the middle 80% against the rank lines is its
  picture.
- **The warm-up rule.** Its own discussion once this ships, as the maintainer
  chose; parked in the 2026-10-11 sessions entry and the Backlog's session
  gap ideas. It will shift the figure.
- **Typical accuracy.** The Backlog's Post-Run Analysis item 8; it would
  follow this definition.
- **A consistency number,** such as the gap between P25 and P75 as a figure.
  The Backlog's Features item 2.3; the band shows it for now.
- **The PB card's use of the figure,** such as the typical score beside the
  PB. The top row cards work didn't include it, and the maintainer chose
  to carry that dependency. The roadmap's Typical score entry names it, and
  the PR that ships this proposal adds it to the vault Backlog as a one-line
  bullet, so it outlives this file.
- **Score vs Sensitivity's redesign,** which might draw a typical score per
  sensitivity. Recorded as lost in the 2026-10-12 chart entry.

## Testing

- **Unit, the definition,** through pure functions on hand-built runs and
  sessions, each state and boundary: 9 runs (unknown), 10 runs from one
  session (unknown), 10 from two (known), 19 in one sitting (unknown), 20 in
  one sitting (known); the value from the last 20 at any age, and from all of
  them below 20; known never turning unknown; an even count's median; the
  quartiles and deciles against hand-worked values; another scenario's runs
  joining two of this scenario's runs into one session; every sensitivity and
  version counted; same-second runs in play order; rounding of whole,
  one-decimal and six-decimal scores, a half rounding up.
- **Unit, recency:** 10 recent runs (recent), from 2 sessions and from one;
  9 (not); a run ended exactly 30 days before the moment (counts) and one
  second more (doesn't); a known value, from 2 sessions or 20 runs, whose 10
  recent runs are all one session's (recent); recent at the run and not
  later, with the fade moment of a hold equal to the moment its 10th-newest
  run passes 30 days; a value recent at its run whose card, a day later,
  isn't; the count of a value's recent runs, all of them, some with the value
  recent, and none.
- **Unit, the chart's traces,** per mode on a hand-built history: which
  points are full strength and which faded, the joins at each end of a faded
  stretch with no step in the value, Score vs Time's holds, their fade moment
  and their end at the newest run; `figure.data[0]` the run trace, `zorder`,
  one legend group per metric, legend ranks; no traces with no known value,
  and none on Score vs Sensitivity; each metric's traces only with its switch
  on; the hover's lines, a band's line only with its switch on.
- **Unit, the presentation step:** each theme's colors on the line and bands,
  and the run points' color unchanged.
- **Callbacks:** each switch rebuilds the chart; the lead updates on a run on
  the scenario, on a scenario change, and when the value stops being recent on
  the tick; its empty states and first-line readouts, `{k} of {n} recent
  runs` over a full-strength value and a dimmed one, and none when every run
  is recent.
- **Live, PRs 2 and 3,** in headless Edge at 2560 and 1920 px, light and
  dark: the line and bands under the runs, the faded stretches, the legend,
  its clicks hiding a metric whole, and its layout with Chart options open,
  the switches and their memory, the hover, a zoom that refits to the bands,
  the lead's dimmed contrast, and the top row's height with the lead and the
  longest first line, `Typical score ⓘ · 19 of 20 recent runs`, with
  and without a benchmark; if it wraps, PR 3 shortens it and lists the new
  string in its description. These
  cover what pure tests can't: draw order, theme colors, the zoom script, and
  layout. Then the maintainer's look in Firefox.
- **Performance,** measured again on the largest scenario in PR 2.
- **Docs:** `tests/test_docs.py` for links and summaries, and the gates in
  AGENTS.md.
