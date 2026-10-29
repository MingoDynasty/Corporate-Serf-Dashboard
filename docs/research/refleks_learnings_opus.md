# Lessons from RefleK's

Date: 2026-10-28
Author: claude-opus-5-5 · effort: xhigh

Research note; recommendations remain unratified. It supersedes the survey
of 2026-07-03. The last section lists what that survey got wrong and what
has changed since.

## Takeaway

Since July, RefleK's has grown in directions this app has chosen not to
take: native capture of the mouse and the screen, training advice, and
uploading every run to its own server by default. Most of what the July
survey proposed taking has shipped here since, built differently and in most
cases more carefully: sessions, reading the `.perf` file, and finding the
player's Steam account. What is left to learn is narrower. Two analytics
ideas fit open questions here: a read of how the whole session compares with
usual play, and a calendar of time spent. The rest is groundwork: a recipe
for putting a run's kills and its `.perf` events on one clock, tests against
real stats files, three gaps in our API notes, and a reduced-motion rule.
RefleK's also shows by example the honesty failures our principles rule out,
chief among them presenting missing evidence as an all-clear.

## Evidence and scope

- Inspected RefleK's at [`e1ef943`][rk], the head of `main` on 2026-10-28.
  It was committed on 2026-10-15, after release 0.10.0 of 2026-09-12. Paths
  cited as `path:line` are at that revision.
- The July survey's commit, `1f31c96`, is no longer in the repository,
  because `main` keeps one squashed commit per release. The July text places
  it between 0.8.3 (2026-05-08) and 0.9.0 (2026-08-01). **New** below means
  absent from the July note, not proven absent from July's snapshot. Several
  surfaces this note describes for the first time already existed at 0.8.3.
- The GitHub release notes are empty, so the release timeline comes from the
  project's [changelog page](https://refleksapp.com/changelog/), fetched
  2026-10-28.
- Compared against this repository at `911ca00`.
- The code was read in five passes split by area: ingest and file formats;
  the KovaaK's API, Steam and rank math; analytics surfaces; mouse trace and
  replay; and engineering practice. The claims the recommendations rest on
  were re-read by hand. A statement here was read in code unless it is
  marked as inferred.
- **Local verification:** read-only scans of all 9,261 stats files in the
  maintainer's install, dated 2019-07-14 to 2026-10-27, for encoding, line
  endings, and the shape of the kill table. This app's `.perf` reader was
  run on RefleK's two `.perf` fixtures. The scripts are not kept in the
  repository.
- **Not done:** RefleK's was not built or run. Nothing was sent to its
  server or to KovaaK's, so the score scaling in finding 6 is RefleK's
  reading, not a probe.
- **License:** RefleK's is GPL-3.0. Concepts, file-format knowledge, and API
  observations are free to use; its code is not copied or ported here. This
  project is AGPL-3.0, whose section 13 permits combining with GPL-3.0 work,
  but a file taken from RefleK's would stay GPL-3.0 and need recording like
  the vendored assets (see the
  [AGPL decision](../decision_log/2026/2026-08-10-the-project-is-agpl-30-and-contributors-sign-nothing.md)).
  This tree keeps its own code under one license, so everything below is
  described at the level of ideas and formats.

## What RefleK's is now

A Windows desktop app with a Go backend (Wails) and a React frontend. It
watches the stats folder, pairs each stats file with its `.perf` file, and
stores each run as a `.refleks` archive: the stats, the `.perf` data, a raw
mouse trace, and a snapshot of the PC, zstd-compressed and checksummed
(format version 2, `internal/runs/codec.go:18-200`). Since July it has
added:

- video replay of each run, recorded with a bundled FFmpeg and off by
  default (0.9.0), with storage limits and cleanup (0.9.4, 0.9.5);
- "target inference", which guesses where targets were from the mouse trace
  and the `.perf` hit counts (0.9.0);
- a redesigned over- and undershoot analysis with a sensitivity suggestion
  (0.9.0);
- an interface scale (0.9.6), six interface languages, a user-editable
  theme, and detection of the Steam folder and account (0.10.0);
- 40 Go and 37 Vitest test files, written between 2026-09-13 and
  2026-10-15 and not yet in a release.

Two defaults frame the rest. Mouse tracking is on by default, and so is
uploading each completed run to the "RefleK's Index" on the project's own
server.

## Where the July suggestions stand

| July suggestion | Where it stands |
| --- | --- |
| Read the `.perf` performance files | Shipped for time-scored detection ([PR #343](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/343)). Our reader takes the header and the score ticks only |
| Parse the kill rows for within-run analysis | Not taken. The roadmap's per-bot breakdown would need them; see finding 3 |
| Read UTF-16 and BOM-prefixed stats files | No evidence it is needed: every local file is plain UTF-8, and RefleK's tests the case only with made-up bytes |
| Document the last-scores endpoint and the progress endpoint's score scaling | Not done; see finding 6 |
| Find the SteamID in `loginusers.vdf` | Shipped ([PR #191](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/191)), stronger than RefleK's: each account is checked against its KovaaK's profile |
| Group runs into sessions | Shipped with a 30-minute break ([PR #359](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/359)). RefleK's still uses 20 minutes, measured differently (finding 8) |
| Load recent runs first at startup | Not taken. RefleK's version hides older history (see What not to take) |
| "What to train" scores | Conflicts with the ratified rule that the app states verdicts, not advice |
| Benchmark energy | Not taken. RefleK's implements 2 of the 40 rank-calculation rules its catalog names |
| cm/360 yaw table | Superseded: this app converts every scale from the stats file's own `Sens Increment` ([2026-09-11](../decision_log/2026/2026-09-11-sensitivities-normalize-to-cm360-at-parse-time-from-the-files-own-increment-and-dpi.md)) |
| Ingest-time run length and cm/360 | Shipped; our run length subtracts pauses |
| Mouse-trace analysis | Not taken; it needs native input hooks |

## Findings

### 1. A read of the whole session against usual play

**Observed:** RefleK's overview has a Performance tile that says how the
current session compares with earlier play
(`frontend/src/features/overview/hooks/useRecentSessionSnapshot.ts:360-428`).

- For each run this session, the baseline is the median of that scenario's
  runs in every earlier loaded session, once it has at least three.
- Each run's difference from its baseline is clamped to ±35%. Once there
  are at least two, the tile shows their mean.
- At +6% or more it reads "Above usual", at −6% or less "Below usual", and
  otherwise "On pace", with the number of comparable runs (`:776-786`).
- With no history it falls back to each scenario's last run against its
  first run this session.

It existed at 0.8.3 and is missing from the July note.

**Inferred weaknesses:** The baseline has no window. For a player who is
improving, the median of all earlier runs sits below current form, so the
tile leans toward "Above usual". The ±6% band is about twice the
session-to-session swing measured on the maintainer's history in October,
near 3% in an untracked note, so the tile would rarely leave "On pace". The
fallback compares two single runs.

**Our baseline:** [product.md](../product.md) names *how is this session
going?* as one of the two in-session questions. The latest-run card
measures each run against the typical score as it stood when the session
began ([run_history.md](../specs/run_history.md)). Nothing sums that up
across the session's runs and scenarios.

**Recommendation:** A candidate for that question, built on our baseline
instead of theirs. The typical score at session start already has a 20-run
window and a minimum before it shows. A count reads more honestly than a
clamped mean: "6 of 8 runs at or above typical". The same count came up in
the October session discussion and is still unruled. Skip the
first-against-last fallback.

### 2. A calendar of time spent

**Observed:** RefleK's Streak & Playtime tile
(`frontend/src/features/overview/lib/streakActivity.ts:47-224`,
`components/sessionWidgets/StreakPlaytimeWidget.tsx:52, 197-209`):

- adds each run's length to the local day it ended;
- counts the current streak back from today, so it reads 0 until the
  day's first run, plus the longest streak, active days, and total playtime;
- draws a heatmap over 30, 90, 180 or 365 days, or an automatic range,
  whose shades are the quartiles of active-day minutes within that range;
- on a click, breaks down that one day by hour, its week, or its streak.

A neighbouring tile shows the session's length and its "active" share, the
sum of run lengths. Both existed at 0.8.3. The July note called the
breakdowns "hourly/weekly activity histograms", which overstates them: each
covers one selected day, week or streak.

**Our baseline:** The roadmap's Future list has "An overview", time spent
and activity across all scenarios, with no design yet
([roadmap](../roadmap.md)). Home holds one line of stats
([home.md](../specs/home.md)).

**Recommendation:** The closest prior art for that item, with two changes.
Label time in runs as a minimum, as the roadmap's uncertainty principle
requires; RefleK's says "Playtime" with no qualifier, though a stats file
covers neither the breaks nor attempts that wrote no file. Fix the shade
scale instead of re-deriving it per range, so a colour means the same
minutes in every range. A streak counter is a nudge to play every day.
Whether this app shows one is a product judgment, not a detail.

### 3. One clock for a run's kills and its `.perf` events

**Observed:** RefleK's Analysis tab plots accuracy over time from the
`.perf` shot and hit events, and each kill's time to kill from the kill
rows, on one axis: seconds since the stats file's `Challenge Start:`
(`frontend/src/features/history/lib/analysisChart.ts:90-131, 165-250`;
`mouseAnalysis.ts:309-345`).

- `.perf` timestamps are already relative to the run's start.
- A kill row's clock time minus the `Challenge Start:` clock gives its
  offset, adding a day when the run crosses midnight.
- The `.perf` header's `challenge_start_utc` places the run in absolute
  time.
- With no `Challenge Start:` line the `.perf` stream is dropped, not
  guessed.

Accuracy from `.perf` events is new in 0.9.0. It draws before the first
kill and on scenarios with no kills.

**Verified with our reader on RefleK's two `.perf` fixtures:**

- The score ticks add up to the stats file's `Score:` in both files (88.0,
  and 886.0568 against 886.056824). This repeats
  [Aimcurve finding 2](aimcurve_learnings_opus.md) on two public files.
- Events come in ticks of about a second: one file has 57 kill events for
  88 kills.
- `challenge_start_utc` is epoch milliseconds truncated to whole seconds.
- The overshots count is not monotonic. It rises by 25 four times, then
  falls by 100, summing to 0 while the stats file says
  `Total Overshots: 100`. What Overshots measures was already unknown
  ([2026-10-22](../decision_log/2026/2026-10-22-the-run-lists-columns-menu-offers-reloads-fov-and-avg-fps-off-to-start.md)).
- One fixture, Air Pure Medium, is time-scored by both of Aimcurve's
  signals. It ends on the profile's bot lives, with
  `end_challenge_after_kills` unset, so a capped scenario need not set that
  field.

**Verified locally, the kill table across 9,261 stats files.** Every file
starts with the header row `Kill #,Timestamp,Bot,...`. Its shape has
changed with the game:

| Files | Dates | Shape |
| --- | --- | --- |
| 12 | 2019-07-14 to 2019-12-15 | 12 columns; times written `15:01:11:577`, a colon before the milliseconds; `Cheated` is `true` or `false` |
| 407 | 2020-06-15 to 2021-07-20 | 12 columns; times written `18:21:44.717`; `Cheated` is `true` or `false` |
| 5,757 | 2024-12-15 to 2026-10-27 | 13 columns, adding `OverShots`; `Cheated` is `0` or `1` |
| 3,085 | 2020-07-21 to 2026-10-27 | The header and no kill rows: 254 scenarios, led by tracking scenarios such as VT Raw Control, VT Snake Track and Whisphere |

The install holds no files from mid-2021 to late 2024, so the change dates
are bounds. Line endings are mixed CRLF and LF in 8,690 files and CRLF only
in 571; Python's universal newlines read both.

RefleK's decodes `Cheated` only from `true` and `false`
(`internal/runs/kovaaks/stats.go:283, 369-383`), so a `1` in a current file
would read as false. Its time-to-kill figures run low (inferred from the
code): the frontend sets the first kill's to 0 and keeps it in the mean,
median and spread (`frontend/src/features/history/lib/scenarioAnalysis.ts:174-285`).
RefleK's parses each kill's bot, but nothing displays it
(`frontend/src/shared/types/ipc/runs.ts:68`), so there is no per-bot prior
art.

**Our baseline:** [performance_file.py](../../source/kovaaks/performance_file.py)
reads the hash, schema version, time limit, timescale, timestamps, and
score deltas. Nothing reads kill rows. The roadmap's Future list has a
per-bot breakdown on time-scored kill scenarios, and the 2026-10-22
decision keeps everything about one run for a later Run Viewer.

**Recommendation:** When within-run work starts, take this recipe:

- Parse the kill table by its header, accepting all three shapes.
- Use the kill rows for per-kill timing, which has millisecond precision,
  and each row's own time to kill.
- Use the `.perf` events for the course of a run second by second. They
  are the only within-run source for the third of runs that have no kills.
- Decode `.perf` counts as signed, and don't assume they only rise.

### 4. Test the parser against real stats files

**Observed:** RefleK's `testdata/` holds two real stats files with their
`.perf` files, and four `.refleks` archives. Its Go tests assert exact
values parsed from the real files: score, kills, hash, sensitivity, DPI,
kill count, and the first kill's time and bot
(`internal/runs/kovaaks/stats_test.go:19-130`, `performances_test.go:14`).
An ingest test lays a fixture out as a game folder, replaces its `.perf`
with one byte, and asserts that a present but malformed file is reported as
an error, not as missing (`internal/runs/ingest_test.go:12-51`). All of it
is new, written from 2026-09-13.

**Our baseline:** `tests/fixtures/performances/` holds two real `.perf`
files. Every stats file in our tests is written by the test itself, as in
`tests/test_data_service_extract.py`.

**Recommendation:** Add a few real stats files from the maintainer's
install, with exact-value assertions. A file the test writes encodes only
our own reading of the format. Choose them to cover the shapes in finding 3:
a 2019 file, a file from before `Challenge Start:` existed, a time-scored
run, and a run recorded on a game's sensitivity scale. A stats file holds
no account name; the newest local file was checked. Our pairing treats an
unreadable `.perf` as no answer rather than failing the run, which is the
better choice; whether a test keeps malformed and missing apart was not
checked.

### 5. Respect the reduced-motion setting

**Observed:** One CSS rule in RefleK's turns off animations, transitions,
and smooth scrolling when the system asks for reduced motion
(`frontend/src/index.css:368-390`). Its count-up numbers and chart entry
animations read the same preference. An in-app setting can override it
either way (`frontend/src/shared/lib/motion.ts:3-66`). New, from 2026-10-08
and 2026-10-15.

**Our baseline:** Only the personal best celebration honours the setting
(`assets/pbCelebration.js`). `assets/stylesheet.css` has transitions and an
endless ellipsis animation on pending playlist cells, with no reduced-motion
rule. The Mantine theme does not set `respectReducedMotion`.

**Recommendation:** Add one `@media (prefers-reduced-motion: reduce)` block
to `stylesheet.css`, and set Mantine's `respectReducedMotion` if Dash
Mantine Components passes it through, which was not checked. An in-app
override is not needed in a browser app.

### 6. Three gaps in our API notes

**Observed:** RefleK's calls two KovaaK's endpoints
(`internal/constants/urls.go:5-8`).

- **Last scores.** `GET /webapp-backend/user/scenario/last-scores/by-name`
  with `username` and `scenarioName`. RefleK's reads a top-level array of
  items shaped `{id, type: "scenario-score", attributes}`
  (`internal/models/scenario.go:160-186`). The attributes it reads are
  score, kills, fov, fovScale, cm360, sensScale, horizSens, vertSens,
  resolution, avgFps, avgTtk, pauseCount, pauseDuration, accuracyDamage,
  challengeStart, scenarioVersion, clientBuildVersion, hash, and epoch. It
  reads `score` unscaled, with a 10-second timeout and no retry
  (`internal/scenarios/service.go:31-55`). It sends the Steam persona as
  `username`, so (inferred) it finds the wrong account, or none, when the
  persona and the KovaaK's username differ.
- **Progress.** RefleK's divides each scenario's `score` from
  `/benchmarks/player-progress-rank-benchmark` by 100 and compares it with
  the unscaled `rank_maxes` (`internal/benchmarks/progress_parser.go:181`).
  Its energy figures would be off by a factor of 100 if that were wrong, so
  the scaling is probably right (inferred).

**Our baseline:** [kovaaks_api_notes.md](../kovaaks_api_notes.md) records
neither fact. It already says that Steam personas and KovaaK's usernames are
distinct namespaces. Its progress section also says "Existing app behavior
uses this endpoint for benchmark progress", and its endpoint table calls it
the "Existing benchmark progress flow". That is out of date: only
`scripts/benchmark_importer/` and `scripts/Leaderboard Sensitivities/` call
it, with a placeholder Steam ID whose scores are all 0. The app computes
benchmark ranks itself from the bundled thresholds.

**Recommendation:** Add both facts to the API notes, marked as RefleK's
reading and not probed, and correct the out-of-date wording. Probe with a
real Steam ID before any code reads the progress `score`. If the app ever
calls last-scores, send the verified KovaaK's username, never a persona.

### 7. Honesty failures to avoid by name

**Observed:** RefleK's has several surfaces that break the roadmap's "be
honest about uncertainty" principle. Each makes a concrete review check.

- **Missing evidence read as an all-clear.** When the sensitivity
  suggestion is withheld for lack of evidence, the copy tells the player to
  carry on with their current sensitivity
  (`frontend/src/shared/lib/i18n/messages/en/history.ts:351`).
- **Defaults shown as findings.** With too few sessions, the session-length
  gauge shows a warm-up of 1 to 2 runs, a peak at runs 3 to 10, and a target
  of 8, with nothing marking them as defaults. It computes a confidence and
  the number of sessions behind it, and shows neither
  (`useRecentSessionSnapshot.ts:430-620`).
- **A constant that looks measured.** Every trace records a sample rate of
  125 Hz. Capture is per mouse event, and the rate argument is unused
  (`internal/runs/mouse/tracker_windows.go:71, 240`).
- **Arrows from too few runs.** The Last Run tile draws an up or down arrow
  from as few as three runs, one run against two
  (`useRecentSessionSnapshot.ts:220-281`). The session overview compares
  this session's best with the previous session's best by exact comparison
  (`frontend/src/features/history/lib/historyModels.ts:446-491`), and a best
  grows with the number of runs.
- **Precision beyond the evidence.** One run's time-to-kill slope shows four
  decimals, and its R² and correlation three
  (`frontend/src/features/history/components/inspector/AnalysisTab.tsx:284-297`).
- **Confidence computed but hidden.** Each kill's over- or undershoot
  confidence is never shown, and target inference conveys uncertainty only
  through opacity.
- **Promises the code can't keep.** The welcome screen promises "zero CPU
  impact" for recording, yet the encoder falls back to software
  (`en/welcome.ts:123`, `internal/runs/screen/encode.go:181-185`). Settings
  say the screen is recorded during scenarios. The whole primary display is
  captured whenever the game is running, and only the run clips are kept.

Three habits are worth copying. Each video replay gets a status with a
stated reason, and a run outside the recording session is refused rather
than matched to an unrelated clip (`internal/constants/codes.go:11-22`). The
over- and undershoot classifier has an "unknown" class that says why.
Traces are labelled in trace units, with a note that they hold no target
centres.

**Our baseline:** The
[typical-run decision](../decision_log/2026/2026-10-04-skill-is-judged-by-the-typical-run-with-honest-uncertainty-in-verdicts-not-advice.md)
ratified these principles; the verdicts on the roadmap, the score trend and
the rank-up chance, have no design yet.

**Recommendation:** Use the list as review checks on those designs. "Not
enough evidence" never reads as "no problem". A fallback or default is
labelled as one. An arrow or a verdict waits for the runs that support it.

### 8. Smaller observations

- **Sessions measured end to end.** RefleK's starts a new session when the
  gap between two runs' end times exceeds a setting of 5 to 120 minutes,
  20 by default (`frontend/src/shared/hooks/useStore.tsx:188-254`). Ours
  measures from one run's end to the next run's start, fixed at 30
  ([2026-10-11](../decision_log/2026/2026-10-11-a-session-ends-after-a-break-of-more-than-30-minutes.md)).
  Nothing to take.
- **Request pacing has converged.** Since 0.10.0 RefleK's sends progress
  requests one at a time, at least 2 seconds apart. It honours
  `Retry-After` on HTTP 429; without one it waits 30 seconds, doubling up
  to 5 minutes. Requests for the same benchmark are shared
  (`internal/benchmarks/progress_fetcher.go:16-122`,
  `internal/benchmarks/service.go:17-137`). Our percentile warmup already
  paces at 2 seconds with a 30 to 1,800 second backoff. Whether a cold
  playlist table can ask for the same leaderboard twice was not checked.
- **Benchmark summaries by category.** RefleK's benchmark page shows the
  mean progress toward max rank per category and a count of scenarios per
  rank, both from personal bests
  (`frontend/src/features/benchmarks/components/detail/StrengthWidget.tsx:173-209`).
  A per-category summary of our Typical Rank, counting unknowns instead of
  averaging them in, could answer "which kind of scenario is weak". That
  would be new scope.
- **Performance against sensitivity.** RefleK's plots each run's score
  against its cm/360 on a numeric axis, with no fit or count
  (`frontend/src/features/history/components/PerformanceVsSensWidget.tsx:360-454`).
  Like our Score vs Sensitivity mode, it mixes sensitivity with improvement
  over time. Plotting each run against the typical score at its session's
  start would remove the trend; that idea is ours, not RefleK's.

## What not to take

- **Uploading runs by default.** RefleK's uploads each completed run to
  `api.refleksapp.com` unless the player turns it off in settings
  (`internal/settings/settings.go:123`, `internal/runs/runtime.go:580-596`).
  The file holds the stats, the `.perf` data, the raw mouse trace, and the
  PC snapshot: hardware, the mouse's device path and IDs, and the Steam ID
  and persona. The first-run dialog offers Public, marked Recommended, or
  Anonymous, and no choice not to upload. Anonymous removes only the Steam
  ID and persona (`internal/runs/cloud_sync.go:121-125`). This app sends no
  run anywhere except a chart the player shares by hand, and with no
  username set it makes no requests on its own
  ([What it talks to](../user_guide.md#what-it-talks-to)).
- **Training advice.** Three surfaces tell the player what to do:
  - A per-scenario "what to play" score, with a legend from "Top pick" to
    "Avoid for now" (0.9.6). It now weighs relative progress, trend, a
    plateau, recency, closeness to the next rank, and a penalty for runs
    already played this session
    (`frontend/src/features/benchmarks/lib/detailRecommendations.ts:87-245`).
  - A gauge of how long to play.
  - The sensitivity suggestion, now an 18 to 45% change presented as a
    deliberately exaggerated setting for a short block.

  All three conflict with the ratified rule that the app states verdicts,
  not advice. RefleK's closeness to a rank is a share of the rank band from
  the personal best, with no spread; the planned rank-up chance would weigh
  the player's own run-to-run spread.
- **Native capture.** Mouse traces, screen video, and target inference all
  need native hooks. Target inference also has no ground truth: its tests
  are synthetic, and the "target" it draws is the smoothed cursor during
  on-target time inferred from per-second hit counts.
- **Recent-first loading as RefleK's does it.** It ingests runs from the
  last 180 days or the newest 2,500, whichever is more (90 days and 1,500 in
  July), and its history view loads the same window, so older runs never
  show (`internal/constants/defaults.go:14-15`, `internal/runs/store.go:470-491`).
  The maintainer's install holds 9,261 stats files. If startup cost becomes
  a problem, measure it first. Only "recent first, the rest in the
  background" would keep full history.
- **Energy and a runtime benchmark catalog.** RefleK's implements 2 of 40
  rank-calculation rules a year in. It fetches its catalog from its own
  server at each start, with an ETag and a built-in fallback. Our bundled
  benchmark library carries its thresholds, generated by the importer and
  committed, so the app has no such dependency.
- **UTF-16 detection.** No local file needs it.
- **Engineering surfaces that don't fit a browser app.** Six languages,
  whose Russian plurals are wrong ("2 забегов" where "2 забега" is needed,
  `frontend/src/shared/lib/i18n/plural.ts:12-14`). A user-editable CSS
  theme. A welcome dialog on every new version, which our cadence of 75
  release tags this month would open on most launches. An installer the
  user starts from inside the app, with no hash or signature check
  (`internal/updater/updater.go:171-218`). Reset and clear-cache buttons.

## Suggested order

1. Fix our API notes (finding 6). Docs only.
2. Add the reduced-motion rule (finding 5). A small UI change.
3. Add real stats-file fixtures (finding 4). Tests only.
4. Bring finding 1 to the next design for *how is this session going?*, and
   finding 2 to the overview when it comes up.
5. Carry finding 3 into the Run Viewer and per-bot breakdown designs.
6. Use finding 7 when reviewing any verdict proposal.

## Compared with the July survey

What the July note got wrong, or what has changed since:

- **Watcher.** It said RefleK's polls every 5 seconds instead of using file
  events. Since 0.9.0 it uses file events and polls only as a fallback
  (`internal/watcher/watcher.go:139-190`).
- **Startup window.** 90 days and 1,500 runs is now 180 days and 2,500,
  both user settings. The same window limits the history view.
- **Run upload.** "Optional cloud sync" understated it: upload is on by
  default and includes the mouse trace and the PC snapshot.
- **Mouse capture.** "125 Hz" was a label even then. The buffer grew from 2
  to 5 minutes and became a setting. The suggestion's gates are new: at
  least 5 kills classified with confidence 0.5 or more, a mean confidence
  of at least 0.55, and one issue carrying at least 62% of the weight and
  appearing in at least 35% of those kills
  (`frontend/src/features/history/lib/mouseAnalysis.ts:805-877`).
- **`.perf` schema.** It is not reverse-engineered: KovaaK's publishes it at
  <https://wiki.kovaaks.com/performance.proto>, and RefleK's decodes it
  field for field. The header's challenge profile has 12 fields.
- **Encoding.** "Implying KovaaK's sometimes emits non-UTF-8 files" has no
  support. RefleK's tests the case with made-up bytes only, and no local
  file needs it.
- **Kill analytics.** The 10th and 90th percentiles and the longest gap
  without a kill are computed but never displayed. The slope and R² are
  fitted to the 5-kill moving average. The first kill's time to kill is set
  to 0.
- **Session tiles.** The average score and most repeated scenario are never
  displayed; their helpers have no caller, at 0.8.3 or now. The trend
  against the previous session compares the two sessions' bests only.
- **Recommendations.** The July description was incomplete; What not to
  take lists the full set of inputs.
- **Ingest-time values.** Run length ignores pauses and falls back to an
  invented 60 seconds. The yaw table can't convert non-linear scales,
  including Battlefield, the scale of RefleK's own fixtures.
- **Benchmark refresh.** The comparison with "our rank-freshness timer
  chain" doesn't fit: our benchmark ranks are computed locally.
- **Steam detection.** It moved to `internal/steam/detect`, finds the Steam
  folder in the registry, and saves the detected account into settings on
  first load, so a later account switch isn't followed. Its parser reads
  each byte as a character, which would garble a persona that isn't ASCII
  (inferred, `internal/steam/detect/loginusers.go:66`).
- **Missing surfaces.** The note omitted the whole-session read, the
  session-length gauge, performance against sensitivity, a radar of the
  session's scenario mix, session names and notes, scenario notes with a
  training-sensitivity field, and run-to-run comparison. All of them
  existed at 0.8.3.

[rk]: https://github.com/ARm8-2/refleks/tree/e1ef9437169eee484b03a723887f7ece86a7c4f8
