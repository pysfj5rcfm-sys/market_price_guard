from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .config_observability import PROJECT_ROOT, run_config_check


LAYER_ALIASES = {
    "operation": "operation",
    "core": "operation",
    "tech_core": "operation",
    "operation_candidate": "operation_candidate",
    "candidate": "operation_candidate",
    "operation_candidates": "operation_candidate",
    "tech_operation_candidates": "operation_candidate",
    "watchlist": "watchlist",
    "tech_watchlist": "watchlist",
    "scan": "scan",
    "tech_scan_ai": "scan",
}

LAYER_FILES = {
    "operation": "tech_core.yaml",
    "operation_candidate": "tech_operation_candidates.yaml",
    "watchlist": "tech_watchlist.yaml",
    "scan": "tech_scan_ai.yaml",
}

LAYER_ORDER = ["operation", "operation_candidate", "watchlist", "scan"]
SYMBOL_PATTERN = re.compile(r"^[A-Z0-9^][A-Z0-9.^=_-]*(\.(SH|SZ|HK))?$")

BACKUP_FILES = [
    "config/universes/tech_core.yaml",
    "config/universes/tech_operation_candidates.yaml",
    "config/universes/tech_watchlist.yaml",
    "config/universes/tech_scan_ai.yaml",
    "config/watchlist.yaml",
    "config/symbol_registry.yaml",
]

POLICY_MARKERS = {
    "failed_trial_observation",
    "failed_trial_observation_only",
    "no_add_no_t",
    "not_repair_candidate",
    "new_trade_requires_full_re_evaluation",
    "event_stock",
    "event_watch_only",
    "individual_stock",
    "manual_price_only",
    "defensive_asset",
    "broad_base_reference",
    "non_tech_asset",
    "qdii_premium_required",
    "premium_required",
    "non_default_candidate",
    "operation_validator",
    "reference_only",
}


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    manager = TechLayerManager(args.project_root)
    try:
        result = manager.run(args)
    except ManagerError as exc:
        result = manager.base_report(getattr(args, "command", "unknown"), dry_run=getattr(args, "dry_run", False))
        result["errors"].append(str(exc))
        manager.write_report(result)
        print(_format_console(result))
        return 1
    manager.write_report(result)
    print(_format_console(result))
    return 1 if result["errors"] else 0


class ManagerError(ValueError):
    pass


class TechLayerManager:
    def __init__(self, project_root: Path = PROJECT_ROOT) -> None:
        self.project_root = Path(project_root)
        self.config_dir = self.project_root / "config"
        self.universes_dir = self.config_dir / "universes"
        self.watchlist_path = self.config_dir / "watchlist.yaml"
        self.registry_path = self.config_dir / "symbol_registry.yaml"
        self.output_dir = self.project_root / "outputs_config_manager_latest"

    def run(self, args: argparse.Namespace) -> dict[str, Any]:
        command = args.command.replace("_", "-")
        if command == "show":
            return self.show()
        if command == "validate":
            return self.validate()
        if command == "export":
            return self.export()
        if command == "backup":
            return self.backup_command()
        if command == "sync-root":
            return self.sync_root(dry_run=args.dry_run, backup=args.backup)
        if command == "add":
            return self.add(
                args.symbol,
                args.layer,
                dry_run=args.dry_run,
                backup=args.backup,
                confirm_policy_override=args.confirm_policy_override,
                allow_operation_layer=args.allow_operation_layer,
            )
        if command == "remove":
            return self.remove(
                args.symbol,
                args.layer,
                dry_run=args.dry_run,
                backup=args.backup,
                allow_operation_layer=args.allow_operation_layer,
            )
        if command == "move":
            return self.move(
                args.symbol,
                args.from_layer,
                args.to_layer,
                dry_run=args.dry_run,
                backup=args.backup,
                confirm_policy_override=args.confirm_policy_override,
                allow_operation_layer=args.allow_operation_layer,
            )
        raise ManagerError(f"unsupported command: {command}")

    def base_report(self, command: str, *, dry_run: bool) -> dict[str, Any]:
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "command": command,
            "dry_run": dry_run,
            "changed_files": [],
            "before_counts": {},
            "after_counts": {},
            "added_symbols": [],
            "removed_symbols": [],
            "moved_symbols": [],
            "structural_warnings": [],
            "policy_warnings": [],
            "errors": [],
            "validation_status": "not_run",
            "policy_override_required": False,
            "policy_override_used": False,
            "override_scope": "",
            "override_reason": "",
            "root_mirror_mismatch": False,
            "root_mirror_synced": False,
            "backup_path": "",
            "symbols": {},
            "root_mirror": {},
        }

    def show(self) -> dict[str, Any]:
        state = self.load_state()
        report = self.base_report("show", dry_run=False)
        report.update(
            {
                "before_counts": _counts(state["layers"]),
                "after_counts": _counts(state["layers"]),
                "symbols": state["layers"],
                "root_mirror": state["root_layers"],
                "root_mirror_mismatch": bool(_mirror_diffs(state)),
                "validation_status": "not_run",
            }
        )
        return report

    def validate(self) -> dict[str, Any]:
        state = self.load_state()
        report = self.base_report("validate", dry_run=False)
        check = run_config_check(self.project_root / "outputs_config_check_latest", self.project_root)
        report.update(
            {
                "before_counts": _counts(state["layers"]),
                "after_counts": _counts(state["layers"]),
                "symbols": state["layers"],
                "root_mirror": state["root_layers"],
                "root_mirror_mismatch": bool(_mirror_diffs(state)),
                "validation_status": str(check.get("status", "unknown")),
                "policy_warnings": check.get("policy_warnings", []),
                "structural_warnings": check.get("warnings", []),
                "errors": check.get("errors", []),
            }
        )
        return report

    def add(
        self,
        symbol: str,
        layer_name: str,
        *,
        dry_run: bool,
        backup: bool,
        confirm_policy_override: bool,
        allow_operation_layer: bool,
    ) -> dict[str, Any]:
        layer = normalize_layer(layer_name)
        symbol = normalize_symbol(symbol)
        state = self.load_state()
        report = self.base_report("add", dry_run=dry_run)
        report["before_counts"] = _counts(state["layers"])
        self._check_symbol_inputs(report, symbol, layer, allow_operation_layer=allow_operation_layer)
        if symbol in state["layers"][layer]:
            report["structural_warnings"].append(f"no-op: {symbol} already in {layer}")
        else:
            state["layers"][layer].append(symbol)
            report["added_symbols"].append({"symbol": symbol, "layer": layer})
        self._finish_mutation(
            report,
            state,
            dry_run=dry_run,
            backup=backup,
            confirm_policy_override=confirm_policy_override,
            override_scope=f"{symbol}/{layer}",
        )
        return report

    def remove(
        self,
        symbol: str,
        layer_name: str,
        *,
        dry_run: bool,
        backup: bool,
        allow_operation_layer: bool,
    ) -> dict[str, Any]:
        layer = normalize_layer(layer_name)
        symbol = normalize_symbol(symbol)
        state = self.load_state()
        report = self.base_report("remove", dry_run=dry_run)
        report["before_counts"] = _counts(state["layers"])
        if layer == "operation" and not allow_operation_layer:
            report["errors"].append("operation layer modification requires -AllowOperationLayer")
        if symbol not in state["layers"][layer]:
            report["structural_warnings"].append(f"no-op: {symbol} not in {layer}")
        else:
            state["layers"][layer] = [item for item in state["layers"][layer] if item != symbol]
            report["removed_symbols"].append({"symbol": symbol, "layer": layer})
        self._finish_mutation(
            report,
            state,
            dry_run=dry_run,
            backup=backup,
            confirm_policy_override=True,
            require_policy_override=False,
            override_scope=f"{symbol}/{layer}",
        )
        return report

    def move(
        self,
        symbol: str,
        from_layer_name: str,
        to_layer_name: str,
        *,
        dry_run: bool,
        backup: bool,
        confirm_policy_override: bool,
        allow_operation_layer: bool,
    ) -> dict[str, Any]:
        from_layer = normalize_layer(from_layer_name)
        to_layer = normalize_layer(to_layer_name)
        symbol = normalize_symbol(symbol)
        state = self.load_state()
        report = self.base_report("move", dry_run=dry_run)
        report["before_counts"] = _counts(state["layers"])
        if "operation" in {from_layer, to_layer} and not allow_operation_layer:
            report["errors"].append("operation layer modification requires -AllowOperationLayer")
        if symbol not in state["layers"][from_layer]:
            report["structural_warnings"].append(f"no-op source: {symbol} not in {from_layer}")
        else:
            state["layers"][from_layer] = [item for item in state["layers"][from_layer] if item != symbol]
        if symbol in state["layers"][to_layer]:
            report["structural_warnings"].append(f"no-op target: {symbol} already in {to_layer}")
        else:
            state["layers"][to_layer].append(symbol)
        report["moved_symbols"].append({"symbol": symbol, "from": from_layer, "to": to_layer})
        self._check_symbol_inputs(report, symbol, to_layer, allow_operation_layer=True)
        self._finish_mutation(
            report,
            state,
            dry_run=dry_run,
            backup=backup,
            confirm_policy_override=confirm_policy_override,
            override_scope=f"{symbol}/{from_layer}->{to_layer}",
        )
        return report

    def sync_root(self, *, dry_run: bool, backup: bool) -> dict[str, Any]:
        state = self.load_state()
        report = self.base_report("sync-root", dry_run=dry_run)
        report["before_counts"] = _counts(state["root_layers"])
        report["after_counts"] = _counts(state["layers"])
        report["root_mirror_mismatch"] = bool(_mirror_diffs(state))
        report["root_mirror"] = state["root_layers"]
        self.sync_root_mirror(state)
        report["root_mirror_synced"] = True
        report["changed_files"] = [_display(self.watchlist_path, self.project_root)] if _mirror_diffs(state) or report["root_mirror_mismatch"] else []
        if not dry_run and report["changed_files"] and not report["errors"]:
            if backup:
                report["backup_path"] = str(self.create_backup())
            self.write_watchlist(state["watchlist_data"])
            report["validation_status"] = str(run_config_check(self.project_root / "outputs_config_check_latest", self.project_root).get("status", "unknown"))
        else:
            report["validation_status"] = "dry_run" if dry_run else "not_run"
        return report

    def export(self) -> dict[str, Any]:
        state = self.load_state()
        report = self.base_report("export", dry_run=False)
        report.update(
            {
                "before_counts": _counts(state["layers"]),
                "after_counts": _counts(state["layers"]),
                "symbols": state["layers"],
                "root_mirror": state["root_layers"],
                "root_mirror_mismatch": bool(_mirror_diffs(state)),
            }
        )
        report["policy_warnings"] = self.collect_policy_warnings(state)
        report["validation_status"] = str(run_config_check(self.project_root / "outputs_config_check_latest", self.project_root).get("status", "unknown"))
        self.write_export_files(report, state)
        return report

    def backup_command(self) -> dict[str, Any]:
        state = self.load_state()
        report = self.base_report("backup", dry_run=False)
        report["before_counts"] = _counts(state["layers"])
        report["after_counts"] = _counts(state["layers"])
        report["backup_path"] = str(self.create_backup())
        report["validation_status"] = "not_run"
        return report

    def load_state(self) -> dict[str, Any]:
        layers: dict[str, list[str]] = {}
        universe_data: dict[str, dict[str, Any]] = {}
        for layer in LAYER_ORDER:
            path = self.universes_dir / LAYER_FILES[layer]
            data = _read_yaml(path)
            if not isinstance(data, dict):
                raise ManagerError(f"invalid yaml object: {_display(path, self.project_root)}")
            universe_data[layer] = data
            layers[layer] = _symbols(data)
        watchlist_data = _read_yaml(self.watchlist_path)
        registry = _read_yaml(self.registry_path)
        if not isinstance(watchlist_data, dict):
            raise ManagerError("config/watchlist.yaml is not a mapping")
        if not isinstance(registry, dict):
            raise ManagerError("config/symbol_registry.yaml is not a mapping")
        layer_universes = watchlist_data.get("projects", {}).get("tech", {}).get("layer_universes", {})
        root_layers = {layer: [str(item) for item in layer_universes.get(layer, []) if str(item)] for layer in LAYER_ORDER}
        return {
            "layers": layers,
            "universe_data": universe_data,
            "watchlist_data": watchlist_data,
            "root_layers": root_layers,
            "registry": registry,
        }

    def _check_symbol_inputs(self, report: dict[str, Any], symbol: str, layer: str, *, allow_operation_layer: bool) -> None:
        if layer == "operation" and not allow_operation_layer:
            report["errors"].append("operation layer modification requires -AllowOperationLayer")
        if symbol not in self.load_state()["registry"]:
            report["errors"].append("symbol not found in config/symbol_registry.yaml")
        if not SYMBOL_PATTERN.match(symbol):
            report["errors"].append(f"invalid symbol format: {symbol}")

    def _finish_mutation(
        self,
        report: dict[str, Any],
        state: dict[str, Any],
        *,
        dry_run: bool,
        backup: bool,
        confirm_policy_override: bool,
        override_scope: str,
        require_policy_override: bool = True,
    ) -> None:
        self.sync_root_mirror(state)
        report["after_counts"] = _counts(state["layers"])
        report["root_mirror"] = {layer: list(state["layers"][layer]) for layer in LAYER_ORDER}
        report["root_mirror_synced"] = True
        report["root_mirror_mismatch"] = False
        report["changed_files"] = self.changed_files_for_report(report)
        all_policy_warnings = self.collect_policy_warnings(state)
        relevant = _relevant_policy_warnings(all_policy_warnings, override_scope)
        report["policy_warnings"] = relevant
        if require_policy_override and relevant and report["changed_files"]:
            report["policy_override_required"] = True
            if confirm_policy_override:
                report["policy_override_used"] = True
                report["override_scope"] = override_scope
                report["override_reason"] = "user_explicit_command"
            elif not dry_run:
                report["errors"].append("policy warning requires -ConfirmPolicyOverride")
        if dry_run:
            report["validation_status"] = "dry_run"
            return
        if report["errors"]:
            report["validation_status"] = "not_run"
            return
        if backup:
            report["backup_path"] = str(self.create_backup())
        self.write_layers(state["universe_data"], state["layers"])
        self.write_watchlist(state["watchlist_data"])
        check = run_config_check(self.project_root / "outputs_config_check_latest", self.project_root)
        report["validation_status"] = str(check.get("status", "unknown"))
        if check.get("status") == "failed":
            report["errors"].extend([str(item) for item in check.get("errors", [])])

    def collect_policy_warnings(self, state: dict[str, Any]) -> list[str]:
        warnings: list[str] = []
        registry = state["registry"]
        for layer, symbols in state["layers"].items():
            for symbol in symbols:
                warnings.extend(policy_warnings_for_symbol(symbol, layer, dict(registry.get(symbol, {}))))
        return list(dict.fromkeys(warnings))

    def changed_files_for_report(self, report: dict[str, Any]) -> list[str]:
        changed_layers = {item.get("layer") for item in report.get("added_symbols", []) + report.get("removed_symbols", [])}
        changed_layers.update(item.get("from") for item in report.get("moved_symbols", []))
        changed_layers.update(item.get("to") for item in report.get("moved_symbols", []))
        files = [
            _display(self.universes_dir / LAYER_FILES[layer], self.project_root)
            for layer in LAYER_ORDER
            if layer in changed_layers
        ]
        if files or report.get("command") == "sync-root":
            files.append(_display(self.watchlist_path, self.project_root))
        return list(dict.fromkeys(files))

    def sync_root_mirror(self, state: dict[str, Any]) -> None:
        projects = state["watchlist_data"].setdefault("projects", {})
        tech = projects.setdefault("tech", {})
        layer_universes = tech.setdefault("layer_universes", {})
        for layer in LAYER_ORDER:
            layer_universes[layer] = list(state["layers"][layer])
        layer_universes["counts"] = _counts(state["layers"])
        tech["layer_counts"] = {**_counts(state["layers"]), "all_layer_union": len(set().union(*(set(v) for v in state["layers"].values())))}

    def write_layers(self, universe_data: dict[str, dict[str, Any]], layers: dict[str, list[str]]) -> None:
        for layer in LAYER_ORDER:
            data = universe_data[layer]
            data["symbols"] = list(layers[layer])
            _write_yaml(self.universes_dir / LAYER_FILES[layer], data)

    def write_watchlist(self, data: dict[str, Any]) -> None:
        _write_yaml(self.watchlist_path, data)

    def create_backup(self) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.project_root / "backups" / f"config_layers_{timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=False)
        for relative in BACKUP_FILES:
            src = self.project_root / relative
            dst = backup_dir / relative
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        return backup_dir

    def write_report(self, report: dict[str, Any]) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "config_manager_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (self.output_dir / "config_manager_report.md").write_text(_format_markdown_report(report), encoding="utf-8")

    def write_export_files(self, report: dict[str, Any], state: dict[str, Any]) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        export = {
            "layers": state["layers"],
            "root_mirror": state["root_layers"],
            "per_symbol_membership": _per_symbol_membership(state["layers"], state["registry"]),
            "registry_status": {symbol: symbol in state["registry"] for symbol in _all_layer_symbols(state["layers"])},
            "policy_warnings": report["policy_warnings"],
            "structural_rule_status": report["validation_status"],
        }
        (self.output_dir / "tech_layer_config_export.json").write_text(
            json.dumps(export, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (self.output_dir / "tech_layer_config_export.md").write_text(_format_export_markdown(export), encoding="utf-8")
        with (self.output_dir / "tech_layer_config_export.csv").open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=["symbol", "registered", *LAYER_ORDER])
            writer.writeheader()
            for row in export["per_symbol_membership"]:
                writer.writerow(row)


def normalize_layer(value: str) -> str:
    key = str(value).strip().lower().replace("-", "_")
    if key not in LAYER_ALIASES:
        raise ManagerError(f"invalid layer: {value}")
    return LAYER_ALIASES[key]


def normalize_symbol(value: str) -> str:
    return str(value).strip().upper()


def policy_warnings_for_symbol(symbol: str, layer: str, entry: dict[str, Any]) -> list[str]:
    tags = {str(tag) for tag in entry.get("universe_tags", []) if str(tag)}
    role = str(entry.get("role", ""))
    notes = str(entry.get("notes", ""))
    restriction = str(entry.get("candidate_restriction", ""))
    haystack = " ".join([role, notes, restriction, " ".join(sorted(tags))]).lower().replace(" ", "_").replace("-", "_")
    warnings: list[str] = []
    for marker in sorted(POLICY_MARKERS):
        if marker in tags or marker in haystack or bool(entry.get(marker, False)):
            warnings.append(f"{symbol}:{layer}:{marker}")
    if bool(entry.get("qdii_premium_required", False)):
        warnings.append(f"{symbol}:{layer}:qdii_premium_required")
        warnings.append(f"{symbol}:{layer}:premium data required before operation decision")
    if layer == "operation_candidate":
        if "event" in role or "event_watch" in tags or "event" in haystack:
            warnings.extend(
                [
                    f"{symbol}:{layer}:event_stock_candidate_warning",
                    f"{symbol}:{layer}:requires_event_state_machine_review",
                    f"{symbol}:{layer}:requires_user_confirmation",
                ]
            )
        if "non_tech" in tags or "broad_base" in tags or "broad_base" in haystack:
            warnings.append(f"{symbol}:{layer}:non_tech_candidate_warning")
        if str(entry.get("market", "")) == "MANUAL" or str(entry.get("asset_type", "")) == "manual_price":
            warnings.append(f"{symbol}:{layer}:manual_price_only_candidate_warning")
        if symbol == "159516.SZ":
            warnings.extend(
                [
                    f"{symbol}:{layer}:failed_trial_observation_only",
                    f"{symbol}:{layer}:no_add_no_t",
                    f"{symbol}:{layer}:not_repair_candidate",
                    f"{symbol}:{layer}:new_trade_requires_full_re_evaluation",
                ]
            )
    return list(dict.fromkeys(warnings))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage tech layer config files.")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT, help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("show")
    sub.add_parser("validate")
    sub.add_parser("export")
    sub.add_parser("backup")
    sync = sub.add_parser("sync-root")
    _add_common(sync)
    add = sub.add_parser("add")
    add.add_argument("symbol")
    add.add_argument("-Layer", "--layer", required=True)
    _add_common(add)
    add.add_argument("-ConfirmPolicyOverride", "--confirm-policy-override", action="store_true")
    add.add_argument("-AllowOperationLayer", "--allow-operation-layer", action="store_true")
    remove = sub.add_parser("remove")
    remove.add_argument("symbol")
    remove.add_argument("-Layer", "--layer", required=True)
    _add_common(remove)
    remove.add_argument("-AllowOperationLayer", "--allow-operation-layer", action="store_true")
    move = sub.add_parser("move")
    move.add_argument("symbol")
    move.add_argument("-From", "--from-layer", required=True)
    move.add_argument("-To", "--to-layer", required=True)
    _add_common(move)
    move.add_argument("-ConfirmPolicyOverride", "--confirm-policy-override", action="store_true")
    move.add_argument("-AllowOperationLayer", "--allow-operation-layer", action="store_true")
    return parser


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-DryRun", "--dry-run", action="store_true")
    parser.add_argument("-Backup", "--backup", action="store_true")


def _read_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _write_yaml(path: Path, data: Any) -> None:
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _symbols(data: dict[str, Any]) -> list[str]:
    return [str(symbol).strip() for symbol in data.get("symbols", []) if str(symbol).strip()]


def _counts(layers: dict[str, list[str]]) -> dict[str, int]:
    return {layer: len(layers.get(layer, [])) for layer in LAYER_ORDER}


def _mirror_diffs(state: dict[str, Any]) -> dict[str, dict[str, list[str]]]:
    diffs: dict[str, dict[str, list[str]]] = {}
    for layer in LAYER_ORDER:
        if state["layers"].get(layer, []) != state["root_layers"].get(layer, []):
            diffs[layer] = {
                "universe": state["layers"].get(layer, []),
                "root": state["root_layers"].get(layer, []),
            }
    return diffs


def _display(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _all_layer_symbols(layers: dict[str, list[str]]) -> list[str]:
    symbols: list[str] = []
    for layer in LAYER_ORDER:
        symbols.extend(layers.get(layer, []))
    return list(dict.fromkeys(symbols))


def _per_symbol_membership(layers: dict[str, list[str]], registry: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for symbol in _all_layer_symbols(layers):
        row: dict[str, Any] = {"symbol": symbol, "registered": symbol in registry}
        for layer in LAYER_ORDER:
            row[layer] = symbol in layers[layer]
        rows.append(row)
    return rows


def _relevant_policy_warnings(policy_warnings: list[str], override_scope: str) -> list[str]:
    symbol = override_scope.split("/", 1)[0]
    layer = ""
    if "/" in override_scope:
        layer = override_scope.split("/", 1)[1]
        if "->" in layer:
            layer = layer.split("->", 1)[1]
    prefix = f"{symbol}:{layer}:" if layer else f"{symbol}:"
    return [warning for warning in policy_warnings if warning.startswith(prefix)]


def _format_console(report: dict[str, Any]) -> str:
    lines = [
        f"command: {report['command']}",
        f"dry_run: {str(report['dry_run']).lower()}",
        f"validation_status: {report['validation_status']}",
        f"changed_files: {', '.join(report['changed_files']) if report['changed_files'] else 'none'}",
        f"before_counts: {report['before_counts']}",
        f"after_counts: {report['after_counts']}",
        f"ROOT_MIRROR_MISMATCH: {str(report.get('root_mirror_mismatch', False)).lower()}",
        f"policy_override_required: {str(report['policy_override_required']).lower()}",
        f"policy_override_used: {str(report['policy_override_used']).lower()}",
    ]
    if report.get("backup_path"):
        lines.append(f"backup_path: {report['backup_path']}")
    if report["policy_warnings"]:
        lines.append("policy_warnings:")
        lines.extend(f"- {item}" for item in report["policy_warnings"])
    if report["structural_warnings"]:
        lines.append("structural_warnings:")
        lines.extend(f"- {item}" for item in report["structural_warnings"])
    if report["errors"]:
        lines.append("errors:")
        lines.extend(f"- {item}" for item in report["errors"])
    if report.get("symbols"):
        for layer in LAYER_ORDER:
            symbols = report["symbols"].get(layer, [])
            lines.append(f"{layer}: count={len(symbols)} symbols={', '.join(symbols) if symbols else 'none'}")
    return "\n".join(lines)


def _format_markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Tech Layer Config Manager Report",
        "",
        f"- command: {report['command']}",
        f"- dry_run: {str(report['dry_run']).lower()}",
        f"- validation_status: {report['validation_status']}",
        f"- changed_files: {', '.join(report['changed_files']) if report['changed_files'] else 'none'}",
        f"- before_counts: {report['before_counts']}",
        f"- after_counts: {report['after_counts']}",
        f"- ROOT_MIRROR_MISMATCH: {str(report.get('root_mirror_mismatch', False)).lower()}",
        f"- policy_override_required: {str(report['policy_override_required']).lower()}",
        f"- policy_override_used: {str(report['policy_override_used']).lower()}",
        f"- override_scope: {report.get('override_scope', '')}",
        f"- override_reason: {report.get('override_reason', '')}",
        f"- backup_path: {report.get('backup_path', '')}",
        "",
        "## Layer Counts",
        "",
        "| layer | before | after |",
        "|---|---:|---:|",
    ]
    for layer in LAYER_ORDER:
        lines.append(f"| {layer} | {report.get('before_counts', {}).get(layer, 0)} | {report.get('after_counts', {}).get(layer, 0)} |")
    lines.extend(["", "## Symbol Diffs"])
    lines.append(f"- symbols_in: {json.dumps(report.get('added_symbols', []), ensure_ascii=False)}")
    lines.append(f"- symbols_out: {json.dumps(report.get('removed_symbols', []), ensure_ascii=False)}")
    lines.append(f"- symbols_moved: {json.dumps(report.get('moved_symbols', []), ensure_ascii=False)}")
    lines.extend(["", "## Policy Warnings"])
    lines.extend([f"- {item}" for item in report.get("policy_warnings", [])] or ["- none"])
    lines.extend(["", "## Structural Warnings"])
    lines.extend([f"- {item}" for item in report.get("structural_warnings", [])] or ["- none"])
    lines.extend(["", "## Errors"])
    lines.extend([f"- {item}" for item in report.get("errors", [])] or ["- none"])
    return "\n".join(lines) + "\n"


def _format_export_markdown(export: dict[str, Any]) -> str:
    lines = ["# Tech Layer Config Export", "", "## Counts", ""]
    for layer in LAYER_ORDER:
        lines.append(f"- {layer}: {len(export['layers'].get(layer, []))}")
    lines.extend(["", "## Symbols"])
    for layer in LAYER_ORDER:
        lines.append(f"- {layer}: {', '.join(export['layers'].get(layer, []))}")
    lines.extend(["", "## Root Mirror"])
    for layer in LAYER_ORDER:
        lines.append(f"- {layer}: {', '.join(export['root_mirror'].get(layer, []))}")
    lines.extend(["", "## Policy Warnings"])
    lines.extend([f"- {item}" for item in export.get("policy_warnings", [])] or ["- none"])
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
