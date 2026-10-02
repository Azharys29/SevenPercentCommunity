import json
import re
from datetime import datetime, timezone
from pathlib import Path

import csv
from io import StringIO

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/commodity-play.json"
MAP = ROOT / "data/commodity-map.json"

KEMENDAG_URL = "https://satudata.kemendag.go.id/data-informasi/perdagangan-luar-negeri/harga-internasional"
WORLD_BANK_XLSX = "https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx"
YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=1d&events=history"
FCPO_URLS = [
    "https://ifcpo.com.my/futures/FCPO",
    "https://www.tradingview.com/symbols/MYX-FCPO1!/",
]
HEADERS = {"User-Agent": "Mozilla/5.0 SevenPercentCommunity/CommodityPlay"}

WANTED = {
    "Brent Oil": {"unit": "USD/bbl", "kem": None},
    "Natural Gas": {"unit": "USD/MMBtu", "kem": None},
    "Coal": {"unit": "USD/mt", "kem": "Coal, Australian"},
    "Gold": {"unit": "USD/toz", "kem": "Gold"},
    "Nickel": {"unit": "USD/mt", "kem": "Nickel"},
    "Timah": {"unit": "USD/mt", "kem": "Tin"},
    "Copper": {"unit": "USD/mt", "kem": "Copper"},
    "Palm Oil": {"unit": "MYR/mt", "kem": None},
}

def num(v):
    try:
        return float(str(v).replace(",", "").strip())
    except Exception:
        return None

def yahoo_futures(symbol, unit):
    r = requests.get(YAHOO_CHART.format(symbol=symbol), timeout=20, headers=HEADERS)
    r.raise_for_status()
    data = r.json()["chart"]["result"][0]
    q = data["indicators"]["quote"][0]
    closes = q.get("close", [])
    timestamps = data.get("timestamp", [])
    vals = [(ts, float(v)) for ts, v in zip(timestamps, closes) if v is not None]
    if len(vals) < 2:
        raise ValueError(f"{symbol}: insufficient Yahoo Finance data")
    return {
        "price": vals[-1][1],
        "previous": vals[-2][1],
        "unit": unit,
        "period": datetime.fromtimestamp(vals[-1][0], timezone.utc).date().isoformat(),
        "source": f"Yahoo Finance {symbol}",
        "symbol": symbol,
    }

def parse_fcpo_page(html, source):
    # iFCPO publishes the continuous Bursa Malaysia FCPO price in RM.
    m = re.search(r"(?:Current Price|harga saat ini|harga terkini).*?(?:RM|MYR)\s*([0-9][0-9,]*(?:\.\d+)?)", html, re.I | re.S)
    change = re.search(r"(?:Daily Change|Perubahan Harian).*?(?:\+|−|-)?\s*([0-9][0-9,]*(?:\.\d+)?)\s*\(([-+]?\d+(?:\.\d+)?)%", html, re.I | re.S)
    if not m:
        # TradingView fallback: "current price ... 4,xxx MYR/TNE"
        m = re.search(r"(?:current price|harga saat ini).*?([0-9][0-9,]*(?:\.\d+)?)\s*MYR\s*/?\s*(?:TNE|tonne)", html, re.I | re.S)
        if not m:
            return None
    price = num(m.group(1))
    previous = None
    if change:
        daily_change = num(change.group(1))
        if daily_change is not None:
            # iFCPO's daily change is in RM/MT.
            sign = -1 if "−" in change.group(0) or re.search(r"\(-", change.group(0)) else 1
            previous = price - sign * daily_change
    if previous is None:
        # Fall back to the latest MPOB daily local CPO price if available.
        previous = None
    return {
        "price": price,
        "previous": previous,
        "unit": "MYR/mt",
        "period": datetime.now(timezone.utc).date().isoformat(),
        "source": "Bursa Malaysia FCPO / iFCPO",
        "symbol": "FCPO_CONT",
    }

def fetch_fcpo():
    errors = []
    for url in FCPO_URLS:
        try:
            r = requests.get(url, timeout=25, headers=HEADERS)
            r.raise_for_status()
            x = parse_fcpo_page(r.text, url)
            if x:
                return x
        except Exception as exc:
            errors.append(f"{url}: {exc}")
    raise RuntimeError("FCPO source unavailable: " + " | ".join(errors))

def parse_kemendag():
    html = requests.get(KEMENDAG_URL, timeout=30, headers=HEADERS).text
    rows = {}
    for m in re.finditer(r"<tr>(.*?)</tr>", html, re.S | re.I):
        cells = [re.sub(r"<[^>]+>", "", x).strip() for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", m.group(1), re.S | re.I)]
        if len(cells) >= 3:
            rows[re.sub(r"\s+", " ", cells[0]).strip()] = cells[1:]
    result = {}
    for name, cfg in WANTED.items():
        label = cfg.get("kem")
        if not label or label not in rows:
            continue
        cells = rows[label]
        values = [num(x) for x in cells[1:]]
        values = [x for x in values if x is not None]
        if values:
            result[name] = {
                "price": values[-1],
                "previous": values[-2] if len(values) > 1 else None,
                "unit": cfg["unit"],
                "period": "latest public monthly value",
                "source": "Kemendag / World Bank",
            }
    return result

def parse_world_bank():
    import openpyxl
    raw = requests.get(WORLD_BANK_XLSX, timeout=60, headers=HEADERS)
    raw.raise_for_status()
    path = ROOT / ".commodity_worldbank.xlsx"
    path.write_bytes(raw.content)
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    wanted_labels = {"Coal, Australian": "Coal", "Gold": "Gold", "Nickel": "Nickel", "Tin": "Timah", "Copper": "Copper"}
    result = {}
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            vals = [c.value for c in row]
            label = next((str(v).strip() for v in vals[:4] if v is not None and str(v).strip() in wanted_labels), None)
            if not label:
                continue
            nums = [num(v) for v in vals if num(v) is not None]
            if len(nums) >= 2:
                name = wanted_labels[label]
                result[name] = {
                    "price": nums[-1],
                    "previous": nums[-2],
                    "unit": WANTED[name]["unit"],
                    "period": "latest public monthly value",
                    "source": "World Bank Pink Sheet",
                }
    try:
        path.unlink()
    except Exception:
        pass
    return result

def main():
    mapping = json.loads(MAP.read_text(encoding="utf-8"))
    prices = {}

    # Use live futures rather than delayed monthly Pink Sheet/FRED values for energy.
    for name, symbol, unit in [
        ("Brent Oil", "BZ=F", "USD/bbl"),
        ("Natural Gas", "NG=F", "USD/MMBtu"),
    ]:
        try:
            prices[name] = yahoo_futures(symbol, unit)
            print(f"{name}: {prices[name]['price']} {unit} from Yahoo Finance")
        except Exception as exc:
            print(f"{name} warning:", exc)

    # CPO benchmark: Bursa Malaysia FCPO, denominated in MYR/metric ton.
    try:
        prices["Palm Oil"] = fetch_fcpo()
        print(f"Palm Oil: {prices['Palm Oil']['price']} MYR/mt from Bursa Malaysia FCPO")
    except Exception as exc:
        print("Palm Oil warning:", exc)

    try:
        prices.update(parse_kemendag())
    except Exception as exc:
        print("Kemendag source warning:", exc)

    try:
        wb = parse_world_bank()
        for k, v in wb.items():
            prices.setdefault(k, v)
    except Exception as exc:
        print("World Bank source warning:", exc)

    commodities = []
    for name, cfg in WANTED.items():
        x = prices.get(name)
        if not x:
            commodities.append({
                "id": name, "name": name, "price": None, "previous": None,
                "change_pct": None, "unit": cfg["unit"], "source": None
            })
            continue
        prev = x.get("previous")
        price = x.get("price")
        pct = ((price / prev) - 1) * 100 if price is not None and prev not in (None, 0) else None
        commodities.append({
            "id": name, "name": name, "price": price, "previous": prev,
            "change_pct": pct, "unit": x["unit"], "period": x.get("period"),
            "source": x.get("source"), "symbol": x.get("symbol"),
        })

    lookup = {x["id"]: x for x in commodities}
    impacts = []
    for m in mapping.get("stocks", []):
        c = lookup.get(m.get("commodity"))
        if not c or c.get("change_pct") is None:
            continue
        move = float(c["change_pct"])
        weight = max(0.0, num(m.get("weight")) or 1.0)
        up = num(m.get("impact_up")) or 0
        down = num(m.get("impact_down")) or 0
        signed = move * weight * (up if move >= 0 else abs(down))
        impact = max(-5.0, min(5.0, signed))
        direction = "UP" if move > 0.25 else "DOWN" if move < -0.25 else "FLAT"
        expected = "UP" if signed > 0.25 else "DOWN" if signed < -0.25 else "FLAT"
        impacts.append({
            "ticker": m["ticker"], "commodity": c["name"], "commodity_id": c["id"],
            "commodity_direction": direction, "commodity_change_pct": move,
            "expected_direction": expected, "impact_score": impact,
            "weight": weight, "note": m.get("note", ""), "source": c.get("source")
        })

    by_ticker = {}
    for x in impacts:
        by_ticker.setdefault(x["ticker"], []).append(x)
    for ticker, arr in by_ticker.items():
        total = sum(x["impact_score"] for x in arr)
        avg = total / len(arr)
        for x in arr:
            x["ticker_aggregate_impact"] = max(-5.0, min(5.0, total))
            x["ticker_average_impact"] = avg

    impacts.sort(key=lambda x: abs(x.get("ticker_aggregate_impact", x["impact_score"])), reverse=True)
    payload = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "asof": datetime.now(timezone.utc).date().isoformat(),
        "source": "Yahoo Finance futures + Bursa Malaysia FCPO + World Bank Pink Sheet + Kemendag",
        "methodology": "Live/near-live futures for Brent and Natural Gas; Bursa Malaysia FCPO in MYR/metric ton for Palm Oil; monthly benchmark data for other commodities. Impact is directional exposure, not a price target.",
        "commodities": commodities,
        "impacts": impacts,
        "mapping_count": len(mapping.get("stocks", []))
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Commodity Play: {len([x for x in commodities if x.get('price') is not None])}/8 commodities, {len(impacts)} mapped impacts")

if __name__ == "__main__":
    main()
