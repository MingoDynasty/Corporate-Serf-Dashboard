# Corporate Serf Dashboard — Product Roadmap

## Vision

Help aim training enthusiasts understand and direct their improvement by
turning raw run data into actionable insight about *where they stand*, *where
they're going*, and *where to focus*.

The dashboard already captures every run. This roadmap is about turning that
data into answers to the questions players actually ask themselves:

> *Am I improving? Where am I weak? What should I work on next?*

This roadmap is intentionally short-horizon. It focuses on what's next and
keeps farther-out work as brief mentions until they're up next.

---

## Shipped

- **Scenario rank lookup** — current rank fetched from the live leaderboard,
  with Steam ID identity matching, background refresh on new high scores, and
  thread-safe cache I/O. (PR #8)
- **Leaderboard total and percentile** — display extends to
  `Rank: 11,290 of 63,892 (82.33% Percentile)` using KovaaK's midpoint
  formula. (PRs #9, #10)

For design details, see
[`scenario_rank_proposal.md`](./scenario_rank_proposal.md).

---

## Upcoming milestones

### 1. Playlist scenarios overview

**What:** A table view of every scenario in a selected playlist, showing each
scenario's rank, percentile, last-played date, run count, and high score at a
glance — without having to click through scenarios one at a time.

**Why:** Today, players have to cycle through the scenario dropdown one by
one to see how they're doing on each. This makes it hard to see the forest
for the trees. A table lets them spot weak scenarios at a glance, sort by
percentile to surface training priorities, and see which scenarios have gone
stale.

The headline use case:

> *"Show me the scenarios where I'm worst, sorted ascending. That's my
> training priority list."*

This is a session-planning tool — checked at the start of every training
session — which is why it's prioritized despite being the largest engineering
effort on the horizon.

---

### 2. Playlist-level overview and stats

**What:** A higher-level view of all imported playlists with aggregate stats —
average percentile, last-played date, total runs — and a way to drill into
any playlist to see its scenarios.

**Why:** Playlists go stale. A player might have crushed a Voltaic benchmark
six months ago and forgotten about it, only to come back later with
significantly better mechanics and beat all their old scores. This view
surfaces forgotten playlists worth revisiting, and gives a single-glance
summary of which playlists are getting attention versus which are
languishing.

**Decided:** Lives as new dashboard real estate, not folded into an existing
page (home, Aim Training Journey).

**Open question:** Whether to ship milestones 1 and 2 as **two separate Dash
pages** (with drill-down navigation) or as **one combined page** with the
playlist-level overview on top and the per-scenario table revealed by
selecting a playlist. Either is viable; the choice affects layout, routing,
and how the URL reflects state. Worth resolving before milestone 1 ships,
since whichever decision is made shapes the milestone 1 entry point.

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
  from the playlist-level overview in milestone 2 — so it remains a separate
  concern to revisit later, not a replacement for milestone 2.

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
