# HANDOFF v0.8.1.2

## Scope

- version: v0.8.1.2
- scope classification: admin task run frontend/runtime polish + UI alignment polish
- This round is limited to Admin Run and Admin UI alignment.
- No config universe edit was made in this round.
- No provider router edit was made in this round.
- No pipeline main script edit was made in this round.
- No provider integration was introduced.
- No trading logic was changed.

## Existing Config State

- A pre-existing uncommitted `config/watchlist.yaml` diff was present at the start of this round.
- Per round scope, this round did not continue config/root mirror/core loader work.
- Current baseline remains sourced from `config/universes/*.yaml`, not hard-coded prompt text.

## Run Root Cause

- Admin runner only resolved `pwsh`.
- On Windows hosts with Windows PowerShell but without `pwsh`, Run could fail before invoking the task script.
- The tech pipeline command also always included `-UseRunCache`, even when the UI checkbox was absent.
- POST `/admin/tasks/run` returned an intermediate result page instead of landing on the durable task detail URL.

## Run Fix

- POST `/admin/tasks/run` now parses form fields and redirects to `/admin/tasks/{task_id}` with HTTP 303.
- Unknown `task_name` values remain rejected by the fixed whitelist.
- `use_run_cache` missing value now maps to `False`; checked value maps to `True`.
- `tech_pipeline` and UAT task commands only receive `-UseRunCache` when requested.
- The runner still uses `shell=False` and fixed command mappings.
- Failed task scripts still produce task records and logs; UI detail renders failure state instead of a 500.

## PowerShell Resolver

- Windows lookup order: `pwsh`, `powershell.exe`, `powershell`.
- non-Windows lookup order: `pwsh`.
- Missing executable produces a failed task record with a clear message.
- Runner environment now also includes `.venv/Scripts` on PATH when present.

## UI Alignment

- Static HTML/CSS audit only; browser server launch was blocked by a Windows `Path`/`PATH` environment duplication issue in `Start-Process`.
- `/admin/tasks`, `/admin/tasks/{task_id}`, and `/admin/bundles` templates were checked and polished.
- Task cards use consistent control height and full-width Run buttons.
- Status values render as `status-pill`.
- Table action cells use stable nowrap button layout.
- Stdout/stderr/command blocks use `log-box` with bounded scroll behavior.
- Back and bundle actions now share toolbar/button styling.

## Validation

- Admin route/task tests:
  - `pytest -q tests/test_admin_routes.py tests/test_admin_task_runner.py tests/test_admin_no_command_injection.py`
  - Output showed `21 passed`.
  - The shell returned 137 after pytest completion in this environment; no pytest assertion failed.
- Wider bundle test attempt:
  - `pytest -q tests/test_admin_routes.py tests/test_admin_task_runner.py tests/test_admin_no_command_injection.py tests/test_bundles.py`
  - Admin tests passed, but `tests/test_bundles.py::test_tech_reference_upload_bundle_is_reference_only` failed on an existing report text assertion outside this round's Admin scope.
- `config_check_tech` script was verified separately before this round and remained outside this round's edits.

## Manual Checks

- ASGI route tests verified:
  - GET `/admin/tasks` returns 200.
  - POST `/admin/tasks/run` redirects to task detail for `config_check_tech`.
  - unknown task names are rejected.
  - missing `use_run_cache` does not cause 422/500.
  - checked `use_run_cache` reaches task options.
  - failed task detail displays status, stdout tail, stderr tail, exit code, cwd, and command.
  - missing task detail returns a friendly 404 page.
  - bundle download rejects path traversal.

## Known Limitations

- Browser screenshot verification was not completed because local dashboard launch via `Start-Process` hit the Windows environment duplication issue noted above.
- Full project pytest was not run in this round.
- The unrelated bundle assertion should be handled separately if v0.8.1.2 acceptance requires the full suite.

## Next Version Options

- v0.8.2 Admin UX polish follow-up.
- v0.8.2 task runner background queue/refresh polish.
- v0.8.2 bundle page usability polish.
