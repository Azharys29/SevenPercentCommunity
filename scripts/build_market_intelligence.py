#!/usr/bin/env python3
"""Build rule-based Market Intelligence from technical signals + public Google News RSS."""
import html,json,re,time,urllib.parse,urllib.request,xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
SIGNALS=ROOT/"data/signals.json"; OUT=ROOT/"data/market-intelligence.json"
MAX_ITEMS=10; MAX_NEWS=5
POSITIVE_TERMS=["naik","meningkat","tumbuh","pertumbuhan","ekspansi","kontrak baru","pesanan","kerja sama","dividen","laba","pendapatan","rebound","bullish","akuisisi","guidance naik","target naik","investasi"]
NEGATIVE_TERMS=["turun","menurun","penurunan","rugi","kerugian","utang","dilusi","private placement","gugatan","suspensi","phk","pemutusan hubungan kerja","guidance turun","target turun","downgrade","bearish","default"]
def clean_text(v):
    v=html.unescape(v or ""); v=re.sub(r"<[^>]+>"," ",v); return re.sub(r"\s+"," ",v).strip()
def news_sentiment(title,description):
    t=(title+" "+description).lower(); p=sum(1 for x in POSITIVE_TERMS if x in t); n=sum(1 for x in NEGATIVE_TERMS if x in t)
    return "Campuran" if p and n else "Positif" if p else "Negatif" if n else "Netral"
def market_sentiment(score,agree,total):
    if score>=60 and agree>=3:return "Strong Positive"
    if score>=35 and agree>=3:return "Positive"
    if score<=-35 and agree>=3:return "Strong Negative"
    if score<=-15 and agree>=3:return "Negative"
    return "Neutral"
def interpretation(x):
    score=float(x.get("score") or 0); agree=int(x.get("agree") or 0); total=int(x.get("total") or 4)
    base="Momentum bullish kuat" if score>=60 else "Momentum bullish" if score>=35 else "Momentum bearish kuat" if score<=-60 else "Momentum bearish" if score<=-35 else "Momentum belum menunjukkan dominasi yang jelas"
    notes=[]; sk=float(x.get("stoch_k") or 50); sd=float(x.get("stoch_d") or 50); macd=float(x.get("macd_hist_pct") or 0); rvol=float(x.get("rvol") or 0)
    if sk>=80 and sk>sd: notes.append("Stochastic berada di area tinggi sehingga risiko perlambatan momentum perlu dipantau")
    elif sk<=20 and sk<sd: notes.append("Stochastic berada di area rendah sehingga potensi rebound perlu dipantau")
    if macd>0: notes.append("MACD histogram positif")
    elif macd<0: notes.append("MACD histogram negatif")
    if rvol>=1.2: notes.append("volume relatif di atas rata-rata 20 hari")
    elif rvol<0.8: notes.append("volume relatif masih di bawah rata-rata 20 hari")
    return f"{base} dengan konfluensi {agree}/{total}. "+". ".join(notes[:2])+"." if notes else f"{base} dengan konfluensi {agree}/{total}."
def fetch_news(ticker,name):
    q=f'"{ticker}" saham' if not name or name.upper()==ticker.upper() else f'"{ticker}" "{name}" saham'
    url="https://news.google.com/rss/search?"+urllib.parse.urlencode({"q":q,"hl":"id","gl":"ID","ceid":"ID:id"})
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 SevenPercentCommunity/1.0"})
    try:
        with urllib.request.urlopen(req,timeout=20) as r: root=ET.fromstring(r.read())
    except Exception as e:
        print(f"news fetch failed {ticker}: {e}"); return []
    out=[]
    for item in root.findall("./channel/item")[:MAX_NEWS]:
        title=clean_text(item.findtext("title")); link=item.findtext("link") or ""; pub=item.findtext("pubDate") or ""; desc=clean_text(item.findtext("description")); se=item.find("source"); source=clean_text(se.text if se is not None else "")
        if title and link: out.append({"title":title,"source":source or "Google News","published":pub,"url":link,"sentiment":news_sentiment(title,desc)})
    return out
def main():
    s=json.loads(SIGNALS.read_text(encoding="utf-8"))
    c=[x for x in s.get("signals",[]) if x.get("signal")=="Bullish" and float(x.get("score") or 0)>=35 and int(x.get("agree") or 0)>=3]
    c=sorted(c,key=lambda x:float(x.get("score") or 0),reverse=True)[:MAX_ITEMS]; items=[]
    for x in c:
        items.append({"ticker":x.get("ticker"),"name":x.get("name",""),"asof":x.get("asof"),"score":x.get("score"),"score_delta":x.get("score_delta"),"signal":x.get("signal"),"strength":x.get("strength"),"confluence":f'{x.get("agree",0)}/{x.get("total",0)}',"rsi":x.get("rsi"),"stoch_k":x.get("stoch_k"),"stoch_d":x.get("stoch_d"),"macd_hist_pct":x.get("macd_hist_pct"),"rvol":x.get("rvol"),"market_sentiment":market_sentiment(float(x.get("score") or 0),int(x.get("agree") or 0),int(x.get("total") or 4)),"interpretation":interpretation(x),"news":fetch_news(x.get("ticker",""),x.get("name","")),"updated_at":datetime.now(timezone.utc).isoformat(timespec="seconds")}); time.sleep(.25)
    OUT.write_text(json.dumps({"generated":datetime.now(timezone.utc).isoformat(timespec="seconds"),"asof":s.get("asof"),"candidate_count":len(items),"news_status":"Google News RSS","items":items},ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    print(json.dumps({"candidate_count":len(items),"news_articles":sum(len(x["news"]) for x in items)}))
if __name__=="__main__": main()
