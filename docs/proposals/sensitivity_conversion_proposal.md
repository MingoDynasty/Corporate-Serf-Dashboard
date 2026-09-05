# Cross-Scale Sensitivity Conversion

Status: Proposed
Date: 2026-09-05

## TL;DR

Runs recorded under a per-game sensitivity scale plot under their raw
number, so an old Valorant run lands at the far left of the Score vs
Sensitivity axis instead of beside the cm/360 value it corresponds to.
Newer stats files carry enough information to convert those runs to cm/360
exactly, using KovaaK's own conversion numbers. This proposal normalizes
sensitivities to cm/360 at the moment a stats file is parsed, so converted
runs sort, group, and display like native cm/360 runs everywhere, the PB
cm/360 column on the playlist pages included. Runs too old to carry the
needed fields keep their original label and are never dropped.

## Decisions needed

Two decisions. Nothing is ratified: the maintainer's position on D1 is
recorded as a lean, which is non-binding and stays open to challenge, and
D2 has no recorded position yet. Two further choices were settled in the
2026-08-03 design conversation at the severity they were made at; they are
restated under "Settled decisions" in Design, and D2 asks whether one of
them extends to a surface that did not exist then.

### D1 — Conversion mechanism: the stats file's `Sens Increment` field, or a formula evaluator over KovaaK's scale definitions

Status: Proposed
Maintainer lean (2026-09-05, non-binding): the increment path.

**Recommended: derive cm/360 from the stats file's own `Sens Increment` and
`DPI` fields.** Every post-2024 stats file records `Sens Increment`, which
is the sensitivity re-expressed in KovaaK's internal base scale (UE4, yaw
0.07°/count; see Verified facts). That makes the conversion
`cm/360 = 360 × 2.54 / (0.07 × increment × DPI)` universal: every scale
KovaaK's supports converts with zero per-scale knowledge, including scales
added in future game updates, and the result is exactly what KovaaK's
itself displays.

**Alternative: a formula evaluator over KovaaK's scale definitions.** The
repository carries `resources/sensitivity converter/response.json`, a
capture of the kovaaks.com `game-settings` endpoint, whose per-scale
`IncrementFormula` entries reproduce KovaaK's UI exactly. This alternative
is not a fixed per-scale yaw table, and the earlier draft of this proposal
was wrong to describe it as one: of the capture's roughly 35 sensitivity
scales, Splitgate, Paladins, and PUBG multiply by the run's FOV (PUBG is
also exponential in the sensitivity), Battlefield V/1/Hardline, GTA 5, and
Battlefield 6 are affine (`a × Sens + b`, so cm/360 is not proportional to
1/Sens), and counts/360 and in/360 invert the sensitivity. A yaw table
converts those scales silently wrong, by far more than the 0.06% Valorant
delta discussed below. Reproducing the capture faithfully needs an
expression evaluator, the run's FOV as an input, a mapping from the stats
file's `Sens Scale` string onto the capture's `ScaleName`, and a refresh
whenever KovaaK's adds a scale. It offers nothing over the increment the
file already records: for every scale in the capture, the recorded
`Sens Increment` is that scale's formula value divided by 0.07.

The risk of the recommended path is reliance on an undocumented stats-file
field. It is mitigated by the field's consistency across every one of the
7,494 files that carry it, by the capture's own UE4 entry
(`IncrementFormula: "Sens * 0.07"`) that explains the divisor structurally,
and by regression fixtures taken from real files (see Testing). Choosing
the alternative means a materially larger implementation plus a dependency
on a capture that goes stale.

### D2 — Trusting recorded DPI now reaches a headline stat

Status: Proposed
Maintainer lean: none recorded.

The 2026-08-03 conversation settled that the DPI a stats file records is
trusted as-is. That ruling was made against one artifact: a mis-grouped
cluster on the Score vs Sensitivity chart. Since then, main added the
sortable PB cm/360 column on the playlist scenarios page, which reads the
same two `RunData` fields this proposal rewrites. Under this proposal the
column fills in for every scenario whose personal best is a converted run:
72 of 866 scenarios today. Four of those PBs are among the 368 runs
misrecorded at 400 DPI and would read 163.4 cm/360, sorting to the extreme
of a user-sortable column (Leapcorn Pure, VT Frogtagon Novice S5, VT
Midrange Long Strafes Novice, VT Midrange Short Strafes Novice).

**Recommended: accept the consequence and keep the escape hatch on the data
side.** The app cannot detect a mismatch between recorded and physical DPI;
any in-app override (a config knob, a per-era DPI map) is a second source
of truth that hides a data error instead of fixing it. The maintainer's own
four cells are fixed by a one-time edit of the `DPI:,400` lines in the 368
files, offered on 2026-08-03 and still open; a beta tester's misrecorded
runs are theirs to fix the same way. Choosing differently means either
keeping the column at `N/A` for converted PBs, which withholds 68 correct
values to hide 4 wrong ones, or building the override.

## Problem

The Score vs Sensitivity plot groups runs by the string
`f"{horizontal_sens} {sens_scale}"`. That string is built in three places:
`load_csv_file_into_database` in `source/kovaaks/data_service.py`, the
watchdog's new-file path in `source/my_watchdog/file_watchdog.py`, and the
plot's `scatter_x` extractor in `source/plot/plot_service.py`. The
per-scenario `sensitivities_vs_runs` container is a `SortedDict` keyed by
`float(key.split(" ")[0])`, the numeric prefix alone, ignoring the scale.
A `0.2 Valorant` run therefore sorts as 0.2 among cm/360 values and renders
as its own category at the far left of the axis, even though it corresponds
to about 40.8 cm/360.

Census of the maintainer's full stats directory (8,064 parseable files,
2026-09-05):

| Scale | DPI in file | Runs | Dates |
|---|---|---|---|
| cm/360 | 1600 | 6,266 | 2025-08 → 2026-08 |
| Valorant | 1600 | 860 | 2024-12 → 2025-08 |
| Valorant | 400 | 368 | 2025-08-12 → 08-16 |
| Valorant | none | 95 | 2020-07 |
| Overwatch | none | 475 | 2019-07 → 2021-07 |

So 15% of all runs (the 1,228 Valorant runs with DPI recorded) are exactly
convertible today, every future run is, and the 570 runs from 2019–2021
predate the fields needed to convert. New runs are all native cm/360, so
the convertible share only improves.

A second, incidental defect: the parser rounds the raw sensitivity to
`sens_round_decimal_places` (configured 1) before keying, so `0.16 Valorant`
and `0.25 Valorant` currently collapse into the `0.2 Valorant` group, and
the two `0.3 Valorant` runs share a group with 95 legacy `0.32 Valorant`
runs. Conversion moves the rounding to the cm/360 result, where one decimal
place is appropriate, and the convertible runs separate correctly: 0.16 →
51.1, 0.25 → 32.7, and 0.3 → 27.2 cm/360, splitting off from the true 0.2
runs at 40.8.

A third consumer appeared after the first draft of this proposal: the
playlist scenarios page's PB cm/360 column (`_personal_best_cm360` in
`source/kovaaks/playlist_scenarios_service.py`) reads `sens_scale` and
`horizontal_sens` from the scenario's personal-best run and shows `N/A`
unless the scale is cm/360. Today 133 of 866 scenarios show `N/A` there;
72 of them have a convertible PB.

Why now: a beta tester has asked for a sensitivity range and a
single-sensitivity view on the same axis (design note in the maintainer's
local `ignore/` directory, 2026-09-01). Both are more coherent once every
post-2024 run sits on one scale, and the mis-sorted Valorant runs are the
kind of outlier that request is about.

## Verified facts

All verified against the live stats directory on 2026-09-05. The
2026-08-03 numbers, independently recomputed by both reviewers of the
earlier draft, reproduce with the corpus growth since.

- Stats files from 2024-12 onward all carry `DPI:` and `Sens Increment:`
  key-value lines; files from 2019–2021 carry neither; no file carries only
  one, and the corpus has no files in between. Counts: 7,494 with both, 570
  with neither.
- `Sens Increment` is the current sensitivity converted into KovaaK's base
  scale, which the capture names UE4 (`IncrementFormula: "Sens * 0.07"`,
  yaw 0.07°/count). All 17 distinct cm/360 `(sens, DPI)` combinations in the
  corpus satisfy `increment = 360 × 2.54 / (0.07 × cm × DPI)`; across 6,266
  cm/360 files the largest deviation is 4.4e-7, consistent with six-decimal
  recording (e.g. 50 cm @ 1600 → 0.163286; 1 cm @ 1600 → 8.164286, which
  pins the base yaw to 0.07 exactly). The capture's own cm/360 entry,
  `IncrementFormula: "2.54 * 360 / (Sens * DPI)"`, divided by 0.07 is this
  formula.
- For game scales the increment is DPI-independent, as the model predicts
  and as the capture's game formulas, which carry no DPI term, require:
  `0.2 Valorant` records 0.199886 at both 400 and 1600 DPI.
- KovaaK's internal Valorant yaw is 0.06996°/count (increment/sens is
  0.99943 across all five Valorant sensitivities in the corpus), not the
  community-standard 0.07. The capture's Valorant entry records
  `IncrementFormula: "Sens * 0.06996"` and
  `InchesFormula: "360 / (Inches * 0.06996 * DPI)"`, corroborating the
  corpus measurement. The difference is 0.06%, invisible at one decimal
  place, but it means the increment path reproduces KovaaK's own numbers
  while a community yaw table would not.
- The already-normalized scales convert correctly under the same formula:
  in/360 (`360 / (Sens * DPI)`) yields 2.54 × Sens cm, and counts/360
  (`360 / Sens`) yields 2.54 × Sens / DPI cm. The corpus contains neither;
  the claim is algebraic and is pinned by a synthetic fixture (see Testing).
- The yaw model originates from KovaaK's own tooling
  (github.com/KovaaK/SensitivityMatcher); community references list
  Valorant 0.07 and Overwatch 0.0066.
- The 368 runs recorded at DPI 400 (2025-08-12 → 08-16) are a KovaaK's
  settings mistake; the mouse was physically at 1600 DPI. See D2 and
  Settled decisions.
- Personal bests: of 866 scenarios with local runs, 733 already have a
  cm/360 PB, 72 have a convertible PB (4 of them from the 400-DPI window),
  and 61 have a legacy PB that stays `N/A`.

## Design

Normalization happens in one place: `extract_data_from_file` in
`source/kovaaks/data_service.py`, which already parses `Sens Scale:` and
`Horiz Sens:`. It additionally reads `DPI:` and `Sens Increment:` and then:

- `sens_scale == "cm/360"` → keep the value as today (no DPI needed).
- Any other scale, with `increment > 0` and `DPI > 0` present →
  `cm = 360 × 2.54 / (0.07 × increment × DPI)`, rounded to
  `sens_round_decimal_places`; store `horizontal_sens = cm`,
  `sens_scale = "cm/360"`.
- Otherwise (either field missing, empty, zero, or malformed) → keep the
  original value and scale exactly as today, raw-sensitivity rounding
  included. `DPI` and `Sens Increment` must **not** join the parser's
  required-field check: legacy files lack them and must still load, and a
  malformed value costs the conversion, never the run.

Everything downstream inherits the normalization: the three
sensitivity-key builders, the `SortedDict` ordering, the plot axis and
hover, run notifications, and the PB cm/360 column all consume
`RunData.horizontal_sens` / `RunData.sens_scale`. `RunData`'s shape is
unchanged; the original scale value is not retained in v1 (see Future). The
run database is in-memory and rebuilt from the stats directory at every
start, so historical runs convert retroactively on the next launch and the
choice is fully reversible: there is no cache to invalidate or migrate.

The one code change outside the parser is a comment: `_personal_best_cm360`
in `playlist_scenarios_service.py` states that local CSVs expose cm/360
only when the run was recorded on that scale. Conversion removes exactly
that invariant, so the comment is rewritten to say the value is cm/360
natively or by conversion and stays unknown only for legacy runs. The
function body needs no change.

### Observable behavior changes

The complete list; anything not here is a defect of the implementation.

1. Converted runs join the cm/360 axis at their converted value. A
   converted group whose rounded value coincides with a native cm/360 group
   merges with it (intended).
2. The 0.16, 0.25, and 0.3 Valorant runs leave the rounded 0.2 and 0.3
   groups for their own correctly placed cm/360 groups. The rounding fix is
   not universal: the fallback branch keeps today's raw-sensitivity
   rounding, so the 95 legacy 0.32 Valorant runs still display as
   `0.3 Valorant` (consistent with Settled decisions).
3. PB cm/360 on the playlist scenarios page reads a number for the 72
   scenarios whose PB is a converted run, and `N/A` still for the 61 whose
   PB is a legacy run. Four of the 72 read 163.4 (D2).
4. Run notification text renders a converted run's sensitivity as e.g.
   `40.8 cm/360` instead of `0.2 Valorant`; the notification contract itself
   is unchanged.

### Spec statements to update (PR 2)

- `docs/specs/scenario_performance.md`, "The graph": add the normalization
  rule as a statement (parse-time conversion, its two inputs, the legacy
  fallback), linking the decision-log entry PR 2 writes. This is the home
  because the axis is the primary consumer; a separate run-ingest spec for
  one rule is not warranted (author's call).
- `docs/specs/playlists.md`: "PB cm/360 is known only when the PB run used
  the cm/360 scale" becomes "PB cm/360 is known when the PB run's
  sensitivity is in cm/360, natively or by conversion; a legacy run without
  DPI and increment keeps `N/A`", linking the same entry.
- `docs/specs/notifications.md`: no statement changes; the `{sensitivity}`
  placeholder's value changes, its contract does not.

### Copy

None. No user-facing string is added or edited. Strings whose rendered
value changes without editing: the Score vs Sensitivity axis categories and
hover x value, the run toast's `{sensitivity}` placeholder, and the PB
cm/360 cell (`N/A` → a number). The PB cm/360 header tooltip ("Mouse
sensitivity of your personal-best run, in centimeters of mouse travel per
full 360-degree turn (higher = lower sensitivity).") stays accurate for
converted runs and is unchanged.

### Settled decisions

Ratified by the maintainer in the 2026-08-03 design conversation:

- **Legacy runs keep their original label.** The 570 DPI-less runs from
  2019–2021 stay grouped under e.g. `5.0 Overwatch`: data is never excluded
  because the DPI is unknown, and no legacy-DPI config knob is added.
- **Recorded DPI is trusted as-is, on the chart.** KovaaK's DPI field is
  whatever the user typed into KovaaK's settings; a mismatch with the
  mouse's physical DPI is undetectable from the data. The known instance,
  368 Valorant runs misrecorded at 400 DPI converting to about 163.4 cm/360
  instead of about 40.8, is accepted as a chart-grouping artifact. Whether
  the same acceptance extends to the PB cm/360 column is D2.

## Out of scope

- **A numeric (linear) x-axis.** The axis stays categorical; conversion
  fixes ordering and grouping, which is the ask. Proportional spacing is an
  independent, pre-existing question.
- **A sensitivity range or single-sensitivity filter** on the chart. The
  beta-tester request is a separate design; this proposal only makes the
  axis it would filter single-scale for post-2024 runs.
- **In-app correction of misrecorded DPI** (config overrides, per-era DPI
  maps). See D2 and Settled decisions.
- **Vertical sensitivity.** The app already reads only `Horiz Sens`.

## Testing

- Unit tests for the conversion, with fixtures taken from real corpus
  files: cm/360 identity; `0.2 Valorant` @ 1600 → 40.8; the same increment
  @ 400 → 163.4; `0.16` @ 1600 → 51.1 and `0.25` @ 1600 → 32.7, separating
  from 40.8. Rounded expectations alone cannot pin the mechanism: a
  community-yaw (0.07) computation from the raw sensitivity differs from
  the increment-derived value by only 0.06%, which one-decimal rounding
  hides. So fixtures also assert the unrounded value (increment 0.199886 @
  1600 → ≈40.8447) at a relative tolerance of 1e-5, an order of magnitude
  below that delta; a regression that silently recomputes from raw
  sensitivity with community constants lands a relative 5.7e-4 away and
  fails.
- Fallback coverage: missing DPI, missing increment, empty, zero, and
  malformed values each keep the original label and rounding; legacy files
  still parse (the new fields never join the required-field check).
- A cross-check test asserting the increment-derived result matches the
  capture's Valorant `InchesFormula`, `360 / (Inches * 0.06996 * DPI)`,
  within the precision of the six-decimal increment field, documenting the
  field's semantics as an executable invariant with KovaaK-sourced
  provenance.
- Synthetic fixtures for in/360 and counts/360, derived from the capture's
  formulas, pinning the "already-normalized scales convert correctly" claim
  (the corpus has no such runs).
- `tests/test_playlist_scenarios_service.py`: a converted-PB case asserting
  a numeric PB cm/360, beside the existing legacy case that keeps `N/A`.
- Existing parser/grouping tests updated where labels change.
- Standard gates (ruff format, ruff check, mypy, pytest, compileall).

## Delivery plan

1. **PR 1 — this proposal**, with the `docs/proposals/` convention it
   inaugurates. No code.
2. **PR 2 — implementation.** Gated on D1 and D2 flipping to Ratified.
   Parser change and tests; the `_personal_best_cm360` comment rewrite; the
   two spec statement updates above; a decision-log entry carrying the
   `Sens Increment` / `DPI` field semantics and the empirical invariant
   (they become relied-upon fields), which the specs link;
   `docs/kovaaks_api_notes.md` gains the `game-settings` endpoint as the
   source of the in-repo capture (the earlier draft put the field semantics
   there too; the API notes document endpoints, so the semantics live in
   the decision-log entry instead); then the full shipping checklist:
   proposal deletion, roadmap, product inventory.

Single implementation PR; the blast radius is one parser function, one
comment, tests, and docs. Recommended kickoff: Opus 5 at high effort. The
spec is complete and the change is mechanical once D1 and D2 are ruled, so
more model capacity would not improve the PR.

Optional, outside the repo: the one-time script that rewrites the
`DPI:,400` lines in the 368 misrecorded files (see D2), run by the
maintainer against the live stats directory.

## Future / optional

- Preserve the original scale value on `RunData` and show it in plot hover
  (e.g. `40.8 cm/360 (0.2 Valorant @ 1600)`). Cheap, but adds fields and
  display variance; deliberately not in v1. Reversible at any time since
  the source files are the system of record.

## Provenance

This document supersedes the 2026-08-03 draft reviewed on PR #197, which
was parked as `Future` and closed unmerged in favor of this one. Its
evidence and settled decisions carry over; the reviews' findings are folded
in: the PB cm/360 consumer and its census (gpt-5.6-sol, 2026-08-12), the
corrected D1 alternative and the UE4, in/360, and counts/360
corroborations (claude-opus-5, 2026-08-08, confirmed 2026-08-12), the third
key builder, and the non-universal rounding fix. All numbers were
re-verified on 2026-09-05.
