# Cross-Scale Sensitivity Conversion

Status: Proposed
Date: 2026-08-03

## TL;DR

Runs recorded under per-game sensitivity scales plot under their raw number,
so an old Valorant run lands at the far left of the Score vs Sensitivity axis
instead of beside the cm/360 value it actually corresponds to. Newer stats
files carry enough information to convert those runs to cm/360 exactly, using
KovaaK's own conversion numbers. This proposal normalizes sensitivities to
cm/360 at the moment a stats file is parsed, so converted runs sort, group,
and display like native cm/360 runs everywhere. Runs too old to carry the
needed fields keep their original label and are never dropped.

## Decisions needed

### D1 — Conversion mechanism: KovaaK's `Sens Increment` field vs. a maintained yaw table

Status: Proposed

**Recommended: derive cm/360 from the stats file's own `Sens Increment` and
`DPI` fields.** Every post-2024 stats file records `Sens Increment`, which is
empirically the sensitivity re-expressed in KovaaK's internal base scale
(yaw 0.07°/count — see Verified facts). That makes the conversion
`cm/360 = 360 × 2.54 / (0.07 × increment × DPI)` universal: every sens scale
KovaaK's supports, including ones added in future game updates, converts with
zero per-game knowledge, and the result is exactly what KovaaK's itself would
display. The alternative — porting the per-game yaw table from KovaaK's
SensitivityMatcher project — supports only the scales we hardcode, makes us
the owner of each constant's provenance, and provably disagrees with KovaaK's
in-game numbers in the fourth significant digit (KovaaK's internal Valorant
yaw is 0.06996, not the community's 0.07). Choosing the table instead means
new-scale support requires a code change each time and the converted values
differ from what the KovaaK's UI shows the user; the risk of the recommended
path is reliance on an undocumented field, mitigated by its perfect
consistency across 7,413 real files and by regression fixtures taken from
those files.

## Problem

The Score vs Sensitivity plot keys runs by the string
`f"{horizontal_sens} {sens_scale}"` (built in `source/kovaaks/data_service.py`
and again in `source/my_watchdog/file_watchdog.py`), and
`sensitivities_vs_runs` is a `SortedDict` ordered by
`float(key.split(" ")[0])` — the numeric prefix alone, ignoring the scale. A
`0.2 Valorant` run therefore sorts as 0.2 among cm/360 values and renders as
its own category at the far left of the axis, even though it corresponds to
~40.8 cm/360.

Census of the maintainer's full stats directory (7,983 parseable files,
2026-08-03):

| Scale | DPI in file | Runs | Dates |
|---|---|---|---|
| cm/360 | 1600 | 6,185 | 2025-08 → now |
| Valorant | 1600 | 860 | 2024-12 → 2025-08 |
| Valorant | 400 | 368 | 2025-08-12 → 08-16 |
| Valorant | none | 95 | 2020-07 |
| Overwatch | none | 475 | 2019-07 → 2021-07 |

So 15% of all runs (the 1,228 Valorant runs with DPI recorded) are exactly
convertible today, and every future run is, while the 570 runs from 2019–2021
predate the fields needed to convert.

A second, incidental defect: the parser rounds the raw sensitivity to
`sens_round_decimal_places` (configured 1) before keying, so `0.16 Valorant`
and `0.25 Valorant` currently collapse into the `0.2 Valorant` group.
Conversion moves the rounding to the cm/360 result, where one decimal place
is appropriate, and those runs separate correctly (51.1 vs 40.8 cm/360).

## Verified facts

All verified against the live stats directory on 2026-08-03:

- Stats files from 2024-12 onward all carry `DPI:` and `Sens Increment:`
  key-value lines; files from 2019–2021 carry neither; the corpus has no
  files in between.
- `Sens Increment` is the current sensitivity converted into a base scale
  with yaw exactly 0.07°/count. All 17 distinct cm/360 `(sens, DPI)`
  combinations in the corpus satisfy
  `increment = 360 × 2.54 / (0.07 × cm × DPI)` to all six recorded decimals
  (e.g. 50 cm @ 1600 → 0.163286; 1 cm @ 1600 → 8.164286, which pins the base
  yaw to 0.07 exactly).
- For game scales the increment is DPI-independent, as the model predicts:
  `0.2 Valorant` records 0.199886 at both 400 and 1600 DPI.
- KovaaK's internal Valorant yaw is 0.06996°/count (increment/sens is
  0.99943 across all four Valorant sens values in the corpus), not the
  community-standard 0.07. The difference is 0.06% — invisible at one
  decimal place — but it means the increment path reproduces KovaaK's own
  numbers while a community yaw table would not.
- The yaw model and per-game constants originate from KovaaK's own
  SensitivityMatcher project (github.com/KovaaK/SensitivityMatcher);
  community references list Valorant 0.07 and Overwatch 0.0066.
- The 368 runs recorded at DPI 400 (2025-08-12 → 08-16) are a KovaaK's
  settings mistake — the mouse was physically at 1600 DPI. See Settled
  decisions.

## Design

Normalization happens in one place: `_get_data_from_csv_file` in
`source/kovaaks/data_service.py`, which already parses `Sens Scale:` and
`Horiz Sens:`. It additionally reads `DPI:` and `Sens Increment:` and then:

- `sens_scale == "cm/360"` → keep the value as today (no DPI needed).
- Any other scale, with `increment > 0` and `DPI > 0` present →
  `cm = 360 × 2.54 / (0.07 × increment × DPI)`, rounded to
  `sens_round_decimal_places`; store `horizontal_sens = cm`,
  `sens_scale = "cm/360"`.
- Otherwise (either field missing, zero, or malformed) → keep the original
  value and scale exactly as today. `DPI` and `Sens Increment` must **not**
  join the parser's required-field check — legacy files lack them and must
  still load.

Everything downstream inherits the normalization for free: both
`sensitivity_key` builders, the `SortedDict` ordering, the plot axis and
hover, and run notifications all consume `RunData.horizontal_sens` /
`RunData.sens_scale`. No other code changes. `RunData`'s shape is unchanged;
the original scale value is not retained in v1 (see Future). The run
database is in-memory and rebuilt from the stats directory at every start,
so historical runs convert retroactively on the next launch and the choice
is fully reversible — there is no cache to invalidate or migrate.

Observable behavior change beyond the intended one: the `0.16`/`0.25`
Valorant runs currently lumped into `0.2 Valorant` separate into their own
correctly-placed cm/360 groups, and converted groups whose rounded cm/360
value coincides with a native cm/360 group merge with it (intended).

### Settled decisions

Ratified by the maintainer in the 2026-08-03 design conversation:

- **Legacy runs keep their original label.** The 570 DPI-less runs from
  2019–2021 stay grouped under e.g. `5.0 Overwatch` — data is never excluded
  because the DPI is unknown, and no legacy-DPI config knob is added.
- **Recorded DPI is trusted as-is.** KovaaK's DPI field is whatever the user
  typed into KovaaK's settings; a mismatch with the mouse's physical DPI is
  undetectable from the data. The known instance — 368 Valorant runs
  misrecorded at 400 DPI, converting to ~163.4 cm/360 instead of ~40.8 —
  is accepted. The escape hatch is fixing the data, not the app: a one-time
  edit of the `DPI:,400` lines in those files, at the maintainer's option.

## Out of scope

- **A numeric (linear) x-axis.** The axis stays categorical; conversion
  fixes ordering and grouping, which is the ask. Proportional spacing is an
  independent, pre-existing question.
- **In-app correction of misrecorded DPI** (config overrides, per-era DPI
  maps). See Settled decisions.
- **Vertical sensitivity.** The app already reads only `Horiz Sens`.

## Testing

- Unit tests for the conversion, with fixtures taken from real corpus files:
  cm/360 identity; `0.2 Valorant` @ 1600 → 40.8; the same increment @ 400 →
  163.4; missing DPI, missing increment, and zero values each fall back to
  the original label; legacy files still parse (fields stay optional).
- A cross-check test asserting the increment-derived result for the corpus's
  Valorant fixtures agrees with the community-yaw computation
  (`360/(0.07 × sens)/DPI × 2.54`) within 0.1%, documenting the field's
  semantics as an executable invariant.
- Existing parser/grouping tests updated where labels change.
- Standard gates (ruff format, ruff check, mypy, pytest, compileall).

## Delivery plan

1. **PR 1 — this proposal.** No code.
2. **PR 2 — implementation.** Gated on D1 flipping to Accepted. Parser
   change + tests, `docs/kovaaks_api_notes.md` gains the `Sens Increment` /
   `DPI` field semantics and the empirical invariant (they become
   relied-upon fields), plus the full shipping checklist: decision-log
   distillation, proposal deletion, roadmap and product inventory updates.

Single implementation PR; the blast radius is one parser function plus
tests and docs.

## Future / optional

- Preserve the original scale value on `RunData` and show it in plot hover
  (e.g. `40.8 cm/360 (0.2 Valorant @ 1600)`). Cheap, but adds fields and
  display variance; deliberately not in v1. Reversible at any time since
  the source files are the system of record.
