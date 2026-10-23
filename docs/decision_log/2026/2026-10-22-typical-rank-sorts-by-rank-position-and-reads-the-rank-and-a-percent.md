# 2026-10-22: Typical Rank Sorts By Rank Position And Reads The Rank And A Percent

Status: Accepted

The Typical Rank column shows the benchmark rank a scenario's typical score
reaches and how far it sits toward the next one, such as Celadon · 7%.
Sorting it lists the scenarios from weakest to strongest on the benchmark's
own rank ladder, which a score can't do across scenarios. The gap to the next
rank is in the cell's hover.

**Ruling.** TB2 of
[proposal #408](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/408),
ratified by the maintainer on 2026-10-22, as amended in review. Before that,
on what the table is for, the maintainer wanted to "Sort by weakness. Since
Score is not really comparable across scenarios", and proposed "numerical
steps": Bronze is 2.0, and 40% of the way to Silver is 2.4. On the format,
after trying three on the prototype: "I'm leaning toward 'Celadon 7%' option,
simply because it is more user friendly." The review wave amended the
below-first key (it followed a ratio of scores, which a time-scored
scenario's constant moves) and capped the percent at 99. Shipped in
[#414](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/414).

**The rank position**, the column's sort key, is computed from the exact
median and never rounded.

- **Ranked:** the ranks passed, from the table's own ladder walk, plus
  `(typical - last passed threshold) / (next threshold - last passed
  threshold)`. The walk stops at the first threshold above the score, so the
  fraction is at least 0 and below 1, on ladders that tie or dip too.
- **Below the first rank:** `1 / (1 + gap / 100)`, `gap` being the unrounded
  gap to the first rank by the Next Rank rule: by pace where it applies, a
  percentage of the score otherwise. With no gap, a score of zero or less on
  score math, the key is 0. It is always below 1, so the row sorts under every
  ranked row.
- **At the top rank:** the rank count.
- **Pace.** Between two thresholds the fraction is the same in score or in
  time, since a time-scored score is a constant minus the time. Below the
  first rank it isn't: with a 120-second typical run and a 100-second first
  rank, the ratio of scores is 0.98 at a constant of 1,000 and 0.8 at 200,
  either side of an ordinary row at 90 against 100, while the ratio of times
  is 0.83 for both. Pace applies when every run behind the typical score is
  of the version the constant was read from, and the hover's gap follows the
  same rule.

**The cell** reads `{rank} · {percent}%`, the rank's name alone at the top
rank, and `No rank` below the first rank, with no number: a displayed one
would rest on an invented floor. It reads `N/A` with Too few runs, with no
runs, and for a benchmark scenario without a ladder. The percent is
`min(99, floor(round(fraction * 100, 6)))`. The inner round strips float
noise, as the Next Rank gap's does, and the cap stops it carrying a score a
hair under the next threshold to 100. So no cell reads as the next rank, and
`0%` means on the threshold or just above it.

**The hover** is the gap to the next rank in Next Rank's figures,
`+{gap}% to {rank} · {points} to go`, or `+{gap}% faster to {rank} · {points}
to go` by pace. At the top rank there is none, as Next Rank's Top rank has
none.

**Why the position, not the gap.** A scenario that has just reached a rank is
the farthest from the next one, so sorting by the gap puts each rank's
weakest scenarios last. On Viscose Benchmark S2 Medium the 19 Celadon
scenarios order almost exactly opposite by gap and by position (Kendall tau
−0.88), and over the 31 ranks holding three or more scenarios across 23 of
the maintainer's benchmarks the mean is −0.68. The
[2026-09-27 rank columns](2026-09-27-benchmark-tables-show-each-scenarios-rank-and-the-gap-to-the-next-one.md)
set this fraction aside for Next Rank, whose question is the score to beat;
this column uses it for an order, which that decision did not weigh.

**Not checked.** The order assumes a benchmark's ranks mark the same level on
all its scenarios, as ranks are meant to. A scenario whose thresholds sit
harder or easier than the others' sorts weaker or stronger than it plays.

**Accepted cost.** The rank, the percent and the hover's points count from
the exact median, while the Typical Score cell shows it rounded half up: a
median of 78.5 shows 79 beside a hover reading `1.5 to go` against 80. The
maintainer: "We'll skip it for now and accept that discrepancy." The fix, if
ever wanted, belongs to the typical score's rounding, not to this column.

**Rejected:** `Celadon 4.07` and `4.07`, which sort the same; the maintainer
found the percent friendlier, and the ordinal changes meaning between
ladders. Measuring from the rounded value, to make the hover agree with the
cell, was declined as a workaround.
