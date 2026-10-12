# 2026-07-11: Match Scenario Names On Their Stripped Form

Status: Accepted

Decision: Scenario-name matching is exact on **stripped** names, and the strip
is enforced at two boundaries: the CSV run parse
(`source/kovaaks/data_service.py`, `scenario = line.split(",", 1)[1].strip()`)
and a `field_validator` on `Scenario.name` in `source/kovaaks/data_models.py`.
The model validator normalizes every path that builds a `Scenario` — runtime
share-code import, bundled/user playlist file load
(`PlaylistData.model_validate_json`), and the benchmark importer's output —
so a playlist scenario name always joins `kovaaks_database` (which is keyed by
the CSV-stripped names) under the same key. The validator is lenient on an
empty result (a whitespace-only name becomes `""` rather than raising, unlike
the sibling `code` validator) because a blank scenario name is an odd upstream
quirk, not a store key, and must not reject the whole playlist import.

Why: Every scenario lookup is exact-match — `is_scenario_in_database` (dict
membership), `get_rank_data_from_playlist_code` (`!=` compare),
`get_scenarios_from_playlist_code` (verbatim) — while `kovaaks_database` keys
are always stripped. A padded name from the KovaaK's playlist API therefore
never resolved local runs / PB / rank overlays. Padding is observed, not
hypothetical: PR #97 found real corpus files with one- and five-space paddings
from the KovaaK's benchmark API. The model boundary was chosen over a call-site
strip (which would fix only one of the three entry points — the #97
whack-a-mole) and over normalize-at-lookup (which would spread the invariant
across every comparison and dict lookup); it is a single choke point that
mirrors the existing `PlaylistData.strip_and_require_code` precedent.

Consequences: The two enforcement points must agree — drift between the CSV
parse strip and the `Scenario.name` validator silently recreates this bug
class, so a future change to the normalization strategy must update both
together (a shared `normalize_scenario_name()` helper was considered and
declined as premature; this entry is the cheaper drift guard). Nothing bakes
the association in: `kovaaks_database` is rebuilt from CSVs each startup and the
validator re-runs on every playlist file load, so the match key is re-derived
at runtime on both sides and changing strategy re-keys everything on the next
startup. Name-keyed persisted caches (leaderboard-id / rank) tolerate a
strategy change by design — a miss refetches, bounded by the 168 h TTLs. The
only one-way loss is that imported playlist JSON persists the stripped name,
discarding original padding (semantically void whitespace, recoverable by
re-import from the code). The benchmark importer's own `.strip()` at
`scripts/benchmark_importer/script.py` is now redundant defense-in-depth and is
left in place. Shipped in PR #100.
