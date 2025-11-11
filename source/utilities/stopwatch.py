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

    def stop(self):
        if self.running:
            self.end_time = time.time()
            self.running = False

    def elapsed(self) -> float:
        return self.end_time - self.start_time

    def reset(self):
        self.start_time = None
        self.end_time = None
        self.running = False
