# Run History

The Run History page shows one scenario's runs three ways: a chart of every
run in a range, a list of the runs grouped by session, and a card for the
last run played. A run that lands reaches all three with no reload, and the
page can follow the scenario just played. A check beside a run's score says
the run met the score threshold and a star says it set a new personal best,
each judged as of when the run was played. The browser remembers every
control on the page, the chosen playlist and scenario included.

Statements below describe what the app does today and link the
[decision log](../decision_log/README.md) entries that set them. Rationale
lives in those entries, not here. A statement with no link is an
implementation fact that no decision-log entry governs. Runtime structure is
mapped in [architecture.md](../architecture.md), the user-facing rationale in
[product.md](../product.md), and what the terms mean in the
[glossary](../glossary.md). What a session is, and when one is in progress,
is in [sessions.md](sessions.md). The Aim Training Journey page
(`/aim-training-journey`, reachable by URL only) is work in progress and out
of scope here, apart from its chart toolbar, noted under The chart.

## Identity

- The page is registered at `/run-history`
  ([2026-10-12][address]). Its name is "Run History": the navbar link, the
  page `name`, and the browser-tab title ([2026-10-12][name]).
- The navbar reads Home, Run History, Playlists, Settings. Its Run History
  link leads to the page with no parameters, where a reload changes nothing.
  The header title leads to [Home](home.md), not to this page
  ([2026-10-12][address]).
- The preference panel and its disclosure button are named "Chart options",
  and the controls inside carry the vocabulary the app's own chart
  annotations and the aim-training community already use, "PB score" and
  "Score threshold", rather than invented terms
  ([2026-08-09][naming]).
  Control labels, placeholders, tooltips, and toast titles are sentence case.
  The page title, the group headings, the run list's column headers, and the
  named chart modes "Score vs Run", "Score vs Time", and "Score vs
  Sensitivity" keep their capitals
  ([2026-09-14][copy]).
- Page copy says "Position" for leaderboard placement and reserves "Rank"
  for benchmark tiers, as in the "Rank thresholds" overlay. The rule lives in
  [scenario_rank.md](scenario_rank.md)
  ([2026-07-06][one-word]).
- With `show_version_in_title` enabled, the tab title is prefixed with the
  build's release label. The key is specified in
  [settings.md](settings.md#the-configuration-file).
- `?scenario=` and `?playlist_code=` query parameters select the two
  dropdowns, and the selection they make is remembered exactly like one made
  by hand: arriving from a scenario link in a playlist's table and then
  returning to the page shows that playlist and scenario, not an earlier one
  ([2026-09-19][query]).
  That holds for a hidden playlist too: `?playlist_code=` selects any loaded
  playlist, and the filter names it
  ([2026-10-12][hidden-filter]).
  A parameter the URL omits leaves its control on the remembered value. An
  unknown playlist code clears the filter. The parameters are applied on
  every load of that URL, so reloading a link applies it again over a later
  choice, and the selection it makes becomes the remembered one
  ([2026-09-19][query]).
- A scenario that the Playlist filter does not list is still selected, and
  the filter is cleared in the same step. That holds for a `?scenario=` link,
  for a run the page follows, and for the latest-run card's scenario button.
  The scenario must have local runs: a link that names one with none leaves
  the filter alone and selects nothing. The filter empties in view with no
  toast, and the cleared filter is what the browser then remembers
  ([2026-10-12][clear-filter]).
- The page accepts query parameters it does not name and reads none of them.

## The top row

- The row holds, in order: the "Playlist filter" select, with the "Open
  scenario table" link beneath it while a playlist is selected, the "Selected
  scenario" searchable select (placeholder "Select a scenario") with the
  "Follow newly played scenario" switch beneath it, the Scenario Stats block,
  and the latest-run card, which fills the rest of the row
  ([2026-10-12][column]).
  The two dropdowns and the Follow switch persist in the browser. The Follow
  switch carries a help tooltip: "Automatically selects the scenario you just
  played when a new run is detected. If the **Playlist filter** doesn't list
  that scenario, the filter is cleared."
  ([2026-10-12][clear-filter]).
- Opening either dropdown's list keeps the selected name in the field and
  highlights it, so it can be copied, and the first keystroke replaces it
  with a search. The list shows every option until then. A drag on the field
  highlights only the part dragged over, and a second click while the list is
  open places a cursor. Every other way in highlights the whole name: a click
  on the label, a right-click, Tab, and focus returning to the page. After a
  pick or Escape, focus stays in the field with the list closed. An edit or
  an arrow key there highlights the name first, so typing still starts a
  fresh search, and a right-click there highlights it when the field shows
  only a cursor
  ([2026-10-12][highlight]).
- The Follow switch sits under the scenario selector, not in the panel: it
  governs selection, not presentation
  ([2026-08-09][panel]).
- The playlist filter lists the visible playlists
  ([playlists.md](playlists.md#the-overview)), plus the playlist it
  holds when that one is hidden. A hidden playlist becomes the selection
  through a `?playlist_code=` link, which every row of its scenario table
  carries, or by being hidden while it is selected. It is listed only while
  it is held: picking another playlist or clearing the filter takes it out of
  the list, and it can't be picked again until it is shown. Nothing in the
  list marks it as hidden. A playlist the URL names is in the list when the
  page paints. One the browser restored is added by the callback that lists
  the playlist's scenarios, so its name appears just after the page paints
  ([2026-10-12][hidden-filter]).
- While the playlist filter holds a loaded playlist, the "Open scenario
  table" link under it leads to that playlist's scenario table at
  `/playlists/{code}`, which opens in playlist order
  ([playlists.md](playlists.md#routes-and-navigation)). There is no link, and
  no room held for one, while the filter is empty. The callback that lists the
  playlist's scenarios writes the link, so it arrives with that list just
  after the page paints, whether the selection was remembered, made by hand,
  or named by `?playlist_code=`.
- A remembered code that no playlist has does not stay in the filter. When
  the page loads, the filter drops it and is empty, with no clear button, and
  nothing is remembered: the list the filter is given has no such playlist,
  and the Select drops a value its new options lack
  ([2026-10-12][hidden-filter]).
- The row wraps on its own width and never on the window's
  ([2026-08-03][content-area]).
  Each dropdown joins a line at 200px and grows back toward a 400px target,
  twice as fast as the card beside it, so a row with room to spare gives it
  to the scenario's name first. The card is 380px wide at least.
- The scenario list comes from the selected playlist when one is chosen, and
  otherwise from the scenarios with at least one run loaded from the stats
  directory, named by each file's own `Scenario:` field
  ([2026-09-12][local-list]).
  Without a usable stats directory that local list is empty, while a selected
  playlist still lists its scenarios. The list is read again when a run
  lands, so a scenario whose first run has just landed is in it with no
  reload, whether or not the page follows that run.

## The latest-run card

- The card reports the last run played, on whatever scenario, and is worked
  out from the run store each time, never from the message a new run arrives
  in. So it is right on a page load with no new run
  ([2026-10-12][check]).
  The last run played is the last run of the newest session, in the order
  [sessions.md](sessions.md#sessions) sets.
- Its first line reads `Latest run · {time} · {scenario}`. The time is a
  time of day for a run played today, such as `10:50 PM`, and carries the
  date otherwise: `Oct 4, 10:50 PM`, or `Dec 30, 2025, 10:50 PM` in an
  earlier year. While the run's scenario is the selected one its name is
  plain text, with the whole name as its tooltip where the card cuts it
  short. While another scenario is selected the name is a button, drawn as
  the app draws a link, whose accessible name is `Show {scenario}`. Pressing
  it selects that scenario in place, clearing a Playlist filter that does not
  list it, and the button then leaves the card
  ([2026-10-12][check],
  [2026-10-12][clear-filter]).
  A press from the keyboard hands keyboard focus to the Selected scenario
  dropdown once the button has gone, and the dropdown opens its list as it
  does when tabbed into. A click with the mouse moves focus nowhere.
- The score is large, formatted as the playlist scenario table formats PB
  Score, with one badge beside it. A new PB shows "New PB", whether or not
  the run was judged. Otherwise a judged run shows "Threshold passed" or
  "Below threshold", and a run nothing judges shows no badge
  ([2026-10-12][check]).
  The badges are yellow, green, and gray in that order.
- The second line compares the run with the PB it was chasing, then gives
  its accuracy to the whole percent: `{pct}% of PB · Accuracy {accuracy}%`,
  or `{pct}% of PB pace` where the comparison is by pace. A new PB says how
  far it beat the previous best instead:
  `Up {pct}% on your previous best of {previous}`,
  `{pct}% faster than your previous best of {previous}` by pace, or
  `Your previous best was {previous}` over a previous best of zero or less.
  The percentage is a fact about the run, so it shows whether or not the run
  was judged, and an empty threshold doesn't hide it. Two kinds of run have
  none and show `Accuracy {accuracy}%` alone: a scenario's first run, and a
  run that is not a new PB and is compared by score with a previous best of
  zero or less
  ([2026-10-12][check]).
  The percentage has one decimal and the two display caps of the run toast
  ([notifications.md](notifications.md#run-notifications)): a run below the
  PB shows at most 99.9%, and a judged miss shows at most one tenth under
  its goal.
- The third line reads `Run {n} this session · {duration} on this scenario`
  while the run's session is in progress, and `Run {n} last session` once it
  has ended. `{n}` counts the session's runs on the run's scenario. The
  duration is the time spent on the scenario in the session, as
  [sessions.md](sessions.md#where-sessions-show) defines it. Where that time
  can't be known the line reads `Time on this scenario unknown` in its place
  and keeps the run's number
  ([2026-10-12][check]).
- A measured time, here and in the run list, is rounded to the nearest
  minute, a half rounding up: `9 min`, `1 hr 6 min`
  ([2026-10-13][nearest-minute]).
  A time that rounds to zero reads `<1 min`, so that form means under 30
  seconds.
- The card is one height in every state, so the page doesn't jump. With no
  run in the store it reads "No runs yet" over "Play a scenario in KovaaK's
  and your latest run will show here.", at the same height
  ([2026-10-12][check]).
- The card is rewritten when a run lands on any scenario, when the selected
  scenario changes, when the Score threshold percentage changes, when the
  date moves on, and when the newest session stops being in progress. A run
  that lands older than the run store's newest leaves the card as it was.

## The chart

- The chart has three modes, chosen by a segmented control in the chart's
  header whose accessible name is "Chart mode": "Score vs Run", "Score vs
  Time", and "Score vs Sensitivity". It opens on Score vs Run
  ([2026-10-12][every-run]).
- Each mode plots every run of the scenario in its range as a point, legend
  "Run data point". No mode draws a summary line
  ([2026-10-12][every-run]).
- Score vs Run plots the runs in the order they were played, evenly spaced.
  The order is the one [sessions.md](sessions.md#sessions) sets, so the chart
  and the run list never disagree about which run came first. A run's place
  on the axis is its number in the scenario's whole history, so it keeps its
  place when the range changes. The axis title is "Run" and its labels are
  dates, one at the first plotted run of a day, in the form `Oct 12`, or
  `Dec 7, 2025` in another year than this one. The labels are thinned on the
  server for a plot 330px wide, from the newest back, so the day being played
  keeps its label
  ([2026-10-12][every-run]).
- Score vs Time plots each run at its own timestamp, on an axis titled
  "Date". Score vs Sensitivity plots each run at its sensitivity-and-scale
  string, on an axis titled "Sensitivity", with the sensitivities in sorted
  order
  ([2026-10-12][every-run]).
- The range is a select beside the mode control, with the accessible name
  "Range" and no visible label. Under Score vs Run it counts runs: "Last 50
  runs", "Last 100 runs", "Last 200 runs", or "All runs". Under the other two
  modes it counts days: "Last 7 days", "Last 14 days", "Last 30 days", "Last
  90 days", "Last 12 months", or "All time". The chart opens on the last 100
  runs, or the last 90 days. The mode and both ranges persist in the browser,
  one remembered range for runs and one for days: they are two selects, both
  always in the layout, and the one the mode does not use is hidden
  ([2026-10-12][every-run]).
- A range of N days is N calendar dates, counting today: it starts at local
  midnight N minus 1 days before today, so on October 11 the last 7 days are
  October 5 to 11. The last 12 months are 365 days, counted the same way. The
  date is the app's own, never the browser's. A chart left open past midnight
  is redrawn within 30 seconds of the date moving on, with no toast
  ([2026-10-12][every-run]).
- The plot title is the scenario's name alone
  ([2026-10-12][every-run]).
- Score vs Run and Score vs Time mark each plotted run that set a
  [new PB](../glossary.md#new-pb) with a star: a second trace, legend "New
  PB", drawn over the run points. A new PB is a run whose score is strictly
  above every earlier run of its scenario, judged oldest first over the
  scenario's whole history, at every sensitivity and including runs the range
  leaves out. So a tie is not one, the earliest run to reach a score holds
  it, and the scenario's first run is not one. A star belongs to its run, not
  to a position on the chart. A new PB the range leaves off the chart gets no
  star and still counts in the comparison. With no new PB among its points
  the chart has no New PB trace and no legend entry, and Score vs Sensitivity
  never has one
  ([2026-10-05][stars],
  extended to Score vs Run by
  [2026-10-12][stars-run]).
  New PBs are judged in the order the runs were played, so a star sits on the
  same run of a same-second pair as the axis puts first.
- The scenario's newest run carries a ring while it is also the last run
  played on any scenario and the range holds it. The ring has no legend entry
  and no hover of its own, and is drawn over a star. It is the app's blue,
  `#1c7ed6` on the light background and `#74c0fc` on the dark one. A run on
  another scenario takes the ring off with no new figure, so a zoom on the
  chart is kept
  ([2026-10-12][every-run]).
- A run recorded under a game's own sensitivity scale is normalized to cm/360
  when its file is parsed, from the file's own `Sens Increment` and `DPI`
  fields, by `cm/360 = 360 x 2.54 / (0.07 x increment x DPI)`. A run whose
  file lacks either field, or carries one the conversion cannot use, keeps its
  recorded value and scale. Every consumer reads the normalized fields, so the
  normalized sensitivity-and-scale group is the unit for grouping, for run
  placement, and for first-sensitivity detection
  ([2026-09-11][normalize]).
  A cm/360 value, native or converted, is rounded to one decimal place, so a
  typed value and a converted one a few hundredths apart share a group. The
  buckets have hard edges: `40.849` and `40.851` land in `40.8` and `40.9`. A
  value on any other scale keeps exactly what its file recorded, so
  `0.32 Valorant` reads `0.32 Valorant`
  ([2026-09-27][precision]).
  A converted run also keeps the value, scale, and DPI its file recorded,
  unrounded, for the point hover only
  ([2026-09-26][recorded]).
- Point hover is the same in each mode. It shows the run's timestamp with
  seconds kept, the one surface that keeps them, cross-referencing KovaaK's
  second-stamped CSV filenames
  ([2026-07-11][timestamps]).
  Then come the score, the run's sensitivity-and-scale string, and the
  accuracy to two decimals. A converted run's sensitivity line adds the
  setting it was recorded at, as in
  `Sensitivity: 40.8 cm/360 (0.2 Valorant at 1600 DPI)`. Any other run's line
  ends at its sensitivity
  ([2026-09-26][recorded]).
  A star takes no hover of its own, so hovering one shows its run's hover.
  Runs at one position share one hover, the one whose point comes last in the
  run trace. In Score vs Time that is runs that ended in the same second with
  the same score, and a new PB is ordered last among them, so the star's
  hover names the run that set the PB. Score vs Run gives every run its own
  position. Score vs Sensitivity still shares positions and has no stars
  ([2026-10-05][stars]).
- Three overlay families, all dashed labelled lines. "PB score ({value})"
  and "Score threshold ({value})" draw at the current personal best and at
  the configured percentage of it, while a run's verdict is judged against
  the PB the run was chasing
  ([2026-07-08][previous-pb]).
  On a [time-scored scenario](#time-scored-scenarios) whose PB can be
  measured by pace, the threshold line draws at the score that finishes at
  that percentage of the PB's pace, `C − (C − PB) × 100 / goal` for the
  scenario's constant `C`: a PB of 896.2 at 95% and a constant of 1,000
  draws at 890.74, where the score form would draw at 851.39. A goal above
  100% puts the line above the PB. The annotation is unchanged and still
  shows a score
  ([2026-10-05][pace]).
  "Rank thresholds" draws the selected playlist's rank lines, in ladder
  order and color: the ranks whose thresholds land inside the plotted score
  range plus every rank tied at the nearest threshold below and at the
  nearest above, or the whole ladder with "Show all ranks" on. No playlist
  selected means no rank lines, and an empty threshold percentage skips the
  threshold line. The rank lines redraw at once when the Playlist filter
  changes
  ([2026-10-12][every-run]).
- Zooming the x axis refits the score axis to the runs in view: the run
  points inside the x window, padded by 5% of their span. The stars and the
  ring repeat run points, so they never change the fit. Overlay lines are not
  part of the fit, so a line beyond the fitted range is out of view while
  zoomed. A trace hidden from the legend is left out too, and showing or
  hiding one while zoomed refits. A window holding no runs leaves the score
  axis as it was. Double-clicking the plot, "Reset axes", "Autoscale", and
  any new figure (a rebuild or an appearance change) return both axes to the
  full autorange. Double-clicking the x axis alone also returns a refit score
  axis to its full autorange, but leaves a score range the user dragged
  themselves.
- Until the first data callback resolves, the chart is a transparent,
  annotation-free placeholder. A result with nothing to plot gets an explicit
  empty state instead
  ([2026-07-16][pre-hydration]):
  "No scenario selected" / "Select a scenario to see your score history.",
  "No local runs found" / "Play this scenario once and the graph will fill
  in.", and, in the two modes that count days, "No runs in this range" /
  "Choose a longer range or play more runs.". An unexpected mode value gets
  "Unsupported graph option" / "Choose <b>Score vs Run</b>, <b>Score vs
  Time</b>, or <b>Score vs Sensitivity</b>.". A control named in an
  empty-state message is bold through `<b>` in the annotation string
  ([2026-09-14][copy]).
- The figure takes the Mantine light or dark template with the app theme.
  With no point color chosen the run points draw in the template's own blue,
  `#228be6` light and `#1971c2` dark
  ([2026-08-20][points]
  as amended by
  [2026-08-21][default-color]).
  A New PB star is plotly's `star` symbol, gold `#fab005` with a 1px
  `#5f3d00` outline, the same in both themes
  ([2026-10-05][stars]).
- "Point size" is a Small | Default | Large preset (Small 4px, Large 10px).
  Default leaves the generated size untouched rather than writing a pixel
  count. It sizes the New PB stars too: 9px on Small, 16px on Large, and the
  12px they are generated with on Default
  ([2026-10-05][stars]).
  It sizes the ring as well, 14px, 18px, and 22px, wide enough to clear a
  star at the same setting.
  "Point color" accepts eight curated swatches on one row, a picker,
  or a typed hex value. The empty value means Default (placeholder
  "Default"), a "Use default" button is the only way back to it, and
  anything unparseable falls back to the generated color. The empty field's
  preview swatch shows the color the graph is using in the current theme
  ([2026-08-20][points]
  as amended by
  [2026-08-21][default-color]).
- Color restyles only the run trace, and size restyles the run trace, the
  New PB trace, and the ring. Each is selected by its trace name in a cheap
  presentation callback applied after theming: the expensive chart rebuild
  never reruns for an appearance change, and placeholder and empty figures
  pass through untouched, as does a figure with no New PB trace. Nothing else
  on the chart is customizable, the stars' own color and shape included, and
  that boundary is deliberate
  ([2026-08-20][points],
  with the stars' size as its one exception, set by
  [2026-10-05][stars]).
- The stars have no control. Clicking "New PB" in the legend hides them and
  leaves every run point, and the choice is not remembered: the figure sets
  no `uirevision`, so the next figure draws them again, whether it comes from
  a new run on the scenario, a control that rebuilds the chart, or an
  appearance change
  ([2026-10-05][stars]).
- The chart keeps plotly.js's default modebar, which offers "Download plot as
  a PNG", a save to this PC, and "Share chart...". Pressing "Share chart..."
  opens plotly.js's confirmation naming Plotly Cloud, and nothing is sent
  before its Share button. Share opens Plotly Cloud in a new browser tab and
  hands that tab the figure only once Plotly Cloud reports the user signed in
  there. A blocked popup ends the flow with nothing sent. The figure is
  everything plotted: the title, each plotted run's timestamp, score,
  accuracy, sensitivity, and x value, the setting a converted run was
  recorded at, the New PB stars and the ring, which repeat the position and
  score of runs already in it, and the label and value of each overlay line
  drawn. Neither the button nor the flow is app code: the graph passes no
  `config`, so both are plotly.js 4 defaults, kept on purpose.
  The Aim Training Journey graph passes no `config` either and carries the
  same toolbar and flow. Its figure is the playlist lines, their dates and
  progress percentages, and the aim-training-hours checkpoint labels
  ([2026-09-12][share]).

## The run list

- The list is a second column to the right of the chart, 500px wide and
  always shown. It lists the selected scenario's runs on two levels:
  sessions, newest first, and under each the scenario's runs in that session,
  newest first. Only sessions that hold a run of the scenario are listed,
  with one exception: the newest session is always the first row, in progress
  or not, even when the scenario was not played in it
  ([2026-10-12][column]).
- Its heading line reads `{scenario} · {n} runs`, or `1 run`, where `{n}`
  counts every run of the scenario in the run store, the figure Scenario
  Stats shows as Number of runs. Under it are the "Expand all" button and the
  "Columns" menu.
- A session row is named by when the session started: `Oct 4, 9:45 PM`, or
  `Dec 30, 2025, 9:45 PM` in an earlier year. Its right side reads how many
  of the session's runs were on this scenario, such as `7 of 47 runs` or
  `1 of 1 run`. The first row's right side also gives the session's length,
  as `1 hr 6 min · 7 of 47 runs`, and carries an "In progress" badge while
  its session is in progress. Hovering the length reads "The length runs from
  the first run to the last run. It doesn't count the time since your last
  run." With the selected scenario not played in the first row's session, the
  row reads `0 of 47 runs` and, opened, "Not played in this session"
  ([2026-10-12][column]).
- The first row stays in view under the column headers while the list
  scrolls.
- A run row has seven columns: `#`, the run's number among this scenario's
  runs in its session, counted in the order they were played, "Time", a time
  of day with no seconds, "Score", the marks, "Accuracy" to the whole
  percent, "Shots Fired", and "Sensitivity". The marks column has no visible
  header, and its accessible name is "Marks". Shots Fired is shown on every
  scenario and counts the shots of the first weapon the stats file lists.
  Sensitivity is the run's normalized sensitivity-and-scale string, as on the
  chart's axis. Columns don't sort
  ([2026-10-12][column]).
- A divider marks where the scenario was left and returned to within a
  session, and counts what was played between: `10 runs on 3 other
  scenarios`, or `1 run on 1 other scenario`.
- A date header names the date of any listed run that is not on the date its
  session started: `Oct 12`, or `Jan 1, 2027` in another year than this one.
  A run's date is the date it ended on. Where any of a session's runs of the
  scenario has another date than the session's start, each date among those
  runs gets a header, the start date included. Two cases have one date among
  the listed runs and still get its header: a scenario played only after
  midnight in a session that started before it, and a single run that started
  before midnight and ended after it. Where a header and a divider fall
  between the same two runs, the divider comes first.
- A session row opens and closes on a click, with no request to the server.
  "Expand all" opens every loaded session and reads "Collapse all" once they
  are all open. On arrival the first row is open and the rest are closed, and
  which rows are open is never remembered.
- The "Columns" menu shows or hides Shots Fired and Sensitivity, both shown
  to start, and the browser remembers each choice
  ([2026-10-05][columns-menu]).
- The list loads 30 sessions. A "Show older sessions" button at its end adds
  30 more. A change of scenario keeps the number loaded, and a reload starts
  from 30 again.
- The list is rebuilt from the run store, never from a batch of new runs,
  when a run lands on any scenario, when the selected scenario changes, when
  the Score threshold percentage changes, when older sessions are asked for,
  when the date moves on, and when the newest session stops being in
  progress. So its "In progress" badge clears within 30 seconds of the
  session ending, with no run landing
  ([sessions.md](sessions.md#in-progress)).
- A run that lands shows as a new row with nothing lost: opened rows stay
  open, and keyboard focus stays on the same run. The first row opens for it,
  once per run, whatever scenario it is on, so a row the player closed is not
  reopened by a later change of scenario. With Follow on, the list scrolls
  back to the top.
- The row of the last run played, on any scenario, is highlighted. It is in
  the list only while the selected scenario is the one that run was on, so
  the highlight follows the selection and not the chart's range: the row is
  highlighted where the range leaves the run's point, and its ring, off the
  chart. The highlight is a look alone and tells a screen reader nothing.
- With no run in the store the list reads "No runs yet", and with runs and
  no scenario selected it reads "No scenario selected". A selected scenario
  with no local runs lists the newest session alone, under the heading
  `{scenario} · 0 runs`.
- The list is the grid the app's other tables use, in its free edition, made
  to read as a list of sessions: a session row is a full-width row drawn by
  the app's own script, and opening a session is a filter over the rows. The
  rows reach the grid as data, never as Dash components
  ([2026-10-12][grid]).
- On a session row, Enter and Space open or close it, Right opens it, and
  Left closes it. A key that changes a row writes "Expanded" or "Collapsed"
  to a live region, and so does "Expand all". The row holds a button whose
  accessible name is "Session", which Tab reaches. The grid's accessible name
  is `Runs of {scenario}, by session`. What NVDA says of the list, and what
  still does not work well, is recorded in
  [run_history_list_nvda_walk.md](../research/run_history_list_nvda_walk.md)
  ([2026-10-12][grid]).
- The grid draws only the rows in view, so a browser's find-in-page reaches
  only those.

## Marks: the check and the star

- Two facts about a run are drawn beside its score in the run list, and
  worded as the latest-run card's badge. A check says the run met the score
  threshold. A star says the run was a
  [new PB](../glossary.md#new-pb), by the rule the chart's stars use, and a
  run can carry both. The check's hover and accessible name are "Threshold
  passed", and the star's are "New PB"
  ([2026-10-12][check]).
- A run is judged against the PB it was chasing: the scenario's best score
  before it, at any sensitivity
  ([2026-07-08][previous-pb]).
  So a later PB removes no check: a check means "passed when it was played".
  The chart's threshold line is drawn at the current PB, so an old run can
  carry a check and sit below today's line
  ([2026-10-12][check]).
- The percentage is the Score threshold percentage as it is set now, for
  every run. A change to it marks every run again, at once, because the
  percentage in force when an old run was played was never recorded. It lives
  only in the browser, so checks are per browser. The field sends its value
  on Enter or on losing focus, never per keystroke, and the threshold line
  moves with it
  ([2026-10-12][check]).
- No switch gates a mark. An empty percentage is the one way to turn checks
  off, and it removes no star
  ([2026-10-12][check]).
- Three kinds of run are not judged: every run while the percentage is
  empty, a scenario's first run and the first run at a new sensitivity, and a
  run compared by score whose PB before it was zero or less. A star never
  depends on the threshold: the first run at a new sensitivity can be a new
  PB and carry one. A run with no verdict has no check, and neither does a
  judged run that missed. The cell's hover and accessible text give the one
  reason that applies, the first that fits in that order: "Not judged. No
  score threshold percentage is set.", "Not judged. A scenario's first run,
  and the first run at a new sensitivity, aren't judged against the score
  threshold.", "Not judged. Your personal best before this run was zero or
  less, so there is no percentage to judge by.", or, for a judged miss,
  "Below threshold"
  ([2026-10-12][check]).
- A past run is judged by pace under its own version of the scenario, the
  one its stats file names in `Hash:`, where the app measures pace on that
  version. Whether a version is time-scored, and its constant, is one answer
  for the whole version, taken from the newest performance file of that
  version that can answer. The comparison is by pace only when the PB the run
  was chasing was set on the same version and both times are positive.
  Otherwise it is by score, as it is for a run whose file names no version
  and where no performance file of its version can answer. So a run on a
  later version changes no earlier check. New evidence about a run's own
  version can: the first performance file of a version that can answer turns
  that version's earlier runs to pace, and a later file of the same version
  that answers differently judges every run of that version again
  ([2026-10-12][check]).
- The run toast judges a landed run against the run store's high score when
  the run lands. The check and the card's badge judge it against the PB
  before the run in the order the runs were played. The two differ only for a
  run that lands older than the store's newest, such as a stats file copied
  into the folder.

## Time-scored scenarios

- A time-scored scenario scores the time left on a clock that counts down
  from a constant when the task is done, so a score of `s` took `C − s`
  seconds. Wherever the app can measure pace on one, these surfaces divide
  times instead of scores: the Next Rank gap
  ([playlists.md](playlists.md#the-per-playlist-scenario-table)), the Score
  threshold line (The chart), the threshold verdict and the New personal
  best toast ([notifications.md](notifications.md#run-notifications)), and
  the check and the latest-run card's badge and percentage
  ([Marks](#marks-the-check-and-the-star)).
  Anything that orders or places scores is unchanged, because a higher score
  is always a faster finish: the chart's points and axis, the PB score line,
  the rank lines, the Rank column, and top-N placement. No completion time is
  shown anywhere
  ([2026-10-05][pace]).
- Pace applies to a comparison only when three things hold: the scenario is
  recognized as time-scored, every score in the comparison is eligible, and
  both times are positive. Otherwise the surface behaves exactly as it does
  on any other scenario, with its own `N/A` and unjudged rules. A
  time-scored PB of zero or less still gets a pace percentage, because only
  the times have to be positive
  ([2026-10-05][pace]).
- A scenario is recognized from a performance file, the file KovaaK's writes
  beside each run's stats file. The file is time-scored when it has at least
  two score events and, after every one, the running score is within 0.5 of
  `time_limit − timescale × timestamp`. Then the constant is the file's
  `time_limit`, and the scenario version is its `scenario_hash`. Any other
  file that can answer says the scenario is not time-scored. A file can't
  answer when its bytes do not parse, when its `schema_version` is not 1, or
  when its header lacks a scenario hash, or a time limit or a timescale
  that is a positive, finite number. A run paused partway through is
  recognized like any other, because the file's timestamps leave paused
  time out
  ([2026-10-05][pace]).
- For the surfaces that judge the scenario as it stands, the scenario's
  newest run names the version. That run and the older runs with the same
  stats-file `Hash:` are tried newest first, and the first whose performance
  file can answer decides. A file that can't be read or can't answer is
  skipped. A file that answers "not time-scored" decides, and no older file
  is read. The app can't tell, and every surface keeps its score math, when
  no file of that version can answer, when none of the scenario's runs has a
  performance file, when the newest run has no `Hash:`, or when the stats
  folder has no `performances` folder beside it. A scenario's first run on a
  game build that writes these files therefore turns it to pace, and its
  numbers move then
  ([2026-10-05][pace]).
  A past run's check is the exception: it is judged under the run's own
  version ([Marks](#marks-the-check-and-the-star)).
- A score is eligible for a pace comparison only when its run's `Hash:`
  equals the deciding file's `scenario_hash`. A rank threshold counts as
  eligible. A run whose stats file has no `Hash:` still loads, and its score
  is never eligible. So a PB set on an older version of the scenario keeps
  the score math, on the table and the chart, until a run on the current
  version beats it
  ([2026-10-05][pace]).
- A run's performance file is found by name: the stats file's name with
  ` Stats.csv` replaced by ` Performance.perf`, in the `performances` folder
  beside the stats folder
  ([settings.md](settings.md#restart-scope-and-pinning)). Startup lists that
  folder once and parses nothing. A run that lands adds its file to the
  listing, so the table and the chart see the file the watchdog judged the
  run by, with no restart. A file is parsed only when a surface asks about
  its scenario, and its answer is remembered by file name for the life of
  the process. A file that can't be read is not remembered, so the next look
  tries again. A missing, unreadable, or malformed performance file costs
  only the detection, never the run
  ([2026-10-05][pace]).
  The first time a file is parsed, the debug log records its answer. For a
  file that can answer, the line also carries its time limit, its score
  event count, and its largest distance from the countdown.

## Chart options panel

- The panel is an in-flow column beside the chart, between the chart and the
  run list, disclosed by the "Chart options" button in the chart's header. It
  starts closed on every visit, its open state is never persisted, and
  collapsing hides the controls with `display: none` while keeping them
  mounted and feeding their callbacks
  ([2026-08-09][panel]).
  When the chart's own area, the page less the navbar and the run list,
  drops to 48em, the same panel stacks above the chart
  ([2026-10-12][column]).
- Four groups in order: **Overlays** ("Rank thresholds" on, "Show all ranks"
  off, "PB score" on), **Run Data Points** ("Point size" Default, "Point
  color" empty), **Score Threshold** ("Score threshold overlay" on, "Score
  threshold percentage" 95, minimum 1, placeholder "Percentage", "Score
  threshold verdict" on), and **Notifications** ("Run notifications" on)
  ([2026-08-09][panel],
  [2026-08-20][points],
  [2026-08-21][master-switch];
  label casing as amended by [2026-09-14][copy]).
  A help text that names another control renders the name bold: "Needs
  **Rank thresholds** turned on." and "Needs **Run notifications** turned
  on."
  ([2026-09-14][copy]).
- The Score threshold percentage help text reads the same on every scenario:
  "Sets the score goal as a percentage of your personal best. On a scenario
  scored by completion time, it's a percentage of your personal best's pace
  instead, when the app can measure pace reliably. Otherwise, it stays a
  percentage of your score. The overlay line tracks your current personal
  best. A run is judged against the personal best you had before the run."
  ([2026-10-05][pace];
  the last sentence as set by
  [2026-10-12][check]).
- Every control in the panel persists via Dash persistence in the browser's
  local storage, so preferences are per browser and per origin, which is why
  every human-facing URL says `localhost`
  ([2026-08-09][localhost]).
- What the two notification switches gate, the run-toast family, the verdict
  sub-toggle, and their interaction, is specified in
  [notifications.md](notifications.md#run-notifications). This page only
  hosts them. Neither gates a check, a star, or the card.

## Scenario Stats

- The block shows "Last played:", "Number of runs:", and "Position:" for the
  selected scenario. The personal best appears on the chart as the PB score
  overlay, not as a stats row.
- "Last played" is a relative, single-unit humanized string ("5 minutes
  ago"), self-updating on its own 30-second interval
  ([2026-06-21][last-played]).
  Its empty states are explicit: `—` with no scenario selected, `Never` for
  a scenario with no local runs, and only a real timestamp gets the tooltip
  affordance: hover, keyboard focus, or touch
  ([2026-06-30][empty-states]).
  The tooltip shows the absolute timestamp without seconds, in the shared
  GitHub-shaped format whose JS and Python implementations are kept in sync
  by hand
  ([2026-07-11][timestamps]).
- The Position field, its inline hints, and its Refresh button are fully
  specified in [scenario_rank.md](scenario_rank.md#failure-handling). On
  interval ticks the field re-reads caches only and makes no network calls
  ([2026-07-01][score-aware]).

## Run delivery

- The app shell drains the run-event deque, on its own interval and on every
  page, and publishes one batch per tick. This page's `forward_run_events`
  consumes that batch store as its only `Input` and writes two stores in one
  answer: a summary of the batch for the scenario the page shows, which is
  the scenario last played when the Follow switch is on, and the id of the
  batch's newest run, written for every batch. The Follow switch and the
  scenario dropdown are `State` there, so flipping either forwards nothing on
  its own. The supported usage model is one active tab
  ([2026-07-06][coalesce]).
  The drain semantics and the toasts the summary produces are specified in
  [notifications.md](notifications.md#run-notifications).
- One callback writes both dropdowns' values, with plain outputs. It reads
  the summary and lands on the scenario just played when Follow is on,
  clearing a Playlist filter that does not list it, and it is the callback
  that applies a link's parameters and the card's scenario button
  ([2026-10-12][clear-filter]).
  With Follow off the page stays on the selected scenario.
- The chart rebuild consumes the summary, so a batch of several runs becomes
  one rebuild and one change of scenario rather than a replay
  ([2026-07-06][coalesce]).
  Its other rebuild triggers are a scenario change, the Playlist filter, the
  chart mode, the two ranges, the date moving on, and any Chart options
  control that feeds it
  ([2026-10-12][every-run]).
- The run list, the latest-run card, the scenario dropdown's list, and the
  check for a session in progress take the second store, so each is brought
  up to date for a run on any scenario, once per batch.
- The page polls on `polling_interval` (default 1000 ms) for two callbacks:
  the run-import failure flush and the rank read. The shell's drain is a
  third poll, on its own interval, and it runs on every page. Waitress's 8
  worker threads absorb the burst, and both intervals keep ticking while the
  tab is hidden
  ([2026-07-17][threads]).
- Two background queues reach the screen here and on [Home](home.md),
  whichever of the two is open: run-import failures on the next poll tick,
  and the startup playlist warnings on a one-shot interval 250 ms after
  mount. The page that is open empties the queue
  ([2026-10-12][address]).
  Both toast families are specified in
  [notifications.md](notifications.md#background-threads-and-diagnostics).

## Narrow windows

- Both rules measure the page's own boxes and never the window, because the
  navbar takes 225px without changing the window's width
  ([2026-08-03][content-area]).
- When the page area is 900px or narrower, the run list goes above the chart
  at up to 600px tall, and the page scrolls. The order is then the top row,
  the list, and the chart
  ([2026-10-12][column]).
- Chart options sits beside the chart only while the chart's own area is
  wider than 48em. At that width or less it stacks above the chart, with its
  groups side by side
  ([2026-10-12][column]).
- There is no phone design. At phone width the list scrolls sideways
  ([2026-10-12][column]).

## What the page keeps and forgets

- Runs are files: every run is a CSV in the stats directory, the in-memory
  stores are rebuilt from them at startup, and every view on this page is
  therefore recomputable at any time: the chart, the run list, the marks, and
  the card
  ([2026-08-08][rank-history]).
- Leaderboard positions are not history: only the latest position per
  scenario is cached, past positions are overwritten and cannot be
  reconstructed, and capture stays unbuilt until a position-over-time
  feature is designed, whose first deliverable must be that capture
  ([2026-08-08][rank-history]).
- The browser remembers the Playlist filter, the Selected scenario, the
  Follow switch, the chart mode, the two ranges, the Chart options controls,
  and the Columns menu's two checkboxes, each under the control's own id. It
  does not remember whether Chart options is open, which session rows are
  open, or how many sessions are loaded
  ([2026-10-12][own-ids]).
- The chart-appearance and notification preferences live only in the
  browser's local storage. Nothing the panel sets is written server-side
  ([2026-08-20][points]).
- Nothing about a mark is stored. A check and a star are worked out again
  each time something asks, from the runs, the percentage, and what the
  performance files say now
  ([2026-10-12][check]).

## Setup surfaces

- With no runs to read, the page says why in place, above its top row. It
  shows the stats-folder hint, and the setup card's two yellow states, "Your
  settings can't be read" and "Finish setting up". Each reads and looks as
  it does on Home, where [home.md](home.md#setup-surfaces) specifies them.
  The card here has no Skip and never offers the account: that state is
  Home's alone
  ([2026-10-12][address]).
- The chart, the run list, and the card keep their ordinary empty states
  beneath them.

[name]: ../decision_log/2026/2026-10-12-the-chart-page-is-named-run-history.md
[address]: ../decision_log/2026/2026-10-12-run-history-has-its-own-address-and-the-landing-address-is-home.md
[column]: ../decision_log/2026/2026-10-12-the-run-list-is-a-second-column-beside-the-chart.md
[grid]: ../decision_log/2026/2026-10-12-the-run-list-is-built-on-ag-grid-community-and-nvda-is-run-on-the-built-list.md
[every-run]: ../decision_log/2026/2026-10-12-the-run-history-chart-plots-every-run-and-draws-no-summary-line.md
[stars-run]: ../decision_log/2026/2026-10-12-score-vs-run-stars-each-new-pb.md
[clear-filter]: ../decision_log/2026/2026-10-12-follow-and-a-scenario-link-clear-a-playlist-filter-that-does-not-list-the-scenario.md
[check]: ../decision_log/2026/2026-10-12-a-past-runs-check-is-judged-against-the-pb-it-was-chasing-under-its-own-version.md
[own-ids]: ../decision_log/2026/2026-10-12-run-history-keeps-its-own-control-ids-so-every-browser-saw-the-defaults-once.md
[nearest-minute]: ../decision_log/2026/2026-10-13-a-measured-time-rounds-to-the-nearest-minute.md
[naming]: ../decision_log/2026/2026-08-09-the-graph-page-is-scenario-performance-its-panel-is-chart-options.md
[panel]: ../decision_log/2026/2026-08-09-chart-options-live-in-a-collapsible-panel-beside-the-graph.md
[localhost]: ../decision_log/2026/2026-08-09-human-facing-urls-say-localhost-machine-probes-stay-on-127001.md
[copy]: ../decision_log/2026/2026-09-14-app-copy-follows-one-set-of-rules-and-the-em-dash-is-gated-out.md
[one-word]: ../decision_log/2026/2026-07-06-one-word-per-concept-in-leaderboard-verbiage.md
[query]: ../decision_log/2026/2026-09-19-a-query-parameter-selects-a-control-it-does-not-suspend-its-memory.md
[hidden-filter]: ../decision_log/2026/2026-10-12-the-playlist-filter-lists-the-hidden-playlist-it-holds.md
[highlight]: ../decision_log/2026/2026-10-12-opening-a-scenario-performance-dropdown-highlights-its-name.md
[content-area]: ../decision_log/2026/2026-08-03-homes-controls-row-measures-the-content-area-not-the-window.md
[local-list]: ../decision_log/2026/2026-09-12-the-local-scenario-list-comes-from-the-run-store.md
[stars]: ../decision_log/2026/2026-10-05-the-score-vs-time-chart-marks-each-new-pb-with-a-star.md
[pace]: ../decision_log/2026/2026-10-05-time-scored-scenarios-are-measured-by-pace.md
[normalize]: ../decision_log/2026/2026-09-11-sensitivities-normalize-to-cm360-at-parse-time-from-the-files-own-increment-and-dpi.md
[precision]: ../decision_log/2026/2026-09-27-sensitivity-precision-is-fixed-per-scale-and-its-config-knob-is-retired.md
[recorded]: ../decision_log/2026/2026-09-26-a-converted-run-keeps-the-setting-it-was-recorded-at-for-display-only.md
[timestamps]: ../decision_log/2026/2026-07-11-humanize-the-absolute-timestamp-format.md
[previous-pb]: ../decision_log/2026/2026-07-08-judge-score-threshold-notifications-against-the-previous-pb.md
[pre-hydration]: ../decision_log/2026/2026-07-16-keep-pre-hydration-states-honest.md
[points]: ../decision_log/2026/2026-08-20-run-points-get-a-size-preset-and-a-color-and-the-chart-stops-there.md
[default-color]: ../decision_log/2026/2026-08-21-the-empty-point-color-is-called-default-and-the-points-follow-the-theme.md
[master-switch]: ../decision_log/2026/2026-08-21-run-notifications-have-a-master-switch-and-the-threshold-switch-is-renamed.md
[share]: ../decision_log/2026/2026-09-12-charts-keep-plotlyjs-4s-share-chart-button.md
[columns-menu]: ../decision_log/2026/2026-10-05-a-columns-menu-shows-and-hides-table-columns-and-kovaaks-ids-are-optional-ones.md
[last-played]: ../decision_log/2026/2026-06-21-relative-humanized-last-played-timestamps.md
[empty-states]: ../decision_log/2026/2026-06-30-model-home-last-played-empty-states-explicitly.md
[score-aware]: ../decision_log/2026/2026-07-01-keep-scenario-rank-consistent-with-score-aware-refreshes.md
[coalesce]: ../decision_log/2026/2026-07-06-coalesce-pending-home-run-events.md
[threads]: ../decision_log/2026/2026-07-17-absorb-poll-tick-bursts-with-threads-not-visibility-gating.md
[rank-history]: ../decision_log/2026/2026-08-08-rank-history-capture-is-deferred-until-a-position-over-time-feature-is-designed.md
