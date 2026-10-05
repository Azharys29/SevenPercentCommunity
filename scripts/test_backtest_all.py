#!/usr/bin/env python3
"""Fail-closed validation for Phase D all-setup backtest."""
import json, math
from pathlib import Path
P=Path(__file__).resolve().parent.parent/"data/backtest-all.json"
assert P.exists(),"data/backtest-all.json missing"
d=json.loads(P.read_text())
assert isinstance(d,dict) and d.get("universe")=="KOMPAS100"
summary=d.get("summary"); ranking=d.get("ranking")
assert isinstance(summary,dict) and isinstance(ranking,list)
families={"TECHNICAL SIGNAL","TECHNICAL TRADE JOURNAL","EARLY BREAKOUT","EARLY PULLBACK"}
assert set(summary)==families
assert len(ranking)==len(families)
for name,x in summary.items():
    assert isinstance(x,dict)
    assert isinstance(x.get("count"),int) and x["count"]>=0
    for k in ["win_rate","tp1_rate","tp2_rate","sl_rate","timeout_rate","avg_return","avg_r","expectancy_r","best_r","worst_r","max_drawdown_r"]:
        if x.get(k) is not None:
            assert isinstance(x[k],(int,float)) and math.isfinite(x[k]),f"{name}: invalid {k}"
    if x["count"]:
        assert 0<=x["win_rate"]<=100
        assert 0<=x["sl_rate"]<=100
        assert x["best_r"]>=x["worst_r"]
diag=d.get("diagnostics",{})
for k in ["stocks","technical_candidates","journal_candidates","journal_rr_valid","early_breakout","early_pullback"]:
    assert isinstance(diag.get(k),int) and diag[k]>=0,k
assert diag["journal_rr_valid"]<=diag["journal_candidates"]
for name,events in d.get("events",{}).items():
    assert name in families and isinstance(events,list)
    for e in events:
        for k in ["ticker","signal_date","entry_price","return_pct","r","outcome"]:
            assert k in e
        assert all(isinstance(e[k],(int,float)) and math.isfinite(e[k]) for k in ["entry_price","return_pct","r"])
        assert e["outcome"] in {"WIN","LOSS","TP1","TP2","STOP LOSS","TIMEOUT"}
assert d.get("method",{}).get("lookahead_free") is True
print("Phase D all-setup backtest test: OK")
