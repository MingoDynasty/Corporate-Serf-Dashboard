# Run List Columns Proposal

Status: Proposed
Date: 2026-10-21

## TL;DR

A player asked to see each run's FOV in the Run History run list, and the
maintainer wants the list to stay a short panel for picking out a run, not a
column for every figure a stats file holds. This proposal adds three columns
a player can turn on in the list's Columns menu, FOV with its scale among
them, all off to start, so the list looks exactly as it does today until a
player asks for more. The list then grows to fit the columns it shows, never
narrower than today and never so wide that the chart beside it gets too
narrow, and past that it scrolls sideways with its session rows held in view.
The latest-run card keeps today's width as a width of its own instead of
following the list, so a wider list never wraps the top row.

## Decisions needed

Three rows, RC1 to RC3. **Nothing in this proposal is ratified.** Each row is
the maintainer's call from the design discussion of 2026-10-21, which began
with another player's request and went through five mockup versions built on
the maintainer's own runs, two of them shared with that player (the
requester, below). Each row quotes what was said, all on 2026-10-21. A lean
is not a ruling. Where the discussing session presented a point and met no
objection, rather than an explicit yes, the row says "presented, not
answered". Reviewers are invited to challenge any row, and any author-owned
choice in [Design](#design).

One row reverses part of a ratified decision: RC3 asks the maintainer to
supersede the part of T1 of the top row cards proposal that makes the
latest-run card take the run list's width. The rest of T1 stands.

### RC1. Three optional columns, all off to start: FOV with its scale, Reloads, and Avg FPS

Status: proposed.

**The maintainer's calls.** "Avg FPS in the menu, disabled by default."
"Reloads in the menu, disabled by default." Of FOV, asking for the third
mockup: "FOV in the viewer and the Columns menu (off)". On the scale:
"Ideally we include the scale, because I'm not sure if '103' is treated
equally across all scales." It isn't ([The evidence](#the-evidence)). The
tiers behind the row, in the maintainer's words: "1: Probably useful, and we
think this should be the default for most users ... 2: Possibly useful, but
perhaps some users might want to add this to their view ... 3: Probably not
useful, and we don't think it is worth adding clutter to the UI". Tier 1 is
today's columns. FOV, Reloads and Avg FPS are tier 2. Everything else in a
stats file, from Kills and Avg TTK to the crosshair and Overshots, is tier
3: the future Run Viewer's, never the list's.

FOV and Reloads both started in tier 1 that day and moved to tier 2. FOV
moved after the requester's answer: "see it when i open a run. i dont think
most people care about FOV, and the majority of scenarios wont need it."
Reloads moved after mockup v3, which showed it to start and listed its zeros
on most scenarios as an open point. The requester still wants it: "i love
the reloads, ive been playing popcorn & this is a very useful 'stat' to keep
track of".

**Recommendation.** The run list's **Columns** menu gains three entries, each
unchecked to start: Reloads, FOV and Avg FPS, listed with today's Shots Fired
and Sensitivity in the columns' own order and followed, as today, by Median
and best. A checked entry shows its column in both views. Nothing else from
the stats file reaches the list. With every new entry off, the list a player
meets is today's: seven columns, 500px wide.

- **Off, because each is for a player who asks.** FOV is 103 on 9,177 of the
  maintainer's 9,212 runs. Reloads is 0 on every run of 648 of their 810
  scenarios with hit counts. Avg FPS says how the machine ran, not how the
  player aimed.
- **Three new entries reset nobody's choices.** The menu remembers each
  checkbox under its own id, so a new unchecked entry leaves every stored
  choice as it was, as long as its default never changes.
- **How a player finds them:** the Columns menu, where Shots Fired,
  Sensitivity and Median and best already are, and a sentence in the user
  guide's Run History section. Nothing on the page advertises them. Until a
  Run Viewer exists, the Columns menu is the only place FOV shows.

**What choosing differently costs.** Any of the three on to start widens the
default list for every player: Reloads alone takes it to 564px and puts a
column of zeros on four scenarios in five. Offering every field turns the
list into the run's whole file, which the run navigation framing rejects:
the maintainer, "Short and sweet, and solely the information needed to help
identify a run of interest", and the requester, "100%".

### RC2. The list grows to fit the columns it shows

Status: proposed.

**The maintainer's call.** Of the four list widths in the first mockup, they
chose the one that fits its columns ("option 1") over a full-width mode:
"Option 1 can work well for now, while Option 2 can be added on top of
Option 1 later, if/when we have so many columns that we end up hiding the
chart anyways." The requester chose it too: "i really like how much bigger
the right panel is on the 'fits its column' choice". On sorting: "Probably no
sort. I can't yet imagine a use case for sorting besides by timestamp."

**Recommendation.** The list is as wide as the columns it shows need, never
narrower than 500px, and never so wide that the chart beside it drops under
480px. Past that, the list scrolls sideways inside its own box, and its
session rows, scenario rows and the other full-width rows stay whole in view
while the run rows scroll under them. Columns still don't sort. The two
numbers came with the mockup the maintainer chose: presented, not answered.
They, the mechanism, and how the list scrolls are author-owned and argued in
[The width rule](#the-width-rule) and
[Scrolling sideways](#scrolling-sideways).

- **Every column a player turns on is in view at the maintainer's widths.**
  With all three on, the list is 744px, and the chart is 1,543px at 2560 and
  903px at 1920, measured in the real grid.
- **The default page doesn't move.** With every new column off, the list's
  need is today's 500px, so at every width it is today's list.
- **No sort:** the list is a tree of sessions, and a sort would scatter each
  session's rows. A sortable flat table is a separate idea and is not
  proposed.

**What choosing differently costs.** A list held at 500px, scrolling
sideways, starts every column a player turned on out of view, at every
window: at 1920 with all three on, 216px of columns sit past the list's
edge. A full-width mode now would need a second column set and rules for
leaving it, for a case no common column set reaches at 2560.

### RC3. The latest-run card keeps a 500px width of its own

Status: proposed. The width itself was presented, not answered.

**The maintainer's call.** "my initial thought is to remove Latest Run
card's width's dependency, and allow it to size on its own based on the Top
Row along the other cards. Long term we can plan to have a Session Clock or
other useful information. But for now I think this unblocks?" It does: with
the card following the list, a list wider than 500px wraps the top row at
1920 (measured below). The discussing session first suggested a narrower
card sized to its content, about 360px, while Reloads was still on by
default and the default list would have been wider than 500px, so a 500px
card would have missed it anyway. Once Reloads went off by default, it
recommended keeping the card at a fixed 500px. The maintainer didn't reply
to the width itself.

**Recommendation.** The latest-run card keeps 500px, the width it has today,
as a width of its own: the top row's second column is 500px whatever the
list's width. The card and the list line up as today while the list is at
500px, which it is by default. They part only once a player turns a column
on: the list then reaches further left than the card, under the PB card.
This supersedes, in part, T1's "The latest-run card aligns over the run list
instead of filling the remaining width", the 2026-10-12 run-list entry's
shared 500px column, and the spec's "one value sets the list's 500px width
for both" and "The card is 500px wide, the run list's width" (see
[Decisions this changes](#decisions-this-changes)). The rest of T1 stands.

- **Out of the box, nothing changes.** The page every player meets is
  today's, aligned as T1 made it.
- **Nothing needs measuring again.** The card's tallest state was measured at
  500px: 135px holds it. A new width would need that measured afresh.
- **The alternative is a narrower card sized to its own content,** about
  360px, estimated from its longest second line, a new PB's. It would free
  about 140px for the
  first column at every width. At 1920 that room goes to the note card,
  which already grows to 800px. At 1536 it unwraps nothing: the first column
  needs about 1,106px for one line and would have 903px. It would also cut a
  scenario's name in the card's first line sooner, change every player's
  default page, and part the card from the list on every load.
- **A card that fills the room left** would compete with the note card,
  which already flexes from 240px to 800px for that room.

**What choosing differently costs.** Keeping the card on the list's width
wraps the top row at 1920 whenever any column is on, and with it the chart
loses the height of a second card line. A narrower card changes every
player's page for room the first column mostly can't use.

## Problem

### What the app shows today

The run list on Run History is a column to the right of the chart, 500px
wide, and always shown. A run row has seven columns: `#`, Time, Score, the
marks, Accuracy, Shots Fired and Sensitivity. The Columns menu shows or hides
Shots Fired and Sensitivity, both shown to start, and offers Median and best,
off to start. One CSS value sets the list's 500px for both the list's column
and the top row's second column, so the latest-run card sits exactly over the
list ([run_history.md](../specs/run_history.md#the-top-row)).

The six fixed columns take 436px. What is left of 500px, 64px, holds the
list's two borders, a scrollbar's room and the marks column, which flexes:
45px beside a classic scrollbar and 50px where the scrollbar is drawn over
the rows, measured. The stats file records many more figures than the list
shows, and the parser skips the stats file's `Reloads:`, `FOV:`, `FOVScale:`
and `Avg FPS:` lines.

### The request

A player asked to "have the FOV for the run also tracked in the right column
along with the sens, shots, acc score etc", because they "play above 103 very
often in floating heads" and think "around 107-110 is my best spot". The
maintainer didn't want the list to bloat as such requests pile up. The
discussion separated three things:

- **The run list** stays a short "run navigation" panel. The maintainer: "I
  think the better vision is to treat the right panel as essentially a 'Run
  Navigation' panel. Short and sweet, and solely the information needed to
  help identify a run of interest." The requester: "100%".
- **A Run Viewer,** everything about one run with a per-bot breakdown, is a
  later proposal: "Run Viewer as a future proposal, agreed."
- **This proposal** gives the list a few optional columns and the room to
  show them.

### The evidence

All measured on 2026-10-21 on the maintainer's stats files, one player's
data.

- **FOV:** 9,177 of 9,212 runs at 103, 27 at 80, and 8 at 70. Scales:
  Overwatch on 8,366 runs, Valorant on 276, and no `FOVScale:` line on 570
  older files. SmoothBot Perfected's PB, 5,079.14 on Oct 16, was set in a
  block of 8 runs at FOV 70, then the player went back to 103. Nothing on
  today's page shows that. With the FOV column on, the session reads
  `103 Overwatch` on its last run and `70 Overwatch` on the eight before it.
- **FOV numbers mean different things on different scales.** KovaaK's
  settings capture, `resources/sensitivity converter/response.json`, has 41
  scales and 13 FOV definitions, named by codes such as `16ML9`, `4ML3`,
  `vML` and `16MF9`, which KovaaK's doesn't document. Overwatch's slider runs
  from 80 to 103, so a player at 107 to 110 is on another scale, most likely
  one whose slider runs from 60 to 140, such as Apex Legends or Quake/Source
  (inferred: the requester didn't say).
  Worked out from the scales' definitions, not measured: across a 16:9
  screen, an FOV of 103 is about 103° wide on Overwatch, 118° on Apex
  Legends or Quake/Source, and 132° on a vertical scale.
- **Reloads:** nonzero on 162 of 810 scenarios with hit counts (1,624 runs),
  and varying on 112. It follows misses, with a correlation against Accuracy
  of −0.42 to −0.88, and not Shots Fired, from −0.51 to +0.59. On one-hit
  scenarios Score is fully explained by Shots Fired and Accuracy. Reloads
  explains part of a drop in Shots Fired beyond what Accuracy explains on 11
  of the 27 scenarios with 15 or more varying runs, about 2 to 7 shots per
  reload, and nothing on the rest. The most reloads in one run is 22.
- **Avg FPS:** median 676 and first percentile 317 in the 2026-10-17 survey;
  145 to 987 across the 8,642 files that record it. The maintainer judged it
  not worth pursuing for themselves on 2026-10-17, then put it in the menu,
  off, on 2026-10-21.
- **Overshots, the reason it stays tier 3:** recorded on 168 of 573
  scenarios with a kill table, about 19 to 26 per kill on nearly every kill,
  uncorrelated with kill time or shots, and 0 on every Popcorn and PGT kill.
  What it measures is unknown. The requester had asked whether it would show
  "which bot jukes u more".

### Verified facts

Read at `8eda2b6` (PR #400's merge), the base of this proposal, on
2026-10-21. Each was found by name.

- `extract_data_from_file` in `source/kovaaks/data_service.py` reads a stats
  file line by line, in any order. `Reloads:` is in the block before
  `Score:`, and `FOV:`, `FOVScale:` and `Avg FPS:` are after the timing
  lines, where `Sens Scale:` sits. `_optional_field_value` reads an optional
  line and never raises, so a line with no value yet costs that value only.
  The watcher reads a new file a second after it appears.
- `RunData` in `source/kovaaks/data_models.py` says in its docstring when each
  field can be `None`, and that unknown is never read as zero.
- `RUN_LIST_MENU_COLUMNS` and `MEDIAN_AND_BEST_CHOICE` in
  `source/components/run_history_list.py` define the menu. `columns_menu` in
  `source/components/columns_menu.py` renders one persisted checkbox per
  entry, under an id built from the menu's id and the column's, and
  `MenuColumn.shown_by_default` must match the column's initial visibility
  and never change.
- `run_list_column_defs` builds the columns, each but the marks held to one
  width by `_fixed_width`, whose docstring says "The columns add up to the
  list's own width less a scrollbar". The marks column flexes, from 34px.
  `_run_row` builds a run row's fields.
- `assets/stylesheet.css`: `.run-history-page` sets
  `--run-history-list-width: 500px`, and `.run-history-top-row` and
  `.run-history-columns` both take it as their second column. The rule on
  `.run-history-list-grid:has(.ag-body-vertical-scroll.ag-scrollbar-invisible)`
  gives a scrollbar drawn over the rows 12px of room. At a page of 900px or
  less, `@container run-history-page (max-width: 900px)` stacks the list
  above the chart and turns the top row into one wrapping line.
- The grid is dash-ag-grid 35.3.0, AG Grid 35.3.1, with
  `embedFullWidthRows` on so a screen reader reads a session row with the
  runs under it.
- The top row's other cards: the scenario note card flexes from 240px to
  800px, Scenario Stats is 270px and the PB card 300px. PR #401, open at
  `11e0477`, rewrites Scenario Stats' contents and keeps its 270px.

## Design

### What the player sees

**Out of the box, nothing changes.** At 2560, with the Columns menu as it is
today:

```
| dropdowns | Scenario Stats | note card ·········· | PB card |  latest-run card    500 |
| chart                                            1787 |                run list    500 |

  #  Time     Score         Accuracy  Shots Fired  Sensitivity
  9  6:14 PM  4,895.25  ✓     62.55%        6,000  40.0 cm/360
```

**One column on, FOV, at 2560.** The list grows by the column's 116px to
616px, the chart gives the same, and the top row doesn't move:

```
| dropdowns | Scenario Stats | note card ·········· | PB card |  latest-run card    500 |
| chart                                     1671 |                    run list       616 |

  #  Time     Score         Accuracy  Shots Fired  Sensitivity            FOV
  9  6:14 PM  4,895.25  ✓     62.55%        6,000  40.0 cm/360  103 Overwatch
  8  6:01 PM  4,477.9         57.21%        6,001  40.0 cm/360   70 Overwatch
  6  5:58 PM  5,079.14  ✓★    64.89%        6,001  40.0 cm/360   70 Overwatch
```

**All three on, at 2560 and at 1920.** The list is 744px at both. The chart
is 1,543px at 2560 and 903px at 1920. The top row stays one line, 143px tall,
at both: the card keeps its 500px, so the list reaches 244px further left,
under the right part of the PB card.

```
| dropdowns | Scenario Stats | note card ··· | PB card     |  latest-run card    500 |
| chart                            903 |         run list                       744 |
                                       ^ the list's left edge, under the PB card

  #  Time     Score         Accuracy  Shots Fired  Reloads  Sensitivity            FOV  Avg FPS
  9  6:14 PM  4,895.25  ✓     62.55%        6,000        0  40.0 cm/360  103 Overwatch      853
  8  6:01 PM  4,477.9         57.21%        6,001        0  40.0 cm/360   70 Overwatch      878
```

**A window narrow enough that the list scrolls sideways,** 1366 wide with all
three on. The chart stops at its 480px floor, so the list is 613px, and its
columns need 744px. The marks column gives first, from 50px to its 34px
minimum, and the run rows scroll the remaining 103px. The session row stays
whole at either end:

```
at the start                                   scrolled to the end
▾ Oct 16, 5:48 PM            9 of 35 runs      ▾ Oct 16, 5:48 PM            9 of 35 runs
9  6:14 PM  4,895.25 ✓  62.55%  6,000  0  40…    4,895.25 ✓  62.55%  …  103 Overwatch  853
```

Every state measured, with the default column set beside all three:

| Window | Page area | Columns on | List | Chart | Top row | Sideways scroll |
|---|---|---|---|---|---|---|
| 2560 | 2,303 | none new | 500 | 1,787 | 143 | no |
| 2560 | 2,303 | Reloads or Avg FPS / FOV / all three | 564 / 616 / 744 | 1,723 / 1,671 / 1,543 | 143 | no |
| 1920 | 1,663 | none new | 500 | 1,147 | 143 | no |
| 1920 | 1,663 | Reloads or Avg FPS / FOV / all three | 564 / 616 / 744 | 1,083 / 1,031 / 903 | 143 | no |
| 1536 | 1,279 | none new / all three | 500 / 744 | 763 / 519 | 297, as today | no |
| 1366 | 1,109 | none new / FOV / all three | 500 / 613 / 613 | 593 / 480 / 480 | 297, as today | no / no / yes |
| 1280 | 1,023 | none new / any | 500 / 527 | 507 / 480 | 493, as today | no / yes |
| 1200 | 943 | none new / any | 500 / 500 | 427 / 427 | 493, as today | no / yes |
| 1100 | 843, stacked | any | 843, above the chart | 843 | 297, as today | no |

The top row's height never changes with the columns. At 1536 and narrower
the PB card is already on a second line today, and it stays there. The top
row read 143px at 2560 and 1920 in this measuring state, with every column
set; the spec's 141px was measured in another state, by PR #380.

**How these were measured.** In the real grid, not in the mockups: the app at
`8eda2b6` with the three columns added in memory and the proposed CSS
injected, on the maintainer's stats files, in headless Edge 155 and the
installed Firefox 158, with overlay scrollbars and with classic ones. Every
figure is Edge's unless it says otherwise. Firefox's differ only where its
scrollbars do. The page area is the window less the navbar's 225px and the
page's 32px of padding. The scripts are listed under [Testing](#testing).

### The columns

The three columns sit among today's, results first and settings after:
`#`, Time, Score, the marks, Accuracy, Shots Fired, **Reloads**,
Sensitivity, **FOV**, **Avg FPS**. Reloads sits beside the shots it costs,
FOV beside the other setting a run was played at, and Avg FPS, which says
how the machine ran, last. The menu lists them in the same order, after
which comes Median and best, as today: the 2026-10-05 rule that a menu lists
"every column the table can work without, in table order" holds.

Each is right-aligned, as the list's other figures are, and held to one width
as the others are:

| Column | Width | What sets it |
|---|---|---|
| Reloads | 64px | The header, 42px of text, with the cell's 8px of padding and the 13px the Accuracy and Shots Fired columns leave beyond their headers. Its values are at most two digits. |
| FOV | 116px | `110 Apex Legends` and `110 Quake/Source`, 105px and 106px of text, 113px and 114px with the padding: the scales a player above 103 is most likely on. `103 Overwatch` is 86px of text. |
| Avg FPS | 64px | The header, 44px of text, with about the same room as Reloads. `1,024` is 31px of text. |

Widths were measured as text in the grid's own fonts, 13px cells and 12px
semibold headers, and Edge and Firefox agreed to a tenth of a pixel.

**The FOV cell** reads the run's FOV, a space, and its scale:
`103 Overwatch`. That is how the Sensitivity column already reads,
`40.0 cm/360`, so the two cells that pair a number with its scale look alike.
The number is the one the player typed into KovaaK's, as the stats file
records it, with trailing zeros dropped: `103.0` reads `103`, and `106.5`
stays `106.5`. A file with no `FOVScale:` line, 570 of the maintainer's,
shows the number alone. A scale too long for the column, such as
`Horizontal (16:9)`, `Quake Champions` or `Battlefield V/1/Hardline`, is cut
with an ellipsis: the number leads, so it is never the part cut. The cell's
hover gives its whole text, as a scenario row's name gives its whole name.
The mockups drew the scale dimmed. Plain text is recommended instead: a
dimmed scale beside an undimmed one in Sensitivity would look like a
mistake, and it would need a cell renderer where a plain value needs none.

**Reloads** is a plain count, `0` shown as `0`, with a thousands separator as
Shots Fired has one. **Avg FPS** is the recorded average rounded to the
nearest whole number, with a thousands separator, as every count and score in
the list has: `676`, `1,024`. A run whose file lacks a field, or holds one
that isn't a number, shows an empty cell, as Shots Fired does. Unknown is
never shown as zero.

**Where the values come from.** `RunData` gains four fields, each `None` when
the file has no usable value: `reloads`, a whole number of zero or more;
`fov`, a number greater than zero; `fov_scale`, the scale's name as the file
writes it; and `avg_fps`, a number of zero or more. The parser reads each
with `_optional_field_value`, as it reads `DPI:`, so a line with no value
costs that field only, never the run. No field joins the run's required set.
The FOV cell is put together where the run's row is built, in `_run_row`,
beside the Sensitivity string. Nothing is converted: the app shows the FOV
and scale the run was played at, and a degree figure would be a number the
player never typed.

**Both views.** All scenarios lists its runs in the same columns as This
scenario, from one set of column definitions, and the one Columns menu sets
both. Median and best is unaffected: its figures sit in the group rows,
which stay in view as [Scrolling sideways](#scrolling-sideways) describes.

### The width rule

The list's width is `clamp(500px, need, room − 480px)`, where `room` is the
width the chart and the list share less the 16px gap between them. When the
upper bound is less than 500px, the 500px wins.

- **`need` is today's 64px plus the fixed widths of the columns shown.** With
  today's columns that is exactly 500px. With Reloads or Avg FPS it is 564px,
  with FOV 616px, with FOV and Avg FPS 680px, and with all three 744px. With
  Shots Fired and Sensitivity hidden and nothing new on it is 322px, and the
  500px minimum holds the list where it is today. The 64px keeps the marks
  column, the borders and the scrollbar's room exactly as they are, so no
  browser sees its marks column change.
- **500px is the minimum because the header needs it.** The view switch,
  Expand all and Columns share one line at 500px. They don't depend on the
  columns, so a list with columns hidden doesn't narrow below it.
- **480px is the chart's floor.** It leaves a plot area of about 320px, by
  plotly's 160px of margins measured in the 2026-10-12 run-list entry. A
  column turned on never takes the chart below it; only a narrow window
  does, as today ([Narrow windows](#narrow-windows)). At the maintainer's
  widths the floor never binds: all three on leave the chart 903px at 1920.
  It binds from about a 1,497px window with all three on, about 1,369px with
  FOV alone, and about 1,317px with Reloads or Avg FPS alone.
- **The marks column** keeps the room it has today, 45px or 50px, and takes
  any spare room, as today, when the 500px minimum holds a list whose columns
  need less. When the chart's floor binds, it gives first, down to its 34px
  minimum, so a list up to 16px short of its need doesn't scroll, or 11px
  beside a classic scrollbar: FOV alone at 1366 measured 613px with the marks
  at 47px in Edge, and scrolled 9px in classic Firefox, whose page scrollbar
  also takes 17px of the page. Past that, the list scrolls.
- **The overlay scrollbar's room is unchanged.** The 12px rule keys on the
  scrollbar the grid marks invisible and adds room inside both scrolling
  areas. It holds at every width measured: a session row's count ends 16px
  inside the list's edge in Edge and in Firefox with overlay scrollbars, and
  4px inside beside Firefox's classic one, as today.

**How the page learns `need`: from the server's column list, not the grid.**
Every column but the marks has one allowed width, set once in
`run_list_column_defs`. The page registers a clientside callback on the
Columns menu's checkboxes, given those widths when it is registered, that adds
up the widths of the checked columns and the always-shown ones and writes
`need` to a CSS variable on the page. The CSS clamp does the rest, and the
900px rule that stacks the list ignores it. The callback runs as the page
mounts, with the stored choices, as the menu's own callback does, and on
every change. Reading widths from the grid was the other way. It would wait
for the grid's API, and the marks column's width depends on the list's,
which is what it would be setting.

- `--run-history-list-width` stays the list's 500px minimum, and a second
  value, the card's 500px, takes its place in the top row (RC3). The page's
  root gets an id, so the callback can write the variable as a Dash style
  prop rather than by reaching into the page.
- The list may draw at 500px for a moment before a stored column widens it,
  since the callback runs after the layout is drawn. The chart follows as it
  follows Chart options opening: the page's resize observer redraws the plot
  whenever the graph's box changes. The implementation PR measures the moment
  in Firefox and says what a player sees.

### Scrolling sideways

Measured in the real grid at 1366 with all three on. Three ways were tried.

- **Plain sideways scrolling breaks the session rows.** With
  `embedFullWidthRows` on, a session row is as wide as all the columns, not
  the list, so at the start its count, length and In progress badge sit 99px
  past the list's edge, out of view, and scrolled to the end its date is cut
  off at the left. Today's list does this too, at phone width, where its
  columns are wider than the page: in a 420px window a session row's count
  sits 80px out of view.
- **Pinning `#`, Time, Score and the marks doesn't work with embedded
  full-width rows.** The grid draws every full-width row once in the pinned
  part and once in the part that scrolls, so each session row's text appeared
  twice side by side. The marks column also lost its flex there, as pinned
  columns do, and fell back to 200px. The row's renderer would have to split
  its line by part, and the pinned part, 238px with the marks held to 50px,
  can't hold a session row's line, so its count would still scroll away.
- **Held group rows work.** Each full-width row's content is held to the
  list's visible width and stays put while the run rows scroll under it, in
  Edge and in Firefox with either kind of scrollbar. Its name stays at the
  list's left and its count where it is today, 16px inside the right edge in
  Edge, at the start and at the end. Recommended.

How it is held, in CSS alone:

```css
/* The grid's two scrolling areas measure what the content is held to. */
.run-history-list-grid :is(.ag-center-cols-viewport, .ag-floating-top-viewport) {
    container-type: inline-size;
}
/* AG Grid gives a row overflow: hidden, which makes the row the scroll
   container of what is inside it, so the content could never stay put.
   clip cuts the same way and makes no scroll container. */
.run-history-list-grid .ag-full-width-row {
    overflow: clip;
}
.run-history-list-grid .ag-full-width-row .run-list-wide {
    left: 0;
    position: sticky;
    width: 100cqw;
}
```

`100cqw` is the scrolling area's width less its padding, so the 12px of the
overlay scrollbar's room stays clear. Wherever the list doesn't scroll, the
content is exactly as wide as the row, so every such state draws as today.
The run rows scroll whole, so scrolled to the end a run's `#` and Time are
out of view. That case only arises in a window narrower than about 1,480px
with all three on, or about 1,350px with FOV alone, and the session row above
the runs still names the session. This is an eleventh piece of grid-specific work an AG Grid
upgrade can break, beside the ten the grid's entry lists, and the spec's
[There is no phone design](../specs/run_history.md#narrow-windows) gains it:
at phone width the session rows now stay whole too.

### Narrow windows

- **A page of 900px or less stacks the list above the chart, as today,** at
  the page's full width and up to 600px tall. The width rule doesn't apply
  there. The list holds every column on and scrolls sideways only where the
  page is narrower than their need, with its group rows held: all three on
  fit a page of about 730px, the marks column at its minimum.
- **Between a page of 901px and about 996px,** 500px of list, 16px of gap
  and 480px of chart can't all fit. The list's minimum wins and the chart
  gives, from 480px down to 385px at a 901px page, which is exactly what the
  chart does there today with the default list. A column turned on there
  scrolls the list sideways and takes nothing more from the chart. Moving the
  stacking threshold to 996px would keep the floor everywhere, but it changes
  a ratified narrow-window rule for a state the app already ships, so it is
  not proposed.
- **The latest-run card in the wrapping top row is unchanged:** it joins a
  line at 380px and takes the room left on it, measured 531px at a 1,100px
  window. RC3 changes only the two-column layout.

### The top row

The top row's second column is the card's own 500px, set by a value of its
own beside the list's minimum. The two are equal on purpose: so the default
page lines up as T1 made it. A change to one asks whether the other follows.

Measured with the card following a list that fits its columns, as it would
without RC3: at 1920 the top row goes from 143px to 297px as soon as the
list passes 500px, with Reloads alone, the PB card dropping to a second line,
and the chart loses 154px of height. At 2560 it stays one line even at
744px. With RC3, the row is 143px at 1920 with every column set. The first column, the dropdowns, Scenario Stats, the note card and the
PB card, is unchanged, and so is the order in which it wraps.

PR #401, open at `11e0477`, rewrites Scenario Stats' contents and keeps its
270px, so it doesn't move this row. Whichever of the two implementations
merges second measures the top row again at 1920 and 2560.

### Beyond the rows

One effect reaches past what the rows ask for, flagged so it is chosen and
not slipped in. The held group rows apply wherever the list scrolls
sideways, so they also change today's list at phone width, where its seven
columns are wider than the page and a session row's count sits out of view.
With them, it stays in view there too. It is the same CSS, so taking it out
of the phone case would cost a rule of its own. The trade-off is the one
every held row carries: another piece of grid work an AG Grid upgrade can
break. Nothing else is added beyond the rows.

### Copy

Every string this proposal adds. They follow the nine copy rules in
[AGENTS.md](../../AGENTS.md#styling-conventions). Grid column headers keep
Title Case, and a menu entry that names a column reads as the column's
header, as `Shots Fired` does.

| Where | String | Why |
|---|---|---|
| Column header and Columns menu entry | `Reloads` | KovaaK's own word for the figure, in the stats file and in game. |
| Column header and Columns menu entry | `FOV` | The word players and KovaaK's use. The glossary says what it is and why its scale matters. |
| Column header and Columns menu entry | `Avg FPS` | KovaaK's own label for the figure. |
| FOV cell | `{fov} {scale}`, such as `103 Overwatch`, or `{fov}` alone, such as `103`, where the file has no scale | The number first, then its scale, as Sensitivity reads `40.0 cm/360`. |
| FOV cell's hover | The cell's own text, such as `110 Quake Champions` | Gives a cut cell whole, as a scenario row's name does. No new words. |
| Reloads cell | `{n}`, such as `0` or `12` | A count, formatted as Shots Fired is. |
| Avg FPS cell | `{n}`, such as `676` or `1,024` | A whole number, with the separator every count in the list has. |
| A cell whose field is missing | empty | As Shots Fired shows a missing count: unknown is never shown as zero. |

No new accessible names: each header is named by its text, and a cell is
read as it shows. No header has a hover. The FOV cell's scale explains
itself, and the glossary holds the rest.

### Terms

One entry, written as [docs/glossary.md](../glossary.md) would hold it, under
"Play", after cm/360. Reloads and Avg FPS get none: each is KovaaK's own
figure, shown as the stats file records it, as Shots Fired is, which has no
entry either.

> ### FOV
>
> The field of view a run was played at: a number on a scale, such as 103 on
> the Overwatch scale. The same number is a different width on different
> scales, so 103 on Overwatch is narrower than 103 on Apex Legends. The app
> shows the FOV and the scale as the run's stats file records them and
> converts nothing.
>
> - On screen: the run list's FOV column, as `103 Overwatch`.
> - In code: `fov` and `fov_scale`, from the stats file's `FOV:` and
>   `FOVScale:` lines.

### Decisions this changes

Each entry this changes stays and is marked superseded in part, naming what
changed and what stands, as the decision log does. Two more are touched and
not marked, because nothing in them stops holding.

- **T1, the 2026-10-14 entry
  [Run History's Top Row Has One Card Per Kind Of Information](../decision_log/2026/2026-10-14-run-historys-top-row-has-one-card-per-kind-of-information.md):**
  "The latest-run card aligns over the run list instead of filling the
  remaining width", and the row and the chart and list sharing "two columns,
  the second 500px wide". The card keeps its 500px and its place at the
  row's right end, and lines up with the list only while the list is at
  500px. Everything else in T1 stands: the dropdowns' column, the cards and
  their order, the PB card beside the latest-run card, the Follow switch,
  and the narrow-window line.
- **The 2026-10-12 entry
  [The Run List Is A Second Column Beside The Chart](../decision_log/2026/2026-10-12-the-run-list-is-a-second-column-beside-the-chart.md):**
  R3's "500 px wide", the 2026-10-15 note's "their shared 500px column", "A
  run row has seven columns", and "The Columns menu shows or hides Shots
  Fired and Sensitivity". The list is 500px at least and as wide as its
  columns need, a run row has seven columns by default and up to ten, and
  the menu also shows or hides Reloads, FOV and Avg FPS. The list's place
  beside the chart, its narrow-window rules and every rule of what it shows
  stand.
- **The 2026-10-14 entry
  [The Run List's Columns Menu Offers Median And Best, Off To Start](../decision_log/2026/2026-10-14-the-run-lists-columns-menu-offers-median-and-best-off-to-start.md):**
  "a third checkbox". Median and best is now the sixth, still after the
  columns. Its default, its rows and its figures stand.
- **The 2026-10-12 entry
  [The Run List Is Built On AG Grid Community, And NVDA Is Run On The Built List](../decision_log/2026/2026-10-12-the-run-list-is-built-on-ag-grid-community-and-nvda-is-run-on-the-built-list.md):**
  nothing in it stops holding, so it isn't marked. Its list of grid-specific
  work gains the held group rows, and item 8's fixed widths now also set the
  list's width.
- **The 2026-10-05 Columns menu entry stands.** The three new entries follow
  its rule, every column the table can work without, in table order.
- **The spec,** [run_history.md](../specs/run_history.md): "one value sets the
  list's 500px width for both" and the card sitting "over the run list" with
  "its edges are the list's at every zoom level" (The top row); "The card is
  500px wide, the run list's width" (The latest-run card); "500px wide and
  always shown", "A run row has seven columns" and "shows or hides Shots Fired
  and Sensitivity" (The run list); "in the seven columns of This scenario"
  (All scenarios); "the Columns menu's three checkboxes"
  (What the page keeps and forgets); and the phone-width line (Narrow
  windows). The shipping PR rewrites each and links the new entries.
- **[architecture.md](../architecture.md)** says one CSS value sets the list's
  width for both columns. The shipping PR corrects it.

### Alternatives rejected

- **A combined sensitivity-and-FOV cell.** The maintainer: "it simply adds
  more complexity and edge cases". The same width is spent either way.
- **FOV only where it varies,** in the Sensitivity label, in the list and on
  the Score vs Sensitivity axis, the discussing session's first
  recommendation. The rule that decides where it varies was the complexity,
  and a column that is off to start saves the same width.
- **500px with sideways scrolling.** Every column a player turns on starts out
  of view at every window: 216px of them at 1920 with all three on. Without
  the held rows, the session rows' counts sat 212px out of view there.
- **Drag to resize.** The heavy version of fitting the columns: a splitter, a
  width to remember, and a list a player has to fix by hand when a column
  goes on.
- **A full-width mode now.** Additive, so it can come later on top of this
  one, with its own column set and a rule for leaving it. Kept as an
  addition, with its trigger under [Out of scope](#out-of-scope).
- **A separate sortable runs table.** It would duplicate the list and move
  the bloat there, and a sort would break the session tree. The maintainer:
  "Probably no sort."
- **"Add all columns".** Most of the stats file's fields are constant for a
  player or worked out from others, such as Avg TTK from the run's length and
  kills, and Kills, which follows Score or Hits. Tier 3 is the Run Viewer's.
- **Reloads on by default.** A column of zeros on four scenarios in five, and
  a wider default list for every player.
- **Pinning `#`, Time, Score and the marks.** Measured: session rows drawn
  twice and the marks column at 200px (see
  [Scrolling sideways](#scrolling-sideways)).
- **A dimmed scale in the FOV cell,** as the mockups drew it. It would read
  differently from Sensitivity's plain scale and need a cell renderer.
- **FOV converted to degrees.** The definitions' codes are undocumented, a
  conversion needs each run's screen shape, and the player compares the
  number they typed.
- **The card filling the room left.** It would compete with the note card.
- **A card sized to its content,** about 360px. It changes every player's
  page and parts the card from the list on every load, for room the first
  column mostly can't use (RC3).
- **Splitting the card now** into a run card and a session card, as mockup
  v5 did. A later idea: a live session clock counts the current break, which
  today's session length leaves out on purpose, so it waits on the tracker's
  "Definition of Time" item. The 270px run card also cut the scenario's name.
- **Moving the stacking threshold to 996px** (see
  [Narrow windows](#narrow-windows)).

## Delivery plan

One implementation PR, after this proposal is ratified and merged. The list
can't grow without RC3, or the top row wraps at 1920, and the three columns
are what make it grow, so the parts can't usefully ship apart. The parser
alone could, with nothing on screen, but it would cost a review round for no
change a player sees.

**PR 1: the columns, the width rule and the card.** The four `RunData` fields
and the parser's reading of them; the three columns and menu entries; the FOV
cell and its hover; the clientside callback, the width rule and the held
group rows; the card's width of its own; and the docs that ship a proposal:
three superseding notes and the new decision-log entries, the spec, the
glossary's FOV entry, a sentence in the user guide, architecture.md,
product.md's inventory, and the deletion of this file.

- **Recommended:** `claude-opus-5-5` at high effort. The design and its
  measurements are done here, and the probes exist, so the work is building
  to a measured spec. The browser checks and gate runs are mechanical and go
  to a Sonnet 5.5 subagent with exact commands.
- **Review:** the Codex seat at xhigh, with the connector. The maintainer
  tries it in their own Firefox at 2560 and 1920, from the PR's instance,
  before marking it ready.
- **Depends on:** this proposal's ratification. PR #401 touches the same
  spec section and stylesheet, so whichever merges second merges main and
  measures the top row again.

## Out of scope

- **The Run Viewer,** everything about one run with a per-bot breakdown: a
  later proposal. It is tracked in the vault's Dashboard, "Run Viewer page",
  and Backlog Codex v1, "Run details and metrics". Until it exists, the
  Columns menu is the only place FOV shows.
- **A full-width list mode.** Add it when a common column set makes the list
  scroll sideways at 2560, or a player asks. It adds a second remembered
  column set and a rule for leaving it.
- **A session card or session clock** in the top row. It waits on the
  tracker's "Definition of Time" item, as the card split above does.
- **Overshots,** whose meaning is unknown (see [The evidence](#the-evidence)).
- **Sorting the list.**
- **FOV in the chart's hover or on an axis.** The tracker's Dashboard asks
  for a shorter chart hover, because the run list already holds a run's
  details.

## Testing

- **The parser.** For each of `Reloads:`, `FOV:`, `FOVScale:` and
  `Avg FPS:`: present, missing, a line with no value, and a value that isn't
  a number. A file with no `FOVScale:` keeps its FOV and has no scale. A
  missing or malformed field costs that field only, never the run. Built on
  real line order: the test helper writes the sensitivity lines first, the
  reverse of a real file, which the parser doesn't mind.
- **The row.** `_run_row`'s FOV cell with a scale, without one, and with a
  decimal; Reloads and Avg FPS formats; an empty cell for each missing value.
- **The columns and the menu.** The ten columns in order, each fixed width as
  above and the new three hidden to start; the menu's five column entries in
  table order, the new three unchecked, then Median and best; and the stored
  ids of Shots Fired, Sensitivity and Median and best unchanged, so no stored
  choice resets.
- **The width rule in the browser.** At 2560, 1920, 1536 and 1366, and a
  stacked page, with no new column, each one alone and all three: the list's
  width, the chart's, and whether the list scrolls, against the table above;
  the top row's height the same in every column set at each width; no header
  or cell cut at the widths that don't scroll; and a session row's count in
  view at the start and at the end of a sideways scroll. In Edge, and in
  Firefox with overlay scrollbars and with classic ones.
- **A stored choice on load.** A browser with FOV stored on opens with the
  list at 616px, and the moment it spends at 500px is measured and reported.
- **A screen reader.** The grid's entry repeats its NVDA walk for "any later
  change to what a screen reader hears". By default nothing a screen reader
  hears changes. With a column on, it hears one more cell per run, of the
  kind it already hears as Shots Fired, and the held rows change only CSS.
  So the recommendation is one NVDA pass, in browse mode, over a run row with
  all three on, rather than the full walk. It needs the maintainer's
  hands-off time, so the maintainer decides at the implementation PR.
- **Gates:** `uv run pytest`, `uv run ruff format --check .`,
  `uv run ruff check`, `uv run mypy source`, and
  `uv run python -m compileall source tests`.

The scripts that measured this proposal are in the main checkout's
`ignore/scripts/run-list-columns/`: `serve_patched.py` serves the app with
the three columns added in memory, `probe.py` and `probe_rows.py` drive Edge
and Firefox through the states above, and `summarize.py` prints the tables.
