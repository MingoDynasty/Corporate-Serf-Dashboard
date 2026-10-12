# 2026-10-12: Each Decision Is Its Own File, In A Folder Per Year

Status: Accepted

The decision log was one file, and every change that shipped added its entry
at the same line, so two changes in review at once collided there. Each
decision is now its own file, in a folder per year, and no decision's text
changed. A new decision is a new file, so two pull requests that each add one
no longer touch the same line. The length of the old file was not what was
fixed, and no entry was shortened or removed.

**Ruling.** Ruled (user) 2026-10-12: accept the recommendation on rows L1,
L2, and L3 of the split proposal
([#361](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/361)),
after the Codex seat had endorsed all three. An advisory consult with
`claude-fable-5-1` had reached the same shape before it read the author's
answer. The split shipped in
[#366](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/366).

**Why split (L1).** A new entry was inserted at line 16 of the one file,
under the list of status values. Two pull requests that each added an entry
therefore changed the same line, and the second to merge conflicted. Every
merge commit since 2026-08-01 was replayed in memory with `git merge-tree`,
on 2026-10-12 at `main` `685d16a`:

- 271 merge commits. In 45 of them both sides had edited the log.
- In 34 of those 45 the log conflicted, each time in a single hunk at line 16.
- In 27 of the 34 the log was the only file in conflict.
- The 34 fall on 23 branches. Twelve are dated 2026-10-04 or 2026-10-05.

Each fix was trivial: keep both entries. The cost was the commit that carried
it. `main` does not require a branch to be up to date before merging, so in
those 27 cases the log alone forced a sync commit, and a sync commit is a new
head that review and CI have to pass again. Whether any of the 34 cost a full
review round was not shown.

Length was not the reason. Nobody reads the log from top to bottom. An agent
follows a link from a spec to one entry, and the maintainer reads an entry's
summary in the PR that adds it, so a lookup costs the same at any size. One
cost of length was real but distant: GitHub renders a Markdown preview for
files that are "generally less than 2 MB", and the proposal put the log there
between February and June 2027. It was 614,641 bytes when it was split.

**The layout (L2).** `docs/decision_log/<year>/<date>-<title>.md`. The
folder's `README.md` holds what the top of the old file held, word for word:
what earns an entry, the rule that a changed decision keeps its old entry, and
the four status values. It adds three lines on naming a new file, and it
holds no list of entries. `docs/decision_log.md` is deleted, with no stub.

- **A folder per year, from the start.** Moving the files later would mean
  rewriting every link a second time. The log gains about 360 entries a year.
  GitHub's documentation recommends at most 3,000 entries in one directory,
  and users report that the web listing of a folder stops at 1,000, which one
  flat folder would reach in early 2029.
- **The folder keeps the log's name.** It is `decision_log`, not the more
  usual `decisions`. The docs, the specs, and the code comments all say "the
  decision log" and "a decision-log entry". With this name both stay true, and
  a decision-log entry is one file.
- **An existing entry's file is named by its old heading's anchor.** The
  anchor is what every existing link already carried, so the rewrite was one
  rule with no table: `decision_log.md#<anchor>` became
  `decision_log/2026/<anchor>.md`. All 133 anchors were distinct and plain
  ASCII, and the longest file name is 97 characters.
- **A new entry** is named `<date>-<title in lowercase with hyphens>.md` and
  sits in the folder of its year. The author may shorten the title part.
- **Only the date is gated.** A test requires the date that opens a file's
  name to equal the date in its heading, and the folder to be that date's
  year. A file listing sorted by name is the chronology and nothing else
  keeps it, so the date is the one property a wrong name would break.
- **Order within one day carries no meaning.** At the split 33 days held more
  than one entry, and one day held nine. Files from the same day sort by
  title.

**What an entry file holds.** The old entry, word for word. Its `##` heading
became the file's `#` heading, date included, and the one deeper heading in
the log moved up a level with it. Joining the 133 files in the old order, with
each heading moved back down a level, reproduces the old file byte for byte.

**What changed inside the entries.** Link targets, and twelve sentences.

- A link from one entry to another, `#<anchor>`, became `<anchor>.md`. An
  entry that links one in another year writes `../<year>/<name>.md`.
- A link from an entry to another doc took `../../` in front.
- Twelve sentences pointed at another entry by where it sat in the file: "the
  entry above", "the six below", "previous entry". Position means nothing once
  each entry is a file, so each now links the entry it means. The one inside a
  layer-1 summary names its entry in words, because a summary carries no link.
  The proposal counted six, from a search for "the entry above" and "the entry
  below". A wider search at the split found twelve.
- Nothing else. An entry that says `decision_log.md` in a sentence is a
  record of its day and stays as written.

**Links from other files.** A link to a heading of the log became a link to
that entry's file, and a link to the log as a whole became a link to the
folder's README. A relative prefix did not change, because the folder sits
where the file sat. At the split that was 497 links to an entry, in 19 files,
and 15 to the log as a whole. Another 28 links had the old file's name as
their text, and took the folder's name or the words "decision log".

**Three sentences changed meaning, and none was reversed.**

- The log "stays the chronological change history": the folder is that
  history.
- A shipping PR distills a proposal "into `docs/decision_log.md`": into a new
  file in the folder.
- A spec links the entry that governs a statement "by heading anchor": by
  file. That clause is in the
  [2026-08-22 spec-layer entry](2026-08-22-the-capability-spec-layer-is-written-in-one-pass.md),
  whose `Status:` line now says so.

**The rejection of a topic index stands.** The
[2026-08-01 doc-style entry](2026-08-01-doc-style-follow-up--decisions-needed-roadmap-trim-no-log-index.md)
rejected one, and the README holds no list of entries. A folder listing is
not an index anyone maintains, and the specs remain how a reader finds the
decision behind a behavior.

**The code comments, and one release (L3).** Eleven comment and docstring
lines, in nine files under `source/` and `assets/`, named the old path. The
split corrected them in the same PR. Each took `docs/decision_log/` and kept
the words that say which entry it means, and the two that named no entry
gained its date. The release job publishes a version when a changed path can
affect an installed copy, and a Python or JavaScript file can even when only
a comment changed. So merging the split published one release whose only
change is comments. That was accepted: a release is routine here, leaving the
lines for later had no owner, and the lines would have been published either
way. Eleven other comment lines name the log or an entry with no path, and
were not touched.

**History.** `git log --follow` cannot trace one file into 133. An entry
file's history starts at the split, and the earlier history of any entry is
read with `git log -- docs/decision_log.md`.

**A PR open across the split.** It merges only after it has synced with
`main` and passed the gates again. A branch that added an entry to the old
file conflicts on it, deleted on one side and edited on the other, and its
author moves the entry into its own file. A branch that only added links in
the old form merges cleanly, and its links dangle until they are converted.
`main` does not require an up-to-date branch, so without the sync GitHub
would merge on a check that passed before the split. No other PR was open
when the split PR opened.

**What the tests hold.** The placement test exempts the folder, as it exempts
the proposals and specs folders, because every entry carries a `Status:` line
and one has "proposal" in its file name. The summary test reads each entry
file where it read each `##` section, with the same cutover date and the same
one named exemption. The date test is new. The two link tests did not change:
they already walked every Markdown file under `docs/`.

**Seven links on GitHub died.** By the consult's count, six in five merged PR
descriptions and one in a review comment pointed at a heading of the log on
`main`. They are not repaired.

**Alternatives rejected.**

- **Leave the file as it was.** The collisions continue wherever two shipping
  PRs are in review together, and the size question returns in 2027.
- **Ship one PR at a time.** It stops the collisions with no split. It is a
  change to how the maintainer runs parallel sessions, not to the docs.
- **Wait until the file nears 1.5 MB.** A certain one-time cost now, against
  a cost per collision of one trivial hunk. Set aside because waiting makes
  nothing cheaper: the link count only rises, and the collisions continue.
- **A `merge=union` attribute on the file.** It never reports a conflict, so
  two branches that edit the same old lines would silently keep both
  versions, and old entries do get edited. The consult found reports from
  2016 to 2018 that GitHub's own merge check ignores the attribute, which
  nobody tested here. It does nothing about the size ceiling.
- **A few large files, by quarter or by year.** New entries still collide at
  the top of the current file.
- **Files by topic.** A cross-cutting decision has no single home, and the
  specs already map topic to entry.
- **One flat folder.** Simpler to browse today, and a second link rewrite
  when it fills.
- **A folder named `decisions`.** Every sentence that says "the decision log"
  then points at a folder called something else.
- **Trimming or summarizing old entries, or a limit on entry length.** No
  reader loads the whole log, some of the detail cannot be regenerated, and
  once each entry is a file its length costs one reader at a time.
- **Month folders, an index file, or renaming superseded entries.** The first
  adds clicks for about 30 files, the second is the index already rejected,
  and the third breaks links that the `Status:` line makes unnecessary.
- **Leaving the code comments for a later PR.** The split would then publish
  nothing, and eleven lines on `main` would name a file that does not exist
  until some later PR edited nine files it had no other reason to touch.

**Out of scope.**

- How long an entry is, and what earns one. An entry's length follows its
  proposal's length, so the place to shorten entries is the proposal
  template.
- Whether every entry clears the bar for a durable decision. Nobody has
  audited all of them.
- The other files that shipping PRs collide in. The roadmap, the
  architecture doc, and the specs conflicted in 7 of the 34 replayed merges.
- The maintainer's global skills, which name the old file on two lines each
  and still read correctly as the log's name.
