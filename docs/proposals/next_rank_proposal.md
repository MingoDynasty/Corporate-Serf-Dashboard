# Benchmark Scenarios Show Their Rank And The Gap To The Next One

Status: Proposed
Date: 2026-09-27

## TL;DR

A benchmark's scenario table shows leaderboard position and percentile, but
not the benchmark rank each scenario has reached. So finding the scenarios
closest to their next rank means leaving the app for a site such as Evxl.
This proposal adds two columns to a benchmark's scenario table: the rank the
personal best has reached, and the percentage the personal best has to grow
to reach the next rank. Both come from thresholds and scores the app already
holds, so they work offline and appear instantly. Sorting the second column
puts the closest ranks first.

## Decisions needed

Two rows. Nothing is ratified. On 2026-09-27 the maintainer asked in chat for
this feature and for the current-rank column, and leaned toward D1's
recommendation and toward deferring D2's recent-form alternative. A lean is
not a ruling. Every choice outside these rows, including the Copy block, is
author-owned and open to challenge.

### D1 — The gap is how much the PB must grow, as a percentage of the PB

Status: open. Maintainer lean (chat, 2026-09-27): this recommendation.

**Recommendation: the next rank's threshold minus the PB, divided by the PB.**
A PB of 100 with Gold at 110 reads "+10.0% to Gold". Three properties carry
the choice. It is defined below the first rank, where no lower threshold
exists, so every No rank row gets a real number. It states an actionable
target: how much better the player has to get. And it matches how the app
already sets score goals, since the Scenario Performance page's score
threshold is a percentage of the PB. The number is also scale-free, so
scenarios whose thresholds run from 1 to 1,630,000 share one column. Sorted
ascending, it lists the smallest gaps first.

Scale-free is not the same as difficulty-normalized. The percentage gap
counts every percent as equal, so a scenario with a compressed score scale
always looks closer. The next bullet measures how often that changes which
scenario reads as closest.

Choosing differently:

- **How far the PB sits through its current band** (PB 100 between 90 and
  110 reads 50%). KovaaK's benchmark progress uses this idea, and it makes a
  natural progress bar. It counts every band as one equal step, and the
  widths of those steps vary. Across the 23,791 bands of the corpus's
  strictly ascending ladders with three or more ranks, a band spans +3.5%
  (p10) to +18.9% (p90) of its lower threshold, median +8.3%. So two rows
  that both read 50% can need about +1.7% and +8.6%. The widths vary about
  as much across scenarios as within a ladder:
  - Two bands of one ladder differ in percentage width by a median 1.40×
    (p75 2.00×).
  - Two scenarios' bands at the same rank of one benchmark differ by a
    median 1.35× (p75 1.86×).

  Band widths are the only difficulty signal in the data, and neither metric
  is difficulty-normalized. The two disagree about which scenario is
  closest. A simulation placed a player in the same band on every scenario
  of a benchmark, at a random position on each. In 22% of 40,920 trials, the
  two metrics picked a different closest scenario, and the median Kendall τ
  between the two orders was 0.74. The player's own run spread would settle
  it; Out of scope lists that as a follow-up. What decides the choice today
  is the first rank. Below it there is no lower threshold, so a band
  fraction needs an invented floor. A zero floor makes a PB of 850 against a
  first threshold of 940 read 90%, on a scale no other row uses. 4,380 of
  the 4,384 ladders start above zero, so nearly every No rank row would hit
  this.
- **The PB as a percentage of the next threshold** ("at 90.9% of Gold").
  This carries the same information, since it equals 1 / (1 + gap) with the
  gap as a fraction. The closest rows sort first in descending order,
  though, not ascending. It is bounded at 100% and reads as progress rather
  than as the target to beat. Most rows would cluster between 85% and 99%.
- **Points needed**, the "+47 to Gold" of the roadmap's Future entry. It
  can't be compared across scenarios with different score scales, so it
  can't order the table. The design shows it in the cell tooltip instead,
  rounded up to hundredths.

Material consequence: the band fraction would pick a different closest
scenario about a fifth of the time, and it leaves No rank rows without a
number. Points needed can't order the table at all. The PB as a percentage
of the next threshold keeps the order but reverses the sort direction and
the wording.

### D2 — Rank and gap read the local all-time PB, the row's own PB Score

Status: open. Maintainer lean (chat, 2026-09-27): defer recent form as a
follow-up.

**Recommendation: both columns compute from the local high score the PB
Score column already shows.** The row then agrees with itself: PB Score 100,
Rank Silver, "+10.0% to Gold". The columns work with no username configured
and before the leaderboard fill finishes. The rank also follows the rule
KovaaK's uses to award one, which is the best score ever set.

Choosing differently:

- **The leaderboard score that the position lookup returns.** This is higher
  than the local PB when runs were played on another machine. But it
  arrives only in the table's second phase, so a Rank cell could change after
  the page paints. It is absent with no username or a failed lookup, and it
  could disagree with the PB Score beside it.
- **Recent form**, such as the best of the last few sessions. This separates a
  stale, lucky PB from current ability, and that is closer to what "low-hanging
  fruit" means. It needs a window decision of its own, and it would make the
  Rank column disagree with the rank KovaaK's shows. Out of scope lists it as
  a follow-up.

Material consequence: recent form changes what both columns mean, and it
would need its own window decision.

## Problem

The per-playlist scenario table lists Scenario, Last Played, Runs, Position,
Total Players, Percentile, PB Score, PB Date, PB cm/360, and PB Accuracy
([playlists.md](../specs/playlists.md#the-per-playlist-scenario-table)). A
*benchmark* is a playlist whose scenarios carry rank thresholds. Each
scenario has a *ladder*: an ordered list of ranks, each with a name, a color,
and a threshold score. The only place a threshold reaches the screen today is
the Scenario Performance chart's threshold lines, one scenario at a time. No
surface names the rank a scenario has reached, and none compares the
distance to the next rank across scenarios.

That comparison is the everyday question a benchmark player asks: which
scenario is closest to ranking up? Answering it today takes Evxl or KovaaK's
in-game benchmark view. The roadmap already lists this as the Future item
"Next-rank threshold for benchmark playlists" and calls it consolidation
rather than a new capability ([roadmap.md](../roadmap.md#future-briefly)).

Everything the feature needs is local. The ladders ship in the bundled
corpus as `Scenario.ranks` (`source/kovaaks/data_models.py`). The PB is
`ScenarioStats.high_score`, which the row builder already reads for PB Score.
A playlist imported by code is built from scenario names alone and carries no
ladder, so benchmarks come only from the bundled corpus. No network call is
involved.

Ladder facts, surveyed across all 261 bundled files at `ea5b757`:

- 4,384 ladders, every scenario of every benchmark carries one, and every
  benchmark's scenarios share a single list of rank names. So a ladder
  position means the same rank on every row of one table. Lengths run from
  1 to 19; 54 ladders have a single rank.
- 4,367 ladders strictly ascend. 7 repeat a threshold, for example TSK
  ClickTrack Vertical 2t Short, which ends `142, 142`. 10 are not monotonic,
  for example TSK - Wavy Tracking Small, which ends `2000, 1933`, and Viscose
  1w3ts reload Larger, which starts `36, 54, 50`. These are upstream data
  errors, and the benchmark importer carries them through faithfully.
- 4 ladders contain a zero threshold. Three rxns scenarios start at `0`, and
  Valorant Skyclick Multi Easy is `0, 0, 0, 0`.

## Design

### What the table shows

A benchmark's table gains two columns directly after Scenario: **Rank** and
**Next Rank**. They sit first because they are the benchmark's headline, and
because scanning Next Rank is the point of the feature. A table is a
benchmark's when any of its scenarios carries a ladder, the same test the
overview's Type column uses. A playlist's table is unchanged.

**Rank** names the highest rank the PB has reached. It reads "No rank" below
the first threshold and `N/A` with no PB. It sorts by ladder position, with
No rank lowest and `N/A` last in both directions.

**Next Rank** reads "+{gap}% to {name}", with a cell tooltip naming the
threshold and the points still needed. It reads "Top rank" once the PB has
reached the last rank. It reads `N/A` with no PB, and with a PB of zero or
less, where no percentage exists. Top rank comes first: a PB that passes
every threshold reads Top rank whatever its value, so a PB of 0 on an
all-zero ladder reads Top rank, not `N/A`. An `N/A` cell carries no tooltip,
even when a next rank exists, as for a PB of 0 on a ladder `0, 250, …`. That
keeps `N/A` one uniform state. It sorts by the unrounded gap, with Top rank
and `N/A` last in both directions, so ascending lists the closest ranks
first.

A scenario that has no ladder inside a benchmark reads `N/A` in both
columns. The corpus has none, but a hand-edited file could.

### Computing them

One pure function takes a ladder and a PB:

1. The **current rank** is reached by walking the ladder from the bottom and
   stopping at the first threshold above the PB. The last rank passed is the
   current rank. If the walk stops at the first rank, the current rank is No
   rank.
2. The **next rank** is the one the walk stopped at. If the walk passed every
   rank, the next rank is Top rank.
3. The **gap** is `(next threshold - PB) / PB * 100`, computed only when the
   PB is above zero.

A PB equal to a threshold has reached it. By construction the next threshold
is always above the PB, so the gap and the tooltip's points are always
positive. On a strictly ascending ladder, which is 4,367 of 4,384, the walk
gives the same answer as any other reasonable rule. The remaining ladders
behave like this:

- **Tied thresholds.** A PB of 142 on a ladder ending `142, 142` passes both,
  so Rank names the last rank and Next Rank reads Top rank.
- **Non-monotonic ladders.** The walk never grants a rank whose own threshold,
  or any threshold below it on the ladder, is unmet. On Viscose's `36, 54,
  50, …`, a PB of 52 reads the first rank, "+3.9% to" the second at 54,
  although it beats the third rank's 50. Two alternatives were rejected. The
  first names the last rank on the ladder whose threshold the PB beats (the
  third, here). That claims a rank past an unmet threshold. The second counts
  the thresholds the PB beats (2 here) and names that rank, which is the
  second. That claims a rank whose own threshold (54) is unmet, and it then
  points Next Rank at a threshold the PB already beats (50), giving a
  negative gap. The chart's threshold lines are unaffected: they select by
  value and compute no rank.
- **Zero thresholds.** A PB of 0 or more reaches a zero threshold. So every
  played row of Valorant Skyclick Multi Easy reads Top rank, and a PB of 100
  on an rxns ladder `0, 250, …` reads the first rank and "+150.0% to" the
  second.

The cell rounds the gap **up** to one decimal and never shows less than
"+0.1%". A PB just under a threshold therefore reads "+0.1%", never "+0.0%",
which would look like the rank was reached (PB 999.96 against 1,000 is a
0.004% gap). The tooltip's points round up the same way, to the two decimals
PB Score shows, and never read less than 0.01, so they never read "0 to go".
The floors are always safe to apply, because the next threshold is always
above the PB and every gap is positive.

The floors are needed, not just safe. Run files record scores to as many as
six decimals (1,388 of the 8,665 runs in the maintainer's stats folder on
2026-09-27), and the run parser accepts any float. A PB of 9,999.999999
against a 10,000 threshold is a gap of 0.00000001%, which a ceiling alone
rounds to "+0.0%". A PB of 999.999999999 against 1,000 leaves 0.000000001
points, which it rounds to "0 to go". The sort key stays unrounded, and both
columns compare the unrounded PB with the threshold. PB Score beside them
still displays such a PB as `1,000`, as it does today. The tooltip is what
shows a gap remains.

Each displayed value is `max(floor, ceil(round(x * 10**d, 6)) / 10**d)`, with
a floor of 0.1 for the gap and 0.01 for the points. The inner rounding
strips float noise. A bare ceiling shows "+10.1%" for PB 2.8 against 3.08,
because the gap computes as `10.000000000000009`. It also shows "0.29 to
go", because the difference computes as `0.28000000000000025`. Rounding
before scaling doesn't fix the second case, because `0.28 * 100` is
`28.000000000000004`. Above the floor, the recipe matched an exact decimal
ceiling on 200,000 random score pairs.

### Where it lives

The function is a module-level pure function in the scenario-table service
(`source/kovaaks/playlist_scenarios_service.py`), with no page or Dash
dependency. If another page adopts the columns later, it moves then. The row
builder calls it and adds five fields: `tier_display`, `tier_sort`,
`next_tier_display`, `next_tier_sort`, and `next_tier_tooltip`. The internal
name *tier* avoids the row's existing `rank_*` fields, which hold the
leaderboard position: that rename changed labels only
([2026-07-06](../decision_log.md#2026-07-06-one-word-per-concept-in-leaderboard-verbiage)).

The table builds rows from three sources, all through the same row builder:
- phase 1, when the page opens;
- the fill's streamed rows;
- a cancelled fill's rebuild, run on its first terminal drain for the rows
  the fill never resolved.

The last two apply their rows as AG Grid update transactions, which replace a
row's data whole. So a row built without its ladder would erase its Rank and
Next Rank cells, and they would read as the no-ladder `N/A` until the page
reopens.

A cancelled fill is ordinary: opening any playlist in a second tab cancels
the first tab's fill. The fill state therefore captures each scenario's
ladder at registration, from the same playlist object as `scenario_names`,
and it holds and releases the ladders the way it does the names. It hands
them to both the fill and the cancelled rebuild. An optional ladder
parameter would let a missed path type-check, so the tests below cover every
path.

The column definitions gain the benchmark test. On a playlist the two
definitions are left out. The URL sort names gain `rank` for Rank and
`next-rank` for Next Rank. The existing comment on the name table already
reserves `rank` for the benchmark tier, and this uses it that way.

The name table is page-independent, so the sort parser has to change. Today
`_parse_sort` accepts any name in the table, and `_column_defs` then indexes
the column that name maps to. On a playlist, `?sort=next-rank.asc` would
raise `KeyError: 'next_tier_sort'`. The parser therefore checks each name
against the columns the page actually has. A name for a column the page
lacks makes the whole value invalid, as an unknown name does today. On a
playlist's table the two names then read as unknown, so the existing rule
applies: the table opens unsorted and the value leaves the address
([2026-09-27](../decision_log.md#2026-09-27-the-playlist-scenario-table-keeps-its-sort-in-the-page-url)).
Both columns join the auto-size keys.

The change touches no cache, setting, network path, or notification.

### Copy

Rank names come from the ladder data and are not copy. Every string this
design adds:

| Where | String | Why |
|---|---|---|
| Rank header | `Rank` | Title Case like every grid header. *Rank* means the benchmark tier in this app. |
| Rank header tooltip | `The highest rank your PB score has reached on this scenario.` | Follows the Percentile tooltip's pattern. "PB score" is a paraphrased value, not a control name. |
| Rank cell, below the first threshold | `No rank` | *Unranked* already means "no leaderboard entry" in the Position column ([2026-07-06](../decision_log.md#2026-07-06-one-word-per-concept-in-leaderboard-verbiage)), and one row can show both. KovaaK's own ladder calls tier 0 "No Rank". Sentence case per the copy rules. |
| Rank and Next Rank cells, no PB; Next Rank for a PB of zero or less below the top rank | `N/A` | The table's existing sentinel for a missing PB value ([2026-08-09](../decision_log.md#2026-08-09-pb-columns-keep-their-na-sentinel-even-for-timestamps)). No tooltip. |
| Next Rank header | `Next Rank` | Title Case. Names the target rather than the metric, so the header survives a D1 change of metric. |
| Next Rank header tooltip | `How much your PB score has to grow to reach the next rank. Lower is closer.` | "Lower is closer." mirrors the Percentile tooltip's "Higher is better." and tells the reader which sort direction finds the closest ranks. |
| Next Rank cell | `+{gap}% to {rank name}`, such as `+10.0% to Gold` | Reads as the maintainer's own sentence, "push my PB by 10% to reach Gold." A readout, so no period. The sign marks it as growth still needed. The gap groups thousands as PB Score does: a PB of 50 against 940 reads `+1,780.0% to {rank name}` (`f"{gap:,.1f}"`). |
| Next Rank cell tooltip | `{rank name} at {threshold} · {points} to go`, such as `Gold at 110 · 10 to go` | Carries the points D1 leaves out of the cell, rounded up to hundredths. A readout, so the middle dot and no period. Numbers format like PB Score: up to two decimals, trailing zeros dropped ([2026-09-27](../decision_log.md#2026-09-27-the-scenario-table-drops-trailing-zeros-from-pb-score-and-pb-cm360)). The points round up, so a remaining gap never reads `0 to go`. |
| Next Rank cell, last rank reached | `Top rank` | States the fact without implying a failure. Sorts last, beside `N/A`. |

## Out of scope

- **Rank and gap on the Scenario Performance page.** That chart already draws
  each threshold line with its value, so one scenario's gap is visible there
  today. The cross-scenario comparison happens only in the table. This is a
  follow-up if wanted, and the function moves out of the table service then.
- **Difficulty measured against the player's own runs.** Two scenarios can
  both need +5%, but if one scenario's runs vary by 8% and the other's by 2%,
  only the first is a good day away. Recent form (D2's alternative) belongs
  with it. The app holds every local run, which Evxl does not, so this is the
  follow-up that could beat the external tools rather than match them. The
  shipping PR adds it to the roadmap's Future list.
- **A benchmark-level rank.** Benchmarks combine scenario ranks by their own
  rules, and the ladder data carries no rule. Voltaic-style benchmarks sum
  progress across scenarios. Anima Micro Benchmark v2 ranks each subcategory
  by its best scenario and takes the lowest subcategory as the overall rank
  (observed 2026-08-11 against its published rules). So under some rules,
  closing one scenario's gap moves nothing at the benchmark level. Next Rank
  is always the gap to that scenario's own next rank.
- **Rank colors in the Rank cell.** Upstream colors include near-white
  placeholders and pale yellows that don't read on the light theme. A swatch
  beside the name would work in both themes, and it is a cheap follow-up if
  wanted.

## Delivery plan

One implementation PR, with no dependencies, startable once D1 and D2 are
ratified:

- The pure function, the five row fields on all three row paths, the two gated
  column definitions, the two URL sort names, and the tests below.
- The shipping docs in the same PR: a decision-log entry, the playlists spec
  (column list and sort names), the user guide's Playlists and Benchmarks
  section, the product inventory, and the roadmap (the Future entry becomes
  Shipped, and the own-runs difficulty follow-up becomes a Future entry). The
  PR also deletes this proposal.

Recommended implementer: `claude-opus-5-5` at high. The spec is settled and
mechanical, and unit tests plus one live check verify it; more effort would
buy polish, not correctness.

## Testing

- **The pure function**, table-driven:
  - an ascending ladder below the first threshold, mid-band, exactly on a
    threshold, and past the last rank;
  - tied thresholds;
  - the three non-monotonic shapes above, including the no-negative-gap
    property;
  - zero thresholds, including the all-zero ladder;
  - a single-rank ladder, no PB, and a PB of zero or less, including a PB
    of 0 on the all-zero ladder (Top rank) and on `0, 250, …` (`N/A`, no
    tooltip);
  - a four-digit gap with its thousands separator (50 against 940 reads
    "+1,780.0%");
  - rounding up (999.96 against 1,000 reads "+0.1%", and 999.999 against
    1,000 reads "0.01 to go") and float noise (2.8 against 3.08 reads
    "+10.0%" and "0.28 to go");
  - the floors (9,999.999999 against 10,000 reads "+0.1%", and
    999.999999999 against 1,000 reads "0.01 to go").
- **The row builder:** a benchmark row carries the five fields. A playlist
  row carries none. A second-phase row and a cancelled fill's rebuilt row
  each carry the same values as the first-phase row for the same scenario.
- **The page:** a benchmark's column definitions include Rank and Next Rank
  after Scenario, and a playlist's don't. `?sort=next-rank.asc` seeds the
  initial sort on a benchmark. On a playlist, `?sort=rank.asc`,
  `?sort=next-rank.asc`, and the mixed `?sort=percentile.desc,next-rank.asc`
  each open unsorted without raising.
- **Gates:** the standard local validation in AGENTS.md, including the docs
  test for this file's placement and links.
- **Live check:** open a benchmark the maintainer plays and sort Next Rank
  ascending. For one row, check Rank and Next Rank by hand against PB Score and
  the Scenario Performance chart's threshold lines, including the tooltip.
