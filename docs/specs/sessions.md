# Sessions

The app groups a player's runs into sessions: the runs separated by breaks of
no more than 30 minutes. To measure a break it works out when each run began
and how long it took, from two lines of the run's stats file. Inside a
session it also finds each visit, the consecutive runs on one scenario. Run
History shows each run in its practice context and session lengths in All
scenarios.

Statements below describe what the app does today and link the
[decision log](../decision_log/README.md) entry that set them. Rationale lives in
that entry, not here. A statement with no link is an implementation fact that
no decision-log entry governs. What the terms mean is in the
[glossary](../glossary.md#session), and the modules are mapped in
[architecture.md](../architecture.md).

Two words are kept apart throughout. A **break** is time between runs. A
**pause** is the game's own pause inside a run, which a stats file records as
`Pause Duration:`.

## Where sessions show

- The Run History page is the one page that shows a session, in four
  places: its run list, its latest-run card, the chart's typical-score hover,
  and the Scenario Stats lead's hover. Both typical-score hovers count the
  sessions behind a value ([TS3][typical-chart], [TS5][typical-card-value]).
- The run list has two views. Under This scenario it lists a scenario's runs
  under the session each was played in, names a session by when it started,
  and counts the session's runs, with no session length in this view
  ([2026-10-23](../decision_log/2026/2026-10-23-this-scenario-session-rows-keep-their-score-summaries-inline.md)).
  Under All scenarios it lists every session whole, with its length,
  its runs, and its scenarios, and under each session a row per visit, in the
  order played, with that visit's runs under it
  ([2026-10-14](../decision_log/2026/2026-10-14-the-run-list-has-a-second-view-all-scenarios-that-shows-each-session-whole.md)).
- What the list and the card show in full is in
  [run_history.md](run_history.md#the-run-list).
- Under This scenario the list marks where a scenario was left and returned
  to within a session, which is the boundary between two of its visits, and
  counts the runs played on other scenarios between them. Under All scenarios
  each visit is a row, named by its scenario and numbered by its place in the
  session. The word visit is not on screen.
- The newest session is always the list's first row, whether or not it is in
  progress, and is marked while it is (see [In progress](#in-progress)).
- The latest-run card reports the selected scenario's latest run: its last
  run in the newest session that holds one
  ([2026-10-18](../decision_log/2026/2026-10-18-the-latest-run-card-reports-the-selected-scenarios-latest-run.md)).
  Its third line gives the run's number among its scenario's runs in its
  session, and its fourth the time spent on that scenario in the session:
  the sum of the scenario's visits, each from its first run's start to its
  last run's end. For the newest session it says "this session" while the
  session is in progress and "last session" once it has ended (see
  [In progress](#in-progress)). An older session is named as the list names
  its row, by its first run's start, such as `Run 7 (Oct 16, 2:00 PM
  session)`.
- Where the first run of any of those visits has no usable start, the card
  says the time on the scenario is unknown and gives no number. Such a visit
  is counted from that run's end, so one long run would read as under a
  minute (see [Run start and run length](#run-start-and-run-length)).
- That page's chart plots a scenario's runs in the order sessions are split
  in (see [Sessions](#sessions)).
- No toast or log line shows a session, a visit, a run's start, or a run's
  length.
- A run's start and its run length are shown nowhere by themselves. They
  decide which session a run joins, a session's name and its length are read
  from its first run's start, and the card's time on a scenario is read from
  each visit's first run's start.

## Run start and run length

- Every run has an end: the time in its stats file's name, in whole seconds.
  A run may also have a start and a run length. A run has both or neither
  ([2026-10-11][entry]).
- The start is the date of the run's end with the file's `Challenge Start:`
  as the time of day. `Challenge Start:` is a time of day with no date, so
  when that lands after the end the start is moved back one day: the run
  crossed midnight ([2026-10-11][entry]).
- The run length is the end minus the start, minus the file's
  `Pause Duration:` in seconds. A file with no `Pause Duration:` line
  subtracts nothing ([2026-10-11][entry]).
- A run length under 1 second or over 1,800 seconds is not trusted, and the
  run then has neither a start nor a length. Both ends of the range are
  trusted ([2026-10-11][entry]).
- **Invariant: the upper bound never exceeds the session limit, and never
  exceeds an hour.** A wrong start can then hide a break only when that break
  would not have ended the session anyway, and a run played while the clock
  went forward is never trusted. The code takes the bound as the smaller of
  the two, so changing the session limit can't break it
  ([2026-10-11][entry]).
- A run has neither a start nor a length when its file has no
  `Challenge Start:`, when that line's value is not a time of day written as
  `HH:MM:SS` with a fractional second, or when the file has a
  `Pause Duration:` line whose value is missing, not a number, negative, or
  not finite. None of these costs the run: it loads, and joins a session by
  its end ([2026-10-11][entry]).
- A run with no run length has an unknown length, never a length of zero
  ([Guiding principles](../roadmap.md#guiding-principles)).
- A file that looks like a reset, with a start within a second of its end,
  is still a run. It has no start and no length
  ([2026-10-11][entry]).
- Neither field is stored. The run store is rebuilt from the stats folder at
  every start, and both are read again each time ([2026-10-11][entry]).

## Sessions

- A run belongs to the session of the run that ended before it unless the
  break between them is longer than 30 minutes. A break of exactly 30 minutes
  does not end a session ([2026-10-11][entry]).
- The 30 minutes is one constant in the code, `PLAY_SESSION_BREAK_LIMIT`. The
  app has no setting and no `config.toml` key for it
  ([2026-10-11][entry]).
- The break before a run is its start minus the previous run's end. For a run
  with no start it is the run's end minus the previous run's end, which
  overstates the break by that run's length ([2026-10-11][entry]).
- A negative break counts as no break ([2026-10-11][entry]).
- A pause inside a run is part of the run, not a break. A run that began
  within 30 minutes of the previous run's end joins that session when it
  finishes, however long it was paused, as long as its start is usable
  ([2026-10-11][entry]).
- A run longer than 30 minutes has no start, so its break is measured to its
  end, and it starts a new session ([2026-10-11][entry]).
- Runs are ordered by their end before they are split, so the same runs
  split the same way whatever order they were handed over in. Runs that ended
  in the same second go by their start, earliest first, then by scenario
  name, then by stats file name. A run with no start counts there as
  beginning at its end ([2026-10-11][entry]).
- A session starts at its first run's start, or at that run's end when the
  run has no start. It ends at its last run's end
  ([2026-10-11][entry]).
- Session length is the session's end minus its start, whether or not the
  session is in progress. It includes the breaks between runs
  ([2026-10-11][entry]).
- A session has no identity of its own. A view that needs a key for one uses
  the session's first run ([2026-10-11][entry]).
- A session can cross midnight, and one day can hold several
  ([2026-10-11][entry]).

## In progress

- At most one session is in progress. Only the newest can be: the one whose
  last run ended last ([2026-10-11][entry]).
- The newest session is in progress while no more than 30 minutes have
  passed since its last run ended. At exactly 30 minutes it is still in
  progress. The 30 minutes is the same constant that splits sessions
  ([2026-10-11][entry]).
- The question is asked of every session at once, never of one. After a
  clock change an older session can also be within 30 minutes of the current
  time, and it is still not in progress ([2026-10-11][entry]).
- A newest session whose last run ended after the current time is in
  progress ([2026-10-11][entry]).
- The current time is handed in by the caller, as the app's own clock. It is
  never a browser's clock, because a browser on another device may be in
  another time zone ([2026-10-11][entry]).
- A session that has ended can be in progress again. A run with a usable
  start that began within the 30 minutes and finished after them joins the
  session when it finishes. A run with no usable start does not: a run that
  began a minute after the last one ended and took 40 minutes to play starts
  a new session ([2026-10-11][entry]).
- Nothing happens when a session ends, so a view that shows the state has to
  re-check it on a timer ([2026-10-11][entry]).
- The Run History page's run list asks again every 30 seconds, and when a
  run lands. So its mark for a session in progress clears within 30 seconds
  of the session ending, with no run landing.

## Visits

- A visit is consecutive runs on one scenario within one session. Switching
  to another scenario ends it, and coming back to the scenario later in the
  session starts a new one ([2026-10-11][entry]).
- A scenario is its name. A change of sensitivity doesn't end a visit
  ([2026-10-11][entry]).
- A visit never spans two sessions: visits are found one session at a time
  ([2026-10-11][entry]).
- A visit starts at its first run's start, or at that run's end when the run
  has no start, and ends at its last run's end ([2026-10-11][entry]).

## Computed, never stored

- Sessions and visits are worked out from a list of runs each time something
  asks. Nothing about them is written to disk or kept in memory, so there is
  nothing to migrate, and changing the constant re-splits the whole history
  ([2026-10-11][entry]).
- The session functions take a list of runs and never read the run store. A
  caller copies the store's list of every run and hands the copy over
  ([2026-10-11][entry]).
- A view works out its sessions from the run store when it draws, never from
  the batches of new runs it was sent, because a batch can be missed
  ([2026-10-11][entry]).

## Clock changes

Every time in a stats file is local wall-clock time, and these rules use it
as written. What follows is accepted ([2026-10-11][entry]).

- When the clock goes back, an hour repeats. A break during it can vanish,
  and runs from the two passes through that hour are ordered among each
  other.
- When the clock goes forward, a break reads an hour longer than it was, so
  a five-minute break across the change ends the session.
- A manual clock change, or a trip across time zones, does the same.

[entry]: ../decision_log/2026/2026-10-11-a-session-ends-after-a-break-of-more-than-30-minutes.md

[typical-card-value]: ../decision_log/2026/2026-10-18-scenario-stats-shows-the-newest-typical-score-at-any-age.md

[typical-chart]: ../decision_log/2026/2026-10-18-the-typical-score-is-drawn-after-each-run.md
