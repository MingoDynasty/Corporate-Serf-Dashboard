# 2026-09-04: Comment And Docstring Conventions

Status: Accepted

The application code carries a lot of explanatory prose, and nearly all of it
is the useful kind, but the rules that shaped it were never written down. A
fresh session had to learn the house style by imitation, and the two places it
tended to go wrong were narrating what code already says and writing a comment
as a reply to whoever asked in review. The agent instructions now state what
earns a comment, what stays beside the code when fuller rationale also lives
elsewhere, and the shape a docstring takes. The enforced lint and type gates
do not change.

**What was measured (2026-09-04, 44 files under `source/`; later additions
dated).** Comment-only lines are 12% of code lines and docstring lines 23%;
the test tree sits at 4% and 6%. Of 385 comment blocks, 58 run five lines or
more and 12 run eight or more. Nearly every definition has a docstring; 352
open in the imperative against 9 in the third person, and none carries an
Args/Returns/Raises section. Identifier spans in docstrings and comments run
383 double-backtick against 32 single (2026-09-08). `X | None` appears 217
times against one `Optional[]`. 42 of 47 `# noqa` markers give no reason, and
of the 14 blind-except suppressions 4 name what the catch protects
(2026-09-08). Narration is confined to the oldest modules: 17 label-style and
36 trailing comments in the whole tree, plus four legacy TODOs in
`kovaaks/data_service.py`, none of which names a concrete problem. Fifteen of
1143 non-merge commits exist only to correct a stale comment or docstring.

**Why a written bar rather than a trim.** The volume sits in the newest code
and is rationale, not narration, so removing narration barely moves it. Nearly
every measured dimension shows a style the code already follows: no
Args/Returns/Raises sections, imperative summaries, double-backtick
identifiers at better than nine spans in ten, one `Optional[]` in the tree.
That style existed only as a pattern to imitate, in a repository where most
edits come from fresh agent sessions, and AGENTS.md is the only channel that
reaches a session on every edit. The case for the section is transmission: it
writes down what is already there so a new session does not default to
Google-style sections or narrating comments. One cost does recur and has a
number: comments go stale, a few because they cite a relative position, a
count of things in the tree, or a neighbor's name and the neighbor moves, and
more often because the behavior they describe changed. The fifteen repair
commits above are that cost, and the rule addresses both halves. A second is
first-hand rather than measured: from the sessions that wrote this code,
comments authored as the answer to a review question that then outlive the
thread. On placement the rule keeps the failure-preventing reason beside the
code and moves only evidence and history up, into a document whose scope
already fits, so a bare pointer never stands where the constraint was and this
log is not widened into a store of library detail; length alone is never the
trigger. The three comments in `source/` that point at this log already do
exactly this. The two hygiene rules are new rather than transcribed: a reason
on suppressions the rule code does not explain is already the norm, but a
blind-except suppression that names what the catch protects is four of
fourteen, and none of the four legacy TODOs names a concrete problem; both
ride on the same no-sweep scope as the rest. The section sits beside the
2026-08-01 two-layer doc-style entry as the code-side counterpart: that one
governs prose in the docs, this one governs prose in the code.

**What is deliberately not enforced.** No lint rule judges comment quality.
Ruff's `pydocstyle` `pep257` convention would check only part of the docstring
shape (summary placement, the blank line after it, mood, terminal period): 39
findings on 2026-09-08 under the locked ruff, none safely auto-fixable, and it
does not see Args/Returns/Raises sections, single-backtick identifiers, or a
summary that starts below the opening quotes. Deferred, and not a substitute
for the written rule. Annotations are not required: under mypy's
`disallow_untyped_defs`, 59 diagnostics across 56 definitions in 12 files
(2026-09-08, after `check_untyped_defs` landed), 39 of them Dash callbacks and
page layouts whose parameters are whatever Dash passes and 17 ordinary
functions. The options are nothing, annotating the seventeen, or a sweep plus
the mypy flag; a prose rule no gate checks was rejected because it would
drift. The `N` naming family stays off: its 35 hits are API models mirroring
KovaaK's field names. The 2026-07-03 ruff consolidation entry is unchanged.

**No sweep.** Existing comments are not rewritten to match. The rule governs
new and edited comments, the same no-backfill convention the layer-1 summaries
follow. The legacy TODOs and label comments in the oldest modules are a
separate drive-by when someone is in those files anyway.
