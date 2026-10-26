# 2026-10-25: Run History's Three Score Cards Line Up From The Top

Status: Accepted

Typical score, PB and Latest run now start their lines 12 px below their top
edge, 2 px apart, instead of centering them. Their first lines then share
one top and their large numbers another, and the offset only takes room the
row already has, so the row never grows for it. In a narrow window the latest-run card's minimum
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
  with `gap: 2px`, no `justify-content`, and no padding at the top or the
  bottom. Scenario Stats gains the 2 px gap the other two had.
- **The 12 px is a spacer, not padding.** Each card's `::before` is
  `flex: 1 1 0` with `max-height: var(--run-history-score-card-top)` and a
  `-2px` bottom margin that cancels the gap after it. Empty, it adds nothing
  to the card's height, so it never raises the row; it grows into the room
  the stretched card has, up to the offset. Padding did add to the height:
  whenever the PB card's leaderboard line wrapped, the card filled the row it
  made and 12 px of padding raised the row by up to 12 px, which the Codex
  seat found twice in review of #431 (with no username, and with a cached
  `Unranked (12,345 players) · from cache`).
- They still stretch to their line's height. A card with fewer lines leaves
  its spare room at its bottom.
- **While the leaderboard line shows a hint the offset is 0 for all three.**
  A hint is what wraps the line in most such states: the username hint
  always does, and a long position does with `from cache` or
  `lookup failed`. `--run-history-score-card-top` is set on the top row,
  12 px, and `.run-history-top-row:has(.pb-card .scenario-rank-hint)` sets it
  to 0, so the three cards stay lined up at their top edge, as the PB card's
  lines sat there on `main`.
- **The ruled exception.** A long position with no hint can wrap the line
  too: `Position: Unranked (123,456 players)` with a benchmark selected, for
  one. Then the PB card has less than 12 px of room and its lines start up to
  about 10 px higher than the other two cards'. The maintainer accepted this
  on 2026-10-25, when choosing this rule over a script that would measure the
  three cards and set one shared offset: "SOL-F2: use the CSS-only spacer
  plus the zero offset while a leaderboard hint shows. I accept that in rare
  states (a long Position value with a benchmark and no hint) the PB card's
  lines start up to ~10 px higher. Record it as a ruled exception." CSS alone
  can't give the three cards the smallest offset that fits, because they sit
  in different containers.
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
| With no username: the row, from 1920 px up | 143.4 px without a benchmark, 164.4 px with one | the same |
| With no username: the row at 1536 px | 296.8 px and 317.8 px | the same |
| With no username: the three numbers' tops, apart | 33.0 to 37.1 px | 0 px in every state |
| Every leaderboard text and hint written into the PB card, 36 cases at 1920 px | | the row as tall as with no offset in all 36; the cards lined up in 35, and in the ruled exception the PB card's lines 9.6 px higher |

The first five rows' measurements had the maintainer's username and a copy
of the leaderboard cache; the next three none. The last row wrote each of
six position forms, with no hint, `from cache` or `lookup failed`, into the
live card, on Flower 50cm and on VT Controlsphere Viscose with its
benchmark. No card's content overflows
it in any state. In a page area of 843 px, with a username, the card is
158 px tall in all four states, where it was 135.

**What this changes in older entries.** Each keeps its text and gains a dated
note.

- [2026-10-18, the card follows the selection](2026-10-18-the-latest-run-card-reports-the-selected-scenarios-latest-run.md):
  the card's lines centered in a height of at least 135 px in every layout.
- [2026-10-20, Scenario Stats leads with the typical score](2026-10-20-scenario-stats-leads-with-the-typical-score.md):
  the card's lines centered.
- The PB card's centered lines had no entry of their own.
