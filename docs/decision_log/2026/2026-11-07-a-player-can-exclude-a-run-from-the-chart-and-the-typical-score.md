# 2026-11-07: A Player Can Exclude A Run From The Chart And The Typical Score

Status: Proposed

A player can exclude a run from the run viewer, and it then leaves the Run
History chart and the typical score. It stays in the run list, dimmed and
marked, and the PB, the stars and the leaderboard still count it. The choice
is the player's own, for a test run, an experiment or a run left halfway, and
it is kept in a file of its own under the app's data folder. This entry
records a working build for the maintainer to look at, not a ruling.

**Where it comes from.** The maintainer's discussion of
[#469](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/469) on
2026-11-06: a player may want to hide a run for a reason a date can't find,
such as a test run, an experimental run or a run where they went AFK, and
"Just hiding those runs once is fine. No need for date range." Hiding is
meant to be rare. A Fable consult (`claude-fable-5-1`) weighed three
meanings of hidden: chart only (A), chart and typical score (B), and chart,
typical score, PB and stars (C). It recommended B. On 2026-11-07 the
maintainer asked for B to be built as a working pull request to look at;
which meaning is right is still theirs to rule. Built in the pull request
that adds this entry.

**The rule.**

- The run viewer's header has **Exclude run** beside **Close**. It asks
  first, in the browser's confirm box: `Exclude this run? It leaves the chart
  and your typical score. Your PB and the leaderboard still count it.` On an
  excluded run the button reads **Include run**, which asks nothing, and a
  line under the header says `Excluded. This run doesn't count on the chart
  or in your typical score.`
- An excluded run is not drawn in any chart mode, and is never a score in a
  typical score's window, so it leaves the chart's line and bands, the
  Scenario Stats lead, the playlist scenario table's typical columns, and
  the session-start value the latest-run card and the run viewer measure
  against. It still joins the runs either side of it into one play session.
- It still counts in a range's count of runs and in the run numbers, so
  Score vs Run leaves its place on the axis empty. The PB, the stars, the
  PB card, Total runs and the leaderboard position all still count it; a
  new PB that is excluded gets no star drawn and still decides which later
  runs are new PBs.
- The run list keeps every run. An excluded row's cells are dimmed, and its
  marks cell says `Excluded. It doesn't count on the chart or in your
  typical score.` on hover and to a screen reader.
- A range whose runs are all excluded shows `Every run in this range is
  excluded` / `Choose a longer range, or open a run from the list to include
  it again.` A scenario whose runs are all excluded has no typical score:
  the lead reads `Too few runs` with the hover `Every run of this scenario is
  excluded.`, and the playlist table has no value for it.
- A press writes the store, then the page's exclusions store, which redraws
  the chart, the run list, the latest-run card and Scenario Stats. The chart
  behind the viewer is rebuilt, so it forgets its zoom.

**The store.** `data/excluded_runs.json`, one file for every scenario, born
stamped:
`{"schema_version": 1, "excluded_runs": [{"run": <stats file name>, "excluded_at": <UTC time>}]}`.
The key sets are fixed and a run listed twice is an error. It runs through
the shared four-state machine: missing excludes nothing; error and future
read as no excluded run, so every run counts, and the run viewer's line
shows the machine's message; a file from a newer build refuses every press,
and a broken one is copied aside before the next write. It is read whenever
asked and never cached. A run is named by its stats file's name, the run's
id, which survives a rescan of the stats folder.

**Why B.**

- The maintainer's cases are runs that aren't the player's current form,
  and the typical score is the app's form number. Under A an AFK run would
  leave the chart and still feed the value the next run is measured
  against.
- A does not fix the old runs the maintainer would hide once. The bands
  count the hidden runs and hold the axis: on Ground Plaza Sparky V3 the
  axis would stay at 48 points under A and drop to about 23 under B, on the
  2026-11-06 check of the date-range note.
- C would let the PB card disagree with the player's position: the PB is
  what the leaderboard ranks, and the leaderboard keeps every run. A run
  excluded for being bad is never the PB anyway.
- The data folder, not the browser: the server works out the typical score
  for every browser, the playlist table included, and a rare action must
  survive a cleared browser.

**Not chosen.** The date range of #469. A bulk action: hiding is rare.
Detecting an AFK run on its own: a run is excluded only by the player. A
control on the chart's hover or on every row.

**Costs.**

- The typical score now depends on a file the player writes, so it can no
  longer be rebuilt from the stats folder alone, and losing the file brings
  every run back.
- Excluding many runs on a small scenario can leave its typical score
  unknown: it needs 10 counted runs again.
- Numbers already on screen change after a press: the typical score
  everywhere, the latest-run card's measure, and the playlist table's ranks
  by typical score.

**Open before a ruling.**

- The word: Exclude, since the numbers change, or Hide.
- A reason for each exclusion, such as "AFK", is not in version 1. Every
  store shares one schema version, so adding one later means a key every
  build would accept from now, or a version change across the stores.
- Whether the latest-run card should say its run is excluded. Today it
  shows the run as before.

**What this changes in older entries.** The
[typical score's definition](2026-10-15-typical-score-uses-the-last-twenty-runs-and-counts-every-version.md)
said every sensitivity, warm-up run and version counts: an excluded run
doesn't. The
[every-run chart](2026-10-12-the-run-history-chart-plots-every-run-and-draws-no-summary-line.md)
plotted every run in its range: an excluded one isn't drawn. Each carries a
dated note.
