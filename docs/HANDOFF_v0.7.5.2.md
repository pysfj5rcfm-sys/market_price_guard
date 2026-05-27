# HANDOFF v0.7.5.2

Version: `v0.7.5.2 | Baseline & Snapshot Consistency Polish`

Scope classification: `account-generic baseline and output snapshot polish`

This version is not tech-only, not energy-only, not provider runtime hardening, not provider coverage polish, not QDII premium, not commodity realtime framework, not trading logic, and not UI.

## Completed

- Unified current account baselines in tests and validation posture.
- Current tech baseline is `operation=7`, `operation_candidate=19`, `watchlist=28`, `scan=40`.
- Current energy baseline is `operation=4`, `operation_candidate=8`, `watchlist=24`, `scan=41`.
- Marked older tech `7 / 11 / 16 / 30` references in historical handoff files as historical, not the current fact source.
- Added pipeline output snapshots for tech and energy research pipelines.
- Added `pipeline_run_id`, `source_run_id`, snapshot paths, generated timestamps, and sha256 hash fields to pipeline summary and manifest output.
- Preserved UAT mode-specific summaries under `outputs_uat_latest/<mode>/`.
- Did not modify config.
- Did not modify provider main routing logic.
- Did not change strict semantics or `usable_for_operation`.

## Current Baselines

Tech:

| layer | count |
|---|---:|
| operation | 7 |
| operation_candidate | 19 |
| watchlist | 28 |
| scan | 40 |

Energy:

| layer | count |
|---|---:|
| operation | 4 |
| operation_candidate | 8 |
| watchlist | 24 |
| scan | 41 |

The older tech baseline `7 / 11 / 16 / 30` is historical only and must not be used as the current fact source.

## Pipeline Snapshot Mechanism

Each pipeline creates a fresh `snapshots/` directory under its pipeline output directory at run start. After each step completes, the pipeline copies that step's audit-relevant outputs into a per-step snapshot directory before later standalone layer scripts can overwrite mutable `outputs_*_latest` directories.

Tech snapshot structure:

```text
outputs_tech_pipeline_latest/snapshots/
  tech_scan_ai/
  tech_watchlist/
  tech_operation_candidates/
  tech_fast_strict/
  tech_minute_probe/
  tech_intraday_metrics/
```

Energy snapshot structure:

```text
outputs_energy_pipeline_latest/snapshots/
  energy_scan/
  energy_watchlist/
  energy_operation_candidates/
  energy_fast_strict/
```

Snapshot files include the available subset of:

- `layer_manifest.json`
- `data_completeness_report.md`
- `runtime_diagnostics.md`
- `provider_health_report.md`
- `0_upload_bundle.md`
- `prices_snapshot.csv`
- `debug_bundle.md`
- relevant layer-specific markdown reports
- `snapshot_metadata.json`

Energy does not include minute probe, intraday metrics, or VWAP.

## New Manifest Fields

`pipeline_summary.md`, `pipeline_manifest.json`, and `pipeline_layer_manifest.json` now record:

- `pipeline_run_id`
- `source_run_id`
- `snapshots_root`
- per-step `snapshot_dir`
- per-step `snapshot_metadata_path`
- per-step `generated_at`
- per-step `layer_manifest_path`
- `layer_manifest_hash_sha256`
- `prices_snapshot_hash_sha256`
- `upload_bundle_hash_sha256`
- `snapshot_steps`

The pipeline layer manifest reads per-step layer manifests from the snapshot copy when available, so later standalone layer runs do not change the pipeline audit package.

## UAT Summary

Mode-specific UAT output remains:

```text
outputs_uat_latest/
  quick/
  intraday/
  energy/
  uat_run_manifest.json
```

The root `outputs_uat_summary.md` remains latest-only. Mode directories remain separately auditable.

## Config And Semantics

- No config files were modified by this version.
- `git diff -- config` should be empty after validation.
- Strict was not relaxed.
- `usable_for_operation` was not changed.
- `quote_trust_tier` semantics were not changed.
- No provider main routing logic was changed.
- No trading logic was implemented.
- No automatic symbol promotion was implemented.

## Validation Commands

```powershell
pytest
.\scripts\check_account_layer_config.ps1 -Account tech
.\scripts\check_account_layer_config.ps1 -Account energy
.\scripts\check_tech_layer_config.ps1
.\scripts\manage_account_layers.ps1 -Account tech show
.\scripts\manage_tech_layers.ps1 show
.\scripts\manage_tech_layers.ps1 validate
.\scripts\manage_tech_layers.ps1 export
.\scripts\manage_account_layers.ps1 -Account energy show
.\scripts\manage_account_layers.ps1 -Account energy validate
.\scripts\manage_account_layers.ps1 -Account energy export
.\scripts\run_tech_research_pipeline.ps1 -UseRunCache
Get-Content outputs_tech_pipeline_latest\pipeline_summary.md -Encoding UTF8
Get-Content outputs_tech_pipeline_latest\pipeline_layer_manifest.json -Encoding UTF8
Get-ChildItem -Recurse outputs_tech_pipeline_latest\snapshots | Select-Object FullName
.\scripts\run_energy_research_pipeline.ps1
Get-Content outputs_energy_pipeline_latest\pipeline_summary.md -Encoding UTF8
Get-Content outputs_energy_pipeline_latest\pipeline_layer_manifest.json -Encoding UTF8
Get-ChildItem -Recurse outputs_energy_pipeline_latest\snapshots | Select-Object FullName
.\scripts\run_uat.ps1 -Mode quick -UseRunCache
.\scripts\run_uat.ps1 -Mode intraday -UseRunCache
.\scripts\run_uat.ps1 -Mode energy -UseRunCache
Get-ChildItem -Recurse outputs_uat_latest | Select-Object FullName
git diff -- config
```

## Strict Prohibitions To Preserve

- Do not mix tech and energy symbols or rules.
- Do not let `-Account energy` fallback to tech.
- Do not relax strict.
- Do not mark mock, stale, development, or provider-missing quotes as operation-usable.
- Do not implement execution action fields.
- Do not implement QDII premium inside this version.
- Do not implement commodity realtime framework inside this version.
- Do not add energy minute probe, intraday metrics, or VWAP.
- Do not modify positions, costs, cash, gold amount, or controller total assets.
- Do not promote symbols automatically across layers.
- Do not treat provider failure as an investment signal.

## Suggested Next Versions

- `v0.7.5.3 | Provider Coverage Follow-up`
- `v0.7.6 | QDII Premium Framework`
- `v0.7.6 | Energy Commodity Reference Framework`

These are suggestions only and are not implemented in v0.7.5.2.

## Next Thread Must Read

- `docs/ACCOUNT_ARCHITECTURE.md`
- `docs/HANDOFF_v0.7.5.2.md`
- `docs/HANDOFF_v0.7.5.1.md`
- `scripts/run_tech_research_pipeline.ps1`
- `scripts/run_energy_research_pipeline.ps1`
- `scripts/run_uat.ps1`
- `outputs_tech_pipeline_latest/pipeline_summary.md`
- `outputs_energy_pipeline_latest/pipeline_summary.md`
- provider / quote / runtime / report / UAT related modules
