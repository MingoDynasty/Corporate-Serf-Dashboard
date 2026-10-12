# 2026-07-19: Build Identity Comes From The Manifest, Corroborated By The Stamp

Status: Accepted
Superseded in part: 2026-08-02 (PR #188) added a release-file layer above the
manifest and retired the accepted `tag: None` consequence recorded below.
Every other decision in this entry stands.

The app works out which release it is running by reading files left beside the
code and in the install directory, never a version string committed in the
source. Each of those files is trusted only when it agrees with the stamp that
ships inside the downloaded code, so a half-finished update cannot make a new
build report the old version. Since 2026-08-02 the installer and launcher also
leave a copy of the release description next to each installed version, which
is what lets a freshly updated app name its own release right away. Someone
updating the app now sees the right version reported from the first session
rather than a session later. Where they see it is the settings page, which
since 2026-08-02 shows the running version; the header GitHub link's tooltip
used to carry it and no longer does.

Decision: one reader (`source/utilities/build_info.py`) resolves the running
build's identity, and every user-visible build string derives from it. The
precedence is manifest → expanded stamp → git → `unknown` (a release-file
layer was added above the manifest on 2026-08-02; see the end of this entry):

1. **`install.json`** — the install manifest, written atomically by the
   installer/launcher into the state root, never by the app. The only layer that
   can know the release *tag* — until the 2026-08-02 copy, which carries it too.
2. **`version.txt`** — committed with git `export-subst` placeholders
   (`sha: $Format:%H$`, `commit-date: $Format:%cs$`) plus a `.gitattributes`
   entry. GitHub's archive endpoints run `git archive`, which expands them, so
   any zip download carries its full SHA and commit date.
3. **git** — if the placeholders are unexpanded, this is a checkout, so ask it.

The manifest is authoritative **only when it corroborates the running code**:
its `sha` must equal the SHA in the expanded stamp sitting beside that code. The
manifest describes the install's *state*, not any one code directory, so during
a staged update it still names the previous version while the new one is already
running. Unconditional manifest-first precedence would make the new build report
the old identity — and the launcher's own promotion check would then reject it
forever. This was found by the Codex review of PR #154, during implementation,
against a frozen design.

Accepted consequence: a freshly promoted version reports `source: "archive"` and
`tag: None` until the next launch. SHA and date still identify it exactly, and
the tag↔SHA mapping is public in the releases.

**That accepted consequence is superseded (2026-08-02, PR #188).** The
installer and the launcher now copy the release's `release.json` verbatim into
`versions/<tag>/` at stage time, and `build_info.py` reads that copy ahead of
the manifest under the same corroboration rule, reporting
`source: "release-file"`. The copy is written before the staged version ever
runs, so it cannot lag the code it sits beside: a trial build names its own tag
from its first session. The precedence above gains that file at the top and is
otherwise unchanged — the manifest remains the fallback for version directories
staged without a copy, which is how an install still on a pre-copy release
degrades for exactly one update cycle (documented, not engineered around, under
the single-user support boundary).

`version.txt` is deliberately plain `key: value` text rather than JSON: the
committed file needs a comment header (a raw placeholder looks broken to anyone
browsing the repo), and `export-subst` output is not JSON-escaped, so a JSON
envelope would silently constrain future placeholders to escape-safe expansions.

Identity surfaces in three places: a startup line in `data/logs/debug.log`
(bug reports arrive with the log), the `/health` endpoint, and — since
2026-08-02 (PR #190) — a version section on the settings page.

**That surfaces list is corrected and superseded (2026-08-02, PR #190).** It
originally named the header GitHub icon's tooltip and the browser title, and
rejected an app-settings page as spending permanent space on a string read
once per bug report. Two changes:

- The tooltip suffix is gone; the label is a plain "View this app on GitHub"
  again. Hanging version information off a hover on a repo link is an
  affordance failure — it was a stopgap chosen only because no page existed to
  own the display, and the settings page (PRs #181–#184) now does. The
  space objection died with it: the section costs nothing on a page the user
  opened deliberately.
- The browser-title claim was factually wrong. Dash Pages sets a per-page
  title on every navigation, so `document.title` never carried build identity
  in practice. The tab title stays deliberately unversioned — the correction
  is to this claim, not to the title.

Why not have CI commit a version file on every push: the commit changes the SHA,
so the file always describes its own parent; it doubles commit traffic; and it
forces constant fetch friction for the maintainer and for parallel agent
sessions. `export-subst` needs no commits and is never stale.
