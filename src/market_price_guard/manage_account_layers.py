from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .account_config import LAYER_ORDER, account_layer_paths, normalize_account, normalize_layer as normalize_account_layer
from .config_observability import PROJECT_ROOT, run_config_check
from .manage_tech_layers import TechLayerManager


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
        if command in {"show", "validate", "export"}:
            report = self._not_bootstrapped_report(command)
            if command == "validate":
                check = run_config_check(self.project_root / "outputs_config_check_latest", self.project_root, account=self.account)
                report["validation_status"] = str(check.get("status", "unknown"))
                report["warnings"] = check.get("warnings", [])
                report["errors"] = check.get("errors", [])
                if not report["errors"]:
                    report["errors"] = [f"{self.account}_account_not_bootstrapped"]
            return report
        report = self._not_bootstrapped_report(command)
        report["errors"] = [f"{self.account}_account_not_bootstrapped"]
        return report

    def _add_account_fields(self, report: dict[str, Any]) -> dict[str, Any]:
        report = dict(report)
        report.update(
            {
                "account": self.account,
                "scope_classification": "account-generic foundation",
                "account_project_path": self.paths.project_path,
                "root_mirror_path": self.paths.root_mirror_path,
                "account_bootstrapped": True,
                "missing_account_config_files": [],
            }
        )
        return report

    def _not_bootstrapped_report(self, command: str) -> dict[str, Any]:
        missing = self.paths.missing_config_files(self.project_root)
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "command": command,
            "dry_run": False,
            "account": self.account,
            "scope_classification": "account-generic foundation",
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
            "root_mirror_synced": False,
            "backup_path": "",
        }

    def write_report(self, report: dict[str, Any]) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "config_manager_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (self.output_dir / "config_manager_report.md").write_text(_format_markdown_report(report), encoding="utf-8")


def normalize_layer(value: str, account: str = "tech") -> str:
    return normalize_account_layer(value, account=account)


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
    lines = [
        f"account: {report.get('account', '')}",
        f"command: {report.get('command', '')}",
        f"account_bootstrapped: {str(report.get('account_bootstrapped', False)).lower()}",
        f"validation_status: {report.get('validation_status', '')}",
        f"before_counts: {report.get('before_counts', {})}",
        f"after_counts: {report.get('after_counts', {})}",
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


if __name__ == "__main__":
    raise SystemExit(main())
