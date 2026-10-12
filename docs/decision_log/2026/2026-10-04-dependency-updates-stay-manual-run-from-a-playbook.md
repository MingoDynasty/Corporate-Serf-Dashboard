# 2026-10-04: Dependency Updates Stay Manual, Run From A Playbook

Status: Accepted

Dependencies and toolchain pins are updated by hand, about once a month, from
a written playbook. No bot opens update PRs, and no scheduled job reports what
is outdated. A contributor who wants newer versions runs the playbook at a
quiet point in the project.

**Ruling.** Ruled (user) 2026-10-04, in chat, on PR #340: updates stay manual,
and no bot opens update PRs. The scheduled check was skipped "for now", so it
is the part of this entry most likely to be revisited. The procedure is
[docs/dependency_refresh.md](../../dependency_refresh.md).

**Why no scheduled check.** It would answer a question whose answer is always
yes. On 2026-10-04, 22 days after the previous refresh, 25 of the 84 locked
packages had a newer release. The useful trigger is a quiet point in the
project, which a timer cannot see: the uv pin is exact, so moving it strands
every open branch on the old pin until that branch merges `main`.

**Why no bot PRs.** Three reasons, the first of them mechanical.

- Dependabot cannot run here. Its uv updater supports only the uv version it
  bundles, and rejects an exact `required-version` pin that differs. Another
  of the maintainer's repositories, on the same pin style, has failed every
  monthly Dependabot uv run since 2026-08-01 with
  `tool_version_not_supported`, and
  [dependabot-core issue 13199](https://github.com/dependabot/dependabot-core/issues/13199)
  was still open on 2026-10-04. The version Dependabot bundles was different
  on each of those three runs (0.11.8, then 0.12.7, then 0.12.18), so no exact
  pin could have kept up with it. The pin cannot be loosened to suit it: the
  release job reads the pin into `release.json` and refuses anything but an
  exact `==`, because every install provisions that version
  ([2026-07-19 entry](2026-07-19-the-installer-brings-its-own-toolchain-app-locally.md)).
  Dependabot's security fix PRs run through the same updater, so they stay
  off as well.
- Renovate can refresh a uv lockfile, but it is a third-party app that needs
  write access. On 2026-10-04 `main` required only the CI check, and a merge
  that changes `uv.lock` cuts a release, so write access reaches installed
  copies.
- A green CI run does not make a version bump safe. plotly 7 put a new button
  on both charts, which only a look at the running app could show
  ([2026-09-12 entry](2026-09-12-charts-keep-plotlyjs-4s-share-chart-button.md)),
  and ruff 0.16 changed which rules were enabled. Two of the four refreshes
  before this entry needed a judgment of that kind.

**What stays automatic.** Dependabot alerts only read the lockfile, so the pin
does not affect them; they have been on since 2026-08-30. The fix for an alert
is a single-package upgrade made by hand, as its own PR.

**The pinned GitHub Actions.** Ruled (user) 2026-10-04, in chat: they move
through the cross-repo tooling spec
([2026-07-06 entry](2026-07-06-adopt-the-cross-repo-python-v2-tooling-spec.md)),
never in a refresh of this repository alone. The spec carries their SHAs, and
every repository that follows it carries the same ones. A refresh therefore
only reports a pin that is behind, and a bump arrives as a new version of the
spec.
