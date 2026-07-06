# Playlist Re-key Proposal

> **Status:** Proposed — awaiting review. Land before the playlist-level
> overview milestone (upcoming #1 in [`roadmap.md`](./roadmap.md)) so the
> overview is born code-keyed.
>
> Provenance: top finding of the 2026-07-04 whole-project audit TODO triage
> (vault draft); ported 2026-07-05 with all code citations re-verified at
> `a252af3`.

Re-key the in-memory `playlist_database` from playlist **name** to playlist
**code**. Names become display-only labels; codes are the identity the app has
already ratified everywhere else (URLs, imports, the shared selector).

## Problem (current behavior, verified)

`playlist_database` is keyed by playlist **name**, but KovaaK's playlist names
are not guaranteed unique. Every same-named playlist after the first is
silently lost:

- `playlist_database: dict[str, PlaylistData]` keyed by `playlist_data.name` —
  `source/kovaaks/data_service.py:48`, populated at `:485` and `:523`.
- `load_playlists()` (`data_service.py:479-485`): a second JSON file carrying a
  duplicate name is **skipped with only a log warning**. The UI never shows it
  and nothing tells the user.
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
  also collide at the file layer.
- The Home page playlist filter uses the **name** as its selector value: the
  dropdown is fed by `get_playlists()` (sorted names, `home.py:572`) and its
  value flows into `get_scenarios_from_playlists(name)` (`home.py:521-527`)
  and `get_rank_data_from_playlist(name, ...)` (`home.py:329-331`, `:356-358`).
  The newer shared `playlist_selector()` component
  (`source/pages/playlist_components.py`) already uses
  `{label: playlist.name, value: playlist.code}`.

The storage key contradicts the identity the app has already ratified: URLs,
imports, and the shared selector all speak playlist **code**; only the
database and the Home filter still speak name.

## Target design

1. **Key `playlist_database` by `code`**: `dict[str, PlaylistData]` where the
   key is `playlist.code`. Duplicate *names* become legal; duplicate *codes*
   become the real conflict.
2. **Duplicate-code policy**: skip and warn (do not last-wins). Precedent: the
   benchmark importer skips-and-reports conflicting duplicates rather than
   resolving them silently, "because a missing benchmark is visible and
   recoverable" while a silent wrong result is not (2026-07-03 "Import
   Benchmarks From Evxl And KovaaK's" entry in
   [`decision_log.md`](./decision_log.md)). The same reasoning applies here: a
   missing playlist is visible and recoverable; a silently replaced one is not.
3. **Lookups migrate from name to code**:
   - `get_playlist_by_code()` becomes a dict hit.
   - `get_scenarios_from_playlist_code()` already exists (`:248-254`) — becomes
     the canonical scenario lookup.
   - `get_scenarios_from_playlists(name)` (`:243-245`),
     `get_rank_data_from_playlist(name, scenario)` (`:256-275`), and the
     aim-training-journey functions (`:77-125`, which take playlist *names*)
     switch to code parameters; names remain display-only labels.
   - `get_playlists()` / `get_playlist_selector_options()` (`:218-232`) sort by
     name for display but carry code values.
4. **Selectors**: every playlist dropdown uses `{label: name, value: code}` via
   the shared `playlist_selector()` — the Home filter migrates onto it. When
   two playlists share a name, disambiguate the label as `Name (CODE)` — only
   for colliding names, so the common case stays clean.
5. **On-disk filenames**: new/updated writes include the code, e.g.
   `{sanitized name} [{code}].json`, eliminating file collisions. The loader is
   already filename-agnostic (it keys from JSON *content*, not the filename —
   `load_playlists()` reads every `*.json`), so old files need no rename.
6. **Playlists without a `code`**: `PlaylistData.code` is already a required
   field (`source/kovaaks/data_models.py:52`), so a codeless file already fails
   validation today and is skipped — but with a generic "Invalid JSON format"
   warning (`data_service.py:486-487`). All 347 bundled
   `resources/playlists/**` files carry `code` (verified 2026-07-05); only
   hand-crafted files can lack it (API-imported and generated benchmark files
   always have one). Remaining work: make the missing-`code` skip warning
   actionable ("add a `code` field") and document the requirement in the
   README's Rank Data section. Simpler than synthesizing fallback keys.

## Migration plan (existing user data)

- **No forced migration.** Loading keys from file *content*, so existing
  `{name}.json` files under `resources/playlists/` keep working untouched. No
  rename script, no data rewrite.
- Files missing `code` already fail to load today (required model field), so
  there is **no behavioral break** — the change is a clearer warning (see §6).
- New imports write the collision-free filename format; old files only change
  if re-imported.
- **Stale persisted Home filter**: the Home dropdown has `persistence=True`
  (`home.py:578`), so after the upgrade the client restores the previously
  selected *name* into a now code-valued selector. The migrated callbacks must
  treat an unknown value as "no selection" rather than raising (today an
  unknown name raises `KeyError` in `get_scenarios_from_playlists`).
- No cache impact: rank/leaderboard caches key on leaderboard/scenario
  identity, not playlist name.

## Blast radius

| Surface | Change |
| ------- | ------ |
| `source/kovaaks/data_service.py` | Store key, dup policy, lookup signatures, file naming — the bulk of the diff. |
| `source/pages/home.py` | Playlist filter → shared `playlist_selector()`; callbacks pass codes to the renamed lookups; tolerate the stale persisted name (see migration plan). |
| `source/pages/playlist_components.py` | Already `{label: name, value: code}` — becomes the single selector implementation; no change expected. |
| `/playlists` pages | Already route by code; `get_playlist_by_code` just gets cheaper. Selector removal is separately scheduled by the overview milestone's checklist in the "Playlists Routes Are Stable" decision — do not couple it here. |
| Aim Training Journey page | Passes playlist names today; migrate to codes with names as labels. |
| Tests | New fixtures with duplicate names / duplicate codes; existing playlist fixtures gain `code` fields if any lack them. |

Note: [`architecture.md`](./architecture.md) already describes
`playlist_database` as "keyed by code" — incorrect today, true once this
ships; no doc change needed in the shipping PR.

Explicitly out of scope: the store-locking work ("Unsynchronized shared
in-memory stores" in [`tech_debt.md`](./tech_debt.md)) — same module, separate
PR; and the playlist-level overview page itself, which this unblocks but does
not include.

## Acceptance criteria

1. Two playlists with identical names and different codes: both load from
   disk, both import via share code, both appear in every selector (labels
   disambiguated), and each resolves correctly at `/playlists/{code}`.
2. Importing a playlist whose *name* matches an existing one succeeds; only a
   duplicate *code* is refused, with a user-visible message in the import flow
   (not just a log line).
3. No name-keyed access to `playlist_database` remains (`rg` for the old
   lookup names comes back empty).
4. Existing user playlist files load with zero manual steps; a file without
   `code` produces one actionable warning and is skipped (today it is skipped
   with a generic invalid-JSON warning).
5. Same-named imports no longer overwrite or collide on disk.
6. A stale persisted Home-filter value (a pre-migration playlist name) does
   not crash any callback; it degrades to "no selection".
7. Full merge bar green (ruff format/check, mypy, compileall, pytest) locally
   and in CI.

## Test plan

- **Regression (the bug):** fixture dir with two same-named/different-code
  playlists → both present in `playlist_database`, both selectable,
  `get_playlist_by_code` resolves each.
- **Conflict:** two files with the same *code* → second skipped, warning
  logged; import of duplicate code refused with message.
- **Missing code:** file without `code` → skipped with actionable warning;
  rest of directory still loads.
- **File naming:** `write_playlist_data_to_file` for same-named playlists
  produces distinct filenames; round-trips through `load_playlists()`.
- **Lookup migration:** rank-overlay and journey queries by code return
  identical results to the pre-change name-based queries on a non-colliding
  fixture (behavioral parity check).
- **Home selector:** callback tests assert the filter emits codes and label
  disambiguation triggers only on collisions; a stale persisted name as the
  incoming value is handled without raising.

## Review round

Two decision points need sign-off:

1. **Duplicate-code policy** — skip-and-warn (proposed) vs last-wins.
2. **Missing-`code` policy** — the status quo already rejects codeless files
   via required-field validation; the question reduces to improving the skip
   warning (proposed) vs synthesizing fallback keys.

Everything else is mechanical once those are fixed. Suggested sequencing: land
before the playlist-level overview milestone (the overview will enumerate
playlists — it should be born code-keyed).
