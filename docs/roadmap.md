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

## Shipped (recent)

The five most recently shipped milestones, newest first — older entries
leave this file entirely. Their user-facing rationale lives in
[`product.md`](./product.md), design rationale in
[`decision_log.md`](./decision_log.md), runtime structure in
[`architecture.md`](./architecture.md), and git history holds the full
sequence.

- **Notification system redesign** — the app is quiet during normal play. The
  wall of red error toasts about an unconfigured username is gone: persistent
  conditions now explain themselves in place, beside the value they affect,
  and passive navigation never interrupts. Each run produces at most one
  toast, whose title states the verdict — a threshold pass or miss, or the
  placement it earned — and playing again replaces it instead of stacking a
  second one beside it. The no-information "Graph updated!" toast is gone
  too. (PRs #194, #196, #198, #200; design in #82, #195) Design rationale
  distilled into [`decision_log.md`](./decision_log.md).
- **Settings detection** — the Settings page now offers what the machine
  already knows. The stats-folder box suggests every Steam library holding a
  KovaaK's stats folder, so a wrong first-start pick is a click to repair
  instead of a path dug out of Explorer by hand; a Detect button checks this
  machine's Steam accounts against KovaaK's and fills in the one it can prove
  is yours, offering a choice when it cannot prove exactly one. Detection only
  ever fills the form — Save is still what writes. (PRs #189, #191, #193;
  design in #186) Design rationale distilled into
  [`decision_log.md`](./decision_log.md).
- **Version display** — the Settings page now names the running build: the
  release tag, with the commit it came from underneath. A freshly updated app
  knows its own tag from its first session, because the installer and launcher
  leave a copy of the release description beside each installed version at
  download time. Checking whether an update landed, or quoting a version in a
  bug report, no longer means hovering the header's GitHub icon. (PRs #188,
  #190; design in #187) Design rationale distilled into
  [`decision_log.md`](./decision_log.md).
- **In-app settings** — the stats folder, KovaaK's username, and Steam ID moved
  out of the hand-edited `config.toml` into an app-owned store with a Settings
  page that edits all three. The app now starts and serves whatever its stats
  folder is doing — unset, moved, or missing — instead of exiting, installs ask
  no questions at all, and a start with nothing configured finds the KovaaK's
  stats folder itself. Configuring the dashboard no longer means opening a text
  editor. (PRs #181, #182, #183, #184; design in #171) Design rationale
  distilled into [`decision_log.md`](./decision_log.md).
- **Leaderboard-ID seeding** — the bundled benchmark corpus now embeds each
  scenario's KovaaK's leaderboard ID, and the app seeds them into the permanent
  name→ID mapping cache at startup. First opens of unfamiliar bundled playlists
  no longer fan out over the slow exact-name search endpoint, and ID resolution
  no longer needs a configured username. (PR #169) Design rationale distilled
  into [`decision_log.md`](./decision_log.md).

---

## Upcoming milestones

- **Run history and sessions** — a reviewable, persistent record of past runs
  that the ephemeral per-run toast can't provide: the current cross-scenario
  training session, and a scenario's full history over time (e.g. cold-start
  vs warmed-up comparisons). Gap-based *sessions* are a later
  quality-of-life layer on top; this supersedes the interim console-log
  stopgap in `file_watchdog.py`. Design in
  [`run_history_proposal.md`](./run_history_proposal.md).

The settings arc's guided first-run flow — a setup card for a fresh install,
and what "skip" should mean — was deliberately left out of settings detection
and still needs a proposal of its own before it can be sequenced.

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
- **Scenarios page** — scenario-first navigation for scenarios that live in
  several playlists or in none, parked from the playlist-overview design. The
  overview → scenario table → Home drill chain covers playlist-first
  navigation; this would answer "show me this scenario regardless of
  playlist."
- **Cross-scale sensitivity conversion** — normalize runs recorded under
  per-game sensitivity scales (Valorant, Overwatch) to cm/360 so they sort
  and group correctly on the Score vs Sensitivity axis, using conversion
  fields the stats files already carry. Fully designed and evidence-backed;
  parked with one open decision (conversion mechanism). Design in
  [`sensitivity_conversion_proposal.md`](./sensitivity_conversion_proposal.md).

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
