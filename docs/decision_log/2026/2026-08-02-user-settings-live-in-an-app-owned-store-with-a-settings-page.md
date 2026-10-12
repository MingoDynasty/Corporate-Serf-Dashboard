# 2026-08-02: User Settings Live In An App-Owned Store With A Settings Page

Status: Accepted

Where the KovaaK's stats live, the KovaaK's username, and the Steam ID have
moved out of the hand-edited configuration file into a small file the app
owns and writes. A Settings page inside the app shows and changes all three,
so ordinary use no longer needs a text editor. The configuration file keeps
only what a person genuinely sets by hand, such as the port. An update never
blocks on editing that file: keys a release no longer knows about are named
in one warning and ignored.

Decision — **one home, one writer**: every parameter lives in exactly one
file, and every file has exactly one owner. `config.toml` is human-owned and
app-read-only. `data/settings.json` is app-owned and written only through
`source/config/settings_service.py`, whose mechanics mirror the playlist
visibility store (module `RLock`, in-process cache, temp file + `fsync` +
`replace_with_retry`, tolerant reads). Nothing else ever writes it — the
installer included.

The schema is flat, three string keys, no `schema_version`, no nesting.
(**Superseded on the `schema_version` point only** by the 2026-08-11
durable-store stamp entry: the file now carries a top-level integer
`schema_version`, unknown keys are invalid rather than ignored, and an
unusable file no longer rewrites itself on the next automatic write. The flat
three-key schema and the unset semantics below are unchanged.)
Unset semantics are deliberately flat too: a missing key, an empty value, and
a missing, unreadable, or malformed file all mean *not configured* — no
identity disables rank lookups, no usable `stats_dir` runs the app empty. A
malformed file is warned about once, treated as holding no keys, and rewritten
whole by the next *user-initiated* save (which copies it aside first); it is
never fatal. Hand-editing while the app is
stopped stays a legitimate escape hatch, but edits made while it runs are not
picked up, because reads are cached in-process. Only the bootstrap in the next
entry distinguishes an absent key from an empty one.

`ConfigData` therefore drops all three fields and `example.toml` drops their
entries; the installed `config.toml` is `port` only. **Unknown `config.toml`
keys are warn-logged and ignored** — a permanent design choice, not a
transition shim. It is the removed-field mirror of the update contract's
"releases must read older state" rule, and it is what makes every promotion
boundary and every rollback safe by construction: a config carrying retired
keys runs on both the outgoing and the incoming version. The governing rule
follows from it — **through any promotion boundary, `config.toml` stays in a
shape both versions can read, and cleanup happens only after promotion**. (An
earlier revision claimed pydantic rejected unknown keys and would fail startup
on an unmigrated config; that behavior never existed, and the warning replaces
the imagined typo protection with visible, non-fatal feedback.) Migration is
manual and never blocks an update, per the single-user no-compat-shims
convention: there are no in-app migrations.

The page at `/settings` edits the three values with one Save. The write is
all-or-nothing — any field error writes nothing, so the store never holds half
a form — and a successful save writes every key, empty string included, which
is what keeps "cleared" distinguishable from "never set". Validation is
offline only: `stats_dir` must be an existing directory or empty, and
`steam_id` must be shaped like a SteamID64 (17 ASCII digits at or above the
universe-1 base `76561197960265728`, tightened from digits-only as the arc
shipped, because an account ID or a SteamID3 fragment is digits too). The
username is free text; confirming it against KovaaK's is detection territory
and belongs to a later proposal. The form is built per visit from the stored
view rather than the pinned accessors, so it always shows what is on disk. A
write that fails is caught and reported in the status line rather than
escaping into a request the user cannot see. State-writing page callbacks are
`n_clicks`-guarded with a None-trigger regression test, because under
DashProxy a callback can still fire once on page load despite
`prevent_initial_call`.

Provenance: distilled from `docs/settings_store_and_page_proposal.md`
(proposed in PR #171, register R1–R8, amended twice during review), shipped in
PRs #181, #182, #183, and #184; the proposal file is deleted in the shipping
PR and git history holds its full text.
