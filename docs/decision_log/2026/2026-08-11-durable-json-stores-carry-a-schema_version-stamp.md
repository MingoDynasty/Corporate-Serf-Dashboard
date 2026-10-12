# 2026-08-11: Durable JSON Stores Carry A schema_version Stamp

Status: Accepted

Every durable JSON store the app keeps now starts with `"schema_version": 1`,
so future data migrations can tell a format the app understands from one it
does not. A file the app cannot use is never deleted or rewritten behind the
user's back: it is left exactly as it is, the app falls back to its first-run
defaults, and the page that owns the setting says what happened and how to fix
it. A file written by a *newer* version of the app is recognized as newer: the
app reads nothing from it, refuses every write to it, and says the data is
intact and an update will restore it. Existing installs are converted once by
a script that ships with the release; the app itself has no migration code.

Decision: settled with the maintainer on 2026-08-10 and 2026-08-11, after a
review round on the contract. The premise is the public launch. `data/` is the
app's database in lieu of SQLite, and a format change with no version marker is
indistinguishable from corruption.

**Scope.** `data/settings.json`, `data/playlist_visibility.json`, and every
user playlist under `data/playlists/`. The bundled corpus in
`resources/benchmarks/` is exempt: it ships with the code that reads it and is
governed by its own `generated_from.schema_version` provenance contract, so its
format can never be older or newer than the build. Cache files under
`data/cache/` get no stamp and no cache-schema rule; that is deferred to a
need-time proposal. The tolerance invariant for caches (missing, stale,
malformed, partially-written files must all be survivable) is unchanged and
still stated in `AGENTS.md`; only the versioning and invalidation *mechanism*
is deferred, and the known tolerance violations in `api_service.py` are tracked
separately.

**The marker.** Top-level `"schema_version"`, an integer. Validation is strict:
`type(value) is int` — so a JSON `true`, which `isinstance` would accept as an
`int`, is rejected — and exact membership in the supported set (today `{1}`).

**No grandfather rule.** An existing well-formed file *without* a stamp is an
error state, not implicit v1. Two machines is a cheap population to convert
once, and the alternative is a missing-means-v1 special case that every future
reader carries forever.

**Four read states, per store**, implemented once in
`source/utilities/store_schema.py`:

1. *Missing* — first-run defaults (settings unset, visibility seed, empty
   user-playlist set). Unchanged from before the stamp existed.
2. *Error* — unreadable, not JSON, not an object, no stamp, a malformed or
   **non-positive** stamp (`0` and negatives are garbage, not the future: a
   file that read as future would refuse every write and strand the store), or
   a supported stamp whose payload fails that version's definition. The bytes
   are preserved, the store reads as its first-run default, and an actionable
   message is reported. A stamp routes a payload to a validator; it never
   vouches for the payload.
3. *Supported* — a known stamp with a payload that validates.
4. *Future* — a stamp above the highest supported version. Nothing is read, and
   every write is refused.

The error and future states surface in the UI, not only in the log: an inline
alert on the settings page (an unusable store otherwise renders as an ordinary
empty form, exactly like a first run) and an alert on the Playlists page for
visibility (whose fallback is the seed, which looks exactly like a fresh
install). Unusable playlist files are skipped with the existing startup warning
queue. Without those surfaces the migration window reads as unexplained data
loss instead of loud but inert.

**Write rules.** Automatic writers never touch a store they cannot use:
`bootstrap_stats_dir` declines out loud in the error and future states, because
those read as "no keys" and writing would erase an identity the user really
configured. User-initiated saves *own* an error-state file, so self-service
recovery from a bad hand edit stays possible: the incumbent is copied
byte-for-byte to an adjacent `<name>.corrupt-<n>.bak` (exclusive create, so a
backup never replaces an earlier backup; a copy, never a move, so a write that
never lands leaves the original at its path), and only then is the file
replaced. If the copy cannot be made, the write is refused. Reads never mutate.
Future-state files raise `UnsupportedSchemaError`, which every caller reports in
its own register: a settings-page status distinct from the I/O-failure one (the
remedy is updating, not retrying), a toast on direct hide/unhide, the existing
partial-success branches for import and delete, and a log line at startup.

**Import collision guard.** A rejected playlist file is absent from
`playlist_database`, so the import's duplicate-code check cannot see it, and
two different name/code pairs can sanitize onto one filename anyway — the
filename is not authoritative and "not loaded" must never be inferred from the
code. So immediately before its atomic replace, the import classifies whatever
already occupies the destination, through the same decoder the loader uses: a
future incumbent refuses the import, an unusable one is copied aside and
replaced, and a healthy v1 incumbent refuses the path collision. That last case
also fixes a live overwrite bug at the time of writing. This could not be
deferred to the release that first breaks the playlist schema, because the
vulnerable writer is *this* release's import path running after a rollback, and
a future PR cannot retrofit already-installed code. The shadow case — the same
code imported under a different filename, so no path collision — is accepted as
non-destructive: nothing is overwritten, and the loader's duplicate warning
surfaces it on the next start.

**v1 payload definitions**, implemented once and imported by both the runtime
readers and the conversion script. Settings v1 is a flat object whose keys are
a subset of {`stats_dir`, `kovaaks_username`, `steam_id`} with string values;
missing still means unset, and **unknown keys are invalid**, because within a
version the key set is fixed (rejecting preserve-unknown-keys below means any
future key addition bumps the version anyway, so a stray key under stamp 1 is a
typo worth surfacing). Settings is read `utf-8-sig`: a Windows-editor BOM is
valid legacy data for the documented hand-edit escape hatch. Visibility v1 is
exactly {`shown_playlists`: list of strings}, unknown keys invalid. Playlist v1
is `PlaylistData` unchanged, extra fields still ignored — these are
machine-written envelopes, not hand-edit surfaces. Visibility and playlist
files are plain UTF-8, where a BOM is invalid.

**Migration.** `scripts/stamp_schema_version.py` converts the existing
population once. Its state machine is narrow: unstamped with a valid v1 payload
gets the stamp; stamp 1 with a valid payload is a no-op (so re-runs are safe);
anything else is preserved and reported. A file carrying a *different* stamp is
never rewritten even when its payload happens to satisfy v1 — pydantic ignores
extra fields, so a looser rule would let a run years from now silently
downgrade a file from a much later release. The ordering contract is: back up
`data/`, update the app, **close it**, run the script once, relaunch. The app
must be closed because its in-process caches race the rewrites, and it must
already be updated because a stamped `settings.json` is rejected outright by
the pre-stamp reader, which then reads every setting as unset and lets
`bootstrap_stats_dir` overwrite the file with a bare `{"stats_dir": ...}`,
destroying the stored identity. Between update and script the app boots loud
but inert. **Compatibility floor:** once stamped files exist, pre-stamp
releases are unsafe rollback targets, by that same bootstrap-wipe mechanism.

The script resolves the *state root* itself rather than reading the module
constants the services bind at import, because on an installed copy those bind
to the wrong tree: the launcher exports `CSD_STATE_DIR` only around the app
process, so a manual command inherits nothing, and the code lives in
`versions/<tag>/` while the durable state lives at the install root. Resolution
order is `--state-dir`, then `CSD_STATE_DIR`, then the install root inferred
from the script's own location, then the working directory; the chosen root and
the rule that chose it are printed before any file is touched. The inference
demands install-only evidence, not just the `versions/<tag>/scripts` shape: the
candidate root must also hold the installer's `install.json`. Shape alone would
classify a checkout that happens to sit under a directory named `versions` as
an install and convert its parent, which is the silent wrong-tree write this
resolution exists to prevent; without the evidence the inference stays out and
the working directory wins, which is what a source checkout wants anyway. The installed command runs the release's
own `versions/<tag>/.venv/Scripts/python.exe` by absolute path, because a
standard install deliberately puts neither uv nor Python on `PATH` (see the
script's docstring for the exact snippet).

Note for the first release that actually *migrates* data: the launcher's staged
trial run executes load-time migrations before `/health` is consulted, so that
PR has to consider the trial window — for example by migrating only after
promotion.

Rejected: a string marker (an integer sorts and compares without a parser); a
missing-means-v1 grandfather rule (see above); a single global
`data/schema_version` sidecar (the three stores version independently, and a
sidecar can desynchronize from the files it describes); rewriting files to
preserve unknown keys (it converts a typo into permanent silent state); tolerating
unknown keys within a version for settings and visibility (playlists keep
`PlaylistData`'s ignore-extras deliberately, for the reason above); best-effort
reads of future files (guessing at a format the build does not know is how
data gets corrupted rather than preserved); move-instead-of-copy backups (a
failed write would leave nothing at the file's own path); deferring the import
guard to the v2 release (the vulnerable writer is this release's own import
path); and a reservation registry for import destinations (a second source of
truth that can drift from the filesystem, where the destination point-check
asks the only authority there is).

Supersedes, on these narrow points only: the 2026-08-02 settings entry's "no
`schema_version`" sentence, and the 2026-07-19 update-contract entry's position
that the durable state is schema-stable enough for a format break to be handled
by a manual step called out in its PR.
