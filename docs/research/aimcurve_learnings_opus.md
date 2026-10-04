# Lessons from Aimcurve

Date: 2026-10-03
Author: claude-opus-5-5 · effort: xhigh

Research note; recommendations remain unratified.

## Takeaway

Aimcurve reads a second file that current KovaaK's builds write for each
completed run, the `.perf` performance file. This app reads only the stats
CSV. One run's `.perf` is enough to classify a scenario as scored on
completion time, from two signals taken together: a sentinel in the header
and score ticks that count down. The open pace proposal infers the same
thing from run lengths across a scenario's runs. The two signals were
checked here against the maintainer's own recordings and agreed on all
1,764 files. The rest of the survey is design input for the run-history
work, plus one ingest risk worth reproducing before that work leans on run
counts and medians.

## Evidence and scope

- Inspected Aimcurve at
  [`be28be9`](https://github.com/voidfill/aimcurve/tree/be28be999587888d4d5cb34d69d1fa3dfc1fe6d8),
  the head of `master` on 2026-10-03: the README, the design specs under
  `docs/superpowers/specs/`, and the format notes `docs/perf-format.md` and
  `docs/ingest.md`. External links below are pinned to that revision.
- The project was created on 2026-09-14 and has 91 commits from one author.
  It carries no license file, so none of its code is reusable here. Ideas and
  file-format facts are. The `.perf` schema is KovaaK's own, published at
  <https://wiki.kovaaks.com/performance.proto> (fetched 2026-10-03).
- Compared against this repository at `161b2cd`, and against the pace
  proposal in
  [PR #329](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/329)
  at `bdd59eb`.
- **Local verification.** A read-only script decoded every `.perf` file in
  the maintainer's KovaaK's install and read the name and two lines of every
  stats CSV. It covered 1,764 `.perf` files dated 2026-04-30 to 2026-10-03
  and 8,880 stats files. The script is kept, untracked, at
  `ignore/scripts/aimcurve-survey-opus/probe_perf.py`.
- **Not done.** Aimcurve was not run, and no recordings were imported into
  it. Its live page was read as text only, so this note makes no claim about
  its visual design. No reset or abort file was produced on purpose; finding
  4 rests on Aimcurve's captures and a reading of our parser.
- Written without sight of the [Astra survey](aimcurve_learnings_astra.md)
  and compared with it afterwards, in the last section.

## Findings

### 1. One `.perf` file classifies a time-scored scenario

**Observed:** Aimcurve classifies each run from its own `.perf` file, using
two independent signals. The header's `time_limit` holds `1000`, which
KovaaK's uses as its "no time limit" value. The per-second score ticks count
down with the clock: the first is positive and each later one is minus the
seconds elapsed since the tick before. Neither signal is a scoring type on
its own. The published schema has no such field, and `1000` says only that
the run has no time limit. Aimcurve requires both, so that a run where they
disagree, or a format change, degrades to "unsupported" instead of the
wrong kind. In its corpus the two signals agree on 153 of 153 such runs,
and score plus elapsed time is 1,000 on every one.
[Scoring model, D2 and D3][scoring], [format notes][perf-format].

**Verified locally:** The same two tests were applied to all 1,764 local
`.perf` files, with these results.

- 84 runs across 10 scenarios carry the `1000` value. The countdown test
  passes on exactly those 84 runs and on no others.
- Score plus the last tick's timestamp is 999.98 to 1,000.00 on all 84.
- The 10 scenarios are the seven the pace proposal detects, plus three with
  a single `.perf` run each: Air CELESTIAL No UFO Easier, Air Spectral Easy
  85%, and Ground Plaza Sparky v3 Easy.
- Two scenarios set the header's `end_challenge_after_kills` (Aimerz+ VAS
  Easy S1 and VT Plaza Viscose). Neither signal marks them as time-scored.
  Aimcurve found the same of its own kill-capped scenarios: their length is
  set by the bot rotation, and they score like any fixed-length run.
- The header's `timescale` is 1.0 on all 84 time-scored runs and differs
  from 1.0 on 363 fixed-length runs (0.52 to 2.0). So the local files hold
  no example of a slowed or sped-up time-scored run.

**Coverage:** Local `.perf` files start on 2026-04-30, so they cover about a
fifth of the stats files. Aimcurve dates the format to game version 3.9.0;
why the local files start later was not established. Since that date
coverage is near complete: one non-reset stats file has no `.perf` of the
same name. A `.perf` is written only when a run completes.

**Our baseline:** The pace proposal states that "KovaaK's writes no scoring
type anywhere the app can read", and it does not mention `.perf`. It detects
a time-scored scenario by fitting score plus run length across the
scenario's runs, with run length taken from the stats file's name and its
`Challenge Start:` line. Its fitted constants are 999.48 to 999.71 with up
to 0.53 s of spread, and it notes that thirteen single-run scenarios "are
likely time-scored too, but one run can't show it". The
[RefleK's survey](refleks_learnings.md) lists the file's header fields and
events without this use of them.

**Recommendation:** Put this evidence in front of the pace proposal's
reviewers before its detection design is settled. Where any run of a
scenario has a `.perf`, that one run can classify the scenario, provided
the classification requires both signals: the `1000` sentinel and the
countdown. The sentinel alone is not enough. A run with no time limit whose
score accumulates has to stay unclassified, as it does in Aimcurve. With
both signals present, the constant is read from the header instead of
fitted. The fit stays necessary as the fallback for scenarios whose runs
all predate `.perf`. Three costs come with it:

- A second directory to read. `performances` sits beside `stats`, and the
  stats-folder setting names only `stats`.
- A protobuf reader. The countdown test needs the score events as well as
  the header, so the reader decodes the whole file. The script's is about
  sixty lines of dependency-free Python, and it decoded every local file
  without error.
- An identity question. The header carries the scenario's hash, and our run
  model groups runs by name. Aimcurve saw no hash with both kinds.

### 2. Projected final score puts a run, its best, and the ranks on one axis

**Observed:** Aimcurve's run chart plots, at each moment, the final score
the run would reach if its pace so far held. The axis is therefore in score
units. The personal best and every rank threshold are horizontal lines on
it, with no conversion, and the line ends on the run's real score. A second
line shows pace over the last five seconds. For a time-scored run the same
axis is relabelled in seconds. No per-scenario scoring formula is needed,
because the `.perf` score ticks are increments of the game's own running
score: in Aimcurve's corpus they sum to the stats file's `Score:` on 2,156
of 2,156 runs. A per-bot table beside the chart shows time or points lost
against the baseline run. [Scoring model, D1, D5 and D7][scoring],
[run view][run-view].

**Not verified:** The sum was not compared with `Score:` on local
fixed-length runs. Ticks arrive about once a second, so nothing finer than
a second can be shown.

**Our baseline:** "How did that run go?" is one of the two in-session
questions in [product.md](../product.md). The run toast, the personal best
celebration, and the new point on the plot answer it today. The
[run model](../../source/kovaaks/data_models.py) keeps one score per run
and nothing from inside it.

**Recommendation:** If within-run analysis is ever taken up, start from
this model instead of per-scenario formulas. It is a separate capability
and is not on the [roadmap](../roadmap.md). One practical fact for any
design that reads `.perf` as runs land: Aimcurve measured the stats file
being written about 1.6 ms before its `.perf`, so a watcher that reacts to
the stats file has to wait for the pair. [Ingest notes][ingest].

### 3. Scenario history: a typical line, an attempt axis, and honest gaps

**Observed:** Aimcurve's per-scenario page draws one dot per completed run,
a step line for the best so far, and a rolling median of the last ten runs.
The median is drawn thicker than the best line and lighter until its window
is full. The default x-axis is the attempt number, with a toggle to dates,
because runs cluster into stretches months apart. Session boundaries are
faint vertical rules. Dots are colored by settings group (sensitivity, DPI,
and field of view), and only the three most recent groups get a color. The
settings table says in a caption that it does not isolate the effect of a
setting, since later settings have more practice behind them. Missing data
is shown as a gap with a count, such as "212 of 240 runs have bot detail",
and never as a zero. [Scenario page, S4 and S5][scenario-page].

**Our baseline:** Score vs Time plots by date. The
[run-history proposal](../proposals/run_history_proposal.md) owns the
per-scenario history view, and the product direction in PR #327 proposes
typical performance over best performance. Neither is ratified.

**Recommendation:** Treat these as inputs to the run-history rewrite: the
median drawn as the main line, the attempt axis as an option, session rules
on the chart, and a stated sample count wherever a window is not full. The
window size and the settings key remain design questions there.

### 4. A reset can write a stats file that looks like a run

**Observed:** KovaaK's has a setting for when stats files are written:
none, on completion, on completion and reset, or always. Aimcurve captured
files under the last setting with a filesystem watcher. A file written on
reset keeps the scenario name and the counters so far. Its score is zero
only when the score is derived at run end. Its `Challenge Start:` is the
start of the attempt that follows, so two files can share one start time.
Its `Avg FPS:` is usually zero but was a meaningless large number in 3 of
22 resets. Aimcurve's rule is that a file is a reset when the time in its
name minus `Challenge Start:` is under one second, which caught 22 of 22.
A file written when the player leaves a paused scenario has an empty
`Scenario:` line and no ` - Challenge - ` in its name. Aimcurve keeps
resets as attempts and off every performance chart, because a player
resets when a run is going badly. [Ingest notes][ingest].

**Verified locally:** Of 8,880 stats files, one is reset-shaped by that
rule (Pasu Voltaic Easy, 2021-01-05, 0.52 s, score 48.0) and none is
abort-shaped. This install does not write them. Whether that one file is a
reset was not established. The rule cannot apply to the 463 files from old
builds that have no `Challenge Start:` line.

**Read in our code, not reproduced:** `extract_data_from_file` in
[data_service.py](../../source/kovaaks/data_service.py) accepts a file that
has a scenario, a score, a sensitivity, and a weapon row with at least one
shot. It does not look at the interval. A reset file with shots fired would
be stored as a run with a low score. It would count toward the run total,
could draw a "Below threshold" toast, and would pull down any median.

**Recommendation:** Reproduce this first: switch the KovaaK's setting on a
throwaway session, reset a few runs, and see what the app stores. If it is
confirmed, exclude such files by the interval rule, and treat files with no
`Challenge Start:` as complete. This matters more once typical scores and
run counts drive verdicts, and now that the app's users are no longer one
install.

### 5. A link that opens a scenario in KovaaK's

**Observed:** Aimcurve links each scenario to
`steam://run/824270/?action=jump-to-scenario;name=<name>;mode=challenge`,
with the name percent-encoded. KovaaK's documents the link without the last
part. Aimcurve's author found by hand on 2026-09-25 that the documented
form opens freeplay, and that `;mode=challenge` opens the challenge. The
link selects by name, not by hash. [Scenario page, S7][scenario-page].

**Not verified:** The link was not tried here.

**Our baseline:** No `steam://` link exists anywhere under `source/`.

**Recommendation:** A small candidate for the playlist scenario table,
where the Next Rank column already names what to play next. It is a plain
link, the browser asks before opening Steam, and the app makes no request
of its own. Try it by hand before designing around it.

### 6. Corpus facts kept as tests, and demo assets built from real runs

**Observed:** Aimcurve keeps its full recordings dump out of git and writes
sweep tests that skip when the dump is absent. A small committed set of
fixture files has a README saying what each file pins. The landing page's
sample data is a committed snapshot, and a test fails when the snapshot no
longer matches what the real ingest produces from the sample runs. One
script recaptures the README screenshots from that page.
[README][readme], [preview assets][preview-assets].

**Our baseline:** Corpus measurements behind our proposals come from one-off
scripts under `ignore/scripts/`, which is untracked, and are recorded in the
proposal text. How `docs/screenshots/` is produced was not checked.

**Recommendation:** Optional. A measured fact that shipped behavior depends
on, such as the constants a pace detector relies on, could be held by a test
that skips without the recordings. Such a test runs only on a machine that
has them, so CI never sees it.

## What not to take

- **The browser-only model.** Aimcurve switched its live folder connection
  off on 2026-09-26, and its README tells users to import again after each
  session. Its benchmark design makes no network request at run time, so it
  has no leaderboard positions. Automatic capture, standing, and playlist
  planning are what a local process buys us.
- **A client-side database with migrations.** Aimcurve documents five
  conditions under which a migration drops every imported run. Re-reading
  the stats folder at startup has no equivalent hazard.

## Suggested order

1. Bring finding 1 to PR #329 while its detection design is still open.
2. Reproduce finding 4 before the run-history work depends on run counts
   and medians.
3. Carry finding 3 into the run-history proposal.
4. Consider finding 5 on its own; it is small and separable.
5. Keep finding 2 as a separate investigation, and finding 6 as optional.

## Compared with the Astra survey

The two surveys agree on the main product lessons: show typical recent
performance beside the best, treat within-run analysis as a separate
capability, and give settings comparisons their context.

This survey adds the local check that the Astra survey lists as not done
and recommends: the time-scored signals verified on our recordings, and the
reset and abort shapes counted. It also adds the link to the pace proposal,
the projected-score axis, the Steam link, and the vendor's published
schema.

The Astra survey covers ground this one does not. It inspected the live
demo in a browser, so its notes on connected chart and table selection and
on label legibility are first-hand. It also raises scenario revisions: our
run model groups by name and drops the stats file's `Hash:` line, which
Aimcurve uses to keep versions of a scenario apart.

[scoring]: https://github.com/voidfill/aimcurve/blob/be28be999587888d4d5cb34d69d1fa3dfc1fe6d8/docs/superpowers/specs/2026-09-24-scoring-model-design.md
[perf-format]: https://github.com/voidfill/aimcurve/blob/be28be999587888d4d5cb34d69d1fa3dfc1fe6d8/docs/perf-format.md
[ingest]: https://github.com/voidfill/aimcurve/blob/be28be999587888d4d5cb34d69d1fa3dfc1fe6d8/docs/ingest.md
[run-view]: https://github.com/voidfill/aimcurve/blob/be28be999587888d4d5cb34d69d1fa3dfc1fe6d8/docs/superpowers/specs/2026-09-24-run-view-design.md
[scenario-page]: https://github.com/voidfill/aimcurve/blob/be28be999587888d4d5cb34d69d1fa3dfc1fe6d8/docs/superpowers/specs/2026-09-25-scenario-page-design.md
[readme]: https://github.com/voidfill/aimcurve/blob/be28be999587888d4d5cb34d69d1fa3dfc1fe6d8/README.md
[preview-assets]: https://github.com/voidfill/aimcurve/blob/be28be999587888d4d5cb34d69d1fa3dfc1fe6d8/docs/preview-assets.md
