# RefleK's Research Findings

Learnings from a survey of [ARm8-2/refleks](https://github.com/ARm8-2/refleks)
(surveyed 2026-07-03 at commit `1f31c96`), a KovaaK's analytics app in the same
domain as this dashboard. File references below are paths inside the refleks
repo unless prefixed with `source/` or `docs/`.

**License caveat:** refleks is GPL-3.0. Concepts, file-format knowledge, and
API observations are free to use; verbatim code is not (this project is not
GPL). Everything below is described at the idea/format level for that reason.

## What refleks is

A Windows desktop app (Go + Wails backend, React/TypeScript frontend). It polls
the KovaaK's stats directory, converts each run into a self-contained versioned
`.refleks` file (stats CSV data + performance time-series + raw mouse trace +
environment snapshot), and builds session, benchmark, and per-run analytics on
top. Optional cloud sync of run files.

## Data sources we are not using

### 1. `.perf` performance files (unread by us today)

Alongside `stats/*.csv`, KovaaK's writes
`FPSAimTrainer/performances/<scenario> - Challenge - <timestamp> Performance.perf`
— a protobuf-encoded time-series of within-run events. Refleks decodes it with
low-level protowire parsing (`internal/runs/kovaaks/performances.go`); the
reverse-engineered schema:

Top-level message:

| Field | Content |
| --- | --- |
| 1 | Header: scenario name (1), scenario hash (2), challenge start UTC (3), schema version (4), challenge profile snapshot (5: time limit, player profile, bots, map, timescale, ...) |
| 2 | Repeated event: timestamp float32 (1) + one payload field |

Event payload fields (each an embedded message; counts are varint field 1,
floats are fixed32 field 1):

| Field | Payload | Kind |
| --- | --- | --- |
| 2 | shotsFired | count |
| 3 | shotsHit | count |
| 4 | shotsMissed | count |
| 5 | damageDone | delta |
| 6 | damagePossible | delta |
| 7 | score | delta |
| 8 | kills | count |
| 9 | deaths | count |
| 10 | overshots | count |
| 11 | playerDamageTaken | delta |
| 12 | reloads | count |
| 13 | pauseCount | count |
| 14 | distanceTraveled | delta |
| 15 | mbsPoints | delta |
| 16 | targetSize | value |
| 17 | targetSpeed | value |
| 18 | randomSensScale | value |

This unlocks *within-run* progression plots (score/accuracy over the course of
a 60s run). Refleks bundles sample `.perf` files under
`testdata/FPSAimTrainer/performances/` usable as parser fixtures.

### 2. Per-kill event rows in the stats CSVs (we parse only summaries)

Each stats CSV contains a kill table before the `key:,value` summary section.
Columns: kill index, timestamp (`HH:MM:SS[.ffffff]`), bot, weapon, TTK
(`"...s"` suffix), shots, hits, accuracy, damage done, damage possible,
efficiency, cheated, overshots. Refleks detects these rows structurally (first
cell integer + second cell `NN:NN:NN`-shaped) rather than by section headers.

From this alone (`frontend/src/features/history/lib/scenarioAnalysis.ts`) they
derive: real-TTK series, 5-kill moving average with linear-regression slope and
R² (fatigue/warm-up within a run), cumulative accuracy over time, per-kill
accuracy, kills-per-minute, TTK percentiles (p10/p90/median/stddev), longest
no-kill gap, and KPM-vs-accuracy Pearson correlation. All new signal from files
we already ingest — [data_service.py](../source/kovaaks/data_service.py)
currently reads only the summary/weapon sections.

Day-boundary handling: kill timestamps are time-of-day only; deltas that go
negative are corrected by adding 86400s (run crossing midnight).

### 3. Stats CSV encoding robustness

Refleks's reader handles UTF-8 BOM and UTF-16 LE/BE, implying KovaaK's
sometimes emits non-UTF-8 files. Their detection order:

1. UTF-8 BOM (`EF BB BF`) → skip BOM.
2. UTF-16 BOM (`FF FE` / `FE FF`) → decode UTF-16 LE/BE.
3. Heuristic: if null bytes exceed 1/8 of the first 512 bytes, treat as
   BOM-less UTF-16; more nulls at odd offsets → LE, else BE.

We open with plain `encoding="utf-8"`
([data_service.py:395](../source/kovaaks/data_service.py)), which would raise
on such a file.

## KovaaK's API learnings

### 4. Endpoint not in our notes: last scores by name

```text
GET /webapp-backend/user/scenario/last-scores/by-name?username=<name>&scenarioName=<scenario>
```

Recent scores for one user on one scenario. Refleks calls it with the Steam
*persona name* (`internal/scenarios/service.go`). Candidate addition to
[kovaaks_api_notes.md](kovaaks_api_notes.md) even if unused.

### 5. Response shape of `/benchmarks/player-progress-rank-benchmark`

Our notes list this endpoint but not its shape. From refleks's parser
(`internal/benchmarks/progress_parser.go`):

- Keyed by `benchmarkId` + `steamId` (not username).
- Per scenario (under `categories.*.scenarios.<name>`): `score` — **scaled
  ×100, divide by 100**; `scenario_rank` (int index); `rank_maxes` (ascending
  per-rank score thresholds).
- Top level: `ranks` (name + color; a "No Rank" entry they filter out),
  `overall_rank`, `benchmark_progress`.

So KovaaK's itself serves per-scenario rank thresholds here — a cross-check
for the benchmark importer's threshold data.

They also refresh benchmark progress event-driven: when a newly ingested run
beats the cached score for a scenario belonging to a benchmark, only affected
benchmarks are re-fetched (`internal/benchmarks/service.go`,
`CheckAndRefreshIfNeeded`) — same shape as our rank-freshness timer chain,
applied to benchmarks.

### 6. SteamID auto-detection from Steam's `loginusers.vdf`

Refleks resolves the SteamID64 and PersonaName by parsing
`<steam>/config/loginusers.vdf` for the entry with `MostRecent = 1`
(`internal/steam/steam.go`), with priority: settings override → env var →
vdf parse. Since our rank lookups already prefer exact `steamId` matching,
auto-detecting it would remove the `kovaaks_username` config friction and the
fuzziness of `usernameSearch`.

## Feature ideas (concepts, not code)

### Sessions as a first-class analytics unit

Runs grouped into sessions by inactivity gap (default 20 min, configurable).
Per-session widgets: active playtime (sum of run durations), unique scenario
count, average score, top repeated scenario, and per-scenario trend vs the
*previous* session. Plus streak analytics: daily playtime, streak spans,
hourly/weekly activity histograms (`frontend/src/features/overview/lib/streakActivity.ts`).
We have the cumulative journey plot but no session concept; this is a natural
next analytics layer.

### Bounded startup catch-up

On startup refleks does *not* ingest every historical file: it takes runs from
the last 90 days with a floor of the newest 1500 runs, newest first, in a
background goroutine; everything else is marked seen and skipped
(`internal/watcher/watcher.go`). Our `initialize_kovaaks_data` loads every CSV
synchronously — a real startup cost for a years-old stats folder. A
"recent-first, backfill in background" variant would keep full-history views
(journey plot) intact.

### "What to train" recommendations

Cheap heuristics, no ML (`frontend/src/features/benchmarks/lib/recommendations.ts`):

- Benchmark-level score: maxed = 5 (maintenance), brand-new = 50, in-progress
  = 60 + 30 × completion, next-difficulty-unlocked = 70.
- Plus a *deterministic daily jitter* (hash of name + date, 0–5) so ties break
  differently each day without feeling random within a day.
- Beginner boost for starter benchmarks (Voltaic S5, Viscose) when the user
  has fewer than 10 sessions.
- Normalize 0–100, pick 2–5 above a threshold.

A per-scenario variant inside a benchmark weighs closeness to next rank-up,
recency-weighted score slope, and volatility
(`frontend/src/features/benchmarks/lib/detailRecommendations.ts`).

### Benchmark "energy" calculation

Voltaic-style energy: linear interpolation between adjacent rank thresholds,
100 energy per rank step, benchmark-specific variants (`vt-energy`, `ra-s5`)
under `internal/benchmarks/rankcalc/`. They prepend a synthetic baseline
threshold below the first rank (first threshold minus the average inter-rank
delta) so sub-first-rank progress renders sensibly.

### cm/360 yaw table

Sens-scale → yaw constants sourced from KovaaK's own `FovSensConfig.json`
(`internal/constants/defaults.go`), with non-linear scales (Splitgate,
Paladins, PUBG, Battlefield, GTA 5) deliberately excluded. Formula for linear
engines: `cm/360 = 360 / (dpi × sens × yaw) × 2.54`. Notable values: Source
family 0.022; Overwatch family 0.0066; Valorant 0.06996; Halo 0.022222;
Fortnite 0.005555; Siege/Reflex Arena 0.018/π. Ready-made reference if we ever
normalize sensitivity across scales; regenerate from `FovSensConfig.json` in
the local KovaaK's install rather than copying their constants.

### Ingest-time enrichments

Computed once per run at ingest (`internal/runs/ingest.go`):

- Accuracy = hits / (hits + misses) from summary counts.
- Real average TTK from consecutive kill-event timestamp deltas.
- Run duration from a derived window: `Challenge Start` time-of-day mapped
  onto the filename date (fallback: first kill event; fallback: end − 60s),
  with day-rollover correction.
- cm/360 from sens scale + DPI via the yaw table.

### Out of scope but notable: raw mouse-trace analysis

Their headline feature: Windows Raw Input capture at 125 Hz into a ring buffer
(2 min), started/stopped by polling for the `FPSAimTrainer.exe` process every
3s, sliced per run window and stored with the run. Per-kill overshoot/
undershoot classification (path efficiency, crossing counts, corrections,
clicked-while-moving) feeds a concrete "train at X cm/360 for 3–10 runs"
suggestion, gated on confidence (≥4 kills, average confidence ≥ 0.42,
ambiguous over/under mix suppressed) and capped at ±3–30% change
(`frontend/src/features/history/lib/mouseAnalysis.ts`). They also snapshot the
run environment (OS, CPU, app version, mouse VID/PID/name, sample rate).
Impressive, but requires native input hooks — a heavy lift for a Dash app.

## Engineering patterns observed

- **Watcher**: 5s directory polling with a seen-set and store-level duplicate
  check, instead of filesystem events. More robust to editor/AV quirks, but
  our watchdog approach works — not worth switching. A generation counter
  cancels stale background catch-ups after config changes.
- **Benchmark catalog fetch**: ETag-based conditional GET with an embedded
  fallback JSON compiled into the binary — offline-first. Our JSON cache uses
  TTLs; ETag is a refinement where an API supports it.
- **Self-contained run archive** (`.refleks`, versioned codec) + optional
  cloud sync. Our in-memory + raw CSV approach is simpler and fine.

## Suggested next steps (cheapest first)

1. Document the two API findings (last-scores endpoint; progress endpoint
   response shape and ×100 score scaling) in
   [kovaaks_api_notes.md](kovaaks_api_notes.md).
2. Harden stats CSV reading against UTF-16/BOM encodings in
   `data_service.py`.
3. Proposal: parse kill-event rows → within-run analytics (TTK trend,
   accuracy-over-time) on the home page.
4. Proposal: session grouping (20-min gap) + session summary view.
5. Larger: `.perf` parsing (needs a Python protobuf/protowire reader),
   SteamID auto-detection from `loginusers.vdf`, startup catch-up policy.
