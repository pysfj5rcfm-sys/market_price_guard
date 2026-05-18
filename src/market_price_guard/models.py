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
    provider_priority: list[str] | None = None
    allow_mock_fallback_for_operation: bool = False
    allow_manual_fallback_for_operation: bool = False
    required_for_operation: bool = False
    asset_role: str | None = None


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
    name: str | None = None
    market: str | None = None
    quote_time: datetime | None = None
    fetch_time: datetime | None = None
    market_status: MarketStatus = "unknown"
    entry_time: datetime | None = None
    source_note: str | None = None
    product_type: str | None = None
    price_type: str | None = None
    tradable: bool | None = None
    fee_note: str | None = None
    project: str | None = None
    asset_role: str | None = None
    required_for_operation: bool | None = None
    quality_issues: list[str] = Field(default_factory=list)
    provider_diagnostics: dict[str, object] = Field(default_factory=dict)

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
    source_note: str | None = None
    product_type: str | None = None
    price_type: str | None = None
    tradable: bool | None = None
    fee_note: str | None = None
    asset_role: str | None = None
    quality_issues: list[str] = Field(default_factory=list)
    provider_diagnostics: dict[str, object] = Field(default_factory=dict)

    def output_dict(self) -> dict[str, object]:
        data = self.model_dump()
        data.pop("core", None)
        data.pop("required_for_operation", None)
        data.pop("source_note", None)
        data.pop("product_type", None)
        data.pop("price_type", None)
        data.pop("tradable", None)
        data.pop("fee_note", None)
        data.pop("asset_role", None)
        data.pop("quality_issues", None)
        data.pop("provider_diagnostics", None)
        return data
