# 2026-11-07: A Weekly Workflow Audits The Lock

Status: Accepted

Once a week, a scheduled workflow checks every locked package against a
database of known vulnerabilities, and a finding fails that run. It never runs
on a pull request, so no change is blocked by an advisory it did not cause. It
covers the weeks between refreshes, when GitHub's own alerts can miss what the
lock holds.

**Source.** Row R3 of version 4 of the cross-repo tooling spec, which the
maintainer keeps outside this repository. This entry merges with that
version's ratification. `.github/workflows/audit.yml` is the spec's second
canonical file, the same in every Python repository that follows it, and it
carries the action pins of the spec's `ci.yml`. The stamp stays in `ci.yml`.

**What it runs.** `uv audit --locked --preview-features audit-command`, the
command of the playbook's
[package pass](../../dependency_refresh.md#package-pass) step 6, on
`ubuntu-latest`, Mondays at 14:00 UTC and on `workflow_dispatch`. A finding
exits 1, and so does a `uv.lock` that no longer matches `pyproject.toml`. There
is no OS matrix: the lock is one universal resolution and the lookup is OSV,
so the runner's OS does not change the answer. The preview flag goes when
`uv audit` leaves preview.

**Why never on a pull request.** A finding is about the lock, not the diff.
The [2026-10-05 entry](2026-10-05-adopt-the-cross-repo-python-v3-tooling-spec.md)
kept a pip-audit step out of CI for that reason, and that still holds: this
workflow fails only its own run.

**Why Dependabot's alerts are not enough.** Dependabot reads the lock only on
a Python version it supports. Since the move to 3.15 it has not, so its alerts
still describe the 2026-10-12 lock
([tech-debt entry](../../tech_debt.md#dependabot-cant-read-the-lock-on-python-315)),
and the same gap can open at every Python minor this project moves to before
Dependabot supports it. The weekly run reads the lock with the uv that CI
installs, so it does not wait on Dependabot. The alerts stay on.

**What it does not change.** It checks known vulnerabilities, not whether a
newer release exists, so the
[2026-10-04 entry](2026-10-04-dependency-updates-stay-manual-run-from-a-playbook.md)
still stands: no scheduled check of what is outdated, and no bot PRs. A
finding is fixed by hand, as the playbook's
[security section](../../dependency_refresh.md#a-security-alert-between-refreshes)
says.

**Consequences.** GitHub runs a schedule only from the default branch, so the
first scheduled run is the first Monday after the merge. GitHub disables a
public repository's schedule after 60 days with no activity in the repository.
