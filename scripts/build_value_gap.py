#!/usr/bin/env python3
"""Build Value Gap Score for KOMPAS100 from Yahoo Finance."""
import datetime as dt, json, math, time
from pathlib import Path
import pandas as pd
import yfinance as yf

ROOT=Path(__file__).resolve().parent.parent
UNIVERSE=ROOT/"universe.csv"; SCREENER=ROOT/"data/screener.json"; OUT=ROOT/"data/value-gap.json"

def finite(v):
    try:
        x=float(v); return x if math.isfinite(x) else None
    except (TypeError,ValueError): return None

def pe_row(df):
    if df is None or df.empty: return None
    for idx in df.index:
        k=str(idx).lower().replace(" ","").replace("_","")
        if k in ("peratio","trailingpe","priceearnings"): return df.loc[idx]
    for idx in df.index:
        if "pe" in str(idx).lower() and "peg" not in str(idx).lower(): return df.loc[idx]
    return None

def pe_values(v):
    row=pe_row(v)
    if row is None: return None, []
    cur=finite(row.get("Current"))
    hist=[]
    for col in v.columns:
        if str(col).lower()=="current": continue
        x=finite(row.get(col))
        if x is not None and x>0: hist.append((str(col),x))
    hist=hist[:3]
    return (cur if cur and cur>0 else None), hist

def returns(t, asof):
    h=t.history(period="1y",auto_adjust=False)
    if h is None or h.empty: return None,None
    c=h["Close"].dropna()
    if len(c)<22: return None,None
    last=finite(c.iloc[-1]); base=finite(c.iloc[-22])
    r1m=(last/base-1)*100 if last and base and base>0 else None
    cy=c[c.index.year==asof.year]
    rY=(last/float(cy.iloc[0])-1)*100 if last and len(cy) and float(cy.iloc[0])>0 else None
    return r1m,rY

def main():
    u=pd.read_csv(UNIVERSE,dtype=str).fillna("")
    screen=json.loads(SCREENER.read_text(encoding="utf-8"))
    asof=dt.date.fromisoformat(str(screen["asof"])[:10])
    rows=[]; errors=[]
    for _,r in u.iterrows():
        ticker=str(r["ticker"]).strip().upper()
        if not ticker: continue
        try:
            t=yf.Ticker(ticker+".JK")
            val=t.get_valuation_measures(freq="yearly",periods=4)
            info=t.info or {}
            cur,hist=pe_values(val)
            if cur is None: cur=finite(info.get("trailingPE"))
            hist3=[x for _,x in hist if x>0]
            avg=sum(hist3)/3 if len(hist3)==3 else None
            growth=finite(info.get("earningsGrowth"))
            if growth is not None and abs(growth)<2: growth*=100
            r1m,ry=returns(t,asof)
            score=(avg-cur)*growth if avg is not None and cur is not None and growth is not None else None
            rows.append({"ticker":ticker,"name":str(r["name"]).strip() or ticker,"sector":str(r["sector"]).strip() or "Lainnya",
                "current_pe":round(cur,2) if cur is not None else None,"avg_pe_3y":round(avg,2) if avg is not None else None,
                "eps_growth":round(growth,2) if growth is not None else None,"value_gap_score":round(score,2) if score is not None else None,
                "return_1m":round(r1m,2) if r1m is not None else None,"return_ytd":round(ry,2) if ry is not None else None,
                "pe_history":[{"period":p,"pe":round(x,2)} for p,x in hist],"status":"ok" if score is not None else "incomplete"})
        except Exception:
            errors.append(ticker)
            rows.append({"ticker":ticker,"name":str(r["name"]).strip() or ticker,"sector":str(r["sector"]).strip() or "Lainnya",
                "current_pe":None,"avg_pe_3y":None,"eps_growth":None,"value_gap_score":None,"return_1m":None,"return_ytd":None,"pe_history":[],"status":"error"})
        time.sleep(.05)
    rows.sort(key=lambda x:(x["value_gap_score"] is None,-(x["value_gap_score"] or 0)))
    payload={"generated":dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),"asof":asof.isoformat(),"universe":"KOMPAS100",
      "universe_count":len(rows),"valid_count":sum(x["value_gap_score"] is not None for x in rows),"error_count":len(errors),
      "formula":"(Average 3Y P/E - Current P/E) × EPS Growth (%)",
      "eps_growth_definition":"Yahoo Finance trailing EPS growth (earningsGrowth), shown as percent",
      "sources":["Yahoo Finance / yfinance"],"stocks":rows}
    OUT.write_text(json.dumps(payload,separators=(",",":"),ensure_ascii=False),encoding="utf-8")
    print(f"Value Gap: {payload['valid_count']}/{payload['universe_count']} valid, asof {payload['asof']}, errors {payload['error_count']}")

if __name__=="__main__": main()
