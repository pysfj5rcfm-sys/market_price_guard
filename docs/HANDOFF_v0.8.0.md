# HANDOFF v0.8.0

Version: v0.8.0 | Local Admin Layer Manager UI

Scope classification: local FastAPI admin dashboard for account layer management.

## Completed

- Implemented a local FastAPI admin app for account layer management.
- Created Jinja templates with HTMX-style partial result pages and plain CSS.
- Created tech and energy account pages with four-layer display.
- Implemented symbol wizard, move, remove, dry-run, apply, validate, backup, root mirror sync, registry status, policy warnings, and audit log support.
- Created Mac/Linux and PowerShell local startup scripts.
- Created admin tests for symbol inference, routes, dry-run, apply safety, backup, audit, validation, root mirror sync, and boundary checks.

## Current Baselines

Tech current baseline:

| layer | count |
|---|---:|
| operation | 7 |
| operation_candidate | 19 |
| watchlist | 28 |
| scan | 40 |

Energy current baseline:

| layer | count |
|---|---:|
| operation | 4 |
| operation_candidate | 8 |
| watchlist | 24 |
| scan | 41 |

The historical tech 7 / 11 / 16 / 30 baseline is not current.

## Startup

Local URL:

```text
http://127.0.0.1:8766/admin
```

Commands:

```powershell
.\scripts\run_admin_dashboard.ps1
```

```sh
./scripts/run_admin_dashboard.sh
```

```sh
python -m market_price_guard.admin_app --host 127.0.0.1 --port 8766
uvicorn market_price_guard.admin_app:app --host 127.0.0.1 --port 8766
```

## Routes

- `/admin`
- `/admin/accounts/{account}` where account is `tech` or `energy`
- `/admin/layers/a` + `dd` for the symbol wizard runtime path
- `/admin/layers/move`
- `/admin/layers/remove`
- `/admin/validate`
- `/admin/registry/{symbol}`

There is no pipeline runner route in v0.8.0. There is no zip bundle route in v0.8.0.

## Symbol Wizard

Minimum required fields:

- account
- target_layer
- symbol

Optional fields:

- display_name
- note
- category
- instrument_type when inference is ambiguous

Wizard flow:

- Step 1 captures the minimum fields.
- Step 2 analyzes raw symbol, canonical symbol, market, asset type, registry status, existing layers, duplicate status, policy warnings, suggested category, and registry stub need.
- Step 3 confirms instrument type and category.
- Step 4 shows dry-run preview.
- Step 5 applies only after explicit confirmation.

## Canonicalization Rules

- Existing suffixes `.SZ`, `.SH`, and `.HK` are kept and normalized.
- `159`, `002`, `003`, `300`, and `301` six-digit codes infer `.SZ`.
- `510`, `511`, `512`, `513`, `515`, `516`, `517`, `518`, `588`, `600`, `601`, `603`, `605`, and `688` six-digit codes infer `.SH`.
- Five-digit numeric symbols infer `.HK`.
- `GOLD_CNY` remains manual.
- Global tickers such as `QQQ` remain suffix-free.
- Ambiguous symbols require user selection.

## Registry Handling

- Registered symbols display registry name, market, asset type, tags, and status.
- Missing registry symbols show a registry_missing warning.
- Missing registry symbols may continue as layer configuration changes with warning.
- Minimal registry stub creation is optional and only happens when the checkbox is selected.
- v0.8.0 is not a full registry editor.

## Policy Warnings

Policy warning display maps existing manager/config policy markers. It covers:

- operation layer explicit confirmation
- registry_missing
- duplicate target-layer membership
- membership in other layers
- root mirror sync notice
- non-tech broad index warning for tech account
- manual asset warning
- failed-trial and no-increase/no-intraday markers
- event watch markers

Policy warnings are configuration warnings only. The admin UI generates no trading advice.

## Dry-Run And Apply

Dry-run returns:

- operation type
- account and symbol
- canonical symbol
- source and target layer
- files to modify
- root mirror sync plan
- registry stub plan
- policy warnings
- before and after counts
- validation plan
- diff preview
- apply_allowed
- blocking reasons

Apply order:

- create backup
- write layer files
- optionally write registry stub
- sync root mirror
- validate account
- write audit log

Apply requires explicit confirmation. Operation-layer changes require an extra confirmation.

## Backup

Admin apply creates:

```text
backups/admin_config_YYYYMMDD_HHMMSS/
```

Backed files include root watchlist, current account universe files, and symbol registry when registry may be touched.

Manifest:

```text
backup_manifest.json
```

Manifest includes generated time, operation, account, symbol, file list, SHA256 before values, and `user_action_source = admin_ui`.

## Audit

Admin apply writes one JSON line per apply:

```text
runtime/admin_audit.log
```

The event includes timestamp, operation, account, symbol, canonical symbol, source layer, target layer, backup path, validation status, success, and warnings. It does not record account assets, positions, orders, or broker data.

## Validate

`/admin/validate` runs the existing account config check and displays:

- counts
- root mirror match
- registry missing
- duplicate registry entries
- config mismatch / errors
- status

## Root Mirror

Root mirror sync preserves `config/watchlist.yaml -> projects.{account}.layer_universes` as a legacy-compatible mirror of `config/universes/{account}_*.yaml`.

## Security Boundary

- Local only: `127.0.0.1:8766`.
- No remote deployment.
- No database.
- No login system.
- No broker account reading.
- No trading execution.
- No shell command submission.
- No pipeline execution in v0.8.0.
- No output zip bundle in v0.8.0.

## Non-Changes

- Config unchanged by implementation and tests.
- `provider_router.py` unchanged.
- `strict` unchanged.
- `usable_for_operation` unchanged.
- `quote_trust_tier` unchanged.
- Provider runtime semantics unchanged.
- No provider implementation.
- No QMT or iQuant integration.
- No QDII premium.
- No commodity realtime framework.
- No trading advice.

## Tests And Validation

Validation completed on 2026-06-04:

- `pytest`: 393 passed.
- `python -m market_price_guard.admin_app --help`: exit 0.
- admin app import smoke: exit 0.
- uvicorn local smoke for `/admin`: HTTP 200.
- tech account config check: exit 0.
- energy account config check: exit 0.
- tech manager show / validate: exit 0.
- energy manager show / validate: exit 0.
- `git diff -- config`: empty.
- `git diff -- src/market_price_guard/provider_router.py`: empty.
- pipeline script diffs: empty.
- admin UI source/template/handoff keyword scan: no matches.

Validation commands:

```powershell
pytest
python -m market_price_guard.admin_app --help
python -c "from market_price_guard.admin_app import app; print('admin app import ok')"
.\scripts\check_account_layer_config.ps1 -Account tech
.\scripts\check_account_layer_config.ps1 -Account energy
.\scripts\manage_account_layers.ps1 -Account tech show
.\scripts\manage_account_layers.ps1 -Account energy show
.\scripts\manage_account_layers.ps1 -Account tech validate
.\scripts\manage_account_layers.ps1 -Account energy validate
git diff -- src/market_price_guard/provider_router.py
git diff -- config
git diff -- scripts/run_tech_research_pipeline.ps1
git diff -- scripts/run_energy_research_pipeline.ps1
```

Mac equivalent:

```sh
python -m pytest
python -c "from market_price_guard.admin_app import app; print('admin app import ok')"
pwsh ./scripts/check_account_layer_config.ps1 -Account tech
pwsh ./scripts/check_account_layer_config.ps1 -Account energy
pwsh ./scripts/manage_account_layers.ps1 -Account tech show
pwsh ./scripts/manage_account_layers.ps1 -Account energy show
git diff -- src/market_price_guard/provider_router.py
git diff -- config
```

## Known Limitations

- Result pages are plain Jinja templates; no heavy frontend framework.
- Registry editing is limited to optional minimal stub creation.
- Apply failure does not auto-rollback; backup path and partial changes are shown.
- The symbol wizard does not discover provider coverage.
- No pipeline runner or output bundle UI exists in v0.8.0.

## Next Version Plan

v0.8.1 | Pipeline Runner + Output Bundle UI

v0.8.1 should implement:

- run tech pipeline
- run energy pipeline
- run UAT quick / intraday / energy
- build acceptance
- task status
- stdout / stderr tail
- zip bundle
- zip naming: `market_price_guard_{batch_name}_outputs_{YYYYMMDD_HHMMSS}.zip`
- bundle content: pipeline latest, four-layer latest, optional tech observation latest, `zip_manifest.json`, and latest-vs-pipeline manifest consistency checks

Do not implement v0.8.1 content inside v0.8.0.
