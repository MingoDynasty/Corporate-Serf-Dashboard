# 2026-10-25: The Latest-Run Card's First Line Drops The Scenario's Name

Status: Accepted

Run History's latest-run card now opens with `Latest run · {age}`, as the PB
card opens with `PB · set {age}`. The card always reports the selected
scenario, so its name only repeated the Selected scenario field and the
chart's title. The run list's heading line stays off screen, now because
those two name the scenario.

**Ruling and delivery.** SC2 of the Run History score cards proposal,
[#430](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/430),
ratified by the maintainer on 2026-10-25 at `c77ad06`: "I ratify the proposal
on PR #430 at c77ad06." Before it, the maintainer's lean of 2026-10-25: "Keep
changes 2 to 5 as proposed: no scenario name, the rebalanced lines,
top-aligned cards, and readable badges." The first review wave endorsed the
row. Built in [#431](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/431),
the proposal's first delivery PR. Current behavior is in
[run_history.md](../../specs/run_history.md#the-latest-run-card).

**Why.** Since
[the card follows the selection](2026-10-18-the-latest-run-card-reports-the-selected-scenarios-latest-run.md),
its scenario is always the Selected scenario field's, which the chart's title
names too: three times on screen at once. Neither of the other two score
cards names it.

**What changes.**

- The first line is `Latest run`, then a span that holds ` · ` and the run's
  age, hidden with no run. The age's hover, its keyboard focus and
  `AGE_SCRIPT` are unchanged.
- The line is no longer a flex container, as the PB card's first line is
  not. It was one so a long name could be cut short; a flex container drops
  the space before the age, and a screen reader would hear the words run
  together. The label's own item and its classes go with the name.
- The scenario's span, its `title` and the card's `heading` output and id
  are gone. `show_latest_run` writes when the run ended, the lines under the
  first, and the ring's store.
- A long name is no longer cut short on the card, and its tooltip goes with
  it.
- A screen reader that reaches the card hears no scenario's name there. The
  nearest names are the Selected scenario field and the run list's hidden
  heading line. The Chromium accessibility tree reads the card as
  `Latest run · 9 days ago`, then its score, badge and lines (2026-10-25,
  headless Edge).

**The run list's heading line stays for screen readers only.** It left the
screen
([2026-10-18](2026-10-18-the-run-lists-heading-line-is-for-screen-readers-only.md))
because the card right above the list named its scenario. After this entry
the names nearest the list are the chart's title, beside it, and the
Selected scenario field. The list's This scenario view lists only the
selection's runs, so its scenario is still the page's one scenario. Bringing
the line back would cost about 35 px of list rows.

**What this changes in older entries.** Each keeps its text and gains a dated
note.

- [2026-10-18, the card follows the selection](2026-10-18-the-latest-run-card-reports-the-selected-scenarios-latest-run.md):
  the scenario's name on the first line, plain text with its whole name as a
  title.
- [2026-10-18, the heading line](2026-10-18-the-run-lists-heading-line-is-for-screen-readers-only.md):
  its reason. The line stays as it is.
- [2026-10-14, a card's lines follow their role](2026-10-14-a-cards-lines-follow-their-role-in-the-players-next-action.md):
  its example of a relative age quotes the old first line. The rule is
  unchanged.
