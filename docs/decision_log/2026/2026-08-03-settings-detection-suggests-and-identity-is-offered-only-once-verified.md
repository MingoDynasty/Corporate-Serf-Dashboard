# 2026-08-03: Settings Detection Suggests, And Identity Is Offered Only Once Verified

Status: Accepted; the single-runtime-writer clause is narrowed by the
2026-08-11
["A Fresh Install Is Asked Once, On A Card Keyed To Key Absence"](2026-08-11-a-fresh-install-is-asked-once-on-a-card-keyed-to-key-absence.md)
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
