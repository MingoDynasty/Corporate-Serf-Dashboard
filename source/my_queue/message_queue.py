"""
Shared message my_queue between UI and File Watchdog components.
"""

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class NewFileMessage:
    """Dataclass models messages in this my_queue."""

    datetime_created: datetime
    nth_score: int
    previous_high_score: Optional[float]
    scenario_name: str
    score: float
    sensitivity: str


message_queue: deque[NewFileMessage] = deque()
