# HANDOFF v0.7.5.3

Version: `v0.7.5.3 | Runtime/UAT Tail Cleanup + Acceptance Polish`

Scope classification: `account-generic runtime/UAT acceptance polish`

This version is not tech-only, not energy-only, not provider coverage polish, not provider expansion, not QDII premium, not commodity realtime framework, not trading logic, and not UI.

## Completed

- Added mode-specific UAT runtime policy in `scripts/run_uat.ps1`.
- Added UAT hard timeout wrapping per step so intraday is not limited by the old fixed 300s external expectation.
- UAT summaries now record `timeout_seconds`, `soft_budget_seconds`, `hard_timeout_seconds`, `elapsed_seconds`, `timed_out`, `runtime_budget_warning`, `failed`, and `strict_blocked_but_reported`.
- Added runtime warning levels to tech and energy pipeline summaries and manifests.
- Added `scripts/build_acceptance_summary.ps1`.
- Added `outputs_acceptance_latest/acceptance_summary.md` and `outputs_acceptance_latest/acceptance_summary.json` generation.
- Kept pipeline snapshot mechanism unchanged.
- Kept UAT mode-specific summary directories unchanged.
- Added tests for runtime warning classification, UAT timeout/budget fields, and acceptance summary contract.

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

The old tech `7 / 11 / 16 / 30` baseline is historical only and must not be used as a current assertion.

## UAT Timeout / Budget Policy

`run_uat.ps1` now owns explicit mode policy:

| mode | timeout_seconds | soft_budget_seconds | hard_timeout_seconds |
|---|---:|---:|---:|
| quick | 360 | 120 | 360 |
| intraday | 900 | 420 | 900 |
| full | 1200 | 900 | 1200 |
| energy | 900 | 420 | 900 |

Soft budget excess is reported as `soft_budget_exceeded` and does not imply failure. A true step timeout is reported as `hard_timeout` and fails UAT. `strict_blocked_but_reported` remains separate from failure when reports exist.

## Runtime Warning Levels

Pipeline and UAT reporting use these levels:

- `runtime_info`
- `runtime_warning`
- `soft_budget_exceeded`
- `hard_timeout`
- `provider_timeout`
- `provider_circuit_open`
- `strict_blocked_but_reported`
- `failed`

Runtime warnings can exist while `failed=0`. `strict_blocked_but_reported` is an acceptance status, not a failed command.

## Acceptance Summary

`scripts/build_acceptance_summary.ps1` creates:

```text
outputs_acceptance_latest/
  acceptance_summary.md
  acceptance_summary.json
```

It summarizes:

- version and scope classification
- tech baseline `7 / 19 / 28 / 40`
- energy baseline `4 / 8 / 24 / 41`
- tech and energy pipeline status, failed count, strict blocked count, runtime warnings, snapshot path, and pipeline summary path
- quick / intraday / energy UAT summary paths and per-mode status
- config diff status
- no-advice scan result
- unresolved backlog

The acceptance script does not rerun heavy pipeline or UAT tasks. It summarizes existing outputs after validation commands.

## Snapshot Contract

Preserved from v0.7.5.2:

- `outputs_tech_pipeline_latest/snapshots/`
- `outputs_energy_pipeline_latest/snapshots/`
- `pipeline_summary.md` records snapshot paths.
- `pipeline_layer_manifest.json` records snapshot paths.
- snapshot metadata includes generated timestamp, source run id, and hashes.
- standalone layer reruns do not rewrite the pipeline snapshot package.

## UAT Summary Contract

Preserved:

```text
outputs_uat_latest/
  quick/
  intraday/
  energy/
  uat_run_manifest.json
```

Each mode keeps its own `outputs_uat_summary.md` and `outputs_uat_summary.json`.

## Config And Semantics

- Config files were not modified in this version.
- `strict` semantics were not changed.
- `usable_for_operation` semantics were not changed.
- `quote_trust_tier` semantics were not changed.
- Provider main routing logic was not changed.
- Trading logic was not implemented.
- QDII premium was not implemented.
- Commodity realtime framework was not implemented.

## Validation Commands

```powershell
pytest
.\scripts\check_account_layer_config.ps1 -Account tech
.\scripts\check_account_layer_config.ps1 -Account energy
.\scripts\manage_account_layers.ps1 -Account tech show
.\scripts\manage_account_layers.ps1 -Account energy show
.\scripts\run_tech_research_pipeline.ps1 -UseRunCache
.\scripts\run_energy_research_pipeline.ps1
.\scripts\run_uat.ps1 -Mode quick -UseRunCache
.\scripts\run_uat.ps1 -Mode intraday -UseRunCache
.\scripts\run_uat.ps1 -Mode energy -UseRunCache
.\scripts\build_acceptance_summary.ps1
git diff -- config
```

## Strict Prohibitions

- Do not mix tech and energy symbols or rules.
- Do not let `-Account energy` fallback to tech.
- Do not relax strict.
- Do not change `usable_for_operation`.
- Do not change `quote_trust_tier` semantics.
- Do not add provider expansion in this version line.
- Do not implement QDII premium inside v0.7.5.3.
- Do not implement commodity realtime framework inside v0.7.5.3.
- Do not add energy minute probe, intraday metrics, or VWAP.
- Do not modify positions, costs, cash, gold amount, or controller total assets.
- Do not promote symbols automatically across layers.
- Do not treat provider failure as an investment signal.

## Remaining Issues

- `tech_scan_ai` and `tech_minute_probe` may exceed soft runtime budget.
- Energy operation provider coverage is still weak.
- QDII premium is not implemented.
- Energy commodity reference is not implemented.

## Suggested Next Versions

- `v0.7.6 | QDII Premium Framework`
- `v0.7.6 | Energy Commodity Reference Framework`

Do not treat either suggestion as implemented in v0.7.5.3.

## Next Thread Must Read

- `docs/ACCOUNT_ARCHITECTURE.md`
- `docs/HANDOFF_v0.7.5.3.md`
- `docs/HANDOFF_v0.7.5.2.md`
- `scripts/run_tech_research_pipeline.ps1`
- `scripts/run_energy_research_pipeline.ps1`
- `scripts/run_uat.ps1`
- `scripts/build_acceptance_summary.ps1`
- `outputs_acceptance_latest/acceptance_summary.md`
- `outputs_tech_pipeline_latest/pipeline_summary.md`
- `outputs_energy_pipeline_latest/pipeline_summary.md`
