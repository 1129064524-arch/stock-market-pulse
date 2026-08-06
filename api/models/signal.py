"""Signal models for the versioned API."""

from typing import Any

from pydantic import BaseModel, Field


class SignalEvent(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")
    name: str
    rule_name: str
    rule_version: str
    score: float
    direction: str
    evidence: dict[str, Any]
    risk_note: str
    triggered_at: str


class SignalStats(BaseModel):
    total_today: int
    bullish_count: int
    bearish_count: int
    top_rules: list[dict[str, Any]]
