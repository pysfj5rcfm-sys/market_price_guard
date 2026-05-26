from __future__ import annotations

import argparse
from pathlib import Path

from .account_config import normalize_account
from .config_observability import PROJECT_ROOT, run_config_check


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check account layer config source and root mirror consistency.")
    parser.add_argument("--account", "-Account", default="tech")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "outputs_config_check_latest")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    account = normalize_account(args.account)
    result = run_config_check(args.output_dir, account=account)
    prefix = "tech_layer_config_check" if account == "tech" else f"{account}_layer_config_check"
    print(f"account: {account}")
    print(f"account_bootstrapped: {str(result.get('account_bootstrapped', False)).lower()}")
    if not result.get("account_bootstrapped", False):
        print(f"{account}_account_not_bootstrapped")
        for path in result.get("missing_account_config_files", []):
            print(f"missing {path}")
    print(f"Config check report: {args.output_dir / (prefix + '.md')}")
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
