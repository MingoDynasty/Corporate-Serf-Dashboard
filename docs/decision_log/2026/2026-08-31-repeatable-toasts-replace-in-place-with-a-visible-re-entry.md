# 2026-08-31: Repeatable Toasts Replace In Place With A Visible Re-Entry

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
