# Run History Proposal

> **Status:** Future — deliberately high-level. This is expected to ship
> *after* the playlist-level overview milestone, so its ship date is far
> out. The app will
> likely change materially before then; the navigation/UI surface below is
> intentionally left open and should be revisited at build time. Only the
> durable data-model and sequencing decisions are meant to survive that long.

## Problem

When a run finishes, a transient toast reports whether it passed the
user's score threshold. That works in the moment but is ephemeral — once the
message is popped off the queue, it's gone. A user who plays several runs and
only hits threshold on the last one has no way to review how the earlier runs
compared.

The score-threshold pass/fail info is therefore *already in the UI* (the live
toast); what's missing is **review after the fact**. The console log in
`file_watchdog.py` is a crude, developer-facing version of that missing
capability — unlike the ephemeral toast, it accumulates a scrollable per-run
record within a session. It is therefore **retained as an interim stopgap**
and removed only once this feature ships; it is not deleted ahead of a
replacement.

## The two views

Both are slices of the existing chronological `run_database` — no new data
capture is required.

1. **Current session (cross-scenario).** A time-ordered view of the runs in
   the user's current training block, which typically interleaves multiple
   scenarios. Answers "what am I doing right now / how did the last few runs
   go." Because scores aren't comparable across scenarios, this view
   normalizes on **% of PB** rather than raw score.

2. **Full history for a scenario (single-scenario).** All runs for one
   scenario, chronologically, so the user can compare across time — e.g. a
   cold-start run 1 against a previous session's warmed-up run 5. Single
   scenario, so raw score / PB-delta is directly meaningful.

## Durable decisions

- **Raw timestamps first; sessions are a later quality-of-life layer.** With
  timestamps visible, the user can eyeball the session boundary. Sessions
  automate that, but the views work without them.
- **Sequencing within the feature:** ship view (2), the per-scenario history,
  first — it needs no sessionization. View (1), the current-session view,
  arrives *with* the sessionization layer, since "current session" is
  precisely what requires a session boundary to exist.
- **Sessions are gap-based, not per-calendar-day.** A new session begins when
  the gap between consecutive runs exceeds a threshold. This handles
  morning-vs-night blocks automatically and crosses midnight cleanly, unlike a
  calendar-day model. Sessionization is a pure function over the already
  time-sorted `run_database`.
- **The gap threshold is a module-level constant (~30 min), not config or a UI
  knob.** The output is insensitive across a wide range (~15–60 min), so a
  dial buys nothing but validation/documentation surface. Promote to
  `config.toml` only if real demand appears — a non-breaking change to make
  later, whereas removing a shipped knob would be breaking.
- **No SQLite migration is required for this feature.** The in-memory
  `run_database` already supports history and gap-based sessions with a trivial
  O(n) walk. SQLite remains a separate, later optimization justified by startup
  scan cost at scale or by a need to persist data not derivable from the CSVs
  (e.g. session notes) — not by this work.

## Open questions (defer to build time)

- **Navigation surface.** *No permanent sidebar* — a sidebar plus a page would
  be two surfaces onto overlapping data (noise + duplicated wiring). The real
  choice is between one consolidated Run History page hosting both views, and a
  per-scenario history panel on the home page (contextual to the selected
  scenario) plus a separate current-session page. Trade-off is context vs
  consolidation. The analogous question for the playlists feature was settled
  as two pages with drill-down (see the 2026-07-03 "Playlists Routes Are
  Stable" decision-log entry); settle this one as part of the app's overall
  navigation story, once, rather than piecemeal.
- **Columns per view.** Straw man: time, score, % of PB, delta vs previous
  run, accuracy, threshold pass. `accuracy` / `damage_accuracy` are barely
  surfaced today and this is their natural home.
- **Roadmap placement.** Belongs in the roadmap's "Future" list; exact
  ordering relative to later work to be decided.

## Future / optional

- **Cold-vs-warm insight.** Once runs carry a position-within-session,
  "your warm runs average +X% over cold starts" becomes a derivable insight
  rather than something the user eyeballs. Explicitly out of scope for the
  first build.
