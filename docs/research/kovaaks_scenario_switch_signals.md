# Detecting a scenario switch from KovaaK's files

Date: 2026-10-25
Author: claude-opus-5-5 · effort: xhigh
Game version: KovaaK's 3.9.10. This app's code was not involved.

The question was whether the app can tell which scenario is loaded in
KovaaK's before its first run finishes, so that the Run History page's Follow
switch could move at once instead of waiting for a run's stats file. Not
from anything tested. With the game's usual settings, the only file found to
name a scenario as it loads is the game's analytics log, and the game writes
that log in 4 KB batches, so a switch reaches the disk anywhere from seconds
to minutes late. Two other candidates stay untested: the analytics
library's event database, checked only after play, and a stats file that a
non-default export setting writes when a run is left for another scenario.
On 2026-10-25 the maintainer chose not to build load-based Follow, and
Follow still moves only when a run lands.

**Run the check again if a KovaaK's update changes its logging**, or if the
idea of following a scenario as it loads comes back. The quick test is in
[If the idea comes back](#if-the-idea-comes-back).

**Since 3.9.12 the game no longer writes the analytics log** (checked
2026-10-29). KovaaK's removed the analytics library, so the log and its event
database are gone, and with them this check's one signal and one of its two
untested candidates. The Statistics Export candidate is the one left. The
evidence is in
[the restarts check](kovaaks_analytics_log_restarts.md#since-kovaaks-3912).

## Verified findings

Measured on the maintainer's machine: one live session on 2026-10-25, and
an archive of the analytics log from 34 game launches, 2026-10-03 to
2026-10-25, matched against the stats folder.

**The Unreal log is no longer written.** Until 3.9.10, KovaaK's wrote
`%LOCALAPPDATA%\FPSAimTrainer\Saved\Logs\FPSAimTrainer.log`. That log had a
line as each scenario started,
`LogScenarioManager: Scenario start broadcast: '<name>'`, and the
same events the analytics log now carries, under `LogAnalyticsManager`.
From 3.9.10 the game no longer writes the file, and its last line is from
2026-09-28. How quickly its lines reached the disk was never measured.

**The analytics log names each scenario as it loads.** The GameAnalytics SDK
that KovaaK's ships writes `%LOCALAPPDATA%\GameAnalytics\ga_log.txt`. Each
game event is one line, followed by a JSON line whose `client_ts` is the
event's time in whole Unix seconds:

```text
Info/GameAnalytics : Add DESIGN event: {eventId:challenge:start:Flower 50cm, value:0.000000, fields:null}
Info/GameAnalytics : {"build":"3.9.10","client_ts":1792738218,...}
```

- The event kinds seen are `challenge:start`, `challenge:restart`,
  `challenge:replay`, `challenge:complete`, `freeplay:start`,
  `playlist:start`, `playlist:stop`, `playlist:complete`, `settings:*`, and
  `stats:sandbox`.
- The `value` of `challenge:complete` is the run's score. That of
  `challenge:restart` looks like the seconds left when the run was
  restarted, such as `59.49` half a second into a 60-second scenario. That
  reading is inferred from the values, not confirmed.
- The scenario name is the stats file's name exactly. All 24 scenarios the
  log shows completed match a stats file. The 2 that match none were never
  completed.
- Every `challenge` event names its scenario. A load that logged no
  `challenge:start`, as 7 of 67 challenge loads did, is still named by its
  first restart.
- The game empties the file within seconds of each launch and keeps no
  backup of it. The file can be read while the game runs.
- The folder name is GameAnalytics', not KovaaK's. Any other game built on
  the same SDK would presumably write to the same folder. This is inferred
  from the path, not tested.

**The game writes the analytics log in 4 KB batches.** A line reaches the
disk only when the 4096-byte block holding it is full, or when the game
closes. In the live session:

| Event, local time | Byte offset | Readable at |
| --- | --- | --- |
| `playlist:start` 19:55:23 | 3,495 (block 0) | 19:55:24 |
| `challenge:start` Valorant Fireworks Flick Horizontal 19:56:10 | 4,636 (block 1) | 19:57:33 |
| `challenge:start` Smoothsphere Viscose 19:56:28 | 6,403 (block 1) | 19:57:33 |
| `challenge:complete` Smoothsphere Viscose 19:57:28 | 7,642 (block 1) | 19:57:33 |
| `playlist:stop` 19:57:48 | 8,568 (block 2) | 19:57:54, at game exit |

Each batch split the events exactly where a 4096-byte boundary falls
between them. The probe did not record the file's size at each read, so the
block size is inferred from those splits, and from the replay in
[Measurements](#measurements) matching the live timing. The Smoothsphere
switch became readable 65 s after the load, and 5 s after that run's stats
file had already landed.

**Windows reports the change as soon as the bytes land.** A watchdog
observer on the folder heard each batch at the same instant a 50 ms poll of
the file's size did. It did so also in a dry run in which a script held the
file open and appended to it, as the game does. The delay is the game's
buffer, not file notification.

**No other file written during the live session names the loaded
scenario.** These were written, and none of them helps:

- `Saved\SaveGames\PlaylistInProgress.json` is the running playlist's
  definition: its scenarios in order, with play counts.
- `Saved\SaveGames\PlaylistOrder.json` has a `currentScenarioIndex`, but
  the file was written only when the playlist started. It pointed at the
  third scenario while the first was played.
- A map file and the Steam scenario cache files were written as one
  scenario loaded, and not when the next one did. A map file names a map,
  not a scenario.

**Two candidates are untested as live signals.**

- `GameAnalytics\ga.sqlite3` queues each event until it is uploaded. A copy
  taken after the live session had an empty `ga_events` table, and the
  analytics log shows each event uploaded within seconds of being added.
  Whether a queued row can be read while the game runs, and for how long,
  was not measured: the live probe watched only `ga_log.txt`. The empty
  table explains why the rows were gone afterwards. It does not rule the
  database out.
- With KovaaK's **Statistics Export** setting on **Always** instead of
  **Challenge Completion**, leaving a run for another scenario writes a
  stats file named after the incoming scenario, with an empty `Scenario:`
  line. In a 2026-10-10 experiment on 3.9.10 this happened twice, written
  3 s and 22 s before the incoming scenario's `challenge:start`. It needs a
  run left unfinished, and the setting also exports resets and freeplay,
  so the stats folder gains files that are not completed runs. It was not
  studied further here.

## Measurements

From the 34 archived launches. A switch is the first event that names a
scenario other than the one before it.

| Measure | Result |
| --- | --- |
| Challenge loads | 67, plus 10 freeplay loads, left out because the comparison uses completed Challenge stats files. Freeplay wrote stats files with Statistics Export on Always, and none under Challenge Completion |
| Loads with no completed run before the next switch | 20 of 67 |
| Loads followed by a completed run | 47 |
| How much earlier the load is logged than that run's stats file | median 74 s, minimum 60 s, 75th percentile 94 s, maximum 496 s |
| When a load becomes readable, after the 4 KB batching | median 17 s after the load, 25th percentile 6 s, 75th percentile 66 s, maximum 149 s |
| Loads readable within 5 s, 10 s, 30 s, 60 s | 15, 26, 42, 48 of 67 |
| Loads readable before that run's stats file | 34 of 47, a median 65 s sooner when they were |

The stats folder no longer holds the files of the 2026-10-10 Statistics
Export experiment, which were moved out of it. So one load from those
launches counts as having no completed run, though it had one: a full run
that scored 0.

The batched figures come from replaying the 4 KB rule over the archived
files: each line becomes readable when the block holding it fills, and a
line with no timestamp gets one interpolated between its neighbors. Run on
the live session's own log, the replay put the Smoothsphere batch at
19:57:28 against the observed 19:57:33.

Restarts fill blocks fast, at about 1 KB of log per event. So a load
followed by a few restarts becomes readable quickly, and a load played
straight through, as in the live session, often stays unread until after
its first run.

## How it was measured

- **The live probe** polled the size of `ga_log.txt` every 50 ms and read
  any new bytes. It paired each `Add DESIGN event` line with the `client_ts`
  on the next line, and printed the read time minus `client_ts`. Beside
  that, a watchdog observer on the folder recorded each change
  notification. Because `client_ts` is whole seconds, each delay it printed
  is up to 1 s too long. The probe noted the game's launch, when the file is
  emptied, and stopped when the game closed.
- **The archive** is a scheduled task on the maintainer's machine that
  copies `ga_log.txt` hourly and around each launch, because the game
  empties it at the next launch.
- **The byte offsets** in the live table come from the file after the
  session. They are checked against when each event was first read.

## What this means for a design

These are recommendations, not decisions.

- No file tested gives the loaded scenario at once. A Follow that moves on
  load from the analytics log could only be best-effort: often a minute
  sooner than a run's stats file, sometimes later than it.
- A best-effort version would act only when the log names a new game
  scenario, never on a repeated one. Otherwise a batch that lands while the
  user browses another scenario would move the page back. It would take
  the last scenario a batch names. It would skip a scenario with no runs,
  which the page has nothing to show for, and fall back to following runs
  whenever the file is missing. Its tailer would have to notice the file
  being emptied at launch, even when the new launch has already written
  past the old end.
- Uses that read the log after the fact are not affected by the batching,
  because a closed launch's log is complete. Two examples are counting
  restarts and taking a session's launch and exit times. The other limits
  still apply: the game empties the file at each launch, and an update can
  stop writing it, as 3.9.10 did with the Unreal log.

## If the idea comes back

Check first whether the batching is still there. While switching scenarios
in the game, watch the file's size in PowerShell:

```powershell
$f = "$env:LOCALAPPDATA\GameAnalytics\ga_log.txt"
while ($true) { "{0:HH:mm:ss} {1}" -f (Get-Date), (Get-Item $f).Length; Start-Sleep 1 }
```

If the size moves only in steps of 4096 bytes, the log is still batched and
these findings stand. If it grows a line at a time, measure again: load-based
Follow would then be close to instant.

Then test the two open candidates before settling on the log: whether a
queued row in `ga.sqlite3` can be read during play, and for how long, and
whether a load-time file that appears only when a run is left unfinished,
under a non-default export setting, is worth what that setting adds to the
stats folder.
