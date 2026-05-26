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

from .account_config import LAYER_ORDER, account_layer_paths, normalize_account, normalize_layer as normalize_account_layer
from .config_observability import ENERGY_SCOPE_CLASSIFICATION, PROJECT_ROOT, run_config_check
from .manage_tech_layers import TechLayerManager, policy_warnings_for_symbol


SYMBOL_PATTERN = re.compile(r"^[A-Z0-9^][A-Z0-9.^=_-]*(\.(SH|SZ|HK))?$")


class AccountLayerManager:
    def __init__(self, account: str, project_root: Path = PROJECT_ROOT) -> None:
        self.account = normalize_account(account)
        self.project_root = Path(project_root)
        self.paths = account_layer_paths(self.account)
        self.output_dir = self.project_root / "outputs_config_manager_latest"

    def run(self, args: argparse.Namespace) -> dict[str, Any]:
        command = args.command.replace("_", "-")
        if self.account == "tech":
            tech_args = argparse.Namespace(**{k: v for k, v in vars(args).items() if k not in {"account"}})
            report = TechLayerManager(self.project_root).run(tech_args)
            return self._add_account_fields(report)
        if not self.paths.account_bootstrapped(self.project_root):
            report = self._not_bootstrapped_report(command)
            if command in {"validate", "export"}:
                check = run_config_check(self.project_root / "outputs_config_check_latest", self.project_root, account=self.account)
                report["validation_status"] = str(check.get("status", "unknown"))
                report["warnings"] = check.get("warnings", [])
                report["errors"] = check.get("errors", [])
                if not report["errors"]:
                    report["errors"] = [f"{self.account}_account_not_bootstrapped"]
            return report
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
        report = self.base_report(command, dry_run=False)
        report["errors"] = [f"unsupported command for {self.account}: {command}"]
        return report

    def _add_account_fields(self, report: dict[str, Any]) -> dict[str, Any]:
        report = dict(report)
        _normalize_root_mirror_fields(report)
        report.update(
            {
                "account": self.account,
                "scope_classification": _scope_classification_for_account(self.account),
                "account_project_path": self.paths.project_path,
                "root_mirror_path": self.paths.root_mirror_path,
                "account_bootstrapped": True,
                "missing_account_config_files": [],
            }
        )
        return report

    def base_report(self, command: str, *, dry_run: bool) -> dict[str, Any]:
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "command": command,
            "dry_run": dry_run,
            "account": self.account,
            "scope_classification": _scope_classification_for_account(self.account),
            "account_project_path": self.paths.project_path,
            "root_mirror_path": self.paths.root_mirror_path,
            "account_bootstrapped": True,
            "missing_account_config_files": [],
            "changed_files": [],
            "before_counts": {},
            "after_counts": {},
            "added_symbols": [],
            "removed_symbols": [],
            "moved_symbols": [],
            "symbols": {},
            "root_mirror": {},
            "warnings": [],
            "errors": [],
            "validation_status": "not_run",
            "policy_warnings": [],
            "structural_warnings": [],
            "policy_override_required": False,
            "policy_override_used": False,
            "override_scope": "",
            "override_reason": "",
            "root_mirror_mismatch": False,
            "root_mirror_match": True,
            "root_mirror_synced": False,
            "backup_path": "",
        }

    def show(self) -> dict[str, Any]:
        state = self.load_state()
        report = self.base_report("show", dry_run=False)
        mismatch = bool(_mirror_diffs(state))
        report.update(
            {
                "before_counts": _counts(state["layers"]),
                "after_counts": _counts(state["layers"]),
                "symbols": state["layers"],
                "root_mirror": state["root_layers"],
                "root_mirror_mismatch": mismatch,
                "root_mirror_match": not mismatch,
            }
        )
        return report

    def validate(self) -> dict[str, Any]:
        state = self.load_state()
        report = self.base_report("validate", dry_run=False)
        check = run_config_check(self.project_root / "outputs_config_check_latest", self.project_root, account=self.account)
        mismatch = bool(_mirror_diffs(state))
        report.update(
            {
                "before_counts": _counts(state["layers"]),
                "after_counts": _counts(state["layers"]),
                "symbols": state["layers"],
                "root_mirror": state["root_layers"],
                "root_mirror_mismatch": mismatch,
                "root_mirror_match": not mismatch,
                "validation_status": str(check.get("status", "unknown")),
                "policy_warnings": check.get("policy_warnings", []),
                "structural_warnings": check.get("warnings", []),
                "errors": check.get("errors", []),
            }
        )
        return report

    def export(self) -> dict[str, Any]:
        state = self.load_state()
        report = self.base_report("export", dry_run=False)
        mismatch = bool(_mirror_diffs(state))
        report.update(
            {
                "before_counts": _counts(state["layers"]),
                "after_counts": _counts(state["layers"]),
                "symbols": state["layers"],
                "root_mirror": state["root_layers"],
                "root_mirror_mismatch": mismatch,
                "root_mirror_match": not mismatch,
            }
        )
        report["policy_warnings"] = self.collect_policy_warnings(state)
        report["validation_status"] = str(
            run_config_check(self.project_root / "outputs_config_check_latest", self.project_root, account=self.account).get("status", "unknown")
        )
        self.write_export_files(report, state)
        return report

    def sync_root(self, *, dry_run: bool, backup: bool) -> dict[str, Any]:
        state = self.load_state()
        before_mismatch = bool(_mirror_diffs(state))
        report = self.base_report("sync-root", dry_run=dry_run)
        report["before_counts"] = _counts(state["root_layers"])
        report["after_counts"] = _counts(state["layers"])
        report["root_mirror"] = state["root_layers"]
        _set_root_mirror_fields(report, before_mismatch)
        self.sync_root_mirror(state)
        report["root_mirror_synced"] = True
        report["changed_files"] = [_display(self.project_root / "config/watchlist.yaml", self.project_root)] if before_mismatch else []
        if not dry_run and report["changed_files"] and not report["errors"]:
            if backup:
                report["backup_path"] = str(self.create_backup())
            self.write_watchlist(state["watchlist_data"])
            report["validation_status"] = str(
                run_config_check(self.project_root / "outputs_config_check_latest", self.project_root, account=self.account).get("status", "unknown")
            )
        else:
            report["validation_status"] = "dry_run" if dry_run else "not_run"
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
        layer = normalize_layer(layer_name, account=self.account)
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

    def remove(self, symbol: str, layer_name: str, *, dry_run: bool, backup: bool, allow_operation_layer: bool) -> dict[str, Any]:
        layer = normalize_layer(layer_name, account=self.account)
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
        from_layer = normalize_layer(from_layer_name, account=self.account)
        to_layer = normalize_layer(to_layer_name, account=self.account)
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

    def backup_command(self) -> dict[str, Any]:
        state = self.load_state()
        report = self.base_report("backup", dry_run=False)
        report["before_counts"] = _counts(state["layers"])
        report["after_counts"] = _counts(state["layers"])
        report["backup_path"] = str(self.create_backup())
        return report

    def load_state(self) -> dict[str, Any]:
        layers: dict[str, list[str]] = {}
        universe_data: dict[str, dict[str, Any]] = {}
        for layer in LAYER_ORDER:
            path = self.project_root / self.paths.layer_files[layer]
            data = _read_yaml(path)
            if not isinstance(data, dict):
                raise ValueError(f"invalid yaml object: {_display(path, self.project_root)}")
            universe_data[layer] = data
            layers[layer] = _symbols(data)
        watchlist_path = self.project_root / "config/watchlist.yaml"
        registry_path = self.project_root / "config/symbol_registry.yaml"
        watchlist_data = _read_yaml(watchlist_path)
        registry = _read_yaml(registry_path)
        if not isinstance(watchlist_data, dict):
            raise ValueError("config/watchlist.yaml is not a mapping")
        if not isinstance(registry, dict):
            raise ValueError("config/symbol_registry.yaml is not a mapping")
        layer_universes = watchlist_data.get("projects", {}).get(self.account, {}).get("layer_universes", {})
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
        report["root_mirror_match"] = True
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
        check = run_config_check(self.project_root / "outputs_config_check_latest", self.project_root, account=self.account)
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
            _display(self.project_root / self.paths.layer_files[layer], self.project_root)
            for layer in LAYER_ORDER
            if layer in changed_layers
        ]
        if files or report.get("command") == "sync-root":
            files.append(_display(self.project_root / "config/watchlist.yaml", self.project_root))
        return list(dict.fromkeys(files))

    def sync_root_mirror(self, state: dict[str, Any]) -> None:
        projects = state["watchlist_data"].setdefault("projects", {})
        project = projects.setdefault(self.account, {})
        layer_universes = project.setdefault("layer_universes", {})
        layer_universes["note"] = (
            f"Legacy-compatible mirror of config/universes/{self.account}_*.yaml. "
            "Scripts should prefer account universe files when available."
        )
        for layer in LAYER_ORDER:
            layer_universes[layer] = list(state["layers"][layer])
        layer_universes["counts"] = _counts(state["layers"])
        project["layer_counts"] = {
            **_counts(state["layers"]),
            "all_layer_union": len(set().union(*(set(values) for values in state["layers"].values()))),
        }

    def write_layers(self, universe_data: dict[str, dict[str, Any]], layers: dict[str, list[str]]) -> None:
        for layer in LAYER_ORDER:
            data = universe_data[layer]
            data["symbols"] = list(layers[layer])
            _write_yaml(self.project_root / self.paths.layer_files[layer], data)

    def write_watchlist(self, data: dict[str, Any]) -> None:
        _write_yaml(self.project_root / "config/watchlist.yaml", data)

    def create_backup(self) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.project_root / "backups" / f"config_layers_{self.account}_{timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=False)
        for relative in [*self.paths.layer_files.values(), "config/watchlist.yaml", "config/symbol_registry.yaml"]:
            src = self.project_root / relative
            dst = backup_dir / relative
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        return backup_dir

    def write_export_files(self, report: dict[str, Any], state: dict[str, Any]) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        export = {
            "account": self.account,
            "scope_classification": report.get("scope_classification", ""),
            "layers": state["layers"],
            "root_mirror": state["root_layers"],
            "root_mirror_match": not bool(_mirror_diffs(state)),
            "per_symbol_membership": _per_symbol_membership(state["layers"], state["registry"]),
            "registry_status": {symbol: symbol in state["registry"] for symbol in _all_layer_symbols(state["layers"])},
            "policy_warnings": report["policy_warnings"],
            "structural_rule_status": report["validation_status"],
        }
        prefix = f"{self.account}_layer_config_export"
        (self.output_dir / f"{prefix}.json").write_text(
            json.dumps(export, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (self.output_dir / f"{prefix}.md").write_text(_format_export_markdown(export), encoding="utf-8")
        with (self.output_dir / f"{prefix}.csv").open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=["symbol", "registered", *LAYER_ORDER])
            writer.writeheader()
            for row in export["per_symbol_membership"]:
                writer.writerow(row)

    def _not_bootstrapped_report(self, command: str) -> dict[str, Any]:
        missing = self.paths.missing_config_files(self.project_root)
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "command": command,
            "dry_run": False,
            "account": self.account,
            "scope_classification": _scope_classification_for_account(self.account),
            "account_project_path": self.paths.project_path,
            "root_mirror_path": self.paths.root_mirror_path,
            "account_bootstrapped": False,
            "missing_account_config_files": missing,
            "changed_files": [],
            "before_counts": {},
            "after_counts": {},
            "symbols": {},
            "root_mirror": {},
            "warnings": [f"{self.account}_account_not_bootstrapped", *[f"missing {path}" for path in missing]],
            "errors": [],
            "validation_status": "account_not_bootstrapped",
            "policy_warnings": [],
            "structural_warnings": [],
            "policy_override_required": False,
            "policy_override_used": False,
            "override_scope": "",
            "override_reason": "",
            "root_mirror_mismatch": False,
            "root_mirror_match": True,
            "root_mirror_synced": False,
            "backup_path": "",
        }

    def write_report(self, report: dict[str, Any]) -> None:
        _normalize_root_mirror_fields(report)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "config_manager_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (self.output_dir / "config_manager_report.md").write_text(_format_markdown_report(report), encoding="utf-8")


def normalize_layer(value: str, account: str = "tech") -> str:
    return normalize_account_layer(value, account=account)


def _scope_classification_for_account(account: str) -> str:
    return ENERGY_SCOPE_CLASSIFICATION if account == "energy" else "account-generic foundation"


def _set_root_mirror_fields(report: dict[str, Any], mismatch: bool) -> None:
    report["root_mirror_mismatch"] = bool(mismatch)
    report["root_mirror_match"] = not bool(mismatch)


def _normalize_root_mirror_fields(report: dict[str, Any]) -> None:
    mismatch = bool(report.get("root_mirror_mismatch", False))
    _set_root_mirror_fields(report, mismatch)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    manager = AccountLayerManager(args.account, args.project_root)
    try:
        report = manager.run(args)
    except Exception as exc:
        report = manager._not_bootstrapped_report(getattr(args, "command", "unknown"))
        report["errors"].append(str(exc))
    manager.write_report(report)
    print(_format_console(report))
    return 1 if report.get("errors") or report.get("account_bootstrapped") is False else 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage account layer config files.")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT, help=argparse.SUPPRESS)
    parser.add_argument("-Account", "--account", required=True, choices=["tech", "energy"])
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


def _format_console(report: dict[str, Any]) -> str:
    _normalize_root_mirror_fields(report)
    lines = [
        f"account: {report.get('account', '')}",
        f"command: {report.get('command', '')}",
        f"account_bootstrapped: {str(report.get('account_bootstrapped', False)).lower()}",
        f"validation_status: {report.get('validation_status', '')}",
        f"before_counts: {report.get('before_counts', {})}",
        f"after_counts: {report.get('after_counts', {})}",
        f"ROOT_MIRROR_MISMATCH: {str(report.get('root_mirror_mismatch', False)).lower()}",
    ]
    if not report.get("account_bootstrapped", False):
        lines.append(f"{report.get('account', '')}_account_not_bootstrapped")
        lines.append("missing_account_config_files:")
        lines.extend(f"- {path}" for path in report.get("missing_account_config_files", []))
    if report.get("symbols"):
        for layer in LAYER_ORDER:
            symbols = report["symbols"].get(layer, [])
            lines.append(f"{layer}: count={len(symbols)} symbols={', '.join(symbols) if symbols else 'none'}")
    if report.get("policy_warnings"):
        lines.append("policy_warnings:")
        lines.extend(f"- {item}" for item in report["policy_warnings"])
    if report.get("structural_warnings"):
        lines.append("structural_warnings:")
        lines.extend(f"- {item}" for item in report["structural_warnings"])
    if report.get("warnings"):
        lines.append("warnings:")
        lines.extend(f"- {item}" for item in report["warnings"])
    if report.get("errors"):
        lines.append("errors:")
        lines.extend(f"- {item}" for item in report["errors"])
    return "\n".join(lines)


def _format_markdown_report(report: dict[str, Any]) -> str:
    _normalize_root_mirror_fields(report)
    lines = [
        "# Account Layer Config Manager Report",
        "",
        f"- generated_at: {report.get('generated_at', '')}",
        f"- account: {report.get('account', '')}",
        f"- scope_classification: {report.get('scope_classification', '')}",
        f"- command: {_safe_command_name(report.get('command', ''))}",
        f"- account_project_path: {report.get('account_project_path', '')}",
        f"- root_mirror_path: {report.get('root_mirror_path', '')}",
        f"- account_bootstrapped: {str(report.get('account_bootstrapped', False)).lower()}",
        f"- missing_account_config_files: {', '.join(report.get('missing_account_config_files', [])) if report.get('missing_account_config_files') else 'none'}",
        f"- validation_status: {report.get('validation_status', '')}",
        f"- changed_files: {', '.join(report.get('changed_files', [])) if report.get('changed_files') else 'none'}",
        f"- before_counts: {report.get('before_counts', {})}",
        f"- after_counts: {report.get('after_counts', {})}",
        f"- ROOT_MIRROR_MISMATCH: {str(report.get('root_mirror_mismatch', False)).lower()}",
        f"- root_mirror_match: {str(report.get('root_mirror_match', False)).lower()}",
        "",
        "## Layer Counts",
        "",
        "| layer | before | after |",
        "|---|---:|---:|",
    ]
    for layer in LAYER_ORDER:
        lines.append(f"| {layer} | {report.get('before_counts', {}).get(layer, 0)} | {report.get('after_counts', {}).get(layer, 0)} |")
    lines.extend(["", "## Warnings"])
    lines.extend([f"- {_safe_report_text(item)}" for item in report.get("warnings", [])] or ["- none"])
    lines.extend(["", "## Policy Warnings"])
    lines.extend([f"- {_safe_report_text(item)}" for item in report.get("policy_warnings", [])] or ["- none"])
    lines.extend(["", "## Errors"])
    lines.extend([f"- {_safe_report_text(item)}" for item in report.get("errors", [])] or ["- none"])
    return "\n".join(lines) + "\n"


def _safe_report_text(value: Any) -> str:
    return str(value).replace("no_add_no_t", "no_increase_no_intraday")


def _safe_command_name(value: Any) -> str:
    command = str(value)
    return {"add": "insert"}.get(command, command)


def normalize_symbol(value: str) -> str:
    return str(value).strip().upper()


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


def _format_export_markdown(export: dict[str, Any]) -> str:
    lines = [
        "# Account Layer Config Export",
        "",
        f"- account: {export.get('account', '')}",
        f"- scope_classification: {export.get('scope_classification', '')}",
        f"- root_mirror_match: {str(export.get('root_mirror_match', False)).lower()}",
        "",
        "## Counts",
        "",
    ]
    for layer in LAYER_ORDER:
        lines.append(f"- {layer}: {len(export['layers'].get(layer, []))}")
    lines.extend(["", "## Symbols"])
    for layer in LAYER_ORDER:
        lines.append(f"- {layer}: {', '.join(export['layers'].get(layer, [])) if export['layers'].get(layer, []) else 'none'}")
    lines.extend(["", "## Root Mirror"])
    for layer in LAYER_ORDER:
        lines.append(f"- {layer}: {', '.join(export['root_mirror'].get(layer, [])) if export['root_mirror'].get(layer, []) else 'none'}")
    lines.extend(["", "## Policy Warnings"])
    lines.extend([f"- {_safe_report_text(item)}" for item in export.get("policy_warnings", [])] or ["- none"])
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
