from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from market_price_guard.admin_task_models import TASK_NAMES, TaskOptions
from market_price_guard.admin_task_runner import AdminTaskRunner, TaskRunnerError, POWER_SHELL_MISSING, resolve_powershell_executable, utc_now


def test_task_whitelist_matches_v081_scope():
    assert TASK_NAMES == [
        "tech_pipeline",
        "energy_pipeline",
        "both_pipelines",
        "uat_quick",
        "uat_intraday",
        "uat_energy",
        "acceptance",
        "config_check_tech",
        "config_check_energy",
        "config_check_both",
    ]


def test_unknown_task_name_is_rejected(tmp_path):
    runner = AdminTaskRunner(tmp_path)

    with pytest.raises(TaskRunnerError):
        runner.run_task("echo hello")


def test_task_runner_builds_expected_commands(tmp_path):
    runner = AdminTaskRunner(tmp_path)

    assert runner._command_sequence("tech_pipeline", TaskOptions(use_run_cache=False)) == [
        ["pwsh", "./scripts/run_tech_research_pipeline.ps1"]
    ]
    assert runner._command_sequence("tech_pipeline", TaskOptions(use_run_cache=True)) == [
        ["pwsh", "./scripts/run_tech_research_pipeline.ps1", "-UseRunCache"]
    ]
    assert runner._command_sequence("energy_pipeline", TaskOptions()) == [["pwsh", "./scripts/run_energy_research_pipeline.ps1"]]
    assert runner._command_sequence("uat_quick", TaskOptions(use_run_cache=True)) == [["pwsh", "./scripts/run_uat.ps1", "-Mode", "quick", "-UseRunCache"]]
    assert runner._command_sequence("uat_intraday", TaskOptions(use_run_cache=True)) == [
        ["pwsh", "./scripts/run_uat.ps1", "-Mode", "intraday", "-UseRunCache"]
    ]
    assert runner._command_sequence("uat_energy", TaskOptions(use_run_cache=True)) == [["pwsh", "./scripts/run_uat.ps1", "-Mode", "energy", "-UseRunCache"]]
    assert runner._command_sequence("acceptance", TaskOptions()) == [["pwsh", "./scripts/build_acceptance_summary.ps1"]]


def test_task_runner_writes_record_and_logs(tmp_path, monkeypatch):
    calls: list[dict[str, object]] = []

    def fake_run(command, **kwargs):
        calls.append({"command": command, **kwargs})
        return SimpleNamespace(returncode=0, stdout="ok\n", stderr="warn\n")

    monkeypatch.setattr("market_price_guard.admin_task_runner.resolve_powershell_executable", lambda: "/usr/bin/pwsh")
    monkeypatch.setattr("market_price_guard.admin_task_runner.subprocess.run", fake_run)

    record = AdminTaskRunner(tmp_path).run_task("acceptance")

    assert record.status == "passed"
    assert record.exit_code == 0
    assert "ok" in Path(record.stdout_log_path).read_text(encoding="utf-8")
    assert "warn" in Path(record.stderr_log_path).read_text(encoding="utf-8")
    saved = json.loads((tmp_path / "runtime/admin_tasks" / f"{record.task_id}.json").read_text(encoding="utf-8"))
    assert saved["task_name"] == "acceptance"
    assert saved["no_trading_advice"] is True
    assert calls[0]["shell"] is False


def test_task_runner_uses_reported_pipeline_status(tmp_path, monkeypatch):
    output_dir = tmp_path / "outputs_tech_pipeline_latest"
    output_dir.mkdir()
    (output_dir / "pipeline_manifest.json").write_text(
        json.dumps({"summary": {"passed": 5, "failed": 0, "strict_blocked_but_reported": 1, "runtime_warnings": 0}}),
        encoding="utf-8",
    )
    (output_dir / "pipeline_summary.md").write_text("# summary\n", encoding="utf-8")

    monkeypatch.setattr("market_price_guard.admin_task_runner.resolve_powershell_executable", lambda: "/usr/bin/pwsh")
    monkeypatch.setattr(
        "market_price_guard.admin_task_runner.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    record = AdminTaskRunner(tmp_path).run_task("tech_pipeline")

    assert record.status == "strict_blocked_but_reported"


def test_missing_pwsh_records_clear_failure(tmp_path, monkeypatch):
    monkeypatch.setattr("market_price_guard.admin_task_runner.resolve_powershell_executable", lambda: "")

    record = AdminTaskRunner(tmp_path).run_task("acceptance")

    assert record.status == "failed"
    assert record.exit_code == 1
    assert POWER_SHELL_MISSING in record.warnings
    assert POWER_SHELL_MISSING in Path(record.stderr_log_path).read_text(encoding="utf-8")


def test_powershell_resolver_prefers_platform_candidates(monkeypatch):
    seen: list[str] = []

    def fake_which(name: str) -> str | None:
        seen.append(name)
        return "C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe" if name == "powershell.exe" else None

    monkeypatch.setattr("market_price_guard.admin_task_runner.os.name", "nt")
    monkeypatch.setattr("market_price_guard.admin_task_runner.shutil.which", fake_which)

    assert resolve_powershell_executable().endswith("powershell.exe")
    assert seen[:2] == ["pwsh", "powershell.exe"]


def test_task_lock_prevents_concurrent_task(tmp_path, monkeypatch):
    lock_path = tmp_path / "runtime/admin_task.lock"
    lock_path.parent.mkdir(parents=True)
    lock_path.write_text(
        json.dumps({"task_id": "current", "task_name": "tech_pipeline", "pid": os.getpid(), "created_at": utc_now()}),
        encoding="utf-8",
    )
    monkeypatch.setattr("market_price_guard.admin_task_runner.subprocess.run", lambda *args, **kwargs: pytest.fail("should not run"))

    record = AdminTaskRunner(tmp_path).run_task("energy_pipeline")

    assert record.status == "failed"
    assert record.lock["acquired"] is False
    assert "task lock active" in record.warnings
