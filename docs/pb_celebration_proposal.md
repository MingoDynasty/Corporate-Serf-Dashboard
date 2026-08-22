# Personal Best Celebration

Status: Proposed
Date: 2026-08-21

## TL;DR

When a run beats a scenario's personal best, the app should throw a short
celebration: a burst of confetti and one toast that says so. Today a new
personal best earns nothing on screen except a quiet rank refresh. The
celebration fires on every page and for every scenario, because a personal
best is an achievement regardless of what the user happens to be looking at.
A setting on the Settings page picks the animation style or turns it off.

## Decisions needed

Every decision below is open. Each carries the current lean from the design
conversation of 2026-08-21 so the trade-off is concrete; none is ratified.

### D1 — Does the celebration fire on every page, for every scenario?

Status: Open. Lean: **yes, app-wide.**

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

Status: Open. Lean: **a control on the Settings page, persisted in the
browser, in its own section outside the Save form.**

The behavior is app-wide, so the Chart options inspector on one page is the
wrong home: undiscoverable, and a control there describes itself as a chart
option. The Settings page is the UI home. Storage stays browser-local Dash
persistence rather than `data/settings.json`, for the reasons in Design
("Storage"): the settings store's versioning contract makes the first key
addition a real migration with a rollback cost, which a cosmetic preference
should not be the thing to trigger.

This departs from the placement rule the point customization entry and the
run notifications proposal both state, that the inspector owns
browser-persisted presentation preferences. The departure is deliberate and
narrow: that rule governs preferences about the chart; this preference is
about the app. The Settings page section is also the first browser-persisted
control on that page, beside a form whose three fields are written to disk
behind Save. The section is visibly separate and its control applies
instantly, so the form's contract is untouched.

Choosing the inspector instead keeps the placement rule intact and is
marginally cheaper. Choosing `data/settings.json` instead is the
settings-v2 migration described in Design, and should wait for a setting that
deserves it; this one would be folded into that version when it comes.

### D3 — Vendor `canvas-confetti`, or hand-roll the animation?

Status: Open. Lean: **vendor `canvas-confetti` 1.9.4 (ISC), unminified.**

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

Status: Open. Lean: **yes.** A personal best run gets the celebration toast
("New personal best") and no threshold verdict toast.

Today a personal best has no toast of its own; the threshold verdict
headlines when there is one, and a placement otherwise. The score threshold
goal has no upper bound, so a goal above 100% lets a personal best read
"Below threshold" while confetti falls, which is contradictory on screen.
Even with a goal at or under 100% (where a personal best always passes), a
"Threshold passed" headline under confetti says the less interesting thing.

This amends the run-notification priority rule recorded in `product.md`.
Choosing to keep the verdict headline instead preserves that rule and the
"need N%" detail for goals above 100%, at the cost of the contradiction.

### D5 — Ship without a noise gate for young scenarios?

Status: Open. Lean: **yes, ungated.**

Early in a scenario's life most runs are personal bests, so a freshly
imported playlist celebrates nearly every run for a session, which is when
it means least. The lean is to ship with the one gate that is clearly right
(an existing personal best must be beaten; a scenario's first run sets a
baseline and is never celebrated) and let the setting be the escape hatch.
This follows the repo's accepted-limitation habit: document the gap, point at
the existing control, stop.

Choosing a gate instead (a minimum run count, or a minimum margin over the
previous best) adds a threshold that needs a number, a rationale, and copy,
before anyone knows the noise grates. It can be added later if it does.

### D6 — One toggle, or a choice of styles?

Status: Open. Lean: **a choice of styles, as one control with Off.**

`canvas-confetti`'s demo recipes give four distinct short effects for the
price of a lookup table (see Design, "Styles"): Confetti, Fireworks,
Cannons, Stars. The lean is a single select with Off plus those four,
defaulting to Confetti, and a Preview button beside it, because with several
styles the only other way to see one is to set a personal best. Curated
presets only: no duration, particle, or color knobs, and no custom style.

Choosing a plain on/off switch instead is simpler by one control and a few
strings, and converting it into a select later resets the persisted value
once. A Random option (a style per personal best) is cheap and is left out of
the lean only to keep the copy block short; say the word and it joins the
list.

### D7 — Does the Run Notifications master switch gate the celebration?

Status: Open. Lean: **no. The two settings are independent families.**

The style select governs the confetti and the celebration toast together;
the master switch governs the verdict, placement, and catch-up toasts. With
the celebration set to a style and the master switch off, a personal best
still gets confetti and its "New personal best" toast on every page; ordinary
runs stay silent. The toast travels with the animation because it is the
part that carries information (which scenario, what score, by how much); on
a page other than Scenario Performance, confetti without it is a burst with
no explanation, and under reduced motion the toast is the whole celebration.
The master switch's ratified help text enumerates the three shapes it gates,
so a fourth family outside that list breaks no promise, and a user in the
off-plus-style state has asked for two things at once: no narration of
routine runs, and a celebration of personal bests.

Choosing to let the master switch silence the celebration toast (or the
whole celebration) reads the master-switch proposal's "do not toast me about
runs" rationale more broadly. It also couples the two settings mechanically:
the master switch's persisted value lives on the Scenario Performance page,
so the shell would need a second mirror store to see it, like the style
store in Design.

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
and for every other scenario. The run notifications master switch proposal
deferred making run toasts app-wide because judging a run against the
selected scenario's threshold does not generalize. A celebration has no such
dependency: it needs "a personal best happened, in this scenario, with this
score", which the watchdog already knows.

## Verified facts

Repository, at `main` as of 2026-08-21:

- `is_new_high_score = run_data.score > high_score` is computed per run in
  the watchdog; strictly greater, scenario-wide
  (`get_high_score(scenario)`). A scenario's first run (Case 1) and a
  sensitivity's first run (Case 2) both enqueue with
  `previous_high_score=None`; Case 2 can be a scenario personal best.
- `NewFileMessage` carries `datetime_created`, so freshness is measurable
  without adding a field.
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
  Performance inspector has twelve browser-persisted controls.
- Browser persistence is per origin; the 2026-07 URL-unification entry in
  the decision log records the app once accumulating disjoint toggle state
  across `localhost` and `127.0.0.1`.
- The score threshold goal input has `min=1` and no maximum.
- `product.md` states: "A new personal best has no toast of its own; it
  triggers the background rank refresh."
- There is no JavaScript lint, test, or build step. `assets/*.js` files are
  served as classic scripts; the local-icon README is the precedent for
  vendoring third-party assets with a license table.

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
`run_import_failure_queue`. `PersonalBestEvent` carries `datetime_created`,
`scenario_name`, `score`, and `previous_high_score`. The watchdog appends one
exactly when `is_new_high_score` is true and a previous high score exists
(Cases 2 and 3); Case 1 never celebrates. `NewFileMessage` and the Scenario
Performance `RunEventData` also gain an explicit `is_new_high_score: bool`,
set at all three construction sites, because the page's own toast needs the
scenario-wide fact and cannot derive it (see Problem). The rank refresh keeps
its current trigger; the celebration is not coupled to a network call.

**The consumer.** The app shell hosts a `dcc.Interval`
(`pb-celebration-interval`, period `config.polling_interval`), a
`dcc.Store` (`pb-celebration-event`) that carries one event to the browser,
and the setting mirror described under Storage. A shell callback drains the
queue on each tick. It celebrates at most once per drain: the newest event
wins, and only if it is fresh, meaning `datetime_created` is within a short
window of the drain. The window must comfortably exceed the polling interval
so a live event is never judged stale by its own delivery latency; 10 s is
the working value, author-owned. Anything older is dropped unseen: a
personal best set while no tab was open, or while the app was closed, is
never replayed on the next visit. The callback also emits the celebration
toast (below) through the shared notification container, using
`upsert_toast` with the shell's lifetime counter.

**The animation.** A clientside callback on `pb-celebration-event` calls
`window.pbCelebration.play(style)`, defined in a small app-owned file
(`assets/pbCelebration.js`) beside the vendored library. It does nothing when
the style is Off, when `document.hidden` is true (a background tab throttles
animation frames and would dump a stalled burst on the next alt-tab; the
player is in KovaaK's fullscreen when this fires), or when the user prefers
reduced motion (`disableForReducedMotion` on the instance, plus the same
check around the app's own loops). It cancels any burst still in flight
before starting a new one, so a fast streak never stacks. The store payload
carries a monotonic sequence number so two identical personal bests back to
back both fire. Every style is bounded to at most about three seconds and
returns a cancel handle; `confetti.reset()` clears particles but does not
stop a `setInterval` or animation-frame loop, so the loop-based styles must
not be taken from the demo verbatim.

**Styles.** A name-keyed registry in `pbCelebration.js`, mirrored by the
option list in Python; the two lists agree by convention, and an unknown name
plays Confetti rather than nothing, so a style removed later never silently
turns celebrations off. The v1 set, derived from the upstream recipes:

- **Confetti**: the Realistic Look recipe, unchanged.
- **Fireworks**: the Fireworks recipe cut from 15 s to about 3 s.
- **Cannons**: the School Pride recipe cut from 15 s to about 2.5 s, colors
  taken from the app's accent rather than the demo's red and white.
- **Stars**: the Stars recipe, unchanged.

Snow is ambient, not a celebration, and is excluded. Emoji and custom SVG
shapes are possible later styles, not v1.

**The toast.** The shell's celebration toast reuses the run-verdict toast id,
which moves from `home.py` to `notifications.py` as a shared constant, so a
personal best toast and the next run's verdict replace each other exactly as
two run toasts do today. On Scenario Performance, the page's own live run
toast yields for a personal best run when celebrations are on (the page reads
the setting mirror as `State`): `_build_run_event_notification` returns
`None` for a live event whose `is_new_high_score` is set, leaving the shell's
toast as the one toast that run earns. The backlog digest is unaffected,
since the shell never replays a stale personal best; a digest whose latest
run is a personal best headlines it per D4. With celebrations Off the page
behaves as today, except that a personal best run's own toast headlines the
personal best (D4) instead of the verdict. The invariant: a personal best
run earns exactly one toast on any page, from exactly one producer. The
alternative considered, a page-local replacement where both producers emit
and the later one wins, depends on callback ordering within a tick and was
rejected.

The toast is informational, so it shows under reduced motion too; only the
animation is skipped.

**Relation to the run notifications master switch.** Per D7, the
celebration is its own family, gated by its own setting. Master off with a
style selected still celebrates a personal best; celebrations Off with master
on reports the personal best through the page's run toast, on Scenario
Performance only, as today. Neither setting reads the other.

**Storage.** Browser-local Dash persistence on the select, as every other UI
preference is stored. Because the consumer is shell-level and the Settings
page is not always mounted, the select mirrors its value into a shell-hosted
`dcc.Store(id="pb-celebration-style", storage_type="local")` through a small
callback, and the shell's drain callback and the Scenario Performance yield
rule read that store as `State`. The store's default is Confetti, so a
browser that has never visited Settings celebrates. The known costs of
browser persistence apply and are accepted: per origin, cleared with site
data, and reset if the layout default ever changes. Every one of those fails
toward "celebrations came back", never toward silence.

`data/settings.json` was rejected for v1 on cost, not principle. Settings v1
is a closed set of three string keys, so a new key is settings v2: a
validator, a version bump, the stamp script becoming a real migration under
the documented ordering contract, the launcher's trial-run window to be
solved for the first migrating release, and an older build refusing the v2
file on rollback. When a setting that deserves v2 arrives, this preference
joins it. Nothing here forecloses that move; only the select's persistence
and the mirror would change.

**Settings page placement.** A new section after the version section's
divider (or between the form and the version section; author's call at
build time), with its own heading, the select, its description, and the
Preview button in one row. The select applies instantly and does not go
through Save; the restart notice and the store alert concern the form's
three keys and are untouched. Preview plays the currently selected style
through the same clientside path as a real celebration, so it obeys the
reduced-motion and hidden-tab guards; it shows no toast.

**Copy.** Every user-facing string this change adds or edits, in one place,
following the house rules: short sentences, no em dashes.

- Settings section heading: **Celebrations**.
- Select label: **Personal best celebration**. Description under it: "Plays a
  short animation and shows a toast when a run beats your personal best in
  any scenario. Works on every page, and does not depend on Run
  Notifications."
- Select options, in order: **Off**, **Confetti**, **Fireworks**,
  **Cannons**, **Stars**.
- Button beside the select: **Preview**.
- Celebration toast title: **New personal best**. Message: "{scenario}:
  {score}. Up {percent}% on your previous best of {previous}." with the score
  and previous best to two decimals and the percentage to one, matching the
  run toasts. Green, with a trophy icon vendored into `assets/icons/` under
  the existing license table.
- Scenario Performance, D4 case with celebrations Off: the live run toast
  for a personal best run uses the same title and message as the celebration
  toast, with the existing placement detail dropped (a personal best is
  trivially the best at its sensitivity) and the threshold verdict omitted.
  The backlog digest whose latest run is a personal best keeps its "While
  you were away" shape and headlines **New personal best** in place of the
  verdict.

The existing run toast bodies keep their em dashes; they belong to the
deferred all-messaging review.

## Delivery plan

One implementation PR, with an optional split if review prefers smaller
diffs:

1. **Event and toast** (can stand alone): `is_new_high_score` on the run
   message and page payload; `pb_celebration_queue` and `PersonalBestEvent`;
   the shell interval, drain callback, freshness rule, and celebration toast;
   the Scenario Performance yield rule and the D4 headline; the shared toast
   id; the trophy icon; tests.
2. **Animation and setting** (depends on 1): the vendored library and its
   license record; `pbCelebration.js` with the four styles and guards; the
   Settings page section, the select, the mirror store, and Preview; the
   clientside callback.

Plus the shipping checklist from `AGENTS.md`: decision-log entries (the
celebration itself and its storage, the D4 priority amendment, the
Settings-page placement departure, the D7 independence from the master
switch), the `product.md` run-notifications
paragraph and a new inventory entry, `architecture.md` (the new channel in
the sanctioned-channels list, the shell's interval and stores, the asset
file), the README, the roadmap, and deletion of this file.

Dependencies: none hard. Soft: the run notifications master switch
implementation PR edits `_build_run_event_notification` and the inspector;
whichever lands second rebases over a small conflict with no semantic
interaction, since that switch and this setting gate different families.

## Out of scope

- **App-wide run toasts.** Verdict, placement, and digest toasts stay on
  Scenario Performance; the deferral in the run notifications proposal
  stands. This proposal adds one app-wide family, not a general producer.
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
  and none on a tie or a lower score; `is_new_high_score` is set correctly
  on the run message in all three cases.
- Shell drain tests: an empty queue is a no-op; a fresh event produces one
  store payload with an incremented sequence and one toast; several events in
  one drain celebrate only the newest; a stale event is dropped with no
  output; the style store at Off suppresses both the payload and the toast.
- Scenario Performance tests beside the existing ones in
  `tests/test_home_run_events.py`: a live personal best event yields (returns
  `None`) when celebrations are on and headlines "New personal best" when
  they are off; the backlog digest headlines it either way; non-personal-best
  events are unchanged; the master switch's value has no effect on any of
  the above (D7).
- Callback-level checks through a direct POST to `/_dash-update-component`,
  the established way to exercise shell-level outputs here.
- Docs gate: `tests/test_docs.py` for the proposal's section order and
  links.
- Manual: with the app running, the Preview button plays each of the five
  options (Off plays nothing); dropping a run CSV that beats a known
  personal best celebrates on the Playlists page and on Settings, not only
  on Scenario Performance; a CSV older than the freshness window does not;
  the same run with a system reduced-motion preference shows the toast and
  no animation. No JavaScript harness exists, so the animation file is
  verified by this manual pass and by review.
