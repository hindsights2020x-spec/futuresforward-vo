"""
seed_tree.py
============
Optional: seeds the workflow tree by hitting the Supabase REST API directly
from Python. Use this only if the SQL seed file is inconvenient.

The SQL seed at supabase/seed_workflow_tree.sql is the source of truth.
This file runs the equivalent inserts via REST so you can re-seed from your
desktop or from CI without opening the Supabase SQL editor.

Usage:
    set SUPABASE_URL=https://...
    set SUPABASE_SERVICE_KEY=...
    py scripts\\seed_tree.py
"""

import os
import sys
import requests

URL = (os.getenv("SUPABASE_URL") or "").rstrip("/")
KEY = os.getenv("SUPABASE_SERVICE_KEY") or ""
if not URL or not KEY:
    print("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.")
    sys.exit(1)

HEADERS = {
    "apikey":        KEY,
    "Authorization": f"Bearer {KEY}",
    "Content-Type":  "application/json",
    "Prefer":        "resolution=merge-duplicates,return=minimal",
}


def upsert(table: str, rows: list, on_conflict: str):
    r = requests.post(f"{URL}/rest/v1/{table}?on_conflict={on_conflict}",
                      headers=HEADERS, json=rows, timeout=20)
    if not r.ok:
        print(f"[!] {table} -> {r.status_code} {r.text[:200]}")
    else:
        print(f"[+] {table}: {len(rows)} row(s) upserted")


NODES = [
    # root + branches
    ("root", "FuturesForged", "doc",
     "Proprietary algorithmic futures trading platform — NQ + ES"),
    ("branch.strategies", "Strategies",     "doc", "Active and queued trading strategies"),
    ("branch.infra",      "Infrastructure", "doc", "Deployment, brokers, connectors"),
    ("branch.accounts",   "Accounts",       "doc", "Live broker + prop firm accounts"),
    ("branch.cowork",     "Cowork Queue",   "doc", "Handoff items and build sessions"),
    ("branch.docs",       "Methodology",    "doc", "Strategy development methodology — phases 1-9"),
    # strategies
    ("strat.sweep_reverse", "Sweep & Reverse",        "strategy", "NY session 13-17 UTC, NQ"),
    ("strat.box_london",    "Box MR — London",        "strategy", "London 08:00-10:00 UTC, NQ"),
    ("strat.box_power",     "Box MR — Power Hour",    "strategy", "Power Hour 20:00-21:00 UTC, NQ"),
    ("strat.momentum_nq",   "Momentum Breakout — NQ", "strategy", "Trend follow on NQ"),
    ("strat.momentum_es",   "Momentum Breakout — ES", "strategy", "Trend follow on ES"),
    ("strat.orb_scalp",     "ORB Scalp (shelved)",    "strategy", "WR 42.7% / PF 1.12 — needs regime filter"),
    # phases
    ("phase.1", "Phase 1 — Idea",                    "phase", "Capture concept + premise"),
    ("phase.2", "Phase 2 — Hypothesis",              "phase", "Falsifiable thesis"),
    ("phase.3", "Phase 3 — Data acquisition",        "phase", "Databento NQ 1m, etc."),
    ("phase.4", "Phase 4 — In-sample backtest",      "phase", "PF, WR, MAR"),
    ("phase.5", "Phase 5 — Costs + slippage",        "phase", "Realistic execution model"),
    ("phase.6", "Phase 6 — Parameter robustness",    "phase", "Plateau, not peaks"),
    ("phase.7", "Phase 7 — Walk-forward validation", "phase", "OOS PF > 1.3, eff > 0.6"),
    ("phase.8", "Phase 8 — Prop firm compatibility", "phase", "Trailing DD survival"),
    ("phase.9", "Phase 9 — Regime-gated deployment", "phase", "Hard DO-NOT-TRADE gates"),
    # infra
    ("infra.render_bot",    "Render — bot worker",   "infra", "futuresforged-bot.onrender.com"),
    ("infra.render_vo_web", "Render — VO web",       "infra", "Virtual Office Flask dashboard"),
    ("infra.render_vo_wkr", "Render — VO worker",    "infra", "Telegram polling worker"),
    ("infra.supabase",      "Supabase",              "infra", "Tables + workflow tree"),
    ("infra.telegram",      "Telegram bot",          "infra", "Buttons OFF by default"),
    ("infra.nt_ati",        "NinjaTrader ATI",       "infra", "Port 36973 — all prop firms"),
    ("infra.tradovate_api", "Tradovate API",         "infra", "Personal AMP only"),
    ("infra.rithmic",       "Rithmic",               "infra", "Conformance PASSED 2026-05-05"),
    ("infra.github",        "GitHub repo",           "infra", "hindsights2020x-spec/futuresforged-bot"),
    # accounts
    ("acct.amp_229107", "AMP #229107",         "account", "LIVE personal — Rithmic broker"),
    ("acct.mffu",       "MyFundedFutures",     "account", "Eval in progress — routes via NT8 ATI"),
    ("acct.apex",       "Apex Trader Funding", "account", "Pending provisioning"),
    # cowork
    ("cw.6",  "Cowork #6 — built",                  "cowork", "Completed"),
    ("cw.7",  "Cowork #7 — ready",                  "cowork", "Queued"),
    ("cw.8a", "Cowork #8a — ready",                 "cowork", "Queued"),
    ("cw.9",  "Cowork #9 — ready",                  "cowork", "Queued"),
    ("cw.11", "Cowork #11 — NT8 Production Bridge", "cowork", "In execution"),
    ("cw.vo", "Cowork — Virtual Office",            "cowork", "This build"),
]

EDGES = [
    ("root","branch.strategies"), ("root","branch.infra"),
    ("root","branch.accounts"),   ("root","branch.cowork"),
    ("root","branch.docs"),
    *[("branch.strategies", n) for n in
      ("strat.sweep_reverse","strat.box_london","strat.box_power",
       "strat.momentum_nq","strat.momentum_es","strat.orb_scalp")],
    ("branch.docs","phase.1"),
    *[(f"phase.{i}", f"phase.{i+1}") for i in range(1,9)],
    *[("branch.infra", n) for n in
      ("infra.render_bot","infra.render_vo_web","infra.render_vo_wkr",
       "infra.supabase","infra.telegram","infra.nt_ati",
       "infra.tradovate_api","infra.rithmic","infra.github")],
    *[("branch.accounts", n) for n in
      ("acct.amp_229107","acct.mffu","acct.apex")],
    *[("branch.cowork", n) for n in
      ("cw.6","cw.7","cw.8a","cw.9","cw.11","cw.vo")],
]

STATUS = [
    ("strat.sweep_reverse","live", 100), ("strat.box_london","live", 100),
    ("strat.box_power","live", 100),     ("strat.momentum_nq","live", 100),
    ("strat.momentum_es","live", 100),   ("strat.orb_scalp","shelved", 30),
    ("infra.render_bot","live",100),     ("infra.render_vo_web","active",10),
    ("infra.render_vo_wkr","active",10), ("infra.supabase","active",20),
    ("infra.telegram","active",30),      ("infra.nt_ati","live",100),
    ("infra.tradovate_api","live",100),  ("infra.rithmic","passed",100),
    ("infra.github","live",100),
    ("acct.amp_229107","live",100),      ("acct.mffu","active",60),
    ("acct.apex","blocked",0),
    ("cw.6","done",100), ("cw.7","idea",0), ("cw.8a","idea",0),
    ("cw.9","idea",0), ("cw.11","active",50), ("cw.vo","active",80),
]

PARAMS = [
    ("strat.sweep_reverse","session_utc", {"start":13,"end":17}),
    ("strat.box_london",   "session_utc", {"start":8,"end":10}),
    ("strat.box_power",    "session_utc", {"start":20,"end":21}),
    ("strat.orb_scalp",    "backtest",
        {"wr":0.427,"pf":1.12,"shelved_to":"Q3","reason":"insufficient — needs regime filter"}),
]


def main():
    print(f"Seeding Virtual Office workflow tree at {URL}")
    upsert("nodes",
           [{"id":i,"title":t,"kind":k,"summary":s} for (i,t,k,s) in NODES],
           on_conflict="id")
    upsert("edges",
           [{"from_node":a,"to_node":b,"relation":"parent_of"} for (a,b) in EDGES],
           on_conflict="from_node,to_node,relation")
    upsert("node_status",
           [{"node_id":n,"status":st,"progress":p} for (n,st,p) in STATUS],
           on_conflict="node_id")
    upsert("node_params",
           [{"node_id":n,"key":k,"value":v} for (n,k,v) in PARAMS],
           on_conflict="node_id,key")
    print("done.")


if __name__ == "__main__":
    main()
