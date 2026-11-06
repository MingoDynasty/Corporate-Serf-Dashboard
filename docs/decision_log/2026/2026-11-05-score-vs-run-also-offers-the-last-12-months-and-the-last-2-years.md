# 2026-11-05: Score vs Run Also Offers The Last 12 Months And The Last 2 Years

Status: Accepted

Score vs Run's range now offers the last 12 months and the last 2 years,
beside its counts of runs. On scenarios with fewer than 100 runs, the runs
that stretch the score axis are mostly early ones from another era, and a
range of days leaves them off with no new control. Only the chart's points and
its score axis change. A remembered range of days shows an empty chart on a
scenario not played in that time, as Score vs Time already does.

**Approval.** The maintainer approved the two entries on 2026-11-05. They come
from a research note of that day on the maintainer's own runs, which weighed
them against a per-run Hide, a minimum-date picker, and an automatic clamp of
the score axis, and recommended these. Built in
[#469](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/469).
What the chart does today is in
[run_history.md](../../specs/run_history.md#the-chart).

**The rule.**

- Score vs Run's select offers `Last 50 runs`, `Last 100 runs`,
  `Last 200 runs`, `Last 12 months`, `Last 2 years`, and `All runs`, in that
  order. Its id, `run-history-run-range`, and its default, `100`, are
  unchanged.
- The two new entries count calendar dates as the day modes count them: 365
  and 730 dates, counting today, from local midnight on the app's clock
  (`first_moment_of_day_range`). The `run-history-today` store, already an
  input of the chart, redraws them after midnight.
- Their values carry a unit, `365d` and `730d`. A bare number is a count of
  runs, so the days select's `365` never reads as 365 runs under Score vs Run.
  Like any value the select does not offer, it reads as the default.
- Play order puts a run's end first, so a range of days keeps the scenario's
  newest runs, as a range of runs does. They are plotted the same way: in play
  order, evenly spaced, each at its number in the whole history, with the
  typical score's values taken from the whole history's.
- `No runs in this range` over `Choose a longer range or play more runs.` is
  now reachable in Score vs Run, and the overlays are skipped there as in the
  day modes.
- Unchanged: the stars, the ring, the typical score and its bands, the PB
  line, the Score threshold line, the rank lines, the run list, and the
  cards. No control and nothing persisted is new.

**Why.** From the research note, on the maintainer's 9,284 runs over 866
scenarios through 2026-10-29, at the chart's default view:

- Of the 231 scenarios with 10 runs or more, 23 had a score axis stretched
  low: their lowest 5% of plotted runs took a quarter or more of its span.
  All 23 have fewer than 100 runs, so `Last 100 runs` is their whole history.
  No full 100-run window was stretched low.
- In 18 of the 23 the lowest plotted run is over a year old, and in 3 over
  two years. 17 of them were recorded at another sensitivity or scale than
  the latest run. They are early runs on earlier settings at the old end of the
  window, so a rule built for lone outliers does not find them.
- On those 23, `Last 12 months` leaves out the lowest run on 18, cuts the
  span by a quarter or more on 12, and leaves 20 runs or more on 14.
  `Last 2 years` does so on 3, 3, and 19. Hiding the single lowest run cut
  the span on 13. A 1.5 IQR clamp cut it on 8, and across all 231 it would
  have clipped a PB on 39.
- Ground Plaza Sparky V3, 22 runs, loses its 2020 runs under either entry.
  The note's model of the axis, which counts the runs, the PB, and the rank
  lines but not the typical score's bands, puts the cut at 76%.

**Not chosen.** A per-run Hide needs a new store and would let the chart and
the run list disagree, which
[the 2026-10-12 entry](2026-10-12-the-run-history-chart-plots-every-run-and-draws-no-summary-line.md)
was written to prevent. A minimum date is the retired `Oldest date to
consider` picker, and an absolute date chosen for one scenario is wrong for
the next. An automatic clamp misses a trend and clips the PB the page exists
to show. A floor such as "never fewer than the last N runs" would make
`Last 12 months` mean something else. A recent bad run stays on the chart.

**Costs, accepted.**

- A browser that remembers `Last 12 months` shows `No runs in this range` on
  a scenario not played in a year: 79 of the maintainer's 231 scenarios with
  10 runs or more on 2026-11-05, and 3 under `Last 2 years`. Score vs Time
  has carried the same consequence at its 90-day default since 2026-10-12,
  and Follow lands on the scenario just played, so it does not show in a
  session.
- The typical score's bands still count runs before the range, so at the
  range's first runs they can hold part of the old stretch on the axis. On a
  synthetic scenario shaped like Ground Plaza (23 runs, the last 10 in the
  last 12 months, the oldest 799.8 and the rest 848 to 894), the score axis
  spanned 124 under `Last 100 runs`. Under `Last 12 months` it spanned 27
  with every overlay off, 55 with Middle 80% alone, and 57 at the defaults.

**What a stored value does on another build.** Dash stores the choice with the
default it was made against, `["365d","100"]`. Every value an earlier build
could store, `50`, `100`, `200`, or `all`, is still offered, so it comes back
as it was. On a build from before this entry, checked in the app with the
chart module of `0fdde2af` and the same browser storage, Dash restores `365d`,
the select shows no entry, and the chart plots the last 100 runs. The stored
value stays until another entry is picked, so the next build that offers it
shows `Last 12 months` again, which the same check saw.

**Plotly's autorange holds the overlay lines.** Measured 2026-11-05 in the
app, on a synthetic scenario whose PB of 1,000 was set 1,000 days ago and
whose last 12 months score 700 to 744, under `Last 12 months`. The score axis
ran from 584 to 1,082 with every overlay on, 670 to 1,065 with the typical
score's line and bands off, 675 to 1,004 with the PB line off too (the
Score threshold sat at 950), and 696 to 751 with the threshold off as well.
So the lines `add_hline` draws are in plotly's autorange, as the rank-overlay
code had said without a measurement. The rank lines are drawn the same way
and were not measured on their own.

**What this changes in older entries.** The 2026-10-12 entry's **Ranges**
bullet, that Score vs Run counts runs, and its empty-state bullet, that `No
runs in this range` is reachable only in the two modes that count days. Its
note says so.
