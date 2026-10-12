# 2026-07-19: All Mutable State Lives Under An Explicit State Root

Status: Accepted

Decision: `CSD_STATE_DIR` names the directory holding every mutable file —
`config.toml` and everything under `data/` (playlists, logs, preferences,
caches). Unset means the current working directory, so dev checkouts behave
exactly as before. Bundled read-only assets (`resources/benchmarks`) stop
resolving from the working directory and resolve relative to the installed
package instead, since they ship with the code. `source/utilities/paths.py`
centralizes both rules.

Why: without this split, versioned code directories cannot work at all. Running
the app from a fresh version directory would lose `config.toml` and `data/`;
running it from the state root would lose `resources/benchmarks`. An environment
variable keeps the contract explicit and testable, and lets the launcher — not
the app — own the choice of directories. (An early revision of the proposal
claimed the installer needed zero code changes; that claim was wrong and the
external review killed it.)
