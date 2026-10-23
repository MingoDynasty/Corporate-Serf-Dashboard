# 2026-10-18: The Latest-Run Card Reports The Selected Scenario's Latest Run

Status: Accepted

Run History's latest-run card reports the selected scenario's latest
result beside its personal best. The chart ring and highlighted list row
identify that same run during both play and manual browsing. An older
result names the session it came from. An empty card explains why it has
no run to report.

**2026-10-23 amendment.** The **What stays** rule that reserved the chart ring and run-list highlight for the last run played on any scenario
is superseded by [selected-scenario latest-run highlights](2026-10-23-run-history-highlights-the-selected-scenarios-latest-run.md).
The original text is retained as history; the other rules stand.

**Ruling and delivery.** R1 of
[#388](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/388),
ratified by the maintainer on 2026-10-18 at `0fcac03`, "I ratify the
proposal.", as amended in review: the selection decides the empty state first
(SOL-S1 and AS-F1), and a late run reaches the card by the selected
scenario's latest run (F3). Before it, the maintainer's lean of 2026-10-14 on
three cases for the card (a new run, the selected scenario, a clicked run):
"I agree with the case 2 lean. Case 3 can come later or never." Refined on
2026-10-18, so the card has nothing to fall back on: "For simplicity, why not
just make the Latest Run card follow what scenario is selected in the top left
filter?" That replaced their answer of 2026-10-14 that with nothing selected
the card would show the last run on any scenario. Built in
[#391](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/391).
Current behavior is in
[run_history.md](../../specs/run_history.md#the-latest-run-card).

**Why.** Proposal 1 put the PB card beside the latest-run card because the two
hold the numbers a player compares after every run: the target and the
result. During a lookup, which the page also exists for ("before I play
Scenario B, I might manually swap to Scenario B, so I can look at its stats
or notes"), they described two scenarios: on 2026-10-18, with VT Controlsphere
Viscose selected, the card showed RawControlSphere's 11,598, a new PB, beside
the PB card's 3,653. Under this rule it shows Viscose's own latest run, 3,133,
85.8% of PB.

**Which run.**

- The selected scenario's last run in the newest session that holds one. The
  sessions are split from every run in the store, as the run list splits
  them, so the two agree on which run is newest, two that ended in the same
  second included. `latest_run_from_store` reads the store once and works
  out both the card's run and the newest run on any scenario from that copy.
- It is judged exactly as before: against the PB it was chasing, under its
  own version of the scenario, with the same badge, percentage, caps and
  accuracy. Every rule of the
  [2026-10-12 card section](2026-10-12-a-past-runs-check-is-judged-against-the-pb-it-was-chasing-under-its-own-version.md)
  about a run's marks and its second line stands.
- **A late run reaches the card by the selected scenario's latest,** not the
  store's newest. A run on the selected scenario newer than its latest run
  becomes the card's run, even when it is older than the store's newest, such
  as one copied into the stats folder late. One older than the scenario's
  latest leaves the card's run as it is.
- The scenario's name on the first line is always plain text, with the whole
  name as its title where the card cuts it short.

**The third line becomes two.**

- The newest session keeps its words: `Run {n} this session` while it is in
  progress, `Run {n} last session` once it has ended.
- An older session is named as the run list names its row, by when its first
  run began, with `format_short_timestamp`: `Run 7 (Oct 16, 2:00 PM
  session)`, or with the year where it is not this one, `Run 8 (Jul 20, 2020,
  11:47 PM session)`. The parentheses are the maintainer's wording. "Session"
  stays inside them, or the time would read as the run's own. The year is
  judged against the server's date, as the run list's is.
- The time spent on the scenario takes a line of its own in every form:
  `{duration} on this scenario`, or `Time on this scenario unknown`. The
  maintainer could go either way, and the author chose it because, with a
  benchmark selected and the PB card's leaderboard line on one line, it lines
  the card's score up with the PB card's: 2 px apart, where one line left 12.
  With no benchmark the PB card has one line fewer, and the run's score sits
  8.5 px above the PB's. Both cards center their own lines, so the offset
  follows the PB card's state and is not a rule the app holds: with no
  KovaaK's username the leaderboard line's hint takes two lines, and the run's
  score sits 24 px below the PB's. One line also fit:
  the longest real line, 70 characters, took 373 of 474 px.
- `{n}` is still the run's number among the scenario's runs in that session,
  and the time still the sum of the scenario's visits in it.
- `_session_lines` returns the two parts apart, and the card draws each as a
  line in its session style.

**The empty states.** Each opens on a quiet first line that reads `Latest
run` alone, as the PB card's open on `PB`. The card's name is plain text in
the heading's one item, and only the span that holds the age is hidden with no
run, so `AGE_SCRIPT`, which both cards register, hides the same kind of span
on each.

| When | The card reads |
|---|---|
| No scenario is selected, and the store has no runs | "No runs yet" over "Play a scenario in KovaaK's. Select it to see its latest run." |
| No scenario is selected, and the store has runs | "No scenario selected" |
| The selected scenario has no runs, whether or not the store has any | "No runs yet" over "Play this scenario in KovaaK's and your latest run will show here." |

- **The selection decides first, as on the PB card.** A playlist filter lists
  its scenarios before any is played, so a scenario can be selected in a store
  with no runs, and the card then speaks of it.
- **"Play this scenario" holds with Follow off.** Playing the selected
  scenario keeps it selected, and a different scenario would not show here.
- **With nothing selected and no runs, the sentence says to select the
  scenario played.** With Follow off a first run leaves the selection empty,
  and the card then reads "No scenario selected", so "your latest run will
  show here" would promise what the card does not do. With Follow on, the
  default, the run's scenario is selected as it lands.
- `latest_run_card_content` takes whether the store has runs as its third
  argument, from the newest run's id `show_latest_run` already works out: the
  card's run alone is `None` both with nothing selected and with no runs for
  the selection.

**When it is written.** On today's triggers, plus the date moving on: a run
landing on any scenario, a change of scenario, the Score threshold
percentage, the newest session ending, and the page's date store. A run on
another scenario can change the third line's words without changing the run:
a new session makes the old one "last" or older. The date store is read for
nothing but its change, as the run list's rows read it, because an older
session's name leaves its year out only while it is this year's: a page left
open over New Year's would otherwise keep `Dec 31, 2:00 PM session` with no
year.

**What stays.** The chart's ring and the run list's highlight still mark the
last run played on any scenario, so during a lookup they leave the selected
scenario: that says the card's run is not the one just played. The store the
page writes for them stays the newest run overall, from the same copy of the
store as the card. The run toast, the celebration and Follow are unchanged.

**The Show {scenario} button goes,** with everything that served it: its
`Show {scenario}` accessible name, the script that handed keyboard focus to
the Selected scenario dropdown after a press and the store it wrote, its
`Input` and `State` on the selection callback, and that callback's
`_button_was_clicked`. The selection callback keeps three callers: a link's
parameters, a followed run, and a name pressed in the run list's All
scenarios view. A scenario is still chosen on the page with the dropdown,
with Follow and a run, or with a name in the All scenarios view, and from
elsewhere with the run toast's link or a playlist table's scenario link.
What is lost is the half-follow with Follow off: a run on another scenario no
longer reaches the card. It shows in its run toast, whose link selects it,
and in the All scenarios view. With Run notifications also off, the page
shows it only in small ways: the first session row counts it, and the ring
and the highlight leave the selected scenario's run.

**Set aside.**

- **A clicked run in the card (case 3).** A past run's percentage is against
  the PB of its day, so a run of 3,181 would read "94.8% of PB" beside a PB
  card showing 3,653, and it needs rules for what selects a run and what ends
  the selection. Later or never.
- **Dimming the card when its run is another scenario's.** It keeps the
  half-follow, but still sets two scenarios' scores side by side, and Last
  played could not go.
- **The last run on any scenario with nothing selected.** The maintainer's
  answer of 2026-10-14, dropped for simplicity.
- **`Run 7 (latest session)` for the newest session,** which cannot say
  whether the session is still going, and naming the newest session by its
  time too, which is harder to read during play than "this session".
- **Today's sentence for a store with no runs,** true only with Follow on, and
  a sentence that changes with the Follow switch, which would make the switch
  one of the card's triggers for a state a new user sees once.

**The card's floor rises from 132 px to 135 px,** a correction the
implementation made and the proposal did not foresee. The card is never less
than its tallest state, so its height never follows a run
([2026-10-12](2026-10-12-a-past-runs-check-is-judged-against-the-pb-it-was-chasing-under-its-own-version.md)).
With the fourth line, that state, the second line on two lines in a card
380 px wide, measures 135 px in Edge and Firefox, so the old floor would
have let the card grow by 3 px for such a run in a narrow window. The wide
layout is unchanged, since the row is 141.4 px there.

**Measured at the build,** against `main` at `69fd722` on the maintainer's
stats (9,212 runs), headless Edge and Firefox, light and dark, at 3840, 2560,
1920 and 1536 px, in eight states: the top row is as tall as on `main` in
every one, 141.4 px from 1920 up. The card's text is 113 to 114 px where it
was 93 to 94, in a card 141.4 px tall, and no card's text leaves its card. A
first run landing in an empty scratch stats folder while the page was open
was checked with Follow off and on, with nothing selected and with a
playlist's unplayed scenario selected. The PR's description has the tables.

**What this changes in older entries.** Each keeps its text and gains a dated
note.

- [2026-10-12, a past run's check](2026-10-12-a-past-runs-check-is-judged-against-the-pb-it-was-chasing-under-its-own-version.md):
  its section on the latest-run card, which reported the last run on
  whatever scenario and had the scenario button, and its sentence that a run
  landing older than the store's newest leaves the card alone.
- [2026-10-12, Follow and a scenario link clear the filter](2026-10-12-follow-and-a-scenario-link-clear-a-playlist-filter-that-does-not-list-the-scenario.md):
  the card's button as one of the selection callback's inputs.
- [2026-10-14, a card's lines follow their role](2026-10-14-a-cards-lines-follow-their-role-in-the-players-next-action.md):
  its closing paragraph, which kept the card on the last run played during a
  lookup and left changing that to a separate proposal. This is that
  proposal.

Proposed in
[#388](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/388),
which merged as `69fd722`, with
[the Scenario Stats entry](2026-10-18-last-played-leaves-scenario-stats-and-its-first-line-is-plain-text.md)
and [the run list's heading line](2026-10-18-the-run-lists-heading-line-is-for-screen-readers-only.md).
The proposal file, `docs/proposals/latest_run_card_follows_selection_proposal.md`,
is deleted, and git history keeps it.
