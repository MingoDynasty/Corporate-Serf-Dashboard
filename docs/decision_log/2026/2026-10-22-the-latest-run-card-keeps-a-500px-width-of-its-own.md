# 2026-10-22: The Latest-Run Card Keeps A 500px Width Of Its Own

Status: Accepted

The latest-run card on Run History keeps the 500px it had, as a width of its
own, instead of following the run list's width. On the default page the two
are still the same width and line up, because the list is at its 500px
minimum. Once a player turns a column on and the list grows, the list reaches
further left than the card, and the top row doesn't wrap.

**Ruling.** RC3 of
[#403](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/403),
ratified by the maintainer on 2026-10-22: "I ratify the run list columns
proposal, rows RC1 to RC3, as amended at 20f6619", the fixed 500px included.
The direction was the maintainer's: "my initial thought is to remove Latest
Run card's width's dependency, and allow it to size on its own based on the
Top Row along the other cards. Long term we can plan to have a Session Clock
or other useful information. But for now I think this unblocks?" It
supersedes in part
[T1 of the top-row cards](2026-10-14-run-historys-top-row-has-one-card-per-kind-of-information.md),
its "The latest-run card aligns over the run list instead of filling the
remaining width" and the shared 500px column; the rest of T1 stands. Shipped
in
[#406](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/406).
What the page does today is in
[run_history.md](../../specs/run_history.md#the-top-row).

**Why a width of its own.** With the card following a list that fits its
columns ([the width rule](2026-10-22-the-run-list-grows-to-fit-the-columns-it-shows.md)),
the top row at 1920 went from 143px to 297px as soon as the list passed
500px, with Reloads alone: the PB card dropped to a second line, and the
chart lost 154px of height. At 2560 it stayed one line even at 744px. With
the card's own width, the row is 143px at 1920 with every column set.

**Two values, equal on purpose.** The stylesheet holds the list's 500px
minimum and the card's 500px as two values side by side. They are equal so
the default page lines up as T1 made it, and a change to one asks whether
the other follows. The card's tallest state was measured at 500px, and its
135px minimum height holds it, so nothing about the card needed measuring
again.

**Alternatives set aside.**

- **A card sized to its content,** about 360px, estimated from its longest
  second line. It would free about 140px for the top row's first column at
  every width, which at 1920 goes to the note card, already able to grow to
  800px, and at 1536 unwraps nothing. It would also cut the scenario's name
  in the card sooner, change every player's default page, and part the card
  from the list on every load.
- **A card that fills the room left.** It would compete with the note card,
  which already flexes from 240px to 800px for that room.
- **Keeping the card on the list's width.** It wraps the top row at 1920
  whenever a column is on.
- **Splitting the card** into a run card and a session card. A live session
  clock would count the current break, which a session's length leaves out
  on purpose, so it waits on the definition of a session's time. The 270px
  run card in the mockup also cut the scenario's name.

**Narrow windows are unchanged.** Where the page stacks, the card joins the
top row's wrapping line at 380px and takes the room left on it, as before.
