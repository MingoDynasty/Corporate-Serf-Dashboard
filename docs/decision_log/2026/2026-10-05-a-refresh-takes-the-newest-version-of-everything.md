# 2026-10-05: A Refresh Takes The Newest Version Of Everything

Status: Accepted

A dependency refresh takes the newest version of every package and pins the
latest uv release, however recently each was published. The one-week minimum
age is removed, within a day of the first refresh switching it on. Nothing now
keeps a version published hours earlier out of the lockfile, and the
maintainer chose to handle a bad release if one arrives.

**Ruling.** Ruled (user) 2026-10-05, in chat, on
[#349](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/349): "I
vote to simply remove the `exclude-newer = "7 days"` line. I'll deal with the
issue if a broken package makes it way in." Asked whether that was a ruling,
the maintainer answered "Yes, ruling." It supersedes the
[2026-10-04 entry](2026-10-04-upgrades-skip-package-versions-younger-than-a-week.md).

**What changed.** `exclude-newer` is gone from `[tool.uv]` in `pyproject.toml`,
and the `[options]` block it wrote is gone from `uv.lock`. Removing it moved no
package version. The playbook lost its minimum-age section, the check that
opened the package pass, and the exemption step for a security fix.

**Why.** The maintainer wants each refresh to bring the newest versions. With
the setting on, that took one `exclude-newer-package` entry per young package,
kept in `pyproject.toml` until that version was a week old, because a plain
`uv lock` moves an unexempted young version back and exits 0. On 2026-10-05,
12 of the 13 packages with an update had a newest version under a week old.

**What is given up.** The setting was there to keep a hijacked package out of
the lock and out of the next release. That refresh locked a version published
14 hours earlier (filelock 4.0.12, dev-only), and nothing would now delay one
that ships to users. What still stands between a new version and an installed
copy: updates are made by hand, about monthly, so nothing moves between
refreshes
([2026-10-04 entry](2026-10-04-dependency-updates-stay-manual-run-from-a-playbook.md));
the playbook's release-note reading and its checks by what moved; and
Dependabot alerts on the lockfile.

**The uv pin.** Ruled (user) 2026-10-05, in the same chat: "remove the one
week requirement everywhere." The week no longer applies to the uv release a
refresh pins. A refresh pins the latest release whose installer is being
served, and this one pinned 0.12.23 at three days old.

**Bringing it back.** The 2026-10-04 entry records what uv requires: the
setting has to live in `pyproject.toml`, and an exemption has to stay until its
version is a week old.
