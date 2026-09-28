#!/usr/bin/env python3
import csv, json, statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNIVERSE = ROOT / "universe.csv"
SIGNALS = ROOT / "data" / "signals.json"
OUT = ROOT / "data" / "sector-rotation.json"

with UNIVERSE.open(encoding="utf-8") as f:
    sectors = {r["ticker"]: r["sector"] for r in csv.DictReader(f)}

data = json.loads(SIGNALS.read_text(encoding="utf-8"))
rows = data.get("signals", [])
groups = defaultdict(list)

for r in rows:
    sector = sectors.get(r.get("ticker"), "Unknown")
    if sector and sector != "Lainnya":
        groups[sector].append(r)

items = []
for sector, arr in groups.items():
    scores = [float(x.get("score", 0)) for x in arr]
    deltas = [float(x.get("score_delta", 0)) for x in arr]
    bullish = sum(x.get("signal") == "Bullish" for x in arr)
    bearish = sum(x.get("signal") == "Bearish" for x in arr)
    neutral = len(arr) - bullish - bearish
    avg = statistics.fmean(scores) if scores else 0
    med = statistics.median(scores) if scores else 0
    avg_delta = statistics.fmean(deltas) if deltas else 0
    breadth = (bullish - bearish) / len(arr) * 100 if arr else 0
    items.append({
        "sector": sector,
        "count": len(arr),
        "avg_score": round(avg, 2),
        "median_score": round(med, 2),
        "avg_score_delta": round(avg_delta, 2),
        "breadth": round(breadth, 1),
        "bullish": bullish,
        "neutral": neutral,
        "bearish": bearish,
        "bullish_pct": round(bullish / len(arr) * 100, 1) if arr else 0,
        "bearish_pct": round(bearish / len(arr) * 100, 1) if arr else 0,
        "stocks": sorted(
            [{"ticker": x["ticker"], "score": round(float(x.get("score", 0)), 2), "signal": x.get("signal"), "score_delta": round(float(x.get("score_delta", 0)), 2)}
             for x in arr],
            key=lambda x: x["score"], reverse=True
        ),
    })

if items:
    baseline = statistics.median(x["avg_score"] for x in items)
    for x in items:
        improving = x["avg_score_delta"] >= 0
        above = x["avg_score"] >= baseline
        if above and improving:
            phase = "Leading"
        elif not above and improving:
            phase = "Improving"
        elif above and not improving:
            phase = "Weakening"
        else:
            phase = "Lagging"
        x["phase"] = phase
        x["relative_score"] = round(x["avg_score"] - baseline, 2)
else:
    baseline = 0

phase_order = {"Leading": 0, "Improving": 1, "Weakening": 2, "Lagging": 3}
items.sort(key=lambda x: (phase_order[x["phase"]], -x["avg_score"], -x["breadth"]))

out = {
    "generated": datetime.now(timezone.utc).isoformat(),
    "asof": data.get("asof"),
    "universe": "KOMPAS100",
    "sector_count": len(items),
    "baseline_median_score": round(baseline, 2),
    "methodology": {
        "score": "rata-rata Technical Score saham dalam sektor",
        "acceleration": "rata-rata perubahan Technical Score harian",
        "breadth": "(jumlah Bullish - jumlah Bearish) / jumlah saham x 100",
        "phase": "Leading/Improving/Weakening/Lagging berdasarkan posisi average score terhadap median sektor dan arah score_delta"
    },
    "sectors": items,
}
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Sector rotation: {len(items)} sectors, asof {data.get('asof')}")
