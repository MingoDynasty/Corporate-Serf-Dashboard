# 2026-07-03: Playlists Routes Are Stable; The Bare-Route Selector Is Transitional

Status: Accepted

Decision: The playlists feature owns two routes: `/playlists` (navbar
destination) and `/playlists/{playlistCode}` (per-playlist scenario table).
The per-playlist route and its `playlistCode` URL identity are stable
contracts. The current content of the bare route — a selector dropdown plus an
empty prompt — is transitional scaffolding from milestone 1: when the
playlist-level overview (roadmap milestone 2) ships, the overview replaces the
bare-route content, overview rows navigate to `/playlists/{playlistCode}`, and
the selector dropdowns are removed from both pages.

Why: A single canonical landing route keeps the navbar destination stable
across milestones, and the human-readable playlist code is already user-facing
via the import flow. The overview is a strictly richer playlist picker than a
name-only dropdown (it surfaces last-played, aggregate percentile, and similar
metadata), so keeping the selector after it ships would be scaffolding
outliving its purpose. Distilled from the milestone-1 playlist scenarios
proposal (shipped in PRs #12, #15, #16).

Consequences: Keep the selector wiring separate enough that its removal is a
clean delete, not a refactor. Post-overview, switching playlists means
navigating back to `/playlists` and clicking a row, so the overview needs
visible row-click affordances (cursor, hover tint, full-row target). Do not
bake the selector into the per-playlist page in a way that blocks removal.

**Superseded in part (2026-10-12).** The overview's rows are no longer
full-row click targets. A click in the Playlist name cell opens the playlist
and no other cell does, so that cell text can be selected. The routes and the
hover tint stand
([2026-10-12](2026-10-12-on-both-playlist-tables-only-the-name-navigates-and-cell-text-can-be-selected.md)).
