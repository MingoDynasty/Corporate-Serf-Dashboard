# 2026-10-15: Typical Score Uses The Last Twenty Runs And Counts Every Version

Status: Accepted

The typical score is the median of a scenario's last twenty runs, whatever their age.
A minimum keeps a first short sitting from being mistaken for an established level.
Every version and sensitivity counts, so a scenario change can temporarily mix scores that are no longer comparable.

**Ruling and amendments.** TS1 of [proposal #382](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/382), ruled by the maintainer on 2026-10-15: pool every version with the assumption stated, recorded at [47acc33](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/commit/47acc33). TS6, ruled 2026-10-20 at [7908d00](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/commit/7908d00), removes the age window and carry-forward from the value. This entry records TS1 as amended. Delivered by #398, #400, #402 and #401.

**Contract.** After each run, take the scenario's last 20 runs in play order, or all of them below 20. A value exists at 10 runs from at least 2 play sessions, or 20 runs from any number of sessions. Sessions are split over every scenario's runs, so another scenario can join two visits into one session. Below the minimum, unknown never means weak. Once known, a value remains known without a stored flag: below 20 its whole history stays in the window, and a full window always qualifies.

Every sensitivity, warm-up run and version counts, including a missing version hash. A scenario is its name. Versions are assumed comparable, as for the PB line and stars; this does not prove their score scales equal. After a rework, up to 19 supporting runs can be from the old version, however long the break. On the maintainer's history through 2026-10-16, 59 values mixed versions and 25 were drawn at full strength. A hash changes for edits that need not change scoring, so resetting on every hash was rejected. A later warm-up rule can change the value and needs its own decision.

**Why these numbers.** The median resists one unusually good or bad run. Twenty runs was the maintainer's hand method and sat inside the 10-to-30 range with similar next-session accuracy on this one player's history; 40 and 50 lagged. The two-session minimum guards the first sitting's form. The full-20 exception prevents a long grind from unmaking an established value: removing it erased values on 547 runs over 26 scenarios in the measured history. Fixed constants keep one definition across installs; no window or minimum setting is added.

**Rounding.** Keep unrounded statistics for calculation. Display the most decimal places of any supporting score, capped at two, with a half rounded up, thousands separators and trailing zero removal. Whole-score 2140.5 reads `2,141`; one-decimal 1.25 reads `1.3`; six-decimal 2.145 reads `2.15`. Decimal arithmetic preserves a decimal half before this display step.

Current rules and APIs are in [typical_score.md](../../specs/typical_score.md). [Recency](2026-10-20-a-typical-score-is-recent-with-ten-runs-from-the-last-thirty-days.md) is separate from the value. This names the typical run of [the skill principles](2026-10-04-skill-is-judged-by-the-typical-run-with-honest-uncertainty-in-verdicts-not-advice.md) as Typical score on screen and `typical_score` in code.
