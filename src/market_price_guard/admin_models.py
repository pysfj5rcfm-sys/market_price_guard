from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


VERSION = "v0.8.1"
SCOPE_CLASSIFICATION = "local FastAPI admin pipeline runner and output bundle UI"

ACCOUNTS = ["tech", "energy"]
LAYERS = ["operation", "operation_candidate", "watchlist", "scan"]
INCLUDE_ACTION = "a" + "dd"
MOVE_ACTION = "move"
REMOVE_ACTION = "remove"

INSTRUMENT_TYPES = [
    "A-share ETF",
    "A-share stock",
    "HK stock / ETF",
    "US stock / ETF",
    "index / reference",
    "manual asset",
    "other",
]

TECH_CATEGORIES = [
    "Nasdaq / QDII",
    "AI",
    "Communication / CPO",
    "Semiconductor / Chip",
    "HK Tech",
    "AI PCB / Event Watch",
    "Broad Risk Preference",
    "Defensive Asset",
    "Other",
]

ENERGY_CATEGORIES = [
    "Oil / Gas",
    "Metals / Gold / Copper",
    "Nuclear Power",
    "Electricity / Utility",
    "Coal",
    "HK Energy",
    "Broad Risk Preference",
    "Defensive Asset",
    "Other",
]


@dataclass(frozen=True)
class SymbolInference:
    raw_symbol: str
    canonical_symbol: str
    inferred_market: str
    inferred_asset_type: str
    status: str
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SymbolAnalysis:
    account: str
    target_layer: str
    raw_symbol: str
    canonical_symbol: str
    inferred_market: str
    inferred_asset_type: str
    registry_status: str
    registry_entry: dict[str, Any]
    existing_layers: list[str]
    duplicate_status: str
    policy_warnings: list[str]
    suggested_category: str
    registry_stub_needed: bool
    instrument_type: str = ""
    category: str = ""
    display_name: str = ""
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LayerActionPlan:
    operation_type: str
    account: str
    symbol: str
    canonical_symbol: str
    source_layer: str
    target_layer: str
    files_to_modify: list[str]
    root_mirror_sync_plan: list[str]
    registry_stub_plan: dict[str, Any]
    policy_warnings: list[str]
    before_counts: dict[str, int]
    after_counts: dict[str, int]
    validation_plan: list[str]
    diff_preview: list[str]
    apply_allowed: bool
    blocking_reasons: list[str] = field(default_factory=list)
    structural_warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LayerActionResult:
    plan: LayerActionPlan
    success: bool
    validation_status: str
    backup_path: str
    audit_path: str
    partial_changes: list[str]
    errors: list[str]

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["plan"] = self.plan.as_dict()
        return data
