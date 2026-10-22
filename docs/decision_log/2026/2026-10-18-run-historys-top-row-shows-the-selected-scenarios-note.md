# 2026-10-18: Run History's Top Row Shows The Selected Scenario's Note

Status: Superseded in part by the
[2026-10-19 long-note entry](2026-10-19-a-long-scenario-note-scrolls-in-its-card.md):
a note taller than the card scrolls inside it, with a scrollbar Mantine draws,
and its bottom line fades only while more is below, so **Edit** is no longer
the only way to read it. The box rule, and the reasons against Show more,
stand.

Run History's top row now holds the selected scenario's note, in the room
kept for it between Scenario Stats and the PB card, so a reminder is read
with no click during play and during a lookup. A scenario with no note shows
only an **Add a scenario note** link, and with no scenario selected the room
is empty. The card takes the same box whatever it shows, so the chart under
it doesn't move while reading. A note is edited in place with Save and
Cancel, and the card grows only while editing, and only where the lines
under the buttons need the room.

**Superseded in part (2026-10-21).** [The score-strip entry](2026-10-21-run-historys-score-cards-stay-together-after-the-note.md)
moves the note after the dropdowns, before the score pair. Room beyond the
note's cap sits before both scores, and the pair wraps before the note.
The note still stretches to its line, and the score pair shares its 132px
floor. Beyond that floor, the wrapped score line takes its cards' height,
which varies with the selection and can grow when the pair itself stacks.
At a page area of 900px or less the pair has no box and its floor has no
effect. The existing long-note supersession and the rest of this entry stand.

**Ruling and delivery.** SN2, SN4, SN5, SN7 and SN8's line of the scenario
notes proposal
([#390](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/390)),
ratified by the maintainer on 2026-10-18: "I ratify the scenario notes
proposal, SN1 to SN8, as at 88aa8b0." The ratification covers Design and its
Copy block. On SN7 the maintainer, after the first review: "SN7: go with the
link." Built in
[#396](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/396).
Current behavior is in
[run_history.md](../../specs/run_history.md#the-scenario-note-card); what the
note is and how it is saved is in
[the storage entry](2026-10-18-a-scenario-note-is-one-plain-text-note-per-scenario-in-a-file-of-its-own.md).

**Why on screen (SN2).** The page has two uses, a glance between runs on a
second 4K monitor with Follow on, and a lookup: "before I play Scenario B, I
might manually swap to Scenario B, so I can look at its stats or notes." Both
want the note in view. At 2560 px, the maintainer's width, the card is 761 ×
143 px and a paragraph shows whole; at 3840 px it is capped at 800 px; at
1920 px it is 260 px wide and a paragraph is cut off and fades.

**The card.**

- Between the Scenario Stats card and the PB card, taking the room the row
  leaves, from 240 px to 800 px; at 3840 px the rest sits before the PB card.
  As tall as the row, and never less than 132 px.
- Its first line reads `Scenario note · edited {age}`, drawn as the PB card's
  `PB · set {age}`: relative, reworded every 30 seconds, the exact time on
  hover and focus (T4). **Edit**, drawn as a link, sits at the line's right
  end. A broken file's line has no age, and a newer build's file has no
  **Edit**.
- The note at 14 px, its line breaks kept, broken anywhere a word is too long,
  centered when short. One taller than the card runs to its bottom, and its
  last line fades. No Show more: growing the card would move the chart, and
  an overlay would cover the PB card. The editor shows the whole note.
- While reading, what the card shows is out of the layout's flow, so its box
  is the row's and never the note's. The text is selectable; only **Edit**
  opens the editor.

**The empty states (SN7).** With no note, the bare link **Add a scenario
note** and no frame, so a frame means "this scenario has a note", which a
glance across the row picks up, and lookups stay quiet. Most scenarios never
get a note, and an empty card would be the row's widest box framed around
nothing. With no scenario selected the room is empty and unframed. Set aside:
an empty card reading `No note yet` with **Add a note**.

**The editor's height.** The text box never shows less than three lines,
69 px, and scrolls inside itself. The editor keeps the row's height wherever
that fits, and the card, and the row with it, grows only where the lines
under the buttons (a waiting run, the count, a save error) need more room.
Measured at the build in Edge and Firefox, light and dark:

| Window | Row while reading | A run waiting | The count | Both | All three |
|---|---|---|---|---|---|
| 2560 | 143 px | 143 | 143 | 151 | 169 |
| 3840 | 143 | 143 | 143 | 151 | 169 |
| 1920 | 143 | 201 | 165 | 219 | 255 |
| 1536 | 297 | 322 | 297 | 340 | 376 |

Set aside: keeping the row's height at any cost, which left about 14 px of
text box at 1920 px while a run waited, and growing the row on every edit,
which moved the chart 45 px at 2560 px each time.

**Against `main`.** While reading, the row is as tall as on `main` in every
state at 2560, 3840 and 1920 px. At 1536 px, with the row wrapped, the card's
132 px floor holds the second line's height when no scenario is selected
(285 px where `main` has 200 px), so the chart moves 11 px between a selected
scenario and none where `main` moves it 97 px. The floor is there so a card
alone on a wrapped line still shows five lines.

**Scope (SN5) and the first run (SN4).** Notes are read and written only in
Run History's top row. With Follow on, the page reaches a scenario when its
first run's file lands, so its note shows from the second run of a visit;
selecting the scenario before playing shows it for the first run too. Over
the maintainer's last 30 days that gap was about one run in six. Following a
scenario as it starts, from KovaaK's log, is vault Backlog Features item 8,
and a note column on a playlist's table is item 9.

**What this changes in older entries.** Each keeps its text and gains a dated
note.

- [2026-10-14, the top row](2026-10-14-run-historys-top-row-has-one-card-per-kind-of-information.md):
  the "empty room with no element reserving it" now holds the note card.

Proposed in
[#390](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/390).
