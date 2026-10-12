# 2026-09-27: The Scenario Table Drops Trailing Zeros From PB Score And PB cm/360

Status: Accepted

The playlist scenario table shows PB Score and PB cm/360 with up to two
decimals and drops trailing zeros, so one column can read 710 beside 863.94.
Audits kept flagging this as ragged decimals, and it is now ruled the intended
style rather than a defect. The same rule makes the table show a sensitivity
of 50 where the chart says 50.0 cm/360, and that difference is accepted too.

**Ruling.** Ruled (user) 2026-09-27, in a decisions chat, on finding P8 of
the 2026-07-12 UI audit, which proposed fixed precision (two decimals for
scores, one for cm/360) and which every audit since re-raised as unruled.
Both halves: stripping stays within a column (won't-fix), and the
table-versus-chart difference for PB cm/360 stays. `_format_score` in
`source/kovaaks/playlist_scenarios_service.py` formats both columns as
`f"{value:,.2f}"` with trailing zeros and a bare point stripped; PB Accuracy
keeps its fixed two decimals.

**Why not fixed precision.** Fixed decimals pay off when a reader compares
values by lined-up decimal points. The table's columns are left-aligned, and
each row is a different scenario with its own score scale, so no comparison
runs down the PB Score column, and `.00` on a whole-number scenario is noise.
Right-aligning the numeric columns is a separate question this ruling does
not take up.

**Why the chart keeps `50.0 cm/360`.** The chart's axis and hover and the run
toasts print `f"{horizontal_sens} {sens_scale}"`, which is also
`sensitivity_key`, the Score vs Sensitivity grouping and first-sensitivity
key. A chart reading `50 cm/360` would need a display-only string at plot
time, never a change to the key, and the table already shows the same number.
Rejected: a `docs/tech_debt.md` entry for the difference, since an entry
nobody plans to work on is what kept the finding coming back.

**Exactness.** Two decimals lose nothing while stored sensitivities carry two
decimals or fewer, which holds at the shipped `sens_round_decimal_places` of
one. A configured value above two would let the chart read `50.125` beside a
table rounded to two places. That case stays open until the knob's removal
ships: the same chat ruled the removal, with cm/360 fixed at one decimal, and
queued it as a separate implementation.
*(Resolved 2026-09-27: the knob is retired and every stored cm/360 value
carries one decimal place, so the case can't arise. See
[Sensitivity Precision Is Fixed Per Scale, And Its Config Knob Is Retired](#2026-09-27-sensitivity-precision-is-fixed-per-scale-and-its-config-knob-is-retired).)*
