# 2026-10-18: A Run's Accuracy Shows Two Decimals

Status: Accepted

Run History's run list, latest-run card, and PB card show a run's accuracy to
two decimals, such as 82.31%, where they showed the whole percent. KovaaK's
shows accuracy to two decimals in game, and a whole percent hid differences
between runs that a player compares. A value keeps its trailing zeros, so
100.00% lines up with 82.31% in the run list's right-aligned column.

**Direction.** Asked for by the maintainer, 2026-10-18, in a chat: "at least
1 or 2 decimals of precision", since the game uses two, for the run list, the
PB card, and the latest-run card alike. Two decimals rather than one matches
the game. Supersedes the whole percent in
[the run list entry](2026-10-12-the-run-list-is-a-second-column-beside-the-chart.md),
which the latest-run card followed, and in
[the PB card entry](2026-10-14-the-pb-card-shows-the-local-record-and-next-rank.md).

- **What is measured is unchanged.** It is the hit accuracy, hits over shots
  of the first weapon row the stats file lists. The scenario table's PB
  Accuracy still prefers the damage accuracy, so one run can still show two
  accuracies. *(Superseded 2026-10-18: PB Accuracy shows the hit accuracy
  too. See
  [PB Accuracy Shows Hit Accuracy, As The Game Does](2026-10-18-pb-accuracy-shows-hit-accuracy-as-the-game-does.md).)*
- **The precision is the app's choice, not the file's.** The stats file
  records shot and hit counts, not a percentage (`Track Master 100,6000,3866,`
  on the maintainer's files, 2026-10-18), so the accuracy is exact and only
  its display is rounded.
- **A half rounds up,** as the whole percent did, in `format_percent` in
  `source/utilities/utilities.py`. Real halves occur: 57 hits of 800 shots is
  7.125%, which reads 7.13%. Over every hit count up to 3,000 shots there are
  3,600 halves, and plain float arithmetic rounds 63 of them down, so the
  helper strips float noise before it rounds.
- **Trailing zeros stay, unlike PB Score's**
  ([2026-09-27](2026-09-27-the-scenario-table-drops-trailing-zeros-from-pb-score-and-pb-cm360.md)).
  That ruling drops them because no comparison runs down a column of
  different scenarios. The run list compares one scenario's runs down a
  right-aligned column, where lined-up decimal points pay. The scenario
  table's PB Accuracy and percentile keep fixed two decimals too.
- **The chart's hover is left as it was.** It already showed two decimals,
  but prints the rounded number, so it drops trailing zeros (`82.3%` where
  the list reads `82.30%`) and sends a half to the even digit.
