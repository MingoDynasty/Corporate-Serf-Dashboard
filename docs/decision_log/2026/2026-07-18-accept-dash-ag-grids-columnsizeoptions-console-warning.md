# 2026-07-18: Accept dash-ag-grid's `columnSizeOptions` Console Warning

Status: Accepted

Decision: The AG Grid console warning `invalid gridOptions property
'columnSizeOptions'`, emitted once per grid mount on the Playlists and
per-playlist scenario pages, is benign upstream noise from the dash-ag-grid
wrapper. We accept it, keep passing `columnSizeOptions`, and do not work
around it. It is distinct from the
[first-request pages race](2026-07-18-accept-dashs-first-request-pages-race-instead-of-warming-the-app.md):
that noise appears only on the first load after a server start, while this
warning appears on every mount of either grid.

Why: dash-ag-grid folds its remaining props into AG Grid's `gridOptions`
after stripping its own Dash-side props via a hardcoded list
(`PROPS_NOT_FOR_AG_GRID` in the wrapper's `src/lib/fragments/AgGrid.react.js`).
That list contains `columnSize` but not `columnSizeOptions`, so the prop
leaks through and AG Grid's validator flags an unknown key. Our usage is
correct — both are documented top-level `dag.AgGrid` props, and the wrapper
genuinely consumes `columnSizeOptions` (it destructures `keys`, `skipHeader`,
`defaultMinWidth`, `defaultMaxWidth`, and `columnLimits` from it to drive
`autoSizeColumns`/`sizeColumnsToFit`; verified in the installed 35.3.0
bundle). The upstream fix is adding one string to that list.

Correction to the record: the warning was believed fixed by the PR #146
upgrade to dash-ag-grid 35.3.0. Re-verification on a bare `main` baseline
(2026-07-18, during the PR #153 work) showed it still present, so treat it as
expected noise on 35.3.0, not a regression signal.

Alternatives rejected:

- Dropping the prop silences the warning but loses the `keys`/`skipHeader`
  autosize configuration — real behavior traded for cosmetics.
- AG Grid's blanket switch `suppressPropertyNamesCheck` would silence it —
  the bundled v35 validator still honors the flag — but the option is
  deprecated since v33 (AG Grid's deprecation message calls it redundant now
  that `context` exists for arbitrary user data), so enabling it trades the
  invalid-property warning for a deprecation warning while also disabling
  the check that catches real typos in our own gridOptions and colDefs.
- Re-implementing autosizing through a clientside grid-API call just to avoid
  the prop is a workaround for someone else's cosmetic bug — the same bar
  [the pages-race entry](2026-07-18-accept-dashs-first-request-pages-race-instead-of-warming-the-app.md)
  declines to meet.

Consequences: treat the warning as expected baseline noise during browser
checks. Not filed upstream as of 2026-07-18, so do not assume a version bump
fixes it; re-check cheaply after a dash-ag-grid upgrade by loading
`/playlists` and looking for the warning. If an upgrade makes it disappear,
mark this entry superseded.
