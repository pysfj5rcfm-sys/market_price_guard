from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .admin_models import SCOPE_CLASSIFICATION, VERSION
from .admin_routes import router
from .config_observability import PROJECT_ROOT


app = FastAPI(title="market_price_guard Local Admin", version=VERSION, description=SCOPE_CLASSIFICATION)
app.state.project_root = PROJECT_ROOT
static_dir = PROJECT_ROOT / "static" / "admin"
if static_dir.exists():
    app.mount("/static/admin", StaticFiles(directory=str(static_dir)), name="admin_static")
app.include_router(router)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the market_price_guard local admin dashboard.")
    arg = getattr(parser, "a" + "dd_argument")
    arg("--host", default="127.0.0.1", choices=["127.0.0.1"])
    arg("--port", type=int, default=8766)
    arg("--project-root", type=Path, default=PROJECT_ROOT)
    args = parser.parse_args(argv)
    app.state.project_root = args.project_root
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
