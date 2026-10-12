# 2026-09-11: Sensitivities Normalize To cm/360 At Parse Time From The File's Own Increment And DPI

Status: Accepted

Runs from older stats files were plotted under whatever sensitivity number
the game they were played on used, so a Valorant-era run sat at the far left
of the sensitivity axis instead of next to the centimeters it actually
equals. Those runs are now converted to cm/360 the moment their file is read,
using two fields KovaaK's has written into every stats file since 2024. They
sort, group, and earn run notifications exactly like runs recorded in cm/360,
and the playlist tables' PB cm/360 column fills in for them. Runs from 2019
to 2021, whose files predate those fields, keep their original label and are
never dropped.

**The conversion, and where it runs.** `extract_data_from_file` in
`source/kovaaks/data_service.py` reads the stats file's `Sens Increment:` and
`DPI:` lines alongside the `Sens Scale:` and `Horiz Sens:` it already read,
and after the key-value loop computes
`cm/360 = 360 x 2.54 / (0.07 x increment x DPI)`, rounded to
`sens_round_decimal_places`, storing it as `horizontal_sens` with
`sens_scale` set to `cm/360`. It runs after the loop and not inline because
`DPI:` follows `Horiz Sens:` in the file, so the inputs are only complete
once the whole tail has been read. A run already on the cm/360 scale keeps
its recorded value untouched. A run missing either field, or carrying one the
conversion cannot use, keeps its original value and scale. "Cannot use" is
wider than "not a number": empty, zero, and negative, but also the non-finite
values `float()` accepts (`inf`, `nan`), magnitudes that make
`0.07 x increment x DPI` underflow to zero or overflow to infinity, and a
conversion that rounds away to zero at the configured precision. The rounding
happens inside the same guard that validates, so the value checked is the
value stored and no gap between them can record a false `0.0 cm/360`. Neither
field joins the parser's required-field check: legacy files lack them and
must still load, and an unusable value costs the conversion, never the run --
and never the startup scan, which has no guard of its own around the parser.
Normalizing here means every consumer inherits it with no change of its
own -- the three sensitivity-key builders, the `SortedDict` ordering, the
plot axis and hover, run notifications, and the PB cm/360 column all read
`RunData.horizontal_sens` and `RunData.sens_scale`. `RunData`'s shape is
unchanged, so the original scale value is not retained. The run database is
in-memory and rebuilt from the stats directory at every start, so historical
runs convert retroactively on the next launch and the choice is fully
reversible: there is no cache to invalidate or migrate.

**What `Sens Increment` and `DPI` mean.** These are now relied-upon fields,
so their semantics are recorded here. `Sens Increment` is the run's
sensitivity re-expressed in KovaaK's internal base scale, which
`resources/sensitivity converter/response.json` names UE4
(`IncrementFormula: "Sens * 0.07"`, yaw 0.07 degrees per mouse count),
whatever per-game scale the run was played on. The empirical invariant, over
the 7,494 corpus files that carry the field: the recorded increment equals
that scale's own formula value divided by 0.07. All 17 distinct cm/360
`(sens, DPI)` combinations satisfy
`increment = 360 x 2.54 / (0.07 x cm x DPI)` with a largest deviation of
4.4e-7 across 6,266 files, consistent with six-decimal recording, which pins
the base yaw to 0.07 exactly. For game scales the increment carries no DPI
term and is DPI-independent, as the capture's game formulas require:
`0.2 Valorant` records `0.199886` at both 400 and 1600 DPI. The
already-normalized scales fall out of the same formula: in/360
(`360 / (Sens * DPI)`) yields `2.54 x Sens` cm and counts/360
(`360 / Sens`) yields `2.54 x Sens / DPI` cm. `DPI` is whatever the user
typed into KovaaK's settings, not a measurement.

**KovaaK's Valorant yaw is 0.06996, not the community 0.07.** The capture's
Valorant entry records `IncrementFormula: "Sens * 0.06996"` and
`InchesFormula: "360 / (Inches * 0.06996 * DPI)"`, and the corpus measurement
agrees (increment/sens is 0.99943 across all five Valorant sensitivities).
The difference is 0.06%, invisible at one decimal place, but it means the
increment path reproduces KovaaK's own displayed numbers where a
community-yaw table would not. Rounded test expectations alone cannot pin
this, so the parser tests also assert the unrounded value at `rel=1e-5`: a
regression that recomputes from the raw sensitivity with the community
constants lands a relative 5.7e-4 away and fails.

**Rejected: a formula evaluator over KovaaK's scale definitions.** The
alternative was to evaluate the capture's per-scale `IncrementFormula`
entries directly. Of its roughly 35 scales, Splitgate, Paladins, and PUBG
multiply by the run's FOV (PUBG is also exponential in the sensitivity),
Battlefield V/1/Hardline, GTA 5, and Battlefield 6 are affine, and
counts/360 and in/360 invert the sensitivity, so reproducing the capture
faithfully needs an expression evaluator, the run's FOV as an input, a
mapping from the stats file's `Sens Scale` string onto the capture's
`ScaleName`, and a refresh whenever KovaaK's adds a scale. It offers nothing
over the increment the file already records, which converts every scale --
including scales added in future game updates -- with zero per-scale
knowledge. A fixed per-scale yaw table, a weaker version of the same idea,
would convert the FOV-dependent and affine scales silently wrong.

**Settled: legacy runs keep their label, and recorded DPI is trusted
as-is.** The 570 DPI-less runs from 2019 to 2021 stay grouped under e.g.
`5.0 Overwatch`. Data is never excluded because its DPI is unknown, and no
legacy-DPI config knob is added. Separately, the app cannot detect a mismatch
between the DPI a file records and the mouse's physical DPI, so the recorded
value is trusted wherever it is read -- on the chart and, since this change,
in the PB cm/360 column. The known instance, 368 Valorant runs misrecorded at
400 DPI that convert to about 163.4 cm/360 instead of about 40.8, is
accepted; four of them are scenario personal bests and sort to the extreme of
that user-sortable column. Any in-app override (a config knob, a per-era DPI
map) would be a second source of truth that hides a data error instead of
fixing it, and withholding the column for converted PBs would hide 4 wrong
values by dropping 68 correct ones. The escape hatch stays on the data side:
a one-time edit of the `DPI:,400` lines in the affected files.

**Notifications judge the normalized group.** The watchdog computes
`nth_score` and `is_new_sensitivity` against the scenario's runs at the same
sensitivity key, so after conversion the normalized group is the unit for
placement and for first-sensitivity detection. Where a converted group shares
a rounded value with a native one, the merged history is the denominator: a
run that would have placed within Top N among the raw-scale runs alone can
fall outside it, and a first native run at a converted group's value is not a
new sensitivity. No separate raw-scale notification history is kept, and the
notification rules themselves do not change.

**The rounding fix does not reach legacy runs.** Rounding the raw sensitivity
to one decimal place collapsed `0.16`, `0.2`, and `0.25 Valorant` into one
`0.2 Valorant` group. Converting first moves the rounding onto the cm/360
result, where one decimal place is the right precision, and those three
separate into 51.1, 40.8, and 32.7 cm/360. The fallback branch keeps today's
raw-sensitivity rounding, so the 95 legacy `0.32 Valorant` runs still display
as `0.3 Valorant`.

**Provenance.** Proposed and merged as
`docs/proposals/sensitivity_conversion_proposal.md` (PR #277); both decisions
ruled on 2026-09-11 (PR #279), each accepting the recommendation. It
supersedes a 2026-08-03 draft reviewed on PR #197, which was parked and
closed unmerged. Corpus numbers were verified against the live stats
directory on 2026-09-05: 8,064 parseable files, of which 7,494 carry both
fields and 570 carry neither, with no file carrying only one.

Superseded in part by the
[2026-09-26 recorded-setting entry](2026-09-26-a-converted-run-keeps-the-setting-it-was-recorded-at-for-display-only.md):
the clause "`RunData`'s shape is unchanged, so the original scale value is
not retained" no longer holds. A converted run keeps its recorded value,
scale, and DPI, for the chart hover only. Everything else here stands,
recorded DPI trusted as-is included.

Superseded in part by the
[2026-09-27 per-scale precision entry](2026-09-27-sensitivity-precision-is-fixed-per-scale-and-its-config-knob-is-retired.md):
the paragraph "The rounding fix does not reach legacy runs" no longer holds. A
legacy run keeps the sensitivity its file recorded, unrounded, so the 95
`0.32 Valorant` runs read `0.32 Valorant`. cm/360 values still round to one
decimal place, now fixed rather than configured. Everything else here stands.
