#!/usr/bin/env python3
"""Basic validation for the Signal Intelligence data contract."""
import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"data"/"signal-intelligence.json"
d=json.loads(p.read_text(encoding="utf-8"))
assert d["universe_count"]>0
assert len(d["signals"])==8, f"expected 8 modules, got {len(d['signals'])}"
assert d["stocks"]
for s in d["stocks"]:
 assert 0 <= s["factor_score"] <= 100
 assert 0 <= s["factor_coverage"] <= s["factor_total"] == 6
 assert isinstance(s["explanation"],list) and s["explanation"]
for r in next(x for x in d["signals"] if x["id"]=="validation")["results"]:
 assert r["horizon_days"] in (5,20)
 assert r["sample"]>=0
print(f"Signal Intelligence validation PASS: {d['universe_count']} stocks / 8 modules")
