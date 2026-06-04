from __future__ import annotations

from types import SimpleNamespace

import pytest

from market_price_guard.admin_task_models import TaskOptions
from market_price_guard.admin_task_runner import AdminTaskRunner, TaskRunnerError


def test_task_runner_never_uses_user_supplied_command_text(tmp_path, monkeypatch):
    seen = []

    def fake_run(command, **kwargs):
        seen.append((command, kwargs))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("market_price_guard.admin_task_runner.shutil.which", lambda name: "/usr/bin/pwsh")
    monkeypatch.setattr("market_price_guard.admin_task_runner.subprocess.run", fake_run)

    record = AdminTaskRunner(tmp_path).run_task("tech_pipeline", TaskOptions(optional_note="; rm -rf project"))

    assert record.status == "passed"
    assert record.command == "pwsh ./scripts/run_tech_research_pipeline.ps1 -UseRunCache"
    assert seen[0][0] == ["/usr/bin/pwsh", "./scripts/run_tech_research_pipeline.ps1", "-UseRunCache"]
    assert seen[0][1]["shell"] is False


def test_unknown_task_cannot_be_treated_as_shell_command(tmp_path):
    with pytest.raises(TaskRunnerError):
        AdminTaskRunner(tmp_path).run_task("pwsh ./scripts/run_uat.ps1 -Mode quick")
