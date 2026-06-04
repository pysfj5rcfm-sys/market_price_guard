from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_audit_event(
    project_root: Path,
    *,
    operation: str,
    account: str,
    symbol: str,
    canonical_symbol: str,
    source_layer: str,
    target_layer: str,
    backup_path: str,
    validation_status: str,
    success: bool,
    warnings: list[str],
) -> Path:
    log_path = Path(project_root) / "runtime" / "admin_audit.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    event: dict[str, Any] = {
        "timestamp": utc_now_text(),
        "operation": operation,
        "account": account,
        "symbol": symbol,
        "canonical_symbol": canonical_symbol,
        "source_layer": source_layer,
        "target_layer": target_layer,
        "backup_path": backup_path,
        "validation_status": validation_status,
        "success": success,
        "warnings": warnings,
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    return log_path
