"""Log uncaught exceptions so crashes leave a record in the app log files.

Bug reports arrive with debug.log, but Python's default hooks print crash
tracebacks to stderr only -- gone once the console window closes. The worst
case is a background thread dying: the app keeps serving while the thread's
job has silently stopped. These hooks add the log-file record, then defer to
the interpreter's default hooks so console behavior is unchanged.
"""

import logging
import sys
import threading
from types import TracebackType

logger = logging.getLogger(__name__)

# Record attribute marking log records whose content the terminal already
# receives through a direct stderr write (a startup-error print, the default
# excepthooks' tracebacks). The app's console handler drops marked records so
# the terminal is not told twice; the file handlers keep them.
SUPPRESS_CONSOLE_KEY = "suppress_console"


def _log_uncaught_exception(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: TracebackType | None,
) -> None:
    """Record a main-thread crash, then defer to the default hook."""
    if not issubclass(exc_type, KeyboardInterrupt):
        # Ctrl+C is a normal way to stop a console app, not a crash.
        logger.critical(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback),
            extra={SUPPRESS_CONSOLE_KEY: True},
        )
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


def _log_uncaught_thread_exception(args: threading.ExceptHookArgs) -> None:
    """Record a thread crash, then defer to the default hook."""
    if issubclass(args.exc_type, SystemExit):
        # Match the default hook, which ignores SystemExit in threads.
        return
    # exc_value is only None for exotic C-level raises; log without the
    # traceback rather than fabricating an exception instance.
    exc_info = (
        (args.exc_type, args.exc_value, args.exc_traceback)
        if args.exc_value is not None
        else None
    )
    logger.critical(
        "Uncaught exception in thread %s",
        args.thread.name if args.thread is not None else "(unknown)",
        exc_info=exc_info,
        extra={SUPPRESS_CONSOLE_KEY: True},
    )
    threading.__excepthook__(args)


def install_crash_logging() -> None:
    """Install the crash-logging hooks for the main thread and worker threads."""
    sys.excepthook = _log_uncaught_exception
    threading.excepthook = _log_uncaught_thread_exception
