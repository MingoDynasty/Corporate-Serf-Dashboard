# 2026-10-29: The Run List's Marks Column Is 30px, And Three Columns Share Its Spare Room

Status: Accepted

The run list's check and star now sit in a 30px column beside the score,
whatever columns are shown. Before, that column took whatever room the
list's width left, from 50px to over 200px, so the marks drifted away from
the score they describe. Spare room now goes to the columns the Columns menu
can't hide, in proportion to their widths. The list keeps its width rules,
its 480px minimum and its header.

**Maintainer direction, 2026-10-29.** On 2026-10-27 the maintainer asked
whether to shrink the column, "much wider than is needed to fit the two
symbols", and leaned toward a list that fits its content: "Why not just
simply resize the entire Run History panel so it autosizes with the
content? I don't see a point to showing all this whitespace if we can free
up that space for the chart instead." Two advisory consults,
`claude-fable-5-1` and `gpt-6.1-sol` at xhigh, each found that the list's
rows, not its columns, set how narrow it can go. Live copies of four layouts
followed. The maintainer set the test, "The goal is to efficiently manage
the whitespace. If we must have whitespace, then it should be for a good
reason", rejected two-line session rows, "C is the worst option because now
the session stats get put on a new line, which creates even more
whitespace", and chose: "The only option that seems reasonable so far is
basically just option B, but only shrinking the Latest Run so that it lines
up with the Run History panel's minimum width." Then: "Which also implies
that the Run History panel stays as-is, since we could not find a better
alternative." Asked which version of that to build, the maintainer answered
"Copy A". What the list does today is in
[run_history.md](../../specs/run_history.md#the-run-list).

**The rule.**

- **The marks column is fixed at 30px**, one allowed width, as the other
  fixed columns have. The check is 10.0px and the star 10.2px wide (9.8px
  in Edge), in the cell's 4px padding each side.
- **`#`, Time and Accuracy share spare room.** Each has `flex` equal to its
  width (50, 66 and 70px) and a `minWidth` 5px under it (`SHARING_GIVE`).
  The room the list's minimum leaves over the shown columns splits by
  width, and in a window where the chart's floor binds the three give 15px
  together before the list scrolls sideways. Only columns the menu can't
  hide share: the menu's `autoSizeColumns` takes `flex` off a column it
  shows.
- **The list needs `RUN_LIST_ROOM`, 19px, plus every shown column's width,**
  the marks column's included. The 19px is the list's two borders and a
  classic scrollbar's 17px. With Shots Fired hidden to start
  ([its entry](2026-10-29-the-run-lists-shots-fired-column-starts-hidden.md)),
  the default columns need 403px, so the default list sits at its 480px
  minimum. Shots Fired adds 82px, Reloads and Avg FPS 64px each, FOV 116px,
  and every column together needs 729px.
- **A scrollbar drawn over the rows** takes its 12px from the 17px the list
  keeps for a classic one. The sharing columns have the other 5px, and all
  17px where no scrollbar shows.
- **Unchanged:** the width rule `clamp(480px, need, max(500px, room − 480px))`,
  the 480px minimum the header needs, the text buttons and the view switch.
  Before the page's script writes the need, the list takes its minimum, the
  default columns' width, so the default page doesn't shift as it mounts.

**Measured** in Firefox 158 with overlay scrollbars, at 2560 CSS px, on the
maintainer's stats, VT DotTS Intermediate S5. Before: the marks column was
50px with the default columns, 126px with Sensitivity hidden, 208px with
every optional column hidden, and 112px with Shots Fired hidden. After, with
the default columns, the list is 480px, the marks column 30px, and `#`, Time
and Accuracy 72, 95 and 101px. Every session row fits at 480px with Median
and best on, across all 329 of the maintainer's sessions open in All
scenarios.

**Alternatives set aside,** each built as a live copy and measured as above.

- **A list exactly as wide as its columns, with icon buttons and a 318px
  minimum.** The rows set the floor: a session row with its facts, its count
  and Show all runs needs about 450px in All scenarios, and about 445px in
  This scenario with Median and best on. At 389px those rows overflowed by
  21 to 55px, at 318px 34 of 35 scenario names were cut, and the icon header
  still wrapped at 318px in Edge. Both consults found the row floor
  independently.
- **Spare room after the last column**, a blank strip under the full-width
  session rows, whose counts sit at the right edge.
- **Session rows on two lines**, which let the list fit its columns at
  397px: rejected by the maintainer as more whitespace, not less.
- **A width that follows the view**, narrow under This scenario and wider
  for All scenarios or Median and best, and **filling the minimum's room
  with Shots Fired**: offered, not chosen.
- **Expand all as an icon, with a 460px minimum.** The widest session rows
  then fit with 0 to 1px to spare, and 112 scenario names were cut in All
  scenarios with Median and best on, against 65 at 480px.
- **The marks column fixed at 45px**, which kept the default list at 500px
  and the latest-run card where it was, but left the default view's column
  as wide as the maintainer first noticed.
