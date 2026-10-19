# 2026-10-18: A Scenario Note Is One Plain-Text Note Per Scenario, In A File Of Its Own

Status: Accepted

A player can keep one plain-text note on each scenario, such as a reminder
about technique, and rewrites it in place. Each note is saved as a small file
of its own, named from the scenario's name, and it records when its text last
changed. This is the first data in the app that a player writes and nothing
can rebuild, so its format is fixed by a schema version. There is no history:
once the editor closes, the earlier text is gone.

**Ruling and delivery.** SN1, SN6 and SN8 of the scenario notes proposal
([#390](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/390)),
ratified by the maintainer on 2026-10-18: "I ratify the scenario notes
proposal, SN1 to SN8, as at 88aa8b0." SN1 and SN6 as amended in review. The
store was built in
[#394](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/394),
the card and its editor in
[#PRTWO](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/PRTWO).
The card's behavior is in
[the scenario notes entry](2026-10-18-run-historys-top-row-shows-the-selected-scenarios-note.md)
and the editor's protections in
[the unsaved text entry](2026-10-18-unsaved-note-text-is-never-lost-to-a-change-of-scenario-or-page.md).

**What a note is (SN1).**

- At most one per scenario, plain text with its line breaks kept and no
  formatting or links, rewritten in place. Any scenario the page can select
  takes one, including a playlist's scenario never played.
- It belongs to the scenario's name as the app holds it: the stats file's
  `Scenario:` field with its outer spaces stripped, case and inner spaces
  kept. Every version of a scenario shares its note, and a renamed scenario's
  note stays with the old name. The hash names a version, not a scenario: 866
  names carried 882 hashes in the maintainer's folder, so a note keyed by hash
  would be lost at every update.
- The accepted cost, stated to the maintainer: no undo once the editor closes.
  While it is open, Ctrl+Z undoes and Cancel puts the saved text back.
- A day's observations belong to a session, not a scenario. Session notes are
  a possible later feature with a store of their own, and the name "session
  note" is left free for them.

**Where and how it is saved (SN6).**

- `data/scenario_notes/<prefix>-<code>.json`. The prefix is the name with
  every character other than a letter, a digit (as `str.isalnum` counts them),
  `-` or `_` turned to `_`; the code is the first 8 hex digits of the sha256
  of the name in UTF-8. This is the cache's formula, now shared as
  `safe_file_key` in `source/utilities/file_keys.py`. Two real names differ
  only by case, which Windows file names fold together, and the code keeps
  them apart.
- Version 1 is exactly `schema_version`, `scenario`, `text` and `edited_at`.
  `scenario` must equal the name asked for; `text` holds at least one
  character that isn't whitespace and at most 2,000 characters. Anything else
  is the error state.
- Each file is a stamped store of its own, read through the shared four-state
  machine: missing is no note, error and future show their message on that
  scenario's card, supported is the note. A file holding another scenario's
  note is in the error state too, so a save copies it aside and neither note
  is lost.
- Save reads the file on disk first: a newer build's file refuses the save, a
  broken one is copied to `<name>.corrupt-<n>.bak` before the save replaces
  it. Saving empty text deletes the note after the same check. Text equal to
  the readable note on disk writes nothing.
- A note is read when its scenario is selected and never cached; nothing
  scans the folder. The last save wins across tabs.
- A path longer than Windows allows fails to save, with the save's error, and
  the editor keeps its text. Nothing truncates the name.

**The edit time (SN8).** `edited_at`, in UTC to the second, written only when
Save changes the text, shown in local time. Not the file's modified time: a
conversion script, a git checkout or a sync tool changes that without an
edit. A hand edit outside the app leaves `edited_at` as it was. Stored from
the first version because a key added later is a new schema version, and a
note saved before it would have no time to show.

**Set aside.** A single notes file for every note (it held in the
measurements, but a save then rewrites every note and one broken file costs
them all); SQLite; file names from the scenario's name alone; the stats
file's hash as the key; the file's modified time as the edit time; a dated
history of notes, and keeping the previous text hidden in the file.

**What this changes in older entries.** It keeps its text and gains a
dated note.

- [2026-08-11, the schema stamp](2026-08-11-durable-json-stores-carry-a-schema_version-stamp.md):
  its stamped stores gain the scenario notes, whose errors show on the card.

Proposed in
[#390](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/390).
The proposal file, `docs/proposals/scenario_notes_proposal.md`, is deleted,
and git history keeps it.
