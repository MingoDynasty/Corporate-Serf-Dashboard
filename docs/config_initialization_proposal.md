# Config Initialization Proposal

**Status:** Proposed — decision-first. The goal of this doc is to pick *how far
to go* (or to consciously accept the status quo), not to pre-commit to a large
refactor. Payoff is modest; the point is to decide deliberately rather than
drift.

## Problem

`source/config/config_service.py` runs `config = load_config()` at module
import (inside a top-level `try/except`). Because nearly everything imports
this module — directly or transitively through `app.py`, `data_service.py`,
`home.py`, `file_watchdog.py`, `playlist_scenarios_service.py` — importing any
of them triggers a config read and, on a missing/invalid `config.toml`, a
`SystemExit(1)`.

Two consequences:

1. **Import-time side effects.** You cannot import the app's modules in a test
   or REPL without a valid `config.toml` on disk. `tests/test_config_service.py`
   already works around this by spawning a *subprocess* (`python -m source.app`)
   to exercise the bad-config exit path, rather than importing anything.
2. **A by-value singleton.** Five modules bind the value with
   `from source.config.config_service import config`. The binding captures the
   object at import time, so simply moving the load later would leave those
   five names pointing at nothing unless the *access pattern* also changes.

Related import-time side effect (same spirit, separate call site):
`data_service.py` runs `load_playlists()` at import (bottom of the module). Call
it out so we decide whether it's in or out of scope; it is not the subject of
this proposal.

## Why this is non-trivial

The by-value import is the crux. "Load config in `main()` instead" is one line;
making the existing five call sites see that value is the actual work, and the
*right* access pattern is a genuine choice with testability trade-offs. It also
has to stay compatible with the pytest harness, which swaps the repo-root
`config.toml` for the whole session (see `tests/conftest.py`) — the subprocess
startup test in `test_config_service.py` must stay green.

## Options

**A — Accept as-is (close the tech-debt entry).**
Do nothing but optionally document the decision. Bad config already exits
cleanly with a concise message (shipped in `e4d3f08`), and the subprocess test
covers it. Cost: import side effects remain; config-dependent code stays
un-unit-testable without a `config.toml` present. This is the debt entry's
implicit current stance and is defensible for a single-user local app.

**B — Lazy accessor `get_config()` (recommended if we act).**
Replace the module-level `config` with a cached loader:

```python
@functools.cache
def get_config() -> ConfigData:
    ...  # load_config() + the current error handling
```

Convert the five `config` uses to `get_config()`. Load moves off the import
path (first *access* triggers it); `main()` can call `get_config()` explicitly
and own the error message. Tests override via `get_config.cache_clear()` +
monkeypatching, no subprocess needed. Least invasive way to actually remove the
import-time side effect while keeping singleton ergonomics.

**C — Explicit init in `main()`, module-attribute access.**
`main()` calls a `configure()` that populates a module global; the five sites
switch from `from x import config` to `import x` + `x.config`. Startup fully
owns load + error handling. Slightly more ceremony than B at every call site,
no real advantage over B for this codebase.

**D — Dependency injection (pass `ConfigData` through).**
Thread config as an argument. Cleanest for testing, but a large change across
call chains for a local single-user tool — almost certainly over-engineering
here. Listed for completeness; not recommended.

## Recommendation

Decide between **A** (accept and close) and **B** (lazy `get_config()` seam).
Both are honest endpoints; B buys unit-testability of startup/config-dependent
code for a small, mechanical diff. Avoid C and D. If B is chosen, decide
separately whether to fold the `load_playlists()` import-time call into the same
cleanup or leave it.

## Interactions / constraints

- `tests/conftest.py` swaps the repo-root `config.toml` for the pytest session;
  `test_config_service.py` spawns a subprocess to test the bad-config exit.
  Both must keep passing. Under B, the subprocess test still exercises the real
  startup path; add an in-process test for the loader as the new fast path.
- Keep the app boundary behavior: on bad config the *process* exits `1` with the
  existing stderr message and no traceback. A library-style `get_config()` that
  merely *raises* is fine as long as `main()` translates that to the clean exit.

## Open questions (decide at build time)

- How far: **A vs B** (this is the real decision).
- Include the `data_service.load_playlists()` import-time call, or leave it?
- Should `get_config()` exit the process itself, or raise and let `main()`
  translate? (Prefer raise-and-translate to keep the module import-safe.)
