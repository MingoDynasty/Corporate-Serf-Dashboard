# 2026-09-02: A New Personal Best Celebrates On Every Page

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
interval to about one tick per minute — and a tab can stay hidden through a
whole session, minimized or behind another tab, so a tight window would drop
exactly the mid-session personal bests this exists for. The poll period is
added because `polling_interval` carries no product cap: a run can be a
whole period old through nothing but the drain's
cadence, and a fixed cap below the configured period would stamp every run
stale and silently retire every toast liveness gates. The consequence, stated
rather than hidden: a deliberately slow poll widens no-tab replay by exactly
the period it chose. Validating the interval with a product cap instead stays
rejected, for the reasons in
[2026-09-01](2026-09-01-configured-ports-and-poll-intervals-are-bounded-at-load.md).

**The toast.** Green, a trophy icon, titled "New personal best", and sent with
`auto_close=False` so it is still there on alt-tab. Its channel key is
`pb-celebration`, deliberately not `run-verdict`: an ordinary run toast lands
beside it rather than replacing it, and only a later celebration replaces a
celebration. It is a persistent channel in the sense the
[2026-08-31 toast-identity entry](2026-08-31-repeatable-toasts-replace-in-place-with-a-visible-re-entry.md)
defines, and that entry owns the mechanism.

**The celebration takes the headline.** When celebrations are on, the
celebrated run's one toast *is* the celebration toast and the page's run toast
yields. The score threshold goal has no upper bound, so a goal above 100% let
a personal best read "Below threshold" while confetti fell, and even under a
goal it passes, "Threshold passed" says the less interesting thing. This
amends the priority rule in
[2026-08-03](2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy.md)
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

**A hidden tab holds the animation.** The ruling assumed that Chromium marks a
fully occluded window's tab hidden. The player is in KovaaK's fullscreen when a
personal best lands, so under that assumption a hard `document.hidden` drop
would mean the animation never plays for a real personal best on a
single-monitor setup — only from Preview. At most one celebration is held
instead, a newer one replacing it, and it plays
on the next `visibilitychange` to visible; playing while hidden would also
dump a stalled burst on the next alt-tab, since a hidden tab throttles
animation frames. The accepted cost, stated with the ruling: personal best
toasts are dismissed by hand on every setup, including one where the animation
played in view. Relaxing the toast to the normal lifetime is a one-line
follow-up that does not touch the pending mechanism. The ruling needed no
pre-ship evidence, and the asymmetry was the deciding argument: where the tab
never reports hidden the pending path is dormant and behaviour is identical,
and where occlusion does mark it hidden, pending is the only version that
plays at all. The post-ship check, run on 2026-09-28, did not bear out the
occlusion premise: on one Windows 11 machine (three monitors, both browsers
moved onto the game's), Firefox 156 and Edge 154 never reported a tab hidden
while KovaaK's covered the whole window, in borderless and exclusive
fullscreen alike, though minimizing did. The ruling stands on its asymmetry.
Where the game only covers the window, the pending path is dormant, the burst
plays unseen under the game, and the sticky toast is what the player comes
back to; a minimized window or a background tab still holds the burst.

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
[2026-07-06 coalescing entry](2026-07-06-coalesce-pending-home-run-events.md)
loses its "sole consumer" clause — the shell's drain is the consumer now and
the page listens to a store — and its digest. Its coalescing rule survives,
applied to the batch: the page still considers only the latest matching run.
The [2026-08-21 master-switch entry](2026-08-21-run-notifications-have-a-master-switch-and-the-threshold-switch-is-renamed.md)
loses the digest from the set of shapes its gate covers, and its deferral of
the queue-to-UI redesign for the drain alone; the product question that
deferral protected, app-wide verdict toasts, stays deferred, and run toasts
remain page-built and page-scoped. The
[2026-08-03 notification-layer entry](2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy.md)
loses its rule that a personal best earns nothing beyond the run verdict, and
the "backlog digest included" clause of its replacement rule.

**Superseded in part, for copy (2026-09-14).** The master switch this entry
calls Run Notifications is labelled "Run notifications", and the celebration
description names it in bold: "…and doesn't depend on **Run notifications**."
The decision is unchanged. See [App Copy Follows One Set Of Rules, And The Em Dash Is Gated Out](2026-09-14-app-copy-follows-one-set-of-rules-and-the-em-dash-is-gated-out.md).

**Superseded in part (2026-10-13).** "Run toasts remain page-built and
page-scoped" no longer holds, and the question that sentence deferred,
app-wide run toasts, is answered: the app shell's drain builds the run toast,
on every page, with no verdict. The page's part in the coalescing rule is gone
with it: the shell picks the batch's newest live run, whatever its scenario.
The celebration stands in full, as do one notification per run at most and the
two settings staying independent. See
[A Run Toast Is Plain And Shows On Every Page](2026-10-13-a-run-toast-is-plain-and-shows-on-every-page.md).

Shipped in PRs #261 and #268; proposal and rulings in #248, toast mechanism
reconciled in #263. Distilled from the personal best celebration proposal, now
deleted.
