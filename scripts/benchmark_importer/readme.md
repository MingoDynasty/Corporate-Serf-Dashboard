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
4. Manually copy reviewed output to `resources/playlists/generated/`.
5. Copy the benchmarks you want the app to load from there into
   `data/playlists/`, then restart the app.

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
  (default: 3).

Evxl also publishes its
[API documentation](https://api.evxl.app/documentation).
