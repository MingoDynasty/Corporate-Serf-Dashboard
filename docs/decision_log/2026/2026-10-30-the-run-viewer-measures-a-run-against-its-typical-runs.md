# 2026-10-30: The Run Viewer Measures A Run Against Its Typical Runs

Status: Accepted

Everything the run viewer compares, whether a tile, a setting or a bot, is
compared with one set of runs: the runs behind the scenario's typical score
when the run's session began. A figure's typical is its median over the runs
that have it, and its hover says how many runs that was. A line under the
score names the runs and when they were played, or says why there are none.
There is no menu to compare with the PB run or the previous run instead.

**Ruling.** RV2 of
[proposal #450](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/450),
ratified by the maintainer on 2026-10-30 at `f80c109` ("Sounds good. I
ratify."), as recommended. Their lean before that, 2026-10-30, after a
write-up of what a menu would take: "Yes, keep it shelved." Shipped in
[#455](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/455)
for the tiles and Settings and in
[#PR3NUM](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/PR3NUM)
for By Bot, on the figures from
[#453](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/453).
What the page does today is in
[run_history.md](../../specs/run_history.md#what-it-shows).

**The typical runs** (`view_run` in `source/kovaaks/run_viewer.py`):

- `typical_score_at_session_start(...).runs` while that value is known, at
  any age, as the latest-run card counts it: up to 20 runs of the scenario
  before the run's session, known at 20 runs or at 10 across 2 or more
  sessions. When the value is unknown or there is none, the run has no
  typical runs.
- The Score tile's typical is therefore the latest-run card's typical score
  at session start: over the mockup's six scenarios the two agree on every
  run, up to rounding. The roadmap's principles judge skill by the typical
  run, and the card already measures the newest run this way
  ([2026-10-25](2026-10-25-the-latest-run-card-measures-the-run-against-the-typical-score-at-session-start.md)).
- Nothing is stored. The run's stats file and its typical runs' files are
  read each time the run opens, up to 21 files of a few kilobytes.

**A typical.**

- A tile's typical is the median of its figure over the typical runs that
  have it, and a bot's is the median over the typical runs that name the bot
  and have the figure. A setting's is its most common displayed value, a tie
  going to the value the latest typical run used.
- There is no minimum beyond one run. Each typical's hover counts the runs it
  took, `Median of {n} of your {N} typical runs`, or `Median of your {N}
  typical runs` when every one counts, so a typical on one run reads as one.
- With no typical runs, every Typical and Difference is left out, no setting
  is marked, and each By Bot figure is one column.

**The reference line**, under the score: `Typical comes from your {N} runs
before this session, played on {date}.`, or `played from {date} to {date}.`
when they span more than a day. With none, `This is the scenario's first
session, so there's no typical run to compare with yet.`, or `There's no
typical run for this run's session yet: it had {N} runs before it, and a
typical score needs 10 runs across 2 or more sessions, or 20 in one session.`
(`1 run` for one).

**Rejected: a Compare with menu** (shelved as S2), offering the PB run or the
previous run. The arithmetic is the same with a set of one run; the cost is
in decisions and states. The PB has to be the one the run chased, not
today's, which differs on 39 of 55 Popcorn runs and 69 of 86 PGT runs; the
first run has neither a PB nor a previous run; the choice needs rules for
sticking across runs, scenarios and reloads; every `Typical` label and hover
needs a wording per option. And a single run is noise: a median of 10 to 20
runs moves far less than one run, so each Difference would swing by chance.
Revisit when a question comes up that the typical runs can't answer.

**Provenance.** Proposal by `claude-opus-5-5` (#450), read by `gpt-6-astra`
(flagship, first wave) and reviewed by `gpt-6.1-sol` (the seat) and
`claude-fable-5-1`. Built by `claude-opus-5-5` in #453, #455 and #PR3NUM.
