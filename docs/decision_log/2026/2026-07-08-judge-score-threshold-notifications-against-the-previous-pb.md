# 2026-07-08: Judge Score-Threshold Notifications Against The Previous PB

Status: Accepted

Decision: Score-threshold notification verdicts compare in score space against
the personal best the run was chasing:
`score >= previous_high_score * score_threshold_percentage / 100`. The overlay
line still uses the current post-run personal best for the same percentage
setting.

Why: The toast already displays the run's percentage against the previous PB.
Using the post-run PB for the verdict made goals above 100% unreachable,
because a new PB moved the target upward before the run was judged. Keeping the
comparison in score space preserves the exact-threshold `>=` boundary; the
displayed-ratio form can round `820 / 800 * 100` below `102.5` and turn an
exact hit into a failure.

Consequences: Goals above 100% now pass when a run beats the previous PB by
the configured margin. New-scenario and new-sensitivity events still carry
`previous_high_score=None`, so they remain verdict-less. Backlog summaries keep
judging only the batch's latest run; fuller historical pass/fail review belongs
to run history.

**Superseded in part (2026-10-05).** On a time-scored scenario, wherever the
app can measure pace, the verdict compares pace instead of score: a run
passes when it is at least the goal percentage as fast as the previous PB.
The reasons above stand there too: the verdict still judges against the
previous PB, and still compares exactly rather than through the ratio it
displays. Every other scenario keeps the formula as written. The
[2026-10-05 entry](2026-10-05-time-scored-scenarios-are-measured-by-pace.md)
holds the pace formula.

**Superseded in part (2026-10-13).** No notification judges a run: the run
toast is plain. The rule and its exact comparison stand, as the rule for the
check beside a run's score and for the latest-run card. See
[A Run Toast Is Plain And Shows On Every Page](2026-10-13-a-run-toast-is-plain-and-shows-on-every-page.md)
and
[A Past Run's Check Is Judged Against The PB It Was Chasing, Under Its Own Version](2026-10-12-a-past-runs-check-is-judged-against-the-pb-it-was-chasing-under-its-own-version.md).
