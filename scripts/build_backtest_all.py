#!/usr/bin/env python3
"""Phase D: chronological backtest for all LONG setup families."""
import datetime as dt, json, math
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
DATA=ROOT/"data/screener.json"
OUT=ROOT/"data/backtest-all.json"

RSI_N=14; ST_K=14; ST_S=5; ST_D=5; MAC_F=10; MAC_S=20; MAC_G=9
VOL_N=20; ATR_N=14; MIN_SCORE=25; MIN_AGREE=3; RSI_MIN=50; RSI_MAX=70
LOOKBACK=90; PIVOT=3; MIN_RR=1.5; HORIZONS=(5,10,20)

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
        out[i]=sum(vals)/n if len(vals)==n else x*(2/(n+1))+out[i-1]*(1-2/(n+1))
    return out

def rsi(c,n=14):
    out=[float("nan")]*len(c); gains=[]; losses=[]
    for i in range(1,len(c)):
        d=c[i]-c[i-1]; gains.append(max(d,0)); losses.append(max(-d,0))
        if i<n: continue
        if i==n: ag=sum(gains[-n:])/n; al=sum(losses[-n:])/n
        else: ag=(ag*(n-1)+gains[-1])/n; al=(al*(n-1)+losses[-1])/n
        out[i]=100 if al==0 else 100-(100/(1+ag/al))
    return out

def stochastic(h,l,c,k=14,s=5,d=5):
    raw=[float("nan")]*len(c)
    for i in range(k-1,len(c)):
        hi=max(h[i-k+1:i+1]); lo=min(l[i-k+1:i+1])
        raw[i]=50 if hi==lo else 100*(c[i]-lo)/(hi-lo)
    slow_k=sma(raw,s)
    return slow_k,sma(slow_k,d)

def macd_hist(c,f=10,s=20,g=9):
    ef=ema(c,f); es=ema(c,s)
    line=[a-b if finite(a) and finite(b) else float("nan") for a,b in zip(ef,es)]
    sig=ema(line,g)
    return [a-b if finite(a) and finite(b) else float("nan") for a,b in zip(line,sig)]

def atr(h,l,c,n=14):
    tr=[]
    for i in range(len(c)):
        tr.append(h[i]-l[i] if i==0 else max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1])))
    out=[float("nan")]*len(c)
    for i in range(n-1,len(c)): out[i]=sum(tr[i-n+1:i+1])/n
    return out

def signal_series(c,h,l,v):
    rr=rsi(c); k,d=stochastic(h,l,c); mh=macd_hist(c); e20=ema(c,20); e50=ema(c,50)
    out=[None]*len(c)
    for i in range(len(c)):
        if i<VOL_N-1 or not all(finite(x) for x in (rr[i],k[i],d[i],mh[i],e20[i],e50[i])): continue
        av=sum(v[i-VOL_N+1:i+1])/VOL_N; rv=v[i]/av if av else float("nan")
        if not finite(rv): continue
        trend=1 if c[i]>e20[i]>e50[i] else -1 if c[i]<e20[i]<e50[i] else 0
        rs=max(-1,min(1,(rr[i]-50)/15))
        if rr[i]>=70 and rs>0: rs*=.35
        if rr[i]<=30 and rs<0: rs*=.35
        st=1 if k[i]>d[i] and k[i]<85 else -1 if k[i]<d[i] and k[i]>15 else 0
        ms=max(-1,min(1,(mh[i]/max(abs(c[i])*.01,1e-9))*5))
        if i and mh[i]>0 and mh[i]<mh[i-1]: ms*=.65
        if i and mh[i]<0 and mh[i]>mh[i-1]: ms*=.65
        pd=1 if c[i]>c[i-1] else -1 if c[i]<c[i-1] else 0
        vs=0 if rv<.9 else pd*min(1,(rv-.9)/.9)
        comps=[trend,rs,st,ms,vs]
        score=25*trend+20*rs+15*st+25*ms+15*vs
        agree=sum(x>=.25 for x in comps) if score>=0 else sum(x<=-.25 for x in comps)
        sig="Bullish" if score>=25 and agree>=3 else "Bearish" if score<=-25 and agree>=3 else "Neutral"
        out[i]={"score":score,"agree":agree,"signal":sig,"rsi":rr[i],"rvol":rv}
    return out

def new_bullish(sig,i):
    if i<1 or not sig[i] or not sig[i-1] or sig[i]["signal"]!="Bullish": return False
    return sig[i-1]["signal"]!="Bullish" or sig[i]["score"]-sig[i-1]["score"]>=15

def pivots_confirmed(h,l,end,p=3):
    start=max(0,end-LOOKBACK+1); ph=[]; pl=[]
    # A pivot is only usable after p bars to its right have printed.
    for x in range(start+p,end-p+1):
        hw=h[x-p:x+p+1]; lw=l[x-p:x+p+1]
        if h[x]==max(hw) and h[x]>max(h[x-p:x]): ph.append(x)
        if l[x]==min(lw) and l[x]<min(l[x-p:x]): pl.append(x)
    return ph,pl

def fib_setup(h,l,c,i):
    ph,pl=pivots_confirmed(h,l,i,PIVOT)
    highs=[x for x in ph if x<=i-PIVOT]
    if not highs: return None
    hi=highs[-1]; lows=[x for x in pl if x<hi]
    if not lows: return None
    lo=lows[-1]; low=l[lo]; high=h[hi]
    if high<=low: return None
    rng=high-low; entry=c[i]; sl=low; tp1=high+rng*.272; tp2=high+rng*.618
    risk=entry-sl; rr=(tp1-entry)/risk if risk else 0
    if risk<=0 or tp1<=entry or rr<MIN_RR or entry>=tp2: return None
    return {"entry":entry,"sl":sl,"tp1":tp1,"tp2":tp2}

def risk_outcome(h,l,c,dates,i,plan,max_days=40):
    entry=plan["entry"]; sl=plan["sl"]; tp1=plan["tp1"]; tp2=plan["tp2"]
    risk=entry-sl
    for j in range(i+1,min(len(h),i+1+max_days)):
        hit_sl=l[j]<=sl; hit_tp2=h[j]>=tp2; hit_tp1=h[j]>=tp1
        if hit_sl and (hit_tp2 or hit_tp1):
            return {"outcome":"STOP LOSS","exit_price":sl,"exit_date":dates[j],"r":-1,"days":j-i,"tp1_hit":bool(hit_tp1 or hit_tp2),"tp2_hit":bool(hit_tp2),"ambiguous":True}
        if hit_tp2:
            return {"outcome":"TP2","exit_price":tp2,"exit_date":dates[j],"r":(tp2-entry)/risk,"days":j-i,"tp1_hit":True,"tp2_hit":True,"ambiguous":False}
        if hit_tp1:
            return {"outcome":"TP1","exit_price":tp1,"exit_date":dates[j],"r":(tp1-entry)/risk,"days":j-i,"tp1_hit":True,"tp2_hit":False,"ambiguous":False}
        if hit_sl:
            return {"outcome":"STOP LOSS","exit_price":sl,"exit_date":dates[j],"r":-1,"days":j-i,"tp1_hit":False,"tp2_hit":False,"ambiguous":False}
    j=min(len(h)-1,i+max_days)
    if j<=i: return None
    return {"outcome":"TIMEOUT","exit_price":c[j],"exit_date":dates[j],"r":(c[j]-entry)/risk,"days":j-i,"tp1_hit":False,"tp2_hit":False,"ambiguous":False}

def pct(a,b): return (b/a-1)*100 if a else None

def stats(rows):
    if not rows:
        return {"count":0,"win_rate":None,"tp1_rate":None,"tp2_rate":None,"sl_rate":None,"timeout_rate":None,"avg_return":None,"avg_r":None,"profit_factor":None,"expectancy_r":None,"best_r":None,"worst_r":None,"max_drawdown_r":None}
    rr=[x["r"] for x in rows]; rets=[x["return_pct"] for x in rows]
    wins=[x for x in rows if x["outcome"] in ("TP1","TP2")]
    gross_win=sum(max(0,x["r"]) for x in rows); gross_loss=sum(abs(min(0,x["r"])) for x in rows)
    eq=peak=0; dd=0
    for x in sorted(rows,key=lambda z:z["signal_date"]):
        eq+=x["r"]; peak=max(peak,eq); dd=min(dd,eq-peak)
    return {
        "count":len(rows),"win_rate":round(100*len(wins)/len(rows),2),
        "tp1_rate":round(100*sum(x["tp1_hit"] for x in rows)/len(rows),2),
        "tp2_rate":round(100*sum(x["tp2_hit"] for x in rows)/len(rows),2),
        "sl_rate":round(100*sum(x["outcome"]=="STOP LOSS" for x in rows)/len(rows),2),
        "timeout_rate":round(100*sum(x["outcome"]=="TIMEOUT" for x in rows)/len(rows),2),
        "avg_return":round(sum(rets)/len(rets),2),"avg_r":round(sum(rr)/len(rr),3),
        "profit_factor":round(gross_win/gross_loss,3) if gross_loss else None,
        "expectancy_r":round(sum(rr)/len(rr),3),"best_r":round(max(rr),3),
        "worst_r":round(min(rr),3),"max_drawdown_r":round(dd,3)
    }

def main():
    data=json.loads(DATA.read_text())
    families={"TECHNICAL SIGNAL":[],"TECHNICAL TRADE JOURNAL":[],"EARLY BREAKOUT":[],"EARLY PULLBACK":[]}
    diagnostics={k:0 for k in ["stocks","technical_candidates","journal_candidates","journal_rr_valid","early_breakout","early_pullback"]}
    for s in data["stocks"]:
        c=list(map(float,s["c"])); h=list(map(float,s["h"])); l=list(map(float,s["l"])); v=list(map(float,s["v"])); dates=s["d"]
        if len(c)<120: continue
        diagnostics["stocks"]+=1; sig=signal_series(c,h,l,v); av=atr(h,l,c)
        for i in range(60,len(c)-21):
            q=sig[i]
            if not q: continue
            fresh=new_bullish(sig,i)
            if q["signal"]=="Bullish" and fresh:
                diagnostics["technical_candidates"]+=1
                for n in HORIZONS:
                    if i+n<len(c):
                        ret=pct(c[i],c[i+n])
                        families["TECHNICAL SIGNAL"].append({"ticker":s["t"],"signal_date":dates[i],"entry_price":c[i],"horizon":n,"return_pct":ret,"r":ret,"outcome":"WIN" if ret>0 else "LOSS","tp1_hit":ret>0,"tp2_hit":False})
            if q["signal"]=="Bullish" and fresh and RSI_MIN<=q["rsi"]<RSI_MAX and q["score"]>=MIN_SCORE and q["agree"]>=MIN_AGREE:
                fib=fib_setup(h,l,c,i)
                if fib:
                    diagnostics["journal_candidates"]+=1; diagnostics["journal_rr_valid"]+=1
                    o=risk_outcome(h,l,c,dates,i,fib)
                    if o: families["TECHNICAL TRADE JOURNAL"].append({"ticker":s["t"],"signal_date":dates[i],"entry_price":c[i],"return_pct":pct(c[i],o["exit_price"]),"setup_score":q["score"],**o})
            if av[i] and q["signal"]=="Bullish":
                e20=ema(c[:i+1],20)[-1]; e50=ema(c[:i+1],50)[-1]
                if not finite(e20) or not finite(e50): continue
                price=c[i]; rsi_v=q["rsi"]; rv=q["rvol"]; recent_high=max(h[max(0,i-5):i+1]); draw=(price/recent_high-1)*100 if recent_high else 0
                prev20=max(h[i-20:i])
                pull=price<=recent_high*.985 and price>=e20*.97 and price>e50 and -12<=draw<=-1.5 and 45<=rsi_v<68
                breakout=price>prev20*1.002 and c[i-1]<=prev20*1.002 and rv>=1.2 and 50<=rsi_v<75
                if breakout or pull:
                    plan={"entry":price,"sl":price-1.5*av[i],"tp1":price+2.25*av[i],"tp2":price+3*av[i]}
                    o=risk_outcome(h,l,c,dates,i,plan)
                    if o:
                        row={"ticker":s["t"],"signal_date":dates[i],"entry_price":price,"return_pct":pct(price,o["exit_price"]),"setup_score":q["score"],**o}
                        if breakout: families["EARLY BREAKOUT"].append(row); diagnostics["early_breakout"]+=1
                        if pull: families["EARLY PULLBACK"].append(row); diagnostics["early_pullback"]+=1
    summary={k:stats(v) for k,v in families.items()}
    ranked=sorted(summary.items(),key=lambda kv:(kv[1]["expectancy_r"] if kv[1]["expectancy_r"] is not None else -999),reverse=True)
    payload={
        "generated":dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "asof":data["asof"],"universe":"KOMPAS100",
        "method":{
            "mode":"chronological LONG-only",
            "entry":"close on signal day; risk setups evaluated from next trading day",
            "technical_signal":"NEW BULLISH: Bullish >=25, confluence >=3/5, previous non-Bullish OR score delta >=15",
            "trade_journal":"fresh Bullish + score >=25 + confluence >=3/5 + RSI 50-<70 + confirmed Fibonacci pivots + R:R >=1.5",
            "early_signals":"Bullish trend with breakout/pullback rules; ATR14 SL=1.5 ATR, TP1=2.25 ATR, TP2=3 ATR",
            "ambiguity":"if TP and SL are both touched on the same daily bar, classify STOP LOSS conservatively",
            "costs":"gross results; fees, tax, slippage and spread are not modeled",
            "lookahead_free":True
        },
        "summary":summary,
        "ranking":[{"setup":k,**v} for k,v in ranked],
        "diagnostics":diagnostics,
        "events":{k:v[-500:] for k,v in families.items()}
    }
    OUT.write_text(json.dumps(payload,separators=(",",":"),allow_nan=False),encoding="utf-8")
    print(json.dumps({"summary":summary,"diagnostics":diagnostics}))

if __name__=="__main__": main()
