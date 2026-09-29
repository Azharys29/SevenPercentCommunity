#!/usr/bin/env python3
"""Build Value Gap Score for KOMPAS100 using Yahoo Finance price + annual EPS data."""
import datetime as dt, json, math, time
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
UNIVERSE = ROOT / "universe.csv"
SCREENER = ROOT / "data/screener.json"
OUT = ROOT / "data/value-gap.json"


def finite(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def pick_eps_row(stmt):
    if stmt is None or stmt.empty:
        return None
    preferred = [
        "Diluted EPS",
        "Basic EPS",
        "DilutedEPS",
        "BasicEPS",
    ]
    for name in preferred:
        if name in stmt.index:
            return stmt.loc[name]
    for idx in stmt.index:
        key = str(idx).lower().replace(" ", "").replace("_", "")
        if key in ("dilutedeps", "basiceps"):
            return stmt.loc[idx]
    return None


def annual_eps(stmt):
    row = pick_eps_row(stmt)
    if row is None:
        return []
    out = []
    for col in row.index:
        value = finite(row.get(col))
        if value is None or value <= 0:
            continue
        try:
            date = pd.Timestamp(col).date()
        except Exception:
            continue
        out.append((date, value))
    out.sort(key=lambda x: x[0], reverse=True)
    return out


def price_on_or_before(history, target):
    if history is None or history.empty:
        return None
    h = history.copy()
    idx = pd.DatetimeIndex(h.index)
    dates = idx.tz_localize(None).date
    mask = dates <= target
    if not mask.any():
        return None
    pos = mask.nonzero()[0][-1]
    return finite(h.iloc[pos]["Close"])


def historical_pe(stmt, history):
    eps = annual_eps(stmt)
    result = []
    for fiscal_date, eps_value in eps:
        price = price_on_or_before(history, fiscal_date)
        if price is not None and price > 0:
            pe = price / eps_value
            if math.isfinite(pe) and pe > 0:
                result.append((fiscal_date.isoformat(), pe))
    return result[:3], eps


def returns(history, asof):
    if history is None or history.empty:
        return None, None
    c = history["Close"].dropna()
    if len(c) < 22:
        return None, None
    last = finite(c.iloc[-1])
    base = finite(c.iloc[-22])
    r1m = (last / base - 1) * 100 if last and base and base > 0 else None

    dates = pd.DatetimeIndex(c.index).tz_localize(None)
    cy = c[dates.year == asof.year]
    ry = (last / float(cy.iloc[0]) - 1) * 100 if last and len(cy) and float(cy.iloc[0]) > 0 else None
    return r1m, ry


def main():
    u = pd.read_csv(UNIVERSE, dtype=str).fillna("")
    screen = json.loads(SCREENER.read_text(encoding="utf-8"))
    asof = dt.date.fromisoformat(str(screen["asof"])[:10])

    rows = []
    errors = []

    for _, r in u.iterrows():
        ticker = str(r["ticker"]).strip().upper()
        if not ticker:
            continue

        try:
            t = yf.Ticker(ticker + ".JK")

            # Current PE from Yahoo's current trailing PE. If unavailable,
            # calculate it from current price / trailing EPS.
            info = t.info or {}
            current_pe = finite(info.get("trailingPE"))
            trailing_eps = finite(info.get("trailingEps"))

            history = t.history(period="5y", auto_adjust=False)
            if history is None or history.empty:
                raise ValueError("No price history")

            last_close = finite(history["Close"].dropna().iloc[-1])
            if current_pe is None and last_close and trailing_eps and trailing_eps > 0:
                current_pe = last_close / trailing_eps

            # Yahoo valuation-measures endpoint has become unreliable for many
            # IDX tickers. Build the 3Y historical PE directly from annual EPS
            # and the closing price at/just before each fiscal year-end.
            stmt = t.get_income_stmt(freq="yearly")
            pe_hist, eps_hist = historical_pe(stmt, history)
            hist3 = [x for _, x in pe_hist if x > 0]
            avg_pe = sum(hist3) / 3 if len(hist3) == 3 else None

            # EPS Growth = latest annual diluted/basic EPS growth vs prior year.
            growth = None
            if len(eps_hist) >= 2:
                latest_eps = eps_hist[0][1]
                prior_eps = eps_hist[1][1]
                if prior_eps > 0:
                    growth = (latest_eps / prior_eps - 1) * 100

            # Fallback to Yahoo trailing earningsGrowth if annual EPS is unavailable.
            if growth is None:
                growth = finite(info.get("earningsGrowth"))
                if growth is not None and abs(growth) < 2:
                    growth *= 100

            r1m, ry = returns(history, asof)
            score = (
                (avg_pe - current_pe) * growth
                if avg_pe is not None and current_pe is not None and growth is not None
                else None
            )

            rows.append({
                "ticker": ticker,
                "name": str(r["name"]).strip() or ticker,
                "sector": str(r["sector"]).strip() or "Lainnya",
                "current_pe": round(current_pe, 2) if current_pe is not None else None,
                "avg_pe_3y": round(avg_pe, 2) if avg_pe is not None else None,
                "eps_growth": round(growth, 2) if growth is not None else None,
                "value_gap_score": round(score, 2) if score is not None else None,
                "return_1m": round(r1m, 2) if r1m is not None else None,
                "return_ytd": round(ry, 2) if ry is not None else None,
                "pe_history": [
                    {"period": period, "pe": round(pe, 2)}
                    for period, pe in pe_hist
                ],
                "status": "ok" if score is not None else "incomplete",
            })
        except Exception as exc:
            errors.append({"ticker": ticker, "error": str(exc)[:160]})
            rows.append({
                "ticker": ticker,
                "name": str(r["name"]).strip() or ticker,
                "sector": str(r["sector"]).strip() or "Lainnya",
                "current_pe": None,
                "avg_pe_3y": None,
                "eps_growth": None,
                "value_gap_score": None,
                "return_1m": None,
                "return_ytd": None,
                "pe_history": [],
                "status": "error",
            })

        time.sleep(0.05)

    rows.sort(key=lambda x: (x["value_gap_score"] is None, -(x["value_gap_score"] or 0)))

    payload = {
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "asof": asof.isoformat(),
        "universe": "KOMPAS100",
        "universe_count": len(rows),
        "valid_count": sum(x["value_gap_score"] is not None for x in rows),
        "error_count": len(errors),
        "formula": "(Average 3Y P/E - Current P/E) × EPS Growth (%)",
        "eps_growth_definition": "Annual EPS growth: latest fiscal-year EPS versus prior fiscal-year EPS; Yahoo trailing earningsGrowth used only as fallback",
        "historical_pe_definition": "Each annual P/E = fiscal-year-end/nearest prior closing price divided by that fiscal year's EPS",
        "sources": ["Yahoo Finance / yfinance"],
        "errors": errors,
        "stocks": rows,
    }

    OUT.write_text(
        json.dumps(payload, separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8",
    )
    print(
        f"Value Gap: {payload['valid_count']}/{payload['universe_count']} valid, "
        f"asof {payload['asof']}, errors {payload['error_count']}"
    )


if __name__ == "__main__":
    main()
