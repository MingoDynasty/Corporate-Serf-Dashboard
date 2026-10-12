# 2026-08-02: The Settings Page Owns Version Display

Status: Accepted

The app's version now appears on the settings page — the release tag on one
line, the commit it was built from on the next — instead of hiding in a
tooltip on the header's GitHub icon. Anyone checking which version they are
running, or quoting one in a bug report, can look somewhere they would think
to look. The section is plain text: it shows what the app already knew about
itself and asks the network nothing. Its two dates can honestly disagree by a
day, because the version dates the release and the second line dates the
commit; that line is labelled Commit so the difference reads as fact, not
error.

Decision (PR #190): the settings page is the venue for build identity, and
`github_component`'s tooltip reverts to a plain "View this app on GitHub".
The build suffix was an explicit stopgap — identity shipped (PR #154) before
any page existed that could own the display, and information behind a hover
on a repo link is found by accident rather than on purpose. A separate About
page was considered and rejected in the same call: a nav destination for three
lines of static text is not worth the space, and the settings page
([entry](2026-08-02-user-settings-live-in-an-app-owned-store-with-a-settings-page.md))
is already the "about this install" home.

The section is static text built with the page layout from
`BuildInfo.release_label` (the CalVer tag, `dev` in a source checkout, or
`unknown`) and `BuildInfo.short_description` (short SHA and commit date). It
re-derives no part of the identity, owns no callback, and makes no request.
Identity resolution is unchanged: the stage-time `release.json` copy and the
full precedence live in
[Build Identity Comes From The Manifest](2026-07-19-build-identity-comes-from-the-manifest-corroborated-by-the-stamp.md),
whose surfaces list this entry rewrites.

Clock semantics (PR #225): the CalVer tag date is the release date in UTC —
CI mints the tag with `date -u` — while the displayed commit date is git's
`%cs`, rendered in the commit's own recorded offset. They date different
events on different clocks, so an evening local-time merge routinely
straddles UTC midnight and picks up a next-day tag. Rather than
UTC-normalising every identity producer to force agreement, the build line
carries a `Commit` prefix that attributes the parenthesised date to its
event.

Sequencing behind that mechanism (PR #188) was a hard dependency, not a
preference. Post-update verification — "the console said it updated to vX; did
it work?" — is the display's peak-usage moment, and a version line reading
`unknown` exactly then looks like a failed update and manufactures the
confused bug reports the display exists to prevent.

Support boundary for that guarantee (maintainer, adjudicating the PR #187
review): the app has a single-user install base, so update paths originating
from releases that predate PR #188 are out of support. The guarantee holds
whenever the launcher staging the update is PR #188's or newer. An install
still on an older release stages its next update without the copy, so that
one trial session shows `unknown`; it self-heals at the next launch, and
permanently once a newer launcher stages the following update. Both escape
hatches already exist — launch again, or re-run the install one-liner. With a
single-user install base this is documented rather than engineered around.

Rejected alternatives:

- **Delivering `release.json` inside the release archive**, so launchers
  predating the copy step still receive the metadata. The zip is pure
  `git archive` output — the only producer that expands the `version.txt`
  stamp — so injecting a generated file means the release job post-processes
  the archive and a second identity artifact must be validated before
  publish. Its only beneficiary is the out-of-support path above. Rejected
  with that boundary, not forever: if the boundary widens, this is the
  mechanism to revisit.
- **An update-availability check on the page** ("newest release is vX"). It
  needs a network call from a page that makes none, plus policy decisions
  (when to check, what to cache) that nothing here requires. Out of scope,
  not rejected forever.
- **A multi-entry `install.json`** with per-version records and an `is_active`
  flag — already recorded, and still rejected, in the entry linked above.

Deliberately not shown: the update policy (automatic, or pinned to a tag). It
is a cheap manifest read, but it only repeats a fact the user set themselves
via the installer; skipped until asked for.
