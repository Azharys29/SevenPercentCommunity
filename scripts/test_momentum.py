#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from scripts.build_momentum import clamp,percentile_rank,ret,rsi_regime,sma
assert round(ret([100,102,105],2),2)==5.0
assert round(sma([1,2,3,4,5],3),2)==4.0
assert percentile_rank([10,20,30])==[0.0,50.0,100.0]
assert clamp(120)==100 and clamp(-10)==0
assert rsi_regime(60)>rsi_regime(45)
assert rsi_regime(70)>=rsi_regime(85)
print("Momentum Dashboard tests: PASS")
