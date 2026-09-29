#!/usr/bin/env python3
import sys,datetime as dt
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from scripts.build_catalysts import parse_date
assert parse_date("2026-10-01")==dt.date(2026,10,1)
assert parse_date(dt.datetime(2026,10,1,12,0))==dt.date(2026,10,1)
assert parse_date(None) is None
print("Earnings Calendar tests: PASS")
