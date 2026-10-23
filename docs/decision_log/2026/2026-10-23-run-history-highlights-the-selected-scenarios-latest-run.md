# 2026-10-23: Run History Highlights The Selected Scenario's Latest Run

Status: Accepted

The Latest Run card, chart ring and run-list highlight now identify the
selected scenario's latest run. This makes manual browsing show the same
result consistently across the page. Chart ranges and the list's open rows
and scroll position stay as chosen.

**Direction.** The maintainer accepted this behavior on 2026-10-23:
"Let's go with your recommendations." It replaces the global last-played
scope retained when the [card became selection-scoped](2026-10-18-the-latest-run-card-reports-the-selected-scenarios-latest-run.md).
The card's run, the row and the point answer one question during both play
and lookup: what was the selected scenario's latest result? Follow and run
toasts still provide the path to a newly played scenario.

**One highlighted run.** The selected scenario's last run in play order is
the target, with the same whole-store session ordering and same-second tie
breaks the card already uses. Both run-list views highlight that run alone.
The chart rings it in all three modes when it is plotted. Nothing is marked
with no selection or no runs for it. A dropdown choice, a scenario name
pressed in the list, a link and Follow all use this rule. A name pressed in
an older visit selects the scenario, not that historical visit's run.

**New runs.** A newer run on the selected scenario moves all three to that
run, including a late-arriving run older than the newest run overall. An
older run leaves the target alone. With Follow off a run on another scenario
leaves the selected run and its highlights alone, preserving the chart's
zoom. With Follow on the selection and all three move to the new scenario.

**Visibility.** A ring appears only when the existing chart range includes
its run. The list highlights the run when its row is visible, without
expanding, scrolling or loading older sessions to reach it. Changing the
highlight does not change a range or the list's open rows. The global newest
run remains the list's expansion token for new-run delivery; changing the
selection cannot masquerade as another run landing.

**Scope of the amendment.** This supersedes the global last-played ring and
row-highlight rules in the [chart decision](2026-10-12-the-run-history-chart-plots-every-run-and-draws-no-summary-line.md),
the [All scenarios decision](2026-10-14-the-run-list-has-a-second-view-all-scenarios-that-shows-each-session-whole.md)
and the card decision above. Their other rules stand. The highlights retain
their appearance and add no copy, keyboard behavior or accessible names.
The current contract is in [Run History](../../specs/run_history.md).
