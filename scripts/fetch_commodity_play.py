import json, os, re
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/commodity-play.json'
MAP=ROOT/'data/commodity-map.json'
API='https://api.tradingeconomics.com/markets/commodities'
KEY=os.getenv('TRADING_ECONOMICS_API_KEY','guest:guest')
WANTED={
 'Brent Oil':['Brent'], 'Natural Gas':['Natural gas','Natural Gas'], 'Coal':['Coal'], 'Gold':['Gold'],
 'Nickel':['Nickel'], 'Timah':['Tin'], 'Copper':['Copper'], 'Palm Oil':['Palm Oil']
}
UNIT={'Brent Oil':'USD/Bbl','Natural Gas':'USD/MMBtu','Coal':'USD/T','Gold':'USD/t.oz','Nickel':'USD/T','Timah':'USD/T','Copper':'USD/Lbs','Palm Oil':'MYR/T'}

def num(v):
 try:return float(v)
 except:return None

def main():
 r=requests.get(API,params={'c':KEY,'f':'json'},timeout=30,headers={'User-Agent':'SevenPercentCommunity/CommodityPlay'})
 r.raise_for_status(); raw=r.json()
 if isinstance(raw,dict): raw=raw.get('data',[])
 by={str(x.get('Name') or x.get('name') or '').strip().lower():x for x in raw}
 commodities=[]
 for name,aliases in WANTED.items():
  row=next((by.get(a.lower()) for a in aliases if by.get(a.lower())),None)
  if not row: continue
  price=num(row.get('Price') if 'Price' in row else row.get('price'))
  change=num(row.get('Change') if 'Change' in row else row.get('change'))
  pct=num(row.get('PercentChange') if 'PercentChange' in row else row.get('percentChange'))
  if pct is None and price is not None and change is not None and price-change: pct=change/(price-change)*100
  commodities.append({'id':name,'name':name,'symbol':row.get('Symbol') or row.get('symbol'),'price':price,'previous':price-change if price is not None and change is not None else None,'change':change,'change_pct':pct,'unit':UNIT[name],'date':row.get('Date') or row.get('date')})
 mapping=json.loads(MAP.read_text()) if MAP.exists() else {'stocks':[]}
 impacts=[]
 lookup={c['id']:c for c in commodities}
 for x in mapping.get('stocks',[]):
  c=lookup.get(x.get('commodity'))
  if not c or c.get('change_pct') is None: continue
  move=c['change_pct']; w=max(0,num(x.get('weight')) or 1); sign=num(x.get('impact_up')) or 0
  direction='UP' if move>0.25 else 'DOWN' if move<-0.25 else 'FLAT'
  expected='UP' if move>0.25 and sign>0 or move<-0.25 and (num(x.get('impact_down')) or 0)>0 else 'DOWN' if move>0.25 and sign<0 or move<-0.25 and (num(x.get('impact_down')) or 0)<0 else 'FLAT'
  impact=abs(move)*w* (1 if expected!='FLAT' else 0)
  impacts.append({'ticker':x.get('ticker'),'commodity':c['name'],'commodity_id':c['id'],'commodity_direction':direction,'commodity_change_pct':move,'expected_direction':expected,'impact_score':impact,'weight':w,'note':x.get('note','')})
 impacts.sort(key=lambda z:z['impact_score'],reverse=True)
 payload={'generated':datetime.now(timezone.utc).isoformat(),'asof':max([x.get('date') or '' for x in commodities],default=datetime.now(timezone.utc).date().isoformat()),'source':'Trading Economics','commodities':commodities,'impacts':impacts,'mapping_count':len(mapping.get('stocks',[]))}
 OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
 print(f'Commodity Play: {len(commodities)} commodities, {len(impacts)} mapped impacts')
if __name__=='__main__': main()
