# Run History Opens Any Run And Measures It Against Its Typical Runs

Status: Proposed
Date: 2026-10-30

## TL;DR

Run History lists and charts a scenario's runs but can't show one: a run's
settings, how it went against each bot, and most of what its stats file
recorded stay out of reach. This proposal opens any run from the run list or
the chart in the chart's place, and measures it against the runs behind its
typical score at session start. The run shows its score tiles, a By Bot table
when it names two bots or more, all twelve of its settings with the changed
ones marked, and everything the stats file recorded, closed by default. Close
or the Esc key brings the chart back as it was left.

## Decisions needed

Six rows, RV1 to RV6. **Nothing is ratified.** Each row carries the
maintainer's lean from the design discussion of 2026-10-25 to 2026-10-30,
worked out on twelve versions of a mockup built from their own stats, at
2560 and 1920 wide, in light and dark (local only, under the main
checkout's `ignore/mockups/run-viewer/`). A lean is not a ruling.
Reviewers may challenge any row, and anything in [Design](#design), which
is author-owned.
The ideas the discussion set aside are in [Out of scope](#out-of-scope), each
with what would bring it back.

### RV1. A run opens in the chart's place, and Close or Esc closes it

Status: open. The maintainer's lean, 2026-10-29, on the author's proposal to
keep the open run out of the address: "agree, but I also vote to make a
keyboard shortcut to make navigation a bit more seamless."

The material consequence: the browser's Back doesn't close a run. It leaves
the page, as it does after any change on Run History today, and no link
reopens a run.

**Recommendation: a click on a Run row of the run list, in either view, or
on a run point or PB star of the chart, opens that run in the chart
column's place, with the list beside it. A click on another Run row switches
to that run. Close, or Esc, brings back the chart as it was left: its mode,
zoom, ranges and hidden traces. Esc is left alone while a text field has
focus or a dialog, menu or dropdown is open. The open run is not written to
the address and adds no history entry.**

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
- **Hover is unchanged.** The 2026-10-23 and 2026-10-24 hover entries kept
  click actions out of scope, and the second accepted that an old run's
  accuracy needs the list "until a click feature exists". This is that
  feature ([Decisions this changes](#decisions-this-changes)).

### RV2. The run is measured against its typical runs, with no Compare with menu

Status: open. The maintainer's lean, 2026-10-30, after a write-up of what a
menu would take: "Yes, keep it shelved."

The material consequence: the page can't answer "what did my PB run do
differently?" except by opening the PB run, whose figures read against its
own typical runs.

**Recommendation: everything compares with one set of runs, the run's
typical runs: the runs behind its typical score at session start, up to 20
runs of the scenario before the run's session, known from 10 runs over 2
sessions. A tile's typical is the median of its figure over those runs, a
setting's is its most common value, and a bot's is its median over the
typical runs that name it. One line under the score names the runs: `Typical
is the median of your 20 runs before this session, played from Sep 27, 2025
to Oct 6, 2025.`**

- **One yardstick for the whole page, and the card's.** The latest-run card
  already measures a run against the typical score at session start
  ([2026-10-25](../decision_log/2026/2026-10-25-the-latest-run-card-measures-the-run-against-the-typical-score-at-session-start.md)).
  The Score tile's typical is the same value, the median of the same runs:
  over the mockup's six scenarios, the median of the 20 runs before each
  run's session equals the card's typical score at session start on every
  run, up to rounding. The roadmap's principles judge skill by the typical
  run.
- **What a menu would take.** It would swap the yardstick of every section:
  each tile's second line, each card's typical line, By Bot's middle column
  and its lead line, and the line under the score. The arithmetic is the
  same with a set of one run. The cost is in decisions and states:
  - Which PB. It has to be the one the run chased, not today's, which
    disagrees with the score line's `% of PB` on 39 of 55 Popcorn runs and
    69 of 86 PGT runs. On a run that set a PB, it is the PB it beat.
  - The first run has neither a PB before it nor a previous run.
  - Whether the choice sticks across runs, scenarios and reloads.
  - Every `Typical` label and hover count, worded for each option.
  - Noise. A median of 10 to 20 runs moves far less than one run, so By
    Bot's lead line against a single run would name a different bot more
    often, by chance.
- **When there are no typical runs,** the line says why, in one of two
  forms ([Copy](#copy)). Every Typical and Difference figure is then left
  out, and no setting is marked.

### RV3. The tiles: Score, Accuracy, Shots fired and Reloads always, then Time and Fire held by kind

Status: open. The maintainer's lean, 2026-10-29: "I now vote for always
showing them, regardless of the type of run. Otherwise the user has to
adjust columns in the right side panel, when the intent of the Run Viewer
UI is to show everything applicable to the run." Fire held was their idea
(2026-10-29), and the tile won over a notice shown only on a low run
(2026-10-29).

The material consequence:
- Time is the first place the app shows a completion time
  ([Decisions this changes](#decisions-this-changes)).
- Fire held is a figure the app derives. The stats file doesn't hold it.
- On a tracking scenario, Shots fired and Fire held show the same count two
  ways.
- Reloads reads 0 on scenarios with unlimited ammo.

**Recommendation: a row of tiles, in this order: Score, Accuracy, Shots
fired, Reloads, then Time on a time-scored scenario and Fire held on a
tracking scenario. Each shows the run's value over `Typical {value} ·
{difference}`. Accuracy stays KovaaK's hits over shots, and Fire held's
hover gives the accuracy that counts the time let go as misses.**

- **The same place on every scenario.** The four every run has come first,
  so a tile never moves between scenarios. Score and Accuracy differences
  are green when better and red when worse. Shots fired's is uncolored,
  since more shots is neither. Reloads' is green when fewer.
- **Time** is the clock's constant less the score, `C − s`, on a scenario
  the app already recognizes as time-scored from its performance files. It
  is exact. The run length the stats file gives is up to 1.7% off on a
  60-second run, because the file name's end time is in whole seconds. A
  faster time is green.
- **A tracking scenario** is one whose runs' median is 8 shots a second or
  more. Over 810 of the maintainer's scenarios, 325 have a median
  under 5 a second, none between 5 and 10, and 485 at 10 or more: 7 at 10
  to 15, such as B180T and bounceTS, target switching with automatic weapons
  at 35 to 60, and most tracking at 60 to 110. A line at 15 read B180T, at
  13, as clicking.
- **Fire held** is the run's shots a second as a share of the scenario's
  highest run. The game doesn't record the fire rate, so the scenario's best
  run stands in for fire held throughout. Letting go of fire off target
  raises accuracy, as the maintainer suspected. Over 2,794 tracking runs
  with 20 runs before them, 95% held within 1.15 points of their usual
  share. The 1.8% held 2 or more points less, and they scored 2.8 to 3.7
  points more accuracy than usual, against 0.8 to 1.1 for the rest. It was
  mostly target switching with automatic weapons: Pokevox,
  StaticSwitchingVox and beanTS.
- **The hover's accuracy** is the hits over the hits the run would have had
  the chance at with fire held throughout: accuracy times fire held, which
  letting go can't raise. Damage Done over Damage Possible can. Damage
  Possible is shots fired times the weapon's damage per shot, so it falls
  with the shots just as hits over shots does. Over 9,280 runs it agrees
  with hits over shots within 0.5 points on 89%. The other 11% differ by
  damage per hit, not by letting go: 1w2ts Angelic reads exactly half.
- **A tile, not a notice.** v10 showed a notice only when a run held fire 2
  or more points less than typical. It would have appeared on 49 of the
  2,794 tracking runs. The tile needs no threshold, since its difference
  shows a drop, and it doesn't come and go between runs.

### RV4. By Bot: each bot against its own typical, with no verdict on which to practice

Status: open. The maintainer's leans, 2026-10-29: play order where it is
fixed, rows that highlight on hover, the section above Settings, This Run,
Typical and Difference columns, every column sortable, and no By Bot for a
single bot.

The material consequence: the page names the bot this run lost the most on,
but never which bot to practice, and nothing else in the app answers that.

**Recommendation: a By Bot table when the run's kill table names two bots
or more, one row per bot. Its figure follows what the score is made of:
time per kill where bots come many times, time per bot where each bot is
one kill of a time-scored run, and accuracy alone where each bot is one
phase of a fixed-length run. The figure and accuracy each show This Run,
Typical and Difference. Rows start in play order where each bot is one
kill, and in name order otherwise. Each header sorts ascending, then
descending, then back. A lead line names the bot this run lost the most on,
and its row is tinted.**

- **Reach.** 175 of the 866 scenarios the maintainer ever played name two
  bots or more (20%). Of the 54 played in the last 90 days with 10 runs or
  more, 14 do: 26% of those scenarios and 20% of their runs. Tracking
  scenarios have an empty kill table.
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
- **One bot shows no table.** It would repeat the tiles. VoxTS's kills
  equal its score, and its time per kill is 60 seconds over the score. Its
  typical accuracy would also read 0.18 points off the tile's, because the
  kill table leaves out shots fired after the last kill.
- **Names are taken as they come.** FlyTS's Fly Bot and Fly Bot 2 have
  median TTKs of 1.041 and 1.040 seconds and still get a row each.

### RV5. Settings: all twelve cards on every run, a changed one marked with its typical value

Status: open. The maintainer's leans:
- 2026-10-29: cards of one size, with the count on hover.
- 2026-10-29, on show-or-hide rules: "keep things simple and just show all
  the cards. We can always consider trimming things later."
- 2026-10-29, on a summary of changed settings: "I'd prefer that this info
  lived inside the respective card."
- 2026-10-30: keep Crosshair color and its color square, report the game's
  bug to KovaaK's developers, and reconsider only if it is never fixed.

The material consequence: since KovaaK's 3.7.0, the Crosshair color card
shows a value that isn't the tint the player used, and its color square
draws it. Six cards that rarely change take a row of their own.

**Recommendation: twelve cards in two rows of six, the same on every run.
The first row is the aim setup: Sensitivity, DPI, FOV, Crosshair, Crosshair
scale and Crosshair color. The second is set once: Vertical sensitivity,
Hide gun, Resolution, Resolution scale, Frame cap and Input lag. A card
whose value differs from its most common value over the typical runs is
tinted and shows `Typical {value}` under its own, with the count on hover.
A value the stats file doesn't have reads `Not recorded` and is never
marked.**

- **What changes in practice.** All 9,280 of the maintainer's runs, from
  2019-07-14 to 2026-10-29:
  - Never changed: Hide Gun, Input Lag.
  - Unchanged for the last year: DPI, Resolution, Resolution Scale (one run
    at 50% on Oct 9, 2025), Crosshair, Crosshair Color.
  - Changed in the last year: sensitivity 359 times, Crosshair Scale 105,
    Max FPS 3, FOV 2.
- **Why all twelve.** Show-or-hide rules multiply states and edge cases, in
  the maintainer's words, and a grid that never changes shape reads the
  same on every run. Any of the twelve can change a run, which is why the
  rarely changed six stay on screen rather than living only in Everything
  Recorded.
- **Why in the card.** The mark and the typical value sit where the eye
  already is. v8 to v11 also put a notice under the tiles; this row drops
  it. At 2560 by 1320 the cards are on screen without scrolling in every
  mocked state. At 1920 by 960 their second row is cut off on the three
  multi-bot scenarios, and on Air all of Settings is below the fold.
- **`Not recorded`.** The 570 runs from 2019-07-14 to 2021-07-20 have no
  DPI, Resolution or Resolution Scale line.
- **The crosshair color bug.** In-game tint 00FF00 is written `000100FF`,
  and a test run tinted 147245 was written `000000FF`. Before Dec 15, 2024,
  the field held a six-digit color (FFFFFF, FFFF00, 00FF00). Every run
  since, 8,714 of them, reads `000100FF`. The weapon row's crosshair color
  column is empty. A fix in the game would correct new files only. After
  it, new runs would read as a changed color against typical runs written
  before it, until all the typical runs are fixed ones.
- **Not cards.** The scenario's version: the player can't change it, and 1
  run in 3,589 was on another version than most of the 20 runs before it.
  It is in Everything Recorded. The performance file's time scale is the
  scenario's own, not a setting: it differs from 1 in 483 files, and no
  scenario of 248 ever has two.

### RV6. Everything Recorded: the whole stats file, closed, grouped by kind

Status: open. The maintainer's leans, 2026-10-29: everything in the stats
file, organized and low priority, collapsed or at the bottom. On
2026-10-30: "Yes, keep folding."

The material consequence: the page shows fields that answer no question
today, such as Midairs and MBS Points, under the game's own names, behind a
closed section.

**Recommendation: a closed section at the bottom. The fields are grouped as
Result, Other Counters, Run and Settings, then Other for any field the app
doesn't know, so a game update never hides one. A group whose fields are
all zero folds to one line. Files names the stats file and whether a
performance file was found. Weapons shows the weapon rows, and Kills the
kill table, both as written.**

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
  It is known from 10 runs over 2 sessions, and `None` when the scenario
  has no run before the session.
- The app tells a time-scored scenario by its performance files'
  constant (`get_pace_basis`), which gives `C − s`.
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

1. **The header.** A small line names the scenario, when the run ended and
   its length. Under it the title gives the run's number and session, as
   the list does: `Run 2 · Aug 6, 10:23 PM session`. **Close** sits at the
   right, with a small `Esc` key hint.
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
  point or a PB star of the chart, in any chart mode. A Session or Scenario
  row keeps its own click, which opens and closes the group. Hover linking
  is unchanged.
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
  Accuracy's difference is in percentage points.
- **Time** is `C − s` for the run and for each typical run, shown as
  `m:ss.s`, with the difference in seconds.
- **Tracking.** The median, over every run of the scenario with a run
  length, of shots fired over run length is 8 or more.
- **Fire held** is a run's shots a second over the highest of the scenario's
  runs, as a percentage. It is worked out again on each open, so an old
  run's value can drop after a later run fires faster.
- **A setting's typical** is its most common displayed value over the
  typical runs that have one. A card is marked when the run has a value,
  there is a typical, and the two differ. A tie goes to the value the
  latest typical run used.
- **Per bot.** For each bot named in the run's kill table: its kills; its
  time, the sum of its kills' gaps since the kill before, the first kill's
  from Challenge Start; its time per kill, that time over its kills; and
  its accuracy, its kill rows' hits over their shots. Its typical is the
  median of each over the typical runs that name it. A bot no typical run names has
  no typical. The lead line takes the bot with the largest loss against
  its typical in the section's figure. A loss that rounds to zero at the
  figure's shown precision isn't a loss.

### Settings card values

The card shows the value the way the rest of the app does where one
exists.

| Card | Shows |
|---|---|
| Sensitivity | The run list's Sensitivity text, such as `45.0 cm/360`, with its recorded-setting suffix on a converted run |
| DPI | `DPI` as written, such as `1600` |
| FOV | `FOV` and `FOVScale`, such as `103 Overwatch` |
| Crosshair | `Crosshair` without `.png`, such as `0snowi_nicedot` |
| Crosshair scale | `Crosshair Scale`, such as `1.6` |
| Crosshair color | `Crosshair Color` as written, after a square of its first six digits |
| Vertical sensitivity | `Same as horizontal` when equal, else the value and scale |
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
| Header, small line | `{scenario} · ended {date, time} · {run length} long` (run length as the app formats elapsed time, such as `1 min`; the part is left out when the run has no length) |
| Header, title | `Run {n} · {session start} session` |
| Close button | `Close`, with an `Esc` key hint; accessible name `Close` |
| Reference line, known | `Typical is the median of your {N} runs before this session, played on {date}.`, or `played from {date} to {date}.` in place of the last part when they span more than a day |
| Reference line, first session | `This is the scenario's first session, so there's no typical run to compare with yet.` |
| Reference line, too few | `There's no typical run for this run's session yet: it had {N} runs before it, and a typical score needs 10 runs from 2 sessions.` (`1 run` when N is 1) |
| Tile labels | `Score`, `Accuracy`, `Shots fired`, `Reloads`, `Time`, `Fire held` |
| Tile second line | `Typical {value} · {difference}`, the difference signed, in ` pts` for Accuracy and Fire held and ` s` for Time |
| Fire held hover | `How much of the run the fire button was down, measured against your run of this scenario that fired the most shots a second. Letting go when off target raises accuracy. Counting the time you let go as misses, this run's accuracy is {x}%.` |
| By Bot heading | `By Bot` |
| By Bot subtitle, many kills | `Each kill's time runs from the kill before it, so it includes finding the bot.` |
| By Bot subtitle, time-scored | `Each bot is one kill, in a set order, so these are the run's splits. A kill's time runs from the kill before it.` |
| By Bot subtitle, phases | `Each bot is one timed phase of the run, so accuracy is what tells them apart.` |
| By Bot subtitle, added in play order | `Listed in the order the run plays them.` |
| By Bot subtitle, added with typical runs | `Typical is each bot's median over your typical runs. Difference is this run minus typical, in percentage points (pts) for accuracy.` (without its last clause when there is no accuracy column) |
| By Bot lead, a loss | `This run lost the most {time / accuracy} on {bot}: {difference}{ per kill} against your typical for that bot.` (bot in bold) |
| By Bot lead, no loss | `Every bot was at or better than your typical for it.` |
| By Bot column headers | `Bot`, `Kills`, `Time per Kill`, `Time`, `Accuracy`; under each figure `This Run`, `Typical`, `Difference` |
| Settings heading | `Settings` |
| Settings subtitle | `A setting that differs from your typical runs is marked, with the typical value under it.` |
| Card labels | `Sensitivity`, `DPI`, `FOV`, `Crosshair`, `Crosshair scale`, `Crosshair color`, `Vertical sensitivity`, `Hide gun`, `Resolution`, `Resolution scale`, `Frame cap`, `Input lag` |
| Card values the app words | `Same as horizontal`, `Yes`, `No`, `Not recorded` |
| Card typical line | `Typical {value}` |
| Card hover, unmarked | `{value}`, so a value cut short can be read whole |
| Card hover, marked | `{value}` then `Typical {value} · on {n} of your {N} typical runs` |
| Card hover, not recorded | `This run's stats file doesn't have this setting. Older versions of the game didn't record it.` |
| Everything Recorded summary | `Everything Recorded` |
| Everything Recorded subtitle | `The stats file as the game wrote it, grouped by kind.` |
| Group headings | `Result`, `Other Counters`, `Run`, `Settings`, `Other`, `Files`, `Weapons`, `Kills` |
| A folded group | `All zero: {field names}` |
| Files rows | `Stats file`, `Performance file`; values `Found`, `None` |
| No kill table | `No kill table: this scenario records no kills.` |
| A file that can't be read | `This run's stats file couldn't be read. See data/logs/debug.log.` |

Field names, weapon names and kill-table headers are the game's own,
shown as written. The score line's badge and comparison are the latest-run
card's strings, unchanged.

### Terms

The entries the shipping PR adds to the glossary, in its form. Run viewer
goes under The Run History page, Tracking scenario under Play beside
Time-scored scenario, and Typical runs and Fire held under Scores and
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
median over them, and a setting's is its most common value among them. A
run has none while its typical at session start is unknown.

- On screen: `Typical` on the run viewer's tiles, cards and By Bot columns,
  and `your typical runs` in its copy.
- Not the runs behind the Typical score card's value, which follows every
  run.

#### Tracking scenario

A scenario whose runs fire continuously: the median of its runs' shots a
second is 8 or more. A run of one shows Fire held.

- On screen: not named.

#### Fire held

How much of a run the fire button was down, as the run's shots a second
against the highest of its scenario's runs. Shown only on a tracking
scenario, because the stats file doesn't record the fire rate.

- On screen: `Fire held`.

### Decisions this changes

- **[2026-10-23, linked hover](../decision_log/2026/2026-10-23-run-history-links-chart-and-list-runs-on-hover.md)**
  and **[2026-10-24, compact tooltips](../decision_log/2026/2026-10-24-chart-point-tooltips-show-score-time-and-run-numbers.md)**
  kept click actions out of scope, and the second accepted a navigation gap
  "until a click feature exists". A click now opens a run. Hover keeps
  every statement both make.
- **[2026-10-05, pace](../decision_log/2026/2026-10-05-time-scored-scenarios-are-measured-by-pace.md)**
  says "No completion time is shown anywhere", and kept Run History and a
  per-bot breakdown out of its scope. The run viewer's Time tile shows the
  completion time, `C − s`, on a time-scored scenario, and By Bot shows each
  bot's split. The entry gains a note. The run_history spec's Time-scored
  scenarios section changes with it.
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
  the typical line in the card, and the others went (RV3, RV5).
- **Showing a setting only when it changed** (v7 to v10). It made the
  grid change shape between runs and needed a list of which settings
  always show.
- **Dropping the Shots fired and Reloads tiles** (proposed after v10). The
  maintainer chose to show everything that applies, rather than send the
  player to the list's Columns menu.
- **Damage Done over Damage Possible as an accuracy that letting go can't
  raise.** It can (RV3).
- **One By Bot table shape for every scenario.** It would show Kills of 1
  and a time per kill that never changes on PGT and Air.

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
- **S7. Keyboard stepping and copy support.** Esc is in (RV1). Arrow keys
  belong to the list's grid.
- **S8. A link to a run,** with the run in the address and Back closing it.
  Revisit if runs need to be shared or bookmarked.

Also out: a fix for the game's crosshair color line, which the maintainer
is reporting to KovaaK's, and any change to the run list, the chart or the
cards beyond the click that opens a run.

## Delivery plan

Stated intent, not a contract. A PR that moves a boundary says so in its
description.

1. **Read a run whole.** A reader for a stats file's three parts, returning
   its fields in file order, its weapon rows and its kill table, with the
   figures RV2 to RV5 derive from them: medians over typical runs, the most
   common setting, tracking, fire held and per-bot figures. Pure functions,
   no UI. Tests build stats files of each era (six-digit and eight-digit
   crosshair color, no DPI line, no kill table, many kills per bot, one
   kill per bot).
2. **The run viewer.** Opening from a Run row, a point or a star, Close and
   Esc, the header, score line and reference line, the tiles, Settings and
   Everything Recorded. It updates the run_history spec. Depends on PR 1.
3. **By Bot.** The table, its kinds, sorting and lead line. It ships the
   proposal: decision-log entries, the run_history spec, the glossary's
   Terms, the roadmap and product inventory, the pace entry's note, and the
   proposal's deletion. Depends on PR 2: the table goes between the tiles
   and Settings.

PR 1 is pure and fully specified, so it suits any implementer. PRs 2 and 3
touch the page's callbacks and its traps. PR 3's figures come with PR 1, so
it needs no new reader.

## Testing

- **PR 1.** Unit tests on built stats files, in the style of
  `test_data_service_extract.py`: every field read in order, weapon rows,
  the kill table, a missing line read as missing and never as zero, and
  each figure against a hand-worked value. The tracking line at 8, a tie
  for the most common setting, a bot no typical run names, and a loss
  that rounds to zero each get a case.
- **PR 2.** Callback tests for opening, switching and closing, and for a
  selection change closing the run. A browser test in the style of
  `test_run_history_hover_browser.py` covers a point click, a row click,
  Close, Esc, Esc with the scenario field focused or the note dialog open,
  and the chart's zoom surviving a close. A live check at 2560 and 1920,
  light and dark, on the six scenarios the mockup used: VT Popcorn
  Intermediate S5, SmoothBot Perfected, VT PGT Intermediate S5, Air
  CELESTIAL No UFO Medium, VoxTS Click Medium and RawControlSphere.
- **PR 3.** The three kinds on built files, the default orders, each
  header's three sort states, and the lead line's two forms.
- **Every PR.** The standard gates in AGENTS.md, and an instance of the
  build for the maintainer, as AGENTS.md describes.
