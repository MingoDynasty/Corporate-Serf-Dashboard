# 2026-10-14: The Run List's Columns Menu Offers Median And Best, Off To Start

Status: Superseded in part by the
[2026-10-18 entry](2026-10-18-median-and-best-sit-in-the-rows-own-line-ahead-of-its-count.md):
the figures sit in the row's own line, ahead of its count, and only the first
row under This scenario keeps a second line. The checkbox, its default, and
which rows carry figures stand.
Superseded in part again, 2026-10-23, by
[the inline session summaries entry](2026-10-23-this-scenario-session-rows-keep-their-score-summaries-inline.md):
the first row under This scenario also keeps its figures in the count's line.

**Superseded in part (2026-10-22).** [Three new column entries](2026-10-22-the-run-lists-columns-menu-offers-reloads-fov-and-avg-fps-off-to-start.md)
come before it, so "a third checkbox" is now the sixth, still after the
columns. Its default, its rows and its figures stand.

The Columns menu on Run History has a third checkbox, Median and best, which
is off until a player turns it on. With it on, a row that stands for one
scenario's runs gains a second line with the median score and the best score
of the runs under it. The figure describes those runs and judges nothing, so
it is never worded as the typical run. It is the first choice in a
Columns menu that is not a column, and the playlist tables' menus are
unchanged.

**Rulings.** By the maintainer, 2026-10-14, on
[PR #375](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/375):
"I ratify the proposal." This entry is row A3, ratified as recommended.
Before it, the design note of 2026-10-07 recorded the lean, "Median and best
are off to start, to avoid overload", and on 2026-10-13 the maintainer kept
the row in this proposal rather than the typical score's: "okay let's keep it
in." Built in
[#378](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/378).
What the list does today is in
[run_history.md](../../specs/run_history.md#the-run-list).

**Which rows.** A scenario row under All scenarios covers that visit's runs.
A session row under This scenario covers the selected scenario's runs in that
session. A session row under All scenarios shows neither: it mixes
scenarios, whose scores don't share a scale.

**What the line says.**

- `Median {median} · Best {best}`, two readout fragments each led by its
  label. A row that holds one run reads `Score {score}`: a median of one run
  is the run. A row with no run, such as `0 of 47 runs`, has no second line.
- The median is the middle score of the runs under the row, or the mean of
  the two middle scores when their number is even. The best is the highest.
  Both count every run under the row, at any sensitivity, and are formatted
  as a score is. A time-scored scenario needs no special case, because a
  higher score is always a faster finish.
- The figures show whether the row is open or closed, so a row's height
  depends on the checkbox and never on a click. The server always sends them,
  and the checkbox is the browser's alone, so turning it on makes no request.
- **A second line, not the row's own.** The mockup and the trial drew the
  figures inline. In a 500 px column that left a scenario's name about 27
  characters, and 9 of the 36 names in the maintainer's newest 30 sessions
  are longer; under This scenario the first row would run past 500 px.

**Why this isn't the mistake R5 avoided.**
[The chart's entry](2026-10-12-the-run-history-chart-plots-every-run-and-draws-no-summary-line.md)
draws no summary line because "A new summary line would be a second
definition of the typical run." This figure covers exactly the runs listed
under the row it sits on, with no window in time, no minimum, and no run left
out; opening the row shows every score that went into it. It compares
nothing: no run is judged against it, no mark depends on it, and it colors
nothing. Its label says `Median` and `Best` and never typical, usual,
average, or normal, on screen, in the glossary, or in the user guide.

**Where the evidence is against it.** The roadmap's trend verdict is planned
on session medians. Under This scenario this figure on a session row is that
quantity with no rule added; if the later proposal gives its session median
a rule this one lacks, such as leaving warm-up runs out, the list's figure
follows that rule, is relabelled, or goes. That is R5's risk in a smaller
form, accepted here. Many rows hold too few runs for a median to mean much:
of the 159 scenario rows in the maintainer's newest 30 sessions, 15 hold one
run and 17 hold two. The run count always sits beside the figures.

**The menu.**

- The shared Columns menu takes an optional list of choices that are not
  columns, drawn after the columns' checkboxes, each one remembered checkbox
  as the 2026-10-05 rulings require. The menu is named for columns, so the
  columns come first.
- A choice's checkbox id has a `type` of its own, the menu's id and
  `-choice`. The callback that shows and hides columns matches every
  checkbox of the menu's `type`, and would ask the grid to show a column
  that does not exist. Run History's is
  `{"type": "run-history-list-columns-choice", "choice": "median_best"}`,
  chosen once, unchecked by default; renaming it resets the stored choice
  in every browser.
- The list reads it with a small clientside callback of its own, which runs
  as the page mounts with the remembered value.
- The two playlist pages pass no choice and draw the menu they drew before.

**The grid.** The grid measures its body's rows again when the checkbox
changes, and its pinned first row only when that row is handed in again,
because the pinned row is a row model of its own (AG Grid 35.3, measured
2026-10-14). The script does both, and lists it with the grid-specific work
an upgrade can break.

**What being wrong costs.** One checkbox that is off unless turned on, and
nothing stored but its state. Relabelling it or taking it out is a small
change.

**If the maintainer had chosen otherwise.** A3 would have moved to the
typical score's proposal, the menu would have kept its two checkboxes, and
the shared menu module and the playlist pages would not have been touched.
Nothing in A1, A2, or the view depends on it.
