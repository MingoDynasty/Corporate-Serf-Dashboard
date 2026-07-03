"""Provide elapsed-time measurements for diagnostic logging."""

import logging
import time

logger = logging.getLogger(__name__)


class Stopwatch:
    """Measure elapsed wall-clock time across a named operation."""

    def __init__(self):
        """Initialize a stopped stopwatch with no recorded timestamps."""
        self.start_time = None
        self.end_time = None
        self.running = False

    def start(self):
        """Start timing unless the stopwatch is already running."""
        if not self.running:
            self.start_time = time.time()
            self.running = True

    def stop(self):
        """Stop timing while preserving the elapsed interval."""
        if self.running:
            self.end_time = time.time()
            self.running = False

    def elapsed(self) -> float:
        """Return the elapsed interval in seconds."""
        return self.end_time - self.start_time

    def reset(self):
        """Clear recorded timestamps and return to the stopped state."""
        self.start_time = None
        self.end_time = None
        self.running = False
