# 2026-10-23: Run History Links Chart And List Runs On Hover

Status: Superseded in part by the [one-row hover decision](2026-10-23-run-history-hover-outlines-one-list-row.md)
and the [run opening decision](2026-10-30-a-run-opens-in-the-charts-place-and-close-or-esc-closes-it.md)

Hovering a run links its chart marker and visible list row. When the run is
inside collapsed content, its Session row is highlighted instead. This helps
players connect scores with session context while keeping their place in
both views.

**Superseded in part (2026-10-23).** The [one-row hover decision](2026-10-23-run-history-hover-outlines-one-list-row.md)
replaces the Session-only fallback. A hidden run now outlines the most
specific row exposed by expansion: its Scenario row under All scenarios,
otherwise its Session row. The remaining interaction rules stay in force.

**Superseded in part (2026-10-30).** [A Run Opens In The Chart's Place](2026-10-30-a-run-opens-in-the-charts-place-and-close-or-esc-closes-it.md):
a click on a run point, a PB star or a Run row opens that run in the run
viewer, so click actions are no longer out of scope. Opening or closing a
run clears the emphasis. Every hover statement here stands.

**Direction.** The maintainer chose bidirectional hover, then limited the
first implementation to visible run rows and a Session-row fallback for
collapsed content. Automatic scrolling, opening groups, loading older
sessions, and click actions remain out of scope.

**Contract.**

- A chart run point or PB star highlights its corresponding run row in
  either list view. If a session or scenario group hides that run, its
  containing Session row is the target, including the pinned current session.
- A visible run row highlights that run's visible dot or PB star in the
  current chart. A row outside the chart's selected scenario or range has
  no marker to highlight. Session-row hover does not highlight a group of
  points.
- The effect is immediate and transient. Leaving the target, scrolling the
  list, changing its model or expansion state, redrawing the chart, or
  leaving the page clears it. It never moves keyboard focus.
- An off-screen or unloaded counterpart yields no visible cross-highlight.
  Hover changes neither list position nor expansion, chart axes, selection,
  or the number of sessions loaded. Normal incoming-run and Follow behavior
  remains as specified.
- Grape outlines identify temporary links independently of the blue
  latest-run highlight and the selected-scenario band. Point colors, sizes,
  PB-star shapes, and the latest-run ring return unchanged on unhover.
  A linked PB star retains its gold fill.
- Run and star traces carry the same filename-based run IDs as the list.
  Point indices, rounded scores, and timestamps are never identity. A star
  carries its run's tooltip too, so hiding ordinary dots still leaves its
  hover identifiable. Coincident points identify the run their tooltip names.
- The interaction runs in the browser with no hover callback to the server.
  Only SVG run markers are styled, with their IDs re-indexed after a plot.
  Plotly's SVG calcdata binding is covered by real-browser tests against the
  locked renderer. The [dependency refresh playbook](../../dependency_refresh.md#packages-that-ship-browser-code)
  requires them for plotly and dash-ag-grid bumps; skipped tests do not count
  as a pass.

Current behavior is specified in [Run History](../../specs/run_history.md).
