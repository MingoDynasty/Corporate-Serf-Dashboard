# Notifications

The dashboard stays quiet during normal play and interrupts only for
something the player did, a run worth celebrating, or a failure they would
act on. A condition that stays true is explained where it happens instead of
popping up again on every trigger. A run earns at most one notification, its
title states the verdict, and the next run replaces it rather than stacking
beside it. One switch in Chart options silences the run notifications while
the chart keeps updating.

Statements below describe what the app does today and link the
[decision log](../decision_log.md) entries that set them — rationale lives
in those entries, not here. A statement with no link is an implementation
fact that no decision-log entry governs. Runtime structure, including the
thread-to-UI channels, is mapped in [architecture.md](../architecture.md);
the user-facing rationale is in [product.md](../product.md). Toasts that
belong to another capability — the Position field's hints, the manual
Refresh outcomes, the Steam ID mismatch, the playlist outcome toasts — are
named here only as instances of the routing policy; their owning spec keeps
their full behavior.

## Delivery

- Every toast is a `sendNotifications` payload for the one
  `dmc.NotificationContainer` in the app shell, id `notification-container`,
  built by `toast()` in `utilities/notifications.py`. Python `logging` is the
  console and file record and never reaches the screen
  ([2026-08-03](../decision_log.md#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)).
- A payload carries `action: "show"`, the id, title, message, color, and
  `autoClose`, plus an optional icon. Ids are stable and semantic: DMC's
  `show` ignores a payload whose id is already on screen, so a repeat of the
  same event dedupes instead of stacking
  ([2026-08-03](../decision_log.md#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)).
- The nominal lifetime is 8000 ms. Two toasts pass `auto_close=False` and
  stay until dismissed: the Steam ID mismatch and the startup playlist
  warnings
  ([2026-08-03](../decision_log.md#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)).
  The helper always sets `autoClose`, so the container's own 4000 ms default
  never applies.
- `upsert_toast(notification, sequence)` lets one id replace whatever it is
  showing: it sends an `update` and a `show` with the same id and payload, so
  whichever matches the toast's current state applies, and it alternates
  `autoClose` between 8000 and 8001 ms by the parity of `sequence`, which
  re-keys Mantine's auto-close timer so the replacement starts a full
  lifetime. `sequence` is the per-client `dcc.Store` `toast-lifetime-sequence`,
  hosted in the app shell beside the container with initial data `0`
  ([2026-08-03](../decision_log.md#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)).
  Only the run-verdict family uses it.
- Toasts are built only inside Dash callbacks. A background thread publishes
  to typed shared state that a Scenario Performance interval callback polls,
  and never writes `sendNotifications` itself
  ([2026-08-03](../decision_log.md#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy);
  the channels are enumerated under
  [background threads never drive UI outputs](../architecture.md#background-threads-never-drive-ui-outputs)).
  So every thread-fed toast — run verdicts, run-import failures, startup
  playlist warnings — appears only while Scenario Performance is mounted, on
  its next poll tick.

## Routing policy

- Whether an event toasts is decided per event, in this order
  ([2026-08-03](../decision_log.md#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)):
  a persistent condition (misconfiguration, missing data, a degraded feature)
  is stated in place at the point of impact, never toasted; an automatic
  failure during passive navigation gets no toast, the field state conveys it
  and a console `logger.warning` is kept; a user-initiated failure (Import,
  manual Refresh, a run file that failed to import) gets an error toast; an
  achievement or coaching verdict gets one toast per run; a diagnostic
  (thread failures, timeouts with an automatic fallback) is console-only.
- Two named exceptions to the persistent-condition rule, both conditions with
  no in-place home, each surfaced once per lifecycle rather than once per
  trigger and persistent until dismissed: the Steam ID mismatch, one toast per
  app session (per server process, not per browser), and the startup
  playlist warnings, one batch per boot
  ([2026-08-03](../decision_log.md#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)).
  The mismatch toast itself is specified in
  [scenario_rank.md](scenario_rank.md#data-sources-and-identity).
- An unset KovaaK's username is persistent configuration state, never a
  failure: the Position field and both playlist pages state it in place, and
  the only toast it earns is the blue answer to a Refresh click
  ([2026-08-09](../decision_log.md#2026-08-09-an-unset-username-is-stated-in-place-never-reported-as-a-failure));
  the instances are specified in
  [scenario_rank.md](scenario_rank.md#failure-handling).
- With a scenario selected, Manual Refresh answers every click with a
  toast — red, yellow, green, or blue; with none selected the click sets the
  field to `N/A` and toasts nothing. The passive rank renders that used to
  toast red or yellow no longer do
  ([2026-07-12](../decision_log.md#2026-07-12-rank-fetch-failure-degrades-to-the-last-cached-rank)
  as amended by
  [2026-08-03](../decision_log.md#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy));
  the four outcomes are specified in
  [scenario_rank.md](scenario_rank.md#failure-handling).
- One named exception to the stable-id rule: a repeatable user-action result
  carries a per-click id so back-to-back clicks each answer — the green
  Refresh confirmation
  ([2026-08-03](../decision_log.md#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy))
  and the blue unset-username notice
  ([2026-08-09](../decision_log.md#2026-08-09-an-unset-username-is-stated-in-place-never-reported-as-a-failure)).
- The title carries the verdict and never reads "Notification"; the message
  leads with the scenario, with sensitivity as a trailing qualifier; a failing
  threshold verdict names the target it missed; a new personal best gets no
  toast of its own beyond the run verdict it already earned
  ([2026-08-03](../decision_log.md#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)).
- A local validation problem is an inline field error, not a toast: an empty
  playlist import code sets "Enter a playlist code." on the field.
- The playlist scenarios page's progressive fill ends with at most one
  aggregate toast per fill — red when positions could not be updated, yellow
  when some were served from cache, nothing when clean
  ([2026-07-15](../decision_log.md#2026-07-15-stream-playlist-positions-with-generation-scoped-progressive-fill));
  the playlists spec owns it.

## Run notifications

- The watchdog thread imports a new run CSV, loads it into the in-memory
  stores, and only then appends a `NewFileMessage` to the process-wide
  `message_queue` deque
  ([2026-07-06](../decision_log.md#2026-07-06-coalesce-pending-home-run-events)).
  Its `nth_score` is the run's 1-based place among the scenario's runs at
  the same sensitivity, ties not counted as higher; its
  `previous_high_score` is the scenario's pre-run high score across all
  sensitivities, and is `None` for a scenario's first run and for the first
  run at a new sensitivity
  ([2026-07-08](../decision_log.md#2026-07-08-judge-score-threshold-notifications-against-the-previous-pb)).
- Scenario Performance's `check_for_new_data` is the deque's sole consumer.
  On each `interval-component` tick (`polling_interval`, default 1000 ms),
  and whenever the "Follow newly played scenario" switch or the selected
  scenario changes, it drains every pending message, lands on the most
  recently played scenario when the follow switch is on and on the selected
  scenario otherwise, discards messages for any other scenario, and publishes
  one `run-events` summary — `count` plus the `latest` run's scenario name,
  sensitivity, `nth_score`, score, and `previous_high_score` — changing the
  dropdown at most once; with no scenario selected and the follow switch
  off, the drained messages are dropped
  ([2026-07-06](../decision_log.md#2026-07-06-coalesce-pending-home-run-events)).
- The interval runs only while the page is mounted, so runs played while
  another page is open wait in the deque and arrive as one digest on the
  next visit. The supported usage model is one active Scenario Performance
  tab; extra tabs are crash-safe but unsynchronized
  ([2026-07-06](../decision_log.md#2026-07-06-coalesce-pending-home-run-events)).
  The interval keeps ticking while the tab is hidden
  ([2026-07-17](../decision_log.md#2026-07-17-absorb-poll-tick-bursts-with-threads-not-visibility-gating)).
- `generate_graph` builds the toast from the summary only when `run-events`
  triggered it, so a control change never re-toasts a stale payload
  ([2026-07-06](../decision_log.md#2026-07-06-coalesce-pending-home-run-events)).
  A summary whose latest run belongs to another scenario earns nothing, and
  a render that resolves to an empty-state plot skips the toast.
- A run is judged only when Score Threshold Verdict is on, the threshold
  percentage is a usable non-zero number, and `previous_high_score` is
  positive. It passes when `score >= previous_high_score × goal / 100`; the
  message shows `score / previous_high_score × 100` and the goal, each to one
  decimal
  ([2026-07-08](../decision_log.md#2026-07-08-judge-score-threshold-notifications-against-the-previous-pb)).
  A run is placed when `nth_score` is at most the Top N value; first place is
  phrased "best" and the rest "Nth-best".
- A single run (`count` 1): the threshold verdict headlines and the placement
  trails it; a run that is neither judged nor placed emits nothing
  ([2026-08-03](../decision_log.md#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)).
  Pass: green, "Threshold passed",
  `{scenario} — {score:.2f}, {pct:.1f}% of PB. Also your {best|Nth-best} at {sensitivity}.`
  when placed, else `... Ready to move on.` Fail: yellow, "Below threshold",
  `{scenario} — {score:.2f}, {pct:.1f}% of PB — need {goal:.1f}%. Still your {best|Nth-best} at {sensitivity}. Keep grinding...`,
  the "Still" sentence only when placed. Unjudged and placed: green,
  "New best score" or "New {Nth}-best score",
  `{scenario} — {score:.2f} at {sensitivity}.`
- A backlog (`count` above 1): one digest titled "While you were away",
  judged on the batch's latest run only and ignoring placement, so a digest
  always fires. Unjudged: blue,
  `{count} new {scenario} runs. Latest: {score:.2f} at {sensitivity}.` Pass:
  green, `{count} new {scenario} runs. Latest: {score:.2f} — {pct:.1f}% of PB, passed threshold.`
  Fail: yellow,
  `{count} new {scenario} runs. Latest: {score:.2f} — {pct:.1f}% of PB, below the {goal:.1f}% threshold.`
  ([2026-07-06](../decision_log.md#2026-07-06-coalesce-pending-home-run-events),
  [2026-07-08](../decision_log.md#2026-07-08-judge-score-threshold-notifications-against-the-previous-pb)).
- One run, one toast: every shape above shares the id `run-verdict`, at most
  one is visible at a time, a later verdict — the digest included — replaces
  it with a full lifetime, and this holds per browser client and survives
  page navigation
  ([2026-08-03](../decision_log.md#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)).
  Each emission goes through `upsert_toast` and advances the shell's
  sequence store by one.
- The Run Notifications master switch (`run-notification-switch`, on by
  default; help text "Controls the threshold, placement, and catch-up
  notifications for your runs. Turn this off to update the chart silently.")
  gates all three shapes through one early return at the top of the producing
  function. It does not gate the run-import failure toast, the plot update,
  scenario auto-switching, or the rank, Steam ID, and playlist toast families.
  It is read as `State`, so flipping it never rebuilds the plot
  ([2026-08-21](../decision_log.md#2026-08-21-run-notifications-have-a-master-switch-and-the-threshold-switch-is-renamed)).
- The Score Threshold Verdict switch (`score-threshold-notification-switch`,
  on by default; help text "Adds a pass or fail verdict to run notifications
  when the run can be judged against the score threshold. Needs Run
  Notifications turned on.") decides only whether a run is judged and is an
  `Input` to the graph callback. Master off is silence whatever it says;
  master on with it off gives placement toasts and neutral digests only
  ([2026-08-21](../decision_log.md#2026-08-21-run-notifications-have-a-master-switch-and-the-threshold-switch-is-renamed)).
  Where the switches sit and how their values persist is the Chart options
  panel's concern, not specified here.

## Background threads and diagnostics

- When the watchdog cannot import a run file — a CSV that will not parse, a
  handler exception, or a store load that fails after a successful parse — it
  appends "Could not process a new run file. See debug.log for details." to
  `run_import_failure_queue`, and the observer thread survives. On each
  `interval-component` tick `flush_run_import_failures` drains the queue into
  one red toast, id `run-import-failure`, title "Run not recorded": the
  message above for one failure, or
  `{n} new run files could not be processed. See debug.log for details.` for
  a batch; a drained batch never toasts again
  ([2026-08-03](../decision_log.md#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)).
- Playlist files the startup scan could not load are recorded in
  `playlist_startup_warning_queue`; `flush_startup_playlist_warnings` drains
  it 250 ms after a Scenario Performance mount (a one-shot interval), one
  yellow persistent toast per warning, ids `startup-playlist-warning-{n}`,
  title "Playlist not loaded"
  ([2026-07-07](../decision_log.md#2026-07-07-use-playlist-codes-as-playlist-identity)
  for the buffering,
  [2026-08-03](../decision_log.md#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)
  for the persistence).
- Background rank diagnostics are console-only: the score-aware refresh
  chain's exhaustion, its unknown-user stop, its unexpected-error net, and a
  failed refresh scheduling in the watchdog each log and never toast, and the
  displayed position keeps its last confirmed value
  ([2026-08-03](../decision_log.md#2026-08-03-background-rank-diagnostics-are-console-only),
  superseding the "asks the user to click Refresh" clause of
  [2026-07-01](../decision_log.md#2026-07-01-keep-scenario-rank-consistent-with-score-aware-refreshes)).
  The playlist percentile warmup worker reports through the overview page's
  status strip and the log, never a toast.
- Whether a background rank event ("rank updated after that PB", a timed-out
  position update) deserves a toast is deliberately open; any such toast
  needs its own typed channel
  ([2026-08-03](../decision_log.md#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)).

## Committed side effects

- A screen never keeps showing a success claim after the write it describes
  failed, and an action whose irreversible work already happened still
  reports it even when a later step fails
  ([2026-08-02](../decision_log.md#2026-08-02-a-committed-side-effect-reports-its-outcome-even-when-a-later-write-fails)).
  The instances are on the playlists overview: an import whose visibility
  write fails reports the split outcome in orange, "Playlist imported — not
  shown", with every other output matching the success path; a delete whose
  visibility write fails still confirms in green, "Playlist deleted"; a
  visibility toggle propagates the failure, since nothing was committed and
  no claim was printed. The playlists spec carries those toasts in full.

## Inventory

Every toast id in the app, with its color and owner. Lifetime is 8000 ms
unless noted.

| Id | Title | Color | Produced by |
| --- | --- | --- | --- |
| `run-verdict` | per verdict, or "While you were away" | green / yellow / blue | `generate_graph`; this spec |
| `run-import-failure` | "Run not recorded" | red | `flush_run_import_failures`; this spec |
| `startup-playlist-warning-{n}` | "Playlist not loaded" | yellow, until dismissed | `flush_startup_playlist_warnings`; this spec |
| `steam-id-mismatch` | "Steam ID mismatch" | yellow, until dismissed, once per process | `get_scenario_rank`; rank spec |
| `rank-refresh-failed` | "Position refresh failed" | red | `refresh_rank`; rank spec |
| `rank-refresh-stale` | "Position refresh failed" | yellow | `refresh_rank`; rank spec |
| `rank-refresh-notification-{uuid}` | "Position refreshed" | green | `refresh_rank`; rank spec |
| `rank-refresh-username-unset-{uuid}` | "KovaaK's username not set" | blue | `refresh_rank`; rank spec |
| `setup-card-skip-refused-notification` | "Skip was not saved" | red | `skip_identity_setup`; settings spec |
| `imported-playlist-successful-notification` | "Playlist imported" | green | `import_playlist`; playlists spec |
| `imported-playlist-visibility-failed-notification` | "Playlist imported — not shown" | orange | `import_playlist`; playlists spec |
| `imported-playlist-failed-notification` | "Playlist import failed" | red | `import_playlist`; playlists spec |
| `deleted-playlist-successful-notification` | "Playlist deleted" | green | `confirm_delete_playlist`; playlists spec |
| `deleted-playlist-failed-notification` | "Playlist delete failed" | red | `confirm_delete_playlist`; playlists spec |
| `superseded-cleanup-successful-notification` | "Leftover files deleted" | green | `confirm_delete_superseded`; playlists spec |
| `superseded-cleanup-failed-notification` | "Cleanup failed" | red | `confirm_delete_superseded`; playlists spec |
| `visibility-refused-notification` | "Show and hide are unavailable" | red | `update_playlist_visibility`; playlists spec ([2026-08-11](../decision_log.md#2026-08-11-durable-json-stores-carry-a-schema_version-stamp)) |
| `playlist-progressive-fill-{generation}` | "Position update incomplete" / "Positions served from cache" | red / yellow | `drain_playlist_scenario_rows`; playlists spec |
