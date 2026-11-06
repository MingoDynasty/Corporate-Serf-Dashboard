# 2026-11-05: The PB Card's Open Run Opens The PB Run And Brings Its Row Into View

Status: Accepted

The PB card's first line now ends with an Open run button, which opens the PB
run where the chart is, as a click on its point on the chart does. Beside it,
the run list opens the PB's session and scrolls the run's row into view. The
chart gains no mark, no range changes, and nothing is kept. This is the jump
to the PB that the design of the top row's cards set aside for a later, small
change.

**Approval and delivery.** Approved by the maintainer on 2026-11-05, from
the design brief "Jump to PB" by `claude-fable-5-1`, a note in the
maintainer's own files. The brief left five questions to the maintainer.
Each took the brief's recommended answer, and the pull request that built it
listed them as open, so its merge settles them:

1. The jump is the run viewer, not a standing mark on the chart.
2. A press opens the PB's session in the run list and scrolls its row into
   view, rather than leaving the viewer's outline on the row where it is.
3. The button sits on the first line, after the age, since it doesn't move
   the card's lines; the score row after the badge was the fallback.
4. Its label is `Open run`. `Jump to PB` says less about what happens.
5. It stays when the PB is the latest run.

What the page does today is in
[run_history.md](../../specs/run_history.md#the-pb-card).

**Why.**

- **The origin.** The maintainer's Backlog asked to make the target clear at
  all times, "maybe even a 'click to jump to PB'", on the chart and in the
  run list. The PB card shipped with #379's rows. D19 of that design's
  working note of 2026-10-14, left out of #379, dropped a jump to the latest
  run (the maintainer: "the use case is slim"), kept the jump to the PB for
  "a later, separate proposal or small PR", and rejected making the
  timestamps links.
- **The chart half has nothing to reach.** In the brief's count over the
  maintainer's 9,284 runs through 2026-10-29, the PB is on the default chart,
  Last 100 runs, on all 585 scenarios with two runs or more, and on every
  scenario played in the last 90 days it is within 9 runs of the end. The PB
  score line, on by default, touches it, and it is the last gold star. A mark
  would repeat the line, as
  [the stars entry](2026-10-05-the-score-vs-time-chart-marks-each-new-pb-with-a-star.md)
  said when it rejected one.
- **The viewer answers the question behind "what is the target".** It names
  the run's date, its session and its place in it, its settings, and how it
  stood against the typical runs of its day, under its own version.
- **The list needs one motion.** Only the first session is open on arrival,
  so the PB's row is usually under a closed one. Opening it is what a
  session's count does
  ([2026-10-14](2026-10-14-a-sessions-count-jumps-to-it-in-the-tree-and-an-open-session-row-has-show-all-runs.md)).
  It is a press, not a highlight, so the rule that a selection change never
  opens rows or scrolls to the latest run
  ([2026-10-23](2026-10-23-run-history-highlights-the-selected-scenarios-latest-run.md))
  doesn't bind it.
- **It keeps the card's rules.** A small action beside the fact it acts on is
  what Refresh already is on this card
  ([2026-10-14](2026-10-14-a-cards-lines-follow-their-role-in-the-players-next-action.md)).
  No line is added, no fact moves, and no number changes what it means.

**The rule.**

- **The button.** A subtle `compact-xs` button with an eye icon, built as
  Refresh is, at the right end of the first line. Its accessible name is
  `Open run of your PB`, which starts with its words, so a voice command
  that says them still finds it. Its hover and focus show "Open your PB run
  where the chart is, and show its row in the run list." It shows in every
  state with a local PB, the PB being the latest run included, and is
  hidden with no scenario selected and with no local PB.
- **The line keeps its height.** The button is 22px and the line 18px. It is
  floated to the line's end, since the line is not a flex box (that would
  drop the spaces either side of the age), with 2px negative margins above
  and below. The line stays 18px, so the 12px offset and the lines' shared
  tops of [SC4](2026-10-25-run-historys-three-score-cards-line-up-from-the-top.md)
  hold, and the row stays 141.4px.
- **The run.** The PB run the card describes: the earliest run, in the run
  store's order, to reach the high score, by its run id. It is read when the
  button is pressed, so after a new PB it opens the new one.
- **The request.** The run viewer's own, `runViewer.request(id, "card")`, a
  third source beside `list` and `chart`. Focus goes to Close when the run
  opens, and back to the button on Close or Esc. A card that no longer shows
  the button sends it to the chart's mode control. Pressed while another run
  is open, the button switches to the PB run and keeps focus. Pressed while
  the PB run is open from the list or the chart, it changes only where Close
  returns, as a second press elsewhere already did.
- **The list.** In the view on screen, the press opens the PB row's session
  row, and under All scenarios its scenario row, then scrolls the row into
  view as little as it takes. Keyboard focus stays where it is, rows already
  open stay open, and nothing is said in the live region. A PB whose session
  the view hasn't loaded is left alone, and no older sessions load; the run
  still opens. On the maintainer's data every PB's session is among the
  first 30.
- **Not done.** No mark, ring or trace on the chart, and no range change.
  Nothing is persisted: the open run is held by the page, as any open run
  is. The score and the age stay tooltips, not links.

**Rejected.**

- **A standing mark on the chart for the current PB.** It repeats the PB line
  and the last star. When the PB is the latest run, two thirds of the
  maintainer's scenarios, it would sit under the latest-run ring. When the
  range leaves the PB off the chart, the one case a jump is for, it shows
  nothing, since the range is never widened for a mark.
- **The age or the score as the link** (D19). Both already carry a tooltip
  with the dotted underline.
- **Loading older sessions to reach a PB row.** No PB on the maintainer's
  data needs it, and the viewer opens either way.
- **Hovering the card's score to emphasize the PB's point and row**, as
  hovering a row does. Optional and not built: transient, and the score's
  hover already shows the gain.

**What this changes in older entries.** Each keeps its text and gains a dated
note: [the PB card entry](2026-10-14-the-pb-card-shows-the-local-record-and-next-rank.md),
whose card was "neither a landmark nor a button" and held one control, and
[the run viewer's opening entry](2026-10-30-a-run-opens-in-the-charts-place-and-close-or-esc-closes-it.md),
whose runs opened from the list and the chart alone.

**Provenance.** Design brief by `claude-fable-5-1`. Built by
`claude-opus-5-5`.
