# Playlists and Benchmarks

The Playlists page is the one place playlists and benchmarks are managed, and
it lists every loaded one with local aggregates. A benchmark is a playlist that also carries rank thresholds, and
the bundled library ships with the app with only the popular ones visible.
Clicking a row opens that playlist's scenario table, which paints local stats
immediately and streams leaderboard positions in behind them. A background
worker keeps the overview's percentile columns warm without getting in the way
of anything the user is doing.

Statements below describe what the app does today and link the
[decision log](../decision_log.md) entries that set them — rationale lives
in those entries, not here. A statement with no link is an implementation
fact that no decision-log entry governs. Structure is mapped in
[architecture.md](../architecture.md), endpoint quirks in
[kovaaks_api_notes.md](../kovaaks_api_notes.md), the user-facing picture in
the README's [Playlists and Benchmarks](../../README.md#playlists-and-benchmarks)
section and [product.md](../product.md). Leaderboard placement is worded
"Position"
([2026-07-06](../decision_log.md#2026-07-06-one-word-per-concept-in-leaderboard-verbiage)).

## Vocabulary and identity

- A *playlist* is a bare scenario list; a *benchmark* is a playlist plus rank
  thresholds and colors
  ([2026-07-03](../decision_log.md#2026-07-03-import-benchmarks-from-evxl-and-kovaaks)).
  The overview's Type column reads "Benchmark" when any scenario carries
  ranks, otherwise "Playlist".
- The share code is the playlist's identity everywhere: `playlist_database`
  key, route value, import duplicate check, show-list member, and filename
  suffix (`data/playlists/{sanitized name} [{code}].json`). Names are
  display-only labels, rendered `Name (CODE)` only when two loaded playlists
  share a name; option lists and the overview sort by case-folded name, then
  name, then code
  ([2026-07-07](../decision_log.md#2026-07-07-use-playlist-codes-as-playlist-identity)).
  The store is unsynchronized and single-writer; iterating readers take a
  one-call `list()` snapshot first
  ([2026-07-09](../decision_log.md#2026-07-09-accept-unsynchronized-in-memory-stores-single-writer)).
- Scenario names match exactly on their stripped form, enforced at the CSV
  run parse and by the `Scenario.name` validator; a whitespace-only name
  becomes `""` rather than rejecting the playlist
  ([2026-07-11](../decision_log.md#2026-07-11-match-scenario-names-on-their-stripped-form)).

## Routes and navigation

- `/playlists` and `/playlists/{playlistCode}` are stable contracts. The
  bare-route selector is gone; `playlist_selector.py` is now only a shared
  prop preset for the Home and Aim Training Journey dropdowns
  ([2026-07-03](../decision_log.md#2026-07-03-playlists-routes-are-stable-the-bare-route-selector-is-transitional)).
- Overview rows are full-row click targets (pointer cursor, hover tint): a
  click on any cell except the two action cells navigates to
  `/playlists/{code}`. The Playlist name cell and the table's Scenario cell
  (prebuilt `/?playlist_code=<code>&scenario=<name>`, the Scenario
  Performance page) are real anchors: a modified click (Ctrl/Cmd/Shift/Alt)
  keeps the native anchor and stops the grid's `cellClicked` navigation; a
  plain click does the opposite.
- The table load is driven by the mounted layout's `playlist-scenarios-code`
  store, never by the URL change
  ([2026-04-29](../decision_log.md#2026-04-29-drive-playlist-table-loads-from-mounted-route-state)).
  An unknown code renders "Playlist code is not imported: {code}"; no code
  renders "Select a playlist from the Playlists page."

## The overview

- Columns: Playlist, Type, Played (`played/total`, sorted by ratio), Runs,
  Last Played (default sort, descending), Median Percentile, Lowest
  Percentile, then the show/hide and delete action cells. Sortable columns
  use the repo-owned `nullsLastComparator`, referenced by bare name
  ([2026-04-29](../decision_log.md#2026-04-29-use-controlled-ag-grid-js-for-null-aware-sorting),
  [2026-06-20](../decision_log.md#2026-06-20-reference-dash-ag-grid-grid-functions-by-bare-name)).
  Rows come from local run data and rank caches only, never the network.
  Last Played is relative with "Never" as sentinel, an absolute timestamp on
  hover plus a "Stalest: {scenario}, {relative}" line, on a 30-second tick
  ([2026-06-21](../decision_log.md#2026-06-21-relative-humanized-last-played-timestamps)
  as amended by
  [2026-07-11](../decision_log.md#2026-07-11-humanize-the-absolute-timestamp-format)).
- Percentile aggregates cover played scenarios only. Until every played
  scenario is display-resolved (UNRANKED, or RANKED with a cached percentile)
  both cells read `{resolved}/{played} cached`, dimmed, tooltip "Shown once
  all N played scenarios have data — open the playlist to fetch now"; a
  resolved all-UNRANKED playlist reads `N/A`. Lowest shows "Lowest:
  {scenario}" on hover. The warmup status line reads "Updating percentile
  data: N remaining" while work exists, with " (~ETA)" appended once a pace
  sample exists, "… · paused; retrying at H:MM AM" in backoff, and "Percentile update stopped: {reason}" after a
  fatal stop; a one-second interval rebuilds rows without recording
  interactive activity, disables after one idle rebuild, and re-arms on the
  worker's enqueue generation
  ([2026-07-16](../decision_log.md#2026-07-16-warm-playlist-percentiles-with-one-polite-background-worker)).
- Visibility is a per-code show-list in `data/playlist_visibility.json`,
  uniform for bundled and user playlists. A missing or unusable file yields
  the first-run seed (eleven Voltaic S5 and Viscose codes plus every
  user-root code) without writing; a usable file is authoritative, even
  empty. Hidden playlists still load, route, and draw rank overlays; the
  browser-persisted "Show hidden" switch reveals them muted, and the eye
  cell toggles one code with no confirm step
  ([2026-07-11](../decision_log.md#2026-07-11-the-playlist-overview-is-the-playlist-management-surface)).
  The file is `schema_version`-stamped: an unusable file shows the yellow
  alert "Playlist visibility is not being used" with the store's message and
  is copied aside by the first toggle; a newer-build file refuses every
  write, the toggle answering with a red "Show and hide are unavailable"
  toast and leaving the rows alone
  ([2026-08-11](../decision_log.md#2026-08-11-durable-json-stores-carry-a-schema_version-stamp)).
  An ordinary failed toggle write propagates; nothing was committed and the
  next click retries
  ([2026-08-02](../decision_log.md#2026-08-02-a-committed-side-effect-reports-its-outcome-even-when-a-later-write-fails)).
- The status line reads "No playlists are loaded." or 'All playlists are
  hidden. Toggle "Show hidden" to manage them.' on an empty grid; with rows
  and no username, "Percentiles unavailable. Set your KovaaK's username in
  Settings." with Settings linked, as the rank spec states
  ([2026-08-11](../decision_log.md#2026-08-11-a-fresh-install-is-asked-once-on-a-card-keyed-to-key-absence)).
- Both grids feed their quick filter into AG Grid's built-in one client-side,
  and both log AG Grid's `columnSizeOptions` warning on every mount
  ([2026-07-18](../decision_log.md#2026-07-18-accept-dash-ag-grids-columnsizeoptions-console-warning)).

## Import and delete

- Import opens the "Import Playlist" modal (field "Playlist code", help
  "Paste a KovaaK's playlist share code and press Import to add that playlist
  to this list."); an empty submit sets the inline error "Enter a playlist
  code." and the button spins, refusing clicks, for the fetch.
- KovaaK's `/playlist/playlists?search=<code>` is primary. Zero usable
  records or more than one falls back to Evxl's exact `playlist-by-code`
  before refusing with "Failed to load playlist data for playlist code:
  {code}" or "Found more than one playlist from code: {code}"; a search that
  raises refuses with "Failed to look up playlist code {code}: KovaaK's API
  error." and does not fall back. The stored code is the canonical one the
  resolving source returned, never the pasted input
  ([2026-07-17](../decision_log.md#2026-07-17-playlist-import-falls-back-to-evxl-exact-by-code)).
  A loaded code is refused: "Playlist code already exists: {code} is already
  imported as {name} ({code})." plus ' It is currently hidden — toggle "Show
  hidden" on this page to unhide it.' when that playlist is hidden
  ([2026-07-07](../decision_log.md#2026-07-07-use-playlist-codes-as-playlist-identity)).
  Refusals are red "Playlist import failed" toasts leaving the modal open.
- The file is written atomically and stamped after a destination check: a
  newer-build file or a different healthy playlist at that filename refuses
  the import; only an unusable file is copied aside and replaced
  ([2026-08-11](../decision_log.md#2026-08-11-durable-json-stores-carry-a-schema_version-stamp)).
  Success adds the code to the show-list, enqueues warmup, closes and clears
  the modal, rebuilds rows, and toasts green "Playlist imported" / 'Imported
  "{label}" ({code}).'. A failed show-list write changes only the toast:
  orange "Playlist imported — not shown", with a hint to toggle "Show
  hidden" and click the row's eye icon
  ([2026-08-02](../decision_log.md#2026-08-02-a-committed-side-effect-reports-its-outcome-even-when-a-later-write-fails)).
- Delete exists only for user playlists; bundled rows render no icon and
  never open the modal. "Delete Playlist" asks 'Delete "{label}" ({code})?
  You can re-import it later by share code.' Confirming unlinks every user
  file recorded for the code (duplicates first, served file last, stopping
  at the first hard failure), drops the store entry and user-root tracking,
  forgets the show-list membership, and toasts green "Playlist deleted"; a
  failed unlink toasts red "Playlist delete failed" and leaves the store
  alone
  ([2026-07-11](../decision_log.md#2026-07-11-the-playlist-overview-is-the-playlist-management-surface)).
  A failed show-list write after the delete is logged; the green toast still
  shows
  ([2026-08-02](../decision_log.md#2026-08-02-a-committed-side-effect-reports-its-outcome-even-when-a-later-write-fails)).
  Confirm handlers act only on a real click (`n_clicks`), because
  duplicate-output callbacks can fire once on page load.

## The per-playlist scenario table

- Columns: Scenario, Last Played, Runs, Position, Total Players, Percentile,
  PB Score, PB Date, PB cm/360, PB Accuracy. Position reads a formatted
  rank, "Unranked", or `N/A`. PB columns take `N/A` as null sentinel, PB Date
  included; Last Played keeps "Never"; the 30-second tick refreshes both
  timestamp columns
  ([2026-08-09](../decision_log.md#2026-08-09-pb-columns-keep-their-na-sentinel-even-for-timestamps)).
  PB cm/360 is known only when the PB run used the cm/360 scale; PB Accuracy
  prefers damage accuracy, falling back to hit accuracy.
- Opening the route has two phases. Phase 1 paints every row from local stats
  and TTL-ignored caches with explicit pending flags per unresolved Position,
  Total Players, and Percentile cell. Phase 2 hydrates leaderboard IDs once
  (only if some scenario is unmapped), then runs the four-worker fan-out in
  one daemon thread, streaming rows keyed `generation_token:playlist_order`
  into a registry that a one-second enable-only interval drains as update
  transactions. Starting a fill cancels every other live fill; terminal fills
  are tombstones in an eight-item set, consumed evicted before unconsumed. The
  first terminal tick alone drains final updates, rebuilds cancelled rows
  cache-only, settles the status, and emits the toast. Status: "Updating
  positions from KovaaK's… {done}/{total}" live; "Update interrupted · {done}
  of {total} refreshed" cancelled; "{n} of {total} positions unavailable" (+ "
  · {m} from cache — KovaaK's unreachable") or "{m} of {total} positions from
  cache — KovaaK's unreachable" degraded; empty when clean. The toast fires
  once per generation: red "Position update incomplete" if any lookup ended
  UNKNOWN, yellow "Positions served from cache" if only stale results
  occurred, nothing when clean or cancelled
  ([2026-07-15](../decision_log.md#2026-07-15-stream-playlist-positions-with-generation-scoped-progressive-fill)).
- With no username the fill is skipped, pending flags are cleared, and the
  status reads "Positions unavailable — set your KovaaK's username in
  Settings" with Settings linked
  ([2026-08-09](../decision_log.md#2026-08-09-an-unset-username-is-stated-in-place-never-reported-as-a-failure)).
  A playlist deleted between phase 1 and registration settles as "Update
  interrupted" with no pending cell.
- Both grids own vertical scrolling inside the AppShell viewport with a
  300px minimum height
  ([2026-07-06](../decision_log.md#2026-07-06-let-the-playlist-scenarios-grid-own-vertical-scrolling))
  and declare no initial `rowData`, so the loading overlay owns the gap
  ([2026-07-16](../decision_log.md#2026-07-16-keep-pre-hydration-states-honest)).

## Bundled corpus, user playlists, and the importer

- `resources/benchmarks/` ships flat, is scanned in full at startup, and is
  machine-generated, never hand-edited; 230 files as of 2026-08-22. User
  playlists live under `data/playlists/`, created on first import. Files
  load in filename order per root, bundled root first; the first file for a
  code wins and a shadowed one is skipped with a startup warning, delivered
  as a notification once the UI mounts
  ([2026-07-07](../decision_log.md#2026-07-07-use-playlist-codes-as-playlist-identity),
  root per
  [2026-07-11](../decision_log.md#2026-07-11-the-playlist-overview-is-the-playlist-management-surface)).
  A user file whose code a bundled benchmark serves is recorded, never
  deleted at startup; the overview shows the yellow alert "Leftover playlist
  files" / "{N} leftover playlist file(s) in data/playlists is/are superseded
  by bundled benchmarks." with a "Delete leftover files" button and a
  "Delete Leftover Files" confirm. Cleanup tolerates files already gone,
  keeps any that fail, and toasts "Leftover files deleted" or red "Cleanup
  failed". User files are stamped and read through the store state machine
  (unusable or newer files skipped with an actionable warning); bundled
  files are unstamped by design
  ([2026-08-11](../decision_log.md#2026-08-11-durable-json-stores-carry-a-schema_version-stamp)).
- Every bundled scenario carries a `leaderboard_id`; startup merges the
  corpus's name→ID pairs (excluding names two files disagree on) into the
  permanent mapping cache, suppressing removals when any bundled file failed
  to load. The runtime lookup is the [rank spec](scenario_rank.md)'s. Each
  generated file carries a `generated_from` stamp (sharecode, benchmark ID,
  ordered rank-color pairs, timestamp, generator, `schema_version` 2) that
  the app ignores; a file under an older marker regenerates through the
  importer's payload cache without `--force`
  ([2026-07-20](../decision_log.md#2026-07-20-seed-leaderboard-ids-from-the-bundled-benchmark-corpus)).
- `scripts/benchmark_importer/` resolves names and codes through Evxl and
  thresholds through KovaaK's, pairing Evxl's ordered rank colors with
  `rank_maxes` positionally; a count mismatch or an empty benchmark is a
  deterministic failure, and sharecodes Evxl lists twice with different
  payloads are skipped and reported
  ([2026-07-03](../decision_log.md#2026-07-03-import-benchmarks-from-evxl-and-kovaaks)).
  Deterministic failures land in `generated/failures.json` with the Evxl
  signature they failed against and are skipped until that changes,
  `--force` runs, or `--only` names the code; transient failures feed a
  consecutive-failure breaker (default 3). The manifest skips intact current
  output and unlinks a renamed playlist's previous file. Operator steps are
  in the [importer readme](../../scripts/benchmark_importer/readme.md); the
  script is exempt from the lint and type gates
  ([tech_debt.md](../tech_debt.md)).

## The percentile warmup worker

- One app-lifetime daemon starts after startup ingests local runs, or on the
  first username save; `percentile_warmup_enabled = false` (default true) or
  an empty username skips it. The queue holds played scenarios from visible
  playlists, each once, most recently played playlist first. It is
  sequential, waits for a five-second interactive quiet window, sleeps two
  seconds between items, and blocks on a condition variable when idle.
  Unhide and import prepend the playlist's played scenarios and wake it;
  hide and delete cancel nothing. Every dequeue rechecks cache freshness and
  a session outcome map. Connection errors, 5xx, and post-retry 429 re-queue
  under escalating backoff that ends early on a real network success; read
  timeouts and permanent failures are terminal for the session, three
  transient attempts per name. UNRANKED is cached only after one positive
  username validation per session. Worker state is process-local; a restart
  rebuilds the queue from cache freshness
  ([2026-07-16](../decision_log.md#2026-07-16-warm-playlist-percentiles-with-one-polite-background-worker)).
- An API-confirmed unknown username stops the queue for the session, shown
  by the overview's status line and the log only, no toast
  ([2026-07-16](../decision_log.md#2026-07-16-warm-playlist-percentiles-with-one-polite-background-worker)
  as amended by
  [2026-08-03](../decision_log.md#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)).
