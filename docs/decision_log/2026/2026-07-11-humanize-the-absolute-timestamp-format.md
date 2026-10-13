# 2026-07-11: Humanize The Absolute Timestamp Format

Status: Accepted

Decision: The absolute "on-hover / in-title" timestamp adopts a GitHub-shaped, humanized format instead of the previous `%Y-%m-%d %I:%M:%S %p` (which rendered `2026-04-12 07:04:22 PM`). Two variants: staleness surfaces (home last-played tooltip, playlist/scenario grid tooltips, plot-title `updated:`) show `Apr 9, 2026, 7:04 PM` (no seconds); the per-run scatter hover shows `Apr 9, 2026, 7:04:22 PM` (seconds kept). Format rules: abbreviated English month from a hardcoded array (never `%b`/`calendar.month_abbr`), unpadded day, 4-digit year, unpadded 12-hour hour with `0 → 12` (midnight `12:xx AM`, noon `12:xx PM`), zero-padded minutes/seconds, uppercase space-separated AM/PM, browser/local time with no timezone suffix. The Python side is `format_absolute_timestamp(dt, *, include_seconds=False)` in `source/utilities/utilities.py`; the JS side is `dagfuncs.absoluteTime` in `assets/dashAgGridFunctions.js`, which mirrors the no-seconds variant. The relative string, the `Never`/`—` sentinels, the epoch-seconds plumbing, and the dotted-underline tooltip affordance are all unchanged.

Why: Market research (GitHub, Discord, Slack, Steam, AWS Cloudscape) confirmed the relative-primary + absolute-on-hover pattern is standard, but the old absolute string deviated from every comparator — a zero-padded 12-hour hour (no consumer app pads it), seconds on staleness surfaces (GitHub/Discord/Cloudscape all drop them), and a machine-register ISO date glued to a consumer-register AM/PM time. The GitHub shape reads as one register. Seconds are kept only on the run-level hover because they cross-reference KovaaK's second-stamped stats CSV filenames. The format is hand-rolled (not `strftime`/`toLocaleString`) for locale independence (hardcoded month array) and because no cross-platform strftime code exists for an unpadded hour (`%-I` is POSIX-only, `%#I` Windows-only).

Consequences: Python↔JS parity is held by this spec and by hand — there is no JS test harness — so the two implementations must be kept in sync (both carry a comment pointing at the other). This supersedes only the exact-format aspect of the 2026-06-21 and 2026-06-30 entries; their behavioral decisions stand.

**Superseded in part (2026-10-12).** The plot title's `updated:` use ends:
on the Run History page the title is the scenario's name alone. That page
adds three shorter uses. A session's name and the latest-run card's time
drop the year while it is this year's, and a run row in the list shows a
time of day alone. The format and its rules stand. See
[The Run History Chart Plots Every Run And Draws No Summary Line](2026-10-12-the-run-history-chart-plots-every-run-and-draws-no-summary-line.md),
[The Run List Is A Second Column Beside The Chart](2026-10-12-the-run-list-is-a-second-column-beside-the-chart.md),
and
[A Past Run's Check Is Judged Against The PB It Was Chasing, Under Its Own Version](2026-10-12-a-past-runs-check-is-judged-against-the-pb-it-was-chasing-under-its-own-version.md).
