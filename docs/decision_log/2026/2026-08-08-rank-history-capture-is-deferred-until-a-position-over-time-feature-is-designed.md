# 2026-08-08: Rank-History Capture Is Deferred Until A Position-Over-Time Feature Is Designed

Status: Accepted

The app keeps only the latest leaderboard position per scenario, so past
positions are overwritten and cannot be reconstructed later. A proposal to
start capturing them now, ahead of any feature that uses them, was reviewed
and deferred. Score-over-time needs no capture — runs are kept as files and
can be recomputed at any time. Position- and percentile-over-time would need
capture running before they ship, but those features are ideas rather than
designs, so the project accepts losing that history until one is fleshed out.

Decision: rank-observation capture does not ship now. The revisit trigger is
concrete: the day any position- or percentile-over-time feature moves from
idea to design, that design's **first** deliverable is the capture below —
history starts when capture starts, and the gap between now and then is the
accepted, known cost. Agents: do not re-propose capture absent that trigger;
cite this entry instead. Do not silently widen any rank-cache write into a
history store either — the serving cache stays a cache.

The reviewed capture spec is preserved here so revival needs no re-derivation
(it was review-corrected twice and is believed sound): append one NDJSON line
per **fetched** observation to an append-only file under `data/` (not
`data/cache/` — capture, not cache); fields `leaderboard_id`, `username`,
`scenario_name`, `rank`, `score`, `observed_at` (UTC ISO-8601, from the
fetch), plus `total_players` as an optional best-effort join with its own
fetch moment (the rank fetch does not carry it; percentile analysis must
treat the denominator as temporally approximate). The capture boundary is
fetch-result handling, not `_save_rank_monotonic` — the `_score_is_fresh`
gate discards real observations before the monotonic writer, and candidates
the monotonic filter rejects are recorded (a worsening rank is signal). Cache
re-serves and the `allow_network` re-save of an already-cached value are not
observations. Consecutive identical observations per
`(leaderboard_id, username)` dedupe; appends are fail-soft; no reader ships
with capture.

Why: maintainer review. Position- and percentile-over-time sound useful on
paper but are unfleshed, and both are less settled than score-over-time,
which needs none of this. Capturing data for an undesigned feature class is
exactly the speculative scope this project prunes; the irreversibility
argument for capturing anyway was weighed and accepted as a known loss. The
2026-08-06 `json-vs-sqlite-storage` note had dropped the vault design's
Phase 2 ledger by taxonomy accident — this entry replaces that silence with
a deliberate call.

Consequences: every day before revival is unrecorded position history, by
choice. The existing SQLite triggers ("reconsider SQLite when we need rank
history…") are unchanged — if capture is revived it remains engine-neutral
(NDJSON re-ingests into whatever table a migration creates), so this defers
nothing about, and prejudices nothing in, the open SQLite questions.
