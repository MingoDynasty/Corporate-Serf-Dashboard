# Config Initialization Proposal

**Status:** Accepted — Option B, full scope (design review 2026-07-09). Ready
to implement. The shipping PR distills this into `decision_log.md`, deletes
this file, and removes the tech-debt entry (AGENTS.md "Shipping a proposal";
the roadmap/product steps don't apply — this is not a product feature).

## Problem

`source/config/config_service.py` runs `config = load_config()` at module
import (inside a top-level `try/except`). Because nearly everything imports
this module — directly or transitively through `app.py`, `data_service.py`,
`home.py`, `file_watchdog.py`, `playlist_scenarios_service.py`,
`playlist_overview_service.py` — importing any of them triggers a config read
and, on a missing/invalid `config.toml`, a `SystemExit(1)`.

Two consequences:

1. **Import-time side effects.** You cannot import the app's modules in a test
   or REPL without a valid `config.toml` on disk.
2. **A by-value singleton.** Six modules bind the value with
   `from source.config.config_service import config`, so moving the load later
   requires converting the access pattern at every call site.

The load-bearing consequence, found in review: the import-time load forces the
pytest harness to intercept at the *file* level. `tests/conftest.py`
**overwrites the real repo-root `config.toml`** at session start with a test
config and restores it at session end — with the backup held **only in process
memory**. Abnormal termination (kill, OOM, power loss) permanently replaces the
user's config with the test one; two concurrent pytest runs in the same
checkout corrupt each other's backup/restore chain; and this mechanism is the
root cause of the standing "never run gates and the preview app concurrently
from the same worktree" restriction.

## Options considered

- **A — Accept as-is.** Rejected: it preserves the conftest file-swap hazard
  above, which is a real operational risk, not an aesthetic complaint.
- **B — Lazy `get_config()` accessor.** **Accepted**, full scope (below).
- **B-middle — env-var override for `CONFIG_FILE`.** Would fix the conftest
  hazard for ~10 lines while keeping the import-time load. Rejected on the
  repo's own testing philosophy (AGENTS.md): a test-only production knob is the
  discouraged kind of seam; `get_config()` is the sanctioned kind (it also
  improves the production design — startup owns loading, modules import-safe).
- **C — explicit init + module-attribute access / D — dependency injection.**
  Rejected: more ceremony (C) or far more churn (D) than B, no added benefit at
  this codebase's scale.

## Decision record — design review findings (2026-07-09)

1. **Call-site census:** ~24 `config.` attribute reads across the six
   importing modules, **all inside function bodies** — zero module-level
   access anywhere in `source/`. The conversion is mechanical; `home.py`
   already funnels five of them through `_rank_lookup_config()`, and the two
   playlist services funnel five each through their rank-lookup helpers.
   (`playlist_overview_service.py` joined in PR #78, after the review's
   original five-module census — re-grep the import at implementation HEAD.)
2. **Conftest hazard** (see Problem): retired entirely by B — tests seed the
   loader in-process and never touch the real `config.toml`.
3. **`load_playlists()` is in scope — required, not optional.** Today a bad
   config exits at `app.py`'s config import, *before* `configure_logging()`
   and before `data_service` imports. Under B with `load_playlists()` left at
   import, the chain survives to the playlist scan; in a cwd without
   `resources/playlists` that emits a warning through logging's last-resort
   handler → **stderr noise ahead of the friendly config error**, breaking
   `test_config_service`'s exact-stderr assertion and changing user-visible
   bad-config behavior. Moving `load_playlists()` into `main()` after config
   validation preserves the current contract exactly.
4. **Raise-and-translate.** `get_config()` raises (`OSError`,
   `UnicodeDecodeError`, `tomllib.TOMLDecodeError`, `ValidationError`);
   `main()` catches and reproduces the exact current stderr message +
   `SystemExit(1)` + no traceback. `config_service` becomes import-safe and
   library-like. The existing subprocess test pins this contract unchanged.

## Implementation shape

- `config_service.py`: drop the module-level `try/except` and `config` global;
  add `@functools.cache def get_config() -> ConfigData`. (`functools.cache`
  does not cache exceptions, and `main()` populates it before any threads
  exist — no concurrency wrinkle.)
- Convert the six modules: `from … import get_config`; call sites become
  `get_config().x` (or a local `config = get_config()` where a function reads
  several fields, as `_rank_lookup_config` already does).
- `app.py` `main()` order: `get_config()` (with error translation) →
  `load_playlists()` → `initialize_kovaaks_data(...)` → observer → serve.
- `tests/conftest.py`: replace the sessionstart/sessionfinish file-swap with an
  autouse fixture that monkeypatches `load_config` (or seeds the cache) and
  calls `get_config.cache_clear()` around it. The subprocess startup test in
  `test_config_service.py` stays exactly as-is — it exercises the real path.
- Test ripple: grep tests for reliance on import-time playlist loading
  (`test_playlist_pages.py`, `test_playlist_rekey.py`,
  `test_playlist_scenarios_service.py`, …) and call `load_playlists()`
  explicitly via fixture where needed.

## Constraints

- Boundary behavior is frozen: bad config → exit code 1, the exact existing
  stderr message, empty stdout, no traceback.
- Committed blobs LF; standard merge bar (ruff format/check, mypy, pytest).
