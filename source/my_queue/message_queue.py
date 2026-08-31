"""
Shared message my_queue between UI and File Watchdog components.
"""

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class NewFileMessage:
    """Dataclass models messages in this my_queue.

    Facts only: the watchdog reports what happened and every consumer derives
    its own verdict. A decision field here would let two consumers disagree
    about the same run, or let one of them read a value the other set.
    """

    datetime_created: datetime
    # True for a scenario's first run and for the first run at a new
    # sensitivity, which is exactly when the run cannot be judged against a
    # per-sensitivity history.
    is_new_sensitivity: bool
    nth_score: int
    # The run CSV's file name: unique per run, and the identity a celebration
    # decision names.
    run_id: str
    scenario_name: str
    # The scenario-wide best before this run, across every sensitivity. None
    # only when the scenario had no prior run at all.
    scenario_previous_best: Optional[float]
    score: float
    sensitivity: str


message_queue: deque[NewFileMessage] = deque()
