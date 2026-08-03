# Version display on the settings page

Status: Proposed
Date: 2026-08-02

## TL;DR

The app's version is shown only in a tooltip on the header's GitHub icon,
where nobody looks for it, and for the entire first session after an
automatic update the app cannot name its own release tag. This proposal
moves version display to the settings page and fixes the
self-identification gap first, because checking the version right after an
update is exactly when the display will be used. The fix: the installer and
launcher leave a copy of the release description beside each installed
version at download time, so a freshly updated app knows its tag from its
first breath.

## Decisions needed

None open — the shape was settled in the 2026-07-20 build-identity design
discussion and a 2026-08-02 follow-up with the maintainer, recorded here
for the review record:

1. **Venue: the settings page, not a separate About page** (maintainer,
   2026-08-02). A nav destination for three lines of static text is not
   worth the space; the settings page is the natural "about this install"
   home now that it exists.
2. **The page owns version display; the GitHub tooltip's build suffix is
   removed in the same milestone.** Nobody hovers a GitHub icon expecting
   version info — users click it to visit the repo. The tooltip was a
   stopgap chosen only because no page existed.
3. **The release tag is the primary identity** (`v2026.07.19.4`-style
   CalVer), with short SHA and commit date as secondary detail. The UI
   reads everything from `BuildInfo` and re-derives nothing.
4. **Hard prerequisite: the first-session-after-update `tag: None`
   wrinkle dies with (or before) the page.** Post-update verification —
   "the console said it updated to vX; did it work?" — is the display's
   peak-usage moment. A version line reading "unknown" exactly then looks
   like a failed update and manufactures the confused bug reports the
   display exists to prevent.
5. **The mechanism for (4) is a stage-time copy of `release.json` into
   the version directory**, corroborated by the same two-witness rule the
   install manifest already obeys. The rejected alternative — a
   multi-entry `install.json` with per-version records and an `is_active`
   flag — stays rejected; do not revisit. It makes illegal states
   representable (zero or two active versions), grows the manifest
   lifecycle from a single write-on-promote into stage/flip/prune
   transitions (giving the failed-update path cleanup obligations where
   today it touches nothing), and conflates install-level policy with
   per-version facts.
6. **Support boundary for the tag guarantee** (maintainer, 2026-08-02,
   adjudicating the PR #187 review): the app currently has a
   single-user install base, so update paths that originate from
   releases predating Part 1 are out of support. The guarantee in (4)
   holds whenever the staging launcher is Part 1's or newer; an update
   staged by an older launcher gets one session of `unknown` and
   self-heals (mechanics under Design), and no delivery mechanism is
   added for its benefit (see Rejected alternatives).

## Problem

Build identity is resolved by one reader,
`source/utilities/build_info.py`, and currently surfaces in three places:
the startup line in `data/logs/debug.log`, the `/health` endpoint, and a
suffix on the header GitHub icon's tooltip (`app_shell.github_component()`).
The governing decision-log entry —
[Build Identity Comes From The Manifest](decision_log.md#2026-07-19-build-identity-comes-from-the-manifest-corroborated-by-the-stamp)
— also claims the browser title as a surface, which is factually wrong:
Dash Pages per-page titles overwrite `document.title` on navigation, so
the tab title is effectively unversioned. (It should stay that way — the
fix is to the entry's claim, not the title.)

Two problems:

- **The tooltip is an affordance failure.** Version info behind a hover on
  a repo link is discovered by accident. It was an explicit stopgap: the
  identity work shipped before any page existed that could own the
  display. The settings page (PRs #181–#184) now exists.
- **The app cannot name its release when it matters most.** The install
  manifest (`install.json`) is the only layer that knows the release tag,
  and it is trusted only when its SHA corroborates the stamp beside the
  running code. During a staged update the manifest still describes the
  previous version while the new one is on trial, so for the entire first
  session after an update `BuildInfo.tag` is `None` — an accepted
  consequence in the decision-log entry above. A version display inherits
  that gap at its peak-usage moment (decision 4).

## Design

### Part 1 — trial builds know their tag

At stage time, both writers — `install.ps1` and `scripts/launcher.ps1`,
in their `Install-ReleaseVersion` functions — copy `release.json` verbatim
into `versions/<tag>/`, beside that version's `version.txt` stamp. Both
writers already hold the release description at that point and have just
verified the extracted stamp carries the release's SHA, so the copied file
is corroborated at write time. One mechanical wrinkle for the
implementer: `Get-ReleaseInfo` currently returns only the parsed object,
and the copy must be byte-verbatim, so the raw response text needs to
ride along to the copy site (return both, or write the file at fetch
time).

`build_info.py` gains a reader for the per-directory file, applying the
same two-witness rule as the manifest reader: trust it only if its `sha`
equals the SHA in the expanded stamp. It validates `schema_version` 1 and
ignores the file (with a warning) on any parse or schema surprise, the
same tolerances the manifest reader has. The extra `release.json` fields
(`uv_version`, `source_asset`) are irrelevant to identity and simply
unread. The resolved `BuildInfo` carries a distinct `source:
"release-file"` so the startup log line names which witness answered.

Precedence becomes: per-directory release file → corroborated
`install.json` → stamp → git → unknown. The release file never lags — it
is written at stage time, before the trial run — so it answers during the
post-update session. The manifest path stays as fallback for version
directories staged before this change (graceful degradation; per house
convention, no migration shims — the old directories age out via the
keep-last-two prune). Whenever both sources corroborate they describe the
same release, so the order between them cannot change the answer; the
release file goes first because it is the one that is never stale.

Wire-contract impact: none. This is additive within
[contract v1](decision_log.md#2026-07-19-updates-are-staged-reversible-and-speak-a-frozen-wire-contract)
— no field changes to either schema, and an old launcher that does not
write the copy leaves behavior exactly as today.

Accepted transition limitation (decision 6): the launcher that stages an
update is always the *installed* release's launcher, and the wire
contract deliberately supports jumping from any old release straight to
latest — so an install still on a pre-Part-1 release stages its next
update without the copy, and that trial session resolves from the stamp
(`tag: None`; the page, once it exists, shows `unknown`). This is
today's accepted limitation surviving for exactly one more update cycle
on that install: it self-heals at the next launch, where the promoted
manifest corroborates and names the tag, and permanently once a
Part-1-or-later launcher stages the following update. Both escape
hatches already exist — launch again, or re-run the install one-liner,
which fetches the latest release's installer and does write the copy.
With a single-user install base this is documented rather than
engineered around.

The filename stays
`release.json` (not renamed on copy): one name for one schema, greppable
across the CI release job, both scripts, and the app; sitting inside a
version directory rather than the state root, it does not read as
config.

The decision-log entry's accepted first-session `tag: None` consequence
is marked superseded by this mechanism in the same PR, keeping the
history per house convention.

### Part 2 — the settings page section, and the tooltip reverts

The settings page (`source/pages/settings.py`) gains a small version
section at the bottom of the existing stack: the release label as primary
text (`BuildInfo.release_label` — the CalVer tag, or `dev` in a source
checkout, or `unknown`), with short SHA and commit date as secondary
detail (`BuildInfo.short_description`). All strings come from
`get_build_info()`; the section is static per process (the resolver is
cached) and is rebuilt per visit like the rest of the page layout, which
costs nothing and needs no callback. Exact markup (divider, heading
level, text sizes) is the implementer's call — plain text only, no
buttons, no network.

`github_component()` in `source/app_shell.py` reverts to the plain
"View this app on GitHub" tooltip label.

Docs riding along in the same PR: the build-identity entry's identity-
surfaces list is rewritten (startup log line, `/health`, settings page;
tooltip suffix removed) and its browser-title claim corrected as
described under Problem; the `build_info.py` bullet in
[architecture.md](architecture.md) names the same surfaces.

### Rejected alternatives

- **Multi-entry `install.json`** — settled rejection, recorded under
  Decisions needed (5).
- **A separate About page** — settled venue call, recorded under
  Decisions needed (1).
- **An update-availability check on the page** ("newest release is vX")
  — needs a network call from a page that today makes none, plus policy
  decisions (when to check, what to cache); nothing settled here needs
  it. Out of scope, not rejected forever.
- **Delivering `release.json` inside the release archive** (the PR #187
  review's suggested mechanism, so that launchers predating the copy
  step still receive the metadata) — the zip is pure `git archive`
  output today, the only producer that expands the `version.txt` stamp;
  injecting a generated file means the release job post-processes the
  archive and a second identity artifact must be validated before
  publish. Its only beneficiary is an update staged by a pre-Part-1
  launcher, which decision 6 places out of support. Rejected with that
  decision, not forever — if the support boundary ever widens, this is
  the mechanism to revisit.

## Delivery plan

- **PR 1 — stage-time release copy and reader.** `install.ps1`,
  `scripts/launcher.ps1`, `build_info.py` + tests, and the decision-log
  supersession note. No UI change; ships safely alone.
- **PR 2 — settings section, tooltip revert, docs.**
  `source/pages/settings.py`, `source/app_shell.py` + test updates, the
  decision-log surfaces rewrite and browser-title correction, the
  architecture-map sweep, and the full shipping-a-proposal checklist
  (distill, delete this file, roadmap, product inventory). Hard
  dependency on PR 1 — decision 4 forbids shipping the page first.

Kickoff prompts derive from this plan, one per PR.

## Out of scope

- **Update behavior.** The maintainer raised automatic-versus-manual
  updates as an open product question in the 2026-08-02 discussion; this
  proposal leaves launch-time auto-update exactly as it is, and nothing
  here depends on the answer. A change there would be its own proposal.
- **Displaying the update policy** (an "updates: automatic" / "pinned to
  vX" line read from the manifest). Cheap, but it surfaces a fact the
  user set themselves via the installer; deliberately skipped until asked
  for.
- **Update-available indicators or in-app update triggers** (see
  Rejected alternatives).
- **`install.json` or `release.json` schema changes.** Part 1 is
  additive-only within wire-contract v1.
- **Settings detection and dropdowns** — the separate in-flight proposal
  (PR #186); the two touch different regions of the same page and can
  land in either order.

## Testing

- **PR 1**, in `tests/test_build_info.py`: a corroborated release file
  resolves with the tag and `source: "release-file"`; a SHA-mismatched
  file falls through to the stamp; malformed JSON, a non-object, a bad
  `schema_version`, and a missing `sha` each warn and fall through; with
  the file absent, the corroborated-manifest path still answers
  (fallback preserved). The PowerShell side has no pytest harness — two
  manual checks on the dev machine cover the supported path: a fresh
  install of Part 1's release (its installer stages with the copy;
  confirm `versions/<tag>/release.json` exists and the startup log and
  `/health` report the tag), and, once the next release lands, a launch
  that stages it (Part 1's launcher performs the copy; confirm the
  *trial* session's startup log already reports the new tag — the
  moment decision 4 is about). A direct jump from a pre-Part-1 release
  is deliberately not covered: decision 6 places it out of support, and
  its expected behavior (one `unknown` session) is stated under Design.
- **PR 2**: `tests/test_app_shell.py`'s
  `test_github_tooltip_carries_the_build_identity` flips to pin the
  plain label; a settings-page layout test asserts the section renders
  the `BuildInfo`-derived strings (monkeypatched `get_build_info`).
- Both PRs run the standard local gate set (pytest, ruff format check,
  ruff lint, mypy, compileall); `tests/test_docs.py` gates this file's
  lifecycle and the link sweep mechanically.
