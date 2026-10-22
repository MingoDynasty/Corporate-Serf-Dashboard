# 2026-10-22: The Run List's Columns Menu Offers Reloads, FOV And Avg FPS, Off To Start

Status: Accepted

The run list's Columns menu can add three columns, Reloads, FOV with its
scale, and Avg FPS, and each is off until a player turns it on. A player who
never opens the menu sees the list as it was. The list stays a short panel
for picking out a run, so a later column has to show it helps choose or
compare runs before one is opened, and that it is worth its width.

**Ruling.** RC1 of
[#403](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/403),
ratified by the maintainer on 2026-10-22: "I ratify the run list columns
proposal, rows RC1 to RC3, as amended at 20f6619." As first written, the row
also said no other stats-file field would ever reach the list. The first
review wave asked for a bar that a later column has to meet instead, and the
row was amended to it at `20f6619`. Shipped in
[#406](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/406).
The proposal is in those PRs and git history. What the list does today is in
[run_history.md](../../specs/run_history.md#the-run-list).

**The request, and the line it drew.** A player asked to "have the FOV for
the run also tracked in the right column along with the sens, shots, acc
score etc", because they play above 103 on some scenarios. The maintainer
didn't want the list to grow a column for every such request: "I think the
better vision is to treat the right panel as essentially a 'Run Navigation'
panel. Short and sweet, and solely the information needed to help identify a
run of interest." The requester: "100%". Everything about one run, with a
per-bot breakdown, belongs to a later Run Viewer. The maintainer sorted the
stats file's figures into three tiers: probably useful by default (today's
columns), possibly useful to some players (these three), and not worth the
clutter (everything else, today).

**The bar for a later column.** This entry adds only these three. A later
column needs a concrete use for choosing or comparing runs before opening
one, information the existing columns don't adequately supply, and a width
and menu cost worth paying. Detailed inspection of one run belongs in the Run
Viewer. That is a bar, not a list of fields that may never be shown: a field
doesn't earn a column because the stats file holds it, and a later request is
judged on its task and its cost. A permanent rule against further columns
was the row's first form; it would have made a later request as well argued
as FOV's first reverse a product rule.

**Why each is off.** Measured on 2026-10-21 on the maintainer's stats files.

- **FOV** is 103 on 9,177 of 9,212 runs. Where it moves, it matters:
  SmoothBot Perfected's PB, 5,079.14 on Oct 16, was set in a block of eight
  runs at FOV 70, and nothing on the page showed it before this column.
- **Reloads** is 0 on every run of 648 of 810 scenarios with hit counts. On
  the scenarios where it varies it follows misses, a correlation against
  Accuracy of −0.42 to −0.88. The requester asked for it: "i love the
  reloads, ive been playing popcorn & this is a very useful 'stat' to keep
  track of".
- **Avg FPS** says how the machine ran, not how the player aimed: median 676,
  145 to 987 across 8,642 files.
- **Any of them on to start** widens every player's default list: Reloads
  alone takes it to 564px and puts a column of zeros on four scenarios in
  five.

**The columns.** The run row reads `#`, Time, Score, the marks, Accuracy,
Shots Fired, **Reloads**, Sensitivity, **FOV**, **Avg FPS**: results first,
settings after, and Avg FPS, which describes the machine, last. The menu
lists its five columns in that order, then Median and best, so the
[2026-10-05 rule](2026-10-05-a-columns-menu-shows-and-hides-table-columns-and-kovaaks-ids-are-optional-ones.md)
of every hideable column in table order holds. Each is right-aligned and held
to one width, measured as text in the grid's own fonts, in Edge and Firefox:

| Column | Width | What sets it |
|---|---|---|
| Reloads | 64px | The header, 42px of text, with the cell's padding and the room the other figure columns leave beyond their headers. |
| FOV | 116px | `110 Apex Legends` and `110 Quake/Source`, 105px and 106px of text: the scales a player above 103 is most likely on. |
| Avg FPS | 64px | The header, 44px of text. `1,024` is 31px. |

- **The FOV cell reads the number, a space, and the scale,** `103 Overwatch`,
  as Sensitivity reads `40.0 cm/360`. The number is the one the player typed,
  with trailing zeros dropped: `103.0` reads `103`, and `106.5` stays. A file
  with no `FOVScale:` line, 570 of the maintainer's, shows the number alone.
  A scale too long for the column is cut with an ellipsis after the number,
  and the cell's native hover gives its whole text, as a scenario row's name
  does.
- **Nothing is converted.** The same number is a different width on
  different scales: across a 16:9 screen, 103 is about 103° wide on
  Overwatch and about 118° on Apex Legends, worked out from KovaaK's own
  scale definitions. The definitions' codes are undocumented, a conversion
  needs each run's screen shape, and the player compares the number they
  typed.
- **Reloads is a count** with a thousands separator, as Shots Fired is.
  **Avg FPS** is rounded to a whole number with a separator: `676`, `1,024`.
- **Unknown is never shown as zero.** A run whose file lacks a field, or holds
  one that can't be read, shows an empty cell.

**Where the values come from.** The run record gains four optional fields,
`reloads`, `fov`, `fov_scale` and `avg_fps`, from the stats file's
`Reloads:`, `FOV:`, `FOVScale:` and `Avg FPS:` lines. Each is read as `DPI:`
is, so a missing line, a line with no value yet, or a value out of range
costs that field only, never the run, and none joins the run's required set.
`reloads` is a whole number of zero or more, `fov` a finite number above
zero, `fov_scale` the name as written (empty is none), and `avg_fps` a finite
number of zero or more.

**Stored choices.** The menu remembers each checkbox under an id built from
the column's, `reloads`, `fov` and `avg_fps`, and Dash drops a stored choice
whose layout default changed. So the three new entries reset nobody's choice
of Shots Fired, Sensitivity or Median and best, and their defaults, off, must
never change.

**Alternatives set aside.**

- **A combined sensitivity-and-FOV cell.** The maintainer: "it simply adds
  more complexity and edge cases". The same width is spent either way.
- **FOV only where it varies,** in the Sensitivity label or on the chart's
  axis. The rule that decides where it varies was the complexity, and a
  column that is off to start saves the same width.
- **Every field the stats file holds.** Most are constant for a player or
  worked out from others, such as Avg TTK from the run's length and kills. A
  later column meets the bar above on its own case.
- **A dimmed scale,** as the mockups drew it. It would read differently from
  Sensitivity's plain scale and need a cell renderer.
- **Overshots,** which a requester hoped would show "which bot jukes u more".
  It is about 19 to 26 per kill on nearly every kill, uncorrelated with kill
  time or shots, and what it measures is unknown.
