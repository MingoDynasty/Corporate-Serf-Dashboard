"""Atomic file replacement that survives transient Windows file locks.

``os.replace`` occasionally fails on Windows with ``PermissionError`` when
antivirus or the search indexer briefly holds the destination file open. A
short retry clears these transient locks. Several writers across the app and
the benchmark importer need the same loop, so it lives here once rather than
copied per call site.
"""

import logging
import os
import time
from pathlib import Path

REPLACE_RETRY_DELAYS_SECONDS = (0.05, 0.1)  # Windows AV/indexer file locks.


def replace_with_retry(
    source: Path,
    destination: Path,
    *,
    logger: logging.Logger,
    delays: tuple[float, ...] = REPLACE_RETRY_DELAYS_SECONDS,
) -> None:
    """Atomically replace ``destination`` with ``source``, retrying on locks.

    Retries ``os.replace`` on Windows ``PermissionError`` (antivirus/indexer
    holding the destination open), sleeping ``delays`` between attempts, then
    re-raises once the retries are exhausted. Warnings are emitted through the
    caller-supplied ``logger`` to preserve per-module attribution.
    """
    for retry_delay in (*delays, None):
        try:
            os.replace(source, destination)
            return
        except PermissionError:
            if retry_delay is None:
                raise
            logger.warning("Retrying replace after PermissionError: %s", destination)
            time.sleep(retry_delay)
