"""Fund holding penetration models."""

from pydantic import BaseModel, Field


class LinkedStock(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")
    name: str
    weight_pct: float
    change_pct: float
    contribution: float


class LinkageOverview(BaseModel):
    fund_code: str = Field(pattern=r"^\d{6}$")
    fund_name: str
    estimate_pct: float | None = None
    holdings_change_pct: float
    diff: float | None = None
    resonance: str
    top_contributors: list[LinkedStock]
