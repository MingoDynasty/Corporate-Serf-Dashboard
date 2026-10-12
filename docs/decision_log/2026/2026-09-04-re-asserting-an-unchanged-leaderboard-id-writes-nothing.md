# 2026-09-04: Re-Asserting An Unchanged Leaderboard ID Writes Nothing

Status: Accepted

Starting the app took over a minute on a beta tester's machine before any page
would draw, and restarting did not help. Every startup rewrote the same 400 KB
file about 2,500 times over, once for each scenario it had ever played, to
store IDs that were already correct. It now checks first and writes only when
something actually changed. On the measured workload that step drops from 37
seconds to under a tenth of a second, and the app stops writing roughly a
gigabyte to disk on every launch.

**The waste.** `hydrate_leaderboard_id_cache` calls `save_leaderboard_id` once
per scenario in the user's `/user/scenario/total-play` response (26 pages of
100 for the reporting tester, so about 2,500 calls). Each call was a full
read-modify-write of the entire `scenarioName -> leaderboardId` mapping, ending
in an `fsync` and an atomic replace, and it ran even when the stored ID already
matched, because `fetched_at` was refreshed unconditionally. Measured on a
Samsung 990 PRO NVMe with a 3,000-entry, 416 KB mapping: **36.9s, ~1 GB
written, 2,500 fsyncs**. The fast path measures 0.09s and writes nothing.

**Why it was invisible.** The step logs nothing on success, so it appears in
`debug.log` only as a silent gap. A fresh total-play cache skips the network
but not the writes, so the affected sessions show no API calls at all. Its cost
lands inside the warmup worker's batch window, so it is reported as part of
`Percentile warmup complete: ... elapsed=67.1s` — a line whose `processed=0
skipped=379` invites reading the whole elapsed as drain cost. It is not: the
drain is a few thousand cheap reads. **Do not derive per-operation disk latency
from that line.**

**It also stalled every request thread.** `save_leaderboard_id` holds
`_CACHE_IO_LOCK` across its fsync, so for the whole hydration any waitress
thread touching any cache file blocked behind it. That is what produced the
`waitress.queue | Task queue depth` warnings in the tester's logs, a 38-second
first Home render, and Playlists times of 26-74 seconds that barely moved when
"show hidden" was toggled — both settings sat on the same fixed floor.

**Correcting the 2026-09-02 entry.** That entry attributed the tester's ~60s to
per-file antivirus scanning making small random reads "roughly 400x slower".
A probe on the reporting machine measured **0.029 ms per cache-file open** —
reads are fine there; the cost was fsync-heavy writes. The lock-scope decision
that entry records still stands on its own merits and is not superseded; only
its supporting attribution was wrong.

**Provenance is part of "unchanged".** The skip requires the stored `source` to
match as well as the ID. `merge_seed_leaderboard_ids` refreshes seed-owned rows
whose asserted ID changed and deletes those the corpus stops asserting, while
never touching learned ones (2026-07-20 entry), so a seed-owned row that
`total-play` confirms must still be rewritten to take live ownership —
otherwise a later corpus release could overwrite the ID of a live-confirmed
mapping, or drop the row outright. An ID-only check shipped in review and was
caught there.

Promotion costs one write per row, once: the first hydration after an install
promotes the seeded rows, and a corpus release promotes only the newly seeded
names that `total-play` also covers. That one-off run is about 20% slower than
the old unconditional rewrite, because a promoting call parses the mapping
twice — the fast-path check revalidates the mirror against a signature the
previous write already moved, and the slow path then parses again (44.9s versus
36.9s on a 2,500-call workload; recorded in `docs/tech_debt.md`, and removed by
the batch upsert). Every later startup is the steady state, measured at 0.09s
and zero writes.

**The stored value is authoritative.** The check reads the mtime-revalidated
in-memory mirror (2026-07-18 entry) rather than the file, so it inherits that
mirror's one accepted blind spot and no other. A stale hit skips a write whose
only effect would have been a `fetched_at` refresh; nothing reads `fetched_at`
on these entries. Conflict refusal, malformed-value replacement, and every
write path are unchanged — the fast path is purely additive.

**Not fixed here.** Hydration still makes one call per scenario; a batch upsert
folding all of them into a single atomic read-modify-write, as
`merge_seed_leaderboard_ids` already does for the bundled seed, is left as
follow-up. `_CACHE_IO_LOCK` still serializes every cache file operation
app-wide, and the Playlists overview still reads two cache files per played
scenario per row with no memo and no dedup across rows (measured 1,595 file
opens with "show hidden" on, 52% of them re-reads within one render). Both
remain in `docs/tech_debt.md` under Performance.
