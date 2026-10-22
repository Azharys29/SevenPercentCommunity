#!/usr/bin/env python3
"""Low-volume, non-invasive Alpha Vantage diagnostics for IDX ticker coverage.

This script does not feed SPC signals or modify existing datasets. It writes a
sanitized status report only; API keys and raw provider responses are never saved.
"""
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

API_URL = "https://www.alphavantage.co/query"
OUT = Path("data/alpha-vantage-reference-status.json")
TICKERS = ["BBCA", "BBRI", "ANTM", "MEDC", "PTBA"]
CONTROL_SYMBOL = "IBM"
TIMEOUT = 20


def request_api(params, api_key):
    query = dict(params)
    query["apikey"] = api_key
    req = Request(API_URL + "?" + urlencode(query), headers={"User-Agent": "SevenPercentCommunity-reference-check/1.0"})
    try:
        with urlopen(req, timeout=TIMEOUT) as response:
            status = response.status
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict):
            return status, {}, "invalid_response"
        return status, payload, None
    except HTTPError as exc:
        return exc.code, {}, "http_error"
    except (URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None, {}, "request_error"


def classify(status, payload, error):
    if error:
        return "request_error"
    if status != 200:
        return "http_error"
    if "Error Message" in payload:
        return "unsupported_or_invalid_symbol"
    notice = str(payload.get("Information") or payload.get("Note") or "").lower()
    if notice:
        if any(word in notice for word in ("invalid api key", "apikey", "api key", "missing api key")):
            return "api_key_notice"
        if any(word in notice for word in ("premium", "subscription", "entitlement", "endpoint is premium")):
            return "premium_entitlement_notice"
        if any(word in notice for word in ("rate", "frequency", "limit", "requests per day", "call frequency")):
            return "quota_notice"
        return "provider_notice"
    return "ok"


def safe_notice_category(payload):
    """Expose only a reason category, never the provider message or key."""
    notice = str(payload.get("Information") or payload.get("Note") or "").lower()
    if not notice:
        return None
    if any(word in notice for word in ("invalid api key", "apikey", "api key", "missing api key")):
        return "api_key_check_required"
    if any(word in notice for word in ("premium", "subscription", "entitlement", "endpoint is premium")):
        return "premium_or_entitlement_required"
    if any(word in notice for word in ("rate", "frequency", "limit", "requests per day", "call frequency")):
        return "daily_quota_or_rate_limit"
    return "provider_notice_unclassified"


def main():
    api_key = os.environ.get("ALPHA_VANTAGE_API_KEY", "").strip()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    report = {
        "provider": "Alpha Vantage",
        "diagnostic_version": 3,
        "generated_at_utc": now,
        "purpose": "diagnostic_only_not_used_for_spc_signals",
        "secret_configured": bool(api_key),
        "checks": [],
        "notes": [
            "No raw provider payloads or API key are stored.",
            "Provider notices are reduced to safe categories; raw notice text is never written.",
            "A successful response confirms endpoint response only, not data quality or licensing suitability.",
            "IDX ticker support and endpoint access must be confirmed empirically."
        ],
    }
    if not api_key:
        report["overall_status"] = "secret_missing"
        report["message"] = "Repository secret ALPHA_VANTAGE_API_KEY is not available to this workflow."
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print("Alpha Vantage check: secret missing; wrote sanitized status.")
        return

    status, payload, error = request_api({"function": "SYMBOL_SEARCH", "keywords": "BBCA"}, api_key)
    search_state = classify(status, payload, error)
    matches = payload.get("bestMatches", []) if search_state == "ok" else []
    symbol_search = {
        "endpoint": "SYMBOL_SEARCH",
        "query": "BBCA",
        "http_status": status,
        "status": search_state,
        "notice_category": safe_notice_category(payload),
        "match_count": len(matches) if isinstance(matches, list) else 0,
        "candidate_symbols": [
            str(item.get("1. symbol", "")) for item in matches[:10]
            if isinstance(item, dict) and item.get("1. symbol")
        ] if isinstance(matches, list) else [],
    }
    report["checks"].append(symbol_search)

    # Known supported control symbol separates API-key/endpoint problems from
    # IDX ticker coverage. It is diagnostic only and is never used by SPC.
    status, payload, error = request_api(
        {"function": "TIME_SERIES_DAILY", "symbol": CONTROL_SYMBOL, "outputsize": "compact"},
        api_key,
    )
    state = classify(status, payload, error)
    control_series = payload.get("Time Series (Daily)", {}) if state == "ok" else {}
    control_dates = sorted(control_series.keys(), reverse=True) if isinstance(control_series, dict) else []
    control_rows = 0
    if isinstance(control_series, dict):
        for row in control_series.values():
            if isinstance(row, dict) and all(k in row for k in ("1. open", "2. high", "3. low", "4. close", "5. volume")):
                try:
                    values = [float(row[k]) for k in ("1. open", "2. high", "3. low", "4. close", "5. volume")]
                    if all(v >= 0 for v in values) and values[1] >= values[2] and values[3] >= values[2] and values[3] > 0:
                        control_rows += 1
                except (TypeError, ValueError):
                    pass
    report["checks"].append({
        "endpoint": "TIME_SERIES_DAILY",
        "ticker": CONTROL_SYMBOL,
        "symbol_tested": CONTROL_SYMBOL,
        "symbol_format": "control_us_symbol",
        "is_control": True,
        "http_status": status,
        "status": state,
        "notice_category": safe_notice_category(payload),
        "observations_returned": len(control_series) if isinstance(control_series, dict) else 0,
        "valid_ohlcv_rows": control_rows,
        "latest_date": control_dates[0] if control_dates else None,
        "oldest_date_in_response": control_dates[-1] if control_dates else None,
    })
    time.sleep(1)

    for ticker in TICKERS:
        # Symbol Search returned an unsuffixed BBCA candidate. Test both formats
        # rather than assuming the Yahoo Finance .JK convention is accepted.
        for symbol in (ticker, ticker + ".JK"):
            status, payload, error = request_api(
                {"function": "TIME_SERIES_DAILY", "symbol": symbol, "outputsize": "compact"},
                api_key,
            )
            state = classify(status, payload, error)
            series = payload.get("Time Series (Daily)", {}) if state == "ok" else {}
            dates = sorted(series.keys(), reverse=True) if isinstance(series, dict) else []
            valid_rows = 0
            if isinstance(series, dict):
                for row in series.values():
                    if isinstance(row, dict) and all(k in row for k in ("1. open", "2. high", "3. low", "4. close", "5. volume")):
                        try:
                            values = [float(row[k]) for k in ("1. open", "2. high", "3. low", "4. close", "5. volume")]
                            if all(v >= 0 for v in values) and values[1] >= values[2] and values[3] > 0:
                                valid_rows += 1
                        except (TypeError, ValueError):
                            pass
            notice_category = safe_notice_category(payload)
            report["checks"].append({
                "endpoint": "TIME_SERIES_DAILY",
                "ticker": ticker,
                "symbol_tested": symbol,
                "symbol_format": "unsuffixed" if symbol == ticker else "dot_jk_suffix",
                "http_status": status,
                "status": state,
                "notice_category": notice_category,
                "observations_returned": len(series) if isinstance(series, dict) else 0,
                "valid_ohlcv_rows": valid_rows,
                "latest_date": dates[0] if dates else None,
                "oldest_date_in_response": dates[-1] if dates else None,
            })
            time.sleep(1)

    daily = [item for item in report["checks"] if item.get("endpoint") == "TIME_SERIES_DAILY"]
    valid_tickers = sorted({
        item.get("ticker") for item in daily
        if not item.get("is_control")
        and item.get("symbol_format") != "control_us_symbol"
        and item["status"] == "ok"
        and item["valid_ohlcv_rows"] > 0
        and item.get("ticker") in TICKERS
    })
    ok_count = len(valid_tickers)
    control_check = next((x for x in report["checks"] if x.get("is_control")), {})
    control_ok = control_check.get("status") == "ok" and control_check.get("valid_ohlcv_rows", 0) > 0
    if ok_count:
        report["overall_status"] = "idx_symbols_responding"
    elif not control_ok:
        report["overall_status"] = "provider_access_not_confirmed"
    else:
        report["overall_status"] = "idx_support_not_confirmed"
    report["diagnosis"] = {
        "control_symbol": CONTROL_SYMBOL,
        "control_symbol_status": control_check.get("status", "not_checked"),
        "control_symbol_notice_category": control_check.get("notice_category"),
        "idx_coverage_can_be_judged": bool(control_ok),
        "summary": (
            "API key/plan/quota access must be resolved before IDX ticker coverage can be judged."
            if not control_ok else
            ("At least one IDX ticker returned valid data." if ok_count else
             "The API responds for the control symbol, but none of the tested IDX symbols returned valid daily data.")
        )
    }
    report["idx_symbols_with_valid_daily_data"] = ok_count
    report["valid_idx_tickers"] = valid_tickers
    report["idx_symbols_tested"] = len(TICKERS)
    report["symbol_formats_tested"] = ["unsuffixed", "dot_jk_suffix"]
    report["reference_families"] = {
        "price_cross_check": {
            "status": "available" if ok_count == len(TICKERS) else ("partially_available" if ok_count else "unavailable"),
            "provider": "Alpha Vantage",
            "endpoint": "TIME_SERIES_DAILY",
            "valid_tested_symbols": ok_count,
            "tested_symbols": len(TICKERS),
            "source_date": max((item.get("latest_date") for item in daily if item.get("latest_date")), default=None),
            "fetched_at_utc": now,
            "note": "Only validated daily OHLCV responses can be used for comparison; no external value is used in SPC calculations."
        },
        "fundamental_reference": {
            "status": "not_checked", "provider": "Alpha Vantage", "endpoint": "OVERVIEW / financial statements",
            "fetched_at_utc": None, "note": "Endpoint entitlement and IDX ticker coverage have not been validated."
        },
        "news_sentiment": {
            "status": "not_checked", "provider": "Alpha Vantage", "endpoint": "NEWS_SENTIMENT",
            "fetched_at_utc": None, "note": "Endpoint entitlement, ticker coverage, and publication metadata have not been validated."
        },
        "macro_reference": {
            "status": "not_checked", "provider": "Alpha Vantage", "endpoint": "Economic Indicators / Commodities",
            "fetched_at_utc": None, "note": "Relevant Indonesia-specific macro coverage has not been validated; US indicators are not a substitute."
        }
    }
    report["message"] = (
        "At least one tested IDX ticker returned parseable daily OHLCV data using one of the tested symbol formats."
        if ok_count else
        ("Control-symbol test failed; resolve API key, plan entitlement, or daily quota before judging IDX coverage."
         if not control_ok else
         "The control-symbol test succeeded, but no tested IDX ticker returned parseable daily OHLCV data; do not enable this source for SPC analysis.")
    )
    report["rollout_state"] = "reference_status_only" if not ok_count else "price_cross_check_candidate"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Alpha Vantage reference diagnostics completed.")
    print("Overall status:", report["overall_status"])
    print("Valid IDX daily series:", f"{ok_count}/{len(TICKERS)}")
    print("Report:", OUT.as_posix())


if __name__ == "__main__":
    main()
