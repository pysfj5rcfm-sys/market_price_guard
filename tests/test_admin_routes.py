from __future__ import annotations

import asyncio
from urllib.parse import urlencode

from market_price_guard.admin_app import app


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


def test_admin_app_imports_successfully():
    assert app.title == "market_price_guard Local Admin"


def test_admin_routes_exist_and_home_returns_200():
    status, body = asyncio.run(_request("/admin"))

    assert status == 200
    assert b"Local Admin Layer Manager" in body
    assert b"No pipeline runner in v0.8.0" in body


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


def test_admin_v080_has_no_pipeline_or_bundle_routes():
    pipeline_status, _ = asyncio.run(_request("/admin/pipeline"))
    bundle_status, _ = asyncio.run(_request("/admin/bundle"))

    assert pipeline_status == 404
    assert bundle_status == 404
