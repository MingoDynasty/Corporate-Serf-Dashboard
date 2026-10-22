# 2026-10-18: Two Percentile Bands Show The Typical Score's Spread

Status: Accepted

Two bands show how widely the runs behind a typical score vary.
The darker band holds the middle half and the lighter band the middle eighty percent.
Their widths show consistency without letting one best or worst run set the bounds.

**Ruling and amendment.** TS4 of [proposal #382](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/382), ratified on 2026-10-18 at [951d1c2](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/commit/951d1c2). [TS7](2026-10-20-the-typical-score-and-both-bands-have-independent-switches.md), ruled 2026-10-20 at [e2d36db](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/commit/e2d36db), replaces its original always-on middle half and initially-off middle eighty percent with independent switches, all on. Delivered in #400 and #402.

**Contract.** Both bands use the same supporting runs as [the value](2026-10-15-typical-score-uses-the-last-twenty-runs-and-counts-every-version.md). Middle 50% is P25 to P75; Middle 80% is P10 to P90. Percentiles interpolate inclusively between scores, as `statistics.quantiles` with `method="inclusive"` does. The middle half uses the line's gray at 14% opacity, the middle eighty at 7%, with faded stretches at 35% of their normal strength. The line draws above the bands, and the narrower band above the wider.

**Why percentiles.** The maximum grows with the sample count and a lucky run can set it for the whole window; the minimum records the worst accident. P10 and P90 need several runs to move. A narrower band means more consistent scores. A single consistency number remains separate future work.

Current drawing and on-screen terms are in [Run History](../../specs/run_history.md#the-chart) and [the glossary](../../glossary.md#middle-50).
