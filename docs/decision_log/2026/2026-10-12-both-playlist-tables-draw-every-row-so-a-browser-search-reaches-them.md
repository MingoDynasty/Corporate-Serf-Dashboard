# 2026-10-12: Both Playlist Tables Draw Every Row, So A Browser Search Reaches Them

Status: Accepted

A browser's own text search, Ctrl+F, could not find a row of either playlist
table unless that row was on screen or just off it. Both tables now draw
every row, so the search finds any of them and the browser scrolls the table
to the match. Each table still scrolls inside itself with its header in view. Search
matches and text selections follow the displayed row order after sorting.

**Go-ahead.** The maintainer agreed to it in chat on 2026-10-12, with no
proposal, after the investigating session and a second-opinion consult had
each recommended it. It was the second of three rows about these tables. The
other two, which cells a click acts on and which text can be selected, ship
separately.

**The defect.** AG Grid draws the rows in view and ten either side, and adds
and removes rows as the table scrolls. A browser's text search reads the
page, so a row the grid had not drawn was not there to find. Measured on
`685d16a` with dash-ag-grid 35.3.0, in a 1920x1080 window, in Edge and in
Firefox:

- The grid drew 30 rows whatever the table's length: of 33 on the Playlists
  table, of 288 with **Show hidden** on, of 60 on the longest bundled
  scenario table, and of 39 on a grouped one.
- A search for the bottom row found nothing on all four. A search for the top
  row always did.
- A row inside the ten-row margin was found, which is why the search failed
  only some of the time.

**The change.** Both grids set `suppressRowVirtualisation`. Nothing else about
the layout moves: the grid is still bounded to the window, still owns its
scrollbar, and still keeps its headers in view, which is what the
[2026-07-06 entry](2026-07-06-let-the-playlist-scenarios-grid-own-vertical-scrolling.md)
was for. That entry's remark that a bounded grid "restores row
virtualization" is the one part this supersedes.

**The second option.** Both grids also set
`suppressMaxRenderedRowRestriction`. AG Grid stops at about 500 drawn rows
unless told otherwise, and with row virtualization off it never draws the
rows past that, even when the table is scrolled to them. Measured by feeding
the Playlists table synthetic rows: at 600 rows it drew 501, and the last row
was neither in the page nor findable. With both options it drew all 600. The
Playlists table holds 288 rows on the maintainer's install with **Show
hidden** on, 261 of them bundled, and the bundled library grows.

**What it costs.**

- The Playlists table at 288 rows goes from 671 to 4,051 elements in the
  page. The scenario tables go from about 900 to at most 1,351.
- Rewriting every row of the 288-row table took about 8 ms before and 18 to
  20 ms after. The same on a 60-row table, the 30-second refresh of the
  relative times, sorting, and page loads did not move beyond run-to-run
  noise. All are single runs.
- Autosize measures the cells the grid has drawn, so it now measures every
  row and not the first 30. On the 60-row table in Firefox, Next Rank opened
  2 px wider and PB Date 8 px wider. No other column moved.

**Verified on the built branch,** in headless Firefox and Edge: every row
drawn on all four tables above, the bottom row found, and the console clean
after a reload. In Firefox the grid scrolled to the match, with its header
where it was and the page itself not scrolled. Merged category cells looked
the same as before, at the top of the table and at the bottom.

**Checked by hand.** The browser's find bar cannot be scripted, so
`window.find` stood in for it above. The maintainer tried the real one in
Firefox on 2026-10-12, on a build that held this change. With **Show hidden**
on and the Playlists table unscrolled, Ctrl+F found rows at the bottom and
scrolled the table to them with the header in view. On the 60-row scenario
table it scrolled to the last row.

**Not verified.**

- The find bar in a Chromium browser. In Edge the stand-in found the row and
  did not scroll the grid to it, so whether Chromium's find bar scrolls is
  still open.
- The cost with a KovaaK's username set, when the position fill rewrites rows
  once a second. Every check ran with no username. The full-table rewrite
  above is the nearest measurement.

**A limit this leaves.** After a sort, a search steps through its matches in
the order the rows sit in the page, which is no longer their order on screen:
on one sorted table the hits came at rows 3, 1, 13, 0, and 27. That was
already true of the rows the grid had drawn. AG Grid's `ensureDomOrder`
option fixes it, measured as 0, 1, 3, 13, 27. It is left for a change of its
own, because in one Firefox run the two builds that set it opened a table
with Next Rank at its minimum width, clipping the text, and a second run did
not repeat that.

**Follow-up, 2026-10-22.** The ordering limit is superseded: both grids now
set `ensureDomOrder`. On unchanged `120fc17`, five fresh browser contexts
for each of the overview, a 60-row table, and a grouped 39-row table
reproduced the wrong search order in Chromium 156 and Firefox 157. The
initial-layout controls passed. Chromium also reproduced the wrong
four-row drag selections in all 15 cases. With the option set, all 15
search and drag cases passed in Chromium, and all 15 search cases passed
in Firefox. Sorts used header clicks, drags used mouse input, and search
used `window.find`; the browser toolbar was not driven. Firefox's initial
mouse-drag control selected only two of four rows, so its cross-row drag
behavior remains unverified.

The Firefox sizing concern did not recur on either build in repeated
checks at viewport widths 1024, 1366, and 1920, including a persisted hidden
Next Rank column, showing it again, reloading, and sorting. Synthetic
one-point runs made the next-rank text wide enough to require more than the
column's 150px minimum. Chromium clipped some of that text on both builds
until the column was hidden and shown again; this is a separate existing
autosize issue, not evidence against `ensureDomOrder`. No sizing workaround
is added here. The original Firefox observation remains part of the
history, with its cause unknown.

**Rejected.**

- `domLayout: autoHeight`. It draws every row by letting the grid grow to
  its full height, which scrolls the page and carries the headers away. The
  2026-07-06 entry removed it for that reason.
- A larger `rowBuffer`. It costs the same, still stops at the row cap, and is
  a number that has to stay ahead of the longest table.
- A jump-to-row box, or taking over Ctrl+F. Both are new interface for
  something the browser already does once the rows are in the page.

**Unchanged.** The filter box still narrows the rows. Column virtualization
was already off on both grids.

**Provenance.** Requested by the maintainer on 2026-10-12, with no proposal.
Shipped in
[PR #362](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/362).
