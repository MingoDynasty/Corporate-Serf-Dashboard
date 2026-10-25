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

Four rows, SC1 to SC4. **Nothing is ratified.** Each row carries the
maintainer's lean from the design discussion of 2026-10-24 and 2026-10-25,
worked out on three versions of a mockup built from their own stats, with
today's cards behind a switch. A lean is not a ruling, and reviewers may
challenge any row, and anything in [Design](#design), which is author-owned.
Two more changes from the same discussion go elsewhere
([Out of scope](#out-of-scope)): the verdict badges' contrast in light mode,
a defect fix in its own pull request, and the typical score's rank on the
Typical score card, which gets a proposal of its own.

### SC1. The latest run is compared with the typical score at session start

Status: open. The maintainer's lean, 2026-10-24: "Use the typical score at
session start for the comparison." The author had recommended the Typical
score card's own value; see [Alternatives rejected](#alternatives-rejected).

The material consequence: the card gains a second comparison, and during a
session its percentage can differ from what the number on the Typical score
card beside it would give.

**Recommendation: the comparison line names the run's distance from the
typical score as it stood when the run's session began, `3.6% above typical`
or `5.8% below typical`, beside its percentage of the PB. On a new PB the PB
gain stays first. Every run of a session is measured against the same value.
A known value counts at any age, and the phrase's hover says when it was old;
with no known value the phrase is left out.**

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
  On a good session the two drift apart: the maintainer's new PB of 3,152 on
  Flower 50cm reads `17.4% above typical` against a session-start value of
  2,684, while the card beside it shows 2,847, from which the run is 10.7%
  above. The phrase's hover names the value it used, so the two can be
  reconciled.
- **The evidence bar.** The 2026-10-04 principles say a judgment that uses an
  old value must choose its evidence bar. This row chooses the scenario
  table's
  ([2026-10-22](../decision_log/2026/2026-10-22-every-known-typical-score-gets-a-typical-rank-old-or-not.md)):
  a known value counts at any age. Three of the four mocked states, on two
  scenarios, compare against a session-start value that wasn't recent when
  the session began (both Flower 50cm states, 8 of 16 runs recent; VT ww5t
  Intermediate S5, 0 of 20). The
  phrase's hover then adds that the value may have been out of date. A
  scenario with no known typical score before the session gets no phrase.
- **Time-scored scenarios** are compared by pace when the run's PB comparison
  is by pace and every run behind the typical value is of the run's version,
  as the scenario table's Typical Rank column decides it: `2.1% faster than
  typical`.

| Mocked state | Score | At session start | Typical card's value |
|---|---|---|---|
| Just played, new PB (Flower 50cm) | 3,152 | 2,684, +17.4% | 2,847, +10.7% |
| Just played, threshold passed (Flower 50cm) | 2,884 | 2,684, +7.5% | 2,778, +3.8% |
| Just played, below threshold (VT Controlsphere Viscose) | 3,133 | 3,025, +3.6% | 2,999, +4.5% |
| Looking up, 2 months later (VT ww5t Intermediate S5) | 1,310 | 1,390, −5.8% | 1,385, −5.4% |

### SC2. The card's first line drops the scenario's name

Status: open. The maintainer's lean, 2026-10-25: "Keep changes 2 to 5 as
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

### SC3. One comparison line, one session line, then cm/360 and accuracy

Status: open. The maintainer's lean, 2026-10-25, as quoted under SC2.

The material consequence: the card shows the run's sensitivity, and accuracy
moves from the comparison line to a quiet last line.

**Recommendation: under the score, three lines. The comparison line, at
today's weight, holds only comparisons (SC1's phrase and the PB comparison).
The session line puts today's two quiet lines on one: `Run 7 this session ·
9 min on this scenario`. The last line, in the same quiet style, is the run's
`50 cm/360 · Accuracy 52.21%`, the PB card's last line for the PB run.**

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

### SC4. The three score cards line up from the top

Status: open. The maintainer's lean, 2026-10-25, as quoted under SC2.

The material consequence: a card with fewer lines leaves its spare room at
its bottom instead of above and below its lines.

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
  no run makes the page jump. With SC1 and SC3 that state is its narrowest
  layout (380 px, page areas of 900 px or less) with the comparison line on
  two lines, about 147 px by arithmetic, and the implementation measures it.

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
- The longest comparison line seen on 2026-10-18 was 70 characters in 373 of
  the card's 474 px. A new PB's gain with SC1's phrase on a time-scored
  scenario, the longest form, is about 75 characters, which by that measure
  still fits one line at 500 px.

### Not checked

- **The narrowest card's tallest state,** at 380 px, measured. SC4 gives
  arithmetic only.
- **What a screen reader says** for the phrase and its hover.
- **Firefox.** The mockup was measured in headless Edge.

## Design

### What the player sees

The below-threshold state, VT Controlsphere Viscose on Viscose Benchmark S2
Medium, 90 s after the run:

| Card | Today | Proposed |
|---|---|---|
| Typical score | `Typical score` / `2,999` / `Category: Control Tracking · Wrist` / `Total runs: 147` | the same lines, from the top, 2 px apart |
| PB | `PB · set 6 days ago` / `3,653` [Cerulean] / next rank / leaderboard / `50 cm/360 · Accuracy 60.87%` | the same lines, from the top |
| Latest run | `Latest run · 1 minute ago · VT Controlsphere Viscose` / `3,133` [Below threshold] / `85.8% of PB · Accuracy 52.21%` / `Run 7 this session` / `9 min on this scenario` | `Latest run · 1 minute ago` / `3,133` [Below threshold] / `3.6% above typical · 85.8% of PB` / `Run 7 this session · 9 min on this scenario` / `50 cm/360 · Accuracy 52.21%` |

### The Latest Run card's lines

1. `Latest run · {age}`, quiet, the age's hover and focus unchanged.
2. The score and its one badge, unchanged.
3. The comparison line, at today's 13 px weight:
   - not a new PB: `{typical phrase} · {pct}% of PB`, or `of PB pace`;
   - a new PB: today's gain, then `· {typical phrase}`;
   - a part with nothing to say is left out, and with neither part the line
     is absent (a scenario's first run).
4. The session line, quiet: today's run words, `·`, today's time words.
5. The last line, quiet: `{cm/360} cm/360 · Accuracy {accuracy}%`, or
   `Accuracy {accuracy}%` where the run's cm/360 is unknown, as the PB card
   words its own.

### The typical phrase

- **The value:** the scenario's typical score after its last run before the
  run's session began, built from the same copy of the store as the card's
  run. Unknown before the session (too few runs, or no earlier run): no
  phrase.
- **The percentage:** `(score − typical) / typical × 100` to one decimal,
  `above` when positive and `below` when negative; `At typical` when it rounds
  to 0.0. A typical score of zero or less on score math has no phrase.
- **By pace,** under SC1's condition: `((C − typical) / (C − score) − 1) ×
  100`, `faster` when positive and `slower` when negative, the run toast's
  formula.
- **The hover,** by mouse and keyboard, as the card's age has one: `Typical
  score when this run's session began: {typical}`, and on a value that wasn't
  recent at that moment a second line.
- **Written** when the card is, from the store, never from the run's
  message. A run later in the same session never moves it.

### Lining the cards up

- All three cards start their lines 12 px below their frame's top, with 2 px
  between lines; Scenario Stats gains the 2 px gap the other two have.
- They still stretch to their line's height; spare room is at the bottom.
- The Latest Run card's minimum height is re-measured for its tallest state
  at 380 px wide (SC4). The other cards' floors are unchanged.
- The narrow layout keeps its order and wrapping; each card's lines start
  from its top there too.

### Copy

Every string this proposal adds or edits. The rest of the cards are
unchanged.

**Latest Run card:**
- First line: `Latest run · {age}`.
- The typical phrase: `{pct}% above typical`, `{pct}% below typical`, `At
  typical`; by pace `{pct}% faster than typical`, `{pct}% slower than
  typical`.
- The comparison line: `{typical phrase} · {pct}% of PB`, `{typical phrase}
  · {pct}% of PB pace`, `Up {pct}% on your previous best of {previous} ·
  {typical phrase}`, `{pct}% faster than your previous best of {previous} ·
  {typical phrase}`, `Your previous best was {previous} · {typical phrase}`.
- The phrase's hover: `Typical score when this run's session began:
  {typical}`, and on an old value `Fewer than 10 of its runs were from the 30
  days before the session began, so it may have been out of date.`
- The session line: `Run {n} this session · {duration} on this scenario`,
  `Run {n} last session · {duration} on this scenario`, `Run {n} ({session}
  session) · {duration} on this scenario`, and each with `Time on this
  scenario unknown` after the dot in place of the time.
- The last line: `{cm/360} cm/360 · Accuracy {accuracy}%`, or `Accuracy
  {accuracy}%`.

New to the app: the typical phrase and its hover. The rest is today's wording
rearranged.

### Terms

For [docs/glossary.md](../glossary.md), under Scores and notifications:

**Typical at session start.** The typical score as it stood when a session
began: the value after the scenario's last run before that session. The
Latest Run card measures a run against it, so every run of a session meets
the same value, and a run never meets a value it helped make. Unknown when
the scenario had no known typical score before the session.
- On screen: the Latest Run card's `3.6% above typical`, with the value in
  its hover.
- Not the Typical score card's value, which follows every run.

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
  (SC3), the
  [2026-10-04 principles](../decision_log/2026/2026-10-04-skill-is-judged-by-the-typical-run-with-honest-uncertainty-in-verdicts-not-advice.md)
  (SC1 chooses its evidence bar), and the
  [typical score drawn after each run](../decision_log/2026/2026-10-18-the-typical-score-is-drawn-after-each-run.md)
  (SC1 is the comparison its session freeze was kept for).

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
- **The typical phrase on a line of its own.** Six lines don't fit the row's
  141 px with the card's padding.
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
  with a settled fix, in its own pull request from its own kickoff.
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

- **Already split out: the badge contrast fix.** Independent of everything
  here. Where it and PR 1 both touch the card's badge, whichever merges second
  rebases.
- **PR 1, gated on SC2, SC3 and SC4:** the Latest Run card's first line, its
  session and last lines, and the three cards lined up from the top; the
  card's new minimum height measured; the spec, and decision-log entries for
  SC2 to SC4 superseding the entries above. The comparison line keeps today's
  PB comparison, without accuracy.
- **PR 2, gated on SC1, after PR 1:** the typical score at session start,
  and the phrase and its hover with the pace rule; the typical score spec,
  the glossary, a decision-log entry for SC1, and the rest of the shipping
  checklist, deleting this proposal.
- **Why two, in order.** PR 1 changes no figure, only where they sit. PR 2
  carries the new computations and the rules a reviewer must check, and it
  writes into the comparison line PR 1 reshapes, so it starts from PR 1.

## Testing

- **Unit, PR 1:** the first line's words with and without a run; the
  comparison line without accuracy in each of today's forms; the session
  line joined, with each session form and the unknown time; the last line
  with and without a cm/360; the stylesheet's top alignment and 2 px gap in
  all three cards.
- **Unit, PR 2:** the session-start value is the one after the scenario's last
  run before the session, the same for every run of the session, unknown for
  a first session and for too few runs before it; the phrase's rounding,
  `At typical`, both signs; pace on one version and score math on mixed
  versions; the new PB order; the old-value hover line, judged at the
  session's start.
- **Browser** (headless Edge, then the maintainer's Firefox), on the mocked
  states, both themes, at 3840, 2560, 1920 and 1536 px: the three first lines
  share a top and the three numbers share a top; the row's height is
  unchanged; nothing overflows; the narrowest card's tallest state fits its
  minimum height.
- **Screen reader** (NVDA, in the maintainer's Firefox): the typical phrase
  reads as written, and its hover is reachable from the keyboard.
- **Gates:** pytest, ruff format and lint, mypy, compileall, as AGENTS.md
  lists.
