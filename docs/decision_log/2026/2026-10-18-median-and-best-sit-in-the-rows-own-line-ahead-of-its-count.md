# 2026-10-18: Median And Best Sit In The Row's Own Line, Ahead Of Its Count

Status: Accepted

With Median and best on, a row's median and best now sit in the row's own
line, just before its run count, instead of on a second line under it. That
holds for scenario rows under All scenarios and for session rows under This
scenario. The first row under This scenario keeps the second line, because
its length and its In progress badge leave the figures no room. Every other
row keeps its usual height with the checkbox on, and the count stays at the
right edge whether it is on or off.

**Rulings.** By the maintainer, 2026-10-18, in the design chat that compared
versioned mockups built from their own runs: "Ruled: Option 1 for scenario
rows under All scenarios (Median · Best · runs, star last)", and, after the
This scenario rows were measured, "Ruled: This scenario's session rows also
go on one line (Median · Best · count), except the first row, which keeps its
second line." This supersedes the second-line part of
[the 2026-10-14 entry](2026-10-14-the-run-lists-columns-menu-offers-median-and-best-off-to-start.md),
whose checkbox, default, and choice of rows stand. What the list does today is
in [run_history.md](../../specs/run_history.md#the-run-list).

**What the line says.**

- A scenario row: `Median {median} · Best {best} · {count} runs`, then the
  star when the visit set a new PB. The count and the star sit where they sit
  with the checkbox off, so turning it on only adds to their left. A one-run
  row reads `Score {score} · 1 run`.
- A session row under This scenario: `Median {median} · Best {best} · {n} of
  {m} runs`, the count still the button that shows the whole session.
- The first row under This scenario carries `figures_below`, set by the
  server, and keeps its figures on a second line. It alone gives the
  session's length, and it says In progress while the session is played.
  With the figures in its line as well, a session over an hour long ran about
  10px past a 500px list. Every other session row needed 316 to 335 of its
  462px.
- Only a row with `figures_below` grows when the checkbox turns on. Turning it
  on or off still makes no request.

**Why the earlier reason didn't hold.** The 2026-10-14 entry chose the second
line because inline figures "left a scenario's name about 27 characters, and 9
of the 36 names in the maintainer's newest 30 sessions are longer". Measured
in a 500px list on the maintainer's newest 30 sessions, names up to 41
characters fit beside the figures. 5 of 157 scenario rows were cut short, all
of them one scenario, 1 of 34 names. A cut name is whole in the row's hover,
and the row already gives up its name before its facts.

**Where the evidence is against it.** Longer names than the maintainer's, or
longer figures, cut more names short. Wrapping only a row whose name would be
cut was mocked and set aside: the grid needs every row's height before it
draws the row, so the script would have to measure text first, which is work
an AG Grid upgrade can break, for 5 rows on this data. A larger list font
cuts more too: a step up for the facts cut 4 names, and 14px names and runs
cut 7.

**What being wrong costs.** The placement is a few lines of the list's
script and one row field. Going back to a second line is the same size.
