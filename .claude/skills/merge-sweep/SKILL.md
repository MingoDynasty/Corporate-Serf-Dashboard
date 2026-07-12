---
name: merge-sweep
description: Reconcile the local ignore/ doc queues with merged PRs — archive review handoffs and consumed kickoff prompts to done/, and audit recent merges for missed "Shipping a proposal" checklist steps. Use after PRs merge, on a schedule, or whenever the live queues look stale.
---

# Merge sweep

Reconciles the local scratch queues in `ignore/` against merged/closed PRs,
then audits recent merges for missed doc-cleanup steps. Idempotent — safe to
run at any time, including when nothing has merged.

## Setup

`ignore/` is untracked and exists only in the MAIN checkout. All file moves
happen there, never in a worktree. Resolve the path first and use it
absolutely throughout:

```
git worktree list   # first entry is the main checkout
```

`ignore/README.md` is tracked, so `ignore/` itself exists in every checkout —
its presence proves nothing. The untracked queue dirs are the real check:
if `ignore/pr-reviews/` and `ignore/prompts/` are not both present at the
main-checkout path (e.g. a cloud session), stop and report that the sweep
must run on the local machine — do not report empty queues.

## 1. Archive merged review handoffs

For each `ignore/pr-reviews/pr<N>-review.md` in the live queue (not in
`done/`): check `gh pr view <N> --json state`. If the state is MERGED or
CLOSED, move the file to `ignore/pr-reviews/done/`. These files are
untracked — move, never delete.

Review docs without a PR number in the name (proposal reviews): read the doc
and archive it only when the proposal it reviews has shipped or been
abandoned; otherwise leave it in the live queue.

## 2. Archive consumed kickoff prompts

For each `ignore/prompts/*.md` in the live queue (not in `done/`), find the
PR that consumed it: match the prompt's filename, title, and content against
merged-PR branch names and titles
(`gh pr list --state merged --limit 30 --json number,title,headRefName`;
raise the limit or use `gh pr list --search` for older prompts). Matching is
judgment, not string equality — e.g.
`flaky-importer-test-investigation-prompt.md` was consumed by branch
`claude/flaky-importer-test-f50f68`.

- Consumed by a MERGED PR → move to `ignore/prompts/done/`.
- Matched only an OPEN PR, or no PR yet → leave in the live queue.
- Ambiguous → leave it and flag it in the report rather than guessing.

## 3. Audit recent merges for missed checklist steps

For PRs merged since the last sweep (default: the last 7 days), where the PR
shipped or finished shipping a proposal, verify the "Shipping a proposal"
definition of done in AGENTS.md actually happened: proposal file deleted,
`docs/decision_log.md` entry added, `docs/roadmap.md` milestone moved to
Shipped, `docs/product.md` inventory updated, fixed `docs/tech_debt.md`
entries removed, and no stale references to the deleted proposal file remain
(`rg` the filename across the repo — CI's `test_docs.py` only catches
dangling Markdown links, not plain-text or source references).

Report gaps — do NOT fix tracked docs from the sweep. Doc fixes on main
belong in a PR (ideally the shipping PR; a small follow-up docs PR when
missed).

## 4. Report

End with:

- Files moved (from → to), with the PR that justified each move.
- The live queues after the sweep: reviews still in flight, prompts still
  ready to start.
- Any checklist gaps or ambiguous prompts that need a human decision.
