"""
Entrypoint to the Corporate Serf Dashboard app.
"""

import errno
import ipaddress
import json
import logging
import socket
import sys
import tomllib
from dataclasses import asdict
from logging.handlers import RotatingFileHandler
from typing import NoReturn

from dash_extensions.enrich import DashProxy
from pydantic import ValidationError
from waitress import serve
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver

from source.app_shell import APP_INDEX_STRING, layout
from source.config.config_service import (
    DEFAULT_HOST,
    config_file_path,
    get_config,
)
from source.config.settings_service import (
    KOVAAKS_USERNAME_KEY,
    get_settings,
    get_usable_stats_dir,
    resolve_stats_dir,
)
from source.config.stats_dir_detection import bootstrap_stats_dir
from source.health import register_health_endpoint
from source.kovaaks.api_service import set_request_timeout
from source.kovaaks.data_service import (
    initialize_kovaaks_data,
    load_playlists,
    seed_leaderboard_ids_from_bundled_corpus,
)
from source.kovaaks.percentile_warmup_service import (
    start_percentile_warmup_worker,
)
from source.my_watchdog.file_watchdog import NewFileHandler
from source.utilities.build_info import get_build_info
from source.utilities.crash_logging import (
    SUPPRESS_CONSOLE_KEY,
    install_crash_logging,
)
from source.utilities.paths import log_dir

# Logging setup
LOG_DIR = log_dir()
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


def _console_should_emit(record: logging.LogRecord) -> bool:
    """Drop records whose content the terminal already got via stderr."""
    return not getattr(record, SUPPRESS_CONSOLE_KEY, False)


def configure_logging() -> None:
    """Configure stdout and rotating file logging for the app process."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.addFilter(_console_should_emit)

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
    # The app's own per-attempt request records (api_service._get_with_retry)
    # carry the params, status, duration, and attempt count, so urllib3's
    # transport chatter duplicated them -- 2,641 lines, ~16% of a sampled
    # debug.log. INFO keeps urllib3's warnings (its own retries, pool issues).
    logging.getLogger("urllib3").setLevel(logging.INFO)


configure_logging()
install_crash_logging()

logger = logging.getLogger(__name__)


def _log_startup_error(message: str) -> None:
    """Report a preflight failure on stderr and in the log files.

    Bug reports arrive with debug.log; stderr alone would leave a
    "won't start" report with a Build line and then nothing. The record
    skips the console handler -- the stderr print already covers the
    terminal, and a doubled message there would be noise.
    """
    logger.error(message, extra={SUPPRESS_CONSOLE_KEY: True})
    print(message, file=sys.stderr)


def log_rank_lookup_availability() -> None:
    """Note once, at startup, that leaderboard lookups are off for lack of a name.

    An unset username is a supported state -- the app runs fully offline -- so
    it is reported once here rather than per lookup. Home's Position field
    carries the user-facing half, with a link to the settings page.

    Reads the store rather than ``get_identity``: this is a report on what is
    configured, not a consumer of the identity, and it must not be the read
    that freezes the process pin.
    """
    if not get_settings().get(KOVAAKS_USERNAME_KEY):
        logger.info(
            "KovaaK's username not configured -- scenario position lookups "
            "disabled (set it in Settings)."
        )


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


def _bind_face(family: int, address: str, port: int) -> socket.socket:
    """Bind one address exclusively, returned bound but not listening."""
    sock = socket.socket(family, socket.SOCK_STREAM)
    if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    # Close before re-raising so a failed bind doesn't leak the socket; the
    # caller classifies the OSError (see bind_server_socket for the buckets).
    try:
        sock.bind((address, port))
    except OSError:
        sock.close()
        raise
    return sock


def _exit_port_taken(
    port: int, claimed: list[socket.socket], host: str = DEFAULT_HOST
) -> NoReturn:
    """Release any bound faces and exit with an actionable message."""
    for sock in claimed:
        sock.close()
    where = (
        "on both loopback addresses, 127.0.0.1 and [::1]"
        if host == DEFAULT_HOST
        else f"on {host}"
    )
    _log_startup_error(
        f"Startup error: port {port} is already in use -- most likely "
        "another copy of the dashboard is already running, or another "
        "program has taken the port (Steam uses 8080). The port must be free "
        f"{where}. Close that program, "
        f"or set a different port in {config_file_path()}."
    )
    raise SystemExit(1) from None


def _exit_bad_host(host: str, why: str) -> NoReturn:
    """Exit naming the host setting, for a host this machine cannot serve.

    Kept distinct from the port-taken exit: an address this machine does not
    hold is not fixed by freeing or changing the port, so pointing the user at
    the port would send them down a dead end.
    """
    _log_startup_error(
        f'Startup error: the configured host "{host}" {why} Set host in '
        f"{config_file_path()} to an address this machine holds, or remove it "
        "to serve this machine only."
    )
    raise SystemExit(1) from None


def host_address_family(host: str) -> int:
    """Validate ``host`` as an IP literal and return its address family.

    Literals only, deliberately: a *name* would be resolved, and resolution
    picks one face of whatever it resolves to. ``localhost`` would bind
    ``::1`` alone here and ``127.0.0.1`` alone on a resolver that orders IPv4
    first -- one loopback face held, the other left free for an unrelated
    process to squat on, which is the ambiguity the dual-face default bind
    exists to close. The empty string is the same trap wearing a different
    hat: ``getaddrinfo("", ...)`` yields ``AF_INET6``, so ``host = ""`` -- the
    natural way to write "unset" by hand -- would publish the app on ``::``,
    every IPv6 interface included, with none of the warnings that gate an
    explicit ``0.0.0.0``.

    Rejecting names costs nothing the documentation promised: ``README.md``,
    ``example.toml``, and the decision log all specify literals.
    """
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        _exit_bad_host(host, "is not an IP address.")
    return socket.AF_INET6 if address.version == 6 else socket.AF_INET


def bind_server_socket(port: int, host: str = DEFAULT_HOST) -> list[socket.socket]:
    """
    Bind the app's listening sockets, or exit with an actionable error.

    A ``host`` other than the default is an explicit choice of one address --
    ``0.0.0.0`` to serve every IPv4 interface, or a single LAN address -- and
    is bound alone (it must be an IP literal; see ``host_address_family``),
    since the ``::1`` companion below exists only to close a ``localhost``
    ambiguity that a specific address does not have. Under
    ``0.0.0.0`` nothing answers on ``::1``: a client that insists on IPv6
    loopback is refused, while ``localhost`` still connects because resolvers
    and browsers fall back to the IPv4 address. The app has no
    authentication, so every device that can reach the chosen address can read
    the run data and change the settings.

    On the default host both loopback faces are bound -- ``127.0.0.1`` and
    ``::1`` -- because Windows may resolve ``localhost`` to ``::1`` first.
    Binding IPv4 alone leaves the IPv6 face free for an unrelated process to
    squat on, and the browser then silently reaches that stranger instead of
    the dashboard.
    Claiming ``::1`` ourselves means ``localhost`` either reaches us (a
    specific bind wins over someone else's wildcard ``::`` listener) or the
    app exits loudly, never the middle case where it is quietly shadowed.

    Windows also lets a second process bind a port another process is already
    serving, which splits incoming connections nondeterministically between
    the two instances -- a second copy of the dashboard then answers some
    requests with its own state. ``SO_EXCLUSIVEADDRUSE`` (Windows only)
    makes the second bind fail instead, so the duplicate exits immediately
    rather than quietly stealing traffic. Elsewhere a plain bind already
    refuses the second binder.

    A machine without IPv6 is served on IPv4 alone: there ``localhost``
    resolves to IPv4 anyway, so the ambiguity disappears with the interface.

    Sockets are returned bound but not listening: waitress calls ``listen()``
    itself for each socket handed to it via ``sockets=``.
    """
    family = host_address_family(host)

    # Two buckets, keyed on errno. EADDRNOTAVAIL means the literal is well
    # formed but no interface here holds it -- a mistyped LAN address, or one this machine
    # has since lost via DHCP -- which changing the port cannot fix. Everything
    # else is treated as "port taken": socket creation and the
    # SO_EXCLUSIVEADDRUSE setsockopt essentially cannot fail on a fresh socket,
    # so folding them in rather than splitting hairs keeps the taxonomy to the
    # cases that actually happen.
    try:
        primary = _bind_face(family, host, port)
    except OSError as error:
        if error.errno == errno.EADDRNOTAVAIL:
            _exit_bad_host(host, "is not an address this machine holds.")
        _exit_port_taken(port, [], host)
    sockets = [primary]
    # Port 0 asks the OS to choose one. Both faces have to answer on the same
    # port, so the second bind asks for the port the first one was given.
    port = primary.getsockname()[1]

    if host != DEFAULT_HOST:
        return sockets

    try:
        sockets.append(_bind_face(socket.AF_INET6, "::1", port))
    except OSError as error:
        # Two buckets, keyed on errno: an IPv6-absence error (the family is
        # unsupported, or ::1 does not exist here) degrades to IPv4-only
        # service; every other OSError -- including the near-impossible
        # creation/setsockopt failure -- is treated as the port being taken.
        if error.errno not in (errno.EAFNOSUPPORT, errno.EADDRNOTAVAIL):
            _exit_port_taken(port, sockets)
        logger.info(
            "No IPv6 loopback available (%s); serving on 127.0.0.1 only.",
            error,
        )
    return sockets


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
        # Name the file: a deployed install reads its config from the state
        # root, not the working directory, so "config.toml" alone leaves the
        # user guessing which one. Missing vs. unparseable is deliberately not
        # split out -- opening the named file answers that immediately.
        _log_startup_error(
            f"Configuration error: could not load {config_file_path()} -- "
            "copy example.toml to config.toml."
        )
        raise SystemExit(1) from None

    logger.debug(
        "Loaded config:\n%s",
        json.dumps(asdict(config), indent=2),
    )

    set_request_timeout(config.kovaaks_api_timeout_seconds)

    load_playlists()

    # Fold the bundled corpus's embedded leaderboard IDs into the permanent
    # name->ID mapping cache before any rank lookup needs them.
    seed_leaderboard_ids_from_bundled_corpus()

    # Detect the stats directory when nothing ever configured one -- before the
    # pin below, so a first detection serves this boot instead of the next one.
    bootstrap_stats_dir()

    # Resolve the stats directory once, here: it is restart-scoped, and every
    # consumer reads the pin for the rest of the process (resolve_stats_dir).
    configured_stats_dir = resolve_stats_dir()
    stats_dir = get_usable_stats_dir()

    if stats_dir is None:
        # Not fatal: only `port` is needed to serve pages. Without a stats
        # directory the app is merely empty, and Home says so.
        logger.warning(
            "No usable KovaaK's stats directory (%s): serving with no run "
            "data, and skipping the initial scan and the file watchdog.",
            f'"{configured_stats_dir}" is not an existing directory'
            if configured_stats_dir
            else "not configured",
        )
    else:
        # Initialize scenario data
        initialize_kovaaks_data(stats_dir)

    log_rank_lookup_availability()

    # The warmup queue is the played/visible intersection, so it can only be
    # assembled after both playlists and local CSV stats have loaded.
    start_percentile_warmup_worker(config)

    # Monitor for new files
    observer: BaseObserver | None = None
    if stats_dir is not None:
        observer = Observer()
        observer.schedule(
            NewFileHandler(),
            stats_dir,
            recursive=False,
        )  # Set recursive=True to monitor subdirectories
        observer.start()
        logger.info("Monitoring directory: %s", stats_dir)

    try:
        # Run the Dash app. `app.run()` uses Flask's development server even when
        # debug is disabled, so switch to Waitress for non-debug runs.
        if config.debug:
            # This path never reaches bind_server_socket, so validate the host
            # here too -- otherwise a bad literal is a raw traceback on one
            # server path and an actionable message on the other.
            host_address_family(config.host)
            if config.host != DEFAULT_HOST:
                # Flask sets use_debugger from debug, and Dash forwards host
                # straight through, so this combination puts the Werkzeug
                # console on that network. It is PIN-gated, and debug is
                # documented dev-only, so this warns rather than refuses.
                logger.warning(
                    "debug is on and host is %s, so the interactive debugger "
                    "is reachable from that network, not just this machine. "
                    "Turn debug off in %s unless you meant this.",
                    config.host,
                    config_file_path(),
                )
            app.run(
                debug=True,
                use_reloader=False,
                host=config.host,
                port=config.port,
            )
        else:
            # Each Home poll tick bursts several callback POSTs at once;
            # Waitress's default 4 threads left no headroom (task queue depth
            # warnings with a single open tab).
            serve(
                app.server,
                sockets=bind_server_socket(config.port, config.host),
                threads=8,
            )
    finally:
        if observer is not None:
            observer.stop()
            observer.join()  # Wait until the observer thread terminates


if __name__ == "__main__":
    main()
