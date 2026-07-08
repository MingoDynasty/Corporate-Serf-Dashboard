# Playlist-Level Overview & Management Proposal

> **Status:** Draft — round 2, in review on PR #76. Register updated after
> the 2026-07-08 user review: OQ-1/3/4/5/6/7/8 settled, OQ-2 resolved as a
> tooltip, phases given an explicit PR breakdown. PR #76 review folded in:
> corrected the provenance-stamp assumption (no committed file is stamped —
> see R2). The former prerequisite has shipped: playlist code identity
> landed in PR #67 (2026-07-07 "Use Playlist Codes As Playlist Identity"
> entry in [`decision_log.md`](./decision_log.md)).
>
> Provenance: roadmap milestone "Playlist-level overview and stats"
> (upcoming #1 in [`roadmap.md`](./roadmap.md)); the 2026-07-03 "Playlists
> Routes Are Stable" decision; vault notes *CSD TODO triage* and *Refleks
> app research* (2026-07-04) and *CSD benchmark visibility model*
> (2026-07-06); user direction notes 2026-07-08.

One page that answers, across **playlists**, what the per-playlist scenario
table already answers within one: *where should I direct my attention?*
Around it, the playlist/benchmark ownership model the page forces us to
settle: what ships with the app, what the user owns, and how the user
controls what they see.

## The user problem

From [`product.md`](./product.md) and [`roadmap.md`](./roadmap.md):
playlists go stale. A player crushes a benchmark, moves on, and forgets it;
months later their mechanics are better and the old scores are worth
re-measuring. Meanwhile another playlist shows a low aggregate percentile —
a weakness worth targeted work. Today nothing surfaces either signal; the
bare `/playlists` route is a name-only dropdown. At a glance, the app should
say which playlists are getting attention, which are languishing, and which
are weak.

## Terms

- **Playlist** — bare scenario list, no rank data. **Benchmark** — playlist
  plus rank thresholds (2026-07-03 "Import Benchmarks From Evxl And
  KovaaK's" decision). "Playlists" unqualified below covers both.
- **The overview** — the new page content at `/playlists` (this proposal).
  **The scenario table** — the shipped per-playlist page at
  `/playlists/{playlistCode}` (called "playlist scenarios overview" in
  `product.md`).

## Shape of the work — three phases, six PRs

Phase 1 alone completes the roadmap milestone as written. Phases 2–3 are
**scope beyond that milestone** (the management model from the vault
direction notes and the 2026-07-08 user notes); accepting this proposal
should add them to the roadmap as the follow-on milestone rather than
silently widening this one.

Phases are user-meaningful stopping points — after any phase the app is
complete and the work could pause indefinitely. PRs within a phase are
review units, cut where semantics change so mechanical diffs never share a
review with behavioral ones.

1. **Phase 1 — the overview page.**
   - *PR 1a:* overview service + grid replacing the transitional selector
     content at `/playlists`; rows navigate to `/playlists/{code}`.
   - *PR 1b:* selector-dropdown removal from both playlist pages (the
     checklist in the routes decision). Fold into 1a if it stays small.
2. **Phase 2 — benchmark library + visibility.**
   - *PR 2a:* the visibility mechanism — preference store, filtering in the
     shared options builder, per-row hide/unhide and a "show hidden" toggle
     on the overview. Ships dark: with today's small playlist set and
     defaults seeded, nothing is hidden until the user hides it.
   - *PR 2b:* the library flip — bundled root becomes `resources/benchmarks/`
     (flat), the six legacy top-level files are deleted as redundant (see
     R2), default visibility seeds Voltaic + Viscose, importer readme
     updated. Mostly mechanical because 2a already owns the semantics.
3. **Phase 3 — playlist management.**
   - *PR 3a:* import moves from Home → Settings to the overview surface.
   - *PR 3b:* delete for user playlists + cleanup affordance for user files
     superseded by bundled benchmarks.

Sequencing note: 2a-before-2b is deliberate — the semantic risk (visibility
filtering everywhere) lands and stabilizes while every playlist is still
visible; the 100-row library arrives only after the focus mechanism exists.
Flipping that order is the cheap experiment if we want to feel the
full-library world first (see R3).

## Requirements register

### Ownership model (R1–R5)

- **R1. Two roots, two owners.** Bundled benchmarks live under a
  `resources/` root, maintained by the repo and updated with app updates;
  user playlists live in `data/playlists/`, managed by the user through the
  app. Single source of truth — no seeding, no copies of bundled files into
  `data/` (vault visibility model: seeding creates a staleness/merge problem
  on every update; one copy read from `resources/` makes updates flow
  automatically). Extends the 2026-06-22 "Keep User Runtime Data Under
  `data/`" decision and the shipped dual-root loader (2026-07-07 decision).
- **R2. The bundled root becomes `resources/benchmarks/`, flat, scanned in
  full.** (User direction; layout settled 2026-07-08, closing OQ-6.) The
  111 files under `resources/playlists/generated/` move to
  `resources/benchmarks/`; the loader scans the whole library instead of
  today's activated six. The six top-level `resources/playlists/*.json`
  files are **deleted, not moved**: their codes are all duplicated by files
  in `generated/` (verified 2026-07-08) — under full-library scanning they
  would be pure duplicate-code noise. Before deleting, verify the
  `generated/` twins carry equivalent rank thresholds/colors, since the app
  currently serves the top-level copies; if any pair disagrees, regenerate
  that benchmark through the importer (a fresh, authoritative pull) rather
  than guessing which copy is stale. No `generated/` subdir survives: the
  don't-hand-edit boundary becomes the rule that the *entire*
  `resources/benchmarks/` root is pipeline-managed — documented in the
  importer readme and enforced by the bundled-invariant test (every bundled
  file carries rank data) extended to the whole root. Note (PR #76 review,
  2026-07-08): **no committed file carries a `generated_from` stamp** — the
  committed corpus predates the importer's provenance stamping (PRs
  #45–#48), so stamps cannot serve as a boundary or a deletion criterion
  today. Restamping the corpus via a bulk importer regeneration would
  restore the inspectability intended by the 2026-07-03 provenance decision
  and is desirable hygiene, but it is **not** a PR 2b prerequisite: nothing
  in this milestone reads the stamps. The importer's true working
  directory — `scripts/benchmark_importer/generated/` staging with its
  manifest — is untouched; its readme's manual-copy destination becomes
  `resources/benchmarks/` and the copy-to-activate step dies (activation
  becomes unhiding).
- **R3. Visibility is a per-code show/hide preference, not file state.**
  Hiding a playlist removes it from selector option lists and (by default)
  the overview; the data still loads, `/playlists/{code}` still resolves
  (route contract: codes are stable), and rank overlays still draw for its
  scenarios. Applies uniformly to benchmarks **and** user playlists — which
  gives "hide instead of delete, so I don't have to remember the share
  code" for free.
  *Why visibility at all, when dropdowns are searchable?* (User challenge,
  2026-07-08.) Search solves findability when you know the name; it doesn't
  solve browsing (open the Home filter and skim what you care about — dead
  at 117 options) or first-run focus (the curated defaults buried under a
  hundred "Never played" rows). The overview itself degrades gracefully —
  sorted by last-played, active playlists float up — so the dropdowns and
  first-run experience, not the grid, are what visibility protects.
  Verified bound on the blast radius: rank overlays draw only for the
  *selected* playlist filter (`home.py:640`), so loading 100+ benchmarks
  does not change overlay behavior; PR 2b should still audit the few code
  paths that enumerate the whole store.
- **R4. Defaults-aware show-list.** (Settled 2026-07-08, closing OQ-4 and
  its acknowledged tradeoff.) The preference store keeps two user lists —
  `shown` and `hidden` — and the app ships a per-release
  `DEFAULT_VISIBLE_CODES` constant (Voltaic + Viscose). Visibility:
  user-root playlists are visible unless in `hidden` (importing *is* the
  intent to see); bundled benchmarks are visible if in `shown`, or in the
  shipped defaults and not in `hidden`. This keeps show-list semantics for
  the long tail (new library additions arrive hidden — no surprise
  flooding) while letting a future default-worthy "Voltaic S6" arrive
  visible via the updated defaults constant — unless this user explicitly
  hid it, which `hidden` remembers. Not a `config.toml` option: after first
  run the UI owns visibility, and a config knob would be a second control
  surface fighting it. A "new benchmarks arrived (hidden)" startup
  notification would need a seen-codes list — deferred nicety, not in
  scope.
- **R5. Delete exists only for user playlists.** Deleting removes the
  `data/playlists/` file and the store entry (with confirmation).
  Bundled benchmarks cannot be deleted — hiding is the equivalent — which
  forecloses the delete-then-reimport degradation (a re-import via share
  code would come back rank-less; vault visibility model). Startup remains
  read-only: files are deleted only by explicit user action.

### The overview page (R6–R11)

- **R6. Placement and navigation per the routes decision.** The overview
  replaces the bare-route selector content at `/playlists`; rows navigate to
  `/playlists/{playlistCode}`; the transitional selector dropdowns are then
  removed from both playlist pages. Rows need visible click affordances —
  cursor, hover tint, full-row target. Home's playlist *filter* dropdown is
  a different component with a different role and stays. With the scenario
  table's rows now linking into Home per scenario (PR #70), this completes
  the drill chain: overview → scenario table → Home.
- **R7. Columns come from local run data and the existing rank cache —
  the overview triggers no network calls.** One playlist's scenario table
  already creates bursty cold-cache lookups (2026-04-28 retry decision); an
  overview fanning out across *all* visible playlists would multiply that.
  Aggregate percentile therefore reads only cached rank info, shows its
  coverage honestly (R9), and fills in as drilling into playlists warms the
  cache. **Accepted tradeoff** (user, 2026-07-08): a user rapidly clicking
  through playlists triggers each table's cold-cache burst manually — but
  that is user-paced, one playlist per click, identical to today's behavior,
  and deduplicated per navigation by the 2026-04-29 mounted-route-state
  decision. The line held here is that the *overview itself* never
  initiates lookups. A playlist-wide/overview-wide refresh action stays a
  parked bursty-API design question (vault TODO triage).
- **R8. Column set (v1).** See the column register below. Sortable AG Grid,
  same conventions as the scenario table: bare-name grid functions,
  NULLS-LAST comparators, relative timestamps with exact-time tooltips,
  grid-owned scrolling.
- **R9. Aggregates declare their coverage.** Percentile aggregates are
  computed over *played scenarios with cached rank info* and displayed with
  the denominator (e.g. `78% · 12/20`), so a number computed from 2 of 20
  scenarios can't masquerade as playlist-wide truth. Unplayed playlists show
  "Never" / em-dash and sort last.
- **R10. The overview is the future home of "what should I train".** The
  Refleks-derived Focus column (rank closeness + trend + staleness,
  deterministic daily jitter) lands here once the next-rank-delta and
  trend-verdict Future items exist. Out of scope now; the column layout just
  shouldn't preclude adding a column later (it doesn't — AG Grid).
- **R11. Store reads take snapshots.** Overview aggregation iterates the
  shared in-memory stores at callback time — same exposure as the
  "Unsynchronized shared in-memory stores" item in
  [`tech_debt.md`](./tech_debt.md). Take `list(...)` snapshots at callback
  entry; if the store-locking work lands first, use it.

### Visibility & management surfaces (R12–R14)

- **R12. Management lives on the overview page, not a separate page.**
  (Settled 2026-07-08, closing OQ-3.) The overview already enumerates
  exactly the objects being managed. Concretely: an Import button (Phase
  3), per-row hide/unhide, per-row delete where R5 allows, and a "show
  hidden" toggle that reveals hidden rows (visually muted) for unhiding.
  Guiding principle from the vault note: the user interacts with the app,
  not the filesystem. Revisit only if the page gets crowded.
- **R13. Visibility filters every playlist option list through the shared
  options builder.** `get_playlist_selector_options()` (shipped by the
  re-key work) is the single source of finished options; visibility
  filtering belongs there (or in one wrapper), so the Home filter, the Aim
  Training Journey `MultiSelect`, and the overview can never disagree about
  what's visible.
- **R14. Import relocates; the flow is reused.** Phase 3 moves the import
  entry point from the Home Settings modal to the overview surface, reusing
  the existing import service path and the shipped duplicate-code refusal
  messaging (extended to "already exists (hidden) — unhide it" once R3
  exists). Other Settings-modal content stays put (verify exact modal
  contents at build time). The superseded-user-copy notification from the
  re-key work gets its cleanup affordance here (a delete action on the
  redundant file), keeping startup read-only.

## Column register (Phase 1)

| Column | Source | Cost | Notes |
| ------ | ------ | ---- | ----- |
| Name | `PlaylistData.name` via shared display labels | Local | Disambiguated `Name (CODE)` labels from the re-key work |
| Type badge (Benchmark/Playlist) | `scenarios[].ranks` presence | Local | Kept (settled 2026-07-08, OQ-7) — distinguishes curated vs imported once both mix in one table |
| Played / Scenarios | run store ∩ playlist scenarios | Local | Fused coverage form `12/20` answers "have I even played this?" and gives R9 its denominator; subsumes a bare scenario-count column |
| Total runs | sum of per-scenario run counts | Local | |
| Last played | max of per-scenario last-played | Local | The staleness signal; "Never" + NULLS LAST for untouched playlists. Tooltip is two lines: the exact timestamp (existing convention) plus the stalest scenario — see OQ-2 resolution |
| Median percentile | rank cache only | Cached | Median over mean (settled 2026-07-08, OQ-1) — robust to one outlier scenario in small playlists; with coverage per R9 |
| Lowest percentile | rank cache only | Cached | "My worst weakness here" — mirrors the scenario table's headline use case |

Deliberately excluded, with reasons:

- **Leaderboard / benchmark / playlist IDs** (user stats list 2–4):
  `PlaylistData` carries only `name`, `code`, `scenarios` (re-verified
  post-re-key) — leaderboard IDs are *per-scenario* metadata, and the
  KovaaK's benchmark ID appears nowhere in the committed corpus (the
  committed generated files predate the importer's provenance stamping —
  see R2). Debugging metadata, not attention-directing signals. Defer until
  a concrete need appears.
- **Share code** (user stats list 5): agreed not needed — it *is* the URL
  identity. A copy-share-code affordance on the scenario table page header
  would serve sharing better than a grid column; parked.
- **Average timestamp**: rejected — an average of "last played" dates
  doesn't correspond to any question a player asks.
- **Median timestamp** (raised 2026-07-08): rejected too, but for a
  different reason — it *is* interpretable ("half the scenarios touched
  since X"), yet it's a softer restatement of what `Played 12/20` + last
  played + the stalest-scenario tooltip already say, and the stalest bound
  is the crisper freshness signal. Not worth a column.
- **Stalest scenario as a column**: folded into the Last played tooltip
  (OQ-2 resolution below); promote to a real column only if sorting by it
  proves wanted.
- **Lowest rank** (user stats list 8): future column once rank-per-scenario
  derivation ships with the next-rank-threshold Future item; slots in beside
  the Focus column (R10).

## Open questions — resolutions (2026-07-08 review)

Numbering kept from round 1 for continuity; all are settled or resolved
with a lean.

- **OQ-1. Mean or median percentile? → Median.** Settled.
- **OQ-2. Stalest scenario: column? → Tooltip line, with a caveat.** User
  suggestion: hover tooltip instead of a column — adopted, with one honest
  limitation and one convention note. Limitation: tooltip content can't be
  sorted on, so this serves curiosity ("which scenario is dragging this
  playlist?"), not attention-direction; if "sort playlists by stalest
  scenario" ever becomes the wanted behavior, promote it to a column then.
  Convention note: the Last played cell's tooltip is already claimed by the
  exact-timestamp convention (PRs #17/#19/#23), so this becomes a two-line
  tooltip — exact timestamp, then `Stalest: <scenario>, <relative age>` —
  rather than a second competing tooltip surface.
- **OQ-3. Manager surface → overview-hosted.** Settled (R12).
- **OQ-4. Preference semantics → defaults-aware show-list.** Settled; the
  user-flagged tradeoff (a default-worthy "Voltaic S6" arriving hidden) is
  resolved by the shipped defaults constant + `hidden`-list override design
  in R4.
- **OQ-5. Terminology → "show/hide".** Settled. Nothing is functionally
  disabled — data loads, routes resolve, overlays draw — so "hide" is the
  honest verb. A favorites/star system is a third state that doesn't answer
  the 117-row default problem; it can layer on later as sort pinning.
- **OQ-6. Bundled-root layout → flat, no `generated/` subdir.** Settled;
  rationale and the legacy-six deletion in R2. The subdir's only real value
  would be separating hand-crafted from importer-produced files — and after
  the redundant six are deleted, the whole root is pipeline-managed by
  rule. (No stamp-based distinction exists in the committed corpus today —
  see the R2 note; the boundary is the documented rule plus the
  bundled-invariant test, not per-file provenance.) A future hand-crafted
  benchmark is still expressible as a `data/playlists/` file with `ranks`
  filled in.
- **OQ-7. Type badge → keep.** Settled.
- **OQ-8. Scenario-first navigation → out of scope; park a Scenarios
  page.** Settled. The overview → scenario table → Home drill chain is
  complete (PR #70); no breadcrumb component needed at this depth. The real
  gap behind the question — scenarios living in several playlists or none —
  is a dedicated **Scenarios page**: add it to `roadmap.md` Future when
  this proposal is accepted.

## Interactions with in-flight and parked work

- **Playlist code identity (shipped, PR #67).** The overview consumes
  code-keyed stores, finished selector options, and dual-root loading —
  all in place. R2's root rename and full-library scan build on it in
  PR 2b.
- **Benchmark importer.** PR 2b ends the readme's copy-to-activate
  instruction (activation becomes unhiding) and repoints the reviewed-output
  destination to `resources/benchmarks/`. The staging dir and manifest are
  untouched.
- **Dropdown UX consistency pass** ([`tech_debt.md`](./tech_debt.md)) —
  explicitly scheduled to be revisited *after* the overview ships; Phase 1's
  selector removal is what unblocks it.
- **Run history proposal** — sequenced after this milestone; no coupling
  ([`run_history_proposal.md`](./run_history_proposal.md)).
- **Focus column / next-rank / trend verdict** — future layers that land on
  this page (R10); this proposal only reserves the room.

## Provisional acceptance criteria

Phase 1:

1. `/playlists` renders the overview table for all loaded playlists; each
   row navigates to `/playlists/{code}`; the transitional selector dropdowns
   are gone from both playlist pages (routes-decision checklist complete).
2. Rendering the overview issues zero KovaaK's API requests; percentile
   cells show cached values with coverage counts, and cold-cache playlists
   render with placeholders, not errors.
3. A never-played playlist shows "Never" and sorts after played ones in
   every sortable column (NULLS LAST); the Last played tooltip carries the
   exact timestamp and the stalest scenario.
4. Aggregates are correct on fixtures with: unplayed scenarios, partially
   cached ranks, duplicate playlist names, and an empty playlist.

Phase 2:

5. PR 2a: hide/unhide from the overview persists across restarts via the
   `data/` preference store; hidden playlists vanish from the Home filter
   and Journey picker (shared options builder) but remain reachable at
   `/playlists/{code}`; "show hidden" reveals muted rows.
6. PR 2b: a fresh checkout loads the full bundled library from
   `resources/benchmarks/`; only the default set (Voltaic, Viscose) is
   visible; the six legacy top-level files are gone after threshold/color
   parity with their `generated/` twins is verified (importer regeneration
   as the tiebreaker on any mismatch); the bundled-invariant test covers
   the whole new root; the importer readme no longer instructs
   copy-to-activate.
7. PR 2b: an audit of store-enumerating code paths (Home filter options,
   Journey, overview, overlays) confirms no surface changed behavior from
   the library expansion except the intended option lists.

Phase 3:

8. Import is reachable from the overview surface and absent from the Home
   Settings modal; duplicate-code refusal suggests unhiding when the
   existing playlist is hidden.
9. Deleting a user playlist removes its file and row after confirmation;
   bundled benchmarks offer hide but not delete; a bundled-superseded user
   copy can be cleaned up from the UI.
10. Full merge bar green per PR (ruff format/check, mypy, pytest).
