# 2026-09-27: The Playlist Scenario Table Keeps Its Sort In The Page URL

Status: Accepted (amended by
[2026-10-05](#2026-10-05-a-columns-menu-shows-and-hides-table-columns-and-kovaaks-ids-are-optional-ones):
a sort on a column the Columns menu has hidden is cleared, on arrival too, so
Back, Forward, a reload, and a copied link no longer restore or keep that one
sort)

A sort on a playlist's scenario table used to be lost as soon as you left the
page. The sort now rides in the page's address, so Back, Forward, a reload,
or a copied link reopens the table sorted the way it was left. A fresh visit
from the Playlists page still starts unsorted, in playlist order. Sorting adds
no history entries, so one Back still leaves the page.

**Ruling.** Ruled (user) 2026-09-27, in the design chat that produced the
kickoff: the sort belongs to the browser-history entry, carried in the page
URL as `?sort=`. Back and Forward restore that entry's sort; a fresh visit
(navbar, then Playlists, then a playlist) starts unsorted, because the user
is "starting a new trail rather than backtracking a breadcrumb"; a reload or
a copied link keeps it. Each tab's entries are its own, so two tabs on one
playlist keep separate sorts. One standalone PR, no proposal.

**Format and names.** `?sort=<name>.<dir>[,<name>.<dir>…]`, list order is
sort priority, `dir` is `asc` or `desc`, and the commas stay literal. The
names, ruled verbatim as address-bar copy: `scenario`, `last-played`,
`runs`, `position`, `total-players`, `percentile`, `pb-score`, `pb-date`,
`pb-cm360`, `pb-accuracy`. `SORT_URL_NAMES` in `playlist_scenarios.py` is
the one table from name to column ID; the clientside writer receives it
through `json.dumps`, never a hand copy. Column IDs are unchanged, because
other code keys on them: `AUTO_SIZE_COLUMN_KEYS`, the relative-time
refresh's column list, and `route_to_scenario_home`'s `"scenario"` check.
Names, not IDs, because `rank_sort` would put "rank" in the address and Rank
is the benchmark tier, and because a saved link survives a later field
rename.

**Restore is a server-side seed.** Dash Pages passes query parameters to
`layout` (`parse_qs(keep_blank_values=True)`, so `?sort=` arrives as `""`
and a repeated parameter as a list). A value that is not entirely valid
means unsorted, silently: empty, repeated, an unknown name, a missing or bad
direction, a duplicate name (which also caps the list at one entry per
column), or any other case or spelling. No valid part of a mixed value is
kept. Each call deep-copies `TABLE_COLUMN_DEFS`, a module constant shared
across requests, and sets `initialSort`/`initialSortIndex` on the named
columns. Never `sort`/`sortIndex`: in AG Grid 35.3.1, `SortService.initCol`
seeds a new column from either pair, but `_updateColumnState` reapplies only
`sort`/`sortIndex` when column defs are sent again, which would override the
user's header clicks. Never a `columnState` prop either: dash-ag-grid applies
a Dash-written `columnState` with `applyOrder: true`.

**Write is a raw `replaceState`.** One clientside callback reads the grid's
`columnState`, which dash-ag-grid 35.3.0 publishes when its API initializes,
after autosize, immediately on a sort, and 500 ms after a resize or a
displayed-columns change, and never after unmount. The callback ignores
anything that is not an initialized column-state array (non-empty, every
entry with a `colId`): the initial call has none, and reading that as
unsorted would strip `?sort=` on arrival. It writes only when the value
differs from the address's `sort`, so opening a sorted page writes nothing
and an invalid value is removed by the grid's first publish. It writes only
while `location.pathname` is still `/playlists/<code>`, compared raw because
Dash Pages hands the page its path segment undecoded; a row click moves the
address before the grid unmounts. `history.replaceState(history.state, "",
url)` changes only the `sort` key and keeps every other parameter and the
hash; a cleared sort removes the key. Not through `dcc.Location`, an
external constraint of dash 4.4.1: `updateLocation` pushes a new history
entry whenever a location prop changes and, with `refresh="callback-nav"`,
dispatches `_dashprivate_pushstate`, which makes Pages re-render the page;
its only listeners are `popstate` and `_dashprivate_pushstate`, so a raw
`replaceState` is invisible to Dash. The page's own Location keeps receiving
only `href`: a `pathname` output would push the pathname plus the Location's
stale `search`, which predates every rewrite.

**Rejected alternatives.**

- One localStorage sort for every playlist, the kickoff's earlier draft: it
  breaks the fresh-visit rule, the grid's unsorted first publish can erase
  the saved sort on mount, and tabs overwrite each other.
- `persistence` with `persisted_props=["columnState"]`: it also keeps column
  widths and order, and it restores on fresh visits.
- `history.state` or per-entry sessionStorage: both need a client-side
  restore that races the grid's mount, and neither can be tested with
  pytest.

**Out of scope.** The Playlists overview grid defaults to Last Played,
newest first, and remembers no sort the user picks. It writes
`Output("playlists-location", "pathname")`, so if it ever adopts this
pattern that output would carry a stale `?sort=`. Filters, column widths and
order, and a reset control are not kept either; clearing through the header
is the reset. Fast Back/Forward presses get no safeguard: the address check
cannot tell apart two entries with the same address, but a rapid
Back/Forward/Back live check did not reproduce a mismatch.

**Provenance.** No proposal: the maintainer ruled the direction and the
process on 2026-09-27. Three models reviewed the design and agreed on it:
`claude-opus-5-5`, `claude-fable-5-1`, and `gpt-6-astra`. Shipped in PR
#316.

**Superseded in part (2026-10-04).** The column ID this entry names,
`rank_sort`, is now `position_sort`, and the PB Score column's ID is now
`pb_score_sort`. The names in the address did not change, so a link saved
before the rename still sorts the table
([2026-10-04](#2026-10-04-the-scenario-tables-row-fields-use-the-words-on-screen)).
