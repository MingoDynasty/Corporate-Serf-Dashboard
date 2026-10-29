# 2026-10-22: The Run List Can Shrink To 480px When Columns Are Hidden

Status: Superseded in part, 2026-10-29, by
[the marks column's entry](2026-10-29-the-run-lists-marks-column-is-30px-and-three-columns-share-its-spare-room.md) and
[the card's new width](2026-10-29-the-latest-run-card-is-as-wide-as-the-run-lists-minimum.md).

Hiding run-list columns can now return a little more room to the chart.
The list can shrink to 480px while its controls stay on one line.
Its default columns still need 500px, and changing the list's width leaves
the top-row cards in place. Long scenario names can be cut short sooner.

**Superseded in part (2026-10-29).** [The marks column's entry](2026-10-29-the-run-lists-marks-column-is-30px-and-three-columns-share-its-spare-room.md):
the need is 19px plus every shown column's width, and with Shots Fired
hidden to start the default columns need 407px, so the default list sits
at this entry's 480px minimum, which the page also draws before the column
choices load. [The card's new width](2026-10-29-the-latest-run-card-is-as-wide-as-the-run-lists-minimum.md): the latest-run
card is 480px, the minimum, so the two line up. The minimum, the width
rule and the header stand.

**Maintainer direction, 2026-10-22.** After asking whether hidden columns
should reduce the list further, the maintainer authorized the measured
480px minimum and its implementation. This supersedes the 500px minimum in
[the column-fitting rule](2026-10-22-the-run-list-grows-to-fit-the-columns-it-shows.md)
and the equality of the minimum and card widths in
[the latest-run card's entry](2026-10-22-the-latest-run-card-keeps-a-500px-width-of-its-own.md).
The rest of those decisions stands.

**The width rule.** The list takes
`clamp(480px, need, max(500px, room - 480px))`, where `room` is the chart and
list's shared width less their 16px gap. The need remains 64px plus the
fixed widths of the shown columns. Hiding Sensitivity with the other
columns at their defaults makes the need 404px, and hiding every menu
column makes it 322px; both lists stop at 480px. The default need is still
500px, and the maximum's 500px floor preserves the default list's room in
narrow windows. A list whose columns need more room still grows and scrolls
sideways by the previous rule.

**Why stop at 480px.** The header also needs room for the view switch,
Expand all and Columns. Collapse all is wider than Expand all, so fitting
only the latter is not sufficient. Shrinking the list further would wrap
the controls and take height away from the runs. The 500px default width
is used before the column-choice callback runs, avoiding a new mount-time
shift on the default page.

**Independent cards and stacked pages.** The latest-run card stays 500px
wide. A list reduced to 480px starts 20px further right than that card;
its freed width goes to the chart. No top-row card moves or resizes.
At a page area of 900px or less, the list still stacks above the chart and
takes the page's full width. Rows keep the same data, but long scenario
names in All scenarios can be cut short sooner at 480px. Hovering a scenario
name still gives its full text. Column persistence, marks, scrollbar room
and control labels are unchanged.

**Verification.** Edge 155.0.4283.62 and Firefox 158.0.1 each pass 128
geometry observations: window widths 2,560, 1,920, 1,536, 1,280, 1,200,
1,158, 1,157 and 900px; both list views; default columns, Sensitivity
hidden, every menu column hidden and every column shown; Expand all and
Collapse all. The old CSS keeps hidden columns at 500px, and the new CSS
lets them reach 480px. The header stays on one line at the minimum, card
geometry is unchanged across column choices, and stacked pages retain
their full-width list. Saved hidden columns return at 480px after reload,
and the initial CSS fallback remains 500px.
