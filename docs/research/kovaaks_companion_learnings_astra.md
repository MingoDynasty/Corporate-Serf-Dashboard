# Lessons from KovaaK's Companion

Date: 2026-10-28
Author: gpt-6-astra · effort: xhigh

Research note; recommendations remain unratified.

## Takeaway

KovaaK's Companion makes a training result easy to inspect: a session leads
to a scenario, a scenario to a recorded run, and the run's chart to the same
moment in its video. CSD can learn most immediately from that continuity,
its session summaries, and a verified alternative for discovering a
KovaaK's username. Its coaching system offers useful ways to limit advice,
but its causal language and several data assumptions should not be adopted
without stronger evidence. Recording is a substantial additional product,
not a prerequisite for improving our run analysis.

## Evidence and scope

- Inspected source at
  [`9c634585a325aab3c1a22fb4c453d87208bb90b7`][snapshot], the main-branch
  head and application version **1.19.7** on the survey date. The latest
  [release][release] was published on October 27. The repository was created
  on October 7; version numbers do not establish a long operating history.
- Read the product README, release/build configuration, relevant Core and
  WPF code, browser userscript, storage and update paths, and the author's
  advice redesign document. Inspected five committed screenshots: Home,
  playlist, scenario overview, session and replay. Screenshots illustrate
  the supplied UI; their running build and data were not independently
  established.
- Executed isolated probes of the actual CSV parser and advice-test code
  using PowerShell's C# compiler. The only parser substitution expanded its
  generated regular-expression declaration into the equivalent ordinary
  `Regex` factory, because `Add-Type` does not run source generators.
  Results and inputs are recorded below. Scratch is in
  `ignore/scripts/companion-research/`; no competitor code is added to CSD.
- With maintainer permission, verified the benchmark-to-username route
  against KovaaK's public API using the public example account already in
  our API notes. Retained only the match result and request coordinates,
  not the returned username.
- CSD baseline:
  [`911ca00986c109de614861e9db2613c326d52d6c`][csd-snapshot]. Read current
  capability specs and the run model, then compared the earlier
  [Aimcurve Astra](aimcurve_learnings_astra.md),
  [Aimcurve Opus](aimcurve_learnings_opus.md), and
  [RefleK's](refleks_learnings.md) surveys. Those other competitors were
  not surveyed again.
- The desktop application and browser extension were not installed or run.
  Capture overhead, synchronization accuracy, keyboard/screen-reader
  usability, update recovery and actual coaching benefit remain unmeasured.
  This is a product and source investigation with targeted executions,
  not an end-to-end certification of the released executable.

## What the app offers

Companion is a portable Windows tray application built with C#/.NET 10 and
WPF. It combines benchmark progress, a calendar and session history,
scenario analytics, automatic game recording, optional webcams, and a
replay player with a reconstructed mouse trail. Its source separates the
Core calculations and storage from the WPF shell. The catalog contains
132 benchmark groups and 268 difficulty entries; the README calls these
132 benchmark playlists. [README][readme], [catalog][catalog],
[project files][projects].

The useful comparison is what each app helps the player do:

| Player task | Companion at the inspected revision | CSD at the baseline | Lesson |
| --- | --- | --- | --- |
| Judge normal performance | Score averages, history, comparisons and rule-based advice | Defined Typical Score, spread, recency and a session-start baseline | Keep our established semantics; add useful interpretation carefully |
| Review a whole sitting | Calendar, session card, per-scenario and aim-kind summaries, advice and image export | Sessions and visits organize Run History; Home is still a placeholder | A coherent session summary is a real opportunity |
| Explain one attempt | Video, trail, per-second chart and mouse metrics | Run summaries and history; `.perf` already supports pace classification | Extend within-run evidence before taking on recording |
| Choose and launch practice | Favorites, goal filters, rank ladders and Steam launch actions | Playlist tables, Typical Rank, PB-based Next Rank and sensitivity comparisons | Reduce the steps from finding a scenario to playing it |
| Recover scores from another PC | Server bests and recent scores merged with local history | Local runs underpin performance statistics; online data supplies standing and metadata | Explore recovery only with explicit source and coverage semantics |
| Use another benchmark website | Optional userscript plays local recordings on Evxl and Voltaic | Links and existing online integrations | Preserve context across tools; avoid duplicating calculations |

CSD references: [Home](../specs/home.md), [Run History](../specs/run_history.md),
[Typical Score](../specs/typical_score.md), [sessions](../specs/sessions.md),
[playlists](../specs/playlists.md).

## Product lessons

### Make the session a useful destination

**Observed in screenshots and source:** Home connects an activity calendar
with the sessions on the selected day. A session opens into its runs,
summary figures, comparisons and advice. A floating control returns to the
live session when its card is below the viewport. Unless exiting with the
game, the application opens the session summary when the game closes.
These provide a natural before-play, between-run and after-play flow.
[Home and session UI][home-ui], [application lifecycle][app-host],
[session screenshot][session-image].

**Recommendation:** Design a manually accessible session summary using our
existing run store and session model. Lead with the scenarios practiced,
their results relative to their own session-start typical values, notable
runs and links into Run History. Show elapsed session span separately from
the sum of trustworthy run durations, with coverage when some durations
are unknown. A calendar is useful navigation if it opens the corresponding
sessions; a decorative streak chart alone adds less.

Companion does not establish that a single cross-scenario score is needed.
Its `SessionAdvice` first divides each run's score by its own scenario's
baseline, then combines the relative values. This avoids averaging raw
scores with different units, but the result remains weighted by run count,
and raw score ratios are unsuitable for our time-scored pace semantics.
Start with per-scenario comparisons and make any aggregate a separate
design judgment. [Session advice][session-advice].

Its session identity is also different: live sessions are tied to a game
launch and persisted; untagged history uses a 20-minute gap. CSD deliberately
derives sessions from breaks longer than 30 minutes. Reusing its summary
idea does not require changing our session definition or adding a game
process watcher. [Session grouping][session-code], [live sessions][live-session].

### Carry one selected run through every view

**Observed:** The replay screenshot keeps a run list alongside the video
and chart. The overview occupies the same scenario context. The browser
player's chart follows the video, dragging seeks, and its handoff link
contains a replay ID and playback position. The desktop player includes
keyboard controls for playback, seeking and the trail.
[Replay screenshot][replay-image], [replay UI][replay-ui],
[browser player documentation][web-doc].

**Recommendation:** Treat the selected run and selected time as shared
state in a future run viewer. A bot or kill selection should focus the
relevant chart segment; a chart selection should identify the corresponding
event. Opening details should preserve the scenario, session and way back.
Our current chart/list hover and latest-run highlighting already provide
part of this continuity; this extends them into run detail.

The first useful version can work from per-kill CSV rows and `.perf`
telemetry, with no video. The earlier Aimcurve surveys made the same
within-run case; Companion strengthens the case for a connected interaction,
not the case for any particular layout or framework.

### Put a small amount of interpretation near its evidence

**Verified in source:** `AdviceTests` uses 1,000 deterministic random
permutations, a Benjamini–Hochberg-style correction based on tests counted,
and a false-discovery threshold of 0.1. It selects at most one item from
each of four areas: current state, pace, movement and practice. The default
maximum is four. Process comparisons require at least 12 measured runs and
a standardized difference of at least 0.5, along with metric-specific
thresholds. Session baselines use up to 20 prior runs per scenario and
require at least five. [Advice selection][advice],
[scenario rules][scenario-advice], [session rules][session-advice].

This is more considered than a list of fixed-threshold tips. The author's
[redesign document][advice-design] explicitly identifies circular advice,
multiple comparisons, conflicting recommendations and an all-time baseline
that flatters improving players. Although that document still describes a
proposal, the inspected code implements several of its changes. The code,
not the document's old description, establishes the behavior above.

**Recommendation:** Borrow the restraint: a few relevant observations,
minimum support, a stable comparison, and permission to show nothing.
Each observation should expose the runs and dates behind it. CSD already
has a stronger product contract for its session-start baseline: a median,
minimum support, recency and explicit pace handling. Reuse that contract
instead of introducing a second meaning of normal performance.

**Do not borrow the certainty of the coaching copy.** A statistically
unusual score drop does not prove fatigue or establish that stopping will
help. The code says a large drop rarely recovers through continued play,
but its calculation compares two groups of five scores; it does not measure
recovery after a drop. Likewise, correlation between a movement metric and
score is not an estimated benefit from changing that movement.

Specific limits matter before adopting these tests:

- Consecutive runs are not necessarily interchangeable independent samples.
  Practice, fatigue, settings changes and scenario revisions can affect
  both the metric and score. Permutation arithmetic alone does not remove
  those dependencies.
- The sensitivity rule selects the best average among eligible settings,
  then tests that selected setting against the common setting. It does not
  repeat the setting-selection step inside each shuffle. By contrast, the
  pace rule does repeat its best-window search during permutation. That
  difference is material when many sensitivities were tried.
- Un-tested count rules such as plateau and practice spread can still
  produce advice. A card appearing does not universally mean it passed a
  significance test.
- The p-value is not the probability that the explanation is true. The
  ranking expression `Effect * (1 - Q)` does not establish expected score
  improvement. These are interpretation limits, not claims that the entire
  calculation has been statistically validated or invalidated.

A useful first CSD observation would describe a result and offer an
inspection action. Prescriptive coaching needs its own evaluation against
held-out sessions and plausible alternative explanations.

### Give sensitivity comparisons their sample and time context

Companion's scenario screenshot shows counts, individual run points,
average and best for each sensitivity. `ScenarioInsights` groups known
cm/360 values rounded to two decimals and displays five groups selected
by their best score. The advice rule separately requires four runs per
group and compares the usual sensitivity only within the date range of
the candidate setting. [Overview screenshot][overview-image],
[grouping source][scenario-insights], [advice source][scenario-advice].

**Recommendation:** Add sample size and dates to the evidence a player uses
in Score vs Sensitivity, and keep Typical Score or a robust group summary
distinct from a group's PB. Temporal overlap is a useful comparability
check, not a controlled experiment. Avoid telling the player that a
scenario rewards a particular physical technique solely because one
sensitivity averaged higher. Selecting groups by their best run can also
hide ordinary settings; display selection needs an explicit rule.

### Shorten the path from analysis to practice

Companion supplies explicit Steam actions for both a scenario in challenge
mode and a playlist by sharecode. Its filters express concrete browsing
intent: recent play, no recent play, never played, favorites, rank progress
and PB activity. [Launch URLs][launch], [filter implementation][home-ui].

There are useful warnings in the filter semantics. Recent means at most
14 days, stale means at least 30, and the PB-streak filter accepts a PB in
any of the last four weekly buckets. It is not necessarily a consecutive
streak. All goal filters reject a maxed tier, even though someone may want
to maintain that skill. These choices should not quietly become training
recommendations.

**Recommendation:** Test a clear Play action in our playlist and scenario
surfaces. No Steam launch URI was found under CSD's `source/` at the
baseline. Check names containing punctuation, Steam not running and the
browser's external-protocol prompt before designing around it. This repeats
an Aimcurve lead and adds a second implementation, not an end-to-end test
of the URI. Filters should explain their exact populations and retain
maintenance as a legitimate reason to revisit a completed benchmark.

### Give benchmark progress a legible visual hierarchy

The playlist screenshot groups scenarios by skill and subcategory, with
rank thresholds visible across each row. Home combines favorites, a
calendar and benchmark cards; profile and session image export make a
result shareable. These provide concrete references for a future Overview
and for explaining the next threshold. [Playlist screenshot][playlist-image],
[Home screenshot][home-image], [profile export][profile-export].

The desktop screenshots are dense, with small secondary text and color
doing considerable work. They do not demonstrate second-monitor
legibility, phone usability or screen-reader support. CSD should retain
text labels, keyboard semantics and accessible alternatives to charts.
Take the hierarchy and the routes into detail, then test them against our
glance-oriented use. Image sharing is optional and separable from analysis;
it also needs deliberate control over which identity and history it exposes.

## Data and engineering lessons

### A conditional SteamID to username lookup works

**Verified live:** Companion's resolver starts with benchmark progress for
a SteamID64. A ranked scenario supplies `leaderboard_id` and
`leaderboard_rank`. Fetching that position with `max=1` exposes a
`webappUsername`; the resolver accepts it only when the row's `steamId`
exactly matches the requested identity. [Resolver source][api].

The approved check succeeded with benchmark 458: leaderboard 98330,
position 14738, one returned row, exact Steam ID match and a nonempty
username. The position
is an observation on October 28, not a stable fixture. This proves a
conditional route, not universal reverse lookup.

**Impact for CSD:** Our [API notes](../kovaaks_api_notes.md) previously said
that going from a SteamID64 to a username was impossible. The unavailable
direct profile endpoints do not support that broader conclusion; the
notes are corrected with this evidence. A future identity-detection
fallback could use likely played benchmarks when Steam persona matching
fails. It should remain bounded, verify the exact identity, preserve
current privacy-sensitive logging and offline behavior, and treat no
usable rank or a moved position as an unresolved lookup. No detection
behavior changes in this research.

### Preserve the source of a score and the limits of its history

Companion accumulates server recent-score snapshots and combines them with
local runs. Its API code reads server bests through `total-play`, capped
at twenty pages of 100 entries, and reads a scenario's recent list through
`last-scores/by-name`. A server-only score has no accuracy, kills or
settings; `FromCloud` sets start equal to end. A known all-time best may
have no known date. [API][api], [score merging][history],
[run record][run-record], [persistent score store][stats-store].

This makes a new installation useful even when some files are on another
PC. It does not reconstruct complete history, session lengths or mouse
details. CSD's existing API notes also warn that `total-play` can lag
current scores, so it should not silently become the authority for a
fresh PB or leaderboard result.

**Source-level risks:** `ScenarioHistory` drops a server record when a
local end time is less than ten seconds away, without requiring equal
scores. That can conflate distinct short attempts. Import deduplication
also uses a three-second name-to-end tolerance. The analytics run record
does not retain a scenario hash, although the richer CSV/replay statistics
do. Thus preservation in a raw record does not guarantee that a derived
comparison separates versions.

**Recommendation:** If cloud history is pursued, retain provenance,
unknown fields, coverage dates, the undated-best distinction, and an
explicit reconciliation contract. Do not feed an incomplete server list
into our last-20-run Typical Score as if it were complete local history.
CSD intentionally pools scenario versions for Typical Score today while
restricting pace eligibility by version; changing that is a proposal,
not a research cleanup.

### Treat motion metrics as derived observations

Companion captures Windows Raw Input, maps mouse counts into angular
movement using recorded settings, and aligns the run with video using a
wall-clock/QPC anchor sampled per save. Unknown sensitivity conversion or
incomplete buffer coverage is represented in the replay metadata.
[Trajectory construction][trajectory], [replay saving][replay-saver].

Its mouse metrics are ingenious but have narrower meanings than their
labels may suggest:

- Reaction measures time from the previous kill to movement above a
  30-degrees-per-second threshold. It has no observed target-spawn or
  visual-detection time, so it is not a general reaction-time measurement.
- Path efficiency divides the direct angle between the interval's endpoint
  view directions by the distance traveled. Moving targets, target choice
  and ongoing motion affect the interpretation; the calculation has no
  target geometry.
- Click-after-stop measures against a movement threshold and an estimated
  kill-shot match. It is not an instrumented game event saying the player
  arrived on a target.
- Advice classifies aim kind from name substrings before considering
  measured hold ratio. `pasu` is classified as tracking even though the
  bundled data puts Pasu Voltaic Easy in Clicking. That can select the
  wrong family of advice. [Mouse metrics][mouse-stats],
  [bundled thresholds][tier-data], [scenario advice][scenario-advice].

Shot colors are also inferred. `ShotClassifier` estimates a clock offset,
matches kills to nearby left-button events, and uses CSV counts and
approximately one-second `.perf` buckets to constrain the remaining
outcomes. It explicitly preserves unknown outcomes. Held-fire accuracy is
interpolated between bucket centers. Those colors are useful explanatory
overlays, not authoritative per-shot telemetry. [Shot classifier][shots],
[held accuracy][held].

**Recommendation:** Preserve measured versus inferred versus unavailable
as distinct states. Start with per-bot kills, hits/shots and TTK that CSV
rows directly support. A motion-analysis proposal would need corpus
validation, settings and clock checks, scenario applicability and neutral
names for its proxies before it could support coaching.

### Recording requires its own performance and retention design

The recording service follows the game process, uses embedded libobs
window capture, tries NVIDIA/AMD/Intel hardware encoders, and extracts
finished-run clips from a rolling packet buffer. Defaults are 60 FPS and
ten minutes of buffer, with five seconds before a run and ten after.
The README advertises higher configurable frame rates and multiple webcams;
those are options, not measured performance guarantees.
[Recording service][recording], [capture backend][capture],
[video defaults][video-options].

Storage policy is thoughtful: retain stats and mouse data after deleting
video, support size/age limits, optionally keep only improved runs within
a session or save only PB videos, and protect important recordings.
The archive distinguishes irreplaceable evidence from disposable caches,
uses SQLite WAL with full synchronization and transactions, and provides
backup/corruption handling. [Cleanup rules][cleanup], [archive][archive],
[settings][settings].

**Recommendation:** Retain this distinction if CSD ever records material
that cannot be reconstructed from the stats folder. Do not adopt a database
or native capture stack solely for parity. A recording decision needs
measurements of frame-time impact, GPU/CPU load, high-polling-rate input,
long/paused runs, storage growth and crash recovery. Resource limits should
have visible meaning: Companion defaults both size and age limits to zero,
meaning unlimited, and protected videos can leave a configured cap exceeded.

Retention also affects analysis. The browser player's per-second comparison
loads recordings with video, while its score history can include runs whose
video is gone. PB-only retention therefore creates different populations.
Any comparison should identify its support rather than labeling survivors
as an unconditional average. [Browser player documentation][web-doc].

### The file parser needs stronger boundaries than its happy path

The following probes executed the inspected parser. Every filename was
`Probe - Challenge - 2026.10.28-12.00.00 Stats.csv`; the text contained
`Scenario:,Probe`, the listed fields and `Score:,100` unless specified.
Duration is parsed `End - Start`, the same expression used by `RunRecord`.
These are synthetic boundary checks, not estimates of how frequently real
players encounter them. [CSV parser][parser], [run record][run-record].

| Input | Observed result | Implication |
| --- | --- | --- |
| `Challenge Start:,11:59:00.000` | 61 seconds | Parser uses filename end plus one second, an upper bound rather than the exact finish |
| Start `11:58:30.000`, `Pause Duration:,30` | 91 seconds | Pause duration is not subtracted; this is unsuitable as active playtime |
| No challenge start | 1 second | Unknown duration becomes an invented positive duration |
| Start `12:00:00.500` | 86,400.5 seconds | A start within the filename's truncated second is interpreted as the previous day |
| Start `11:59:00.123456` | `FormatException` | The timestamp parser requires exactly three fractional digits |
| No score | Score 0 | A missing required value becomes a valid-looking value |
| `Score:,NaN` | Non-finite score accepted | Parsing alone does not guard downstream calculations or serialization |

As an execution sanity check, the actual `AdviceTests.SplitP` returned
1 for two groups of five scores all equal to 100. In the same test object,
five scores of 100 against five of 80 returned approximately 0.00799.
This checks execution of the test routine, not the calibration or causal
validity of the coaching rules.

The live watcher waits for two equal reads, 300 ms apart by default, with
up to 40 attempts. That is a useful stability check, but not proof of a
complete valid file: a stable partial file without a score already parses
as zero. The path enters `_seen` before success and is not removed after
failure, so a later change event in that watcher cannot retry it. Startup
ingest offers another opportunity later; this source finding is scoped to
the live watcher, not permanent loss in every circumstance. [Watcher][watcher].

**Recommendation:** Carry these cases into any new multi-file run-viewer
ingestion contract. Preserve CSD's finite-score guard, successful-import
identity, pause-aware trusted duration and unknown-duration state. CSD's
current [ingestion spec](../specs/run_ingestion.md) also records remaining
limits: bounded retries on the observer thread and no periodic
reconciliation. We should not describe our ingestion as risk-free either.

Companion waits briefly for a fresh CSV's `.perf`, then saves without it
when unavailable. This reinforces the existing Aimcurve lesson that the
two files are not a single atomic event. Its parser comment says there is
no published `.perf` schema, but the vendor's
[schema](https://wiki.kovaaks.com/performance.proto) was retrievable during
this survey. Use that source and our existing pace parser as the starting
point for format work; Companion does not add a new authoritative format.
[Performance parser][perf], [replay saving][replay-saver].

### Cross-tool integration can preserve context without a cloud service

The current userscript supports Evxl and Voltaic. It reads an app-generated
index through the userscript manager, then reads clips from a folder the
user selects through the browser's File System Access API. It stores the
handle per site, refreshes the index, and can hand off to the desktop app
at a replay/time pair. This implementation does not need a replay HTTP
server; the architecture overview's loopback-server description is stale.
[Generated files][web-files], [userscript][web-script],
[browser architecture][web-doc].

It reuses advice and statistics generated by the C# core rather than
reimplementing those calculations in JavaScript. That is a particularly
useful engineering lesson for any additional CSD surface.

The setup is not frictionless: a userscript manager, local-file access,
Chromium folder-picking support and permission renewal are involved, and
site DOM changes can affect placement. The selected website origin also
matters to the folder permission. Before adopting such integration, define
exactly which local files are exposed and to whom. For CSD, opening the
relevant scenario or run through a normal app link is a smaller first
step than maintaining a browser extension.

### Separate convenient installation from demonstrated reliability

Companion detects Steam libraries, ships one executable, supports four
languages and offers tray startup. Its default settings enable startup
with Windows and automatic updates. The updater checks the downloaded
asset against GitHub's supplied SHA-256 before replacing the executable.
[Path detection][paths], [settings][settings], [updater][updater].

The inspected HTTP call sites fetch account and score data from KovaaK's
and releases from GitHub. Replays and their archive are local; external
benchmark pages are separate integrations. The README's no-telemetry claim
is consistent with those inspected paths, but no network capture was
performed. Raw Input is started with the app and buffers mouse events in
memory; the game process controls video recording, and a completed run
selects the interval to save. A future capture design should explain that
distinction instead of treating all background capture as one switch.
[Application lifecycle][app-host], [replay saving][replay-saver].

The public tree inspected here contains no automated test project. Its
sole workflow builds and publishes releases, with a version/tag check;
the contribution guide asks for a successful build. This is evidence of
the visible validation process, not proof that the author has no private
tests. The rapid release history and absence of public issues cannot
establish stability or adoption. [Release workflow][workflow],
[contribution guide][contributing].

CSD already provides installation/update management and Steam-based
discovery. The incremental lessons are clear setup communication,
intentional background behavior and a single source for localized copy.
There is no evidence here that changing from Dash to WPF would improve
our product. The inspected license declares GPL-2.0-or-later and identifies
older releases through 1.4.3 as MIT; this survey transfers ideas and
observations, not implementation code. [License declaration][license].

## Recommended follow-up order

These are research priorities, not a roadmap change.

| Priority | Follow-up | Scope and evidence needed |
| --- | --- | --- |
| First | Consider the benchmark-based identity fallback | Small investigation backed by one live success; test unplayed benchmarks, moved positions, exact identity checks, bounded requests and privacy handling |
| First | Try scenario and playlist Play actions | Small interaction experiment; verify real Steam behavior and browser prompts |
| Next design | Session summary and route into its runs | Moderate product design using existing sessions and session-start Typical Score; prove that players can judge the session without mixing incomparable scores |
| Next design | Within-run CSV and `.perf` viewer | Moderate to large; start with per-bot evidence and linked selection, validate scoring models and coverage, leave video optional |
| Supporting improvement | Better context for sensitivity comparisons | Counts, dates and comparison populations; distinguish exploratory association from a recommended setting |
| Separate research | Bounded observations or coaching | Validate proxies, sample dependence, false discoveries and wording before prescribing behavior; test on unseen sessions |
| Defer pending demand | Automatic video/raw-input capture and browser userscript | Large operational and product surface; measure benefit against resource cost, storage, permission and maintenance burden |

The earlier surveys exposed sources of data and ways to chart recent form.
CSD has since shipped Typical Score, session organization, pace handling
and connected history interactions. Companion's new contribution is chiefly
how these pieces form a reviewable training session, plus the identity
fallback verified here. Its weaker assumptions are useful evidence for
why our existing contracts matter.

[snapshot]: https://github.com/dededed1024/kovaakscompanion/tree/9c634585a325aab3c1a22fb4c453d87208bb90b7
[release]: https://github.com/dededed1024/kovaakscompanion/releases/tag/v1.19.7
[csd-snapshot]: https://github.com/MingoDynasty/Corporate-Serf-Dashboard/tree/911ca00986c109de614861e9db2613c326d52d6c
[readme]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/README.md
[catalog]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Benchmarks/BenchmarkCatalog.cs
[projects]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.App/KovaaksCompanion.App.csproj
[home-ui]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.App/StatsView.Home.cs
[app-host]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.App/AppHost.cs
[session-image]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/assets/screenshots/app-session-169.png
[session-advice]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Library/SessionAdvice.cs
[session-code]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Library/PlaySession.cs
[live-session]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Library/LiveSession.cs
[replay-image]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/assets/screenshots/app-replay.png
[replay-ui]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.App/ReplayView.xaml.cs
[web-doc]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/docs/wiki/web-player.md
[advice]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Library/Advice.cs
[scenario-advice]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Library/ScenarioAdvice.cs
[advice-design]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/docs/wiki/advice-redesign.md
[overview-image]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/assets/screenshots/app-overview-169.png
[scenario-insights]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Library/ScenarioInsights.cs
[launch]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/KovaaksLaunch.cs
[playlist-image]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/assets/screenshots/app-playlist.png
[home-image]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/assets/screenshots/app-home.png
[profile-export]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.App/StatsView.ProfileWebp.cs
[api]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Benchmarks/BenchmarkProgress.cs
[history]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Library/ScenarioHistory.cs
[run-record]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Library/RunRecord.cs
[stats-store]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Benchmarks/StatsStore.cs
[trajectory]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Trajectory/TrajectoryBuilder.cs
[replay-saver]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Replays/ReplaySaver.cs
[mouse-stats]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Trajectory/MouseSpeedStats.cs
[tier-data]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Benchmarks/tier-data.json
[shots]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Trajectory/ShotClassifier.cs
[held]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Trajectory/HeldAccuracy.cs
[recording]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Video/RecordingService.cs
[capture]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Video/Obs/ObsCapture.cs
[video-options]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Video/VideoOptions.cs
[cleanup]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Replays/StorageCleaner.cs
[archive]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/ArchiveDb.cs
[settings]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/AppSettings.cs
[parser]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Stats/StatsCsvParser.cs
[watcher]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Replays/StatsWatcher.cs
[perf]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Perf/PerfParser.cs
[web-files]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Web/ReplayWebFiles.cs
[web-script]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Web/replay-player.user.js
[paths]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/PathDetector.cs
[updater]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Update/SelfUpdate.cs
[workflow]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/.github/workflows/release.yml
[contributing]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/CONTRIBUTING.md
[license]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/LICENSE
