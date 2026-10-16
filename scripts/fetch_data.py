#!/usr/bin/env python3
"""Build daily screener data for SevenPercentCommunity.

Universe: current KOMPAS100 constituents stored in universe.csv.
OHLCV: Yahoo Finance via yfinance.
Output: data/screener.json consumed by index.html.
"""
import datetime as dt
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
UNIVERSE = ROOT / "universe.csv"
OUT = ROOT / "data" / "screener.json"
BENCH = "^JKSE"
BARS = 520  # approximately two years of IDX trading sessions
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


def download_symbols(symbols, attempts=3, start=None):
    # auto_adjust=False preserves raw OHLC suitable for a technical screener.
    # Retry transient Yahoo/network failures so one temporary outage does not
    # invalidate an otherwise healthy hourly build.
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            kwargs = dict(tickers=symbols, interval="1d", group_by="ticker", auto_adjust=False, actions=False, threads=True, progress=False)
            if start:
                kwargs["start"] = start
            else:
                kwargs["period"] = "2y"
            raw = yf.download(**kwargs)
            if raw is not None and not raw.empty:
                return raw
        except Exception as exc:
            last_error = exc
        if attempt < attempts:
            time.sleep(3 * attempt)
    if last_error:
        raise last_error
    return pd.DataFrame()


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

    # data/screener.json is the persistent history store. Existing history below
    # ~450 bars triggers a one-time two-year bootstrap; later runs update incrementally.
    previous = {}
    previous_bench = {}
    if OUT.exists():
        try:
            old_payload = json.loads(OUT.read_text(encoding="utf-8"))
            previous = {x.get("t"): x for x in old_payload.get("stocks", []) if x.get("t")}
            previous_bench = old_payload.get("benchmark_history") or {}
        except Exception as exc:
            print(f"Riwayat lama tidak dapat dibaca; bootstrap 2 tahun: {exc}")

    def incremental_start(date_values, min_rows=450):
        if not date_values or len(date_values) < min_rows:
            return None
        latest = dt.date.fromisoformat(date_values[-1])
        return (latest - dt.timedelta(days=7)).isoformat()

    bench_start = incremental_start(previous_bench.get("d", []))
    bench_raw = download_symbols([BENCH], start=bench_start)
    bench_new = extract(bench_raw, BENCH)
    if bench_new is None or bench_new.empty:
        print("Gagal mengambil IHSG.", file=sys.stderr)
        sys.exit(1)
    if previous_bench.get("d") and previous_bench.get("c"):
        old_idx = pd.to_datetime(previous_bench["d"])
        old_bench = pd.DataFrame({"Close": previous_bench["c"]}, index=old_idx)
        bench = pd.concat([old_bench, bench_new[["Close"]]]).groupby(level=0).last().sort_index()
    else:
        bench = bench_new[["Close"]].copy()
    bench = bench.tail(BARS)
    bench_close = bench["Close"]
    benchmark_history = {"d": [x.strftime("%Y-%m-%d") for x in bench.index], "c": [round(float(x), 2) for x in bench["Close"]]}
    stocks = []
    failed = []

    for start in range(0, len(universe), BATCH_SIZE):
        batch = universe[start:start + BATCH_SIZE]
        symbols = [f"{u['t']}.JK" for u in batch]
        print(f"Batch {start + 1}-{start + len(batch)} / {len(universe)}")
        batch_dates = [previous.get(u["t"], {}).get("d", []) for u in batch]
        if all(incremental_start(ds) for ds in batch_dates):
            start_date = min(incremental_start(ds) for ds in batch_dates)
        else:
            start_date = None
        try:
            raw = download_symbols(symbols, start=start_date)
        except Exception as exc:
            print(f"Batch gagal: {exc}", file=sys.stderr)
            failed.extend(u["t"] for u in batch)
            continue

        for u, symbol in zip(batch, symbols):
            df = extract(raw, symbol)
            if df is None or len(df) < 120:
                # Keep last known-good bars if this ticker temporarily fails.
                old = previous.get(u["t"])
                if old and len(old.get("d", [])) == len(old.get("c", [])) and old.get("c"):
                    stocks.append(old)
                    print("Using stored history for temporarily unavailable ticker:", u["t"])
                failed.append(u["t"])
                continue

            old = previous.get(u["t"], {})
            if old.get("d") and len(old.get("c", [])) == len(old.get("d", [])) and len(old.get("d", [])) >= 450:
                old_frame = pd.DataFrame({"Open": old.get("o", []), "High": old.get("h", []), "Low": old.get("l", []), "Close": old.get("c", []), "Volume": old.get("v", [])}, index=pd.to_datetime(old["d"]))
                merged = pd.concat([old_frame, df[["Open", "High", "Low", "Close", "Volume"]]])
                merged = merged[~merged.index.duplicated(keep="last")].sort_index().tail(BARS)
                d = merged
            else:
                d = df.tail(BARS)
            b = beta(d["Close"], bench_close)

            # Market cap is optional; leaving it null is safer than issuing
            # hundreds of slow per-ticker metadata calls to Yahoo.
            stocks.append({
                **u,
                "mc": old.get("mc"),
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
        "universe_name": "KOMPAS100",
        "universe_period": "2026-08-03 to 2027-01-29",
        "universe_count": len(universe),
        "success_count": len(stocks),
        "failed_count": len(failed),
        "benchmark_history": benchmark_history,
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
