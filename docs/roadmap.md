# Corporate Serf Dashboard — Product Roadmap

## Vision

Help aim training enthusiasts understand and direct their improvement by
turning raw run data into actionable insight about *where they stand*, *where
they're going*, and *where to focus*.

The dashboard already captures every run. This roadmap is about turning that
data into answers to the questions players actually ask themselves:

> *Am I improving? Where am I weak? What should I work on next?*

This roadmap is intentionally short-horizon. It focuses on what's next and
keeps farther-out work as brief mentions until they're up next. The durable
"what does the app do and why" record — including the rationale for features
after they ship and leave this file — lives in
[`product.md`](./product.md).

---

## Shipped

Design rationale for shipped work lives in
[`decision_log.md`](./decision_log.md); runtime structure in
[`architecture.md`](./architecture.md).

- **Scenario rank lookup** — current rank fetched from the live leaderboard,
  with Steam ID identity matching, background refresh on new high scores, and
  thread-safe cache I/O. (PR #8)
- **Leaderboard total and percentile** — display extends to
  `Position: 11,290 of 63,892 (82.33% Percentile)` using KovaaK's midpoint
  formula. (PRs #9, #10)
- **Playlist scenarios overview** (was milestone 1) — sortable per-playlist
  table at `/playlists/{playlistCode}`: rank, total, percentile, last played,
  runs, high score, and PB cm/360 + accuracy for every scenario in the
  playlist. Long playlists use grid-owned scrolling so their column headers
  remain visible. (PRs #12, #15, #16, on retry groundwork from #11)
- **Relative "last played" timestamps** — humanized staleness display with
  exact-time tooltips, live-ticking on home and the playlist grid.
  (PRs #17, #19, #23)
- **Score-aware rank refreshes** — bounded post-PB polling until the
  leaderboard catches up, monotonic cache writes, manual Refresh escape
  hatch. (PRs #38, #40)
- **Benchmark importer** — script that resolves playlists via Evxl and rank
  thresholds via KovaaK's into reviewable generated benchmark files with
  provenance stamps. (PRs #45–#48)
- **Playlist code identity and user-root imports** — playlists are keyed by
  KovaaK's share code, duplicate names are preserved with disambiguated
  labels, duplicate codes warn visibly, and imported playlists live under
  `data/playlists/`. This shipped the enabling identity work for the
  playlist-level overview. (PR #67)
- **Playlist-level overview and stats** — a sortable overview at `/playlists`,
  one row per imported playlist with coverage, runs, last-played, and
  aggregate-percentile stats; any row drills into that playlist's scenario
  table. Surfaces stale and weak playlists at a glance to direct attention
  across playlists. Completing this milestone also removed the transitional
  per-playlist selector. (PRs #78, #83)
- **Playlist management & benchmark library** — the overview became the single
  playlist-management surface: per-code show/hide filtering every dropdown, the
  full importer-generated benchmark library shipped flat under
  `resources/benchmarks/` with Voltaic + Viscose visible by default, and
  overview-hosted import, delete (user playlists only), and cleanup of user
  files superseded by bundled benchmarks. The whole library ships with the app
  without flooding dropdowns, and playlists are managed in the app instead of
  by copying files. (PRs #87, #90, #92, and this PR) Design rationale distilled
  into [`decision_log.md`](./decision_log.md).

---

## Upcoming milestones

Nothing is actively in progress right now. The sequenced next candidate is
**Run history and sessions** (see Future); it will be promoted here with a
full entry when work on it starts.

---

## Future (briefly)

Listed so they aren't forgotten, but not yet actively planned. Each will be
expanded into its own roadmap entry when it becomes the next thing up.

- **Score trend verdict** — *improving / plateauing / declining* classification
  per scenario, answering "is my current training working?" Likely shipped
  against raw score data first; richer rank-trend analysis would need rank
  history infrastructure that doesn't yet exist.
- **Next-rank threshold for benchmark playlists** — "+47 to Gold" motivational
  target on benchmark scenarios. External tools (e.g. evxl.app) already
  provide a substitute, so this is consolidation rather than net-new
  capability.
- **Aim Training Journey page polish** — the page already exists at
  `/aim-training-journey` (currently marked work-in-progress). It visualizes
  training-hour checkpoints across playlists, which is a different question
  from the shipped playlist-level overview — so it remains a separate
  concern to revisit later, not a replacement for it.
- **Run history and sessions** — a reviewable, persistent record of past runs
  that the ephemeral per-run toast can't provide: the current cross-scenario
  training session, and a scenario's full history over time (e.g. cold-start
  vs warmed-up comparisons). Gap-based *sessions* are a later quality-of-life
  layer on top. Sequenced after the playlist-level overview milestone;
  supersedes the interim console-log stopgap in `file_watchdog.py`. See
  [`run_history_proposal.md`](./run_history_proposal.md).
- **Scenarios page** — scenario-first navigation for scenarios that live in
  several playlists or in none, parked from the playlist-overview design. The
  overview → scenario table → Home drill chain covers playlist-first
  navigation; this would answer "show me this scenario regardless of
  playlist."

---

## Guiding principles

- **Answer the question, don't just show the data.** Charts and numbers are
  means; the user wants conclusions.
- **Compose, don't replicate.** Each milestone reuses the rank, percentile,
  threshold, and trend logic from earlier milestones rather than introducing
  parallel mechanisms.
- **Defer breadth for depth.** Each milestone delivers a complete
  user-facing capability before the next one starts. Half-built features
  across the dashboard are worse than one fully realized one.
- **Prioritize by frequency of use.** Daily-use features come before
  occasional-insight features, even when the latter are cheaper to build.
- **Plan one horizon deep.** Detail what's next; keep the further-out work as
  brief mentions until it's the next thing up.
