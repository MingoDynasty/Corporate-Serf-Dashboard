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

- **Rank and next-rank gap on benchmarks** — a benchmark's scenario table now
  shows the rank each personal best has reached and how much it has to grow
  to reach the next one, such as "+4.8% to Gold", with the threshold and the
  points still needed on hover. Sorting that column ascending lists the
  scenarios closest to ranking up, the question that used to send players to
  Evxl. Both columns come from the bundled thresholds and the local personal
  best, so they appear with the table and work offline. (PR #321; design in
  #320) Design rationale distilled into
  [`decision_log.md`](./decision_log.md).
- **Setup hints become notices** — the three plain-text lines that tell the
  user the app needs something from them (the stats-folder hint on Scenario
  Performance, its restart-pending twin, and the Settings page's restart
  notice) now wear the same yellow panel, warning icon, and no title that
  the first-run setup card already wore. The Settings notice leaves the
  orange the app reserves for a partly-committed action. No wording changed,
  and the Position field's inline hints stay value qualifiers. (PR #298;
  design in #281) Design rationale distilled into
  [`decision_log.md`](./decision_log.md).
- **App messaging consistency** — every string the app shows now follows one
  short set of copy rules, so the same condition reads the same way on every
  page: whole sentences with periods, one vocabulary, everyday contractions,
  control names in bold, and no em dashes, which a test now keeps out of the
  source. Some toasts that sounded like log lines now say what happened and
  what to do. No new surface and no behavior change. (PR #291; design in
  #247) Design rationale distilled into
  [`decision_log.md`](./decision_log.md).
- **Cross-scale sensitivity conversion** — a run recorded on a game's own
  sensitivity scale, like `0.2 Valorant`, used to plot under that raw number,
  so it sorted as 0.2 among centimeters and sat at the far left of the Score
  vs Sensitivity axis instead of beside the 40.8 cm/360 it actually is. Those
  runs now convert to cm/360 the moment their file is read, using two fields
  every stats file has carried since 2024, so they group, sort, and earn run
  notifications like every other run, and the playlist tables' PB cm/360
  column fills in for them. Sensitivities that one-decimal rounding used to
  collapse into one group separate correctly. Runs from 2019 to 2021 predate
  the fields and keep their original label rather than being dropped. (PR
  #280; design in #277, rulings in #279) Design rationale distilled into
  [`decision_log.md`](./decision_log.md).
- **Personal best celebration** — a run that beats a scenario's personal best
  now gets a short burst of confetti and a toast that says so, on whatever page
  is open and for every scenario rather than only the one being watched. The
  toast stays until it is dismissed, because the run that earned it was played
  in a fullscreen game, and if the tab was hidden when the run landed the
  animation waits for it to come back. A Settings control picks the
  animation — Confetti, Fireworks, Cannons, or Stars — or turns the whole thing
  off, with a Preview button beside it, and it is independent of Run
  notifications. Run delivery moved into the app shell to make that possible,
  which retired the "While you were away" catch-up digest: a run no longer
  waits for a Scenario Performance visit to be announced. (PRs #261, #268,
  #272; design in #248) Design rationale distilled into
  [`decision_log.md`](./decision_log.md); the follow-up that turned the switch
  into the choice of styles landed in #272, which closes the arc.
---

## Upcoming milestones

- **Run history and sessions** — a reviewable, persistent record of past runs
  that the ephemeral per-run toast can't provide: the current cross-scenario
  training session, and a scenario's full history over time (e.g. cold-start
  vs warmed-up comparisons). Gap-based *sessions* are a later
  quality-of-life layer on top; this supersedes the interim console-log
  stopgap in `file_watchdog.py`. Design in
  [`run_history_proposal.md`](./proposals/run_history_proposal.md), against the
  baseline in [`specs/scenario_performance.md`](./specs/scenario_performance.md).
---

## Future (briefly)

Listed so they aren't forgotten, but not yet actively planned. Each will be
expanded into its own roadmap entry when it becomes the next thing up.

- **Per-family celebration staleness** — the run-event freshness window
  applies the quiet-return rule to celebrations and ordinary run toasts alike,
  so a personal best set with no tab open celebrates only if the dashboard is
  opened within a couple of minutes of it, while any open tab keeps the
  celebration toast until it is dismissed, however long the player is away. A
  browser window the game only covers is not hidden (checked 2026-09-28), so
  during play the burst itself plays unseen and the toast is what lasts.
  Whether the celebration deserves its own longer or
  unbounded window is a question for real usage: whether the missed
  celebration in the play-then-open-the-dashboard flow grates, and how the late
  delivery feels when it fires. Nothing shipped forecloses the change; it is
  one conditional in the drain's decision rule plus an amendment to the
  digest ruling.
- **Score trend verdict** — *improving / plateauing / declining* classification
  per scenario, answering "is my current training working?" Likely shipped
  against raw score data first; richer rank-trend analysis would need rank
  history infrastructure that doesn't yet exist.
- **Difficulty measured against the player's own runs** — the shipped
  next-rank gap counts every percent as equal. Two scenarios can both need
  +5%, but if one's runs vary by 8% and the other's by 2%, only the first is
  a good day away. Weighing the gap by the player's run-to-run spread, and
  by recent form rather than the all-time personal best, would rank
  "closest" by what the player can actually reach. The app holds every local
  run, which external tools don't, so this could beat them rather than match
  them.
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
