from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .admin_summary_reader import output_paths_for, read_summary_preview, reported_status_from_summary, summary_paths_for
from .admin_task_models import ACCEPTABLE_TASK_STATUSES, TASK_NAMES, TaskDefinition, TaskOptions, TaskRecord
from .config_observability import PROJECT_ROOT


TASK_DEFINITIONS: dict[str, TaskDefinition] = {
    "tech_pipeline": TaskDefinition("tech_pipeline", "Tech pipeline", "tech_pipeline", supports_run_cache=True),
    "energy_pipeline": TaskDefinition("energy_pipeline", "Energy pipeline", "energy_pipeline"),
    "both_pipelines": TaskDefinition("both_pipelines", "Both pipelines", "both_pipelines", supports_run_cache=True, supports_continue_on_failure=True),
    "uat_quick": TaskDefinition("uat_quick", "UAT quick", "uat_quick", supports_run_cache=True),
    "uat_intraday": TaskDefinition("uat_intraday", "UAT intraday", "uat_intraday", supports_run_cache=True),
    "uat_energy": TaskDefinition("uat_energy", "UAT energy", "uat_energy", supports_run_cache=True),
    "acceptance": TaskDefinition("acceptance", "Acceptance summary", "acceptance"),
    "config_check_tech": TaskDefinition("config_check_tech", "Config check tech", "config_check_tech"),
    "config_check_energy": TaskDefinition("config_check_energy", "Config check energy", "config_check_energy"),
    "config_check_both": TaskDefinition("config_check_both", "Config check both", "config_check_both"),
}

_PROCESS_LOCK = threading.Lock()
STALE_LOCK_SECONDS = 6 * 60 * 60
POWER_SHELL_MISSING = "PowerShell executable not found. Please install pwsh."


class TaskRunnerError(ValueError):
    pass


class AdminTaskRunner:
    def __init__(self, project_root: Path = PROJECT_ROOT) -> None:
        self.project_root = Path(project_root)
        self.task_dir = self.project_root / "runtime" / "admin_tasks"
        self.lock_path = self.project_root / "runtime" / "admin_task.lock"

    def definitions(self) -> list[TaskDefinition]:
        return [TASK_DEFINITIONS[name] for name in TASK_NAMES]

    def run_task(self, task_name: str, options: TaskOptions | None = None) -> TaskRecord:
        if task_name not in TASK_DEFINITIONS:
            raise TaskRunnerError(f"unsupported task_name: {task_name}")
        options = options or TaskOptions()
        definition = TASK_DEFINITIONS[task_name]
        task_id = _task_id(task_name)
        self.task_dir.mkdir(parents=True, exist_ok=True)
        stdout_path = self.task_dir / f"{task_id}.stdout.log"
        stderr_path = self.task_dir / f"{task_id}.stderr.log"
        record = TaskRecord(
            task_id=task_id,
            task_name=task_name,
            batch_name=definition.batch_name,
            command=_format_sequence(self._command_sequence(task_name, options)),
            cwd=str(self.project_root),
            started_at=utc_now(),
            finished_at="",
            elapsed_seconds=None,
            exit_code=None,
            status="pending",
            stdout_log_path=str(stdout_path),
            stderr_log_path=str(stderr_path),
            bundle_eligible=True,
            optional_note=options.optional_note,
        )
        self._write_logs(stdout_path, stderr_path, "", "")
        self._write_record(record)
        lock_context = self._lock_context(task_id, task_name)
        try:
            with lock_context as lock_info:
                record.lock = lock_info
                if not lock_info.get("acquired"):
                    record.status = "failed"
                    record.finished_at = utc_now()
                    record.elapsed_seconds = 0.0
                    record.warnings.append(str(lock_info.get("reason") or "task lock active"))
                    self._write_record(record)
                    return self._hydrate_record(record)
                return self._run_locked(record, options)
        except Exception as exc:
            record.status = "failed"
            record.finished_at = utc_now()
            record.elapsed_seconds = _elapsed(record.started_at, record.finished_at)
            record.exit_code = 1
            record.warnings.append(f"{type(exc).__name__}: {exc}")
            self._write_record(record)
            return self._hydrate_record(record)

    def recent_tasks(self, limit: int = 10) -> list[TaskRecord]:
        if not self.task_dir.exists():
            return []
        paths = sorted(self.task_dir.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
        records = []
        for path in paths[:limit]:
            record = self.load_task(path.stem)
            if record:
                records.append(record)
        return records

    def load_task(self, task_id: str) -> TaskRecord | None:
        if not _safe_name(task_id):
            return None
        path = self.task_dir / f"{task_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            record = TaskRecord(**data)
        except (OSError, TypeError, json.JSONDecodeError):
            return None
        return self._hydrate_record(record)

    def lock_status(self) -> dict[str, Any]:
        return read_lock_status(self.lock_path)

    def _run_locked(self, record: TaskRecord, options: TaskOptions) -> TaskRecord:
        record.status = "running"
        self._write_record(record)
        sequence = self._command_sequence(record.task_name, options)
        pwsh = shutil.which("pwsh")
        if not pwsh:
            record.status = "failed"
            record.exit_code = 1
            record.finished_at = utc_now()
            record.elapsed_seconds = _elapsed(record.started_at, record.finished_at)
            record.warnings.append(POWER_SHELL_MISSING)
            self._write_logs(Path(record.stdout_log_path), Path(record.stderr_log_path), "", POWER_SHELL_MISSING + "\n")
            self._write_record(record)
            return self._hydrate_record(record)

        stdout_chunks: list[str] = []
        stderr_chunks: list[str] = []
        exit_codes: list[int] = []
        statuses: list[str] = []
        for command in sequence:
            runnable = [pwsh, *command[1:]]
            result = subprocess.run(runnable, cwd=self.project_root, capture_output=True, text=True, shell=False, env=_script_env(self.project_root))
            stdout_chunks.append(result.stdout or "")
            stderr_chunks.append(result.stderr or "")
            exit_codes.append(int(result.returncode))
            statuses.append(_status_from_exit(int(result.returncode)))
            if result.returncode != 0 and not options.continue_on_failure:
                break
        record.exit_code = _combined_exit(exit_codes)
        record.status = _combined_status(statuses)
        if record.status == "passed":
            record.status = reported_status_from_summary(record.task_name, self.project_root)
        record.finished_at = utc_now()
        record.elapsed_seconds = _elapsed(record.started_at, record.finished_at)
        record.summary_paths = summary_paths_for(record.task_name, self.project_root)
        record.output_paths = output_paths_for(record.task_name, self.project_root)
        record.summary_preview = read_summary_preview(record.task_name, self.project_root)
        record.bundle_eligible = record.status in ACCEPTABLE_TASK_STATUSES
        self._write_logs(Path(record.stdout_log_path), Path(record.stderr_log_path), "\n".join(stdout_chunks), "\n".join(stderr_chunks))
        self._write_record(record)
        return self._hydrate_record(record)

    def _command_sequence(self, task_name: str, options: TaskOptions) -> list[list[str]]:
        cache = bool(options.use_run_cache and TASK_DEFINITIONS[task_name].supports_run_cache)
        if task_name == "tech_pipeline":
            return [["pwsh", "./scripts/run_tech_research_pipeline.ps1", "-UseRunCache"]]
        if task_name == "energy_pipeline":
            return [["pwsh", "./scripts/run_energy_research_pipeline.ps1"]]
        if task_name == "both_pipelines":
            return [*self._command_sequence("tech_pipeline", TaskOptions(use_run_cache=True)), *self._command_sequence("energy_pipeline", TaskOptions())]
        if task_name == "uat_quick":
            return [["pwsh", "./scripts/run_uat.ps1", "-Mode", "quick", "-UseRunCache"]]
        if task_name == "uat_intraday":
            return [["pwsh", "./scripts/run_uat.ps1", "-Mode", "intraday", "-UseRunCache"]]
        if task_name == "uat_energy":
            return [["pwsh", "./scripts/run_uat.ps1", "-Mode", "energy", "-UseRunCache"]]
        if task_name == "acceptance":
            return [["pwsh", "./scripts/build_acceptance_summary.ps1"]]
        if task_name == "config_check_tech":
            return [["pwsh", "./scripts/check_account_layer_config.ps1", "-Account", "tech"]]
        if task_name == "config_check_energy":
            return [["pwsh", "./scripts/check_account_layer_config.ps1", "-Account", "energy"]]
        if task_name == "config_check_both":
            return [
                ["pwsh", "./scripts/check_account_layer_config.ps1", "-Account", "tech"],
                ["pwsh", "./scripts/check_account_layer_config.ps1", "-Account", "energy"],
            ]
        raise TaskRunnerError(f"unsupported task_name: {task_name}")

    @contextmanager
    def _lock_context(self, task_id: str, task_name: str) -> Iterator[dict[str, Any]]:
        with _PROCESS_LOCK:
            acquired, info = acquire_lock(self.lock_path, task_id=task_id, task_name=task_name)
        if not acquired:
            yield info
            return
        try:
            yield info
        finally:
            release_lock(self.lock_path, task_id=task_id)

    def _write_record(self, record: TaskRecord) -> None:
        self.task_dir.mkdir(parents=True, exist_ok=True)
        path = self.task_dir / f"{record.task_id}.json"
        path.write_text(json.dumps(record.as_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def _write_logs(stdout_path: Path, stderr_path: Path, stdout: str, stderr: str) -> None:
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        stdout_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text(stderr, encoding="utf-8")

    def _hydrate_record(self, record: TaskRecord) -> TaskRecord:
        record.stdout_tail = tail_text(Path(record.stdout_log_path))
        record.stderr_tail = tail_text(Path(record.stderr_log_path))
        if not record.summary_paths:
            record.summary_paths = summary_paths_for(record.task_name, self.project_root)
        if not record.output_paths:
            record.output_paths = output_paths_for(record.task_name, self.project_root)
        if not record.summary_preview:
            record.summary_preview = read_summary_preview(record.task_name, self.project_root)
        return record


def acquire_lock(lock_path: Path, *, task_id: str, task_name: str) -> tuple[bool, dict[str, Any]]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    existing = read_lock_status(lock_path)
    if existing.get("active"):
        return False, {"acquired": False, "reason": "task lock active", "existing": existing}
    if lock_path.exists():
        try:
            lock_path.unlink()
        except OSError:
            return False, {"acquired": False, "reason": "stale task lock could not be cleared", "existing": existing}
    data = {"task_id": task_id, "task_name": task_name, "pid": os.getpid(), "created_at": utc_now()}
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    try:
        fd = os.open(lock_path, flags)
    except FileExistsError:
        return False, {"acquired": False, "reason": "task lock active", "existing": read_lock_status(lock_path)}
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return True, {"acquired": True, **data}


def release_lock(lock_path: Path, *, task_id: str) -> None:
    try:
        data = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if data.get("task_id") == task_id:
        try:
            lock_path.unlink()
        except OSError:
            return


def read_lock_status(lock_path: Path) -> dict[str, Any]:
    if not lock_path.exists():
        return {"active": False, "path": str(lock_path)}
    try:
        data = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"active": True, "stale": True, "path": str(lock_path), "reason": "lock file is not valid JSON"}
    created_at = str(data.get("created_at") or "")
    age = _age_seconds(created_at)
    pid = data.get("pid")
    active = bool(_pid_active(pid) and age < STALE_LOCK_SECONDS)
    data.update({"active": active, "stale": not active, "path": str(lock_path), "age_seconds": age})
    return data


def tail_text(path: Path, max_lines: int = 200) -> str:
    if not path.exists():
        return ""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    return "\n".join(lines[-max_lines:])


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _task_id(task_name: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"{stamp}_{task_name}_{uuid.uuid4().hex[:8]}"


def _status_from_exit(exit_code: int) -> str:
    if exit_code == 0:
        return "passed"
    if exit_code == 2:
        return "strict_blocked_but_reported"
    return "failed"


def _combined_status(statuses: list[str]) -> str:
    if not statuses:
        return "failed"
    if "failed" in statuses:
        return "failed"
    if "strict_blocked_but_reported" in statuses:
        return "strict_blocked_but_reported"
    if "runtime_warning" in statuses:
        return "runtime_warning"
    return "passed"


def _combined_exit(exit_codes: list[int]) -> int | None:
    if not exit_codes:
        return None
    for code in exit_codes:
        if code != 0:
            return code
    return 0


def _format_sequence(sequence: list[list[str]]) -> str:
    return " | ".join(" ".join(item) for item in sequence)


def _elapsed(started_at: str, finished_at: str) -> float:
    try:
        start = datetime.fromisoformat(started_at)
        finish = datetime.fromisoformat(finished_at)
    except ValueError:
        return 0.0
    return round((finish - start).total_seconds(), 3)


def _age_seconds(created_at: str) -> float:
    try:
        created = datetime.fromisoformat(created_at)
    except ValueError:
        return STALE_LOCK_SECONDS + 1
    return time.time() - created.timestamp()


def _pid_active(pid: Any) -> bool:
    try:
        value = int(pid)
    except (TypeError, ValueError):
        return False
    if value <= 0:
        return False
    try:
        os.kill(value, 0)
        return True
    except OSError:
        return False


def _safe_name(value: str) -> bool:
    return bool(value) and "/" not in value and "\\" not in value and ".." not in value


def _script_env(project_root: Path) -> dict[str, str]:
    values = dict(os.environ)
    path_parts = []
    venv_bin = project_root / ".venv" / "bin"
    if venv_bin.exists():
        path_parts.append(str(venv_bin))
    if values.get("PATH"):
        path_parts.append(values["PATH"])
    if path_parts:
        values["PATH"] = os.pathsep.join(path_parts)
    src = project_root / "src"
    python_path_parts = [str(src)]
    if values.get("PYTHONPATH"):
        python_path_parts.append(values["PYTHONPATH"])
    values["PYTHONPATH"] = os.pathsep.join(python_path_parts)
    if not values.get("USERPROFILE") and values.get("HOME"):
        values["USERPROFILE"] = values["HOME"]
    return values
