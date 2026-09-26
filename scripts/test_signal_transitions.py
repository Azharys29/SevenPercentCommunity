#!/usr/bin/env python3
"""Deterministic transition tests for the signal engine."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_signals import transition

def c(signal,score,agree=4): return {"signal":signal,"score":score,"score_delta":0,"agree":agree}
def run():
    cases=[
      ("no previous",None,c("Bullish",60,4),False,False),
      ("neutral to bullish, AI threshold 35",c("Neutral",10),c("Bullish",40,3),True,True),
      ("neutral to bullish, AI",c("Neutral",10),c("Bullish",60,3),True,True),
      ("bullish score +15",c("Bullish",60),dict(c("Bullish",75),score_delta=15),True,True),
      ("bullish score +10",c("Bullish",60),dict(c("Bullish",70),score_delta=10),False,False),
      ("bullish to neutral",c("Bullish",60),c("Neutral",5),False,False),
      ("bearish to bullish",c("Bearish",-20),c("Bullish",60,3),True,True),
      ("HRTA simulation: Bullish 30 to 51.02",c("Bullish",30,4),dict(c("Bullish",51.02,4),score_delta=21.02),True,True),
    ]
    for name,p,cur,nb,ai in cases:
        got=transition(p,cur)
        assert got==(nb,ai),f"{name}: expected {(nb,ai)}, got {got}"
    print(f"PASS: {len(cases)} transition cases (including HRTA simulation)")
if __name__=="__main__": run()
