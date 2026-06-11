from __future__ import annotations

import asyncio
from urllib.parse import urlencode
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("uvicorn")
pytest.importorskip("jinja2")

from market_price_guard.admin_app import app
from market_price_guard.admin_task_models import TaskRecord
from market_price_guard.admin_task_runner import TaskRunnerError


async def _request(path: str, query: dict[str, str] | None = None) -> tuple[int, bytes]:
    messages: list[dict[str, object]] = []
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "method": "GET",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": urlencode(query or {}).encode("ascii"),
        "headers": [(b"host", b"testserver")],
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("testclient", 50000),
        "root_path": "",
    }

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, object]) -> None:
        messages.append(message)

    await app(scope, receive, send)
    status = next(int(message["status"]) for message in messages if message["type"] == "http.response.start")
    body = b"".join(bytes(message.get("body", b"")) for message in messages if message["type"] == "http.response.body")
    return status, body


async def _post_form(path: str, data: dict[str, str]) -> tuple[int, dict[str, str], bytes]:
    body_bytes = urlencode(data).encode("ascii")
    messages: list[dict[str, object]] = []
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "method": "POST",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "headers": [
            (b"host", b"testserver"),
            (b"content-type", b"application/x-www-form-urlencoded"),
            (b"content-length", str(len(body_bytes)).encode("ascii")),
        ],
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("testclient", 50000),
        "root_path": "",
    }

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": body_bytes, "more_body": False}

    async def send(message: dict[str, object]) -> None:
        messages.append(message)

    await app(scope, receive, send)
    status = next(int(message["status"]) for message in messages if message["type"] == "http.response.start")
    headers = {
        key.decode("latin1").lower(): value.decode("latin1")
        for message in messages
        if message["type"] == "http.response.start"
        for key, value in message.get("headers", [])
    }
    body = b"".join(bytes(message.get("body", b"")) for message in messages if message["type"] == "http.response.body")
    return status, headers, body


def _record(task_id: str = "task_1", status: str = "passed", exit_code: int = 0) -> TaskRecord:
    return TaskRecord(
        task_id=task_id,
        task_name="config_check_tech",
        batch_name="config_check_tech",
        command="pwsh ./scripts/check_account_layer_config.ps1 -Account tech",
        cwd="D:/AIProjects/market_price_guard",
        started_at="2026-06-11T00:00:00+00:00",
        finished_at="2026-06-11T00:00:01+00:00",
        elapsed_seconds=1.0,
        exit_code=exit_code,
        status=status,
        stdout_log_path="runtime/admin_tasks/task_1.stdout.log",
        stderr_log_path="runtime/admin_tasks/task_1.stderr.log",
        stdout_tail="stdout tail",
        stderr_tail="stderr tail",
    )


def test_admin_app_imports_successfully():
    assert app.title == "market_price_guard Local Admin"


def test_admin_routes_exist_and_home_returns_200():
    status, body = asyncio.run(_request("/admin"))

    assert status == 200
    assert b"Local Admin Layer Manager" in body
    assert b"Task runner" in body


def test_admin_account_pages_return_200():
    tech_status, tech_body = asyncio.run(_request("/admin/accounts/tech"))
    energy_status, energy_body = asyncio.run(_request("/admin/accounts/energy"))

    assert tech_status == 200
    assert energy_status == 200
    assert b"Tech Account" in tech_body
    assert b"Energy Account" in energy_body


def test_admin_validate_route_returns_200():
    status, body = asyncio.run(_request("/admin/validate"))

    assert status == 200
    assert b"Validate tech" in body
    assert b"Validate energy" in body


def test_admin_v081_task_and_bundle_routes_exist():
    tasks_status, tasks_body = asyncio.run(_request("/admin/tasks"))
    bundles_status, bundles_body = asyncio.run(_request("/admin/bundles"))

    assert tasks_status == 200
    assert bundles_status == 200
    assert b"Pipeline Runner" in tasks_body
    assert b"Output Bundles" in bundles_body


def test_admin_task_run_redirects_to_detail(monkeypatch):
    calls = []

    class FakeRunner:
        def run_task(self, task_name, options):
            calls.append((task_name, options))
            return _record("task_123")

    monkeypatch.setattr("market_price_guard.admin_routes.get_task_runner", lambda request: FakeRunner())

    status, headers, _body = asyncio.run(_post_form("/admin/tasks/run", {"task_name": "config_check_tech"}))

    assert status == 303
    assert headers["location"] == "/admin/tasks/task_123"
    assert calls[0][0] == "config_check_tech"
    assert calls[0][1].use_run_cache is False


def test_admin_task_run_rejects_unknown_task(monkeypatch):
    class FakeRunner:
        def run_task(self, task_name, options):
            raise TaskRunnerError(f"unsupported task_name: {task_name}")

    monkeypatch.setattr("market_price_guard.admin_routes.get_task_runner", lambda request: FakeRunner())

    status, _headers, body = asyncio.run(_post_form("/admin/tasks/run", {"task_name": "not_allowed"}))

    assert status == 400
    assert b"unsupported task_name" in body


def test_admin_task_run_cache_checkbox_maps_to_options(monkeypatch):
    calls = []

    class FakeRunner:
        def run_task(self, task_name, options):
            calls.append((task_name, options))
            return _record("task_cache")

    monkeypatch.setattr("market_price_guard.admin_routes.get_task_runner", lambda request: FakeRunner())

    status, headers, _body = asyncio.run(_post_form("/admin/tasks/run", {"task_name": "tech_pipeline", "use_run_cache": "true"}))

    assert status == 303
    assert headers["location"] == "/admin/tasks/task_cache"
    assert calls[0][0] == "tech_pipeline"
    assert calls[0][1].use_run_cache is True


def test_admin_task_detail_shows_failed_logs(monkeypatch):
    class FakeRunner:
        def load_task(self, task_id):
            return _record(task_id, status="failed", exit_code=1)

    monkeypatch.setattr("market_price_guard.admin_routes.get_task_runner", lambda request: FakeRunner())

    status, body = asyncio.run(_request("/admin/tasks/task_failed"))

    assert status == 200
    assert b"failed" in body
    assert b"stdout tail" in body
    assert b"stderr tail" in body


def test_admin_task_detail_missing_is_friendly_404(monkeypatch):
    class FakeRunner:
        def load_task(self, task_id):
            return None

    monkeypatch.setattr("market_price_guard.admin_routes.get_task_runner", lambda request: FakeRunner())

    status, body = asyncio.run(_request("/admin/tasks/missing_task"))

    assert status == 404
    assert b"task not found" in body


def test_bundle_download_rejects_path_traversal():
    status, body = asyncio.run(_request("/admin/bundles/download/..%2Fsecret.zip"))

    assert status == 404
    assert b"bundle" in body.lower() or body == b'{"detail":"invalid bundle name"}'


def test_admin_templates_and_css_keep_alignment_classes():
    css = Path("static/admin/admin.css").read_text(encoding="utf-8")
    tasks = Path("templates/admin/tasks.html").read_text(encoding="utf-8")
    detail = Path("templates/admin/task_detail.html").read_text(encoding="utf-8")
    bundles = Path("templates/admin/bundles.html").read_text(encoding="utf-8")

    for expected in [".task-card", ".toolbar", ".status-pill", ".log-box", ".action-cell"]:
        assert expected in css
    assert 'method="post" action="/admin/tasks/run"' in tasks
    assert 'name="task_name"' in tasks
    assert "status-pill" in detail
    assert "log-box" in detail
    assert "action-cell" in bundles
