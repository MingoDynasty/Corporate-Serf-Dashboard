# 2026-09-27: Benchmark Tables Show Each Scenario's Rank And The Gap To The Next One

Status: Accepted

A benchmark's scenario table now shows the rank each scenario's personal best
has reached, and how much that personal best has to grow, as a percentage, to
reach the next rank. Sorting the gap ascending lists the scenarios closest to
ranking up, a question that used to send the player to Evxl. Both columns come
from the bundled rank thresholds and the local personal best, so they appear
the moment the table opens and work offline. A plain playlist's table is
unchanged.

**Ruling.** Ratified (user) 2026-09-27 as a whole, after two review waves on
the proposal (PR #320, merged as `9dbf05a`; rulings recorded at `42488b9`).
Its two decision rows, D1 and D2, are below, each with the alternatives it
rejected. Everything else was author-owned and reviewed.

**D1: the gap is a percentage of the PB.** `(next threshold - PB) / PB * 100`,
computed only when the PB is above zero. It is defined below the first rank,
where no lower threshold exists, so every No rank row gets a real number; it
states the target to beat; and it matches the Scenario Performance score
threshold, which is also a percentage of the PB. It is scale-free, so
thresholds from 1 to 1,630,000 share one column, but it is not
difficulty-normalized: every percent counts the same, so a compressed score
scale always looks closer. The honest cost is against the rejected band
fraction (how far the PB sits through its current band, KovaaK's own
progress idea). Band widths vary, a median +8.3% of the lower threshold (p10
+3.5%, p90 +18.9%) across the corpus's 23,791 strictly ascending bands, about
as much across scenarios as within a ladder. A simulation that placed a
player in the same band on every scenario of a benchmark found the two
metrics pick a different closest scenario in 22% of 40,920 trials, median
Kendall τ 0.74 between their orders. What decided it is the first rank: a band
fraction needs an invented floor there, and 4,380 of 4,384 ladders start
above zero. Also rejected: the PB as a percentage of the next threshold (same
order, but the closest rows sort descending and it reads as progress rather
than a target), and points needed (the roadmap's "+47 to Gold"), which can't
be compared across score scales and so lives in the cell tooltip instead.

**D2: the PB is the local all-time high.** `ScenarioStats.high_score`, the
row's own PB Score, so a row agrees with itself, fills with no username and
before the fill, and follows KovaaK's rule that a rank is the best score ever
set. Rejected: the leaderboard score the position lookup returns, which
arrives only in the fill, is absent with no username or a failed lookup, and
can disagree with PB Score beside it; and recent form, which needs a window
decision of its own and would disagree with the rank KovaaK's shows. Recent
form is deferred to the own-runs difficulty follow-up on the roadmap.

**The ladder walk.** Walk from the bottom and stop at the first threshold
above the PB; a PB equal to a threshold has reached it. The last rank passed
is Rank (none passed: "No rank"), and the rank the walk stopped at is the
next rank (every rank passed: "Top rank"). The ladder keeps its stored order
and is never sorted. At `ea5b757` the corpus held 4,384 ladders: 4,367
strictly ascending, 7 with a tie (a ladder ending `142, 142`), 10
non-monotonic (an early dip `36, 54, 50, …`, a mid dip `2800, 2850, 2900,
2950, 2900, …`, a final descent `…, 2000, 1933`), and 4 with a zero threshold
(`0, 250, …`, `0, 0, 0, 0`). These are upstream data errors the importer
carries faithfully. The walk never grants a rank whose own threshold, or any
threshold below it on the ladder, is unmet, and the next threshold is always
above the PB, so every gap and every tooltip's points are positive. Rejected:
the last rank whose threshold the PB beats (claims a rank past an unmet
threshold), and the count of beaten thresholds (claims a rank whose own
threshold is unmet, then points Next Rank at a threshold the PB already
beats, a negative gap). The chart's threshold lines are unaffected: they
select by value and compute no rank.

**Precedence.** No PB: both columns `N/A`. Otherwise Top rank wins, whatever
the PB, so a PB of 0 on the all-zero ladder reads Top rank. Only then does a
PB of zero or less make Next Rank `N/A`. An `N/A` Next Rank carries no
tooltip, even when a next rank exists (a PB of 0 on `0, 250, …`), which keeps
`N/A` one uniform state. A benchmark scenario with no ladder reads `N/A` in
both columns; the corpus has none, but a hand-edited file could.

**Display.** Each displayed value is
`max(floor, ceil(round(x * 10**d, 6)) / 10**d)`: the gap with `d = 1`, floor
0.1, formatted `f"{gap:,.1f}"` (a PB of 50 against 940 reads `+1,780.0%`);
the tooltip's points with `d = 2`, floor 0.01. Thresholds and points format
through `_format_score`, as PB Score does. Rounding up keeps a remaining gap
from reading as reached (999.96 against 1,000 reads `+0.1%`). The floors are
needed, not just safe: run files record up to six decimals (1,388 of the
maintainer's 8,665 runs on 2026-09-27), so 9,999.999999 against 10,000 would
ceil to `+0.0%` and 999.999999999 against 1,000 to `0 to go`. The inner
`round` strips float noise: for PB 2.8 against 3.08 the gap computes as
`10.000000000000009` and the difference as `0.28000000000000025`, which a
bare ceiling shows as `+10.1%` and `0.29 to go`. It runs after scaling,
because `0.28 * 100` is itself `28.000000000000004`. Sort keys and the
comparison with the threshold stay unrounded, so PB Score beside such a PB
still reads `1,000`, and the tooltip is what shows a gap remains.

**Rows, fields, and columns.** `benchmark_rank_fields` in
`source/kovaaks/playlist_scenarios_service.py` is a pure function of a
ladder and a PB, with no Dash dependency; it moves out if another page
adopts the columns. It fills five row fields: `tier_display`, `tier_sort`
(ranks passed, so No rank is 0), `next_tier_display`, `next_tier_sort` (the
unrounded gap), and `next_tier_tooltip`. *Tier* avoids the legacy `rank_*`
fields, which hold the leaderboard position
([2026-07-06](#2026-07-06-one-word-per-concept-in-leaderboard-verbiage)).
A table is a benchmark's when `any(scenario.ranks …)` holds, the overview's
Type test (`is_benchmark_playlist`), and a plain playlist's rows carry none
of the fields. The two columns sit directly after Scenario with their header
tooltips; both sort with `nullsLastComparator`, so Rank puts No rank lowest
and `N/A` last in both directions, and Next Rank puts Top rank and `N/A` last
in both directions. Both join the auto-size keys.

**All three row paths carry the ladder.** Rows come from phase 1, the fill,
and a cancelled fill's rebuild on its first terminal drain
([2026-07-15](#2026-07-15-stream-playlist-positions-with-generation-scoped-progressive-fill)).
The last two are AG Grid update transactions, which replace a row's data
whole, so a row built without its ladder would flip Rank and Next Rank to
`N/A` until the page reopens. A cancelled fill is ordinary: opening any
playlist in a second tab cancels the first tab's. `_FillState` therefore
captures each scenario's ladder at registration, from the same playlist
object as `scenario_names`, and releases the ladders with the names on
terminal consumption. `_build_row` takes the ladder as a required keyword,
so mypy flags a path that forgets it; `None` means a plain playlist's row and
an empty list a benchmark scenario without a ladder.

**Sort names, checked per page.** `?sort=` gains `rank` for Rank and
`next-rank` for Next Rank; the name table already reserved `rank` for the
tier
([2026-09-27](#2026-09-27-the-playlist-scenario-table-keeps-its-sort-in-the-page-url)).
`SORT_URL_NAMES` stays one page-independent table, so `_parse_sort` checks
each name against the columns the page actually has. A name for a missing
column invalidates the whole value, as an unknown name does, so the table
opens unsorted and the value leaves the address. Without the check,
`?sort=next-rank.asc` on a plain playlist raised
`KeyError: 'next_tier_sort'` while building the column defs.

**"No rank", not "Unranked".** *Unranked* already means "no leaderboard
entry" in the Position column, and one row can show both. KovaaK's own ladder
calls tier 0 "No Rank".

**Out of scope.** Rank and gap on the Scenario Performance page, whose chart
already draws each threshold. A benchmark-level rank: benchmarks combine
scenario ranks by their own rules, which the ladder data doesn't carry (Anima
Micro Benchmark v2 ranks each subcategory by its best scenario and takes the
lowest subcategory), so Next Rank is always that scenario's own next rank. Rank colors, whose upstream
near-white and pale-yellow values don't read on the light theme. Difficulty
measured against the player's own runs, with recent form, a roadmap Future
entry. Refreshing the table when a run lands: like PB Score, both columns
stay as they were until the page reopens.

**Superseded in part (2026-09-28).** The two columns now sit directly after
PB Score, not after Scenario, at the maintainer's direction. Both compute from
PB Score, so a row reads left to right from the score to the rank it reached
and the gap to the next one, and the points in Next Rank's tooltip sit beside
the score they count from. The accepted cost is that a narrow window has to
scroll sideways to show them, where the old placement kept them in view. The
placement was author-owned, not a ratified row, and D1, D2, and everything
else here stand. Shipped in PR #323.

**Superseded in part (2026-10-05).** On a time-scored scenario, wherever the
app can measure pace, D1's gap is a pace gap: how much faster the PB run has
to finish to reach the next rank, shown as "2.8% faster to Lavender". There,
D1's `N/A` for a PB of zero or less applies only where pace is undefined.
Every other row keeps D1 as written, and the ladder walk, the Rank column,
the rounding, the sort, and the tooltip are unchanged for all rows. The
[2026-10-05 entry](#2026-10-05-time-scored-scenarios-are-measured-by-pace)
holds the formula and the reasons. Shipped in PR #343.

**Provenance.** Proposal by `claude-opus-5-5` (PR #320), reviewed by
`gpt-6-sol` and, as a supplementary seat, `claude-fable-5-1`. Shipped in PR
#321.
