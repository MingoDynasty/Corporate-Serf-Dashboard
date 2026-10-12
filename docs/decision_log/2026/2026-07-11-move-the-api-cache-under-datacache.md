# 2026-07-11: Move The API Cache Under data/cache/

Status: Accepted

Decision: Relocate the runtime API cache root from `cache/` to `data/cache/`
as a plain path change, with no in-app compatibility migration. An existing
`cache/` directory is moved by hand after the change lands.

Why: The 2026-06-22 entry grouped user/runtime state under `data/` but
deferred the cache to a dedicated compatibility migration. The app currently
has exactly one user and the cache is fully regenerable from the API, so
migration code would outlive its single use; a one-time manual move (or just
letting the cache rebuild) covers it.

Consequences: All runtime state — logs, preferences, user playlists, and the
cache — lives under one ignored `data/` root. A legacy `cache/` root left in
place is silently ignored; `.gitignore` keeps its entry so pre-move checkouts
stay clean. Revisit an in-app migration only if the app gains users beyond
its author.
