# 2026-10-24: Chart Point Tooltips Show Score, Time And Run Numbers

Status: Accepted

Run-point tooltips identify a run and name the session where it can be found.
Score vs Run also describes how much practice followed that run.
Scores and session labels match the run list, and sensitivity keeps its
recorded game setting. Accuracy is available in the list and can require
more navigation for older runs.

**Direction.** The maintainer approved this contract on 2026-10-24 following
the Fable consult and Opus's requirements handoff. Full run detail belongs
in the list; click-to-jump or a Run Viewer is planned separately.

**Contract and copy.**

Score vs Run:

```text
Oct 12, 2026, 7:04:22 PM · 57 runs ago
Score: 3,324
Session: Oct 12, 6:40 PM · run 7 of 12
Sensitivity: 40.8 cm/360 (0.2 Valorant at 1600 DPI)
```

- Score vs Time and Score vs Sensitivity use the same four lines without
  the ` · 57 runs ago` suffix. No mode has a blank line after the timestamp.
  Labels are bold. Each tooltip states the point's position on both axes:
  Score vs Run alone needs a distance in runs because its Run-axis labels
  show only dates.
- The run's timestamp keeps seconds and the full year under the
  [2026-07-11 rule](2026-07-11-humanize-the-absolute-timestamp-format.md).
- Runs ago counts every newer imported run of this scenario in play order,
  at every sensitivity and version, independently of chart range and zoom.
  The newest reads `Latest run`, one reads `1 run ago`, and larger counts
  read `{n} runs ago` with thousands separators. Older points' ages increase
  as runs of the scenario are imported.
- Score uses the list's `format_score` output, including thousands separators,
  up to two decimals and no trailing zeroes.
- The session name is exactly the list's Session-row name, including its
  conditional year. It names the whole play session, even when other
  scenarios were played before the selected one. The numerator equals the
  run's `#`; the denominator equals the first number in the session row's
  `12 of 47 runs`. Both count only this scenario, across returning visits,
  sensitivities and versions. Counts cover the whole session, including
  later runs and runs outside the chart range; an ongoing session's total
  grows as more runs of that scenario are imported.
- Sensitivity stays in every mode, including the unrounded original setting
  and DPI for converted runs. Native and unconverted runs have no suffix.
  The [2026-09-26 decision](2026-09-26-a-converted-run-keeps-the-setting-it-was-recorded-at-for-display-only.md)
  remains in force. The PR also exposes the same recorded details on the
  run list's Sensitivity-cell tooltip, without changing its displayed value
  or width.
- PB stars reuse their run's tooltip, including with ordinary dots hidden.
  Coincident points retain the PB tie-order and filename-identity contracts.
  Hover does not scroll, expand or load the list, and adds no click action.
  Typical Score's tooltips are unchanged.

**Accepted gap.** Accuracy is absent from the chart tooltip. Until a click
feature exists, inspecting an old run's accuracy may require scrolling,
expanding groups or loading older sessions in the list. This is an accepted
navigation cost, not an assumption that hover always exposes the run row.

**Considered and rejected.**

- An all-time run ordinal such as `run 1,237 of 1,294`: the timestamp already
  identifies the run, and run age answers the practice-distance question.
- Following the list's column choices: those choices partly manage width,
  the dependency would be hidden, and the tooltip could grow to nine lines.
- Keeping accuracy: Fable recommended it as useful outlier context; the
  maintainer accepts the navigation cost above to keep the tooltip focused.

**Supersedes in part.** Only the identical-content, accuracy and
"Nothing new went into the hover" clauses in the
[2026-10-12 chart decision](2026-10-12-the-run-history-chart-plots-every-run-and-draws-no-summary-line.md)
change. Timestamp seconds, recorded sensitivity, plotting, grouping and
identity contracts stand.
