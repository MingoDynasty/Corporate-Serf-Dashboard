# 2026-10-28: The Scenario Note Lines Up With The Score Cards

Status: Accepted

The scenario note card on Run History now starts its lines 12 px below its
top edge, as Typical score, PB and Latest run do, instead of centering them.
Its first line then sits level with theirs whatever the note holds, and so
does the Add a scenario note link when there is no note. A long note shows
12 px less before it scrolls, and the row keeps its height.

**Ruling and delivery.** On 2026-10-27 the maintainer asked why Typical
score, PB and Latest run had been lined up
([SC4](2026-10-25-run-historys-three-score-cards-line-up-from-the-top.md))
and the note card had not, and whether to align it. The proposal behind SC4,
[#430](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/430),
never names the note card, in its rows or its Out of scope: it was left out by
scope, not judged. The maintainer's lean that day: "I'm leaning toward
aligning it." Two advisory consults, `claude-fable-5-1` and `gpt-6.1-sol` at
xhigh, each reached the same recommendation independently: a fixed offset,
the Add link on the first line, and the editor unchanged. Sol also suggested
15 px note text. Asked "Rule it as recommended and open the draft PR?", the
maintainer ruled on 2026-10-28: "Rule it, keep 14px." Current behavior is in
[run_history.md](../../specs/run_history.md#the-scenario-note-card).

**Why.** The card centered its lines because every card in the row did when
it shipped, and its first line is drawn as the PB card's. SC4 lined up the
three score cards and left the note's first line the one off theirs, at a
height that followed the note's length: the stagger SC4 was made to remove.
On `main` at `911ca00`, at 2560 px, against the score cards' 13 px from their
top edge, it sat at 50.7 px over a one-line note, 30.7 over three lines and
1 over a long one, and the Add link at 59.8.

**The rule.**

- `.run-history-note-read`, the reading view, pads its top with
  `--run-history-score-card-top` and sets no `justify-content`, so its lines
  start from the top: the first line 13 px below the card's outer edge, the
  note under it, and any spare room at the bottom.
- **Padding, not SC4's spacer.** The reading view is out of the layout's
  flow, so padding there never makes the card or the row taller, which is
  what the score cards needed a spacer for. A spacer takes only spare room,
  so a long note would take the offset back and its first line would sit at
  the card's top edge, 12 px above the others.
- The card shares the score cards' variable, so while the PB card shows a
  leaderboard hint it starts its lines at its top edge with them. In SC4's
  ruled exception the PB card's lines start higher than the note card's, as
  they do than the other two cards'.
- With no note, **Add a scenario note** sits on the first line, where the
  note's first line appears after a Save. A broken file's view and a newer
  build's follow the same rule. With no scenario the card is empty.
- The editor keeps its own spacing. Its text box's text starts about 3 px
  below where the note's text starts while reading, so opening **Edit**
  hardly moves the text. Giving the editor the 12 px made the row 147 px
  while editing at 2560 and 1920 px, the growth the note card entry set
  aside.
- The note text stays at 14 px.

**What it costs.** A long note's room under the first line is 12 px shorter:
107.4 px where it was 119.4, so about five lines show, the last fading,
where about six did. By arithmetic, a card alone on a wrapped line at its
132 px floor shows about five lines where it showed five and a half; no
measured width put the card there.

**Measured at the build,** in headless Edge at 3840, 2560, 1920, 1536, 1100,
800 and 700 px, and in Firefox at the first four, light, on the maintainer's
stats with the Position lookup faked as ranked; with no username, in Edge at
2560 and 1920. Each column is the same page and data, `main`'s reading-view
rule injected for the first. Firefox matched Edge to 0.1 px.

| | `main` | This rule |
|---|---|---|
| The note's first line or Add link, at every width: one-line, three-line, long note, no note | 50.7, 30.7, 1, 59.8 px at 2560 and 3840; 40.7, 20.7, 1, 59.8 at 1920 and 1100 | 13 px in every state |
| A broken file's first line | 30.7 px at 2560 and 3840, 1 at 1920 and below, where its message wraps to fill the card | 13 px |
| The score cards' first lines, from 1100 px up | 13 px | 13 px |
| The row | 141.4 px from 1920 up, 285.4 at 1536, 330.4 at 1100, 530.7 at 800, 441.4 at 700 | the same |
| With no username: the note's first line | 51.7, 31.7, 1, 60.8 px at 2560 | 1 px in every state, as the score cards |
| With no username: the row | 143.4 px | the same |
| A long note's visible room | 119.4 px, 121.4 with no username | 107.4 px, 121.4 with no username |

At 1536 px the score cards wrap to a second line and the note stays on the
first, level with the Latest run card. At a page area of 900 px or less the
cards sit on lines of their own.

**What this changes in older entries.** Each keeps its text and gains a dated
note.

- [2026-10-18, the note card](2026-10-18-run-historys-top-row-shows-the-selected-scenarios-note.md):
  the note centered when short, and the Add link centered with it.
