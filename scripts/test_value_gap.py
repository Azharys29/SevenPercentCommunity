#!/usr/bin/env python3
def value_gap(avg_pe,current_pe,eps_growth_pct): return (avg_pe-current_pe)*eps_growth_pct
assert value_gap(20,15,20)==100
assert value_gap(15,20,20)==-100
assert value_gap(20,15,-10)==-50
print("Value Gap tests: PASS")
