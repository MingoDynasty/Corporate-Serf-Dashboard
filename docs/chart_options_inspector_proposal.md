# Chart Options Inspector Proposal

Status: In progress
Date: 2026-08-04

## TL;DR

The Home graph's display preferences live in a modal that dims and blocks
the chart while the user adjusts them, and that modal is named "Settings"
even though the app has a separate Settings page. This proposal retires the
modal and moves its controls into a collapsible panel beside the chart, so
every adjustment shows on the live chart immediately. On narrow windows the
same panel stacks above the chart instead. The one control that governs
scenario selection rather than the chart moves next to the scenario
selector, and no setting changes its meaning, default, or storage.

## Decisions needed

None — all ruled. The container, naming, scope boundaries, and open-state
calls were ruled by the maintainer on 2026-08-04 after a live-size mockup
comparison, with both AI reviewers concurring; the last open item,
Follow-switch placement, was ratified on 2026-08-08 (promoted out of the
panel to sit by the scenario selector; an in-inspector "Behavior" group
was the rejected alternative).

## Problem

- The modal (`settings-modal`, opened by `settings-modal-open-button`,
  title "Settings", inner heading "Display Settings") holds six page-scoped
  preferences, all client-persisted (`persistence=True` → browser
  localStorage, no server write): `automatically-change-scenario-switch`,
  `rank-overlay-switch`, `high-score-overlay-switch`,
  `score-threshold-overlay-switch`, `score-threshold-percentage`,
  `score-threshold-notification-switch`.
- Four of the six change the chart immediately, and the chart is their only
  feedback surface — but `dmc.Modal` dims the page behind an overlay and
  blocks interaction with it, so tuning is an open-close-open loop against
  a dimmed chart.
- Three surfaces answer to the name "Settings": the navbar link to
  `/settings`, the Home button, and the modal title — two with the same
  icon. The surfaces are different in kind: `/settings` edits
  server-persisted app setup (stats folder, identity) through one validated
  Save with restart semantics; the modal edits instant-apply browser
  preferences.
- Merging the modal's controls into `/settings` was considered and
  rejected: disjoint content, opposite commit models (instant apply vs
  deliberate Save), no chart on `/settings` to give feedback, and the
  repo precedent that controls live on the surface that owns their effect
  (playlist management moved off this same modal to `/playlists` — the
  2026-07-11 decision-log entry).
- `dmc.Modal` never mounts in the automated browser pane, so the current
  surface cannot be live-verified; an in-flow panel can.

## Design

**Adjudication.** Above-chart tray vs right-side inspector was decided on a
live-size interactive mockup built from measured app geometry (1600×900,
light scheme, real element positions):
<https://claude.ai/code/artifact/7cead5fd-7230-495c-8548-1d9479a92fc3>
(private artifact; reviewers without access can rebuild the numbers from
the geometry below). Open plot areas are nearly equal — stacked-above
1318×477 ≈ 629 k px², right inspector 1002×639 ≈ 640 k px² — so the choice
is shape, growth, and ergonomics, and all three favor the inspector: the
1.57:1 chart stays visually balanced where 2.76:1 reads wide and shallow;
a vertical panel absorbs future controls without shrinking the chart
further; and the panel can stay open through sustained tuning. Ruled:
responsive right-side inspector, with the stacked-above layout kept as the
narrow-width mode of the same design, not a competing one.

**Layout.**

- Page-local, in-flow inspector on the Home page. Not `dmc.Drawer` (a
  fixed overlay that covers the graph), not `AppShellAside` (global chrome
  shared by every page).
- The chart row is a CSS grid: graph track `minmax(0, 1fr)` — the `0`
  matters, Plotly overflows grid/flex tracks without it — beside an
  inspector column of ~19–20 rem.
- The chart row replaces `.home-graph` as the direct flex child of
  `.home-page` (a flex column pinned to the viewport height), so the
  chart-row class must take over the `flex: 1 1 0` growth and the
  `min-height` floor that `.home-graph` carries today — otherwise the row
  falls back to intrinsic content height and the graph stops consuming the
  remaining viewport. `.home-graph` keeps filling its grid track inside
  the row.
- Collapsed, the inspector column is removed and the graph returns to full
  width. The panel starts closed on each page visit; its open state is not
  persisted (ruled — the maintainer's stated usage, collapsed most of the
  time, was given container-neutrally, so the call carries to the rail).
- Narrow windows: the same DOM re-flows so the inspector stacks above the
  chart. One component tree, one set of ids, no duplicated controls across
  modes. The reflow threshold must measure the chart row's own available
  width — a CSS container query, the same mechanism PR #199 gave the
  controls grid (`type="container"` emits `@container` rules that measure
  the grid rather than the window) — never a viewport `@media`: the fixed
  250 px navbar shrinks the content area without touching the viewport,
  so a viewport threshold would keep the inspector beside the graph while
  crushing it. Take the threshold value from the existing
  `HOME_GRID_BREAKPOINTS` scale rather than inventing a token, derived
  from minimum useful chart width (author-owned), and validate both
  navbar-open and navbar-closed states around it.
- Plotly redraws a responsive graph only on window `resize` events;
  container-driven redraws on Home come from `assets/homeGraphResize.js`,
  whose ResizeObserver locates graph containers by the `.home-graph`
  class. That script and its class hook must survive the refactor
  unchanged — opening and collapsing the inspector is exactly the
  container-resize-without-window-resize case it exists for. The graph
  component itself does not change.

**Disclosure.** The Home "Settings" button becomes **"Chart options"**
(name adopted 2026-08-04), with a disclosure chevron and the full
disclosure contract: the panel has a stable id, the button carries
`aria-controls` naming it alongside `aria-expanded`, and the collapsed
class hides with `display: none` (or equivalent) so hidden controls leave
the tab order and accessibility tree while staying mounted for Dash.
`/settings` keeps the name "Settings" — the collision is resolved from the
Home side (ruled; an "App setup" rename was considered and rejected).

**Contents.** Five controls, grouped by user concept rather than kept as a
flat list:

- *Overlays* — `rank-overlay-switch` ("Playlist rank lines"),
  `high-score-overlay-switch` ("Personal-best line").
- *Score goal* — `score-threshold-overlay-switch` ("Show goal line"),
  `score-threshold-percentage` ("Goal percentage of PB"),
  `score-threshold-notification-switch`. Label caveat pinned during design
  review: since the notification redesign, this switch gates only whether a
  run is judged against the goal (`_threshold_verdict` returns None when it
  is off) — placement toasts still fire regardless. Its label must not
  claim to control run notifications wholesale; "Show goal verdict" is
  the recommended copy — it names the effect inside the run toast without
  implying placement toasts are gated — and the existing help tooltip
  ("Notifies after each new run whether it reached the score threshold")
  is already accurate and carries over unchanged.

The three "Score Threshold *" controls are one user concept; a Score goal
group makes the relationship explicit. Help tooltips (`SETTINGS_HELP_TEXT`
via `_settings_help_label`) carry over per control.

**Promotion (ratified 2026-08-08).** `automatically-change-scenario-switch`
governs what the scenario selector does when a new run lands — selection
behavior, not chart presentation; the callback wiring corroborates the
taxonomy mechanically, since it is the one moved control that is not an
input to `generate_graph`. It moves out of the panel to sit by the
scenario selector, relabeled "Follow newly played scenario". Exact spot is
the implementer's: the mockup placed it directly under the selector, but
that measurement predates the header-responsiveness rework (PR #199
changed exactly this geometry), so re-measure the header fit at build
time — the ratified placement rests on the association argument, not on
the stale row-1-gap figure.

**Header.** Everything else stays put and visible: playlist filter,
scenario selector, Top N, oldest date, axis radio, Scenario Stats, Refresh.
Top N and oldest date are data filters — hiding filters makes an empty
chart inexplicable — and the axis radio is the primary analysis mode.

**Invariants.**

- The six preference inputs keep their component ids and defaults, so
  localStorage-persisted values survive the move (Dash persistence is
  keyed by component id; changing a layout default silently wipes every
  stored value).
- Collapsed controls are hidden with a semantic CSS class (per the repo's
  styling conventions), never conditionally rendered — they stay mounted
  and keep feeding their callbacks.
- `settings-modal`, `settings-modal-open-button`, and the `modal_demo`
  callback are deleted; the disclosure button may take a new id, since no
  persisted props ride on buttons.
- The inspector gets its own vertical scroll if its content ever outgrows
  the graph column.

**Page identity.** "Scenario Performance" was adopted as the page's product
name (ruled 2026-08-04). With the route restructure deferred, this is a
labels-only rename — navbar link text, page title/display name, doc
vocabulary — with `/`, `/home`, `/index` redirects untouched. It ships as
its own small PR (delivery plan below).

## Delivery plan

- **PR 1 — the inspector.** Replace the modal with the collapsible
  responsive inspector; promote the Follow switch; regroup and relabel per
  above; semantic CSS in `assets/stylesheet.css`; update
  `docs/architecture.md`'s Home description (and README if it mentions the
  modal); tests below. No hard dependencies.
- **PR 2 — "Scenario Performance" labels.** Navbar link, page
  title/display name, doc sweep. Independent of PR 1; soft-ordered after
  it so the rename lands on the new layout's text.

## Out of scope

- Route restructure (`/` reserved for a future Overview page, a durable
  `/scenario` route): deferred until an Overview has concrete plans
  (ruled 2026-08-04).
- Any Run History surface. The maintainer's current thinking (2026-08-08)
  has Run History — possibly a compact version — living on the page's
  right side someday, Home-tied or app-wide undecided. This proposal's
  inspector therefore claims no exclusive tenancy of the right rail: it
  is a page-local column that a later design may share, stack with, or
  re-host. If Run History does become Home-tied, it composes into this
  same rail/stack rather than adding a second side column. How the two
  coexist is the run-history proposal's question, not this one's.
- Renaming the `/settings` page — it keeps "Settings".
- Splitting Top N's dual role (plot density and top-N notification
  qualification): a documented coupling; no evidence two values are
  wanted.
- Axis radio → `SegmentedControl` polish: independent, not required to
  retire the modal.
- Any change to what a setting does, its default, or where it persists.

## Testing

- Update the two structure assertions in `tests/test_home_rank_format.py`:
  the "Display Settings" title assertion is replaced by
  inspector-structure assertions, and the per-control help-tooltip
  assertion follows the controls into the inspector (coverage per control
  id, not per container).
- New assertions: the five inspector inputs and the promoted Follow switch
  exist with unchanged ids and defaults; no `settings-modal` remains in
  the layout; the collapsed state is a CSS-class change, not removal (all
  controls remain in the layout tree).
- The disclosure toggle writes state by definition — the panel class *is*
  the open state, and `aria-expanded` rides with it — and under DashProxy
  `allow_duplicate` callbacks can fire on initial page load despite
  `prevent_initial_call=True`. The `n_clicks`/trigger guard and the
  None-trigger regression test are therefore unconditional: before a real
  click, both the panel class and `aria-expanded` must be unchanged.
- Live check in the implementation PR: open the inspector in the browser
  pane (it is in-flow DOM, unlike the modal), toggle an overlay, confirm
  the chart updates without dimming, and confirm the chart resizes cleanly
  on open/collapse — if Plotly misbehaves during an animated width
  transition, drop the transition. Exercise the open and closed layouts
  with the navbar both open and closed around the reflow threshold, not
  only at the 1600×900 reference size. Reload before judging the console;
  the known first-load Dash race is unrelated.
- Gates: the standard five local commands.
