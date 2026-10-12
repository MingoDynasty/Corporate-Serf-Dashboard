# 2026-10-11: A Session Ends After A Break Of More Than 30 Minutes

Status: Accepted

The app now has a rule for which runs belong together: a session is the runs
separated by breaks of no more than 30 minutes. The 30 minutes is fixed
rather than a setting, and a session reads as in progress until that long
after its last run. Each run gains a start and a length, read from its stats
file, so a break can be told apart from a long run. No screen shows any of
this yet, and the typical score that Run History was going to define now
waits for a proposal of its own.

**Rulings.** All by the maintainer, 2026-10-11, on
[PR #355](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/355):
rows S1 to S4 ratified as recommended, after both review seats and a
flagship read had endorsed all four. The ratification covers the
author-owned rules below as well. The build is
[PR #359](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/359).
The rules as the app applies them are in [sessions.md](specs/sessions.md).
This entry holds what the spec doesn't: the reasons, the evidence and its
limits, and the options set aside.

**Two words.** A break is time between runs. A pause is the game's own pause
inside a run, which a stats file records as `Pause Duration:`. The rules turn
on the difference.

**S1, a break of more than 30 minutes ends a session.** A run belongs to the
session of the run before it unless more than 30 minutes pass between that
run's end and this run's start. A break of exactly 30 minutes does not end a
session. The argument, in order:

1. **No value is the natural one.** The only real valley in the break lengths
   is at about five hours. Below that the number is a definition, and the
   data only says where it is cheap: 20 to 60 minutes.
2. **Not under 20.** The game stayed open through every logged break of 5 to
   30 minutes. A limit of 10 puts 716 of 2026's 3,277 runs in a different
   session and leaves 29 sessions with fewer than five runs.
3. **Not 60.** In every logged closure the game was shut within 42 minutes of
   the last run. Breaks of 60 to 120 minutes are a second kind of break,
   coming back an hour or two later, and 60 sits on its rising edge. A limit
   of 60 also counts absences of up to 85 minutes inside a session's length,
   and keeps a session in progress for an hour after the player left.
4. **30 inside that range.** It is the value web analytics tools default to,
   and the one the maintainer's training notes already use. It is the
   shortest defensible value, so a session stops reading as in progress
   soonest. After a break of 30 to 60 minutes the next run was on the same
   scenario a quarter of the time, against about half after a shorter break,
   which is suggestive and not established.

Where 30 gives a wrong answer, on 2026's runs:

- A break of 31 to 59 minutes ends the session even when the player came back
  to the same sitting. There were nine, in eight sittings.
- A break of 20 to 30 minutes followed by something unrelated does not end
  it. There were seven, and five came back to a different scenario.
- Six breaks fall within 3 minutes of 30. None falls within 3 minutes of 45.
- A session's length includes time away. Breaks over 10 minutes add up to
  10.3 hours inside the year's session lengths.

45 is the runner-up. It is the quietest part of the data, it sits just above
the 42 minutes the game was left open after a last run, and it would merge
six of 2026's 117 boundaries. 30 won over it because the two errors aren't
equally visible: a session split at a 35-minute break shows as two rows with
their start times, while a 40-minute absence merged into one session is
hidden inside its length. Three positions agreed on 30 with 45 second: the
discussion that gathered the evidence, a consult with `claude-fable-5-1`
whose brief withheld that recommendation, and the proposal's author. What
would move it to 45:

- game logs covering breaks of 30 to 60 minutes that show the game left open
  through most of them (no logged day has such a break);
- other players' histories whose breaks within a sitting run past 45
  minutes;
- the eight split sittings reading as wrongly split on the real page.

Another value shifts every session count and length and nothing else. At 15
minutes the 2026 history gains 16 sessions, at 45 it loses 6, and at 60 it
loses 9.

**S2, the 30 is fixed.** The limit is one named constant in the code,
`PLAY_SESSION_BREAK_LIMIT`. The app has no setting and no `config.toml` key
for it, so every install splits the same runs the same way.

- The evidence can't advise a user. Anywhere from 20 to 60 minutes, the limit
  puts about 5% of 2026's runs or fewer in a different session than 30 does,
  so a setting would ask each user to tune a number the app can't recommend a
  value for.
- A setting needs a control, its copy, a spec line, and tests, and two
  installs would stop agreeing on what a session is.
- Fixed is the reversible choice. A `config.toml` key can be added later
  without breaking anything, and removing a shipped setting would break
  whoever set it.
- One player's history is the weak point. If other players' breaks within a
  sitting run longer, the answer is a different constant for everyone, which
  stays a one-line change.

**S3, in progress until 30 minutes after the last run.** A session is in
progress while no more than 30 minutes have passed since its last run ended,
and after that it has ended. The 30 is S1's constant, not a second number, so
a session reads as in progress for exactly as long as a new run would still
join it.

- The state depends on the clock, not on a run landing. Nothing arrives when
  a session ends, so a surface that shows the state re-checks it on a timer.
  The
  [connector raised this](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/351#discussion_r4191712545)
  on PR #351: a list that redraws only when a run lands would read "in
  progress" indefinitely. This entry sets the rule, and the Run History page
  owns the timer.
- An ended session can reopen. The app sees a run only when it finishes, so a
  run begun inside the 30 minutes and finished after them joins the session
  it was begun in, as long as its start is usable. The session reads as ended
  from the 30-minute mark until that run finishes. That is usually under a
  minute, and longer when the run was paused. It happened twice in seven
  years of the maintainer's history, for about half a minute each time.
- Where it gives a wrong answer: the session reads as in progress for 30
  minutes after the player has left.
- A shorter timer for the state alone was set aside. A session would read as
  ended and then routinely gain runs, and the app would have a second number
  to explain.

**S4, the typical score's definition leaves Run History.** Run History
neither defines nor shows the typical score, which the roadmap calls the
typical run. Its definition goes to a later proposal of its own, written
before the first feature that judges by it. This changes one sentence of the
[2026-10-04 entry](#2026-10-04-skill-is-judged-by-the-typical-run-with-honest-uncertainty-in-verdicts-not-advice),
which said the definition was the Run History proposal's to set. That entry
carries a dated note beside the sentence. Its row D1 is unchanged: skill is
still judged by the typical run, and only where the definition gets written
moves.

- Nothing in version 1 of the page reads it. The page shows runs, sessions,
  and each run's result against the PB and the score threshold.
- A definition with no reader can't be checked.
  [PR #351](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/351)
  defined it and found it unknown for 80% of the scenarios played in a 2026
  session. What the window and the minimum should be depends on what the
  figure is used for.
- Its inputs left too. That definition excluded warm-up runs, and version 1
  has no warm-up rule in any form.
- The later proposal inherits PR #351's row H4 and its typical score
  evidence, at commit `6177dd3`, and two of the connector's comments on that
  PR: that the figure
  [stays known from an arbitrarily old session](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/351#discussion_r4191712540)
  after a long break, and that
  [holding a run's comparison set fixed for its session](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/351#discussion_r4191712550)
  is a product choice.

**Run start and run length.** The run record gains a start and a length, both
optional, read from two more lines of a stats file the parser already reads.
Nothing is written to disk: the run store is rebuilt from the stats folder at
every start.

- The start is the file's date with `Challenge Start:` as the time of day. It
  moves back a day when that lands after the end, which is a run that crossed
  midnight.
- The length is the end minus the start, minus `Pause Duration:` when the
  file has one.
- The length is unknown outside 1 to 1,800 seconds, and the start with it. A
  length out of range means the start or the pause can't be trusted. The
  range covers the 46 negative lengths from 2021, a reset-shaped file whose
  start is within a second of its end, a run across a clock change, and a
  start left over from another run when it is far enough off.
- A file with no `Challenge Start:` has neither, and still joins a session by
  its end. A malformed start reads as a missing one. A `Pause Duration:` line
  that is there and can't be read also costs the start and the length,
  because the paused time is then unknown. None of these costs the run.
- A run longer than 30 minutes loses its start and its length, and its break
  is measured to its end. The longest run in the history is 238 seconds, but
  a scenario sets its own timer and other players' runs may be far longer.

**The bound's invariant.** The upper bound may never exceed the session
limit. A start left over from an earlier run makes the break before its run
read as nothing. With the bound at the limit, such a start is trusted only
when the real break was under 30 minutes, which would not have ended the
session anyway. So a wrong start can hide a break only when that break would
not have ended the session. The bound also has to sit above any real run and
at or under an hour, so that a run played while the clock went forward is
still caught. The code derives it as the smaller of the session limit and an
hour, so an edit to the limit can't break either condition.

The bound doesn't catch a start that is wrong by less. A run from 2025-07-13
reads 127.7 seconds on a 60-second scenario, because its `Challenge Start:`
repeats the previous run's. Its break comes out negative, which the session
rule counts as no break. Two days of files from July 2021 wrote the pause as
a running total for the whole time the game was open. They are not
special-cased: where the subtraction leaves a length in range, it is too
short, never too long. Trusting the start by the span and the length
separately would have kept 45 of those starts, and was rejected as a second
rule for two days of play five years ago.

**How a session is built.** One pure function over the runs. It sorts them by
end time itself, so its answer never depends on the order a caller hands
them over in. The end is in whole seconds, so two runs can share one, after
the clock goes back or when a stats file has a stray copy, and which comes
first can move a boundary when their starts differ. Such runs go by their
start, earliest first, a run with no start counting as beginning at its end,
then by scenario name and stats file name. The maintainer's history has no
two runs that share an end second.

- The break between two runs is the next run's start minus this run's end.
  When the next run has no start, it is the next run's end minus this run's
  end, which overstates the break by that run's length.
- A negative break counts as no break.
- A session starts at its first run's start, or at that run's end when it has
  no start, and ends at its last run's end. Its length is the difference, in
  progress or not, so it includes the time between runs.
- A session has no stored identity. A view that needs a key uses the
  session's first run.

On the history the missing start moves no boundary: 508 breaks are measured
to the next run's end, all before 2022, and none is within a run's length of
30 minutes. 37 of the 322 sessions start at their first run's end.

**A pause inside a run is part of the run, not a break.** A run with a usable
start inside the 30 minutes rejoins its session when it finishes, even after
a long pause. The alternative, counting a run's paused time as part of the
break before it, was rejected. A run paused for an hour would then start a
new session, and a session could read as ended for one run's playing time at
most. But the run's start would then mean two things: when it began, for a
session's length, and when its playing began, for the break. No pause since
2024 is longer than 209 seconds, and the two rules agree on every session
boundary in the history.

**In progress is asked of the whole list.** One pure function of the sessions
and the current time returns the session in progress, or none. Only the
newest session can be in progress, the one whose last run ended last. After a
clock change two sessions can both pass the time test: one that ended minutes
ago, and a later-sorted one whose runs carry times still in the future. Asked
of the list, the answer is one session or none. The time is an argument, and
the caller passes the app's own clock: run times are wall-clock times on the
machine that wrote the stats files, and a browser on another device may be in
another time zone. A last run in the future counts as in progress.

**Visits.** A visit is consecutive runs on one scenario within a session.
Switching scenarios ends it, and coming back later in the session starts a
new one. A scenario is its name, and a change of sensitivity doesn't end a
visit. The 2026-10-04 entry called visit a working word that the shipping
proposal names and may rename. This one keeps it and gives it a glossary
entry, because the code and the spec now ship the word. No screen shows it
yet.

**Computed, never stored.** Sessions and visits are derived from the run
store when something asks for them, and nothing is stored, so no migration is
needed and changing the constant re-splits the whole history. A view derives
its sessions from the run store when it draws, never from the batches of new
runs it was sent, because a batch can be missed. The functions take a list of
runs and never read the store. The store is written by the watchdog thread
and read without a lock, and a caller that hands over a copy keeps that
question out of the session code. One pass over 9,135 runs, into sessions and
each session into visits, took a median of 2.6 ms on the maintainer's machine
on 2026-10-11.

**Code words.** The code says `play_session` for a session and
`scenario_visit` for a visit. `session` already names an HTTP session and an
app session there, and "visit" is the docs' everyday word for one load of a
page.

**Clock changes are accepted.** Every time in a stats file is local
wall-clock time, and the rules use it as written.

- When the clock goes back, an hour repeats. A real break can vanish, and
  runs from the two passes through that hour sort among each other.
- When the clock goes forward, a break reads an hour longer than it was, so a
  five-minute break across the change ends the session.
- A manual clock change or a trip across time zones does the same.

It happened once in seven years. On 2025-11-02 the clock went from 2 AM back
to 1 AM while the maintainer was playing. By the files' own modification
times the night held a 54-minute break, which ends a session, and ran about
160 minutes from first to last. By the times in the file names the break is
not there, and the night reads as one session of 32 runs, about 100 minutes
long. A time in the repeated hour can't be placed without another clock. The
file's modification time is one, but copying or restoring the stats folder
rewrites it, so it can't be the rule. The cost is a wrong session at most
twice a year, for a player who is playing when the clock changes.

**Alternatives rejected.**

- **One session per calendar day.** 22 sessions cross midnight. Of the 169
  dates a session started on, 85 hold two or more sessions, and the most on
  one date is six.
- **A session as one launch of the game.** It needs the game's own log, a new
  dependency, and the game was left open through breaks of up to 15 minutes
  on the logged days. KovaaK's 3.9.10 also stopped writing the log that holds
  the open and close times.
- **A threshold fitted to each player's own breaks.** Two published methods
  were tried. The Mehrzadi and Feitelson rule gives 34 minutes on all years
  and 137 on 2025 alone. The Halfaker mixture method gives 19 to 42 minutes
  in most fits and 387 in one, and changes between runs on the same data.
- **Measuring every break from end to end.** It needs no start, and it agrees
  with the rule above on all but 2 of 8,941 breaks. But a break is time not
  playing. Measured end to end, a long run counts as part of the break before
  it, and a session can be cut by the length of the run that resumed it. Both
  of the 2 are such cases.

**Carried from the earlier Run History proposal.** That proposal held three
positions on sessions under its Durable decisions, and the page proposal
rewrites the file, so this entry now carries them.

| Position | Here |
|---|---|
| Sessions are gap-based, not per calendar day. | Kept, as S1. |
| The gap is a constant of about 30 minutes in the code, not config or a control. | Kept, as S1 and S2, with its reason corrected. |
| No SQLite migration is required. | Kept: sessions are computed and never stored. |

The second position's reason was that the output is "insensitive across a
wide range". It isn't: moving the limit from 15 to 60 minutes removes 81 of
374 session boundaries, about one in five. The choice matters, and it has no
evidence-backed answer inside 20 to 60 minutes.

**The evidence is one player's history.** The numbers above are from the
maintainer's stats folder as it stood at its last run of 2026-10-08: 8,942
stats files, covering 866 scenarios from 2019-07-14. They show what the rules
do on that history, and nothing about other players' histories. Game logs
covered seven days and no break of 30 to 60 minutes. The scripts are
untracked, in the main checkout's scratch folder. The built code was run over
the same snapshot on 2026-10-11 and gave the proposal's counts: 8,433 runs
with a usable start, 322 sessions, 15 of them a single run, and 2,895 visits.

**Out of scope, and where it went.** Everything on screen belongs to the Run
History page's proposal
([PR #356](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/356)):
session rows, the in-progress state and its timer, the run number within a
session, and marks on a run. Warm-up runs, a divider for a long break inside
a session, and a shorter timer for the in-progress state are parked. Reset
files still count as runs, and get no run length because their start is
within a second of their end.
