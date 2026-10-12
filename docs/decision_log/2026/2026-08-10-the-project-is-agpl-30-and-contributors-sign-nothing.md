# 2026-08-10: The Project Is AGPL-3.0, And Contributors Sign Nothing

Status: Accepted

Corporate Serf Dashboard is licensed under the GNU Affero General Public
License, version 3 or any later version, its copyright is held by
MingoDynasty, and contributors are not asked to sign a contributor agreement.
Anyone may use, change, and redistribute it, but a version they pass on has to
stay free and open source under the same terms. The choice was confirmed
deliberately on 2026-08-10, before the public launch, because it is the one
launch decision that cannot be taken back later. A few assets the app bundles
from other projects keep their own terms, so this is not a whole-tree claim.

**What was chosen.** AGPL-3.0 for this project's own code, whole text in
`LICENSE`. No contributor license agreement, no copyright assignment: a pull
request is accepted on its merits, and its author keeps their copyright. The
ruling is from 2026-08-10; the README's `## License` section has stated the
license publicly since PR #278, and this entry is the record of why.

**Amended 2026-09-13: the holder is named and the version form is chosen.**
The maintainer ruled both on 2026-09-13. The copyright holder is
MingoDynasty, the maintainer's commit and GitHub handle, and it is the sole
holder: `git shortlog -sne fd812fd`, run on the amending PR's base, lists only
the maintainer's own identity and the maintainer's Codex and Claude agent
sessions. The license form is AGPL-3.0-or-later. Until this amendment the
README said "v3.0" with no "or any later version" wording, and section 14 of
the license applies only the named version in that case, so the project was
3.0-only by omission rather than by ruling. Or-later was chosen so that a
future AGPL revision, such as one fixing a flaw, can be adopted without
relicensing, which stops being possible at the first outside contribution.
Section 14 bounds the risk the other way: later versions are promised to be
similar in spirit, and following one imposes no additional obligation on any
author or copyright holder. Per-file copyright headers were considered and
rejected: the project has a single author, `LICENSE` is enforced into every
release zip, and the app header links the source.

**Bundled third-party assets keep their own licenses**, and this is not a
whole-tree AGPL claim. `assets/vendor/canvas-confetti.js` is ISC
(`assets/vendor/canvas-confetti.LICENSE`), and the vendored SVGs under
`assets/icons/` are MIT, Apache-2.0 and CC0 by collection, tabulated in
`assets/icons/README.md`. `assets/` is in the release archive contract, so
those notices travel inside every published zip and have to be preserved on
redistribution. Vendoring anything new means confirming its license and
recording it the same way. `resources/` ships under the same contract but is
imported data, not vendored code: the benchmark library, a snapshot of Evxl's
benchmark index, and a KovaaK's game-settings response. No license is recorded
for any of it, and this entry does not settle whether one should be.

**Amended 2026-10-05: one bundled file is under no open license.**
`assets/icons/evxl-logo.png` is Evxl's logo. It ships with its owner's
permission, recorded in `assets/icons/README.md`, and neither the AGPL nor
any icon collection's license covers it. The detail is in
[the 2026-10-04 Evxl entry](2026-10-04-a-benchmarks-scenario-page-links-to-its-evxl-page.md).

**Why this license.** The priority is that derivatives stay free and open
source. AGPL binds anyone who conveys a modified version, or offers one to
users over a network, to make that version's source available to those
recipients or users under the same terms.

**Why no CLA.** At this scale the friction a CLA puts in front of a first-time
contributor costs more than the flexibility it buys. What it would have bought
is the ability to relicense later without hunting down every contributor, and
that is the price being paid knowingly.

**The relicensing window closes at the first outside contribution, on
purpose.** Relicensing needs the consent of every copyright holder. Today that
is one person, so the license could still be changed unilaterally. The moment
an outside pull request is merged, it cannot. A public launch invites exactly
that, which is why the question was answered before launching rather than
after.

**Rejected alternatives.**

- **MIT or Apache-2.0.** Permissive terms would allow a closed commercial fork
  of the app, which is the outcome the choice exists to prevent.
- **AGPL plus a CLA, or copyright assignment.** Keeps the relicensing option
  open, at the cost of asking every contributor to sign before their first
  patch. Judged not worth it here.

**Where the terms travel.** `LICENSE` is named in `REQUIRED_ARCHIVE_ENTRIES`
in `scripts/release_job.py`, so a release whose zip lost it fails the draft
rather than shipping: every published copy carries the terms. The README's
`## License` section states them for readers who never open the file. Since
the 2026-09-13 amendment that section also carries the copyright line, and
`pyproject.toml` carries `authors` and the SPDX `license` expression
`AGPL-3.0-or-later`. Both files are release-archive entries too, so every
published zip carries the notice and the metadata.
