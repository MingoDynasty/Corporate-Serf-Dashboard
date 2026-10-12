# 2026-08-01: Durable Docs Open Plain And Proposals Lead With Decisions

Status: Superseded — replaced by
[the follow-up entry](2026-08-01-doc-style-follow-up--decisions-needed-roadmap-trim-no-log-index.md)
(section rename; all other rules carried forward there in full)

Docs now serve their two readers in layers instead of forcing one register
on both. Every new decision-log entry opens with a short plain-language
summary, like this paragraph, before the dense detail. Proposals open with
a summary and a filtered list of the decisions that genuinely need the
maintainer, and the docs test enforces that order. The dense record itself
is unchanged.

Decision: durable docs are layered. Layer 1 (maintainer): every new or
materially-edited `decision_log.md` entry — and every `docs/specs/` file,
once that layer exists — opens with a 2–4 sentence plain-language summary
(one idea per sentence; no cross-references, file paths, or embedded
enumerations). Layer 2 (agents): the dense payload follows, written as
before — compression there is a feature, not a bug. The summary is
written, updated, and reviewed in the same PR as its payload, by the same
author. No backfill: existing entries convert only when a change touches
them anyway.

Proposals follow the template in `AGENTS.md` ("Proposal template"):
`Status:` → `## TL;DR` → `## Decision points` → `## Problem`, dense body
per-proposal after that (Design is the normal next section but may be
replaced by more specific ones). Decision points carry only choices
requiring maintainer product or workflow judgment, or acceptance of a
costly-to-reverse trade-off, each with a recommended answer and the
material consequence of choosing differently; the author owns mechanical,
reversible, and evidence-resolvable choices. `tests/test_docs.py` enforces
the leading section order mechanically (placement, not just presence);
prose quality is held by same-PR authorship and review, not tests.
`docs/product.md` is exempt — its *Problem solved:* format already leads
with the user-facing statement.

Why: the docs pipeline optimizes for agent readers — distillation is
compression — while the maintainer, now primarily a reader and decider
with agents doing most implementation, pays the skim cost. Layering serves
both without compromising either, and the decision filter attacks the
number of escalations put in front of the maintainer, not just their
discoverability.

Provenance: distilled from `docs/doc_style_proposal.md` (two same-day
external review rounds), committed and then deleted in the shipping PR —
git history holds the full text.
