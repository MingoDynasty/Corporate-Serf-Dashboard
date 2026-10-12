# 2026-04-27: Use JSON Files For Runtime API Caches

Status: Accepted (cache root superseded by the 2026-07-11 cache-relocation
entry: caches now live under `data/cache/`)

Decision: Store current API cache data as JSON files under `cache/`.

Why: The current cache use cases are simple key-value lookups with short or medium TTLs. JSON keeps the implementation transparent, easy to inspect, and low-friction.

Consequences: Cache reads must tolerate missing, malformed, stale, or partially-written files. Cache writes should be atomic where practical. Reconsider SQLite when we need rank history, multi-record queries, or stronger transactional guarantees.
