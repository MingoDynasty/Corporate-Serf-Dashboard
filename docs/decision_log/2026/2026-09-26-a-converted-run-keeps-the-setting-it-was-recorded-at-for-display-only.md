# 2026-09-26: A Converted Run Keeps The Setting It Was Recorded At, For Display Only

Status: Accepted

A run recorded on a game's own scale, such as 0.2 Valorant, used to lose that
setting when it was converted to cm/360. The chart's point hover now shows
the setting and its DPI after the cm/360 value, in both chart modes. A wrong
DPI in a file now shows up there instead of hiding behind an odd cm/360
value. Everything else still works from the converted value, so a wrong DPI
is shown but not corrected.

**Display extended (2026-10-24).** The
[compact point-tooltip decision](2026-10-24-chart-point-tooltips-show-score-time-and-run-numbers.md)
also exposes recorded settings in the run list's Sensitivity cell tooltip.
The chart still shows them in every mode. The original display rationale,
retention, conversion, grouping and DPI trust remain in force; the historical
template and customdata positions below describe their original implementation.

**What is kept.** The recorded setting is the one a player remembers
playing, and its DPI explains a cm/360 group that would otherwise look
wrong. `RunData` gains `recorded_sensitivity`, a frozen
`RecordedSensitivity(value, scale, dpi)` defaulting to `None`.
`extract_data_from_file` sets it only on the converted branch, from the
unrounded `Horiz Sens`, the recorded `Sens Scale`, and the parsed `DPI`.
Every other branch leaves it `None`: a native cm/360 run, a legacy file
without the two fields, a field the conversion cannot use, and a conversion
that rounds away. One nested value rather than three loose fields makes "all
three or none" hold by construction. The value never passes through
`sens_round_decimal_places`: at the shipped one decimal place,
`0.16 Valorant` would display as `0.2`, a false original that 56 corpus runs
would show.

**Display only.** The sensitivity-key builders, the `SortedDict` ordering,
the plot axis, run notifications, and the PB cm/360 column still read
`RunData.horizontal_sens` and `RunData.sens_scale`, so no group, placement,
notification, or column value moves. The one reader is `plot_service`, which
builds the suffix ` ({value} {scale} at {DPI} DPI)` with `format_decimal`,
which never rounds and drops a whole number's `.0`, so the DPI reads `1600`.
The suffix is the run points' last `customdata` column, `""` for a run that
was not converted, so a native run shows nothing where it would go. Both
modes share one run-point line,
`<b>Sensitivity</b>: %{customdata[2]}%{customdata[3]}`; in Score vs
Sensitivity it stands in for the x-value line, which would repeat it. The
Average score line keeps its hovertemplate and reads no `customdata`: a
converted run and a native run at the same cm/360 share one group, so a group
has no single recorded setting to name. An unconverted legacy run already
shows its recorded scale and gets no suffix.

**No migration.** The run store is in-memory and rebuilt from the stats
folder at every start, so every converted run carries the field from the
first launch after this change. Nothing persists `RunData`.

**Recorded DPI is still trusted as-is.** Showing the DPI is not correcting
it. The runs misrecorded at 400 DPI still convert to about four times their
real cm/360 and still group, sort, notify, and fill the PB cm/360 column
there. Only their hover changes, to read
`163.4 cm/360 (0.2 Valorant at 400 DPI)`. The rejection of any in-app DPI
override stands, and the escape hatch is still a one-time edit of the
affected files.

Supersedes, in part, the
[2026-09-11 sensitivity-normalization entry](2026-09-11-sensitivities-normalize-to-cm360-at-parse-time-from-the-files-own-increment-and-dpi.md):
its "`RunData`'s shape is unchanged, so the original scale value is not
retained" clause only. The conversion, its inputs and guards, the trust in
recorded DPI, the legacy-label rule, the notification semantics, and the
rounding rule all stand.

**Copy.** The fragment follows the value it explains, in parentheses, because
they read as "what this came from"; a ` · ` separator would read as two
independent facts. `at … DPI` keeps the unit, which is what makes the 400-DPI
misrecord legible. The scale is a proper name and keeps the casing the file
recorded.

**Provenance.** No proposal: the maintainer approved skipping one on
2026-09-26 and approved the scope, the run-point hover in both modes, on the
author's recommendation in the kickoff. Shipped in PR #312.
