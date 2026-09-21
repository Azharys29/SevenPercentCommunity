#!/usr/bin/env python3
"""Ambil data harian saham IDX (yfinance), hitung beta terhadap IHSG, tulis data/screener.json.

Dijalankan oleh GitHub Actions setiap hari bursa. Bisa juga dijalankan lokal:
    pip install yfinance pandas numpy
    python scripts/fetch_data.py
"""
import json, sys, time, datetime as dt
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
UNIVERSE = ROOT / "universe.csv"
OUT = ROOT / "data" / "screener.json"
BENCH = "^JKSE"          # IHSG
BARS = 320               # jumlah bar harian yang disimpan per saham
BETA_WINDOW = 252        # ~1 tahun bursa
MIN_OK_RATIO = 0.6       # batalkan penulisan jika terlalu banyak saham gagal


def load_universe():
    df = pd.read_csv(UNIVERSE, comment="#", dtype=str).fillna("")
    out = []
    for _, r in df.iterrows():
        t = r["ticker"].strip().upper()
        if not t:
            continue
        out.append({
            "t": t,
            "n": r["name"].strip() or t,
            "s": r["sector"].strip() or "Lainnya",
            "ix": [x.strip() for x in r["indices"].split("|") if x.strip()],
        })
    return out


def market_cap(sym):
    try:
        fi = yf.Ticker(sym).fast_info
        for k in ("market_cap", "marketCap"):
            try:
                v = fi[k]
                if v:
                    return float(v)
            except Exception:
                continue
    except Exception:
        pass
    return None


def calc_beta(close: pd.Series, bench: pd.Series):
    r = pd.concat([close.pct_change(), bench.pct_change()], axis=1, join="inner").dropna().tail(BETA_WINDOW)
    if len(r) < 120:
        return None
    var = r.iloc[:, 1].var()
    return float(r.iloc[:, 0].cov(r.iloc[:, 1]) / var) if var > 0 else None


def main():
    uni = load_universe()
    prev = {}
    if OUT.exists():
        try:
            prev = {s["t"]: s for s in json.loads(OUT.read_text())["stocks"]}
        except Exception:
            prev = {}

    symbols = [f"{u['t']}.JK" for u in uni]
    raw = yf.download(symbols + [BENCH], period="2y", interval="1d", group_by="ticker",
                      auto_adjust=False, actions=False, threads=True, progress=False)

    def frame(sym):
        try:
            df = raw[sym][["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"])
            return df[df["Volume"] > 0]          # buang hari tanpa transaksi
        except Exception:
            return None

    bench = frame(BENCH)
    if bench is None or bench.empty:
        print("Gagal mengambil IHSG; batal.", file=sys.stderr)
        sys.exit(1)
    bench_close = bench["Close"]

    stocks, failed = [], []
    for u, sym in zip(uni, symbols):
        df = frame(sym)
        if df is None or len(df) < 120:
            failed.append(u["t"])
            continue
        old = prev.get(u["t"], {})
        mc = market_cap(sym) or old.get("mc")
        beta = calc_beta(df["Close"], bench_close)
        if beta is None:
            beta = old.get("b")
        d = df.tail(BARS)
        stocks.append({
            **u,
            "mc": mc,
            "b": round(beta, 2) if beta is not None else None,
            "d": [x.strftime("%Y-%m-%d") for x in d.index],
            "o": [round(float(x), 2) for x in d["Open"]],
            "h": [round(float(x), 2) for x in d["High"]],
            "l": [round(float(x), 2) for x in d["Low"]],
            "c": [round(float(x), 2) for x in d["Close"]],
            "v": [int(x) for x in d["Volume"]],
        })
        time.sleep(0.15)

    print(f"Berhasil {len(stocks)}/{len(uni)} saham. Gagal: {failed or '-'}")
    if len(stocks) / max(len(uni), 1) < MIN_OK_RATIO:
        print("Terlalu banyak kegagalan; data lama dipertahankan.", file=sys.stderr)
        sys.exit(1)

    payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "asof": max(s["d"][-1] for s in stocks),
        "benchmark": BENCH,
        "stocks": stocks,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    print(f"Ditulis {OUT} ({OUT.stat().st_size / 1024:.0f} KB), data s.d. {payload['asof']}")


if __name__ == "__main__":
    main()
