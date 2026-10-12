# 2026-07-19: Releases And Their Assets Are Immutable

Status: Accepted

Decision: GitHub's immutable-releases setting is enabled on the repo, so tags
and releases cannot be moved or deleted. The release job therefore creates a
tag, then a **draft**, attaches assets, validates them, and only then publishes.

Why: rollback is only trustworthy if `v2026.07.19` means the same bytes forever;
a movable tag makes "go back to the version that worked" meaningless. The
setting is not retroactive, which is why it was flipped *before* the release-job
PR merged — that merge cut the first release, and a release published while the
setting was off stays mutable forever.

The consequence to remember: assets lock at publication, so validation must run
pre-publish. After an immutable release is published it is too late to fix a bad
asset — the only remedy is another release. This is what forces the draft-first
flow above; do not "simplify" it into publish-then-attach.

Launcher-side checksum verification is deliberately deferred: HTTPS to
github.com is the trust anchor at this audience size.
