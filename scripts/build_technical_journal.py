#!/usr/bin/env python3
"""Build Fibonacci-based technical trade journal from the deterministic signal engine."""
import datetime as dt
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
SCREENER=ROOT/"data/screener.json"
SIGNALS=ROOT/"data/signals.json"
OUT=ROOT/"data/technical-journal.json"

MIN_SCORE=25
MIN_AGREE=3
LOOKBACK=90
PIVOT=3
MIN_RR=1.5
MAX_ACTIVE_DAYS=20

def finite(x):
    return isinstance(x,(int,float)) and math.isfinite(x)

def pivots(h,l,n=3):
    ph=[]; pl=[]
    for i in range(n,len(h)-n):
        hw=h[i-n:i+n+1]; lw=l[i-n:i+n+1]
        if finite(h[i]) and h[i]==max(hw) and h[i]>max(h[i-n:i]):
            ph.append(i)
        if finite(l[i]) and l[i]==min(lw) and l[i]<min(l[i-n:i]):
            pl.append(i)
    return ph,pl

def fib_setup(stock,signal):
    c=list(map(float,stock["c"])); h=list(map(float,stock["h"])); l=list(map(float,stock["l"]))
    if len(c)<LOOKBACK: return None
    start=max(0,len(c)-LOOKBACK)
    hh=h[start:]; ll=l[start:]; cc=c[start:]
    ph,pl=pivots(hh,ll,PIVOT)
    if signal=="Bullish":
        highs=[i for i in ph if i>=PIVOT]
        if not highs: return None
        hi=highs[-1]
        lows=[i for i in pl if i<hi]
        if not lows: return None
        lo=lows[-1]
        low=ll[lo]; high=hh[hi]
        if high<=low: return None
        rng=high-low
        entry=c[-1]
        tp1=high+rng*0.272
        tp2=high+rng*0.618
        sl=low
        direction="LONG"
    elif signal=="Bearish":
        lows=[i for i in pl if i>=PIVOT]
        if not lows: return None
        lo=lows[-1]
        highs=[i for i in ph if i<lo]
        if not highs: return None
        hi=highs[-1]
        high=hh[hi]; low=ll[lo]
        if high<=low: return None
        rng=high-low
        entry=c[-1]
        tp1=low-rng*0.272
        tp2=low-rng*0.618
        sl=high
        direction="SHORT"
    else:
        return None
    risk=abs(entry-sl)
    reward=abs(tp1-entry)
    rr=reward/risk if risk else 0
    if risk<=0 or reward<=0 or rr<MIN_RR: return None
    if direction=="LONG" and entry>=tp2: return None
    if direction=="SHORT" and entry<=tp2: return None
    return {
        "direction":direction,
        "swing_low":round(low,2),
        "swing_high":round(high,2),
        "fib_range":round(rng,2),
        "fib_1272":round(tp1,2),
        "fib_1618":round(tp2,2),
        "entry":round(entry,2),
        "stop_loss":round(sl,2),
        "tp1":round(tp1,2),
        "tp2":round(tp2,2),
        "risk_pct":round(risk/entry*100,2),
        "rr_tp1":round(rr,2),
        "rr_tp2":round(abs(tp2-entry)/risk,2),
        "anchor_low_index":start+lo,
        "anchor_high_index":start+hi
    }

def touch_status(direction,high,low,entry,tp1,tp2,sl,entered):
    if not entered:
        if direction=="LONG" and high>=entry and low<=entry: entered=True
        if direction=="SHORT" and low<=entry and high>=entry: entered=True
        if not entered: return "WAITING ENTRY",False,False,False
    if direction=="LONG":
        tp2hit=high>=tp2; tp1hit=high>=tp1; slhit=low<=sl
    else:
        tp2hit=low<=tp2; tp1hit=low<=tp1; slhit=high>=sl
    if tp2hit and slhit: return "TP2 & SL TOUCHED",True,True,True
    if tp1hit and slhit: return "TP1 & SL TOUCHED",True,True,True
    if tp2hit: return "TP2 HIT",True,True,False
    if tp1hit: return "TP1 HIT",True,False,False
    if slhit: return "STOP LOSS HIT",True,False,True
    return "ENTRY HIT",True,False,False

def main():
    screener=json.loads(SCREENER.read_text())
    signals=json.loads(SIGNALS.read_text())
    old=json.loads(OUT.read_text()) if OUT.exists() else {"generated":None,"trades":[]}
    trades=old.get("trades",[])
    by_id={x.get("setup_id"):x for x in trades if x.get("setup_id")}

    stocks={x["t"]:x for x in screener.get("stocks",[])}
    sigs=signals.get("signals",[])
    today=signals.get("asof") or screener.get("asof")
    new_count=0

    for s in sigs:
        if s.get("signal") not in ("Bullish","Bearish"): continue
        eligible = bool(s.get("new_bullish")) or (s.get("signal")=="Bearish" and bool(s.get("signal_changed"))) or s.get("previous_signal") is None
        if not eligible: continue
        if float(s.get("score",0)) < MIN_SCORE and s.get("signal")=="Bullish": continue
        if float(s.get("score",0)) > -MIN_SCORE and s.get("signal")=="Bearish": continue
        if int(s.get("agree",0)) < MIN_AGREE: continue
        stock=stocks.get(s["ticker"])
        if not stock: continue
        setup=f'{s["ticker"]}|{s["signal"]}|{s.get("asof")}|{s.get("score")}'
        if setup in by_id: continue
        fib=fib_setup(stock,s["signal"])
        if not fib: continue
        trade={
            "setup_id":setup,"ticker":s["ticker"],"name":s.get("name",s["ticker"]),
            "signal":s["signal"],"direction":fib["direction"],"signal_date":s.get("asof"),
            "created_at":dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "score":s.get("score"),"strength":s.get("strength"),"confluence":s.get("agree"),
            **fib,"status":"WAITING ENTRY","entry_hit":False,"tp1_hit":False,"tp2_hit":False,
            "sl_hit":False,"closed":False,"close_date":None,"close_price":None
        }
        by_id[setup]=trade; new_count+=1

    # Rebuild the state of active trades using available daily OHLC.
    for trade in by_id.values():
        if trade.get("closed"): continue
        stock=stocks.get(trade["ticker"])
        if not stock: continue
        dates=stock.get("d",[]); highs=stock.get("h",[]); lows=stock.get("l",[])
        start_date=trade.get("signal_date")
        try: start_idx=dates.index(start_date)
        except ValueError: start_idx=max(0,len(dates)-1)
        entered=bool(trade.get("entry_hit"))
        status=trade.get("status","WAITING ENTRY")
        for i in range(start_idx,len(dates)):
            high=float(highs[i]); low=float(lows[i])
            day_status,entered,tp1hit,slhit=touch_status(trade["direction"],high,low,trade["entry"],trade["tp1"],trade["tp2"],trade["stop_loss"],entered)
            trade["entry_hit"]=entered
            trade["tp1_hit"]=trade.get("tp1_hit",False) or tp1hit or day_status.startswith("TP1") or day_status.startswith("TP2")
            trade["tp2_hit"]=trade.get("tp2_hit",False) or day_status.startswith("TP2")
            trade["sl_hit"]=trade.get("sl_hit",False) or slhit or "SL" in day_status or day_status=="STOP LOSS HIT"
            if day_status=="TP2 & SL TOUCHED": status=day_status
            elif day_status=="TP1 & SL TOUCHED": status=day_status
            elif day_status=="STOP LOSS HIT": status=day_status
            elif day_status=="TP2 HIT": status=day_status
            elif trade["tp1_hit"]: status="TP1 HIT"
            elif entered: status="ENTRY HIT"
            else: status="WAITING ENTRY"
            trade["status"]=status
            if status in ("TP2 HIT","TP2 & SL TOUCHED","STOP LOSS HIT","TP1 & SL TOUCHED"):
                trade["closed"]=True; trade["close_date"]=dates[i]
                if status.startswith("TP2"): trade["close_price"]=trade["tp2"]
                elif status.startswith("TP1"): trade["close_price"]=trade["tp1"]
                else: trade["close_price"]=trade["stop_loss"]
                break
        if not trade.get("closed") and trade.get("signal_date") and dates:
            try:
                age=len(dates)-1-dates.index(trade["signal_date"])
            except ValueError: age=0
            if age>=MAX_ACTIVE_DAYS:
                trade["status"]="EXPIRED"; trade["closed"]=True; trade["close_date"]=dates[-1]; trade["close_price"]=float(stock["c"][-1])

    trades=sorted(by_id.values(),key=lambda x:(x.get("signal_date") or "",x.get("ticker") or ""),reverse=True)
    payload={"generated":dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),"asof":today,"trade_count":len(trades),"active_count":sum(not x.get("closed") for x in trades),"new_count":new_count,"trades":trades}
    OUT.write_text(json.dumps(payload,separators=(",",":"),allow_nan=False))
    print(json.dumps({"trade_count":payload["trade_count"],"active_count":payload["active_count"],"new_count":new_count}))

if __name__=="__main__": main()
