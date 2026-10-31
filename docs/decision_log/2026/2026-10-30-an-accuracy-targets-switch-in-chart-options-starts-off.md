# 2026-10-30: An Accuracy Targets Switch In Chart Options Starts Off

Status: Accepted

Chart options gains an Accuracy targets switch after Show all ranks, off
until the player turns it on. While it is off, or Rank thresholds is off, the
chart is exactly as it was. Its default can't change later without resetting
the choice every browser has stored.

**Ruling.** AT4 of
[proposal #449](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/449),
ratified by the maintainer on 2026-10-30 ("I ratify"). Before that, their
direction, 2026-10-29: "Accuracy Thresholds should not show by default; it
should be toggle-able via a setting. In most cases it's something I would
toggle a few times just to gauge the numbers, but probably not something I
would leave on all the time, mostly because of graph clutter (unless we can
manage that clutter somehow)." The author put the switch in Chart options,
where the maintainer saw it in the second mockup. Shipped in
[#452](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/452).
What the panel does today is in
[run_history.md](../../specs/run_history.md#chart-options-panel).

**The switch.**

- `dmc.Switch`, id `run-history-accuracy-targets-switch`, in Overlays after
  Show all ranks, `checked=False`, `persistence=True`, labelled `Accuracy
  targets`. The panel's eleventh control
  ([2026-08-09](2026-08-09-chart-options-live-in-a-collapsible-panel-beside-the-graph.md)).
- Its help text: "Shows beside each rank line an estimate of the accuracy
  that rank needs when you hold the fire button for the whole run. It's
  calculated from your runs, on scenarios where your score follows your
  accuracy, such as tracking. Needs **Rank thresholds** turned on." The
  bold name is built with `control_name()`, as Show all ranks' is. "The
  fire button" rather than Mouse 1, since the game lets a player rebind it.
- An Input of the chart rebuild, as Show all ranks is, passed to
  `build_run_history_figure` as `accuracy_targets_switch`. The score at 100%
  is worked out only while it and Rank thresholds are both on.
- **Its id and default never change,** as every remembered control's
  ([2026-10-12](2026-10-12-run-history-keeps-its-own-control-ids-so-every-browser-saw-the-defaults-once.md)).
  Dash stores a remembered value with the layout default it was saved
  against and drops it when that default changes, so turning the switch on
  by default in a later release would turn it on in every browser,
  including those that had turned it off.

**Why.**

- **Chart options.** The switch is flipped a few times while looking at the
  chart, and the rank lines' own switches are there. The Settings page is a
  page away from the chart.
- **Off, even though the margin keeps the plot clear.** The maintainer's
  direction. The margin placement
  ([AT3's entry](2026-10-30-accuracy-targets-sit-beside-the-rank-lines-in-the-charts-right-margin.md))
  is what would let a later release consider turning it on, and the reset
  is the price of doing so.
