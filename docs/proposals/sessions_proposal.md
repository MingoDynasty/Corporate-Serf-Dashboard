# Sessions Proposal

Status: Proposed
Date: 2026-10-11

## TL;DR

The app holds every run but has no rule for which runs belong together, so
it can't show a session or say whether one is still going. This proposal
defines a session as the runs separated by breaks of no more than 30
minutes, and gives each run a start and a length so a break can be measured.
It builds that as a layer with nothing on screen, which the Run History page
then stands on. It also moves the definition of the typical score out of Run
History, to a proposal of its own.

## Decisions needed

Four rulings: S1 to S4. The maintainer ratified this proposal on
2026-10-11, after every reviewer had endorsed all four rows. That settles
each as its recommendation. Each keeps its argument, where the
recommendation gives a wrong answer, and what the alternatives would have
changed, for the record. Everything else is author-owned, in
[Design](#design), and the ratification covers it too. The IDs start with S
so they can't be confused with H1 to H6 of
[PR #351](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/351)
or D1 to D5 of
[PR #327](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/327).

**Where this sits.** Run History was one proposal and is now five pieces:
groundwork with no proposal, Sessions, Run toasts
([PR #354](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/354)),
the Run History page, version 1
([PR #356](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/356)),
and All scenarios. The maintainer agreed the split on 2026-10-10: "Merged
breakdown is a go." That agrees the outline and ratifies no row. This piece
depends on none of the others. The page's run list and its latest-run card
are built on it.

**Already decided, and binding here.**

- **Sessions come first.** "Sessions, and the visits inside them, are built
  before either history view, as the foundation the views and later
  features share"
  ([2026-10-04](../decision_log.md#2026-10-04-skill-is-judged-by-the-typical-run-with-honest-uncertainty-in-verdicts-not-advice),
  row D4). This proposal is that foundation.
- **Unknown isn't weak.** A run whose stats file gives no usable start has
  no run length. It never reads as zero
  ([Guiding principles](../roadmap.md#guiding-principles)).

**Carried forward from the old proposal.** The
[Run History proposal](./run_history_proposal.md) on `main` holds three
positions on sessions under its Durable decisions. The page proposal
rewrites that file from scratch, so the three continue here.

| Old position | Here |
|---|---|
| Sessions are gap-based, not per calendar day. | S1. Kept. |
| The gap is a constant of about 30 minutes in the code, not config or a control. | S1 and S2. Kept, with its reason corrected. The old text says the output is "insensitive across a wide range". It isn't: see S1. |
| No SQLite migration is required. | Kept, as an author-owned choice: [Computed, never stored](#computed-never-stored). |

### S1. A session ends after a break of more than 30 minutes

Status: Ratified (user), 2026-10-11: accept the recommendation below.

The material consequence: the app splits a player's runs into sessions
wherever more than 30 minutes pass between one run's end and the next run's
start. A break of 31 to 59 minutes inside one sitting ends a session.

**Recommendation: a run belongs to the session of the run before it unless
more than 30 minutes pass between that run's end and this run's start.**

The maintainer, 2026-10-10: "I accept 30." And later that day: "30 is an
accepted lean. Let's take it to proposal review to get Codex's take before
we ratify." It went to review for that take and was ratified after it.

The argument, in order. The numbers are in [Evidence](#evidence).

1. **No value is the natural one.** The only real valley in the
   maintainer's break lengths is at about five hours. Below that the number
   is a definition, and the data only says where it is cheap: 20 to 60
   minutes.
2. **Not under 20.** The game stayed open through every logged break of 5
   to 30 minutes. A limit of 10 puts 716 of 2026's 3,277 runs in a
   different session and leaves 29 sessions with fewer than five runs.
3. **Not 60.** In every logged closure the game was shut within 42 minutes
   of the last run. Breaks of 60 to 120 minutes are a second kind of break,
   coming back an hour or two later, and 60 sits on its rising edge. A
   limit of 60 also counts absences of up to 85 minutes inside a session's
   length, and keeps a session in progress for an hour after the player
   left.
4. **30 inside that range.** It is the value web analytics tools default
   to, and the one the maintainer's training notes already use. It is the
   shortest defensible value, so a session stops reading as in progress
   soonest. The maintainer's behavior also changes there: after a break of
   30 to 60 minutes the next run is on the same scenario a quarter of the
   time, against about half after a shorter break. That last point is
   suggestive, not established.

**The old proposal's reason does not hold.** It kept the gap fixed because
the output was "insensitive" from 15 to 60 minutes. Moving the limit across
that range removes 81 of 374 session boundaries, about one in five. The
choice matters. It just has no evidence-backed answer inside 20 to 60.

**Where 30 gives a wrong answer.**

- **A break of 31 to 59 minutes ends the session, even when the player
  came back to the same sitting.** There were nine in 2026, in eight
  sittings. The [table](#where-30-splits-a-sitting) lists them.
- **A break of 20 to 30 minutes followed by something unrelated does not
  end it.** There were seven in 2026, and five came back to a different
  scenario.
- **Near misses.** Six of 2026's breaks fall within 3 minutes of 30. None
  falls within 3 minutes of 45.
- **A session's length includes time away.** Breaks over 10 minutes add up
  to 10.3 hours inside 2026's session lengths.

**45 is the runner-up.** It is the quietest part of the data. It also sits
just above 42 minutes, the longest the game was left open after a last run
on the logged days. It would merge six of 2026's 117 boundaries. 10, 15,
20, and 60 are argued against above.

**Three positions exist, and they agree.** The discussion that gathered the
evidence chose 30 with 45 second. A consult with `claude-fable-5-1`, whose
brief withheld that recommendation, chose the same. This author session
re-ran the scripts and agrees, for one more reason: the two errors aren't
equally visible. A session split at a 35-minute break shows as two rows
with their start times, so the player can see what happened. A 40-minute
absence merged into one session is hidden inside its length, because
version 1 draws nothing where a break was. None of the three would fight
between 30 and 45.

**What would move it to 45:**

- game logs covering breaks of 30 to 60 minutes that show the game left
  open through most of them (no logged day has such a break);
- other players' histories whose breaks within a sitting run past 45
  minutes;
- the eight sittings in the table reading as wrongly split on the real
  page.

**If the maintainer chooses another value:** every session count and
session length shifts with it, and nothing else does. Sessions are never
stored, so the constant can change later with no migration. At 15 minutes
the 2026 history gains 16 sessions. At 45 it loses 6, and at 60 it loses 9.

### S2. The 30 is fixed, not a setting

Status: Ratified (user), 2026-10-11: accept the recommendation below.

The material consequence: the app has no setting and no `config.toml` key
for the limit, so every install splits the same runs the same way. Changing
the value is a change to the code.

**Recommendation: the limit is one named constant in the code. The app has
no setting and no `config.toml` key for it.**

The lean is recorded from 2026-10-07 without the maintainer's wording. The
`claude-fable-5-1` consult endorsed it.

- **The evidence can't advise a user.** Anywhere from 20 to 60 minutes, the
  limit puts about 5% of 2026's runs or fewer in a different session than
  30 does. A setting would ask each user to tune a number the app can't
  recommend a value for.
- **A setting has a cost.** It needs a control, its copy, a spec line, and
  tests. Two installs would also stop agreeing on what a session is.
- **Fixed is the reversible choice.** A `config.toml` key can be added
  later without breaking anything. Removing a shipped setting would break
  whoever set it.
- **One player's history is the weak point.** If other players' breaks
  within a sitting run longer, the answer is a different constant for
  everyone (S1), which stays a one-line change.

**If the maintainer chooses a setting:** this proposal gains a control and
a Copy block, and two installs can split the same runs into different
sessions.

### S3. A session is in progress until 30 minutes after its last run

Status: Ratified (user), 2026-10-11: accept the recommendation below.

The material consequence: a session reads as in progress for 30 minutes
after its last run, a view that shows the state re-checks it on a timer,
and a session that has read as ended can reopen when a late run lands.

**Recommendation: a session is in progress while no more than 30 minutes
have passed since its last run ended. After that it has ended. The 30 is
S1's constant, not a second number.**

No wording of the maintainer's is recorded for this row. It was in the
breakdown the maintainer agreed.

- **One number, one meaning.** A session reads as in progress for exactly
  as long as a new run would still join it.
- **It depends on the clock, not on a run landing.** Nothing arrives when a
  session ends. Any surface that shows the state has to re-check it on a
  timer. The connector raised this on PR #351
  ([comment](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/351#discussion_r4191712545)):
  a list that redraws only when a run lands would read "in progress"
  indefinitely. This row sets the rule. The page proposal owns the timer.
- **An ended session can reopen.** The app sees a run only when it
  finishes. A run begun inside the 30 minutes and finished after them joins
  the session it was begun in, as long as its start is usable. So a session
  can read as ended and then gain a run. It reads as ended from the
  30-minute mark until that run finishes. That is usually under a minute.
  It is longer when the run was paused, because a pause is part of the run
  and not a break. It happened twice in seven years of the maintainer's
  history, for about half a minute each time.

**Where it gives a wrong answer.** The session reads as in progress for 30
minutes after the player has left.

**If the maintainer chooses a shorter timer for the state alone:** a
session reads as ended and then routinely gains runs, and the app has a
second number to explain. That option is parked with three other ideas
([Out of scope](#out-of-scope)).

### S4. The typical score's definition leaves Run History

Status: Ratified (user), 2026-10-11: accept the recommendation below.

The material consequence: Run History version 1 neither defines nor shows
the typical score. Its definition waits for a proposal of its own, and the
2026-10-04 entry gains a dated note saying so when this proposal ships.

**Recommendation: Run History neither defines nor shows the typical score,
which the roadmap calls the typical run. The definition goes to a later
proposal of its own, written before the first feature that judges by it.**

This needs a row because a ruled decision says otherwise. The
[2026-10-04 entry](../decision_log.md#2026-10-04-skill-is-judged-by-the-typical-run-with-honest-uncertainty-in-verdicts-not-advice)
says: "What counts as the typical run (the window, the run count, the
warm-up rule) is the Run History proposal's to set." The maintainer,
2026-10-10: "Typical score: agree to leave out of v1 entirely."

- **Nothing in version 1 reads it.** The page shows runs, sessions, and
  each run's result against the PB and the score threshold.
- **A definition with no reader can't be checked.** PR #351 defined it and
  found it unknown for 80% of the scenarios played in a 2026 session. What
  the window and the minimum should be depends on what the figure is used
  for.
- **Its inputs left too.** That definition excluded warm-up runs, and
  version 1 has no warm-up rule in any form.
- **It keeps this piece small.** The maintainer's concern with the single
  proposal was "trying to ship too many things at once."

What does not change: skill is still judged by the typical run (row D1 of
the same entry). Only where its definition gets written moves. The features
it would be written for are in the roadmap's Future list: the trend verdict
and weakness by the typical run.

What the later proposal inherits:

- PR #351's row H4 and its typical score evidence, at commit `6177dd3`;
- two of the connector's comments on that PR: that the figure stays known
  from an arbitrarily old session after a long break
  ([comment](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/351#discussion_r4191712540)),
  and that holding a run's comparison set fixed for its session is a
  product choice
  ([comment](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/351#discussion_r4191712550)).

**If the maintainer keeps it in Run History:** it becomes a row of the page
proposal, and the warm-up rule has to be decided first.

## Problem

The app (a Dash web app that watches the KovaaK's stats folder and plots
each scenario's scores) keeps every run in memory, in the order the runs
ended.

- **It has no rule for a session.** The
  [glossary](../glossary.md#session) says so: "The app has no rule yet for
  where one session ends; the first feature that needs one sets it."
  [product.md](../product.md#when-they-ask-them) names *how is this session
  going?* as one of the two questions asked in session.
- **A run has an end and no start.** The run record's one timestamp comes
  from the stats file's name, in whole seconds. Nothing under `source/`
  reads the file's `Challenge Start:` or `Pause Duration:` lines. So the
  app can't tell a break from a long run, and can't say how long a run
  took.
- **The page needs both.** Version 1 of the Run History page groups its run
  list by session, numbers a run within its session, and marks the session
  in progress. Later features need the same: the trend verdict is built on
  session medians.
- **It was part of a proposal that carried too much.** PR #351 defined
  sessions together with two views, a typical score, and a per-run readout.
  The maintainer asked for the work to be split so that one part can ship
  while another is still debated. This is the part nothing else has to wait
  for.

## Evidence

One player's history: the maintainer's stats folder. It shows what the
rules do on that history. It doesn't show what other players' histories
look like.

- **The snapshot.** 8,942 stats files, all of which the app's own parser
  accepts, covering 866 scenarios from 2019-07-14 to 2026-10-08. By year:
  12 in 2019, 471 in 2020, 87 in 2021, none in 2022 or 2023, 36 in 2024,
  5,059 in 2025, and 3,277 in 2026.
- **Re-run for this proposal.** The folder keeps growing, so on 2026-10-11
  the scripts were re-run with the runs cut off at the snapshot's last run.
  The gap analysis, the per-limit table, and the threshold rule printed the
  same results as on 2026-10-08, line for line. The mixture fit, which
  starts from random points, and the game-log reading were not re-run.
- **On the folder as it stood on 2026-10-11** (9,135 files), no conclusion
  changes. There are 325 sessions at 30 minutes, against 322. The 2026
  breaks of 30 to 60 minutes are the same nine, and so is the table of
  split sittings.
- **The scripts are untracked,** in `ignore/scripts/run-history/`,
  `ignore/scripts/session-gap/`, and `ignore/scripts/sessions-proposal/` of
  the main checkout. Their printed results are in `ignore/data/session-gap/`
  and `ignore/data/sessions-proposal/`. The last folder's `snapshot.py` runs
  any of them with the runs cut off at `2026-10-08T14:15:35`, which
  reproduces the snapshot.

### Run length

A run's length is the time in its file name, minus `Challenge Start:`,
minus `Pause Duration:`.

- **Every run since 2024 has one:** 8,372 runs. Across all years it is
  8,433 of 8,942.
- **463 files have no `Challenge Start:`,** 12 from 2019 and 451 from 2020.
  They have an end and no start.
- **46 lengths come out negative,** all from 2021. One is half a second
  short, the file the
  [Aimcurve survey](../research/aimcurve_learnings_opus.md#4-a-reset-can-write-a-stats-file-that-looks-like-a-run)
  calls reset-shaped. The other 45 are from 2021-07-19 and 2021-07-20. On
  those two days the game wrote `Pause Count:` and `Pause Duration:` as
  running totals for the whole time it was open. On the second day the
  count climbs from 1 to 55 across 50 files, while each run still spans
  about 60 seconds.
- **51 files have a start and no `Pause Duration:`,** all from 2020 and
  2021.
- **Since 2024 the pause is per run.** Ten runs were paused. In the nine
  whose scenario has other runs to compare with, the span minus the pause
  is within a second of the scenario's usual length. One spans 269 seconds
  with 209 paused.
- **13 runs crossed midnight.** `Challenge Start:` is a time of day with no
  date, so a start later in the day than the end means the day before.
- **Lengths are steady and short.** Of 324 scenarios with five or more
  timed runs, 318 have a fixed length: 287 at 59 or 60 seconds, 23 at 29 or
  30, and 8 between 39 and 50. Six vary from run to run, and all six are
  time-scored. The longest run in the history is 238 seconds.
- **One start since 2021 is wrong.** A run from 2025-07-13 reads 127.7
  seconds on a 60-second scenario, with no pause recorded. Its
  `Challenge Start:` repeats the previous run's, to the millisecond.
- **Runs fill about half a session.** In the 104 sessions of 2026 with five
  or more runs and ten or more minutes, runs fill a median 49% of the
  session's length, with a middle half of 41% to 56%.

### Breaks between runs

A break here is the time from one run's end to the next run's start. There
are 8,941. Two are negative. The rest, by length in minutes:

| Under 5 | 5-10 | 10-15 | 15-20 | 20-30 | 30-45 | 45-60 | 60-90 | 90-120 | 120-240 | 240-480 | 480-1440 | Over 1440 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 8,345 | 160 | 60 | 26 | 27 | 18 | 10 | 26 | 23 | 30 | 22 | 100 | 92 |

- **Breaks of 2 to 60 minutes follow one line.** A power law fitted on
  breaks of 2 to 30 minutes predicts about 18 breaks of 30 to 45 minutes
  (16.5 to 20.2 across fitting ranges; 18 seen) and about 9 of 45 to 60
  (10 seen).
- **A second population starts at about 60 minutes.** The same line
  predicts 8.9 breaks of 60 to 90 minutes and 4.5 of 90 to 120. There are
  26 and 23. The excess is three to five times in every fitting range, and
  in 2025 and 2026 separately.
- **The only valley is at about five hours.** The least likely break length
  is 256 to 314 minutes, depending on smoothing.
- **Published threshold methods land near 30 without pinning it.** The
  Mehrzadi and Feitelson rule gives 34 minutes on all years, on 2026, and
  on 2025 and 2026 together, and 137 on 2025 alone. The Halfaker mixture
  method gives 19 to 42 minutes in most fits and 387 in one, and it changes
  between runs on the same data.
- **Game logs, seven days** (2026-09-23 to 2026-09-28, and 2026-10-04).
  The game stayed open through all 13 breaks of 5 to 30 minutes, the
  longest 15.3. It was closed in every logged break of 86 minutes or more,
  nine of them. In ten closures it was shut 0.8 to 41.8 minutes after the
  last run, a median of about 4. No break of 30 to 60 minutes fell on a
  covered day.
- **The same scenario after a break:** about half the time after any break
  of 2 to 30 minutes, 25% after 30 to 60 (7 of 28), 43% after 60 to 120
  (21 of 49), and about 19% beyond two hours. Fisher's exact test gives p
  0.02 for 10-to-30 against 30-to-60, 0.10 for 20-to-30 against 30-to-60,
  and 0.14 for 30-to-60 against 60-to-120.
- **Measuring to the next run's start or to its end** puts 2 of the 8,941
  breaks on different sides of 30 minutes. Both are from 2026: 29.5 and
  28.3 minutes of idle time, each 30.5 or more from end to end.
- **Counting a run's paused time as part of the break** changes the
  measure of 21 breaks, by 209 seconds at most, and puts none on the other
  side of 30 minutes.

### What each limit does

All years:

| Limit, minutes | 5 | 10 | 15 | 20 | 30 | 45 | 60 | 90 | 120 |
|---|---|---|---|---|---|---|---|---|---|
| Sessions | 595 | 435 | 375 | 349 | 322 | 304 | 294 | 268 | 245 |

In 2026:

| Limit, minutes | 10 | 15 | 20 | 30 | 45 | 60 |
|---|---|---|---|---|---|---|
| Sessions | 158 | 134 | 125 | 118 | 112 | 109 |
| Sessions under 5 runs | 29 | 18 | 14 | 11 | 8 | 8 |
| Median session length, 2+ runs, minutes | 32 | 38 | 44 | 49 | 59 | 60 |
| Runs in a different session than at 30 | 716 | 316 | 174 | 0 | 80 | 122 |
| Hours away counted inside session lengths | 0.0 | 4.9 | 7.4 | 10.3 | 13.6 | 16.3 |
| Sessions holding a break over 30 minutes | 0 | 0 | 0 | 0 | 6 | 8 |

### Where 30 splits a sitting

The nine 2026 breaks of 31 to 59 minutes, in eight sittings:

| Sitting | Minutes away | Sessions at 30, in runs | At 60 |
|---|---|---|---|
| Sun May 3 | 31 | 22, 1 | 23 |
| Tue May 5 | 31 | 3, 4 | 7 |
| Sun May 10 | 58 | 51, 17 | 68 |
| Mon Sep 14 | 35 | 5, 19 | 24 |
| Tue Sep 15, afternoon | 51 and 34 | 9, 13, 9 | 31 |
| Tue Sep 15, night | 31 | 19, 37 | 56 |
| Wed Sep 16 | 38 | 18, 10 | 28 |
| Thu Oct 1 | 53 | 36, 12 | 48 |

The six 2026 breaks within 3 minutes of 30 are 28.1, 28.3, 29.5, 30.5,
30.7, and 31.0 minutes. Across all years the consult counted 11 near 30
against 4 near 45. Both are what the fitted line predicts, so 30 is busier,
not unusual.

### What the research says

Gathered in two passes on 2026-10-08. "Checked" means the gathering session
read the figure on the source. The rest came from a research subagent,
mostly from abstracts. This session re-read none of it.

- **Sports science dates warm-up decay, not sessions.** About half of a
  warm-up's jump-height gain is lost between 20 and 30 minutes of sitting
  (Swinton et al. 2022, 12 players; checked). No source gives a session
  boundary in minutes.
- **The 30-minute convention is thin.** It traces to Catledge and Pitkow
  1995: a mean gap of 9.3 minutes plus 1.5 standard deviations gave 25.5,
  in 107 web users, later rounded up. Jones and Klinkner 2008 found it
  "receives no support" for search sessions.
- **Data-driven thresholds vary with the activity.** Halfaker et al. 2015
  recommend "about 1 hour" for web activity and found 14 minutes for League
  of Legends (checked). Sapienza et al. 2018 cut League of Legends sessions
  at 15 minutes, the median break between matches (checked).
- **Precedents split by purpose.** Studies of fatigue inside continuous
  play use 5 to 20 minutes. Tools and studies that group activity into
  sittings use 30 to 120. A session row is the second kind.
- **Other KovaaK's tools:** RefleK's defaults to 20 minutes. The
  kovaaks-stats project uses 60 (both checked in source).

### Sessions at 30 minutes

- **322 sessions,** 15 of them a single run. The median session has about
  22 runs. Among those of two or more runs, the median lasts 40 minutes and
  the longest 242.
- **Per calendar day would be wrong often.** 22 sessions cross midnight. Of
  the 169 dates a session started on, 85 hold two or more sessions, and the
  most on one date is six.
- **Cost:** one pass that splits all 8,942 runs into sessions, and each
  session into stretches of one scenario, took 3.0 ms in plain Python on
  the maintainer's machine on 2026-10-11, and 5.9 ms on 2026-10-05.

### Stretches of one scenario

A stretch is consecutive runs on one scenario inside a session, with no
other scenario between them. It is what the Terms block calls a visit.

- **2,895 stretches** in the 322 sessions. In 2026 the median session has
  5, a third have more than 8, and the largest has 71.
- **A scenario is usually played in one stretch.** Of 2,699
  scenario-in-session pairs, 94% are a single stretch. The player came back
  to a scenario later in the same session 196 times.
- **66 of 322 sessions** hold a scenario that was left and returned to, 26
  of them among 2026's 118.

### A clock change in the history

One session in seven years spans a daylight-saving change. On 2025-11-02
the clock went from 2 AM back to 1 AM while the maintainer was playing. The
stats files' own modification times give the true order:

- four runs ending 12:35 AM to 12:47 AM;
- a break of 29 minutes;
- two runs ending 1:17 AM and 1:20 AM, before the change;
- a break of 54 minutes;
- 26 runs ending 1:15 AM to 2:16 AM, after the change.

By the times in the file names, the 54-minute break is not there. The two
runs from before the change sort among the runs from after it, and the
whole night reads as one session of 32 runs, about 100 minutes long. It was
about 160 minutes from first to last, with a break that ends a session
inside it. One of the history's two negative breaks is from this night.
The other is the repeated start in [Run length](#run-length).

### Ingestion

The app's surviving debug logs cover 2026-07-27 to 2026-10-09 and record
1,163 new stats files, 1,151 of them still in the stats folder.

- **No file was detected twice.**
- **No import failure was logged.**
- **No stats file sits between two detected runs under ten minutes apart
  without being detected itself.**

The logs include agents' test runs, and the last check can't see a miss at
the start or end of a stretch.

### Not checked

- **No other player's data.** S1 and S2 rest on one history.
- **Game logs for breaks of 30 to 60 minutes.** None fell on a logged day.
  KovaaK's 3.9.10, released 2026-09-28, stopped writing the log that holds
  open, close, and focus times.
- **Game builds between 2.0.5 and 3.7.** The folder has 87 runs from 2021
  and none until December 2024, so the build where the pause fields changed
  meaning isn't known.
- **A spring clock change.** None falls inside a session in this history.
  It is reasoned about in Design.
- **Reset files,** which are out of scope.
- **A long scenario.** The longest run in the history is 238 seconds, so
  nothing here measures a run of ten minutes or more.

## Design

No user sees this layer. The Run History page, and later features, read it.

**Two words.** A break is time between runs. A pause is the game's own
pause inside a run, which the stats file records as `Pause Duration:`. The
rules below turn on the difference, so each word means one thing here.

### Run start and run length

Author-owned. The run record gains a start and a length, both optional. The
parser reads two more lines from a file it already reads.

- **The start** is the file's date with `Challenge Start:` as the time of
  day. It moves back a day when that lands after the end, which is a run
  that crossed midnight.
- **The length** is the end minus the start, minus `Pause Duration:` when
  the file has one.
- **The length is unknown outside 1 to 1,800 seconds, and the start with
  it.** A length out of that range means the start or the pause can't be
  trusted. The range covers:
  - the 46 negative lengths from 2021;
  - a reset-shaped file, whose start is within a second of its end;
  - a run across a clock change, which comes out an hour or a day off;
  - a start left over from another run, when it is far enough off.
- **It doesn't catch a start that is wrong by less.** The repeated start
  from 2025-07-13 leaves a length in range. That run's break comes out
  negative, which the session rule counts as no break.
- **The upper bound is the session limit.** It has to sit above any real
  run and under an hour, so that a run across a clock change is still
  caught. It also has to be no more than the session limit, for this
  reason: a start left over from an earlier run makes the break before the
  run read as nothing. With the bound at 30 minutes, such a start is
  trusted only when the real break was under 30 minutes, which would not
  have ended the session anyway. The spec states that as an invariant, so a
  later edit keeps it.
- **A run longer than 30 minutes loses its start and its length,** and its
  break is measured to its end. The longest run in the history is 238
  seconds, but a scenario sets its own timer and other players' runs may be
  far longer.
- **A file with no `Challenge Start:` has neither.** It still joins a
  session by its end.
- **A malformed value reads as a missing one.** It costs the start and the
  length, never the run, which is how the parser already treats its other
  optional fields.
- **The 2021 files with running-total pauses are not special-cased.** Where
  the subtraction leaves a length in range, it is too short, never too
  long.
- **Nothing is written to disk.** The run store is rebuilt from the stats
  folder at every start, so the two fields are read again each time.

Alternative rejected: trusting a start by the span from start to end, and
the length separately by the span minus the pause. It would keep the starts
of the 45 files from July 2021 whose pause is a running total. It adds a
second rule for two days of play five years ago.

### Sessions

S1. One pure function over the runs. It sorts them by end time itself, so
its answer never depends on the order a caller hands them over in.

- **The break between two runs** is the next run's start minus this run's
  end. When the next run has no start, it is the next run's end minus this
  run's end, which overstates the break by that run's length.
- **More than 30 minutes starts a new session.** A break of exactly 30
  minutes does not.
- **A negative break counts as no break.**
- **A session's start** is its first run's start, or that run's end when it
  has no start. Its end is its last run's end.
- **Session length** is the end minus the start, in progress or not. It
  includes the time between runs.
- **A session has no stored identity.** Where a view needs a key for one,
  it uses the session's first run.

How the missing start plays out on the history: 508 breaks are measured to
the next run's end, all before 2022. None of them is within a run's length
of 30 minutes, so the fallback moves no boundary. 37 of the 322 sessions
start at their first run's end, all from 2019 and 2020.

Alternatives rejected:

- **Measuring every break from end to end.** It needs no start, and it
  agrees with the rule above on all but 2 of 8,941 breaks. But a break is
  time not playing. Measured end to end, a long run counts as part of the
  break before it, and a session can be cut by the length of the run that
  resumed it. Both of the 2 are such cases.
- **One session per calendar day.** See
  [Sessions at 30 minutes](#sessions-at-30-minutes).
- **A session as one launch of the game.** It needs the game's own log,
  which is a new dependency, and the game was left open through breaks of
  up to 15 minutes on the logged days. Parked with the other ideas.
- **A threshold fitted to each player's own breaks.** The two published
  methods tried here disagree with each other and, for one of them, with
  itself between runs.
- **Counting a run's paused time as part of the break before it.** A run
  paused for an hour would then start a new session, and a session could
  read as ended for one run's playing time at most. But the run's start
  would then mean two things: when it began, for a session's length, and
  when its playing began, for the break. No pause since 2024 is longer than
  209 seconds, and the two rules agree on every session boundary in the
  history.

### In progress

S3. One pure function of the sessions and the current time. It returns the
session in progress, or none.

- **Only the newest session can be in progress.** That is the last one in
  the order the runs ended. It is in progress when the current time is no
  more than 30 minutes after its last run's end. No earlier session is,
  whatever its times.
- **The question is asked of the whole list, never of one session.** After
  a clock change two sessions can both pass the time test: one that ended
  minutes ago, and a later-sorted one whose runs carry times still in the
  future. Asked of the list, the answer is one session or none.
- **The time is an argument,** so the function is testable and holds no
  clock of its own.
- **The clock is the app's.** Run times are wall-clock times on the machine
  that wrote the stats files, and the app runs on that machine. A browser
  on another device may be in another time zone, so the state is never
  worked out from the browser's clock.
- **A last run in the future counts as in progress.** It can happen after a
  clock change.
- **A run that lands late reopens the session.** A run with a usable start
  inside the 30 minutes joins the session when it finishes, even after a
  long pause. A run paused for an hour reopens a session that has read as
  ended for most of that hour, and the next run can do it again. A run
  whose own playing time is over 30 minutes has no usable start, so it
  starts a new session instead.
- **The state changes with no event.** A view re-checks it on a timer. The
  page proposal owns that mechanism.

### Stretches of one scenario

Author-owned. One pure function over one session's runs.

- **A stretch is consecutive runs on one scenario.** Switching to another
  scenario ends it. Coming back later in the session starts a new one.
- **A scenario is its name,** as everywhere else in the app.
- **A change of sensitivity doesn't end a stretch.**
- **A stretch's start and end** follow the session's rule: its first run's
  start, or that run's end when it has no start, to its last run's end.

Version 1 of the page uses stretches for two things. One is the divider in
a scenario's run list where the scenario was left and returned to. The
other is the latest-run card's time on a scenario, which adds up that
scenario's stretches in the session. The All scenarios view draws one row
per stretch.

**The word.** The roadmap, the 2026-10-04 decision, and PR #351 call a
stretch a visit. The recommendation is that the code and the docs keep
"visit", and that the [Terms](#terms) block defines it.

- **It fits.** A player visits a scenario, leaves, and may visit it again.
- **It is already the word** in a ruled decision's text and in every note
  of this work.
- **It gets its glossary entry with the code that ships it.** That
  decision calls visit a working word, and says the proposal that ships it
  "names and defines it in its Terms block, and may rename it". The
  implementation ships the word in code and in the spec, so this is that
  proposal.
- **No version 1 screen shows it.** The divider is worded in runs and
  scenarios. All scenarios is the first piece that could put the word on
  screen. If it picks another word, its Terms block changes the entry and
  the code follows, as code names follow the glossary.
- **One cost.** The docs and the code's comments already use "visit" as
  plain English for one load of a page, dozens of times. So the code
  qualifies the name, `scenario_visit`, the way it qualifies
  `play_session`.

### Computed, never stored

Author-owned. Sessions and visits are derived from the run store when
something asks for them.

- **The old proposal's position holds:** no SQLite migration is needed.
- **The pass is cheap enough to repeat:** 3 to 6 ms over the whole history.
- **A view derives its sessions from the run store when it draws.** It
  never builds them up from the batches of new runs it was sent, because a
  batch can be missed.
- **The functions take a list of runs** and never read the store
  themselves. The store already keeps one list of every run in the order
  the runs ended, and that list is what a caller copies. The store is
  written by the watchdog thread and read without a lock, and a caller that
  hands over a copy keeps that out of the session code.
- **Changing the constant re-splits the whole history,** with nothing to
  migrate.

### Clock changes

Author-owned. Every time in a stats file is local wall-clock time, and the
rules above use it as written.

- **When the clock goes back,** an hour repeats. A real break can vanish,
  and runs from the two passes through that hour sort among each other.
  [It happened once](#a-clock-change-in-the-history) in seven years.
- **When the clock goes forward,** a break reads an hour longer than it
  was. A five-minute break across the change ends the session.
- **A manual clock change or a trip across time zones** does the same.

This is accepted, and the spec will say so. A time in the repeated hour
can't be placed without another clock. The file's modification time is
one, and it is what recovered the true order above. But copying or
restoring the stats folder rewrites it, so it can't be the rule. The cost
is a wrong session at most twice a year, for a player who is playing when
the clock changes.

### Terms

Each entry is written as [docs/glossary.md](../glossary.md) would hold it.
The implementation PR moves them in. The spec they point to is
`docs/specs/sessions.md`, which that PR creates.

Changed entry:

- **[Session](../glossary.md#session).** One stretch of play, including the
  breaks between runs, as [product.md](../product.md#when-they-ask-them)
  defines it. A break of more than 30 minutes between runs ends it, so a
  session can cross midnight and one day can hold several. It is in
  progress until 30 minutes have passed since its last run. How a break is
  measured is in the sessions spec.
  - Not an app session, which the specs use for one run of the server
    process.
  - In code: `play_session`, because `session` already names an HTTP
    session and an app session.

New entries:

- **Session length.** How long a session lasted, from the start of its
  first run to the end of its last. It includes the time between runs.
- **Run length.** How long a run took to play, with paused time left out.
  Some runs have none, because their stats files give no usable start.
- **Visit.** Consecutive runs on one scenario within a session, with no
  other scenario between them. Switching to another scenario ends the
  visit, and coming back later in the session starts a new one.
  - Not a visit to a page, which the docs also say in the everyday sense.
  - In code: `scenario_visit`.
  - Not on screen yet.

The agreed outline for this proposal listed three terms. Visit is a fourth,
added because the implementation ships the word.

### Copy

None. This design adds no user-facing string, so it has no Copy block.

### Carried from PR #351

PR #351 is a closed draft whose design is superseded. This proposal takes
three things from it.

- **Its Foundation section,** less the typical score, the readout's
  reference, and the marks. Marks go to the page proposal.
- **Its Evidence sections** Run length, Sessions, and Ingestion,
  re-measured on the snapshot above and corrected where the session-gap
  discussion found them wrong.
- **Its Testing list** for the pure functions and the parser.

The connector left four comments on it. None was answered there.

| Comment | Says | Where it went |
|---|---|---|
| [4191712535](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/351#discussion_r4191712535) | The rewrite left superseded decisions only in git history. | The three session positions are carried forward under [Decisions needed](#decisions-needed). The other two stay with the page proposal. |
| [4191712545](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/351#discussion_r4191712545) | A list that redraws only on a new run can read "in progress" indefinitely. | S3 sets the rule. The page proposal owns the timer. |
| [4191712540](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/351#discussion_r4191712540) | After a long break the typical score stays known from an old session. | The later typical score proposal (S4). |
| [4191712550](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/351#discussion_r4191712550) | Holding a run's comparison set fixed for its session is a product choice. | The later typical score proposal (S4). |

## Delivery plan

One implementation PR, with nothing on screen. This is intent, not a
contract: a boundary that moves is noted in that PR's description.

**What it builds:**

- run start and run length on the run record, read by the parser;
- sessions, the in-progress test, and visits, as pure functions in a module
  of their own that nothing calls yet;
- their tests.

**What it writes in the docs,** following Shipping a proposal:

- a decision-log entry for what a session is, which also records S4 and
  adds a dated note beside the sentence S4 moves, leaving that sentence in
  place;
- `docs/specs/sessions.md`, a new spec: the rules in Design, and that no
  screen shows them yet;
- the four glossary entries;
- one word in `docs/product.md`, whose definition of a session says "the
  pauses between runs". It becomes "breaks", so the glossary and the
  sentence it cites use the same word;
- "app session" in place of a bare "session" in the specs, where the line
  means one run of the server. On `main` today that is up to five lines of
  `docs/specs/playlists.md` and two of `docs/specs/notifications.md`. Each
  is judged by what it means: one of them describes a store kept per
  browser;
- the run record's two fields and the new module in
  `docs/architecture.md`;
- the roadmap's Upcoming entry, with this piece marked built. The milestone
  stays in Upcoming, and `docs/product.md` gains nothing, because no user
  sees a change;
- this file deleted.

**Unblocked:** S1 to S4 were ratified on 2026-10-11.

**Order:** it depends on nothing and can run beside the groundwork PRs. The
page's run list and its latest-run card wait for it.

**It cuts a release.** The PR changes `source/`, so merging it publishes a
version in which users see no difference.

**Recommended session:** `claude-opus-5-5` at high effort. The rules are
fixed here, and the work is a parser change, three pure functions, and
their tests.

## Out of scope

- **Everything on screen.** Session rows, the "in progress" state and its
  timer, the run number within a session, the divider, and the latest-run
  card belong to the Run History page proposal
  ([PR #356](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/356)),
  which rewrites [run_history_proposal.md](./run_history_proposal.md).
- **Marks on a run,** threshold passed and New PB. The page proposal.
- **The typical score.** S4: a later proposal of its own.
- **Warm-up runs,** in any form. The dip after a break grows gradually with
  the break's length and has no step at 30 minutes, so a rule tied to a
  session's start would miss most of it. Parked in
  `ignore/design-notes/session-gap.md` of the main checkout, under "Ideas
  for later".
- **Four ideas from the gap discussion,** parked in the same place: a
  divider for a long break inside a session, warm-up keyed on a break, "in
  progress" on its own shorter timer, and a session as one launch of the
  game. The maintainer, 2026-10-10: good ideas, probably not for the first
  release.
- **The gap as a setting.** S2. Nothing tracks it. A `config.toml` key
  could be added later without breaking anything.
- **Time in runs as a figure.** No version 1 screen shows it. Run length
  makes it a sum for the feature that wants it.
- **Reset files,** and the KovaaK's option that writes them. A file written
  on reset has a start within a second of its end, so this design gives it
  no run length, and still counts it as a run. Parked in
  `ignore/design-notes/stats-export-always.md` of the main checkout.
- **Stray CSV copies in the stats folder.** A kickoff is queued:
  `ignore/prompts/ignore-stray-stats-csvs-prompt.md` in the main checkout.
- **The four ingestion bugs** in
  [tech_debt.md](../tech_debt.md#bugs). A doubled run would count twice in
  a session, and a missed one not at all, until a restart rebuilds the
  store. Neither happened in ten weeks of logs.
- **The watchdog's per-run lines in the debug log.** They retire when the
  page goes public.

## Testing

- **Unit tests for the pure functions,** with the runs given as plain
  records:
  - a break of exactly 30 minutes, one second under, and one second over;
  - a session across midnight, and two sessions in one day;
  - a run with no start beside runs that have one;
  - a paused run begun inside the 30 minutes and finished long after them;
  - a negative break;
  - runs handed over out of order;
  - no runs, and one run;
  - in progress at exactly 30 minutes after the last run, one second
    later, and with a last run in the future;
  - two sessions that both pass the time test, where only the newest is in
    progress;
  - a return to a scenario later in the session;
  - a visit of one run;
  - a change of sensitivity inside a visit.
- **Parser tests** on small stats files:
  - a start after the end's time of day;
  - a pause, and a pause larger than the span;
  - a missing `Challenge Start:`, and a malformed one;
  - a missing `Pause Duration:`;
  - a start within a second of the end;
  - a 20-minute run, which keeps its start;
  - a span of an hour plus a run, which loses it.
- **The existing parser tests pass unchanged,** since both fields are
  optional.
- **The docs test** holds this file's sections and its links.
- **The scripts** reproduce every number in Evidence against the stats
  folder, with the cutoff set.
- **Nothing is checked in a browser,** because nothing is drawn.
