# 2026-10-18: The Run List's Heading Line Is For Screen Readers Only

Status: Accepted

The run list on Run History no longer shows its heading line, in either view.
The latest-run card right above the list names its scenario, and Scenario
Stats counts its runs, so the line was a second label for one fact. It keeps
its words for screen readers, and the list's view switch and two buttons move
up to the header's first line, which gives the list about 35 px more rows.

**Superseded in part (2026-10-25).** [The latest-run card's first line drops the scenario's name](2026-10-25-the-latest-run-cards-first-line-drops-the-scenarios-name.md),
so the card above the list no longer names it. The line stays for screen
readers only, for a new reason: the Selected scenario field and the chart's
title, beside the list, name the scenario on screen, and on a line of its own
it would cost about 35 px of list rows. The rest stands.

**Ruling and delivery.** R3 of
[#388](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/388),
ratified by the maintainer on 2026-10-18 at `0fcac03`, "I ratify the
proposal." Before it, the maintainer's lean of 2026-10-14. They noted that
the All scenarios heading counts every run in the store, a total Home already
gives. Built in
[#391](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/391).
Current behavior is in
[run_history.md](../../specs/run_history.md#the-run-list).

**Why it waited for the card.** Before
[the latest-run card's rule](2026-10-18-the-latest-run-card-reports-the-selected-scenarios-latest-run.md),
the card could show another scenario, and the heading was what named the
list's scenario. Removing it without that rule would have left nothing above
the list naming its scenario during a lookup.

**What changes.**

- The heading line keeps its `dmc.Text`, its words (`{scenario} · {n} runs`,
  `1 run`, `All scenarios · {n} runs`) and its place before the view switch,
  and takes the app's `visually-hidden` class. A screen reader hears it where
  it heard it before.
- **It is not an HTML heading, and it does not become one.** An `h2` would
  give the page a heading to jump to once Scenario Stats' `h2` went, but it
  would change what a screen reader hears, and what NVDA makes of the page
  was not checked. A pull request that checks it can propose one.
- The class's absolute position takes the line out of the header's flex line,
  and the rule that gave it a whole line, `flex: 1 0 100%`, is gone. So the
  view switch, **Expand all** and **Columns** sit on the header's first line.
- The `display: none` rules for the list's two states with nothing to show
  stay, so in those states a screen reader hears no heading line, as before.
- A scenario with no runs no longer reads `{scenario} · 0 runs` above the
  list. The card reads "No runs yet", and the list shows the newest session
  alone, as before.

**Measured.** The list's header is 56 px tall where it was 90.8, at 2560 px,
in Edge and Firefox, in both views.

**Set aside.** Keeping the heading while the card names the scenario, a
second label for one fact.

**What this changes in older entries.** Each keeps its text and gains a dated
note.

- [2026-10-12, the run list is a second column](2026-10-12-the-run-list-is-a-second-column-beside-the-chart.md):
  the list's heading on a line of its own, above its buttons.
- [2026-10-14, the All scenarios view](2026-10-14-the-run-list-has-a-second-view-all-scenarios-that-shows-each-session-whole.md):
  the heading keeping the line of its own, with the switch on the second.
