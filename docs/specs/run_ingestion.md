# Run Ingestion

The app loads existing run files at startup and watches the stats folder for
new ones. A second directory listing after monitoring starts recovers files
written during startup. Each successfully imported filename contributes one run
per app session. A new file that can't be read yet is tried again for a few
seconds before the run is reported as not recorded.

## Startup And Monitoring

- The stats folder is pinned for the process. Without a usable stats folder,
  both the initial scan and monitoring are skipped and the app serves without
  run data ([settings](settings.md)).
- The initial scan lists the folder's CSV files, imports readable runs, and
  returns every scanned path, including files that failed to load. Those
  imports do not publish new-run messages.
- After the observer starts, a second listing queues CSVs absent from the
  initial scan as create events on the same observer. A file arriving
  after this listing is covered by normal filesystem monitoring.
- The watchdog thread processes both reconciliation and live events. Startup
  loading finishes before it starts, so the run stores retain their single
  writer ([accepted threading contract](../decision_log/2026/2026-07-09-accept-unsynchronized-in-memory-stores-single-writer.md)).
- Reconciled runs use the ordinary live-import path: the stores are updated
  before a new-run message is published, and personal-best rank refresh follows
  the existing rules ([notifications](notifications.md),
  [scenario position](scenario_rank.md)).

## Successful File Identity

- The stores identify each successful import by its full stats filename,
  using the platform's filename casing rules. The handler checks this identity
  for initial-scan imports as well as earlier live imports, without maintaining
  a separate registry ([run identity](notifications.md#run-notifications)).
- A repeated create event for a successful filename is ignored before parsing or
  waiting. Overlap between reconciliation and a real event contributes one
  run, one new-run message, and at most one rank-refresh scheduling call.
- File contents are not part of this identity. A successful run file is treated
  as immutable for the session, including deletion and recreation with the same
  filename. Distinct filenames remain distinct runs, even when their scores and
  timestamps match. Restarting rebuilds the stores from the files currently on
  disk; identities are not persisted.

## Read Failures

- An unsuccessful parse or load is not remembered as a successful import. A
  later create event for that path may try again. Files already attempted by
  the initial scan are not queued by the second listing, so historical read
  failures do not create a backlog of live imports or failure notifications.
- A live or reconciled import parses the file after waits of 1, 2 and 4
  seconds and stops at the first parse that succeeds, so a CSV still locked or
  mid-write gets about seven seconds to settle. Only the last failed attempt
  queues the failure message. The waits run on the observer thread, so files
  arriving faster than one a second import one at a time
  ([2026-10-26](../decision_log/2026/2026-10-26-run-imports-retry-a-failed-parse-on-the-observer-thread.md),
  [accepted debt](../tech_debt.md#fixed-one-second-handler-sleep-serializes-ingestion)).
- There is no periodic reconciliation. A file that still fails after the last
  attempt stays absent until a later event or a restart. A store load that
  fails after a successful parse is not retried.
- Startup scan failures are counted in the startup log. A failed watchdog
  import queues the existing run-import failure message for the UI.
