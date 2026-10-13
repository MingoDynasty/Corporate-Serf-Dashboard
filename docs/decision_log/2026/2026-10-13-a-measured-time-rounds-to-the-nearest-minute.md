# 2026-10-13: A Measured Time Rounds To The Nearest Minute

Status: Accepted

Run History shows two measured lengths of time, a session's length and the
time spent on a scenario, and both now round to the nearest minute. They used
to count only the whole minutes gone by, so a single 60-second run read as
under a minute. The app measures such a run at just under 60 seconds, because
a run's start is recorded more finely than its end.

**Ruling.** By the maintainer, 2026-10-13, after a lone 60-second run read
`<1 min` in their look at
[PR #372](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/372):
"I think I would prefer rounding to the nearest minute." Then, on where it
lands: "land it in PR 4". One part below is a lean and not a ruling, and is
marked. The rule as the app applies it is in
[run_history.md](../../specs/run_history.md#the-latest-run-card).

**The rule.** A measured time is rounded to the nearest minute, and a half
rounds up. The form is unchanged: `9 min`, `1 hr 6 min`. It covers the two
places a measured time shows: the first row's session length in the run
list, and the latest-run card's time on a scenario. One formatter serves
both.

**Why a 60-second run measured 59.9 seconds.** A run's start is written to
the millisecond, in its stats file. Its end is the whole second in the stats
file's name. So a run of exactly 60 seconds measures a little under 60.
Counted in whole minutes gone by, that is no minutes, and one such run alone
in its visit read `<1 min on this scenario` on the maintainer's own data. A
session of one such run read the same way in the list.

**What it replaces, and what it keeps.** PR #371 had a measured time count
the whole minutes gone by, as a deviation from the proposal's letter, and
PR #372 followed it for the card. That choice was made against the app's
other duration formatter, which rounds up to the next minute because it
words an estimate. A measured session from 9:45 PM to 10:51:01 PM would have
read `1 hr 7 min` there. Rounding to the nearest minute keeps what the
deviation was for: a measurement is not rounded up as an estimate is, and
that session of 1 hr 6 min 1 s still reads `1 hr 6 min`.

**A time that rounds to zero reads `<1 min`. This part is a lean, not a
ruling.** It is the maintainer's lean and the author's. The maintainer:
"maybe this is an edge case where "<1 min" actually makes the most sense".
Under this rule `<1 min` means under 30 seconds. The alternatives:

- **`0 min`** would read as nothing played.
- **`1 min`** would say four times what a 15-second run took.

**Unchanged.** Where the time on a scenario can't be known, the card still
says so and shows no number.

Ruled on PR #372 and shipped in
[#373](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/373).
The duration form comes from the Run History page proposal
([PR #356](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/356),
merged as `a65f72d`). Its file, `docs/proposals/run_history_proposal.md`, is
deleted, and git history keeps it.
