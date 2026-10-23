# 2026-10-22: The Scenario Table Shows The Typical Score Beside The PB Columns

Status: Accepted

A playlist's scenario table now shows each scenario's typical score, and a
benchmark's table also shows the rank that score reaches. The two columns sit
after the PB columns, so a row compares the player's usual play with their
record at a glance. Every column that was there keeps reporting the PB.

**Ruling.** TB1 of
[proposal #408](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/408),
ratified by the maintainer on 2026-10-22: "I ratify the proposal." Their lean
before that, after comparing this layout with a PB / Typical switch on a live
prototype: "two columns, Typical Rank as Celadon · 7% sorted by rank position
with the gap in its hover, no Typical Next Rank column." Shipped in
[#414](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/414).
What the table does today is in
[playlists.md](../../specs/playlists.md#the-per-playlist-scenario-table).

**The layout.**

- **Placement.** A benchmark's table reads PB Score, Rank, Next Rank, Typical
  Score, Typical Rank. A playlist's has no ranks, so it gains Typical Score
  alone, after PB Score.
- **Shown by default, listed in the Columns menu** as `Typical score` and
  `Typical rank`, in table order. The menu keys a stored choice by column ID,
  so the IDs `typical_score_sort` and `typical_tier_sort` are fixed.
- **Sort names** `typical-score` and `typical-rank`. On a playlist's table
  `typical-rank` names no column, so a value holding it is not valid there, as
  `rank` is not.
- **Nothing is amended.** Rank, Next Rank, Position and Percentile keep the
  PB, as the
  [2026-10-04 principles](2026-10-04-skill-is-judged-by-the-typical-run-with-honest-uncertainty-in-verdicts-not-advice.md)
  say, and a link that carries a sort keeps meaning the same sort.

**One snapshot per table build.** The values come from one copy of the run
store, split into play sessions once, as Scenario Stats takes one, and
recency is judged at the moment the copy was taken. The page takes it once
and hands it to phase 1, to the fill, and to a cancelled fill's rebuild, so
every row path gives a scenario the same typical cells. Like PB Score, the
cells don't change when a run lands until the page reopens, and a table left
open can disagree with Run History's card, which updates every 30 seconds.
Measured on the maintainer's store: about 35 ms to split the store and 69 ms
to build a 39-scenario benchmark's values.

**Width.** A benchmark's table is about 320 px wider: Typical Score measured
163 px and Typical Rank 159 px, as wide as their headers. At 2560 px both
fit with no sideways scroll, the Scenario column narrowing from 400 to 333
px; at 1920 px the table already scrolled, by 587 px now, and the Columns
menu hides what a player never reads (Edge and Firefox, Viscose Benchmark S2
Medium, 2026-10-22).

**Rejected.**

- **A PB / Typical switch that changed PB Score, Rank and Next Rank in
  place,** the maintainer's first request. It showed one basis at a time, so
  the per-row comparison took a flip and a memory; it needed a held-order
  sort and a cleared address; and a copied sort link would sort differently
  in a browser on the other basis, against the
  [2026-09-27 rule](2026-09-27-the-playlist-scenario-table-keeps-its-sort-in-the-page-url.md)
  that a copied link keeps its sort.
- **A third column for the typical Next Rank gap.** Its figure is in the
  Typical Rank hover; as a column it would scroll the table by 152 px at
  2560. An optional, hidden one is on the backlog, never as a weakness sort
  ([the Typical Rank entry](2026-10-22-typical-rank-sorts-by-rank-position-and-reads-the-rank-and-a-percent.md)
  says why).
