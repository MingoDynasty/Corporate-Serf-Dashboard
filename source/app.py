"""
Entrypoint to the Corporate Serf Dashboard app.
"""

import json
import logging
import socket
import sys
import tomllib
from dataclasses import asdict
from logging.handlers import RotatingFileHandler
from pathlib import Path

from dash_extensions.enrich import DashProxy
from pydantic import ValidationError
from waitress import serve
from watchdog.observers import Observer

from source.app_shell import APP_INDEX_STRING, layout
from source.config.config_service import (
    CONFIG_ERROR_MESSAGE,
    config_file_path,
    get_config,
)
from source.health import register_health_endpoint
from source.kovaaks.api_service import set_request_timeout
from source.kovaaks.data_service import initialize_kovaaks_data, load_playlists
from source.kovaaks.percentile_warmup_service import (
    start_percentile_warmup_worker,
)
from source.my_watchdog.file_watchdog import NewFileHandler
from source.utilities.build_info import get_build_info
from source.utilities.paths import state_dir

# Logging setup
LOG_DIR = state_dir() / "data" / "logs"
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(threadName)s | %(name)s | %(message)s"
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3


def make_file_handler(filename: str, level: int) -> RotatingFileHandler:
    """Create a rotating file handler for one app log file."""
    handler = RotatingFileHandler(
        LOG_DIR / filename,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
        delay=True,
    )
    handler.setLevel(level)
    return handler


def configure_logging() -> None:
    """Configure stdout and rotating file logging for the app process."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    logging.basicConfig(
        level=logging.DEBUG,
        format=LOG_FORMAT,
        handlers=[
            console_handler,
            make_file_handler("debug.log", logging.DEBUG),
            make_file_handler("info.log", logging.INFO),
        ],
        force=True,
    )


configure_logging()

logger = logging.getLogger(__name__)


def app_name() -> str:
    """Name the app for the browser title, versioned only by a release tag."""
    tag = get_build_info().tag
    return f"Corporate Serf Dashboard {tag}" if tag else "Corporate Serf Dashboard"


APP_NAME = app_name()
app = DashProxy(
    title=APP_NAME,
    update_title=None,
    assets_folder="../assets",
    index_string=APP_INDEX_STRING,
    use_pages=True,  # enable Dash pages
)
app.layout = layout()  # layout logic encapsulated in another file
register_health_endpoint(app.server)


def bind_server_socket(port: int) -> socket.socket:
    """
    Bind the app's listening socket, or exit with an actionable error.

    Windows lets a second process bind a port another process is already
    serving, which splits incoming connections nondeterministically between
    the two instances -- a second copy of the dashboard then answers some
    requests with its own state. ``SO_EXCLUSIVEADDRUSE`` (Windows only)
    makes the second bind fail instead, so the duplicate exits immediately
    rather than quietly stealing traffic. Elsewhere a plain bind already
    refuses the second binder.

    The socket is returned bound but not listening: waitress calls
    ``listen()`` itself for sockets handed to it via ``sockets=``.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    # Only the bind is caught: a setsockopt failure is a bug, and reporting it
    # as a busy port would send the reader chasing a conflict that isn't there.
    try:
        sock.bind(("127.0.0.1", port))
    except OSError:
        sock.close()
        print(
            f"Startup error: port {port} is already in use -- most likely "
            "another copy of the dashboard is already running, or another "
            "program has taken the port (Steam uses 8080). Close that "
            f"program, or set a different port in {config_file_path()}.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
    return sock


def main() -> None:
    """
    Main entry point.
    :return: None.
    """
    build_info = get_build_info()
    # Bug reports arrive with debug.log, so the log is where build identity
    # matters most.
    logger.info(
        "Build %s, %s",
        build_info.short_description,
        build_info.release_label,
    )

    try:
        config = get_config()
    except OSError, UnicodeDecodeError, tomllib.TOMLDecodeError, ValidationError:
        print(CONFIG_ERROR_MESSAGE, file=sys.stderr)
        raise SystemExit(1) from None

    # Checked before anything uses it: the watchdog observer is the first
    # consumer and throws a raw traceback at a missing directory, which is
    # what example.toml's "Change me!" placeholder produces on first run.
    if not Path(config.stats_dir).is_dir():
        print(
            f'Configuration error: stats_dir "{config.stats_dir}" is not an '
            f"existing directory -- edit {config_file_path()} and set "
            "stats_dir to your KovaaK's stats folder, usually "
            "<Steam library>/steamapps/common/FPSAimTrainer/FPSAimTrainer/stats",
            file=sys.stderr,
        )
        raise SystemExit(1)

    logger.debug(
        "Loaded config:\n%s",
        json.dumps(asdict(config), indent=2),
    )

    set_request_timeout(config.kovaaks_api_timeout_seconds)

    load_playlists()

    # Initialize scenario data
    initialize_kovaaks_data(config.stats_dir)

    # The warmup queue is the played/visible intersection, so it can only be
    # assembled after both playlists and local CSV stats have loaded.
    start_percentile_warmup_worker(config)

    # Monitor for new files
    event_handler = NewFileHandler()
    observer = Observer()
    observer.schedule(
        event_handler,
        config.stats_dir,
        recursive=False,
    )  # Set recursive=True to monitor subdirectories
    observer.start()
    logger.info("Monitoring directory: %s", config.stats_dir)

    try:
        # Run the Dash app. `app.run()` uses Flask's development server even when
        # debug is disabled, so switch to Waitress for non-debug runs.
        if config.debug:
            app.run(
                debug=True,
                use_reloader=False,
                host="localhost",
                port=config.port,
            )
        else:
            # Each Home poll tick bursts several callback POSTs at once;
            # Waitress's default 4 threads left no headroom (task queue depth
            # warnings with a single open tab).
            serve(app.server, sockets=[bind_server_socket(config.port)], threads=8)
    finally:
        observer.stop()
        observer.join()  # Wait until the observer thread terminates


if __name__ == "__main__":
    main()
