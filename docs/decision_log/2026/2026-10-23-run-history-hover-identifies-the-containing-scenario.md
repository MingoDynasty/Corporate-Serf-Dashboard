# 2026-10-23: Run History Hover Identifies The Containing Scenario

Status: Accepted

Hovering a chart run also highlights the Scenario row containing it. This
identifies the right group when its runs are collapsed. The existing Run or
Session highlight stays in place, and the list keeps its position and expansion.

**Direction.** Ruled (user) 2026-10-23: extend chart hover to identify the
containing Scenario row under All scenarios. The Session-only fallback
could leave the player looking at another scenario without realizing where
the run belonged.

**Contract.**

- A chart run point or PB star retains its existing Run-row highlight, or
  Session-row fallback when collapsed content hides that run.
- Under All scenarios, the same hover also outlines the run's exact Scenario
  visit if that row is shown in the expanded hierarchy. With the visit open,
  the Run and Scenario rows are linked. With the visit closed, the Session
  and Scenario rows are linked. With the Session closed, only the Session
  row is linked.
- Visits use their existing IDs. Returning to a scenario creates a separate
  visit, so the outlined Scenario row is the one containing the hovered run.
- Both targets use the same temporary grape outline and clear together on
  unhover, list scroll, model or expansion changes, chart redraw, and page
  departure. A hover with no loaded matching run clears both targets too.
- The outline preserves the selected-scenario band, latest-run highlights,
  row geometry, keyboard focus, selection, scroll, expansion, and loaded
  session count. Off-screen rows stay off-screen and unloaded rows stay
  unloaded.
- The reverse interaction remains run-based: a Run row emphasizes its chart
  marker. Hovering a Scenario or Session row does not emphasize a set of
  chart points. Click actions are unchanged.

This amends only the targets of the [original linked-hover decision](2026-10-23-run-history-links-chart-and-list-runs-on-hover.md).
Current behavior is specified in [Run History](../../specs/run_history.md#linked-hover).
