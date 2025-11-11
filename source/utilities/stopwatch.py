import logging
import time

logger = logging.getLogger(__name__)


class Stopwatch:
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.running = False

    def start(self):
        if not self.running:
            self.start_time = time.time()
            self.running = True
            logger.debug("Stopwatch started.")
        else:
            logger.debug("Stopwatch is already running.")

    def stop(self):
        if self.running:
            self.end_time = time.time()
            self.running = False
            elapsed_time = self.end_time - self.start_time
            logger.debug(
                f"Stopwatch stopped. Elapsed time: {elapsed_time:.2f} seconds."
            )
            return elapsed_time
        else:
            logger.debug("Stopwatch is not running.")
            return None

    def reset(self):
        self.start_time = None
        self.end_time = None
        self.running = False
        logger.debug("Stopwatch reset.")
