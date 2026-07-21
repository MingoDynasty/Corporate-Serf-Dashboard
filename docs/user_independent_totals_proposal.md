# User-Independent Totals

Status: Proposed
Date: 2026-07-20 (split out of the leaderboard ID seeding proposal,
since shipped in PR #169 and distilled into the 2026-07-20 "Seed
Leaderboard IDs From The Bundled Benchmark Corpus" entry of
`docs/decision_log.md`)

## Problem

Without a configured KovaaK's username, the Playlists pages show N/A in
every rank column. That is correct for Position and Percentile — both
are properties of a specific user — but Total Players is a property of
the leaderboard alone: `fetch_leaderboard_total` asks the leaderboard
endpoint for one row and reads the board size, no user involved. The
reason it never shows is upstream: `get_scenario_rank_info` returns
UNKNOWN immediately when no username is configured, before resolving
anything. A fresh install (the common username-less case) gets a dead
grid where board sizes could be shown.

## Design — the totals PR

**Service.** When no username is configured, `get_scenario_rank_info`
stops returning UNKNOWN immediately. It resolves the leaderboard ID
(the seeded mapping cache, then exact search; total-play hydration is
naturally unavailable), skips the rank fetch entirely, attaches the
leaderboard total through the existing `_with_leaderboard_total`
enrichment, and returns status UNKNOWN with `total_players` populated.
The "KovaaK's username is not configured." message moves from
`error_message` to `warning_message`: once the app deliberately supports
running without a username, an unconfigured username is a chosen,
feature-limiting state rather than a failure, and the UI's established
yellow-warning degradation (introduced for the stale-rank fallback) fits
it better than red.

**No new status.** UNKNOWN keeps meaning exactly what it means — the
*rank* is unknown. The total is orthogonal enrichment, same as the
existing rule that percentile is derived, not stored. This avoids
touching the `ScenarioRankStatus` enum (stable JSON values) and the rank
cache (nothing is cached for a user that doesn't exist; the rank fetch
never runs).

**UI.** The playlist row formatter
(`format_playlist_scenario_rank_row`) currently fills Total Players only
for RANKED/UNRANKED rows; it changes to render `total_players` whenever
the value is present, regardless of status. Position and Percentile stay
N/A without a user. Totals are fetched lazily per scenario at playlist
open (a one-row leaderboard call each, cached under the existing
168-hour totals TTL) behind the existing pending/progressive UI.
Accepted cost: the first open of a playlist on a username-less install
performs one cheap totals call per scenario.

**The background worker stays username-gated — deliberately.** This rule
is uniform across this proposal, the optional import-warmup PR included:
without a username, nothing is ever fetched in the background; totals
arrive only lazily at playlist open. Why not warm totals in the
background too: the worker's mission is percentiles for the overview,
and without a username there are no percentiles — totals alone feed only
the detail grids. Its session pipeline is built around username
validation and rank fetching, so a totals-only mode is genuine new
branching through the step machinery, bought for the smallest audience
(username-less installs, usually a transient state), whose lazy cost is
already once per scenario per week behind a progressive UI.

**Home rides along.** Home does no rank fetching or caching of its own:
its Scenario Stats rank line calls the same `get_scenario_rank_info`
service and renders the result through a pure formatter
(`format_scenario_rank` in `source/pages/home.py`). The service change
above therefore reaches Home automatically — the only Home-specific work
is display: its UNKNOWN branch, today a bare `"N/A"`, gains a
totals-aware variant when `total_players` is present, e.g.
`"N/A (18,342 players)"` (exact wording is the implementer's call). One
branch plus a test.

**Docs on ship.** The "Scenario Rank Feature" and "UI Boundaries"
sections of `AGENTS.md` change (username no longer gates all rank
lookups; UNKNOWN rows may carry totals), plus a decision-log entry —
per the shipping checklist.

## Design — the import-warmup PR (optional)

The import-then-browse flow already has a background hook: a successful
import calls `enqueue_playlist_percentile_warmup` (as does unhiding a
playlist), which batch-prepends the playlist's scenarios to the warmup
worker's queue with move-to-front dedup and wakes it. The hook fires on
every import today — but the enqueue keeps only *played* scenarios
(`_ordered_played_scenarios`), which is the right mission for the
overview and nearly empty for a freshly imported playlist the user
hasn't trained yet. So in practice almost nothing enters the queue, and
the first open of the new playlist does all the fetching interactively.

The change is one filter: at the **import** call site only, enqueue the
full scenario list (played first under the existing ordering heuristic,
unplayed after in playlist order). The worker's per-item step needs no
changes — an unplayed scenario resolves its leaderboard ID (from the
seed for bundled scenarios; via exact search otherwise, paced politely
in the background), fetches rank (caching UNRANKED), and warms the
total, which is exactly what the detail grid shows. The unhide call
site stays played-only; the overview's needs have not changed.

Interplay with opening the playlist is already designed for: the worker
waits for interactive quiet between items, so during the import → click
seconds it steps aside and the open's phase-2 fan-out does the
interactive fetching; the worker fills the remainder in idle gaps, and
the two coordinate through the same caches. Worst case is one
duplicated in-flight fetch.

This PR follows the proposal-wide rule stated above: the background
worker runs only with a configured username. On a username-less install
this PR changes nothing — the worker is not running and the enqueue
no-ops, so importing a playlist still fetches nothing in the background,
and totals arrive lazily at the first open exactly as the totals PR
describes.

## Delivery plan

- **Totals PR** — service change (including the error-to-warning message
  change), playlist row formatter change, Home formatter branch, tests.
  Its soft dependency — the seeding PR, without which a username-less
  playlist open would fan out over the exact-search endpoint — shipped
  as PR #169, so nothing blocks this.
- **Import-warmup PR (optional)** — relax the played-only filter at the
  import enqueue call site. Small (the enqueue/worker machinery all
  exists); its soft dependency on the seeding PR (shipped, PR #169) is
  met. Independent of the totals PR.

## Testing

- Totals PR: `get_scenario_rank_info` with no username returns UNKNOWN
  with `total_players` set and a `warning_message` (network mocked);
  playlist formatter renders totals on an UNKNOWN row and still shows
  N/A for Position/Percentile; Home `format_scenario_rank`
  UNKNOWN-with-total variant; regression test for the original report —
  username-less install, seeded mapping, cached total → Total Players
  column populated.
- Import-warmup PR: the import call site enqueues unplayed scenarios
  (played ordered first); the unhide call site stays played-only; no
  username → enqueue is a no-op.
