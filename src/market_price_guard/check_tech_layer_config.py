from __future__ import annotations

import argparse
from pathlib import Path

from .config_observability import PROJECT_ROOT, run_config_check


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check tech layer config source and root mirror consistency.")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "outputs_config_check_latest")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_config_check(args.output_dir)
    print(f"Config check report: {args.output_dir / 'tech_layer_config_check.md'}")
    return 1 if result.get("status") == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
