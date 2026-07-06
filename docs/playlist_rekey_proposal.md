# Playlist Re-key Proposal

> **Status:** Proposed — revised through review rounds 1–4 (2026-07-05/06;
> import semantics settled by the user 2026-07-06); all in PR #58. Land
> before the playlist-level overview milestone (upcoming #1 in
> [`roadmap.md`](./roadmap.md)) so the overview is born code-keyed.
>
> Provenance: top finding of the 2026-07-04 whole-project audit TODO triage
> (vault draft); ported 2026-07-05 with all code citations re-verified at
> `a252af3`.

Re-key the in-memory `playlist_database` from playlist **name** to playlist
**code**. Names become display-only labels; codes are the identity the app has
already ratified everywhere else (URLs, imports, the shared selector options).

## Problem (current behavior, verified)

`playlist_database` is keyed by playlist **name**, but KovaaK's playlist names
are not guaranteed unique. Every same-named playlist after the first is
silently lost:

- `playlist_database: dict[str, PlaylistData]` keyed by `playlist_data.name` —
  `source/kovaaks/data_service.py:48`, populated at `:485` and `:523`.
- `load_playlists()` (`data_service.py:479-485`): a second JSON file carrying a
  duplicate name is **skipped with only a log warning**. The UI never shows it
  and nothing tells the user. The scan order is unsorted `os.scandir()`
  (`:469-472`), so *which* duplicate survives is unspecified.
- `load_playlist_from_code()` (`data_service.py:513-516`): importing a playlist
  whose name matches an existing one is refused the same way — even though its
  code is unique.
- `get_playlist_by_code()` (`data_service.py:235-240`) linearly scans
  `values()` — a dropped playlist is unreachable even by its unique code, so
  the stable `/playlists/{playlistCode}` route contract (2026-07-03 "Playlists
  Routes Are Stable" entry in [`decision_log.md`](./decision_log.md)) can 404
  for a playlist the user believes they imported.
- On-disk filenames are name-derived (`get_playlist_file_path`,
  `data_service.py:51-61`; write at `:527-532`), so two same-named playlists
  also collide at the file layer. Imports are also still written into
  `resources/playlists/`, which the 2026-06-22 "Keep User Runtime Data Under
  `data/`" decision reserves for bundled defaults — future user-imported
  playlists belong under `data/playlists/`.
- The Home page playlist filter uses the **name** as its selector value: the
  dropdown is fed by `get_playlists()` (sorted names, `home.py:572`) and its
  value flows into `get_scenarios_from_playlists(name)` (`home.py:521-527`)
  and `get_rank_data_from_playlist(name, ...)` (`home.py:329-331`, `:356-358`).
  The Aim Training Journey `MultiSelect` is fed the same name list
  (`aim_training_journey.py:75-82`). The shared `playlist_selector()` component
  (`source/pages/playlist_components.py`) already uses
  `{label: playlist.name, value: playlist.code}`.

The storage key contradicts the identity the app has already ratified: URLs,
imports, and the shared selector options all speak playlist **code**; the
database, the Home filter, and the Journey picker still speak name.

## Target design

1. **Key `playlist_database` by `code`**: `dict[str, PlaylistData]` where the
   key is `playlist.code`. Duplicate *names* become legal; duplicate *codes*
   become the real conflict.
2. **Startup duplicate-code policy: skip and warn, deterministically.**
   Applies to directory loading only — an explicit import of a duplicate code
   is refused with a message (§3). The
   first occurrence of a code wins; later ones are skipped with a warning
   naming both files. Precedent: the benchmark importer skips-and-reports
   conflicting duplicates rather than resolving them silently, "because a
   missing benchmark is visible and recoverable" while a silent wrong result
   is not (2026-07-03 "Import Benchmarks From Evxl And KovaaK's" entry in
   [`decision_log.md`](./decision_log.md)). "First" is well-defined: roots are
   scanned in a fixed order (§6), and within each root files are processed
   sorted by `(filename.casefold(), filename)` — casefolded for
   cross-platform stability, with the exact name as tiebreaker because
   case-sensitive filesystems can hold names that tie under casefold alone —
   never raw `os.scandir()` order.
3. **Explicit imports of an existing code are refused, visibly.**
   `load_playlist_from_code()` keeps refusing duplicates — but by *code*, not
   name, and the refusal is a user-visible message naming the existing
   playlist (name and code), not just a log line. A new code adds the playlist
   and writes it to `data/playlists/` (§6); import stays insert-only. Settled
   2026-07-06 (user decision, superseding the upsert design from review
   round 2): refusal avoids the fiddly parts of upsert — no obsolete-file
   cleanup when an upstream rename changes the name-derived filename, no
   "updated"-vs-"imported" dual messaging — and composes with the future
   model: refresh becomes delete-then-import once playlist deletion ships
   (future functionality; until then, deleting the playlist's file from
   `data/playlists/` and restarting is the documented workaround — a conscious
   gap, and one that only covers user-root playlists: bundled playlists
   refresh via app updates instead). Refusal also closes the import-time path
   to a degradation upsert would have allowed: share-code imports carry no
   rank data (`data_service.py:509`), so an import matching an
   already-loaded bundled *benchmark* (playlist + rank thresholds) could have
   replaced it with a bare, rank-less copy. The temporal reverse — a code
   imported *before* a later bundled update ships it — still shadows the
   richer copy, but that is exactly the §6 cross-root case: the startup
   warning names the shadowed file, and deleting the user copy adopts the
   bundled benchmark. Adding upsert later would be a non-breaking addition if
   refresh demand appears; shipping it now and walking it back would be a
   behavior break.
4. **Lookups migrate from name to code**:
   - `get_playlist_by_code()` becomes a dict hit.
   - `get_scenarios_from_playlist_code()` already exists (`:248-254`) — becomes
     the canonical scenario lookup.
   - `get_scenarios_from_playlists(name)` (`:243-245`) and
     `get_rank_data_from_playlist(name, scenario)` (`:256-275`) switch to code
     parameters; names remain display-only labels.
   - The aim-training-journey functions (`:77-125`) take codes and key their
     result dict by **code** — today it is keyed by name, so duplicate names
     would still collapse to one series even with a code-keyed store. The page
     maps code → display label at the plot layer via the service lookup (§5).
     This is a mechanical parity change only: the page is work-in-progress and
     may be removed, so no further UX investment.
   - `get_playlists()` (`:218-220`, the bare name list feeding Home and
     Journey today) is superseded by `get_playlist_selector_options()`
     (`:223-232`): sorted by name for display, carrying code values.
5. **Selectors: the service returns finished options.**
   `get_playlist_selector_options()` becomes the single source of playlist
   options *with disambiguation already applied*: `{label: name, value:
   code}`, where the label becomes `Name (CODE)` only when two or more
   playlists share a name — the common case stays clean. A companion service
   lookup (e.g. `get_playlist_display_label(code)`) exposes the same labels
   for non-dropdown surfaces: Journey's legend and messages. Labels live in
   one place, so dropdowns and legends can never disagree. Components consume
   finished options and keep their role-specific behavior: the Home filter
   stays a clearable, persisted `Select` (it means "no filter" when empty);
   `playlist_selector()` is genuinely unchanged — it already passes
   `get_playlist_selector_options()` straight through
   (`playlist_components.py:14`) — and remains transitional on `/playlists`
   per the "Playlists Routes Are Stable" decision; Journey keeps its
   `MultiSelect`. Component-level UX unification is explicitly out of scope
   (parked in [`tech_debt.md`](./tech_debt.md)).
6. **Two on-disk roots, collision-free filenames, tolerant of absence.** Per
   the 2026-06-22 "Keep User Runtime Data Under `data/`" decision, newly
   imported playlists are written to
   `data/playlists/{sanitized name} [{code}].json` (code-suffixed, eliminating
   same-name file collisions); `resources/playlists/` becomes read-only
   bundled defaults. The loader scans `data/playlists/` first, then
   `resources/playlists/` — top-level `*.json` only in each, matching today's
   non-recursive semantics (`resources/playlists/generated/` stays an
   unscanned library; users activating a generated benchmark copy it to
   `data/playlists/` going forward — the importer readme's copy instructions
   update in the shipping PR). Combined with §2, root order gives cross-root
   precedence: **a `data/playlists/` copy of a code wins over a bundled
   copy**, with a warning naming the shadowed file (settled 2026-07-05:
   `data/` is the user's, and the warning keeps the conflict visible and
   recoverable — delete the user copy to fall back to the bundled one).
   Same-code-in-both-roots arises without re-imports: a code imported today
   can appear in a later bundled update, and the importer's manual activation
   copies can collide the same way. Because
   `data/` is gitignored and `load_playlists()` runs at module import
   (`data_service.py:535`), the loader must treat a missing `data/playlists/`
   as empty rather than raising — a clean checkout starts on bundled playlists
   alone — and the import writer creates the directory (parents included)
   before its first write. The loader keys from JSON *content*, not the
   filename, so existing files need no rename; `get_playlist_file_path`'s
   path-traversal guard (`:59-60`) carries over to the new write root.
7. **Playlists without a usable `code`**: `PlaylistData.code` is already a
   required field (`source/kovaaks/data_models.py:52`), so a codeless file
   already fails validation today and is skipped — but with a generic
   "Invalid JSON format" warning (`data_service.py:486-487`). The field is a
   plain `str`, however, so empty and whitespace-only codes currently pass
   validation (found in review round 3) — unacceptable once `code` is the
   store key, selector value, route identity, and filename suffix. Tighten
   the model: strip surrounding whitespace and reject blank codes at
   validation, so blank behaves exactly like missing. All 117 committed
   `resources/playlists/**` files carry a non-blank `code` (value-level check
   2026-07-06: the 6 top-level files — the only ones `load_playlists()`
   scans — and the 111 under `generated/`). Only hand-crafted files can lack
   one (API-imported and generated benchmark files always have one).
   Remaining work: make the skip warning actionable for missing **or blank**
   codes ("add a `code` field") and document the requirement in the README's
   Rank Data section. Simpler than synthesizing fallback keys.

## Migration plan (existing user data)

- **No forced migration.** Loading keys from file *content*, and
  `resources/playlists/` stays scanned, so existing `{name}.json` files there
  keep working untouched. No rename script, no data rewrite, no file moves.
- Fresh installs have no `data/` directory (it is gitignored); the loader
  treats the missing root as empty and the first import creates it.
- Files missing `code` already fail to load today (required model field), so
  there is **no behavioral break** — the change is a clearer warning (see §7).
- Re-importing an existing code is refused with a message naming the existing
  playlist (§3). There is no in-app refresh path until playlist deletion
  ships; deleting the playlist's file from `data/playlists/` and restarting is
  the interim workaround.
- **Stale persisted selections (Home and Journey)**: the Home dropdown and
  the Journey `MultiSelect` both have `persistence=True` (`home.py:578`,
  `aim_training_journey.py:86`), so after the upgrade the client restores
  previously selected *names* into now code-valued selectors. The migrated
  callbacks must treat unknown values as "no selection" — for the
  `MultiSelect`, filter unknown entries out and keep any valid ones — rather
  than raising (today an unknown name raises `KeyError` in
  `get_scenarios_from_playlists`).
- No cache impact: rank/leaderboard caches key on leaderboard/scenario
  identity, not playlist name.

## Blast radius

| Surface | Change |
| ------- | ------ |
| `source/kovaaks/data_service.py` | Store key, startup dup policy + deterministic ordering, dual-root loading tolerant of a missing user root, code-keyed import refusal with a named message, options builder returning finished labels + code→label lookup, write root + file naming — the bulk of the diff. |
| `source/pages/home.py` | Filter consumes the shared code-valued options (stays a clearable, persisted `Select`); callbacks pass codes to the renamed lookups; import flow surfaces the refusal message naming the existing playlist; tolerate the stale persisted name (see migration plan). |
| `source/pages/playlist_components.py` | No change — `playlist_selector()` already consumes `get_playlist_selector_options()`, which now returns finished labels. |
| `/playlists` pages | Already route by code; `get_playlist_by_code` just gets cheaper. Selector removal is separately scheduled by the overview milestone's checklist in the "Playlists Routes Are Stable" decision — do not couple it here. |
| Aim Training Journey page | Mechanical parity only: `MultiSelect` consumes the shared options; journey functions keyed by code; legend labels via the service's code→label lookup; stale persisted names filtered like Home's (see migration plan). WIP page, possibly removed later — no further investment. |
| `scripts/benchmark_importer/readme.md` | Activation-copy destination for users becomes `data/playlists/` — update in the shipping PR. |
| Tests | Fixtures with duplicate names / duplicate codes, dual-root fixtures, deterministic-ordering cases, missing-user-root case, import-refusal cases. |

Note: [`architecture.md`](./architecture.md) already describes
`playlist_database` as "keyed by code" — incorrect today, true once this
ships. The shipping PR should add the dual-root loading to its store
description while it's in there.

Explicitly out of scope: the store-locking work ("Unsynchronized shared
in-memory stores" in [`tech_debt.md`](./tech_debt.md)) — same module, separate
PR; the playlist-level overview page itself, which this unblocks but does not
include; and dropdown UX/component unification (see `tech_debt.md`).

## Acceptance criteria

1. Two playlists with identical names and different codes: both load from
   disk, both import via share code, both appear in every selector (labels
   disambiguated), and each resolves correctly at `/playlists/{code}`.
2. Importing a playlist whose *name* matches an existing one succeeds as a new
   playlist. Importing a *code* that already exists is refused with a
   user-visible message naming the existing playlist (name and code), not just
   a log line; the store and both on-disk roots are left unchanged.
3. No name-keyed access to `playlist_database` remains (`rg` for the old
   lookup names comes back empty).
4. Existing user playlist files load with zero manual steps; a file with a
   missing, empty, or whitespace-only `code` produces one actionable warning
   and is skipped (today a missing code is skipped with a generic
   invalid-JSON warning, and blank codes are accepted outright).
5. New imports land in `data/playlists/` with code-suffixed filenames;
   same-named imports no longer overwrite or collide on disk.
6. The same code in both roots: the `data/playlists/` copy wins, one warning
   names the shadowed bundled file, and the winner is identical regardless of
   directory-enumeration order (deterministic across runs and platforms).
7. On a fresh checkout with no `data/` directory, the app starts and serves
   bundled playlists; the first import creates `data/playlists/`.
8. Stale persisted selector values (pre-migration playlist names) do not
   crash any callback: the Home filter degrades to "no selection", and the
   Journey `MultiSelect` drops unknown entries while keeping valid ones.
9. Selecting two same-named playlists on Aim Training Journey produces two
   distinct series with disambiguated labels.
10. Full merge bar green (ruff format/check, mypy, compileall, pytest) locally
    and in CI.

## Test plan

- **Regression (the bug):** fixture dir with two same-named/different-code
  playlists → both present in `playlist_database`, both selectable,
  `get_playlist_by_code` resolves each.
- **Startup conflict + determinism:** two files with the same *code* in one
  root → the sort-order-first file wins, warning logged naming both (assert
  the exact winner); include a casefold-tie pair (`A.json` vs `a.json`) to
  exercise the exact-name tiebreaker.
- **Import refusal:** importing a new code succeeds and writes under
  `data/playlists/`; importing an existing code — whether it was loaded from
  the bundled or the user root — is refused with a message naming the existing
  playlist, and neither the store nor the on-disk files change.
- **Dual root:** same code in `data/playlists/` and `resources/playlists/` →
  the user copy wins with a warning naming the shadowed bundled file; a
  bundled-only code still loads.
- **Missing user root:** `load_playlists()` with no `data/playlists/` present
  → no error, bundled playlists load; the first import creates the directory.
- **Missing or blank code:** files with a missing, an empty, and a
  whitespace-only `code` → each skipped with an actionable warning; rest of
  directory still loads.
- **File naming:** `write_playlist_data_to_file` for same-named playlists
  produces distinct filenames under `data/playlists/`; round-trips through
  `load_playlists()`.
- **Lookup migration:** rank-overlay and journey queries by code return
  identical results to the pre-change name-based queries on a non-colliding
  fixture (behavioral parity check).
- **Journey identity + stale persistence:** the journey data function returns
  one entry per code for two same-named playlists; the plot layer renders two
  traces whose labels come from the same service lookup the dropdowns use; a
  persisted pre-migration selection (mixed stale names and valid codes) is
  filtered without raising, mirroring the Home test.
- **Options builder:** service-level test that disambiguation triggers only on
  collisions; Home callback tests assert the filter emits codes and a stale
  persisted name as the incoming value is handled without raising.

## Review round

Round 1 (2026-07-05, Codex): dual-root loading with new writes under
`data/playlists/` (was: writes stayed in `resources/playlists/`, conflicting
with the 2026-06-22 `data/` decision); unify the options contract rather than
the component; journey series keyed by code; deterministic scan ordering;
committed-file count corrected to 117. Cross-root precedence — user root
wins — was settled by the user 2026-07-05.

Round 2 (2026-07-05, Codex): explicit imports became **upserts by code**
(§3), resolving the contradiction between the re-import/shadowing story and
round 1's "refuse duplicate code" criterion — startup file conflicts and
explicit imports are now distinct policies; the loader tolerates a missing
`data/playlists/` and the writer creates it, since `load_playlists()` runs at
module import and `data/` is gitignored (§6); and disambiguated labels moved
into the service — `get_playlist_selector_options()` returns finished options
and a code→label lookup serves Journey (§5, the reviewer's preferred option),
leaving `playlist_selector()` genuinely unchanged.

Follow-up (2026-07-06, user decision): round 2's upsert was reverted to
**refusal with a named message** (§3), settling round 2's open decision
point 3. Refusal keeps the import insert-only (no obsolete-file cleanup, no
dual messaging), composes with delete-then-import once playlist deletion
ships, and closes the import-time path to a rank-less share-code import
replacing a rank-rich bundled benchmark (the import-before-bundling edge is
§6's warning case). The cross-root precedence rule (§6) survives on its own
merits — organic same-code collisions still need a deterministic, visible
winner.

Round 3 (2026-07-06, Codex): `code` validation tightened to reject empty and
whitespace-only values, not just missing ones (§7) — blank codes previously
passed the plain-`str` field, unacceptable for a store key / route identity /
filename suffix; within-root ordering became a total order,
`(filename.casefold(), filename)`, since casefold alone ties on
case-sensitive filesystems (§2); and stale upsert-era wording was corrected —
§6's "re-imported" writes, the delete-file workaround scoped to user-root
playlists (bundled refresh via app updates), and §3's benchmark-shadowing
claim scoped to the import-time path.

Round 4 (2026-07-06, Codex): stale-persistence handling extended to the Aim
Training Journey `MultiSelect`, which also carries `persistence=True`
(`aim_training_journey.py:86`) — unknown persisted entries are filtered out
while valid ones are kept, mirroring Home (migration plan, criterion 8, test
plan).

Decision points needing sign-off:

1. **Startup duplicate-code policy** — skip-and-warn (proposed) vs last-wins.
2. **Missing-`code` policy** — the status quo already rejects codeless files
   via required-field validation; the question reduces to improving the skip
   warning (proposed) vs synthesizing fallback keys.

Everything else is mechanical once those are fixed. Suggested sequencing: land
before the playlist-level overview milestone (the overview will enumerate
playlists — it should be born code-keyed).
