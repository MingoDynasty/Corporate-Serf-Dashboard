# 2026-10-21: Run History's Score Cards Stay Together After The Note

Status: Accepted

Run History keeps its three score cards together so their figures compare
at a glance. The scenario note sits beside the selectors, with spare room
between the note and the scores. The personal best stays next to the latest
run, and the first two score cards wrap together as space narrows.

**Ruling, 2026-10-21.** The maintainer, after the layout discussion and an
advisory consult with `claude-fable-5-1`: "I rule L1 and L2 as option A: the
note card moves right after the dropdowns, and the score cards read Typical
score, PB, then Latest run."

**The contract.**

- The first column's DOM order is the dropdowns' column, the scenario note
  card, then Scenario Stats and the PB card in one pair. CSS `order` does
  not reorder them, so keyboard focus and screen-reader order follow the
  screen. The latest-run card stays alone in the second column over the
  run list.
- Spare room sits between the note and Scenario Stats, never between the
  two score cards. The PB card stays at the first column's right end,
  beside the latest-run card.
- As the first column narrows, the score pair moves together to the next
  line's right end before the note wraps. If the column cannot hold the
  two score cards side by side, the pair itself wraps, with its inner
  lines packed to the right end.
- At a page area of 900 px or less, the row is one wrapping line packed
  from its start: dropdowns, note, Scenario Stats, PB, latest run. Both the
  first-column wrapper and the score-pair wrapper become `display: contents`.
- Every card stretches to its line's height. No reading or editor state at
  2,560 or 3,840 px is taller than on `main`.

**Why this order.** Scenario Stats now leads with a large typical score,
so the three score cards read as one strip only when nothing of another
kind separates them. The note belongs with the scenario selection, and
its flexible room and any remaining slack fall at the seam between
selection and scores. With no note, the Add link stays by the scenario's
name. The note keeps its weight and moves earlier in reading order;
[the rule for a card's lines](2026-10-14-a-cards-lines-follow-their-role-in-the-players-next-action.md)
stands.

The latest-run card's badge and percentage name the PB the run was chasing,
so the PB remains its neighbor. The chart already compares the run with the
typical score through its last point, line and bands. This preserves
[T1's reason for PB beside latest run](2026-10-14-run-historys-top-row-has-one-card-per-kind-of-information.md)
while moving the note from
[SN2's inherited spot](2026-10-18-run-historys-top-row-shows-the-selected-scenarios-note.md).

**Set aside.** Keeping the old order leaves the note, and on a wide screen
its spare room, between the typical score and PB. Option B, with PB before
Scenario Stats, would put the typical score next to the latest run, helping
a comparison the latest-run card does not print. The consult's tie-breaker
was what that card says today: it reports how close the run came to the PB,
while the chart supplies the comparison with the typical score. Aligning
all three large numbers to one baseline and adding a typical-score
comparison to the latest-run card remain outside this layout change.

**Mechanical delivery.** The wrapping `run-history-score-pair` flex box
carries the small gap, `margin-left: auto` and `max-width: 100%`. It keeps
default stretch alignment and packs an inner wrapped line to the right.
The PB card has `width: 300px` beside `flex: 0 0 300px`, as Scenario Stats
already has an explicit width. This is the preferred correction in the
2026-10-22 kickoff amendment: Firefox otherwise derives a 705.7 px wrapper
from the PB card's content instead of the 582 px occupied by the two cards
and gap, narrowing the note and making the pair wrap early. The explicit
PB width avoids restating both card widths in a wrapper `calc()` basis.

**Measurements.** The implementation is compared with `main` at `e08cbd5`,
whose runtime code and assets match the original `eb97872` baseline. Edge
155.0.4283.62 and Firefox 158.0.1 use isolated state, the same local stats
folder, no username, and percentile warmup disabled. Each reading case is
measured in light and dark with a saved note, without a note, and with no
scenario selected. The editor is opened through its control; draft input,
waiting and failed-save results are supplied to the production controller,
without modifying the stats folder. In Firefox the draft prop is synchronized after filling the text box,
because its headless fill did not reliably deliver the new value to Dash.

Heights are CSS pixels, rounded to one decimal. Selected covers both a
scenario with a note and one without; light and dark have the same heights.

| Browser | Window | Selected, main → PR | Unselected, main → PR |
|---|---:|---:|---:|
| Edge | 2,560 | 143.4 → 143.4 | 141.4 → 141.4 |
| Edge | 3,840 | 143.4 → 143.4 | 141.4 → 141.4 |
| Edge | 1,920 | 143.4 → 143.4 | 141.4 → 141.4 |
| Edge | 1,707 | 296.8 → 296.8 | 200.2 → 200.2 |
| Edge | 1,536 | 296.8 → 296.8 | 285.4 → 200.2 |
| Firefox | 2,560 | 143.1 → 143.1 | 141.4 → 141.4 |
| Firefox | 3,840 | 143.1 → 143.1 | 141.4 → 141.4 |
| Firefox | 1,920 | 143.1 → 143.1 | 141.4 → 141.4 |
| Firefox | 1,707 | 296.5 → 296.5 | 200.2 → 200.2 |
| Firefox | 1,536 | 296.5 → 296.5 | 285.4 → 200.2 |

At 1,536 px, selecting a scenario now moves the chart about 96 px rather
than about 11 px on `main`: the note's 132 px floor is on the first line,
not the wrapped score line. This is the permitted narrow-screen difference,
reported without adding a floor that changes the wide-screen layout. The
1,707 px unselected row was already about 200 px on `main`.

All eight editor combinations match `main` at both 2,560 and 3,840 px, in
both themes. The footer lines here are the waiting-run message, character
count and save error; `edit` means none is shown.

| Editor footer | Edge, main = PR | Firefox, main = PR |
|---|---:|---:|
| edit | 143.4 | 143.1 |
| count | 143.4 | 143.1 |
| waiting | 143.4 | 143.1 |
| error | 143.4 | 143.1 |
| count-waiting | 151.0 | 151.0 |
| count-error | 151.0 | 151.0 |
| waiting-error | 151.0 | 151.0 |
| all-three | 169.0 | 169.0 |

Adjacency, card stretch, wrapping together and the PB's alignment to the
column edge are checked from live geometry. Additional checks in both
browsers cover 1,800 px, the wrap transition at 1,880/1,878 px, a column too
narrow for both scores, and page areas of 901, 900 and 767 px. The 900 px
container rule flattens the wrappers and keeps DOM order packed from the
line's start.
