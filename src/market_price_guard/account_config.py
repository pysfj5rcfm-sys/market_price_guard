from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


LAYER_ORDER = ["operation", "operation_candidate", "watchlist", "scan"]


@dataclass(frozen=True)
class AccountLayerPaths:
    account: str
    project_path: str
    root_mirror_path: str
    layer_files: dict[str, str]

    def universe_path(self, project_root: Path, layer: str) -> Path:
        return project_root / self.layer_files[layer]

    def missing_config_files(self, project_root: Path) -> list[str]:
        return [relative for relative in self.layer_files.values() if not (project_root / relative).exists()]

    def account_bootstrapped(self, project_root: Path) -> bool:
        return not self.missing_config_files(project_root)


def normalize_account(value: str) -> str:
    account = str(value).strip().lower().replace("-", "_")
    if account not in {"tech", "energy"}:
        raise ValueError(f"unsupported account: {value}")
    return account


def account_layer_paths(account: str) -> AccountLayerPaths:
    account = normalize_account(account)
    if account == "tech":
        layer_files = {
            "operation": "config/universes/tech_core.yaml",
            "operation_candidate": "config/universes/tech_operation_candidates.yaml",
            "watchlist": "config/universes/tech_watchlist.yaml",
            "scan": "config/universes/tech_scan_ai.yaml",
        }
    else:
        layer_files = {
            "operation": "config/universes/energy_core.yaml",
            "operation_candidate": "config/universes/energy_operation_candidates.yaml",
            "watchlist": "config/universes/energy_watchlist.yaml",
            "scan": "config/universes/energy_scan.yaml",
        }
    return AccountLayerPaths(
        account=account,
        project_path=f"projects.{account}",
        root_mirror_path=f"config/watchlist.yaml -> projects.{account}.layer_universes",
        layer_files=layer_files,
    )


def normalize_layer(value: str, account: str = "tech") -> str:
    account = normalize_account(account)
    key = str(value).strip().lower().replace("-", "_")
    aliases = {
        "operation": "operation",
        "core": "operation",
        f"{account}_core": "operation",
        "operation_candidate": "operation_candidate",
        "candidate": "operation_candidate",
        "operation_candidates": "operation_candidate",
        f"{account}_operation_candidates": "operation_candidate",
        "watchlist": "watchlist",
        f"{account}_watchlist": "watchlist",
        "scan": "scan",
        f"{account}_scan": "scan",
    }
    if account == "tech":
        aliases["tech_scan_ai"] = "scan"
    if key not in aliases:
        raise ValueError(f"invalid layer: {value}")
    return aliases[key]
