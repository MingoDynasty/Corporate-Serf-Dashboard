# 2026-10-30: Accuracy Targets Sit Beside The Rank Lines In The Chart's Right Margin

Status: Accepted

Each drawn rank line's accuracy target sits just outside the plot's right
edge, level with the line, in the chart's ordinary text color. The plot keeps
its width, because the figures fit in the margin the chart already leaves,
and the rank labels don't change. Only rank lines get targets, not the PB
line or the score threshold line.

**Ruling.** AT3 and AT6 of
[proposal #449](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/449),
ratified by the maintainer on 2026-10-30 ("I ratify"), AT3 as amended in
review. Before that, the maintainer's choice, 2026-10-30, between the two
placements of the second mockup: "Right margin". Review dropped the
mockup's 64 px right margin for Plotly's default. Shipped in
[#452](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/452).
What the chart does today is in
[run_history.md](../../specs/run_history.md#the-chart).

**The placement** (`_add_accuracy_targets` in `source/plot/plot_service.py`):

- One figure per drawn rank line whose target is at most 100%: exactly the
  lines `_add_rank_overlays` draws, the ranks around the plotted scores or
  the whole ladder with Show all ranks on
  ([2026-10-12](2026-10-12-the-run-history-chart-plots-every-run-and-draws-no-summary-line.md)).
  The selection is shared, never repeated. All three chart modes, since
  they share the rank lines.
- An annotation at `x=1`, `xref="paper"`, `xanchor="left"`, `xshift=6`,
  `y=threshold`, `yref="y"`, `showarrow=False`, with no font of its own, so
  it takes the theme's text color and the chart's 14 px.
- **No margin changes.** The chart sets no margin of its own and its legend
  sits above the plot, so the right margin is Plotly's default 80 px, which
  holds the widest figure, `100.0%`. The plot's width never changes with
  the switch or the scenario.
- **Zoomed,** Plotly drops a figure whose line leaves the view, so only the
  lines in view keep their figures.
- The lines and their labels, `{rank} ({threshold})`, are unchanged.

**Why.**

- **The margin.** It adds no text inside the plot. The first mockup, and
  the second's other placement, put the figure in each label,
  `Saffron (2350 · 39.2% accuracy)`, which doubled every label's length.
- **Not the rank's color.** The second mockup drew each figure in its
  rank's color, and the pale ones (Lavender, Celadon, Diamond) could not be
  read on the light theme. The line beside the figure carries the color.
- **Rank lines only.** The PB card already shows the PB run's accuracy. The
  score threshold line could take the same rule, but it moves with the PB
  and the percentage, and the maintainer asked about rank thresholds; a
  later change can add it with nothing here in its way.

**Rejected.** **In the label,** and **in the rank's color,** above. **A
second y axis** with ticks at the thresholds: the same place as the margin
figures, but its range would have to be kept matched to the score axis's
through every zoom, where an annotation tied to the score axis needs
nothing.
