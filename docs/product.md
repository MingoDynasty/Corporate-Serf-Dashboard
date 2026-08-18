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
- **Run notifications.** A run earns at most one toast, and its title is the
  verdict. A score-threshold pass or miss against the run's previous high
  score headlines whenever the threshold switch is on and a previous high
  score exists ("Threshold passed" / "Below threshold", the miss naming the
  target percentage it fell short of); otherwise a top-N placement within the
  run's sensitivity is the headline ("New 2nd-best score"). When a run earns
  both, the threshold verdict leads and the placement trails it. The message
  leads with the scenario, and the sensitivity is a trailing qualifier. The
  overlay line for that same percentage tracks the current personal best. A
  run that qualifies for neither is reported by its new point on the plot and
  nothing else. A new personal best has no toast of its own; it triggers the
  background rank refresh. If runs accumulate while Scenario Performance is
  not open, the next visit rebuilds once from final state and gives one
  scenario-named summary instead of replaying stale toasts and selections —
  and the next run you play replaces that catch-up digest, which is by then
  the staler news.
  *Problem solved:* immediate in-session feedback on whether the run you just
  played met your bar, readable at a glance without leaning in, and without a
  pile of toasts accumulating over a session or a noisy catch-up sequence
  after time away.
- **Quiet by default.** Toasts are reserved for what you did, what you
  achieved, and failures you would act on. A condition that stays true — no
  username configured, a leaderboard lookup that failed, a scenario with no
  runs yet — explains itself where it happens instead of interrupting again on
  every scenario switch. *Problem solved:* with no username set (the default
  on a fresh install) the app used to report that supported state as a red
  error on every rank render, stacking into a wall of red during normal play;
  now nothing turns red unless something you asked for failed, or a run of
  yours failed to record.
- **No username means quiet, on the position surfaces too** (PR #227). With
  no KovaaK's username configured, opening a playlist skips the position
  update entirely and the table says "Positions unavailable — set your
  KovaaK's username in Settings"; clicking Refresh on Scenario Performance
  answers with a blue notice naming the missing username. *Problem solved:*
  a fresh install could not open a playlist without watching a progress line
  count through an update that was fetching nothing, then land on a red
  "couldn't update 16 of 16 positions" — and Refresh answered the same
  configuration state with an anonymous "Position refresh failed". Both now
  name the actual condition and point at where to fix it. (A username that is
  set but wrong still reports as a generic failure; that case is not fixed
  yet.)
- **Rank overlays.** Benchmark rank thresholds drawn onto the plots.
  *Problem solved:* a raw score is meaningless without context; the overlay
  shows which rank band a score sits in and how far the next band is. By
  default it draws only the bands around your scores, so the runs fill the
  chart; a **Show all ranks** chart option draws the whole ladder instead, for
  when you want to see how far the climb goes rather than what is next.
- **Chart options beside the chart** (Scenario Performance page, PRs #209,
  #215). The graph's display preferences — the overlays, and the score
  threshold and its percentage — open in a panel next to the chart, grouped by
  what they affect, and collapse back out of the way. On a narrow window the
  panel stacks above the chart. *Problem solved:* these settings used to live
  in a modal that dimmed and blocked the only surface that shows what they do,
  so picking a threshold percentage meant guessing, closing the modal to look,
  and opening it again. Now the chart answers immediately. The same change
  gave the page a name of its own, **Scenario Performance**, so "Settings"
  means the Settings page and nothing else — the modal, the button that opened
  it, and the navbar link had all been calling themselves Settings, two of
  them with the same icon.

### Standing: where do I rank

- **Scenario rank and percentile** (PRs #8–#10). The Scenario Performance page
  shows your global leaderboard standing for the selected scenario —
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
- **Live percentile warmup** (PRs #129, #130, #132, #133). Played scenarios
  from visible playlists fill their percentile caches politely in the
  background; the overview shows honest coverage placeholders and live
  remaining/ETA or paused status until complete. *Problem solved:* a cold cache
  no longer produces misleading partial medians or makes the user open every
  playlist by hand before cross-playlist weakness comparisons become useful.
- **Playlist show/hide** (PR #87). Per-playlist Hide/Unhide on the
  overview, a "Show hidden" toggle for managing hidden ones, and hiding
  filters every playlist dropdown (Scenario Performance filter, Journey
  picker). Hidden playlists stay loaded — routes and rank overlays keep
  working. *Problem
  solved:* focus — dropdowns and the overview show only the playlists you
  care about, which is what makes shipping the full benchmark library
  tolerable.
- **Bundled benchmark library** (PR #90; expanded by the 2026-07-11 curation
  import). Every importer-generated benchmark (216 files) ships with the app
  and loads at startup; Voltaic and Viscose are visible by default and the
  rest wait behind "Show hidden" on the Playlists page. *Problem solved:* enabling a benchmark used to mean
  manually copying a JSON file and restarting — now it's one unhide click,
  and app updates refresh the whole library automatically.
- **Bundled scenarios ship their leaderboard IDs** (PR #169). Every scenario
  in the bundled benchmark library carries its KovaaK's leaderboard ID, folded
  into the local name→ID mapping cache at startup. *Problem solved:* opening a
  bundled playlist you have never played used to resolve each scenario's
  leaderboard ID one slow, timeout-prone name-search call at a time — now those
  IDs are already known, so first opens of unfamiliar playlists are faster and
  less flaky, even before a username is configured.
- **Playlist scenarios overview** (PRs #12, #15, #16, plus progressive fill in
  PR #127 and PB Date in PR #216). A sortable table of every scenario in a
  playlist — position, total players, percentile, last played, runs, PB Score,
  PB Date, PB cm/360, PB Accuracy. Long playlists scroll inside the table so
  the column labels remain visible while scanning deep rows. The local and
  cached parts paint immediately; unresolved leaderboard cells animate and
  stream into place with a counter instead of hiding the table behind a
  minutes-long spinner. *Problem solved:* the headline use case is *"show me
  the scenarios where I'm worst, sorted ascending — that's my training
  priority list."* It also surfaces scenarios gone stale, and remains usable
  while KovaaK's is slow or unreachable. Last played tells you recency of
  play while PB Date tells you recency of improvement, so sorting PB Date
  ascending surfaces plateaus — scenarios still being played whose best
  hasn't moved. A session-planning tool, checked at the start of a training
  session.
- **Relative "last played" timestamps** (PRs #17, #19, #23). "5 minutes ago"
  / "3 months ago" everywhere a timestamp appears, exact time on hover.
  *Problem solved:* staleness is the actual question ("how long since I
  touched this?"); absolute dates make the user do the math.
- **Aim Training Journey page** (work in progress, currently unlinked from
  the navbar). Visualizes training-hour checkpoints across playlists.

### Getting data in

- **Settings page, and a stats folder the app finds itself** (`/settings`, PRs
  #181–#184). The stats folder, KovaaK's username, and Steam ID are edited in
  the app and stored in a file the app owns; a start with nothing configured
  looks the stats folder up on this machine and stores what it finds. *Problem
  solved:* configuring the dashboard used to mean finding a TOML file and
  typing a Steam library path into it, and a moved Steam library turned that
  chore into a dashboard that refused to start. It now starts regardless —
  empty pages and a hint pointing at Settings when there is nothing to show —
  and usually needs no configuration at all. Changes that cannot safely take
  effect under a running app say "restart to apply" instead of pretending.
- **The Settings page suggests what the machine already knows** (`/settings`,
  PRs #189, #191, #193). The stats-folder box lists every Steam library that
  holds a KovaaK's stats folder, and a Detect button checks this machine's
  Steam accounts against KovaaK's and fills in the account it can prove is
  yours — offering the ones it found when it cannot prove exactly one. *Problem
  solved:* the page used to accept only what the user could type from memory.
  A username typo produced silently absent ranks, nobody knows their 17-digit
  Steam ID offhand, and repairing a wrong-library stats folder meant digging a
  deep path out of Explorer — all of it answerable from Steam's own files plus
  one public KovaaK's lookup. Identity now arrives verified rather than
  remembered, and a wrong pick is repaired by choosing a suggestion. Nothing is
  written until Save, so a suggestion is never a decision made for the user.
- **A fresh install explains itself, once** (Scenario Performance page, PRs
  #235, #236). A setup card appears while something has never been asked
  about: it says so when no stats folder was found, and otherwise offers the
  KovaaK's account that turns leaderboard positions and percentiles on. Either
  way it points at the Settings page and nothing else; the account offer can
  be skipped, which turns rank lookups off and never asks again. The playlists
  overview says the same thing where its percentile columns read N/A. *Problem
  solved:* a first launch usually charts runs with no setup at all, which left
  the one optional feature invisible unless a user stumbled onto it, and when
  the folder lookup missed, exactly one page explained why everything was
  empty. The app now states what is missing without a wizard, and stops asking
  the moment the user answers — including when the answer is no.
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

### Getting and updating the app

- **One-line install with a self-updating shortcut** (PRs #155, #159, #163).
  The whole install is one line pasted into PowerShell: it brings its own
  Python and uv, asks nothing at all, and leaves a desktop shortcut (finding
  the KovaaK's stats folder moved into the app itself, above). Each launch
  updates to the newest release before starting, and
  quietly runs the version already installed when there's no internet.
  *Problem solved:* the audience is Windows gamers, not Python developers —
  "clone the repo, install uv, run `uv sync`" excluded most of them. Everything
  it installs stays in one folder, so uninstalling is deleting that folder and
  the shortcut.
- **Every build says what it is, and installer-era releases can be rolled back**
  (PRs #154, #158, #159). Releases are dated, immutable, and kept forever; the
  running build records its commit in the log. *Problem solved:* a bug report
  couldn't be tied to a version, and a bad push had no "go back to yesterday" —
  installing an older tag now pins it there until the user opts back into
  updates. Rollback targets must ship the installer and launcher, so
  `v2026.07.19.4` is the earliest; older tags predate that contract and their
  installs abort.
- **The version is on the Settings page** (PRs #188, #190). The page names the
  release tag, with the commit it was built from underneath, and a freshly
  updated app knows its own tag from its first session. *Problem solved:* the
  two moments anyone wants a version are right after an update ("the console
  said it updated — did it?") and while writing a bug report, and until now the
  answer sat in a tooltip on the header's GitHub icon, where nobody looks. It
  used to read "unknown" for the whole session after an update — exactly when
  it was most likely to be checked, and exactly the look of a failed update.
- **Somewhere to send a bug report** (PRs #228, #229). GitHub Issues is the
  place, with a bug form and a feature form so a report arrives with what it
  needs instead of as a paragraph the maintainer has to interview. The bug
  form asks almost nothing — what happened, the app version, and one attached
  log file — and the Settings page fills in the version and shows where the
  log lives, so filing one is a click rather than a hunt through
  `%LOCALAPPDATA%`. Before the upload box, the form says in plain words that
  the issue and its attachments are public and what the log contains — the
  KovaaK's username and Steam ID already stamped on your leaderboard scores,
  your scores and play times, and paths that may name your Windows account —
  and invites you to open it in a text editor first. *Problem solved:* the app
  runs entirely on the user's machine and phones nothing home, so a failure
  nobody else can reproduce is only diagnosable if the user can hand over the
  evidence — and they will only do that if what they are handing over, and to
  whom, is stated honestly rather than buried.

**The dashboard can be opened from another device.** By default the app serves
only the machine it runs on. One setting in `config.toml` widens that to the
whole network, so the dashboard opens on a phone or a second PC at that
machine's address. The setting is off by default and says plainly what turning
it on costs: the app has no login, so anything that can reach the address can
read the run data and change the settings. *Problem solved:* the stats live on
the gaming PC, but that is often the worst place to read them — mid-session,
between runs, the useful screen is the one already in your hand. Without this
the only way to see a scenario's history was to stop playing and alt-tab.

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
