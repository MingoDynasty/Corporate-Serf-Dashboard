# 2026-08-01: Doc-Style Follow-Up — Decisions Needed, Roadmap Trim, No Log Index

Status: Superseded in part by the
[2026-09-28 no-backfill entry](2026-09-28-no-backfill-covers-missing-summaries-not-broken-ones.md):
the sentence "No backfill: existing entries convert only when a change touches
them anyway" no longer holds. An entry with no summary still waits for a
payload edit, but a summary that breaks the rules is a defect, fixed on its
own commit. Superseded in part also by the
[2026-09-30 sentence-count entry](2026-09-30-the-docs-test-counts-summary-sentences-and-its-count-is-the-definition.md):
the test now gates the summary sentence count, as it counts them, so "the test
never judges prose quality" no longer holds for that count. The PR #174
settlement still holds for Markdown rendering fidelity. Everything else here
stands.

The proposal section listing what the maintainer must rule on is renamed
from "Decision points" to "Decisions needed", so the heading itself tells
you whether a document wants your attention. This entry now carries the
complete doc-style rules and replaces the original entry, "Durable Docs
Open Plain And Proposals Lead With Decisions". The
roadmap keeps only the few most recently shipped milestones instead of a
full history. A topic index for this log was considered and rejected.

Decision — the complete two-layer doc style (supersedes
[the original entry](2026-08-01-durable-docs-open-plain-and-proposals-lead-with-decisions.md);
the only rule change is the section rename, everything else carries
forward unchanged):

- Durable docs are layered. Layer 1 (maintainer): every new or
  materially-edited `decision_log.md` entry — and every `docs/specs/`
  file, once that layer exists — opens with a 2–4 sentence
  plain-language summary (one idea per sentence; no cross-references,
  file paths, or embedded enumerations). Layer 2 (agents): the dense
  payload follows, written as before — compression there is a feature.
  The summary is written, updated, and reviewed in the same PR as its
  payload, by the same author. No backfill: existing entries convert
  only when a change touches them anyway.
- Proposals follow the template in `AGENTS.md` ("Proposal template"):
  `Status:` → `## TL;DR` → `## Decisions needed` → `## Problem`, dense
  body per-proposal after that (Design is the normal next section but
  may be replaced by more specific ones). Renaming "TL;DR" to "Summary"
  was considered and deliberately not done.
- Decisions needed carries only choices requiring maintainer product or
  workflow judgment, or acceptance of a costly-to-reverse trade-off,
  each with a recommended answer and the material consequence of
  choosing differently; the author owns mechanical, reversible, and
  evidence-resolvable choices.
- `tests/test_docs.py` enforces the leading section order mechanically
  (placement, not just presence). The layer-1 prose rules are writing
  guidance held by same-PR review — the test never judges prose quality
  or Markdown rendering fidelity (settled across the PR #174 review
  rounds).
- `docs/product.md` is exempt — its *Problem solved:* format already
  leads with the user-facing statement.

Why (unchanged from the superseded entry): the docs pipeline optimizes
for agent readers — distillation is compression — while the maintainer,
now primarily a reader and decider with agents doing most
implementation, pays the skim cost. Layering serves both without
compromising either, and the decision filter attacks the number of
escalations put in front of the maintainer, not just their
discoverability.

Roadmap policy: the Shipped section keeps only the ~5 most recent
milestones, newest first, and older entries leave the file entirely —
the shipping checklist already lands their user-facing rationale in
`product.md` and their technical rationale here, and git history holds
the full sequence.

Rejected: a topic index at the top of this log (reviewer suggestion once
the log passed ~1,500 lines). The planned `docs/specs/` capability layer
links the relevant log entries per capability and is the intended
findability fix; a hand-maintained index would duplicate it as a third
structure, touched in every shipping PR and verified by nothing. Revisit
only if findability still hurts after capability specs land.

Provenance: the two-layer rules were established via
`docs/doc_style_proposal.md` (PR #174; two external review rounds;
proposal deleted per "Shipping a proposal" — git history holds the full
text). This entry restates them in full with the post-merge follow-up
refinements (external reviewer suggestions, maintainer-ratified scope:
rename yes, "TL;DR" kept, trim yes, index no) and supersedes the
[original entry](2026-08-01-durable-docs-open-plain-and-proposals-lead-with-decisions.md).
