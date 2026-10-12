# 2026-09-27: Sensitivity Precision Is Fixed Per Scale, And Its Config Knob Is Retired

Status: Accepted

A run's sensitivity is now rounded according to its scale, and the setting
that used to control the rounding is gone. Sensitivities in cm/360 always
round to one decimal place, which was already the default. Runs from old stats
files that keep a game's own scale now show exactly the number the player
typed, so 0.32 Valorant no longer reads as 0.3. A user who had changed the
setting loses that change without notice, and a leftover line in the config
file only logs a warning.

**Ruling.** Ruled (user) 2026-09-27, in a decisions chat, after independent
second opinions from `claude-fable-5-1` and `gpt-6-astra`, both of which
endorsed this shape. `sens_round_decimal_places` dates from play on Valorant
sensitivity. Since the
[2026-09-11 conversion](#2026-09-11-sensitivities-normalize-to-cm360-at-parse-time-from-the-files-own-increment-and-dpi)
nearly every run is cm/360 at parse time, and the knob did two contradictory
jobs with one number. On cm/360 it merges formula output into groups, which
wants one decimal. On a legacy run that keeps its game scale it should
preserve what the player typed, which one decimal breaks.

**The rule.** `extract_data_from_file` in `source/kovaaks/data_service.py`
rounds a cm/360 value to `CM360_DECIMAL_PLACES`, one: a converted value inside
`_converted_cm360`'s validation guard as before, so a conversion that rounds
away still falls back, and a native value on the fallback branch. Any other
scale reaching the fallback branch (a legacy file without `Sens Increment` and
`DPI`, a field the conversion cannot use, or a conversion that rounds away)
keeps the parsed `Horiz Sens` float untouched. `RecordedSensitivity` was
already unrounded and is unchanged. `sensitivity_key` is
`f"{horizontal_sens} {sens_scale}"`, so the rule reaches grouping, Top N
placement, averages, first-sensitivity notifications, and the plot axis and
hover. The PB cm/360 column skips every scale but cm/360 and sees no change.

**Decimal bucketing, not a tolerance.** The cm/360 rounding exists so that a
typed value and a converted one a few hundredths apart share a group:
`0.2 Valorant` at 1600 DPI converts to 40.84 and joins a typed 40.8. Its edges
are hard. 40.849 and 40.851 land in 40.8 and 40.9, and nothing merges values
by distance.

**Evidence.** Measured 2026-09-27 over the maintainer's stats folder, 8,666
files. The 8,096 cm/360 runs group identically at one and two decimals, 1,418
groups over 810 scenarios: native cm/360 values are all whole numbers, and
converted ones take six distinct values. Of the 570 legacy runs (475
Overwatch, 95 Valorant), one decimal got 170 wrong: `0.32 Valorant` read `0.3`
(95 runs), and Overwatch `2.38` merged into `2.4` (24) and `4.75` into `4.8`
(51). The raw `Horiz Sens:` text across all files is 37 distinct short
decimals, such as `40.0`, `0.32`, and `4.75`, so "as recorded" is exact.
Rejected: two decimals for game scales, which would still corrupt a
three-decimal setting (`round(0.235, 2) == 0.23`, `round(1.125, 2) == 1.12`).

**The retired key.** The `ConfigData` field and its `example.toml` block are
deleted, with no bound, migration, or special case. `_warn_unknown_keys`
tolerates unknown keys permanently, so a `config.toml` still carrying the key
loads and names it in the existing unknown-key warning. A public user who had
set a non-default value loses it silently; the reviewers judged that
negligible one day after launch. No cache persists sensitivities and the run
store rebuilds from the stats folder at every start, so nothing migrates.
Rolling back to a release that still requires the key needs the literal line
`sens_round_decimal_places = 1`, which the user guide's rollback instructions
under [Manual install](user_guide.md#manual-install) give.

Supersedes, in part, the
[2026-09-11 sensitivity-normalization entry](#2026-09-11-sensitivities-normalize-to-cm360-at-parse-time-from-the-files-own-increment-and-dpi):
its "The rounding fix does not reach legacy runs" paragraph only. Everything
else there stands; where it names `sens_round_decimal_places` or the
configured precision for a conversion, the precision is now this fixed one
decimal place, the value the knob shipped with. This also closes the case the
[2026-09-27 PB-format entry](#2026-09-27-the-scenario-table-drops-trailing-zeros-from-pb-score-and-pb-cm360)
left open: every stored cm/360 value carries one decimal, so the PB cm/360
column's two decimals are always exact.

**Provenance.** No proposal: the ruling went straight to a standalone
implementation. Shipped in PR #319.
