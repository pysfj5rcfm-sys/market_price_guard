# HANDOFF v0.8.1

Version: v0.8.1 | Pipeline Runner + Output Bundle UI

Scope classification: local FastAPI admin pipeline runner and output bundle UI.

## Completed

- Created a local admin pipeline runner UI for fixed task names only.
- Created output bundle UI with per-batch zip creation and guarded retrieval.
- Created task service, task record model, summary preview reader, and bundle service.
- Created task JSON records plus stdout/stderr log files under `runtime/admin_tasks/`.
- Created a task lock at `runtime/admin_task.lock`.
- Created bundle zips under `dist/output_bundles/`.
- Created route and service tests for the v0.8.1 scope.
- Updated `check_account_layer_config.ps1` and `manage_account_layers.ps1` Python discovery for Mac/Windows local validation.

## Current Baselines

Requested current tech baseline:

| layer | count |
|---|---:|
| operation | 7 |
| operation_candidate | 19 |
| watchlist | 28 |
| scan | 40 |

Requested current energy baseline:

| layer | count |
|---|---:|
| operation | 4 |
| operation_candidate | 8 |
| watchlist | 24 |
| scan | 41 |

Validation caveat: this checkout currently reads tech as 8 / 19 / 28 / 40 because `config/universes/tech_core.yaml` contains `159995.SZ` in `symbols`. `git diff -- config` is empty, so v0.8.1 did not modify config.

## Task Whitelist

- `tech_pipeline`
- `energy_pipeline`
- `both_pipelines`
- `uat_quick`
- `uat_intraday`
- `uat_energy`
- `acceptance`
- `config_check_tech`
- `config_check_energy`
- `config_check_both`

There is no free-form shell entry.

## Task Runner

Implementation files:

- `src/market_price_guard/admin_task_models.py`
- `src/market_price_guard/admin_task_runner.py`
- `src/market_price_guard/admin_summary_reader.py`

Each task maps to a fixed PowerShell command list and runs with `shell=False`. Mac/Linux also use `pwsh` for `.ps1` scripts. If `pwsh` is not found, the task record fails with:

```text
PowerShell executable not found. Please install pwsh.
```

`both_pipelines` runs tech first, then energy. Default behavior stops after a failing first command unless the UI form requests continue after failure.

## Task Lock

The task lock path is:

```text
runtime/admin_task.lock
```

Only one task can run at a time. A live lock rejects a new task and writes that lock behavior into the task record. Stale lock files are cleared only when their process is not live or the age exceeds the stale limit.

## Task Records

Each run writes:

```text
runtime/admin_tasks/{task_id}.json
runtime/admin_tasks/{task_id}.stdout.log
runtime/admin_tasks/{task_id}.stderr.log
```

Task JSON includes task id, task name, batch name, command, cwd, start/finish time, elapsed seconds, exit code, status, summary paths, output paths, bundle eligibility, warnings, and `no_trading_advice = true`.

The UI shows the last 200 stdout/stderr lines.

## UI Routes

- `GET /admin/tasks`
- `POST /admin/tasks/run`
- `GET /admin/tasks/{task_id}`
- `GET /admin/bundles`
- `POST /admin/bundles/build`
- `GET /admin/bundles/download/{bundle_name}`

Existing v0.8.0 routes remain in place.

## Summary Preview

Task detail pages show summary path links, parsed metrics where JSON is available, first lines of markdown summaries, and pipeline snapshot path presence.

Preview sources:

- tech pipeline: `outputs_tech_pipeline_latest/pipeline_summary.md`
- energy pipeline: `outputs_energy_pipeline_latest/pipeline_summary.md`
- UAT: `outputs_uat_latest/{mode}/outputs_uat_summary.md/json`
- acceptance: `outputs_acceptance_latest/acceptance_summary.md/json`
- config checks: `outputs_config_check_latest/*_layer_config_check.md/json`

## Bundle Naming

Bundle zips use:

```text
market_price_guard_{batch_name}_outputs_{YYYYMMDD_HHMMSS}.zip
```

Bundle directory:

```text
dist/output_bundles/
```

## Bundle Scope

`tech_pipeline` includes:

- `outputs_tech_pipeline_latest/`
- matching `outputs_tech_scan_ai_latest/`
- matching `outputs_tech_watchlist_latest/`
- matching `outputs_tech_operation_candidates_latest/`
- matching `outputs_tech_latest/`
- optional matching `outputs_tech_minute_probe_latest/`
- optional matching `outputs_tech_intraday_metrics_latest/` or `outputs_tech_intraday_latest/`

`energy_pipeline` includes:

- `outputs_energy_pipeline_latest/`
- matching `outputs_energy_scan_latest/`
- matching `outputs_energy_watchlist_latest/`
- matching `outputs_energy_operation_candidates_latest/`
- matching `outputs_energy_latest/`

Energy bundles do not include minute, intraday, or VWAP outputs.

UAT bundles include:

- `outputs_uat_latest/quick/`
- `outputs_uat_latest/intraday/`
- `outputs_uat_latest/energy/`
- `outputs_uat_latest/uat_run_manifest.json` when present

Acceptance bundle includes:

- `outputs_acceptance_latest/`

Config check bundles include:

- `outputs_config_check_latest/`

## Pipeline Consistency Check

Pipeline bundles read:

```text
outputs_{account}_pipeline_latest/pipeline_layer_manifest.json
```

The bundle service compares each latest layer directory `layer_manifest.json` SHA256 with the recorded pipeline snapshot hash. Matching latest paths are included with `latest_match_pipeline = true`.

If a latest path is missing, mismatched, or has insufficient metadata, it is skipped. The manifest records the reason and an authoritative fallback path under `outputs_{account}_pipeline_latest/snapshots/{step}/`.

## Zip Manifest

Every zip root contains:

```text
zip_manifest.json
```

Manifest fields include:

- bundle type
- batch name
- generated time
- zip name
- project root
- git commit if available
- task id and task name when provided
- command
- included paths
- skipped paths
- missing optional paths
- excluded paths
- warnings
- SHA256 values for key summary files
- pipeline run id when applicable
- pipeline summary path when applicable
- pipeline layer manifest path when applicable
- `no_trading_advice = true`

Excluded path policy includes `.git/`, `.venv/`, `backups/`, `runtime/`, `**/__pycache__/`, `.pytest_cache/`, and other zips under `dist/output_bundles/`.

## Retrieval Safety

`/admin/bundles/download/{bundle_name}` accepts only a plain zip filename under `dist/output_bundles/`. Names with traversal segments or path separators are rejected.

## Dependencies

`pyproject.toml` already includes:

- `fastapi`
- `uvicorn`
- `jinja2`
- `python-multipart`

No React, Vue, Next.js, Celery, Redis, or database dependency was introduced.

## Security Boundary

- Local admin only.
- Default host remains `127.0.0.1`.
- No `0.0.0.0` default.
- No database.
- No login system.
- No remote service.
- No broker account access.
- No order placement.
- No free-form shell entry.
- Pipeline runs are data/report generation only.
- No trading advice is generated.

## Non-Changes

- Config unchanged by v0.8.1 implementation.
- `provider_router.py` unchanged.
- Strict semantics unchanged.
- `usable_for_operation` unchanged.
- `quote_trust_tier` unchanged.
- Provider runtime semantics unchanged.
- No provider implementation.
- No QMT or iQuant integration.
- No QDII premium.
- No commodity realtime framework.

## Tests And Validation

Completed locally:

```text
.venv/bin/python -X pycache_prefix=/private/tmp/market_price_guard_pycache -m pytest tests/test_admin_task_runner.py tests/test_admin_no_command_injection.py tests/test_admin_bundle_service.py tests/test_admin_pipeline_bundle_manifest.py tests/test_admin_routes.py tests/test_admin_no_pipeline_impact.py
```

Result:

```text
20 passed, 1 skipped
```

The skipped module is the route test module because this local `.venv` lacks FastAPI/Uvicorn/Jinja2, while `pyproject.toml` declares them.

Service import smoke:

```text
admin task and bundle services import ok
```

Full pytest result in this checkout:

```text
391 passed, 14 failed, 1 skipped
```

The failures are not from v0.8.1 service tests. They are caused by:

- checked-in tech config currently reading 8 / 19 / 28 / 40 rather than the requested 7 / 19 / 28 / 40;
- old feasibility tests calling `powershell`, while this Mac has `pwsh` but not `powershell`;
- local `.venv` missing declared admin runtime dependencies.

Real validation commands completed:

```text
pwsh ./scripts/check_account_layer_config.ps1 -Account tech
pwsh ./scripts/check_account_layer_config.ps1 -Account energy
pwsh ./scripts/manage_account_layers.ps1 -Account tech show
pwsh ./scripts/manage_account_layers.ps1 -Account energy show
pwsh ./scripts/run_tech_research_pipeline.ps1 -UseRunCache
pwsh ./scripts/run_energy_research_pipeline.ps1
pwsh ./scripts/run_uat.ps1 -Mode quick -UseRunCache
pwsh ./scripts/build_acceptance_summary.ps1
python -m market_price_guard.admin_bundle_service --batch tech_pipeline
python -m market_price_guard.admin_bundle_service --batch energy_pipeline
python -m market_price_guard.admin_bundle_service --batch uat_quick
python -m market_price_guard.admin_bundle_service --batch acceptance
```

Results:

- tech config check: exit 0.
- energy config check: exit 0.
- tech account show: exit 0 and reports 8 / 19 / 28 / 40 in this checkout.
- energy account show: exit 0 and reports 4 / 8 / 24 / 41.
- tech pipeline: exit 0; generated `outputs_tech_pipeline_latest/pipeline_summary.md`; strict-blocked step was reported in pipeline outputs.
- energy pipeline: exit 0; generated `outputs_energy_pipeline_latest/pipeline_summary.md`; strict-blocked step was reported in pipeline outputs.
- UAT quick: exit 1; generated `outputs_uat_latest/quick/outputs_uat_summary.md`.
- acceptance summary: exit 0; generated `outputs_acceptance_latest/acceptance_summary.md/json`.
- generated bundles: acceptance, tech pipeline, energy pipeline, and UAT quick.

Commands attempted:

```text
env PYTHONPATH=src .venv/bin/python -X pycache_prefix=/private/tmp/market_price_guard_pycache -c "from market_price_guard.admin_app import app; print('admin app import ok')"
env PYTHONPATH=src .venv/bin/python -X pycache_prefix=/private/tmp/market_price_guard_pycache -c "import fastapi, uvicorn, jinja2; print('admin deps ok')"
```

Both failed in this local `.venv` because FastAPI/Uvicorn are not installed.

`git diff -- config` is empty.
`git diff -- src/market_price_guard/provider_router.py` is empty.
`git diff -- scripts/run_tech_research_pipeline.ps1 scripts/run_energy_research_pipeline.ps1` is empty.
No-advice scan over new admin source, templates, and this handoff returned no matches.

## Known Limitations

- Route tests need the declared admin deps installed in `.venv`.
- The checked-in tech operation count conflicts with the requested v0.8.1 baseline.
- Existing feasibility tests should use `pwsh` on Mac/Linux or provide a `powershell` alias.
- UAT quick still exits 1 because underlying strict/runtime checks report blocking conditions.

## Next Version Plan

Option A: v0.8.2 | Admin UX Polish + Registry Editor Lite

Option B: v0.8.2 | Guosen iQuant Internal Bridge Probe

Option C: v0.8.2 | QMT / miniQMT / xtquant Discovery Spike

Option D: v0.8.2 | QDII Premium Framework
