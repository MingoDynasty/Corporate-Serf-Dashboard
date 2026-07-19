# Benchmark Importer

Imports benchmarks by combining upstream Evxl metadata with KovaaK's rank
thresholds.

## Glossary

- A **playlist** is a scenario list without rank data. This is what the app's
  Import Playlist flow produces.
- A **benchmark** is a playlist plus rank thresholds and colors. Benchmarks are
  the only files this script produces.

## Pipeline

1. Unless `--offline` is set, validate the live
   [Evxl benchmarks data](https://evxl.app/data/benchmarks) and atomically
   refresh `resources/evxl/benchmarks.json`. A live candidate that removes any
   existing sharecode is rejected unless `--accept-removals` is set.
2. Resolve each playlist name and code through Evxl, fetch its rank thresholds
   from KovaaK's, and merge the data.
3. Write benchmark JSON to `scripts/benchmark_importer/generated/`, with
   provenance in each file and resume state in `generated/manifest.json`.
4. Manually copy reviewed output to `resources/benchmarks/` — the app scans
   that whole directory at startup. No per-benchmark activation copies:
   which benchmarks the user sees is a show/hide preference managed on the
   app's Playlists page ("Show hidden" reveals new arrivals).

Run from the repository root:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run python scripts/benchmark_importer/script.py
```

## Options

- `--offline` skips the live Evxl refresh and uses the local snapshot.
- `--force` ignores resume state and bypasses the KovaaK's benchmark cache.
- `--accept-removals` accepts the whole live Evxl candidate when it removes
  sharecodes.
- `--only SHARECODE` imports one sharecode; repeat the flag for more than one.
- `--limit N` stops after generating N benchmarks.
- `--max-consecutive-failures N` changes the circuit-breaker threshold
  (default: 3). Only *transient* failures count toward it — see below.

## Failure handling

Per-item failures are classified, because the two kinds want opposite
treatment:

- **Transient** — KovaaK's 5xx responses, rate limiting (429), connection
  errors, and timeouts. These count toward the `--max-consecutive-failures`
  circuit breaker, which aborts the sweep when the API is down entirely rather
  than grinding through every sharecode.
- **Deterministic** — a rank-count mismatch between Evxl and KovaaK's, a
  schema-invalid response, or a 4xx other than 429. These recur on every
  attempt because the upstream *data* is wrong, so they never touch the
  breaker.

Deterministic failures are recorded in `generated/failures.json`, a ledger
mapping sharecode to the error, the UTC timestamp when it was recorded, and
the Evxl metadata (benchmark id and rank ladder) the failure was recorded
against. Later sweeps skip recorded sharecodes before making any network call
and report them in the run summary's known-bad bucket. A skip is informational
and does not affect the exit code — the failure was already reported by the
run that recorded it.

A recorded verdict is a statement about specific upstream data, so it expires
when that data changes: if Evxl's benchmark id or rank ladder for the
sharecode no longer matches what was recorded, the item is retried
automatically. That is what makes the ledger self-healing — when Evxl fixes
one of these data bugs, the next snapshot refresh flows the correction in
without anyone remembering to clear the entry.

The one case this cannot detect is a fix on the KovaaK's side (say, its
benchmark API starting to return the full rank ladder) while Evxl's metadata
stays byte-identical. Use `--force` or `--only SHARECODE` to retry then.

To retry a recorded sharecode explicitly, name it with `--only SHARECODE`
(explicitly naming a code always attempts it) or run with `--force` (which
attempts everything). A retry that succeeds clears the entry; one that fails
deterministically again refreshes it. Transient failures are never recorded.

Entries are only consulted for sharecodes still present in the Evxl snapshot,
so a code that later leaves the snapshot just becomes dead weight in the file;
delete `failures.json` at any time to clear the whole ledger.

Evxl also publishes its
[API documentation](https://api.evxl.app/documentation).
