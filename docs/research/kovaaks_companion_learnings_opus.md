# Lessons from KovaaK's Companion

Date: 2026-10-28
Author: claude-opus-5-5 · effort: xhigh

Research note; recommendations remain unratified.

## Takeaway

KovaaK's Companion is a Windows tray app whose headline is recording: it
saves every run as a video with the mouse path drawn over it. Around that
recording it builds benchmark standing, sessions, and training advice, and
two of those parts change facts this app relies on. A SteamID64 does lead
to the player's KovaaK's username, through the player's own leaderboard
entry, which our API notes call impossible. The Evxl data this app already
bundles names the rule each benchmark uses for its overall rank, and the
two simplest rules cover 41 of the 132 benchmarks. The most useful product
lesson is its advice engine: the author documented why naive advice rules
mislead, then rebuilt them on permutation tests. That record supports this
app's choice to state verdicts rather than advice. The rest is smaller:
Steam links that start a scenario or a playlist, server scores that fill
gaps in local history, aim kinds read from benchmark categories, and
celebrations for rank-ups.

## Evidence and scope

- Inspected [KovaaK's Companion][repo] at
  [`9c63458`][head], the head of `main` and release 1.19.7 on 2026-10-28.
  External links below are pinned to that revision. The project was created
  on 2026-10-06 and has 392 commits from one developer, 30 GitHub releases,
  about 200 release downloads in total, and no stars at survey time.
- It is a .NET 10 WPF app for Windows. Video comes from libobs, embedded
  from an unmodified OBS Studio build, and the mouse path from Windows Raw
  Input. It speaks English, Korean, Chinese, and Russian; its early commits
  and its wiki are in Korean.
- **License:** GPL-2.0-or-later; releases up to 1.4.3 were MIT. Treated as
  the [RefleK's survey](refleks_learnings.md) treats RefleK's: concepts and
  file-format and API facts are free to use, and no code is copied or
  ported. A copied file would keep its own license and need recording under
  the
  [AGPL decision](../decision_log/2026/2026-08-10-the-project-is-agpl-30-and-contributors-sign-nothing.md).
- **Read here:** the README, the two wiki pages, and the Core library's
  `Benchmarks/`, `Library/`, `Stats/`, and `Perf/` folders, with the
  KovaaK's API client in full. The 1,502-line rank calculation was read for
  its structure and for its two simplest rules. Three read-only subagents
  (`claude-sonnet-5-5`) inventoried the WPF interface, the recording and
  mouse code, and the git history. Their claims used below were spot-checked
  against the source, and statements that rest on them say so.
- **Verified live, 2026-10-28:** three probes against KovaaK's public API,
  each using the top players of one public leaderboard as subjects. The
  scripts printed match results, counts, ranges, and field names only, never
  names, IDs, or scores. They were not kept; findings 1 and 4 say what each
  did.
- **How it was built:** 339 of the 392 commits name Claude Sonnet 5.5 as
  co-author and 9 name Claude Opus 5.5. The advice rebuild in finding 3 was
  committed by a Discord-driven bot the morning its review was written, and
  the review is still marked as a proposal awaiting approval.
- **Not done:** the app was not built or run, so its recording and
  interface are known from source and screenshots only. The repository has
  no automated tests, and its only workflow builds releases, so its
  statistical code is described as written, not as checked.
- Compared against this repository at `911ca00`.

## Findings

### 1. A SteamID64 leads to a KovaaK's username after all

**Observed:** The app learns the player's webapp username from their
SteamID64 alone, in two requests ([`ResolveUsernameAsync`][api]).
`/benchmarks/player-progress-rank-benchmark` takes a `steamId` and returns,
for each scenario, its `leaderboard_id` and the player's `leaderboard_rank`.
The global leaderboard page at index `rank - 1` with `max=1` is then the
player's own entry, and it carries `steamId` and `webappUsername`. It tries
up to six benchmarks, those with the most locally played scenarios first.
It stops after three scenarios of one benchmark, because a rank can move
between the two requests. The SteamID64 comes from Steam's
`loginusers.vdf` (`MostRecent`, then `AutoLogin`, then the newest
`Timestamp`), and failing that from the registry value
`HKCU\Software\Valve\Steam\ActiveProcess\ActiveUser`, a 32-bit account ID
that becomes a SteamID64 by adding 76561197960265728
([`SteamAccount`][steam]).

**Verified live:** Six lookups, two scenarios for each of three players
taken from a public leaderboard, all returned the player's own entry with
the matching username. Their leaderboard positions ran from 2 to 3,226.

**Our baseline:** [kovaaks_api_notes.md](../kovaaks_api_notes.md) states
"**No reverse lookup exists**" and "Going from a SteamID64 to a username is
impossible", and the docstring of `source/config/identity_detection.py`
says the same. Detection therefore probes each local Steam persona with
`/user/profile/by-username` and keeps a profile whose `steamId` matches.
That cannot find a player whose persona differs from their username.

**Limits:** The lookup needs a leaderboard entry on a scenario of a
benchmark that is tried. It costs at least two requests per attempt, and a
rank that moves between them misses. A player who has never played a
benchmark scenario is not found this way.

**Recommendation:** Correct the API note and the docstring, which state as
fact something that is false. Then consider the lookup as detection's
fallback when no persona matches, which is the case detection cannot solve
today. It complements the persona probe, which needs no benchmark history,
rather than replacing it. The bundled benchmarks' IDs are known, so the
order the competitor uses is available here too.

### 2. Each benchmark's overall-rank rule is already in our bundled data

**Observed:** The app shows an overall rank and a progress bar for every
benchmark difficulty, computed locally ([`TierCalculation`][tiercalc]). The
rule comes from Evxl's `rankCalculation` field, one value per benchmark,
and the app implements all 46 values in one file. Two rules are simple:

- `basic`: each subcategory is ranked by its best scenario, and the overall
  rank is the lowest of those. Any unranked subcategory leaves the overall
  unranked.
- `complete`: the overall rank is the highest rank every scenario has
  reached.

The overall rank is the higher of the `complete` result and the method's
own, so `basic` can lift a benchmark above its weakest scenario. The other
methods are energy sums, point tables, and counts of scenarios above a
rank, several of which read the rank ladders of the benchmark's sibling
difficulties. The code's comments first called this "evxl's rank
calculation". A later commit rewrote it "from a written spec of the
playlist rules" and removed the Evxl wording; that spec is not in the
repository. The app had used the endpoint's own progress until 2026-10-13,
when it switched to this local calculation.

**Verified here:** This app's `resources/evxl/benchmarks.json` carries the
same field for all 132 benchmarks, with 46 distinct values: `basic` 37,
`generic-energy` 19, `aplus-alt` 9, `complete` 4, `generic-energy-alt` 4,
`generic-energy-uncapped` 4, and 40 others used by one to three benchmarks
each. Viscose, Voltaic S3, and Revosect S1 use `basic`. Voltaic S4, S5, and
S5.5 use `vt-energy`, and Revosect S4 and S5 have rules of their own. The
benchmark importer's model reads `rankCalculation`, but the generated
playlist files under `resources/benchmarks/` don't carry it.

**Our baseline:** The scenario table shows each scenario's Rank, Next Rank,
and Typical Rank. Nothing shows a benchmark's overall rank. The endpoint's
own `overall_rank` is not a substitute: it follows one energy model for
every benchmark. In a check made for this project on 2026-08-11, not
recorded in the docs, that model disagreed with Anima Micro Benchmark v2's
published rule, which is the `basic` rule. Evxl assigns that benchmark
`basic`, so on the one benchmark checked by hand the field and the
published rule agree.

**Recommendation:** An overall rank is within reach for the 41 `basic` and
`complete` benchmarks with no new data: carry `rankCalculation` into the
generated files and implement those two rules. The other 44 methods need
their meaning written down from sources this project may read, such as
Evxl itself or each benchmark's published rules, and not from the
competitor's code. Run on typical scores, the same rule gives a typical
overall rank, which fits the principle that skill is judged by the typical
run. A design would also need to say what a benchmark whose method this app
doesn't know shows.

### 3. The advice engine documents why advice misleads

**Observed:** The first advice engine was a list of more than 30
independent rules. Each computed one figure and spoke when it crossed a
fixed threshold. On 2026-10-19 the author wrote a review of it, in Korean
([advice redesign][advice-wiki]), naming five defects:

1. **Advice that restates the score.** Runs were split into thirds by
   score, and figures the score is made of were then compared. Time to kill
   on a click scenario, accuracy on a tracking scenario, and time on the
   trigger always differ between the thirds, so the gap carries no
   information.
2. **No line between chance and a real gap.** A 12-run minimum gave groups
   of four, and with more than 30 rules each judged on its own, some would
   fire on noise.
3. **Contradictions.** Three rules judged pace separately and could give
   opposite advice on one screen.
4. **No priority and no targets.** Up to ten tips were shown in code order.
5. **A drifting baseline.** Session advice compared against the all-time
   average, so an improving player beat their average almost every session.

The rebuild ([`Advice`][advice], [`ScenarioAdvice`][scenario-advice],
[`SessionAdvice`][session-advice]) is implemented:

- Every comparison is a permutation test of 1,000 shuffles. A
  Benjamini–Hochberg correction at a false discovery rate of 0.1 covers
  every test run, the silent ones included. A process figure must also
  differ by half a standard deviation.
- Runs are ranked by form, not by raw score: a run's score over the mean of
  the five runs on each side of it. Raw scores rise with practice, so the
  best third would otherwise be the latest runs.
- Only process figures are compared between good and bad runs, such as the
  time from the mouse stopping to the click, path straightness, and
  direction changes.
- Speed against accuracy is judged once, as the accuracy band where
  form-relative scores peak, tested by re-searching the best band on every
  shuffle.
- A sensitivity is compared only with the main sensitivity's runs from the
  same period, so the one tried later doesn't win on practice alone.
- Advice falls into four areas (state, pace, movement, practice), at most
  one each and four in all, ranked by expected effect times confidence.
- A session's runs are each compared with the same scenario's last 20 runs
  before the session, and scenarios are never averaged together.

Not built: tracking whether advice was followed and helped, and suggesting
the weakest benchmark category.

**Where the rebuild still falls short:** The scenario page's mouse-speed
card compares the top and bottom 5% of runs by raw score, and its figures
include firing time and time between kills ([`TopAverageBottom`][topbottom]).
That is the first defect again, in a display instead of a tip, and raw
scores bring back the practice effect that ranking by form removes. Each
group is 5% of the runs but at least one, so below 20 runs the card sets
the single best run against the single worst.

The session rule that tells a player scoring 3% above their recent average
that "whatever you did differently today is worth repeating" asserts a
cause. This app's measurement of the maintainer's runs on 2026-10-08 found
a day effect of about 3% that does not carry into the next session. That
measurement is kept untracked, in `ignore/design-notes/session-results.md`
in the main checkout.

**Our baseline:** The roadmap's principles say to state verdicts, not
advice, and that advice the app vouches for takes strong evidence first.
The latest-run card measures a run against the typical score as it stood
when the session began, the median of the last 20 runs. The competitor
reached the same 20-run, pre-session window independently, using the mean.

**Recommendation:** No change of direction. The review is independent
evidence for the verdicts principle: each of its five defects is a way
advice outruns its evidence. Two of its rules also bind verdicts and
displays. Don't split runs by score and then show a figure the score is
made of. Don't rank runs by raw score when practice moves the scores; rank
them against form. If the app ever moves past verdicts, this gating is the
bar to meet, and its unbuilt follow-up tracking is the missing half.

### 4. Server scores fill in runs the stats folder never saw

**Observed:** Once the username is known, the app downloads the best score
of every scenario the player has played, once, from
`/user/scenario/total-play` ([`GetBestScoresAsync`][api]). For each
scenario the player opens, it asks
`/user/scenario/last-scores/by-name` for the recent runs. A server score
within 10 seconds of a local run's end is that run, and any other is added
as a run with only a time and a score ([`ScenarioHistory`][history]).
Because the server lists only the latest few, every score is kept in a
SQLite archive that the project's own rules call irreplaceable, backed up
daily. Personal bests, ranks, run counts, and the activity calendar
therefore include runs from another PC and from before the install.

**Verified live:** For the top ten players of one leaderboard, the
endpoint returned at most 10 entries each, and one player got an empty
list. Each entry has `score` and an `attributes` object with `epoch`
(milliseconds, as a string), `score`, `kills`, `avgTtk`, `cm360`, `fov`,
`fovScale`, `horizSens`, `vertSens`, `sensScale`, `resolution`,
`pauseCount`, `pauseDuration`, `challengeStart`, `hash`,
`scenarioVersion`, `clientBuildVersion`, `avgFps`, `accuracyDamage`,
`modelOverrides`, and `sensRandomizer`. That is the same set of keys a
leaderboard entry's `attributes` carries, where
[the API notes](../kovaaks_api_notes.md) record `accuracyDamage` as hit
accuracy times 1,000. Here its values ran from 80,473 to 96,026 over 82 runs
of a tracking scenario, which fits that reading, but no run was matched one
to one. The competitor reads only the time and the score.

**Our baseline:** Run history is local only. A run played on another PC
moves the leaderboard position but not the PB card, the typical score, or
the run list. The endpoint is not in
[kovaaks_api_notes.md](../kovaaks_api_notes.md); the
[RefleK's survey](refleks_learnings.md) recommended adding it on 2026-07-03.

**Recommendation:** Document the endpoint and the shape above now. Whether
server-only runs belong in a scenario's history is a product question for
later, and the app now has users who may play on more than one PC. Such a
run likely carries its sensitivity, field of view, and accuracy, but ten
recent runs per scenario cannot rebuild an old history.

### 5. A session as one game launch

**Observed:** A live session is one launch of KovaaK's. The app polls once
a second for the process `FPSAimTrainer-Win64-Shipping` and tags each run
that ends while it runs with that launch's ID, which it stores. Runs played
without the app, and server-only scores, are grouped by a 20-minute gap
once and then keep their grouping ([`PlaySession`][session],
[`LiveSession`][live-session]). When the game closes, the card for that
session opens by itself. The app sees no run start or end as it happens: a
run is found when its stats file lands, and its window is rebuilt from the
file's `Challenge Start:` line and the time in its name. (Process polling
from the recording inventory, spot-checked.)

**Our baseline:** Sessions are runs separated by breaks of no more than 30
minutes ([sessions spec](../specs/sessions.md)). A session as one game
launch is one of four ideas parked for after Run History's first release.

**Recommendation:** Evidence that the idea works in practice, nothing more.
It needs the app running beside the game and a fallback for every other
run, which here is a gap rule. The card that opens when the game closes is
an entry point worth noting for the between-sessions moment.

### 6. Steam links that start a scenario or a playlist

**Observed:** A Play button on a scenario opens
`steam://run/824270/?action=jump-to-scenario;name=<name>;mode=challenge`,
and one on a playlist opens
`steam://run/824270/?action=jump-to-playlist;sharecode=<code>`
([`KovaaksLaunch`][launch]). A third link opens the player's Evxl page for
the difficulty.

**Our baseline:** No `steam://` link exists under `source/`.
[Aimcurve's survey](aimcurve_learnings_opus.md) recommended trying the
scenario link by hand.

**Recommendation:** The same small candidate, on stronger evidence: two
independent apps now ship the `;mode=challenge` form, and this one adds the
playlist link. A Play link fits the scenario table, Run History, and a
playlist's row. Try both by hand first.

### 7. Aim kinds read from benchmark categories

**Observed:** Each bundled scenario gets an aim kind, tracking, switching,
or flick, from keywords in the names of the benchmark categories it sits
in, or the benchmark's name when a category says none. The kind is voted
over every benchmark holding the scenario, with the scenario's own name as
a fallback ([`ScenarioKinds`][kinds]). The Stats tab and the session card
then show one card per kind with runs, time, accuracy, time to kill, and
the most used cm/360. Each card has a "tier level", the mean position of
the player's best scores on their rank ladders, and the highest is marked
"Strongest". The kind also decides which advice applies. (Interface claims
from the UI inventory, spot-checked.)

**Our baseline:** Run History names a scenario's benchmark category.
Nothing groups scenarios by kind across benchmarks.

**Recommendation:** A cheap grouping for *where am I weak?* at the level
players talk about it. The categories in the bundled Evxl data are enough
to vote with. Read through typical scores rather than bests, it would give
a typical rank per kind. The keyword lists are a heuristic and would need
checking against the bundled categories.

### 8. Benchmark standing over time, and goals to filter by

**Observed:** A benchmark's page charts its standing over time: after each
day with a run, the mean over its scenarios of each best score's position
on its rank ladder, with unplayed scenarios counted as zero
([`TierLadder.History`][ladder]). A "Skill balance" radar shows each
category's position with a grey shape for 30 days earlier. Lists of
playlists and scenarios filter by goal: "Rank up", "PB streak" (a PB in the
last four weeks), "Played lately" (14 days), "Not played lately" (30 days),
and "Never played". (From the UI inventory; the goal rules were checked in
source.)

**Our baseline:** No chart of a benchmark's standing over time. The
roadmap's score-trend verdict is per scenario. The playlist overview shows
last played but has no goal filters.

**Recommendation:** Inputs for the score-trend and planning work. A
standing built from bests can only rise, so the useful version here is the
typical one, which can show a benchmark slipping. The goal filters are a
cheap way to answer *what should I work on next?* without advice.

### 9. Smaller observations

- **Rank-up celebrations.** After each run the app compares every
  playlist's and scenario's rank with a snapshot taken before it. A rise,
  or a playlist whose every scenario reaches its rank, puts up to five
  cards with confetti on Home for ten minutes. Server syncs never
  celebrate. This app celebrates personal bests only
  ([notifications spec](../specs/notifications.md)).
- **Each run labelled with its rank.** A scenario's run list names and
  colours the rank each run's score reached. This app's run list marks a
  passed threshold and a new PB instead.
- **DPI correction.** The stats file records the DPI the player typed into
  KovaaK's, and cm/360 is wrong when that is wrong. The app lets the player
  correct the DPI of every run recorded at a given DPI and cm/360. This app
  computes cm/360 from the file's DPI as written.
- **One request queue.** Every KovaaK's request waits its turn, at least
  150 ms apart, and a 429 pauses all of them, for `Retry-After` capped at
  20 s or else 2, 4, and 8 s with jitter, with three retries. This app
  retries a request once on 429.
- **Reset files.** Its stats parser has no reset or abort detection, like
  this app's ([Aimcurve survey, finding 4](aimcurve_learnings_opus.md#4-a-reset-can-write-a-stats-file-that-looks-like-a-run)).

## What the author removed

Three weeks of history include several reversals, read from commit
messages and the files they touched. Most commits give no reason.

- **Outbound reporting.** An automatic error-report webhook, a feedback
  webhook, and Discord invite buttons, each one to two weeks old, were
  removed together on 2026-10-27. Errors are now only logged, feedback opens
  a GitHub issue, and the README and agent rules promise no telemetry.
- **An account-wide rating.** A card rating the whole account from
  Voltaic-style energy lasted eight days.
- **Charts of scenarios by rank.** A donut of how many scenarios sit at
  each rank went on 2026-10-08, and the bar chart that replaced it went on
  2026-10-28.
- **Tamper protection.** Local data was first stored signed with a key
  shipped in the app, and runs whose stats file disagreed with the signed
  record were dropped. Within a week the app wrote plain JSON and the check
  was gone.

## What not to take

- **Recording.** Video and the mouse path are the headline, and most of
  the code. They need a native Windows process, an embedded OBS, a
  hardware video encoder (there is no software fallback), a Raw Input
  hook, and an anti-cheat answer in the FAQ. The per-run mouse figures need
  the path, and nothing in KovaaK's files replaces it.
- **Editing Steam's settings.** The opt-in "Start with KovaaK's" rewrites
  the game's launch options in Steam's `localconfig.vdf`, which needs Steam
  closed, and the app offers to shut Steam down to do it.
- **The browser userscript.** It puts a video icon beside scenarios on
  Evxl and Voltaic's site. It needs Tampermonkey with file access and a
  folder grant per site, and its wiki records three earlier transports that
  were dropped.
- **An archive as the record of truth.** The competitor needs a database
  because server scores can't be fetched again. This app's record is the
  stats folder, which it re-reads at startup.

## Suggested order

1. Correct the API note and the identity docstring (finding 1), and
   document the last-scores endpoint (finding 4). Docs only.
2. Try both Steam links by hand (finding 6).
3. A proposal for an overall rank from the `basic` and `complete` rules,
   with a typical-rank version (finding 2).
4. Carry aim kinds (finding 7) and standing over time with goal filters
   (finding 8) into the score-trend and planning work.
5. Keep finding 3 as evidence for the verdicts principle, finding 5 for
   session design, and the server-scores question (finding 4) open.

## Compared with earlier surveys

[RefleK's](refleks_learnings.md) also reads `loginusers.vdf`, groups
sessions by a 20-minute gap, calls the last-scores endpoint, and computes
per-benchmark rank methods such as `vt-energy` and `ra-s5`, so rank rules
as data are now seen in two apps. Its "what to train" picks were heuristic
scores. This app's advice is the first in these surveys with significance
testing, and the only one whose author published why the first version
failed. Like [Aimcurve](aimcurve_learnings_opus.md), it reads `.perf` files,
for per-second figures in the replay, but it does not use them to classify
time-scored scenarios.

[repo]: https://github.com/dededed1024/kovaakscompanion
[head]: https://github.com/dededed1024/kovaakscompanion/tree/9c634585a325aab3c1a22fb4c453d87208bb90b7
[api]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Benchmarks/BenchmarkProgress.cs
[steam]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Benchmarks/SteamAccount.cs
[tiercalc]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Benchmarks/TierCalculation.cs
[advice-wiki]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/docs/wiki/advice-redesign.md
[advice]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Library/Advice.cs
[scenario-advice]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Library/ScenarioAdvice.cs
[session-advice]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Library/SessionAdvice.cs
[topbottom]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.App/ReplayView.xaml.cs#L910-L921
[history]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Library/ScenarioHistory.cs
[session]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Library/PlaySession.cs
[live-session]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Library/LiveSession.cs
[launch]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/KovaaksLaunch.cs
[kinds]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Benchmarks/ScenarioKinds.cs
[ladder]: https://github.com/dededed1024/kovaakscompanion/blob/9c634585a325aab3c1a22fb4c453d87208bb90b7/src/KovaaksCompanion.Core/Benchmarks/TierLadder.cs
