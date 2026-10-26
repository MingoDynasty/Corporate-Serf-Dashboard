# 2026-10-23: Schedule Run Imports On One Worker

Status: Accepted

New runs and files recovered during startup share their waiting time so a
burst reaches the app promptly.
One background worker imports ready files and retries unfinished ones without
holding up other runs. Repeated events for an imported file leave its run count
unchanged, and a file that remains unreadable raises one notice while recovery
checks continue.

## Contract

- The observer handles create, modify, and rename-to-final CSV events by
  queuing paths, without reading or sleeping on the observer thread.
- One worker starts after the initial scan and performance-file indexing.
  It is the sole live writer of run stores and the performance-file listing,
  preserving the [single-writer decision](2026-07-09-accept-unsynchronized-in-memory-stores-single-writer.md).
- Each path receives a one-second grace period. Modify events refresh that
  quiet period until the first attempt; duplicate create events do not.
  This retains time for the game's companion performance file to arrive.
- Deadlines use a monotonic clock. The earliest due file runs first; an
  unfinished file's retry deadline never holds up another due file.
- A successful import is remembered by the stats file name within the one
  watched folder, with platform case normalization for identity only. Original
  file-name casing is retained in stored runs and notifications. Startup scan
  results seed that set; failed attempts never enter it. Replacing a file with
  the same name does not create a second logical run during the session.
- Failures retry after 0.25, 0.5, 1, 2, and 4 seconds. Once those retries are
  exhausted, queue the existing run-import failure notice once per path, then
  recheck that path every 30 seconds without repeating the notice. A corrected
  file can recover without a new filesystem event or a restart.
- Successful storage still precedes notification publication, and pre-run PB
  facts and pace classification are computed by the same writer.
- Shutdown stops the observer first, then wakes and joins the writer. An active
  import finishes; pending files are recovered by the next startup scan.

## Evidence And Scope

The prior handler spent at least one second on every created CSV even when the
whole burst was already complete. A native Windows reproduction at the former
head imported 20 files in 20.028 seconds, compared with 0.017 seconds when only
that sleep was disabled. A file completed 300 ms after creation was missed in
the latter experiment, so deleting the delay alone was rejected.

Regression coverage uses a native observer and 1,000 synthetic files, real
parsing and stores, duplicate events, delayed writes, rename arrivals, exhausted
retries, recovery without a modify event, and worker shutdown. No thread pool,
new persisted store, or configurable retry policy is introduced. Post-startup
reconciliation uses the same worker and successful-file identity check; its
current contract is recorded in the [run ingestion spec](../../specs/run_ingestion.md).
