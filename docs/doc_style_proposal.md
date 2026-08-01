# Doc Style: Two Readers, Two Layers

Status: Proposed
Date: 2026-08-01 (revised same day across two Codex review rounds)

## TL;DR

Our durable docs are written by agents and optimized for agents, so they
read like legal documents. The maintainer is now the main reader: most
maintainer time goes to reading docs, while agents do most of the
implementing. This proposal adds style rules so decision-log entries,
proposals, and future capability specs open with a short plain-language
summary before the dense detail, and every proposal leads with the few
decisions that genuinely need the maintainer. No dense detail is removed;
the record gains a plain opening layer and a fixed, filtered place for
decisions.

## Decision points

- **Mechanical enforcement.** Proposed: extend `tests/test_docs.py` to
  require `## TL;DR`, `## Decision points`, and `## Problem` as the first
  three sections of a proposal, in that order — placement, not just
  presence, same mechanical shape as the existing `Status:` check.
  Alternative: convention only.
- **product.md applicability.** Proposed: the layer rule applies to
  `decision_log.md` entries, proposals, and future `docs/specs/` files;
  `product.md` keeps its existing *Problem solved:* format, which already
  leads with the user-facing statement.

## Problem

The docs are dense because the pipeline that produces them optimizes for
density. "Shipping a proposal" step 1 says *distill* — and distillation is
compression. Agents write entries where every sentence is load-bearing,
because each entry is written to survive being the only thing a future
agent reads. The result is prose like this, from the 2026-07-19 release
entry:

> a redundant release is only noise, while a missed release strands
> distribution inputs — `install.ps1`, the launcher, `example.toml`,
> `.python-version`, `.gitattributes` — at an older tag.

That is a good sentence for an agent: maximum constraint per token,
embedded enumeration, zero redundancy. It is a bad sentence to skim, and
skimming is what the maintainer does — reviewing, deciding, spot-checking —
across a decision log now past 100 KB and 54 entries. The two readers have
opposite needs, and today the docs serve only one of them.

The same mismatch hits proposals. The maintainer's questions are "what is
this?" and "what do I need to rule on?", but decision points surface
wherever the design narrative happens to raise them — sometimes only in a
tracker note outside the repo. Reading the whole dense body is currently
the only way to be sure nothing needs a ruling.

## Design

Serve both readers by layering, not by compromising in the middle. Layer 1
is for the maintainer; layer 2 is the dense payload agents already write,
unchanged.

### 1. New subsection under "Documentation Habits" in AGENTS.md

Insert after the `docs/decision_log.md` bullet:

```markdown
### Doc style — two readers, two layers

Durable docs have two readers with opposite needs: the maintainer, who
skims to decide, and agents, who want maximum constraint per token. Serve
both by layering:

- **Layer 1 (maintainer).** Every new or materially-edited
  `decision_log.md` entry — and every `docs/specs/` file, once that layer
  exists — opens with a 2–4 sentence plain-language summary: what changed,
  why, and what a user or contributor would notice. One idea per sentence.
  No cross-references, file paths, or embedded enumerations — those belong
  in the payload.
- **Layer 2 (agents).** The dense payload follows: invariants, edge cases,
  enumerations, cross-references. Write it as before — compression is a
  feature here.
- The summary is written and updated in the same PR as its payload, by the
  same author, and reviewed with it. A payload change that leaves the
  summary untouched should make the reviewer ask which layer is wrong.
- No backfill: existing entries are converted only when a change touches
  them anyway.
```

### 2. Replace the proposal bullet in "Documentation Habits"

The current bullet ("Use proposal docs under `docs/` ... at a glance")
becomes:

```markdown
- Use proposal docs under `docs/` for feature design that is in flight or
  planned, following the template below. The maintainer reads `Status:`,
  **TL;DR**, and **Decision points** by default and the dense body on
  demand — so a judgment call buried in the body is a process bug, and so
  is a mechanical choice escalated into Decision points.
  `tests/test_docs.py` enforces the `Status:` line (`Proposed`,
  `In progress`, `Future`, ...) and the leading section order.
```

### 3. Proposal template, appended to "Documentation Habits" in AGENTS.md

The template lives inline rather than in a separate file: one source,
always in agent context. Under the decision filter below this is an
author-owned, reversible choice, so it is stated here rather than
escalated to Decision points.

```markdown
### Proposal template

# <Title>

Status: Proposed
Date: YYYY-MM-DD

## TL;DR

<2–4 plain sentences: the problem and the shape of the fix. Layer-1 rules
apply — no cross-references, no embedded lists.>

## Decision points

<Only choices requiring maintainer product or workflow judgment, or
acceptance of a costly-to-reverse trade-off, each with a recommended
answer and the material consequence of choosing differently. The author owns mechanical,
reversible, and evidence-resolvable choices — do not escalate them here.
Write "None — mechanical." if there are none.>

## Problem

<Dense. Evidence, verified facts, current behavior, why now.>

## Design

<Dense. Behavior, invariants, edge cases, blast radius, alternatives
rejected.>

## Out of scope

<What this deliberately does not do; where deferred work is tracked.>

## Testing

<How the change proves itself: new or updated tests, gates, manual
checks.>

Optional sections (Verified facts, Open questions, Future / optional) slot
in where the existing proposals put them. The first three H2 sections are
fixed and mechanically enforced; the dense body after Problem is
per-proposal — Design is the normal next section, but more specific
sections may replace it.
```

### 4. Amend "Shipping a proposal" step 1

From "Distill the proposal's durable decisions into `docs/decision_log.md`"
to:

```markdown
1. Distill the proposal's durable decisions into `docs/decision_log.md`;
   each new entry opens with its layer-1 summary (see "Doc style — two
   readers, two layers").
```

### 5. Enforcement (per decision point 2, if accepted)

Add a check to `tests/test_docs.py` mirroring
`test_proposal_docs_declare_status`: in every `docs/**/*proposal*.md`, the
first three `##` headings must be `## TL;DR`, `## Decision points`, and
`## Problem`, in that order. Placement matters — a Decision points section
at the bottom of the file defeats the read-path — and the check stays
purely mechanical, with no prose-quality judgment. Grandfathering: the
check lands in the same PR that brings the in-flight proposal up to the
template, so the gate is green at merge.

## Out of scope

- **Backfilling the decision log.** The 54 existing entries stay as they
  are; entries gain summaries only when materially edited (the no-backfill
  rule above).
- **The per-capability `docs/specs/` layer.** Tracked as its own work item
  in the project tracker (Planning, handoff prompt ready). Interplay is
  one-way and additive: spec files created under that work item open with
  a layer-1 summary like any other durable doc. Its handoff prompt needs
  no change — a plain "what this capability does" opener is current-state
  description, not the rationale narrative that prompt excludes.
- **Prose rules for layer 2.** Density in the payload is deliberate; no
  style constraints are added there.

## Testing

- `uv run pytest tests` — the docs test must stay green: this file matches
  `*proposal*.md` and carries its `Status:` line in the first 15 lines.
- If decision point 2 is accepted, the new heading check runs against this
  proposal itself (it complies) and the one other in-flight proposal,
  `run_history_proposal.md`, which gains the two leading sections in the
  same PR. Its Decision points will honestly read "None now — Status is
  Future and the open questions are deferred to build time," which is
  exactly the ten-line stop this style exists to enable.
- Not mechanically testable: whether summaries stay plain. That is held by
  the same-PR authorship rule and review, the same way "do not log every
  small implementation choice" is held today.
