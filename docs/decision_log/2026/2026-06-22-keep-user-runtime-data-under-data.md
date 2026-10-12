# 2026-06-22: Keep User Runtime Data Under `data/`

Status: Accepted (bundled-root path superseded in part by the 2026-07-11
playlist-overview entry: bundled playlists now live under
`resources/benchmarks/`, not `resources/playlists/`; the deferred cache move
shipped in the 2026-07-11 cache-relocation entry)

Decision: Store user/runtime app data under a repo-local ignored `data/` directory. New runtime logs belong under `data/logs/`. Existing API caches remain under `cache/` until a separate migration moves them.

Why: Logs are runtime artifacts, but they are not cache. A dedicated `data/` root keeps future runtime state such as logs, imported/custom playlists, and an eventual SQLite database grouped in one place without mixing it with source-controlled resources.

Consequences: Keep bundled/default playlists under `resources/playlists/`. Put future user-imported or user-created playlists under `data/playlists/`. If the existing API cache moves from `cache/` to `data/cache/`, handle it as a dedicated compatibility migration instead of silently changing paths.
