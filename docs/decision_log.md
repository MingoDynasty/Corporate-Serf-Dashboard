# Decision Log

Durable project decisions that future contributors and agents should preserve unless a newer entry supersedes them.

Use this log for decisions that are hard to reverse, cross-cutting, based on external API behavior, or likely to be questioned later. Do not record every small implementation choice.

When a decision changes, keep the old entry and mark it `Superseded`. Add a new entry explaining what changed, why, and any migration notes.

## Status Values

- `Proposed`: under consideration, not yet agreed.
- `Accepted`: current agreed decision.
- `Superseded`: replaced by a newer decision.
- `Rejected`: considered and intentionally not chosen.

## 2026-10-05: A Columns Menu Shows And Hides Table Columns, And KovaaK's IDs Are Optional Ones

Status: Accepted

The app knows the KovaaK's leaderboard ID of every scenario it has resolved
and the benchmark ID of every bundled benchmark, but it showed neither, so
trying a KovaaK's API request by hand meant digging the number out of a file.
The Playlists table and a playlist's scenario table now each have a Columns
menu that shows or hides any column and remembers the choice in the browser.
Each table also has one ID column that starts hidden, so both pages look as
they did until the menu is used. A sort on a column the user has hidden is
dropped, because the rows would otherwise be ordered by something off screen.

**Rulings.** Ratified (user) 2026-10-05, on the proposal
([PR #334](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/334)),
after two review waves in which every reviewer endorsed both rows.

- **D1. The IDs are optional columns, behind a menu that covers every
  column.** One ID column per table, hidden by default, and a **Columns** menu
  that lists every column the table can work without. Rejected: a menu that
  lists only the ID column, and a "Show IDs" switch, which both put a control
  on a page every user sees for a need only an API caller has; a hover tooltip
  on the name cell, whose text can't be selected and which nothing on screen
  announces; and no UI, which leaves the lookup a file search.
- **D2. Choices are remembered in the browser, one set per table.** Each
  column's shown or hidden state is kept in local storage, as the Show hidden
  switch is, and the scenario table's set is shared by every playlist. A
  browser that has never opened the app shows the defaults, which fails toward
  the IDs being hidden; the celebration setting accepted the same costs
  ([2026-09-02](#2026-09-02-the-celebration-setting-is-browser-local-on-the-settings-page)).
  Rejected: the URL, as the sort uses, because which columns a user reads is a
  standing preference and not part of one visit; one set per playlist, which
  multiplies the stored state for no stated need; the settings file, which
  needs a server write path and a schema stamp for a display preference; and
  no memory, which makes hiding a column pointless.

**What the menu lists.** Every column the table can work without, in table
order. The rule is a property, not a list: a column the table's structure
depends on is never listed. That is the name column, because the row means
nothing without it and it is the link into the row, and the overview's action
cells, because they are the only way to hide or delete a playlist.

- Overview: Type, Benchmark ID, Played, Runs, Last Played, Median Percentile,
  Lowest Percentile.
- Scenario table: Leaderboard ID, Last Played, Runs, Position, Total Players,
  Percentile, PB Score, PB Date, PB cm/360, PB Accuracy, with Rank and Next
  Rank after PB Score on a benchmark's table only.

A checked column is shown. A change applies at once, and the menu stays open
until an outside click or Escape, so several columns can be set in one visit.
Every column is shown by default except the two ID columns. The checkbox
labels are sentence case, as controls, while the headers they name keep Title
Case
([2026-09-14](#2026-09-14-app-copy-follows-one-set-of-rules-and-the-em-dash-is-gated-out)).
They are two lists kept by hand; the labels are not derived from the headers.

**One persisted checkbox per column, never one checkbox group.** Dash stores a
persisted prop as the pair of the chosen value and the layout's default, and
drops the stored value when the default no longer matches. A group's value is
the list of shown columns, and that list's default differs between a
benchmark's table and a playlist's, so moving between the two would reset the
choice every time, and a column added in a later release would reset it once
more. With one checkbox per column, each default is a constant: checked for a
default-shown column, unchecked for an ID column, the same on both kinds of
table. A benchmark-only column's checkbox is rendered only on a benchmark's
table, so a playlist's table leaves its stored value alone. The checkbox ID,
`{"type": <menu ID>, "column": <column ID>}`, is the storage key
(`_dash_persistence.<id>.checked.true`), so renaming a menu or a column ID
resets that one stored choice once.

**The menu's dropdown stays mounted while closed.** Measured on the real pages
in headless Edge on 2026-10-05 (dash 4.4.1, dash-mantine-components 2.8.0): a
popover that unmounts its closed dropdown brought a checkbox back in its old
state. Hide a column, close the menu, open it again, and the checkbox read
checked beside a hidden column, and the first click on it did nothing. The
cause was read in Dash's renderer source, not traced at run time: a component
that mounts as a new render draws from the props its parent last passed down,
not from its current ones. With `keepMounted` set on the popover, the same
steps showed the checkbox unchecked and the first click showed the column.
The stored choices still reach the grid as the page mounts, before the menu
is ever opened.

**The popover traps focus, and does not return it.** The dropdown renders in
a portal at the end of the page, out of reach of the keyboard otherwise, so
opening the menu moves focus to its first checkbox. `returnFocus` stays off.
It hands focus back to the button on every close, including one caused by a
click on another control, and that click still lands. With it on, text typed
into the filter after such a click went to the button instead: the first
space reopened the menu and the second flipped a checkbox, which hid the
column just shown and stored that (found in review of PR #344, and measured
on both tables on 2026-10-05). Escape returns focus to the button without it.

**One clientside callback per table applies the checkboxes through the grid
API.** It is the app's first pattern-matching callback, over that menu's
checkboxes. It runs as the page mounts, with the stored values, and on every
change, and does four things in order:

1. `setColumnsVisible` for the shown set and for the hidden set.
2. Clears the sort of every hidden column, with `applyColumnState` and
   `sort: null`. A hidden column otherwise keeps its sort.
3. Re-runs the quick filter, with `onFilterChanged`. The proposal listed
   three steps and not this one. AG Grid matches the quick filter against
   visible columns, but on a visibility change it only drops the filter's
   cached text and filters nothing again. Without this step, with `2336` in
   the filter, hiding Benchmark ID left its row on screen, and showing the
   column again left no rows, each until the text was next edited (found in
   review of PR #344, and measured on both tables on 2026-10-05).
4. `autoSizeColumns` on the columns it just showed. On the proposal's
   prototype (2026-10-04), a column shown through the API was not sized, and
   one shown as the page opened came up at its minimum width and clipped its
   header. With this step, on the real pages, Benchmark ID sized to 145 px
   and Leaderboard ID to 154 px after a toggle, a reload, and an in-app round
   trip alike (2026-10-05).

Step 4 fits only the columns a run showed, so a toggle never undoes a width
the user set by hand. Every other column is left to the grid's own autosize,
and for that to work both grids turn column virtualization off
(`suppressColumnVirtualisation`).

With virtualization on, AG Grid renders only the columns inside the window. A
stored choice changes which columns those are as the page opens, and the
grid's own autosize, which runs right after the callback's first run, then
left each column that had just come into the window at its minimum width,
narrower than its header. With Position, Total Players, and Percentile stored
as hidden, a benchmark's table in a 1920 px window opened with PB cm/360 and
PB Accuracy clipped, on every load (found in review of PR #344, 2026-10-05).
Which stored sets clipped depended on the window width, the data, and the
browser. Why AG Grid sizes such a column to its minimum was not traced.

Two fixes that fit the columns again were tried first and rejected:

- *In the same task as the first run.* In the review's probe it cleared the
  reported sets and clipped three others.
- *Two animation frames later.* It cleared every reported case in Edge. In
  Firefox it clipped sets that had been whole without it: 18 of 26 stored
  sets on a benchmark at 2000 px. A fit timed by frames or by a delay has a
  browser, a width, or a machine where it runs too early.

With every column rendered there is nothing to time. None of the review's
stored sets clipped a header: 26 sets on a benchmark, in Edge at window
widths from 1366 px to 2400 px and in Firefox 157 from 1920 px to 2400 px, 22
on a playlist, and 16 on the overview (measured 2026-10-05). The tables have
at most 13 columns, so rendering them all costs nothing visible.

Turning virtualization off also changes the default view in a narrow window.
Before, a column scrolled out of view when the page opened kept AG Grid's 200
px default, which a benchmark's table showed from 1680 px down. Now every
column is sized to its header and its content, whether the page or the menu
showed it.

Only the newest run of the callback applies anything. Each run waits for the
grid API on its own timer, so a run that started earlier can finish later,
and it would put its older values back over the newer ones.

It never writes the grid's `columnState` prop, which dash-ag-grid applies with
`applyOrder: true`, and never resends column definitions, whose `sort` and
`hide` AG Grid reapplies over the user's own. For the same reason the ID
columns declare `initialHide`, never `hide`. The control and the callback body
live in one module both pages import. The server never learns which columns
are shown: rows always carry every field, and hiding Position, Total Players,
or Percentile stops none of their fetches.

**Sort: hiding a sorted column clears its sort.** This amends the ruled sort
contract
([2026-09-27](#2026-09-27-the-playlist-scenario-table-keeps-its-sort-in-the-page-url)),
and D1's ratification covers the amendment. That entry has Back and Forward
restore an entry's sort, and a reload or a copied link keep it. For a sort on
a hidden column neither holds any more. The server cannot know which columns
the browser hides, so on arrival it seeds the sort from `?sort=` as before;
the callback then hides the column and clears that sort, the grid publishes
its new state, and the existing address writer removes that name. Other sorts
in the value are kept, as are the other query parameters and the hash, and no
history entry is added. Showing the column again does not bring its sort back.

The ID columns are not sortable. A sortable column on the scenario table
needs a name in `?sort=`, and the address writer stops writing for as long as
a sorted column has none, which would silently end sort memory.

**Two states are accepted, not bugs.**

- *The overview can show Last Played with its rows in name order.* Its
  default sort, Last Played newest first, is declared in the column
  definition and seeded on every mount. Hiding Last Played clears it, and the
  rows fall back to name order, including when they rebuild. Showing Last
  Played again leaves name order for the rest of that visit, and the next
  page load sorts by it again. The column definition is not changed to avoid
  this.
- *A status line can report on columns that are hidden.* Each status line
  reports on a fetch, not on a column, so "Updating positions from KovaaK's…"
  and the two username lines read the same with Position, Total Players,
  Percentile, or both percentile columns hidden.

**Benchmark ID comes from a side table, not from the model.** The bundled
loader reads `generated_from.kovaaks_benchmark_id` from each bundled file's
raw text into a table keyed by playlist code, rebuilt on every load, as it
already collects the seed's name and ID pairs. `PlaylistData` gains no field,
because the benchmark importer shares the model: its drift check compares a
shipped file with a stamp-free rebuild by whole-model equality
([2026-09-26](#2026-09-26-a-read-only-check-finds-bundled-benchmarks-that-kovaaks-changed)),
so a field would report all 261 bundled files as drifted, and the importer
would start writing it into every file it regenerates.

- Only bundled files are read, so a user file's stamp is ignored. A playlist
  imported by code has no benchmark ID and reads `N/A`.
- A missing or malformed block reads as no ID and never stops the file from
  loading.
- When two bundled files claim one code, the table holds the ID of the file
  that won it.
- Validation stays the only judge of a broken file. The loader validates the
  text first and reads the stamp with a second, tolerant parse after it. One
  `json.loads` in place of both raises an error the loader does not catch, so
  a file that isn't valid JSON would lose its startup warning. The second
  parse costs about 10 ms over the 261 files (3.8 MB, measured 2026-10-05).

**Leaderboard ID comes from the name-to-ID mapping.** That is the value the
app itself sends to KovaaK's, not the copy embedded in the playlist file. The
two differ when a learned entry has replaced the seeded one, or when the seed
left the name out because two bundled files embed different IDs for it
([2026-07-20](#2026-07-20-seed-leaderboard-ids-from-the-bundled-benchmark-corpus)).
One name is in that state today: CB SmoothTrack, which one file gives as
97841 and two give as 92603. The mapping is the right source in both cases,
because it names the leaderboard the Position beside the cell came from. A
scenario the app hasn't resolved reads `N/A`, which includes that excluded
name on an install with no username, until a lookup learns an ID for it.

The table builds rows on three paths: the first paint, the fill's streamed
rows, and a cancelled fill's rebuild. The last two replace a row's data
whole, so a path that dropped the field would blank the cell. All three go
through one row builder, which reads the mapping. The fill looks a position up
before it builds the row, so a streamed row carries an ID that lookup just
learned.

**Both ID columns.** The value is bare digits, such as `184106`, with no
thousands separator, because it gets pasted into a request. The cell's text
can be selected, through one cell class that sets `user-select: text`; the
grid-wide `enableCellTextSelection` option is not used. On the overview every
other cell opens the playlist on a click, so the Benchmark ID cell is left
out of that navigation, as the action cells are: a double-click is two
clicks. Each header carries a tooltip saying what the number is.

**Unchanged.** Column widths and column order are still not remembered. The
quick filter keeps matching visible columns only, which is AG Grid's default,
so typing an ID finds a row only while the ID column is shown. No cache,
setting, network path, or notification is touched.

**Out of scope.** An ID readout on the Scenario Performance page, for a
scenario in no playlist; a reset or show-all control; reordering columns from
the menu; a copy button in the ID cell; and skipping the fetch for a hidden
column.

**Provenance.** Proposal in PR #334, ratified 2026-10-05. Shipped in
PR #344.

## 2026-10-05: Time-Scored Scenarios Are Measured By Pace

Status: Accepted

Some scenarios score the time left on a countdown when the task is done, and
on those the app now measures by pace: how fast a run finishes compared with
the personal best. A percentage of such a score understates a real
improvement many times over, so these scenarios looked closer to the next
rank and easier to pass than they were. A player sees "faster" in the Next
Rank column and "PB pace" in a run's verdict wherever pace applies. Where the
app can't tell whether a scenario is time-scored, everything reads as it did
before.

**Ruling.** Ratified (user) 2026-10-04 as a whole, after three review waves
on the proposal (PR #329, merged as `3efebe5`; the P1 and P2 rulings recorded
at `72eec3e`, the ratification at `18174de`). P1 and P2 were ruled together,
each as recommended, and P8 was ruled as a deferral. The author-owned rows
P3, P6, P7, P9, and P10 were reviewed and settled by the ratification. The
maintainer had already set three constraints: it is a bug fixed on its own
track (2026-09-28); the app detects such a scenario from the player's own
runs, accepts any constant, and falls back whenever it is unsure
(2026-09-28); and it adds no run length to the run record (2026-10-04).

**Supersedes in part**, for time-scored scenarios only, D1 of the
[2026-09-27 entry](#2026-09-27-benchmark-tables-show-each-scenarios-rank-and-the-gap-to-the-next-one)
and the verdict formula of the
[2026-07-08 entry](#2026-07-08-judge-score-threshold-notifications-against-the-previous-pb).
Each keeps its text and gains a note. Every other scenario keeps both
unchanged.

**What a time-scored scenario is.** It has no fixed length. It ends when the
player finishes a task, such as killing six bots, and its score is the time
left on a clock that counts down from a constant. So the score is the
constant minus the completion time, and one point is one second. A
percentage of a score assumes the score starts at zero, and this one starts
at the constant. For a small change, the percentage of the score understates
the percentage of pace by the score divided by the run's time, a factor of 4
to 16 across the maintainer's 99 runs of ten such scenarios (2026-10-04).

**The pace formulas.** With constant `C`, a score `s` took `C − s` seconds.
`T` is the next rank's threshold, `g` the goal percentage, and `prev` the PB
before the run. Each percentage that divided one score by another divides
the other way round on times, and nothing else in its formula changes:

| Surface | Score math | Pace math |
|---|---|---|
| Next Rank gap | `(T − PB) / PB × 100` | `((C − PB) / (C − T) − 1) × 100` |
| Threshold line | `PB × g / 100` | `C − (C − PB) × 100 / g` |
| Verdict passes when | `s × 100 ≥ prev × g` | `(C − prev) × 100 ≥ g × (C − s)` |
| Verdict shows | `s / prev × 100` | `(C − prev) / (C − s) × 100` |
| Personal best gain | `(s / prev − 1) × 100` | `((C − prev) / (C − s) − 1) × 100` |

**Pace applies only when it is defined.** A surface uses pace when the
scenario is recognized, every score in the comparison is eligible, and both
times are positive. Otherwise it runs the code it ran before, with that
code's own `N/A` and unjudged rules. One consequence is deliberate: a
time-scored PB of zero or less still gets a pace percentage, because only
the times have to be positive. The verdict converts each score and the
constant to decimals before subtracting and compares the cross-multiplied
form, so a run exactly at the goal passes, as the 2026-07-08 entry requires.
Display rounding is unchanged. The gap rounds up with a floor of 0.1, and a
verdict keeps both of its caps: a miss prints at most one tenth below the
goal, and a run below the previous best prints at most 99.9%. The second cap
needs no change, because a run's pace is below the previous best's exactly
when its score is.

**Why pace and not time: both are a percentage of throughput.** On a
fixed-length scenario the time is fixed and the score is the work done in
it, so score divided by PB score is a ratio of throughput. On a time-scored
scenario the work is fixed and the time varies, so throughput is one over
the time, and its ratio to the PB's is the PB's time divided by the run's.
That is pace. So the one global threshold setting keeps one meaning, a
higher setting still demands more, and a pace gap and a score gap can share
one sorted column. It also lets every formula carry over with only the ratio
replaced, so the rounding, capping, and boundary rules needed nothing new.

**P1: the Next Rank gap on a time-scored scenario is a pace gap.** It is how
much faster the PB run has to finish to reach the next rank. D1's three
reasons all survive: the gap is defined below the first rank, it states the
target to beat, and it still matches the score threshold, which P2 moves the
same way. The ladder walk, the Rank column, the round-up and its floor, the
unrounded sort key, Top rank's precedence, and the tooltip in points are
unchanged, because a higher score is always a faster finish. One rule
narrows: D1's `N/A` for a PB of zero or less now applies to a time-scored
row only where pace is undefined. Rejected: keeping D1, which understated
these gaps 9 to 12 times on the maintainer's Viscose rows and floated all
four to the top of an ascending sort; the gap in seconds, which is exact but
can't be compared across scenarios and already sits in the tooltip; percent
less time, which is not what "faster" means and would measure differently
from P2; and `N/A`, which drops the one answer the column exists for.

**P2: the score threshold on a time-scored scenario is a percentage of PB
pace.** At 95%, a run passes when it is at least 95% as fast as the PB,
which means finishing within the PB's time divided by 0.95. The chart line
sits at the score that finishes exactly then, from the current PB, and the
verdict judges against the previous PB, as before. A goal above 100% puts
the line above the PB. The setting stays one global percentage. Judged
after the fact on the maintainer's six time-scored scenarios with at least
five runs, the score form passed 86 of 86 runs and the pace form 59.
Rejected: keeping a percentage of the score; reading the percentage as
time, which taken literally demands a run 5% faster than the PB and
otherwise needs a translation of the setting that no other scenario uses;
turning the threshold off on these scenarios; and a separate or
per-scenario percentage, which is a Run History question.

**Detection: one performance file answers one of three ways (P9).**
KovaaK's writes a performance file beside each run's stats file. The check
reads the header's `schema_version` and `scenario_hash`, its challenge
profile's `time_limit` and `timescale`, and each event's `timestamp` and
score delta.

- *Time-scored:* the file has at least two score events, and after every
  one the running score is within 0.5 of
  `time_limit − timescale × timestamp`. The constant is the file's
  `time_limit`, and the scenario version is its `scenario_hash`.
- *Not time-scored:* any other file that can answer.
- *Can't answer:* the bytes do not parse, or `schema_version` is not 1. The
  proposal left four header cases open, and each also can't answer: no
  header, no scenario hash, a time limit that is missing, not positive, or
  not a finite number, and a timescale that is any of those three. No file
  in the maintainer's folder has any of them.

**Which file decides.** The scenario's newest run names the version. That
run and the older runs of the same hash are tried newest first, and the
first whose performance file can answer decides. A file that can't answer
is skipped, so a damaged file, or a schema change in the game, doesn't turn
a recognized scenario back. A file that answers "not time-scored" is not
skipped: every ordinary scenario's newest file answers that, and skipping
it would read that scenario's whole history. No file that can answer means
the app can't tell. So does a newest run with no hash, which names no
version. One file can decide because how a scenario scores belongs to its
definition, which the hash identifies. A scenario's first run on a current
build therefore flips it to pace, and it flips back only if a newer run's
file can answer and shows no countdown.

**The tolerance absorbs a start lag, not noise.** From the maintainer's
1,764 performance files on 2026-10-04: the 84 countdown files, across 10
scenarios, stay within 0.02 of the line at every event, and the nearest of
the other 1,680 is off by 42. Every tolerance from 0.02 to 40 recognizes
the same 84. The distance is set at the first score event and barely moves
after it. On the other paired files that first event's timestamp falls up
to 72 ms short of one second, with a 99th percentile of 31 ms. Every run in
the data was played at 407 to 988 FPS, so a slower machine may lag more,
and a missed file is silent. Half a point is seven times the largest lag
seen. `timescale` is the scenario's own game speed: the time limit counts
game time and the timestamps count real time, so a slowed time-scored
scenario should lose `timescale` points per real second. No such run is in
the data, and if the game does otherwise the check fails and the scenario
falls back.

**The file facts the app relies on.** KovaaK's publishes the format, a
protobuf schema, at <https://wiki.kovaaks.com/performance.proto>, and the
app reads it by hand, with no protobuf dependency. Game builds from 3.9.0
write the files, into the `performances` folder beside the stats folder. A
run's file is found by name: the stats file's name with ` Stats.csv`
replaced by ` Performance.perf`. Of the 1,757 stats files written since the
first performance file, 1,756 have one of the same name, and on all 1,756
the header's hash equals the stats file's `Hash:`. The game writes the
performance file within 10 ms of the stats file, and the watchdog already
waits a second before reading a new stats file. Every file in the folder is
schema version 1. There is no new setting, and the app only reads the
folder.

**Eligibility is by hash (P10).** A run record keeps the stats file's
`Hash:` and the stats file's own name, and no run length. A score is
eligible for a pace comparison only when its run's hash equals the deciding
file's. That covers the row's PB, the chart's PB, the verdict's and the
celebration's previous best, and the new run. A rank threshold comes from
the benchmark file and counts as eligible. A stats file with no `Hash:`
still loads, and its score is never eligible. So a PB from an older version
of the scenario keeps the score math until a run on the current version
beats it: the constant was read from one version, and nothing shows that
another scores the same way. Of the maintainer's 866 scenarios, 15 have
more than one hash, and none of the ten time-scored ones do.

**The constant travels with the run.** The watchdog works the constant out
before it queues a run's message, with the landed run judged by its own
file, and the message and the batch record carry it as a fact, like the
previous best. It is absent when the scenario isn't recognized, when the
new run or the previous best isn't eligible, and on a scenario's first run,
which nothing judges or celebrates. So the toast agrees with the chart,
which rebuilds after the run lands, and neither the drain nor the page
reads the stores for it.

**Cost and memory.** Startup lists the `performances` folder once and
parses nothing. A run that lands adds its file to that listing, so the
table and the chart see the file the watchdog read. A file is parsed only
when a surface asks about its scenario, and each answer is remembered by
file name, because a written file never changes. A file that can't be read
is not remembered, so the next look tries again. Reading one costs about
0.6 ms in plain Python for a median file of 4.7 KB. Nothing is written to
disk. A missing, unreadable, or malformed performance file costs only the
detection, never the run. The stores are read on the terms of the
[2026-07-09 entry](#2026-07-09-accept-unsynchronized-in-memory-stores-single-writer).

**Five surfaces.** Next Rank reads "{gap}% faster to {rank name}" and sorts
by the unrounded pace gap, on all three row paths. The Score threshold line
draws at the pace line, and its annotation still shows a score. The
threshold verdict says "% of PB pace". The New personal best toast says
"Finished {pct}% faster than your previous best of {previous}." The session
debug log judges by pace at its fixed 95%, because left on score it would
pass every run the toast fails. Anything that orders or places scores is
unchanged: the chart's points and axis, the Average score line, the PB
line, the rank lines, the Rank column, top-N placement, and the
celebration's strictly-greater test. The Next Rank header tooltip and the
Score threshold percentage help text name both measures, in wording that
stays true in every fallback. No completion time is shown anywhere.

**Rejected: inferring it from the stats files.** A stats file gives a run's
length only as its name's time stamp less its start time and pause
duration, precise to about a second, and a detector can fit score plus
length to a constant across a scenario's runs. The proposal's first design
did. It needs five runs, and four of the ten scenarios have fewer. A fit
through noisy lengths can't establish one point per second. Its constant
came out 0.3 to 0.5 s low, which distorts a short run's percentages. And
the stats file can't see a slowed scenario: its time dilation field reads
1.0 on all 363 runs whose performance file records another timescale.
Keeping the inference as a fallback was rejected too, since on the
maintainer's data it recognizes nothing the file doesn't. Also rejected: a
hand-kept list of scenarios, which can't cover what public users play; the
header alone, since a time limit says how long a run may last and not how
it scores; requiring a time limit of exactly 1,000, which would hard-code
the constant; and parsing every file at startup, which grows with every
run.

**P8: the Aim Training Journey graph keeps its score ratios.** That graph
averages each scenario's best score so far as a share of its PB, the same
ratio corrected here. The page was ruled shelved on 2026-09-28, as recorded
in
[#327](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/327),
so leaving it alone is a deferral under that ruling, separable from this
fix. On a playlist that holds time-scored scenarios the graph keeps
overstating how close earlier runs were to the PB. A plan that revives the
page carries this fix with it.

**Checked in the game before the merge.** Two cases had no run in the
data, so the maintainer played one of each on 2026-10-05, on Air Pure
Easier No UFO and game build 3.9.10. A run paused for 15 s partway through
was recognized, with a largest distance of 0.011. Its file carries one
pause event, and its timestamps leave the paused time out: the run took
about 102 s by the clock, and its last event is stamped 87.2 s. So a file
with a pause event needs no special case. A run at a 60 FPS cap was
recognized with a largest distance of 0.027, where that scenario's six
earlier files sit at 0.006 to 0.008. That is one run, so it shows the
typical lag and not its tail, and half a point is about nineteen times
it. The debug log records each parsed file's largest distance from the
countdown, which is the number to read if a scenario is ever not
recognized.

**Out of scope.** Run History, including a run length field and a
per-scenario threshold. A per-bot breakdown. Anything else the performance
file holds. A scenario whose score isn't the time left on its clock, and
one with no performance file: both keep the score math.

**Provenance.** Proposal by `claude-opus-5-5` (PR #329), reviewed by
`gpt-6-astra` and `claude-fable-5-1`. Shipped in PR #343.

## 2026-10-05: The Score vs Time Chart Marks Each New PB With A Star

Status: Accepted

The Score vs Time chart now draws a gold star on each plotted run that beat
the scenario's personal best when it was played. Every run used to be the same
dot, and a day's runs share one position, so the runs that set each best could
only be found by comparing every dot with all the ones before it. The stars
need no setting, and the Score vs Sensitivity chart is drawn exactly as
before. They record what the player reached and when, and they don't judge
whether the player is improving.

**Ruling.** Ruled (user) 2026-10-05, on PR #337: the maintainer ratified the
whole proposal after two review waves, with every reviewer endorsing every
row. That settled the rule, the chart it applies to, and the absence of a
control as recommended. It also covered the author-owned look, build, copy,
and term, and with them one exception to an earlier entry, named under
**Point size sizes the stars**.

**The rule.** A new PB is a run whose score is strictly above every earlier
run of its scenario. It is the rule the personal best celebration applies to
one new run
([2026-09-02](#2026-09-02-a-new-personal-best-celebrates-on-every-page)), so a
star and a celebration judge a run the same way.

- One pass over the scenario's runs from oldest to newest, at every
  sensitivity, including the runs older than the page's oldest date. A star
  then means one thing whatever the chart's filters are set to: this run was
  the PB when it was played.
- A tie is not a new PB, so the earliest run to reach a score holds the star.
  The playlist tables' PB Date already reads a tied PB that way.
- The scenario's first run sets the baseline and is not one.
- Nothing is stored. The pass runs when the chart is rebuilt, and the
  maintainer's largest scenario had 463 runs on 2026-10-04.
- A higher score is better on every scenario, time-scored ones included, so
  pace doesn't change the rule.

Rejected:

- **Mark only the current PB.** One star per chart, on the point the PB score
  line already touches. It adds nothing the line doesn't show, and it can't
  say when the earlier PBs happened.
- **Judge against the plotted window only,** restarting the comparison at the
  oldest date. The star's meaning would move with a chart control, and it
  would mark runs that were never a PB: 86 of them, across 45 of the 188
  scenarios with runs older than the window.
- **Count the first run.** Every scenario would open with a star that says
  nothing. The celebration skips it for the same reason.
- **One star per day,** on the run that held the PB when the day ended: 421
  stars where the rule draws 666. A star would stop matching the celebration's
  rule one to one, and its meaning would depend on the chart drawing its axis
  in days. The 245 stars it drops are the ones a reader couldn't find before,
  because a day's runs share one position.

**Only Score vs Time is marked.** Score vs Sensitivity keeps its two traces.
The chart opens on Score vs Sensitivity and remembers the choice per browser,
so a fresh browser shows no stars until the reader switches. Along the date
axis the stars read left to right as the history of the PB, and along the
sensitivity axis they have no order. That chart also keeps only the top scores
at each sensitivity, which are mostly the latest new PBs. About four in ten of
its points would be stars (584 of 1,355), and on the 75 scenarios with 20 or
more runs it would draw only 172 of the 255 new PBs, with nothing to show
which are missing. Rejected: marking both charts at that cost, and marking
only the current PB on Score vs Sensitivity, where the PB score line already
touches that point and the star would mean something different on each chart.

**A star belongs to the run, not to a position.** A star is drawn on a plotted
run that is a new PB.

- A new PB the chart doesn't plot gets no star, whether the Top N filter
  dropped it or it is older than the oldest date. It still counts in the
  comparison. By this rule 666 of the year's 691 new PBs get a star.
- A later run the same day with the same score sits at the same position, and
  it is not a new PB.
- **A kept tie doesn't inherit the star.** The day's filter keeps the later of
  two equal scores, so with Top N low enough it drops a new PB and keeps the
  run that tied it. That day then has a point at the PB's score and no star.
  A match on the position would star it: 4 stars on runs that never beat the
  PB.
- A chart where no plotted point is a new PB has no New PB trace and no legend
  entry.

**The hover names the run that set the PB.** When a new PB and a later
same-day tie are both plotted, their points coincide: 26 of the 666 stars. The
chart shows one hover for the pair. Among points at one position plotly.js
shows the hover of the one that comes last in the trace, and in time order
that is the later run, which never beat the PB. So the run trace places a new
PB after the runs that share its position, and its hover is the one shown.
Only the order of points within the trace changes: the same runs are plotted
at the same positions, and the Average score line is unchanged.

That order is an observed behavior of the bundled plotly.js 4, not a
documented one. A unit test pins the order within the trace. Which point
plotly.js answers with can only be seen in a browser, and the implementation's
scripted check does that: on a real shared star it read the new PB's own time
and accuracy at six cursor positions across the star. A plotly.js upgrade is
where it could change.

**The look.** One color for both themes, with no theme logic.

| Property | Value |
|---|---|
| Symbol | plotly's `star` |
| Fill | `#fab005`, Mantine yellow 6 |
| Outline | `#5f3d00`, 1 px |
| Size | 12 with Point size on Default, 9 on Small, 16 on Large |

- **Gold,** the usual color of an award. Yellow is also one of the four color
  families the Point color swatches leave out, so no swatch can match it.
- **An outline, because gold alone fails on white.** Gold has 1.86:1 against
  the light plot background and 8.34:1 against the dark one. The outline has
  9.75:1 against white and 5.24:1 against the gold. The
  [2026-08-20 entry](#2026-08-20-run-points-get-a-size-preset-and-a-color-and-the-chart-stops-there)
  dropped yellow from the swatches for the same contrast reason.
- **A shape as well as a color.** Point color accepts any hex value, so a
  player can set the run points to this exact gold. The star and its outline
  still stand apart then, and the mark never depends on color alone.
- **About twice the run point's size.** A star reads smaller than a circle of
  the same size. The run points are 4, 6, and 10 px at the three presets. The
  Large star is 16 and not 20, so stars on neighboring days don't crowd.

The values were chosen from a prototype built through the app's own plot
functions on the maintainer's runs, in both themes, at the three sizes, and
with gold run points.

**How it is built.** A third trace named New PB, added after Average score so
that it is drawn on top.

- The run trace keeps every run, so hiding the stars from the legend leaves an
  ordinary point where each star was.
- The star trace sets `hoverinfo` to `skip`, so hovering a star shows the run
  trace's hover for that point.
- Share chart and Download plot as a PNG carry the stars, as they carry
  everything plotted. The figure holds no new data: each star repeats a
  plotted run's date and score.
- The zoom fit is unchanged. It reads every visible trace, and the stars sit
  on run points, so the fitted range is the same with the stars shown or
  hidden.
- The legend's three entries were 364 px wide and on one row at the narrowest
  chart the open Chart options panel leaves, where the plot area was 497 px
  wide (headless Edge, 2026-10-05).
- A star on a recent PB can sit under the PB score label, which is drawn at
  the right end of its line. Where the overlay labels go is a separate
  question, and this entry doesn't move them.

**Point size sizes the stars, an exception to the 2026-08-20 entry.** That
entry
([Run Points Get A Size Preset And A Color, And The Chart Stops There](#2026-08-20-run-points-get-a-size-preset-and-a-color-and-the-chart-stops-there))
says "Nothing else on the chart became customizable", and its point
preferences restyle only the run trace. Point size now sizes the New PB trace
too: 9 on Small, 16 on Large, and the generated 12 on Default. Point color
still restyles only the run trace. The set of controls doesn't change, but one
control now restyles two traces, so that entry is superseded in part, for that
one sentence and nothing else.

The same entry says when to look at symbols again: "reconsider marker symbols
only if the graph ever carries multiple semantic point categories". This is
that case, since a new PB is a second category of point. The outcome is a
symbol the app fixes, and still no symbol control.

**No control.** Nothing in the Chart options panel changed: no switch, no
color or shape setting, and no new persisted id.

- Clicking New PB in the legend hides the stars, as it hides any trace. That
  choice is not remembered. A new figure brings the stars back, because
  plotly.js keeps a legend click across figures only when the figure sets
  `uirevision`, and this chart sets none on purpose. The chart gets a new
  figure from a new run on the scenario, a control that rebuilds it, or an
  appearance change: Point size, Point color, or the theme.
- The celebration accepted the same density of new PBs on a lightly played
  scenario with its setting as the way out. The stars have no equivalent: in
  session, a legend click lasts until the next run on the scenario.
- No workflow asks for a control yet. The 2026-08-20 entry asks that a chart
  control answer a recognizable user goal, and keeps "nothing else until a
  real workflow demands it".
- A star costs little to ignore. It sits on a point that is drawn anyway, so
  the axes cover the same runs with or without it. An overlay line differs: it
  can stretch the score axis, as the full rank ladder does.

Rejected:

- **A New PB switch in Overlays.** Hiding the stars would persist like the
  other switches, at the cost of a fourth control in a group of three, one
  more persisted id, and one more input that rebuilds the chart. It can be
  added later without migrating anything, so waiting to see whether the stars
  bother anyone loses nothing.
- **Letting the PB score switch hide the stars too.** No new control, and the
  choice would persist. But the switch is named for the line, and the line
  stretches the score axis where the stars don't. A player who turns the line
  off to see recent runs closer would lose the stars with it.
- **A color or shape setting.** The 2026-08-20 entry stops chart customization
  at the run points' size and color, and nothing here needs it moved.

**Achievements, not a trend.** The
[2026-10-04 direction entry](#2026-10-04-skill-is-judged-by-the-typical-run-with-honest-uncertainty-in-verdicts-not-advice)
moves judgments about skill toward the typical run and keeps the personal best
as the achievement. The stars sit on the achievement side of that line.

- They record what the player reached and when, as the celebration does. They
  are not a judgment of skill, and they are not a trend.
- A PB only rises, so a row of stars can't show a decline, and after one lucky
  run it reads as a plateau. Whether the player is improving stays the trend
  verdict's question, answered from session medians.
- This chart has no typical-run read of its own. Its Average score line
  averages only the runs each day plots, the top N, so on a busy day it is the
  average of that day's best.
- The cost accepted is emphasis: gold stars draw the eye to the best runs, on
  a chart that already plots each day's best, in an app whose reading of skill
  is moving toward the typical run.
- A star is a fact about a run, with no estimate in it and no advice, so that
  entry's other two rules ask nothing of it.

**Measured.** On the maintainer's stats folder on 2026-10-04: 8,880 runs over
866 scenarios, at the page defaults of Top N scores 5 and an oldest date of
January 1. The folder has grown since, so it no longer gives these counts.

- 480 scenarios have a run this year, so they have a chart. 691 runs this year
  were new PBs, and 284 of the 480 charts show at least one star.
- 666 of the 2,220 plotted points are stars (30%). The share falls as a
  scenario is played more: 240 of 1,195 (20%) on the 75 scenarios with 20 or
  more runs, and 24 of 208 (12%) on the 9 with 100 or more.
- 245 of the 666 stars (37%) are on a run that a later run the same day beat,
  and 174 of the 830 plotted days carry two or more stars. Those 245 are what
  the stars add over reading each day's top point, and a third of their
  density.

**Copy and term.** The legend entry is `New PB`, the short form of the
celebration toast's New personal best that the chart already uses in PB score.
The glossary gains New PB, with `new_high_score` as its code word. "PB run"
was taken: it is the one run that holds the PB now.

**Out of scope.** A hover line on a marked run, such as the PB it beat.
Keeping a new PB that the Top N filter drops, which would change which runs
the chart plots and the Average score line with them. A minimum run count or
margin before a run counts, which the celebration declined. New PBs anywhere
else: the playlist tables, the Aim Training Journey graph, or a list of them.
A trend or a verdict read from the stars.

Design in [#337](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/337),
implementation in [#346](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/346).

## 2026-10-04: Upgrades Skip Package Versions Younger Than A Week

Status: Accepted

uv ignores any package version published in the last seven days. A hijacked
package is usually caught and withdrawn within days, so the delay keeps one
out of the lockfile and out of the next release. A contributor who needs a
newer version sooner exempts that one package. A refresh holds the uv release
it pins to the same week, by hand.

**Ruling.** Ruled (user) 2026-10-04, in chat, on PR #340. The setting is
`exclude-newer = "7 days"` under `[tool.uv]` in `pyproject.toml`. It lands
with the first refresh after this entry, not with the entry: adding it changes
`uv.lock`, and a change to `uv.lock` cuts a release.

**Why.** Updates here are made by hand
([2026-10-04 entry](#2026-10-04-dependency-updates-stay-manual-run-from-a-playbook)),
and a plain `uv lock --upgrade` takes the newest version of everything. On
2026-10-04, 13 of the 25 pending updates would have resolved to a version
under seven days old. Merging a lock cuts a release, so those versions reach
installed copies.

**Why in `pyproject.toml`.** Measured under uv 0.12.13 on 2026-10-04. uv
records the setting in the lock's `[options]` as a span
(`exclude-newer-span = "P7D"`) beside a placeholder date, so the lock does not
go stale as time passes. `uv sync --locked`, which CI and the installer both
run, compares those options with the project's. Passing `--exclude-newer` only
on the upgrade command writes an option the project does not have, and
`uv sync --locked` then exits 1. Adding the setting to an existing lock moves
no package version.

**The exemption.** `exclude-newer-package = { <name> = false }` lifts the limit
for one package, and uv records it in the lock the same way. It is for a fix
that cannot wait a week, usually one for a security alert. It comes out at the
first refresh after the exempted version is a week old, never sooner: removed
while the version is still under the limit, `uv lock` moves the package back
to an older version and exits 0, which would undo the fix without a warning.

**The uv pin.** Ruled (user) 2026-10-05, in the review of PR #340: the same
week applies to the uv release a refresh pins. Every install downloads that
exact build and runs it, so the reasoning for packages holds at least as
strongly here. uv publishes often, with ten releases in the 23 days before
2026-10-04, so its latest release is usually days old. The setting cannot
enforce this, because it governs the packages uv resolves and not uv itself.
A refresh applies it by hand and pins the newest release at least a week old.

## 2026-10-04: Dependency Updates Stay Manual, Run From A Playbook

Status: Accepted

Dependencies and toolchain pins are updated by hand, about once a month, from
a written playbook. No bot opens update PRs, and no scheduled job reports what
is outdated. A contributor who wants newer versions runs the playbook at a
quiet point in the project.

**Ruling.** Ruled (user) 2026-10-04, in chat, on PR #340: updates stay manual,
and no bot opens update PRs. The scheduled check was skipped "for now", so it
is the part of this entry most likely to be revisited. The procedure is
[docs/dependency_refresh.md](dependency_refresh.md).

**Why no scheduled check.** It would answer a question whose answer is always
yes. On 2026-10-04, 22 days after the previous refresh, 25 of the 84 locked
packages had a newer release. The useful trigger is a quiet point in the
project, which a timer cannot see: the uv pin is exact, so moving it strands
every open branch on the old pin until that branch merges `main`.

**Why no bot PRs.** Three reasons, the first of them mechanical.

- Dependabot cannot run here. Its uv updater supports only the uv version it
  bundles, and rejects an exact `required-version` pin that differs. Another
  of the maintainer's repositories, on the same pin style, has failed every
  monthly Dependabot uv run since 2026-08-01 with
  `tool_version_not_supported`, and
  [dependabot-core issue 13199](https://github.com/dependabot/dependabot-core/issues/13199)
  was still open on 2026-10-04. The version Dependabot bundles was different
  on each of those three runs (0.11.8, then 0.12.7, then 0.12.18), so no exact
  pin could have kept up with it. The pin cannot be loosened to suit it: the
  release job reads the pin into `release.json` and refuses anything but an
  exact `==`, because every install provisions that version
  ([2026-07-19 entry](#2026-07-19-the-installer-brings-its-own-toolchain-app-locally)).
  Dependabot's security fix PRs run through the same updater, so they stay
  off as well.
- Renovate can refresh a uv lockfile, but it is a third-party app that needs
  write access. On 2026-10-04 `main` required only the CI check, and a merge
  that changes `uv.lock` cuts a release, so write access reaches installed
  copies.
- A green CI run does not make a version bump safe. plotly 7 put a new button
  on both charts, which only a look at the running app could show
  ([2026-09-12 entry](#2026-09-12-charts-keep-plotlyjs-4s-share-chart-button)),
  and ruff 0.16 changed which rules were enabled. Two of the four refreshes
  before this entry needed a judgment of that kind.

**What stays automatic.** Dependabot alerts only read the lockfile, so the pin
does not affect them; they have been on since 2026-08-30. The fix for an alert
is a single-package upgrade made by hand, as its own PR.

**The pinned GitHub Actions.** Ruled (user) 2026-10-04, in chat: they move
through the cross-repo tooling spec
([2026-07-06 entry](#2026-07-06-adopt-the-cross-repo-python-v2-tooling-spec)),
never in a refresh of this repository alone. The spec carries their SHAs, and
every repository that follows it carries the same ones. A refresh therefore
only reports a pin that is behind, and a bump arrives as a new version of the
spec.

## 2026-10-04: A Benchmark's Scenario Page Links To Its Evxl Page

Status: Accepted

A benchmark's scenario page now carries a View on Evxl link that opens the
same benchmark on Evxl in a new browser tab. Evxl shows what this app doesn't,
such as the overall rank a benchmark awards, and getting there used to mean
finding the benchmark on Evxl by hand. With a Steam ID set the link opens the
player's own sheet, and without one it opens the page where Evxl asks for a
profile. The app builds the address and requests nothing from Evxl itself.

**Agreed before the PR.** In chat on 2026-10-04 the maintainer agreed to the
placement, the header of the per-playlist scenario page, and asked for the
build. The rest of this entry is the author's, open to review: where the names
come from, the page a missing Steam ID falls back to, and the label "View on
Evxl".

**Addresses.** `https://evxl.app/u/{Steam ID}/{benchmark}/{difficulty}` with a
Steam ID, and `https://evxl.app/benchmarks/{benchmark}` without one. Both
names are Evxl's own, matched exactly and case-sensitively, and each is
percent-encoded as one path segment, so a `/` inside a name travels as `%2F`.
Neither address carries a query: Evxl appends `?tab=` from the visitor's
remembered tab, and a link that set one would override that choice. The
measurements are in
[kovaaks_api_notes.md](kovaaks_api_notes.md#evxl-benchmark-pages-linked-never-fetched).

**Where the names come from.** A bundled file carries the KovaaK's playlist
name, which is not Evxl's: "Viscose Benchmark S2 - Medium" is "Viscose
Benchmarks S2" and "Medium" there. `source/kovaaks/evxl_links.py` reads both
names from `resources/evxl/benchmarks.json`, the snapshot the importer
generates the bundled library from, once per process, keyed by playlist code.
The file already ships in the release zip, and the release's archive contract
names it, so a release that would ship without it fails its draft instead of
silently losing every link. Rejected: having the importer write
the names into each bundled file. That is the tidier data model, but it bumps
the generated schema and regenerates all 261 files against live KovaaK's
data, and the diff would carry whatever thresholds KovaaK's had changed since
the last refresh. The cost accepted
instead is that the running app now reads a file only the importer read
before. A snapshot that is missing or in another shape logs one warning and
removes the link, and nothing else. The importer refreshes the snapshot before
it generates, so the names move at the corpus's own cadence, and a benchmark
Evxl renames is a 404 until the next refresh.

**Matching a code.** Codes compare case-folded, because the snapshot has
carried a code in different letter case from the bundled file's. A code the
snapshot lists twice keeps its first listing, the one the importer generates
the file from.

**Which pages get it.** A benchmark's page, by the test that adds the Rank and
Next Rank columns, when the snapshot lists its code. A playlist's page never
gets it, whatever Evxl lists: the link goes with the rank columns.

**No Steam ID.** The profile-less page is the fallback rather than no link, so
the link doesn't silently vanish for a user who skipped the account setup, and
that address holds nothing personal. Evxl's profile-less page answers 404 for
a benchmark name holding `+`, `/`, `&`, or `:`, so those benchmarks show no
link until a Steam ID is set, which was 25 of the 261 bundled files on the day
it was measured. The code excludes the wider set JavaScript's `decodeURI`
leaves encoded, the likely cause, so that the unmeasured characters fail
toward no link instead of a broken one.

**A plain anchor.** The link is `html.A` with its own stylesheet class, not
`dmc.Anchor`. dash-mantine-components 2.8.0 bundles `@braintree/sanitize-url`,
which runs `decodeURIComponent` over an href and rebuilds it through `URL`, so
`%2F` reached the DOM as `/` and split "NRS 360 / Macro Benchmarks" into two
segments. Dash 4.4.1's `html.A` passes an href through
`dash_clientside.clean_url`, which returns it unchanged unless its scheme is
dangerous.

**Disclosure.** The user guide's What it talks to section names the link
beside the app's other browser-opened links and says its address holds the
Steam ID. It is not a row in that section's table, which lists what the app
itself reaches.

**Rejected.** A link in each row of the Playlists overview: the link is about
one benchmark, and the overview would carry the control on every row of a
library most of which a user doesn't play. The profile-less page for everyone:
it keeps the Steam ID out of the address, but drops the difficulty and costs a
click on every visit.

**Amended 2026-10-05: the link is Evxl's logo.** The link now shows Evxl's
logo and no text. "View on Evxl" stays, as the link's tooltip and its
accessible name. The addresses, the pages that get the link, and the new tab
are as this entry describes them.

- **Agreed in chat, not ruled.** On 2026-10-05 the maintainer chose the logo
  alone with a tooltip, after the app header's GitHub and Discord links. The
  author had recommended the logo in front of the text, because a logo alone
  means nothing to someone who doesn't know Evxl. The maintainer's answer was
  that Evxl is well known among aim trainers. The size, the placement, the
  tooltip on keyboard focus, and the wording of the permission record are the
  author's.
- **Permission.** Evxl's owner told the maintainer in a direct message that
  the app may use the logo, with no conditions. The logo stays its owner's
  and is under no open license, and `assets/icons/README.md` holds the
  record. The file is the site's 721×679 icon scaled down to 102×96 and
  otherwise untouched.
- **Bundled, never loaded from Evxl.** The logo is served from
  `assets/icons/` through `local_icon`. Loading it from evxl.app would make
  every benchmark page contact Evxl, and would break this entry's statement
  that the app requests nothing from Evxl.
- **Its name.** The logo is hidden from assistive technology, so an
  `aria-label` names the link. The tooltip opens on keyboard focus as well as
  on hover, which the header's two icon links don't do: it is the only place
  a sighted keyboard user can read where the link goes.
- **Focus ring.** The plain anchor had the browser's own ring, which in Edge
  is `rgb(16, 16, 16)`: 1.23:1 against the dark theme's page. The link now
  carries Mantine's `mantine-focus-auto` class, the ring `dmc.Anchor` brings.
  Measured in headless Edge on 2026-10-05 it is 3.56:1 on the light theme and
  3.09:1 on the dark one, against a floor of 3:1. Firefox was not measured.
- **Known cost.** The logo is cyan and can't be recolored without its owner's
  say. Rendered at its 24-pixel height it measures 2.0:1 against the light
  theme's page and 6.82:1 against the dark one's.

## 2026-10-04: The Scenario Table's Row Fields Use The Words On Screen

Status: Accepted

The code behind a playlist's scenario table now names its Position and PB
Score columns the way the screen does. The Position fields were named for
rank and sat beside fields named for tier that hold the Rank column, so the
two words were swapped against what a user sees. Nothing a user sees or has
saved changes. The rest of the code still says rank for a leaderboard
position.

**Direction.** The maintainer chose this on 2026-10-04, in chat, over leaving
every identifier as it was and over parking the question. It supersedes one
consequence of the
[2026-07-06 entry](#2026-07-06-one-word-per-concept-in-leaderboard-verbiage),
which kept row field names along with every other internal identifier.

**What changed.** On the row a scenario table draws, `rank_sort`,
`rank_display`, and `rank_pending` are now `position_sort`,
`position_display`, and `position_pending`, and `high_score_sort` and
`high_score_display` are now `pb_score_sort` and `pb_score_display`. The class
on a cell whose value is still loading was `playlist-rank-pending` and is now
`playlist-cell-pending`, because it marks the Position, Total Players, and
Percentile cells and never the Rank column. The Rank column's `tier_*` and
`next_tier_*` fields stay. Renaming them to `rank_*` in the same change would
have made `rank_sort` mean the position in one commit and the tier in the
next.

**Why only here.** `rank` has three meanings in code: a leaderboard position,
a benchmark tier, and KovaaK's own field name for the position. After this
change it still appears about 870 times under `source/` and about 1,650 under
`tests/` (counted 2026-10-04), and each use would need sorting into one of the
three by hand. Renaming every position use would still not make the code
consistent, because four kinds of name stay `rank` or cost something to
change:

- The fields KovaaK's sends, which the app cannot rename.
- The `rank` key and the `RANKED` and `UNRANKED` statuses, which are written
  to the cache.
- The `scenario_rank_cache_ttl_hours` config key, which a user's `config.toml`
  already holds.
- The `leaderboard/user_rank/` cache folder, whose rename would orphan every
  cached position.

A blanket rename moves the boundary between the two words. It does not remove
it. The scenario table was the one place where the two words met and pointed
the wrong way: `"position": "rank_sort"` beside `"rank": "tier_sort"` in the
table that maps `?sort=` names to column IDs.

**Consequences.** The names in `?sort=` are unchanged, so a link saved before
this change still sorts the table. `SORT_URL_NAMES` is the one place a name
meets a column ID, which is what the
[2026-09-27 entry](#2026-09-27-the-playlist-scenario-table-keeps-its-sort-in-the-page-url)
set it up for. No stored state keys on a row field name: the page's stores
hold nothing between visits, and the grid's column state is read only to
write the address. Everything else that says `rank` for a position is
unchanged, including `ScenarioRankInfo`, the Home page's component IDs, and
the cache. The [glossary](glossary.md) gives the code words as they now
stand. A new row field for a leaderboard position says `position`.

**Provenance.** No proposal. The change came out of a check of the glossary
against the code, whose docs-only half shipped in PR #333. Shipped in PR
#342.

## 2026-10-04: The Position Value Says When It Was Last Updated

Status: Accepted

Hovering the Position value on the Scenario Performance page now shows when
that position was last updated. A cached position can be a week old, and
nothing on screen told a fresh one from an old one. The age sits beside the
Refresh button, so it comes with a way to act on it. The playlist pages don't
show it, because they have no refresh of their own.

**Settled in chat, 2026-10-04.** The maintainer directed the Scenario
Performance-only scope. The wording is the maintainer's proposal, adopted over
the author's "Checked"; it was not separately ruled.

**Copy.** `Last updated {age} · {timestamp}`, as in `Last updated 3 days ago ·
Oct 1, 2026, 4:18 AM`. It is a status readout, so it takes no period.

**"Last updated", not "Checked".** The time is the rank cache entry's
`fetched_at`, which moves only when a leaderboard read is stored. A fetch that
fails leaves it alone, and so does an automatic read the monotonic writer
refuses
([2026-07-01](#2026-07-01-keep-scenario-rank-consistent-with-score-aware-refreshes)).
"Checked" describes what the app did and is false in both cases: with KovaaK's
unreachable for a month the app goes on trying, while the position on screen
is a month old. "Last updated" describes the data and holds in every case. It
does not mean the position moved, since a read that returns the same position
restarts the age.

**Scenario Performance only.** There the value sits beside **Refresh**, so an
age is a reason to click or not. The playlist scenario table has no refresh
control, so an age there is information with no action, and opening a playlist
already re-reads every entry past the cache lifetime, so nearly every row
would read under a week. Revisit if that table gains a refresh action. An age
always visible beside the value was rejected too: it would mark every routine
cache read, and the field keeps its marks for failures.

**The time is the position's alone.** The readout joins two caches, and the
leaderboard total carries its own time. A clicked Refresh and a PB catch-up
re-read both together
([2026-09-19](#2026-09-19-a-clicked-refresh-re-reads-the-leaderboard-total)),
but a lifetime-driven fetch does not, so the two can differ by up to the
lifetime. The hover dates the position and shows no second time.

**The tooltip is part of the layout, not of the value's children.** Home
rewrites the value on every polling tick, and Dash remounts component children
on each write. Built into the children, an open tooltip blinked off in 16 of
72 samples over four seconds, and the value's node was replaced between
samples, which would also drop keyboard focus (headless Edge, 2026-10-04). As
a fixed element whose label a store feeds, it held in 73 of 73, and the value
stays a plain text node. The age is worded in the browser by the helpers the
Last played hover uses, on the same 30-second tick.

## 2026-10-04: Skill Is Judged By The Typical Run, With Honest Uncertainty, In Verdicts Not Advice

Status: Accepted

The app's judgments about a player's skill are heading toward the typical
run, what their recent runs usually score, and away from the personal best,
which stays the achievement. A judgment the runs can't support says so
instead of guessing, and the app reports what it found without telling the
player what to do in training. One lucky run can make a scenario look
stronger than it usually plays, and the evidence behind any training method
is still thin. Every later proposal is held to these three rules, and Run
history now builds sessions first.

**Ruling.** Ruled (user) 2026-10-04, in chat, after both reviewers endorsed
each row:
[rows D1 to D5 of PR #327](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/327#issuecomment-5986985763)
as recommended, with D3's evidence bar as amended in review. D5, what the
roadmap's Future list holds, is recorded in the roadmap alone.

The rules themselves are in the roadmap's
[Guiding principles](roadmap.md#guiding-principles). This entry holds what
the roadmap doesn't: the reasons, the evidence and its limits, and the
options set aside.

**D1, the typical run.** Judgments about skill, meaning where the player is
weak, where their level stands, and whether they're improving, move toward
the typical run. The personal best stays the achievement: KovaaK's ranks it,
the app celebrates it, and the shipped Rank, Next Rank, Position, and
Percentile columns keep reporting it. The two answer different questions, how
a scenario usually plays and what the player has reached, so the app keeps
both. Judging skill by the personal best alone was rejected. A personal best
is one run, so a lucky one can rank a consistent scenario as weaker than a
spiky one that usually plays worse. It also only rises, so it can't show a
decline, and after one lucky run it reads as a plateau when there isn't one.
What counts as the typical run (the window, the run count, the warm-up rule)
is the Run History proposal's to set.

**D1's evidence, and its limits.** The evidence is one player's history,
checked on 2026-09-27. Ordering scenarios against each other by the typical
run tracked the level the next time each scenario was played better than
ordering by personal best: a rank correlation of 0.62 against 0.51, over
eight sessions. Within one scenario the two tied, with an error spread of
5.5% against 5.6% over 267 predictions across 69 scenarios, one per scenario
per session. Neither comparison shows that practicing in that order causes
more learning. A re-check of the ordering is due around 2026-10-09, and the
columns that would rank weakness this way wait for it. The research on
learning and performance supports judging learning apart from the scores
during a session. It doesn't validate a particular window or warm-up rule for
this app.

**D2, honest uncertainty.** Unknown isn't weak. A judgment with too little
behind it says so, and a scenario isn't ranked weak or strong until it has
enough: unknown rows form a group of their own and are never ranked among the
known ones. A figure that can only be a minimum is labelled one wherever it's
shown, such as time spent in runs, which leaves out the time between runs and
any attempt that wrote no stats file. An estimate is shown no more precisely
than it's known. Under-sampling is the common case: on 2026-09-25, 23 of the
39 scenarios in the maintainer's benchmark had fewer than 10 lifetime runs.
How much is enough isn't set here, and it isn't only a run count: the runs
also have to be comparable, and the estimate's model has to hold.

**D3, verdicts, not advice.** The app states facts and verdicts: the typical
run, a trend, a rank-up chance, "unknown", and whether a bar the player set,
such as the score threshold, was met. A result measured against something the
player set is still a verdict. Telling the player what to play or when to
stop is advice, and the app doesn't give it. The rule covers training
decisions only, so a notice that asks for a setting isn't advice. Verdicts
only is the simplest option and the easiest to reverse: adding advice later
is cheap, and taking away advice people rely on is not. It keeps one player's
regimen from being imposed on every user, and it matches what the app shows
today with one exception, which it retires. The cost is accepted: a "leave
now or keep going" line shrinks to the facts the player's own rule reads.

**The line D3 retires.** A run that passes the score threshold without
placing gets a toast that ends "Ready to move on.", which tells the player
when to stop. The
[2026-09-14 copy entry](#2026-09-14-app-copy-follows-one-set-of-rules-and-the-em-dash-is-gated-out)
kept that line under its D4, ruled 2026-09-12. By the bar set out here it's
a default rule the app vouches for, and no check came before it. Ruled
(user) 2026-10-04,
[in review](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/327#discussion_r4179636701):
the line is retired. That toast ends at the fact, and the placed variant and
every other toast are unchanged. D3 supersedes that D4 in part: its other
half, which dropped "Keep grinding...", stands. The string changed in
PR #341,
[a PR of its own](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/327#discussion_r4179646591),
as also ruled on 2026-10-04. That PR updated the notifications spec and the
pace proposal's Copy block with it, and added the supersession note to the
2026-09-14 entry.

Two options were set aside for now. Rules the player sets would add rule
semantics and a settings surface, and a default rule is advice by another
name. A built-in training method makes the strongest claim, and published
research supports general practice principles but no single aim-training
method.

**What would move D3.** Any move past verdicts takes a decision of its own.
What else it takes depends on what the app would be claiming.

- A rule the player writes, off until they write it and worded as theirs,
  claims nothing about training. It's an ordinary product decision: whether
  the convenience is worth a settings surface and the risk that it reads as
  the app's advice. The verdicts it reads ship first, and the player can
  override it and turn it off.
- A default rule or a built-in method is advice the app vouches for, so it
  takes strong evidence first. That means a check declared before its data
  comes in, measuring the benefit the rule claims, on results after the
  session rather than during it. A claim about learning needs retained
  performance, not a score from the same session.
- One player's results justify an opt-in experiment for that player. A method
  shipped to everyone needs evidence across players and tasks. The app
  collects none, so it would come from voluntary testing, results users
  supply, or published research.

**D4, Run history builds sessions first.** Sessions, and the visits inside
them, are built before either history view, as the foundation the views and
later features share. This reverses two durable decisions in the
[Run History proposal](proposals/run_history_proposal.md): "raw timestamps
first; sessions are a later quality-of-life layer", and the view order that
followed from it. Both are marked superseded there, with their text kept.
Nearly every planned feature needs sessions, and splitting the runs into them
is one pure pass over runs the app already holds in time order. Which view
ships first is open, for the proposal's rewrite to decide. The roadmap
carries the milestone's reasons and the Future list, which is planned work in
no particular order.

**Terms.** Typical run, visit, and rank-up chance are working words here, not
[glossary](glossary.md) terms: nothing ships them yet. The proposal that
ships each one names and defines it in its Terms block, and may rename it.

## 2026-09-30: A Glossary Says What The App's Own Terms Mean

Status: Accepted

The words the app uses for its own concepts now have one glossary that says
what each means. Their definitions were scattered across the repo, and code
names already disagreed with the words on screen. Each entry gives a term's
meaning, then its code name and its on-screen wording where those differ. A
term joins only once the app or the product doc has its concept, and a change
that makes an entry untrue corrects it in the same PR.

**Settled before the PR.** The maintainer settled two points on 2026-09-28, in
the kickoff for this work. The file is `docs/glossary.md`, titled Glossary:
*vocabulary* is already copy rule 7's word, and *terminology* names the
subject rather than the document. It holds shipped terms only, meaning the
app or `docs/product.md` already has the concept. The draft terms from the
product brainstorm, such as visit, warm-up run, and typical score, stay leans
until the proposal that ships them.

**Ruling.** Ruled (user) 2026-09-30, in chat, after both reviewers endorsed
each row: D1, D2, and D3 as recommended, then D4 as amended in review, with
four hooks.

**D1, an entry's scope.** The meaning, plus the code name and the on-screen
wording where they differ from the term: Position is `rank_*` in code, Rank
is `tier_*`, and PB is `high_score`. Meaning alone would leave out exactly the
mismatches that send a reader to the wrong field. An entry states the meaning
and links the spec for mechanics. KovaaK's own terms appear only inside the
entries for the app's terms, as Unranked and share code do. Challenge and
freeplay have no entries: no code or current doc defines either, and
*Challenge* appears only as a separator token in stats file names.

**D2, how terms arrive.** A proposal gathers the terms it adds or redefines in
a **Terms** block in Design, as it gathers strings in a Copy block, and the PR
that ships it moves the block into the glossary. A proposal opened before the
rule keeps its terms where they are, the Copy block's no-backfill convention;
its shipping PR still updates the glossary under D4's same-PR duty.

**D3, relation to the existing definitions.** The glossary holds meanings, and
AGENTS.md copy rule 7 keeps its on-screen wording rules; each links to the
other. The
[2026-07-03 importer entry](#2026-07-03-import-benchmarks-from-evxl-and-kovaaks)
(playlist and benchmark) and the
[2026-07-06 verbiage entry](#2026-07-06-one-word-per-concept-in-leaderboard-verbiage)
(Rank, Position, and PB) keep their definitions as history, unedited, and the
glossary links them. Folding rule 7's vocabulary line into the glossary was
rejected: it would take a wording rule out of the copy rules that copy review
reads.

**D4, hooks.** Four hooks, and no test. A Documentation Habits bullet makes
any PR that ships a new term, or makes an entry untrue, update the glossary in
the same PR, whether or not a proposal backs it, as the spec rule already does
for specs. A "Shipping a proposal" step moves a proposal's Terms block in and
corrects any entry the change makes untrue. The Terms block is described
beside the Copy block rule, and the Layout list names the file. The same-PR
duty is what keeps the glossary true: most PRs here ship without a proposal,
and the proposal path alone would let an entry go stale silently. Three hooks
on the proposal path alone were rejected for that reason. No test is
added, because the glossary is prose held by review, and a rename already
surfaces it to anyone who searches for the old name. The shipping step is
step 3, between the spec update and the deletion of the proposal file,
because the block has to move before the file goes. The steps after it move
down one, so the "Steps 4 and 5" of the
[2026-09-22 README entry](#2026-09-22-the-readme-is-a-front-door-and-user-reference-lives-in-a-user-guide)
are now steps 5 and 6.

## 2026-09-30: The Docs Test Counts Summary Sentences, And Its Count Is The Definition

Status: Accepted

The docs test now fails when a capability spec or a recent decision-log entry
opens with a summary outside two to four sentences. The test's own count is
what a sentence is, so a summary it miscounts is fixed by rephrasing, not by
arguing with the counter. It judges nothing else about the prose, and review
still holds every other summary rule. The cap kept coming back as a review
finding, and the earlier settlement that kept prose out of the test was about
Markdown rendering, never about counting.

**Ruling.** Ruled (user) 2026-09-28, in chat, accepting the recommendation
(D2), alongside the no-backfill wording (D1) and a two-PR sequence (D3). The
wording shipped first in
[#325](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/325), so
the two summary fixes below ride under its broken-summary clause.

**Scope.** Every `docs/specs/*.md`, whose summary is the first
blank-line-delimited paragraph after the H1. Every entry in this log whose
heading date is 2026-08-01 or later, whose summary is the first paragraph after
the whole `Status:` paragraph: a Status line wraps when it carries a
supersession note, and the first measuring counter, which stopped at its first
line, misread five entries that way. A supersession note therefore belongs
inside the Status paragraph or after the summary. Proposal TL;DRs,
`docs/product.md`, and the roadmap are not gated, and entries dated before
2026-08-01 predate the two-layer rule.

**One exemption, by name.** "2026-08-01: No Username Stays Fully Offline —
User-Independent Totals Rejected" carries the cutover date but opens with the
old `Decision:` shape: its commit `22ea0f8` (02:53 -0700) predates the rule's
commit `a0c5044` (10:06 -0700) the same day. It is named rather than matched by
shape, so a `Decision:` opener can't become a way around the gate, and a test
fails if the name stops matching a real entry.

**The count is the definition.** `count_sentences` in `tests/test_docs.py`
blanks code spans, keeps link text, drops the dots of e.g., i.e., vs., etc.,
cf., approx., decimals, and versions, and ends a sentence at terminal
punctuation, plus any closing quote, bracket, or star, followed by whitespace
and a capital, quote, backtick, star, or bracket. A fixture pins each shape.
The count is a floor: a sentence that opens with a digit or a lowercase word
doesn't split from the one before it. Review still holds the cap and the other
layer-1 rules: one idea per sentence, and no cross-references, paths, or
enumerations.

**Why this doesn't reopen #174.** The 2026-08-01 settlement that the test
"never judges prose quality or Markdown rendering fidelity" came from reviewers
escalating the section-order test into rendering edge cases, such as headings
inside an HTML comment opened mid-line or inside `<template>`. Rendering has an
external truth, what GitHub shows, so each new edge case was a real mismatch
and review could always find another. Sentence segmentation has none to
chase: the counter's output is the definition, so a disputed count closes by
rephrasing, and the regions are cut from the source text for the same reason.
Nobody evaluated a counter in #174. The cap itself recurred as a review finding
in #267, #268, and #275.

**The README word-count rejection stands.** The 2026-09-22 README entry
rejected a word-count gate because it "would fail unrelated PRs on an editorial
threshold". A README length is a line any feature PR can cross; the summary cap
is a ratified per-summary rule that only a PR editing that summary can break.
That entry's second reason, that the test "gates structure, never prose", is
narrowed by this one to everything but the summary count.

**Violations fixed first.** The gate found two summaries outside the cap on
main: `docs/specs/scenario_rank.md` at five sentences and the 2026-08-11
schema_version entry at six. Each was condensed in its own commit ahead of the
gate, nothing moved out of either payload, and every statement cut from a
summary was already in its payload. Those were the only two summaries flagged
across 6 specs and 58 entries.

**Supersedes in part** the 2026-08-01 Doc-Style Follow-Up entry's claim that
the test never judges prose, for the summary sentence count only, and amends
the 2026-09-22 README entry's "gates structure, never prose" reason the same
way. Both keep one Status paragraph.

## 2026-09-28: No Backfill Covers Missing Summaries, Not Broken Ones

Status: Accepted

The no-backfill rule now tells apart an entry with no summary and a summary
that breaks the rules. An entry written before the two-layer style still gains
its summary only when a payload change edits it anyway, never in a PR of its
own. A summary that breaks the rules is a defect, fixed as its own commit in a
PR that edits the file anyway or in a docs-only PR the maintainer asked for.
The old wording read as a bar on every standalone fix, so a known violation
waited on unrelated work.

**Ruling.** Ruled (user) 2026-09-28, in chat, accepting the recommended
wording over two alternatives. Relief only would invite unrequested
summary-only churn across the 55 entries dated before 2026-08-01. A bar leaves
a known violation waiting until an unrelated payload change happens to land,
then pushes the cleanup into that PR's diff against the rule that a drive-by
fix never shares a commit with the requested change.

**Two populations.**

- Legacy: an entry that predates the two-layer rule and has no summary. It
  gains one only when a payload change edits it anyway, never in a
  summary-only PR. This is the relief the original proposal meant by "The 54
  existing entries stay as they are" (`6d4eecf`).
- Broken: a summary that exists but breaks the layer-1 rules, such as one over
  the 2–4 sentence cap or one carrying a cross-reference, a path, or an
  enumeration. It is a defect, not legacy. It is brought into line as its own
  commit, in a PR that edits the file anyway or in a docs-only PR the
  maintainer asked for. An unrequested summary-only PR is still the backfill
  the rule refuses.
- "Payload change" closes the circular reading in which a summary edit is
  itself the change that licenses the summary edit.

**History.** The previous bullet read "existing entries are converted only
when a change touches them anyway".
[#267](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/267), a
standalone condensation of the notifications spec summary that the maintainer
asked for, drew a connector P1 that read "only when" as a necessary condition,
so a summary-only edit was the backfill the rule forbade. The implementer
contested that the clause was relief from a duty, not a bar. #267 closed
unmerged when #268, a real payload edit to the same spec, carried the same four
sentences. That settled the instance and left the wording open until this
ruling.

**Main already practised the split.** These merged summary fixes each rode
as their own commit, touching only the summary, in a PR that edited the file:
`e9e1aa2` and `a321393` (#302), `baa2296` (#307), and `8885cd0` (#319).

**Scope.** This supersedes in part the
[2026-08-01 Doc-Style Follow-Up entry](#2026-08-01-doc-style-follow-up--decisions-needed-roadmap-trim-no-log-index),
for its no-backfill sentence only. The earlier 2026-08-01 "Durable Docs Open
Plain" entry restates the same clause but was already superseded in full, so
it is left alone. The sibling no-backfill clauses in `AGENTS.md`, the Comment
and Docstring Conventions intro and the Copy paragraph's "same no-backfill
convention", need no edit: both spare existing items a sweep without barring a
fix.

## 2026-09-27: Benchmark Tables Show Each Scenario's Rank And The Gap To The Next One

Status: Accepted

A benchmark's scenario table now shows the rank each scenario's personal best
has reached, and how much that personal best has to grow, as a percentage, to
reach the next rank. Sorting the gap ascending lists the scenarios closest to
ranking up, a question that used to send the player to Evxl. Both columns come
from the bundled rank thresholds and the local personal best, so they appear
the moment the table opens and work offline. A plain playlist's table is
unchanged.

**Ruling.** Ratified (user) 2026-09-27 as a whole, after two review waves on
the proposal (PR #320, merged as `9dbf05a`; rulings recorded at `42488b9`).
Its two decision rows, D1 and D2, are below, each with the alternatives it
rejected. Everything else was author-owned and reviewed.

**D1: the gap is a percentage of the PB.** `(next threshold - PB) / PB * 100`,
computed only when the PB is above zero. It is defined below the first rank,
where no lower threshold exists, so every No rank row gets a real number; it
states the target to beat; and it matches the Scenario Performance score
threshold, which is also a percentage of the PB. It is scale-free, so
thresholds from 1 to 1,630,000 share one column, but it is not
difficulty-normalized: every percent counts the same, so a compressed score
scale always looks closer. The honest cost is against the rejected band
fraction (how far the PB sits through its current band, KovaaK's own
progress idea). Band widths vary, a median +8.3% of the lower threshold (p10
+3.5%, p90 +18.9%) across the corpus's 23,791 strictly ascending bands, about
as much across scenarios as within a ladder. A simulation that placed a
player in the same band on every scenario of a benchmark found the two
metrics pick a different closest scenario in 22% of 40,920 trials, median
Kendall τ 0.74 between their orders. What decided it is the first rank: a band
fraction needs an invented floor there, and 4,380 of 4,384 ladders start
above zero. Also rejected: the PB as a percentage of the next threshold (same
order, but the closest rows sort descending and it reads as progress rather
than a target), and points needed (the roadmap's "+47 to Gold"), which can't
be compared across score scales and so lives in the cell tooltip instead.

**D2: the PB is the local all-time high.** `ScenarioStats.high_score`, the
row's own PB Score, so a row agrees with itself, fills with no username and
before the fill, and follows KovaaK's rule that a rank is the best score ever
set. Rejected: the leaderboard score the position lookup returns, which
arrives only in the fill, is absent with no username or a failed lookup, and
can disagree with PB Score beside it; and recent form, which needs a window
decision of its own and would disagree with the rank KovaaK's shows. Recent
form is deferred to the own-runs difficulty follow-up on the roadmap.

**The ladder walk.** Walk from the bottom and stop at the first threshold
above the PB; a PB equal to a threshold has reached it. The last rank passed
is Rank (none passed: "No rank"), and the rank the walk stopped at is the
next rank (every rank passed: "Top rank"). The ladder keeps its stored order
and is never sorted. At `ea5b757` the corpus held 4,384 ladders: 4,367
strictly ascending, 7 with a tie (a ladder ending `142, 142`), 10
non-monotonic (an early dip `36, 54, 50, …`, a mid dip `2800, 2850, 2900,
2950, 2900, …`, a final descent `…, 2000, 1933`), and 4 with a zero threshold
(`0, 250, …`, `0, 0, 0, 0`). These are upstream data errors the importer
carries faithfully. The walk never grants a rank whose own threshold, or any
threshold below it on the ladder, is unmet, and the next threshold is always
above the PB, so every gap and every tooltip's points are positive. Rejected:
the last rank whose threshold the PB beats (claims a rank past an unmet
threshold), and the count of beaten thresholds (claims a rank whose own
threshold is unmet, then points Next Rank at a threshold the PB already
beats, a negative gap). The chart's threshold lines are unaffected: they
select by value and compute no rank.

**Precedence.** No PB: both columns `N/A`. Otherwise Top rank wins, whatever
the PB, so a PB of 0 on the all-zero ladder reads Top rank. Only then does a
PB of zero or less make Next Rank `N/A`. An `N/A` Next Rank carries no
tooltip, even when a next rank exists (a PB of 0 on `0, 250, …`), which keeps
`N/A` one uniform state. A benchmark scenario with no ladder reads `N/A` in
both columns; the corpus has none, but a hand-edited file could.

**Display.** Each displayed value is
`max(floor, ceil(round(x * 10**d, 6)) / 10**d)`: the gap with `d = 1`, floor
0.1, formatted `f"{gap:,.1f}"` (a PB of 50 against 940 reads `+1,780.0%`);
the tooltip's points with `d = 2`, floor 0.01. Thresholds and points format
through `_format_score`, as PB Score does. Rounding up keeps a remaining gap
from reading as reached (999.96 against 1,000 reads `+0.1%`). The floors are
needed, not just safe: run files record up to six decimals (1,388 of the
maintainer's 8,665 runs on 2026-09-27), so 9,999.999999 against 10,000 would
ceil to `+0.0%` and 999.999999999 against 1,000 to `0 to go`. The inner
`round` strips float noise: for PB 2.8 against 3.08 the gap computes as
`10.000000000000009` and the difference as `0.28000000000000025`, which a
bare ceiling shows as `+10.1%` and `0.29 to go`. It runs after scaling,
because `0.28 * 100` is itself `28.000000000000004`. Sort keys and the
comparison with the threshold stay unrounded, so PB Score beside such a PB
still reads `1,000`, and the tooltip is what shows a gap remains.

**Rows, fields, and columns.** `benchmark_rank_fields` in
`source/kovaaks/playlist_scenarios_service.py` is a pure function of a
ladder and a PB, with no Dash dependency; it moves out if another page
adopts the columns. It fills five row fields: `tier_display`, `tier_sort`
(ranks passed, so No rank is 0), `next_tier_display`, `next_tier_sort` (the
unrounded gap), and `next_tier_tooltip`. *Tier* avoids the legacy `rank_*`
fields, which hold the leaderboard position
([2026-07-06](#2026-07-06-one-word-per-concept-in-leaderboard-verbiage)).
A table is a benchmark's when `any(scenario.ranks …)` holds, the overview's
Type test (`is_benchmark_playlist`), and a plain playlist's rows carry none
of the fields. The two columns sit directly after Scenario with their header
tooltips; both sort with `nullsLastComparator`, so Rank puts No rank lowest
and `N/A` last in both directions, and Next Rank puts Top rank and `N/A` last
in both directions. Both join the auto-size keys.

**All three row paths carry the ladder.** Rows come from phase 1, the fill,
and a cancelled fill's rebuild on its first terminal drain
([2026-07-15](#2026-07-15-stream-playlist-positions-with-generation-scoped-progressive-fill)).
The last two are AG Grid update transactions, which replace a row's data
whole, so a row built without its ladder would flip Rank and Next Rank to
`N/A` until the page reopens. A cancelled fill is ordinary: opening any
playlist in a second tab cancels the first tab's. `_FillState` therefore
captures each scenario's ladder at registration, from the same playlist
object as `scenario_names`, and releases the ladders with the names on
terminal consumption. `_build_row` takes the ladder as a required keyword,
so mypy flags a path that forgets it; `None` means a plain playlist's row and
an empty list a benchmark scenario without a ladder.

**Sort names, checked per page.** `?sort=` gains `rank` for Rank and
`next-rank` for Next Rank; the name table already reserved `rank` for the
tier
([2026-09-27](#2026-09-27-the-playlist-scenario-table-keeps-its-sort-in-the-page-url)).
`SORT_URL_NAMES` stays one page-independent table, so `_parse_sort` checks
each name against the columns the page actually has. A name for a missing
column invalidates the whole value, as an unknown name does, so the table
opens unsorted and the value leaves the address. Without the check,
`?sort=next-rank.asc` on a plain playlist raised
`KeyError: 'next_tier_sort'` while building the column defs.

**"No rank", not "Unranked".** *Unranked* already means "no leaderboard
entry" in the Position column, and one row can show both. KovaaK's own ladder
calls tier 0 "No Rank".

**Out of scope.** Rank and gap on the Scenario Performance page, whose chart
already draws each threshold. A benchmark-level rank: benchmarks combine
scenario ranks by their own rules, which the ladder data doesn't carry (Anima
Micro Benchmark v2 ranks each subcategory by its best scenario and takes the
lowest subcategory), so Next Rank is always that scenario's own next rank. Rank colors, whose upstream
near-white and pale-yellow values don't read on the light theme. Difficulty
measured against the player's own runs, with recent form, a roadmap Future
entry. Refreshing the table when a run lands: like PB Score, both columns
stay as they were until the page reopens.

**Superseded in part (2026-09-28).** The two columns now sit directly after
PB Score, not after Scenario, at the maintainer's direction. Both compute from
PB Score, so a row reads left to right from the score to the rank it reached
and the gap to the next one, and the points in Next Rank's tooltip sit beside
the score they count from. The accepted cost is that a narrow window has to
scroll sideways to show them, where the old placement kept them in view. The
placement was author-owned, not a ratified row, and D1, D2, and everything
else here stand. Shipped in PR #323.

**Superseded in part (2026-10-05).** On a time-scored scenario, wherever the
app can measure pace, D1's gap is a pace gap: how much faster the PB run has
to finish to reach the next rank, shown as "2.8% faster to Lavender". There,
D1's `N/A` for a PB of zero or less applies only where pace is undefined.
Every other row keeps D1 as written, and the ladder walk, the Rank column,
the rounding, the sort, and the tooltip are unchanged for all rows. The
[2026-10-05 entry](#2026-10-05-time-scored-scenarios-are-measured-by-pace)
holds the formula and the reasons. Shipped in PR #343.

**Provenance.** Proposal by `claude-opus-5-5` (PR #320), reviewed by
`gpt-6-sol` and, as a supplementary seat, `claude-fable-5-1`. Shipped in PR
#321.

## 2026-09-27: Sensitivity Precision Is Fixed Per Scale, And Its Config Knob Is Retired

Status: Accepted

A run's sensitivity is now rounded according to its scale, and the setting
that used to control the rounding is gone. Sensitivities in cm/360 always
round to one decimal place, which was already the default. Runs from old stats
files that keep a game's own scale now show exactly the number the player
typed, so 0.32 Valorant no longer reads as 0.3. A user who had changed the
setting loses that change without notice, and a leftover line in the config
file only logs a warning.

**Ruling.** Ruled (user) 2026-09-27, in a decisions chat, after independent
second opinions from `claude-fable-5-1` and `gpt-6-astra`, both of which
endorsed this shape. `sens_round_decimal_places` dates from play on Valorant
sensitivity. Since the
[2026-09-11 conversion](#2026-09-11-sensitivities-normalize-to-cm360-at-parse-time-from-the-files-own-increment-and-dpi)
nearly every run is cm/360 at parse time, and the knob did two contradictory
jobs with one number. On cm/360 it merges formula output into groups, which
wants one decimal. On a legacy run that keeps its game scale it should
preserve what the player typed, which one decimal breaks.

**The rule.** `extract_data_from_file` in `source/kovaaks/data_service.py`
rounds a cm/360 value to `CM360_DECIMAL_PLACES`, one: a converted value inside
`_converted_cm360`'s validation guard as before, so a conversion that rounds
away still falls back, and a native value on the fallback branch. Any other
scale reaching the fallback branch (a legacy file without `Sens Increment` and
`DPI`, a field the conversion cannot use, or a conversion that rounds away)
keeps the parsed `Horiz Sens` float untouched. `RecordedSensitivity` was
already unrounded and is unchanged. `sensitivity_key` is
`f"{horizontal_sens} {sens_scale}"`, so the rule reaches grouping, Top N
placement, averages, first-sensitivity notifications, and the plot axis and
hover. The PB cm/360 column skips every scale but cm/360 and sees no change.

**Decimal bucketing, not a tolerance.** The cm/360 rounding exists so that a
typed value and a converted one a few hundredths apart share a group:
`0.2 Valorant` at 1600 DPI converts to 40.84 and joins a typed 40.8. Its edges
are hard. 40.849 and 40.851 land in 40.8 and 40.9, and nothing merges values
by distance.

**Evidence.** Measured 2026-09-27 over the maintainer's stats folder, 8,666
files. The 8,096 cm/360 runs group identically at one and two decimals, 1,418
groups over 810 scenarios: native cm/360 values are all whole numbers, and
converted ones take six distinct values. Of the 570 legacy runs (475
Overwatch, 95 Valorant), one decimal got 170 wrong: `0.32 Valorant` read `0.3`
(95 runs), and Overwatch `2.38` merged into `2.4` (24) and `4.75` into `4.8`
(51). The raw `Horiz Sens:` text across all files is 37 distinct short
decimals, such as `40.0`, `0.32`, and `4.75`, so "as recorded" is exact.
Rejected: two decimals for game scales, which would still corrupt a
three-decimal setting (`round(0.235, 2) == 0.23`, `round(1.125, 2) == 1.12`).

**The retired key.** The `ConfigData` field and its `example.toml` block are
deleted, with no bound, migration, or special case. `_warn_unknown_keys`
tolerates unknown keys permanently, so a `config.toml` still carrying the key
loads and names it in the existing unknown-key warning. A public user who had
set a non-default value loses it silently; the reviewers judged that
negligible one day after launch. No cache persists sensitivities and the run
store rebuilds from the stats folder at every start, so nothing migrates.
Rolling back to a release that still requires the key needs the literal line
`sens_round_decimal_places = 1`, which the user guide's rollback instructions
under [Manual install](user_guide.md#manual-install) give.

Supersedes, in part, the
[2026-09-11 sensitivity-normalization entry](#2026-09-11-sensitivities-normalize-to-cm360-at-parse-time-from-the-files-own-increment-and-dpi):
its "The rounding fix does not reach legacy runs" paragraph only. Everything
else there stands; where it names `sens_round_decimal_places` or the
configured precision for a conversion, the precision is now this fixed one
decimal place, the value the knob shipped with. This also closes the case the
[2026-09-27 PB-format entry](#2026-09-27-the-scenario-table-drops-trailing-zeros-from-pb-score-and-pb-cm360)
left open: every stored cm/360 value carries one decimal, so the PB cm/360
column's two decimals are always exact.

**Provenance.** No proposal: the ruling went straight to a standalone
implementation. Shipped in PR #319.

## 2026-09-27: The Manual-Refresh Hard Failure Stays Red

Status: Accepted

When a clicked position refresh gets nothing usable back, its toast stays red
instead of softening to yellow. The app's color scale reserves red for an
operation that failed, and a refresh the user asked for that returned nothing
is exactly that. The outcome that falls back to a cached position stays
yellow, so the two still differ by color as well as by title.

**Ruling.** Ruled (user) 2026-09-27, in a decisions chat. It closes the color
question the 2026-08-03 notification entry left open in `docs/tech_debt.md`
("Manual-refresh failure color"), whose precondition, a title of its own for
the served-stale toast, the 2026-09-14 copy sweep met. Nothing in the code
changes: `_rank_refresh_problem_notification` in `source/pages/home.py` stays
red "Position refresh failed" for a hard failure and yellow "Refresh failed ·
data from cache" for a served-stale one, on one `rank-refresh-problem`
channel.

**Why red.** The severity scale makes red an operation that failed and yellow
caution without anything having failed
([2026-08-30](#2026-08-30-one-severity-color-language-for-inline-notices)).
The routing policy gives a user-initiated failure, manual Refresh named among
them, an error toast, and its peers are red: "Playlist import failed",
"Cleanup failed", "Skip wasn't saved". For this pair the scale reads as
whether anything usable came back: the served-stale outcome returned a cached
position, the hard failure returned nothing.

**The argument for yellow, rejected.** From the user's seat both outcomes
leave an older position on screen: the hard failure leaves the field
untouched, and the served-stale one re-serves the cache, so only the
service's confirmation of the fallback differs. That is why they share one
channel, but softening one toast turns the scale into an exception list for
little gain, since an icon-bearing notification shows its color only as the
icon's circle, not as Mantine's full-height bar.

## 2026-09-27: The Scenario Table Drops Trailing Zeros From PB Score And PB cm/360

Status: Accepted

The playlist scenario table shows PB Score and PB cm/360 with up to two
decimals and drops trailing zeros, so one column can read 710 beside 863.94.
Audits kept flagging this as ragged decimals, and it is now ruled the intended
style rather than a defect. The same rule makes the table show a sensitivity
of 50 where the chart says 50.0 cm/360, and that difference is accepted too.

**Ruling.** Ruled (user) 2026-09-27, in a decisions chat, on finding P8 of
the 2026-07-12 UI audit, which proposed fixed precision (two decimals for
scores, one for cm/360) and which every audit since re-raised as unruled.
Both halves: stripping stays within a column (won't-fix), and the
table-versus-chart difference for PB cm/360 stays. `_format_score` in
`source/kovaaks/playlist_scenarios_service.py` formats both columns as
`f"{value:,.2f}"` with trailing zeros and a bare point stripped; PB Accuracy
keeps its fixed two decimals.

**Why not fixed precision.** Fixed decimals pay off when a reader compares
values by lined-up decimal points. The table's columns are left-aligned, and
each row is a different scenario with its own score scale, so no comparison
runs down the PB Score column, and `.00` on a whole-number scenario is noise.
Right-aligning the numeric columns is a separate question this ruling does
not take up.

**Why the chart keeps `50.0 cm/360`.** The chart's axis and hover and the run
toasts print `f"{horizontal_sens} {sens_scale}"`, which is also
`sensitivity_key`, the Score vs Sensitivity grouping and first-sensitivity
key. A chart reading `50 cm/360` would need a display-only string at plot
time, never a change to the key, and the table already shows the same number.
Rejected: a `docs/tech_debt.md` entry for the difference, since an entry
nobody plans to work on is what kept the finding coming back.

**Exactness.** Two decimals lose nothing while stored sensitivities carry two
decimals or fewer, which holds at the shipped `sens_round_decimal_places` of
one. A configured value above two would let the chart read `50.125` beside a
table rounded to two places. That case stays open until the knob's removal
ships: the same chat ruled the removal, with cm/360 fixed at one decimal, and
queued it as a separate implementation.
*(Resolved 2026-09-27: the knob is retired and every stored cm/360 value
carries one decimal place, so the case can't arise. See
[Sensitivity Precision Is Fixed Per Scale, And Its Config Knob Is Retired](#2026-09-27-sensitivity-precision-is-fixed-per-scale-and-its-config-knob-is-retired).)*

## 2026-09-27: The Playlist Scenario Table Keeps Its Sort In The Page URL

Status: Accepted (amended by
[2026-10-05](#2026-10-05-a-columns-menu-shows-and-hides-table-columns-and-kovaaks-ids-are-optional-ones):
a sort on a column the Columns menu has hidden is cleared, on arrival too, so
Back, Forward, a reload, and a copied link no longer restore or keep that one
sort)

A sort on a playlist's scenario table used to be lost as soon as you left the
page. The sort now rides in the page's address, so Back, Forward, a reload,
or a copied link reopens the table sorted the way it was left. A fresh visit
from the Playlists page still starts unsorted, in playlist order. Sorting adds
no history entries, so one Back still leaves the page.

**Ruling.** Ruled (user) 2026-09-27, in the design chat that produced the
kickoff: the sort belongs to the browser-history entry, carried in the page
URL as `?sort=`. Back and Forward restore that entry's sort; a fresh visit
(navbar, then Playlists, then a playlist) starts unsorted, because the user
is "starting a new trail rather than backtracking a breadcrumb"; a reload or
a copied link keeps it. Each tab's entries are its own, so two tabs on one
playlist keep separate sorts. One standalone PR, no proposal.

**Format and names.** `?sort=<name>.<dir>[,<name>.<dir>…]`, list order is
sort priority, `dir` is `asc` or `desc`, and the commas stay literal. The
names, ruled verbatim as address-bar copy: `scenario`, `last-played`,
`runs`, `position`, `total-players`, `percentile`, `pb-score`, `pb-date`,
`pb-cm360`, `pb-accuracy`. `SORT_URL_NAMES` in `playlist_scenarios.py` is
the one table from name to column ID; the clientside writer receives it
through `json.dumps`, never a hand copy. Column IDs are unchanged, because
other code keys on them: `AUTO_SIZE_COLUMN_KEYS`, the relative-time
refresh's column list, and `route_to_scenario_home`'s `"scenario"` check.
Names, not IDs, because `rank_sort` would put "rank" in the address and Rank
is the benchmark tier, and because a saved link survives a later field
rename.

**Restore is a server-side seed.** Dash Pages passes query parameters to
`layout` (`parse_qs(keep_blank_values=True)`, so `?sort=` arrives as `""`
and a repeated parameter as a list). A value that is not entirely valid
means unsorted, silently: empty, repeated, an unknown name, a missing or bad
direction, a duplicate name (which also caps the list at one entry per
column), or any other case or spelling. No valid part of a mixed value is
kept. Each call deep-copies `TABLE_COLUMN_DEFS`, a module constant shared
across requests, and sets `initialSort`/`initialSortIndex` on the named
columns. Never `sort`/`sortIndex`: in AG Grid 35.3.1, `SortService.initCol`
seeds a new column from either pair, but `_updateColumnState` reapplies only
`sort`/`sortIndex` when column defs are sent again, which would override the
user's header clicks. Never a `columnState` prop either: dash-ag-grid applies
a Dash-written `columnState` with `applyOrder: true`.

**Write is a raw `replaceState`.** One clientside callback reads the grid's
`columnState`, which dash-ag-grid 35.3.0 publishes when its API initializes,
after autosize, immediately on a sort, and 500 ms after a resize or a
displayed-columns change, and never after unmount. The callback ignores
anything that is not an initialized column-state array (non-empty, every
entry with a `colId`): the initial call has none, and reading that as
unsorted would strip `?sort=` on arrival. It writes only when the value
differs from the address's `sort`, so opening a sorted page writes nothing
and an invalid value is removed by the grid's first publish. It writes only
while `location.pathname` is still `/playlists/<code>`, compared raw because
Dash Pages hands the page its path segment undecoded; a row click moves the
address before the grid unmounts. `history.replaceState(history.state, "",
url)` changes only the `sort` key and keeps every other parameter and the
hash; a cleared sort removes the key. Not through `dcc.Location`, an
external constraint of dash 4.4.1: `updateLocation` pushes a new history
entry whenever a location prop changes and, with `refresh="callback-nav"`,
dispatches `_dashprivate_pushstate`, which makes Pages re-render the page;
its only listeners are `popstate` and `_dashprivate_pushstate`, so a raw
`replaceState` is invisible to Dash. The page's own Location keeps receiving
only `href`: a `pathname` output would push the pathname plus the Location's
stale `search`, which predates every rewrite.

**Rejected alternatives.**

- One localStorage sort for every playlist, the kickoff's earlier draft: it
  breaks the fresh-visit rule, the grid's unsorted first publish can erase
  the saved sort on mount, and tabs overwrite each other.
- `persistence` with `persisted_props=["columnState"]`: it also keeps column
  widths and order, and it restores on fresh visits.
- `history.state` or per-entry sessionStorage: both need a client-side
  restore that races the grid's mount, and neither can be tested with
  pytest.

**Out of scope.** The Playlists overview grid defaults to Last Played,
newest first, and remembers no sort the user picks. It writes
`Output("playlists-location", "pathname")`, so if it ever adopts this
pattern that output would carry a stale `?sort=`. Filters, column widths and
order, and a reset control are not kept either; clearing through the header
is the reset. Fast Back/Forward presses get no safeguard: the address check
cannot tell apart two entries with the same address, but a rapid
Back/Forward/Back live check did not reproduce a mismatch.

**Provenance.** No proposal: the maintainer ruled the direction and the
process on 2026-09-27. Three models reviewed the design and agreed on it:
`claude-opus-5-5`, `claude-fable-5-1`, and `gpt-6-astra`. Shipped in PR
#316.

**Superseded in part (2026-10-04).** The column ID this entry names,
`rank_sort`, is now `position_sort`, and the PB Score column's ID is now
`pb_score_sort`. The names in the address did not change, so a link saved
before the rename still sorts the table
([2026-10-04](#2026-10-04-the-scenario-tables-row-fields-use-the-words-on-screen)).

## 2026-09-26: Log Lines Delimit Their Values By Kind

Status: Accepted

Log lines had no written convention, so the same scenario name, playlist
name, or file path appeared bare, in parentheses, in single quotes, or as a
Python repr depending on who wrote the line. Nearly every name contains a
space, and the debug log travels with bug reports to a reader who can't
re-run what happened, so a name with no visible start or end is a misread
waiting to happen. Names and paths now sit in double quotes, codes and counts
stay bare, and a value the app hasn't checked yet is shown exactly as
received. Every existing line was changed to match in one pass, and a caught
exception reaches the log by one of three written routes.

**The rule.** AGENTS.md's Logging Conventions section carries the operative
form. It governs how a value is delimited, never whether it may be logged:
the identity probe's persona names and a `sensitive` request's parameters
stay out of the log where they are handled, and nothing here changes that.

**What was measured.** Commit-scoped: an AST walk over a `git archive`
export of `origin/main`, first at `8aa47fd` on 2026-09-19, then at `88060d9`
on 2026-09-25, and again by the shipping PR at `47cd578` on 2026-09-26 with
identical counts. 163 logging calls in 19 files under `source/`, all on a
module-level `logger`, none an f-string (ruff's `G` rules are on); 273
placeholders: `%s` 200, `%d` 47, `%f` 19, `%g` 4, `%r` 3. Each of the 203
string placeholders was read and its argument recorded in a table of 87
distinct expressions; an expression the table did not know was reported,
never guessed.

| Kind | Placeholders | How it was delimited |
| --- | --- | --- |
| Names and other outside text | 61 | 56 bare, 4 in parentheses, 1 `%r` |
| Codes and keys the user typed | 8 | 7 bare, 1 single-quoted |
| Paths and file names | 34 | 33 bare, 1 double-quoted inside its argument |
| Tokens rendered as strings | 71 | 56 bare, 11 in parentheses, 2 single-quoted, 2 `%r` |
| Request summaries | 11 | all last, after a colon |
| Exceptions interpolated | 8 | 7 last after a colon, 1 in parentheses |
| Pre-built messages | 5 | all last, after a colon |
| Collections | 5 | Python's container repr |

The 103 free-text and path placeholders sat in 100 calls: 53 with prose
after the value, 5 in parentheses, 44 ending the message, and 1 already
quoted. A playlist code was single-quoted in one module and parenthesized,
after a colon, or bare in another. The bundled corpus at the same commit
holds 3177 scenario names and 257 playlist names: 96.5% and 96.9% contain a
space, 62 an apostrophe, 35 a parenthesis, 7 a bracket, and none a double
quote. The sweep changed 104 placeholders in 101 calls across 17 files and
broke 24 test assertions in 10 test files, every one an assertion on rendered
log text, each updated to assert the quoted rendering.

**The decisions**, all ratified by the maintainer on 2026-09-26.

- *D1, free text takes `"%s"` wherever it sits.* Of the three candidate
  delimiters the double quote is the only one no bundled name contains. It
  is what copy already does for the same values (`"{label}"` for a playlist,
  `"{username}"` for a user name), and it never escapes, so a search of the
  log for a reported name always hits. A code or key the user typed takes
  `%r` until validation accepts it: a clipboard can carry a double quote or
  an invisible character, and a zero-width space survives `strip()`, so a
  pasted code renders as `'KovaaKsXyz\u200b'` under `%r` and as nothing
  under `"%s"`. The eight such lines are the six that log a pasted playlist
  code, the import line, and the unknown config keys, which now log the list
  itself. Once validation accepts a code it is a token and stays bare.
  Rejected: `%r` for all free text, which flips to a double-quoted repr for
  the 62 names with an apostrophe, stops matching a log search once it
  escapes, and cannot serve paths; `"%s"` for typed codes too, which leaves
  the values that can hold a double quote or an invisible character as the
  ones the delimiter cannot bound; and no rule, where an empty value renders
  as nothing and `for %s (leaderboard %s)` turns `Tracking Benchmarks (Easy)`
  into two parenthesized groups.
- *The KovaaK's username, the one D1 point a reviewer contested.* The
  username is typed and then validated against KovaaK's, but it is a name,
  not a code, so it takes `"%s"` before and after validation, as copy quotes
  it. The counter was `%r` until KovaaK's confirms it, treating every typed
  value alike. What settled it is that the name's exact characters already
  reach the log: every attempt of the total-play request that validates it
  logs its parameters at DEBUG, and a dict renders its values with `repr`, so
  a pasted zero-width space shows as `'Pasu\u200b'` on the request line of
  the lookup that got KovaaK's answer. That line need not sit near the
  rejection: a rejection served from the cached unknown-user marker sends no
  request, so the escaped name is on the line of the earlier lookup whose
  answer the marker records. `%r` for the username would have added
  locality, not information, and cost two moved placeholders (the lines that
  log the username when the total-play lookup failed with no cached answer,
  both network failures) plus a third divergence from copy rule 6.
- *D2, paths take the same `"%s"`.* A Windows path cannot contain a double
  quote, so the delimiter cannot collide, and the quoted form is what
  Windows produces for Copy as path. `%r` cannot serve: it doubles every
  backslash in a `str`, renders a `Path` as `WindowsPath('C:/...')`, and
  switches to double quotes, the delimiter D1 reserves, when the path holds
  an apostrophe. Rejected: bare paths, always last after a colon, which keeps
  a path pasteable with nothing to trim but cannot hold two paths in one line
  (the unusable-store backup line names the file and its copy), would have
  needed 18 sentences rebuilt around the path, and leaves an empty or
  whitespace-tailed path invisible.
- *D3, a caught exception reaches the log one of three ways, keyed on what
  can reach the handler.* Before the rule, 55 calls logged an exception: 36
  with a traceback, 11 through `request_exception_summary`, and 8 by bare
  `%s`. In five of the eight, everything that could reach the handler carried
  a message. The identity probe's `except ValueError` is one of them, and is
  safe only because its callee raises four handwritten `ValueError`s and
  nothing else in the `try` can raise one, which is why the test cannot be
  read off the `except` clause. The other three caught broadly, and what
  reached them included `requests` exceptions that bypassed the summary
  helper and types that can carry no message. Bare `%s` is the hazard: `TimeoutError()` renders as nothing,
  `KeyError("steamId")` as `'steamId'`, and `str()` of a bare `OSError()`
  or `ValueError()` is empty too, so every route keeps the floor that the
  words before the colon name the failure. The `requests` route exists for
  privacy: a `requests` failure's `str`, `repr`, and logged traceback all
  carry the query string (measured on Python 3.14.6), so no handler a
  `sensitive` request's failure can reach may interpolate it or take a
  traceback. Rejected: `%r` on every exception logged without a traceback,
  which renders the app's own messages, full of contractions and double
  quotes, with backslash escapes, drops the filename from an `OSError`, and
  changes all eight lines instead of three; a class-name fallback helper for
  every interpolated exception, which the floor makes unnecessary.
- *D4, one full sweep, in the PR that lands the rule.* The comment and
  docstring conventions
  ([2026-09-04](#2026-09-04-comment-and-docstring-conventions)) took no
  backfill because they transcribed a style the tree already followed nine
  times in ten; here 1 of 103 placeholders did. Agents in this repository
  learn house style from neighboring code at least as much as from the
  instructions, so an unswept tree would teach bare `%s` on every edit. The
  sweep is also what makes `%r` legible: a single-quoted placeholder value
  now means "shown as received, not vouched for", which three hand-quoted
  formats would otherwise have contradicted until someone edited them. It was
  cheapest before the public launch, after which bug-report logs in two
  formats would coexist for as long as old installs do. Rejected: no
  backfill, a mixed log for as long as the lines go unedited; a targeted
  sweep of only the values with prose after them or parentheses around them
  (60 placeholders, 58 calls, 11 failing tests), which leaves 44 bare values
  at line ends and a two-branch rule.

**Two deliberate divergences from copy rule 6.** Rule 6 keeps playlist
codes and paths bare as tokens, and shipped copy follows it, down to a code
that hasn't passed validation (`Couldn't look up {input_playlist_code} on
KovaaK's.`). The log quotes every path, and renders a playlist code with `%r`
until validation accepts it, because the log's reader needs an unambiguous
boundary more than a sentence needs to read naturally, and a code that has
not passed validation may not be a code at all. The two sides agree on names
and user names, which both quote, and on a validated playlist code, which
both leave bare.

**`OSError` text keeps Python's rendering.** Python puts the filename into
an `OSError`'s text as a repr: backslashes doubled, in single quotes, or in
double quotes when the path holds an apostrophe. A conforming line that also
carries a traceback therefore shows one path two ways, once as
`"C:\...\loginusers.vdf"` in the message and once as
`'C:\\...\\loginusers.vdf'` in the traceback's last line. The second is
neither corruption nor a distrusted value; it is Python's text, a fix would
be per line, and it stays.

**What is deliberately not enforced.** Review only, the posture of the
comment conventions. A guard in the style of the em dash test would have to
know a placeholder's value kind, which the AST does not carry: the census
needed 87 hand-read expressions, and a name heuristic misfiles the pair that
matters most (`playlist_code` is a token, `input_playlist_code` is typed and
takes `%r`). The one check with no false positives, no `'%s'` in a logger
format, guards three lines' worth of deviation. After the sweep the tree is
the second teacher. Ruff's `G` rules stay on and logging calls keep lazy `%`
arguments; a quoting helper in the argument list was rejected because it
formats eagerly and hides the delimiter from the format string.

**Out of scope.** `scripts/` (developer tools that print to a terminal and
never reach a bug report); lines from bundled libraries; numeric formats; the
log format, levels, handlers, and rotation; structured or JSON logging. A
line that logs a user-facing message verbatim is copy and keeps its text,
including the bad-stamp message that shows a non-ASCII stamp with `\u`
escapes, and the unknown-username rejection, which carries the name as
typed. Also rejected as delimiters: single quotes (62 bundled names hold an
apostrophe), brackets (7 names hold one) and curly quotes (not typeable in a
log search), parentheses (10.1% of playlist names hold one, and the
dominant playlist pattern is already name then code in parentheses), and
placement alone (44 calls carry a free-text or path value followed by
another value, and a line has one last position).

Provenance: proposal
[#301](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/301)
(opened 2026-09-19; all four rows ratified 2026-09-26 in the
[ratification record](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/301#issuecomment-5851883535)),
shipped in
[#315](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/315).
Distilled from `docs/proposals/log_line_delimiting_proposal.md`, deleted in
the shipping PR.

## 2026-09-26: A Converted Run Keeps The Setting It Was Recorded At, For Display Only

Status: Accepted

A run recorded on a game's own scale, such as 0.2 Valorant, used to lose that
setting when it was converted to cm/360. The chart's point hover now shows
the setting and its DPI after the cm/360 value, in both chart modes. A wrong
DPI in a file now shows up there instead of hiding behind an odd cm/360
value. Everything else still works from the converted value, so a wrong DPI
is shown but not corrected.

**What is kept.** The recorded setting is the one a player remembers
playing, and its DPI explains a cm/360 group that would otherwise look
wrong. `RunData` gains `recorded_sensitivity`, a frozen
`RecordedSensitivity(value, scale, dpi)` defaulting to `None`.
`extract_data_from_file` sets it only on the converted branch, from the
unrounded `Horiz Sens`, the recorded `Sens Scale`, and the parsed `DPI`.
Every other branch leaves it `None`: a native cm/360 run, a legacy file
without the two fields, a field the conversion cannot use, and a conversion
that rounds away. One nested value rather than three loose fields makes "all
three or none" hold by construction. The value never passes through
`sens_round_decimal_places`: at the shipped one decimal place,
`0.16 Valorant` would display as `0.2`, a false original that 56 corpus runs
would show.

**Display only.** The sensitivity-key builders, the `SortedDict` ordering,
the plot axis, run notifications, and the PB cm/360 column still read
`RunData.horizontal_sens` and `RunData.sens_scale`, so no group, placement,
notification, or column value moves. The one reader is `plot_service`, which
builds the suffix ` ({value} {scale} at {DPI} DPI)` with `format_decimal`,
which never rounds and drops a whole number's `.0`, so the DPI reads `1600`.
The suffix is the run points' last `customdata` column, `""` for a run that
was not converted, so a native run shows nothing where it would go. Both
modes share one run-point line,
`<b>Sensitivity</b>: %{customdata[2]}%{customdata[3]}`; in Score vs
Sensitivity it stands in for the x-value line, which would repeat it. The
Average score line keeps its hovertemplate and reads no `customdata`: a
converted run and a native run at the same cm/360 share one group, so a group
has no single recorded setting to name. An unconverted legacy run already
shows its recorded scale and gets no suffix.

**No migration.** The run store is in-memory and rebuilt from the stats
folder at every start, so every converted run carries the field from the
first launch after this change. Nothing persists `RunData`.

**Recorded DPI is still trusted as-is.** Showing the DPI is not correcting
it. The runs misrecorded at 400 DPI still convert to about four times their
real cm/360 and still group, sort, notify, and fill the PB cm/360 column
there. Only their hover changes, to read
`163.4 cm/360 (0.2 Valorant at 400 DPI)`. The rejection of any in-app DPI
override stands, and the escape hatch is still a one-time edit of the
affected files.

Supersedes, in part, the
[2026-09-11 sensitivity-normalization entry](#2026-09-11-sensitivities-normalize-to-cm360-at-parse-time-from-the-files-own-increment-and-dpi):
its "`RunData`'s shape is unchanged, so the original scale value is not
retained" clause only. The conversion, its inputs and guards, the trust in
recorded DPI, the legacy-label rule, the notification semantics, and the
rounding rule all stand.

**Copy.** The fragment follows the value it explains, in parentheses, because
they read as "what this came from"; a ` · ` separator would read as two
independent facts. `at … DPI` keeps the unit, which is what makes the 400-DPI
misrecord legible. The scale is a proper name and keeps the casing the file
recorded.

**Provenance.** No proposal: the maintainer approved skipping one on
2026-09-26 and approved the scope, the run-point hover in both modes, on the
author's recommendation in the kickoff. Shipped in PR #312.

## 2026-09-26: A Read-Only Check Finds Bundled Benchmarks That KovaaK's Changed

Status: Accepted

The importer regenerates a bundled benchmark only when Evxl's listing of it
changes, so when KovaaK's moved a benchmark's rank thresholds or swapped a
scenario underneath, the file went stale silently and showed players wrong
rank badges. The importer now has a read-only check that rebuilds every
bundled benchmark from live data and names the files that differ. Each
refresh runs the check and regenerates the files it names. Nothing runs on its
own.

**The rule.** Drift is found by `scripts/benchmark_importer/script.py
--check`, run by hand in each refresh before anything is regenerated (the
importer readme's refresh runbook). It is decided by whole-model equality
between `PlaylistData.model_validate` of the shipped file and
`build_playlist(sharecode, item, use_cache=False)`, the importer's own
fetch-and-merge, over the committed Evxl snapshot. Regeneration still keys on
Evxl metadata: a normal run's manifest skip is unchanged, and the check only
names the sharecodes, printing a ready-to-paste
`--offline --force --only ...` line for them.

- **Whole model, not a field diff.** A field-by-field diff passes any field
  added to the models later, and scenarios matched by name collapse when a
  name repeats. `describe_drift` explains a drifted file for the summary and
  never decides; a difference it can't describe still counts. The
  `generated_from` stamp is not a model field, so it never reads as drift:
  over all 257 files, validating the shipped payload with and without it
  gives equal models.
- **Live KovaaK's, committed Evxl.** The KovaaK's fetch passes
  `use_cache=False`, because the benchmark cache can hold the very payload
  the file was built from. The Evxl snapshot is never refreshed, which keeps
  the check read-only (its only write is the benchmark cache) and leaves
  Evxl-side changes to the runbook's first step. The playlist name and code
  still come from Evxl's live playlist-by-code endpoint, as in every run.
- **Keyed by provenance.** A file is matched to the snapshot by
  `generated_from.sharecode`, never by `code` or filename: one bundled file's
  `code` differs from its sharecode in casing.
- **Nothing reads as clean by accident.** Every file lands in identical,
  drifted, failed, or not checked, and the exit code is 0 only when all of
  them matched. A deterministic or transient rebuild failure, a sharecode
  missing from the snapshot, and a conflicting duplicate all fail; a tripped
  circuit breaker lists the unvisited files as not checked. Failed and
  not-checked files never appear on the paste line, because regeneration
  can't fix them.

**Evidence.** The limit was recorded from the start: the
[2026-07-03 entry](#2026-07-03-import-benchmarks-from-evxl-and-kovaaks)'s last
consequence says threshold changes under an unchanged benchmark ID need an
explicit forced refresh. Iron Pipe #1 (benchmark 2757) drifted that way and
was caught in PR #289 only because Evxl's `scenarioCount` happened to change.
A one-off script then rebuilt all 253 files live on 2026-09-15 in 3.8 minutes
wall clock: 248 identical, 5 drifted, 0 failed, with no name, code, order,
leaderboard-ID, or rank-ladder drift anywhere. PR #293 regenerated the five
with `--offline --force --only`:

| File | Benchmark ID | Drift |
|---|---|---|
| Pasu Track DOJO | 880 | 8 scenarios rebalanced, lower tiers dropped a lot (`Pasu Track Extrasmooth TE` 7000 → 5525) |
| Ground Track DOJO | 977 | 6 scenarios rebalanced, all tiers lowered (`DeceptiveStrafes` 2600 → 1550) |
| Jade Palace Ground Benchmark - Hard | 959 | 7 scenarios, small threshold moves |
| IRON PIPE AIM PLAYLIST #2 | 2789 | `TSK - SYW` swapped for `SYW (Smooth Your Wrist) Truly FIXED` (leaderboard ID 13150); `VAI 314 TE` −100 per tier |
| AimSpeed Benchmarks 2 Easy | 2168 | `Skeet Tracking Goated Easy` +200 per tier |

The shipping PR's first full `--check` on 2026-09-26 took 3.9 minutes wall
clock over 257 files: 252 identical, 5 drifted, 0 failed, 0 not checked. All
five matched KovaaK's on 2026-09-15: the three older files were identical in
the one-off rebuild, and PR #294 generated the two AIMCORE files live that
day.

| File | Benchmark ID | Drift |
|---|---|---|
| AIMCORE Benchmarks S1 - Harder | 2892 | thresholds in 3 of 18 scenarios |
| AIMCORE Benchmarks S1 - Medium | 2891 | thresholds in 1 of 18 scenarios (`AC WideShot` 47 → 50 first tier) |
| Peter Ground Technology | 2884 | `MLSI demotori hard` swapped for `MLSI demotori hard v2` |
| Underaim-Benchmark | 2942 | thresholds in 13 of 14 scenarios |
| XYZ SMOOTHNESS BENCHMARKS V2 | 2450 | thresholds in all 15 scenarios |

Regenerating them is a separate refresh PR, not part of shipping the check.

**Rejected.**

- Detecting drift inside normal runs, for example with a digest of the
  KovaaK's payload in the provenance stamp: it needs a live fetch for every
  benchmark on every run, discarding the cache that keeps reruns cheap.
- A blanket `--force` sweep: it rewrites `generated_at` in every file and
  buries a handful of real changes in a 257-file diff.
- A scheduled CI job: more infrastructure than a four-minute manual step
  needs.

**Consequences.** A refresh PR runs the check before regenerating anything,
and regenerates only the drifted sharecodes among the files already bundled. The refresh procedure, which lived only in the bodies of
PRs #289, #293, #294, and #297, is now the importer readme's runbook, written
in tracked commands. The check stays manual, so drift that lands between
refreshes ships until the next one.

Provenance: the maintainer revived the shelved idea on 2026-09-26;
claude-fable-5-1 and claude-opus-5-5 converged on this design and the
maintainer accepted it as the kickoff basis the same day. Shipped in PR #311.

## 2026-09-22: The README Stops Explaining How The Installer Works

Status: Accepted

A second pass on the README cut the installer details a player does not need
before installing, such as how releases are verified and how an update
protects itself. Install now covers only what the player does and sees.
A reader who wants to check a release before running it follows the manual
install link, which now carries the digest check in full.
The README also shows the playlist pages, and its screenshots live in their
own folder.

**What this reverses.** The
[front-door entry](#2026-09-22-the-readme-is-a-front-door-and-user-reference-lives-in-a-user-guide)
kept Install's paragraph on what the installer touches, the
release-integrity paragraph, Updates, and Uninstall unchanged, "because those
are what make pasting a one-line installer acceptable". The maintainer
overrode that the same day: the average reader does not care how releases are
made. A separate release document was considered and not made, because each
fact already has a home:

- The installer-touches paragraph (one root under `%LOCALAPPDATA%`, its own uv
  and Python, no registry, `PATH`, or machine-wide toolchain) lives in
  `docs/specs/release_and_install.md` and the
  [installer entry](#2026-07-19-the-installer-brings-its-own-toolchain-app-locally).
  Its "nothing else is touched" also overstated: the desktop shortcut and
  `get.ps1`'s `%TEMP%` copy sit outside the root.
- The release-integrity paragraph: the digest check, `Get-FileHash` included,
  moved into the user guide's Manual install step, which already listed the
  digest; immutability and the archive contract live in the release spec and
  the [immutability](#2026-07-19-releases-and-their-assets-are-immutable) and
  [archive-contract](#2026-08-21-release-integrity-rests-on-github-digests-and-an-enforced-archive-contract)
  entries.
- Updates' promotion-after-a-healthy-start and untouched-`config.toml`-and-`data`
  sentences live in the release spec and the user guide's Configuration
  section.
- Uninstall lost its registry and `PATH` list and the `%TEMP%` script's
  "inert" clause. The `%TEMP%` `<details>` block stays, because the installer
  entry says the README documents deleting that file, and Uninstall's
  closing sentence names that script as the one change outside the folder
  and the shortcut; an unqualified "nothing else on the machine was
  modified" would be false while the script remains.
- Also cut: Run From Source's first-start and `git pull` paragraph, the
  `product.md` rationale pointer, and the bug section's account of why
  `debug.log` matters. The bug section asks for no logs at all and leaves that
  to the bug form, which names the file for each failure and warns that
  attachments are public; a blanket request for "log files" invites
  over-sharing, and the issue chooser also leads to the feature-request form,
  which asks for none. Run From Source stays, per the front-door entry's
  2026-09-21 ruling.

**Development links `docs/`, not `architecture.md`.** The front-door entry put
the tech-stack sentence beside the architecture link, "which keeps the
`docs/architecture.md` archive row true on the README's own account". The
sentence now points at the `docs/` folder, and with the `product.md` pointer
also gone, neither file is a target of the README or the user guide. Those two
shipped entry points are what the contract's documentation rows cover, per the
[archive-contract entry](#2026-08-21-release-integrity-rests-on-github-digests-and-an-enforced-archive-contract)
and the two tests that hold their targets in `REQUIRED_ARCHIVE_ENTRIES`, so
both rows left it. `docs/roadmap.md`, itself a row, still links both, as it
links `decision_log.md`, a spec, and a proposal that never had rows: targets
one hop further in are covered by `.gitattributes` keeping `docs/` whole, not
by rows. Relinking either file from the README or the guide fails that
entry point's test until the row returns. The AI-assisted-development sentence
(#278 D1) stays, shorter.

**Screenshots live in `docs/screenshots/`**, named for the view they show:
`scenario_performance.png` (formerly `docs/example.png`), `playlists.png`,
and `playlist_scenarios.png`. `.github/` was rejected because `.gitattributes`
prunes it from the release zip, which would break the shipped README's
images; `assets/` because Dash serves it at runtime. Each embedded image is
its own `REQUIRED_ARCHIVE_ENTRIES` row: a `docs/screenshots/` directory row
would still pass after the embedded file was renamed away. The two playlist
shots are cropped to the page title, its controls, the column headers, and
six rows, and stack at full width below Features. Side by side at half width
was rejected: at GitHub's README width their table text renders about 3 px
tall.

**Tagline and Run notifications.** The tagline names history as well as live
runs, because "plotted as you play" read as the app's only use when it also
serves reviewing past runs. The Run notifications bullet now reads "a toast to
compare your new run against your personal best": it no longer names the
top-N verdict or says that a run earning neither gets no toast, the qualifier
the front-door entry's size paragraph defended. The maintainer chose this
wording on 2026-09-22, intending every run to notify, which has not fully
shipped. Under default settings it holds for the latest live run of each poll
on the Scenario Performance page: that run gets a threshold pass or fail
against the previous best, a top-N placement when it is the first at its
sensitivity, or the personal-best celebration. Earlier runs coalesced into the
same poll stay plot-only, a personal best among them included, and the latest
run also goes silent when the threshold verdict is switched off or its
percentage is blank and the run falls outside the top N; the notifications
spec states those edges.

**Size.** 772 words in 148 lines by the front-door entry's measure, down from
1,196 at #308's merge.

Provenance: the maintainer's own README edits, reviewed and completed in PR
#309; no proposal.

## 2026-09-22: The README Is A Front Door, And User Reference Lives In A User Guide

Status: Accepted (amended by
[2026-09-22](#2026-09-22-the-readme-stops-explaining-how-the-installer-works):
Install no longer carries the installer-touches or release-integrity
paragraphs, and Development links `docs/` rather than `architecture.md`; and
by the
[2026-09-30 sentence-count entry](#2026-09-30-the-docs-test-counts-summary-sentences-and-its-count-is-the-definition):
the docs test now counts summary sentences, so "that test gates structure,
never prose" holds for everything but that count, and the README word-count
gate stays rejected)

The README had grown to 3,289 words, most of it reference material that a
player arriving from a link never reads. It is now a front door: what the app
does, one line per feature, how to install it, and where to get help.
The reference sections moved word for word into a user guide that the
README links.
The README keeps a short summary of the app's network use, because a reader
deciding whether to run the installer needs it before they install.

**The rule.** The README is for the reader who arrived from a link and has not
installed yet, or installed a minute ago. It says what the app does and why,
shows it, lists features one line each, installs it, and points at help.
Reference, how-to, and troubleshooting for a reader who already runs the app
live in `docs/user_guide.md`. A new feature adds at most one line to Features;
its settings, edge cases, and failure modes go to the guide or the capability
spec. `AGENTS.md` carries the rule under Documentation Habits, and review
holds it. A word-count gate in `tests/test_docs.py` was rejected: it would
fail unrelated PRs on an editorial threshold, and that test gates structure,
never prose. Collapsing sections into `<details>` in place was rejected too:
the words stay in every diff, and a collapsed block is invisible to a reader
searching the page.

**One guide.** Everything that left went to one file written for users.
Each section kept its heading text, so the anchors other documents link
(`#configuration`, `#playlists-and-benchmarks`, `#troubleshooting`,
`#what-it-talks-to`, `#manual-install`) survive under the new file name.
Sections run by how often a running user needs them: Configuration, Playlists
and Benchmarks, Troubleshooting, What it talks to, Manual install.
`docs/architecture.md` was rejected as the home because it is the contributor
and agent map of the codebase, and a player will not open a file called
architecture. A `docs/guide/` folder of five files would have cost five
archive rows and made the `#configuration` reference inside Troubleshooting a
cross-file link. The GitHub wiki is not versioned with the code, sits outside
the same-PR documentation rule and the link gate, and does not ship. The guide
does ship: `REQUIRED_ARCHIVE_ENTRIES` names it, and `tests/test_release_job.py`
requires every target it links, resolved from `docs/`, as it already did for
the README's `docs/` links.

**The network disclosure has two surfaces.** The guide's What it talks to
section is the public disclosure: the table of services, never hostnames, and
its caveats. The README keeps four sentences under the same heading: no usage
or crash analytics, data stays on the PC, three things reach the network
(installing and updating, leaderboard lookups once a username is set, and the
actions the user clicks), and a link to the guide. The summary names
categories rather than services, so a new service under an existing category
cannot make it false; a service-naming short form in the maintainer's launch
notes went stale the day chart sharing landed. It stays in the README because
the reader being asked to paste `irm | iex` needs it before installing, not
after going looking. The cost is a second surface, so a PR that adds an
outbound service or a new trigger updates the guide's section and checks that
the README's summary is still true, in the same PR.

**The move is verbatim.** Configuration, Playlists and Benchmarks,
Troubleshooting, What it talks to, and Manual install with its Rollback block
were copied, not rewritten. Wording, order, the collapsed `<details>` blocks,
the network table's services-not-hostnames shape, and the schema-recovery
entry's order (back up `data` first, the converter script, the hand edit
last) all carried over. The only edits: the three references to the install
one-liner, in Manual install, Rollback, and the network table's first row,
link to the README's Install section, and Manual install's heading is H2
because the guide has no Install section for it to sit under. Rewording while
moving was rejected because it would reopen text #278 verified against the
scripts and make the move unreviewable as a move. Install keeps its
three-step quick start, the paragraph on what the installer touches, the
release-integrity paragraph, Updates, and Uninstall, unchanged, because those
are what make pasting a one-line installer acceptable. Troubleshooting moved
whole, all eight entries in order, rather than splitting a few inline entries
from the rest; the README's pointer names both log locations, because it still
advertises Run From Source, whose logs live in the checkout. Features was
rewritten in place from ratified prose; its lost per-feature detail is what
the capability specs already state.

**Run From Source stays in the README, reworded (ruled 2026-09-21).** The
section is short, sits below where players stop reading, and is where a
contributor and a user managing their own toolchain both look for the
commands. Its opening fragment became a sentence, its configuration aside
went, and its tech-stack sentence moved to Development beside the
architecture link, which keeps the `docs/architecture.md` archive row true on
the README's own account. Moving it into the guide as a third install path
was rejected: it would have saved about 60 README words at the cost of a
copied sentence, a reversal of #278's unanimous outcome, and one more click
for a contributor. A standalone `docs/development.md` was rejected as a second
file and a second archive row for 85 words.

**The size is 1,241 words in 179 lines.** Words are whitespace tokens,
`awk '{w += NF} END {print w}' README.md`; a locale-less `wc -w` in Git Bash
skips standalone em dashes and reads low. The proposal set 1,000 to 1,200 as
an editorial budget, and the result sits about 40 over it once Run From Source
stayed. The qualifiers that carry it past the band are true and stayed: the
Run notifications bullet keeps that a run earning neither verdict says
nothing, because one toast per run is false under ordinary settings, and the
Benchmarks bullet keeps both steps of enabling a hidden benchmark. Going
further, to the 450 to 700 words of the shortest exemplars, would have meant
moving the installer-trust paragraph, Updates, and Uninstall as well.

**Shipping-checklist scope.** Steps 4 and 5 of "Shipping a proposal" in
`AGENTS.md`, the roadmap milestone and the product inventory, apply when a
proposal ships an app feature; a docs-only proposal records itself in the
decision log alone. Earlier docs-only changes relied on that reading without
writing it down; this change writes it down, and it is why this change adds no
roadmap or product entry.

Provenance: distilled from `docs/proposals/readme_trim_proposal.md` (proposed
in PR #303; D6 ruled 2026-09-21, D1 to D5 ratified 2026-09-22), shipped in PR
#307; the proposal file is deleted in the shipping PR and git history holds
its full text.

## 2026-09-20: A Rank Above The Known Total Suppresses The Percentile

Status: Accepted

A scenario's position and its leaderboard's player count are fetched and cached
separately, so a current position can be paired with an older, smaller count
and the percentile derived from the pair goes negative. The app now withholds
the percentile whenever the position sits past the count it knows, showing the
two numbers on their own until the count refreshes, which clicking Refresh on
that scenario forces. A user sees that scenario's Position lose its percentile,
and the playlists holding it fall back to the cached-coverage placeholder in
Median Percentile and Lowest Percentile.

Decision: `_with_percentile` derives nothing when `rank > total_players`. It
returns the result unchanged — `rank` and `total_players` both survive,
`percentile` stays `None` — and logs the scenario, leaderboard id, rank and
total at WARNING so the staleness is diagnosable from `data/logs/debug.log`.
That warning is emitted once per leaderboard per rank/total pair, because the
cache-only read path re-derives the percentile on every polling tick and the
playlists overview re-derives it per played scenario: one line in the log
means one condition, not one occurrence.
The guard is strictly `>`: `rank == total_players` is a real last place on the
board and keeps its
[midpoint value](#2026-04-27-use-the-midpoint-percentile-formula).

Why: rank comes from `/leaderboard/scores/global` with `usernameSearch`, whose
`total` counts search matches rather than the board, so the population is a
second unfiltered request cached under `leaderboard_total_cache_ttl_hours`
([one week by default](#2026-04-29-cache-leaderboard-totals-for-one-week)).
Boards are expected to grow, so a cached total is normally a lower bound on the
live one, and `((total - rank + 0.5) / total) * 100` crosses zero as soon as
the rank passes it: a board cached at 500 that grew to 1,200 renders a 900th
placement as `900 of 500 (-79.90% percentile)`. Every path whose rank and total
ages are independent can reach it — the percentile warmup worker, the playlist
scenarios fill, the overview's cache-only reads, a TTL-expired foreground
lookup, the stale-rank fallback, and a clicked Refresh whose total re-read
failed and fell back to the cached count
([2026-09-19](#2026-09-19-a-clicked-refresh-re-reads-the-leaderboard-total)).

Consequences: a suppressed percentile leaves that scenario unresolved for the
playlists overview, so the whole playlist shows the
`{resolved}/{played} cached` placeholder in both percentile columns instead of
a median it cannot support. That is the honest readout — the aggregate
genuinely is not known — but it is visible, and it lasts until the total
refreshes. The placeholder's tooltip suggests opening the playlist, which
doesn't clear it while the total is TTL-fresh, because the playlist's fill
honors that TTL. A clicked Refresh on that scenario does, since it re-reads the
total
([2026-09-19](#2026-09-19-a-clicked-refresh-re-reads-the-leaderboard-total));
otherwise the row waits out `leaderboard_total_cache_ttl_hours`, a week by
default. The suppression also breaks two properties
[2026-07-16](#2026-07-16-warm-playlist-percentiles-with-one-polite-background-worker)
stated for that placeholder, whose display rule it called weaker than the
warmup worker's freshness test and monotonic: a scenario the worker counts as
fresh can still hold a row on the placeholder, and a row that was showing
aggregates can return to it.

Rejected: clamping to `0.0`, or to the value at `rank == total`. Either
invents a number from data already known to be inconsistent, and the invented
floor still feeds the median as though it had been measured. Also rejected:
dropping the total along with the percentile, which discards a count the app
legitimately has and contradicts the principle that a degraded read
[shows no less than the app already knows](#2026-07-12-rank-fetch-failure-degrades-to-the-last-cached-rank).

Not done: refreshing the total when the guard trips. A rank above the total is
good evidence the total is stale. The self-heal would not live in
`_with_percentile`, which stays a pure derivation, but in the network-allowed
enrichment path: `_with_leaderboard_total` bypassing the TTL once when the
cached total sits below the rank, plus `_freshly_satisfied` learning the same
condition so the warmup worker stops skipping the scenario as satisfied. It
covers only a board that grew. If a board ever loses rows, the stale side is
the rank, and a total re-read heals nothing. Suppression is the right floor
either way, which is why the self-heal is a separable follow-up rather than
part of this guard.

## 2026-09-19: A Query Parameter Selects A Control, It Does Not Suspend Its Memory

Status: Accepted

Clicking a scenario in a playlist now counts as choosing it. Before, arriving
at Scenario Performance from a playlist link put the page into a mode where
nothing the user picked was remembered, so going back to the page snapped both
dropdowns to a selection that could be weeks old. The page now remembers a
selection however it was made, and the navbar link returns to the latest one.

**The bug.** `layout()` derived `persistence=playlist_code is None` and
`persistence=scenario is None` for the two dropdowns, so a
`/?playlist_code=…&scenario=…` arrival rendered both with `persistence=False`.
Dash's `recordUiEdit` returns early on a falsy `persistence`, so every
selection made during that visit went unrecorded; `persistenceMods` skips the
component for the same reason, so the value stored *before* the visit was not
cleared either. Returning to `/` re-enabled persistence against a layout
`value` of `None`, which matched the stored original, and the pre-visit value
was restored. Confirmed against the shipped `dash_renderer` and reproduced in
a browser: with no deep-linked visit the selection survives a Home click; with
one, both dropdowns revert, through the navbar link and the header title
alike.

**The invariant this establishes.** *A browser-persisted control's layout
default never varies per visit; a per-visit initial value arrives by
callback.* Dash pins a persisted edit to the layout value it was made against
and discards the edit when a later visit renders a different one, so a default
that varies per visit retires persistence for that control instead of
overriding it. This is the per-visit twin of the keyed-by-id rule in
[2026-08-09](#2026-08-09-chart-options-live-in-a-collapsible-panel-beside-the-graph),
and it binds any future `?param=` preselect on any page.

**Its corollary, learned the hard way in review.** *A callback that writes a
control only on some visits starves that control's single-Input dependents on
the others.* The renderer drops a ready callback when none of its Inputs was
written and every one of them is a declared output of a group member that
already ran. `select_playlist`'s only Input was the playlist value, which
`apply_deep_link` now declares and returns `no_update` for on every visit
without `?playlist_code=` — so it stopped making its initial call, and the
scenario dropdown kept the layout's full local list while the filter named a
playlist. The fix is a second Input that nothing writes, which makes the
prune's "every Input covered" test fail; `select_playlist` carries the
`home-deep-link` store for that reason and no other. A structural test in
`tests/test_home_rank_format.py` fails if any callback's Input set is ever
again a subset of what `apply_deep_link` conditionally writes.

**The mechanism.** Both dropdowns carry `persistence=True` and an explicit
`value=None` on every visit. `layout()` resolves the query parameters into a
layout-bound `dcc.Store` (`home-deep-link`), and one callback,
`apply_deep_link`, writes them to the two dropdowns. Callback-written values
*are* persisted — the response path reaches `recordUiEdit` — so the deep link
becomes an ordinary remembered selection. Details that are load-bearing:

- **`value=None` is explicit, not omitted.** An omitted prop is `undefined`
  rather than `null`, which would not match the original already stored in
  every existing browser and would discard those values on upgrade.
- **A layout-bound store, not the URL.** Dash Pages rebuilds the page on a
  route change and the store then triggers exactly one write, keeping the deep
  link out of the router's callback graph — the same reason
  [2026-04-29](#2026-04-29-drive-playlist-table-loads-from-mounted-route-state)
  drives the playlist scenario table from mounted route state.
- **`allow_duplicate` plus `prevent_initial_call="initial_duplicate"`.**
  `check_for_new_data` already writes the scenario value, and applying the
  deep link is the mount's whole job. Folding it into `check_for_new_data` was
  rejected: that callback's `prevent_initial_call=True` stops a remount
  replaying the retained run-event batch.
- **Presence, not just value.** The store records a key only for a parameter
  the URL carried, and the callback returns `no_update` for the rest, so
  `?scenario=` alone leaves the playlist filter on the restored value. An
  unknown playlist code is recorded with no value and clears the filter, which
  is what applying the URL's selection as given means.

**The URL is not rewritten after the deep link is consumed**, so a reload
re-applies it over a later choice. `_pages_location.search` is a router
`Input`; rewriting it would remount the page. The behavior matches a URL with
parameters read as a bookmark, and the navbar link is the way back.

**Accepted cost.** Persistence restores the previous selection before the
callback's value lands, so a deep-linked visit shows the old playlist name for
one round trip. What the renderer holds during that round trip is asymmetric,
and only the playlist half is held: `getReadyCallbacks` waits on a pending
output only when an Input's `id.prop` equals the output's key, and an
`allow_duplicate` output's key carries an `@<hash>` suffix that this
comparison does not strip (though `cleanOutputProp` strips it when results are
applied). So the playlist value's dependents wait, and the scenario value's do
not: on a deep-linked visit `generate_graph` and `get_scenario_num_runs` each
run twice, once for the restored scenario and again for the deep-linked one.
A stale run's outputs are not discarded — they land. The stale
`generate_graph` response finishes before the second request is issued and
is applied, so the `cached-plot` store holds the stale plot for tens of
milliseconds. The user still does not see it, because the hold this paragraph
describes works one hop downstream: `cached-plot.data` is a plain output, so
`apply_graph_appearance` waits behind the pending second `generate_graph` and
draws once, from the deep-linked plot. That rests on `apply_deep_link`'s
response landing alongside the stale plot's, which it did in every measured
load and which nothing guarantees; "never drew the stale plot when measured"
is the honest claim, not "cannot". The cost is server-side: one plot build
that is never drawn and one stats read per deep-linked visit.
`get_scenario_rank` also runs twice, and its stale run is an ordinary mount
run: it arrives with real triggers (three `changedPropIds`), so it is
network-allowed and toast-allowed, and its lookup is TTL-governed — a cache
read while that scenario's rank cache is fresh, which is the usual case
because the scenario was the selection a moment ago and the TTL is a week,
and a KovaaK's lookup when the cache is cold or expired. The falsy list Dash
substitutes for an *untriggered* call — one item whose `prop_id` is `"."`,
so `ctx.triggered` is never `[]` inside a callback — is what keeps such a
call quiet without refusing it the network, since `_rank_allows_network`
refuses only when the interval is the sole trigger. It does not apply to this
run, which is triggered. A clientside callback would shrink the transient to a
frame at the cost of moving the resolution out of Python; it stays available
if the transient ever proves visible.

**Rejected.** Keeping `persistence=False` for the visit and clearing the
stored keys from the browser: it depends on dash-renderer's private key format
and still discards the visit's selections. Keeping the query value as the
layout `value` with persistence on: the pinned original then becomes the query
value, so the next Home visit discards the entry and both dropdowns come up
empty — the same loss, reached differently. Making `apply_deep_link` the plain
writer of the scenario value and moving `allow_duplicate` onto
`check_for_new_data`, which would make the hold symmetric and the double run
go away: it puts the mount-fire hazard on the one callback whose contract is
that a mount must not replay the retained run-event batch, which is worth more
than one never-drawn plot build per deep-linked visit. No prior entry governed
the original behavior, so nothing is superseded.

## 2026-09-19: A Clicked Refresh Re-Reads The Leaderboard Total

Status: Accepted (amended by
[2026-09-20](#2026-09-20-a-rank-above-the-known-total-suppresses-the-percentile):
the `rank > total` guard it deferred has landed)

The Refresh button beside the Position field used to fetch a live position and
divide it by a player count that could be a week old, so the percentile it
showed was two numbers from different moments. Clicking Refresh now re-reads
the count as well and recomputes the percentile from both. When the position
refreshes but the count cannot be reached, the app keeps the last count it has
and says so in an orange notification instead of confirming a clean refresh.
Automatic lookups that still go to the network reuse a cached count for a
week, and when their own fetch fails they now fall back to the last count they
have instead of showing none.

**What `force_refresh` means now.** It marks the whole readout
board-authoritative, not just the rank: `get_scenario_rank_info` passes it
through to `_with_leaderboard_total`, which bypasses
`leaderboard_total_cache_ttl_hours` for that call. The flag already bypassed
the rank cache and already permitted a regressing write
([2026-07-01](#2026-07-01-keep-scenario-rank-consistent-with-score-aware-refreshes));
the denominator was the part it did not cover. The PB-triggered freshness chain
had been forcing the total since 59b2d1d by passing a zero TTL, never recorded
as a decision — an unlogged precedent that this entry adopts and states, and
that call now names the flag instead of the zero.

**Why the one-week TTL still stands elsewhere.**
[2026-04-29](#2026-04-29-cache-leaderboard-totals-for-one-week) priced the
trade against bursty cold-cache total fetches across every playlist scenario,
and named "a targeted refresh flow" as the remedy if stale totals ever
misled. The Refresh button is that flow: one leaderboard, one extra
unfiltered GET, at a moment the user asked for truth. Every other automatic
path that fetches — the warmup worker, the network phase of the playlist
scenarios fill, a foreground lookup whose rank cache expired — keeps the TTL,
so the knob still governs what it was bought for. A cache-only reader never
had a TTL to keep: the playlists overview, the Home interval tick and the
fill's first paint all pass `allow_network=False`, which serves the rank and
total caches regardless of age so those surfaces can render without touching
the network. A percentile needs an unfiltered count the rank call cannot
supply: with `usernameSearch` the response's `total` is the number of search
matches, not the board population.

**The failed-total fallback is not gated on the flag.** A total fetch that
fails now substitutes the last cached count whatever its age and marks the
result `total_refresh_failed`, for every caller rather than only a clicked
one. One rule, because the cache-only interval path and `_stale_rank_fallback`
already read the total TTL-free, so gating it would have left three callers
disagreeing about the same cache. The consequence for automatic renders: one
whose own total fetch fails now shows the last cached count at any age where
it used to show none. On Home that is the count the next interval tick would
have supplied a second later anyway; in the playlist scenarios fill it is the
one the first paint had already shown. It also supersedes the Consequences line of
[2026-04-27](#2026-04-27-make-leaderboard-total-enrichment-best-effort), which
described returning the original `ScenarioRankInfo` untouched.

**Orange when the position lands and the count does not.** A clicked refresh
whose total fetch failed answers orange — the partial-success rung
([2026-08-30](#2026-08-30-one-severity-color-language-for-inline-notices)),
**extended here** from "a follow-up write did not" to any follow-up step, since
what failed is a read. `docs/specs/notifications.md` carries the widened
sentence.
Green would assert a freshness the readout does not have, and the served-stale
yellow would claim the position came from cache when the position is the one
part that did refresh. It shares the per-scenario success channel, so the
green a re-click earns replaces it rather than stacking under a contradicting
verdict. Rejected: dropping the count entirely, which shows less than the app
knows and contradicts
[2026-07-12](#2026-07-12-rank-fetch-failure-degrades-to-the-last-cached-rank);
a silent green over the cached count, which is the smallest diff but leaves
the button's promise unverifiable; a new inline hint, since the affordance is
already beside the value and the same host is failing seconds apart. No total
request is made at all when the rank fetch itself failed.

**Not fixed here.** `_with_percentile` guarded `total_players <= 0` but not
`rank > total`, so an automatic path, or a click whose total re-read failed
and fell back to the cached count, could still print a negative percentile
from a fresh rank over an older smaller count. The guard shipped separately in
[2026-09-20](#2026-09-20-a-rank-above-the-known-total-suppresses-the-percentile),
and that pairing now withholds the percentile instead. The click's orange
verdict is unchanged by it: the verdict keys on the failed re-read, not on the
percentile.

## 2026-09-15: Setup Hints Wear The Notice Anatomy

Status: Accepted

Three messages telling the user the app needs something from them were still
plain text: the stats-folder line at the top of Scenario Performance, its
restart-pending twin, and the restart notice on the Settings page. They now
look like every other inline notice, a yellow panel with a warning icon
beside the sentence. Nothing they say changed, and no new message was added.

**The three surfaces.** The Home hint (`_stats_dir_hint()` in
`source/pages/home.py`) and the Settings restart notice (`_restart_notice()`
in `source/pages/settings.py`) are `dmc.Paper` elements wearing
`alert-panel alert-panel-caution` plus their own layout class, holding one
`dmc.Group` of `local_icon("material-symbols:warning-outline")` and a
`dmc.Text`. No title row: each sentence already names the action, and a
title over it would be new copy. The Home hint keeps its id, both branches,
and the selection logic that picks between them; the Settings notice keeps
its id, its `(children, class)` shape, its hidden-class reveal, and the two
`save_user_settings` outputs that drive it. The Home panels share the setup
card's width so the two match when they stack; the Settings panel is capped
at the form fields' width and ends where they do.

**The rulings** (proposal #281, all four ratified by the maintainer on
2026-09-15 after two full reviews):

- **D1**: the Position field's inline hints stay value qualifiers and are
  not promoted. Rejected: promoting them, which detaches the explanation
  from the value it qualifies and turns the post-Skip state into a permanent
  notice nagging about a choice the user made.
- **D2**: the restart-pending branch is yellow, like the unconfigured one. A
  pending restart needs the user and blocks every plot on the page. Rejected:
  blue, which reads the state as an FYI and costs a second class and icon
  pair on one id.
- **D3**: no title. Rejected: a title, which would be the only new copy in
  the change.
- **D4**: the Settings notice joins the same anatomy. Rejected: keeping the
  orange text as an accepted exception; blue on Settings with yellow on Home,
  which changes severity mid-flow on the first-run path; and yellow text,
  which the numbers below rule out.

**Why not yellow text.** Measured against the dmc 2.8.0 palette (WCAG 2.x,
page backgrounds `#ffffff` and `#242424`, tint alpha 0.1 light and 0.15
dark), no Mantine yellow reaches 4.5:1 as text on the light background:
yellow-9, the darkest, is 3.00:1 (5.18:1 dark). The shipped orange measured
2.57:1 light and 4.34:1 dark, and the dimmed Home hint 3.32:1 light. In the
panel the sentence stays at body text color, 19.66:1 light and 6.85:1 dark,
and the yellow is a cue on the icon and border (1.74:1 on the light tint,
8.70:1 dark) rather than the thing being read.

**`wrap="nowrap"` is load-bearing on both groups.** `dmc.Group` defaults to
`wrap="wrap"` and flexbox then sizes the `dmc.Text` at its one-line width, so
a sentence wider than the space beside the icon drops whole onto the row
under the icon instead of wrapping beside it; `align` does not prevent that.
Both sentences do exceed that space at a narrow window, and the Settings one
also did at the 32rem width the Home panels use. With `align="flex-start"`
the icon then pins to the top of a taller line box, so a CSS rule drops it by
half the leading onto the first line's middle.

**The co-render is reachable.** `bootstrap_stats_dir()` merges only
`stats_dir` into the store, so a detected folder that later vanishes leaves a
present-but-unusable `stats_dir` beside an absent `kovaaks_username` key:
the hint's case and the account offer's case at once. The page shows the
yellow hint above the blue card, each speaking for its own key, at the same
width. The restart branch has no such case, because the card stands aside
while a stats-folder change is pending.

Amends the
[2026-08-30 color-language entry](#2026-08-30-one-severity-color-language-for-inline-notices),
whose enumeration of five inline surfaces becomes seven, and the
[2026-08-02 pinning entry](#2026-08-02-restart-scoped-settings-are-pinned-at-boot-and-the-stats-folder-finds-itself),
which created the Settings notice without ruling its look. Out of scope, so
that the next sweep does not re-find them: the Settings save-status line,
which stays a red status line beside the button it answers, and the pale
yellow tint, deferred by the 2026-08-30 entry.

Provenance: `docs/proposals/setup_hints_become_notices_proposal.md`, proposed
in PR #281 and deleted in the shipping PR; git history holds its full text.

## 2026-09-15: The Bundled Corpus Is Evxl's Listed, Non-Hidden Benchmarks

Status: Accepted

The app ships a benchmark only while Evxl lists it and does not mark it
hidden. When Evxl delists a benchmark, its file leaves the app at the next
refresh, even if KovaaK's still serves it. A benchmark Evxl marks hidden
stays out until Evxl unhides it. Refreshes apply both rules without asking
the maintainer again.

**The rule.** `resources/benchmarks/` holds the importable sharecodes that
the committed Evxl snapshot (`resources/evxl/benchmarks.json`) lists under a
benchmark without `hidden: true`. The maintainer made both calls for the
2026-09-14 refresh and ruled them standing rules on 2026-09-15
([PR #289 thread](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/289#discussion_r4013683306)):

- **Delisting removes.** A bundled file whose sharecode the refreshed
  snapshot no longer lists is deleted in the refresh PR, even when KovaaK's
  still serves that benchmark ID unchanged. First applied to
  `Trial of Lords S2.json` (Black Dawn / Trials V2, benchmark 2285), which
  still matched KovaaK's exactly when Evxl dropped Black Dawn.
- **Hidden waits.** A sharecode under a hidden benchmark is not imported
  until Evxl unhides it. First applied to AIMCORE Benchmarks S1 and The Good
  Benchmark. Voltaic S5.5 Advanced had been kept out on the same grounds
  since the 2026-07-11 curation, and was imported once Evxl unhid it. A
  bundled benchmark that Evxl later hides is not covered by this ruling.

**The importer enforces neither rule.** `load_evxl_data` does not filter
`hidden`, and a sweep leaves the file for a removed sharecode in place,
logging that the manifest contains a removed sharecode. The refresh author
applies both: generate with `--only` over the listed, non-hidden codes, and
delete delisted files in the same PR.

**Consequences.** Corpus membership can be checked against the committed
snapshot alone, so a reviewer can verify a refresh PR mechanically. A user
who had a delisted benchmark shown stops seeing it after the update, with no
migration.

## 2026-09-14: App Copy Follows One Set Of Rules, And The Em Dash Is Gated Out

Status: Superseded in part by the
[2026-10-04 skill-judgment entry](#2026-10-04-skill-is-judged-by-the-typical-run-with-honest-uncertainty-in-verdicts-not-advice):
D4 keeping "Ready to move on." on a passed run that did not place no longer
holds, and that toast now ends at the fact. D4 dropping "Keep grinding..."
from the below-threshold toast stands. Everything else here stands.

The app's text was written one feature at a time, so the same condition read
differently from page to page and some messages sounded like log lines. Every
string the app shows now follows nine short copy rules, and every string the
rules changed was swept in one pass. What a user notices is that the same
thing now reads the same way on every page. A test keeps the em dash out of
the app's source for good.

**Scope of "copy" (rule 8).** Every string this app's code puts in front of a
user: page text, service messages a page shows verbatim (import refusals,
startup playlist warnings, store messages, warmup stop reasons), chart
annotations and legend entries, and accessible names, which a screen reader
announces. Text a bundled library draws itself is not copy: plotly.js's
toolbar and its `Share chart...` dialog, kept by the
[2026-09-12 entry](#2026-09-12-charts-keep-plotlyjs-4s-share-chart-button),
AG Grid's overlays, and Mantine's built-in text. The app passes no override for
any of it (no plotly `config`, no grid `localeText`); should it ever supply
such text, that text becomes copy. Console, launcher, and installer output,
`logging` lines, docstrings, comments, and documentation prose are outside the
rules.

**The rules.** AGENTS.md's styling conventions carry the operative form; the
numbering is the proposal's.

1. *A sentence ends with a period; a status readout does not.* `Settings
   saved.` is a sentence; `Update interrupted · 8 of 40 refreshed`, the
   Position hint, and a closing `File: {path}` are readouts. A semicolon never
   joins two sentences. A sentence that ends on an inline link puts its period
   in a separate child after the anchor, or the period renders underlined as
   part of the link. Basis: Microsoft's periods and semicolons entries and the
   Windows writing guidance; Apple punctuates message bodies; Google and
   Polaris also avoid semicolons. Material, Polaris, and Atlassian drop the
   period on a lone-sentence tooltip, and lose on the Windows-first weighting.
2. *No em dashes.* Prose splits into sentences; a readout chains fragments
   with ` · ` (space, middle dot, space). The one exception is the `—` empty
   value under Last played when no scenario is selected
   ([2026-06-30](#2026-06-30-model-home-last-played-empty-states-explicitly)).
   The run-toast scenario/score separator became a colon, the separator the
   celebration toast already used. Why: the no-em-dash ruling of the
   [2026-08-11 setup-card entry](#2026-08-11-a-fresh-install-is-asked-once-on-a-card-keyed-to-key-absence),
   which deferred this sweep; Material calls em dashes best avoided in UX
   writing and Atlassian prefers two sentences. No guide prescribes a fragment
   separator; the middle dot is the web's metadata separator and the grid
   status lines already used it.
3. *Casing (D2).* Sentence case for controls (labels, switches, buttons,
   placeholders), toast, alert, and modal titles, status lines, tooltips,
   chart annotations, and legend entries. Page titles, section headings, and
   grid column headers keep Title Case, as do proper names (KovaaK's, Steam
   ID, PB, SteamID64) and the named chart modes "Score vs Sensitivity" and
   "Score vs Time". Prose that quotes a control repeats its on-screen casing.
4. *One ellipsis form.* The single `…` character, and only for work still in
   progress (the fill's live readout). Placeholders are bare noun phrases, a
   path is never elided, and no line trails off for tone. The app authors no
   command that opens a further dialog, so the desktop ellipsis-on-command
   convention has no site. Basis: Microsoft, Apple, Atlassian, and Polaris use
   the character; Polaris rejects it on placeholders; Windows and Material
   endorse it for in-progress text.
5. *Contractions, consistently (D6).* The common ones: can't, couldn't,
   doesn't, isn't, wasn't, aren't, you're. A contraction and its full form
   never both appear on screen (Microsoft's consistency clause); "do not" is
   reserved for a warning the user must not skip (Material's carve-out), and
   no string uses it today.
6. *Control names are bold (D8), user-typed text is quoted.* A control named
   in prose is bold, in its on-screen casing, and takes its type word when the
   label reads as prose: "Turn on the **Show hidden** switch", "Press the
   **Detect my accounts** button again". Where bold cannot render (a toast
   title, already bold; an accessible name) the name stays plain and the type
   word carries it. A page name ("Settings") and a paraphrased value ("the
   oldest date", "a checkpoint hour") are not control names. User-entered free
   text keeps double straight quotes (`"{name}"`, `KovaaK's username "X"`),
   because playlist names and usernames can contain anything; tokens (Steam
   IDs, playlist codes, counts, full paths) stay bare; a literal file key is
   quoted (`a "code" field`). The app now has a three-way marker: bold for a
   control, double quotes for what the user typed, nothing for a token.
7. *Vocabulary.* The software is *this app* or *the app*, never *the
   dashboard* (the
   [2026-08-21 launcher entry](#2026-08-21-the-launcher-narrates-a-slow-start-and-keeps-its-120-second-ceiling)).
   The run source is the *stats folder*. A cached position is *from cache*.
   *Position*, *Rank*, and *PB* keep the
   [2026-07-06 meanings](#2026-07-06-one-word-per-concept-in-leaderboard-verbiage),
   so a leaderboard lookup is a *position lookup*. A playlist's identifier is
   its *playlist code*; the import help introduces KovaaK's own name, *share
   code*, once. Instructions say *turn on* and *turn off*, states say *on* and
   *off*, the control is a *switch*, and *toggle* is never a verb. An
   open-ended list uses *such as*, never *etc.* Data the app can't use is *not
   valid*, never *invalid*, and a message names the specific problem where it
   can. The log pointer is always `See data/logs/debug.log.`
8. *A message that reaches the screen is copy wherever the app builds it*
   (scope above). The diagnostic detail stays in the log line beside it.
9. *Error copy says what happened, then what to do when there is something to
   do (D7).* A failure with no useful recovery says only what happened. An
   object name or a path never opens a sentence: a noun names it first, and a
   count or a score may lead. A path goes inline only as the last words of a
   message's only sentence (`Couldn't read the playlist file {file}.`);
   otherwise the message names the file by kind, finishes its sentences, and
   closes with the labeled readout `File: {path}`. The toast title carries the
   verdict, unchanged from the
   [2026-08-03 policy](#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy);
   the "… failed" titles stay, since Atlassian endorses the form and only the
   legacy Windows guide bans "failed to".

**The decisions**, all ruled or ratified by the maintainer on PR #247.

- *D1, the Position hint* (ratified 2026-09-14): middle-dot fragments with
  the instruction halves dropped (`N/A · set your KovaaK's username in
  Settings`, `… · lookup failed`, `… · from cache`). The Refresh button beside
  the value is the affordance, and a hint that keeps "Refresh to update"
  wraps a 300 px stats box to two lines and pushes Refresh to a third
  (measured 2026-08-21). The unset variant keeps its Settings link because no
  adjacent control repairs it. A screen reader may skip the glyph, so each
  hint reads correctly without it. Rejected: keeping the instruction halves
  (a two-line field on every stale render); full sentences beside a
  parenthesised value.
- *D2, casing* (ratified 2026-09-14): as rule 3. The Microsoft and Windows
  guides, Material, Atlassian, Polaris, GitHub's Primer, Obsidian's plugin
  guidelines, and the Mantine docs all use sentence case for controls, modal
  titles, and notification titles; macOS alone title-cases controls, and this
  is a Windows app. The same guides also lowercase page titles, section
  headings, and column headers, so the Title Case exception for those is
  house style, not convention; extending sentence case to them would rename
  surfaces the README, specs, and launch material already name, and is a
  separate scope question. Rejected: Title Case for every control; leaving
  casing unruled.
- *D3, the two unset-username status lines* (ratified 2026-09-14): keep the
  split, "Percentiles unavailable." on the overview and "Positions
  unavailable." on the scenario table, because each names the columns its own
  page empties. Rejected: one noun for both, which names a column the overview
  does not have.
- *D4, the coaching flourishes* (ruled 2026-09-12): keep "Ready to move on."
  on a passed run that did not place; drop "Keep grinding..." from the
  below-threshold toast, which already states the score, the shortfall, and
  any placement, and which repeats on every miss in a session, where
  Atlassian and the Nielsen Norman Group say a flourish wears out. No guide
  covers a flourish on a miss, so this applies general guidance; a short
  repeated-run comparison with a few users is how to measure it if reopened.
  Rejected: "Keep grinding." with a period (taste with no comprehension
  argument, and a period does not answer repetition); dropping both lines.
- *D5, sequencing* (ratified 2026-09-14): the sweep lands before the release
  the launch announcement promotes, because the post's lead visual is a run
  toast beside the Position field, both of which this sweep rewrote. Rejected:
  shipping the post against the old copy.
- *D6, contractions* (ratified 2026-09-14): as rule 5, reversing the first
  draft's full-form rule. Microsoft, the Windows guidance ("too formal or even
  stilted" without them), Google, Material, Apple, Atlassian, and Polaris all
  say to use common contractions. One 2026 corpus study found AI-generated
  academic abstracts lacked the informality features it measured,
  contractions among them; that is a frequency difference in one genre, not a
  detector, so it corroborates the guides rather than carrying the case.
  Rejected: full forms as house voice, legitimate as taste but not the
  convention.
- *D7, values in sentences* (ratified 2026-09-14): as rule 9, with the
  supplemental path written as the readout `File: {path}`. Windows says to
  avoid starting sentences with object names (a value can open with a
  lowercase letter, a digit, or a backslash) and keeps a full path out of the
  main sentence. Rejected: the first draft's ban on every sentence-initial
  value, which would have rewritten clear count-led toasts; exempting the
  store messages as a named exception; writing the path as a sentence (`The
  file is {path}.`); and the "verdict: value" colon tail, which is the log
  idiom. A true second line for the path in alerts and toasts would be closer
  to the Windows layout; it is a component change, and the readout degrades
  into it without a word changing.
- *D8, control names in prose* (ruled 2026-09-14, the alternative): as rule
  6. Apple's rule is that sentence-style element names need marking; Atlassian
  bolds element names in app copy; Microsoft's in-UI guidance prefers wording
  that sets the name off, adding the element type. Bold gives a lowercased
  verb-phrase label a visible edge, and the type word stays because a screen
  reader does not announce bold. The precedent for bold in app copy is
  narrower than for the type word, so this is a product judgment for this
  app's sentence-case labels rather than a convention. Rejected: the type word
  alone (the 2026-09-04 lean); bolding only the four type-word sentences,
  which would put a bold and a plain control name on one detection line;
  quotation marks, reserved for user text; dropping the name beside its
  button.

**Mechanics that hold the rules.**

- One helper, `control_name()` in `source/components/control_name.py`, builds
  the bold span as `html.B`. Not a bold `dmc.Text`: an unsized `dmc.Text`
  renders at Mantine's md size, larger than the 14 px tooltip, description,
  or toast body around it. A chart annotation cannot hold a component and
  writes `<b>…</b>` into its string, which plotly draws. Sentences that carry
  a bold name are children lists; the ones returned from callbacks are built
  fresh per call, and `toast()` accepts a list message.
- `read_store_document` and `decode_store_document` take the file's `kind`
  ("settings file", "playlist visibility file", "playlist file") from their
  four call sites. A malformed stamp is quoted with `json.dumps`, so the
  message shows `"1"`, `true`, or `null` as the file holds them, not Python's
  `repr`.
- Log lines are unchanged where the new user message dropped a fact or added a
  user-only pointer: every import and delete refusal logs its previous text
  beside the new message, and the file-collision refusal is logged where the
  file name is known, in `_guard_playlist_destination`. The playlist-save
  refusal points the user at the log and nothing on the write path records its
  `OSError`, so its warning gained `exc_info` and carries the traceback. Not
  every log-directed message has an exception behind it: a run file with a
  missing field, or a Steam account list the app does not recognize, logs a
  plain warning. The startup playlist
  warnings and the store messages are logged by helpers that log what they
  show, so those log lines follow the new copy. A user-root playlist file the
  loader skipped was logged twice with identical text (store layer and
  loader) until the
  [2026-09-26 logging conventions](#2026-09-26-log-lines-delimit-their-values-by-kind)
  shipped; the loader now only queues the message for the UI. That entry is
  also the audit of how log lines delimit their values.
- `tests/test_em_dash_guard.py` walks every module under `source/`, visits
  every string constant including f-string parts, skips docstrings, and fails
  on an em dash outside an allowlist holding only the Last played glyph, keyed
  by module, enclosing function, and value. It does not see `assets/`, and it
  does not gate the three-period ellipsis, which clientside JavaScript spreads
  and a log line use legitimately. `tests/rendered_text.py` flattens children
  and renders a bold span back as `**name**`, so tests assert the ratified
  text verbatim and a name that loses its bold fails.

**Deliberately not changed.** Softening the red refresh-failure toast, whose
title question this sweep answered and whose color question stays open in
[tech_debt.md](./tech_debt.md) *(resolved 2026-09-27: it stays red, see
[The Manual-Refresh Hard Failure Stays Red](#2026-09-27-the-manual-refresh-hard-failure-stays-red))*;
the configured-but-wrong username; the Steam ID
mismatch toast's structure; the two `plot_service.py` empty-state messages the
page callbacks never reach; the Aim Training Journey page beyond its banner
and one label; the personal best celebration surfaces, already in the target
style.

**Supersedes in part, for copy only.** Each entry keeps its decision and gains
a note where its quoted strings changed:
[2026-08-03 notification layer](#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy),
[2026-08-09 unset username](#2026-08-09-an-unset-username-is-stated-in-place-never-reported-as-a-failure),
[2026-08-09 Scenario Performance naming](#2026-08-09-the-graph-page-is-scenario-performance-its-panel-is-chart-options),
[2026-08-11 setup card](#2026-08-11-a-fresh-install-is-asked-once-on-a-card-keyed-to-key-absence),
[2026-08-20 run points](#2026-08-20-run-points-get-a-size-preset-and-a-color-and-the-chart-stops-there),
[2026-08-21 empty point color](#2026-08-21-the-empty-point-color-is-called-default-and-the-points-follow-the-theme),
[2026-08-21 master switch](#2026-08-21-run-notifications-have-a-master-switch-and-the-threshold-switch-is-renamed),
[2026-08-22 playlist fill](#2026-08-22-the-playlist-fill-reports-degradation-in-place-only),
and
[2026-09-02 celebration](#2026-09-02-a-new-personal-best-celebrates-on-every-page).

**Sources**, read 2026-09-04 unless noted:
[Microsoft capitalization](https://learn.microsoft.com/en-us/style-guide/capitalization),
[contractions](https://learn.microsoft.com/en-us/style-guide/word-choice/use-contractions),
[periods](https://learn.microsoft.com/en-us/style-guide/punctuation/periods),
[semicolons](https://learn.microsoft.com/en-us/style-guide/punctuation/semicolons),
[ellipses](https://learn.microsoft.com/en-us/style-guide/punctuation/ellipses),
[etc.](https://learn.microsoft.com/en-us/style-guide/a-z-word-list-term-collections/e/etc),
[toggle](https://learn.microsoft.com/en-us/style-guide/a-z-word-list-term-collections/t/toggle),
[turn on, turn off](https://learn.microsoft.com/en-us/style-guide/a-z-word-list-term-collections/t/turn-on-turn-off),
and [formatting text in instructions](https://learn.microsoft.com/en-us/style-guide/procedures-instructions/formatting-text-in-instructions);
the [Windows app writing style](https://learn.microsoft.com/en-us/windows/apps/design/style/writing-style);
the legacy Windows UX guide on
[error messages](https://learn.microsoft.com/en-us/windows/win32/uxguide/mess-error)
and [UI text](https://learn.microsoft.com/en-us/windows/win32/uxguide/text-ui);
Google developer style on
[contractions](https://developers.google.com/style/contractions),
[capitalization](https://developers.google.com/style/capitalization),
[ellipses](https://developers.google.com/style/ellipses), and its
[word list](https://developers.google.com/style/word-list);
Material 3 [UX writing best practices](https://m3.material.io/foundations/content-design/style-guide/ux-writing-best-practices)
and [grammar and punctuation](https://m3.material.io/foundations/content-design/style-guide/grammar-and-punctuation);
the Apple Style Guide on
[quotation marks](https://support.apple.com/guide/applestyleguide/q-apsg38496e66/web)
and [contractions](https://support.apple.com/guide/applestyleguide/c-apsgb744e4a3/web);
Atlassian [language and grammar](https://atlassian.design/content/language-and-grammar)
and [writing style](https://atlassian.design/content/writing-style);
Polaris [grammar and mechanics](https://github.com/Shopify/polaris/blob/main/polaris.shopify.com/content/content/grammar-and-mechanics.mdx);
Primer [content](https://primer.style/product/getting-started/foundations/content/);
Obsidian [plugin guidelines](https://docs.obsidian.md/Plugins/Releasing/Plugin+guidelines);
the Nielsen Norman Group on
[error messages](https://www.nngroup.com/articles/error-message-guidelines/);
and the corpus study
[Informality features in AI-generated academic writing](https://www.sciencedirect.com/science/article/pii/S1475158526000019).
Rule 7's *not valid* line follows the Microsoft Writing Style Guide's word-list
entry on the pair and the Windows error-message guide, read 2026-09-13. Each
guide's position, question by question, is in the research note behind the
proposal (`ignore/design-notes/copy-conventions-research.md`, main checkout
only, untracked).

Provenance: proposal
[#247](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/247)
(opened 2026-08-21; D4 ruled 2026-09-12, D8 ruled 2026-09-14, D1 to D3 and D5
to D7 ratified 2026-09-14), shipped in
[#291](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/291).
Distilled from `docs/proposals/app_messaging_consistency_proposal.md`, deleted
in the shipping PR; git history holds its Copy block, which lists every string
the sweep changed.

## 2026-09-12: The Local Scenario List Comes From The Run Store

Status: Accepted

With no playlist selected, the Scenario Performance dropdown listed scenarios
by reading the stats file names, and it cut each name at its first hyphen. A
scenario like "Anti-Centering Easy" showed up as "Anti", and choosing it said
there were no local runs. The list now comes from the runs the app has
already loaded, named the way each stats file names its own scenario. A
scenario none of whose files could be read no longer appears.

**The defect.** `get_unique_scenarios` listed the stats directory and took
`file.split("-")[0].strip()` as the name, splitting at the first hyphen
rather than at the ` - Challenge - ` separator. The run store
(`kovaaks_database`) is keyed by `RunData.scenario`, which
`extract_data_from_file` reads from the file's `Scenario:` line
(`Anti-Centering Easy - Challenge - ... Stats.csv` carries
`Scenario:,Anti-Centering Easy`; `Reflex Flick - Easy - ... Stats.csv`
carries `Scenario:,Reflex Flick - Easy`). The two sources disagreed for every
hyphenated name, and `is_scenario_in_database` is a plain membership test, so
a truncated entry fell to the "No local runs found" empty state. Measured on
the maintainer's corpus (8,066 files, 2026-09-12, names as the parser strips
them): 866 scenarios in the store against 838 dropdown entries, 13 entries
naming no scenario (`Anti`, `Reflex Flick`, `Reflex Flick Wide`, `cA x`,
`TSK`, and others), and 41 scenarios with no entry at all, among them the 23
`TSK - ...` scenarios collapsed into the single dead `TSK` entry.

**The store is the single authority for which scenarios exist locally.**
`get_scenario_names()` returns `sorted(kovaaks_database)`; it takes no
directory. `_local_scenario_options()` in the home page keeps its
`get_usable_stats_dir()` guard. The pin that guard reads is restart-scoped,
and the store is only ever filled behind a usable pin, so today the guard
never trims a populated list; it keeps the spec's promise (no usable
directory, no local list) a property of this function rather than of the
startup order. The store is populated at startup before the server serves,
and the watchdog adds newly played scenarios to it, so the list is complete
on first render. Rejected: fixing the split to cut at ` - Challenge - `. It
works for today's names, re-breaks on the next naming quirk, and still would
not be guaranteed to agree with the store's keys; the file's own field is the
only authority and the store already holds it.

**Accepted consequence: a scenario with no parseable run leaves the list.**
Before, such a scenario contributed a filename-derived entry that already
showed "No local runs found" when selected, so dropping it removes a dead
entry rather than hiding data. Its failed files are still reported the way
they were: the startup load's counted log line, and the watchdog's toast for
live imports.

**Incidental.** The per-render `os.listdir` of the stats directory is gone.
That was not the motivation, and no caching was restructured for it.

## 2026-09-12: Charts Keep plotly.js 4's Share Chart Button

Status: Accepted

Upgrading plotly put a "Share chart..." button on both of the app's charts,
because the new plotly.js turns that button on by default. The button stays
rather than being hidden. Sharing happens only when a user presses it,
confirms a dialog that names Plotly Cloud, and is signed in there, so it is
an export the user chooses and not data the app sends on its own. Users see it
beside the existing PNG download, and the user guide lists Plotly Cloud among
the services the app can reach.

**What changed.** plotly 7.0.0 bundles plotly.js 4.0.0, and Dash serves
plotly.js from the plotly package (`package_data/plotly.min.js`), so the
upgrade changes the browser runtime and not only the Python API. plotly.js
4.0.0 changed the `showSendToCloud` config default from `false` to `true`.
Neither `dcc.Graph` passes `config` (`graph-content` in
`source/pages/home.py`, `aim-training-journey-graph` in
`source/pages/aim_training_journey.py`), so both render the button. Ruled on
2026-09-12 (PR #283): ship it, do not suppress it. There is no config line to
carry this reason beside the code, because the behavior is a library default;
this entry is the only record that it is deliberate.

**What pressing it does**, verified against the bundled plotly.js 4.0.0. The
button opens plotly.js's own dialog naming Plotly Cloud, with Cancel and
Share; nothing is sent before Share. Share runs `sendDataToCloud`: it
serializes the figure with `graphJson` (data arrays and layout), opens
`plotlyServerURL` (default `https://cloud.plotly.com/newchart`; Dash sets no
`PLOTLYENV.BASE_URL`) in a new tab with the dashboard's
`window.location.origin` as an `origin` query parameter, and listens for a
`CHART_AUTH_SUCCESS` message from that origin, which Plotly Cloud sends once
the user is signed in there (the dialog offers account creation to anyone
without one). Only then does it `postMessage` the figure to that tab. Whether
an existing Plotly Cloud session skips the sign-in step is Plotly Cloud's
behavior, not visible in plotly.js. The app makes no request itself, and a
blocked popup ends the flow with nothing sent. The figure carries, on
Scenario Performance: the scenario
name and render time in the title; every plotted run's timestamp, score, and
accuracy, and its x value (sensitivity or date); the average-score line; and
the label and value of any rank, PB score, or score-threshold overlay shown.
On Aim Training Journey: playlist names, dates, progress percentages, and the
aim-training-hours checkpoint labels.

**Why it stays.** The flow is user-initiated, gated by a dialog that names
its destination, and completes in a Plotly Cloud tab the user can see, which
makes it an export in the same class as saving the PNG. That is what
separates it from crash telemetry, which the
[2026-08-10 bug-reports entry](#2026-08-10-bug-reports-land-on-github-issues-with-the-log-attached-unredacted-and-disclosed)
rejects as privacy-hostile for a local tool. The user guide's
outside-services table carries a Plotly row as the disclosure.

**Rejected alternative.** `config={"showSendToCloud": False}` on both graphs,
holding the plotly.js 3 default. PR #283 shipped that hold first and backed it
out on the ruling: it guarded against a hidden data flow that does not exist,
and the one real gap, the README's list of services, was cheaper to close by
updating the README.

**Reversing it.** Pass `config={"showSendToCloud": False}` to every
`dcc.Graph`, including any added later (a layout test that walks all graphs,
rather than naming ids, is the guard that holds), and remove the Plotly row
from the user guide's What it talks to table and "sharing a chart" from the
README's summary. **Revisit trigger:** plotly.js changing the flow so data
leaves before the dialog or without the Plotly Cloud tab, or changing the
default `plotlyServerURL`; or a user report of the button being mistaken for
a local save.

## 2026-09-11: Sensitivities Normalize To cm/360 At Parse Time From The File's Own Increment And DPI

Status: Accepted

Runs from older stats files were plotted under whatever sensitivity number
the game they were played on used, so a Valorant-era run sat at the far left
of the sensitivity axis instead of next to the centimeters it actually
equals. Those runs are now converted to cm/360 the moment their file is read,
using two fields KovaaK's has written into every stats file since 2024. They
sort, group, and earn run notifications exactly like runs recorded in cm/360,
and the playlist tables' PB cm/360 column fills in for them. Runs from 2019
to 2021, whose files predate those fields, keep their original label and are
never dropped.

**The conversion, and where it runs.** `extract_data_from_file` in
`source/kovaaks/data_service.py` reads the stats file's `Sens Increment:` and
`DPI:` lines alongside the `Sens Scale:` and `Horiz Sens:` it already read,
and after the key-value loop computes
`cm/360 = 360 x 2.54 / (0.07 x increment x DPI)`, rounded to
`sens_round_decimal_places`, storing it as `horizontal_sens` with
`sens_scale` set to `cm/360`. It runs after the loop and not inline because
`DPI:` follows `Horiz Sens:` in the file, so the inputs are only complete
once the whole tail has been read. A run already on the cm/360 scale keeps
its recorded value untouched. A run missing either field, or carrying one the
conversion cannot use, keeps its original value and scale. "Cannot use" is
wider than "not a number": empty, zero, and negative, but also the non-finite
values `float()` accepts (`inf`, `nan`), magnitudes that make
`0.07 x increment x DPI` underflow to zero or overflow to infinity, and a
conversion that rounds away to zero at the configured precision. The rounding
happens inside the same guard that validates, so the value checked is the
value stored and no gap between them can record a false `0.0 cm/360`. Neither
field joins the parser's required-field check: legacy files lack them and
must still load, and an unusable value costs the conversion, never the run --
and never the startup scan, which has no guard of its own around the parser.
Normalizing here means every consumer inherits it with no change of its
own -- the three sensitivity-key builders, the `SortedDict` ordering, the
plot axis and hover, run notifications, and the PB cm/360 column all read
`RunData.horizontal_sens` and `RunData.sens_scale`. `RunData`'s shape is
unchanged, so the original scale value is not retained. The run database is
in-memory and rebuilt from the stats directory at every start, so historical
runs convert retroactively on the next launch and the choice is fully
reversible: there is no cache to invalidate or migrate.

**What `Sens Increment` and `DPI` mean.** These are now relied-upon fields,
so their semantics are recorded here. `Sens Increment` is the run's
sensitivity re-expressed in KovaaK's internal base scale, which
`resources/sensitivity converter/response.json` names UE4
(`IncrementFormula: "Sens * 0.07"`, yaw 0.07 degrees per mouse count),
whatever per-game scale the run was played on. The empirical invariant, over
the 7,494 corpus files that carry the field: the recorded increment equals
that scale's own formula value divided by 0.07. All 17 distinct cm/360
`(sens, DPI)` combinations satisfy
`increment = 360 x 2.54 / (0.07 x cm x DPI)` with a largest deviation of
4.4e-7 across 6,266 files, consistent with six-decimal recording, which pins
the base yaw to 0.07 exactly. For game scales the increment carries no DPI
term and is DPI-independent, as the capture's game formulas require:
`0.2 Valorant` records `0.199886` at both 400 and 1600 DPI. The
already-normalized scales fall out of the same formula: in/360
(`360 / (Sens * DPI)`) yields `2.54 x Sens` cm and counts/360
(`360 / Sens`) yields `2.54 x Sens / DPI` cm. `DPI` is whatever the user
typed into KovaaK's settings, not a measurement.

**KovaaK's Valorant yaw is 0.06996, not the community 0.07.** The capture's
Valorant entry records `IncrementFormula: "Sens * 0.06996"` and
`InchesFormula: "360 / (Inches * 0.06996 * DPI)"`, and the corpus measurement
agrees (increment/sens is 0.99943 across all five Valorant sensitivities).
The difference is 0.06%, invisible at one decimal place, but it means the
increment path reproduces KovaaK's own displayed numbers where a
community-yaw table would not. Rounded test expectations alone cannot pin
this, so the parser tests also assert the unrounded value at `rel=1e-5`: a
regression that recomputes from the raw sensitivity with the community
constants lands a relative 5.7e-4 away and fails.

**Rejected: a formula evaluator over KovaaK's scale definitions.** The
alternative was to evaluate the capture's per-scale `IncrementFormula`
entries directly. Of its roughly 35 scales, Splitgate, Paladins, and PUBG
multiply by the run's FOV (PUBG is also exponential in the sensitivity),
Battlefield V/1/Hardline, GTA 5, and Battlefield 6 are affine, and
counts/360 and in/360 invert the sensitivity, so reproducing the capture
faithfully needs an expression evaluator, the run's FOV as an input, a
mapping from the stats file's `Sens Scale` string onto the capture's
`ScaleName`, and a refresh whenever KovaaK's adds a scale. It offers nothing
over the increment the file already records, which converts every scale --
including scales added in future game updates -- with zero per-scale
knowledge. A fixed per-scale yaw table, a weaker version of the same idea,
would convert the FOV-dependent and affine scales silently wrong.

**Settled: legacy runs keep their label, and recorded DPI is trusted
as-is.** The 570 DPI-less runs from 2019 to 2021 stay grouped under e.g.
`5.0 Overwatch`. Data is never excluded because its DPI is unknown, and no
legacy-DPI config knob is added. Separately, the app cannot detect a mismatch
between the DPI a file records and the mouse's physical DPI, so the recorded
value is trusted wherever it is read -- on the chart and, since this change,
in the PB cm/360 column. The known instance, 368 Valorant runs misrecorded at
400 DPI that convert to about 163.4 cm/360 instead of about 40.8, is
accepted; four of them are scenario personal bests and sort to the extreme of
that user-sortable column. Any in-app override (a config knob, a per-era DPI
map) would be a second source of truth that hides a data error instead of
fixing it, and withholding the column for converted PBs would hide 4 wrong
values by dropping 68 correct ones. The escape hatch stays on the data side:
a one-time edit of the `DPI:,400` lines in the affected files.

**Notifications judge the normalized group.** The watchdog computes
`nth_score` and `is_new_sensitivity` against the scenario's runs at the same
sensitivity key, so after conversion the normalized group is the unit for
placement and for first-sensitivity detection. Where a converted group shares
a rounded value with a native one, the merged history is the denominator: a
run that would have placed within Top N among the raw-scale runs alone can
fall outside it, and a first native run at a converted group's value is not a
new sensitivity. No separate raw-scale notification history is kept, and the
notification rules themselves do not change.

**The rounding fix does not reach legacy runs.** Rounding the raw sensitivity
to one decimal place collapsed `0.16`, `0.2`, and `0.25 Valorant` into one
`0.2 Valorant` group. Converting first moves the rounding onto the cm/360
result, where one decimal place is the right precision, and those three
separate into 51.1, 40.8, and 32.7 cm/360. The fallback branch keeps today's
raw-sensitivity rounding, so the 95 legacy `0.32 Valorant` runs still display
as `0.3 Valorant`.

**Provenance.** Proposed and merged as
`docs/proposals/sensitivity_conversion_proposal.md` (PR #277); both decisions
ruled on 2026-09-11 (PR #279), each accepting the recommendation. It
supersedes a 2026-08-03 draft reviewed on PR #197, which was parked and
closed unmerged. Corpus numbers were verified against the live stats
directory on 2026-09-05: 8,064 parseable files, of which 7,494 carry both
fields and 570 carry neither, with no file carrying only one.

Superseded in part by the
[2026-09-26 recorded-setting entry](#2026-09-26-a-converted-run-keeps-the-setting-it-was-recorded-at-for-display-only):
the clause "`RunData`'s shape is unchanged, so the original scale value is
not retained" no longer holds. A converted run keeps its recorded value,
scale, and DPI, for the chart hover only. Everything else here stands,
recorded DPI trusted as-is included.

Superseded in part by the
[2026-09-27 per-scale precision entry](#2026-09-27-sensitivity-precision-is-fixed-per-scale-and-its-config-knob-is-retired):
the paragraph "The rounding fix does not reach legacy runs" no longer holds. A
legacy run keeps the sensitivity its file recorded, unrounded, so the 95
`0.32 Valorant` runs read `0.32 Valorant`. cm/360 values still round to one
decimal place, now fixed rather than configured. Everything else here stands.

## 2026-09-04: Comment And Docstring Conventions

Status: Accepted

The application code carries a lot of explanatory prose, and nearly all of it
is the useful kind, but the rules that shaped it were never written down. A
fresh session had to learn the house style by imitation, and the two places it
tended to go wrong were narrating what code already says and writing a comment
as a reply to whoever asked in review. The agent instructions now state what
earns a comment, what stays beside the code when fuller rationale also lives
elsewhere, and the shape a docstring takes. The enforced lint and type gates
do not change.

**What was measured (2026-09-04, 44 files under `source/`; later additions
dated).** Comment-only lines are 12% of code lines and docstring lines 23%;
the test tree sits at 4% and 6%. Of 385 comment blocks, 58 run five lines or
more and 12 run eight or more. Nearly every definition has a docstring; 352
open in the imperative against 9 in the third person, and none carries an
Args/Returns/Raises section. Identifier spans in docstrings and comments run
383 double-backtick against 32 single (2026-09-08). `X | None` appears 217
times against one `Optional[]`. 42 of 47 `# noqa` markers give no reason, and
of the 14 blind-except suppressions 4 name what the catch protects
(2026-09-08). Narration is confined to the oldest modules: 17 label-style and
36 trailing comments in the whole tree, plus four legacy TODOs in
`kovaaks/data_service.py`, none of which names a concrete problem. Fifteen of
1143 non-merge commits exist only to correct a stale comment or docstring.

**Why a written bar rather than a trim.** The volume sits in the newest code
and is rationale, not narration, so removing narration barely moves it. Nearly
every measured dimension shows a style the code already follows: no
Args/Returns/Raises sections, imperative summaries, double-backtick
identifiers at better than nine spans in ten, one `Optional[]` in the tree.
That style existed only as a pattern to imitate, in a repository where most
edits come from fresh agent sessions, and AGENTS.md is the only channel that
reaches a session on every edit. The case for the section is transmission: it
writes down what is already there so a new session does not default to
Google-style sections or narrating comments. One cost does recur and has a
number: comments go stale, a few because they cite a relative position, a
count of things in the tree, or a neighbor's name and the neighbor moves, and
more often because the behavior they describe changed. The fifteen repair
commits above are that cost, and the rule addresses both halves. A second is
first-hand rather than measured: from the sessions that wrote this code,
comments authored as the answer to a review question that then outlive the
thread. On placement the rule keeps the failure-preventing reason beside the
code and moves only evidence and history up, into a document whose scope
already fits, so a bare pointer never stands where the constraint was and this
log is not widened into a store of library detail; length alone is never the
trigger. The three comments in `source/` that point at this log already do
exactly this. The two hygiene rules are new rather than transcribed: a reason
on suppressions the rule code does not explain is already the norm, but a
blind-except suppression that names what the catch protects is four of
fourteen, and none of the four legacy TODOs names a concrete problem; both
ride on the same no-sweep scope as the rest. The section sits beside the
2026-08-01 two-layer doc-style entry as the code-side counterpart: that one
governs prose in the docs, this one governs prose in the code.

**What is deliberately not enforced.** No lint rule judges comment quality.
Ruff's `pydocstyle` `pep257` convention would check only part of the docstring
shape (summary placement, the blank line after it, mood, terminal period): 39
findings on 2026-09-08 under the locked ruff, none safely auto-fixable, and it
does not see Args/Returns/Raises sections, single-backtick identifiers, or a
summary that starts below the opening quotes. Deferred, and not a substitute
for the written rule. Annotations are not required: under mypy's
`disallow_untyped_defs`, 59 diagnostics across 56 definitions in 12 files
(2026-09-08, after `check_untyped_defs` landed), 39 of them Dash callbacks and
page layouts whose parameters are whatever Dash passes and 17 ordinary
functions. The options are nothing, annotating the seventeen, or a sweep plus
the mypy flag; a prose rule no gate checks was rejected because it would
drift. The `N` naming family stays off: its 35 hits are API models mirroring
KovaaK's field names. The 2026-07-03 ruff consolidation entry is unchanged.

**No sweep.** Existing comments are not rewritten to match. The rule governs
new and edited comments, the same no-backfill convention the layer-1 summaries
follow. The legacy TODOs and label comments in the oldest modules are a
separate drive-by when someone is in those files anyway.

## 2026-09-04: The Launcher's Browser Open Is A Config Knob; Tab Reuse Is Not Achievable

Status: Accepted

The desktop shortcut opened a browser tab every time the dashboard started,
and a tester who keeps that tab in a browser folder and restarts the app often
was collecting a new one each time. There is no way for a launcher to reuse
the tab that is already open, so the app now takes a config setting,
`open_browser_on_launch`, that stops it opening one at all. It is on by
default and the console still prints the address, so the only person affected
is the one who turns it off.

**Tab reuse is not achievable from a launcher.** `Open-Dashboard` is
`Start-Process "http://<address>:<port>/"`, and shell-executing a URL always
creates a new tab. Neither Windows nor the browsers expose "focus the tab
already showing this URL", and `window.focus()` from a background tab is
blocked without user activation. The request as posed ("open only if the tab
is not there") has no API behind it. Suppressing the open is the only lever
that exists.

**What this protects, and what it does not.** Every stale tab is a live
hazard, not just clutter: the supported model is one active tab
([specs/notifications.md](specs/notifications.md)), because `message_queue` is
process-wide and each drain's payload reaches one client, so with two tabs
open a run toast or a PB celebration lands in whichever drain runs first. The
knob lets a user stop accumulating tabs, but it only helps the user who finds
it. The hazard still reaches everyone else, so this is the interim, not the
fix.

**Live-client detection is the eventual fix, and is deferred.** The server
always knows whether a tab is watching, since every open tab polls
continuously, so "skip the browser when a client is already connected" is
detectable. It does not serve the case that prompted this. Restarting the app
means closing the console, which kills the app and releases the mutex, so the
relaunch is a cold start and the surviving tab is a dead tab from the previous
session: at the moment the server becomes ready that tab has not checked in
yet, and it reconnects only on its next timer tick. Chromium throttles timers
in long-hidden tabs to roughly once a minute, so the launcher would have to
wait up to a minute after readiness before it could decide, on every cold
start, to serve a minority case. The knob has none of that cost.

**Rejected alternatives.** `data/settings.json` with a Settings-page control:
app-owned with a frozen three-key schema, and it would put a control on the
Settings page for something the app never does. A flag on the desktop
shortcut: passing it needs a bootstrap version bump, and the shortcut is
rewritten on every reinstall. Parsing `config.toml` in PowerShell: exactly
what `Get-ConfiguredEndpoint` exists to refuse, because TOML integer forms
(`8_051`, `0x1F73`) and pydantic coercion would make the launcher probe a port
the server did not bind. Two knobs (one for cold start, one for the
already-running branch): over-configuration for one behavior.

**The accepted smell.** `ConfigData` now carries a key the app never reads.
That is deliberate. `config.toml` is the only user-owned file both sides of
the install already agree on, and the launcher already asks the app's loader
to read it.

**The `Get-ConfiguredEndpoint` contract.** The one-line answer grew a third
field: `print(c.port, c.host, getattr(c, 'open_browser_on_launch', True))`.
The launcher splits the last stdout line into exactly three fields and reads
the third as on when it is the literal `True`; a two-field line is not
accepted, because a launcher never meets an older loader through a supported
path (the bootstrap runs `versions\<tag>\scripts\launcher.ps1` from the same
tag it reads the loader from) and a lenient parse would hide a broken
contract. The `getattr` is belt-and-braces against a hand-mixed install, kept
because the failure mode without it is this function's worst: a nonzero exit
takes the fallback and loses the port and host too, and a healthy app is then
declared dead on the wrong port.

**The snippet must contain no double quote.** Windows PowerShell 5.1, which
the desktop shortcut runs, re-quotes a native command's argument without
escaping the double quotes inside it, so the previous
`print(f"{c.port} {c.host}")` form arrived at python as `print(f{c.port}` and
exited with a `SyntaxError`. `Get-ConfiguredEndpoint` was therefore taking
its fallback on every launch, probing `8050` on `127.0.0.1` whatever
`config.toml` said, and any install with a non-default port or host would
have been reported as a dashboard that failed to start. The probe's first
form, `Get-ConfiguredPort` (`print(load_config().port)`, no double quote),
worked; the breakage arrived with the rename to `Get-ConfiguredEndpoint` and
its f-string, so the affected releases are `v2026.08.18` through the last one
cut before this fix. Backslash-escaping the quotes fixes 5.1 and breaks
PowerShell 7, which passes the backslashes through to python; both were
measured. The snippet now lives in a `$EndpointProbeSnippet` here-string,
uses `print` with commas instead of an f-string, and quotes the attribute
name with Python's single quotes, which survive both shells unchanged.

One consequence worth recording against
[2026-08-14](#2026-08-14-the-listen-address-is-configurable-loopback-by-default):
that entry's launcher half, deriving the probe and browser addresses from the
configured `host`, was inert in every installed launcher over that window,
because the fallback always reported `127.0.0.1`.

**Only stdout is captured, and not under `Stop`.** Two separate traps sit on
the same line. The first is ordering: stdout and stderr are separate pipes,
so merging them with `2>&1` gives no guaranteed order, and the "last line
wins" parse the original comment described as robust against a config warning
was not. Measured at roughly one run in sixty, the unknown-key warning
arrived after the print line, so the parse read the warning and fell back --
an intermittent wrong-port kill for anyone with a typo in `config.toml`.
Nothing read the stderr text, so it is discarded rather than ordered.

The second is the preference. The launcher sets
`$ErrorActionPreference = 'Stop'` at the top of the script, and 5.1 turns a
native command's redirected stderr into a terminating `NativeCommandError` on
its first line while that preference holds. The one line the loader is known
to write is the unknown-key warning, so any typo in `config.toml` reached the
catch-all and took the fallback. Paired with the redirect since the probe was
first written, and masked from `v2026.08.18` onward by the quoting bug above,
so fixing that unmasked it. Discarding stderr is still a redirect, so the
preference fix is needed either way. The capture now runs under a
function-local `Continue`, restored in the `finally`.

**These are 5.1-only failures, so a Python test cannot see them.** Both bugs
were invisible to a subprocess test, which quotes its arguments properly and
inherits no PowerShell preference. `windows-latest` ships Windows PowerShell
5.1, so the suite now dot-sources the real `Get-ConfiguredEndpoint` through
the PowerShell AST and calls it against a temporary install root, pinning the
three-field contract, the browser flag, and the unknown-key case in the shell
the shortcut actually runs.

**One launch of lag.** The launcher that performs an update is the previous
release's, selected by the bootstrap from the manifest before the update
check ran. The launch that installs the release carrying this change
therefore still opens a browser, and the setting takes effect from the next
one. Setting the key before that update is harmless: an older app names it in
the existing unknown-key warning and starts normally.

## 2026-09-04: Re-Asserting An Unchanged Leaderboard ID Writes Nothing

Status: Accepted

Starting the app took over a minute on a beta tester's machine before any page
would draw, and restarting did not help. Every startup rewrote the same 400 KB
file about 2,500 times over, once for each scenario it had ever played, to
store IDs that were already correct. It now checks first and writes only when
something actually changed. On the measured workload that step drops from 37
seconds to under a tenth of a second, and the app stops writing roughly a
gigabyte to disk on every launch.

**The waste.** `hydrate_leaderboard_id_cache` calls `save_leaderboard_id` once
per scenario in the user's `/user/scenario/total-play` response (26 pages of
100 for the reporting tester, so about 2,500 calls). Each call was a full
read-modify-write of the entire `scenarioName -> leaderboardId` mapping, ending
in an `fsync` and an atomic replace, and it ran even when the stored ID already
matched, because `fetched_at` was refreshed unconditionally. Measured on a
Samsung 990 PRO NVMe with a 3,000-entry, 416 KB mapping: **36.9s, ~1 GB
written, 2,500 fsyncs**. The fast path measures 0.09s and writes nothing.

**Why it was invisible.** The step logs nothing on success, so it appears in
`debug.log` only as a silent gap. A fresh total-play cache skips the network
but not the writes, so the affected sessions show no API calls at all. Its cost
lands inside the warmup worker's batch window, so it is reported as part of
`Percentile warmup complete: ... elapsed=67.1s` — a line whose `processed=0
skipped=379` invites reading the whole elapsed as drain cost. It is not: the
drain is a few thousand cheap reads. **Do not derive per-operation disk latency
from that line.**

**It also stalled every request thread.** `save_leaderboard_id` holds
`_CACHE_IO_LOCK` across its fsync, so for the whole hydration any waitress
thread touching any cache file blocked behind it. That is what produced the
`waitress.queue | Task queue depth` warnings in the tester's logs, a 38-second
first Home render, and Playlists times of 26-74 seconds that barely moved when
"show hidden" was toggled — both settings sat on the same fixed floor.

**Correcting the 2026-09-02 entry.** That entry attributed the tester's ~60s to
per-file antivirus scanning making small random reads "roughly 400x slower".
A probe on the reporting machine measured **0.029 ms per cache-file open** —
reads are fine there; the cost was fsync-heavy writes. The lock-scope decision
that entry records still stands on its own merits and is not superseded; only
its supporting attribution was wrong.

**Provenance is part of "unchanged".** The skip requires the stored `source` to
match as well as the ID. `merge_seed_leaderboard_ids` refreshes seed-owned rows
whose asserted ID changed and deletes those the corpus stops asserting, while
never touching learned ones (2026-07-20 entry), so a seed-owned row that
`total-play` confirms must still be rewritten to take live ownership —
otherwise a later corpus release could overwrite the ID of a live-confirmed
mapping, or drop the row outright. An ID-only check shipped in review and was
caught there.

Promotion costs one write per row, once: the first hydration after an install
promotes the seeded rows, and a corpus release promotes only the newly seeded
names that `total-play` also covers. That one-off run is about 20% slower than
the old unconditional rewrite, because a promoting call parses the mapping
twice — the fast-path check revalidates the mirror against a signature the
previous write already moved, and the slow path then parses again (44.9s versus
36.9s on a 2,500-call workload; recorded in `docs/tech_debt.md`, and removed by
the batch upsert). Every later startup is the steady state, measured at 0.09s
and zero writes.

**The stored value is authoritative.** The check reads the mtime-revalidated
in-memory mirror (2026-07-18 entry) rather than the file, so it inherits that
mirror's one accepted blind spot and no other. A stale hit skips a write whose
only effect would have been a `fetched_at` refresh; nothing reads `fetched_at`
on these entries. Conflict refusal, malformed-value replacement, and every
write path are unchanged — the fast path is purely additive.

**Not fixed here.** Hydration still makes one call per scenario; a batch upsert
folding all of them into a single atomic read-modify-write, as
`merge_seed_leaderboard_ids` already does for the bundled seed, is left as
follow-up. `_CACHE_IO_LOCK` still serializes every cache file operation
app-wide, and the Playlists overview still reads two cache files per played
scenario per row with no memo and no dedup across rows (measured 1,595 file
opens with "show hidden" on, 52% of them re-reads within one render). Both
remain in `docs/tech_debt.md` under Performance.

## 2026-09-02: Warmup Locks Are Never Held Across Cache I/O

Status: Accepted

The Playlists page could show a loading spinner for up to a minute after
startup, and importing or unhiding a playlist could appear to do nothing for
just as long. A background worker was holding a lock while it read hundreds of
small cache files, and the page needed that same lock to draw its progress
line. The worker now does its file reads with the lock released. It warms the
same scenarios as before, and a playlist you have just imported or unhidden can
now take its turn sooner instead of waiting for the scan to end.

**The invariant.** Neither `PercentileWarmupWorker._condition` nor the
module-global `_worker_lock` may be held across cache file I/O. Both are read
by UI callbacks: `get_percentile_warmup_state` (the Playlists status line and
refresh interval) takes `_worker_lock` and then `_condition`, and
`enqueue_playlist_percentile_warmup` (import, unhide) takes both as well. A
hold that spans per-scenario cache reads therefore blocks page renders, not
just the worker.

**Two sites violated it.** `_next_item` held `_condition` across its whole
skip-drain, which reads two cache files per candidate. This only bites when the
cache is warm: nothing returns early, so the loop walks the entire queue.
Measured at 0.13s for 317 scenarios on a fast SSD and about 60s on a
beta tester's disk, where per-file antivirus scanning makes small random reads
roughly 400x slower. (Attribution corrected by the 2026-09-04 entry: that
tester's reads measure 0.029 ms per open, so the ~60s was not read latency — it
was the hydration write storm running inside the same `elapsed` window. The
lock-scope decision below is unaffected.) A direct callback measurement, taken on the fast SSD with
per-candidate latency injected into `_freshly_satisfied` to model the tester's
disk, recorded 45.1s blocked versus 0.2s once the drain finished. That isolates
the lock and only the lock: the overview's own row build reads two cache files
per played scenario per row on the same disk, so the figure is not evidence
that the tester's page renders promptly after this change. `start_percentile_warmup_worker` held
`_worker_lock` across `_startup_queue()`, which reads two cache files per played
scenario; harmless from `app.py` because it runs before the server accepts
requests, but reachable from the settings save that first supplies a username.

**Shape of the fix.** `_next_item` pops under the lock and evaluates freshness
outside it; the popped name is claimed as `_in_flight` before the lock drops, so
a candidate under evaluation still counts toward `remaining_count` and the batch
cannot read as idle or announce completion mid-drain. The loop re-tests the
queue under the lock before waiting, so an enqueue that notifies while the
worker is evaluating is not lost. `start_percentile_warmup_worker` runs a
claim/park/publish handshake: it claims the start under the lock by setting
`_worker_starting`, releases the lock to enumerate, and publishes in a later
hold. There is no post-enumeration singleton re-check and nothing to discard,
because a second caller arriving during the window returns early instead of
enumerating a queue that would be thrown away. What can arrive in that window
is not a competing starter but an enqueue, which is what the parking below
exists for — the two halves are one protocol and must not be implemented
separately.

**Publication is not a gap.** Releasing the lock across enumeration means an
import or unhide can find no worker to enqueue against, where it previously
just waited for one; dropping it there would defer that playlist's warmup until
the next restart, silently. A `_worker_starting` flag marks the window, codes
arriving in it are parked in `_pending_enqueues`, and the starter adopts them in
the same lock hold that publishes the worker. They are enqueued after
publication, so they prepend ahead of the startup queue.

**Starting is a busy state, not an idle one.** The snapshot carries a
`starting` flag that is true from the moment a start claims the singleton until
its parked enqueues have drained, and the overview reads it as busy. Without
it, a poll landing before publication sees no queue, no in-flight item, and
generation 0, concludes the worker is idle, and disarms its refresh interval —
so nothing then observes the generation bumps that publication and the parked
drain produce, and the page sits on stale percentiles until the next visit. The
flag deliberately outlives publication for the same reason: clearing it at
publication would leave the same window between a freshly published empty
worker and its drain.

**Not fixed here.** `_CACHE_IO_LOCK` serializes every cache file operation
app-wide, but each hold is one file operation rather than a scan; recorded in
`docs/tech_debt.md` under Performance.

## 2026-09-02: A New Personal Best Celebrates On Every Page

Status: Accepted

A run that beats a scenario's personal best now gets a short burst of confetti
and a toast that says so. It fires on whatever page is open and for every
scenario, not only the one being watched, and the toast stays until it is
dismissed because the run that earned it was played in a fullscreen game. A
Settings switch turns the whole thing off. Nothing else about how runs are
reported changed.

**One drain decides.** The app shell hosts the `pb-celebration-interval`
(period `polling_interval`), the `run-events-batch` store, and
`publish_run_events`, which is now `message_queue`'s only consumer. Facts
travel and only the drain decides: it stamps each drained run `is_live`, names
at most one `celebrated_run_id`, and advances a monotonic
`animation_sequence` exactly when it names one. `NewFileMessage` carries
`run_id`, `scenario_previous_best`, and `is_new_sensitivity` — facts with no
verdict in them — and Scenario Performance reads the stamps instead of
re-deriving either. The ordering argument is the dependency graph, not a
protocol: a page callback triggered by the batch store necessarily runs after
the shell wrote it, so there is nothing to race. Four review rounds of
coordination machinery between two independent drains (a shared toast id, a
page-side freshness window, a celebrated-run registry, a registry plus a
watermark with deferral) are what this replaced; each moved the race without
closing it, and the single drain closes it by construction.

**The rule.** A run is celebrated when its score is *strictly* greater than
its `scenario_previous_best`, so a tie never celebrates and a scenario's first
run only sets the baseline. The newest qualifying live run in a batch wins and
an older one is plot-only, because one Dash response carries one payload and
drives one animation. That strict comparison is the only gate that ships: most
runs in a freshly imported scenario are personal bests, and the ruling
accepted that noise rather than inventing a minimum run count or margin before
anyone knows it grates, with the setting as the escape hatch. A gate can be
added later if it does.

**Freshness.** A run is stamped live when its `datetime_created` is within a
120-second cap plus one poll period of the drain, and stale otherwise. There
is no watermark and no drain bookkeeping: every drain empties the queue, so a
message a drain finds was never seen by an earlier one, and one appended
mid-drain is caught by that drain or the next, exactly once either way. The
cap sits two orders of magnitude above the default poll interval and
comfortably above Chromium's intensive throttling, which slows a hidden tab's
interval to about one tick per minute — and a tab can stay hidden through a
whole session, minimized or behind another tab, so a tight window would drop
exactly the mid-session personal bests this exists for. The poll period is
added because `polling_interval` carries no product cap: a run can be a
whole period old through nothing but the drain's
cadence, and a fixed cap below the configured period would stamp every run
stale and silently retire every toast liveness gates. The consequence, stated
rather than hidden: a deliberately slow poll widens no-tab replay by exactly
the period it chose. Validating the interval with a product cap instead stays
rejected, for the reasons in
[2026-09-01](#2026-09-01-configured-ports-and-poll-intervals-are-bounded-at-load).

**The toast.** Green, a trophy icon, titled "New personal best", and sent with
`auto_close=False` so it is still there on alt-tab. Its channel key is
`pb-celebration`, deliberately not `run-verdict`: an ordinary run toast lands
beside it rather than replacing it, and only a later celebration replaces a
celebration. It is a persistent channel in the sense the
[2026-08-31 toast-identity entry](#2026-08-31-repeatable-toasts-replace-in-place-with-a-visible-re-entry)
defines, and that entry owns the mechanism.

**The celebration takes the headline.** When celebrations are on, the
celebrated run's one toast *is* the celebration toast and the page's run toast
yields. The score threshold goal has no upper bound, so a goal above 100% let
a personal best read "Below threshold" while confetti fell, and even under a
goal it passes, "Threshold passed" says the less interesting thing. This
amends the priority rule in
[2026-08-03](#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)
for the celebrations-on state only: with the setting off, the verdict
headlines and a personal best has no toast of its own, exactly as before. A
personal best the drain did not celebrate — an older qualifying run coalesced
out of the batch, or one outside the selected scenario with auto-switch off —
follows the ordinary run-toast rules and has no guaranteed toast. The
guarantee is per run and one-sided: every run earns at most one notification,
and the celebrated run exactly one. One batch can therefore put two toasts on
screen when the celebration and the page's narration concern different runs,
and that is correct.

**The master switch does not reach it.** The two settings are independent
families: the celebration setting governs the confetti and the celebration
toast together, and Run Notifications governs the verdict and placement
toasts. With Run Notifications off and celebrations on, a personal best still
celebrates on every page while ordinary runs stay silent — a user in that
state has asked for two things at once. The toast travels with the animation
because it is the half that carries information; on a page other than Scenario
Performance, confetti without it is a burst with no explanation, and under
reduced motion the toast is the whole celebration. Coupling them was rejected
on that reading and on mechanics: the master switch's persisted value lives on
the Scenario Performance page, so the shell would need a second mirror store
to see it.

**A hidden tab holds the animation.** The ruling assumed that Chromium marks a
fully occluded window's tab hidden. The player is in KovaaK's fullscreen when a
personal best lands, so under that assumption a hard `document.hidden` drop
would mean the animation never plays for a real personal best on a
single-monitor setup — only from Preview. At most one celebration is held
instead, a newer one replacing it, and it plays
on the next `visibilitychange` to visible; playing while hidden would also
dump a stalled burst on the next alt-tab, since a hidden tab throttles
animation frames. The accepted cost, stated with the ruling: personal best
toasts are dismissed by hand on every setup, including one where the animation
played in view. Relaxing the toast to the normal lifetime is a one-line
follow-up that does not touch the pending mechanism. The ruling needed no
pre-ship evidence, and the asymmetry was the deciding argument: where the tab
never reports hidden the pending path is dormant and behaviour is identical,
and where occlusion does mark it hidden, pending is the only version that
plays at all. The post-ship check, run on 2026-09-28, did not bear out the
occlusion premise: on one Windows 11 machine (three monitors, both browsers
moved onto the game's), Firefox 156 and Edge 154 never reported a tab hidden
while KovaaK's covered the whole window, in borderless and exclusive
fullscreen alike, though minimizing did. The ruling stands on its asymmetry.
Where the game only covers the window, the pending path is dormant, the burst
plays unseen under the game, and the sticky toast is what the player comes
back to; a minimized window or a background tab still holds the burst.

**The animation.** `canvas-confetti` 1.9.4 (ISC) is vendored unminified under
`assets/vendor/`, with its LICENSE and a version pin, rather than hand-rolled:
it ships the physics, the shapes, the reduced-motion guard, cancellation, and
worker-thread rendering, and every later change is configuration instead of
physics code. `assets/pbCelebration.js` is the app-owned half — a name-keyed
style registry, Confetti alone in version one (the upstream Realistic Look
recipe unchanged, about three seconds), behind `play(style)` and
`celebrate(batch, style)`. An unknown style name plays Confetti rather than
nothing, so a style removed later never silently turns celebrations off. A
clientside callback on the batch store drives it, so the burst costs no server
round trip; the library is resolved at call time, because Dash serves
`assets/*.js` in its own order. There is no JavaScript lint, test, or build
step in this repo, so that file is held by review and a manual pass.

**No catch-up digest.** The "While you were away" digest existed because run
events accumulated while Scenario Performance was closed. Delivery is now
app-wide and continuous while any tab is open, so batches stop accumulating in
the case the digest served. What remains is the no-tab case, where the
freshness window draws the line: a personal best set within the window of the
next drain is celebrated on it, and anything older is never replayed. Bounded
replay is accepted rather than suppressed — a player who reopens the tab a
minute after the run wants the celebration, and the timestamp cannot tell that
case from a throttled hidden tab's, which must land. A backlog that does
arrive rebuilds the graph once, auto-switches once, and follows the per-run
rules above: up to two toasts, never a digest. Whether the celebration family
deserves its own longer or unbounded window is a follow-up question, carried
on the roadmap.

**What this supersedes.** The
[2026-07-06 coalescing entry](#2026-07-06-coalesce-pending-home-run-events)
loses its "sole consumer" clause — the shell's drain is the consumer now and
the page listens to a store — and its digest. Its coalescing rule survives,
applied to the batch: the page still considers only the latest matching run.
The [2026-08-21 master-switch entry](#2026-08-21-run-notifications-have-a-master-switch-and-the-threshold-switch-is-renamed)
loses the digest from the set of shapes its gate covers, and its deferral of
the queue-to-UI redesign for the drain alone; the product question that
deferral protected, app-wide verdict toasts, stays deferred, and run toasts
remain page-built and page-scoped. The
[2026-08-03 notification-layer entry](#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)
loses its rule that a personal best earns nothing beyond the run verdict, and
the "backlog digest included" clause of its replacement rule.

**Superseded in part, for copy (2026-09-14).** The master switch this entry
calls Run Notifications is labelled "Run notifications", and the celebration
description names it in bold: "…and doesn't depend on **Run notifications**."
The decision is unchanged. See [App Copy Follows One Set Of Rules, And The Em Dash Is Gated Out](#2026-09-14-app-copy-follows-one-set-of-rules-and-the-em-dash-is-gated-out).

Shipped in PRs #261 and #268; proposal and rulings in #248, toast mechanism
reconciled in #263. Distilled from the personal best celebration proposal, now
deleted.

## 2026-09-02: The Celebration Setting Is Browser-Local, On The Settings Page

Status: Accepted

The control that chooses how a personal best celebrates lives on the Settings
page, in its own Celebrations section, with a Preview button beside it. It
offers Off and four animation styles, and takes effect the moment one is
chosen rather than waiting for Save. The browser remembers the choice instead
of the app's settings file, so a different browser, or one whose site data has
been cleared, celebrates by default.

**The store is the setting.** `dcc.Store(id="pb-celebration-style",
storage_type="local")` in the app shell holds one string: `"off"` or a style
name, defaulting to `"confetti"`. The value was a style name from the start
even though version one shipped a switch, so the follow-up that turned the
switch into a style select only added values to a contract that already
existed and kept whatever was saved. The control initializes from the store
and writes back to it and carries no Dash persistence of its own, so a
switch's boolean
and a select's string never become two competing persisted values. The drain
reads the store as `State`, and so does the clientside animation: changing the
setting must not replay a batch already delivered.

**Why the Settings page.** The behavior is app-wide, so the Chart options
inspector on one page is the wrong home — undiscoverable, and a control there
describes itself as a chart option. This departs from the placement rule the
[point customization](#2026-08-20-run-points-get-a-size-preset-and-a-color-and-the-chart-stops-there)
and [master switch](#2026-08-21-run-notifications-have-a-master-switch-and-the-threshold-switch-is-renamed)
entries both state, that the inspector owns browser-persisted presentation
preferences. The departure is deliberate and narrow: that rule governs
preferences about the chart, and this one is about the app. It is also the
first browser-persisted control on the Settings page, beside a form whose
three fields are written to disk behind Save. The section is visibly separate,
its control applies instantly, and it touches neither the restart notice nor
the store alert, both of which speak for the form's three keys, so the form's
contract is untouched.

**Why not `data/settings.json`.** Rejected on cost, not principle. Settings v1
is a closed set of three string keys, so a new key is settings v2: a
validator, a version bump, the stamp script becoming a real migration under
the documented ordering contract, the launcher's trial-run window to be solved
for the first migrating release, and an older build refusing the v2 file on
rollback
([2026-08-11](#2026-08-11-durable-json-stores-carry-a-schema_version-stamp)).
A cosmetic preference should not be what forces that. When a setting that
deserves v2 arrives, this one joins it; only the store's backing would change.

**Instant apply needs one tick, and the tick is load-bearing.** The obvious
callback pair — the store as `Input` to the switch, the switch as `Input` to
the store — is a dependency cycle the Dash renderer refuses, so the switch is
initialized by a one-shot `dcc.Interval` that reads the store as `State`. That
tick is also the gate on the write direction, and this is the part worth
remembering: mounting the page fires the write callback with the switch's
*layout default* despite `prevent_initial_call`, with the switch itself as
`ctx.triggered_id` — so the repo's usual triggering-id guard does not catch
it, and without the gate, opening Settings wrote the on value over a stored
off. Ordering makes the gate safe rather than lucky: once the tick has landed
the switch already holds the stored value, so the worst a late mount-fire can
write is the value that was there. Any future browser-local control on a page
layout has the same hazard.

**Accepted costs.** Browser persistence is per origin and is cleared with site
data. Both fail towards "celebrations came back", never towards silence, which
is why only the exact `"off"` value silences the family: a style name a later
build wrote, or a store this build cannot read, still celebrates. The layout
default is not a third cost: a `dcc.Store` writes it to storage only when
nothing is stored yet and otherwise takes the stored value, so changing the
default later resets nobody's setting. That is the opposite of Dash
`persistence`, which keys the stored value on the layout default and drops it
when that default moves (the
[2026-08-20 point-customization entry](#2026-08-20-run-points-get-a-size-preset-and-a-color-and-the-chart-stops-there)
records the controls that pay it), and the distinction matters when the
follow-up changes the default style. One more, inherited rather
than introduced: `message_queue` is process-wide and each drain's payload
reaches one client, so with two tabs open a batch lands in whichever drain
runs first. That is the single-consumer shape the page's drain already had,
and the supported usage model stays one active tab.

**Preview, and the styles that follow.** Preview plays the currently selected
style through the same clientside path a real celebration takes, so it obeys
the reduced-motion guard; it shows no toast, because the toast reports a run
and there is no run. It ships in version one because it is the only way to see
the effect without setting a personal best. The follow-up converted the switch
to a select over Off, Confetti, Fireworks, Cannons, and Stars — curated
presets only, no duration, particle, or color knobs, no custom style, and no
Random option. Since the proposal file is deleted, its specification of that
step is recorded here: Confetti is the upstream Realistic Look recipe
unchanged (five bursts from one origin, about 200 particles, about three
seconds); Fireworks is the upstream Fireworks recipe cut from 15 s to about
3 s; Cannons is School Pride cut to about 2.5 s with the app's accent colors
in place of the demo's red and white; Stars is the upstream Stars recipe
unchanged (three volleys, star and circle shapes, no gravity). Snow is
ambient rather than a celebration and is excluded. `confetti.reset()` clears
particles but does not stop a `setInterval` or animation-frame loop, so the
two loop-based recipes must not be taken from the demo verbatim — each style
is bounded to about three seconds and must cancel cleanly.

**What that step settled when it shipped.** Cancellation is centralized rather
than repeated per style: every style returns a cancel closure, the animation
module holds exactly one, and it is invoked before any new play. That way a
style's whole leak surface is its own one-line closure, and a style that
schedules nothing returns nothing. Cannons uses Mantine's primary blue
(`#228be6`, the filled-button color) and white, which is the reading of "the
app's accent colors" this repository can point at. Preview is `disabled` while
Off is selected, replacing the earlier behavior of a click that produced
nothing: the section applies instantly, so the committed value is the only
sensible preview target, and previewing a merely highlighted option would be a
different product. A Python test parses the animation's style registry and
asserts it matches the select's options, because a name offered with no entry
falls back to Confetti — a wrong answer rather than a visible failure. A
JavaScript test harness was considered again here and again declined; the
centralized cancellation is what shrinks the surface one would have covered.

Shipped in PR #268, and the style select in #272; ruled on #248.

## 2026-09-01: Configured Ports And Poll Intervals Are Bounded At Load

Status: Accepted

A port a machine could never serve, such as 70000, used to get all the way to
the socket and fail with a raw Python traceback. It now fails as the
configuration file is read, with one line naming that file and exit code 1.
The accepted range is 1 through 65535, and the poll interval must be between 1
and the largest delay a browser timer can hold. The example configuration file
states both rules beside the settings they govern.

Provenance: retires the "Out-of-range port crashes with a raw traceback" entry
adopted into `docs/tech_debt.md` from the 2026-08-12 engineering audit corpus
(PR #258); fixed in PR #266.

**The bounds.** `ConfigData.port` is `Annotated[int, Field(ge=1, le=65535)]`
and `polling_interval` is `Annotated[int, Field(gt=0, le=2_147_483_647)]`, both
shaped like the `kovaaks_api_timeout_seconds` bound that preceded them. Nothing
else in `ConfigData` gained a constraint: `sens_round_decimal_places` and the
cache TTLs stay unbounded, deliberately. The scope is these two fields, so a
bad `host` keeps its own later, differently-worded failure at the bind rather
than joining this exit.

**Why validation, not a bind-path fix.** An unbounded `port` reached
`sock.bind()`, which raises `OverflowError` ("bind(): port must be 0-65535")
rather than `OSError`, so neither `_bind_face`'s `except OSError` nor
`bind_server_socket`'s errno-classifying one caught it. Bounding the field
turns the same input into a `ValidationError`, which `main()`'s existing
configuration handler already converts into the curated "Configuration error:
could not load `<path>` -- copy example.toml to config.toml." exit. The
collapsed one-message design is unchanged: the ranges are stated in
`example.toml`, where the user is already looking when they edit the setting.

**Why configured `0` is refused.** Port `0` is valid to the socket layer and
still supported there: `bind_server_socket(0)` asks the OS for a free port and
is unchanged, which direct callers and the socket tests rely on. It is not a
usable configured endpoint, though, because the installed launcher reads the
configured port before startup (`Get-ConfiguredEndpoint`), polls
`http://<probe>:<port>/health` on that exact port to decide the app is ready,
and opens the browser on it. An OS-chosen port is one the launcher cannot
discover, so the app would serve while the launcher declared a readiness
timeout.

**Why `polling_interval` is bounded at both ends.** The value is handed
straight to `window.setInterval` -- Dash 4.4.1's Interval calls
`setInterval(this.reportInterval, props.interval)` with no clamping -- and that
delay is a signed 32-bit int. Both ends of the range therefore produce the same
silent request flood: a non-positive period, and one above `2147483647`, which
overflows and fires immediately. Measured in Chromium, `2147483647` never
fired and `2147483648` fired at 0 ms.

The upper bound is browser representability, not a product cap. A *product*
cap -- one tight enough to keep the run-event freshness window small -- stays
rejected on the PB-celebration proposal's reasoning: that window already
absorbs an arbitrarily slow poll by adding the configured period to its cap,
and a tight cap would refuse config files that load today for the sake of a
toast. `2147483647` ms is about 24.8 days, so it refuses only values the
browser could not have honoured anyway.

## 2026-08-31: Repeatable Toasts Replace In Place With A Visible Re-Entry

Status: Accepted

Every toast that answers one thing you did now replaces its own previous copy
with a visible re-entry, instead of stacking a duplicate or being dropped in
silence. Importing a second playlist while the first import's toast was still up
used to show nothing at all; both toasts now stand, because reports about
different playlists are different toasts. A retry of the same action pops its
answer back onto the screen with a fresh eight seconds, and a success clears the
failure message it answers. The one deliberate exception is the background
report that folds several unreadable run files into a single message, which
keeps batching exactly as it did.

Provenance: distilled from `docs/toast_policy_proposal.md` (three decisions
ratified 2026-08-30), committed in PR #257 and deleted in this shipping PR --
git history holds the full text, including the design-system and UX survey the
policy rests on and the live POC that measured the mechanism.

**The policy.** Every toast is classified before it is written, by two
questions. First: can the reported fact recur inside one toast lifetime, judged
against the complete supported workflow *including inverse actions that make
the same subject eligible again*? A fact that cannot recur is an **event
toast** -- unique id per emission, plain `show`, occurrences stack, no registry
wiring. A fact that can recur is a **channel**. Applying that test to today's
inventory leaves the event bucket empty: every current toast's fact can recur
through some supported cycle, so the rule exists to classify future toasts, and
any claim that a fact cannot recur must survive the inverse-action check
(delete-then-re-import defeats the naive claim for import success).

Second: what is the channel's identity? Identity follows the semantic lane. An
operation's **problem lane** is one channel: its mutually exclusive outcome
flavors (a red hard failure, a yellow served-stale) share one key with a
differing payload, so two contradictory claims about the same latest attempt can
never be on screen together. **Success lanes** and **standing-condition lanes**
are their own channels, keyed by subject when independent subjects can be in
flight at once -- one success channel per scenario, one per playlist code. The
mutual-exclusion clause is deliberately problem-lane-only: success flavors of
one operation (a green full success, an orange partial one) may keep distinct
channels, accepting the narrow cross-flavor window a re-attempt can open. Lanes
interact only through explicit **cross-clears**: a success hides its operation's
problem channel and any standing-condition channel it falsifies.

A third pattern survives untouched: a **burst toast** folds many same-type
events into one summary carrying a count and points at where the individual
events are recorded. And persistence (`auto_close=False`, process- or
session-gated) stays orthogonal to all three.

**The mechanism: hide-and-reshow.** A channel emission shows a *fresh instance
id* -- the logical channel key plus a per-emission unique suffix -- and lists
the channel's previous instance id, plus any cross-clear targets' current ids,
in the container's separate `hideNotifications` prop. Why a new id: DMC 2.8.0
ignores a `show` whose id is already on screen, so a stable id answers a retry
with nothing. Why the pairing works in one response: the container declares its
hide effect *after* its send effect, so the fresh instance enters with the full
animation while the outgoing one animates out. The POC measured the result on
2026-08-29 against the installed DMC (harness under
`ignore/scripts/toast_hide_reshow_poc/`, findings on PR #257): first paint about
31 ms after the click, a ~135 ms entry slide, a ~250 ms crossfade with
complementary opacities that reads as replacement rather than as two toasts,
and a structurally fresh ~8.0 s lifetime even when replacing at 7.5 s. Hiding an
absent or already-closed id is a clean no-op with a clean console. Accepted
cosmetics: a toast that arrived as a replacement auto-closes without its own
exit fade, and bystander toasts bounce upward for roughly 280 ms during a
replacement.

**The registry.** The store beside the container is now
`toast-channel-registry`: a dict mapping each logical channel key to its current
instance id, read as `State` and written as an `allow_duplicate` `Output` by
every emitting callback. It sits in the app shell, not a page layout, for the
reason the counter it replaces did: a toast outlives the page that emitted it,
and a page-scoped store would reset on navigation and leave a visible toast with
no id to replace it by. **Writes are per-key `dash.Patch` assignments, never
whole-dict replacements.** This is load-bearing, not tidiness: a response that
rewrote the whole dict would carry a stale value for every channel it did not
emit, so two responses landing out of order could resurrect an obsolete instance
id -- leaving two toasts of one channel on screen, or a problem toast beside the
success that cleared it. What remains is only same-operation concurrency, which
the renderer covers rather than loading guards: every channel has exactly one
producing callback, and Dash 4.4.1 marks an older in-flight invocation with the
same output set outdated and discards its response.

**The conversions (13).** Subject-keyed channels, keyed by the canonical stored
code and never the pasted input: `imported-playlist-successful-{code}`,
`imported-playlist-visibility-failed-{code}`,
`deleted-playlist-successful-{code}`, plus `rank-refresh-success-{scenario}`
keyed by the scenario name verbatim (toast ids are internal, never parsed apart
and never rendered, so identity is the stable collision-free derivation and a
hash would only add a collision it cannot have). Single-identity channels: the
three per-action failure toasts, the two refusals, the constant-copy cleanup
success, and username-unset, whose uuid suffix goes. `rank-refresh-failed` and
`rank-refresh-stale` merge into one `rank-refresh-problem` channel whose payload
carries the red or yellow outcome. `run-verdict` rides the same helper.
Cross-clears: each import outcome clears the import failure, delete success
clears delete failure, cleanup success clears cleanup failure, and refresh
success clears both the problem channel and username-unset. No user-facing
string is added or edited; titles, messages, colors, and icons carry over
verbatim.

**Both upsert helpers are deleted.** With every channel on hide-and-reshow,
the `update`-plus-`show` pair with its alternating 8000/8001 ms durations
existed for one toast only, so `run-verdict` migrates and the trick goes with
its sequence store. The ratified run-verdict contract is preserved -- one run,
one toast, the newest verdict replacing what is on screen with a full lifetime,
per browser client and across navigation -- with one qualifier: during the
~250 ms replacement crossfade the outgoing instance is still animating out, and
each new verdict now re-enters with the pop animation instead of morphing in
place. `upsert_sticky_toast` goes with it, because `channel_toast` carries the
payload's `autoClose` through untouched instead of stamping a lifetime, which
is the only thing the sticky sibling existed to avoid.

**The personal best celebration is reconciled onto this policy.** PR #261
landed the `pb-celebration` toast through `upsert_sticky_toast` while this
proposal was still under review, so it arrived as the one family the standing
rule had not been applied to. It is a channel by the classifier -- a second
personal best inside one lifetime is plainly reachable -- so it moves to
`channel_toast` as a **persistent channel**: its own key, still distinct from
`run-verdict`, a fresh rendered instance per celebration, the previous instance
hidden with it, and `auto_close=False` passed at its builder so it still stays
until dismissed. Its ratified product contract is untouched: a dedicated lane
that an ordinary run verdict lands beside rather than replacing, the newest
celebration replacing the previous one, and no lifetime. What changes is only
the mechanism, and one visible detail that follows from it -- a second personal
best now re-enters with the pop animation instead of morphing in place, which
is the same visible re-entry every other channel gets and the reason it is
wanted. This is a mechanism conformance change, not new celebration scope; the
in-flight personal best celebration proposal is updated in step.

**What this supersedes.** The
[2026-08-03 notification-layer entry](#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)
loses three clauses: its per-click-id exception to the stable-id rule (the green
refresh confirmation and, via the 2026-08-09 entry, the blue unset-username
notice are now subject-keyed and single-identity channels, so nothing needs a
per-click id), its rationale for keeping the two refresh-failure outcomes under
distinct ids (they are one channel now, which is what stops them contradicting
each other), and the absolute reading of "at most one run-verdict toast is
visible at a time" (true once a response has been applied, with the crossfade
qualifier above). Its "`hide` cannot substitute" note stands as written and is
exactly why this works: the hide effect running *after* the send effect is what
lets a differing id pair show-and-hide in one response. The
[2026-08-09 unset-username entry](#2026-08-09-an-unset-username-is-stated-in-place-never-reported-as-a-failure)
loses only its per-click-id mechanism; its ruling -- that an unset username is
configuration state answered blue, never a red failure -- is untouched.

**Deliberately out of scope.** `run-import-failure` keeps its own cross-tick
swallowing: a second batch inside 8 s is dropped. It is a background burst
channel where anti-flood wins, its folded copy already points at `debug.log`,
and no user report exists; if it ever surfaces, the fix is a replacement
channel, not uuids. The research's broader position that error toasts should be
banners or inline messages is a much larger re-platforming question, deliberately
not opened. Mantine's visible-toast `limit` and queueing defaults stay untouched
as the flood backstop.

## 2026-08-30: One Severity Color Language For Inline Notices

Status: Accepted (the orange rung widened by
[2026-09-19](#2026-09-19-a-clicked-refresh-re-reads-the-leaderboard-total) from
a failed follow-up write to any failed follow-up step)

The app's inline notices each picked their own look, so the surfaces that most
needed attention were the faintest things on the page. They now speak the same
severity colors the toasts already do, and every one of them carries a leading
icon. The first-run setup card is tinted like the rest instead of being a white
card on a white page, and the leftover-playlist-files notice became a plain
panel so screen readers are no longer told that a panel of buttons is an alert.
No wording changed anywhere.

Decision: one severity scale governs every notification surface, inline and
toast alike. Blue is informational and any action it offers is optional; yellow
is caution, an attention-worthy negative outcome or a state that needs the user
without anything having failed; red is an error, an operation that failed;
green is a positive outcome; orange is partial success, where the action
committed but a follow-up write did not. Green and orange stay toast-only:
no inline success or split-outcome panel exists, and none is added. Yellow
deliberately spans both configuration states and coaching outcomes such as a
below-threshold run, because a narrower warning-only reading would leave the
shipped threshold verdicts outside the scale.

Why: the severity information already existed in the code and did not reach the
eye. Three of the four alerts were `color="yellow"` with Mantine's `light`
variant, whose yellow tint is the palest token in the palette and reads as
near-white in light mode, and none of them had an icon; the fourth hard-coded
`#ff6b6b`, a red tint on a purely informational banner. The setup card, the
first notice a fresh install ever shows, was an untinted `dmc.Paper` on the
untinted page body. In a live render the icon, not the background, was the
dominant legibility fix.

The component rule: which component a notice uses follows its content model,
not its look. Mantine renders `Alert`'s root with `role="alert"` and the dmc
2.8.0 wrapper exposes no role override. Per
[WAI-ARIA 1.2](https://www.w3.org/TR/wai-aria-1.2/#alert) that role is an
assertive, atomic live region for important, usually time-sensitive messages,
and [MDN's guidance](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Roles/alert_role)
draws the consequences this rule applies: the role is for text content rather
than interactive elements like links or buttons, and for content that appears
dynamically rather than with the page. So a text-only notice may be a
`dmc.Alert`, and a notice holding interactive controls is a `dmc.Paper` wearing
the alert anatomy through the shared `.alert-panel` classes in
`assets/stylesheet.css`. Should an interactive notice ever need announcing, the
shape is a separate polite status message, or an alert dialog for a workflow
that requires a response, never `role="alert"` around controls.

The five inline surfaces as shipped: the Settings store alert and the Playlists
visibility alert stay yellow `dmc.Alert`s and gain
`material-symbols:warning-outline`; the Aim Training Journey work-in-progress
banner becomes blue with `material-symbols:info-outline`, deleting the hex; the
Playlists leftover-files notice becomes a blue `dmc.Paper`, keeping its id, its
callbacks, and its hidden-class reveal; the Home setup card keeps its
`dmc.Paper` and takes the blue treatment for the identity offer and the yellow
one for the blocking stats-folder state, with the matching icon beside its
title. Both icons were already vendored, so no assets were added. Mantine
defines the `-light` tokens per color scheme, so dark mode needs no separate
rules.

Superseded in part by the
[2026-09-15 setup-hints entry](#2026-09-15-setup-hints-wear-the-notice-anatomy):
that sweep enumerated the notices by component and so never saw the three
plain-text messages about setup, which now wear the same anatomy. The
enumeration above is the five as shipped that day; there are seven, and the
two added carry no title. Everything else here stands, the scale included.

Rejected: one accent color for every inline notice, which is calmer and uniform
but makes "your saved choices are silently not applying" look identical to an
FYI and splits the app into two color vocabularies, one for toasts and another
for panels. Rejected for the setup card: one color for both states, which hides
that the first state blocks every plot on the page while the second is a
skippable offer. Rejected for the leftover-files notice: yellow, which keeps
housekeeping louder than the problem warrants and dilutes the two yellow alerts
that earn it. Rejected as variants: `filled`, far too loud for a persistent
panel and poorly contrasted in yellow, and `outline` or `default`, both whiter
than what shipped before. Rejected as a component: rebuilding the setup card as
a `dmc.Alert`, which would entrench the role mislabel permanently rather than
merely start from the wrong place. The `dmc.Paper` anatomy carries one ongoing
cost, accepted knowingly: it tracks Mantine's `Alert` look by hand across
upgrades.

Extends the toast layer specified by the
[2026-08-03 notification entry](#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy),
which stays authoritative for toasts, including their white-card-with-icon
anatomy: an icon suppresses Mantine's colored side bar, so a toast's color is a
circle rather than a stripe, and nothing here changes that. Orange keeps the
meaning the
[2026-08-02 committed-side-effect entry](#2026-08-02-a-committed-side-effect-reports-its-outcome-even-when-a-later-write-fails)
gave it and stays a distinct severity rather than folding into yellow.

Deferred: strengthening the pale yellow tint with a scoped CSS override. The
icons are expected to be enough, and the override is a one-line follow-up if
they are not.

## 2026-08-22: The Playlist Fill Reports Degradation In Place Only

Status: Accepted

Opening a playlist used to end a degraded position update with a red or
yellow toast that repeated a count the page's own status line already showed.
The toast is gone. The status line above the grid, beside the filter box, is
now the only place the fill reports that positions were unavailable or served
from cache, and a clean fill still clears it and stays silent. Nothing else about the update
changes.

Decision: the progressive fill on `/playlists/<code>` states degradation in
its status line and emits no notification. `_fill_summary_notification` and
the `notification-container.sendNotifications` output of
`drain_playlist_scenario_rows` (`source/pages/playlist_scenarios.py`) are
deleted; the callback returns the row transaction and the status only. The
status copy is unchanged, and `tests/test_playlist_pages.py` guards the
callback's declared outputs so the toast cannot return unnoticed.

Why: the toast was non-conformant against the
[2026-08-03 routing policy](#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy).
A degraded fill is an automatic failure during passive navigation, which that
entry routes to in-place state with no toast, and its second litmus — already
visible somewhere? then nothing — is answered by the status line, which
carries the same counts ("1 of 3 positions unavailable · 1 from cache —
KovaaK's unreachable") in the filter row directly above the grid the user is
already reading.

Rejected: ratifying the toast as a third named exception to the
persistent-condition rule, beside the Steam-ID mismatch and the startup
playlist warnings. Both of those earn their exception by having no in-place
home; this fill has one, on screen, in the reader's line of sight. The
exception would be defensible only if the status line were easy to miss, and
it is not. Ratifying it would also have made "the policy names it" the test
for conformance rather than the litmus tests themselves.

Supersedes, in part, the
[2026-07-15 progressive-fill entry](#2026-07-15-stream-playlist-positions-with-generation-scoped-progressive-fill):
its completion-toast clauses only — the first terminal tick no longer "emits
any aggregate completion toast", and "Completion uses the existing
red/yellow/silent failure tiers" no longer describes a notification. The two
phases, the generation-scoped row identity, the cancel-on-start rule, the
tombstone retention and eviction order, the pending-flag rules, the outcome
counting, and the status settling are all unchanged and remain Accepted.

Discharges, for the playlist page only, one half of what the
[2026-08-09 unset-username entry](#2026-08-09-an-unset-username-is-stated-in-place-never-reported-as-a-failure)
left open. That entry deferred the configured-but-wrong-username case,
noting it "still produces both generic red toasts today". A wrong username
resolves every position to `UNKNOWN`, so the aggregate toast was the
playlist page's half, and deleting it settles that surface: the fill reports
the count in place, like any other degradation.

The other half stands, and this entry rules nothing on it. Clicking Refresh
on Scenario Performance with a wrong username still answers with the generic
red "Position refresh failed" toast, and correctly so — a manual Refresh is a
user-initiated failure, which the routing policy toasts. Neither surface
diagnoses the wrong username: the playlist status line says positions are
unavailable, not why. Naming the condition is still the open question, and a
typed reason on `ScenarioRankInfo` is still where it should be
reconsidered.

Consequences: the app has one fewer toast id, and the notifications
inventory in [specs/notifications.md](specs/notifications.md#inventory)
loses its `playlist-progressive-fill-{generation}` row. The fill's
background-thread channel is untouched — it still streams rows into the
registry an interval callback drains, which was never a notification path.

**Superseded in part, for copy (2026-09-14).** The status line quoted above
chains its fragments with middle dots only: "1 of 3 positions unavailable · 1
from cache · KovaaK's unreachable", and "{m} of {total} positions from cache ·
KovaaK's unreachable". The in-place-only decision is unchanged. See [App Copy Follows One Set Of Rules, And The Em Dash Is Gated Out](#2026-09-14-app-copy-follows-one-set-of-rules-and-the-em-dash-is-gated-out).

## 2026-08-22: The Capability Spec Layer Is Written In One Pass

Status: Accepted

Every shipped capability with a durable behavior contract must have a spec
that states what the app does today, and the four still missing are being
written in one deliberate pass instead of waiting for a change to touch each
capability. A new capability brings its spec in the PR that ships it, and a
change to specified behavior updates the spec in the same PR. The specs are
how a reader finds the decision behind a behavior, so the log still keeps no
topic index.

Decision: the "do not backfill specs ahead of need" rule in `AGENTS.md` is
replaced by a standing criterion — **every shipped capability with a durable
behavior contract must have a spec under `docs/specs/`**. A new capability
gets its spec in the shipping PR; a PR that changes specified behavior
updates the spec in the same PR (the "Shipping a proposal" checklist's step 2
now says the same thing). The criterion is a requirement, not a description
of the tree: when this entry landed the directory held two specs, and the
four the pass names below are in flight as their own PRs, so the layer is
complete only once those merge. The `AGENTS.md` "Scenario Rank Feature"
pointer becomes a
"Capability Specs" section pointing at the directory, which lists itself, so
no per-spec list is touched by every spec PR; `architecture.md`'s "Where to
look first" table carries the same pointer.

The pass: five specs, five PRs, each authored by a Fable session and reviewed
by a fresh Fable session plus Codex, in dependency order —

- `notifications.md` (PR #249; also carries this entry and the rule change),
- `settings.md` (after notifications: its in-place statuses cite the routing
  policy),
- `scenario_performance.md` (after settings: the Chart options switches'
  gating semantics live in the notifications spec, their placement and
  persistence here),
- `playlists.md` and `release_and_install.md`, independent of the others and
  of each other.

Deliberately excluded: app copy, which the app messaging consistency
proposal (PR #247) leaves out of the spec layer; bug-report intake,
which one decision-log entry covers in full; Home as a standalone capability,
folded into `scenario_performance.md`; and tooling and process, for which
`AGENTS.md` is the spec.

The spec contract, which every file in the pass follows and later specs
inherit:

- Statement form, present tense, no rationale. Each statement links the
  decision-log entry that governs it by heading anchor; a statement with no
  governing entry is an implementation fact, stays unlinked, and is covered
  by the preamble's disclaimer — no entry is invented for it.
- Verified against code or a test before it is written, never transcribed
  from the log. The PR body carries the evidence map; the spec does not.
- Where code contradicts an entry, the spec states what the code does and
  the PR body lists the contradiction as a finding for the maintainer. No
  code changes ride in a spec PR.
- Supersession is cited as current: the governing entry, or the surviving
  clause "as amended by" the amending entry; a superseded clause is never
  cited as current.
- Opens with a layer-1 summary held to the 2–4 sentence budget, then H2
  sections. No `Status:` line; anchors as GitHub slugs them
  (`tests/test_docs.py` validates both).
- App strings are quoted exactly as the code has them, shipped em dashes
  included. Specs link `architecture.md` and `product.md` rather than
  restating them, and link another spec only to say a rule lives there.

Consequences: the
[2026-08-01 doc-style follow-up entry](#2026-08-01-doc-style-follow-up--decisions-needed-roadmap-trim-no-log-index)'s
"revisit a log index only if findability still hurts after specs land"
loop closes when the pass's last PR merges — the specs are the findability
fix, and a topic index stays rejected; until then the loop is open only in
the sense that the fix is still landing. `docs/product.md` and
`docs/roadmap.md` are untouched: nothing user-facing changes.

## 2026-08-21: The Empty Point Color Is Called Default, And The Points Follow The Theme

Status: Accepted

The Point color field's empty state now reads Default instead of Automatic,
and its reset button reads Use default. Automatic suggested a Manual mode that
never existed, and Default is the word the Point size control beside it
already uses. The run points with no color chosen used to be the same indigo
in both themes; they now take the theme's own blue, a little deeper in dark
mode. The small preview swatch beside an empty field used to be plain white;
it now shows the color the graph is using in the current theme.

Decision: the first change is copy only. The stored value is unchanged: an
empty `point-color` still means the generated color, under the same persisted
id, so nothing a browser already saved is discarded. `POINT_COLOR_AUTOMATIC`
became `POINT_COLOR_DEFAULT`, and the reset button's id `point-color-default`.

**The run points take the theme template's colorway.** The 2026-08-20 entry
says an empty color keeps whatever Plotly and the Mantine template give it.
Until now the Mantine template's colorway never reached the run points:
`px.scatter` writes the first colorway entry of Plotly's default template,
`#636efa`, into the trace's `marker.color` when the figure is generated, and
the `update_layout(template=...)` applied afterwards never overrides a
property the trace already sets, so the points were `#636efa` in both themes.
The generator now clears that baked color (`marker_color=None`), so the run
trace carries no color of its own and Plotly draws it in the first colorway
entry of whichever template the theme applies: `#228be6` (blue-6) under
`mantine_light`, `#1971c2` (blue-7) under `mantine_dark`. First entry because
the run trace is the figure's first trace; colorway assignment is by index in
Plotly, and that ordering is pinned by test. `plot_service.generated_point_color`
reads the same entry for a scheme, and is the single source for the preview.

**How the swatch shows it.** Mantine's `ColorInput` renders its preview as a
`ColorSwatch` whose color is the value when valid and a hardcoded `#fff`
otherwise, as an inline style. Home sets `--point-color-default-light` and
`--point-color-default-dark` on the field from `generated_point_color`, and
two stylesheet rules scoped to `.point-color-field:has(input:placeholder-shown)`
(the second under `:root[data-mantine-color-scheme="dark"]`) repaint the
swatch's color overlay from the active one with `!important`, the only way
past an inline style. A typed or picked color hides the placeholder, and the
rules with it, so Mantine's own preview of that color takes over. Alternatives
rejected: **keeping the baked `#636efa` and previewing it as a constant**,
which leaves the theme template decorative for the primary data mark;
**storing a hex as the layout value**, which moves a persisted default
(discarding stored values) and turns the generated color into a chosen one;
**replacing the preview through `leftSection`** with a swatch kept in sync by
a callback, a round trip per keystroke to do what two CSS rules do.

Not changed: the Average Score line, which `px.line` bakes in the same
`#636efa` and which now sits beside blue points. Clearing its color would hand
it the colorway's second entry (red) rather than the points' color. Ruled
2026-08-22: the line gets a user setting of its own in a later PR, not a
colorway change here.

**Superseded in part, for copy (2026-09-14).** The line this entry calls
Average Score is labelled "Average score" in the legend and its hover label.
The color decision is unchanged. See [App Copy Follows One Set Of Rules, And The Em Dash Is Gated Out](#2026-09-14-app-copy-follows-one-set-of-rules-and-the-em-dash-is-gated-out).

## 2026-08-21: Run Notifications Have A Master Switch, And The Threshold Switch Is Renamed

Status: Accepted

Run toasts can now be turned off. Chart options carries a Run Notifications
switch, on by default, and turning it off silences the toasts that report how
a run went while the chart keeps updating in the background. A run file that
fails to import still says so, and nothing else about the toasts changed. The
switch that used to be labelled "Score Threshold Notification" never gated
toasts at all, only whether a run was judged, so it is renamed "Score
Threshold Verdict" and its help text now says what it actually does.

Decision: a `dmc.Switch` with id `run-notification-switch`, `checked=True` and
`persistence=True`, in a new **Notifications** group at the end of the Chart
options inspector.

**What the switch gates.** All three shapes `_build_run_event_notification`
produces: the threshold verdict, the top-N placement, and the "While you were
away" catch-up digest. They share one toast id and one producing function, so
the gate is a single early return at the top of that function rather than a
check per shape. The digest is deliberately inside the gate: it is the same
family reporting the same events, and a digest that survived the off switch
would read as a bug rather than a feature. The catch-up case that survives it
is the planned run history, not a toast.

**What it does not gate.** The red run-import failure toast
(`run-import-failure`, its own interval callback) is error feedback rather
than run feedback and stays on; the master switch's help text names the three
shapes it covers instead of saying "all notifications", so it cannot be read
to promise otherwise. With the switch off the plot still updates, scenario
auto-switch still follows a new run, and the rank-refresh, Steam-mismatch, and
playlist toast families are untouched.

**The threshold switch is the verdict sub-toggle, not a second master.** Four
combinations, all defined: master off is silence whatever the threshold switch
says; master on with threshold on is the behavior that shipped in the
[notification redesign](#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy);
master on with threshold off is that redesign's judging-off behavior, meaning
placement toasts and neutral digests only. Its id, default, and persistence
are unchanged — renaming the id would orphan every value a browser has already
stored under it — so only its label, its help text, and the dated code comment
beside it move. That comment, and the "knowingly imprecise" consequence
recorded in the
[Chart options rename entry](#2026-08-09-the-graph-page-is-scenario-performance-its-panel-is-chart-options),
are resolved here: this is the later copy pass that entry deferred, for the
two strings it touches and no others.

**`State`, not `Input`.** The switch's value matters only when
`run-events.data` triggers `generate_graph`. Wired as an `Input` it would
rebuild the plot and reread the scenario's runs every time someone flipped a
notification preference. The existing threshold switch has the same
State-worthy property but stays an `Input`; changing it is a behavior change
with its own review.

**Storage is browser-local Dash persistence**, like every other Chart options
control. `data/settings.json` was rejected: it is scoped to the stats
directory and the KovaaK's identity behind a Save model, which is the wrong
interaction for a switch that should take effect the moment it is flipped.
`config.toml` was rejected: it holds human-owned boot facts.

Rejected alternatives:

- **The digest surviving the off switch.** It would preserve a rare catch-up
  toast at the price of a switch that is not quite off.
- **Per-family toggles** for import failures or rank-refresh feedback. Each of
  those is error or action feedback, and nothing asked for them.
- **App-wide notification production**, deliberately deferred rather than
  dropped. Run toasts are produced only on Scenario Performance because the
  producing interval, store, and preferences are mounted in that page's
  layout. Making production app-wide is a redesign of the queue-to-UI flow
  with its own product questions, and this change forecloses none of it: the
  guard sits at toast production wherever that later runs, and Dash
  persistence survives a same-id component move.

**Superseded in part (2026-09-02).** The catch-up digest above no longer
exists, so the gate covers the threshold verdict and the placement alone, and
the help text gained a second sentence naming the celebration's own setting.
The last rejected alternative's deferral of the queue-to-UI redesign also
falls, for the drain alone; the product question it protected, app-wide
verdict toasts, stays deferred. Both are recorded in
[A New Personal Best Celebrates On Every Page](#2026-09-02-a-new-personal-best-celebrates-on-every-page).

**Superseded in part, for copy (2026-09-14).** The two control names this
entry sets are sentence case: "Run notifications" and "Score threshold
verdict". The verdict switch's help text names the master switch in bold,
"Needs **Run notifications** turned on." What each switch gates is unchanged.
See [App Copy Follows One Set Of Rules, And The Em Dash Is Gated Out](#2026-09-14-app-copy-follows-one-set-of-rules-and-the-em-dash-is-gated-out).

Shipped in PR #245; design discussion in #240. Distilled from
`docs/run_notifications_switch_proposal.md`, now deleted.

## 2026-08-21: Release Integrity Rests On GitHub Digests And An Enforced Archive Contract

Status: Accepted

The first thing a new visitor asks about a downloadable Windows app is whether
it is safe to run, and the release page is where that gets answered. This
project relies on the SHA-256 digest GitHub publishes for every uploaded asset,
together with releases that can never be changed, rather than shipping a
checksum file of its own. The release page now opens with a short header saying
what those guarantees are and which download to take, and CI now proves
byte-for-byte that the uploaded assets are the ones it built. The release zip
also stopped carrying development-only files that an installed copy cannot use,
and a new pre-publish check fails the draft if the zip ever loses a file an
install needs.

Decision: no custom `SHA256SUMS.txt`, no hash duplicated into the release
notes, and no launcher-side hash verification at launch. Integrity rests on
GitHub's per-asset digests plus immutable releases, which this repo already has
enabled — see
[Releases And Their Assets Are Immutable](#2026-07-19-releases-and-their-assets-are-immutable),
which this entry extends rather than restates. Alongside that: the release page
gets a curated header, `.gitattributes` prunes development-only trees from the
archive, and `validate_release` enforces an archive contents contract before
publication.

Why: at this audience size the marginal security of a project-published hash
over a platform-published one is zero, and both are downloaded over the same
HTTPS connection from the same host. GitHub's digests are visible on the
release page, are computed by GitHub on receipt, and cannot change afterward
because the release is immutable. Both of our assets additionally carry a
GitHub-signed release attestation, retrievable at
`repos/.../attestations/sha256:<digest>` — supporting evidence for this
decision, deliberately not surfaced in user-facing copy, because attestation
commands are not something a general user should be asked to run.

Rejected alternatives:

- **A custom `SHA256SUMS.txt` asset.** Redundant with digests GitHub already
  publishes and signs, and it would be permanent release machinery — generated,
  validated, and maintained on every release — bought for no added security.
  It also invites the copy failure this entry avoids: a hash pasted into the
  notes reads as proof of trustworthiness rather than of byte integrity.
- **Launcher-side hash verification at launch.** It touches the frozen update
  contract, the named-asset/source-archive fallback, and failure behavior all
  at once. The launcher already validates `release.json`'s identity fields and
  health-gates promotion on the SHA carried in `version.txt`, so the marginal
  gain is small. Deferred until evidence demands it, consistent with the
  deferral already recorded in the 2026-07-19 immutability entry.

Consequences and constraints:

- **Digests cover uploaded assets only.** Every release page also shows
  GitHub's auto-generated "Source code (zip / tar.gz)" downloads, which have no
  digest. Copy must never claim digests for "every download", and must never
  say "verified safe" or "secure download" — a digest proves byte integrity,
  not trustworthiness.
- **The archive is a contract, and it is enforced.** `validate_release` rejects
  the draft unless the zip carries every entry in `REQUIRED_ARCHIVE_ENTRIES`
  and none of `EXCLUDED_ARCHIVE_TREES`. The required set covers installation,
  runtime, legal, and self-documentation needs rather than only files read by
  code, and it is deliberately not a snapshot of the whole tree: each entry is
  listed with what reads it. Without this, a `.gitattributes` edit or a file
  move that drops an install-critical path is undetected until someone's
  install fails, and immutability makes the bad asset permanent.
- **Name the file when something opens it by name.** A directory entry in the
  required set only asserts that the tree holds at least one file, so it still
  passes after the one member that mattered is renamed away. Required
  individually for that reason: `source/app.py`, `scripts/launch_bootstrap.ps1`,
  and `scripts/launcher.ps1`, which the launcher, the installer, and the
  bootstrap each open by name and abort without; and `docs/example.png`,
  `docs/architecture.md`, `docs/product.md`, and `docs/roadmap.md`, which are
  every relative target the shipped README opens. A test cross-checks that
  README target set against the contract, so a new link into `docs/` cannot
  quietly fall outside it. Only `assets/` and `resources/` remain directory
  entries, where no single member is the dependency.
- **A tree holding only its own directory entry is empty, not present.**
  `git archive` emits an entry for each directory, and a `/**` export-ignore
  rule leaves that entry behind after removing every file under it, so a
  prefix match alone would accept an empty required tree. The check requires a
  child path, and a regression test covers each required directory in that
  shape.
- **`export-ignore` is narrow, and `docs/` stays.** `/tests`, `/.idea`, and
  `/.github` are pruned. `docs/` ships because the shipped README embeds
  `docs/example.png` and links `docs/*.md`, so dropping it breaks the zip's own
  front page for the manual-install reader. `resources/`, `scripts/`,
  `install.ps1`, and `version.txt` must ship for the app, the installer, the
  launcher, and build identity respectively.
- **Use the anchored directory form.** Tested on git 2.55: `/tests`, `tests`,
  and `tests/` all prune the directory entirely, while `/tests/**` removes the
  files and leaves an empty `tests/` directory entry in the zip. The contract
  treats an empty excluded directory as still shipped, so the two rules agree.
- **`export-ignore` also prunes GitHub's source archive.** The
  `archive/<sha>.zip` download changes the same way. That is intended, and it
  matters because that archive is the launcher's documented fallback when the
  named asset is missing, and because the CI stamp job downloads it.
- **The digest check is a build-versus-upload comparison, not a size check.**
  It recomputes SHA-256 locally and requires equality, treats a null or missing
  digest as a failure rather than a skip, and requires the release to carry
  exactly the versioned zip and `release.json` — a resumed draft keeps any
  asset `--clobber` never replaced. It subsumes the size comparison it
  replaced.
- **Blocking a release and shipping a file are separate lists.**
  `_BLOCKED_DIRECTORIES` in `scripts/release_job.py` decides whether a push cuts
  a release; `.gitattributes` decides what the zip carries. `docs/` is on the
  first and not the second — see
  [PyCharm Config Stays Tracked And Its Upgrade Churn Is Committed Once](#2026-08-08-pycharm-config-stays-tracked-and-its-upgrade-churn-is-committed-once).

## 2026-08-21: The Launcher Narrates A Slow Start And Keeps Its 120-Second Ceiling

Status: Accepted

The launcher used to print one "Starting" line and then nothing while it
waited for the app, so a slow first start looked exactly like a hang. It now
stays quiet for the first few seconds and, if the app is still not up, prints
how many seconds have passed, repeating every few seconds until the app
answers or the wait gives up. A start that finishes quickly prints nothing
new. The two-minute limit on the wait is unchanged, on purpose.

Decision: the heartbeat lives inside `Wait-AppReady` in `scripts/launcher.ps1`,
so both call sites get it: the normal start and pending-update activation.
The output contract, ratified 2026-08-20 and shipped in PR #243:

- Ready before the ~5 s gate: nothing new. The fast path's console output is
  byte-identical to what it was before.
- Still waiting at the gate: `Still starting Corporate Serf Dashboard ... N
  seconds elapsed.`, then another line every ~5 s.
- Ready after at least one heartbeat: `Corporate Serf Dashboard is ready
  after N seconds.` No heartbeat shown means no completion line. The
  `exited` and `timeout` outcomes never print a completion line; their
  callers report the failure as before.
- The `Dashboard running at http://...` line is unchanged, and still prints
  on every successful launch by either startup path, once the app is ready.
  It was never reached on a failed start: a normal start that returns
  `timeout` or `exited` stops at `Stop-Fatal` before it.
- No reassurance or explanation sentences. The elapsed counter is the whole
  feature. Gate and interval are implementer-tunable around ~5 s; both are
  5 s today.

Why the gate is ~5 s: 14 installed starts measured 2026-08-20 on the
development machine ranged 0.12–5.62 s, median 2.18 s. The samples are
warm-biased and single-machine. A slow-but-healthy warm start may therefore
occasionally show a single heartbeat line; that is accepted, do not tune it
away. Why this copy: it echoes the launcher's own vocabulary ("Corporate Serf
Dashboard", the existing "Starting ... " lines). Never "the dashboard" for
the thing being started; a prior ruling found it reads as the browser.

The cadence is a floor, not a schedule. Loop granularity is an in-flight
health probe's two-second timeout plus the half-second sleep, so a heartbeat
can land up to ~2.5 s after its nominal time and the timeout outcome can
overshoot the ceiling by about as much. On a machine where a closed loopback
port is slow to refuse, every pre-listen probe burns its full timeout, which
is why the PR's transcripts show 7/12 s rather than 5/10 s. The probe itself
is unchanged. Its address stays governed by the
[2026-08-14 configurable-listen-address entry](#2026-08-14-the-listen-address-is-configurable-loopback-by-default):
`Get-ProbeAddress` sends a wildcard bind to its own family's loopback and
every other configured host to that host's literal URL form. The gate on
the full SHA and launch token, and process exit detected at the next loop
check rather than at the ceiling, are likewise unchanged.

Why `$HealthTimeoutSec` stays at 120: the ceiling's job is failure
declaration, and timeout is destructive. On the normal start the child is
killed and the launcher exits with a fatal "check config / reinstall"
message; on the update path the pending version is killed and the previous
one is started instead. A false timeout on a genuinely slow cold start turns
"slow" into "broken" on exactly the first-run path the heartbeat exists to
protect, and the warm-biased measurements above say nothing about the
cold-start tail. Revisit only with clean-machine cold-start evidence, and
then size the ceiling at two to three times the worst observed start.

Alternatives rejected: reassurance copy such as "the first start can take
longer" (words without information; the counter already says it), and
retuning the ceiling alongside the heartbeat (no evidence to size it, and
the failure mode of guessing low is the one described above).

## 2026-08-20: Run Points Get A Size Preset And A Color, And The Chart Stops There

Status: Accepted

The Scenario Performance chart now lets you change how the raw run points look:
a Small, Default, or Large point size, and a point color chosen from eight
curated swatches, a picker, or a typed hex value. Both live in a new **Run Data
Points** group in Chart options and persist in your browser like the overlays
beside them. Leaving the size on Default and the color empty keeps exactly the
chart the app drew before. Nothing else on the chart became customizable, and
that boundary is the decision as much as the two controls are.

Decision: the inspector gains one **Run Data Points** group between *Overlays*
and *Score Threshold*, holding a full-width `Small | Default | Large` segmented
control (`point-size`) and a `dmc.ColorInput` (`point-color`). Both carry
`persistence=True`, the same browser-local model as their siblings; nothing is
written to `data/settings.json` or `config.toml`. A **Use automatic** button
beside the color field is the reset.

**The product rule.** A chart control has to answer a recognizable user goal,
not expose a Plotly property. Size and color earn their place because two goals
are demonstrable: make the points easier to see, and pick a color that reads
better for you. The interface keeps three levels — a strong Automatic or
Default appearance for most users, a small set of controls for the primary data
marks, and nothing else until a real workflow demands it. The promotion rule
follows from that: reconsider opacity only if overlapping points are shown to
hide useful density, reconsider marker symbols only if the graph ever carries
multiple semantic point categories, and if a visual-object group would exceed
roughly three controls, revisit presets or design an advanced mode rather than
appending another property.

**Default is semantic, not a number.** Selecting Default leaves `marker.size`
completely unmodified rather than writing the pixel count the chart happens to
use today. Two consequences: the generated appearance and any future template
change flow through untouched, and the layout default of a persisted control
never has to move — changing one silently discards every value the browser
already stored under that id.

**Automatic is the empty value.** An empty `point-color` means Automatic and the
field says so through its placeholder. Cleared dmc inputs send `""`, never
`None`, so the guard is truthiness, never `is not None`. Hex is the only
accepted format, which keeps alpha out of the feature; anything unparseable
falls back to the generated color rather than erroring.

**The eight swatches, and how they were chosen.** One hex value has to work on
both real plot backgrounds — `#ffffff` light and `#242424` dark — so the shade
was selected per family against both, rather than taking one Mantine shade index
across the board. All eight clear 3:1 on both:

| Family | Hex | Light | Dark |
|---|---|---:|---:|
| blue-7 | `#1c7ed6` | 4.20:1 | 3.70:1 |
| cyan-8 | `#0c8599` | 4.35:1 | 3.57:1 |
| teal-8 | `#099268` | 3.95:1 | 3.93:1 |
| green-9 | `#2b8a3e` | 4.37:1 | 3.55:1 |
| orange-9 | `#d9480f` | 4.30:1 | 3.61:1 |
| red-7 | `#f03e3e` | 3.84:1 | 4.04:1 |
| grape-6 | `#be4bdb` | 4.02:1 | 3.86:1 |
| pink-6 | `#e64980` | 3.73:1 | 4.16:1 |

`swatchesPerRow` is set to 8 explicitly; the component's own default is 7, which
would strand the eighth swatch on a row of its own.

**The exclusions are v1 curation under the current themes, not permanent bans.**
Yellow is out because no Mantine yellow shade reaches 3:1 on both backgrounds.
Lime is out because green already covers that family and only its deepest shade
passes, so it would add a weakly differentiated choice. Gray is out because it
collides with the grid lines. Dark is out because it disappears against the dark
plot. Re-audit all four if the chart backgrounds change. Contrast was only an
eligibility screen — small rendered points were checked in both themes before
shipping — and an arbitrary custom color carries no such guarantee, which is why
the graph updates immediately and **Use automatic** is an obvious,
keyboard-reachable way back.

**Appearance applies after theming, and never touches `generate_graph`.** Both
controls are Inputs to `apply_graph_appearance` (formerly
`apply_light_dark_theme_to_graph`), which deserializes `cached-plot`, applies the
light or dark template, and only then calls
`plot_service.apply_point_appearance`. The expensive callback that writes
`cached-plot` keeps its inputs unchanged, so changing a size or a color cannot
reread scenario data, rebuild overlays, or fire a notification. That split is
asserted against the callback registry, not just documented. The raw-run trace is
selected **by name** (`RUN_DATA_POINT_TRACE_NAME`), never by index: placeholder
figures, empty-state figures, figures without a run trace, and any future
reordering fall back untouched, and *Average Score*, the overlays, the axes, and
the hover labels are never restyled. Both graph modes are covered by
construction, and preferences survive scenario switches.

Alternatives rejected: **improving the default for everyone** — a larger
universal marker or a size that adapts to point count — because no universal
default satisfies personal color preference, and adaptive sizing makes the same
data look different as its point count grows; rendered evidence may still improve
the Automatic size later, but a better default is not a substitute for
personalization. **Palette-only** (governable but weakens personalization) and
**picker-only** (flexible but makes everyone solve color selection from scratch
and hides the safe choices). **Five presets or a continuous slider**, which
elevate rendering precision into a product concept and make the default harder to
recognize and restore. **Ten swatches**, adding indigo-5 (`#5c7cfa`) and violet-5
(`#845ef7`): finer blue-to-purple choice at the cost of two more neighboring
options the picker already covers. **The 14-color DMC example list**, which is a
component demonstration rather than a palette curated for these backgrounds, and
several of whose values fail the contrast target.

Out of scope and staying there: opacity, marker symbols, borders and outlines,
Average Score line styling, rank/PB/threshold overlay styling, axes, grid lines,
fonts, plot backgrounds, hover-label styling, per-scenario or per-playlist
appearance profiles, import/export of appearance preferences, and any generic
Plotly-property editor.

Design in [#238](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/238),
implementation in [#241](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/241).
The panel this group joined is the
[2026-08-09 chart options entry](#2026-08-09-chart-options-live-in-a-collapsible-panel-beside-the-graph).
The Automatic wording, the generated color, and the empty field's white
preview swatch were revised the next day; see the
[2026-08-21 entry](#2026-08-21-the-empty-point-color-is-called-default-and-the-points-follow-the-theme).

**Superseded in part, for copy (2026-09-14).** The chart's legend entries are
"Run data point" and "Average score", so `RUN_DATA_POINT_TRACE_NAME`, the
handle this entry selects the run trace by, now holds "Run data point". The
point preferences are unchanged. See [App Copy Follows One Set Of Rules, And The Em Dash Is Gated Out](#2026-09-14-app-copy-follows-one-set-of-rules-and-the-em-dash-is-gated-out).

**Superseded in part (2026-10-05).** Point size now sizes the New PB stars on
the Score vs Time chart as well as the run points, so "Nothing else on the
chart became customizable" has one exception. The set of controls is
unchanged, Point color still restyles only the run trace, and the rest of this
entry stands. See [The Score vs Time Chart Marks Each New PB With A Star](#2026-10-05-the-score-vs-time-chart-marks-each-new-pb-with-a-star).

## 2026-08-14: The Listen Address Is Configurable, Loopback By Default

Status: Accepted

The app now reads a `host` setting from `config.toml`, and still serves this
machine only unless that setting says otherwise. Setting it to `0.0.0.0` lets
other devices on the same network open the dashboard, which is the only way to
reach it from a phone or a second PC. The app has no login, so every device
that can reach the chosen address can read the run data and change the
settings. An install that does not set `host` behaves exactly as it did
before.

Decision: `ConfigData` gains `host: str = "127.0.0.1"`, and both server paths
honor it — `bind_server_socket(port, host)` for the waitress path, and the
`config.debug` Flask path via `app.run(host=config.host, ...)`. On the default
host the bind is byte-for-byte the previous behavior: both loopback faces,
`SO_EXCLUSIVEADDRUSE`, two-bucket failure semantics. A non-default host is
bound **alone**, with no `::1` companion.

**`host` must be an IP literal**, never a name; the address family is taken
from the literal, so `::` binds as IPv6 rather than failing as a malformed
IPv4 address. Resolution is what makes a name dangerous here: it picks one
face of whatever it resolves to, so `localhost` would bind `::1` alone on
this machine and `127.0.0.1` alone where the resolver orders IPv4 first,
holding one loopback face and leaving the other free to squat — the very
ambiguity the default's dual-face bind exists to close, reintroduced through
the most natural spelling of "same as the default". The empty string is the
same trap in different clothing: `getaddrinfo("", ...)` yields `AF_INET6`, so
`host = ""` — the natural way to hand-write "unset" — would publish the app
on `::`, every IPv6 interface included, with none of the warnings that gate an
explicit `0.0.0.0`. Both exit naming the setting. This costs nothing the
documentation promised: `README.md`, `example.toml`, and this entry all
specify literals.

Why loopback remains the default: there is no authentication anywhere in the
app. Settings are writable from the UI, so a reachable instance is not
read-only exposure. Defaulting to the LAN would hand that to every device on
whatever network the machine joins next, including untrusted ones.

Why a non-default host is bound alone: the `::1` companion in the
[2026-07-19 exclusive-bind entry](#2026-07-19-the-app-binds-its-port-exclusively-and-exits-if-it-is-taken)
and its 2026-07-20 addendum exists to stop `localhost` resolving to a face the
app does not hold. A user naming one address outright has no such ambiguity to
close, and binding a speculative second address is not something a config
value should do silently.

Verified consequence of `0.0.0.0`: nothing answers on `::1`, so a client that
insists on IPv6 loopback is refused; `localhost` and `127.0.0.1` both connect,
because resolvers and browsers fall back to the IPv4 address.

**The launcher derives its addresses from `host`.** A fixed `127.0.0.1` probe
would have made a single-address bind unlaunchable from the installed
shortcut: no listener on `127.0.0.1` means `Wait-AppReady` times out and kills
a perfectly healthy server. `scripts/launcher.ps1` therefore reads `host`
alongside `port` — through the same "ask the app's own loader" contract, so
there is still no second TOML parser — and maps it to two destinations. The
`/health` probe stays resolver-free per the
[2026-08-09 entry](#2026-08-09-human-facing-urls-say-localhost-machine-probes-stay-on-127001):
`0.0.0.0` probes `127.0.0.1`, `::` probes `[::1]` (Windows sets
`IPV6_V6ONLY`, so the IPv6 wildcard serves no IPv4 face), and any other host
is probed at the literal address it names. The browser URL says `localhost`
only on the **default** host, where the app holds both loopback faces and
whichever one the resolver picks is therefore ours. Under any other host the
app owns at most one face and an unrelated process can hold the other:
verified on Windows, an app bound to `0.0.0.0` alongside a stranger holding
`::1` sends `localhost` to the stranger, after the launcher's own IPv4 health
check has already passed. Every non-default host therefore opens at the same
literal address the readiness probe proved reachable. IPv6 literals are
bracketed for both.

Failure taxonomy — two buckets, not three. A host that is not an IP literal is
rejected before any bind, naming the setting. A well-formed literal that no
local interface holds — a mistyped LAN address, or one lost to a DHCP change —
fails the bind with `EADDRNOTAVAIL`, and that reports the **host**, not the
port: no port is free on an address this machine does not have, so the
port-taken message would send the user after the wrong setting.

Relationship to prior entries: nothing is superseded. The exclusive-bind
decision stands unchanged — the app still creates and binds its own sockets,
still sets `SO_EXCLUSIVEADDRUSE`, and still exits rather than half-serving a
port. What changes is only which address it claims. The
[2026-08-09 human-facing-URL entry](#2026-08-09-human-facing-urls-say-localhost-machine-probes-stay-on-127001)
reasoning that "whichever face the resolver hands `localhost` is ours" is
narrowed to the default host, and holds there.

`debug` and `host` interact, and nothing enforces it. Flask sets
`use_debugger` from `debug` and Dash forwards `host` straight through, so
`debug = true` with a non-default host puts the PIN-gated Werkzeug console on
that network — an execution surface, not just the read-and-change-settings
ceiling the rest of this entry reasons about. The combination warns at startup
and is called out beside `debug` in `example.toml`, but is not refused:
`debug` is documented dev-only and both are the operator's own settings.
Refusing it outright stays available if that judgment turns out wrong.

Out of scope: authentication, TLS, and any in-app affordance for turning LAN
access on. On Windows a bind is also not sufficient by itself — an inbound
firewall rule is required, which is the operator's business and is documented
in `README.md` rather than automated.

## 2026-08-11: Durable JSON Stores Carry A schema_version Stamp

Status: Accepted

Every durable JSON store the app keeps now starts with `"schema_version": 1`,
so future data migrations can tell a format the app understands from one it
does not. A file the app cannot use is never deleted or rewritten behind the
user's back: it is left exactly as it is, the app falls back to its first-run
defaults, and the page that owns the setting says what happened and how to fix
it. A file written by a *newer* version of the app is recognized as newer: the
app reads nothing from it, refuses every write to it, and says the data is
intact and an update will restore it. Existing installs are converted once by
a script that ships with the release; the app itself has no migration code.

Decision: settled with the maintainer on 2026-08-10 and 2026-08-11, after a
review round on the contract. The premise is the public launch. `data/` is the
app's database in lieu of SQLite, and a format change with no version marker is
indistinguishable from corruption.

**Scope.** `data/settings.json`, `data/playlist_visibility.json`, and every
user playlist under `data/playlists/`. The bundled corpus in
`resources/benchmarks/` is exempt: it ships with the code that reads it and is
governed by its own `generated_from.schema_version` provenance contract, so its
format can never be older or newer than the build. Cache files under
`data/cache/` get no stamp and no cache-schema rule; that is deferred to a
need-time proposal. The tolerance invariant for caches (missing, stale,
malformed, partially-written files must all be survivable) is unchanged and
still stated in `AGENTS.md`; only the versioning and invalidation *mechanism*
is deferred, and the known tolerance violations in `api_service.py` are tracked
separately.

**The marker.** Top-level `"schema_version"`, an integer. Validation is strict:
`type(value) is int` — so a JSON `true`, which `isinstance` would accept as an
`int`, is rejected — and exact membership in the supported set (today `{1}`).

**No grandfather rule.** An existing well-formed file *without* a stamp is an
error state, not implicit v1. Two machines is a cheap population to convert
once, and the alternative is a missing-means-v1 special case that every future
reader carries forever.

**Four read states, per store**, implemented once in
`source/utilities/store_schema.py`:

1. *Missing* — first-run defaults (settings unset, visibility seed, empty
   user-playlist set). Unchanged from before the stamp existed.
2. *Error* — unreadable, not JSON, not an object, no stamp, a malformed or
   **non-positive** stamp (`0` and negatives are garbage, not the future: a
   file that read as future would refuse every write and strand the store), or
   a supported stamp whose payload fails that version's definition. The bytes
   are preserved, the store reads as its first-run default, and an actionable
   message is reported. A stamp routes a payload to a validator; it never
   vouches for the payload.
3. *Supported* — a known stamp with a payload that validates.
4. *Future* — a stamp above the highest supported version. Nothing is read, and
   every write is refused.

The error and future states surface in the UI, not only in the log: an inline
alert on the settings page (an unusable store otherwise renders as an ordinary
empty form, exactly like a first run) and an alert on the Playlists page for
visibility (whose fallback is the seed, which looks exactly like a fresh
install). Unusable playlist files are skipped with the existing startup warning
queue. Without those surfaces the migration window reads as unexplained data
loss instead of loud but inert.

**Write rules.** Automatic writers never touch a store they cannot use:
`bootstrap_stats_dir` declines out loud in the error and future states, because
those read as "no keys" and writing would erase an identity the user really
configured. User-initiated saves *own* an error-state file, so self-service
recovery from a bad hand edit stays possible: the incumbent is copied
byte-for-byte to an adjacent `<name>.corrupt-<n>.bak` (exclusive create, so a
backup never replaces an earlier backup; a copy, never a move, so a write that
never lands leaves the original at its path), and only then is the file
replaced. If the copy cannot be made, the write is refused. Reads never mutate.
Future-state files raise `UnsupportedSchemaError`, which every caller reports in
its own register: a settings-page status distinct from the I/O-failure one (the
remedy is updating, not retrying), a toast on direct hide/unhide, the existing
partial-success branches for import and delete, and a log line at startup.

**Import collision guard.** A rejected playlist file is absent from
`playlist_database`, so the import's duplicate-code check cannot see it, and
two different name/code pairs can sanitize onto one filename anyway — the
filename is not authoritative and "not loaded" must never be inferred from the
code. So immediately before its atomic replace, the import classifies whatever
already occupies the destination, through the same decoder the loader uses: a
future incumbent refuses the import, an unusable one is copied aside and
replaced, and a healthy v1 incumbent refuses the path collision. That last case
also fixes a live overwrite bug at the time of writing. This could not be
deferred to the release that first breaks the playlist schema, because the
vulnerable writer is *this* release's import path running after a rollback, and
a future PR cannot retrofit already-installed code. The shadow case — the same
code imported under a different filename, so no path collision — is accepted as
non-destructive: nothing is overwritten, and the loader's duplicate warning
surfaces it on the next start.

**v1 payload definitions**, implemented once and imported by both the runtime
readers and the conversion script. Settings v1 is a flat object whose keys are
a subset of {`stats_dir`, `kovaaks_username`, `steam_id`} with string values;
missing still means unset, and **unknown keys are invalid**, because within a
version the key set is fixed (rejecting preserve-unknown-keys below means any
future key addition bumps the version anyway, so a stray key under stamp 1 is a
typo worth surfacing). Settings is read `utf-8-sig`: a Windows-editor BOM is
valid legacy data for the documented hand-edit escape hatch. Visibility v1 is
exactly {`shown_playlists`: list of strings}, unknown keys invalid. Playlist v1
is `PlaylistData` unchanged, extra fields still ignored — these are
machine-written envelopes, not hand-edit surfaces. Visibility and playlist
files are plain UTF-8, where a BOM is invalid.

**Migration.** `scripts/stamp_schema_version.py` converts the existing
population once. Its state machine is narrow: unstamped with a valid v1 payload
gets the stamp; stamp 1 with a valid payload is a no-op (so re-runs are safe);
anything else is preserved and reported. A file carrying a *different* stamp is
never rewritten even when its payload happens to satisfy v1 — pydantic ignores
extra fields, so a looser rule would let a run years from now silently
downgrade a file from a much later release. The ordering contract is: back up
`data/`, update the app, **close it**, run the script once, relaunch. The app
must be closed because its in-process caches race the rewrites, and it must
already be updated because a stamped `settings.json` is rejected outright by
the pre-stamp reader, which then reads every setting as unset and lets
`bootstrap_stats_dir` overwrite the file with a bare `{"stats_dir": ...}`,
destroying the stored identity. Between update and script the app boots loud
but inert. **Compatibility floor:** once stamped files exist, pre-stamp
releases are unsafe rollback targets, by that same bootstrap-wipe mechanism.

The script resolves the *state root* itself rather than reading the module
constants the services bind at import, because on an installed copy those bind
to the wrong tree: the launcher exports `CSD_STATE_DIR` only around the app
process, so a manual command inherits nothing, and the code lives in
`versions/<tag>/` while the durable state lives at the install root. Resolution
order is `--state-dir`, then `CSD_STATE_DIR`, then the install root inferred
from the script's own location, then the working directory; the chosen root and
the rule that chose it are printed before any file is touched. The inference
demands install-only evidence, not just the `versions/<tag>/scripts` shape: the
candidate root must also hold the installer's `install.json`. Shape alone would
classify a checkout that happens to sit under a directory named `versions` as
an install and convert its parent, which is the silent wrong-tree write this
resolution exists to prevent; without the evidence the inference stays out and
the working directory wins, which is what a source checkout wants anyway. The installed command runs the release's
own `versions/<tag>/.venv/Scripts/python.exe` by absolute path, because a
standard install deliberately puts neither uv nor Python on `PATH` (see the
script's docstring for the exact snippet).

Note for the first release that actually *migrates* data: the launcher's staged
trial run executes load-time migrations before `/health` is consulted, so that
PR has to consider the trial window — for example by migrating only after
promotion.

Rejected: a string marker (an integer sorts and compares without a parser); a
missing-means-v1 grandfather rule (see above); a single global
`data/schema_version` sidecar (the three stores version independently, and a
sidecar can desynchronize from the files it describes); rewriting files to
preserve unknown keys (it converts a typo into permanent silent state); tolerating
unknown keys within a version for settings and visibility (playlists keep
`PlaylistData`'s ignore-extras deliberately, for the reason above); best-effort
reads of future files (guessing at a format the build does not know is how
data gets corrupted rather than preserved); move-instead-of-copy backups (a
failed write would leave nothing at the file's own path); deferring the import
guard to the v2 release (the vulnerable writer is this release's own import
path); and a reservation registry for import destinations (a second source of
truth that can drift from the filesystem, where the destination point-check
asks the only authority there is).

Supersedes, on these narrow points only: the 2026-08-02 settings entry's "no
`schema_version`" sentence, and the 2026-07-19 update-contract entry's position
that the durable state is schema-stable enough for a format break to be handled
by a manual step called out in its PR.

## 2026-08-11: A Fresh Install Is Asked Once, On A Card Keyed To Key Absence

Status: Accepted

A fresh install now says what it could not set up on its own. The landing page
carries a small card that either reports that no KovaaK's stats folder was
found, or offers the leaderboard features that would otherwise stay invisible.
The account offer can be skipped, which turns rank lookups off and takes the
card away for good. An install that is already configured never sees it, and
nothing about it blocks the app.

Decision: five parts, settled with the maintainer in the 2026-08-11 design
session and shipped from `docs/initial_setup_proposal.md` (proposed in PR
#231).

**A card on the landing page, and nothing heavier.** One card with one primary
action, on `/` (Scenario Performance) and only there; if a dedicated Home page
ever ships, the card moves with it. It is navigation and dismissal only: it
links to `/settings`, where detection and Save already live, so it never grows
a second detection UI and never touches the network — opening a page still
costs no KovaaK's request. It renders from the stored view (`get_settings()`),
the view the settings page renders from, never the process-pinned accessors,
because what it speaks about is what is on disk. Copy is fixed and part of the
decision: State A is "Add your KovaaK's account" over "See your leaderboard
position and percentiles for every scenario.", with "Open Settings", "Skip",
and the fine print "Skipping username disables rank lookups. You can set it
anytime in Settings."; State B is "Finish setting up" (D1) over "No KovaaK's
stats folder was found, so the dashboard can't read your runs yet. Set it in
Settings." State B names the action rather than the failure, which the body
already carries.

**Triggers are key absence, per item.** The card is the *never asked* surface:
each state shows only while its `settings.json` key is absent, and a key that
exists — with any value, `""` included — retires that item permanently. An
absent `stats_dir` gives State B, which offers no Skip (without run data the
app has nothing to plot) and wins whenever both keys are absent; a present
`stats_dir` with an absent `kovaaks_username` gives State A. Degraded settings
that do exist — a deliberate `""`, a stored path that has since vanished —
stay with the point-of-impact hints, so `home._stats_dir_hint()`'s
unconfigured branch narrowed to a key that is *present* and unusable. One
condition, one surface, instead of two lines saying it at once. Mixed presence
(`stats_dir: ""` beside an absent username key) is unreachable through the
app, because every Save writes all three keys; under a hand-edited file the
card and the hint each still state something true.

**The card stands aside for a pending restart.** While
`is_stats_dir_change_pending()` holds, nothing renders: the user is mid-setup,
the existing "Restart the app to apply your saved settings." hint owns
that moment, and stacking the identity ask on top would be two banners for one
unfinished action. The card returns after the restart if identity is still
unasked. It never claims completion; restart honesty stays with the settings
page's save statuses and notice.

**Skip is a locked identity decline, and it narrows the single-writer
decision.** `settings_service.decline_identity()` re-reads the stored mapping
and writes it back with only `kovaaks_username` set to `""` — the shipped
empty-means-off value — entirely inside the module `RLock` every read and
`save_settings` already take. That makes "alters no other key" an invariant of
the operation rather than a read-merge-write in a page callback: the card was
rendered at some earlier moment, and a review of PR #231 reproduced the race
where that stale snapshot restores an old `stats_dir` or `steam_id` over
values saved since. `save_settings` keeps its replace-all contract and its
pinning test untouched. That staleness cuts one more way, so the operation is
a no-op whenever the username key already exists: a card rendered in one tab
and clicked after another tab saved a real username would otherwise erase it,
and a refusal to answer is never grounds for discarding an answer somebody
gave (found in PR #236's review). This deliberately narrows the single-runtime-writer
clause of the 2026-08-03
["Settings Detection Suggests, And Identity Is Offered Only Once Verified"](#2026-08-03-settings-detection-suggests-and-identity-is-offered-only-once-verified)
entry rather than contradicting it: Save remains the only runtime writer of
*values*, and the decline can only ever record "asked and declined" — never
something a user typed. `pages/settings.py`'s module docstring carries the
same exception. The decline is surgical for a reason beyond the race: an
absent `stats_dir` stays absent, so the startup bootstrap keeps looking for
one on later boots. Nothing else follows from the click — no warmup worker
starts (there is no username to warm anything for), and nothing pins, because
the identity pin freezes only on a read that sees a configured username, so no
restart notice appears either. Recovery from a decline is the settings page
plus the point-of-impact hints; the card itself never returns. The callback
guards on `n_clicks` and `ctx.triggered_id` against the DashProxy
initial-call hazard (see the 2026-08-02
["A Committed Side Effect Reports Its Outcome Even When A Later Write Fails"](#2026-08-02-a-committed-side-effect-reports-its-outcome-even-when-a-later-write-fails)
entry's hazard note), which matters here because this callback writes to disk.

**New user-facing copy avoids em dashes.** A rule that emerged with this arc
and now lives in AGENTS.md's styling conventions: copy the app shows a user
reads as machine-written with them, so new copy uses short sentences instead.
Sweeping the shipped copy is explicitly deferred to a future review of all app
messaging; the temporary inconsistency between old and new lines is accepted
rather than fixed piecemeal.

**Rejected alternatives.** A blocking first-run wizard: heavier than a problem
whose setup is one Detect click plus Save, and modals are unverifiable in the
automated browser pane. A per-setting row checklist: scales poorly if settings
grow. A dedicated dismissed-flag key: persists a distinction no consumer reads
— runtime already treats `""` and absent identically everywhere — and grows
the flat schema with UI state. Session-only dismissal: reappears every boot,
which is nagging.

**Superseded in part, for copy (2026-09-14).** The card's fine print reads
"Skipping keeps position lookups off. You can add your username anytime in
Settings.", and State B's body reads "No KovaaK's stats folder was found, so
this app can't read your runs yet. Set it in Settings." The deferral in the
em-dash paragraph above is discharged: the sweep of all app messaging shipped,
and the em-dash rule is now one of nine copy rules, gated by a test. Triggers,
states, and Skip are unchanged. See [App Copy Follows One Set Of Rules, And The Em Dash Is Gated Out](#2026-09-14-app-copy-follows-one-set-of-rules-and-the-em-dash-is-gated-out).

Provenance: distilled from `docs/initial_setup_proposal.md` (proposed in PR
#231), shipped in PRs #235 (the companion playlists-overview status line,
which gives the overview grid the same unset-username explanation the
drill-down page already had) and #236 (the card); the proposal file is deleted
in the shipping PR and git history holds its full text.

## 2026-08-10: The Project Is AGPL-3.0, And Contributors Sign Nothing

Status: Accepted

Corporate Serf Dashboard is licensed under the GNU Affero General Public
License, version 3 or any later version, its copyright is held by
MingoDynasty, and contributors are not asked to sign a contributor agreement.
Anyone may use, change, and redistribute it, but a version they pass on has to
stay free and open source under the same terms. The choice was confirmed
deliberately on 2026-08-10, before the public launch, because it is the one
launch decision that cannot be taken back later. A few assets the app bundles
from other projects keep their own terms, so this is not a whole-tree claim.

**What was chosen.** AGPL-3.0 for this project's own code, whole text in
`LICENSE`. No contributor license agreement, no copyright assignment: a pull
request is accepted on its merits, and its author keeps their copyright. The
ruling is from 2026-08-10; the README's `## License` section has stated the
license publicly since PR #278, and this entry is the record of why.

**Amended 2026-09-13: the holder is named and the version form is chosen.**
The maintainer ruled both on 2026-09-13. The copyright holder is
MingoDynasty, the maintainer's commit and GitHub handle, and it is the sole
holder: `git shortlog -sne fd812fd`, run on the amending PR's base, lists only
the maintainer's own identity and the maintainer's Codex and Claude agent
sessions. The license form is AGPL-3.0-or-later. Until this amendment the
README said "v3.0" with no "or any later version" wording, and section 14 of
the license applies only the named version in that case, so the project was
3.0-only by omission rather than by ruling. Or-later was chosen so that a
future AGPL revision, such as one fixing a flaw, can be adopted without
relicensing, which stops being possible at the first outside contribution.
Section 14 bounds the risk the other way: later versions are promised to be
similar in spirit, and following one imposes no additional obligation on any
author or copyright holder. Per-file copyright headers were considered and
rejected: the project has a single author, `LICENSE` is enforced into every
release zip, and the app header links the source.

**Bundled third-party assets keep their own licenses**, and this is not a
whole-tree AGPL claim. `assets/vendor/canvas-confetti.js` is ISC
(`assets/vendor/canvas-confetti.LICENSE`), and the vendored SVGs under
`assets/icons/` are MIT, Apache-2.0 and CC0 by collection, tabulated in
`assets/icons/README.md`. `assets/` is in the release archive contract, so
those notices travel inside every published zip and have to be preserved on
redistribution. Vendoring anything new means confirming its license and
recording it the same way. `resources/` ships under the same contract but is
imported data, not vendored code: the benchmark library, a snapshot of Evxl's
benchmark index, and a KovaaK's game-settings response. No license is recorded
for any of it, and this entry does not settle whether one should be.

**Amended 2026-10-05: one bundled file is under no open license.**
`assets/icons/evxl-logo.png` is Evxl's logo. It ships with its owner's
permission, recorded in `assets/icons/README.md`, and neither the AGPL nor
any icon collection's license covers it. The detail is in
[the 2026-10-04 Evxl entry](#2026-10-04-a-benchmarks-scenario-page-links-to-its-evxl-page).

**Why this license.** The priority is that derivatives stay free and open
source. AGPL binds anyone who conveys a modified version, or offers one to
users over a network, to make that version's source available to those
recipients or users under the same terms.

**Why no CLA.** At this scale the friction a CLA puts in front of a first-time
contributor costs more than the flexibility it buys. What it would have bought
is the ability to relicense later without hunting down every contributor, and
that is the price being paid knowingly.

**The relicensing window closes at the first outside contribution, on
purpose.** Relicensing needs the consent of every copyright holder. Today that
is one person, so the license could still be changed unilaterally. The moment
an outside pull request is merged, it cannot. A public launch invites exactly
that, which is why the question was answered before launching rather than
after.

**Rejected alternatives.**

- **MIT or Apache-2.0.** Permissive terms would allow a closed commercial fork
  of the app, which is the outcome the choice exists to prevent.
- **AGPL plus a CLA, or copyright assignment.** Keeps the relicensing option
  open, at the cost of asking every contributor to sign before their first
  patch. Judged not worth it here.

**Where the terms travel.** `LICENSE` is named in `REQUIRED_ARCHIVE_ENTRIES`
in `scripts/release_job.py`, so a release whose zip lost it fails the draft
rather than shipping: every published copy carries the terms. The README's
`## License` section states them for readers who never open the file. Since
the 2026-09-13 amendment that section also carries the copyright line, and
`pyproject.toml` carries `authors` and the SPDX `license` expression
`AGPL-3.0-or-later`. Both files are release-archive entries too, so every
published zip carries the notice and the metadata.

## 2026-08-10: Bug Reports Land On GitHub Issues, With The Log Attached Unredacted And Disclosed

Status: Accepted

The app now has one place for feedback and bug reports: GitHub Issues, with a
bug form and a feature form and no blank-issue option. The bug form asks for
the app version and requires a log file, because a failure on a machine no one
else can see is otherwise undiagnosable. The log is attached exactly as the
app wrote it — including the reporter's KovaaK's username and Steam ID — and
the form says so plainly before the upload box, because the issue and its
attachments are public. The Settings page pre-fills the version into the form
and shows where the log lives, so filing a report is a click rather than a
scavenger hunt.

Decision: three parts, all settled on the
[feedback intake proposal](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/226)
and shipped in PRs #228 and #229.

**Disclose, do not redact (D1).** `debug.log` is attached as written. A
KovaaK's player's username and SteamID64 are already stamped on every
leaderboard score they set unless they opt out of leaderboards entirely, and
both values are what diagnoses the likeliest bug class — rank lookups and
benchmark row matching that fail on *which account* they resolved. An audit of
real logs on 2026-08-09 (the maintainer's production installs, Aug 5–9, plus a
4.3 MB dev corpus back to June 24) established the boundary this rests on:
Steam personas never reach the log at all (the identity probe's by-username
calls log as `<redacted>` via the `sensitive` flag in
`api_service._get_with_retry`, and `config/identity_detection.py` logs counts
and positions only); the startup config dump is benign under the current
schema; and no credentials exist anywhere in the app to leak. What *is* in the
log and is accepted here: the KovaaK's username in per-attempt request params
and in failure lines that embed the full URL, the SteamID64 that
`get_benchmark_json` passes unredacted (latent — not witnessed in any log
yet, and knowingly left that way by this decision), Windows usernames inside
absolute paths under `%LOCALAPPDATA%`, and the scores, sensitivities, and
timestamps the app exists to record. Nothing about what the app logs changes;
the escape hatch is that the log is plain text the reporter can read first.

Disclosure must name the audience, not only the contents. The form's copy
states that the issue and its attachments are public to anyone on the
internet, GitHub account or not, and invites reading the log before uploading.
Those two are required content, not style. The alternative — redaction
machinery across several unredacted failure-logging sites plus the benchmark
request params — buys privacy the leaderboard already gave away and costs the
values that identify the root cause.

**Issues and forms only (D2).** Blank issues are disabled in favor of
`bug_report.yml` and `feature_request.yml`; there is no Discord server and no
GitHub Discussions. Labels: `bug`, `enhancement`, `question`, `needs-info`,
and `upstream` for KovaaK's-side breakage the app can only work around.
Feedback arriving anywhere else is transcribed into an issue by the maintainer
as the canonical record (`gh issue create` is unaffected by the blank-issue
setting). This knowingly accepts an exclusion: users without a GitHub account
— likely a real share of a gamer audience — have no direct submission path.
**Revisit trigger:** launch feedback showing reports dying for want of an
account. Rejected for now: a second moderated inbox (Discord) or a second
triage surface (Discussions) for a single maintainer, ahead of any
demonstrated volume; and email, for its spam surface and lack of public dedupe
or history. Crash telemetry (Sentry or similar) is rejected outright as
privacy-hostile for a local tool.

**The Settings-page affordance (D3).** Under the version block,
`pages/settings.py` renders a "Report a bug" anchor whose href is
`bug_report_url(release_label)` — `…/issues/new?template=bug_report.yml&version=<label>`,
built with `urlencode`. Two contracts with
`.github/ISSUE_TEMPLATE/bug_report.yml` live in that URL: the template
*filename*, and the `version` field *id* that GitHub pre-fills by name. The
label is encoded rather than pasted because a release tag arrives from JSON
the app did not write. Every label the resolver produces is pre-filled —
`dev` and `unknown` included — since the field is required and editable, so a
placeholder beats an empty box. Beside it the resolved log directory is shown,
so "attach `debug.log`" names a place to look. `data/logs` moved into
`utilities/paths.log_dir()` for this, consumed by both `app.py` and the page:
pages cannot import `app`, and the literal should exist once.

## 2026-08-09: An Unset Username Is Stated In Place, Never Reported As A Failure

Status: Accepted, except that the per-click-id mechanism described below is
superseded by the 2026-08-31
["Repeatable Toasts Replace In Place With A Visible Re-Entry"](#2026-08-31-repeatable-toasts-replace-in-place-with-a-visible-re-entry)
entry: the blue notice is now a single-identity channel that re-pops by showing
a fresh instance id. The ruling — an unset username is configuration state
answered blue, never a red failure — is untouched. The
configured-but-wrong-username case the Scope note below defers is now half
settled by the 2026-08-22
["The Playlist Fill Reports Degradation In Place Only"](#2026-08-22-the-playlist-fill-reports-degradation-in-place-only)
entry, which deleted the playlist fill's aggregate toast — and with it
`_fill_summary_notification`, described below as untouched. Only the Refresh
half of "both generic red toasts" still fires. Everything else here stands.

With no KovaaK's username configured, opening a playlist used to run a
position update that fetched nothing and then popped a red "Position update
incomplete — couldn't update 16 of 16 positions", and clicking Refresh on the
Scenario Performance page answered with a red "Position refresh failed".
Nothing had failed: without a username the app never contacts KovaaK's at all.
The playlist page now skips that pointless update and says "Positions
unavailable — set your KovaaK's username in Settings" in its own status line,
and Refresh answers with a blue notice naming the missing username. Red again
means a lookup that really failed.

Decision: both position surfaces gate on the configured username before doing
any work, and report the unset case as the persistent configuration state it
is.

- `load_playlist_scenario_rows` (`source/pages/playlist_scenarios.py`) checks
  `get_kovaaks_username()` after the playlist resolves and before
  `start_playlist_scenario_fill`. When it is empty the phase-1 rows are
  returned with every pending flag cleared, a `None` generation token, the
  drain interval disabled, and the status line carrying the copy above with
  "Settings" as a `dmc.Anchor` — the same link the Position field's hint uses.
  `_fill_summary_notification` is untouched: the toast cannot fire because the
  fill it summarizes never runs.
- `refresh_rank` (`source/pages/home.py`) checks the same read after its
  `n_clicks` and selected-scenario guards, and returns `no_update` for the
  value plus one blue toast titled "KovaaK's username not set". The value is
  left alone because the field already reads "N/A — set your KovaaK's username
  in Settings".

Why in place on the playlist page and a toast on Refresh: the
[2026-08-03 routing policy](#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)
sends persistent conditions to in-place UI, and the playlist grid has such a
home. Refresh collides with the same policy's user-initiated branch, and that
branch wins for this event: the in-place hint was already on screen before the
click, so it cannot produce any perceptible response to the click itself, and
a user who clicks Refresh beside the hint plausibly clicked because they had
not read it. To keep every click answerable the toast carries a fresh
per-click id, the same mechanism the green confirmation uses — a stable id
would be swallowed by DMC's `show` while the previous toast is still up.
*(Superseded 2026-08-31: the toast is a channel whose fresh instance id per
emission does the same job, and hides the instance it replaces so repeats do not
stack.)* Blue, not yellow: yellow means degraded data (stale serve, threshold miss, Steam
mismatch), and nothing here is degraded.

Why skipping the fill is safe without a compensating cancel call: skipping
`start_playlist_scenario_fill` also skips its `_cancel_live_fills_locked` side
effect. Identity is process-pinned in one direction only — reads stay live
until the first non-empty username is observed, then freeze — so a tripped
gate means the username has been empty for the whole process, every earlier
playlist open tripped it too, and no live fill can exist.

Why the gate reads settings directly: string-matching the service's
`error_message` would couple routing to display copy, and a typed reason field
on `ScenarioRankInfo` cannot serve a pre-flight gate that must skip the fill
before any lookup runs. Only two sites consume the condition.

Scope: this entry rules on the **unset**-username case only. A username that
is configured but wrong is a different mechanism — it is knowable only per
result, after a network round-trip — and still produces both generic red
toasts today. That case is deliberately deferred and remains open; a typed
reason on `ScenarioRankInfo` is where it should be reconsidered.

Consequences: nothing is superseded. This discharges the kernel the
[2026-08-01 fully-offline entry](#2026-08-01-no-username-stays-fully-offline--user-independent-totals-rejected)
deferred until a settings page existed to point at — quiet state instead of a
red error, no futile fill, and a pointer to how to turn the features on.
Position cells still render N/A throughout: the service's guard fires before
any cache read, so no cached position can contradict the status line.

**Superseded in part, for copy (2026-09-14).** The two strings quoted above
now read "Positions unavailable. Set your KovaaK's username in Settings.",
with the period outside the link, and "N/A · set your KovaaK's username in
Settings". The ruling is unchanged. See [App Copy Follows One Set Of Rules, And The Em Dash Is Gated Out](#2026-09-14-app-copy-follows-one-set-of-rules-and-the-em-dash-is-gated-out).

Provenance: distilled from `docs/unset_username_position_feedback_proposal.md`
(four decisions ratified 2026-08-09), committed and then deleted in the
shipping PR — git history holds the full text.

## 2026-08-09: Human-Facing URLs Say localhost, Machine Probes Stay On 127.0.0.1

Status: Accepted

The launcher used to open the browser at `http://127.0.0.1:<port>/` while the
README and the development run said `http://localhost:<port>/`. Those are two
different browser origins, so the dashboard opened from the desktop shortcut
and the same install reached by typing `localhost` kept two separate sets of
saved UI preferences. Every URL a person sees or clicks now says `localhost`.
The launcher's internal health check still uses `127.0.0.1`, because a
machine-to-machine check should not depend on how the machine resolves names.

Decision: Human-facing URLs — the browser the launcher opens
(`scripts/launcher.ps1`, `Open-Dashboard`), the "Dashboard running at ..."
line it prints, and the URLs in `README.md` and `docs/` — use
`http://localhost:<port>/`. Machine-to-machine URLs stay on the literal
`127.0.0.1`: the launcher's `/health` readiness probe in `Wait-AppReady` is
deliberately resolver-free, and is not to be swept into consistency with the
human surfaces. `source/app.py` is untouched — its bind logic and port-taken
error text are about which addresses the server claims, not about which name
the browser is handed.

Why: the app persists UI state in `window.localStorage`, which is keyed by
origin — the Mantine color scheme written by the head script in
`source/app_shell.py`, the navbar Burger's `persistence_type="local"`, and the
chart-option switches in `source/pages/home.py` (Dash persistence defaults to
local storage). `localhost:<port>` and `127.0.0.1:<port>` are distinct
origins, so the two entry points to one install were accumulating disjoint
toggle state. Unifying on the name the docs and the development run already
use collapses that to one origin.

Why this is safe despite the shadowing history: the
[2026-07-19 exclusive-bind entry](#2026-07-19-the-app-binds-its-port-exclusively-and-exits-if-it-is-taken)
and its 2026-07-20 addendum bind **both** loopback faces (`127.0.0.1` and
`::1`) with `SO_EXCLUSIVEADDRUSE`, and the addendum's failure semantics are
two-bucket: a port free on only one face is refused outright rather than
half-served. So a half-bound instance cannot exist, and while the app is
serving, whichever face the resolver hands `localhost` is ours — the old
"browser gets a stranger's 404" failure needed an IPv6 face we did not hold.
The launcher's start and update paths open the browser only after
`Wait-AppReady` succeeds, and the already-running path opens it at an instance
that passed its own launcher's probe — so that one IPv4 probe vouches for both
faces. On a machine with no IPv6 the app serves IPv4 alone and `localhost`
resolves to IPv4 anyway.

Consequences: Nothing is superseded; the bind decision stands unchanged. The
maintainer's existing install has persisted toggles under the `127.0.0.1`
origin, which appear reset once after this change and are re-set by hand — per
the single-user policy, no migration code. Future URL surfaces pick a side by
audience: shown to a person, `localhost`; consumed by a script, `127.0.0.1`.

## 2026-08-09: PB Columns Keep Their N/A Sentinel Even For Timestamps

Status: Accepted

The playlist table gained a PB Date column showing when the personal best
was achieved. On a scenario with no local runs it renders "N/A" like the
other PB columns beside it, rather than the grid's "Never" sentinel, so an
unplayed row shows both words at once. This was chosen deliberately: each
word keeps one meaning, and the row's PB cells stay consistent with each
other.

Decision: A grid column whose value is a stat of the personal-best run
takes "N/A" as its null sentinel, even when the value is a timestamp
rendered with the shared relative-time helpers. "Never" stays scoped to
Last Played (in a playlist but never played). On an unplayed row, Last
Played reads "Never" while PB Score / PB Date / PB cm/360 / PB Accuracy
read "N/A"; the sentinels co-occur by design. Last Played and PB Date are
null under exactly the same condition — the scenario has no local runs —
so an unplayed row is the only place "Never" and "N/A" describe the same
fact. (PB cm/360 additionally reads "N/A" on played rows whose PB used a
different sensitivity scale; "N/A" in a PB column is not by itself
evidence the scenario is unplayed.) The playlist grid's live tick now
refreshes both timestamp columns:
`refreshCells({force: true, columns: ["last_played_sort",
"pb_timestamp_sort"]})`.

Why: "Never" answers "have I played this?"; "N/A" marks a stat that does
not exist because there is nothing to measure, and a missing PB is the
second kind. Column-family consistency (a row's PB cells agreeing with
each other) was judged to beat renderer consistency (every relative-time
cell sharing one sentinel). Maintainer-ratified copy call.

Consequences: Shipped in PR #216. Narrows the sentinel rule and extends
the single-column `refreshCells` call of the
[2026-06-21 relative timestamp entry](#2026-06-21-relative-humanized-last-played-timestamps),
whose Status line points here. Future timestamp columns choose their null
sentinel by column family, not by renderer.

## 2026-08-09: Chart Options Live In A Collapsible Panel Beside The Graph

Status: Accepted

The graph's display preferences used to open in a modal that dimmed the page
and blocked the chart behind it, so tuning an overlay meant adjusting, closing,
looking, and opening again. They now sit in a panel that slides out beside the
chart, which stays live and readable the whole time. On a narrow window the
same panel stacks above the chart instead. No preference changed what it does,
what it defaults to, or where it is stored.

Decision: `settings-modal`, `settings-modal-open-button`, and the `modal_demo`
callback are deleted. Their five chart preferences move into an in-flow
`chart-options-panel` beside `graph-content`, disclosed by a
`chart-options-toggle` button labelled "Chart options" and grouped under
*Overlays* and *Score Threshold* headings. `automatically-change-scenario-switch`
governs selection rather than presentation — it is the one moved control that is
not an input to `generate_graph` — so it is promoted out of the panel to sit
under the scenario selector. The panel starts closed on every visit and its open
state is not persisted.

Why: the container was adjudicated on a live-size interactive mockup built from
measured app geometry (1600×900, real element positions), not from taste. Open
plot area came out near-identical either way — stacked above the chart
1318×477 ≈ 629k px², beside it 1002×639 ≈ 640k px² — so the call fell to shape,
growth, and ergonomics, and all three favour the side panel: 1.57:1 stays
visually balanced where 2.76:1 reads wide and shallow, a vertical column absorbs
future controls without shrinking the chart further, and the panel can stay open
through sustained tuning. `dmc.Drawer` (a fixed overlay over the graph) and
`AppShellAside` (global chrome on every page) were rejected for the modal's own
reason: the graph is the only feedback surface these controls have. Folding them
into `/settings` was rejected earlier still — disjoint content, instant-apply
against deliberate-Save commit models, and no chart there to give feedback.

Consequences and constraints:

- **The flex role transfers; it is not duplicated.** `.home-chart-area` is now
  the direct flex child of `.home-page` and carries the `flex: 1 1 0` growth and
  the `min-height` floor that `.home-graph` used to hold. Leave those on the
  graph and the row falls back to intrinsic content height, so the graph stops
  consuming the remaining viewport.
- **`.home-graph` is a resize hook, not decoration.**
  `assets/homeGraphResize.js` locates graph containers by that class, and
  opening or collapsing the panel is exactly the
  container-resize-without-window-resize case Plotly does not redraw for on its
  own. The class and the script survive any future refactor of this row.
- **The reflow threshold is a container query, never a media query.**
  `@container home-chart-area (max-width: 62em)` measures the chart row's own
  box. The fixed 250px navbar shrinks the content area without touching the
  viewport, so a viewport threshold would keep the panel beside a chart it had
  already crushed — the same trap as
  [2026-08-03](#2026-08-03-homes-controls-row-measures-the-content-area-not-the-window).
  62em is Mantine's `md` step, off the scale the controls grid already uses. A
  container query cannot match on the element that declares the container, so
  `.home-chart-area` declares it and `.home-chart-row` carries the layout.
- **Collapsing animates the track, and the row clips.** The inspector's grid
  track transitions between `0` and 20rem at `dmc.AppShell`'s own 200 ms rather
  than being removed, so the graph grows and shrinks the way it does when the
  navbar collapses. Two facts make that work: the panel holds its own width
  while the track moves under it, so it is revealed rather than squeezed; and
  `.home-chart-row` clips, because Plotly redraws exactly once ~200 ms *after*
  its container stops moving and until then is still drawn at its old width.
  The navbar hides that overhang by being fixed-position and painting over it;
  an in-flow panel has to clip from the other side. Stacked, there is no width
  to animate, so that mode sets the duration to zero.
- **Ids and defaults survive verbatim.** Dash persistence is keyed by component
  id, and changing a layout default silently drops every stored value, so all
  six preference inputs kept both across the move. Collapsed controls hide with
  `display: none` — mounted, in the layout tree, still feeding their callbacks —
  and are never conditionally rendered.
- **The toggle's `n_clicks` guard is unconditional.** Under DashProxy a
  callback can fire on initial page load despite `prevent_initial_call=True`,
  which here would spring the panel open on arrival. The panel's class *is* the
  open state and `aria-expanded` rides with it, so a regression test pins that
  both are unchanged before a real click.

Shipped in PRs #209 and #215; design discussion in #206. This entry and
[the naming entry](#2026-08-09-the-graph-page-is-scenario-performance-its-panel-is-chart-options)
distil `docs/chart_options_inspector_proposal.md`, now deleted.

## 2026-08-09: The Graph Page Is Scenario Performance, Its Panel Is Chart Options

Status: Accepted

Three surfaces used to answer to the name "Settings", two of them with the same
icon. The graph page's preference panel is now called "Chart options", the page
itself is called "Scenario Performance" in the navbar and the browser tab, and
the Settings page keeps its name. The controls inside the panel are named the
way the app's own charts and the aim-training community already name them,
rather than in invented vocabulary.

Decision, four rulings:

- The disclosure button and the panel are **"Chart options"**.
- **`/settings` keeps the name "Settings".** The collision is resolved from the
  graph page's side; an "App setup" rename was considered and rejected.
- The graph page's product name is **"Scenario Performance"**, applied as
  labels only: the navbar link, the page's registered `name` and `title`, and
  doc vocabulary. `/` still serves it and `/home` and `/index` still redirect.
- The panel's column claims **no exclusive tenancy of the page's right side**.
  It is a page-local column a later design may share, stack with, or re-host.

Why: the surfaces sharing the "Settings" name are different in kind. `/settings`
edits server-persisted app setup through one validated Save with restart
semantics; the panel edits instant-apply browser preferences that only the chart
can give feedback on. Naming the panel after what it configures also follows the
repo's precedent that controls live on the surface owning their effect —
playlist management left this same modal for `/playlists`
([2026-07-11](#2026-07-11-the-playlist-overview-is-the-playlist-management-surface)).
"Scenario Performance" is the page's product identity, distinct from its route
position as the default landing page, which is why the rename is labels-only.

Consequences and constraints:

- **The control labels are the app's own vocabulary, not the proposal's.** The
  proposal recommended a *Score goal* group with "Playlist rank lines",
  "Personal-best line", "Show goal line", "Goal percentage of PB", and "Show
  goal verdict". The maintainer rejected that on first local test: the app's own
  chart annotations already render "PB Score" and "Score Threshold", and "Score
  Threshold" is what the aim-training community says. What shipped is *Overlays*
  ("Rank Thresholds", "PB Score") and *Score Threshold* ("Score Threshold
  Overlay", "Score Threshold Percentage", "Score Threshold Notification") —
  the modal's original labels, verbatim. The general rule this carries: proposed
  UI copy is checked against the app's existing plot annotations and sibling
  pages before it ships, however settled a proposal declares it.
- **"Score Threshold Notification" is knowingly imprecise.** Since the
  notification redesign it gates only whether a run is judged against the
  threshold (`_threshold_verdict` returns `None` when it is off); placement
  toasts fire regardless. The maintainer accepted the wording and deferred the
  fix to a later copy pass; a dated comment at the control in
  `source/pages/home.py` records it. The help tooltip is accurate as written and
  is unchanged. That copy pass has since happened: the control is now "Score
  Threshold Verdict"
  ([2026-08-21](#2026-08-21-run-notifications-have-a-master-switch-and-the-threshold-switch-is-renamed)).
- **The route restructure is deferred, not dropped.** Reserving `/` for a future
  Overview page and giving this page a durable `/scenario` route waits until an
  Overview has concrete plans.
- **Run History composes into this column rather than adding a second one.** If
  a run history tied to Scenario Performance arrives, how the two share the
  space is the run-history proposal's question; this one only promises not to
  have claimed the space.

**Superseded in part, for copy (2026-09-14).** The control labels and chart
annotations quoted above are sentence case: "Rank thresholds", "PB score",
"Score threshold overlay", "Score threshold percentage", "Score threshold
verdict", and the annotations "PB score" and "Score threshold". The group
headings keep their capitals as section headings. The vocabulary rule this
entry carries is unchanged. See [App Copy Follows One Set Of Rules, And The Em Dash Is Gated Out](#2026-09-14-app-copy-follows-one-set-of-rules-and-the-em-dash-is-gated-out).

Shipped in PRs #209 and #215; design discussion in #206. Distilled with
[the inspector entry](#2026-08-09-chart-options-live-in-a-collapsible-panel-beside-the-graph)
from `docs/chart_options_inspector_proposal.md`, now deleted.

## 2026-08-08: Rank-History Capture Is Deferred Until A Position-Over-Time Feature Is Designed

Status: Accepted

The app keeps only the latest leaderboard position per scenario, so past
positions are overwritten and cannot be reconstructed later. A proposal to
start capturing them now, ahead of any feature that uses them, was reviewed
and deferred. Score-over-time needs no capture — runs are kept as files and
can be recomputed at any time. Position- and percentile-over-time would need
capture running before they ship, but those features are ideas rather than
designs, so the project accepts losing that history until one is fleshed out.

Decision: rank-observation capture does not ship now. The revisit trigger is
concrete: the day any position- or percentile-over-time feature moves from
idea to design, that design's **first** deliverable is the capture below —
history starts when capture starts, and the gap between now and then is the
accepted, known cost. Agents: do not re-propose capture absent that trigger;
cite this entry instead. Do not silently widen any rank-cache write into a
history store either — the serving cache stays a cache.

The reviewed capture spec is preserved here so revival needs no re-derivation
(it was review-corrected twice and is believed sound): append one NDJSON line
per **fetched** observation to an append-only file under `data/` (not
`data/cache/` — capture, not cache); fields `leaderboard_id`, `username`,
`scenario_name`, `rank`, `score`, `observed_at` (UTC ISO-8601, from the
fetch), plus `total_players` as an optional best-effort join with its own
fetch moment (the rank fetch does not carry it; percentile analysis must
treat the denominator as temporally approximate). The capture boundary is
fetch-result handling, not `_save_rank_monotonic` — the `_score_is_fresh`
gate discards real observations before the monotonic writer, and candidates
the monotonic filter rejects are recorded (a worsening rank is signal). Cache
re-serves and the `allow_network` re-save of an already-cached value are not
observations. Consecutive identical observations per
`(leaderboard_id, username)` dedupe; appends are fail-soft; no reader ships
with capture.

Why: maintainer review. Position- and percentile-over-time sound useful on
paper but are unfleshed, and both are less settled than score-over-time,
which needs none of this. Capturing data for an undesigned feature class is
exactly the speculative scope this project prunes; the irreversibility
argument for capturing anyway was weighed and accepted as a known loss. The
2026-08-06 `json-vs-sqlite-storage` note had dropped the vault design's
Phase 2 ledger by taxonomy accident — this entry replaces that silence with
a deliberate call.

Consequences: every day before revival is unrecorded position history, by
choice. The existing SQLite triggers ("reconsider SQLite when we need rank
history…") are unchanged — if capture is revived it remains engine-neutral
(NDJSON re-ingests into whatever table a migration creates), so this defers
nothing about, and prejudices nothing in, the open SQLite questions.

## 2026-08-08: PyCharm Config Stays Tracked And Its Upgrade Churn Is Committed Once

Status: Accepted

An IDE upgrade changed the format PyCharm writes its own tracked config files
in, and PyCharm re-emits that format every time it launches. Reverting the diff
therefore only defers it, so the project commits it once instead. The IDE
config directory also no longer counts as a reason to cut an automated release,
which it previously would have. A leftover Black on-save setting turned out to
be orphaned by the same upgrade, and deleting it survived an IDE restart, so it
is gone rather than merely documented.

Decision: `.idea/` stays tracked, IDE-upgrade schema churn is committed rather
than reverted, and `.idea/` joins `_BLOCKED_DIRECTORIES` in
`scripts/release_job.py` so an IDE-config-only push does not release.

Why: the same tool-config diff was committed as `89d54cf` on 2026-08-04 and
reverted by `b44901a`; launching PyCharm on `main` rewrote both XML files
immediately, so the revert bought nothing. Untracking `.idea/` instead would
throw away real configuration work — the interpreter and mypy setup, the source
root, and the indexing exclusions — while the genuinely volatile per-user files
(`workspace.xml`, `tasks.xml`, `shelf/`, datasources) are already covered
between the root `.gitignore` and `.idea/.gitignore`. On the release side,
`is_release_worthy()` is a blocklist, and `.idea/` matched no entry, so
`should_release()` returned `True` for a PyCharm tool map and
`.github/workflows/ci.yml` would have tagged CalVer and published a Latest
release that cannot be deleted. `.gitignore` and `.pre-commit-config.yaml` were
already blocked for exactly this reason.

Consequences and constraints:

- **Committing is not self-enforcing.** `.idea/pyLspTools.xml` records the
  registered tool map, so the loop restarts whenever a tool is toggled in the
  IDE: `89d54cf` registered `black` and `ruff`, while the settled state
  registers `ruff` only. What ended the churn is that tool state is now stable,
  not the act of committing it.
- **Neither remaining on-save formatter switch is live.** `.idea/misc.xml`'s
  `Black` component (`enabledOnSave=true`, against the
  `uv (Corporate-Serf-Dashboard)` SDK where `black.exe` really resolves) was
  deleted, because the upgrade orphaned it rather than leaving it live: tool
  state moved to `pyLspTools.xml`, and dropping `enabledOnReformat` was a
  one-time migration write. Hand-editing a generated file is normally what
  invites churn back, so this was tested — after the deletion a PyCharm restart
  rewrote `pyLspTools.xml` and `workspace.xml` and left `misc.xml` alone.
  `.idea/ruff.xml`'s `RuffConfigService` (`runRuffOnSave=true`) is inert for a
  different reason: it belongs to the third-party `com.koxudaxi.ruff` plugin,
  which is disabled IDE-side, so ruff-on-save runs from the built-in tool state
  instead. Read `ruff.xml` as a dormant plugin's config, not as live state. If
  a future upgrade re-emits either component, repeat the delete-and-restart
  check rather than reverting the config.
- **black is a transitive dependency, not an absent one.** It is not in
  `pyproject.toml` and not a configured project tool, but it stays in the lock
  under `datamodel-code-generator` and is installed in `.venv` — see
  [Consolidate Formatting And Linting On Ruff](#2026-07-03-consolidate-formatting-and-linting-on-ruff).
- **Blocking is about triggering, not shipping.** The two lists are separate:
  `_BLOCKED_DIRECTORIES` decides whether a push cuts a release, while
  `.gitattributes` decides what the release zip carries. `.idea/` is now on
  both — it neither triggers a release nor ships in one, per
  [Release Integrity Rests On GitHub Digests And An Enforced Archive Contract](#2026-08-21-release-integrity-rests-on-github-digests-and-an-enforced-archive-contract).
  `docs/` still shows the split as it was: blocked from triggering, but
  shipped, because the zip's own README links into it.

## 2026-08-03: Home's Controls Row Measures The Content Area, Not The Window

Status: Accepted

Opening the navigation sidebar used to shove Home's row of controls onto a
second line, and closing it snapped them back. The sidebar takes 250px away
from the page, but the rules deciding how to lay the controls out were reading
the width of the whole browser window, which does not change when the sidebar
opens. Those rules now read the width of the area the controls actually get,
and the two wide dropdowns narrow a little before the row gives up and wraps.

Decision: Home's controls `dmc.Grid` sets `type="container"` and passes
`breakpoints`, and both wide playlist/scenario dropdowns swap a hard
`miw="min(400px, 100%)"` floor for `flex="1 1 200px"` under a
`maw="min(400px, 100%)"` cap and over a matching `miw` floor. The breakpoint
*values* are unchanged Mantine defaults; only the box they measure moves.

Why: `dmc.AppShellNavbar` is `position: fixed` with `width: 250px` and offsets
main's padding, so the content area shrinks by 250px while the viewport does
not. Mantine's default Grid emits `@media (min-width: …)` for responsive
`span` values, so Home's `span={"base": 12, "lg": 10}` crossed its threshold at
a 1200px *window* even when the content area was only ~900px. Both columns then
got a share of width the page did not have: the left column's controls wrapped
and the right column's radio labels were squeezed. The 400px `min-width` floor
compounded it, for the reason recorded below.

Consequences and constraints:

- **Line-breaking reads the hypothetical main size, not the shrunk size.** A
  flex item is collected onto a line at its flex-basis clamped by min/max
  width; `flex-shrink` only redistributes space *inside* a line that has
  already been collected. Anything pinning a dropdown's pre-wrap size at the
  400px target — the original `min-width: 400px`, and equally a
  `flex: 0 1 400px` basis — books 400px of the row before shrinking can run, so
  the row wraps at exactly the width it did before. The basis must therefore sit
  at the 200px *floor*, with `flex-grow` climbing back toward the 400px cap on a
  line that has room. `tests/test_home_layout.py` asserts the derived
  hypothetical size stays below the target rather than asserting the prop
  strings, because a prop-shaped test passes on all of the broken combinations.

- **`breakpoints` is not optional here.** Mantine renders the element carrying
  `container: mantine-grid / inline-size` only when a Grid passes *both*
  `type="container"` and `breakpoints`, while the `@container` queries
  themselves are emitted on `type` alone. Setting `type` without `breakpoints`
  produces queries with no container to match, silently collapsing every column
  to its `base` span. `tests/test_home_layout.py` pins both props together.
- **The threshold band moves.** Between roughly 1200px and 1480px of window
  width with the sidebar open, Home now stacks its two columns where it
  previously split them. That is the band where the split was crushing both
  columns, so the stack is the intended outcome rather than a regression.
- **Responsive *style props* have no container equivalent.** Mantine resolves
  those through theme media queries only, so this fix reaches responsive `span`
  values and nothing else. Nothing on Home relies on one today: the playlist
  filter's `ml={"base": 0, "lg": "xl"}` was the last, and PR #201 removed it
  outright for left-edge alignment — `tests/test_ui_presentation.py` now
  rejects any left offset on either playlist filter. A responsive margin or
  padding added elsewhere later would silently go back to measuring the window.
- **The sizing rule lives in `PLAYLIST_SELECTOR_PRESET`**, so the Aim Training
  Journey page's `dmc.MultiSelect` picks it up too. Both sit in wrapping rows
  and want the same behavior; splitting the rule to spare the second page would
  cost more than it saves. *(Renamed 2026-10-04: the rule is
  `PLAYLIST_SELECTOR_SIZING`, a second dict in the same module, so a page can
  put it on the column that holds its dropdown. Both pages still read the one
  rule.)*

## 2026-08-03: One Quiet Notification Layer With Verdict-Carrying Copy

Status: Accepted; three clauses are superseded by the 2026-08-31
["Repeatable Toasts Replace In Place With A Visible Re-Entry"](#2026-08-31-repeatable-toasts-replace-in-place-with-a-visible-re-entry)
entry -- the per-click-id exception to the stable-id rule, the distinct-ids
rationale for the two refresh-failure toasts, and the absolute reading of "at
most one run-verdict toast is visible at a time". Each is marked in place below.
Everything else here stands, including the routing policy that decides which
events toast at all.

The dashboard now stays quiet during normal play. Toasts are reserved for
things the user did, achievements worth interrupting for, and failures they
would act on; a condition that stays true explains itself where it happens
instead of popping up again on every trigger. Each run produces at most one
toast, its title states the verdict, and a newer run replaces the one on
screen rather than stacking beside it.

Predecessor: the
[2026-08-03 background-diagnostics entry](#2026-08-03-background-rank-diagnostics-are-console-only)
deleted four toasts under this policy before the policy itself was recorded;
that entry stands unchanged and this one supersedes nothing. Shipped in
PRs #194, #196, #198, and #200; design in #82 and #195.

**One delivery path.** The app had two notification subsystems. The
logging-driven one routed Python `logging` records into Mantine toasts through
an in-repo handler, and it is deleted: the handler, its module-level queue, its
drain callback, and the tests covering that machinery. `logging` remains the
console and file record; it no longer reaches the screen. The decisive argument
is that **a log level is not a routing policy** — the bridge made every
`dash_logger` call a toast, with a severity picked at the call site standing in
for a judgment that belongs to the event. It also gave every record a fresh
`uuid` id, so records stacked instead of replacing, under generic
"Info/Warning/Error" titles. Everything now goes through `sendNotifications` on
the shell's one `dmc.NotificationContainer`, fed by payloads from the
`utilities/notifications.py` builder.

**Routing policy — who gets a toast.** Decided per event, in this order:

- *Persistent condition* (misconfiguration, missing data, degraded feature) →
  **in-place UI** at the point of impact, never a toast. Conditions do not stop
  being true when a toast expires. Two named exceptions, both persistent
  conditions with no in-place home, both surfaced once per lifecycle rather
  than once per trigger: the Steam-ID mismatch gets one toast per app session,
  and the startup playlist warnings one batch per boot. Both persist until
  dismissed.
- *Automatic failure* during passive navigation → **no toast**; the field state
  conveys it, with a console `logger.warning` retained.
- *User-initiated failure* (Import, manual Refresh) → **error toast**; the user
  asked and deserves the result. A run file that failed to import sits here
  too: playing the run was the user's act, and nothing else tells them it never
  recorded.
- *Achievement / coaching* → one toast per run.
- *Diagnostic* (thread failures, timeouts with automatic fallback) → **console
  log only**.

Litmus tests, in order: is it a state rather than an event? → in-place. Is it
already visible somewhere (plot point, Position field, empty-state canvas,
warmup status strip)? → nothing. Would the user act differently for having seen
it right now? No → log, not toast.

**Background threads never drive UI outputs.** They publish to typed shared
state that an interval callback polls. There is deliberately no general event
bus: each channel carries one kind of event and its consumer decides what the
user sees. The deleted level-driven queue is the anti-pattern the rule exists
to prevent. The one background toast that survived the routing verdicts — the
run-import failure — got its own typed deque rather than a field grafted onto
the run-event queue. The sanctioned channels are enumerated in
[architecture.md](./architecture.md).

**One run, one toast.** Every run verdict and the catch-up digest share the
stable id `run-verdict`. When a run both places top-N and earns a threshold
verdict, the threshold verdict is the headline and the placement a trailing
detail; a run that earns neither emits nothing, because the new point on the
plot is the confirmation that it landed. Four behaviors are normative, and the
mechanism is not:

- at most one run-verdict toast is visible at a time (as amended 2026-08-31:
  true once a response has been applied -- during the ~250 ms replacement
  crossfade the outgoing instance is still animating out);
- a later verdict replaces the visible one, the backlog digest included;
- the replacement receives a full toast lifetime, never the remainder of the
  old timer;
- all of the above holds per browser client and survives page navigation.

The mechanism that satisfies them on DMC 2.8.0, verified against the shipped
bundle: a bare `show` cannot replace (the store ignores it for an id already on
screen) and `update` is a no-op for an id that is not, so each emission sends
**both actions with the same id and payload** and whichever matches applies.
Mantine's auto-close timer is a React effect keyed on the resolved duration
alone, so an `update` carrying the same duration leaves the original timer
running; the payload therefore alternates between two indistinguishable
durations (8000/8001 ms) to force the effect to cancel and re-arm. The
alternation counter is a `dcc.Store` in `app_shell.py` beside the container,
**not** in Home's page layout: a toast outlives the page that emitted it, and a
page-scoped store would reset on remount and hand a still-visible toast the
duration it is already displaying. `hide` cannot substitute — it is a separate
prop whose effect runs after the `sendNotifications` effect, so a hide-then-show
pair in one response would hide the toast it just showed.
`tests/test_home_run_verdict_lifetime.py` models those store semantics against a
clock and asserts the behaviors in elapsed time; it is the upgrade guard for
future DMC versions.

**Presentation standards.**

- Stable, semantic notification ids; dedupe or replace by id. One named
  exception: repeatable user-action results use a **per-click id** — the
  manual-refresh confirmation, where `show` with a reused id would swallow the
  second of two deliberate back-to-back results. *(Superseded 2026-08-31: the
  confirmation is a per-scenario channel and every repeatable result re-pops by
  showing a fresh instance id, so no toast carries a per-click id.)*
- **The title carries the verdict.** Title plus color tell the whole story from
  across the room; never the literal word "Notification".
- **The message leads with the scenario.** Sensitivity is a trailing qualifier:
  top-N is per-sensitivity, so it matters, but it is never the subject.
- One nominal `autoClose` duration, with two deliberate exceptions that persist
  until dismissed — the Steam-ID mismatch and the startup playlist warnings,
  both of which fire when the user may not be looking.
- A failing threshold verdict names the target it missed: one extra number with
  real motivational value.
- No "New personal best!" retitle. A new overall PB necessarily places 1st
  within its sensitivity, so it already earns the run-verdict toast — titled
  "New best score" when unjudged, or carrying the threshold verdict when
  judged; retitling it would create by the back door the dedicated PB toast
  that `product.md` records as declined.

Two manual-refresh failure toasts deliberately share the title "Position
refresh failed" under distinct ids (red when nothing usable came back, yellow
when a cached position was served). They are mutually exclusive outcomes of one
click, and the distinct ids keep a later result from being swallowed by `show`'s
dedupe. *(Superseded 2026-08-31: being mutually exclusive is exactly why they
are now one `rank-refresh-problem` channel — under distinct ids a hard failure
followed by a served-stale retry left both on screen contradicting each other
about the same attempt.)* Softening the red to yellow is coupled to giving the
served-stale toast a title of its own — without that, only the color separates
them — and is left open in [tech_debt.md](./tech_debt.md). *(Superseded in
part, for copy, 2026-09-14: the served-stale toast now has that title of its
own, "Refresh failed · position from cache", while the red hard failure keeps
"Position refresh failed"; the color question stays open. See [App Copy Follows One Set Of Rules, And The Em Dash Is Gated Out](#2026-09-14-app-copy-follows-one-set-of-rules-and-the-em-dash-is-gated-out).)*
*(Superseded again, for copy, 2026-09-22: the served-stale title is now
"Refresh failed · data from cache", chosen by the maintainer over "Refresh
failed · from cache", and when the cached readout includes a total its
message reads "Couldn't refresh. The position and total shown are from
cache." A failed position request asks for no total, so that total predates
the click too, and once a partial refresh began reporting the total on its
own, naming only the position read as though the total had refreshed. With no
total on screen the message still names only the position, and the red hard
failure keeps its message because it never sees what the field shows. See
[scenario_rank.md](specs/scenario_rank.md#failure-handling).)*
*(Resolved 2026-09-27: the hard failure stays red. See
[The Manual-Refresh Hard Failure Stays Red](#2026-09-27-the-manual-refresh-hard-failure-stays-red).)*

**Deliberately left open: do background rank events deserve a real toast?**
"Your rank updated after that PB" and "Position update timed out" are
console-only under the background-thread rule. Surfacing either needs a
conformant channel — a dedicated typed event queue or polled cache state, never
the run-specific `message_queue` — and the run-import-failure queue is the
pattern to copy if it is ever wanted. It pairs with the unbuilt "rank improved"
toast and should be decided with it, not piecemeal.

## 2026-08-03: Background Rank Diagnostics Are Console-Only

Status: Accepted

Supersedes: the "asks the user to click Refresh" consequence of the
[2026-07-01 score-aware refresh entry](#2026-07-01-keep-scenario-rank-consistent-with-score-aware-refreshes).
The rest of that decision — the timer schedule, the two-decimal catch-up floor,
the monotonic writer, the cache-only interval poll, and the board-authoritative
manual Refresh — is unchanged.

When a position lookup fails in the background, the app no longer shows the user
an error message. The failure is written to the console and the log file, and
the position on screen keeps showing the last value the app confirmed. Nothing
is lost or overwritten by the failure, but the app no longer announces it
either: a background failure is now something the user finds in the log, or
infers from a position that did not move after a personal best.

Decision: four background diagnostic error toasts are deleted and their
`logger` siblings retained. Three are in the rank-freshness timer chain in
`kovaaks/api_service.py` — retry exhaustion, the unknown-user stop, and the
unexpected-error safety net — and one is in `my_watchdog/file_watchdog.py`,
where scheduling the refresh itself fails. `api_service.py` loses its
`dash_logger` import and module-global with them; `file_watchdog.py` keeps both
for its run-import failure toast, which this entry does not touch.

Why: these calls were dead code when written — `dash_logger` records emitted
from a plain thread never reached a callback context — and PR #115's queueing
handler made them live without anyone re-deciding whether they should be. What
they actually deliver is a generic red "Error" toast, batched onto the next
Home visit. One channel was reporting two failures of different kinds, and the
reasons for dropping it differ per kind — neither of them is "the chain retries
until it works", which is true of no path here:

- **An exhausted chain has a recoverable outcome, not a self-healing one.**
  The chain stops; nothing reschedules it. What makes the outcome benign is the
  monotonic writer: a failed attempt never replaces the cached position, so the
  widget keeps serving the last confirmed value and the *next successful
  lookup* corrects it — a later PB, a manual Refresh, or a foreground fetch
  once the week-long rank-cache TTL expires (the interval poll is cache-only
  and never triggers one). With no later PB, the displayed position can sit at
  its pre-PB value for that full TTL. That is bounded staleness on a value that
  was correct when written, and it is the honest ceiling on this decision.
- **The unknown-user stop never recovers, and is not claimed to.**
  `_run_attempt` returns without scheduling, and every later PB repeats the
  same failure until the username is fixed on the settings page. It is dropped
  for a different reason: it is a persistent misconfiguration that the
  foreground already reports. Home's rank callback takes `run-events` as an
  input, so the same new run that schedules the chain also triggers a
  network-allowed foreground lookup, which returns `UNKNOWN` carrying
  `KovaaK's username '<name>' was not found.` and toasts it through
  `_emit_rank_messages`. The deleted background toast was a second, later, less
  specific copy of a message the user already receives.

Consequences — the accepted loss is on the exhaustion path: it now has no
user-visible surface at all, so noticing one means reading `data/logs/debug.log`
or the console, or noticing the position did not move. This entry accepts that
rather than solving it. The remedy on the table — a persistent in-place state on
the Position field that explains why the value is what it is — is a UI addition
belonging to the notification redesign, not to a deletion-only change, and is
tracked there (PR #82, the routing-policy and in-place-state decisions). Manual
Refresh, which reports its own failures in the foreground, remains the escape
hatch the superseded entry reserved for a permanently divergent score; what
changes is that the app no longer prompts for it. The regression tests for these
paths assert the retained log records rather than toast delivery.

Scope: this entry decides these four call sites only. The broader notification
redesign — which subsystem owns toasts, the routing policy that produced this
verdict, and the fate of every other toast in the app — was still under debate
in PR #82 when this shipped, and is now recorded in the
[2026-08-03 notification-layer entry](#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)
above. The deletion was split out (PR #194) because it stands alone: nothing
else reads the removed calls, and the retained logging is untouched.

## 2026-08-03: Settings Detection Suggests, And Identity Is Offered Only Once Verified

Status: Accepted; the single-runtime-writer clause is narrowed by the
2026-08-11
["A Fresh Install Is Asked Once, On A Card Keyed To Key Absence"](#2026-08-11-a-fresh-install-is-asked-once-on-a-card-keyed-to-key-absence)
entry — Save is still the only runtime writer of settings *values*, but a
locked service operation may record a declined identity as `""`. Everything
else here stands.

The Settings page now offers what this machine already knows instead of asking
the user to type it. The stats-folder box suggests every Steam library that
holds a KovaaK's stats folder, and a Detect button beside the identity fields
checks the machine's Steam accounts against KovaaK's and fills in the one it
can prove belongs here. When it cannot prove exactly one, it lists what it
found and lets the user choose. Nothing reaches disk until Save: detection
only ever fills the form.

Decision — **detection suggests, Save writes.** Both detectors feed inputs the
user can still edit or ignore, so the store keeps its single runtime writer and
all of Save's shipped semantics (all-or-nothing validation, every key written,
warmup cold-start on a first identity, the restart notice from
`is_restart_pending()`). Stats-directory suggestions are hints, not an allowed
set: the field stays free text, a path Steam never heard of is still valid, and
Mantine's default option filter is overridden (`allOptions` in
`assets/dashMantineFunctions.js`) because the field is normally prefilled and
the alternatives are precisely what it must keep showing. The absent-key
`stats_dir` bootstrap remains the app's one silent writer, per the earlier
one-silent-writer decision; identity never joins it, because a wrong identity
is not self-evident the way a wrong stats folder is — it fills caches with
someone else's ranks.

**Identity is offered only as a verified pair.** KovaaK's has no reverse
lookup — `by-steam-id` answers 404 and the query-parameter profile endpoint 401
— so detection cannot ask who a Steam ID belongs to. It guesses and verifies
instead: every local Steam account's persona is probed against the
unauthenticated `by-username` endpoint, and the answer counts only when the
profile's `steamId` equals that account's SteamID64. A persona that merely
coincides with someone else's KovaaK's name is discarded rather than believed,
409 is a confirmed absence, and what the page fills in is the profile's
canonical `webapp.username`, never the persona that found it: the two are
distinct namespaces that often coincide, and only the canonical spelling works
against the rest of the API. Accounts come from every Steam root the registry
names rather than the first — the 32-bit and 64-bit views can point at
different installs, and neither is guaranteed to be the active client — merged
by SteamID64 keeping the newest `Timestamp`, because the most recently used
client holds the freshest persona.

**The trigger is split by cost.** Stats-directory candidates are a registry
read and a handful of directory probes, so they are recomputed on every render
of the page. Identity detection calls KovaaK's, so it runs only behind the
button, which doubles as re-detect: opening the page never spends a request,
and a slow-spell account can hold the button's spinner for tens of seconds
without a render waiting on it.

**Probing personas is an accepted privacy trade, and it stays out of the log.**
Detection sends the persona name of every Steam account on the machine —
including other people's on a shared PC — to a public endpoint. That is
deliberate: personas are already public on Steam, the probe is equivalent to
typing the name into kovaaks.com's search, it fires only on an explicit press,
and nothing is persisted for candidates the user does not save. The consequence
is designed in rather than left for review to find: `data/logs/debug.log` is
collected with bug reports, so the probe marks its request sensitive — attempt
lines log a placeholder in place of the queried name and failure summaries drop
the query string — and detection's own lines name counts and positions
("account 2 of 3"), never personas or IDs. A regression test drives success,
409, and transport failure under `caplog` and asserts no persona reaches a
record.

**An incomplete detection is never dressed up as a conclusive one.** The engine
reports two failure facts beside its candidates: how many accounts could not be
checked (a transport failure, an unexpected status, or a 2xx payload the
pipeline cannot use — schema drift degrades exactly like an outage, never as an
exception), and whether account discovery itself was complete (an account list
that existed and could not be read is a different fact from reading cleanly and
finding nobody). The page spends both. **The auto-fill gate is exactly one
candidate, zero unchecked, discovery complete**; a sole candidate from a run
with anything unresolved goes to the picker, because the unresolved part may be
hiding a second valid account. The conclusive "no Steam account here has a
KovaaK's profile" message — the one that tells the user manual entry is all
that is left — is reachable only from that same certainty; an unreadable
account list says so in its own words instead.

Deliberately out of scope: the guided first-run experience, whose
discoverability and dismissal questions are deferred to their own proposal;
verifying a manually typed username; the pre-2021 numeric-key
`libraryfolders.vdf` format (a known gap, pinned by test); and any change to
startup — the bootstrap stays first-hit and absent-key-only.

Provenance: distilled from `docs/settings_detection_proposal.md` (proposed in
PR #186), shipped in PRs #189 (stats-directory candidates), #191 (the identity
engine), and #193 (the page's Detect action); the proposal file is deleted in
the shipping PR and git history holds its full text.

## 2026-08-02: The Settings Page Owns Version Display

Status: Accepted

The app's version now appears on the settings page — the release tag on one
line, the commit it was built from on the next — instead of hiding in a
tooltip on the header's GitHub icon. Anyone checking which version they are
running, or quoting one in a bug report, can look somewhere they would think
to look. The section is plain text: it shows what the app already knew about
itself and asks the network nothing. Its two dates can honestly disagree by a
day, because the version dates the release and the second line dates the
commit; that line is labelled Commit so the difference reads as fact, not
error.

Decision (PR #190): the settings page is the venue for build identity, and
`github_component`'s tooltip reverts to a plain "View this app on GitHub".
The build suffix was an explicit stopgap — identity shipped (PR #154) before
any page existed that could own the display, and information behind a hover
on a repo link is found by accident rather than on purpose. A separate About
page was considered and rejected in the same call: a nav destination for three
lines of static text is not worth the space, and the settings page
([entry](#2026-08-02-user-settings-live-in-an-app-owned-store-with-a-settings-page))
is already the "about this install" home.

The section is static text built with the page layout from
`BuildInfo.release_label` (the CalVer tag, `dev` in a source checkout, or
`unknown`) and `BuildInfo.short_description` (short SHA and commit date). It
re-derives no part of the identity, owns no callback, and makes no request.
Identity resolution is unchanged: the stage-time `release.json` copy and the
full precedence live in
[Build Identity Comes From The Manifest](#2026-07-19-build-identity-comes-from-the-manifest-corroborated-by-the-stamp),
whose surfaces list this entry rewrites.

Clock semantics (PR #225): the CalVer tag date is the release date in UTC —
CI mints the tag with `date -u` — while the displayed commit date is git's
`%cs`, rendered in the commit's own recorded offset. They date different
events on different clocks, so an evening local-time merge routinely
straddles UTC midnight and picks up a next-day tag. Rather than
UTC-normalising every identity producer to force agreement, the build line
carries a `Commit` prefix that attributes the parenthesised date to its
event.

Sequencing behind that mechanism (PR #188) was a hard dependency, not a
preference. Post-update verification — "the console said it updated to vX; did
it work?" — is the display's peak-usage moment, and a version line reading
`unknown` exactly then looks like a failed update and manufactures the
confused bug reports the display exists to prevent.

Support boundary for that guarantee (maintainer, adjudicating the PR #187
review): the app has a single-user install base, so update paths originating
from releases that predate PR #188 are out of support. The guarantee holds
whenever the launcher staging the update is PR #188's or newer. An install
still on an older release stages its next update without the copy, so that
one trial session shows `unknown`; it self-heals at the next launch, and
permanently once a newer launcher stages the following update. Both escape
hatches already exist — launch again, or re-run the install one-liner. With a
single-user install base this is documented rather than engineered around.

Rejected alternatives:

- **Delivering `release.json` inside the release archive**, so launchers
  predating the copy step still receive the metadata. The zip is pure
  `git archive` output — the only producer that expands the `version.txt`
  stamp — so injecting a generated file means the release job post-processes
  the archive and a second identity artifact must be validated before
  publish. Its only beneficiary is the out-of-support path above. Rejected
  with that boundary, not forever: if the boundary widens, this is the
  mechanism to revisit.
- **An update-availability check on the page** ("newest release is vX"). It
  needs a network call from a page that makes none, plus policy decisions
  (when to check, what to cache) that nothing here requires. Out of scope,
  not rejected forever.
- **A multi-entry `install.json`** with per-version records and an `is_active`
  flag — already recorded, and still rejected, in the entry linked above.

Deliberately not shown: the update policy (automatic, or pinned to a tag). It
is a cheap manifest read, but it only repeats a fact the user set themselves
via the installer; skipped until asked for.

## 2026-08-02: A Committed Side Effect Reports Its Outcome Even When A Later Write Fails

Status: Accepted

Saving a preference to disk can fail — on Windows, antivirus or the search
indexer can hold a file open long enough to defeat the retries. When that
happens partway through an action the user already triggered, the app used to
abandon the whole response, so the screen said nothing at all. Two rules now
govern that: a screen must never keep showing a success message for a write
that failed, and an action whose real work already happened must still tell
the user it happened. In practice, importing a playlist that cannot be marked
visible now shows an orange notice saying the playlist was imported and how to
unhide it, and deleting a playlist still confirms the deletion.

Decision — two rules for a failed store write inside a callback:

1. **No stale success claim.** A UI that prints a success claim must not keep
   printing it after a failed write. A silent optimistic UI that reverts on
   its own may keep propagating. (Adjudicated during the PR #183 review;
   implemented there in `bae99a5` on the settings page, and first recorded
   here.)
2. **A committed side effect reports its outcome**, even when a later step
   fails. The rule above is about a false claim; this one covers the absence
   of any claim after an irreversible operation has already succeeded.

Mechanism: the handling is page-local `try/except OSError` at the call site
(`PermissionError` is a subclass). `replace_with_retry` re-raising after
exhausted retries stays the store contract, and the three writers in
`playlist_visibility_service.py` keep propagating with unchanged signatures —
a store-wide no-propagation policy was considered and deferred, since it would
force a UI answer for the toggle, where the right answer is "show nothing".
The write-before-cache ordering in those writers is load-bearing: a failed
write leaves the in-memory set holding the old value, so a retry still writes.

Per call site in `source/pages/playlists.py`:

- **Toggle** (`update_playlist_visibility`) — propagates, unchanged. Nothing
  is committed and no claim is printed; the cell renders purely from
  server-supplied state, so a failed request leaves no wrong icon on screen
  and the next click retries. Pinned by a regression test so a future
  catch-all cannot quietly change it.
- **Import** (`import_playlist`) — reports the split outcome. The playlist
  file is already on disk, so every output matches the success path (refresh
  bumped, modal closed, field cleared, warmup still enqueued) and only the
  toast changes: orange, under its own id, saying the import succeeded and
  naming the label and canonical code, then that the playlist could not be
  marked visible and how to surface it. Generic "import failed" wording is
  forbidden here — it would be a false statement, the exact defect this
  fixes.
- **Delete** (`confirm_delete_playlist`) — logs the failure and shows the
  ordinary green "Playlist Deleted" toast, deliberately with no split-outcome
  message. This `hide_playlist` is membership bookkeeping (pruning the deleted
  code from the shown set) and its failure has no observable consequence: the
  row is gone either way, a dead code renders nowhere, and the residue
  self-heals if the code is re-imported, because "importing is the intent to
  see" early-returns on an already-shown code. Reporting it would be noise
  about internals. The user-visible fix is that the request no longer fails,
  so the retry that produced a red "Playlist Delete Failed" toast for a
  *successful* delete never happens.

Reachability, so nobody re-derives it: import can only hit the write once a
visibility file exists — with no file, the shown set is seeded from the user
root, which already contains the just-imported playlist, so `show_playlist`
early-returns. First-run installs are immune; steady state is not. Delete only
writes when the playlist was visible.

Provenance: the PR #183 review and commit `bae99a5` (rule 1), and PR #185
(rule 2 and the playlist call sites).

## 2026-08-02: User Settings Live In An App-Owned Store With A Settings Page

Status: Accepted

Where the KovaaK's stats live, the KovaaK's username, and the Steam ID have
moved out of the hand-edited configuration file into a small file the app
owns and writes. A Settings page inside the app shows and changes all three,
so ordinary use no longer needs a text editor. The configuration file keeps
only what a person genuinely sets by hand, such as the port. An update never
blocks on editing that file: keys a release no longer knows about are named
in one warning and ignored.

Decision — **one home, one writer**: every parameter lives in exactly one
file, and every file has exactly one owner. `config.toml` is human-owned and
app-read-only. `data/settings.json` is app-owned and written only through
`source/config/settings_service.py`, whose mechanics mirror the playlist
visibility store (module `RLock`, in-process cache, temp file + `fsync` +
`replace_with_retry`, tolerant reads). Nothing else ever writes it — the
installer included.

The schema is flat, three string keys, no `schema_version`, no nesting.
(**Superseded on the `schema_version` point only** by the 2026-08-11
durable-store stamp entry: the file now carries a top-level integer
`schema_version`, unknown keys are invalid rather than ignored, and an
unusable file no longer rewrites itself on the next automatic write. The flat
three-key schema and the unset semantics below are unchanged.)
Unset semantics are deliberately flat too: a missing key, an empty value, and
a missing, unreadable, or malformed file all mean *not configured* — no
identity disables rank lookups, no usable `stats_dir` runs the app empty. A
malformed file is warned about once, treated as holding no keys, and rewritten
whole by the next *user-initiated* save (which copies it aside first); it is
never fatal. Hand-editing while the app is
stopped stays a legitimate escape hatch, but edits made while it runs are not
picked up, because reads are cached in-process. Only the bootstrap in the next
entry distinguishes an absent key from an empty one.

`ConfigData` therefore drops all three fields and `example.toml` drops their
entries; the installed `config.toml` is `port` only. **Unknown `config.toml`
keys are warn-logged and ignored** — a permanent design choice, not a
transition shim. It is the removed-field mirror of the update contract's
"releases must read older state" rule, and it is what makes every promotion
boundary and every rollback safe by construction: a config carrying retired
keys runs on both the outgoing and the incoming version. The governing rule
follows from it — **through any promotion boundary, `config.toml` stays in a
shape both versions can read, and cleanup happens only after promotion**. (An
earlier revision claimed pydantic rejected unknown keys and would fail startup
on an unmigrated config; that behavior never existed, and the warning replaces
the imagined typo protection with visible, non-fatal feedback.) Migration is
manual and never blocks an update, per the single-user no-compat-shims
convention: there are no in-app migrations.

The page at `/settings` edits the three values with one Save. The write is
all-or-nothing — any field error writes nothing, so the store never holds half
a form — and a successful save writes every key, empty string included, which
is what keeps "cleared" distinguishable from "never set". Validation is
offline only: `stats_dir` must be an existing directory or empty, and
`steam_id` must be shaped like a SteamID64 (17 ASCII digits at or above the
universe-1 base `76561197960265728`, tightened from digits-only as the arc
shipped, because an account ID or a SteamID3 fragment is digits too). The
username is free text; confirming it against KovaaK's is detection territory
and belongs to a later proposal. The form is built per visit from the stored
view rather than the pinned accessors, so it always shows what is on disk. A
write that fails is caught and reported in the status line rather than
escaping into a request the user cannot see. State-writing page callbacks are
`n_clicks`-guarded with a None-trigger regression test, because under
DashProxy a callback can still fire once on page load despite
`prevent_initial_call`.

Provenance: distilled from `docs/settings_store_and_page_proposal.md`
(proposed in PR #171, register R1–R8, amended twice during review), shipped in
PRs #181, #182, #183, and #184; the proposal file is deleted in the shipping
PR and git history holds its full text.

## 2026-08-02: Restart-Scoped Settings Are Pinned At Boot, And The Stats Folder Finds Itself

Status: Accepted

The app no longer has to be told where the KovaaK's stats folder is. On a
start with nothing ever configured it looks the folder up the way the
installer used to, stores what it finds, and uses it immediately. Settings
that cannot safely change under a running app are frozen when it starts, so a
saved change either applies at once or the Settings page says a restart is
needed. The app also starts and serves with no stats folder at all, showing
empty pages and a hint instead of refusing to run.

Decision — **restart-scoped values are pinned, not re-read.** `stats_dir` is
resolved once by server startup (`resolve_stats_dir`) and every consumer reads
that pin (`get_usable_stats_dir`); a per-operation read would let a mid-run
save move half the app to a new directory while the watchdog and the runs
already in memory stayed on the old one. Whether the directory is usable is
decided as part of that resolution, not per call, so a directory that appears
mid-run — a network library coming online — cannot half-enable an app whose
scan and watchdog were already skipped. A pin that was never resolved (tests,
imports, any entry point that is not the real startup) reads exactly like an
unset value.

Identity is pinned as a **pair**, frozen by the first read that observes a
configured username. Reading both fields together is what stops a lookup from
straddling a save and resolving one player's rank into another's cache entry.
Staying live until that first non-empty read is what lets a first-time
identity set apply without a restart; a later change is restart-scoped
instead, because the warmup worker keeps the context it started with and the
caches it fills are scoped to one identity per process. `is_restart_pending()`
derives the Settings page's notice by comparing the store against both pins,
so the notice describes reality for every consumer and stands until the
restart actually happens. It is derived, never stored. Its look, unruled here
and shipped as orange text, is set by the
[2026-09-15 setup-hints entry](#2026-09-15-setup-hints-wear-the-notice-anatomy);
its trigger and its derivation are unchanged. The app never restarts
itself, and there is no live re-initialization of the watchdog, the warmup
singleton, or the in-memory data — that machinery is the riskiest code this
arc could have contained, and a restart costs one console close and a shortcut
click.

**The app starts without a usable stats directory.** Unset, and set but not an
existing directory (the moved-library case), behave identically: startup skips
the initial scan and the file watchdog, logs one line naming what was
configured, and serves — only `port` is needed to serve pages. Home shows a
hint linking to the settings page. The `SystemExit` that used to guard this is
gone.

**`stats_dir` bootstraps app-side**, replacing the detection deleted from the
installer (see the 2026-08-02 addendum on the 2026-07-19 installer entry
below, which this supersedes for stats-directory detection). On startup with
the key **absent** — a missing file counts — the app collects Steam's install
roots from the registry (`HKCU` `SteamPath`, then both `HKLM` `InstallPath`
views, every hit kept), treats those roots as libraries, adds every `"path"`
value from each root's `steamapps/libraryfolders.vdf`, and probes
`<library>/steamapps/common/FPSAimTrainer/FPSAimTrainer/stats` per unique
library. The first existing directory is written through the settings service,
merged with whatever is already stored. The bootstrap runs before the pin
above, so a first detection serves the boot that made it. A miss writes
nothing and is retried on the next start, so a dashboard installed before
KovaaK's self-configures once KovaaK's appears. A present-but-empty value is
never overridden: that is the user saying "run without run data" on the page,
and the page writes every key on every save precisely so this distinction
survives.

The pick is silent — no confirmation step. On a machine with a stale copy in a
second Steam library it can be wrong, which is immediately visible (empty or
wrong data), fixable on the settings page, and properly solved by the
follow-on proposal's candidate dropdown. The page shipping first is why the
silent write is acceptable at all: the repair surface precedes it.

The vdf is read with the installer's flat `"path"\s*"([^"]*)"` regex,
unescaping `\\`, rather than with the `vdf` PyPI package: no new dependency
for a file read once per start, the upstream package is unmaintained, and the
regex ignores the file's structure by design. It harvests the per-library
object format Steam writes today; a pre-structured file (numeric key to path)
contributes no extra libraries, exactly as the installer behaved, and the
Steam roots themselves are still probed. An unreadable or malformed vdf is
logged and skipped, never fatal. The bootstrap runs only from the real server
startup path, never at import, and the registry read is isolated in one
function so no test ever touches the real registry.

Provenance: same proposal and delivery arc as the entry above (PR #171;
PRs #181, #182, #183, #184).

## 2026-08-01: Doc-Style Follow-Up — Decisions Needed, Roadmap Trim, No Log Index

Status: Superseded in part by the
[2026-09-28 no-backfill entry](#2026-09-28-no-backfill-covers-missing-summaries-not-broken-ones):
the sentence "No backfill: existing entries convert only when a change touches
them anyway" no longer holds. An entry with no summary still waits for a
payload edit, but a summary that breaks the rules is a defect, fixed on its
own commit. Superseded in part also by the
[2026-09-30 sentence-count entry](#2026-09-30-the-docs-test-counts-summary-sentences-and-its-count-is-the-definition):
the test now gates the summary sentence count, as it counts them, so "the test
never judges prose quality" no longer holds for that count. The PR #174
settlement still holds for Markdown rendering fidelity. Everything else here
stands.

The proposal section listing what the maintainer must rule on is renamed
from "Decision points" to "Decisions needed", so the heading itself tells
you whether a document wants your attention. This entry now carries the
complete doc-style rules and replaces the original entry below. The
roadmap keeps only the few most recently shipped milestones instead of a
full history. A topic index for this log was considered and rejected.

Decision — the complete two-layer doc style (supersedes the entry below;
the only rule change is the section rename, everything else carries
forward unchanged):

- Durable docs are layered. Layer 1 (maintainer): every new or
  materially-edited `decision_log.md` entry — and every `docs/specs/`
  file, once that layer exists — opens with a 2–4 sentence
  plain-language summary (one idea per sentence; no cross-references,
  file paths, or embedded enumerations). Layer 2 (agents): the dense
  payload follows, written as before — compression there is a feature.
  The summary is written, updated, and reviewed in the same PR as its
  payload, by the same author. No backfill: existing entries convert
  only when a change touches them anyway.
- Proposals follow the template in `AGENTS.md` ("Proposal template"):
  `Status:` → `## TL;DR` → `## Decisions needed` → `## Problem`, dense
  body per-proposal after that (Design is the normal next section but
  may be replaced by more specific ones). Renaming "TL;DR" to "Summary"
  was considered and deliberately not done.
- Decisions needed carries only choices requiring maintainer product or
  workflow judgment, or acceptance of a costly-to-reverse trade-off,
  each with a recommended answer and the material consequence of
  choosing differently; the author owns mechanical, reversible, and
  evidence-resolvable choices.
- `tests/test_docs.py` enforces the leading section order mechanically
  (placement, not just presence). The layer-1 prose rules are writing
  guidance held by same-PR review — the test never judges prose quality
  or Markdown rendering fidelity (settled across the PR #174 review
  rounds).
- `docs/product.md` is exempt — its *Problem solved:* format already
  leads with the user-facing statement.

Why (unchanged from the superseded entry): the docs pipeline optimizes
for agent readers — distillation is compression — while the maintainer,
now primarily a reader and decider with agents doing most
implementation, pays the skim cost. Layering serves both without
compromising either, and the decision filter attacks the number of
escalations put in front of the maintainer, not just their
discoverability.

Roadmap policy: the Shipped section keeps only the ~5 most recent
milestones, newest first, and older entries leave the file entirely —
the shipping checklist already lands their user-facing rationale in
`product.md` and their technical rationale here, and git history holds
the full sequence.

Rejected: a topic index at the top of this log (reviewer suggestion once
the log passed ~1,500 lines). The planned `docs/specs/` capability layer
links the relevant log entries per capability and is the intended
findability fix; a hand-maintained index would duplicate it as a third
structure, touched in every shipping PR and verified by nothing. Revisit
only if findability still hurts after capability specs land.

Provenance: the two-layer rules were established via
`docs/doc_style_proposal.md` (PR #174; two external review rounds;
proposal deleted per "Shipping a proposal" — git history holds the full
text). This entry restates them in full with the post-merge follow-up
refinements (external reviewer suggestions, maintainer-ratified scope:
rename yes, "TL;DR" kept, trim yes, index no) and supersedes the
original entry below.

## 2026-08-01: Durable Docs Open Plain And Proposals Lead With Decisions

Status: Superseded — replaced by the follow-up entry above (section
rename; all other rules carried forward there in full)

Docs now serve their two readers in layers instead of forcing one register
on both. Every new decision-log entry opens with a short plain-language
summary, like this paragraph, before the dense detail. Proposals open with
a summary and a filtered list of the decisions that genuinely need the
maintainer, and the docs test enforces that order. The dense record itself
is unchanged.

Decision: durable docs are layered. Layer 1 (maintainer): every new or
materially-edited `decision_log.md` entry — and every `docs/specs/` file,
once that layer exists — opens with a 2–4 sentence plain-language summary
(one idea per sentence; no cross-references, file paths, or embedded
enumerations). Layer 2 (agents): the dense payload follows, written as
before — compression there is a feature, not a bug. The summary is
written, updated, and reviewed in the same PR as its payload, by the same
author. No backfill: existing entries convert only when a change touches
them anyway.

Proposals follow the template in `AGENTS.md` ("Proposal template"):
`Status:` → `## TL;DR` → `## Decision points` → `## Problem`, dense body
per-proposal after that (Design is the normal next section but may be
replaced by more specific ones). Decision points carry only choices
requiring maintainer product or workflow judgment, or acceptance of a
costly-to-reverse trade-off, each with a recommended answer and the
material consequence of choosing differently; the author owns mechanical,
reversible, and evidence-resolvable choices. `tests/test_docs.py` enforces
the leading section order mechanically (placement, not just presence);
prose quality is held by same-PR authorship and review, not tests.
`docs/product.md` is exempt — its *Problem solved:* format already leads
with the user-facing statement.

Why: the docs pipeline optimizes for agent readers — distillation is
compression — while the maintainer, now primarily a reader and decider
with agents doing most implementation, pays the skim cost. Layering serves
both without compromising either, and the decision filter attacks the
number of escalations put in front of the maintainer, not just their
discoverability.

Provenance: distilled from `docs/doc_style_proposal.md` (two same-day
external review rounds), committed and then deleted in the shipping PR —
git history holds the full text.

## 2026-08-01: No Username Stays Fully Offline — User-Independent Totals Rejected

Status: Rejected

Decision: an empty `kovaaks_username` keeps its documented meaning — the app
runs fully offline and no leaderboard feature makes network calls. The
proposal to resolve leaderboard IDs and show Total Players without a
configured username (PR #166, split out of the leaderboard-ID seeding
proposal) was reviewed independently twice and closed as not planned.

Why:

- The README promises that leaving the username empty runs the app fully
  offline, and today the rank service short-circuits before any network call.
  The proposed lazy per-scenario totals fetch at playlist open would silently
  break that zero-network contract.
- A board's population without the user's position or percentile answers none
  of the product's core questions ("am I improving? where am I weak?") — it
  fills a grid column, not a need.
- The proposal understated the plumbing: `_with_leaderboard_total` rejects
  non-RANKED/UNRANKED results by design, and the progressive-fill accounting
  counts UNKNOWN rows as unavailable positions, so username-less playlist
  opens would fetch totals and still end in red "positions unavailable"
  messaging unless both grew new semantics.

What survives: the leaderboard-ID seeding (PR #169, previous entry) stands on
its own merits. The worthwhile kernel — treating "leaderboard features off"
as a normal quiet state rather than a red error, skipping the futile
progressive position fill, and pointing at how to enable the features — is
deferred until a settings page exists to give that pointer a destination
(settings/config work proposed in PR #171, not yet agreed as of this
writing). The optional import-warmup companion (prefetching
unplayed scenarios of a freshly imported playlist) is dropped with the
proposal; revisit only if the import-then-open flow proves slow in practice.

## 2026-07-20: Seed Leaderboard IDs From The Bundled Benchmark Corpus

Status: Accepted

Decision: the benchmark importer embeds each scenario's KovaaK's
`leaderboard_id` — from the `/benchmarks/player-progress-rank-benchmark`
payload it already fetches — into every generated playlist JSON, and the app
folds those embedded IDs into the permanent name->ID mapping cache at startup.
The scenario schema field is optional (`Scenario.leaderboard_id`, default
`None`) so imported and pre-change files keep validating, and the runtime
lookup path (`get_cached_leaderboard_id`) is unchanged.

**The corpus is the seed.** The IDs live in the same files as the scenario
names, so every corpus lifecycle rule (staging, review, activation, retention)
applies to both automatically — the shipped corpus and the shipped IDs cannot
diverge because they are one artifact. There is no aggregate seed file.

**Startup merge against the asserted set.** The existing full-corpus scan now
also collects the embedded `scenario name -> leaderboard_id` pairs. Names two
bundled files disagree on are excluded with a warning; the survivors form the
*asserted set*. The merge is one atomic read-modify-write of the mapping cache:

- an asserted name missing from the cache is added, tagged `source: "seed"`;
- a seed-owned entry whose asserted value changed is refreshed, so corrected
  IDs reach existing installs;
- a seed-owned entry whose name is no longer asserted is removed, so an
  upgraded install never resolves a mapping a fresh install would not;
- entries learned from the live API are never touched, and a name that already
  has a learned entry never gets a seed-owned row.

If any bundled file fails to load, the merge still adds and refreshes but
suppresses removals — a partial view of the corpus must not retract mappings it
may still assert.

**Regeneration mechanic.** The generated-file provenance carries a
`schema_version` marker (`generated_from.schema_version`), bumped when the
generated schema changes. `should_skip_generation` then treats a file written
under an older schema as stale, so a plain importer run regenerates the whole
corpus through the benchmark payload cache — without `--force`, which would
refetch every payload live.

Why: resolving a scenario name to its leaderboard ID was treated as
user-dependent, and it isn't. The bulk mapper (total-play hydration) only
returns *played* scenarios, so every unplayed playlist scenario fell through to
the exact-name search endpoint (`/scenario/popular`) — the slowest,
most timeout-prone call in the app's KovaaK's surface, one call per scenario —
and a username-less install could not resolve IDs at all. Shipping the IDs with
the corpus makes first opens of unfamiliar bundled playlists fast and
identity-free.

Accepted limitation: if KovaaK's ever re-uploads a scenario under the same name
with a new leaderboard ID, a *learned* cache entry keeps winning until it is
deleted — seed-owned entries are refreshed by the merge, so only learned rows
can pin a stale value. Escape hatch: delete the mapping cache file; the next
startup re-merges the bundled IDs.

Corpus coverage is CI-enforced (`tests/test_playlist_rekey.py`): every scenario
of every tracked `resources/benchmarks/*.json` carries a non-null
`leaderboard_id`, with an exception list that ships empty.

## 2026-07-19: Releases Are Automated CalVer Tags Cut By CI

Status: Accepted

Decision: every push to `main` that changes anything an installed copy runs
publishes a GitHub Release tagged `vYYYY.MM.DD` (`.N` suffix for same-day
repeats). No human picks a version number or judges whether a commit "deserves"
a release. The job lives in `.github/workflows/ci.yml` with `needs: test` — a
commit that fails the gates never becomes a release — and the logic is in
`scripts/release_job.py`.

The skip rule is a **blocklist** (`docs/`, `tests/`, `.github/`, any `*.md`,
`.gitignore`, `.pre-commit-config.yaml`), not an allowlist, because the failure
directions are asymmetric: a redundant release is only noise, while a missed
release strands distribution inputs — `install.ps1`, the launcher,
`example.toml`, `.python-version`, `.gitattributes` — at an older tag. When in
doubt, release.

Two properties the job must keep:

- **The Latest invariant.** Concurrent pushes serialize through a fixed
  concurrency group (`cancel-in-progress: false`, `queue: max`), but that
  serialization is FIFO by wait-start time, not by source order — a newer push
  with faster tests can enter the critical section first. So inside it the job
  checks ancestry (`git merge-base --is-ancestor`) against published releases
  and passes `make_latest: false` when a published release descends from its
  own SHA. `make_latest` defaults to true, so without this an older commit's
  slow run would silently downgrade every `latest`-tracking install. After
  claiming Latest, the job asserts `releases/latest` really resolves to its tag.
- **Idempotency across every partial-failure state**, not just
  tag-without-release: a rerun reuses a tag already pointing at `HEAD` and
  *resumes an existing draft* (re-attaching assets) rather than creating a
  second release.

The zip asset is built by `git archive`, the only producer that expands the
`export-subst` stamp — zipping a checkout would ship `version.txt` unexpanded.
A second, tiny asset (`release.json`) carries the tag, full SHA, commit date,
and that release's uv and Python pins, so the installer and launcher never parse
TOML from PowerShell or spend an extra API call resolving the exact SHA
(`releases/latest` reports `target_commitish`, which may be a branch name).

Why: the maintainer explicitly does not want per-commit SemVer judgment, and the
app has no API consumers to justify SemVer semantics. Market research across
fast-shipping projects (yt-dlp, Path of Building Community, RuneLite, and
FFmpeg's binary channels) found dated, immutable, retained artifacts to be the
baseline even for daily-or-faster shippers, and found no comparable project
shipping *unidentified* builds from a branch tip — tags are load-bearing for
rollback and support.

Provenance: this entry and the six below distill the release, versioning, and
distribution proposal added in PR #150 and deleted once shipped (git history
holds the full text). It went through four external design-review rounds plus
the market-research run summarized above, and was implemented in PRs #154,
#155, #158, #159, and the activation PR that removed it.

## 2026-07-19: Releases And Their Assets Are Immutable

Status: Accepted

Decision: GitHub's immutable-releases setting is enabled on the repo, so tags
and releases cannot be moved or deleted. The release job therefore creates a
tag, then a **draft**, attaches assets, validates them, and only then publishes.

Why: rollback is only trustworthy if `v2026.07.19` means the same bytes forever;
a movable tag makes "go back to the version that worked" meaningless. The
setting is not retroactive, which is why it was flipped *before* the release-job
PR merged — that merge cut the first release, and a release published while the
setting was off stays mutable forever.

The consequence to remember: assets lock at publication, so validation must run
pre-publish. After an immutable release is published it is too late to fix a bad
asset — the only remedy is another release. This is what forces the draft-first
flow above; do not "simplify" it into publish-then-attach.

Launcher-side checksum verification is deliberately deferred: HTTPS to
github.com is the trust anchor at this audience size.

## 2026-07-19: Build Identity Comes From The Manifest, Corroborated By The Stamp

Status: Accepted
Superseded in part: 2026-08-02 (PR #188) added a release-file layer above the
manifest and retired the accepted `tag: None` consequence recorded below.
Every other decision in this entry stands.

The app works out which release it is running by reading files left beside the
code and in the install directory, never a version string committed in the
source. Each of those files is trusted only when it agrees with the stamp that
ships inside the downloaded code, so a half-finished update cannot make a new
build report the old version. Since 2026-08-02 the installer and launcher also
leave a copy of the release description next to each installed version, which
is what lets a freshly updated app name its own release right away. Someone
updating the app now sees the right version reported from the first session
rather than a session later. Where they see it is the settings page, which
since 2026-08-02 shows the running version; the header GitHub link's tooltip
used to carry it and no longer does.

Decision: one reader (`source/utilities/build_info.py`) resolves the running
build's identity, and every user-visible build string derives from it. The
precedence is manifest → expanded stamp → git → `unknown` (a release-file
layer was added above the manifest on 2026-08-02; see the end of this entry):

1. **`install.json`** — the install manifest, written atomically by the
   installer/launcher into the state root, never by the app. The only layer that
   can know the release *tag* — until the 2026-08-02 copy, which carries it too.
2. **`version.txt`** — committed with git `export-subst` placeholders
   (`sha: $Format:%H$`, `commit-date: $Format:%cs$`) plus a `.gitattributes`
   entry. GitHub's archive endpoints run `git archive`, which expands them, so
   any zip download carries its full SHA and commit date.
3. **git** — if the placeholders are unexpanded, this is a checkout, so ask it.

The manifest is authoritative **only when it corroborates the running code**:
its `sha` must equal the SHA in the expanded stamp sitting beside that code. The
manifest describes the install's *state*, not any one code directory, so during
a staged update it still names the previous version while the new one is already
running. Unconditional manifest-first precedence would make the new build report
the old identity — and the launcher's own promotion check would then reject it
forever. This was found by the Codex review of PR #154, during implementation,
against a frozen design.

Accepted consequence: a freshly promoted version reports `source: "archive"` and
`tag: None` until the next launch. SHA and date still identify it exactly, and
the tag↔SHA mapping is public in the releases.

**That accepted consequence is superseded (2026-08-02, PR #188).** The
installer and the launcher now copy the release's `release.json` verbatim into
`versions/<tag>/` at stage time, and `build_info.py` reads that copy ahead of
the manifest under the same corroboration rule, reporting
`source: "release-file"`. The copy is written before the staged version ever
runs, so it cannot lag the code it sits beside: a trial build names its own tag
from its first session. The precedence above gains that file at the top and is
otherwise unchanged — the manifest remains the fallback for version directories
staged without a copy, which is how an install still on a pre-copy release
degrades for exactly one update cycle (documented, not engineered around, under
the single-user support boundary).

`version.txt` is deliberately plain `key: value` text rather than JSON: the
committed file needs a comment header (a raw placeholder looks broken to anyone
browsing the repo), and `export-subst` output is not JSON-escaped, so a JSON
envelope would silently constrain future placeholders to escape-safe expansions.

Identity surfaces in three places: a startup line in `data/logs/debug.log`
(bug reports arrive with the log), the `/health` endpoint, and — since
2026-08-02 (PR #190) — a version section on the settings page.

**That surfaces list is corrected and superseded (2026-08-02, PR #190).** It
originally named the header GitHub icon's tooltip and the browser title, and
rejected an app-settings page as spending permanent space on a string read
once per bug report. Two changes:

- The tooltip suffix is gone; the label is a plain "View this app on GitHub"
  again. Hanging version information off a hover on a repo link is an
  affordance failure — it was a stopgap chosen only because no page existed to
  own the display, and the settings page (PRs #181–#184) now does. The
  space objection died with it: the section costs nothing on a page the user
  opened deliberately.
- The browser-title claim was factually wrong. Dash Pages sets a per-page
  title on every navigation, so `document.title` never carried build identity
  in practice. The tab title stays deliberately unversioned — the correction
  is to this claim, not to the title.

Why not have CI commit a version file on every push: the commit changes the SHA,
so the file always describes its own parent; it doubles commit traffic; and it
forces constant fetch friction for the maintainer and for parallel agent
sessions. `export-subst` needs no commits and is never stale.

## 2026-07-19: All Mutable State Lives Under An Explicit State Root

Status: Accepted

Decision: `CSD_STATE_DIR` names the directory holding every mutable file —
`config.toml` and everything under `data/` (playlists, logs, preferences,
caches). Unset means the current working directory, so dev checkouts behave
exactly as before. Bundled read-only assets (`resources/benchmarks`) stop
resolving from the working directory and resolve relative to the installed
package instead, since they ship with the code. `source/utilities/paths.py`
centralizes both rules.

Why: without this split, versioned code directories cannot work at all. Running
the app from a fresh version directory would lose `config.toml` and `data/`;
running it from the state root would lose `resources/benchmarks`. An environment
variable keeps the contract explicit and testable, and lets the launcher — not
the app — own the choice of directories. (An early revision of the proposal
claimed the installer needed zero code changes; that claim was wrong and the
external review killed it.)

## 2026-07-19: The Installer Brings Its Own Toolchain, App-Locally

Status: Accepted

Installing the dashboard is one PowerShell command, and it brings everything it
needs with it: its own Python, its own package manager, the app, and a
first-run configuration file. Nothing outside the install folder is used or
disturbed, so uninstalling is deleting that folder and the desktop shortcut.
Installs ask no questions — as of the 2026-08-02 addendum below, the generated
configuration carries only the port the dashboard serves on, and where the
KovaaK's stats live is the app's own business.

Decision: installation is a PowerShell one-liner that fetches `get.ps1` from
`main`. That shim is deliberately trivial and permanently backward compatible —
resolve the latest release, fetch *that release's* `install.ps1`, run it,
nothing else — so the installer is always exactly the same age as the payload it
installs. Without the split, any installer change that merged ahead of its
release would run against a payload whose layout it no longer matched, and would
stay broken indefinitely if a release job failed.

The installer puts the **entire toolchain** under the install root
(`%LOCALAPPDATA%\CorporateSerfDashboard` by default): `UV_UNMANAGED_INSTALL`
places uv in the tree and it is invoked by absolute path,
`UV_PYTHON_INSTALL_DIR` plus `--managed-python` keep a managed CPython there
instead of silently selecting whatever Python the machine has, and
`UV_CACHE_DIR` keeps the cache inside too. No Python, uv, or registry state
outside the root is used or disturbed, so uninstall is deleting the folder and
the shortcut. Two files are written outside it by design: the desktop shortcut
itself, and `get.ps1`'s copy of the installer at
`%TEMP%\csd-install-<tag>.ps1`, which is inert once the install finishes and is
deliberately not cleaned up (the shim stays trivial); the README documents
deleting it.

The uv version is **per release, not per install**: installer and launcher read
the target release's `release.json` and provision that exact uv before syncing.
An install-time-frozen uv would brick the first update that bumps the pin — the
old binary rejects the new project, and `UV_UNMANAGED_INSTALL` disables uv
self-update — so the toolchain upgrade must ride the same transaction as the
code.

First run does not merely copy `example.toml`, whose `stats_dir = "Change me!"`
placeholder would crash the first launch. The installer locates the KovaaK's
stats directory itself (Steam's registry `InstallPath` plus
`libraryfolders.vdf`), confirms it with the user, validates that it exists, and
writes it into `config.toml`. It then **round-trips the generated config through
the installed app's own `load_config()`** and aborts loudly on failure, before
writing the manifest or creating the shortcut. Validating with `tomllib` alone
would only prove the file is syntactically TOML; the app's loader also proves
the schema is one the app accepts. A config the app cannot load must fail the
install loudly rather than surface later as a permanently broken first launch —
permanent because existing `config.toml` and `data/` are never touched again.

Why: the user's machine needs exactly one bootstrapped tool, acquired the way
rustup and uv themselves are distributed. Python and git are never
prerequisites. PyInstaller was rejected: unsigned executables trip SmartScreen
and AV heuristics (fatal for a gaming audience's trust), signing is a recurring
cost, every release would become a large re-download, and bundling
dash/plotly/dash-ag-grid assets under PyInstaller is a known hook-debugging time
sink. Revisit only if "run one command" ever becomes too much to ask.

Addendum (2026-07-20): the first-run `config.toml` now writes only the two
required fields, `stats_dir` and `port`. `polling_interval` (1000) and
`sens_round_decimal_places` (1) gained code defaults on `ConfigData`, so they
are no longer required fields and no longer seeded into the generated file —
`example.toml` still documents them for anyone who wants to tune them. The
round-trip through the installed app's `load_config()` still runs and must pass
with the two-field file.

Addendum (2026-08-02): the stats-directory detection, the `[Y/n]` confirm, the
manual-entry retry loop, and the stats-directory `Stop-Fatal` are all deleted,
so **installs are fully non-interactive** and the generated `config.toml` is
`port` only. `stats_dir` now lives in the app-owned `data/settings.json`, which
the installer never touches — one home, one writer — so its detection had
nowhere legitimate left to write: a `stats_dir` line in `config.toml` would only
be warn-logged and ignored. The app absorbs the consequences instead of the
installer: it starts and serves without a usable stats directory (initial scan
and file watchdog skipped, one log line naming what was configured, a hint on
Home — plain text until the settings page shipped, a link to it since), and an
app-side startup bootstrap that re-detects the directory
follows in the same proposal. Between the two, a fresh install runs empty until
the directory is set by hand. That bootstrap has since shipped — see the
2026-08-02 pinning-and-bootstrap entry, which supersedes this addendum on
stats-directory detection. The `load_config()` round-trip through the
installed app is unchanged and still gates the install, now against the
one-field file.

## 2026-07-19: PowerShell Writes UTF-8 Without BOM And Forward-Slash Paths

Status: Accepted

Decision: every machine-readable file written by the install/launch scripts
(`config.toml`, `install.json`, the `launch.ps1` bootstrap) is written UTF-8
**without** a byte-order mark, via `System.Text.UTF8Encoding($false)`, and every
path inside them uses forward slashes. The scripts target Windows PowerShell
5.1 — the shell the one-liner actually lands in on a stock Windows 11 machine.

Why: 5.1's `-Encoding UTF8` emits a BOM, and this repo's Python 3.14 `tomllib`
rejects both a BOM and raw `\` in TOML basic strings. Either alone yields a
config the app can never parse, which the never-touch-an-existing-config rule
would then make permanent. Both halves were verified empirically against this
repo's interpreter rather than taken from documentation.

This is a contract, not a style preference: do not "modernize" these writes to
`Set-Content -Encoding UTF8`, and do not let Windows-native backslashes reach a
generated TOML file.

## 2026-07-19: Updates Are Staged, Reversible, And Speak A Frozen Wire Contract

Status: Accepted

Decision: the desktop shortcut targets a stable bootstrap at the install root
(`launch.ps1`) that reads the manifest and delegates to the selected version's
launcher — nothing else. Per-tag directories get pruned (keep last two), so the
shortcut must never point into one. When the bootstrap itself must change, the
versioned launcher replaces it on a higher embedded marker by writing a
same-directory temp file, validating its marker and PowerShell syntax, then
renaming over it. Never truncate the live file in place: PowerShell keeps
executing the already-parsed body, so an interrupted in-place write leaves a
working session now and a bricked entrypoint for every launch after it.

The launcher is **single-instance** via a named mutex scoped to the install
root, held for the launcher+app lifetime. A second launch opens the browser at
the running instance and exits without updating, syncing, or touching the
manifest — atomic manifest writes protect one file, not a whole transaction.

Then it applies the manifest's policy:

- **`latest`** (default): query `releases/latest` on a short timeout; a
  different tag is downloaded and synced into a new per-tag directory but is
  **not promoted yet**. It starts as a pending activation, and the launcher
  polls `/health` until the child process is still alive *and* the response
  carries the expected full SHA and a per-launch token passed in by environment
  variable. A bare HTTP 200 is not proof of life: an already-running instance or
  an unrelated service holding the port can answer while the pending process
  never bound. Only then is the manifest atomically rewritten. On timeout or
  early exit the launcher starts the previous version and leaves the manifest
  untouched — a crashing release never becomes the recorded install. The gate
  deliberately does **not** require a tag match, because a build on trial is
  still described by the previous manifest and reports `tag: None` under the
  corroboration rule above. Any network or API failure fails open: run what is
  installed, offline-safe.
- **`pinned`** + `pinned_tag`: skip the update check entirely. A rollback
  install (`install.ps1 -Tag ...`) *writes this pin*; without it the next launch
  would immediately reinstall the bad release, making rollback a no-op. Undoing
  it is explicit: re-run the installer without `-Tag`.

**Wire contract v1.** A pinned or long-offline install may jump from the first
launcher straight to any future release, and the launcher performing that update
is always the *old* one. So everything an old launcher parses is a frozen,
versioned contract from day one: `release.json` and `install.json` both carry
`schema_version: 1`, and the v1 field set froze when the installer shipped.
Changes within v1 are additive-only. A breaking change bumps the version and
dual-publishes the v1 envelope for as long as v1 launchers may exist. A launcher
meeting an unknown `schema_version` — or any parse failure — runs the existing
install and says so loudly ("re-run the install one-liner"), because fail-open
alone would convert a contract break into *silent permanent stranding*: every
launch retries, fails, runs the old version, and never tells the user.

`install.json` deliberately carries **no uv field and no zip-prefix field**. The
launcher takes uv from the new release's `release.json` at update time, and
running the current version needs no uv at all — it starts the synced venv's
`python.exe` directly, which is offline-safe and makes the health gate and the
kill target the real server process rather than a wrapper. The zip's top-level
directory name is **discovered after extraction, never derived**: the named
asset keeps the "v" (`Corporate-Serf-Dashboard-v2026.07.19/`) while GitHub's
source-archive fallback strips it. Both scripts assert exactly one top-level
directory and verify the extracted stamp's SHA before syncing.

Rollback protects *code*; durable state is governed by a rule rather than
machinery. Releases must read older state (missing keys get defaults) and must
not rewrite user-authored files. The durable state is a handful of tiny,
schema-stable files, so a genuine format break is rare enough to be called out
in its PR with a manual step — the house convention at this user-base size.
State snapshot/restore was deferred on that basis.
(**Superseded on the schema-stability point only** by the 2026-08-11
durable-store stamp entry: those files now carry a `schema_version`, a release
that meets an unknown one refuses to write rather than relying on the manual
step alone, and pre-stamp releases are an unsafe rollback target. The
read-older-state and do-not-rewrite-user-files rules, and the deferral of
state snapshot/restore, are unchanged.)

Accepted limitation: a release that fails its health gate is retried in full —
download, sync, then the readiness timeout — on every launch until the next
release lands. Bounded by the near-daily release cadence; the escape hatches are
the rollback pin and waiting for the replacement release. Documented rather than
solved with a failed-tag marker.

## 2026-07-19: The App Binds Its Port Exclusively And Exits If It Is Taken

Status: Accepted

Decision: `source/app.py` creates and binds the listening socket itself
(`bind_server_socket`), sets `SO_EXCLUSIVEADDRUSE` where the platform has it,
and hands the bound socket to waitress as `serve(app.server, sockets=[sock],
threads=8)`. A failed bind prints an actionable message naming the port and
`config.toml`, then exits 1. Do not "simplify" this back to
`serve(app.server, host=..., port=...)` — that reintroduces the bug below.

Why: on Windows, a socket bound with `SO_REUSEADDR` (waitress's default for
sockets it creates) does not reserve the address. A second process can bind
the same `127.0.0.1:<port>` while the first is serving it, and Windows then
splits incoming connections nondeterministically between the two. The visible
symptom is a second copy of the dashboard silently answering some requests
with its own state — observed live during the release-launcher work, where
the launcher's `/health` token gate correctly refused to promote the build
but the user got a 120-second hang instead of an error. It is also the
long-standing "one dev run shadowing another on localhost" trap. POSIX
already refuses the second bind, so the flag is the Windows-only half of a
behavior we want everywhere.

Mechanism, verified against waitress 3.0.2: a socket passed through
`sockets=` is constructed with `bind_socket=False`, so waitress never binds
it, and `accept_connections()` calls `listen()` — hand it over **bound but
not listening**. Waitress then calls `set_reuse_addr()` on it unconditionally;
on an exclusively-bound socket that `setsockopt` fails with `WSAEINVAL`
(10022) and waitress swallows the error, so exclusivity survives. Confirmed
empirically: with the flag set, a second bind of the same port is refused
whether the second binder asks for a plain bind (`WSAEADDRINUSE` 10048),
`SO_REUSEADDR` (`WSAEACCES` 10013), or `SO_EXCLUSIVEADDRUSE` (10048).

Alternatives rejected: probing `/health` for a foreign responder before
binding (racy — the port can be taken between probe and bind — and blind to
non-app squatters like Steam on 8080); a launcher-side check (the launcher
already fails safe on a shadowed health answer, and with this change the
duplicate exits immediately, which its "exited" path already handles).

Scope: the `config.debug` Flask development-server path is unchanged; it is a
dev-only convenience. The bind happens immediately before `serve()`, so a
duplicate instance still does its ~2s of startup work before exiting.

POSIX footnote: binding the socket ourselves means waitress's pre-bind
`SO_REUSEADDR` no longer applies, and on POSIX that flag is what lets a
server rebind a port whose old connections are still in `TIME_WAIT`. A fast
restart there could now be refused. Windows is unaffected — verified that an
immediate rebind succeeds with a genuine `TIME_WAIT` pair on the port. We
accept this because nothing serves on POSIX: the app targets Windows and CI
runs `windows-latest` only. If that ever changes, set `SO_REUSEADDR` before
`bind()` on non-Windows platforms — on POSIX it permits the `TIME_WAIT`
rebind without letting a second live server share the port, so it restores
the old behavior without weakening the Windows guarantee.

Addendum, 2026-07-20: both loopback faces are bound, not just IPv4.
`bind_server_socket` now returns a list — `127.0.0.1` and `::1`, same port,
each claimed with the same `SO_EXCLUSIVEADDRUSE` treatment — and both go to
waitress as `sockets=`. The IPv4-only bind left the decision half-enforced:
on Windows `localhost` may resolve to `::1` first, so an unrelated process
holding the IPv6 face still captured every browser request to
`http://localhost:<port>/` while the dashboard sat unreachable on IPv4.
Observed live during the PR #153 session — another project's server held
wildcard `::` while the dashboard held `127.0.0.1`, and the browser got the
stranger's 404 page. (The squatter was *not* a `config.debug` run of this
app: werkzeug picks the address family with a colon heuristic, so its
`host="localhost"` always binds `AF_INET` `127.0.0.1` — verified against the
pinned werkzeug.) Claiming `::1` ourselves collapses that to the two outcomes
the original decision wanted: a specific bind takes routing precedence over
someone else's wildcard `::`, and if the face is genuinely taken the app
exits loudly instead of being silently shadowed.

Do not "simplify" the two sockets into one dual-stack `AF_INET6` socket with
`IPV6_V6ONLY=0`. That shape does not work here at all: v4-mapped addressing
applies only to wildcard binds, so a dual-stack socket bound to `::1` accepts
no `127.0.0.1` traffic whatsoever. Two explicit sockets are the only correct
shape, and they keep the per-face exclusivity semantics verified above.

Failure semantics stay deliberately two-bucket. Either face already taken
(`EADDRINUSE`) closes whatever was bound and takes the existing exit-1 path,
now with a message saying the port must be free on both addresses — a port
free on only one face is refused outright rather than half-served. IPv6
genuinely absent (`EAFNOSUPPORT` creating the socket, or `EADDRNOTAVAIL`
binding `::1`) logs one info line and serves IPv4 alone; on such a machine
`localhost` resolves to IPv4 anyway, so the ambiguity disappears with the
interface. Re-verified against waitress 3.0.2 that the multi-socket path
gives each socket the same treatment as the single-socket contract above:
`create_server` loops over `adj.sockets` constructing every `AF_INET`/
`AF_INET6` socket with `bind_socket=False`, calls the swallowed
`set_reuse_addr()` per socket, and calls `listen()` per socket in
`accept_connections()`; with two entries it returns a `MultiSocketServer`
driving both from one loop.

## 2026-07-19: Default Port Is 8050, Not 8080

Status: Accepted

Decision: The example config (`example.toml`) ships with `port = 8050`. The
app itself has no built-in default — `port` is a required config field served
through waitress — so the example file is the only default we own.

Why: 8080 is one of the most contended ports on end-user machines; Steam in
particular holds it whenever it is running, and this app's audience is
KovaaK's players, who all run Steam. 8050 is the Dash convention (`app.run()`
default), so it signals "Dash app" to anyone inspecting the port, and its
only common occupant is *other* Dash apps run with defaults — a rare
collision for this audience. No port choice defends against Windows
Hyper-V/WSL2 excluded-port-range reservations, which land semi-randomly;
the `port` config setting remains the escape hatch for any collision.

Migration: none in-app (single-user convention — no compat shims). Existing
installs keep whatever their `config.toml` says; only fresh copies of
`example.toml` pick up 8050.

## 2026-07-18: Accept Dash's First-Request Pages Race Instead of Warming the App

Status: Accepted

Decision: The browser-console noise on the first page load after a server
start — a `TypeError: Cannot read properties of undefined (reading 'apply')`
from `handleClientside`, plus a flood of ~86 "ID not found in layout" entries
in the dev-tools overlay — is a known upstream Dash defect. We accept it and
do not work around it. Treat it as expected baseline noise during browser
checks; reload the page before judging whether the console is clean.

Why: Dash's `enable_pages()` registers its page router as a `before_request`
hook (`dash/dash.py`, in `router_sync`/`router_async`). The hook sets its
`_got_first_request["pages"]` guard flag *before* it finishes its work, and
takes no lock:

```python
if self._got_first_request["pages"]:
    return
self._got_first_request["pages"] = True
...   # builds validation_layout, registers the document.title clientside callback
```

Inline clientside function bodies are injected into the index HTML at render
time. Under a threaded server — Waitress with `threads=8` in production,
Flask's threaded dev server when `debug = true` — a concurrent early request
sees the flag already set, returns immediately, and serves an index page whose
script block is missing, while `/_dash-dependencies` still advertises the
callback. The renderer looks the function up, gets `undefined`, and calls
`.apply` on it. `validation_layout` is populated in the same unfinished hook
body, which is why the "ID not found in layout" flood appears alongside: one
root cause, two symptoms.

Measured 2026-07-18 on dash 4.4.0: eight simultaneous first requests produced
**seven of eight** renders missing the script; every later render has it. A
browser triggers it because it opens several connections at startup.

The missing function is Dash's own `_pages_dummy` `document.title` setter, not
application code — all six of our clientside callbacks register correctly every
time. It is not a dash-extensions defect either: `DashProxy._setup_server`
correctly takes a `setup_server_lock`, and plain `dash.Dash` races identically
(measured: 7/8 for both, in a minimal app with no dash-extensions involved).
It reproduces on dash 4.3.0 and 4.4.0 alike, so it is not a regression from the
PR #146 dependency upgrade.

### Reproducing it requires a wide enough race window

Two conditions must both hold, which is why a casual minimal repro shows
nothing and reports "works fine":

1. **`suppress_callback_exceptions` must be at its default `False`.** When it
   is `True`, Dash skips the whole `validation_layout` block inside the pages
   router (`dash/dash.py`, the `if not self.config.suppress_callback_exceptions:`
   guard) — which is the slow part of the hook. The window collapses to
   near-zero and the race effectively never fires. This app leaves the setting
   at its default.
2. **Page layouts must be expensive enough to matter.** That block calls every
   registered page's layout function to build `validation_layout`. The window
   is as wide as those calls take. A `html.Div("hi")` page closes it instantly;
   this app's real page layouts hold it open long enough to lose 7 of 8 races.
   A minimal repro reproduces once a page layout is given real work to do
   (a 0.4s sleep was sufficient).

Practical consequence: **do not expect an upstream fix to arrive on its own.**
Most small Dash apps and most upstream tests satisfy neither condition, so the
bug is invisible in exactly the places that would catch it. Absent someone
filing it (not done as of 2026-07-18), assume it survives future Dash releases
rather than treating a version bump as a likely cure. Re-check cheaply after a
Dash upgrade: load the app once, reload, and see whether the first-load console
noise is gone.

Impact is cosmetic and self-healing: on an affected load `document.title` shows
the app-level title instead of the page title, and any reload fixes it. A
workaround for someone else's bug is not worth carrying for that.

"No feature is affected" is measured, not assumed. Exercised on a load
confirmed to have lost the race — six of seven clientside functions registered,
86 "ID not found in layout" entries, the app-level title — the Home page still
rendered fully, the Plotly graph mounted (a beat later than usual), server
callbacks fired and returned 200, and toggling the x-axis radio round-tripped
end to end and updated the figure. The only observable defect was
`document.title`. The "ID not found in layout" flood is the renderer reporting
a transient state it recovers from, not callbacks being dropped.

Validated mitigation, should this ever become worth fixing: prime the app with
one synchronous in-process request before serving — `with
app.server.test_client() as c: c.get("/")` in `main()`, ahead of `serve(...)` /
`app.run(...)`. Measured under the same eight-way concurrency test, this took
seven-of-eight failures down to zero. Deliberately not applied.

## 2026-07-18: Accept dash-ag-grid's `columnSizeOptions` Console Warning

Status: Accepted

Decision: The AG Grid console warning `invalid gridOptions property
'columnSizeOptions'`, emitted once per grid mount on the Playlists and
per-playlist scenario pages, is benign upstream noise from the dash-ag-grid
wrapper. We accept it, keep passing `columnSizeOptions`, and do not work
around it. It is distinct from the first-request pages race above: that noise
appears only on the first load after a server start, while this warning
appears on every mount of either grid.

Why: dash-ag-grid folds its remaining props into AG Grid's `gridOptions`
after stripping its own Dash-side props via a hardcoded list
(`PROPS_NOT_FOR_AG_GRID` in the wrapper's `src/lib/fragments/AgGrid.react.js`).
That list contains `columnSize` but not `columnSizeOptions`, so the prop
leaks through and AG Grid's validator flags an unknown key. Our usage is
correct — both are documented top-level `dag.AgGrid` props, and the wrapper
genuinely consumes `columnSizeOptions` (it destructures `keys`, `skipHeader`,
`defaultMinWidth`, `defaultMaxWidth`, and `columnLimits` from it to drive
`autoSizeColumns`/`sizeColumnsToFit`; verified in the installed 35.3.0
bundle). The upstream fix is adding one string to that list.

Correction to the record: the warning was believed fixed by the PR #146
upgrade to dash-ag-grid 35.3.0. Re-verification on a bare `main` baseline
(2026-07-18, during the PR #153 work) showed it still present, so treat it as
expected noise on 35.3.0, not a regression signal.

Alternatives rejected:

- Dropping the prop silences the warning but loses the `keys`/`skipHeader`
  autosize configuration — real behavior traded for cosmetics.
- AG Grid's blanket switch `suppressPropertyNamesCheck` would silence it —
  the bundled v35 validator still honors the flag — but the option is
  deprecated since v33 (AG Grid's deprecation message calls it redundant now
  that `context` exists for arbitrary user data), so enabling it trades the
  invalid-property warning for a deprecation warning while also disabling
  the check that catches real typos in our own gridOptions and colDefs.
- Re-implementing autosizing through a clientside grid-API call just to avoid
  the prop is a workaround for someone else's cosmetic bug — the same bar the
  pages-race entry above declines to meet.

Consequences: treat the warning as expected baseline noise during browser
checks. Not filed upstream as of 2026-07-18, so do not assume a version bump
fixes it; re-check cheaply after a dash-ag-grid upgrade by loading
`/playlists` and looking for the warning. If an upgrade makes it disappear,
mark this entry superseded.

## 2026-07-17: Playlist Import Falls Back to Evxl Exact By-Code

Status: Accepted

Decision: KovaaK's `/playlist/playlists?search=<code>` stays the primary lookup
for playlist import. Whenever it fails to produce exactly one usable record —
zero after the null-drop validator, or more than one match — import falls back
to Evxl's exact `playlist-by-code` endpoint
(`https://api.evxl.app/kovaaks/playlist-by-code?shareCode=<code>`) before
refusing. If the fallback also fails, the user sees the same refusal message as
before.

Why: KovaaK's search has a null-hydration quirk — for some real, public
playlists it counts the match but returns a `null` record, which the
`ignore_null_playlist_items` validator drops, so a valid playlist looks like
zero results (observed: `KovaaKsCarryingGodlikeTile`; details in
`kovaaks_api_notes.md`). There is no first-party KovaaK's by-code endpoint, and
Evxl's by-code lookup resolves arbitrary community playlists exactly.

This is the app's first *runtime* dependency on Evxl; previously Evxl was used
only by the offline `scripts/benchmark_importer`. First-party KovaaK's data
stays preferred on the happy path — Evxl's copy is cached upstream (can be days
stale) and its case-strict HTTP 400 on mis-cased codes would be a worse
default — so Evxl is consulted only when the first-party search cannot resolve
the code cleanly. The stored code is always the canonical `playlist_code` from
whichever source resolved it, never the pasted input.

## 2026-07-16: Warm Playlist Percentiles With One Polite Background Worker

Status: Superseded in part by the
[2026-08-03 quiet-layer entry](#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy):
the fatal-state toast for an unknown username was removed in PR #196; the
overview's status line and a WARNING log carry it. Amended by
[2026-09-20](#2026-09-20-a-rank-above-the-known-total-suppresses-the-percentile):
the display rule is no longer weaker and monotonic, because a RANKED scenario
whose rank sits above its cached total is worker-fresh yet display-unresolved,
and a resolved row returns to the placeholder when a rewritten rank lands above
the cached total. Everything else stands.

Decision: After startup finishes ingesting local runs, one app-lifetime daemon
worker warms the rank and leaderboard-total caches used by the Playlists
overview. Its queue contains only played scenarios from visible playlists,
grouped to finish recently played playlists first. The worker is sequential,
leaves a two-second politeness gap between network items, and blocks on a
condition variable when idle. Unhiding or importing a playlist prepends that
playlist's played scenarios and wakes the same worker; hiding or deleting does
not cancel already queued work.

Queue duplication is intentionally cheap rather than prevented. Every dequeue
rechecks the disk caches and a session outcome map, so duplicate names from
overlapping playlists, repeated imports, and hide/unhide spam skip without
network work. A scenario is fresh enough for the worker when it has a fresh
UNRANKED cache entry, or a fresh RANKED entry plus a fresh leaderboard total.
The overview's display rule is weaker and monotonic: it may read entries of any
age, but it shows aggregate percentiles only after every played scenario in the
playlist is display-resolved. Until then both aggregate cells show an honest
`n/total cached` placeholder; a fully resolved all-UNRANKED playlist shows
`N/A`, not a pending state.

Interactive rank work always takes priority. The shared API activity signal
keeps separate monotonic timestamps for interactive lookups (cache hits
included) and successful network responses. The worker waits for an
interactive quiet window, while outage backoff wakes early only after evidence
of a real network success. The worker calls the lower-level resolve, rank, and
total operations so it can classify failures without the UI service's UNKNOWN
flattening. Before caching UNRANKED it requires one positive username
validation per session; an API-confirmed unknown username stops the whole
queue and produces one UI notification. Connection errors, 5xx responses, and
post-retry 429s tail-requeue with escalating global backoff; read timeouts and
permanent failures become terminal for that session. Three transient attempts
per name are allowed. A restart reconstructs work from cache freshness rather
than persisting queue state.

The Playlists page reads the worker through an immutable snapshot. While queued
or in-flight work exists it shows `Updating percentile data: N remaining
(~ETA)`, using unique non-terminal names and recent pace; outage backoff adds a
paused/retry time and fatal state remains visible. A one-second interval
rebuilds the normal cache-only overview rows and disables itself only after one
final idle rebuild. `Interval.disabled` has one callback owner. That callback
observes a monotonic enqueue generation and is also driven by the page's row
refresh store, so work enqueued after idle re-arms the browser interval and an
older snapshot cannot disable a newer re-arm. Interval-driven cache reads pass
`record_activity=False`; otherwise the reporting loop would continuously mark
the user active and postpone the worker it reports on.

Why: A cold overview previously showed incomplete percentile aggregates only
for scenarios the user happened to open, which made cross-playlist comparisons
biased and unstable. Bulk warming the full play history would spend API budget
on data no overview consumes, while parallel fetching would add avoidable load.
The played-visible queue plus all-or-nothing display makes each completed value
trustworthy, and the background status makes a 15-minute cold fill visible
without blocking any route.

Consequences: `percentile_warmup_enabled` disables only this worker, and an
empty `kovaaks_username` keeps startup and enqueue hooks fully offline.
Interactive Home and playlist-scenario refreshes remain available. The queue,
pace, backoff, and generation state are process-local; cache files remain the
durable data plane and retain their existing atomic-write and monotonic-rank
rules. A separate background TTL and negative leaderboard-resolution cache are
deferred levers. Shipped across PRs #129, #130, #132, and #133.

## 2026-07-13: KovaaK's Timeout Is 30s (Configurable); Read Timeouts Are Not Retried

Status: Accepted

Decision: All KovaaK's API requests share one timeout, default 30 seconds,
configurable via `kovaaks_api_timeout_seconds` in `config.toml` and applied at
app startup through `api_service.set_request_timeout()`. `_get_with_retry`
retries only `requests.ConnectionError` (which covers `ConnectTimeout`); a
`ReadTimeout` fails immediately instead of being retried.

Supersedes: the `requests.Timeout` clause of the 2026-04-28 transient-retry
decision. The `429`/`Retry-After` policy and the `ConnectionError` retry from
that entry stand, and the 2026-06-21 keep-the-hand-rolled-retry decision is
reaffirmed, not revisited.

Rationale: measured 2026-07-13 during a KovaaK's slow spell,
`/leaderboard/scores/global` latency ranged 9–28s while responses stayed
valid — a Postman probe succeeded after ~28s, and in-app fetches succeeded at
9.0–9.4s, just under the old hardcoded 10s wire. With a 10s timeout every
attempt during the spell died, and because the stale-rank fallback is
deliberately read-only (see the 2026-07-12 entry), the same expired cache
entry re-timed-out on every page open — one expired scenario added ~20s to
every playlist load until a fetch succeeded. A read timeout also does not
cancel the server-side query, so the old immediate retry doubled KovaaK's
load for almost nothing (2 of 63 retries succeeded that night); a connection
error, by contrast, means the request never reached the server and remains
safe to retry. 30s clears the observed worst case, and the config knob is the
escape hatch if slow spells drift past it.

Constraints:

- Deliberately a single timeout value — no connect/read split and no
  urllib3 `Retry` adoption (the 2026-06-21 entry holds the full migration
  analysis). Beyond that entry's reasons: the per-retry warnings in
  `_get_with_retry` are the primary forensic log, and the benchmark importer
  depends on its per-call `attempts`/`backoff_seconds` knobs, which
  `requests` cannot express per request through adapter-mounted `Retry`.
- The importer shares the helper, so its retry schedule now governs only
  connection errors and 429s; a read timeout fails the sharecode
  immediately.

## 2026-07-12: Rank-Fetch Failure Degrades To The Last Cached Rank

Status: Superseded in part, for the passive red/yellow toasts of the
three-tier toast model in Constraints below, by the
[2026-08-03 notification-layer entry](#2026-08-03-one-quiet-notification-layer-with-verdict-carrying-copy)
(passive renders state the condition in place; manual Refresh keeps all
three tiers). The fallback semantics are unchanged and remain Accepted.

Decision: When `get_scenario_rank_info` has resolved a leaderboard but the
live rank fetch fails — either an unreachable endpoint (`RequestException`) or
a successful-but-unusable, schema-invalid response (`ValidationError`) — it
falls back to the last cached rank (read via `_cached_rank`, ignoring the
rank-cache TTL) instead of returning UNKNOWN. Both failure modes route through
the shared `_stale_rank_fallback` helper. UNKNOWN is reserved for the case
where there is genuinely nothing cached to show. `force_refresh=True` inherits
the same fallback — a failed forced refresh showing last-known still beats
"N/A".

Rationale: the app should never display less than it already knows, and the
behavior was already inconsistent — the Playlists overview reads ranks with
`allow_network=False`, which serves TTL-expired cached ranks, so a transient
KovaaK's failure made the overview show a percentile while Home and the
playlist-scenarios page showed "N/A" for the same scenario. This extends the
existing graceful-degradation precedent in the same function
(`_with_leaderboard_total` keeps a valid rank when the total-players fetch
fails).

Constraints:

- **Read-only.** The fallback path never writes the cache — no
  `_save_rank_monotonic`, no `_write_json`. A write would bump the cache
  file's mtime and launder stale data into TTL-fresh on the next read.
- `scenario_name` is backfilled via `model_copy` when the cached rank lacks
  it; the leaderboard total is attached best-effort from
  `_cached_leaderboard_total` (also TTL-free) and percentile derived, mirroring
  the `allow_network=False` read path.
- The resolve-failure branch is unchanged: no `leaderboard_id` means nothing
  is cached to fall back on.
- The stale result carries a `warning_message`, driving a three-tier toast
  model on the Home rank paths: fetch fails with nothing cached → red error;
  fetch fails but a stale rank is served → yellow warning; fetch succeeds →
  green success (manual refresh only). `refresh_rank`'s green confirmation is
  suppressed by any error *or* warning. No persistent on-display staleness
  indicator is surfaced (`fetched_at` remains on the model for a future
  opt-in).

## 2026-07-11: The Playlist Overview Is The Playlist Management Surface

Status: Accepted

Decision: The `/playlists` overview is the single surface for managing
playlists and benchmarks. It lists every loaded playlist with local
aggregates and hosts all management controls — per-code show/hide, share-code
import, and delete for user playlists — rather than spreading them across a
Settings modal and the filesystem. Concretely:

- **Visibility is a plain per-code show-list**, not file state. It is
  persisted as the `shown_playlists` key in `data/preferences.json` (now
  `data/playlist_visibility.json`), and a playlist is visible iff its code
  is in the list — uniformly for bundled benchmarks and user playlists. A
  missing (or unusable) preferences file yields a first-run seed — the
  bundled `DEFAULT_VISIBLE_CODES` (Voltaic + Viscose) plus every code loaded
  from the user root — **without writing**; the file materializes on the
  first show/hide, and an existing file is authoritative including an empty
  list (everything hidden on purpose).
  Importing a code appends it (importing is the intent to see); hide removes,
  unhide re-adds. `get_visible_playlist_selector_options()` is the single
  visibility filter every option list consumes (Home filter, Journey picker,
  overview), so they cannot disagree. Hidden playlists still load, their
  `/playlists/{code}` routes still resolve, and rank overlays still draw.
- **The full bundled benchmark library ships flat under
  `resources/benchmarks/`** and is scanned in full at startup, with only the
  curated defaults visible. The whole root is pipeline-managed (machine
  generated by `scripts/benchmark_importer/`; don't hand-edit); the
  bundled-invariant test asserts every committed file carries rank data.
  Enabling a benchmark is one unhide click, not a copy-and-restart, and app
  updates refresh the library automatically.
- **Delete exists only for user playlists** (`data/playlists/` files). It
  unlinks the file recorded for that code at load/import time (not a
  reconstructed name, so hand-dropped filenames are handled), drops the store
  entry, and forgets the code's show-list membership so `preferences.json`
  does not accumulate dead codes. Bundled benchmarks cannot be deleted —
  hiding is the equivalent, which forecloses the delete-then-reimport
  degradation (a share-code re-import comes back rank-less).
- **Startup stays read-only.** A `data/playlists/` file whose code is already
  served by a bundled benchmark (a pre-#90 copy-to-activate leftover) is
  skipped with a warning; the overview surfaces those dead copies with an
  in-app cleanup action instead of deleting anything at load.

Why: The bare `/playlists` route was a name-only dropdown that answered
nothing about where to direct attention, and shipping the whole benchmark
library would have flooded every dropdown with 100+ rows. Visibility protects
browsing and first-run focus (search only helps when you already know the
name). Managing playlists by editing files ("copy a JSON in, restart") is the
opposite of "the user interacts with the app, not the filesystem." The
single-writer/single-user assumption (the user is also the library curator)
lets visibility be a plain show-list instead of a richer defaults-aware store.

Consequences: This entry supersedes the `resources/playlists/` bundled-root
path in the 2026-06-22 and 2026-07-07 entries: the bundled root is now
`resources/benchmarks/`. Accepted tradeoff: a future default-worthy benchmark
(e.g. a Voltaic S6) arrives hidden, because a plain show-list has no
live-evaluated notion of "new default." This is acceptable while the app has
one user who is also the curator — a new benchmark only enters
`resources/benchmarks/` because that user ran the importer and committed it,
and unhiding it is one known click. The rejected richer design (a `shown`
list plus a `hidden` list plus a live-evaluated defaults constant, letting
shipped defaults auto-surface) remains the known, backward-compatible upgrade
path if the app is ever distributed to non-curator users; it was declined
here as machinery defending against a surprise this app cannot currently
produce. Separately, deleting the three legacy top-level Viscose files during
the library flip changed 19 served thresholds; the canonical values are a
fresh importer pull taken at flip time (OQ-9), because KovaaK's is
authoritative for thresholds and the served top-level values were
demonstrably stale.

## 2026-07-11: Match Scenario Names On Their Stripped Form

Status: Accepted

Decision: Scenario-name matching is exact on **stripped** names, and the strip
is enforced at two boundaries: the CSV run parse
(`source/kovaaks/data_service.py`, `scenario = line.split(",", 1)[1].strip()`)
and a `field_validator` on `Scenario.name` in `source/kovaaks/data_models.py`.
The model validator normalizes every path that builds a `Scenario` — runtime
share-code import, bundled/user playlist file load
(`PlaylistData.model_validate_json`), and the benchmark importer's output —
so a playlist scenario name always joins `kovaaks_database` (which is keyed by
the CSV-stripped names) under the same key. The validator is lenient on an
empty result (a whitespace-only name becomes `""` rather than raising, unlike
the sibling `code` validator) because a blank scenario name is an odd upstream
quirk, not a store key, and must not reject the whole playlist import.

Why: Every scenario lookup is exact-match — `is_scenario_in_database` (dict
membership), `get_rank_data_from_playlist_code` (`!=` compare),
`get_scenarios_from_playlist_code` (verbatim) — while `kovaaks_database` keys
are always stripped. A padded name from the KovaaK's playlist API therefore
never resolved local runs / PB / rank overlays. Padding is observed, not
hypothetical: PR #97 found real corpus files with one- and five-space paddings
from the KovaaK's benchmark API. The model boundary was chosen over a call-site
strip (which would fix only one of the three entry points — the #97
whack-a-mole) and over normalize-at-lookup (which would spread the invariant
across every comparison and dict lookup); it is a single choke point that
mirrors the existing `PlaylistData.strip_and_require_code` precedent.

Consequences: The two enforcement points must agree — drift between the CSV
parse strip and the `Scenario.name` validator silently recreates this bug
class, so a future change to the normalization strategy must update both
together (a shared `normalize_scenario_name()` helper was considered and
declined as premature; this entry is the cheaper drift guard). Nothing bakes
the association in: `kovaaks_database` is rebuilt from CSVs each startup and the
validator re-runs on every playlist file load, so the match key is re-derived
at runtime on both sides and changing strategy re-keys everything on the next
startup. Name-keyed persisted caches (leaderboard-id / rank) tolerate a
strategy change by design — a miss refetches, bounded by the 168 h TTLs. The
only one-way loss is that imported playlist JSON persists the stripped name,
discarding original padding (semantically void whitespace, recoverable by
re-import from the code). The benchmark importer's own `.strip()` at
`scripts/benchmark_importer/script.py` is now redundant defense-in-depth and is
left in place. Shipped in PR #100.

## 2026-07-11: Humanize The Absolute Timestamp Format

Status: Accepted

Decision: The absolute "on-hover / in-title" timestamp adopts a GitHub-shaped, humanized format instead of the previous `%Y-%m-%d %I:%M:%S %p` (which rendered `2026-04-12 07:04:22 PM`). Two variants: staleness surfaces (home last-played tooltip, playlist/scenario grid tooltips, plot-title `updated:`) show `Apr 9, 2026, 7:04 PM` (no seconds); the per-run scatter hover shows `Apr 9, 2026, 7:04:22 PM` (seconds kept). Format rules: abbreviated English month from a hardcoded array (never `%b`/`calendar.month_abbr`), unpadded day, 4-digit year, unpadded 12-hour hour with `0 → 12` (midnight `12:xx AM`, noon `12:xx PM`), zero-padded minutes/seconds, uppercase space-separated AM/PM, browser/local time with no timezone suffix. The Python side is `format_absolute_timestamp(dt, *, include_seconds=False)` in `source/utilities/utilities.py`; the JS side is `dagfuncs.absoluteTime` in `assets/dashAgGridFunctions.js`, which mirrors the no-seconds variant. The relative string, the `Never`/`—` sentinels, the epoch-seconds plumbing, and the dotted-underline tooltip affordance are all unchanged.

Why: Market research (GitHub, Discord, Slack, Steam, AWS Cloudscape) confirmed the relative-primary + absolute-on-hover pattern is standard, but the old absolute string deviated from every comparator — a zero-padded 12-hour hour (no consumer app pads it), seconds on staleness surfaces (GitHub/Discord/Cloudscape all drop them), and a machine-register ISO date glued to a consumer-register AM/PM time. The GitHub shape reads as one register. Seconds are kept only on the run-level hover because they cross-reference KovaaK's second-stamped stats CSV filenames. The format is hand-rolled (not `strftime`/`toLocaleString`) for locale independence (hardcoded month array) and because no cross-platform strftime code exists for an unpadded hour (`%-I` is POSIX-only, `%#I` Windows-only).

Consequences: Python↔JS parity is held by this spec and by hand — there is no JS test harness — so the two implementations must be kept in sync (both carry a comment pointing at the other). This supersedes only the exact-format aspect of the 2026-06-21 and 2026-06-30 entries; their behavioral decisions stand.

## 2026-07-09: Load Configuration Lazily At Application Startup

Status: Accepted

Decision: Configuration is loaded and cached through `get_config()` instead of
at module import. `main()` owns the initial load and translates expected file,
decode, TOML, and validation failures into the existing concise startup error
before loading playlists or initializing runtime services. Other modules resolve
the cached configuration only inside function bodies.

Why: Import-time loading forced pytest to overwrite the real repo-root
`config.toml`, keeping its backup only in process memory. Abnormal termination
could permanently replace a user's configuration, and concurrent test sessions
could corrupt each other's backup/restore chain. A lazy production accessor makes
modules import-safe and gives tests an in-process seam without adding a test-only
environment-variable override.

Consequences: Tests monkeypatch the config loader and clear the accessor cache;
they never modify the real `config.toml`. `get_config()` propagates load errors,
while the executable startup boundary alone prints the user-facing message and
exits. Playlist loading happens in `main()` after configuration validation so a
bad config still produces exactly one clean error with no prior warning output.

## 2026-07-09: Accept Unsynchronized In-Memory Stores (Single-Writer)

Status: Accepted

Decision: The module-global in-memory stores in `source/kovaaks/data_service.py`
(`kovaaks_database`, `run_database`, and `playlist_database`) remain
unsynchronized. No lock is added. This is a reviewed acceptance, not an
oversight.

Why: Design review (2026-07-09) verified the structural guarantees that bound
the risk. After startup, the watchdog observer thread is the only writer to
`kovaaks_database`/`run_database` (the startup bulk load is single-threaded,
before the observer and server exist), so writer-writer corruption cannot
occur. The top-level `kovaaks_database` dict is read via GIL-atomic lookups;
the one reader that iterates it (`get_scenario_stats_snapshot`, PR #78)
snapshots with a single C-level `list()` call that a concurrent insert cannot
break, and PR #78 also made the writer replace `ScenarioStats` objects instead
of mutating fields in place, so a reader that binds one sees field-consistent
values. The remaining exposure is server-thread readers iterating nested
`sortedcontainers` structures (and the journey page walking `run_database`)
mid-`add()`: worst case is a skipped or duplicated point, or a rare exception,
in one render. Dash contains callback exceptions and no path writes torn state
back. Self-healing has two cadences: home-page consumers re-render on the
polling interval, so races there clear within about a second; the journey,
playlist grid, and playlist overview pages rebuild store-derived data only on
navigation or control interaction (their intervals only re-tick relative
timestamps), so a raced render there can persist until the next interaction.
Both cadences stay within the accepted class — a wrong or failed render, never
corrupted state. The load-before-notify
ordering in `_enqueue_after_loading` guarantees a drained message's run is
already fully visible in the stores. `playlist_database` carried the same
class between server threads (the import callback's insert vs. `.values()`
iterations under Waitress's worker pool) until PR #78 converted its iterating
readers to the same `list()` snapshot pattern, leaving only atomic containment
checks and single-key lookups exposed — which are safe. A coarse lock
was rejected because it imposes permanent accessor discipline — silent when
violated — against a self-healing one-frame glitch; a single-writer ingest
redesign was rejected as not worth reworking the load-before-notify contract
on its own.

Consequences: Two lists govern when this decision ends. Hazard triggers (add
synchronization, or implement the single-writer ingest redesign): a store-race
exception or corruption actually observed in logs; a genuine second writer to
these stores (for example runtime playlist reload or a background recompute);
a move to free-threaded (no-GIL) CPython, which weakens the per-bytecode
atomicity and pure-Python `sortedcontainers` invariants this acceptance leans
on. Resolving events (the problem dissolves as a side effect): a SQLite
migration, or an ingest rework undertaken for other reasons (which should then
adopt the single-writer design). For the SQLite path, file-backed WAL is the
chosen shape — a design choice, not the only technically viable one. In-memory
variants can be shared across threads (a single serialized connection via
`check_same_thread=False`, or one shared database via `cache=shared` or SQLite
3.36+'s `memdb` VFS), while a naive connection-per-thread `:memory:` setup
silently gives each thread a separate empty database. The shared variants are
rejected because WAL does not support in-memory databases, so each of them
forfeits concurrent snapshot-isolated readers and reintroduces reader-writer
serialization or a discouraged mode; file-backed is also the only shape that
serves the persistence and startup-scan justifications that would motivate the
migration in the first place. Run History adds more reader iteration over `run_database` but no
writers; it stays within this acceptance. New readers that iterate a shared
store dict should follow the established snapshot pattern — one C-level
`list()` call before iterating (see `get_scenario_stats_snapshot`). That
pattern is deliberately not extended to the nested `sortedcontainers`
structures, where `list()` is itself Python-level iteration and offers no
atomicity; those remain the accepted self-healing class above.

## 2026-07-08: Judge Score-Threshold Notifications Against The Previous PB

Status: Accepted

Decision: Score-threshold notification verdicts compare in score space against
the personal best the run was chasing:
`score >= previous_high_score * score_threshold_percentage / 100`. The overlay
line still uses the current post-run personal best for the same percentage
setting.

Why: The toast already displays the run's percentage against the previous PB.
Using the post-run PB for the verdict made goals above 100% unreachable,
because a new PB moved the target upward before the run was judged. Keeping the
comparison in score space preserves the exact-threshold `>=` boundary; the
displayed-ratio form can round `820 / 800 * 100` below `102.5` and turn an
exact hit into a failure.

Consequences: Goals above 100% now pass when a run beats the previous PB by
the configured margin. New-scenario and new-sensitivity events still carry
`previous_high_score=None`, so they remain verdict-less. Backlog summaries keep
judging only the batch's latest run; fuller historical pass/fail review belongs
to run history.

**Superseded in part (2026-10-05).** On a time-scored scenario, wherever the
app can measure pace, the verdict compares pace instead of score: a run
passes when it is at least the goal percentage as fast as the previous PB.
The reasons above stand there too: the verdict still judges against the
previous PB, and still compares exactly rather than through the ratio it
displays. Every other scenario keeps the formula as written. The
[2026-10-05 entry](#2026-10-05-time-scored-scenarios-are-measured-by-pace)
holds the pace formula.

## 2026-04-27: Use JSON Files For Runtime API Caches

Status: Accepted (cache root superseded by the 2026-07-11 cache-relocation
entry: caches now live under `data/cache/`)

Decision: Store current API cache data as JSON files under `cache/`.

Why: The current cache use cases are simple key-value lookups with short or medium TTLs. JSON keeps the implementation transparent, easy to inspect, and low-friction.

Consequences: Cache reads must tolerate missing, malformed, stale, or partially-written files. Cache writes should be atomic where practical. Reconsider SQLite when we need rank history, multi-record queries, or stronger transactional guarantees.

## 2026-06-22: Keep User Runtime Data Under `data/`

Status: Accepted (bundled-root path superseded in part by the 2026-07-11
playlist-overview entry: bundled playlists now live under
`resources/benchmarks/`, not `resources/playlists/`; the deferred cache move
shipped in the 2026-07-11 cache-relocation entry)

Decision: Store user/runtime app data under a repo-local ignored `data/` directory. New runtime logs belong under `data/logs/`. Existing API caches remain under `cache/` until a separate migration moves them.

Why: Logs are runtime artifacts, but they are not cache. A dedicated `data/` root keeps future runtime state such as logs, imported/custom playlists, and an eventual SQLite database grouped in one place without mixing it with source-controlled resources.

Consequences: Keep bundled/default playlists under `resources/playlists/`. Put future user-imported or user-created playlists under `data/playlists/`. If the existing API cache moves from `cache/` to `data/cache/`, handle it as a dedicated compatibility migration instead of silently changing paths.

## 2026-07-07: Use Playlist Codes As Playlist Identity

Status: Accepted (bundled-root path superseded in part by the 2026-07-11
playlist-overview entry: the loader's first root is now
`resources/benchmarks/`, not `resources/playlists/`)

Decision: Treat KovaaK's playlist `code` as the app's playlist identity everywhere: the in-memory `playlist_database` key, route value, selector value, import duplicate check, and import filename suffix. Playlist names are display-only labels. Selectors receive finished `{label, value}` options from the service; labels become `Name (CODE)` only when duplicate names need disambiguation.

Why: KovaaK's playlist names are not unique, so name-keyed storage silently dropped later same-named playlists and made those playlists unreachable even by their stable code routes. Codes are already user-facing through share-code imports and `/playlists/{playlistCode}` URLs, so they are the stable identity to preserve.

Consequences: The startup loader scans top-level JSON files from `resources/playlists/` first and `data/playlists/` second, sorted within each root by `(filename.casefold(), filename)`. The first occurrence of a code wins; duplicate-code files are skipped with a warning naming both files, and startup warnings are buffered until the UI mounts so they become visible notifications instead of being dropped outside Dash callback context. This supersedes the 2026-07-05 proposal call that user-root files should win: the final rule is bundled-wins because bundled benchmark files carry rank data and share-code imports do not. New imports write atomically to `data/playlists/{sanitized name} [{code}].json`; importing an existing code is refused with a user-visible message naming the existing playlist. The `data/playlists/` root may be absent on clean checkouts and is created on first import. Legacy user imports under `resources/playlists/` are a clean break, not migrated; owners preview and remove ignored legacy files manually with `git clean -Xn resources/playlists` then `git clean -Xf resources/playlists`, re-importing anything still wanted by share code.

## 2026-04-27: Treat `total-play` As Metadata Only

Status: Accepted

Decision: Use `/user/scenario/total-play` only to hydrate or upsert scenario metadata such as `scenarioName -> leaderboardId`.

Why: The endpoint can lag behind current leaderboard scores and ranks. `/leaderboard/scores/global` is the authoritative source for current rank.

Consequences: Current-rank lookup should not trust score or rank data from `total-play`. The endpoint remains useful for cache initialization and metadata discovery.

## 2026-04-27: Keep KovaaK's API Details Behind `ScenarioRankInfo`

Status: Accepted

Decision: UI code consumes `ScenarioRankInfo` and should not know which KovaaK's endpoint produced the data.

Why: Endpoint details, fallback behavior, cache rules, and expected API failures belong in the service layer. This keeps Dash callbacks focused on rendering.

Consequences: Expected KovaaK's API/domain failures should become `ScenarioRankInfo(status=UNKNOWN, error_message=...)` in `api_service.py`. UI code can render `RANKED`, `UNRANKED`, or `UNKNOWN` without duplicating endpoint logic.

## 2026-04-27: Prefer Steam ID Matching When Configured

Status: Accepted

Decision: When `steam_id` is configured, prefer it for leaderboard identity matching. If Steam ID matching fails but exact username matching succeeds, keep the rank result and surface a warning.

Why: `usernameSearch` can return partial matches. Steam ID is the strongest identity check, but a mistyped Steam ID should not hide otherwise valid exact-username rank data.

Consequences: The warning is transient and derived from current config each time rank info is returned. It should not be persisted in rank cache.

## 2026-04-27: Make Leaderboard Total Enrichment Best-Effort

Status: Accepted (amended by
[2026-09-19](#2026-09-19-a-clicked-refresh-re-reads-the-leaderboard-total): a
failed total lookup now falls back to the last cached count for every caller
rather than returning the result untouched)

Decision: Leaderboard total lookup should never invalidate a valid rank or unranked result.

Why: Total players and percentile are enrichment data. If total lookup fails because of network errors, malformed responses, validation failures, or cache I/O issues, showing the valid rank alone is better than falling back to `N/A`.

Consequences: `_with_leaderboard_total()` catches expected total-enrichment failures, logs them, and returns the original `ScenarioRankInfo`.

## 2026-04-29: Cache Leaderboard Totals For One Week

Status: Accepted (amended by
[2026-09-19](#2026-09-19-a-clicked-refresh-re-reads-the-leaderboard-total): the
TTL governs automatic paths only, and both board-authoritative callers — a
user-clicked Refresh and the PB-triggered freshness chain — bypass it)

Decision: `leaderboard_total_cache_ttl_hours` defaults to `168`, matching `scenario_rank_cache_ttl_hours`.

Why: Leaderboard total player counts are expected to increase slowly. For large leaderboards, a mildly stale total count changes displayed percentile by less than the UI's two-decimal precision in most cases, while avoiding daily cold-cache total fetches across every playlist scenario.

Consequences: Total-count freshness remains configurable. If users notice stale total counts causing misleading displays, revisit the TTL or add a targeted refresh flow.

## 2026-04-27: Use The Midpoint Percentile Formula

Status: Accepted

Decision: Derive percentile with:

```python
percentile = ((total_players - rank + 0.5) / total_players) * 100
```

Why: This matches the KovaaK's-style percentile behavior we agreed to use.

Consequences: Percentile is display-only metadata derived when rank info is returned. It is not stored in rank cache. No tiny-leaderboard special casing is planned, so `rank 1 of 1` displays `50.00%`.

## 2026-04-27: Keep KovaaK's API Findings In A Dedicated Notes File

Status: Accepted

Decision: Track KovaaK's endpoint behavior, relied-upon fields, and discovered quirks in `docs/kovaaks_api_notes.md`.

Why: We are probing unofficial or lightly documented API behavior across multiple milestones. Keeping API lore in one living document helps future agents avoid rediscovering endpoint semantics from chat history.

Consequences: When new endpoint behavior or failure modes are discovered, update the notes file and add regression coverage when practical.

## 2026-04-28: Retry KovaaK's GET Transient Failures Once

Status: Superseded in part by the 2026-07-13 timeout/read-timeout decision — `requests.Timeout` is no longer in the retry set (read timeouts fail immediately); the `429`/`Retry-After` policy and the `requests.ConnectionError` retry stand

Decision: KovaaK's GET requests should retry exactly once on HTTP `429 Too Many Requests`, `requests.Timeout`, and `requests.ConnectionError`. `429` retries should honor `Retry-After` when present and cap the wait.

Why: Playlist scenario overview can create bursty cold-cache rank and total lookups. KovaaK's can also occasionally exceed the current read timeout for one row while adjacent requests succeed. A single bounded retry handles transient failures without turning the retry helper into a full scheduler or hiding unrelated failures.

Consequences: Retry remains GET-only. Non-429 HTTP failures and unexpected exceptions continue through the existing service-layer error handling. Recovered retries are logged but are not user-facing notifications.

## 2026-04-29: Drive Playlist Table Loads From Mounted Route State

Status: Accepted

Decision: Playlist scenario table loads should be driven by state created in the mounted `/playlists/<playlist_code>` layout, not directly by selector changes or URL-change callbacks.

Why: When the playlist selector changes the route, Dash Pages can briefly have the old page instance responding to the URL update before the new route layout finishes mounting. If the expensive table load listens directly to that navigation event, one user selection can trigger duplicate cache/API loads.

Consequences: Keep the selector callback navigation-only. The route layout should publish the resolved playlist code through a lightweight mounted component, currently `dcc.Store(id="playlist-scenarios-code")`, and the table-loading callback should use that mounted state as its trigger.

## 2026-04-29: Use Controlled AG Grid JS For Null-Aware Sorting

Status: Accepted

Decision: Playlist scenario AG Grid tables may use repo-owned JavaScript comparators from `assets/dashAgGridFunctions.js` with `dangerously_allow_code=True` when AG Grid requires client-side sort behavior that Python cannot provide directly.

Why: AG Grid sorting runs in the browser. The playlist table needs `NULLS LAST` behavior for rank, total, and percentile columns so unknown values do not sort ahead of real numeric values.

Consequences: Only reference controlled functions committed under `assets/`. Do not generate JavaScript strings from user input. If additional custom grid behavior is needed, prefer adding named functions to `assets/dashAgGridFunctions.js` rather than embedding ad hoc code in page callbacks.

## 2026-04-29: Use Thread-Local Sessions For KovaaK's GET Requests

Status: Accepted

Decision: KovaaK's GET requests should go through a reusable `requests.Session` scoped to the current worker thread.

Why: Cold-cache playlist table loads make many small HTTPS calls. Reusing sessions lets Requests keep connections alive and avoid repeated TCP/TLS setup. Keeping sessions thread-local avoids sharing one mutable `Session` object across the playlist table's concurrent worker threads.

Consequences: `_get_with_retry()` should call the thread-local session wrapper instead of `requests.get(...)` directly. Tests should patch that wrapper when faking HTTP responses. If we later add async HTTP or a centralized rate limiter, revisit this decision.

## 2026-06-21: Keep The Hand-Rolled GET Retry; Defer urllib3 `Retry` Migration

Status: Accepted

Decision: Keep the hand-rolled retry helpers in `source/kovaaks/api_service.py`
(`_get_with_retry`, `_retry_after_seconds`) instead of mounting a urllib3
`HTTPAdapter(max_retries=Retry(...))` on the thread-local sessions. Reconsider
only when requirements grow past one retry (exponential backoff with jitter, a
broader `status_forcelist` such as 503, separate connect/read budgets).

Why: The happy path maps cleanly onto urllib3 `Retry`, but a faithful migration
is not a clean delete. It would lose the 0.5s default delay on a 429 without
`Retry-After` (urllib3 sleeps 0s on the first retry), change the exhaustion
exception types the tests assert on (`HTTPError`/bare timeout become
`RetryError`/wrapped `ConnectionError`), downgrade recovered-retry logging from
WARNING to a DEBUG line on urllib3's logger, and still require a wrapper for the
per-request timeout default. Preserving the 5s `Retry-After` cap needs
`retry_after_max`, which requires pinning `urllib3>=2.6` — currently only a
transitive dependency. Net-neutral complexity plus a full test rewrite does not
clear the bar for replacing working, ratified code.

Consequences: The retry layer stays per-request and hand-rolled; the score-aware
rank refresh loop sits on top of it and relies on its contract (one inner retry,
bounded sleeps). If migrating later, the minimal-drift recipe is: one
module-level `Retry(total=1, status=1, connect=1, read=1, status_forcelist=[429],
allowed_methods={"GET"}, retry_after_max=5, raise_on_status=False)` mounted on
both schemes of each thread-local session, a thin wrapper retained for the
timeout default and WARNING log, and an explicit `urllib3>=2.6` floor. The full
analysis lives in git history as `docs/api_retry_urllib3_migration_proposal.md`.

## 2026-07-03: Playlists Routes Are Stable; The Bare-Route Selector Is Transitional

Status: Accepted

Decision: The playlists feature owns two routes: `/playlists` (navbar
destination) and `/playlists/{playlistCode}` (per-playlist scenario table).
The per-playlist route and its `playlistCode` URL identity are stable
contracts. The current content of the bare route — a selector dropdown plus an
empty prompt — is transitional scaffolding from milestone 1: when the
playlist-level overview (roadmap milestone 2) ships, the overview replaces the
bare-route content, overview rows navigate to `/playlists/{playlistCode}`, and
the selector dropdowns are removed from both pages.

Why: A single canonical landing route keeps the navbar destination stable
across milestones, and the human-readable playlist code is already user-facing
via the import flow. The overview is a strictly richer playlist picker than a
name-only dropdown (it surfaces last-played, aggregate percentile, and similar
metadata), so keeping the selector after it ships would be scaffolding
outliving its purpose. Distilled from the milestone-1 playlist scenarios
proposal (shipped in PRs #12, #15, #16).

Consequences: Keep the selector wiring separate enough that its removal is a
clean delete, not a refactor. Post-overview, switching playlists means
navigating back to `/playlists` and clicking a row, so the overview needs
visible row-click affordances (cursor, hover tint, full-row target). Do not
bake the selector into the per-playlist page in a way that blocks removal.

## 2026-06-20: Reference dash-ag-grid Grid Functions By Bare Name

Status: Accepted

Decision: In dash-ag-grid `{"function": "..."}` strings (`valueFormatter`, `tooltipValueGetter`, `comparator`, `valueGetter`, etc.), reference functions from the `assets/dashAgGridFunctions.js` registry by their **bare name** — `relativeTime(params.value, "Never")`, `nullsLastComparator` — never with a `dagfuncs.` prefix.

Why: dash-ag-grid (35.2.0) does not run these strings as a browser-global eval. It parses each to an AST and evaluates it against a constructed scope that spreads the contents of `window.dashAgGridFunctions` in as bare names (alongside `params`, `agGrid`, `d3`, `dash_clientside`). There is no `dagfuncs` object in that scope — the identifier never appears in the dash-ag-grid bundle — so `dagfuncs.X(...)` resolves to undefined and the expression **silently fails**: the cell renders the raw field value, or the comparator falls back to AG Grid's default sort, with no console error. The `assets/` file's `var dagfuncs = (window.dashAgGridFunctions = ...)` alias is only for *defining* the registry functions.

Consequences: Plain Dash `clientside_callback`s are different — they run in real browser global scope, so there use the full `window.dashAgGridFunctions.X(...)` path (e.g. the home page's "Last played" relative-time callback). This decision corrected two silent bugs: the grid "Last Played" `valueFormatter`/`tooltipValueGetter` (PR #17) and the `NULLS LAST` comparator on all sortable columns (PR #19), the latter broken since the 2026-04-29 "Use Controlled AG Grid JS For Null-Aware Sorting" entry. Verified by decompiling the installed bundle and by a live browser test.

## 2026-06-20: Interim Merge Bar Until Lint/Format Cleanup

Status: Superseded by the 2026-07-03 ruff-only tooling decision

Decision: Until the lint/format cleanup lands, the merge bar is: `uv run pytest` and `uv run mypy source` must be **green**, and `uv run pylint source` plus `black --check`/`isort --check` must **not regress versus `main`** (no new findings in the files a change touches). The absolute CLAUDE.md bar (pylint `fail-under = 10`, black/isort clean) is the target, not yet current reality.

Why: As of 2026-06-20 `main` is green on pytest and mypy (the latter since PR #18 deleted a dead `mypy.ini` that was shadowing `[tool.mypy]`), but not on pylint (9.22/10 — missing docstrings, TODOs, broad-except, too-many-*), `black --check` (3 files), or `isort --check` (2 files). Those are pre-existing and reproduce on the committed LF blobs (not a CRLF flap). There is no CI, so the gates are an honour-system check; blocking feature PRs on an absolute bar `main` itself cannot meet is incoherent, while a baseline-comparison bar keeps shipping unblocked without growing the debt.

Consequences: Reviewers compare pylint/black/isort output for the changed files against the `main` baseline rather than requiring a green absolute run; pytest and mypy are hard green gates. The remaining pylint cleanup is deferred tech debt (~115 findings on `main`, dominated by missing docstrings, plus fix-or-disable calls on `too-many-*`, `broad-except`, `fixme`, and similar); the `black`/`isort` deltas are a few files. Remove this interim framing once pylint and the formatters are green on `main`.

## 2026-07-03: Consolidate Formatting And Linting On Ruff

Status: Accepted

Decision: Use ruff as the sole formatter and linter, with mypy and pytest retained as separate gates. Ruff formats at 88 characters and enforces a 120-character hard ceiling through `E501`. Lint `source/` and `tests/`, but exclude `scripts/`; tests are exempt from missing-docstring, design-metric, and unused-argument rules. Require docstrings in `source/`, leave deliberate TODOs unenforced, and keep preview mode disabled. Local pre-commit hooks enforce ruff check and format; mypy, pytest, and the inexpensive CPython `compileall` syntax check remain manual validation because the project has no CI.

Why: The previous black, isort, and pylint configuration described conflicting line lengths, duplicated responsibilities, and could not meet its own score gate while intentional TODOs remained. One pinned ruff configuration provides a green, deterministic format/lint bar without a score or `fail-under`, while preserving the established 88-character formatting and keeping tests and replacement-bound scripts free from low-value lint churn.

Consequences: Pylint, black, and isort are no longer direct dependencies or configured tools. Black and isort remain transitive lockfile dependencies of `datamodel-code-generator`. Accepted enforcement losses are: no ruff equivalents for duplicate-code, too-many-instance-attributes, or too-many-lines; preview-only rules for unspecified-encoding, too-many-locals, too-many-positional-arguments, too-many-boolean-expressions, and too-many-nested-blocks remain disabled; and `no-else-return` is outside the selected rule families. The two current encoding omissions and the current unnecessary `else` were fixed once during migration, but are not ongoing gates. Keep the pre-commit ruff revision synchronized with the ruff version in `uv.lock`, and add CI or a single-command task runner separately.

## 2026-07-03: CI Runs The Merge Bar On Every PR

Status: Superseded in part by the 2026-07-06 cross-repo Python v2 tooling decision

Decision: A single GitHub Actions `gates` job runs the repository merge bar on
every pull request and push to `main`: ruff format check, ruff lint, mypy,
CPython `compileall`, and pytest. It runs on `windows-latest`, validates the
lockfile with `uv sync --locked`, and executes each gate with
`uv run --no-sync`. Python and uv are pinned, action dependencies use immutable
full commit SHAs, the workflow token has read-only contents access, and
superseded runs on the same ref are cancelled.

Why: This fulfills the deferred CI consequence of the 2026-07-03 ruff
consolidation decision. An executable merge bar catches stale lockfiles,
formatting drift, type errors, syntax errors, and regressions consistently,
including on doc-only changes where the docs hygiene tests still matter.
Windows matches the supported development and runtime environment.

Consequences: `.github/workflows/gates.yml` is the canonical executable list of
gates. Local pre-handoff validation remains unchanged because it is the fastest
feedback path. A local single-command task runner remains optional rather than
part of this decision. After the workflow has established a short green
history, the repository owner should mark the `gates` check required on
`main`; branch protection is intentionally outside the workflow.

## 2026-07-06: Adopt The Cross-Repo Python V2 Tooling Spec

Status: Accepted

Supersedes: The workflow shape, command set, tool and runtime pin placement,
and concurrency behavior in the 2026-07-03 CI decision. Windows execution,
locked dependency sync, SHA-pinned actions, read-only contents permission, and
the broader local pre-handoff validation remain in force.

Decision: Use the canonical `tooling-spec: python-v2` workflow at
`.github/workflows/ci.yml`. Its matrix-backed `test (windows-latest)` job runs
`uv sync --locked`, ruff format, ruff lint, bare mypy, and bare pytest.
`pyproject.toml` owns the required uv version (`==0.11.26`), pytest discovery
and options, and mypy's `source/` scope. The workflow no longer overrides Git
line endings, cancels superseded runs, caches uv, pins Python or uv through
`setup-uv`, or runs `compileall`.

Why: The cross-repo spec keeps local and CI invocations aligned through project
configuration and gives repositories one recognizable CI shape. Moving the uv,
pytest, and mypy defaults into `pyproject.toml` makes the bare commands
authoritative in every environment instead of relying on workflow-only flags.

Consequences: Local pre-handoff validation still includes `compileall`, while
CI has four named checks inside the single Windows matrix job. CI resolves a
compatible interpreter from `requires-python = ">=3.14"`; this migration does
not add a `.python-version` pin. The required branch-protection check changes
from `gates` to `test (windows-latest)` and must be updated by the repository
owner at merge time. Add a minimal `.gitattributes` only if a runner actually
reports line-ending format drift; the migration's first CI run did not.

## 2026-06-21: Relative ("Humanized") Last-Played Timestamps

Status: Superseded in part by the 2026-06-30 home empty-state decision; for the exact absolute-string format (`%Y-%m-%d %I:%M:%S %p`), by the 2026-07-11 humanized absolute-format decision; and, for the grid sentinel's scope and the single-column `refreshCells` call, by the [2026-08-09 PB-sentinel decision](#2026-08-09-pb-columns-keep-their-na-sentinel-even-for-timestamps)

Decision: "Last played" renders as a relative, humanized string ("5 minutes ago") in both the home Scenario Stats block and the playlists grid, with the exact timestamp shown on hover (`%Y-%m-%d %I:%M:%S %p`). Formatting lives in a single shared pair of pure JS helpers (`relativeTime`/`absoluteTime`) in `assets/dashAgGridFunctions.js`. Rules: a single rounded unit, never compound — just now (≤60s, including ≤0 / future) → N minutes → N hours → N days → N months → N years, with months/years calendar-based and a `max(0, …)` clamp (no `Intl` dependency, no "over"/"about" prefix). The value stays relative all the way (no absolute-date cutover) because it is a staleness gauge, not a reference date. Timestamps are epoch **seconds** end-to-end (the JS multiplies by 1000). Sentinels: "Never" on the grid (in a playlist but never played), "N/A" on home (no selection / not in DB) — never blank. The home value self-updates via a dedicated 30s `dcc.Interval` (decoupled from `polling_interval`); the grid live-ticks via a dedicated interval + `refreshCells({force: true, columns: ['last_played_sort']})`.

Why: A relative string answers "how stale is this?" directly, while the tooltip preserves the exact instant. Hand-rolled formatting (~30 lines) is simpler than `Intl` for an English-only app and fully controls the edges; calendar-based month/year math matches what a human reading two dates would say and avoids day-division boundary fudges.

Consequences: Shipped in PRs #17/#19 (Phase 1: shared helpers, home self-update, grid render-on-load) and #23 (Phase 2: grid live-ticking). Exact-timestamp access is hover-only (tooltip), consciously waived for this local single-user app. For how grid colDef `{"function": ...}` strings invoke these helpers, see the 2026-06-20 "Reference dash-ag-grid Grid Functions By Bare Name" entry. This entry distills and replaces `docs/relative_timestamp_proposal.md`, now deleted.

## 2026-06-30: Model Home Last-Played Empty States Explicitly

Status: Superseded in part, for the exact absolute-string format (`%Y-%m-%d %I:%M:%S %p`), by the 2026-07-11 humanized absolute-format decision

Supersedes: The home sentinel and hover-only tooltip interaction in the 2026-06-21 relative timestamp decision. The playlist-grid behavior and shared timestamp formatting rules remain unchanged.

Decision: Home Scenario Stats distinguishes three "Last played" states: no scenario selected renders `—`; a selected scenario with no local play data renders `Never`; and a selected scenario with play data renders the relative timestamp. Only a real timestamp receives the dotted underline and `cursor: help` affordance. Its exact local timestamp (`%Y-%m-%d %I:%M:%S %p`) is available by hover, keyboard focus, or touch. Empty states are not focusable and disable the tooltip entirely.

Why: `—` communicates an unselected field without implying missing or failed data, while `Never` communicates a known selected scenario with no recorded plays. Showing the affordance only when more information exists keeps the interaction honest and avoids a tooltip that merely repeats an empty-state value.

Consequences: The home callback owns the empty-state value and tooltip affordance alongside the raw timestamp. The clientside relative-time callback continues to own the live-updating visible timestamp. A selected scenario missing from the local database is treated as having no local play data; temporary loading or error states must not be mapped to `Never`.

## 2026-07-01: Keep Scenario Rank Consistent With Score-Aware Refreshes

Status: Superseded in part, for the exhausted-loop notification ("asks the user
to click Refresh" in Consequences below), by the
[2026-08-03 console-only background diagnostics decision](#2026-08-03-background-rank-diagnostics-are-console-only).
Every other part of this entry remains Accepted.

Supersedes: The `ThreadPoolExecutor(max_workers=2)` high-score refresh and the
decision not to provide manual rank refresh in the original scenario rank
proposal (since distilled into this log and deleted).

Decision: After a local high score, run a bounded score-aware refresh using a
daemon `threading.Timer` chain with delays of 2, 4, 8, 16, and 32 seconds. Accept
the leaderboard as caught up only when its score reaches the two-decimal floor of
the local score. Route every automatic rank-cache write through one process-locked
monotonic writer so a lower score or transient `UNRANKED` result cannot replace a
known better value. The home rank widget passively re-reads rank and total caches
on its existing interval without making network calls, including when those cache
files are older than their normal TTLs. A user-clicked Refresh performs one
authoritative fetch and may deliberately write a lower score or `UNRANKED` result.

Why: KovaaK's leaderboard updates are eventually consistent, so the old single
post-PB fetch could persist lagging data for the week-long cache TTL. Timer
attempts keep delayed work off a bounded executor, centralized write arbitration
prevents loop/read races, and the cache-only UI poll surfaces successful background
writes within about one second. Automatic rechecks after the bounded window would
hammer permanently divergent offline/server-down scores; explicit Refresh gives
the user a bounded escape hatch instead.

Consequences: Automatic rank displays move forward by score and never flicker from
a known rank to `UNRANKED`; explicit Refresh is board-authoritative and can move
backward after a leaderboard reset. Interval ticks resolve only cached leaderboard
IDs, read rank and total files independent of TTL, emit no repeated warning/error
toasts, and make zero KovaaK's requests. A refresh loop that exhausts leaves the
previous cache untouched and asks the user to click Refresh. The retry schedule is
a code constant, not configuration.

## 2026-07-03: Import Benchmarks From Evxl And KovaaK's

Status: Accepted (amended by
[2026-09-26](#2026-09-26-a-read-only-check-finds-bundled-benchmarks-that-kovaaks-changed):
KovaaK's threshold and scenario changes under an unchanged benchmark ID are
now found by the importer's read-only drift check, which names the files a
forced refresh regenerates)

Decision: The benchmark importer uses Evxl to resolve playlist names and codes,
and KovaaK's to fetch benchmark rank thresholds. In project terminology, a
*playlist* is a bare scenario list without rank data; a *benchmark* is a
playlist plus rank thresholds and colors. Generated benchmark JSON carries a
`generated_from` provenance stamp containing the Evxl sharecode, KovaaK's
benchmark ID, ordered rank-color pairs, generation timestamp, and generator
name.

Why: KovaaK's playlist search cannot resolve every known sharecode, while Evxl's
exact-code endpoint can; Evxl does not expose the per-scenario rank thresholds,
so KovaaK's remains authoritative for those values. The terminology distinguishes
the app's playlist import from the richer files produced by the importer.
Provenance makes the upstream inputs inspectable and allows generated files to be
checked for stale or mismatched benchmark metadata.

Consequences: Keep Evxl-specific resolution and snapshot handling in
`scripts/benchmark_importer/` unless an app-side feature explicitly adopts that
dependency. Preserve rank-color order when comparing provenance because colors
pair positionally with KovaaK's thresholds. Conflicting duplicate Evxl
sharecodes must be skipped and reported rather than resolved first-wins because
a missing benchmark is visible and recoverable, while silently pairing the wrong
rank thresholds is not. KovaaK's threshold changes under an unchanged benchmark
ID remain invisible to provenance checks and require an explicit forced refresh.

## 2026-07-06: Coalesce Pending Home Run Events

Status: Accepted

Decision: Home's `check_for_new_data` callback is the sole consumer of the
process-wide run-event deque. On each invocation it drains all pending messages,
lands on the most recently played scenario when automatic scenario switching is
enabled, and publishes a JSON-safe `run-events` summary for that scenario.
`generate_graph` rebuilds from the already-current in-memory stores and creates
toasts from that summary only when `run-events` triggered it. A single run keeps
the existing per-run toast behavior; a backlog produces one scenario-named
summary based on the latest matching run. The watchdog must successfully load a
run into the stores before enqueueing its message. The supported usage model is
one active Home tab; extra tabs remain crash-safe but unsynchronized.

Why: Home's interval does not run while the page is unmounted, so queued events
previously replayed one tick at a time on return. That rebuilt the same final
plot repeatedly, moved the scenario dropdown through stale history, and emitted
stale toast batches. Enqueue-before-load also allowed a consumer to rebuild
before the corresponding run was queryable, or to toast a run whose second parse
failed.

Consequences: A backlog is consumed in one tick, produces at most one dropdown
change and one toast batch, and cannot expose a message without queryable run
data. Mixed-scenario counts describe only the landing scenario. Nonmatching
events are discarded when automatic switching is off, preserving the previous
policy without wasting ticks. Coherent multi-tab delivery would require a
broadcast or push transport and remains outside this local single-user design.

## 2026-07-06: One Word Per Concept In Leaderboard Verbiage

Status: Accepted

Decision: "Rank" was used for both benchmark tiers (Bronze/Silver/..., Rank
Overlay) and leaderboard placement (Home "Rank:", grid "Current Rank"),
mirroring a split in the ecosystem (KovaaK's leaderboards: rank = position;
Voltaic/Aimlabs: rank = tier). In user-facing text, **Rank** means tier only,
**Position** means leaderboard placement ("Total Players" for board size), and
**PB** prefixes stats of the personal-best run (PB Score, PB cm/360, PB
Accuracy). "Unranked" is retained as KovaaK's own term for having no leaderboard
entry.

Consequences: Labels, plot annotations, and toasts follow the invariant.
Internal identifiers, component ids, and row field names keep their old names
because this is a label-only rename. New UI text must not reintroduce "rank" for
leaderboard placement.

**Superseded in part (2026-10-04).** Row field names no longer all keep their
old names: the playlist scenario table's Position and PB Score fields now say
`position` and `pb_score`. Every other internal identifier still keeps its
old name
([2026-10-04](#2026-10-04-the-scenario-tables-row-fields-use-the-words-on-screen)).

## 2026-07-06: Let The Playlist Scenarios Grid Own Vertical Scrolling

Status: Accepted

Decision: Bound the playlist scenarios page to the Mantine AppShell content
viewport and let the AG Grid use its normal layout with an internal vertical
scrollbar. The page Stack and Dash Loading wrappers form a flex column, and the
grid fills the remaining space with a 300px minimum height. Keep the existing
content-based column sizing and capped flexible Scenario column.

Why: `domLayout: autoHeight` expanded the grid to every row, so the document
scrolled and carried the column headers out of view on large playlists. A
bounded grid keeps the headers visible while the user sorts and scans scenarios
deep in the playlist, and restores row virtualization.

Consequences: Short playlists show empty grid body below their final row instead
of collapsing the grid. Very short windows may still scroll the page to preserve
the 300px usable minimum. The layout tracks AppShell header and padding variables
instead of duplicating their pixel values.

## 2026-07-11: Move The API Cache Under data/cache/

Status: Accepted

Decision: Relocate the runtime API cache root from `cache/` to `data/cache/`
as a plain path change, with no in-app compatibility migration. An existing
`cache/` directory is moved by hand after the change lands.

Why: The 2026-06-22 entry grouped user/runtime state under `data/` but
deferred the cache to a dedicated compatibility migration. The app currently
has exactly one user and the cache is fully regenerable from the API, so
migration code would outlive its single use; a one-time manual move (or just
letting the cache rebuild) covers it.

Consequences: All runtime state — logs, preferences, user playlists, and the
cache — lives under one ignored `data/` root. A legacy `cache/` root left in
place is silently ignored; `.gitignore` keeps its entry so pre-move checkouts
stay clean. Revisit an in-app migration only if the app gains users beyond
its author.

## 2026-07-15: Stream Playlist Positions With Generation-Scoped Progressive Fill

Status: Superseded in part, for the aggregate completion toast alone, by
the
[2026-08-22 in-place-only entry](#2026-08-22-the-playlist-fill-reports-degradation-in-place-only)
(the fill states degradation in the page's status line and emits no
notification). The fill mechanism, generation scoping, tombstones, and
status settling are unchanged and remain Accepted.

Supersedes: The blocking all-scenarios load and Dash Loading wrapper for the
per-playlist scenario grid. The bounded, grid-owned scrolling decision from
2026-07-06 remains in force.

Decision: Opening `/playlists/<code>` has two phases. Phase 1 paints every row
from local stats plus TTL-ignored rank caches, with explicit per-cell pending
flags for unresolved Position, Total Players, and Percentile values. Phase 2
hydrates leaderboard IDs once, then runs the normal cache/network lookup path
through the existing four-worker fan-out in one daemon-thread fill. Workers
stream complete row dictionaries into a lock-guarded in-memory registry keyed
by a per-open generation token. A one-second, enable-only interval drains those
rows through AG Grid update transactions; row identity is
`generation_token:playlist_order`, so a superseded response cannot update the
current grid.

Starting a fill synchronously cancels every other live generation. Completion
and cancellation become bounded tombstones with final counters, a terminal
state, and an atomic consumed flag. The first terminal tick alone drains final
updates, rebuilds unresolved cancelled rows cache-only, settles the status, and
emits any aggregate completion toast; later ticks only reassert the settled
status. Consumed tombstones drop queued rows and finalization payloads, but stay
in the same eight-item retention set as unconsumed tombstones. Overflow evicts
consumed before unconsumed, oldest first within each class, and the cap is
enforced at every terminal transition.

Pending state is never inferred from null values: resolved `UNRANKED` Position
is valid with a null sort key. Completed/finalized rows clear all pending flags.
Outcomes are counted before row formatting as fresh, `UNKNOWN`, or structurally
`served_stale`; the transient stale marker is never written to the rank cache.
Completion uses the existing red/yellow/silent failure tiers without
per-scenario toast spam. The API coordination signal keeps two monotonic
timestamps: interactive rank activity includes cache hits, while network
success changes only after a real successful HTTP response.

Why: Cold or flaky playlist opens previously hid six locally available columns
behind minutes of blocking API work. Progressive fill makes the training table
useful immediately while preserving the existing cache freshness and lookup
semantics. Generation-scoped row IDs plus consumed tombstones close the races
created by navigation, two tabs, callback responses already in flight, and
DashProxy's spurious initial callback behavior without adding a persistent job
system.

Consequences: The grid no longer uses `dcc.Loading`; animated CSS placeholders
and a `done/total` status provide progress. Clean fills clear the status and stay
silent, degraded fills retain a compact summary, and cancelled fills settle as
interrupted with no cell left pending. The registry is process-local and
single-user: reloads start a new fill, a second tab cancels the first tab's
network work, and completed API calls still warm the normal atomic disk caches.
Shipped in PR #127.

## 2026-07-16: Keep Pre-Hydration States Honest

Status: Accepted

Decision: Empty-state copy renders only after the owning data callback resolves.
AG Grid layouts omit initial `rowData` so the built-in loading overlay owns the
hydration gap. Plot layouts use a transparent, annotation-free placeholder;
`generate_empty_plot` is reserved for resolved-empty results.

Consequences: Initial page hydration stays visually neutral and never makes a
false no-data claim. Callbacks that resolve to empty grid rows or empty figures
continue to show their explicit empty-state guidance.

## 2026-07-17: Absorb Poll-Tick Bursts With Threads, Not Visibility Gating

Status: Accepted

Decision: Waitress runs with 8 worker threads (PR #116) as the sole fix for
poll-tick pressure. The demand-side alternative — pausing Home's
`interval-component` while the tab is hidden (Page Visibility API) — stays
unbuilt; its pre-approved design is parked as a kickoff prompt in
`ignore/prompts/icebox/` for reactivation if the symptom returns.

Why: Every Home polling tick (1 s default) fires three callback POSTs at once
(`check_for_new_data`, `flush_background_notifications`, and the cache-only
branch of `get_scenario_rank`). Against Waitress's default 4 threads, that
burst plus one thread held by a slow KovaaK's fetch (slow spells reach ~28 s)
left zero headroom, and a single idle tab produced task-queue-depth warnings.
Raising supply to 8 threads was deliberately tried first as the minimal fix,
with visibility-gated polling queued as the contingent next step; four days of
post-merge logs showed zero warnings, so the contingency never fired. Push
delivery (WebSocket/SSE) was also rejected: this is a single-user local app,
and with the warnings gone the polling cost argument for push collapses.

Consequences: An idle-but-hidden Home tab still polls (~3 POSTs/s of cheap
cache-only work) — accepted chatter, not a defect. If queue-depth warnings
reappear, reach for the iceboxed visibility-gating prompt (gate on
`document.hidden`, never window focus: an unfocused-but-visible window on a
secondary monitor must keep polling) before raising threads further.

## 2026-07-18: Leaderboard Mapping Reads Through an mtime-Revalidated In-Memory Mirror

Status: Accepted

Decision: `get_cached_leaderboard_id` serves lookups from a module-level parsed
copy of `scenario_name_to_leaderboard_id.json`, revalidated on every read by
comparing the file's identity — `(path, st_mtime_ns, st_size)` from one
`stat()` call — against the signature recorded when the copy was parsed. In
cache-policy terms: read-through population, write-around writes
(`save_leaderboard_id` still writes only the file), revalidate-on-read
coherence. Disk remains the source of truth; memory is a verified mirror. The
check-and-load runs under `_CACHE_IO_LOCK`, which `_write_json` also holds, so
lookups cannot interleave with in-process writes.

Why: The mapping file is a whole-store key-value file (~140KB, ~1,000 entries,
append-mostly immutable facts) consulted once per rank lookup, so every point
lookup paid a full parse. The playlist overview's "Show hidden" toggle made
this visible: rebuilding all 217 rows performed 1,062 cache-only rank lookups
and re-parsed the same file 1,062 times (~150MB of JSON) — measured at 0.77s
per toggle, and again on every 1s warmup-interval repaint. The mtime cache
alone cut the build to 0.19s; per-build memoization alone reached only 0.44s
because playlist overlap is modest (1,062 lookups over 659 distinct scenarios,
1.61x), so the per-lookup parse, not duplication, was the dominant cost.

Alternatives considered: (a) a loading spinner — rejected: the row-build
callback is shared with the warmup interval and refresh-store bumps, so any
`dcc.Loading`/`running=` indicator flashes on every automated repaint, and it
decorates waste rather than removing it; (b) per-build memoization of rank
resolution in the overview service — deferred, not rejected: it would add
snapshot consistency (the R11 property scenario stats already have) and take
0.19s to 0.11s, but is no longer the headline fix; (c) write-through (updating
the in-memory copy in `save_leaderboard_id` instead of revalidating) —
rejected: it maintains coherence only for writes made through this process's
write path, and the cache conventions explicitly support external mutation
(deleting `data/cache/` mid-run, other processes); trusting memory
unconditionally would invert the source of truth. As a redundant addition on
top of revalidation it buys one ~1ms parse per rare write at the cost of a
three-way coherence invariant (file, dict, signature) in the write path;
(d) SQLite — unchanged from the 2026-06 cache-layer decision: indexed point
reads would dissolve this whole class of cost and subsume this fix, but the
migration stays parked behind its documented triggers (rank history,
multi-record queries, transactional guarantees).

Consequences: `api_service` is no longer fully stateless — this one file has
an in-memory mirror, with the invariant that every serve is preceded by a
fresh `stat()` proof. The signature includes the resolved path so tests that
repoint `CACHE_DIR` cannot alias a stale copy; `st_size` guards against
same-mtime rewrites on coarse-timestamp filesystems. Metadata revalidation
inherently cannot detect a rewrite that preserves both size and timestamp
(deliberate `os.utime` forgery after an in-place edit — the known limit of
every mtime-keyed cache, `.pyc` included). This is an accepted risk, not an
oversight: the PR #147 review asked for a bounded forced refresh and a
60-second re-parse backstop was briefly added, then removed at the
maintainer's direction — a periodic redundant reload with no intervening
write contradicts the cache's purpose (fast reads until the next write), no
realistic writer forges timestamps (atomic replace, editors, and restores
all shift mtime_ns or size), and the only actor who could is the single
user poisoning their own local cache. A content-hash key was also rejected:
it must read the whole file per check (~146ms vs ~27ms per toggle build for
`stat`), returning a third of the original cost to buy a guarantee only the
forgery scenario needs. A regression test pins the accepted behavior
(forged rewrite served until the next genuine write) so it reads as
deliberate. A missing mapping file no
longer logs a read-failure warning per lookup (the stat short-circuits the
read), and a malformed file warns once per file version instead of once per
lookup. All `resolve_leaderboard_id` callers (Home rank display, playlist
drill-in fill, warmup worker, watchdog rank-freshness timers) share the
parse-free path. The other cache files (per-scenario rank, totals) stay as
direct per-read files: small, per-key reads where mirroring would add
bookkeeping for little gain. Regression tests pin the single-parse property,
write-then-read invalidation, external rewrite, deletion, and malformed-file
tolerance.
