# 2026-07-18: Leaderboard Mapping Reads Through an mtime-Revalidated In-Memory Mirror

Status: Accepted

Decision: `get_cached_leaderboard_id` serves lookups from a module-level parsed
copy of `scenario_name_to_leaderboard_id.json`, revalidated on every read by
comparing the file's identity — `(path, st_mtime_ns, st_size)` from one
`stat()` call — against the signature recorded when the copy was parsed. In
cache-policy terms: read-through population, write-around writes
(`save_leaderboard_id` still writes only the file), revalidate-on-read
coherence. Disk remains the source of truth; memory is a verified mirror. The
check-and-load runs under `_CACHE_IO_LOCK`, which `_write_json` also holds, so
lookups cannot interleave with in-process writes.

Why: The mapping file is a whole-store key-value file (~140KB, ~1,000 entries,
append-mostly immutable facts) consulted once per rank lookup, so every point
lookup paid a full parse. The playlist overview's "Show hidden" toggle made
this visible: rebuilding all 217 rows performed 1,062 cache-only rank lookups
and re-parsed the same file 1,062 times (~150MB of JSON) — measured at 0.77s
per toggle, and again on every 1s warmup-interval repaint. The mtime cache
alone cut the build to 0.19s; per-build memoization alone reached only 0.44s
because playlist overlap is modest (1,062 lookups over 659 distinct scenarios,
1.61x), so the per-lookup parse, not duplication, was the dominant cost.

Alternatives considered: (a) a loading spinner — rejected: the row-build
callback is shared with the warmup interval and refresh-store bumps, so any
`dcc.Loading`/`running=` indicator flashes on every automated repaint, and it
decorates waste rather than removing it; (b) per-build memoization of rank
resolution in the overview service — deferred, not rejected: it would add
snapshot consistency (the R11 property scenario stats already have) and take
0.19s to 0.11s, but is no longer the headline fix; (c) write-through (updating
the in-memory copy in `save_leaderboard_id` instead of revalidating) —
rejected: it maintains coherence only for writes made through this process's
write path, and the cache conventions explicitly support external mutation
(deleting `data/cache/` mid-run, other processes); trusting memory
unconditionally would invert the source of truth. As a redundant addition on
top of revalidation it buys one ~1ms parse per rare write at the cost of a
three-way coherence invariant (file, dict, signature) in the write path;
(d) SQLite — unchanged from the 2026-06 cache-layer decision: indexed point
reads would dissolve this whole class of cost and subsume this fix, but the
migration stays parked behind its documented triggers (rank history,
multi-record queries, transactional guarantees).

Consequences: `api_service` is no longer fully stateless — this one file has
an in-memory mirror, with the invariant that every serve is preceded by a
fresh `stat()` proof. The signature includes the resolved path so tests that
repoint `CACHE_DIR` cannot alias a stale copy; `st_size` guards against
same-mtime rewrites on coarse-timestamp filesystems. Metadata revalidation
inherently cannot detect a rewrite that preserves both size and timestamp
(deliberate `os.utime` forgery after an in-place edit — the known limit of
every mtime-keyed cache, `.pyc` included). This is an accepted risk, not an
oversight: the PR #147 review asked for a bounded forced refresh and a
60-second re-parse backstop was briefly added, then removed at the
maintainer's direction — a periodic redundant reload with no intervening
write contradicts the cache's purpose (fast reads until the next write), no
realistic writer forges timestamps (atomic replace, editors, and restores
all shift mtime_ns or size), and the only actor who could is the single
user poisoning their own local cache. A content-hash key was also rejected:
it must read the whole file per check (~146ms vs ~27ms per toggle build for
`stat`), returning a third of the original cost to buy a guarantee only the
forgery scenario needs. A regression test pins the accepted behavior
(forged rewrite served until the next genuine write) so it reads as
deliberate. A missing mapping file no
longer logs a read-failure warning per lookup (the stat short-circuits the
read), and a malformed file warns once per file version instead of once per
lookup. All `resolve_leaderboard_id` callers (Home rank display, playlist
drill-in fill, warmup worker, watchdog rank-freshness timers) share the
parse-free path. The other cache files (per-scenario rank, totals) stay as
direct per-read files: small, per-key reads where mirroring would add
bookkeeping for little gain. Regression tests pin the single-parse property,
write-then-read invalidation, external rewrite, deletion, and malformed-file
tolerance.
