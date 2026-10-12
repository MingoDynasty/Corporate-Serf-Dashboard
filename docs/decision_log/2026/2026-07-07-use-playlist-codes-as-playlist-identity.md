# 2026-07-07: Use Playlist Codes As Playlist Identity

Status: Accepted (bundled-root path superseded in part by the 2026-07-11
playlist-overview entry: the loader's first root is now
`resources/benchmarks/`, not `resources/playlists/`)

Decision: Treat KovaaK's playlist `code` as the app's playlist identity everywhere: the in-memory `playlist_database` key, route value, selector value, import duplicate check, and import filename suffix. Playlist names are display-only labels. Selectors receive finished `{label, value}` options from the service; labels become `Name (CODE)` only when duplicate names need disambiguation.

Why: KovaaK's playlist names are not unique, so name-keyed storage silently dropped later same-named playlists and made those playlists unreachable even by their stable code routes. Codes are already user-facing through share-code imports and `/playlists/{playlistCode}` URLs, so they are the stable identity to preserve.

Consequences: The startup loader scans top-level JSON files from `resources/playlists/` first and `data/playlists/` second, sorted within each root by `(filename.casefold(), filename)`. The first occurrence of a code wins; duplicate-code files are skipped with a warning naming both files, and startup warnings are buffered until the UI mounts so they become visible notifications instead of being dropped outside Dash callback context. This supersedes the 2026-07-05 proposal call that user-root files should win: the final rule is bundled-wins because bundled benchmark files carry rank data and share-code imports do not. New imports write atomically to `data/playlists/{sanitized name} [{code}].json`; importing an existing code is refused with a user-visible message naming the existing playlist. The `data/playlists/` root may be absent on clean checkouts and is created on first import. Legacy user imports under `resources/playlists/` are a clean break, not migrated; owners preview and remove ignored legacy files manually with `git clean -Xn resources/playlists` then `git clean -Xf resources/playlists`, re-importing anything still wanted by share code.
