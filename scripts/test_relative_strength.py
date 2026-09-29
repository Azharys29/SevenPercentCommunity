#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.build_relative_strength import rank, ret
assert round(ret([100,110,120],2),2)==20
r=rank([10,20,30]); assert r[0]==0 and r[-1]==100
print("relative strength tests: OK")
