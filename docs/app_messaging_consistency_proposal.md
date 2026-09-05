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

Seven product rulings and one workflow ruling. D1 to D5 are the original
rows. D6 to D8 were added on 2026-09-04, after the maintainer's redline pass
asked whether the rules follow standard convention rather than taste and
commissioned a survey of the mainstream style guides and of current apps
(the copy conventions research note,
`ignore/design-notes/copy-conventions-research.md` in the main checkout,
dated 2026-09-04). The survey confirmed nine of the thirteen conventions it
tested and found the proposal against the guides on three, which are the
three new rows; its smaller findings are folded into the rules and the Copy
block as author redlines. The maintainer's leans on D6 to D8 are recorded
as leans: non-binding until ruled. Everything else in this proposal is
author-owned copy, gathered in the Design section's Copy block for the
maintainer's redline pass.

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
no adjacent control for it. The 2026-09-04 conventions survey found no guide
that prescribes a separator for a fragment chain and the middle dot in use
as the web's metadata separator; its one caution, that a screen reader may
skip the glyph, is met because each hint reads correctly without it.

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

The 2026-09-04 conventions survey endorses this row. The Microsoft style
guide, the Windows app writing guidance, Material, Atlassian, Polaris,
GitHub's Primer, Obsidian's plugin guidelines, and the Mantine docs all use
sentence case for controls, modal titles, and notification titles, and none
endorses capitalizing terminology that is not a proper noun; macOS is the
one platform that title-cases controls, and this is a Windows app. KovaaK's
own copy draws the same line, lowercasing generic nouns (scenario, playlist,
leaderboard) and capitalizing only named modes and products. One honesty
note for the decision-log entry: the same guides also lowercase page titles,
section headings, and column headers, so this proposal's Title Case
exception for those is house style, not convention. Extending sentence case
to them would rename surfaces the README, the specs, and the launch material
already name, and is left as a separate scope question.

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
The 2026-09-04 conventions survey endorses the split: Windows asks a label
to say what it describes, and each line names the columns on its own page.

Choosing differently: one noun ("Positions unavailable" on both) buys a
verbatim match between two lines that are never on screen together, at the
cost of the overview naming a column it does not have.

### D4 — The coaching flourishes

Status: Open

Two run-toast fragments are tone, not information: "Keep grinding..." on a
below-threshold run and "Ready to move on." on a passed run that did not
place. They are the only places the app has a personality, and the
product's name suggests it wants one. (A third, the "While you were away"
digest title, left with the digest when the celebration arc retired it: the
2026-09-02 celebrates-on-every-page entry.)

**Recommendation: keep both; "Keep grinding..." becomes "Keep grinding."
with a period.** "Ready to move on." is already a correct sentence. The
period rather than the single ellipsis character is the 2026-09-04
conventions survey's finding: Polaris and Google reject an ellipsis that
trails off for tone and Microsoft merely permits it, so the period is the
form every guide accepts, and it leaves rule 4 with no named exception. The
earlier recommendation, "Keep grinding…", would need that exception back.
Whether the miss line survives at all is taste: Atlassian and the Nielsen
Norman Group warn that a flourish on a repeated miss wears out, and a user
grinding one scenario sees this toast many times in a session; Apple's own
streak copy shows coaching lines work in success moments, and no guide
covers a miss. Maintainer lean (2026-09-04): keep the line, with the period.

Decide this with the launch visual in mind, not only the running app: the
launch prep notes want the announcement post to lead with a clip of a run
landing and its notification, so whichever way D4 goes, a run toast is the
first copy a cold reader sees.

Choosing differently: dropping them makes the run toasts strictly factual.
That is cleaner but colder, and the 2026-08-03 notification policy already
files run toasts under "achievement / coaching", so the flourishes are in
policy.

### D5 — Does the sweep gate the launch post?

Status: Open

The launch prep notes plan an announcement post led by a clip of a new run
updating the chart and its notification, with the leaderboard standing in
view. Both surfaces carry strings this proposal changes: the run-toast body
is an em-dash site, and the Position hint is D1. The same notes record that
"was this AI-written" was the first community question on a comparable
launch, and the no-em-dash ruling exists because the old copy reads that way.

**Recommendation: yes.** The implementation PR lands before the release the
post promotes, and the launch prep notes' pre-post checklist carries it as an
item. The cost is one more PR in front of the post; the sweep is a day of
mechanical work once the Copy block is ratified.

Choosing differently: the post's visual shows the old copy, and the rules
govern only strings written after launch. The app would be answering the
authorship question beside a screenshot of the copy the rule was written
against.

### D6 — Contractions

Status: Open. Maintainer lean (2026-09-04): adopt, pending the review's
stance.

Rule 5 as first drafted banned contractions: "Could not", "cannot", "does
not" everywhere, on the reasoning that full forms read terse and deliberate.
The 2026-09-04 conventions survey found this the one place the proposal is
unanimously against the guides. The Microsoft style guide, the Windows app
writing guidance, Google's developer style, Material, Apple's style guide,
Atlassian, and Polaris all say to use common contractions; Windows warns
that avoiding them makes an app read "too formal or even stilted". The
survey also looked at what makes prose read as machine-written, which is
the concern behind the 2026-08-11 no-em-dash ruling: the sources that name
a register tell name formality, and the one study with a measured result
separated machine text from human text by its lack of contractions. Nothing
found implicates contractions the other way.

**Recommendation: reverse rule 5.** Use the common contractions (can't,
couldn't, doesn't, isn't, wasn't, aren't, you're) and adopt Microsoft's
consistency clause: a contraction and its full form never both appear in
the app, so "can't" and "cannot" do not coexist. "Do not" survives only in
a warning the user must not skip, which is Material's carve-out; the app
has no such string today.

Consequence: the five Copy entries that expanded a contraction revert to
the contracted form (the two refresh-toast bodies, the setup card's
stats-folder body, and its unreadable-store title and body, the title
dropping out of the block because nothing else in it changes), and every
full-form negation on screen contracts: the seventeen block entries whose
rewritten text used a full form, plus eight strings the block had left
unchanged or uninventoried (the two store-alert titles, the "Skip was not
saved" toast title, the account-list detection line, the warmup's
"KovaaK's username is not configured." reason, the playlist-payload
neighbour "is not valid playlist data.", and the store layer's "is not
valid JSON." and "could not be read."). The Copy block below is written in
the contracted form; AGENTS.md's operative convention gains the never-mix
line.

Choosing differently: keeping full forms is a legitimate house voice, and
the block's earlier draft (every "Couldn't" expanded) shows what it looks
like. It should then be recorded as taste, because the claim that it is the
convention does not survive the survey.

### D7 — A sentence never opens with a runtime value

Status: Open. Maintainer lean (2026-09-04): adopt, pending the review's
stance.

Several rewritten messages began with a value the app fills in at runtime:
`{file} could not be read.`, `{code} is already imported as "{name}".`, and
every store message in `store_schema.py` (`{path} has no "schema_version"
line. …`). The redline pass asked for the value to come last, after a colon,
so the verdict leads and the value's edges are visible. The survey found no
guide behind the colon form (it is the log-line idiom rule 8 exists to keep
off the screen) but a direct Windows rule against the current shape, "Avoid
starting sentences with object names": a sentence that opens with a path or
a code may begin with a lowercase letter, a digit, or a backslash, and has
no visible start. Windows and Polaris both embed the value in the sentence
with a noun in front of it, and Atlassian's example does the same.

**Recommendation: add the clause to rule 9.** A noun names the value before
it appears (`Couldn't read the playlist file {file}.`), a long path goes
last in its sentence or in a sentence of its own, and user-typed free text
keeps its quotes under rule 6. This delivers the redline's "verdict first,
edges visible" without the colon.

Consequence: eight Copy entries restructure (four startup playlist warnings,
the store-message pass-through, the duplicate-import refusal, the
newer-version save refusal, and the not-yours delete refusal), and the
store messages join the sweep instead of standing as unchanged: every
`{path} …` message gains "The file" in front of the path, one change at the
six composition sites in `store_schema.py`, with the fragments the
validators raise left as they are. The 2026-08-11 schema entry's quoted
messages get a "superseded in part, for copy" note; the stamp script prints
the same messages to its console and follows along, because it calls the
same function.

Choosing differently: exempt the store messages as the named exception,
which keeps the Settings page's store alert and the stamp script's console
output byte-identical, at the cost of one sentence family that starts with a
Windows path.

### D8 — Control names in prose carry their type

Status: Open. Maintainer lean (2026-09-04): adopt, pending the review's
stance.

Rule 6 named a control in prose bare, in its on-screen casing: "Turn on
Show hidden to manage them." The redline pass observed that once D2
lowercases the labels, a verb-phrase label disappears into the sentence
around it, and asked for the name to be set off, for instance in bold. The
survey found the guides split on the marker but agreed on the need: Apple's
rule is precisely that sentence-style element names need marking where
title-style ones do not; Atlassian bolds element names in app copy;
Microsoft's in-UI guidance says to avoid bold and italic in the UI itself
and instead choose "wording that clearly sets off the name of the element",
its examples adding the element type ("the Create my database button"),
with quotation marks as the sparing last resort. Bold also costs markup in
every string and is unavailable inside a toast title that is already bold.

**Recommendation: amend rule 6.** A control name stays unquoted in its
on-screen casing, and when the label reads as prose (a verb phrase such as
Show hidden or Detect my accounts) the sentence adds the control's type:
`Turn on the Show hidden switch to manage them.`, `Press the Detect my
accounts button again to retry.` Noun-phrase labels (Rank thresholds, Top N
scores, Run notifications) stay bare. Quotes remain the last resort for an
ambiguity that survives rewording.

Consequence: four Copy entries change (the all-hidden status, the two
hidden-playlist hints, and the unchecked-accounts detection line).

Choosing differently: bold is the Atlassian answer and the one the redline
pass reached for; it needs the affected surfaces to become component trees
(status lines and alerts already are; help text and toast bodies are plain
strings today) and a rule for the surfaces that cannot render it.

## Problem

The inventory was taken against `39f96d4` (main, 2026-08-21) by reading every
user-facing string in `source/pages/`, `source/app_shell.py`, the service
messages that reach a toast or alert (`source/kovaaks/data_service.py`,
`source/kovaaks/api_service.py`, `source/utilities/store_schema.py`,
`source/kovaaks/percentile_warmup_service.py` and the fatal reasons it
relays, `source/my_watchdog/file_watchdog.py`), the chart annotations in
`source/plot/plot_service.py`, and the grid renderers in `assets/`. It
supersedes the 2026-08-11 design note that seeded it; that note's one
"carry-along fix" (the Home restart hint saying "the dashboard") has already
shipped in `b288b9f` and is not repeated here.

Re-verified against `16f9afd` (main, 2026-08-23) after the capability-spec
pass and PR #253 merged. The one copy-bearing change was #253 deleting the
playlist fill's two summary toasts (the 2026-08-22 in-place-only entry), so
their Copy-block entries are gone and the counts are restated for the
new base; the fill's status-line strings survive unchanged and stay in the
block.

Re-verified again against `1878659` (main, 2026-09-04) after the
celebration, alert-color, and toast-channel arcs merged. Three changes bear
on copy. The celebration arc (the 2026-09-02 celebrates-on-every-page
entry) added the personal-best toast and the Settings Celebrations section,
both already in the target style except one control-name quote D2 renames,
and retired the "While you were away" digest, so the digest's two
Copy-block entries give way to a note and D4 shrinks to two flourishes. PR
#265's setup card gained an unreadable-store state whose title and body use
contractions and "the dashboard" (the vocabulary the 2026-08-21 launcher
entry ruled out) plus a Skip-failure line with a nonstandard log pointer;
all three join the Copy block. The toast id-to-channel migration (the
2026-08-31 replace-in-place entry) changed no user-facing strings. The
counts below are restated for `1878659`.

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

1. **Em dashes.** 22 sites. 20 join clauses in prose; 2 are typographic
   (the `—` empty-value glyph under Last played, ratified 2026-06-30, and
   the scenario/score separator in run-toast bodies).
2. **Terminal punctuation.** Most sentences end with a period; the four
   above and a handful of grid tooltips do not. Nine messages join two
   sentences with a semicolon (an AST sweep of every non-docstring string
   constant under `source/` finds no others that reach the screen); one
   ends with an exclamation mark.
3. **Contractions, mixed.** "Couldn't refresh", "can't read your runs", and
   the unreadable-store card's "can't be read", "can't use it", and "what's
   wrong" beside "Could not save", "could not be checked", "cannot look
   one up". Counting every string constant under `source/` that reaches the
   screen, full forms outnumber contractions 26 to 5 (21 distinct messages
   to 5). The mix is the defect; D6 picks the side.
4. **Ellipses, three ways.** `Keep grinding...` and every placeholder use
   three periods; the fill status uses the `…` character; one tooltip uses
   `, ...` inside parentheses, and the stats folder description elides a
   path with `...\`.
5. **Casing.** See D2.
6. **Quoting control names.** `Toggle "Show hidden"` in three places, bare
   `press Detect my accounts again`, `then Save`, `Needs Rank Thresholds
   turned on` everywhere else.
7. **Vocabulary.** "the dashboard" in the setup card (both its
   stats-folder and unreadable-store bodies) against "this app" and
   "the app" on Settings and in every store message; "Stats directory" as a
   field label against "stats folder" in its own description and the setup
   card. (A fourth split, "served from cache" in the fill toasts against
  "from cache" in the status lines, resolved itself when #253 deleted the
  toasts.)
8. **Developer voice reaching the screen.** Import refusals and startup
   playlist warnings are built in `data_service.py` and shown verbatim:
   `Failed to load playlist data for playlist code: X`, `Invalid playlist
   data returned by API for playlist code: X`, `Skipping playlist file X:
   missing or blank playlist code; add a \`code\` field.` (backticks render
   literally). The Steam-ID mismatch toast and the warmup's unknown-username
   reason quote their values in single quotes; nothing else does.
9. **A stray capital.** The Position value reads `(52.47% Percentile)`
   mid-phrase.

Why now: the no-em-dash ruling explicitly deferred the shipped-copy sweep to
"a future review of all app messaging" rather than letting each PR fix what
it touched, and the last three feature PRs have each shipped copy in the new
style beside old copy in the old one. The longer the sweep waits, the more
the review tail of every PR spends on per-line style questions that one
ruling would settle. There is also a concrete deadline: the launch prep notes
plan an announcement post whose lead visual is a run toast beside the
Scenario Stats block, so the promoted release is the copy a cold reader
judges the app by (D5).

## Design

### The rules

These are the durable record. The decision-log entry carries them with the
rationale; AGENTS.md carries the operative form an implementer needs at write
time, replacing the current one-line em-dash convention.

1. **If it has a subject and a verb, it ends with a period. Status readouts
   do not.** `Settings saved.` and `No such folder.` are sentences.
   `Updating positions from KovaaK's… 12/40`, `Update interrupted · 8 of 40
   refreshed`, `3 of 40 positions unavailable`, and the Position hint (D1)
   are readouts and stay bare. A semicolon never joins two sentences; they
   are two sentences. A sentence that ends on an inline link puts
   its period in a **separate child after the anchor**, or it renders
   underlined as part of the link; `_username_unset_status()` in
   `source/pages/playlists.py` is the pattern.
2. **No em dashes.** Prose breaks into two sentences. A readout that chains
   fragments joins them with ` · ` (space, middle dot, space), which the grid
   status lines already use. One exception, named so a later sweep does not
   delete it: the `—` empty-value glyph under Last played when no scenario
   is selected (ratified 2026-06-30). The run-toast scenario/score separator
   becomes a colon.
3. **Casing** per D2.
4. **One ellipsis form.** The single `…` character, never three periods,
   and only where something is still going on: the in-progress fill
   readout. Placeholders are bare noun phrases (`Select a scenario`, `Filter
   playlists`), a path is never elided with one, and no line trails off for
   tone (D4). The app has no command that opens a further dialog, so the
   desktop convention of an ellipsis on such a command has no site.
5. **Contractions, consistently (D6).** The common ones: `can't`,
   `couldn't`, `doesn't`, `isn't`, `wasn't`, `aren't`, `you're`. A
   contraction and its full form never both appear in the app; `do not` is
   reserved for a warning the user must not skip, and no string uses it
   today.
6. **Control names are unquoted, carry their on-screen casing, and take
   their type when the label reads as prose (D8).** `then Save`, `Needs
   Rank thresholds turned on`, but `Turn on the Show hidden switch` and
   `press the Detect my accounts button again`, because a lowercased verb
   phrase has no other edge. Quotation marks are the last resort for an
   ambiguity that survives rewording. User-entered free text keeps double
   straight quotes: imported playlist names and KovaaK's usernames can
   contain anything, so `"{name}"` and `KovaaK's username "X"`. Tokens stay
   bare: Steam IDs, playlist codes, counts, and full paths. A literal file
   key keeps double quotes too (`a "code" field`, as the store messages
   already do).
7. **Vocabulary.** The software is *this app* or *the app*, never *the
   dashboard* (the 2026-08-21 launcher ruling: it reads as the browser page).
   The run source is the *stats folder*. A position that came from a local
   cache is *from cache*. *Position*, *Rank*, and *PB* keep the 2026-07-06
   meanings; KovaaK's itself says "rank" for a leaderboard position, and the
   app does not echo that, because *Rank* here is the benchmark tier. A
   playlist's identifier is its *playlist code*; the import help introduces
   KovaaK's own name for it, *share code*, once. Instructions say *turn on*
   and *turn off*, states say *on* and *off*, the control is a *switch*, and
   *toggle* is never a verb. An open-ended list uses *such as* with an
   example or two, never *etc.* The pointer to the log is always `See
   data/logs/debug.log.`
8. **A message that reaches the screen is user copy wherever it is built.**
   Service-layer strings that a page shows verbatim follow every rule above;
   the diagnostic detail stays in the log line beside them.
9. **Error copy says what happened first, then what to do when there is
   something to do.** A failure with no useful recovery step says only what
   happened and does not invent one (`Couldn't read the playlist file
   {file}.`, `The file {path} isn't valid JSON.`). A sentence never opens
   with a runtime value: a noun names the value before it appears, and a
   long path goes last in its sentence or in one of its own (D7). The toast
   title carries the verdict (unchanged from 2026-08-03).

Basis. Rules 1, 2, 4, and 8, the structure half of rule 9, the sentence-case
half of rule 3, and D1 to D3 match the Microsoft Writing Style Guide, the
Windows app writing guidance, Google's developer style and Material, Apple's
style guide, Atlassian, Polaris, and GitHub's Primer as read on 2026-09-04;
rule 5, the quoting and type-word halves of rule 6, the verb and list items
in rule 7, and rule 9's value clause were changed on that date to match
them. The research note records each guide's position with its URL, and the
decision-log entry carries the citations at ship time.

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
  in Settings.` → `No KovaaK's stats folder was found, so this app can't
  read your runs yet. Set it in Settings.` (rule 7; the contraction stays
  under D6)
- Setup card fine print *(ratified 2026-08-11)*: `Skipping username disables
  rank lookups. You can set it anytime in Settings.` → `Skipping keeps rank
  lookups off. You can add your username anytime in Settings.` "Skipping
  username" drops its article and reads clipped, and "set it" has nothing to
  refer to; "keeps rank lookups off" is the on/off state idiom rule 7 adopts
  and the phrase the username field's own description already uses (rule 7,
  one vocabulary).
- Setup card, unreadable-store body: `A settings file exists, but this
  version of the app can't use it, so the dashboard started without your
  settings. Open Settings to see what's wrong and how to fix it.` → `A
  settings file exists, but this version of the app can't use it, so the
  app started without your settings. Open Settings to see what's wrong and
  how to fix it.` ("the dashboard" is the vocabulary the 2026-08-21 launcher
  entry ruled out; this card shipped in #265 after the proposal opened, and
  its title, `Your settings can't be read`, is already correct under D6)
- Setup card, Skip write failed: `Nothing was written. Try again, or see
  data/logs/debug.log for details.` → `Nothing was written. Try again. See
  data/logs/debug.log.` (the rule-7 pointer form; "for details" adds
  nothing)
- Setup card, Skip refused, toast title: `Skip was not saved` → `Skip wasn't
  saved` (D6; its body, `The settings file was written by a newer version of
  this app. Update the app to change settings.`, is unchanged)

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
- Score threshold percentage help text: `…The overlay line tracks your
  current personal best; notifications judge the run against the personal
  best it was chasing.` → `…The overlay line tracks your current personal
  best. Notifications judge the run against the personal best it was
  chasing.`
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
  scenario.` (`the oldest date` paraphrases the `Oldest date to consider`
  label, the one place the block knowingly does so)
- Empty chart, date range: `Choose an older start date or play more runs.` →
  `Choose an older date or play more runs.`
- Chart annotations and legend names: `PB Score (123.00)` → `PB score
  (123.00)`; `Score Threshold (118.00)` → `Score threshold (118.00)`

**Scenario Performance: toasts**

- Refresh failed, body: `Couldn't refresh — position unchanged.` →
  `Couldn't refresh. The position shown is unchanged.`
- Refresh served stale, title: `Position refresh failed` → `Cached position
  shown`; body: `Couldn't refresh — showing the cached position.` →
  `Couldn't refresh. The position shown is from cache.` This gives the
  served-stale toast the title of its own that the 2026-08-03 entry and
  `tech_debt.md` left open; the color question there stays open, and the
  red hard-failure toast keeps its title.
- Run verdict, scenario/score separator in all three live bodies:
  `1w4ts Reload — 125.00` → `1w4ts Reload: 125.00` (the colon the
  2026-09-02 celebration toast already uses for the same pair)
- Run verdict, below threshold: `…, 92.1% of PB — need 95.0%. Still your
  3rd-best at 0.35 cm/360. Keep grinding...` → `…, 92.1% of PB (need 95.0%).
  Still your 3rd-best at 0.35 cm/360. Keep grinding.` (D4)
- The "While you were away" backlog digest, whose two bodies were
  redlined in an earlier draft, was retired wholesale by the celebration
  arc before this proposal shipped (the 2026-09-02 celebrates-on-every-page
  entry): a batch's other runs earn nothing and the plot is their record,
  so there is nothing left to reword.
- Run import failure, single: `Could not process a new run file. See
  debug.log for details.` → `Couldn't process a new run file. See
  data/logs/debug.log.`; batch: `3 new run files could not be processed. See
  debug.log for details.` → `3 new run files couldn't be processed. See
  data/logs/debug.log.`
- Steam ID mismatch body: `Configured Steam ID '7656…' does not match
  KovaaK's user 'X' (actual Steam ID: 7656…).` → `The saved Steam ID 7656…
  doesn't match KovaaK's user "X", whose Steam ID is 7656….` (the username
  is user-typed free text and keeps double quotes under rule 6; the two IDs
  are tokens and stay bare)
- Startup playlist warnings (built in `data_service.py`, shown under
  "Playlist not loaded"; D7 puts a noun in front of every value):
  - `Playlist directory is missing: {root}` → `The playlist folder {root} is
    missing.`
  - `Failed to read playlist file: {file}` → `Couldn't read the playlist
    file {file}.`
  - `Invalid JSON format in playlist file: {file}` → `The playlist file
    {file} isn't valid JSON.`
  - `Skipping playlist file {file}: missing or blank playlist code; add a
    \`code\` field.` → `The playlist file {file} has no playlist code. Add a
    "code" field to it.`
  - `Skipping playlist file {file}: playlist code {code} already loaded from
    {source}.` → `Skipped the playlist file {file}. Its playlist code {code}
    is already loaded from {source}.`
  - `Skipping playlist file: {store message}` → `{store message}` (the store
    message is a full sentence naming the file, and under D7 every one of
    them now opens with "The file"; see the store messages group). Two of
    the fragments composed after the file name change: the playlist-payload
    check's `has a missing or blank playlist code; add a \`code\` field.` →
    `has no playlist code. Add a "code" field to it.`, mirroring the
    bundled-root sibling above, and its neighbour `is not valid playlist
    data.` → `isn't valid playlist data.` (D6).

**Playlists overview**

- Status, all hidden: `All playlists are hidden. Toggle "Show hidden" to
  manage them.` → `All playlists are hidden. Turn on the Show hidden switch
  to manage them.` (D8)
- Store alert title: `Playlist visibility is not being used` → `Playlist
  visibility isn't being used` (D6)
- Warmup stopped, the reason relayed after `Percentile update stopped:`:
  `KovaaK's username 'X' was not found.` → `KovaaK's username "X" wasn't
  found.` (a mistyped username; double quotes under rule 6, D6), and the
  other fixed reason `KovaaK's username is not configured.` → `KovaaK's
  username isn't configured.` (D6). The combined line renders as a readout
  label followed by the reason sentence, which is accepted: the label says
  what stopped and the sentence says why.
- Warmup status, paused: `Updating percentile data: 8 remaining · paused;
  retrying at 3:05 PM` → `Updating percentile data: 8 remaining · paused
  until 3:05 PM`
- Lowest Percentile header tooltip: `…Shown once every played scenario has
  enough cached leaderboard data; hover a value to see which scenario.` →
  `…Shown once every played scenario has enough cached leaderboard data.
  Hover a value to see which scenario.`
- Type header tooltip: `Benchmarks carry rank thresholds (Bronze, Silver,
  ...) for their scenarios; playlists are plain scenario lists.` →
  `Benchmarks carry rank thresholds such as Bronze and Silver for their
  scenarios. Playlists are plain scenario lists.` ("such as" is the open-list
  form rule 7 adopts)
- Percentile placeholder tooltip: `Shown once all N played scenarios have
  data — open the playlist to fetch now` → `Shown once all N played scenarios
  have data. Open the playlist to fetch it now.`
- Modal titles: `Import Playlist` → `Import playlist`; `Delete Playlist` →
  `Delete playlist`; `Delete Leftover Files` → `Delete leftover files` (D2)
- Placeholders: `Filter playlists...` → `Filter playlists`; `KovaaK's
  playlist code...` → `KovaaK's playlist code` (the import help beside it
  already introduces KovaaK's own name, "share code", and keeps it)
- Import succeeded but hidden, title: `Playlist imported — not shown` →
  `Playlist imported but hidden`; appended hint: ` It could not be marked
  visible, so it may be missing from playlist selectors — toggle "Show hidden"
  on this page, then click its row's eye icon to show it.` → ` It couldn't
  be marked visible, so it may be missing from playlist selectors. Turn on
  the Show hidden switch on this page, then click the eye icon on its row to
  show it.` (D6, D8)
- Duplicate-and-hidden hint: ` It is currently hidden — toggle "Show hidden"
  on this page to unhide it.` → ` It is currently hidden. Turn on the Show
  hidden switch on this page to unhide it.` (D8)
- Import refusals (built in `data_service.py`, shown under "Playlist import
  failed"; the diagnostic detail stays in the log line each already writes):
  - `Failed to look up playlist code {code}: KovaaK's API error.` →
    `Couldn't look up {code} on KovaaK's. Check the code and try again.`
    (covers both causes: a slow spell and a code KovaaK's rejects outright)
  - `Failed to load playlist data for playlist code: {code}` → `Couldn't
    load a playlist for the code {code}. Check the code and try again.`
    Outcome-neutral on purpose: this branch is reached when KovaaK's search
    returns no usable record *and* the Evxl by-code fallback then fails,
    whether with a 400 for an unknown code or with a connection error or an
    invalid payload, so it cannot claim that no playlist matches.
  - `Found more than one playlist from code: {code}` → the same `Couldn't
    load a playlist for the code {code}. Check the code and try again.`, for
    the same reason: the ambiguous-search branch also returns its message
    only after the Evxl fallback fails, and a 400 there means no playlist
    has that exact code. The log lines beside the two branches keep the
    zero-versus-many diagnostic.
  - `Invalid playlist data returned by API for playlist code: {code}` and
    `Invalid playlist data returned by API: {name} ({code})` → `The
    playlist data for {code} is unusable.` (no source named: the second
    original fires on local filename sanitization, and the data may have
    come from Evxl)
  - `Playlist code already exists: {code} is already imported as {name}
    ({code}).` → `The playlist code {code} is already imported as
    "{name}".` (both codes in the original are the same canonical code, so
    one is enough; D7)
  - `Failed to save playlist data: {name} ({code})` → `Couldn't save the
    playlist file for "{name}" ({code}). See data/logs/debug.log.`
  - `Cannot save this playlist: {name} ({code}) would replace a playlist
    file written by a newer version of this app.` → `The playlist "{name}"
    ({code}) would replace a playlist file written by a newer version of
    this app. Update the app to import it.` (D7)
  - `Cannot save this playlist: {file} already holds {name} ({code}). Delete
    that playlist first, then import again.` → `The file for this playlist
    already holds "{name}" ({code}). Delete that playlist first, then import
    again.`
- Delete refusals (shown under "Playlist delete failed" / "Cleanup failed"):
  - `Playlist code cannot be deleted: {code} is not a user playlist.` →
    `The playlist code {code} isn't one you imported, so it can't be
    deleted.` (D6, D7)
  - `Failed to delete playlist file: {path}` → `Couldn't delete {path}. See
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
- The fill's two summary toasts ("Position update incomplete" and
  "Positions served from cache"), redlined in an earlier draft, were deleted
  wholesale by PR #253 under the 2026-08-22 in-place-only ruling before this
  proposal shipped; the status line above is now the fill's only report and
  there is nothing left to reword.
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
- Stats folder description, the path example: `The KovaaK's stats folder
  this app reads runs from, usually ...\FPSAimTrainer\FPSAimTrainer\stats.`
  → `The KovaaK's stats folder this app reads runs from, usually
  FPSAimTrainer\FPSAimTrainer\stats inside your Steam library.` (the rest
  of the description, in both its with- and without-suggestions forms, is
  unchanged)
- Store alert title: `Your saved settings are not being used` → `Your saved
  settings aren't being used` (D6)
- Steam ID error: `Enter a 17-digit SteamID64 — it starts with 7656119.` →
  `Enter a 17-digit SteamID64. It starts with 7656119.`
- Steam ID description: `Your 17-digit SteamID64. Optional; it disambiguates
  accounts that share a KovaaK's username.` → `Your 17-digit SteamID64.
  Optional. It tells apart accounts that share a KovaaK's username.` The
  semicolon split is rule 1; "tells apart" for "disambiguates" is a plain
  word for a jargon one and needs no rule.
- Save failed: `Could not save settings — nothing was written. See
  data/logs/debug.log.` → `Couldn't save settings, so nothing was written.
  See data/logs/debug.log.`
- Detection, no match: `No Steam account on this machine has a KovaaK's
  profile. Type your username in yourself — KovaaK's cannot look one up from
  a Steam ID.` → `No Steam account on this machine has a KovaaK's profile.
  Type your username in yourself. KovaaK's can't look one up from a Steam
  ID.`
- Detection, unchecked: `2 Steam accounts could not be checked; press Detect
  my accounts again to retry.` → `2 Steam accounts couldn't be checked.
  Press the Detect my accounts button again to retry.` (D6, D8)
- Detection, account list unreadable: `Steam's account list could not be
  read, so accounts on this machine may have been missed. See
  data/logs/debug.log.` → `Steam's account list couldn't be read, so
  accounts on this machine may have been missed. See data/logs/debug.log.`
  (D6)
- Picker description: `Choosing one fills the fields above; Save applies
  it.` → `Choosing one fills the fields above. Save applies it.`
- Celebration description, the control-name quote and one full form: `…and
  does not depend on Run Notifications.` → `…and doesn't depend on Run
  notifications.` (D2, D6; the rest of the description is unchanged)

**Aim Training Journey**

- Banner: `This page is still a work in progress!` → `This page is a work in
  progress.`
- Label `Checkpoint Hour` → `Checkpoint hour` (D2); empty chart: `Choose a
  Checkpoint Hour value to plot progress.` → `Set a checkpoint hour to plot
  progress.`

**Store messages** (built in `store_schema.py` for the settings,
visibility, and playlist stores; shown in the Settings and Playlists store
alerts and under "Playlist not loaded"; D7 puts "The file" before the path
and D6 contracts two of them)

- `{path} has no "schema_version" line. Add "schema_version": 1 to it, or
  delete the file to start over.` → `The file {path} has no "schema_version"
  line. Add "schema_version": 1 to it, or delete the file to start over.`
- `{path} has an invalid "schema_version" value ({value}). It must be the
  whole number 1.` → `The file {path} has an invalid "schema_version" value
  ({value}). It must be the whole number 1.`
- `{path} was written by a newer version of this app (schema_version {n}).
  The file is intact. Update the app to use it.` → `The file {path} was
  written by a newer version of this app (schema_version {n}). The file is
  intact. Update the app to use it.`
- `{path} is not valid JSON.` → `The file {path} isn't valid JSON.`
- `{path} must hold a JSON object.` → `The file {path} must hold a JSON
  object.`
- `{path} could not be read. See data/logs/debug.log.` → `The file {path}
  couldn't be read. See data/logs/debug.log.`
- The composed form for a validator's refusal, `{path} {fragment}` → `The
  file {path} {fragment}`. The settings and visibility fragments (`has an
  unknown setting "X".`, `must hold text values for every setting.`, `has an
  unknown key "X".`, `is missing "shown_playlists".`, `must hold
  "shown_playlists" as a list of text codes.`) are unchanged; the two
  playlist fragments are listed under the startup warnings above. The stamp
  script prints the same messages to its console and follows along, because
  it calls the same function.

**Unchanged on purpose**

- The `—` empty-value glyph under Last played (rule 2).
- The personal-best celebration surfaces (the two 2026-09-02 entries): the
  New personal best toast title and body, the Celebrations heading, the
  Personal best celebration label, its style names, and Preview are
  already in the target style — the toast's scenario/score colon is the
  separator rule 2 adopts — except the one control-name quote listed under
  Settings.
- Every toast title not listed: they are already sentence case and carry the
  verdict. The "… failed" titles stay: the guides split on the form
  (Atlassian endorses "Upload failed", the legacy Windows guide bans "failed
  to"), and the 2026-08-03 policy that the title carries the verdict is not
  reopened.
- The unreadable-store card's title, `Your settings can't be read`, and the
  Skip-refused toast body: correct as they stand under D6.
- The Settings version section, the bug-report link, the navbar, and the
  header tooltips.
- The launcher's and installer's console output, which the 2026-08-21
  launcher entry governs, and every `logging` line: neither is app copy.
  Log lines keep their full forms; D6's never-mix clause governs what the
  browser shows.

### Testing the rule, not just the strings

Most of these strings are module-level constants, but the riskiest ones (run
verdicts, backlog digests, fill statuses, the import refusals) are built
inline in f-strings, which a constant-list check would miss. The guard should
therefore walk the AST: for every module under `source/`, visit every
`ast.Constant` whose value is a `str` (f-string literal parts arrive as
constants inside `ast.JoinedStr`, so inline bodies are covered), skip
docstrings (the first statement of a module, class, or function body), and
fail on any `—` outside an explicit allowlist holding the one ratified glyph
site. Comments never reach the AST, so the check cannot misfire on them.

The guard covers the em dash only. Walking `source/` this way at `1878659`
finds 21 non-docstring string constants containing `—` (22 occurrences; the
Top N help text has two): the 20 Copy-block sites and the allowlisted glyph,
and no log line or other non-UI string, so
the gate passes the moment the Copy block ships and needs no UI-versus-log
distinction it cannot make. The three-period ellipsis is deliberately not
gated: the same walk finds it in the JavaScript spread operator inside a
clientside-callback source string (`...navbar` in `app_shell.py`) and in a
logging-only line in `file_watchdog.py`, neither of which is app copy, and
any future `...args` in callback JavaScript would trip it again. The walk
also does not see `assets/`: a `—` typed into a grid renderer there would
pass (today there are none in user-facing text). Ellipses, casing,
contractions, and the renderers are review territory, not a gate; D6's
never-mix clause is one `rg` for the full forms (`cannot`, `could not`,
`does not`, `is not`, `was not`, `are not`) over the strings that reach
the screen, and log lines are outside it.

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
- Network and privacy wording. Checked 2026-08-21 against the launch prep
  notes' enumeration of what the app talks to: every in-app string that makes
  a network claim (the username description, the setup card's fine print, the
  Detect hint, the Refresh tooltip, the import help) agrees with it, and none
  carries the enumeration itself. The "What it talks to" statement stays a
  README job, and its same-PR maintenance rule does not reach app copy.

## Testing

- The AST guard described in Design, as a new test module under `tests/`.
- Every existing test that pins a changed string is updated, never loosened
  to a substring match: the page modules `test_home_rank_format.py`,
  `test_home_run_events.py`, `test_home_setup_card.py`,
  `test_home_stats_dir_hint.py`,
  `test_playlist_pages.py`, `test_settings_page.py`, `test_ui_presentation.py`,
  and the service modules `test_data_service_extract.py`,
  `test_playlist_visibility_service.py`, and `test_settings_service.py`,
  which asserts the store layer's "is not valid JSON" through the log, plus
  whatever `rg` finds for each quoted string at implementation time.
- The standard local gates (`pytest`, `ruff format --check`, `ruff check`,
  `mypy`, `compileall`).
- One manual pass at the running app over every surface in the Copy block,
  including the D1 field with a real position value, to confirm nothing
  wraps or renders a period inside a link.

## Delivery plan

1. **This PR**: the proposal. Nothing ships until D1 to D5 are ruled and the
   Copy block has had its redline pass.
2. **One implementation PR**, after ratification, from a kickoff prompt that
   hands the implementer the ratified Copy block verbatim. One PR rather than
   one per surface because the rules are one ruling: splitting them would
   leave the app mid-style across a review window, which is the state this
   proposal exists to end. Suggested commit split: the copy and the rules
   (source and AGENTS.md), the tests and AST guard, then the docs. The docs
   commit carries the full shipping checklist: the decision-log entry with
   the rules and their rationale, "superseded in part, for copy" notes on the
   2026-08-03, 2026-08-09, 2026-08-11, 2026-08-21, 2026-08-22, and
   2026-09-02 entries whose quoted strings change (both 2026-08-11 entries,
   the setup card and the schema stamp whose store messages D7 reshapes; the
   celebration entry quotes the Run Notifications control name), the
   `tech_debt.md` edit for the refresh-toast title, a
   `product.md` line, the roadmap milestone moved to Shipped, and the
   deletion of this file. The current-behavior docs that quote changed
   strings are updated in the same commit, because a spec that names the
   old copy is wrong the moment the new copy ships. The capability-spec
   layer that landed 2026-08-22 quotes current strings throughout, so the
   sweep runs `rg` for every changed string across `docs/specs/` and updates
   each hit — today that is `scenario_rank.md` (the unset-username status
   line, the three Position hints under D1, and the refresh toast's title
   and body), `playlists.md` (the overview status lines, the import modal
   title and toasts, the Show hidden phrasing, the percentile tooltip, and
   the fill status lines, the visibility alert title, and the import and
   delete refusals), `settings.md` (the field label, the Steam ID error, the
   save-failed status, the detection copy, the store alert title, and the
   setup card's Skip-failure line), `scenario_performance.md` (the control
   names D2 renames, the toast bodies, and the setup card's unreadable-store
   body, stats-folder body, and fine print), and `notifications.md` (the
   control names D2 renames, the toast bodies, and the Skip-refused title) —
   plus `docs/product.md` (the unset-username status, the refresh toast, and
   the Run Notifications control name), `docs/architecture.md` and
   `docs/roadmap.md` (the control names D2 renames), and the README wherever
   the same `rg` finds a changed string. No new capability spec is created:
   app copy as a whole has no spec, and the strings that do live in one live
   in the spec of the capability they belong to. No hard dependency on other
   in-flight work. Under D5 it is sequenced before the release the
   announcement post promotes, and the shipping PR ticks the matching item
   off the launch prep notes' pre-post checklist.
