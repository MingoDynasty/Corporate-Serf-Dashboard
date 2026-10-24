# 2026-10-24: Chart Point Tooltips Show Score, Time And Run Numbers

Status: Accepted

Chart point tooltips put each value on its own labeled line beneath the
exact timestamp. Both run numbers count only the selected scenario, so
the session number matches the run list and the overall number describes
its whole imported history. Detailed accuracy and recorded sensitivity
settings are available in the run list.

**Direction.** The maintainer approved this scope in the 2026-10-24
implementation kickoff after the tooltip direction discussion.

**Contract.**

- Run dots and PB stars start with the existing absolute timestamp with
  seconds, then a blank line. Three labeled lines follow:
  `Score: {score}`, `Run: {overall_number} (overall)` and
  `Run: {session_number} (this session)`. The labels are bold.
  Counts use thousands separators. The timestamp retains the
  [absolute-format contract](2026-07-11-humanize-the-absolute-timestamp-format.md).
- Both ordinals count the scenario's runs in play order at every sensitivity
  and version. The session ordinal continues across visits to that scenario
  and resets at a new play session, matching the list's `#` column in both
  views. The overall ordinal counts the scenario's whole imported history.
  Counts are computed before range filtering or drawing coincident PBs last.
  Other scenarios still contribute to session boundaries, as the
  [session rules](../../specs/sessions.md#sessions) specify.
- Score vs Sensitivity adds `Sensitivity: {sensitivity}` as a final line,
  using the exact axis category. Other modes omit it. Accuracy remains in
  the list. Typical Score's tooltips are unchanged.
- A converted run's Sensitivity cell has a native tooltip containing
  `{normalized_value} {scale} ({recorded_value} {recorded_scale} at {DPI} DPI)`
  in both list views. Original values are not rounded; whole values drop
  trailing zeroes. Native and unconverted runs have no extra tooltip.
  The column's displayed value and width stay the same.
- Tooltip content identifies the same run as its point, star and linked row,
  including coincident points. Hover does not expand, scroll or load the list.
  The compact readout remains useful when its list counterpart is hidden.

**Supersedes in part.** The display location and point-tooltip contents in
the [recorded-sensitivity decision](2026-09-26-a-converted-run-keeps-the-setting-it-was-recorded-at-for-display-only.md)
change. Retention, conversion, grouping, DPI trust and persistence rules stand.
