#!/usr/bin/env python3
"""Build a rolling catalyst calendar for the KOMPAS100 universe.

Automatic source: Yahoo Finance via yfinance earnings calendars.
Manual source: data/catalysts-manual.json for curated IDX/company events.
The dashboard window is the next 30 calendar days from the market-data as-of date.
"""
import datetime as dt, json, time
from pathlib import Path
import yfinance as yf

ROOT=Path(__file__).resolve().parent.parent
UNIVERSE=ROOT/"universe.csv"
SCREENER=ROOT/"data/screener.json"
MANUAL=ROOT/"data/catalysts-manual.json"
OUT=ROOT/"data/catalysts.json"

def parse_date(v):
    if v is None:return None
    if isinstance(v,dt.datetime): return v.date()
    if isinstance(v,dt.date): return v
    s=str(v)
    for f in ("%Y-%m-%d","%Y-%m-%d %H:%M:%S"):
        try:return dt.datetime.strptime(s[:19],f).date()
        except ValueError: pass
    return None

def main():
    import csv
    universe={}
    with UNIVERSE.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            t=(row.get("ticker") or row.get("Ticker") or "").strip().upper()
            if t: universe[t]=row
    screen=json.loads(SCREENER.read_text(encoding="utf-8"))
    asof=parse_date(screen["asof"]) or dt.date.today()
    start=asof+dt.timedelta(days=1); end=asof+dt.timedelta(days=30)
    events=[]
    errors=[]
    for ticker,meta in universe.items():
        yf_ticker=ticker+".JK"
        try:
            cal=yf.Ticker(yf_ticker).calendar
            if cal is not None and not cal.empty:
                vals={}
                for key in cal.index:
                    v=cal.loc[key]
                    if hasattr(v,"iloc"): v=v.iloc[0]
                    vals[str(key).lower()]=v
                ed=vals.get("earnings date") or vals.get("earnings_dates")
                if isinstance(ed,(list,tuple)) and ed: ed=ed[0]
                d=parse_date(ed)
                if d and start<=d<=end:
                    events.append({
                        "date":d.isoformat(),"ticker":ticker,"name":meta.get("name") or meta.get("Nama") or ticker,
                        "sector":meta.get("sector") or "Lainnya","type":"Earnings","title":"Perkiraan tanggal earnings",
                        "source":"Yahoo Finance / yfinance","source_url":"https://finance.yahoo.com/quote/"+yf_ticker+"/",
                        "importance":"High","status":"automatic"
                    })
        except Exception as e:
            errors.append(ticker)
        time.sleep(0.05)
    manual=[]
    if MANUAL.exists():
        try: manual=json.loads(MANUAL.read_text(encoding="utf-8"))
        except Exception: manual=[]
    for e in manual:
        d=parse_date(e.get("date"))
        if not d or not (start<=d<=end): continue
        t=str(e.get("ticker","")).upper()
        meta=universe.get(t,{})
        events.append({
            "date":d.isoformat(),"ticker":t,"name":e.get("name") or meta.get("name") or t or "Market",
            "sector":e.get("sector") or meta.get("sector") or "Market","type":e.get("type","Corporate"),
            "title":e.get("title","Catalyst"),"source":e.get("source","Manual"),
            "source_url":e.get("source_url",""),"importance":e.get("importance","Medium"),"status":"manual"
        })
    # De-duplicate by date/ticker/type/title.
    uniq={}
    for e in events: uniq[(e["date"],e["ticker"],e["type"],e["title"])]=e
    events=sorted(uniq.values(),key=lambda x:(x["date"], {"High":0,"Medium":1,"Low":2}.get(x["importance"],3),x["ticker"]))
    by_date={}
    for e in events: by_date.setdefault(e["date"],[]).append(e)
    payload={
        "generated":dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "asof":asof.isoformat(),"window_start":start.isoformat(),"window_end":end.isoformat(),
        "universe":"KOMPAS100","event_count":len(events),"automatic_errors":errors,
        "sources":["Yahoo Finance / yfinance earnings calendar","data/catalysts-manual.json"],
        "events":events,"by_date":by_date
    }
    OUT.write_text(json.dumps(payload,separators=(",",":"),ensure_ascii=False),encoding="utf-8")
    print(f"Catalyst Calendar: {len(events)} events, window {start} to {end}, yahoo errors {len(errors)}")

if __name__=="__main__": main()
