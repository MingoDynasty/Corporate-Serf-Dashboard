# Initial Setup Flow

Status: Proposed
Date: 2026-08-11

## TL;DR

A fresh install usually charts runs with no configuration at all, because the
app finds the stats folder on its own. But nothing tells a new user that
leaderboard ranks exist or how to turn them on, and when the automatic folder
detection misses, only one page explains why everything is empty. This
proposal adds a small setup card to the landing page that appears until each
setting has been asked about once, and a one-line explanation on the playlist
overview. The card only navigates to the Settings page or records a decline;
it never detects, never writes paths, and never blocks the app.

## Decisions needed

None open. The core design was settled with the maintainer in the
2026-08-11 design session and is recorded under "Ratified decisions" below;
the two decisions this proposal opened with were ratified by the maintainer
during review, so both delivery-plan PRs are unblocked:

- **D1 — State B card title.** Status: Ratified (2026-08-11). The title is
  "Finish setting up". Rejected alternative: a more technical title naming
  the stats-folder failure, which would repeat the body without improving
  the action.
- **D2 — Ship the playlist-overview status line first, as its own PR.**
  Status: Ratified (2026-08-11). The status line ships as PR 1. Rejected
  alternatives: folding it into the card PR, which couples an
  uncontroversial one-line fix to the larger review, and dropping it, which
  leaves the overview grid silent about why every percentile reads N/A.

## Problem

A first launch with no `data/settings.json` is two different situations, and
today the app explains itself well in neither.

**The common case: the folder finds itself, identity stays dark.** The
startup bootstrap
(see the 2026-08-02
["Restart-Scoped Settings Are Pinned At Boot, And The Stats Folder Finds Itself"](decision_log.md#2026-08-02-restart-scoped-settings-are-pinned-at-boot-and-the-stats-folder-finds-itself)
entry) silently writes `stats_dir` on any machine where Steam and KovaaK's
are installed normally, before the first page render, so charts work
immediately. Identity is never auto-set — the bootstrap is deliberately the
app's only silent writer (see the 2026-08-03
["Settings Detection Suggests, And Identity Is Offered Only Once Verified"](decision_log.md#2026-08-03-settings-detection-suggests-and-identity-is-offered-only-once-verified)
entry) — so every rank feature is dark: the Scenario Performance Position
field reads N/A, both playlist pages show N/A percentiles, and the percentile
warmup worker never starts (visible only in the log). The existing dimmed
hints explain some of this at the point of impact (the Position field's
"set your KovaaK's username" hint in `source/pages/home.py`; the drill-down
status line in `source/pages/playlist_scenarios.py`), but they presuppose the
user is already looking at a rank surface. Nothing proactively tells a new
user the feature exists — the discoverability question deferred out of
settings detection, named in `docs/roadmap.md` as still needing a proposal.

**The rescue case: the bootstrap misses.** No Steam, or a nonstandard
install: nothing is written, the scan and watchdog are skipped, and the app
serves with every scenario control empty. Exactly one surface says why — the
dimmed one-line hint on the landing page (`_stats_dir_hint()` in
`source/pages/home.py`, pinned by `tests/test_home_stats_dir_hint.py`). The
playlist overview renders every bundled benchmark row as `0/N`, `Never`, and
N/A percentiles with no explanation at all (its status line stays empty
whenever rows exist, `source/pages/playlists.py`).

So the fresh-install problem is not a data-entry burden — setup is one
Detect click plus Save on the shipped Settings page — it is a communication
gap: the app silently looks broken in places, and its one optional feature
is invisible unless stumbled upon.

Market patterns agree on the shape of the fix. Blocking first-run wizards
suit apps whose required configuration is mandatory and multi-valued — OBS's
auto-configuration wizard is the canonical example — which this app's is
not; the shipped bootstrap-plus-Settings-page architecture already matches
the alternative pattern of self-configuring silently with a manual fallback.
What the app lacks is the widely used getting-started card (a dismissible
setup surface on the home screen) and empty states that state their cause
and link the fix.

## Design

### Ratified decisions (2026-08-11)

Settled with the maintainer; reviewers should treat these as fixed.

1. **A single-CTA card on the landing page, and only there** — today `/`
   (Scenario Performance); if a dedicated Home page ever ships, the card
   moves with it. No wizard, no modal, no tour, no per-page banners.
2. **The card is navigation and dismissal only.** It links to `/settings`
   (where Detect already lives) and can record a decline. It never embeds a
   second detection UI and never touches the network — opening a page never
   spends a request.
3. **Triggers are key absence, per item.** The card is the "never asked"
   surface: each section shows only while its `settings.json` key is absent.
   The existing dimmed hints remain the "degraded state" surface (deliberate
   `""`, vanished path). Once a key exists — any value — the card can never
   come back for it.
4. **Skip is identity-only, surgical, and permanent.** Skip renders only
   when the account is the sole missing item, and writes
   `kovaaks_username: ""` — the shipped empty-means-off semantics — through
   a locked settings-service operation that alters no other key, so an
   absent `stats_dir` stays absent and the bootstrap keeps retrying on
   later boots. Recovery from a decline is the Settings page plus the
   point-of-impact hints; the card itself never returns.
5. **Card copy** (final; no em dashes in app copy, per the same session):
   State A title "Add your KovaaK's account", body "See your leaderboard
   position and percentiles for every scenario.", buttons "Open Settings"
   and "Skip", fine print "Skipping username disables rank lookups. You can
   set it anytime in Settings." State B title "Finish setting up" (D1),
   body "No KovaaK's stats folder was found, so the dashboard can't read
   your runs yet. Set it in Settings."
6. **Alternatives rejected:** a blocking wizard (heavier than the problem;
   modals are also unverifiable in the automated browser pane); a per-setting
   row checklist (scales poorly if settings grow); a dedicated
   dismissed-flag key (persists a distinction no consumer reads — runtime
   already treats `""` and absent identically everywhere, and it would grow
   the flat schema with UI state); session-only dismissal (reappears every
   boot — nagging).

### Card behavior

The card renders from the landing page's layout using the stored settings
view (`get_settings()`), the same view the Settings page renders from — not
the process-pinned accessors. Two independent conditions:

- `stats_dir` key absent → **State B**: the "Finish setting up" title, the
  State B body, one "Open Settings" button. No Skip — the app is useless
  without the folder, so this state is not dismissible. State B wins
  whenever both keys are absent.
- `stats_dir` key present, `kovaaks_username` key absent → **State A**: the
  identity ask with "Open Settings", "Skip", and the fine print.
- Both keys present → no card, permanently.

While a saved stats-dir change is pending restart
(`is_stats_dir_change_pending()`), the card is suppressed: the user is
mid-setup, the existing "Settings saved — restart the dashboard to apply
them." hint owns the moment, and piling the identity ask on top would stack
banners. After the restart the card reappears as State A if identity is
still unasked. The card never claims completion; restart honesty stays with
the Settings page's existing save statuses and notices.

Skip's callback follows the repo's DashProxy discipline: guarded on
`n_clicks` and `ctx.triggered_id` with a None-trigger regression test (an
`allow_duplicate` callback can fire once on page load despite
`prevent_initial_call`). Its write is a new narrow settings-service
operation — an identity decline — that re-reads the stored mapping and
writes it back with only the username key set to `""`, entirely inside the
service's existing module lock (the same `RLock` every read and
`save_settings` take). That makes "alters no other key" an invariant of the
operation rather than a read-merge-write sequence in a page callback, which
a concurrent Settings save could interleave with: a stale snapshot taken at
card render must never restore an old `stats_dir` or `steam_id` over values
saved since. The shipped `save_settings` keeps its replace-all contract and
its pinning test untouched.

This is deliberately a second runtime write path, and it narrows the
2026-08-03 decision that the store keeps a single runtime writer (see
["Settings Detection Suggests, And Identity Is Offered Only Once Verified"](decision_log.md#2026-08-03-settings-detection-suggests-and-identity-is-offered-only-once-verified)):
the Settings page's Save remains the only runtime writer of *values*; the
decline operation can only record "asked and declined" for identity, never
a value. The card PR's decision-log entry records this narrowing against
the earlier entry — and updates the "one runtime writer" claim in
`source/pages/settings.py`'s module docstring — rather than silently
contradicting either. The callback does not start the percentile warmup
worker (the username is empty), and it removes the card in place — no
restart, nothing pins (the identity pin freezes only on a non-empty read).

The bare stats-dir hint cedes its "never configured" case to the card: the
hint's unconfigured branch shows only when the `stats_dir` key is *present*
but unusable (deliberate `""`, or a stored path that no longer exists), so
one condition is explained by exactly one surface. Its restart-pending
branch is unchanged.

Interactions with shipped behavior, for the reviewer's checklist: the first
identity save on the Settings page still applies live and cold-starts the
warmup worker (the card's "Open Settings" path inherits this — the happy
path never sees a restart prompt); a normal Settings save writes all three
keys, so any save also retires the card — correct, since a user who saved a
blank form has seen the fields and chosen empty; `steam_id` never appears on
the card (it blocks nothing; Detect fills it when applicable). Mixed
presence states (e.g. `stats_dir: ""` with `kovaaks_username` absent) are
unreachable through the app because every Settings save writes all keys;
under a hand-edited file the card and hint each still state something true,
which is sane enough.

### Companion fix: the playlist overview explains itself

The overview's status line (currently empty whenever rows exist) gains the
username case, mirroring the drill-down page one level up: "Percentiles
unavailable. Set your KovaaK's username in Settings." with "Settings" as the
in-app link, shown whenever the username is unset (absent or `""` — this is
a degraded-state surface, so it uses the same truthiness the rank code
uses). The copy is dash-free per the ratified rule; the shipped drill-down
sibling keeps its em dash until the deferred app-wide messaging review.

### Blast radius

`source/config/settings_service.py` (one narrow, locked identity-decline
operation), `source/pages/home.py` (card, hint-branch narrowing, Skip
callback), `source/pages/playlists.py` (status line),
`source/pages/settings.py` (module docstring only: the "one runtime writer"
claim gains the decline exception), `assets/stylesheet.css` (card classes),
tests. No changes to the bootstrap, the detection engines, the settings
schema, `save_settings`, `api_service`, or the warmup worker.

## Delivery plan

- **PR 1 — overview status line.** The companion fix alone: one status-line
  branch on the playlists overview plus its test. No dependencies. D2
  ratified 2026-08-11.
- **PR 2 — the setup card.** Card states, hint-branch narrowing, the
  identity-decline service operation with its writer-narrowing decision-log
  entry, and their tests. No hard dependency on PR 1; soft-ordered after
  it. D1 ratified 2026-08-11.

## Out of scope

- The em-dash sweep of shipped copy — deferred (2026-08-11 ruling) to a
  future review of all app messaging; the temporary old-vs-new inconsistency
  is accepted.
- A dedicated Home page; the card rides whatever page is `/`.
- Re-detection or account-switch UX — restart-scoped by the pinning
  decisions; lives on the Settings page.
- Any new `settings.json` keys, and any change to bootstrap or detection
  behavior.
- In-app run-data onboarding beyond the card (sample data, demo mode).

## Testing

- Card state matrix over key presence: absent/`""`/set for both keys —
  State B precedence, State A, no-card, and the never-resurrect cases
  (deliberate `""`, stored-but-vanished path show hint, not card).
- Restart-pending suppression: saved stats-dir change hides the card and
  shows the existing pending hint.
- Skip: writes `""` to the username key only; an absent `stats_dir` key is
  still absent afterwards; the card is gone on the next render; the warmup
  worker is not started; None-trigger DashProxy regression test.
- Identity-decline atomicity: a Settings save that lands after a stale
  settings snapshot was taken (the card-render read) and before Skip's
  decline runs is preserved — the decline operation re-reads under the
  lock, so the newer `stats_dir` and `steam_id` survive and only the
  username key changes. `save_settings`'s replace-all pinning test stays
  untouched.
- Hint-branch narrowing: the bare hint no longer renders while the card
  owns the absent-key case; existing `tests/test_home_stats_dir_hint.py`
  cases updated to pin the split.
- Overview status line: shown when the username is unset (absent and `""`),
  absent when set; copy pinned.
- Docs gates: `tests/test_docs.py` (Status line, section order, link
  targets) passes; full standard validation before the PR.
