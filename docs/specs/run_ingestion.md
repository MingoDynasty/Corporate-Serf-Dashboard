# Run Ingestion

Existing run files load at startup, and a second listing recovers files written
during startup. New and recovered files share their waiting time so a burst
reaches the app promptly. One worker retries unfinished files without delaying
ready runs. Each successfully imported filename contributes one run per app
session.

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
- The observer queues reconciliation and live events for one ingestion worker.
  Startup loading finishes before that worker starts, so the run stores retain
  their single writer
  ([accepted threading contract](../decision_log/2026/2026-07-09-accept-unsynchronized-in-memory-stores-single-writer.md)).
- Created, modified, and renamed-to-final CSVs receive a one-second quiet
  period per path before the first attempt. Modify events refresh that initial
  period; duplicate create events do not. Ready paths are imported without an
  extra wait between files, and an unfinished path's retry deadline does not
  delay another ready path
  ([scheduled imports](../decision_log/2026/2026-10-23-schedule-run-imports-on-one-worker.md)).
- Reconciled runs use the ordinary live-import path: the stores are updated
  before a new-run message is published, and personal-best rank refresh follows
  the existing rules ([notifications](notifications.md),
  [scenario position](scenario_rank.md)).
- Shutdown stops the observer, then finishes any active import and joins the
  worker. Pending source files are recovered by the next startup scan.

## Successful File Identity

- The stores identify each successful import by its full stats filename,
  using the platform's filename casing rules. The worker seeds a successful-name
  cache from startup-loaded runs and remembers its successful live imports.
  The importer also checks the stores before parsing or publishing, so a
  queued file that has already loaded succeeds without another notification
  ([run identity](notifications.md#run-notifications)).
- A repeated create event for a successful filename is ignored before parsing
  or waiting. Overlap between reconciliation and a real event contributes one
  run, one new-run message, and at most one rank-refresh scheduling call.
- File contents are not part of this identity. A successful run file is treated
  as immutable for the session, including deletion and recreation with the same
  filename. Distinct filenames remain distinct runs, even when their scores and
  timestamps match. Restarting rebuilds the stores from the files currently on
  disk; identities are not persisted.

## Read Failures

- An unsuccessful parse or load is not remembered as a successful import.
  Scheduled retries and later events may try again. Files already attempted by
  the initial scan are not queued by the second listing, so historical read
  failures do not create a backlog of live imports or failure notifications.
- Live and reconciled imports retry after 0.25, 0.5, 1, 2, and 4 seconds. Once
  those retries are exhausted, the worker queues the existing run-import failure
  notice once per path and rechecks the path every 30 seconds without repeating
  the notice. A corrected file can recover without another filesystem event or
  a restart ([failure notices](notifications.md#background-threads-and-diagnostics)).
- Startup scan failures are counted in the startup log. Both reconciliation
  and live imports use the same retry and failure-notification policy.
