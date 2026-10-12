# 2026-10-06: Benchmark Scenario Tables Group Scenarios By Category And Subcategory

Status: Accepted

A benchmark's scenario table now draws the groups its author sorted the
scenarios into, as merged, colored cells ahead of the scenario names, each
labeled with its category or subcategory the way the benchmark's own sheet
does. A sorted or filtered table can't keep a group's rows together, so there
each row names its group under its scenario instead. The grouping comes from
data that already ships with the app, so nothing new is fetched. A player sees
a benchmark's structure at a glance, and can type a group's name in the filter
box to find its scenarios.

**Rulings.** All by the maintainer. 2026-10-06, on
[PR #338](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/338):
D1, what the group columns show when the table is sorted or filtered, ruled
as recommended once both reviewers had endorsed it, and the proposal ratified
as a whole the same day. 2026-10-06, in chat, during the build
([PR #352](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/352)):
ship the workaround under "A workaround for the grid's stale merged cells"
below, over parking the feature and over replacing the mechanism.

**Supersedes in part** the
[2026-10-04 entry](#2026-10-04-a-benchmarks-scenario-page-links-to-its-evxl-page):
the snapshot read moved out of `source/kovaaks/evxl_links.py` into
`source/kovaaks/evxl_snapshot.py`, which both features use, and its two
warnings now say that benchmarks get no Evxl link and no categories. The
link's addresses, its rules, and its evidence are unchanged.

**Two states (D1).** The table is *grouped* while it is in playlist order and
the filter box is empty, which is how a fresh visit opens. Any sort, or any
filter text that is not only spaces, makes it *ungrouped*. It is one flag for
the whole table, not a judgment per cell.

- Grouped: each group is one merged cell with a vertical label, uppercase,
  reading bottom to top.
- Ungrouped: the cells keep their colors and lose their labels, and each
  Scenario cell gains a second line naming the row's group, such as
  "Control Tracking · Arm".
- No column changes width between the states: each group column is 34 px wide
  in both. A link that carries a `?sort=` opens ungrouped.

A vertical label needs its group's whole height, and a sorted or filtered
table leaves most groups a single 42 px row, which fits about five letters.
Three alternatives were rejected:

- **Swap the narrow columns for one wider column under a sort.** The group
  area grows from 68 px to between 115 px and 150 px, so every column to its
  right moves on the first click of every sort, and a second click to reverse
  the direction can land on the neighboring header.
- **One horizontal column in every state.** Nothing moves, but it spends that
  115 px to 150 px in playlist order too, on a table that already scrolls
  sideways, and gives up the benchmark-sheet layout the request asked for.
- **Hide the group columns under a sort or a filter.** The least code. A
  sorted table would then say nothing about groups, and the filter box
  couldn't match a group's name while a sort is active, because the grid's
  quick filter skips hidden columns.

**The data path.** The groups come from the committed Evxl benchmark snapshot,
`resources/evxl/benchmarks.json`, through the one read the View on Evxl link
already made. Nothing is written into the bundled files, `PlaylistData` gains
no field, and the app makes no new network call. The rejected alternative had
the importer write each scenario's group into its bundled file. The Evxl link
entry weighed the same alternative for the Evxl names and rejected it: it
raises the importer's `schema_version`, which marks all 261 files stale, and
the live run that regenerates them carries whatever thresholds KovaaK's
changed upstream into the same diff. For groups it costs one thing more. The
playlist model would gain fields, and the importer's drift check compares a
shipped file with its rebuild by whole-model equality, so a snapshot refresh
that renamed a group would report every affected file as drifted.

**The join is positional.** A bundled file lists scenarios and no groups. The
snapshot lists each benchmark's categories in order, each with its
subcategories, their colors, and how many scenarios each holds, and no
scenario names. So the join walks the counts down the file's scenario list:

1. Match the file's playlist code to a snapshot sharecode without regard to
   case. A sharecode listed twice keeps its first listing.
2. Sum the layout's scenario counts. If the sum differs from the file's
   scenario count, the benchmark gets no groups.
3. Otherwise hand each scenario its category and subcategory, with both
   colors. Names are trimmed. A color is kept as six-digit hex, a short form
   such as `#FFF` is expanded, and any other value becomes no color.
4. If no category in the layout is named, the subcategories become the
   categories, so a benchmark with one level always has categories.

Only bundled benchmarks are joined. A playlist the user imported has its own
scenario order, which the counts don't describe. Each entry's layout is
validated on its own, so an entry whose layout is unusable has no groups and
keeps its Evxl link, with one warning that names it. A snapshot the read can't
use at all costs every benchmark both, with one warning.

**The premise, and what holds it.** The join is right only if the snapshot's
counts, taken in order, cut the file's scenario list where the benchmark's
author cut it. A matching total doesn't show that: two groups swapped, or a
boundary moved by one scenario, keep the total and mislabel rows. Three things
hold the premise.

- **The file's order is KovaaK's.** The importer writes scenarios in KovaaK's
  category order, and its drift check reports a file whose scenario list no
  longer matches KovaaK's
  ([2026-09-26 entry](#2026-09-26-a-read-only-check-finds-bundled-benchmarks-that-kovaaks-changed)).
  That check compares KovaaK's with KovaaK's and never looks at the snapshot.
- **A comparison in the importer looks at both.** Wherever a benchmark is
  built, at generation and in the drift check, the importer compares the
  groups the app would draw with KovaaK's own categories, through the app's
  own join. No drawn group and no KovaaK's category may partly overlap: where
  the two meet, one has to contain the other. Either side may subdivide the
  other. Both drawn levels are checked, because a category can straddle a
  boundary that each of its subcategories respects.
- **A benchmark that fails gets no groups,** through the exclusion list
  below.

**How the comparison reports.** A crossing is reported by benchmark name, with
the scenarios at issue, beside the drift check's result buckets and never as
one of them: such a file can be identical or drifted, and regenerating it
changes nothing about its groups, so it never reaches the regenerate line. A
crossing fails the exit code, at generation and in the check, unless the
benchmark's playlist code is already on the exclusion list, where it is
logged for information. Without that, the check could never exit zero again
while an excluded benchmark stays in the corpus.

**A refreshed layout is compared again.** The comparison runs only where a
benchmark is built, and a normal run skips a benchmark whose resume state is
current. The app draws its groups from the snapshot that run may just have
refreshed, so the layout is part of the resume state: the manifest records
the layout each benchmark was last compared under, and a benchmark whose
layout changed is built and compared again although its ID, its ladder, and
its generated file are unchanged. A manifest entry written before layouts
were recorded matches no live item, so it is built once. The manifest records
a layout only after a comparison that found no crossing. A benchmark whose
groups cross is therefore never current: every normal run builds it again
and reports the crossing again, so the failure keeps blocking across resumed
runs, and blocks again on the first run after its code leaves the exclusion
list. An excluded benchmark is rebuilt on every run as well, which is the
price of that. A run narrowed with
`--only` still compares only what it names, so the drift check, which the
refresh runbook requires, stays the comparison over the whole corpus.

**The comparison's result.** The proposal's one-off run, on payloads fetched
for every bundled benchmark on 2026-10-05, compared 258 benchmarks. On 221,
KovaaK's categories begin exactly where the drawn groups do. On 34, Evxl is
finer. On 2, KovaaK's is finer. One disagrees: on IRIS Mixed Benchmarks Easy,
KovaaK's holds IRIS Smoothbot Easy in its Clicking category, and Evxl's counts
put it under Tracking, in PRECISE. The built comparison's first run through
the drift check, on 2026-10-06 over 261 bundled files, named IRIS Mixed
Benchmarks Easy and no other benchmark. The same run found 259 files
identical, one drifted (Jade Palace Air Benchmark - Hard, thresholds), and one
that no longer builds (Coach Ben - VALORANT Strafe Aim Benchmark, whose ladder
KovaaK's cut from seven ranks to four). Those two are a corpus refresh's to
fix, not this change's.

**Evxl's finer level has no second source.** Where Evxl subdivides one of
KovaaK's categories, the subdivision rests on Evxl's counts alone, and a wrong
count there moves a subcategory boundary without crossing anything, so the
comparison can't see it. The table shows there what Evxl's own page shows,
which is the layout the request asked for. The maintainer's screenshots of
Evxl's sheets matched the join row for row on the two benchmarks they show,
Voltaic Intermediate S5 and Viscose S2 Medium.

**The exclusion list is kept by hand.** `GROUP_EXCLUDED_PLAYLIST_CODES` in
`source/kovaaks/scenario_groups.py` holds the playlist codes of benchmarks
that get no groups although their counts add up. It starts with IRIS Mixed
Benchmarks Easy (`KovaaKsDeathballingFlyJump`). The importer never writes it:
each failure needs a look, and usually a report upstream, before it belongs
there. A corpus test pins the bundled benchmarks that get no groups, three as
of 2026-10-06: that one, PureG S1 - Worthless, whose file holds 14 scenarios
where Evxl counts 12, and kl2 - Reflex by dummy, whose layout names nothing.
The other 258 get groups, 180 with two levels and 78 with one. The importer
rewrites the snapshot on every run, so a refresh can change a benchmark's
counts before its file is regenerated, and that benchmark then stops joining.
The corpus test fails in the PR that commits such a refresh.

**The two column IDs are a one-way choice.** They are `category` and
`subcategory`. The Columns menu keeps each stored choice under its column's
ID, so renaming one resets that choice in every browser. The row fields under
them (`category_name`, `category_color`, `category_run`, and the same three
for `subcategory`) can be renamed freely.

**What cell spanning asks of the grid.** The merges are AG Grid's cell
spanning, `enableCellSpan` on the grid and `spanRows` on a column, which its
Community build includes.

- It merges neighboring cells whose values are equal, over the rows as
  displayed, and dash-ag-grid 35.3.0 passes no `spanRows` function through, so
  equality is the only merge test. The cell's value is therefore a run
  number, counted down the benchmark, never the group's name: two benchmarks
  have a subcategory name on both sides of a category boundary, and with the
  name as the value those two groups would merge.
- Because the value is a number, each group column supplies its name as its
  text for the filter box. Without that, a typed digit would match run
  numbers.
- It rules out a few grid features on the same grid: the grid-wide text
  selection option, click row selection, cell selection, and editing or row
  dragging on a spanning column. The list is read from the validation rules in
  the AG Grid 35.3.1 bundle, not from its documentation. The table uses none
  of them, and the Leaderboard ID cell's selectable text comes from a cell
  class. Superseded in part (2026-10-12): selectable text now comes from
  one stylesheet rule for every cell, and the merged cells are left out
  ([2026-10-12](#2026-10-12-on-both-playlist-tables-only-the-name-navigates-and-cell-text-can-be-selected)).
- It is an initial grid option, set only on a table that has groups, so every
  other table's grid is configured as before.

**The label follows the scroll.** A group can be taller than the window: four
span 30 rows or more, and a 36-row cell is 1,511 px tall. The label is
`position: sticky` toward both the top and the bottom of the grid's scrolling
viewport, so it sits in the middle of its cell and stops at the nearer edge of
the part still showing. That needs the group columns pinned left, because an
unpinned cell's nearest scroll container is the one that scrolls the columns
sideways, and it needs the group cell's overflow left visible. The cell's
tooltip, which names the group in both states, is the guarantee. The pin and
the following label are the improvement.

**A workaround for the grid's stale merged cells.** AG Grid 35.3.1, the
version dash-ag-grid 35.3.0 bundles, loses merged cells after an ordinary sort
cycle. This was found on the built page, after the proposal was ratified. The
proposal's "the merges were checked through a sort" was one sort.

- **The defect.** Two sort changes and then none leave merged cells at a
  stale height and rows with no cell in the group column. Clicking a header
  three times, ascending, descending, then unsorted, does it. On Viscose S2
  Medium a cycle on Scenario left 18 of 39 rows with no Category cell and 1
  with no Subcategory cell, and a cycle on Runs left 10 and 2. Sorting Last
  Played and then Runs left 2 rows blank while the table was still sorted.
  One sort and back is clean, and so is every filter-only sequence tried.
- **Whose defect.** The grid's. It reproduces with this app's own redraw
  switched off, and plain AG Grid from its CDN bundle, outside Dash, with the
  same rows and the same spanning setup, gives the same counts. Read from the
  bundle, and not confirmed as the cause: the grid reuses a merged cell's
  control across row-model updates when the merge keeps its first row.
- **Where it is fixed.** Measured on 2026-10-06 with that standalone grid: the
  defect is present in AG Grid 35.3.1, 36.0.0, 36.0.1, and 36.0.2, and gone in
  36.1.0 and 36.2.0. dash-ag-grid 35.3.0 is the newest stable release. Its one
  later release, 36.0.0rc0, pins AG Grid 36.0.1, so it still has the defect.
- **What does not repair it.** `refreshCells` with `force`, `redrawRows`,
  `refreshClientSideRowModel`, `resetRowHeights`, `onRowHeightChanged`, and
  `onFilterChanged`.
- **The workaround.** After each row-model update on a table with groups, the
  page hides and then shows the group columns that are showing, through the
  grid API, one task later. The grid builds a column's cells again when it
  shows the column, which replaces the stale controls. It is installed once
  per grid by the callback that keeps the grouped state. A column the Columns
  menu has hidden is never touched.
- **What it costs.** It leans on grid behavior the documentation does not
  promise. It fires two column-visibility events on every model update,
  including each tick of the position fill. Measured, in Edge and in
  Firefox: no column moves or changes width, the sort and the address are
  untouched, a focused group cell keeps keyboard focus through a rebuild, and
  a tooltip on a group cell under a resting pointer still names its group
  after one. The two calls run in one task, so the browser paints nothing
  between them.
- **The alternatives.** Park the feature until a dash-ag-grid release bundles
  AG Grid 36.1.0 or later, for which there is no date. Or draw the merged look
  without the grid's cell spanning, which replaces the mechanism the proposal
  ratified with one upstream has since fixed.
- **When it goes.** When dash-ag-grid bundles AG Grid 36.1.0 or later. Remove
  the listener, its test, and the
  [tech-debt entry](tech_debt.md#remove-the-merged-cell-repair-when-dash-ag-grid-bundles-ag-grid-3610),
  and run a sort cycle on a benchmark's table. The
  [dependency refresh playbook](dependency_refresh.md#packages-that-ship-browser-code)
  carries the check. AG Grid 36 also lays its rows out in one scrolling
  container, with no separate pinned section, so the following label needs
  checking again on that upgrade.

**Mechanics that differ from the proposal's text.** Each keeps the ratified
outcome.

- The run numbers are computed by the join, not by the row builder, so the
  importer's comparison and the table read one definition of a group.
- The join normalizes each color, so the browser only picks black or white
  text for a six-digit hex fill.
- A group column's header keeps its name in the header, hidden by a
  stylesheet rule, where the proposal wrote "no visible text". Assistive
  technology then reads the name from the header itself.
- A group column can't be dragged to another position or out of the pinned
  area, because the following label depends on the pin.

**Where it lives.** The shared read is `source/kovaaks/evxl_snapshot.py`. The
join and the exclusion list are `source/kovaaks/scenario_groups.py`, and
`data_service.load_playlists` fills a side table from them, behind
`get_scenario_groups`, beside the benchmark IDs and for the same reason
([2026-10-05 entry](#2026-10-05-a-columns-menu-shows-and-hides-table-columns-and-kovaaks-ids-are-optional-ones)).
`playlist_scenarios_service.py` puts the group fields on all three row paths,
and its fill state captures the groups at registration, as it does the
ladders. `pages/playlist_scenarios.py` holds the column definitions, the menu
entries, and the state callback. The renderers are in
`assets/dashAgGridComponentFunctions.js`, the fill function in
`assets/dashAgGridFunctions.js`, and the styles in `assets/stylesheet.css`.
The comparison is `find_group_crossings` in
`scripts/benchmark_importer/script.py`.
