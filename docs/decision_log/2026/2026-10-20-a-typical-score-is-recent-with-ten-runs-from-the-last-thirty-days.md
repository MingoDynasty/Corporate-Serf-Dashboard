# 2026-10-20: A Typical Score Is Recent With Ten Runs From The Last Thirty Days

Status: Accepted

A typical score is drawn at full strength when at least ten supporting runs are from the last thirty days.
Otherwise the same value is faded on the chart and dimmed on the card.
The card discloses older support even when the number is at full strength.

**Ruling.** TS6 of [proposal #382](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/382), ruled by the maintainer on 2026-10-20 at [7908d00](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/commit/7908d00): D as amended. This replaces [TS2's window and carry](2026-10-20-a-thirty-day-score-window-gives-way-to-recency-only.md) and amends TS1. Sol's stricter all-recent preference remained recorded; accepting the ruling did not turn it into endorsement. Astra withdrew its blocking counter in [the bounded consult](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/382#issuecomment-6280128278); that counter was not adopted. Delivered in #398, #400, #402 and #401.

**Contract.** A known value is recent at a moment when at least 10 supporting runs ended within the preceding 30 days, including the moment itself and the exact 30-day boundary. Runs after the moment do not count. Sessions guard existence only, not strength. The score is always the last-20 value at any age, never a recent-only replacement or a carried earlier value. A scenario that has never had 10 recent runs still shows its known value faded.

Scenario Stats judges as of now. Score vs Run judges at each run, so a plotted point never ages later. Score vs Time judges along a hold: it is recent through the end of the tenth-newest supporting run plus 30 days and faded strictly after it. The line ends at the newest run, so the card can be dimmed while the chart's last point remains full strength. A held faded hover says `Recent: too few · last run {date}` because its count changes along the hold.

Whenever any supporting runs are older than 30 days, the card adds `{k} of {n} recent runs`, zero included, over both full-strength and dimmed values. A full-strength value can still contain 10 old runs. The help explains that fewer than 10 recent supporting runs means the figure may be out of date; it does not certify an undimmed figure's accuracy.

**Accepted cost and evidence.** The value can lag after a return, low after improvement or high after decline. Ten old scores of 200 and ten new scores of 100 give a full-strength 150. On the maintainer's 9,212-run history through 2026-10-16, judged at 322 paired session starts against the next session's median, D's median error was 3.84% versus 3.56% for the 30-day-window alternative. The 95 mixed-age starts carried the gap: 4.59% versus 3.61%. These were one player's measurements, not a guarantee for others. Requiring every supporting run to be recent would reduce 2026's full-strength coverage from 46.0% to 30.9%, fading lightly played scenarios and returns longer. A 90-day ceiling added another threshold with a similar fading cost. Both were rejected. The ruling chose a shared, checkable drawing rule and a visible mixture; later judgment features may require more evidence.

Current rules are in [typical_score.md](../../specs/typical_score.md#recency-and-holds) and [Run History](../../specs/run_history.md#scenario-stats).
