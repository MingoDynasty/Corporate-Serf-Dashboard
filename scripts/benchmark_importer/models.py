from dataclasses import dataclass

from pydantic import BaseModel, RootModel


@dataclass()
class EvxlDatabaseItem:
    kovaaksBenchmarkId: int
    rankColors: dict[str, str]


class EvxlDifficulty(BaseModel):
    difficultyName: str
    kovaaksBenchmarkId: int
    sharecode: str
    rankColors: dict[str, str]


class EvxlBenchmark(BaseModel):
    benchmarkName: str
    difficulties: list[EvxlDifficulty]


class EvxlData(RootModel):
    root: list[EvxlBenchmark]


class EvxlPlaylistScenario(BaseModel):
    scenario_name: str


class EvxlPlaylist(BaseModel):
    playlist_name: str
    playlist_code: str
    scenario_list: list[EvxlPlaylistScenario]


class EvxlPlaylistByCodeResponse(BaseModel):
    playlist: EvxlPlaylist
