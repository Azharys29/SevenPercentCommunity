#!/usr/bin/env python3
"""Small deterministic tests for Dividend Intelligence calculations."""
def annualize(ytd_revenue, months):
    return ytd_revenue * 12 / months if ytd_revenue is not None and months else None

def estimate(revenue, npm_pct, dpr_pct, shares, price):
    net_income = revenue * npm_pct / 100
    total_dividend = net_income * dpr_pct / 100
    dps = total_dividend / shares
    return net_income, total_dividend, dps, dps / price * 100

assert annualize(900, 9) == 1200
ni, total, dps, yield_pct = estimate(12000, 15, 40, 10, 1200)
assert (ni, total, dps, yield_pct) == (1800, 720, 72, 6)
assert estimate(1000, 10, 120, 10, 100)[2] == 12
print("Dividend Intelligence tests: PASS")
