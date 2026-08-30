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

- **Run notifications master switch** — run toasts can now be turned off. One
  Chart options switch, Run Notifications, silences the per-run toast family:
  the threshold verdict and the placement. The chart keeps updating either
  way, and a run file that failed to import still says so. The switch that
  used to read "Score Threshold Notification" never gated toasts at all, so it
  is now "Score Threshold Verdict" and says what it does. (PR #245; design in
  #240) Design rationale distilled into
  [`decision_log.md`](./decision_log.md). The catch-up digest this switch also
  gated has since been retired, and the personal best celebration is a
  separate family the switch does not reach (PR #261).
- **Scenario Performance point customization** — the raw run points can now be
  made smaller, larger, or a color of your choosing, from a Run Data Points
  group in Chart options. Eight curated swatches read on both the light and the
  dark chart; a picker and a hex field cover everything else; Automatic and
  Default keep the chart exactly as it was. Nothing else about the chart became
  customizable, which is the point. (PR #241; design in #238) Design rationale
  distilled into [`decision_log.md`](./decision_log.md).
- **Initial setup flow** — a fresh install now says what it could not set up
  for itself. The Scenario Performance page carries a small setup card while
  something has never been asked about: no KovaaK's stats folder was found, or
  the account that turns leaderboard positions and percentiles on has never
  been offered. The card links to Settings and nothing else — no wizard, no
  modal — and the account offer can be skipped, which turns rank lookups off
  and never asks again. The playlists overview explains its N/A percentile
  columns in the same words. (PRs #235, #236; design in #231) Design rationale
  distilled into [`decision_log.md`](./decision_log.md).
- **Feedback and bug-report intake** — the app has a defined place to send
  feedback and bug reports: GitHub Issues, with a bug form and a feature form
  and no blank-issue option. The bug form asks almost nothing — what happened,
  the version, and one attached log — and says plainly, before the upload box,
  that the issue and its attachments are public and what the log contains. The
  Settings page pre-fills the version into the form and shows where the log
  lives, so filing a report is a click instead of a hunt. (PRs #228, #229;
  design in #226) Design rationale distilled into
  [`decision_log.md`](./decision_log.md).
- **Chart options inspector** — the Scenario Performance graph's display
  preferences left the blocking "Settings" modal for a collapsible panel beside
  the chart, so an overlay is tuned against the live chart instead of through an
  open-close-open loop behind a dimmed page. On a narrow window the panel stacks
  above the chart instead. The page itself is now named Scenario Performance in
  the navbar and the browser tab, so only the Settings page answers to
  "Settings". No preference changed what it does or where it is stored. (PRs
  #209, #215; design in #206) Design rationale distilled into
  [`decision_log.md`](./decision_log.md).
---

## Upcoming milestones

- **Run history and sessions** — a reviewable, persistent record of past runs
  that the ephemeral per-run toast can't provide: the current cross-scenario
  training session, and a scenario's full history over time (e.g. cold-start
  vs warmed-up comparisons). Gap-based *sessions* are a later
  quality-of-life layer on top; this supersedes the interim console-log
  stopgap in `file_watchdog.py`. Design in
  [`run_history_proposal.md`](./run_history_proposal.md), against the
  baseline in [`specs/scenario_performance.md`](./specs/scenario_performance.md).
- **Personal best celebration** — confetti and a "New personal best" toast
  when a run beats a scenario's personal best, on every page and for every
  scenario, with a Settings-page switch to turn it off; a follow-up adds
  a choice of styles.
  The motivation layer the per-run verdict toast can't provide: the one
  moment every run is chasing currently passes in silence. Design in
  [`pb_celebration_proposal.md`](./pb_celebration_proposal.md).

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
  overview → scenario table → Scenario Performance drill chain covers
  playlist-first navigation; this would answer "show me this scenario
  regardless of playlist."

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
