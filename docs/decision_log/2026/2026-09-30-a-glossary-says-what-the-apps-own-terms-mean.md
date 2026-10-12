# 2026-09-30: A Glossary Says What The App's Own Terms Mean

Status: Accepted

The words the app uses for its own concepts now have one glossary that says
what each means. Their definitions were scattered across the repo, and code
names already disagreed with the words on screen. Each entry gives a term's
meaning, then its code name and its on-screen wording where those differ. A
term joins only once the app or the product doc has its concept, and a change
that makes an entry untrue corrects it in the same PR.

**Settled before the PR.** The maintainer settled two points on 2026-09-28, in
the kickoff for this work. The file is `docs/glossary.md`, titled Glossary:
*vocabulary* is already copy rule 7's word, and *terminology* names the
subject rather than the document. It holds shipped terms only, meaning the
app or `docs/product.md` already has the concept. The draft terms from the
product brainstorm, such as visit, warm-up run, and typical score, stay leans
until the proposal that ships them.

**Ruling.** Ruled (user) 2026-09-30, in chat, after both reviewers endorsed
each row: D1, D2, and D3 as recommended, then D4 as amended in review, with
four hooks.

**D1, an entry's scope.** The meaning, plus the code name and the on-screen
wording where they differ from the term: Position is `rank_*` in code, Rank
is `tier_*`, and PB is `high_score`. Meaning alone would leave out exactly the
mismatches that send a reader to the wrong field. An entry states the meaning
and links the spec for mechanics. KovaaK's own terms appear only inside the
entries for the app's terms, as Unranked and share code do. Challenge and
freeplay have no entries: no code or current doc defines either, and
*Challenge* appears only as a separator token in stats file names.

**D2, how terms arrive.** A proposal gathers the terms it adds or redefines in
a **Terms** block in Design, as it gathers strings in a Copy block, and the PR
that ships it moves the block into the glossary. A proposal opened before the
rule keeps its terms where they are, the Copy block's no-backfill convention;
its shipping PR still updates the glossary under D4's same-PR duty.

**D3, relation to the existing definitions.** The glossary holds meanings, and
AGENTS.md copy rule 7 keeps its on-screen wording rules; each links to the
other. The
[2026-07-03 importer entry](#2026-07-03-import-benchmarks-from-evxl-and-kovaaks)
(playlist and benchmark) and the
[2026-07-06 verbiage entry](#2026-07-06-one-word-per-concept-in-leaderboard-verbiage)
(Rank, Position, and PB) keep their definitions as history, unedited, and the
glossary links them. Folding rule 7's vocabulary line into the glossary was
rejected: it would take a wording rule out of the copy rules that copy review
reads.

**D4, hooks.** Four hooks, and no test. A Documentation Habits bullet makes
any PR that ships a new term, or makes an entry untrue, update the glossary in
the same PR, whether or not a proposal backs it, as the spec rule already does
for specs. A "Shipping a proposal" step moves a proposal's Terms block in and
corrects any entry the change makes untrue. The Terms block is described
beside the Copy block rule, and the Layout list names the file. The same-PR
duty is what keeps the glossary true: most PRs here ship without a proposal,
and the proposal path alone would let an entry go stale silently. Three hooks
on the proposal path alone were rejected for that reason. No test is
added, because the glossary is prose held by review, and a rename already
surfaces it to anyone who searches for the old name. The shipping step is
step 3, between the spec update and the deletion of the proposal file,
because the block has to move before the file goes. The steps after it move
down one, so the "Steps 4 and 5" of the
[2026-09-22 README entry](#2026-09-22-the-readme-is-a-front-door-and-user-reference-lives-in-a-user-guide)
are now steps 5 and 6.
