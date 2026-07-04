# UI/UX Audit

An end-to-end audit of the dashboard UI: every page was exercised in a live
run (Chromium, light + dark themes, desktop 1600px and mobile 390px viewports)
against a synthetic stats directory of ~220 runs across 5 scenarios, including
live watchdog updates (new CSVs written while the page was open). Findings are
ordered by severity within each section. This is a point-in-time review doc;
per repo convention, distill whatever ships into `decision_log.md` and delete
this file.

## P0 — the app does not start

`source/kovaaks/api_service.py` contained three Python-2-style exception
clauses (`except TypeError, ValueError:`) at lines 99, 102, 266 and 888. This
is a `SyntaxError` on every Python 3 version: `python source/app.py` dies at
import time, pytest cannot collect, and `ruff check` reports E999. Fixed in
this branch by parenthesizing the tuples. With the fix, all 199 tests and
`ruff check` pass.

Takeaway beyond the fix itself: nothing in the merge bar ran before this
landed on main. A minimal CI workflow (ruff format/check + pytest) would have
caught it — worth the ~20 lines of GitHub Actions YAML even for a solo
project.

## Navigation & information architecture

1. **Aim Training Journey is unreachable.** The page exists at
   `/aim-training-journey` but `app_shell.py` only renders nav links for Home
   and Playlists. Users can only find it by knowing the URL. Add a nav link
   (it can carry a "WIP" badge) or gate the page registration behind a config
   flag until it ships.
2. **The nav is hidden by default on desktop.** `AppShell.navbar.collapsed`
   is `True` for both mobile and desktop, so a first-time user sees only a
   burger icon; the existence of a Playlists section is invisible. With two
   (really three) destinations, an always-visible desktop navbar — or top-level
   header tabs — costs little space and makes the app self-describing.
3. **`/playlists` is a dead-end hop.** The page is just a select plus the
   sentence "Select a playlist to view its scenarios." — an extra click on the
   way to `/playlists/<code>`. Either render the playlist list itself (cards or
   a table: name, scenario count, has-rank-data, last played) or skip the page
   and put the selector on the scenarios page (which already has one).
4. **No cross-linking between the two main views.** The playlist scenarios
   grid and the home plot don't reference each other: clicking a scenario row
   should navigate to Home with that scenario (and playlist filter) selected.
   Today users retype the scenario name into the Home dropdown. This is the
   single highest-leverage navigation improvement.
5. **404 page is bare.** "404 - Page not found" with no link back Home. Minor.

## Home page

1. **Empty states are meaningless axes.** Before a scenario is selected — and
   whenever "Top N scores" or the date picker is cleared — the graph area
   renders an empty Plotly figure with axes running −1…6 / −1…4. It reads as
   "broken", not "waiting for input". Return a figure with an annotation
   ("Select a scenario to see your runs", "Enter a Top N value") and hidden
   axes, or hide the graph behind a placeholder panel.
2. **Unconfigured rank lookups raise a red error toast on every scenario
   change.** With `kovaaks_username` unset (the out-of-box state), selecting
   any scenario pops "Error: KovaaK's username is not configured." — and the
   toast does not auto-close (the `dash_extensions` handler path sets
   `autoClose: 8000`, but the toasts persisted through subsequent renders in
   testing; they also stack duplicates). An unset optional feature is not a
   user error: show "Rank: —" with a tooltip/link "set kovaaks_username in
   config.toml to enable", emit the notice once per session at most, and hide
   the Refresh button when the feature is off.
3. **Notification copy leads with the sensitivity, not the scenario.** New
   top-N toast reads "32.0 Overwatch has a new 1st place score: 145.00". The
   subject should be the scenario ("New 1st-place score on VT Pasu Rasp
   Intermediate: 145.00 @ 32.0 Overwatch"). "Notification" as a title is
   filler — "New high score" carries information.
4. **"Top N scores" is unexplained.** It actually means "keep the best N runs
   per sensitivity/date bucket", which is impossible to infer from the label.
   Add a help tooltip. Same for the interaction between "Playlist filter" and
   the rank overlay (rank lines only appear when the selected playlist carries
   rank data — nothing communicates this).
5. **Scenario dropdown options go stale.** Options are built at page load (or
   playlist change). If a scenario is played for the first time mid-session,
   the auto-switch callback sets the dropdown to a value that isn't in its
   options list, and the new scenario can't be re-picked without a reload.
   Refresh the options list when a new-scenario message arrives.
6. **Plot title duplicates chrome.** "VT Pasu Rasp Intermediate (updated:
   2026-07-04 02:55:43 AM)" — the scenario name is already in the dropdown,
   and the updated-timestamp is developer telemetry. If freshness matters,
   a small dimmed "Updated 3s ago" caption outside the figure is calmer.
7. **Average line in Score-vs-Time zigzags through the scatter.** Averages are
   per exact-bucket and connected, producing a sawtooth that obscures the
   trend. Consider a daily mean or rolling average, and render it visually
   distinct (thicker, muted color) from run points.
8. **Layout is assembled with spacer hacks.** Stacked `dmc.Space(h="xl")`
   pairs align the controls row; at intermediate widths (e.g. with the navbar
   open) the Scenario Stats block re-wraps to unpredictable positions. Use a
   single `dmc.Group`/`SimpleGrid` with `align="end"` and let the stats block
   be its own row/card. The x-axis `RadioGroup` has no visible group label
   ("X-axis"); a `SegmentedControl` above the graph would be more idiomatic
   for a two-way view toggle.
9. **Settings modal mixes concerns and hides a primary action.** "Import
   Playlist" is data management, not a display setting, and it's buried in a
   modal labeled Settings; meanwhile the settings users must edit most
   (stats_dir, kovaaks_username) are not in the UI at all (config.toml only).
   Short term: move Import next to the Playlist filter, and surface the
   configured username (read-only) under Settings so rank features are
   discoverable. The import flow also lacks: a loading state on the button
   (KovaaK's API calls retry up to ~30s while the UI sits inert), the failure
   toast discards the specific `error_message` the service returns, and the
   input isn't cleared on success.
10. **Date filter is floor-only.** "Oldest date to consider" can't express
    "last 30 days" (it's a fixed date, so it rots) or a date *range*. A
    range picker with presets (7/30/90 days, all time) fits how aim trainers
    actually review progress.

## Playlist scenarios page

1. **All-N/A ranks with no explanation.** With no `kovaaks_username`, every
   rank column shows N/A silently. One dimmed status line ("Rank columns need
   kovaaks_username in config.toml") would prevent the "is it broken?" moment.
2. **No text filter.** Benchmarks have 15–60 scenarios; AG Grid's
   `quickFilterText` is a one-prop win.
3. **No row → plot link** (see Navigation #4).
4. **No aggregate row/summary.** Benchmark users think in terms of "overall
   rank / energy"; a footer with counts (played 12/18, ranked 9/18) or a
   summary card would make the page a real progress view rather than a data
   dump. (Larger feature: see Missing features #2.)
5. The grid itself is in good shape: NULLS-LAST sorting, relative "Last
   Played" with absolute-time tooltips, Mantine-matched quartz theming in both
   color schemes — nice work.

## Aim Training Journey page

- Unreachable (above), marked WIP via a hardcoded `#ff6b6b` alert (use a
  Mantine color token), empty-figure axes on load, "Checkpoint Hour" is
  unexplained, and warnings fire per playlist with insufficient data. If it's
  not ready, keep it unregistered; if it is, add the nav link and an intro
  sentence explaining what "percentage" means on the y-axis.

## Feedback & notifications

- **Toast pile-up.** During normal play (new CSV every ~60s), each run
  produces one or two toasts, errors persist, and duplicates stack — after a
  session the corner is a wall of stale notifications (observed while
  simulating live runs). Deduplicate by using stable notification ids
  per category (Mantine `action: "update"`), auto-close everything, and
  reserve red for actual failures.
- **"Graph updated!" adds no information** — the user can see the graph
  update; the plot title even re-stamps. Drop it or make it a subtle inline
  "Updated Xs ago".

## Theming, responsiveness, offline

1. **Mobile is broken.** At 390px the h1 wraps to three lines and overflows
   the fixed `4em` header onto the controls; the selects' `miw=400` forces
   horizontal scroll. If mobile matters (glancing at your phone between runs),
   cap the title size responsively, let the header grow or truncate, and drop
   the min-widths (`w="100%"` inside a Stack). If it doesn't matter, say so in
   the README — but the header overflow is worth fixing regardless because it
   also bites at narrow desktop windows.
2. **Icons require the Iconify CDN at runtime.** Every `DashIconify` icon is
   fetched from api.iconify.design (with fallbacks to api.unisvg.com /
   api.simplesvg.com). Offline — the README's stated normal mode ("only
   playlist import requires internet") — every icon renders as an empty box,
   including the theme toggle, which becomes an unlabeled blank button.
   Bundle the ~15 used icons as local SVGs in `assets/`.
3. **Dark mode is otherwise solid** — plots re-theme via the cached-figure
   store without a refetch, the AG Grid CSS variables track the Mantine
   scheme, and the pre-hydration script prevents a flash. The stored default
   is light regardless of OS preference; honoring `prefers-color-scheme` on
   first visit would be a nice touch.

## Accessibility

- **Nested anchors in the navbar.** `nav_link` wraps `dmc.NavLink` (which
  renders its own `<a>`) inside `dcc.Link` (another `<a>`): invalid HTML,
  double tab-stops per nav item. Render `dmc.NavLink` with `href=` and Dash
  Pages' client-side navigation, or use `dmc.Anchor` styling.
- **Burger has no `aria-label`** ("Open navigation"). The color-scheme toggle
  does have one (from DMC) — good.
- **Heading order jumps h1 → h6** ("Scenario Stats" is `Title order=6` for
  its visual size; use `order=2` + `size` override).
- **`<html lang>` is unset** (Dash default `index_string` is already
  customized in `app_shell.py`, so adding `lang="en"` is a one-word change).

## Missing features users would expect (prioritized)

1. **Scenario click-through from the playlist grid** — turns the two pages
   into one workflow (low effort, high value).
2. **Benchmark progress summary** — per-playlist overall rank/points and
   next-rank deltas ("need +32 on Smoothbot for Platinum"). The rank
   thresholds are already in the playlist JSON; this is the core value prop
   of benchmark files and currently only visible as plot overlay lines.
3. **Recent-runs view** — a small table of the last N runs (score, accuracy,
   sens, when) beside/below the plot; the data is already in `run_database`.
   Today accuracy exists only inside hover tooltips.
4. **Session stats** — runs today, time trained today/this week (the journey
   page hints at this ambition; a simple stat row on Home is 80% of the value).
5. **First-run experience** — the app requires hand-editing a TOML before
   first launch, and the two settings that unlock features (stats_dir,
   kovaaks_username) are invisible in the UI. Even read-only display of the
   active config with "edit config.toml to change" guidance would cut setup
   confusion; a writable settings form is the real fix.
6. **Playlist management** — imported playlists can't be renamed, removed, or
   distinguished from bundled benchmark playlists in the pickers.
7. **Sensitivity-comparison aids** — the sensitivity view is the app's
   namesake; run-count per sens bucket (confidence), or a box/violin option,
   would make "which sens is actually better" answerable.
8. **Export/share** — Plotly's camera icon covers images, but exporting the
   filtered runs as CSV is cheap and fits the power-user audience.

## Polish nits

- `example.toml`'s `stats_dir = "Change me!"` guarantees a first-run failure
  mode; consider detecting the default Steam path or failing with a clearer
  message.
- Percentile copy: "(2.47% Percentile)" → "Top 2.5%".
- The Settings gear button already has text "Settings"; its tooltip repeating
  "Settings" is noise.
- Discord/GitHub header icons have tooltips but open in the same tab
  (`target` unset on both anchors), navigating away from a live dashboard —
  use `target="_blank"`.
- 1s `dcc.Interval` polling fires two callbacks/second/tab even when idle;
  fine locally, but the interval could back off when the tab is hidden
  (`dcc.Interval.disabled` via a visibility clientside callback).
