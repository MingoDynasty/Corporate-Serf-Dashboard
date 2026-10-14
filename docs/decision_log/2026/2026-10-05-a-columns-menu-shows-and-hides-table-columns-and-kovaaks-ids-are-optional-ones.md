# 2026-10-05: A Columns Menu Shows And Hides Table Columns, And KovaaK's IDs Are Optional Ones

Status: Superseded in part, 2026-10-14, by
[Median and best](2026-10-14-the-run-lists-columns-menu-offers-median-and-best-off-to-start.md):
"What the menu lists" gains, on Run History alone, a choice that is not a
column, drawn after the columns with an id of its own shape. D1, D2, one
remembered checkbox per choice, and both playlist tables' menus stand.

The app knows the KovaaK's leaderboard ID of every scenario it has resolved
and the benchmark ID of every bundled benchmark, but it showed neither, so
trying a KovaaK's API request by hand meant digging the number out of a file.
The Playlists table and a playlist's scenario table now each have a Columns
menu that shows or hides any column and remembers the choice in the browser.
Each table also has one ID column that starts hidden, so both pages look as
they did until the menu is used. A sort on a column the user has hidden is
dropped, because the rows would otherwise be ordered by something off screen.

**Rulings.** Ratified (user) 2026-10-05, on the proposal
([PR #334](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/334)),
after two review waves in which every reviewer endorsed both rows.

- **D1. The IDs are optional columns, behind a menu that covers every
  column.** One ID column per table, hidden by default, and a **Columns** menu
  that lists every column the table can work without. Rejected: a menu that
  lists only the ID column, and a "Show IDs" switch, which both put a control
  on a page every user sees for a need only an API caller has; a hover tooltip
  on the name cell, whose text can't be selected and which nothing on screen
  announces; and no UI, which leaves the lookup a file search.
- **D2. Choices are remembered in the browser, one set per table.** Each
  column's shown or hidden state is kept in local storage, as the Show hidden
  switch is, and the scenario table's set is shared by every playlist. A
  browser that has never opened the app shows the defaults, which fails toward
  the IDs being hidden; the celebration setting accepted the same costs
  ([2026-09-02](2026-09-02-the-celebration-setting-is-browser-local-on-the-settings-page.md)).
  Rejected: the URL, as the sort uses, because which columns a user reads is a
  standing preference and not part of one visit; one set per playlist, which
  multiplies the stored state for no stated need; the settings file, which
  needs a server write path and a schema stamp for a display preference; and
  no memory, which makes hiding a column pointless.

**What the menu lists.** Every column the table can work without, in table
order. The rule is a property, not a list: a column the table's structure
depends on is never listed. That is the name column, because the row means
nothing without it and it is the link into the row, and the overview's action
cells, because they are the only way to hide or delete a playlist.

- Overview: Type, Benchmark ID, Played, Runs, Last Played, Median Percentile,
  Lowest Percentile.
- Scenario table: Leaderboard ID, Last Played, Runs, Position, Total Players,
  Percentile, PB Score, PB Date, PB cm/360, PB Accuracy, with Rank and Next
  Rank after PB Score on a benchmark's table only.

A checked column is shown. A change applies at once, and the menu stays open
until an outside click or Escape, so several columns can be set in one visit.
Every column is shown by default except the two ID columns. The checkbox
labels are sentence case, as controls, while the headers they name keep Title
Case
([2026-09-14](2026-09-14-app-copy-follows-one-set-of-rules-and-the-em-dash-is-gated-out.md)).
They are two lists kept by hand; the labels are not derived from the headers.

**One persisted checkbox per column, never one checkbox group.** Dash stores a
persisted prop as the pair of the chosen value and the layout's default, and
drops the stored value when the default no longer matches. A group's value is
the list of shown columns, and that list's default differs between a
benchmark's table and a playlist's, so moving between the two would reset the
choice every time, and a column added in a later release would reset it once
more. With one checkbox per column, each default is a constant: checked for a
default-shown column, unchecked for an ID column, the same on both kinds of
table. A benchmark-only column's checkbox is rendered only on a benchmark's
table, so a playlist's table leaves its stored value alone. The checkbox ID,
`{"type": <menu ID>, "column": <column ID>}`, is the storage key
(`_dash_persistence.<id>.checked.true`), so renaming a menu or a column ID
resets that one stored choice once.

**The menu's dropdown stays mounted while closed.** Measured on the real pages
in headless Edge on 2026-10-05 (dash 4.4.1, dash-mantine-components 2.8.0): a
popover that unmounts its closed dropdown brought a checkbox back in its old
state. Hide a column, close the menu, open it again, and the checkbox read
checked beside a hidden column, and the first click on it did nothing. The
cause was read in Dash's renderer source, not traced at run time: a component
that mounts as a new render draws from the props its parent last passed down,
not from its current ones. With `keepMounted` set on the popover, the same
steps showed the checkbox unchecked and the first click showed the column.
The stored choices still reach the grid as the page mounts, before the menu
is ever opened.

**The popover traps focus, and does not return it.** The dropdown renders in
a portal at the end of the page, out of reach of the keyboard otherwise, so
opening the menu moves focus to its first checkbox. `returnFocus` stays off.
It hands focus back to the button on every close, including one caused by a
click on another control, and that click still lands. With it on, text typed
into the filter after such a click went to the button instead: the first
space reopened the menu and the second flipped a checkbox, which hid the
column just shown and stored that (found in review of PR #344, and measured
on both tables on 2026-10-05). Escape returns focus to the button without it.

**One clientside callback per table applies the checkboxes through the grid
API.** It is the app's first pattern-matching callback, over that menu's
checkboxes. It runs as the page mounts, with the stored values, and on every
change, and does four things in order:

1. `setColumnsVisible` for the shown set and for the hidden set.
2. Clears the sort of every hidden column, with `applyColumnState` and
   `sort: null`. A hidden column otherwise keeps its sort.
3. Re-runs the quick filter, with `onFilterChanged`. The proposal listed
   three steps and not this one. AG Grid matches the quick filter against
   visible columns, but on a visibility change it only drops the filter's
   cached text and filters nothing again. Without this step, with `2336` in
   the filter, hiding Benchmark ID left its row on screen, and showing the
   column again left no rows, each until the text was next edited (found in
   review of PR #344, and measured on both tables on 2026-10-05).
4. `autoSizeColumns` on the columns it just showed. On the proposal's
   prototype (2026-10-04), a column shown through the API was not sized, and
   one shown as the page opened came up at its minimum width and clipped its
   header. With this step, on the real pages, Benchmark ID sized to 145 px
   and Leaderboard ID to 154 px after a toggle, a reload, and an in-app round
   trip alike (2026-10-05).

Step 4 fits only the columns a run showed, so a toggle never undoes a width
the user set by hand. Every other column is left to the grid's own autosize,
and for that to work both grids turn column virtualization off
(`suppressColumnVirtualisation`).

With virtualization on, AG Grid renders only the columns inside the window. A
stored choice changes which columns those are as the page opens, and the
grid's own autosize, which runs right after the callback's first run, then
left each column that had just come into the window at its minimum width,
narrower than its header. With Position, Total Players, and Percentile stored
as hidden, a benchmark's table in a 1920 px window opened with PB cm/360 and
PB Accuracy clipped, on every load (found in review of PR #344, 2026-10-05).
Which stored sets clipped depended on the window width, the data, and the
browser. Why AG Grid sizes such a column to its minimum was not traced.

Two fixes that fit the columns again were tried first and rejected:

- *In the same task as the first run.* In the review's probe it cleared the
  reported sets and clipped three others.
- *Two animation frames later.* It cleared every reported case in Edge. In
  Firefox it clipped sets that had been whole without it: 18 of 26 stored
  sets on a benchmark at 2000 px. A fit timed by frames or by a delay has a
  browser, a width, or a machine where it runs too early.

With every column rendered there is nothing to time. None of the review's
stored sets clipped a header: 26 sets on a benchmark, in Edge at window
widths from 1366 px to 2400 px and in Firefox 157 from 1920 px to 2400 px, 22
on a playlist, and 16 on the overview (measured 2026-10-05). The tables have
at most 13 columns, so rendering them all costs nothing visible.

Turning virtualization off also changes the default view in a narrow window.
Before, a column scrolled out of view when the page opened kept AG Grid's 200
px default, which a benchmark's table showed from 1680 px down. Now every
column is sized to its header and its content, whether the page or the menu
showed it.

Only the newest run of the callback applies anything. Each run waits for the
grid API on its own timer, so a run that started earlier can finish later,
and it would put its older values back over the newer ones.

It never writes the grid's `columnState` prop, which dash-ag-grid applies with
`applyOrder: true`, and never resends column definitions, whose `sort` and
`hide` AG Grid reapplies over the user's own. For the same reason the ID
columns declare `initialHide`, never `hide`. The control and the callback body
live in one module both pages import. The server never learns which columns
are shown: rows always carry every field, and hiding Position, Total Players,
or Percentile stops none of their fetches.

**Sort: hiding a sorted column clears its sort.** This amends the ruled sort
contract
([2026-09-27](2026-09-27-the-playlist-scenario-table-keeps-its-sort-in-the-page-url.md)),
and D1's ratification covers the amendment. That entry has Back and Forward
restore an entry's sort, and a reload or a copied link keep it. For a sort on
a hidden column neither holds any more. The server cannot know which columns
the browser hides, so on arrival it seeds the sort from `?sort=` as before;
the callback then hides the column and clears that sort, the grid publishes
its new state, and the existing address writer removes that name. Other sorts
in the value are kept, as are the other query parameters and the hash, and no
history entry is added. Showing the column again does not bring its sort back.

The ID columns are not sortable. A sortable column on the scenario table
needs a name in `?sort=`, and the address writer stops writing for as long as
a sorted column has none, which would silently end sort memory.

**Two states are accepted, not bugs.**

- *The overview can show Last Played with its rows in name order.* Its
  default sort, Last Played newest first, is declared in the column
  definition and seeded on every mount. Hiding Last Played clears it, and the
  rows fall back to name order, including when they rebuild. Showing Last
  Played again leaves name order for the rest of that visit, and the next
  page load sorts by it again. The column definition is not changed to avoid
  this.
- *A status line can report on columns that are hidden.* Each status line
  reports on a fetch, not on a column, so "Updating positions from KovaaK's…"
  and the two username lines read the same with Position, Total Players,
  Percentile, or both percentile columns hidden.

**Benchmark ID comes from a side table, not from the model.** The bundled
loader reads `generated_from.kovaaks_benchmark_id` from each bundled file's
raw text into a table keyed by playlist code, rebuilt on every load, as it
already collects the seed's name and ID pairs. `PlaylistData` gains no field,
because the benchmark importer shares the model: its drift check compares a
shipped file with a stamp-free rebuild by whole-model equality
([2026-09-26](2026-09-26-a-read-only-check-finds-bundled-benchmarks-that-kovaaks-changed.md)),
so a field would report all 261 bundled files as drifted, and the importer
would start writing it into every file it regenerates.

- Only bundled files are read, so a user file's stamp is ignored. A playlist
  imported by code has no benchmark ID and reads `N/A`.
- A missing or malformed block reads as no ID and never stops the file from
  loading.
- When two bundled files claim one code, the table holds the ID of the file
  that won it.
- Validation stays the only judge of a broken file. The loader validates the
  text first and reads the stamp with a second, tolerant parse after it. One
  `json.loads` in place of both raises an error the loader does not catch, so
  a file that isn't valid JSON would lose its startup warning. The second
  parse costs about 10 ms over the 261 files (3.8 MB, measured 2026-10-05).

**Leaderboard ID comes from the name-to-ID mapping.** That is the value the
app itself sends to KovaaK's, not the copy embedded in the playlist file. The
two differ when a learned entry has replaced the seeded one, or when the seed
left the name out because two bundled files embed different IDs for it
([2026-07-20](2026-07-20-seed-leaderboard-ids-from-the-bundled-benchmark-corpus.md)).
One name is in that state today: CB SmoothTrack, which one file gives as
97841 and two give as 92603. The mapping is the right source in both cases,
because it names the leaderboard the Position beside the cell came from. A
scenario the app hasn't resolved reads `N/A`, which includes that excluded
name on an install with no username, until a lookup learns an ID for it.

The table builds rows on three paths: the first paint, the fill's streamed
rows, and a cancelled fill's rebuild. The last two replace a row's data
whole, so a path that dropped the field would blank the cell. All three go
through one row builder, which reads the mapping. The fill looks a position up
before it builds the row, so a streamed row carries an ID that lookup just
learned.

**Both ID columns.** The value is bare digits, such as `184106`, with no
thousands separator, because it gets pasted into a request. The cell's text
can be selected, through one cell class that sets `user-select: text`; the
grid-wide `enableCellTextSelection` option is not used. On the overview every
other cell opens the playlist on a click, so the Benchmark ID cell is left
out of that navigation, as the action cells are: a double-click is two
clicks. Each header carries a tooltip saying what the number is.

**Superseded in part (2026-10-12).** The cell class is gone. One stylesheet
rule now makes every cell's text selectable on both tables, and only the
Playlist name cell navigates, so the Benchmark ID cell needs no exception
([2026-10-12](2026-10-12-on-both-playlist-tables-only-the-name-navigates-and-cell-text-can-be-selected.md)).

**Unchanged.** Column widths and column order are still not remembered. The
quick filter keeps matching visible columns only, which is AG Grid's default,
so typing an ID finds a row only while the ID column is shown. No cache,
setting, network path, or notification is touched.

**Out of scope.** An ID readout on the Scenario Performance page, for a
scenario in no playlist; a reset or show-all control; reordering columns from
the menu; a copy button in the ID cell; and skipping the fetch for a hidden
column.

**Provenance.** Proposal in PR #334, ratified 2026-10-05. Shipped in
PR #344.
