# Run History States A Scenario's 28-Day Trend From Its Session Medians

Status: Proposed
Date: 2026-11-05

## TL;DR

Run History shows every run and the typical score, but it can't say whether
practice on a scenario is still paying off, so the player reads the chart by
eye. This proposal fits a straight line to the median of each session over the
28 days up to the scenario's newest run, and states the result in Scenario
Stats with its range and the sessions behind it. A switch draws those medians
on the chart, and the fitted line on Score vs Time. It is the first phase of a
milestone whose later parts wait for evidence this phase can't give.

## Decisions needed

Seven rows, TR1 to TR7. **Nothing is ratified.** The maintainer's milestone
names three parts, "Score trend analysis, Plateau detection, and High score
imminence", and says there is no clear vision yet; the backlog item reads "the
trend in per-session medians over a 14-day window". Neither is a lean on any
row below. Two research reads, of 2026-11-04 and 2026-11-05, are quoted per
row as "the 11-04 read" and "the 11-05 read". Reviewers may challenge any row,
and anything in [Design](#design), which is author-owned.

### TR1. Phase 1 is the trend on Run History; the rest of the milestone waits

Status: open. No lean on the shape: the milestone names three parts and says
"I don't currently have a clear vision".

The material consequence: phase 1 ships one of the milestone's three named
parts. Plateau detection becomes the player's reading of a rate (TR5), and
high score imminence waits for a check it may never pass ([Milestone
outline](#milestone-outline)).

**Recommendation: phase 1 is a scenario's trend on Run History: its session
medians, the 28-day rate with its range, the sessions behind it, and a word. A
Trend column, a reach figure beside Next Rank, any chance of a PB or a rank
line, and Home lines are later phases, each waiting for the evidence the
outline names.**

- **Both reads put the trend first and any chance last.** Their merged
  position: the trend as a fact on Run History first, a Trend column after, no
  percentage until recorded forecasts are checked, Home waits.
- **The trend answers the open question** product.md lists, "Is my current
  training working?", between sessions, for every scenario, including "not
  enough yet". It reuses sessions, the chart and Scenario Stats, with one new
  function.
- **No chance yet.** On the maintainer's runs a normal on the last 20 runs
  predicted PBs on 4.6% of 706 held-out runs, and 11.3% were PBs. Runs it put
  under 1% were PBs 8 to 9% of the time (6 of 76, and 6 of 65, in the two
  reads' sets). Rank lines cleared 3 to 4 times as often as predicted. "An
  estimate is shown no more precisely than it's known" rules out a figure that
  wrong.
- **The Trend column waits** for the view to be read and understood (the 11-05
  read's order). It reuses this function, so waiting costs little.
- **It reads Too few sessions most of the time** (77% of regimen post-session
  views, 93% lifetime), and that is honest. On the scenarios played most it
  reads a trend: VT Controlsphere and Whisphere read Improving after each of
  their last nine sessions.

### TR2. One median per session, every run counted

Status: open. No lean on first runs. The backlog item says "per-session
medians".

The material consequence: each session's first run stays in, where the
maintainer's planning script leaves it out, so the app's rate can differ from
the script's: RawControlSphere reads +2.3% a week here and +2.7% there, both
Improving.

**Recommendation: the trend's points are one per session of the scenario: the
median of every run of it in that session, at any sensitivity and version,
which is the figure the run list's session row shows as Median. A session
counts when it holds 2 runs of the scenario or more.**

- **A, every run (recommended).** One session has one median on screen: the
  chart's diamond, the trend's point and the run list's Median agree. The
  typical score counts first runs too, and its entry says "A later warm-up
  rule can change the value and needs its own decision"; this row adds none.
- **B, the first run of each session left out.** The planning script's rule,
  and the reads' merged position before they put it to the maintainer. First
  runs after a break score low, and a short session's median carries that.
- **The word rarely changes.** Where the same sessions qualify under both, the
  word differs at 2 of 44 regimen post-session views and 13 of 127 lifetime.
  Leaving first runs out mostly turns Improving into No clear direction (both
  regimen cases; 10 of the 13). Today's two script verdicts keep their words
  either way.
- **Why 2 runs.** A one-run session shows Score, not Median, in the run list,
  and its one run is usually the warm-up. Counting one-run sessions would
  raise regimen views with a trend from 47 to 52, and lifetime from 180
  to 267.
- **On file:** the 11-04 read: "One rule for both is cleaner; which one is a
  product call." The 11-05 read: "Should the trend include first runs to align
  with Typical, or keep the regimen's post-first population with a permanent
  explicit label?"

### TR3. The window: the 28 days up to the scenario's newest run, at any age

Status: open. No lean. The backlog item says "a 14-day window"; the
maintainer's planning script has used 28 days, with at least 5 sessions
spanning at least 10 days, since 2026-10-03.

The material consequence: a trend never lapses with time away. After a break
it still reads, dated, about sessions weeks old, and a flattening shows in it
up to four weeks late.

**Recommendation: the trend uses the scenario's sessions that ended in the 28
days up to its newest run, and needs at least 5 of them spanning at least 10
days. It is shown at any age, with its first and last session's dates in the
hover, as the typical score is shown at any age. A session in progress counts
as it stands.**

- **A, ending at the scenario's newest run (recommended).** It never lapses,
  and it says what the last four weeks of play on the scenario showed.
- **B, ending now.** The 11-05 read's "current-calendar assessment". It thins
  out while the scenario isn't played and lapses after 28 days.
- **C, ending at one moment for every scenario.** The planning script's rule:
  the newest run of any benchmark scenario.
- **The end decides more than any other row.** Of the 39 benchmark scenarios,
  A gives 11 a trend (8 Improving, 3 No clear direction); C on 10-29 gives 2;
  B gives 1 on 11-05 and none on 11-08.
- **The same runs, two words.** VT Controlsphere, last played Oct 16:
    - A: 17 sessions from Sep 19, Improving, +6.0% a week (+3.7 to +8.4).
    - C on 10-29: 5 sessions from Oct 2, No clear direction, +1.8% a week
      (−3.4 to +6.9); the script, first runs out, called it Plateau.
    - The 11-04 read's weekly sweep: Improving on 10-06, 10-13 and 10-20, then
      Plateau on 10-27 and 10-29, with no run after 10-16.
- **Each end has a cost.** October's five sessions sit flatter than
  September's, between about 2,860 and 3,090: A's line still rises through
  them, since 28 days lag a flattening. B and C read time away as fewer
  sessions. The diamonds show both (TR7).
- **28 days is the steadiest window that still covers.** Regimen views with a
  trend, and how often the word changed from one session to the next:
    - 21 days: 54 views, 5 changes of 43.
    - 28 days: 47 views, 4 of 35.
    - 42 days: 51 views, 3 of 38.
    - The last 6 sessions within 42 days (the 11-04 read's idea): 27 views, 6
      of 16.
    - Lifetime, 42 days changed the word 46 times in 219 with 10
      back-and-forth reversals; 28 days, 17 in 134 with 1.
- **The 10-day span bites:** 32 of the 208 regimen views had 5 sessions inside
  10 days and read Too few sessions.
- **The session in progress.** On the five most-played regimen scenarios, the
  word changed between a session's second run and its last in 4 of 82
  sessions. Freezing the trend until a session ends would add a rule for 1
  session in 20.
- **On file:** the 11-05 read: "At the November 5 calendar cutoff only
  RawControlSphere still qualifies. VT Controlsphere loses support without a
  new run. This must read as insufficient current evidence, not as a change in
  skill." Its open question 5 asks for "a dated last-play assessment, a
  current-calendar assessment with less support, or both". The 11-04 read asks
  which window (question 2). Neither tested A.

### TR4. What the word says

Status: open. No lean.

The material consequence: Improving says the direction is supported, not that
the rate is large. RawControlSphere reads Improving with a range that starts
at +0.6% a week.

**Recommendation: Improving when the whole 90% range of the rate is above
zero, Declining when it is below, No clear direction otherwise, and Too few
sessions under TR3's minimum. The rate and its range always show beside the
word, so a player who cares about size reads it there.**

- **A, the range excludes zero (recommended).** The 11-04 read's rule, and the
  planning script's Improving.
- **B, the range clears a size.** The 11-05 read's rule: Improving only when
  the whole range is above +0.3% a day; "little change" when it sits inside
  ±0.3; "direction supported, size not established" when it excludes zero but
  not 0.3.
- **C, no word:** the rate and range alone.
- **How often each word shows,** on the 47 regimen post-session views with a
  trend (lifetime, 180):

| # | Rule | Improving | Direction only | No clear direction | Little change | Declining | Word changes after a session |
|---|---|---|---|---|---|---|---|
| 1 | A | 40 (77) | n/a | 7 (103) | n/a | 0 (0) | 4 of 35 (17 of 134) |
| 2 | B at ±0.3% a day | 23 (32) | 17 (45) | 7 (96) | 0 (7) | 0 (0) | 15 of 35 (30 of 134) |

- **B's extra changes** are Improving and "direction only" trading places as
  the range's lower end crosses 0.3. A word that changes after a third of
  sessions on unchanged play reads as noise.
- **B's size is a judgment.** 0.3% a day is 2.1% a week and 8.4% over 28 days.
  The 11-05 read: it "may be much too large" to call little change. A rate on
  screen lets each player apply their own.
- **C** gives up the roadmap's first principle, "answer the question, don't
  just show the data".
- **Declining never showed** at 90% on these runs, and it stays because
  another player's runs can fall. An 80% range would show Improving at 44
  regimen views rather than 40, and change the word more often (22 lifetime
  changes against 17).
- **On file:** the 11-05 read: "The UI should distinguish **direction
  supported** from **size not established**, rather than displaying a bare
  "Unclear."" The 11-04 read: "Improving" or "Declining" "only when the range
  excludes zero".

### TR5. No Plateau and no "imminence" on screen

Status: open. No lean on the words. The milestone names "Plateau detection"
and "High score imminence"; the roadmap's planned verdict reads "improving /
plateauing / declining".

The material consequence: Plateau detection leaves the milestone as a feature.
A player's own plateau rule reads the rate and range.

**Recommendation: the app shows no Plateau verdict and no "imminence" wording.
The roadmap's Future entry and product.md's open problem read "improving /
declining / no clear direction".**

- **A plateau call is "not shown to be improving".** The planning script's
  rule calls Plateau when the range doesn't clear zero and the rate is under
  0.3% a day, a failure to show a rise, not evidence of a flat month. No
  regimen view's range sat inside ±0.3% a day; lifetime, 7 of 180 did, on two
  scenarios.
- **The three calls on these runs.** The script called Plateau on three
  benchmark scenarios between 10-13 and 10-29. RawControlSphere read Improving
  by the same rule on 10-29. StaticSwitchingVox Small read Improving by a
  robust fit (Theil-Sen) on the same medians. VT Controlsphere is TR3's window
  end. Three calls measure no error rate: the windows overlap, and a rise can
  start after a flat month (the 11-05 read).
- **"Imminence" suggests a countdown** (the 11-05 read). Both reads keep it
  off the screen.
- **D3 doesn't require this.** PR #327 said the app "would show … "Plateau",
  not what to do about it". The reason here is evidence, not the principle.
- **The roadmap and product.md change wording only.** The Future list's
  membership, ruled as D5 on 2026-10-04, stands.

### TR6. Scenario Stats states the trend

Status: open. No lean.

The material consequence: Scenario Stats grows by two lines in every state,
Too few sessions included, and that is what three in four regimen post-session
views show.

**Recommendation: after the typical score's lead, Scenario Stats shows
`Trend: {word}` with a hover, then the rate, its range and the session count,
such as `+2.3% a week (+0.6 to +3.9) · 5 sessions`. Too few sessions says how
many it has and what it needs.**

- **A, Scenario Stats (recommended).** The 11-04 read's sketch. The trend
  describes the typical score over time, and sits beside it.
- **B, in the chart's area only.** The 11-05 read's "Recent trend" view (TR7's
  option B).
- **C, nowhere but the chart.** The word would need the switch on to be seen.
- **Uncertainty and support without a hover.** The 11-05 read's interaction
  rule: "show essential uncertainty and support without hover". The range and
  the session count are on the line; the dates and the method are in the
  hover.
- **It has to fit.** The card is 270 px wide and fits in the row the
  dropdowns' column sets (SC4). The longest figures line,
  `+12.4% a week (−10.1 to +34.9) · 17 sessions`, is 44 characters. Whether
  two more lines fit the row is checked in the browser in PR 2 ([Not
  checked](#not-checked)).

### TR7. A Session medians switch on the chart, off to start

Status: open. No lean.

The material consequence: the evidence behind the word is one switch away.
With it on, the chart gains a diamond per session and, on Score vs Time, a
dotted line.

**Recommendation: Chart options' Overlays gains `Session medians` after
`Middle 80%`, off to start. On, Score vs Run and Score vs Time mark each
session's median with a hollow diamond, and Score vs Time also draws the
trend's fitted line over its sessions when the trend has a word. Score vs
Sensitivity shows neither.**

- **A, a switch on the chart, off to start (recommended).** The 11-04 read's
  switch.
- **B, a "Recent trend" view in the chart's place,** listing the session
  medians with links to their sessions (the 11-05 read). It would be a second
  thing that opens where the chart was, beside the run viewer. The run list's
  session rows already show each median and open each session.
- **C, on to start.**
- **The points show what one rate hides.** VT Controlsphere's line to Oct 16
  rises 6% a week while its last five diamonds sit between about 2,860 and
  3,090.
- **Why off to start.** AT4's reason: a remembered control's stored value
  resets when its default changes, so turning it on later turns it on
  everywhere. And the chart already holds runs, stars, a ring, the typical
  line, two bands and three overlay families.
- **Why the line on Score vs Time only.** The rate is per calendar day. On
  Score vs Run's axis of runs, a straight line in days would bend at every
  uneven gap.

## Problem

### What Run History shows today

- **The chart** ([spec](../specs/run_history.md#the-chart)): every run as a
  point, New PB stars, the latest run's ring, and on Score vs Run and Score vs
  Time the typical score's line inside its Middle 50% and Middle 80% bands,
  worked out after each run.
- **Scenario Stats** ([spec](../specs/run_history.md#scenario-stats)):
  `Typical score`, its lead and hover, Category and Total runs.
- **The run list's session rows**
  ([spec](../specs/run_history.md#this-scenario)): with "Median and best" on,
  `Median {median}` and `Best {best}` of the scenario's runs in each session.
- **Nothing says whether the scenario is improving.** The typical line moves
  one run at a time and its values share up to 19 runs, so three rises in a
  row are not three pieces of evidence.

### Why now

- The roadmap's Future entry "Score trend verdict" names its shipped
  prerequisites, "that chart and the typical score definition". Both have
  shipped.
- product.md lists "Is my current training working?" as the first unsolved
  problem.
- The maintainer named this milestone next and asked for a plan, with no clear
  vision of its shape.

### Verified facts

- `build_run_history_figure` in `source/components/run_history_chart.py` takes
  one snapshot of the run store, splits it with `split_into_play_sessions`,
  works every typical value out over the whole history, and only then applies
  the range. The trend can take the same snapshot.
- `_figures` and `_figure_parts` in `source/components/run_history_list.py`
  compute a session row's median with `statistics.median` over every run under
  the row; a one-run row shows `Score` instead.
- Scenario Stats is built in `source/components/scenario_stats.py`. Its lead's
  hover comes from `typical_score_hover`, and it updates on a
  selected-scenario run, a scenario change and the page's 30-second tick.
- `scipy` is already a dependency (`pyproject.toml`), so
  `scipy.stats.linregress` and `scipy.stats.t` need nothing new.
- Pace: `get_version_pace_basis(scenario, hash)` answers for a version; the
  latest-run card measures by pace only where every run behind its value is of
  the run's version.

### What the maintainer's runs say

9,284 runs through 2026-10-29 23:57, 866 scenarios, 332 sessions. Points are
session medians of 2 or more runs, every run counted, over the 28 days up to
the newest run, at least 5 sessions over 10 days; Improving or Declining when
the 90% range excludes zero.

| # | Measure | Regimen (39 benchmark scenarios, since 2026-09-13) | Lifetime (all scenarios) |
|---|---|---|---|
| 1 | Post-session views | 208 | 2,750 |
| 2 | With a trend | 47 (23%) | 180 (7%) |
| 3 | Improving / No clear direction / Declining | 40 / 7 / 0 | 77 / 103 / 0 |
| 4 | Word changed from one session to the next | 4 of 35 | 17 of 134 |
| 5 | Median width of the 90% range | 5.4% a week | 6.0% a week |
| 6 | Scenarios with a trend at their newest run | 11 of 39 | 18 of 866 |

Why the other 28 benchmark scenarios have none at their newest run: 8 have 1
session in their last 28 days, 11 have 2, 5 have 3 and 4 have 4.

The 11 with a trend, as each would read on 2026-11-08:

| # | Scenario | Sessions | Days since | Word | Rate a week (90% range) |
|---|---|---|---|---|---|
| 1 | RawControlSphere | 5, Oct 8 to Oct 29 | 9 | Improving | +2.3% (+0.6 to +3.9) |
| 2 | VT Controlsphere Viscose | 17, Sep 19 to Oct 16 | 22 | Improving | +6.0% (+3.7 to +8.4) |
| 3 | Air Voltaic Invincible 4 Medium | 9, Sep 19 to Oct 16 | 22 | Improving | +2.4% (+1.1 to +3.7) |
| 4 | Popcorn MV Medium | 6, Sep 26 to Oct 16 | 22 | Improving | +7.2% (+1.5 to +13.0) |
| 5 | Whisphere Viscose | 20, Sep 15 to Oct 9 | 29 | Improving | +6.3% (+4.8 to +7.8) |
| 6 | Smoothsphere Viscose | 12, Sep 13 to Oct 9 | 29 | Improving | +3.8% (+2.8 to +4.8) |
| 7 | StaticSwitchingVox Small | 5, Sep 18 to Oct 9 | 29 | No clear direction | +0.8% (−1.3 to +3.0) |
| 8 | Leapstrafes Control wobin | 6, Sep 13 to Oct 4 | 34 | Improving | +4.4% (+2.2 to +6.6) |
| 9 | Pasu Voltaic Reload Easy | 7, Sep 18 to Sep 30 | 38 | No clear direction | +6.7% (−1.0 to +14.5) |
| 10 | Plink Palace Easy | 7, Sep 20 to Sep 30 | 38 | No clear direction | +5.9% (−0.7 to +12.6) |
| 11 | Air CELESTIAL No UFO Medium | 10, Sep 14 to Sep 28 | 40 | Improving | +4.7% by pace (+1.7 to +7.6) |

### Not checked

- **The app's own session split** against `viscose.py`'s; they differ on runs
  outside 1 to 1,800 seconds (both research reads' caveat). Not diffed.
- **The app's functions were not run.** The trend is a re-implementation over
  the planning script's sessions.
- **Scenario Stats' height** with two more lines, against the row the
  dropdowns' column sets.
- **Sensitivity changes inside a window,** which can read as a rate. Not
  measured.
- **One player, one regimen** that set 180 PBs in seven weeks: a player who
  isn't improving would see No clear direction far more often.

## Milestone outline

Each later phase is its own proposal, out of scope here, and waits for the
evidence named.

| # | Phase | What | Waits for |
|---|---|---|---|
| 1 | This proposal | The trend on Run History (TR1 to TR7) | n/a |
| 2 | Trend column | The same function as a column on the scenario table, sorted by rate, Too few sessions last | Phase 1 read at a few weekly checks; TR4's word holding up in use |
| 3 | Reach | Beside Next Rank: the line's distance from the typical score in the scenario's spread, and recent runs near it | Its own row set; a re-run of the clear check after the next rank push |
| 4 | Any chance | A PB or rank-line chance, per run or per visit | Forecasts recorded before each run and checked for calibration below 5% |
| 5 | Home lines | Dated counts of trend words linking to the table | An overview design |

- **Phase 2's evidence.** That the word reads right to the player over weeks,
  and that the app's session split matches the planning script's.
- **Phase 3's evidence.** On the maintainer's runs the PB gap predicted a
  clear better than a distance in spreads (AUC 0.77 against 0.70) on only 30
  clears. Reach would be added beside Next Rank, never in its place, and never
  as a percentage.
- **Phase 4's evidence.** The forecasts are written down before each run. The
  bins the screen would show, under 1% and 1 to 5%, are checked on a later
  stretch of play. Before any figure ships, the denominator (a completed run,
  an attempt, a minute) and the run's position in its visit are named. It may
  never pass.
- **Not a phase:** a Plateau verdict (TR5). It would need a size of change the
  player calls little, and ranges that sit inside it.

The milestone's two notes, placed:

- **"Calculate Median, variance, standard deviation, chance of hitting a new
  PB."** The median is the typical score, and the spread is its two bands,
  both shipped. A standard deviation is Reach's unit (phase 3). The chance is
  phase 4.
- **"Calculate how far current PB is from the Median."** The PB's height above
  the typical score, in the same spread, belongs in Reach's hover (phase 3).

## Design

### The trend

- **Points.** One per session of the scenario holding 2 or more of its runs:
  their median at any sensitivity and version (TR2), placed in time at the
  midpoint between its first and last run's end.
- **Window.** The sessions whose last run of the scenario ended in the 28 days
  up to the scenario's newest run, the newest session included while in
  progress (TR3).
- **Minimum.** At least 5 sessions, the first and last points at least 10 days
  apart. Under it: Too few sessions, with the counts. Unknown is never read as
  flat or as weak.
- **Fit.** Each median as a percent of the window's mean median; ordinary
  least squares against days; the 90% range is the slope ± `t(0.95, n − 2)` ×
  its standard error. The rate is the slope × 7, a percent a week.
- **Word** (TR4): Improving when the range's low end is above 0, Declining
  when its high end is below 0, else No clear direction.
- **Time-scored scenarios.** By pace, `C / (C − median)`, when the scenario is
  recognized as time-scored and every run in the window is of its newest run's
  version, as the latest-run card decides. Otherwise by score, which orders
  the same way, so the word rarely changes.
- **Constants:** 28 days, 5 sessions, 10 days, 2 runs, 90%. No settings.
- **In code:** a pure `score_trend(runs, play_sessions)` in
  `source/kovaaks/score_trend.py`, beside `typical_score.py`, returning a
  frozen `ScoreTrend` (word, rate, low, high, sessions with their medians and
  times, basis) or the counts that fell short. It reads no clock and caches
  nothing.

### Scenario Stats

- Two lines after the lead, before Category: `Trend: {word}` (the label bold,
  as `Category:` is; the word underlined dotted with a hover, focusable as the
  lead is), then the figures line.
- The figures line reads the rate, its range and the session count; or, under
  the minimum, what it has against what it needs.
- With no scenario selected, or no runs, the two lines are absent.
- It updates on the triggers the lead updates on. Unchanged content returns
  `no_update`, as the lead does.

### The chart and Chart options

- **The switch.** `Session medians` in Overlays after `Middle 80%`, off,
  remembered as its neighbors are, id `run-history-session-medians-switch`. An
  input of the chart rebuild.
- **Diamonds.** On, Score vs Run and Score vs Time draw a hollow diamond per
  session of 2 or more runs in the range: on Score vs Run at its middle run's
  position, on Score vs Time at its midpoint. They use the typical line's
  gray, drawn over the bands and under the runs (`zorder` −1). Legend
  `Session median`, one group.
- **The line.** On Score vs Time, when the trend has a word, a dotted line in
  the same gray from the window's first point to its last, at the fitted
  values. Legend `Trend`.
- **Hovers.** A diamond's names its median, session and run count; the line's
  names the word, the rate, the range and the sessions.
- **Not drawn** on Score vs Sensitivity.
- **Zoom.** Diamonds sit among the runs and change no fit. The line takes part
  in the refit as the typical line does.

### Copy

Every string this proposal adds. Rules 1 to 9 apply. Rates and ranges show one
decimal with a sign, the minus as `−`.

| Where | String |
|---|---|
| Scenario Stats, word line | `Trend: Improving`, `Trend: Declining`, `Trend: No clear direction`, `Trend: Too few sessions` |
| Figures line | `{rate}% a week ({low} to {high}) · {n} sessions`; by pace `{rate}% a week by pace ({low} to {high}) · {n} sessions` |
| Figures line, too few | `{n} of 5 sessions in 28 days`, or `{n} sessions over {d} days · needs 10 days` |
| Word hover, first line | `Fitted to the median of each session with 2 or more runs here, in the 28 days up to your latest run.` |
| Word hover, readouts | `Sessions: {n} · {first} to {last}` and `Rate: {rate}% a week · 90% range {low} to {high}` |
| Word hover, last line | `The whole range is above zero.`, `The whole range is below zero.`, or `The range runs from below zero to above it, so these sessions don't show a direction.` |
| Word hover, pace | `Measured by pace, because this scenario is scored by completion time.` |
| Word hover, too few | `A trend needs at least 5 sessions with 2 or more runs here, at least 10 days apart from first to last, in the 28 days up to your latest run.` |
| Switch and help | `Session medians`; `Marks the median of each session's runs with a diamond. On **Score vs Time** it also draws the trend of the 28 days up to your latest run, when there is one. **Score vs Sensitivity** doesn't show either.` |
| Legend | `Session median`, `Trend` |
| Diamond hover | `Session median: {median}` and `Session: {session_name} · {n} runs` |
| Line hover | `Trend: {word}`, `Rate: {rate}% a week · 90% range {low} to {high}`, `Sessions: {n} · {first} to {last}` |

- **Per week, not per day.** One decimal a day (`+0.3%`) can't tell 0.25 from
  0.34, and a week is about how often a scenario is played and checked. The
  planning script's 0.3% a day is 2.1% a week.
- **The dates live in the hover.** The latest-run card beside Scenario Stats
  already dates the newest run.

### Terms

For the glossary, under Scores and notifications, after Typical score.

**Trend.** How fast a scenario's session medians changed over the 28 days up
to its newest run, as a percent of their mean a week, with a 90% range.
Improving or Declining when the whole range is above or below zero, else No
clear direction; Too few sessions under 5 sessions spanning 10 days.
- On screen: `Trend: {word}` in Scenario Stats; the chart's `Trend` line.
- In code: `ScoreTrend`, `score_trend`.
- Not a plateau verdict, not the typical score's change, and not a forecast.

**Session median.** The median of a scenario's runs in one session of 2 or
more: the run list's Median, the chart's diamond, and a trend's point.

### Decisions this changes

- **The roadmap's "Score trend verdict"** reads "improving / declining / no
  clear direction" and becomes this milestone, with the outline's phases. D5's
  membership stands.
- **product.md, "Where it's going":** the same words.
- **The roadmap's "Difficulty measured against the player's own runs":**
  unchanged here; it becomes phases 3 and 4.
- Applied, not changed:
  [2026-10-04](../decision_log/2026/2026-10-04-skill-is-judged-by-the-typical-run-with-honest-uncertainty-in-verdicts-not-advice.md)
  D2 (Too few sessions is never weak) and D3 (a trend is a verdict, and
  nothing here says what to play);
  [TS1](../decision_log/2026/2026-10-15-typical-score-uses-the-last-twenty-runs-and-counts-every-version.md)
  (every run, version and sensitivity counts; no warm-up rule);
  [2026-10-14](../decision_log/2026/2026-10-14-the-run-lists-columns-menu-offers-median-and-best-off-to-start.md)
  (the session row's Median is the trend's point); 2026-10-05 pace;
  2026-10-30's switch default.

### Alternatives rejected

- **The rolling typical score as the trend** (its change over 14 days, say).
  Its values share up to 19 runs, and "not played" reads as flat: in the 11-04
  read's sweep that rule called 99 of 132 scenario-weeks Plateau.
- **The last 10 runs against the 10 before.** Flips: 20 changes and 4
  back-and-forth reversals in 9 weeks (the 11-04 read).
- **Theil-Sen in place of least squares.** On the same medians it disagreed
  with least squares at 10 of 35 verdicts (the 11-04 read), so the word would
  follow the fit's convention. Least squares is also what the planning script
  uses.
- **A shaded band around the fitted line.** Its range is the slope's, not
  where runs land, and a third gray band beside Middle 50% and Middle 80%
  would read as one of them. The range is in words instead.
- **The fitted line on Score vs Run.** Runs are not evenly spaced in time.
- **A rate per day,** the planning script's unit (Copy).
- **Freezing the trend until the session ends** (TR3).

## Out of scope

- **The later phases:** the Trend column, Reach, any chance, Home lines
  ([Milestone outline](#milestone-outline)).
- **A Plateau verdict** (TR5), and anything that says what to play or when to
  stop.
- **Warm-up marking,** a separate item. Revisit TR2 if one ships.
- **Sensitivity and version splits inside a window.** Every run counts, as for
  the typical score.
- **The run viewer, the run toast and the scenario table:** unchanged.

## Delivery plan

Stated intent, not a contract; a PR that moves a boundary says so in its
description.

1. **The trend, pure.** `score_trend` and `ScoreTrend`, with tests. No UI.
2. **Every surface and the docs.** Scenario Stats' two lines and hover, the
   switch, the diamonds and the line. The Run History spec, the glossary, the
   roadmap and product.md, the README Features line and the user guide; this
   proposal is deleted.

## Testing

- **PR 1, unit:** the minimum at 4 sessions, at 5 sessions inside 9 days and
  at 5 over 10; one-run sessions skipped; a session in progress; a rising, a
  falling and a flat series; pace on a time-scored version, and score where
  the window mixes versions; a window at the 28-day edge; ties.
- **PR 2, unit:** each word's two lines and hover; Too few sessions' two
  forms; the switch off and on in each mode; the line only with a word; Score
  vs Sensitivity unchanged; the legend entries.
- **Browser** (headless Edge, then the maintainer's Firefox), both themes, at
  3840, 2560, 1920 and 1536 px: the longest figures line, the top row's
  height, the diamonds against the runs and the bands.
- **Screen reader** (NVDA): the word and its hover, the switch and its help.
- **Gates:** pytest, ruff format and lint, mypy, compileall, as AGENTS.md
  lists.
