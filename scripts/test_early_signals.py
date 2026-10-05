#!/usr/bin/env python3
"""Fail-closed checks for Early Signals output."""
import json, math
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
p=ROOT/"data/early-signals.json"
assert p.exists(),"data/early-signals.json missing"
d=json.loads(p.read_text())
assert isinstance(d,dict)
assert isinstance(d.get("items"),list)
assert d.get("candidate_count")==len(d["items"])
allowed_setup={"PULLBACK","BREAKOUT"}; allowed_stage={"READY","PREPARE"}; allowed_grade={"A+","A","B","WATCH"}
seen=set()
for x in d["items"]:
    for k in ["ticker","setup","stage","grade","setup_score","price","rsi","rvol","atr14","entry","stop_loss","tp1","tp2","risk_pct","rr_tp1","rr_tp2"]:
        assert k in x,f"missing {k}"
    assert x["ticker"] not in seen,f"duplicate ticker {x['ticker']}"; seen.add(x["ticker"])
    assert x["setup"] in allowed_setup
    assert x["stage"] in allowed_stage
    assert x["grade"] in allowed_grade
    assert 0 <= float(x["setup_score"]) <= 100
    vals=[x[k] for k in ["price","rsi","rvol","atr14","entry","stop_loss","tp1","tp2","risk_pct","rr_tp1","rr_tp2"]]
    assert all(isinstance(v,(int,float)) and math.isfinite(v) for v in vals)
    assert x["entry"] > x["stop_loss"] and x["tp1"] > x["entry"] and x["tp2"] > x["tp1"]
    assert x["atr14"] > 0 and x["risk_pct"] > 0
    assert x["rr_tp1"] >= 1.5 and x["rr_tp2"] > x["rr_tp1"]
diag=d.get("diagnostics",{})
for k in ["universe","bullish","trend_ok","pullback","breakout","volume_ok","rr_ok","candidates"]:
    assert isinstance(diag.get(k),int) and diag[k]>=0,k
assert diag["bullish"] <= diag["universe"]
assert diag["trend_ok"] <= diag["bullish"]
assert diag["candidates"] == d["candidate_count"]
print(f"Early Signals test OK: {d['candidate_count']} candidates")
