# Settings detection: verified identity and stats-directory candidates

Status: Proposed
Date: 2026-08-02

## TL;DR

The settings page accepts only values typed from memory, even though the
machine already knows most of the answers. This proposal makes the page
offer detected candidates: every Steam library holding a KovaaK's stats
folder becomes a suggestion under the stats-directory field, and a Detect
button finds local Steam accounts with a matching KovaaK's profile and
fills in the verified name and ID. Everything stays suggestion-only — the
Save button remains the only thing that writes. The guided first-run
experience is deliberately deferred to a later proposal.

## Decisions needed

None open — the three judgment calls this proposal raised were settled
with the maintainer in the 2026-08-02 design discussion, recorded here for
the review record:

1. **Scope cut.** The config/settings arc's remaining scope was detection,
   dropdowns, and an initial-setup flow. The setup flow carries the
   unresolved product questions (discoverability, dismissal semantics) and
   is deferred to a future proposal; this proposal is the detection engine
   and the settings-page candidates only, which are pure enhancement on
   the shipped page.
2. **Detection trigger — split by cost.** Stats-directory candidates come
   from registry and file reads (local, milliseconds) and populate
   automatically when the page renders. Identity detection calls the
   KovaaK's API and runs only behind an explicit Detect button, which
   doubles as re-detect. Casually opening the page never causes API
   traffic.
3. **Privacy of identity probing — accepted.** Detection sends the persona
   name of every Steam account in `loginusers.vdf` — including other
   household accounts on a shared machine — to the public unauthenticated
   KovaaK's profile endpoint. Persona names are already public on Steam,
   the probe is equivalent to typing the name into kovaaks.com's search,
   it fires only on an explicit button press, and nothing is persisted for
   candidates the user does not save — including in request logs: probe
   log lines redact the queried name, because `debug.log` ships with bug
   reports. This is a deliberate choice, not a side effect.

## Problem

The settings page shipped manual-entry-only by design: page-first ordering
(see the 2026-08-02 entries in [decision_log.md](decision_log.md)) means
every detection dead end now resolves to "type it on the page" instead of
needing bespoke escape hatches. With PRs #181–#184 merged, that
prerequisite exists, and the decision log itself names the follow-on: the
silent `stats_dir` bootstrap's wrong-library case is "properly solved by
the follow-on proposal's candidate dropdown". Three gaps remain:

- **`stats_dir`**: the startup bootstrap takes the first library hit. On a
  machine with a stale FPSAimTrainer copy in a second Steam library the
  pick can be wrong, and the page offers no alternatives — repair means
  digging a deep path out of Explorer by hand. The detector
  (`source/config/stats_dir_detection.py`) already walks every library;
  it just stops at the first hit because startup wants one answer.
- **Identity**: the user must know their exact KovaaK's webapp username —
  a typo produces silently absent ranks (`total-play` returns `null`,
  the explicit unknown state), and nothing anywhere verifies the name.
  The Steam ID is a 17-digit number nobody knows offhand, yet it sits in
  `loginusers.vdf` on disk.
- **The data to close both gaps exists** and the pipeline was live-probed
  on the dev machine (2026-07-20): enumerate all `loginusers.vdf`
  accounts, probe each persona against the unauthenticated
  `/user/profile/by-username` endpoint, keep only candidates whose
  profile `steamId` equals that account's SteamID64. Three local accounts
  collapsed to exactly one verified pair; both alt personas returned
  HTTP 409 "Player does not exist".

Verified facts the design leans on (probed 2026-07-20, dev machine):

- `by-username` is unauthenticated and returns `steamId`,
  `webapp.username` (canonical casing), and `lastAccess`; unknown
  username → HTTP 409.
- **No reverse lookup exists**: `/user/profile/by-steam-id` → 404,
  `/user/profile?steamId=` → 401. Detection must guess names and verify;
  ID64 → username is impossible.
- KovaaK's game files and stats CSVs store no webapp identity, so disk-only
  identity detection is impossible; the webapp username lives server-side
  only.
- Steam persona and webapp username are distinct namespaces that merely
  often coincide; the `steamId` equality check is what turns that
  coincidence into a tested fact rather than an assumption.

## Design

### Detection engine

**`stats_dir` candidates.** A new pure function in
`source/config/stats_dir_detection.py` (indicatively
`detect_stats_dir_candidates()`) returns *every* library whose probe hits,
deduplicated by normalized path, in the existing roots-first order.
`detect_stats_dir()` keeps its exact contract — startup depends on it —
and may become "first candidate or None" internally. The known pre-2021
numeric-key `libraryfolders.vdf` gap stays as-is (pinned by test; fix only
if ever needed).

**Identity candidates.** A new module (indicatively
`source/config/identity_detection.py`, beside the stats-dir detector):

- Read `<root>/config/loginusers.vdf` for every Steam root the
  detector's registry walk yields, not just the first hit — the walk
  deliberately keeps every root because the 32-bit and 64-bit registry
  views can point at different installs, and the first root is not
  guaranteed to be the active client. Accounts merge across files and
  deduplicate by SteamID64, keeping the entry with the newest
  `Timestamp`: the most recently used client's view of an account
  carries the freshest persona.
- Enumerate every account: a tolerant scan for SteamID64-keyed blocks
  capturing `PersonaName` (the probe key) plus `AccountName` and
  `Timestamp` (display/tie-break material). A malformed or unreadable
  file warns once and contributes no accounts — never fatal — but the
  failure is not erased: the result records that discovery was
  incomplete (an account list existed and could not be read), which is
  a different fact from reading cleanly and finding no accounts.
  Parsing is regex-based like the shipped detector — the upstream `vdf`
  package is unmaintained, and a dependency for two small files read on
  demand is not warranted.
- For each account, probe `by-username` with its persona (duplicate
  persona strings probed once) and classify:
  - profile exists and `steamId` == the account's ID64 → **verified
    pair**: the profile's canonical `webapp.username` (never the raw
    persona) plus the ID64, with persona and `lastAccess` as display
    metadata;
  - HTTP 409 → confirmed absent, discarded;
  - profile exists but `steamId` differs → coincidental name, discarded;
  - transport failure, an unexpected status, or a 2xx payload the
    pipeline cannot use (malformed JSON; a profile missing or invalid
    `steamId`, `webapp.username`, or `lastAccess`) → **unchecked**,
    counted so the UI can say detection was incomplete. Schema drift
    degrades to an incomplete result exactly like an outage — it never
    escapes as an exception that fails the Detect callback.
- Return verified pairs ranked by profile `lastAccess` (newest first),
  the unchecked count, and whether account discovery was complete. The
  engine never writes settings and never raises for ordinary misses (no
  Steam, no file, no accounts → zero candidates with complete
  discovery).

The API call lands in `source/kovaaks/api_service.py` as a small function
over the existing `_get_with_retry` stack, inheriting the project retry
policy (retry once on 429 and connection failures, never on read
timeouts, 30-second default timeout — sized for KovaaK's ~28 s slow
spells). The same PR documents the endpoint in
[kovaaks_api_notes.md](kovaaks_api_notes.md): 409 semantics, the fields
relied on, and the negative results (no reverse lookup) so nobody
re-probes them.

One consequence of the accepted privacy decision is designed in rather
than left for review to discover: `_get_with_retry` logs every
attempt's `params` at DEBUG, its transport-failure summaries embed the
prepared URL with its query string, and `data/logs/debug.log` is
persisted, rotated, and collected with bug reports — an unmodified call
would therefore retain every probed persona on disk, including 409s and
candidates never selected. The probe call marks its request sensitive:
attempt lines log a placeholder in place of the username parameter,
failure summaries for this call are scrubbed of the query string, and
identity-detection's own log lines name counts and positions ("account
2 of 3"), never the personas or IDs of accounts the user did not save.
A regression test drives success, 409, and transport-failure probes
under `caplog` and asserts no persona reaches any log record.

Probes are sequential — typically one to three accounts — and run only
inside the Detect callback, never on a render path and never at startup.
Worst case is roughly 30 seconds per slow-spell account behind a button
with a loading state; acceptable for an explicit, rare action.

### Settings page

**Stats directory field.** The `dmc.TextInput` becomes a free-text input
with a suggestions dropdown (`dmc.Autocomplete`), fed the candidate list
computed locally at render time. Zero candidates degrade to exactly
today's field. Suggestions are just text the user could have typed:
validation (existing directory or empty) and the all-or-nothing Save are
untouched.

**Identity detection.** A Detect button beside the identity fields runs
the pipeline synchronously with a loading state:

- exactly one verified pair → the username and Steam ID inputs are filled
  with it, and the status line says what was found and that Save applies
  it;
- two or more → a picker appears listing each pair (canonical username,
  with persona and last-seen as secondary text, newest first); choosing
  one fills the two inputs. Never auto-picked: two verified accounts is
  precisely the case where silent selection would fill caches with
  someone else's ranks;
- zero verified, discovery complete, all probes answered → status: no
  local Steam account matches a KovaaK's profile; enter the username
  manually (with no reverse lookup, manual entry is the only remaining
  path);
- incomplete results are never dressed up as conclusive: if some probes
  went unchecked, the status says N account(s) could not be checked and
  Detect can be pressed again; if account discovery itself failed (an
  account list existed but could not be read), the status says Steam's
  account list could not be read — never the no-match message above.

Filling inputs is transient UI state. The store is written only by Save,
with its shipped semantics: all-or-nothing validation, every key written,
warmup cold-start on a first identity, and the restart notice derived
from `is_restart_pending()` — a re-detected identity on a running app
presents as restart-required exactly like any other identity edit. Both
new callbacks are `n_clicks`-guarded with None-trigger regression tests,
per the DashProxy initial-call hazard.

### Blast radius

No store schema change, no new writers, no startup changes. The bootstrap,
both pins, and `detect_stats_dir()` keep their contracts.
`api_service.py` gains one endpoint function and a sensitive-request
logging option on `_get_with_retry`; `pages/settings.py` gains the
candidates, the button, and the picker; `docs/architecture.md`'s module
map rows are updated in the PRs whose behavior they describe.

### Alternatives rejected

- **Identity probing on page load or at startup** — API traffic on every
  visit, slow spells stall the page, and the superseded startup-banner
  design's problems return. Rejected with the split-by-cost decision.
- **The `vdf` package** — unmaintained upstream; the regex approach is
  installer-proven and fixture-tested.
- **`ActiveUser` registry cross-check** — corroboration only; subsumed by
  online `steamId` verification, and worthless when Steam is closed
  (`ActiveUser` = 0). Dropped for simplicity.
- **A combined identity control replacing the two fields** — the shipped
  form stays; the picker fills the existing inputs, keeping one Save path
  and the cleared-versus-never-set semantics untouched.
- **Auto-writing a single verified pair** — identity is never silently
  written: a wrong identity is not self-evident the way a wrong stats
  directory is, and the adjudicated one-silent-writer rule reserves
  silence for the absent-key `stats_dir` bootstrap alone.
- **Probing only the `MostRecent` account** — recency is the wrong
  heuristic (live-probed: the KovaaK's account need not be the last Steam
  login), and it defeats the multi-account collapse detection exists for.

## Out of scope

- **The initial-setup flow** — Home setup card, discoverability for users
  who skipped setup, and skip/dismissal semantics — deferred to a future
  proposal; its material stays in the gitignored pickup notes
  (`ignore/design-notes/config-settings-arc.md`).
- **Verifying manually typed identities** (a "check this name" action) —
  a natural later extension of the same pipeline, not needed for
  candidates.
- **The pre-2021 numeric-key `libraryfolders.vdf` format** — known gap,
  pinned by test, unchanged.
- **Any change to startup**: the bootstrap stays first-hit and
  absent-key-only; no re-detection on boot, no freshness machinery.
- **Non-Windows platforms** — the app is Windows-only today.

## Testing

- **Engine, pure and fixture-driven** (no live registry, file system
  outside `tmp_path`, or API in any test, matching
  `tests/test_stats_dir_detection.py`): all-candidates ordering and
  dedup; `loginusers.vdf` enumeration (multi-account, zero accounts,
  missing file, accounts merged across several roots' files with
  SteamID64 dedup preferring the newest `Timestamp`, malformed vdf
  warning and flagging discovery incomplete rather than reading as a
  clean empty); the verify pipeline against mocked responses — the
  live-probed three-accounts-to-one collapse, 409, `steamId` mismatch,
  transport failures and unusable 2xx payloads (malformed JSON, missing
  or invalid profile fields) each producing an unchecked count,
  `lastAccess` ranking, duplicate personas probed once.
- **API layer**: `by-username` maps 409 to a domain result rather than an
  exception escaping the pipeline; retry behavior rides the existing
  `_get_with_retry` coverage. The log-privacy regression drives success,
  409, and transport-failure probes under `caplog` and asserts no
  persona string reaches any log record.
- **Page callbacks**: render-time candidates land in the field's
  suggestion data; Detect outcomes (fill on one pair, picker on several,
  the conclusive no-match, unchecked, and discovery-failure statuses);
  None-trigger regressions for both
  new callbacks. Picker interaction is verified at the callback layer —
  the automated browser pane cannot open Mantine dropdowns, the
  established practice from the settings-page tests.
- **Gates**: the standard local validation set; `tests/test_docs.py`
  covers this file's lifecycle sections and links.

## Delivery plan

Three PRs, each independently green:

1. **Stats-directory candidates** — `detect_stats_dir_candidates()`, the
   Autocomplete swap on the settings page, tests, and the module-map
   touch-up. No dependencies.
2. **Identity detection engine** — `loginusers.vdf` enumeration, the
   `by-username` function in `api_service.py`, the verify pipeline with
   its fixtures, and the [kovaaks_api_notes.md](kovaaks_api_notes.md)
   entry. No UI. Independent of PR 1.
3. **Identity detection UI** — the Detect button, statuses, picker, and
   fill behavior on the settings page, with the None-trigger regression
   tests and the architecture/README sweep. Hard dependency on PR 2;
   soft-ordered after PR 1 to avoid rebase churn in
   `pages/settings.py`.

The shipping PR (PR 3) also runs the full "Shipping a proposal"
checklist: decision-log distillation, this file's deletion, roadmap and
product updates, and the kickoff-prompt archive step.
