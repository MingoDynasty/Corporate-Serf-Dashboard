# 2026-10-04: Upgrades Skip Package Versions Younger Than A Week

Status: Superseded by the
[2026-10-05 newest-versions entry](#2026-10-05-a-refresh-takes-the-newest-version-of-everything):
the setting is removed, and the week no longer applies to the uv pin. What
this entry measured about how uv records the setting still holds.

uv ignores any package version published in the last seven days. A hijacked
package is usually caught and withdrawn within days, so the delay keeps one
out of the lockfile and out of the next release. A contributor who needs a
newer version sooner exempts that one package. A refresh holds the uv release
it pins to the same week, by hand.

**Ruling.** Ruled (user) 2026-10-04, in chat, on PR #340. The setting is
`exclude-newer = "7 days"` under `[tool.uv]` in `pyproject.toml`. It lands
with the first refresh after this entry, not with the entry: adding it changes
`uv.lock`, and a change to `uv.lock` cuts a release.

**Why.** Updates here are made by hand
([2026-10-04 entry](#2026-10-04-dependency-updates-stay-manual-run-from-a-playbook)),
and a plain `uv lock --upgrade` takes the newest version of everything. On
2026-10-04, 13 of the 25 pending updates would have resolved to a version
under seven days old. Merging a lock cuts a release, so those versions reach
installed copies.

**Why in `pyproject.toml`.** Measured under uv 0.12.13 on 2026-10-04. uv
records the setting in the lock's `[options]` as a span
(`exclude-newer-span = "P7D"`) beside a placeholder date, so the lock does not
go stale as time passes. `uv sync --locked`, which CI and the installer both
run, compares those options with the project's. Passing `--exclude-newer` only
on the upgrade command writes an option the project does not have, and
`uv sync --locked` then exits 1. Adding the setting to an existing lock moves
no package version.

**The exemption.** `exclude-newer-package = { <name> = false }` lifts the limit
for one package, and uv records it in the lock the same way. It is for a fix
that cannot wait a week, usually one for a security alert. It comes out at the
first refresh after the exempted version is a week old, never sooner: removed
while the version is still under the limit, `uv lock` moves the package back
to an older version and exits 0, which would undo the fix without a warning.

**The uv pin.** Ruled (user) 2026-10-05, in the review of PR #340: the same
week applies to the uv release a refresh pins. Every install downloads that
exact build and runs it, so the reasoning for packages holds at least as
strongly here. uv publishes often, with ten releases in the 23 days before
2026-10-04, so its latest release is usually days old. The setting cannot
enforce this, because it governs the packages uv resolves and not uv itself.
A refresh applies it by hand and pins the newest release at least a week old.
