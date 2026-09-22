# The README Is A Front Door, And Its Reference Moves To A User Guide

Status: Proposed
Date: 2026-09-19

## TL;DR

The README has grown to about 3,300 words, and most of it is reference
material that a player arriving from a link does not read. This proposal
makes the README a front door: what the app does, how to install it, and
where to get help, in about 1,200 words. Everything that leaves moves, word
for word, into one user guide that the README links. The network disclosure
keeps a short summary in the README, because a reader deciding whether to
run an installer needs it before they install.

## Decisions needed

One row is ruled and five are open; nothing else is ratified. The maintainer
stated leans in chat on 2026-09-19, and each open row records the one that
applies. A lean is non-binding, and two rows (D2, D3) carry an author
recommendation that differs from it. Each open row keeps its recommendation
beside the strongest alternative and what choosing it would change.
Everything else in this proposal is author-owned and sits in Design; a
reviewer may still challenge it.

Two rows reopen decisions from PR #278, the README rework merged on
2026-09-12. They reopen where the content lives, never what it says: every
section that moves keeps the wording #278's review settled. D6 was ruled to
leave #278's outcome standing.

### D1 — The README is a front door, about 1,000 to 1,200 words

Status: Open.

Maintainer lean: the average user reads what the app does and how to
install and use it, and little else. Features should be succinct, not a
paragraph per feature "like it's a spec", and the same goes for
Configuration.

**Recommendation: the README answers four questions and links the rest.**
What is this, how do I install it, what does it do on first run, and where
do I get help. Features are one line each. Configuration is a pointer.
Reference material is one link away. The draft assembled from this proposal
measures 1,241 words against 3,289 today: about 40 over the band's nominal
ceiling once the D6 ruling keeps Run From Source in the file. The band is
an editorial budget, and the qualifiers that carried the draft past it are
true, so the ratified draft's count, not the band, is what implementation
is measured against.

Choosing differently: the research's raw target is about 450 to 700 words,
which is where ShareX, OBS, Syncthing, and Playnite sit. Every one of them
hands off to a website or a wiki, and this project has neither. Reaching
that size means moving the installer-trust paragraph, Updates, and Uninstall
out as well, and those are what make pasting a one-line installer
acceptable. Heroic Games Launcher, the one exemplar without a marketing
site, runs 1,406 words.

### D2 — Everything that leaves goes to one user guide, `docs/user_guide.md`

Status: Open.

Maintainer lean: "What it talks to" and "Playlists and Benchmarks" belong
"in some sort of architecture document".

**Recommendation: one new file, `docs/user_guide.md`, written for users.**
Sections move into it with their headings intact, so every anchor that
other documents link today survives under the new file name. It ships in
the release zip beside the README, and `tests/test_docs.py` checks its
links like any other doc.

Choosing differently:

- **`docs/architecture.md`, the lean.** That file is the contributor and
  agent map of the codebase: 693 lines on modules, threads, and data flow. A
  player asking why the app contacts Plotly, or how to import a playlist,
  will not open a file called architecture, and an agent reading it for
  module structure would wade through user how-to. The content is
  user-facing, so its home should be too.
- **A `docs/guide/` folder of five files.** This was the author's first
  lean in chat. File names such as `network.md` announce themselves in the
  repository tree. The costs: five archive-contract rows instead of one, a
  133-word file for Playlists and Benchmarks, and the `#configuration`
  reference inside Troubleshooting becomes a cross-file link.
- **The GitHub wiki.** Conventional for end-user apps. It is not versioned
  with the code, sits outside the same-PR documentation rule and the link
  gate, and does not ship in the zip.

### D3 — The README keeps a short network summary that links the full disclosure

Status: Open. Reopens #278 D2 (location only).

Maintainer lean: the section does not need to be in the README.

**Recommendation: four sentences stay, and the table moves.** The first two
sentences are today's, unchanged: no usage or crash analytics, and data
stays on the PC. A third names the three reasons the app reaches the
network, by category. The fourth links the full section in the guide. The
reader this serves is the one being asked to paste `irm | iex` from a
Reddit link, and they need it before they install, not after they go
looking.

The summary names categories, not services, so a new service under an
existing category cannot make it false. There is evidence for that choice:
the service-naming short form kept in the maintainer's private launch note
went stale the day chart sharing landed, and still omits Plotly.

The cost is a second surface. The `AGENTS.md` rule that binds the
disclosure to same-PR updates is rewritten to cover the summary too (see
Design).

Choosing differently: fully out of the README, the lean, leaves nothing to
drift, and the README says nothing about network use at the moment the
reader decides to install. Unchanged keeps 429 words between Install and
Troubleshooting. PowerToys uses the recommended pattern: two sentences in
the README that link a separate privacy document. Playnite keeps about 85
words inline.

### D4 — Install keeps its quick start and trust story; Manual install and Rollback move

Status: Open.

Maintainer lean: none on record. The maintainer did not name this section;
the author adds the row because Install is the largest section, at 811
words.

**Recommendation: move 357 words and leave the rest untouched.** Manual
install (133 words) and the collapsed Rollback block (224 words) move to
the guide. The three-step quick start, the paragraph on what the installer
touches, the release-integrity paragraph, Updates, and Uninstall stay
exactly as #278 verified them against the scripts. A short "Other ways to
install" subsection links what moved.

Choosing differently: leaving Install alone puts the README near 1,550
words. Tightening the quick start as well saves about 60 more words, and
the price is rewording sentences that were checked line by line against
`launcher.ps1` and `install.ps1`.

### D5 — Troubleshooting moves whole; the README keeps a pointer and the log location

Status: Open. Reopens #278 D3 (location only).

Maintainer lean: none on record. Also an author-added row: the section is
512 words.

**Recommendation: all eight entries move to the guide, in order,
unchanged.** One list in one place, so the schema-recovery ordering that
#278's review restored travels intact. The README keeps a short paragraph
that names the kinds of symptom covered, links the list, and says where the
logs are. The two failures a new user can hit in the first minute already
explain themselves: the console names a port conflict, and a card on the
Scenario Performance page names a stats folder it could not find.

Choosing differently: keeping three entries inline (port, stats folder,
logs) is the alternative #278 D3 rejected. It adds about 200 words and
splits one list across two files. Leaving the section alone adds about 460.

### D6 — Where Run From Source lives

Status: Ruled (user), 2026-09-21, after the first review wave. Settled
unless material new evidence emerges.

**Ruling: Run From Source stays in the README, reworded so it reads
cleaner.** The section is short, sits below the point where players stop
reading, and is where a contributor and a user managing their own toolchain
both expect to find the commands. Keeping it leaves #278 D4 standing, avoids
duplicating the tech-stack sentence, and keeps the `docs/architecture.md`
archive row true on the README's own account. The rewording is a change in
place, not a move, so the section joins the new README prose block for
review instead of the verbatim rule. Its tech-stack sentence moves within
the README to Development, where it describes the codebase beside the
architecture link; its configuration aside goes, because the sentence about
the Settings page already says where the rest is set.

Material consequences: five blocks move instead of six; "Other ways to
install" links Manual install in the guide and Run From Source in this file;
the guide holds no link into `docs/` today, so the archive-test extension
guards the next such link rather than an existing one; the draft measures
1,241 words.

Rejected: moving the section into the guide as a third install path beside
Manual install. That would have given secondary install paths one
destination and saved about 60 README words, at the cost of a copied
sentence, a reversed unanimous #278 outcome, and one more click for a
contributor. A standalone `docs/development.md` was rejected earlier for
adding a second file and a second archive row for 85 words. The kickoff
prompt parked on 2026-09-12 for that move is retired by this ruling.

## Problem

### Why now

The README is the landing page for the public re-launch: a player arrives
from a Reddit or Discord link, and the first screen decides whether they
install. #278 made the content accurate and complete. Since then the file
has kept growing by one correct paragraph at a time, because the standing
habit is to document each shipped behavior in the README in the same PR.
Nothing in the repository says what does not belong there.

### What was measured

Words per section at `413a8c0`, heading line excluded. A word here is a
whitespace-separated token, which is what `awk '{w += NF}'` counts on any
platform and what `wc -w` counts under a UTF-8 locale. `wc -w` with no
locale set, the default in Git Bash on Windows, skips a standalone em dash
and reads 43 lower on today's file (3,246), so it is not the method.

| Section | Words |
| --- | --- |
| Install | 811 |
| of which Manual install and Rollback | 357 |
| Configuration | 746 |
| Troubleshooting | 512 |
| What it talks to | 429 |
| Features | 302 |
| Playlists and Benchmarks | 133 |
| Found a bug? | 87 |
| Run From Source | 85 |
| Intro, Development, License | 151 |
| Heading lines | 33 |
| **Total** | **3,289** |

Two findings beyond the sizes. `example.toml` already documents every
`config.toml` key, including the no-login warning beside `host`, so the
README's Configuration bullets restate it. And the installed `config.toml`
contains only `port`, so a reader is never looking at `host` without having
opened `example.toml` or the Configuration section first.

### What the sources say

An Opus subagent fetched and read each source below on 2026-09-19. The full
notes, including what could not be fetched, are in the main checkout at
`ignore/design-notes/readme-trim-research.md`. They are a convenience, not
evidence: reviewers should check the sources themselves.

- [GitHub's README documentation](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes)
  lists what a README answers: what the project does, why it is useful, how
  to get started, where to get help, and who maintains it. It sends longer
  documentation elsewhere.
- [Google's documentation guide](https://google.github.io/styleguide/docguide/READMEs.html)
  calls a README a short summary that links the user-facing documentation.
- Art of README (the original repository is gone; read through
  [a fork](https://raw.githubusercontent.com/bradparks/art-of-readme/master/README.md))
  says "The ideal README is as short as it can be without being any
  shorter." It orders content from broadest to most specific, so a reader
  can stop as soon as they have what they came for.
- [makeareadme.com](https://www.makeareadme.com/) is the dissent: it prefers
  too long over too short, while still recommending separate documents for
  the excess.
- [Prana et al.](https://ar5iv.labs.arxiv.org/html/1802.06997) hand-labelled
  4,226 README sections from 393 repositories. 97% of READMEs say what the
  project is and 88.5% say how to use it. Only 25.7% say why it is useful.
  The "why" is the scarce content.
- [Diátaxis](https://diataxis.fr/) says nothing about READMEs. By its types,
  a Configuration section is reference and a Playlists explainer is
  explanation, and both conventionally live in their own documents.

Exemplars, by a raw word count of each file. These are approximate: badge
markup inflates them, and they were taken with a locale-less `wc -w`, which
can read a few words low.

| Project | Words | Features | Configuration | Privacy or network |
| --- | --- | --- | --- | --- |
| ShareX | 176 | website only | none | links a website policy |
| OBS Studio | 300 | one paragraph | none | none |
| Syncthing | 470 | seven goals | none | on its docs site |
| Playnite | 607 | homepage | none | about 85 words inline |
| PowerToys | 882 | a grid of links | none | two sentences linking a separate document |
| Heroic Games Launcher | 1,406 | 16 one-line bullets | none | none |
| Jellyfin | 1,600 | none | developer variables only | none |

No exemplar carries a configuration reference. Feature lists are one line
per feature or live elsewhere. `PRIVACY.md` is not a file GitHub
recognizes, and `SECURITY.md` is for vulnerability reports, so neither is a
conventional home for the network disclosure.

### What constrains a move

- **Inbound anchors.** Three specs and `AGENTS.md` link README headings:
  `#configuration`, `#manual-install`, `#playlists-and-benchmarks`,
  `#what-it-talks-to`, plus `#install` and `#uninstall`, which stay.
  `tests/test_docs.py` fails on a heading anchor that no longer exists.
- **The README ships in the release zip.** Every relative `docs/` link in
  it must be named in `REQUIRED_ARCHIVE_ENTRIES` in
  `scripts/release_job.py`. The test
  `test_readme_doc_targets_are_all_required` enforces that, because the
  archive contract is checked before an irreversible publication.
- **The gate keys off the link, not the file.** A section deleted from the
  README with no link to its new home passes every test and ships a README
  that is silently missing the content.
- **The network rule.** `AGENTS.md` names the README section as the public
  disclosure of outbound network use and requires same-PR updates to it.

## Design

### The rule

The README is for the reader who arrived from a link and has not installed
yet, or installed a minute ago. It says what the app does and why, shows
it, lists features one line each, installs it, and points at help.
Reference, how-to, and explanation for a reader who already runs the app
live in the user guide. A new feature adds at most one line to Features;
its settings, edge cases, and failure modes go to the guide or the spec.

### The README after the trim

Measured on a draft assembled from today's file and the new prose below.

| Section | Today | After | How |
| --- | --- | --- | --- |
| Intro | 78 | 104 | unchanged, plus one "why" sentence; the name line moves below it |
| Features | 302 | 198 | new prose: six one-line bullets, plus today's closing pointer sentence |
| Install | 811 | 491 | unchanged, minus Manual install and Rollback, plus "Other ways to install" |
| What it talks to | 429 | 75 | new prose: the summary (D3) |
| Troubleshooting | 512 | 51 | new prose: the pointer (D5) |
| Found a bug? | 87 | 87 | unchanged |
| Configuration | 746 | 42 | new prose: the pointer |
| Playlists and Benchmarks | 133 | 0 | folded into the Benchmarks bullet |
| Run From Source | 85 | 76 | reworded in place (D6); its tech-stack sentence moves to Development |
| Development | 37 | 52 | unchanged, plus the tech-stack sentence from Run From Source |
| License | 36 | 36 | unchanged |
| Heading lines | 33 | 29 | |
| **Total** | **3,289** | **1,241** | |

Section order is unchanged. The "why" sentence restates the three
questions that open the product overview, so it introduces no new claim.

### What moves, and the verbatim rule

Five blocks move to `docs/user_guide.md`: Configuration, Playlists and
Benchmarks, Troubleshooting, What it talks to, and Manual install with its
Rollback block.

**A moved block is copied, not rewritten.** Headings, wording, order, and
the collapsed `<details>` blocks are preserved. The only permitted edits
are the cross-reference fixes a change of file forces, and the
implementation PR lists each one in its description:

- References inside a moved block to the install one-liner ("the one-liner"
  in Manual install, "the install one-liner" in Rollback) gain a link to
  the README's Install section. "The easy install", in the Uninstall
  footnote, stays in the README and needs none.
- The `#configuration` reference inside Troubleshooting needs no change,
  because both sections land in the same file.

This is what keeps #278's two review redlines intact without re-arguing
them: the network table names services and never hostnames, and schema
recovery leads with backing up the `data` folder and the converter script.

Nothing in a moved block is dropped. Two sections are rewritten in place
rather than moved, and their new text sits in the prose block: Features,
and Run From Source under the D6 ruling, whose tech-stack sentence moves
within the README to Development. The one deliberate loss is in Features:
the per-feature detail that the capability specs already state. That covers how a notification
replaces the previous one, the celebration's covered-window and
reduced-motion behavior and its Settings control, the chart-point
preferences, and the manual **Refresh** button for when the leaderboard
lags.

### The user guide

`docs/user_guide.md`, H1 "User Guide", opening with two sentences: the
README covers what the app is and how to install it, and this guide covers
everything after that. Sections in this order, by how often a running user
needs them: Configuration, Playlists and Benchmarks, Troubleshooting, What
it talks to, Manual install. Heading text is unchanged, so the anchors are
`#configuration`, `#playlists-and-benchmarks`, `#troubleshooting`,
`#what-it-talks-to`, and `#manual-install`.

### New README prose

No app copy changes: the copy rules govern strings the app's code shows,
and the README is a document. The new prose is gathered here anyway, and
reviewers are asked to redline it as they would a Copy block. Everything in
the README that is not in this block is today's text. Two sentences inside
it are today's text in a new place: the pointer sentence that closes
Features today closes it still, and the tech-stack sentence that opens Run
From Source today moves to Development. Run From Source itself is reworded
in place under the D6 ruling, so its new text is here too. A heading in
the block introduces that section's whole new text, so Development shows
the sentence it gains and then today's paragraph, unchanged.

````markdown
It turns the runs you already play into answers to three questions: am I improving, where am
I weak, and what should I work on next?

## Features

- **Scenario plots** — Score vs Sensitivity and Score vs Time for each scenario, with optional
  PB-score, score-threshold, and benchmark-rank overlays.
- **Run notifications** — one toast when a run earns a verdict, titled with it: score-threshold
  pass or fail against your personal best, or the top-N placement it earned. A run that earns
  neither says nothing.
- **Personal best celebration** — confetti, fireworks, cannons, or stars when a run beats your
  scenario best, on whatever page you have open.
- **Leaderboard standing** — your global position and percentile for the selected scenario, e.g.
  `Position: 11,290 of 63,892 (82.33% percentile)`, refreshed after a new personal best.
- **Playlist scenarios table** — every scenario in a playlist with position, percentile, last
  played, runs, and personal-best stats; sort by percentile to build a training priority list.
- **Benchmarks** — a bundled benchmark library, built with the help of
  [Evxl.app](https://evxl.app)'s author. Voltaic and Viscose are visible by default, the
  **Show hidden** switch on the Playlists page lists the rest, a playlist's eye icon turns one
  on, and **Import** adds any playlist by share code. More in
  [Playlists and Benchmarks](docs/user_guide.md#playlists-and-benchmarks).

The rationale behind each feature lives in [docs/product.md](docs/product.md); what's next in
[docs/roadmap.md](docs/roadmap.md).

### Other ways to install

[Manual install](docs/user_guide.md#manual-install) installs from a release you have inspected
yourself, and covers rolling back to, and pinning, an older release.
[Run From Source](#run-from-source) is for development, or for managing the toolchain
yourself.

## What it talks to

The dashboard does not collect or send usage or crash analytics. Your runs, settings, and
caches stay on your PC unless you share a chart yourself. Three things reach the network:
installing and updating it, leaderboard lookups once a KovaaK's username is set, and the
actions you click (detecting your accounts, importing a playlist, sharing a chart).
[What it talks to](docs/user_guide.md#what-it-talks-to) in the user guide lists every service
and what makes the app reach it.

## Troubleshooting

[Troubleshooting](docs/user_guide.md#troubleshooting) in the user guide lists problems by what
you see, such as a port already in use, a stats folder that was not found, a missing
leaderboard position, or a slow first start. An installed copy keeps its logs in
`%LOCALAPPDATA%\CorporateSerfDashboard\data\logs`; a source checkout keeps them in its own
`data\logs`.

## Configuration

Most settings live on the dashboard's own **Settings** page: where your KovaaK's stats live,
and who you are on the leaderboards. Boot settings such as `port` live in `config.toml`
(installed: `%LOCALAPPDATA%\CorporateSerfDashboard\config.toml`), which updates never touch.
[Configuration](docs/user_guide.md#configuration) in the user guide covers both.

## Run From Source

Run from a git checkout if you develop the app, or if you would rather manage the toolchain
yourself. You need git and [uv](https://docs.astral.sh/uv/):

```shell
git clone https://github.com/MingoDynasty/Corporate-Serf-Dashboard.git
cd Corporate-Serf-Dashboard
uv sync
```

Copy `example.toml` to `config.toml`, then start the app:

```shell
uv run python source/app.py
```

The stats folder is detected on the first start, and the Settings page covers whatever it
missed. A checkout does not update itself: `git pull` is the update path.

## Development

The app is Python + [Dash](https://dash.plotly.com/) (Plotly, Dash Mantine Components);
[docs/architecture.md](docs/architecture.md) has the module map.

Development uses AI coding agents. Every change is reviewed and must pass the
project's test suite and CI gates (ruff, mypy, pytest) before it merges; the
reasoning behind the durable choices is public in the
[decision log](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/blob/main/docs/decision_log.md).
````

The choices inside that block, each open to challenge:

- **The network summary is checked against the table row by row.** Rows one
  to three are installing and updating. Row four is leaderboard lookups
  behind a username, which includes the background percentile fill. Row
  five is two of the clicked actions and row six is the third. It stays
  consistent with the sentence that moves to the guide: with no username
  set, the running app makes no requests on its own. It names triggers
  rather than making the app the actor, because the install and the
  launch-time update check run in the scripts before the app exists.
- **The Run notifications bullet keeps today's qualifier** that a run
  earning neither verdict says nothing. A live run with no score-threshold
  verdict that lands outside the top N produces no toast, so a bullet
  promising one toast per run would be false under ordinary settings.
- **The Benchmarks bullet keeps both steps of enabling a hidden benchmark.**
  The **Show hidden** switch only lists hidden playlists in the overview;
  a row's eye icon is what adds one to every picker, and so to the
  benchmark-rank overlays.
- **The Troubleshooting pointer names both log locations**, because the
  README still advertises Run From Source, whose logs live in the checkout.
- **Run From Source is reworded, not moved.** The opening fragment becomes a
  sentence, the tech-stack sentence leaves for Development, and the
  configuration aside goes, because the sentence about the Settings page
  already says where the rest is set. Every fact stays: git and uv, the
  three commands, copying `example.toml` to `config.toml`, first-start
  detection, and no self-update.
- **The Configuration pointer names `port` and never `host`.** `host` is
  the one setting with a security consequence, and its no-login warning
  lives beside it in `example.toml` and in the guide. The README should not
  name the key without the warning.
- **The plots bullet uses the chart modes' on-screen names**, Score vs
  Sensitivity and Score vs Time. Today's bullet paraphrases them.
- **The name line moves below the description**, so the first sentence
  under the title says what the app does. The wording is unchanged.

### Links and contracts

- Three specs name the README in prose as well as in a link, so each gets
  a sentence edit, not an href swap. `docs/specs/settings.md` says the
  user's view of both files is the README's Configuration section, and
  will say it is the guide's. `docs/specs/playlists.md` says the same of
  Playlists and Benchmarks. `docs/specs/release_and_install.md` names
  Install, Manual install, and Uninstall in one sentence, and is rewritten
  so that Install and Uninstall stay with the README and Manual install
  goes to the guide. The `#install` and `#uninstall` links stay.
- The README's release-integrity paragraph repoints its Manual install
  link to the guide.
- `REQUIRED_ARCHIVE_ENTRIES` gains one row, `docs/user_guide.md`, with a
  comment in the existing style. The `docs/architecture.md`,
  `docs/product.md`, and `docs/roadmap.md` rows each say the shipped README
  links them, and that stays true only because the prose block carries the
  Features pointer sentence and the tech-stack sentence. The archive test
  checks one direction, that every README link is a row, and not that
  every row is still linked, so a row whose justification lapses goes
  false without a failing gate. A row whose link moves to the guide gets
  its comment updated in the same commit.
- The archive test reads relative `docs/` links from the README only. The
  guide is a second shipped document with links of its own; today it holds
  none into `docs/`, only links back to `README.md#install`, so the extension
  guards the next such link rather than an existing one. The author
  recommends extending
  `test_readme_doc_targets_are_all_required` to the guide's links, resolved
  from `docs/`. It is the same failure the test exists for. It goes beyond
  the trim itself, so it is flagged here and is cheap to drop.

### The `AGENTS.md` rules

The network rule in Documentation Habits is rewritten in place. The guide's
section becomes the public disclosure, the same-PR duty is unchanged, and
one duty is added: the PR also checks that the README's summary is still
true. The services-not-hostnames sentence and its link to the #278 thread
are kept.

One new bullet records the rule from this proposal, so the README does not
grow back: the README is the front door; user-facing reference, how-to, and
troubleshooting go to `docs/user_guide.md`; a new feature adds at most one
line to Features. Enforcement is review-only, like the prose rules beside
it.

A third edit scopes the shipping checklist. Its opening line reads as
unconditional, and a reviewer read it that way on this proposal, so one
sentence under "Shipping a proposal" says that steps 4 and 5, the roadmap
milestone and the product inventory, apply when the proposal ships an app
feature, and that a docs-only proposal records itself in the decision log
alone. #278 and #301 relied on that reading without writing it down; this
proposal writes it down.

### Alternatives rejected

- **A word-count gate in `tests/test_docs.py`.** It would fail unrelated
  PRs on an editorial threshold, and the docs test deliberately gates
  structure, never prose.
- **Collapsing sections into `<details>` blocks in place.** The words stay
  in the file and in every diff, and a collapsed block is invisible to a
  reader searching the page.
- **Rewriting the moved sections while moving them.** It would reopen
  wording that #278 verified against code, and it would make the move
  unreviewable as a move.
- **A table of contents.** At about 180 lines GitHub's outline button
  covers it.

### Blast radius

One new file, one README rewrite that is mostly deletion, three spec
sentences rewritten to name the guide, three `AGENTS.md` edits, one
archive row, and one test extension. No application code changes. Because
`scripts/release_job.py` changes, the merge is release-worthy and cuts a
release; that release is how the new README and the guide reach installed
copies. External links to the old README anchors, in a forum post for
instance, land at the top of the README and no longer scroll to the
section.

## Out of scope

- The wording of every moved section, including the network table and all
  eight troubleshooting entries.
- `docs/example.png`, the screenshot, and any new visual such as a GIF.
- A website, a wiki, or GitHub Pages.
- A `CONTRIBUTING.md`. The Development section's statement on AI-assisted
  development stays where #278 D1 put it.
- The license section, and mentioning the license nearer the top.
- In-app links. The app links the repository and the bug form, never a
  README section, so no app code depends on these anchors.
- De-duplicating the moved Configuration section against `example.toml`,
  which already documents every key. The verbatim rule forbids rewriting
  while moving, so it is a separate change; the implementation PR files it
  as a Backlog line so the finding survives this proposal's deletion.

## Testing

- This PR is one Markdown file: `git diff --check` and
  `uv run pytest tests/test_docs.py`.
- The implementation PR runs the five gates. `tests/test_docs.py` proves
  every relative link and heading anchor resolves after the move, and
  `tests/test_release_job.py` proves the archive contract names every
  `docs/` target the README links.
- The move is proven as a move: commit 1 of the implementation PR is
  reviewed with `git diff --color-moved`, and the PR description lists each
  permitted cross-reference fix.
- A link that resolves is not evidence that the sentence around it is
  still true. The PR description quotes each edited spec sentence, and the
  reviewer reads it against the section it now names.
- The size is proven by `awk '{w += NF} END {print w}' README.md`, the
  platform-independent count used throughout, against the ratified
  draft's count rather than D1's band.
- Manual: open the branch's README and guide on GitHub and follow every
  link once, including the collapsed Rollback block.

## Delivery plan

1. **This PR: the proposal.** The review lane follows the maintainer's
   direction in chat on 2026-09-19 and is recorded in the PR description.
   The author is a Fable session, so there is no Fable review seat.
2. **One implementation PR** (Opus 5 at high, from a kickoff prompt written
   into `ignore/prompts/` after ratification), in four commits:
   1. the move: the five blocks leave the README for `docs/user_guide.md`
      with only the listed cross-reference fixes, the specs and the
      `AGENTS.md` link repoint, and the archive row lands. This must be one
      commit, because the link and archive gates fail on any subset;
   2. the new README prose from the block in Design, exactly as ratified,
      with any divergence flagged in the PR description;
   3. the three `AGENTS.md` edits and the archive-test extension;
   4. the docs definition of done.
3. **Docs definition of done**, in the implementation PR: a decision-log
   entry, opening with its plain-language summary, that records the front
   door rule, the guide as the home of user-facing reference, and the
   network disclosure's two surfaces; this proposal file deleted; the
   kickoff prompt moved to `ignore/prompts/done/`. No capability spec
   covers the README, and no app behavior changes, so there is no spec
   statement, `docs/roadmap.md`, or `docs/product.md` change beyond the
   three edited spec sentences.

Rows ruled differently shrink the plan without reshaping it: a block ruled
to stay is left out of commit 1, and its pointer is left out of commit 2.
If D2 is ruled for a different destination, commit 1 targets that file and
the rest holds.
