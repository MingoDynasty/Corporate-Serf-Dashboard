# 2026-09-22: The README Is A Front Door, And User Reference Lives In A User Guide

Status: Accepted (amended by
[2026-09-22](2026-09-22-the-readme-stops-explaining-how-the-installer-works.md):
Install no longer carries the installer-touches or release-integrity
paragraphs, and Development links `docs/` rather than `architecture.md`; and
by the
[2026-09-30 sentence-count entry](2026-09-30-the-docs-test-counts-summary-sentences-and-its-count-is-the-definition.md):
the docs test now counts summary sentences, so "that test gates structure,
never prose" holds for everything but that count, and the README word-count
gate stays rejected)

The README had grown to 3,289 words, most of it reference material that a
player arriving from a link never reads. It is now a front door: what the app
does, one line per feature, how to install it, and where to get help.
The reference sections moved word for word into a user guide that the
README links.
The README keeps a short summary of the app's network use, because a reader
deciding whether to run the installer needs it before they install.

**The rule.** The README is for the reader who arrived from a link and has not
installed yet, or installed a minute ago. It says what the app does and why,
shows it, lists features one line each, installs it, and points at help.
Reference, how-to, and troubleshooting for a reader who already runs the app
live in `docs/user_guide.md`. A new feature adds at most one line to Features;
its settings, edge cases, and failure modes go to the guide or the capability
spec. `AGENTS.md` carries the rule under Documentation Habits, and review
holds it. A word-count gate in `tests/test_docs.py` was rejected: it would
fail unrelated PRs on an editorial threshold, and that test gates structure,
never prose. Collapsing sections into `<details>` in place was rejected too:
the words stay in every diff, and a collapsed block is invisible to a reader
searching the page.

**One guide.** Everything that left went to one file written for users.
Each section kept its heading text, so the anchors other documents link
(`#configuration`, `#playlists-and-benchmarks`, `#troubleshooting`,
`#what-it-talks-to`, `#manual-install`) survive under the new file name.
Sections run by how often a running user needs them: Configuration, Playlists
and Benchmarks, Troubleshooting, What it talks to, Manual install.
`docs/architecture.md` was rejected as the home because it is the contributor
and agent map of the codebase, and a player will not open a file called
architecture. A `docs/guide/` folder of five files would have cost five
archive rows and made the `#configuration` reference inside Troubleshooting a
cross-file link. The GitHub wiki is not versioned with the code, sits outside
the same-PR documentation rule and the link gate, and does not ship. The guide
does ship: `REQUIRED_ARCHIVE_ENTRIES` names it, and `tests/test_release_job.py`
requires every target it links, resolved from `docs/`, as it already did for
the README's `docs/` links.

**The network disclosure has two surfaces.** The guide's What it talks to
section is the public disclosure: the table of services, never hostnames, and
its caveats. The README keeps four sentences under the same heading: no usage
or crash analytics, data stays on the PC, three things reach the network
(installing and updating, leaderboard lookups once a username is set, and the
actions the user clicks), and a link to the guide. The summary names
categories rather than services, so a new service under an existing category
cannot make it false; a service-naming short form in the maintainer's launch
notes went stale the day chart sharing landed. It stays in the README because
the reader being asked to paste `irm | iex` needs it before installing, not
after going looking. The cost is a second surface, so a PR that adds an
outbound service or a new trigger updates the guide's section and checks that
the README's summary is still true, in the same PR.

**The move is verbatim.** Configuration, Playlists and Benchmarks,
Troubleshooting, What it talks to, and Manual install with its Rollback block
were copied, not rewritten. Wording, order, the collapsed `<details>` blocks,
the network table's services-not-hostnames shape, and the schema-recovery
entry's order (back up `data` first, the converter script, the hand edit
last) all carried over. The only edits: the three references to the install
one-liner, in Manual install, Rollback, and the network table's first row,
link to the README's Install section, and Manual install's heading is H2
because the guide has no Install section for it to sit under. Rewording while
moving was rejected because it would reopen text #278 verified against the
scripts and make the move unreviewable as a move. Install keeps its
three-step quick start, the paragraph on what the installer touches, the
release-integrity paragraph, Updates, and Uninstall, unchanged, because those
are what make pasting a one-line installer acceptable. Troubleshooting moved
whole, all eight entries in order, rather than splitting a few inline entries
from the rest; the README's pointer names both log locations, because it still
advertises Run From Source, whose logs live in the checkout. Features was
rewritten in place from ratified prose; its lost per-feature detail is what
the capability specs already state.

**Run From Source stays in the README, reworded (ruled 2026-09-21).** The
section is short, sits below where players stop reading, and is where a
contributor and a user managing their own toolchain both look for the
commands. Its opening fragment became a sentence, its configuration aside
went, and its tech-stack sentence moved to Development beside the
architecture link, which keeps the `docs/architecture.md` archive row true on
the README's own account. Moving it into the guide as a third install path
was rejected: it would have saved about 60 README words at the cost of a
copied sentence, a reversal of #278's unanimous outcome, and one more click
for a contributor. A standalone `docs/development.md` was rejected as a second
file and a second archive row for 85 words.

**The size is 1,241 words in 179 lines.** Words are whitespace tokens,
`awk '{w += NF} END {print w}' README.md`; a locale-less `wc -w` in Git Bash
skips standalone em dashes and reads low. The proposal set 1,000 to 1,200 as
an editorial budget, and the result sits about 40 over it once Run From Source
stayed. The qualifiers that carry it past the band are true and stayed: the
Run notifications bullet keeps that a run earning neither verdict says
nothing, because one toast per run is false under ordinary settings, and the
Benchmarks bullet keeps both steps of enabling a hidden benchmark. Going
further, to the 450 to 700 words of the shortest exemplars, would have meant
moving the installer-trust paragraph, Updates, and Uninstall as well.

**Shipping-checklist scope.** Steps 4 and 5 of "Shipping a proposal" in
`AGENTS.md`, the roadmap milestone and the product inventory, apply when a
proposal ships an app feature; a docs-only proposal records itself in the
decision log alone. Earlier docs-only changes relied on that reading without
writing it down; this change writes it down, and it is why this change adds no
roadmap or product entry.

Provenance: distilled from `docs/proposals/readme_trim_proposal.md` (proposed
in PR #303; D6 ruled 2026-09-21, D1 to D5 ratified 2026-09-22), shipped in PR
#307; the proposal file is deleted in the shipping PR and git history holds
its full text.
