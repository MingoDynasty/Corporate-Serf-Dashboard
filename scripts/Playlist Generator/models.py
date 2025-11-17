from dataclasses import dataclass
from typing import Dict, List

from pydantic import BaseModel, RootModel


@dataclass()
class EvxlDatabaseItem:
    kovaaksBenchmarkId: int
    rankColors: Dict[str, str]


class EvxlDifficulty(BaseModel):
    kovaaksBenchmarkId: int
    sharecode: str
    rankColors: Dict[str, str]


class EvxlBenchmark(BaseModel):
    difficulties: List[EvxlDifficulty]


class EvxlData(RootModel):
    root: List[EvxlBenchmark]
