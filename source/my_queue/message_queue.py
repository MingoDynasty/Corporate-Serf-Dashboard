"""
Shared message my_queue between UI and File Watchdog components.
"""

import queue
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class NewFileMessage:
    """Dataclass models messages in this my_queue."""

    datetime_created: datetime
    nth_score: int
    scenario_name: str
    score: float
    sensitivity: str


message_queue: queue.Queue[NewFileMessage] = queue.Queue()
