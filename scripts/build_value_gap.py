#!/usr/bin/env python3
"""Build Value Gap Score for KOMPAS100 using Yahoo Finance."""
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
    for name in ("Diluted EPS", "Basic EPS", "DilutedEPS", "BasicEPS"):
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
    return sorted(out, key=lambda x: x[0], reverse=True)


def ttm_eps(stmt):
    """Sum the latest four reported quarterly EPS observations."""
    row = pick_eps_row(stmt)
    if row is None:
        return None
    vals = []
    for col in row.index:
        value = finite(row.get(col))
        if value is None:
            continue
        try:
            date = pd.Timestamp(col)
        except Exception:
            continue
        vals.append((date, value))
    vals.sort(key=lambda x: x[0], reverse=True)
    if len(vals) < 4:
        return None
    total = sum(v for _, v in vals[:4])
    return total if math.isfinite(total) else None


def price_on_or_before(history, target):
    if history is None or history.empty:
        return None
    idx = pd.DatetimeIndex(history.index).tz_localize(None)
    mask = idx.date <= target
    if not mask.any():
        return None
    return finite(history.iloc[mask.nonzero()[0][-1]]["Close"])


def fx_on_or_before(history, target):
    rate = price_on_or_before(history, target)
    return rate if rate and rate > 0 else None


def historical_pe(stmt, price_history, fx_history, financial_currency):
    eps = annual_eps(stmt)
    result = []
    for fiscal_date, eps_value in eps:
        price = price_on_or_before(price_history, fiscal_date)
        if price is None or price <= 0:
            continue

        # Yahoo may report Indonesian-company financials in USD while the
        # quoted share price is in IDR. Convert the historical price into the
        # financial-statement currency before calculating P/E.
        if str(financial_currency).upper() == "USD":
            fx = fx_on_or_before(fx_history, fiscal_date)
            if fx is None:
                continue
            price = price / fx

        pe = price / eps_value
        # Guard against obvious Yahoo unit/currency anomalies.
        if math.isfinite(pe) and 0 < pe < 300:
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

    # One FX history is shared by all IDX names whose financial statements
    # are reported in USD.
    fx_history = yf.Ticker("IDR=X").history(period="5y", auto_adjust=False)

    rows = []
    errors = []

    for _, r in u.iterrows():
        ticker = str(r["ticker"]).strip().upper()
        if not ticker:
            continue

        try:
            t = yf.Ticker(ticker + ".JK")
            info = t.info or {}
            current_pe = finite(info.get("trailingPE"))
            trailing_eps = finite(info.get("trailingEps"))
            # Yahoo can omit trailingEps for some IDX names even when quarterly EPS is available.
            if trailing_eps is None:
                try:
                    trailing_eps = ttm_eps(t.get_income_stmt(freq="quarterly"))
                except Exception:
                    trailing_eps = None
            financial_currency = str(
                info.get("financialCurrency")
                or info.get("currency")
                or "IDR"
            )

            history = t.history(period="5y", auto_adjust=False)
            if history is None or history.empty:
                raise ValueError("No price history")

            last_close = finite(history["Close"].dropna().iloc[-1])
            if current_pe is None and last_close and trailing_eps and trailing_eps > 0:
                current_pe = last_close / trailing_eps

            stmt = t.get_income_stmt(freq="yearly")
            pe_hist, eps_hist = historical_pe(
                stmt, history, fx_history, financial_currency
            )
            hist3 = [x for _, x in pe_hist if x > 0]
            # Use up to 3 valid annual observations. Newly listed names may
            # legitimately have only 2 years available; require at least 2
            # observations rather than dropping them unnecessarily.
            avg_pe = sum(hist3) / len(hist3) if len(hist3) >= 2 else None

            growth = None
            if len(eps_hist) >= 2:
                latest_eps = eps_hist[0][1]
                prior_eps = eps_hist[1][1]
                if prior_eps > 0:
                    growth = (latest_eps / prior_eps - 1) * 100

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
                "pe_history": [{"period": p, "pe": round(x, 2)} for p, x in pe_hist],
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
        "incomplete_count": sum(x["value_gap_score"] is None for x in rows) - len(errors),
        "error_count": len(errors),
        "formula": "(Average 3Y P/E - Current P/E) × EPS Growth (%)",
        "eps_growth_definition": "Annual EPS growth: latest fiscal-year EPS versus prior fiscal-year EPS; Yahoo trailing earningsGrowth used only as fallback",
        "historical_pe_definition": "Average of up to 3 valid annual P/E observations; at least 2 observations required, with USD financials converted using historical USD/IDR",
        "sources": ["Yahoo Finance / yfinance"],
        "errors": errors,
        "stocks": rows,
    }
    OUT.write_text(json.dumps(payload, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    print(f"Value Gap: {payload['valid_count']}/{payload['universe_count']} valid, asof {payload['asof']}, errors {payload['error_count']}")


if __name__ == "__main__":
    main()
