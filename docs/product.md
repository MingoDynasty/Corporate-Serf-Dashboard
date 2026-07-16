# Product Overview

What the app does and *why* — the user problem behind each feature. This is
the durable companion to [`roadmap.md`](./roadmap.md) (which sequences what's
next and trims itself as work ships) and [`decision_log.md`](./decision_log.md)
(which records *technical* decisions). When a feature ships, its user-facing
rationale lands here so it survives the deletion of the proposal that designed
it (see AGENTS.md "Shipping a proposal").

## The user and the questions

One user, one machine: a KovaaK's aim-training enthusiast who generates
dozens of runs per session and wants that data to direct their training
instead of piling up unread. Everything in the app serves three questions:

> *Am I improving? Where am I weak? What should I work on next?*

The overriding principle: **answer the question, don't just show the data.**
Charts and numbers are means; the user wants conclusions. (Full principles
list in the roadmap.)

## What the app does today

### The core loop: watch, plot, notify

- **Automatic run capture.** The app watches the KovaaK's stats directory and
  ingests every finished run as it lands; the plots follow what you're
  playing without manual imports. *Problem solved:* manual tracking
  (spreadsheets, screenshots) dies because logging a run after every play is
  friction — here the act of playing *is* the act of logging.
- **Sensitivity vs score and score-over-time plots.** Per-scenario plots with
  runs grouped by sensitivity. *Problem solved:* "is my current sensitivity
  actually better?" and "am I trending up on this scenario?" are answered
  visually instead of by gut feel.
- **Run notifications.** When a new run lands, a toast reports it. Two
  conditional classifications: a top-N placement within the run's sensitivity
  ("40.2 cm/360 has a new 2nd place score"), shown when the run makes the
  configured top N for the on-screen scenario; and a score-threshold
  pass/fail against the run's previous high score ("ready to move on" vs
  "keep grinding"), shown when the threshold notification switch is on and a
  previous high score exists. The overlay line for that same percentage tracks
  the current personal best. A run that qualifies for neither still gets a
  generic "Graph updated!" toast. A new personal best has no toast of its
  own; it triggers the background rank refresh. If runs accumulate while Home
  is not open, the next visit rebuilds once from final state and gives one
  scenario-named summary instead of replaying stale toasts and selections.
  *Problem solved:* immediate in-session feedback on whether the run you just
  played met your bar, without a noisy catch-up sequence after time away.
- **Rank overlays.** Benchmark rank thresholds drawn onto the plots.
  *Problem solved:* a raw score is meaningless without context; the overlay
  shows which rank band a score sits in and how far the next band is.

### Standing: where do I rank

- **Scenario rank and percentile** (PRs #8–#10). The home page shows your
  global leaderboard standing for the selected scenario —
  `Position: 11,290 of 63,892 (82.33% Percentile)`. It's read from a local cache
  (one-week TTL) and refetched when a selection finds it stale, after a new
  personal best, or on manual Refresh — not fetched live on every view. *Problem solved:* raw scores aren't comparable
  across scenarios, but percentile is; it turns "804.2" into "top 18%," which
  is the number a player actually reasons with.
- **Score-aware rank refreshes** (PRs #38, #40). After a new personal best,
  the app polls the leaderboard in a bounded backoff (five attempts over
  about a minute) waiting for it to catch up, never regressing the display.
  If the leaderboard still lags when the attempts are exhausted, the cached
  value stays put and the manual Refresh button is the authoritative escape
  hatch. *Problem solved:* trust — a rank display that lags your own PB for
  a week undermines the whole feature.

### Planning: what should I train

- **Playlist-level overview** (PRs #78, #83). A sortable table at `/playlists`,
  one row per imported playlist with coverage, runs, last-played, and
  aggregate-percentile stats; each row drills into that playlist's scenario
  table. *Problem solved:* the scenario table answers "where am I weak *within*
  a playlist," but not "*which* playlist deserves attention" — this surfaces
  stale and weak playlists at a glance and directs training focus across
  playlists, the way the scenario table already does within one.
- **Playlist show/hide** (PR #87). Per-playlist Hide/Unhide on the
  overview, a "Show hidden" toggle for managing hidden ones, and hiding
  filters every playlist dropdown (Home filter, Journey picker). Hidden
  playlists stay loaded — routes and rank overlays keep working. *Problem
  solved:* focus — dropdowns and the overview show only the playlists you
  care about, which is what makes shipping the full benchmark library
  tolerable.
- **Bundled benchmark library** (PR #90; expanded by the 2026-07-11 curation
  import). Every importer-generated benchmark (216 files) ships with the app
  and loads at startup; Voltaic and Viscose are visible by default and the
  rest wait behind "Show hidden" on the Playlists page. *Problem solved:* enabling a benchmark used to mean
  manually copying a JSON file and restarting — now it's one unhide click,
  and app updates refresh the whole library automatically.
- **Playlist scenarios overview** (PRs #12, #15, #16, plus progressive fill in
  this PR). A sortable table of
  every scenario in a playlist — rank, total, percentile, last played, runs,
  high score, PB cm/360, PB accuracy. Long playlists scroll inside the table so
  the column labels remain visible while scanning deep rows. The local and
  cached parts paint immediately; unresolved leaderboard cells animate and
  stream into place with a counter instead of hiding the table behind a
  minutes-long spinner. *Problem solved:* the headline use case is *"show me
  the scenarios where I'm worst, sorted ascending — that's my training
  priority list."* It also surfaces scenarios gone stale, and remains usable
  while KovaaK's is slow or unreachable. A session-planning tool, checked at
  the start of a training session.
- **Relative "last played" timestamps** (PRs #17, #19, #23). "5 minutes ago"
  / "3 months ago" everywhere a timestamp appears, exact time on hover.
  *Problem solved:* staleness is the actual question ("how long since I
  touched this?"); absolute dates make the user do the math.
- **Aim Training Journey page** (work in progress, currently unlinked from
  the navbar). Visualizes training-hour checkpoints across playlists.

### Getting data in

- **Playlist import via sharecode** (Playlists overview page, PR #92;
  previously the Home Settings modal). *Problem solved:* onboarding a playlist
  takes one code paste, not hand-building a scenario list. Lives on the
  playlist management surface, where the imported playlist lands as a new
  visible row; a duplicate-code refusal whose playlist is hidden points the
  user at the "Show hidden" toggle. The only part of the app that requires an
  internet connection besides rank lookups.
- **Playlist delete & superseded-copy cleanup** (Playlists overview page, PR
  #98). A per-row Delete on user playlists removes the `data/playlists/` file
  after confirmation (bundled benchmarks offer Hide instead — a share-code
  re-import would come back rank-less); a one-click cleanup clears user files
  left dead by the bundled library flip. *Problem solved:* the user prunes
  playlists and stale copies in the app — with a confirmation guard and no
  filesystem surgery — instead of hunting down JSON files by hand.
- **Code-based playlist identity** (PR #67). Playlist
  codes, not names, identify imported and bundled playlists; duplicate names
  stay visible with disambiguated labels, and imports are stored under
  `data/playlists/`. *Problem solved:* same-named playlists no longer
  silently overwrite each other in memory or on disk, and user imports no
  longer live in the committed bundled-playlist root.
- **Benchmark importer** (`scripts/benchmark_importer/`, PRs #45–#48). Merges
  Evxl playlist resolution with KovaaK's rank thresholds into reviewable
  benchmark files under `resources/benchmarks/`. *Problem solved:*
  rank overlays need threshold data that no single public API provides; the
  importer builds it reproducibly, with provenance, instead of by hand.

## Where it's going

Sequencing and design state live in the [roadmap](./roadmap.md). The unsolved
user problems (each becomes a roadmap milestone when it's next up):

- *"Is my current training working?"* — a per-scenario improving /
  plateauing / declining verdict, not just a plot to squint at.
- *"How close am I to the next rank?"* — "+47 to Gold" as a motivational
  target on benchmark scenarios.
- *"How did the rest of this session go?"* — a reviewable run history; the
  per-run toast is ephemeral and the console log is a developer-facing
  stopgap.

## Maintaining this doc

Update the feature inventory in the PR that ships a feature (step in the
AGENTS.md shipping checklist). One or two sentences per feature on the
*problem it solves*; design details belong in the decision log and
architecture doc, not here. If a feature is removed or its purpose changes,
edit the entry — this doc describes the present, git history keeps the past.
