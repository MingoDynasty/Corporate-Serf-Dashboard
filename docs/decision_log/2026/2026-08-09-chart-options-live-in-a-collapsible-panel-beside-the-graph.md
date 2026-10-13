# 2026-08-09: Chart Options Live In A Collapsible Panel Beside The Graph

Status: Accepted

The graph's display preferences used to open in a modal that dimmed the page
and blocked the chart behind it, so tuning an overlay meant adjusting, closing,
looking, and opening again. They now sit in a panel that slides out beside the
chart, which stays live and readable the whole time. On a narrow window the
same panel stacks above the chart instead. No preference changed what it does,
what it defaults to, or where it is stored.

Decision: `settings-modal`, `settings-modal-open-button`, and the `modal_demo`
callback are deleted. Their five chart preferences move into an in-flow
`chart-options-panel` beside `graph-content`, disclosed by a
`chart-options-toggle` button labelled "Chart options" and grouped under
*Overlays* and *Score Threshold* headings. `automatically-change-scenario-switch`
governs selection rather than presentation — it is the one moved control that is
not an input to `generate_graph` — so it is promoted out of the panel to sit
under the scenario selector. The panel starts closed on every visit and its open
state is not persisted.

Why: the container was adjudicated on a live-size interactive mockup built from
measured app geometry (1600×900, real element positions), not from taste. Open
plot area came out near-identical either way — stacked above the chart
1318×477 ≈ 629k px², beside it 1002×639 ≈ 640k px² — so the call fell to shape,
growth, and ergonomics, and all three favour the side panel: 1.57:1 stays
visually balanced where 2.76:1 reads wide and shallow, a vertical column absorbs
future controls without shrinking the chart further, and the panel can stay open
through sustained tuning. `dmc.Drawer` (a fixed overlay over the graph) and
`AppShellAside` (global chrome on every page) were rejected for the modal's own
reason: the graph is the only feedback surface these controls have. Folding them
into `/settings` was rejected earlier still — disjoint content, instant-apply
against deliberate-Save commit models, and no chart there to give feedback.

Consequences and constraints:

- **The flex role transfers; it is not duplicated.** `.home-chart-area` is now
  the direct flex child of `.home-page` and carries the `flex: 1 1 0` growth and
  the `min-height` floor that `.home-graph` used to hold. Leave those on the
  graph and the row falls back to intrinsic content height, so the graph stops
  consuming the remaining viewport.
- **`.home-graph` is a resize hook, not decoration.**
  `assets/homeGraphResize.js` locates graph containers by that class, and
  opening or collapsing the panel is exactly the
  container-resize-without-window-resize case Plotly does not redraw for on its
  own. The class and the script survive any future refactor of this row.
- **The reflow threshold is a container query, never a media query.**
  `@container home-chart-area (max-width: 62em)` measures the chart row's own
  box. The fixed 250px navbar shrinks the content area without touching the
  viewport, so a viewport threshold would keep the panel beside a chart it had
  already crushed — the same trap as
  [2026-08-03](2026-08-03-homes-controls-row-measures-the-content-area-not-the-window.md).
  62em is Mantine's `md` step, off the scale the controls grid already uses. A
  container query cannot match on the element that declares the container, so
  `.home-chart-area` declares it and `.home-chart-row` carries the layout.
- **Collapsing animates the track, and the row clips.** The inspector's grid
  track transitions between `0` and 20rem at `dmc.AppShell`'s own 200 ms rather
  than being removed, so the graph grows and shrinks the way it does when the
  navbar collapses. Two facts make that work: the panel holds its own width
  while the track moves under it, so it is revealed rather than squeezed; and
  `.home-chart-row` clips, because Plotly redraws exactly once ~200 ms *after*
  its container stops moving and until then is still drawn at its old width.
  The navbar hides that overhang by being fixed-position and painting over it;
  an in-flow panel has to clip from the other side. Stacked, there is no width
  to animate, so that mode sets the duration to zero.
- **Ids and defaults survive verbatim.** Dash persistence is keyed by component
  id, and changing a layout default silently drops every stored value, so all
  six preference inputs kept both across the move. Collapsed controls hide with
  `display: none` — mounted, in the layout tree, still feeding their callbacks —
  and are never conditionally rendered.
- **The toggle's `n_clicks` guard is unconditional.** Under DashProxy a
  callback can fire on initial page load despite `prevent_initial_call=True`,
  which here would spring the panel open on arrival. The panel's class *is* the
  open state and `aria-expanded` rides with it, so a regression test pins that
  both are unchanged before a real click.

**Superseded in part (2026-10-12).** The 62em threshold no longer applies. On
the Run History page, which replaced this one, the panel stacks above the
chart when the chart's own area is 48em or narrower: the run list now takes
a column beside the chart, and 62em would have stacked the panel in every
window narrower than about 1,760 px. "Ids and defaults survive verbatim" was
set aside once, for the move to a new page that keeps control ids of its
own, and it stands for every later change. The panel beside the chart, the
container query, the clipping row, `.home-graph` as the resize hook, and the
toggle's guard all stand. See
[The Run List Is A Second Column Beside The Chart](2026-10-12-the-run-list-is-a-second-column-beside-the-chart.md)
and
[Run History Keeps Its Own Control Ids, So Every Browser Saw The Defaults Once](2026-10-12-run-history-keeps-its-own-control-ids-so-every-browser-saw-the-defaults-once.md).

Shipped in PRs #209 and #215; design discussion in #206. This entry and
[the naming entry](2026-08-09-the-graph-page-is-scenario-performance-its-panel-is-chart-options.md)
distil `docs/chart_options_inspector_proposal.md`, now deleted.
