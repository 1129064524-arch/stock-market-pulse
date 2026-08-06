"""Market quote models exposed by the versioned API."""

from typing import Optional

from pydantic import BaseModel, Field


class MarketSnapshot(BaseModel):
    captured_at: str
    indices: dict[str, float]
    total_amount: float = 0.0
    up_count: int
    down_count: int
    limit_up: int = 0


class StockSummary(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")
    name: str
    price: float
    change_pct: float
    volume: float = 0.0
    amount: float = 0.0
    turnover: float = 0.0
    sector: str = "全市场"
    main_inflow: float = 0.0


class StockDetail(StockSummary):
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    pre_close: float = 0.0
    amplitude: float = 0.0
    pe_ttm: Optional[float] = None
    total_mv: Optional[float] = None


class Bar(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float = 0.0
    ma5: Optional[float] = None
    ma20: Optional[float] = None


class SectorStat(BaseModel):
    name: str
    avg_pct: float
    up_ratio: float = 0.0
    stock_count: int = 0


class Mover(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")
    name: str
    price: float
    change_pct: float
    reason: str
