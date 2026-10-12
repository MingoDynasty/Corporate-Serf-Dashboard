# Decision Log

Durable project decisions that future contributors and agents should preserve unless a newer entry supersedes them.

Use this log for decisions that are hard to reverse, cross-cutting, based on external API behavior, or likely to be questioned later. Do not record every small implementation choice.

When a decision changes, keep the old entry and mark it `Superseded`. Add a new entry explaining what changed, why, and any migration notes.

## Status Values

- `Proposed`: under consideration, not yet agreed.
- `Accepted`: current agreed decision.
- `Superseded`: replaced by a newer decision.
- `Rejected`: considered and intentionally not chosen.

## New Entries

- Each decision is one file: `<year>/<date>-<title in lowercase with hyphens>.md`, such as `2026/2026-10-11-a-session-ends-after-a-break-of-more-than-30-minutes.md`. The title part may be shortened.
- The file opens with a `# <date>: <Title>` heading, then its `Status:` line. The date in the file's name must equal the date in the heading, and the folder must be that date's year. `tests/test_docs.py` holds both.
- A file listing sorted by name is the chronology. Order within one day carries no meaning, and nothing lists the entries.
