# 2026-08-11: A Fresh Install Is Asked Once, On A Card Keyed To Key Absence

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
["Settings Detection Suggests, And Identity Is Offered Only Once Verified"](2026-08-03-settings-detection-suggests-and-identity-is-offered-only-once-verified.md)
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
["A Committed Side Effect Reports Its Outcome Even When A Later Write Fails"](2026-08-02-a-committed-side-effect-reports-its-outcome-even-when-a-later-write-fails.md)
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

**Superseded in part, for copy (2026-09-14).** The card's fine print reads
"Skipping keeps position lookups off. You can add your username anytime in
Settings.", and State B's body reads "No KovaaK's stats folder was found, so
this app can't read your runs yet. Set it in Settings." The deferral in the
em-dash paragraph above is discharged: the sweep of all app messaging shipped,
and the em-dash rule is now one of nine copy rules, gated by a test. Triggers,
states, and Skip are unchanged. See [App Copy Follows One Set Of Rules, And The Em Dash Is Gated Out](2026-09-14-app-copy-follows-one-set-of-rules-and-the-em-dash-is-gated-out.md).

Provenance: distilled from `docs/initial_setup_proposal.md` (proposed in PR
#231), shipped in PRs #235 (the companion playlists-overview status line,
which gives the overview grid the same unset-username explanation the
drill-down page already had) and #236 (the card); the proposal file is deleted
in the shipping PR and git history holds its full text.
