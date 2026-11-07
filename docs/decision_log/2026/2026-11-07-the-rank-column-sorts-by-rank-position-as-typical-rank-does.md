# 2026-11-07: The Rank Column Sorts By Rank Position, As Typical Rank Does

Status: Accepted

Sorting the Rank column now orders the scenarios that share a rank by how far
each personal best sits toward the next rank. Before, they tied on the rank
and stayed in playlist order, so the sort couldn't tell a scenario that has
just reached a rank from one about to pass it. The key is the rank position
that Typical Rank already sorts by, measured from the personal best instead
of the typical score.

**Maintainer direction, 2026-11-07.** Typical Rank's PR left Rank sorting by
the rank alone, and vault Backlog Features item 10 held the same position for
Rank as a change that needs its own decision. The maintainer said "all" to
building it on 2026-11-07, to see it. Current behavior is in
[playlists.md](../../specs/playlists.md#the-per-playlist-scenario-table).

**The key** is Typical Rank's own `rank_position`, given the PB, and never
rounded:

- **Ranked:** the ranks passed, from the ladder walk, plus `(PB - last
  passed threshold) / (next threshold - last passed threshold)`, at least 0
  and below 1, on ladders that tie or dip too.
- **Below the first rank:** `1 / (1 + gap / 100)`, `gap` being Next Rank's
  own unrounded gap, by pace where it applies. With no gap, a PB of zero or
  less on score math, the key is 0. It is always below 1, so the row sorts
  under every ranked row.
- **At the top rank:** the rank count.
- **No PB, or no ladder:** null, last in both directions, as before.

Why the position orders a rank's scenarios by weakness, and what it assumes
about a benchmark's ladders, is in the
[2026-10-22 entry](2026-10-22-typical-rank-sorts-by-rank-position-and-reads-the-rank-and-a-percent.md).

**What moves.** Every row keeps its rank, and the key's whole part is the
ranks passed, so rows on different ranks keep their order. Rows on one rank
now order by the fraction, where they kept playlist order. So do rows below
the first rank, which all keyed 0 before: a PB nearer the first rank sorts
above one farther from it. Below the first rank the key follows Next Rank's
gap, so a time-scored row whose PB can be measured by pace sorts by time
there, as Typical Rank's does. Between two thresholds the fraction is the
same in score or in time, so pace moves nothing from the first rank up.

**The cell tooltip.** Rank's tooltip still shows only from the first rank
up. Its test is `tier_sort >= 1`, since a below-first key is above 0 and a
plain truthiness test would give No rank a tooltip.

**Not changed:** Rank's cell, Next Rank, the PB card's badge, the field name
`tier_sort`, and the `?sort=rank` name, so a saved link opens the new order.

**Rejected:** breaking a rank's ties by Next Rank's gap, which Next Rank's own
column already sorts by, and which puts a rank's newest arrivals last, since
a scenario that has just reached a rank is the farthest from the next.
