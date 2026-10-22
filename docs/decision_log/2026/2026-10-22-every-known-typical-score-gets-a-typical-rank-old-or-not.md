# 2026-10-22: Every Known Typical Score Gets A Typical Rank, Old Or Not

Status: Accepted

A typical score with few recent runs behind it still gets its Typical Rank
and sorts among the other known values, marked as not recent. A scenario
with too few runs for a typical score reads Too few runs, is never marked,
and sorts last whichever way the column sorts. Unknown is never read as weak,
and old is not the same as unknown.

**Ruling.** TB3 of
[proposal #408](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/408),
ratified by the maintainer on 2026-10-22. Their lean before that, on
2026-10-21: "2: I agree." Shipped in
[#414](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/414).

**The evidence bar.** The
[2026-10-04 principles](2026-10-04-skill-is-judged-by-the-typical-run-with-honest-uncertainty-in-verdicts-not-advice.md)
say defining the typical score "does not authorize a later judgment to use a
dimmed value without choosing its evidence bar". This is that choice for the
scenario table's weakness order:

- **A known value counts, at any age.** Scenario Stats already shows an old
  value dimmed rather than hiding it, because hiding one "would discard
  useful information about past play"
  ([2026-10-18](2026-10-18-scenario-stats-shows-the-newest-typical-score-at-any-age.md)).
  A rank read from one is the same figure placed on the ladder.
- **Setting old values aside would empty the column on most benchmarks.** On
  IRON PIPE AIM PLAYLIST #2, 6 of the 9 scenarios with a typical score are
  not recent; treated as unknown, they would join the 25 played scenarios that
  already read Too few runs.
- **Unknown sorts last in both directions,** as `N/A` already does, through
  the table's nulls-last comparator, so an unknown value is never placed
  among the weak ones.
- **Admitting an old value rests on its qualification reaching every
  reader.** The mark, its hover and its screen-reader words are in the
  [Not recent entry](2026-10-22-an-old-typical-value-on-the-table-is-marked-with-a-clock-in-a-readable-grey.md).

Recency is the [2026-10-20 rule](2026-10-20-a-typical-score-is-recent-with-ten-runs-from-the-last-thirty-days.md),
judged once, when the table is built.
