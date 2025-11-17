"""
Entrypoint to the Corporate Serf Dashboard app.
"""

import logging.config
import sys

from dash_extensions.enrich import DashProxy
from watchdog.observers import Observer

from source.app_shell import layout
from source.config.config_service import config
from source.kovaaks.data_service import initialize_kovaaks_data
from source.my_watchdog.file_watchdog import NewFileHandler

# Logging setup
logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

APP_NAME = "Corporate Serf Dashboard v1.0.0"  # TODO: is this used elsewhere in the app?
app = DashProxy(
    title=APP_NAME,
    update_title=None,
    assets_folder="../assets",
    use_pages=True,  # enable Dash pages
)
app.layout = layout()  # layout logic encapsulated in another file


def main() -> None:
    """
    Main entry point.
    :return: None.
    """
    logger.debug("Loaded config: %s", config)

    # Initialize scenario data
    initialize_kovaaks_data(config.stats_dir)

    # Monitor for new files
    event_handler = NewFileHandler()
    observer = Observer()
    observer.schedule(
        event_handler, config.stats_dir, recursive=False
    )  # Set recursive=True to monitor subdirectories
    observer.start()
    logger.info("Monitoring directory: %s", config.stats_dir)

    # Run the Dash app
    app.run(debug=True, use_reloader=False, host="localhost", port=config.port)

    # Probably don't need this, but I kept it anyway
    observer.stop()
    observer.join()  # Wait until the observer thread terminates


if __name__ == "__main__":
    main()
