# 2026-07-06: Coalesce Pending Home Run Events

Status: Accepted

Decision: Home's `check_for_new_data` callback is the sole consumer of the
process-wide run-event deque. On each invocation it drains all pending messages,
lands on the most recently played scenario when automatic scenario switching is
enabled, and publishes a JSON-safe `run-events` summary for that scenario.
`generate_graph` rebuilds from the already-current in-memory stores and creates
toasts from that summary only when `run-events` triggered it. A single run keeps
the existing per-run toast behavior; a backlog produces one scenario-named
summary based on the latest matching run. The watchdog must successfully load a
run into the stores before enqueueing its message. The supported usage model is
one active Home tab; extra tabs remain crash-safe but unsynchronized.

Why: Home's interval does not run while the page is unmounted, so queued events
previously replayed one tick at a time on return. That rebuilt the same final
plot repeatedly, moved the scenario dropdown through stale history, and emitted
stale toast batches. Enqueue-before-load also allowed a consumer to rebuild
before the corresponding run was queryable, or to toast a run whose second parse
failed.

Consequences: A backlog is consumed in one tick, produces at most one dropdown
change and one toast batch, and cannot expose a message without queryable run
data. Mixed-scenario counts describe only the landing scenario. Nonmatching
events are discarded when automatic switching is off, preserving the previous
policy without wasting ticks. Coherent multi-tab delivery would require a
broadcast or push transport and remains outside this local single-user design.

**Superseded in part (2026-10-13).** The chart callback no longer creates a
toast, and a backlog no longer yields a toast batch from the page. The app
shell's drain sends one plain toast for the batch's newest live run, on every
page. The rule for the plot and for landing on the scenario last played is
unchanged. See
[A Run Toast Is Plain And Shows On Every Page](2026-10-13-a-run-toast-is-plain-and-shows-on-every-page.md).
