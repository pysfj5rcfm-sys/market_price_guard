# HANDOFF v0.7.3.2

Version: `v0.7.3.2 | Config Source Verification + Layer Manifest`

This handoff is based on repository files, current git status, generated outputs, and validation commands from this thread. Do not rely on older chat history.

## 1. Completed Work

- Added config source observability for tech layers.
- Added `layer_manifest.json` generation for main tech outputs.
- Added `pipeline_layer_manifest.json` and `Layer Config Summary` in pipeline summary.
- Added config check command `scripts/check_tech_layer_config.ps1`.
- Added `outputs_config_check_latest/tech_layer_config_check.md`.
- Added `outputs_config_check_latest/tech_layer_config_check.json`.
- Added report sections named `Config Source / Layer Manifest` to upload/debug/completeness/runtime reports.
- Added UAT summary layer manifest fields for items that generate manifests.
- Kept provider behavior, provider priority, YFinance circuit behavior, strict semantics for operation/core, and `usable_for_operation` semantics unchanged.
- Fixed reference-layer strict pollution so candidate/watchlist/scan universes keep `required_for_operation=false` even if a raw provider payload carries operation flags.
- Sanitized generated Markdown report wording so the requested no-advice keyword scan is clean.

## 2. Implementation

Core implementation lives in:

- `src/market_price_guard/config_observability.py`
- `src/market_price_guard/check_tech_layer_config.py`

`market_price_guard.main` now builds a layer manifest after records are normalized and before reports are written. It compares:

- `configured_symbols`: top-level real layer list from config.
- `loaded_symbols`: actual symbols in generated records.

The parser intentionally reads only real top-level list fields:

1. `symbols`
2. `universe`
3. `items`
4. `instruments`
5. `config/watchlist.yaml -> projects.tech.layer_universes.<layer>`

It does not treat `forbidden`, `removed`, `deleted`, `audit`, `notes`, `examples`, `restrictions`, or `changelog` metadata as configured symbols.

## 3. New Files

- `scripts/check_tech_layer_config.ps1`
- `src/market_price_guard/config_observability.py`
- `src/market_price_guard/check_tech_layer_config.py`
- `tests/test_config_observability.py`
- `docs/HANDOFF_v0.7.3.2.md`

## 4. Manifest Fields

Every direct tech layer manifest includes:

- `layer_name`
- `universe_name`
- `universe_type`
- `config_source_path`
- `config_source_exists`
- `config_source_hash_sha256`
- `config_source_mtime`
- `config_loader_name`
- `config_loader_version`
- `configured_symbol_count`
- `loaded_symbol_count`
- `configured_symbols`
- `loaded_symbols`
- `missing_from_loaded`
- `extra_loaded_symbols`
- `duplicate_configured_symbols`
- `duplicate_loaded_symbols`
- `legacy_fallback_used`
- `legacy_fallback_source_path`
- `hardcoded_default_used`
- `hardcoded_default_reason`
- `root_watchlist_layer_mirror_used`
- `root_watchlist_layer_name`
- `config_mismatch`
- `config_load_status`
- `config_load_warnings`

Derived intraday manifest additionally includes:

- `source_layer_manifest_path`

## 5. Check Script Usage

```powershell
.\scripts\check_tech_layer_config.ps1
Get-Content outputs_config_check_latest\tech_layer_config_check.md -Encoding UTF8
Get-Content outputs_config_check_latest\tech_layer_config_check.json -Encoding UTF8
```

The check covers:

- universe counts
- root mirror consistency
- symbol registry coverage
- duplicate symbols
- hard boundary checks
- forbidden/deleted metadata parser-safety warnings

## 6. Current Counts

Historical `config/universes/*.yaml` counts at v0.7.3.2 validation time. These are no longer the current baseline after the user-confirmed v0.7.5.1 config update:

| layer | count |
|---|---:|
| tech_core | 7 |
| tech_operation_candidates | 11 |
| tech_watchlist | 16 |
| tech_scan_ai | 30 |

Historical `config/watchlist.yaml projects.tech.layer_universes` mirror counts at v0.7.3.2 validation time:

| root layer | count |
|---|---:|
| operation | 7 |
| operation_candidate | 11 |
| watchlist | 16 |
| scan | 30 |

Root mirror matches universes for all four layers.

## 7. Current Runtime Results

Latest pipeline run:

```powershell
.\scripts\run_tech_research_pipeline.ps1 -UseRunCache
```

Result:

- exit code: `0`
- `tech_core`: configured 7, loaded 7, mismatch false
- `tech_operation_candidates`: configured 11, loaded 11, mismatch false
- `tech_watchlist`: configured 16, loaded 16, mismatch false
- `tech_scan_ai`: configured 30, loaded 30, mismatch false
- `tech_minute_probe`: configured 15, loaded 15, mismatch false
- `tech_intraday_metrics`: derived from minute probe; configured 15, loaded 18 rows, mismatch false, duplicate loaded symbols are the three core/candidate overlaps.

Generated manifests:

- `outputs_tech_latest/layer_manifest.json`
- `outputs_tech_operation_candidates_latest/layer_manifest.json`
- `outputs_tech_watchlist_latest/layer_manifest.json`
- `outputs_tech_scan_ai_latest/layer_manifest.json`
- `outputs_tech_minute_probe_latest/layer_manifest.json`
- `outputs_tech_intraday_latest/layer_manifest.json`
- `outputs_tech_pipeline_latest/pipeline_layer_manifest.json`

## 8. Validation

Passed:

```powershell
pytest
```

Result: `300 passed`.

Passed:

```powershell
.\scripts\check_tech_layer_config.ps1
.\scripts\run_tech_research_pipeline.ps1 -UseRunCache
.\scripts\run_uat.ps1 -Mode quick -UseRunCache
.\scripts\run_uat.ps1 -Mode intraday -UseRunCache
```

All returned exit code `0`.

No-advice keyword scan over generated pipeline/scan/watchlist/operation-candidate Markdown returned no matches after report wording sanitization.

## 9. Known Issues

- Live provider runtime remains slow. Latest pipeline showed runtime warnings for `tech_scan_ai`, `tech_watchlist`, and `tech_minute_probe`.
- `tech_intraday_metrics` is a derived row-level output. It shows 18 loaded rows because 159819.SZ, 515880.SH, and 159516.SZ appear both as core and operation-candidate source rows. It has no missing/extra config mismatch.
- `git diff -- config` still shows pre-existing user config changes from the target config update. v0.7.3.2 did not auto-modify config.
- `outputs_uat_summary.md` is generated in workspace root and currently untracked.

## 10. Next Version Suggestions

- Optional strict mismatch failure flag for CI, e.g. `--fail-on-config-mismatch`.
- Runtime hardening for slow scan/watchlist/minute live provider paths.
- Cleaner intraday unique-symbol summary while preserving row-level source-universe diagnostics.
- Optional JSON schema docs for `layer_manifest.json`.

## 11. Strictly Out Of Scope

- Do not implement QDII premium.
- Do not implement NDX / QQQ / FX reference framework.
- Do not implement advice layer.
- Do not develop `action_hint`.
- Do not develop `preferred_action`.
- Do not output trading instructions, execution prices, or target prices.
- Do not auto-modify config.
- Do not auto-promote scan/watchlist/candidate symbols.
- Do not change provider priority.
- Do not change YFinance circuit behavior.
- Do not change AKShare / Eastmoney / YFinance main provider flow.
- Do not change `quote_trust_tier` semantics.
- Do not change `strict` semantics for operation/core.
- Do not change `usable_for_operation` semantics.
- Do not add UI.

## 12. Next Thread Should Read First

- `docs/HANDOFF_v0.7.3.2.md`
- `docs/HANDOFF_v0.7.3.1.md`
- `docs/runtime_modes.md`
- `config/watchlist.yaml`
- `config/universes/tech_core.yaml`
- `config/universes/tech_operation_candidates.yaml`
- `config/universes/tech_watchlist.yaml`
- `config/universes/tech_scan_ai.yaml`
- `scripts/check_tech_layer_config.ps1`
- `scripts/run_tech_research_pipeline.ps1`
