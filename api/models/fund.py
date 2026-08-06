"""Fund and public holdings response models."""

from pydantic import BaseModel, Field


class HoldingItem(BaseModel):
    stock_code: str = Field(pattern=r"^\d{6}$")
    stock_name: str
    weight_pct: float
    report_date: str


class FundSummary(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")
    name: str
    nav: float
    estimate_pct: float
    fund_type: str
    theme: str
