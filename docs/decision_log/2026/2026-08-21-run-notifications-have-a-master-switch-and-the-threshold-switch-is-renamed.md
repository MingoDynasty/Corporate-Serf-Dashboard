# 2026-08-21: Run Notifications Have A Master Switch, And The Threshold Switch Is Renamed

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

**Superseded in part, for copy (2026-09-14).** The two control names this
entry sets are sentence case: "Run notifications" and "Score threshold
verdict". The verdict switch's help text names the master switch in bold,
"Needs **Run notifications** turned on." What each switch gates is unchanged.
See [App Copy Follows One Set Of Rules, And The Em Dash Is Gated Out](#2026-09-14-app-copy-follows-one-set-of-rules-and-the-em-dash-is-gated-out).

Shipped in PR #245; design discussion in #240. Distilled from
`docs/run_notifications_switch_proposal.md`, now deleted.
