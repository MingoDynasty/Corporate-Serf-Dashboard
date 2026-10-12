# 2026-07-12: Rank-Fetch Failure Degrades To The Last Cached Rank

Status: Superseded in part, for the passive red/yellow toasts of the
three-tier toast model in Constraints below, by the
[2026-08-03 notification-layer entry](2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy.md)
(passive renders state the condition in place; manual Refresh keeps all
three tiers). The fallback semantics are unchanged and remain Accepted.

Decision: When `get_scenario_rank_info` has resolved a leaderboard but the
live rank fetch fails — either an unreachable endpoint (`RequestException`) or
a successful-but-unusable, schema-invalid response (`ValidationError`) — it
falls back to the last cached rank (read via `_cached_rank`, ignoring the
rank-cache TTL) instead of returning UNKNOWN. Both failure modes route through
the shared `_stale_rank_fallback` helper. UNKNOWN is reserved for the case
where there is genuinely nothing cached to show. `force_refresh=True` inherits
the same fallback — a failed forced refresh showing last-known still beats
"N/A".

Rationale: the app should never display less than it already knows, and the
behavior was already inconsistent — the Playlists overview reads ranks with
`allow_network=False`, which serves TTL-expired cached ranks, so a transient
KovaaK's failure made the overview show a percentile while Home and the
playlist-scenarios page showed "N/A" for the same scenario. This extends the
existing graceful-degradation precedent in the same function
(`_with_leaderboard_total` keeps a valid rank when the total-players fetch
fails).

Constraints:

- **Read-only.** The fallback path never writes the cache — no
  `_save_rank_monotonic`, no `_write_json`. A write would bump the cache
  file's mtime and launder stale data into TTL-fresh on the next read.
- `scenario_name` is backfilled via `model_copy` when the cached rank lacks
  it; the leaderboard total is attached best-effort from
  `_cached_leaderboard_total` (also TTL-free) and percentile derived, mirroring
  the `allow_network=False` read path.
- The resolve-failure branch is unchanged: no `leaderboard_id` means nothing
  is cached to fall back on.
- The stale result carries a `warning_message`, driving a three-tier toast
  model on the Home rank paths: fetch fails with nothing cached → red error;
  fetch fails but a stale rank is served → yellow warning; fetch succeeds →
  green success (manual refresh only). `refresh_rank`'s green confirmation is
  suppressed by any error *or* warning. No persistent on-display staleness
  indicator is surfaced (`fetched_at` remains on the model for a future
  opt-in).
