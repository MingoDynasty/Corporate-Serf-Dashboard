# 2026-10-25: Run History's Three Score Cards Line Up From The Top

Status: Accepted

Typical score, PB and Latest run now start their lines 12 px below their top
edge, 2 px apart, instead of centering them. Their first lines then share
one top and their large numbers another, whatever each card holds, and the
row keeps its height. In a narrow window the latest-run card's minimum
height rises, so its tallest state still fits and the page doesn't jump
between runs.

**Ruling and delivery.** SC4 of the Run History score cards proposal,
[#430](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/430),
ratified by the maintainer on 2026-10-25 at `c77ad06`: "I ratify the proposal
on PR #430 at c77ad06." Before it, the maintainer's lean of 2026-10-25: "Keep
changes 2 to 5 as proposed: no scenario name, the rebalanced lines,
top-aligned cards, and readable badges." The first review wave endorsed the
row and corrected its narrow floor. Built in
[#431](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/431),
the proposal's first delivery PR. Current behavior is in
[run_history.md](../../specs/run_history.md#the-top-row).

**Why.** Each card centered its own lines, so where its large number sat
followed how many lines it held. On the maintainer's stats at 3840, 2560 and
1920 px, the three numbers' tops were 11.2 px apart with a benchmark
selected, 19.3 px without one, and 23.4 px with too few runs for a typical
score. Keeping the cards centered and tuning line counts, as the session
details' second line did, lines them up in one PB card state only.

**The rule.**

- `.scenario-stats-card`, `.pb-card` and `.run-history-card` are columns
  with `padding: 12px var(--mantine-spacing-sm) 0` and `gap: 2px`, and no
  `justify-content`. Scenario Stats gains the 2 px gap the other two had.
- They still stretch to their line's height. A card with fewer lines leaves
  its spare room at its bottom, where nothing pads it, so the row stays the
  height the dropdowns' column sets.
- At 1536 px Scenario Stats and the PB card wrap to their own line, as
  before, and line up with each other there. The latest-run card, on the
  first line, can't line up with them.

**The latest-run card's floor.** The card is never less than its tallest
state, so no run makes the page jump.

- In the wide layout every line fits on one, so the row's 141.4 px holds
  every state, and the floor stays 135 px. A higher one would raise the
  whole row.
- In the narrow layout alone, under
  `@container run-history-page (max-width: 900px)`, where the card can be
  380 px wide, the floor is 158 px. That holds the tallest state without
  SC1's phrase: the comparison on one line, over the session line on two (an
  older year's session with a two-digit run number and an unknown time,
  `Run 12 (Jul 20, 2020, 11:47 PM session) · Time on this scenario unknown`),
  with 12 px under the last line. Measured: the last line ends 145 px below
  the card's top, plus 12 px and the 1 px border.
- The proposal's second delivery PR raises the narrow floor for SC1's
  phrase, which can take the comparison line to two lines (the proposal
  estimated about 176 px).

**Measured at the build,** against `main` at `6edf1b0` on the maintainer's
stats, headless Edge, light and dark, at 3840, 2560, 1920 and 1536 px, in
four states: Flower 50cm with no filter, VT Controlsphere Viscose on Viscose
Benchmark S2 Medium, VT ww5t Intermediate S5 on Voltaic Intermediate
Benchmarks S5, and a scenario with too few runs for a typical score.

| | `main` | This rule |
|---|---|---|
| The three numbers' tops, apart, from 1920 px up | 11.2 px with a benchmark, 19.3 px without, 23.4 px with too few runs | 0 px in every state |
| The three first lines' tops, apart | 13.2 to 25.4 px | 0 px in every state |
| The row, from 1920 px up | 141.4 px | 141.4 px |
| The row at 1536 px | 285.4 px | 285.4 px |
| Scenario Stats' and the PB card's numbers at 1536 px | 10.8 to 14.9 px apart | 0 px |

No card's content overflows it in any state. In a page area of 843 px the
card is 158 px tall in all four states, where it was 135.

**What this changes in older entries.** Each keeps its text and gains a dated
note.

- [2026-10-18, the card follows the selection](2026-10-18-the-latest-run-card-reports-the-selected-scenarios-latest-run.md):
  the card's lines centered in a height of at least 135 px in every layout.
- [2026-10-20, Scenario Stats leads with the typical score](2026-10-20-scenario-stats-leads-with-the-typical-score.md):
  the card's lines centered.
- The PB card's centered lines had no entry of their own.
