"""Atomic file replacement that survives transient Windows file locks.

``os.replace`` occasionally fails on Windows with ``PermissionError`` when
antivirus or the search indexer briefly holds the destination file open. A
short retry clears these transient locks. Several writers across the app and
the benchmark importer need the same loop, so it lives here once rather than
copied per call site.

``atomic_write_text`` wraps that loop in the full write dance every durable
store performs: a uniquely named temp file beside the destination, flushed and
fsynced, then replaced into place and cleaned up on any failure.
``remove_stale_temp_files`` clears the temps that cleanup never reached,
because the process was killed before its replace.
"""

import logging
import os
import re
import threading
import time
from collections.abc import Callable
from pathlib import Path

REPLACE_RETRY_DELAYS_SECONDS = (0.05, 0.1)  # Windows AV/indexer file locks.

# Exactly the temp names the app's writers use, so the sweep removes nothing
# else: ``atomic_write_text`` and ``api_service._write_json`` write
# ``.<name>.<pid>.<tid>.tmp`` beside their destination, and
# ``store_schema.back_up_unusable_store`` writes ``.<name>.corrupt.<pid>.<tid>.tmp``.
# Every destination they write is a ``.json`` file. Matched case-sensitively,
# unlike a Windows glob.
_WRITER_TEMP_NAME = re.compile(r"\..+\.json(?:\.corrupt)?\.[0-9]+\.[0-9]+\.tmp")


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
            logger.warning('Retrying replace after PermissionError: "%s"', destination)
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


def remove_stale_temp_files(
    directory: Path,
    *,
    older_than: float,
    logger: logging.Logger,
    recursive: bool = False,
) -> int:
    """Delete the writer temps in ``directory`` older than ``older_than``.

    Returns how many were removed. Only a regular file whose whole name is a
    writer's temp name and whose modification time (seconds since the epoch)
    is before ``older_than`` is removed. A newer one may be a write still in
    flight. A missing directory removes nothing, and a directory that cannot
    be listed, an entry whose type cannot be read, or a temp that cannot be
    removed is logged and left. ``recursive`` descends into subdirectories but
    never through a symbolic link or junction. A backup-claim temp is a second
    hard link to its backup, so removing it leaves the backup whole.
    """
    try:
        with os.scandir(directory) as scan:
            entries = list(scan)
    except FileNotFoundError:
        return 0
    except OSError as error:
        logger.warning('Could not list "%s" for stale temp files: %s', directory, error)
        return 0

    removed = 0
    for entry in entries:
        # Windows may have to query an entry's metadata to answer these, and
        # that query can fail like any other.
        try:
            # follow_symlinks=False keeps a symbolic link out but not a
            # junction, which could carry the sweep outside this tree.
            descend = (
                recursive
                and entry.is_dir(follow_symlinks=False)
                and not entry.is_junction()
            )
            is_temp = (
                not descend
                and _WRITER_TEMP_NAME.fullmatch(entry.name) is not None
                and entry.is_file(follow_symlinks=False)
            )
        except OSError as error:
            logger.warning(
                'Could not check "%s" for stale temp files: %s', entry.path, error
            )
            continue
        if descend:
            removed += remove_stale_temp_files(
                Path(entry.path), older_than=older_than, logger=logger, recursive=True
            )
            continue
        if not is_temp:
            continue
        try:
            if entry.stat(follow_symlinks=False).st_mtime >= older_than:
                continue
            os.unlink(entry.path)
        except OSError as error:
            logger.warning(
                'Could not remove the stale temp "%s": %s', entry.path, error
            )
            continue
        logger.debug('Removed the stale temp "%s".', entry.path)
        removed += 1
    return removed
