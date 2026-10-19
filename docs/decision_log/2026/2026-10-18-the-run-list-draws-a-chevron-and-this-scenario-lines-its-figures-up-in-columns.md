# 2026-10-18: The Run List Draws A Chevron, And This Scenario Lines Its Figures Up In Columns

Status: Accepted

A session row and a scenario row now open and close on the app's own
chevron, which points right when the row is closed and down when it is open,
in place of a small triangle that read as a dot. Under This scenario, with
Median and best on, each session row's median, best, and run count line up
in columns down the list, every value on its decimal point, with space
between the columns and no dot. A session with one run shows its score under
Best, labeled Score, with the Median column left blank.

**Rulings.** By the maintainer, 2026-10-18, in the design chat that compared
versioned mockups built from their own runs: "Ruled: the chevron at 16 px in
gray, columns by decimal points with space between, one-run score under
Best. Build it as a PR after #393 merges." The ideas were theirs: the arrows
were "difficult to distinguish between expanded vs collapsed, and actually
looks closer to a dot", and This scenario's figures were to read "more like
a table" so they could "visually compare Median and Best across sessions".
Against dots between the columns: "it actually makes the decimal numbers
slightly harder to read". The one-run placement followed a second opinion
that it keeps the phrase `Score {score}` both views already read. This
supersedes, for This scenario's session rows, the dots and the one-run
wording in "What the line says" of
[the 2026-10-18 figures-line entry](2026-10-18-median-and-best-sit-in-the-rows-own-line-ahead-of-its-count.md).
What the list does today is in
[run_history.md](../../specs/run_history.md#the-run-list).

**The chevron, both views.** It is the icon Chart options, the Columns menu,
and Settings draw at 20px. Here it is 16px, in the toggle's dimmed gray,
inside the toggle's 14 by 16px box, so no row grows and nothing beside it
moves.
Measured at 2x in Firefox: its ink is 4.5 by 8px closed, where the triangle's
was 4 by 4.5. The session date (13px, weight 600) has digits 9.5px tall, so
at 16px the chevron stays under them and the date is still what a row shows
first; at 20px its ink, 6.5 by 10, stood taller. The button keeps its name
and `aria-expanded`, and the drawing is hidden from a screen reader.

**The columns, This scenario only.**

- A session row with figures in its line reads `Median {m}`, `Best {b}`, and
  `{n} of {m} runs` as three columns, 16px apart. Each label stays on every
  row, right-aligned against its value. A value's whole number is
  right-aligned in room as wide as the column's widest whole number, and its
  decimals follow in room as wide as the column's widest decimals, so whole
  numbers line up exactly and a value with decimals sticks out to the right.
- One run: `Score {s}` in Best's column, and Median's column blank, unseen,
  and out of the accessibility tree. Best's label has room for Score only
  where some session of the scenario has one run.
- The count takes a column only on a row whose figures are in its line; a
  count alone already ends at the row's edge.
- The first row keeps its figures on a second line (`figures_below`). That
  line ends short by the count's column and the space before it, so its
  Median and Best sit over the rows below. With no row below, it ends at the
  edge.
- Every column's width comes from every session the view can list, loaded
  or not, so Show older sessions never moves a column. The count's column
  leaves out the first row's count, which is in no column and grows with
  every run played. On the maintainer's data, only two scenarios had more
  than 30 sessions, and neither's older sessions held a wider value; the rule
  costs nothing there and holds where it would.
- All scenarios is unchanged apart from the chevron: its rows are different
  scenarios, so columns would compare nothing.

**How the widths are made.** The server names the widest text of each part
of each column: the most characters, then the most digits. The list draws
its digits tabular, every digit one width and wider than a comma, a point,
or the plural s, so that ranking is the browser's. Each part holds that text
unseen in the same grid cell as its value, and the browser makes the part as
wide as the wider of the two, by the layout that draws the text. The other
way, the script measuring each width and setting it, would be right only at
the zoom and with the font it measured, and only once the list was drawn.
The list's font, Segoe UI, already draws its digits tabular, so
`tabular-nums` changes nothing there.

**Traps the mockups and the build found.**

- An empty box between two columns puts no space in the text a screen
  reader is handed: Chrome and Edge read "17,080Best". Nor does a bare space
  between two parts, though they draw it: the build's first pass read
  "Median17,080" and "Score16,170". Every space between parts is a character
  in a box of its own, 16px wide between columns, and the build's text was
  read through CDP on every session row.
- A blank column must take the same room as the column it stands in, or its
  row shifts: the mockup's first build was 22px off on one-run rows. The
  blank is the column itself, drawn empty and hidden.
- A part's first child gives it its baseline, and an empty value has none:
  with the value first, a part with an empty value stood on the line by its
  bottom edge and the line grew 3px (Firefox and Edge). The unseen text goes
  first.

**What being wrong costs.** The chevron is a stylesheet rule and one span.
The columns are a few functions of the list's script, split figures and one
model field from the server; going back to the dotted line is the same size.
