# 2026-07-17: Absorb Poll-Tick Bursts With Threads, Not Visibility Gating

Status: Accepted

Decision: Waitress runs with 8 worker threads (PR #116) as the sole fix for
poll-tick pressure. The demand-side alternative — pausing Home's
`interval-component` while the tab is hidden (Page Visibility API) — stays
unbuilt; its pre-approved design is parked as a kickoff prompt in
`ignore/prompts/icebox/` for reactivation if the symptom returns.

Why: Every Home polling tick (1 s default) fires three callback POSTs at once
(`check_for_new_data`, `flush_background_notifications`, and the cache-only
branch of `get_scenario_rank`). Against Waitress's default 4 threads, that
burst plus one thread held by a slow KovaaK's fetch (slow spells reach ~28 s)
left zero headroom, and a single idle tab produced task-queue-depth warnings.
Raising supply to 8 threads was deliberately tried first as the minimal fix,
with visibility-gated polling queued as the contingent next step; four days of
post-merge logs showed zero warnings, so the contingency never fired. Push
delivery (WebSocket/SSE) was also rejected: this is a single-user local app,
and with the warnings gone the polling cost argument for push collapses.

Consequences: An idle-but-hidden Home tab still polls (~3 POSTs/s of cheap
cache-only work) — accepted chatter, not a defect. If queue-depth warnings
reappear, reach for the iceboxed visibility-gating prompt (gate on
`document.hidden`, never window focus: an unfocused-but-visible window on a
secondary monitor must keep polling) before raising threads further.
