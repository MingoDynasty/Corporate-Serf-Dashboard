# Run History Says Where A Run Landed Among Your Last 20 Runs, In Place Of The Score Threshold's Verdict

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
threshold stops judging runs, and its chart line stays as a target the player
sets, off until they turn it on. The run's percentage of its PB stays.

## Decisions needed

Six rows, RT1 to RT6. **Nothing is ratified.** RT1 to RT3 carry the
maintainer's leans from their own note on the idea. The note leaves the badge
slot open ("Open: does it take the badge slot from the PB-based Threshold
badge?"), and retiring the threshold's verdict is the author's
recommendation. At the direction checkpoint on 2026-11-06 the maintainer
answered for RT2's words, RT5's down arrow and RT6's line; those answers are
leans too, quoted in each row. RT4 carries none. A lean is not a ruling.
Reviewers may challenge any row, and anything in [Design](#design), which is
author-owned.

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
    up to 14.3% of new runs whatever the scores' distribution, and by at least
    9.5% when no two scores tie; uniform scores give 13.8%. Ties lower it, to
    none on a scenario whose runs all score the same. "Top 10%" says where the
    run sits in the window, not how often it happens.
- **Its rate follows the trend, not the spread.** Across the 18 regimen
  scenarios with 15 or more banded runs, the top band's rate runs from 17% to
  66% and follows how far the runs sat above the frozen typical (Spearman
  +0.81), not the spread (−0.17). The threshold's pass rate on the same
  scenarios runs from 15% to 90% and leans on the spread instead (−0.38 here;
  −0.64 on 28 scenarios in the 2026-11-05 research read). Two scenarios that
  aren't moving, and whose runs differ only in level and spread, fire their
  top bands at exactly the same rate; any two whose scores don't tie stay
  between 9.5% and 14.3% at 20 runs. The rates describe past runs; they
  promise nothing about the next.
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
  ones. The clock says why, on the card and in the list (RT5).
- **The chart's bands are not the card's.** The chart draws the bands after
  each run, the run included. A third of Top 10% runs are not above the drawn
  Middle 80% band at their own point (in the regimen 67% are above it,
  lifetime 60%). It is the drift the 2026-10-25 ruling accepted between the
  phrase and the Typical score card, now visible on the chart; the hover names
  the runs the card used.

### RT2. The comparison line names the band in place of the typical percentage

Status: open. The maintainer's lean: "Percentile tier on the latest-run card,
in place of "3.6% above typical" … The percentage can't say that without
knowing each scenario's spread." At the direction checkpoint (2026-11-06, in
chat), of the line as first filed, `{band} of your last {N} runs at session
start`: "I feel this is really wordy. Simply say "typical" instead with a
hover over to explain exactly what "typical" means (last 20 runs)." Of the
wordings then offered, they chose the author's, `{band} vs typical at session
start`: "Let's go with your recommended wording."

The material consequence: the line no longer says how far from typical a run
was; that figure moves into the hover, and so does the window's size.

**Recommendation: on a run that isn't a new PB, with a known window, the line
reads `{band} vs typical at session start · {pct}% of PB`. Five bands:
`Top 10%`, `Top 25%`, `Middle 50%`, `Bottom 25%`, `Bottom 10%`. The hover
says which runs typical comes from, then gives the typical score, the run's
percentage from it, and both bands' edges. A new PB keeps its gain alone, as
today.**

- **The percentage hides the spread.** 3.6% above typical is Top 25% on VT
  Controlsphere Viscose and Top 10% on beanTS, whose middle half is about a
  third as wide (2.5% of its typical score against 7.0%).
- **The basis stays on screen, in fewer words.** The 2026-10-25 ruling named
  its basis because "the at-a-glance reading must not depend on a hover", and
  the Typical score card beside the line shows the value after the newest
  run, which can differ. `vs typical at session start` keeps that ruling's own
  words. The window's size, 10 to 20 runs, moves into the hover.
- **The words are the chart's.** Middle 50% is the glossary's and the legend's
  name for the darker band, and Top 10% and Bottom 10% are the runs outside
  the Middle 80% band.
- **Nothing is lost.** The hover keeps the typical value and the percentage,
  worded and computed as the ratified phrase is, by pace where that phrase
  used pace.
- **It fits.** The longest form,
  `Bottom 25% vs typical at session start · 99.9% of PB pace`, is 57
  characters, under the 2026-10-25 phrase's longest, 62, which measured
  361 px. The card has been 480 px wide since 2026-10-29, 454 px of text.

### RT3. Only the outer bands are highlighted

Status: open. The maintainer's lean: "Highlight the outer tiers (P10/P90, 1
run in 5) by default; P25/P75 would flag half of all runs."

The material consequence: with New PB first, the outer-band badges land on
about 1 run in 5.7, and two in five Bottom 10% runs are a visit's first run.

**Recommendation: Top 10% and Bottom 10% are highlighted (RT4 says where). The
three middle bands are named on the line only. No setting chooses the bands.**

- **The estimates in the maintainer's note hold, counted as the card would
  show them.** Of all 1,186 regimen runs: New PB 15%, Top 10% 13% (a new PB is
  always above the window, so it shows New PB instead), Bottom 10% 5%, no
  badge 67%. Quartile highlights would put a badge on 50% of runs, New PB
  included, the note's "half".
- **Today's badge** lands on all but 3 of those runs: New PB 15%, Threshold
  passed 31%, Below threshold 53%.
- **Warm-ups.** Bottom 10% fired on 14% of visits' first runs against 5% of
  later runs, so 22 of the 55 Bottom 10% runs (40%) were a visit's first run.
  A first run is not always a warm-up, and marking warm-ups is separate work
  ([Out of scope](#out-of-scope)).
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

Status: open. The maintainer's lean, at the direction checkpoint (2026-11-06,
in chat), on a mark for Bottom 10% runs: "I think it's a good idea. If not a
down arrow then some sort of icon. The idea is that bottom 10% runs could be
good candidates for VOD review, just like top 10% runs are."

The material consequence: the check means "Top 10% of the runs before its
session", a new mark flags Bottom 10%, a clock marks either one read from an
old window, and marks stop changing with a percentage or a browser.

**Recommendation: a check on a Top 10% run, a gray down arrow on a Bottom 10%
run, and the star as today. A check or down arrow read from a window that
wasn't recent at session start carries the clock, as the card's line does; the
star never does. Every row's marks cell names its band and the window's age on
hover and to a screen reader. A row with no band is blank, and its hover says
why.**

- **The check is the badge's twin** by the 2026-10-12 design, so it follows
  RT4 to both outer bands.
- **Both, not the top only** (the research read's draft marked the top only).
  The maintainer's leans highlight both, and the list is where a past bad run
  is found to open in the run viewer, where "what went wrong at the bottom"
  gets its answer: a Bottom 10% run is a candidate for VOD review, as a Top
  10% run is. The down arrow is the author's choice of icon.
- **An old window shows while scanning.** 60 of the 307 outer-band marks in
  the regimen, and 830 of 1,971 lifetime, are read from a window that was old
  at session start, 285 of them beside a star. Without the clock they look
  like marks against recent play. The 2026-10-22 evidence bar admits an old
  value only with its qualification reaching every reader, and the list is
  where runs are scanned for one to open. The clock qualifies the band, not
  the PB, which is an achievement at any age.
- **Marks stop moving.** A window at session start depends only on the runs
  before the session, so a mark is fixed once its session is played, while
  those runs stay as they are: a stats file that lands older than the session,
  or one gone at the next start, can move it. The threshold's checks moved
  with the percentage, and differed from browser to browser.
- **The column fits its widest cell.** A new PB is always above its window, so
  the star comes with a check when the run has a band, and a down arrow never
  comes with either. The widest cell is a check, a clock and a star; today's
  30 px holds two marks, so the column takes the width the browser check
  measures for three, and stays fixed.
- **Its cost:** a permanent mark on bad runs, 7% of banded regimen runs and 8%
  lifetime, and a clock on 20% of regimen marks and 42% lifetime.

### RT6. The score threshold stops judging runs; its line stays as a target the player sets

Status: open. The maintainer's backlog asks: "Challenge the idea of "Score
Threshold". What is the intention of this? What do we expect the user to do
with this information?" At the direction checkpoint (2026-11-06, in chat),
asked whether they read the line as a target: "I don't use it that much, but
I could imagine some users using it." Asked whether the 2026-11-10 regimen
review keeps its 95%-of-PB good-run bar: "For now yes. But afterward, I'm not
sure yet." Both are leans, not rulings.

The material consequence: nothing the player sets changes a badge or a mark,
and a new player has no threshold line until they turn it on. A browser that
showed the line only by default shows it off; where the player turned the
switch on, it stays on.

**Recommendation: the threshold's verdict retires: Threshold passed, Below
threshold, the check it drove and the rule that judged them. The band takes
the badge and the check (RT4, RT5). The chart's `Score threshold ({value})`
line stays, with its two controls, as a target the player sets that judges no
run: its overlay switch starts off, and the percentage keeps its default, 95.
The card's `{pct}% of PB`, the run viewer's and their 99.9% cap stay; the cap
that held a miss under its goal goes with the verdict.**

- **A verdict and a target are two things.** The 2026-10-04 principles count
  whether a run met a bar the player set as a verdict the app may state, with
  the score threshold as their example. The verdict retires anyway: the badge
  and the check hold one verdict per run (RT4, RT5), and the band does that
  job better (below). That example is superseded in part ([Decisions this
  changes](#decisions-this-changes)). The line stays as a target the player
  chooses, which the app already draws from two controls it already has. The
  evidence below condemns 95% as the app's own good-run verdict, not a bar a
  player chooses: a target that is easy on one scenario and hard on another
  can be what the player meant. Its "Ready to move on." left on 2026-10-04 as
  advice; the line never gave any.
- **As a verdict it means something different on every scenario.** At 95%, the
  regimen's pass rate over each scenario's last 20 runs ran from 10% on VT
  Controlsphere Viscose to 95% on StaticSwitchingVox Small, following the
  spread. Half its Below threshold verdicts (228 of 470) sat on runs above
  typical.
- **The band does the verdict's job.** RT1 to RT5 put a per-run verdict where
  the threshold's was, and on a scenario that isn't moving its rate is held
  in a narrow range by the window, not set by the spread (RT1).
- **Off by default.** A new player starts with no target, so the band and New
  PB are the only verdicts the app draws unasked, and no line at the app's 95%
  reads as a third. Turning the switch on draws the line at the stored
  percentage, or at 95.
- **What a browser keeps: every choice the player made.** A control that
  persists in the browser drops its stored value when its default in the
  layout changes, so the switch's move from on to off needs one step. The
  page's head script, which already carries an old stored switch across for
  the color scheme, carries this one across before Dash restores it
  ([What retires in code](#what-retires-in-code)). Where the player used the
  switch, their last choice stands: on stays on, including off and then on
  again, and off stays off. A browser with no stored choice, new or one that
  only ever had the default, starts off. The percentage's default stays 95, so a stored percentage, a cleared
  one included, survives with no step. A choice made after the change
  persists as today.
- **Least change.** One judging rule goes, nothing is built for the target but
  that step, and the band reads edges the app already computes.
- **The maintainer's answers keep it.** They use the line little but expect
  other players might, and the 2026-11-10 regimen review keeps its 95% bar
  for now, which the line serves, turned on at 95. Once this ships, no run is
  marked as passing that bar; only the line shows it.
- **What would change it:** a ruling that the line has no use as a target
  (then it retires with its two controls).
- **On file:** the 2026-11-05 research read recommends retiring the verdict
  and the line, unless the line is read as a target (its question 2), when it
  keeps "a user-set target" and retires only the verdict. This
  recommendation keeps the line, as the maintainer's answer to that question
  leans.

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
Medium runs since 2026-09-13 (1,186 runs). Bands by score, with strict outer
edges. Every row but 5 was re-run on 2026-11-06 with the app's own parser,
session and visit split, `typical_score_at_session_start` and its recency
rule.

| # | Measure | Regimen | Lifetime |
|---|---|---|---|
| 1 | Runs with a band | 817 (69%) | 4,535 (49%) |
| 2 | Top 10% / Top 25% / Middle 50% | 31% / 18% / 37% | 35% / 17% / 33% |
| 3 | Bottom 25% / Bottom 10% | 7% / 7% | 7% / 8% |
| 4 | Badge as RT4 shows it: New PB / Top 10% / Bottom 10% / none | 15% / 13% / 5% / 67% | 22% / 12% / 4% / 62% |
| 5 | Today's badge: New PB / passed / below / none | 15% / 31% / 53% / 0% | n/a |
| 6 | Top 10% runs above the chart's drawn band at their point | 67% | 60% |
| 7 | Bottom 10% runs that are a visit's first run | 40% | 24% |
| 8 | Outer-band marks read from an old window | 60 of 307 (20%) | 830 of 1,971 (42%) |

Rates with no trend, every order of the runs equally likely, whatever the
scores' distribution: each outer band at most 14.3% for a 20-run window, 18.8%
at 15 runs and 18.2% at 10, and at least 9.5%, 12.5% and 9.1% when no two
scores tie. Uniform scores give 13.8%, 15.0% and 17.3%. Ties lower the rates,
to none when every run scores the same, and a skewed distribution splits them:
scores of exp(8Z), Z normal, give 12.0% top and 14.1% bottom at 20 runs
(simulated, 400,000 windows).

### Not checked

- **The threshold's figures** (row 5, its pass rates and verdicts) are a
  re-implementation's (`viscose.py`'s session split, which is the app's rule,
  with play order by end time only). The re-run of the band figures matched
  that re-implementation's except the visit figures, row 7 and RT3's rates,
  where it had counted a scenario's first run in its session, not a visit's.
- **Copy lengths in pixels.** RT2's 57 characters are compared by count with
  the 2026-10-25 measurement.
- **The All scenarios view's cost** of building every listed scenario's
  windows for its marks.
- **A screen reader** on the badge, the line and the marks' hovers.
- **One player, one regimen** that set 180 PBs in seven weeks: band rates on a
  flat player would sit nearer the no-trend rates above, at most 14.3%.

## Design

### What the player sees

VT Controlsphere Viscose, from the maintainer's runs; window of 20 runs at
session start: typical 3,025, Middle 50% 2,904 to 3,116, Middle 80% 2,851 to
3,207 (2026-10-16), and on 2026-10-04 typical 2,888 and P90 3,118.

| Run | Today | Proposed |
|---|---|---|
| 2026-10-16, run 7, 3,133 | [Below threshold] `3.6% above typical at session start · 85.8% of PB` | no badge, `Top 25% vs typical at session start · 85.8% of PB` |
| 2026-10-16, run 5, 2,665 | [Below threshold] `11.9% below typical at session start · 73.0% of PB` | [Bottom 10%] `Bottom 10% vs typical at session start · 73.0% of PB` |
| 2026-10-04, run 7, 3,181 | [Below threshold] `10.2% above typical at session start · 94.8% of PB` | [Top 10%] `Top 10% vs typical at session start · 94.8% of PB` |
| cloverRawControl Viscose 50cm, 2026-10-29, 9,969, old window of 15 | [Below threshold] `10.7% above typical at session start` + clock ` · 93.7% of PB` | [Top 10%] `Top 10% vs typical at session start` + clock ` · 93.7% of PB`; the hover names the 15 runs |
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
  phrase today, and the list's marks carry the clock too.
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
  window, today's second paragraph, reworded for runs. With no percentage to
  give, by score from a typical score of zero or less, the typical line names
  the score alone and the band still shows.
- **The card is rewritten** on the triggers it has today, less the
  percentage's change.

### The run list's marks

- A check on a Top 10% run, a gray down arrow on a Bottom 10% run, the star
  unchanged. A new PB with a band carries the check and the star.
- The down arrow is `↓` (U+2193), drawn as the check is, in the gray of the
  card's quiet lines, `#676d75` light and `#a6a6a6` dark. The check stays `✓`
  (U+2713) in green, `green-7` light and `green-4` dark, and the star `★`
  (U+2605) in `#fab005`.
- A check or down arrow read from an old window has the clock after it, the
  scenario table's clock as the card draws it, hidden from a screen reader,
  which hears the mark's words instead. The star has no clock.
- Every row's marks cell has a hover and accessible text naming its band, the
  window's size and its age; a row with no band says why.
- The column is as wide as its widest cell, a check, a clock and a star,
  measured in the browser check, and stays fixed, so the marks stay beside
  the score.
- Marks are computed per run from its own session's window, the same build the
  chart uses, and change only when the runs before a played session change: a
  stats file that lands older than it, or one gone at the next start.

### The run viewer

Its score line is `score_line`'s, so it shows the band, the badge and the
hover with no change of its own. Its reference line already names the same
runs ("Typical comes from your {N} runs before this session").

### The chart and Chart options

- The `Score threshold ({value})` line stays, drawn as today, by pace where
  today's is, and judges no run. Clearing the percentage removes the line and
  nothing else.
- Chart options keeps its three groups and eleven controls. "Score threshold
  overlay" starts off; "Score threshold percentage" keeps 95. A stored choice
  of either survives (RT6 says what a browser keeps).
- The Middle 50% and Middle 80% bands are unchanged: they still follow every
  run.

### What retires in code

`judge_run`, `ThresholdVerdict` and `Unjudged` in `score_threshold.py`, with
`shown_percentage`'s miss cap (the 99.9% cap moves with the PB comparison);
`CardBadge.THRESHOLD_PASSED` and `BELOW_THRESHOLD`; the threshold inputs of
the card, list and run viewer callbacks, with `run_viewer_from_store`'s
percentage. `normalize_score_threshold_percentage`, `score_threshold_line`,
the chart callback's threshold inputs and the two controls stay; the switch's
default becomes off.

One step is added, in `APP_INDEX_STRING`'s head script, before the renderer
runs. Dash stores a persisted edit as `[choice, original]` and restores it
only while the layout's value still equals `original`. Every switch entry an
earlier build stored has `original` true, the old default. The step rewrites
such an entry, stored under
`_dash_persistence.run-history-score-threshold-overlay-switch.checked.true`,
as `[choice, false]`, which Dash then restores. Entries recorded after the
change already hold false, so a second load changes nothing.

### Copy

Every string this proposal adds or edits. Rules 1 to 9 apply. The word
"percentile" stays off the screen, as the maintainer leans ("Don't call it
"percentile" on screen, since that word already means leaderboard placement"):
the PB card's leaderboard line reads `{n}% percentile`.

| Where | String |
|---|---|
| Bands | `Top 10%`, `Top 25%`, `Middle 50%`, `Bottom 25%`, `Bottom 10%` |
| Comparison line | `{band} vs typical at session start · {pct}% of PB`, or `· {pct}% of PB pace` |
| Band hover, first line | `Typical comes from your last {N} runs before this run's session began.`, with `last` only when the scenario had more runs than {N} before the session, as the typical score's hover has it |
| Band hover, typical | `Typical score: {typical} · {pct}% above typical`, with `below`, `Matches typical`, or by pace `{pct}% faster than typical` and `slower`; with no percentage to give, `Typical score: {typical}` |
| Band hover, edges | `Middle 50%: {p25} to {p75}` and `Middle 80%: {p10} to {p90}` |
| Band hover, old window | `Fewer than 10 of those runs were from the 30 days before the session began, so they may have been out of date.` |
| Badges | `Top 10%`, `Bottom 10%`; `New PB` unchanged |
| List mark hover and accessible text | `{band} of your last {N} runs at session start`, with `last` by the same rule, and `, which may have been out of date` on an old window, whose mark shows the clock |
| List hover, no band | `There was no typical score yet when this run's session began.` |
| Score threshold percentage help text | `Sets the score goal as a percentage of your personal best. On a scenario scored by completion time, it's a percentage of your personal best's pace instead, when the app can measure pace reliably. Otherwise, it stays a percentage of your score. The overlay line tracks your current personal best.` |

Retired strings: `Threshold passed`, `Below threshold`, the three "Not
judged." hovers, and the percentage help text's last sentence, `A run is
judged against the personal best you had before the run.` The line's label
`Score threshold ({value})`, both controls' labels and the switch's help text
stay as they are.

### Terms

For the glossary, under Scores and notifications, beside Typical at session
start.

**Band at session start.** Where a run's score sits among the runs behind its
scenario's typical score when the run's session began: above their P90, above
P75, between P25 and P75, below P25, or below P10. Unknown while that typical
score is unknown.
- On screen: `Top 10%`, `Top 25%`, `Middle 50%`, `Bottom 25%`, `Bottom 10%`,
  with `vs typical at session start`; the outer two as the latest-run card's
  badge and as the run list's check and down arrow, with the clock where the
  window wasn't recent.
- In code: `RunBand`, `band_at_session_start`.
- Not a leaderboard percentile, not the retired Top N placement, not the
  chart's bands, which follow every run, and not a promised rate for the next
  run.

The glossary's Score threshold entry becomes:

**Score threshold.** A score goal the player sets as a percentage of the PB,
or of the PB's pace where the app measures a time-scored scenario by pace,
drawn as a line on the chart. It judges no run.
- On screen: the chart's `Score threshold ({value})` line, off until the
  player turns on Score threshold overlay.
- Not a rank's threshold, which comes from a benchmark file, and not the band
  the latest-run card's badge and the run list's check show.

The Typical at session start entry's on-screen wording becomes the line's
`vs typical at session start`, with the run's percentage from typical in the
band's hover.

### Decisions this changes

- **[2026-10-25, typical at session
  start](../decision_log/2026/2026-10-25-the-latest-run-card-measures-the-run-against-the-typical-score-at-session-start.md):**
  the percentage moves from the line to the band's hover, and the line keeps
  the basis as `vs typical at session start`; its value, evidence bar, clock
  and pace rule stand. Superseded in part.
- **[2026-10-12, a past run's
  check](../decision_log/2026/2026-10-12-a-past-runs-check-is-judged-against-the-pb-it-was-chasing-under-its-own-version.md):**
  the check and the badge mark bands, not a threshold; the "Not judged"
  reasons and re-marking on a percentage change go. The one-badge rule, the
  star, the card being worked out from the run store, and a past run's pace
  basis for `% of PB` stand. Superseded in part.
- **[2026-10-13, Top N and the verdict
  switch](../decision_log/2026/2026-10-13-top-n-placement-and-the-score-threshold-verdict-switch-are-retired.md):**
  no setting turns marks off any more, and clearing the percentage removes
  only the line. Its "Moving placement to the latest-run card was considered
  and not taken" was about a run's place among all runs at its sensitivity
  against an unexplained 5; the band is a place among the typical's named
  window. Superseded in part.
- **2026-07-08, judged against the previous PB:** superseded; the PB-chased
  rule lives on in `% of PB`.
- **2026-10-05, pace:** the verdict's two rows leave its table; the threshold
  line's pace form stays. Gains a note.
- **[2026-10-04, verdicts, not
  advice](../decision_log/2026/2026-10-04-skill-is-judged-by-the-typical-run-with-honest-uncertainty-in-verdicts-not-advice.md):**
  D3's example of a verdict, whether a bar the player set, such as the score
  threshold, was met, is one the app stops stating: the line judges no run.
  The rule stands, and a result measured against something the player set is
  still a verdict it allows. The entry gains a dated note, and the roadmap's
  "State verdicts, not advice" names the band in the threshold's place.
  Superseded in part.
- Applied, not changed: [2026-10-18, two
  bands](../decision_log/2026/2026-10-18-two-percentile-bands-show-the-typical-scores-spread.md)
  (its edges), 2026-10-14's rule on a card's lines, and 2026-10-22's evidence
  bar and old-value clock, which reach the list's marks.

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
- **`of your last {N} runs at session start` on the line** (RT2), as first
  filed. The maintainer found it wordy at the direction checkpoint; the
  window's size reads in the hover.
- **`vs typical` alone, or `of typical`** (RT2). Bare `typical` drops the
  basis the 2026-10-25 ruling put on screen, beside a Typical score card that
  can show another value. `of typical` reads as a share of the typical score.
- **Quartile highlights, or a setting for them** (RT3).
- **Two badges, or the band badge only while no threshold is set** (RT4).
- **A threshold as a percentage of the typical score.** The same fixed bar
  moved down: +5% is about 2 standard deviations on beanTS and half of one on
  CatClick Medium (the research read).
- **The line retired with the verdict** (RT6). The evidence against 95% bears
  on the app's own verdict, not on a bar the player chooses. The line is a
  target the app already draws, from two controls it already has, and the
  maintainer expects other players may use it.
- **The line on by default, at 95%** (RT6). It would draw the app's own
  good-run bar on every scenario, the bar the pass rates discredit.
- **An old window's mark left to the hover** (RT5). The qualification would
  reach a reader only when they point at a row.
- **A sixth band, `Best of your last 20`.** New PB already takes most such
  runs, and it adds a third top word.
- **Red for Bottom 10%.** It reads as an alarm; gray is today's color for a
  miss.

## Out of scope

- **Warm-up runs.** A visit's first run is 40% of Bottom 10% runs. Marking
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
   the run viewer by way of `score_line`, the list's marks, clock and hovers,
   the judging code deleted, the line's switch off by default with the head
   script's step for a stored choice, and the percentage's help text
   trimmed. Docs: the Run History spec, the notifications spec's sentence on
   judging a run against the threshold, the glossary, the decision log, the
   roadmap's "State verdicts, not advice", the architecture map
   (`score_threshold.py`'s entry, the run marks' and the card's judging
   lines, the "how a run is judged" row, and the edges into
   `ScoreThreshold`), the README Features line, the user guide and the
   product inventory; deletes this proposal. One PR so no build shows a band
   badge beside a threshold check.

PR #462 (K8) bounds the percentage, which stays; whichever merges second
rebases. Open PR #469 adds a Run History spec statement that names the Score
threshold among the overlay lines the score axis's autorange holds, which
stays true.

## Testing

- **PR 1, unit:** each band at, above and below every edge; a window of 10 and
  of 20; integer scores with ties on an edge; unknown (first session, too few
  runs, one session of 15); a new PB always Top 10%; decimals at the edge.
- **PR 2, unit:** the line's forms (band and PB part, PB part alone, new PB
  gain); the badge's precedence; the hover's lines, by score and by pace, old
  and recent, and with no percentage to give; the list's marks and hovers on
  recent, old and unknown windows, an old check with a star and an old down
  arrow; marks unchanged after a later run in another session; Chart options'
  switch off and percentage at 95 to start; the line drawn at a set
  percentage, with the card and the list unchanged by it.
- **Browser, upgrade,** with storage seeded as an earlier build leaves it: a
  switch turned off and then on stays on; one turned off stays off; a stored
  percentage of 87 and a cleared one survive; a browser with nothing stored,
  new or untouched, starts off. Each holds over a second load, and a choice
  made after the upgrade holds over two more.
- **Browser** (headless Edge, then the maintainer's Firefox), on the states
  above, both themes, at 3840, 2560, 1920 and 1536 px: the longest line on one
  line in the wide card, the narrow card's floor, the badge's contrast, and
  the marks column's width holding a check, a clock and a star.
- **Screen reader** (NVDA): the badge, the line with `, Not recent`, and each
  mark's accessible text, old and recent.
- **Gates:** pytest, ruff format and lint, mypy, compileall, as AGENTS.md
  lists.
