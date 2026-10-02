#!/usr/bin/env python3
"""Backtest NEW BULLISH signals using historical OHLCV already in screener.json."""
import datetime as dt, json, math
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
DATA=ROOT/"data/screener.json"; OUT=ROOT/"data/backtest.json"
RSI_N=14; ST_K=14; ST_S=5; ST_D=5; MAC_F=10; MAC_S=20; MAC_G=9; VOL_N=20; EMA_FAST=20; EMA_SLOW=50
HORIZONS=(5,10,20)
def finite(x): return isinstance(x,(int,float)) and math.isfinite(x)
def sma(a,n):
    out=[float("nan")]*len(a)
    for i in range(n-1,len(a)):
        w=a[i-n+1:i+1]
        if all(finite(x) for x in w): out[i]=sum(w)/n
    return out
def ema(a,n):
    out=[float("nan")]*len(a); vals=[]
    for i,x in enumerate(a):
        if not finite(x): continue
        vals.append(x)
        if len(vals)<n: continue
        if len(vals)==n: e=sum(vals)/n
        else: e=x*(2/(n+1))+out[i-1]*(1-2/(n+1))
        out[i]=e
    return out
def rsi(c,n=14):
    out=[float("nan")]*len(c); gains=[]; losses=[]
    if len(c)<=n: return out
    for i in range(1,len(c)):
        d=c[i]-c[i-1]; gains.append(max(d,0)); losses.append(max(-d,0))
        if i<n: continue
        if i==n: ag=sum(gains[-n:])/n; al=sum(losses[-n:])/n
        else: ag=(ag*(n-1)+gains[-1])/n; al=(al*(n-1)+losses[-1])/n
        out[i]=100 if al==0 else 100-(100/(1+ag/al))
    return out
def stochastic(h,l,c,k=14,s=3,d=3):
    raw=[float("nan")]*len(c)
    for i in range(k-1,len(c)):
        hi=max(h[i-k+1:i+1]); lo=min(l[i-k+1:i+1]); raw[i]=50 if hi==lo else 100*(c[i]-lo)/(hi-lo)
    return sma(raw,s), sma(sma(raw,s),d)
def macd(c,f=12,s=26,g=9):
    ef=ema(c,f); es=ema(c,s); line=[a-b if finite(a) and finite(b) else float("nan") for a,b in zip(ef,es)]
    sig=ema(line,g); return [a-b if finite(a) and finite(b) else float("nan") for a,b in zip(line,sig)]
def indicator_series(c,h,l,v):
    rr=rsi(c,RSI_N); k,d=stochastic(h,l,c,ST_K,ST_S,ST_D); mh=macd(c,MAC_F,MAC_S,MAC_G)
    ef=ema(c,EMA_FAST); es=ema(c,EMA_SLOW)
    scores=[None]*len(c)
    for i in range(len(c)):
        if i<VOL_N-1: continue
        rv=v[i]/(sum(v[i-VOL_N+1:i+1])/VOL_N) if sum(v[i-VOL_N+1:i+1])>0 else float("nan")
        vals=[rr[i],k[i],d[i],mh[i],rv,ef[i],es[i]]
        if not all(finite(x) for x in vals): continue
        trend=1 if c[i]>ef[i]>es[i] else -1 if c[i]<ef[i]<es[i] else 0
        rscore=max(-1,min(1,(rr[i]-50)/15))
        if rr[i]>=70 and rscore>0: rscore*=0.35
        if rr[i]<=30 and rscore<0: rscore*=0.35
        stscore=1 if k[i]>d[i] and k[i]<85 else -1 if k[i]<d[i] and k[i]>15 else 0
        mscore=max(-1,min(1,(mh[i]/max(abs(c[i])*0.01,1e-9))*5))
        if i>0 and mh[i]>0 and mh[i]<mh[i-1]: mscore*=0.65
        if i>0 and mh[i]<0 and mh[i]>mh[i-1]: mscore*=0.65
        pdir=1 if c[i]>c[i-1] else -1 if c[i]<c[i-1] else 0
        vscore=0 if rv<0.9 else pdir*min(1,(rv-0.9)/0.9)
        comps=[trend,rscore,stscore,mscore,vscore]
        score=25*trend+20*rscore+15*stscore+25*mscore+15*vscore
        agree=sum(1 for x in comps if x>=0.25) if score>=0 else sum(1 for x in comps if x<=-0.25)
        signal="Bullish" if score>=25 and agree>=3 else "Bearish" if score<=-25 and agree>=3 else "Neutral"
        scores[i]={"score":round(score,2),"signal":signal,"agree":agree}
    return scores
def pct(a,b): return (b/a-1)*100 if a else None
def summarize(rows,h):
    vals=[e["returns"][str(h)] for e in rows if str(h) in e["returns"]]
    if not vals: return {"count":0,"win_rate":None,"avg_return":None,"median_return":None,"best":None,"worst":None}
    vals=sorted(vals)
    return {"count":len(vals),"win_rate":round(100*sum(x>0 for x in vals)/len(vals),2),
            "avg_return":round(sum(vals)/len(vals),2),"median_return":round(vals[len(vals)//2],2),
            "best":round(max(vals),2),"worst":round(min(vals),2)}
def main():
    data=json.loads(DATA.read_text()); events=[]
    for s in data["stocks"]:
        c=list(map(float,s["c"])); h=list(map(float,s["h"])); l=list(map(float,s["l"])); v=list(map(float,s["v"])); dates=s["d"]
        if len(c)<100: continue
        sig=indicator_series(c,h,l,v)
        for i in range(60,len(c)):
            cur,prev=sig[i],sig[i-1]
            if not cur or not prev: continue
            delta=cur["score"]-prev["score"]
            if cur["signal"]!="Bullish" or not (prev["signal"]!="Bullish" or delta>=15): continue
            returns={str(n):round(pct(c[i],c[i+n]),2) for n in HORIZONS if i+n<len(c)}
            if returns:
                events.append({"ticker":s["t"],"name":s["n"],"signal_date":dates[i],"entry_price":round(c[i],2),
                               "score":cur["score"],"score_delta":round(delta,2),"confluence":cur["agree"],"returns":returns})
    summary={str(h):summarize(events,h) for h in HORIZONS}; bands={}
    groups=[("score_15_34",lambda e:15<=e["score"]<35),("score_35_49",lambda e:35<=e["score"]<50),
            ("score_50_plus",lambda e:e["score"]>=50),("confluence_3",lambda e:e["confluence"]==3),("confluence_4",lambda e:e["confluence"]==4)]
    for name,fn in groups:
        subset=[e for e in events if fn(e)]; bands[name]={str(h):summarize(subset,h) for h in HORIZONS}
    by={}
    for e in events: by.setdefault(e["ticker"],[]).append(e)
    ticker_rows=[]
    for t,items in by.items():
        row={"ticker":t,"name":items[0]["name"],"signals":len(items)}
        for h in HORIZONS:
            z=summarize(items,h); row[str(h)]={"count":z["count"],"win_rate":z["win_rate"],"avg_return":z["avg_return"]}
        ticker_rows.append(row)
    ticker_rows.sort(key=lambda x:(x["20"]["avg_return"] if x["20"]["avg_return"] is not None else -999),reverse=True)
    payload={"generated":dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),"asof":data["asof"],"universe":"KOMPAS100",
             "method":{"entry":"close on NEW BULLISH signal day","exit":"closing price after N trading sessions","horizons":[5,10,20],
                       "signal_rule":"Bullish score >= 25 with >=3/5 confirmations and (previous signal was not Bullish OR score delta >= 15)","lookahead_free":True},
             "signal_count":len(events),"summary":summary,"bands":bands,"by_ticker":ticker_rows,"events":events[-500:]}
    OUT.write_text(json.dumps(payload,separators=(",",":"),allow_nan=False),encoding="utf-8")
    print(json.dumps({"signal_count":len(events),"summary":summary}))
if __name__=="__main__": main()
