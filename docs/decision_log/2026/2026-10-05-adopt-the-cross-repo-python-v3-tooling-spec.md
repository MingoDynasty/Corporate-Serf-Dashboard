# 2026-10-05: Adopt The Cross-Repo Python V3 Tooling Spec

Status: Accepted

CI now follows version 3 of the cross-repo tooling spec. A new push to a pull
request cancels that pull request's earlier run when it is still going, and a
push to main is never cancelled. The two GitHub Actions the workflow uses move
to their latest releases, and the checkout step no longer leaves the job's
token behind in the jobs that have no use for it. A contributor notices only
that an outdated run on their pull request stops early.

**Rulings.** All by the maintainer, in chat. 2026-10-04: action pins move
through the spec, never in this repository alone
([2026-10-04 entry](#2026-10-04-dependency-updates-stay-manual-run-from-a-playbook)),
so a pin bump is a new version of the spec. 2026-10-05: version 3 carries
three changes to the spec's workflow (the pin bump,
`persist-credentials: false` on checkout, and a concurrency cancel for pull
requests only), this repository adopts it first, and a `pip-audit` step stays
out of CI, where Dependabot alerts on the lockfile carry that signal. The go
to cut the version came the same day.

**Supersedes in part** the
[2026-07-06 entry](#2026-07-06-adopt-the-cross-repo-python-v2-tooling-spec):
the stamp is now `tooling-spec: python-v3`, the action pins moved, and the
workflow again cancels superseded runs, for pull requests only. The job shape,
the four checks, and where the uv, pytest, and mypy settings live are
unchanged.

**What changed in `.github/workflows/ci.yml`.**

- **Pins, on all three jobs.** `actions/checkout` v7.0.0 to v7.0.1
  (`3d3c42e5aac5ba805825da76410c181273ba90b1`), and `astral-sh/setup-uv`
  v8.2.0 to v10.2.0 (`c18668ad3cf93ea998bef934396af7bb5c839dc7`). Both SHAs
  were resolved from the official tags on 2026-10-05.
- **A workflow-level `concurrency` block.** The group is the pull request's
  number, or the run ID when there is none, and `cancel-in-progress` is true
  only for a `pull_request` event.
- **`persist-credentials: false`** on the checkout in `test` and in
  `release-gate`. The checkout in `release` keeps its credentials, because
  that job pushes the tag with them.

**Why a push to main is never cancelled or queued.** The `release` job needs
`test`, so a cancelled run on `main` would drop a release, and a queued one
would delay it behind an unrelated push. The guarantee rests on the run ID,
which gives every push a group of its own: runs that share no group can
neither cancel one another nor wait behind one another. `cancel-in-progress`
is also false for a push, but that alone would not be enough. In a shared
group it only keeps the running member alive: the next push would still wait,
and a third push would replace the one waiting, which drops its release. So
the run-ID fallback has to stay, even though the event check looks as if it
already covers `main`. The `release` job's own `release` group is separate and
unchanged ([2026-07-19 entry](#2026-07-19-releases-are-automated-calver-tags-cut-by-ci)).

**Why the block sits on the workflow.** On the `test` job, every leg of the OS
matrix would share one group, so in a repository that runs two operating
systems the legs would cancel each other unless the group also named the leg.
The spec's file has to be the same in every repository that follows it.

**The pins.** Read from the release notes and the action source at both tags.
checkout v7.0.1 is a patch release. setup-uv's two breaking changes are
cache-only (v9.0.0 flips the `prune-cache` default, and v10.0.0 narrows where
`enable-cache: auto` caches), and every `setup-uv` step here passes
`enable-cache: false`. With no `version:` input it still reads
`required-version` from `pyproject.toml`. One gain: v8.2.0 bundles uv
checksums only through 0.11.18, so CI installed this repository's pinned uv
unverified. v10.2.0 bundles them through 0.12.17 and checks anything newer
against uv's versions manifest.

**Credentials.** checkout leaves the job's token in the clone's git
configuration unless told not to. Under `permissions: contents: read` that
token is read-only, so the gain is small. Nothing in `test` or `release-gate`
talks to the remote through git: the test suite calls `git show` and
`git ls-files`, and the gate reads history that `fetch-depth: 0` already
fetched.

**Consequences.** The required check keeps its name, `test (windows-latest)`.
An open pull request picks the new workflow up on its next run, because a
pull request's CI runs from its merge with `main`. A pull request's CI runs
the new pins only in `test`, and the first push to `main` adds `release-gate`.
When this entry was written the `release` job had not run them: it first does
on the next merge that cuts a release. The other repositories that follow the
spec adopt version 3 on their own schedule, and until then they carry the
older pins.
