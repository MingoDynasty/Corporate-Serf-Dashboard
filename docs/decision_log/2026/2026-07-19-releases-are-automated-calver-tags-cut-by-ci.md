# 2026-07-19: Releases Are Automated CalVer Tags Cut By CI

Status: Accepted

Decision: every push to `main` that changes anything an installed copy runs
publishes a GitHub Release tagged `vYYYY.MM.DD` (`.N` suffix for same-day
repeats). No human picks a version number or judges whether a commit "deserves"
a release. The job lives in `.github/workflows/ci.yml` with `needs: test` — a
commit that fails the gates never becomes a release — and the logic is in
`scripts/release_job.py`.

The skip rule is a **blocklist** (`docs/`, `tests/`, `.github/`, any `*.md`,
`.gitignore`, `.pre-commit-config.yaml`), not an allowlist, because the failure
directions are asymmetric: a redundant release is only noise, while a missed
release strands distribution inputs — `install.ps1`, the launcher,
`example.toml`, `.python-version`, `.gitattributes` — at an older tag. When in
doubt, release.

Two properties the job must keep:

- **The Latest invariant.** Concurrent pushes serialize through a fixed
  concurrency group (`cancel-in-progress: false`, `queue: max`), but that
  serialization is FIFO by wait-start time, not by source order — a newer push
  with faster tests can enter the critical section first. So inside it the job
  checks ancestry (`git merge-base --is-ancestor`) against published releases
  and passes `make_latest: false` when a published release descends from its
  own SHA. `make_latest` defaults to true, so without this an older commit's
  slow run would silently downgrade every `latest`-tracking install. After
  claiming Latest, the job asserts `releases/latest` really resolves to its tag.
- **Idempotency across every partial-failure state**, not just
  tag-without-release: a rerun reuses a tag already pointing at `HEAD` and
  *resumes an existing draft* (re-attaching assets) rather than creating a
  second release.

The zip asset is built by `git archive`, the only producer that expands the
`export-subst` stamp — zipping a checkout would ship `version.txt` unexpanded.
A second, tiny asset (`release.json`) carries the tag, full SHA, commit date,
and that release's uv and Python pins, so the installer and launcher never parse
TOML from PowerShell or spend an extra API call resolving the exact SHA
(`releases/latest` reports `target_commitish`, which may be a branch name).

Why: the maintainer explicitly does not want per-commit SemVer judgment, and the
app has no API consumers to justify SemVer semantics. Market research across
fast-shipping projects (yt-dlp, Path of Building Community, RuneLite, and
FFmpeg's binary channels) found dated, immutable, retained artifacts to be the
baseline even for daily-or-faster shippers, and found no comparable project
shipping *unidentified* builds from a branch tip — tags are load-bearing for
rollback and support.

Provenance: this entry and the six below distill the release, versioning, and
distribution proposal added in PR #150 and deleted once shipped (git history
holds the full text). It went through four external design-review rounds plus
the market-research run summarized above, and was implemented in PRs #154,
#155, #158, #159, and the activation PR that removed it.
