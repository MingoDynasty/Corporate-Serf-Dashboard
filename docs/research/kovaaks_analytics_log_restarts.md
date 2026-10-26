# KovaaK's analytics log as a source for restarts

Date: 2026-10-25
Author: claude-opus-5-5 · effort: xhigh

Research note; nothing here is ratified, and the recommendations are inputs to
a design that does not exist yet.

## Takeaway

A restarted attempt writes no stats file, so this app can't see restarts
today. KovaaK's analytics library writes a local log that records every
restart, every finished run and every scenario start, with timestamps. On the
maintainer's machine it matched every finished run it could name, to the
second and to the score. It is enough to count restarts per scenario and per
session and to estimate the time spent in them. Two things limit it: it is
debug output that a KovaaK's update could switch off, and the game empties
it at every launch, so the app would have to read it before the next launch.

## Evidence and scope

- **Game:** KovaaK's 3.9.10 (every event carries `"build":"3.9.10"`), whose
  analytics SDK reports `"sdk_version":"unreal 5.5.0"`.
- **Logs:** 35 copies of `%LOCALAPPDATA%\GameAnalytics\ga_log.txt`, one per
  launch from 2026-10-03 to 2026-10-25, kept by the maintainer's own archive
  outside the app. 2,012 events: 577 `challenge:restart`, 535
  `challenge:replay`, 326 `challenge:complete`, 125 `challenge:start`, 26
  `freeplay:start`, and session, playlist and settings events.
- **Older logs:** the game's own Unreal log, written until 3.9.10, logged the
  same events among the game's other lines. Its copies from 2026-09-23 to
  2026-09-28 hold 844 restart and replay events.
- **Stats folder:** 9,229 stats files, 349 of them since the archive began
  (2026-10-03 04:54).
- **SDK source:** `GALogger.cpp` in
  [GameAnalytics/GA-SDK-CPP](https://github.com/GameAnalytics/GA-SDK-CPP),
  read at the head of `master` on 2026-10-25. That KovaaK's Unreal plugin
  runs this logger on Windows is inferred from the file's name, path and line
  format, not confirmed.
- **Earlier work:** the 2026-10-10 Statistics Export test (five resets with
  shots fired, written up in `ignore/design-notes/stats-export-always.md` in
  the main checkout) and the
  [Aimcurve survey](aimcurve_learnings_opus.md#4-a-reset-can-write-a-stats-file-that-looks-like-a-run).
- **Two controlled tests** of restart actions, run by the maintainer on
  2026-10-25 (see [The controlled test](#the-controlled-test-2026-10-25) and
  [The second test](#the-second-test-2026-10-25)).
- **Another player's log:** one launch of about 16 minutes on game 3.9.10,
  shared with the maintainer on 2026-10-26. It holds the player's Windows
  user name and device identifiers, so it is not quoted here.
- The analysis scripts are in this checkout's gitignored
  `ignore/scripts/restart-tracking/`. They only read.

## The file

- One line per event, `Add DESIGN event: {eventId:<group>:<kind>:<scenario>,
  value:<number>, fields:null}`, followed by a JSON line whose `client_ts` is
  the event time in whole Unix seconds and whose `event_uuid` identifies it.
- `challenge:complete`'s value is the score. `challenge:restart`'s value is
  the seconds left on the run's timer, or 0. `challenge:replay` and
  `challenge:start` always carry 0.
- **The game empties it at each launch.** It is readable while the game runs.
  The game writes it in 4 KB blocks, so the last part of a launch reaches
  disk only when a block fills or the game exits.
- **The SDK rotates it after 5,000 messages** to `ga_log-prev.txt` in the
  same folder, overwriting any earlier one. The longest launch here reached
  2,394 lines in 115 minutes, so a launch at that pace would rotate after
  about four hours. Even an idle game logs a queue line about every 8
  seconds. No archived launch has rotated yet.
- **It holds more than events.** The init lines carry the game's key, a
  device identifier and the hardware name. An app should keep the challenge
  events and nothing else.
- **The folder is the SDK's default, not KovaaK's own.** Another game built on
  the same SDK would write the same path. The build number, the engine
  version and the game key in the file tell KovaaK's apart.

## Verified

1. **Every finished run with an accepted name has a `complete` event.** Of
   the 349 runs since 2026-10-03, 318 have one for the same scenario within
   3 seconds, and all 318 scores agree. 298 share the stats file's second
   and 20 are one second later. The other 31 are the three scenarios in
   point 2.
2. **The SDK drops every event of a scenario whose name has a character
   outside `A-z 0-9 -_., ()!?`.** It logs one warning per dropped event, with
   the event name and no time or value. 94 of the 866 scenarios in the stats
   folder have such a name (`%`, `+`, `'`, `#` and `&`), 716 of 9,229 runs
   (7.8%), and 31 of the 349 recent ones. It also drops an event when any
   part of its name is over 64 characters, with a different warning:
   another player's log shows it for a long playlist name. None of the
   maintainer's 866 scenario names is that long, but other players' may be.
3. **The SDK writes the event lines only because KovaaK's switches its info
   logging on.** In `GALogger.cpp`, info lines return early unless info
   logging is enabled. Warnings and errors are written either way. A KovaaK's
   build that turned info logging off would leave a file with no events.
4. **KovaaK's has no analytics setting.** The only related key in
   `PrimaryUserSettings.json` is `StatsExportLevel`.
5. **Every attempt that ends in a finished run begins with a `start`,
   `restart` or `replay` event.** `start` to `complete` is 60 seconds in all
   33 cases. `restart` to `complete` is 61 seconds in all 131 cases, and
   `replay` to `complete` is 60 or 61 in 162. The extra second after a
   restart or replay is the countdown (point 13).
6. **A replay can end a run in progress.** In the Statistics Export test,
   all four resets with kill rows were logged as `replay` with value 0. Each
   replay came within two seconds of the run's last kill, and each run's
   first kill came one to three seconds after the attempt's first event. So
   the clock time between the two events is a fair stand-in for the run's
   length, give or take the countdown and the whole-second timestamps.
7. **A restart that follows a finished run carries 0.** All 136 restarts
   that follow a `complete` on the same scenario have value 0. It is Done on
   the results screen, then Restart Challenge (the second test, step 5).
8. **`restart` is the menu's Restart Challenge button and `replay` is the
   restart key** (the tests below). Esc opens the game's main menu over the
   run, and Restart Challenge sits beside Play. The restart key pressed
   while that menu is open logs a `restart`, as the button does. It fits the
   old Unreal log: all 496 restarts there are followed within 50 ms by the
   mouse cursor hiding, a menu closing, and 389 of them (78%) are preceded
   within 3 seconds by it showing. After a replay the cursor hides 41% of
   the time.
9. **The timer stops while the menu is open,** so a menu restart's value
   leaves the menu time out. A key restart's clock time keeps it in. Opening
   and closing the menu logs no event.
10. **The results screen's Replay button logs two replays a second apart,**
    and so does the restart key there. The timer starts at the second. Esc
    does nothing on the results screen. A double press of the key mid-run
    also logs two replays a second apart.
11. **Leaving a run logs nothing for the run left,** whether by switching
    scenario or by closing the game. Only the next event bounds it. 35
    attempts in the archive ended that way, and whether they were played at
    all isn't known.
12. **A finished run with no shots logs `complete` with value 0 and writes no
    stats file** on Challenge Completion. It still writes a performance file,
    with a header and no samples.
13. **A run begins one countdown after a restart or replay.** The countdown
    is the game's `CountDownBeforeChallengeStart` setting in
    `PrimaryUserSettings.json`, 1 second here. In the old Unreal log the run
    began 1.00 to 1.03 seconds after the press in 479 of 484 cases. Three
    ran long with a menu open (point 14), and two began within 0.01 seconds,
    which is unexplained.
14. **A menu freezes the countdown.** All 8 countdowns in the old log that
    ran past 1.5 seconds had a menu opened during them, and they lasted 4 to
    91 seconds.
15. **Some events are logged when the run begins, not at a press.** In the
    old Unreal log they carry a `(UsingScenarioManager)` tag and sit on the
    run's "Scenario start broadcast" lines: every `start` (38), every
    `complete` (190) and 31 of the 348 replays. So a scenario's first `start`
    is logged after its first countdown. The analytics log does not show the
    tag.
16. **A menu restart pressed during a countdown carries 0, or the old run's
    time.** After a key restart, the old run's timer is gone: the next press
    carries 0 (the second test, step 3). After a menu restart, the old run's
    timer runs on through the countdown until the new run starts or a menu
    freezes it, so the next press carries the old run's time, a little
    further down (step 4: 50.57, then 48.85). In the old log, 257 of 324
    such presses carry 0 and 67 carry a value counting down from the press
    before.
17. **On a time-scored scenario a restart's value is 1,000 minus the seconds
    played** (the second test, step 7: 11.6 and 20.7 seconds, each a second
    or two under the clock, the menu time).
18. **Before a scenario's first run, presses end no attempt.** During the
    first countdown, Restart Challenge is greyed out. The run then begins
    with an ordinary `start` (the second test, steps 1 and 2).
19. **Another player's install writes the same file.** It is at that
    player's own `%LOCALAPPDATA%\GameAnalytics\ga_log.txt`, from the same
    game build and game key, with info logging on, and it logged
    `challenge:start` and `challenge:replay` in the same format. Their one
    launch held no finished run and no menu restart, so scores and timer
    values from another install are still unseen.

## Inferred, not verified

- **A restart's value is read as seconds left on the run's timer** for
  60-second scenarios. Every timed check agrees, but the game's code was not
  read.
- **The second replay of a results-screen pair is the run beginning.** It
  fits a press followed one countdown later by a replay logged at the run's
  start (point 15). A single key press mid-run logged one replay in both
  tests except the first test's step 6, which was most likely a double
  press.

## Measuring a restarted attempt

- **A menu restart is exact:** the scenario's run length minus the value,
  which leaves out time in the menu. Run length is the median of the
  scenario's finished runs.
- **A key restart is measured by the clock:** the replay's time minus the
  attempt's first event, minus the countdown when that event was a press.
  The countdown comes from the game's setting, or from the attempts that
  finish: their first event to `complete`, minus the run length. Timestamps
  are whole seconds, so each one is good to about a second. A pause during
  the run counts as play: in the tests, a 10-second pause made a key restart
  read 8 to 10 seconds longer.
- **A replay no more than one countdown after the attempt's first event
  begins nothing.** It is a press during the countdown or the run's own
  start event.
- **A press whose timer shows more play than the clock allows since the
  press before is a repeat press** and ends nothing: the old run hasn't
  stopped yet (point 16). This clock rule dropped all 18 repeat presses in
  the archive that followed an abandoned run. A long stay in the menu during
  the countdown would defeat it, since the clock runs on while the timer
  stands still: the second test's step 4 cleared it by 0.65 seconds. A
  backstop is to treat a menu restart as the same attempt when its play
  exceeds the press before's by no more than one countdown.
- **Two in three abandoned runs were key restarts** (67 of the archive's
  101), so most timings rest on the clock.
- **The split between a quick restart and an abandoned run is fuzzy for key
  restarts.** 387 of 445 replays (87%) come within 5 seconds of the attempt's
  first event. A one-second change in the countdown allowance moves the
  count of abandoned runs from 95 to 115 and the time lost from 30 to 37
  minutes.

## The two proposed metrics, on the maintainer's sessions

Sessions as the app splits them, 2026-10-04 to 2026-10-25: 47
scenario-sessions with at least one restart, 317 finished runs.

| Measure | Value |
| --- | --- |
| Restarted attempts | 506: 95 abandoned (5 s or more), 411 quick (under 5 s) |
| Time in abandoned attempts | 1,242 s, a median 9 s each, never past 48 s |
| Time in quick restarts | 584 s, with the count unreliable (see above) |
| Finished-run time | 19,330 s (322 min) |
| Runs plus restarted attempts | 352.6 min, 9% more than runs alone |
| The app's time on this scenario today (visit spans) | 524.8 min for the same scenario-sessions |

- **Example of the first metric:** on 2026-10-09, 1w6ts reload v2 had 19
  finished runs, 22 abandoned runs and 55 quick restarts, for 8.6 minutes in
  restarted attempts.
- **Restarts are a small share of play time.** The gap between run time and
  the visit span is mostly results screens, loading, menus and breaks.
- **A runs-plus-restarts time reads about a third lower** than the visit span
  the latest-run card shows today.

## What a feature would need

Recommendations for a design, not decisions.

- **Capture:** read the file at startup and on every change. Handle the file
  emptying at a launch and the rotation to `ga_log-prev.txt`. Check that the
  file is KovaaK's. Keep challenge events only.
- **Storage:** this would be the first data the app keeps that the stats
  folder can't rebuild. Store raw events, append-only and de-duplicated by
  event ID, outside `data/cache/`, and derive attempts when asked, as
  sessions are, so a change to the rules needs no migration.
- **Coverage:** match each finished run to its `complete` event (scenario,
  end within 2 seconds, score). A session with an unmatched run outside the
  dropped names has an unknown restart count, never zero.
- **Dropped names:** the warning lines still count presses, with no times.
  The two drop rules write different warnings, and both need reading.
- **When capture fails:** the game is launched again before the app has read
  the last launch's file. Typical case: the app is closed first and opened
  after the game next time. While the app runs alongside the game, only the
  last unflushed block of a launch is at risk.
- **No history:** restarts from before the app first read the file can't be
  recovered.
- **The countdown:** read `CountDownBeforeChallengeStart`, or learn it from
  finished attempts, since a player can change it.
- **Statistics Export on Always:** the app already imports a reset's stats
  file as a run ([sessions spec](../specs/sessions.md#run-start-and-run-length)).
  With restarts counted from the log too, the same abandoned run would count
  twice.
- **Network:** none. The file is local.

## Questions a design must answer

- What counts as a restart on screen: every press, or only abandoned runs?
  Quick restarts outnumber abandoned runs four to one and can't be counted
  reliably.
- Whether time on a scenario becomes runs plus restarted attempts, and what
  it shows when restarts are unknown.
- Whether the dependency is acceptable: undocumented debug output that one
  KovaaK's build can switch off.
- Where the numbers show: the latest-run card, the run list, Scenario Stats.

## The controlled test, 2026-10-25

The maintainer ran eight steps on Smoothsphere Viscose (60 seconds), with
Statistics Export on Challenge Completion, from 20:36 to 20:41 local time.
The two full runs were played without firing.

| # | Step | Logged | Reading |
| --- | --- | --- | --- |
| 1 | Restart key at 50 left | `replay`, 9 s after `start` | The key logs a replay with no value |
| 2 | Menu at 40 left, about 5 s, then Restart Challenge | `restart` 40.47, 27 s after step 1 | The menu logs a restart. 19.5 s on the timer against 26 s of clock after the countdown, so about 6.5 s in the menu stayed off the timer |
| 3 | Restart key twice at 30 left | `replay` 30 s after step 2, then another 1 s later | 29 s of play, then a double press |
| 4 | Full run, then the key on the results screen | `complete` 61 s later, value 0; 6 s later two replays 1 s apart; `complete` 60 s after the second | The results-screen key logs two replays, and the timer starts at the second |
| 5 | Full run, then the results screen's Replay button | Two replays 1 s apart, 6 s after the `complete` | The button logs the same as the key |
| 6 | Menu at 45 left for about 10 s, then the key at 35 left | `replay` 34 s after the run began, then another 1 s later | 25 s of play read as 33 s: the pause counts. The second replay was not asked for |
| 7 | Switched to Whisphere mid-run, played about 10 s, quit the game | `playlist:start` and `stop`, `challenge:start` Whisphere, `SESSION END` 15 s later | Neither left run logs anything of its own |
| 8 | Close the game | `SESSION END`; the whole file was on disk | |

Neither full run wrote a stats file (point 12). Each wrote a header-only
performance file at the second of its `complete`.

## The second test, 2026-10-25

The maintainer ran it from 22:29 to 22:35 local time, with the countdown set
to 3 seconds for steps 1 to 6, on Smoothsphere Viscose and then Ground Plaza
Sparky V3. The full run was played without firing.

| # | Step | Logged | Reading |
| --- | --- | --- | --- |
| 1, 2 | Esc during the first countdown, then the restart key; Esc during the next countdown, where Restart Challenge was greyed out, so the restart key again | One `restart` 0, then `start` 15 s later | Before the first run a press ends no attempt, and the run begins with an ordinary `start`. One of the two presses logged nothing; which one isn't known |
| 3 | Restart key at 50 left; during the countdown, Esc, about 5 s, the restart key with the menu open | `replay` 9 s after `start`; `restart` 0 7 s later | The key with the menu open logs a `restart`, and after a key restart it carries 0: no play |
| 4 | Restart Challenge at 50 left; during the countdown, Esc, about 5 s, Restart Challenge again | `restart` 50.57, 15 s after step 3; `restart` 48.85 8 s later | The second press carries the old run's timer, 1.72 s further down: it ran on through the countdown until the menu froze it |
| 5 | Full run; Esc did nothing on the results screen, so Done, then Restart Challenge | `complete` 63 s after step 4's second press; `restart` 0 52 s later | 63 s is the 3-second countdown plus the 60-second run. Done then Restart Challenge is the value-0 restart after a finished run |
| 6 | Menu at 45 left for about 10 s, then the restart key once at 35 left | One `replay`, 38 s after step 5 | 3 s of countdown, 25 s of play and 10 s of menu: the pause counts as play |
| 7 | Countdown back to 1 s; Ground Plaza Sparky V3, Restart Challenge about 10 s in, then about 20 s into the next run | `restart` 988.45 14 s after `start`; `restart` 979.30 23 s later | 1,000 minus the seconds played: 11.6 and 20.7 |
| 8 | Close the game | `SESSION END` | |

The full run wrote no stats file and a header-only performance file, as in
the first test.

## Still open

- **Other installs, partly.** One other install writes the file the same
  way (point 19). Its one launch held no finished run or menu restart, so a
  score or timer value from another install hasn't been seen. They come
  from the same game build, so they are expected to match.
- **Two runs in the old log began within 0.01 seconds of a press** instead
  of one countdown later (point 13). Too rare to matter for a count.
