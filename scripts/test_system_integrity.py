#!/usr/bin/env python3
"""Validate cross-module data integrity after all builders have run."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
D=ROOT/"data"

def load(name):
    p=D/name
    if not p.exists(): raise AssertionError(f"missing {name}")
    return json.loads(p.read_text())

def main():
    sc=load("screener.json"); sig=load("signals.json")
    tickers={x["t"] for x in sc["stocks"]}
    signal_tickers={x["ticker"] for x in sig["signals"]}
    assert sc["universe_count"] == 100, f"unexpected universe {sc['universe_count']}"
    assert sc["success_count"] >= 90, f"too many market-data failures: {sc['success_count']}/100"
    assert len(tickers)==len(sc["stocks"]), "duplicate screener tickers"
    assert len(signal_tickers)==len(sig["signals"]), "duplicate signal tickers"
    assert signal_tickers <= tickers, "signals contain tickers absent from screener"
    for x in sig["signals"]:
        assert x["signal"] in {"Bullish","Bearish","Neutral"}
        assert -100 <= float(x["score"]) <= 100
        assert int(x["agree"]) <= int(x["total"]) == 5
    for name in ["market-intelligence.json","sector-rotation.json","backtest.json","relative-strength.json","momentum.json","catalysts.json","value-gap.json"]:
        load(name)
    print(f"System integrity PASS: {len(tickers)} stocks, {len(signal_tickers)} signals")

if __name__=="__main__":
    main()
