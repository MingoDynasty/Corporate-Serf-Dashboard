# Decision Log

Durable project decisions that future contributors and agents should preserve unless a newer entry supersedes them.

Use this log for decisions that are hard to reverse, cross-cutting, based on external API behavior, or likely to be questioned later. Do not record every small implementation choice.

When a decision changes, keep the old entry and mark it `Superseded`. Add a new entry explaining what changed, why, and any migration notes.

An entry that a later decision supersedes, in whole or in part, keeps its opening summary exactly as it was: the summary says what that entry decided on its date. Record the change on the old entry instead. Its `Status:` line names the new entry, and for a partial change a dated note after the summary (`**Superseded in part (<date>).**`) says what the new entry replaces and what still stands. The current behavior goes in the new entry and in the capability spec. Rewriting the old summary to describe the app as it is now makes the entry contradict its own payload and loses the record of what it decided. AGENTS.md's rule that a payload change which leaves the summary untouched should make the reviewer ask which layer is wrong does not apply to these notes: a supersession note records a later change and leaves what the entry decided as it was.

## Status Values

- `Proposed`: under consideration, not yet agreed.
- `Accepted`: current agreed decision.
- `Superseded`: replaced by a newer decision.
- `Rejected`: considered and intentionally not chosen.

## New Entries

- Each decision is one file: `<year>/<date>-<title in lowercase with hyphens>.md`, such as `2026/2026-10-11-a-session-ends-after-a-break-of-more-than-30-minutes.md`. The title part may be shortened.
- The file opens with a `# <date>: <Title>` heading, then its `Status:` line. The date in the file's name must equal the date in the heading, and the folder must be that date's year. `tests/test_docs.py` holds both.
- A file listing sorted by name is the chronology. Order within one day carries no meaning, and nothing lists the entries.
