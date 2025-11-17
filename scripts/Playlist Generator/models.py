from dataclasses import dataclass

from pydantic import BaseModel, RootModel


@dataclass()
class EvxlDatabaseItem:
    kovaaksBenchmarkId: int
    rankColors: dict[str, str]


class EvxlDifficulty(BaseModel):
    kovaaksBenchmarkId: int
    sharecode: str
    rankColors: dict[str, str]


class EvxlBenchmark(BaseModel):
    difficulties: list[EvxlDifficulty]


class EvxlData(RootModel):
    root: list[EvxlBenchmark]
