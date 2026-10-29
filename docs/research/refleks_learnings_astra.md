# Lessons from RefleK's

Date: 2026-10-28
Author: gpt-6-astra · effort: xhigh

Research note; recommendations remain unratified. This Astra survey is retained
separately from the [other RefleK's survey](refleks_learnings.md).

## Takeaway

RefleK's makes a completed run explorable: a player can move from a session
to a run, compare it with another, and inspect events, settings, movement,
and video. CSD would benefit most from that connected inspection workflow
and from making better use of the files it already reads. Its training
prescriptions, inferred target motion, and convenient timing fallbacks need
more evidence before they could become trustworthy CSD features.

## Evidence and scope

- Desktop source: [`e1ef9437169eee484b03a723887f7ece86a7c4f8`][desktop],
  the default branch head inspected on this date; commit dated 2026-10-15.
- Latest published desktop release found:
  [0.10.0, published 2026-09-12][release], at
  `c45cd31c8da8b8fd099f6d95dc3bf7a1c3a07298`. Source observations below
  concern the inspected head, not a claim that its entire contents shipped
  in that release.
- Retrieved the previous survey's exact source revision,
  `1f31c96c4c993572ba5fefa260ba5a1761329b51`, and compared the trees.
  The diff spans 370 files, including translations and tests; that count
  is not a feature count.
- CSD baseline: `911ca00986c109de614861e9db2613c326d52d6c`, also the live
  `main` head at the check. Compared its owning source, current specs, and
  decisions, rather than carrying forward July's account of our gaps.
- Read the project's public documentation, changelog, open issues and PRs,
  and the related research repository's file inventory and workspace
  READMEs. Website content is dated evidence, not revision-pinned source.
- Executed the desktop frontend's existing tests: **37 files, 150 tests
  passed**. Its TypeScript/Vite production build passed, with a bundle-size
  warning. Four additional research probes imported the actual frontend
  functions; results appear below.
- Downloaded KovaaK's [published performance schema][proto] and checked its
  fields. No live player API queries, cloud uploads, or access to the
  maintainer's recordings were needed.
  The downloaded schema's SHA-256 was
  `8a893463d60d16b5161deafec291ebb901b3c4300d30a0a23a5f383a7c60f1cb`.
- This is a source and calculation investigation, not a native-app usability
  or performance benchmark. The Go/backend tests were not run because Go
  was unavailable on PATH. Windows capture, installation, accessibility,
  frame alignment, and training effectiveness were not tested in use.

External desktop source links below are pinned to the inspected revision.
**Observed** means present in source or reproduced by a named probe.
**Recommendation** means our judgment. An upstream issue is a report, not
an independently reproduced defect.

The desktop repository declares GPL-3.0. This update copies no implementation
into CSD; it records behavior, data contracts, and design lessons.

## Corrections to the July survey

| Earlier statement | Verified replacement |
| --- | --- |
| CSD has no session concept. | CSD has sessions, scenario visits, session rows, and session-based comparisons. Its break limit is 30 minutes. See [Sessions](../specs/sessions.md). |
| CSD does not read `.perf` files. | It reads selected header and score-event fields for time-scored detection and pace comparisons. It does not yet expose a general within-run event viewer. See [the parser](../../source/kovaaks/performance_file.py) and [Run History](../specs/run_history.md#time-scored-scenarios). |
| Steam-account discovery is a new opportunity. | CSD already detects accounts and verifies the returned KovaaK's identity against SteamID64. See [Settings](../specs/settings.md#detection). |
| A yaw lookup table is needed for cm/360. | CSD already converts from the recorded `Sens Increment` and DPI, retaining original values. A second engine-name table would duplicate a solved problem. See [Run History](../specs/run_history.md). |
| RefleK's uses polling instead of filesystem events. | It prefers `fsnotify` Create/Write events; five-second polling is the fallback when watcher creation or attachment fails. [Watcher][watcher]. |
| Its catch-up window is 90 days / 1,500 runs. | Defaults are now 180 days with a minimum of the newest 2,500 runs, where available. This is a floor, not a 2,500-run cap. [Defaults][defaults], [filtering][watcher]. |
| Mouse input is recorded at 125 Hz into a two-minute buffer. | The Windows tracker is event-driven Raw Input; its constructor ignores the sample-rate argument. The default buffer is five minutes. The metadata's 125 Hz value is not proof of a measured capture rate. [Tracker][mouse-tracker], [defaults][defaults]. |
| Sensitivity advice needs four kills / 0.42 confidence and changes sensitivity by 3–30%. | Current code requires at least five classified kills with confidence ≥0.5, average ≥0.55, and additional dominance checks. Its dose is clamped to 18–45% **of cm/360**. [Advice][mouse-analysis]. |
| The performance schema is reverse-engineered. | KovaaK's publishes `performance.proto`. It is the primary reference; RefleK's is an implementation example. [Schema][proto]. |
| UTF-16 support proves the game emits UTF-16 files. | It proves RefleK's handles those encodings. This investigation did not establish how often the game itself produces them. [Reader][stats-parser]. |
| Cloud sync is simply optional. | The setting can be disabled, but fresh defaults enable run upload and disable anonymous mode. Screen capture defaults off; mouse tracking defaults on. [Defaults][settings-defaults]. |

CSD's ingestion position also changed. It now deduplicates successful
filenames, reconciles the startup scan/watch gap, and retries live parsing
after waits of 1, 2, and 4 seconds. The maintainer explicitly retained those
waits on the observer thread and closed the worker proposal unmerged.
This survey supplies no new realistic burst evidence that would overturn
that [decision](../decision_log/2026/2026-10-26-run-imports-retry-a-failed-parse-on-the-observer-thread.md).

## Recommended priorities for CSD

These are research priorities, not approved implementation tasks.

| Priority | Learning to apply | User benefit | Evidence or design needed first |
| --- | --- | --- | --- |
| Highest | Connect run selection, raw facts, event charts, and a named reference run. | Answer where two attempts differ without losing the selected run. | Define source availability, comparison eligibility, and time alignment. |
| Highest | Extract kill rows on demand and group recorded bot/weapon results. | Explain a run using data already on disk. | Verify attribution and denominators across mixed-bot, tracking, and partial runs. |
| High | Extend the existing `.perf` reader for specific within-run questions. | Inspect score and accuracy changes before or between kills. | Validate schema/version handling, pause clocks, missing events, and CSV reconciliation. |
| High | Expose data coverage and failure states beside analytics. | Distinguish no evidence, incomplete evidence, and an actual zero. | Preserve CSD's unknown-duration and time-scored contracts. |
| Medium | Test CSV encoding resilience with real examples. | Recover otherwise unreadable imports without losing healthy files. | Establish a representative fixture and explicit BOM/encoding rules. |
| Medium | Add optional session reflection and richer sensitivity comparisons. | Keep training context and compare similar attempts. | Identify demand beyond existing scenario notes, session lists, and Score vs Sensitivity. |
| Conditional | Use bounded detail caches and progressive loading if profiling warrants them. | Keep detailed inspection responsive on large histories. | Measure CSD first; preserve full-history PB and Typical Score semantics. |
| Defer | Native mouse capture, video capture, cloud archives, and automated coaching. | Potentially richer review and recommendations. | Separate scope, consent, storage, validation, and maintenance decisions. |

The first three form a useful sequence: trustworthy run details, then
comparison, then carefully chosen derived explanations. Copying an entire
analytics dashboard would obscure which question each metric answers.

## 1. Product workflow: context survives deeper inspection

**Observed.** History keeps session selection, scenario selection, searches,
sorts, PB filters, and the selected inspector tab. It maintains a pinned run
and a comparison run, offers a PB comparison shortcut, and supports overlay
or side-by-side analysis. Opening the inspector collapses the session list
to give details room. The inspector separates Stats, Analysis, Trace,
Replay, and Environment. These are implemented interactions, not just
marketing screenshots. [History state][history-state], [inspector][inspector].

The overview combines the latest session's status, recent scores, activity,
and benchmark focus. Charts can expand into a larger modal. A separate
benchmark share action renders a capture region into a clipboard image.
[Overview logic][overview], [expandable widgets][widget],
[benchmark sharing][benchmark-page].

**Recommendation.** Borrow continuity of selection and a clearly named
reference run. The useful question is “What changed between these attempts?”
The reference's scenario/version, date, score, sensitivity, and available
evidence should remain visible while the player switches views.

For CSD, a detailed viewer can build on the existing Run History list and
chart. Avoid making users independently select the same run in every panel.
Keep raw recorded facts reachable from derived charts. A compact summary
should lead into detail only when the user asks for it.

A future comparison should define compatible scenarios and versions and
state how time axes align. Equal elapsed time, equal kill index, and equal
fraction of a run answer different questions. A visually aligned overlay
alone does not establish comparability.

## 2. More signal is available in the files we already have

### Kill rows: a useful first increment

**Observed.** RefleK's recognizes kill rows structurally, reads them with a
CSV parser, and retains kill index, time of day, bot, weapon, recorded TTK,
shots, hits, accuracy, damage, efficiency, cheated, and overshots. It also
retains many summary fields as typed values. [Stats parser][stats-parser].

CSD's [current parser](../../source/kovaaks/data_service.py) reads the
summary and weapon sections needed for its run model. It does not retain
that kill-event table. RefleK's demonstrates that useful run-level detail
can start without a native input recorder.

**Recommendation.** Start with recorded events and a bot/weapon breakdown:
kills, recorded TTK distribution, shots/hits and their ratio, and comparison
with the corresponding group in a reference run. Compute an aggregate ratio
from summed hits and shots where those fields have the same meaning; do not
average row percentages.

The important limit is attribution. A kill row describes a recorded kill,
not every attempt against that bot. Misses or damage outside those rows,
an unfinished final engagement, and simultaneous targets can prevent the
table from accounting for the whole run. State the covered population and
reconcile totals before labeling it overall accuracy or total bot effort.
This proposed bot breakdown is our recommendation, not a claim that the
inspected RefleK's UI implements that exact view.

### Performance events: extend our reader, not our assumptions

**Observed.** The published schema provides a header and repeated timestamped
events. Its header includes scenario name/hash, UTC challenge start, schema
version, and a challenge-profile snapshot. The snapshot includes time limit,
timescale, bot names and other scenario configuration. The event payloads
are compact:

| Event field numbers | Payloads | Value field |
| --- | --- | --- |
| 2, 3, 4 | Shots fired, hit, missed | Integer count |
| 5, 6, 7 | Damage done, damage possible, score | Floating-point delta |
| 8, 9, 10 | Kills, deaths, overshots | Integer count |
| 11 | Player damage taken | Floating-point delta |
| 12, 13 | Reloads, pause count | Integer count |
| 14, 15 | Distance traveled, MBS points | Floating-point delta |
| 16, 17, 18 | Target size, target speed, random sensitivity scale | Floating-point value |

The event timestamp is field 1. Each payload's value is its own field 1.
The schema supplies no per-event bot identity, target position, or target
trajectory. Header bot names cannot turn global damage samples into
per-bot telemetry. [Published schema][proto], [RefleK's decoder][perf-parser].

RefleK's combines CSV kill markers with cumulative shots/hits from `.perf`.
Its accuracy chart prefers performance samples when usable; otherwise it
uses kill rows. It requires a valid challenge-start clock to combine those
sources. [Chart construction][analysis-chart].

**Recommendation.** Use the official schema and CSD's existing
[three-state parser](../../source/kovaaks/performance_file.py) as the starting
point. Read only the extra fields a concrete view needs. Confirm whether
event timestamps advance during a pause before mixing them with CSV
wall-clock times. Preserve “can't answer” for missing, malformed,
unsupported, or mismatched evidence. A missing sidecar should cost the
optional detail, not the valid CSV run.

A score-delta plot also needs scenario scoring semantics. CSD already handles
time-scored scenarios and eligible pace comparisons; a larger raw-score
percentage is not a universal description of performance improvement.

### Encoding resilience

RefleK's accepts a UTF-8 BOM, UTF-16 LE/BE BOMs, and a BOM-less UTF-16
heuristic based on null-byte positions in the first 512 bytes. CSD still
opens run CSVs with `encoding="utf-8"`. A UTF-16 file is therefore a useful
candidate fixture, but the old note overstated the evidence for a common
game-generated failure. [RefleK's reader][stats-parser],
[CSD parser](../../source/kovaaks/data_service.py).

Recommend a small fixture-driven investigation before changing ingestion.
Distinguish an encoding problem from a partially written file, and do not
replace decoding errors with silently discarded bytes.

## 3. Metric semantics: useful views, several traps

### “Real TTK” is not the recorded per-kill TTK

**Observed and reproduced.** `computeScenarioAnalysis` derives “real TTK”
from consecutive kill timestamps and starts the series with zero. It then
uses that series for averages, percentiles, a five-kill moving average,
linear-regression slope/R², and per-interval `60 / gap` values.
It does not use the CSV's recorded TTK for that series.
[Calculation][scenario-analysis].

These are different quantities:

- Recorded TTK is a field supplied for the kill.
- Inter-kill interval includes whatever happened between two kill events.
- Kills divided by trusted active duration is a run-wide rate.

The average of reciprocal intervals is not the reciprocal of the average
interval. Neither is automatically the run-wide rate. A trend in inter-kill
intervals can reflect target mix, movement, a pause, or a late difficult
target; it is not evidence of fatigue by itself.

### Reproduced calculation edge cases

Four research probes imported RefleK's actual exported functions. These
results describe the inspected implementation, not desired CSD behavior.

| Input | Observed result | Consequence for CSD |
| --- | --- | --- |
| Three kills at seconds 1, 2, and 3; recorded TTK 0.25 s each | Inter-kill series `[0, 1, 1]`; reported average “TTK” `0.6667 s`; average gap `1 s` | Give distinct measures distinct names; do not include a synthetic first zero in the interval population. |
| First performance sample at second 1: two shots, one hit | Chart also contains 50% accuracy at second 0 | Distinguish drawn extensions from actual observations. |
| Session scores 100 and 10,000 on different scenarios | Session average 5,050 | An average across unrelated score scales is not a training-quality measure. |
| Session scores 0 and 100 | Session average 100; `formatScore(0)` and `formatScore(-1)` return `--` | Keep legitimate zero/negative scores distinct from missing data. |
| One-run session with identical start/end timestamps and a 60 s run duration | Session span 0 ms; summed run duration 60,000 ms | Define time from the underlying run boundaries, not just the first and last completion times. |

Sources: [analysis][scenario-analysis], [chart][analysis-chart],
[history calculations][history-models], [session grouping][store].
The final row used the same completion-time session shape that
`groupSessions` produces.

### Sessions and time are already better specified in CSD

RefleK's groups consecutive **completion timestamps** by a configurable gap
(default 20 minutes from backend settings). A session's start is its earliest
completion timestamp. Separately, ingest derives a run window from
`Challenge Start`, falling back to the first kill and then to end minus
60 seconds. It stores the window length as duration without subtracting
`Pause Duration`. “Active playtime” sums those durations.
[Grouping][store], [ingestion][ingest], [history calculations][history-models].

CSD's [session contract](../specs/sessions.md) instead distinguishes trusted
run duration, session span, and scenario visits. Trusted run duration excludes
pauses; spans include breaks and pauses. Unusable duration remains unknown.
Keep that contract. A new time/activity view should disclose coverage and
must not imply that completed run files reconstruct all time spent in the
game, including freeplay and abandoned attempts.

### Sensitivity comparison is descriptive, not causal

RefleK's Performance vs Sensitivity widget plots a selected scenario's runs
against cm/360 and switches among score, accuracy, and real average TTK.
It can scope to a session. This makes a useful comparison surface.
[Sensitivity widget][sensitivity].

CSD already has sensitivity normalization and Score vs Sensitivity.
A useful extension would compare similar runs by date, scenario version,
and session, with sample counts. A scatter of higher scores at one
sensitivity does not show that sensitivity caused the improvement:
practice, target changes, and selective use can explain the association.
Retain the original recorded settings alongside normalized values.

## 4. Recommendations: borrow explanations, validate prescriptions

### Scenario and benchmark suggestions

**Observed.** The scenario heuristic considers relative benchmark progress,
recent score slope and variation, time since play, repetitions in the latest
session, and closeness to a threshold. It inspects up to 50 sessions and
up to ten recent scores for its slope. Top-pick selection favors category
diversity among similarly scored candidates. [Scenario heuristic][detail-recs].

The separate benchmark selector uses completion, progression to the next
difficulty, beginner boosts below ten sessions, and deterministic daily
jitter. It rescales candidates against each other and returns a small set.
Those scores are relative ranking rules, not calibrated probabilities.
[Benchmark heuristic][benchmark-recs].

**Recommendation.** If CSD later adds training suggestions, start with an
auditable reason such as repeated practice, an under-practiced category,
or an explicit benchmark gap. Show the supporting runs and let the player
ignore or change the goal. Category diversity is worth considering.

Do not relabel CSD's PB-to-next-rank proximity as likelihood of ranking up.
Likewise, a boost from daily jitter changes the ordering without new
performance evidence; it belongs to variety, not a claimed prediction.
The acceptable objective and the evidence needed for a suggestion remain
product decisions.

### Session performance and “when to stop”

RefleK's overview compares current runs with prior same-scenario medians,
clamps each relative difference to ±35%, and averages comparable runs.
Its session-length heuristic maps scores into scenario percentiles and
combines curves by run index, with minimum sample checks and fixed defaults
when evidence is sparse. [Overview calculations][overview].

The normalization is a better starting point than averaging unrelated raw
scores. However, later run positions are represented only by sessions that
lasted that long, and a player may change scenarios or stop because of how
they feel. These are observational-selection problems. The code's confidence
label does not establish that its suggested stopping point improves training.

CSD already has a defined [Typical Score](../specs/typical_score.md) and a
session-start baseline. Build future comparisons on those definitions rather
than introducing another unnamed “normal.” Record observations before
prescribing breaks or claiming fatigue.

## 5. Mouse traces and target inference are different evidence

**Observed.** Windows Raw Input accumulates relative mouse deltas and button
changes into an unbounded virtual coordinate space. It uses a hidden input
window and `RIDEV_INPUTSINK`, with capture lifecycle tied to the game process.
These coordinates are raw input units, not screen pixels or known crosshair
coordinates. [Windows tracker][mouse-tracker], [runtime lifecycle][runtime].

The analysis now explicitly marks its coordinate space and inferred endpoint
evidence. It evaluates coverage, gaps, motion, crossings, and button timing;
some kills are unknown or skipped. The target overlay derives likely motion
from coarse performance evidence and the player's movement. It interpolates
through gaps. It is **not a recorded target path**.
[Mouse analysis][mouse-analysis], [target inference][target-inference].

Current sensitivity advice is intentionally a short training perturbation,
not an estimate of optimal sensitivity. It can prescribe higher sensitivity
for an overshoot pattern to exaggerate the training problem. That is the
opposite of a simple compensating adjustment. The percentage is a cm/360
change; because sensitivity is inverse to cm/360, the same numeric
percentage does not describe the in-game sensitivity change.
[Advice and thresholds][mouse-analysis], [displayed explanation][history-copy].

**Recommendation.** Borrow the distinction between measured, inferred, and
unavailable evidence. Do not borrow the diagnosis or dose without validation
against labeled runs and actual target information. Unknown classifications
and suppressed advice are essential states, not UI defects to fill in.

Native capture is substantial new scope for CSD: device/process lifecycle,
background-input boundaries, data volume, and a meaningful account of capture
quality. Prefer the files the game already writes until that scope has a
clear user benefit. Even a high-quality mouse trace cannot recover the
true target trajectory by itself.

## 6. Video replay is a useful product with substantial operating costs

**Observed.** RefleK's now has separate screen recording and replay support,
added after the July snapshot. The Windows implementation uses DXGI desktop
duplication and FFmpeg, a bounded frame pipeline, and a rolling segmented
recording. Defaults are 30 FPS and 720 resolution; capture is off initially.
The buffer uses five-second segments with five-minute retention, and a
trim can preserve two seconds after the run's end.
[Capture][capture], [defaults][defaults], [trim lifecycle][ingest].

Replay availability has explicit processing and terminal states, and the
frontend listens for state changes. It supports comparison playback and
export. Cleanup can enforce age and storage limits; defaults enable cleanup
with a 5 GiB cap and no age limit. The size-limit pass keeps the newest
replay even if that file alone exceeds the cap.
[Replay UI][replay-ui], [cleanup][cleanup], [settings][settings-defaults].

**Recommendation.** Learn from the lifecycle, especially visible processing,
failed, and unavailable states; bounded buffers; asynchronous publication;
and explicit retention. Those principles also fit expensive run-detail
loading without adopting video.

A recorder needs measurement under actual gameplay: frame pacing,
game-performance overhead, GPU/display changes, process exit, late stats
files, and disk exhaustion. Desktop duplication also warrants verifying
what an alt-tab records. None of these outcomes was tested here. A separately
chosen existing replay file could be a lower-scope experiment than embedding
a recorder, but that alternative is not a ratified direction.

## 7. Engineering patterns worth adapting selectively

### Keep summaries cheap; load evidence when requested

RefleK's stores versioned `.refleks` records with stats, performance data,
mouse trace, and environment metadata. Its codec supports v1/v2, uses
Zstandard compression and an xxh3 checksum, and can skip detailed sections
while building summaries. Video remains a separate replay file.
[Codec][codec], [store][run-store].

The run index bounds its parsed-summary cache at 4,096 entries. Inspector
resources have a separate eight-entry LRU cache, and history lists use
virtualization. This separates opening a history from decoding every run's
trace. A custom archive format is not necessary to borrow that separation.
[Index][run-index], [resource loader][run-resource], [virtual list][virtual-list].

**Recommendation.** Keep CSD's raw files authoritative and consider bounded,
on-demand event parsing for a viewer. Key results by the selected run and
source identity. A late result for run A must not appear under run B.
If a cache outlives a source change, include an invalidation/version strategy.

RefleK's loader catches a failed resource load and exposes an empty array.
That is a useful counterexample: CSD should distinguish “no events” from
“couldn't read events” rather than letting both produce an empty chart.
[Resource loader][run-resource].

### Progressive catch-up is not complete history

The watcher converts a bounded recent subset in the background, publishes
progress every 25 successful conversions, and uses a generation check to
stop obsolete catch-up work. All files present at startup are marked seen,
including those outside the selected subset. The store also filters recent
records when loading history. [Watcher][watcher], [store][run-store].

This is not “recent first, then eventually all historical files.” It is
a history-selection policy. PB maps computed from loaded sessions consequently
refer to the loaded population, even where the UI calls them all-time.
[PB map][history-state].

**Recommendation.** If CSD ever needs progressive startup, retain complete
aggregates or expose a clearly incomplete state until backfill completes.
Do not silently cap the population behind PB, Typical Score, or historical
trends. Profile before adding a persisted index or new startup scheduler.

### Reliability comes from state transitions, not the watcher library

RefleK's reserves in-flight paths before ingest and marks successful files
seen afterward; store-level existence checks provide another duplicate
barrier. It writes to a unique temporary file before rename.
[Watcher][watcher], [atomic publication][run-store].

A limit worth preserving in our interpretation: the matching performance
file is retried while missing, but an existing malformed performance file
returns a parse error to the whole ingest. This is visible in source; it
was not reproduced through the native watcher. A retry mechanism alone
does not prove a complete readiness policy. [Sidecar handling][ingest].

CSD already has filename deduplication, startup reconciliation, and bounded
retry. Its chosen threading model should stay governed by the existing
[ingestion spec](../specs/run_ingestion.md), not by RefleK's different
architecture. Optional enrichment should fail independently of a valid run.

### Cache and network freshness

The benchmark catalog uses ETags and an embedded fallback. Progress fetching
handles 429 responses with Retry-After support and bounded backoff.
A newly parsed run can trigger refreshes of affected benchmarks.
[Catalog][catalog], [progress fetcher][progress-fetcher],
[benchmark service][benchmark-service].

These are useful techniques where the supplying API supports them.
They do not justify adding requests merely for parity. CSD already bundles
benchmarks and refreshes scenario ranks; any new network trigger still needs
the disclosures required by its [user guide](../user_guide.md#what-it-talks-to).

## 8. Privacy, identity, accessibility, and data ownership

### “Local desktop app” does not mean data stays local

Fresh settings enable mouse tracking and run sync, and disable anonymous
mode. Newly ingested live runs reach the upload handler; startup catch-up
uses a path without that callback. The upload sends the `.refleks` record,
not the separate replay video. The anonymous transformation clears
`SteamID` and `PersonaName` only. Stats, timestamps, trace, and other
environment metadata remain.
[Settings][settings-defaults], [live callback][runtime],
[upload and scrubbing][cloud], [catch-up][watcher].

Environment collection includes OS/architecture, CPU information, application
version, and mouse metadata. This investigation did not assess whether the
remaining combination can identify someone. “Anonymous” describes the code's
named-field removal, not a demonstrated privacy guarantee.
[Environment collector][environment].

**Recommendation.** Any future CSD sharing should be explicitly chosen,
show what is sent, and distinguish local export from remote upload. A
self-contained export can be valuable for support and comparison without
automatically introducing a cloud service. Preserve source provenance and
separate derived results from original observations.

### Account detection must preserve identity

RefleK's resolves Steam ID and persona independently through settings,
environment, and Steam's most-recent account. A stored ID can therefore
coexist with a separately detected name. Its recent-score lookup passes
the persona as `username`.
[Identity resolver][steam], [recent-score request][scenario-service].

CSD's existing discovery is more conservative: it checks that the profile
response's Steam ID matches the account and proposes the returned KovaaK's
username. Keep that verification. Steam persona, KovaaK's username, and
SteamID64 are not interchangeable just because one integration uses a
similarly named query parameter.
[Our contract](../specs/settings.md#detection).

### Accessibility and polish have transferable mechanisms

The source has six language catalogs, locale-aware formatting, resizable
presentation controls, and shared expandable widgets. Current main adds an
explicit system/reduced/full motion preference. These mechanisms can make a
dense analytics interface easier to use.
[Localization][i18n], [motion preference][motion], [widgets][widget].

They do not establish screen-reader or keyboard accessibility of the whole
product. Test actual workflows, particularly virtualized rows, nested
interactive controls, charts, and focus after opening/closing a detail pane.
CSD already has [recorded NVDA checks](run_history_list_nvda_walk.md);
continue measuring rather than equating a component library with conformance.
Language expansion needs translation review, not only typed keys.

## 9. API observations and the wider RefleK's ecosystem

The desktop still calls
`/webapp-backend/user/scenario/last-scores/by-name` with `username` and
`scenarioName`. Its code expects a recent-score list and describes it as ten
scores. That is a source observation, not an independently checked current
server limit. The benchmark-progress parser still divides scenario scores
by 100, retains `rank_maxes` thresholds without that division, and filters
“No Rank” from the rank display.
[URLs][urls], [scenario service][scenario-service],
[progress parser][progress-parser].

CSD's [API notes](../kovaaks_api_notes.md) already cover the progress endpoint
and later benchmark-importer observations. Treat RefleK's behavior as a lead
to verify against a controlled response before promoting it into our API
contract. This update does not silently convert another client's assumptions
into verified endpoint facts.

Benchmark semantics deserve particular care. The inspected
[Voltaic energy code][energy] calculates group energy from scenario
thresholds. The open [PR #50][rank-pr] proposes an overall-energy rank
and explicitly distinguishes it from the complete rank; it was unmerged
when checked. Do not use an unmerged correction as proof of current
desktop behavior or treat benchmark-specific energy as one universal formula.

There is now a separate public API and research project:

- The [API documentation][api-readme] describes raw-run archives, scenario
  and player browsing, and benchmark endpoints. These could provide varied
  test data for a separately scoped experiment; the deployed service and
  its retention/privacy promises were not audited here.
- The [research repository][research-tree] names mouse-deviation GRU and
  recommendation-autoencoder workspaces. At the inspected revision the
  tree contains workspace documentation, a design file, and requirements,
  but no training scripts or model weights. The desktop recommendation and
  mouse-analysis paths inspected here are heuristics. The website's
  dataset-size and machine-learning descriptions are not evidence of
  validated or deployed coaching models.

No population dataset was downloaded. If one is used later, verify its
provenance, attribution requirements, scenario coverage, sampling biases,
and suitability for the question before treating it as ground truth.

## 10. Upstream reports: leads, not reproduced conclusions

Open reports inspected on 2026-10-28 include benchmark rank disagreement
[#14][rank-issue], incorrect benchmark membership [#45][catalog-issue],
scenario-launch instability [#18][launch-issue] and [#46][launch-issue-new],
and a black native window [#40][window-issue]. Open PRs [#48][gpu-pr],
[#49][build-pr], and [#50][rank-pr] propose fixes in related areas.

They suggest concrete checks for anyone adopting similar features:
benchmark-specific ranking fixtures, catalog provenance, repeated
deep-link launches during play, a recovery path usable when the UI fails,
and reproducible dependency packaging. The reports do not establish
frequency, root cause, or that RefleK's caused every reported game failure.

## Verification and follow-up questions

The retained survey is supported by source inspection, the official schema,
the frontend tests/build, and the four calculation probes. It does not
claim native runtime performance, coaching efficacy, or a full security
audit.

Reproduction from the pinned desktop source, with Node/npm available:

```text
npm ci --ignore-scripts --no-audit --no-fund
node node_modules/vitest/vitest.mjs run --reporter=dot
npm run build
```

Run those inside `frontend/`. The 150-test count is the unmodified upstream
suite. The four added probes are separate, local research files.
This session kept the source clone, probe file, and logs under this
worktree's ignored `ignore/research/` directory; they are not CSD
production dependencies. The probe inputs and outputs above remain useful
without that scratch checkout.

Next investigations should answer bounded questions:

1. Can recorded kill rows explain a useful per-bot difference across a
   representative mix of clicking, switching, and tracking scenarios?
2. Which within-run question requires `.perf` instead of CSV, and how will
   missing sidecars or incompatible clocks be shown?
3. What does the player need beside a comparison to decide what to practice
   next without receiving an unsupported diagnosis?
4. Do real CSD histories expose a detail-loading bottleneck that warrants
   caching or progressive loading?
5. Is there a real encoding failure that a small parser change can recover?

The strongest opportunity is better explanations from existing evidence.
The main restraint is preserving what each measurement actually means.

[desktop]: https://github.com/ARm8-2/refleks/tree/e1ef9437169eee484b03a723887f7ece86a7c4f8
[release]: https://github.com/ARm8-2/refleks/releases/tag/0.10.0
[proto]: https://wiki.kovaaks.com/performance.proto
[watcher]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/internal/watcher/watcher.go
[defaults]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/internal/constants/defaults.go
[mouse-tracker]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/internal/runs/mouse/tracker_windows.go
[mouse-analysis]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/frontend/src/features/history/lib/mouseAnalysis.ts
[stats-parser]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/internal/runs/kovaaks/stats.go
[settings-defaults]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/internal/settings/settings.go
[history-state]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/frontend/src/features/history/hooks/useHistoryPageState.ts
[inspector]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/frontend/src/features/history/components/HistoryRunDetailPane.tsx
[overview]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/frontend/src/features/overview/hooks/useRecentSessionSnapshot.ts
[widget]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/frontend/src/shared/components/Widget.tsx
[benchmark-page]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/frontend/src/features/benchmarks/pages/BenchmarkDetailPage.tsx
[perf-parser]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/internal/runs/kovaaks/performances.go
[analysis-chart]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/frontend/src/features/history/lib/analysisChart.ts
[scenario-analysis]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/frontend/src/features/history/lib/scenarioAnalysis.ts
[history-models]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/frontend/src/features/history/lib/historyModels.ts
[store]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/frontend/src/shared/hooks/useStore.tsx
[ingest]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/internal/runs/ingest.go
[sensitivity]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/frontend/src/features/history/components/PerformanceVsSensWidget.tsx
[detail-recs]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/frontend/src/features/benchmarks/lib/detailRecommendations.ts
[benchmark-recs]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/frontend/src/features/benchmarks/lib/recommendations.ts
[runtime]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/internal/runs/runtime.go
[target-inference]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/frontend/src/features/history/lib/targetInference.ts
[history-copy]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/frontend/src/shared/lib/i18n/messages/en/history.ts
[capture]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/internal/runs/screen/capture_windows.go
[replay-ui]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/frontend/src/features/history/components/inspector/ReplayTab.tsx
[cleanup]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/internal/runs/cleanup.go
[codec]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/internal/runs/codec.go
[run-store]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/internal/runs/store.go
[run-index]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/internal/runs/index.go
[run-resource]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/frontend/src/features/history/hooks/useRunResource.ts
[virtual-list]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/frontend/src/features/history/components/VirtualList.tsx
[catalog]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/internal/benchmarks/catalog.go
[progress-fetcher]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/internal/benchmarks/progress_fetcher.go
[benchmark-service]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/internal/benchmarks/service.go
[cloud]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/internal/runs/cloud_sync.go
[environment]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/internal/runs/environment/collector.go
[steam]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/internal/steam/steam.go
[scenario-service]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/internal/scenarios/service.go
[i18n]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/frontend/src/shared/lib/i18n/core.ts
[motion]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/frontend/src/shared/lib/motion.ts
[urls]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/internal/constants/urls.go
[progress-parser]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/internal/benchmarks/progress_parser.go
[energy]: https://github.com/ARm8-2/refleks/blob/e1ef9437169eee484b03a723887f7ece86a7c4f8/internal/benchmarks/rankcalc/vt_energy.go
[rank-pr]: https://github.com/ARm8-2/refleks/pull/50
[api-readme]: https://github.com/ARm8-2/refleks-api/blob/f7a24b74bd04f97abe84a9c7d23358b9e5687c45/README.md
[research-tree]: https://github.com/ARm8-2/refleks-research/tree/a30e4cd4f91c2553e9a6e0fefcd0e783508a4433
[rank-issue]: https://github.com/ARm8-2/refleks/issues/14
[catalog-issue]: https://github.com/ARm8-2/refleks/issues/45
[launch-issue]: https://github.com/ARm8-2/refleks/issues/18
[launch-issue-new]: https://github.com/ARm8-2/refleks/issues/46
[window-issue]: https://github.com/ARm8-2/refleks/issues/40
[gpu-pr]: https://github.com/ARm8-2/refleks/pull/48
[build-pr]: https://github.com/ARm8-2/refleks/pull/49
