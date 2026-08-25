# Personal Best Celebration

Status: Proposed
Date: 2026-08-21

## TL;DR

When a run beats a scenario's personal best, the app should throw a short
celebration: a burst of confetti and one toast that says so. Today a new
personal best earns nothing on screen except a quiet rank refresh. The
celebration fires on every page and for every scenario, because a personal
best is an achievement regardless of what the user happens to be looking at.
A Settings-page control turns the celebration off; the first version ships
one confetti effect, and a follow-up adds a choice of styles.

## Decisions needed

The maintainer ruled on 2026-08-25, after three review rounds: all eight
decisions are ratified, D6 as a staged compromise and D8 with a post-ship
observation in place of pre-ship evidence.

### D1 — Does the celebration fire on every page, for every scenario?

Status: Ratified (2026-08-25)

**Decision: yes, app-wide.**

A personal best is an app-level achievement; the current page and the
selected scenario are incidental. The run toasts are produced only by the
Scenario Performance page, and only for the selected scenario (or the
auto-switched one), so a celebration riding that pipeline would stay silent on
the Playlists pages, where a benchmark session is most likely to be watched,
and for any scenario not currently selected. A switch named "celebrate
personal bests" that skips those cases reads as broken, not as consistent.

Choosing Scenario Performance only is the cheaper build (no new event channel,
no shell-level consumer) at the cost of that reliability gap. It also leaves
the celebration inheriting the selected-scenario filter, which the setting's
copy would then have to explain.

### D2 — Where does the setting live, and where is it stored?

Status: Ratified (2026-08-25)

**Decision: a control on the Settings page, persisted in the browser, in
its own section outside the Save form.**

The behavior is app-wide, so the Chart options inspector on one page is the
wrong home: undiscoverable, and a control there describes itself as a chart
option. The Settings page is the UI home. Storage stays browser-local Dash
persistence rather than `data/settings.json`, for the reasons in Design
("Storage"): the settings store's versioning contract makes the first key
addition a real migration with a rollback cost, which a cosmetic preference
should not be the thing to trigger.

This departs from the placement rule the point customization and master
switch decision-log entries (2026-08-20 and 2026-08-21) both state, that the
inspector owns browser-persisted presentation preferences. The departure is
deliberate and narrow: that rule governs preferences about the chart; this
preference is about the app. The Settings page section is also the first
browser-persisted control on that page, beside a form whose three fields are
written to disk behind Save. The section is visibly separate and its control
applies instantly, so the form's contract is untouched.

Choosing the inspector instead keeps the placement rule intact and is
marginally cheaper. Choosing `data/settings.json` instead is the
settings-v2 migration described in Design, and should wait for a setting that
deserves it; this one would be folded into that version when it comes.

### D3 — Vendor `canvas-confetti`, or hand-roll the animation?

Status: Ratified (2026-08-25)

**Decision: vendor `canvas-confetti` 1.9.4 (ISC), unminified.**

The market survey in Verified facts found one candidate that is small,
dependency-free, loadable as a classic script (which is how Dash serves
`assets/*.js`), and still maintained. It ships the physics, the shapes, the
reduced-motion guard, cancellation, and worker-thread rendering, and its
demo recipes are the styles D6 offers. A hand-rolled canvas effect can look
close with a tuning pass, but every later change is physics code instead of
configuration, and every browser quirk is ours.

The cost is the first third-party JavaScript file in the tree. Vendoring the
unminified source with its license and a version pin keeps it reviewable and
diffable against the upstream tag. Choosing to hand-roll instead keeps the
tree free of third-party JS and accepts the tuning pass and the ongoing
ownership.

### D4 — Does a personal best take the run toast's headline?

Status: Ratified (2026-08-25)

**Decision: yes, on the celebration toast only.** When
celebrations are on, a personal best run's one toast is the celebration
toast ("New personal best"), and the page's run toast yields to it. When
celebrations are Off, the page's run-toast policy is unchanged: the threshold
verdict headlines when there is one, a placement otherwise, and a personal
best has no toast of its own, as today.

Today a personal best has no toast of its own; the threshold verdict
headlines when there is one, and a placement otherwise. The score threshold
goal has no upper bound, so a goal above 100% lets a personal best read
"Below threshold" while confetti falls, which is contradictory on screen.
Even with a goal at or under 100% (where a personal best always passes), a
"Threshold passed" headline under confetti says the less interesting thing.
Tying the headline to the celebration keeps Off honest: the style select
turns the animation and the toast off together, and nothing else changes.

This amends the run-notification priority rule recorded in `product.md` for
the celebrations-on state only. Choosing to keep the verdict headline even
under confetti preserves the "need N%" detail for goals above 100%, at the
cost of the contradiction. Choosing the personal best headline in every
state, celebrations Off included, would make the setting animation-only and
need a different name and description.

### D5 — Ship without a noise gate for young scenarios?

Status: Ratified (2026-08-25)

**Decision: yes, ungated.**

Early in a scenario's life most runs are personal bests, so a freshly
imported playlist celebrates nearly every run for a session, which is when
it means least. The ruling ships with the one gate that is clearly right
(an existing personal best must be beaten; a scenario's first run sets a
baseline and is never celebrated) and let the setting be the escape hatch.
This follows the repo's accepted-limitation habit: document the gap, point at
the existing control, stop.

Choosing a gate instead (a minimum run count, or a minimum margin over the
previous best) adds a threshold that needs a number, a rationale, and copy,
before anyone knows the noise grates. It can be added later if it does.

### D6 — One toggle, or a choice of styles?

Status: Ratified (2026-08-25)

**Decision: staged. Version one ships an on/off switch with one polished
Confetti effect and the Preview button; a follow-up converts the switch to
a style select with Off plus Confetti, Fireworks, Cannons, and Stars.**

Both reviewers recommended shipping one effect first: the extra styles
multiply a manual-only JavaScript and cancellation surface before any
evidence that style choice matters, and two of the four presets are
loop-based with their own cancellation handling. The maintainer wants the
styles, so the ruling stages them instead of dropping them: the follow-up
is recorded here and in the Delivery plan as its own step, and the styles
table in Design is its specification. To keep that step purely additive,
the persisted value is a style string from the start ("off" or "confetti");
the v1 switch maps onto those two values, so the select only adds values to
an existing contract. Because the store, not the control, is the persisted
value (see Storage), the conversion keeps the saved setting; the reset the
ruling accepted turns out not to be needed. Preview
ships in v1 because it is the only way to see the effect without setting a
personal best. Curated presets only, in both versions: no duration,
particle, or color knobs, and no custom style. A Random option stays out;
it can join the select later if wanted.

### D7 — Does the Run Notifications master switch gate the celebration?

Status: Ratified (2026-08-25)

**Decision: no. The two settings are independent families.**

The style select governs the confetti and the celebration toast together;
the master switch governs the verdict, placement, and catch-up toasts. With
the celebration set to a style and the master switch off, a personal best
still gets confetti and its "New personal best" toast on every page; ordinary
runs stay silent. The toast travels with the animation because it is the
part that carries information (which scenario, what score, by how much); on
a page other than Scenario Performance, confetti without it is a burst with
no explanation, and under reduced motion the toast is the whole celebration.
The master switch's shipped help text enumerates the three shapes it gates,
so a fourth family outside that list breaks no promise, and a user in the
off-plus-style state has asked for two things at once: no narration of
routine runs, and a celebration of personal bests. `product.md` currently
summarizes the switch as "with it off the chart still updates and nothing
toasts about a run"; the ruling amends that sentence to except the
celebration toast, in the same edit D4 makes to the paragraph.

Choosing to let the master switch silence the celebration toast (or the
whole celebration) reads the master-switch proposal's "do not toast me about
runs" rationale more broadly. It also couples the two settings mechanically:
the master switch's persisted value lives on the Scenario Performance page,
so the shell would need a second mirror store to see it, like the style
store in Design.

### D8 — What happens when the tab is hidden at the moment of the best?

Status: Ratified (2026-08-25)

**Decision: hold one pending celebration and play it when the tab next
becomes visible, with a celebration toast that stays until dismissed.**

Chromium on Windows marks a fully occluded window's tab hidden (native
window occlusion tracking), and the player is in KovaaK's fullscreen when a
personal best lands. On a single-monitor setup a hard `document.hidden` drop
therefore means the animation never plays for a real personal best, only
from Preview, and a normal-lifetime toast has usually expired by the time
the player alt-tabs back. The ruling holds at most one pending celebration
(a newer event replaces it) and plays it on the next `visibilitychange` to
visible; the celebration toast is sent with `auto_close=False`, the
existing convention for conditions that fire when nobody may be looking, so
the news is still there on return. This is the only version of the feature
that works on one monitor. The accepted cost, stated with the ruling:
personal best toasts are dismissed by hand on every setup, including one
where the animation played in view. If that grates in practice, relaxing
the toast to the normal lifetime is a one-line follow-up that does not
touch the pending mechanism.

Choosing the hard drop instead is simpler in `pbCelebration.js` and keeps
every toast lifetime uniform, at the cost above; the Copy block's "Works on
every page" would then need qualifying, since on one monitor the animation
would be Preview-only.

The ruling needed no pre-ship evidence, and that asymmetry was the
deciding argument: on a setup where the tab never reports hidden, the
pending path is dormant and behaviour is identical to playing immediately,
while on a setup where occlusion does mark the tab hidden, pending is the
only version that plays at all. It is the hard drop that would need evidence
(that the tab stays visible during real play) to be safe. The maintainer
cannot currently run the occlusion check, so the check moves to a post-ship
observation: a `visibilitychange` console log while KovaaK's runs
fullscreen, whenever that machine is next available. Deferring the whole
behaviour to a follow-up was considered and rejected: v1 would then ship
the drop untested, which is the one variant that can fail invisibly.

## Problem

The watchdog already decides, for every run file, whether the run beat the
scenario's high score (`is_new_high_score` in
`source/my_watchdog/file_watchdog.py`), scenario-wide across all
sensitivities. That flag reaches nothing the user sees: it gates a
background rank refresh and a debug-log line. The run event the Scenario
Performance page consumes carries `nth_score` and `previous_high_score`
instead, and neither reconstructs the flag: `nth_score == 1` is a
per-sensitivity placement (a run can be the best at its sensitivity while a
different sensitivity holds the scenario high score), and
`previous_high_score` is `None` on the new-sensitivity branch.

So the moment the app is best placed to reinforce, the one every run is
chasing, is the moment it says the least. The run toast for a personal best
reads "Threshold passed" or "New best score"; the latter is the
per-sensitivity placement, not the scenario-wide achievement.

The producer side is also page-bound. `message_queue` is drained by an
interval mounted in the Scenario Performance layout and filtered to the
selected scenario, so any feature built on it is blind on every other page
and for every other scenario. The master switch decision-log entry
(2026-08-21) deferred making run toasts app-wide because judging a run
against the selected scenario's threshold does not generalize. A
celebration has no such dependency: it needs "a personal best happened, in
this scenario, with this score", which the watchdog already knows.

## Verified facts

Repository, at `main` as of 2026-08-21:

- `is_new_high_score = run_data.score > high_score` is computed per run in
  the watchdog; strictly greater, scenario-wide
  (`get_high_score(scenario)`). A scenario's first run (Case 1) and a
  sensitivity's first run (Case 2) both enqueue with
  `previous_high_score=None`; Case 2 can be a scenario personal best.
- `NewFileMessage` carries `datetime_created`, so freshness is measurable
  without adding a field. The watchdog handler has the run CSV's path in
  hand at all three message construction sites.
- Scores are unconstrained floats. The threshold path declines to judge a
  run when `previous_high_score <= 0` because there is no usable
  denominator.
- `message_queue` is drained only by `check_for_new_data` on Scenario
  Performance, filtered to the target scenario; non-matching messages are
  dropped, not deferred. The polling interval defaults to 1000 ms.
- The notification container and the toast-lifetime store are shell-hosted
  (`source/app_shell.py`); toasts outlive the page that sent them. The shell
  hosts no interval today.
- `docs/architecture.md` sanctions typed, single-purpose channels from the
  watchdog thread to an interval callback and rules out a general event bus.
  `run_import_failure_queue` is the precedent for a second queue beside
  `message_queue`.
- Settings v1 (`source/utilities/store_schema.py`) is a closed key set of
  three string-valued keys; unknown keys and non-string values are invalid.
  Adding a key is a version bump. The decision log flags the first release
  that migrates data as having to solve the launcher's staged trial-run
  window first, and a file stamped with a newer version is refused by an
  older build, so a rollback after the bump would run with no settings.
- The Settings page is a Save-all-at-once form for those three keys with a
  restart-pending notice; nothing on it uses Dash persistence. The Scenario
  Performance inspector has thirteen browser-persisted controls, the Run
  Notifications master switch (PR #245) among them.
- Browser persistence is per origin; the 2026-07 URL-unification entry in
  the decision log records the app once accumulating disjoint toggle state
  across `localhost` and `127.0.0.1`.
- The score threshold goal input has `min=1` and no maximum.
- `product.md` states: "A new personal best has no toast of its own; it
  triggers the background rank refresh."
- There is no JavaScript lint, test, or build step. `assets/*.js` files are
  served as classic scripts; the local-icon README is the precedent for
  vendoring third-party assets with a license table.
- Since this proposal's baseline, `main` gained capability specs:
  `docs/specs/notifications.md` (which states "A run earns at most one
  notification") and `docs/specs/settings.md`. A behavior-changing PR
  updates its owning spec in the same PR.

Library survey, checked 2026-08-21 against the npm registry, GitHub, and the
upstream demo source:

| Library | License | Size | Deps | Activity | Classic-script global |
|---|---|---|---|---|---|
| canvas-confetti 1.9.4 | ISC | 10.5 KB min, 4.3 KB gz | 0 | 12.7k stars; last push Oct 2025; last release Dec 2024 | `window.confetti` |
| js-confetti 0.13.1 | MIT | ~27 KB unpacked | 0 | 1.3k stars; last push Sep 2025 | `JSConfetti` |
| @tsparticles/confetti 4.3.2 | MIT | 20–100 KB gz | 16 internal packages | active, frequent majors | bundle |
| party-js 2.2.0 | MIT | ~12 KB gz | 0 | last release Jul 2022 | none in package |
| @neoconfetti/vanilla 0.2.1 | MIT | 24 KB unpacked | 0 | Dec 2023 | ESM only |

`canvas-confetti` specifics: options for angle, spread, velocity, decay,
gravity, drift, scalar, ticks, origin, colors, and shapes (square, circle,
star, SVG path, text/emoji); `disableForReducedMotion`; `reset()` to cancel;
a promise on completion; the default instance renders in a web worker via
`OffscreenCanvas` (`useWorker: true, resize: true`) on a canvas it appends to
`document.body`, outside Dash's render root. The unminified source is about
850 readable lines with no in-file license header (the license is a separate
file). It does no `devicePixelRatio` scaling. js-confetti has no physics
options, no reduced-motion handling, and no worker. The rest are out on
weight, staleness, or module format.

Upstream demo recipes, from the `gh-pages` branch:

| Recipe | Mechanism | Runs for |
|---|---|---|
| Realistic Look | 5 staggered calls, ~200 particles, one burst from `y: 0.7` | ~3 s |
| Stars | 3 volleys 100 ms apart, star and circle shapes, no gravity | ~1 s |
| Fireworks | `setInterval` 250 ms, two random-origin pops per tick | 15 s |
| School Pride | `requestAnimationFrame` loop, side cannons at 60° and 120° | 15 s |
| Snow | `requestAnimationFrame` loop, one particle per frame | 15 s |

## Design

**The event.** The watchdog gains a second typed channel,
`pb_celebration_queue: deque[PersonalBestEvent]`, beside
`run_import_failure_queue`. `PersonalBestEvent` carries `run_id`,
`datetime_created`, `scenario_name`, `score`, and `previous_high_score`.
`run_id` is the run CSV's file name: unique per run, already in hand where
the messages are built, and the identity the shell and the page coordinate
on (see "The toast"). The watchdog appends one exactly when
`is_new_high_score` is true. The flag is computed against the scenario-wide
high score and can only be true in Cases 2 and 3; Case 1's first run has
nothing to beat, carries the flag as False, and never celebrates. So the
flag alone means "a celebration event was enqueued for this run", which is
what the page's candidate test relies on. Every enqueue is stamped with
`event_seq`, one
monotonic counter shared by both queues and incremented only by the
watchdog thread, so "has the shell seen this event yet" is a comparison,
not a guess (see the watermark under "The toast"). `NewFileMessage` and
the Scenario Performance `RunEventData` also gain `run_id`, `event_seq`,
and an explicit `is_new_high_score: bool`, set at all three construction
sites, because the page's own toast needs the scenario-wide fact and
cannot derive it (see Problem). The rank refresh
keeps its current trigger; the celebration is not coupled to a network
call.

**The consumer.** The app shell hosts a `dcc.Interval`
(`pb-celebration-interval`, period `config.polling_interval`), a
`dcc.Store` (`pb-celebration-event`) that carries one event to the browser,
and the style store described under Storage. A shell callback drains the
queue on each tick and celebrates at most one event per drain: the newest
fresh one, where fresh means `datetime_created` is within the freshness
window of the drain. The window is relative to the interval,
`max(10 s, 3 × polling_interval)`, because `polling_interval` is an
unbounded config int and an absolute window would silently kill the feature
at large intervals; the multiplier keeps a live event from being judged
stale by its own delivery latency. Anything older is dropped unseen: a
personal best set while no tab was open is never replayed on the next
visit. One event per drain is a contract, not a convenience: a Dash
callback returns one final value per output, so one response can carry one
store payload and drive one animation. An older fresh personal best in the
same drain is not celebrated and not recorded; it falls through to the
ordinary run-toast path, which "The toast" spells out. The callback emits
the celebration toast (below) and records the celebrated `run_id` in
`celebrated_runs`, a bounded server-side registry in `notifications.py`
(the last 64 ids; module-level state shared between callbacks, as
`_last_rank_hints` in `home.py` already is). After every drain, celebrated
or not, it publishes `pb_drain_watermark`, the highest `event_seq` it has
examined, beside the registry; the shell is the only writer of both. With
the setting at Off the drain still advances the watermark while dropping
every event unseen and recording nothing.

This interval is the first poll outside Scenario Performance: it adds one
request per second on every page for the life of the tab, which changes
what idle looks like in devtools and in the waitress log. Acceptable for a
local single-user app, and stated here and in the `architecture.md` update
so nobody reads the traffic as a bug. Folding the page's existing
`interval-component` consumers into one shell interval would put both
drains on the same tick, but that refactor is not this proposal.

**The animation.** A clientside callback on `pb-celebration-event` calls
`window.pbCelebration.play(style)`, defined in a small app-owned file
(`assets/pbCelebration.js`) beside the vendored library. It does nothing
when the style is Off or when the user prefers reduced motion
(`disableForReducedMotion` on the instance, plus the same check around the
app's own loops). When `document.hidden` is true (a fully occluded window
counts as hidden under Chromium's occlusion tracking, and the player is in
KovaaK's fullscreen when this fires) the animation is not dropped: it is
held as the one pending celebration and plays on the next
`visibilitychange` to visible, a newer event replacing any pending one.
That behaviour is D8's ruling; the rejected hard drop is recorded there.
Playing immediately while hidden would also dump a stalled burst on the
next alt-tab, since a hidden tab throttles animation frames. It cancels any
burst still in flight
before starting a new one, so a fast streak never stacks. The store payload
carries a monotonic sequence number so two identical personal bests back to
back both fire. Every style is bounded to at most about three seconds and
returns a cancel handle; `confetti.reset()` clears particles but does not
stop a `setInterval` or animation-frame loop, so the loop-based styles must
not be taken from the demo verbatim.

**Styles.** A name-keyed registry in `pbCelebration.js`, mirrored by the
option list in Python; the two lists agree by convention, and an unknown
name plays Confetti rather than nothing, so a style removed later never
silently turns celebrations off. Version one registers Confetti alone,
behind the on/off switch (D6); the follow-up adds the other three and the
select. The full set, derived from the upstream recipes:

- **Confetti**: the Realistic Look recipe, unchanged.
- **Fireworks**: the Fireworks recipe cut from 15 s to about 3 s.
- **Cannons**: the School Pride recipe cut from 15 s to about 2.5 s, colors
  taken from the app's accent rather than the demo's red and white.
- **Stars**: the Stars recipe, unchanged.

Snow is ambient, not a celebration, and is excluded. Emoji and custom SVG
shapes are possible later styles, not v1.

**The toast.** The celebration toast has its own id, a
`notifications.py` constant distinct from the page's run-verdict id, and it
is sent as the update-plus-show pair with `autoClose` False on both
actions: a sticky variant of `upsert_toast` (a parameter that skips the
alternation, or a sibling helper), because `upsert_toast` as it exists
stamps the alternating lifetimes over `autoClose` and would silently turn
the sticky toast into an ordinary 8 s one. No alternation is needed here:
alternation exists to re-arm a replacement's timer, and a sticky toast has
no timer. The payload's sequence number serves the clientside animation
replay, not the toast lifetime. The shell therefore touches neither the
run-verdict id nor `TOAST_LIFETIME_STORE_ID`: the two producers share no
toast id and no store, so no interleaving of their responses can make one
overwrite the other. That is the point. Both callbacks run on independent
one-second intervals under a multi-threaded server, and Dash does not order
concurrent duplicate-output responses, so any design where both write the
same id is order-dependent no matter how the decision to write is
coordinated. Per D8's ruling the toast stays until dismissed; a dedicated
id is also what lets it survive the next ordinary run toast instead of
being dismissed by it.

On Scenario Performance, the page decides about a candidate run (one with
`is_new_high_score` set; the flag is only ever true when a scenario-wide
previous best exists, exactly when a celebration event was enqueued, so it
alone defines the candidate — a Case 2 personal best is a candidate even
though its run message's `previous_high_score` is `None`) only after the
shell's decision for it is on record: while the run's `event_seq` is above
`pb_drain_watermark`, the toast decision is deferred. The deferral lives in
the page's existing single chain, because `_build_run_event_notification`
only runs when `generate_graph` is triggered by `run-events`, and an empty
drain emits nothing: `check_for_new_data` owns a module-level pending slot.
A tick that drains a candidate still above the watermark parks it there
and forwards it without a toast; a tick that drains nothing while the slot
holds a candidate the watermark has now passed re-emits `run-events` for
that candidate, re-triggering `generate_graph`, whose toast logic is then
purely claimed-yields or unclaimed-narrates; a tick that drains newer
events supersedes and clears the slot, newest wins, as today. The cost is
one extra graph rebuild per deferred candidate, the same price as a run
landing; accepted for simplicity over a payload flag that would skip the
rebuild. No second writer of the run-verdict id or the lifetime store
appears, and re-evaluation cannot starve: the shell interval is mounted in
the same client, so the watermark always advances. Once the watermark has
passed the run, registry membership is final and the answer is definitive:
claimed means the page yields (returns `None`), unclaimed means the page
narrates today's toast. Deferral costs at most a tick or two, only for
candidate runs, and only when the page's interval fires before the shell's
for the same second; non-candidates never defer. The page never reads the
style setting: an Off
drain advances the watermark without recording, which reads as "decided,
not celebrated", and the page narrates.

The backlog digest follows the same rule through its latest run: a claimed
latest run yields the digest (the celebration toast is the fresher news,
and the batch's remaining information is the plot's job), an unclaimed one
narrates as today, and a digest whose latest run is still above the
watermark defers like a live one. This restores the one-notification
contract for digests too; the earlier never-yield shape kept the count on
screen but let one run be narrated twice, which the ratified D4 and the
notifications spec's "A run earns at most one notification" both rule out.

No interleaving of the two callbacks can now produce two toasts for one
run, and none can produce silence: every candidate decision happens after
the shell's decision for that run is recorded, and an uncelebrated
candidate (the older of two fresh personal bests in a single drain, a
stale one, or any candidate under an Off drain) always falls through to
the ordinary run-toast path, which reports its verdict or placement
truthfully. Nothing can replace the celebration toast, because nothing
else writes its id. Rejected alternatives: a shared run-verdict id (any
concurrent interleaving can bury the celebration under a slower ordinary
response); a page-side freshness window (cannot tell which event the shell
chose); a registry check without the watermark (the page can read just
before the shell records, narrating a celebrated run twice); and a
page-local replacement where both producers emit and the later one wins,
whose end state depends on callback order.

With celebrations Off the shell neither celebrates nor records, so the page
never yields and behaves exactly as today (D4).

The toast is informational, so it shows under reduced motion too; only the
animation is skipped.

**Relation to the run notifications master switch.** Per D7, the
celebration is its own family, gated by its own setting. Master off with a
style selected still celebrates a personal best; celebrations Off with master
on reports the personal best through the page's run toast, on Scenario
Performance only, as today. Neither setting reads the other. Guard order in
`_build_run_event_notification`: the master switch's early return stays
first, the celebration yield comes second. So with celebrations Off a
personal best run gets today's run toast, gated by the master switch like
any other; with both settings off, the page is silent and the shell has
nothing to say.

**Storage.** The shell-hosted
`dcc.Store(id="pb-celebration-style", storage_type="local")` is the
setting: one authoritative browser-persisted string, "off" or a style
name. The Settings page control (v1's switch, the follow-up's select)
initializes from it and writes to it through a small callback pair, and
carries no Dash persistence of its own, so the switch's boolean and the
select's string never become two competing persisted values and the
switch-to-select conversion keeps the saved setting. The shell's drain
callback reads the store as `State`. The store's default is Confetti, so a
browser that has never visited Settings celebrates. The known costs of
browser persistence apply and are accepted: per origin, cleared with site
data, and reset if the layout default ever changes. Every one of those
fails toward "celebrations came back", never toward silence. One more
accepted cost: the queues, registry, watermark, and pending slot are
process-wide with per-response delivery, so with two tabs open the
celebration lands in whichever tab's drain runs first and the other tab
sees nothing for that run. This is the single-consumer shape
`message_queue` already has, noted so nobody files it as a bug.

`data/settings.json` was rejected for v1 on cost, not principle. Settings v1
is a closed set of three string keys, so a new key is settings v2: a
validator, a version bump, the stamp script becoming a real migration under
the documented ordering contract, the launcher's trial-run window to be
solved for the first migrating release, and an older build refusing the v2
file on rollback. When a setting that deserves v2 arrives, this preference
joins it. Nothing here forecloses that move; only the store's backing
would change.

**Settings page placement.** A new section after the version section's
divider (or between the form and the version section; author's call at
build time), with its own heading, the control (a switch in version one,
the style select in the follow-up), its description, and the Preview button
in one row. The control applies instantly and does not go through Save; the
restart notice and the store alert concern the form's three keys and are
untouched. Preview plays the currently selected style
through the same clientside path as a real celebration, so it obeys the
reduced-motion guard; it shows no toast. The hidden-tab hold never applies
to Preview, since clicking it requires a visible tab.

**Copy.** Every user-facing string this change adds or edits, in one place,
following the house rules: short sentences, no em dashes.

- Settings section heading: **Celebrations**.
- Control label: **Personal best celebration** (the v1 switch and the
  follow-up's select share it). Description under it: "Plays a short
  animation and shows a toast when a run beats your personal best in any
  scenario. Works on every page, and does not depend on Run Notifications.
  Takes effect right away." The last sentence keeps the section's instant
  model from blurring into the form's Save-then-restart model beside it.
- Follow-up select options, in order: **Off**, **Confetti**, **Fireworks**,
  **Cannons**, **Stars**. These ship with the styles step, not v1; they are
  gathered here so the whole feature's copy is in one block.
- Button beside the control: **Preview**.
- Celebration toast title: **New personal best**. Message, when the
  previous best is positive: "{scenario}: {score}. Up {percent}% on your
  previous best of {previous}." Otherwise: "{scenario}: {score}. Your
  previous best was {previous}." A previous best of zero has no percentage
  to give, and a negative one would make the percentage read backwards; the
  threshold path declines the same division for the same reason. Score and
  previous best to two decimals, percentage to one, matching the run toasts.
  Green, with a trophy icon vendored into `assets/icons/` under the existing
  license table.

The existing run toast bodies keep their em dashes; they belong to the
deferred all-messaging review.

## Delivery plan

Three implementation PRs, smallest reviewable steps first (the
maintainer's stated preference):

1. **Event and toast** (can stand alone): `is_new_high_score` on the run
   message and page payload; `pb_celebration_queue` and `PersonalBestEvent`;
   the shell interval, drain callback, freshness rule, celebrated-run
   registry, and celebration toast; the Scenario Performance yield rule; the
   dedicated celebration toast id and its sticky update-plus-show pair;
   the watermark and deferral rule; the trophy icon; tests. Owning docs in
   the same PR: `docs/specs/notifications.md` (the celebration family, its
   dedicated sticky toast, the preserved one-notification-per-run
   contract, and an amendment to the spec's replaces-rather-than-stacks
   sentence, to which the sticky celebration toast is D8's deliberate
   exception) and the `architecture.md` entries (the new channel, the shell
   interval and stores, the app-wide polling note). Interim state until
   PR 2: the celebration toast is unconditional (the setting does not
   exist yet) and there is no animation; the spec update states that
   interim honestly and PR 2 rewrites it. Acceptable for a single-user app
   across one review window.
2. **Animation and setting** (depends on 1; completes v1 and ships the
   proposal): the vendored library and its license record;
   `pbCelebration.js` with the Confetti effect, the guards, and the D8
   behaviour; the Settings page section, the on/off switch, the
   authoritative style store, and Preview; the clientside callback.
   Owning doc in the same
   PR: `docs/specs/settings.md` (the Celebrations section and its
   browser-local, instant-apply model). The rest of the "Shipping a
   proposal" checklist lands here.
3. **Styles** (the D6 follow-up, any time after v1): the switch becomes the
   style select; Fireworks, Cannons, and Stars join the registry with their
   cancellation handling; the follow-up copy from the Copy block; the
   settings spec's control description updated in the same PR. Tracked
   on the roadmap once this file is deleted.

Plus the shipping checklist from `AGENTS.md`: decision-log entries (the
celebration itself and its storage, the D4 priority amendment, the
Settings-page placement departure, the D7 independence from the master
switch, the D8 hidden-tab ruling), the `product.md` run-notifications
paragraph and a new inventory entry, `architecture.md` (the new channel in
the sanctioned-channels list, the shell's interval and stores, the
app-wide polling note, the asset file), the README, the roadmap, and
deletion of this file.

Dependencies: none. The run notifications master switch (PR #245) has
landed; its guard sits at the top of `_build_run_event_notification`, and
the personal best yield rule slots in beside it as a second independent
early return.

## Out of scope

- **App-wide run toasts.** Verdict, placement, and digest toasts stay on
  Scenario Performance; the deferral recorded in the master switch
  decision-log entry stands. This proposal adds one app-wide family, not a
  general producer.
- **Per-sensitivity personal bests.** The celebration is scenario-wide, like
  the watchdog's flag. A per-sensitivity best is already the placement
  toast's job.
- **Other achievements.** Rank-ups, benchmark tier changes, streaks, and
  session milestones are candidates for the same channel later, each its
  own proposal.
- **Sound.** None; the player is wearing headphones in another application.
- **Noise gating** (D5), a **Random** style, emoji and custom-shape styles,
  and any per-style tuning controls.
- **Settings v2.** The storage move is described so it can happen later; it
  is not part of this change.
- **The wider copy sweep.** Only the strings in the Copy block are new or
  edited.

## Testing

- Watchdog unit tests: Case 1 enqueues no celebration; Case 2 and Case 3
  enqueue exactly one when the score strictly beats the previous high score
  and none on a tie or a lower score; `is_new_high_score` is False on the
  Case 1 message and true on Case 2 and Case 3 messages exactly when the
  celebration event was enqueued, including a Case 2 message whose own
  `previous_high_score` is `None`.
- Shell drain tests: an empty queue is a no-op; a fresh event produces one
  store payload with an incremented sequence, one toast, and one registry
  entry; two fresh personal bests in one drain celebrate and record only
  the newest, and the older is neither toasted nor recorded; a stale event
  is dropped and not recorded; the freshness window equals
  `max(10 s, 3 × polling_interval)`, pinned at the boundary (a live event
  still celebrates at a 10 s and a 30 s interval); the style store at Off
  drops everything and records nothing; the registry is bounded.
- Producer-isolation contract tests: the celebration toast id differs from
  the run-verdict id; the shell callback declares no output on
  `TOAST_LIFETIME_STORE_ID`, and its toast payload carries `autoClose`
  False on both actions of the pair. These pin the no-shared-state
  construction that makes
  concurrent responses unable to overwrite each other; the overlap itself
  is not schedulable from a unit test.
- Toast builder tests: the percentage message for a positive previous best;
  the fallback message for a previous best of zero and for a negative one.
- Scenario Performance tests beside the existing ones in
  `tests/test_home_run_events.py`: a candidate run above the watermark is
  parked (forwarded without a toast, pending slot set), and an
  otherwise-empty later tick re-emits `run-events` for it once the
  watermark passes; a newer drained run supersedes and clears the pending
  slot; a Case 2 candidate whose message `previous_high_score` is `None`
  defers like any other; below the watermark, a claimed run yields
  (returns `None`) whatever its verdict and an unclaimed one gets today's
  toast; a non-candidate never defers; the digest defers, yields, or
  narrates by its latest run under the same rule; an Off drain advances
  the watermark so the page narrates rather than deferring forever; the
  master switch's early return precedes the yield, so master off is silent
  whether or not the run was celebrated (D7). Together these pin the
  one-notification-per-run invariant under any callback order.
- Callback-level checks through a direct POST to `/_dash-update-component`,
  the established way to exercise shell-level outputs here.
- Docs gate: `tests/test_docs.py` for the proposal's section order and
  links.
- Manual: with the app running, the Preview button plays the effect and
  plays nothing with the switch off (each select option, once the styles
  step lands); dropping a run CSV that beats a known
  personal best celebrates on the Playlists page and on Settings, not only
  on Scenario Performance; a CSV older than the freshness window does not;
  the same run with a system reduced-motion preference shows the toast and
  no animation; with the tab occluded during the drop, nothing plays until
  the tab is next visible, then the animation plays once and the toast is
  still up until dismissed (D8). No JavaScript harness exists, so the
  animation file is verified by this manual pass and by review.
