#!/usr/bin/env python3
"""Build daily screener data for SevenPercentCommunity.

Universe: the checked-in universe.csv. The initial universe intentionally excludes
rows marked speculative in the seed list and is kept small enough for GitHub Actions.
OHLCV: Yahoo Finance via yfinance.
Output: data/screener.json consumed by index.html.
"""
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
UNIVERSE = ROOT / "universe.csv"
OUT = ROOT / "data" / "screener.json"
BENCH = "^JKSE"
BARS = 320
BETA_WINDOW = 252
BATCH_SIZE = 60
MIN_OK_RATIO = 0.45


def load_universe():
    df = pd.read_csv(UNIVERSE, dtype=str).fillna("")
    required = {"ticker", "name", "sector", "indices"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"universe.csv missing columns: {sorted(missing)}")
    rows = []
    for _, r in df.iterrows():
        t = r["ticker"].strip().upper()
        if not t:
            continue
        rows.append({
            "t": t,
            "n": r["name"].strip() or t,
            "s": r["sector"].strip() or "Lainnya",
            "ix": [x.strip() for x in r["indices"].split("|") if x.strip()],
        })
    return rows


def beta(stock_close, bench_close):
    r = pd.concat(
        [stock_close.pct_change(), bench_close.pct_change()],
        axis=1,
        join="inner",
    ).dropna().tail(BETA_WINDOW)
    if len(r) < 120:
        return None
    var = float(r.iloc[:, 1].var())
    if not np.isfinite(var) or var <= 0:
        return None
    v = float(r.iloc[:, 0].cov(r.iloc[:, 1]) / var)
    return round(v, 2) if np.isfinite(v) else None


def download_symbols(symbols):
    # auto_adjust=False preserves raw OHLC suitable for a technical screener.
    return yf.download(
        symbols,
        period="2y",
        interval="1d",
        group_by="ticker",
        auto_adjust=False,
        actions=False,
        threads=True,
        progress=False,
    )


def extract(raw, symbol):
    try:
        if isinstance(raw.columns, pd.MultiIndex):
            if symbol not in raw.columns.get_level_values(0):
                return None
            df = raw[symbol][["Open", "High", "Low", "Close", "Volume"]].copy()
        else:
            df = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
        df = df.dropna(subset=["Close"])
        if "Volume" in df:
            df = df[df["Volume"].fillna(0) > 0]
        return df
    except Exception:
        return None


def main():
    universe = load_universe()
    if not universe:
        raise RuntimeError("universe.csv is empty")

    # IHSG once, then stock data in batches to reduce timeout/rate-limit risk.
    bench_raw = download_symbols([BENCH])
    bench = extract(bench_raw, BENCH)
    if bench is None or bench.empty:
        print("Gagal mengambil IHSG.", file=sys.stderr)
        sys.exit(1)

    bench_close = bench["Close"]
    stocks = []
    failed = []

    for start in range(0, len(universe), BATCH_SIZE):
        batch = universe[start:start + BATCH_SIZE]
        symbols = [f"{u['t']}.JK" for u in batch]
        print(f"Batch {start + 1}-{start + len(batch)} / {len(universe)}")
        try:
            raw = download_symbols(symbols)
        except Exception as exc:
            print(f"Batch gagal: {exc}", file=sys.stderr)
            failed.extend(u["t"] for u in batch)
            continue

        for u, symbol in zip(batch, symbols):
            df = extract(raw, symbol)
            if df is None or len(df) < 120:
                failed.append(u["t"])
                continue

            d = df.tail(BARS)
            b = beta(df["Close"], bench_close)

            # Market cap is optional; leaving it null is safer than issuing
            # hundreds of slow per-ticker metadata calls to Yahoo.
            stocks.append({
                **u,
                "mc": None,
                "b": b,
                "d": [x.strftime("%Y-%m-%d") for x in d.index],
                "o": [round(float(x), 2) for x in d["Open"]],
                "h": [round(float(x), 2) for x in d["High"]],
                "l": [round(float(x), 2) for x in d["Low"]],
                "c": [round(float(x), 2) for x in d["Close"]],
                "v": [int(x) if np.isfinite(x) else 0 for x in d["Volume"]],
            })

    ratio = len(stocks) / max(len(universe), 1)
    print(f"Berhasil {len(stocks)}/{len(universe)} saham ({ratio:.1%}). Gagal: {len(failed)}")
    if ratio < MIN_OK_RATIO:
        print("Terlalu banyak kegagalan; tidak menimpa data.", file=sys.stderr)
        sys.exit(1)

    asof = max(s["d"][-1] for s in stocks)
    payload = {
        "mode": "live",
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "asof": asof,
        "benchmark": BENCH,
        "universe_count": len(universe),
        "success_count": len(stocks),
        "failed_count": len(failed),
        "stocks": stocks,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(payload, separators=(",", ":"), allow_nan=False),
        encoding="utf-8",
    )
    print(f"Ditulis {OUT} ({OUT.stat().st_size / 1024:.0f} KB), data s.d. {asof}")


if __name__ == "__main__":
    main()
