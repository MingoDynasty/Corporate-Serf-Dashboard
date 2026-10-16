# 2026-10-14: Run History's Top Row Has One Card Per Kind Of Information

Status: Accepted

Run History stacks its two dropdowns and gives the scenario, its personal
best, and the latest run their own cards. The latest-run card sits directly
over the run list, so the target and result are close without spending the
row on empty space. A small Follow switch sits under the scenario dropdown,
and the row keeps room for a later notes feature.

**Rulings and delivery.** T1 of [#379](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/379),
ratified by the maintainer on 2026-10-14 at `7329c23`: "I ratify Proposal 1,
rows T1 to T4, as amended at 7329c23." The layout shipped in
[#380](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/380),
the PB card in [#383](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/383).
The proposal is retained in those PRs and git history; current behavior is in
[run_history.md](../../specs/run_history.md#the-top-row).

The row and the chart/list below share two columns, the second 500px wide,
with the same gap. The first column holds the dropdown column, Scenario
Stats, empty room with no element reserving it, and the PB card at the right
end. Every card stretches to the row's height. Stacking the dropdowns frees
the width that lets both score cards fit at the maintainer's design width.
The Playlist filter's label line carries Open scenario table while a
playlist is selected, with no room reserved when it is not.

**Amendment, 2026-10-15.** After inspecting #380 in Firefox, the maintainer
replaced the ratified Follow switch placement on the scenario label's line:
"It doesn't look very good between sandwiched between two dropdown menus."
It goes under the scenario dropdown, "accepting the taller row", with
"xs track, 14 px text, 16 px help icon" and the gaps kept. The measured row
is **141.4px at 2560px**, replacing the proposal's 132px. This ruling is part
of T1's entry, rather than a separate decision. The dropdowns' behavior,
remembered values and Follow semantics do not change.

The maintainer's resolution priority, set on 2026-10-14, is 4K first, 1440p
second, and 1080p only where it costs the other two nothing. The first
column wraps its pieces in order as its own room shrinks, with the PB card
wrapping first. At a page area of 900px or less, the row is one wrapping
line in order: dropdowns, Scenario Stats, PB, latest run; the run list moves
above the chart. This follows the existing content-area rule, rather than
using the window's width as the available room.

This replaces only the top-row layout in
[the run-list decision](2026-10-12-the-run-list-is-a-second-column-beside-the-chart.md).
The run list's width and its relation to the chart stand. Side-by-side
dropdowns consumed room and made the row taller; spreading facts outside
cards obscured their groups. Notes, and the latest-run card following the
selection, remain separate work.
