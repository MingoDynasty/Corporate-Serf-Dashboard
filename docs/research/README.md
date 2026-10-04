# Research

Retained research that can inform future product and engineering work. These
notes preserve sources, observations, and recommendations; their inclusion
here does not approve a feature or establish current app behavior.

## Surveys

| App | Survey date | Focus |
| --- | --- | --- |
| [Aimcurve (Astra)](aimcurve_learnings_astra.md) | 2026-10-01 | Recent form, within-run analysis, settings comparisons, and connected chart/table interactions |
| [Aimcurve (Opus)](aimcurve_learnings_opus.md) | 2026-10-03 | Time-scored detection from `.perf` files, checked against local recordings; reset-file handling; scenario-history design |
| [RefleK's](refleks_learnings.md) | 2026-07-03 | Additional run data, API observations, sessions, and analytics ideas |

## More than one survey of an app

Two models may survey the same app independently, and each survey then keeps
its own file. The file name ends in the model's short name, as in
`aimcurve_learnings_astra.md`. The surveys are not merged: where they differ,
the difference is evidence for the design that uses them. A later survey may
close with a short comparison against an earlier one.

A survey written by a model names it on an `Author:` line under the date, as
`Author: <model-id> · effort: <level>`. That is the canonical model ID and
the effort of the session that wrote the survey, so a reader can weigh two
surveys of one app.

## Where a note belongs

- Keep reusable research here, with the survey date, source revision when
  available, and clear separation between observations and recommendations.
- Keep feature-specific experiments and working notes in
  `ignore/design-notes/`, following the [scratch routing rules](../../ignore/README.md).
- Develop a concrete design under `docs/proposals/`, following the
  [proposal guidance](../../AGENTS.md#documentation-habits).
- Record adopted decisions in [the decision log](../decision_log.md) and
  shipped behavior in `docs/specs/`.

Surveys describe the projects as inspected on their recorded dates. Statements
about our app and suggested next steps may become outdated as either project
changes; verify them against current behavior before using them in a design.
