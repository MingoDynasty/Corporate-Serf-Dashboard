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
| [RefleK's (Opus)](refleks_learnings_opus.md) | 2026-10-28 | A whole-session read and a time-spent calendar for open questions; one clock for kills and `.perf` events, with the kill table's shapes across game versions; API-note gaps; and what not to take: default run upload and training advice |
| [KovaaK's Companion (Opus)](kovaaks_companion_learnings_opus.md) | 2026-10-28 | A SteamID64-to-username lookup checked live, each benchmark's overall-rank rule in data we already bundle, an advice engine and its author's review of why advice misleads, server scores, and sessions as game launches |

## Checks of this app

A check records what was measured on this app's own build, where a survey
looks at another app.

| Check | Date | Focus |
| --- | --- | --- |
| [The Run History page's run list under NVDA](run_history_list_nvda_walk.md) | 2026-10-13, 2026-10-14 | What NVDA said on the built run list in Firefox, Chrome, and Edge, against the five tasks the page's proposal names and the eight the All scenarios tree adds, and what still does not work |

## Checks of KovaaK's

A check of KovaaK's records what the game itself writes to disk, measured on
the recorded game version.

| Check | Date | Focus |
| --- | --- | --- |
| [Detecting a scenario switch from KovaaK's files](kovaaks_scenario_switch_signals.md) | 2026-10-25 | Whether the app can tell which scenario is loaded before its first run lands: the analytics log names it, but the game writes that log in 4 KB batches, so the answer comes seconds to minutes late. Two other candidates stay untested |
| [The analytics log as a source for restarts](kovaaks_analytics_log_restarts.md) | 2026-10-25 | What the game's analytics log records about restarts and finished runs, how far it can be trusted, and what an app feature would need |

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
- Record adopted decisions in [the decision log](../decision_log/README.md) and
  shipped behavior in `docs/specs/`.

Surveys describe the projects as inspected on their recorded dates. Statements
about our app and suggested next steps may become outdated as either project
changes; verify them against current behavior before using them in a design.
