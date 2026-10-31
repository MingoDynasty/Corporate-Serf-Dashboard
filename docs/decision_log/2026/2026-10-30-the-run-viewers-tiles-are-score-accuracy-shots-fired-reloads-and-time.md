# 2026-10-30: The Run Viewer's Tiles Are Score, Accuracy, Shots Fired, Reloads And Time

Status: Accepted

A run opens with a row of tiles in the same order on every scenario, its
score and accuracy first, with a completion time added on a scenario scored
by time. Each tile shows the run's value over its typical and the
difference, green when better and red when worse. That completion time is
the first the app shows anywhere. A tile for how long the fire button was
held was left out of the first version.

**Ruling.** RV3 of
[proposal #450](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/450),
ratified by the maintainer on 2026-10-30 at `f80c109` ("Sounds good. I
ratify."), as amended in review. Their lean before that, 2026-10-29: "I now
vote for always showing them, regardless of the type of run. Otherwise the
user has to adjust columns in the right side panel, when the intent of the
Run Viewer UI is to show everything applicable to the run." Fire held was
their idea (2026-10-29); on 2026-10-30 they leaned toward leaving it out of
the first version and shelving it. Shipped in
[#455](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/455).
What the page does today is in
[run_history.md](../../specs/run_history.md#the-tiles).

**The tiles** (`_tiles` in `source/components/run_viewer_panel.py`):

- Score, Accuracy, Shots fired and Reloads on every run, then Time when the
  run's own version is time-scored. The four every run has come first, so a
  tile never moves between scenarios.
- Each shows the run's value over `Typical {value} · {difference}`, with the
  typical's hover from
  [the typical runs entry](2026-10-30-the-run-viewer-measures-a-run-against-its-typical-runs.md).
  The difference is worked from the two values as shown, so the three add up
  on screen. It reads `+` or `−` (the minus sign, U+2212) before it, and no
  sign on zero, as the v12 mockup drew it.
- Score is formatted as everywhere else, and its typical to its typical
  runs' precision, as Scenario Stats shows the typical score. Accuracy is
  KovaaK's hits over shots, to two decimals, with its difference in
  percentage points (`+1.82 pts`). Shots fired and Reloads read as counts,
  and a median between two runs keeps its half (`5,776.5`).
- A higher Score or Accuracy and fewer Reloads are green, the reverse red.
  Shots fired is uncolored, since more shots is neither. A difference that
  reads zero is uncolored. Reloads reads 0 on a scenario with unlimited ammo.
- A figure the run's file lacks reads `Not recorded`, dimmed and with no
  hover, as a Settings card does. The proposal's copy had it for cards only;
  Reloads is missing from 514 of the maintainer's runs, from 2019 to 2021.

**Time.**

- The clock's constant less the score, `C − s`, for the run's own version
  (`get_version_pace_basis`), never the scenario's newest version's. It is
  exact, where the run length the stats file gives is up to 1.7% off on a
  60-second run, because the file name's end time is in whole seconds. It
  reads `m:ss.s`, such as `1:54.3`, with its difference in seconds
  (`−2.4 s`), and a faster time is green.
- Its typical is the median of `C − s` over the typical runs only when every
  one of them is of the run's version, by `eligible_pace_constant`, as the
  latest-run card measures a run against its typical, so the tile and the
  score line agree. Otherwise the tile shows the run's time alone.
- A run whose version the app can't tell is time-scored has no Time tile, as
  the card then measures it by score. A time of zero or less isn't a time:
  the tile shows none, and such a typical run doesn't count.

**Rejected.**

- A Fire held tile (shelved as S9): how much of the run the fire button was
  down, as the run's shots a second over the scenario's fastest-firing run.
  The file records neither the button nor the weapon's fire rate, so its
  100% is a stand-in, and the run length's rounding alone moves it 1 to 2
  points. On a fixed-length scenario, Shots fired against its typical shows
  the same drop without the stand-in. Revisit if a file records the fire
  rate or how long fire was held.
- Dropping Shots fired and Reloads: the maintainer chose to show everything
  that applies rather than send the player to the run list's Columns menu.

**Supersedes in part** the
[2026-10-05 pace entry](2026-10-05-time-scored-scenarios-are-measured-by-pace.md),
which says no completion time is shown anywhere and kept Run History out of
its scope. Time shows one, and By Bot shows each bot's split
([By Bot's entry](2026-10-30-by-bot-measures-each-bot-against-its-own-typical-and-names-no-bot.md)).
The pace rule and its detection stand, and the entry gains a note.

**Provenance.** Proposal by `claude-opus-5-5` (#450), read by `gpt-6-astra`
(flagship, first wave) and reviewed by `gpt-6.1-sol` (the seat) and
`claude-fable-5-1`. Built by `claude-opus-5-5` in #453, #455 and
[#PR3NUM](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/PR3NUM).
