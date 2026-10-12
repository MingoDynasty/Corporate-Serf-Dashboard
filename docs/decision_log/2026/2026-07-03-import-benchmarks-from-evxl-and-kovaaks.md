# 2026-07-03: Import Benchmarks From Evxl And KovaaK's

Status: Accepted (amended by
[2026-09-26](#2026-09-26-a-read-only-check-finds-bundled-benchmarks-that-kovaaks-changed):
KovaaK's threshold and scenario changes under an unchanged benchmark ID are
now found by the importer's read-only drift check, which names the files a
forced refresh regenerates)

Decision: The benchmark importer uses Evxl to resolve playlist names and codes,
and KovaaK's to fetch benchmark rank thresholds. In project terminology, a
*playlist* is a bare scenario list without rank data; a *benchmark* is a
playlist plus rank thresholds and colors. Generated benchmark JSON carries a
`generated_from` provenance stamp containing the Evxl sharecode, KovaaK's
benchmark ID, ordered rank-color pairs, generation timestamp, and generator
name.

Why: KovaaK's playlist search cannot resolve every known sharecode, while Evxl's
exact-code endpoint can; Evxl does not expose the per-scenario rank thresholds,
so KovaaK's remains authoritative for those values. The terminology distinguishes
the app's playlist import from the richer files produced by the importer.
Provenance makes the upstream inputs inspectable and allows generated files to be
checked for stale or mismatched benchmark metadata.

Consequences: Keep Evxl-specific resolution and snapshot handling in
`scripts/benchmark_importer/` unless an app-side feature explicitly adopts that
dependency. Preserve rank-color order when comparing provenance because colors
pair positionally with KovaaK's thresholds. Conflicting duplicate Evxl
sharecodes must be skipped and reported rather than resolved first-wins because
a missing benchmark is visible and recoverable, while silently pairing the wrong
rank thresholds is not. KovaaK's threshold changes under an unchanged benchmark
ID remain invisible to provenance checks and require an explicit forced refresh.
