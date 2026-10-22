# 2026-10-22: The Run List Grows To Fit The Columns It Shows

Status: Accepted

The run list is as wide as the columns it shows need, never narrower than
the 500px it had before, and never so wide that the chart beside it drops
under 480px. With the default columns it is exactly 500px, so the default
page doesn't move. Past the chart's floor the list scrolls sideways inside
its own box, and its session rows and the other full-width rows stay whole
in view while the run rows scroll under them.

**Superseded in part (2026-10-22).**
[The narrower minimum](2026-10-22-the-run-list-can-shrink-to-480px-when-columns-are-hidden.md)
lets hidden columns reduce the list to 480px. The default columns still
need 500px, and the latest-run card keeps its independent 500px width. The
remaining contract stands.

**Ruling.** RC2 of
[#403](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/403),
ratified by the maintainer on 2026-10-22: "I ratify the run list columns
proposal, rows RC1 to RC3, as amended at 20f6619." Of the four list widths in
the first mockup, the maintainer chose the one that fits its columns over a
full-width mode: "Option 1 can work well for now, while Option 2 can be added
on top of Option 1 later, if/when we have so many columns that we end up
hiding the chart anyways." The requester: "i really like how much bigger the
right panel is on the 'fits its column' choice". The two numbers and the
mechanism were author-owned, and the ratification covered them. Shipped in
[#406](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/406).
What the list does today is in
[run_history.md](../../specs/run_history.md#the-run-list).

**The rule.** The list's width is `clamp(500px, need, room − 480px)`, where
`room` is the width the chart and the list share less the 16px gap between
them. When the upper bound is less than 500px, the 500px wins.

- **`need` is 64px plus the fixed widths of the columns shown.** The 64px
  holds the list's borders, a classic scrollbar's room, and the marks column
  at the 45px or 50px it had, so with the default columns `need` is exactly
  500px and no browser sees its marks column change. With Reloads or Avg FPS
  it is 564px, with FOV 616px, and with all three 744px.
- **500px is the minimum because the header needs it.** The view switch,
  Expand all and Columns share one line at 500px, whatever columns are
  shown.
- **480px is the chart's floor.** It leaves a plot area of about 320px, by
  plotly's 160px of margins. A column turned on never takes the chart below
  it; only a narrow window does, as before. At the maintainer's widths it
  never binds: all three on leave the chart 903px at 1920.
- **The marks column gives first** when the floor binds, down to its 34px
  minimum, so a list up to about 16px short of its need doesn't scroll.
- **The overlay scrollbar's 12px of room is unchanged,** at every width
  measured.

**How the page learns `need`.** A clientside callback on the Columns menu's
column checkboxes adds up the widths of the checked columns and the
always-shown ones, and writes `need` to a CSS variable on the page's root
through its `style` prop. The widths come from the server's column list when
the callback is registered, and not from the grid: the marks column's width
follows the list's, which is what this sets, and reading it would wait on the
grid's API. The callback runs as the page mounts, with the stored choices,
and on every change. A browser with a column stored on draws the list at
500px until it runs.

**Scrolling sideways.** Measured in the real grid at 1366 with all three on,
where the list is 613px and its columns need 744px. Three ways were tried.

- **Plain sideways scrolling breaks the session rows.** With
  `embedFullWidthRows` on, a full-width row is as wide as all the columns,
  not the list, so its count and In progress badge sat 99px out of view at
  the start, and its date was cut off at the end.
- **Pinning `#`, Time, Score and the marks doesn't work with embedded
  full-width rows.** The grid drew every full-width row once in the pinned
  part and once in the part that scrolls, so each session row's text appeared
  twice side by side, and the pinned marks column lost its flex and fell back
  to 200px.
- **Held rows work.** Each full-width row's content is held to the list's
  visible width by CSS sticky, against the grid's scrolling areas as
  containers, and stays put while the run rows scroll under it. Sticky does
  nothing until the row's `overflow: hidden`, which AG Grid sets and which
  makes the row the content's scroll container, becomes `overflow: clip`.
  Where nothing scrolls, the content is exactly the row's width, so the
  default list draws as before.

The held rows are an eleventh piece of grid-specific work an AG Grid upgrade
can break, beside the ten in
[the grid's entry](2026-10-12-the-run-list-is-built-on-ag-grid-community-and-nvda-is-run-on-the-built-list.md)
and the All scenarios entry. They also change the list at phone width, where
its default columns were already wider than the page and a session row's
count sat 80px out of view: it now stays in view there too. Taking that out
of the phone case would cost a rule of its own, so it was flagged and kept.

**Narrow windows keep their rules.** A page of 900px or less still stacks the
list above the chart at the page's full width, and the width rule doesn't
apply there: the list holds every column on and scrolls sideways only where
the page is narrower than their need. Between a page of 901px and about
996px, 500px of list, the gap and 480px of chart can't all fit, so the
chart gives, down to 385px at a 901px page, exactly as it did with the
default list. Moving the stacking threshold to 996px would keep the floor
everywhere, but it changes a ratified narrow-window rule for a state the app
already shipped, so it was set aside.

**Measured.** The proposal's figures, in headless Edge 155 at `8eda2b6` with
the columns added in memory, and again on the build in this entry's PR. The
page area is the window less the navbar's 225px and the page's 32px of
padding.

| Window | Columns on | List | Chart | Sideways scroll |
|---|---|---|---|---|
| 2560 | none new / Reloads or Avg FPS / FOV / all three | 500 / 564 / 616 / 744 | 1,787 / 1,723 / 1,671 / 1,543 | no |
| 1920 | none new / Reloads or Avg FPS / FOV / all three | 500 / 564 / 616 / 744 | 1,147 / 1,083 / 1,031 / 903 | no |
| 1536 | none new / all three | 500 / 744 | 763 / 519 | no |
| 1366 | none new / FOV / all three | 500 / 613 / 613 | 593 / 480 / 480 | no / no / yes |
| 1280 | none new / any | 500 / 527 | 507 / 480 | no / yes |
| 1200 | none new / any | 500 / 500 | 427 / 427 | no / yes |
| 1100 | any, stacked | 843, above the chart | 843 | no |

**Columns still don't sort.** The maintainer: "Probably no sort. I can't yet
imagine a use case for sorting besides by timestamp." The list is a tree of
sessions, and a sort would scatter each session's rows.

**Alternatives set aside.**

- **500px with sideways scrolling.** Every column a player turns on would
  start out of view at every window: 216px of them at 1920 with all three on.
- **Drag to resize.** A splitter, a width to remember, and a list a player
  has to fix by hand when a column goes on.
- **A full-width list mode now.** Additive, so it can come later on top of
  this rule, when a common column set makes the list scroll sideways at 2560
  or a player asks.
- **Pinned columns,** for the reasons above.
- **Moving the stacking threshold to 996px,** for the reason above.
