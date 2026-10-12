# 2026-09-28: No Backfill Covers Missing Summaries, Not Broken Ones

Status: Accepted

The no-backfill rule now tells apart an entry with no summary and a summary
that breaks the rules. An entry written before the two-layer style still gains
its summary only when a payload change edits it anyway, never in a PR of its
own. A summary that breaks the rules is a defect, fixed as its own commit in a
PR that edits the file anyway or in a docs-only PR the maintainer asked for.
The old wording read as a bar on every standalone fix, so a known violation
waited on unrelated work.

**Ruling.** Ruled (user) 2026-09-28, in chat, accepting the recommended
wording over two alternatives. Relief only would invite unrequested
summary-only churn across the 55 entries dated before 2026-08-01. A bar leaves
a known violation waiting until an unrelated payload change happens to land,
then pushes the cleanup into that PR's diff against the rule that a drive-by
fix never shares a commit with the requested change.

**Two populations.**

- Legacy: an entry that predates the two-layer rule and has no summary. It
  gains one only when a payload change edits it anyway, never in a
  summary-only PR. This is the relief the original proposal meant by "The 54
  existing entries stay as they are" (`6d4eecf`).
- Broken: a summary that exists but breaks the layer-1 rules, such as one over
  the 2–4 sentence cap or one carrying a cross-reference, a path, or an
  enumeration. It is a defect, not legacy. It is brought into line as its own
  commit, in a PR that edits the file anyway or in a docs-only PR the
  maintainer asked for. An unrequested summary-only PR is still the backfill
  the rule refuses.
- "Payload change" closes the circular reading in which a summary edit is
  itself the change that licenses the summary edit.

**History.** The previous bullet read "existing entries are converted only
when a change touches them anyway".
[#267](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/267), a
standalone condensation of the notifications spec summary that the maintainer
asked for, drew a connector P1 that read "only when" as a necessary condition,
so a summary-only edit was the backfill the rule forbade. The implementer
contested that the clause was relief from a duty, not a bar. #267 closed
unmerged when #268, a real payload edit to the same spec, carried the same four
sentences. That settled the instance and left the wording open until this
ruling.

**Main already practised the split.** These merged summary fixes each rode
as their own commit, touching only the summary, in a PR that edited the file:
`e9e1aa2` and `a321393` (#302), `baa2296` (#307), and `8885cd0` (#319).

**Scope.** This supersedes in part the
[2026-08-01 Doc-Style Follow-Up entry](#2026-08-01-doc-style-follow-up--decisions-needed-roadmap-trim-no-log-index),
for its no-backfill sentence only. The earlier 2026-08-01 "Durable Docs Open
Plain" entry restates the same clause but was already superseded in full, so
it is left alone. The sibling no-backfill clauses in `AGENTS.md`, the Comment
and Docstring Conventions intro and the Copy paragraph's "same no-backfill
convention", need no edit: both spare existing items a sweep without barring a
fix.
