# Run History's Score Cards Measure The Run Against The Typical Score

Status: Proposed
Date: 2026-10-25

## TL;DR

Run History's Latest Run card compares a run only with the PB, so most runs
read as a miss, and it spends its lines on the scenario's name and on two
lines of session details. This proposal compares the run with the typical
score as it stood when its session began, drops the name, puts the session
details on one line, and ends the card with the run's cm/360 and accuracy as
the PB card ends with its own. The three score cards start their lines from
the top, so their labels and their large numbers line up whatever each card
holds.

## Decisions needed

Four rulings: SC1 to SC4. The maintainer ratified this proposal on
2026-10-25 at `c77ad06`: "I ratify the proposal on PR #430 at c77ad06." That
settles each row as its recommendation, SC1 and SC3 as amended in review.
Before that, each row was the maintainer's lean from the design discussion
of 2026-10-24 and 2026-10-25, worked out on three versions of a mockup built
from their own stats, with today's cards behind a switch. The first review
wave, on 2026-10-25, endorsed SC2 and SC4 and amended SC1 and SC3; each
row's status line keeps what was said, for the record. Everything else is
author-owned, in [Design](#design), and the ratification covers it too.
Two more changes from the same discussion go elsewhere
([Out of scope](#out-of-scope)): the verdict badges' contrast in light mode,
a defect fix that shipped in its own pull request (#429), and the typical
score's rank on the
Typical score card, which gets a proposal of its own.

### SC1. The latest run is compared with the typical score at session start

Status: Ratified (user), 2026-10-25: accept the recommendation below, as
amended in review. The maintainer's lean before that, 2026-10-24: "Use the
typical score at session start for the comparison." The author had recommended the Typical
score card's own value; see [Alternatives rejected](#alternatives-rejected).
The wave kept the basis and the evidence bar, and asked that the basis be
named on screen and an old value be marked on the card, not only in the
hover. Leaving the phrase off a new PB is the author's: there it could never
report a deficit.

The material consequence: the card gains a second comparison, and during a
session its percentage, and even its direction, can differ from what the
number on the Typical score card beside it would give.

**Recommendation: on a run that isn't a new PB, the comparison line names the
run's distance from the typical score as it stood when the run's session
began, `3.6% above typical at session start` or `5.8% below typical at
session start`, before its percentage of the PB. Every run of a session is
measured against the same value. A known value counts at any age; when it
wasn't recent at the session's start, a small clock follows the phrase, a
screen reader hears `Not recent`, and the hover says why. With no known
value the phrase is left out, and on a new PB the line keeps the PB gain
alone.**

- **The PB alone reads almost every run as a miss.** On 2026-10-16 the
  maintainer's VT Controlsphere Viscose run of 3,133 read `85.8% of PB`, and
  "Below threshold" at the default 95% threshold. It was 3.6% above their typical score at the start of
  that session, a good run, and nothing on the card said so. The roadmap's
  principles judge skill by the typical run and keep the PB as the
  achievement; this is the card where a run is judged.
- **Why the session start.** The typical-score ruling that draws the value
  after each run kept "the per-session freeze" for "later comparisons", and
  this is the first one. A frozen value gives every run of a session the same
  yardstick, so run 1 and run 8 compare with each other, and it never
  includes the run being judged or the runs just before it.
- **Its cost.** The Typical score card shows the value after the newest run.
  On a good session the two drift apart. On the maintainer's threshold-passed
  run of 2,884 on Flower 50cm, the phrase reads `7.5% above typical at session
  start` against 2,684, while the card beside it shows 2,778, from which the
  run is 3.8% above. The direction can disagree too: a run of 2,750 in that
  session would read `2.5% above typical at session start` beside the card's
  2,778. The phrase names its basis, and its hover names the value, so the
  two can be reconciled.
- **The basis is named on screen** because the at-a-glance reading must not
  depend on a hover, and a phrase that said only `above typical` beside a
  different typical score could read as wrong.
- **The evidence bar.** The 2026-10-04 principles say a judgment that uses an
  old value must choose its evidence bar. This row chooses the scenario
  table's
  ([2026-10-22](../decision_log/2026/2026-10-22-every-known-typical-score-gets-a-typical-rank-old-or-not.md)):
  a known value counts at any age. That table admitted old values on the
  condition that the qualification reaches every reader, and marks an old
  value where it is shown, with a clock and `Not recent` for a screen reader
  ([2026-10-22](../decision_log/2026/2026-10-22-an-old-typical-value-on-the-table-is-marked-with-a-clock-in-a-readable-grey.md)).
  The phrase takes the same mark. Three of the four mocked states, on two
  scenarios, compare against a session-start value that wasn't recent when
  the session began (both Flower 50cm states, 8 of 16 runs recent; VT ww5t
  Intermediate S5, 0 of 20), and the Typical score card beside the Flower
  states looks current by then, so it can't serve as the warning. A scenario
  with no known typical score before the session gets no phrase.
- **No phrase on a new PB.** A new PB scores above every earlier run, at
  any sensitivity and version, and the typical score at session start is a
  median of earlier runs, so on a new PB the phrase could never report a
  deficit: it would read `above`, or `Matches` where a tiny gain rounds to
  0.0%. It would add only a magnitude, which the Typical score card beside
  it approximates, and the PB gain already says how far the run went. The
  rule rests on that, not on the line's width. The width is a second
  reason: with the phrase a new PB's line can run past the wide card's
  474 px, as the pace form does at 504 px, and a long score form does with
  an old value's clock (438 to 469 px before it).
- **Time-scored scenarios** are compared by pace when every run behind the
  typical value is of the run's version and a performance file answers for
  that version, with both times positive, as the scenario table's Typical
  Rank column decides it: `2.1% faster than typical at session start`. That
  is decided apart from the PB comparison's measure, so one line can mix
  them, and the wording names each (`of PB pace`, `faster than typical`).

| Mocked state | Score | At session start | Typical card's value |
|---|---|---|---|
| Just played, new PB (Flower 50cm; no phrase shown) | 3,152 | 2,684, +17.4% | 2,847, +10.7% |
| Just played, threshold passed (Flower 50cm) | 2,884 | 2,684, +7.5% | 2,778, +3.8% |
| Just played, below threshold (VT Controlsphere Viscose) | 3,133 | 3,025, +3.6% | 2,999, +4.5% |
| Looking up, 2 months later (VT ww5t Intermediate S5) | 1,310 | 1,390, −5.8% | 1,385, −5.4% |

### SC2. The card's first line drops the scenario's name

Status: Ratified (user), 2026-10-25: accept the recommendation below. The
maintainer's lean before that, 2026-10-25: "Keep changes 2 to 5 as
proposed: no scenario name, the rebalanced lines, top-aligned cards, and
readable badges."

The material consequence: nothing directly above the run list names its
scenario any more, which was the reason the list's heading line left the
screen.

**Recommendation: the first line reads `Latest run · {age}`, as the PB card's
reads `PB · set {age}`. The run list's heading line stays for screen readers
only.**

- **The card always follows the selection.** Since 2026-10-18 the card
  reports the selected scenario's latest run, so the name repeats the
  Selected scenario field and the chart's title, three times on screen at
  once. Neither of the other two score cards names it.
- **The run list's heading line** left the screen because "the latest-run
  card right above the list names its scenario". After this row the names
  nearest the list are the chart's title, beside the list, and the Selected
  scenario field. The list's This scenario view lists only the
  selection's runs, so its scenario is still the page's one scenario. The
  alternative, bringing the heading line back, costs about 35 px of list
  rows.
- **A long name is no longer cut short** on the card, and its tooltip goes
  with it.
- **A screen reader** that reaches the card's age hears no scenario's name on
  the card; the nearest names are the Selected scenario field and the list's
  hidden heading line. That is acceptable, and the screen-reader check covers
  it.

### SC3. One comparison line, one session line, then cm/360 and accuracy

Status: Ratified (user), 2026-10-25: accept the recommendation below, as
amended in review. The maintainer's lean before that, 2026-10-25, as quoted
under SC2. The wave asked that the quiet lines stay readable.

The material consequence: the card shows the run's sensitivity, and accuracy
moves from the comparison line to a quiet last line, in a grey that stays
readable.

**Recommendation: under the score, three lines. The comparison line, at
today's weight, holds only comparisons (SC1's phrase and the PB comparison).
The session line puts today's two quiet lines on one: `Run 7 this session ·
9 min on this scenario`. The last line, in the same quiet style, is the run's
`50 cm/360 · Accuracy 52.21%`, the PB card's last line for the PB run. Those
two lines, and the PB card's last line, take the scenario table's readable
grey, at least 4.5:1 in both themes.**

- **The 2026-10-14 rule on a card's lines** puts the fact the player acts on
  first, at full weight, and the supporting facts after it, quieter. Accuracy
  and cm/360 are quiet on the PB card "because they support the PB"; the
  same holds for the run. Today the run's accuracy sits at full weight on the
  comparison line.
- **The two cards then compare line for line:** score, its comparison, then
  cm/360 and accuracy, so a run at a new sensitivity reads against the PB's
  at a glance.
- **The session details took two lines** so the run's score would sit 2 px
  from the PB's when the PB card showed a benchmark and a leaderboard line on
  one line, and 8.5 px or 24 px from it in its other states. SC4 lines them
  up for good, so that reason goes.
- **The quiet style today is too faint for text this size.** The cards' 12 px
  grey measures 3.32:1 light and 4.04:1 dark, under the 4.5:1 WCAG AA asks,
  and the run's accuracy would move into it from a full-strength line. The
  scenario table's readable grey, `#676d75` light and `#a6a6a6` dark,
  measured 5.22:1 and 6.38:1 there
  ([2026-10-22](../decision_log/2026/2026-10-22-an-old-typical-value-on-the-table-is-marked-with-a-clock-in-a-readable-grey.md)),
  and is still quieter than the comparison line. The PB card's last line
  takes it too, so the two cards still read line for line. The cards' first
  lines keep today's grey.

### SC4. The three score cards line up from the top

Status: Ratified (user), 2026-10-25: accept the recommendation below. The
maintainer's lean before that, 2026-10-25, as quoted under SC2. The wave
endorsed the row and corrected its narrow floor.

The material consequence: a card with fewer lines leaves its spare room at
its bottom instead of above and below its lines, and in the narrow layout the
Latest Run card is taller than today.

**Recommendation: Typical score, PB and Latest run start their lines 12 px
below their top edge, with the same 2 px between lines in all three. Their
first lines then share one top, and their large numbers share another, in
every state.**

- **Today they stagger.** Each card centers its own lines, so where the
  numbers sit follows how many lines each card holds. Measured on the
  maintainer's stats at 3840, 2560 and 1920 px, the three numbers' tops were
  11.2 px apart with a benchmark selected, 19.3 px apart without one, and
  23.4 px with too few runs for a typical score. Proposed, they were 0 px
  apart in all five mocked states, both themes, at all three widths.
- **The row keeps its height:** 141.4 px at those widths, as today.
- **At 1536 px** Scenario Stats and the PB card wrap to the next line, as
  today, and line up with each other there; the Latest Run card, on the first
  line, can't line up with them.
- **The Latest Run card's minimum height** still holds its tallest state, so
  no run makes the page jump. In the wide layout every line fits on one, so
  the row's 141.4 px holds every state: the longest comparison, by pace with
  an old value's clock, measures about 359 px and the longest session line
  380 px, against 474 px. In the narrow layout (page areas of 900 px or less,
  where the card can be 380 px wide and a line has about 355 px) both can
  wrap: the comparison by pace with the clock, and the session line for an
  older year's session with a two-digit run number, such as
  `Run 12 (Jul 20, 2020, 11:47 PM session) · Time on this scenario unknown`.
  With both on two lines the card measured 164 px on the mockup in review,
  and the floor keeps 12 px below the last line, so about 176 px there. That
  floor is set in the narrow layout alone, under the page's container query
  at 900 px or less: the wide layout keeps today's floor, since a higher one
  would raise the whole row. The implementation measures it.

## Problem

### What the cards show today

The top row's score cards are, in order, Typical score (Scenario Stats), PB
and Latest run ([run_history.md](../specs/run_history.md#the-top-row)).

- **Latest run** ([spec](../specs/run_history.md#the-latest-run-card)):
  `Latest run · {age} · {scenario}`; the score with one badge; `{pct}% of PB ·
  Accuracy {accuracy}%`, or the gain over the previous best on a new PB;
  `Run {n} this session`; `{duration} on this scenario`. Its lines are
  centered in a card at least 135 px tall.
- **PB** ([spec](../specs/run_history.md#the-pb-card)): `PB · set {age}`; the
  score with its rank badge on a benchmark; the next rank; the leaderboard
  line; `{cm/360} cm/360 · Accuracy {accuracy}%`, quiet. Lines centered.
- **Typical score** ([spec](../specs/run_history.md#scenario-stats)):
  `Typical score` with a help icon and a recency readout; the typical score;
  `Category:` on a benchmark; `Total runs:`. Lines centered.

### Why now

The typical score shipped on 2026-10-21. The Latest Run card's lines were set
on 2026-10-12 and 2026-10-18, before it existed, so the card next to the
typical score never uses it.
A design review of the card on 2026-10-24 found, on the maintainer's own
stats: the comparison only with the PB (SC1); the scenario's name three times
on screen (SC2); the run's accuracy at full weight where the PB's is quiet,
and two quiet lines for one session (SC3); the three numbers at three
heights (SC4).

### Verified facts

- `build_typical_scores` in `source/kovaaks/typical_score.py` returns the
  typical score after each run of one scenario, in play order, from one
  snapshot of the store and its sessions. The value as it stood when a
  session began is the one after the scenario's last run before that session.
- `typical_score_recency` judges a value at any moment, so recency at the
  session's start is the same rule judged then.
- `latest_run` in `source/components/latest_run_card.py` already holds the
  run's chased PB and its pace constant (`what_runs_chased`).
  `personal_best_cm360` in `source/kovaaks/playlist_scenarios_service.py`
  reads any run's cm/360, and the PB card's `_faded_line` words it.
- The mocked numbers come from the app's own functions run on the
  maintainer's stats (9,228 runs on 2026-10-24), with the store cut off at a
  run and the clock set 90 s after it for the four "just played" states, and
  every run with the real clock for the lookup. The mockup's today's cards
  matched the live page's line positions to the tenth of a pixel at 2560 px.
- Line widths, measured on 2026-10-25 in the card's own fonts on the mockup,
  against the wide card's 474 px: `12.3% slower than typical at session start
  · 98.0% of PB pace` is 342 px at 13 px, before an old value's clock; a new
  PB's gain with the phrase is 438 to 469 px by score and 504 px by pace;
  `Run 12 (Jul 20, 2020, 11:47 PM session) · Time on this scenario unknown`
  is 380 px at 12 px.

### Not checked

- **The narrowest card's tallest state** on the app. It was measured on the
  mockup in review; SC4's floor adds 12 px to that.
- **What a screen reader says** for the phrase, its `Not recent` words and
  its hover.
- **Firefox.** The mockup was measured in headless Edge.

## Design

### What the player sees

The below-threshold state, VT Controlsphere Viscose on Viscose Benchmark S2
Medium, 90 s after the run:

| Card | Today | Proposed |
|---|---|---|
| Typical score | `Typical score` / `2,999` / `Category: Control Tracking · Wrist` / `Total runs: 147` | the same lines, from the top, 2 px apart |
| PB | `PB · set 6 days ago` / `3,653` [Cerulean] / next rank / leaderboard / `50 cm/360 · Accuracy 60.87%` | the same lines, from the top, the last in the readable grey |
| Latest run | `Latest run · 1 minute ago · VT Controlsphere Viscose` / `3,133` [Below threshold] / `85.8% of PB · Accuracy 52.21%` / `Run 7 this session` / `9 min on this scenario` | `Latest run · 1 minute ago` / `3,133` [Below threshold] / `3.6% above typical at session start · 85.8% of PB` / `Run 7 this session · 9 min on this scenario` / `50 cm/360 · Accuracy 52.21%`, the last two in the readable grey |

That session's start value was recent. On the lookup, where it wasn't, the
line reads `5.8% below typical at session start` followed by the clock, then
`· 89.1% of PB`.

### The Latest Run card's lines

1. `Latest run · {age}`, quiet, the age's hover and focus unchanged.
2. The score and its one badge, unchanged.
3. The comparison line, at today's 13 px weight:
   - not a new PB: `{typical phrase} · {pct}% of PB`, or `of PB pace`;
   - a new PB: today's gain alone;
   - a part with nothing to say is left out, and with neither part the line
     is absent (a scenario's first run).
4. The session line, quiet: today's run words, `·`, today's time words.
5. The last line, quiet: `{cm/360} cm/360 · Accuracy {accuracy}%`, or
   `Accuracy {accuracy}%` where the run's cm/360 is unknown, as the PB card
   words its own.

The quiet lines 4 and 5, and the PB card's last line, are 12 px in the
scenario table's readable grey (`#676d75` light, `#a6a6a6` dark). Line 1 and
the PB card's first line keep today's grey.

### The typical phrase

- **The value:** the scenario's typical score after its last run before the
  run's session began, built from the same copy of the store as the card's
  run. Unknown before the session (too few runs, or no earlier run): no
  phrase.
- **Only on a run that isn't a new PB** (SC1).
- **The percentage:** `(score − typical) / typical × 100` to one decimal,
  `above` when positive and `below` when negative; `Matches typical at
  session start` when it rounds to 0.0. A typical score of zero or less on
  score math has no phrase.
- **By pace,** under SC1's condition, which is decided apart from the PB
  comparison's measure: `((C − typical) / (C − score) − 1) × 100`, `faster`
  when positive and `slower` when negative, the run toast's formula.
- **An old value,** judged at the session's start by the typical score's
  recency rule: the scenario table's 13 px history clock after the phrase,
  hidden from assistive technology, and `Not recent` after the phrase for a
  screen reader, as the table's old cells have. The clock sits inside the
  phrase's hover target, so hovering or focusing it opens the phrase's
  hover; the table's clock has no tooltip of its own, and the card doesn't
  follow it there.
- **The hover,** by mouse and keyboard, as the card's age has one: `Typical
  score when this run's session began: {typical}`, and on an old value a
  second line.
- **Written** when the card is, from the store, never from the run's
  message. A run later in the same session never moves it.

### Lining the cards up

- All three cards start their lines 12 px below their frame's top, with 2 px
  between lines; Scenario Stats gains the 2 px gap the other two have.
- They still stretch to their line's height; spare room is at the bottom.
- The Latest Run card's minimum height holds its tallest state with 12 px
  below its last line: in the wide layout today's floor, inside the row's
  141.4 px, and in the narrow layout alone, under the page's container query
  at 900 px or less, about 176 px, measured at 380 px wide (SC4). The other
  cards' floors are unchanged.
- The narrow layout keeps its order and wrapping; each card's lines start
  from its top there too.

### Copy

Every string this proposal adds or edits. The rest of the cards are
unchanged.

**Latest Run card:**
- First line: `Latest run · {age}`.
- The typical phrase: `{pct}% above typical at session start`, `{pct}%
  below typical at session start`, `Matches typical at session start`; by
  pace `{pct}% faster than typical at session start`, `{pct}% slower than
  typical at session start`.
- The comparison line: `{typical phrase} · {pct}% of PB`, `{typical phrase}
  · {pct}% of PB pace`. A new PB's line is today's gain, unchanged.
- An old value: `Not recent` after the phrase, for screen readers only, the
  scenario table's words.
- The phrase's hover: `Typical score when this run's session began:
  {typical}`, and on an old value `Fewer than 10 of its runs were from the 30
  days before the session began, so it may have been out of date.`
- The session line: `Run {n} this session · {duration} on this scenario`,
  `Run {n} last session · {duration} on this scenario`, `Run {n} ({session}
  session) · {duration} on this scenario`, and each with `Time on this
  scenario unknown` after the dot in place of the time.
- The last line: `{cm/360} cm/360 · Accuracy {accuracy}%`, or `Accuracy
  {accuracy}%`.

New to the app: the typical phrase and its hover. `Not recent` is the
scenario table's. The rest is today's wording rearranged.

### Terms

For [docs/glossary.md](../glossary.md), under Scores and notifications:

**Typical at session start.** The typical score as it stood when a session
began: the value after the scenario's last run before that session. The
Latest Run card measures a run against it, so every run of a session meets
the same value, and a run never meets a value it helped make. Unknown when
the scenario had no known typical score before the session. Its recency is
judged at the session's start, not when the card is read.
- On screen: the Latest Run card's `3.6% above typical at session start`,
  with the value in its hover, and a clock after it when the value wasn't
  recent.
- Not the Typical score card's value, which follows every run.

The **Recent** entry gains the card: on the Latest Run card, a typical score
at session start that wasn't recent then has a clock after its phrase and
`Not recent` for a screen reader. The **Latest-run card** entry loses the
scenario's name from its first line (SC2), and the **Pace** entry gains the
phrase among the places `faster` appears (SC1).

### Decisions this changes

- [2026-10-12, a past run's check](../decision_log/2026/2026-10-12-a-past-runs-check-is-judged-against-the-pb-it-was-chasing-under-its-own-version.md):
  its second line, the PB comparison then accuracy, gains SC1's phrase and
  loses the accuracy (SC1, SC3). Superseded in part.
- [2026-10-18, the card follows the selection](../decision_log/2026/2026-10-18-the-latest-run-card-reports-the-selected-scenarios-latest-run.md):
  the scenario's name on the first line (SC2), the time on the scenario on a
  line of its own (SC3), and the lines centered at least 135 px (SC4).
  Superseded in part.
- [2026-10-18, the heading line](../decision_log/2026/2026-10-18-the-run-lists-heading-line-is-for-screen-readers-only.md):
  its reason, the card naming its scenario above the list, is replaced
  (SC2); the line stays as it is.
- [2026-10-20, Scenario Stats leads with the typical score](../decision_log/2026/2026-10-20-scenario-stats-leads-with-the-typical-score.md):
  the card's lines centered (SC4). Superseded in part.
- Applied, not changed: the
  [2026-10-14 rule on a card's lines](../decision_log/2026/2026-10-14-a-cards-lines-follow-their-role-in-the-players-next-action.md)
  (SC3), which quotes `Latest run · {age} · {scenario}` as its example of an
  age and takes a dated note for SC2; the
  [2026-10-04 principles](../decision_log/2026/2026-10-04-skill-is-judged-by-the-typical-run-with-honest-uncertainty-in-verdicts-not-advice.md)
  (SC1 chooses its evidence bar); the
  [typical score drawn after each run](../decision_log/2026/2026-10-18-the-typical-score-is-drawn-after-each-run.md)
  (SC1 is the comparison its session freeze was kept for); and the
  [scenario table's old-value mark](../decision_log/2026/2026-10-22-an-old-typical-value-on-the-table-is-marked-with-a-clock-in-a-readable-grey.md)
  (SC1 reuses its clock and words, SC3 its readable grey).

The PB card's "lines are centered" in the spec has no governing entry; SC4
changes it with the others.

### Alternatives rejected

- **Comparing with the Typical score card's value** (the author's first
  recommendation). It agrees with the number beside it, but it moves after
  every run, includes the run being judged, and gives the runs of one session
  different yardsticks. The maintainer chose the session start.
- **Comparing with the value just before the run.** It never includes the
  run, but it moves after every run, and it matches neither the card nor the
  session.
- **The phrase without its basis,** `3.6% above typical` (the first draft).
  Beside a Typical score card showing another value, the reading depended on
  the hover, and its direction could disagree with that card.
- **The old-value flag in the hover only** (the first draft). The scenario
  table's evidence bar, which SC1 adopts, rests on a mark where the value is
  shown.
- **`Not recent at session start` for a screen reader.** The phrase already
  ends `at session start`, so the table's `Not recent` reads the same and
  adds no new words.
- **Keeping the phrase on a new PB,** after the gain. It could never report
  a deficit there, and its longest forms would wrap the line in the wide
  layout, making the row taller on those runs.
- **The short, unnamed phrase on a new PB alone,** `Up 4.3% on your
  previous best of 3,021 · 17.4% above typical`. It fits (the pace form at
  about 409 px), but it would put an unnamed basis back on the card, which
  the wave asked to remove.
- **The typical phrase on a line of its own.** Six lines don't fit the row's
  141 px with the card's padding.
- **The quiet lines in today's grey.** At 3.32:1 light and 4.04:1 dark it is
  under 4.5:1, and the run's accuracy would move into it.
- **Keeping the cards centered and tuning line counts,** as the session
  details' second line did: it lines the numbers up in one PB card state
  only.
- **A rank for the latest run.** KovaaK's ranks the PB. A run that beats the
  PB's rank is a new PB, so the PB card's badge already moves and the
  celebration plays; otherwise the comparison line and the chart's rank
  lines say how the run went. It would also be a second badge beside the
  score, which has one by the 2026-10-12 rule.

## Out of scope

- **The verdict badges' contrast** in light mode (`New PB` 1.75:1, `Threshold
  passed` 2.17:1, `Below threshold` 3.01:1, against 4.5:1 needed). A defect
  with a settled fix, shipped in its own pull request,
  [#429](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/429):
  the badges now draw as the PB card's rank badge does.
- **The typical score's rank on the Typical score card,** as a badge like the
  PB's. It gets a proposal of its own.
- **The typical comparison anywhere else:** the run list, the run toast, the
  chart's tooltips, the scenario table.
- **A "Reached {rank}" line** when a new PB reaches a new rank.
- **The Typical score card's `Category:` and `Total runs:` style,** set on
  2026-10-20, and its dimmed grey's contrast.
- **The empty states** of all three cards.

## Delivery plan

Stated intent, not a contract; a PR that moves a boundary says so in its
description.

- **Already shipped: the badge contrast fix,**
  [#429](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/429).
  PR 1 starts from it.
- **PR 1, gated on SC2, SC3 and SC4:** the Latest Run card's first line, its
  session and last lines, the readable grey on the quiet lines, and the
  three cards lined up from the top; the card's new minimum height measured;
  the spec, decision-log entries for SC2 to SC4 superseding the entries
  above, the dated note on the 2026-10-14 entry, and the glossary's
  Latest-run card entry. The comparison line keeps today's PB comparison,
  without accuracy.
- **PR 2, gated on SC1, after PR 1:** the typical score at session start,
  the phrase with its old-value mark and its hover, and the pace rule; the
  typical score spec, the glossary (the new term, Recent, Pace), a
  decision-log entry for SC1, and the rest of the shipping checklist,
  deleting this proposal. PR 2 measures the minimum height again with the
  phrase.
- **Why two, in order.** PR 1 changes no figure, only where they sit. PR 2
  carries the new computations and the rules a reviewer must check, and it
  writes into the comparison line PR 1 reshapes, so it starts from PR 1.

## Testing

- **Unit, PR 1:** the first line's words with and without a run; the
  comparison line without accuracy in each of today's forms; the session
  line joined, with each session form and the unknown time; the last line
  with and without a cm/360; the stylesheet's top alignment, the 2 px gap in
  all three cards, and the readable grey on the quiet lines.
- **Unit, PR 2:** the session-start value is the one after the scenario's last
  run before the session, the same for every run of the session, unknown for
  a first session and for too few runs before it; the phrase's rounding,
  `Matches typical at session start`, both signs; no phrase on a new PB; pace
  decided apart from the PB comparison, on one version and with score math on
  mixed versions; the old-value mark and hover line, judged at the session's
  start, on an old and a recent value.
- **Browser** (headless Edge, then the maintainer's Firefox), on the mocked
  states, both themes, at 3840, 2560, 1920 and 1536 px: the three first lines
  share a top and the three numbers share a top; the row's height is
  unchanged; nothing overflows. Also a page area of 900 px or less with the
  card at 380 px, holding the tallest state: an older year's session with a
  two-digit run number and an unknown time, and the longest pace phrase on an
  old value. The quiet lines measure at least 4.5:1 in both themes.
- **Screen reader** (NVDA, in the maintainer's Firefox): the typical phrase
  and its `Not recent` read as written, its hover is reachable from the
  keyboard, and the card reads acceptably without the scenario's name.
- **Gates:** pytest, ruff format and lint, mypy, compileall, as AGENTS.md
  lists.
