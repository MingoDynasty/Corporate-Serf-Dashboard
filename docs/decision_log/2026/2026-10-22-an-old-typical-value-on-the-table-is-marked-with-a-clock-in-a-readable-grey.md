# 2026-10-22: An Old Typical Value On The Table Is Marked With A Clock In A Readable Grey

Status: Accepted

On the scenario table, a typical score that is not recent shows in a muted
grey that stays readable, with a small clock after it in both typical
columns. Each old cell's hover says why it is marked, and a screen reader
hears Not recent after the value. The hovers open from the keyboard too, so
the qualification reaches every reader.

**Ruling.** TB4 of
[proposal #408](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/408),
ratified by the maintainer on 2026-10-22, as amended in review. This departs
from the maintainer's first lean. After comparing two greys on the
prototype, they found the darker one "doesn't seem faded enough, and looks
too similar to regular text. The 'Card's grey' option, however, is faded
enough to see a difference." The review wave contested that grey, and the
recommendation kept the darker grey and added the clock, so the difference no
longer rests on the grey. A key line explaining the clock, in the first
amendment, was dropped on the maintainer's word, "I push back on this
because it doesn't lead to good UI/UX"; the hovers explain it instead. A
third consult endorsed the result and asked that the user guide name the
clock, since the page explains it only on hover. Asked once more, the
maintainer kept it: "No, let's keep it as is." Shipped in
[#414](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/414).

**The mark.**

- **Only on a known value that is not recent,** in both typical cells. Too
  few runs and `N/A` are never marked, nor is the `N/A` Typical Rank of a
  benchmark scenario without a ladder.
- **The grey** is `#676d75` light and `#a6a6a6` dark. On the prototype they
  measured 5.22:1, 4.95:1 and 4.7:1 on the plain, alternating and hovered
  rows in the light theme, and 6.38:1, 5.58:1 and 4.6:1 in the dark, all over
  the 4.5:1 WCAG AA asks of text this size. The card's grey measured 3.32:1
  light and 4.04:1 dark on the plain row, with the difference in color alone.
  In the dark theme the grey is barely fainter than normal text, `#c9c9c9`,
  and the clock carries the difference.
- **The clock** is Material Symbols' history icon, 13 px, after the value,
  hidden from assistive technology. It costs no width: both columns are as
  wide as their headers.
- **The card's precedent doesn't carry over.** Scenario Stats dims a 30 px,
  weight-600 lead, held to 3:1 for large text, and its first line states the
  recent count in words. The table's typical cells are the figures a player
  compares to find weakness.

**What explains it.** Each old Typical Score hover adds, after its opening
sentence, `Fewer than 10 of them are from the last 30 days, so it may be out
of date.`, "them" being the runs that sentence counts. Each old Typical Rank
hover adds a line, `Fewer than 10 of the typical score's runs are from the
last 30 days, so it may be out of date.`, which at the top rank is the whole
hover. The Typical Score header's tooltip names the clock. The hovers count
the runs behind the value, as recency does, never the scenario's: the two
differ when the store holds runs dated after the table was built, such as
after a system clock correction. There is no key line, and no tooltip on the
13 px clock alone, which would be hard to hit, would fight the cell's hover,
and couldn't take keyboard focus inside the grid.

**Every reader.**

- **Keyboard.** When keyboard focus lands on a typical cell, its hover opens
  beside it with the same content, and closes on Escape, a pointer press, a
  scroll of the table, and focus moving on or leaving the table. A click that
  focuses a cell opens nothing extra. AG Grid's `tooltipTrigger` can't do
  this: it is one grid-wide option, and set to `focus` it ends every mouse
  hover in the table (dash-ag-grid 35.3.0). So the page opens its own popup
  from the grid's cell-focus event, when the last input was a key.
- **Screen reader.** An old cell reads `Not recent` after its value, and each
  typical cell's hover text is its accessible description. On the prototype
  the Chromium accessibility tree named an old cell `873.11, Not recent` with
  the hover as its description.
- **Header tooltips stay mouse-only,** as every column's are. The cell hovers
  say what the header says about the clock.

**Accepted cost.** Nothing on the page names the clock until a cell or the
header is hovered or focused; the mark itself stays on every old value, and
the user guide names it.
