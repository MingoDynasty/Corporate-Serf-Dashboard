# 2026-09-26: A Read-Only Check Finds Bundled Benchmarks That KovaaK's Changed

Status: Accepted

The importer regenerates a bundled benchmark only when Evxl's listing of it
changes, so when KovaaK's moved a benchmark's rank thresholds or swapped a
scenario underneath, the file went stale silently and showed players wrong
rank badges. The importer now has a read-only check that rebuilds every
bundled benchmark from live data and names the files that differ. Each
refresh runs the check and regenerates the files it names. Nothing runs on its
own.

**The rule.** Drift is found by `scripts/benchmark_importer/script.py
--check`, run by hand in each refresh before anything is regenerated (the
importer readme's refresh runbook). It is decided by whole-model equality
between `PlaylistData.model_validate` of the shipped file and
`build_playlist(sharecode, item, use_cache=False)`, the importer's own
fetch-and-merge, over the committed Evxl snapshot. Regeneration still keys on
Evxl metadata: a normal run's manifest skip is unchanged, and the check only
names the sharecodes, printing a ready-to-paste
`--offline --force --only ...` line for them.

- **Whole model, not a field diff.** A field-by-field diff passes any field
  added to the models later, and scenarios matched by name collapse when a
  name repeats. `describe_drift` explains a drifted file for the summary and
  never decides; a difference it can't describe still counts. The
  `generated_from` stamp is not a model field, so it never reads as drift:
  over all 257 files, validating the shipped payload with and without it
  gives equal models.
- **Live KovaaK's, committed Evxl.** The KovaaK's fetch passes
  `use_cache=False`, because the benchmark cache can hold the very payload
  the file was built from. The Evxl snapshot is never refreshed, which keeps
  the check read-only (its only write is the benchmark cache) and leaves
  Evxl-side changes to the runbook's first step. The playlist name and code
  still come from Evxl's live playlist-by-code endpoint, as in every run.
- **Keyed by provenance.** A file is matched to the snapshot by
  `generated_from.sharecode`, never by `code` or filename: one bundled file's
  `code` differs from its sharecode in casing.
- **Nothing reads as clean by accident.** Every file lands in identical,
  drifted, failed, or not checked, and the exit code is 0 only when all of
  them matched. A deterministic or transient rebuild failure, a sharecode
  missing from the snapshot, and a conflicting duplicate all fail; a tripped
  circuit breaker lists the unvisited files as not checked. Failed and
  not-checked files never appear on the paste line, because regeneration
  can't fix them.

**Evidence.** The limit was recorded from the start: the
[2026-07-03 entry](#2026-07-03-import-benchmarks-from-evxl-and-kovaaks)'s last
consequence says threshold changes under an unchanged benchmark ID need an
explicit forced refresh. Iron Pipe #1 (benchmark 2757) drifted that way and
was caught in PR #289 only because Evxl's `scenarioCount` happened to change.
A one-off script then rebuilt all 253 files live on 2026-09-15 in 3.8 minutes
wall clock: 248 identical, 5 drifted, 0 failed, with no name, code, order,
leaderboard-ID, or rank-ladder drift anywhere. PR #293 regenerated the five
with `--offline --force --only`:

| File | Benchmark ID | Drift |
|---|---|---|
| Pasu Track DOJO | 880 | 8 scenarios rebalanced, lower tiers dropped a lot (`Pasu Track Extrasmooth TE` 7000 → 5525) |
| Ground Track DOJO | 977 | 6 scenarios rebalanced, all tiers lowered (`DeceptiveStrafes` 2600 → 1550) |
| Jade Palace Ground Benchmark - Hard | 959 | 7 scenarios, small threshold moves |
| IRON PIPE AIM PLAYLIST #2 | 2789 | `TSK - SYW` swapped for `SYW (Smooth Your Wrist) Truly FIXED` (leaderboard ID 13150); `VAI 314 TE` −100 per tier |
| AimSpeed Benchmarks 2 Easy | 2168 | `Skeet Tracking Goated Easy` +200 per tier |

The shipping PR's first full `--check` on 2026-09-26 took 3.9 minutes wall
clock over 257 files: 252 identical, 5 drifted, 0 failed, 0 not checked. All
five matched KovaaK's on 2026-09-15: the three older files were identical in
the one-off rebuild, and PR #294 generated the two AIMCORE files live that
day.

| File | Benchmark ID | Drift |
|---|---|---|
| AIMCORE Benchmarks S1 - Harder | 2892 | thresholds in 3 of 18 scenarios |
| AIMCORE Benchmarks S1 - Medium | 2891 | thresholds in 1 of 18 scenarios (`AC WideShot` 47 → 50 first tier) |
| Peter Ground Technology | 2884 | `MLSI demotori hard` swapped for `MLSI demotori hard v2` |
| Underaim-Benchmark | 2942 | thresholds in 13 of 14 scenarios |
| XYZ SMOOTHNESS BENCHMARKS V2 | 2450 | thresholds in all 15 scenarios |

Regenerating them is a separate refresh PR, not part of shipping the check.

**Rejected.**

- Detecting drift inside normal runs, for example with a digest of the
  KovaaK's payload in the provenance stamp: it needs a live fetch for every
  benchmark on every run, discarding the cache that keeps reruns cheap.
- A blanket `--force` sweep: it rewrites `generated_at` in every file and
  buries a handful of real changes in a 257-file diff.
- A scheduled CI job: more infrastructure than a four-minute manual step
  needs.

**Consequences.** A refresh PR runs the check before regenerating anything,
and regenerates only the drifted sharecodes among the files already bundled. The refresh procedure, which lived only in the bodies of
PRs #289, #293, #294, and #297, is now the importer readme's runbook, written
in tracked commands. The check stays manual, so drift that lands between
refreshes ships until the next one.

Provenance: the maintainer revived the shelved idea on 2026-09-26;
claude-fable-5-1 and claude-opus-5-5 converged on this design and the
maintainer accepted it as the kickoff basis the same day. Shipped in PR #311.
