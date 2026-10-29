# 2026-10-29: The Latest-Run Card Is As Wide As The Run List's Minimum

Status: Accepted

The latest-run card is now 480px wide, the run list's minimum, instead of
500px. The default list sits at that minimum, so the card and the list line
up on the default page. A list that shows more columns still widens under the
PB card and leaves the card where it is.

**Maintainer direction, 2026-10-29.** "The only option that seems reasonable
so far is basically just option B, but only shrinking the Latest Run so that
it lines up with the Run History panel's minimum width." The layout built on
it was then chosen as "Copy A"
([the marks column's entry](2026-10-29-the-run-lists-marks-column-is-30px-and-three-columns-share-its-spare-room.md)).
Current behavior is in
[run_history.md](../../specs/run_history.md#the-top-row).

**The rule.**

- `--run-history-card-width` is `var(--run-history-list-width)`, so the card
  is the list's minimum by definition, and a change to one is a change to
  both. The card's width stays its own: the list's need never moves it, so
  a wider list never wraps the top row, which is why it got a width of its
  own ([2026-10-22](2026-10-22-the-latest-run-card-keeps-a-500px-width-of-its-own.md)).
- With the default columns the list needs 407px and takes its 480px minimum
  ([Shots Fired starts hidden](2026-10-29-the-run-lists-shots-fired-column-starts-hidden.md)),
  so the card's edges are the list's at every zoom level. Adding columns
  widens the list under the PB card, as before.
- The top row's first column gains the 20px.

**The card's lines fit.** Measured in Firefox 158 in the card's own classes
and fonts, every line the card can show fits a card of about 420px: the
widest is an older year's session with a three-digit run number and an
unknown time, `Run 124 (Dec 17, 2025, 12:48 AM session) · Time on this
scenario unknown`. A new PB has no typical phrase, so its comparison is its
gain alone. In the wide layout every line still fits on one at 480px.
