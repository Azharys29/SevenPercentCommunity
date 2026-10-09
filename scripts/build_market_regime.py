#!/usr/bin/env python3
"""Train a compact 3-state Gaussian HMM from daily IHSG return, volatility and KOMPAS100 breadth.
Runs only in GitHub Actions; the public page consumes the resulting small JSON file.
"""
import datetime as dt
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data/screener.json"
OUT = ROOT / "data/market-regime.json"


def main():
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    bench = payload.get("benchmark_history") or {}
    dates, closes = bench.get("d", []), bench.get("c", [])
    if len(dates) != len(closes) or len(closes) < 160:
        raise RuntimeError("HMM needs at least 160 daily IHSG closes")

    bench_df = pd.DataFrame({"date": dates, "close": pd.to_numeric(closes, errors="coerce")})
    bench_df = bench_df.dropna().drop_duplicates("date").sort_values("date")
    bench_df["ret"] = bench_df["close"].pct_change()
    bench_df["vol20"] = bench_df["ret"].rolling(20).std() * math.sqrt(252)

    # Daily breadth: fraction of stocks with positive daily return, aligned by date.
    up, total = {}, {}
    for stock in payload.get("stocks", []):
        sd, sc = stock.get("d", []), stock.get("c", [])
        for i in range(1, min(len(sd), len(sc))):
            try:
                prev, cur = float(sc[i - 1]), float(sc[i])
                if prev <= 0 or not math.isfinite(prev) or not math.isfinite(cur):
                    continue
                date = str(sd[i])
                total[date] = total.get(date, 0) + 1
                if cur > prev:
                    up[date] = up.get(date, 0) + 1
            except (TypeError, ValueError):
                continue

    bench_df["breadth"] = bench_df["date"].map(
        lambda d: up.get(d, 0) / total[d] if total.get(d, 0) >= 20 else np.nan
    )
    # All inputs are observable on that date; no future data enters the features.
    features = bench_df[["ret", "vol20", "breadth"]].replace([np.inf, -np.inf], np.nan)
    valid = features.dropna()
    if len(valid) < 120:
        raise RuntimeError(f"Insufficient aligned observations for HMM: {len(valid)}")

    # Robustly standardize to prevent volatility scale dominating returns/breadth.
    med = valid.median()
    scale = (valid.quantile(.75) - valid.quantile(.25)).replace(0, 1)
    x = ((valid - med) / scale).clip(-8, 8).to_numpy()
    model = GaussianHMM(n_components=3, covariance_type="diag", n_iter=100,
                        tol=1e-3, random_state=7, min_covar=1e-4)
    model.fit(x)
    posterior = model.predict_proba(x)
    hidden = model.predict(x)

    # Label states by their estimated mean daily IHSG return, not arbitrary state IDs.
    state_returns = {}
    raw_returns = valid["ret"].to_numpy()
    for state in range(3):
        vals = raw_returns[hidden == state]
        state_returns[state] = float(np.mean(vals)) if len(vals) else 0.0
    ranked = sorted(state_returns, key=state_returns.get)
    labels = {ranked[0]: "BEAR", ranked[1]: "SIDEWAYS", ranked[2]: "BULL"}
    order = ["BULL", "SIDEWAYS", "BEAR"]
    matrix = {}
    for old_state, old_label in labels.items():
        matrix[old_label] = {
            labels[new_state]: round(float(model.transmat_[old_state, new_state]), 4)
            for new_state in range(3)
        }
    last_state = int(hidden[-1])
    last_probs = posterior[-1]
    regime_probs = {labels[s]: round(float(last_probs[s]), 4) for s in range(3)}
    regime_probs = {k: regime_probs[k] for k in order}
    row = matrix[labels[last_state]]
    transition_obs = int(sum(hidden[i - 1] == last_state for i in range(1, len(hidden))))
    result = {
        "model": "Gaussian HMM (3 states)",
        "method": "IHSG daily return + 20-session annualized volatility + KOMPAS100 daily breadth",
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "asof": str(valid.index[-1]) if False else str(bench_df.loc[valid.index[-1], "date"]),
        "observations": int(len(valid)),
        "current_regime": labels[last_state],
        "current_probabilities": regime_probs,
        "stay_probability": round(float(model.transmat_[last_state, last_state]), 4),
        "transition_matrix": matrix,
        "state_mean_daily_return_pct": {labels[s]: round(state_returns[s] * 100, 4) for s in range(3)},
        "note": "Model is refit in GitHub Actions; state labels are assigned by fitted mean daily return. Probabilities are model estimates, not guaranteed forecasts."
    }
    OUT.write_text(json.dumps(result, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    print(f"HMM regime={result['current_regime']} asof={result['asof']} n={len(valid)} probs={regime_probs}")


if __name__ == "__main__":
    main()
