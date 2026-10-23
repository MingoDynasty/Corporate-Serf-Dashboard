# 2026-10-23: This Scenario Session Rows Keep Their Score Summaries Inline

Status: Accepted

Under This scenario, every session row can show Median and best beside
its run count. Session duration appears in All scenarios, where the
whole session is the subject. The newest row keeps its In progress badge
and the same height as older rows.

**Direction.** Approved by the maintainer on 2026-10-23 in the design chat
about RawControlSphere's newest session: remove its duration from This
scenario and move Median and Best onto the run count's line, matching older
sessions. The maintainer approved the before-and-after mockup and directed
implementation. This replaces the newest-row duration rule in
[the original run-list entry](2026-10-12-the-run-list-is-a-second-column-beside-the-chart.md),
the second-line exception in
[the figures placement entry](2026-10-18-median-and-best-sit-in-the-rows-own-line-ahead-of-its-count.md),
and the first-row count exclusion in
[the columns entry](2026-10-18-the-run-list-draws-a-chevron-and-this-scenario-lines-its-figures-up-in-columns.md).

**Why.** This scenario supports comparing the same scenario across sessions.
The newest row's second line interrupts that comparison, while its duration
describes the whole session, including other scenarios and breaks. All
scenarios already gives every session's duration, and the count link leads
there.

**Contract.**

- This scenario shows no session duration or duration hover on any session
  row, whether the newest session is in progress or has ended.
- With Median and best on, every session row's figures sit before its count
  on the same line. Turning the checkbox on or off changes no row's height
  and makes no request.
- Count-column sizing includes the newest row, so a wider newest count
  keeps its Median and Best aligned with the older rows. Widths still come
  from every session of the scenario, loaded or not.
- A one-run session still shows Score under Best, and a session with none
  of the selected scenario's runs has no figures. The newest session is
  still listed in that case, with its count link and empty-state text.
- All scenarios keeps every session's duration and the newest session's
  duration hover. Session boundaries, score calculations, count links,
  keyboard controls, checkbox default and persistence are unchanged.

The current behavior is specified in
[Run History](../../specs/run_history.md#the-run-list) and
[Sessions](../../specs/sessions.md#where-sessions-show).
