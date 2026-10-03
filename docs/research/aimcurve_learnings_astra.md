# Lessons from Aimcurve

Date: 2026-10-01

Research note; recommendations remain unratified.

## Takeaway

Aimcurve makes two useful distinctions: personal best versus typical recent
performance, and a run's final result versus where that result was gained or
lost. Recent-form tracking and connected chart/table selection fit our planned
run-history work. Detailed within-run analysis deserves a separate investigation
because our current run model does not retain the events it needs.

## Evidence and scope

- Inspected the [live sample demo](https://voidfill.github.io/aimcurve/#/about)
  and relevant source and design documents on 2026-10-01.
- Aimcurve source snapshot:
  [`be28be9`](https://github.com/voidfill/aimcurve/tree/be28be999587888d4d5cb34d69d1fa3dfc1fe6d8).
  External source links below are pinned to this revision. The deployed demo
  was inspected separately; its build revision was not established.
- Compared against this checkout at `161b2cd34b9ac59559e41e2c57016e74f875268f`,
  particularly [product framing](../product.md),
  [Scenario Performance](../specs/scenario_performance.md),
  [the roadmap](../roadmap.md),
  [the run-history proposal](../proposals/run_history_proposal.md), and
  [the current run model](../../source/kovaaks/data_models.py).
- This was product research with targeted source inspection. We did not import
  the user's recordings, run Aimcurve's test suite, or independently reproduce
  its file-format measurements.

## Findings

### 1. Show recent form alongside personal bests

**Observed:** Aimcurve's sample progression chart shows every completed run,
a best-so-far staircase, and a rolling median of the last ten runs. Its
calculation uses the available values before the window fills and exposes
whether the window is full; missing values are not zeroes.
[Calculation source](https://github.com/voidfill/aimcurve/blob/be28be999587888d4d5cb34d69d1fa3dfc1fe6d8/src/lib/scenario/series.ts).

**Our baseline:** Score vs Time keeps the top N scores per day and averages
those retained scores. That describes the stronger runs, while typical recent
performance requires a different selection of data.

**Recommendation:** Consider a recent-form view over all completed runs,
alongside the PB. It should make progress such as "my usual performance is
approaching my old PB" visible even when no new record has landed. Calculate
it before any top-N display filtering. Ten runs is Aimcurve's choice, not a
settled requirement for us; window size, sample counts, and how to express
spread remain design questions.

### 2. Explain where performance was lost within a run

**Observed:** The demo compares a run's pace with its previous PB, showing a
mid-run lead that becomes a loss by the finish. A per-bot table breaks down
the difference. Selecting a bot row focused the corresponding portion of the
chart in the browser.
[Run-view design](https://github.com/voidfill/aimcurve/blob/be28be999587888d4d5cb34d69d1fa3dfc1fe6d8/docs/superpowers/specs/2026-09-24-run-view-design.md).

**Opportunity:** Help the player identify the encounter or stretch of a run
worth examining. This adds information that a final score and whole-run
accuracy cannot supply. A slowdown is evidence of where performance changed;
it does not establish a cause such as fatigue or poor technique.

**Cost and boundary:** This would require additional parsing and retained
data from per-kill CSV details and optional `.perf` events. Different scoring
models need different comparisons; Aimcurve explicitly distinguishes timed
score accumulation from completion-time races and can report an unsupported
case. Treat this as a separate capability, evaluated on completed runs.
[Scoring classification](https://github.com/voidfill/aimcurve/blob/be28be999587888d4d5cb34d69d1fa3dfc1fe6d8/src/lib/scoring/classify.ts).

### 3. Give sensitivity comparisons their context

**Verified in source:** Aimcurve groups settings using sensitivity scale,
horizontal and vertical sensitivity, DPI, FOV, and FOV scale. Its table shows
run counts, best, median, and last used. The caption acknowledges that later
settings have more practice behind them, so the comparison does not isolate
the setting's effect.
[Grouping](https://github.com/voidfill/aimcurve/blob/be28be999587888d4d5cb34d69d1fa3dfc1fe6d8/src/lib/scenario/config.ts),
[table and caption](https://github.com/voidfill/aimcurve/blob/be28be999587888d4d5cb34d69d1fa3dfc1fe6d8/src/components/ConfigTable.vue).

**Recommendation:** Consider sample counts, typical scores, and when each
sensitivity was used alongside our existing cm/360 normalization. These would
help users assess comparisons between settings tested at different times or
with very different amounts of practice. Adopting their full grouping key
would be a separate decision: our model does not currently retain all of it.

### 4. Connect tables and charts

**Observed:** A bot row acts as a handle for inspecting the chart. Aimcurve's
scenario design and settings-table source also connect settings groups with
highlighted runs on the progression chart.
[Scenario design](https://github.com/voidfill/aimcurve/blob/be28be999587888d4d5cb34d69d1fa3dfc1fe6d8/docs/superpowers/specs/2026-09-25-scenario-page-design.md).

**Recommendation:** In our run history, selecting a row could highlight its
point and expose its details; selecting a sensitivity could highlight the
associated history. Work out the navigation and selection behavior within the
existing run-history proposal, which already owns the page-space question.
This observation does not settle the choice of page, panel, or layout.

### 5. Demonstrate value before setup

**Observed:** Aimcurve's landing page offers interactive sample data without
requiring an import. Sections introduce a player question, then show the
evidence. The inspected sample includes both within-run comparison and
longer-term progression.
[README and demo description](https://github.com/voidfill/aimcurve/blob/be28be999587888d4d5cb34d69d1fa3dfc1fe6d8/README.md).

**Recommendation:** Consider a small public demonstration of our sensitivity
comparison and benchmark planning. The useful visual lessons are clear
hierarchy, an emphasized comparison, and nearby supporting detail. Some of
Aimcurve's small, muted labels were harder to read at a glance; our
second-monitor use calls for stronger legibility. A public demo is separable
from the run-history work.

### 6. Establish comparability before interpreting trends

**Verified in source:** Aimcurve queries progression by scenario version
hash and uses completed-run views. Its ingestion notes describe incomplete
attempts, mismatched CSV/performance timestamps, and valid older CSV-only
runs. A missing `.perf` therefore cannot by itself invalidate a run.
[Scenario queries](https://github.com/voidfill/aimcurve/blob/be28be999587888d4d5cb34d69d1fa3dfc1fe6d8/src/lib/scenario/queries.ts),
[ingestion findings](https://github.com/voidfill/aimcurve/blob/be28be999587888d4d5cb34d69d1fa3dfc1fe6d8/docs/ingest.md),
[performance-format findings](https://github.com/voidfill/aimcurve/blob/be28be999587888d4d5cb34d69d1fa3dfc1fe6d8/docs/perf-format.md).

**Recommendation:** Investigate scenario revisions and incomplete-attempt
handling before promising stronger trend verdicts. Our current run model
groups scenarios by name and does not retain the scenario hash. Determine
whether that creates material comparison problems in our recordings before
designing a change.

Their measurements are useful leads, not universal guarantees. Reproduce
the relevant cases across our supported file versions and recording settings,
especially pairing, reset detection, and assumptions about file writes.

## Suggested order

1. Explore recent-form tracking within the planned per-scenario run history,
   with explicit completed-run and comparison semantics.
2. Design connected history-row and chart-point selection as part of that
   same feature.
3. Consider richer sensitivity context after establishing which extra fields
   are needed and what question each would answer.
4. Investigate within-run analysis separately, using representative CSV and
   `.perf` pairs before committing to a product design.

A public sample demo can be considered independently. Automatic capture,
normalized sensitivity comparisons, and playlist/benchmark planning remain
useful foundations. These ideas do not require choosing Aimcurve's framework
or browser database; the existing run-history proposal already supports its
first views using our current run store.

## Questions for the next design pass

- What should recent form mean: the last N completed runs, a time window, or
  a session summary? How should sparse history and settings changes read?
- How can top-N comparison and typical-performance analysis coexist without
  making their different populations ambiguous?
- Which scenario revisions and incomplete attempts occur in our supported
  recordings, and how should their histories be presented?
- Which per-kill and performance events are available reliably enough to
  support a useful first within-run view?
- Which interaction lets a player move between a run, its history, and the
  current session without losing their place?

This note records the research and proposed priorities. Feature direction
remains subject to the proposal process.
