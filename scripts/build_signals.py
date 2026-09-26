#!/usr/bin/env python3
"""Build deterministic technical signals for SevenPercentCommunity."""
import datetime as dt
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
DATA=ROOT/"data/screener.json"
OUT=ROOT/"data/signals.json"
HIST=ROOT/"data/signal-history.json"
RSI_N=14
ST_K=14
ST_S=3
ST_D=3
MAC_F=12
MAC_S=26
MAC_G=9
VOL_N=20

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
    out=[float("nan")]*len(c)
    if len(c)<=n: return out
    gains=[]; losses=[]
    for i in range(1,len(c)):
        d=c[i]-c[i-1]; gains.append(max(d,0)); losses.append(max(-d,0))
        if i<n: continue
        if i==n: ag=sum(gains[-n:])/n; al=sum(losses[-n:])/n
        else:
            ag=(ag*(n-1)+gains[-1])/n; al=(al*(n-1)+losses[-1])/n
        out[i]=100 if al==0 else 100-(100/(1+ag/al))
    return out

def stochastic(h,l,c,k=14,s=3,d=3):
    raw=[float("nan")]*len(c)
    for i in range(k-1,len(c)):
        hi=max(h[i-k+1:i+1]); lo=min(l[i-k+1:i+1])
        raw[i]=50 if hi==lo else 100*(c[i]-lo)/(hi-lo)
    kd=sma(raw,s); dd=sma(kd,d)
    return kd,dd

def macd(c,f=12,s=26,g=9):
    ef=ema(c,f); es=ema(c,s)
    line=[a-b if finite(a) and finite(b) else float("nan") for a,b in zip(ef,es)]
    sig=ema(line,g)
    hist=[a-b if finite(a) and finite(b) else float("nan") for a,b in zip(line,sig)]
    return line,sig,hist

def cross_up(a,b):
    return len(a)>1 and all(finite(x) for x in (a[-2],a[-1],b[-2],b[-1])) and a[-2]<=b[-2] and a[-1]>b[-1]

def classify(score):
    if score>=15: return "Bullish"
    if score<=-15: return "Bearish"
    return "Neutral"

def strength(score):
    x=abs(score)
    return "Very Strong" if x>=60 else "Strong" if x>=35 else "Moderate" if x>=15 else "Netral"

def transition(prev,current):
    prev_sig=prev.get("signal") if prev else None
    cur_sig=current["signal"]; delta=current["score_delta"]
    new_bull=bool(prev and cur_sig=="Bullish" and (prev_sig!="Bullish" or delta>=15))
    ai=bool(new_bull and current["score"]>=50 and current["agree"]>=3)
    return new_bull,ai

def main():
    data=json.loads(DATA.read_text())
    old=json.loads(OUT.read_text()).get("signals",[]) if OUT.exists() else []
    prev={x["ticker"]:x for x in old}
    signals=[]; events=[]
    for s in data["stocks"]:
        c=[float(x) for x in s["c"]]; h=[float(x) for x in s["h"]]; l=[float(x) for x in s["l"]]; v=[float(x) for x in s["v"]]
        if len(c)<60: continue
        rr=rsi(c,RSI_N); k,d=stochastic(h,l,c,ST_K,ST_S,ST_D); ml,ms,mh=macd(c,MAC_F,MAC_S,MAC_G)
        rv=(v[-1]/(sum(v[-VOL_N:])/VOL_N)) if sum(v[-VOL_N:])>0 else float("nan")
        vals=[rr[-1],k[-1],d[-1],ml[-1],ms[-1],mh[-1],rv]
        if not all(finite(x) for x in vals): continue
        rscore=max(-1,min(1,(rr[-1]-50)/20))
        stscore=1 if k[-1]>d[-1] and k[-1]<80 else -1 if k[-1]<d[-1] and k[-1]>20 else (0.5 if k[-1]>=80 else -0.5 if k[-1]<=20 else 0)
        mscore=max(-1,min(1,(mh[-1]/max(abs(c[-1])*0.01,1e-9))*4))
        vscore=max(-1,min(1,(rv-1)*0.75))
        score=25*rscore+25*stscore+30*mscore+20*vscore
        agree=sum(1 for x in (rscore,stscore,mscore,vscore) if x>0.15 or x<-0.15)
        sig=classify(score); p=prev.get(s["t"]); delta=round(score-(p.get("score",score) if p else score),4)
        cur={"ticker":s["t"],"name":s["n"],"price":c[-1],"asof":s["d"][-1],"score":round(score,2),"signal":sig,"strength":strength(score),"agree":agree,"total":4,"rsi":round(rr[-1],2),"stoch_k":round(k[-1],2),"stoch_d":round(d[-1],2),"macd_hist_pct":round(100*mh[-1]/c[-1],4),"rvol":round(rv,3),"stoch_cross":cross_up(k,d),"macd_cross":cross_up(ml,ms),"previous_signal":p.get("signal") if p else None,"previous_score":p.get("score") if p else None,"score_delta":delta}
        nb,ai=transition(p,cur); cur["signal_changed"]=bool(p and p.get("signal")!=sig); cur["new_bullish"]=nb; cur["ai_candidate"]=ai
        if nb:
            events.append({"ticker":s["t"],"asof":cur["asof"],"signal":sig,"score":cur["score"],"previous_signal":cur["previous_signal"],"previous_score":cur["previous_score"],"ai_candidate":ai})
        signals.append(cur)
    payload={"generated":dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),"asof":data["asof"],"universe_count":data["universe_count"],"signals_count":len(signals),"new_bullish_count":sum(x["new_bullish"] for x in signals),"ai_queue_count":sum(x["ai_candidate"] for x in signals),"signals":signals}
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(payload,separators=(",",":"),allow_nan=False))
    history=json.loads(HIST.read_text()).get("events",[]) if HIST.exists() else []
    history=(history+events)[-1000:]
    HIST.write_text(json.dumps({"events":history},separators=(",",":")))
    print(json.dumps({"universe_count":data["universe_count"],"signals_count":len(signals),"new_bullish_count":payload["new_bullish_count"],"ai_queue_count":payload["ai_queue_count"]}))

if __name__=="__main__": main()
