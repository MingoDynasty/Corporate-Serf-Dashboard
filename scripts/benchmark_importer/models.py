from dataclasses import dataclass

from pydantic import BaseModel, RootModel


@dataclass()
class EvxlDatabaseItem:
    kovaaksBenchmarkId: int
    rankColors: dict[str, str]


class EvxlSubcategory(BaseModel):
    subcategoryName: str
    color: str
    scenarioCount: int


class EvxlCategory(BaseModel):
    categoryName: str
    color: str
    subcategories: list[EvxlSubcategory]


class EvxlDifficulty(BaseModel):
    difficultyName: str
    kovaaksBenchmarkId: int
    sharecode: str
    rankColors: dict[str, str]
    categories: list[EvxlCategory]


class EvxlBenchmark(BaseModel):
    benchmarkName: str
    rankCalculation: str
    abbreviation: str
    color: str
    spreadsheetURL: str
    dateAdded: str
    hidden: bool = False
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


class ManifestEntry(BaseModel):
    file: str
    playlist_name: str
    kovaaks_benchmark_id: int
    rank_colors: list[tuple[str, str]]
    generated_at: str


class Manifest(RootModel[dict[str, ManifestEntry]]):
    pass


class FailureEntry(BaseModel):
    error: str
    recorded_at: str
    # The Evxl metadata the failure was recorded against. Entries written before
    # these fields existed default to a signature no live item can match, so they
    # are retried rather than skipped forever.
    kovaaks_benchmark_id: int | None = None
    rank_colors: list[tuple[str, str]] | None = None


class FailureLedger(RootModel[dict[str, FailureEntry]]):
    pass
