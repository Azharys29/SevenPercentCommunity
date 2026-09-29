#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.build_backtest import pct, summarize
assert round(pct(100,110),2)==10
r=[{"returns":{"5":10,"10":5,"20":-2}},{"returns":{"5":-4,"10":6,"20":8}}]
assert summarize(r,5)["count"]==2 and summarize(r,5)["win_rate"]==50
assert summarize(r,10)["avg_return"]==5.5
print("backtest tests: OK")
