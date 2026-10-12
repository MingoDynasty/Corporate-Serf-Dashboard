# 2026-07-06: Let The Playlist Scenarios Grid Own Vertical Scrolling

Status: Accepted

Decision: Bound the playlist scenarios page to the Mantine AppShell content
viewport and let the AG Grid use its normal layout with an internal vertical
scrollbar. The page Stack and Dash Loading wrappers form a flex column, and the
grid fills the remaining space with a 300px minimum height. Keep the existing
content-based column sizing and capped flexible Scenario column.

Why: `domLayout: autoHeight` expanded the grid to every row, so the document
scrolled and carried the column headers out of view on large playlists. A
bounded grid keeps the headers visible while the user sorts and scans scenarios
deep in the playlist, and restores row virtualization.

Consequences: Short playlists show empty grid body below their final row instead
of collapsing the grid. Very short windows may still scroll the page to preserve
the 300px usable minimum. The layout tracks AppShell header and padding variables
instead of duplicating their pixel values.

**Superseded in part (2026-10-12).** The grid no longer virtualizes its rows.
It draws every one, so the browser's own text search can reach them. The
bounded grid, its own scrollbar, and the headers that stay in view all stand
([2026-10-12](2026-10-12-both-playlist-tables-draw-every-row-so-a-browser-search-reaches-them.md)).
