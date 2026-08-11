"""Atomic file replacement that survives transient Windows file locks.

``os.replace`` occasionally fails on Windows with ``PermissionError`` when
antivirus or the search indexer briefly holds the destination file open. A
short retry clears these transient locks. Several writers across the app and
the benchmark importer need the same loop, so it lives here once rather than
copied per call site.

``atomic_write_text`` wraps that loop in the full write dance every durable
store performs: a uniquely named temp file beside the destination, flushed and
fsynced, then replaced into place and cleaned up on any failure.
"""

import logging
import os
import threading
import time
from collections.abc import Callable
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


def atomic_write_text(
    destination: Path,
    text: str,
    *,
    logger: logging.Logger,
    encoding: str = "utf-8",
    before_replace: Callable[[], None] | None = None,
) -> None:
    """Write ``text`` to ``destination`` atomically, leaving no temp file behind.

    ``before_replace`` runs after the temp file is durable and immediately
    before the replace, which is the only moment a writer can inspect the file
    it is about to overwrite without widening the window for someone else to
    change it. Raising from it refuses the write with the destination untouched.
    """
    temp_file = destination.with_name(
        f".{destination.name}.{os.getpid()}.{threading.get_ident()}.tmp"
    )
    try:
        with open(temp_file, "w", encoding=encoding) as file:
            file.write(text)
            file.flush()
            os.fsync(file.fileno())
        if before_replace is not None:
            before_replace()
        replace_with_retry(temp_file, destination, logger=logger)
    finally:
        temp_file.unlink(missing_ok=True)
