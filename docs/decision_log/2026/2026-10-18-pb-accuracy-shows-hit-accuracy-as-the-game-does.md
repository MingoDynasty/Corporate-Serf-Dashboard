# 2026-10-18: PB Accuracy Shows Hit Accuracy, As The Game Does

Status: Accepted

The playlist scenario tables' PB Accuracy shows the PB run's hit accuracy,
the share of its shots that hit, where it showed the share of possible damage
done. KovaaK's shows hit accuracy for a run, so the column disagreed with the
game by a point or more on 145 of the maintainer's scenarios, and on most
click scenarios it read about half the game's figure. The column now reads
what the game and Run History read for the same run.

**Direction.** By the maintainer, 2026-10-18, in a chat. They confirmed that
KovaaK's shows 82.31 for their VoxTS Click Medium PB, in the in-game
leaderboard detail's "Accuracy/Damage Efficiency" row. A Fable consult
(`claude-fable-5-1`, xhigh) recommended hit accuracy, and the maintainer
chose it, with the damage parse removed and no header tooltip. This reverses
behavior that no decision-log entry recorded. Supersedes the PB Accuracy
sentences in
[A Run's Accuracy Shows Two Decimals](2026-10-18-a-runs-accuracy-shows-two-decimals.md)
and [the PB card entry](2026-10-14-the-pb-card-shows-the-local-record-and-next-rank.md).

- **Where the damage figure came from.** The column was added on 2026-05-12
  (PR #16) to mirror the leaderboard API's `attributes.accuracyDamage`. The
  stats file has no such field, so damage done over damage possible stood in
  for it, chosen from the field's name and never checked against the game.
- **What KovaaK's stores.** `accuracyDamage` holds hits over shots, as a
  percentage times 1,000, truncated
  ([kovaaks_api_notes.md](../../kovaaks_api_notes.md#leaderboardscoresglobal)).
  All 17 of the maintainer's PBs probed on 2026-10-18 matched the local
  file's hits over shots and none matched the damage figure, across click and
  tracking scenarios whose damage figure ran from near zero to equal to the
  hit figure. The VoxTS Click Medium PB hit 107 of 130 shots and did
  10,700 of 26,000 possible damage: KovaaK's stores 82307 and shows 82.31,
  where the table showed 41.15%. The stats file's per-kill columns name the
  two figures Accuracy and Efficiency.
- **How far apart they were.** Over the maintainer's stats folder (866
  scenarios, 9,212 runs, 2026-10-18), the PB runs of 177 scenarios had two
  different figures, 145 of them a point or more apart. On 98 the damage
  figure was half the hit figure to two places, as on VoxTS, whose kill rows
  record 100 damage done of 200 possible. On 7 it was zero.
- **Format and order.** The column formats with `format_percent`, as Run
  History does, and sorts on the unrounded percentage, so the order never
  disagrees with the display. Its old `.2f` format read an exact half one
  hundredth low: 57 hits of 800 shots read 7.12% where Run History reads
  7.13%.
- **The damage figure is no longer read.** Nothing else used it, runs are
  held in memory only, and its fallback to hit accuracy never fired: all
  9,212 files record damage possible above zero. Efficiency, if it is ever
  wanted, returns as a field and a column of its own, under KovaaK's name.
- **Left open.** No probe found a scenario whose "Accuracy/Damage
  Efficiency" row holds efficiency. Two probed scenarios have hits that do
  less than their full possible damage, Pistol Strafe Gallery Sparky and VT
  Pasu Intermediate S5 Multi, with damage figures at 0.95 and 0.98 of the
  hit figure, and both store hit accuracy. None was chosen for a known
  headshot multiplier, falloff or splash damage. If such a scenario turns
  out to hold efficiency, the rule is still to show what the game shows. No run has two weapons that both fired: in all 123
  two-weapon files the second fired no shots, so the first weapon row, the
  summary hit and miss counts, and the sum over weapons agree.
