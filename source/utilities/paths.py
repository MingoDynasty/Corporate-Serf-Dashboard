"""Filesystem roots for mutable state and bundled read-only assets.

Two roots, because a deployed install runs code out of a per-version
directory that is pruned on update while state has to survive it:

- **state root** — everything the app or the user writes: ``config.toml``
  and everything under ``data/``. Named by ``CSD_STATE_DIR``, which the
  launcher owns; the app only ever reads it. Unset (dev checkouts, tests)
  means the current working directory, i.e. exactly today's behavior.
- **package root** — the code tree, holding read-only assets that ship with
  the code (``resources/benchmarks``). Derived from this file's location so
  it is correct no matter what the working directory is.
"""

import os
from pathlib import Path

STATE_DIR_ENV_VAR = "CSD_STATE_DIR"


def state_dir() -> Path:
    """Return the root directory holding all mutable app state."""
    configured = os.environ.get(STATE_DIR_ENV_VAR)
    if configured:
        return Path(configured).resolve()
    return Path.cwd().resolve()


def package_root() -> Path:
    """Return the root of the code tree (the parent of ``source/``)."""
    return Path(__file__).resolve().parents[2]
