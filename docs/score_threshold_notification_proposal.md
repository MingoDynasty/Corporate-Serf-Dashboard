# Score Threshold Notification Reference-PB Proposal

> **Status:** Proposed (design review, 2026-07-08) — awaiting owner decision
> on the reference-PB question below. Not yet scheduled.

## Context

Surfaced during the PR #68 review (settings-modal tooltips). That PR briefly
capped the score-threshold percentage at 100 to hide the fact that goals above
100% never fire a "passed" notification; the cap was reverted (`b43d2ed`)
because the **overlay** legitimately wants an above-PB target line (e.g. a 105%
stretch line that ratchets up as your PB grows). Reverting the cap restored the
overlay use case but left the underlying notification quirk untouched. This
proposal addresses that quirk on its own.

## Problem

The score-threshold notification decides pass/fail against the **post-run**
personal best, but the percentage it *displays* is measured against the
**previous** personal best. Because the post-run PB already includes the run
being judged, any goal above 100% is mathematically unreachable — the threshold
always chases the new PB out of reach.

Concrete failure case (goal = 105%, previous PB = 800):

| New run | Toast prints (vs previous PB) | Threshold (`post-run PB × 1.05`) | Verdict today | Intuition |
|---|---|---|---|---|
| 820 (+2.5% PB) | 102.5% | 820 × 1.05 = 861 | yellow "keep grinding" | correct — didn't hit +5% |
| 850 (+6.25% PB) | 106.2% | 850 × 1.05 = 892.5 | **yellow "keep grinding"** | **wrong — beat the goal** |

The second row is the defect: the run beat the previous PB by more than the 5%
goal, the toast even prints "106.2%", yet it reports failure. No run can ever
turn a >100% goal green, so the feature is inert above 100% while the overlay
happily draws the target line.

## Root cause

A denominator mismatch between the two numbers in the same notification branch
(`source/pages/home.py`, `_build_run_event_notifications`, both the single-run
and the backlog-summary paths):

- **Displayed percentage** uses the per-run *previous* PB:
  `percentage = latest["score"] / latest["previous_high_score"] * 100`.
- **Pass/fail comparison** uses `score_threshold`, which is computed once in
  `generate_graph` as `get_high_score(selected_scenario) * pct / 100` — and
  `get_high_score` reads the DB *after* the watchdog has already loaded the new
  run (`file_watchdog.py` loads before it enqueues the event). So the
  comparison's denominator is the *post-run* PB, not the previous one.

The overlay's use of the post-run PB is correct and should stay — the target
line is meant to sit at pct% of your *current* best. Only the notification is
using the wrong reference.

## Options

1. **Compare against the previous PB.** (recommended)
   Give the notification's verdict the same denominator as the percentage it
   already displays. A >100% goal becomes achievable exactly when the run
   beats the PB it was chasing by the target margin. The overlay is untouched
   and keeps using the post-run PB.

2. **Re-cap the percentage at 100.** Rejected — this is what `b43d2ed`
   reverted. It breaks the above-PB overlay target, which is the more
   motivating use of the setting.

3. **Split into two independent settings** (an overlay target % and a
   notification goal %). Rejected as over-engineered: the value's whole appeal
   is that one "goal %" drives both the line you watch and the toast you get.
   Revisit only if a concrete need for divergent values appears.

## Recommendation — Option 1

In `_build_run_event_notifications`, decide pass/fail with

```python
latest["score"] >= latest["previous_high_score"] * score_threshold_percentage / 100
```

instead of `latest["score"] >= score_threshold`. Only the reference PB changes
(previous instead of post-run); the comparison stays in **score space**, the
same shape as today's code and the overlay formula.

Deliberately *not* the displayed-ratio form (`percentage >= pct`): that form
regresses the exact-at-threshold boundary settled in `752e47f`, because the
division rounds — `820 / 800 * 100` evaluates to `102.49999999999999`, so a
run at exactly a 102.5% goal would turn yellow. The score-space form evaluates
exactly there (`800 * 102.5 / 100 == 820.0`). Verdict and displayed percentage
still share the same denominator, so they agree up to display rounding (the
toast prints `:.1f`, so a 102.46% run prints "102.5%" yet fails a 102.5 goal —
inherent to rounding the display, unchanged by this proposal).

Why it is safe for the existing ≤100% behavior (verified against the code):

- **Non-PB run:** the previous PB equals the current PB (the run didn't move
  it), so the reference is identical to today — no behavior change.
- **New-PB run, pct ≤ 100:** already passes today and still passes (the run
  exceeds its previous PB, which is ≥ `previous_PB × pct/100`).
- **New-PB run, pct > 100:** the *only* behavior that changes — now it can turn
  green, which is the fix.

## Implementation sketch (confirm at build time)

- Pass `score_threshold_percentage` into `_build_run_event_notifications`
  (replacing the pre-multiplied `score_threshold` parameter, which only the
  notification consumed). `generate_graph` keeps computing its own
  `score_threshold` from the post-run PB for the overlay.
- Both notification paths change identically: the single-run branch and the
  `count > 1` backlog-summary branch.
- The guard stays `previous_high_score is not None and > 0`; runs with no prior
  PB continue to fall through to the generic "Graph updated!" toast.
- Tests: all seven `_build_run_event_notifications` call sites in
  `tests/test_home_run_events.py` pass `score_threshold=` and shift to the new
  percentage parameter — not just the two boundary tests from `752e47f`
  (`test_single_run_threshold_notification_passes_at_exact_threshold`,
  `test_backlog_threshold_summary_passes_at_exact_threshold`). Those two keep
  asserting green at the exact threshold (820 on a PB of 800 at a 102.5%
  goal), which doubles as the regression guard for the score-space-vs-ratio
  rounding above; add a new-PB-beats-a->100%-goal case (the row-2 example
  above) asserting green, and a new-PB-below-a->100%-goal case asserting
  yellow.

## Follow-up copy (small, ships with the change)

The `score-threshold-percentage` tooltip currently reads "…percentage of your
current personal best, used by the threshold line and notification." After this
change the *notification* is relative to the PB you were chasing while the
*line* is relative to your current PB. Tighten to something like: "Sets your
score goal as a percentage of your personal best — the overlay line sits there,
and the notification fires when a run reaches it." Finalize wording at build.

## Decision needed

Confirm the intended meaning of a goal above 100%: **"beat the personal best I
was chasing by that margin"** (Option 1). If instead a >100% goal should mean
something else — or if the notification should simply never be offered above
100% while the overlay still allows it — say so, since that changes the fix.

## Out of scope

- The overlay's reference PB (stays post-run/current — correct as-is).
- The ≥ vs > boundary at the threshold (already settled in PR #68 as `>=`).
- The backlog summary judges only the **latest** run of the batch
  (`_drain_run_events` keeps `matching_messages[-1]`), so a >100% goal met by
  a mid-batch PB run followed by a cooldown run still shows yellow. Not a
  regression — today's summary is equally blind — and reviewing the whole
  batch after the fact is the run-history feature's territory (next bullet).
- Any run-history / after-the-fact review of past pass/fail results — tracked
  separately in `docs/run_history_proposal.md`.
