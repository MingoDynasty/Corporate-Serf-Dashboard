# Notifications

The dashboard stays quiet during normal play and interrupts only for
something the player did, a run worth celebrating, or a failure they would
act on. A condition that stays true is explained where it happens instead of
popping up again on every trigger. A run earns at most one notification, its
title states the verdict, and the next run replaces it rather than stacking
beside it. A run that beats your personal best is the exception the app makes
for itself: it gets its own toast, on whatever page you are looking at, and
that one stays until you dismiss it. One switch in Chart options silences the
ordinary run notifications while the chart keeps updating.

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
- The nominal lifetime is 8000 ms. Three toast families pass
  `auto_close=False` and stay until dismissed: the Steam ID mismatch, the
  startup playlist warnings, and the personal best celebration
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
- `upsert_sticky_toast(notification)` is the same `update`-plus-`show` pairing
  without the alternation, stamping `autoClose` false on both payloads. A
  toast that stays until dismissed has no timer to re-arm, and routing one
  through `upsert_toast` would stamp a lifetime over `autoClose` and quietly
  make it an ordinary 8 s toast. Only the celebration family uses it.
- Toasts are built only inside Dash callbacks. A background thread publishes
  to typed shared state that an interval callback polls, and never writes
  `sendNotifications` itself
  ([2026-08-03](../decision_log.md#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy);
  the channels are enumerated under
  [background threads never drive UI outputs](../architecture.md#background-threads-never-drive-ui-outputs)).
  The run-event channel is drained in the app shell, so it reaches the screen
  on every page. The two channels Scenario Performance drains — run-import
  failures and startup playlist warnings — reach the screen only while that
  page is mounted: the failures on its next poll tick, the warnings on a
  one-shot interval after mount. The playlist fill's channel is drained by
  the playlist scenarios page and carries grid rows, never notifications; the
  playlists spec owns it.

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
  field to `N/A` and toasts nothing. The red and yellow answers carry stable
  ids, so a repeat of the same failure while its toast is still up is
  deduped and shows nothing new; only the green and blue answers are
  per-click. The passive rank renders that used to toast red or yellow no
  longer do
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
- The title carries the verdict and never reads "Notification"; a run
  verdict's message leads with the scenario, with sensitivity as a trailing
  qualifier; a failing threshold verdict names the target it missed
  ([2026-08-03](../decision_log.md#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)).
  A new personal best is the one achievement with a toast of its own, in its
  own family, amending that entry's rule that it earns nothing beyond the run
  verdict.
- A local validation problem is an inline field error, not a toast: an empty
  playlist import code sets "Enter a playlist code." on the field.
- The playlist scenarios page's progressive fill reports degradation in the
  page's own status line and toasts nothing, whatever the outcome: positions
  that could not be updated, positions served from cache, a cancelled fill,
  and a clean one all settle in place. It is an automatic failure during
  passive navigation with an in-place home, so the routing order above sends
  it there
  ([2026-08-22](../decision_log.md#2026-08-22-the-playlist-fill-reports-degradation-in-place-only),
  superseding the aggregate-toast clause of
  [2026-07-15](../decision_log.md#2026-07-15-stream-playlist-positions-with-generation-scoped-progressive-fill)).
  The playlists spec owns the status line.

## Run notifications

- The watchdog thread imports a new run CSV, loads it into the in-memory
  stores, and only then appends a `NewFileMessage` to the process-wide
  `message_queue` deque
  ([2026-07-06](../decision_log.md#2026-07-06-coalesce-pending-home-run-events)).
  The message carries facts and no decision, so each consumer derives its own
  verdict: `nth_score` is the run's 1-based place among the scenario's runs at
  the same sensitivity, ties not counted as higher; `scenario_previous_best`
  is the scenario's pre-run high score across all sensitivities, and is `None`
  only for a scenario's very first run
  ([2026-07-08](../decision_log.md#2026-07-08-judge-score-threshold-notifications-against-the-previous-pb));
  `is_new_sensitivity` is true for a scenario's first run and for the first
  run at a new sensitivity; `run_id` is the run CSV's file name.
- The app shell's `publish_run_events` is the deque's sole consumer. On each
  `pb-celebration-interval` tick (`polling_interval`, default 1000 ms) it
  drains every pending message and publishes one `run-events-batch` payload:
  the drained runs in order, each stamped `is_live`, plus the batch's
  `celebrated_run_id` (or none) and a monotonic `animation_sequence`. An empty
  queue publishes nothing. The drain runs on every page, so a run no longer
  waits for a Scenario Performance visit to be delivered.
- A run is stamped live when its `datetime_created` is within 120 seconds of
  the drain, and stale otherwise. There is no watermark and no drain
  bookkeeping: every drain empties the queue, so a message a drain finds was
  never seen by an earlier one, and a message appended while a drain is
  popping is caught by that drain or the next, exactly once either way. The
  cap bounds replay rather than removing it — a queue that accumulated with no
  tab open announces nothing older than the cap on the next visit, and
  anything within it is announced.
- `celebrated_run_id` names the newest live run whose score is strictly
  greater than its `scenario_previous_best`, and nothing when no run
  qualifies: a tie never celebrates, and a scenario's first run only sets the
  baseline. At most one run per batch is named, so an older qualifying run in
  the same batch is not celebrated. `animation_sequence` advances by one
  exactly when a run is named. The celebration is currently unconditional; the
  setting that turns it off ships with the animation.
- The celebration toast is green with a trophy icon, titled "New personal
  best", and stays until dismissed. Its id is `pb-celebration`, deliberately
  not `run-verdict`, so an ordinary run toast lands beside it rather than
  replacing it. It goes out through `upsert_sticky_toast`, and the shell
  writes nothing to `toast-lifetime-sequence`. With a positive previous best
  the message is
  `{scenario}: {score:.2f}. Up {pct:.1f}% on your previous best of {previous:.2f}.`;
  with a zero or negative one, which has no percentage to give, it is
  `{scenario}: {score:.2f}. Your previous best was {previous:.2f}.`
- Scenario Performance's `check_for_new_data` consumes `run-events-batch` as
  its only `Input`, with the follow switch and the scenario dropdown as
  `State`. It lands on the most recently played scenario when the follow
  switch is on and on the selected scenario otherwise, ignores runs for any
  other scenario, and publishes one `run-events` summary — the latest matching
  run's stamped record plus the batch's `celebrated_run_id` — changing the
  dropdown at most once; with no scenario selected and the follow switch off
  it forwards nothing
  ([2026-07-06](../decision_log.md#2026-07-06-coalesce-pending-home-run-events)).
  A control flip alone forwards nothing, because the controls are `State` and
  a Store replays its last value, and a remount does not replay a retained
  batch (`prevent_initial_call`).
- The supported usage model is one active tab: `message_queue` is
  process-wide and each drain's payload reaches one client, so with two tabs
  open a batch lands in whichever drain runs first. Extra tabs are crash-safe
  but unsynchronized
  ([2026-07-06](../decision_log.md#2026-07-06-coalesce-pending-home-run-events)).
  The interval keeps ticking while the tab is hidden
  ([2026-07-17](../decision_log.md#2026-07-17-absorb-poll-tick-bursts-with-threads-not-visibility-gating)).
- `generate_graph` builds the toast from the summary only when `run-events`
  triggered it, so a control change never re-toasts a stale payload
  ([2026-07-06](../decision_log.md#2026-07-06-coalesce-pending-home-run-events)).
  A summary whose latest run belongs to another scenario earns nothing, and
  a render that resolves to an empty-state plot skips the toast.
- A run is judged only when Score Threshold Verdict is on, the threshold
  percentage is a usable non-zero number, the run is not the first at its
  sensitivity, and `scenario_previous_best` is positive. It passes when
  `score >= scenario_previous_best × goal / 100`; the message shows
  `score / scenario_previous_best × 100` and the goal, each to one decimal
  ([2026-07-08](../decision_log.md#2026-07-08-judge-score-threshold-notifications-against-the-previous-pb)).
  A run is placed when `nth_score` is at most the Top N value; first place is
  phrased "best" and the rest "Nth-best".
- The page narrates only the batch's latest matching run, and only when the
  batch's decision does not name it and it is stamped live: a named run yields,
  because the celebration toast is its one notification, and a stale run
  narrates nothing. Otherwise the threshold verdict headlines and the placement
  trails it; a run that is neither judged nor placed emits nothing
  ([2026-08-03](../decision_log.md#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)).
  Pass: green, "Threshold passed",
  `{scenario} — {score:.2f}, {pct:.1f}% of PB. Also your {best|Nth-best} at {sensitivity}.`
  when placed, else `... Ready to move on.` Fail: yellow, "Below threshold",
  `{scenario} — {score:.2f}, {pct:.1f}% of PB — need {goal:.1f}%. Still your {best|Nth-best} at {sensitivity}. Keep grinding...`,
  the "Still" sentence only when placed. Unjudged and placed: green,
  "New best score" or "New {Nth}-best score",
  `{scenario} — {score:.2f} at {sensitivity}.`
- Every other run in a batch earns nothing; its new point on the plot is its
  record. There is no catch-up digest: a batch of several runs rebuilds the
  graph once, auto-switches once, and toasts exactly as a single run would
  ([2026-07-06](../decision_log.md#2026-07-06-coalesce-pending-home-run-events)).
- The one-notification guarantee is per run, not per batch, and one-sided:
  every run earns at most one notification and the celebrated run earns
  exactly one. So one batch can put two toasts on screen — the celebration and
  the page's narration — when they concern different runs, and a personal best
  the drain did not celebrate has no guaranteed toast at all.
- One run, one toast: every run-verdict shape shares the id `run-verdict`, at
  most one is visible at a time, a later verdict replaces it with a full
  lifetime, and this holds per browser client and survives page navigation
  ([2026-08-03](../decision_log.md#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)).
  Each emission goes through `upsert_toast` and advances the shell's
  sequence store by one. The celebration toast is the deliberate exception to
  replaces-rather-than-stacks: its own id and no lifetime, so it sits beside a
  run verdict and outlives it.
- The Run Notifications master switch (`run-notification-switch`, on by
  default; help text "Controls threshold verdict and placement notifications
  for your runs.") gates the page-built shapes through one early return at the
  top of the producing function, ahead of the celebration yield, so master off
  is silent whether or not the run was celebrated. It does not gate the
  celebration toast, which the shell produces and which no setting governs
  yet, nor the run-import failure toast, the plot update, scenario
  auto-switching, or the rank, Steam ID, and playlist toast families. It is
  read as `State`, so flipping it never rebuilds the plot
  ([2026-08-21](../decision_log.md#2026-08-21-run-notifications-have-a-master-switch-and-the-threshold-switch-is-renamed)).
- The Score Threshold Verdict switch (`score-threshold-notification-switch`,
  on by default; help text "Adds a pass or fail verdict to run notifications
  when the run can be judged against the score threshold. Needs Run
  Notifications turned on.") decides only whether a run is judged and is an
  `Input` to the graph callback. Master off is silence whatever it says;
  master on with it off gives placement toasts only
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
- The warnings the startup playlist scan records — a file it could not
  load, the loser of a duplicate-code pair, a missing bundled directory — go
  to `playlist_startup_warning_queue`; `flush_startup_playlist_warnings` drains
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
| `run-verdict` | per verdict | green / yellow | `generate_graph`; this spec |
| `pb-celebration` | "New personal best" | green, until dismissed | `publish_run_events`; this spec |
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
