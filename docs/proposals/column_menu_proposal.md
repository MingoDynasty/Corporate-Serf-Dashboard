# A Columns Menu Shows And Hides Table Columns, And KovaaK's IDs Become Optional Ones

Status: Proposed
Date: 2026-10-04

## TL;DR

The app knows the KovaaK's leaderboard ID of every scenario it has resolved
and the benchmark ID of every bundled benchmark, but it shows neither, so
using one against the KovaaK's API means digging it out of a file. Neither ID
belongs in the default view, because it means nothing to a player who isn't
calling that API. This proposal adds a Columns menu to the Playlists table and
to a playlist's scenario table, which shows or hides any column and remembers
the choice in the browser. Each table also gains one ID column that starts
hidden.

## Decisions needed

Two product judgments. Nothing is ratified. The maintainer proposed this
shape in the design chat on 2026-10-04 and stated a lean on D1 there. A lean
is recorded below as a lean and stays open to challenge. Everything else in
this proposal, including the Copy and Terms blocks, is author-owned.

### D1 — The IDs are optional columns, behind a Columns menu that covers every column

Status: open. Maintainer lean (chat, 2026-10-04): this recommendation. The
maintainer proposed hidden-by-default ID columns with a show and hide option,
and, asked what the menu should cover, chose every column.

**Recommendation: one ID column per table, hidden by default, and a Columns
menu that lists every column except the name column and the overview's two
action cells.** Hidden by default keeps the IDs out of the view every user
gets. A general menu is a control any user understands, and it contains the
ID columns as two entries among many. The scenario table also has ten columns
on a playlist and twelve on a benchmark today, with no way to drop one a user
never reads. That table keeps gaining columns: PB Date in August, then Rank
and Next Rank in September. A menu gives a later optional column a place to
start hidden, instead of a debate about the default width.

Choosing differently:

- **A menu that lists only the ID column.** About half the build: no general
  hiding, so no sort interplay and nothing to decide about the other columns.
  It leaves a one-entry menu on a page every user sees, for a need only an API
  caller has.
- **A "Show IDs" switch beside Show hidden.** The same objection, with a
  developer term as a permanent toolbar label.
- **A hover tooltip on the name cell.** No control at all. Tooltip text can't
  be selected or copied, and nothing on screen says the tooltip exists.
- **No UI.** Both lookups work today from files (Problem lists them), and
  could be written into the API notes or wrapped in a script. This costs no
  app surface and helps nobody who would rather look in the app.

Material consequence: only the recommendation lets a user hide columns in
general. The alternatives are each a smaller build, and each leaves the
tables as wide as they are.

General hiding also narrows a ruled contract. The scenario table's sort was
ruled to survive Back, Forward, a reload, and a copied link. Under this
recommendation a sort on a column the browser has hidden is dropped on
arrival and removed from the address, because the alternative is rows ordered
by a column that is off screen (Design, Sort interplay). Accepting D1 accepts
that amendment.

### D2 — Column choices are remembered in the browser, one set per table, shared by every playlist

Status: open. No lean stated.

**Recommendation: each column's shown or hidden state is kept in the
browser's local storage, the way the Show hidden switch is.** The scenario
table has one set of choices for every playlist. A choice about Rank or Next
Rank applies to every benchmark. A browser that has never opened the app
shows the defaults, and so does one whose site data was cleared. Both fail
toward the IDs being hidden. The celebration setting accepted the same costs
when it chose the browser over the settings file
([2026-09-02](../decision_log.md#2026-09-02-the-celebration-setting-is-browser-local-on-the-settings-page)).

The table's sort was ruled into the page URL, because a sort belongs to one
visit: a fresh visit starts unsorted, and Back restores the sort it left
([2026-09-27](../decision_log.md#2026-09-27-the-playlist-scenario-table-keeps-its-sort-in-the-page-url)).
Which columns a user reads is not tied to a visit. It is a standing
preference about the table, as Show hidden is about the overview.

Choosing differently:

- **In the URL, as the sort is.** Each history entry keeps its own columns,
  and a fresh visit resets to the defaults. The ID column would need turning
  on again at every visit, and a column hidden for good would keep coming
  back.
- **One set per playlist.** A benchmark could keep a different layout from
  the next one. The stored state grows with the playlist count, and nobody
  has asked for it.
- **In the settings file.** The choice would follow the user across browsers
  and survive clearing site data. It needs a server write path, validation,
  and the settings store's schema stamp, for a display preference.
- **Not remembered.** The simplest build, and enough for a rare ID lookup. It
  makes hiding a column pointless, because the column returns on the next
  page load.

Material consequence: a URL-held or unremembered choice turns the menu into a
per-visit tool, which removes its value beyond the ID lookup. Per-playlist
memory multiplies the stored state for no stated need.

## Problem

**The IDs exist and are invisible.** KovaaK's identifies a scenario's global
leaderboard by a numeric leaderboard ID and a benchmark by a numeric benchmark
ID. The app holds both:

- The leaderboard ID of every scenario it has resolved sits in the permanent
  name-to-ID mapping, `data/cache/scenario_leaderboards/scenario_name_to_leaderboard_id.json`.
  The maintainer's copy held 3,597 scenarios on 2026-10-04. All 4,384 scenario
  entries in the bundled library carry an ID, and startup folds them into the
  mapping
  ([2026-07-20](../decision_log.md#2026-07-20-seed-leaderboard-ids-from-the-bundled-benchmark-corpus)).
  The fold leaves out a name on which two bundled files disagree. Of the
  3,219 distinct names, one is in that state today: CB SmoothTrack, which one
  file gives as 97841 and two give as 92603. Every other bundled scenario has
  its ID with no username and no network.
- The benchmark ID of every bundled benchmark sits in that file's
  `generated_from` block, as `kovaaks_benchmark_id`. All 261 files carry one,
  and the 261 values are distinct. The app never reads the block: the playlist
  model ignores unknown fields, and nothing under `source/` names
  `generated_from`.

No page shows either number. Both are parameters of KovaaK's endpoints, which
the API notes describe ([kovaaks_api_notes.md](../kovaaks_api_notes.md)). The
leaderboard scores endpoint takes `leaderboardId`. The benchmark progress
endpoint takes the benchmark ID as `benchmarkId`, a name the notes don't
spell and `get_benchmark_json` sends. Trying a request by hand therefore
starts with a text search of one of those files.

**They don't belong in the default view.** The app is public, and an ID is
noise to a player who isn't calling the API. So the need is for a place that
is easy to reach and off by default.

**The tables have no such place.** Neither table can hide a column. The
Playlists overview shows seven columns and two action cells. A playlist's
scenario table shows ten columns, or twelve on a benchmark
([playlists.md](../specs/playlists.md#the-per-playlist-scenario-table)). AG
Grid's own column chooser and columns tool panel are Enterprise modules, and
the app runs the Community build, so the grid offers nothing to turn on.

## Verified facts

Measured on 2026-10-04 with a throwaway prototype: a standalone Dash app with
one grid configured like the two pages (`columnSize="autoSize"` with a key
list, a flex name column, `unSortIcon`, rows delivered by a callback), driven
in headless Edge. Versions: dash 4.4.1, dash-ag-grid 35.3.0,
dash-mantine-components 2.8.0. The prototype is not the real pages. The
build's live check repeats each item there. Facts 8 and 9 were measured
during review, on separate probes with the same versions, and were not re-run
by the author.

1. **A persisted checkbox inside a closed popover restores without being
   opened.** With the popover closed, its checkboxes are not in the DOM. After
   a reload the clientside callback still ran once, with the stored values,
   and the grid showed the stored column set. So the restore does not depend
   on the checkboxes being mounted.
2. **The stored choice lands before the rows.** On reload the default headers
   appeared at 109 ms, the stored column set at 125 ms, and the first rows at
   132 ms. The window in which the default set shows is about one frame, with
   no rows in it.
3. **A column shown through the grid API is not sized.** `setColumnsVisible`
   leaves a newly shown column at AG Grid's default 200 px. Worse, on reload
   the column came up at its `minWidth` (90 px), which clipped the header.
   The likely cause, inferred and not traced, is dash-ag-grid's own autosize
   measuring the column before its header had rendered. Calling
   `autoSizeColumns` on the newly shown columns right after showing them gave
   the header-fitting width (151 px for "Leaderboard ID") on a toggle and on a
   reload. It did so whether called synchronously, in a zero timeout, or in
   an animation frame.
4. **A hidden column keeps its sort.** Hiding a sorted column left the rows
   sorted by it, with no header to show why. `applyColumnState` with
   `sort: null` for that column restored the unsorted order, and showing the
   column again did not bring the sort back. Within 50 ms the grid's
   `columnState` prop read `hide: true, sort: null` for the column, so a
   callback that listens to that prop sees the cleared sort.
5. **The quick filter matches visible columns only.** A value held only by a
   hidden column matched no row, and matched one row once the column was
   shown. This is AG Grid's default.
6. **One CSS rule makes a cell's text selectable.** Grid cells compute
   `user-select: none`. A cell class that sets `user-select: text` let a
   double-click or a drag select the number, without the grid-wide
   `enableCellTextSelection` option. A drag emitted no `cellClicked`. A
   double-click emitted two.
7. **Each checkbox persists on its own.** The stored key carries the
   checkbox's ID, and the value is the pair of the chosen state and the layout
   default, such as `[true,false]`. Not measured here, but known from the
   renderer's source: Dash drops a stored value whose recorded default no
   longer matches the layout's.
8. **A cleared default sort stays cleared until the next page load.** On a
   grid whose column definition declares `sort: "desc"`, as the overview's
   Last Played does, hiding the column cleared the sort. It stayed cleared
   through a `rowData` refresh and a row transaction, and a reload with the
   column still hidden ended unsorted. Declaring `initialSort` instead
   behaved the same. Showing the column again did not restore the sort in
   that visit. The next page load did.
9. **The address writer drops a hidden column's sort and nothing else.** A
   probe used the scenario page's real column definitions, sort parser, and
   address writer, over synthetic rows, with this design's checkboxes and
   callback. Hiding Runs under `runs.asc,scenario.desc` left `scenario.desc`
   in the address and kept the other query parameters and the hash. Arriving
   with a sort on a stored-hidden column removed only that sort, and removed
   `?sort=` altogether when no other sort was left.

## Design

### What the user sees

Each table gets a **Columns** button. On the Playlists page it sits between
the **Show hidden** switch and the **Import** button. On a playlist's scenario
table it sits at the right end of the filter row.

The button opens a menu of checkboxes, one per column, in table order, each
labelled with the column's name in sentence case (the Copy block lists every
label). A checked column is shown. A change applies at once, and the menu
stays open until the user clicks outside it or presses Escape, so several
columns can be changed in one visit to the menu.

The menu lists every column the table can work without:

- **Playlists overview:** Type, Benchmark ID, Played, Runs, Last Played,
  Median Percentile, Lowest Percentile. The Playlist column and the two
  action cells are always shown.
- **Scenario table:** Leaderboard ID, Last Played, Runs, Position, Total
  Players, Percentile, PB Score, PB Date, PB cm/360, PB Accuracy. A
  benchmark's menu also lists Rank and Next Rank, in their place after PB
  Score. The Scenario column is always shown.

The rule is a property, not a list of three: a column the table's structure
depends on is never listed. The name column is one, because the row means
nothing without it and it is the link into the row. The action cells are the
others, because hiding them would remove the only way to hide or delete a
playlist. A later column of that kind is left out the same way.

Every column is shown by default except the two ID columns. The page looks
exactly as it does today until the user opens the menu.

### The two ID columns

**Benchmark ID** sits after Type on the Playlists overview, so the columns
that identify a row stay together. It reads the bundled file's
`generated_from.kovaaks_benchmark_id`. A playlist with no benchmark ID reads
`N/A`: a playlist imported by code, which is built from scenario names alone,
or any other file in the user's playlist folder.

The playlist model does not change. The bundled loader reads the ID from the
raw file as it loads it, into a side table keyed by playlist code. That is
how the loader already collects the seed's name and ID pairs, and it is
rebuilt on every load as they are. Only bundled files are read, so a user
file's stamp is ignored. A missing or malformed block reads as no ID and
never stops the file from loading.

Reading the raw file must not change how a broken file is reported. Today
the loader parses and validates in one step, and reports a file that isn't
valid JSON by catching the model's validation error. A separate JSON parse
raises a different error, so the loader has to keep turning it into the same
startup warning.

The model has to stay as it is because the benchmark importer shares it. The
importer's drift check compares each shipped file with a fresh rebuild by
whole-model equality, and a rebuild carries no stamp. The check relies on the
stamp not being a model field
([2026-09-26](../decision_log.md#2026-09-26-a-read-only-check-finds-bundled-benchmarks-that-kovaaks-changed)).
Today a shipped file equals its stamp-free rebuild shape for 261 of 261
files. With a benchmark-ID field on the model that would be 0 of 261: the
next check would report every bundled file as drifted, and the importer
would start writing the field into each file it regenerates.

**Leaderboard ID** sits after Scenario on the scenario table. It reads the
name-to-ID mapping, the value the app itself sends to KovaaK's, not the copy
embedded in the playlist file. For a bundled scenario the two normally
agree. They differ in two cases: a learned entry has replaced the seeded
one, or the seed left the name out because two bundled files embed different
IDs for it, as with CB SmoothTrack. The mapping is the right source in both,
because it names the leaderboard that the Position beside the cell came
from.

A scenario the app hasn't resolved reads `N/A`. The fill resolves leaderboard
IDs before it fetches positions, so a row the fill streams in carries the ID
it found. With no username the fill is skipped, and an unresolved scenario
stays `N/A`. That includes a name the seed left out: its cell reads `N/A`
beside a file that embeds an ID, until a lookup learns one.

The table builds rows on three paths: the first paint, the fill's streamed
rows, and a cancelled fill's rebuild. The last two replace a row's data
whole, so a row built without the field would blank the cell. All three go
through one row builder, which is where the field is added.

Both columns share these rules:

- The value is bare digits, such as `184106`, with no thousands separator. It
  gets pasted into a request.
- The column is not sortable. Nobody orders a table by ID, and a sortable
  column on the scenario table would need a name in the `?sort=` address.
- The cell's text is selectable, through one cell class. On the overview,
  every other cell opens the playlist on a click, so the Benchmark ID cell is
  excluded from that navigation, as the two action cells are. Otherwise a
  double-click to select the number would leave the page.
- The header carries a tooltip saying what the number is.

### How visibility is applied

The server never learns which columns are shown. Rows always carry every
field, and the fill, the caches, and the warmup worker are untouched. Hiding
Position, Total Players, or Percentile does not stop their fetches.

- **Defaults live in the column definitions.** The ID columns carry
  `initialHide`, never `hide`. AG Grid reapplies `hide` whenever column
  definitions are sent again, which would override the user's choice. This is
  the reason the sort seed uses `initialSort`.
- **One persisted checkbox per column.** Each has a constant default: checked
  for a default-shown column, unchecked for an ID column. A single checkbox
  group would hold the list of shown columns as one value, and that list's
  default differs between a benchmark's table and a playlist's. Dash drops a
  stored value whose default changed (fact 7), so moving between the two
  kinds of table would reset the choice every time. Adding a column in a
  later release would reset it once more. Per-column checkboxes have neither
  problem: a new column is a new checkbox, and the others keep their stored
  values.
- **A benchmark-only column's checkbox is rendered only on a benchmark's
  table.** Its stored value is left alone on a playlist's table.
- **One clientside callback per table applies the checkboxes through the grid
  API.** It runs when the page mounts, with the stored values (fact 1), and
  on every change. It does three things, in order:
  1. `setColumnsVisible` for the shown set and for the hidden set.
  2. Clears the sort of every hidden column (fact 4).
  3. `autoSizeColumns` on the columns it just showed (fact 3).

  It never writes the grid's `columnState` prop, which dash-ag-grid applies
  with `applyOrder: true`, and never resends column definitions. Both would
  disturb the sort and the column order
  ([2026-09-27](../decision_log.md#2026-09-27-the-playlist-scenario-table-keeps-its-sort-in-the-page-url)).

The control and the callback body are built once, in a module both pages
import, because both tables need the same thing.

### Sort interplay

Hiding a sorted column clears its sort. Without that, the rows stay ordered
by a column that is no longer on screen, and no header shows it.

The rule also covers arrival. On the scenario table a `?sort=` value can name
a column the browser has hidden: a copied link, or Back to an entry that
predates the hiding. The server can't know, so it seeds the sort as it does
today. The callback then hides the column and clears that sort, the grid
publishes its new state (fact 4), and the existing writer removes the name
from the address. Other sorts in the value are kept (fact 9).

This narrows a ruled contract. The sort ruling has Back and Forward restore
an entry's sort, and a reload or a copied link keep it
([2026-09-27](../decision_log.md#2026-09-27-the-playlist-scenario-table-keeps-its-sort-in-the-page-url)).
For a sort on a hidden column neither holds any more. D1's material
consequence names the amendment, and the shipping PR records it (Delivery
plan).

Showing a column again does not bring its sort back (fact 4).

The overview's default sort is Last Played, newest first. Hiding Last Played
clears it, and the rows fall back to name order, including when the rows
rebuild. Showing Last Played again leaves them in name order for the rest of
that visit. The next page load sorts by Last Played again, because the
default is declared in the column definition and seeded on every mount (fact
8). So the overview can show Last Played with its rows in name order until
the page is reopened. That state is accepted, and the column definition
needs no change.

The ID columns never take part, because they are not sortable. That matters
for the address writer: it stops writing as soon as a sorted column has no
URL name, so a sortable ID column without one would silently end sort memory
for as long as it was sorted.

### What does not change

- No cache, setting, network path, or notification is touched.
- The playlist model, the benchmark importer, its drift check, and the
  bundled files are untouched.
- Column widths and column order are still not remembered.
- The quick filter keeps matching visible columns only (fact 5), so hiding a
  column removes its values from the filter. The name column can't be hidden,
  so filtering by name always works. Typing an ID finds a row only while the
  ID column is shown. A later column the filter must always match is a
  structural column, and stays out of the menu.
- The status lines stay as they are. Each reports on a fetch, not on a
  column, so it stays true when its columns are hidden. The scenario table
  can read "Updating positions from KovaaK's… 3/40" or "Positions
  unavailable. Set your KovaaK's username in Settings." with Position, Total
  Players, and Percentile all hidden. The overview can read "Percentiles
  unavailable. Set your KovaaK's username in Settings.", or show its warmup
  line, with both percentile columns hidden. The copy decision split the two
  username lines because each names the columns its own page empties
  ([2026-09-14](../decision_log.md#2026-09-14-app-copy-follows-one-set-of-rules-and-the-em-dash-is-gated-out)).
  A page showing its line with none of those columns on screen is accepted,
  and is not a copy bug.

### Copy

Every string this design adds:

| Where | String | Why |
|---|---|---|
| Both pages, the button | `Columns` | Sentence case, as a control. One word that names what the menu holds. |
| Overview menu checkboxes | `Type`, `Benchmark ID`, `Played`, `Runs`, `Last played`, `Median percentile`, `Lowest percentile` | A checkbox is a control, so its label takes sentence case while the header it names keeps Title Case. The app already pairs the two: the chart's **PB score** switch names what the table's header calls PB Score. `ID` keeps its capitals. |
| Scenario table menu checkboxes | `Leaderboard ID`, `Last played`, `Runs`, `Position`, `Total players`, `Percentile`, `PB score`, `Rank`, `Next rank`, `PB date`, `PB cm/360`, `PB accuracy` | The same rule. `ID`, `PB`, and `cm/360` keep their own casing. `Rank` and `Next rank` appear on a benchmark only. |
| Overview header | `Benchmark ID` | Title Case, as every grid header. |
| Overview header tooltip | `The number KovaaK's uses to identify this benchmark in its API.` | Says what the number is and where it is used. A sentence, so it takes a period. |
| Scenario table header | `Leaderboard ID` | Title Case, as every grid header. |
| Scenario table header tooltip | `The number KovaaK's uses to identify this scenario's leaderboard in its API.` | Mirrors the overview tooltip. |
| Either ID cell, no ID | `N/A` | The tables' existing sentinel for a value that doesn't exist. |
| Either ID cell | Bare digits, such as `184106` | A token, so it stays bare. |

### Terms

The entries this design would add to the glossary's Playlists and Leaderboard
standing sections:

> ### Benchmark ID
>
> KovaaK's numeric identifier for a benchmark. It is not the playlist code,
> which identifies the same benchmark as a playlist. Only a bundled benchmark
> carries one.
>
> - In code: `kovaaks_benchmark_id`.
>
> ### Leaderboard ID
>
> KovaaK's numeric identifier for a scenario's global leaderboard. Position,
> total players, and percentile all come from that leaderboard.
>
> - In code: `leaderboard_id`.

## Out of scope

- **An ID on the Scenario Performance page.** A scenario that sits in no
  playlist has no row in either table, so its ID stays a file lookup. A
  readout there is a follow-up if that case turns out to matter.
- **A reset or a show-all control.** Twelve checkboxes are quick to set by
  hand.
- **Remembering column widths or order,** and reordering columns from the
  menu.
- **A copy button in the ID cell.** Selecting the number is enough for a
  rare lookup.
- **Skipping the fetch for a hidden column.** Visibility is display only.
- **The other pages.** Only these two pages have a table.

## Delivery plan

One implementation PR, gated on D1 and D2:

- The shared menu and its clientside callback, wired into both tables.
- The two ID columns: the bundled loader's benchmark-ID side table, the
  overview row's field, the scenario row's field on all three row paths, the
  two column definitions, the selectable cell class, and the overview's
  navigation exclusion.
- The tests and the live check below.
- The shipping docs in the same PR:
  - a decision-log entry, which also marks the 2026-09-27 sort entry as
    amended for a hidden column's sort, and records that the menu's labels
    follow the casing rule for controls;
  - the playlists spec, for both column lists, the menu, and the sort rule.
    Two of its sentences change: the sort bullet's "a reload or a copied link
    keeps it" gains the hidden-column exception, and the corpus section's
    "the app ignores it" stops being true of the stamp's benchmark ID;
  - the glossary, from the Terms block;
  - the user guide's Playlists and Benchmarks section;
  - the product inventory and the roadmap;
  - `docs/architecture.md`, for the new shared module;
  - `docs/kovaaks_api_notes.md`, which can now say where the app shows both
    IDs.

  The PR also deletes this proposal.

If a reviewer wants it smaller, the split is the menu first and the ID
columns second. The second depends on the first, because a hidden column
nobody can show is unreachable.

Recommended implementer: `claude-opus-5-5` at high. The mechanics are pinned
by the prototype, and unit tests plus one scripted live check verify the
build. More effort would buy polish, not correctness.

## Testing

- **The bundled loader:** a bundled file's benchmark ID lands in the side
  table. A bundled file with no `generated_from` block, and one with a
  malformed block, both load, with no ID. A user file's stamp is ignored. The
  playlist model has no new field, and the importer's existing check tests
  pass unchanged. A bundled file that isn't valid JSON still produces the
  "isn't valid JSON" startup warning and is skipped, which no test pins
  today.
- **The overview rows:** a bundled benchmark's row carries its ID, and an
  imported playlist's row carries none.
- **The scenario rows:** a first-paint row, a streamed row, and a cancelled
  fill's rebuilt row each carry the leaderboard ID for a mapped scenario, and
  none for an unmapped one. A name the seed leaves out, because two bundled
  files disagree on it, carries none until the mapping learns one.
- **The column definitions:** each ID column is hidden initially, not
  sortable, and carries the selectable class. Every other column is shown.
- **The menu:** each table's menu lists exactly its hideable columns, in
  table order, each with its Copy block label. The name column and the
  action cells are absent. Rank and Next rank appear only on a benchmark.
  Every checkbox's default matches its column's initial visibility and is
  the same on a benchmark and a playlist.
- **Navigation:** a click on the Benchmark ID cell does not open the
  playlist.
- **Live check,** scripted in headless Edge against the real pages:
  - both pages open with today's columns;
  - showing Benchmark ID reads 2594 for IFE, and showing Leaderboard ID reads
    184106 for Smoothsphere Viscose;
  - a shown ID column's header is not clipped, after a toggle and after a
    reload;
  - a choice survives a reload and a round trip through another page, with
    the menu never opened;
  - hiding a sorted column returns the table to playlist order and removes
    its name from `?sort=`, and opening `?sort=` on a hidden column does the
    same;
  - on the overview, hiding Last Played leaves the rows in name order, and
    they are still in name order after turning on the **Show hidden** switch
    rebuilds them;
  - double-clicking an ID selects it, and on the overview it does not
    navigate;
  - the relative-time refresh keeps running with Last Played hidden.
- **Gates:** the standard local validation in AGENTS.md, including the docs
  test for this file's placement and links.
