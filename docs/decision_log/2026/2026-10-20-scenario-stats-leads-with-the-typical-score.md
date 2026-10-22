# 2026-10-20: Scenario Stats Leads With The Typical Score

Status: Accepted

Scenario Stats leads with the typical score in the same large-number style as the neighboring cards.
Its first line names that figure and explains older support, while Category and Total runs follow.
The total count has a distinct name so it is not mistaken for the runs used to calculate the score.

**Ruling.** TS8 of [proposal #382](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/382), ruled with TS7 on 2026-10-20 at [e2d36db](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/commit/e2d36db). It amends TS5's ordinary line and the older card's absence of a lead fact. Delivered in #401 after #398 and #400, alongside #402.

**Contract.** The first line is plain text, not a heading, and reads `Typical score`, then a help icon named `About the typical score`, then [TS6's partial-recent readout](2026-10-20-a-typical-score-is-recent-with-ten-runs-from-the-last-thirty-days.md) whenever any supporting runs are old. The value is a 30px weight-600 lead with a dotted underline for its hover, dimmed in the theme's dimmed color when not recent. Dimmed large text must clear 3:1 against the card background in each theme. Category follows while the Playlist filter holds a grouped benchmark, then `Total runs: {n}`, replacing Number of runs.

With no scenario selected, `No scenario selected` replaces the lead and lines. With no local runs, the lead reads `No runs yet` over `Total runs: 0`; below the existence minimum it reads `Too few runs`. The card remains 270px wide and does not increase the top row's height. The longest first line is `Typical score ⓘ · 19 of 20 recent runs`. Browser verification in both themes and at 2560 and 1920px kept it on one 18px line, with row heights about 143px without a benchmark and 164px with one.

**Why.** The typical score is this card's defining figure, as the PB and latest-run score define theirs. A smaller ordinary line after Category would give the skill summary less emphasis than lookup context. Keeping a separate Scenario stats label over Typical score would cost another line and break the neighboring cards' pattern. Total runs separates the all-history count from the at-most-20 supporting runs.

**Help and terms.** The help explains the last-20 median, the darker middle-half and lighter middle-eighty bands, their switches, why the value dims, and why the card and chart can disagree about recency. Both targets accept keyboard focus and preserve word separation in the accessibility tree. The card keeps the Scenario Stats name in code and documentation. Typical score, Recent, Middle 50% and Middle 80% are defined in [the glossary](../../glossary.md#typical-score).

This decision adds no comparison to the PB card. Current behavior is in [Run History](../../specs/run_history.md#scenario-stats).
