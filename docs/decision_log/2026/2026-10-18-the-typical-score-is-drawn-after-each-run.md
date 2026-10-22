# 2026-10-18: The Typical Score Is Drawn After Each Run

Status: Accepted

The chart shows how each run moves the typical score.
A time axis holds each value flat until the next run, so days off do not look like gradual improvement.
The line ends at the newest plotted run and leaves current recency to the card.

**Ruling.** TS3 of [proposal #382](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/382), ratified by the maintainer on 2026-10-18 at [951d1c2](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/commit/951d1c2). Delivered in #400 and #402. The per-session freeze is for later comparisons, not a display that compares nothing.

**Contract.** Score vs Run has a value at every plotted run where one is known, spaced in play order and joined by straight lines. The values are computed over the whole history before the range is applied. A faded stretch joins the full-strength points at both ends without a step in the value. A lone known value spans half a run on either side so it remains visible.

Score vs Time holds a value flat to the next run, with a step at each run and a fade at [TS6's exact boundary](2026-10-20-a-typical-score-is-recent-with-ten-runs-from-the-last-thirty-days.md). The line ends at the newest plotted run, on that run's value; holding it to now would compress a scenario last played years ago against empty years and make a clockless chart change with time. For same-second runs, the later-played value holds from that second onward; a value held for no time has no point. A lone value has a level stroke, and each band a vertical bar, 14px wide.

Score vs Sensitivity draws neither summary nor bands until that mode is redesigned: a rolling value has no order along a sensitivity axis. Every run remains plotted in every mode. Steps once per session and joining session-frozen values were rejected because they hide the changes within a sitting.

**Presentation and fit.** Summary traces are appended after the run, star and ring traces and draw under them at `zorder=-1`, keeping the run trace first and its generated color unchanged. The line is 2.5px wide, gray `#343a40` in light and `#dee2e6` in dark. Full-strength traces draw above faded ones. The legend orders the line and both bands after New PB, one group per metric, so a click hides all of that metric's stretches. The line has its own hover; bands have none, and the run points' hover stays unchanged. Visible summary points and segment portions inside a zoomed window take part in score-axis fitting, including a time hold spanning that whole window. Share chart includes the summary and its hover as part of the figure.

**Legend ruling.** On 2026-10-21 the maintainer [ruled that the existing legend stays above the plot](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/399#issuecomment-6312838006), closing #399 unmerged. Narrow charts may wrap it over the title; that Backlog item stays open. No label shortening or layout change ships here.

Current rendering and hover details are in [Run History](../../specs/run_history.md#the-chart).
