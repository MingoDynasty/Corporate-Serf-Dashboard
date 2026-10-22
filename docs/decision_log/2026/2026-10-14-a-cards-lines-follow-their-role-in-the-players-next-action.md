# 2026-10-14: A Card's Lines Follow Their Role In The Player's Next Action

Status: Accepted

The top row's cards emphasize facts by their role in the player's next action.
A card's defining figure leads, with supporting context in a quieter style.
How often a fact changes decides neither its order nor its weight.

**Superseded in part (2026-10-21).** [TS8 gives Scenario Stats a lead fact](2026-10-20-scenario-stats-leads-with-the-typical-score.md): its typical score, followed by Category and Total runs. The payload's importance order for a card with no lead still governs cards with no lead; its earlier application to Scenario Stats is historical. The other cards' order and relative-age rules stand.

**Superseded in part (2026-10-18).** [Last played leaves Scenario Stats](2026-10-18-last-played-leaves-scenario-stats-and-its-first-line-is-plain-text.md):
Scenario Stats lists Category and Number of runs, and Last played leaves the
ages this rule names on Run History. The closing paragraph's scope is
superseded too: by
[the latest-run card's rule](2026-10-18-the-latest-run-card-reports-the-selected-scenarios-latest-run.md),
the card reports the selected scenario during a lookup as well, so the two
large scores always concern the same scenario. The rule, and every other
application of it, stands.

**Ruling.** T4 of [#379](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/379),
ratified by the maintainer on 2026-10-14 at `7329c23`, as amended after the
first review wave. This rule also binds later cards in this row, including
the proposed notes card. Current applications are in
[run_history.md](../../specs/run_history.md).

Put the most useful fact first. Keep what the player needs without a hand
on the mouse visible; optional explanation and history belong on hover and
focus. Supporting facts follow the fact they support, quieter but readable.
A card with no lead fact lists its facts at one weight in importance order:
Category, Last played, Number of runs in Scenario Stats. In this layout
only the PB and latest-run scores are large; that is a layout choice, not
a restriction on later cards.

Frequency is not importance. A training note can stay unchanged for weeks
yet be the reason to look at the page, and a next-rank threshold can remain
the goal just as long. Both belong on screen at full weight. The latest
run's time changes every run yet provides context in the quiet first line.
cm/360 and accuracy are quiet because they support the PB.

An age answers how long ago: Last played, `PB · set {age}` and
`Latest run · {age} · {scenario}` read relative, reworded every 30 seconds.
The latter also shows how long a break since the last run has lasted. Exact
times remain on hover and focus in the shared absolute format without
seconds. A time that names or orders something reads absolute: session
names, run rows and the chart. This extends
[Last played's age rule](2026-06-21-relative-humanized-last-played-timestamps.md)
and replaces the latest-run card's absolute display in
[the past-run decision](2026-10-12-a-past-runs-check-is-judged-against-the-pb-it-was-chasing-under-its-own-version.md)
and [the absolute-format entry's 2026-10-12 note](2026-07-11-humanize-the-absolute-timestamp-format.md).

Both large scores compare directly while their cards concern the same
scenario, as during play with Follow on. During a lookup the latest-run
card still reports the last run played on whatever scenario. Changing that
scope is a separate proposal, not an implication of this rule.
