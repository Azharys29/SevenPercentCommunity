import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/commodity-play.json"
MAP = ROOT / "data/commodity-map.json"

KEMENDAG_URL = "https://satudata.kemendag.go.id/data-informasi/perdagangan-luar-negeri/harga-internasional"
WORLD_BANK_XLSX = "https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx"

WANTED = {
    "Brent Oil": {"unit": "USD/bbl", "wb": ["Crude oil, Brent"]},
    "Natural Gas": {"unit": "USD/MMBtu", "wb": ["Natural gas, U.S.", "Natural gas, Europe"]},
    "Coal": {"unit": "USD/mt", "kem": "Coal, Australian"},
    "Gold": {"unit": "USD/toz", "kem": "Gold"},
    "Nickel": {"unit": "USD/mt", "kem": "Nickel"},
    "Timah": {"unit": "USD/mt", "kem": "Tin"},
    "Copper": {"unit": "USD/mt", "kem": "Copper"},
    "Palm Oil": {"unit": "USD/mt", "kem": "Palm oil"},
}

def num(v):
    try:
        return float(str(v).replace(",", "").strip())
    except Exception:
        return None

def parse_kemendag():
    html = requests.get(KEMENDAG_URL, timeout=30, headers={"User-Agent": "SevenPercentCommunity/CommodityPlay"}).text
    # The public table is monthly Jan-Dec. Use the last two populated months.
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
        # cells[0] is unit; remaining are Jan-Dec values.
        values = [num(x) for x in cells[1:]]
        values = [x for x in values if x is not None]
        if values:
            result[name] = {"price": values[-1], "previous": values[-2] if len(values) > 1 else None, "unit": cfg["unit"], "period": "latest public monthly value", "source": "Kemendag / World Bank"}
    return result

def parse_world_bank():
    # XLSX is public and does not require an API key.
    import openpyxl
    raw = requests.get(WORLD_BANK_XLSX, timeout=60, headers={"User-Agent": "SevenPercentCommunity/CommodityPlay"})
    raw.raise_for_status()
    path = ROOT / ".commodity_worldbank.xlsx"
    path.write_bytes(raw.content)
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    result = {}
    wanted_labels = {label: name for name, cfg in WANTED.items() for label in cfg.get("wb", [])}
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            vals = [c.value for c in row]
            label = next((str(v).strip() for v in vals[:4] if v is not None and str(v).strip() in wanted_labels), None)
            if not label:
                continue
            nums = [num(v) for v in vals if num(v) is not None]
            if len(nums) >= 2:
                name = wanted_labels[label]
                result[name] = {"price": nums[-1], "previous": nums[-2], "unit": WANTED[name]["unit"], "period": "latest public monthly value", "source": "World Bank Pink Sheet"}
    try:
        path.unlink()
    except Exception:
        pass
    return result

def main():
    mapping = json.loads(MAP.read_text(encoding="utf-8"))
    prices = {}
    try:
        prices.update(parse_kemendag())
    except Exception as exc:
        print("Kemendag source warning:", exc)
    try:
        prices.update(parse_world_bank())
    except Exception as exc:
        print("World Bank source warning:", exc)

    commodities = []
    for name, cfg in WANTED.items():
        x = prices.get(name)
        if not x:
            commodities.append({"id": name, "name": name, "price": None, "previous": None, "change_pct": None, "unit": cfg["unit"], "source": None})
            continue
        prev = x.get("previous")
        price = x.get("price")
        pct = ((price / prev) - 1) * 100 if price is not None and prev not in (None, 0) else None
        commodities.append({
            "id": name, "name": name, "price": price, "previous": prev,
            "change_pct": pct, "unit": x["unit"], "period": x.get("period"),
            "source": x.get("source")
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
        # Cap display contribution so one extreme commodity move cannot dominate the UI.
        impact = max(-5.0, min(5.0, signed))
        direction = "UP" if move > 0.25 else "DOWN" if move < -0.25 else "FLAT"
        expected = "UP" if signed > 0.25 else "DOWN" if signed < -0.25 else "FLAT"
        impacts.append({
            "ticker": m["ticker"], "commodity": c["name"], "commodity_id": c["id"],
            "commodity_direction": direction, "commodity_change_pct": move,
            "expected_direction": expected, "impact_score": impact,
            "weight": weight, "note": m.get("note", ""), "source": c.get("source")
        })

    # Aggregate multiple commodity exposures per issuer.
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
        "source": "World Bank Pink Sheet + Kemendag Satu Data",
        "methodology": "Monthly benchmark change × mapping weight, capped at ±5 per commodity exposure. Direction is an exposure indicator, not a price target.",
        "commodities": commodities,
        "impacts": impacts,
        "mapping_count": len(mapping.get("stocks", []))
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Commodity Play: {len([x for x in commodities if x.get('price') is not None])}/8 commodities, {len(impacts)} mapped impacts")

if __name__ == "__main__":
    main()
