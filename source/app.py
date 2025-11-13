"""
Entrypoint to the Corporate Serf Dashboard app.
"""

import logging.config
import sys

import dash
from dash_extensions.enrich import DashProxy
from watchdog.observers import Observer

from config.config_service import config
from kovaaks.data_service import (
    initialize_kovaaks_data,
)
from my_watchdog.file_watchdog import NewFileHandler

# Logging setup
logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

APP_NAME = "Corporate Serf Dashboard v1.0.0"
app = DashProxy(
    title=APP_NAME,
    update_title=None,
    assets_folder="../assets",
    use_pages=True,  # turn on Dash pages
)


def serve_layout():
    """Define the layout of the application"""
    return dash.page_container


app.layout = serve_layout  # set the layout to the serve_layout function


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
    return


if __name__ == "__main__":
    main()
