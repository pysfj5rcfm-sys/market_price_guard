from __future__ import annotations

import pandas as pd

from market_price_guard.main import run_pipeline


def test_markdown_report_reads_as_utf8(tmp_path):
    output_dir = tmp_path / "outputs_mock"

    run_pipeline(output_dir=output_dir, provider_mode="mock")
    report = (output_dir / "data_completeness_report.md").read_text(encoding="utf-8")

    assert "数据完整度报告" in report
    assert "不输出买卖建议" in report
    health_report = (output_dir / "provider_health_report.md").read_text(encoding="utf-8")
    assert "行情源健康报告" in health_report


def test_prices_snapshot_reads_as_utf8_sig_with_chinese(tmp_path):
    output_dir = tmp_path / "outputs_mock"

    run_pipeline(output_dir=output_dir, provider_mode="mock")
    df = pd.read_csv(output_dir / "prices_snapshot.csv", encoding="utf-8-sig")

    assert "name" in df.columns
    assert "中海油H" in set(df["name"])
