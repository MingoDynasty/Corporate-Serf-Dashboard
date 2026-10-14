# Home

Home is the page the app opens on. It shows the stats-folder hint and the
setup card when either applies, and one line that says how many runs the app
found in the stats folder. It reads no link parameter and lists no links,
because the navbar already leads to every page. It stands in for an Overview
page that is planned and not yet designed.

Statements below describe what the app does today and link the
[decision log](../decision_log/README.md) entries that set them. Rationale
lives in those entries, not here. A statement with no link is an
implementation fact that no decision-log entry governs. Runtime structure is
mapped in [architecture.md](../architecture.md), and the user-facing
rationale in [product.md](../product.md).

## Identity

- The page is registered at `/`, with `/home` and `/index` redirecting to
  it. Its name is "Home": the navbar link, the page `name`, and the
  browser-tab title
  ([2026-10-12][address]).
- The navbar's first entry and the header title both lead to it. The
  launcher opens `/`, so each start of the app lands here
  ([2026-10-12][address]).
- The navbar marks its Home link on this page and on no other. The rule
  that marks a link on the pages under its address does not make every page
  Home's, although every address begins with `/`
  ([2026-10-13][navbar-mark]). The rule is stated in
  [run_history.md](run_history.md#identity).
- The page reads no query parameter. A link of the shape `/?scenario=...` or
  `/?playlist_code=...&scenario=...`, which once opened a scenario on the
  page that lived at this address, draws Home and selects nothing. Nothing
  forwards it to [Run History](run_history.md)
  ([2026-10-12][address]).
- With `show_version_in_title` enabled, the tab title is prefixed with the
  build's release label. The key is specified in
  [settings.md](settings.md#the-configuration-file).

## What the page shows

- Top to bottom: the stats-folder hint and the setup card when they apply,
  then one line of stats
  ([2026-10-12][address]).
- The stats line counts the runs and the scenarios in the run store: "Found
  {runs} runs across {scenarios} scenarios in your stats folder.", with `1
  run` and `1 scenario` where a count is one. A count takes thousands
  separators. With a usable stats folder that holds no runs it reads "No runs
  found in your stats folder yet. Play a scenario in KovaaK's and your runs
  will appear in Run History."
  ([2026-10-12][address]).
- The line is drawn only while the app has a usable stats folder. Without
  one the hint or the card already says why the app has no runs
  ([2026-10-12][address]).
- The counts are the run store's as the page is drawn, and the line does not
  tick: a run that lands shows in it on the next load
  ([2026-10-12][address]).
- The page lists no links to the app's other pages. The only links on it are
  the hint's and the card's, to Settings
  ([2026-10-12][address]).

## Setup surfaces

- The setup card renders above the stats line, one state at a time. The
  unusable-store state shows "Your settings can't be read" over "A settings
  file exists, but this version of the app can't use it, so the app started
  without your settings. Open Settings to see what's wrong and how to fix
  it.", with "Open Settings" as its one action
  ([2026-08-11][schema-stamp]).
  The stats-folder state shows "Finish setting up" over "No KovaaK's stats
  folder was found, so this app can't read your runs yet. Set it in
  Settings." with "Open Settings" as its one action. The identity state
  shows "Add your KovaaK's account" over "See your leaderboard position and
  percentiles for every scenario.", with "Open Settings", "Skip", and the
  fine print "Skipping keeps position lookups off. You can add your username
  anytime in Settings."
  ([2026-08-11][fresh-install];
  card copy as amended by [2026-09-14][copy]).
  The card is a panel wearing the shared alert treatment rather than a
  `dmc.Alert`, because it holds a link and a button: the unusable-store and
  stats-folder states are yellow with a warning icon beside the title, and the
  identity state blue with an info icon ([2026-08-30][severity]).
  When the card shows, which state wins, and what Skip writes are specified
  in [settings.md](settings.md#the-setup-card).
- The stats-folder hint sits above the setup card and reads "No stats
  folder configured. Set it in Settings." with Settings linked and the period
  outside the link ([2026-09-14][copy]), or
  "Restart the app to apply your saved settings." while a saved directory
  awaits a restart. Its key-presence semantics are specified in
  [settings.md](settings.md#the-setup-card)
  ([2026-08-11][fresh-install]).
- Both branches of the hint are a yellow panel wearing the same alert
  treatment as the card, with the warning icon beside the sentence, no title
  above it, and the card's width. A sentence too long for one line wraps
  beside the icon rather than under it
  ([2026-09-15][notice-anatomy]).
- The hint and the card can render together, hint first: a stored stats
  folder that has since vanished beside a username key that was never
  written leaves the yellow hint above the blue account offer, each speaking
  for its own key
  ([2026-09-15][notice-anatomy]).
- The identity state, the blue account offer with Skip, is this page's alone.
  [Run History](run_history.md#setup-surfaces) shows the hint and the card's
  two yellow states, so a page with no runs to read says why in place, and
  never the account offer
  ([2026-10-12][address]).

## Queued notices

- Two background queues reach the screen here and on Run History, whichever
  of the two is open: run-import failures on the next poll tick, and the
  startup playlist warnings on a one-shot interval 250 ms after mount. The
  page that is open empties the queue. So a warning raised at startup shows
  on the page the launcher opens
  ([2026-10-12][address]).
  Both toast families are specified in
  [notifications.md](notifications.md#background-threads-and-diagnostics).
- The page polls on `polling_interval` (default 1000 ms) for one callback,
  the run-import failure flush. The shell's drain of new runs is a second
  poll, on its own interval, and it runs on every page.

## What the page keeps and forgets

- The page has no control the browser remembers, and stores nothing.

[address]: ../decision_log/2026/2026-10-12-run-history-has-its-own-address-and-the-landing-address-is-home.md
[navbar-mark]: ../decision_log/2026/2026-10-13-the-navbar-marks-the-open-page.md
[schema-stamp]: ../decision_log/2026/2026-08-11-durable-json-stores-carry-a-schema_version-stamp.md
[fresh-install]: ../decision_log/2026/2026-08-11-a-fresh-install-is-asked-once-on-a-card-keyed-to-key-absence.md
[copy]: ../decision_log/2026/2026-09-14-app-copy-follows-one-set-of-rules-and-the-em-dash-is-gated-out.md
[severity]: ../decision_log/2026/2026-08-30-one-severity-color-language-for-inline-notices.md
[notice-anatomy]: ../decision_log/2026/2026-09-15-setup-hints-wear-the-notice-anatomy.md
