# App Messaging Consistency

Status: Proposed
Date: 2026-08-21

## TL;DR

The app's user-facing text was written one feature at a time, and it shows.
The same condition is worded four different ways on four pages, punctuation
and casing drift from surface to surface, and some toasts still carry the
developer's voice. This proposal writes down one short set of copy rules,
lists every string the rules change, and ships the whole sweep in one
implementation PR so the app reads as if one person wrote it.

## Decisions needed

Four product rulings. Everything else in this proposal is author-owned copy,
gathered in the Design section's Copy block for the maintainer's redline pass.

### D1 — Shape of the Scenario Stats Position hint

Status: Open

The Position field on Scenario Performance glues a short hint to its value,
in three variants that share one slot:

```
N/A — set your KovaaK's username in Settings
4,022 of 8,461 (52.47% Percentile) — lookup failed, Refresh to retry
4,022 of 8,461 (52.47% Percentile) — from cache, Refresh to update
```

Measured at the running app (2026-08-21, 300 px stats box, 14 px value, the
hint dimmed at the xs size): a full position value is 208 px wide. Any hint
that keeps an instruction ("Refresh to update") wraps to a second line and
pushes the adjacent Refresh button onto a third. A short qualifier stays on
one line.

**Recommendation: middle-dot fragments, instruction halves dropped.**

```
N/A · set your KovaaK's username in Settings
4,022 of 8,461 (52.47% percentile) · lookup failed
4,022 of 8,461 (52.47% percentile) · from cache
```

The hint is a status readout glued to a value, so under the punctuation rule
it stays a bare fragment, and the middle dot is the separator the app already
uses for fragment chains in the grid status lines. The Refresh button sits
beside the value with the same icon, and its tooltip already explains that a
displayed value can come from a local cache, so the instruction half repeats
what is on screen. The unset variant keeps its Settings link because there is
no adjacent control for it.

Choosing differently: keeping the instruction halves (`· from cache, Refresh
to update`) preserves the explicit affordance at the cost of a two-line field
that reflows the Refresh button on every stale render. Full sentences
(`N/A. Set your KovaaK's username in Settings.` / `…Percentile). From cache.
Refresh to update.`) put two periods beside a parenthesised value and wrap the
same way.

### D2 — Casing of control labels

Status: Open

Control labels mix two conventions with no rule behind them. In the Chart
options panel alone: "Rank Thresholds", "PB Score", "Score Threshold
Overlay", "Score Threshold Percentage", "Score Threshold Verdict", and "Run
Notifications" are Title Case; "Show all ranks", "Point size", "Point color",
"Use default", "Top N scores", and "Follow newly played scenario" are
sentence case. Modal titles are Title Case ("Import Playlist", "Delete
Leftover Files") while the alert beside them is sentence case ("Leftover
playlist files") and every toast title is sentence case.

**Recommendation: sentence case for everything except page titles, section
headings, and grid column headers.** Controls (labels, switches, buttons,
placeholders), toast and alert titles, modal titles, status lines, and
tooltips all take sentence case; "Scenario Performance", "Scenario Stats",
"Run Data Points", "Median Percentile" and their kind keep Title Case as the
headings they are. Proper names keep their own capitals (KovaaK's, Steam ID,
PB, SteamID64). The two chart modes "Score vs Sensitivity" and "Score vs Time"
are treated as named modes and keep their capitals; help text that quotes a
control repeats the control's on-screen casing.

This is the direction the most recent rulings already lean: the ratified Run
Data Points group pairs a Title Case heading with sentence-case fields. The
consequence is renaming six Title Case switch labels, two of them ratified on
2026-08-21 ("Run Notifications", "Score Threshold Verdict"), plus three modal
titles and the chart's "PB Score" and "Score Threshold" annotations, which
follow their switches.

Choosing differently: Title Case for all controls renames the six sentence-case
labels instead, and long switch labels read heavy ("Follow Newly Played
Scenario"). Leaving casing unruled keeps today's mix, which is the visible
symptom this proposal exists to remove.

### D3 — Noun on the two playlist status lines

Status: Open

With no username set, the Playlists overview says "Percentiles unavailable"
and the per-playlist scenario table says "Positions unavailable". The note
that seeded this proposal asked for a deliberate ruling rather than an
accident.

**Recommendation: keep the split.** Each line names the column family it
explains: the overview's empty cells are the Median and Lowest Percentile
columns, the drill-down's are Position, Total Players, and Percentile. One
noun for both would be wrong on one page. Only the punctuation is aligned.

Choosing differently: one noun ("Positions unavailable" on both) buys a
verbatim match between two lines that are never on screen together, at the
cost of the overview naming a column it does not have.

### D4 — The coaching flourishes

Status: Open

Three run-toast fragments are tone, not information: "Keep grinding..." on a
below-threshold run, "Ready to move on." on a passed run that did not place,
and the "While you were away" digest title. They are the only places the app
has a personality, and the product's name suggests it wants one.

**Recommendation: keep all three, and fix only their typography.** "Keep
grinding..." becomes "Keep grinding…" with the single ellipsis character, so
the app has one ellipsis form. The other two are already correct sentences.

Choosing differently: dropping them makes the run toasts strictly factual.
That is cleaner but colder, and the 2026-08-03 notification policy already
files run toasts under "achievement / coaching", so the flourishes are in
policy.

## Problem

The inventory was taken against `39f96d4` (main, 2026-08-21) by reading every
user-facing string in `source/pages/`, `source/app_shell.py`, the service
messages that reach a toast or alert (`source/kovaaks/data_service.py`,
`source/kovaaks/api_service.py`, `source/utilities/store_schema.py`,
`source/my_watchdog/file_watchdog.py`), the chart annotations in
`source/plot/plot_service.py`, and the grid renderers in `assets/`. It
supersedes the 2026-08-11 design note that seeded it; that note's one
"carry-along fix" (the Home restart hint saying "the dashboard") has already
shipped in `b288b9f` and is not repeated here.

The same condition, four shapes, is the seed symptom:

| Surface | Current text |
| --- | --- |
| Playlists overview | `Percentiles unavailable. Set your KovaaK's username in Settings.` |
| Playlist scenario table | `Positions unavailable — set your KovaaK's username in Settings` |
| Scenario Performance, stats folder | `No stats directory configured — set it in Settings` |
| Scenario Performance, Position | `N/A — set your KovaaK's username in Settings` |

Only the first postdates the 2026-08-11 no-em-dash ruling and is already in
the target style. Reading the whole surface found eight further kinds of
drift, each small, together the "vibe-coded" feel:

1. **Em dashes.** 25 sites. 23 join clauses in prose; 2 are typographic
   (the `—` empty-value glyph under Last played, ratified 2026-06-30, and
   the scenario/score separator in run-toast bodies).
2. **Terminal punctuation.** Most sentences end with a period; the four
   above and a handful of grid tooltips do not. Three messages join
   sentences with a semicolon; one ends with an exclamation mark.
3. **Contractions.** "Couldn't refresh", "Couldn't update", "can't read your
   runs" beside "Could not save", "could not be checked", "cannot look one
   up". Full forms are the majority by nine sites to four.
4. **Ellipses, three ways.** `Keep grinding...` and every placeholder use
   three periods; the fill status uses the `…` character; one tooltip uses
   `, ...` inside parentheses.
5. **Casing.** See D2.
6. **Quoting control names.** `Toggle "Show hidden"` in two places, bare
   `press Detect my accounts again`, `then Save`, `Needs Rank Thresholds
   turned on` everywhere else.
7. **Vocabulary.** "the dashboard" in the setup card against "this app" and
   "the app" on Settings and in every store message; "Stats directory" as a
   field label against "stats folder" in its own description and the setup
   card; "served from cache" in toasts against "from cache" in status lines.
8. **Developer voice reaching the screen.** Import refusals and startup
   playlist warnings are built in `data_service.py` and shown verbatim:
   `Failed to load playlist data for playlist code: X`, `Invalid playlist
   data returned by API for playlist code: X`, `Skipping playlist file X:
   missing or blank playlist code; add a \`code\` field.` (backticks render
   literally). The Steam-ID mismatch toast quotes its values in single
   quotes; nothing else does.
9. **A stray capital.** The Position value reads `(52.47% Percentile)`
   mid-phrase.

Why now: the no-em-dash ruling explicitly deferred the shipped-copy sweep to
"a future review of all app messaging" rather than letting each PR fix what
it touched, and the last three feature PRs have each shipped copy in the new
style beside old copy in the old one. The longer the sweep waits, the more
the review tail of every PR spends on per-line style questions that one
ruling would settle.

## Design

### The rules

These are the durable record. The decision-log entry carries them with the
rationale; AGENTS.md carries the operative form an implementer needs at write
time, replacing the current one-line em-dash convention.

1. **If it has a subject and a verb, it ends with a period. Status readouts
   do not.** `Settings saved.` and `No such folder.` are sentences.
   `Updating positions from KovaaK's… 12/40`, `Update interrupted · 8 of 40
   refreshed`, `3 of 40 positions unavailable`, and the Position hint (D1)
   are readouts and stay bare. A sentence that ends on an inline link puts
   its period in a **separate child after the anchor**, or it renders
   underlined as part of the link; `_username_unset_status()` in
   `source/pages/playlists.py` is the pattern.
2. **No em dashes.** Prose breaks into two sentences. A readout that chains
   fragments joins them with ` · ` (space, middle dot, space), which the grid
   status lines already use. Two exceptions, named so a later sweep does not
   delete them: the `—` empty-value glyph under Last played when no scenario
   is selected (ratified 2026-06-30), and nothing else. The run-toast
   scenario/score separator becomes a colon.
3. **Casing** per D2.
4. **One ellipsis form.** The single `…` character, and only in an
   in-progress readout. Placeholders are bare noun phrases (`Select a
   scenario`, `Filter playlists`). The three-period form does not appear in
   app copy.
5. **No contractions.** `Could not`, `cannot`, `does not`.
6. **Control names are unquoted and carry their on-screen casing.** `Turn on
   Show hidden`, `press Detect my accounts again`, `then Save`. A literal
   file key keeps double quotes (`a "code" field`, as the store messages
   already do). Imported playlist names keep double quotes because they are
   user data that can contain anything.
7. **Vocabulary.** The software is *this app* or *the app*, never *the
   dashboard* (the 2026-08-21 launcher ruling: it reads as the browser page).
   The run source is the *stats folder*. A position that came from a local
   cache is *from cache*. *Position*, *Rank*, and *PB* keep the 2026-07-06
   meanings. The pointer to the log is always `See data/logs/debug.log.`
8. **A message that reaches the screen is user copy wherever it is built.**
   Service-layer strings that a page shows verbatim follow every rule above;
   the diagnostic detail stays in the log line beside them.
9. **Error copy says what happened, then what to do**, in that order, and
   the toast title carries the verdict (unchanged from 2026-08-03).

### Copy

Every user-facing string this proposal adds or edits, grouped by surface.
`→` separates before and after. *(ratified YYYY-MM-DD)* marks copy a
decision-log entry fixed; changing it here is deliberate and the shipping PR
adds a "superseded in part, for copy" note to that entry. Strings not listed
are unchanged. `[Settings]` is the inline anchor; its trailing period is a
separate child.

**Scenario Performance: hints, stats, and the setup card**

- Stats folder hint: `No stats directory configured — set it in [Settings]`
  → `No stats folder configured. Set it in [Settings].`
- Position hint, unset *(ratified 2026-08-09)*: `N/A — set your KovaaK's
  username in [Settings]` → `N/A · set your KovaaK's username in [Settings]`
  (D1)
- Position hint, lookup failed: ` — lookup failed, Refresh to retry` →
  ` · lookup failed` (D1)
- Position hint, stale: ` — from cache, Refresh to update` → ` · from cache`
  (D1)
- Position value: `4,022 of 8,461 (52.47% Percentile)` → `4,022 of 8,461
  (52.47% percentile)`
- Setup card body, stats folder state *(ratified 2026-08-11)*: `No KovaaK's
  stats folder was found, so the dashboard can't read your runs yet. Set it
  in Settings.` → `No KovaaK's stats folder was found, so this app cannot
  read your runs yet. Set it in Settings.`
- Setup card fine print *(ratified 2026-08-11)*: `Skipping username disables
  rank lookups. You can set it anytime in Settings.` → `Skipping turns rank
  lookups off. You can add your username anytime in Settings.`

**Scenario Performance: controls and help text** (D2 unless noted)

- `Rank Thresholds` → `Rank thresholds`; its dependent help text `Needs Rank
  Thresholds turned on.` → `Needs Rank thresholds turned on.`
- `PB Score` (switch) → `PB score`
- `Score Threshold Overlay` → `Score threshold overlay`
- `Score Threshold Percentage` → `Score threshold percentage`
- `Score Threshold Verdict` *(ratified 2026-08-21)* → `Score threshold
  verdict`
- `Run Notifications` *(ratified 2026-08-21)* → `Run notifications`; its
  dependent help text `Needs Run Notifications turned on.` → `Needs Run
  notifications turned on.`
- Top N scores help text: `How many of your best scores to plot per
  sensitivity — or per day in Score vs Time — within the selected date range.
  A new run that lands in the top N also triggers a notification.` → `How
  many of your best scores to plot per sensitivity within the selected date
  range, or per day in Score vs Time. A new run that lands in the top N also
  triggers a notification.`
- Placeholders: `Select a scenario...` → `Select a scenario`; `Select a
  playlist...` → `Select a playlist` (shared with Aim Training Journey);
  `Score Percentage...` → `Percentage`
- Empty chart, incomplete controls: `Choose a Top N value and start date to
  plot this scenario.` → `Set Top N scores and the oldest date to plot this
  scenario.` (names the controls as labelled)
- Empty chart, date range: `Choose an older start date or play more runs.` →
  `Choose an older date or play more runs.`
- Chart annotations and legend names: `PB Score (123.00)` → `PB score
  (123.00)`; `Score Threshold (118.00)` → `Score threshold (118.00)`

**Scenario Performance: toasts**

- Refresh failed, body: `Couldn't refresh — position unchanged.` → `Could
  not refresh. The position shown is unchanged.`
- Refresh served stale, title: `Position refresh failed` → `Cached position
  shown`; body: `Couldn't refresh — showing the cached position.` → `Could
  not refresh. The position shown is from cache.` This gives the served-stale
  toast the title of its own that the 2026-08-03 entry and `tech_debt.md`
  left open; the color question there stays open, and the red hard-failure
  toast keeps its title.
- Run verdict, scenario/score separator in all three live bodies:
  `1w4ts Reload — 125.00` → `1w4ts Reload: 125.00`
- Run verdict, below threshold: `…, 92.1% of PB — need 95.0%. Still your
  3rd-best at 0.35 cm/360. Keep grinding...` → `…, 92.1% of PB (need 95.0%).
  Still your 3rd-best at 0.35 cm/360. Keep grinding…` (D4)
- Backlog digest, passed: `3 new X runs. Latest: 120.00 — 96.2% of PB,
  passed threshold.` → `3 new X runs. Latest: 120.00, 96.2% of PB, above your
  95.0% threshold.`
- Backlog digest, below: `3 new X runs. Latest: 120.00 — 92.1% of PB, below
  the 95.0% threshold.` → `3 new X runs. Latest: 120.00, 92.1% of PB, below
  your 95.0% threshold.`
- Run import failure, single: `Could not process a new run file. See
  debug.log for details.` → `Could not process a new run file. See
  data/logs/debug.log.`; batch: `3 new run files could not be processed. See
  debug.log for details.` → `3 new run files could not be processed. See
  data/logs/debug.log.`
- Steam ID mismatch body: `Configured Steam ID '7656…' does not match
  KovaaK's user 'X' (actual Steam ID: 7656…).` → `The saved Steam ID 7656…
  does not match KovaaK's user X, whose Steam ID is 7656….`
- Startup playlist warnings (built in `data_service.py`, shown under
  "Playlist not loaded"):
  - `Playlist directory is missing: {root}` → `The playlist folder {root} is
    missing.`
  - `Failed to read playlist file: {file}` → `{file} could not be read.`
  - `Invalid JSON format in playlist file: {file}` → `{file} is not valid
    JSON.`
  - `Skipping playlist file {file}: missing or blank playlist code; add a
    \`code\` field.` → `{file} has no playlist code. Add a "code" field to
    it.`
  - `Skipping playlist file {file}: playlist code {code} already loaded from
    {source}.` → `{file} was skipped. Its playlist code {code} is already
    loaded from {source}.`
  - `Skipping playlist file: {store message}` → `{store message}` (the store
    message is already a full sentence naming the file)

**Playlists overview**

- Status, all hidden: `All playlists are hidden. Toggle "Show hidden" to
  manage them.` → `All playlists are hidden. Turn on Show hidden to manage
  them.`
- Warmup status, paused: `Updating percentile data: 8 remaining · paused;
  retrying at 3:05 PM` → `Updating percentile data: 8 remaining · paused
  until 3:05 PM`
- Type header tooltip: `Benchmarks carry rank thresholds (Bronze, Silver,
  ...) for their scenarios; playlists are plain scenario lists.` →
  `Benchmarks carry rank thresholds (Bronze, Silver, and so on) for their
  scenarios. Playlists are plain scenario lists.`
- Percentile placeholder tooltip: `Shown once all N played scenarios have
  data — open the playlist to fetch now` → `Shown once all N played scenarios
  have data. Open the playlist to fetch it now.`
- Modal titles: `Import Playlist` → `Import playlist`; `Delete Playlist` →
  `Delete playlist`; `Delete Leftover Files` → `Delete leftover files` (D2)
- Placeholders: `Filter playlists...` → `Filter playlists`; `KovaaK's
  playlist code...` → `KovaaK's playlist code`
- Import succeeded but hidden, title: `Playlist imported — not shown` →
  `Playlist imported but hidden`; appended hint: ` It could not be marked
  visible, so it may be missing from playlist selectors — toggle "Show hidden"
  on this page, then click its row's eye icon to show it.` → ` It could not
  be marked visible, so it may be missing from playlist selectors. Turn on
  Show hidden on this page, then click the eye icon on its row to show it.`
- Duplicate-and-hidden hint: ` It is currently hidden — toggle "Show hidden"
  on this page to unhide it.` → ` It is currently hidden. Turn on Show hidden
  on this page to unhide it.`
- Import refusals (built in `data_service.py`, shown under "Playlist import
  failed"; the diagnostic detail stays in the log line each already writes):
  - `Failed to look up playlist code {code}: KovaaK's API error.` → `Could
    not look up {code} on KovaaK's.`
  - `Failed to load playlist data for playlist code: {code}` → `No playlist
    matches the code {code}.`
  - `Found more than one playlist from code: {code}` → `More than one
    playlist matches the code {code}.`
  - `Invalid playlist data returned by API for playlist code: {code}` and
    `Invalid playlist data returned by API: {name} ({code})` → `KovaaK's
    returned unusable data for {code}.`
  - `Playlist code already exists: {code} is already imported as {name}
    ({code}).` → `{code} is already imported as "{name}" ({code}).`
  - `Failed to save playlist data: {name} ({code})` → `Could not save the
    playlist file for "{name}" ({code}). See data/logs/debug.log.`
  - `Cannot save this playlist: {name} ({code}) would replace a playlist
    file written by a newer version of this app.` → `"{name}" ({code}) would
    replace a playlist file written by a newer version of this app. Update
    the app to import it.`
  - `Cannot save this playlist: {file} already holds {name} ({code}). Delete
    that playlist first, then import again.` → `The file for this playlist
    already holds "{name}" ({code}). Delete that playlist first, then import
    again.`
- Delete refusals (shown under "Playlist delete failed" / "Cleanup failed"):
  - `Playlist code cannot be deleted: {code} is not a user playlist.` →
    `{code} is not one of your imported playlists, so it cannot be deleted.`
  - `Failed to delete playlist file: {path}` → `Could not delete {path}. See
    data/logs/debug.log.`

**Playlist scenario table**

- Status, unset username *(ratified 2026-08-09)*: `Positions unavailable —
  set your KovaaK's username in [Settings]` → `Positions unavailable. Set
  your KovaaK's username in [Settings].` (D3 keeps the noun)
- Status, unknown code: `Playlist code is not imported: {code}` → `No
  imported playlist has the code {code}.`
- Placeholder: `Filter scenarios...` → `Filter scenarios`
- Settled fill status, both shapes: ` · 5 from cache — KovaaK's unreachable`
  → ` · 5 from cache · KovaaK's unreachable`; `5 of 40 positions from cache —
  KovaaK's unreachable` → `5 of 40 positions from cache · KovaaK's
  unreachable`
- Fill summary toast, incomplete: `Couldn't update 3 of 40 positions; 5 more
  served from cache` → `Could not update 3 of 40 positions. 5 more are from
  cache.`
- Fill summary toast, stale: title `Positions served from cache` → `Cached
  positions shown`; body `5 of 40 positions served from cache — KovaaK's was
  unreachable` → `KovaaK's was unreachable. 5 of 40 positions are from cache.`
- Percentile header tooltip: `Your percentile on the scenario's global
  leaderboard — the share of players you place above (higher is better).` →
  `Your percentile on the scenario's global leaderboard: the share of players
  you place above. Higher is better.`
- PB cm/360 header tooltip: `Mouse sensitivity of your personal-best run, in
  centimeters of mouse travel per full 360-degree turn (higher = lower
  sensitivity).` → `Mouse sensitivity of your personal-best run, in
  centimeters of mouse travel per full 360-degree turn. Higher means lower
  sensitivity.`

**Settings**

- Field label `Stats directory` → `Stats folder`; its error `No such
  directory.` → `No such folder.`
- Steam ID error: `Enter a 17-digit SteamID64 — it starts with 7656119.` →
  `Enter a 17-digit SteamID64. It starts with 7656119.`
- Steam ID description: `Your 17-digit SteamID64. Optional; it disambiguates
  accounts that share a KovaaK's username.` → `Your 17-digit SteamID64.
  Optional. It tells apart accounts that share a KovaaK's username.`
- Save failed: `Could not save settings — nothing was written. See
  data/logs/debug.log.` → `Could not save settings, so nothing was written.
  See data/logs/debug.log.`
- Detection, no match: `No Steam account on this machine has a KovaaK's
  profile. Type your username in yourself — KovaaK's cannot look one up from
  a Steam ID.` → `No Steam account on this machine has a KovaaK's profile.
  Type your username in yourself. KovaaK's cannot look one up from a Steam
  ID.`
- Detection, unchecked: `2 Steam accounts could not be checked; press Detect
  my accounts again to retry.` → `2 Steam accounts could not be checked.
  Press Detect my accounts again to retry.`
- Picker description: `Choosing one fills the fields above; Save applies
  it.` → `Choosing one fills the fields above. Save applies it.`

**Aim Training Journey**

- Banner: `This page is still a work in progress!` → `This page is a work in
  progress.`
- Label `Checkpoint Hour` → `Checkpoint hour` (D2); empty chart: `Choose a
  Checkpoint Hour value to plot progress.` → `Set a checkpoint hour to plot
  progress.`

**Unchanged on purpose**

- The `—` empty-value glyph under Last played (rule 2).
- Every toast title not listed: they are already sentence case and carry the
  verdict.
- The store messages in `store_schema.py` (`{path} has no "schema_version"
  line. …`): already full sentences in the target style.
- The Settings version section, the bug-report link, the navbar, and the
  header tooltips.
- The launcher's and installer's console output, which the 2026-08-21
  launcher entry governs, and every `logging` line: neither is app copy.

### Testing the rule, not just the strings

Most of these strings are module-level constants, but the riskiest ones (run
verdicts, backlog digests, fill statuses, the import refusals) are built
inline in f-strings, which a constant-list check would miss. The guard should
therefore walk the AST: for every module under `source/`, visit every
`ast.Constant` whose value is a `str` (f-string literal parts arrive as
constants inside `ast.JoinedStr`, so inline bodies are covered), skip
docstrings (the first statement of a module, class, or function body), and
fail on any `—` outside an explicit allowlist holding the one ratified glyph
site. Comments never reach the AST, so the check cannot misfire on them. The
same walk can assert the three-period ellipsis is absent from string
constants. Anything beyond those two characters (casing, contractions) is
review territory, not a gate.

## Out of scope

- Console, launcher, and installer output, `logging` text, docstrings, code
  comments, and documentation prose. The rules govern what the browser shows.
- Softening the red hard-failure refresh toast to yellow: the `tech_debt.md`
  entry's color question stays open; this proposal resolves only the title
  half it depended on.
- A configured-but-wrong username, deferred by the 2026-08-09 entry.
- Restructuring the Steam-ID mismatch toast beyond its wording.
- Two empty-state messages inside `plot_service.py` (`No sensitivity data is
  available for this scenario yet.` and its Score vs Time twin): the page
  callbacks return their own empty chart before these paths are reached, so
  they are unreachable from the UI and are left alone rather than edited
  blind.
- The Aim Training Journey page beyond its banner and one label; its polish
  is a separate roadmap item.
- Any new string. This is a sweep; it adds no surface.

## Testing

- The AST guard described in Design, as a new test module under `tests/`.
- Every existing test that pins a changed string is updated, never loosened
  to a substring match: the page modules `test_home_rank_format.py`,
  `test_home_run_events.py`, `test_home_stats_dir_hint.py`,
  `test_playlist_pages.py`, `test_settings_page.py`, `test_ui_presentation.py`,
  and the service modules `test_data_service_extract.py`,
  `test_playlist_visibility_service.py`, plus whatever `rg` finds for each
  quoted string at implementation time.
- The standard local gates (`pytest`, `ruff format --check`, `ruff check`,
  `mypy`, `compileall`).
- One manual pass at the running app over every surface in the Copy block,
  including the D1 field with a real position value, to confirm nothing
  wraps or renders a period inside a link.

## Delivery plan

1. **This PR**: the proposal. Nothing ships until D1 to D4 are ruled and the
   Copy block has had its redline pass.
2. **One implementation PR**, after ratification, from a kickoff prompt that
   hands the implementer the ratified Copy block verbatim. One PR rather than
   one per surface because the rules are one ruling: splitting them would
   leave the app mid-style across a review window, which is the state this
   proposal exists to end. Suggested commit split: the copy and the rules
   (source and AGENTS.md), the tests and AST guard, then the docs. The docs
   commit carries the full shipping checklist: the decision-log entry with
   the rules and their rationale, "superseded in part, for copy" notes on the
   2026-08-03, 2026-08-09, 2026-08-11, and 2026-08-21 entries whose quoted
   strings change, the `tech_debt.md` edit for the refresh-toast title, a
   `product.md` line, and the deletion of this file. No capability spec
   covers app copy and this does not justify creating one. No hard
   dependency on other in-flight work.
