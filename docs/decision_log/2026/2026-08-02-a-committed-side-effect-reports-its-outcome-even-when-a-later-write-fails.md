# 2026-08-02: A Committed Side Effect Reports Its Outcome Even When A Later Write Fails

Status: Accepted

Saving a preference to disk can fail — on Windows, antivirus or the search
indexer can hold a file open long enough to defeat the retries. When that
happens partway through an action the user already triggered, the app used to
abandon the whole response, so the screen said nothing at all. Two rules now
govern that: a screen must never keep showing a success message for a write
that failed, and an action whose real work already happened must still tell
the user it happened. In practice, importing a playlist that cannot be marked
visible now shows an orange notice saying the playlist was imported and how to
unhide it, and deleting a playlist still confirms the deletion.

Decision — two rules for a failed store write inside a callback:

1. **No stale success claim.** A UI that prints a success claim must not keep
   printing it after a failed write. A silent optimistic UI that reverts on
   its own may keep propagating. (Adjudicated during the PR #183 review;
   implemented there in `bae99a5` on the settings page, and first recorded
   here.)
2. **A committed side effect reports its outcome**, even when a later step
   fails. The rule above is about a false claim; this one covers the absence
   of any claim after an irreversible operation has already succeeded.

Mechanism: the handling is page-local `try/except OSError` at the call site
(`PermissionError` is a subclass). `replace_with_retry` re-raising after
exhausted retries stays the store contract, and the three writers in
`playlist_visibility_service.py` keep propagating with unchanged signatures —
a store-wide no-propagation policy was considered and deferred, since it would
force a UI answer for the toggle, where the right answer is "show nothing".
The write-before-cache ordering in those writers is load-bearing: a failed
write leaves the in-memory set holding the old value, so a retry still writes.

Per call site in `source/pages/playlists.py`:

- **Toggle** (`update_playlist_visibility`) — propagates, unchanged. Nothing
  is committed and no claim is printed; the cell renders purely from
  server-supplied state, so a failed request leaves no wrong icon on screen
  and the next click retries. Pinned by a regression test so a future
  catch-all cannot quietly change it.
- **Import** (`import_playlist`) — reports the split outcome. The playlist
  file is already on disk, so every output matches the success path (refresh
  bumped, modal closed, field cleared, warmup still enqueued) and only the
  toast changes: orange, under its own id, saying the import succeeded and
  naming the label and canonical code, then that the playlist could not be
  marked visible and how to surface it. Generic "import failed" wording is
  forbidden here — it would be a false statement, the exact defect this
  fixes.
- **Delete** (`confirm_delete_playlist`) — logs the failure and shows the
  ordinary green "Playlist Deleted" toast, deliberately with no split-outcome
  message. This `hide_playlist` is membership bookkeeping (pruning the deleted
  code from the shown set) and its failure has no observable consequence: the
  row is gone either way, a dead code renders nowhere, and the residue
  self-heals if the code is re-imported, because "importing is the intent to
  see" early-returns on an already-shown code. Reporting it would be noise
  about internals. The user-visible fix is that the request no longer fails,
  so the retry that produced a red "Playlist Delete Failed" toast for a
  *successful* delete never happens.

Reachability, so nobody re-derives it: import can only hit the write once a
visibility file exists — with no file, the shown set is seeded from the user
root, which already contains the just-imported playlist, so `show_playlist`
early-returns. First-run installs are immune; steady state is not. Delete only
writes when the playlist was visible.

Provenance: the PR #183 review and commit `bae99a5` (rule 1), and PR #185
(rule 2 and the playlist call sites).
