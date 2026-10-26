# 2026-10-25: The Latest-Run Card Measures The Run Against The Typical Score At Session Start

Status: Accepted

The latest-run card's comparison line now says how far the run was from the
scenario's typical score as it stood when the run's session began, before
its percentage of the PB. Measured against the PB alone almost every run read
as a miss, while this app judges skill by the typical run. Every run of a
session meets the same value, a clock marks one that wasn't recent then, and
a new PB keeps its gain alone.

**Ruling and delivery.** SC1 of the Run History score cards proposal,
[#430](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/430),
ratified by the maintainer on 2026-10-25 at `c77ad06`: "I ratify the proposal
on PR #430 at c77ad06.", as amended in review: the first review wave kept the
basis and the evidence bar, and asked that the basis be named on screen and
an old value be marked on the card, not only in the hover. Before it, the
maintainer's lean of 2026-10-24: "Use the typical score at session start for
the comparison." The author had recommended the Typical score card's own
value. Leaving the phrase off a new PB is the author's. Built in
[#434](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/434),
the proposal's second and last delivery PR, after
[#431](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/431).
Current behavior is in
[run_history.md](../../specs/run_history.md#the-latest-run-card) and
[typical_score.md](../../specs/typical_score.md#api-and-snapshot-ownership).

**Why.**

- **The PB alone reads almost every run as a miss.** On 2026-10-16 the
  maintainer's VT Controlsphere Viscose run of 3,133 read `85.8% of PB` and
  "Below threshold" at the default 95%. It was 3.6% above their typical score
  at the start of that session, a good run, and nothing on the card said so.
  [The 2026-10-04 principles](2026-10-04-skill-is-judged-by-the-typical-run-with-honest-uncertainty-in-verdicts-not-advice.md)
  judge skill by the typical run and keep the PB as the achievement.
- **Why the session start.**
  [The typical score drawn after each run](2026-10-18-the-typical-score-is-drawn-after-each-run.md)
  kept "the per-session freeze" for "later comparisons", and this is the
  first. A frozen value gives every run of a session the same yardstick, so
  run 1 and run 8 compare with each other, and it never includes the run
  being judged or the runs just before it.
- **Its cost.** The Typical score card shows the value after the newest run,
  so on a good session the two drift apart, and the direction can disagree.
  On the maintainer's Flower 50cm session the phrase read `7.5% above typical
  at session start` against 2,684 while the card beside it showed 2,778. The
  phrase names its basis and its hover names the value, so the two can be
  reconciled.
- **The basis is named on screen** because the at-a-glance reading must not
  depend on a hover, and `above typical` beside a different typical score
  could read as wrong.
- **The evidence bar** is the scenario table's
  ([2026-10-22](2026-10-22-every-known-typical-score-gets-a-typical-rank-old-or-not.md)):
  a known value counts at any age, on the condition that the qualification
  reaches every reader, so an old value is marked where it is shown, with the
  table's clock and `Not recent`
  ([2026-10-22](2026-10-22-an-old-typical-value-on-the-table-is-marked-with-a-clock-in-a-readable-grey.md)).
  Three of the proposal's four mocked states compared against a value that
  wasn't recent when the session began, and the Typical score card beside
  them could look current by then, so it can't serve as the warning.
- **No phrase on a new PB.** A new PB scores above every earlier run, and the
  value is a median of earlier runs, so the phrase could only read `above`,
  or `Matches` where a tiny gain rounds to 0.0%. The PB gain already says how
  far the run went. Its longest forms would also wrap the wide card's line.

**The rule.**

- **The value** is the scenario's typical score after its last run before the
  run's session began, from the same copy of the run store as the card's run,
  with the sessions split from every run. No run before the session, or an
  unknown value there: no phrase. A run later in the session never moves it.
  It is written when the card is, never from a run's message.
- **The line** is `{typical phrase} · {pct}% of PB`, or `of PB pace`. A part
  with nothing to say is left out, and with neither the line is absent.
- **By score:** `(score − typical) / typical × 100` to one decimal,
  `{pct}% above typical at session start` or `{pct}% below typical at session
  start`, `Matches typical at session start` where it rounds to 0.0. A
  typical score of zero or less has no phrase.
- **By pace,** when every run behind the value is of the run's version, a
  performance file answers for that version, and both times are positive, as
  the scenario table's Typical Rank decides it: the run toast's
  `percent_faster`, `{pct}% faster than typical at session start` or `{pct}%
  slower than typical at session start`. That is decided apart from the PB
  part's measure, so one line can mix them, and the words name each. Times
  that aren't positive fall back to score math.
- **An old value,** judged at the session's start by the typical score's
  recency rule, has the table's 13 px history clock after the phrase, hidden
  from assistive technology, then `, Not recent` for a screen reader, as the
  table's cells read. The clock sits inside the phrase's hover target.
- **The hover,** by mouse and keyboard as the card's age has one:
  `Typical score when this run's session began: {typical}`, the value
  formatted as the table formats it, and on an old value a second paragraph,
  `Fewer than 10 of its runs were from the 30 days before the session began,
  so it may have been out of date.` It is at most 360 px wide.

**In the code.** `typical_score_at_session_start` in
`source/kovaaks/typical_score.py` builds the value from the scenario's runs
before the session only, since a value depends only on the runs before it.
`LatestRun` holds `typical`, a `TypicalPhrase` (`text`, `typical`,
`not_recent`) or `None`, and `pb_comparison`, the old `comparison` renamed,
since the line now joins two parts. `_typical_target` draws the phrase in a
`dmc.Tooltip` with the age's inline wrapper class. `NOT_RECENT_TEXT` moved
from the scenario table's page module to `typical_score.py`, because a
component must not import a Dash Pages module.

**The narrow floor.** In a page area of 900 px or less, at the card's 380 px
minimum, the tallest state is now the comparison by pace with an old value's
clock on two lines, over an older year's session with a two-digit run number
and an unknown time on two. Its lines take 151 px; with the top row's 12 px
above, 12 px below, and both borders, the floor is 177 px, where it was 158.
The proposal estimated about 176 px. The wide floor stays 135 px: the longest
comparison, `123.4% faster than typical at session start · 99.9% of PB pace`
with the clock, measures 361 px against the card's 474 px of text.

**Measured at the build,** against `main` at `ba8354b` on the maintainer's
stats, headless Edge, light and dark, at 3840, 2560, 1920 and 1536 px, with
and without a KovaaK's username, in seven states: VT Controlsphere Viscose on
Viscose Benchmark S2 Medium (3.6% above 3,025, recent), VT ww5t Intermediate
S5 on Voltaic Intermediate Benchmarks S5 (5.8% below 1,390, old), Flower 50cm
(a new PB), Air Pure Medium (7.1% faster than 908.84, old, by pace), Air
CELESTIAL No UFO Medium (2.1% faster than 883.34, recent, by pace), TSK - SYW
(too few runs before its session), and a scenario with too few runs for any
typical score.

| | `main` | This rule |
|---|---|---|
| Every card's height and top, and the row, in all 224 measurements | | the same as `main` in all 224 |
| The row from 1920 px up, with a username | 141.4 px | 141.4 px |
| The row at 1536 px, with a username | 285.4 px | 285.4 px |
| With no username: the row from 1920 px up | 143.4 px without a benchmark, 164.4 px with one | the same |
| With no username: the row at 1536 px | 296.8 px and 317.8 px | the same |
| The three first lines' and numbers' tops, apart, from 1920 px up | 0 px | 0 px |
| The longest comparison written into the wide card, at every width | | one line, 361 px, the row unchanged |
| The latest-run card in an 843 px page area | 158 px, 164.4 px with a benchmark and no username | 177 px in every state |
| The tallest state at 380 px | | lines 151 px, starting 12 px below the border with a username, so 12 px stay under them at 177 px |
| The phrase's hover | | opens by mouse, from the clock, and by Tab from the age, and closes on leaving; 327 to 336 px wide, 360 px with an old value's second paragraph |
| The card's text in the accessibility tree, on an old value by pace | | `7.1% faster than typical at session start`, `, Not recent`, ` · 98.0% of PB pace`, words apart |

The clock is drawn in the comparison line's own color, 21:1 light and 9.37:1
dark, and the quiet lines still measure 5.22:1 and 6.38:1. No card's content
overflows it in any state, and no page error was logged.

**Alternatives rejected.** Comparing with the Typical score card's value,
which moves after every run and includes the run being judged; comparing
with the value just before the run, which matches neither the card nor the
session; the phrase without its basis; the old-value flag in the hover only;
`Not recent at session start` for a screen reader, which the phrase's own
words already say; and the phrase on a new PB.

**What this changes in older entries.** Each keeps its text and gains a dated
note.

- [2026-10-12, a past run's check](2026-10-12-a-past-runs-check-is-judged-against-the-pb-it-was-chasing-under-its-own-version.md):
  the second line gains the typical phrase before the PB comparison.
- [2026-10-25, the card ends with the run's cm/360 and accuracy](2026-10-25-the-latest-run-card-ends-with-the-runs-cm360-and-accuracy.md):
  the comparison line holds the typical phrase as well as the PB comparison,
  and `LatestRun.comparison` is now `pb_comparison`.
- [2026-10-25, the three score cards line up from the top](2026-10-25-run-historys-three-score-cards-line-up-from-the-top.md):
  the narrow floor is 177 px.
- [The typical score drawn after each run](2026-10-18-the-typical-score-is-drawn-after-each-run.md):
  its per-session freeze has its first use here.

Applied, not changed: the
[2026-10-04 principles](2026-10-04-skill-is-judged-by-the-typical-run-with-honest-uncertainty-in-verdicts-not-advice.md),
whose evidence bar SC1 chooses, and the
[scenario table's old-value mark](2026-10-22-an-old-typical-value-on-the-table-is-marked-with-a-clock-in-a-readable-grey.md),
whose clock and words the card reuses.

The proposal file, `docs/proposals/run_history_score_cards_proposal.md`, is
deleted in #434, and git history keeps it.
