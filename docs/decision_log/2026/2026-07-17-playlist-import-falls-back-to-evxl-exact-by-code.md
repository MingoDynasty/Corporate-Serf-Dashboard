# 2026-07-17: Playlist Import Falls Back to Evxl Exact By-Code

Status: Accepted

Decision: KovaaK's `/playlist/playlists?search=<code>` stays the primary lookup
for playlist import. Whenever it fails to produce exactly one usable record —
zero after the null-drop validator, or more than one match — import falls back
to Evxl's exact `playlist-by-code` endpoint
(`https://api.evxl.app/kovaaks/playlist-by-code?shareCode=<code>`) before
refusing. If the fallback also fails, the user sees the same refusal message as
before.

Why: KovaaK's search has a null-hydration quirk — for some real, public
playlists it counts the match but returns a `null` record, which the
`ignore_null_playlist_items` validator drops, so a valid playlist looks like
zero results (observed: `KovaaKsCarryingGodlikeTile`; details in
`kovaaks_api_notes.md`). There is no first-party KovaaK's by-code endpoint, and
Evxl's by-code lookup resolves arbitrary community playlists exactly.

This is the app's first *runtime* dependency on Evxl; previously Evxl was used
only by the offline `scripts/benchmark_importer`. First-party KovaaK's data
stays preferred on the happy path — Evxl's copy is cached upstream (can be days
stale) and its case-strict HTTP 400 on mis-cased codes would be a worse
default — so Evxl is consulted only when the first-party search cannot resolve
the code cleanly. The stored code is always the canonical `playlist_code` from
whichever source resolved it, never the pasted input.
