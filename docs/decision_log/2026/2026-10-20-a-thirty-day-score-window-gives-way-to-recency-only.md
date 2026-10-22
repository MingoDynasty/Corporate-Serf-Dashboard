# 2026-10-20: A Thirty-Day Score Window Gives Way To Recency Only

Status: Rejected

A thirty-day cutoff in the score calculation was considered and set aside.
The score instead keeps the same last-run history through a break, while fading tells the player when its support is old.
Nothing carries an earlier value in place of a new calculation.

**Disposition.** TS2 of [proposal #382](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/382) pivoted to TS6 on the maintainer's lean on 2026-10-19; TS2 itself was never ratified. The maintainer's 2026-10-20 [TS6 ruling](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/commit/7908d00) chose the replacement. This rejected entry preserves the pivot rather than presenting TS2 as an adopted rule.

**What was set aside.** Compute from at most 20 runs inside 30 days, carrying the last qualifying value while the recent window fails its minimum. A carried stretch, even faded, can stay flat through improving runs and then step when the window qualifies again. No-limit values at full strength were the other rejected extreme: they give no shared meaning to current after a long break.

**Replacement.** [TS1's amended value](2026-10-15-typical-score-uses-the-last-twenty-runs-and-counts-every-version.md) always reads the last 20 runs at any age, and [TS6](2026-10-20-a-typical-score-is-recent-with-ten-runs-from-the-last-thirty-days.md) separately decides strength and discloses the mixture. At 49 measured returns from faded to full strength, the old window's carried value stepped by a median 5.6%, the blended alternative by 3.9%, and the chosen value moved 0.7%, an ordinary run's move. This was one player's history, not a universal prediction test. The continuous summary earned its place through steadiness and a visible spread, not by outperforming the previous session's median as a predictor.

The line and its fade shipped in #400 and #402, and the card in #401. Current behavior is in [typical_score.md](../../specs/typical_score.md) and [Run History](../../specs/run_history.md#the-chart).
