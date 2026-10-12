# 2026-08-09: PB Columns Keep Their N/A Sentinel Even For Timestamps

Status: Accepted

The playlist table gained a PB Date column showing when the personal best
was achieved. On a scenario with no local runs it renders "N/A" like the
other PB columns beside it, rather than the grid's "Never" sentinel, so an
unplayed row shows both words at once. This was chosen deliberately: each
word keeps one meaning, and the row's PB cells stay consistent with each
other.

Decision: A grid column whose value is a stat of the personal-best run
takes "N/A" as its null sentinel, even when the value is a timestamp
rendered with the shared relative-time helpers. "Never" stays scoped to
Last Played (in a playlist but never played). On an unplayed row, Last
Played reads "Never" while PB Score / PB Date / PB cm/360 / PB Accuracy
read "N/A"; the sentinels co-occur by design. Last Played and PB Date are
null under exactly the same condition — the scenario has no local runs —
so an unplayed row is the only place "Never" and "N/A" describe the same
fact. (PB cm/360 additionally reads "N/A" on played rows whose PB used a
different sensitivity scale; "N/A" in a PB column is not by itself
evidence the scenario is unplayed.) The playlist grid's live tick now
refreshes both timestamp columns:
`refreshCells({force: true, columns: ["last_played_sort",
"pb_timestamp_sort"]})`.

Why: "Never" answers "have I played this?"; "N/A" marks a stat that does
not exist because there is nothing to measure, and a missing PB is the
second kind. Column-family consistency (a row's PB cells agreeing with
each other) was judged to beat renderer consistency (every relative-time
cell sharing one sentinel). Maintainer-ratified copy call.

Consequences: Shipped in PR #216. Narrows the sentinel rule and extends
the single-column `refreshCells` call of the
[2026-06-21 relative timestamp entry](2026-06-21-relative-humanized-last-played-timestamps.md),
whose Status line points here. Future timestamp columns choose their null
sentinel by column family, not by renderer.
