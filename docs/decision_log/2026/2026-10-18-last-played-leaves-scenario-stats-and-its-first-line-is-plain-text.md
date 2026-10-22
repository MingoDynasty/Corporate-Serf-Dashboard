# 2026-10-18: Last Played Leaves Scenario Stats, And Its First Line Is Plain Text

Status: Accepted

Scenario Stats on Run History no longer shows Last played, because the
latest-run card beside it now says when the selected scenario was last played.
The card's first line reads Scenario stats as plain text in sentence case, as
the first lines of the two cards beside it do. With no scenario selected it
says so in place of its other lines, where it showed a run count of zero. The
row held the app's one allowed em dash, so the copy rule against em dashes now
has no exception.

**Superseded in part (2026-10-21).** [TS8](2026-10-20-scenario-stats-leads-with-the-typical-score.md) changes the plain-text first line from Scenario stats to Typical score, adds the lead, and renames Number of runs to Total runs. The first line remains plain text rather than a heading, Last played remains on the latest-run card, and the no-selection message and em-dash rule stand.

**Ruling and delivery.** R2 of
[#388](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/388),
ratified by the maintainer on 2026-10-18 at `0fcac03`, "I ratify the
proposal." Before it, their lean of 2026-10-14, while Proposal 1 was in
review, was to remove Last played, and they kept it until now: "'just now' is
fine, keep Last played until Proposal 2." On the card left behind, 2026-10-18:
"Slim the Scenario Stats card is fine. Later it will likely hold the Typical
Score." On its label, the same day, they asked whether "Scenario Stats" and
"Latest run" should be cased alike, and agreed to the recommendation. Built in
[#391](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/391).
Current behavior is in
[run_history.md](../../specs/run_history.md#scenario-stats). The row rests on
[the latest-run card's rule](2026-10-18-the-latest-run-card-reports-the-selected-scenarios-latest-run.md),
and would not have shipped without it.

**Why.**

- **Last played repeated the card beside it.** Both read "1 day ago" for VT
  Controlsphere Viscose on 2026-10-18, once the card reported the selected
  scenario's run.
- **"Number of runs: 0" with nothing selected read as a count.** The card now
  says what the PB card and the latest-run card say there.
- **The three cards' first lines are one kind of thing on screen.** "PB · set
  8 days ago" and "Latest run · 1 day ago · {scenario}" were plain text in
  sentence case. "Scenario Stats" was an `h2` in Title Case, as copy rule 3
  sets for headings, so it read as a title the other two are not.

**What went.** The Last played row, its 30-second ticking text and its
clientside callback, its hover, its two stores, and its empty values `—` and
`Never`. `ScenarioStatsIds` loses the row's four ids and the page's tick it
read, and `scenario_stats_stores` is gone. The playlist tables' Last Played
column is untouched.

**What the card holds.**

- **The first line is plain text, `Scenario stats`:** a `div` in the class the
  `h2` had, drawn as the card's quiet first line, at the card's top like the
  other two cards' first lines. The page outline loses that heading, as the PB
  card and the latest-run card never had one. It was the page's only `h2`.
- **With no scenario selected,** Category and Number of runs give way to "No
  scenario selected", in the PB card's empty-title style. The `Scenario stats`
  first line stays in every state, as the PB card keeps `PB` and the
  latest-run card keeps `Latest run`. One callback writes the count, its
  line's `hidden`, and the no-selection line's `hidden` in one answer, so the
  card never shows both or neither.
- **Category and Number of runs keep their rules,** and a selected scenario
  with no runs still counts 0. The card keeps its 270 px frame.

**The em dash rule has no exception.** Copy rule 2 forbade em dashes
everywhere but Last played's empty value with nothing selected, and
`tests/test_em_dash_guard.py` allowed that one string. Both exceptions go:
AGENTS.md's rule 2 drops its sentence about it, and the guard gates every
string under `source/`. The guard's proof that its walk reads real source,
which found Last played's dash, is replaced: the same walk over the same files
must find the middle dot that chains the latest-run card's first line, both
inline in the card's layout and in an f-string's literal part. A walk that
read none of `source/` fails it.

**Set aside.** Keeping Last played as a deliberate duplicate; removing the
card, which the top row's layout placed and Typical Score is expected to
fill; and `—`, `N/A` or `None` for Number of runs with nothing selected: `—`
would bring the em dash exception back, and `None` reads as zero runs.

**What this changes in older entries.** Each keeps its text and gains a dated
note.

- [2026-10-14, Scenario Stats names the category](2026-10-14-scenario-stats-names-the-selected-benchmarks-category.md):
  Last played in the card, its empty states, and its heading as an `h2`.
- [2026-10-14, a card's lines follow their role](2026-10-14-a-cards-lines-follow-their-role-in-the-players-next-action.md):
  Last played among Scenario Stats' facts and among the ages.
- [2026-06-21, relative Last played](2026-06-21-relative-humanized-last-played-timestamps.md)
  and
  [2026-06-30, Last played's empty states](2026-06-30-model-home-last-played-empty-states-explicitly.md):
  their Run History use goes. The playlist tables' Last Played column keeps
  them.
- [2026-09-14, the copy rules](2026-09-14-app-copy-follows-one-set-of-rules-and-the-em-dash-is-gated-out.md):
  rule 2's one exception and the guard's allowlist.
