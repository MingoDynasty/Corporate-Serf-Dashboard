# Scenario Performance

The landing page plots the kept runs of one scenario as points over
sensitivity or time, with the personal best, a configurable score goal, and
playlist rank thresholds available as overlay lines; older runs recorded on a
game's own sensitivity scale sit on the same cm/360 axis as everything else.
A collapsible Chart options panel tunes how the chart looks and which run
notifications fire, and the browser remembers every control on the page — the
chosen playlist and scenario included, so returning to the page shows the
selection you last made, whether you picked it in the dropdowns or arrived
from a playlist link. A newly played run reaches the chart automatically once
its file is imported, and the page can follow the scenario just played. The
page also hosts the setup surfaces that point you at Settings, whether
something has never been set or saved settings cannot be read.

Statements below describe what the app does today and link the
[decision log](../decision_log.md) entries that set them — rationale lives in
those entries, not here. A statement with no link is an implementation fact
that no decision-log entry governs. Runtime structure is mapped in
[architecture.md](../architecture.md), the user-facing rationale in
[product.md](../product.md). The Aim Training Journey page
(`/aim-training-journey`, reachable by URL only) is work in progress and out
of scope here, apart from its chart toolbar, noted under The graph.

## Identity

- The page is registered at `/`, with `/home` and `/index` redirecting to it.
  Its product name is "Scenario Performance" — the navbar link, the page
  `name`, and the browser-tab title — applied as labels only; the module and
  route keep their historical names
  ([2026-08-09](../decision_log.md#2026-08-09-the-graph-page-is-scenario-performance-its-panel-is-chart-options)).
- The preference panel and its disclosure button are named "Chart options",
  and the controls inside carry the vocabulary the app's own chart
  annotations and the aim-training community already use — "PB score",
  "Score threshold" — rather than invented terms
  ([2026-08-09](../decision_log.md#2026-08-09-the-graph-page-is-scenario-performance-its-panel-is-chart-options)).
  Control labels, placeholders, tooltips, and toast titles are sentence case;
  the page title, the group headings, and the named chart modes "Score vs
  Sensitivity" and "Score vs Time" keep their capitals
  ([2026-09-14](../decision_log.md#2026-09-14-app-copy-follows-one-set-of-rules-and-the-em-dash-is-gated-out)).
- Page copy says "Position" for leaderboard placement and reserves "Rank"
  for benchmark tiers, as in the "Rank thresholds" overlay; the rule lives in
  [scenario_rank.md](scenario_rank.md)
  ([2026-07-06](../decision_log.md#2026-07-06-one-word-per-concept-in-leaderboard-verbiage)).
- With `show_version_in_title` enabled, the tab title is prefixed with the
  build's release label; the key is specified in
  [settings.md](settings.md#the-configuration-file).
- `?scenario=` and `?playlist_code=` query parameters select the dropdowns,
  and the selection they make is remembered exactly like one made by hand:
  arriving from a Playlists grid scenario link and then returning to the page
  shows that playlist and scenario, not an earlier one
  ([2026-09-19](../decision_log.md#2026-09-19-a-query-parameter-selects-a-control-it-does-not-suspend-its-memory)).
  A parameter the URL omits leaves its control on the remembered value, so
  `?scenario=` alone keeps the playlist filter — and a scenario that filter
  does not list is then dropped, leaving no scenario selected and nothing
  remembered. An unknown playlist code clears the filter. The parameters are applied on every load of that URL, so
  reloading a deep link re-applies it over a later choice, and the re-applied
  selection becomes the remembered one. The navbar link and the header title
  lead to the page without parameters, where a reload changes nothing.

## The controls row

- The row holds, in order: the "Playlist filter" select, the "Selected
  scenario" searchable select (placeholder "Select a scenario"), the
  "Follow newly played scenario" switch beneath it, the "Top N scores"
  number input (default `5`, minimum 1), the "Oldest date to consider" date
  picker (defaults to January 1 of the current year; no future dates), and
  the Scenario Stats block. A second column carries the "Score vs
  Sensitivity" / "Score vs Time" radio (default Score vs Sensitivity) and
  the "Chart options" button. Every control in the row persists in the
  browser, the two dropdowns included. The follow switch and the Top N
  input carry help tooltips; the other row controls have plain labels.
- The follow switch sits under the scenario selector, not in the panel: it
  governs selection, not presentation
  ([2026-08-09](../decision_log.md#2026-08-09-chart-options-live-in-a-collapsible-panel-beside-the-graph)).
- The row's responsive rules measure the content area rather than the
  window, and the two wide dropdowns narrow from their 400px target toward a
  200px floor before the row wraps
  ([2026-08-03](../decision_log.md#2026-08-03-homes-controls-row-measures-the-content-area-not-the-window)).
- The scenario list comes from the selected playlist when one is chosen, and
  otherwise from the scenarios with at least one run loaded from the stats
  directory, named by each file's own `Scenario:` field
  ([2026-09-12](../decision_log.md#2026-09-12-the-local-scenario-list-comes-from-the-run-store));
  without a usable stats directory that local fallback is empty, while a
  selected playlist still lists its scenarios.

## The graph

- Both modes plot each kept run as a point, legend "Run data point", with
  one "Average score" line (hover label "Average score")
  through each group's average score: Score vs Sensitivity groups by the
  run's sensitivity-and-scale string, Score vs Time by calendar day. Within the date range, the top N
  scores are kept per sensitivity, or per day in Score vs Time. The date
  range is inclusive of the selected date; the plot title reads
  `{scenario} (updated: {timestamp})`.
- A run recorded under a game's own sensitivity scale is normalized to cm/360
  when its file is parsed, from the file's own `Sens Increment` and `DPI`
  fields, by `cm/360 = 360 x 2.54 / (0.07 x increment x DPI)` rounded to
  `sens_round_decimal_places`; a run whose file lacks either field, or carries
  one the conversion cannot use, keeps its recorded value and scale. Every consumer reads the normalized fields, so the
  normalized sensitivity-and-scale group is the unit for grouping, for run
  placement, and for first-sensitivity detection
  ([2026-09-11](../decision_log.md#2026-09-11-sensitivities-normalize-to-cm360-at-parse-time-from-the-files-own-increment-and-dpi)).
- Point hover shows the run's timestamp with seconds kept — the one surface
  that keeps them, cross-referencing KovaaK's second-stamped CSV filenames —
  plus score, the x value, and accuracy
  ([2026-07-11](../decision_log.md#2026-07-11-humanize-the-absolute-timestamp-format)).
- Three overlay families, all dashed labelled lines. "PB score ({value})"
  and "Score threshold ({value})" draw at the current post-run personal best
  and at the
  configured percentage of it — while the verdict in run notifications
  judges against the PB the run was chasing
  ([2026-07-08](../decision_log.md#2026-07-08-judge-score-threshold-notifications-against-the-previous-pb)).
  "Rank thresholds" draws the selected playlist's rank lines, in ladder
  order and color: the ranks whose thresholds land inside the plotted score
  range plus every rank tied at the nearest threshold below and at the
  nearest above, or the whole ladder with
  "Show all ranks" on. No playlist selected means no rank lines; an empty
  threshold percentage skips the threshold line. The playlist selection is
  read only when the graph rebuilds — switching playlists alone triggers no
  rebuild, so when the selected scenario survives the switch the drawn rank
  lines lag the selection until the next rebuild (a control change, a
  scenario change, or a new run).
- Zooming the x axis refits the score axis to the runs in view: the run
  points and Average Score line inside the x window, padded by 5% of their
  span. Overlay lines are not part of the fit, so a line beyond the fitted
  range is out of view while zoomed. A trace hidden from the legend is left
  out too, and showing or hiding one while zoomed refits. A window holding no
  runs leaves the score axis as it was. Double-clicking the plot, "Reset
  axes", "Autoscale", and any new figure (a rebuild or an appearance change)
  return both axes to the full autorange. Double-clicking the x axis alone
  also returns a refit score axis to its full autorange, but leaves a score
  range the user dragged themselves.
- Until the first data callback resolves, the chart is a transparent,
  annotation-free placeholder; a resolved-but-empty result gets an explicit
  empty state instead
  ([2026-07-16](../decision_log.md#2026-07-16-keep-pre-hydration-states-honest)):
  "No scenario selected" / "Select a scenario to see your score history.",
  "Graph settings incomplete" / "Set <b>Top N scores</b> and the oldest date
  to plot this scenario.", "No local runs found" / "Play this scenario once
  and the graph will fill in.", and "No runs in this date range" / "Choose an
  older date or play more runs."; an unexpected mode value gets "Unsupported
  graph option" / "Choose <b>Score vs Sensitivity</b> or <b>Score vs
  Time</b>.". A control named in an empty-state message is bold through
  `<b>` in the annotation string
  ([2026-09-14](../decision_log.md#2026-09-14-app-copy-follows-one-set-of-rules-and-the-em-dash-is-gated-out)).
- The figure takes the Mantine light or dark template with the app theme.
  With no point color chosen the run points draw in the template's own blue —
  `#228be6` light, `#1971c2` dark — while the Average score line keeps its
  baked `#636efa` in both themes
  ([2026-08-20](../decision_log.md#2026-08-20-run-points-get-a-size-preset-and-a-color-and-the-chart-stops-there)
  as amended by
  [2026-08-21](../decision_log.md#2026-08-21-the-empty-point-color-is-called-default-and-the-points-follow-the-theme)).
- "Point size" is a Small | Default | Large preset (Small 4px, Large 10px);
  Default leaves the generated size untouched rather than writing a pixel
  count. "Point color" accepts eight curated swatches on one row, a picker,
  or a typed hex value; the empty value means Default (placeholder
  "Default"), a "Use default" button is the only way back to it, and
  anything unparseable falls back to the generated color. The empty field's
  preview swatch shows the color the graph is using in the current theme
  ([2026-08-20](../decision_log.md#2026-08-20-run-points-get-a-size-preset-and-a-color-and-the-chart-stops-there)
  as amended by
  [2026-08-21](../decision_log.md#2026-08-21-the-empty-point-color-is-called-default-and-the-points-follow-the-theme)).
- Size and color restyle only the run trace, selected by its "Run Data
  Point" name, in a cheap presentation callback applied after theming — the
  expensive graph rebuild never reruns for an appearance change, and
  placeholder and empty figures pass through untouched. Nothing else on the
  chart is customizable, and that boundary is deliberate
  ([2026-08-20](../decision_log.md#2026-08-20-run-points-get-a-size-preset-and-a-color-and-the-chart-stops-there)).
- The chart keeps plotly.js's default modebar, which offers "Download plot as
  a PNG", a save to this PC, and "Share chart...". Pressing "Share chart..."
  opens plotly.js's confirmation naming Plotly Cloud, and nothing is sent
  before its Share button. Share opens Plotly Cloud in a new browser tab and
  hands that tab the figure only once Plotly Cloud reports the user signed in
  there; a blocked popup ends the flow with nothing sent. The figure is
  everything plotted: the title, each plotted run's timestamp, score,
  accuracy, and x value, the Average score line, and the label and value of
  each overlay line drawn. Neither the button nor the flow is app code: the
  graph passes no `config`, so both are plotly.js 4 defaults, kept on purpose.
  The Aim Training Journey graph passes no `config` either and carries the
  same toolbar and flow; its figure is the playlist lines, their dates and
  progress percentages, and the aim-training-hours checkpoint labels
  ([2026-09-12](../decision_log.md#2026-09-12-charts-keep-plotlyjs-4s-share-chart-button)).

## Chart options panel

- The panel is an in-flow column beside the chart, disclosed by the "Chart
  options" button; it starts closed on every visit, its open state is never
  persisted, and collapsing hides the controls with `display: none` while
  keeping them mounted and feeding their callbacks. When the chart row's own
  width — not the window's — drops to 62em, the same panel stacks above the
  chart
  ([2026-08-09](../decision_log.md#2026-08-09-chart-options-live-in-a-collapsible-panel-beside-the-graph)).
- Four groups in order: **Overlays** ("Rank thresholds" on, "Show all ranks"
  off, "PB score" on), **Run Data Points** ("Point size" Default, "Point
  color" empty), **Score Threshold** ("Score threshold overlay" on, "Score
  threshold percentage" 95, minimum 1, placeholder "Percentage", "Score
  threshold verdict" on), and **Notifications** ("Run notifications" on)
  ([2026-08-09](../decision_log.md#2026-08-09-chart-options-live-in-a-collapsible-panel-beside-the-graph),
  [2026-08-20](../decision_log.md#2026-08-20-run-points-get-a-size-preset-and-a-color-and-the-chart-stops-there),
  [2026-08-21](../decision_log.md#2026-08-21-run-notifications-have-a-master-switch-and-the-threshold-switch-is-renamed);
  label casing as amended by [2026-09-14](../decision_log.md#2026-09-14-app-copy-follows-one-set-of-rules-and-the-em-dash-is-gated-out)).
  A help text that names another control renders the name bold: "Needs
  **Rank thresholds** turned on.", "Needs **Run notifications** turned on.",
  and the Top N scores help's "or per day in **Score vs Time**"
  ([2026-09-14](../decision_log.md#2026-09-14-app-copy-follows-one-set-of-rules-and-the-em-dash-is-gated-out)).
- Every control in the panel persists via Dash persistence in the browser's
  local storage, so preferences are per browser and per origin — which is
  why every human-facing URL says `localhost`
  ([2026-08-09](../decision_log.md#2026-08-09-human-facing-urls-say-localhost-machine-probes-stay-on-127001)).
- What the two notification switches gate — the run-toast family, the
  verdict sub-toggle, and their interaction — is specified in
  [notifications.md](notifications.md#run-notifications); this page only
  hosts them.

## Scenario Stats

- The block shows "Last played:", "Number of runs:", and "Position:" for the
  selected scenario; the personal best appears on the chart as the PB score
  overlay, not as a stats row.
- "Last played" is a relative, single-unit humanized string ("5 minutes
  ago"), self-updating on its own 30-second interval
  ([2026-06-21](../decision_log.md#2026-06-21-relative-humanized-last-played-timestamps)).
  Its empty states are explicit: `—` with no scenario selected, `Never` for
  a scenario with no local runs, and only a real timestamp gets the tooltip
  affordance — hover, keyboard focus, or touch
  ([2026-06-30](../decision_log.md#2026-06-30-model-home-last-played-empty-states-explicitly)).
  The tooltip shows the absolute timestamp without seconds, in the shared
  GitHub-shaped format whose JS and Python implementations are kept in sync
  by hand
  ([2026-07-11](../decision_log.md#2026-07-11-humanize-the-absolute-timestamp-format)).
- The Position field, its inline hints, and its Refresh button are fully
  specified in [scenario_rank.md](scenario_rank.md#failure-handling); on
  interval ticks the field re-reads caches only and makes no network calls
  ([2026-07-01](../decision_log.md#2026-07-01-keep-scenario-rank-consistent-with-score-aware-refreshes)).

## Run delivery

- The page no longer drains the run-event deque. The app shell does, on its
  own interval and on every page, and publishes one batch per tick; this
  page's `check_for_new_data` consumes that batch store as its only `Input`,
  lands on the most recently played scenario when the follow switch is on, and
  changes the dropdown at most once. The follow switch and the scenario
  dropdown are `State` there, so flipping either forwards nothing on its own.
  The supported usage model is one active tab
  ([2026-07-06](../decision_log.md#2026-07-06-coalesce-pending-home-run-events)).
  The drain semantics and the toasts the summary produces are specified in
  [notifications.md](notifications.md#run-notifications).
- The graph rebuild consumes the forwarded summary, so a batch of several runs
  becomes one rebuild and one auto-switch rather than a replay
  ([2026-07-06](../decision_log.md#2026-07-06-coalesce-pending-home-run-events)).
  Its other rebuild triggers are unchanged: any Chart options control that
  feeds it, a scenario change, and the date and axis controls.
- The page still polls on `polling_interval` (default 1000 ms), now for two
  callbacks rather than three: the run-import failure flush and the rank read.
  The shell's drain is the third poll, on its own interval, and it runs on
  every page. Waitress's 8 worker threads absorb the burst, and both intervals
  keep ticking while the tab is hidden
  ([2026-07-17](../decision_log.md#2026-07-17-absorb-poll-tick-bursts-with-threads-not-visibility-gating)).
- The page is also where two background queues reach the screen: run-import
  failures on the next poll tick, and the startup playlist warnings on a
  one-shot interval 250 ms after mount. Both toast families are specified in
  [notifications.md](notifications.md#background-threads-and-diagnostics).

## What the page keeps and forgets

- Runs are files: every run is a CSV in the stats directory, the in-memory
  stores are rebuilt from them at startup, and every score-over-sensitivity
  and score-over-time view is therefore recomputable at any time
  ([2026-08-08](../decision_log.md#2026-08-08-rank-history-capture-is-deferred-until-a-position-over-time-feature-is-designed)).
- Leaderboard positions are not history: only the latest position per
  scenario is cached, past positions are overwritten and cannot be
  reconstructed, and capture stays unbuilt until a position-over-time
  feature is designed — whose first deliverable must be that capture
  ([2026-08-08](../decision_log.md#2026-08-08-rank-history-capture-is-deferred-until-a-position-over-time-feature-is-designed)).
- The chart-appearance and notification preferences live only in the
  browser's local storage; nothing the panel sets is written server-side
  ([2026-08-20](../decision_log.md#2026-08-20-run-points-get-a-size-preset-and-a-color-and-the-chart-stops-there)).

## Hosted setup surfaces

- The setup card renders above the controls row, one state at a time. The
  unusable-store state shows "Your settings can't be read" over "A settings
  file exists, but this version of the app can't use it, so the app started
  without your settings. Open Settings to see what's wrong and how to fix
  it.", with "Open Settings" as its one action
  ([2026-08-11](../decision_log.md#2026-08-11-durable-json-stores-carry-a-schema_version-stamp)).
  The stats-folder state shows "Finish setting up" over "No KovaaK's stats
  folder was found, so this app can't read your runs yet. Set it in
  Settings." with "Open Settings" as its one action. The identity state
  shows "Add your KovaaK's account" over "See your leaderboard position and
  percentiles for every scenario.", with "Open Settings", "Skip", and the
  fine print "Skipping keeps position lookups off. You can add your username
  anytime in Settings."
  ([2026-08-11](../decision_log.md#2026-08-11-a-fresh-install-is-asked-once-on-a-card-keyed-to-key-absence);
  card copy as amended by [2026-09-14](../decision_log.md#2026-09-14-app-copy-follows-one-set-of-rules-and-the-em-dash-is-gated-out)).
  The card is a panel wearing the shared alert treatment rather than a
  `dmc.Alert`, because it holds a link and a button: the unusable-store and
  stats-folder states are yellow with a warning icon beside the title, and the
  identity state blue with an info icon ([2026-08-30](../decision_log.md#2026-08-30-one-severity-color-language-for-inline-notices)).
  When the card shows, which state wins, and what Skip writes are specified
  in [settings.md](settings.md#the-setup-card).
- The stats-folder hint sits above the setup card and reads "No stats
  folder configured. Set it in Settings." with Settings linked and the period
  outside the link ([2026-09-14](../decision_log.md#2026-09-14-app-copy-follows-one-set-of-rules-and-the-em-dash-is-gated-out)), or
  "Restart the app to apply your saved settings." while a saved directory
  awaits a restart. Its key-presence semantics are specified in
  [settings.md](settings.md#the-setup-card)
  ([2026-08-11](../decision_log.md#2026-08-11-a-fresh-install-is-asked-once-on-a-card-keyed-to-key-absence)).
- Both branches of the hint are a yellow panel wearing the same alert
  treatment as the card, with the warning icon beside the sentence, no title
  above it, and the card's width. A sentence too long for one line wraps
  beside the icon rather than under it
  ([2026-09-15](../decision_log.md#2026-09-15-setup-hints-wear-the-notice-anatomy)).
- The hint and the card can render together, hint first: a stored stats
  folder that has since vanished beside a username key that was never
  written leaves the yellow hint above the blue account offer, each speaking
  for its own key
  ([2026-09-15](../decision_log.md#2026-09-15-setup-hints-wear-the-notice-anatomy)).
