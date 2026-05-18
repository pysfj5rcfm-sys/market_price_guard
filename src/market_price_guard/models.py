from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


MarketStatus = Literal["open", "closed", "manual", "unknown"]


class Instrument(BaseModel):
    symbol: str
    name: str
    market: str
    core: bool = True
    provider: str = "mock"
    required_for_operation: bool = False


class WatchProject(BaseModel):
    display_name: str
    allow_full_detail: bool
    instruments: list[Instrument]


class Watchlist(BaseModel):
    projects: dict[str, WatchProject]


class RawPrice(BaseModel):
    symbol: str
    price: float | None = None
    currency: str = ""
    source: str
    quote_time: datetime | None = None
    fetch_time: datetime | None = None
    market_status: MarketStatus = "unknown"
    entry_time: datetime | None = None

    @field_validator("price")
    @classmethod
    def price_must_be_positive(cls, value: float | None) -> float | None:
        if value is not None and value <= 0:
            raise ValueError("price must be positive")
        return value


class PriceRecord(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    project: str
    symbol: str
    name: str
    market: str
    price: float | None
    currency: str
    source: str
    quote_time: datetime | None
    fetch_time: datetime | None
    market_status: MarketStatus
    is_stale: bool
    stale_reason: str = Field(default="")
    core: bool = True
    required_for_operation: bool = False

    def output_dict(self) -> dict[str, object]:
        data = self.model_dump()
        data.pop("core", None)
        return data
