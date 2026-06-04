from __future__ import annotations

import hashlib
import json
import shutil
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .account_config import LAYER_ORDER, account_layer_paths, normalize_account, normalize_layer
from .admin_audit import utc_now_text, write_audit_event
from .admin_models import INCLUDE_ACTION, LayerActionPlan, LayerActionResult, SymbolAnalysis
from .admin_policy import collect_policy_messages, suggest_category
from .admin_symbol_infer import canonicalize_symbol
from .config_observability import PROJECT_ROOT, run_config_check
from .manage_account_layers import AccountLayerManager, normalize_symbol


class AdminLayerService:
    def __init__(self, project_root: Path = PROJECT_ROOT) -> None:
        self.project_root = Path(project_root)

    def account_snapshot(self, account: str) -> dict[str, Any]:
        account = normalize_account(account)
        manager = AccountLayerManager(account, self.project_root)
        state = manager.load_state()
        check = run_config_check(self.project_root / "outputs_config_check_latest", self.project_root, account=account)
        layers: list[dict[str, Any]] = []
        for layer in LAYER_ORDER:
            source_path = account_layer_paths(account).layer_files[layer]
            root_symbols = state["root_layers"].get(layer, [])
            layer_symbols = state["layers"].get(layer, [])
            layers.append(
                {
                    "name": layer,
                    "count": len(layer_symbols),
                    "source_file": source_path,
                    "root_mirror_count": len(root_symbols),
                    "mismatch_status": "mismatch" if layer_symbols != root_symbols else "match",
                    "symbols": [self._symbol_row(account, layer, item, state) for item in layer_symbols],
                }
            )
        return {
            "account": account,
            "counts": _counts(state["layers"]),
            "layers": layers,
            "root_mirror_match": all(item["mismatch_status"] == "match" for item in layers),
            "validation": check,
        }

    def home_summary(self) -> dict[str, Any]:
        tech = self.account_snapshot("tech")
        energy = self.account_snapshot("energy")
        return {
            "tech": tech,
            "energy": energy,
            "config_status": {
                "tech": tech["validation"].get("status", "unknown"),
                "energy": energy["validation"].get("status", "unknown"),
            },
        }

    def analyze_symbol(
        self,
        *,
        account: str,
        target_layer: str,
        raw_symbol: str,
        display_name: str = "",
        note: str = "",
        category: str = "",
        instrument_type: str = "",
    ) -> SymbolAnalysis:
        account = normalize_account(account)
        target_layer = normalize_layer(target_layer, account=account)
        manager = AccountLayerManager(account, self.project_root)
        state = manager.load_state()
        inference = canonicalize_symbol(raw_symbol, state["registry"])
        symbol = normalize_symbol(inference.canonical_symbol)
        entry = dict(state["registry"].get(symbol, {}))
        registry_status = "registered" if entry else "missing"
        market = str(entry.get("market") or inference.inferred_market or _market_from_instrument_type(instrument_type))
        asset_type = str(entry.get("asset_type") or inference.inferred_asset_type or _asset_from_instrument_type(instrument_type))
        existing_layers = [layer for layer in LAYER_ORDER if symbol in state["layers"].get(layer, [])]
        warnings = collect_policy_messages(
            account=account,
            target_layer=target_layer,
            symbol=symbol,
            layers=state["layers"],
            registry_entry=entry,
            registry_status=registry_status,
        )
        return SymbolAnalysis(
            account=account,
            target_layer=target_layer,
            raw_symbol=str(raw_symbol or "").strip(),
            canonical_symbol=symbol,
            inferred_market=market,
            inferred_asset_type=asset_type,
            registry_status=registry_status,
            registry_entry=entry,
            existing_layers=existing_layers,
            duplicate_status="in target layer" if symbol in state["layers"].get(target_layer, []) else "not in target layer",
            policy_warnings=warnings,
            suggested_category=category or suggest_category(account, symbol, entry),
            registry_stub_needed=registry_status != "registered",
            instrument_type=instrument_type,
            category=category,
            display_name=display_name,
            note=note,
        )

    def plan_symbol_insert(
        self,
        *,
        account: str,
        target_layer: str,
        raw_symbol: str,
        display_name: str = "",
        note: str = "",
        category: str = "",
        instrument_type: str = "",
        create_registry_stub: bool = False,
        confirm_apply: bool = False,
        confirm_operation_layer_change: bool = False,
        confirm_policy_override: bool = False,
    ) -> LayerActionPlan:
        analysis = self.analyze_symbol(
            account=account,
            target_layer=target_layer,
            raw_symbol=raw_symbol,
            display_name=display_name,
            note=note,
            category=category,
            instrument_type=instrument_type,
        )
        return self._plan(
            operation_type=INCLUDE_ACTION,
            account=analysis.account,
            symbol=analysis.canonical_symbol,
            source_layer="",
            target_layer=analysis.target_layer,
            create_registry_stub=create_registry_stub,
            display_name=analysis.display_name,
            note=analysis.note,
            category=analysis.category or analysis.suggested_category,
            instrument_type=analysis.instrument_type,
            confirm_apply=confirm_apply,
            confirm_operation_layer_change=confirm_operation_layer_change,
            confirm_policy_override=confirm_policy_override,
        )

    def plan_move(
        self,
        *,
        account: str,
        symbol: str,
        source_layer: str,
        target_layer: str,
        confirm_apply: bool = False,
        confirm_operation_layer_change: bool = False,
        confirm_policy_override: bool = False,
    ) -> LayerActionPlan:
        account = normalize_account(account)
        return self._plan(
            operation_type="move",
            account=account,
            symbol=normalize_symbol(canonicalize_symbol(symbol).canonical_symbol),
            source_layer=normalize_layer(source_layer, account=account),
            target_layer=normalize_layer(target_layer, account=account),
            create_registry_stub=False,
            display_name="",
            note="",
            category="",
            instrument_type="",
            confirm_apply=confirm_apply,
            confirm_operation_layer_change=confirm_operation_layer_change,
            confirm_policy_override=confirm_policy_override,
        )

    def plan_remove(
        self,
        *,
        account: str,
        symbol: str,
        source_layer: str,
        confirm_apply: bool = False,
        confirm_operation_layer_change: bool = False,
    ) -> LayerActionPlan:
        account = normalize_account(account)
        return self._plan(
            operation_type="remove",
            account=account,
            symbol=normalize_symbol(canonicalize_symbol(symbol).canonical_symbol),
            source_layer=normalize_layer(source_layer, account=account),
            target_layer="",
            create_registry_stub=False,
            display_name="",
            note="",
            category="",
            instrument_type="",
            confirm_apply=confirm_apply,
            confirm_operation_layer_change=confirm_operation_layer_change,
            confirm_policy_override=True,
        )

    def perform(self, plan: LayerActionPlan) -> LayerActionResult:
        if not plan.apply_allowed:
            return LayerActionResult(
                plan=plan,
                success=False,
                validation_status="not_run",
                backup_path="",
                audit_path="",
                partial_changes=[],
                errors=list(plan.blocking_reasons),
            )
        backup_path = ""
        audit_path = ""
        partial_changes: list[str] = []
        errors: list[str] = []
        validation_status = "not_run"
        try:
            backup_path = str(create_admin_backup(self.project_root, plan))
            state = AccountLayerManager(plan.account, self.project_root).load_state()
            self._mutate_state(state, plan)
            manager = AccountLayerManager(plan.account, self.project_root)
            manager.sync_root_mirror(state)
            manager.write_layers(state["universe_data"], state["layers"])
            if plan.registry_stub_plan.get("will_create"):
                state["registry"][plan.canonical_symbol] = dict(plan.registry_stub_plan.get("entry", {}))
                _write_yaml(self.project_root / "config/symbol_registry.yaml", state["registry"])
            manager.write_watchlist(state["watchlist_data"])
            partial_changes = list(plan.files_to_modify)
            check = run_config_check(self.project_root / "outputs_config_check_latest", self.project_root, account=plan.account)
            validation_status = str(check.get("status", "unknown"))
            if validation_status == "failed":
                errors.extend(str(item) for item in check.get("errors", []))
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
        success = not errors and validation_status in {"ok", "warning"}
        audit_path = str(
            write_audit_event(
                self.project_root,
                operation=plan.operation_type,
                account=plan.account,
                symbol=plan.symbol,
                canonical_symbol=plan.canonical_symbol,
                source_layer=plan.source_layer,
                target_layer=plan.target_layer,
                backup_path=backup_path,
                validation_status=validation_status,
                success=success,
                warnings=plan.policy_warnings,
            )
        )
        return LayerActionResult(
            plan=plan,
            success=success,
            validation_status=validation_status,
            backup_path=backup_path,
            audit_path=audit_path,
            partial_changes=partial_changes,
            errors=errors,
        )

    def validate(self, account: str) -> dict[str, Any]:
        account = normalize_account(account)
        return run_config_check(self.project_root / "outputs_config_check_latest", self.project_root, account=account)

    def registry_entry(self, symbol: str) -> dict[str, Any]:
        registry = _read_yaml(self.project_root / "config/symbol_registry.yaml")
        symbol = normalize_symbol(canonicalize_symbol(symbol, registry if isinstance(registry, dict) else {}).canonical_symbol)
        entry = dict((registry or {}).get(symbol, {})) if isinstance(registry, dict) else {}
        return {"symbol": symbol, "registry_status": "registered" if entry else "missing", "entry": entry}

    def _plan(
        self,
        *,
        operation_type: str,
        account: str,
        symbol: str,
        source_layer: str,
        target_layer: str,
        create_registry_stub: bool,
        display_name: str,
        note: str,
        category: str,
        instrument_type: str,
        confirm_apply: bool,
        confirm_operation_layer_change: bool,
        confirm_policy_override: bool,
    ) -> LayerActionPlan:
        manager = AccountLayerManager(account, self.project_root)
        state = manager.load_state()
        before_layers = deepcopy(state["layers"])
        registry_entry = dict(state["registry"].get(symbol, {}))
        registry_status = "registered" if registry_entry else "missing"
        structural_warnings: list[str] = []
        after_layers = deepcopy(before_layers)
        if operation_type == INCLUDE_ACTION:
            if symbol in after_layers.get(target_layer, []):
                structural_warnings.append(f"{symbol}:{target_layer}:symbol already exists in target layer")
            else:
                after_layers[target_layer].append(symbol)
        elif operation_type == "move":
            if symbol not in after_layers.get(source_layer, []):
                structural_warnings.append(f"{symbol}:{source_layer}:symbol not present in source layer")
            else:
                after_layers[source_layer] = [item for item in after_layers[source_layer] if item != symbol]
            if symbol in after_layers.get(target_layer, []):
                structural_warnings.append(f"{symbol}:{target_layer}:symbol already exists in target layer")
            else:
                after_layers[target_layer].append(symbol)
        elif operation_type == "remove":
            if symbol not in after_layers.get(source_layer, []):
                structural_warnings.append(f"{symbol}:{source_layer}:symbol not present in source layer")
            else:
                after_layers[source_layer] = [item for item in after_layers[source_layer] if item != symbol]
        else:
            structural_warnings.append(f"unsupported operation: {operation_type}")
        changed_layers = _changed_layers(before_layers, after_layers)
        files_to_modify = _files_for_change(account, changed_layers, self.project_root)
        inference = canonicalize_symbol(symbol, state["registry"])
        stub_entry = _registry_stub(
            account=account,
            symbol=symbol,
            inference_market=inference.inferred_market,
            inference_asset=inference.inferred_asset_type,
            display_name=display_name,
            note=note,
            category=category,
            instrument_type=instrument_type,
            target_layer=target_layer or source_layer,
        )
        registry_stub_plan = {
            "needed": registry_status != "registered",
            "will_create": bool(create_registry_stub and registry_status != "registered"),
            "entry": stub_entry if create_registry_stub and registry_status != "registered" else {},
        }
        if registry_stub_plan["will_create"]:
            files_to_modify.append("config/symbol_registry.yaml")
        policy_warnings = collect_policy_messages(
            account=account,
            target_layer=target_layer or source_layer,
            symbol=symbol,
            layers=before_layers,
            registry_entry=registry_entry,
            registry_status=registry_status,
        )
        blocking_reasons = _blocking_reasons(
            plan_layer=target_layer or source_layer,
            source_layer=source_layer,
            target_layer=target_layer,
            confirm_apply=confirm_apply,
            confirm_operation_layer_change=confirm_operation_layer_change,
            confirm_policy_override=confirm_policy_override,
            policy_warnings=policy_warnings,
            structural_warnings=structural_warnings,
        )
        return LayerActionPlan(
            operation_type=operation_type,
            account=account,
            symbol=symbol,
            canonical_symbol=symbol,
            source_layer=source_layer,
            target_layer=target_layer,
            files_to_modify=list(dict.fromkeys(files_to_modify)),
            root_mirror_sync_plan=_root_plan(changed_layers),
            registry_stub_plan=registry_stub_plan,
            policy_warnings=policy_warnings,
            before_counts=_counts(before_layers),
            after_counts=_counts(after_layers),
            validation_plan=[f"run account config validation for {account}", "check root mirror match", "check registry coverage"],
            diff_preview=_diff_preview(before_layers, after_layers),
            apply_allowed=not blocking_reasons,
            blocking_reasons=blocking_reasons,
            structural_warnings=structural_warnings,
        )

    def _mutate_state(self, state: dict[str, Any], plan: LayerActionPlan) -> None:
        layers = state["layers"]
        if plan.operation_type == INCLUDE_ACTION:
            if plan.canonical_symbol not in layers[plan.target_layer]:
                layers[plan.target_layer].append(plan.canonical_symbol)
        elif plan.operation_type == "move":
            if plan.canonical_symbol in layers[plan.source_layer]:
                layers[plan.source_layer] = [item for item in layers[plan.source_layer] if item != plan.canonical_symbol]
            if plan.canonical_symbol not in layers[plan.target_layer]:
                layers[plan.target_layer].append(plan.canonical_symbol)
        elif plan.operation_type == "remove":
            if plan.canonical_symbol in layers[plan.source_layer]:
                layers[plan.source_layer] = [item for item in layers[plan.source_layer] if item != plan.canonical_symbol]

    def _symbol_row(self, account: str, layer: str, symbol: str, state: dict[str, Any]) -> dict[str, Any]:
        entry = dict(state["registry"].get(symbol, {}))
        registry_status = "registered" if entry else "missing"
        current_layers = [name for name in LAYER_ORDER if symbol in state["layers"].get(name, [])]
        warnings = collect_policy_messages(
            account=account,
            target_layer=layer,
            symbol=symbol,
            layers=state["layers"],
            registry_entry=entry,
            registry_status=registry_status,
        )
        return {
            "symbol": symbol,
            "display_name": str(entry.get("display_name") or entry.get("name") or symbol),
            "market": str(entry.get("market") or ""),
            "asset_type": str(entry.get("asset_type") or ""),
            "registry_status": registry_status,
            "current_layers": current_layers,
            "policy_tags": _policy_tags(entry),
            "warnings": warnings,
        }


def create_admin_backup(project_root: Path, plan: LayerActionPlan) -> Path:
    project_root = Path(project_root)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = project_root / "backups" / f"admin_config_{timestamp}"
    suffix = 1
    while backup_dir.exists():
        backup_dir = project_root / "backups" / f"admin_config_{timestamp}_{suffix:02d}"
        suffix += 1
    backup_dir.mkdir(parents=True, exist_ok=False)
    files = _backup_files(plan.account, plan.files_to_modify)
    manifest_files: list[dict[str, str]] = []
    for relative in files:
        src = project_root / relative
        if not src.exists():
            continue
        dst = backup_dir / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        manifest_files.append({"path": relative, "sha256_before": _sha256(src)})
    manifest = {
        "generated_at": utc_now_text(),
        "operation": plan.operation_type,
        "account": plan.account,
        "symbol": plan.canonical_symbol,
        "files": manifest_files,
        "user_action_source": "admin_ui",
    }
    (backup_dir / "backup_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return backup_dir


def _backup_files(account: str, files_to_modify: list[str]) -> list[str]:
    paths = account_layer_paths(account)
    files = ["config/watchlist.yaml", *paths.layer_files.values()]
    if "config/symbol_registry.yaml" in files_to_modify:
        files.append("config/symbol_registry.yaml")
    return list(dict.fromkeys(files))


def _read_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _write_yaml(path: Path, data: Any) -> None:
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _counts(layers: dict[str, list[str]]) -> dict[str, int]:
    return {layer: len(layers.get(layer, [])) for layer in LAYER_ORDER}


def _changed_layers(before_layers: dict[str, list[str]], after_layers: dict[str, list[str]]) -> list[str]:
    return [layer for layer in LAYER_ORDER if before_layers.get(layer, []) != after_layers.get(layer, [])]


def _files_for_change(account: str, changed_layers: list[str], project_root: Path) -> list[str]:
    paths = account_layer_paths(account)
    files = [paths.layer_files[layer] for layer in changed_layers]
    if changed_layers:
        files.append("config/watchlist.yaml")
    return [_display(project_root / item, project_root) for item in files]


def _root_plan(changed_layers: list[str]) -> list[str]:
    if not changed_layers:
        return ["root mirror unchanged"]
    return [f"sync root mirror for {layer}" for layer in changed_layers]


def _diff_preview(before_layers: dict[str, list[str]], after_layers: dict[str, list[str]]) -> list[str]:
    lines: list[str] = []
    for layer in LAYER_ORDER:
        before = before_layers.get(layer, [])
        after = after_layers.get(layer, [])
        outgoing = [symbol for symbol in before if symbol not in after]
        incoming = [symbol for symbol in after if symbol not in before]
        for symbol in outgoing:
            lines.append(f"{layer}: - {symbol}")
        for symbol in incoming:
            lines.append(f"{layer}: + {symbol}")
    return lines or ["no file content change"]


def _blocking_reasons(
    *,
    plan_layer: str,
    source_layer: str,
    target_layer: str,
    confirm_apply: bool,
    confirm_operation_layer_change: bool,
    confirm_policy_override: bool,
    policy_warnings: list[str],
    structural_warnings: list[str],
) -> list[str]:
    reasons: list[str] = []
    if structural_warnings and all("already exists" in item or "not present" in item for item in structural_warnings):
        pass
    if not confirm_apply:
        reasons.append("apply confirmation required")
    if "operation" in {plan_layer, source_layer, target_layer} and not confirm_operation_layer_change:
        reasons.append("operation layer confirmation required")
    if _needs_policy_confirmation(policy_warnings) and not confirm_policy_override:
        reasons.append("policy warning confirmation required")
    return reasons


def _needs_policy_confirmation(policy_warnings: list[str]) -> bool:
    soft = ("registry_missing", "root mirror will be synced", "already exists", "exists in other layers", "operation layer requires")
    return any(not any(marker in warning for marker in soft) for warning in policy_warnings)


def _registry_stub(
    *,
    account: str,
    symbol: str,
    inference_market: str,
    inference_asset: str,
    display_name: str,
    note: str,
    category: str,
    instrument_type: str,
    target_layer: str,
) -> dict[str, Any]:
    market = inference_market or _market_from_instrument_type(instrument_type) or "UNKNOWN"
    asset_type = inference_asset or _asset_from_instrument_type(instrument_type) or "unknown"
    return {
        "symbol": symbol,
        "name": display_name or symbol,
        "display_name": display_name or symbol,
        "market": market,
        "asset_type": asset_type,
        "project_scope": account,
        "account_tags": [account],
        "universe_tags": [account, "admin_ui_stub"],
        "category": category or "Other",
        "source": "admin_ui_stub",
        "created_at": utc_now_text(),
        "enabled": True,
        "required_for_operation": target_layer == "operation",
        "default_quote_purpose": "operation" if target_layer == "operation" else "reference",
        "notes": note or "Local admin dashboard minimal registry stub for configuration management only.",
    }


def _market_from_instrument_type(instrument_type: str) -> str:
    if instrument_type.startswith("A-share"):
        return "CN"
    if instrument_type.startswith("HK"):
        return "HK"
    if instrument_type.startswith("US"):
        return "US"
    if instrument_type.startswith("manual"):
        return "MANUAL"
    return ""


def _asset_from_instrument_type(instrument_type: str) -> str:
    value = instrument_type.lower()
    if "etf" in value:
        return "ETF"
    if "stock" in value:
        return "stock"
    if "index" in value:
        return "index"
    if "manual" in value:
        return "manual_price"
    return ""


def _policy_tags(entry: dict[str, Any]) -> list[str]:
    tags = [str(tag) for tag in entry.get("universe_tags", []) if str(tag)]
    role = str(entry.get("role") or "")
    if role:
        tags.append(role)
    return list(dict.fromkeys(tags))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _display(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)
