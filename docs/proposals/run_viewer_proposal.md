# Run History Opens Any Run And Measures It Against Its Typical Runs

Status: Proposed
Date: 2026-10-30

## TL;DR

Run History lists and charts a scenario's runs but can't show one: a run's
settings, how it went against each bot, and most of what its stats file
recorded stay out of reach. This proposal opens any run from the run list or
the chart in the chart's place, and measures it against the runs behind its
typical score at session start. The run shows its score tiles, a By Bot table
when it names two bots or more, eleven of its settings with the changed ones
marked, and everything the stats file recorded, closed by default. Close or
the Esc key brings the chart back as it was left.

## Decisions needed

Six rulings: RV1 to RV6. The maintainer ratified this proposal on
2026-10-30 at `f80c109`: "Sounds good. I ratify." That settles each row as
its recommendation, RV3, RV4 and RV5 as amended in review. Before that, each
row was the maintainer's lean from the design discussion of 2026-10-25 to
2026-10-30, worked out on twelve versions of a mockup built from their own
stats, at 2560 and 1920 wide, in light and dark (local only, under the main
checkout's `ignore/mockups/run-viewer/`). Each row keeps what was said, for
the record. Everything else is author-owned, in [Design](#design), and the
ratification covers it too.
The ideas the discussion set aside are in [Out of scope](#out-of-scope), each
with what would bring it back.

### RV1. A run opens in the chart's place, and Close or Esc closes it

Status: Ratified (user), 2026-10-30: accept the recommendation below. The
maintainer's lean before that, 2026-10-29, on the author's proposal to keep
the open run out of the address: "agree, but I also vote to make a keyboard
shortcut to make navigation a bit more seamless."

The material consequence: the browser's Back doesn't close a run. It leaves
the page, as it does after any change on Run History today, and no link
reopens a run.

**Recommendation: a click on a Run row of the run list, in either view, or
on a run point or PB star of the chart, opens that run in the chart
column's place, with the list beside it. Enter or Space on a focused Run row
opens it too. A click on another Run row switches to that run. Close, or
Esc, brings back the chart as it was left: its mode, zoom, ranges and hidden
traces. Esc is left alone while a text field has focus or a dialog, menu or
dropdown is open. The open run is not written to the address and adds no
history entry.**

- **In place, not a page of its own.** The list stays beside the run, so
  stepping between runs is one click, and the chart keeps its state behind
  the run. A separate page with tabs was the first concept; see
  [Alternatives rejected](#alternatives-rejected).
- **Why not in the address.** Run History writes nothing to the address
  today: it reads `?scenario=` once when the page loads and never writes it.
  The open run would be the page's first history handling, and a link to a
  run needs rules for a run whose file is gone and a scenario that isn't
  selected. Shelved as S8.
- **Esc is the shortcut the maintainer asked for.** Stepping between runs
  with the arrow keys is not in it: the run list's grid already moves its
  own focus with them. It stays on the shelf with S7.
- **From the keyboard.** The list already takes Enter and Space on a
  session or scenario row, so a Run row takes them too, and the whole round
  trip works without a mouse: focus goes to Close when a run opens, and back
  to where it came from when the run closes. A chart point can't take focus,
  so the keyboard's way in is the list.
- **Hover is unchanged.** The 2026-10-23 and 2026-10-24 hover entries kept
  click actions out of scope, and the second accepted that an old run's
  accuracy needs the list "until a click feature exists". This is that
  feature ([Decisions this changes](#decisions-this-changes)).

### RV2. The run is measured against its typical runs, with no Compare with menu

Status: Ratified (user), 2026-10-30: accept the recommendation below. The
maintainer's lean before that, 2026-10-30, after a write-up of what a menu
would take: "Yes, keep it shelved."

The material consequence: the page can't answer "what did my PB run do
differently?" except by opening the PB run, whose figures read against its
own typical runs.

**Recommendation: everything compares with one set of runs, the run's
typical runs: the runs behind its typical score at session start, up to 20
runs of the scenario before the run's session, known at 20 runs or at 10
across 2 or more sessions. A tile's typical is the median of its figure over
those runs, a setting's is its most common value, and a bot's is its median
over the typical runs that name it. A typical counts only the runs that
have its figure, and its hover says how many. One line under the score
names the runs: `Typical comes from your 20 runs before this session, played
from Sep 27, 2025 to Oct 6, 2025.`**

- **One yardstick for the whole page, and the card's.** The latest-run card
  already measures a run against the typical score at session start
  ([2026-10-25](../decision_log/2026/2026-10-25-the-latest-run-card-measures-the-run-against-the-typical-score-at-session-start.md)).
  The Score tile's typical is the same value, the median of the same runs:
  over the mockup's six scenarios, the median of the 20 runs before each
  run's session equals the card's typical score at session start on every
  run, up to rounding. The roadmap's principles judge skill by the typical
  run.
- **What a menu would take.** It would swap the yardstick of every section:
  each tile's second line, each card's typical line, By Bot's middle column,
  and the line under the score. The arithmetic is the same with a set of one
  run. The cost is in decisions and states:
  - Which PB. It has to be the one the run chased, not today's, which
    disagrees with the score line's `% of PB` on 39 of 55 Popcorn runs and
    69 of 86 PGT runs. On a run that set a PB, it is the PB it beat.
  - The first run has neither a PB before it nor a previous run.
  - Whether the choice sticks across runs, scenarios and reloads.
  - Every `Typical` label and hover count, worded for each option.
  - Noise. A median of 10 to 20 runs moves far less than one run, so every
    Difference against a single run would swing more, by chance.
- **When there are no typical runs,** the line says why, in one of two
  forms ([Copy](#copy)). Every Typical and Difference figure is then left
  out, and no setting is marked.
- **A typical on fewer runs.** A figure some typical runs don't have, such
  as a bot only some of them name, or a time only some of them can give, is
  the median of the ones that have it. Every typical's hover counts the runs
  it took, so a typical on one run reads as one. There is no smaller
  minimum: the count is shown instead of a second rule.

### RV3. The tiles: Score, Accuracy, Shots fired and Reloads always, then Time on a time-scored scenario

Status: Ratified (user), 2026-10-30: accept the recommendation below, as
amended in review. The maintainer's lean before that, 2026-10-29: "I now
vote for always showing them, regardless of the type of run. Otherwise the user has to
adjust columns in the right side panel, when the intent of the Run Viewer
UI is to show everything applicable to the run." Fire held, a tile for how
much of the run the fire button was down, was their idea (2026-10-29). On
2026-10-30 they leaned toward leaving it out of the first version and
shelving it (S9).

The material consequence:
- Time is the first place the app shows a completion time
  ([Decisions this changes](#decisions-this-changes)).
- Nothing on the page says the player let go of fire. On a fixed-length
  scenario, Shots fired below its typical is the only sign.
- Reloads reads 0 on scenarios with unlimited ammo.

**Recommendation: a row of tiles, in this order: Score, Accuracy, Shots
fired, Reloads, then Time when the run's version is time-scored. Each shows
the run's value over `Typical {value} · {difference}`, and its hover says
how many typical runs the typical rests on. Accuracy is KovaaK's hits over
shots.**

- **The same place on every scenario.** The four every run has come first,
  so a tile never moves between scenarios. Score and Accuracy differences
  are green when better and red when worse. Shots fired's is uncolored,
  since more shots is neither. Reloads' is green when fewer.
- **Time** is the clock's constant less the score, `C − s`, for the run's
  own version of the scenario, which the app recognizes as time-scored from
  its performance files, as the latest-run card does. It is exact. The run
  length the stats file gives is up to 1.7% off on a 60-second run, because
  the file name's end time is in whole seconds. A faster time is green.
- **Time across versions.** The constant is read from one version, and the
  typical runs can be on others: the typical score's window spans versions.
  The tile's typical follows the latest-run card's rule, so the tile and the
  score line agree: Time has a typical only when every typical run is of the
  run's version. Otherwise the tile shows the run's time alone. A run whose
  version the app can't tell is time-scored has no Time tile, as the card
  then measures it by score.
- **No Fire held tile in the first version.** It measured how much of the
  run the fire button was down, as the run's shots a second over the
  scenario's fastest-firing run. Neither the button nor the weapon's fire
  rate is in the file, so that 100% is a stand-in, not a measured full hold,
  and the run length's rounding alone moves the figure 1 to 2 points. On a
  fixed-length scenario, Shots fired against its typical shows the same
  drop without the stand-in. Shelved as S9, with what it found.

### RV4. By Bot: each bot against its own typical, with no verdict on which to practice

Status: Ratified (user), 2026-10-30: accept the recommendation below, as
amended in review. The maintainer's leans before that, 2026-10-29: play
order where it is fixed, rows that highlight on hover, the section above Settings, This Run,
Typical and Difference columns, every column sortable, and no By Bot for a
single bot. On 2026-10-30: no lead line naming the bot this run lost the
most on.

The material consequence: the page shows how each bot went against its own
typical but names no bot, neither the one this run lost the most on nor the
one to practice. Sorting by Difference brings the largest to the top.

**Recommendation: a By Bot table when the run's kill table names two bots
or more, one row per bot. Its figure follows what the score is made of:
time per kill when any bot has two kills or more, time per bot when each
bot is one kill and the run's version is time-scored, and accuracy alone
when each bot is one kill of any other run. The figure and accuracy each
show This Run, Typical and Difference. A bot's times show only when every
gap behind them is known. Rows start in play order where each bot is one
kill, and in name order otherwise. Each header sorts ascending, then
descending, then back, on a click or on Enter while it has focus.**

- **Reach.** 175 of the 866 scenarios the maintainer ever played name two
  bots or more (20%). Of the 54 played in the last 90 days with 10 runs or
  more, 14 do: 26% of those scenarios and 20% of their runs. Scenarios with
  no kills, such as Raw Control and the Controlspheres, have an empty kill
  table.
- **Three kinds among those 14.**
  - Fixed-length phases where each bot is one kill of about 20 seconds
    (PGT, Ground, Aether, Plink Palace). Time is the phase's length, so
    accuracy is what tells the bots apart. A PGT run's three kills take
    19.0, 20.4 and 20.4 seconds.
  - Time-scored runs, one kill per bot (Air CELESTIAL, Air Pure, Air
    Spectral, Ground Plaza Sparky). Each bot's time is the run's split.
  - Many kills per bot (EddieTS, FlyTS, Popcorn, Popcorn MV, B180T,
    Bounceshot).
- **A kill's time is the gap since the kill before it,** not its TTK
  column, since one-shot kills record a TTK of 0. So it includes finding
  the bot, and the subtitle says so.
- **Play order.** Air and PGT play their bots in the same order on every
  run, and Popcorn's come at random: 51 orders in 55 runs.
- **No verdict on which bot to practice.** This was measured by redrawing
  the newest 20 runs at random 300 times. The bot with the slowest typical
  is the same one in 80% of redraws or more on 7 of the 14 scenarios, but
  it is often slow by design. Air Pure's UFO bot is slowest in every redraw,
  with a median TTK 28% longer than any other bot's. The measure that
  corrects for design, the gap between a bot's typical and its best quarter
  of runs, reaches 80% on none of the 14, at 20 runs or at 50 (best 77%).
  The two measures name the same bot on 4 of the 14. On PGT the slowest is
  Bounce 1 Bot, and the most room is on Float 3 Bot.
- **No lead line either.** A line naming the bot this run lost the most on
  needs a ranking the table doesn't have. The largest difference per kill
  puts one kill half a second slow above twenty kills a tenth of a second
  slow, though the second cost 2 seconds and the first half of one. Weighting
  by kills doesn't settle it: a kill's gap also holds the travel since the
  kill before. The table shows each difference, and its sort finds the
  largest.
- **One bot shows no table.** It would repeat the tiles. VoxTS's kills
  equal its score, and its time per kill is 60 seconds over the score. Its
  typical accuracy would also read 0.18 points off the tile's, because the
  kill table leaves out shots fired after the last kill.
- **Names are taken as they come.** FlyTS's Fly Bot and Fly Bot 2 have
  median TTKs of 1.041 and 1.040 seconds and still get a row each.

### RV5. Settings: eleven cards on every run, a changed one marked with its typical value

Status: Ratified (user), 2026-10-30: accept the recommendation below, as
amended in review. The maintainer's leans before that:
- 2026-10-29: cards of one size, with the count on hover.
- 2026-10-29, on show-or-hide rules: "keep things simple and just show all
  the cards. We can always consider trimming things later."
- 2026-10-29, on a summary of changed settings: "I'd prefer that this info
  lived inside the respective card."
- 2026-10-30: keep Crosshair color and its color square, report the game's
  bug to KovaaK's developers, and reconsider only if it is never fixed.
- 2026-10-30, later: leave the Crosshair color card out of the first
  version (S10).

The material consequence: the page doesn't show the crosshair's color. The
stats file has held a wrong value for it since KovaaK's 3.7.0, and the value
stays in Everything Recorded as written. Five cards that rarely change take
a row of their own.

**Recommendation: eleven cards, the same on every run, in rows of six. The
first row is the aim setup: Sensitivity, Vertical sensitivity, DPI, FOV,
Crosshair and Crosshair scale. The second is set once: Hide gun,
Resolution, Resolution scale, Frame cap and Input lag. A card whose value
differs from its most common value over the typical runs is tinted and
shows `Typical {value}` under its own, with the count on hover. A value the
stats file doesn't have reads `Not recorded` and is never marked.**

- **What changes in practice.** All 9,280 of the maintainer's runs, from
  2019-07-14 to 2026-10-29:
  - Never changed: Hide Gun, Input Lag.
  - Unchanged for the last year: DPI, Resolution, Resolution Scale (one run
    at 50% on Oct 9, 2025), Crosshair.
  - Changed in the last year: sensitivity 359 times, Crosshair Scale 105,
    Max FPS 3, FOV 2.
- **Why all eleven.** Show-or-hide rules multiply states and edge cases, in
  the maintainer's words, and a grid that never changes shape reads the
  same on every run. Any of the eleven can change a run, which is why the
  rarely changed five stay on screen rather than living only in Everything
  Recorded.
- **Why in the card.** The mark and the typical value sit where the eye
  already is. v8 to v11 also put a notice under the tiles; this row drops
  it. On the v12 mockup, before the cuts, which can only shorten the page:
  at 2560 by 1320 the cards are on screen without scrolling in every
  mocked state. At 1920 by 960 their second row is cut off on the three
  multi-bot scenarios, and on Air all of Settings is below the fold.
- **`Not recorded`.** The 570 runs from 2019-07-14 to 2021-07-20 have no
  DPI, Resolution or Resolution Scale line.
- **Why no Crosshair color card.** In-game tint 00FF00 is written
  `000100FF`, and a test run tinted 147245 was written `000000FF`. Every one
  of the maintainer's files from KovaaK's 1.0.8 to 2.0.5 holds a six-digit
  color (FFFFFF, FFFF00, 00FF00), and every one from 3.7.0 on, 8,714 of
  them, an eight-digit one. They have no file from the versions between, so
  the bug may be older than 3.7.0. The weapon row's crosshair color column
  is empty. A card would show a value that isn't the player's tint, its
  square would draw it black, and a warning on the card would sit beside
  that on every run since Dec 2024. A fix in the game would correct new
  files only, and new runs would then read as a changed color against
  typical runs written before it. Shelved as S10.
- **Not cards.** The scenario's version: the player can't change it, and 1
  run in 3,589 was on another version than most of the 20 runs before it.
  It is in Everything Recorded. The performance file's time scale is the
  scenario's own, not a setting: it differs from 1 in 483 files, and no
  scenario of 248 ever has two.

### RV6. Everything Recorded: the whole stats file, closed, grouped by kind

Status: Ratified (user), 2026-10-30: accept the recommendation below. The
maintainer's leans before that, 2026-10-29: everything in the stats file,
organized and low priority, collapsed or at the bottom. On 2026-10-30: "Yes,
keep folding."

The material consequence: the page shows fields that answer no question
today, such as Midairs and MBS Points, under the game's own names, behind a
closed section.

**Recommendation: a closed section at the bottom. The fields are grouped as
Result, Other Counters, Run and Settings, then Other for any field the app
doesn't know, so a game update never hides one. A group whose fields are
all zero folds to one line. Files names the stats file and whether a
performance file was found. Weapons shows the weapon rows, and Kills the
kill table, both as written.**

- **Zero, not missing.** A group folds only when every field in it is there
  and reads zero. A field the file doesn't have, or has with no value, isn't
  zero, so its group stays open.

- **Why keep it.** It is the fallback for everything shelved, and power
  users may spot ideas in it. It is cheap once the file is read whole for
  By Bot and Settings. It is the first thing to cut if v1 has to shrink.
- **The kill table shows every column the file has,** in file order. The
  mockup showed a selection, which "Everything" doesn't allow.

## Problem

### What Run History shows of a run today

A run is a row in the run list: its time, score, accuracy and
sensitivity, plus the optional columns Shots Fired, Reloads, FOV and Avg
FPS, hidden to start. It is also a point on the chart, whose tooltip gives
its score, time and run numbers. The latest-run card describes the newest
run only. Nothing shows a run's other settings, how it went against each
bot, or the rest of its stats file. The 2026-10-24 hover entry accepted that
finding an old run's accuracy means scrolling, opening groups or loading
older sessions in the list, "until a click feature exists".

### What the maintainer wants from a run

Their jobs, 2026-10-29, as leans:

1. In scenarios with several bot types, see which bots they're weak at, to
   prioritize practice: "track Typical stats, particularly for accuracy; or
   keep it simple and simply compare vs PB run".
2. Performance through the run, as KovaaK's own chart of score, accuracy,
   SPM, kills and KPS against time shows it: steady, spiking or fading, and
   which moments to review on video. A slight lean, unsure of the value.
3. Everything in the stats file, organized, at low priority. Power users may
   spot feature ideas in it.

Their theme: avoid the overload of data that answers no question. They
asked to build the highest-value items first and keep the rest as shelved
ideas. This proposal is that first version. Job 2 is shelved as S1, and job
1 gets By Bot without a verdict, for the reasons in RV4.

### Why now

The tracker item asks for a Run Viewer: all of the stats and performance
data, a per-bot breakdown, and clickable chart points. The roadmap's Future
list holds "Per-bot breakdown on time-scored kill scenarios". Hover linking
shipped on 2026-10-23, and the chart's points already carry each run's id,
its stats file's name, in the trace's `ids`, so a click has a run to open.

### Verified facts

Checked against `main` at `22894be` and the maintainer's stats folder on
2026-10-29 and 2026-10-30.

- A run's id is its stats file's name (`run_id`). The chart's run trace and
  its stars carry those ids, and the run list keys its rows by them.
- The run record (`RunData`) keeps the score, accuracy, sensitivity, the
  scenario's hash, the run's start and length, shots fired, reloads, FOV,
  FOV scale and Avg FPS. It keeps no kill table, no weapon rows and no
  other field, so the run has to be read again from its file.
- `typical_score_at_session_start` returns the typical score as it stood
  when a session began, with the runs behind it in play order, up to 20.
  It is known at 20 runs, or at 10 across 2 or more sessions, and `None`
  when the scenario has no run before the session. The app words that
  minimum as "A typical score needs 10 runs across 2 or more sessions, or 20
  in one session." (`below_minimum_text`).
- The app tells whether a version of a scenario is time-scored from its
  performance files. `get_version_pace_basis` answers for one version, and
  `get_pace_basis` for the version of the scenario's newest run. Both
  answer `None` alike for a version that isn't time-scored and for one they
  can't tell about, such as a version with no performance file. The
  constant `C` gives a completion time `C − s`. `eligible_pace_constant`
  gives it only when every run compared is of the version it was read from,
  which is how the latest-run card measures a run against its typical.
- `Challenge Start:` is a time of day with no date, as is each kill's
  timestamp. `Pause Duration:` is the run's paused time in total, with no
  record of when. Of the maintainer's 1,595 files that name two bots or
  more, 54 have no `Challenge Start:`, all from 2020 on KovaaK's 2.0.1 and
  2.0.2, and 7 were paused. Two cross midnight, such as a Plink Palace Easy run that started
  at 23:59:42. One, a B180 Voltaic run from Dec 2020, has its first kill 10
  seconds before its `Challenge Start:`.
- The stats folder is read whole at startup, and nothing about a run is
  stored anywhere else. Removing a stats file removes the run at the next
  start.
- A stats file holds a kill table (`Kill #,Timestamp,Bot,Weapon,TTK,Shots,
  Hits,Accuracy,Damage Done,Damage Possible,Efficiency,Cheated,OverShots`),
  one or more weapon rows, and `Key:,value` fields. The weapon row's header
  names the settings columns, but the rows fill only up to Damage Possible.
- The kill table's shots add up to less than the weapon row's when shots
  were fired after the last kill: 5,888 against 5,908 on the VT PGT
  Intermediate S5 run that ended Aug 6, 2026, 11:11 PM.

### Not checked

- How long it takes to read a run's file and its typical runs' files, up
  to 21 files of a few kilobytes each, on opening a run.
- How Esc behaves beside the app's Mantine overlays: the note dialog, the
  scenario dropdowns and the Columns menu. The rule in RV1 is the
  behavior; the build finds how to keep it.
- The All scenarios view of the list, which the mockup doesn't draw.
- A screen reader's view of the run. The tables are real tables, and the
  card's tint is matched by its typical line, so a change isn't carried by
  color alone.

## Design

### What the player sees

A click on a Run row or a chart point replaces the chart, and everything
above it in the chart column, with the run. Top to bottom:

1. **The header.** A small line names the scenario and when the run ended,
   to the second. Under it the title gives the run's number and session, as
   the list does: `Run 2 · Aug 6, 10:23 PM session`. **Close** sits at the
   right, with a small `Esc` key hint. The run's length isn't in the header:
   at the app's nearest-minute rounding every run of a 60-second scenario
   reads `1 min`. Time and Everything Recorded have it.
2. **The score line.** The score, its badge, and the latest-run card's
   comparison: `9.6% below typical at session start · 84.8% of PB`. The
   card's code builds it, for any run, not only the latest.
3. **The reference line,** saying which runs are typical (RV2).
4. **The tiles** (RV3).
5. **By Bot** (RV4), when the run names two bots or more.
6. **Settings** (RV5).
7. **Everything Recorded** (RV6), closed.

The run list stays beside the run, with the open run's row marked, and a
click on another Run row switches the run. Points aren't clickable while a
run is open, because the chart is hidden.

### Opening and closing

- **Opening.** A click on a Run row in either view of the list, or on a run
  point or a PB star of the chart, in any chart mode. Enter or Space on a
  focused Run row, as on a session row. A Session or Scenario row keeps its
  own click and keys, which open and close the group. Hover linking is
  unchanged.
- **A position several runs share,** such as two runs that ended in the
  same second with the same score in Score vs Time, or any shared
  sensitivity in Score vs Sensitivity, opens the run its tooltip names, as
  hover identifies it.
- **Focus.** When a run opens, focus goes to **Close**. When it closes, by
  Close or Esc, focus goes back to the Run row that opened it, or to the
  chart's mode control when a point or star did. Switching runs from the
  list leaves focus on the row pressed.
- **The chart is hidden, not rebuilt.** Closing shows it exactly as it was:
  mode, zoom, ranges, hidden traces and the panel's switches.
- **Closing.** Close, or Esc when no text field has focus and no dialog,
  menu or dropdown is open, as RV1 says.
- **A change of the selected scenario closes the run,** whether the player
  made it or Follow did. The chart the run stood in for is gone, and Follow
  means "show what I just played".
- **A run of another scenario,** a Run row under All scenarios, opens
  without changing the selection. The header names its scenario, and Close
  returns the selected scenario's chart.
- **A run that lands while one is open** joins the list and the hidden
  chart. The open run stays, unless Follow changes the selection.
- **A reload** shows the chart, since the open run isn't in the address.
- **A run whose file can't be read** when it is opened shows the header and
  a line saying the file couldn't be read, with the log pointer. The list
  and Close work as usual.

### The figures

All of them are worked out when the run opens, from its stats file and its
typical runs' files. Nothing is stored, as nothing about a mark is stored
today.

- **Typical runs.** `typical_score_at_session_start(...).runs`, when the
  value is known, at any age, as the latest-run card counts it. The
  reference line's dates show how old the runs are. When the value is
  unknown or `None`, there are no typical runs.
- **A tile's typical** is the median of its figure over the typical runs
  that have one, and its difference is the run's figure less that median.
  Accuracy's difference is in percentage points. The hover counts the runs
  the median took.
- **Time.** The basis is the run's own version's
  (`get_version_pace_basis`), never the scenario's newest version's. With
  none, there is no Time tile. The run's time is `C − s`, shown as
  `m:ss.s`. The typical is the median of `C − s` over the typical runs, only
  when `eligible_pace_constant` gives the constant for all of them and the
  run, as the latest-run card asks it. Otherwise the tile has no typical
  line. A time of zero or less isn't a time: the tile shows none for the
  run, and such a typical run doesn't count toward the median.
- **A setting's typical** is its most common displayed value over the
  typical runs that have one. A card is marked when the run has a value,
  there is a typical, and the two differ. A tie goes to the value the
  latest typical run used.
- **By Bot's kind.** *One kill per bot* when every bot the kill table names
  has exactly one kill row. It is *time-scored* when the run's own version
  has a pace basis, and *accuracy only* otherwise. *Many kills per bot* when
  any bot has two kill rows or more, even if another bot has only one. No
  basis covers two cases `get_version_pace_basis` answers alike: a version
  known not to be time-scored, such as PGT's, and one the app can't tell
  about, such as any version played only before KovaaK's 3.9.0, which
  brought the performance files. In neither does the app know what a bot's
  time measures, a phase's fixed length or a split, so no time is shown
  rather than one that may mean nothing. The subtitle says when a one-kill
  bot's time is shown, not which case the run is.
- **Per bot.** For each bot named in the run's kill table: its kills; its
  accuracy, its kill rows' hits over their shots; its time, the sum of its
  kills' gaps since the kill before, the first kill's from Challenge Start;
  and its time per kill, that time over its kills. Its typical is the
  median of each over the typical runs that name it and have that figure.
  A bot no typical run names has empty Typical and Difference cells.
- **When the times are known.** A gap is taken between two times of day.
  One that comes out more than 12 hours below zero crossed midnight and
  gains a day. Any other gap below zero means the file's times disagree.
  A run's times are unknown when its file has no usable `Challenge Start:`,
  when a gap disagrees, or when it was paused (`Pause Duration:` above zero
  or unreadable): the file gives the paused time but not which gap it fell
  in. A run with unknown times keeps its kills and accuracy, its time cells
  are empty, and a line under the subtitle says why. A typical run with
  unknown times counts toward each bot's typical accuracy and not toward its
  times.

### Settings card values

The card shows the value the way the rest of the app does where one
exists.

| Card | Shows |
|---|---|
| Sensitivity | The run list's Sensitivity text, such as `45.0 cm/360`, with its recorded-setting suffix on a converted run |
| Vertical sensitivity | `Same as horizontal` when equal, else the value and scale |
| DPI | `DPI` as written, such as `1600` |
| FOV | `FOV` and `FOVScale`, such as `103 Overwatch` |
| Crosshair | `Crosshair` without `.png`, such as `0snowi_nicedot` |
| Crosshair scale | `Crosshair Scale`, such as `1.6` |
| Hide gun | `Yes` or `No` |
| Resolution | `Resolution` as written, such as `3840x2160` |
| Resolution scale | `Resolution Scale` as a percentage, such as `100%` |
| Frame cap | `Max FPS (config)`, such as `999` |
| Input lag | `Input Lag` as written |

### Reading the run

- The run's stats file is read whole when the run opens, by a new reader
  that returns its fields in file order, its weapon rows and its kill
  table. It runs on the server and keeps nothing.
- The typical runs' files are read by the same reader, for By Bot and
  Settings: up to 20 files, of a few kilobytes each.
- Whether a performance file exists comes from the listing the
  time-scored check already keeps.
- The tables are sent as data to a component that draws them, not as one
  Dash component per cell. A kill table runs to hundreds of rows on some
  scenarios, and the renderer slows with component count.

### Copy

Every string the run adds. Rules 1 to 9 apply. Section headings and table
column headers take Title Case, and everything else sentence case.

| Where | String |
|---|---|
| Header, small line | `{scenario} · ended {date, time}`, in the app's absolute format with seconds, such as `Aug 6, 2026, 10:56:36 PM` |
| Header, title | `Run {n} · {session start} session` |
| Close button | `Close`, with an `Esc` key hint; accessible name `Close` |
| Reference line, known | `Typical comes from your {N} runs before this session, played on {date}.`, or `played from {date} to {date}.` in place of the last part when they span more than a day |
| Reference line, first session | `This is the scenario's first session, so there's no typical run to compare with yet.` |
| Reference line, too few | `There's no typical run for this run's session yet: it had {N} runs before it, and a typical score needs 10 runs across 2 or more sessions, or 20 in one session.` (`1 run` when N is 1) |
| Tile labels | `Score`, `Accuracy`, `Shots fired`, `Reloads`, `Time` |
| Tile second line | `Typical {value} · {difference}`, the difference signed, in ` pts` for Accuracy and ` s` for Time |
| Tile and By Bot typical hover | `Median of {n} of your {N} typical runs`, or `Median of your {N} typical runs` when every one counts |
| By Bot heading | `By Bot` |
| By Bot subtitle, many kills | `Each kill's time runs from the kill before it, so it includes finding the bot.` |
| By Bot subtitle, time-scored | `Each bot is one kill, in a set order, so these are the run's splits. A kill's time runs from the kill before it.` |
| By Bot subtitle, accuracy only | `Each bot is one kill, so its time is shown only when the app knows this run was scored by completion time.` |
| By Bot subtitle, added in play order | `Listed in the order the run plays them.` |
| By Bot subtitle, added with typical runs | `Typical is each bot's median over your typical runs. Difference is this run minus typical, in percentage points (pts) for accuracy.` |
| By Bot line, no start time | `Times aren't shown because this run's file has no start time.` |
| By Bot line, times disagree | `Times aren't shown because this run's file has times out of order.` |
| By Bot line, paused | `Times aren't shown because this run was paused, and its file doesn't say when.` |
| By Bot column headers | `Bot`, `Kills`, `Time per Kill`, `Time`, `Accuracy`; under each figure `This Run`, `Typical`, `Difference` |
| Settings heading | `Settings` |
| Settings subtitle | `A setting that differs from its most common value over your typical runs is marked, with that value under it.` |
| Card labels | `Sensitivity`, `Vertical sensitivity`, `DPI`, `FOV`, `Crosshair`, `Crosshair scale`, `Hide gun`, `Resolution`, `Resolution scale`, `Frame cap`, `Input lag` |
| Card values the app words | `Same as horizontal`, `Yes`, `No`, `Not recorded` |
| Card typical line | `Typical {value}` |
| Card hover, unmarked | `{value}`, so a value cut short can be read whole |
| Card hover, marked | `{value}` then `Typical {value} · on {n} of your {N} typical runs` |
| Card hover, not recorded | `The run file doesn't have this setting. Older versions of KovaaK's didn't record it.` |
| Everything Recorded summary | `Everything Recorded` |
| Everything Recorded subtitle | `The run file as KovaaK's wrote it, grouped by kind.` |
| Group headings | `Result`, `Other Counters`, `Run`, `Settings`, `Other`, `Files`, `Weapons`, `Kills` |
| A folded group | `All zero: {field names}` |
| Files rows | `Run file`, `Performance file`; values `Found`, `None` |
| No kill table | `This run's file records no kills.` |
| A file that can't be read | `This run's file couldn't be read. See data/logs/debug.log.` |

On screen a stats file is a run file, as the glossary has it, and the game
is KovaaK's. Field names, weapon names and kill-table headers are
KovaaK's own, shown as written. The score line's badge and comparison are
the latest-run card's strings, unchanged.

### Terms

The entries the shipping PR adds to the glossary, in its form. Run viewer
goes under The Run History page, and Typical runs under Scores and
notifications.

#### Run viewer

The view of one run that takes the place of Run History's chart until it
is closed: the run's score against its typical runs, By Bot, its settings,
and everything its stats file recorded.

- On screen: no name of its own. Its sections are By Bot, Settings and
  Everything Recorded, and its button is Close.
- In code: `run_viewer`.

#### Typical runs

A run's typical runs are the runs behind its typical at session start: up to
20 runs of the scenario before the run's session. A figure's typical is its
median over the ones that have the figure, and a setting's is its most
common value among them. A run has none while its typical at session start
is unknown.

- On screen: `Typical` on the run viewer's tiles, cards and By Bot columns,
  and `your typical runs` in its copy.
- Not the runs behind the Typical score card's value, which follows every
  run.

### Decisions this changes

- **[2026-10-23, linked hover](../decision_log/2026/2026-10-23-run-history-links-chart-and-list-runs-on-hover.md)**
  and **[2026-10-24, compact tooltips](../decision_log/2026/2026-10-24-chart-point-tooltips-show-score-time-and-run-numbers.md)**
  kept click actions out of scope, and the second accepted a navigation gap
  "until a click feature exists". A click now opens a run. Hover keeps
  every statement both make.
- **[2026-10-05, pace](../decision_log/2026/2026-10-05-time-scored-scenarios-are-measured-by-pace.md)**
  says "No completion time is shown anywhere", and kept Run History and a
  per-bot breakdown out of its scope. The run viewer's Time tile shows the
  completion time, `C − s`, on a time-scored version, and By Bot shows each
  bot's split. The entry gains a note naming both. The run_history spec's
  Time-scored scenarios section changes with it.
- **The roadmap's Future item** "Per-bot breakdown on time-scored kill
  scenarios" ships as part of By Bot, for every multi-bot scenario.

### Alternatives rejected

- **A page of its own with tabs** (Overview, Bots, Timeline, All data), the
  first concept, from the Codex side. A page loses the list beside the run
  and the chart's state. Tabs hide the sections from each other, and the
  page is short enough to read top to bottom.
- **A scenario-level per-bot view,** in Scenario Stats or as a chart mode.
  It would clutter a page most scenarios don't need it on (80% name one
  bot or none), and the measures it would rest on aren't steady (RV4).
- **Notices for a changed setting, a low fire held and another version**
  (v8 to v11). Each came and went between runs. The setting notice became
  the typical line in the card, and the others went (RV5, S9).
- **Showing a setting only when it changed** (v7 to v10). It made the
  grid change shape between runs and needed a list of which settings
  always show.
- **Dropping the Shots fired and Reloads tiles** (proposed after v10). The
  maintainer chose to show everything that applies, rather than send the
  player to the list's Columns menu.
- **One By Bot table shape for every scenario.** It would show Kills of 1
  and a time per kill that never changes on PGT and Air.
- **A phases subtitle where a version is known not to be time-scored.** The
  time-scored service tells that case apart only internally, and a scenario
  that isn't time-scored still needn't play each bot as a fixed-length
  phase (RV4).
- **A lead line naming the bot this run lost the most on,** with its row
  tinted (v7 to v12). No ranking of the bots says where the score went
  (RV4).
- **A Crosshair color card with a warning on it.** It would still draw a
  black square for a green crosshair on every run since Dec 2024, beside a
  line saying not to believe it (RV5).

## Out of scope

The shelf from the design discussion, with what would bring each back:

- **S1. A timeline from the performance file.** Score through the run
  beside the typical shape, with the dips below the typical runs' worst
  marked by clock time for video review. It is the costliest item: a
  per-second reader, 20 files for the typical shape, and rules for a dip.
  The files exist only since KovaaK's 3.9.0 (Apr 30, 2026), and the
  maintainer's lean is slight. Every scenario's runs end weaker than they
  start, by 5 to 9% in the last third on RawControlSphere, SmoothBot and
  VoxTS, so a timeline needs the typical shape beside it. Revisit if "when
  in the run did it go wrong" keeps coming up.
- **S2. A Compare with menu,** with the PB the run chased and the previous
  run. RV2 has what it would take. Revisit when a question comes up that
  the typical runs can't answer.
- **S3. A scenario-level "practice this bot" verdict.** No measure tried is
  both steady and meaningful (RV4). Revisit with a measure that separates
  a bot hard by design from one the player is weak on, such as other
  players' per-bot figures, which nothing offers today.
- **S4. Per-bot history,** to see whether a bot is improving. It has the
  same noise problem as S3.
- **S5. A kill-time chart on time-scored scenarios.** By Bot already holds
  the splits where each bot is one kill.
- **S6. Older run and Newer run buttons.** The list beside the run already
  steps between runs.
- **S7. Keyboard stepping and copy support.** Esc, and Enter or Space on a
  Run row, are in (RV1). Arrow keys belong to the list's grid.
- **S8. A link to a run,** with the run in the address and Back closing it.
  Revisit if runs need to be shared or bookmarked.
- **S9. Fire held.** A tile for how much of the run the fire button was
  down, on scenarios fired through (a median of 8 shots a second or more),
  with a hover giving the accuracy that counts the time let go as misses.
  Letting go off target does raise accuracy: over 2,794 such runs with 20
  before them, the 1.8% that fired 2 or more points less than usual scored
  2.8 to 3.7 points more accuracy than usual, against 0.8 to 1.1 for the
  rest, mostly on target switching with automatic weapons. But the file
  records neither the button nor the fire rate, so the figure's 100% was
  the scenario's fastest-firing run. The run length's whole-second end
  moves it 1 to 2 points, and on a time-scored run it moves with the travel
  between bots. The hover's accuracy then read below the real one even on a
  run held throughout. Damage Done over Damage Possible is no way around
  it, since Damage Possible falls with the shots too. Revisit if a file
  records the fire rate or how long fire was held.
- **S10. A Crosshair color card.** KovaaK's writes the field wrong (RV5),
  and the maintainer is reporting it. Revisit when a fixed version ships.
  The card would then mark a change only when both values come from fixed
  versions, so the fix doesn't read as the player changing color, and runs
  from before the fix would say their value isn't the color used.

Also out: a fix for the game's crosshair color line, which the maintainer
is reporting to KovaaK's, and any change to the run list, the chart or the
cards beyond the click that opens a run.

## Delivery plan

Stated intent, not a contract. A PR that moves a boundary says so in its
description. The proposal was ratified on 2026-10-30, so PR 1 can start once
this proposal merges.

1. **Read a run whole.** A reader for a stats file's three parts, returning
   its fields in file order, its weapon rows and its kill table, with the
   figures RV2 to RV5 derive from them: medians over typical runs with
   their counts, the time per version, the most common setting, the table's
   kind and the per-bot figures with their timing rule. Pure functions, no
   UI. Tests build stats files of each era (no DPI line, no
   `Challenge Start:`, a pause, no kill table, many kills per bot, one kill
   per bot).
2. **The run viewer.** Opening from a Run row, by click or key, a point or
   a star, Close and Esc with focus, the header, score line and reference
   line, the tiles, Settings and Everything Recorded. It updates the
   run_history spec. Depends on PR 1.
3. **By Bot.** The table, its kinds, its sorting and its unknown-times
   lines. It ships the proposal: decision-log entries, the run_history
   spec, the glossary's Terms, the roadmap and product inventory, the pace
   entry's note, and the proposal's deletion. Depends on PR 2: the table
   goes between the tiles and Settings.

PR 1 is pure and fully specified, so it suits any implementer. PRs 2 and 3
touch the page's callbacks and its traps. PR 3's figures come with PR 1, so
it needs no new reader.

## Testing

- **PR 1.** Unit tests on built stats files, in the style of
  `test_data_service_extract.py`: every field read in order, weapon rows,
  the kill table, a missing line read as missing and never as zero, and
  each figure against a hand-worked value. Each of these gets a case: a tie
  for the most common setting, and a bot one typical run names and one none
  does. Time gets a run on a version with no pace basis and typical runs
  on another version. Bot times get a run with no `Challenge Start:`, a
  paused run, a kill after midnight, and a first kill before
  `Challenge Start:`.
- **PR 2.** Callback tests for opening, switching and closing, and for a
  selection change closing the run. A browser test in the style of
  `test_run_history_hover_browser.py` covers these: a point click and a row
  click, Enter and Space on a focused Run row, and focus on Close and back.
  Close and Esc, and Esc with the scenario field focused or the note dialog
  open. The same point clicked, closed and clicked again: Dash drops a
  repeated identical `clickData`, so the callback has to clear it. The
  chart's zoom and its width surviving a close: a graph hidden and shown
  keeps its hidden size until something resizes it. A live check at 2560 and
  1920, light and dark, on the six scenarios the mockup used: VT Popcorn
  Intermediate S5, SmoothBot Perfected, VT PGT Intermediate S5, Air
  CELESTIAL No UFO Medium, VoxTS Click Medium and RawControlSphere.
- **PR 3.** The three kinds on built files, also a many-kills run where one
  bot has one kill and a one-kill run on a version with no pace basis,
  which shows accuracy alone under the accuracy-only subtitle. The
  default orders, each header's three sort states by click and by key, and
  the three unknown-times lines.
- **Every PR.** The standard gates in AGENTS.md, and an instance of the
  build for the maintainer, as AGENTS.md describes.
