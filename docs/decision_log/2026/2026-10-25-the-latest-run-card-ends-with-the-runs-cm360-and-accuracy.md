# 2026-10-25: The Latest-Run Card Ends With The Run's cm/360 And Accuracy

Status: Accepted

The latest-run card's line under the score now holds only the comparison
with the PB, and the run's accuracy moves to a quiet last line beside its
cm/360, as the PB card ends with the PB run's. The run's number in its
session and its time on the scenario share one quiet line. Those two lines,
and the PB card's last line, take the scenario table's readable grey,
because the cards' dimmed grey is too faint for text this small.

**Ruling and delivery.** SC3 of the Run History score cards proposal,
[#430](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/430),
ratified by the maintainer on 2026-10-25 at `c77ad06`: "I ratify the proposal
on PR #430 at c77ad06.", as amended in review: the first review wave asked
that the quiet lines stay readable. Before it, the maintainer's lean of
2026-10-25: "Keep changes 2 to 5 as proposed: no scenario name, the
rebalanced lines, top-aligned cards, and readable badges." Built in
[#431](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/431),
the proposal's first delivery PR. Current behavior is in
[run_history.md](../../specs/run_history.md#the-latest-run-card).

**Why.**

- [The 2026-10-14 rule on a card's lines](2026-10-14-a-cards-lines-follow-their-role-in-the-players-next-action.md)
  puts the fact the player acts on first, at full weight, and the supporting
  facts after it, quieter. The PB card's cm/360 and accuracy are quiet
  because they support the PB, and the same holds for the run. The run's
  accuracy sat at full weight on the comparison line.
- The two cards now compare line for line: the score, its comparison, then
  cm/360 and accuracy, so a run at a new sensitivity reads against the PB's
  at a glance.
- The session details took two lines so the run's score would sit near the
  PB's in one PB card state
  ([2026-10-18](2026-10-18-the-latest-run-card-reports-the-selected-scenarios-latest-run.md)).
  [The cards now line up from the top](2026-10-25-run-historys-three-score-cards-line-up-from-the-top.md),
  so that reason goes.
- The cards' 12 px dimmed grey measures 3.32:1 light and 4.04:1 dark, under
  the 4.5:1 WCAG AA asks for text this size, and the run's accuracy would
  have moved into it from a full-strength line.

**The lines under the score.**

1. The comparison line, at the card's 13 px weight: today's PB comparison
   with nothing after it, `{pct}% of PB` or `{pct}% of PB pace`, or a new
   PB's gain, worded as before. With no comparison the line is absent: a
   scenario's first run, and a run that is not a new PB and is compared by
   score with a previous best of zero or less. Before, those read
   `Accuracy {accuracy}%` alone.
2. The session line, quiet: the run's words, ` · `, then the time words, as
   in `Run {n} this session · {duration} on this scenario`. The run's words
   are also `Run {n} last session` and `Run {n} ({session} session)`, and
   the time words `Time on this scenario unknown`.
3. The last line, quiet: `{cm/360} cm/360 · Accuracy {accuracy}%`, or
   `Accuracy {accuracy}%` where the run's cm/360 is unknown.
   `sensitivity_and_accuracy` words it for both cards; it moved from the PB
   card's `_faded_line`, and `personal_best_cm360` reads any run.

**The readable grey.** The session line, the last line, and the PB card's
last line are `#676d75` in light mode and `#a6a6a6` in dark mode, the
scenario table's old typical value
([2026-10-22](2026-10-22-an-old-typical-value-on-the-table-is-marked-with-a-clock-in-a-readable-grey.md)).
On the cards they measure 5.22:1 on white and 6.38:1 on `#242424`
(2026-10-25, headless Edge), and still read quieter than the comparison
line. The cards' first lines keep the dimmed grey. The card rules carry the
same two values as the table's rule, which is unchanged: one shared custom
property would have rewritten that rule and its test for no change on
screen.

**In the code.** `LatestRun` holds `comparison` (`None` with nothing to
compare), `session` and `sensitivity_and_accuracy`; `scenario`, `result`
and `time_on_scenario` are gone. `_session_line` returns the one joined
line. The quiet lines' class is `run-history-card-quiet`, which replaces
`run-history-card-session`.

**Left for the proposal's second delivery PR.** SC1's typical phrase goes
before the PB comparison on the comparison line, and that PR measures the
card's narrow floor again with it.

**What this changes in older entries.** Each keeps its text and gains a dated
note.

- [2026-10-12, a past run's check](2026-10-12-a-past-runs-check-is-judged-against-the-pb-it-was-chasing-under-its-own-version.md):
  the second line's accuracy after the PB comparison, and accuracy alone
  where there is no comparison.
- [2026-10-18, the card follows the selection](2026-10-18-the-latest-run-card-reports-the-selected-scenarios-latest-run.md):
  the time on the scenario on a line of its own.
