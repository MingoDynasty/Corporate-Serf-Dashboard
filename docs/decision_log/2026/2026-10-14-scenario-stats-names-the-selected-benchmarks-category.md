# 2026-10-14: Scenario Stats Names The Selected Benchmark's Category

Status: Accepted

Scenario Stats names the selected scenario's benchmark category above its
history. The Playlist filter determines which benchmark's
category it names, because a scenario can belong to several benchmarks.
When that benchmark has no groups or does not list the scenario, the row
disappears so the card holds only useful facts.

**Superseded in part (2026-10-18).** [Last played leaves Scenario Stats](2026-10-18-last-played-leaves-scenario-stats-and-its-first-line-is-plain-text.md):
the card holds Category and Number of runs, under a first line that is
plain text, `Scenario stats`, and no longer an `h2`. With no scenario
selected it reads "No scenario selected" in place of both, so Last played's
empty states below are historical. Category's rules stand.

**Ruling.** T2 of [#379](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/379),
ratified by the maintainer on 2026-10-14 at `7329c23`. The maintainer wanted
the category while grinding a benchmark and kept Last played because the
page is also a tool for looking up past runs. Current behavior is in
[run_history.md](../../specs/run_history.md#scenario-stats).

Category reads `Category: {category} · {subcategory}`, or
`Category: {category}` for a benchmark with one level, using the table's
group labels. The three facts have one weight, Category first. Position
moves to [the PB card](2026-10-14-the-pb-card-shows-the-local-record-and-next-rank.md).
The card is about 270px wide; its heading remains an h2 and Category is text.

Read only the benchmark the Playlist filter holds, indexing its groups by
the scenario's place in its scenario list. Share the table's length guard:
groups of another length would give a scenario its neighbor's label. A
filter change alone rewrites the row, as does a scenario or playlist change.
No filter, an ordinary playlist, an unknown code, a benchmark without
groups, an excluded benchmark, or a scenario absent from the benchmark
means no row, with no placeholder. The existing
[grouping exclusions](2026-10-06-benchmark-scenario-tables-group-scenarios-by-category-and-subcategory.md)
still apply.

At proposal verification, 688 of 3,240 bundled scenarios belonged to more
than one benchmark, one to 11, but none appeared twice within a benchmark.
The filter therefore makes the category exact without guessing a benchmark.
Showing a reason for an empty row would add noise, and putting Category
under the dropdown added height. Last played's existing empty states stand:
`—` with no selection, `Never` with no local runs. Total time remains
deferred until the app defines it consistently across pages.
