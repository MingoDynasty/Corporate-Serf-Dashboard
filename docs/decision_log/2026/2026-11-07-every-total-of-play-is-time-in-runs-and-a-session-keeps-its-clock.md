# 2026-11-07: Every Total Of Play Is Time In Runs, And A Session Keeps Its Clock

Status: Proposed

Every total of play the app shows now adds up the runs' own lengths, called
time in runs, so it leaves out restarts, menus and the breaks between runs.
A session's length stays its clock, breaks included, and is the only length
of play that counts them. Scenario Stats' run count becomes a time in runs,
and the latest-run card's time on a scenario becomes that scenario's time in
runs in the session. A total that holds a run with no recorded length reads
`at least`, never rounded up, or `unknown`.

**Ruling.** None yet. Rows DT1 to DT6 of
[proposal #473](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/473),
built at `24fe398` ahead of ratification, at the maintainer's request on
2026-11-07. DT1, DT2, DT4 and DT6 were unanimous there. DT3 is built as
amended after the first review wave, awaiting the seat's confirmation, and
DT5 as recommended, contested; the maintainer's questions 1 and 2 on them
were open. Their leans on file, of 2026-10-14: count only the runs for a
scenario's total, "since a scenario's total is about that scenario, not
downtime"; keep downtime "belonging to the session as a whole"; "fold into a
time-played figure, with the run count on hover"; and runs only "for the
session line too". The rules as the app applies them are in
[sessions.md](../../specs/sessions.md#time-in-runs) and
[run_history.md](../../specs/run_history.md#scenario-stats).

**DT1, every total of play is time in runs.** A total over any set of runs,
a scenario's, a session's, a day's or all of them, is the sum of their run
lengths: each run's end minus its start minus its paused time. One function
adds it up (`time_in_runs` in `source/kovaaks/play_sessions.py`) and one
display rule shows it (`format_time_in_runs` in
`source/utilities/utilities.py`); every surface that shows a total uses both.
The seconds are summed before rounding, so the parts of a set of runs add up
to the whole. A run belongs to one day or hour only by a rule, such as the
date and hour it ended, which the first calendar proposal sets: 13 of the
maintainer's 9,284 runs cross midnight. Rejected: runs plus the gaps between
them up to 2 minutes (1.46 times A in 2026, a second constant and a hover to
explain it), and visit spans (1.61 times A, and every break under 30 minutes
inside a visit counted). On the maintainer's runs the total reads about half
of a session's clock (49% on 2026 sessions of 5 runs or more) and about a
third of the time the game was open.

**Freeplay files.** A stats file named without ` - Challenge - ` is
freeplay, which Statistics Export on Always writes, with a `Challenge Start:`
left over from the last challenge played. It gets no start and no length, as
a file with no `Challenge Start:` does. It still loads and counts, adds no
time, makes its total a minimum, and joins its session by its end, so its
left-over start can't move a session boundary. The two archived freeplay
files of the 2026-10-10 Statistics Export test had read 24.6 and 35.6
seconds from that left-over start. Rejected: leaving such files out of the
total only, which is a second rule beside the run's own and leaves the
session split exposed.

**DT2, a session keeps its clock.** A session's length is its first run's
start to its last run's end, pauses and breaks between runs included, as
before. It is the only length of play the app shows that counts those
breaks, and the first row's hover says so. No session row shows a time in
runs: "how long was that sitting?" would read 33 minutes for a sitting of
1 hr 13 min (2026-10-27). Runs filled a median 50% of the clock on sessions
of 5 runs or more since 2026-09-13.

**DT3, the card's session line.** The line keeps the run's number in its
session and adds its scenario's time in runs over every visit there:
`Run 7 this session · 7 min in runs`. The visit sum, its
`Time on this scenario unknown` form and the rule for a visit with no usable
start are gone. The minutes repeat the run number in 92% of the card's 2026
readings and say more on longer scenarios: Air CELESTIAL No UFO Medium's 4
runs read 8 minutes on 2026-09-26, and nothing else shows this scenario's
time in this session. Set aside: dropping the time, `Run 7 this session`,
which the second full reviewer endorsed on the premise that the player paces
by run number; the minutes in the line's hover; and the visit spans, which
ran 5 minutes or more over the runs in 16% of 2026 readings.

**DT4, Scenario Stats' Time in runs.** `Total runs: 147` becomes
`Time in runs: 2 hr 26 min`, lifetime, over every run Total runs counted, and
the count moves to the first line of its hover. A 30-day window was set
aside: a second meaning on one card, whose typical score already dates its
runs. With no local runs the line is absent and the lead's `No runs yet`
stands alone.

**DT5, a time in runs names what it counts.** Every time in runs reads
`{duration} in runs`, or `Time in runs: {duration}` as a labelled line.
`at least` goes in front only when a counted run has no length, and then it
never rounds up. Every figure's hover says what runs leave out. The name
carries D2's minimum label, so a figure with every length known shows no
visible minimum word. Set aside: `at least` on every figure, which can't
round up, so the card would read a minute under its own run number in 97% of
its 2026 readings; and D2's sentence,
`Recorded time in runs is a minimum of time played.`, as a visible line on
Scenario Stats and on the card. A later surface whose subject is time, such
as a calendar or a week readout, carries that sentence.

**The display rule.** From a total's seconds and its count of runs with no
length, in one of four forms:

| # | The runs | Reads |
|---|---|---|
| 1 | none | nothing: the figure is absent |
| 2 | every one with a length | the nearest minute, `<1 min` under 30 seconds |
| 3 | some with no length, a minute or more recorded | `at least` and the whole minutes recorded |
| 4 | some with no length, under a minute recorded | unknown |

Form 2 is the [2026-10-13 rule](2026-10-13-a-measured-time-rounds-to-the-nearest-minute.md).
A minimum never rounds up: 90 recorded seconds beside a reset read
`at least 1 min`. Unknown is never a small time: a measured total under 30
seconds reads `<1 min`. On the maintainer's runs, 509 of 9,284 have no length,
all from 2019 to 2021, so `at least` shows on 29 of 866 scenarios and
unknown on 56 more.

**DT6, time comes from the stats folder alone.** The app reads no game log,
no Steam log and no watcher of the game window or input. KovaaK's 3.9.12 no
longer writes the analytics log that timed restarts on 3.9.10
([the research note](../../research/kovaaks_analytics_log_restarts.md)), and
Steam's own log of launches is undocumented, local time, and as deep as Steam
keeps it. From 2026-05-10 to 2026-10-30, 133 launches held 25.9 h in runs,
42.9 h of visit spans and 54.3 h of session clocks while the game was open
75.6 h. D2's minimum covers the gap.

**Copy.**

- Scenario Stats: `Time in runs: ` in bold, then `{duration}`,
  `at least {duration}` or `unknown`. Its hover opens with `{n} runs`,
  `{n} runs · {k} with no recorded length` or
  `{n} runs · none with a recorded length`, singular `1 run`; then
  `Only the runs themselves count, not their pauses. Restarts, results screens and breaks between runs don't either.`
  An `at least` figure adds
  `Runs with no recorded length add no time, so this is a minimum.`, and an
  unknown one with some lengths adds
  `The runs with a recorded length come to under a minute.`
- The card's session line: the run's words, unchanged, then
  ` · {duration} in runs`, ` · at least {duration} in runs` or
  ` · Time in runs unknown`.
- The first session row's length hover:
  `The length runs from the first run to the last run, pauses and breaks between runs included. It doesn't count the time since your last run.`
- Retired: ` · {duration} on this scenario`, `Time on this scenario unknown`,
  `Total runs: `, and the old length hover.

**Not checked.** Another player's run lengths, where time in runs moves
further from the run count; the restart share on 3.9.12, which nothing
records; NVDA on the new hover.
