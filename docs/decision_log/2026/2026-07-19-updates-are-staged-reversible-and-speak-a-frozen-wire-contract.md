# 2026-07-19: Updates Are Staged, Reversible, And Speak A Frozen Wire Contract

Status: Accepted

Decision: the desktop shortcut targets a stable bootstrap at the install root
(`launch.ps1`) that reads the manifest and delegates to the selected version's
launcher — nothing else. Per-tag directories get pruned (keep last two), so the
shortcut must never point into one. When the bootstrap itself must change, the
versioned launcher replaces it on a higher embedded marker by writing a
same-directory temp file, validating its marker and PowerShell syntax, then
renaming over it. Never truncate the live file in place: PowerShell keeps
executing the already-parsed body, so an interrupted in-place write leaves a
working session now and a bricked entrypoint for every launch after it.

The launcher is **single-instance** via a named mutex scoped to the install
root, held for the launcher+app lifetime. A second launch opens the browser at
the running instance and exits without updating, syncing, or touching the
manifest — atomic manifest writes protect one file, not a whole transaction.

Then it applies the manifest's policy:

- **`latest`** (default): query `releases/latest` on a short timeout; a
  different tag is downloaded and synced into a new per-tag directory but is
  **not promoted yet**. It starts as a pending activation, and the launcher
  polls `/health` until the child process is still alive *and* the response
  carries the expected full SHA and a per-launch token passed in by environment
  variable. A bare HTTP 200 is not proof of life: an already-running instance or
  an unrelated service holding the port can answer while the pending process
  never bound. Only then is the manifest atomically rewritten. On timeout or
  early exit the launcher starts the previous version and leaves the manifest
  untouched — a crashing release never becomes the recorded install. The gate
  deliberately does **not** require a tag match, because a build on trial is
  still described by the previous manifest and reports `tag: None` under the
  corroboration rule above. Any network or API failure fails open: run what is
  installed, offline-safe.
- **`pinned`** + `pinned_tag`: skip the update check entirely. A rollback
  install (`install.ps1 -Tag ...`) *writes this pin*; without it the next launch
  would immediately reinstall the bad release, making rollback a no-op. Undoing
  it is explicit: re-run the installer without `-Tag`.

**Wire contract v1.** A pinned or long-offline install may jump from the first
launcher straight to any future release, and the launcher performing that update
is always the *old* one. So everything an old launcher parses is a frozen,
versioned contract from day one: `release.json` and `install.json` both carry
`schema_version: 1`, and the v1 field set froze when the installer shipped.
Changes within v1 are additive-only. A breaking change bumps the version and
dual-publishes the v1 envelope for as long as v1 launchers may exist. A launcher
meeting an unknown `schema_version` — or any parse failure — runs the existing
install and says so loudly ("re-run the install one-liner"), because fail-open
alone would convert a contract break into *silent permanent stranding*: every
launch retries, fails, runs the old version, and never tells the user.

`install.json` deliberately carries **no uv field and no zip-prefix field**. The
launcher takes uv from the new release's `release.json` at update time, and
running the current version needs no uv at all — it starts the synced venv's
`python.exe` directly, which is offline-safe and makes the health gate and the
kill target the real server process rather than a wrapper. The zip's top-level
directory name is **discovered after extraction, never derived**: the named
asset keeps the "v" (`Corporate-Serf-Dashboard-v2026.07.19/`) while GitHub's
source-archive fallback strips it. Both scripts assert exactly one top-level
directory and verify the extracted stamp's SHA before syncing.

Rollback protects *code*; durable state is governed by a rule rather than
machinery. Releases must read older state (missing keys get defaults) and must
not rewrite user-authored files. The durable state is a handful of tiny,
schema-stable files, so a genuine format break is rare enough to be called out
in its PR with a manual step — the house convention at this user-base size.
State snapshot/restore was deferred on that basis.
(**Superseded on the schema-stability point only** by the 2026-08-11
durable-store stamp entry: those files now carry a `schema_version`, a release
that meets an unknown one refuses to write rather than relying on the manual
step alone, and pre-stamp releases are an unsafe rollback target. The
read-older-state and do-not-rewrite-user-files rules, and the deferral of
state snapshot/restore, are unchanged.)

Accepted limitation: a release that fails its health gate is retried in full —
download, sync, then the readiness timeout — on every launch until the next
release lands. Bounded by the near-daily release cadence; the escape hatches are
the rollback pin and waiting for the replacement release. Documented rather than
solved with a failed-tag marker.
