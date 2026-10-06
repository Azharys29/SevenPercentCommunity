#!/usr/bin/env python3
import importlib.util,pathlib
p=pathlib.Path(__file__).with_name("build_market_intelligence.py"); s=importlib.util.spec_from_file_location("mi",p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
assert m.market_sentiment(62,4,4)=="Strong Positive"
assert m.market_sentiment(42,3,4)=="Positive"
assert m.market_sentiment(10,2,4)=="Neutral"
assert m.market_sentiment(-40,3,4)=="Strong Negative"
assert m.news_sentiment("Laba tumbuh 20%","")=="Positif"
assert m.news_sentiment("Laba turun dan private placement","")=="Campuran"
print("Market Intelligence tests: PASS")

from datetime import datetime, timezone, timedelta
from email.utils import format_datetime
now=datetime.now(timezone.utc).replace(microsecond=0)
assert m.is_recent_news(format_datetime(now-timedelta(days=13)),now)
assert m.is_recent_news(format_datetime(now-timedelta(days=14)),now)
assert not m.is_recent_news(format_datetime(now-timedelta(days=14,seconds=1)),now)
assert not m.is_recent_news(format_datetime(now-timedelta(days=30)),now)
assert not m.is_recent_news("",now)
assert not m.is_recent_news("not a date",now)
print("Market Intelligence 14-day news cutoff tests: PASS")
