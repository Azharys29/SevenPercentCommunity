#!/usr/bin/env python3
"""Build a rolling earnings calendar for the KOMPAS100 universe.

Source: Yahoo Finance via yfinance earnings calendars only.
The dashboard window is the next 30 calendar days from the market-data as-of date.
"""
import datetime as dt, json, time
from pathlib import Path
import yfinance as yf

ROOT=Path(__file__).resolve().parent.parent
UNIVERSE=ROOT/"universe.csv"
SCREENER=ROOT/"data/screener.json"
OUT=ROOT/"data/catalysts.json"

def parse_date(v):
    if v is None:
        return None
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    s=str(v)
    for f in ("%Y-%m-%d","%Y-%m-%d %H:%M:%S"):
        try:
            return dt.datetime.strptime(s[:19],f).date()
        except ValueError:
            pass
    return None

def main():
    import csv
    universe={}
    with UNIVERSE.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            t=(row.get("ticker") or row.get("Ticker") or "").strip().upper()
            if t:
                universe[t]=row

    screen=json.loads(SCREENER.read_text(encoding="utf-8"))
    asof=parse_date(screen["asof"]) or dt.date.today()
    start=asof+dt.timedelta(days=1)
    end=asof+dt.timedelta(days=30)

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
                    if hasattr(v,"iloc"):
                        v=v.iloc[0]
                    vals[str(key).lower()]=v

                ed=vals.get("earnings date") or vals.get("earnings_dates")
                if isinstance(ed,(list,tuple)) and ed:
                    ed=ed[0]

                d=parse_date(ed)
                if d and start<=d<=end:
                    events.append({
                        "date":d.isoformat(),
                        "ticker":ticker,
                        "name":meta.get("name") or meta.get("Nama") or ticker,
                        "sector":meta.get("sector") or "Lainnya",
                        "type":"Earnings",
                        "title":"Perkiraan tanggal earnings",
                        "source":"Yahoo Finance / yfinance",
                        "source_url":"https://finance.yahoo.com/quote/"+yf_ticker+"/",
                        "importance":"High",
                        "status":"automatic"
                    })
        except Exception:
            errors.append(ticker)
        time.sleep(0.05)

    # De-duplicate by date/ticker.
    uniq={}
    for e in events:
        uniq[(e["date"],e["ticker"])]=e
    events=sorted(uniq.values(),key=lambda x:(x["date"],x["ticker"]))

    by_date={}
    for e in events:
        by_date.setdefault(e["date"],[]).append(e)

    payload={
        "generated":dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "asof":asof.isoformat(),
        "window_start":start.isoformat(),
        "window_end":end.isoformat(),
        "universe":"KOMPAS100",
        "event_count":len(events),
        "automatic_errors":errors,
        "sources":["Yahoo Finance / yfinance earnings calendar"],
        "events":events,
        "by_date":by_date
    }
    OUT.write_text(json.dumps(payload,separators=(",",":"),ensure_ascii=False),encoding="utf-8")
    print(f"Earnings Calendar: {len(events)} events, window {start} to {end}, yahoo errors {len(errors)}")

if __name__=="__main__":
    main()
