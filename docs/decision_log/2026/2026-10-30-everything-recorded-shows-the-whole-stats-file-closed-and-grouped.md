# 2026-10-30: Everything Recorded Shows The Whole Stats File, Closed And Grouped

Status: Accepted

At the bottom of a run, a closed section holds everything the run's stats
file recorded, under the game's own names and grouped by kind. A group whose
fields all read zero folds to one line, and a field the app doesn't know
goes to a group of its own, so a game update never hides one. The section
stays open while the player steps from run to run in the list, and starts
closed each time a run opens.

**Ruling.** RV6 of
[proposal #450](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/450),
ratified by the maintainer on 2026-10-30 at `f80c109` ("Sounds good. I
ratify."), as recommended. Their leans before that, 2026-10-29: everything in
the stats file, organized and low priority, collapsed or at the bottom; and
on 2026-10-30, "Yes, keep folding." Shipped in
[#455](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/455).
What the page does today is in
[run_history.md](../../specs/run_history.md#everything-recorded).

**The groups** (`RECORDED_GROUPS` and `recorded_groups` in
`source/components/run_viewer_panel.py`), each in this order, from the v12
mockup's lists:

- **Result:** Score, Kills, Deaths, Hit Count, Miss Count, Total Overshots,
  Reloads, Damage Done, Damage Taken, Avg TTK, Fight Time, Time Remaining.
- **Other Counters:** Midairs, Midaired, Directs, Directed, Distance
  Traveled, MBS Points.
- **Run:** Scenario, Hash, Game Version, Challenge Start, Pause Count, Pause
  Duration, Avg Target Scale, Avg Time Dilation, Avg FPS.
- **Settings:** Sens Scale, Sens Increment, Horiz Sens, Vert Sens, DPI, FOV,
  FOVScale, Hide Gun, Crosshair, Crosshair Scale, Crosshair Color,
  Resolution, Resolution Scale, Max FPS (config), Input Lag.
- **Other:** any field none of those names, in file order. Over the
  maintainer's 9,284 stats files, all 42 field keys land in the four named
  groups, and only four hand-added note lines go to Other.
- Then **Files** (`Run file` with the stats file's name, `Performance file`
  reading `Found` or `None`), **Weapons** (the weapon rows as written) and
  **Kills** (the kill table, every column the file has, in file order, or
  `This run's file records no kills.`). A group with no field in the file is
  left out.

**Folding.** A group folds to `All zero: {field names}` only when every field
it names is in the file and reads zero. A field the file doesn't have, or has
with no value, isn't zero, so its group stays open: Other Counters never
folds on the 570 files from before KovaaK's 3.7.0, which have no MBS Points
line. Other folds when each of its fields reads zero.

**Drawn as data.** The tables are handed to Mantine's table as data, never as
one Dash component per cell, because a kill table runs to hundreds of rows
and Dash's renderer slows with the square of its component count. A table
wider than the viewer scrolls sideways in its own box.

**Open through a switch.** The section is closed each time a run opens, and
stays open or closed as it was while another run is switched to from the
list. React keeps the open element while the section keeps its place among
the run's sections, so By Bot leaves a hidden placeholder on a run without a
table ([By Bot's entry](2026-10-30-by-bot-measures-each-bot-against-its-own-typical-and-names-no-bot.md)).

**Why keep it.** It is the fallback for everything shelved, power users may
spot ideas in it, and it costs little once the file is read whole for By Bot
and Settings. It shows fields that answer no question today, such as Midairs
and MBS Points, which is why it starts closed. It is the first thing to cut
if the viewer ever has to shrink.

**Provenance.** Proposal by `claude-opus-5-5` (#450), read by `gpt-6-astra`
(flagship, first wave) and reviewed by `gpt-6.1-sol` (the seat) and
`claude-fable-5-1`. Built by `claude-opus-5-5` in #453, #455 and
[#PR3NUM](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/PR3NUM).
