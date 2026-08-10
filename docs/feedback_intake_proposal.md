# Feedback and Bug Report Intake

Status: Proposed
Date: 2026-08-09

## TL;DR

Real users need somewhere to send feedback, and a bug report needs to carry
enough to debug a failure on a machine we cannot see. GitHub Issues becomes
the canonical channel, with structured forms that ask for little beyond what
happened plus one attached log file. An audit of real logs confirmed the log
is safe to attach as long as the form plainly says what it contains — a
leaderboard username, a Steam ID, scores and play times, and file paths. A
later Settings-page link will pre-fill the report so filing one takes a
click instead of a scavenger hunt.

## Decisions needed

**D1 — Attach `debug.log` as-is with disclosure, or redact identity from log
lines first?**
Status: Accepted 2026-08-09 (maintainer, chat) — the proposal review is the
natural place to contest before implementation starts.
Recommended: disclose, don't redact. Maintainer rationale: a KovaaK's
player's username and Steam ID are already public — every leaderboard score
is stamped with both unless they opt out of leaderboards entirely — and both
values are likely needed to reproduce identity-dependent bugs (rank lookups,
benchmark row matching), which the audit predicts will be the top report
class. Consequence of choosing differently: new redaction machinery across
the several unredacted failure-logging sites plus the benchmark request
params, and bug reports lose exactly the values that diagnose
misspelled-username and mismatched-Steam-ID root causes.

**D2 — Channel policy: GitHub Issues canonical, forms only, nothing else at
launch.**
Status: Open.
Recommended: accept. Blank issues are disabled in favor of the two forms; no
Discord server and no GitHub Discussions; feedback arriving anywhere else
(Discord communities, Reddit) is transcribed into an issue by the maintainer
as the canonical record (`gh issue create` is unaffected by the blank-issue
setting). Accepting this knowingly accepts an exclusion: users without a
GitHub account — likely a real share of a gamer audience — have no direct
submission path, and their reports reach the tracker only if they surface in
a channel the maintainer watches and transcribes. Revisit if launch feedback
shows reports dying for want of an account. Consequence of choosing
differently: a second moderated inbox (Discord) or a second triage surface
(Discussions) for a single maintainer, ahead of any demonstrated volume.

**D3 — Ship the Settings-page "Report a bug" affordance?**
Status: Open.
Recommended: yes, as the second delivery PR — a pre-filled issue link plus
making the log's location visible removes the two failure points of
user-driven reports (wrong/missing version, missing log). All user-facing
copy in the forms and on the Settings page is maintainer-approved at its
implementation PR, not settled here. Consequence of no: every report costs
the user a manual version lookup (the form requires the field) and a
hand-dug log path (`%LOCALAPPDATA%\CorporateSerfDashboard\data\logs`),
raising abandonment risk on exactly the least technical reports.

## Problem

The app is approaching real users, and there is no defined place or shape
for feedback, feature requests, or bug reports. The app runs entirely on the
user's machine — nothing phones home, so every diagnostic artifact a report
needs already lives with the user, and the codebase was built on the working
premise that "bug reports arrive with `debug.log`" (`crash_logging.py`
writes uncaught exceptions there for exactly this reason; `app.py` opens
every session by logging build identity and the config; `request_logging.py`
exists because the log "ships with bug reports"). What has never been
defined: where reports land, what a report must contain, how a
non-developer gamer audience — many without GitHub accounts — gets a log
file off their machine, and what the log's contents mean on a public
tracker. That last question blocks the template copy, so it was answered
first, with evidence.

## Verified facts

Audit of 2026-08-09, run over the maintainer's production install logs
(current release builds, Aug 5–9) and the dev checkout's 4.3 MB `debug.log`
corpus (June 24 – Aug 9), cross-checked against source at `4b68a81`.

Clean by design — and verified working in real logs, not just in code:

- **Steam personas and other local accounts** never reach the log. The
  identity probe's by-username calls appear only as `<redacted>`
  placeholders (the `sensitive` flag in `api_service._get_with_retry`);
  `identity_detection.py` logs counts and positions only. Zero
  persona/`loginusers` hits across every log file.
- **The config dump is benign** under the current schema: port, polling,
  TTLs, flags. The settings store's contents are never logged — only its
  path, on read/write failure.
- **urllib3 transport lines are muted** to INFO, so the historical flood of
  full query-string URLs no longer occurs in current builds.
- **No credentials exist anywhere** (the app holds none), and the server
  binds loopback only.

Present in current builds — the disclosure surface D1 accepts:

- **KovaaK's username**, pervasive once configured: the per-attempt DEBUG
  lines log the request params dict (`username`, `usernameSearch`) for every
  rank and total-play call, and WARNING failure lines carry it both directly
  ("Using stale total-play cache for &lt;username&gt;…") and inside the full
  URL embedded in exception text — several `api_service` failure sites pass
  `request_exception_summary(exc)` without `redact_query`.
- **SteamID64, latent:** `get_benchmark_json` sends `steamId` in its params
  and is not sensitive-marked, so the ID64 lands in attempt lines whenever a
  user with a configured identity triggers a benchmark fetch. Not yet
  witnessed in either log (no `benchmarkId` lines exist); the Steam-ID
  mismatch warning that names both IDs is UI-only and never logged.
- **Windows username via absolute paths:** deployed installs live under
  `%LOCALAPPDATA%`, so crash tracebacks (which `crash_logging.py`
  deliberately writes to the log) and `exc_info` warnings name paths that
  embed the Windows account name. The stats directory is logged at startup;
  standard Steam paths carry no username, but a custom library under a user
  profile would.
- **Behavioral content**, inherent to the app's job: every run's scenario,
  score, personal placement, cm/360 sensitivity, threshold verdict, playlist
  share codes, and timestamps that reveal play schedule.

Historical only: June entries showing `kovaaks_username` and `steam_id`
inside config dumps came from the retired config schema (settings moved to
the app-owned store). A launch user's install cannot produce them; they
exist only in the maintainer's own pre-migration log history.

Deployment facts the form copy relies on: logs rotate at 5 MB × 3 backups
(`app.py`), so `debug.log` is always attachable (GitHub issue attachments
accept `.log`); a deployed install also writes `launcher-app-stdout.log` and
`launcher-app-stderr.log` beside it, which are the artifacts that matter
when the app dies before its own logging starts.

## Design

### Channel and repo configuration

- `.github/ISSUE_TEMPLATE/` gains two issue forms — `bug_report.yml` and
  `feature_request.yml` — plus `config.yml` with blank issues disabled.
- Labels: `bug`, `enhancement`, `question`, `needs-info`, and `upstream` for
  KovaaK's-side breakage the app can only work around (the API's slow spells
  and outages are documented in
  [`kovaaks_api_notes.md`](./kovaaks_api_notes.md)).
- Triage loop: reproduce → label → either close with a stated reason or turn
  into a kickoff prompt; the fixing PR says `Fixes #N`. Reports missing
  diagnostics get `needs-info` and a canned reply asking for the log.

### The bug report form

Fields, in order: what happened (required, free text); what you expected
(optional); steps to reproduce (optional); app version (required, free text
with a "shown on the Settings page" hint, pre-fillable via URL — the log
names the build only until rotation moves the startup record into a backup,
so the field cannot rely on the attached log carrying it, and the pre-filled
link absorbs the friction for the in-app path); attach `debug.log`
(drag-and-drop instruction naming the path, `won't start at all` variant
asking for the two launcher logs as well); screenshots for anything visual
(optional).

The form deliberately does **not** ask for browser console output: the
known first-load Dash pages race floods the console with alarming but
cosmetic errors (see the 2026-07-18 pages-race entry in
[`decision_log.md`](./decision_log.md)), which would generate false reports.
Where console output matters, the maintainer asks in-thread with "reload
first" instructions.

Disclosure copy accompanies the attachment field, to the effect of:
"`debug.log` includes your KovaaK's username and Steam ID (the same values
stamped on your public leaderboard scores), your scenario scores and play
times, and file paths that may include your Windows username. It never
contains passwords or Steam credentials." Exact wording is settled at the
implementation PR (D3's copy rule).

### Settings-page affordance (D3)

A "Report a bug" link beside the version block, targeting
`…/issues/new?template=bug_report.yml&version=<release_label>` — GitHub
issue forms accept query-string pre-fill by field id, and
`get_build_info().release_label` already exists. Next to it, the resolved
log directory (`state_dir()/data/logs`) is displayed so "attach debug.log"
names a copyable location. No new service code; the page already imports
`get_build_info`.

### Rejected alternatives

- **Redaction machinery** — D1: the identity values are public alongside
  every leaderboard score and are diagnostic for the likeliest bug class;
  disclosure is one honest sentence.
- **Crash telemetry (Sentry or similar)** — privacy-hostile for a local
  tool, standing infrastructure, and overkill at this scale.
- **Discord server / GitHub Discussions** — a second inbox and a second
  triage surface for one maintainer, ahead of any volume that would justify
  them; revisit on demand.
- **Email intake** — spam surface, no public dedupe or history.

## Out of scope

- Any change to what the app logs (D1 is an accepted-limitation decision;
  the escape hatch is that a user can read the log before attaching it).
- Auto-generated diagnostic bundles (zip/export button) — revisit only if
  real reports show the attach step failing in practice.
- Discussions, Discord, or any second intake channel — revisit on volume.
- The guided first-run setup flow (separate proposal, per the roadmap).

## Delivery plan

1. **PR 1 — repo intake config.** The two issue forms, `config.yml`, the
   label set (created once via `gh label create`), and a short "Found a
   bug?" section in `README.md` pointing at the issue chooser. No app code.
   Depends on this proposal merging (D2 standing). Recommended: Opus 4.8,
   high — copy-heavy YAML against a fixed spec; more capability would not
   change the outcome.
2. **PR 2 — Settings-page affordance.** The pre-filled link and log-path
   display, with unit tests for URL construction (version param encoding,
   unknown-build case). Hard dependency on PR 1 (the template filename is
   part of the URL) and on D3. Recommended: Opus 4.8, high, via a kickoff
   prompt derived from this plan.

The PR that finishes the arc runs the AGENTS.md "Shipping a proposal"
checklist: D1's privacy stance is the durable, likely-to-be-questioned
decision to distill into [`decision_log.md`](./decision_log.md), the
user-facing rationale lands in [`product.md`](./product.md), and this file
is deleted.

## Testing

- **This PR:** the standard gates; `tests/test_docs.py` enforces the Status
  line, leading-section order, and link resolution for this file.
- **PR 1:** issue forms are repo config with no runnable surface, and GitHub
  reads them from the default branch only — the new-issue chooser cannot
  render a PR branch's forms. Pre-merge gate: validate the YAML locally
  (parse it and check the field structure against GitHub's issue-forms
  schema). Acceptance check: immediately after merge, open the chooser and
  confirm both forms render with the required fields enforced — a broken
  form silently falls back to a blank issue, which is exactly the failure
  the post-merge check exists to catch.
- **PR 2:** unit tests for the issue-URL builder and the log-path display;
  standard gates.
