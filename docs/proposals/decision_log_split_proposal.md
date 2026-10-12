# Decision Log Split Proposal

Status: Proposed
Date: 2026-10-12

## TL;DR

The decision log is one file, and every change that ships adds its entry at
the same line, so two changes in review at once collide there. That has
happened 34 times since August. This proposal gives each decision its own
file, in a folder per year, and changes nothing a decision says. The file's
length is not what is being fixed, and no entry is shortened or removed.

## Decisions needed

Three rulings: L1 to L3. Nothing here is ratified, and the maintainer has
stated no lean on any row. Each row carries a recommendation, its cost, and
what choosing differently changes. Everything in [Design](#design) is
author-owned and open to challenge.

The question came from the maintainer on 2026-10-12: is the log's growth a
problem, and if so, what should be done about it? An advisory consult with
`claude-fable-5-1` answered both questions before reading the author's
answer and reached the same shape. Where it differed, the row says so.

### L1. Each decision gets its own file

Status: open

**Recommendation: split the log into one file per decision, each entry's
text unchanged, in one mechanical PR.**

A new entry becomes a new file, so two PRs that each add one no longer touch
the same line. No file grows large, and a reader who follows a link opens
one entry instead of a 9,312-line page.

The cost:

- **One large PR.** About 155 files change, and 673 links are rewritten by
  one rule. The docs test already fails on any link that is missed.
- **Per-entry history starts at the split.** `git log --follow` on an entry
  file stops at the commit that created it. Everything earlier stays
  reachable under the old path.
- **A transition window.** Every PR open when the split merges has to sync
  with `main` and convert its links before it merges.
  [Landing it](#landing-it) has the rule.
- **Seven links on GitHub die.** By the consult's count, six in five merged
  PR descriptions and one in a review comment point at a heading of the log
  on `main`.

Choosing differently:

- **Leave the file as it is.** The collisions continue wherever two shipping
  PRs are in review together. The question returns on its own between
  February and June 2027, when the file reaches the size at which GitHub may
  stop rendering it.
- **Ship one PR at a time.** The collisions stop with no split. That is a
  change to how the maintainer runs parallel sessions, not to the docs.

### L2. A folder per year, and the folder keeps the log's name

Status: open

**Recommendation: `docs/decision_log/<year>/<date>-<title>.md`, for example
`docs/decision_log/2026/2026-10-11-a-session-ends-after-a-break-of-more-than-30-minutes.md`.**

- **A folder per year, from the start.** Moving the files later means
  rewriting every link a second time, and a year folder never needs it. The
  log gains about 360 entries a year. GitHub's documentation recommends at
  most 3,000 entries in one directory, and users report that the web listing
  of a folder stops at 1,000, which a single flat folder reaches in early
  2029. The consult's own first position was a flat folder with year folders
  added later, and it conceded this point after reading the reason.
- **The folder is named `decision_log`, not `decisions`.** This differs from
  what the author and the consult both said in chat. The docs, the specs, and
  the code comments all call this "the decision log" and one of its parts "a
  decision-log entry". With this name those words stay true, and a search for
  `decision_log` still lands in the right place.
- **Each existing entry's file is named by its heading's anchor.** The anchor
  is what every existing link already carries, so the rewrite is one rule
  with no table: `decision_log.md#<anchor>` becomes
  `decision_log/2026/<anchor>.md`.

Choosing differently:

- **One flat folder.** Simpler to browse today, and a second link rewrite
  when it fills.
- **`docs/decisions/`.** The usual name for such a folder in other projects.
  Every sentence that says "the decision log" then points at a folder called
  something else.

### L3. The split PR publishes no release

Status: open

**Recommendation: the split PR changes no file under `source/` or
`assets/`, so the release job publishes nothing. The 11 code comments that
name `docs/decision_log.md` are corrected by the first later PR that
publishes a release anyway, and `docs/tech_debt.md` lists them until then.**

The release job publishes a new version when any changed path can affect an
installed copy. Markdown files, `docs/`, and `tests/` cannot. A Python file
under `source/` and a JavaScript file under `assets/` can, even when only a
comment changed. Eleven comments in nine such files name the old path. The
other eleven comment lines name the log or one of its entries with no path,
and stay true.

Until they are corrected, each of the 11 names a file that no longer exists,
beside a folder of the same name.

Choosing differently:

- **Correct the comments in the split PR.** No stale path is left behind, and
  a release goes out whose only change is comments. A published release
  cannot be withdrawn.

## Problem

Every figure is from 2026-10-12, at `main` `685d16a`. The scripts that
produced them are untracked scratch in the main checkout, under
`ignore/scripts/decision-log-growth/`.

### What the log is, and who reads it

`docs/decision_log.md` is 582,191 bytes, 9,312 lines, and 129 entries. An
entry is never removed: a decision that changes keeps its old entry, marked
superseded, and 14 entries carry that mark.

Nobody reads the file from top to bottom. Both of its readers arrive at one
entry:

- **An agent** follows a link from a capability spec, or searches for a
  heading, and reads that entry. 463 links in 18 files point at a heading of
  the log, and they reach 115 of the 129 entries. The seven spec files hold
  382 of them. This is the design the log's own rules set: the
  [2026-08-22 entry](../decision_log.md#2026-08-22-the-capability-spec-layer-is-written-in-one-pass)
  makes the specs the way a reader finds the decision behind a behavior.
- **The maintainer** reads the 2 to 4 sentence summary that opens an entry,
  in the PR that adds it. The dense text under it is written for agents, as
  the
  [2026-08-01 entry](../decision_log.md#2026-08-01-doc-style-follow-up--decisions-needed-roadmap-trim-no-log-index)
  says.

So the length costs neither reader. A lookup costs the same at any size, and
GitHub still renders the page: on 2026-10-12 it drew all 129 heading anchors,
and its load event fired at 1.7 seconds.

### What grows

By the month in each entry's heading:

| Month | Entries | kB added | kB per entry |
|---|---|---|---|
| 2026-04 | 12 | 8.5 | 0.7 |
| 2026-06 | 6 | 10.2 | 1.7 |
| 2026-07 | 37 | 97.0 | 2.6 |
| 2026-08 | 32 | 168.0 | 5.3 |
| 2026-09 | 29 | 178.6 | 6.2 |
| 2026-10, first 11 days | 13 | 118.8 | 9.1 |

Two things grow. The count rises by about 30 entries a month, steadily,
because nothing leaves. The size of each new entry has risen from 2.6 kB in
July to 9.1 kB in October. Of the 465 kB added since August, about 40% is
more entries at July's size and about 60% is longer entries.

An entry is long because it is the surviving record of a proposal. The PR
that ships a proposal deletes the proposal file and distills it into the log.
Recent entries are roughly 40 to 50% of the size of the proposal they
replaced (pairs matched by title, so approximate), and what they keep is the
reasons, the evidence, and the alternatives set aside.

### Cost 1: every new entry goes in at the same line

A new entry is inserted at line 16, under the list of status values. Two PRs
that each add an entry therefore change the same line, and the second to
merge conflicts.

Every merge commit since 2026-08-01 was replayed in memory with
`git merge-tree`:

- 271 merge commits. In 45 of them both sides had edited the log.
- In 34 of those 45 the log conflicts. Every one is a single hunk at line 16.
- In 27 of the 34 the log is the only file in conflict.
- The 34 fall on 23 branches. Twelve are dated 2026-10-04 or 2026-10-05.

The fix for each is trivial: keep both entries. The cost is the commit that
carries it. `main` does not require a branch to be up to date before merging
(its protection has `strict` off, and the repository has no rulesets), so in
those 27 cases the log alone forced a sync commit. A sync commit is a new
head, and the review loop exits only when every reviewer has passed the
current head and CI has run on it.

Whether any of the 34 cost a full review round is not shown. The consult
checked four of the branches and found no clear case.

### Cost 2: GitHub stops rendering the page at some size

GitHub's documentation says it renders a Markdown preview for files that are
"generally less than 2 MB", and that a complex file may fall back to plain
text. A plain-text page has no heading anchors, so every link from a spec
would open the top of a 2 MB file.

At the August and September pace, about 173 kB a month, the log reaches 2 MB
around June 2027. At October's pace it gets there around February 2027.

### What is not a problem

- **Entry length.** Once an entry is its own file, a long one costs only the
  reader who opens it. The largest today is 20 kB.
- **Findability.** The specs already map a behavior to its entry. This
  proposal does not claim that finding an entry is hard.
- **Tests and tooling.** Nothing measurable.

## Design

### Layout

```text
docs/decision_log/
  README.md
  2026/
    2026-04-27-use-json-files-for-runtime-api-caches.md
    ...
    2026-10-11-a-session-ends-after-a-break-of-more-than-30-minutes.md
  2027/
    ...
```

`docs/decision_log.md` is deleted. A file listing sorted by name is the
chronology, and nothing maintains it.

### What an entry file holds

Today's entry, word for word. Its `##` heading becomes the file's `#`
heading, date included, and the `Status:` line, the summary, and the payload
follow as they stand. A deeper heading moves up one level with it. One entry
has one.

The entries' own prose is not edited. An entry that mentions
`decision_log.md` in a sentence is a record of its day and stays as written.
Only link targets change, and the six references covered below.

### Names

- **An existing entry** is named by its heading's anchor plus `.md`. All 129
  anchors are distinct, plain ASCII, and at most 94 characters.
- **A new entry** is named `<date>-<title in lowercase with hyphens>.md`, and
  sits in the folder of its year. The author may shorten the title part.
- **The date is the only gated part.** A test requires the date that opens
  the file name to equal the date in the file's heading, and the folder to be
  that date's year. The sorted listing is the chronology, so this is the one
  property a wrong name would break.
- **Order within one day carries no meaning.** 32 days hold more than one
  entry, and one day holds nine. Files from the same day sort by title.

### Links

One rule each, applied by script:

| Link today | Count | Becomes |
|---|---|---|
| From another file to a heading of the log, `decision_log.md#<anchor>` | 463 in 18 files | `decision_log/2026/<anchor>.md` |
| From another file to the log as a whole, `decision_log.md` | 15 in 10 files | `decision_log/README.md` |
| From one entry to another, `#<anchor>` | 178 | `<anchor>.md`, in the same folder |
| From an entry to another doc, such as `specs/sessions.md` | 17 | the same target with `../../` in front |
| From an entry to a web address | 58 | unchanged |

An entry that links to one in another year writes `../2026/<name>.md`.

### References by position

Six sentences point at "the entry above" or "the entry below". Position
means nothing once each entry is a file, so each becomes a link to the entry
it means. These six are the only prose the split rewrites.

### The README

`docs/decision_log/README.md` holds what the top of the log holds today, word
for word: what earns an entry, the rule that a changed decision keeps its old
entry, and the four status values. It adds three lines on naming a new file.
It holds no list of entries. GitHub shows it under the folder's listing.

### Tests

All in `tests/test_docs.py`:

- **The placement test** exempts `docs/decision_log/`, as it exempts the
  proposals and specs folders. That test treats a `Status:` line near the
  top of a doc, or "proposal" in its file name, as the mark of a misplaced
  proposal. Every entry has the first, and at least one has the second.
- **The summary test** reads each entry file in place of each `##` section.
  The summary is still the first paragraph after the heading and the status
  paragraph. The cutover date and the one named exemption carry over.
- **The date test** is new, as described under Names.
- **The two link tests** need no change. They already walk every Markdown
  file under `docs/`.

### Prose that names the file

- **`AGENTS.md`** names `decision_log.md` on ten lines. Each takes the new
  path. "A decision-log entry" keeps its meaning: one file.
- **Three sentences change meaning, and none is reversed.** The log "stays
  the chronological change history": the folder is that history. A shipping
  PR distills "into `docs/decision_log.md`": into a new file in the folder. A
  spec links its entry "by heading anchor": by file.
- **The rejection of a topic index stands.** A folder listing is not an
  index anyone maintains.
- **`docs/architecture.md`, the importer's readme, and the merge-sweep skill**
  name the path in prose and take the new one.

### History

`git log --follow` cannot trace one file into 129. An entry file's history
starts at the split, and earlier history is read with
`git log -- docs/decision_log.md`. The split's commit message says so.

### Landing it

The split conflicts with any branch that predates it, in one of two ways:

- **A branch that added an entry to the old file.** Syncing with `main`
  reports a conflict on `docs/decision_log.md`: deleted on one side, edited
  on the other. The author moves the new entry into its own file.
- **A branch that only added links in the old form.** It merges cleanly, and
  its links dangle. The docs test fails once the branch is synced. Without a
  sync, GitHub would merge it on a check that passed before the split, and
  the test would then fail on `main`.

So the rule for the window is: **a PR opened before the split merges only
after it has synced with `main` and passed the gates again.** The rewrite
rules in the Links table convert its links. On 2026-10-12 one PR is open,
[#356](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/356). It
does not edit the log, and it adds 20 links in the old form.

The maintainer picks the moment. The fewer PRs open, the shorter the window.

### The release zip

`docs/` ships in the release zip, because the shipped README links into it.
The zip therefore gains about 130 small files and loses one large one. The
shipped roadmap's links into the log resolve to files that ship. The list of
paths the zip must carry names nothing under the log.

### Outside the repository

Not changed by the split PR, listed so nothing is a surprise:

- **Two of the maintainer's global skills** name `decision_log.md`, on two
  lines each. The wording still reads correctly as the log's name.
- **One kickoff prompt in the live queue** names the path and needs a
  refresh before it is fired.
- **The author's memory notes and the tracker** name the path in places.

### Copy and terms

No user-facing string changes, and no term is added or redefined.
`docs/glossary.md` changes only in its link targets.

### Alternatives rejected

- **Wait until the file nears 1.5 MB.** This is the consult's strongest
  argument against its own choice: a certain one-time cost now, against a
  per-collision cost that is one trivial hunk. It is set aside because
  waiting makes nothing cheaper. The link count only rises, and the
  collisions continue in the meantime.
- **A `merge=union` attribute on the file.** One line in `.gitattributes`
  that tells git to keep both sides. It never reports a conflict, so two
  branches that edit the same old lines would silently keep both versions,
  and old entries do get edited: 14 carry a superseded mark that a later PR
  wrote. The consult found reports from 2016 to 2018 that GitHub's own merge
  check ignores the attribute, which would leave the sync commit in place.
  Nobody has tested that here. It does nothing about the size ceiling.
- **A few large files, by quarter or by year.** New entries still collide at
  the top of the current file, and the third quarter alone is 444 kB.
- **Files by topic.** A cross-cutting decision has no single home, and the
  specs already map topic to entry.
- **Trim or summarize old entries.** No reader loads the whole file, so it
  saves nothing, and some of the detail cannot be regenerated.
- **A limit on entry length.** Once each entry is a file, length is a cost
  to one reader at a time.
- **Month folders, an index file, or renaming superseded entries.** The
  first adds clicks for about 30 files, the second is the index already
  rejected, and the third breaks links that the `Status:` line makes
  unnecessary.

## Delivery plan

Stated intent, not a contract.

1. **This proposal.** Docs only.
2. **The split**, after L1 to L3 are ruled. One PR, in this commit order:
   - the split itself, each entry cut word for word into its file, with the
     README;
   - the link rewrite and the six references;
   - the test changes;
   - `AGENTS.md` and the other prose;
   - the decision-log entry for this change, written as the first entry born
     as a file, and the deletion of this proposal.

   It opens when the maintainer picks the moment, and the PR description
   lists every PR open at that time.
3. **After the split merges:** each PR that was open syncs and converts its
   links, and the one live kickoff prompt is refreshed.
4. **The 11 code comments,** as L3 rules.

Step 2 is mechanical and fully specified here, so it suits an implementation
session working from a kickoff prompt.

## Out of scope

- **How long an entry is, and what earns one.** The split leaves both alone.
  The consult's observation is recorded for whoever takes it up: an entry's
  length follows its proposal's length, so the place to shorten entries is
  the proposal template.
- **Whether every entry clears the bar for a durable decision.** The consult
  read a sample and found that most do. Nobody has audited all 129.
- **The other files that shipping PRs collide in.** The roadmap, the
  architecture doc, and the specs conflicted in 7 of the 34 replayed merges.
- **The maintainer's global skills and the author's memory notes.**

## Testing

- **The standard gates** pass on the split PR: pytest, ruff format and lint,
  mypy, and compileall.
- **The cut is checked by rebuilding the old file.** At the first commit,
  joining the entry files in the old order, with each heading moved back
  down a level, reproduces every entry of the old log byte for byte. The
  author runs this, and the reviewer runs it again.
- **The link rewrite is checked by the link tests.** Both pass, so no
  Markdown file under `docs/`, the README, or `AGENTS.md` holds a dangling
  link.
- **A search for the old path** over tracked files finds only the entries'
  own prose and the 11 comments L3 defers.
- **The new and changed tests** each have a case that fails: a doc with a
  `Status:` line outside the three exempt folders, an entry whose summary
  has five sentences, and an entry file whose name and heading disagree on
  the date.
- **On GitHub, on the PR's branch:** the folder page shows the README, one
  entry renders, and a link in a spec opens its entry.
- **No release:** `is_release_worthy` returns false for every path the PR
  changes.
