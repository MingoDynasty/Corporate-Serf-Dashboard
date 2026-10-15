# Typical Score Proposal

Status: Proposed
Date: 2026-10-15

## TL;DR

The app's stated direction is to judge skill by what a player's recent runs
usually score, but it has never defined that figure, so no page shows it and
the Run History chart draws no line for it. This proposal defines the
typical score as the median of a scenario's last 20 runs from the 30 days up to
each run, known once those runs number 10 from two sessions or fill all 20, and
carried forward with an "as of" date when later runs fall short. The chart
draws it after every run as a gray line with the middle half of the runs
shaded around it, faded where it is only "as of", with a lighter band for the
middle 80% behind a Chart options switch. Scenario Stats shows the figure after
the scenario's newest run, dated when it is old.

## Decisions needed

Five rows, TS1 to TS5. **Nothing in this proposal is ratified.** Each row is
the maintainer's lean or agreement from the design discussion of 2026-10-14
and 2026-10-15, worked out over five measurements and six versions of a live
prototype on their own stats, and each quotes what they said. A lean is not a
ruling: reviewers are invited to challenge any row, and any author-owned
choice in [Design](#design). **TS2 is the row the maintainer asked to be
scrutinized hardest**, and it gives the alternative its strongest case.

Already ratified, and not reopened here: D1 to D3 of the
[2026-10-04 entry](../decision_log/2026/2026-10-04-skill-is-judged-by-the-typical-run-with-honest-uncertainty-in-verdicts-not-advice.md)
(skill is judged by the typical run, unknown is not weak, verdicts not
advice); S1 to S4 of the
[2026-10-11 sessions entry](../decision_log/2026/2026-10-11-a-session-ends-after-a-break-of-more-than-30-minutes.md),
whose S4 sends this definition to a proposal of its own; R1 to R7 of the Run
History page; A1 to A3 of All scenarios; and T1 to T4 of the
[top row cards proposal](top_row_cards_proposal.md).

The evidence below is one player's history: the maintainer's 9,135 runs over
866 scenarios in 325 play sessions, last run 2026-10-09 22:03. It shows what
the rules do on that history and nothing about other players'.

### TS1. The definition

Status: Open. The maintainer's lean, built up over the discussion: "I agree
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
- **Every version counts, as the PB counts them.** The version rule of the
  [2026-10-12 marks entry](../decision_log/2026/2026-10-12-a-past-runs-check-is-judged-against-the-pb-it-was-chasing-under-its-own-version.md)
  covers a time-scored run's pace only. A reworked scenario clears out of a
  20-run, 30-day window on its own. PR #351's row H4 kept the current version
  alone; this departs from it.
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

This answers the two comments on PR #351 that S4 handed to this proposal. The
figure
[staying known from an arbitrarily old session](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/351#discussion_r4191712540)
is the "as of" state: it stays known, and says how old it is. Holding a run's
[comparison set fixed for its session](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/351#discussion_r4191712550)
is TS3: the chart draws the value after every run, and the session freeze
belongs to the comparisons that come later.

### TS2. Window and staleness on the chart

Status: Open, **for heavy scrutiny.** The maintainer, 2026-10-15: "Let's go
with the 30 day window for now, but I'd like for this to be heavily
scrutinized during proposal review. On paper it seems like it's the best
approach to keep a consistent definition and to make future proposals
smoother. But from a user perspective, seeing the continuous line with No
Limits looks much more appealing than the 30 day option with gaps everywhere;
i.e. with these many gaps, I wonder if it's even worth showing at all." Then,
after seeing the faded style: "Yes: faded, with bands kept, is the
recommended style; no limit stays the alternative in the scrutinized
decision."

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

1. **One answer to "is this current?" for every reader.** The roadmap's
   later judgments read this figure: weakness by the typical run, and the
   rank-up chance, which weighs recent form. Each needs to know whether the
   value is recent. With a window in the definition, they share one answer
   with the chart and the stats line. With no limit, each one writes its own
   recency rule, and the chart and a weakness column can disagree about
   whether the same scenario is known. That is the "second definition of the
   typical run" the
   [2026-10-12 chart entry](../decision_log/2026/2026-10-12-the-run-history-chart-plots-every-run-and-draws-no-summary-line.md)
   refused, repeated once per feature.
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
reason the window must be argued and not assumed. It loses on two counts.
First, a reader can always ask for more recency than the definition's, but a
reader of a no-limit figure must add a rule before it can trust any value, so
every reader restates one, and the typical run means something different on
each page. Second, a display rule that says "as of" over a no-limit value,
which the alternative's point 3 relies on, is itself a second definition of
"current": the stats would call a value old while the chart drew it at full
strength. The coverage in the alternative's point 1 is real, but the runs it
adds are the values the measurement found weakest: months-old medians
labelled current. So the recommendation stands,
and the faded style is how it keeps the picture whole.

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

Status: Open. The maintainer: "Agreed: draw the typical score per run on the
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

Status: Open. The maintainer: "Yes: include the P10 to P90 band as a Chart
options switch, off by default, lighter shade."; "I think P10 and P90 are the
better metrics than min/max."

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

Status: Open. The maintainer: "Ship it first in today's Scenario Stats; the
cards proposal can move it later."; "keep as no limit. '2,140 · as of Mar 3,
2020' is still useful information, even if it is outdated."

The material consequence: Scenario Stats gains a line, and the top row grows
4 px with a KovaaK's username set, 20 px without one, until the cards work
makes room.

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

**Written against the Scenario Stats card at this proposal's base**
(`ccce6c6`): the top row cards' PR 1 (#380) made the block a card with its
content unchanged, Last played, Number of runs and Position, so the line goes
after Number of runs. The top row cards proposal was ratified and merged after
the maintainer's lean. Its card holds Category, Last played and Number of runs
(its T2), its PB card takes Position, and a card orders its lines by
importance (its T4); it doesn't mention the typical score. The maintainer
chose to carry that dependency, and this proposal does not edit that one.
What the rest of the cards work changes here:

- **Its PR 2** moves Position and Refresh out of the card, which frees the
  room of about two lines.
- **Its PR 3** adds Category as the card's first line, while a benchmark is
  selected.
- **Its T4** decides where the line sits among Category, Last played and
  Number of runs; a later move to the PB card, beside the PB, is that work's
  call too.

**The cost, measured at the base** (headless Edge at 2560, 1920 and 1536 px,
the maintainer's stats): the row is 141 px, set by the dropdowns' column. With
a username, simulated as a one-line Position, the card fits in it, and a
fourth line of the same style makes the card and the row 145 px, 4 px taller.
Without a username, Position's hint takes a line of its own and the row goes
from 149 px to 169 px. The card's text is 300 px wide, and every value in
[Copy](#copy) fits on one line in it, the longest being
`Too few recent runs · 16 of 20`. The prototype's `Not enough recent runs`
wraps there with a two-digit count.

**A question for the maintainer: does the Scenario Stats line ship before or
after the top row cards' PRs 2 and 3?** The author's recommendation is to hold
neither for the other. Shipping first, as the lean said, costs the row 4 px
with a username until the cards' PR 2 frees room. The cards' PR 2 will likely
land first anyway, because this line waits for the definition's PR. Both edit
the Scenario Stats module, so whichever lands second rebases onto the
other's. The definition and the chart don't touch the top row and wait for
nothing.

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
- **Scenario Stats shows Last played, Number of runs, and Position**
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

The measurements, their method and their caveats are in the maintainer's
scratch folder: the window evaluation, its 30-day rerun, and the session-rule
comparison, with their scripts. The caveats that matter most: one player; a
steep improvement phase in 2025 and a plateau in 2026, where the windows part
in the first and not the second; targets from sessions of three to five runs
are noisy; and many cells about returns and grinds come from a handful of
sessions.

### Verified facts

Checked at `ccce6c6`, this proposal's base, on 2026-10-15. They were first
checked at `1799df0`; the top row cards' PR 1 (#380) merged between, and
changed none of what is listed here except that Scenario Stats is now a card.

- **The chart's builders.** `build_run_history_figure` in
  `source/components/run_history_chart.py` reads the scenario's runs in play
  order, judges new PBs over the whole history, then applies the range.
  `generate_score_vs_run_plot` and `generate_score_vs_time_plot` in
  `source/plot/plot_service.py` build the run trace first, then the New PB
  trace, then the ring (`RUN_DATA_POINT_TRACE_NAME`, `NEW_PB_TRACE_NAME`,
  `LATEST_RUN_TRACE_NAME`).
- **The run points' color depends on the run trace coming first.**
  `generated_point_color` reads the template's first colorway entry, the one
  plotly gives the first trace that sets no color. Four test files read the
  run trace as `figure.data[0]`: `test_plot_service.py`,
  `test_plot_service_run_history.py`, `test_chart_options.py`,
  `test_chart_point_appearance.py`.
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
  `source/components/scenario_stats.py`. With no scenario selected, Number of
  runs reads `0` and Position `N/A`.
- **Formatting.** `format_score` gives thousands separators and at most two
  decimals; `format_short_date` gives `Oct 12`, or `Mar 3, 2020` in another
  year.
- **Scores' precision.** Of the 9,135 runs, 7,137 scored a whole number, and
  1,611 carry five or six decimals.

Measured on 2026-10-15, the cost, the size and the draw order at `1799df0`,
whose chart code the base leaves unchanged, and the row at the base:

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

### What the player sees

The Scenario Stats card, as it is at the base, in each state:

```
| Scenario Stats              |  | Scenario Stats                      |  | Scenario Stats                      |
| Last played: 2 minutes ago  |  | Last played: 2 months ago           |  | Last played: 5 minutes ago          |
| Number of runs: 463         |  | Number of runs: 169                 |  | Number of runs: 6                   |
| Typical score: 1,179        |  | Typical score: 1,390 · as of Apr 12 |  | Typical score: Too few recent runs · 6 of 20 |
| Position: ...   Refresh     |  | Position: ...   Refresh             |  | Position: ...   Refresh             |
         fresh                              as of                                  unknown
```

The value has a dotted underline and a hover that says how it was worked out
(see [Copy](#copy)).

The chart, Score vs Run, on a scenario played on and off (the shape of VT
ww5t Intermediate S5 over its last 200 runs). `▒` is a band and `━` the line,
at full strength; `░` and `┄` are the same band and line at a third of their
strength, not a dotted line:

```
VT ww5t Intermediate S5                 ● Run data point   ★ New PB   ━ Typical score   ▒ Middle 50%
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -  PB score (1470.00)
     ·   ★     ·     ·   ★    ·    ·      ·   ★    ·     ·    ·   ★   ·     ·   ·
                    ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒░░░░░░░░░░░░░░▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
             ━━━━━━━━━━━━━━━━━━━━━━━━┄┄┄┄┄┄┄┄┄┄┄┄┄┄━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ·    ·         ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒░░░░░░░░░░░░░░▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒
     ·     ·   ·     ·     ·    ·       ·  ·     ·     ·    ·     ·     ·     ·
|-- unknown --|------- fresh ---------|--- as of ---|---------- fresh -------------|
  no line yet:  the 10th run from two   a break, then  10 runs from two sessions in
  under 10 runs sessions                one run: the   the window again; the faded
                                        last value is  stretch joins this run
                                        carried
```

The line's hover, on a point of a fresh stretch and of a faded one:

```
Typical score: 1,350                         Typical score: 1,350
Middle 50% (P25 to P75): 1,330 to 1,362      Middle 50% (P25 to P75): 1,330 to 1,362
20 runs in 4 sessions · Mar 2 to Apr 12      20 runs in 4 sessions · Mar 2 to Apr 12
                                             As of Apr 12
```

With **Middle 80%** turned on, a lighter band surrounds the middle 50% and
the hover gains `Middle 80% (P10 to P90): 1,310 to 1,385` under the middle
50%.

Score vs Time, the same scenario at All time. Each value holds flat until the
next run; a hold that runs on more than 30 days past the newest run behind it
fades from that point:

```
                                                                  ┏━━━━━━━━━━ ends at the
         ┏━━━━━━━━━━━━━━━━━━━━━━┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┛·  · ·  ·   newest run
  ━━━━━━━┛ ·  · ·               ↑                                 · ·
   · ·  ·                       30 days after the newest run
                                behind the value, the hold fades
  Sep 2025        Nov 2025        Jan 2026        Mar 2026        May 2026
```

Score vs Sensitivity is unchanged: no line and no bands.

Chart options, the Overlays group:

```
Overlays
 (●) Rank thresholds  ⓘ
 ( ) Show all ranks   ⓘ
 (●) PB score         ⓘ
 ( ) Middle 80%       ⓘ
```

### The definition, exactly

- **The window after a run** is the scenario's runs up to and including that
  run, in play order, keeping the last 20 or fewer that ended no more than 30
  days before that run ended. A run that ended exactly 30 days before counts.
  Play order sorts by when a run ended, so the window is always a run of
  consecutive runs ending at the run itself.
- **Fresh** when the window holds at least 10 runs from at least 2 play
  sessions, or holds 20 runs. A window's sessions are the play sessions its
  runs belong to, split over every scenario's runs.
- **The value** is the window's median, with P25 and P75 (the middle 50%) and
  P10 and P90 (the middle 80%) interpolated between runs, the "inclusive"
  method: `statistics.quantiles(scores, n=4, method="inclusive")` and its
  `n=10` twin. An even count's median is the mean of the two middle scores.
- **Carried** when the window fails the rule and an earlier window passed: the
  value, both bands, the run and session counts, and the first and last dates
  are the last fresh window's.
- **Unknown** when no window has passed yet.
- **"As of"** applies to a carried value, and to a fresh value whose newest
  run ended more than 30 days before the time asked about. Its date is the
  date of the newest run behind the value.
- **Every run counts,** at every sensitivity and on every version of the
  scenario, warm-up runs included. A time-scored scenario needs no special
  case: a higher score is always a faster finish, so medians and percentiles
  order correctly, and nothing here is a percentage.
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
- **A stretch is faded where its points are carried.** The faded stretch
  starts at the last fresh point before it and ends at the first fresh point
  after it, so the line and the bands are continuous. A point is fresh or
  carried; the segment between a fresh point and a carried one is faded.
- **A fresh value is drawn at full strength however old its run is.** A run
  axis has no time to show passing; the age since the newest run is the
  Scenario Stats line's to say.

#### Score vs Time

- **Each value holds flat from its run to the next plotted run,** a step at
  each run. The line ends at the newest plotted run.
- **A hold fades 30 days after the newest run behind its value,** and a
  carried value's hold is faded throughout. The faded part ends where the
  next run's value begins, so the two meet.
- **Why the line ends at the newest run, and not now,** which the prototype
  did: held to now, the time axis stretches to today. A scenario last played
  in 2020 would then draw its runs at the left edge of six empty years at All
  time, where today's axis spans its runs. Ending at the newest run also
  keeps the figure free of the clock, so a chart left open draws nothing new
  as days pass, and the age since the newest run is the Scenario Stats
  line's, as on Score vs Run.

#### Score vs Sensitivity

No line and no bands, until that mode is redesigned: a rolling value has no
order along a sensitivity axis. The Middle 80% switch changes nothing there.

#### Traces, order and color

- **Up to six traces are added** after the run trace, the stars and the ring:
  the faded middle 80%, the faded middle 50%, the middle 80%, the middle 50%,
  the faded line, and the line, each only when it has a point to draw. The
  middle 80% traces exist only with the switch on.
- **They draw under the runs by `zorder` −1,** not by coming first. So
  `figure.data[0]` stays the run trace, `generated_point_color` stays right,
  and the tests that read the run trace by position don't change. Inside
  their layer, data order draws the line over the bands, and full strength
  over faded. The prototype put its traces first and set the run color in
  the theme step to make up for it; this does neither.
- **The legend** reads `Run data point`, `New PB`, `Typical score`,
  `Middle 50%`, `Middle 80%`, ordered by legend rank. A faded trace shares a
  legend group with its full-strength twin and has no entry of its own,
  unless the figure holds only its faded stretch. A click on an entry hides
  both, and as with the stars, the choice is not remembered.
- **Gray in both themes, with no color setting,** themed in the presentation
  step by trace name, as the ring is. Light: the line `#343a40`, the middle
  50% that gray at 14% opacity, the middle 80% at 7%. Dark: `#dee2e6` at the
  same strengths. The figure is built with the light colors, as it is with
  the ring's. A faded trace is drawn at 35% opacity. The line is 2.5 px wide.
- **No customization beyond the switch.** The
  [2026-08-20 points entry](../decision_log/2026/2026-08-20-run-points-get-a-size-preset-and-a-color-and-the-chart-stops-there.md)
  keeps everything but the run points' size and color fixed. The switch shows
  or hides a band, as the PB score switch shows a line; it does not style
  anything.

#### Hover

- **The run points' hover doesn't change.** The bands take no hover. The line
  has its own, with the lines in [Copy](#copy): the value, the middle 50%,
  the middle 80% while it is drawn, the runs and sessions behind the value
  with their dates, and `As of {date}` on a faded stretch.
- On Score vs Time a hold has a point at each end, both with its value's
  hover.

#### The zoom fit

**The line and the bands take part in the fit, as wanted.** The script already
fits every visible trace, so a refit keeps the band inside the view instead of
clipping it, and a legend-hidden band leaves the fit as today. The script's
comment, which names only the runs, the stars and the ring, is updated, and
so is the spec's sentence. One case is left: on Score vs Time a flat hold that
spans the whole zoomed window has no point inside it, so it doesn't widen the
fit; the line is a median of runs and almost always sits among them.

#### The Middle 80% switch

- **In the Overlays group, after PB score,** labelled `Middle 80%`, off to
  start, remembered in the browser like every Chart options control.
- **Its id is chosen once: `run-history-middle-80-overlay-switch`, unchecked
  by default.** Dash discards a stored value when a later visit draws a
  different default
  ([2026-09-19](../decision_log/2026/2026-09-19-a-query-parameter-selects-a-control-it-does-not-suspend-its-memory.md)),
  so neither may change.
- **It is an input of the chart rebuild,** as the PB score switch is, so the
  figure holds the middle 80% traces, and the hover its line, only while it
  is on.

### The Scenario Stats line

- **`Typical score:`** after Number of runs, in the card's label style, with
  the value and hover in [Copy](#copy).
- **It is worked out again when a run lands on the selected scenario, when
  the scenario changes, and on the page's 30-second tick,** so "as of"
  appears within 30 seconds of a value turning 30 days old. The time is the
  app's own clock. The tick costs at most the 3.9 ms measured above.
- **Its value is the chart's last point,** from the same function.

### Rounding

A shown value is rounded to the most decimal places any run in its window
scored, at most two, with a half rounding up, then formatted as a score is.
So a window of whole-number scores shows whole numbers (`2,140`, never
`2,140.5`), a scenario scored to one decimal shows one, and a tracking
scenario's six decimals show two. A median or a percentile is shown no more
precisely than the runs it comes from, as the roadmap's honesty principle
asks. Rounding is for display only: the definition keeps the exact values.

### How it is built

- **One pure module, `source/kovaaks/typical_score.py`,** takes a scenario's
  runs in play order and the play sessions, and returns the value after each
  run: its median, quartiles, P10 and P90, run and session counts, first and
  last dates, and whether it is fresh, carried, or unknown. A second function
  answers "as of" for a value at a time handed in. Nothing reads the run
  store inside it.
- **One copy of the run store per build.** The scenario's runs are taken from
  the same copy the sessions are split from, so a run that lands mid-build
  can't be in one and not the other. A plotted run that copy doesn't hold
  gets no point, and the rebuild its landing triggers draws it.
- **Nothing is stored.** The value is worked out from the runs whenever the
  chart or the stats line asks, as sessions are.
- **The prototype is read for behavior, not copied.** It is a patch over the
  app; the build writes the module and the traces afresh.
- **The cost is about 4 ms at worst per chart build,** on top of today's 4 to
  7 ms, and the figure about doubles in size at the default range.

### Beside Median and best

The two answer different questions and keep different words. Median and best,
in the run list, describe the runs under one row: a session's or a visit's,
all of them, with no window and no minimum, and they compare nothing. The
typical score is a rolling figure with a window and a minimum, worked out
after each run, and it is what later judgments read. A session row's median
and the typical score after that session's last run will often differ, and
that is correct. The labels keep them apart: `Median` never says typical, and
`Typical score` never says median. The glossary's Median and best entry
changes its pointer from "a later proposal" to the Typical score entry.

### Copy

Every string this proposal adds. They follow the nine copy rules in
[AGENTS.md](../../AGENTS.md#styling-conventions). The prototype's strings were
drafts and are redone here.

| Where | String | Why |
|---|---|---|
| Scenario Stats, label | `Typical score:` | A label as `Last played:` is. "Typical score" and not "Median score": the run list's Median and best already shows a plain median labelled `Median`, KovaaK's own leaderboard shows a third median (the median player's PB), and "median" alone reads as the median of every run. |
| Scenario Stats, fresh value | `{score}`, such as `1,179` | Rounded as [Rounding](#rounding) says, formatted as a score is. |
| Scenario Stats, "as of" value | `{score} · as of {date}`, such as `1,390 · as of Apr 12` or `2,140 · as of Mar 3, 2020` | A readout chain. The date is the short date the run list uses, with the year only when it isn't this year's, and has no age limit (TS5). |
| Scenario Stats, unknown value | `Too few recent runs · {n} of 10` while the window's runs come from two sessions or more, and `Too few recent runs · {n} of 20` while they come from one | Says why, then how far, as the 2026-08-01 plan's "Collecting data, 6/10 runs" did. The count is the window's runs against the number that would make the value fresh if play went on in the same way: 10 once two sessions are in the window, 20 while one sitting is. "Too few" and not the prototype's "Not enough", which wraps in the card's 300 px with a two-digit count. A runs-and-sessions readout (`6 runs · 1 session`) is truer to the rule in one form, and wraps too. |
| Scenario Stats, no scenario | `N/A` | As Position reads with no scenario selected. |
| Scenario Stats, no local runs | `No runs yet` | As the latest-run card's empty state says it. |
| Scenario Stats hover, fresh | `The median of {n} runs in {k} sessions, from {first} to {last}. The middle 50% scored {q1} to {q3}, and the middle 80% scored {p10} to {p90}.` | What the figure is, from what, and its spread. `on {date}` in place of `from {first} to {last}` when both are one date; `1 session` in the singular. |
| Scenario Stats hover, carried | The fresh text, then `It's your last known typical score. Since then, the 30 days up to your newest run hold {n} runs in {k} sessions. A new one needs 10 runs from at least 2 sessions, or 20 runs.` | Why it is "as of", and what would make it current, as a fact, not advice. `1 run`, `1 session` in the singular. |
| Scenario Stats hover, fresh but old | The fresh text, then `It's been more than 30 days since you played this scenario.` | Why it is "as of". |
| Scenario Stats hover, unknown | `A typical score needs 10 runs from at least 2 sessions, or 20 runs, within 30 days. The 30 days up to your newest run hold {n} runs in {k} sessions.` | The rule and the count behind the readout. |
| Chart legend | `Typical score`, `Middle 50%`, `Middle 80%` | Sentence case. "Middle 50%" and "Middle 80%" say what share of the runs each band holds; the percentile names go in the hover for the player who reads them. |
| Line hover, first line | `<b>Typical score</b>: {score}` | Bold labels, as the run points' hover. |
| Line hover, middle 50% | `<b>Middle 50% (P25 to P75)</b>: {q1} to {q3}` | The precise names, in the hover only. |
| Line hover, middle 80% | `<b>Middle 80% (P10 to P90)</b>: {p10} to {p90}` | Only while the switch is on. |
| Line hover, basis | `{n} runs in {k} sessions · {first} to {last}`, or `· {date}` when both are one date | A readout, no period. |
| Line hover, faded stretch | `As of {date}` | The newest run's date, as in Scenario Stats. |
| Chart options switch, label | `Middle 80%` | The legend's words, as the PB score switch takes its line's. |
| Chart options switch, help | `Shades the middle 80% of the runs behind your typical score, from the 10th to the 90th percentile, in a lighter shade than the middle 50%. **Score vs Sensitivity** draws no typical score.` | What it adds and where it doesn't apply. The mode is bold through `control_name()`, as the empty state bolds the modes. |

### Terms

Each entry is written as [docs/glossary.md](../glossary.md) would hold it,
under "Scores and notifications", beside PB. The PRs that ship this move them
in.

- **Typical score.** What a player's recent runs on a scenario usually score:
  the median of the scenario's last 20 runs or fewer from the 30 days up to a
  run. It is known once those runs number at least 10 from at least 2
  sessions, or fill all 20, and before that it is unknown, which is never
  read as weak. The rules are in the typical score's spec.
  - The roadmap and the decision log call it the typical run.
  - Not Median and best, which describe the runs under one row of the run
    list, with no window and no minimum.
  - Not the median KovaaK's leaderboard shows, which is the median player's
    PB.
  - In code: `typical_score`.
- **Middle 50%.** The range the middle half of the runs behind a typical
  score fell in: from the first quartile to the third, P25 to P75. Run
  History draws it as a band around the typical score.
  - On screen: `Middle 50%`, and `Middle 50% (P25 to P75)` in the chart's
    hover.
- **Middle 80%.** The range the middle 80% of the runs behind a typical score
  fell in: from the 10th percentile to the 90th, P10 to P90. Run History draws
  it while its Chart options switch is on.
  - On screen: `Middle 80%`, and `Middle 80% (P10 to P90)` in the chart's
    hover.
- **As of.** The state of a typical score that no longer rests on recent
  runs, shown with the date of the newest run behind it: the runs since it
  fell short of the minimum, or more than 30 days have passed with no run.
  - On screen: `as of {date}` in Scenario Stats, and a faded stretch on the
    chart.
  - In code: a value kept after its window fell short is `carried`.

Entry the same PRs correct: **Median and best** says "Not the typical run,
which is what a player's recent runs usually score. A later proposal defines
that." It becomes "Not the typical score, which is what a player's recent runs
usually score."

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

Statements in the specs that go untrue, which the same PRs rewrite:

- [run_history.md, The chart](../specs/run_history.md#the-chart): "No mode
  draws a summary line"; the zoom fit's "the run points inside the x window"
  and its note that the stars and the ring are the only other traces; and the
  list of what the Share chart figure holds, which gains the typical score's
  line and bands with their hover.
- [run_history.md, Chart options panel](../specs/run_history.md#chart-options-panel):
  "Three groups in order, holding seven controls" becomes eight, with
  `Middle 80%` off in Overlays.
- [run_history.md, Scenario Stats](../specs/run_history.md#scenario-stats):
  "under it, at one weight, are 'Last played:', 'Number of runs:', and
  'Position:'", and the card's height in the row, which a fourth line raises
  by 4 px.
- [run_history.md, Time-scored scenarios](../specs/run_history.md#time-scored-scenarios):
  the list of surfaces that order or place scores, unchanged on a
  time-scored scenario, gains the typical score.
- [glossary.md, Median and best](../glossary.md#median-and-best), as above.

Untouched: the 2026-10-14 Median and best entry, whose label rule this keeps,
and the 2026-08-20 points entry (see Traces, order and color).

### Alternatives rejected

Each was drawn in a prototype or measured, on the maintainer's stats.

- **Steps once per session** (v1). The same statistic sampled once per
  session; it drew a staircase that hid the runs' effect inside a session.
- **Session values joined** (v2). It mixes the per-session freeze into the
  line, which belongs to comparisons (TS3).
- **A carried stretch dotted, with no band** (v3 to v5). It read as gaps
  everywhere; faded keeps the band and the continuity (TS2).
- **7 days.** It loses fresh values that 14 and 30 days get right, for no
  accuracy gain.
- **14 days.** Equal to 30 in 2026; in the 2025 climb it held flat "as of"
  values under a rising player, where 30 days drew the climb (TS2).
- **60 days.** Like no limit after a return: in 35 of 55 returns its first
  value back held pre-break runs, a median of 16, and it missed the first
  session back by 8.1%.
- **No limit.** TS2's alternative.
- **A window the player chooses.** TS2.
- **The rolling maximum and minimum** as ceiling and floor. TS4.
- **The line drawn lighter until its window is full,** as Aimcurve draws its
  median. The minimum already does that job: below it there is no line, and
  above it the hover says how many runs and sessions are behind the value.
- **Two sessions only until a scenario is established,** the maintainer's own
  variant. TS1.
- **Runs at the current sensitivity, or on the current version, only.** TS1.
- **Holding the newest value until now on Score vs Time,** as the prototype
  did. [Score vs Time](#score-vs-time).
- **The traces first in the figure,** as the prototype put them. It moves
  the run trace off index 0, so the run points take another colorway entry
  unless their color is set, and every test that reads `figure.data[0]`
  changes. `zorder` draws them under the runs from the end of the list.

### Optional, beyond the rows

Flagged, not recommended, and left out unless a reviewer or the maintainer
wants it:

- **A switch for the typical score line itself,** beside PB score. It would
  let a player who finds the line noise turn it off for good. It costs a
  control, its copy and its remembered id, and it contradicts TS4's "always
  drawn". A click on the legend hides it for one figure.

## Delivery plan

Three implementation PRs. This is intent, not a contract: a boundary that
moves is noted in that PR's description.

1. **The definition.** `source/kovaaks/typical_score.py` with its pure
   functions and tests, a new capability spec, `docs/specs/typical_score.md`,
   and `architecture.md`. Nothing on screen, as the Sessions implementation
   shipped. Needs nothing.
2. **The chart.** The line, the bands and the faded stretches on Score vs Run
   and Score vs Time, their order, colors, legend and hover, the Middle 80%
   switch, the zoom fit's comment, and the Run History spec's chart and panel
   sections. Needs PR 1. It doesn't touch the top row, so it needn't wait for
   the cards work.
3. **The Scenario Stats line.** The line, its hover, its updates, and the
   spec's Scenario Stats section. Needs PR 1. Its order against the top row
   cards' PRs 2 and 3 is the maintainer's answer to the question under TS5;
   the recommendation is to hold neither, and whichever lands second rebases.

**Why three.** The definition is the contract later features read, and a PR
of its own keeps its review on the boundaries rather than on plotly. The
Scenario Stats line edits the module the cards' PRs 2 and 3 also edit, so it
ships on its own, to be ordered with them, while the chart need not wait. If the
maintainer prefers fewer PRs, PR 1 can fold into PR 2, at the cost of one
larger review.

The last of them to merge ships the proposal, by the
[Shipping a proposal](../../AGENTS.md#shipping-a-proposal-docs-definition-of-done)
checklist: a decision-log entry for each row, the notes in
[Decisions this changes](#decisions-this-changes), the specs, the glossary's
entries in [Terms](#terms), the user guide, the roadmap, `product.md`, and this
file deleted.

**Recommended:** `claude-opus-5-5`, at high for PRs 1 and 3 and at xhigh for
PR 2, which walks each state through two chart modes, the themes, the zoom fit
and the legend. The maintainer looks at PRs 2 and 3 in their own Firefox
before each merges.

### Fallbacks

- **PR 2 grows too large.** Ship Score vs Run first and Score vs Time after.

## Out of scope

Each with where it is tracked.

- **Comparisons and the session freeze:** "better than 15 of your last 20",
  a percentage against the typical score, and the value held fixed through a
  session for them. The vault Backlog's Post-Run Analysis items 3 and 6.
- **The score trend verdict.** The roadmap's Future list; its chart is the
  one this proposal draws.
- **Weakness by the typical run.** The roadmap's Future list.
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
  PB. Not tracked yet: the top row cards proposal doesn't include it, and the
  maintainer chose to carry that dependency.
- **Score vs Sensitivity's redesign,** which might draw a typical score per
  sensitivity. Recorded as lost in the 2026-10-12 chart entry.

## Testing

- **Unit, the definition,** through pure functions on hand-built runs and
  sessions, each state and boundary: 9 runs (unknown), 10 runs from one
  session (unknown), 10 from two (fresh), 19 in one sitting (unknown), 20 in
  one sitting (fresh); a run ended exactly 30 days before (counts) and one
  second more (doesn't); a break, then one run (carried, "as of" the old
  newest run's date), then back to fresh; known never turns unknown; an even
  count's median; the quartiles and deciles against hand-worked values;
  another scenario's runs joining two of this scenario's runs into one
  session; every sensitivity and version counted; same-second runs in play
  order; "as of" at exactly 30 days (not yet) and after (yes); rounding of
  whole, one-decimal and six-decimal scores, a half rounding up.
- **Unit, the chart's traces,** per mode on a hand-built history: which
  points are full strength and which faded, the joins at each end of a faded
  stretch, Score vs Time's holds, their fading at 30 days and their end at
  the newest run; `figure.data[0]` the run trace, `zorder`, legend groups and
  ranks; no traces with no known value, and none on Score vs Sensitivity; the
  middle 80% only with the switch on; the hover's lines.
- **Unit, the presentation step:** each theme's colors on the line and bands,
  and the run points' color unchanged.
- **Callbacks:** the switch rebuilds the chart; the stats line updates on a
  run on the scenario, on a scenario change, and when a value turns "as of"
  on the tick; its empty states.
- **Live, PRs 2 and 3,** in headless Edge at 2560 and 1920 px, light and
  dark: the line and bands under the runs, the faded stretches, the legend
  and its clicks, the hover, a zoom that refits to the bands, and the top
  row's height with the stats line. These cover what pure tests can't: draw
  order, theme colors, the zoom script, and layout. Then the maintainer's
  look in Firefox.
- **Performance,** measured again on the largest scenario in PR 2.
- **Docs:** `tests/test_docs.py` for links and summaries, and the gates in
  AGENTS.md.
