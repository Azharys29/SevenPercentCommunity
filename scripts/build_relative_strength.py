#!/usr/bin/env python3
"""Build lightweight Relative Strength ranking from screener OHLCV."""
import datetime as dt, json, math, statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
DATA=ROOT/"data/screener.json"; OUT=ROOT/"data/relative-strength.json"
H=(1,5,20,60)
def ret(c,n):
    return (c[-1]/c[-1-n]-1)*100 if len(c)>n and c[-1-n] else None
def rank(vals):
    valid=[x for x in vals if x is not None]
    if not valid:return [None]*len(vals)
    ordered=sorted(valid); out=[]
    for x in vals:
        if x is None: out.append(None)
        else:
            # percentile-style 0-100 rank, higher = stronger
            pos=sum(v<=x for v in ordered)-1
            out.append(round(100*pos/max(len(ordered)-1,1),1))
    return out
def main():
    d=json.loads(DATA.read_text()); stocks=d["stocks"]; bench=d.get("benchmark_history",{})
    rows=[]
    for s in stocks:
        c=list(map(float,s["c"])); rr={str(n):ret(c,n) for n in H}
        rows.append({"ticker":s["t"],"name":s["n"],"sector":s.get("s","Lainnya"),"returns":{k:(round(v,2) if v is not None else None) for k,v in rr.items()}})
    benchret={str(n):ret(bench.get("c",[]),n) for n in H}
    for n in H:
        key=str(n); ranks=rank([x["returns"][key] for x in rows])
        for x,rk in zip(rows,ranks): x.setdefault("rank",{})[key]=rk
    sector_stats={}
    for sec in sorted(set(x["sector"] for x in rows)):
        members=[x for x in rows if x["sector"]==sec]
        sector_stats[sec]={}
        for n in H:
            key=str(n); vals=[x["returns"][key] for x in members if x["returns"][key] is not None]
            sector_stats[sec][key]=round(statistics.mean(vals),2) if vals else None
    for x in rows:
        x["vs_ihsg"]={}; x["vs_sector"]={}
        for n in H:
            k=str(n); r=x["returns"][k]; br=benchret[k]; sr=sector_stats[x["sector"]][k]
            x["vs_ihsg"][k]=round(r-br,2) if r is not None and br is not None else None
            x["vs_sector"][k]=round(r-sr,2) if r is not None and sr is not None else None
        ranks=[x["rank"][str(n)] for n in H if x["rank"][str(n)] is not None]
        x["rs_score"]=round(sum(ranks)/len(ranks),1) if ranks else None
    rows.sort(key=lambda x:x["rs_score"] if x["rs_score"] is not None else -1,reverse=True)
    payload={"generated":dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),"asof":d["asof"],"universe":"KOMPAS100","universe_count":len(rows),
             "method":{"periods":[1,5,20,60],"rank":"cross-sectional percentile within KOMPAS100","vs_ihsg":"stock return minus IHSG return","vs_sector":"stock return minus average return of its KOMPAS100 sector"},
             "benchmark_returns":benchret,"sector_returns":sector_stats,"stocks":rows}
    OUT.write_text(json.dumps(payload,separators=(",",":"),allow_nan=False),encoding="utf-8")
    print(f"Relative Strength: {len(rows)} stocks")
if __name__=="__main__": main()
