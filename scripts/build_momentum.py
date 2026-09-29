#!/usr/bin/env python3
"""Build a transparent Momentum Dashboard for the KOMPAS100 universe."""
import datetime as dt
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
DATA=ROOT/"data/screener.json"
SIGNALS=ROOT/"data/signals.json"
OUT=ROOT/"data/momentum.json"

def finite(x): return isinstance(x,(int,float)) and math.isfinite(x)
def ret(c,n):
    return (c[-1]/c[-1-n]-1)*100 if len(c)>n and finite(c[-1-n]) and c[-1-n] else None
def sma(c,n):
    w=c[-n:]
    return sum(w)/n if len(c)>=n and all(finite(x) for x in w) else None
def percentile_rank(values):
    valid=sorted(x for x in values if x is not None)
    if not valid:return [None]*len(values)
    out=[]
    for x in values:
        if x is None: out.append(None)
        else:
            pos=sum(v<=x for v in valid)-1
            out.append(round(100*pos/max(len(valid)-1,1),1))
    return out
def clamp(x,lo=0.0,hi=100.0): return max(lo,min(hi,x))
def rsi_regime(rsi):
    if rsi is None:return 50.0
    if rsi<40:return clamp(rsi/40*35)
    if rsi<50:return 35+(rsi-40)*1.5
    if rsi<=70:return 50+(rsi-50)*2.0
    if rsi<=80:return 90-(rsi-70)*1.5
    return 60

def main():
    data=json.loads(DATA.read_text(encoding="utf-8"))
    sd=json.loads(SIGNALS.read_text(encoding="utf-8")) if SIGNALS.exists() else {"signals":[]}
    sm={x["ticker"]:x for x in sd.get("signals",[])}
    rows=[]
    for s in data["stocks"]:
        c=[float(x) for x in s["c"]]
        if len(c)<200: continue
        sig=sm.get(s["t"],{})
        ma20,ma50,ma200=sma(c,20),sma(c,50),sma(c,200)
        r5,r20=ret(c,5),ret(c,20)
        price=c[-1]
        flags=[
            ma20 is not None and price>ma20,
            ma50 is not None and price>ma50,
            ma200 is not None and price>ma200,
            ma20 is not None and ma50 is not None and ma20>ma50,
            ma50 is not None and ma200 is not None and ma50>ma200,
        ]
        rows.append({
            "ticker":s["t"],"name":s["n"],"sector":s.get("s","Lainnya"),"price":round(price,2),
            "return_5d":round(r5,2) if r5 is not None else None,
            "return_20d":round(r20,2) if r20 is not None else None,
            "ma20":round(ma20,2) if ma20 is not None else None,
            "ma50":round(ma50,2) if ma50 is not None else None,
            "ma200":round(ma200,2) if ma200 is not None else None,
            "above_ma20":flags[0],"above_ma50":flags[1],"above_ma200":flags[2],
            "ma20_gt_ma50":flags[3],"ma50_gt_ma200":flags[4],"trend_points":sum(flags),
            "technical_score":sig.get("score"),"signal":sig.get("signal"),"strength":sig.get("strength"),
            "confluence":sig.get("agree"),"rsi":sig.get("rsi"),"stoch_k":sig.get("stoch_k"),
            "stoch_d":sig.get("stoch_d"),"macd_hist_pct":sig.get("macd_hist_pct"),"rvol":sig.get("rvol")
        })
    r5=percentile_rank([x["return_5d"] for x in rows]); r20=percentile_rank([x["return_20d"] for x in rows])
    for x,p5,p20 in zip(rows,r5,r20):
        tech=clamp(((x["technical_score"] or 0)+100)/2)
        volume=clamp(((x["rvol"] or .5)-.75)/1.25*100)
        rs=rsi_regime(x["rsi"])
        trend=x["trend_points"]/5*100
        score=(p5 or 50)*.20+(p20 or 50)*.20+tech*.25+trend*.20+volume*.10+rs*.05
        x.update({
            "trend_score":round(trend,1),"return_5d_rank":p5,"return_20d_rank":p20,
            "rsi_regime_score":round(rs,1),"volume_score":round(volume,1),"momentum_score":round(score,1),
            "momentum_label":"Explosive" if score>=75 else "Strong" if score>=60 else "Positive" if score>=45 else "Neutral" if score>=30 else "Weak"
        })
    rows.sort(key=lambda x:x["momentum_score"],reverse=True)
    for i,x in enumerate(rows,1): x["rank"]=i
    avg5=sum(x["return_5d"] for x in rows if x["return_5d"] is not None)/max(sum(x["return_5d"] is not None for x in rows),1)
    avg20=sum(x["return_20d"] for x in rows if x["return_20d"] is not None)/max(sum(x["return_20d"] is not None for x in rows),1)
    payload={
        "generated":dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),"asof":data["asof"],
        "universe":"KOMPAS100","universe_count":len(rows),
        "method":{"weights":{"5D return percentile":20,"20D return percentile":20,"technical score":25,"MA trend alignment":20,"RVOL":10,"RSI regime":5},
                  "trend_alignment":"price above MA20/50/200 plus MA20 > MA50 > MA200; 5 binary points total",
                  "ranking":"higher Momentum Score = stronger current momentum within KOMPAS100"},
        "summary":{"explosive":sum(x["momentum_label"]=="Explosive" for x in rows),
                   "strong":sum(x["momentum_label"]=="Strong" for x in rows),
                   "positive":sum(x["momentum_label"]=="Positive" for x in rows),
                   "neutral":sum(x["momentum_label"]=="Neutral" for x in rows),
                   "weak":sum(x["momentum_label"]=="Weak" for x in rows),
                   "avg_return_5d":round(avg5,2),"avg_return_20d":round(avg20,2)},
        "stocks":rows
    }
    OUT.write_text(json.dumps(payload,separators=(",",":"),allow_nan=False),encoding="utf-8")
    print(f"Momentum Dashboard: {len(rows)} stocks, asof {data['asof']}")

if __name__=="__main__": main()
