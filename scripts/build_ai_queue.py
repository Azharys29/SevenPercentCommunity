#!/usr/bin/env python3
"""Build a deterministic AI-research queue from technical signal transitions."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
SIGNALS=ROOT/"data/signals.json"
OUT=ROOT/"data/ai-research.json"

def main():
    s=json.loads(SIGNALS.read_text())
    existing={x.get("ticker"): x for x in json.loads(OUT.read_text()).get("queue",[])} if OUT.exists() else {}
    queue=[]
    for x in s.get("signals",[]):
        if not x.get("ai_candidate"):
            continue
        queue.append({
            "ticker": x["ticker"],
            "name": x.get("name",""),
            "asof": x.get("asof"),
            "created_at": s.get("generated"),
            "score": x.get("score"),
            "score_delta": x.get("score_delta"),
            "signal": x.get("signal"),
            "strength": x.get("strength"),
            "confluence": f'{x.get("agree",0)}/{x.get("total",0)}',
            "rsi": x.get("rsi"),
            "stoch_k": x.get("stoch_k"),
            "stoch_d": x.get("stoch_d"),
            "macd_hist_pct": x.get("macd_hist_pct"),
            "rvol": x.get("rvol"),
            "status": "PENDING_RESEARCH",
            "researched_at": None,
            "narrative": None,
            "catalysts": [],
            "risks": [],
            "sentiment": None,
            "sources": []
        })
    # Keep explicitly marked demo research cards visible for website preview.
    for x in existing.values():
        if x.get("demo") and x.get("ticker") not in {q.get("ticker") for q in queue}:
            queue.append(x)
    payload={
        "generated": s.get("generated"),
        "asof": s.get("asof"),
        "queue_count": len(queue),
        "queue": queue
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",",":")))
    print(json.dumps({"queue_count":len(queue)}))

if __name__=="__main__":
    main()
