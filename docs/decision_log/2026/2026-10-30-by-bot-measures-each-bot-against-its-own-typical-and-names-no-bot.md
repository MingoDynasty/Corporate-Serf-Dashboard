# 2026-10-30: By Bot Measures Each Bot Against Its Own Typical And Names No Bot

Status: Accepted

A run whose kills name two bots or more shows a By Bot table, one row per
bot, each bot measured against its own typical. What the table shows follows
what the run's score is made of, from time per kill, to each bot's split, to
accuracy alone. Every column sorts, so the largest difference is a click
away. The table names no bot as the one the run lost the most on or the one
to practice.

**Ruling.** RV4 of
[proposal #450](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/450),
ratified by the maintainer on 2026-10-30 at `f80c109` ("Sounds good. I
ratify."), as amended in review: the review stated the kind rule and left a
run's unknown times empty. The maintainer's leans before that, 2026-10-29:
play order where it is fixed, rows that highlight on hover, the section above
Settings, This Run, Typical and Difference columns, every column sortable,
and no By Bot for a single bot. On 2026-10-30: no lead line naming the bot
this run lost the most on. Shipped in
[#456](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/456),
on the figures from
[#453](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/453).
What the page does today is in
[run_history.md](../../specs/run_history.md#by-bot).

**When it shows.** When the run's kill table names two bots or more. One bot
would repeat the tiles: VoxTS's kills equal its score, and its typical
accuracy would read 0.18 points off the tile's, because the kill table leaves
out shots fired after the last kill. A run with an empty kill table, such as
Raw Control or a Controlsphere, has none either. Either way a hidden
placeholder keeps By Bot's place, so Everything Recorded keeps its own
([its entry](2026-10-30-everything-recorded-shows-the-whole-stats-file-closed-and-grouped.md)).
Reach: 175 of the 866 scenarios the maintainer ever played name two bots or
more, and 14 of the 54 played in the last 90 days with 10 runs or more.

**The kind** (`ByBotKind` in `source/kovaaks/run_viewer.py`), and what it
shows after the bot's name:

- *Many kills per bot* when any bot has two kill rows or more, even if
  another has one: Kills, then Time per Kill, then Accuracy (EddieTS,
  Popcorn, Bounceshot).
- *Time-scored* when each bot is one kill and the run's own version has a
  pace basis the run is eligible for: Time, each bot's split, then Accuracy
  (Air, Ground Plaza Sparky).
- *Accuracy only* when each bot is one kill on any other run: Accuracy
  alone. That takes in a version known not to be time-scored, such as PGT's,
  whose bots are phases of about 20 seconds, and one the app can't tell
  about, such as any version played only before KovaaK's 3.9.0, which
  brought the performance files. In neither does the app know what a bot's
  time measures, so it shows none rather than one that may mean nothing.
- With typical runs each figure groups This Run, Typical and Difference
  under its name. With none, each figure is one column.

**Per bot.** Its kills; its accuracy, its kill rows' hits over their shots;
its time, the sum of its kills' gaps since the kill before, the first kill's
from Challenge Start; and its time per kill, that time over its kills. A
kill's time is that gap, not its TTK column, since a one-shot kill records a
TTK of 0, so it includes finding the bot. Each typical is the median over the
typical runs that name the bot and have the figure, and a bot no typical run
names has empty Typical and Difference cells. Names are taken as they come:
FlyTS's Fly Bot and Fly Bot 2 get a row each.

**When the times are known.** A gap is taken between two times of day. One
more than 12 hours below zero crossed midnight and gains a day; any other
gap below zero means the file's times disagree. A run's times are unknown
when its file has no usable `Challenge Start:`, when a gap disagrees, or when
it was paused (`Pause Duration:` above zero or unreadable), since the file
gives the paused time but not which gap it fell in. Such a run keeps its
kills and accuracy, its time cells are empty, its typical's included, and a
line under the subtitle says why. Accuracy alone shows no time, so it has no
such line. A typical run with unknown times counts toward each bot's typical
accuracy and not toward its times.

**How it reads.** Times in seconds to two decimals (`1.11 s`), accuracy as
the app shows a run's accuracy (`59.26%`). A difference is worked from the
two values as shown, signed as the tiles sign theirs, in ` s` or ` pts`. A
faster time or a higher accuracy is green, the reverse red, and zero dimmed.
A Typical cell's hover counts the runs it took, as a tile's does. The
subtitle is the kind's line, then `Listed in the order the run plays them.`
where each bot is one kill, then the typical runs' line when there are
typical runs.

**Order and sorting.**

- Rows start in play order where each bot is one kill, since Air and PGT
  play their bots in the same order on every run, and in name order
  otherwise, since Popcorn's come at random (51 orders in 55 runs). Name
  order reads numbers as numbers, so `Fly Bot 2` comes before `Fly Bot 10`.
- Each header sorts ascending, then descending, then back to the default
  order, on a click or on Enter while it has focus, and the sorted header
  carries `aria-sort`. An empty cell goes last both ways, and rows that tie
  keep their default order. A row under the pointer is marked.
- A sort holds for its run only: every run, the one switched to included,
  starts in its default order. The v12 mockup kept a sort through a switch;
  the ruling says the rows start in their order.
- The table is an AG Grid, as the playlist tables are, in print layout so it
  is as wide as its columns, each sized to its contents with room for the
  sort arrow. Sorting never leaves the browser.

**Rejected.**

- A lead line naming the bot this run lost the most on, with its row tinted
  (v7 to v12). No ranking says where the score went: the largest difference
  per kill puts one kill half a second slow above twenty kills a tenth of a
  second slow, though the second cost 2 seconds, and weighting by kills
  doesn't settle it, since a kill's gap also holds the travel since the kill
  before. The sort finds the largest difference.
- A verdict on which bot to practice (shelved as S3). Over the newest 20 runs
  redrawn 300 times, the slowest typical bot is the same in 80% of redraws or
  more on 7 of the 14 scenarios, but it is often slow by design: Air Pure's
  UFO bot is slowest in every redraw. The measure that corrects for design,
  a bot's typical against its best quarter of runs, reaches 80% on none. Per
  bot history (S4) has the same noise.
- One table shape for every scenario, which would show Kills of 1 and a time
  per kill that never changes on PGT and Air; a phases subtitle where a
  version is known not to be time-scored, which the app tells apart only
  internally; a scenario-level per-bot view, on a page 80% of scenarios
  don't need it on; and a kill-time chart (S5), since By Bot holds the
  splits.

**Supersedes in part** the
[2026-10-05 pace entry](2026-10-05-time-scored-scenarios-are-measured-by-pace.md),
which kept a per-bot breakdown out of its scope and says no completion time
is shown anywhere: a time-scored run's By Bot shows each bot's split. The
roadmap's Future item "Per-bot breakdown on time-scored kill scenarios"
ships here, for every scenario that names two bots or more.

**Provenance.** Proposal by `claude-opus-5-5` (#450), read by `gpt-6-astra`
(flagship, first wave) and reviewed by `gpt-6.1-sol` (the seat) and
`claude-fable-5-1`. Built by `claude-opus-5-5` in #453 and #456.
