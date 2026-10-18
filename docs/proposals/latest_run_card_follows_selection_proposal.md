# Latest-Run Card Follows The Selection Proposal

Status: Proposed
Date: 2026-10-18

## TL;DR

Run History's top row puts the PB card beside the latest-run card, but the
latest-run card reports the last run played on any scenario, so while a player
looks another scenario up the two big scores belong to different scenarios.
This proposal makes the latest-run card report the selected scenario's latest
run, names the session of an older run, and gives the card plain empty states.
With the card naming the scenario right above the run list, Last played leaves
Scenario Stats as a duplicate and the run list drops its heading line. During
play with Follow on, the card shows the same run as today and the row keeps
its height.

## Decisions needed

Three rows: R1 to R3. Nothing is ratified. Each row is the maintainer's lean
from the design discussion of 2026-10-14, refined on 2026-10-18 on full-size
mockups built from their own stats (versions 12 to 14), and each keeps what
they said, its argument, and what the alternatives would change. R2 and R3
rest on R1: both are argued from the card naming the selected scenario, and
neither should ship without it. Everything else is author-owned and is in
[Design](#design), including the third line's layout and every string in
[Copy](#copy); reviewers may challenge any of it.

This is the second of two proposals from the 2026-10-14 discussion. The
first, the top row cards, shipped in PRs #379, #380, #383 and #384, and this
one's argument rests on its layout: the latest-run card sits directly over the
run list, beside the PB card.

### R1. The latest-run card reports the selected scenario's latest run

Status: open. The maintainer's lean, 2026-10-14, on three cases for the card
(a new run, the selected scenario, a clicked run): "I agree with the case 2
lean. Case 3 can come later or never." Refined on 2026-10-18, so the card
follows the selection with nothing to fall back on: "For simplicity, why not
just make the Latest Run card follow what scenario is selected in the top left
filter?" That replaces their answer of 2026-10-14 that with no scenario
selected the card would show the last run on any scenario.

The material consequence: the card stops reporting the last run played on
whatever scenario, which the 2026-10-12 card decision set, and its
**Show {scenario}** button goes. With Follow off, a run on another scenario no
longer reaches the card.

**Recommendation: the card reports the selected scenario's latest run, its
last run in the newest session that holds one, judged exactly as the card
judges a run today. With no scenario selected it says so. For a scenario with
no runs it reads "No runs yet". The Show {scenario} button is removed.**

- **The two big scores always describe one scenario.** Looking up VT
  Controlsphere Viscose on 2026-10-18, with Viscose Benchmark S2 - Medium
  selected, today's card shows RawControlSphere's 11,598, a new PB, beside
  the PB card's 3,653. Under R1 it shows Viscose's own latest run: 3,133,
  85.8% of PB.
- **During play with Follow on, the card shows the same run as today.** The
  selected scenario is the one just played.
- **A lookup gets its answer in the card:** when the scenario was last
  played, how that run went, and in which session.
- **What is lost is the half-follow with Follow off.** Today the card shows a
  run on another scenario and offers one click to select it. Under R1 that run
  shows in its run toast, whose "Open in Run History" link selects it, and in
  the run list's All scenarios view, whose names select it. With Run
  notifications also off there is no toast, and the page shows the run only in
  small ways: the run list counts it on its first session row, and the
  chart's ring and the list's highlight leave the selected scenario's run.
- **The card's age becomes the selected scenario's.** With Follow on it is
  still the length of the break since the last run. During a lookup it is how
  long ago that scenario was last played, which is what Last played says.

Rejected:
- **A clicked run in the card (case 3).** A past run's percentage is against
  the PB of its day, so a run of 3,181 would read "94.8% of PB" beside a PB
  card showing 3,653, and it needs rules for what selects a run and what ends
  the selection. Later or never.
- **Dimming the card when its run is another scenario's.** It keeps the
  half-follow, but still sets two scenarios' scores side by side, and Last
  played could not go.
- **The last run on any scenario with nothing selected.** The maintainer's
  answer of 2026-10-14, dropped for simplicity: the dropdown and the All
  scenarios view cover a first visit.

### R2. Last played leaves Scenario Stats

Status: open. The maintainer's lean, 2026-10-14, while Proposal 1 was in
review, was to remove Last played; they kept it until now: "'just now' is
fine, keep Last played until Proposal 2." On the card left behind, 2026-10-18:
"Slim the Scenario Stats card is fine. Later it will likely hold the Typical
Score." On its label, the same day, they asked whether "Scenario Stats" and
"Latest run" should be cased alike, and agreed to the recommendation below.

The material consequence: this supersedes part of Proposal 1's ratified T2,
which put Category, Last played and Number of runs in the card. The card keeps
Category and Number of runs.

**Recommendation: remove Last played. The card's first line becomes plain
text in sentence case, "Scenario stats", and with no scenario selected the
card reads "No scenario selected" in place of its lines.**

- **Under R1, Last played repeats the card beside it.** Both read "1 day ago"
  for VT Controlsphere Viscose on 2026-10-18.
- **Its empty value is the app's only allowed em dash.** Copy rule 2 forbids
  em dashes everywhere but under Last played with no scenario selected, and
  the test that gates them allows that one string. Removing the row leaves the
  rule with no exception.
- **"Number of runs: 0" with nothing selected reads as a count.** The card
  says what the two cards beside it say instead.
- **The three cards' first lines are one kind of thing on screen.** "PB · set
  8 days ago" and "Latest run · 1 day ago · {scenario}" are plain text in
  sentence case. "Scenario Stats" is an `h2` in Title Case, as copy rule 3
  sets for headings, so it reads as a title the other two are not. As plain
  text it matches them. The page outline loses that heading, as the PB card
  and the latest-run card never had one.

Rejected: keeping Last played as a deliberate duplicate; removing the card,
which T1 placed and Typical Score is expected to fill; `—`, `N/A` or `None`
for Number of runs with nothing selected (`—` would bring the em dash
exception back, and `None` reads as zero runs).

### R3. The run list's heading line goes, in both views

Status: open. The maintainer's lean, 2026-10-14. The heading names the list's
scenario and counts its runs. They noted that the All scenarios heading counts
every run in the store, a total Home already gives ("Found {runs} runs across
{scenarios} scenarios in your stats folder.").

The material consequence: `{scenario} · {n} runs` and `All scenarios · {n}
runs` leave the screen, and the list gains 35 px of rows.

**Recommendation: remove the visible heading line in both views. Its text
stays for screen readers, hidden from view, in the same words.**

- **Under R1 the card right above the list names its scenario,** and
  Scenario Stats keeps the run count.
- **Today the heading is what names the list's scenario,** because the card
  can show another one. That is why this row waits for R1.
- **The list's header drops from 90.8 px to 56.0 px** at 2560 px, in Edge and
  Firefox alike.

Rejected: keeping the heading while the card names the scenario (a second
label for one fact); removing it without R1, which would leave nothing above
the list naming its scenario during a lookup.

## Problem

### What the card shows today

The latest-run card "reports the last run played, on whatever scenario"
([run_history.md](../specs/run_history.md#the-latest-run-card), set by
[2026-10-12](../decision_log/2026/2026-10-12-a-past-runs-check-is-judged-against-the-pb-it-was-chasing-under-its-own-version.md)).
`latest_run` in `components/latest_run_card.py` takes the newest session's
last run. While another scenario is selected, the run's scenario name is a
button, `Show {scenario}`, which selects it.

Proposal 1 put the PB card beside it, because the two hold the numbers a
player compares after every run: the target and the result. During play with
Follow on they describe one scenario. During a lookup, the reason the page
also exists ("before I play Scenario B, I might manually swap to Scenario B,
so I can look at its stats or notes"), they do not: the PB card follows the selection
and the latest-run card does not. The roadmap gives this as the reason
Proposal 2 is next.

### What following the selection breaks

Four things in the shipped card assume the card reports the newest run
overall. Each is handled in [Design](#design).

- **The third line.** `_session_line` words the run's session as "this
  session" or "last session", which is true only for the newest session.
  VT Controlsphere Viscose was last played in the session that began Oct 16
  at 2:00 PM. The newest session began at 8:06 PM the same day, so "last
  session" would be false even for a run that morning.
- **The empty state.** It covers only a store with no runs. A selected
  scenario with no runs, and no scenario selected, have no state.
- **Last played** repeats the card's age once the card reports the selected
  scenario's run (R2).
- **The run list's heading** names the scenario the card above it will name
  (R3).

### Verified facts

Measured on 2026-10-18 on the maintainer's stats, served from `main` at
`4199f7f` with the card's rule replaced in the served app (no tracked file
edited), and captured into mockup v14. Scenario Stats and the run list's
heading were edited on the captured page, not in the app.

- **The store:** 9,212 runs in 328 sessions. The newest session began
  Oct 16 at 8:06 PM and holds 4 runs. Its last is RawControlSphere.
- **The row stays 141.4 px** in all seven states the mockup holds (the
  scenario played last, a lookup with and without a benchmark, a scenario
  never played, no scenario selected, the longest third line, and a store
  with no runs), under today's rule and R1, in Edge and Firefox, at 1920, 2560
  and 3840 px, in light (and dark at 2560 px). 192 checks, no page error.
- **The longest real third line** is 70 characters: `Run 8 (Jul 20, 2020,
  11:47 PM session) · Time on this scenario unknown` (Ascended Tracking v3).
  On one line it takes 373 of the line's 474 px. Split as Design does, its
  longer part takes 200 px. A made-up worst case with a date from an earlier
  year and `2 hr 15 min` takes 212 px.
- **The card's text** is 94 px tall today and 114 px with the time on its own
  line, in a card 141.4 px tall. The card keeps its height.
- **The two scores line up with the time on its own line,** while a benchmark
  is selected. The latest-run card's score sits 12 px below the PB card's
  today and 2 px below it with the extra line, and the two first lines then
  sit 2 px apart. With no benchmark the PB card has one line fewer: 1.5 px
  today, and 8.5 px above it with the extra line.
- **The em dash guard** (`tests/test_em_dash_guard.py`) allows one string,
  `("source/components/scenario_stats.py", "get_scenario_num_runs", "—")`:
  Last played's empty value.
- **The Show {scenario} button** is the third `Input` of
  `reach_scenario_or_the_one_asked_for` (`components/scenario_selection.py`),
  the one writer of both dropdowns' values.
- **An existing stats folder with no runs shows no setup hint** above the
  row. The card's "No runs yet" state is what a new user with a stats folder
  sees.
- **With Follow off, a run leaves the selection as it was,** empty or on
  another scenario: `reach_scenario` returns nothing to write for it. With
  Follow on it selects the run's scenario. Checked at `dc4e596` by calling
  it, as two reviewers did.

### Not checked

- What NVDA says of the hidden heading line and of the cards' first lines. The
  mockups are captured pages, not the live app.
- The empty store's new sentence in a browser. The mockups show today's. At
  61 characters it is shorter than the two messages they measured, today's
  at 63 and "Play this scenario…" at 66.
- A run landing while the page is open. The rule ran in the served app, but
  no run landed during the captures.
- 1536 px, and browser zoom at 110% and 125%.

## Design

### Which run the card reports

- **The selected scenario's last run in the newest session that holds one.**
  The sessions are the ones `split_into_play_sessions` makes, so the card
  agrees with the run list about which run is newest.
- **It is judged as today:** against the PB it was chasing, under its own
  version of the scenario, with the same badge, percentage, caps and accuracy.
- **The card is rewritten on today's triggers, plus the date moving on:** a
  run landing on any scenario, a change of scenario, the Score threshold
  percentage, the newest session ending, and the page's date store. A run on
  another scenario can change the third line's words (a new session makes the
  old one "last" or older) without changing the run. The date matters because
  an older session's name leaves its year out only while it is this year's,
  as the run list's rows do: a page left open over New Year's would otherwise
  keep `Dec 31, 2:00 PM session` with no year.
- **The scenario's name on the first line is always plain text,** with the
  whole name as its tooltip where the card cuts it short, as today while it
  is selected.

### The third line, now two lines

- **The newest session keeps today's words:** `Run 4 this session` while it
  is in progress, `Run 4 last session` once it has ended.
- **An older session is named as the run list names its row:**
  `Run 7 (Oct 16, 2:00 PM session)`, or with the year where it is not this
  one, `Run 8 (Jul 20, 2020, 11:47 PM session)`. The parentheses are the
  maintainer's wording. "Session" stays inside them, or the time would read as
  the run's own.
- **The time spent on the scenario gets a line of its own** in every form:
  `9 min on this scenario`, or `Time on this scenario unknown`. The maintainer
  could go either way; the author chose it because, with a benchmark selected,
  it lines the latest-run card's score up with the PB card's (see Verified
  facts). One line fits too: the longest real line takes 373 of 474 px.
- **`{n}` and the time keep their meaning:** the run's number among the
  scenario's runs in that session, and the scenario's visits in that session.

Rejected: `Run 7 (latest session)` for the newest session, which cannot say
whether the session is still going; naming the newest session by its time too,
which is harder to read during play than "this session".

### The empty states

Each opens on a quiet first line that reads `Latest run` alone, as the PB
card's empty states open on `PB`.

| When | The card reads |
|---|---|
| No scenario is selected, and the store has no runs | "No runs yet" over "Play a scenario in KovaaK's. Select it to see its latest run." |
| No scenario is selected | "No scenario selected" |
| The selected scenario has no runs, whether or not the store has any | "No runs yet" over "Play this scenario in KovaaK's and your latest run will show here." |

- **The selection decides first, as on the PB card.** A playlist filter lists
  its scenarios before any is played, so a scenario can be selected in a
  store with no runs. The card then speaks of it, as the PB card beside it
  does: "Play this scenario to record one in this app."
- **"Play this scenario" holds with Follow off.** Playing the selected
  scenario keeps it selected, and a different scenario would not show here.
- **With nothing selected and no runs, the sentence says to select the
  scenario played.** With Follow off a first run leaves the selection empty,
  and the card then reads "No scenario selected", so today's "your latest run
  will show here" would promise what the card does not do. With Follow on,
  the default, the run's scenario is selected as it lands, and the second
  step is already done.
- **The card keeps its height** in every empty state.

Rejected: today's sentence for a store with no runs, which is true only with
Follow on; a sentence that changes with the Follow switch, which would make
the switch one of the card's triggers for a state a new user sees once.

### What goes with the Show {scenario} button

- The button, its `Show {scenario}` accessible name, and the keyboard focus it
  hands to the Selected scenario dropdown after a press.
- Its `Input` on `reach_scenario_or_the_one_asked_for`, which keeps three
  callers: a link's parameters, a followed run, and a name pressed in the run
  list's All scenarios view.
- A scenario is still chosen on the page with the dropdown, with Follow and a
  run, or with a name in the All scenarios view, and from elsewhere with the
  run toast's link or a playlist table's scenario link.

### What stays as it is

- **The chart's ring and the run list's highlight** still mark the last run
  played on any scenario, so during a lookup they leave the selected scenario.
  That says the card's run is not the one just played. The store the page
  writes for them stays the newest run overall.
- **The run toast, the celebration, and Follow** are unchanged.
- **During play with Follow on** the card shows the run it shows today. Its
  third line takes two lines.

### Scenario Stats

- **Last played goes,** with its 30-second ticking text, its hover, its two
  stores, and its empty values `—` and `Never`.
- **The first line is plain text, `Scenario stats`,** styled as today's quiet
  first line, at the card's top like the other two cards' first lines.
- **With no scenario selected,** the card's lines give way to "No scenario
  selected", styled as the PB card's.
- **Category and Number of runs** keep their rules, and the card keeps its
  270 px frame.

### The run list

- **The heading line is hidden from view in both views** and kept for screen
  readers with the app's `visually-hidden` class, in today's words. It stays
  what it is today, a line of text read in its place before the view switch.
  "Heading line" is the spec's name for it: it is not an HTML heading, and it
  does not become one.
- **The view switch, "Expand all" and "Columns"** move up to the header's
  first line. Nothing else in the list changes.
- **A scenario with no runs** no longer reads `{scenario} · 0 runs` above the
  list. The card reads "No runs yet", and the list shows the newest session
  alone, as today.

Rejected: making the hidden line an `h2`, which would give the page a heading
to jump to once Scenario Stats' heading goes. R3 only takes a line out of
view, so a screen reader hears what it hears today; an `h2` would change that,
and what NVDA makes of the page is not checked. An implementing PR that
checks it can propose one.

### Narrow windows, keyboard and screen readers

- **Narrow windows** follow today's rules. At 900 px or less the run list goes
  above the chart, and the latest-run card stays in the top row, above it.
- **Keyboard:** the card's age still takes focus and shows the exact time.
  The button was the card's one control, and it is gone.
- **Screen readers:** the run list keeps its heading line's text, hidden.
  Scenario Stats' first line is no longer a heading, and it was the page's
  only `h2`. The cards' first lines are read as text.

### How it is built

- **`latest_run` takes the scenario** and finds its last run in the newest
  session that holds one. `_session_line` takes the session's place and, for
  an older session, names it with `format_short_timestamp`, the run list's
  own function for a session row. It returns the run part and the time part
  apart, and the card draws each as a line in the card's session style.
- **`show_latest_run` computes two things:** the card's run, from the
  selected scenario, and the newest run overall, whose id it writes to the
  store the chart's ring and the list's highlight read, as today. It takes
  the page's date store (`TODAY_STORE_ID`) as an `Input`, read for nothing
  but its change, as `build_run_list_rows` does for its session names.
- **`latest_run_card_content`** loses its button branch and gains the three
  empty states. The scenario button leaves `latest_run_card`, the page's
  outputs, and `reach_scenario_or_the_one_asked_for`.
- **Scenario Stats** loses the Last played group, its stores and its
  clientside callback, and its `dmc.Title` becomes a `div` in the same class.
- **The em dash guard's allowlist becomes empty.** Its check that the
  allowlisted string is still found, which proved the walk reads real source,
  needs another proof, such as a planted fixture the walk must find.
- **The run list's heading line** keeps its `dmc.Text` and takes the
  `visually-hidden` class.

### Copy

Every string this proposal adds, changes or removes. They follow the nine copy
rules in [AGENTS.md](../../AGENTS.md#styling-conventions). A string the page
has today and this table does not name is unchanged.

| Where | String | Why |
|---|---|---|
| Latest-run card, first line with a run | `Latest run · {age} · {scenario}` | Today's line. The scenario is always plain text now. |
| Latest-run card, first line with no run | `Latest run` | The card's name alone, as the PB card's `PB`. |
| Latest-run card, third line, newest session | `Run {n} this session`, `Run {n} last session` | Today's words, with the time moved to the next line. |
| Latest-run card, third line, older session | `Run {n} ({session} session)`, such as `Run 7 (Oct 16, 2:00 PM session)` | The session's name as the run list's row gives it. The maintainer's form. |
| Latest-run card, fourth line | `{duration} on this scenario`, `Time on this scenario unknown` | Today's words, on a line of their own. |
| Latest-run card, no runs at all and no scenario selected | `No runs yet` over `Play a scenario in KovaaK's. Select it to see its latest run.` | Was `Play a scenario in KovaaK's and your latest run will show here.`, which only Follow on makes true. |
| Latest-run card, no scenario selected | `No scenario selected` | The page's words for the state, as the PB card, the chart and the run list say them. |
| Latest-run card, a scenario with no runs | `No runs yet` over `Play this scenario in KovaaK's and your latest run will show here.` | "This", because the card follows the selection. Also in a store with no runs. |
| Scenario Stats, first line | `Scenario stats` | Plain text in sentence case, as the other cards' first lines. Was `Scenario Stats`. |
| Scenario Stats, no scenario selected | `No scenario selected` | As the two cards beside it. |
| Run list heading line, screen readers only | `{scenario} · {n} runs`, `1 run`, `All scenarios · {n} runs` | Today's words, hidden from view. |

Removed: `Last played:` with its values, `—` and `Never`, and its hover; the
`Show {scenario}` button and its accessible name.

### Terms

Written as [docs/glossary.md](../glossary.md) would hold them, under "The Run
History page". The implementing PR moves them in.

- **Latest-run card** becomes: "The card at the right end of Run History's
  top row, over the run list, that reports the selected scenario's latest run
  with its verdict." On screen its first line reads `Latest run · {age} ·
  {scenario}`, or `Latest run` alone with no run to report.
- **Scenario Stats** becomes: "The card in Run History's top row about the
  selected scenario: its benchmark category and how many runs it has." On
  screen its first line reads `Scenario stats`.

### Decisions this changes

The implementing PR keeps each entry and adds a dated "Superseded in part"
note. It erases nothing.

- [2026-10-12, a past run's check](../decision_log/2026/2026-10-12-a-past-runs-check-is-judged-against-the-pb-it-was-chasing-under-its-own-version.md):
  its section on the latest-run card, which reports the last run on whatever
  scenario and has the scenario button (R1).
- [2026-10-12, Follow and a scenario link clear the filter](../decision_log/2026/2026-10-12-follow-and-a-scenario-link-clear-a-playlist-filter-that-does-not-list-the-scenario.md):
  the card's button as one of the selection callback's inputs (R1).
- [2026-10-12, the run list is a second column](../decision_log/2026/2026-10-12-the-run-list-is-a-second-column-beside-the-chart.md)
  and
  [2026-10-14, the All scenarios view](../decision_log/2026/2026-10-14-the-run-list-has-a-second-view-all-scenarios-that-shows-each-session-whole.md):
  the visible heading line (R3).
- [2026-10-14, Scenario Stats names the category](../decision_log/2026/2026-10-14-scenario-stats-names-the-selected-benchmarks-category.md)
  and
  [2026-10-14, a card's lines follow their role](../decision_log/2026/2026-10-14-a-cards-lines-follow-their-role-in-the-players-next-action.md):
  Last played in the card, and its label (R2).
- [2026-06-21, relative Last played](../decision_log/2026/2026-06-21-relative-humanized-last-played-timestamps.md)
  and
  [2026-06-30, Last played's empty states](../decision_log/2026/2026-06-30-model-home-last-played-empty-states-explicitly.md):
  their Run History use goes; the playlist tables' Last Played column is
  untouched (R2).
- [2026-09-14, the copy rules](../decision_log/2026/2026-09-14-app-copy-follows-one-set-of-rules-and-the-em-dash-is-gated-out.md):
  rule 2's one exception and the guard's allowlist, and the rule's sentence in
  AGENTS.md (R2).

## Delivery plan

One implementation PR. This is intent, not a contract: a boundary that moves
is noted in the PR's description. It changes a public page in its release.

1. **The card follows the selection, and the proposal ships** (R1, R2, R3).
   The card's rule, its two-line third line and three empty states, the
   button's removal, Scenario Stats without Last played with its new label and
   empty state, the hidden list heading, the em dash guard, and the
   [Shipping a proposal](../../AGENTS.md#shipping-a-proposal-docs-definition-of-done)
   checklist: a decision-log entry per row, the notes in
   [Decisions this changes](#decisions-this-changes), the Run History and
   sessions specs, the glossary's entries in [Terms](#terms), the user guide,
   `architecture.md`, AGENTS.md's copy rule 2, the roadmap, `product.md`, and
   this file deleted.

It needs this proposal ratified. **Recommended:** `claude-opus-5-5` at xhigh,
since it removes an input from the shared selection callback and carries the
shipping checklist. The maintainer looks at it in their own Firefox before it
merges.

### Fallback

- **The PR grows too large.** Split it at R1: the card first, then Scenario
  Stats, the list heading and the shipping docs. The second waits for the
  first, since R2 and R3 rest on it.

## Out of scope

- **A clicked run in the card (case 3).** Later or never (R1).
- **Top-aligning every card's lines,** which would line the scores up
  whatever the line count. It changes Proposal 1's shipped layout and leaves
  space under short cards.
- **Typical Score in Scenario Stats.** Its own proposal.
- **Notes on a scenario.** A later proposal for the space kept in the row.
- **Time played on a scenario,** decided once for every page (Backlog).
- **A jump from the PB card to the PB run.** Its own proposal or a small PR.

## Testing

- **Unit, which run the card reports:** the selected scenario played in the
  newest session (in progress, and ended); played only in an older session;
  played in an older session the same day as the newest; never played; no
  scenario selected; a store with no runs, with and without a scenario
  selected, which read the empty store's sentence and "Play this scenario"
  respectively. Each checks the run, the third line's two parts, and the
  empty state's words.
- **Unit, the older session's name:** this year and an earlier year, matching
  the run list's row for the same session; a visit with no usable start.
- **Callbacks:** a change of scenario rewrites the card; with Follow off, a run
  on another scenario leaves the card's run and moves the ring's store; a run
  that starts a new session turns "last session" into the session's name; the
  date store moving into a new year rewrites an older session's name with its
  year, with no run landing; the selection callback has no card input, and
  its three callers still select.
- **Callbacks, the first run into a store with no runs,** with Follow off and
  on, with nothing selected and with a playlist's unplayed scenario selected
  and another scenario played. With Follow off the selection stays as it
  was, and the card reads "No scenario selected" or keeps "Play this
  scenario". With Follow on the card shows the run.
- **Scenario Stats:** no Last played in any state; the first line's text and
  that it is not a heading; "No scenario selected" with nothing selected;
  Category and Number of runs unchanged.
- **The run list:** the heading line's text is hidden in both views, still in
  the page's text for a screen reader, and not a heading element; the
  header's controls sit on its first line.
- **The em dash guard** passes with an empty allowlist and still proves its
  walk reads real source.
- **Live:** headless Edge and Firefox at 3840, 2560, 1920 and 1536 px, in
  light and dark, in the mockup's seven states: the row's height against
  today's 141.4 px, the card's text inside the card, the run list's header.
  The maintainer's look in Firefox.
- **Docs:** `tests/test_docs.py` for the links, and the gates in AGENTS.md.
