# 2026-10-20: The Typical Score And Both Bands Have Independent Switches

Status: Accepted

The typical score and each band have their own switch, all on at first.
Players can keep any combination, and the browser remembers it.
Those choices affect the chart while the card keeps its complete summary.

**Ruling.** TS7 of [proposal #382](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/382), ruled with TS8 on 2026-10-20 at [e2d36db](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/commit/e2d36db). It amends TS4. Delivered in #400 and #402.

**Contract.** Chart options' Overlays ends with Typical score, Middle 50% and Middle 80%, after PB score. Each starts on, is independently remembered, hides all of its metric's faded stretches, and participates in the chart rebuild. A band may show without the line. A band's hover line appears only while that band is on. Score vs Sensitivity draws none of these metrics. Scenario Stats follows none of the switches, and its hover always names both bands.

The ids are `run-history-typical-score-overlay-switch`, `run-history-middle-50-overlay-switch` and `run-history-middle-80-overlay-switch`. Their defaults and ids are fixed once shipped: changing a persisted default discards stored choices, as [the query-parameter and memory rule](2026-09-19-a-query-parameter-selects-a-control-it-does-not-suspend-its-memory.md) records.

**Why.** Each other score overlay has its own switch, and a legend click is forgotten at a rebuild. All on lets players meet the complete summary; the accepted cost is a busier first chart. One joint line-and-band switch and one band chooser were rejected because they remove useful combinations or differ from the panel's other controls. The [legend ruling](2026-10-18-the-typical-score-is-drawn-after-each-run.md) accepts possible wrapping on narrow charts without moving it.

Current controls and help copy are in [Run History](../../specs/run_history.md#chart-options-panel).
