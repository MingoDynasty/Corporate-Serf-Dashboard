# Every Total Of Play Is Time In Runs, And A Session Keeps Its Clock

Status: Proposed
Date: 2026-11-05

## TL;DR

The app shows two lengths of play today, and they use two definitions: a
session's runs from start to end, and a scenario's visits from first run to
last. Every page planned next needs a third, a total for a scenario, a day or
all play, and nothing says how to count it. This proposal makes every total of
play the sum of run lengths, called time in runs, and keeps a session's length
as its clock, breaks included. Scenario Stats' run count becomes a time in
runs, and the latest-run card drops a time that would only repeat its run
number.

## Decisions needed

Six rows, DT1 to DT6. **Nothing is ratified.** The maintainer leaned on
2026-10-14 toward counting only the runs for a scenario's total, toward
keeping downtime with the session, and toward folding the run count into a
time figure. Then they deferred the question so that "the concept of time
stays consistent throughout the app". A lean is not a ruling. Reviewers may
challenge any row, and anything in [Design](#design), which is author-owned.

### DT1. Every total of play is time in runs

Status: open. The maintainer's lean, transcribed in their notes on 2026-10-14:
count only the runs, "since a scenario's total is about that scenario, not
downtime". And of Home: "'By time in runs' makes more sense than 'By runs',
since some scenarios have longer durations."

The material consequence: every total leaves out restarts, results screens,
menus, freeplay and breaks, so it reads about half of a session's clock (49%
on 2026 sessions of 5 or more runs) and about a third of the time the game was
open.

**Recommendation: a total of play over any set of runs (a scenario's, a
session's, a day's, a week's, all of them) is the sum of their run lengths,
called time in runs. One function adds it up and one formatter rounds it, to
the nearest minute. Every page that shows a total uses it.**

- **A, time in runs (recommended).** The sum of each run's end minus its start
  minus its paused time.
- **B, runs plus gaps up to 2 minutes.** A, plus each break between two runs
  of one visit, capped at 2 minutes. It counts the results screen and a quick
  restart: 1.46 times A in 2026. It needs a second constant beside the 30
  minutes, and a hover to explain it.
- **C, visit spans.** Each visit from its first run's start to its last run's
  end, as the latest-run card counts today: 1.61 times A in 2026. It counts
  every break under 30 minutes inside a visit: the card would have read 36 min
  for 5 runs on 2026-09-30.
- **It splits cleanly.** Each run's time belongs to one scenario, one day and
  one hour, so the parts always add up to the whole. A visit's or a session's
  clock can't be split by hour or by scenario without a rule for its breaks.
- **It comes from the stats files alone,** on every game version the app reads
  (DT6).
- **On most scenarios it reads close to the run count in minutes.** 85% of
  scenarios have a median run of 50 to 62 seconds, so VT Controlsphere
  Viscose's 147 runs are 2 hr 26 min in runs. On the rest it says what a count
  can't: Air CELESTIAL No UFO Medium's 37 runs are 1 hr 13 min.
- **What it leaves out,** measured: 9% more in restarted attempts on the
  sessions the 3.9.10 analytics log covered; half the session clock in 2026;
  and the game was open 2.91 times as long as its runs from May to October
  (DT6).

### DT2. A session keeps its clock

Status: open. The session and its length were ruled in S1 (2026-10-11). The
maintainer floated keeping "downtime belonging to the session as a whole" on
2026-10-14 (transcribed).

The material consequence: the app shows two kinds of length side by side,
about two to one apart. The 2026-10-27 session reads
`1 hr 13 min · 33 runs · 6 scenarios` with 33 min in runs.

**Recommendation: a session's length stays its first run's start to its last
run's end, breaks between runs included, as today. It is the only length the
app shows that counts breaks, and its hover says so. No session row shows a
time in runs.**

- **A, the clock (recommended).**
- **B, time in runs on the session row too.** One measure everywhere, but "how
  long was that sitting?" would read 33 min for a sitting of 1 hr 13 min.
- **C, both on the row,**
  `1 hr 13 min · 33 min in runs · 33 runs · 6 scenarios`. A fifth part, and a
  count beside its own time on 60-second scenarios (DT3's problem).
- **The question is the sitting's length,** and a sitting holds its breaks.
  The product page and the glossary already define a session as one stretch of
  play "including the breaks between runs".
- **Runs fill about half a session.** On sessions of 5 or more runs since
  2026-09-13, the runs fill a median 50% of the clock, the middle half 37% to
  58%.
- **Unchanged:** the 30-minute split (S1), the In progress state (S3) and its
  30-second recheck, This scenario's session rows with no length (2026-10-23).

### DT3. The latest-run card's session line drops its time

Status: open. The maintainer floated runs-only "for the session line too" on
2026-10-14 (transcribed). This recommendation differs from that.

The material consequence: the card no longer says how long the player has
spent on the scenario this session.
`Run 7 this session · 9 min on this scenario` becomes `Run 7 this session`.

**Recommendation: the session line names the run's number in its session and
nothing after it. The card shows no length of play.**

- **A, drop the time (recommended).**
- **B, time in runs:** `Run 7 this session · 7 min in runs`.
- **C, the visit spans, as today:**
  `Run 7 this session · 9 min on this scenario`.
- **D, runs plus gaps up to 2 minutes:** `Run 7 this session · 12 min`.
- **B repeats the run number.** 91% of 2026 runs last 50 to 62 seconds, so a
  scenario's time in runs in a session is its run number in minutes. It would
  read `Run 7 this session · 7 min in runs` in 3,341 of the card's 3,619
  readings in 2026 (92%), and 1,153 of 1,221 since 2026-09-13 (94%).
- **C counts breaks no total keeps (DT1).** It ran 5 minutes or more over the
  runs in 16% of 2026 readings, and the same runs would read two times on two
  cards. Its worst: `36 min on this scenario` for 5 runs, 2026-09-30 (before
  the card shipped, so what it would have read).
- **D is DT1's option B on one card:** a second definition for one line.
- **The run number already paces a visit,** and the card's first line,
  `Latest run · 5 minutes ago`, already times the break since the last run.
- **The time is still there, where it adds up:** the scenario's total on
  Scenario Stats (DT4) and the session's clock in All scenarios (DT2).
- **Simpler.** The time part, its unknown form `Time on this scenario unknown`
  and the rule for a visit with no usable start all go.
- **It changes ratified design.** The card's time came with the Run History
  proposal, ratified on 2026-10-12, and was kept by 2026-10-18 and 2026-10-25.

### DT4. Scenario Stats' Total runs becomes Time in runs

Status: open. The maintainer's lean, 2026-10-14: "fold into a time-played
figure, with the run count on hover", because "the Time is the more
interesting metric". Until a time rule existed, "the Scenario stats card keeps
Number of runs".

The material consequence: the all-history run count, which TS8 (2026-10-20)
named Total runs to keep it apart from the typical score's 20 runs, moves into
a hover.

**Recommendation: `Total runs: 147` becomes `Time in runs: 2 hr 26 min`, over
every run of the scenario, as Total runs counts them. Its hover opens with the
count, `147 runs`, and says what is left out. A total that holds a run with no
length reads `at least` (DT5).**

- **A, the time in place of the count (recommended, the lean).**
- **B, both on one line,** `Total runs: 147 · 2 hr 26 min in runs`: a count
  beside its own time, which DT3 removes from the card.
- **C, the count stays,** and no time ships on Run History.
- **Lifetime, not a window.** Total runs is lifetime, and the line answers
  "how much have I put into this scenario?" A 30-day total (53 min on VT
  Controlsphere Viscose since 2026-10-01) would be a second meaning on one
  card, and the typical score's 30 days already date its runs.
- **18 scenarios played in 2026 read `at least`,** because their totals reach
  back to files from 2019 to 2021 with no length: 1w6ts reload v2,
  `at least 31 min` over 48 runs, 17 without a length.
- **One line for one line.** The card stays 270 px wide. Whether the longest
  form fits on one line is checked in the browser ([Not
  checked](#not-checked)).

### DT5. A time in runs names what it counts

Status: open. No lean. D2 (2026-10-04, ruled): "A figure that can only be a
minimum is labelled one wherever it's shown, such as time spent in runs". PR
#381's HM2 took the reviewers' counter for a visible line: "Recorded time in
runs is a minimum of time played."

The material consequence: most figures read without "at least". The minimum is
said by the name `in runs`, and in words where a surface is about time.

**Recommendation: every time in runs reads `{duration} in runs`, or
`Time in runs: {duration}` as a labelled line. `at least` goes in front only
when a counted run has no length. No number on screen is labelled time played,
time spent or play time. A surface whose subject is time, such as a later
calendar or week readout, also carries one visible sentence saying what runs
leave out, as HM2's line does. Every figure's hover says it.**

- **A, the name is the label (recommended).** `in runs` says what is counted,
  so the figure is exact for what it names; `at least` marks the one case
  where it isn't.
- **B, `at least` on every figure,** HM2's line read app-wide. The word would
  be on every number, so it would stop telling one apart from another.
- **C, "time played" with a minimum note.** It names the whole of what the app
  sees about half of.
- **Runs with no length are old.** 509 of 9,284, all from 2019 to 2021: 463
  files with no `Challenge Start:`, 46 out of range. None since 2022. So
  `at least` shows on totals that reach back that far: 85 of 866 scenarios,
  and the lifetime figure, `at least 142 hr in runs`.
- **What runs leave out** is half the session clock and about two thirds of
  the time the game was open (DT6). D2 asks for the label; this row says which
  word carries it.

### DT6. Time comes from the stats folder alone

Status: open. No lean on a source. The maintainer leans toward skipping
restart detection (2026-10-29, not ruled), and the 2026-10-11 entry rejected a
session as one game launch.

The material consequence: no figure can say how long the game was open, and
restarts, freeplay and launches with no finished run stay out of every figure.

**Recommendation: the app works out every time from the stats files. It reads
no game log, no Steam log and no watcher of the game window or input. The
roadmap's Future entry "KovaaK's own log" is corrected: KovaaK's 3.9.12 no
longer writes the analytics log, and Steam's own log is the one known record
of launches left.**

- **A, the stats folder only (recommended).**
- **B, Steam's log for game-open time,** shown beside time in runs as an upper
  bound. Steam writes every launch and exit of the game to
  `logs\content_log.txt`, six months back on the maintainer's machine. It is
  undocumented, found through a registry key, in local time, and as long as
  Steam keeps it.
- **C, a watcher** sampling the game's focus and input while the app runs. It
  would be the first data the stats folder can't rebuild, with no history
  before it starts.
- **The gap, measured.** From 2026-05-10 to 2026-10-30, 133 launches: 25.9 h
  in runs, 42.6 h of visit spans, 54.0 h of session clocks, and the game open
  75.6 h, 2.91 times the runs. 53 launches held no finished run, 10.1 h.
- **Restarts have no source on 3.9.12.** The analytics log that timed them on
  3.9.10 is gone (`docs/research/kovaaks_analytics_log_restarts.md`). With
  Statistics Export on Always a reset writes a stats file, which the app
  counts as a run with no length.
- **D2 already covers the gap** with a minimum. An upper bound would be a
  second number on every figure.

## Problem

### Where the app shows or works out time today

At `0fdde2af`. "Length of play" rows are the ones this proposal governs.

| # | Where | Reads today | Measure | Code | Docs | Here |
|---|---|---|---|---|---|---|
| 1 | Sessions, the split | none on screen | a break over 30 min ends a session | `play_sessions.py:21-26, 104-132` | `sessions.md:107-135`; S1 | unchanged |
| 2 | A run's start and length | none by itself | end − `Challenge Start:` − pause, trusted 1 s to 30 min | `data_service.py:81-91, 740-794` | `sessions.md:72-105` | the unit of every total |
| 3 | In progress | `In progress` badge, first row | newest session within 30 min of its last run | `play_sessions.py:135-156`; `run_history_list.py:476, 639, 770-777`; `run_history.py:391-417` | `sessions.md:141-166`; S3 | unchanged |
| 4 | All scenarios, session row | `1 hr 6 min · 47 runs · 7 scenarios` | session clock: length of play | `run_history_list.py:653-663`; `play_sessions.py:77-80` | `run_history.md:1057-1061`; glossary 128-132 | kept (DT2) |
| 5 | The first row's length hover | "The length runs from the first run to the last run…" | text | `run_history_list.py:114-117, 657`; `runHistoryList.js:600` | 2026-10-12 run list entry, 259-268 | reworded (DT2) |
| 6 | This scenario, session row | `7 of 47 runs` | a count, no length | `run_history_list.py:481-509` | `run_history.md:981-990`; 2026-10-23 | unchanged |
| 7 | Latest-run card, session line | `Run 7 this session · 9 min on this scenario` | visit spans summed: length of play | `latest_run_card.py:307-330, 674` | `sessions.md:48-62`; `run_history.md:440-454` | time leaves (DT3) |
| 8 | Latest-run card, first line | `Latest run · 5 minutes ago` | an age, reworded every 30 s | `latest_run_card.py:109-128` | `run_history.md:365-372` | unchanged |
| 9 | Scenario Stats | `Total runs: 147` | a count | `scenario_stats.py:214-227, 261-277` | `run_history.md:1691-1692, 1711-1714`; TS8 | Time in runs (DT4) |
| 10 | Run list heading, screen readers | `{scenario} · 147 runs` | a count | `run_history_list.py:518-528` | `run_history.md:967-971` | unchanged |
| 11 | Home's line | `Found 9,284 runs across 866 scenarios in your stats folder.` | counts | `home.py:157-179` | `home.md:45-57` | unchanged; later Home work follows DT1 |
| 12 | The formatters | `9 min`, `1 hr 6 min`; ETAs round up | nearest minute; up for estimates | `utilities.py:78-93, 182-206` | 2026-10-13 | one formatter for every time in runs |
| 13 | Playlists' percentile status | `(~5 min)` while updating | an estimate | `playlists.py:540-552`; `percentile_warmup_service.py:663-669` | | unchanged |
| 14 | Run viewer, Time tile and By Bot | `1:54.3`, a time per kill | a run's own clock | `run_viewer_panel.py:103, 324, 404-414`; `run_viewer.py:238` | `run_history.md:1306, 1546-1547` | unchanged |
| 15 | Aim Training Journey, by address only | progress at "N hours" | every 60th run: one run a minute assumed | `data_service.py:271-281`; `aim_training_journey.py:106` | `run_history.md:21-22` | adopts DT1 if revived |
| 16 | Chart tooltips, session names, PB age, Last played, typical recency | `Oct 12, 6:40 PM`, `set 5 days ago`, 30 days | timestamps, ages, calendar windows | several | 2026-10-24; TS6 | unchanged; not lengths |
| 17 | Roadmap and principles | "time spent in runs" as a labelled minimum; "KovaaK's own log" | prose | | `roadmap.md:123-128, 148-153`; D2 | DT5, DT6 |

- **Two shipped lengths of play, two definitions** (rows 4 and 7). The session
  row counts its clock; the card counts its scenario's visits. Neither is a
  total.
- **The card's time came with the Run History proposal**: author-owned design,
  ratified with it on 2026-10-12, and kept as the page grew. Its unknown form
  exists for a visit whose first run has no start, so that one long run
  doesn't read `<1 min`.
- **The glossary has Run length and Session length,** and no word for a
  scenario's, a day's or a lifetime's time. That is the gap this fills.

### Why now

- The Run History top-row work deferred a time figure for Scenario Stats on
  2026-10-14 "so the concept of time stays consistent throughout the app".
  Until a rule exists, the card keeps its run count.
- Home's next design wants time figures: a week's play, a lifetime figure, a
  calendar shaded by time in runs (PR #381, closed unmerged 2026-10-23; its
  unruled HM2 would have authorized time in runs "for the card" only).
- A break divider for the run list is planned after this, and needs the
  session row's hover and the word for a break settled.

### Verified facts

- `PlaySession.length` is the end minus the start (`play_sessions.py:77-80`);
  a visit has no length property, and the card sums `visit.end - visit.start`
  itself (`latest_run_card.py:329`).
- A run has a start and a length, or neither (`data_service.py:761-794`).
  Paused time is in a session's clock and a visit's span, and out of a run's
  length.
- `format_elapsed_duration` rounds a measured time to the nearest minute, a
  half up, `<1 min` under 30 seconds (`utilities.py:182-206`), for both
  shipped lengths (2026-10-13).
- The first row's length is the only one with a hover
  (`run_history_list.py:657`, `runHistoryList.js:600`).
- Scenario Stats' count is `get_scenario_stats(...).number_of_runs`
  (`scenario_stats.py:214-227`), the run store's count for the scenario.
- The session line is drawn as plain text with no hover
  (`latest_run_card.py:674`).
- No other page shows a length of play, and no toast or log line shows one
  (`sessions.md:65-66`).

### What the maintainer's runs say

9,284 runs through 2026-10-29 23:57, 866 scenarios, 332 sessions, read with
the app's own rules.

| # | Measure | Lifetime | 2026 | Since 2026-09-13 |
|---|---|---|---|---|
| 1 | Runs; runs with no length | 9,284; 509 | 3,619; 0 | 1,221; 0 |
| 2 | Time in runs (A) | 142.4 h | 59.6 h | 21.1 h |
| 3 | Runs plus gaps up to 2 min (B), as a multiple of A | 1.42 | 1.46 | 1.45 |
| 4 | Visit spans (C), as a multiple of A | 1.61 | 1.61 | 1.63 |
| 5 | Session clocks (E), as a multiple of A | 2.03 | 2.08 | 2.04 |
| 6 | Runs as a share of a session's clock, sessions of 5+ runs: median (middle half) | 55% (45 to 66) | 49% (41 to 57) | 50% (37 to 58) |
| 7 | Runs of 50 to 62 s | | 91% | 94% |
| 8 | Card readings where time in runs equals the run number | 92% | 92% | 94% |
| 9 | Card readings where visit spans run 5+ min over the runs | 20% | 16% | 13% |

Scenarios played most since 2026-09-13:

| # | Scenario | Runs | Time in runs | Runs plus gaps ≤ 2 min | Visit spans | Visits |
|---|---|---|---|---|---|---|
| 1 | VT Controlsphere Viscose | 145 | 2 hr 24 min | 3 hr 20 min | 3 hr 40 min | 24 |
| 2 | Whisphere Viscose | 134 | 2 hr 13 min | 3 hr 8 min | 4 hr 5 min | 26 |
| 3 | RawControlSphere | 95 | 1 hr 34 min | 2 hr 22 min | 2 hr 42 min | 13 |
| 4 | Smoothsphere Viscose | 74 | 1 hr 13 min | 1 hr 40 min | 1 hr 40 min | 13 |
| 5 | Air Voltaic Invincible 4 Medium | 62 | 1 hr 1 min | 1 hr 28 min | 1 hr 36 min | 18 |
| 6 | Air CELESTIAL No UFO Medium | 36 | 1 hr 11 min | 1 hr 34 min | 1 hr 39 min | 12 |

The ten newest sessions, as the All scenarios row reads them and as time in
runs would:

| # | Session | Runs · scenarios | Session clock (the row) | Time in runs | Runs' share |
|---|---|---|---|---|---|
| 1 | Oct 29, 11:51 PM | 4 · 1 | 6 min | 4 min | 62% |
| 2 | Oct 29, 6:09 PM | 19 · 4 | 41 min | 19 min | 46% |
| 3 | Oct 27, 5:09 PM | 33 · 6 | 1 hr 13 min | 33 min | 45% |
| 4 | Oct 22, 11:40 PM | 16 · 2 | 19 min | 16 min | 83% |
| 5 | Oct 16, 8:06 PM | 4 · 1 | 6 min | 4 min | 70% |
| 6 | Oct 16, 5:48 PM | 35 · 5 | 1 hr 42 min | 38 min | 38% |
| 7 | Oct 16, 2:00 PM | 38 · 6 | 1 hr 11 min | 38 min | 53% |
| 8 | Oct 9, 8:08 PM | 43 · 7 | 1 hr 55 min | 43 min | 37% |
| 9 | Oct 9, 4:49 PM | 48 · 5 | 1 hr 32 min | 48 min | 52% |
| 10 | Oct 8, 5:00 PM | 56 · 8 | 1 hr 29 min | 57 min | 64% |

Game open against the stats files, 2026-05-10 to 2026-10-30, from Steam's log
(133 launches, every one of the 1,520 runs inside one): time in runs 25.9 h,
visit spans 42.6 h, session clocks 54.0 h, game open 75.6 h.

### Not checked

- **The app's functions were not run.** Every figure is a re-implementation of
  the app's rules over the stats folder; it reproduces the counts of two
  earlier reads.
- **Scenario Stats' longest line in pixels.**
  `Time in runs: at least 12 hr 34 min` is 35 characters in a 270 px card;
  `Total runs: 463` is 15.
- **The restart share on 3.9.12.** The 9% is from 9 sessions on 3.9.10;
  nothing records restarts now.
- **Another player's run lengths.** A player on longer scenarios would see
  time in runs move further from the run count, and the card's lost time cost
  more (DT3).
- **One player's folder** throughout.

## Design

### The rule

1. **A total of play is time in runs** (DT1): the sum of the run lengths of
   whichever runs the figure covers.
2. **A session's length is its clock** (DT2), the only length that counts
   breaks.
3. **A run count and its time in runs never sit side by side** (DT3, DT4): a
   figure shows one, and the other goes in its hover or not at all.
4. **A time in runs is named** `in runs` (DT5), with `at least` only where a
   counted run has no length.
5. **Ages, a run's own clock, estimates and calendar windows** keep their
   forms: `5 minutes ago`, `1:54.3`, `~5 min`, "the last 30 days". None is a
   length of play, and none shares a label with one.
6. **Every time comes from the stats files** (DT6).

### Per surface

| # | Surface | Measure | Reads | Change |
|---|---|---|---|---|
| 1 | Scenario Stats | time in runs, lifetime | `Time in runs: 2 hr 26 min`, the count in the hover | replaces Total runs (DT4) |
| 2 | Latest-run card, session line | none | `Run 7 this session` | the time goes (DT3) |
| 3 | All scenarios, session row | session clock | `1 hr 6 min · 47 runs · 7 scenarios` | the first row's hover is reworded (DT2) |
| 4 | This scenario, session row | none | `7 of 47 runs` | none |
| 5 | Later pages: Home's figures, a calendar, a week, a lifetime line, a recently played list | time in runs | their own proposals | bound by rules 1, 3 and 4 |
| 6 | A later break divider | one break's length | `23 min break` | its own proposal; the word is break |
| 7 | Run viewer times, ages, estimates, timestamps | not lengths of play | as today | none |
| 8 | Aim Training Journey, by address only | runs ÷ 60 | as today | adopts rule 1 if revived |

### In code

- **`time_in_runs(runs)`** in `source/kovaaks/play_sessions.py`, beside
  `PlaySession.length`: a pure function returning a frozen
  `TimeInRuns(seconds, unknown)`, the sum of `run_length` over the runs that
  have one and the count of those that don't. It reads no store and no clock.
- **Formatting** is `format_elapsed_duration`, unchanged. A caller puts
  `at least ` in front when `unknown` is above zero.
- **Scenario Stats.** `get_scenario_num_runs` becomes the line's callback:
  from one snapshot of the run store, the scenario's runs, their time in runs
  and their count. With no scenario selected the card reads as today. With no
  local runs the line is absent and `No runs yet` stands alone.
- **The card.** `_session_line` keeps the run's words and drops the time, with
  its visit sum and its unknown branch.
- **The session row.** `SESSION_LENGTH_HELP` gets the new text; still on the
  first row only.
- **Nothing is stored,** so nothing migrates, as with sessions.

### Copy

Every string this proposal adds or edits. Rules 1 to 9 apply.

| Where | String |
|---|---|
| Scenario Stats, line | `Time in runs: ` (the label bold, as `Category:` is), then `{duration}` or `at least {duration}` |
| Scenario Stats, hover, first line | `{n} runs`, or `{n} runs · {k} with no recorded length` |
| Scenario Stats, hover, second line | `Only the runs themselves count. Restarts, results screens and breaks between runs don't.` |
| Scenario Stats, hover, with `at least` | adds `A run with no recorded length isn't counted.` |
| Latest-run card, session line | `Run {n} this session`, `Run {n} last session`, `Run {n} ({session} session)`, unchanged and alone |
| Session row, first row's length hover | `The length runs from the first run's start to the last run's end, breaks between runs included. It doesn't count the time since your last run.` |

Retired: ` · {duration} on this scenario`, `Time on this scenario unknown`,
`Total runs: `, and the old length hover,
`The length runs from the first run to the last run. It doesn't count the time since your last run.`

- **`breaks between runs included`** rewords the glossary's own phrase for a
  session, "including the breaks between runs", and puts the word break on
  screen for the first time, as the specs use it.
- **`in runs` is a tail, `Time in runs:` a label.** Where a figure stands in a
  sentence or a readout, the tail; where it has a line of its own beside
  `Category:`, the label.

### Terms

For the glossary, under Play, after Session length.

**Time in runs.** The sum of the run lengths of some runs: a scenario's, a
session's, a day's, or all of them. It leaves out restarts, results screens,
menus, freeplay and the breaks between runs, because none of them writes a
run. A total that holds a run with no length is a minimum, and reads
`at least`.
- On screen: `Time in runs: 2 hr 26 min` in Scenario Stats;
  `{duration} in runs` where a figure reads in a line.
- In code: `time_in_runs`, `TimeInRuns`.
- Not a session length, which counts the breaks. Not time played, which the
  app can't see. Not a calendar window such as the typical score's 30 days.

**Session length** gains: "It is the only length the app shows that counts the
breaks. On screen: the All scenarios session row."

**Break.** The time between two runs, from one run's end to the next one's
start. A break of more than 30 minutes ends a session.
- On screen: the session row's hover, `breaks between runs included`.
- Not a pause, the game's own pause inside a run, which a stats file records
  as `Pause Duration:` and which a run's length leaves out.

### Decisions this changes

- **2026-10-12, a past run's check** (the card's third line, "the clock time
  spent on the scenario in that session"): superseded in part. The run's
  number in its session stands.
- **2026-10-18, the card reports the selected scenario's latest run** ("the
  time still the sum of the scenario's visits"), and **2026-10-25 (SC3)**
  ("the time on the scenario shares the session line"): superseded in part.
  The session's words stand.
- **2026-10-20 (TS8):** `Total runs: {n}` becomes `Time in runs: {duration}`,
  and the count moves to its hover. The lead, its order and Category stand.
  Superseded in part.
- **2026-10-12, the run list column:** the first row's length hover is
  reworded. Superseded in part.
- **2026-10-13, nearest minute:** gains a note. The rule covers a session's
  length and every time in runs; the card's time on a scenario is gone.
- **The roadmap.** "KovaaK's own log" is corrected for 3.9.12 (DT6). "An
  overview" reads "time in runs and activity". The uncertainty principle's
  example reads "time in runs". The Future list's membership, D5 of
  2026-10-04, stands.
- Applied, not changed: **2026-10-04 D2**, whose label DT5 says how to read
  for time; **2026-10-11 S1 and S3**; **2026-10-23**, This scenario's rows
  with no length.

### Alternatives rejected

- **A scenario's first to last run in a session,** other scenarios between
  included. It counts other scenarios' runs: on VT Controlsphere Viscose,
  lifetime, 4 hr 57 min against 3 hr 42 min of visit spans.
- **Runs plus restarts.** Restarts were timed only by the 3.9.10 analytics
  log, which 3.9.12 no longer writes.
- **A minimum and a maximum on every figure.** The maximum needs a launch
  source (DT6).
- **A run count everywhere, no time.** Scenario durations differ, and the
  maintainer's reason for time was that "some scenarios have longer
  durations".
- **The card's time under a new name,** such as
  `15 min since your first run here`. It keeps the break counting DT1 rejects
  for totals, and still disagrees with Scenario Stats.
- **Every session row's length with a hover.** The first row's hover exists
  for the length that stands still in session; the new text adds the breaks
  and needs no wider reach.

## Out of scope

- **The break divider** in the run list: its own small proposal, after this
  one.
- **Home's figures,** a calendar, a week readout, a lifetime line, a recently
  played list: their own proposals, under rules 1, 3 and 4.
- **A session card** with its time in runs: the session row keeps its clock
  (DT2).
- **Restart detection,** and skipping the reset files Statistics Export on
  Always writes. Revisit both if a source appears; until then a reset file is
  a run with no length, and a total holding one reads `at least`.
- **The Aim Training Journey's hours,** until the page is revived.
- **Ages, the run viewer's times, estimates:** unchanged.

## Delivery plan

Stated intent, not a contract; a PR that moves a boundary says so in its
description.

1. **One PR.** `time_in_runs` and its tests; Scenario Stats' line and hover;
   the card's session line; the session row's hover. `sessions.md`,
   `run_history.md`, the glossary, a decision-log entry, the roadmap's three
   wordings, `architecture.md`'s card line, and a check of the user guide and
   README; this proposal is deleted.

## Testing

- **Unit, `time_in_runs`:** no runs; all with a length; some without; a paused
  run counts its length only; a run at 1 s and at 30 min; the sum over two
  sessions equals the sum of each.
- **Unit, Scenario Stats:** no scenario; no runs; a known total; an `at least`
  total; the hover's two forms; a run landing changes the line.
- **Unit, the card:** the session line's three forms with no time; a session
  whose first run has no start reads as any other.
- **Unit, the session row:** the first row's hover text; the other rows have
  none.
- **Browser** (headless Edge, then the maintainer's Firefox), both themes, at
  3840, 2560, 1920 and 1536 px: Scenario Stats' longest line on one line in
  270 px; the top row's height unchanged; the card's session line.
- **Screen reader** (NVDA): Scenario Stats' line and hover; the session row's
  length and hover.
- **Gates:** pytest, ruff format and lint, mypy, compileall, as AGENTS.md
  lists.
