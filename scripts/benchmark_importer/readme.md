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
   existing sharecode is rejected unless `--accept-removals` is set. The app
   reads this snapshot too, for the benchmark and difficulty names behind a
   benchmark page's "View on Evxl" link, so a committed refresh changes those
   links
   ([decision log](../../docs/decision_log.md#2026-10-04-a-benchmarks-scenario-page-links-to-its-evxl-page)).
2. Resolve each playlist name and code through Evxl, fetch its rank thresholds
   from KovaaK's, and merge the data.
3. Write benchmark JSON to `scripts/benchmark_importer/generated/`, with
   provenance in each file and resume state in `generated/manifest.json`.
4. Manually copy reviewed output to `resources/benchmarks/` — the app scans
   that whole directory at startup. No per-benchmark activation copies:
   which benchmarks the user sees is a show/hide preference managed on the
   app's Playlists page ("Show hidden" reveals new arrivals). Which
   sharecodes belong there is a maintainer rule the script does not enforce:
   Evxl's listed, non-hidden benchmarks, with delisted files removed
   ([decision log](../../docs/decision_log.md#2026-09-15-the-bundled-corpus-is-evxls-listed-non-hidden-benchmarks)).

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
- `--check` rebuilds every bundled benchmark from live data and reports the
  ones that differ, without writing any benchmark file — see
  [Drift check](#drift-check). It uses the local snapshot, as `--offline`
  does, and refuses `--force`, `--limit`, and `--accept-removals`.

## Failure handling

Per-item failures are classified, because the two kinds want opposite
treatment:

- **Transient** — KovaaK's 5xx responses, rate limiting (429), connection
  errors, and timeouts. These count toward the `--max-consecutive-failures`
  circuit breaker, which aborts the sweep when the API is down entirely rather
  than grinding through every sharecode.
- **Deterministic** — a rank-count mismatch between Evxl and KovaaK's, a
  benchmark that returns no scenarios at all, a schema-invalid response, or a
  4xx other than 429. These recur on every attempt because the upstream *data*
  is wrong, so they never touch the breaker.

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

Automatic expiry cannot detect a fix on the KovaaK's side (say, its benchmark
API starting to return the full rank ladder) while Evxl's metadata stays
byte-identical. Retry explicitly for that case.

To retry a recorded sharecode explicitly, name it with `--only SHARECODE` or
run with `--force` (which attempts everything). Naming a recorded sharecode is
treated as retry intent, so it overrides the two things that would otherwise
replay the failure: the manifest skip (an intact older output no longer causes
an early return) and the KovaaK's benchmark cache (the response is refetched,
since a cached rank-mismatch response is schema-valid and would reproduce the
same mismatch forever). A retry that succeeds clears the entry; one that fails
deterministically again refreshes it. Transient failures are never recorded.

This retry override applies only to sharecodes in the ledger. `--only` on a
healthy sharecode keeps its ordinary meaning — restrict the sweep — and an
intact, current output is still skipped; use `--force` to regenerate that.

Entries are only consulted for sharecodes still present in the Evxl snapshot,
so a code that later leaves the snapshot just becomes dead weight in the file;
delete `failures.json` at any time to clear the whole ledger.

## Drift check

A normal run regenerates a benchmark only when its Evxl metadata (benchmark
id and rank ladder) changes. KovaaK's can move a benchmark's thresholds or
swap a scenario while Evxl's entry stays byte-identical, and neither side
publishes a signal for that, so the bundled file goes stale silently and the
app draws wrong rank badges from it. `--check` finds those files:

```powershell
uv run python scripts/benchmark_importer/script.py --check
```

For each file in `resources/benchmarks/`, in filename order, it rebuilds the
benchmark the way a run does (the playlist name and code from Evxl's
playlist-by-code endpoint, the rank ladder from the snapshot, thresholds and
leaderboard ids from KovaaK's) and compares the result with the shipped file.
A file is matched to the snapshot by its `generated_from.sharecode`, never by
`code` or filename, which can differ from it in casing. The comparison covers
the whole benchmark (name, code, scenarios and their order, thresholds, rank
names and colors, leaderboard ids) and ignores the provenance stamp.

- The KovaaK's fetch is always live. The benchmark cache can hold the very
  payload the bundled file was built from, and a rebuild from it would match
  by construction. Each fetch still rewrites the cache under
  `data/cache/benchmarks/`, which is the check's only write: it never touches
  `generated/`, the manifest, or the failure ledger.
- It compares against the snapshot on disk and never refreshes it, so
  Evxl-side changes (new, changed, or delisted sharecodes) are the first step
  of a [refresh](#refresh-runbook), not the check's job. `--offline` alongside
  it is accepted and redundant.
- `--only SHARECODE` narrows it to the named sharecodes, and
  `--max-consecutive-failures` works as in a normal run.

Every visited file lands in one bucket:

- **identical**: rebuilt and matched.
- **drifted**: rebuilt and different. The summary lists each drifted file with
  an account of what changed: name or code, scenarios added or removed,
  scenario order, and which scenarios' thresholds, leaderboard ids, or rank
  ladder moved. The account is best effort; the verdict is whole-benchmark
  inequality, so a difference the account doesn't cover is still reported as
  drift.
- **failed**: the file couldn't be compared. Either the rebuild failed,
  labelled deterministic or transient as in
  [Failure handling](#failure-handling), or the file couldn't be looked up: no
  provenance sharecode, a sharecode the snapshot no longer lists (a delisted
  benchmark), or a conflicting duplicate. An `--only` code that no bundled
  file carries fails too. A bundled file that no longer builds is stale
  either way.
- **not checked**: files the circuit breaker left unvisited, so a run cut
  short never reads as clean.

The exit code is 0 only when every file was rebuilt and matched. When
anything drifted, the summary ends with a ready-to-paste command that
regenerates exactly the drifted sharecodes into `generated/`:

```text
uv run python scripts/benchmark_importer/script.py --offline --force --only SHARECODE_A --only SHARECODE_B
```

Failed and not-checked files never appear on that line, because regenerating
can't fix a file that doesn't build or was never compared. The whole corpus
takes about four minutes.

## Refresh runbook

A refresh brings `resources/benchmarks/` up to date with Evxl and KovaaK's in
one PR. Run every command from the repository root with
`$env:UV_CACHE_DIR='.uv-cache'` set.

1. **See what changed on Evxl before generating anything.** Refresh the
   snapshot on its own:

   ```powershell
   uv run python -c "from scripts.benchmark_importer import script; script.refresh_evxl_snapshot()"
   ```

   It logs `Evxl data unchanged`; or writes the snapshot and logs the added,
   changed, and removed counts; or, when the live data removes sharecodes,
   logs a warning naming them and writes nothing. A rejected candidate leaves
   no diff to judge its removals by, so rerun with
   `script.refresh_evxl_snapshot(accept_removals=True)` to write it; the
   snapshot is tracked, so `git restore resources/evxl/benchmarks.json` backs
   out a candidate whose removals aren't real. Either way, read
   `git diff resources/evxl/benchmarks.json`. A re-code shows as a changed
   `sharecode` under an unchanged `kovaaksBenchmarkId`, and is a real removal.
   A refresh that should carry no snapshot change skips this step.
2. **Apply the membership rule**
   ([decision log](../../docs/decision_log.md#2026-09-15-the-bundled-corpus-is-evxls-listed-non-hidden-benchmarks)):
   import the listed, non-hidden sharecodes that aren't bundled yet, delete
   the files of delisted ones, and leave hidden ones out. The snapshot diff
   shows all three; `git grep -l SHARECODE resources/benchmarks` finds a
   sharecode's bundled file. The importer doesn't filter `hidden` itself, so
   curation is by `--only`.
3. **Find drift.** Run `--check`, then regenerate the drifted sharecodes with
   the line it prints, and carry its per-file account into the PR body. The
   printed line leaves out failed and not-checked files, so rerun transient
   failures, and any files a circuit-breaker abort left not checked, with
   `--check --only`; after an early abort, a full rerun is simpler. A
   deterministic failure means the upstream data no longer builds, which
   needs a look before anything replaces the bundled file.
4. **Generate the new sharecodes** with `--only`, one flag per code. Add
   `--offline` so the run uses the snapshot as reviewed in step 1 (or as
   committed, when the snapshot must stay out of the PR) instead of refreshing
   it again.
5. **Check each generated file before copying it:**
   - Its filename doesn't collide, case-folded, with another benchmark's
     bundled file, which a copy would silently overwrite on Windows. A
     regenerated file should land under its own bundled filename; if Evxl
     renamed the playlist, delete the old file in the same PR.
   - A new file's sharecode and benchmark id aren't already in the corpus
     (`git grep` them in `resources/benchmarks`). A hit means an existing
     benchmark under a new code.
   - Its scenario count equals the sum of `scenarioCount` over its
     difficulty's subcategories in the snapshot.
   - Its rank ladder matches the snapshot's `rankColors`, both in
     `generated_from.rank_colors` and on every scenario.
   - Every scenario carries a `leaderboard_id`.
6. **Land it.** Copy this refresh's files into `resources/benchmarks/`
   (`generated/` is local staging and keeps earlier sessions' output too).
   Update the file count in
   [docs/specs/playlists.md](../../docs/specs/playlists.md), and stage new
   files intent-to-add (`git add -N resources/benchmarks`) so the
   committed-corpus tests, which list files through `git ls-files`, see them.
   Run the gates. `--check --only` over the regenerated and new sharecodes
   should now report them identical. Start the app once and confirm that
   `data/logs/debug.log` reports `Playlist startup load complete` with the new
   bundled count and `warnings=0`.

Evxl also publishes its
[API documentation](https://api.evxl.app/documentation).
