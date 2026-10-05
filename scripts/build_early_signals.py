#!/usr/bin/env python3
"""Build LONG-only Early Signals: pullback + breakout candidates with setup grade and ATR risk plan."""
import datetime as dt, json, math
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
SCREENER=ROOT/"data/screener.json"
SIGNALS=ROOT/"data/signals.json"
OUT=ROOT/"data/early-signals.json"

ATR_N=14
LOOKBACK=20
MIN_RR=1.5

def finite(x): return isinstance(x,(int,float)) and math.isfinite(x)

def ema(a,n):
    out=[float("nan")]*len(a); vals=[]
    for i,x in enumerate(a):
        if not finite(x): continue
        vals.append(x)
        if len(vals)<n: continue
        out[i]=sum(vals)/n if len(vals)==n else x*(2/(n+1))+out[i-1]*(1-2/(n+1))
    return out

def atr(h,l,c,n=14):
    tr=[float("nan")]*len(c)
    for i in range(len(c)):
        if not all(finite(x) for x in (h[i],l[i])): continue
        tr[i]=h[i]-l[i] if i==0 or not finite(c[i-1]) else max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1]))
    out=[float("nan")]*len(c); vals=[]
    for i,x in enumerate(tr):
        if not finite(x): continue
        vals.append(x)
        if len(vals)<n: continue
        out[i]=sum(vals[-n:])/n
    return out

def grade(score):
    if score>=85: return "A+"
    if score>=75: return "A"
    if score>=65: return "B"
    return "WATCH"

def main():
    screener=json.loads(SCREENER.read_text())
    signals=json.loads(SIGNALS.read_text())
    sig={x["ticker"]:x for x in signals.get("signals",[])}
    items=[]; diagnostics={"universe":len(screener.get("stocks",[])),"bullish":0,"trend_ok":0,"pullback":0,"breakout":0,"volume_ok":0,"rr_ok":0,"candidates":0}
    for s in screener.get("stocks",[]):
        ticker=s.get("t"); q=sig.get(ticker)
        if not q or q.get("signal")!="Bullish": continue
        diagnostics["bullish"]+=1
        c=list(map(float,s.get("c",[]))); h=list(map(float,s.get("h",[]))); l=list(map(float,s.get("l",[]))); v=list(map(float,s.get("v",[])))
        if len(c)<max(60,ATR_N+LOOKBACK+2): continue
        a=atr(h,l,c,ATR_N); atrv=a[-1]
        if not finite(atrv) or atrv<=0: continue
        e20=ema(c,20); e50=ema(c,50)
        if not finite(e20[-1]) or not finite(e50[-1]): continue
        price=c[-1]; rsi=float(q.get("rsi",0)); rv=float(q.get("rvol",0) or 0)
        trend=price>e20[-1]>e50[-1]
        if not trend: continue
        diagnostics["trend_ok"]+=1
        prev20=max(h[-LOOKBACK-1:-1]); high20=max(h[-LOOKBACK:]); low20=min(l[-LOOKBACK:])
        recent_high=max(h[-6:]); drawdown=(price/recent_high-1)*100 if recent_high else 0
        pullback=price<=recent_high*0.985 and price>=e20[-1]*0.97 and price>e50[-1] and -12<=drawdown<=-1.5 and 45<=rsi<68
        breakout=price>prev20*1.002 and c[-2]<=prev20*1.002 and rv>=1.2 and 50<=rsi<75
        if pullback: diagnostics["pullback"]+=1
        if breakout: diagnostics["breakout"]+=1
        if not (pullback or breakout): continue
        if rv>=1.2: diagnostics["volume_ok"]+=1
        # ATR risk plan: 1.5 ATR stop, TP1=2.25 ATR (1.5R), TP2=3 ATR (2R).
        sl=price-1.5*atrv
        risk=price-sl
        tp1=price+2.25*atrv
        tp2=price+3.0*atrv
        rr1=(tp1-price)/risk if risk else 0
        if rr1<MIN_RR: continue
        diagnostics["rr_ok"]+=1
        trend_pts=20 if price>e20[-1]>e50[-1] else 10
        momentum_pts=20 if 50<=rsi<65 else 15
        volume_pts=15 if rv>=1.5 else 10 if rv>=1.2 else 5
        setup_pts=25 if breakout and rv>=1.5 else 22 if breakout else 20
        rsi_pts=10 if 52<=rsi<=65 else 7
        risk_pts=10 if rr1>=2 else 8 if rr1>=1.75 else 7
        score=trend_pts+momentum_pts+volume_pts+setup_pts+rsi_pts+risk_pts
        g=grade(score)
        stage="READY" if breakout or score>=75 else "PREPARE"
        setup_type="BREAKOUT" if breakout else "PULLBACK"
        reasons=[]
        if trend: reasons.append("EMA20 > EMA50")
        if pullback: reasons.append("healthy pullback")
        if breakout: reasons.append("20D breakout")
        if rv>=1.2: reasons.append(f"RVOL {rv:.2f}x")
        if 50<=rsi<70: reasons.append(f"RSI {rsi:.1f}")
        diagnostics["candidates"]+=1
        items.append({
            "ticker":ticker,"name":s.get("n",ticker),"asof":s.get("d",[""])[-1],
            "setup":setup_type,"stage":stage,"grade":g,"setup_score":score,
            "price":round(price,2),"rsi":round(rsi,2),"rvol":round(rv,2),
            "atr14":round(atrv,2),"atrp":round(atrv/price*100,2),
            "ema20":round(e20[-1],2),"ema50":round(e50[-1],2),
            "resistance20":round(prev20,2),"recent_high":round(recent_high,2),"drawdown_pct":round(drawdown,2),
            "entry":round(price,2),"stop_loss":round(sl,2),"tp1":round(tp1,2),"tp2":round(tp2,2),
            "risk_pct":round(risk/price*100,2),"rr_tp1":round(rr1,2),"rr_tp2":round((tp2-price)/risk,2),
            "reasons":reasons
        })
    items.sort(key=lambda x:(x["setup_score"],x["grade"],x["rvol"]),reverse=True)
    payload={"generated":dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),"asof":signals.get("asof") or screener.get("asof"),"candidate_count":len(items),"diagnostics":diagnostics,"items":items[:50]}
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(payload,separators=(",",":"),allow_nan=False))
    print(json.dumps({"candidate_count":payload["candidate_count"],"diagnostics":diagnostics}))
if __name__=="__main__": main()
