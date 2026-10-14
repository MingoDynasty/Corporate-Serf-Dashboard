# All Scenarios Proposal

Status: Proposed
Date: 2026-10-13

## TL;DR

The Run History page lists one scenario's runs by session, so what else was
played in a session is a count on a row, and the order it was played in is
nowhere on screen. This proposal adds a second view to that list, All
scenarios, which lists each session whole: the scenarios played in it, in
order, with each one's runs under it. A switch above the list chooses the
view, and a session's run count in the first view becomes a link to that
session in the second. A pair of figures that sum up the runs under a row,
their median and their best score, can be turned on from the Columns menu.

## Decisions needed

Three rows: A1 to A3. **Nothing in this proposal is ratified.** Each row
gives what the maintainer has said in chat, which is a lean or an agreement
and not a ruling, then argues a recommendation and says what choosing
differently would change. Reviewers are invited to challenge every row, and
every author-owned choice in [Design](#design).

This is piece 5 of 5 of the Run History work, and the last to be proposed.
The groundwork has merged. Sessions is ratified and built. The page is
ratified and has been public since
[PR #373](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/373).
The [Run toasts proposal](run_toasts_proposal.md) is ratified and not yet
built. That change and this one don't wait for each other.

**The view itself is not a row.** Its shape was leaned to on 2026-10-07,
from a full-size mockup that replays the maintainer's own sessions, and the
outline the maintainer agreed on 2026-10-10 ("Merged breakdown is a go.")
lists these three rows and not the view. So the view is author-owned and
argued in Design, each item with the date of its lean.

**Four readings of the view were agreed on 2026-10-13.** They were put to
the maintainer as a numbered list, and the answer was: "1-4: agree with all
four". That is agreement in chat with no ruling word, so each is a lean and
stays open to reviewers. None is a row. Design states each where it applies:

1. A row under a session is a visit, so a scenario that is left and returned
   to within a session gets a second row
   ([What the tree lists](#what-the-tree-lists)).
2. **Expand all** opens every session down to its scenario rows, and **Show
   all runs** opens one session's scenario rows down to their runs
   ([Opening and closing](#opening-and-closing)).
3. A click on a scenario's name moves the chart to that scenario and keeps
   the view on All scenarios
   ([Selecting a scenario from the tree](#selecting-a-scenario-from-the-tree)).
4. The list starts on This scenario, and the switch is remembered across a
   reload ([The switch](#the-switch)).

**Already decided, and binding here.** The proposal is held to these and
doesn't reopen them:

- **The run list is a second column, 500 px wide** (row R3,
  [2026-10-12][second-column]). This proposal adds a view to that list and
  moves nothing else on the page.
- **The list is built on AG Grid Community with hand-built group rows** (row
  R4, [2026-10-12][grid]). That entry leaves a rule: "Any later change to
  what a screen reader hears, to the keys, or to where focus goes repeats
  that walk." This proposal changes all three, so the NVDA walk is owed. It
  is in the [Delivery plan](#delivery-plan), under a rule already ratified,
  and is not a new row. The same entry says: "A failed task is the
  maintainer's to decide."
- **Follow and a scenario link clear a Playlist filter that does not list
  the scenario** (row R7, [2026-10-12][clear-filter]). A1 adds one more way
  in to that rule.
- **The chart plots every run and draws no summary line** (row R5,
  [2026-10-12][every-run]). The chart is not changed here.
- **What a session is, when one is in progress, and what a visit is** (rows
  S1 to S3, [2026-10-11][sessions-entry], and the
  [sessions spec](../specs/sessions.md)). Row S4 of the same entry gives the
  typical score's definition to a later proposal of its own. A3 doesn't
  define it.
- **The three skill-judgment principles** in the roadmap's
  [Guiding principles](../roadmap.md#guiding-principles)
  ([2026-10-04][principles]).
- **How a past run is marked** ([2026-10-12][check]). The tree marks runs by
  the same function, one scenario at a time.
- **The Columns menu's rulings** ([2026-10-05][columns-menu]): one
  remembered checkbox per choice, never one checkbox group.
- **The rules for a remembered control**
  ([2026-09-19][query], [2026-10-12][own-ids]): its layout default is the
  same on every visit, and a renamed id or a changed default resets its
  stored value in every browser.
- **One active tab** is the supported way to use the app.

### A1. A click on a scenario's name in the tree selects it, and clears a Playlist filter that does not list it

Status: Open. The maintainer's agreement in chat, 2026-10-10: "Agree, tree
click should take the same rule as Follow."

**Why it is still a row, though R7 is ratified.** The ratified page
proposal looked ahead to this click and sent it here by name: "The same
rule will cover a click in the All scenarios tree (row A1 of that
proposal)"
([R7, at `53170d6`](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/blob/53170d6/docs/proposals/run_history_proposal.md)).
The outline the maintainer agreed on 2026-10-10 lists it as a row too. R7's
ratification settles the rule. Whether it also settles this click is the
maintainer's to say, and this proposal doesn't infer it. Accepting the
recommendation confirms what R7 foresaw.

The material consequence: a click on a scenario's name under All scenarios
can empty the Playlist filter, and the browser then remembers the emptied
filter.

**Recommendation: under All scenarios, a click on a scenario's name selects
that scenario for the whole page. Where the Playlist filter does not list
it, the filter is cleared in the same step, as it is for Follow, for a
`?scenario=` link, and for the latest-run card's button.**

- **The tree lists scenarios the filter does not.** The filter narrows the
  Selected scenario dropdown to one playlist. The tree shows each session
  whole, whatever the filter holds, so a click there can name a scenario the
  dropdown can't show.
- **The rule is already ratified for three ways in.** The R7 entry says in
  its own words: "The same rule covers the other ways in. The scenario's
  name on the latest-run card follows it, and so will a click in the All
  scenarios view, a later proposal." A1 doesn't choose a rule. It confirms
  the tree as the fourth way in.
- **Any other answer makes the page contradict itself.** With the filter
  kept, the dropdown would hold a scenario its list lacks, and this app's
  dropdown then goes on showing the previous name over the new scenario's
  chart ([2026-10-12][clear-filter]).

What it costs is R7's cost. Clearing the filter takes away the rank lines
and the **Open scenario table** link, the cleared filter is what the browser
then remembers, and no toast says so. One click on a scenario outside a
playlist means picking the playlist again. The tree makes that easier to do
without meaning to than Follow does: a click while reading an old session is
enough. How often a session's scenarios fall outside the filtered playlist
was not measured.

**If the maintainer chooses differently:** the tree becomes the one
exception to R7, and R7's decision-log entry, which says a click in this
view will follow the rule, has to be amended. The exception takes one of two
forms.

- **The click keeps the filter and does nothing for such a scenario.** Some
  names in the tree are then dead, and nothing tells which before a click.
  Drawing those names as plain text would need the tree to be rebuilt
  whenever the filter changes.
- **The click selects the scenario and keeps the filter.** The dropdown then
  names a scenario its own list lacks, which R7 rules out for every other
  way in.

### A2. A session's run count links into the tree, and a session row there has Show all runs

Status: Open. No words of the maintainer's are on record for either half
beyond the design they leaned to on 2026-10-07. The design note of that day
records the count's wording, "7 of 47 runs", as the author's, "not objected
to", and the link as a lean: "that text is a link that jumps to the whole
session under All scenarios". **Show all runs** is on record as one line of
the same note, "A session row has **Show all runs**", and in the mockup. On
2026-10-13 the maintainer agreed what it opens (reading 2 above).

The material consequence: under This scenario every session row gains a
second click target. Following it changes the list's view, and the browser
remembers the view it leaves the list on.

**Recommendation, in two halves that can be taken apart:**

- **Under This scenario, the count on a session row, such as `7 of 47 runs`,
  is a link. Following it switches the list to All scenarios, opens that
  session there with the selected scenario's runs showing, and scrolls to
  it.**
- **Under All scenarios, an open session row carries Show all runs. It opens
  every scenario row of that session down to its runs, and reads Hide all
  runs once they are all open.**

For the link:

- **The count raises the question the tree answers.** `7 of 47 runs` says 40
  runs went somewhere else. The divider under it says `10 runs on 3 other
  scenarios` and names none of them.
- **For a session that isn't recent, the switch alone doesn't get there.**
  All scenarios lists every session, and loads 30 at a time. On the
  maintainer's history the most-played scenario's newest session is the 46th
  session back, and the 30th session This scenario lists for it is the 234th
  of 325 ([Verified facts](#verified-facts)). Without the link, reaching
  that session means remembering its date, pressing the switch, and pressing
  **Show older sessions** seven times.
- **It was built in the trial.** A click on the count did not toggle the
  row, and the row still toggled everywhere else.

Its costs:

- **A deep jump loads many sessions.** The tree has to hold every session
  from the newest to the one asked for. Reaching that 234th session is 9,374
  rows ([Sessions loaded](#sessions-loaded)).
- **A link moves a remembered control.** After a jump, a reload opens on All
  scenarios.
- **Focus has to be placed.** On the prototype NVDA said nothing after the
  jump, and keyboard focus fell to the page body. [The jump](#the-jump) says
  where focus goes, and the walk checks it.

For **Show all runs**:

- **A session opened in the tree shows its scenario rows closed.** That is
  its outline: 5 rows in the maintainer's median session, 21 in one session
  in ten, and up to 71. Reading the session's runs is then a click per row.
  **Show all runs** is one click.
- **Expand all doesn't do it, on purpose** (reading 2). Every run of 30
  sessions is about a thousand rows at once.

**If the maintainer chooses differently:** without the link the count stays
plain text, the tree is reached by the switch alone, and an old session is
reached by loading every session newer than it by hand. Without **Show all
runs** each scenario row is opened by hand. Neither half needs the other.

### A3. The Columns menu gains Median and best, off to start

Status: Open. The design note of 2026-10-07 records the lean: "Median and
best are off to start, to avoid overload." On 2026-10-13 the maintainer was
asked whether this row belongs here or with the typical score's own
proposal, and answered: "okay let's keep it in." That is a lean on scope.
The reading they accepted with it was the kickoff author's and not theirs:
the figure is a plain fact about the runs under one row, with no comparison,
and it is never worded as typical or usual.

The material consequence: a median is on screen before the typical run has a
definition, and the Columns menu, which three pages share, gains a checkbox
that is not a column.

**Recommendation: the Columns menu on Run History gains a Median and best
checkbox, unchecked to start and remembered like its other two. With it on,
a row that stands for runs of one scenario gives the median score and the
best score of the runs under it.**

- **Which rows.** A scenario row under All scenarios covers that visit's
  runs. A session row under This scenario covers the selected scenario's
  runs in that session. A session row under All scenarios shows neither: it
  mixes scenarios, and their scores don't share a scale.
- **A closed row hides its scores.** The tree's outline of a session shows
  run counts and stars. With the figures on, it also shows how each visit
  went without opening it.
- **Off to start,** so the list looks as it does until someone asks for
  more.

**Why this isn't the mistake R5 avoided.** The chart's entry gives this
reason for drawing no summary line: "A new summary line would be a second
definition of the typical run." A reviewer will ask why a median in the list
is different. Three things make it so.

- **What it covers.** Exactly the runs listed under the row it sits on. It
  has no window in time, no minimum number of runs, and leaves no run out.
  Opening the row shows every score that went into it.
- **It compares nothing.** No run is judged against it, no percentage is
  taken of it, no mark depends on it, and it colors nothing. The typical run
  is a figure to judge by, and a line on the chart would have been read
  against every point.
- **What its label must never say.** It says `Median` and `Best`. It never
  says typical, usual, average, or normal, on screen, in the glossary, or in
  the user guide. The glossary entry in [Terms](#terms) says in so many
  words that it is not the typical run.

**Where the evidence is against it.**

- **The trend verdict is planned on the same arithmetic.** The roadmap's
  Future list describes it as "built on session medians, the middle of a
  scenario's runs in each session". Under This scenario, A3's figure on a
  session row is that quantity with no rule added. If the later proposal
  gives its session median a rule this one lacks, such as leaving warm-up
  runs out or asking for a minimum number of runs, the page would hold two
  session medians. The list's would then follow that rule, be relabelled, or
  go. That is R5's risk in a smaller form, and A3 accepts it.
- **Many rows hold too few runs for a median to mean much.** Of the 159
  scenario rows in the maintainer's newest 30 sessions, 15 hold one run and
  17 hold two. The median of two runs is their mean, a score no run had. The
  design words a single run's figure as `Score`, and the run count always
  sits beside the figures.
- **"Be honest about uncertainty" is a principle.** It binds judgments of
  skill. This figure describes the listed runs and judges nothing. That is
  the author's reading of the principle, for a reviewer to test.

What being wrong costs: one checkbox that is off unless turned on, and
nothing stored but its remembered state. Relabelling it or taking it out
later is a small change.

**If the maintainer chooses differently:** A3 moves to the typical score's
proposal. The menu keeps its two checkboxes, the shared menu module and the
two playlist pages are not touched, the walk has one task fewer, and a
closed row shows counts and stars alone. Nothing in A1, A2, or the view
depends on A3.

## Problem

### What the list shows today

The app is a Dash web app that watches the KovaaK's stats folder and plots
scenario scores. Its Run History page shows one scenario at a time: a chart
of that scenario's runs, a card for the last run played, and a list of the
scenario's runs grouped by session
([run_history.md](../specs/run_history.md#the-run-list)).

A session is the runs separated by breaks of no more than 30 minutes. A
visit is the consecutive runs on one scenario within a session
([sessions.md](../specs/sessions.md#visits)).

- **The list has two levels:** sessions, newest first, and under each the
  selected scenario's runs in that session.
- **A session row counts what it leaves out.** Its right side reads how many
  of the session's runs were on this scenario, such as `7 of 47 runs`, as
  plain text.
- **A divider counts a gap.** Where the scenario was left and returned to,
  the list says `10 runs on 3 other scenarios`.
- **The card names another scenario's run,** and its scenario button selects
  that scenario.

### What it can't answer

- **Which scenarios a session held, and in what order.** The count and the
  divider say how many runs went elsewhere and never where. Finding out
  means selecting scenarios one at a time, and nothing on the page says
  which ones to try.
- **How the session is going across scenarios.** The product record names
  the question, "how is this session going?", and says where the page stops:
  "Run History's list answers it for the scenario on screen, and not yet for
  the session across scenarios"
  ([product.md](../product.md#when-they-ask-them)).
- **What just happened, with Follow off.** A run on another scenario changes
  the card and the first row's count. Its own row is not in the list.
- **Whether a session was one scenario or twenty.** In the maintainer's
  history a session's median is 22 runs on 5 scenarios. One session in ten
  holds 62 runs or more, and one in ten holds 20 scenarios or more. 72 of
  325 sessions are one scenario from start to end.

The same passage of the product record leaves one choice to this work:
"Whether the live and the finished session are one view or two is a design
choice for the feature that builds them." This proposal answers one view.
The tree shows the session in progress and every finished session the same
way.

### Why now

- **The page proposal left this view to a proposal of its own.** Its entry
  says: "A view of the session across every scenario, and the switch between
  the two, belong to a later proposal, All scenarios"
  ([2026-10-12][second-column]).
- **It waited for one thing, the list's library.** Row R4 settled it, and
  the list is built and public. The view specified here is added to that
  list, not to a prototype.
- **It is the roadmap's next piece.** "All scenarios is what the session
  review still lacks: the page shows one scenario's runs in a session, and
  not yet the session across scenarios."

### Verified facts

Read at `2c5c072`, `main` on 2026-10-13, unless a line says otherwise.

**Nothing in the code anticipates this view.** There is no reserved id, no
spare parameter, and no TODO. `Show all runs`, `Median and best`, and `All
scenarios` appear nowhere under `source/`, `assets/`, or `tests/`.

The row model, `source/components/run_history_list.py`:

- **`build_run_list` is the pure function that turns runs into rows.** It
  takes every run on every scenario, the selected scenario, a session limit,
  the time, and the marks of the selected scenario's runs.
- **Six kinds of row exist,** and none is a second level. Every row carries
  `sid`, its session row's id.
- **The count is plain text.** It is written to the session row's `counts`
  field, and the script draws that field with no handler of its own.
- **`_session_child_rows` already splits a session into visits,** to place
  the dividers.
- **`SESSIONS_PER_LOAD` is 30.**

The grid's script, `assets/runHistoryList.js`:

- **Which rows are open is a set of session ids kept in the browser.** The
  grid's filter always shows a session row and the row that loads older
  sessions, and shows any other row only while its `sid` is in that set. So
  opening is one level deep.
- **The script holds no copy.** Its strings arrive with the rows or in the
  grid's `context`, and a test fails if one appears in it.
- **Its header comment lists nine pieces of grid-specific work,** each a
  place an AG Grid upgrade can break.
- **It already writes a store from the browser.** **Show older sessions**
  sets the session-limit store, which is an input of the list's server
  callback.

Marks, `source/components/run_marks.py`:

- **`mark_runs` judges one scenario's whole history in play order.** The
  list calls it once, for the selected scenario.

The Columns menu, `source/components/columns_menu.py`:

- **Each checkbox's id names a grid column,** and one clientside callback
  hands those ids to the grid to show or hide. A checkbox that is not a
  column has no path through it.
- **Each checkbox is remembered under its own id.** Both playlist pages host
  the same menu.

The page, `source/pages/run_history.py`, and the selection callback,
`source/components/scenario_selection.py`:

- **`build_run_list_rows` is the one server callback that rebuilds the
  list.** It has six inputs and no state. Nothing on the server hears which
  rows are open, and a test holds that.
- **`reach_scenario_or_the_one_asked_for` is the only callback that writes
  either dropdown,** with plain outputs. Three things can ask it for a
  scenario: a link's parameters, a followed run, and the card's button.
  Which one called is read from what triggered the call, never from the
  values.
- **The card's button is always in the layout.** A page has to hold every
  input of a callback whose output it holds.
- **Every remembered control uses Dash `persistence` with its default,**
  under an id that starts `run-history-`. The chart mode,
  `run-history-chart-mode`, is a segmented control.

Measured on 2026-10-13 on the maintainer's stats folder, by scripts that
call the app's own functions and read the folder only: 9,135 runs on 866
scenarios, in 325 sessions.

| | Newest 30 sessions | Newest 60 | Every session |
|---|---|---|---|
| Runs | 831 | 1,373 | 9,135 |
| Visits | 159 | 296 | 2,921 |
| Scenarios | 36 | 104 | 866 |
| Rows in a tree: sessions, visits, and runs | 1,020 | 1,729 | 12,381 |
| Sessions that hold a return to a scenario | 5 | 11 | 66 |
| Marking every run of those scenarios, first time | 67 ms | | |
| The same, once their performance files are read | 3.6 ms | 11 ms | 32 ms |

- **Marking is cheap after the first time.** The first pass reads each
  scenario's performance files, and the app keeps their answers for the life
  of the process. Only the first column was timed with none read.
- **The newest 30 sessions span three weeks,** 2026-09-18 to 2026-10-09.
- **A session:** a median of 22 runs, 5 visits, and 5 scenarios. The 90th
  percentile is 62 runs, 21 visits, and 20 scenarios, each counted on its
  own. The largest are 118 runs, 71 visits, and 61 scenarios.
- **How deep a count's link can go.** The most-played scenario has 463 runs
  in 33 sessions. Its newest session is the 46th of 325, counting back from
  the newest, and the 30th session This scenario lists for it is the 234th.
  A tree that reaches the 234th holds 9,374 rows.
- **Scenario names.** The 36 names in the newest 30 sessions have a median
  length of about 20 characters. The longest has 46, and 9 are longer than
  27.
- **Returns are real and easy to miss.** 66 of 325 sessions hold a scenario
  that was left and returned to. None of the six newest sessions in the
  mockup's data does, so the maintainer may never have seen one drawn.

From earlier work, for comparison:

- **The built list's model is 163 KB for 481 rows,** and a run that lands
  reaches the screen in 106 to 182 ms in Edge ([2026-10-12][grid]).
- **The trial built both views on this grid on 2026-10-10,** against `main`
  at `4272fbb`, before the list was written afresh. With every session
  loaded, 12,129 rows, its grid painted in 234 ms in Edge and 387 ms in
  Firefox, and a run landing took 149 ms and 130 ms. It kept about 39 row
  elements in the page whatever was open.
- **NVDA was run on that prototype's tree on 2026-10-11.** A scenario row
  was read with its text, and with no state and no depth.

### Not checked

- **Nothing here was built.** Every behavior in Design is specified, and
  none was tried on the list as built.
- **The time and the size of the tree in the built list.** The built list's
  rows are about twice the size of the trial's, so the figures above are a
  guide and not a measurement. The implementing PR measures both.
- **Whether a value written to a remembered control from a script is
  remembered.** The design does not depend on it: it writes the switch from
  a server callback, whose writes are known to be remembered
  ([2026-09-19][query]).
- **Every width in a 500 px column.** The header's fit, the widest session
  row, and the room a scenario's name has are arithmetic.
- **Row heights that change with a checkbox,** on full-width rows with a
  pinned row.
- **NVDA on three levels as built.** The prototype pass is the only
  evidence.
- **Touch,** Narrator, and JAWS.

## Design

Every choice in this section is author-owned unless it names a row. A choice
the maintainer agreed to on 2026-10-13 says so, and is a lean. The mockup's
strings were placeholders, and none is agreed copy: the strings are in
[Copy](#copy).

### The view at a glance

The run list as a player meets it under All scenarios. The page around it is
unchanged: the top row, the latest-run card, and the chart.

```
┌─ the run list, under All scenarios ────────────────────────────────┐
│ All scenarios · 9,135 runs                                         │
│ [This scenario | All scenarios]          [Expand all] [Columns ▾]  │
│   #   Time       Score        Accuracy  Shots Fired  Sensitivity   │
│ ▼ Oct 4, 9:45 PM  In progress                                      │
│            1 hr 6 min · 47 runs · 7 scenarios      Show all runs   │
│ ┃ ▼ 8. Leapstrafes Control wobin                        2 runs ★   │
│ ┃   7   10:50 PM   3,324  ✓      55%     6,001   45.0 cm/360       │
│ ┃   6   10:49 PM   3,422  ✓★     57%     6,001   45.0 cm/360       │
│   ▶ 7. 1w6ts reload v2                                  3 runs ★   │
│   ▶ 6. beanTS                                           4 runs     │
│   ▶ 5. StaticSwitchingVox Small                         3 runs     │
│ ┃ ▶ 4. Leapstrafes Control wobin                        5 runs ★   │
│   ▶ 3. VT Controlsphere Viscose                        10 runs     │
│   ▶ 2. Smoothsphere Viscose                            12 runs     │
│   ▶ 1. Whisphere Viscose                                8 runs     │
│ ▶ Oct 2, 11:18 PM                  40 min · 26 runs · 3 scenarios  │
│ ▶ Oct 2, 4:52 PM               1 hr 3 min · 34 runs · 5 scenarios  │
│ [Show older sessions]                                              │
└────────────────────────────────────────────────────────────────────┘
```

- **The session row is one line on screen.** The sketch breaks it in two for
  width.
- **Leapstrafes Control wobin is the selected scenario,** and `┃` stands for
  the band that marks its rows.
- **It was left and returned to,** so it has two rows, 4 and 8. The session
  has 8 scenario rows and 7 scenarios.
- **Run 7 is the last run played,** and its row is highlighted.

The same session under This scenario, which is the list as built with two
changes: the switch, and the count as a link.

```
┌─ the run list, under This scenario ────────────────────────────────┐
│ Leapstrafes Control wobin · 33 runs                                │
│ [This scenario | All scenarios]          [Expand all] [Columns ▾]  │
│   #   Time       Score        Accuracy  Shots Fired  Sensitivity   │
│ ▼ Oct 4, 9:45 PM  In progress         1 hr 6 min · 7 of 47 runs    │
│   7   10:50 PM   3,324  ✓      55%     6,001   45.0 cm/360         │
│   6   10:49 PM   3,422  ✓★     57%     6,001   45.0 cm/360         │
│         10 runs on 3 other scenarios                               │
│   5   10:24 PM   3,417  ✓★     57%     6,001   45.0 cm/360         │
│   ...                                                              │
│ ▶ Oct 2, 11:18 PM                                    6 of 26 runs  │
└────────────────────────────────────────────────────────────────────┘
```

`7 of 47 runs` and `6 of 26 runs` are links (A2). Runs 7 and 6 carry the
same numbers in both views.

### The switch

- **A segmented control with two options, This scenario and All scenarios.**
  It is the control the chart mode uses.
- **It sits on the list's second line, at the left,** with **Expand all**
  and **Columns** at the right. The heading keeps the line of its own that
  the build gave it, because on one line with the buttons it cut a
  scenario's name short. The mockup drew the switch on the heading's line.
- **The list starts on This scenario, and the browser remembers the
  switch.** Agreed on 2026-10-13, as reading 4. The design note of
  2026-10-07 has the same lean: "Remember the switch across a reload, not
  the opened rows", "to revisit after shipping", and "The maintainer accepts
  that the play order is one click away."
- **Why This scenario first.** The page's subject is one scenario. A browser
  that has never seen the switch shows the list every user has today.
- **Pressing it shows the other view from its top.** The first row is the
  newest session in both views. Each view keeps the rows it had open, and
  keyboard focus stays on the switch.
- **Its id and its default are chosen once:** `run-history-list-view`, with
  the values `scenario` and `all`, and `scenario` as the default. A renamed
  id or a changed default resets the stored view in every browser
  ([2026-10-12][own-ids]).

### What the tree lists

All scenarios has three levels: sessions, the scenarios played in each, and
each one's runs.

**Sessions.**

- **Every session is listed, newest first.** Under This scenario only the
  sessions that hold a run of the scenario are.
- **The newest session is the first row,** in progress or not, and stays in
  view under the column headers while the list scrolls. That is the built
  rule, unchanged.
- **A session row reads its name, then three facts:** its length, its runs,
  and its scenarios, as `1 hr 6 min · 47 runs · 7 scenarios`. The name is
  when the session started, and the first row carries the `In progress`
  badge while its session is in progress, both as built.
- **Every session row gives its length here.** Under This scenario only the
  first row does. In the tree a session is the subject, and its length is
  one of the four facts the 2026-10-07 design gave a session: "start (the
  name), length, runs, scenarios". The first row's length keeps its hover.
- **`7 scenarios` counts scenarios, not rows.** A session with a return has
  more scenario rows than scenarios.
- **The Playlist filter doesn't narrow the tree.** It narrows the dropdown.
  The tree is the record of what was played.

**Scenario rows.**

- **A row under a session is a visit:** consecutive runs on one scenario.
  Agreed on 2026-10-13, as reading 1. A scenario that is left and returned
  to within a session gets a second row.
- **Why a visit and not one row per scenario.** The alternative the
  maintainer was given merges a scenario's runs into one row. The order of
  play is what this view adds, and a merged row has no place in it: two
  blocks of runs, an hour apart, would sit together under one number. The
  divider under This scenario already treats a return as worth marking.
- **The word visit stays off the screen.** A scenario row is named by its
  scenario and numbered by its place in the session. Putting the word on
  screen would teach a term for something the numbers already show. The
  [Terms](#terms) block says how the glossary's entry changes.
- **Rows are numbered in the order they were played and listed newest
  first,** as runs are. The newest row is at the top with the highest
  number.
- **A scenario row reads `{number}. {scenario}`, then its run count,** as
  `8. Leapstrafes Control wobin` and `2 runs`. A star follows the count
  where a new PB was set in that visit. The 2026-10-07 note: "A star stays
  on a scenario row where a PB was set."
- **The name is a button, drawn as the app draws a link.** It selects the
  scenario (A1). A click anywhere else on the row opens or closes it.
- **A name too long for the row is cut short with an ellipsis,** and its
  hover gives the whole name. The count is never cut.

**Run rows.**

- **A run row keeps the seven columns and the marks of the built list,**
  word for word: `#`, Time, Score, the marks, Accuracy, Shots Fired, and
  Sensitivity. The columns stay in line with their headers at every level.
- **`#` is the run's number among that scenario's runs in the session,** in
  the order they were played. It does not restart in a second visit: the
  sketch's row 8 holds runs 6 and 7.
- **Why.** One run then has one number everywhere: in both views, and on the
  latest-run card, whose third line reads `Run 7 this session` and counts
  the same way. Numbers that restart would call the same run 2 in the tree
  and 7 under This scenario.
- **Every scenario's runs are marked.** A check and a star mean what they
  mean today ([Marks](../specs/run_history.md#marks-the-check-and-the-star)),
  and the Score threshold percentage as it is set now judges every run in
  the tree.
- **There are no dividers.** A divider says a scenario was left and returned
  to. In the tree the rows between say it.

**Date headers.**

The built list's rule is written for one scenario's runs in a session. The
tree's rule is the same rule, asked of one scenario row at a time.

- **Under a scenario row, a date header names the date of the runs beneath
  it wherever one of that row's runs is not on the date its session
  started.** Each date among the row's runs then gets a header, the
  session's start date included.
- **A row whose runs are all on the session's start date has no header.**
  The session's name already gives that date.
- **A row played wholly after midnight has one header,** above its runs. So
  does a single run that started before midnight and ended after it. A run's
  date is the date it ended on, as built.
- **A closed scenario row shows no date.** The session row gives the start
  and the length, which is enough to tell a session crossed midnight.
- **Headers between scenario rows were set aside.** A visit can span
  midnight, and a header between two rows could then be true of only part of
  the row above it.

### What the tree marks

- **The selected scenario's rows carry a band down their left edge:** each
  of its scenario rows, in every listed session, and the run rows under
  them. With no scenario selected, or with one that has no run in the listed
  sessions, nothing is marked.
- **The tree never goes looking for the selected scenario.** It doesn't
  scroll to it or load older sessions to reach it. That is what This
  scenario is for.
- **The name's button says it is current.** On the selected scenario's rows
  it carries `aria-current`, which is how a screen reader hears what the
  band shows.
- **The row of the last run played keeps its highlight.** Under This
  scenario that row is in the list only while its scenario is selected.
  Under All scenarios it is always in the first session, and it shows once
  its session row and its scenario row are open. A row can carry both the
  band and the highlight.

### Opening and closing

- **A session row and a scenario row each open and close on a click,** with
  no request to the server, as session rows do today.
- **On arrival the first session is open, and so is the scenario row of the
  last run played.** Every other row is closed. That is the built rule, one
  level deeper: the newest run opens the rows above it, once per run.
- **Each view keeps its own open rows.** Opening a session in the tree
  doesn't open it under This scenario. Neither set is remembered across a
  reload or a new visit to the page, as today.
- **A scenario row keeps its state while its session is closed.** Closing a
  session and opening it again shows the same scenario rows open.
- **Expand all opens every loaded session down to its scenario rows,** and
  reads **Collapse all** once every loaded session is open. Agreed on
  2026-10-13, as reading 2. It opens no runs. **Collapse all** closes every
  session and leaves the scenario rows' own state alone.
- **Show all runs** is on an open session row, at the end of its facts. It
  opens every scenario row of that session, and reads **Hide all runs** once
  they are all open. **Hide all runs** closes them and leaves the session
  open. Agreed on 2026-10-13, as reading 2.
- **Both buttons read what a press would do,** so each follows every way a
  row can open or close, and not only its own presses. That is the built
  rule for **Expand all**, which reads for the view on screen.
- **Nothing opens every run of every session at once.** At 30 sessions that
  is about a thousand rows, and the tree is for reading one session.
- **A closed session row has no Show all runs.** Thirty closed rows would
  each carry a link, and the widest row would be every row.

### Selecting a scenario from the tree

What follows from A1.

- **A click on a scenario's name selects that scenario for the whole page:**
  the dropdown, the chart, Scenario Stats, and the band in the tree. A
  Playlist filter that does not list it is cleared in the same step (A1).
- **The view stays on All scenarios.** Agreed on 2026-10-13, as reading 3.
  The click asks to see that scenario on the chart. It doesn't ask to stop
  reading the session.
- **The row doesn't open or close,** and the list doesn't scroll.
- **A press on the selected scenario's own name changes nothing.**
- **From the keyboard, focus stays on the name's button,** and the list says
  `Selected scenario: {scenario}` through its live region. Nothing else
  would tell a screen reader that the press did anything: the chart is not
  near focus.

**How the click reaches the selection callback.** The page has one callback
that writes either dropdown, and R7's mechanism depends on that
([2026-10-12][clear-filter]). The tree's rows are drawn by a script and are
not Dash components, so a click in them can't be an input the way the card's
button is.

- **The script names the scenario in a store that is always in the layout.**
  The store is one of the list's own, beside the one that counts loaded
  sessions, which the script already writes from the browser.
- **The selection callback takes that store as a fourth input.** It stays
  the only writer of both dropdowns, with plain outputs, so the scenario
  list and the chart still wait for it.
- **Which of the four called is still read from what triggered the call.**
  The new store replays its last value into every later call, as the summary
  store does. Read from the values, a run landing after a click would select
  the clicked scenario again.
- **No input is ever missing.** The store is in the layout from the start,
  with no value until a name is pressed.

A scenario in the tree always has local runs, so R7's test for them always
passes.

### The jump

What follows from A2's first half.

- **Under This scenario, the count on every session row is a button, drawn
  as the app draws a link.** Its text is unchanged. A click on it does not
  open or close the row.
- **Following it switches the list to All scenarios.** The switch moves with
  it, and the browser remembers the view as if the switch had been pressed.
  One rule covers both: the view on screen is the view a reload shows. The
  other rule, that a jump is a look and a reload returns to This scenario,
  would make the switch show a view the browser did not keep.
- **It opens that session, and every scenario row of the selected scenario
  in it.** The runs the player was just reading are then in view, among the
  session's other scenario rows, which stay closed. Rows already open in the
  tree stay open.
- **It scrolls the session's row to the top of the list,** just under the
  first row. Where the session is the first row, the list scrolls to its
  top.
- **Keyboard focus goes to that session's row.** The button that was pressed
  is gone, because a session row's right side differs between the views, and
  focus would otherwise fall to the page. A screen reader then reads the row
  it arrived on, whose facts have changed from `7 of 47 runs` to the
  session's three.
- **The count is a link on the first row too,** including `0 of 47 runs`.
  That jump opens the session and nothing under it, which answers what was
  played instead.
- **If the tree that arrives doesn't hold the session,** it shows from its
  top. A run that lands late can give a session a new first run, and with it
  a new id.

**How it is built.**

- **The script names the session in a store that is always in the layout,**
  as it names a scenario for A1.
- **One server callback answers,** and writes the switch's value and the
  number of sessions All scenarios loads. Both are plain outputs, and the
  list's callback takes both as inputs, so it waits and builds the tree
  once, already reaching the session.
- **A value a callback writes to a remembered control is remembered**
  ([2026-09-19][query]). That is why the jump goes through the server and
  not straight from the script to the switch.
- **The script keeps what to open and where to scroll.** It applies them
  when the tree arrives. The server is told how far back to load, and still
  never hears which rows are open.

### Sessions loaded

- **Each view loads 30 sessions and counts its own.** Under This scenario
  they are the 30 newest sessions that hold the scenario. Under All
  scenarios they are the 30 newest sessions.
- **Show older sessions adds 30 to the view it is pressed in.** Neither
  count is remembered: a reload starts both from 30, and a change of
  scenario keeps both, as today.
- **30 reaches less far back in the tree.** On the maintainer's history it
  is three weeks of play and 1,020 rows. Under This scenario the same 30
  reach back more than a year for the most-played scenario.
- **Why not fewer.** One number serves both views, and three weeks is a
  useful first page of sessions.
- **A jump loads as far back as the session it was asked for.** If All
  scenarios has loaded fewer sessions than that, its count becomes the
  session's place among all sessions, counting back from the newest. The
  session is then the last one listed, directly above **Show older
  sessions**.
- **That can be most of the history.** Reaching the 234th session is 9,374
  rows, and the tree stays that size until the page is loaded again. Every
  run that lands meanwhile sends the whole tree again.
- **Why that is acceptable.** The grid draws only the rows in view, which is
  what R4 counted for it. The trial's grid held 12,129 rows and showed a
  landed run in 149 ms. The implementing PR measures the built list at 30
  sessions and at every session, and [Fallbacks](#fallbacks) says what
  happens if the larger figure is too slow.

### A run that lands

- **The list is rebuilt from the run store, in either view,** on the
  triggers it has today and on a change of view.
- **Under All scenarios the run's row always shows.** It opens its session
  row and its scenario row, once per run, as the first row opens today. So a
  row the player closed is not reopened by a later change of scenario or of
  view.
- **Every run in a batch opens its rows, not only the newest.** The app
  shell hands the page new runs in batches, one per poll, and a batch can
  hold runs on two scenarios. The model names only the store's newest run,
  as today. So the script opens the session row and the scenario row of
  every run newer than the one it applied last, which it finds by walking
  the tree's run rows from the top down to that run. Where it can't find
  that run, as on arrival, it opens the newest run's rows alone. Which rows
  are open still never reaches the server.
- **A run opens its rows in both views, whichever is on screen.** A run that
  lands under This scenario has its scenario row open in the tree when the
  switch is next pressed.
- **A run on a new scenario adds a scenario row** at the top of the session,
  with the next number. The row before it stays as it was.
- **Opened scenario rows pile up over a long session.** Each visit opens
  when its first run lands, and nothing closes it. The 2026-10-07 note:
  "Deferred until it proves a burden." It is in
  [Out of scope](#out-of-scope).
- **With Follow on,** the page selects the scenario just played, the band
  moves to its rows, and the list scrolls back to the top. That is today's
  rule.
- **With Follow off,** the selection stays and so does the band. The run
  still shows in the tree, highlighted as the last run played. Under This
  scenario it shows only as the first row's count, as today.
- **Keyboard focus stays on the same run,** by its row's id, as built.
- **A scenario row is keyed by its first run,** as a session row is. A run
  that lands older than the store's newest can split a visit or join two.
  Such a row gets a new id and comes back closed.

### Median and best

What follows from A3.

- **With the checkbox on, a row with figures gains a second line under its
  first,** which reads `Median 3,373 · Best 3,422`.

  ```
  │ ┃ ▼ 8. Leapstrafes Control wobin                        2 runs ★   │
  │ ┃                                    Median 3,373 · Best 3,422     │
  │   ▶ 7. 1w6ts reload v2                                  3 runs ★   │
  │                                          Median 119 · Best 121     │
  ```

- **Why a second line and not the row's own.** The mockup and the trial drew
  the figures inline, as `6 runs · median 119 · best 121`. By arithmetic, in
  a 500 px column that leaves a scenario's name about 27 characters, and 9
  of the 36 names in the maintainer's newest 30 sessions are longer. Under
  This scenario the first row is the tightest: with its name, its badge, its
  length, and its count on it, two more figures run past 500 px by the same
  arithmetic. A second line fits every name and every score, at the cost of
  height.
- **The median is the middle score of the runs under the row,** or the mean
  of the two middle scores when their number is even. **The best is the
  highest.** Both count every run under the row, at any sensitivity.
- **Both are formatted as a score is** in the list: thousands separators, at
  most two decimals, and trailing zeros dropped.
- **A row that holds one run reads `Score 3,324`.** A median of one run is
  that run. The line still earns its place: the row is usually closed, and
  the figure is what the checkbox was turned on to see.
- **A row with no run has no second line.** That is the first row under This
  scenario where the scenario wasn't played, `0 of 47 runs`.
- **A time-scored scenario needs no special case.** The spec says anything
  that orders or places scores is unchanged there, "because a higher score
  is always a faster finish"
  ([Time-scored scenarios](../specs/run_history.md#time-scored-scenarios)).
  A median and a best order scores.
- **The figures show whether the row is open or closed,** so a row's height
  depends on the checkbox and never on a click.
- **The server always sends the figures.** The checkbox is the browser's
  alone, as each column's is, so turning it on makes no request.

**The menu.** The shared Columns menu applies a checkbox by showing or
hiding a grid column, and **Median and best** is not a column.

- **The menu gains an optional list of choices that are not columns.** Each
  is one remembered checkbox, drawn after the columns' checkboxes, with an
  id of another shape, so the callback that shows and hides columns never
  sees it.
- **The list gives its script the checkbox's value** through a small
  clientside callback of its own.
- **The two playlist pages pass no such choice** and are unchanged. Their
  tests hold that.
- **The checkbox is unchecked to start,** and its id is chosen once.

The trial used a look-alike of the menu and drew the choice first. It goes
last here: the menu is named for columns, and the columns come first.

### Empty states

- **With no run in the store, the list reads `No runs yet` in either view,**
  with no controls, as today.
- **With runs and no scenario selected, This scenario reads `No scenario
  selected` with the switch still above it.** Today that text takes the
  place of the list's whole header. The switch has to stay: the tree needs
  no selection, and without the switch a player could not reach it.
  **Expand all** and **Columns** have nothing to act on there and stay out
  of view.
- **All scenarios needs no selected scenario.** With none it lists every
  session and marks nothing.
- **A selected scenario with no local runs** lists the newest session alone
  under This scenario, as today. Under All scenarios it changes nothing.

### Keyboard and screen reader

**Keys.**

- **A scenario row takes the four keys a session row takes:** Enter and
  Space open or close it, Right opens it, and Left closes it.
- **Tab from a group row walks its buttons.** A scenario row has its toggle,
  then its name. A session row under This scenario has its toggle, then its
  count. An open session row under All scenarios has its toggle, then **Show
  all runs**.
- **The switch is a radio group,** as the chart mode is.

**What a screen reader is told.**

- **A scenario row's toggle is named `Scenario`,** as a session row's is
  named `Session`. Each group row then begins with what kind of row it is.
- **A key that opens or closes a scenario row says `Expanded` or
  `Collapsed`** through the list's live region, as a session row's does.
  **Show all runs** and **Hide all runs** say the same two words, as
  **Expand all** does: a button's changed name is not reported in Chrome and
  Edge.
- **A name's button is named `Show {scenario}`,** as the card's is, and
  pressing it says `Selected scenario: {scenario}`.
- **The count's button keeps its text as its name,** and its hover, `Show
  the whole session`, is its description.
- **The grid's name follows the view.**

**A row's depth is never said.** The NVDA record lists it first among what
still does not work, with no fix known in the grid's free edition
([run_history_list_nvda_walk.md](../research/run_history_list_nvda_walk.md#what-still-does-not-work)).
The grid's root has the role `grid`, and a row's level belongs to a
`treegrid`, which AG Grid sets only through its paid features. Two levels
are told apart by their words today. The tree does the same for three, and a
third makes it harder.

- **Each kind of row begins differently.** A session row reads `Session`,
  then a date. A scenario row reads `Scenario`, then a number and a name. A
  run row is read a cell at a time, each with its column heading.
- **A scenario row's number says where it sits in its session.**
- **A run row still doesn't say which scenario it is under.** That is heard
  by moving up to the scenario row, and the session by moving up again. It
  is further than it is today.
- **Nothing more is proposed.** Two things that might help are in
  [Optional, beyond the outline](#optional-beyond-the-outline), and neither
  was tried.

**The walk is owed, under R4's rule.** The proposal changes what a screen
reader hears of a row, which key does what, and where focus goes. NVDA is
run on the built list in Firefox, Chrome, and Edge before the change merges,
and what it says is recorded in the research note beside the first record.
The walk repeats R4's five tasks under This scenario, because a session row
there gains a button. Then it takes the tree's tasks:

1. Switching the list to All scenarios and back, and hearing which view it
   is in.
2. Telling a session row, a scenario row, and a run row apart, and hearing
   whether a scenario row is open.
3. Hearing which scenario and which session a run belongs to.
4. Selecting a scenario from its row, and hearing that it was selected, with
   focus still on that row.
5. Following a session's count under This scenario, and arriving on that
   session in the tree.
6. Opening one session's runs with **Show all runs**, and hearing that they
   opened.
7. Staying on the same run when a new run lands and adds a scenario row
   above it.
8. With **Median and best** on, hearing a row's two figures.

A failed task is the maintainer's to decide, as R4 has it. The app's
accessibility work is best effort. The maintainer, 2026-10-12: "The app has
never promised screen-reader usability".

### Narrow windows and the 500 px column

- **The page's two narrow-window rules are unchanged**
  ([Narrow windows](../specs/run_history.md#narrow-windows)). The list still
  goes above the chart at 900 px of page, and still scrolls sideways at
  phone width.
- **The list's second line wraps on the list's own width.** At 500 px the
  switch and the two buttons should fit on one line, by arithmetic. Where
  they don't, the buttons go under the switch.
- **A session row's facts are never cut short.** The widest row is the first
  one while its session is in progress and open: its name, the badge, three
  facts, and **Show all runs**. The mockup drew that row in 500 px. The
  implementing PR measures it at the built sizes, and says in its
  description what gives if it does not fit.
- **A scenario's name gives before its count does.**
- **The two figures of A3 take a line of their own,** so they fit at any
  width the list has.

### How it is built

- **One Python function still builds the rows,** for either view. Under All
  scenarios it returns session rows, scenario rows, run rows, and date
  headers. A run row carries its scenario row's id beside its session
  row's.
- **The model names the newest run and the rows it opens,** as today. Under
  All scenarios those are its session row and its scenario row. The script
  opens the rows of any other run in the same batch itself
  ([A run that lands](#a-run-that-lands)).
- **The tree marks one scenario at a time,** by the function that marks the
  selected scenario today. For the newest 30 sessions that is 36 scenarios
  and 1,147 runs, and took 3.6 ms once the performance files were read, and
  67 ms the first time. With every session loaded it took 32 ms.
- **The list's callback gains the view as an input,** and the number of
  sessions All scenarios loads.
- **The model is larger.** At the built list's size per row, 1,020 rows are
  about 350 KB, where the built list sends 163 KB for its largest scenario.
  It is sent again when a run lands and when the selected scenario changes.
  The implementing PR measures both.

Of the script's nine pieces of grid-specific work, four change:

- **Item 1.** A scenario row is a second kind of full-width group row, with
  the `gridcell` role and the span the session row's has.
- **Item 2.** The filter gains a second test. A row under a scenario row
  shows only while its session row and its scenario row are both open. Every
  loaded row is still always in the grid.
- **Item 5.** A scenario row takes the session row's four keys.
- **Item 9.** Focus goes back to the same button in the row, and not only
  to the same row. Today it goes to the row's first button, which in a
  scenario row is the toggle. A press on the scenario's name rebuilds the
  tree, so focus would land on the toggle and not stay on the name.

Two things are new: a row's height follows the **Median and best**
checkbox, so the grid measures its rows again when it changes, and the
script keeps one set of open rows for each view.

**The script still holds no copy.** Every string in [Copy](#copy) reaches it
with the rows or in the grid's `context`.

### Remembered controls

| Control | Remembered | Default |
|---|---|---|
| The switch, `run-history-list-view` | Yes | This scenario |
| The **Median and best** checkbox (A3) | Yes | Unchecked |
| Which rows are open, in either view | No | The first session, and under All scenarios the last run's scenario row |
| How many sessions each view has loaded | No | 30 |

Both remembered controls use Dash `persistence` with its default, as every
remembered control on the page does. Each layout default is a constant.

### Copy

Every string the view adds or changes. They follow the nine copy rules in
[AGENTS.md](../../AGENTS.md#styling-conventions). A string the list has
today and this proposal does not name is unchanged.

| Where | String | Why |
|---|---|---|
| The switch, two options | `This scenario`, `All scenarios` | Sentence case, as controls. "This scenario" is the one the page has selected, and "All scenarios" is the mockup's label and the roadmap's name for the view. |
| The switch, accessible name | `Run list view` | Plain, beside `Chart mode` and `Range`. |
| Heading line, This scenario | `{scenario} · {n} runs` | Unchanged. |
| Heading line, All scenarios | `All scenarios · {n} runs`, or `All scenarios · 1 run` | The same shape: what the list covers, then how many runs. `{n}` is every run in the run store, as the other view's is every run of the scenario. The mockup read "All scenarios" alone. |
| A session row's facts, All scenarios | `{length} · {n} runs · {k} scenarios`, such as `1 hr 6 min · 47 runs · 7 scenarios` | The session's length, runs, and scenarios, after its name. Singular where a count is one: `1 run`, `1 scenario`. |
| An open session row, All scenarios | `Show all runs`, `Hide all runs` | One button, reading what a press would do, as `Expand all` and `Collapse all`. |
| A scenario row | `{number}. {scenario}`, such as `8. Leapstrafes Control wobin` | The number is its place in the session. |
| A scenario row's name, accessible name | `Show {scenario}` | The card's button, word for word. |
| A scenario row's count | `{n} runs`, or `1 run` | As the heading counts. |
| A scenario row's star, hover and accessible name | `New PB` | The run's star, word for word. |
| A scenario row's toggle, accessible name | `Scenario` | The kind of row, as `Session` is. The row reads its own name. |
| The count under This scenario | `{n} of {m} runs` | Unchanged text. It becomes a button. |
| The count, hover | `Show the whole session` | Says what a press does. It names no control, so nothing in it is bold. |
| Columns menu, a checkbox (A3) | `Median and best` | Sentence case, as the menu's other labels. |
| A row's second line (A3) | `Median {median} · Best {best}` | Two readout fragments, each led by its label, as the card's `Accuracy 55%` is. Never "typical", "usual", "average", or "normal". |
| The same, a row with one run (A3) | `Score {score}` | A median of one run is the run, so the line says what it is. |
| The grid, accessible name, All scenarios | `Runs of all scenarios, by session` | Beside `Runs of {scenario}, by session`. |
| Live region, a scenario row or a session's runs opened or closed | `Expanded`, `Collapsed` | The list's two words, unchanged. |
| Live region, a scenario's name pressed | `Selected scenario: {scenario}` | A readout, so no period. It leads with the label of the dropdown that now holds the name. |

Kept as today, word for word: `Expand all`, `Collapse all`, `Columns`, the
column headers and `Marks`, `In progress`, the session's name, the first
row's length and its hover, the divider, the date header, `Not played in
this session`, the marks' words and every reason a run is not judged, `Show
older sessions`, `Session`, `No runs yet`, and `No scenario selected`.

### Terms

Each entry is written as [docs/glossary.md](../glossary.md) would hold it,
under "The Run History page". The implementing PR moves them in.

New entries:

- **This scenario.** The run list's view of the selected scenario alone: the
  sessions that hold a run of it, and under each its runs. It is the view
  the list starts on.
- **All scenarios.** The run list's view of each session whole: under a
  session the scenarios played in it, one row for each visit in the order
  they were played, and under each its runs.
  - Not the Playlist filter left empty, which is about the scenario
    dropdown.
- **Median and best.** Two figures the run list can show on a row that
  stands for several runs of one scenario: the middle score and the highest
  score of the runs under that row. They count every run under the row and
  compare nothing.
  - Not the typical run, which is what a player's recent runs usually score.
    A later proposal defines that.
  - Only if A3 is taken.

Entries the same PR corrects:

- **Visit** ends "Not on screen yet." It becomes: "Not on screen as a word.
  Under All scenarios each visit is a row, named by its scenario and
  numbered by its place in the session."
- **Run History** says the page shows "a list of its runs grouped by
  session". The list has a second view, and the entry gains a sentence
  naming it.

### Decisions this changes

The implementing PR keeps each entry and adds a dated "Superseded in part"
note. It erases nothing.

| Entry | What changes | What stands |
|---|---|---|
| [2026-10-12, the second column][second-column] | "Version 1 has one view". The list's two levels become three in the second view. The count "as plain text" becomes a link. "The first row alone gives a session's length" holds under This scenario only. The Columns menu's two checkboxes become three, if A3 is taken | R3: the list is a second column, 500 px wide. Every rule of the list under This scenario |
| [2026-10-12, the filter][clear-filter] | The click it foresaw arrives, as a fourth way in and the selection callback's fourth input | R7, and one callback as the only writer of both dropdowns |
| [2026-10-12, the grid][grid] | Four of its nine pieces of work change, and the walk it requires is repeated with the tree's tasks | R4, the rule the check leaves, and "A failed task is the maintainer's to decide" |
| [2026-10-12, the page's own ids][own-ids] | What the page remembers gains the switch and, if A3 is taken, one checkbox | The rule that a renamed id or a changed default resets a stored value |
| [2026-10-05, the Columns menu][columns-menu] | "What the menu lists" gains, on Run History alone, a choice that is not a column, if A3 is taken | D1 and D2, one remembered checkbox per choice, and both playlist tables' menus |
| [2026-10-11, sessions][sessions-entry] | Nothing. The word visit is still not on screen | S1 to S4 |
| [2026-10-12, the chart][every-run] | Nothing. The chart still draws no summary line | R5, and its reason, which A3 answers for the list and not for the chart |

Statements of [run_history.md](../specs/run_history.md) that go untrue, for
the implementing PR to rewrite. All but the last two are under "The run
list":

- The list "lists the selected scenario's runs on two levels".
- The heading line reads `{scenario} · {n} runs`, with two controls under
  it.
- A session row's right side, which gains the link.
- "Expand all" and what it opens.
- The Columns menu's two checkboxes.
- "The list loads 30 sessions", which becomes a count for each view.
- What rebuilds the list, which gains the view.
- "A run that lands", which gains the scenario row.
- The row of the last run played "is in the list only while the selected
  scenario is the one that run was on".
- The three empty states.
- The grid's accessible name, the keys, and the live region's words.
- Under "Identity" and "Run delivery": who can ask the selection callback
  for a scenario.
- Under "What the page keeps and forgets": the list of what the browser
  remembers.

[sessions.md](../specs/sessions.md) says the run list "lists a scenario's
runs under the session each was played in". It gains the second view. Its
sentence "The word visit is not on screen" stays true.

### Alternatives rejected

- **One row per scenario in a session, with its runs merged.** The
  alternative to reading 1. It loses the order of play, which is what the
  view adds.
- **All scenarios as the view the list starts on.** The page's subject is
  one scenario, and every user has This scenario today.
- **The count opens the whole session in place, under This scenario.** No
  view changes and no session has to be loaded. But one list would then hold
  sessions at two depths, with two meanings of an open row, and the lean of
  2026-10-07 is a jump into the tree.
- **A jump that shows the session alone, outside the loaded sessions.** It
  loads one session where the recommended design can load hundreds. The
  session would then sit below **Show older sessions**, out of order, and
  the list would need a rule for when it leaves.
- **One count of loaded sessions for both views.** Pressing **Show older
  sessions** three times under This scenario would load 120 whole sessions
  on the next press of the switch.
- **Run numbers that restart in each scenario row.** The same run would have
  two numbers.
- **The figures of A3 on the row's own line,** as the mockup drew them. See
  [Median and best](#median-and-best).
- **A scenario's name as plain text on the selected scenario's rows,** which
  is the card's rule. On the card the button leaves and focus is handed to
  the dropdown. In the tree that would drop keyboard focus in the middle of
  the list at every selection.
- **A date header between scenario rows.** See
  [What the tree lists](#what-the-tree-lists).
- **A page of its own for sessions.** The 2026-10-07 design set it aside,
  and the maintainer said "No navbar entry yet".

### Optional, beyond the outline

None of these is proposed. Each is a small addition a reviewer or the
maintainer may want, with what it would cost.

- **Left on a closed scenario row moves focus to its session row.** It is
  what the published treegrid pattern does, and it would answer "which
  session is this" in one key. It adds a key to the walk, and a session row
  would still do nothing on Left when closed.
- **Trying the `treegrid` role and a level on each row by hand.** The grid
  lets a script touch each row as it is drawn, so the roles NVDA announces
  depth from could be set without the paid features. It was never tried. AG
  Grid may write its own roles back, and it would change what NVDA hears of
  every row in both views.
- **A scenario row closes when the next one starts,** unless the player
  opened it. It would stop opened rows piling up. The script would have to
  remember who opened each row.
- **Show all runs on a closed session row,** to open a session and its runs
  in one click. It puts a link on every session row.

## Delivery plan

One implementation PR. This is intent, not a contract: a boundary that moves
is noted in that PR's description.

1. **The All scenarios view.** The switch, the tree's rows and their marks,
   the scenario name's click (A1), the count's link and **Show all runs**
   (A2), **Median and best** with the menu's extension (A3), and the docs.
   - **Needs:** this proposal ratified. Nothing else has to merge first. The
     Run toasts change may land before it or after it. Both edit
     `source/pages/run_history.py` and the roadmap's Upcoming entry, in
     different places, and whichever merges second merges `main`.
   - **It changes a public page in one release.** The page proposal's four
     PRs were hidden until the last. This one is not: the list gains the
     switch and the link on the day it merges.
   - **Measures and reports:** the model's size and the time from a run
     landing to the list painted, under All scenarios at 30 sessions and
     with every session loaded. The header's fit at 500 px. The widest
     session row. The cost of marking the listed scenarios.
   - **Runs NVDA on the built list,** in Firefox, Chrome, and Edge, through
     the tasks in
     [Keyboard and screen reader](#keyboard-and-screen-reader), and adds
     what it said to the research record. The walk takes the keyboard and
     the foreground window for some minutes, so it runs on the maintainer's
     word. The PR's session hands it to a subagent, as PR #371's did. A
     failed task goes to the maintainer.
   - **The maintainer looks at it in their own Firefox** before it merges,
     from steps the PR's description gives.
   - **Docs,** by the
     [Shipping a proposal](../../AGENTS.md#shipping-a-proposal-docs-definition-of-done)
     checklist: a decision-log entry for each row taken and one for the
     view, the notes in [Decisions this changes](#decisions-this-changes),
     the Run History and sessions specs, the glossary, the user guide,
     `architecture.md`, the roadmap, `product.md`, and this file deleted.
   - **Recommended:** `claude-opus-5-5` at xhigh. It is a row model with
     three levels, a script changed in the places an upgrade can break, and
     an NVDA walk.

The kickoff for this proposal read the work as one PR, and this plan follows
it. The reason is the walk: A3 changes what a screen reader hears of a row,
so a second PR would mean a second walk.

### Fallbacks

- **A3 is not settled when A1 and A2 are.** The tree ships without it, and
  A3 follows as a PR of its own with a short walk of its own: task 8, and
  R4's first two tasks with the figures on. That is the cut if the work
  proves to be two PRs' worth. A3 touches the shared menu module and nothing
  the tree needs.
- **A deep jump is too slow in the built list.** The PR says so, with the
  number, before it changes the design. The first remedy is smaller rows:
  each row carries its stats file's name twice, about 140 characters. The
  second is the jump that shows the session alone, from
  [Alternatives rejected](#alternatives-rejected), which is a change to this
  proposal and goes to the maintainer.
- **The walk finds a task NVDA can't do.** The walk is required and a repair
  is not (R4). The maintainer decides then: repair it first, ship with the
  failure recorded, or change the design.

## Out of scope

Each with where it is tracked. The local notes are under `ignore/` in the
maintainer's main checkout.

- **The typical run and its definition.** A later proposal of its own, by
  row S4 ([2026-10-11][sessions-entry]). The roadmap's
  [Guiding principles](../roadmap.md#guiding-principles) hold the rule, and
  the re-check of its evidence is queued as
  `ignore/prompts/typical-run-evidence-recheck-prompt.md`.
- **A median line on the chart.** Row R5 ([2026-10-12][every-run]). It
  belongs with the typical run.
- **The trend verdict.** The roadmap's
  [Future list](../roadmap.md#future-briefly), "Score trend verdict".
- **Run detail and a per-bot breakdown.** The roadmap's Future list,
  "Per-bot breakdown on time-scored kill scenarios", and
  `ignore/design-notes/run-history-page.md`, "Not at launch".
- **A Sessions entry in the navbar, month dividers or a jump to a date, and
  a chart point that opens its row.** The same note, "Not at launch".
- **What to do when opened rows pile up, and remembering which rows are
  open.** The same note, under "The run list": "Deferred until it proves a
  burden", and "to revisit after shipping".
- **Time spent and activity across all scenarios.** The roadmap's Future
  list, "An overview".
- **The run toast.** The [Run toasts proposal](run_toasts_proposal.md),
  ratified.
- **Score vs Sensitivity's redesign.**
  `ignore/prompts/icebox/score-vs-sensitivity-redesign-prompt.md`.
- **A browser's find-in-page reaching rows the grid has not drawn,** a phone
  design, and Narrator, JAWS, and a person listening. Each is recorded as
  left alone or not covered in the R3 and R4 entries
  ([2026-10-12][second-column], [2026-10-12][grid]).
- **Running the list's script in CI.** It would be the repository's first
  JavaScript test, and a decision of its own.
- **The two-tab model.**

## Testing

- **The row model,** as a pure function over plain run records, in
  `tests/test_run_history_list.py`:
  - A session with a return: two scenario rows for one scenario, numbered in
    the order they were played and listed newest first, with run numbers
    that carry on from the first row to the second.
  - A session row's three facts, with one run and with one scenario.
  - A star on a scenario row where a new PB was set, and none where it
    wasn't.
  - Every date-header case, asked of a scenario row: a row on the session's
    start date, a row wholly after midnight, a row that spans midnight, a
    single run that crosses it, and a session that crosses a year.
  - The marks of every listed scenario. A run's check and star in the tree
    equal its check and star under This scenario.
  - Median and best: one run, two runs, an odd and an even number, the
    session row's figures under This scenario, and no figures on a row with
    no run.
  - Which rows the newest run opens, for a run that carries on a visit and
    for one that starts a new one. A run that lands older than the store's
    newest and splits a visit.
  - A count of loaded sessions for each view, and the place among all
    sessions that a session row gives for its link.
  - The empty states: no runs, and All scenarios with no scenario selected.
- **The page,** in `tests/test_run_history_page_list.py`. Five tests there
  pin what this changes and are rewritten: the list's inputs, the Columns
  menu's checkboxes, the functions the grid names, what the list's layout
  holds, and the rule that the text for nothing to list hides the whole
  header. The tests that tie the script to Python stay: every function the
  grid names is defined in the script, the script reads no row field the
  rows don't carry, and it reads nothing from `context` that Python did not
  put there. So does the test that no server callback hears which rows are
  open.
- **The selection callback,** in `tests/test_run_history_page.py`. The test
  that pins who may ask for a scenario gains the tree. Two new tests hold
  that the asker is read from the trigger: a run that lands after a name was
  pressed follows the run with Follow on and moves nothing with Follow off,
  and a name pressed after a run landed selects the name.
- **The Columns menu.** Both playlist pages' menus render and register as
  they do today, with no choice that isn't a column.
- **The structural test of the 2026-09-19 entry** still passes with the
  switch written by a callback on a jump.
- **In a browser, by the PR,** in Edge and Firefox. The trial's scripts are
  the starting point: they already assert the two click targets on a row,
  the jump, and what survives a run landing.
  - The click targets: a row toggles, a name selects and does not toggle,
    and a count jumps and does not toggle.
  - The jump: which rows open, where the list scrolls, where focus lands,
    and a session beyond the 30 loaded.
  - The view is remembered across a reload, after a press of the switch and
    after a jump. Open rows are kept for each view and forgotten on a
    reload.
  - A run landing with rows open in the tree, with focus in a run row, with
    Follow on and off, and on a new scenario. One batch that holds runs on
    two scenarios opens both scenario rows.
  - Focus on a scenario's name stays on that button after the name is
    pressed and after a run lands.
  - **Median and best** turned on and off, with row heights and focus kept,
    and remembered across a reload.
  - The dropdown's visible text as well as its value after a name is
    pressed, with a Playlist filter that does not list the scenario.
  - Column alignment at every level, light and dark, and the narrow layouts.
  - The measurements the delivery plan names.
- **NVDA on the built list,** in Firefox, Chrome, and Edge.
- **The maintainer's own Firefox,** before the merge.
- **The docs test** holds this file's sections and its links.

[second-column]: ../decision_log/2026/2026-10-12-the-run-list-is-a-second-column-beside-the-chart.md
[grid]: ../decision_log/2026/2026-10-12-the-run-list-is-built-on-ag-grid-community-and-nvda-is-run-on-the-built-list.md
[clear-filter]: ../decision_log/2026/2026-10-12-follow-and-a-scenario-link-clear-a-playlist-filter-that-does-not-list-the-scenario.md
[every-run]: ../decision_log/2026/2026-10-12-the-run-history-chart-plots-every-run-and-draws-no-summary-line.md
[own-ids]: ../decision_log/2026/2026-10-12-run-history-keeps-its-own-control-ids-so-every-browser-saw-the-defaults-once.md
[check]: ../decision_log/2026/2026-10-12-a-past-runs-check-is-judged-against-the-pb-it-was-chasing-under-its-own-version.md
[sessions-entry]: ../decision_log/2026/2026-10-11-a-session-ends-after-a-break-of-more-than-30-minutes.md
[columns-menu]: ../decision_log/2026/2026-10-05-a-columns-menu-shows-and-hides-table-columns-and-kovaaks-ids-are-optional-ones.md
[principles]: ../decision_log/2026/2026-10-04-skill-is-judged-by-the-typical-run-with-honest-uncertainty-in-verdicts-not-advice.md
[query]: ../decision_log/2026/2026-09-19-a-query-parameter-selects-a-control-it-does-not-suspend-its-memory.md
