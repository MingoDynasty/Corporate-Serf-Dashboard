# 2026-10-14: The PB Card Shows The Local Record And Next Rank

Status: Accepted

Run History gives the selected scenario's personal best a card beside the
latest run, making the record to beat visible without a chart overlay. The
next rank's score sits under the PB score, with the gap and amount still
needed, so the benchmark milestone is visible without arithmetic or a hover.
The leaderboard standing follows underneath. The PB run's sensitivity and
accuracy give quieter context for that record.

**Ruling and delivery.** T3 of [#379](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/379),
ratified by the maintainer on 2026-10-14 at `7329c23`, as amended after review
to show the next rank's threshold and omit the leaderboard line without a
local PB. The maintainer chose to put the two scores adjacent and deferred
a remote-only record to Remote personal best reconciliation. Built in
[#383](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/383).
Current behavior is in [run_history.md](../../specs/run_history.md#the-pb-card)
and [scenario_rank.md](../../specs/scenario_rank.md#on-run-history).

The 300px card sits at the first column's right end, beside the latest-run
card. Its lines are, in order:

1. `PB · set {age}`, reworded every 30 seconds, exact time on hover and focus.
2. The large PB score and, while the selected benchmark supplies a ladder,
   the rank reached as a badge. The score's hover repeats the latest-run
   card's new-PB comparison; a PB set by the first run has no hover.
3. The next rank, such as `3,700 Lavender · +1.3% · 47 to go`, with the
   threshold under the PB and each beside its rank. A time-scored gap says
   `+2.8% faster`; the threshold stays a score. `Top rank` stands alone at
   the top, and no benchmark, no ladder or an `N/A` table result hides it.
4. The leaderboard line, `{percentile}% percentile` to two decimals, with
   `Position {position} of {total}` over Last updated on hover and focus.
   Without a percentile it keeps the former Position field's label, values
   and hints. Refresh stays with that value and keeps its existing behavior.
5. The quieter `{cm/360} cm/360 · Accuracy {accuracy}%`, or accuracy alone
   when sensitivity is unknown. Sensitivity is the table's PB cm/360 with
   trailing zeros dropped; accuracy is hit accuracy to the whole percent,
   which can differ from the table's damage accuracy. *(Superseded
   2026-10-18: the accuracy shows two decimals. See
   [A Run's Accuracy Shows Two Decimals](2026-10-18-a-runs-accuracy-shows-two-decimals.md).)*

Use the table's own ladder computation and eligible pace constant. Its
sortable wording differs from a card's wording, but its threshold, gap and
points do not. The card chooses no training goal and does not alter the
configured Score threshold. The rank badge keeps page text on a tint with
the rank color as its border, readable in both themes.

The record is local; the leaderboard independently ranks what KovaaK's
holds, which can differ after play on another computer. With no local runs
there is **no leaderboard line, no Refresh and no lookup**, even with a
username set. The empty states lead with `PB`, then `No scenario selected`
or `No local PB yet` over `Play this scenario to record one in this app.`.
The leading `PB` was disclosed as new copy in #383.

The PB run is the one `get_personal_best_run` selects, the earliest run to
reach the high score in the store's order. When tied runs ended in one
second, that order can differ from play order. #383's disclosed mechanical
deviation takes the score's hover from the first run in play order to reach
the score, preserving the comparison shown when the score landed rather
than saying it improved by zero. The spec retains that distinction.

Every run on the selected scenario rebuilds the card: even a run that sets
no PB can change the eligible pace basis. Scenario and filter changes do
too; the existing position reads write the leaderboard line. The row keeps
one height through changes between runs. The username setup hint is
measured separately, about 164px rather than the mocked 175px. Hovers are
also keyboard focus targets; the card itself is neither a landmark nor a
button.
