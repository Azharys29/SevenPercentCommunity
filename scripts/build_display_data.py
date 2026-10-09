#!/usr/bin/env python3
"""Build compact presentation feed from raw screener history without changing analysis inputs."""
import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "screener.json"
OUT = ROOT / "data" / "display.json"


def pct(values, n):
    if len(values) <= n or not values[-1-n]:
        return None
    return round((values[-1] / values[-1-n] - 1) * 100, 2)


def main():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    rows = []
    for stock in raw.get("stocks", []):
        closes = stock.get("c") or []
        if not closes:
            continue
        dates = stock.get("d") or []
        last = closes[-1]
        prev = closes[-2] if len(closes) > 1 else None
        year = str(raw.get("asof", ""))[:4]
        ytd_i = next((i for i, day in enumerate(dates) if day[:4] == year), None)
        rows.append({
            "ticker": stock.get("t"),
            "name": stock.get("n"),
            "sector": stock.get("s", "Lainnya"),
            "indices": stock.get("ix", []),
            "price": round(last, 2),
            "change_1d": round((last / prev - 1) * 100, 2) if prev else None,
            "return_1m": pct(closes, 21),
            "return_ytd": round((last / closes[ytd_i] - 1) * 100, 2) if ytd_i is not None and closes[ytd_i] else None,
            "volume": (stock.get("v") or [None])[-1],
            "beta": stock.get("b"),
        })
    payload = {
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "asof": raw.get("asof"),
        "source": "data/screener.json",
        "purpose": "compact display feed; raw OHLCV history remains the analysis source",
        "universe_count": len(rows),
        "stocks": rows,
    }
    OUT.write_text(json.dumps(payload, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    print(f"Display feed: {len(rows)} stocks, {OUT.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
