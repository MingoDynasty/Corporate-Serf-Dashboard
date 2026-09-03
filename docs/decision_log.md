# Decision Log

Durable project decisions that future contributors and agents should preserve unless a newer entry supersedes them.

Use this log for decisions that are hard to reverse, cross-cutting, based on external API behavior, or likely to be questioned later. Do not record every small implementation choice.

When a decision changes, keep the old entry and mark it `Superseded`. Add a new entry explaining what changed, why, and any migration notes.

## Status Values

- `Proposed`: under consideration, not yet agreed.
- `Accepted`: current agreed decision.
- `Superseded`: replaced by a newer decision.
- `Rejected`: considered and intentionally not chosen.

## 2026-09-02: Warmup Locks Are Never Held Across Cache I/O

Status: Accepted

The Playlists page could show a loading spinner for up to a minute after
startup, and importing or unhiding a playlist could appear to do nothing for
just as long. A background worker was holding a lock while it read hundreds of
small cache files, and the page needed that same lock to draw its progress
line. The worker now does its file reads with the lock released. It warms the
same scenarios as before, and a playlist you have just imported or unhidden can
now take its turn sooner instead of waiting for the scan to end.

**The invariant.** Neither `PercentileWarmupWorker._condition` nor the
module-global `_worker_lock` may be held across cache file I/O. Both are read
by UI callbacks: `get_percentile_warmup_state` (the Playlists status line and
refresh interval) takes `_worker_lock` and then `_condition`, and
`enqueue_playlist_percentile_warmup` (import, unhide) takes both as well. A
hold that spans per-scenario cache reads therefore blocks page renders, not
just the worker.

**Two sites violated it.** `_next_item` held `_condition` across its whole
skip-drain, which reads two cache files per candidate. This only bites when the
cache is warm: nothing returns early, so the loop walks the entire queue.
Measured at 0.13s for 317 scenarios on a fast SSD and about 60s on a
beta tester's disk, where per-file antivirus scanning makes small random reads
roughly 400x slower. A direct callback measurement, taken on the fast SSD with
per-candidate latency injected into `_freshly_satisfied` to model the tester's
disk, recorded 45.1s blocked versus 0.2s once the drain finished. That isolates
the lock and only the lock: the overview's own row build reads two cache files
per played scenario per row on the same disk, so the figure is not evidence
that the tester's page renders promptly after this change. `start_percentile_warmup_worker` held
`_worker_lock` across `_startup_queue()`, which reads two cache files per played
scenario; harmless from `app.py` because it runs before the server accepts
requests, but reachable from the settings save that first supplies a username.

**Shape of the fix.** `_next_item` pops under the lock and evaluates freshness
outside it; the popped name is claimed as `_in_flight` before the lock drops, so
a candidate under evaluation still counts toward `remaining_count` and the batch
cannot read as idle or announce completion mid-drain. The loop re-tests the
queue under the lock before waiting, so an enqueue that notifies while the
worker is evaluating is not lost. `start_percentile_warmup_worker` runs a
claim/park/publish handshake: it claims the start under the lock by setting
`_worker_starting`, releases the lock to enumerate, and publishes in a later
hold. There is no post-enumeration singleton re-check and nothing to discard,
because a second caller arriving during the window returns early instead of
enumerating a queue that would be thrown away. What can arrive in that window
is not a competing starter but an enqueue, which is what the parking below
exists for — the two halves are one protocol and must not be implemented
separately.

**Publication is not a gap.** Releasing the lock across enumeration means an
import or unhide can find no worker to enqueue against, where it previously
just waited for one; dropping it there would defer that playlist's warmup until
the next restart, silently. A `_worker_starting` flag marks the window, codes
arriving in it are parked in `_pending_enqueues`, and the starter adopts them in
the same lock hold that publishes the worker. They are enqueued after
publication, so they prepend ahead of the startup queue.

**Starting is a busy state, not an idle one.** The snapshot carries a
`starting` flag that is true from the moment a start claims the singleton until
its parked enqueues have drained, and the overview reads it as busy. Without
it, a poll landing before publication sees no queue, no in-flight item, and
generation 0, concludes the worker is idle, and disarms its refresh interval —
so nothing then observes the generation bumps that publication and the parked
drain produce, and the page sits on stale percentiles until the next visit. The
flag deliberately outlives publication for the same reason: clearing it at
publication would leave the same window between a freshly published empty
worker and its drain.

**Not fixed here.** `_CACHE_IO_LOCK` serializes every cache file operation
app-wide, but each hold is one file operation rather than a scan; recorded in
`docs/tech_debt.md` under Performance.

## 2026-09-02: A New Personal Best Celebrates On Every Page

Status: Accepted

A run that beats a scenario's personal best now gets a short burst of confetti
and a toast that says so. It fires on whatever page is open and for every
scenario, not only the one being watched, and the toast stays until it is
dismissed because the run that earned it was played in a fullscreen game. A
Settings switch turns the whole thing off. Nothing else about how runs are
reported changed.

**One drain decides.** The app shell hosts the `pb-celebration-interval`
(period `polling_interval`), the `run-events-batch` store, and
`publish_run_events`, which is now `message_queue`'s only consumer. Facts
travel and only the drain decides: it stamps each drained run `is_live`, names
at most one `celebrated_run_id`, and advances a monotonic
`animation_sequence` exactly when it names one. `NewFileMessage` carries
`run_id`, `scenario_previous_best`, and `is_new_sensitivity` — facts with no
verdict in them — and Scenario Performance reads the stamps instead of
re-deriving either. The ordering argument is the dependency graph, not a
protocol: a page callback triggered by the batch store necessarily runs after
the shell wrote it, so there is nothing to race. Four review rounds of
coordination machinery between two independent drains (a shared toast id, a
page-side freshness window, a celebrated-run registry, a registry plus a
watermark with deferral) are what this replaced; each moved the race without
closing it, and the single drain closes it by construction.

**The rule.** A run is celebrated when its score is *strictly* greater than
its `scenario_previous_best`, so a tie never celebrates and a scenario's first
run only sets the baseline. The newest qualifying live run in a batch wins and
an older one is plot-only, because one Dash response carries one payload and
drives one animation. That strict comparison is the only gate that ships: most
runs in a freshly imported scenario are personal bests, and the ruling
accepted that noise rather than inventing a minimum run count or margin before
anyone knows it grates, with the setting as the escape hatch. A gate can be
added later if it does.

**Freshness.** A run is stamped live when its `datetime_created` is within a
120-second cap plus one poll period of the drain, and stale otherwise. There
is no watermark and no drain bookkeeping: every drain empties the queue, so a
message a drain finds was never seen by an earlier one, and one appended
mid-drain is caught by that drain or the next, exactly once either way. The
cap sits two orders of magnitude above the default poll interval and
comfortably above Chromium's intensive throttling, which slows a hidden tab's
interval to about one tick per minute — and the tab is occluded during play,
so a tight window would drop exactly the mid-session personal bests this
exists for. The poll period is added because `polling_interval` carries no
product cap: a run can be a whole period old through nothing but the drain's
cadence, and a fixed cap below the configured period would stamp every run
stale and silently retire every toast liveness gates. The consequence, stated
rather than hidden: a deliberately slow poll widens no-tab replay by exactly
the period it chose. Validating the interval with a product cap instead stays
rejected, for the reasons in
[2026-09-01](#2026-09-01-configured-ports-and-poll-intervals-are-bounded-at-load).

**The toast.** Green, a trophy icon, titled "New personal best", and sent with
`auto_close=False` so it is still there on alt-tab. Its channel key is
`pb-celebration`, deliberately not `run-verdict`: an ordinary run toast lands
beside it rather than replacing it, and only a later celebration replaces a
celebration. It is a persistent channel in the sense the
[2026-08-31 toast-identity entry](#2026-08-31-repeatable-toasts-replace-in-place-with-a-visible-re-entry)
defines, and that entry owns the mechanism.

**The celebration takes the headline.** When celebrations are on, the
celebrated run's one toast *is* the celebration toast and the page's run toast
yields. The score threshold goal has no upper bound, so a goal above 100% let
a personal best read "Below threshold" while confetti fell, and even under a
goal it passes, "Threshold passed" says the less interesting thing. This
amends the priority rule in
[2026-08-03](#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)
for the celebrations-on state only: with the setting off, the verdict
headlines and a personal best has no toast of its own, exactly as before. A
personal best the drain did not celebrate — an older qualifying run coalesced
out of the batch, or one outside the selected scenario with auto-switch off —
follows the ordinary run-toast rules and has no guaranteed toast. The
guarantee is per run and one-sided: every run earns at most one notification,
and the celebrated run exactly one. One batch can therefore put two toasts on
screen when the celebration and the page's narration concern different runs,
and that is correct.

**The master switch does not reach it.** The two settings are independent
families: the celebration setting governs the confetti and the celebration
toast together, and Run Notifications governs the verdict and placement
toasts. With Run Notifications off and celebrations on, a personal best still
celebrates on every page while ordinary runs stay silent — a user in that
state has asked for two things at once. The toast travels with the animation
because it is the half that carries information; on a page other than Scenario
Performance, confetti without it is a burst with no explanation, and under
reduced motion the toast is the whole celebration. Coupling them was rejected
on that reading and on mechanics: the master switch's persisted value lives on
the Scenario Performance page, so the shell would need a second mirror store
to see it.

**A hidden tab holds the animation.** Chromium marks a fully occluded window's
tab hidden, and the player is in KovaaK's fullscreen when a personal best
lands, so a hard `document.hidden` drop would mean the animation never plays
for a real personal best on a single-monitor setup — only from Preview. At
most one celebration is held instead, a newer one replacing it, and it plays
on the next `visibilitychange` to visible; playing while hidden would also
dump a stalled burst on the next alt-tab, since a hidden tab throttles
animation frames. The accepted cost, stated with the ruling: personal best
toasts are dismissed by hand on every setup, including one where the animation
played in view. Relaxing the toast to the normal lifetime is a one-line
follow-up that does not touch the pending mechanism. The ruling needed no
pre-ship evidence, and the asymmetry was the deciding argument: where the tab
never reports hidden the pending path is dormant and behaviour is identical,
and where occlusion does mark it hidden, pending is the only version that
plays at all. The `visibilitychange` observation during a real fullscreen
session remains a post-ship check.

**The animation.** `canvas-confetti` 1.9.4 (ISC) is vendored unminified under
`assets/vendor/`, with its LICENSE and a version pin, rather than hand-rolled:
it ships the physics, the shapes, the reduced-motion guard, cancellation, and
worker-thread rendering, and every later change is configuration instead of
physics code. `assets/pbCelebration.js` is the app-owned half — a name-keyed
style registry, Confetti alone in version one (the upstream Realistic Look
recipe unchanged, about three seconds), behind `play(style)` and
`celebrate(batch, style)`. An unknown style name plays Confetti rather than
nothing, so a style removed later never silently turns celebrations off. A
clientside callback on the batch store drives it, so the burst costs no server
round trip; the library is resolved at call time, because Dash serves
`assets/*.js` in its own order. There is no JavaScript lint, test, or build
step in this repo, so that file is held by review and a manual pass.

**No catch-up digest.** The "While you were away" digest existed because run
events accumulated while Scenario Performance was closed. Delivery is now
app-wide and continuous while any tab is open, so batches stop accumulating in
the case the digest served. What remains is the no-tab case, where the
freshness window draws the line: a personal best set within the window of the
next drain is celebrated on it, and anything older is never replayed. Bounded
replay is accepted rather than suppressed — a player who reopens the tab a
minute after the run wants the celebration, and the timestamp cannot tell that
case from a throttled hidden tab's, which must land. A backlog that does
arrive rebuilds the graph once, auto-switches once, and follows the per-run
rules above: up to two toasts, never a digest. Whether the celebration family
deserves its own longer or unbounded window is a follow-up question, carried
on the roadmap.

**What this supersedes.** The
[2026-07-06 coalescing entry](#2026-07-06-coalesce-pending-home-run-events)
loses its "sole consumer" clause — the shell's drain is the consumer now and
the page listens to a store — and its digest. Its coalescing rule survives,
applied to the batch: the page still considers only the latest matching run.
The [2026-08-21 master-switch entry](#2026-08-21-run-notifications-have-a-master-switch-and-the-threshold-switch-is-renamed)
loses the digest from the set of shapes its gate covers, and its deferral of
the queue-to-UI redesign for the drain alone; the product question that
deferral protected, app-wide verdict toasts, stays deferred, and run toasts
remain page-built and page-scoped. The
[2026-08-03 notification-layer entry](#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)
loses its rule that a personal best earns nothing beyond the run verdict, and
the "backlog digest included" clause of its replacement rule.

Shipped in PRs #261 and #268; proposal and rulings in #248, toast mechanism
reconciled in #263. Distilled from the personal best celebration proposal, now
deleted.

## 2026-09-02: The Celebration Setting Is Browser-Local, On The Settings Page

Status: Accepted

The switch that turns the personal best celebration on and off lives on the
Settings page, in its own Celebrations section, with a Preview button beside
it. It takes effect the moment it is flipped rather than waiting for Save, and
the browser remembers it instead of the app's settings file. A different
browser, or one whose site data has been cleared, celebrates by default.

**The store is the setting.** `dcc.Store(id="pb-celebration-style",
storage_type="local")` in the app shell holds one string: `"off"` or a style
name, defaulting to `"confetti"`. The value is a style name from the start
even though version one ships a switch, so the follow-up that turns the switch
into a style select only adds values to a contract that already exists and
keeps whatever was saved. The control initializes from the store and writes
back to it and carries no Dash persistence of its own, so a switch's boolean
and a select's string never become two competing persisted values. The drain
reads the store as `State`, and so does the clientside animation: changing the
setting must not replay a batch already delivered.

**Why the Settings page.** The behavior is app-wide, so the Chart options
inspector on one page is the wrong home — undiscoverable, and a control there
describes itself as a chart option. This departs from the placement rule the
[point customization](#2026-08-20-run-points-get-a-size-preset-and-a-color-and-the-chart-stops-there)
and [master switch](#2026-08-21-run-notifications-have-a-master-switch-and-the-threshold-switch-is-renamed)
entries both state, that the inspector owns browser-persisted presentation
preferences. The departure is deliberate and narrow: that rule governs
preferences about the chart, and this one is about the app. It is also the
first browser-persisted control on the Settings page, beside a form whose
three fields are written to disk behind Save. The section is visibly separate,
its control applies instantly, and it touches neither the restart notice nor
the store alert, both of which speak for the form's three keys, so the form's
contract is untouched.

**Why not `data/settings.json`.** Rejected on cost, not principle. Settings v1
is a closed set of three string keys, so a new key is settings v2: a
validator, a version bump, the stamp script becoming a real migration under
the documented ordering contract, the launcher's trial-run window to be solved
for the first migrating release, and an older build refusing the v2 file on
rollback
([2026-08-11](#2026-08-11-durable-json-stores-carry-a-schema_version-stamp)).
A cosmetic preference should not be what forces that. When a setting that
deserves v2 arrives, this one joins it; only the store's backing would change.

**Instant apply needs one tick, and the tick is load-bearing.** The obvious
callback pair — the store as `Input` to the switch, the switch as `Input` to
the store — is a dependency cycle the Dash renderer refuses, so the switch is
initialized by a one-shot `dcc.Interval` that reads the store as `State`. That
tick is also the gate on the write direction, and this is the part worth
remembering: mounting the page fires the write callback with the switch's
*layout default* despite `prevent_initial_call`, with the switch itself as
`ctx.triggered_id` — so the repo's usual triggering-id guard does not catch
it, and without the gate, opening Settings wrote the on value over a stored
off. Ordering makes the gate safe rather than lucky: once the tick has landed
the switch already holds the stored value, so the worst a late mount-fire can
write is the value that was there. Any future browser-local control on a page
layout has the same hazard.

**Accepted costs.** Browser persistence is per origin and is cleared with site
data. Both fail towards "celebrations came back", never towards silence, which
is why only the exact `"off"` value silences the family: a style name a later
build wrote, or a store this build cannot read, still celebrates. The layout
default is not a third cost: a `dcc.Store` writes it to storage only when
nothing is stored yet and otherwise takes the stored value, so changing the
default later resets nobody's setting. That is the opposite of Dash
`persistence`, which keys the stored value on the layout default and drops it
when that default moves (the
[2026-08-20 point-customization entry](#2026-08-20-run-points-get-a-size-preset-and-a-color-and-the-chart-stops-there)
records the controls that pay it), and the distinction matters when the
follow-up changes the default style. One more, inherited rather
than introduced: `message_queue` is process-wide and each drain's payload
reaches one client, so with two tabs open a batch lands in whichever drain
runs first. That is the single-consumer shape the page's drain already had,
and the supported usage model stays one active tab.

**Preview, and the styles that follow.** Preview plays the currently selected
style through the same clientside path a real celebration takes, so it obeys
the reduced-motion guard; it shows no toast, because the toast reports a run
and there is no run. It ships in version one because it is the only way to see
the effect without setting a personal best. The follow-up converts the switch
to a select over Off, Confetti, Fireworks, Cannons, and Stars — curated
presets only, no duration, particle, or color knobs, no custom style, and no
Random option. Since the proposal file is deleted, its specification of that
step is recorded here: Confetti is the upstream Realistic Look recipe
unchanged (five bursts from one origin, about 200 particles, about three
seconds); Fireworks is the upstream Fireworks recipe cut from 15 s to about
3 s; Cannons is School Pride cut to about 2.5 s with the app's accent colors
in place of the demo's red and white; Stars is the upstream Stars recipe
unchanged (three volleys, star and circle shapes, no gravity). Snow is
ambient rather than a celebration and is excluded. `confetti.reset()` clears
particles but does not stop a `setInterval` or animation-frame loop, so the
two loop-based recipes must not be taken from the demo verbatim — each style
is bounded to about three seconds and must cancel cleanly.

Shipped in PR #268; ruled on #248.

## 2026-09-01: Configured Ports And Poll Intervals Are Bounded At Load

Status: Accepted

A port a machine could never serve, such as 70000, used to get all the way to
the socket and fail with a raw Python traceback. It now fails as the
configuration file is read, with one line naming that file and exit code 1.
The accepted range is 1 through 65535, and the poll interval must be between 1
and the largest delay a browser timer can hold. The example configuration file
states both rules beside the settings they govern.

Provenance: retires the "Out-of-range port crashes with a raw traceback" entry
adopted into `docs/tech_debt.md` from the 2026-08-12 engineering audit corpus
(PR #258); fixed in PR #266.

**The bounds.** `ConfigData.port` is `Annotated[int, Field(ge=1, le=65535)]`
and `polling_interval` is `Annotated[int, Field(gt=0, le=2_147_483_647)]`, both
shaped like the `kovaaks_api_timeout_seconds` bound that preceded them. Nothing
else in `ConfigData` gained a constraint: `sens_round_decimal_places` and the
cache TTLs stay unbounded, deliberately. The scope is these two fields, so a
bad `host` keeps its own later, differently-worded failure at the bind rather
than joining this exit.

**Why validation, not a bind-path fix.** An unbounded `port` reached
`sock.bind()`, which raises `OverflowError` ("bind(): port must be 0-65535")
rather than `OSError`, so neither `_bind_face`'s `except OSError` nor
`bind_server_socket`'s errno-classifying one caught it. Bounding the field
turns the same input into a `ValidationError`, which `main()`'s existing
configuration handler already converts into the curated "Configuration error:
could not load `<path>` -- copy example.toml to config.toml." exit. The
collapsed one-message design is unchanged: the ranges are stated in
`example.toml`, where the user is already looking when they edit the setting.

**Why configured `0` is refused.** Port `0` is valid to the socket layer and
still supported there: `bind_server_socket(0)` asks the OS for a free port and
is unchanged, which direct callers and the socket tests rely on. It is not a
usable configured endpoint, though, because the installed launcher reads the
configured port before startup (`Get-ConfiguredEndpoint`), polls
`http://<probe>:<port>/health` on that exact port to decide the app is ready,
and opens the browser on it. An OS-chosen port is one the launcher cannot
discover, so the app would serve while the launcher declared a readiness
timeout.

**Why `polling_interval` is bounded at both ends.** The value is handed
straight to `window.setInterval` -- Dash 4.4.1's Interval calls
`setInterval(this.reportInterval, props.interval)` with no clamping -- and that
delay is a signed 32-bit int. Both ends of the range therefore produce the same
silent request flood: a non-positive period, and one above `2147483647`, which
overflows and fires immediately. Measured in Chromium, `2147483647` never
fired and `2147483648` fired at 0 ms.

The upper bound is browser representability, not a product cap. A *product*
cap -- one tight enough to keep the run-event freshness window small -- stays
rejected on the PB-celebration proposal's reasoning: that window already
absorbs an arbitrarily slow poll by adding the configured period to its cap,
and a tight cap would refuse config files that load today for the sake of a
toast. `2147483647` ms is about 24.8 days, so it refuses only values the
browser could not have honoured anyway.

## 2026-08-31: Repeatable Toasts Replace In Place With A Visible Re-Entry

Status: Accepted

Every toast that answers one thing you did now replaces its own previous copy
with a visible re-entry, instead of stacking a duplicate or being dropped in
silence. Importing a second playlist while the first import's toast was still up
used to show nothing at all; both toasts now stand, because reports about
different playlists are different toasts. A retry of the same action pops its
answer back onto the screen with a fresh eight seconds, and a success clears the
failure message it answers. The one deliberate exception is the background
report that folds several unreadable run files into a single message, which
keeps batching exactly as it did.

Provenance: distilled from `docs/toast_policy_proposal.md` (three decisions
ratified 2026-08-30), committed in PR #257 and deleted in this shipping PR --
git history holds the full text, including the design-system and UX survey the
policy rests on and the live POC that measured the mechanism.

**The policy.** Every toast is classified before it is written, by two
questions. First: can the reported fact recur inside one toast lifetime, judged
against the complete supported workflow *including inverse actions that make
the same subject eligible again*? A fact that cannot recur is an **event
toast** -- unique id per emission, plain `show`, occurrences stack, no registry
wiring. A fact that can recur is a **channel**. Applying that test to today's
inventory leaves the event bucket empty: every current toast's fact can recur
through some supported cycle, so the rule exists to classify future toasts, and
any claim that a fact cannot recur must survive the inverse-action check
(delete-then-re-import defeats the naive claim for import success).

Second: what is the channel's identity? Identity follows the semantic lane. An
operation's **problem lane** is one channel: its mutually exclusive outcome
flavors (a red hard failure, a yellow served-stale) share one key with a
differing payload, so two contradictory claims about the same latest attempt can
never be on screen together. **Success lanes** and **standing-condition lanes**
are their own channels, keyed by subject when independent subjects can be in
flight at once -- one success channel per scenario, one per playlist code. The
mutual-exclusion clause is deliberately problem-lane-only: success flavors of
one operation (a green full success, an orange partial one) may keep distinct
channels, accepting the narrow cross-flavor window a re-attempt can open. Lanes
interact only through explicit **cross-clears**: a success hides its operation's
problem channel and any standing-condition channel it falsifies.

A third pattern survives untouched: a **burst toast** folds many same-type
events into one summary carrying a count and points at where the individual
events are recorded. And persistence (`auto_close=False`, process- or
session-gated) stays orthogonal to all three.

**The mechanism: hide-and-reshow.** A channel emission shows a *fresh instance
id* -- the logical channel key plus a per-emission unique suffix -- and lists
the channel's previous instance id, plus any cross-clear targets' current ids,
in the container's separate `hideNotifications` prop. Why a new id: DMC 2.8.0
ignores a `show` whose id is already on screen, so a stable id answers a retry
with nothing. Why the pairing works in one response: the container declares its
hide effect *after* its send effect, so the fresh instance enters with the full
animation while the outgoing one animates out. The POC measured the result on
2026-08-29 against the installed DMC (harness under
`ignore/scripts/toast_hide_reshow_poc/`, findings on PR #257): first paint about
31 ms after the click, a ~135 ms entry slide, a ~250 ms crossfade with
complementary opacities that reads as replacement rather than as two toasts,
and a structurally fresh ~8.0 s lifetime even when replacing at 7.5 s. Hiding an
absent or already-closed id is a clean no-op with a clean console. Accepted
cosmetics: a toast that arrived as a replacement auto-closes without its own
exit fade, and bystander toasts bounce upward for roughly 280 ms during a
replacement.

**The registry.** The store beside the container is now
`toast-channel-registry`: a dict mapping each logical channel key to its current
instance id, read as `State` and written as an `allow_duplicate` `Output` by
every emitting callback. It sits in the app shell, not a page layout, for the
reason the counter it replaces did: a toast outlives the page that emitted it,
and a page-scoped store would reset on navigation and leave a visible toast with
no id to replace it by. **Writes are per-key `dash.Patch` assignments, never
whole-dict replacements.** This is load-bearing, not tidiness: a response that
rewrote the whole dict would carry a stale value for every channel it did not
emit, so two responses landing out of order could resurrect an obsolete instance
id -- leaving two toasts of one channel on screen, or a problem toast beside the
success that cleared it. What remains is only same-operation concurrency, which
the renderer covers rather than loading guards: every channel has exactly one
producing callback, and Dash 4.4.1 marks an older in-flight invocation with the
same output set outdated and discards its response.

**The conversions (13).** Subject-keyed channels, keyed by the canonical stored
code and never the pasted input: `imported-playlist-successful-{code}`,
`imported-playlist-visibility-failed-{code}`,
`deleted-playlist-successful-{code}`, plus `rank-refresh-success-{scenario}`
keyed by the scenario name verbatim (toast ids are internal, never parsed apart
and never rendered, so identity is the stable collision-free derivation and a
hash would only add a collision it cannot have). Single-identity channels: the
three per-action failure toasts, the two refusals, the constant-copy cleanup
success, and username-unset, whose uuid suffix goes. `rank-refresh-failed` and
`rank-refresh-stale` merge into one `rank-refresh-problem` channel whose payload
carries the red or yellow outcome. `run-verdict` rides the same helper.
Cross-clears: each import outcome clears the import failure, delete success
clears delete failure, cleanup success clears cleanup failure, and refresh
success clears both the problem channel and username-unset. No user-facing
string is added or edited; titles, messages, colors, and icons carry over
verbatim.

**Both upsert helpers are deleted.** With every channel on hide-and-reshow,
the `update`-plus-`show` pair with its alternating 8000/8001 ms durations
existed for one toast only, so `run-verdict` migrates and the trick goes with
its sequence store. The ratified run-verdict contract is preserved -- one run,
one toast, the newest verdict replacing what is on screen with a full lifetime,
per browser client and across navigation -- with one qualifier: during the
~250 ms replacement crossfade the outgoing instance is still animating out, and
each new verdict now re-enters with the pop animation instead of morphing in
place. `upsert_sticky_toast` goes with it, because `channel_toast` carries the
payload's `autoClose` through untouched instead of stamping a lifetime, which
is the only thing the sticky sibling existed to avoid.

**The personal best celebration is reconciled onto this policy.** PR #261
landed the `pb-celebration` toast through `upsert_sticky_toast` while this
proposal was still under review, so it arrived as the one family the standing
rule had not been applied to. It is a channel by the classifier -- a second
personal best inside one lifetime is plainly reachable -- so it moves to
`channel_toast` as a **persistent channel**: its own key, still distinct from
`run-verdict`, a fresh rendered instance per celebration, the previous instance
hidden with it, and `auto_close=False` passed at its builder so it still stays
until dismissed. Its ratified product contract is untouched: a dedicated lane
that an ordinary run verdict lands beside rather than replacing, the newest
celebration replacing the previous one, and no lifetime. What changes is only
the mechanism, and one visible detail that follows from it -- a second personal
best now re-enters with the pop animation instead of morphing in place, which
is the same visible re-entry every other channel gets and the reason it is
wanted. This is a mechanism conformance change, not new celebration scope; the
in-flight personal best celebration proposal is updated in step.

**What this supersedes.** The
[2026-08-03 notification-layer entry](#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)
loses three clauses: its per-click-id exception to the stable-id rule (the green
refresh confirmation and, via the 2026-08-09 entry, the blue unset-username
notice are now subject-keyed and single-identity channels, so nothing needs a
per-click id), its rationale for keeping the two refresh-failure outcomes under
distinct ids (they are one channel now, which is what stops them contradicting
each other), and the absolute reading of "at most one run-verdict toast is
visible at a time" (true once a response has been applied, with the crossfade
qualifier above). Its "`hide` cannot substitute" note stands as written and is
exactly why this works: the hide effect running *after* the send effect is what
lets a differing id pair show-and-hide in one response. The
[2026-08-09 unset-username entry](#2026-08-09-an-unset-username-is-stated-in-place-never-reported-as-a-failure)
loses only its per-click-id mechanism; its ruling -- that an unset username is
configuration state answered blue, never a red failure -- is untouched.

**Deliberately out of scope.** `run-import-failure` keeps its own cross-tick
swallowing: a second batch inside 8 s is dropped. It is a background burst
channel where anti-flood wins, its folded copy already points at `debug.log`,
and no user report exists; if it ever surfaces, the fix is a replacement
channel, not uuids. The research's broader position that error toasts should be
banners or inline messages is a much larger re-platforming question, deliberately
not opened. Mantine's visible-toast `limit` and queueing defaults stay untouched
as the flood backstop.

## 2026-08-30: One Severity Color Language For Inline Notices

Status: Accepted

The app's inline notices each picked their own look, so the surfaces that most
needed attention were the faintest things on the page. They now speak the same
severity colors the toasts already do, and every one of them carries a leading
icon. The first-run setup card is tinted like the rest instead of being a white
card on a white page, and the leftover-playlist-files notice became a plain
panel so screen readers are no longer told that a panel of buttons is an alert.
No wording changed anywhere.

Decision: one severity scale governs every notification surface, inline and
toast alike. Blue is informational and any action it offers is optional; yellow
is caution, an attention-worthy negative outcome or a state that needs the user
without anything having failed; red is an error, an operation that failed;
green is a positive outcome; orange is partial success, where the action
committed but a follow-up write did not. Green and orange stay toast-only:
no inline success or split-outcome panel exists, and none is added. Yellow
deliberately spans both configuration states and coaching outcomes such as a
below-threshold run, because a narrower warning-only reading would leave the
shipped threshold verdicts outside the scale.

Why: the severity information already existed in the code and did not reach the
eye. Three of the four alerts were `color="yellow"` with Mantine's `light`
variant, whose yellow tint is the palest token in the palette and reads as
near-white in light mode, and none of them had an icon; the fourth hard-coded
`#ff6b6b`, a red tint on a purely informational banner. The setup card, the
first notice a fresh install ever shows, was an untinted `dmc.Paper` on the
untinted page body. In a live render the icon, not the background, was the
dominant legibility fix.

The component rule: which component a notice uses follows its content model,
not its look. Mantine renders `Alert`'s root with `role="alert"` and the dmc
2.8.0 wrapper exposes no role override. Per
[WAI-ARIA 1.2](https://www.w3.org/TR/wai-aria-1.2/#alert) that role is an
assertive, atomic live region for important, usually time-sensitive messages,
and [MDN's guidance](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Roles/alert_role)
draws the consequences this rule applies: the role is for text content rather
than interactive elements like links or buttons, and for content that appears
dynamically rather than with the page. So a text-only notice may be a
`dmc.Alert`, and a notice holding interactive controls is a `dmc.Paper` wearing
the alert anatomy through the shared `.alert-panel` classes in
`assets/stylesheet.css`. Should an interactive notice ever need announcing, the
shape is a separate polite status message, or an alert dialog for a workflow
that requires a response, never `role="alert"` around controls.

The five inline surfaces as shipped: the Settings store alert and the Playlists
visibility alert stay yellow `dmc.Alert`s and gain
`material-symbols:warning-outline`; the Aim Training Journey work-in-progress
banner becomes blue with `material-symbols:info-outline`, deleting the hex; the
Playlists leftover-files notice becomes a blue `dmc.Paper`, keeping its id, its
callbacks, and its hidden-class reveal; the Home setup card keeps its
`dmc.Paper` and takes the blue treatment for the identity offer and the yellow
one for the blocking stats-folder state, with the matching icon beside its
title. Both icons were already vendored, so no assets were added. Mantine
defines the `-light` tokens per color scheme, so dark mode needs no separate
rules.

Rejected: one accent color for every inline notice, which is calmer and uniform
but makes "your saved choices are silently not applying" look identical to an
FYI and splits the app into two color vocabularies, one for toasts and another
for panels. Rejected for the setup card: one color for both states, which hides
that the first state blocks every plot on the page while the second is a
skippable offer. Rejected for the leftover-files notice: yellow, which keeps
housekeeping louder than the problem warrants and dilutes the two yellow alerts
that earn it. Rejected as variants: `filled`, far too loud for a persistent
panel and poorly contrasted in yellow, and `outline` or `default`, both whiter
than what shipped before. Rejected as a component: rebuilding the setup card as
a `dmc.Alert`, which would entrench the role mislabel permanently rather than
merely start from the wrong place. The `dmc.Paper` anatomy carries one ongoing
cost, accepted knowingly: it tracks Mantine's `Alert` look by hand across
upgrades.

Extends the toast layer specified by the
[2026-08-03 notification entry](#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy),
which stays authoritative for toasts, including their white-card-with-icon
anatomy: an icon suppresses Mantine's colored side bar, so a toast's color is a
circle rather than a stripe, and nothing here changes that. Orange keeps the
meaning the
[2026-08-02 committed-side-effect entry](#2026-08-02-a-committed-side-effect-reports-its-outcome-even-when-a-later-write-fails)
gave it and stays a distinct severity rather than folding into yellow.

Deferred: strengthening the pale yellow tint with a scoped CSS override. The
icons are expected to be enough, and the override is a one-line follow-up if
they are not.

## 2026-08-22: The Playlist Fill Reports Degradation In Place Only

Status: Accepted

Opening a playlist used to end a degraded position update with a red or
yellow toast that repeated a count the page's own status line already showed.
The toast is gone. The status line above the grid, beside the filter box, is
now the only place the fill reports that positions were unavailable or served
from cache, and a clean fill still clears it and stays silent. Nothing else about the update
changes.

Decision: the progressive fill on `/playlists/<code>` states degradation in
its status line and emits no notification. `_fill_summary_notification` and
the `notification-container.sendNotifications` output of
`drain_playlist_scenario_rows` (`source/pages/playlist_scenarios.py`) are
deleted; the callback returns the row transaction and the status only. The
status copy is unchanged, and `tests/test_playlist_pages.py` guards the
callback's declared outputs so the toast cannot return unnoticed.

Why: the toast was non-conformant against the
[2026-08-03 routing policy](#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy).
A degraded fill is an automatic failure during passive navigation, which that
entry routes to in-place state with no toast, and its second litmus — already
visible somewhere? then nothing — is answered by the status line, which
carries the same counts ("1 of 3 positions unavailable · 1 from cache —
KovaaK's unreachable") in the filter row directly above the grid the user is
already reading.

Rejected: ratifying the toast as a third named exception to the
persistent-condition rule, beside the Steam-ID mismatch and the startup
playlist warnings. Both of those earn their exception by having no in-place
home; this fill has one, on screen, in the reader's line of sight. The
exception would be defensible only if the status line were easy to miss, and
it is not. Ratifying it would also have made "the policy names it" the test
for conformance rather than the litmus tests themselves.

Supersedes, in part, the
[2026-07-15 progressive-fill entry](#2026-07-15-stream-playlist-positions-with-generation-scoped-progressive-fill):
its completion-toast clauses only — the first terminal tick no longer "emits
any aggregate completion toast", and "Completion uses the existing
red/yellow/silent failure tiers" no longer describes a notification. The two
phases, the generation-scoped row identity, the cancel-on-start rule, the
tombstone retention and eviction order, the pending-flag rules, the outcome
counting, and the status settling are all unchanged and remain Accepted.

Discharges, for the playlist page only, one half of what the
[2026-08-09 unset-username entry](#2026-08-09-an-unset-username-is-stated-in-place-never-reported-as-a-failure)
left open. That entry deferred the configured-but-wrong-username case,
noting it "still produces both generic red toasts today". A wrong username
resolves every position to `UNKNOWN`, so the aggregate toast was the
playlist page's half, and deleting it settles that surface: the fill reports
the count in place, like any other degradation.

The other half stands, and this entry rules nothing on it. Clicking Refresh
on Scenario Performance with a wrong username still answers with the generic
red "Position refresh failed" toast, and correctly so — a manual Refresh is a
user-initiated failure, which the routing policy toasts. Neither surface
diagnoses the wrong username: the playlist status line says positions are
unavailable, not why. Naming the condition is still the open question, and a
typed reason on `ScenarioRankInfo` is still where it should be
reconsidered.

Consequences: the app has one fewer toast id, and the notifications
inventory in [specs/notifications.md](specs/notifications.md#inventory)
loses its `playlist-progressive-fill-{generation}` row. The fill's
background-thread channel is untouched — it still streams rows into the
registry an interval callback drains, which was never a notification path.

## 2026-08-22: The Capability Spec Layer Is Written In One Pass

Status: Accepted

Every shipped capability with a durable behavior contract must have a spec
that states what the app does today, and the four still missing are being
written in one deliberate pass instead of waiting for a change to touch each
capability. A new capability brings its spec in the PR that ships it, and a
change to specified behavior updates the spec in the same PR. The specs are
how a reader finds the decision behind a behavior, so the log still keeps no
topic index.

Decision: the "do not backfill specs ahead of need" rule in `AGENTS.md` is
replaced by a standing criterion — **every shipped capability with a durable
behavior contract must have a spec under `docs/specs/`**. A new capability
gets its spec in the shipping PR; a PR that changes specified behavior
updates the spec in the same PR (the "Shipping a proposal" checklist's step 2
now says the same thing). The criterion is a requirement, not a description
of the tree: when this entry landed the directory held two specs, and the
four the pass names below are in flight as their own PRs, so the layer is
complete only once those merge. The `AGENTS.md` "Scenario Rank Feature"
pointer becomes a
"Capability Specs" section pointing at the directory, which lists itself, so
no per-spec list is touched by every spec PR; `architecture.md`'s "Where to
look first" table carries the same pointer.

The pass: five specs, five PRs, each authored by a Fable session and reviewed
by a fresh Fable session plus Codex, in dependency order —

- `notifications.md` (PR #249; also carries this entry and the rule change),
- `settings.md` (after notifications: its in-place statuses cite the routing
  policy),
- `scenario_performance.md` (after settings: the Chart options switches'
  gating semantics live in the notifications spec, their placement and
  persistence here),
- `playlists.md` and `release_and_install.md`, independent of the others and
  of each other.

Deliberately excluded: app copy, which the app messaging consistency
proposal (PR #247) leaves out of the spec layer; bug-report intake,
which one decision-log entry covers in full; Home as a standalone capability,
folded into `scenario_performance.md`; and tooling and process, for which
`AGENTS.md` is the spec.

The spec contract, which every file in the pass follows and later specs
inherit:

- Statement form, present tense, no rationale. Each statement links the
  decision-log entry that governs it by heading anchor; a statement with no
  governing entry is an implementation fact, stays unlinked, and is covered
  by the preamble's disclaimer — no entry is invented for it.
- Verified against code or a test before it is written, never transcribed
  from the log. The PR body carries the evidence map; the spec does not.
- Where code contradicts an entry, the spec states what the code does and
  the PR body lists the contradiction as a finding for the maintainer. No
  code changes ride in a spec PR.
- Supersession is cited as current: the governing entry, or the surviving
  clause "as amended by" the amending entry; a superseded clause is never
  cited as current.
- Opens with a layer-1 summary held to the 2–4 sentence budget, then H2
  sections. No `Status:` line; anchors as GitHub slugs them
  (`tests/test_docs.py` validates both).
- App strings are quoted exactly as the code has them, shipped em dashes
  included. Specs link `architecture.md` and `product.md` rather than
  restating them, and link another spec only to say a rule lives there.

Consequences: the
[2026-08-01 doc-style follow-up entry](#2026-08-01-doc-style-follow-up--decisions-needed-roadmap-trim-no-log-index)'s
"revisit a log index only if findability still hurts after specs land"
loop closes when the pass's last PR merges — the specs are the findability
fix, and a topic index stays rejected; until then the loop is open only in
the sense that the fix is still landing. `docs/product.md` and
`docs/roadmap.md` are untouched: nothing user-facing changes.

## 2026-08-21: The Empty Point Color Is Called Default, And The Points Follow The Theme

Status: Accepted

The Point color field's empty state now reads Default instead of Automatic,
and its reset button reads Use default. Automatic suggested a Manual mode that
never existed, and Default is the word the Point size control beside it
already uses. The run points with no color chosen used to be the same indigo
in both themes; they now take the theme's own blue, a little deeper in dark
mode. The small preview swatch beside an empty field used to be plain white;
it now shows the color the graph is using in the current theme.

Decision: the first change is copy only. The stored value is unchanged: an
empty `point-color` still means the generated color, under the same persisted
id, so nothing a browser already saved is discarded. `POINT_COLOR_AUTOMATIC`
became `POINT_COLOR_DEFAULT`, and the reset button's id `point-color-default`.

**The run points take the theme template's colorway.** The 2026-08-20 entry
says an empty color keeps whatever Plotly and the Mantine template give it.
Until now the Mantine template's colorway never reached the run points:
`px.scatter` writes the first colorway entry of Plotly's default template,
`#636efa`, into the trace's `marker.color` when the figure is generated, and
the `update_layout(template=...)` applied afterwards never overrides a
property the trace already sets, so the points were `#636efa` in both themes.
The generator now clears that baked color (`marker_color=None`), so the run
trace carries no color of its own and Plotly draws it in the first colorway
entry of whichever template the theme applies: `#228be6` (blue-6) under
`mantine_light`, `#1971c2` (blue-7) under `mantine_dark`. First entry because
the run trace is the figure's first trace; colorway assignment is by index in
Plotly, and that ordering is pinned by test. `plot_service.generated_point_color`
reads the same entry for a scheme, and is the single source for the preview.

**How the swatch shows it.** Mantine's `ColorInput` renders its preview as a
`ColorSwatch` whose color is the value when valid and a hardcoded `#fff`
otherwise, as an inline style. Home sets `--point-color-default-light` and
`--point-color-default-dark` on the field from `generated_point_color`, and
two stylesheet rules scoped to `.point-color-field:has(input:placeholder-shown)`
(the second under `:root[data-mantine-color-scheme="dark"]`) repaint the
swatch's color overlay from the active one with `!important`, the only way
past an inline style. A typed or picked color hides the placeholder, and the
rules with it, so Mantine's own preview of that color takes over. Alternatives
rejected: **keeping the baked `#636efa` and previewing it as a constant**,
which leaves the theme template decorative for the primary data mark;
**storing a hex as the layout value**, which moves a persisted default
(discarding stored values) and turns the generated color into a chosen one;
**replacing the preview through `leftSection`** with a swatch kept in sync by
a callback, a round trip per keystroke to do what two CSS rules do.

Not changed: the Average Score line, which `px.line` bakes in the same
`#636efa` and which now sits beside blue points. Clearing its color would hand
it the colorway's second entry (red) rather than the points' color. Ruled
2026-08-22: the line gets a user setting of its own in a later PR, not a
colorway change here.

## 2026-08-21: Run Notifications Have A Master Switch, And The Threshold Switch Is Renamed

Status: Accepted

Run toasts can now be turned off. Chart options carries a Run Notifications
switch, on by default, and turning it off silences the toasts that report how
a run went while the chart keeps updating in the background. A run file that
fails to import still says so, and nothing else about the toasts changed. The
switch that used to be labelled "Score Threshold Notification" never gated
toasts at all, only whether a run was judged, so it is renamed "Score
Threshold Verdict" and its help text now says what it actually does.

Decision: a `dmc.Switch` with id `run-notification-switch`, `checked=True` and
`persistence=True`, in a new **Notifications** group at the end of the Chart
options inspector.

**What the switch gates.** All three shapes `_build_run_event_notification`
produces: the threshold verdict, the top-N placement, and the "While you were
away" catch-up digest. They share one toast id and one producing function, so
the gate is a single early return at the top of that function rather than a
check per shape. The digest is deliberately inside the gate: it is the same
family reporting the same events, and a digest that survived the off switch
would read as a bug rather than a feature. The catch-up case that survives it
is the planned run history, not a toast.

**What it does not gate.** The red run-import failure toast
(`run-import-failure`, its own interval callback) is error feedback rather
than run feedback and stays on; the master switch's help text names the three
shapes it covers instead of saying "all notifications", so it cannot be read
to promise otherwise. With the switch off the plot still updates, scenario
auto-switch still follows a new run, and the rank-refresh, Steam-mismatch, and
playlist toast families are untouched.

**The threshold switch is the verdict sub-toggle, not a second master.** Four
combinations, all defined: master off is silence whatever the threshold switch
says; master on with threshold on is the behavior that shipped in the
[notification redesign](#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy);
master on with threshold off is that redesign's judging-off behavior, meaning
placement toasts and neutral digests only. Its id, default, and persistence
are unchanged — renaming the id would orphan every value a browser has already
stored under it — so only its label, its help text, and the dated code comment
beside it move. That comment, and the "knowingly imprecise" consequence
recorded in the
[Chart options rename entry](#2026-08-09-the-graph-page-is-scenario-performance-its-panel-is-chart-options),
are resolved here: this is the later copy pass that entry deferred, for the
two strings it touches and no others.

**`State`, not `Input`.** The switch's value matters only when
`run-events.data` triggers `generate_graph`. Wired as an `Input` it would
rebuild the plot and reread the scenario's runs every time someone flipped a
notification preference. The existing threshold switch has the same
State-worthy property but stays an `Input`; changing it is a behavior change
with its own review.

**Storage is browser-local Dash persistence**, like every other Chart options
control. `data/settings.json` was rejected: it is scoped to the stats
directory and the KovaaK's identity behind a Save model, which is the wrong
interaction for a switch that should take effect the moment it is flipped.
`config.toml` was rejected: it holds human-owned boot facts.

Rejected alternatives:

- **The digest surviving the off switch.** It would preserve a rare catch-up
  toast at the price of a switch that is not quite off.
- **Per-family toggles** for import failures or rank-refresh feedback. Each of
  those is error or action feedback, and nothing asked for them.
- **App-wide notification production**, deliberately deferred rather than
  dropped. Run toasts are produced only on Scenario Performance because the
  producing interval, store, and preferences are mounted in that page's
  layout. Making production app-wide is a redesign of the queue-to-UI flow
  with its own product questions, and this change forecloses none of it: the
  guard sits at toast production wherever that later runs, and Dash
  persistence survives a same-id component move.

**Superseded in part (2026-09-02).** The catch-up digest above no longer
exists, so the gate covers the threshold verdict and the placement alone, and
the help text gained a second sentence naming the celebration's own setting.
The last rejected alternative's deferral of the queue-to-UI redesign also
falls, for the drain alone; the product question it protected, app-wide
verdict toasts, stays deferred. Both are recorded in
[A New Personal Best Celebrates On Every Page](#2026-09-02-a-new-personal-best-celebrates-on-every-page).

Shipped in PR #245; design discussion in #240. Distilled from
`docs/run_notifications_switch_proposal.md`, now deleted.

## 2026-08-21: Release Integrity Rests On GitHub Digests And An Enforced Archive Contract

Status: Accepted

The first thing a new visitor asks about a downloadable Windows app is whether
it is safe to run, and the release page is where that gets answered. This
project relies on the SHA-256 digest GitHub publishes for every uploaded asset,
together with releases that can never be changed, rather than shipping a
checksum file of its own. The release page now opens with a short header saying
what those guarantees are and which download to take, and CI now proves
byte-for-byte that the uploaded assets are the ones it built. The release zip
also stopped carrying development-only files that an installed copy cannot use,
and a new pre-publish check fails the draft if the zip ever loses a file an
install needs.

Decision: no custom `SHA256SUMS.txt`, no hash duplicated into the release
notes, and no launcher-side hash verification at launch. Integrity rests on
GitHub's per-asset digests plus immutable releases, which this repo already has
enabled — see
[Releases And Their Assets Are Immutable](#2026-07-19-releases-and-their-assets-are-immutable),
which this entry extends rather than restates. Alongside that: the release page
gets a curated header, `.gitattributes` prunes development-only trees from the
archive, and `validate_release` enforces an archive contents contract before
publication.

Why: at this audience size the marginal security of a project-published hash
over a platform-published one is zero, and both are downloaded over the same
HTTPS connection from the same host. GitHub's digests are visible on the
release page, are computed by GitHub on receipt, and cannot change afterward
because the release is immutable. Both of our assets additionally carry a
GitHub-signed release attestation, retrievable at
`repos/.../attestations/sha256:<digest>` — supporting evidence for this
decision, deliberately not surfaced in user-facing copy, because attestation
commands are not something a general user should be asked to run.

Rejected alternatives:

- **A custom `SHA256SUMS.txt` asset.** Redundant with digests GitHub already
  publishes and signs, and it would be permanent release machinery — generated,
  validated, and maintained on every release — bought for no added security.
  It also invites the copy failure this entry avoids: a hash pasted into the
  notes reads as proof of trustworthiness rather than of byte integrity.
- **Launcher-side hash verification at launch.** It touches the frozen update
  contract, the named-asset/source-archive fallback, and failure behavior all
  at once. The launcher already validates `release.json`'s identity fields and
  health-gates promotion on the SHA carried in `version.txt`, so the marginal
  gain is small. Deferred until evidence demands it, consistent with the
  deferral already recorded in the 2026-07-19 immutability entry.

Consequences and constraints:

- **Digests cover uploaded assets only.** Every release page also shows
  GitHub's auto-generated "Source code (zip / tar.gz)" downloads, which have no
  digest. Copy must never claim digests for "every download", and must never
  say "verified safe" or "secure download" — a digest proves byte integrity,
  not trustworthiness.
- **The archive is a contract, and it is enforced.** `validate_release` rejects
  the draft unless the zip carries every entry in `REQUIRED_ARCHIVE_ENTRIES`
  and none of `EXCLUDED_ARCHIVE_TREES`. The required set covers installation,
  runtime, legal, and self-documentation needs rather than only files read by
  code, and it is deliberately not a snapshot of the whole tree: each entry is
  listed with what reads it. Without this, a `.gitattributes` edit or a file
  move that drops an install-critical path is undetected until someone's
  install fails, and immutability makes the bad asset permanent.
- **Name the file when something opens it by name.** A directory entry in the
  required set only asserts that the tree holds at least one file, so it still
  passes after the one member that mattered is renamed away. Required
  individually for that reason: `source/app.py`, `scripts/launch_bootstrap.ps1`,
  and `scripts/launcher.ps1`, which the launcher, the installer, and the
  bootstrap each open by name and abort without; and `docs/example.png`,
  `docs/architecture.md`, `docs/product.md`, and `docs/roadmap.md`, which are
  every relative target the shipped README opens. A test cross-checks that
  README target set against the contract, so a new link into `docs/` cannot
  quietly fall outside it. Only `assets/` and `resources/` remain directory
  entries, where no single member is the dependency.
- **A tree holding only its own directory entry is empty, not present.**
  `git archive` emits an entry for each directory, and a `/**` export-ignore
  rule leaves that entry behind after removing every file under it, so a
  prefix match alone would accept an empty required tree. The check requires a
  child path, and a regression test covers each required directory in that
  shape.
- **`export-ignore` is narrow, and `docs/` stays.** `/tests`, `/.idea`, and
  `/.github` are pruned. `docs/` ships because the shipped README embeds
  `docs/example.png` and links `docs/*.md`, so dropping it breaks the zip's own
  front page for the manual-install reader. `resources/`, `scripts/`,
  `install.ps1`, and `version.txt` must ship for the app, the installer, the
  launcher, and build identity respectively.
- **Use the anchored directory form.** Tested on git 2.55: `/tests`, `tests`,
  and `tests/` all prune the directory entirely, while `/tests/**` removes the
  files and leaves an empty `tests/` directory entry in the zip. The contract
  treats an empty excluded directory as still shipped, so the two rules agree.
- **`export-ignore` also prunes GitHub's source archive.** The
  `archive/<sha>.zip` download changes the same way. That is intended, and it
  matters because that archive is the launcher's documented fallback when the
  named asset is missing, and because the CI stamp job downloads it.
- **The digest check is a build-versus-upload comparison, not a size check.**
  It recomputes SHA-256 locally and requires equality, treats a null or missing
  digest as a failure rather than a skip, and requires the release to carry
  exactly the versioned zip and `release.json` — a resumed draft keeps any
  asset `--clobber` never replaced. It subsumes the size comparison it
  replaced.
- **Blocking a release and shipping a file are separate lists.**
  `_BLOCKED_DIRECTORIES` in `scripts/release_job.py` decides whether a push cuts
  a release; `.gitattributes` decides what the zip carries. `docs/` is on the
  first and not the second — see
  [PyCharm Config Stays Tracked And Its Upgrade Churn Is Committed Once](#2026-08-08-pycharm-config-stays-tracked-and-its-upgrade-churn-is-committed-once).

## 2026-08-21: The Launcher Narrates A Slow Start And Keeps Its 120-Second Ceiling

Status: Accepted

The launcher used to print one "Starting" line and then nothing while it
waited for the app, so a slow first start looked exactly like a hang. It now
stays quiet for the first few seconds and, if the app is still not up, prints
how many seconds have passed, repeating every few seconds until the app
answers or the wait gives up. A start that finishes quickly prints nothing
new. The two-minute limit on the wait is unchanged, on purpose.

Decision: the heartbeat lives inside `Wait-AppReady` in `scripts/launcher.ps1`,
so both call sites get it: the normal start and pending-update activation.
The output contract, ratified 2026-08-20 and shipped in PR #243:

- Ready before the ~5 s gate: nothing new. The fast path's console output is
  byte-identical to what it was before.
- Still waiting at the gate: `Still starting Corporate Serf Dashboard ... N
  seconds elapsed.`, then another line every ~5 s.
- Ready after at least one heartbeat: `Corporate Serf Dashboard is ready
  after N seconds.` No heartbeat shown means no completion line. The
  `exited` and `timeout` outcomes never print a completion line; their
  callers report the failure as before.
- The `Dashboard running at http://...` line is unchanged, and still prints
  on every successful launch by either startup path, once the app is ready.
  It was never reached on a failed start: a normal start that returns
  `timeout` or `exited` stops at `Stop-Fatal` before it.
- No reassurance or explanation sentences. The elapsed counter is the whole
  feature. Gate and interval are implementer-tunable around ~5 s; both are
  5 s today.

Why the gate is ~5 s: 14 installed starts measured 2026-08-20 on the
development machine ranged 0.12–5.62 s, median 2.18 s. The samples are
warm-biased and single-machine. A slow-but-healthy warm start may therefore
occasionally show a single heartbeat line; that is accepted, do not tune it
away. Why this copy: it echoes the launcher's own vocabulary ("Corporate Serf
Dashboard", the existing "Starting ... " lines). Never "the dashboard" for
the thing being started; a prior ruling found it reads as the browser.

The cadence is a floor, not a schedule. Loop granularity is an in-flight
health probe's two-second timeout plus the half-second sleep, so a heartbeat
can land up to ~2.5 s after its nominal time and the timeout outcome can
overshoot the ceiling by about as much. On a machine where a closed loopback
port is slow to refuse, every pre-listen probe burns its full timeout, which
is why the PR's transcripts show 7/12 s rather than 5/10 s. The probe itself
is unchanged. Its address stays governed by the
[2026-08-14 configurable-listen-address entry](#2026-08-14-the-listen-address-is-configurable-loopback-by-default):
`Get-ProbeAddress` sends a wildcard bind to its own family's loopback and
every other configured host to that host's literal URL form. The gate on
the full SHA and launch token, and process exit detected at the next loop
check rather than at the ceiling, are likewise unchanged.

Why `$HealthTimeoutSec` stays at 120: the ceiling's job is failure
declaration, and timeout is destructive. On the normal start the child is
killed and the launcher exits with a fatal "check config / reinstall"
message; on the update path the pending version is killed and the previous
one is started instead. A false timeout on a genuinely slow cold start turns
"slow" into "broken" on exactly the first-run path the heartbeat exists to
protect, and the warm-biased measurements above say nothing about the
cold-start tail. Revisit only with clean-machine cold-start evidence, and
then size the ceiling at two to three times the worst observed start.

Alternatives rejected: reassurance copy such as "the first start can take
longer" (words without information; the counter already says it), and
retuning the ceiling alongside the heartbeat (no evidence to size it, and
the failure mode of guessing low is the one described above).

## 2026-08-20: Run Points Get A Size Preset And A Color, And The Chart Stops There

Status: Accepted

The Scenario Performance chart now lets you change how the raw run points look:
a Small, Default, or Large point size, and a point color chosen from eight
curated swatches, a picker, or a typed hex value. Both live in a new **Run Data
Points** group in Chart options and persist in your browser like the overlays
beside them. Leaving the size on Default and the color empty keeps exactly the
chart the app drew before. Nothing else on the chart became customizable, and
that boundary is the decision as much as the two controls are.

Decision: the inspector gains one **Run Data Points** group between *Overlays*
and *Score Threshold*, holding a full-width `Small | Default | Large` segmented
control (`point-size`) and a `dmc.ColorInput` (`point-color`). Both carry
`persistence=True`, the same browser-local model as their siblings; nothing is
written to `data/settings.json` or `config.toml`. A **Use automatic** button
beside the color field is the reset.

**The product rule.** A chart control has to answer a recognizable user goal,
not expose a Plotly property. Size and color earn their place because two goals
are demonstrable: make the points easier to see, and pick a color that reads
better for you. The interface keeps three levels — a strong Automatic or
Default appearance for most users, a small set of controls for the primary data
marks, and nothing else until a real workflow demands it. The promotion rule
follows from that: reconsider opacity only if overlapping points are shown to
hide useful density, reconsider marker symbols only if the graph ever carries
multiple semantic point categories, and if a visual-object group would exceed
roughly three controls, revisit presets or design an advanced mode rather than
appending another property.

**Default is semantic, not a number.** Selecting Default leaves `marker.size`
completely unmodified rather than writing the pixel count the chart happens to
use today. Two consequences: the generated appearance and any future template
change flow through untouched, and the layout default of a persisted control
never has to move — changing one silently discards every value the browser
already stored under that id.

**Automatic is the empty value.** An empty `point-color` means Automatic and the
field says so through its placeholder. Cleared dmc inputs send `""`, never
`None`, so the guard is truthiness, never `is not None`. Hex is the only
accepted format, which keeps alpha out of the feature; anything unparseable
falls back to the generated color rather than erroring.

**The eight swatches, and how they were chosen.** One hex value has to work on
both real plot backgrounds — `#ffffff` light and `#242424` dark — so the shade
was selected per family against both, rather than taking one Mantine shade index
across the board. All eight clear 3:1 on both:

| Family | Hex | Light | Dark |
|---|---|---:|---:|
| blue-7 | `#1c7ed6` | 4.20:1 | 3.70:1 |
| cyan-8 | `#0c8599` | 4.35:1 | 3.57:1 |
| teal-8 | `#099268` | 3.95:1 | 3.93:1 |
| green-9 | `#2b8a3e` | 4.37:1 | 3.55:1 |
| orange-9 | `#d9480f` | 4.30:1 | 3.61:1 |
| red-7 | `#f03e3e` | 3.84:1 | 4.04:1 |
| grape-6 | `#be4bdb` | 4.02:1 | 3.86:1 |
| pink-6 | `#e64980` | 3.73:1 | 4.16:1 |

`swatchesPerRow` is set to 8 explicitly; the component's own default is 7, which
would strand the eighth swatch on a row of its own.

**The exclusions are v1 curation under the current themes, not permanent bans.**
Yellow is out because no Mantine yellow shade reaches 3:1 on both backgrounds.
Lime is out because green already covers that family and only its deepest shade
passes, so it would add a weakly differentiated choice. Gray is out because it
collides with the grid lines. Dark is out because it disappears against the dark
plot. Re-audit all four if the chart backgrounds change. Contrast was only an
eligibility screen — small rendered points were checked in both themes before
shipping — and an arbitrary custom color carries no such guarantee, which is why
the graph updates immediately and **Use automatic** is an obvious,
keyboard-reachable way back.

**Appearance applies after theming, and never touches `generate_graph`.** Both
controls are Inputs to `apply_graph_appearance` (formerly
`apply_light_dark_theme_to_graph`), which deserializes `cached-plot`, applies the
light or dark template, and only then calls
`plot_service.apply_point_appearance`. The expensive callback that writes
`cached-plot` keeps its inputs unchanged, so changing a size or a color cannot
reread scenario data, rebuild overlays, or fire a notification. That split is
asserted against the callback registry, not just documented. The raw-run trace is
selected **by name** (`RUN_DATA_POINT_TRACE_NAME`), never by index: placeholder
figures, empty-state figures, figures without a run trace, and any future
reordering fall back untouched, and *Average Score*, the overlays, the axes, and
the hover labels are never restyled. Both graph modes are covered by
construction, and preferences survive scenario switches.

Alternatives rejected: **improving the default for everyone** — a larger
universal marker or a size that adapts to point count — because no universal
default satisfies personal color preference, and adaptive sizing makes the same
data look different as its point count grows; rendered evidence may still improve
the Automatic size later, but a better default is not a substitute for
personalization. **Palette-only** (governable but weakens personalization) and
**picker-only** (flexible but makes everyone solve color selection from scratch
and hides the safe choices). **Five presets or a continuous slider**, which
elevate rendering precision into a product concept and make the default harder to
recognize and restore. **Ten swatches**, adding indigo-5 (`#5c7cfa`) and violet-5
(`#845ef7`): finer blue-to-purple choice at the cost of two more neighboring
options the picker already covers. **The 14-color DMC example list**, which is a
component demonstration rather than a palette curated for these backgrounds, and
several of whose values fail the contrast target.

Out of scope and staying there: opacity, marker symbols, borders and outlines,
Average Score line styling, rank/PB/threshold overlay styling, axes, grid lines,
fonts, plot backgrounds, hover-label styling, per-scenario or per-playlist
appearance profiles, import/export of appearance preferences, and any generic
Plotly-property editor.

Design in [#238](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/238),
implementation in [#241](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/241).
The panel this group joined is the
[2026-08-09 chart options entry](#2026-08-09-chart-options-live-in-a-collapsible-panel-beside-the-graph).
The Automatic wording, the generated color, and the empty field's white
preview swatch were revised the next day; see the
[2026-08-21 entry](#2026-08-21-the-empty-point-color-is-called-default-and-the-points-follow-the-theme).

## 2026-08-14: The Listen Address Is Configurable, Loopback By Default

Status: Accepted

The app now reads a `host` setting from `config.toml`, and still serves this
machine only unless that setting says otherwise. Setting it to `0.0.0.0` lets
other devices on the same network open the dashboard, which is the only way to
reach it from a phone or a second PC. The app has no login, so every device
that can reach the chosen address can read the run data and change the
settings. An install that does not set `host` behaves exactly as it did
before.

Decision: `ConfigData` gains `host: str = "127.0.0.1"`, and both server paths
honor it — `bind_server_socket(port, host)` for the waitress path, and the
`config.debug` Flask path via `app.run(host=config.host, ...)`. On the default
host the bind is byte-for-byte the previous behavior: both loopback faces,
`SO_EXCLUSIVEADDRUSE`, two-bucket failure semantics. A non-default host is
bound **alone**, with no `::1` companion.

**`host` must be an IP literal**, never a name; the address family is taken
from the literal, so `::` binds as IPv6 rather than failing as a malformed
IPv4 address. Resolution is what makes a name dangerous here: it picks one
face of whatever it resolves to, so `localhost` would bind `::1` alone on
this machine and `127.0.0.1` alone where the resolver orders IPv4 first,
holding one loopback face and leaving the other free to squat — the very
ambiguity the default's dual-face bind exists to close, reintroduced through
the most natural spelling of "same as the default". The empty string is the
same trap in different clothing: `getaddrinfo("", ...)` yields `AF_INET6`, so
`host = ""` — the natural way to hand-write "unset" — would publish the app
on `::`, every IPv6 interface included, with none of the warnings that gate an
explicit `0.0.0.0`. Both exit naming the setting. This costs nothing the
documentation promised: `README.md`, `example.toml`, and this entry all
specify literals.

Why loopback remains the default: there is no authentication anywhere in the
app. Settings are writable from the UI, so a reachable instance is not
read-only exposure. Defaulting to the LAN would hand that to every device on
whatever network the machine joins next, including untrusted ones.

Why a non-default host is bound alone: the `::1` companion in the
[2026-07-19 exclusive-bind entry](#2026-07-19-the-app-binds-its-port-exclusively-and-exits-if-it-is-taken)
and its 2026-07-20 addendum exists to stop `localhost` resolving to a face the
app does not hold. A user naming one address outright has no such ambiguity to
close, and binding a speculative second address is not something a config
value should do silently.

Verified consequence of `0.0.0.0`: nothing answers on `::1`, so a client that
insists on IPv6 loopback is refused; `localhost` and `127.0.0.1` both connect,
because resolvers and browsers fall back to the IPv4 address.

**The launcher derives its addresses from `host`.** A fixed `127.0.0.1` probe
would have made a single-address bind unlaunchable from the installed
shortcut: no listener on `127.0.0.1` means `Wait-AppReady` times out and kills
a perfectly healthy server. `scripts/launcher.ps1` therefore reads `host`
alongside `port` — through the same "ask the app's own loader" contract, so
there is still no second TOML parser — and maps it to two destinations. The
`/health` probe stays resolver-free per the
[2026-08-09 entry](#2026-08-09-human-facing-urls-say-localhost-machine-probes-stay-on-127001):
`0.0.0.0` probes `127.0.0.1`, `::` probes `[::1]` (Windows sets
`IPV6_V6ONLY`, so the IPv6 wildcard serves no IPv4 face), and any other host
is probed at the literal address it names. The browser URL says `localhost`
only on the **default** host, where the app holds both loopback faces and
whichever one the resolver picks is therefore ours. Under any other host the
app owns at most one face and an unrelated process can hold the other:
verified on Windows, an app bound to `0.0.0.0` alongside a stranger holding
`::1` sends `localhost` to the stranger, after the launcher's own IPv4 health
check has already passed. Every non-default host therefore opens at the same
literal address the readiness probe proved reachable. IPv6 literals are
bracketed for both.

Failure taxonomy — two buckets, not three. A host that is not an IP literal is
rejected before any bind, naming the setting. A well-formed literal that no
local interface holds — a mistyped LAN address, or one lost to a DHCP change —
fails the bind with `EADDRNOTAVAIL`, and that reports the **host**, not the
port: no port is free on an address this machine does not have, so the
port-taken message would send the user after the wrong setting.

Relationship to prior entries: nothing is superseded. The exclusive-bind
decision stands unchanged — the app still creates and binds its own sockets,
still sets `SO_EXCLUSIVEADDRUSE`, and still exits rather than half-serving a
port. What changes is only which address it claims. The
[2026-08-09 human-facing-URL entry](#2026-08-09-human-facing-urls-say-localhost-machine-probes-stay-on-127001)
reasoning that "whichever face the resolver hands `localhost` is ours" is
narrowed to the default host, and holds there.

`debug` and `host` interact, and nothing enforces it. Flask sets
`use_debugger` from `debug` and Dash forwards `host` straight through, so
`debug = true` with a non-default host puts the PIN-gated Werkzeug console on
that network — an execution surface, not just the read-and-change-settings
ceiling the rest of this entry reasons about. The combination warns at startup
and is called out beside `debug` in `example.toml`, but is not refused:
`debug` is documented dev-only and both are the operator's own settings.
Refusing it outright stays available if that judgment turns out wrong.

Out of scope: authentication, TLS, and any in-app affordance for turning LAN
access on. On Windows a bind is also not sufficient by itself — an inbound
firewall rule is required, which is the operator's business and is documented
in `README.md` rather than automated.

## 2026-08-11: Durable JSON Stores Carry A schema_version Stamp

Status: Accepted

Every JSON file the app writes under `data/` now starts with
`"schema_version": 1`. The point is future data migrations: before the app has
users outside two machines, it needs a way to tell the format it understands
from one it does not. A file the app cannot use is never deleted or rewritten
behind the user's back. It is left exactly as it is, the app falls back to its
first-run defaults, and the page that owns the setting says what happened and
how to fix it. A file written by a *newer* version of the app is recognized as
newer: the app reads nothing from it, refuses every write to it, and says the
data is intact and an update will restore it. Existing installs are converted
once by a script that ships with the release; the app itself has no migration
code.

Decision: settled with the maintainer on 2026-08-10 and 2026-08-11, after a
review round on the contract. The premise is the public launch. `data/` is the
app's database in lieu of SQLite, and a format change with no version marker is
indistinguishable from corruption.

**Scope.** `data/settings.json`, `data/playlist_visibility.json`, and every
user playlist under `data/playlists/`. The bundled corpus in
`resources/benchmarks/` is exempt: it ships with the code that reads it and is
governed by its own `generated_from.schema_version` provenance contract, so its
format can never be older or newer than the build. Cache files under
`data/cache/` get no stamp and no cache-schema rule; that is deferred to a
need-time proposal. The tolerance invariant for caches (missing, stale,
malformed, partially-written files must all be survivable) is unchanged and
still stated in `AGENTS.md`; only the versioning and invalidation *mechanism*
is deferred, and the known tolerance violations in `api_service.py` are tracked
separately.

**The marker.** Top-level `"schema_version"`, an integer. Validation is strict:
`type(value) is int` — so a JSON `true`, which `isinstance` would accept as an
`int`, is rejected — and exact membership in the supported set (today `{1}`).

**No grandfather rule.** An existing well-formed file *without* a stamp is an
error state, not implicit v1. Two machines is a cheap population to convert
once, and the alternative is a missing-means-v1 special case that every future
reader carries forever.

**Four read states, per store**, implemented once in
`source/utilities/store_schema.py`:

1. *Missing* — first-run defaults (settings unset, visibility seed, empty
   user-playlist set). Unchanged from before the stamp existed.
2. *Error* — unreadable, not JSON, not an object, no stamp, a malformed or
   **non-positive** stamp (`0` and negatives are garbage, not the future: a
   file that read as future would refuse every write and strand the store), or
   a supported stamp whose payload fails that version's definition. The bytes
   are preserved, the store reads as its first-run default, and an actionable
   message is reported. A stamp routes a payload to a validator; it never
   vouches for the payload.
3. *Supported* — a known stamp with a payload that validates.
4. *Future* — a stamp above the highest supported version. Nothing is read, and
   every write is refused.

The error and future states surface in the UI, not only in the log: an inline
alert on the settings page (an unusable store otherwise renders as an ordinary
empty form, exactly like a first run) and an alert on the Playlists page for
visibility (whose fallback is the seed, which looks exactly like a fresh
install). Unusable playlist files are skipped with the existing startup warning
queue. Without those surfaces the migration window reads as unexplained data
loss instead of loud but inert.

**Write rules.** Automatic writers never touch a store they cannot use:
`bootstrap_stats_dir` declines out loud in the error and future states, because
those read as "no keys" and writing would erase an identity the user really
configured. User-initiated saves *own* an error-state file, so self-service
recovery from a bad hand edit stays possible: the incumbent is copied
byte-for-byte to an adjacent `<name>.corrupt-<n>.bak` (exclusive create, so a
backup never replaces an earlier backup; a copy, never a move, so a write that
never lands leaves the original at its path), and only then is the file
replaced. If the copy cannot be made, the write is refused. Reads never mutate.
Future-state files raise `UnsupportedSchemaError`, which every caller reports in
its own register: a settings-page status distinct from the I/O-failure one (the
remedy is updating, not retrying), a toast on direct hide/unhide, the existing
partial-success branches for import and delete, and a log line at startup.

**Import collision guard.** A rejected playlist file is absent from
`playlist_database`, so the import's duplicate-code check cannot see it, and
two different name/code pairs can sanitize onto one filename anyway — the
filename is not authoritative and "not loaded" must never be inferred from the
code. So immediately before its atomic replace, the import classifies whatever
already occupies the destination, through the same decoder the loader uses: a
future incumbent refuses the import, an unusable one is copied aside and
replaced, and a healthy v1 incumbent refuses the path collision. That last case
also fixes a live overwrite bug at the time of writing. This could not be
deferred to the release that first breaks the playlist schema, because the
vulnerable writer is *this* release's import path running after a rollback, and
a future PR cannot retrofit already-installed code. The shadow case — the same
code imported under a different filename, so no path collision — is accepted as
non-destructive: nothing is overwritten, and the loader's duplicate warning
surfaces it on the next start.

**v1 payload definitions**, implemented once and imported by both the runtime
readers and the conversion script. Settings v1 is a flat object whose keys are
a subset of {`stats_dir`, `kovaaks_username`, `steam_id`} with string values;
missing still means unset, and **unknown keys are invalid**, because within a
version the key set is fixed (rejecting preserve-unknown-keys below means any
future key addition bumps the version anyway, so a stray key under stamp 1 is a
typo worth surfacing). Settings is read `utf-8-sig`: a Windows-editor BOM is
valid legacy data for the documented hand-edit escape hatch. Visibility v1 is
exactly {`shown_playlists`: list of strings}, unknown keys invalid. Playlist v1
is `PlaylistData` unchanged, extra fields still ignored — these are
machine-written envelopes, not hand-edit surfaces. Visibility and playlist
files are plain UTF-8, where a BOM is invalid.

**Migration.** `scripts/stamp_schema_version.py` converts the existing
population once. Its state machine is narrow: unstamped with a valid v1 payload
gets the stamp; stamp 1 with a valid payload is a no-op (so re-runs are safe);
anything else is preserved and reported. A file carrying a *different* stamp is
never rewritten even when its payload happens to satisfy v1 — pydantic ignores
extra fields, so a looser rule would let a run years from now silently
downgrade a file from a much later release. The ordering contract is: back up
`data/`, update the app, **close it**, run the script once, relaunch. The app
must be closed because its in-process caches race the rewrites, and it must
already be updated because a stamped `settings.json` is rejected outright by
the pre-stamp reader, which then reads every setting as unset and lets
`bootstrap_stats_dir` overwrite the file with a bare `{"stats_dir": ...}`,
destroying the stored identity. Between update and script the app boots loud
but inert. **Compatibility floor:** once stamped files exist, pre-stamp
releases are unsafe rollback targets, by that same bootstrap-wipe mechanism.

The script resolves the *state root* itself rather than reading the module
constants the services bind at import, because on an installed copy those bind
to the wrong tree: the launcher exports `CSD_STATE_DIR` only around the app
process, so a manual command inherits nothing, and the code lives in
`versions/<tag>/` while the durable state lives at the install root. Resolution
order is `--state-dir`, then `CSD_STATE_DIR`, then the install root inferred
from the script's own location, then the working directory; the chosen root and
the rule that chose it are printed before any file is touched. The inference
demands install-only evidence, not just the `versions/<tag>/scripts` shape: the
candidate root must also hold the installer's `install.json`. Shape alone would
classify a checkout that happens to sit under a directory named `versions` as
an install and convert its parent, which is the silent wrong-tree write this
resolution exists to prevent; without the evidence the inference stays out and
the working directory wins, which is what a source checkout wants anyway. The installed command runs the release's
own `versions/<tag>/.venv/Scripts/python.exe` by absolute path, because a
standard install deliberately puts neither uv nor Python on `PATH` (see the
script's docstring for the exact snippet).

Note for the first release that actually *migrates* data: the launcher's staged
trial run executes load-time migrations before `/health` is consulted, so that
PR has to consider the trial window — for example by migrating only after
promotion.

Rejected: a string marker (an integer sorts and compares without a parser); a
missing-means-v1 grandfather rule (see above); a single global
`data/schema_version` sidecar (the three stores version independently, and a
sidecar can desynchronize from the files it describes); rewriting files to
preserve unknown keys (it converts a typo into permanent silent state); tolerating
unknown keys within a version for settings and visibility (playlists keep
`PlaylistData`'s ignore-extras deliberately, for the reason above); best-effort
reads of future files (guessing at a format the build does not know is how
data gets corrupted rather than preserved); move-instead-of-copy backups (a
failed write would leave nothing at the file's own path); deferring the import
guard to the v2 release (the vulnerable writer is this release's own import
path); and a reservation registry for import destinations (a second source of
truth that can drift from the filesystem, where the destination point-check
asks the only authority there is).

Supersedes, on these narrow points only: the 2026-08-02 settings entry's "no
`schema_version`" sentence, and the 2026-07-19 update-contract entry's position
that the durable state is schema-stable enough for a format break to be handled
by a manual step called out in its PR.

## 2026-08-11: A Fresh Install Is Asked Once, On A Card Keyed To Key Absence

Status: Accepted

A fresh install now says what it could not set up on its own. The landing page
carries a small card that either reports that no KovaaK's stats folder was
found, or offers the leaderboard features that would otherwise stay invisible.
The account offer can be skipped, which turns rank lookups off and takes the
card away for good. An install that is already configured never sees it, and
nothing about it blocks the app.

Decision: five parts, settled with the maintainer in the 2026-08-11 design
session and shipped from `docs/initial_setup_proposal.md` (proposed in PR
#231).

**A card on the landing page, and nothing heavier.** One card with one primary
action, on `/` (Scenario Performance) and only there; if a dedicated Home page
ever ships, the card moves with it. It is navigation and dismissal only: it
links to `/settings`, where detection and Save already live, so it never grows
a second detection UI and never touches the network — opening a page still
costs no KovaaK's request. It renders from the stored view (`get_settings()`),
the view the settings page renders from, never the process-pinned accessors,
because what it speaks about is what is on disk. Copy is fixed and part of the
decision: State A is "Add your KovaaK's account" over "See your leaderboard
position and percentiles for every scenario.", with "Open Settings", "Skip",
and the fine print "Skipping username disables rank lookups. You can set it
anytime in Settings."; State B is "Finish setting up" (D1) over "No KovaaK's
stats folder was found, so the dashboard can't read your runs yet. Set it in
Settings." State B names the action rather than the failure, which the body
already carries.

**Triggers are key absence, per item.** The card is the *never asked* surface:
each state shows only while its `settings.json` key is absent, and a key that
exists — with any value, `""` included — retires that item permanently. An
absent `stats_dir` gives State B, which offers no Skip (without run data the
app has nothing to plot) and wins whenever both keys are absent; a present
`stats_dir` with an absent `kovaaks_username` gives State A. Degraded settings
that do exist — a deliberate `""`, a stored path that has since vanished —
stay with the point-of-impact hints, so `home._stats_dir_hint()`'s
unconfigured branch narrowed to a key that is *present* and unusable. One
condition, one surface, instead of two lines saying it at once. Mixed presence
(`stats_dir: ""` beside an absent username key) is unreachable through the
app, because every Save writes all three keys; under a hand-edited file the
card and the hint each still state something true.

**The card stands aside for a pending restart.** While
`is_stats_dir_change_pending()` holds, nothing renders: the user is mid-setup,
the existing "Restart the app to apply your saved settings." hint owns
that moment, and stacking the identity ask on top would be two banners for one
unfinished action. The card returns after the restart if identity is still
unasked. It never claims completion; restart honesty stays with the settings
page's save statuses and notice.

**Skip is a locked identity decline, and it narrows the single-writer
decision.** `settings_service.decline_identity()` re-reads the stored mapping
and writes it back with only `kovaaks_username` set to `""` — the shipped
empty-means-off value — entirely inside the module `RLock` every read and
`save_settings` already take. That makes "alters no other key" an invariant of
the operation rather than a read-merge-write in a page callback: the card was
rendered at some earlier moment, and a review of PR #231 reproduced the race
where that stale snapshot restores an old `stats_dir` or `steam_id` over
values saved since. `save_settings` keeps its replace-all contract and its
pinning test untouched. That staleness cuts one more way, so the operation is
a no-op whenever the username key already exists: a card rendered in one tab
and clicked after another tab saved a real username would otherwise erase it,
and a refusal to answer is never grounds for discarding an answer somebody
gave (found in PR #236's review). This deliberately narrows the single-runtime-writer
clause of the 2026-08-03
["Settings Detection Suggests, And Identity Is Offered Only Once Verified"](#2026-08-03-settings-detection-suggests-and-identity-is-offered-only-once-verified)
entry rather than contradicting it: Save remains the only runtime writer of
*values*, and the decline can only ever record "asked and declined" — never
something a user typed. `pages/settings.py`'s module docstring carries the
same exception. The decline is surgical for a reason beyond the race: an
absent `stats_dir` stays absent, so the startup bootstrap keeps looking for
one on later boots. Nothing else follows from the click — no warmup worker
starts (there is no username to warm anything for), and nothing pins, because
the identity pin freezes only on a read that sees a configured username, so no
restart notice appears either. Recovery from a decline is the settings page
plus the point-of-impact hints; the card itself never returns. The callback
guards on `n_clicks` and `ctx.triggered_id` against the DashProxy
initial-call hazard (see the 2026-08-02
["A Committed Side Effect Reports Its Outcome Even When A Later Write Fails"](#2026-08-02-a-committed-side-effect-reports-its-outcome-even-when-a-later-write-fails)
entry's hazard note), which matters here because this callback writes to disk.

**New user-facing copy avoids em dashes.** A rule that emerged with this arc
and now lives in AGENTS.md's styling conventions: copy the app shows a user
reads as machine-written with them, so new copy uses short sentences instead.
Sweeping the shipped copy is explicitly deferred to a future review of all app
messaging; the temporary inconsistency between old and new lines is accepted
rather than fixed piecemeal.

**Rejected alternatives.** A blocking first-run wizard: heavier than a problem
whose setup is one Detect click plus Save, and modals are unverifiable in the
automated browser pane. A per-setting row checklist: scales poorly if settings
grow. A dedicated dismissed-flag key: persists a distinction no consumer reads
— runtime already treats `""` and absent identically everywhere — and grows
the flat schema with UI state. Session-only dismissal: reappears every boot,
which is nagging.

Provenance: distilled from `docs/initial_setup_proposal.md` (proposed in PR
#231), shipped in PRs #235 (the companion playlists-overview status line,
which gives the overview grid the same unset-username explanation the
drill-down page already had) and #236 (the card); the proposal file is deleted
in the shipping PR and git history holds its full text.

## 2026-08-10: Bug Reports Land On GitHub Issues, With The Log Attached Unredacted And Disclosed

Status: Accepted

The app now has one place for feedback and bug reports: GitHub Issues, with a
bug form and a feature form and no blank-issue option. The bug form asks for
the app version and requires a log file, because a failure on a machine no one
else can see is otherwise undiagnosable. The log is attached exactly as the
app wrote it — including the reporter's KovaaK's username and Steam ID — and
the form says so plainly before the upload box, because the issue and its
attachments are public. The Settings page pre-fills the version into the form
and shows where the log lives, so filing a report is a click rather than a
scavenger hunt.

Decision: three parts, all settled on the
[feedback intake proposal](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/226)
and shipped in PRs #228 and #229.

**Disclose, do not redact (D1).** `debug.log` is attached as written. A
KovaaK's player's username and SteamID64 are already stamped on every
leaderboard score they set unless they opt out of leaderboards entirely, and
both values are what diagnoses the likeliest bug class — rank lookups and
benchmark row matching that fail on *which account* they resolved. An audit of
real logs on 2026-08-09 (the maintainer's production installs, Aug 5–9, plus a
4.3 MB dev corpus back to June 24) established the boundary this rests on:
Steam personas never reach the log at all (the identity probe's by-username
calls log as `<redacted>` via the `sensitive` flag in
`api_service._get_with_retry`, and `config/identity_detection.py` logs counts
and positions only); the startup config dump is benign under the current
schema; and no credentials exist anywhere in the app to leak. What *is* in the
log and is accepted here: the KovaaK's username in per-attempt request params
and in failure lines that embed the full URL, the SteamID64 that
`get_benchmark_json` passes unredacted (latent — not witnessed in any log
yet, and knowingly left that way by this decision), Windows usernames inside
absolute paths under `%LOCALAPPDATA%`, and the scores, sensitivities, and
timestamps the app exists to record. Nothing about what the app logs changes;
the escape hatch is that the log is plain text the reporter can read first.

Disclosure must name the audience, not only the contents. The form's copy
states that the issue and its attachments are public to anyone on the
internet, GitHub account or not, and invites reading the log before uploading.
Those two are required content, not style. The alternative — redaction
machinery across several unredacted failure-logging sites plus the benchmark
request params — buys privacy the leaderboard already gave away and costs the
values that identify the root cause.

**Issues and forms only (D2).** Blank issues are disabled in favor of
`bug_report.yml` and `feature_request.yml`; there is no Discord server and no
GitHub Discussions. Labels: `bug`, `enhancement`, `question`, `needs-info`,
and `upstream` for KovaaK's-side breakage the app can only work around.
Feedback arriving anywhere else is transcribed into an issue by the maintainer
as the canonical record (`gh issue create` is unaffected by the blank-issue
setting). This knowingly accepts an exclusion: users without a GitHub account
— likely a real share of a gamer audience — have no direct submission path.
**Revisit trigger:** launch feedback showing reports dying for want of an
account. Rejected for now: a second moderated inbox (Discord) or a second
triage surface (Discussions) for a single maintainer, ahead of any
demonstrated volume; and email, for its spam surface and lack of public dedupe
or history. Crash telemetry (Sentry or similar) is rejected outright as
privacy-hostile for a local tool.

**The Settings-page affordance (D3).** Under the version block,
`pages/settings.py` renders a "Report a bug" anchor whose href is
`bug_report_url(release_label)` — `…/issues/new?template=bug_report.yml&version=<label>`,
built with `urlencode`. Two contracts with
`.github/ISSUE_TEMPLATE/bug_report.yml` live in that URL: the template
*filename*, and the `version` field *id* that GitHub pre-fills by name. The
label is encoded rather than pasted because a release tag arrives from JSON
the app did not write. Every label the resolver produces is pre-filled —
`dev` and `unknown` included — since the field is required and editable, so a
placeholder beats an empty box. Beside it the resolved log directory is shown,
so "attach `debug.log`" names a place to look. `data/logs` moved into
`utilities/paths.log_dir()` for this, consumed by both `app.py` and the page:
pages cannot import `app`, and the literal should exist once.

## 2026-08-09: An Unset Username Is Stated In Place, Never Reported As A Failure

Status: Accepted, except that the per-click-id mechanism described below is
superseded by the 2026-08-31
["Repeatable Toasts Replace In Place With A Visible Re-Entry"](#2026-08-31-repeatable-toasts-replace-in-place-with-a-visible-re-entry)
entry: the blue notice is now a single-identity channel that re-pops by showing
a fresh instance id. The ruling — an unset username is configuration state
answered blue, never a red failure — is untouched. The
configured-but-wrong-username case the Scope note below defers is now half
settled by the 2026-08-22
["The Playlist Fill Reports Degradation In Place Only"](#2026-08-22-the-playlist-fill-reports-degradation-in-place-only)
entry, which deleted the playlist fill's aggregate toast — and with it
`_fill_summary_notification`, described below as untouched. Only the Refresh
half of "both generic red toasts" still fires. Everything else here stands.

With no KovaaK's username configured, opening a playlist used to run a
position update that fetched nothing and then popped a red "Position update
incomplete — couldn't update 16 of 16 positions", and clicking Refresh on the
Scenario Performance page answered with a red "Position refresh failed".
Nothing had failed: without a username the app never contacts KovaaK's at all.
The playlist page now skips that pointless update and says "Positions
unavailable — set your KovaaK's username in Settings" in its own status line,
and Refresh answers with a blue notice naming the missing username. Red again
means a lookup that really failed.

Decision: both position surfaces gate on the configured username before doing
any work, and report the unset case as the persistent configuration state it
is.

- `load_playlist_scenario_rows` (`source/pages/playlist_scenarios.py`) checks
  `get_kovaaks_username()` after the playlist resolves and before
  `start_playlist_scenario_fill`. When it is empty the phase-1 rows are
  returned with every pending flag cleared, a `None` generation token, the
  drain interval disabled, and the status line carrying the copy above with
  "Settings" as a `dmc.Anchor` — the same link the Position field's hint uses.
  `_fill_summary_notification` is untouched: the toast cannot fire because the
  fill it summarizes never runs.
- `refresh_rank` (`source/pages/home.py`) checks the same read after its
  `n_clicks` and selected-scenario guards, and returns `no_update` for the
  value plus one blue toast titled "KovaaK's username not set". The value is
  left alone because the field already reads "N/A — set your KovaaK's username
  in Settings".

Why in place on the playlist page and a toast on Refresh: the
[2026-08-03 routing policy](#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)
sends persistent conditions to in-place UI, and the playlist grid has such a
home. Refresh collides with the same policy's user-initiated branch, and that
branch wins for this event: the in-place hint was already on screen before the
click, so it cannot produce any perceptible response to the click itself, and
a user who clicks Refresh beside the hint plausibly clicked because they had
not read it. To keep every click answerable the toast carries a fresh
per-click id, the same mechanism the green confirmation uses — a stable id
would be swallowed by DMC's `show` while the previous toast is still up.
*(Superseded 2026-08-31: the toast is a channel whose fresh instance id per
emission does the same job, and hides the instance it replaces so repeats do not
stack.)* Blue, not yellow: yellow means degraded data (stale serve, threshold miss, Steam
mismatch), and nothing here is degraded.

Why skipping the fill is safe without a compensating cancel call: skipping
`start_playlist_scenario_fill` also skips its `_cancel_live_fills_locked` side
effect. Identity is process-pinned in one direction only — reads stay live
until the first non-empty username is observed, then freeze — so a tripped
gate means the username has been empty for the whole process, every earlier
playlist open tripped it too, and no live fill can exist.

Why the gate reads settings directly: string-matching the service's
`error_message` would couple routing to display copy, and a typed reason field
on `ScenarioRankInfo` cannot serve a pre-flight gate that must skip the fill
before any lookup runs. Only two sites consume the condition.

Scope: this entry rules on the **unset**-username case only. A username that
is configured but wrong is a different mechanism — it is knowable only per
result, after a network round-trip — and still produces both generic red
toasts today. That case is deliberately deferred and remains open; a typed
reason on `ScenarioRankInfo` is where it should be reconsidered.

Consequences: nothing is superseded. This discharges the kernel the
[2026-08-01 fully-offline entry](#2026-08-01-no-username-stays-fully-offline--user-independent-totals-rejected)
deferred until a settings page existed to point at — quiet state instead of a
red error, no futile fill, and a pointer to how to turn the features on.
Position cells still render N/A throughout: the service's guard fires before
any cache read, so no cached position can contradict the status line.

Provenance: distilled from `docs/unset_username_position_feedback_proposal.md`
(four decisions ratified 2026-08-09), committed and then deleted in the
shipping PR — git history holds the full text.

## 2026-08-09: Human-Facing URLs Say localhost, Machine Probes Stay On 127.0.0.1

Status: Accepted

The launcher used to open the browser at `http://127.0.0.1:<port>/` while the
README and the development run said `http://localhost:<port>/`. Those are two
different browser origins, so the dashboard opened from the desktop shortcut
and the same install reached by typing `localhost` kept two separate sets of
saved UI preferences. Every URL a person sees or clicks now says `localhost`.
The launcher's internal health check still uses `127.0.0.1`, because a
machine-to-machine check should not depend on how the machine resolves names.

Decision: Human-facing URLs — the browser the launcher opens
(`scripts/launcher.ps1`, `Open-Dashboard`), the "Dashboard running at ..."
line it prints, and the URLs in `README.md` and `docs/` — use
`http://localhost:<port>/`. Machine-to-machine URLs stay on the literal
`127.0.0.1`: the launcher's `/health` readiness probe in `Wait-AppReady` is
deliberately resolver-free, and is not to be swept into consistency with the
human surfaces. `source/app.py` is untouched — its bind logic and port-taken
error text are about which addresses the server claims, not about which name
the browser is handed.

Why: the app persists UI state in `window.localStorage`, which is keyed by
origin — the Mantine color scheme written by the head script in
`source/app_shell.py`, the navbar Burger's `persistence_type="local"`, and the
chart-option switches in `source/pages/home.py` (Dash persistence defaults to
local storage). `localhost:<port>` and `127.0.0.1:<port>` are distinct
origins, so the two entry points to one install were accumulating disjoint
toggle state. Unifying on the name the docs and the development run already
use collapses that to one origin.

Why this is safe despite the shadowing history: the
[2026-07-19 exclusive-bind entry](#2026-07-19-the-app-binds-its-port-exclusively-and-exits-if-it-is-taken)
and its 2026-07-20 addendum bind **both** loopback faces (`127.0.0.1` and
`::1`) with `SO_EXCLUSIVEADDRUSE`, and the addendum's failure semantics are
two-bucket: a port free on only one face is refused outright rather than
half-served. So a half-bound instance cannot exist, and while the app is
serving, whichever face the resolver hands `localhost` is ours — the old
"browser gets a stranger's 404" failure needed an IPv6 face we did not hold.
The launcher's start and update paths open the browser only after
`Wait-AppReady` succeeds, and the already-running path opens it at an instance
that passed its own launcher's probe — so that one IPv4 probe vouches for both
faces. On a machine with no IPv6 the app serves IPv4 alone and `localhost`
resolves to IPv4 anyway.

Consequences: Nothing is superseded; the bind decision stands unchanged. The
maintainer's existing install has persisted toggles under the `127.0.0.1`
origin, which appear reset once after this change and are re-set by hand — per
the single-user policy, no migration code. Future URL surfaces pick a side by
audience: shown to a person, `localhost`; consumed by a script, `127.0.0.1`.

## 2026-08-09: PB Columns Keep Their N/A Sentinel Even For Timestamps

Status: Accepted

The playlist table gained a PB Date column showing when the personal best
was achieved. On a scenario with no local runs it renders "N/A" like the
other PB columns beside it, rather than the grid's "Never" sentinel, so an
unplayed row shows both words at once. This was chosen deliberately: each
word keeps one meaning, and the row's PB cells stay consistent with each
other.

Decision: A grid column whose value is a stat of the personal-best run
takes "N/A" as its null sentinel, even when the value is a timestamp
rendered with the shared relative-time helpers. "Never" stays scoped to
Last Played (in a playlist but never played). On an unplayed row, Last
Played reads "Never" while PB Score / PB Date / PB cm/360 / PB Accuracy
read "N/A"; the sentinels co-occur by design. Last Played and PB Date are
null under exactly the same condition — the scenario has no local runs —
so an unplayed row is the only place "Never" and "N/A" describe the same
fact. (PB cm/360 additionally reads "N/A" on played rows whose PB used a
different sensitivity scale; "N/A" in a PB column is not by itself
evidence the scenario is unplayed.) The playlist grid's live tick now
refreshes both timestamp columns:
`refreshCells({force: true, columns: ["last_played_sort",
"pb_timestamp_sort"]})`.

Why: "Never" answers "have I played this?"; "N/A" marks a stat that does
not exist because there is nothing to measure, and a missing PB is the
second kind. Column-family consistency (a row's PB cells agreeing with
each other) was judged to beat renderer consistency (every relative-time
cell sharing one sentinel). Maintainer-ratified copy call.

Consequences: Shipped in PR #216. Narrows the sentinel rule and extends
the single-column `refreshCells` call of the
[2026-06-21 relative timestamp entry](#2026-06-21-relative-humanized-last-played-timestamps),
whose Status line points here. Future timestamp columns choose their null
sentinel by column family, not by renderer.

## 2026-08-09: Chart Options Live In A Collapsible Panel Beside The Graph

Status: Accepted

The graph's display preferences used to open in a modal that dimmed the page
and blocked the chart behind it, so tuning an overlay meant adjusting, closing,
looking, and opening again. They now sit in a panel that slides out beside the
chart, which stays live and readable the whole time. On a narrow window the
same panel stacks above the chart instead. No preference changed what it does,
what it defaults to, or where it is stored.

Decision: `settings-modal`, `settings-modal-open-button`, and the `modal_demo`
callback are deleted. Their five chart preferences move into an in-flow
`chart-options-panel` beside `graph-content`, disclosed by a
`chart-options-toggle` button labelled "Chart options" and grouped under
*Overlays* and *Score Threshold* headings. `automatically-change-scenario-switch`
governs selection rather than presentation — it is the one moved control that is
not an input to `generate_graph` — so it is promoted out of the panel to sit
under the scenario selector. The panel starts closed on every visit and its open
state is not persisted.

Why: the container was adjudicated on a live-size interactive mockup built from
measured app geometry (1600×900, real element positions), not from taste. Open
plot area came out near-identical either way — stacked above the chart
1318×477 ≈ 629k px², beside it 1002×639 ≈ 640k px² — so the call fell to shape,
growth, and ergonomics, and all three favour the side panel: 1.57:1 stays
visually balanced where 2.76:1 reads wide and shallow, a vertical column absorbs
future controls without shrinking the chart further, and the panel can stay open
through sustained tuning. `dmc.Drawer` (a fixed overlay over the graph) and
`AppShellAside` (global chrome on every page) were rejected for the modal's own
reason: the graph is the only feedback surface these controls have. Folding them
into `/settings` was rejected earlier still — disjoint content, instant-apply
against deliberate-Save commit models, and no chart there to give feedback.

Consequences and constraints:

- **The flex role transfers; it is not duplicated.** `.home-chart-area` is now
  the direct flex child of `.home-page` and carries the `flex: 1 1 0` growth and
  the `min-height` floor that `.home-graph` used to hold. Leave those on the
  graph and the row falls back to intrinsic content height, so the graph stops
  consuming the remaining viewport.
- **`.home-graph` is a resize hook, not decoration.**
  `assets/homeGraphResize.js` locates graph containers by that class, and
  opening or collapsing the panel is exactly the
  container-resize-without-window-resize case Plotly does not redraw for on its
  own. The class and the script survive any future refactor of this row.
- **The reflow threshold is a container query, never a media query.**
  `@container home-chart-area (max-width: 62em)` measures the chart row's own
  box. The fixed 250px navbar shrinks the content area without touching the
  viewport, so a viewport threshold would keep the panel beside a chart it had
  already crushed — the same trap as
  [2026-08-03](#2026-08-03-homes-controls-row-measures-the-content-area-not-the-window).
  62em is Mantine's `md` step, off the scale the controls grid already uses. A
  container query cannot match on the element that declares the container, so
  `.home-chart-area` declares it and `.home-chart-row` carries the layout.
- **Collapsing animates the track, and the row clips.** The inspector's grid
  track transitions between `0` and 20rem at `dmc.AppShell`'s own 200 ms rather
  than being removed, so the graph grows and shrinks the way it does when the
  navbar collapses. Two facts make that work: the panel holds its own width
  while the track moves under it, so it is revealed rather than squeezed; and
  `.home-chart-row` clips, because Plotly redraws exactly once ~200 ms *after*
  its container stops moving and until then is still drawn at its old width.
  The navbar hides that overhang by being fixed-position and painting over it;
  an in-flow panel has to clip from the other side. Stacked, there is no width
  to animate, so that mode sets the duration to zero.
- **Ids and defaults survive verbatim.** Dash persistence is keyed by component
  id, and changing a layout default silently drops every stored value, so all
  six preference inputs kept both across the move. Collapsed controls hide with
  `display: none` — mounted, in the layout tree, still feeding their callbacks —
  and are never conditionally rendered.
- **The toggle's `n_clicks` guard is unconditional.** Under DashProxy a
  callback can fire on initial page load despite `prevent_initial_call=True`,
  which here would spring the panel open on arrival. The panel's class *is* the
  open state and `aria-expanded` rides with it, so a regression test pins that
  both are unchanged before a real click.

Shipped in PRs #209 and #215; design discussion in #206. This entry and
[the naming entry](#2026-08-09-the-graph-page-is-scenario-performance-its-panel-is-chart-options)
distil `docs/chart_options_inspector_proposal.md`, now deleted.

## 2026-08-09: The Graph Page Is Scenario Performance, Its Panel Is Chart Options

Status: Accepted

Three surfaces used to answer to the name "Settings", two of them with the same
icon. The graph page's preference panel is now called "Chart options", the page
itself is called "Scenario Performance" in the navbar and the browser tab, and
the Settings page keeps its name. The controls inside the panel are named the
way the app's own charts and the aim-training community already name them,
rather than in invented vocabulary.

Decision, four rulings:

- The disclosure button and the panel are **"Chart options"**.
- **`/settings` keeps the name "Settings".** The collision is resolved from the
  graph page's side; an "App setup" rename was considered and rejected.
- The graph page's product name is **"Scenario Performance"**, applied as
  labels only: the navbar link, the page's registered `name` and `title`, and
  doc vocabulary. `/` still serves it and `/home` and `/index` still redirect.
- The panel's column claims **no exclusive tenancy of the page's right side**.
  It is a page-local column a later design may share, stack with, or re-host.

Why: the surfaces sharing the "Settings" name are different in kind. `/settings`
edits server-persisted app setup through one validated Save with restart
semantics; the panel edits instant-apply browser preferences that only the chart
can give feedback on. Naming the panel after what it configures also follows the
repo's precedent that controls live on the surface owning their effect —
playlist management left this same modal for `/playlists`
([2026-07-11](#2026-07-11-the-playlist-overview-is-the-playlist-management-surface)).
"Scenario Performance" is the page's product identity, distinct from its route
position as the default landing page, which is why the rename is labels-only.

Consequences and constraints:

- **The control labels are the app's own vocabulary, not the proposal's.** The
  proposal recommended a *Score goal* group with "Playlist rank lines",
  "Personal-best line", "Show goal line", "Goal percentage of PB", and "Show
  goal verdict". The maintainer rejected that on first local test: the app's own
  chart annotations already render "PB Score" and "Score Threshold", and "Score
  Threshold" is what the aim-training community says. What shipped is *Overlays*
  ("Rank Thresholds", "PB Score") and *Score Threshold* ("Score Threshold
  Overlay", "Score Threshold Percentage", "Score Threshold Notification") —
  the modal's original labels, verbatim. The general rule this carries: proposed
  UI copy is checked against the app's existing plot annotations and sibling
  pages before it ships, however settled a proposal declares it.
- **"Score Threshold Notification" is knowingly imprecise.** Since the
  notification redesign it gates only whether a run is judged against the
  threshold (`_threshold_verdict` returns `None` when it is off); placement
  toasts fire regardless. The maintainer accepted the wording and deferred the
  fix to a later copy pass; a dated comment at the control in
  `source/pages/home.py` records it. The help tooltip is accurate as written and
  is unchanged. That copy pass has since happened: the control is now "Score
  Threshold Verdict"
  ([2026-08-21](#2026-08-21-run-notifications-have-a-master-switch-and-the-threshold-switch-is-renamed)).
- **The route restructure is deferred, not dropped.** Reserving `/` for a future
  Overview page and giving this page a durable `/scenario` route waits until an
  Overview has concrete plans.
- **Run History composes into this column rather than adding a second one.** If
  a run history tied to Scenario Performance arrives, how the two share the
  space is the run-history proposal's question; this one only promises not to
  have claimed the space.

Shipped in PRs #209 and #215; design discussion in #206. Distilled with
[the inspector entry](#2026-08-09-chart-options-live-in-a-collapsible-panel-beside-the-graph)
from `docs/chart_options_inspector_proposal.md`, now deleted.

## 2026-08-08: Rank-History Capture Is Deferred Until A Position-Over-Time Feature Is Designed

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

## 2026-08-08: PyCharm Config Stays Tracked And Its Upgrade Churn Is Committed Once

Status: Accepted

An IDE upgrade changed the format PyCharm writes its own tracked config files
in, and PyCharm re-emits that format every time it launches. Reverting the diff
therefore only defers it, so the project commits it once instead. The IDE
config directory also no longer counts as a reason to cut an automated release,
which it previously would have. A leftover Black on-save setting turned out to
be orphaned by the same upgrade, and deleting it survived an IDE restart, so it
is gone rather than merely documented.

Decision: `.idea/` stays tracked, IDE-upgrade schema churn is committed rather
than reverted, and `.idea/` joins `_BLOCKED_DIRECTORIES` in
`scripts/release_job.py` so an IDE-config-only push does not release.

Why: the same tool-config diff was committed as `89d54cf` on 2026-08-04 and
reverted by `b44901a`; launching PyCharm on `main` rewrote both XML files
immediately, so the revert bought nothing. Untracking `.idea/` instead would
throw away real configuration work — the interpreter and mypy setup, the source
root, and the indexing exclusions — while the genuinely volatile per-user files
(`workspace.xml`, `tasks.xml`, `shelf/`, datasources) are already covered
between the root `.gitignore` and `.idea/.gitignore`. On the release side,
`is_release_worthy()` is a blocklist, and `.idea/` matched no entry, so
`should_release()` returned `True` for a PyCharm tool map and
`.github/workflows/ci.yml` would have tagged CalVer and published a Latest
release that cannot be deleted. `.gitignore` and `.pre-commit-config.yaml` were
already blocked for exactly this reason.

Consequences and constraints:

- **Committing is not self-enforcing.** `.idea/pyLspTools.xml` records the
  registered tool map, so the loop restarts whenever a tool is toggled in the
  IDE: `89d54cf` registered `black` and `ruff`, while the settled state
  registers `ruff` only. What ended the churn is that tool state is now stable,
  not the act of committing it.
- **Neither remaining on-save formatter switch is live.** `.idea/misc.xml`'s
  `Black` component (`enabledOnSave=true`, against the
  `uv (Corporate-Serf-Dashboard)` SDK where `black.exe` really resolves) was
  deleted, because the upgrade orphaned it rather than leaving it live: tool
  state moved to `pyLspTools.xml`, and dropping `enabledOnReformat` was a
  one-time migration write. Hand-editing a generated file is normally what
  invites churn back, so this was tested — after the deletion a PyCharm restart
  rewrote `pyLspTools.xml` and `workspace.xml` and left `misc.xml` alone.
  `.idea/ruff.xml`'s `RuffConfigService` (`runRuffOnSave=true`) is inert for a
  different reason: it belongs to the third-party `com.koxudaxi.ruff` plugin,
  which is disabled IDE-side, so ruff-on-save runs from the built-in tool state
  instead. Read `ruff.xml` as a dormant plugin's config, not as live state. If
  a future upgrade re-emits either component, repeat the delete-and-restart
  check rather than reverting the config.
- **black is a transitive dependency, not an absent one.** It is not in
  `pyproject.toml` and not a configured project tool, but it stays in the lock
  under `datamodel-code-generator` and is installed in `.venv` — see
  [Consolidate Formatting And Linting On Ruff](#2026-07-03-consolidate-formatting-and-linting-on-ruff).
- **Blocking is about triggering, not shipping.** The two lists are separate:
  `_BLOCKED_DIRECTORIES` decides whether a push cuts a release, while
  `.gitattributes` decides what the release zip carries. `.idea/` is now on
  both — it neither triggers a release nor ships in one, per
  [Release Integrity Rests On GitHub Digests And An Enforced Archive Contract](#2026-08-21-release-integrity-rests-on-github-digests-and-an-enforced-archive-contract).
  `docs/` still shows the split as it was: blocked from triggering, but
  shipped, because the zip's own README links into it.

## 2026-08-03: Home's Controls Row Measures The Content Area, Not The Window

Status: Accepted

Opening the navigation sidebar used to shove Home's row of controls onto a
second line, and closing it snapped them back. The sidebar takes 250px away
from the page, but the rules deciding how to lay the controls out were reading
the width of the whole browser window, which does not change when the sidebar
opens. Those rules now read the width of the area the controls actually get,
and the two wide dropdowns narrow a little before the row gives up and wraps.

Decision: Home's controls `dmc.Grid` sets `type="container"` and passes
`breakpoints`, and both wide playlist/scenario dropdowns swap a hard
`miw="min(400px, 100%)"` floor for `flex="1 1 200px"` under a
`maw="min(400px, 100%)"` cap and over a matching `miw` floor. The breakpoint
*values* are unchanged Mantine defaults; only the box they measure moves.

Why: `dmc.AppShellNavbar` is `position: fixed` with `width: 250px` and offsets
main's padding, so the content area shrinks by 250px while the viewport does
not. Mantine's default Grid emits `@media (min-width: …)` for responsive
`span` values, so Home's `span={"base": 12, "lg": 10}` crossed its threshold at
a 1200px *window* even when the content area was only ~900px. Both columns then
got a share of width the page did not have: the left column's controls wrapped
and the right column's radio labels were squeezed. The 400px `min-width` floor
compounded it, for the reason recorded below.

Consequences and constraints:

- **Line-breaking reads the hypothetical main size, not the shrunk size.** A
  flex item is collected onto a line at its flex-basis clamped by min/max
  width; `flex-shrink` only redistributes space *inside* a line that has
  already been collected. Anything pinning a dropdown's pre-wrap size at the
  400px target — the original `min-width: 400px`, and equally a
  `flex: 0 1 400px` basis — books 400px of the row before shrinking can run, so
  the row wraps at exactly the width it did before. The basis must therefore sit
  at the 200px *floor*, with `flex-grow` climbing back toward the 400px cap on a
  line that has room. `tests/test_home_layout.py` asserts the derived
  hypothetical size stays below the target rather than asserting the prop
  strings, because a prop-shaped test passes on all of the broken combinations.

- **`breakpoints` is not optional here.** Mantine renders the element carrying
  `container: mantine-grid / inline-size` only when a Grid passes *both*
  `type="container"` and `breakpoints`, while the `@container` queries
  themselves are emitted on `type` alone. Setting `type` without `breakpoints`
  produces queries with no container to match, silently collapsing every column
  to its `base` span. `tests/test_home_layout.py` pins both props together.
- **The threshold band moves.** Between roughly 1200px and 1480px of window
  width with the sidebar open, Home now stacks its two columns where it
  previously split them. That is the band where the split was crushing both
  columns, so the stack is the intended outcome rather than a regression.
- **Responsive *style props* have no container equivalent.** Mantine resolves
  those through theme media queries only, so this fix reaches responsive `span`
  values and nothing else. Nothing on Home relies on one today: the playlist
  filter's `ml={"base": 0, "lg": "xl"}` was the last, and PR #201 removed it
  outright for left-edge alignment — `tests/test_ui_presentation.py` now
  rejects any left offset on either playlist filter. A responsive margin or
  padding added elsewhere later would silently go back to measuring the window.
- **The sizing rule lives in `PLAYLIST_SELECTOR_PRESET`**, so the Aim Training
  Journey page's `dmc.MultiSelect` picks it up too. Both sit in wrapping rows
  and want the same behavior; splitting the rule to spare the second page would
  cost more than it saves.

## 2026-08-03: One Quiet Notification Layer With Verdict-Carrying Copy

Status: Accepted; three clauses are superseded by the 2026-08-31
["Repeatable Toasts Replace In Place With A Visible Re-Entry"](#2026-08-31-repeatable-toasts-replace-in-place-with-a-visible-re-entry)
entry -- the per-click-id exception to the stable-id rule, the distinct-ids
rationale for the two refresh-failure toasts, and the absolute reading of "at
most one run-verdict toast is visible at a time". Each is marked in place below.
Everything else here stands, including the routing policy that decides which
events toast at all.

The dashboard now stays quiet during normal play. Toasts are reserved for
things the user did, achievements worth interrupting for, and failures they
would act on; a condition that stays true explains itself where it happens
instead of popping up again on every trigger. Each run produces at most one
toast, its title states the verdict, and a newer run replaces the one on
screen rather than stacking beside it.

Predecessor: the
[2026-08-03 background-diagnostics entry](#2026-08-03-background-rank-diagnostics-are-console-only)
deleted four toasts under this policy before the policy itself was recorded;
that entry stands unchanged and this one supersedes nothing. Shipped in
PRs #194, #196, #198, and #200; design in #82 and #195.

**One delivery path.** The app had two notification subsystems. The
logging-driven one routed Python `logging` records into Mantine toasts through
an in-repo handler, and it is deleted: the handler, its module-level queue, its
drain callback, and the tests covering that machinery. `logging` remains the
console and file record; it no longer reaches the screen. The decisive argument
is that **a log level is not a routing policy** — the bridge made every
`dash_logger` call a toast, with a severity picked at the call site standing in
for a judgment that belongs to the event. It also gave every record a fresh
`uuid` id, so records stacked instead of replacing, under generic
"Info/Warning/Error" titles. Everything now goes through `sendNotifications` on
the shell's one `dmc.NotificationContainer`, fed by payloads from the
`utilities/notifications.py` builder.

**Routing policy — who gets a toast.** Decided per event, in this order:

- *Persistent condition* (misconfiguration, missing data, degraded feature) →
  **in-place UI** at the point of impact, never a toast. Conditions do not stop
  being true when a toast expires. Two named exceptions, both persistent
  conditions with no in-place home, both surfaced once per lifecycle rather
  than once per trigger: the Steam-ID mismatch gets one toast per app session,
  and the startup playlist warnings one batch per boot. Both persist until
  dismissed.
- *Automatic failure* during passive navigation → **no toast**; the field state
  conveys it, with a console `logger.warning` retained.
- *User-initiated failure* (Import, manual Refresh) → **error toast**; the user
  asked and deserves the result. A run file that failed to import sits here
  too: playing the run was the user's act, and nothing else tells them it never
  recorded.
- *Achievement / coaching* → one toast per run.
- *Diagnostic* (thread failures, timeouts with automatic fallback) → **console
  log only**.

Litmus tests, in order: is it a state rather than an event? → in-place. Is it
already visible somewhere (plot point, Position field, empty-state canvas,
warmup status strip)? → nothing. Would the user act differently for having seen
it right now? No → log, not toast.

**Background threads never drive UI outputs.** They publish to typed shared
state that an interval callback polls. There is deliberately no general event
bus: each channel carries one kind of event and its consumer decides what the
user sees. The deleted level-driven queue is the anti-pattern the rule exists
to prevent. The one background toast that survived the routing verdicts — the
run-import failure — got its own typed deque rather than a field grafted onto
the run-event queue. The sanctioned channels are enumerated in
[architecture.md](./architecture.md).

**One run, one toast.** Every run verdict and the catch-up digest share the
stable id `run-verdict`. When a run both places top-N and earns a threshold
verdict, the threshold verdict is the headline and the placement a trailing
detail; a run that earns neither emits nothing, because the new point on the
plot is the confirmation that it landed. Four behaviors are normative, and the
mechanism is not:

- at most one run-verdict toast is visible at a time (as amended 2026-08-31:
  true once a response has been applied -- during the ~250 ms replacement
  crossfade the outgoing instance is still animating out);
- a later verdict replaces the visible one, the backlog digest included;
- the replacement receives a full toast lifetime, never the remainder of the
  old timer;
- all of the above holds per browser client and survives page navigation.

The mechanism that satisfies them on DMC 2.8.0, verified against the shipped
bundle: a bare `show` cannot replace (the store ignores it for an id already on
screen) and `update` is a no-op for an id that is not, so each emission sends
**both actions with the same id and payload** and whichever matches applies.
Mantine's auto-close timer is a React effect keyed on the resolved duration
alone, so an `update` carrying the same duration leaves the original timer
running; the payload therefore alternates between two indistinguishable
durations (8000/8001 ms) to force the effect to cancel and re-arm. The
alternation counter is a `dcc.Store` in `app_shell.py` beside the container,
**not** in Home's page layout: a toast outlives the page that emitted it, and a
page-scoped store would reset on remount and hand a still-visible toast the
duration it is already displaying. `hide` cannot substitute — it is a separate
prop whose effect runs after the `sendNotifications` effect, so a hide-then-show
pair in one response would hide the toast it just showed.
`tests/test_home_run_verdict_lifetime.py` models those store semantics against a
clock and asserts the behaviors in elapsed time; it is the upgrade guard for
future DMC versions.

**Presentation standards.**

- Stable, semantic notification ids; dedupe or replace by id. One named
  exception: repeatable user-action results use a **per-click id** — the
  manual-refresh confirmation, where `show` with a reused id would swallow the
  second of two deliberate back-to-back results. *(Superseded 2026-08-31: the
  confirmation is a per-scenario channel and every repeatable result re-pops by
  showing a fresh instance id, so no toast carries a per-click id.)*
- **The title carries the verdict.** Title plus color tell the whole story from
  across the room; never the literal word "Notification".
- **The message leads with the scenario.** Sensitivity is a trailing qualifier:
  top-N is per-sensitivity, so it matters, but it is never the subject.
- One nominal `autoClose` duration, with two deliberate exceptions that persist
  until dismissed — the Steam-ID mismatch and the startup playlist warnings,
  both of which fire when the user may not be looking.
- A failing threshold verdict names the target it missed: one extra number with
  real motivational value.
- No "New personal best!" retitle. A new overall PB necessarily places 1st
  within its sensitivity, so it already earns the run-verdict toast — titled
  "New best score" when unjudged, or carrying the threshold verdict when
  judged; retitling it would create by the back door the dedicated PB toast
  that `product.md` records as declined.

Two manual-refresh failure toasts deliberately share the title "Position
refresh failed" under distinct ids (red when nothing usable came back, yellow
when a cached position was served). They are mutually exclusive outcomes of one
click, and the distinct ids keep a later result from being swallowed by `show`'s
dedupe. *(Superseded 2026-08-31: being mutually exclusive is exactly why they
are now one `rank-refresh-problem` channel — under distinct ids a hard failure
followed by a served-stale retry left both on screen contradicting each other
about the same attempt.)* Softening the red to yellow is coupled to giving the
served-stale toast a title of its own — without that, only the color separates
them — and is left open in [tech_debt.md](./tech_debt.md).

**Deliberately left open: do background rank events deserve a real toast?**
"Your rank updated after that PB" and "Position update timed out" are
console-only under the background-thread rule. Surfacing either needs a
conformant channel — a dedicated typed event queue or polled cache state, never
the run-specific `message_queue` — and the run-import-failure queue is the
pattern to copy if it is ever wanted. It pairs with the unbuilt "rank improved"
toast and should be decided with it, not piecemeal.

## 2026-08-03: Background Rank Diagnostics Are Console-Only

Status: Accepted

Supersedes: the "asks the user to click Refresh" consequence of the
[2026-07-01 score-aware refresh entry](#2026-07-01-keep-scenario-rank-consistent-with-score-aware-refreshes).
The rest of that decision — the timer schedule, the two-decimal catch-up floor,
the monotonic writer, the cache-only interval poll, and the board-authoritative
manual Refresh — is unchanged.

When a position lookup fails in the background, the app no longer shows the user
an error message. The failure is written to the console and the log file, and
the position on screen keeps showing the last value the app confirmed. Nothing
is lost or overwritten by the failure, but the app no longer announces it
either: a background failure is now something the user finds in the log, or
infers from a position that did not move after a personal best.

Decision: four background diagnostic error toasts are deleted and their
`logger` siblings retained. Three are in the rank-freshness timer chain in
`kovaaks/api_service.py` — retry exhaustion, the unknown-user stop, and the
unexpected-error safety net — and one is in `my_watchdog/file_watchdog.py`,
where scheduling the refresh itself fails. `api_service.py` loses its
`dash_logger` import and module-global with them; `file_watchdog.py` keeps both
for its run-import failure toast, which this entry does not touch.

Why: these calls were dead code when written — `dash_logger` records emitted
from a plain thread never reached a callback context — and PR #115's queueing
handler made them live without anyone re-deciding whether they should be. What
they actually deliver is a generic red "Error" toast, batched onto the next
Home visit. One channel was reporting two failures of different kinds, and the
reasons for dropping it differ per kind — neither of them is "the chain retries
until it works", which is true of no path here:

- **An exhausted chain has a recoverable outcome, not a self-healing one.**
  The chain stops; nothing reschedules it. What makes the outcome benign is the
  monotonic writer: a failed attempt never replaces the cached position, so the
  widget keeps serving the last confirmed value and the *next successful
  lookup* corrects it — a later PB, a manual Refresh, or a foreground fetch
  once the week-long rank-cache TTL expires (the interval poll is cache-only
  and never triggers one). With no later PB, the displayed position can sit at
  its pre-PB value for that full TTL. That is bounded staleness on a value that
  was correct when written, and it is the honest ceiling on this decision.
- **The unknown-user stop never recovers, and is not claimed to.**
  `_run_attempt` returns without scheduling, and every later PB repeats the
  same failure until the username is fixed on the settings page. It is dropped
  for a different reason: it is a persistent misconfiguration that the
  foreground already reports. Home's rank callback takes `run-events` as an
  input, so the same new run that schedules the chain also triggers a
  network-allowed foreground lookup, which returns `UNKNOWN` carrying
  `KovaaK's username '<name>' was not found.` and toasts it through
  `_emit_rank_messages`. The deleted background toast was a second, later, less
  specific copy of a message the user already receives.

Consequences — the accepted loss is on the exhaustion path: it now has no
user-visible surface at all, so noticing one means reading `data/logs/debug.log`
or the console, or noticing the position did not move. This entry accepts that
rather than solving it. The remedy on the table — a persistent in-place state on
the Position field that explains why the value is what it is — is a UI addition
belonging to the notification redesign, not to a deletion-only change, and is
tracked there (PR #82, the routing-policy and in-place-state decisions). Manual
Refresh, which reports its own failures in the foreground, remains the escape
hatch the superseded entry reserved for a permanently divergent score; what
changes is that the app no longer prompts for it. The regression tests for these
paths assert the retained log records rather than toast delivery.

Scope: this entry decides these four call sites only. The broader notification
redesign — which subsystem owns toasts, the routing policy that produced this
verdict, and the fate of every other toast in the app — was still under debate
in PR #82 when this shipped, and is now recorded in the
[2026-08-03 notification-layer entry](#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)
above. The deletion was split out (PR #194) because it stands alone: nothing
else reads the removed calls, and the retained logging is untouched.

## 2026-08-03: Settings Detection Suggests, And Identity Is Offered Only Once Verified

Status: Accepted; the single-runtime-writer clause is narrowed by the
2026-08-11
["A Fresh Install Is Asked Once, On A Card Keyed To Key Absence"](#2026-08-11-a-fresh-install-is-asked-once-on-a-card-keyed-to-key-absence)
entry — Save is still the only runtime writer of settings *values*, but a
locked service operation may record a declined identity as `""`. Everything
else here stands.

The Settings page now offers what this machine already knows instead of asking
the user to type it. The stats-folder box suggests every Steam library that
holds a KovaaK's stats folder, and a Detect button beside the identity fields
checks the machine's Steam accounts against KovaaK's and fills in the one it
can prove belongs here. When it cannot prove exactly one, it lists what it
found and lets the user choose. Nothing reaches disk until Save: detection
only ever fills the form.

Decision — **detection suggests, Save writes.** Both detectors feed inputs the
user can still edit or ignore, so the store keeps its single runtime writer and
all of Save's shipped semantics (all-or-nothing validation, every key written,
warmup cold-start on a first identity, the restart notice from
`is_restart_pending()`). Stats-directory suggestions are hints, not an allowed
set: the field stays free text, a path Steam never heard of is still valid, and
Mantine's default option filter is overridden (`allOptions` in
`assets/dashMantineFunctions.js`) because the field is normally prefilled and
the alternatives are precisely what it must keep showing. The absent-key
`stats_dir` bootstrap remains the app's one silent writer, per the earlier
one-silent-writer decision; identity never joins it, because a wrong identity
is not self-evident the way a wrong stats folder is — it fills caches with
someone else's ranks.

**Identity is offered only as a verified pair.** KovaaK's has no reverse
lookup — `by-steam-id` answers 404 and the query-parameter profile endpoint 401
— so detection cannot ask who a Steam ID belongs to. It guesses and verifies
instead: every local Steam account's persona is probed against the
unauthenticated `by-username` endpoint, and the answer counts only when the
profile's `steamId` equals that account's SteamID64. A persona that merely
coincides with someone else's KovaaK's name is discarded rather than believed,
409 is a confirmed absence, and what the page fills in is the profile's
canonical `webapp.username`, never the persona that found it: the two are
distinct namespaces that often coincide, and only the canonical spelling works
against the rest of the API. Accounts come from every Steam root the registry
names rather than the first — the 32-bit and 64-bit views can point at
different installs, and neither is guaranteed to be the active client — merged
by SteamID64 keeping the newest `Timestamp`, because the most recently used
client holds the freshest persona.

**The trigger is split by cost.** Stats-directory candidates are a registry
read and a handful of directory probes, so they are recomputed on every render
of the page. Identity detection calls KovaaK's, so it runs only behind the
button, which doubles as re-detect: opening the page never spends a request,
and a slow-spell account can hold the button's spinner for tens of seconds
without a render waiting on it.

**Probing personas is an accepted privacy trade, and it stays out of the log.**
Detection sends the persona name of every Steam account on the machine —
including other people's on a shared PC — to a public endpoint. That is
deliberate: personas are already public on Steam, the probe is equivalent to
typing the name into kovaaks.com's search, it fires only on an explicit press,
and nothing is persisted for candidates the user does not save. The consequence
is designed in rather than left for review to find: `data/logs/debug.log` is
collected with bug reports, so the probe marks its request sensitive — attempt
lines log a placeholder in place of the queried name and failure summaries drop
the query string — and detection's own lines name counts and positions
("account 2 of 3"), never personas or IDs. A regression test drives success,
409, and transport failure under `caplog` and asserts no persona reaches a
record.

**An incomplete detection is never dressed up as a conclusive one.** The engine
reports two failure facts beside its candidates: how many accounts could not be
checked (a transport failure, an unexpected status, or a 2xx payload the
pipeline cannot use — schema drift degrades exactly like an outage, never as an
exception), and whether account discovery itself was complete (an account list
that existed and could not be read is a different fact from reading cleanly and
finding nobody). The page spends both. **The auto-fill gate is exactly one
candidate, zero unchecked, discovery complete**; a sole candidate from a run
with anything unresolved goes to the picker, because the unresolved part may be
hiding a second valid account. The conclusive "no Steam account here has a
KovaaK's profile" message — the one that tells the user manual entry is all
that is left — is reachable only from that same certainty; an unreadable
account list says so in its own words instead.

Deliberately out of scope: the guided first-run experience, whose
discoverability and dismissal questions are deferred to their own proposal;
verifying a manually typed username; the pre-2021 numeric-key
`libraryfolders.vdf` format (a known gap, pinned by test); and any change to
startup — the bootstrap stays first-hit and absent-key-only.

Provenance: distilled from `docs/settings_detection_proposal.md` (proposed in
PR #186), shipped in PRs #189 (stats-directory candidates), #191 (the identity
engine), and #193 (the page's Detect action); the proposal file is deleted in
the shipping PR and git history holds its full text.

## 2026-08-02: The Settings Page Owns Version Display

Status: Accepted

The app's version now appears on the settings page — the release tag on one
line, the commit it was built from on the next — instead of hiding in a
tooltip on the header's GitHub icon. Anyone checking which version they are
running, or quoting one in a bug report, can look somewhere they would think
to look. The section is plain text: it shows what the app already knew about
itself and asks the network nothing. Its two dates can honestly disagree by a
day, because the version dates the release and the second line dates the
commit; that line is labelled Commit so the difference reads as fact, not
error.

Decision (PR #190): the settings page is the venue for build identity, and
`github_component`'s tooltip reverts to a plain "View this app on GitHub".
The build suffix was an explicit stopgap — identity shipped (PR #154) before
any page existed that could own the display, and information behind a hover
on a repo link is found by accident rather than on purpose. A separate About
page was considered and rejected in the same call: a nav destination for three
lines of static text is not worth the space, and the settings page
([entry](#2026-08-02-user-settings-live-in-an-app-owned-store-with-a-settings-page))
is already the "about this install" home.

The section is static text built with the page layout from
`BuildInfo.release_label` (the CalVer tag, `dev` in a source checkout, or
`unknown`) and `BuildInfo.short_description` (short SHA and commit date). It
re-derives no part of the identity, owns no callback, and makes no request.
Identity resolution is unchanged: the stage-time `release.json` copy and the
full precedence live in
[Build Identity Comes From The Manifest](#2026-07-19-build-identity-comes-from-the-manifest-corroborated-by-the-stamp),
whose surfaces list this entry rewrites.

Clock semantics (PR #225): the CalVer tag date is the release date in UTC —
CI mints the tag with `date -u` — while the displayed commit date is git's
`%cs`, rendered in the commit's own recorded offset. They date different
events on different clocks, so an evening local-time merge routinely
straddles UTC midnight and picks up a next-day tag. Rather than
UTC-normalising every identity producer to force agreement, the build line
carries a `Commit` prefix that attributes the parenthesised date to its
event.

Sequencing behind that mechanism (PR #188) was a hard dependency, not a
preference. Post-update verification — "the console said it updated to vX; did
it work?" — is the display's peak-usage moment, and a version line reading
`unknown` exactly then looks like a failed update and manufactures the
confused bug reports the display exists to prevent.

Support boundary for that guarantee (maintainer, adjudicating the PR #187
review): the app has a single-user install base, so update paths originating
from releases that predate PR #188 are out of support. The guarantee holds
whenever the launcher staging the update is PR #188's or newer. An install
still on an older release stages its next update without the copy, so that
one trial session shows `unknown`; it self-heals at the next launch, and
permanently once a newer launcher stages the following update. Both escape
hatches already exist — launch again, or re-run the install one-liner. With a
single-user install base this is documented rather than engineered around.

Rejected alternatives:

- **Delivering `release.json` inside the release archive**, so launchers
  predating the copy step still receive the metadata. The zip is pure
  `git archive` output — the only producer that expands the `version.txt`
  stamp — so injecting a generated file means the release job post-processes
  the archive and a second identity artifact must be validated before
  publish. Its only beneficiary is the out-of-support path above. Rejected
  with that boundary, not forever: if the boundary widens, this is the
  mechanism to revisit.
- **An update-availability check on the page** ("newest release is vX"). It
  needs a network call from a page that makes none, plus policy decisions
  (when to check, what to cache) that nothing here requires. Out of scope,
  not rejected forever.
- **A multi-entry `install.json`** with per-version records and an `is_active`
  flag — already recorded, and still rejected, in the entry linked above.

Deliberately not shown: the update policy (automatic, or pinned to a tag). It
is a cheap manifest read, but it only repeats a fact the user set themselves
via the installer; skipped until asked for.

## 2026-08-02: A Committed Side Effect Reports Its Outcome Even When A Later Write Fails

Status: Accepted

Saving a preference to disk can fail — on Windows, antivirus or the search
indexer can hold a file open long enough to defeat the retries. When that
happens partway through an action the user already triggered, the app used to
abandon the whole response, so the screen said nothing at all. Two rules now
govern that: a screen must never keep showing a success message for a write
that failed, and an action whose real work already happened must still tell
the user it happened. In practice, importing a playlist that cannot be marked
visible now shows an orange notice saying the playlist was imported and how to
unhide it, and deleting a playlist still confirms the deletion.

Decision — two rules for a failed store write inside a callback:

1. **No stale success claim.** A UI that prints a success claim must not keep
   printing it after a failed write. A silent optimistic UI that reverts on
   its own may keep propagating. (Adjudicated during the PR #183 review;
   implemented there in `bae99a5` on the settings page, and first recorded
   here.)
2. **A committed side effect reports its outcome**, even when a later step
   fails. The rule above is about a false claim; this one covers the absence
   of any claim after an irreversible operation has already succeeded.

Mechanism: the handling is page-local `try/except OSError` at the call site
(`PermissionError` is a subclass). `replace_with_retry` re-raising after
exhausted retries stays the store contract, and the three writers in
`playlist_visibility_service.py` keep propagating with unchanged signatures —
a store-wide no-propagation policy was considered and deferred, since it would
force a UI answer for the toggle, where the right answer is "show nothing".
The write-before-cache ordering in those writers is load-bearing: a failed
write leaves the in-memory set holding the old value, so a retry still writes.

Per call site in `source/pages/playlists.py`:

- **Toggle** (`update_playlist_visibility`) — propagates, unchanged. Nothing
  is committed and no claim is printed; the cell renders purely from
  server-supplied state, so a failed request leaves no wrong icon on screen
  and the next click retries. Pinned by a regression test so a future
  catch-all cannot quietly change it.
- **Import** (`import_playlist`) — reports the split outcome. The playlist
  file is already on disk, so every output matches the success path (refresh
  bumped, modal closed, field cleared, warmup still enqueued) and only the
  toast changes: orange, under its own id, saying the import succeeded and
  naming the label and canonical code, then that the playlist could not be
  marked visible and how to surface it. Generic "import failed" wording is
  forbidden here — it would be a false statement, the exact defect this
  fixes.
- **Delete** (`confirm_delete_playlist`) — logs the failure and shows the
  ordinary green "Playlist Deleted" toast, deliberately with no split-outcome
  message. This `hide_playlist` is membership bookkeeping (pruning the deleted
  code from the shown set) and its failure has no observable consequence: the
  row is gone either way, a dead code renders nowhere, and the residue
  self-heals if the code is re-imported, because "importing is the intent to
  see" early-returns on an already-shown code. Reporting it would be noise
  about internals. The user-visible fix is that the request no longer fails,
  so the retry that produced a red "Playlist Delete Failed" toast for a
  *successful* delete never happens.

Reachability, so nobody re-derives it: import can only hit the write once a
visibility file exists — with no file, the shown set is seeded from the user
root, which already contains the just-imported playlist, so `show_playlist`
early-returns. First-run installs are immune; steady state is not. Delete only
writes when the playlist was visible.

Provenance: the PR #183 review and commit `bae99a5` (rule 1), and PR #185
(rule 2 and the playlist call sites).

## 2026-08-02: User Settings Live In An App-Owned Store With A Settings Page

Status: Accepted

Where the KovaaK's stats live, the KovaaK's username, and the Steam ID have
moved out of the hand-edited configuration file into a small file the app
owns and writes. A Settings page inside the app shows and changes all three,
so ordinary use no longer needs a text editor. The configuration file keeps
only what a person genuinely sets by hand, such as the port. An update never
blocks on editing that file: keys a release no longer knows about are named
in one warning and ignored.

Decision — **one home, one writer**: every parameter lives in exactly one
file, and every file has exactly one owner. `config.toml` is human-owned and
app-read-only. `data/settings.json` is app-owned and written only through
`source/config/settings_service.py`, whose mechanics mirror the playlist
visibility store (module `RLock`, in-process cache, temp file + `fsync` +
`replace_with_retry`, tolerant reads). Nothing else ever writes it — the
installer included.

The schema is flat, three string keys, no `schema_version`, no nesting.
(**Superseded on the `schema_version` point only** by the 2026-08-11
durable-store stamp entry: the file now carries a top-level integer
`schema_version`, unknown keys are invalid rather than ignored, and an
unusable file no longer rewrites itself on the next automatic write. The flat
three-key schema and the unset semantics below are unchanged.)
Unset semantics are deliberately flat too: a missing key, an empty value, and
a missing, unreadable, or malformed file all mean *not configured* — no
identity disables rank lookups, no usable `stats_dir` runs the app empty. A
malformed file is warned about once, treated as holding no keys, and rewritten
whole by the next *user-initiated* save (which copies it aside first); it is
never fatal. Hand-editing while the app is
stopped stays a legitimate escape hatch, but edits made while it runs are not
picked up, because reads are cached in-process. Only the bootstrap in the next
entry distinguishes an absent key from an empty one.

`ConfigData` therefore drops all three fields and `example.toml` drops their
entries; the installed `config.toml` is `port` only. **Unknown `config.toml`
keys are warn-logged and ignored** — a permanent design choice, not a
transition shim. It is the removed-field mirror of the update contract's
"releases must read older state" rule, and it is what makes every promotion
boundary and every rollback safe by construction: a config carrying retired
keys runs on both the outgoing and the incoming version. The governing rule
follows from it — **through any promotion boundary, `config.toml` stays in a
shape both versions can read, and cleanup happens only after promotion**. (An
earlier revision claimed pydantic rejected unknown keys and would fail startup
on an unmigrated config; that behavior never existed, and the warning replaces
the imagined typo protection with visible, non-fatal feedback.) Migration is
manual and never blocks an update, per the single-user no-compat-shims
convention: there are no in-app migrations.

The page at `/settings` edits the three values with one Save. The write is
all-or-nothing — any field error writes nothing, so the store never holds half
a form — and a successful save writes every key, empty string included, which
is what keeps "cleared" distinguishable from "never set". Validation is
offline only: `stats_dir` must be an existing directory or empty, and
`steam_id` must be shaped like a SteamID64 (17 ASCII digits at or above the
universe-1 base `76561197960265728`, tightened from digits-only as the arc
shipped, because an account ID or a SteamID3 fragment is digits too). The
username is free text; confirming it against KovaaK's is detection territory
and belongs to a later proposal. The form is built per visit from the stored
view rather than the pinned accessors, so it always shows what is on disk. A
write that fails is caught and reported in the status line rather than
escaping into a request the user cannot see. State-writing page callbacks are
`n_clicks`-guarded with a None-trigger regression test, because under
DashProxy a callback can still fire once on page load despite
`prevent_initial_call`.

Provenance: distilled from `docs/settings_store_and_page_proposal.md`
(proposed in PR #171, register R1–R8, amended twice during review), shipped in
PRs #181, #182, #183, and #184; the proposal file is deleted in the shipping
PR and git history holds its full text.

## 2026-08-02: Restart-Scoped Settings Are Pinned At Boot, And The Stats Folder Finds Itself

Status: Accepted

The app no longer has to be told where the KovaaK's stats folder is. On a
start with nothing ever configured it looks the folder up the way the
installer used to, stores what it finds, and uses it immediately. Settings
that cannot safely change under a running app are frozen when it starts, so a
saved change either applies at once or the Settings page says a restart is
needed. The app also starts and serves with no stats folder at all, showing
empty pages and a hint instead of refusing to run.

Decision — **restart-scoped values are pinned, not re-read.** `stats_dir` is
resolved once by server startup (`resolve_stats_dir`) and every consumer reads
that pin (`get_usable_stats_dir`); a per-operation read would let a mid-run
save move half the app to a new directory while the watchdog and the runs
already in memory stayed on the old one. Whether the directory is usable is
decided as part of that resolution, not per call, so a directory that appears
mid-run — a network library coming online — cannot half-enable an app whose
scan and watchdog were already skipped. A pin that was never resolved (tests,
imports, any entry point that is not the real startup) reads exactly like an
unset value.

Identity is pinned as a **pair**, frozen by the first read that observes a
configured username. Reading both fields together is what stops a lookup from
straddling a save and resolving one player's rank into another's cache entry.
Staying live until that first non-empty read is what lets a first-time
identity set apply without a restart; a later change is restart-scoped
instead, because the warmup worker keeps the context it started with and the
caches it fills are scoped to one identity per process. `is_restart_pending()`
derives the Settings page's notice by comparing the store against both pins,
so the notice describes reality for every consumer and stands until the
restart actually happens. It is derived, never stored. The app never restarts
itself, and there is no live re-initialization of the watchdog, the warmup
singleton, or the in-memory data — that machinery is the riskiest code this
arc could have contained, and a restart costs one console close and a shortcut
click.

**The app starts without a usable stats directory.** Unset, and set but not an
existing directory (the moved-library case), behave identically: startup skips
the initial scan and the file watchdog, logs one line naming what was
configured, and serves — only `port` is needed to serve pages. Home shows a
hint linking to the settings page. The `SystemExit` that used to guard this is
gone.

**`stats_dir` bootstraps app-side**, replacing the detection deleted from the
installer (see the 2026-08-02 addendum on the 2026-07-19 installer entry
below, which this supersedes for stats-directory detection). On startup with
the key **absent** — a missing file counts — the app collects Steam's install
roots from the registry (`HKCU` `SteamPath`, then both `HKLM` `InstallPath`
views, every hit kept), treats those roots as libraries, adds every `"path"`
value from each root's `steamapps/libraryfolders.vdf`, and probes
`<library>/steamapps/common/FPSAimTrainer/FPSAimTrainer/stats` per unique
library. The first existing directory is written through the settings service,
merged with whatever is already stored. The bootstrap runs before the pin
above, so a first detection serves the boot that made it. A miss writes
nothing and is retried on the next start, so a dashboard installed before
KovaaK's self-configures once KovaaK's appears. A present-but-empty value is
never overridden: that is the user saying "run without run data" on the page,
and the page writes every key on every save precisely so this distinction
survives.

The pick is silent — no confirmation step. On a machine with a stale copy in a
second Steam library it can be wrong, which is immediately visible (empty or
wrong data), fixable on the settings page, and properly solved by the
follow-on proposal's candidate dropdown. The page shipping first is why the
silent write is acceptable at all: the repair surface precedes it.

The vdf is read with the installer's flat `"path"\s*"([^"]*)"` regex,
unescaping `\\`, rather than with the `vdf` PyPI package: no new dependency
for a file read once per start, the upstream package is unmaintained, and the
regex ignores the file's structure by design. It harvests the per-library
object format Steam writes today; a pre-structured file (numeric key to path)
contributes no extra libraries, exactly as the installer behaved, and the
Steam roots themselves are still probed. An unreadable or malformed vdf is
logged and skipped, never fatal. The bootstrap runs only from the real server
startup path, never at import, and the registry read is isolated in one
function so no test ever touches the real registry.

Provenance: same proposal and delivery arc as the entry above (PR #171;
PRs #181, #182, #183, #184).

## 2026-08-01: Doc-Style Follow-Up — Decisions Needed, Roadmap Trim, No Log Index

Status: Accepted

The proposal section listing what the maintainer must rule on is renamed
from "Decision points" to "Decisions needed", so the heading itself tells
you whether a document wants your attention. This entry now carries the
complete doc-style rules and replaces the original entry below. The
roadmap keeps only the few most recently shipped milestones instead of a
full history. A topic index for this log was considered and rejected.

Decision — the complete two-layer doc style (supersedes the entry below;
the only rule change is the section rename, everything else carries
forward unchanged):

- Durable docs are layered. Layer 1 (maintainer): every new or
  materially-edited `decision_log.md` entry — and every `docs/specs/`
  file, once that layer exists — opens with a 2–4 sentence
  plain-language summary (one idea per sentence; no cross-references,
  file paths, or embedded enumerations). Layer 2 (agents): the dense
  payload follows, written as before — compression there is a feature.
  The summary is written, updated, and reviewed in the same PR as its
  payload, by the same author. No backfill: existing entries convert
  only when a change touches them anyway.
- Proposals follow the template in `AGENTS.md` ("Proposal template"):
  `Status:` → `## TL;DR` → `## Decisions needed` → `## Problem`, dense
  body per-proposal after that (Design is the normal next section but
  may be replaced by more specific ones). Renaming "TL;DR" to "Summary"
  was considered and deliberately not done.
- Decisions needed carries only choices requiring maintainer product or
  workflow judgment, or acceptance of a costly-to-reverse trade-off,
  each with a recommended answer and the material consequence of
  choosing differently; the author owns mechanical, reversible, and
  evidence-resolvable choices.
- `tests/test_docs.py` enforces the leading section order mechanically
  (placement, not just presence). The layer-1 prose rules are writing
  guidance held by same-PR review — the test never judges prose quality
  or Markdown rendering fidelity (settled across the PR #174 review
  rounds).
- `docs/product.md` is exempt — its *Problem solved:* format already
  leads with the user-facing statement.

Why (unchanged from the superseded entry): the docs pipeline optimizes
for agent readers — distillation is compression — while the maintainer,
now primarily a reader and decider with agents doing most
implementation, pays the skim cost. Layering serves both without
compromising either, and the decision filter attacks the number of
escalations put in front of the maintainer, not just their
discoverability.

Roadmap policy: the Shipped section keeps only the ~5 most recent
milestones, newest first, and older entries leave the file entirely —
the shipping checklist already lands their user-facing rationale in
`product.md` and their technical rationale here, and git history holds
the full sequence.

Rejected: a topic index at the top of this log (reviewer suggestion once
the log passed ~1,500 lines). The planned `docs/specs/` capability layer
links the relevant log entries per capability and is the intended
findability fix; a hand-maintained index would duplicate it as a third
structure, touched in every shipping PR and verified by nothing. Revisit
only if findability still hurts after capability specs land.

Provenance: the two-layer rules were established via
`docs/doc_style_proposal.md` (PR #174; two external review rounds;
proposal deleted per "Shipping a proposal" — git history holds the full
text). This entry restates them in full with the post-merge follow-up
refinements (external reviewer suggestions, maintainer-ratified scope:
rename yes, "TL;DR" kept, trim yes, index no) and supersedes the
original entry below.

## 2026-08-01: Durable Docs Open Plain And Proposals Lead With Decisions

Status: Superseded — replaced by the follow-up entry above (section
rename; all other rules carried forward there in full)

Docs now serve their two readers in layers instead of forcing one register
on both. Every new decision-log entry opens with a short plain-language
summary, like this paragraph, before the dense detail. Proposals open with
a summary and a filtered list of the decisions that genuinely need the
maintainer, and the docs test enforces that order. The dense record itself
is unchanged.

Decision: durable docs are layered. Layer 1 (maintainer): every new or
materially-edited `decision_log.md` entry — and every `docs/specs/` file,
once that layer exists — opens with a 2–4 sentence plain-language summary
(one idea per sentence; no cross-references, file paths, or embedded
enumerations). Layer 2 (agents): the dense payload follows, written as
before — compression there is a feature, not a bug. The summary is
written, updated, and reviewed in the same PR as its payload, by the same
author. No backfill: existing entries convert only when a change touches
them anyway.

Proposals follow the template in `AGENTS.md` ("Proposal template"):
`Status:` → `## TL;DR` → `## Decision points` → `## Problem`, dense body
per-proposal after that (Design is the normal next section but may be
replaced by more specific ones). Decision points carry only choices
requiring maintainer product or workflow judgment, or acceptance of a
costly-to-reverse trade-off, each with a recommended answer and the
material consequence of choosing differently; the author owns mechanical,
reversible, and evidence-resolvable choices. `tests/test_docs.py` enforces
the leading section order mechanically (placement, not just presence);
prose quality is held by same-PR authorship and review, not tests.
`docs/product.md` is exempt — its *Problem solved:* format already leads
with the user-facing statement.

Why: the docs pipeline optimizes for agent readers — distillation is
compression — while the maintainer, now primarily a reader and decider
with agents doing most implementation, pays the skim cost. Layering serves
both without compromising either, and the decision filter attacks the
number of escalations put in front of the maintainer, not just their
discoverability.

Provenance: distilled from `docs/doc_style_proposal.md` (two same-day
external review rounds), committed and then deleted in the shipping PR —
git history holds the full text.

## 2026-08-01: No Username Stays Fully Offline — User-Independent Totals Rejected

Status: Rejected

Decision: an empty `kovaaks_username` keeps its documented meaning — the app
runs fully offline and no leaderboard feature makes network calls. The
proposal to resolve leaderboard IDs and show Total Players without a
configured username (PR #166, split out of the leaderboard-ID seeding
proposal) was reviewed independently twice and closed as not planned.

Why:

- The README promises that leaving the username empty runs the app fully
  offline, and today the rank service short-circuits before any network call.
  The proposed lazy per-scenario totals fetch at playlist open would silently
  break that zero-network contract.
- A board's population without the user's position or percentile answers none
  of the product's core questions ("am I improving? where am I weak?") — it
  fills a grid column, not a need.
- The proposal understated the plumbing: `_with_leaderboard_total` rejects
  non-RANKED/UNRANKED results by design, and the progressive-fill accounting
  counts UNKNOWN rows as unavailable positions, so username-less playlist
  opens would fetch totals and still end in red "positions unavailable"
  messaging unless both grew new semantics.

What survives: the leaderboard-ID seeding (PR #169, previous entry) stands on
its own merits. The worthwhile kernel — treating "leaderboard features off"
as a normal quiet state rather than a red error, skipping the futile
progressive position fill, and pointing at how to enable the features — is
deferred until a settings page exists to give that pointer a destination
(settings/config work proposed in PR #171, not yet agreed as of this
writing). The optional import-warmup companion (prefetching
unplayed scenarios of a freshly imported playlist) is dropped with the
proposal; revisit only if the import-then-open flow proves slow in practice.

## 2026-07-20: Seed Leaderboard IDs From The Bundled Benchmark Corpus

Status: Accepted

Decision: the benchmark importer embeds each scenario's KovaaK's
`leaderboard_id` — from the `/benchmarks/player-progress-rank-benchmark`
payload it already fetches — into every generated playlist JSON, and the app
folds those embedded IDs into the permanent name->ID mapping cache at startup.
The scenario schema field is optional (`Scenario.leaderboard_id`, default
`None`) so imported and pre-change files keep validating, and the runtime
lookup path (`get_cached_leaderboard_id`) is unchanged.

**The corpus is the seed.** The IDs live in the same files as the scenario
names, so every corpus lifecycle rule (staging, review, activation, retention)
applies to both automatically — the shipped corpus and the shipped IDs cannot
diverge because they are one artifact. There is no aggregate seed file.

**Startup merge against the asserted set.** The existing full-corpus scan now
also collects the embedded `scenario name -> leaderboard_id` pairs. Names two
bundled files disagree on are excluded with a warning; the survivors form the
*asserted set*. The merge is one atomic read-modify-write of the mapping cache:

- an asserted name missing from the cache is added, tagged `source: "seed"`;
- a seed-owned entry whose asserted value changed is refreshed, so corrected
  IDs reach existing installs;
- a seed-owned entry whose name is no longer asserted is removed, so an
  upgraded install never resolves a mapping a fresh install would not;
- entries learned from the live API are never touched, and a name that already
  has a learned entry never gets a seed-owned row.

If any bundled file fails to load, the merge still adds and refreshes but
suppresses removals — a partial view of the corpus must not retract mappings it
may still assert.

**Regeneration mechanic.** The generated-file provenance carries a
`schema_version` marker (`generated_from.schema_version`), bumped when the
generated schema changes. `should_skip_generation` then treats a file written
under an older schema as stale, so a plain importer run regenerates the whole
corpus through the benchmark payload cache — without `--force`, which would
refetch every payload live.

Why: resolving a scenario name to its leaderboard ID was treated as
user-dependent, and it isn't. The bulk mapper (total-play hydration) only
returns *played* scenarios, so every unplayed playlist scenario fell through to
the exact-name search endpoint (`/scenario/popular`) — the slowest,
most timeout-prone call in the app's KovaaK's surface, one call per scenario —
and a username-less install could not resolve IDs at all. Shipping the IDs with
the corpus makes first opens of unfamiliar bundled playlists fast and
identity-free.

Accepted limitation: if KovaaK's ever re-uploads a scenario under the same name
with a new leaderboard ID, a *learned* cache entry keeps winning until it is
deleted — seed-owned entries are refreshed by the merge, so only learned rows
can pin a stale value. Escape hatch: delete the mapping cache file; the next
startup re-merges the bundled IDs.

Corpus coverage is CI-enforced (`tests/test_playlist_rekey.py`): every scenario
of every tracked `resources/benchmarks/*.json` carries a non-null
`leaderboard_id`, with an exception list that ships empty.

## 2026-07-19: Releases Are Automated CalVer Tags Cut By CI

Status: Accepted

Decision: every push to `main` that changes anything an installed copy runs
publishes a GitHub Release tagged `vYYYY.MM.DD` (`.N` suffix for same-day
repeats). No human picks a version number or judges whether a commit "deserves"
a release. The job lives in `.github/workflows/ci.yml` with `needs: test` — a
commit that fails the gates never becomes a release — and the logic is in
`scripts/release_job.py`.

The skip rule is a **blocklist** (`docs/`, `tests/`, `.github/`, any `*.md`,
`.gitignore`, `.pre-commit-config.yaml`), not an allowlist, because the failure
directions are asymmetric: a redundant release is only noise, while a missed
release strands distribution inputs — `install.ps1`, the launcher,
`example.toml`, `.python-version`, `.gitattributes` — at an older tag. When in
doubt, release.

Two properties the job must keep:

- **The Latest invariant.** Concurrent pushes serialize through a fixed
  concurrency group (`cancel-in-progress: false`, `queue: max`), but that
  serialization is FIFO by wait-start time, not by source order — a newer push
  with faster tests can enter the critical section first. So inside it the job
  checks ancestry (`git merge-base --is-ancestor`) against published releases
  and passes `make_latest: false` when a published release descends from its
  own SHA. `make_latest` defaults to true, so without this an older commit's
  slow run would silently downgrade every `latest`-tracking install. After
  claiming Latest, the job asserts `releases/latest` really resolves to its tag.
- **Idempotency across every partial-failure state**, not just
  tag-without-release: a rerun reuses a tag already pointing at `HEAD` and
  *resumes an existing draft* (re-attaching assets) rather than creating a
  second release.

The zip asset is built by `git archive`, the only producer that expands the
`export-subst` stamp — zipping a checkout would ship `version.txt` unexpanded.
A second, tiny asset (`release.json`) carries the tag, full SHA, commit date,
and that release's uv and Python pins, so the installer and launcher never parse
TOML from PowerShell or spend an extra API call resolving the exact SHA
(`releases/latest` reports `target_commitish`, which may be a branch name).

Why: the maintainer explicitly does not want per-commit SemVer judgment, and the
app has no API consumers to justify SemVer semantics. Market research across
fast-shipping projects (yt-dlp, Path of Building Community, RuneLite, and
FFmpeg's binary channels) found dated, immutable, retained artifacts to be the
baseline even for daily-or-faster shippers, and found no comparable project
shipping *unidentified* builds from a branch tip — tags are load-bearing for
rollback and support.

Provenance: this entry and the six below distill the release, versioning, and
distribution proposal added in PR #150 and deleted once shipped (git history
holds the full text). It went through four external design-review rounds plus
the market-research run summarized above, and was implemented in PRs #154,
#155, #158, #159, and the activation PR that removed it.

## 2026-07-19: Releases And Their Assets Are Immutable

Status: Accepted

Decision: GitHub's immutable-releases setting is enabled on the repo, so tags
and releases cannot be moved or deleted. The release job therefore creates a
tag, then a **draft**, attaches assets, validates them, and only then publishes.

Why: rollback is only trustworthy if `v2026.07.19` means the same bytes forever;
a movable tag makes "go back to the version that worked" meaningless. The
setting is not retroactive, which is why it was flipped *before* the release-job
PR merged — that merge cut the first release, and a release published while the
setting was off stays mutable forever.

The consequence to remember: assets lock at publication, so validation must run
pre-publish. After an immutable release is published it is too late to fix a bad
asset — the only remedy is another release. This is what forces the draft-first
flow above; do not "simplify" it into publish-then-attach.

Launcher-side checksum verification is deliberately deferred: HTTPS to
github.com is the trust anchor at this audience size.

## 2026-07-19: Build Identity Comes From The Manifest, Corroborated By The Stamp

Status: Accepted
Superseded in part: 2026-08-02 (PR #188) added a release-file layer above the
manifest and retired the accepted `tag: None` consequence recorded below.
Every other decision in this entry stands.

The app works out which release it is running by reading files left beside the
code and in the install directory, never a version string committed in the
source. Each of those files is trusted only when it agrees with the stamp that
ships inside the downloaded code, so a half-finished update cannot make a new
build report the old version. Since 2026-08-02 the installer and launcher also
leave a copy of the release description next to each installed version, which
is what lets a freshly updated app name its own release right away. Someone
updating the app now sees the right version reported from the first session
rather than a session later. Where they see it is the settings page, which
since 2026-08-02 shows the running version; the header GitHub link's tooltip
used to carry it and no longer does.

Decision: one reader (`source/utilities/build_info.py`) resolves the running
build's identity, and every user-visible build string derives from it. The
precedence is manifest → expanded stamp → git → `unknown` (a release-file
layer was added above the manifest on 2026-08-02; see the end of this entry):

1. **`install.json`** — the install manifest, written atomically by the
   installer/launcher into the state root, never by the app. The only layer that
   can know the release *tag* — until the 2026-08-02 copy, which carries it too.
2. **`version.txt`** — committed with git `export-subst` placeholders
   (`sha: $Format:%H$`, `commit-date: $Format:%cs$`) plus a `.gitattributes`
   entry. GitHub's archive endpoints run `git archive`, which expands them, so
   any zip download carries its full SHA and commit date.
3. **git** — if the placeholders are unexpanded, this is a checkout, so ask it.

The manifest is authoritative **only when it corroborates the running code**:
its `sha` must equal the SHA in the expanded stamp sitting beside that code. The
manifest describes the install's *state*, not any one code directory, so during
a staged update it still names the previous version while the new one is already
running. Unconditional manifest-first precedence would make the new build report
the old identity — and the launcher's own promotion check would then reject it
forever. This was found by the Codex review of PR #154, during implementation,
against a frozen design.

Accepted consequence: a freshly promoted version reports `source: "archive"` and
`tag: None` until the next launch. SHA and date still identify it exactly, and
the tag↔SHA mapping is public in the releases.

**That accepted consequence is superseded (2026-08-02, PR #188).** The
installer and the launcher now copy the release's `release.json` verbatim into
`versions/<tag>/` at stage time, and `build_info.py` reads that copy ahead of
the manifest under the same corroboration rule, reporting
`source: "release-file"`. The copy is written before the staged version ever
runs, so it cannot lag the code it sits beside: a trial build names its own tag
from its first session. The precedence above gains that file at the top and is
otherwise unchanged — the manifest remains the fallback for version directories
staged without a copy, which is how an install still on a pre-copy release
degrades for exactly one update cycle (documented, not engineered around, under
the single-user support boundary).

`version.txt` is deliberately plain `key: value` text rather than JSON: the
committed file needs a comment header (a raw placeholder looks broken to anyone
browsing the repo), and `export-subst` output is not JSON-escaped, so a JSON
envelope would silently constrain future placeholders to escape-safe expansions.

Identity surfaces in three places: a startup line in `data/logs/debug.log`
(bug reports arrive with the log), the `/health` endpoint, and — since
2026-08-02 (PR #190) — a version section on the settings page.

**That surfaces list is corrected and superseded (2026-08-02, PR #190).** It
originally named the header GitHub icon's tooltip and the browser title, and
rejected an app-settings page as spending permanent space on a string read
once per bug report. Two changes:

- The tooltip suffix is gone; the label is a plain "View this app on GitHub"
  again. Hanging version information off a hover on a repo link is an
  affordance failure — it was a stopgap chosen only because no page existed to
  own the display, and the settings page (PRs #181–#184) now does. The
  space objection died with it: the section costs nothing on a page the user
  opened deliberately.
- The browser-title claim was factually wrong. Dash Pages sets a per-page
  title on every navigation, so `document.title` never carried build identity
  in practice. The tab title stays deliberately unversioned — the correction
  is to this claim, not to the title.

Why not have CI commit a version file on every push: the commit changes the SHA,
so the file always describes its own parent; it doubles commit traffic; and it
forces constant fetch friction for the maintainer and for parallel agent
sessions. `export-subst` needs no commits and is never stale.

## 2026-07-19: All Mutable State Lives Under An Explicit State Root

Status: Accepted

Decision: `CSD_STATE_DIR` names the directory holding every mutable file —
`config.toml` and everything under `data/` (playlists, logs, preferences,
caches). Unset means the current working directory, so dev checkouts behave
exactly as before. Bundled read-only assets (`resources/benchmarks`) stop
resolving from the working directory and resolve relative to the installed
package instead, since they ship with the code. `source/utilities/paths.py`
centralizes both rules.

Why: without this split, versioned code directories cannot work at all. Running
the app from a fresh version directory would lose `config.toml` and `data/`;
running it from the state root would lose `resources/benchmarks`. An environment
variable keeps the contract explicit and testable, and lets the launcher — not
the app — own the choice of directories. (An early revision of the proposal
claimed the installer needed zero code changes; that claim was wrong and the
external review killed it.)

## 2026-07-19: The Installer Brings Its Own Toolchain, App-Locally

Status: Accepted

Installing the dashboard is one PowerShell command, and it brings everything it
needs with it: its own Python, its own package manager, the app, and a
first-run configuration file. Nothing outside the install folder is used or
disturbed, so uninstalling is deleting that folder and the desktop shortcut.
Installs ask no questions — as of the 2026-08-02 addendum below, the generated
configuration carries only the port the dashboard serves on, and where the
KovaaK's stats live is the app's own business.

Decision: installation is a PowerShell one-liner that fetches `get.ps1` from
`main`. That shim is deliberately trivial and permanently backward compatible —
resolve the latest release, fetch *that release's* `install.ps1`, run it,
nothing else — so the installer is always exactly the same age as the payload it
installs. Without the split, any installer change that merged ahead of its
release would run against a payload whose layout it no longer matched, and would
stay broken indefinitely if a release job failed.

The installer puts the **entire toolchain** under the install root
(`%LOCALAPPDATA%\CorporateSerfDashboard` by default): `UV_UNMANAGED_INSTALL`
places uv in the tree and it is invoked by absolute path,
`UV_PYTHON_INSTALL_DIR` plus `--managed-python` keep a managed CPython there
instead of silently selecting whatever Python the machine has, and
`UV_CACHE_DIR` keeps the cache inside too. No Python, uv, or registry state
outside the root is used or disturbed, so uninstall is deleting the folder and
the shortcut. Two files are written outside it by design: the desktop shortcut
itself, and `get.ps1`'s copy of the installer at
`%TEMP%\csd-install-<tag>.ps1`, which is inert once the install finishes and is
deliberately not cleaned up (the shim stays trivial); the README documents
deleting it.

The uv version is **per release, not per install**: installer and launcher read
the target release's `release.json` and provision that exact uv before syncing.
An install-time-frozen uv would brick the first update that bumps the pin — the
old binary rejects the new project, and `UV_UNMANAGED_INSTALL` disables uv
self-update — so the toolchain upgrade must ride the same transaction as the
code.

First run does not merely copy `example.toml`, whose `stats_dir = "Change me!"`
placeholder would crash the first launch. The installer locates the KovaaK's
stats directory itself (Steam's registry `InstallPath` plus
`libraryfolders.vdf`), confirms it with the user, validates that it exists, and
writes it into `config.toml`. It then **round-trips the generated config through
the installed app's own `load_config()`** and aborts loudly on failure, before
writing the manifest or creating the shortcut. Validating with `tomllib` alone
would only prove the file is syntactically TOML; the app's loader also proves
the schema is one the app accepts. A config the app cannot load must fail the
install loudly rather than surface later as a permanently broken first launch —
permanent because existing `config.toml` and `data/` are never touched again.

Why: the user's machine needs exactly one bootstrapped tool, acquired the way
rustup and uv themselves are distributed. Python and git are never
prerequisites. PyInstaller was rejected: unsigned executables trip SmartScreen
and AV heuristics (fatal for a gaming audience's trust), signing is a recurring
cost, every release would become a large re-download, and bundling
dash/plotly/dash-ag-grid assets under PyInstaller is a known hook-debugging time
sink. Revisit only if "run one command" ever becomes too much to ask.

Addendum (2026-07-20): the first-run `config.toml` now writes only the two
required fields, `stats_dir` and `port`. `polling_interval` (1000) and
`sens_round_decimal_places` (1) gained code defaults on `ConfigData`, so they
are no longer required fields and no longer seeded into the generated file —
`example.toml` still documents them for anyone who wants to tune them. The
round-trip through the installed app's `load_config()` still runs and must pass
with the two-field file.

Addendum (2026-08-02): the stats-directory detection, the `[Y/n]` confirm, the
manual-entry retry loop, and the stats-directory `Stop-Fatal` are all deleted,
so **installs are fully non-interactive** and the generated `config.toml` is
`port` only. `stats_dir` now lives in the app-owned `data/settings.json`, which
the installer never touches — one home, one writer — so its detection had
nowhere legitimate left to write: a `stats_dir` line in `config.toml` would only
be warn-logged and ignored. The app absorbs the consequences instead of the
installer: it starts and serves without a usable stats directory (initial scan
and file watchdog skipped, one log line naming what was configured, a hint on
Home — plain text until the settings page shipped, a link to it since), and an
app-side startup bootstrap that re-detects the directory
follows in the same proposal. Between the two, a fresh install runs empty until
the directory is set by hand. That bootstrap has since shipped — see the
2026-08-02 pinning-and-bootstrap entry, which supersedes this addendum on
stats-directory detection. The `load_config()` round-trip through the
installed app is unchanged and still gates the install, now against the
one-field file.

## 2026-07-19: PowerShell Writes UTF-8 Without BOM And Forward-Slash Paths

Status: Accepted

Decision: every machine-readable file written by the install/launch scripts
(`config.toml`, `install.json`, the `launch.ps1` bootstrap) is written UTF-8
**without** a byte-order mark, via `System.Text.UTF8Encoding($false)`, and every
path inside them uses forward slashes. The scripts target Windows PowerShell
5.1 — the shell the one-liner actually lands in on a stock Windows 11 machine.

Why: 5.1's `-Encoding UTF8` emits a BOM, and this repo's Python 3.14 `tomllib`
rejects both a BOM and raw `\` in TOML basic strings. Either alone yields a
config the app can never parse, which the never-touch-an-existing-config rule
would then make permanent. Both halves were verified empirically against this
repo's interpreter rather than taken from documentation.

This is a contract, not a style preference: do not "modernize" these writes to
`Set-Content -Encoding UTF8`, and do not let Windows-native backslashes reach a
generated TOML file.

## 2026-07-19: Updates Are Staged, Reversible, And Speak A Frozen Wire Contract

Status: Accepted

Decision: the desktop shortcut targets a stable bootstrap at the install root
(`launch.ps1`) that reads the manifest and delegates to the selected version's
launcher — nothing else. Per-tag directories get pruned (keep last two), so the
shortcut must never point into one. When the bootstrap itself must change, the
versioned launcher replaces it on a higher embedded marker by writing a
same-directory temp file, validating its marker and PowerShell syntax, then
renaming over it. Never truncate the live file in place: PowerShell keeps
executing the already-parsed body, so an interrupted in-place write leaves a
working session now and a bricked entrypoint for every launch after it.

The launcher is **single-instance** via a named mutex scoped to the install
root, held for the launcher+app lifetime. A second launch opens the browser at
the running instance and exits without updating, syncing, or touching the
manifest — atomic manifest writes protect one file, not a whole transaction.

Then it applies the manifest's policy:

- **`latest`** (default): query `releases/latest` on a short timeout; a
  different tag is downloaded and synced into a new per-tag directory but is
  **not promoted yet**. It starts as a pending activation, and the launcher
  polls `/health` until the child process is still alive *and* the response
  carries the expected full SHA and a per-launch token passed in by environment
  variable. A bare HTTP 200 is not proof of life: an already-running instance or
  an unrelated service holding the port can answer while the pending process
  never bound. Only then is the manifest atomically rewritten. On timeout or
  early exit the launcher starts the previous version and leaves the manifest
  untouched — a crashing release never becomes the recorded install. The gate
  deliberately does **not** require a tag match, because a build on trial is
  still described by the previous manifest and reports `tag: None` under the
  corroboration rule above. Any network or API failure fails open: run what is
  installed, offline-safe.
- **`pinned`** + `pinned_tag`: skip the update check entirely. A rollback
  install (`install.ps1 -Tag ...`) *writes this pin*; without it the next launch
  would immediately reinstall the bad release, making rollback a no-op. Undoing
  it is explicit: re-run the installer without `-Tag`.

**Wire contract v1.** A pinned or long-offline install may jump from the first
launcher straight to any future release, and the launcher performing that update
is always the *old* one. So everything an old launcher parses is a frozen,
versioned contract from day one: `release.json` and `install.json` both carry
`schema_version: 1`, and the v1 field set froze when the installer shipped.
Changes within v1 are additive-only. A breaking change bumps the version and
dual-publishes the v1 envelope for as long as v1 launchers may exist. A launcher
meeting an unknown `schema_version` — or any parse failure — runs the existing
install and says so loudly ("re-run the install one-liner"), because fail-open
alone would convert a contract break into *silent permanent stranding*: every
launch retries, fails, runs the old version, and never tells the user.

`install.json` deliberately carries **no uv field and no zip-prefix field**. The
launcher takes uv from the new release's `release.json` at update time, and
running the current version needs no uv at all — it starts the synced venv's
`python.exe` directly, which is offline-safe and makes the health gate and the
kill target the real server process rather than a wrapper. The zip's top-level
directory name is **discovered after extraction, never derived**: the named
asset keeps the "v" (`Corporate-Serf-Dashboard-v2026.07.19/`) while GitHub's
source-archive fallback strips it. Both scripts assert exactly one top-level
directory and verify the extracted stamp's SHA before syncing.

Rollback protects *code*; durable state is governed by a rule rather than
machinery. Releases must read older state (missing keys get defaults) and must
not rewrite user-authored files. The durable state is a handful of tiny,
schema-stable files, so a genuine format break is rare enough to be called out
in its PR with a manual step — the house convention at this user-base size.
State snapshot/restore was deferred on that basis.
(**Superseded on the schema-stability point only** by the 2026-08-11
durable-store stamp entry: those files now carry a `schema_version`, a release
that meets an unknown one refuses to write rather than relying on the manual
step alone, and pre-stamp releases are an unsafe rollback target. The
read-older-state and do-not-rewrite-user-files rules, and the deferral of
state snapshot/restore, are unchanged.)

Accepted limitation: a release that fails its health gate is retried in full —
download, sync, then the readiness timeout — on every launch until the next
release lands. Bounded by the near-daily release cadence; the escape hatches are
the rollback pin and waiting for the replacement release. Documented rather than
solved with a failed-tag marker.

## 2026-07-19: The App Binds Its Port Exclusively And Exits If It Is Taken

Status: Accepted

Decision: `source/app.py` creates and binds the listening socket itself
(`bind_server_socket`), sets `SO_EXCLUSIVEADDRUSE` where the platform has it,
and hands the bound socket to waitress as `serve(app.server, sockets=[sock],
threads=8)`. A failed bind prints an actionable message naming the port and
`config.toml`, then exits 1. Do not "simplify" this back to
`serve(app.server, host=..., port=...)` — that reintroduces the bug below.

Why: on Windows, a socket bound with `SO_REUSEADDR` (waitress's default for
sockets it creates) does not reserve the address. A second process can bind
the same `127.0.0.1:<port>` while the first is serving it, and Windows then
splits incoming connections nondeterministically between the two. The visible
symptom is a second copy of the dashboard silently answering some requests
with its own state — observed live during the release-launcher work, where
the launcher's `/health` token gate correctly refused to promote the build
but the user got a 120-second hang instead of an error. It is also the
long-standing "one dev run shadowing another on localhost" trap. POSIX
already refuses the second bind, so the flag is the Windows-only half of a
behavior we want everywhere.

Mechanism, verified against waitress 3.0.2: a socket passed through
`sockets=` is constructed with `bind_socket=False`, so waitress never binds
it, and `accept_connections()` calls `listen()` — hand it over **bound but
not listening**. Waitress then calls `set_reuse_addr()` on it unconditionally;
on an exclusively-bound socket that `setsockopt` fails with `WSAEINVAL`
(10022) and waitress swallows the error, so exclusivity survives. Confirmed
empirically: with the flag set, a second bind of the same port is refused
whether the second binder asks for a plain bind (`WSAEADDRINUSE` 10048),
`SO_REUSEADDR` (`WSAEACCES` 10013), or `SO_EXCLUSIVEADDRUSE` (10048).

Alternatives rejected: probing `/health` for a foreign responder before
binding (racy — the port can be taken between probe and bind — and blind to
non-app squatters like Steam on 8080); a launcher-side check (the launcher
already fails safe on a shadowed health answer, and with this change the
duplicate exits immediately, which its "exited" path already handles).

Scope: the `config.debug` Flask development-server path is unchanged; it is a
dev-only convenience. The bind happens immediately before `serve()`, so a
duplicate instance still does its ~2s of startup work before exiting.

POSIX footnote: binding the socket ourselves means waitress's pre-bind
`SO_REUSEADDR` no longer applies, and on POSIX that flag is what lets a
server rebind a port whose old connections are still in `TIME_WAIT`. A fast
restart there could now be refused. Windows is unaffected — verified that an
immediate rebind succeeds with a genuine `TIME_WAIT` pair on the port. We
accept this because nothing serves on POSIX: the app targets Windows and CI
runs `windows-latest` only. If that ever changes, set `SO_REUSEADDR` before
`bind()` on non-Windows platforms — on POSIX it permits the `TIME_WAIT`
rebind without letting a second live server share the port, so it restores
the old behavior without weakening the Windows guarantee.

Addendum, 2026-07-20: both loopback faces are bound, not just IPv4.
`bind_server_socket` now returns a list — `127.0.0.1` and `::1`, same port,
each claimed with the same `SO_EXCLUSIVEADDRUSE` treatment — and both go to
waitress as `sockets=`. The IPv4-only bind left the decision half-enforced:
on Windows `localhost` may resolve to `::1` first, so an unrelated process
holding the IPv6 face still captured every browser request to
`http://localhost:<port>/` while the dashboard sat unreachable on IPv4.
Observed live during the PR #153 session — another project's server held
wildcard `::` while the dashboard held `127.0.0.1`, and the browser got the
stranger's 404 page. (The squatter was *not* a `config.debug` run of this
app: werkzeug picks the address family with a colon heuristic, so its
`host="localhost"` always binds `AF_INET` `127.0.0.1` — verified against the
pinned werkzeug.) Claiming `::1` ourselves collapses that to the two outcomes
the original decision wanted: a specific bind takes routing precedence over
someone else's wildcard `::`, and if the face is genuinely taken the app
exits loudly instead of being silently shadowed.

Do not "simplify" the two sockets into one dual-stack `AF_INET6` socket with
`IPV6_V6ONLY=0`. That shape does not work here at all: v4-mapped addressing
applies only to wildcard binds, so a dual-stack socket bound to `::1` accepts
no `127.0.0.1` traffic whatsoever. Two explicit sockets are the only correct
shape, and they keep the per-face exclusivity semantics verified above.

Failure semantics stay deliberately two-bucket. Either face already taken
(`EADDRINUSE`) closes whatever was bound and takes the existing exit-1 path,
now with a message saying the port must be free on both addresses — a port
free on only one face is refused outright rather than half-served. IPv6
genuinely absent (`EAFNOSUPPORT` creating the socket, or `EADDRNOTAVAIL`
binding `::1`) logs one info line and serves IPv4 alone; on such a machine
`localhost` resolves to IPv4 anyway, so the ambiguity disappears with the
interface. Re-verified against waitress 3.0.2 that the multi-socket path
gives each socket the same treatment as the single-socket contract above:
`create_server` loops over `adj.sockets` constructing every `AF_INET`/
`AF_INET6` socket with `bind_socket=False`, calls the swallowed
`set_reuse_addr()` per socket, and calls `listen()` per socket in
`accept_connections()`; with two entries it returns a `MultiSocketServer`
driving both from one loop.

## 2026-07-19: Default Port Is 8050, Not 8080

Status: Accepted

Decision: The example config (`example.toml`) ships with `port = 8050`. The
app itself has no built-in default — `port` is a required config field served
through waitress — so the example file is the only default we own.

Why: 8080 is one of the most contended ports on end-user machines; Steam in
particular holds it whenever it is running, and this app's audience is
KovaaK's players, who all run Steam. 8050 is the Dash convention (`app.run()`
default), so it signals "Dash app" to anyone inspecting the port, and its
only common occupant is *other* Dash apps run with defaults — a rare
collision for this audience. No port choice defends against Windows
Hyper-V/WSL2 excluded-port-range reservations, which land semi-randomly;
the `port` config setting remains the escape hatch for any collision.

Migration: none in-app (single-user convention — no compat shims). Existing
installs keep whatever their `config.toml` says; only fresh copies of
`example.toml` pick up 8050.

## 2026-07-18: Accept Dash's First-Request Pages Race Instead of Warming the App

Status: Accepted

Decision: The browser-console noise on the first page load after a server
start — a `TypeError: Cannot read properties of undefined (reading 'apply')`
from `handleClientside`, plus a flood of ~86 "ID not found in layout" entries
in the dev-tools overlay — is a known upstream Dash defect. We accept it and
do not work around it. Treat it as expected baseline noise during browser
checks; reload the page before judging whether the console is clean.

Why: Dash's `enable_pages()` registers its page router as a `before_request`
hook (`dash/dash.py`, in `router_sync`/`router_async`). The hook sets its
`_got_first_request["pages"]` guard flag *before* it finishes its work, and
takes no lock:

```python
if self._got_first_request["pages"]:
    return
self._got_first_request["pages"] = True
...   # builds validation_layout, registers the document.title clientside callback
```

Inline clientside function bodies are injected into the index HTML at render
time. Under a threaded server — Waitress with `threads=8` in production,
Flask's threaded dev server when `debug = true` — a concurrent early request
sees the flag already set, returns immediately, and serves an index page whose
script block is missing, while `/_dash-dependencies` still advertises the
callback. The renderer looks the function up, gets `undefined`, and calls
`.apply` on it. `validation_layout` is populated in the same unfinished hook
body, which is why the "ID not found in layout" flood appears alongside: one
root cause, two symptoms.

Measured 2026-07-18 on dash 4.4.0: eight simultaneous first requests produced
**seven of eight** renders missing the script; every later render has it. A
browser triggers it because it opens several connections at startup.

The missing function is Dash's own `_pages_dummy` `document.title` setter, not
application code — all six of our clientside callbacks register correctly every
time. It is not a dash-extensions defect either: `DashProxy._setup_server`
correctly takes a `setup_server_lock`, and plain `dash.Dash` races identically
(measured: 7/8 for both, in a minimal app with no dash-extensions involved).
It reproduces on dash 4.3.0 and 4.4.0 alike, so it is not a regression from the
PR #146 dependency upgrade.

### Reproducing it requires a wide enough race window

Two conditions must both hold, which is why a casual minimal repro shows
nothing and reports "works fine":

1. **`suppress_callback_exceptions` must be at its default `False`.** When it
   is `True`, Dash skips the whole `validation_layout` block inside the pages
   router (`dash/dash.py`, the `if not self.config.suppress_callback_exceptions:`
   guard) — which is the slow part of the hook. The window collapses to
   near-zero and the race effectively never fires. This app leaves the setting
   at its default.
2. **Page layouts must be expensive enough to matter.** That block calls every
   registered page's layout function to build `validation_layout`. The window
   is as wide as those calls take. A `html.Div("hi")` page closes it instantly;
   this app's real page layouts hold it open long enough to lose 7 of 8 races.
   A minimal repro reproduces once a page layout is given real work to do
   (a 0.4s sleep was sufficient).

Practical consequence: **do not expect an upstream fix to arrive on its own.**
Most small Dash apps and most upstream tests satisfy neither condition, so the
bug is invisible in exactly the places that would catch it. Absent someone
filing it (not done as of 2026-07-18), assume it survives future Dash releases
rather than treating a version bump as a likely cure. Re-check cheaply after a
Dash upgrade: load the app once, reload, and see whether the first-load console
noise is gone.

Impact is cosmetic and self-healing: on an affected load `document.title` shows
the app-level title instead of the page title, and any reload fixes it. A
workaround for someone else's bug is not worth carrying for that.

"No feature is affected" is measured, not assumed. Exercised on a load
confirmed to have lost the race — six of seven clientside functions registered,
86 "ID not found in layout" entries, the app-level title — the Home page still
rendered fully, the Plotly graph mounted (a beat later than usual), server
callbacks fired and returned 200, and toggling the x-axis radio round-tripped
end to end and updated the figure. The only observable defect was
`document.title`. The "ID not found in layout" flood is the renderer reporting
a transient state it recovers from, not callbacks being dropped.

Validated mitigation, should this ever become worth fixing: prime the app with
one synchronous in-process request before serving — `with
app.server.test_client() as c: c.get("/")` in `main()`, ahead of `serve(...)` /
`app.run(...)`. Measured under the same eight-way concurrency test, this took
seven-of-eight failures down to zero. Deliberately not applied.

## 2026-07-18: Accept dash-ag-grid's `columnSizeOptions` Console Warning

Status: Accepted

Decision: The AG Grid console warning `invalid gridOptions property
'columnSizeOptions'`, emitted once per grid mount on the Playlists and
per-playlist scenario pages, is benign upstream noise from the dash-ag-grid
wrapper. We accept it, keep passing `columnSizeOptions`, and do not work
around it. It is distinct from the first-request pages race above: that noise
appears only on the first load after a server start, while this warning
appears on every mount of either grid.

Why: dash-ag-grid folds its remaining props into AG Grid's `gridOptions`
after stripping its own Dash-side props via a hardcoded list
(`PROPS_NOT_FOR_AG_GRID` in the wrapper's `src/lib/fragments/AgGrid.react.js`).
That list contains `columnSize` but not `columnSizeOptions`, so the prop
leaks through and AG Grid's validator flags an unknown key. Our usage is
correct — both are documented top-level `dag.AgGrid` props, and the wrapper
genuinely consumes `columnSizeOptions` (it destructures `keys`, `skipHeader`,
`defaultMinWidth`, `defaultMaxWidth`, and `columnLimits` from it to drive
`autoSizeColumns`/`sizeColumnsToFit`; verified in the installed 35.3.0
bundle). The upstream fix is adding one string to that list.

Correction to the record: the warning was believed fixed by the PR #146
upgrade to dash-ag-grid 35.3.0. Re-verification on a bare `main` baseline
(2026-07-18, during the PR #153 work) showed it still present, so treat it as
expected noise on 35.3.0, not a regression signal.

Alternatives rejected:

- Dropping the prop silences the warning but loses the `keys`/`skipHeader`
  autosize configuration — real behavior traded for cosmetics.
- AG Grid's blanket switch `suppressPropertyNamesCheck` would silence it —
  the bundled v35 validator still honors the flag — but the option is
  deprecated since v33 (AG Grid's deprecation message calls it redundant now
  that `context` exists for arbitrary user data), so enabling it trades the
  invalid-property warning for a deprecation warning while also disabling
  the check that catches real typos in our own gridOptions and colDefs.
- Re-implementing autosizing through a clientside grid-API call just to avoid
  the prop is a workaround for someone else's cosmetic bug — the same bar the
  pages-race entry above declines to meet.

Consequences: treat the warning as expected baseline noise during browser
checks. Not filed upstream as of 2026-07-18, so do not assume a version bump
fixes it; re-check cheaply after a dash-ag-grid upgrade by loading
`/playlists` and looking for the warning. If an upgrade makes it disappear,
mark this entry superseded.

## 2026-07-17: Playlist Import Falls Back to Evxl Exact By-Code

Status: Accepted

Decision: KovaaK's `/playlist/playlists?search=<code>` stays the primary lookup
for playlist import. Whenever it fails to produce exactly one usable record —
zero after the null-drop validator, or more than one match — import falls back
to Evxl's exact `playlist-by-code` endpoint
(`https://api.evxl.app/kovaaks/playlist-by-code?shareCode=<code>`) before
refusing. If the fallback also fails, the user sees the same refusal message as
before.

Why: KovaaK's search has a null-hydration quirk — for some real, public
playlists it counts the match but returns a `null` record, which the
`ignore_null_playlist_items` validator drops, so a valid playlist looks like
zero results (observed: `KovaaKsCarryingGodlikeTile`; details in
`kovaaks_api_notes.md`). There is no first-party KovaaK's by-code endpoint, and
Evxl's by-code lookup resolves arbitrary community playlists exactly.

This is the app's first *runtime* dependency on Evxl; previously Evxl was used
only by the offline `scripts/benchmark_importer`. First-party KovaaK's data
stays preferred on the happy path — Evxl's copy is cached upstream (can be days
stale) and its case-strict HTTP 400 on mis-cased codes would be a worse
default — so Evxl is consulted only when the first-party search cannot resolve
the code cleanly. The stored code is always the canonical `playlist_code` from
whichever source resolved it, never the pasted input.

## 2026-07-16: Warm Playlist Percentiles With One Polite Background Worker

Status: Superseded in part by the
[2026-08-03 quiet-layer entry](#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy):
the fatal-state toast for an unknown username was removed in PR #196; the
overview's status line and a WARNING log carry it. Everything else stands.

Decision: After startup finishes ingesting local runs, one app-lifetime daemon
worker warms the rank and leaderboard-total caches used by the Playlists
overview. Its queue contains only played scenarios from visible playlists,
grouped to finish recently played playlists first. The worker is sequential,
leaves a two-second politeness gap between network items, and blocks on a
condition variable when idle. Unhiding or importing a playlist prepends that
playlist's played scenarios and wakes the same worker; hiding or deleting does
not cancel already queued work.

Queue duplication is intentionally cheap rather than prevented. Every dequeue
rechecks the disk caches and a session outcome map, so duplicate names from
overlapping playlists, repeated imports, and hide/unhide spam skip without
network work. A scenario is fresh enough for the worker when it has a fresh
UNRANKED cache entry, or a fresh RANKED entry plus a fresh leaderboard total.
The overview's display rule is weaker and monotonic: it may read entries of any
age, but it shows aggregate percentiles only after every played scenario in the
playlist is display-resolved. Until then both aggregate cells show an honest
`n/total cached` placeholder; a fully resolved all-UNRANKED playlist shows
`N/A`, not a pending state.

Interactive rank work always takes priority. The shared API activity signal
keeps separate monotonic timestamps for interactive lookups (cache hits
included) and successful network responses. The worker waits for an
interactive quiet window, while outage backoff wakes early only after evidence
of a real network success. The worker calls the lower-level resolve, rank, and
total operations so it can classify failures without the UI service's UNKNOWN
flattening. Before caching UNRANKED it requires one positive username
validation per session; an API-confirmed unknown username stops the whole
queue and produces one UI notification. Connection errors, 5xx responses, and
post-retry 429s tail-requeue with escalating global backoff; read timeouts and
permanent failures become terminal for that session. Three transient attempts
per name are allowed. A restart reconstructs work from cache freshness rather
than persisting queue state.

The Playlists page reads the worker through an immutable snapshot. While queued
or in-flight work exists it shows `Updating percentile data: N remaining
(~ETA)`, using unique non-terminal names and recent pace; outage backoff adds a
paused/retry time and fatal state remains visible. A one-second interval
rebuilds the normal cache-only overview rows and disables itself only after one
final idle rebuild. `Interval.disabled` has one callback owner. That callback
observes a monotonic enqueue generation and is also driven by the page's row
refresh store, so work enqueued after idle re-arms the browser interval and an
older snapshot cannot disable a newer re-arm. Interval-driven cache reads pass
`record_activity=False`; otherwise the reporting loop would continuously mark
the user active and postpone the worker it reports on.

Why: A cold overview previously showed incomplete percentile aggregates only
for scenarios the user happened to open, which made cross-playlist comparisons
biased and unstable. Bulk warming the full play history would spend API budget
on data no overview consumes, while parallel fetching would add avoidable load.
The played-visible queue plus all-or-nothing display makes each completed value
trustworthy, and the background status makes a 15-minute cold fill visible
without blocking any route.

Consequences: `percentile_warmup_enabled` disables only this worker, and an
empty `kovaaks_username` keeps startup and enqueue hooks fully offline.
Interactive Home and playlist-scenario refreshes remain available. The queue,
pace, backoff, and generation state are process-local; cache files remain the
durable data plane and retain their existing atomic-write and monotonic-rank
rules. A separate background TTL and negative leaderboard-resolution cache are
deferred levers. Shipped across PRs #129, #130, #132, and #133.

## 2026-07-13: KovaaK's Timeout Is 30s (Configurable); Read Timeouts Are Not Retried

Status: Accepted

Decision: All KovaaK's API requests share one timeout, default 30 seconds,
configurable via `kovaaks_api_timeout_seconds` in `config.toml` and applied at
app startup through `api_service.set_request_timeout()`. `_get_with_retry`
retries only `requests.ConnectionError` (which covers `ConnectTimeout`); a
`ReadTimeout` fails immediately instead of being retried.

Supersedes: the `requests.Timeout` clause of the 2026-04-28 transient-retry
decision. The `429`/`Retry-After` policy and the `ConnectionError` retry from
that entry stand, and the 2026-06-21 keep-the-hand-rolled-retry decision is
reaffirmed, not revisited.

Rationale: measured 2026-07-13 during a KovaaK's slow spell,
`/leaderboard/scores/global` latency ranged 9–28s while responses stayed
valid — a Postman probe succeeded after ~28s, and in-app fetches succeeded at
9.0–9.4s, just under the old hardcoded 10s wire. With a 10s timeout every
attempt during the spell died, and because the stale-rank fallback is
deliberately read-only (see the 2026-07-12 entry), the same expired cache
entry re-timed-out on every page open — one expired scenario added ~20s to
every playlist load until a fetch succeeded. A read timeout also does not
cancel the server-side query, so the old immediate retry doubled KovaaK's
load for almost nothing (2 of 63 retries succeeded that night); a connection
error, by contrast, means the request never reached the server and remains
safe to retry. 30s clears the observed worst case, and the config knob is the
escape hatch if slow spells drift past it.

Constraints:

- Deliberately a single timeout value — no connect/read split and no
  urllib3 `Retry` adoption (the 2026-06-21 entry holds the full migration
  analysis). Beyond that entry's reasons: the per-retry warnings in
  `_get_with_retry` are the primary forensic log, and the benchmark importer
  depends on its per-call `attempts`/`backoff_seconds` knobs, which
  `requests` cannot express per request through adapter-mounted `Retry`.
- The importer shares the helper, so its retry schedule now governs only
  connection errors and 429s; a read timeout fails the sharecode
  immediately.

## 2026-07-12: Rank-Fetch Failure Degrades To The Last Cached Rank

Status: Superseded in part, for the passive red/yellow toasts of the
three-tier toast model in Constraints below, by the
[2026-08-03 notification-layer entry](#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)
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

## 2026-07-11: The Playlist Overview Is The Playlist Management Surface

Status: Accepted

Decision: The `/playlists` overview is the single surface for managing
playlists and benchmarks. It lists every loaded playlist with local
aggregates and hosts all management controls — per-code show/hide, share-code
import, and delete for user playlists — rather than spreading them across a
Settings modal and the filesystem. Concretely:

- **Visibility is a plain per-code show-list**, not file state. It is
  persisted as the `shown_playlists` key in `data/preferences.json` (now
  `data/playlist_visibility.json`), and a playlist is visible iff its code
  is in the list — uniformly for bundled benchmarks and user playlists. A
  missing (or unusable) preferences file yields a first-run seed — the
  bundled `DEFAULT_VISIBLE_CODES` (Voltaic + Viscose) plus every code loaded
  from the user root — **without writing**; the file materializes on the
  first show/hide, and an existing file is authoritative including an empty
  list (everything hidden on purpose).
  Importing a code appends it (importing is the intent to see); hide removes,
  unhide re-adds. `get_visible_playlist_selector_options()` is the single
  visibility filter every option list consumes (Home filter, Journey picker,
  overview), so they cannot disagree. Hidden playlists still load, their
  `/playlists/{code}` routes still resolve, and rank overlays still draw.
- **The full bundled benchmark library ships flat under
  `resources/benchmarks/`** and is scanned in full at startup, with only the
  curated defaults visible. The whole root is pipeline-managed (machine
  generated by `scripts/benchmark_importer/`; don't hand-edit); the
  bundled-invariant test asserts every committed file carries rank data.
  Enabling a benchmark is one unhide click, not a copy-and-restart, and app
  updates refresh the library automatically.
- **Delete exists only for user playlists** (`data/playlists/` files). It
  unlinks the file recorded for that code at load/import time (not a
  reconstructed name, so hand-dropped filenames are handled), drops the store
  entry, and forgets the code's show-list membership so `preferences.json`
  does not accumulate dead codes. Bundled benchmarks cannot be deleted —
  hiding is the equivalent, which forecloses the delete-then-reimport
  degradation (a share-code re-import comes back rank-less).
- **Startup stays read-only.** A `data/playlists/` file whose code is already
  served by a bundled benchmark (a pre-#90 copy-to-activate leftover) is
  skipped with a warning; the overview surfaces those dead copies with an
  in-app cleanup action instead of deleting anything at load.

Why: The bare `/playlists` route was a name-only dropdown that answered
nothing about where to direct attention, and shipping the whole benchmark
library would have flooded every dropdown with 100+ rows. Visibility protects
browsing and first-run focus (search only helps when you already know the
name). Managing playlists by editing files ("copy a JSON in, restart") is the
opposite of "the user interacts with the app, not the filesystem." The
single-writer/single-user assumption (the user is also the library curator)
lets visibility be a plain show-list instead of a richer defaults-aware store.

Consequences: This entry supersedes the `resources/playlists/` bundled-root
path in the 2026-06-22 and 2026-07-07 entries: the bundled root is now
`resources/benchmarks/`. Accepted tradeoff: a future default-worthy benchmark
(e.g. a Voltaic S6) arrives hidden, because a plain show-list has no
live-evaluated notion of "new default." This is acceptable while the app has
one user who is also the curator — a new benchmark only enters
`resources/benchmarks/` because that user ran the importer and committed it,
and unhiding it is one known click. The rejected richer design (a `shown`
list plus a `hidden` list plus a live-evaluated defaults constant, letting
shipped defaults auto-surface) remains the known, backward-compatible upgrade
path if the app is ever distributed to non-curator users; it was declined
here as machinery defending against a surprise this app cannot currently
produce. Separately, deleting the three legacy top-level Viscose files during
the library flip changed 19 served thresholds; the canonical values are a
fresh importer pull taken at flip time (OQ-9), because KovaaK's is
authoritative for thresholds and the served top-level values were
demonstrably stale.

## 2026-07-11: Match Scenario Names On Their Stripped Form

Status: Accepted

Decision: Scenario-name matching is exact on **stripped** names, and the strip
is enforced at two boundaries: the CSV run parse
(`source/kovaaks/data_service.py`, `scenario = line.split(",", 1)[1].strip()`)
and a `field_validator` on `Scenario.name` in `source/kovaaks/data_models.py`.
The model validator normalizes every path that builds a `Scenario` — runtime
share-code import, bundled/user playlist file load
(`PlaylistData.model_validate_json`), and the benchmark importer's output —
so a playlist scenario name always joins `kovaaks_database` (which is keyed by
the CSV-stripped names) under the same key. The validator is lenient on an
empty result (a whitespace-only name becomes `""` rather than raising, unlike
the sibling `code` validator) because a blank scenario name is an odd upstream
quirk, not a store key, and must not reject the whole playlist import.

Why: Every scenario lookup is exact-match — `is_scenario_in_database` (dict
membership), `get_rank_data_from_playlist_code` (`!=` compare),
`get_scenarios_from_playlist_code` (verbatim) — while `kovaaks_database` keys
are always stripped. A padded name from the KovaaK's playlist API therefore
never resolved local runs / PB / rank overlays. Padding is observed, not
hypothetical: PR #97 found real corpus files with one- and five-space paddings
from the KovaaK's benchmark API. The model boundary was chosen over a call-site
strip (which would fix only one of the three entry points — the #97
whack-a-mole) and over normalize-at-lookup (which would spread the invariant
across every comparison and dict lookup); it is a single choke point that
mirrors the existing `PlaylistData.strip_and_require_code` precedent.

Consequences: The two enforcement points must agree — drift between the CSV
parse strip and the `Scenario.name` validator silently recreates this bug
class, so a future change to the normalization strategy must update both
together (a shared `normalize_scenario_name()` helper was considered and
declined as premature; this entry is the cheaper drift guard). Nothing bakes
the association in: `kovaaks_database` is rebuilt from CSVs each startup and the
validator re-runs on every playlist file load, so the match key is re-derived
at runtime on both sides and changing strategy re-keys everything on the next
startup. Name-keyed persisted caches (leaderboard-id / rank) tolerate a
strategy change by design — a miss refetches, bounded by the 168 h TTLs. The
only one-way loss is that imported playlist JSON persists the stripped name,
discarding original padding (semantically void whitespace, recoverable by
re-import from the code). The benchmark importer's own `.strip()` at
`scripts/benchmark_importer/script.py` is now redundant defense-in-depth and is
left in place. Shipped in PR #100.

## 2026-07-11: Humanize The Absolute Timestamp Format

Status: Accepted

Decision: The absolute "on-hover / in-title" timestamp adopts a GitHub-shaped, humanized format instead of the previous `%Y-%m-%d %I:%M:%S %p` (which rendered `2026-04-12 07:04:22 PM`). Two variants: staleness surfaces (home last-played tooltip, playlist/scenario grid tooltips, plot-title `updated:`) show `Apr 9, 2026, 7:04 PM` (no seconds); the per-run scatter hover shows `Apr 9, 2026, 7:04:22 PM` (seconds kept). Format rules: abbreviated English month from a hardcoded array (never `%b`/`calendar.month_abbr`), unpadded day, 4-digit year, unpadded 12-hour hour with `0 → 12` (midnight `12:xx AM`, noon `12:xx PM`), zero-padded minutes/seconds, uppercase space-separated AM/PM, browser/local time with no timezone suffix. The Python side is `format_absolute_timestamp(dt, *, include_seconds=False)` in `source/utilities/utilities.py`; the JS side is `dagfuncs.absoluteTime` in `assets/dashAgGridFunctions.js`, which mirrors the no-seconds variant. The relative string, the `Never`/`—` sentinels, the epoch-seconds plumbing, and the dotted-underline tooltip affordance are all unchanged.

Why: Market research (GitHub, Discord, Slack, Steam, AWS Cloudscape) confirmed the relative-primary + absolute-on-hover pattern is standard, but the old absolute string deviated from every comparator — a zero-padded 12-hour hour (no consumer app pads it), seconds on staleness surfaces (GitHub/Discord/Cloudscape all drop them), and a machine-register ISO date glued to a consumer-register AM/PM time. The GitHub shape reads as one register. Seconds are kept only on the run-level hover because they cross-reference KovaaK's second-stamped stats CSV filenames. The format is hand-rolled (not `strftime`/`toLocaleString`) for locale independence (hardcoded month array) and because no cross-platform strftime code exists for an unpadded hour (`%-I` is POSIX-only, `%#I` Windows-only).

Consequences: Python↔JS parity is held by this spec and by hand — there is no JS test harness — so the two implementations must be kept in sync (both carry a comment pointing at the other). This supersedes only the exact-format aspect of the 2026-06-21 and 2026-06-30 entries; their behavioral decisions stand.

## 2026-07-09: Load Configuration Lazily At Application Startup

Status: Accepted

Decision: Configuration is loaded and cached through `get_config()` instead of
at module import. `main()` owns the initial load and translates expected file,
decode, TOML, and validation failures into the existing concise startup error
before loading playlists or initializing runtime services. Other modules resolve
the cached configuration only inside function bodies.

Why: Import-time loading forced pytest to overwrite the real repo-root
`config.toml`, keeping its backup only in process memory. Abnormal termination
could permanently replace a user's configuration, and concurrent test sessions
could corrupt each other's backup/restore chain. A lazy production accessor makes
modules import-safe and gives tests an in-process seam without adding a test-only
environment-variable override.

Consequences: Tests monkeypatch the config loader and clear the accessor cache;
they never modify the real `config.toml`. `get_config()` propagates load errors,
while the executable startup boundary alone prints the user-facing message and
exits. Playlist loading happens in `main()` after configuration validation so a
bad config still produces exactly one clean error with no prior warning output.

## 2026-07-09: Accept Unsynchronized In-Memory Stores (Single-Writer)

Status: Accepted

Decision: The module-global in-memory stores in `source/kovaaks/data_service.py`
(`kovaaks_database`, `run_database`, and `playlist_database`) remain
unsynchronized. No lock is added. This is a reviewed acceptance, not an
oversight.

Why: Design review (2026-07-09) verified the structural guarantees that bound
the risk. After startup, the watchdog observer thread is the only writer to
`kovaaks_database`/`run_database` (the startup bulk load is single-threaded,
before the observer and server exist), so writer-writer corruption cannot
occur. The top-level `kovaaks_database` dict is read via GIL-atomic lookups;
the one reader that iterates it (`get_scenario_stats_snapshot`, PR #78)
snapshots with a single C-level `list()` call that a concurrent insert cannot
break, and PR #78 also made the writer replace `ScenarioStats` objects instead
of mutating fields in place, so a reader that binds one sees field-consistent
values. The remaining exposure is server-thread readers iterating nested
`sortedcontainers` structures (and the journey page walking `run_database`)
mid-`add()`: worst case is a skipped or duplicated point, or a rare exception,
in one render. Dash contains callback exceptions and no path writes torn state
back. Self-healing has two cadences: home-page consumers re-render on the
polling interval, so races there clear within about a second; the journey,
playlist grid, and playlist overview pages rebuild store-derived data only on
navigation or control interaction (their intervals only re-tick relative
timestamps), so a raced render there can persist until the next interaction.
Both cadences stay within the accepted class — a wrong or failed render, never
corrupted state. The load-before-notify
ordering in `_enqueue_after_loading` guarantees a drained message's run is
already fully visible in the stores. `playlist_database` carried the same
class between server threads (the import callback's insert vs. `.values()`
iterations under Waitress's worker pool) until PR #78 converted its iterating
readers to the same `list()` snapshot pattern, leaving only atomic containment
checks and single-key lookups exposed — which are safe. A coarse lock
was rejected because it imposes permanent accessor discipline — silent when
violated — against a self-healing one-frame glitch; a single-writer ingest
redesign was rejected as not worth reworking the load-before-notify contract
on its own.

Consequences: Two lists govern when this decision ends. Hazard triggers (add
synchronization, or implement the single-writer ingest redesign): a store-race
exception or corruption actually observed in logs; a genuine second writer to
these stores (for example runtime playlist reload or a background recompute);
a move to free-threaded (no-GIL) CPython, which weakens the per-bytecode
atomicity and pure-Python `sortedcontainers` invariants this acceptance leans
on. Resolving events (the problem dissolves as a side effect): a SQLite
migration, or an ingest rework undertaken for other reasons (which should then
adopt the single-writer design). For the SQLite path, file-backed WAL is the
chosen shape — a design choice, not the only technically viable one. In-memory
variants can be shared across threads (a single serialized connection via
`check_same_thread=False`, or one shared database via `cache=shared` or SQLite
3.36+'s `memdb` VFS), while a naive connection-per-thread `:memory:` setup
silently gives each thread a separate empty database. The shared variants are
rejected because WAL does not support in-memory databases, so each of them
forfeits concurrent snapshot-isolated readers and reintroduces reader-writer
serialization or a discouraged mode; file-backed is also the only shape that
serves the persistence and startup-scan justifications that would motivate the
migration in the first place. Run History adds more reader iteration over `run_database` but no
writers; it stays within this acceptance. New readers that iterate a shared
store dict should follow the established snapshot pattern — one C-level
`list()` call before iterating (see `get_scenario_stats_snapshot`). That
pattern is deliberately not extended to the nested `sortedcontainers`
structures, where `list()` is itself Python-level iteration and offers no
atomicity; those remain the accepted self-healing class above.

## 2026-07-08: Judge Score-Threshold Notifications Against The Previous PB

Status: Accepted

Decision: Score-threshold notification verdicts compare in score space against
the personal best the run was chasing:
`score >= previous_high_score * score_threshold_percentage / 100`. The overlay
line still uses the current post-run personal best for the same percentage
setting.

Why: The toast already displays the run's percentage against the previous PB.
Using the post-run PB for the verdict made goals above 100% unreachable,
because a new PB moved the target upward before the run was judged. Keeping the
comparison in score space preserves the exact-threshold `>=` boundary; the
displayed-ratio form can round `820 / 800 * 100` below `102.5` and turn an
exact hit into a failure.

Consequences: Goals above 100% now pass when a run beats the previous PB by
the configured margin. New-scenario and new-sensitivity events still carry
`previous_high_score=None`, so they remain verdict-less. Backlog summaries keep
judging only the batch's latest run; fuller historical pass/fail review belongs
to run history.

## 2026-04-27: Use JSON Files For Runtime API Caches

Status: Accepted (cache root superseded by the 2026-07-11 cache-relocation
entry: caches now live under `data/cache/`)

Decision: Store current API cache data as JSON files under `cache/`.

Why: The current cache use cases are simple key-value lookups with short or medium TTLs. JSON keeps the implementation transparent, easy to inspect, and low-friction.

Consequences: Cache reads must tolerate missing, malformed, stale, or partially-written files. Cache writes should be atomic where practical. Reconsider SQLite when we need rank history, multi-record queries, or stronger transactional guarantees.

## 2026-06-22: Keep User Runtime Data Under `data/`

Status: Accepted (bundled-root path superseded in part by the 2026-07-11
playlist-overview entry: bundled playlists now live under
`resources/benchmarks/`, not `resources/playlists/`; the deferred cache move
shipped in the 2026-07-11 cache-relocation entry)

Decision: Store user/runtime app data under a repo-local ignored `data/` directory. New runtime logs belong under `data/logs/`. Existing API caches remain under `cache/` until a separate migration moves them.

Why: Logs are runtime artifacts, but they are not cache. A dedicated `data/` root keeps future runtime state such as logs, imported/custom playlists, and an eventual SQLite database grouped in one place without mixing it with source-controlled resources.

Consequences: Keep bundled/default playlists under `resources/playlists/`. Put future user-imported or user-created playlists under `data/playlists/`. If the existing API cache moves from `cache/` to `data/cache/`, handle it as a dedicated compatibility migration instead of silently changing paths.

## 2026-07-07: Use Playlist Codes As Playlist Identity

Status: Accepted (bundled-root path superseded in part by the 2026-07-11
playlist-overview entry: the loader's first root is now
`resources/benchmarks/`, not `resources/playlists/`)

Decision: Treat KovaaK's playlist `code` as the app's playlist identity everywhere: the in-memory `playlist_database` key, route value, selector value, import duplicate check, and import filename suffix. Playlist names are display-only labels. Selectors receive finished `{label, value}` options from the service; labels become `Name (CODE)` only when duplicate names need disambiguation.

Why: KovaaK's playlist names are not unique, so name-keyed storage silently dropped later same-named playlists and made those playlists unreachable even by their stable code routes. Codes are already user-facing through share-code imports and `/playlists/{playlistCode}` URLs, so they are the stable identity to preserve.

Consequences: The startup loader scans top-level JSON files from `resources/playlists/` first and `data/playlists/` second, sorted within each root by `(filename.casefold(), filename)`. The first occurrence of a code wins; duplicate-code files are skipped with a warning naming both files, and startup warnings are buffered until the UI mounts so they become visible notifications instead of being dropped outside Dash callback context. This supersedes the 2026-07-05 proposal call that user-root files should win: the final rule is bundled-wins because bundled benchmark files carry rank data and share-code imports do not. New imports write atomically to `data/playlists/{sanitized name} [{code}].json`; importing an existing code is refused with a user-visible message naming the existing playlist. The `data/playlists/` root may be absent on clean checkouts and is created on first import. Legacy user imports under `resources/playlists/` are a clean break, not migrated; owners preview and remove ignored legacy files manually with `git clean -Xn resources/playlists` then `git clean -Xf resources/playlists`, re-importing anything still wanted by share code.

## 2026-04-27: Treat `total-play` As Metadata Only

Status: Accepted

Decision: Use `/user/scenario/total-play` only to hydrate or upsert scenario metadata such as `scenarioName -> leaderboardId`.

Why: The endpoint can lag behind current leaderboard scores and ranks. `/leaderboard/scores/global` is the authoritative source for current rank.

Consequences: Current-rank lookup should not trust score or rank data from `total-play`. The endpoint remains useful for cache initialization and metadata discovery.

## 2026-04-27: Keep KovaaK's API Details Behind `ScenarioRankInfo`

Status: Accepted

Decision: UI code consumes `ScenarioRankInfo` and should not know which KovaaK's endpoint produced the data.

Why: Endpoint details, fallback behavior, cache rules, and expected API failures belong in the service layer. This keeps Dash callbacks focused on rendering.

Consequences: Expected KovaaK's API/domain failures should become `ScenarioRankInfo(status=UNKNOWN, error_message=...)` in `api_service.py`. UI code can render `RANKED`, `UNRANKED`, or `UNKNOWN` without duplicating endpoint logic.

## 2026-04-27: Prefer Steam ID Matching When Configured

Status: Accepted

Decision: When `steam_id` is configured, prefer it for leaderboard identity matching. If Steam ID matching fails but exact username matching succeeds, keep the rank result and surface a warning.

Why: `usernameSearch` can return partial matches. Steam ID is the strongest identity check, but a mistyped Steam ID should not hide otherwise valid exact-username rank data.

Consequences: The warning is transient and derived from current config each time rank info is returned. It should not be persisted in rank cache.

## 2026-04-27: Make Leaderboard Total Enrichment Best-Effort

Status: Accepted

Decision: Leaderboard total lookup should never invalidate a valid rank or unranked result.

Why: Total players and percentile are enrichment data. If total lookup fails because of network errors, malformed responses, validation failures, or cache I/O issues, showing the valid rank alone is better than falling back to `N/A`.

Consequences: `_with_leaderboard_total()` catches expected total-enrichment failures, logs them, and returns the original `ScenarioRankInfo`.

## 2026-04-29: Cache Leaderboard Totals For One Week

Status: Accepted

Decision: `leaderboard_total_cache_ttl_hours` defaults to `168`, matching `scenario_rank_cache_ttl_hours`.

Why: Leaderboard total player counts are expected to increase slowly. For large leaderboards, a mildly stale total count changes displayed percentile by less than the UI's two-decimal precision in most cases, while avoiding daily cold-cache total fetches across every playlist scenario.

Consequences: Total-count freshness remains configurable. If users notice stale total counts causing misleading displays, revisit the TTL or add a targeted refresh flow.

## 2026-04-27: Use The Midpoint Percentile Formula

Status: Accepted

Decision: Derive percentile with:

```python
percentile = ((total_players - rank + 0.5) / total_players) * 100
```

Why: This matches the KovaaK's-style percentile behavior we agreed to use.

Consequences: Percentile is display-only metadata derived when rank info is returned. It is not stored in rank cache. No tiny-leaderboard special casing is planned, so `rank 1 of 1` displays `50.00%`.

## 2026-04-27: Keep KovaaK's API Findings In A Dedicated Notes File

Status: Accepted

Decision: Track KovaaK's endpoint behavior, relied-upon fields, and discovered quirks in `docs/kovaaks_api_notes.md`.

Why: We are probing unofficial or lightly documented API behavior across multiple milestones. Keeping API lore in one living document helps future agents avoid rediscovering endpoint semantics from chat history.

Consequences: When new endpoint behavior or failure modes are discovered, update the notes file and add regression coverage when practical.

## 2026-04-28: Retry KovaaK's GET Transient Failures Once

Status: Superseded in part by the 2026-07-13 timeout/read-timeout decision — `requests.Timeout` is no longer in the retry set (read timeouts fail immediately); the `429`/`Retry-After` policy and the `requests.ConnectionError` retry stand

Decision: KovaaK's GET requests should retry exactly once on HTTP `429 Too Many Requests`, `requests.Timeout`, and `requests.ConnectionError`. `429` retries should honor `Retry-After` when present and cap the wait.

Why: Playlist scenario overview can create bursty cold-cache rank and total lookups. KovaaK's can also occasionally exceed the current read timeout for one row while adjacent requests succeed. A single bounded retry handles transient failures without turning the retry helper into a full scheduler or hiding unrelated failures.

Consequences: Retry remains GET-only. Non-429 HTTP failures and unexpected exceptions continue through the existing service-layer error handling. Recovered retries are logged but are not user-facing notifications.

## 2026-04-29: Drive Playlist Table Loads From Mounted Route State

Status: Accepted

Decision: Playlist scenario table loads should be driven by state created in the mounted `/playlists/<playlist_code>` layout, not directly by selector changes or URL-change callbacks.

Why: When the playlist selector changes the route, Dash Pages can briefly have the old page instance responding to the URL update before the new route layout finishes mounting. If the expensive table load listens directly to that navigation event, one user selection can trigger duplicate cache/API loads.

Consequences: Keep the selector callback navigation-only. The route layout should publish the resolved playlist code through a lightweight mounted component, currently `dcc.Store(id="playlist-scenarios-code")`, and the table-loading callback should use that mounted state as its trigger.

## 2026-04-29: Use Controlled AG Grid JS For Null-Aware Sorting

Status: Accepted

Decision: Playlist scenario AG Grid tables may use repo-owned JavaScript comparators from `assets/dashAgGridFunctions.js` with `dangerously_allow_code=True` when AG Grid requires client-side sort behavior that Python cannot provide directly.

Why: AG Grid sorting runs in the browser. The playlist table needs `NULLS LAST` behavior for rank, total, and percentile columns so unknown values do not sort ahead of real numeric values.

Consequences: Only reference controlled functions committed under `assets/`. Do not generate JavaScript strings from user input. If additional custom grid behavior is needed, prefer adding named functions to `assets/dashAgGridFunctions.js` rather than embedding ad hoc code in page callbacks.

## 2026-04-29: Use Thread-Local Sessions For KovaaK's GET Requests

Status: Accepted

Decision: KovaaK's GET requests should go through a reusable `requests.Session` scoped to the current worker thread.

Why: Cold-cache playlist table loads make many small HTTPS calls. Reusing sessions lets Requests keep connections alive and avoid repeated TCP/TLS setup. Keeping sessions thread-local avoids sharing one mutable `Session` object across the playlist table's concurrent worker threads.

Consequences: `_get_with_retry()` should call the thread-local session wrapper instead of `requests.get(...)` directly. Tests should patch that wrapper when faking HTTP responses. If we later add async HTTP or a centralized rate limiter, revisit this decision.

## 2026-06-21: Keep The Hand-Rolled GET Retry; Defer urllib3 `Retry` Migration

Status: Accepted

Decision: Keep the hand-rolled retry helpers in `source/kovaaks/api_service.py`
(`_get_with_retry`, `_retry_after_seconds`) instead of mounting a urllib3
`HTTPAdapter(max_retries=Retry(...))` on the thread-local sessions. Reconsider
only when requirements grow past one retry (exponential backoff with jitter, a
broader `status_forcelist` such as 503, separate connect/read budgets).

Why: The happy path maps cleanly onto urllib3 `Retry`, but a faithful migration
is not a clean delete. It would lose the 0.5s default delay on a 429 without
`Retry-After` (urllib3 sleeps 0s on the first retry), change the exhaustion
exception types the tests assert on (`HTTPError`/bare timeout become
`RetryError`/wrapped `ConnectionError`), downgrade recovered-retry logging from
WARNING to a DEBUG line on urllib3's logger, and still require a wrapper for the
per-request timeout default. Preserving the 5s `Retry-After` cap needs
`retry_after_max`, which requires pinning `urllib3>=2.6` — currently only a
transitive dependency. Net-neutral complexity plus a full test rewrite does not
clear the bar for replacing working, ratified code.

Consequences: The retry layer stays per-request and hand-rolled; the score-aware
rank refresh loop sits on top of it and relies on its contract (one inner retry,
bounded sleeps). If migrating later, the minimal-drift recipe is: one
module-level `Retry(total=1, status=1, connect=1, read=1, status_forcelist=[429],
allowed_methods={"GET"}, retry_after_max=5, raise_on_status=False)` mounted on
both schemes of each thread-local session, a thin wrapper retained for the
timeout default and WARNING log, and an explicit `urllib3>=2.6` floor. The full
analysis lives in git history as `docs/api_retry_urllib3_migration_proposal.md`.

## 2026-07-03: Playlists Routes Are Stable; The Bare-Route Selector Is Transitional

Status: Accepted

Decision: The playlists feature owns two routes: `/playlists` (navbar
destination) and `/playlists/{playlistCode}` (per-playlist scenario table).
The per-playlist route and its `playlistCode` URL identity are stable
contracts. The current content of the bare route — a selector dropdown plus an
empty prompt — is transitional scaffolding from milestone 1: when the
playlist-level overview (roadmap milestone 2) ships, the overview replaces the
bare-route content, overview rows navigate to `/playlists/{playlistCode}`, and
the selector dropdowns are removed from both pages.

Why: A single canonical landing route keeps the navbar destination stable
across milestones, and the human-readable playlist code is already user-facing
via the import flow. The overview is a strictly richer playlist picker than a
name-only dropdown (it surfaces last-played, aggregate percentile, and similar
metadata), so keeping the selector after it ships would be scaffolding
outliving its purpose. Distilled from the milestone-1 playlist scenarios
proposal (shipped in PRs #12, #15, #16).

Consequences: Keep the selector wiring separate enough that its removal is a
clean delete, not a refactor. Post-overview, switching playlists means
navigating back to `/playlists` and clicking a row, so the overview needs
visible row-click affordances (cursor, hover tint, full-row target). Do not
bake the selector into the per-playlist page in a way that blocks removal.

## 2026-06-20: Reference dash-ag-grid Grid Functions By Bare Name

Status: Accepted

Decision: In dash-ag-grid `{"function": "..."}` strings (`valueFormatter`, `tooltipValueGetter`, `comparator`, `valueGetter`, etc.), reference functions from the `assets/dashAgGridFunctions.js` registry by their **bare name** — `relativeTime(params.value, "Never")`, `nullsLastComparator` — never with a `dagfuncs.` prefix.

Why: dash-ag-grid (35.2.0) does not run these strings as a browser-global eval. It parses each to an AST and evaluates it against a constructed scope that spreads the contents of `window.dashAgGridFunctions` in as bare names (alongside `params`, `agGrid`, `d3`, `dash_clientside`). There is no `dagfuncs` object in that scope — the identifier never appears in the dash-ag-grid bundle — so `dagfuncs.X(...)` resolves to undefined and the expression **silently fails**: the cell renders the raw field value, or the comparator falls back to AG Grid's default sort, with no console error. The `assets/` file's `var dagfuncs = (window.dashAgGridFunctions = ...)` alias is only for *defining* the registry functions.

Consequences: Plain Dash `clientside_callback`s are different — they run in real browser global scope, so there use the full `window.dashAgGridFunctions.X(...)` path (e.g. the home page's "Last played" relative-time callback). This decision corrected two silent bugs: the grid "Last Played" `valueFormatter`/`tooltipValueGetter` (PR #17) and the `NULLS LAST` comparator on all sortable columns (PR #19), the latter broken since the 2026-04-29 "Use Controlled AG Grid JS For Null-Aware Sorting" entry. Verified by decompiling the installed bundle and by a live browser test.

## 2026-06-20: Interim Merge Bar Until Lint/Format Cleanup

Status: Superseded by the 2026-07-03 ruff-only tooling decision

Decision: Until the lint/format cleanup lands, the merge bar is: `uv run pytest` and `uv run mypy source` must be **green**, and `uv run pylint source` plus `black --check`/`isort --check` must **not regress versus `main`** (no new findings in the files a change touches). The absolute CLAUDE.md bar (pylint `fail-under = 10`, black/isort clean) is the target, not yet current reality.

Why: As of 2026-06-20 `main` is green on pytest and mypy (the latter since PR #18 deleted a dead `mypy.ini` that was shadowing `[tool.mypy]`), but not on pylint (9.22/10 — missing docstrings, TODOs, broad-except, too-many-*), `black --check` (3 files), or `isort --check` (2 files). Those are pre-existing and reproduce on the committed LF blobs (not a CRLF flap). There is no CI, so the gates are an honour-system check; blocking feature PRs on an absolute bar `main` itself cannot meet is incoherent, while a baseline-comparison bar keeps shipping unblocked without growing the debt.

Consequences: Reviewers compare pylint/black/isort output for the changed files against the `main` baseline rather than requiring a green absolute run; pytest and mypy are hard green gates. The remaining pylint cleanup is deferred tech debt (~115 findings on `main`, dominated by missing docstrings, plus fix-or-disable calls on `too-many-*`, `broad-except`, `fixme`, and similar); the `black`/`isort` deltas are a few files. Remove this interim framing once pylint and the formatters are green on `main`.

## 2026-07-03: Consolidate Formatting And Linting On Ruff

Status: Accepted

Decision: Use ruff as the sole formatter and linter, with mypy and pytest retained as separate gates. Ruff formats at 88 characters and enforces a 120-character hard ceiling through `E501`. Lint `source/` and `tests/`, but exclude `scripts/`; tests are exempt from missing-docstring, design-metric, and unused-argument rules. Require docstrings in `source/`, leave deliberate TODOs unenforced, and keep preview mode disabled. Local pre-commit hooks enforce ruff check and format; mypy, pytest, and the inexpensive CPython `compileall` syntax check remain manual validation because the project has no CI.

Why: The previous black, isort, and pylint configuration described conflicting line lengths, duplicated responsibilities, and could not meet its own score gate while intentional TODOs remained. One pinned ruff configuration provides a green, deterministic format/lint bar without a score or `fail-under`, while preserving the established 88-character formatting and keeping tests and replacement-bound scripts free from low-value lint churn.

Consequences: Pylint, black, and isort are no longer direct dependencies or configured tools. Black and isort remain transitive lockfile dependencies of `datamodel-code-generator`. Accepted enforcement losses are: no ruff equivalents for duplicate-code, too-many-instance-attributes, or too-many-lines; preview-only rules for unspecified-encoding, too-many-locals, too-many-positional-arguments, too-many-boolean-expressions, and too-many-nested-blocks remain disabled; and `no-else-return` is outside the selected rule families. The two current encoding omissions and the current unnecessary `else` were fixed once during migration, but are not ongoing gates. Keep the pre-commit ruff revision synchronized with the ruff version in `uv.lock`, and add CI or a single-command task runner separately.

## 2026-07-03: CI Runs The Merge Bar On Every PR

Status: Superseded in part by the 2026-07-06 cross-repo Python v2 tooling decision

Decision: A single GitHub Actions `gates` job runs the repository merge bar on
every pull request and push to `main`: ruff format check, ruff lint, mypy,
CPython `compileall`, and pytest. It runs on `windows-latest`, validates the
lockfile with `uv sync --locked`, and executes each gate with
`uv run --no-sync`. Python and uv are pinned, action dependencies use immutable
full commit SHAs, the workflow token has read-only contents access, and
superseded runs on the same ref are cancelled.

Why: This fulfills the deferred CI consequence of the 2026-07-03 ruff
consolidation decision. An executable merge bar catches stale lockfiles,
formatting drift, type errors, syntax errors, and regressions consistently,
including on doc-only changes where the docs hygiene tests still matter.
Windows matches the supported development and runtime environment.

Consequences: `.github/workflows/gates.yml` is the canonical executable list of
gates. Local pre-handoff validation remains unchanged because it is the fastest
feedback path. A local single-command task runner remains optional rather than
part of this decision. After the workflow has established a short green
history, the repository owner should mark the `gates` check required on
`main`; branch protection is intentionally outside the workflow.

## 2026-07-06: Adopt The Cross-Repo Python V2 Tooling Spec

Status: Accepted

Supersedes: The workflow shape, command set, tool and runtime pin placement,
and concurrency behavior in the 2026-07-03 CI decision. Windows execution,
locked dependency sync, SHA-pinned actions, read-only contents permission, and
the broader local pre-handoff validation remain in force.

Decision: Use the canonical `tooling-spec: python-v2` workflow at
`.github/workflows/ci.yml`. Its matrix-backed `test (windows-latest)` job runs
`uv sync --locked`, ruff format, ruff lint, bare mypy, and bare pytest.
`pyproject.toml` owns the required uv version (`==0.11.26`), pytest discovery
and options, and mypy's `source/` scope. The workflow no longer overrides Git
line endings, cancels superseded runs, caches uv, pins Python or uv through
`setup-uv`, or runs `compileall`.

Why: The cross-repo spec keeps local and CI invocations aligned through project
configuration and gives repositories one recognizable CI shape. Moving the uv,
pytest, and mypy defaults into `pyproject.toml` makes the bare commands
authoritative in every environment instead of relying on workflow-only flags.

Consequences: Local pre-handoff validation still includes `compileall`, while
CI has four named checks inside the single Windows matrix job. CI resolves a
compatible interpreter from `requires-python = ">=3.14"`; this migration does
not add a `.python-version` pin. The required branch-protection check changes
from `gates` to `test (windows-latest)` and must be updated by the repository
owner at merge time. Add a minimal `.gitattributes` only if a runner actually
reports line-ending format drift; the migration's first CI run did not.

## 2026-06-21: Relative ("Humanized") Last-Played Timestamps

Status: Superseded in part by the 2026-06-30 home empty-state decision; for the exact absolute-string format (`%Y-%m-%d %I:%M:%S %p`), by the 2026-07-11 humanized absolute-format decision; and, for the grid sentinel's scope and the single-column `refreshCells` call, by the [2026-08-09 PB-sentinel decision](#2026-08-09-pb-columns-keep-their-na-sentinel-even-for-timestamps)

Decision: "Last played" renders as a relative, humanized string ("5 minutes ago") in both the home Scenario Stats block and the playlists grid, with the exact timestamp shown on hover (`%Y-%m-%d %I:%M:%S %p`). Formatting lives in a single shared pair of pure JS helpers (`relativeTime`/`absoluteTime`) in `assets/dashAgGridFunctions.js`. Rules: a single rounded unit, never compound — just now (≤60s, including ≤0 / future) → N minutes → N hours → N days → N months → N years, with months/years calendar-based and a `max(0, …)` clamp (no `Intl` dependency, no "over"/"about" prefix). The value stays relative all the way (no absolute-date cutover) because it is a staleness gauge, not a reference date. Timestamps are epoch **seconds** end-to-end (the JS multiplies by 1000). Sentinels: "Never" on the grid (in a playlist but never played), "N/A" on home (no selection / not in DB) — never blank. The home value self-updates via a dedicated 30s `dcc.Interval` (decoupled from `polling_interval`); the grid live-ticks via a dedicated interval + `refreshCells({force: true, columns: ['last_played_sort']})`.

Why: A relative string answers "how stale is this?" directly, while the tooltip preserves the exact instant. Hand-rolled formatting (~30 lines) is simpler than `Intl` for an English-only app and fully controls the edges; calendar-based month/year math matches what a human reading two dates would say and avoids day-division boundary fudges.

Consequences: Shipped in PRs #17/#19 (Phase 1: shared helpers, home self-update, grid render-on-load) and #23 (Phase 2: grid live-ticking). Exact-timestamp access is hover-only (tooltip), consciously waived for this local single-user app. For how grid colDef `{"function": ...}` strings invoke these helpers, see the 2026-06-20 "Reference dash-ag-grid Grid Functions By Bare Name" entry. This entry distills and replaces `docs/relative_timestamp_proposal.md`, now deleted.

## 2026-06-30: Model Home Last-Played Empty States Explicitly

Status: Superseded in part, for the exact absolute-string format (`%Y-%m-%d %I:%M:%S %p`), by the 2026-07-11 humanized absolute-format decision

Supersedes: The home sentinel and hover-only tooltip interaction in the 2026-06-21 relative timestamp decision. The playlist-grid behavior and shared timestamp formatting rules remain unchanged.

Decision: Home Scenario Stats distinguishes three "Last played" states: no scenario selected renders `—`; a selected scenario with no local play data renders `Never`; and a selected scenario with play data renders the relative timestamp. Only a real timestamp receives the dotted underline and `cursor: help` affordance. Its exact local timestamp (`%Y-%m-%d %I:%M:%S %p`) is available by hover, keyboard focus, or touch. Empty states are not focusable and disable the tooltip entirely.

Why: `—` communicates an unselected field without implying missing or failed data, while `Never` communicates a known selected scenario with no recorded plays. Showing the affordance only when more information exists keeps the interaction honest and avoids a tooltip that merely repeats an empty-state value.

Consequences: The home callback owns the empty-state value and tooltip affordance alongside the raw timestamp. The clientside relative-time callback continues to own the live-updating visible timestamp. A selected scenario missing from the local database is treated as having no local play data; temporary loading or error states must not be mapped to `Never`.

## 2026-07-01: Keep Scenario Rank Consistent With Score-Aware Refreshes

Status: Superseded in part, for the exhausted-loop notification ("asks the user
to click Refresh" in Consequences below), by the
[2026-08-03 console-only background diagnostics decision](#2026-08-03-background-rank-diagnostics-are-console-only).
Every other part of this entry remains Accepted.

Supersedes: The `ThreadPoolExecutor(max_workers=2)` high-score refresh and the
decision not to provide manual rank refresh in the original scenario rank
proposal (since distilled into this log and deleted).

Decision: After a local high score, run a bounded score-aware refresh using a
daemon `threading.Timer` chain with delays of 2, 4, 8, 16, and 32 seconds. Accept
the leaderboard as caught up only when its score reaches the two-decimal floor of
the local score. Route every automatic rank-cache write through one process-locked
monotonic writer so a lower score or transient `UNRANKED` result cannot replace a
known better value. The home rank widget passively re-reads rank and total caches
on its existing interval without making network calls, including when those cache
files are older than their normal TTLs. A user-clicked Refresh performs one
authoritative fetch and may deliberately write a lower score or `UNRANKED` result.

Why: KovaaK's leaderboard updates are eventually consistent, so the old single
post-PB fetch could persist lagging data for the week-long cache TTL. Timer
attempts keep delayed work off a bounded executor, centralized write arbitration
prevents loop/read races, and the cache-only UI poll surfaces successful background
writes within about one second. Automatic rechecks after the bounded window would
hammer permanently divergent offline/server-down scores; explicit Refresh gives
the user a bounded escape hatch instead.

Consequences: Automatic rank displays move forward by score and never flicker from
a known rank to `UNRANKED`; explicit Refresh is board-authoritative and can move
backward after a leaderboard reset. Interval ticks resolve only cached leaderboard
IDs, read rank and total files independent of TTL, emit no repeated warning/error
toasts, and make zero KovaaK's requests. A refresh loop that exhausts leaves the
previous cache untouched and asks the user to click Refresh. The retry schedule is
a code constant, not configuration.

## 2026-07-03: Import Benchmarks From Evxl And KovaaK's

Status: Accepted

Decision: The benchmark importer uses Evxl to resolve playlist names and codes,
and KovaaK's to fetch benchmark rank thresholds. In project terminology, a
*playlist* is a bare scenario list without rank data; a *benchmark* is a
playlist plus rank thresholds and colors. Generated benchmark JSON carries a
`generated_from` provenance stamp containing the Evxl sharecode, KovaaK's
benchmark ID, ordered rank-color pairs, generation timestamp, and generator
name.

Why: KovaaK's playlist search cannot resolve every known sharecode, while Evxl's
exact-code endpoint can; Evxl does not expose the per-scenario rank thresholds,
so KovaaK's remains authoritative for those values. The terminology distinguishes
the app's playlist import from the richer files produced by the importer.
Provenance makes the upstream inputs inspectable and allows generated files to be
checked for stale or mismatched benchmark metadata.

Consequences: Keep Evxl-specific resolution and snapshot handling in
`scripts/benchmark_importer/` unless an app-side feature explicitly adopts that
dependency. Preserve rank-color order when comparing provenance because colors
pair positionally with KovaaK's thresholds. Conflicting duplicate Evxl
sharecodes must be skipped and reported rather than resolved first-wins because
a missing benchmark is visible and recoverable, while silently pairing the wrong
rank thresholds is not. KovaaK's threshold changes under an unchanged benchmark
ID remain invisible to provenance checks and require an explicit forced refresh.

## 2026-07-06: Coalesce Pending Home Run Events

Status: Accepted

Decision: Home's `check_for_new_data` callback is the sole consumer of the
process-wide run-event deque. On each invocation it drains all pending messages,
lands on the most recently played scenario when automatic scenario switching is
enabled, and publishes a JSON-safe `run-events` summary for that scenario.
`generate_graph` rebuilds from the already-current in-memory stores and creates
toasts from that summary only when `run-events` triggered it. A single run keeps
the existing per-run toast behavior; a backlog produces one scenario-named
summary based on the latest matching run. The watchdog must successfully load a
run into the stores before enqueueing its message. The supported usage model is
one active Home tab; extra tabs remain crash-safe but unsynchronized.

Why: Home's interval does not run while the page is unmounted, so queued events
previously replayed one tick at a time on return. That rebuilt the same final
plot repeatedly, moved the scenario dropdown through stale history, and emitted
stale toast batches. Enqueue-before-load also allowed a consumer to rebuild
before the corresponding run was queryable, or to toast a run whose second parse
failed.

Consequences: A backlog is consumed in one tick, produces at most one dropdown
change and one toast batch, and cannot expose a message without queryable run
data. Mixed-scenario counts describe only the landing scenario. Nonmatching
events are discarded when automatic switching is off, preserving the previous
policy without wasting ticks. Coherent multi-tab delivery would require a
broadcast or push transport and remains outside this local single-user design.

## 2026-07-06: One Word Per Concept In Leaderboard Verbiage

Status: Accepted

Decision: "Rank" was used for both benchmark tiers (Bronze/Silver/..., Rank
Overlay) and leaderboard placement (Home "Rank:", grid "Current Rank"),
mirroring a split in the ecosystem (KovaaK's leaderboards: rank = position;
Voltaic/Aimlabs: rank = tier). In user-facing text, **Rank** means tier only,
**Position** means leaderboard placement ("Total Players" for board size), and
**PB** prefixes stats of the personal-best run (PB Score, PB cm/360, PB
Accuracy). "Unranked" is retained as KovaaK's own term for having no leaderboard
entry.

Consequences: Labels, plot annotations, and toasts follow the invariant.
Internal identifiers, component ids, and row field names keep their old names
because this is a label-only rename. New UI text must not reintroduce "rank" for
leaderboard placement.

## 2026-07-06: Let The Playlist Scenarios Grid Own Vertical Scrolling

Status: Accepted

Decision: Bound the playlist scenarios page to the Mantine AppShell content
viewport and let the AG Grid use its normal layout with an internal vertical
scrollbar. The page Stack and Dash Loading wrappers form a flex column, and the
grid fills the remaining space with a 300px minimum height. Keep the existing
content-based column sizing and capped flexible Scenario column.

Why: `domLayout: autoHeight` expanded the grid to every row, so the document
scrolled and carried the column headers out of view on large playlists. A
bounded grid keeps the headers visible while the user sorts and scans scenarios
deep in the playlist, and restores row virtualization.

Consequences: Short playlists show empty grid body below their final row instead
of collapsing the grid. Very short windows may still scroll the page to preserve
the 300px usable minimum. The layout tracks AppShell header and padding variables
instead of duplicating their pixel values.

## 2026-07-11: Move The API Cache Under data/cache/

Status: Accepted

Decision: Relocate the runtime API cache root from `cache/` to `data/cache/`
as a plain path change, with no in-app compatibility migration. An existing
`cache/` directory is moved by hand after the change lands.

Why: The 2026-06-22 entry grouped user/runtime state under `data/` but
deferred the cache to a dedicated compatibility migration. The app currently
has exactly one user and the cache is fully regenerable from the API, so
migration code would outlive its single use; a one-time manual move (or just
letting the cache rebuild) covers it.

Consequences: All runtime state — logs, preferences, user playlists, and the
cache — lives under one ignored `data/` root. A legacy `cache/` root left in
place is silently ignored; `.gitignore` keeps its entry so pre-move checkouts
stay clean. Revisit an in-app migration only if the app gains users beyond
its author.

## 2026-07-15: Stream Playlist Positions With Generation-Scoped Progressive Fill

Status: Superseded in part, for the aggregate completion toast alone, by
the
[2026-08-22 in-place-only entry](#2026-08-22-the-playlist-fill-reports-degradation-in-place-only)
(the fill states degradation in the page's status line and emits no
notification). The fill mechanism, generation scoping, tombstones, and
status settling are unchanged and remain Accepted.

Supersedes: The blocking all-scenarios load and Dash Loading wrapper for the
per-playlist scenario grid. The bounded, grid-owned scrolling decision from
2026-07-06 remains in force.

Decision: Opening `/playlists/<code>` has two phases. Phase 1 paints every row
from local stats plus TTL-ignored rank caches, with explicit per-cell pending
flags for unresolved Position, Total Players, and Percentile values. Phase 2
hydrates leaderboard IDs once, then runs the normal cache/network lookup path
through the existing four-worker fan-out in one daemon-thread fill. Workers
stream complete row dictionaries into a lock-guarded in-memory registry keyed
by a per-open generation token. A one-second, enable-only interval drains those
rows through AG Grid update transactions; row identity is
`generation_token:playlist_order`, so a superseded response cannot update the
current grid.

Starting a fill synchronously cancels every other live generation. Completion
and cancellation become bounded tombstones with final counters, a terminal
state, and an atomic consumed flag. The first terminal tick alone drains final
updates, rebuilds unresolved cancelled rows cache-only, settles the status, and
emits any aggregate completion toast; later ticks only reassert the settled
status. Consumed tombstones drop queued rows and finalization payloads, but stay
in the same eight-item retention set as unconsumed tombstones. Overflow evicts
consumed before unconsumed, oldest first within each class, and the cap is
enforced at every terminal transition.

Pending state is never inferred from null values: resolved `UNRANKED` Position
is valid with a null sort key. Completed/finalized rows clear all pending flags.
Outcomes are counted before row formatting as fresh, `UNKNOWN`, or structurally
`served_stale`; the transient stale marker is never written to the rank cache.
Completion uses the existing red/yellow/silent failure tiers without
per-scenario toast spam. The API coordination signal keeps two monotonic
timestamps: interactive rank activity includes cache hits, while network
success changes only after a real successful HTTP response.

Why: Cold or flaky playlist opens previously hid six locally available columns
behind minutes of blocking API work. Progressive fill makes the training table
useful immediately while preserving the existing cache freshness and lookup
semantics. Generation-scoped row IDs plus consumed tombstones close the races
created by navigation, two tabs, callback responses already in flight, and
DashProxy's spurious initial callback behavior without adding a persistent job
system.

Consequences: The grid no longer uses `dcc.Loading`; animated CSS placeholders
and a `done/total` status provide progress. Clean fills clear the status and stay
silent, degraded fills retain a compact summary, and cancelled fills settle as
interrupted with no cell left pending. The registry is process-local and
single-user: reloads start a new fill, a second tab cancels the first tab's
network work, and completed API calls still warm the normal atomic disk caches.
Shipped in PR #127.

## 2026-07-16: Keep Pre-Hydration States Honest

Status: Accepted

Decision: Empty-state copy renders only after the owning data callback resolves.
AG Grid layouts omit initial `rowData` so the built-in loading overlay owns the
hydration gap. Plot layouts use a transparent, annotation-free placeholder;
`generate_empty_plot` is reserved for resolved-empty results.

Consequences: Initial page hydration stays visually neutral and never makes a
false no-data claim. Callbacks that resolve to empty grid rows or empty figures
continue to show their explicit empty-state guidance.

## 2026-07-17: Absorb Poll-Tick Bursts With Threads, Not Visibility Gating

Status: Accepted

Decision: Waitress runs with 8 worker threads (PR #116) as the sole fix for
poll-tick pressure. The demand-side alternative — pausing Home's
`interval-component` while the tab is hidden (Page Visibility API) — stays
unbuilt; its pre-approved design is parked as a kickoff prompt in
`ignore/prompts/icebox/` for reactivation if the symptom returns.

Why: Every Home polling tick (1 s default) fires three callback POSTs at once
(`check_for_new_data`, `flush_background_notifications`, and the cache-only
branch of `get_scenario_rank`). Against Waitress's default 4 threads, that
burst plus one thread held by a slow KovaaK's fetch (slow spells reach ~28 s)
left zero headroom, and a single idle tab produced task-queue-depth warnings.
Raising supply to 8 threads was deliberately tried first as the minimal fix,
with visibility-gated polling queued as the contingent next step; four days of
post-merge logs showed zero warnings, so the contingency never fired. Push
delivery (WebSocket/SSE) was also rejected: this is a single-user local app,
and with the warnings gone the polling cost argument for push collapses.

Consequences: An idle-but-hidden Home tab still polls (~3 POSTs/s of cheap
cache-only work) — accepted chatter, not a defect. If queue-depth warnings
reappear, reach for the iceboxed visibility-gating prompt (gate on
`document.hidden`, never window focus: an unfocused-but-visible window on a
secondary monitor must keep polling) before raising threads further.

## 2026-07-18: Leaderboard Mapping Reads Through an mtime-Revalidated In-Memory Mirror

Status: Accepted

Decision: `get_cached_leaderboard_id` serves lookups from a module-level parsed
copy of `scenario_name_to_leaderboard_id.json`, revalidated on every read by
comparing the file's identity — `(path, st_mtime_ns, st_size)` from one
`stat()` call — against the signature recorded when the copy was parsed. In
cache-policy terms: read-through population, write-around writes
(`save_leaderboard_id` still writes only the file), revalidate-on-read
coherence. Disk remains the source of truth; memory is a verified mirror. The
check-and-load runs under `_CACHE_IO_LOCK`, which `_write_json` also holds, so
lookups cannot interleave with in-process writes.

Why: The mapping file is a whole-store key-value file (~140KB, ~1,000 entries,
append-mostly immutable facts) consulted once per rank lookup, so every point
lookup paid a full parse. The playlist overview's "Show hidden" toggle made
this visible: rebuilding all 217 rows performed 1,062 cache-only rank lookups
and re-parsed the same file 1,062 times (~150MB of JSON) — measured at 0.77s
per toggle, and again on every 1s warmup-interval repaint. The mtime cache
alone cut the build to 0.19s; per-build memoization alone reached only 0.44s
because playlist overlap is modest (1,062 lookups over 659 distinct scenarios,
1.61x), so the per-lookup parse, not duplication, was the dominant cost.

Alternatives considered: (a) a loading spinner — rejected: the row-build
callback is shared with the warmup interval and refresh-store bumps, so any
`dcc.Loading`/`running=` indicator flashes on every automated repaint, and it
decorates waste rather than removing it; (b) per-build memoization of rank
resolution in the overview service — deferred, not rejected: it would add
snapshot consistency (the R11 property scenario stats already have) and take
0.19s to 0.11s, but is no longer the headline fix; (c) write-through (updating
the in-memory copy in `save_leaderboard_id` instead of revalidating) —
rejected: it maintains coherence only for writes made through this process's
write path, and the cache conventions explicitly support external mutation
(deleting `data/cache/` mid-run, other processes); trusting memory
unconditionally would invert the source of truth. As a redundant addition on
top of revalidation it buys one ~1ms parse per rare write at the cost of a
three-way coherence invariant (file, dict, signature) in the write path;
(d) SQLite — unchanged from the 2026-06 cache-layer decision: indexed point
reads would dissolve this whole class of cost and subsume this fix, but the
migration stays parked behind its documented triggers (rank history,
multi-record queries, transactional guarantees).

Consequences: `api_service` is no longer fully stateless — this one file has
an in-memory mirror, with the invariant that every serve is preceded by a
fresh `stat()` proof. The signature includes the resolved path so tests that
repoint `CACHE_DIR` cannot alias a stale copy; `st_size` guards against
same-mtime rewrites on coarse-timestamp filesystems. Metadata revalidation
inherently cannot detect a rewrite that preserves both size and timestamp
(deliberate `os.utime` forgery after an in-place edit — the known limit of
every mtime-keyed cache, `.pyc` included). This is an accepted risk, not an
oversight: the PR #147 review asked for a bounded forced refresh and a
60-second re-parse backstop was briefly added, then removed at the
maintainer's direction — a periodic redundant reload with no intervening
write contradicts the cache's purpose (fast reads until the next write), no
realistic writer forges timestamps (atomic replace, editors, and restores
all shift mtime_ns or size), and the only actor who could is the single
user poisoning their own local cache. A content-hash key was also rejected:
it must read the whole file per check (~146ms vs ~27ms per toggle build for
`stat`), returning a third of the original cost to buy a guarantee only the
forgery scenario needs. A regression test pins the accepted behavior
(forged rewrite served until the next genuine write) so it reads as
deliberate. A missing mapping file no
longer logs a read-failure warning per lookup (the stat short-circuits the
read), and a malformed file warns once per file version instead of once per
lookup. All `resolve_leaderboard_id` callers (Home rank display, playlist
drill-in fill, warmup worker, watchdog rank-freshness timers) share the
parse-free path. The other cache files (per-scenario rank, totals) stay as
direct per-read files: small, per-key reads where mirroring would add
bookkeeping for little gain. Regression tests pin the single-parse property,
write-then-read invalidation, external rewrite, deletion, and malformed-file
tolerance.
