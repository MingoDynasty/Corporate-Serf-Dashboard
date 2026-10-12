# 2026-08-22: The Capability Spec Layer Is Written In One Pass

Status: Accepted (amended by
[2026-10-12](2026-10-12-each-decision-is-its-own-file-in-a-folder-per-year.md):
a spec links the entry that governs a statement by its file, because an
entry is now a file and no longer a heading of one log)

Every shipped capability with a durable behavior contract must have a spec
that states what the app does today, and the four still missing are being
written in one deliberate pass instead of waiting for a change to touch each
capability. A new capability brings its spec in the PR that ships it, and a
change to specified behavior updates the spec in the same PR. The specs are
how a reader finds the decision behind a behavior, so the log still keeps no
topic index.

Decision: the "do not backfill specs ahead of need" rule in `AGENTS.md` is
replaced by a standing criterion — **every shipped capability with a durable
behavior contract must have a spec under `docs/specs/`**. A new capability
gets its spec in the shipping PR; a PR that changes specified behavior
updates the spec in the same PR (the "Shipping a proposal" checklist's step 2
now says the same thing). The criterion is a requirement, not a description
of the tree: when this entry landed the directory held two specs, and the
four the pass names below are in flight as their own PRs, so the layer is
complete only once those merge. The `AGENTS.md` "Scenario Rank Feature"
pointer becomes a
"Capability Specs" section pointing at the directory, which lists itself, so
no per-spec list is touched by every spec PR; `architecture.md`'s "Where to
look first" table carries the same pointer.

The pass: five specs, five PRs, each authored by a Fable session and reviewed
by a fresh Fable session plus Codex, in dependency order —

- `notifications.md` (PR #249; also carries this entry and the rule change),
- `settings.md` (after notifications: its in-place statuses cite the routing
  policy),
- `scenario_performance.md` (after settings: the Chart options switches'
  gating semantics live in the notifications spec, their placement and
  persistence here),
- `playlists.md` and `release_and_install.md`, independent of the others and
  of each other.

Deliberately excluded: app copy, which the app messaging consistency
proposal (PR #247) leaves out of the spec layer; bug-report intake,
which one decision-log entry covers in full; Home as a standalone capability,
folded into `scenario_performance.md`; and tooling and process, for which
`AGENTS.md` is the spec.

The spec contract, which every file in the pass follows and later specs
inherit:

- Statement form, present tense, no rationale. Each statement links the
  decision-log entry that governs it by heading anchor; a statement with no
  governing entry is an implementation fact, stays unlinked, and is covered
  by the preamble's disclaimer — no entry is invented for it.
- Verified against code or a test before it is written, never transcribed
  from the log. The PR body carries the evidence map; the spec does not.
- Where code contradicts an entry, the spec states what the code does and
  the PR body lists the contradiction as a finding for the maintainer. No
  code changes ride in a spec PR.
- Supersession is cited as current: the governing entry, or the surviving
  clause "as amended by" the amending entry; a superseded clause is never
  cited as current.
- Opens with a layer-1 summary held to the 2–4 sentence budget, then H2
  sections. No `Status:` line; anchors as GitHub slugs them
  (`tests/test_docs.py` validates both).
- App strings are quoted exactly as the code has them, shipped em dashes
  included. Specs link `architecture.md` and `product.md` rather than
  restating them, and link another spec only to say a rule lives there.

Consequences: the
[2026-08-01 doc-style follow-up entry](2026-08-01-doc-style-follow-up--decisions-needed-roadmap-trim-no-log-index.md)'s
"revisit a log index only if findability still hurts after specs land"
loop closes when the pass's last PR merges — the specs are the findability
fix, and a topic index stays rejected; until then the loop is open only in
the sense that the fix is still landing. `docs/product.md` and
`docs/roadmap.md` are untouched: nothing user-facing changes.
