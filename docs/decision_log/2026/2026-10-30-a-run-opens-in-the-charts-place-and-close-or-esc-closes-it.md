# 2026-10-30: A Run Opens In The Chart's Place, And Close Or Esc Closes It

Status: Accepted

A click on any run in Run History, in the run list or on the chart, opens
that run where the chart was, with the list still beside it. Close, or the
Esc key, brings the chart back exactly as it was left. The open run isn't
kept in the address, so the browser's Back leaves the page and a reload shows
the chart.

**Ruling.** RV1 of
[proposal #450](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/450),
ratified by the maintainer on 2026-10-30 at `f80c109` ("Sounds good. I
ratify."), as recommended. Their lean before that, 2026-10-29, on keeping the
open run out of the address: "agree, but I also vote to make a keyboard
shortcut to make navigation a bit more seamless." Esc is that shortcut.
Shipped in
[#455](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/455),
on the reader from
[#453](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/453).
What the page does today is in
[run_history.md](../../specs/run_history.md#the-run-viewer).

**Opening** (`show_run` in `source/components/run_viewer_panel.py`, with
`assets/runViewer.js`):

- A click on a Run row in either view of the run list, Enter or Space on a
  focused Run row, or a click on a run point or a PB star in any chart mode.
  A position several runs share opens the run its tooltip names. Session and
  Scenario rows keep their own click and keys. Hover is unchanged.
- A chart click is plotly's `plotly_click`, not `dcc.Graph`'s `clickData`.
  The proposal expected `clickData`, which Dash drops when the same value
  repeats, so the same point clicked twice would need it cleared.
  `assets/runHistoryHover.js` already holds the graph's plotly events, and
  its click handler takes the run from the same points the tooltip names, so
  the same point clicked, closed and clicked again opens the run again.
- A click on another Run row switches the run, which starts from its top.
  The chart's points can't be clicked while a run is open, because the chart
  is hidden.
- A Run row of another scenario, under All scenarios, opens without changing
  the selection, and Close returns the selected scenario's chart.

**In the chart's place.** A class on the chart's column hides the chart's own
parts, its header and Chart options, and keeps them mounted. No callback that
opens or closes a run writes the figure. Closing shows the chart with its
mode, zoom, ranges and hidden traces as they were, and a chart drawn again
while hidden, as when a run lands, comes back at its column's width. The open
run's Run row carries an outline in either view. Opening a run measured 75 to
111 ms from click to drawn on the maintainer's stats folder, so it is a plain
server callback with no loading state.

**Closing.**

- Close, at the header's right with an `Esc` key hint and the accessible name
  `Close`, or Esc. Esc is left alone while a text field has focus or a
  dialog, menu or dropdown is drawn, and then does only what that control
  does with it. The listener is on the window in the capture phase, so it
  sees a Mantine overlay that Esc is about to close while it is still open,
  and one press never closes both.
- Focus goes to Close when a run opens, and stays on the row pressed when a
  run is switched from the list. On closing it goes back to the Run row that
  opened the run, or to the chart's mode control when a point or a star did,
  or when the row is no longer on screen.
- A change of the selected scenario closes the run, made by the player or by
  Follow: the chart the run stood in for is gone, and Follow means "show what
  I just played". A run that lands while one is open joins the list and the
  hidden chart, and the open run stays.
- The open run isn't written to the address and adds no history entry.

**Rejected.**

- A page of its own with tabs, the first concept. A page loses the list
  beside the run and the chart's state, and tabs hide the sections from each
  other on a page short enough to read top to bottom.
- The open run in the address, with Back closing it (shelved as S8). Run
  History writes nothing to the address, and a link to a run needs rules for
  a run whose file is gone and a scenario that isn't selected. Revisit if
  runs need to be shared or bookmarked.
- Arrow keys stepping between runs (S7): the run list's grid already moves
  its own focus with them. Older run and Newer run buttons (S6): the list
  beside the run already steps between runs.

**Supersedes in part** the
[2026-10-23 linked hover entry](2026-10-23-run-history-links-chart-and-list-runs-on-hover.md)
and the
[2026-10-24 compact tooltip entry](2026-10-24-chart-point-tooltips-show-score-time-and-run-numbers.md).
Both kept click actions out of scope, and the second accepted a navigation
gap "until a click feature exists". A click now opens a run. Hover keeps
every statement both make, and each entry gains a note.

**Provenance.** Proposal by `claude-opus-5-5` (#450), read by `gpt-6-astra`
(flagship, first wave) and reviewed by `gpt-6.1-sol` (the seat) and
`claude-fable-5-1`. Built by `claude-opus-5-5` in #453, #455 and
[#456](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/456),
which shipped the proposal.
