# Runtime Modes

v0.7.3 introduces runtime and coverage modes for the technology research path. These modes only control provider probing breadth and reporting. They do not change strict, freshness, quote trust tier, usable_for_operation, or operation/reference semantics.

## Scan AI Modes

`run_tech_scan_ai.ps1` supports:

```powershell
.\scripts\run_tech_scan_ai.ps1
.\scripts\run_tech_scan_ai.ps1 -Mode fast
.\scripts\run_tech_scan_ai.ps1 -Mode diagnostic
```

Default mode is `fast`.

`fast` keeps ETF / QDII ETF coverage on AKShare ETF batch where available. For A-share scan stocks, it uses Eastmoney Direct spot quote first and skips slow AKShare stock exhaustive fallback. Eastmoney stock quotes remain reference-only and do not become operation-grade.

`diagnostic` is for provider coverage troubleshooting. It may keep broader fallback attempts and can run slower.

## Minute Probe Modes

`run_tech_minute_probe.ps1` supports:

```powershell
.\scripts\run_tech_minute_probe.ps1
.\scripts\run_tech_minute_probe.ps1 -Mode fast
.\scripts\run_tech_minute_probe.ps1 -Mode balanced
.\scripts\run_tech_minute_probe.ps1 -Mode diagnostic
.\scripts\run_tech_minute_probe.ps1 -Mode balanced -MinuteWorkers 3
```

Default mode is `balanced`.

- `fast`: AKShare first; fallback is skipped by default when AKShare fails.
- `balanced`: AKShare first; skips Eastmoney minute fallback; tries YFinance reference fallback.
- `diagnostic`: AKShare, then Eastmoney Direct, then YFinance for full troubleshooting.

`MinuteWorkers` is parsed and reported. The current implementation remains serial and reports `parallel_enabled=false` until a later version safely enables concurrent provider calls.

## Pipeline Defaults

`run_tech_research_pipeline.ps1` defaults to:

```powershell
.\scripts\run_tech_research_pipeline.ps1 -ScanMode fast -MinuteMode balanced -MinuteWorkers 3
```

You can switch to diagnostic coverage:

```powershell
.\scripts\run_tech_research_pipeline.ps1 -UseRunCache -ScanMode diagnostic -MinuteMode diagnostic
```

The pipeline does not modify config, promote symbols, alter provider semantics, or generate trading advice.

## Safety

Runtime modes are coverage and diagnostics controls only. They do not implement QDII premium, NDX / QQQ / FX references, action hints, preferred actions, or an advice layer.
