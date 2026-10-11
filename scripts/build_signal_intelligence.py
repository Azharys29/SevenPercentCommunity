#!/usr/bin/env python3
"""Build lightweight institutional-style Signal Intelligence from existing SPC data."""
import datetime as dt, json, math, statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
D=ROOT/"data"
def load(n, default=None):
 p=D/n
 if not p.exists(): return default if default is not None else {}
 try: return json.loads(p.read_text(encoding="utf-8"))
 except Exception: return default if default is not None else {}
def finite(x): return isinstance(x,(int,float)) and math.isfinite(x)
def ret(c,n): return (c[-1]/c[-1-n]-1)*100 if len(c)>n and c[-1-n] else None
def rank(vals):
 good=sorted(x for x in vals if finite(x)); out=[]
 for x in vals:
  out.append(round(100*(sum(v<=x for v in good)-1)/max(len(good)-1,1),1) if finite(x) and good else None)
 return out
def mean(a): return statistics.mean(a) if a else None
def stdev(a): return statistics.stdev(a) if len(a)>1 else None
def clamp(x,lo=0,hi=100): return max(lo,min(hi,x))
def main():
 raw=load("screener.json"); stocks=raw.get("stocks",[])
 mom= {x["ticker"]:x for x in load("momentum.json",{}).get("stocks",[])}
 rs= {x["ticker"]:x for x in load("relative-strength.json",{}).get("stocks",[])}
 sig={x["ticker"]:x for x in load("signals.json",{}).get("signals",[])}
 vg={x["ticker"]:x for x in load("value-gap.json",{}).get("stocks",[])}
 regime=load("market-regime.json",{})
 sectors=load("sector-rotation.json",{})
 rows=[]; hist=[]
 for s in stocks:
  t=s.get("t"); c=[float(x) for x in s.get("c",[]) if finite(x) and x>0]
  if not t or len(c)<60: continue
  m=mom.get(t,{}); r=rs.get(t,{}); q=sig.get(t,{}); v=vg.get(t,{})
  r21,r63,r126,r252=[ret(c,n) for n in (21,63,126,252)]
  # Trend persistence is consistency across horizons; 12M excludes the most recent month.
  mom12=(c[-22]/c[-253]-1)*100 if len(c)>253 and c[-253] else r252
  horizons=[r21,r63,r126,mom12]
  pos=sum(x is not None and x>0 for x in horizons)
  trend=pos/len([x for x in horizons if x is not None])*100 if any(x is not None for x in horizons) else None
  closes=c[-61:]; daily=[(closes[i]/closes[i-1]-1)*100 for i in range(1,len(closes)) if closes[i-1]>0]
  vol=(stdev(daily)*math.sqrt(252)) if len(daily)>10 else None
  # Simple 14-day ATR proxy using close-to-close absolute returns where OHLC isn't guaranteed complete.
  atr=mean([abs(x) for x in daily[-14:]]) if daily else None
  # Liquidity proxy: recent volume vs historical median, normalized conservatively.
  vv=[float(x) for x in (s.get("v") or []) if finite(x) and x>=0]
  volratio=(vv[-1]/max(statistics.median(vv[-21:-1]),1)) if len(vv)>=21 else None
  value=v.get("value_gap_score")
  # Transform extreme Value Gap outliers before cross-sectional ranking.
  value_signal=(math.copysign(math.log1p(abs(value)),value) if finite(value) else None)
  zvals=[]
  for i in range(max(20,len(c)-60),len(c)+1):
   w=c[max(0,i-20):i]
   if i<len(c) and len(w)>=15 and statistics.mean(w)>0:
    sd=stdev(w)
    if sd and sd>0: zvals.append((c[i]/statistics.mean(w)-1)*100/(sd/statistics.mean(w)*100))
  z=zvals[-1] if zvals else None
  hl=None; theta=None; r2=None
  # OU-style half-life on log(close/SMA20), only a screening estimate.
  xvals=[]
  for i in range(max(20,len(c)-60),len(c)):
   w=c[i-19:i+1]
   if len(w)==20 and statistics.mean(w)>0: xvals.append(math.log(c[i]/statistics.mean(w)))
  if len(xvals)>=30:
   lag=xvals[:-1]; dx=[xvals[i+1]-xvals[i] for i in range(len(xvals)-1)]
   ml=mean(lag); md=mean(dx); den=sum((a-ml)**2 for a in lag)
   b=sum((a-ml)*(d-md) for a,d in zip(lag,dx))/den if den>0 else 0
   theta=-b
   yh=[md+b*(a-ml) for a in lag]
   sst=sum((d-md)**2 for d in dx); ssr=sum((d-y)**2 for d,y in zip(dx,yh))
   r2=1-ssr/sst if sst>0 else None
   hl=math.log(2)/theta if theta>0 else None
   if not finite(hl) or hl<2 or hl>30: hl=None
  rows.append({"ticker":t,"name":s.get("n",t),"sector":s.get("s","Lainnya"),"price":c[-1],"return_1m":r21,"return_3m":r63,"return_6m":r126,"return_12m":r252,"momentum_ex_month":mom12,"trend_raw":trend,"volatility":vol,"atr_proxy_pct":atr,"volume_ratio":volratio,"value_raw":value_signal,"rs_raw":r.get("rs_score"),"technical":q.get("score"),"technical_signal":q.get("signal"),"zscore":z,"ou_half_life":hl,"ou_r2":r2,"value_available":finite(value),"quality_available":False})
 # Cross-sectional ranks avoid mixing incompatible scales and extreme outliers.
 fields={"momentum":[x["return_1m"] for x in rows],"trend":[x["trend_raw"] for x in rows],"relative_strength":[x["rs_raw"] for x in rows],"value":[x["value_raw"] for x in rows],"liquidity":[x["volume_ratio"] for x in rows],"low_volatility":[-x["volatility"] if finite(x["volatility"]) else None for x in rows]}
 ranks={k:rank(vals) for k,vals in fields.items()}
 for i,x in enumerate(rows):
  components={"momentum":ranks["momentum"][i],"trend_persistence":ranks["trend"][i],"relative_strength":ranks["relative_strength"][i],"value":ranks["value"][i],"liquidity":ranks["liquidity"][i],"low_volatility":ranks["low_volatility"][i]}
  # Reweight only available data; Quality intentionally omitted until reliable point-in-time fundamentals exist.
  weights={"momentum":.25,"trend_persistence":.20,"relative_strength":.20,"value":.15,"liquidity":.10,"low_volatility":.10}
  valid=[(components[k],w) for k,w in weights.items() if finite(components[k])]
  score=sum(v*w for v,w in valid)/sum(w for _,w in valid) if valid else None
  x["factor_components"]=components; x["factor_score"]=round(score,1) if score is not None else None
  x["factor_coverage"]=len(valid); x["factor_total"]=6
  explanations=[]
  if finite(components["momentum"]) and components["momentum"]>=70: explanations.append("Momentum relatif berada di kelompok atas universe.")
  elif finite(components["momentum"]) and components["momentum"]<=30: explanations.append("Momentum relatif lemah dibanding universe.")
  if finite(components["trend_persistence"]) and components["trend_persistence"]>=75: explanations.append("Return positif pada mayoritas horizon yang tersedia.")
  elif finite(components["trend_persistence"]) and components["trend_persistence"]<=25: explanations.append("Tren belum konsisten pada beberapa horizon.")
  if finite(components["relative_strength"]) and components["relative_strength"]>=70: explanations.append("Mengungguli banyak saham KOMPAS100 pada relative strength.")
  if finite(components["value"]) and components["value"]>=75: explanations.append("Value Gap relatif menarik; perlu konfirmasi kualitas fundamental.")
  if finite(x["volatility"]) and x["volatility"]>60: explanations.append("Volatilitas tahunan tinggi; pertimbangkan ukuran posisi lebih kecil.")
  if finite(x["volume_ratio"]) and x["volume_ratio"]<.5: explanations.append("Volume sesi terakhir rendah dibanding median 20 sesi.")
  if finite(x["zscore"]) and abs(x["zscore"])>=1.5: explanations.append("Harga menyimpang dari rerata 20 sesi; deviasi bukan bukti pasti akan berbalik.")
  if not explanations: explanations.append("Belum ada faktor dominan; lihat komponen dan coverage sebelum mengambil keputusan.")
  x["explanation"]=explanations
  x["risk_flags"]=[]
  if finite(x["volatility"]) and x["volatility"]>60:x["risk_flags"].append("Volatilitas tinggi")
  if finite(x["volume_ratio"]) and x["volume_ratio"]<.5:x["risk_flags"].append("Likuiditas/volume relatif rendah")
  if finite(x["zscore"]) and abs(x["zscore"])>2.5:x["risk_flags"].append("Deviasi harga ekstrem")
  x["invalidation"]="Tinjau ulang jika momentum 1M dan relative strength turun ke kuartil bawah, atau harga menembus level risiko yang ditentukan trader."
 # Historical validation: walk-forward-style cross-sectional momentum signal; next-session entry, 5/20-session exit.
 # This is an exploratory proxy and includes only historical price series present in the source.
 bt=[]
 for horizon in (5,20):
  sigrets=[]; base=[]
  for s in stocks:
   c=[float(x) for x in s.get("c",[]) if finite(x) and x>0]
   if len(c)<160: continue
   for i in range(max(80,len(c)-252),len(c)-horizon-2):
    look=(c[i]/c[i-21]-1)*100 if i>=21 and c[i-21] else None
    entry=c[i+1]; exitp=c[i+1+horizon]
    if look is None or entry<=0: continue
    fwd=(exitp/entry-1)*100; base.append(fwd)
    # Only signal when historical momentum is positive and price is above trailing 50-day mean.
    ma=mean(c[i-49:i+1]) if i>=49 else None
    if look>0 and ma and c[i]>ma: sigrets.append(fwd)
  cost=0.30
  net=[x-cost for x in sigrets]
  bt.append({"horizon_days":horizon,"sample":len(net),"win_rate_pct":round(100*sum(x>0 for x in net)/len(net),2) if net else None,"avg_net_return_pct":round(mean(net),3) if net else None,"median_net_return_pct":round(statistics.median(net),3) if net else None,"baseline_avg_return_pct":round(mean(base),3) if base else None,"assumed_round_trip_cost_pct":cost,"note":"Exploratory pooled historical observations; overlapping trades and cross-sectional dependence mean this is not a final portfolio backtest."})
 rows.sort(key=lambda x:x["factor_score"] if finite(x["factor_score"]) else -1,reverse=True)
 payload={"generated":dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),"asof":raw.get("asof"),"universe":"KOMPAS100","universe_count":len(rows),"regime":regime,"method":{"factor_weights":{"momentum":25,"trend_persistence":20,"relative_strength":20,"value":15,"liquidity":10,"low_volatility":10},"quality":"not scored: reliable point-in-time quality fundamentals are not currently available in the existing data feed","momentum":"cross-sectional percentile of 1-month return","trend_persistence":"fraction of available 1/3/6/12-month horizons with positive return; 12-month variant excludes most recent month where history permits","relative_strength":"existing SPC Relative Strength score","value":"existing monthly Value Gap transformed with signed log then ranked; not a standalone valuation conclusion","liquidity":"latest volume divided by median of prior 20 sessions","low_volatility":"inverse annualized standard deviation of daily close-to-close returns","mean_reversion":"OU-style half-life estimated on log(close/SMA20), screening range 2-30 sessions","backtest":"next-session entry, 5/20-session exit; 0.30% assumed round-trip costs; overlapping pooled observations; not portfolio simulation"},"signals":[{"id":"factor","name":"Multi-Factor Alpha","status":"active","description":"Cross-sectional ranking across available Momentum, Trend Persistence, Relative Strength, Value Gap, Liquidity, and Low Volatility. Quality is deliberately not imputed without reliable point-in-time fundamentals.","count":sum(1 for x in rows if finite(x["factor_score"]))},{"id":"trend","name":"Trend Persistence & Momentum Quality","status":"active","description":"Checks 1/3/6/12-month return consistency and a momentum variant excluding the latest month.","count":len(rows)},{"id":"regime","name":"Market Regime & Adaptive Signals","status":"context","description":"Uses the existing HMM market regime probabilities as context. It does not independently issue buy/sell orders.","count":1},{"id":"relative","name":"Cross-Sectional Relative Strength","status":"active","description":"Existing percentile-style SPC relative strength ranking and sector/IHSG excess return.","count":len(rs)},{"id":"breadth","name":"Breadth & Sector Rotation","status":"context","description":"Uses existing sector rotation and technical signal universe as context; a full historical breadth series is not inferred if unavailable.","count":len(sectors.get("sectors",[])) if isinstance(sectors.get("sectors",[]),list) else 0},{"id":"risk","name":"Volatility-Adjusted Risk & Position Sizing","status":"partial","description":"Displays annualized realized volatility, an absolute-return ATR proxy, and risk flags. Position size is a scenario estimate, not a personalized allocation.","count":sum(bool(x["risk_flags"]) for x in rows)},{"id":"ou","name":"Mean Reversion & OU Half-Life","status":"active","description":"OU-style estimate on log(close/SMA20), with half-life limited to 2–30 sessions; R² is diagnostic only and not a stationarity test.","count":sum(finite(x["ou_half_life"]) for x in rows)},{"id":"validation","name":"Signal Validation & Walk-Forward Lab","status":"exploratory","description":"Rolling historical momentum proxy with next-session entry, 5/20-session exit, assumed costs, and a market-universe baseline. Not yet a full portfolio-level walk-forward engine.","results":bt}],"summary":{"factor_top":[{"ticker":x["ticker"],"score":x["factor_score"]} for x in rows[:10]],"risk_flags":sum(bool(x["risk_flags"]) for x in rows),"ou_candidates":sum(finite(x["ou_half_life"]) and finite(x["zscore"]) and abs(x["zscore"])>=1.5 for x in rows),"quality_factor_available":False},"stocks":rows}
 out=D/"signal-intelligence.json"; out.write_text(json.dumps(payload,separators=(",",":"),allow_nan=False),encoding="utf-8")
 print(f"Signal Intelligence: {len(rows)} stocks; top factor score {rows[0]['ticker'] if rows else 'n/a'}; {out.stat().st_size/1024:.1f} KB")
if __name__=="__main__": main()
