# Top Row Cards Proposal

Status: Proposed
Date: 2026-10-14

## TL;DR

Run History's top row says nothing about the target a player is chasing: the
personal best shows only as a line on the chart, and the latest-run card
spends most of its width on empty space. This proposal stacks the two
dropdowns in one column and gives the row one card per kind of information:
the scenario, its personal best, and the latest run, with the latest-run card
lined up over the run list. The new PB card leads with the PB score and the
gap to the next rank, and takes over the leaderboard position, while the
Scenario Stats card gains the scenario's benchmark category. At the
maintainer's width the row stays exactly as tall as it is today.

## Decisions needed

Four rows: T1 to T4. **Nothing is ratified.** The one ruling that binds this
design is the maintainer's resolution priority of 2026-10-14, which it treats
as a constraint (see [What the maintainer needs](#what-the-maintainer-needs)).
Each row is the maintainer's lean from the design discussion of 2026-10-14,
worked out on nine versions of a full-size mockup built from their own stats.
A lean is not a ruling: every row, and every premise in Problem, is open to
challenge. Everything else is author-owned, in [Design](#design).

This is the first of two proposals from that discussion. The second, the
latest-run card following the selected scenario and the run list losing its
heading line, is written after this one ships, because its argument rests on
T1's alignment.

### T1. The row's layout: stacked dropdowns, a card per group, the latest-run card over the run list

Status: Proposed. The maintainer's lean, 2026-10-14. The stacking and the
alignment are their ideas: "Stacking the selects does seem to free up a ton
of space", and the latest-run card "should be aligned with the Run History
panel on the right", which "isn't necessarily a requirement". Of the layouts
mocked: "I think F looks the best", then "v8 is looking the best so far".

The material consequence: the top row is rebuilt. The two dropdowns move
into one column, the latest-run card changes width and place, and the
Scenario Stats block becomes a card.

**Recommendation: lay the row out as two columns, the same two the chart and
the run list use below it. The left one holds, in order, the two dropdowns
stacked in one column, the Scenario Stats card, empty space kept for notes,
and the PB card (T3). The right one, 500px wide, holds the latest-run card,
directly over the run list.**

- **The latest-run card is mostly empty space today.** At 2560 px it is
  1,167 px wide and its text takes about 300 px. Lined up over the run list it
  is 500 px, and its edges meet the list's at every zoom level, because the
  two share one column.
- **Stacking the dropdowns frees about 400 px.** It is what lets every card
  fit on one line at the maintainer's width. With the dropdowns side by side
  (mocked as layout E), the row grows by 74 to 94 px at 1920 px.
- **The row stays one height.** The stacked column is the tallest piece, and
  it fits in today's 132 px because the **Open scenario table** link moves up
  onto the **Playlist filter** label's line, and the **Follow newly played
  scenario** switch onto the **Selected scenario** label's line, where that
  line has room. At 2560 px and 3840 px the row is 132 px, exactly as today.
- **The PB card sits at the right end of the left column,** beside the
  latest-run card: they hold the two numbers a player compares after every
  run, the target and the result.
- **The space between the Scenario Stats card and the PB card is kept for
  notes,** a later proposal. Until then it is empty, with no element in it.
  The maintainer: "gap is fine."

Rejected: the dropdowns side by side with the card lined up (layout E); the
note card between the PB card and the latest-run card (layout F); the
latest-run card filling the rest of the row (today); the note in the space
beside the latest-run card (layouts C and D).

### T2. The Scenario Stats card: Category, Last played, Number of runs

Status: Proposed. The maintainer's lean, 2026-10-14. They asked for the
category ("when I'm grinding a benchmark, it sometimes helps to know the name
of the category and subcategory that this scenario is in") and kept Last
played: "The Run History page also serves as a tool to get information about
past runs." On a row with no benchmark: "perhaps hiding the row is fine."

The material consequence: Position leaves this card for the PB card (T3), and
the card gains a Category row while a benchmark is selected.

**Recommendation: the Scenario Stats card is about the scenario itself and
the player's history with it. It holds, in order, Category, Last played, and
Number of runs, at one weight. Category reads the selected scenario's
category and subcategory in the benchmark the Playlist filter holds, and the
row is hidden when the filter holds no benchmark or the benchmark has no
groups.**

- **The Playlist filter makes the category exact.** Of the 3,240 scenarios in
  the bundled benchmarks, 688 are in more than one benchmark, one of them in
  11, so a scenario alone does not name a category. No scenario appears twice
  in one benchmark, so the benchmark the filter holds does.
- **A hidden row, not a placeholder.** A row that only says why it is empty
  is noise, and the rank overlays already need a benchmark selected in the
  same way.
- **Last played stays.** During play, with Follow on, it reads a minute ago,
  but the page is also where a player looks a scenario up before playing it.
- **Number of runs stays until time is defined.** A total time on the
  scenario was considered and deferred: how runs become time is decided once
  for the whole app (see [Out of scope](#out-of-scope)).

Rejected: removing the card and spreading its facts elsewhere (layout G); the
category as a line under the scenario dropdown, which cost 12 px of row
height; a "No benchmark selected" row.

### T3. The PB card

Status: Proposed. The maintainer's lean, 2026-10-14, built up over the
discussion: the original ask ("PB score, PB accuracy, etc. Make it
immediately clear what our target is at all times"); "PB Stats should at
least include cm/360 since I often refer to it when I am training";
"Position belongs with PB Card"; the percentile at a glance ("percentile
mostly, but position sometimes"), at two decimals as today; the next rank as
a percentage, "so it matches how it is displayed on Playlist Scenarios
page"; accuracy on the faded line ("Accuracy line confirmed").

The material consequence: the personal best gets its own card in the top
row, and the leaderboard position moves into it, out of the Scenario Stats
card.

**Recommendation: a PB card for the selected scenario, its lines in this
order:**

1. **`PB · set {time}`,** the time the PB was set.
2. **The PB score, large,** with the current rank as a badge while a
   benchmark is selected. Hovering or focusing the score gives the line the
   latest-run card showed when this PB landed, such as `Up 2.5% on your
   previous best of 11,934`.
3. **The next rank, worded as the benchmark table's Next Rank cell:**
   `+1.3% to Lavender`, or `+2.8% faster to Lavender` on a time-scored
   scenario, or `Top rank`. Hovering gives the cell's own tooltip, `Lavender
   at 3,700 · 47 to go`. Shown only while a benchmark is selected.
4. **The percentile, `81.13% percentile`,** with **Refresh** right after it.
   Hovering gives `Position 5,400 of 28,614` over the existing `Last updated
   {age} · {timestamp}`. Without a percentile, the line is today's Position
   field: `Position: Unranked (12,345 players)`, or `Position: N/A · set your
   KovaaK's username in Settings`.
5. **`50 cm/360 · Accuracy 61%`, faded:** the PB run's sensitivity and
   accuracy.

- **It answers the target question at a glance.** The score, the rank it
  holds, and how far the next rank is are the first three lines.
- **Position is where the PB ranks.** The leaderboard places a player's best
  score, so the position belongs with the PB. It already updates on its own
  after every new PB.
- **The percentile is what the maintainer checks against the game.** KovaaK's
  shows `Percentile: 81.1` for a position of 5,400 among 28,614 entries; the
  app works it out with the same formula and shows `81.13`.
- **The next rank's percentage is the only honest gap on a time-scored
  scenario.** On Ground Plaza Sparky V3, points would read `2.83 to go`, which
  is seconds, while the table already reads `+2.8% faster to Lavender`. One
  fact gets one wording across the app.
- **cm/360 answers "what sens should I use".** In each of the 11 recent
  scenarios the maintainer has played at two or more sensitivities, the PB's
  sensitivity is also the one they play most and the one with their best
  three scores (see [Verified facts](#verified-facts)).
- **Refresh stays beside the value it refreshes.** In the card's heading it
  would read as refreshing the whole card, and the card does not widen for it:
  the percentile line with Refresh is about 229 px in a card with 274 px of
  room.

Rejected: PB rows in the Scenario Stats block (layout A); the PB as the
Scenario Stats card's big number with the note inside (layout B); the next
rank in points at a glance; the PB's accuracy on hover; Refresh in the card's
heading; a wider card to hold `Position: 639 of 12,190 (94.76% percentile)`
and Refresh on one line.

### T4. How a card orders and weights its lines

Status: Proposed. The maintainer's lean, 2026-10-14, like every row here,
and open to challenge. The order rule is their idea: "within a card, the
information should be displayed by order of importance. For example: '50
cm/360' is low priority, so it should probably go towards the bottom of the
card and/or even slightly faded." The tiers it rests on are theirs, from the
Run History brainstorm. Neither is a ruling. Amended after the first review
wave: a fact's role in the player's next action decides its order and its
weight, and how often it changes decides neither.

The material consequence: a rule later cards in this row follow too,
including the note card.

**Recommendation: in the top row's cards,**

- **lines go in order of their role in the player's next action,** the most
  important first;
- **a fact needed at a glance, with no hand on the mouse, is on screen;**
  optional explanation and history go on hover and focus, as the position,
  the previous best, and the next rank's points do;
- **a fact that supports another comes after it, in a quieter but readable
  style,** as cm/360 and the accuracy support the PB;
- **a card with no lead fact lists its facts at one weight,** in order of
  importance, as Scenario Stats does;
- **in this layout only the two scores are large,** the PB card's and the
  latest-run card's. That is this layout's choice, not a rule for later
  cards.

- **How often a fact changes decides neither its order nor its weight.** The
  rule holds against four cases. A training note can stay the same for weeks
  and still be the reason to look at the page, so it is on screen at full
  weight. A next-rank threshold can stay the same for weeks and is the goal,
  so it is on screen near the top of the PB card. A time that changes with
  every run, such as when the latest run was played, is context, so it sits
  in a card's quiet first line. Scenario Stats has no lead fact, so its three
  lines are at one weight, Category first.
- **cm/360 and the accuracy are quiet because they support the PB,** not
  because they rarely change.
- **Two large scores make the row's comparison obvious** while both cards are
  about the same scenario, as during play with Follow on. During a lookup the
  latest-run card can show another scenario, as it does today.

Rejected: how often a fact changes setting its emphasis; static facts on
hover; one large score as a rule for every later card.

## Problem

### What the top row shows today

The [top row](../specs/run_history.md#the-top-row) holds the Playlist filter
with **Open scenario table** under it, the Selected scenario dropdown with
the **Follow newly played scenario** switch under it, the
[Scenario Stats](../specs/run_history.md#scenario-stats) block (Last played,
Number of runs, Position and **Refresh**), and the
[latest-run card](../specs/run_history.md#the-latest-run-card), which fills
the rest of the row
([2026-10-12](../decision_log/2026/2026-10-12-the-run-list-is-a-second-column-beside-the-chart.md)).
The row is 132 px tall, the latest-run card's fixed height.

- **The personal best is not on the row.** The Run History spec says so in so
  many words: "The personal best appears on the chart as the PB score overlay,
  not as a stats row." That line can be turned off, and the latest-run card
  gives only a percentage of the PB, and only for the last run played.
- **The next rank is on another page.** The benchmark table has a Next Rank
  column
  ([2026-09-27](../decision_log/2026/2026-09-27-benchmark-tables-show-each-scenarios-rank-and-the-gap-to-the-next-one.md));
  Run History draws the rank thresholds as lines on the chart.
- **The category is on another page.** The benchmark table draws the groups
  ([2026-10-06](../decision_log/2026/2026-10-06-benchmark-scenario-tables-group-scenarios-by-category-and-subcategory.md)).
- **The latest-run card is mostly empty.** It is 1,167 px wide at 2560 px,
  with about 300 px of text.

### What the maintainer needs

These are the maintainer's, stated during the design discussion of
2026-10-14. A reviewer may say one is wrong or missing.

- **Three Backlog asks started it.** PB info in Scenario Stats ("Make it
  immediately clear what our target is at all times"), the category and
  subcategory while grinding a benchmark, and user notes on a scenario, which
  are a later proposal.
- **Two uses of the page.** During play, glanced at between runs on a second
  monitor with Follow on. And as a lookup: "before I play Scenario B, I might
  manually swap to Scenario B, so I can look at its stats or notes."
- **Three tiers.** Tier 1 is read at a glance, tier 2 takes a click or a
  hover, tier 3 is another page. Tier 1 stays small to avoid information
  overload.
- **The target, the sensitivity, and the percentile** are what they look up
  most: the PB and the next rank, the PB's cm/360, and the percentile to check
  against the game.
- **Resolution, ruled 2026-10-14:** "support my own resolution (4K) first and
  foremost, with 1440p resolution second. I'll support 1080p only if it
  doesn't affect the other two resolutions." Their 4K runs at 150% scaling,
  so the page is 2560 CSS px wide, the same as 1440p at 100%.
- **Smaller proposals:** "easier to debate on and faster to ship." Hence two
  proposals, and notes and the PB jump left to their own.

### Verified facts

Measured 2026-10-14 at `c827a62` against the maintainer's stats folder, with
headless Edge at the widths named.

- **Today's row:** 150 px tall in the app with no username set, at 1600 px
  and 2560 px, where the Position hint takes two lines. With a username set it
  is the latest-run card's 132 px, as the mockup's copy of today's row
  measures. The latest-run card is 425 px wide at 1600 px and 1,167 px at
  2560 px.
- **The proposed row, as mocked** (layout H of the ninth mockup, with nothing
  in the note space; the top row's height in px, so the chart starts that
  much lower than today):

  | Width | Today | Proposed |
  |---|---|---|
  | 3840 | 132 | 132 |
  | 2560 | 132 | 132 |
  | 2327 (2560 at 110% zoom) | 132 | 132 |
  | 2048 (2560 at 125% zoom) | 132 | 149 |
  | 1920 | 132 | 149 |
  | 1707 (2560 at 150% zoom) | 132 | 149 |
  | 1536 | 132 | 267 |

- **Categories:** 265 bundled benchmarks, 3,240 distinct scenario names, 688
  in more than one benchmark (at most 11), none twice in one benchmark.
- **Sensitivity:** 24 scenarios played in the last 60 days with 15 or more
  runs in all; 11 of them played at two or more sensitivities; in all 11 the
  PB's sensitivity is the one played most in those 60 days and the one with
  the best mean of its top three scores.
- **The next rank, from the table's own code** (`benchmark_rank_fields`):
  VT Controlsphere Viscose reads `+1.3% to Lavender` with the tooltip
  `Lavender at 3,700 · 47 to go`; Ground Plaza Sparky V3, time-scored with a
  constant of 1,000, reads `+2.8% faster to Lavender` with `Lavender at 899 ·
  2.83 to go`.
- **The percentile:** `calculate_percentile` is KovaaK's midpoint,
  `(total − position + 0.5) / total × 100`. For 5,400 of 28,614 it gives 81.13;
  the game shows 81.1.
- **The position updates itself** after a new PB, with a bounded background
  refresh ([scenario_rank.md](../specs/scenario_rank.md#refresh-behavior)).

### Not checked

- Firefox. The mockups were checked in headless Edge; the maintainer reads the
  page in Firefox.
- A screen reader on the new cards.
- The zoom level at which the run list moves above the chart: estimated at
  about 220% of a 2560 px window, from the 900 px rule.

## Design

### The row at a glance

```
| Playlist filter    Open scenario table | Scenario Stats   |  (space kept   | PB · set Oct 9, 5:24 PM | Latest run · Oct 9, 10:03 PM · ... |
| [Viscose Benchmark S2 - Medium      ]  | Category: ...    |   for notes)   | 3,653  [Cerulean]       | 103  [New PB]                      |
| Selected scenario  (o) Follow newly... | Last played: ... |                | +1.3% to Lavender       | Up 1.0% on your previous best ...  |
| [VT Controlsphere Viscose           ]  | Number of runs:  |                | 94.76% percentile  Refresh | Run 1 last session · 1 min ...   |
|                                        |                  |                | 50 cm/360 · Accuracy 61%|                                    |
```

The row is two columns, `minmax(0, 1fr)` and 500 px, with the gap of the
columns below, so the latest-run card's edges are the run list's. The left
column is a wrapping row of four pieces: the dropdown column, the Scenario
Stats card, the note space, and the PB card, pinned to its right end. Every
card is as tall as the row.

### The dropdown column

- **It holds the Playlist filter over the Selected scenario dropdown,** each
  at the full width of the column, which grows from 260 px to 420 px with the
  room the row has.
- **Open scenario table sits on the Playlist filter label's line,** at its
  right end, while a playlist is selected. Its rule is unchanged: there is no
  link, and no room held for one, with the filter empty.
- **The Follow switch sits on the Selected scenario label's line,** at its
  right end, when the column is wide enough to hold the label and the switch
  on one line, and under the dropdown when it is not. The column's own width
  decides, not the window's
  ([2026-08-03](../decision_log/2026/2026-08-03-homes-controls-row-measures-the-content-area-not-the-window.md)).
  It stays with the scenario dropdown either way, since it governs selection
  ([2026-08-09](../decision_log/2026/2026-08-09-chart-options-live-in-a-collapsible-panel-beside-the-graph.md)).
- Every behavior of the two dropdowns and the switch is unchanged: what they
  list, what they remember, and how a link, Follow, and the card's scenario
  button set them.

### The Scenario Stats card

- **Its heading stays `Scenario Stats`**, now at the top of a card drawn as
  the latest-run card is. It has no lead fact, so its lines are at one
  weight, as today's rows are (T4).
- **Category** (T2) reads `Category: {category} · {subcategory}`, or
  `Category: {category}` for a benchmark with one level, the names as the
  benchmark table labels its groups. It is the first row, and it is there
  only while the Playlist filter holds a benchmark that groups its scenarios
  and lists the selected scenario. A benchmark on the table's exclusion list
  has no groups, so it has no Category row.
- **Last played and Number of runs are unchanged,** with their empty states:
  `—` with no scenario selected, `Never` for a scenario with no runs
  ([2026-06-30](../decision_log/2026/2026-06-30-model-home-last-played-empty-states-explicitly.md)).
- **Position leaves the card** for the PB card.
- **The card is about 270 px wide,** its longest line being the category.

### The PB card

About 300 px wide, its five lines as T3 lists them. Each line follows a rule
that exists today, so the card computes nothing new:

| Line | Source | States |
|---|---|---|
| `PB · set {time}` | The PB run, as `get_personal_best_run` finds it (the earliest run to reach the high score) | The time as the latest-run card words it: `10:50 PM` today, `Oct 4, 10:50 PM`, `Dec 30, 2025, 10:50 PM` |
| The score and badge | `format_score`; the badge is the Rank the table would show | No badge below the first threshold, with no benchmark selected, or for a scenario the benchmark has no ladder for |
| The next rank | `benchmark_rank_fields(ladder, PB, pace constant)`, the table's own function, with the pace constant as the table chooses it | Hidden with no benchmark selected, with no ladder, and where the cell would read `N/A` |
| The percentile | The Position field's `ScenarioRankInfo`, as today | See below |
| cm/360 and accuracy | The PB run's normalized sensitivity string, as the run list's Sensitivity column; `format_whole_percent` of its accuracy | Always shown while there is a PB |

**The percentile line.** It is today's Position field, moved, with the
percentile leading:

- **Ranked with a total:** `{percentile}% percentile`, two decimals, with the
  dotted underline. Hovering or focusing it gives `Position {position} of
  {total}` over today's `Last updated {age} · {timestamp}`
  ([2026-10-04](../decision_log/2026/2026-10-04-the-position-value-says-when-it-was-last-updated.md)).
  A value served from cache keeps its ` · from cache` hint.
- **Every other state reads as the Position field does today,** with its
  label: `Position: {position}` with no total, `Position: Unranked
  ({n} players)`, `Position: N/A · set your KovaaK's username in Settings`,
  `Position: N/A · lookup failed`
  ([scenario_rank.md](../specs/scenario_rank.md#failure-handling)).
- **Refresh follows the value on the same line,** with its tooltip, its
  toasts, its loading delay, and every rule in
  [scenario_rank.md](../specs/scenario_rank.md) unchanged.
- **The username hint takes two lines** in a 300 px card, so in that state
  the card, and the row, are a line taller. It is a setup state, not a
  change between runs; the implementation measures it and reports the height.

**The score's hover** repeats the latest-run card's line for a new PB, word
for word: `Up {pct}% on your previous best of {previous}`, `{pct}% faster than
your previous best of {previous}` by pace, or `Your previous best was
{previous}` over a previous best of zero or less
([2026-10-12](../decision_log/2026/2026-10-12-a-past-runs-check-is-judged-against-the-pb-it-was-chasing-under-its-own-version.md)).
A PB set by the scenario's first run has no previous best, so the score has
no hover and no dotted underline.

**Empty states.** With no scenario selected the card reads `Select a
scenario to see its PB.` A scenario with no runs reads `No PB yet` over
`Your first run on it sets one.`, as the latest-run card shows its own empty
state. Both keep the card's height.

**A time-scored scenario** shows its PB as a score, as everywhere: no
completion time is shown anywhere
([2026-10-05](../decision_log/2026/2026-10-05-time-scored-scenarios-are-measured-by-pace.md)).
Its next rank and its score's hover read by pace where the table and the
latest-run card do.

**A mismatch with the leaderboard is accepted.** KovaaK's ranks the best
score its server holds, which can differ from the local PB, for example after
runs on another computer. Position already rests on cached reads, and
reconciling the two is a shelved item. The spec says so.

### The note space

Empty space between the Scenario Stats card and the PB card, with no element
in it, so a narrower window can use it. The notes proposal decides what fills
it.

### The latest-run card

Its place and width change (T1); nothing it says does. It reports the last run
played on whatever scenario, with its **Show {scenario}** button, as the
[spec](../specs/run_history.md#the-latest-run-card) says. Its height becomes
the row's, which is 132 px at 2560 px as today; its lines stay centered.

### When the cards change

- **Every run that lands on the selected scenario** rebuilds the PB card, as
  it rebuilds the chart, whether or not it sets a new PB. A new PB moves the
  score, the badge, the next rank, the time, the faded line, and the hover
  together. A run that sets none can still change the next rank's wording:
  the pace constant follows the scenario's newest version and the first
  performance file that can tell, so a run of a new version, or the first
  file that recognizes a time-scored scenario, turns `+2.8% faster to
  Lavender` into the score's `+0.4% to Lavender`, or back. The position
  follows when the background refresh it already triggers stores a new one.
- **A new scenario or playlist** rebuilds both cards. The Playlist filter
  alone changes Category, the badge, and the next rank.
- **The position's poll and Refresh** write the percentile line, as they write
  the Position field today.

### Narrow windows and zoom

The resolution ruling makes 2560 px the design width; 1920 px and narrower
only have to not break.

- **Below the room for everything,** the left column's pieces wrap in order,
  so the PB card goes to a second line of the left column first. The
  latest-run card stays in the right column.
- **At a page area of 900 px or narrower,** where the run list moves above the
  chart ([narrow windows](../specs/run_history.md#narrow-windows)), the row
  becomes one wrapping line again, in order: dropdowns, Scenario Stats, PB,
  latest run.
- **Zooming in is a narrower window.** At 110% the row is unchanged; at 125%
  and 150% the Follow switch drops under the dropdown and the row is 149 px.

### Keyboard and screen reader

- **The cards are not landmarks or buttons.** `Scenario Stats` stays a
  heading. The PB card's first line is text, as the latest-run card's is.
- **Every hover is also a focus,** as Last played's and Position's are today:
  the dotted score, the next rank, and the percentile take focus and show their
  tooltips, with the existing tooltip events.
- **The order a screen reader reads** is the visual order: dropdowns, Scenario
  Stats, PB, latest run, then the chart's controls.
- **The rank badge** keeps the page's text color on a tint of the rank's color,
  with a border in that color, so a pale rank such as Lavender stays legible
  in both themes.

### Light and dark

Every card uses the theme's tokens, as the latest-run card does. The rank
colors come from the benchmark files and are the only fixed colors; the badge
above keeps them legible.

### How it is built

- **The Scenario Stats block's module becomes the card,** and loses the
  Position field to a new PB card component beside it. Both keep the
  page-ids pattern `ScenarioStatsIds` uses, so a page passes its own ids.
- **The PB card's text is built by one pure function** from the store, as
  `latest_run` builds the latest-run card's, so it can be tested without a
  page.
- **The next rank calls `benchmark_rank_fields`,** and the pace constant comes
  from `eligible_pace_constant(get_pace_basis(scenario), pb_run)`, as the
  table chooses it.
- **Category comes from `get_scenario_groups(playlist_code)`,** indexed by the
  scenario's place in that playlist.
- **The two-column row** reuses the run list's column width, so one constant
  sets both.

### Copy

Every string this proposal adds or changes. They follow the nine copy rules
in [AGENTS.md](../../AGENTS.md#styling-conventions). A string the page has
today and this proposal does not name is unchanged.

| Where | String | Why |
|---|---|---|
| Scenario Stats card, Category row | `Category:` then `{category} · {subcategory}`, or `{category}` | A label as `Last played:` is; the two names chained as a readout, as the table's group labels write them. |
| PB card, first line | `PB · set {time}` | A readout, as the latest-run card's first line. "Set" says what the time is. |
| PB card, rank badge | `{rank name}` | The ladder's own name, as the table's Rank column. |
| PB card, next rank | `+{gap}% to {rank name}`, `+{gap}% faster to {rank name}`, `Top rank` | The table's Next Rank cell, word for word. |
| PB card, next rank hover | `{rank name} at {threshold} · {points} to go` | The cell's tooltip, word for word. |
| PB card, percentile | `{percentile}% percentile` | Today's value without its parentheses, now leading the line. |
| PB card, percentile hover, first line | `Position {position} of {total}` | The position as a readout, over the existing `Last updated` line. |
| PB card, the line without a percentile | `Position: {value}`, with today's values and hints | Today's field and its label, unchanged. |
| PB card, faded line | `{sensitivity} · Accuracy {accuracy}%` | The run list's sensitivity string and the latest-run card's accuracy, chained. |
| PB card, score hover | `Up {pct}% on your previous best of {previous}`, `{pct}% faster than your previous best of {previous}`, `Your previous best was {previous}` | The latest-run card's new-PB lines, word for word. |
| PB card, no scenario | `Select a scenario to see its PB.` | A sentence saying what to do. |
| PB card, no runs | `No PB yet` over `Your first run on it sets one.` | A title over one sentence, as the latest-run card's empty state. |

Kept as today, word for word: `Playlist filter`, `Open scenario table`,
`Selected scenario`, `Select a scenario`, `Follow newly played scenario` and
its help tooltip, `Scenario Stats`, `Last played:`, `Number of runs:`,
`Refresh` and its tooltip, every Position value and hint, and every string of
the latest-run card.

### Terms

Each entry is written as [docs/glossary.md](../glossary.md) would hold it,
under "The Run History page". The implementing PRs move them in.

New entries:

- **PB card.** The card in Run History's top row about the selected
  scenario's personal best: its score and rank, the gap to the next rank, the
  player's leaderboard percentile, and the PB run's sensitivity and accuracy.
  - On screen it has no title. Its first line reads `PB · set {time}`.
- **Scenario Stats.** The card in Run History's top row about the selected
  scenario: its benchmark category, when it was last played, and how many runs
  it has.

Entries the same PRs correct:

- **Latest-run card** calls it "The panel at the top of Run History". It
  becomes "The card at the right end of Run History's top row, over the run
  list".
- **Position** gains: "On Run History it is in the PB card, under the
  percentile."

### Decisions this changes

The implementing PRs keep each entry and add a dated "Superseded in part"
note. They erase nothing.

- [2026-10-12, the run list is a second column](../decision_log/2026/2026-10-12-the-run-list-is-a-second-column-beside-the-chart.md)
  set the top row's order with the latest-run card filling the rest of the
  row. T1 replaces that order.

### Alternatives rejected

Seven layouts were mocked before this one, each at full size from the
maintainer's stats, in light and dark.

- **A:** PB, rank and category as rows of the Scenario Stats block, the note
  as a strip under the row. The strip spans too wide, and the rows grow the
  row by 43 px with nothing in the strip.
- **B:** the Scenario Stats block as a card whose big number is the PB, the
  note inside it. Position squeezed into one short line; the latest-run card
  stretched with blank space.
- **C and D:** the note in the space beside the latest-run card. It fits at
  2560 px and costs a full line at 1600 px.
- **E:** the latest-run card lined up, the dropdowns side by side. A second
  line at 1920 px.
- **F:** this layout with the note between the PB card and the latest-run
  card, splitting the two numbers a player compares.
- **G:** no Scenario Stats card, its facts spread elsewhere. Last played
  matters for looking a scenario up.

## Delivery plan

Three implementation PRs. This is intent, not a contract: a boundary that
moves is noted in that PR's description. Each PR changes a public page in its
release.

1. **The layout.** The two-column row, the dropdown column with the link and
   the switch on the labels' lines, the Scenario Stats block as a card with its
   content unchanged (Position still in it), the latest-run card over the run
   list, the note space, and the narrow-window rules (T1, and T4 for the
   cards' frame).
   - **Measures and reports** the row's height at 3840, 2560, 1920, and 1536 px,
     in light and dark, and that the card's edges meet the run list's.
2. **The PB card** (T3, T4). The new card, with Position, its hints, its
   hover and **Refresh** moved into it from the Scenario Stats card.
   - Updates [scenario_rank.md](../specs/scenario_rank.md), whose Position
     field it moves.
3. **Category** in the Scenario Stats card (T2).

PR 1 goes first. PRs 2 and 3 each need PR 1 and not each other. The last of
them to merge ships the proposal, by the
[Shipping a proposal](../../AGENTS.md#shipping-a-proposal-docs-definition-of-done)
checklist: a decision-log entry for each row, the note in
[Decisions this changes](#decisions-this-changes), the Run History and
scenario rank specs, the glossary's entries in [Terms](#terms), the user
guide, `architecture.md`, the roadmap, `product.md`, and this file deleted.

**Recommended:** `claude-opus-5-5`, at xhigh for PR 2, which moves the
Position field with its many states, and at high for PRs 1 and 3. The
maintainer looks at each in their own Firefox before it merges.

### Fallbacks

- **PR 2 grows too large.** Move Position into the PB card first, then add the
  PB's own facts.
- **T3 is not settled when T1 is.** PR 1 ships alone; the row then has the
  Scenario Stats card, the note space, and the latest-run card until the PB
  card follows.

## Out of scope

- **The latest-run card following the selected scenario, and the run list
  losing its heading line.** The second proposal, written after this one
  ships.
- **Notes on a scenario.** A later proposal: a new durable store and an
  editor. This one keeps their space.
- **A jump from the PB card to the PB run in the list.** Its own proposal or a
  small PR, once the PB card exists.
- **Time played on a scenario.** How runs become time is decided once for
  every page, Home included (Backlog).
- **Detecting restarts,** which write no stats file (Backlog).
- **Inferring the benchmark** when no playlist is selected and the scenario is
  in exactly one shown benchmark: an idea, not proposed.
- **The percentile's decimals across the app:** unchanged, two.

## Testing

- **Unit, the PB card's text:** a table of cases through the pure function:
  a PB with and without a benchmark; below the first rank; at the top rank; a
  time-scored PB with a pace gap and with none; a PB of zero or less; a PB set
  by the first run; no runs; no scenario; each Position state, including
  served from cache and the unset username.
- **Unit, Category:** a benchmark with two levels, one level, no groups, on
  the exclusion list; a playlist that is not a benchmark; a scenario the
  playlist does not list.
- **Callbacks:** every run on the selected scenario rebuilds the PB card; a
  run that sets no PB but is of a new version of a time-scored scenario
  switches the next rank from the pace wording to the score wording; a run on
  another scenario leaves the card; a scenario change and a filter change
  rebuild both cards; the position's poll and Refresh write the percentile
  line.
- **Live, each PR:** headless Edge at 3840, 2560, 1920, and 1536 px and at 110%
  and 125% zoom, in light and dark: the row's height against today's, the
  latest-run card's edges against the run list's, nothing overlapping. The
  maintainer's look in Firefox.
- **Docs:** `tests/test_docs.py` for the links and the summaries; the gates
  in AGENTS.md.
