# 2026-10-26: Run Imports Retry A Failed Parse On The Observer Thread

Status: Accepted

A new run file that can't be read yet is now tried again after two more
seconds and then four more before the app reports the run as not recorded.
Before, one failed read left the run missing until a restart. The waits stay
on the thread that receives file events, so files arriving faster than one a
second still import one at a time, a cost accepted because play never
produces them.

**Ruling and delivery.** The maintainer, in chat on 2026-10-26: "Close PR 423
with a signed comment that explains why and invites the author to reopen it
with evidence of a realistic trigger, then open the small retry PR with
Fable's docs list." Built in
[#433](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/433).
[#423](https://github.com/MingoDynasty/Corporate-Serf-Dashboard/pull/423),
which moved imports to a worker thread, was closed unmerged the same day. A
`claude-fable-5-1` consult at xhigh recommended this shape before it read the
recommendation of the `claude-opus-5-5` session that implemented it. Current
behavior is in [run_ingestion.md](../../specs/run_ingestion.md#read-failures)
and [notifications.md](../../specs/notifications.md#background-threads-and-diagnostics).

**What changes.**

- `NewFileHandler._import_created_file` parses after each wait in
  `PARSE_WAITS_SECONDS`, `(1, 2, 4)`, and stops at the first parse that
  returns a run. The handler's warning and the failure toast follow the last
  attempt only; `extract_data_from_file` still logs each attempt's own
  failure.
- Only the handler's parse retries. A store load that fails after a
  successful parse, which needs the file replaced or deleted in between,
  still reports at once.
- A file that never parses holds the observer thread for seven seconds
  instead of one. Events queue meanwhile and none are dropped.
- The run stores keep their single writer
  ([2026-07-09](2026-07-09-accept-unsynchronized-in-memory-stores-single-writer.md)):
  no thread is added.

**Why not a worker thread.** The 2026-08-12 runtime soak recommended taking
the wait off the dispatch path. #423 did, with a worker thread, a deadline
scheduler, a filename-identity set beside `is_run_file_loaded`, modify and
move handlers, and a recheck every 30 seconds after the retries that never
stopped. Measured by the consult on #423's head `540c282d`: one file that
never parses was re-read about 2,880 times a day, writing about 3.4 MiB a day
to `debug.log` against its 5 MiB rotation. The worker's only gain is
throughput for files arriving faster than one a second. Play never does that:
the main instance's logs hold 1,267 run arrivals from 2026-07-27 to
2026-10-25, the shortest gap 30.16 s, and no failed parse. The soak's
1,000-file burst wrote far faster than play. When a burst does happen,
nothing is lost: the imports are late, and a restart imports the rest in
about a second.

**Criteria applied.** The maintainer's leans of 2026-10-26, not rulings: fix
a bug whose fix is small, simple and inexpensive; otherwise fix it when it
reproduces in a realistic situation or its consequences are serious. The
consult sharpened both: cost includes carrying the change, and seriousness is
judged after the recovery the app already offers, the failure toast and the
restart rescan. The retry passes the first test. The worker passes neither.

**Reopen when** a feature or workflow writes many run files while the app
runs. Start from #423's outline then, without the endless recheck, the second
identity set, or the modify and move handlers. The burst stays recorded as
accepted debt in [tech_debt.md](../../tech_debt.md#fixed-one-second-handler-sleep-serializes-ingestion).
