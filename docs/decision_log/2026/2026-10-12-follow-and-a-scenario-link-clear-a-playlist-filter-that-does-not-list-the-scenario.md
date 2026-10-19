# 2026-10-12: Follow And A Scenario Link Clear A Playlist Filter That Does Not List The Scenario

Status: Superseded in part, 2026-10-14, by the
[All scenarios entry](2026-10-14-the-run-list-has-a-second-view-all-scenarios-that-shows-each-session-whole.md):
the click in the All scenarios view this entry foresaw has arrived, as a
fourth way in. A scenario's name pressed in the tree is the selection
callback's fourth input, so "which of the three called" now reads which of
the four, still from what triggered the call. R7, and one callback as the
only writer of both dropdowns, stand.

When a run lands on a scenario the Playlist filter does not list, or a link
names one, Run History now empties the filter and selects the scenario.
Before, a link kept the filter and selected nothing, and a followed run could
leave the old scenario's name in the dropdown over the new one's chart. One
rule now covers every way of reaching such a scenario. The cost is that one
run outside a playlist means picking the playlist again, because the browser
remembers the emptied filter.

**Superseded in part (2026-10-18).** [The latest-run card's rule](2026-10-18-the-latest-run-card-reports-the-selected-scenarios-latest-run.md)
removes the card's button, so the selection callback's third input and the
button's `State` below are gone. A name pressed in the All scenarios view is
now the third input, and "which of the four called" reads which of the
three, still from what triggered the call. R7, and one callback as the only
writer of both dropdowns, stand.

**Superseded in part (2026-10-18).** [The unsaved note text entry](2026-10-18-unsaved-note-text-is-never-lost-to-a-change-of-scenario-or-page.md)
has Follow select the scenario just played except while a scenario note has
unsaved changes: the run then waits, and the card names its scenario. The
selection callback gains the note card's answers and the Follow switch as
inputs, so turning Follow off ends a wait, and it reads the note's editor and
text as `State`. A name pressed in the All scenarios view is held while the
note has unsaved changes. R7, and one callback as the only writer of both
dropdowns, stand.

**Rulings.** By the maintainer, 2026-10-12, on
[PR #356](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/356):
"I ratify the proposal." This entry is row R7, ratified as recommended.
Before it, the maintainer, 2026-10-10, on Follow: "For now if this happens,
we can simply unfilter the playlist, as it probably implies that the user is
not playing the playlist anymore." On the link: "I initially lean yes, but
what is your take?" The author's take on the link was yes, for one reason:
one rule then covers every way of reaching such a scenario. Built in
[#370](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/370),
with the latest-run card's button in
[#372](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/372).
The rule as the app applies it is in
[run_history.md](../../specs/run_history.md#run-delivery). This entry holds
the reasons, the cost, and the mechanism that makes the rule safe.

**Two words.** Follow is the **Follow newly played scenario** switch: while
it is on, the page selects the scenario just played when a new run is
detected. The Playlist filter narrows the scenario dropdown to one playlist's
scenarios, and its playlist supplies the chart's rank lines.

**R7, the rule.** When Follow lands on a scenario the Playlist filter does
not list, or a `?scenario=` link names one, the filter is cleared and the
scenario is selected. The scenario must have local runs: a link that names
one with none leaves the filter alone and selects nothing.

- **Neither way worked well before.** A `?scenario=` link kept the filter
  and dropped the scenario, leaving nothing selected. Follow's callback wrote
  the scenario without looking at the filter. What the dropdown then showed
  was not checked for Follow. On this app's playlist filter, the same
  component kept the previous option's name on screen when a callback wrote
  a value its list lacked (headless Edge, 2026-10-11). So Follow most likely
  left the old scenario's name in the dropdown while the chart and Scenario
  Stats showed the new one.
- **The list makes it more visible.** A run that lands is a new row and a
  new card. A page still filtered to a playlist that run isn't in would
  show a selection its own dropdown can't name.
- **The same rule covers the other ways in.** The scenario's name on the
  latest-run card follows it, and so will a click in the All scenarios view,
  a later proposal.
- **The ratified run toast's link depends on it.** That link names the
  scenario and carries no playlist, because the app shell doesn't know what
  the page's filter holds.

**What it costs.** Clearing the filter takes away the rank lines and the
Open scenario table link, and the cleared filter is what the browser then
remembers. One run outside a playlist means picking the playlist again. The
filter empties in view and no toast says so. The Follow switch's help text
gained a sentence, the one place that explains a filter that emptied itself:
`Automatically selects the scenario you just played when a new run is
detected. If the **Playlist filter** doesn't list that scenario, the filter
is cleared.`

**One exception to the 2026-09-19 entry.**
[That entry](2026-09-19-a-query-parameter-selects-a-control-it-does-not-suspend-its-memory.md)
says "`?scenario=` alone leaves the playlist filter on the restored value".
That now holds only while the filter lists the scenario. Everything else in
it binds the new page unchanged: the invariant that a remembered control's
layout default never varies per visit, its corollary about a callback that
writes a control only on some visits, an unknown playlist code clearing the
filter, and the URL not being rewritten. The two parameters select the two
dropdowns on the new address by callback, never as a layout default.

**If the maintainer had chosen otherwise.** With the old link rule kept, a
link to a scenario outside the filtered playlist selects nothing, while
Follow on the same scenario clears the filter. A run toast for such a
scenario then opens the page with nothing selected. With Follow keeping the
filter too, it has to stop following such a run, or the dropdown has to show
a scenario its playlist doesn't list, and the card then reports a run the
rest of the page ignores.

**The cases, as checked in a browser.** PR #370, in headless Edge and
Firefox. The dropdown's visible text was read beside the value Dash holds.

| Case | Result |
|---|---|
| A link to a scenario the remembered filter does not list | Filter cleared, scenario selected, text and value agree, rank lines gone, and the cleared filter is what the browser stored |
| A plain visit afterwards | The same selection, the filter still empty |
| A link to a scenario the filter lists | Filter kept |
| A link to a scenario with no local runs | Filter kept, nothing selected |
| Both parameters, and the playlist does not list the scenario | Filter cleared, scenario selected |
| An unknown playlist code | Filter cleared, as before |
| A run lands on a scenario the filter does not list, Follow on | Filter cleared, scenario selected, one chart rebuild |
| The same with Follow off | Nothing changes, and nothing rebuilds |
| A run lands on a scenario the filter lists, Follow on | Scenario selected, filter and rank lines kept |

**The mechanism: one callback writes both dropdowns.** The rule needs the
filter and the scenario to change in one step, and the proposal did not say
how. PR #370 chose the build below, and the list and the card of the later
pull requests hang on it.

- **The old page's batch consumer wrote the scenario dropdown itself.**
  Under R7 a followed run may have to clear the filter in the same step, and
  the filter already had a writer, the callback that applies a link. A
  second writer of an output needs `allow_duplicate`.
- **Dash does not hold a dependent callback back for an output written with
  `allow_duplicate`.** The scenario list could then be built for the old
  filter, land after the scenario was selected, and drop it. The 2026-09-19
  entry records the same fact from the other side, as the reason a
  deep-linked visit ran the chart callback twice.
- **So one callback is the only writer of both dropdowns' values, with plain
  outputs.** It applies a link's parameters, a followed run, and the card's
  button. Dash then holds the scenario list and the chart until it has
  answered.
- **Run delivery is three callbacks, where the old page had two.** The
  page's batch consumer writes only a summary of the batch. The selection
  callback reads the summary and moves the dropdowns. What draws, the chart
  and the list, waits on the selection and is built once per batch, for the
  scenario the page ends up on. The browser check counted one chart rebuild
  per batch.
- **The cost is time.** A landed run waits for the server three times in a
  row, and reached the screen in 106 to 182 ms in Edge in PR #371's rounds.
- **The structural test of the 2026-09-19 entry is carried to the page.** It
  fails if any callback's inputs are all among the two outputs the selection
  callback writes only on some visits.

**The scenario list is read again when a run lands.** A flagship read of
PR #370 by `gpt-6-astra` found a gap after both review seats had passed the
build. With no filter and Follow on, the first run of a scenario that had no
runs when the page was drawn moved the chart and the stats, while the
dropdown kept the old name: the selection callback wrote the value, and with
no filter to clear nothing wrote the list. The callback that lists the
scenarios now takes a run landing as an input.

- **First it took the summary,** which is written only for a batch the page
  shows. With Follow off, a scenario's first run then stayed out of the list
  until the list was next built.
- **PR #371 gave it the id of the batch's newest run instead,** a store
  written for every batch, on whatever scenario. That closed the second
  gap.
- **The list still waits for the selection.** The batch consumer writes both
  stores in one answer, and the list takes the filter's value, which is the
  selection callback's plain output. So a filter in the way is cleared
  before the list is built.
- **The cost:** one more small request for each batch.

**The card's button is the selection callback's third input.** The name of
the last run's scenario, on the latest-run card, selects that scenario under
this rule
([the card's entry](2026-10-12-a-past-runs-check-is-judged-against-the-pb-it-was-chasing-under-its-own-version.md)).

- **Which of the three called is read from what triggered the call, never
  from the values.** The summary store replays its last batch. Read from the
  values, a click made after a run landed would be taken for that run: with
  Follow on the page would go back to the scenario last played, and with
  Follow off the click would do nothing. Two tests hold both.
- **The button is in the layout from the start, and is never drawn again.**
  A page has to hold every input of a callback whose output it holds, and a
  button that came and went with the card's text would call the selection
  callback each time it was put back. While it names no scenario it is out
  of the page by `display: none`, so it is out of the tab order too.

**The dropdown can show the old name for one round trip.** In the Follow
case the value is written first, then the list that holds it. PR #370's
check sampled both every 60 ms and some rounds caught it, in each browser,
before the text and the value agreed. So a browser test of this rule asserts
the dropdown's visible text as well as its value: a test on the value alone
passes through the gap.

**A parameter the page doesn't name.** The page's layout accepts query
parameters it doesn't read, as the old page's did. The ratified run toast's
link carries `run=` beside `?scenario=`. It is there only so each toast's
address is new, because a link to the address the page already holds does
nothing.

**What did not change in run delivery.** The app shell drains new runs on
every page and publishes one batch per poll
([2026-07-06](2026-07-06-coalesce-pending-home-run-events.md)). The page
consumes that batch as the old one did: one chart rebuild and at most one
change of scenario per batch, and a page that mounts replays nothing. One
active tab is still the supported way to use the app.

Proposed in
[PR #356](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/356),
which merged as `a65f72d`. Shipped in
[#370](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/370),
[#371](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/371), and
[#372](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/372),
hidden, and made public in
[#373](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/373),
which also removed the old page and its rule. The proposal file,
`docs/proposals/run_history_proposal.md`, is deleted, and git history keeps
it.
