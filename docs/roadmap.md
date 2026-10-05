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

- **Columns menu and KovaaK's ID columns** — the Playlists table and a
  playlist's scenario table each gain a Columns menu that shows or hides any
  column and remembers the choice in the browser. Each table also gains one
  column that starts hidden, the KovaaK's ID of the benchmark or of the
  scenario's leaderboard, so trying an API request by hand no longer starts
  with digging the number out of a file. Both pages look as they did until
  the menu is used. (PR #344; design in #334) Design rationale distilled
  into [`decision_log.md`](./decision_log.md).
- **New PB stars on the Score vs Time chart** — the chart now draws a gold
  star on each plotted run that beat the scenario's personal best when it was
  played, so it shows when each best was reached, including the ones a later
  run the same day beat. The rule is the personal best celebration's, judged
  over the scenario's whole history at every sensitivity. There is no
  setting: the stars follow Point size, and the Score vs Sensitivity chart is
  unchanged. The stars record achievements, and whether the player is
  improving stays the trend verdict's question. (PR #346; design in #337)
  Design rationale distilled into [`decision_log.md`](./decision_log.md).
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
---

## Upcoming milestones

What we plan to do now or very soon, each with the reasons it comes next.

- **Run history and sessions, sessions first** — a reviewable record of past
  runs that the per-run toast can't provide: the session in progress, recent
  sessions, and a scenario's history over weeks. The app will split the runs
  into sessions at a gap between runs, and each session into visits, a visit
  being an unbroken stretch of runs on one scenario. Sessions and visits are
  built first, as the foundation the history views stand on, not as a later
  layer.
  The milestone retires the interim per-run lines the watchdog writes to the
  debug log. Why it's next, and why sessions first:
  - Nearly every planned feature needs sessions and visits: history grouped
    by session, time spent in a session, the trend verdict built on session
    medians, and the typical run.
  - They're cheap: one pure pass over the runs the app already holds in time
    order, with no new data to capture.
  - It's what gets used most in session: a scenario's history and the
    session so far are what the player checks between runs.
  - All three seats that reviewed the in-session and between-sessions framing
    (#317) recommended building the session review first.

  The [current proposal](./proposals/run_history_proposal.md) predates this
  order. Its "sessions later" decision and its view order are marked
  superseded, and a rewritten proposal will replace it. Baseline in
  [`specs/scenario_performance.md`](./specs/scenario_performance.md).
- **Time-scored scenarios measured by pace** — some scenarios score the time
  left on a countdown when the task is done, and on those a percentage of the
  score understates the real change several times over. So the percentages
  the app shows there, the Next Rank gap and the score threshold among them,
  make those scenarios look closer to ranking up and easier to pass than they
  are. The fix measures them by pace: how fast a run finishes compared with
  the personal best. Why now: it's a bug in shipped features, and a small
  one. It's a correctness fix rather than a milestone, so it runs beside Run
  history. Its design is ratified in
  [`time_scored_pace_proposal.md`](./proposals/time_scored_pace_proposal.md),
  and one implementation PR follows.
---

## Future (briefly)

Planned work, in no particular order. The order of this list carries no
meaning; an entry becomes an Upcoming milestone, with its reasons, when it's
next.

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
  per scenario, answering "is my current training working?" It's built on
  session medians, the middle of a scenario's runs in each session, and shown
  with a chart of the typical run over time. A scenario without enough
  sessions gets no verdict rather than a guess.
- **Difficulty measured against the player's own runs** — the shipped
  next-rank gap counts every percent as equal. Two scenarios can both need
  +5%, but if one's runs vary by 8% and the other's by 2%, only the first is
  a good day away. A rank-up chance, the estimated chance that one run clears
  the next rank line, would weigh the gap by the player's run-to-run spread
  and by recent form rather than the all-time personal best, and so rank
  "closest" by what the player can actually reach. The app holds every local
  run, which external tools don't, so this could beat them rather than match
  them.
- **Scenarios page** — scenario-first navigation for scenarios that live in
  several playlists or in none, parked from the playlist-overview design. The
  overview → scenario table → Scenario Performance drill chain covers
  playlist-first navigation; this would answer "show me this scenario
  regardless of playlist."
- **Weakness by the typical run** — columns on the playlist scenario table
  that rank weakness by the typical run instead of the personal best. They
  wait on a re-check, due around 2026-10-09, of the evidence that the typical
  run orders weaknesses better.
- **An overview** — time spent and activity across all scenarios. No design
  yet.
- **KovaaK's own log** — the game's log records what stats files usually
  don't: restarts, freeplay, and how long the game was open, which could give
  time spent an upper bound. A local archive outside the app is already
  collecting the maintainer's logs, so there's history to design against.
- **Accuracy guideline** — the accuracy the top leaderboard players land at on
  a scenario, as a reference for what good play looks like rather than a
  target.
- **Per-bot breakdown on time-scored kill scenarios** — which bots cost the
  most time, from each bot's time to kill, which the stats files record.

---

## Guiding principles

- **Answer the question, don't just show the data.** Charts and numbers are
  means; the user wants conclusions.
- **Judge skill by the typical run, not the best run.** The typical run is
  what the player's recent runs usually score. Judgments about skill (where
  the player is weak, where their level stands, whether they're improving)
  move toward it. A personal best is one run, and a lucky one makes a
  scenario look stronger than it usually plays, so a list ordered by
  personal bests can rank a consistent scenario as weaker than a spiky one
  that usually plays worse. The personal best stays the achievement:
  KovaaK's ranks it, the app celebrates it, and the rank and leaderboard
  position show it.
- **Be honest about uncertainty.** Unknown isn't weak: a judgment with too few
  runs behind it says so, and a scenario isn't ranked weak or strong until it
  has enough. A figure that can only be a minimum is labelled one, such as
  time spent in runs, which leaves out the time between runs and any attempt
  that wrote no stats file. An estimate is shown no more precisely than it's
  known, such as "about 1 in 25 runs" rather than "4.1%".
- **State verdicts, not advice.** The app states facts and verdicts: the
  typical run, a trend, a rank-up chance, "unknown", and whether a bar the
  player set, such as the score threshold, was met. A verdict answers the
  question, and what to do about it in training stays the player's call: the
  app doesn't say what to play or when to stop. Moving past verdicts takes a
  decision of its own, and advice the app vouches for takes strong evidence
  first.
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

The typical-run, uncertainty, and verdict principles are recorded with their
evidence, its limits, and the options set aside in the
[decision log](./decision_log.md#2026-10-04-skill-is-judged-by-the-typical-run-with-honest-uncertainty-in-verdicts-not-advice).
