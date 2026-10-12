#!/usr/bin/env python3
"""Build monthly Dividend Intelligence data for the Kompas 100 universe.

Yahoo Finance is an automation source, not an authoritative filing source.
Missing or implausible data stay null; no synthetic values are filled.
"""
import datetime as dt
import json
import math
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
UNIVERSE = ROOT / "universe.csv"
SCREENER = ROOT / "data/screener.json"
OUT = ROOT / "data/dividend-intelligence.json"
IDX_URL = "https://www.idx.id/id/perusahaan-tercatat/laporan-keuangan-dan-tahunan"


def num(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def find_row(frame, names):
    if frame is None or frame.empty:
        return None
    normalized = {str(i).strip().lower().replace(" ", "").replace("_", ""): i for i in frame.index}
    for name in names:
        key = name.lower().replace(" ", "").replace("_", "")
        if key in normalized:
            return frame.loc[normalized[key]]
    return None


def row_year_values(frame, names, max_years=5):
    row = find_row(frame, names)
    if row is None:
        return {}
    vals = {}
    for col in row.index:
        value = num(row.get(col))
        if value is None:
            continue
        try:
            year = pd.Timestamp(col).year
        except Exception:
            continue
        vals[year] = value
    years = sorted(vals, reverse=True)[:max_years]
    return {y: vals[y] for y in years}


def series_year_sums(series):
    out = {}
    if series is None or len(series) == 0:
        return out
    try:
        for date, value in series.items():
            v = num(value)
            if v is None:
                continue
            year = pd.Timestamp(date).year
            out[year] = out.get(year, 0.0) + v
    except Exception:
        pass
    return out


def dividend_payment_pattern(series, current_year, years=3):
    """Summarize observed cash dividend payment dates; multiple payments/year are only an interim indicator."""
    if series is None or len(series) == 0:
        return {"years": [], "month_range": "Belum ada data", "pattern_note": "Riwayat tanggal pembayaran tidak tersedia"}
    month_names = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
    by_year = {}
    try:
        for date, value in series.items():
            amount = num(value)
            if amount is None or amount <= 0:
                continue
            d = pd.Timestamp(date)
            if d.year < current_year - years + 1 or d.year > current_year:
                continue
            by_year.setdefault(d.year, []).append({"date": d.strftime("%Y-%m-%d"), "month": int(d.month), "amount_per_share": rounded(amount)})
    except Exception:
        pass
    summaries = []
    months = []
    for year in sorted(by_year):
        items = sorted(by_year[year], key=lambda x: x["date"])
        for item in items:
            if item["month"] not in months:
                months.append(item["month"])
        multi = len(items) > 1
        summaries.append({
            "year": year,
            "payments": len(items),
            "months": [month_names[x["month"] - 1] for x in items],
            "dates": [x["date"] for x in items],
            "amounts_per_share": [x["amount_per_share"] for x in items],
            "interim_indicator": multi,
            "note": ("Beberapa pembayaran dalam setahun; indikasi interim/lebih dari satu tahap, perlu verifikasi pengumuman resmi" if multi else "Satu pembayaran tercatat; kemungkinan dividen tahunan/final, perlu verifikasi pengumuman resmi")
        })
    month_range = ", ".join(month_names[m - 1] for m in sorted(months)) if months else "Belum ada data"
    if summaries:
        interim_years = [str(x["year"]) for x in summaries if x["interim_indicator"]]
        note = "Indikasi pembayaran interim/bertahap pada " + ", ".join(interim_years) if interim_years else "Belum terdeteksi pembayaran lebih dari sekali per tahun"
    else:
        note = "Riwayat tanggal pembayaran 3 tahun tidak tersedia"
    return {"years": summaries, "month_range": month_range, "pattern_note": note, "source_note": "Tanggal pembayaran historis dari Yahoo Finance; klasifikasi interim hanya indikasi, cek pengumuman resmi BEI/KSEI/emiten."}


def safe_mean(values):
    vals = [num(x) for x in values]
    vals = [x for x in vals if x is not None]
    return sum(vals) / len(vals) if vals else None


def rounded(v, digits=2):
    return round(v, digits) if v is not None and math.isfinite(v) else None


def build_stock(ticker, meta, now_year):
    t = yf.Ticker(ticker + ".JK")
    info = t.info or {}
    annual = t.get_income_stmt(freq="yearly")
    quarterly = t.get_income_stmt(freq="quarterly")
    revenue = row_year_values(annual, ["Total Revenue", "Operating Revenue", "Revenue"], 5)
    net_income = row_year_values(annual, ["Net Income", "Net Income Common Stockholders", "Net Income Continuous Operations"], 5)
    eps = row_year_values(annual, ["Diluted EPS", "Basic EPS", "DilutedEPS", "BasicEPS"], 5)
    dividend_series = t.dividends
    divs = series_year_sums(dividend_series)
    payment_pattern = dividend_payment_pattern(dividend_series, now_year, 3)
    shares_raw = num(info.get("sharesOutstanding"))
    market_cap = num(info.get("marketCap"))

    history = t.history(period="5d", auto_adjust=False)
    price = num(history["Close"].dropna().iloc[-1]) if history is not None and not history.empty else None
    if not price or price <= 0:
        price = num(info.get("currentPrice") or info.get("regularMarketPrice"))
    # Yahoo's sharesOutstanding can occasionally reflect float/incorrect units for IDX tickers.
    # Prefer implied shares from market cap / price when the two disagree materially.
    shares_from_market_cap = market_cap / price if market_cap and price and price > 0 else None
    if shares_from_market_cap and shares_from_market_cap > 0:
        if not shares_raw or shares_raw <= 0 or max(shares_raw, shares_from_market_cap) / min(shares_raw, shares_from_market_cap) > 1.5:
            shares = shares_from_market_cap
        else:
            shares = shares_raw
    else:
        shares = shares_raw

    years = sorted(set(revenue) | set(net_income) | set(eps), reverse=True)
    hist = []
    for year in years[:5]:
        rev = revenue.get(year)
        ni = net_income.get(year)
        ep = eps.get(year)
        # Yahoo dividend history can be incomplete or reflect corporate-action adjustments.
        dps = divs.get(year)
        dpr = (dps / ep * 100) if dps is not None and ep is not None and ep > 0 else None
        npm = (ni / rev * 100) if ni is not None and rev is not None and rev > 0 else None
        hist.append({
            "year": year, "revenue": rounded(rev, 0), "net_income": rounded(ni, 0),
            "eps": rounded(ep, 2), "npm_pct": rounded(npm),
            "dividend_per_share": rounded(dps), "dividend_yield_pct": rounded(dps / price * 100) if dps is not None and price else None,
            "dpr_pct": rounded(dpr),
        })

    model_years = hist[:3]
    npm_values = [x["npm_pct"] for x in model_years if x["npm_pct"] is not None]
    dpr_values = [x["dpr_pct"] for x in model_years if x["dpr_pct"] is not None and 0 <= x["dpr_pct"] <= 150]
    npm_avg = safe_mean(npm_values)
    dpr_avg = safe_mean(dpr_values)
    dps_hist = [x["dividend_per_share"] for x in hist if x["dividend_per_share"] is not None and x["dividend_per_share"] >= 0]
    yield_hist = [x["dividend_yield_pct"] for x in hist if x["dividend_yield_pct"] is not None and x["dividend_yield_pct"] >= 0]

    # Estimate full-year revenue from current calendar YTD quarterly reports when available.
    qrev = find_row(quarterly, ["Total Revenue", "Operating Revenue", "Revenue"])
    ytd_revenue = None
    ytd_months = None
    if qrev is not None:
        qvals = []
        for col in qrev.index:
            try:
                date = pd.Timestamp(col)
            except Exception:
                continue
            value = num(qrev.get(col))
            if date.year == now_year and value is not None and value > 0:
                qvals.append((date, value))
        qvals.sort()
        # Yahoo quarterly statements are generally single-quarter values; use available current-year quarters.
        if qvals:
            ytd_revenue = sum(v for _, v in qvals)
            ytd_months = min(12, max(3, 3 * len(qvals)))
    if ytd_revenue is not None and ytd_months:
        revenue_runrate = ytd_revenue * 12 / ytd_months
        forecast_basis = "current_year_quarters_annualized"
    else:
        latest_year = max(revenue) if revenue else None
        revenue_runrate = revenue.get(latest_year) if latest_year is not None else None
        forecast_basis = "latest_annual_revenue_fallback" if revenue_runrate is not None else "unavailable"

    # Scenarios deliberately shrink/expand historical profitability and payout assumptions.
    scenarios = []
    settings = [
        ("Conservative", 0.85, 0.80),
        ("Base", 1.00, 1.00),
        ("Optimistic", 1.10, 1.10),
    ]
    for label, npm_mult, dpr_mult in settings:
        npm = npm_avg * npm_mult if npm_avg is not None else None
        dpr = min(100.0, dpr_avg * dpr_mult) if dpr_avg is not None else None
        net_est = revenue_runrate * npm / 100 if revenue_runrate is not None and npm is not None else None
        total_dividend = net_est * dpr / 100 if net_est is not None and dpr is not None else None
        dps_est = total_dividend / shares if total_dividend is not None and shares and shares > 0 else None
        yield_est = dps_est / price * 100 if dps_est is not None and price and price > 0 else None
        # Extremely high modeled yields usually indicate faulty share count or source data.
        if yield_est is not None and (yield_est < 0 or yield_est > 35):
            yield_est = None
        scenarios.append({
            "scenario": label, "revenue_estimate": rounded(revenue_runrate, 0),
            "npm_assumption_pct": rounded(npm), "dpr_assumption_pct": rounded(dpr),
            "net_income_estimate": rounded(net_est, 0), "total_dividend_estimate": rounded(total_dividend, 0),
            "dps_estimate": rounded(dps_est),
            "yield_estimate_pct": rounded(yield_est),
            "yield_flag": "review_required" if dps_est is not None and price and dps_est / price * 100 > 35 else None,
        })

    valid_divs = [x for x in hist if x["dividend_per_share"] is not None]
    consistency = {
        "years_with_dividend": sum(1 for x in valid_divs if x["dividend_per_share"] > 0),
        "years_observed": len(valid_divs),
        "five_year_consistent": len(valid_divs) >= 5 and all(x["dividend_per_share"] > 0 for x in valid_divs[:5]),
        "avg_yield_5y_pct": rounded(safe_mean(yield_hist)),
        "avg_dps_5y": rounded(safe_mean(dps_hist)),
    }
    return {
        "ticker": ticker, "name": str(meta.get("name") or ticker), "sector": str(meta.get("sector") or "Lainnya"),
        "price": rounded(price), "currency": "IDR", "shares_outstanding": rounded(shares, 0),
        "history": hist, "dividend_payment_pattern_3y": payment_pattern, "npm_avg_3y_pct": rounded(npm_avg), "dpr_avg_3y_pct": rounded(dpr_avg),
        "revenue_estimation_basis": forecast_basis, "revenue_ytd": rounded(ytd_revenue, 0),
        "revenue_estimate_next_fy": rounded(revenue_runrate, 0), "scenarios": scenarios,
        "dividend_consistency": consistency,
        "data_quality": {
            "annual_periods_available": len(hist),
            "has_3y_revenue": sum(1 for x in model_years if x["revenue"] is not None) >= 3,
            "has_3y_npm": len(npm_values) >= 2,
            "has_3y_dpr": len(dpr_values) >= 2,
            "price_available": price is not None,
            "shares_source": "marketCap/price" if shares_from_market_cap and shares == shares_from_market_cap else "sharesOutstanding",
            "source": "Yahoo Finance; cross-check financial statements and corporate actions against IDX/issuer disclosures",
            "validation_url": IDX_URL,
        },
    }


def main():
    universe = pd.read_csv(UNIVERSE, dtype=str).fillna("")
    if "indices" in universe.columns:
        universe = universe[universe["indices"].str.upper().str.contains("KOMPAS100", na=False)]
    screen = json.loads(SCREENER.read_text(encoding="utf-8")) if SCREENER.exists() else {}
    asof = str(screen.get("asof") or dt.date.today().isoformat())[:10]
    now_year = dt.date.today().year
    rows, errors = [], []
    for _, r in universe.iterrows():
        ticker = str(r.get("ticker", "")).strip().upper()
        if not ticker:
            continue
        meta = {"name": r.get("name") or ticker, "sector": r.get("sector") or "Lainnya"}
        try:
            rows.append(build_stock(ticker, meta, now_year))
        except Exception as exc:
            errors.append({"ticker": ticker, "error": str(exc)[:160]})
            rows.append({
                "ticker": ticker, "name": meta["name"], "sector": meta["sector"], "price": None,
                "history": [], "npm_avg_3y_pct": None, "dpr_avg_3y_pct": None,
                "revenue_estimate_next_fy": None, "scenarios": [], "dividend_consistency": {},
                "data_quality": {"status": "error", "message": str(exc)[:160], "validation_url": IDX_URL},
            })
        time.sleep(0.08)
    rows.sort(key=lambda x: (-(next((s.get("yield_estimate_pct") for s in x.get("scenarios", []) if s.get("scenario") == "Base"), None) or -1), x["ticker"]))
    payload = {
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "asof": asof, "universe": "KOMPAS100", "source": "Yahoo Finance; official IDX/issuer filings for validation",
        "validation_url": IDX_URL, "model_history_years": 3, "consistency_history_years": 5, "dividend_payment_history_years": 3,
        "universe_count": len(rows), "valid_price_count": sum(1 for x in rows if x.get("price") is not None),
        "error_count": len(errors), "errors": errors, "stocks": rows,
        "methodology": {
            "revenue_estimate": "Current-year reported quarterly revenue annualized by reported months; fallback to latest annual revenue when YTD data unavailable.",
            "dividend_estimate": "Estimated revenue × scenario NPM × scenario DPR ÷ shares outstanding; estimated yield = DPS ÷ latest price.",
            "payment_pattern": "Actual historical dividend payment dates from Yahoo Finance over three years; months are historical windows, not guaranteed future payment dates. Multiple payments in a year are flagged as a possible interim/instalment pattern and must be verified against official IDX/KSEI/issuer announcements.",
            "scenario_factors": {"Conservative": {"npm": 0.85, "dpr": 0.8}, "Base": {"npm": 1.0, "dpr": 1.0}, "Optimistic": {"npm": 1.1, "dpr": 1.1}},
            "caveat": "Exploratory estimate only. Fiscal periods, special dividends, share changes, corporate actions and incomplete Yahoo data may distort results. Validate against official filings.",
        },
    }
    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, separators=(",", ":"), ensure_ascii=False, allow_nan=False), encoding="utf-8")
    tmp.replace(OUT)
    print(f"Dividend Intelligence: {len(rows)} stocks; {payload['valid_price_count']} prices; {len(errors)} fetch errors; {OUT.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
