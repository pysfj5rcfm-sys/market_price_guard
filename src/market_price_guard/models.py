from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


MarketStatus = Literal["open", "closed", "manual", "unknown"]
QuoteTrustTier = Literal["operation", "reference", "development"]
QuotePurpose = Literal["operation", "reference"]


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
    asset_type: str | None = None
    project_scope: str | None = None
    role: str | None = None
    universe_tags: list[str] = Field(default_factory=list)
    universe_type: str = "core_holdings"
    default_quote_purpose: str | None = None
    report_group: str | None = None
    notes: str | None = None
    registry_found: bool = True
    unsupported_reason: str = ""


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
    quote_trust_tier: QuoteTrustTier | None = None
    usable_for_reference: bool | None = None
    quote_purpose: QuotePurpose = "operation"
    confirmation_required: bool | None = None
    operation_blocking_reason: str = ""
    reference_note: str = ""

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
    selected_provider: str = ""
    usable_for_operation: bool = False
    quote_trust_tier: QuoteTrustTier = "development"
    usable_for_reference: bool = False
    quote_purpose: QuotePurpose = "operation"
    confirmation_required: bool = True
    operation_blocking_reason: str = ""
    reference_note: str = ""
    reconciliation_enabled: bool = False
    source_agreement_status: str = ""
    compared_sources: str = ""
    reference_source: str = ""
    candidate_source: str = ""
    price_diff_abs: float | None = None
    price_diff_pct: float | None = None
    quote_time_gap_seconds: float | None = None
    reconciliation_note: str = ""
    operation_candidate_agreed: bool = False
    asset_type: str = ""
    project_scope: str = ""
    role: str = ""
    universe_tags: list[str] = Field(default_factory=list)
    universe_type: str = "core_holdings"
    default_quote_purpose: str = ""
    report_group: str = ""
    notes: str = ""
    registry_found: bool = True
    unsupported_reason: str = ""

    def output_dict(self) -> dict[str, object]:
        data = self.model_dump()
        data.pop("core", None)
        data.pop("source_note", None)
        data.pop("product_type", None)
        data.pop("price_type", None)
        data.pop("tradable", None)
        data.pop("fee_note", None)
        data.pop("asset_role", None)
        data.pop("quality_issues", None)
        data.pop("provider_diagnostics", None)
        return data
