# 2026-08-21: Release Integrity Rests On GitHub Digests And An Enforced Archive Contract

Status: Accepted

The first thing a new visitor asks about a downloadable Windows app is whether
it is safe to run, and the release page is where that gets answered. This
project relies on the SHA-256 digest GitHub publishes for every uploaded asset,
together with releases that can never be changed, rather than shipping a
checksum file of its own. The release page now opens with a short header saying
what those guarantees are and which download to take, and CI now proves
byte-for-byte that the uploaded assets are the ones it built. The release zip
also stopped carrying development-only files that an installed copy cannot use,
and a new pre-publish check fails the draft if the zip ever loses a file an
install needs.

Decision: no custom `SHA256SUMS.txt`, no hash duplicated into the release
notes, and no launcher-side hash verification at launch. Integrity rests on
GitHub's per-asset digests plus immutable releases, which this repo already has
enabled — see
[Releases And Their Assets Are Immutable](#2026-07-19-releases-and-their-assets-are-immutable),
which this entry extends rather than restates. Alongside that: the release page
gets a curated header, `.gitattributes` prunes development-only trees from the
archive, and `validate_release` enforces an archive contents contract before
publication.

Why: at this audience size the marginal security of a project-published hash
over a platform-published one is zero, and both are downloaded over the same
HTTPS connection from the same host. GitHub's digests are visible on the
release page, are computed by GitHub on receipt, and cannot change afterward
because the release is immutable. Both of our assets additionally carry a
GitHub-signed release attestation, retrievable at
`repos/.../attestations/sha256:<digest>` — supporting evidence for this
decision, deliberately not surfaced in user-facing copy, because attestation
commands are not something a general user should be asked to run.

Rejected alternatives:

- **A custom `SHA256SUMS.txt` asset.** Redundant with digests GitHub already
  publishes and signs, and it would be permanent release machinery — generated,
  validated, and maintained on every release — bought for no added security.
  It also invites the copy failure this entry avoids: a hash pasted into the
  notes reads as proof of trustworthiness rather than of byte integrity.
- **Launcher-side hash verification at launch.** It touches the frozen update
  contract, the named-asset/source-archive fallback, and failure behavior all
  at once. The launcher already validates `release.json`'s identity fields and
  health-gates promotion on the SHA carried in `version.txt`, so the marginal
  gain is small. Deferred until evidence demands it, consistent with the
  deferral already recorded in the 2026-07-19 immutability entry.

Consequences and constraints:

- **Digests cover uploaded assets only.** Every release page also shows
  GitHub's auto-generated "Source code (zip / tar.gz)" downloads, which have no
  digest. Copy must never claim digests for "every download", and must never
  say "verified safe" or "secure download" — a digest proves byte integrity,
  not trustworthiness.
- **The archive is a contract, and it is enforced.** `validate_release` rejects
  the draft unless the zip carries every entry in `REQUIRED_ARCHIVE_ENTRIES`
  and none of `EXCLUDED_ARCHIVE_TREES`. The required set covers installation,
  runtime, legal, and self-documentation needs rather than only files read by
  code, and it is deliberately not a snapshot of the whole tree: each entry is
  listed with what reads it. Without this, a `.gitattributes` edit or a file
  move that drops an install-critical path is undetected until someone's
  install fails, and immutability makes the bad asset permanent.
- **Name the file when something opens it by name.** A directory entry in the
  required set only asserts that the tree holds at least one file, so it still
  passes after the one member that mattered is renamed away. Required
  individually for that reason: `source/app.py`, `scripts/launch_bootstrap.ps1`,
  and `scripts/launcher.ps1`, which the launcher, the installer, and the
  bootstrap each open by name and abort without; and `docs/example.png`,
  `docs/architecture.md`, `docs/product.md`, and `docs/roadmap.md`, which are
  every relative target the shipped README opens. A test cross-checks that
  README target set against the contract, so a new link into `docs/` cannot
  quietly fall outside it. Only `assets/` and `resources/` remain directory
  entries, where no single member is the dependency.
- **A tree holding only its own directory entry is empty, not present.**
  `git archive` emits an entry for each directory, and a `/**` export-ignore
  rule leaves that entry behind after removing every file under it, so a
  prefix match alone would accept an empty required tree. The check requires a
  child path, and a regression test covers each required directory in that
  shape.
- **`export-ignore` is narrow, and `docs/` stays.** `/tests`, `/.idea`, and
  `/.github` are pruned. `docs/` ships because the shipped README embeds
  `docs/example.png` and links `docs/*.md`, so dropping it breaks the zip's own
  front page for the manual-install reader. `resources/`, `scripts/`,
  `install.ps1`, and `version.txt` must ship for the app, the installer, the
  launcher, and build identity respectively.
- **Use the anchored directory form.** Tested on git 2.55: `/tests`, `tests`,
  and `tests/` all prune the directory entirely, while `/tests/**` removes the
  files and leaves an empty `tests/` directory entry in the zip. The contract
  treats an empty excluded directory as still shipped, so the two rules agree.
- **`export-ignore` also prunes GitHub's source archive.** The
  `archive/<sha>.zip` download changes the same way. That is intended, and it
  matters because that archive is the launcher's documented fallback when the
  named asset is missing, and because the CI stamp job downloads it.
- **The digest check is a build-versus-upload comparison, not a size check.**
  It recomputes SHA-256 locally and requires equality, treats a null or missing
  digest as a failure rather than a skip, and requires the release to carry
  exactly the versioned zip and `release.json` — a resumed draft keeps any
  asset `--clobber` never replaced. It subsumes the size comparison it
  replaced.
- **Blocking a release and shipping a file are separate lists.**
  `_BLOCKED_DIRECTORIES` in `scripts/release_job.py` decides whether a push cuts
  a release; `.gitattributes` decides what the zip carries. `docs/` is on the
  first and not the second — see
  [PyCharm Config Stays Tracked And Its Upgrade Churn Is Committed Once](#2026-08-08-pycharm-config-stays-tracked-and-its-upgrade-churn-is-committed-once).
