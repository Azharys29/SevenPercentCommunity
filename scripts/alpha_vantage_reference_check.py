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
    if "Note" in payload or "Information" in payload:
        return "quota_or_entitlement_notice"
    return "ok"


def main():
    api_key = os.environ.get("ALPHA_VANTAGE_API_KEY", "").strip()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    report = {
        "provider": "Alpha Vantage",
        "generated_at_utc": now,
        "purpose": "diagnostic_only_not_used_for_spc_signals",
        "secret_configured": bool(api_key),
        "checks": [],
        "notes": [
            "No raw provider payloads or API key are stored.",
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
        "match_count": len(matches) if isinstance(matches, list) else 0,
        "candidate_symbols": [
            str(item.get("1. symbol", "")) for item in matches[:10]
            if isinstance(item, dict) and item.get("1. symbol")
        ] if isinstance(matches, list) else [],
    }
    report["checks"].append(symbol_search)

    for ticker in TICKERS:
        symbol = ticker + ".JK"
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
                        if all(v >= 0 for v in values) and values[1] >= values[2]:
                            valid_rows += 1
                    except (TypeError, ValueError):
                        pass
        report["checks"].append({
            "endpoint": "TIME_SERIES_DAILY",
            "symbol_tested": symbol,
            "http_status": status,
            "status": state,
            "observations_returned": len(series) if isinstance(series, dict) else 0,
            "valid_ohlcv_rows": valid_rows,
            "latest_date": dates[0] if dates else None,
            "oldest_date_in_response": dates[-1] if dates else None,
        })
        time.sleep(1)

    daily = [item for item in report["checks"] if item.get("endpoint") == "TIME_SERIES_DAILY"]
    ok_count = sum(item["status"] == "ok" and item["valid_ohlcv_rows"] > 0 for item in daily)
    report["overall_status"] = "idx_symbols_responding" if ok_count else "idx_support_not_confirmed"
    report["idx_symbols_with_valid_daily_data"] = ok_count
    report["idx_symbols_tested"] = len(TICKERS)
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
        "At least one tested IDX symbol returned parseable daily OHLCV data."
        if ok_count else
        "No tested IDX symbol returned parseable daily OHLCV data; do not enable this source for SPC analysis."
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
