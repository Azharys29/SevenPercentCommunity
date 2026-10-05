#!/usr/bin/env python3
"""Validate Technical Trade Journal output and trading-rule invariants."""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JOURNAL = ROOT / "data/technical-journal.json"

MIN_SCORE = 25
MIN_AGREE = 3
MIN_RR = 1.5
RSI_MIN = 50
RSI_MAX = 70

ALLOWED_STATUSES = {
    "WAITING ENTRY",
    "ENTRY HIT",
    "TP1 HIT",
    "TP2 HIT",
    "STOP LOSS HIT",
    "TP1 & SL TOUCHED",
    "TP2 & SL TOUCHED",
    "EXPIRED",
}

CLOSED_STATUSES = {
    "TP2 HIT",
    "STOP LOSS HIT",
    "TP1 & SL TOUCHED",
    "TP2 & SL TOUCHED",
    "EXPIRED",
}


def fail(message):
    raise AssertionError(message)


def finite_number(value, field, ticker):
    if isinstance(value, bool):
        fail(f"{ticker}: {field} must be numeric, got bool")
    try:
        value = float(value)
    except (TypeError, ValueError):
        fail(f"{ticker}: {field} is not numeric: {value!r}")
    if not math.isfinite(value):
        fail(f"{ticker}: {field} is not finite")
    return value


def main():
    if not JOURNAL.exists():
        fail("technical-journal.json is missing")

    data = json.loads(JOURNAL.read_text())
    if not isinstance(data, dict):
        fail("technical-journal.json root must be an object")

    trades = data.get("trades")
    if not isinstance(trades, list):
        fail("technical-journal.json 'trades' must be a list")

    trade_count = data.get("trade_count")
    if trade_count != len(trades):
        fail(f"trade_count={trade_count} but actual trades={len(trades)}")

    active_count = data.get("active_count")
    if not isinstance(active_count, int):
        fail("active_count must be an integer")

    diagnostics = data.get("diagnostics", {})
    if not isinstance(diagnostics, dict):
        fail("diagnostics must be an object")

    diagnostic_keys = [
        "universe",
        "bullish",
        "fresh_bullish",
        "score_ok",
        "confluence_ok",
        "rsi_ok",
        "fib_rr_ok",
        "already_recorded",
        "rejected_no_stock",
    ]
    for key in diagnostic_keys:
        value = diagnostics.get(key)
        if not isinstance(value, int) or value < 0:
            fail(f"diagnostics.{key} must be a non-negative integer")

    if diagnostics["bullish"] > diagnostics["universe"]:
        fail("diagnostics: bullish > universe")
    if diagnostics["fresh_bullish"] > diagnostics["bullish"]:
        fail("diagnostics: fresh_bullish > bullish")
    if diagnostics["score_ok"] > diagnostics["fresh_bullish"]:
        fail("diagnostics: score_ok > fresh_bullish")
    if diagnostics["confluence_ok"] > diagnostics["score_ok"]:
        fail("diagnostics: confluence_ok > score_ok")
    if diagnostics["rsi_ok"] > diagnostics["confluence_ok"]:
        fail("diagnostics: rsi_ok > confluence_ok")
    if diagnostics["fib_rr_ok"] > diagnostics["rsi_ok"]:
        fail("diagnostics: fib_rr_ok > rsi_ok")
    if diagnostics["already_recorded"] > diagnostics["rsi_ok"]:
        fail("diagnostics: already_recorded > rsi_ok")
    if diagnostics["rejected_no_stock"] > diagnostics["rsi_ok"]:
        fail("diagnostics: rejected_no_stock > rsi_ok")

    seen = set()
    active = 0

    for idx, trade in enumerate(trades, 1):
        if not isinstance(trade, dict):
            fail(f"trade #{idx} must be an object")

        ticker = str(trade.get("ticker") or f"trade#{idx}")
        required = [
            "setup_id",
            "ticker",
            "signal",
            "direction",
            "signal_date",
            "score",
            "confluence",
            "entry",
            "stop_loss",
            "tp1",
            "tp2",
            "risk_pct",
            "rr_tp1",
            "rr_tp2",
            "status",
            "entry_hit",
            "tp1_hit",
            "tp2_hit",
            "sl_hit",
            "closed",
        ]
        missing = [field for field in required if field not in trade]
        if missing:
            fail(f"{ticker}: missing required fields: {', '.join(missing)}")

        setup_id = trade["setup_id"]
        if not isinstance(setup_id, str) or not setup_id:
            fail(f"{ticker}: invalid setup_id")
        if setup_id in seen:
            fail(f"{ticker}: duplicate setup_id {setup_id}")
        seen.add(setup_id)

        if trade["signal"] != "Bullish":
            fail(f"{ticker}: journal contains non-Bullish signal")
        if trade["direction"] != "LONG":
            fail(f"{ticker}: journal contains non-LONG direction")
        if not bool(trade.get("new_bullish", True)):
            fail(f"{ticker}: trade is not marked as fresh bullish")
        
        score = finite_number(trade["score"], "score", ticker)
        agree = int(trade["confluence"])
        if score < MIN_SCORE:
            fail(f"{ticker}: score {score} < {MIN_SCORE}")
        if agree < MIN_AGREE or agree > 5:
            fail(f"{ticker}: confluence {agree} outside 3/5..5/5")

        if "rsi" not in trade:
            fail(f"{ticker}: RSI missing from journal trade")
        rsi = finite_number(trade["rsi"], "rsi", ticker)
        if not (RSI_MIN <= rsi < RSI_MAX):
            fail(f"{ticker}: RSI {rsi} outside {RSI_MIN}–<{RSI_MAX}")

        entry = finite_number(trade["entry"], "entry", ticker)
        sl = finite_number(trade["stop_loss"], "stop_loss", ticker)
        tp1 = finite_number(trade["tp1"], "tp1", ticker)
        tp2 = finite_number(trade["tp2"], "tp2", ticker)
        risk_pct = finite_number(trade["risk_pct"], "risk_pct", ticker)
        rr1 = finite_number(trade["rr_tp1"], "rr_tp1", ticker)
        rr2 = finite_number(trade["rr_tp2"], "rr_tp2", ticker)

        if not (entry > sl):
            fail(f"{ticker}: LONG requires Entry > Stop Loss")
        if not (tp1 > entry):
            fail(f"{ticker}: LONG requires TP1 > Entry")
        if not (tp2 > tp1):
            fail(f"{ticker}: LONG requires TP2 > TP1")
        if not (risk_pct > 0):
            fail(f"{ticker}: risk_pct must be > 0")
        if rr1 < MIN_RR:
            fail(f"{ticker}: TP1 R:R {rr1} < {MIN_RR}")
        if rr2 < rr1:
            fail(f"{ticker}: TP2 R:R {rr2} < TP1 R:R {rr1}")

        for field in ("swing_low", "swing_high", "fib_range", "fib_1272", "fib_1618"):
            if field not in trade:
                fail(f"{ticker}: missing Fibonacci field {field}")
            finite_number(trade[field], field, ticker)

        if trade["swing_high"] <= trade["swing_low"]:
            fail(f"{ticker}: swing high must be above swing low")
        if trade["anchor_low_index"] >= trade["anchor_high_index"]:
            fail(f"{ticker}: Fibonacci anchors are not ordered low -> high")

        status = trade["status"]
        if status not in ALLOWED_STATUSES:
            fail(f"{ticker}: invalid status {status!r}")

        closed = bool(trade["closed"])
        if closed:
            if status not in CLOSED_STATUSES:
                fail(f"{ticker}: closed trade has non-terminal status {status!r}")
            if not trade.get("close_date"):
                fail(f"{ticker}: closed trade missing close_date")
            finite_number(trade.get("close_price"), "close_price", ticker)
        else:
            active += 1
            if status in CLOSED_STATUSES:
                fail(f"{ticker}: open trade has terminal status {status!r}")

        entry_hit = bool(trade["entry_hit"])
        tp1_hit = bool(trade["tp1_hit"])
        tp2_hit = bool(trade["tp2_hit"])
        sl_hit = bool(trade["sl_hit"])

        if tp2_hit and not tp1_hit:
            fail(f"{ticker}: TP2 hit requires TP1 hit")
        if status == "WAITING ENTRY" and entry_hit:
            fail(f"{ticker}: WAITING ENTRY cannot have entry_hit=true")
        if status == "ENTRY HIT" and (not entry_hit or tp1_hit or tp2_hit or sl_hit):
            fail(f"{ticker}: ENTRY HIT flags are inconsistent")
        if status == "TP1 HIT" and (not entry_hit or not tp1_hit or tp2_hit or sl_hit or closed):
            fail(f"{ticker}: TP1 HIT flags are inconsistent")
        if status == "TP2 HIT" and (not entry_hit or not tp2_hit or sl_hit or not closed):
            fail(f"{ticker}: TP2 HIT flags are inconsistent")
        if status == "STOP LOSS HIT" and (not entry_hit or not sl_hit or not closed):
            fail(f"{ticker}: STOP LOSS HIT flags are inconsistent")
        if status == "TP1 & SL TOUCHED" and (not entry_hit or not tp1_hit or not sl_hit or closed is not True):
            fail(f"{ticker}: TP1 & SL TOUCHED flags are inconsistent")
        if status == "TP2 & SL TOUCHED" and (not entry_hit or not tp2_hit or not tp1_hit or not sl_hit or closed is not True):
            fail(f"{ticker}: TP2 & SL TOUCHED flags are inconsistent")
        if status == "EXPIRED" and not closed:
            fail(f"{ticker}: EXPIRED must be closed")

    if active_count != active:
        fail(f"active_count={active_count} but calculated active={active}")

    print(
        f"Technical Trade Journal PASS: {len(trades)} trades, "
        f"{active} active, {len(seen)} unique setup IDs"
    )


if __name__ == "__main__":
    main()
