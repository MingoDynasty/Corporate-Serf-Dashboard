# Scenario Notes Proposal

Status: Proposed
Date: 2026-10-18

## TL;DR

Run History's top row kept a room between Scenario Stats and the PB card for
the player's own notes, and the room is still empty. This proposal fills it
with a scenario note: one plain-text reminder per scenario, on screen whenever
that scenario is selected, written and rewritten in place. A note is edited
with explicit Save and Cancel, and nothing the page does on its own while the
player types can throw the text away. Each note is saved as a small file of
its own, named from the scenario's exact name.

## Decisions needed

Eight rows, SN1 to SN8. **Nothing is ratified.** SN1 to SN6 are the
maintainer's agreement from the design discussion of 2026-10-18, held on four
full-size mockups built from their own stats. None was said in a ruling word,
so each stays open to review, and where a point only met no objection rather
than an explicit yes, its row says so. SN7 and SN8 are open: the maintainer
has no lean on either. Everything else is author-owned and is in
[Design](#design), including every string in [Copy](#copy); reviewers may
challenge any of it.

This proposal builds on the top row cards (Proposal 1, rows T1 to T4,
ratified on 2026-10-14 in #379), which are not reopened here. T1 kept the
room this proposal fills, and T4 set how a card orders its lines and that an
age reads relative with the exact time on hover. It runs in parallel with
Proposal 2, the latest-run card following the selection (#388). The two meet
in one place, the callback that selects a scenario
([Proposal 2](#proposal-2)).

### SN1. A note is one plain-text note per scenario, rewritten in place

Status: open. The maintainer, 2026-10-18: "Agreed: one note per scenario that
I rewrite, with the edited age shown behind a switch in the mockup." And:
"Agreed: the first version is plain-text scenario notes on Run History only".

The material consequence: there is no history. Once the editor closes, the
earlier text is gone, and no undo brings it back.

**Recommendation: each scenario has at most one note, plain text with its line
breaks kept and no formatting or links, which the player rewrites in place.
Any scenario the page can select takes one, including a scenario a playlist
lists that has never been played. A note belongs to the scenario's exact
name.**

- **A reminder about technique belongs to a scenario.** The Backlog idea this
  started from: "Option to save 'User Notes' on a scenario. (e.g. 'try to use
  more wrist/fingers here; on sweeping motions use arm', etc.)" It is read
  before the next run, so the latest text is the one that matters.
- **A day's observations belong to a session.** "Tired today" is about one
  evening, not the scenario. Session notes are a possible later feature with
  a store of their own ([Out of scope](#out-of-scope)).
- **The accepted cost was stated to the maintainer:** no undo once the editor
  closes. While it is open, Ctrl+Z undoes and **Cancel** puts the saved text
  back.
- **The exact name is the app's identity for a scenario.** Every version of a
  scenario shares its note, and a renamed scenario's note stays with the old
  name ([SN6](#sn6-storage-a-file-per-note)).

Rejected: a dated log of notes; keeping the previous text hidden in the file,
a just-in-case feature (a later store version could turn each note into the
first entry of a history, converted once by a script, if one is ever wanted);
formatting and links.

### SN2. The note is always on screen for the selected scenario

Status: open. The discussing session presented this as its lean. The
maintainer answered only the empty state (SN7) and raised no objection to
the rest; that is not an explicit yes.

The material consequence: the note is read with no click, during play and
during a lookup, and at narrow widths a long note is cut off.

**Recommendation: the note card sits in the room T1 kept and shows the
selected scenario's note. With no scenario selected the room shows nothing. A
long note fades out where the card runs short, and Edit shows the rest; there
is no Show more. The card takes the same box with a note, without one, and
with no scenario selected, so the chart never moves when Follow passes from a
scenario with a note to one without.**

- **The page has two uses** (premise P2 of the top row design): a glance
  between runs on a second 4K monitor with Follow on, and a lookup, "before I
  play Scenario B, I might manually swap to Scenario B, so I can look at its
  stats or notes." Both want the note in view.
- **A paragraph fits where it matters most.** The card is 761 × 141 px at
  2560 px, the maintainer's width, where a paragraph shows whole, and 800 px
  (capped) at 3840 px. At 1920 px it is 261 px wide and a paragraph is cut off.
- **No Show more:** growing the card would move the chart, and an overlay
  would cover the PB card. The editor already shows the whole note.

Rejected: a note behind a click (a popover or a disclosure), which loses the
glance during play; a Show more control.

### SN3. The editor, Follow, and changes the player makes

Status: open. The maintainer's agreement on the buttons, 2026-10-18: "I am
still leaning toward explicit Save/Cancel buttons. From the older
`scenario-stats-layout-v9.html` mockup, it showed small buttons that didn't
take up much screen space. Having explicit buttons also means it trivial for
the user to copy and paste the notes without editing." On protecting the text
from Follow: "there is always the possibility of a delay between the run
finishing, CSV file getting created, and CSV file getting ingested into the
app ... So I think we should still build protections around the edge case".
On the dialog: "Agreed: a change I make myself with unsaved changes opens the
dialog (Keep editing, Discard, Save), and runs keep waiting in the card."
Their reason for rejecting a locked dropdown: "it feels a little restrictive
to the user." Rules 1, 3 and 4 are those agreements, and rule 2 is the
meaning of "unsaved changes" they were agreed with. When they asked what
happens if several runs on different scenarios land, the newest-run answer in
rule 3 met no objection, and so did rules 5 to 8 when the discussing session
presented them; that is not an explicit yes. Two points are this author's:
turning Follow off ends a wait (rule 3), and rule 9.
Writing this proposal also found that two routes in rule 4 need more than the
discussion assumed. The run toast's link draws the page again before the
selection callback runs, and on 2026-10-18 the maintainer chose to have the
browser stop it and select the scenario in place. A Playlist filter change can
clear the selected scenario, a route the discussion did not list; including
it is this author's call.

The material consequence: while a note has unsaved changes, Follow does not
move the page, and every change of scenario the player makes asks first.

**Recommendation, as rules:**

1. **Edit opens a text box with Save and Cancel.** Reading never opens the
   editor, so a note can be selected and copied.
2. **The editor has unsaved changes while its text differs from the text it
   opened with.** Typing a word and deleting it again leaves none.
3. **Follow waits while the note has unsaved changes.** The run's toast still
   shows. While a run waits, the card names the scenario the page will switch
   to, since the toast is gone after 8 s. **Save** or **Cancel** then switches
   once, to the newest waiting run's scenario. A run on the edited scenario
   ends the wait, and so does turning Follow off.
4. **A change of scenario the player makes, with unsaved changes, opens a
   dialog:** **Keep editing**, **Discard**, **Save**. It covers a pick in the
   Selected scenario dropdown, the run toast's link, a name in the run list's
   All scenarios view, the latest-run card's scenario button while it exists,
   and a Playlist filter change that leaves the edited scenario off the list.
   Keep editing puts the old selection back. Escape or a click outside the
   dialog means Keep editing.
5. **An editor with no unsaved changes just closes** when the scenario
   changes, by Follow or by hand, and the card shows the new scenario's note.
6. **A save goes to the scenario the editor opened on.**
7. **Escape does nothing in the editor.** It closes popups everywhere else in
   the app, and here a reflexive press could throw away a paragraph.
8. **Unsaved text is lost if the player leaves the page:** the navbar, a
   reload, the browser's back button, closing the tab.
9. **A failed save keeps the editor open,** with an error under it, and its
   unsaved changes keep every protection above. This replaces the discussion's
   "a scenario change then loses that text": with Follow waiting and every
   route asking, nothing changes the scenario under a failed save.

- **The rule behind 3 and 4:** what the player does gets a question now; what
  happens to them waits in the card. The dialog opens only right after the
  player's own click, never during play. Its reason, the maintainer's: it
  "really encourages the user to settle the issue as soon as possible, so the
  system can get back into a clean state."
- **Several runs while a note is open end where Follow would have left the
  page:** on the newest run's scenario, with one switch. That is how Follow
  already treats a batch of runs.

Rejected: saving as you type; closing the editor when it loses focus; Escape
undoing the edit; asking in the card instead of a dialog; locking the
dropdown; pausing Follow whenever an editor is open; keeping the editor on the
old scenario while the page shows the new one. Each reason is in
[Alternatives rejected](#alternatives-rejected).

### SN4. The first-run gap is accepted

Status: open. The maintainer, 2026-10-18: "Agreed: the Notes proposal accepts
the one-run gap and states the numbers, and following scenario starts from
KovaaK's log goes to the Backlog as its own idea."

The material consequence: with Follow on, the page reaches a scenario only
when its first run's file lands, so the note shows from that scenario's
second run.

**Recommendation: accept the gap. Selecting a scenario before playing it
shows its note for the first run too. Following a scenario as it starts, which
would help every card, is Backlog item 8.**

The maintainer's play, from their stats folder on 2026-10-18. A visit is
consecutive runs on one scenario. One player's data.

| Period | Runs | Scenarios | Top 20 share | Median runs per visit | First runs of a visit |
|---|---|---|---|---|---|
| Last 30 days | 943 | 37 | 85% | 6 | 18% |
| Last 90 days | 1,232 | 76 | 76% | 5 | 21% |
| Last year | 4,825 | 503 | 42% | 2 | 24% |

Over the last year, 54% of visits were one or two runs: exploring, where the
gap costs most. Over the last 30 days, mostly grinding, it cost about one run
in six.

### SN5. The first version is scenario notes on Run History only

Status: open. The maintainer, 2026-10-18: "Agreed: the first version is
plain-text scenario notes on Run History only, and the playlist-table column
waits for a later proposal."

The material consequence: a note is read and written only on Run History.

**Recommendation: plain-text scenario notes, shown and edited only in Run
History's top row.** Each item left out is listed in
[Out of scope](#out-of-scope) with where it is tracked.

### SN6. Storage: a file per note

Status: open. The maintainer, 2026-10-18: "Agreed: each scenario note gets its
own file, named from the scenario with a code from its exact name, holding the
exact name and the text."

The material consequence: this fixes a saved format, the first data in the
app that a player writes and nothing can rebuild. Changing it later means a
new schema version and a conversion script.

**Recommendation:**

- **Path:** `data/scenario_notes/<prefix>-<code>.json`. The prefix is the
  exact name with every character other than a letter, a digit, `-` or `_`
  turned to `_`. The code is the first 8 hex digits of the sha256 of the exact
  name in UTF-8. This is how `_safe_cache_key` in
  `source/kovaaks/api_service.py` names a cache file.
- **Content:**
  `{"schema_version": 1, "scenario": "<exact name>", "text": "<the note>"}`,
  plus `"edited_at"` if SN8 ships.
- **Read when its scenario is selected.** The path comes from the name, so no
  folder scan finds a note, and nothing is held in memory.
- **Save writes one file;** saving empty text deletes it.
- **Each file is a stamped store of its own,** read and written through the
  app's existing schema machinery, and a broken file shows its error on that
  scenario's card.

How the agreement was reached, all on 2026-10-18:

- **The maintainer asked whether storage needed discussing,** naming SQLite,
  a folder of files, the name as the file name, and JSON with name and
  content fields. The discussing session recommended one file for every note.
- **They pushed back on one file:** "if a power user writes huge notes for
  every scenario ... writing a big file repeatedly". The measurements below
  showed one file would hold. They stayed unsure.
- **The discussing session then moved to a file per note.** It had ruled out
  files named from the scenario because Windows ignores case in file names
  and two real scenarios differ only by case. The cache's naming, a readable
  prefix plus a code from the exact name, removes that: it was added after
  sanitized names alone collided and overwrote each other.
- **They asked whether a stats file's `Hash:` could tell scenarios apart.** It
  can't: it names a version of a scenario's contents, not the scenario.

| Scenarios with notes | Characters per note | One file | Save | Read |
|---|---|---|---|---|
| 866 | 500 | 0.5 MB | 5 to 9 ms | 2 ms |
| 3,000 | 2,000 | 6.2 MB | 21 to 23 ms | 12 ms |
| 10,000 | 5,000 | 51 MB | 145 to 154 ms | 100 ms |

Measured for the single file with the app's own `atomic_write_text`, median
of 7, on two drives of the maintainer's machine. A file per note saves one
small file whatever the count.

Rejected, each with its reason in
[Alternatives rejected](#alternatives-rejected): a single notes file; SQLite;
file names from the scenario's name alone; the stats file's hash as the key;
the file's modified time as the edit time.

### SN7. The empty state

Status: open. The maintainer has no lean, 2026-10-18: "I don't feel strongly
whether it's an empty card vs purely the link. I feel like it's simply a
UI/UX preference. Let's leave it up for debate during proposal review."

The material consequence: what a scenario with no note shows, which is most
lookups and every new scenario, though rarely during play once the regulars
have notes.

The two options, each in the same box, so the chart doesn't move either way:

- **An empty card:** the frame, the first line `Scenario note`, `No note yet`
  under it, and **Add a note**. It shows a new player where notes live and
  what they are called, and every card in the row keeps a frame.
- **Only a link:** **Add a scenario note** in the room, with no frame. The
  frame then means "this scenario has a note", which a glance across the row
  picks up, and lookups stay quieter.

**Recommendation: only the link.** The link sits where the card would and
names what it adds, so a new player finds notes either way. The empty card
spends a frame, a heading and a line to say there is nothing, and it costs
the at-a-glance signal.

### SN8. The edited-age line

Status: open, not yet judged. The mockup shows it behind a switch.

The material consequence: whether the store keeps an edit time. If it ships
later instead, every note written before then has no time to show, and adding
the field needs a new schema version for this store.

**Recommendation: ship it, and store the edit time from the first version.**
The first line reads `Scenario note · edited 3 weeks ago`, drawn as the PB
card's `PB · set 5 days ago`: relative, reworded every 30 seconds, with the
exact time on hover and focus (T4).

- **A reminder can go stale.** A note written before a change of sensitivity
  or grip may no longer hold, and "edited 4 months ago" says so.
- **The time can't be recovered later.** A note saved before the field exists
  has no edit time, and its file's modified time is not one (below).
- **Adding a key later is a version change.** Within a version a store's key
  set is fixed, as the settings store's v1 sets it, and the schema machinery
  today carries one version number for every store.

**How the time is stored,** agreed with the maintainer for the case where the
line ships ("Sounds good", 2026-10-18): in the file as `edited_at`, in UTC,
written only when **Save** changes the text, and shown in local time. Not the
file's modified time: a future conversion script rewriting every file, a git
checkout, or a backup or sync tool changes it without an edit, and every
note would read "edited just now". A hand edit outside the app leaves
`edited_at` as it was (accepted).

## Problem

### What the room holds today

T1 placed the row's pieces: the dropdowns' column, Scenario Stats, then
"empty room with no element reserving it", and the PB card at the right end
([2026-10-14 entry](../decision_log/2026/2026-10-14-run-historys-top-row-has-one-card-per-kind-of-information.md)).
The spec states it as "the room kept for notes, which holds nothing"
([run_history.md](../specs/run_history.md#the-top-row)). The roadmap names
notes as a separate proposal for that room, and the work item's build order
puts this proposal after Proposal 1, which has shipped.

### What the player needs

- **A reminder before the next run,** "a line or two, but potentially up to a
  paragraph" (premise P7 of the top row design).
- **The page at a glance on a second monitor during play,** with Follow on,
  at 2560 CSS px: 4K at 150%, the maintainer's own width. The resolution
  priority, ruled 2026-10-14: 2560 first, 3840 second, 1920 only where it
  costs the other two nothing.
- **Typing is not safe from Follow.** The discussing session first claimed a
  run can't land while the player types, since playing needs KovaaK's focus.
  The maintainer corrected it: a run's file is read and the page moves a
  second or two after the run ends, and an editor can be left open across a
  run.

### Verified facts

Checked at `4f05766` on 2026-10-18. The design discussion read the code at
`4199f7f`; the two merges since (#387, #389) changed none of it.

- **One callback writes both dropdowns' values.**
  `reach_the_scenario_asked_for` in `source/components/scenario_selection.py`,
  registered by `register_scenario_selection_clearing_filter`, takes Follow's
  run summary, the page's deep-link store, the latest-run card's scenario
  button and a name pressed in the All scenarios view. A pick in the dropdown
  is not among its inputs: it changes the dropdown's value in the browser
  first.
- **The run toast's link draws the page again.** It is a `dcc.Link` to
  `/run-history?scenario={scenario}&run={run id}`, and Dash Pages rebuilds the
  page on a change of address. The deep-link store "only changes when the
  page is drawn again" (`reach_scenario`'s docstring;
  [2026-09-19 entry](../decision_log/2026/2026-09-19-a-query-parameter-selects-a-control-it-does-not-suspend-its-memory.md)).
  So by the time the selection callback sees a toast's link, an open editor
  and its text are already gone. Blocking that callback can't protect them;
  the click has to be stopped in the browser.
- **A Playlist filter change can clear the selected scenario.** The
  filter's callback writes the scenario dropdown's list, and the dmc 2.8.0
  Select drops a value its new options lack. The spec states it for the
  filter's own value. That it clears the selected scenario the same way is an
  inference from the same component, not observed for this proposal.
- **A value a callback writes is remembered like a pick.** The 2026-09-19
  entry: "Callback-written values *are* persisted — the response path reaches
  `recordUiEdit`". So when Keep editing writes the old scenario back, the
  browser should remember the old one, and a reload should open on it. The
  design discussion assumed the opposite; the build checks it with a reload.
- **Follow already lands on the newest run.** `forward_run_events` in
  `source/pages/run_history.py` summarizes a batch for the most recently
  played scenario, and the selection moves at most once per batch. The run
  toast is one per batch, for its newest live run, and lasts 8 s
  ([notifications.md](../specs/notifications.md#run-notifications)).
- **The lag:** the watchdog sleeps 1 s before reading a new stats file
  (`_import_created_file` in `source/my_watchdog/file_watchdog.py`), and the
  page receives new runs every `polling_interval` (default 1000 ms).
- **The store pattern exists.** `source/utilities/store_schema.py` has the
  four read states (`read_store_document`, `StoreState`), the refusal for a
  newer file (`UnsupportedSchemaError`), the copy aside before a user save
  replaces a broken file (`back_up_unusable_store`) and the stamp
  (`stamped_payload`). `save_settings` with `_guard_settings_destination` in
  `source/config/settings_service.py` is a user save that owns a broken file.
  Writes go through `atomic_write_text` in `source/utilities/atomic_write.py`.
- **The schema module carries one version for every store:**
  `CURRENT_SCHEMA_VERSION = 1` and `SUPPORTED_SCHEMA_VERSIONS = {1}`.
- **`data/` is git-ignored as a whole,** so notes never reach git. Nothing
  here uses the network.
- **The hash names a version, not a scenario.** `scenario_hash` in
  `source/kovaaks/data_models.py` is the stats file's `Hash:`.

### Evidence: names and versions

From the maintainer's stats folder on 2026-10-18. One player's data.

- **Every stats file's name matches its `Scenario:` field,** over 866
  scenarios played.
- **Two names differ only by case:** `psalmTS angelic click 30% Larger` and
  `psalmTS angelic click 30% larger`. On Windows, file names from the name
  alone would put both notes in one file.
- **One name ends in a space,** `Pasu Voltaic Silver `, so a key is never
  trimmed. The longest name is 48 characters; none is outside ASCII.
- **Their files under SN6:** `SmoothBot_Perfected-98173bc5.json`,
  `psalmTS_angelic_click_30__Larger-e7ca36d5.json`,
  `psalmTS_angelic_click_30__larger-0f416bac.json`,
  `Pasu_Voltaic_Silver_-04dda976.json`. Recomputed for this proposal.
- **The hash:** 866 names carry 882 hashes, and 16 scenarios have 2 or 3. A
  note keyed by hash would be lost at every update of its scenario. The
  case-only pair shares one hash: the lowercase name has 9 runs from
  2025-08-13 to 2026-04-19, the capitalized one 2 runs on 2026-04-24, which
  looks like a renamed capitalization (an inference).

### Evidence: room for the note

Measured on 2026-10-18 in mockup v4, a captured copy of the served page with
the note card drawn in. The card's size comes from the discussion's checks in
headless Edge and Firefox; the editor's columns and the waiting line were
measured again for this proposal, in headless Edge.

| Window | Note card | A paragraph | Text box, editing, keeping the row | Row, editing, growing the row |
|---|---|---|---|---|
| 2560 | 761 × 141 px | whole | 69 px | 186 px (+45) |
| 3840 | 800 px, capped | whole | 69 px | 186 px (+45) |
| 1920 | 261 × 141 px | cut off | 69 px | 186 px (+45) |
| 1536 | 451 × 132 px, row wrapped to 285 px | cut off | 60 px | 339 px (+54) |

With a run waiting, the waiting line (see [Copy](#copy)) takes one line beside
the buttons at 2560 and 3840 px, even for a 48-character name, and the text
box keeps 69 px. At 1920 px it takes three lines under them and the text box
shrinks to 14 px; at 1536 px it takes two or three and the box keeps 32 to
50 px. Growing the row instead keeps a 114 px box everywhere, and a waiting
run then makes the row 246 px at 1920 px (+105).

### Not checked

- **The room with no scenario selected.** The mockup's capture has no such
  state.
- **The narrow layout,** a page area of 900 px or less, where the row is one
  wrapping line.
- **The dialog as a real Mantine modal,** its focus, and what NVDA says of it.
  The mockup draws a stand-in.
- **Persistence after Keep editing,** expected to hold from the 2026-09-19
  entry.
- **The Playlist filter route,** inferred, not observed.
- **Ctrl+Z in the app's text box.** Native undo is expected.
- **How the page behind the dialog looks after a pick** (see
  [The dialog](#the-dialog)).

## Design

### The top row as a player meets it

At 2560 px, with a benchmark selected and Follow on. The note card is the
third box; the latest-run card, at the right, sits over the run list.

```text
+ Playlist filter -----+ +- Scenario Stats ---+ +- Scenario note · edited 3 weeks ago -------- Edit -+ +- PB · set 1 day ago --+ +- Latest run · 1 day ago -+
| [Jay9's Benchmark  v]| | Category: Tracking | | try to use more wrist/fingers here; on sweeping     | | 5,079.14  (Sapphire)  | | 11,598  (New PB)         |
| Selected scenario    | | Last played: 1 day | | motions use arm                                     | | Top rank              | | Up 0.5% on your previous |
| [SmoothBot Perfect v]| | Number of runs: 23 | |                                                     | | 81.13% percentile     | | Run 4 last session       |
| (o) Follow newly ... | |                    | |                                                     | | 40 cm/360 · Acc 64.89%| |                          |
+----------------------+ +--------------------+ +-----------------------------------------------------+ +-----------------------+ +--------------------------+
```

The note card alone, in each state:

```text
1. A note: read with no click, centered in the card's height.
+- Scenario note · edited 3 weeks ago ----------------------------- Edit -+
| try to use more wrist/fingers here; on sweeping motions use arm         |
+-------------------------------------------------------------------------+

2. A long note (here at 1920 px): it runs to the card's bottom and fades out.
+- Scenario note · edited 3 weeks ago - Edit -+
| try to use more wrist/fingers here; on      |
| sweeping motions use arm. Keep the          |
| crosshair on the head, not the body: it     |
| strafes in short bursts, so reacting late   |
| loses it. Relax the grip before each run,   |
| ░░ since a tense hand ░░░░░░░░░░░░░░░░░░░░░ |  (fading)
+---------------------------------------------+

3a. No note, recommended (SN7): a link in the same box, no frame.
  Add a scenario note

3b. No note, the alternative: an empty card.
+- Scenario note ---------------------------------------------- Add a note -+
| No note yet                                                              |
+--------------------------------------------------------------------------+

4. No scenario selected: the same box, empty, no frame.

5. Editing: the text box fills the card and scrolls inside it.
+- Scenario note ---------------------------------------------------------+
| +---------------------------------------------------------------------+ |
| | try to use more wrist/fingers here; on sweeping motions use arm|    | |
| +---------------------------------------------------------------------+ |
| [Save] [Cancel]                                                         |
+-------------------------------------------------------------------------+

6. A run waiting (unsaved changes, Follow on, a run landed on another scenario).
+- Scenario note ---------------------------------------------------------+
| +---------------------------------------------------------------------+ |
| | try to use more wrist/fingers here; on sweeping motions use arm a|  | |
| +---------------------------------------------------------------------+ |
| [Save] [Cancel]  A run on Air Voltaic Invincible 4 Medium is waiting.  |
|                  Press Save or Cancel to show it.                      |
+-------------------------------------------------------------------------+

7. The dialog, after a pick in the dropdown with unsaved changes.
        +- Your scenario note isn't saved ------------------------+
        | Save your changes to the note on SmoothBot Perfected    |
        | before you switch to Smoothsphere Viscose?              |
        |                     [Keep editing] [Discard] [Save]     |
        +---------------------------------------------------------+

8. A broken note file: the error in place of the text.
+- Scenario note ------------------------------------------------- Edit -+
| The scenario note file isn't valid JSON. File: C:\...\data\scenario_   |
| notes\SmoothBot_Perfected-98173bc5.json                                 |
+-------------------------------------------------------------------------+
```

The mockup is `ignore/mockups/scenario-notes/scenario-notes-v4.html` in the
maintainer's checkout. It is not in the repository.

### The note card

- **Place:** between the Scenario Stats card and the PB card, the room T1
  kept. The PB card keeps its place at the row's right end.
- **Width:** it takes the room the row leaves, never less than 240 px and
  never more than 800 px, so a line stays readable at 3840 px. At 3840 px the
  gap left over sits between the note card and the PB card. Where the first
  column wraps, it wraps as T1 set: the PB card first, then Scenario Stats.
- **Height:** as tall as the row, as every card is. Its box never depends on
  the note, so the chart doesn't move.
- **First line:** `Scenario note`, quiet, as the other cards' first lines are,
  with `· edited {age}` if SN8 ships, and **Edit** at the line's right end,
  drawn as the app draws a link.
- **Text:** 14 px, line breaks kept, wrapped anywhere a word is too long for
  the card, centered in the card's height when short. A note taller than the
  card is cut at the card's bottom with a fade over its last line.
- **Not a control:** the text is selectable, and only **Edit** opens the
  editor.

### The editor

- **Edit** turns the card into a text box over **Save** and **Cancel**, with
  the cursor at the end of the text. The first line reads `Scenario note`
  alone while editing.
- **The editor keeps the row's height.** The discussion left this open. The
  text box fills what the card leaves and scrolls inside itself. Re-measured
  for this proposal: with no run waiting, the box is 69 px, about three lines,
  at 1920, 2560 and 3840 px, and the chart never moves. Growing the row
  instead would give a 114 px box, at the cost of moving the chart 45 px at
  2560 px every time the player edits. The cost of keeping the row lands at
  1920 px, and only while a run waits: the waiting line takes three lines
  under the buttons and the box shrinks to about 14 px until the player
  presses **Save** or **Cancel**. That matches the resolution ruling, 2560 and
  3840 first, and the state lasts until the player's next click. The text
  stays whole inside the box.
- **A note holds at most 2,000 characters,** the number the discussion
  suggested. The card shows about 500 at 2560 px, and no cap can make a note fit
  at 1920 px, so the cap bounds rather than fits: a long paragraph and a short
  list fit under it, and a file stays near 2 KB. The text box stops typing at
  2,000 and cuts a paste there. From 1,800 characters a count shows under the
  box: `1,850 of 2,000 characters`. The browser counts UTF-16 units, so any
  text it lets through is within the store's 2,000-character limit, which
  counts characters.
- **Save** writes the text to the scenario the editor opened on, closes the
  editor, and shows the saved text. Saving empty text, or only whitespace,
  deletes the note. Saving text that equals what the editor opened with
  writes nothing and leaves `edited_at` alone, when the editor opened on a
  note the app could read. Opened on a broken file, the editor starts empty
  and **Save** always writes: text replaces the file, and empty text deletes
  it, each after the broken file is copied aside. So **Edit** then **Save**
  clears a broken note's error with no hand edit.
- **Cancel** closes the editor and shows the saved text.
- **A failed save** keeps the editor open with its text, and the error under
  the buttons. The text keeps its unsaved changes and every protection.
- **Escape does nothing** in the editor (SN3, rule 7). Tab leaves the text box
  for **Save**, as in any form.

### Follow's wait

- **It holds only with unsaved changes.** An editor whose text matches what it
  opened with closes when Follow moves the page, as on any change of
  scenario.
- **A run on another scenario, with unsaved changes:** the page stays on the
  edited scenario. The run's toast shows as it always does. The card's
  waiting line names the run's scenario.
- **More runs:** the newest run's scenario replaces the one named. A run on
  the edited scenario ends the wait, and the line goes.
- **Turning Follow off** ends the wait and the line goes. Turning it on again
  brings back no earlier run, as a flip of the switch forwards nothing today.
- **Save or Cancel** then moves the page once, to the scenario named, with the
  filter clearing that Follow already does for a scenario the filter doesn't
  list.
- **The rest of the page while a run waits:** the chart, Scenario Stats and
  the PB card stay on the edited scenario, since the dropdown hasn't moved.
  The run list adds the run. Today's latest-run card moves to the newest run
  on any scenario; under Proposal 2's R1 it would stay on the edited one.

### The dialog

It opens when the player changes the scenario while the note has unsaved
changes. Its title is `Your scenario note isn't saved`, and its body names the
note's scenario and where the player asked to go.

- **Keep editing** closes the dialog and leaves the editor and the selection
  as they were. Escape and a click outside the dialog do the same. Keyboard
  focus starts on Keep editing, so Enter can't throw text away.
- **Discard** drops the unsaved text, closes the editor, and goes where the
  player asked.
- **Save** saves the text to the note's scenario, then goes where the player
  asked. If the save fails, it acts as Keep editing, with the error under the
  editor.
- **A run waiting is dropped** by Discard and Save: the player chose where to
  go. Keep editing keeps it waiting.
- **No close button:** the three answers are the ways out.

Every way the player changes the scenario on this page:

| Route | How the dialog catches it | What Keep editing puts back |
|---|---|---|
| A pick in the Selected scenario dropdown | The pick has already changed the dropdown. A callback sees the new value differ from the edited scenario and opens the dialog. | The old scenario, written back by the selection callback. |
| A Playlist filter change whose list lacks the edited scenario | The Select has already dropped the scenario. The same callback opens the dialog. | The old filter and the old scenario. |
| The run toast's link | A script on the page stops the click before the page is drawn again, and opens the dialog. Save or Discard then selects the scenario in place, clearing a filter that doesn't list it, as the link would; the address stays as it was. | Nothing has moved. |
| A name in the run list's All scenarios view | The selection callback holds the change and opens the dialog. | Nothing has moved. |
| The latest-run card's scenario button, while it exists | As a name in the All scenarios view. | Nothing has moved. |

- **Behind the dialog after a pick or a filter change,** the chart and the
  other cards have already redrawn for the pick, since the dropdown is their
  input. Keep editing redraws them for the old scenario. The note card does
  not redraw while the dialog is open. Catching a pick before the dropdown takes it would
  need a hook into Mantine's list that the app doesn't have.
- **With no unsaved changes,** every route behaves as today, and the toast's
  link draws the page again as it does now.
- **Leaving the page** is not caught (SN3, rule 8). A browser's "Leave site?"
  prompt can't see moves between the app's own pages, so it would catch a
  reload and a tab close but not the navbar.

### What redraws the note card

A testable statement for the build: **the note card is redrawn only by a
change of the page's scenario that the rules let through, by Edit, Save and
Cancel, and by the dialog's answers.** A run landing on any scenario, the
30-second tick, the date moving on, the Playlist filter, the Score threshold
and a dropdown value held behind the dialog never redraw it. If SN8 ships,
the tick rewrites only the age, which shows only while reading.

### Storage

- **The file name** is formed as SN6 states, from the exact name. The prefix
  keeps every letter and digit, as Python's `str.isalnum` counts them, so it
  holds no path separator, and the code keeps names that differ only by case
  or punctuation apart. Where the shared helper lives is the build's call; the
  cache's `_safe_cache_key` is private to `api_service.py` today.
- **Version 1 of the file:** a JSON object with exactly `schema_version`,
  `scenario` and `text`, plus `edited_at` if SN8 ships. `scenario` must equal
  the name the page asked for. `text` is a string with at least one character
  that isn't whitespace, and at most 2,000 characters.
  `edited_at` is an ISO 8601 time in UTC, such as `2026-10-18T20:25:00Z`. Any
  other key, or a value that breaks these rules, puts the file in the error
  state. "Whitespace" here is what Python's `str.isspace` counts.
- **Reading:** the four states of the schema machinery, per file. Missing
  means no note. Error shows its message on the card in place of the text,
  and **Edit** opens an empty editor whose **Save** always writes (see
  [The editor](#the-editor)). Future shows its message and offers no
  **Edit**, since every write to the file is refused. Supported shows the
  note.
- **Writing:** **Save** first reads the file on disk, not what the card
  showed, as `_guard_settings_destination` does. A file from a newer build
  refuses the save. A broken file is copied to
  `<name>.corrupt-<n>.bak` beside it first, and the save replaces it. The
  text is written with `atomic_write_text`; empty text deletes the file after
  the same check. The folder is made on the first save.
- **Where a broken file's error shows,** which the discussion left open: on
  that scenario's card only, and in the log as every store error is. Not in
  the startup warning queue, since notes are never read at startup, and not
  on Settings: a note file is read only when its scenario is selected, and its
  card is the one place the player meets it.
- **Two tabs:** the last save wins, under the one-active-tab model.
- **A path longer than Windows allows** fails to save, with the save's error.
  The longest of 866 real names is 48 characters, and nothing truncates the
  name, which keeps the file name from depending on a length rule.

### Proposal 2

Proposal 2 (#388) is in review in parallel, and both can be implemented in
parallel. They meet in two places:

- **The selection callback.** This proposal adds inputs to it: the dialog's
  answers and the editor's unsaved state. Proposal 2's R1 removes one, the
  latest-run card's **Show {scenario}** button, which this proposal names as a
  route "while it exists". Whichever implementation merges second rebases
  onto the first and re-checks the whole selection flow.
- **The Run History spec and the roadmap.** Both edit the top row and the
  selection statements, and both edit the roadmap's Upcoming entry.

While Follow waits on a note, today's latest-run card moves to the newest run
on any scenario. Under R1 it would stay on the edited scenario, which agrees
with the rest of the row.

### Narrow windows, keyboard and screen readers

- **At a page area of 900 px or less** the row is one wrapping line. The note
  card goes after Scenario Stats and before the PB card, at least 240 px wide.
  Not measured.
- **Keyboard:** **Edit** is a button and takes focus. Pressing it puts focus
  in the text box, and Tab then reaches **Save** and **Cancel**. After Save or
  Cancel, focus returns to **Edit**, or to **Add a scenario note** when the
  note is gone. The dialog traps focus while open.
- **Screen readers:** the card's first line is text, as the other cards'
  are. The text box's accessible name is `Scenario note`, and **Edit**'s is
  `Edit scenario note`. The waiting line is announced politely as it appears.
  The dialog's accessible name is its title.
- **Light and dark:** the card uses the theme's tokens, as the other cards do.
  The waiting line uses the app's blue text color, checked in both themes in
  the mockup.

### How it is built

A sketch for the implementer, not a contract.

- **A store module of its own,** with read, save and delete for one
  scenario's note, the v1 validator, and the destination guard, shaped as the
  settings service is.
- **A card component,** `scenario_note_card`, holding the read view, the
  editor and the waiting line.
- **Browser-side state for the editor:** the scenario it opened on, the text
  it opened with, and whether the text differs. The card carries the last as
  an attribute, so a page script can read it.
- **A store for the waiting run,** set when the selection callback holds a
  run and cleared on release, on a run on the edited scenario, and when Follow
  goes off. The run summary store can't serve: it replays its last value to
  every later call, so a Cancel minutes later would follow an old run.
- **The selection callback** stays the one writer of both dropdowns. It gains
  the dialog's answers as an input and the editor's state as `State`. For a
  run, with unsaved changes, it sets the waiting store and moves nothing. For
  the card's button or a name in the list, it opens the dialog.
- **A callback on the dropdown's and the filter's values** opens the dialog
  when the scenario no longer matches the edited one.
- **A page script for the toast's link,** listening for clicks before Dash's
  own handler. While the card says there are unsaved changes, it stops the
  link and writes its scenario to the dialog's store with `set_props`, as the
  run list's script writes a name today.
- **The dialog** is a Mantine modal in the page's layout.

### Copy

Every string this proposal adds. They follow the nine copy rules in
[AGENTS.md](../../AGENTS.md#styling-conventions). The discussion's drafts were
checked against them: `No note yet.` loses its period, as `No runs yet` has
none, and the waiting line is shorter.

| Where | String | Why |
|---|---|---|
| Card, first line | `Scenario note` | Names a note that belongs to a scenario, leaving "session note" free. |
| Card, first line, if SN8 ships | `Scenario note · edited {age}`, such as `edited 3 weeks ago`; hover `Oct 9, 2026, 5:24 PM` | As the PB card's `PB · set {age}`. |
| Card, button | `Edit`; accessible name `Edit scenario note` | Short on screen, named in full for a screen reader. |
| Empty state, recommended | `Add a scenario note` | A link that says what it adds. |
| Empty state, alternative | `Scenario note` over `No note yet`, with `Add a note` | A status readout, as `No runs yet`. |
| Editor, text box | Placeholder `Note for this scenario`; accessible name `Scenario note` | A bare noun phrase, as rule 4 asks. |
| Editor, buttons | `Save`, `Cancel` | |
| Editor, count from 1,800 characters | `{n} of 2,000 characters`, such as `1,850 of 2,000 characters` | A readout, no period. |
| Waiting line | `A run on {scenario} is waiting. Press **Save** or **Cancel** to show it.` | Names where the page will go, and how. "Press" as in "press **Import**" on Playlists. |
| Dialog, title | `Your scenario note isn't saved` | |
| Dialog, body | `Save your changes to the note on {from} before you switch to {to}?`, where `{from}` is the note's scenario and `{to}` the one asked for | Names both scenarios. |
| Dialog, body, Playlist filter route | `The **Selected scenario** list no longer holds {from}. Save your changes to its note first?` | The player picked a playlist, not a scenario. |
| Dialog, buttons | `Keep editing`, `Discard`, `Save` | `Discard`, not `Cancel`, which could read as cancelling the switch. |
| Save error | `Couldn't save the scenario note. See data/logs/debug.log.` | Rule 9; the log pointer as rule 7 sets it. |
| Card and save errors, broken file | The schema machinery's messages with the kind `scenario note file`, such as `The scenario note file isn't valid JSON. File: {path}` | The shared wording for every store. |
| Card errors, version 1's own rules | `The scenario note file {predicate} File: {path}`, the predicate one of `has an unknown key "{key}".`, `is missing "{key}".`, `is for another scenario.`, `holds an empty note.`, `holds more than 2,000 characters.`, `must hold "{key}" as text.`, and if SN8 ships `must hold "edited_at" as a UTC time.` | As the settings file's predicates compose. |

### Terms

Written as [docs/glossary.md](../glossary.md) would hold it, under "The Run
History page". The shipping PR moves it in.

- **Scenario note.** The player's own plain-text note about one scenario, such
  as a reminder about technique, shown in Run History's top row while the
  scenario is selected. Each scenario has at most one, rewritten in place. It
  belongs to the scenario's exact name, so every version of the scenario
  shares it.
  - On screen: `Scenario note`.
  - In code: `scenario_notes`, the store and its folder.
  - Not a session note, a possible later idea that would belong to a session.

### Decisions this changes

The shipping PR keeps each entry and adds a dated "Superseded in part" note.
It erases nothing.

- [2026-10-14, the top row](../decision_log/2026/2026-10-14-run-historys-top-row-has-one-card-per-kind-of-information.md):
  "empty room with no element reserving it" now holds the note card. The
  spec's "the room kept for notes, which holds nothing" is rewritten.
- [2026-08-11, the schema stamp](../decision_log/2026/2026-08-11-durable-json-stores-carry-a-schema_version-stamp.md):
  its list of stamped stores gains the scenario notes, a store per file like
  the user playlists, whose errors show on the card. `architecture.md`'s
  "State" gains a scenario notes entry, and its "Schema stamps" stops counting
  three stores. The docstring of `store_schema.py` says the same.
- [2026-10-12, Follow and a scenario link](../decision_log/2026/2026-10-12-follow-and-a-scenario-link-clear-a-playlist-filter-that-does-not-list-the-scenario.md):
  Follow selects the scenario just played, except while a scenario note has
  unsaved changes, and the selection callback gains the dialog's answers.
  One callback stays the only writer of both dropdowns.
- [2026-10-13, the run toast](../decision_log/2026/2026-10-13-a-run-toast-is-plain-and-shows-on-every-page.md):
  on Run History, while a scenario note has unsaved changes, the link asks in
  the dialog and selects the scenario in place.
- [2026-10-14, the All scenarios view](../decision_log/2026/2026-10-14-the-run-list-has-a-second-view-all-scenarios-that-shows-each-session-whole.md):
  a name pressed in the tree asks first while a note has unsaved changes.

### Alternatives rejected

From the design discussion of 2026-10-18 unless marked.

- **Saving as you type, with the editor open only while it has focus.** Agreed
  for a while, then the maintainer preferred explicit buttons: v9's were small,
  and copying a note needs no edit.
- **Closing the editor when it loses focus, saving on close.** Withdrawn: a
  tab close or reload mid-edit would lose the edit, edge cases the maintainer
  cares about.
- **Escape putting back the text the editor opened with.** Withdrawn: Ctrl+Z
  already undoes a mistake while editing, and a reflexive Escape, which closes
  popups everywhere else, would be the likelier accident.
- **Asking in the card instead of a dialog:** the pick shows, the page waits,
  the card names the destination, and picking the old scenario again stays.
  Less intrusive, but it leaves an unresolved state in which the dropdown
  disagrees with the page. The dialog won on the clean state.
- **Locking the dropdown while the note has unsaved changes.** "It feels a
  little restrictive to the user."
- **Pausing Follow whenever an editor is open.** An editor left open during
  play would leave a stale page between runs. The wait holds only for unsaved
  changes.
- **Keeping the editor open on the old scenario while the page shows the new
  one.** One card would contradict the rest of the row.
- **A dated history of notes.** A day's observations are about a session.
- **A single notes file** for every note. It held in the measurements, and
  the maintainer still preferred a file per note: a save writes one note, a
  broken file costs one note, and a hand edit to another note is never
  overwritten, which a single file would need a re-read before each save to
  guarantee.
- **SQLite.** Nothing to query, a few dozen short texts, no machinery for it
  in the app, and authored state stays JSON (the storage note's bucket A).
- **File names from the scenario's name alone.** Two real names differ only by
  case, which Windows file names ignore, and reserved names such as `CON`
  would need escaping.
- **The stats file's hash as the key.** It changes when the scenario is
  updated (Evidence).
- **The file's modified time as the edit time** (SN8).
- **A toast's link that counts as leaving the page,** losing the text. The
  maintainer chose on 2026-10-18 to catch it and select in place. Catching it
  and then following the link was set aside too: the script would have to
  repeat `dcc.Link`'s navigation by hand.

## Delivery plan

Two pull requests, in order. This is intent, not a contract: a boundary that
moves is noted in the PR's description.

1. **The scenario note store,** with nothing on screen (SN6, and SN8's field
   if it ships). The module, the v1 validator, the destination guard, read,
   save and delete, their tests, and the code-truth docs: `architecture.md`'s
   "State" and "Schema stamps", and `store_schema.py`'s docstring. It needs
   SN6 and SN8 ratified. **Recommended:** `claude-opus-5-5` at high: it
   follows the settings store's pattern closely. Nothing to look at in
   Firefox.
2. **The note card, the editor, Follow's wait, the dialog, and the shipping
   docs** (SN1 to SN5, SN7, SN8's line). The card, the editor and the waiting
   line, the dialog and its routes, the toast link's script, the selection
   callback's changes, the CSS, and the
   [Shipping a proposal](../../AGENTS.md#shipping-a-proposal-docs-definition-of-done)
   checklist: the decision-log entries, the notes in
   [Decisions this changes](#decisions-this-changes), the Run History spec,
   the glossary's entry from [Terms](#terms), the user guide, the roadmap,
   `product.md`, and this file deleted. It needs PR 1 merged and the
   proposal ratified. **Recommended:** `claude-opus-5-5` at xhigh, since the
   editor's rules interact and it changes the shared selection callback. The
   maintainer looks at it in their own Firefox at 2560 px, with a run landing
   while a note is being edited.

**Why two:** the store is the part that is costly to reverse, and on its own
its review is about nothing but the format and its read and write states. PR
2 is then about behavior only. Against it: a store with no caller sits on main
until PR 2, and the format only reaches a player when PR 2 releases, so
merging PR 1 doesn't freeze it. One PR would also work; it would be large.

**PR 2 does not split further.** The editor can't ship without Follow's wait
and the dialog, which would otherwise lose text, and they are most of its
size.

**With Proposal 2:** if its implementation is open at the same time as PR 2,
the second to merge rebases onto the first and re-checks the selection flow.
PR 1 touches nothing Proposal 2 does.

## Out of scope

- **Following a scenario as it starts,** from KovaaK's log, which would show
  the note for the first run (SN4). Vault Backlog, Features item 8.
- **A note column on a playlist's scenario table,** hidden by default in the
  **Columns** menu. Vault Backlog, Features item 9.
- **Notes on playlists or benchmark categories.** Not tracked; a later
  proposal if wanted.
- **Session notes,** a different note tied to a session, with its own store.
  The name "session note" is left free for it.
- **A note in the run toast.** The toast stays plain
  ([2026-10-13](../decision_log/2026/2026-10-13-a-run-toast-is-plain-and-shows-on-every-page.md)).
- **A page listing every note.** It would read one file per scenario.
- **A history or undo of past notes** (SN1).

## Testing

- **The store, as pytest:** the file name for the four names in Evidence, and
  that the case-only pair gets two files; each read state (missing, each
  error cause, supported, future) and each v1 rule; a save that writes, a save
  of empty text that deletes, a save over a broken file that copies it aside
  first, a save of empty text from an editor opened on a broken file that
  copies it aside and deletes it, a save refused by a newer file, a name with a trailing space kept as
  it is; `edited_at` written only when the text changes, in UTC.
- **The selection callback, as pytest** with `ctx.triggered` faked as the
  current tests fake it: a run with unsaved changes moves nothing and sets the
  waiting store; a later run replaces it; a run on the edited scenario clears
  it; Follow off clears it; Save and Cancel release it once; a dialog answer
  selects, and Keep editing puts the old values back; a run with no unsaved
  changes moves the page as today.
- **Live, headless Edge and Firefox, at 2560, 3840, 1920 and 1536 px, light
  and dark,** in the served app with a scratch state root and runs copied into
  its stats folder:
  - runs landing mid-edit on another scenario and on the edited one, and the
    newest run winning;
  - each route opening the dialog, and Keep editing, Discard and Save from
    each, including a failed save;
  - one character typed in the same tick a run lands;
  - Escape doing nothing in the editor, and meaning Keep editing in the
    dialog;
  - an unchanged editor closing on a switch, by Follow and by hand;
  - a landing run never redrawing the card, checked by the text box's
    identity and its text across the run;
  - the chart's top not moving between a scenario with a note, one without,
    and no scenario selected;
  - after Keep editing on a pick, a reload opening on the old scenario;
  - the toast's link with no unsaved changes drawing the page again, as
    today.
- **The maintainer's look** in their own Firefox, on an instance of the PR's
  build.
- **Docs:** `tests/test_docs.py` for the links, and the gates in AGENTS.md.
