# 2026-10-23: Run History Hover Outlines One List Row

Status: Accepted

Hovering a chart run now outlines one matching list row. Collapsed content
moves the outline to the most specific group row available. This keeps the
hovered run's location clear without adding outlines around its ancestors.

**Direction.** Ruled (user) 2026-10-23: adopt one outline per hovered run,
using the most specific row exposed by expansion. The Session-only fallback
could leave the player looking at another scenario without realizing where
the run belonged. Outlining the exact Scenario row, identified by visit ID,
locates its containing group while keeping one clear hover target.

**Contract.**

- A chart run point or PB star targets its Run row when the expanded hierarchy
  exposes that row. An expanded Scenario visit receives no additional outline.
- If the Run is hidden by a collapsed visit under All scenarios, only the
  exact containing Scenario row is outlined. Its Session gets no additional
  outline. Repeated visits to the same scenario remain distinct by visit ID.
- If the Session is collapsed, only its Session row is outlined, including
  the pinned current session. The **This scenario** view has no Scenario
  rows, so its fallback goes directly from Run to Session.
- Expansion state chooses the target, independently of scroll position. An
  off-screen Run in expanded content remains the target even if its Scenario
  header is visible. This can produce no visible outline. Hover neither
  scrolls to a match nor opens groups or loads older sessions.
- Grape identifies the temporary link. Hover preserves the selected-scenario
  band, latest-run highlights, marker preferences, PB-star fill, row geometry,
  focus, selection, and chart axes. Unhover, list scroll, model or expansion
  changes, chart redraw, page departure, and an unmatched hover clear the link.
- The reverse interaction remains run-based. Hovering a Run row emphasizes
  its dot or star; hovering a Scenario or Session row does not emphasize a
  set of chart points. Click actions are unchanged.

This replaces the Session-only fallback in the [original linked-hover decision](2026-10-23-run-history-links-chart-and-list-runs-on-hover.md).
Current behavior is specified in [Run History](../../specs/run_history.md#linked-hover).
