from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from market_price_guard.models import PriceRecord
from market_price_guard.providers.akshare_provider import AkshareProvider
from market_price_guard.report import build_completeness_report, build_provider_health_report, get_blocking_records


def make_ak(a_df=None, hk_df=None, etf_df=None):
    return SimpleNamespace(
        stock_zh_a_spot_em=lambda: a_df if a_df is not None else pd.DataFrame(),
        stock_sh_a_spot_em=lambda: a_df if a_df is not None else pd.DataFrame(),
        stock_sz_a_spot_em=lambda: a_df if a_df is not None else pd.DataFrame(),
        stock_hk_spot_em=lambda: hk_df if hk_df is not None else pd.DataFrame(),
        stock_hk_main_board_spot_em=lambda: hk_df if hk_df is not None else pd.DataFrame(),
        stock_hsgt_sh_hk_spot_em=lambda: hk_df if hk_df is not None else pd.DataFrame(),
        fund_etf_spot_em=lambda: etf_df if etf_df is not None else pd.DataFrame(),
    )


def test_akshare_provider_handles_a_share_dataframe():
    df = pd.DataFrame(
        [
            {"代码": "601899", "名称": "紫金矿业", "最新价": 18.42},
            {"代码": "601985", "名称": "中国核电", "最新价": 10.91},
            {"代码": "003816", "名称": "中国广核", "最新价": 4.27},
        ]
    )

    prices = AkshareProvider(make_ak(a_df=df)).fetch(["601899.SH", "601985.SH", "003816.SZ"])

    assert prices["601899.SH"].price == 18.42
    assert prices["601985.SH"].price == 10.91
    assert prices["003816.SZ"].price == 4.27
    assert prices["601899.SH"].source == "akshare"
    assert prices["601899.SH"].currency == "CNY"
    assert "quote_time_missing" in prices["601899.SH"].quality_issues


def test_akshare_provider_handles_hk_dataframe():
    df = pd.DataFrame([{"代码": "00883", "名称": "中海油H", "最新价": 21.35}])

    prices = AkshareProvider(make_ak(hk_df=df)).fetch(["00883.HK"])

    assert prices["00883.HK"].price == 21.35
    assert prices["00883.HK"].currency == "HKD"
    assert prices["00883.HK"].source == "akshare"


def test_akshare_provider_matches_hk_code_without_leading_zeroes():
    df = pd.DataFrame([{"代码": "883", "名称": "中海油H", "最新价": 21.35}])

    prices = AkshareProvider(make_ak(hk_df=df)).fetch(["00883.HK"])

    assert prices["00883.HK"].price == 21.35


def test_akshare_provider_handles_etf_dataframe():
    df = _etf_df()

    prices = AkshareProvider(make_ak(etf_df=df)).fetch(["159632.SZ", "513300.SH", "159819.SZ", "515880.SH", "510300.SH"])

    assert prices["159632.SZ"].price == 1.432
    assert prices["513300.SH"].price == 1.671
    assert prices["159819.SZ"].price == 0.921
    assert prices["515880.SH"].price == 1.084
    assert prices["510300.SH"].price == 3.921
    assert prices["510300.SH"].currency == "CNY"


def test_etf_update_time_with_timezone_sets_quote_time():
    df = pd.DataFrame([{"代码": "159819", "名称": "人工智能ETF", "最新价": 0.921, "更新时间": "2024-12-26 16:11:57+08:00"}])

    price = AkshareProvider(make_ak(etf_df=df)).fetch(["159819.SZ"])["159819.SZ"]

    assert price.quote_time is not None
    assert price.quote_time.isoformat() == "2024-12-26T16:11:57+08:00"
    assert "quote_time_missing" not in price.quality_issues
    assert price.provider_diagnostics["quote_time_raw"] == "2024-12-26 16:11:57+08:00"
    assert price.provider_diagnostics["quote_time_utc"] == "2024-12-26T08:11:57+00:00"


def test_sh_etf_after_close_quote_time_sets_closed_market_status():
    df = pd.DataFrame([{"代码": "513300", "名称": "纳指ETF", "最新价": 1.671, "更新时间": "2026-05-18 15:34:03+08:00"}])

    price = AkshareProvider(make_ak(etf_df=df)).fetch(["513300.SH"])["513300.SH"]

    assert price.market_status == "closed"
    assert price.market_status != "open"


def test_sz_etf_after_close_quote_time_sets_closed_market_status():
    df = pd.DataFrame([{"代码": "159819", "名称": "人工智能ETF", "最新价": 0.921, "更新时间": "2026-05-18 15:34:21+08:00"}])

    price = AkshareProvider(make_ak(etf_df=df)).fetch(["159819.SZ"])["159819.SZ"]

    assert price.market_status == "closed"
    assert price.market_status != "open"


def test_a_share_trading_quote_time_sets_open_market_status():
    df = pd.DataFrame([{"代码": "601899", "名称": "紫金矿业", "最新价": 18.42, "更新时间": "2026-05-18 10:00:00+08:00"}])

    price = AkshareProvider(make_ak(a_df=df)).fetch(["601899.SH"])["601899.SH"]

    assert price.market_status == "open"


def test_etf_update_time_without_timezone_assumes_shanghai():
    df = pd.DataFrame([{"代码": "159819", "名称": "人工智能ETF", "最新价": 0.921, "更新时间": "2024-12-26 16:11:57"}])

    price = AkshareProvider(make_ak(etf_df=df)).fetch(["159819.SZ"])["159819.SZ"]

    assert price.quote_time is not None
    assert price.quote_time.isoformat() == "2024-12-26T16:11:57+08:00"
    assert "assumed_timezone_asia_shanghai" in price.quality_issues
    assert "quote_time_missing" not in price.quality_issues
    assert price.market_status == "closed"


def test_etf_date_only_marks_low_precision_quote_time():
    df = pd.DataFrame([{"代码": "159819", "名称": "人工智能ETF", "最新价": 0.921, "数据日期": "2024-12-26"}])

    price = AkshareProvider(make_ak(etf_df=df)).fetch(["159819.SZ"])["159819.SZ"]

    assert price.quote_time is not None
    assert "quote_time_date_only" in price.quality_issues
    assert "low_precision_quote_time" in price.quality_issues
    assert "quote_time_missing" not in price.quality_issues


def test_etf_without_time_fields_marks_quote_time_missing():
    df = pd.DataFrame([{"代码": "159819", "名称": "人工智能ETF", "最新价": 0.921}])

    price = AkshareProvider(make_ak(etf_df=df)).fetch(["159819.SZ"])["159819.SZ"]

    assert price.quote_time is None
    assert "quote_time_missing" in price.quality_issues


def test_akshare_provider_reports_symbol_not_found():
    prices = AkshareProvider(make_ak(a_df=pd.DataFrame([{"代码": "000001", "名称": "其他", "最新价": 1.0}]))).fetch(["601899.SH"])

    assert prices["601899.SH"].price is None
    assert "symbol_not_found" in prices["601899.SH"].quality_issues


def test_akshare_provider_reports_invalid_price():
    df = pd.DataFrame([{"代码": "601899", "名称": "紫金矿业", "最新价": 0}])

    prices = AkshareProvider(make_ak(a_df=df)).fetch(["601899.SH"])

    assert prices["601899.SH"].price is None
    assert "invalid_price" in prices["601899.SH"].quality_issues


def test_akshare_provider_reports_provider_error_with_diagnostics():
    ak = SimpleNamespace(
        stock_zh_a_spot_em=lambda: (_ for _ in ()).throw(ConnectionError("remote disconnected")),
        stock_sh_a_spot_em=lambda: (_ for _ in ()).throw(ConnectionError("sh fallback down")),
        stock_sz_a_spot_em=lambda: pd.DataFrame(),
        stock_hk_spot_em=lambda: pd.DataFrame(),
        stock_hk_main_board_spot_em=lambda: pd.DataFrame(),
        stock_hsgt_sh_hk_spot_em=lambda: pd.DataFrame(),
        fund_etf_spot_em=lambda: pd.DataFrame(),
    )

    prices = AkshareProvider(ak).fetch(["601899.SH"])
    diagnostic = prices["601899.SH"].provider_diagnostics

    assert prices["601899.SH"].price is None
    assert "provider_error" in prices["601899.SH"].quality_issues
    assert diagnostic["function_name"] == "stock_sh_a_spot_em"
    assert diagnostic["exception_type"] == "ConnectionError"
    assert "sh fallback down" in diagnostic["exception_message"]
    assert diagnostic["category"] == "A_SHARE"
    assert diagnostic["provider_status"] == "fallback_failed"
    assert {attempt["function_name"] for attempt in diagnostic["attempts"]} == {
        "stock_zh_a_spot_em",
        "stock_sh_a_spot_em",
    }


def test_partial_success_keeps_etf_success_when_a_share_and_hk_fail():
    ak = SimpleNamespace(
        stock_zh_a_spot_em=lambda: (_ for _ in ()).throw(ConnectionError("a share down")),
        stock_sh_a_spot_em=lambda: (_ for _ in ()).throw(ConnectionError("sh fallback down")),
        stock_sz_a_spot_em=lambda: (_ for _ in ()).throw(ConnectionError("sz fallback down")),
        stock_hk_spot_em=lambda: (_ for _ in ()).throw(RuntimeError("hk ssl error")),
        stock_hk_main_board_spot_em=lambda: (_ for _ in ()).throw(RuntimeError("hk main down")),
        stock_hsgt_sh_hk_spot_em=lambda: (_ for _ in ()).throw(RuntimeError("hk hsgt down")),
        fund_etf_spot_em=lambda: _etf_df(),
    )

    prices = AkshareProvider(ak).fetch(["601899.SH", "00883.HK", "159819.SZ", "515880.SH", "510300.SH"])

    assert prices["601899.SH"].price is None
    assert prices["601899.SH"].provider_diagnostics["function_name"] == "stock_sh_a_spot_em"
    assert prices["00883.HK"].price is None
    assert prices["00883.HK"].provider_diagnostics["function_name"] == "stock_hsgt_sh_hk_spot_em"
    assert prices["159819.SZ"].price == 0.921
    assert prices["515880.SH"].price == 1.084
    assert prices["510300.SH"].price == 3.921
    assert "provider_error" not in prices["159819.SZ"].quality_issues


def test_report_shows_each_akshare_interface_status_and_partial_success():
    ak = SimpleNamespace(
        stock_zh_a_spot_em=lambda: (_ for _ in ()).throw(ConnectionError("a share down")),
        stock_sh_a_spot_em=lambda: (_ for _ in ()).throw(ConnectionError("sh fallback down")),
        stock_sz_a_spot_em=lambda: (_ for _ in ()).throw(ConnectionError("sz fallback down")),
        stock_hk_spot_em=lambda: (_ for _ in ()).throw(RuntimeError("hk ssl error")),
        stock_hk_main_board_spot_em=lambda: (_ for _ in ()).throw(RuntimeError("hk main down")),
        stock_hsgt_sh_hk_spot_em=lambda: (_ for _ in ()).throw(RuntimeError("hk hsgt down")),
        fund_etf_spot_em=lambda: _etf_df(),
    )
    raw_prices = AkshareProvider(ak).fetch(["601899.SH", "00883.HK", "159819.SZ"])
    records = [
        _record("energy", raw_prices["601899.SH"], required=True),
        _record("energy", raw_prices["00883.HK"], required=True),
        _record("tech", raw_prices["159819.SZ"], required=True),
    ]

    report = build_completeness_report(records)

    assert "Provider diagnostics" in report
    assert "stock_zh_a_spot_em: fail" in report
    assert "stock_sh_a_spot_em: fail" in report
    assert "stock_sz_a_spot_em: not_called" in report
    assert "stock_hk_spot_em: fail" in report
    assert "stock_hk_main_board_spot_em: fail" in report
    assert "stock_hsgt_sh_hk_spot_em: fail" in report
    assert "fund_etf_spot_em: success" in report
    assert "AKShare partially succeeded" in report
    assert "AKShare 全部接口调用失败" not in report
    assert "ConnectionError" in report
    assert "a share down" in report


def test_required_provider_errors_appear_in_blocking_records_with_function_name():
    ak = SimpleNamespace(
        stock_zh_a_spot_em=lambda: (_ for _ in ()).throw(ConnectionError("a share down")),
        stock_sh_a_spot_em=lambda: (_ for _ in ()).throw(ConnectionError("sh fallback down")),
        stock_sz_a_spot_em=lambda: (_ for _ in ()).throw(ConnectionError("sz fallback down")),
        stock_hk_spot_em=lambda: (_ for _ in ()).throw(RuntimeError("hk ssl error")),
        stock_hk_main_board_spot_em=lambda: (_ for _ in ()).throw(RuntimeError("hk main down")),
        stock_hsgt_sh_hk_spot_em=lambda: (_ for _ in ()).throw(RuntimeError("hk hsgt down")),
        fund_etf_spot_em=lambda: _etf_df(),
    )
    raw_prices = AkshareProvider(ak).fetch(["601899.SH", "00883.HK", "159819.SZ"])
    records = [
        _record("energy", raw_prices["601899.SH"], required=True),
        _record("energy", raw_prices["00883.HK"], required=True),
        _record("tech", raw_prices["159819.SZ"], required=True),
    ]

    blocking = get_blocking_records(records)

    assert {record["symbol"] for record in blocking} >= {"601899.SH", "00883.HK"}
    assert any(record["function_name"] == "stock_sh_a_spot_em" for record in blocking)
    assert any(record["exception_type"] == "ConnectionError" for record in blocking)


def test_a_share_fallback_sh_success_returns_prices():
    ak = SimpleNamespace(
        stock_zh_a_spot_em=lambda: (_ for _ in ()).throw(ConnectionError("primary down")),
        stock_sh_a_spot_em=lambda: pd.DataFrame(
            [
                {"代码": "601899", "名称": "紫金矿业", "最新价": 18.42, "更新时间": "2026-05-18 12:00:00+08:00"},
                {"代码": "601985", "名称": "中国核电", "最新价": 10.91, "更新时间": "2026-05-18 12:00:00+08:00"},
            ]
        ),
        stock_sz_a_spot_em=lambda: pd.DataFrame(),
        stock_hk_spot_em=lambda: pd.DataFrame(),
        stock_hk_main_board_spot_em=lambda: pd.DataFrame(),
        stock_hsgt_sh_hk_spot_em=lambda: pd.DataFrame(),
        fund_etf_spot_em=lambda: pd.DataFrame(),
    )

    prices = AkshareProvider(ak).fetch(["601899.SH", "601985.SH"])

    assert prices["601899.SH"].price == 18.42
    assert prices["601985.SH"].price == 10.91
    assert prices["601899.SH"].provider_diagnostics["function_name"] == "stock_sh_a_spot_em"
    assert prices["601899.SH"].provider_diagnostics["provider_status"] == "fallback_success"
    assert "provider_error" not in prices["601899.SH"].quality_issues


def test_a_share_fallback_sz_success_returns_price():
    ak = SimpleNamespace(
        stock_zh_a_spot_em=lambda: (_ for _ in ()).throw(ConnectionError("primary down")),
        stock_sh_a_spot_em=lambda: pd.DataFrame(),
        stock_sz_a_spot_em=lambda: pd.DataFrame(
            [{"代码": "003816", "名称": "中国广核", "最新价": 4.27, "更新时间": "2026-05-18 12:00:00+08:00"}]
        ),
        stock_hk_spot_em=lambda: pd.DataFrame(),
        stock_hk_main_board_spot_em=lambda: pd.DataFrame(),
        stock_hsgt_sh_hk_spot_em=lambda: pd.DataFrame(),
        fund_etf_spot_em=lambda: pd.DataFrame(),
    )

    price = AkshareProvider(ak).fetch(["003816.SZ"])["003816.SZ"]

    assert price.price == 4.27
    assert price.provider_diagnostics["function_name"] == "stock_sz_a_spot_em"
    assert price.provider_diagnostics["provider_status"] == "fallback_success"


def test_report_shows_a_share_primary_failed_and_fallback_success():
    ak = SimpleNamespace(
        stock_zh_a_spot_em=lambda: (_ for _ in ()).throw(ConnectionError("primary down")),
        stock_sh_a_spot_em=lambda: pd.DataFrame(
            [{"代码": "601899", "名称": "紫金矿业", "最新价": 18.42, "更新时间": "2026-05-18 12:00:00+08:00"}]
        ),
        stock_sz_a_spot_em=lambda: pd.DataFrame(),
        stock_hk_spot_em=lambda: pd.DataFrame(),
        stock_hk_main_board_spot_em=lambda: pd.DataFrame(),
        stock_hsgt_sh_hk_spot_em=lambda: pd.DataFrame(),
        fund_etf_spot_em=lambda: pd.DataFrame(),
    )
    raw = AkshareProvider(ak).fetch(["601899.SH"])["601899.SH"]

    report = build_completeness_report([_record("energy", raw, required=True)])

    assert "stock_zh_a_spot_em: fail" in report
    assert "stock_sh_a_spot_em: success" in report
    assert "provider_status=fallback_success" in report
    assert "AKShare partially succeeded" in report


def test_hk_main_board_fallback_success_returns_price():
    ak = SimpleNamespace(
        stock_zh_a_spot_em=lambda: pd.DataFrame(),
        stock_sh_a_spot_em=lambda: pd.DataFrame(),
        stock_sz_a_spot_em=lambda: pd.DataFrame(),
        stock_hk_spot_em=lambda: (_ for _ in ()).throw(RuntimeError("primary hk down")),
        stock_hk_main_board_spot_em=lambda: pd.DataFrame(
            [{"代码": "00883", "名称": "中海油H", "最新价": 21.35, "更新时间": "2026-05-18 12:00:00+08:00"}]
        ),
        stock_hsgt_sh_hk_spot_em=lambda: pd.DataFrame(),
        fund_etf_spot_em=lambda: pd.DataFrame(),
    )

    price = AkshareProvider(ak).fetch(["00883.HK"])["00883.HK"]

    assert price.price == 21.35
    assert price.provider_diagnostics["function_name"] == "stock_hk_main_board_spot_em"
    assert price.provider_diagnostics["provider_status"] == "fallback_success"


def test_hk_hsgt_fallback_success_returns_price():
    ak = SimpleNamespace(
        stock_zh_a_spot_em=lambda: pd.DataFrame(),
        stock_sh_a_spot_em=lambda: pd.DataFrame(),
        stock_sz_a_spot_em=lambda: pd.DataFrame(),
        stock_hk_spot_em=lambda: (_ for _ in ()).throw(RuntimeError("primary hk down")),
        stock_hk_main_board_spot_em=lambda: (_ for _ in ()).throw(RuntimeError("main board down")),
        stock_hsgt_sh_hk_spot_em=lambda: pd.DataFrame(
            [{"代码": "883", "名称": "中海油H", "最新价": 21.35, "更新时间": "2026-05-18 12:00:00+08:00"}]
        ),
        fund_etf_spot_em=lambda: pd.DataFrame(),
    )

    price = AkshareProvider(ak).fetch(["00883.HK"])["00883.HK"]

    assert price.price == 21.35
    assert price.provider_diagnostics["function_name"] == "stock_hsgt_sh_hk_spot_em"
    assert price.provider_diagnostics["provider_status"] == "fallback_success"


def test_all_hk_fallback_failures_keep_all_attempts():
    ak = SimpleNamespace(
        stock_zh_a_spot_em=lambda: pd.DataFrame(),
        stock_sh_a_spot_em=lambda: pd.DataFrame(),
        stock_sz_a_spot_em=lambda: pd.DataFrame(),
        stock_hk_spot_em=lambda: (_ for _ in ()).throw(RuntimeError("primary hk down")),
        stock_hk_main_board_spot_em=lambda: (_ for _ in ()).throw(RuntimeError("main board down")),
        stock_hsgt_sh_hk_spot_em=lambda: (_ for _ in ()).throw(RuntimeError("hsgt down")),
        fund_etf_spot_em=lambda: pd.DataFrame(),
    )

    price = AkshareProvider(ak).fetch(["00883.HK"])["00883.HK"]
    attempts = price.provider_diagnostics["attempts"]

    assert price.price is None
    assert "provider_error" in price.quality_issues
    assert [attempt["function_name"] for attempt in attempts] == [
        "stock_hk_spot_em",
        "stock_hk_main_board_spot_em",
        "stock_hsgt_sh_hk_spot_em",
    ]
    assert all(attempt["status"] == "fail" for attempt in attempts)


def test_fallback_success_does_not_create_strict_blocker_for_provider_error():
    ak = SimpleNamespace(
        stock_zh_a_spot_em=lambda: (_ for _ in ()).throw(ConnectionError("primary down")),
        stock_sh_a_spot_em=lambda: pd.DataFrame(
            [{"代码": "601899", "名称": "紫金矿业", "最新价": 18.42, "更新时间": "2026-05-18 12:00:00+08:00"}]
        ),
        stock_sz_a_spot_em=lambda: pd.DataFrame(),
        stock_hk_spot_em=lambda: pd.DataFrame(),
        stock_hk_main_board_spot_em=lambda: pd.DataFrame(),
        stock_hsgt_sh_hk_spot_em=lambda: pd.DataFrame(),
        fund_etf_spot_em=lambda: pd.DataFrame(),
    )
    raw = AkshareProvider(ak).fetch(["601899.SH"])["601899.SH"]
    record = _record("energy", raw, required=True)
    record.is_stale = False
    record.stale_reason = ""

    assert get_blocking_records([record]) == []


def test_fallback_failure_required_record_blocks():
    ak = SimpleNamespace(
        stock_zh_a_spot_em=lambda: (_ for _ in ()).throw(ConnectionError("primary down")),
        stock_sh_a_spot_em=lambda: (_ for _ in ()).throw(ConnectionError("fallback down")),
        stock_sz_a_spot_em=lambda: pd.DataFrame(),
        stock_hk_spot_em=lambda: pd.DataFrame(),
        stock_hk_main_board_spot_em=lambda: pd.DataFrame(),
        stock_hsgt_sh_hk_spot_em=lambda: pd.DataFrame(),
        fund_etf_spot_em=lambda: pd.DataFrame(),
    )
    raw = AkshareProvider(ak).fetch(["601899.SH"])["601899.SH"]

    blocking = get_blocking_records([_record("energy", raw, required=True)])

    assert blocking[0]["symbol"] == "601899.SH"
    assert blocking[0]["function_name"] == "stock_sh_a_spot_em"
    assert blocking[0]["provider_status"] == "fallback_failed"


def test_report_for_closed_etf_does_not_say_open_market_stale():
    raw = AkshareProvider(make_ak(etf_df=pd.DataFrame([
        {"代码": "159819", "名称": "人工智能ETF", "最新价": 0.921, "更新时间": "2026-05-18 15:34:21+08:00"}
    ]))).fetch(["159819.SZ"])["159819.SZ"]
    record = _record("tech", raw, required=True)
    record.is_stale = False
    record.stale_reason = "市场已收盘；收盘后/最后更新时间参考价，不可用于盘中做T"
    record.provider_diagnostics.update(
        {
            "age_seconds": 1557,
            "max_age_seconds": 86400,
            "fetch_time_utc": "2026-05-18T08:00:00+00:00",
        }
    )

    report = build_completeness_report([record])

    assert "market_status=closed" in report
    assert "quote_time_utc=2026-05-18T07:34:21+00:00" in report
    assert "fetch_time_utc=2026-05-18T08:00:00+00:00" in report
    assert "age_seconds=1557" in report
    assert "max_age_seconds=86400" in report
    assert "交易中价格超过 max_age_seconds" not in report
    assert "不适合盘中做T判断" in report


def test_provider_health_report_shows_etf_success():
    raw_prices = AkshareProvider(make_ak(etf_df=_etf_df())).fetch(["159632.SZ", "513300.SH", "159819.SZ", "515880.SH", "510300.SH"])
    records = [_record("tech", raw, required=raw.symbol != "510300.SH") for raw in raw_prices.values()]

    report = build_provider_health_report(records, provider_mode="live")

    assert "## AKShare ETF" in report
    assert "function_name=fund_etf_spot_em, status=success" in report
    assert "matched_symbols=159632.SZ, 513300.SH, 159819.SZ, 515880.SH, 510300.SH" in report


def test_provider_health_report_lists_a_share_primary_and_fallback_failures():
    ak = SimpleNamespace(
        stock_zh_a_spot_em=lambda: (_ for _ in ()).throw(ConnectionError("primary down")),
        stock_sh_a_spot_em=lambda: (_ for _ in ()).throw(ConnectionError("sh down")),
        stock_sz_a_spot_em=lambda: (_ for _ in ()).throw(ConnectionError("sz down")),
        stock_hk_spot_em=lambda: pd.DataFrame(),
        stock_hk_main_board_spot_em=lambda: pd.DataFrame(),
        stock_hsgt_sh_hk_spot_em=lambda: pd.DataFrame(),
        fund_etf_spot_em=lambda: pd.DataFrame(),
    )
    raw_prices = AkshareProvider(ak).fetch(["601899.SH", "601985.SH", "003816.SZ"])
    records = [_record("energy", raw, required=True) for raw in raw_prices.values()]

    report = build_provider_health_report(records, provider_mode="live")

    assert "stock_zh_a_spot_em" in report
    assert "stock_sh_a_spot_em" in report
    assert "stock_sz_a_spot_em" in report
    assert "affected_symbols=601899.SH, 601985.SH, 003816.SZ" in report
    assert "ConnectionError" in report


def test_provider_health_report_lists_all_hk_fallback_failures():
    ak = SimpleNamespace(
        stock_zh_a_spot_em=lambda: pd.DataFrame(),
        stock_sh_a_spot_em=lambda: pd.DataFrame(),
        stock_sz_a_spot_em=lambda: pd.DataFrame(),
        stock_hk_spot_em=lambda: (_ for _ in ()).throw(RuntimeError("primary hk down")),
        stock_hk_main_board_spot_em=lambda: (_ for _ in ()).throw(RuntimeError("main down")),
        stock_hsgt_sh_hk_spot_em=lambda: (_ for _ in ()).throw(RuntimeError("hsgt down")),
        fund_etf_spot_em=lambda: pd.DataFrame(),
    )
    raw = AkshareProvider(ak).fetch(["00883.HK"])["00883.HK"]

    report = build_provider_health_report([_record("energy", raw, required=True)], provider_mode="live")

    assert "stock_hk_spot_em" in report
    assert "stock_hk_main_board_spot_em" in report
    assert "stock_hsgt_sh_hk_spot_em" in report
    assert "affected_symbols=00883.HK" in report
    assert "RuntimeError" in report


def _etf_df():
    return pd.DataFrame(
        [
            {"代码": "159632", "名称": "纳指相关ETF", "最新价": 1.432, "更新时间": "2024-12-26 16:11:57+08:00"},
            {"代码": "513300", "名称": "纳指ETF", "最新价": 1.671, "更新时间": "2024-12-26 16:11:57+08:00"},
            {"代码": "159819", "名称": "人工智能ETF", "最新价": 0.921, "更新时间": "2024-12-26 16:11:57+08:00"},
            {"代码": "515880", "名称": "通信ETF", "最新价": 1.084, "更新时间": "2024-12-26 16:11:57+08:00"},
            {"代码": "510300", "名称": "沪深300ETF", "最新价": 3.921, "更新时间": "2024-12-26 16:11:57+08:00"},
        ]
    )


def _record(project: str, raw, required: bool):
    return PriceRecord(
        project=project,
        symbol=raw.symbol,
        name=raw.name or raw.symbol,
        market=raw.market or "CN",
        price=raw.price,
        currency=raw.currency,
        source=raw.source,
        quote_time=raw.quote_time,
        fetch_time=raw.fetch_time,
        market_status=raw.market_status,
        is_stale=bool(raw.quality_issues),
        stale_reason=", ".join(raw.quality_issues),
        required_for_operation=required,
        quality_issues=raw.quality_issues,
        provider_diagnostics=raw.provider_diagnostics,
    )
