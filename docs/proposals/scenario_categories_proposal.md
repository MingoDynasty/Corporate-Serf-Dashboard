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

Two rulings, and nothing is ratified. The maintainer asked for the feature
in chat on 2026-10-03. On 2026-10-04 they asked whether one combined column
would do, and whether Evxl's vertical labels are worth adopting, naming a
table sorted by Last Played as the one worry. Those were questions, not
leans. Everything else in this proposal, including the Copy and Terms
blocks, is author-owned and open to challenge.

### D1 — What the group columns show when the rows leave benchmark order

Status: open

A vertical label needs its group's whole height. Evxl's table can't be
sorted, so its groups are always whole. This table sorts and filters, and
then most groups are a single 42 px row, which fits about five letters of a
vertical label. On Viscose S2 Medium sorted by Last Played, 33 of the 46
vertical labels the grid had rendered were clipped. So benchmark order can
use the benchmark-sheet layout, and the decision is what a sorted or
filtered table shows in its place.

**Recommendation: keep the two narrow columns where they are, and name each
row's group under its scenario.** In benchmark order with no filter text,
every group is one merged cell with a vertical label, as on Evxl. Under any
sort or filter text, the cells keep their colors and drop their labels, and
each Scenario cell gains a second line such as "Control Tracking · Arm". The
columns are 34 px wide in both modes, so no column moves when the mode
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
- **One horizontal column in every mode.** There are no modes and nothing
  moves. It spends that 115 px to 150 px in benchmark order too, against
  68 px, on a table that already scrolls sideways in a 1500 px window. It
  also gives up the benchmark-sheet layout the request asked for.
- **Hide the group columns outside benchmark order.** This is the least
  code. A sorted table would then say nothing about groups, which is the
  view the maintainer's question was about. The filter box also couldn't
  match a category name while a sort is active, because the grid's quick
  filter skips hidden columns.

Material consequence: the swap moves the column headers on the first click
of every sort. The single horizontal column spends 47 px to 82 px more in
the default view and doesn't look like the benchmark's sheet. Hiding leaves
a sorted table without the feature.

### D2 — Where the grouping data comes from

Status: open

Neither the bundled benchmark files nor KovaaK's hold the grouping. Evxl
does, and the repo already carries Evxl's data as the benchmark importer's
input, `resources/evxl/benchmarks.json`. For each benchmark that snapshot
lists the categories in order, each with its subcategories, their colors,
and how many scenarios each holds. A bundled file keeps its scenarios in
that same order, so slicing the scenario list by those counts gives each
scenario its group. The decision is which side does the slicing.

**Recommendation: the app joins the snapshot at startup, and the bundled
files stay as they are.** The snapshot already travels in the release zip.
The app would read it once, slice each bundled benchmark by the counts, and
keep the result in memory beside the playlist store. A benchmark gets groups
only when the counts add up to its scenario count. The benchmark files,
their schema, the `Scenario` model, and the importer don't change, and
removing the feature later means deleting the reader. A category that Evxl
renames reaches the app with the next snapshot refresh, which every importer
run already performs.

Choosing differently:

- **The importer writes each scenario's group into its bundled file.** The
  app then reads the groups from the files it already loads and never parses
  Evxl's format. The bundled files stay the app's only runtime data, as they
  are for rank ladders and leaderboard IDs
  ([2026-07-20](../decision_log.md#2026-07-20-seed-leaderboard-ids-from-the-bundled-benchmark-corpus)),
  and a snapshot refresh alone can't change what the app shows. The cost is
  a change to every bundled file. The importer's `schema_version` rises to
  3, which marks all 261 files stale, and a live importer run regenerates
  them: one Evxl lookup each, plus a KovaaK's benchmark request for every
  payload that isn't cached. That run rewrites thresholds from live data, so
  whatever KovaaK's changed upstream since each file was generated arrives
  in the same change. The importer's skip test would also need the category
  layout added to it, or a group that Evxl renames would never regenerate
  its file.

Material consequence: writing the groups into the files turns this into two
deliveries, with a corpus-wide data change and a schema bump first, and both
are awkward to undo. The join makes the app depend at runtime on a file
whose shape Evxl defines, and lets a snapshot refresh change the table with
no benchmark file changing. Both paths draw the same table.

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
group. Evxl answers the question at a glance, so this is another reason to
leave the app for it.

The question belongs to both moments in
[product.md](../product.md#when-they-ask-them). Between sessions, the look
ahead at what to work on is usually asked by group: which tracking scenarios
are weak. Just before a session, and between scenarios within one, the
player wants to pick a scenario and get playing, so the table has to give up
its structure at a glance.

Everything the feature needs is local, and it makes no network call.

### Verified facts

Surveyed against `main` at `fb2f679`, with the snapshot last refreshed on
2026-09-26.

- **The bundled files carry no grouping.** A scenario has a name, a ladder,
  and a leaderboard ID. The importer walks KovaaK's categories in order and
  flattens them into that list.
- **The snapshot does.** It has 266 difficulty entries. Each lists
  categories in order, and each category lists subcategories with a name, a
  color, and a scenario count. It holds no scenario names, so Evxl itself
  can only place scenarios by position.
- **KovaaK's has one level and no colors.** Its benchmark payload groups
  scenarios under category keys with progress, a rank, and thresholds. In
  the five payloads cached in the maintainer's checkout on 2026-10-03, those
  categories match Evxl's subcategories one for one in size and order. Their
  names differ, such as "WideWall" against "Widewall", and one payload pads
  a repeated name with a space. The category level and every color exist
  only in Evxl's data.
- **260 of the 261 bundled files join.** Matching a file's playlist code to
  a snapshot sharecode without regard to case finds an entry whose counts
  add up to the file's scenario count. One file matches only that way:
  Revosect Season 4 Easy's code differs from its sharecode in the case of
  one letter. PureG S1 - Worthless doesn't join: the file holds 14 scenarios
  and Evxl counts 12.
- **The slice reproduces Evxl's page.** The maintainer's screenshot of
  Evxl's Viscose S2 Medium sheet, shared in chat on 2026-10-04, shows all 39
  scenarios in the bundled file's order, under the groups the slice assigns.
- **One or two levels.** Of the 260, 181 name both levels. 22 name
  categories only. 56 name one level that Evxl stores as subcategories under
  an unnamed category. 1 names nothing. No benchmark mixes named and unnamed
  subcategories.
- **Loose ends in the data.** 16 names carry leading or trailing spaces. Two
  colors use the short form `#FFF`. One sharecode appears on two entries,
  with the same layout. One entry has an empty sharecode.
- **The grid can merge cells without a license.** dash-ag-grid 35.3.0 bundles
  AG Grid 35.3.1, whose Community build includes cell spanning
  (`enableCellSpan` on the grid, `spanRows` on a column). It merges
  neighboring cells with equal values, over the rows as displayed. The
  merges were checked through a sort, a filter, and a whole-row update
  transaction.
- **Every label fits in benchmark order.** In a bold 11 px uppercase label,
  all 1,854 labels fit their merged cells. That is a calculation from
  measured letter widths, not a rendering of each. 72 groups are one row
  tall, and their authors already abbreviate them, such as "Sta" and "Ref".
  The tightest is "Static" on one row, with 0.2 px to spare.

A prototype of the recommended design, and of D1's swap alternative, is on
the local branch `claude/scenario-categories-prototype` in the maintainer's
checkout. It stamps the groups into the bundled files with a one-off script,
which is neither of D2's paths, and four fill-state tests fail on it. It is
evidence, not a starting point to merge.

## Design

The design below follows both recommendations. A different D1 ruling changes
the "Two modes" section. A different D2 ruling changes only "Getting the
groups" and the delivery plan.

### What the table shows

A bundled benchmark's table gains up to two columns ahead of Scenario, one
per level its groups name. A benchmark with categories and subcategories
shows both. A benchmark with one level shows one, and that level is the
category, whichever field Evxl stores it in. A table with no groups is
unchanged: a plain playlist, a playlist imported by code, PureG S1 -
Worthless, and the one benchmark that names nothing.

Each column is 34 px wide, with no visible header text, and it can't be
resized or sorted. Its cells merge down each run of neighboring rows that
share a group, and each merged cell is filled with the group's color. The
text is black or white, whichever reads better on the fill. Colors come from
the snapshot in either hex form, and any other value leaves the cell
unfilled.

Clicking a group cell does nothing. Rank, Next Rank, and every other column
are untouched, and the columns add no `?sort=` name
([2026-09-27](../decision_log.md#2026-09-27-the-playlist-scenario-table-keeps-its-sort-in-the-page-url)).
The filter box matches group names in both modes, so typing "arm" on
Viscose S2 Medium leaves its three Arm scenarios.

### Two modes

The table is in **benchmark order** while it has no sort and no filter
text. That is how a fresh visit opens, and clearing a sort through its
header returns to it.

- **In benchmark order,** each group is whole, so its merged cell is tall
  enough for a vertical label. The label reads bottom to top in uppercase,
  as on the benchmark's sheet. A label too long for its cell is cut with an
  ellipsis and shown in full on hover. The corpus has none today.
- **Otherwise,** the cells keep their colors and lose their labels, with the
  group's name on hover. Each Scenario cell gains a second line under the
  scenario link: the category and subcategory joined by a middle dot, or the
  category alone on a one-level benchmark. Neighboring rows that still share
  a group keep merging, which only makes a taller block of color.

The mode is one flag for the whole table, not a judgment per cell. A sort
and a filter both break groups apart, and one rule for both is easier to
predict than labels that appear wherever a group happens to survive. A link
that already carries a `?sort=` opens straight in the second mode.

In the prototype the two lines measure 39 px inside the 41 px cell, and no
column changes width between modes.

### Getting the groups

At startup, after the bundled benchmarks load, the app reads the snapshot
once and builds each benchmark's groups:

1. Index the snapshot's entries by sharecode, ignoring case. Entries that
   share a sharecode are used only when their layouts agree.
2. For each bundled benchmark, look up its playlist code. Sum the entry's
   scenario counts. If the sum differs from the benchmark's scenario count,
   the benchmark gets no groups.
3. Otherwise walk the layout in order and hand each scenario its category
   and subcategory, with both colors. Names are trimmed.
4. If no category in the layout is named, the subcategories become the
   categories, so a one-level benchmark always has categories.

Only bundled benchmarks are looked up. A playlist the user imported has its
own scenario order, which the counts don't describe.

The snapshot is a read-only bundled asset. If it is missing, unreadable, or
in a shape the reader doesn't expect, no benchmark gets groups, the app logs
one warning, and every table renders as it does today. No message reaches
the screen, because nothing the user asked for failed.

Three things follow from reading the file at runtime:

- The release contract lists paths that a component opens by name. The
  snapshot joins that list, so a release can't ship without it.
- The importer rewrites the snapshot on every run. A refresh can therefore
  change a benchmark's counts before its file is regenerated, and that
  benchmark then loses its groups. A test over the committed corpus pins the
  list of benchmarks that don't join, one today, so such a refresh fails in
  the PR that commits it rather than passing silently.
- The reader keeps its own minimal model of the snapshot. The importer's
  models live under `scripts/`, outside the app package.

The app makes no new network call, so the user guide's
[What it talks to](../user_guide.md#what-it-talks-to) section doesn't
change.

### Where it lives

- **The reader and the join** sit with playlist loading in
  `source/kovaaks/data_service.py`, or in a small module beside it if that
  file's size argues for one. The result is a per-code tuple aligned with
  the benchmark's scenarios, behind one accessor. It stays out of
  `PlaylistData`, which is also the schema of the user's playlist files.
- **The row builder** in `source/kovaaks/playlist_scenarios_service.py` adds
  each row's names, colors, and two run keys. A key numbers a run of
  neighbors that share a group, and it is the cell's value. The grid merges
  cells whose values are equal, so two groups that share a name, such as
  Reading under two categories, would merge if the name were the value.
  dash-ag-grid 35.3.0 doesn't pass a `spanRows` function through to the
  grid, which leaves value equality as the only merge test.
- **All three row sources carry the groups.** Phase 1, the fill's streamed
  rows, and a cancelled fill's rebuild each replace a row whole
  ([2026-07-15](../decision_log.md#2026-07-15-stream-playlist-positions-with-generation-scoped-progressive-fill)).
  The fill state captures the groups at registration, as it does the
  ladders, or an update would blank the group cells.
- **The page** adds the column definitions for the levels present, turns on
  `enableCellSpan`, and seeds the mode from `?sort=`. A clientside callback
  on the grid's column state and the filter text flips the mode and redraws
  the group and Scenario cells.
- **The renderers** go in `assets/dashAgGridComponentFunctions.js`, the
  fill function in `assets/dashAgGridFunctions.js` under a bare name
  ([2026-06-20](../decision_log.md#2026-06-20-reference-dash-ag-grid-grid-functions-by-bare-name)),
  and the styles in `assets/stylesheet.css`. The Scenario renderer keeps its
  anchor and click handling, and wraps the anchor only in the second mode.

Cell spanning rules out a few grid features on the same grid: text
selection across cells, click row selection, cell selection, and editing or
row dragging on a spanning column. The table uses none of them. The
implementation records that as a constraint beside the grid option.

### Copy

Group names and colors are the benchmark's data, not copy. They are shown as
stored, after trimming. Every string this design adds:

| Where | String | Why |
|---|---|---|
| First group column's header: accessible name and header tooltip, no visible text | `Category` | Title Case like every grid header. A 34 px header can't fit the word, so it stays in the name and the tooltip. |
| Second group column's header, same treatment | `Subcategory` | As above. Absent on a one-level benchmark. |
| Scenario cell, second line, outside benchmark order | `{category} · {subcategory}`, such as `Control Tracking · Arm`, or `{category}` alone | A readout, so the middle dot and no period (copy rule 2). |
| Group cell tooltip, outside benchmark order | the group's name | The cell holds only a color there. No tooltip in benchmark order, where the label is on the cell. |

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
> - Not the `Category` of KovaaK's benchmark payload, whose groups are this
>   app's subcategories.
>
> ### Subcategory
>
> A group within a category, such as Dynamic within Clicking. A benchmark
> with one level of grouping has categories and no subcategories.

Each entry links the playlists spec for how the table draws it, once the
spec has that section.

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
- **Sorting by group, and collapsing a group.** Benchmark order already
  groups the table. Collapsible groups are AG Grid's row grouping, which is
  an Enterprise feature.
- **Pinning the group columns** so they stay in view during a sideways
  scroll. Scenario isn't pinned either. This is a cheap follow-up if wanted.
- **Fixing PureG S1 - Worthless upstream.** Its counts disagree between Evxl
  and KovaaK's. The table simply shows it without groups.

## Delivery plan

One implementation PR, once D1 and D2 are ruled:

- The snapshot reader and the join, the row fields on all three row paths,
  the gated column definitions, the mode flag and its callback, the two
  renderers, the styles, the release-contract entry, and the tests below.
- The shipping docs in the same PR:
  - a decision-log entry;
  - the playlists spec, for the columns, the two modes, and the join;
  - the glossary, from the Terms block;
  - the user guide's Playlists and Benchmarks section;
  - the product inventory;
  - `docs/architecture.md`, for the new startup read and the row fields;
  - the importer readme, for the note that a snapshot refresh can change
    groups;
  - the README's Features line for the scenario table, amended in place;
  - the roadmap's Shipped list.

  The PR also deletes this proposal.

If D2 is ruled the other way, an importer PR comes first: the group fields,
the schema bump, the skip-test change, and the regenerated corpus. The app
PR then reads the fields from the files and drops the snapshot reader and
the release-contract entry.

Recommended implementer: `claude-opus-5-5` at high. Once the two rows are
ruled the spec is settled, and unit tests plus one live check verify it. The
prototype branch shows the grid mechanics working, so little is left to
discover.

## Testing

- **The join**, table-driven, on small snapshot fixtures:
  - a two-level layout, a one-level layout stored as subcategories, and a
    layout that names nothing;
  - counts that don't add up to the scenario count;
  - a code that differs from its sharecode only in case;
  - a sharecode on two entries, with matching layouts and with different
    ones;
  - padded names, a short-form color, and a color that is not a hex value;
  - a missing snapshot, one that is not valid JSON, and one in an unexpected
    shape, each of which leaves every benchmark without groups.
- **The corpus:** every bundled benchmark joins the committed snapshot,
  except a pinned list that holds PureG S1 - Worthless today.
- **The row builder:** a grouped row carries its names, colors, and keys.
  Two neighboring groups with one name get different keys. A playlist's row
  carries none of the fields. A second-phase row and a cancelled fill's
  rebuilt row carry the same group fields as the first-phase row.
- **The page:** a two-level benchmark gets both columns ahead of Scenario, a
  one-level benchmark one, and a playlist none. A `?sort=` value opens the
  table in the second mode, and no value opens it in benchmark order.
- **The release contract:** a zip without the snapshot fails the check.
- **Gates:** the standard local validation in AGENTS.md, including the docs
  test for this file's placement and links.
- **Live check**, on Viscose S2 Medium, Voltaic S5.5 Intermediate, a
  one-level benchmark, and a playlist imported by code, in both themes:
  - benchmark order shows the merged, labeled cells, matching Evxl's sheet;
  - sorting by Last Played drops the labels, adds the second line, and moves
    no column;
  - clearing the sort restores the labels;
  - typing "arm" in the filter box leaves the three Arm scenarios;
  - the position fill, with a username set, leaves the group cells intact
    while rows stream in.
