# 2026-10-19: A Long Scenario Note Scrolls In Its Card

Status: Accepted

A scenario note taller than its card on Run History now scrolls inside the
card, with a scrollbar that stays in view whenever there is more to read. The
fade at the card's bottom shows only while more of the note is below, and goes
at its end. Before this, a note cut off inside a run of blank lines looked
whole, because the fade had nothing to fade and Firefox hides its own
scrollbar. The card keeps its box, so the chart under it still never moves.

**Ruling.** The maintainer tested #396's build with a note of two lines, eight
blank lines and `big gap`. At 2560 px the card shows six lines, so the note
read as two lines over empty space: "So there is no way to see the "big gap"
text at the bottom." Shown three options on a live prototype, they ruled on
2026-10-19: "I rule option 1." That is the note scrolling inside the card.
They then asked whether the scrollbar should always show while the note is
long, and pointed to dmc's ScrollArea. They ruled the same day: "Build option
1 with dmc ScrollArea type=auto and no chevron." This supersedes in part the
card bullet of
[the note card entry](2026-10-18-run-historys-top-row-shows-the-selected-scenarios-note.md):
**Edit** is no longer the only way to read a long note. SN2's box rule and its
reasons against Show more stand, because scrolling neither grows the card nor
covers the PB card. Current behavior is in
[run_history.md](../../specs/run_history.md#the-scenario-note-card).

**What it does.**

- The note sits in a `dmc.ScrollArea` with `type="auto"` and vertical
  scrollbars only. Mantine draws the scrollbar itself, 8 px wide, at the
  card's right edge, and shows it whenever the note is taller than the room
  under the first line, whatever the system's scrollbar setting.
- The scroll area is a flex item that shrinks to the room left in the read
  view, which stays out of the layout's flow, so the card's box is still the
  row's and never the note's.
- A page script sets `data-clipped` on the viewport while more of the note is
  below the visible part. It measures when the text is drawn, on every
  scroll, and whenever the text or the viewport changes size. The mask is on
  the viewport, so the scrollbar beside it doesn't fade. A scroll changes that
  attribute alone: no callback runs, and the note is never redrawn.
- Another scenario's note, or a note just saved, starts at its top.
- The wheel, a trackpad, and dragging Mantine's thumb scroll the note.
  Edge and Firefox make the viewport a tab stop only while it can scroll, so
  a short note adds no stop after **Edit**. From the keyboard, Tab reaches it
  and the arrow keys, Page Up and Down, Home and End scroll it.
- The viewport is a region named `Scenario note`, because a tab stop needs a
  name and a generic element can't carry one. The keyboard's ring is drawn on
  the scroll area: the area clips anything drawn outside the viewport.

**Why not the browser's scrollbar.** Firefox on Windows 11 draws overlay
scrollbars unless Windows' "Always show scrollbars" is on, which is how the
maintainer tests. Measured headless with overlay scrollbars on 2026-10-19: the
note's native scrollbar showed 300 ms after the page drew and was gone at
3 s, and `scrollbar-color` didn't keep it. No page setting keeps an overlay
scrollbar in view.

**Set aside.**

- Collapsing runs of blank lines while reading (option 2). It fits the
  maintainer's note but not a note that is simply long, and it breaks "line
  breaks kept".
- Leaving it as ratified (option 3). A note like the maintainer's looks
  shorter than it is.
- A hand-drawn cue over the browser's own scrollbar: a chevron while more is
  below, or a track always shown. The chevron added nothing once Mantine's
  scrollbar stays in view, and the track's thumb looked draggable and wasn't.
