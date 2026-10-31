# 2026-10-30: The Run Viewer Shows Eleven Settings And Marks A Changed One

Status: Accepted

A run shows the same eleven settings cards on every run, in two rows, so the
grid never changes shape between runs. A card whose value differs from the
setting's most common value over the run's typical runs is tinted, with that
typical value under its own. A setting the run's file doesn't have reads as
not recorded and is never marked. The crosshair's color has no card, because
the game writes it wrong.

**Ruling.** RV5 of
[proposal #450](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/450),
ratified by the maintainer on 2026-10-30 at `f80c109` ("Sounds good. I
ratify."), as amended in review. Their leans before that: cards of one size
with the count on hover (2026-10-29); "keep things simple and just show all
the cards. We can always consider trimming things later." (2026-10-29); "I'd
prefer that this info lived inside the respective card." (2026-10-29), on a
summary of changed settings; then, on 2026-10-30, keeping the Crosshair color
card and reporting the game's bug, and later the same day leaving the card
out of the first version. Shipped in
[#455](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/455).
What the page does today is in
[run_history.md](../../specs/run_history.md#settings).

**The cards** (`_settings` in `source/kovaaks/run_viewer.py`, `_card` in
`source/components/run_viewer_panel.py`), the same on every run, six to a
row. The first row is the aim setup: Sensitivity, Vertical sensitivity, DPI,
FOV, Crosshair and Crosshair scale. The second is set once: Hide gun,
Resolution, Resolution scale, Frame cap and Input lag.

| Card | Shows |
|---|---|
| Sensitivity | The run list's Sensitivity text, with a converted run's recorded setting |
| Vertical sensitivity | `Same as horizontal` when equal, else the value and scale |
| DPI | `DPI` as written |
| FOV | The run list's FOV text, such as `103 Overwatch` |
| Crosshair | `Crosshair` without `.png` |
| Crosshair scale | `Crosshair Scale` as written |
| Hide gun | `Yes` or `No` |
| Resolution | `Resolution` as written |
| Resolution scale | `Resolution Scale` as a percentage |
| Frame cap | `Max FPS (config)`, a trailing `.0` dropped |
| Input lag | `Input Lag` as written |

**The mark.** A card is marked when the run has a value, there is a typical,
and the two differ. The typical is the setting's most common displayed value
over the typical runs that have one, a tie going to the value the latest
typical run used. A marked card is tinted and shows `Typical {value}` under
its own, so the change isn't carried by color alone, and every card keeps
that line's room, so a marked card never grows. Its hover is the value, then
`Typical {value} · on {n} of your {N} typical runs`; an unmarked card's hover
is its value, so a value cut short can be read whole.

**Not recorded.** A value the stats file doesn't have reads `Not recorded`,
with the hover `The run file doesn't have this setting. Older versions of
KovaaK's didn't record it.`, and is never marked. The 570 runs from
2019-07-14 to 2021-07-20 have no DPI, Resolution or Resolution Scale line.

**Why all eleven.** Show-or-hide rules multiply states and edge cases, and a
grid that never changes shape reads the same on every run. Over all 9,280 of
the maintainer's runs, Hide Gun and Input Lag never changed, and DPI,
Resolution, Resolution Scale and Crosshair barely did, but any of the eleven
can change a run, so the rarely changed five stay on screen rather than
living only in Everything Recorded.

**Rejected.**

- A Crosshair color card (shelved as S10). In-game tint 00FF00 is written
  `000100FF`, and a tint of 147245 was written `000000FF`; every file from
  KovaaK's 3.7.0 on holds such an eight-digit value. A card would show a
  value that isn't the player's tint and draw its square black. A fixed game
  would correct new files only, so new runs would then read as a changed
  color. The value stays in Everything Recorded as written. Revisit when a
  fixed version ships, marking a change only when both values come from
  fixed versions.
- Showing a setting only when it changed (v7 to v10), which made the grid
  change shape between runs; a notice under the tiles for a changed setting
  (v8 to v11), which this row moved into the card.
- The scenario's version and the performance file's time scale as cards:
  the player can't change either. The version is in Everything Recorded,
  as the stats file's `Hash:` line; the time scale is the performance
  file's, which the viewer doesn't read.

**Provenance.** Proposal by `claude-opus-5-5` (#450), read by `gpt-6-astra`
(flagship, first wave) and reviewed by `gpt-6.1-sol` (the seat) and
`claude-fable-5-1`. Built by `claude-opus-5-5` in #453, #455 and
[#456](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/456).
