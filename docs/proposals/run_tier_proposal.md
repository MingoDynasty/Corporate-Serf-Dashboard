# Run History Says Where A Run Landed Among Your Last 20 Runs, In Place Of The Score Threshold

Status: Proposed
Date: 2026-11-05

## TL;DR

The latest-run card says how far a run was from the typical score as a
percentage, which can't say whether the run was unusual, because each
scenario's runs spread differently. Its badge and the run list's check judge
the run against a percentage of the PB, which passes 1 run in 10 on one
scenario and 9 in 10 on another. This proposal names the band of the
scenario's last 20 runs at session start that the run landed in, such as Top
10%, and lets the outer two bands take the badge and the check. The score
threshold, its chart line and its two controls retire, and the run's
percentage of its PB stays.

## Decisions needed

Six rows, RT1 to RT6. **Nothing is ratified.** RT1 to RT3 carry the
maintainer's leans from their own note on the idea. RT4 to RT6 carry none: the
note leaves the badge slot open ("Open: does it take the badge slot from the
PB-based Threshold badge?"), and retiring the threshold is the author's
recommendation. A lean is not a ruling. Reviewers may challenge any row, and
anything in [Design](#design), which is author-owned.

### RT1. A run's band is read against its scenario's last 20 runs at session start

Status: open. The maintainer's lean: "name the band of your last 20 runs (as
they stood at session start) that the run landed in, e.g. "Top 10% of your
last 20"."

The material consequence: on this history the top band fires on about 1 run in
3, not 1 in 10, and 3 runs in 10 get no band.

**Recommendation: a run's band is where its score sits among the runs behind
its scenario's typical score at session start, the same runs the card's
typical phrase and the run viewer use: up to 20 runs before the run's session,
known from 10 runs over 2 sessions, or 20 in one. The edges are those runs'
P10, P25, P75 and P90, the edges of the chart's two bands. Every run of a
session meets the same edges. A known window counts at any age, and one that
wasn't recent at session start carries the clock, as the typical phrase does
today. With no known window there is no band, never a low one.**

- **One yardstick, nothing new to compute.** The value at session start
  already holds P10 to P90 (`TypicalScore` in
  `source/kovaaks/typical_score.py`). The freeze is the one the 2026-10-25
  ruling kept "for later comparisons": run 1 and run 8 of a session meet the
  same edges, and no run meets edges it helped make.
- **How often it fires.** On the maintainer's Viscose S2 Medium runs since
  2026-09-13, 817 runs with a band: Top 10% on 31%, Bottom 10% on 7%.
  Lifetime, 4,535 runs: 35% and 8%. Two causes, both honest:
  - The player is improving, so the window lags. A window that moves with
    every run lowers the top band only from 31% to 28%. The lag is the trend,
    not the freeze.
  - Even with no trend at all, a P90 interpolated inside 20 runs is beaten by
    about 14% of new runs (17% for a window of 10; simulated). "Top 10%" says
    where the run sits in the window, not how often it happens.
- **Its rate follows the trend, not the spread.** Across the 18 regimen
  scenarios with 15 or more banded runs, the top band's rate runs from 17% to
  66% and follows how far the runs sat above the frozen typical (Spearman
  +0.81), not the spread (−0.17). The threshold's pass rate on the same
  scenarios runs from 15% to 90% and leans on the spread instead (−0.38 here;
  −0.64 on 28 scenarios in the 2026-11-05 research read). Two scenarios that
  aren't moving fire their top bands at the same rate, whatever their spreads.
- **No band: 31% of regimen runs** (369), all on scenarios with fewer than 10
  runs before the session or only one session. Lifetime, 635 of 866 scenarios
  never reach 10 runs. Unknown isn't weak, so these runs get no band and no
  badge. The threshold judged 361 of them.
- **Small windows behave.** A window of 10 to 19 runs held 28% of banded
  regimen runs; their rates are close to full windows' (Top 10% 27% to 29%
  against 32%; Bottom 10% 7% to 11% against 6%).
- **Old windows** held 14% of banded regimen runs and 35% lifetime. After time
  away the player tends to come back better than the old window: on old
  windows the top band fired on 50% of runs lifetime, against 28% on recent
  ones. The clock says why.
- **The chart's bands are not the card's.** The chart draws the bands after
  each run, the run included. A third of Top 10% runs are not above the drawn
  Middle 80% band at their own point (in the regimen 67% are above it,
  lifetime 60%). It is the drift the 2026-10-25 ruling accepted between the
  phrase and the Typical score card, now visible on the chart; the hover names
  the runs the card used.

### RT2. The comparison line names the band in place of the typical percentage

Status: open. The maintainer's lean: "Percentile tier on the latest-run card,
in place of "3.6% above typical" … The percentage can't say that without
knowing each scenario's spread."

The material consequence: the line no longer says how far from typical a run
was; that figure moves into the hover.

**Recommendation: on a run that isn't a new PB, with a known window, the line
reads `{band} of your last {N} runs at session start · {pct}% of PB`. Five
bands: `Top 10%`, `Top 25%`, `Middle 50%`, `Bottom 25%`, `Bottom 10%`. The
hover gives the typical score, the run's percentage from it, and both bands'
edges. A new PB keeps its gain alone, as today.**

- **The percentage hides the spread.** 3.6% above typical is Top 25% on VT
  Controlsphere Viscose and Top 10% on beanTS, whose middle half is about a
  third as wide (2.5% of its typical score against 7.0%).
- **The basis is on screen.** The 2026-10-25 ruling named its basis because
  "the at-a-glance reading must not depend on a hover". `at session start` is
  that ruling's own wording, and `last {N}` counts the window, 10 to 20 runs.
- **The words are the chart's.** Middle 50% is the glossary's and the legend's
  name for the darker band, and Top 10% and Bottom 10% are the runs outside
  the Middle 80% band.
- **Nothing is lost.** The hover keeps the typical value and the percentage,
  worded and computed as the ratified phrase is, by pace where that phrase
  used pace.
- **It fits.** The longest form,
  `Bottom 25% of your last 20 runs at session start · 99.9% of PB pace`, is 67
  characters. The 2026-10-25 phrase's longest is 62 and measured 361 px of the
  card's 474, so by that measure this is about 390 px.

### RT3. Only the outer bands are highlighted

Status: open. The maintainer's lean: "Highlight the outer tiers (P10/P90, 1
run in 5) by default; P25/P75 would flag half of all runs."

The material consequence: with New PB first, the outer-band badges land on
about 1 run in 5.7, and a third of Bottom 10% runs are a visit's first run.

**Recommendation: Top 10% and Bottom 10% are highlighted (RT4 says where). The
three middle bands are named on the line only. No setting chooses the bands.**

- **The estimates in the maintainer's note hold, counted as the card would
  show them.** Of all 1,186 regimen runs: New PB 15%, Top 10% 13% (a new PB is
  always above the window, so it shows New PB instead), Bottom 10% 5%, no
  badge 67%. Quartile highlights would put a badge on 50% of runs, New PB
  included, the note's "half".
- **Today's badge** lands on all but 3 of those runs: New PB 15%, Threshold
  passed 31%, Below threshold 53%.
- **Warm-ups.** Bottom 10% fired on 15% of visits' first runs against about 5%
  of later runs, so 21 of the 55 Bottom 10% runs (38%) were a visit's first
  run. Marking warm-ups is separate work ([Out of scope](#out-of-scope)).
- **No setting.** "By default" is read as the default the app ships. A setting
  is a control nobody has asked for, and it would make the badge mean
  different things in different browsers, which the threshold's percentage
  already did.

### RT4. The highlight takes the badge slot, after New PB

Status: open. No lean: the maintainer's note asks "does it take the badge slot
from the PB-based Threshold badge?"

The material consequence: Threshold passed and Below threshold leave the card
and the run viewer, and a run with no band shows no badge where the threshold
used to judge it (30% of regimen runs).

**Recommendation: one badge beside the score: `New PB` when the run is one,
else `Top 10%` in the threshold's green or `Bottom 10%` in its gray, else
none.**

- **One verdict per run,** as the 2026-10-12 rule has it. Two badges would
  disagree: in the regimen, 30 non-PB runs in the Top 10% read Below
  threshold, and 45 runs in the Middle 50% read Threshold passed.
- **The badge is the glance and the line is the reading,** as `New PB` sits
  over `Up 2.1% on your previous best of 3,200`, so `Top 10%` sits over the
  line that names its basis.
- **A verdict, not advice.** It says where the run landed among the player's
  own runs, and nothing about what to do, which the 2026-10-04 principles
  allow.
- **On file:** the 2026-11-05 research read recommends the same: "The tier
  takes it; New PB keeps precedence."

### RT5. The run list's marks follow the badge

Status: open. No lean.

The material consequence: the check means "Top 10% of the runs before its
session", a new mark flags Bottom 10%, and marks stop changing with a
percentage or a browser.

**Recommendation: a check on a Top 10% run, a gray down arrow on a Bottom 10%
run, and the star as today. Every row's marks cell names its band on hover. A
row with no band is blank, and its hover says why.**

- **The check is the badge's twin** by the 2026-10-12 design, so it follows
  RT4 to both outer bands.
- **Both, not the top only** (the research read's draft marked the top only).
  The maintainer's lean highlights both, and the list is where a past bad run
  is found to open in the run viewer, where "what went wrong at the bottom"
  gets its answer.
- **Marks stop moving.** A window at session start depends only on the runs
  before the session, so a mark is fixed once its session is played. The
  threshold's checks moved with the percentage, and differed from browser to
  browser.
- **The 30 px column holds them.** A new PB is always above its window, so the
  star comes with a check when the run has a band, and a down arrow never
  comes with either.
- **Its cost:** a permanent mark on bad runs, 7% of banded regimen runs and 8%
  lifetime.

### RT6. Score threshold retires; `% of PB` stays

Status: open. No lean. The maintainer's backlog asks: "Challenge the idea of
"Score Threshold". What is the intention of this? What do we expect the user
to do with this information?"

The material consequence: a player can no longer set a bar of their own or
turn the marks off, and Chart options loses its Score Threshold group.

**Recommendation: the chart's "Score threshold" line, the Score threshold
overlay switch and the Score threshold percentage, and the verdict they drive
all retire. The card's `{pct}% of PB`, the run viewer's and its 99.9% cap
stay; the cap that held a miss under its goal goes with the goal. A value a
browser stored is left behind, unused, as the 2026-10-13 switches' were.**

- **Its purpose was retired; its mechanism was not.** The threshold is a
  method's "advance once you hit it" rule. Its "Ready to move on." left on
  2026-10-04 as advice, and no entry records another purpose.
- **It means something different on every scenario.** At 95%, the regimen's
  pass rate over each scenario's last 20 runs ran from 10% on VT Controlsphere
  Viscose to 95% on StaticSwitchingVox Small, following the spread. Half its
  Below threshold verdicts (228 of 470) sat on runs above typical.
- **The band does its job, calibrated.** RT1 to RT5 put a per-run verdict
  where the threshold's was, and a scenario that isn't moving fires it at the
  same rate as any other.
- **Simpler.** Two controls, one line family and one judging rule go; the band
  reads edges the app already computes.
- **What would change it** (none known today): the maintainer reads the line
  as a chase target when no rank line is near (then keep a line the player
  sets, with no verdict); the 2026-11-10 regimen review keeps its 95% good-run
  bar and wants the app to show it (then keep the threshold opt-in, empty by
  default); a reason from 2025 nobody wrote down.
- **On file:** the 2026-11-05 research read recommends this: "Retire Score
  Threshold as a percent-of-PB verdict and let the percentile tier take its
  place".

## Problem

### What Run History shows today

- **The latest-run card**
  ([spec](../specs/run_history.md#the-latest-run-card)): `Latest run · {age}`;
  the score with one badge, New PB, else Threshold passed or Below threshold
  for a judged run; `{pct}% above typical at session start · {pct}% of PB`;
  the session line; cm/360 and accuracy.
- **The run list's marks**
  ([spec](../specs/run_history.md#marks-the-check-and-the-star)): a check for
  a run that met the threshold, a star for a new PB.
- **The chart:** a dashed `Score threshold ({value})` line at the percentage
  of the current PB, and the typical score with its Middle 50% and Middle 80%
  bands, drawn after each run.
- **Chart options:** the Score Threshold group, a switch and a percentage, 95
  by default.

### Why now

The typical phrase shipped on 2026-10-26. A run of 3,133 on VT Controlsphere
Viscose reads `3.6% above typical at session start · 85.8% of PB` beside a
gray Below threshold. Neither part says whether the run was unusual for this
scenario: it sat in the window's top quarter, under its P90. The maintainer's
note asks for that answer, and for the extreme run to be the cue: "what went
right at the top, what went wrong at the bottom".

### Verified facts

- `typical_score_at_session_start` returns the window as a `TypicalScore` with
  `p10`, `p25`, `p75` and `p90`, computed with
  `statistics.quantiles(method="inclusive")`, the chart bands' rule.
- `score_line` in `source/components/latest_run_card.py` builds the card's and
  the run viewer's score line from one call, so both surfaces change together.
- `judge_run` and `shown_percentage` in `source/components/score_threshold.py`
  are the check's and the card's only judging code; the toast stopped judging
  on 2026-10-13.
- A new PB beats every earlier run, so its score is above its window's P90
  whenever the window is known: every one of the 532 banded new PBs in the
  history is in the top band.
- Open PR #462 (K8, 2026-11-05) gives the percentage a maximum of 200 and a
  strict clamp. It decides nothing about what the threshold is for.

### What the maintainer's runs say

9,284 runs through 2026-10-29, 866 scenarios; "regimen" is the Viscose S2
Medium runs since 2026-09-13 (1,186 runs). Sessions split as the app splits
them. Bands by score, with strict outer edges.

| # | Measure | Regimen | Lifetime |
|---|---|---|---|
| 1 | Runs with a band | 817 (69%) | 4,535 (49%) |
| 2 | Top 10% / Top 25% / Middle 50% | 31% / 18% / 37% | 35% / 17% / 33% |
| 3 | Bottom 25% / Bottom 10% | 7% / 7% | 7% / 8% |
| 4 | Badge as RT4 shows it: New PB / Top 10% / Bottom 10% / none | 15% / 13% / 5% / 67% | 22% / 12% / 4% / 62% |
| 5 | Today's badge: New PB / passed / below / none | 15% / 31% / 53% / 0% | n/a |
| 6 | Top 10% runs above the chart's drawn band at their point | 67% | 60% |
| 7 | Bottom 10% runs that are a visit's first run | 38% | 24% |

Expected rates with no trend at all (simulated, any distribution): Top 10% and
Bottom 10% each 13.9% for a 20-run window, 15.0% at 15 runs, 17.2% at 10.

### Not checked

- **The app's own functions** were not run; the windows are a
  re-implementation (`viscose.py`'s session split, which is the app's rule,
  with play order by end time only).
- **Copy lengths in pixels.** RT2's 67 characters are compared by count with
  the 2026-10-25 measurement.
- **The All scenarios view's cost** of building every listed scenario's
  windows for its marks.
- **A screen reader** on the badge, the line and the marks' hovers.
- **One player, one regimen** that set 180 PBs in seven weeks: band rates on a
  flat player would sit nearer the 14% expectation.

## Design

### What the player sees

VT Controlsphere Viscose, from the maintainer's runs; window of 20 runs at
session start: typical 3,025, Middle 50% 2,904 to 3,116, Middle 80% 2,851 to
3,207 (2026-10-16), and on 2026-10-04 typical 2,888 and P90 3,118.

| Run | Today | Proposed |
|---|---|---|
| 2026-10-16, run 7, 3,133 | [Below threshold] `3.6% above typical at session start · 85.8% of PB` | no badge, `Top 25% of your last 20 runs at session start · 85.8% of PB` |
| 2026-10-16, run 5, 2,665 | [Below threshold] `11.9% below typical at session start · 73.0% of PB` | [Bottom 10%] `Bottom 10% of your last 20 runs at session start · 73.0% of PB` |
| 2026-10-04, run 7, 3,181 | [Below threshold] `10.2% above typical at session start · 94.8% of PB` | [Top 10%] `Top 10% of your last 20 runs at session start · 94.8% of PB` |
| cloverRawControl Viscose 50cm, 2026-10-29, 9,969, old window of 15 | [Below threshold] `10.7% above typical at session start` + clock ` · 93.7% of PB` | [Top 10%] `Top 10% of your last 15 runs at session start` + clock ` · 93.7% of PB` |
| A new PB | [New PB] `Up {pct}% on your previous best of {previous}` | unchanged |
| A scenario's third session, 8 runs before it | [Threshold passed] `{pct}% of PB` | no badge, `{pct}% of PB` |

### The band

- **Edges:** the window's P10, P25, P75 and P90, unrounded, as `TypicalScore`
  holds them.
- **Bands:** above P90, Top 10%; above P75 up to P90, Top 25%; P25 to P75,
  Middle 50%; P10 up to below P25, Bottom 25%; below P10, Bottom 10%. A score
  on an edge belongs to the inner band, as a point on a drawn band's edge is
  on the band. Scores compare as decimals, as the threshold's did.
- **By score, always.** On a time-scored version the order of times is the
  order of scores, so the band is the same by pace; the window counts every
  version by score anyway (TS1). Only the hover's percentage uses pace, under
  the 2026-10-25 rule.
- **Unknown:** no run before the session, or a window under the minimum: no
  band, no badge, no mark. Never read as low.
- **Old:** judged at session start by the typical score's recency rule; the
  clock and `, Not recent` follow the band phrase, as they follow the typical
  phrase today, and the list's hover says so.
- **In code:** a pure `band_at_session_start(score, typical)` beside
  `typical_score_at_session_start`, returning a `RunBand` or `None`.
  `score_line` calls it, so the card and the run viewer agree.

### The latest-run card

- **Badge:** `New PB` (yellow) when the run is one; else `Top 10%` (green) or
  `Bottom 10%` (gray); else none. Drawn as today's badges, with today's
  contrast.
- **Comparison line,** not a new PB: the band phrase, then ` · `, then the PB
  part, `{pct}% of PB` or `of PB pace`. With no band the line is the PB part
  alone; with neither, absent. A new PB: its gain alone, as today.
- **The band phrase's hover,** by mouse and keyboard as today's phrase's: a
  first line naming the window, the typical score with the run's percentage
  from it, and both bands' edges in the scenario table's format; on an old
  window, today's second paragraph, reworded for runs.
- **The card is rewritten** on the triggers it has today, less the
  percentage's change.

### The run list's marks

- A check on a Top 10% run, a gray down arrow on a Bottom 10% run, the star
  unchanged. A new PB with a band carries the check and the star.
- Every row's marks cell has a hover and accessible text naming its band, the
  window's size and its age; a row with no band says why. The column stays 30
  px.
- Marks are computed per run from its own session's window, the same build the
  chart uses, and change only when a stats file lands older than a played
  session.

### The run viewer

Its score line is `score_line`'s, so it shows the band, the badge and the
hover with no change of its own. Its reference line already names the same
runs ("Typical comes from your {N} runs before this session").

### The chart and Chart options

- The `Score threshold ({value})` line goes; the overlay families are the PB
  line and the rank lines.
- Chart options: the Score Threshold group and its two controls go, leaving
  Overlays and Run Data Points, nine controls. The stored values stay behind,
  unused.
- The Middle 50% and Middle 80% bands are unchanged: they still follow every
  run.

### What retires in code

`judge_run`, `ThresholdVerdict`, `Unjudged`,
`normalize_score_threshold_percentage` and `score_threshold_line` in
`score_threshold.py`; `shown_percentage`'s miss cap (the 99.9% cap moves with
the PB comparison); `CardBadge.THRESHOLD_PASSED` and `BELOW_THRESHOLD`; the
threshold inputs of the card, list and chart callbacks; the two controls and
their help text in `chart_options.py`.

### Copy

Every string this proposal adds or edits. Rules 1 to 9 apply. The word
"percentile" stays off the screen, as the maintainer leans ("Don't call it
"percentile" on screen, since that word already means leaderboard placement"):
the PB card's leaderboard line reads `{n}% percentile`.

| Where | String |
|---|---|
| Bands | `Top 10%`, `Top 25%`, `Middle 50%`, `Bottom 25%`, `Bottom 10%` |
| Comparison line | `{band} of your last {N} runs at session start · {pct}% of PB`, or `· {pct}% of PB pace` |
| Band hover, first line | `Measured against your last {N} runs when this run's session began.` |
| Band hover, typical | `Typical score: {typical} · {pct}% above typical`, with `below`, `Matches typical`, or by pace `{pct}% faster than typical` and `slower` |
| Band hover, edges | `Middle 50%: {p25} to {p75}` and `Middle 80%: {p10} to {p90}` |
| Band hover, old window | `Fewer than 10 of those runs were from the 30 days before the session began, so they may have been out of date.` |
| Badges | `Top 10%`, `Bottom 10%`; `New PB` unchanged |
| List mark hover and accessible text | `{band} of your last {N} runs at session start`, with `, which may have been out of date` on an old window |
| List hover, no band | `There was no typical score yet when this run's session began.` |

Retired strings: `Threshold passed`, `Below threshold`, the three "Not
judged." hovers, `Score threshold ({value})`, the Score threshold overlay
switch, the Score threshold percentage and its help text.

### Terms

For the glossary, under Scores and notifications, beside Typical at session
start.

**Band at session start.** Where a run's score sits among the runs behind its
scenario's typical score when the run's session began: above their P90, above
P75, between P25 and P75, below P25, or below P10. Unknown while that typical
score is unknown.
- On screen: `Top 10%`, `Top 25%`, `Middle 50%`, `Bottom 25%`, `Bottom 10%`,
  with `of your last {N} runs at session start`; the outer two as the
  latest-run card's badge and as the run list's check and down arrow.
- In code: `RunBand`, `band_at_session_start`.
- Not a leaderboard percentile, not the retired Top N placement, and not the
  chart's bands, which follow every run.

The glossary's Score threshold entry is removed.

### Decisions this changes

- **[2026-10-25, typical at session
  start](../decision_log/2026/2026-10-25-the-latest-run-card-measures-the-run-against-the-typical-score-at-session-start.md):**
  the phrase moves from the line to the band's hover; its value, basis,
  evidence bar, clock and pace rule stand. Superseded in part.
- **[2026-10-12, a past run's
  check](../decision_log/2026/2026-10-12-a-past-runs-check-is-judged-against-the-pb-it-was-chasing-under-its-own-version.md):**
  the check and the badge mark bands, not a threshold; the "Not judged"
  reasons and re-marking on a percentage change go. The one-badge rule, the
  star, the card being worked out from the run store, and a past run's pace
  basis for `% of PB` stand. Superseded in part.
- **[2026-10-13, Top N and the verdict
  switch](../decision_log/2026/2026-10-13-top-n-placement-and-the-score-threshold-verdict-switch-are-retired.md):**
  no setting turns marks off any more. Its "Moving placement to the latest-run
  card was considered and not taken" was about a run's place among all runs at
  its sensitivity against an unexplained 5; the band is a place among the
  typical's named window. Superseded in part.
- **2026-07-08, judged against the previous PB:** superseded; the PB-chased
  rule lives on in `% of PB`.
- **2026-10-05, pace:** the threshold line's pace form leaves its list of
  surfaces. Gains a note.
- **The roadmap's "State verdicts, not advice"** names the score threshold as
  its example of a bar the player set; the example becomes the band. The
  2026-10-04 entry itself stands.
- Applied, not changed: [2026-10-18, two
  bands](../decision_log/2026/2026-10-18-two-percentile-bands-show-the-typical-scores-spread.md)
  (its edges), 2026-10-14's rule on a card's lines, and 2026-10-22's old-value
  clock.

### Alternatives rejected

- **The window just before the run, after the run, or every run ever** (RT1).
  Before the run moves after every run and gives a session's runs different
  yardsticks, for 3 points less top band; after the run includes the run
  itself; every run ever measures against years-old play.
- **A count, `Better than 18 of your last 20`.** Exact, but a new number per
  run where a band repeats the chart's names, it needs a tie rule, and it
  reads as the ranking the 2026-10-13 entry retired.
- **The percentage and the band both on the line.** Three parts don't fit, and
  the band answers what the percentage was for.
- **Quartile highlights, or a setting for them** (RT3).
- **Two badges, or the band badge only while no threshold is set** (RT4).
- **A threshold as a percentage of the typical score.** The same fixed bar
  moved down: +5% is about 2 standard deviations on beanTS and half of one on
  CatClick Medium (the research read).
- **The threshold kept, opt-in and empty by default.** Two controls and a
  verdict family for a use nobody has named, and a second badge to rank
  against the band (RT6).
- **A sixth band, `Best of your last 20`.** New PB already takes most such
  runs, and it adds a third top word.
- **Red for Bottom 10%.** It reads as an alarm; gray is today's color for a
  miss.

## Out of scope

- **Warm-up runs.** A visit's first run is 38% of Bottom 10% runs. Marking
  warm-ups is an item of its own in the maintainer's note, tracked outside
  this proposal. Revisit if the first-run share keeps the bottom badge from
  being a useful cue.
- **The band on the chart:** marking banded runs, or drawing session-start
  bands. Revisit if the chart's band and the card's disagreeing (a third of
  Top 10% runs) confuses in use.
- **The band anywhere else:** the run toast, the scenario table, a session's
  results count (the session-results note's "runs past the Score Threshold").
- **A consistency figure, a PB gap in spreads, Typical Accuracy:** separate
  notes, separate proposals.
- **Next Rank, the PB card, the PB line, the rank lines, the New PB star and
  celebration:** unchanged. The PB stays the achievement.
- **Any stop or "move on" wording.**

## Delivery plan

Stated intent, not a contract; a PR that moves a boundary says so in its
description.

1. **The band, pure.** `RunBand` and `band_at_session_start`, with tests on
   edges, ties, windows of 10 to 20, unknown and old windows. No UI.
2. **Every surface, and the retirement.** The card's line, badge and hover,
   the run viewer by way of `score_line`, the list's marks and hovers, the
   chart line and Chart options group removed, the judging code deleted.
   Specs, glossary, decision log, roadmap example, README Features line, user
   guide and product inventory; deletes this proposal. One PR so no build
   shows a band badge beside a threshold check.

PR #462 (K8) bounds the percentage this retires. Whichever merges second
rebases; if #462 merges first, PR 2 removes its bound with the field. Open PR
#469 adds a Run History spec statement that names the Score threshold among
the overlay lines the score axis's autorange holds; if it merges first, PR 2
drops the threshold from that statement too.

## Testing

- **PR 1, unit:** each band at, above and below every edge; a window of 10 and
  of 20; integer scores with ties on an edge; unknown (first session, too few
  runs, one session of 15); a new PB always Top 10%; decimals at the edge.
- **PR 2, unit:** the line's forms (band and PB part, PB part alone, new PB
  gain); the badge's precedence; the hover's lines, by score and by pace, old
  and recent; the list's marks and hovers, the 30 px column holding a check
  and a star; marks unchanged after a later run in another session; Chart
  options without the group; a stored percentage ignored.
- **Browser** (headless Edge, then the maintainer's Firefox), on the states
  above, both themes, at 3840, 2560, 1920 and 1536 px: the longest line on one
  line in the wide card, the narrow card's floor, the badge's contrast.
- **Screen reader** (NVDA): the badge, the line with `, Not recent`, and each
  mark's accessible text.
- **Gates:** pytest, ruff format and lint, mypy, compileall, as AGENTS.md
  lists.
