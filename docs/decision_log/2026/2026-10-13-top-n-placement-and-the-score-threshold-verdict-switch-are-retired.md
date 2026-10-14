# 2026-10-13: Top N Placement And The Score Threshold Verdict Switch Are Retired

Status: Accepted

Nothing in the app says where a run placed among the runs at its
sensitivity any more, and the switch that decided whether a run's toast
carried a pass or a miss is gone. Both existed only for the toast that
judged a run, which is now plain. Clearing the Score threshold percentage is
the one way left to stop runs being judged.

**The rulings.** Rows T2 and T3 of the Run toasts proposal, ratified by the
maintainer on 2026-10-11. Their words on 2026-10-10: "Lean toward your
recommendation of retiring Top N." And: "Yes, drop the Score Threshold
verdict switch. It can be entirely replaced with the 'green checkmark' idea
in the mockups to the right of the score. Essentially that green checkmark
and/or star IS the verdict, which tells the user whether this run passed
the Score Threshold or not, and if this was a PB or not."

**Top N placement.** It was where a new run's score placed among the
scenario's runs at the same sensitivity, and it existed only as toast copy:
the sentence "Also your 2nd-best at 34.6 cm/360.", and the title "New
2nd-best score" on a run that was not judged.

- **Its N had gone.** The chart plots every run and has no Top N scores
  control
  ([2026-10-12](2026-10-12-the-run-history-chart-plots-every-run-and-draws-no-summary-line.md)),
  so the toast had been placing a run against a fixed 5 that nothing on
  screen explained.
- **A plain toast has no room for it.** The toast carries no judgment of
  the run, and a placement is one
  ([the toast's entry](2026-10-13-a-run-toast-is-plain-and-shows-on-every-page.md)).
- **It was almost never the headline.** A run that could be judged led with
  the threshold verdict, and a run that could not was nearly always the
  first at its sensitivity, where the title was always "New best score".

What it costs: "your 2nd-best at this sensitivity" is a real fact, and
nothing states it now. The run list shows every score in time order, not
grouped by sensitivity, and Score vs Sensitivity still plots every run at
each sensitivity. Moving placement to the latest-run card was considered
and not taken.

**What left with it.** `nth_score` left the run message and the shell's
batch record. The watchdog no longer counts the runs that scored higher,
and no longer logs its "place score" debug line. The glossary lost the
term.

**What stays in the run message.**

- `score`, `scenario_previous_best`, `pace_constant`, and `run_id`: the
  celebration reads them.
- `is_new_sensitivity` and `sensitivity`: the proposal kept both, in case
  the page's card and check read them from the message. They read the run
  store instead, so nothing under `source/` reads either from the message
  now. They stay as the watchdog's facts about the run. Taking
  `is_new_sensitivity` out would reshape the watchdog's three import cases,
  which this decision did not ask for.

**The verdict switch.** It decided whether a run's toast carried a pass or
a miss. No toast carries a verdict, so it gated nothing. It could have been
kept to turn the checks off instead, but an empty Score threshold
percentage already means no run is judged, so the switch would have been a
second control for one job
([the check's entry](2026-10-12-a-past-runs-check-is-judged-against-the-pb-it-was-chasing-under-its-own-version.md)).

What it costs: one combination is gone, the threshold line on the chart
with no pass or miss shown anywhere. The line needs a percentage, and a
percentage means checks. The reverse still works: checks without the line,
by turning the overlay off.

This rests on a toast with no verdict. If the toast ever keeps a verdict
again, the switch needs another look, though its retirement could still
stand.

**The functions that judge a run stay.** `judge_run` and
`shown_percentage` are the check's and the card's. Only the toast's
builders were deleted, with the wrapper that applied the switch.

**Chart options holds three groups and seven controls,** and no
notification control: Overlays, Run Data Points, and Score Threshold. The
value a browser stored for the verdict switch is left behind, unused.
Nothing clears it.

Shipped in PR #376; proposal and rulings in #354. Distilled from
`docs/proposals/run_toasts_proposal.md`, deleted in the shipping PR.
