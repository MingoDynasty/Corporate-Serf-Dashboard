"""
Pydantic models for Kovaak's Sensitivity API responses.
"""

from typing import List, Optional

from pydantic import BaseModel


class FieldOfView(BaseModel):
    FILMS: str
    SliderMax: int
    SliderMin: int


class Sensitivity(BaseModel):
    TypicalMaxCM: Optional[str] = None
    TypicalMinCM: Optional[str] = None
    InchesFormula: Optional[str] = None
    IncrementFormula: str


class SensitivityScale(BaseModel):
    FOV: Optional[FieldOfView] = None
    Sens: Optional[Sensitivity] = None
    ScaleName: str


class SensitivityAPIResponse(BaseModel):
    SensitivityAndFov: List[SensitivityScale]
