# Playlists and Benchmarks

The Playlists page is the one place playlists and benchmarks are managed, and
it lists the playlists the user has chosen to see, with local aggregates. A
benchmark is a playlist that also carries rank thresholds, and the bundled
library ships with the app with only the popular ones visible. Clicking a row
opens that playlist's scenario table, which paints local stats immediately and
streams leaderboard positions in behind them. A background worker keeps the
overview's percentile columns warm without getting in the way of anything the
user is doing.

Statements below describe what the app does today and link the
[decision log](../decision_log.md) entries that set them — rationale lives
in those entries, not here. A link follows the sentences its entry governs; a
sentence after the link, or with no link, is an implementation fact that no
decision-log entry governs. Structure is mapped in
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
  key, route value, selector value, import duplicate check, and filename
  suffix. Names are display-only labels, rendered `Name (CODE)` only when two
  loaded playlists share a name
  ([2026-07-07](../decision_log.md#2026-07-07-use-playlist-codes-as-playlist-identity)).
  The show-list is keyed by code too (see the overview). Import writes
  `data/playlists/{sanitized name} [{sanitized code}].json`. Option lists are
  ordered by case-folded name, then name, then code; the overview's row data
  arrives in that order under its own Last Played default sort.
- Scenario names match exactly on their stripped form, enforced at the CSV
  run parse and by the `Scenario.name` validator; a whitespace-only name
  becomes `""` rather than rejecting the playlist
  ([2026-07-11](../decision_log.md#2026-07-11-match-scenario-names-on-their-stripped-form)).
- `playlist_database` is unsynchronized; writes are single-key dict
  operations and iterating readers take a one-call `list()` snapshot first
  ([2026-07-09](../decision_log.md#2026-07-09-accept-unsynchronized-in-memory-stores-single-writer)).

## Routes and navigation

- `/playlists` and `/playlists/{playlistCode}` are stable contracts, and the
  bare-route selector dropdown is gone
  ([2026-07-03](../decision_log.md#2026-07-03-playlists-routes-are-stable-the-bare-route-selector-is-transitional)).
  `playlist_selector.py` is now only a shared prop preset for the Home and
  Aim Training Journey dropdowns.
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
  Percentile, then the show/hide and delete action cells. The numeric and
  timestamp columns use the repo-owned `nullsLastComparator`, referenced by
  bare name
  ([2026-04-29](../decision_log.md#2026-04-29-use-controlled-ag-grid-js-for-null-aware-sorting),
  [2026-06-20](../decision_log.md#2026-06-20-reference-dash-ag-grid-grid-functions-by-bare-name)).
  Rows come from local run data and rank caches only, never the network.
  Last Played is relative with "Never" as sentinel and an absolute timestamp
  on hover, refreshed by a 30-second tick
  ([2026-06-21](../decision_log.md#2026-06-21-relative-humanized-last-played-timestamps)
  as amended by
  [2026-07-11](../decision_log.md#2026-07-11-humanize-the-absolute-timestamp-format)).
  The hover adds a "Stalest: {scenario}, {relative}" second line.
- Percentile aggregates cover played scenarios only. Until every played
  scenario is display-resolved (UNRANKED, or RANKED with a cached percentile)
  both cells read `{resolved}/{played} cached`; a resolved all-UNRANKED
  playlist, or one with no played scenario, reads `N/A`
  ([2026-07-16](../decision_log.md#2026-07-16-warm-playlist-percentiles-with-one-polite-background-worker)).
  The placeholder is dimmed with the tooltip "Shown once all N played
  scenarios have data — open the playlist to fetch now"; a Lowest value
  shows "Lowest: {scenario}" on hover.
- The warmup status line has three renderings: "Updating percentile data: N
  remaining", the same with " (~{duration})" once a pace sample exists
  (smallest form "<1 min"), and "Updating percentile data: N remaining ·
  paused; retrying at H:MM AM/PM" (12-hour local time, never with the ETA)
  in backoff; "Percentile update stopped: {reason}" after a fatal stop. A
  one-second interval rebuilds rows without recording interactive activity,
  disables after one idle rebuild, and re-arms on the worker's enqueue
  generation
  ([2026-07-16](../decision_log.md#2026-07-16-warm-playlist-percentiles-with-one-polite-background-worker)).
- Visibility is a per-code show-list in `data/playlist_visibility.json`,
  uniform for bundled and user playlists. A missing or unusable file yields
  the first-run seed (eleven Voltaic S5 and Viscose codes plus every
  user-root code) without writing; a usable file is authoritative, even
  empty. Hidden playlists still load, route, and draw rank overlays
  ([2026-07-11](../decision_log.md#2026-07-11-the-playlist-overview-is-the-playlist-management-surface)).
  The browser-persisted "Show hidden" switch reveals them muted, and the eye
  cell toggles one code with no confirm step. The file is
  `schema_version`-stamped: an unusable or newer-build file yields the seed
  and shows the yellow alert "Playlist visibility is not being used" with the
  store's message; an unusable file is copied aside by the first write, and a
  newer-build file refuses every write
  ([2026-08-11](../decision_log.md#2026-08-11-durable-json-stores-carry-a-schema_version-stamp)).
  A refused toggle answers with a red "Show and hide are unavailable" toast
  and leaves the rows alone. An ordinary failed toggle write propagates;
  nothing was committed and the next click retries
  ([2026-08-02](../decision_log.md#2026-08-02-a-committed-side-effect-reports-its-outcome-even-when-a-later-write-fails)).
- With rows and no username the status line reads "Percentiles unavailable.
  Set your KovaaK's username in Settings." with Settings linked, as the rank
  spec states
  ([2026-08-11](../decision_log.md#2026-08-11-a-fresh-install-is-asked-once-on-a-card-keyed-to-key-absence)).
  On an empty grid it reads "No playlists are loaded." or 'All playlists are
  hidden. Toggle "Show hidden" to manage them.' instead.
- Both grids feed their quick filter into AG Grid's built-in one client-side.
  Both log AG Grid's `columnSizeOptions` warning on every mount
  ([2026-07-18](../decision_log.md#2026-07-18-accept-dash-ag-grids-columnsizeoptions-console-warning)).

## Import and delete

- Import opens the "Import Playlist" modal (field "Playlist code", help
  "Paste a KovaaK's playlist share code and press Import to add that playlist
  to this list."). Every submit spins the button, refusing clicks, for the
  callback's duration; an empty submit sets the inline error "Enter a
  playlist code." and makes no request.
- KovaaK's `/playlist/playlists?search=<code>` is primary. Zero usable
  records or more than one falls back to Evxl's exact `playlist-by-code`
  before refusing; the stored code is the canonical one the resolving source
  returned, never the pasted input
  ([2026-07-17](../decision_log.md#2026-07-17-playlist-import-falls-back-to-evxl-exact-by-code)).
  The refusals are "Failed to load playlist data for playlist code: {code}"
  and "Found more than one playlist from code: {code}". Two outcomes never
  consult Evxl: a search that raises refuses with "Failed to look up playlist
  code {code}: KovaaK's API error.", and one record with a blank code refuses
  with "Invalid playlist data returned by API for playlist code: {code}".
- A loaded code is refused: "Playlist code already exists: {code} is already
  imported as {name} ({code})."
  ([2026-07-07](../decision_log.md#2026-07-07-use-playlist-codes-as-playlist-identity)),
  plus ' It is currently hidden — toggle "Show hidden" on this page to
  unhide it.' when that playlist is hidden. Refusals are red "Playlist import
  failed" toasts leaving the modal open.
- The stamped file is written to a temp path and replaced into place after a
  destination check: a newer-build file or any healthy playlist at that
  filename refuses the import; only an unusable file is copied aside and
  replaced
  ([2026-08-11](../decision_log.md#2026-08-11-durable-json-stores-carry-a-schema_version-stamp)).
  Success adds the code to the show-list, enqueues warmup, closes and clears
  the modal, rebuilds rows, and toasts green "Playlist imported" / 'Imported
  "{label}" ({code}).'. A failed or refused show-list write changes only the
  toast: orange "Playlist imported — not shown", with a hint to toggle "Show
  hidden" and click the row's eye icon
  ([2026-08-02](../decision_log.md#2026-08-02-a-committed-side-effect-reports-its-outcome-even-when-a-later-write-fails)).
- Delete exists only for user playlists; it unlinks the file recorded for
  the code, drops the store entry, and forgets the show-list membership
  ([2026-07-11](../decision_log.md#2026-07-11-the-playlist-overview-is-the-playlist-management-surface)).
  Bundled rows render no icon and never open the modal. "Delete Playlist"
  asks 'Delete "{label}" ({code})? You can re-import it later by share
  code.' When two user files share the code, every recorded file is unlinked
  (duplicates first, served file last, stopping at the first hard failure).
  Success toasts green "Playlist deleted"; a failed unlink toasts red
  "Playlist delete failed" and leaves the store alone. A failed show-list
  write after the delete is logged; the green toast still shows
  ([2026-08-02](../decision_log.md#2026-08-02-a-committed-side-effect-reports-its-outcome-even-when-a-later-write-fails)).
  Confirm handlers act only on a real click (`n_clicks`), because
  duplicate-output callbacks can fire once on page load.

## The per-playlist scenario table

- Columns: Scenario, Last Played, Runs, Position, Total Players, Percentile,
  PB Score, PB Date, PB cm/360, PB Accuracy. Position reads a formatted
  rank, "Unranked", `N/A`, or, while pending, a blank cell with an animated
  ellipsis. PB columns take `N/A` as null sentinel, PB Date included; Last
  Played keeps "Never"; the 30-second tick refreshes both timestamp columns
  ([2026-08-09](../decision_log.md#2026-08-09-pb-columns-keep-their-na-sentinel-even-for-timestamps)).
  PB cm/360 is known only when the PB run used the cm/360 scale; PB Accuracy
  prefers damage accuracy, falling back to hit accuracy.
- Opening the route has two phases. Phase 1 paints every row from local
  stats and TTL-ignored caches with explicit pending flags per unresolved
  Position, Total Players, and Percentile cell. Phase 2 hydrates leaderboard
  IDs once, then runs the four-worker fan-out in one daemon thread,
  streaming rows into a registry keyed by the per-open generation token; a
  one-second enable-only interval drains them as update transactions, with
  row id `generation_token:playlist_order`. Starting a fill cancels every
  other live fill; terminal fills are tombstones in an eight-item set,
  consumed evicted before unconsumed. The first terminal tick alone drains
  final updates, rebuilds unresolved cancelled rows cache-only, and emits the
  toast; it and every later tick assert the settled status. The toast uses
  the red, yellow, and silent tiers
  ([2026-07-15](../decision_log.md#2026-07-15-stream-playlist-positions-with-generation-scoped-progressive-fill)).
  Hydration is skipped when every scenario is already mapped. Status:
  "Updating positions from KovaaK's… {done}/{total}" live; "Update
  interrupted · {done} of {total} refreshed" cancelled; "{n} of {total}
  positions unavailable" (+ " · {m} from cache — KovaaK's unreachable") or
  "{m} of {total} positions from cache — KovaaK's unreachable" degraded;
  empty when clean. The toast fires once per generation: red "Position
  update incomplete" if any lookup ended UNKNOWN, yellow "Positions served
  from cache" if only stale results occurred, nothing when clean or
  cancelled.
- With no username the fill is skipped, pending flags are cleared, and the
  status reads "Positions unavailable — set your KovaaK's username in
  Settings" with Settings linked
  ([2026-08-09](../decision_log.md#2026-08-09-an-unset-username-is-stated-in-place-never-reported-as-a-failure)).
  A playlist deleted between phase 1 and registration settles as "Update
  interrupted" with no pending cell.
- The scenarios grid owns vertical scrolling inside the AppShell viewport
  with a 300px minimum height
  ([2026-07-06](../decision_log.md#2026-07-06-let-the-playlist-scenarios-grid-own-vertical-scrolling));
  the overview grid uses the same layout, the floor being each grid's inline
  `minHeight` style. Neither declares initial `rowData`, so the loading
  overlay owns the gap
  ([2026-07-16](../decision_log.md#2026-07-16-keep-pre-hydration-states-honest)).

## Bundled corpus, user playlists, and the importer

- `resources/benchmarks/` ships flat, is scanned in full at startup, and is
  machine-generated, never hand-edited
  ([2026-07-11](../decision_log.md#2026-07-11-the-playlist-overview-is-the-playlist-management-surface));
  230 files as of 2026-08-22. User playlists live under `data/playlists/`,
  created on first import. Files load in `(filename.casefold(), filename)`
  order per root, bundled root first; the first file for a code wins, and a
  shadowed one is skipped with a startup warning buffered for the UI
  ([2026-07-07](../decision_log.md#2026-07-07-use-playlist-codes-as-playlist-identity)).
  Those warnings drain only when the Scenario Performance page mounts, as
  persistent yellow toasts titled "Playlist not loaded"; a session that
  starts on `/playlists` sees them after its first visit there.
- - A user file whose code a bundled benchmark serves is recorded and never
  deleted at startup; the overview offers an in-app cleanup instead
  ([2026-07-11](../decision_log.md#2026-07-11-the-playlist-overview-is-the-playlist-management-surface)).
  The yellow alert is titled "Leftover playlist files" and reads "1 leftover
  playlist file in data/playlists is superseded by bundled benchmarks." or
  "{N} leftover playlist files in data/playlists are superseded by bundled
  benchmarks.", with a "Delete leftover files" button. The "Delete Leftover
  Files" modal asks "Delete 1 leftover playlist file from data/playlists? They
  are superseded by bundled benchmarks and hold no data." or "Delete {N}
  leftover playlist files from data/playlists? They are superseded by bundled
  benchmarks and hold no data." with a "Delete" button. Cleanup tolerates
  files already gone, keeps any that fail, and toasts "Leftover files deleted"
  or red "Cleanup failed".
- User files are stamped and read through the store state machine (unusable
  or newer files skipped with an actionable warning); bundled files are
  unstamped by design
  ([2026-08-11](../decision_log.md#2026-08-11-durable-json-stores-carry-a-schema_version-stamp)).
- Every bundled scenario carries a `leaderboard_id`; startup merges the
  corpus's name→ID pairs (excluding names two files disagree on) into the
  permanent mapping cache: a live-learned entry is never overwritten, a
  seed-owned entry is added or refreshed, and a seed-owned entry the corpus
  no longer asserts is removed only when every bundled file loaded. Each
  generated file carries a `generated_from` stamp whose `schema_version`
  marks files written under an older schema as stale, so a plain importer
  run regenerates them through the benchmark payload cache without `--force`
  ([2026-07-20](../decision_log.md#2026-07-20-seed-leaderboard-ids-from-the-bundled-benchmark-corpus)).
  The runtime lookup is the [rank spec](scenario_rank.md)'s. That cache is
  the app's KovaaK's benchmark cache under `data/cache/benchmarks/`; Evxl is
  re-queried on every regeneration. The stamp holds sharecode, benchmark ID,
  ordered rank-color pairs, timestamp, generator, and `schema_version`
  (currently 2); the app ignores it. An empty bundled root also suppresses
  removals.
- `scripts/benchmark_importer/` resolves playlist names and codes and the
  ordered (rank name, color) ladder through Evxl, and thresholds plus each
  scenario's `leaderboard_id` through KovaaK's, pairing the ladder with
  `rank_maxes` positionally; sharecodes Evxl lists twice with different
  payloads are skipped and reported
  ([2026-07-03](../decision_log.md#2026-07-03-import-benchmarks-from-evxl-and-kovaaks)).
  A rank-count mismatch or an empty benchmark is a deterministic failure.
  Deterministic failures land in `generated/failures.json` with the Evxl
  signature they failed against and are skipped until that changes,
  `--force` runs, or `--only` names the code; transient failures feed a
  consecutive-failure breaker (default 3). The manifest skips intact current
  output and unlinks a renamed playlist's previous file. Operator steps are
  in the [importer readme](../../scripts/benchmark_importer/readme.md); the
  script is exempt from the lint and type gates
  ([tech_debt.md](../tech_debt.md)).

## The percentile warmup worker

- - One app-lifetime daemon starts after startup (whether or not local runs
  were ingested), or on the first username save. The queue holds played
  scenarios from visible playlists, each once, grouped to finish recently
  played playlists first; the worker is sequential, sleeps two seconds between
  items, blocks on a condition variable when idle, waits for an interactive
  quiet window, and backs off on outages, waking early on a real network
  success. Unhide and import prepend the playlist's played scenarios and wake
  it; hide and delete cancel nothing. Every dequeue rechecks cache freshness
  and a session outcome map. UNRANKED is cached only after one positive
  username validation per session. `percentile_warmup_enabled = false` or an
  empty username skips the worker
  ([2026-07-16](../decision_log.md#2026-07-16-warm-playlist-percentiles-with-one-polite-background-worker)).
  Within each playlist, scenarios lacking a displayable percentile queue
  first, then most recently played; the prepend uses the same order. The quiet
  window is five seconds; the backoff ladder runs 30 s to 30 min. Connection
  errors, 5xx, and post-retry 429 re-queue and trip the backoff; a read
  timeout and an exhausted third transient attempt are terminal for the
  session and also trip it; other permanent failures are terminal without it.
  The three-attempt budget is per scenario name, with one shared budget for
  username validation. `percentile_warmup_enabled` defaults to true. A restart
  re-enqueues everything and skips fresh items at dequeue.
- An unknown username stops the queue for the session, whether confirmed by
  the API or by a fresh cached marker; the overview's status line and a
  WARNING log carry it, with no toast
  ([2026-07-16](../decision_log.md#2026-07-16-warm-playlist-percentiles-with-one-polite-background-worker)
  as amended by
  [2026-08-03](../decision_log.md#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)).
  An unexpected exception in hydration or an item stops the queue the same
  way.
