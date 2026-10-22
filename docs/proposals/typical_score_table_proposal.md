# Typical Score On The Scenario Table

Status: Proposed
Date: 2026-10-22

## TL;DR

The playlist scenario table judges every scenario by its personal best, so a
single lucky run decides its rank, and the table can't show where a player
is weak. This proposal adds two columns beside the PB ones: the typical
score, the median of the scenario's last 20 runs, and the rank it reaches
with how far it sits toward the next one, such as Celadon · 7%. Sorting that
rank column lists the scenarios from weakest to strongest by the player's
usual play, while the PB columns beside it keep the record. An old typical
score is marked with a clock and stays readable, and each value's hover
explains it, from the mouse or the keyboard.

## Decisions needed

Four rulings: TB1 to TB4. The maintainer ratified this proposal on
2026-10-22: "I ratify the proposal." That settles each row as its
recommendation, TB2 and TB4 as amended in review. Before that, each row was
the maintainer's lean from the design discussion of 2026-10-21 and
2026-10-22, worked out on five versions of a live prototype built from their
own stats, with two rounds of advice from `claude-fable-5-1` before review
and a third, on TB4, during it. Each row keeps what was said, for the record.
Everything else is author-owned, in [Design](#design), and the ratification
covers it too. TB4's recommendation departs from the maintainer's first
lean, and its status line says how.

### TB1. Two typical columns beside the PB columns

Status: Ratified (user), 2026-10-22: accept the recommendation below. The
maintainer's lean before that, 2026-10-22, after comparing this
layout with a PB / Typical switch on the prototype: "two columns, Typical
Rank as Celadon · 7% sorted by rank position with the gap in its hover, no
Typical Next Rank column."

The material consequence: a benchmark's table gains two columns, and is
wider by about 320 px.

**Recommendation: add Typical Score and Typical Rank after Next Rank on a
benchmark's table, and Typical Score after PB Score on a playlist's. Both
are shown by default and listed in the Columns menu. Every existing column
keeps what it reports.**

- **The comparison is per row.** PB Rank beside Typical Rank shows at a
  glance where a lucky run flatters a scenario: Whisphere Viscose is
  Cerulean by its PB and Celadon by its typical score, while Celadon beside
  Celadon means the scenario plays at its rank.
- **It fits the maintainer's window.** At 2560 px both columns fit with no
  sideways scroll; the Scenario column narrows from 400 to 333 px, and no
  scenario name is cut on Viscose Benchmark S2 Medium. At 1920
  px the table already scrolls today, and the Columns menu hides what a
  player never reads.
- **Each typical value has a hover,** the one Scenario Stats gives its lead
  number: the runs behind it, how many are recent, and both middle bands.
  The maintainer asked for it on 2026-10-21.
- **Nothing is amended.** Rank, Next Rank, Position and Percentile keep
  reporting the PB, as the 2026-10-04 principles say, and links that carry a
  sort keep meaning the same sort.

Rejected, with the record in [Alternatives rejected](#alternatives-rejected):
a switch that changed PB Score, Rank and Next Rank in place (the
maintainer's first lean), and a third column for the typical Next Rank gap.

### TB2. Typical Rank sorts by rank position and reads `Celadon · 7%`

Status: Ratified (user), 2026-10-22: accept the recommendation below, as
amended in review. Before that, the maintainer, 2026-10-22, on what the
table is for: the
typical Next Rank "essentially allows me to 'Sort by weakness'. Since Score
is not really comparable across scenarios", and the alternative, "convert
the Rank and Next Rank into numerical steps": Bronze is 2.0, and 40% of the
way to Silver is 2.4. On the format, after trying three on the prototype:
"I'm leaning toward 'Celadon 7%' option, simply because it is more user
friendly."

The material consequence: the weakness order is the benchmark's own ranks,
each split by how far the typical score sits toward the next one, not the
gap to the next rank.

**Recommendation: Typical Rank sorts by its rank position, the number of
ranks the typical score has reached plus the fraction of the way to the
next one. The cell shows the rank's name and that fraction as a whole
percent, `Celadon · 7%`, rounded down and never above 99%. The gap to the
next rank goes in the cell's hover, `+10.3% to Viridian · 45 to go`.**

- **The gap sorts against weakness inside a rank.** A scenario that has just
  reached a rank is the farthest from the next one, so sorting by the gap
  puts the weakest scenarios of each rank last. On Viscose Benchmark S2
  Medium the 19 Celadon scenarios order almost exactly opposite by gap and by
  position (Kendall tau −0.88). CatClick Medium, 7% into Celadon, is last of
  31 by gap. Ground Plaza Sparky V3, the weakest scenario on the table
  (Saffron · 34%), is 22nd. Over the 31 ranks holding three or more
  scenarios across 23 of the maintainer's benchmarks, the mean is −0.68
  (`claude-fable-5-1`'s count; the Viscose figures were reproduced
  independently).
- **The position is the benchmark's own scale.** A benchmark's ranks are
  meant to mark the same level on every one of its scenarios, which a score
  cannot. How evenly a given benchmark's thresholds achieve that is
  [not checked](#not-checked). A scenario sitting exactly on its rank's
  threshold reads `Viridian · 0%` whatever its score scale; by gap it would
  rank by how wide its score bands happen to be.
- **The name, not the ordinal.** `Celadon 4.07` and `4.07` sort the same, but
  a player knows rank names, and the ordinal shifts between ladders: Celadon
  is fourth of nine on Viscose, while a four-rank ladder ends at 4.
- **Below the first rank** there is no lower threshold. The cell reads
  `No rank`, with no number, and sorts by how far the typical score falls
  short of the first rank, measured as the Next Rank gap measures it: the
  score over the first threshold, or, on a time-scored scenario where pace
  applies, the first rank's time over the typical time. A ratio of scores
  would move with a time-scored scenario's arbitrary starting constant; a
  ratio of times doesn't. A displayed number would have to rest on an
  invented floor. This is common on harder benchmarks: 6 of the 7 known
  typical scores on Aimspeed Benchmark 2 Normal.
- **At the top rank** the cell reads the rank's name alone, and sorts last
  ascending.

The 2026-09-27 decision set this fraction aside for the Next Rank column,
whose question is the score to beat. This row uses it for an order, which
that decision did not weigh.

### TB3. Every known typical score gets a rank, old or not

Status: Ratified (user), 2026-10-22: accept the recommendation below. The
maintainer's lean before that, 2026-10-21: "2: I agree."

The material consequence: a typical score with few recent runs behind it
still gets a Typical Rank and sorts among the others.

**Recommendation: a known typical score gets its Typical Rank whether or not
it is recent, and sorts with the known values. A known value that is not
recent is marked Not recent in both typical cells (TB4). A typical score
below the minimum is never marked: unknown is not the same as old. It reads
`Too few runs`, and its row sorts after every known value in both
directions.**

- **The 2026-10-04 principles ask for this choice to be made.** Their
  2026-10-21 note says defining the typical score "does not authorize a later
  judgment to use a dimmed value without choosing its evidence bar". This row
  is that choice.
- **Old is not unknown.** Scenario Stats already shows an old value, dimmed,
  rather than hiding it: the 2026-10-18 entry kept old values because hiding
  one "would discard useful information about past play". A rank read from
  one is the same figure placed on the ladder.
- **Setting old values aside would empty the column for most benchmarks.**
  On IRON PIPE AIM PLAYLIST #2, 6 of the 9 scenarios with a typical score are
  not recent; treated as unknown, they would join the 25 played scenarios
  that already read Too few runs.
- **Unknown is never weak,** per the same principles. Too few runs rows are
  never ranked among the known ones, so they sort last whichever way the
  column sorts, as `N/A` already does.
- **Admitting an old value rests on its qualification reaching every
  reader.** So the mark is visible without the grey, read aloud by a screen
  reader, and explained from the keyboard (TB4,
  [The hovers](#the-hovers)).

### TB4. Old values are marked Not recent, in a grey that stays readable

Status: Ratified (user), 2026-10-22: accept the recommendation below, as
amended in review. The maintainer's first lean, 2026-10-22, after comparing
two greys on the prototype: the darker one
"doesn't seem faded enough, and looks too similar to regular text. The
'Card's grey' option, however, is faded enough to see a difference." This
recommendation departs from that lean. It keeps the darker grey and adds a
mark, so the difference no longer rests on the grey; the prototype's panel
switches between the two. A key line beside the status line, in the first
amendment, is gone: the maintainer, 2026-10-22, "I push back on this because
it doesn't lead to good UI/UX", and chose the prototype's version that
explains the clock in the hovers instead.

The material consequence: an old value carries a small clock, its hover says
why, and the numbers stay at 4.5:1 or more. Choosing the card's grey instead
leaves the old figures under 4.5:1, with the difference in color alone.

**Recommendation: show a known typical score that is not recent in a muted
grey that clears 4.5:1 on every row, with a clock after the value in both
typical cells. Each old cell's hover says why it is marked, counting the
runs behind the value. A screen reader hears `Not recent` after the
value.**

- **These are the figures the table is for.** The typical cells are what the
  player compares to find weakness, and TB3 admits old values on the
  condition that they are qualified. In the card's grey they measure 3.32:1
  light and 4.04:1 dark on the plain row, 3.15:1 and 3.53:1 on the
  alternating one, under the 4.5:1 WCAG AA asks of text this size. And the
  difference is color alone, which a reader who can't tell the grey, or
  doesn't see the table, misses.
- **The card's precedent doesn't carry over.** Scenario Stats dims a 30 px,
  weight-600 lead, held to 3:1 for large text, and its first line states the
  recent count in words. The playlist code and the status line, which use the
  same grey, are not figures anyone compares.
- **The darker grey alone read too close to normal text,** worst in the dark
  theme, where normal text is `#c9c9c9`. The clock carries the difference
  instead. On the prototype, `#676d75` light and `#a6a6a6` dark measure
  5.22:1, 4.95:1 and 4.7:1 on the plain, alternating and hovered rows in the
  light theme, and 6.38:1, 5.58:1 and 4.6:1 in the dark.
- **It costs no width.** Both typical columns are as wide as their headers,
  so the clock widens neither, and the table's overflow is unchanged at every
  width measured.
- **The explanation sits where the clock is.** The whole cell opens its
  hover, by mouse or keyboard, so the clock needs no target of its own; a
  tooltip on the 13 px clock alone would be hard to hit, would fight the
  cell's hover, and couldn't take keyboard focus inside the grid. A key line
  for one mark would be clutter that comes and goes with the data.

## Problem

### What the table shows today

A benchmark's scenario table shows PB Score, then Rank and Next Rank, all
from the PB: the local all-time high
([playlists.md](../specs/playlists.md#the-per-playlist-scenario-table)).
Sorting Next Rank ascending lists the scenarios closest to ranking up. A
plain playlist's table has PB Score and no rank columns.

The typical score shipped on 2026-10-21 (#398, #400, #402, #401), on Run
History only: the Scenario Stats card leads with it, and the chart draws it
with two bands. The table never shows it
([typical_score.md](../specs/typical_score.md#api-and-snapshot-ownership)).

### Why the table

The roadmap's guiding principles say judgments about skill, where a player
is weak and where their level stands, move toward the typical run, because
one lucky run makes a scenario look stronger than it usually plays. The
scenario table is where the player compares scenarios and picks the next one
to play, and today it can only compare personal bests. Scores can't be
compared across scenarios, and nothing on the table orders them by weakness.

### The evidence, from the maintainer's history

Measured 2026-10-21 and 2026-10-22 on 9,212 runs over 866 scenarios, with
the shipped definition (226 scenarios have a known typical score, 26 of them
recent):

- **Viscose Benchmark S2 Medium,** the benchmark the maintainer plays most
  (1,119 runs in 90 days): all 39 scenarios played, 31 with a typical score,
  26 of them recent, 5 not recent, 8 Too few runs.
- **The typical score places lower than the PB on 30 of those 31:** one rank
  lower on 15, two on 13, three on 2.
- **19 of the 31 sit in one rank, Celadon.** A rank sort without the
  fraction would leave them in playlist order.
- **The weakness order by rank position** starts Ground Plaza Sparky V3
  (Saffron · 34%), Pasu Voltaic Reload Easy (Saffron · 81%), CatClick Medium
  (Celadon · 7%), VoxTS Click Medium (Celadon · 28%).
- **Lightly played benchmarks have few typical scores.** IRON PIPE AIM
  PLAYLIST #2: 9 of 34 played scenarios. FN Prospects Benchmarks 2026: 1 of
  11. The columns there read mostly Too few runs, which is honest.

These are one player's numbers, and they show what the columns would
display, not that they improve training.

### Verified facts

- `ladder_standing` in `source/kovaaks/playlist_scenarios_service.py` takes
  any score, so the typical score walks the same ladder with the same pace
  rule, and the walk's last passed and next threshold bound the fraction.
- Building every row's newest typical value for a 39-scenario benchmark
  costs about 35 ms to split the whole store into sessions and 69 ms to build
  the values, measured in-process on the maintainer's store.
- Widths, headless Edge at 1300 px tall with the navigation open, prototype
  at the maintainer's data, 2026-10-22: the two columns fit at 2560 px, where
  the Scenario column narrows from 400 to 333 px; a third, the typical Next
  Rank, would scroll the table by 152 px there. With the two, the table
  scrolls by 587 px at 1920 and 971 px at 1536. The Not recent clock changes
  none of these.
- AG Grid's `tooltipTrigger` is one grid-wide option with two values, and
  each wires its own listeners: `hover` the mouse's, `focus` the focus's
  instead. Setting `focus` would end every mouse hover in the table
  (dash-ag-grid 35.3.0's bundle).
- On the prototype, the Chromium accessibility tree names an old Typical
  Score cell `873.11, Not recent` with its hover's text as the description,
  a recent one by its value alone, and a Too few runs cell by those words
  with the below-minimum text. Arrowing onto a typical cell opens its hover;
  Escape closes it; the mouse hover still opens as before.
- In dash-ag-grid's `{"function": ...}` strings, `Boolean(...)` silently
  fails, as `dagfuncs.` does: the scope holds the registered functions,
  `params` and a few named libraries, not the browser's globals (found on the
  prototype).
- A custom tooltip component needs the `ag-tooltip` class for the app's
  tooltip styles to reach it, and an explicit width, or the grid's popup
  shrinks it to its narrowest (prototype).

### Not checked

- **Whether a benchmark's ranks mark the same level on all its scenarios.**
  TB2's weakness order assumes they do, as ranks are meant to. A scenario
  whose thresholds sit harder or easier than the others' would sort weaker or
  stronger than it plays. Nothing here measures how even a benchmark's
  thresholds are.
- **Firefox.** The maintainer looked at the prototype in Firefox; the
  measurements above are headless Edge.
- **What a screen reader says.** The accessibility tree reads as specified
  on the prototype; no screen reader has spoken the table yet.

## Design

### What the player sees

| Column | Shows | Sorts by |
|---|---|---|
| Typical Score | the newest typical score, rounded as Scenario Stats rounds it | the unrounded median |
| Typical Rank | the rank it reaches and how far toward the next, `Celadon · 7%` | rank position |

On a benchmark's table both follow Next Rank, so the three PB columns stay
together and the typical pair reads after them. A playlist's table has no
ranks, so it gains Typical Score alone, after PB Score.

The typical columns are computed as the page opens and, like PB Score, do
not change when a run lands until the page reopens. Neither does whether a
value is marked Not recent, nor what its hover counts. Run History's card, which
updates every 30 seconds, can disagree with a table left open for a long
time.

### The cells

- **Typical Score:** the value from `format_typical_score`. Below the
  existence minimum, `Too few runs`. With no local runs, `N/A`, as PB Score
  reads.
- **Typical Rank:** `{rank} · {percent}%`; the rank name alone at the top
  rank; `No rank` below the first rank; `N/A` with Too few runs, with no
  runs, or for a benchmark scenario without a ladder.
- **Not recent:** both typical cells of a row whose typical score is known
  and not recent, as of the page opening (TB3, TB4). The value shows in a
  muted grey that clears 4.5:1 on the plain, alternating and hovered rows in
  both themes, with a clock after it that a screen reader skips, and
  `Not recent` is read after the value. Too few runs and `N/A` are never
  marked.
- **What explains the clock:** each old cell's hover ([The hovers](#the-hovers))
  and the Typical Score header's tooltip. There is no key line. The
  explanation counts the runs behind the value, as recency does, never the
  scenario's runs: they differ when the store holds runs dated after the
  page opened, such as after a system clock correction.

### Rank position

- **Ranked:** the ranks passed, from the table's ladder walk, plus
  `(typical - last passed threshold) / (next threshold - last passed
  threshold)`. The walk stops at the first threshold above the score, so the
  fraction is always at least 0 and below 1, even on the corpus's ladders
  that tie or dip.
- **Below the first rank:** `1 / (1 + gap / 100)`, where `gap` is the
  unrounded gap from the typical score to the first rank by the Next Rank
  rule: by pace where it applies, a percentage of the score otherwise. On
  score math that is the typical score over the first threshold; by pace it
  is the first rank's time over the typical time. Where the gap is
  undefined, a score of zero or less with no pace, the key is 0. Always below
  1, so it sorts under every ranked row.
- **At the top rank:** the rank count.
- **The percent:** the fraction times 100, rounded down and capped at 99
  while a next rank remains: `min(99, floor(round(x * 100, 6)))`. The inner
  round strips float noise, as the Next Rank gap's does before it rounds up,
  but it can carry a score a hair under the next threshold to 100: between
  thresholds of 1,000 and 10,000, a typical score of 9,999.999999 would read
  100% without the cap. So no cell reads as the next rank, and `0%` means on
  the threshold or just above it: 500.5 between 500 and 600 reads `0%`. The
  sort key and the ladder walk use the unrounded fraction.
- **Pace:** between two thresholds the fraction is the same whether measured
  in score or in time, since a time-scored score is a constant minus the time
  and the constant cancels. Below the first rank it doesn't cancel: with a
  120-second typical run and a 100-second first rank, the ratio of scores is
  0.98 when the constant is 1,000 and 0.8 when it is 200, either side of an
  ordinary row at 90 against 100, while the ratio of times is 0.83 for both.
  That is why the below-first key follows the gap's rule. Pace applies, as
  for the PB's gap, when every run behind the typical score is of the version
  the constant was read from; the hover's gap follows the same rule.

### The hovers

- **Typical Score:** the Scenario Stats lead's hover, built from the same
  strings ([Copy](#copy)): the median's run count, the run and session counts
  with their dates, the recent count, and the middle 50% and middle 80%.
  Below the minimum, the card's below-minimum hover. On an old value, the
  opening sentence is followed by `Fewer than 10 of them are from the last
  30 days, so it may be out of date.`, "them" being the runs the opening
  sentence counts.
- **Typical Rank:** the gap from the typical score to the next rank,
  `+{gap}% to {rank} · {points} to go`, or `+{gap}% faster to {rank} ·
  {points} to go` where pace applies. No hover at the top rank, as Next
  Rank's Top rank has none. On an old value, a second line, `Fewer than 10 of
  the typical score's runs are from the last 30 days, so it may be out of
  date.`; at the top rank that line is the whole hover.
- Both cells carry the dotted underline the table uses for a cell with a
  hover.
- **From the keyboard:** when keyboard focus lands on a typical cell, its
  hover opens beside it with the same content. It closes when focus moves on,
  on Escape, on a click, and when focus leaves the table. A click that
  focuses a cell opens nothing extra; the mouse hover stays the grid's own.
  AG Grid's `tooltipTrigger` can't do this without ending every mouse hover
  ([Verified facts](#verified-facts)), so the build opens it from the grid's
  cell-focus event, as the prototype does.
- **For a screen reader:** each typical cell's hover text is its accessible
  description, read after the value and, on an old value, after
  `Not recent`.

### Sorting and the address

Both columns sort with the existing nulls-last comparator, so Too few runs
and `N/A` sort last in both directions. `?sort=` gains `typical-score` and
`typical-rank`; on a playlist's table `typical-rank` names no column, so a
value holding it is not valid there, as `rank` already is not.

### Accepted costs

- **A hover can count from a half the cell does not show.** The typical
  score is a median, and with an even run count it is the mean of the two
  middle runs: Pasu Voltaic Reload Easy's middle runs are 78 and 79, so its
  typical score is 78.5. Scenario Stats' rounding rule shows it as 79, and
  the rank, the percent and the hover's `1.5 to go` count from 78.5 against
  Celadon at 80. The maintainer, 2026-10-22: "We'll skip it for now and
  accept that discrepancy." It can show on the 49 of 226 known typical
  scores whose median falls halfway between two runs. The fix, if it is ever
  wanted, belongs to the typical score's rounding rule, not to this table.
- **Header tooltips stay mouse-only,** as every column's are today. The cell
  hovers, which open from the keyboard, say what the Typical Score header
  says about the clock.
- **The clock's meaning takes a hover the first time.** Nothing on the page
  names it until a cell or the header is hovered or focused; the mark itself
  stays visible on every old value.

### How it is built

- **Row fields.** Each row gains `typical_score_display`,
  `typical_score_sort`, `typical_not_recent`, the Typical Score hover's text, and
  on a benchmark `typical_tier_display`, the rank position, the percent and
  the Typical Rank hover's text. They come from one whole-store snapshot per
  table build, as Scenario Stats takes one, and every row path (phase 1, the
  fill, and a cancelled fill's rebuild) carries them, as all three already
  carry the ladder.
- **Column defs.** Two columns with their own IDs, `typical_score_sort` and
  `typical_tier_sort`, added after `next_tier_sort` (or `pb_score_sort`), in
  the auto-size keys and the Columns menu. Their formatters read their own
  row fields; no column changes another's meaning. Both draw their cells with
  one cell renderer: the value, the clock and `Not recent` on an old value,
  and the hover's text as the grid cell's accessible description.
- **The Typical Score hover** is a custom tooltip component that wears the
  `ag-tooltip` class and is as wide as its text, up to the card's 360 px. The
  Typical Rank hover is a small one of the same kind, so an old value's
  second line breaks.
- **The keyboard hover** opens from the grid's cell-focus event when the
  focus came from a key, with the same content and the same tooltip styles.

The prototype that settled the rows lives outside the repository, with its
versions; it is a reference for the build, not its code.

### Copy

Every string this proposal adds. The rest of the table is unchanged.

**Headers:** `Typical Score`, `Typical Rank`.

**Header tooltips:**
- Typical Score: `The median of your last 20 runs of this scenario, or of
  all your runs if you have fewer. A clock beside the number means fewer
  than 10 of those runs are from the last 30 days, so it may be out of
  date.`
- Typical Rank: `The highest rank your typical score reaches on this
  scenario, and how far it is toward the next rank. The percent rounds down,
  so 0% can be just above the rank's threshold. Lower is weaker on this
  benchmark's rank ladder.`

**Cells:** `{rank} · {percent}%`, `Too few runs`, and the existing `N/A` and
`No rank`.

**Not recent:** `Not recent`, read by a screen reader after an old value.

**The Typical Score hover**, verbatim from Scenario Stats, plus one
sentence:
- `The median of your last {n} runs.`, or `The median of your {n} runs.`
  when the scenario has no runs outside the window.
- On an old value, after it: `Fewer than 10 of them are from the last 30
  days, so it may be out of date.`
- **`Runs:`** `{n} in {s} sessions · {first} to {last}`, with `on {date}`
  for a single date and `session` for one.
- **`Recent:`** `{k} of {n} from the last 30 days`
- **`Middle 50%:`** `{p25} to {p75}`
- **`Middle 80%:`** `{p10} to {p90}`
- Below the minimum: `A typical score needs 10 runs across 2 or more
  sessions, or 20 in one session. You have {n} runs in {s} sessions.`, with
  `run` and `session` for one.

**The Typical Rank hover:** `+{gap}% to {rank} · {points} to go`, or
`+{gap}% faster to {rank} · {points} to go`, each figure formatted as Next
Rank's are. On an old value, a second line: `Fewer than 10 of the typical
score's runs are from the last 30 days, so it may be out of date.`

**Columns menu:** `Typical score`, `Typical rank`.

### Terms

For [docs/glossary.md](../glossary.md), under Benchmark ranks:

**Typical Rank.** The benchmark tier a scenario's typical score reaches on
its ladder, found the way Rank is found from the PB, with how far the
typical score sits toward the next tier. It is never a rank the player has
earned: KovaaK's ranks the PB. It is unknown while the typical score is,
which is never read as weak.
- On screen: the Typical Rank column, such as `Celadon · 7%`.
- In code: `typical_tier`; its sort key is the rank position, the ranks
  reached plus that fraction.
- Not Rank.

The existing **Recent** entry gains the table: on the scenario table, an old
value shows in a muted grey with a clock after it and `Not recent` for a
screen reader, explained in its hover.

### Decisions this changes

None. The 2026-10-04 principles keep Rank, Next Rank, Position and
Percentile on the PB, and they stay there. The 2026-09-27 rank columns keep
the local all-time high. The typical score's rounding is unchanged
([Accepted costs](#accepted-costs)). The shipping PR records TB1 to TB4 as
new decision-log entries.

### The roadmap

This proposal is the one the roadmap's "Weakness by the typical run" entry
asked for: columns that "rank weakness by the typical run", with "the
judgment and its evidence bar" in a proposal of their own. TB2 is the
ranking and TB3 its evidence bar, so the entry leaves
[the roadmap's Future list](../roadmap.md#future-briefly) when this ships,
as a step of the shipping checklist. The rank-up chance entry stays: how
likely one run is to clear the next rank is a different question.

### Alternatives rejected

- **A PB / Typical switch that changed PB Score, Rank and Next Rank in
  place.** It was the maintainer's request on 2026-10-21 ("I'd like to have
  the option to base these metrics on Typical Score instead") and the first
  draft of this proposal, with Next Rank measured from the typical score to
  the rank above it, and a flip that held the rows in place. Advised against
  by `claude-fable-5-1` on 2026-10-22, and set aside by the maintainer after
  comparing the two layouts on the prototype. Against it: it shows one basis
  at a time, so the per-row comparison takes a flip and a memory; it needed a
  held-order sort, a cleared address and a mount-time header workaround; and
  a copied sort link meant a different sort in a browser on the other basis,
  breaking the 2026-09-27 rule that a copied link keeps its sort.
- **A typical Next Rank column, as the weakness sort.** It answers which
  scenario is closest to its next rank, which inside a rank is nearly the
  reverse of weakness (TB2). Its figure stays in the Typical Rank hover. As
  an extra column it would scroll the table by 152 px at 2560.
- **`Celadon 4.07` or `4.07`.** Same sort; the maintainer found the percent
  friendlier, and the ordinal changes meaning between ladders. `Celadon
  4.07` does let a player compare across ranks by eye; sorting does that
  here.
- **Measuring the rank and gap from the rounded typical score,** to make the
  hover agree with the cell. The maintainer declined it as a workaround;
  the cause is the typical score's rounding ([Accepted
  costs](#accepted-costs)).

## Out of scope

- **The rank-up chance,** the estimated chance that one run clears the next
  rank, from the player's spread. It stays on the roadmap.
- **Changing the typical score's rounding** to end the half-point mismatch.
- **Rank position for the PB Rank column,** which still sorts by rank alone.
  It would be its own decision.
- **Updating the table when a run lands.** The table's existing rule holds
  for the new columns.
- **A typical Position or Percentile.** The leaderboard ranks best scores.
- **A benchmark-level rank,** for either basis.
- **Long Next Rank cells cut off at page open,** such as `+1.9% faster to
  L…`. Main does this today in headless Edge at 1536 to 2560 px, with or
  without this change; it is a separate defect.

## Delivery plan

**One PR, unblocked:** the proposal was ratified on 2026-10-22, and the PR
starts once this proposal merges. It also ships this proposal: the row
fields, the two columns,
the hovers and their keyboard route, the Not recent mark, the
rank position, the Columns menu entries and sort names, and
the shipping checklist (decision-log entries TB1 to TB4, the playlists and
typical score specs, the glossary, the roadmap, the product inventory, the
user guide).

**Why one.** The columns without the position sort would ship a Typical
Rank that cannot order its largest rank, and the row fields alone show
nothing.

## Testing

- **Unit:** the rank position and percent on a four-rank ladder (500 is
  `Bronze · 0%`, 540 is `Bronze · 40%`, 599.999 is `Bronze · 99%`), at the
  top rank, and on a ladder that ties and one that dips; the cap, where a
  typical score of 9,999.999999 between thresholds of 1,000 and 10,000 reads
  99% and 10,000 reads the next rank at 0%; below the first rank by score
  math and by pace, where an ordinary row at 90 against 100 and a time-scored
  row whose 120-second typical run misses a 100-second first rank keep the
  same order whether the scenario's constant is 1,000 or 200, and a score of
  zero or less with no pace keys 0; the typical row fields for a known, a
  not-recent, a below-minimum (singular and plural counts) and a no-runs
  scenario; a scenario with 10 runs in the last 30 days and 11 dated after
  the judging moment, which is not recent, and whose hover counts 9 of its
  20 runs as recent, not the scenario's 10; pace on one version and score
  math on mixed versions; all three row paths carry the fields.
- **Column defs:** the two columns' placement on both kinds of table, the
  Columns menu entries, and the `?sort=` names, including `typical-rank` not
  valid on a playlist's table.
- **Browser** (headless Edge, then the maintainer's Firefox), on Viscose
  Benchmark S2 Medium in both themes: Typical Rank sorted ascending starts
  Ground Plaza Sparky V3, Pasu Voltaic Reload Easy, CatClick Medium; both
  hovers read as specified; Flower 50cm marks both cells Not recent and each
  hover adds its old-value line, which a recent value's hover never has; an
  old value
  measures 4.5:1 or more on the plain, alternating and hovered rows in both
  themes; arrowing onto Flower 50cm's typical cells opens each hover, Escape
  closes it, and a click opens only the mouse hover; Aimspeed Benchmark 2
  Normal's below-first rows read `No rank` and sort first; no header is
  clipped at 1536, 1920, 2560 and 3840 px.
- **Screen reader** (NVDA, in the maintainer's Firefox): on Viscose Benchmark
  S2 Medium, arrowing across the typical cells reads a recent value as its
  value, an old one with `Not recent`, and Too few runs as those words, each
  followed by its hover's text. The ordinary gates can't establish this.
- **Gates:** pytest, ruff format and lint, mypy, compileall, as AGENTS.md
  lists.
