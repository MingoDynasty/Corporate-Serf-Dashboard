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
  pass/fail against the previous high score ("ready to move on" vs "keep
  grinding"), shown when the threshold notification switch is on and a
  previous high score exists. A run that qualifies for neither still gets a
  generic "Graph updated!" toast. A new personal best has no toast of its
  own; it triggers the background rank refresh. *Problem solved:* immediate
  in-session feedback on whether the run you just played met your bar.
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

- **Playlist scenarios overview** (PRs #12, #15, #16). A sortable table of
  every scenario in a playlist — rank, total, percentile, last played, runs,
  high score, PB cm/360, PB accuracy. *Problem solved:* the headline use case
  is *"show me the scenarios where I'm worst, sorted ascending — that's my
  training priority list."* It also surfaces scenarios gone stale. A
  session-planning tool, checked at the start of a training session.
- **Relative "last played" timestamps** (PRs #17, #19, #23). "5 minutes ago"
  / "3 months ago" everywhere a timestamp appears, exact time on hover.
  *Problem solved:* staleness is the actual question ("how long since I
  touched this?"); absolute dates make the user do the math.
- **Aim Training Journey page** (work in progress, currently unlinked from
  the navbar). Visualizes training-hour checkpoints across playlists.

### Getting data in

- **Playlist import via sharecode** (Settings modal). *Problem solved:*
  onboarding a playlist takes one code paste, not hand-building a scenario
  list. The only part of the app that requires an internet connection besides
  rank lookups.
- **Benchmark importer** (`scripts/benchmark_importer/`, PRs #45–#48). Merges
  Evxl playlist resolution with KovaaK's rank thresholds into reviewable
  benchmark files under `resources/playlists/generated/`. *Problem solved:*
  rank overlays need threshold data that no single public API provides; the
  importer builds it reproducibly, with provenance, instead of by hand.

## Where it's going

**Next up: the playlist-level overview** — the same "direct my attention"
logic, one level above the scenario table. As the user put it: if Playlist A
hasn't been played in over a year, it's worth revisiting to measure new
skills against old scores; if Playlist B shows a low average or median
percentile, that's a weakness worth targeted work. At a glance, the app
should tell the player where to focus across *playlists*, the way the
scenario table already does within one. Sequencing and design state live in
the [roadmap](./roadmap.md).

Behind it, the unsolved user problems (each becomes a roadmap milestone when
it's next up):

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
