# Benchmark Scenario Tables Group Scenarios By Category And Subcategory

Status: Proposed
Date: 2026-10-04

## TL;DR

A benchmark's scenario table lists its scenarios as one flat run of rows, so
finding one means reading names, although the benchmark's author already
sorted them into categories such as Clicking and Tracking. This proposal
draws that grouping in the table the way the benchmark's own sheet and Evxl
do: two narrow columns of merged, colored cells ahead of the scenario names,
labeled with each category and subcategory. A sorted or filtered table no
longer keeps a group's rows together, so there each row names its own group
under the scenario instead. The grouping data already ships with the app, so
nothing new is fetched.

## Decisions needed

One ruling, and nothing is ratified. The maintainer asked for the feature in
chat on 2026-10-03. On 2026-10-04 they asked whether one combined column
would do, and whether Evxl's vertical labels are worth adopting, naming a
table sorted by Last Played as the one worry. Those were questions, not
leans. Everything else in this proposal, including the Copy and Terms
blocks, is author-owned and open to challenge.

The data path was a second row when this proposal opened. A decision that
shipped on 2026-10-04 took the same path for the View on Evxl link and
rejected the alternative, for reasons that apply here unchanged. The choice
is therefore author-owned now, and it sits in Design under "Getting the
groups", with the alternative it rejects.

### D1 — What the group columns show when the table is sorted or filtered

Status: open

A vertical label needs its group's whole height. Evxl's table can't be
sorted, so its groups are always whole. This table sorts and filters, and
then most groups are a single 42 px row, which fits about five letters of a
vertical label. On Viscose S2 Medium sorted by Last Played, 33 of the 46
vertical labels the grid had rendered were clipped. So a table in playlist
order with nothing filtered can use the benchmark-sheet layout, and the
decision is what a sorted or filtered table shows in its place.

**Recommendation: keep the two narrow columns where they are, and name each
row's group under its scenario.** In playlist order with no filter text,
every group is one merged cell with a vertical label, as on Evxl. Under any
sort or filter text, the cells keep their colors and drop their labels, and
each Scenario cell gains a second line such as "Control Tracking · Arm". The
columns are 34 px wide in both states, so no column moves when the state
changes, and both lines fit the row height the table has today.

Choosing differently:

- **Swap the narrow columns for one wider column under a sort.** The
  vertical columns hide, and a horizontal column appears whose cells stack
  the category over the subcategory. The names get a column of their own,
  which scans a little better than a second line. But the group area grows
  from 68 px to 150 px on Viscose S2 Medium and to 115 px on Voltaic S5.5
  Intermediate. Every column to the right of it then moves by 82 px or 47 px
  whenever a sort starts or ends. The Last Played header is 150 px wide, so
  the header just clicked can leave the pointer, and a second click to
  reverse the direction then sorts the neighboring column.
- **One horizontal column in every state.** There are no two states and
  nothing moves. It spends that 115 px to 150 px in playlist order too,
  against 68 px, on a table that already scrolls sideways in a 1500 px
  window. The Columns menu now lets a user drop columns they don't read,
  which eases that for them and leaves the default view as wide as before.
  This option also gives up the benchmark-sheet layout the request asked
  for.
- **Hide the group columns under a sort or a filter.** This is the least
  code. A sorted table would then say nothing about groups, which is the
  view the maintainer's question was about. The filter box also couldn't
  match a category name while a sort is active, because the grid's quick
  filter skips hidden columns. A user who wants the columns gone can already
  hide them through the Columns menu, in either state.

Material consequence: the swap moves the column headers on the first click
of every sort. The single horizontal column spends 47 px to 82 px more in
the default view and doesn't look like the benchmark's sheet. Hiding leaves
a sorted table without the feature.

## Problem

The per-playlist scenario table lists a playlist's scenarios in playlist
order, one row each
([playlists.md](../specs/playlists.md#the-per-playlist-scenario-table)). A
bundled benchmark holds between 2 and 60 scenarios, 16 at the median, and 68
of the 261 hold 20 or more. Their authors arrange them in groups. Viscose S2
Medium has 39 scenarios in four categories, such as Control Tracking, each
split into subcategories, such as Arm, Wrist, Fingertip, and Blending. The
benchmark's own spreadsheet and Evxl draw those groups as merged cells
beside the scenario names.

The app shows none of it. Finding the Arm scenarios, or a scenario that the
player remembers by its group, means reading names down the table. The
filter box matches scenario names and the other cells, and no cell holds a
group. Evxl answers the question at a glance, and a benchmark's page now
links to its Evxl page. That puts the grouped view one click away, and
outside the app, away from this table's own columns.

The question belongs to both moments in
[product.md](../product.md#when-they-ask-them). Between sessions, the look
ahead at what to work on is usually asked by group: which tracking scenarios
are weak. Just before a session, and between scenarios within one, the
player wants to pick a scenario and get playing, so the table has to give up
its structure at a glance.

Everything the feature needs is local, and it makes no network call.

### Verified facts

Surveyed against `main` at `fb2f679`, with the snapshot last refreshed on
2026-09-26. Neither the bundled files nor the snapshot has changed on `main`
since, as of `bb71988`. The grid measurements and the prototype date from
2026-10-04, before the Columns menu shipped. The tall-group probe dates from
2026-10-05.

- **The bundled files carry no grouping.** A scenario has a name, a ladder,
  and a leaderboard ID. The importer walks KovaaK's categories in order and
  flattens them into that list.
- **The snapshot does.** `resources/evxl/benchmarks.json` has 266 difficulty
  entries. Each lists categories in order, and each category lists
  subcategories with a name, a color, and a scenario count. It holds no
  scenario names.
- **The app already reads the snapshot.** The View on Evxl link takes each
  benchmark's Evxl names from it, once per process, matched to the playlist
  code without regard to case. The release contract names the file, so a
  release can't ship without it
  ([2026-10-04](../decision_log.md#2026-10-04-a-benchmarks-scenario-page-links-to-its-evxl-page)).
- **KovaaK's has one level and no colors.** Its benchmark payload groups
  scenarios under category keys with progress, a rank, and thresholds. That
  level is Evxl's subcategory level on most benchmarks and Evxl's category
  level on others, as the comparison in this list counts. Their names differ
  from Evxl's, such as "WideWall" against "Widewall", and one payload pads a
  repeated name with a space. A benchmark's second level and every color
  exist only in Evxl's data.
- **260 of the 261 bundled files join by count.** Matching a file's playlist
  code to a snapshot sharecode without regard to case finds an entry whose
  counts add up to the file's scenario count. One file matches only that
  way: Revosect Season 4 Easy's code differs from its sharecode in the case
  of one letter. PureG S1 - Worthless doesn't join: the file holds 14
  scenarios and Evxl counts 12.
- **Where the groups fall agrees with KovaaK's on 257 of 258 benchmarks.**
  A matching total doesn't show that each count cuts the list in the right
  place, so the drawn groups were compared with KovaaK's own categories, on
  payloads fetched for every bundled benchmark on 2026-10-05:
  - 221: KovaaK's categories begin exactly where the drawn groups do.
  - 34: Evxl is finer. Every KovaaK's boundary is a drawn boundary, and the
    drawn groups subdivide KovaaK's categories. In 31 of them KovaaK's
    categories are exactly Evxl's categories, the Voltaic S5 benchmarks
    among them.
  - 2: KovaaK's is finer, on Control Track DOJO and Tosoku Aim FundamentalLVL
    Benchmarks.
  - 1 disagrees: IRIS Mixed Benchmarks Easy. KovaaK's holds IRIS Smoothbot
    Easy in its Clicking category, and Evxl's counts put it under Tracking,
    in PRECISE.

  Three more can't be compared. PureG S1 - Worthless doesn't join, and kl2 -
  Reflex by dummy names nothing. Coach Ben - VALORANT Strafe Aim Benchmark's
  bundled file holds 8 scenarios where KovaaK's now serves 11, which is the
  importer's drift check to report, not this proposal's.
- **Evxl's finer level has no second source, and two sheets confirm it.**
  Where Evxl subdivides one of KovaaK's categories, KovaaK's can't say where
  the subdivision falls. The maintainer's screenshots of Evxl's own sheets,
  shared in chat on 2026-10-04, match the slice row for row on both
  benchmarks they show. Voltaic Intermediate S5 has 18 scenarios, in nine
  subcategories of two where KovaaK's has three categories of six. Viscose
  S2 Medium has 39.
- **One or two levels.** Of the 260, 181 name both levels. 22 name
  categories only. 56 name one level that Evxl stores as subcategories under
  an unnamed category. 1 names nothing. No benchmark mixes named and unnamed
  subcategories.
- **Loose ends in the data.** 16 names carry leading or trailing spaces. Two
  colors use the short form `#FFF`. One sharecode appears on two entries,
  with the same layout. One entry has an empty sharecode.
- **Two groups can share a name across a category boundary.** CONTINIUM
  TacFPS Benchmarks E1 has MICRO as the last subcategory of FLICKING and the
  first of DYNAMIC, and vAim Benchmarks v1 has Blending on both sides of the
  boundary between Tracking and Switching.
- **The grid can merge cells without a license.** dash-ag-grid 35.3.0 bundles
  AG Grid 35.3.1, whose Community build includes cell spanning
  (`enableCellSpan` on the grid, `spanRows` on a column). It merges
  neighboring cells with equal values, over the rows as displayed. The
  merges were checked through a sort, a filter, and a whole-row update
  transaction.
- **A whole group's label fits its cell.** The 1,856 named groups draw as
  1,854 labels once same-named neighbors merge, and in a bold 11 px
  uppercase label every one fits its merged cell. That is a calculation from
  letter widths measured in one Chromium-based browser, not a rendering of
  each. 72 groups are one row tall, and their authors already abbreviate
  them, such as "Sta" and "Ref". The tightest is "Static" on one row, with
  0.2 px to spare, so another browser's fonts may cut it.
- **A whole group can be taller than the window.** Four groups span 30 rows
  or more: 40 on TSK Ultimate Benchmarks - All Scenarios, 36 twice on
  Hewchy's Smoothness - VAI Complete, and 30 on TSK Static Benchmarks -
  ClickTrack. A 36-row cell is 1,511 px tall. A label centered in it is out
  of view on a fresh visit, which a reviewer measured with the prototype's
  renderers.
- **A label can follow the scroll.** A standalone grid with the table's
  options and one 36-row group was probed in a Chromium-based browser. With
  the two group columns pinned left and the label positioned `sticky`, the
  label stayed whole and in view at the start, middle, and end of the group,
  in a 546 px and a 248 px viewport. It was cut only once less of the cell
  was showing than the label is long. Without the pin the label scrolled
  away, because the unpinned columns sit inside their own sideways scroll
  container. Firefox was not probed, and neither was the app's own page.

A prototype of the recommended design, and of D1's swap alternative, is on
the local branch `claude/scenario-categories-prototype` in the maintainer's
checkout. It stamps the groups into the bundled files with a one-off script,
which is not the data path proposed here, and four fill-state tests fail on
it. It also predates the Columns menu and was not rebuilt on it, so nothing
under "The Columns menu" below has been run, and it centers its labels
without pinning. It is evidence for the grid mechanics, not a starting point
to merge.

## Design

The design below follows D1's recommendation. A different ruling changes the
"Grouped and ungrouped" section and what follows from it.

### What the table shows

A bundled benchmark's table gains up to two columns ahead of Scenario, one
per level its groups name. A benchmark with categories and subcategories
shows both. A benchmark with one level shows one, and that level is the
category, whichever field Evxl stores it in. A table with no groups is
unchanged: a plain playlist, a playlist imported by code, PureG S1 -
Worthless, and the one benchmark that names nothing.

Each column is 34 px wide, with no visible header text, and it can't be
resized or sorted. Both are pinned to the table's left edge. That keeps them
in view when the table scrolls sideways, and it is what lets a tall group's
label follow the scroll. Their cells merge down each run of neighboring rows
that share a group, and each merged cell is filled with the group's color.
The text is black or white, whichever reads better on the fill. Colors come
from the snapshot in either hex form, and any other value leaves the cell
unfilled.

Hovering a group cell names its group, in both states below. Clicking one
does nothing. Rank, Next Rank, and every other column are untouched, and the
columns add no `?sort=` name
([2026-09-27](../decision_log.md#2026-09-27-the-playlist-scenario-table-keeps-its-sort-in-the-page-url)).

The filter box matches group names in both states, so typing "arm" on
Viscose S2 Medium leaves its three Arm scenarios. Each group column supplies
its group's name as its text for the filter. Its cell value is a run key
("Where it lives"), which the filter must never match.

### Grouped and ungrouped

The table is **grouped** while it is in playlist order and the filter box is
empty. That is how a fresh visit opens. A sort, or any filter text, makes it
**ungrouped**, and clearing both makes it grouped again. Filter text that is
only spaces counts as empty.

- **Grouped.** Each group is whole, so its merged cell is tall enough for a
  vertical label. The label reads bottom to top in uppercase, as on the
  benchmark's sheet, and sits in the middle of its cell. When that middle is
  scrolled out of view, the label moves to the nearer edge of the part still
  showing, so a group taller than the window stays named. A label longer
  than its cell is cut with an ellipsis, and one longer than the part of its
  cell still showing is cut at the window's edge. Either way the cell's
  tooltip names the group.
- **Ungrouped.** The cells keep their colors and lose their labels. Each
  Scenario cell gains a second line under the scenario name: the category
  and subcategory joined by a middle dot, or the category alone on a
  one-level benchmark. Neighboring rows that still share a group keep
  merging, which only makes a taller block of color.

The state is one flag for the whole table, not a judgment per cell. A sort
and a filter both break groups apart, and one rule for both is easier to
predict than labels that appear wherever a group happens to survive. A link
that already carries a `?sort=` opens ungrouped.

In the prototype the two lines measure 39 px inside the 41 px cell, and no
column changes width between the states.

### The Columns menu

The table's Columns menu lists every column the table can work without, and
keeps each choice in the browser
([playlists.md](../specs/playlists.md#the-overview)). A row means the same
without its group cells, so the group columns are listed: `Category` and
`Subcategory`, first in the menu because they are first in the table, and
shown by default. Each entry is rendered only on a table that has that
level, the way Rank and Next rank are rendered only on a benchmark's table,
so a table without groups leaves the stored choices alone.

Hiding a group column removes that level from the table. The column goes,
its names leave the filter box, which matches shown columns only, and the
Scenario cell's second line names only the levels still shown. With both
hidden the table reads as it does today.

Two parts of the menu's mechanics need care:

- The menu fits a column it has just shown to its content. A group column
  has a fixed width, so it opts out of auto-sizing.
- A stored choice is keyed by the column's ID. The two IDs are chosen once,
  because renaming one later resets that choice.

### How the two states meet the table's other state

Grouped or ungrouped is a new piece of grid state, so it is set against each
piece the table already has, with that piece active:

- **A sort.** Any sorted column makes the table ungrouped. The Columns menu
  clears the sort of a column it hides, and a `?sort=` on a hidden column is
  cleared on arrival
  ([2026-10-05](../decision_log.md#2026-10-05-a-columns-menu-shows-and-hides-table-columns-and-kovaaks-ids-are-optional-ones)).
  When that leaves no sort and an empty filter box, the table is grouped
  again and the labels return.
- **Filter text.** Text in the filter box makes the table ungrouped,
  whatever it matches. Showing or hiding a column re-runs the filter, and
  the state doesn't change.
- **The position fill.** Its update transactions replace rows whole. The
  rows carry their group fields, and a redrawn cell reads the current state,
  so a row that streams in during a sort draws its second line.
- **The timestamp refresh.** Every 30 seconds it redraws the two timestamp
  columns and nothing else.
- **A stored column choice.** It applies as the page opens. The Scenario
  cell reads which group columns are shown when it draws. The Columns menu
  redraws no cells, so the state callback does: the grid's column state
  carries each column's visibility, and a change to a group column's
  visibility redraws the Scenario cells even when the table stays grouped or
  stays ungrouped.
- **Navigation.** The second line is part of the scenario link, so a plain
  click on it opens the scenario and a modified click opens it in a new tab,
  as on the name. The link's accessible name then carries the group names
  while the table is ungrouped, which is when the group cells have no label
  to read.

### Getting the groups

The groups come from the snapshot read the app already has. That read
validates the file once per process, indexes its entries by sharecode
without regard to case, and keeps the first listing of a sharecode that
appears twice. It serves the View on Evxl link today. The proposal extends
it and adds the join:

1. The read also keeps each entry's layout: its categories in order, each
   with its subcategories, their colors, and their scenario counts.
2. For each bundled benchmark, sum the layout's scenario counts. If the sum
   differs from the benchmark's scenario count, the benchmark gets no
   groups.
3. Otherwise walk the layout in order and hand each scenario its category
   and subcategory, with both colors. Names are trimmed.
4. If no category in the layout is named, the subcategories become the
   categories, so a one-level benchmark always has categories.

Only bundled benchmarks are joined. A playlist the user imported has its own
scenario order, which the counts don't describe.

The link's own validation stays as it is. Each entry's layout is validated
separately, so an entry whose layout is unusable has no groups and keeps its
link. A snapshot the link can't read at all costs the groups as well, and
the one warning it logs says so. Every table then renders as it does today,
and no message reaches the screen, because nothing the user asked for
failed.

**The premise, and what holds it.** The join assigns groups by position. It
is right only if the snapshot's counts, taken in order, cut the bundled
file's scenario list where the benchmark's author cut it. A matching total
doesn't show that: two groups swapped, or a boundary moved by one scenario,
keep the total and mislabel rows. Three things hold the premise:

- **The file's order is KovaaK's.** The importer writes scenarios in
  KovaaK's category order, and its drift check, which the refresh runbook
  requires, reports a file whose scenario list no longer matches KovaaK's
  ([2026-09-26](../decision_log.md#2026-09-26-a-read-only-check-finds-bundled-benchmarks-that-kovaaks-changed)).
  That check compares KovaaK's with KovaaK's. It never looks at the
  snapshot.
- **A new comparison in the importer looks at both.** The importer holds
  KovaaK's categories and the snapshot at once. For each benchmark it
  compares the groups the table would draw with KovaaK's categories. No
  group and no KovaaK's category may partly overlap: where the two meet, one
  has to contain the other. Evxl may subdivide KovaaK's categories, as it
  does on Voltaic S5, and KovaaK's may subdivide Evxl's. A group that
  straddles a boundary between two of KovaaK's categories fails. The
  comparison runs at generation and in the drift check, and each reports a
  benchmark that fails by name.
- **A benchmark that fails gets no groups.** Its playlist code goes on a
  short exclusion list beside the join, kept by hand, because each failure
  needs a look and usually a report upstream. The list starts with IRIS
  Mixed Benchmarks Easy. The corpus test below pins that list together with
  the benchmarks whose counts don't add up.

The comparison can't see one thing. Where Evxl subdivides one of KovaaK's
categories, the subdivision rests on Evxl's counts alone, and a wrong count
there moves a subcategory boundary without crossing anything. The table
shows there what Evxl's own page shows, which is the layout the request
asked for.

A one-off script ran the comparison over the corpus, with the result in
Verified facts. The implementation PR builds it into the importer, and its
first run through the drift check should reproduce that result.

The importer also rewrites the snapshot on every run. A refresh can
therefore change a benchmark's counts before its file is regenerated, and
that benchmark then stops joining. The corpus test fails in the PR that
commits such a refresh, so it can't pass silently.

The app makes no new network call, so the user guide's
[What it talks to](../user_guide.md#what-it-talks-to) section doesn't
change.

**Alternative rejected: the importer writes each scenario's group into its
bundled file.** The link's decision weighed the same alternative for the
Evxl names and rejected it. It raises the importer's `schema_version`, which
marks all 261 files stale, and the live run that regenerates them carries
whatever thresholds KovaaK's changed upstream into the same diff
([2026-10-04](../decision_log.md#2026-10-04-a-benchmarks-scenario-page-links-to-its-evxl-page)).
For groups it costs one thing more. The playlist model would gain fields,
and the importer's drift check compares a shipped file with its rebuild by
whole-model equality. A snapshot refresh that renamed a group would then
report every affected file as drifted. What the alternative buys is bundled
files that describe themselves. The app's runtime read of the snapshot
exists either way.

### Where it lives

- **The snapshot read** is in `source/kovaaks/evxl_links.py`, with a minimal
  model of the two names the link needs. The groups need the same file
  through the same tolerant read, so it is shared, not done twice. Whether
  that module grows the layout fields or the read moves to a small module
  both features use is the implementer's call.
- **The join** runs with playlist loading in
  `source/kovaaks/data_service.py`, after the bundled files load. Its result
  is a side table keyed by playlist code and aligned with each benchmark's
  scenarios, rebuilt on every load, behind one accessor. It stays out of
  `PlaylistData`, as the benchmark ID does, because the importer shares that
  model
  ([2026-10-05](../decision_log.md#2026-10-05-a-columns-menu-shows-and-hides-table-columns-and-kovaaks-ids-are-optional-ones)).
  The exclusion list sits beside it.
- **The group comparison** goes in `scripts/benchmark_importer/`, where
  generation and the drift check already hold KovaaK's payload and the
  snapshot together.
- **The row builder** in `source/kovaaks/playlist_scenarios_service.py` adds
  each row's names, colors, and two run keys. A key numbers a run of
  neighbors that share a group, and it is the cell's value. The grid merges
  cells whose values are equal, so with the name as the value, two groups
  that share a name across a category boundary would merge, as the two
  benchmarks in Verified facts would today. dash-ag-grid 35.3.0 doesn't pass
  a `spanRows` function through to the grid, which leaves value equality as
  the only merge test.
- **All three row sources carry the groups.** Phase 1, the fill's streamed
  rows, and a cancelled fill's rebuild each replace a row whole
  ([2026-07-15](../decision_log.md#2026-07-15-stream-playlist-positions-with-generation-scoped-progressive-fill)).
  The fill state captures the groups at registration, as it does the
  ladders, or an update would blank the group cells.
- **The page** adds the column definitions and the menu entries for the
  levels present, turns on `enableCellSpan` beside the Columns menu's grid
  options, and seeds the state from `?sort=`. Each group column is pinned
  left and supplies its name through `getQuickFilterText`, which
  dash-ag-grid passes through as a function. A clientside callback on the
  grid's column state and the filter text sets the state and redraws the
  group and Scenario cells. It only reads the column state. Writing that
  prop from Dash also sets the column order, which is why the Columns menu
  applies its own changes through the grid API.
- **The renderers** go in `assets/dashAgGridComponentFunctions.js`, the
  fill function in `assets/dashAgGridFunctions.js` under a bare name
  ([2026-06-20](../decision_log.md#2026-06-20-reference-dash-ag-grid-grid-functions-by-bare-name)),
  and the styles in `assets/stylesheet.css`. The Scenario renderer keeps its
  anchor and click handling, and puts the second line inside the anchor.
- **The label follows the scroll** through `position: sticky`, set toward
  both the top and the bottom of the grid's scrolling viewport. That needs
  the group columns pinned, because an unpinned cell's nearest scroll
  container is the one that scrolls the columns sideways, and it needs the
  group cell's overflow left visible.

Cell spanning rules out a few grid features on the same grid: the grid-wide
text selection option, click row selection, cell selection, and editing or
row dragging on a spanning column. That list is read from the validation
rules in the installed AG Grid 35.3.1 bundle, not from its documentation.
The table uses none of them. The Leaderboard ID cell's selectable text comes
from a cell class, not from the grid-wide option, so the two don't conflict.
The implementation records the constraint beside the grid option.

### Copy

Group names and colors are the benchmark's data, not copy. They are shown as
stored, after trimming. Every string this design adds:

| Where | String | Why |
|---|---|---|
| First group column's header: accessible name and header tooltip, no visible text | `Category` | Title Case like every grid header. A 34 px header can't fit the word, so it stays in the name and the tooltip. |
| Second group column's header, same treatment | `Subcategory` | As above. Absent on a one-level benchmark. |
| Columns menu checkboxes | `Category`, `Subcategory` | Sentence case, as controls, which for one word is the header's own casing. `Subcategory` is absent on a one-level benchmark, and both are absent on a table with no groups. |
| Scenario cell, second line, while ungrouped | `{category} · {subcategory}`, such as `Control Tracking · Arm`, or one name when one level is shown | A readout, so the middle dot and no period (copy rule 2). |
| Group cell tooltip, in both states | the group's name | While ungrouped the cell holds only a color. While grouped the label can be cut, or sit in a part of a tall cell the user hasn't scrolled to yet. |

The vertical labels are the names in uppercase. That is a presentation
choice, made in the stylesheet, to match the benchmark sheets, and it
changes no stored text.

### Terms

Entries the shipping PR adds to [docs/glossary.md](../glossary.md), under
Playlists:

> ### Category
>
> One of the groups a benchmark's author sorts its scenarios into, such as
> Clicking or Tracking. Only a benchmark from the bundled library has
> categories.
>
> - Not the `Category` of KovaaK's benchmark payload. KovaaK's has one level
>   of groups, which is this app's categories on some benchmarks and its
>   subcategories on others.
>
> ### Subcategory
>
> A group within a category, such as Dynamic within Clicking. A benchmark
> with one level of grouping has categories and no subcategories.

Each entry links the playlists spec for how the table draws it, once the
spec has that section.

The table's row order keeps its existing name, playlist order. "Grouped" and
"ungrouped" name the table's two states in this proposal and in the spec
section the shipping PR writes. Neither appears on screen, so neither is a
glossary entry.

## Out of scope

- **Anything computed per group.** Evxl shows an energy figure for each
  subcategory and a benchmark-level rank. Benchmarks combine scenario ranks
  by their own rules, and the data carries none of them
  ([2026-09-27](../decision_log.md#2026-09-27-benchmark-tables-show-each-scenarios-rank-and-the-gap-to-the-next-one)).
  This proposal draws the groups and computes nothing from them.
- **Groups on other surfaces.** The Scenario Performance page's scenario
  dropdown and the Playlists overview stay as they are.
- **Groups for playlists imported by code.** Nothing upstream describes
  them. A benchmark that Evxl lists but the corpus lacks gets groups when it
  joins the corpus, not when a user imports its code.
- **Sorting by group, and collapsing a group.** Playlist order already
  groups the table. Collapsible groups are AG Grid's row grouping, which is
  an Enterprise feature.
- **Pinning the Scenario column.** The group columns are pinned for the
  label's sake. Scenario still scrolls sideways with the rest.
- **Fixing PureG S1 - Worthless upstream.** Its counts disagree between Evxl
  and KovaaK's. The table simply shows it without groups.

## Delivery plan

One implementation PR, once D1 is ruled, with no dependencies. Its first
step puts the comparison where it will keep running:

- The importer's group comparison, at generation and in the drift check,
  with its tests. Then one run of the drift check over the corpus, which
  should name IRIS Mixed Benchmarks Easy and no other benchmark, and goes in
  the PR.
- The shared snapshot read and the join, the row fields on all three row
  paths, the gated and pinned column definitions and their menu entries, the
  state flag and its callback, the two renderers, the styles, and the tests
  below.
- The shipping docs in the same PR:
  - a decision-log entry, which records the comparison's result and that
    Evxl's finer level has no second source;
  - the playlists spec, for the columns, the two states, the menu entries,
    and the join;
  - the glossary, from the Terms block;
  - the user guide's Playlists and Benchmarks section;
  - the product inventory;
  - `docs/architecture.md`, for the join and the row fields;
  - the importer readme, for the comparison, the exclusion list, and its
    note on the app reading the snapshot, which names only the link;
  - the release contract's comment on the snapshot, for the same reason;
  - the README's Features line for the scenario table, amended in place;
  - the roadmap's Shipped list.

  The PR also deletes this proposal.

The prototype predates the Columns menu and the renamed row fields. The
implementer builds on current `main` and takes the grid mechanics from the
prototype, not its code.

Recommended implementer: `claude-opus-5-5` at high. Once D1 is ruled the
spec is settled, and unit tests plus one live check verify it. The prototype
and the tall-group probe show cell spanning, the state flag, and the
following label each working alone. What is left to discover is how they sit
together beside the Columns menu, and the live check below covers that.

## Testing

- **The join**, table-driven, on small snapshot fixtures:
  - a two-level layout, a one-level layout stored as subcategories, and a
    layout that names nothing;
  - counts that don't add up to the scenario count;
  - a boundary moved by one scenario with the total unchanged, which changes
    which group the scenario beside it lands in;
  - a code that differs from its sharecode only in case;
  - a sharecode on two entries, where the first listing is the one used;
  - padded names, a short-form color, and a color that is not a hex value;
  - an entry whose layout is unusable, which gets no groups and keeps its
    Evxl link;
  - a code on the exclusion list, which gets no groups;
  - a missing snapshot, one that is not valid JSON, and one in an unexpected
    shape, each of which leaves every benchmark without groups and without
    its Evxl link.
- **The importer's comparison:** groups that begin where KovaaK's
  categories do pass. Groups that subdivide a KovaaK's category pass, and so
  do KovaaK's categories that subdivide a group. A group that straddles a
  boundary between two of KovaaK's categories fails, at generation and in
  the drift check, and names the benchmark.
- **The corpus:** a test pins which bundled benchmarks join the committed
  snapshot by count and are not excluded. It covers which benchmarks show
  groups. It does not show where their groups fall, which the importer's
  comparison does.
- **The row builder:** a grouped row carries its names, colors, and keys.
  Two neighboring groups with one name get different keys. A playlist's row
  carries none of the fields. A second-phase row and a cancelled fill's
  rebuilt row carry the same group fields as the first-phase row.
- **The page:** a two-level benchmark gets both columns ahead of Scenario, a
  one-level benchmark one, and a playlist none. Each group column is pinned
  left, opts out of auto-sizing, and supplies its name as its filter text.
  The Columns menu lists the same levels first, shown by default. A `?sort=`
  value opens the table ungrouped, and no value opens it grouped.
- **Gates:** the standard local validation in AGENTS.md, including the docs
  test for this file's placement and links.
- **Live check**, in Edge and in Firefox, on Viscose S2 Medium, Voltaic S5.5
  Intermediate, a one-level benchmark, and a playlist imported by code, in
  both themes:
  - playlist order shows the merged, labeled cells, matching Evxl's sheet;
  - on Hewchy's Smoothness - VAI Complete, at the start, the middle, and the
    end of its 36-row group, each label is in view and hovering either cell
    names its group, at the table's normal height and at its 300 px
    minimum;
  - sorting by Last Played drops the labels, adds the second line, and moves
    no column;
  - clearing the sort restores the labels;
  - typing "arm" in the filter box leaves the three Arm scenarios;
  - typing a digit leaves the same rows with the group columns shown as with
    them hidden, so no run key is matched;
  - typing only a space leaves the table grouped;
  - the position fill, with a username set, leaves the group cells intact
    while rows stream in, grouped and ungrouped;
  - hiding Subcategory through the Columns menu removes the column and its
    name from the second line, with a sort active and with filter text
    typed, and showing it again leaves the column 34 px wide;
  - a stored choice that hides a group column opens the table that way after
    a reload;
  - hiding a sorted column through the menu makes the table grouped again;
  - a plain click on the second line opens the scenario, and a Ctrl-click
    opens it in a new tab.
