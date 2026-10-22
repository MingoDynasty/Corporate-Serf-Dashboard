# 2026-10-18: Scenario Stats Shows The Newest Typical Score At Any Age

Status: Accepted

Scenario Stats shows the value after the selected scenario's newest run.
An old value remains useful when the card shows how much recent support it has.
The hover explains the runs behind the figure so the player can inspect what it represents.

**Ruling and amendments.** TS5 of [proposal #382](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/382), ratified 2026-10-18 at [951d1c2](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/commit/951d1c2). TS6 replaces its carried-value and `as of` treatment with a current recency test, and TS8 replaces the ordinary line after Category with a lead number. Both amendments were ruled 2026-10-20. This entry records the surviving choice; [TS8](2026-10-20-scenario-stats-leads-with-the-typical-score.md) sets the layout. Delivered in #401.

**Contract.** Use the same pure definition as the chart's last point over one whole-store snapshot, with the scenario's runs and sessions taken from that copy. Judge recency as of the app's own current local clock. Update on a selected-scenario run, scenario changes and the page's existing 30-second interval, so a value dims within 30 seconds of its recency test failing. Unchanged rendered children and readout return `no_update`, preserving a held tooltip. No card-specific interval or persisted score is added.

The lead's hover gives its median's supporting count, actual run and session counts with short dates, the number from the last 30 days, and both percentile bands regardless of chart switches. It says `your last {n} runs` only when more runs exist outside the window, and `your {n} runs` otherwise. Bold labels include their colons: `Runs:`, `Recent:`, `Middle 50%:` and `Middle 80%:`. One date reads `on {date}` and only a date outside the current year shows a year. Singular counts use `run` and `session`. Below the minimum, the hover gives the existence rule and the actual run/session counts; that rule has no age limit.

**Why keep old values.** Hiding a known value would discard useful information about past play. Recency and supporting dates disclose its limits rather than equating old with weak. A new feature using the figure still chooses its own evidence bar before judging skill.

Current card states and update behavior are in [Run History](../../specs/run_history.md#scenario-stats).
