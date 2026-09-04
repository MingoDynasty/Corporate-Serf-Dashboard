# Notifications

The dashboard stays quiet during normal play and interrupts only for
something the player did, a run worth celebrating, or a failure they would
act on. A condition that stays true is explained where it happens instead of
popping up again on every trigger. A message answering something you did
replaces its own previous copy and pops back onto the screen, so a retry
always gets a visible answer, while messages about different things stack
side by side. Toasts and the notices printed into the page share one severity
color scale, so a color means the same thing wherever it appears.

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

## The severity scale

- One color scale governs every notification surface, toast and inline notice
  alike. Blue is informational and any action it offers is optional; yellow is
  caution, an attention-worthy negative outcome or a state that needs the user
  without anything having failed; red is an error, an operation that failed;
  green is a positive outcome; orange is partial success, where the action
  committed but a follow-up write did not
  ([2026-08-30](../decision_log.md#2026-08-30-one-severity-color-language-for-inline-notices)).
  Green and orange are toast-only: no inline surface uses either.
- Every inline notice carries a leading icon,
  `material-symbols:warning-outline` on yellow and
  `material-symbols:info-outline` on blue
  ([2026-08-30](../decision_log.md#2026-08-30-one-severity-color-language-for-inline-notices)).
- Which component a notice uses follows its content model. A text-only notice
  may be a `dmc.Alert`, whose root Mantine renders with `role="alert"`: an
  assertive, atomic live region, so assistive technology reads the element's
  entire contents as one message, keyboard focus never moves to it, and the
  announcement offers no direct interaction. A notice that holds interactive
  controls is a `dmc.Paper` wearing the alert anatomy through the shared
  `.alert-panel` classes in `assets/stylesheet.css`, per
  [MDN's `role=alert` guidance](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Roles/alert_role)
  that the role is for text content rather than interactive elements like
  links or buttons, and for content that appears dynamically rather than with
  the page
  ([2026-08-30](../decision_log.md#2026-08-30-one-severity-color-language-for-inline-notices)).
- The five inline notices, each owned by the spec named beside it: the
  Settings store alert (settings spec) and the Playlists visibility alert
  (playlists spec) are yellow `dmc.Alert`s; the Aim Training Journey
  work-in-progress banner is a blue `dmc.Alert`, recorded only here because
  that page is work in progress and has no capability spec; the Playlists
  leftover-files notice (playlists spec) is a blue `dmc.Paper`; the Home setup
  card (settings and scenario-performance specs) is a `dmc.Paper` that is blue
  in its identity state and yellow in its stats-folder and unusable-store
  states
  ([2026-08-30](../decision_log.md#2026-08-30-one-severity-color-language-for-inline-notices)).

## Delivery

- Every toast is a `sendNotifications` payload for the one
  `dmc.NotificationContainer` in the app shell, id `notification-container`,
  built by `toast()` in `utilities/notifications.py`. Python `logging` is the
  console and file record and never reaches the screen
  ([2026-08-03](../decision_log.md#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)).
- A payload carries `action: "show"`, the id, title, message, color, and
  `autoClose`, plus an optional icon. Ids are semantic. DMC's `show` ignores a
  payload whose id is already on screen
  ([2026-08-03](../decision_log.md#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)), which is why every
  toast that can recur is emitted through `channel_toast` under a rotating
  instance id rather than a fixed one
  ([2026-08-31](../decision_log.md#2026-08-31-repeatable-toasts-replace-in-place-with-a-visible-re-entry)).
- The nominal lifetime is 8000 ms. Three toast families pass
  `auto_close=False` and stay until dismissed: the Steam ID mismatch, the
  startup playlist warnings, and the personal best celebration
  ([2026-08-03](../decision_log.md#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)).
  The helper always sets `autoClose`, so the container's own 4000 ms default
  never applies.
- `channel_toast(notification, registry, clears=())` is how every
  replace-in-place toast goes out. The payload's `id` carries the channel's
  logical key; the helper stamps a fresh instance id over it (the key plus a
  per-emission `uuid4` hex suffix), returns the `sendNotifications` list, the
  `hideNotifications` list, and a `dash.Patch` for the registry, and the
  emitting callback wires all three as outputs. The hide list holds the
  channel's previous instance id plus the current instance of every channel
  named in `clears`. It carries the payload's `autoClose` through untouched,
  which is what lets one mechanism serve every channel: an ordinary channel
  keeps the nominal 8 s lifetime, and the personal best celebration passes
  `auto_close=False` at its builder and stays until dismissed while a later
  celebration still replaces it. It is the only helper — there is no separate
  sticky pairing
  ([2026-08-31](../decision_log.md#2026-08-31-repeatable-toasts-replace-in-place-with-a-visible-re-entry)).
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

## Toast identity

Routing decides whether an event toasts at all. This section decides what id it
toasts under, and it applies to every toast the app adds from here on
([2026-08-31](../decision_log.md#2026-08-31-repeatable-toasts-replace-in-place-with-a-visible-re-entry)).

- The classifying test is **recurrence**: can the reported fact recur inside one
  toast lifetime, judged against the complete supported workflow including
  inverse actions that make the same subject eligible again? A fact that cannot
  recur is an **event toast** -- unique id per emission, plain `show`,
  occurrences stack, no registry wiring. A fact that can recur is a **channel**.
  The event bucket is empty today: every current toast's fact can recur through
  some supported cycle, so the rule exists to classify future toasts, and a
  claim that a fact cannot recur has to survive the inverse-action check
  (delete-then-re-import defeats the naive claim for import success).
- A **channel** is replaced in place by hide-and-reshow, so each recurrence
  visibly re-enters with a structurally fresh lifetime. Its identity follows the
  semantic lane. An operation's **problem lane** is one channel: mutually
  exclusive outcome flavors (a red hard failure, a yellow served-stale) share
  one key with a differing payload, so two contradictory claims about the same
  latest attempt can never be on screen together. **Success lanes** and
  **standing-condition lanes** are their own channels, keyed by subject when
  independent subjects can be in flight at once (per scenario, per playlist
  code). The mutual-exclusion clause is problem-lane-only: success flavors of
  one operation may keep distinct channels, accepting the narrow cross-flavor
  window a re-attempt can open.
- Lanes interact only through explicit **cross-clears**. A success emission
  hides its operation's problem channel, and any standing-condition channel it
  falsifies, by naming them in `clears`. Widening one channel to span all
  outcomes of an operation instead would make two consecutive distinct
  successes replace each other.
- A **burst toast** is many same-type events where the aggregate is the message.
  It folds into one summary carrying a count and points at where the individual
  events are recorded. `run-import-failure` is the one instance.
- Persistence (`auto_close=False`, process- or session-gated) is orthogonal to
  all three and stacks with any of them. The personal best celebration is a
  persistent channel: it replaces its own previous instance and never expires
  on its own
  ([2026-08-31](../decision_log.md#2026-08-31-repeatable-toasts-replace-in-place-with-a-visible-re-entry)).
- **The registry.** `toast-channel-registry` is the per-client `dcc.Store`
  mapping each logical channel key to the instance id currently on screen for
  it, hosted in the app shell beside the container with initial data `{}`. It
  is read as `State` and written as an `allow_duplicate` `Output` by every
  emitting callback. It sits in the shell, not a page layout, because a toast
  outlives the page that emitted it and a page-scoped store would reset on
  navigation, leaving a visible toast with no id to replace it by. It grows one
  small entry per channel seen in a session.
- **Registry writes are per-key `dash.Patch` assignments, never whole-dict
  replacements.** A response that rewrote the whole dict would carry a stale
  value for every channel it did not emit, so two responses landing out of order
  could resurrect an obsolete instance id, leaving two toasts of one channel on
  screen or a problem toast beside the success that cleared it. A cross-cleared
  channel's entry is assigned `None` in the same patch. Same-operation
  concurrency needs no loading guard: every channel has exactly one producing
  callback, and Dash 4.4.1 discards an older in-flight invocation's response for
  the same output set.
- **What the user sees.** The container applies `hideNotifications` after
  `sendNotifications`, so the fresh instance enters with the full animation
  while the one it replaces animates out: a ~250 ms crossfade that reads as
  replacement, not as two toasts. The replacement's lifetime is its own full
  8000 ms. Hiding an id that is not on screen is a clean no-op. Two accepted
  cosmetics: a toast that arrived as a replacement auto-closes without its own
  exit fade, and bystander toasts bounce upward for roughly 280 ms during a
  replacement.
- **One accepted exception.** `run-import-failure` is a fixed id with no
  channel wiring, so a second drained batch inside one 8 s lifetime is
  swallowed. It is a background burst channel where anti-flood wins and its copy
  already points at `debug.log`; the inventory below conforms to this section in
  full apart from this row
  ([2026-08-31](../decision_log.md#2026-08-31-repeatable-toasts-replace-in-place-with-a-visible-re-entry)).

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
  the only toast it earns is the blue answer to a Refresh click, on its own
  standing-condition channel
  ([2026-08-09](../decision_log.md#2026-08-09-an-unset-username-is-stated-in-place-never-reported-as-a-failure)
  as amended by
  [2026-08-31](../decision_log.md#2026-08-31-repeatable-toasts-replace-in-place-with-a-visible-re-entry));
  the instances are specified in
  [scenario_rank.md](scenario_rank.md#failure-handling).
- With a scenario selected, Manual Refresh answers every click with a
  toast — red, yellow, green, or blue; with none selected the click sets the
  field to `N/A` and toasts nothing. Every answer is a channel emission, so a
  repeat click always re-pops its answer: the red and yellow outcomes share one
  problem channel, the green confirmation is keyed by scenario, and the blue
  notice is its own standing-condition channel. The passive rank renders that
  used to toast red or yellow no longer do
  ([2026-07-12](../decision_log.md#2026-07-12-rank-fetch-failure-degrades-to-the-last-cached-rank)
  as amended by
  [2026-08-03](../decision_log.md#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)
  and
  [2026-08-31](../decision_log.md#2026-08-31-repeatable-toasts-replace-in-place-with-a-visible-re-entry));
  the four outcomes are specified in
  [scenario_rank.md](scenario_rank.md#failure-handling).
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
- A run is stamped live when its `datetime_created` is within the freshness
  window of the drain, and stale otherwise. The window is a 120-second cap
  plus one poll period, so it is 121 seconds at the default 1000 ms interval:
  a run can be a whole period old through nothing but the drain's cadence, and
  a window shorter than the configured period would stamp every run stale and
  silence the toasts liveness gates. There is no watermark and no drain
  bookkeeping: every drain empties the queue, so a message a drain finds was
  never seen by an earlier one, and a message appended while a drain is
  popping is caught by that drain or the next, exactly once either way. The
  window bounds replay rather than removing it — a queue that accumulated with
  no tab open announces nothing older than the window on the next visit, and
  anything within it is announced.
- `celebrated_run_id` names the newest live run whose score is strictly
  greater than its `scenario_previous_best`, and nothing when no run
  qualifies: a tie never celebrates, and a scenario's first run only sets the
  baseline. At most one run per batch is named, so an older qualifying run in
  the same batch is not celebrated. `animation_sequence` advances by one
  exactly when a run is named.
- The drain reads the celebration setting as `State`
  ([settings.md](settings.md#celebrations)). With it off it names no run, so
  nothing is stamped, the sequence stands still, and no celebration toast goes
  out; the batch still publishes every run with its liveness stamp, and the
  page narrates it under the ordinary rules below. Only the exact value `off`
  silences the family: any other stored value, including one a later build
  wrote and a store the browser has lost, still celebrates
  ([2026-09-02](../decision_log.md#2026-09-02-the-celebration-setting-is-browser-local-on-the-settings-page)).
- The celebration toast is green with a trophy icon, titled "New personal
  best", and stays until dismissed. Its channel key is `pb-celebration`,
  deliberately not `run-verdict`, so an ordinary run toast lands beside it
  rather than replacing it; only a later celebration replaces a celebration,
  showing a fresh instance and hiding the one before it. It goes out through
  `channel_toast` like every other replaceable toast, with `auto_close=False`
  passed at the builder, and the shell writes exactly the one
  `toast-channel-registry` key
  ([2026-08-31](../decision_log.md#2026-08-31-repeatable-toasts-replace-in-place-with-a-visible-re-entry)).
  With a positive previous best
  the message is
  `{scenario}: {score:.2f}. Up {pct:.1f}% on your previous best of {previous:.2f}.`;
  with a zero or negative one, which has no percentage to give, it is
  `{scenario}: {score:.2f}. Your previous best was {previous:.2f}.`
- The animation lives in `assets/pbCelebration.js` and is driven by a
  clientside callback on `run-events-batch`, with the style store as `State`,
  so no server round trip separates the decision from the burst. It holds a
  name-keyed registry of four styles, all played through the vendored
  `assets/vendor/canvas-confetti.js` (1.9.4, ISC) and all bounded to about
  three seconds: `confetti` is the upstream Realistic Look recipe unchanged;
  `fireworks` is the upstream Fireworks recipe cut to 3 s; `cannons` is School
  Pride cut to 2.5 s in Mantine's primary blue (`#228be6`) and white; `stars`
  is the upstream Stars recipe unchanged. An unknown style name plays
  `confetti`, so a style retired later never silently turns celebrations off
  ([2026-09-02](../decision_log.md#2026-09-02-a-new-personal-best-celebrates-on-every-page)).
- Every style returns a cancel closure, or nothing when it schedules nothing,
  and the module holds exactly one such handle and invokes it before any new
  play. That is what stops a looping style: `confetti.reset()` clears the
  particles already drawn but does not cancel an interval or an animation
  frame
  ([2026-09-02](../decision_log.md#2026-09-02-the-celebration-setting-is-browser-local-on-the-settings-page)).
- It plays nothing when the setting is off and nothing when the browser
  prefers reduced motion; the toast still shows in that case, because it is
  informational and under reduced motion it is the whole celebration. A burst
  still in flight is cancelled before a new one starts. `animation_sequence`
  is what makes a repeat play at all: the same sequence never replays, and a
  payload naming no run plays nothing
  ([2026-09-02](../decision_log.md#2026-09-02-a-new-personal-best-celebrates-on-every-page)).
- While the tab is hidden — a fully occluded window counts as hidden under
  Chromium's occlusion tracking — the burst is not dropped. At most one
  celebration is held, a newer one replacing it, and it plays on the next
  `visibilitychange` to visible; the toast is already on screen and stays
  until dismissed. The Settings page's Preview never reaches that path,
  because clicking it needs a visible tab
  ([2026-09-02](../decision_log.md#2026-09-02-a-new-personal-best-celebrates-on-every-page)).
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
- One run, one toast: every run-verdict shape shares the channel key
  `run-verdict`, at most one is on screen once a response has been applied, a
  later verdict replaces it with a full lifetime, and this holds per browser
  client and survives page navigation
  ([2026-08-03](../decision_log.md#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)).
  Each emission goes through `channel_toast`, so the newest verdict enters
  under a fresh instance id while the one it replaces is hidden in the same
  response; during that ~250 ms crossfade the outgoing instance is still
  animating out
  ([2026-08-31](../decision_log.md#2026-08-31-repeatable-toasts-replace-in-place-with-a-visible-re-entry)).
  The celebration toast is the deliberate exception to
  replaces-*this* lane: its own channel key and no lifetime, so it sits beside
  a run verdict and outlives it. It is not an exception to the mechanism —
  it replaces its own previous instance the same way
  ([2026-08-31](../decision_log.md#2026-08-31-repeatable-toasts-replace-in-place-with-a-visible-re-entry)).
- The Run Notifications master switch (`run-notification-switch`, on by
  default; help text "Controls threshold verdict and placement notifications
  for your runs. Personal best celebrations use their own setting.") gates the
  page-built shapes through one early return at the top of the producing
  function, ahead of the celebration yield, so master off is silent whether or
  not the run was celebrated. It does not gate the celebration, which the
  shell produces and which the Celebrations setting governs alone
  ([settings.md](settings.md#celebrations)); the two are independent families,
  so master off with celebrations on still celebrates a personal best on every
  page while ordinary runs stay silent
  ([2026-09-02](../decision_log.md#2026-09-02-a-new-personal-best-celebrates-on-every-page)).
  It does not gate the run-import failure toast, the plot update, scenario
  auto-switching, or the rank, Steam ID, and playlist toast families either. It is
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
  It is the one burst toast, and the one accepted exception to the identity
  policy: the id is fixed and unwired, so a second drained batch inside one
  lifetime is swallowed
  ([2026-08-31](../decision_log.md#2026-08-31-repeatable-toasts-replace-in-place-with-a-visible-re-entry)).
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

Every toast in the app, with its pattern, color, and owner. Lifetime is
8000 ms unless noted. A **channel** row names the logical key; what the
container actually renders is that key plus a per-emission suffix, and the row's
`clears` column names the channels its emission also hides.

| Key | Pattern | Title | Color | Clears | Produced by |
| --- | --- | --- | --- | --- | --- |
| `run-verdict` | channel | per verdict | green / yellow | — | `generate_graph`; this spec |
| `pb-celebration` | channel, persistent | "New personal best" | green, until dismissed | — | `publish_run_events`; this spec |
| `run-import-failure` | burst, fixed id | "Run not recorded" | red | — | `flush_run_import_failures`; this spec |
| `startup-playlist-warning-{n}` | fixed id per warning, sticky | "Playlist not loaded" | yellow, until dismissed | — | `flush_startup_playlist_warnings`; this spec |
| `steam-id-mismatch` | fixed id, sticky, once per process | "Steam ID mismatch" | yellow, until dismissed | — | `get_scenario_rank`; rank spec |
| `rank-refresh-problem` | channel | "Position refresh failed" | red (hard) / yellow (served stale) | — | `refresh_rank`; rank spec |
| `rank-refresh-success-{scenario}` | channel per scenario | "Position refreshed" | green | `rank-refresh-problem`, `rank-refresh-username-unset` | `refresh_rank`; rank spec |
| `rank-refresh-username-unset` | channel | "KovaaK's username not set" | blue | — | `refresh_rank`; rank spec |
| `setup-card-skip-problem` | channel | "Skip was not saved" | red | — | `skip_identity_setup`; settings spec |
| `imported-playlist-successful-{code}` | channel per playlist code | "Playlist imported" | green | `imported-playlist-failed-notification` | `import_playlist`; playlists spec |
| `imported-playlist-visibility-failed-{code}` | channel per playlist code | "Playlist imported — not shown" | orange | `imported-playlist-failed-notification` | `import_playlist`; playlists spec |
| `imported-playlist-failed-notification` | channel | "Playlist import failed" | red | — | `import_playlist`; playlists spec |
| `deleted-playlist-successful-{code}` | channel per playlist code | "Playlist deleted" | green | `deleted-playlist-failed-notification` | `confirm_delete_playlist`; playlists spec |
| `deleted-playlist-failed-notification` | channel | "Playlist delete failed" | red | — | `confirm_delete_playlist`; playlists spec |
| `superseded-cleanup-successful-notification` | channel | "Leftover files deleted" | green | `superseded-cleanup-failed-notification` | `confirm_delete_superseded`; playlists spec |
| `superseded-cleanup-failed-notification` | channel | "Cleanup failed" | red | — | `confirm_delete_superseded`; playlists spec |
| `visibility-refused-notification` | channel | "Show and hide are unavailable" | red | — | `update_playlist_visibility`; playlists spec ([2026-08-11](../decision_log.md#2026-08-11-durable-json-stores-carry-a-schema_version-stamp)) |

The channel rows were converted in one pass
([2026-08-31](../decision_log.md#2026-08-31-repeatable-toasts-replace-in-place-with-a-visible-re-entry)).
