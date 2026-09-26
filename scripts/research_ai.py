#!/usr/bin/env python3
"""Research NEW BULLISH candidates with OpenAI web search."""
import json, os, re, urllib.request
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
QUEUE=ROOT/"data"/"ai-research.json"
MAX_ITEMS=int(os.getenv("AI_RESEARCH_MAX","5"))
MODEL=os.getenv("OPENAI_MODEL","gpt-5.6-luna")
API_URL="https://api.openai.com/v1/responses"

def call_openai(item):
    prompt = """You are an equity research assistant for an Indonesian capital-markets screener.

Research ticker TICKER (NAME) using CURRENT web information.
Technical context:
- as-of: ASOF
- price: PRICE
- score: SCORE
- score delta: SCORE_DELTA
- signal: SIGNAL
- strength: STRENGTH
- confluence: CONFLUENCE
- RSI: RSI
- Stoch K/D: STOCHK/STOCHD
- MACD histogram %: MACD
- RVOL: RVOL

Search recent and material company/sector news, preferably primary sources, IDX/company disclosures, reputable Indonesian business media, and major financial news.
Return ONLY valid JSON with these keys:
{"narrative":"2-4 sentence professional research commentary in Indonesian. Separate verified facts from interpretation. If no material recent catalyst is found, explicitly say so.","catalysts":["verified catalyst 1"],"risks":["verified/current risk 1"],"sentiment":"Positif|Netral|Negatif|Campuran","source_urls":["https://..."]}
Do not invent facts, catalysts, risks, or URLs. Use empty arrays when no reliable item is found."""
    vals={"TICKER":item["ticker"],"NAME":item.get("name",""),"ASOF":item.get("asof"),"PRICE":item.get("price"),"SCORE":item.get("score"),"SCORE_DELTA":item.get("score_delta"),"SIGNAL":item.get("signal"),"STRENGTH":item.get("strength"),"CONFLUENCE":item.get("confluence"),"RSI":item.get("rsi"),"STOCHK":item.get("stoch_k"),"STOCHD":item.get("stoch_d"),"MACD":item.get("macd_hist_pct"),"RVOL":item.get("rvol")}
    for k,v in vals.items(): prompt=prompt.replace(k,str(v))
    payload={"model":MODEL,"tools":[{"type":"web_search","search_context_size":"medium"}],"input":prompt,"include":["web_search_call.action.sources"]}
    req=urllib.request.Request(API_URL,data=json.dumps(payload).encode(),headers={"Authorization":"Bearer "+os.environ["OPENAI_API_KEY"],"Content-Type":"application/json"},method="POST")
    with urllib.request.urlopen(req,timeout=120) as resp: data=json.load(resp)
    text=data.get("output_text","").strip()
    if not text:
        for src in data.get("web_search_call",{}).get("action",{}).get("sources",[]) or []:
        u=src.get("url")
        if u and u not in urls: urls.append(u)
    for out in data.get("output",[]):
            if out.get("type")=="message":
                for part in out.get("content",[]):
                    if part.get("type")=="output_text": text=part.get("text","").strip(); break
    text=re.sub(r"^```json\\s*","",text,flags=re.I); text=re.sub(r"\\s*```$","",text).strip()
    result=json.loads(text); urls=list(result.get("source_urls") or [])
    if not isinstance(result,dict): raise ValueError("AI response is not a JSON object")
    for out in data.get("output",[]):
        for part in out.get("content",[]) if out.get("type")=="message" else []:
            for ann in part.get("annotations",[]):
                if ann.get("type")=="url_citation":
                    u=ann.get("url_citation",{}).get("url")
                    if u and u not in urls: urls.append(u)
    return result,urls

def main():
    if not os.getenv("OPENAI_API_KEY"): print("OPENAI_API_KEY not configured; AI research skipped safely."); return
    payload=json.loads(QUEUE.read_text(encoding="utf-8")); pending=[x for x in payload.get("queue",[]) if x.get("status")=="PENDING_RESEARCH"][:MAX_ITEMS]
    if not pending: print("No pending AI research candidates."); return
    done=0
    for item in pending:
        try:
            result,urls=call_openai(item); item.update({"status":"RESEARCHED","researched_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),"narrative":result.get("narrative"),"catalysts":result.get("catalysts") or [],"risks":result.get("risks") or [],"sentiment":result.get("sentiment"),"sources":urls}); done+=1; print("Researched "+item["ticker"])
        except Exception as exc: print("Research failed for "+item.get("ticker","?")+": "+str(exc))
    payload["generated"]=datetime.now(timezone.utc).isoformat(timespec="seconds"); QUEUE.write_text(json.dumps(payload,ensure_ascii=False,separators=(",",":")),encoding="utf-8"); print(json.dumps({"researched":done,"pending_total":len(pending)}))
if __name__=="__main__": main()