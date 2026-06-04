from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


TASK_NAMES = [
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

TASK_STATUSES = [
    "pending",
    "running",
    "passed",
    "failed",
    "strict_blocked_but_reported",
    "runtime_warning",
    "cancelled",
]

ACCEPTABLE_TASK_STATUSES = {"passed", "strict_blocked_but_reported", "runtime_warning"}


@dataclass(frozen=True)
class TaskOptions:
    use_run_cache: bool = False
    continue_on_failure: bool = False
    optional_note: str = ""


@dataclass(frozen=True)
class TaskDefinition:
    task_name: str
    label: str
    batch_name: str
    supports_run_cache: bool = False
    supports_continue_on_failure: bool = False


@dataclass
class TaskRecord:
    task_id: str
    task_name: str
    batch_name: str
    command: str
    cwd: str
    started_at: str
    finished_at: str
    elapsed_seconds: float | None
    exit_code: int | None
    status: str
    stdout_log_path: str
    stderr_log_path: str
    summary_paths: list[str] = field(default_factory=list)
    output_paths: list[str] = field(default_factory=list)
    bundle_eligible: bool = False
    warnings: list[str] = field(default_factory=list)
    no_trading_advice: bool = True
    optional_note: str = ""
    lock: dict[str, Any] = field(default_factory=dict)
    summary_preview: dict[str, Any] = field(default_factory=dict)
    stdout_tail: str = ""
    stderr_tail: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
