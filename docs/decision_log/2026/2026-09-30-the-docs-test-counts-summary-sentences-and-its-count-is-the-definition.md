# 2026-09-30: The Docs Test Counts Summary Sentences, And Its Count Is The Definition

Status: Accepted

The docs test now fails when a capability spec or a recent decision-log entry
opens with a summary outside two to four sentences. The test's own count is
what a sentence is, so a summary it miscounts is fixed by rephrasing, not by
arguing with the counter. It judges nothing else about the prose, and review
still holds every other summary rule. The cap kept coming back as a review
finding, and the earlier settlement that kept prose out of the test was about
Markdown rendering, never about counting.

**Ruling.** Ruled (user) 2026-09-28, in chat, accepting the recommendation
(D2), alongside the no-backfill wording (D1) and a two-PR sequence (D3). The
wording shipped first in
[#325](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/325), so
the two summary fixes below ride under its broken-summary clause.

**Scope.** Every `docs/specs/*.md`, whose summary is the first
blank-line-delimited paragraph after the H1. Every entry in this log whose
heading date is 2026-08-01 or later, whose summary is the first paragraph after
the whole `Status:` paragraph: a Status line wraps when it carries a
supersession note, and the first measuring counter, which stopped at its first
line, misread five entries that way. A supersession note therefore belongs
inside the Status paragraph or after the summary. Proposal TL;DRs,
`docs/product.md`, and the roadmap are not gated, and entries dated before
2026-08-01 predate the two-layer rule.

**One exemption, by name.** "2026-08-01: No Username Stays Fully Offline —
User-Independent Totals Rejected" carries the cutover date but opens with the
old `Decision:` shape: its commit `22ea0f8` (02:53 -0700) predates the rule's
commit `a0c5044` (10:06 -0700) the same day. It is named rather than matched by
shape, so a `Decision:` opener can't become a way around the gate, and a test
fails if the name stops matching a real entry.

**The count is the definition.** `count_sentences` in `tests/test_docs.py`
blanks code spans, keeps link text, drops the dots of e.g., i.e., vs., etc.,
cf., approx., decimals, and versions, and ends a sentence at terminal
punctuation, plus any closing quote, bracket, or star, followed by whitespace
and a capital, quote, backtick, star, or bracket. A fixture pins each shape.
The count is a floor: a sentence that opens with a digit or a lowercase word
doesn't split from the one before it. Review still holds the cap and the other
layer-1 rules: one idea per sentence, and no cross-references, paths, or
enumerations.

**Why this doesn't reopen #174.** The 2026-08-01 settlement that the test
"never judges prose quality or Markdown rendering fidelity" came from reviewers
escalating the section-order test into rendering edge cases, such as headings
inside an HTML comment opened mid-line or inside `<template>`. Rendering has an
external truth, what GitHub shows, so each new edge case was a real mismatch
and review could always find another. Sentence segmentation has none to
chase: the counter's output is the definition, so a disputed count closes by
rephrasing, and the regions are cut from the source text for the same reason.
Nobody evaluated a counter in #174. The cap itself recurred as a review finding
in #267, #268, and #275.

**The README word-count rejection stands.** The 2026-09-22 README entry
rejected a word-count gate because it "would fail unrelated PRs on an editorial
threshold". A README length is a line any feature PR can cross; the summary cap
is a ratified per-summary rule that only a PR editing that summary can break.
That entry's second reason, that the test "gates structure, never prose", is
narrowed by this one to everything but the summary count.

**Violations fixed first.** The gate found two summaries outside the cap on
main: `docs/specs/scenario_rank.md` at five sentences and the 2026-08-11
schema_version entry at six. Each was condensed in its own commit ahead of the
gate, nothing moved out of either payload, and every statement cut from a
summary was already in its payload. Those were the only two summaries flagged
across 6 specs and 58 entries.

**Supersedes in part** the 2026-08-01 Doc-Style Follow-Up entry's claim that
the test never judges prose, for the summary sentence count only, and amends
the 2026-09-22 README entry's "gates structure, never prose" reason the same
way. Both keep one Status paragraph.
