# 2026-09-22: The README Stops Explaining How The Installer Works

Status: Accepted

A second pass on the README cut the installer details a player does not need
before installing, such as how releases are verified and how an update
protects itself. Install now covers only what the player does and sees.
A reader who wants to check a release before running it follows the manual
install link, which now carries the digest check in full.
The README also shows the playlist pages, and its screenshots live in their
own folder.

**What this reverses.** The
[front-door entry](2026-09-22-the-readme-is-a-front-door-and-user-reference-lives-in-a-user-guide.md)
kept Install's paragraph on what the installer touches, the
release-integrity paragraph, Updates, and Uninstall unchanged, "because those
are what make pasting a one-line installer acceptable". The maintainer
overrode that the same day: the average reader does not care how releases are
made. A separate release document was considered and not made, because each
fact already has a home:

- The installer-touches paragraph (one root under `%LOCALAPPDATA%`, its own uv
  and Python, no registry, `PATH`, or machine-wide toolchain) lives in
  `docs/specs/release_and_install.md` and the
  [installer entry](2026-07-19-the-installer-brings-its-own-toolchain-app-locally.md).
  Its "nothing else is touched" also overstated: the desktop shortcut and
  `get.ps1`'s `%TEMP%` copy sit outside the root.
- The release-integrity paragraph: the digest check, `Get-FileHash` included,
  moved into the user guide's Manual install step, which already listed the
  digest; immutability and the archive contract live in the release spec and
  the [immutability](2026-07-19-releases-and-their-assets-are-immutable.md) and
  [archive-contract](2026-08-21-release-integrity-rests-on-github-digests-and-an-enforced-archive-contract.md)
  entries.
- Updates' promotion-after-a-healthy-start and untouched-`config.toml`-and-`data`
  sentences live in the release spec and the user guide's Configuration
  section.
- Uninstall lost its registry and `PATH` list and the `%TEMP%` script's
  "inert" clause. The `%TEMP%` `<details>` block stays, because the installer
  entry says the README documents deleting that file, and Uninstall's
  closing sentence names that script as the one change outside the folder
  and the shortcut; an unqualified "nothing else on the machine was
  modified" would be false while the script remains.
- Also cut: Run From Source's first-start and `git pull` paragraph, the
  `product.md` rationale pointer, and the bug section's account of why
  `debug.log` matters. The bug section asks for no logs at all and leaves that
  to the bug form, which names the file for each failure and warns that
  attachments are public; a blanket request for "log files" invites
  over-sharing, and the issue chooser also leads to the feature-request form,
  which asks for none. Run From Source stays, per the front-door entry's
  2026-09-21 ruling.

**Development links `docs/`, not `architecture.md`.** The front-door entry put
the tech-stack sentence beside the architecture link, "which keeps the
`docs/architecture.md` archive row true on the README's own account". The
sentence now points at the `docs/` folder, and with the `product.md` pointer
also gone, neither file is a target of the README or the user guide. Those two
shipped entry points are what the contract's documentation rows cover, per the
[archive-contract entry](2026-08-21-release-integrity-rests-on-github-digests-and-an-enforced-archive-contract.md)
and the two tests that hold their targets in `REQUIRED_ARCHIVE_ENTRIES`, so
both rows left it. `docs/roadmap.md`, itself a row, still links both, as it
links `decision_log.md`, a spec, and a proposal that never had rows: targets
one hop further in are covered by `.gitattributes` keeping `docs/` whole, not
by rows. Relinking either file from the README or the guide fails that
entry point's test until the row returns. The AI-assisted-development sentence
(#278 D1) stays, shorter.

**Screenshots live in `docs/screenshots/`**, named for the view they show:
`scenario_performance.png` (formerly `docs/example.png`), `playlists.png`,
and `playlist_scenarios.png`. `.github/` was rejected because `.gitattributes`
prunes it from the release zip, which would break the shipped README's
images; `assets/` because Dash serves it at runtime. Each embedded image is
its own `REQUIRED_ARCHIVE_ENTRIES` row: a `docs/screenshots/` directory row
would still pass after the embedded file was renamed away. The two playlist
shots are cropped to the page title, its controls, the column headers, and
six rows, and stack at full width below Features. Side by side at half width
was rejected: at GitHub's README width their table text renders about 3 px
tall.

**Tagline and Run notifications.** The tagline names history as well as live
runs, because "plotted as you play" read as the app's only use when it also
serves reviewing past runs. The Run notifications bullet now reads "a toast to
compare your new run against your personal best": it no longer names the
top-N verdict or says that a run earning neither gets no toast, the qualifier
the front-door entry's size paragraph defended. The maintainer chose this
wording on 2026-09-22, intending every run to notify, which has not fully
shipped. Under default settings it holds for the latest live run of each poll
on the Scenario Performance page: that run gets a threshold pass or fail
against the previous best, a top-N placement when it is the first at its
sensitivity, or the personal-best celebration. Earlier runs coalesced into the
same poll stay plot-only, a personal best among them included, and the latest
run also goes silent when the threshold verdict is switched off or its
percentage is blank and the run falls outside the top N; the notifications
spec states those edges.

**Size.** 772 words in 148 lines by the front-door entry's measure, down from
1,196 at #308's merge.

**Superseded in part (2026-10-13).** The Run notifications bullet reads "a
toast on every page when a new run is detected, with a link to its scenario on
Run History." Every run notifying, which this entry says "has not fully
shipped", has shipped: the edges listed above went with the verdict and the
placement, and the toast no longer needs one page open. One edge is left, by
the maintainer's ruling: runs detected together share one toast, for the
newest. See
[A Run Toast Is Plain And Shows On Every Page](2026-10-13-a-run-toast-is-plain-and-shows-on-every-page.md).

Provenance: the maintainer's own README edits, reviewed and completed in PR
#309; no proposal.
