"""
vo_client.py
============
FuturesForged → Virtual Office reporter.

DROP-IN MODULE for C:\\Users\\TOM\\Desktop\\TradingBot\\

Imported by bot_engine.py. Posts events, trades, account snapshots,
and pending signals to the Virtual Office Supabase via REST.

Design rules:
    * Fully non-blocking — every call returns immediately.
    * Failures are swallowed: VO outages MUST NOT crash the bot.
    * No new deps beyond `requests` (already in TradingBot venv).
    * Reads SUPABASE_URL / SUPABASE_SERVICE_KEY from the bot's .env.

Hook points in bot_engine.py — see the patch at the bottom of this file.

Env vars:
    SUPABASE_URL          https://xxxxx.supabase.co
    SUPABASE_SERVICE_KEY  service_role key (NOT the anon key)
    VO_ENABLED            "1" to enable (default), "0" to disable
"""

import os
import queue
import threading
import time
from typing import Any

import requests


SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or ""
VO_ENABLED   = os.getenv("VO_ENABLED", "1") == "1" and bool(SUPABASE_URL and SUPABASE_KEY)

_HEADERS = {
    "apikey":        SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type":  "application/json",
    "Prefer":        "return=minimal",
}


# ── Background queue ─────────────────────────────────────────
# Bot is latency-sensitive; we never wait for HTTP. A single worker
# thread drains a queue and POSTs to Supabase. Queue is bounded so
# a long outage can't balloon memory.

_q: "queue.Queue[tuple[str, dict]]" = queue.Queue(maxsize=2000)
_worker_started = False
_worker_lock = threading.Lock()


def _worker():
    while True:
        try:
            table, row = _q.get(timeout=5)
        except queue.Empty:
            continue
        if not VO_ENABLED:
            continue
        try:
            requests.post(
                f"{SUPABASE_URL}/rest/v1/{table}",
                headers=_HEADERS, json=row, timeout=8,
            )
        except Exception:
            pass  # never raise from the worker


def _ensure_worker():
    global _worker_started
    if _worker_started:
        return
    with _worker_lock:
        if _worker_started:
            return
        threading.Thread(target=_worker, daemon=True, name="VOClient").start()
        _worker_started = True


def _enqueue(table: str, row: dict):
    if not VO_ENABLED:
        return
    _ensure_worker()
    try:
        _q.put_nowait((table, row))
    except queue.Full:
        pass  # silently drop


# ── Public API ───────────────────────────────────────────────

def log_event(message: str, level: str = "info", source: str = "bot_engine",
              account_id: str | None = None, payload: dict | None = None):
    _enqueue("events", {
        "source": source, "level": level, "account_id": account_id,
        "message": message, "payload": payload or {},
    })


def log_trade(account_id: str, strategy: str, instrument: str,
              direction: str, qty: int,
              entry: float | None = None, stop: float | None = None,
              tp: float | None = None, exit_price: float | None = None,
              exit_reason: str | None = None, pnl: float | None = None,
              raw: dict | None = None):
    row = {
        "account_id": account_id, "strategy": strategy,
        "instrument": instrument, "direction": direction, "qty": qty,
    }
    if entry       is not None: row["entry"]       = entry
    if stop        is not None: row["stop"]        = stop
    if tp          is not None: row["tp"]          = tp
    if exit_price  is not None: row["exit_price"]  = exit_price
    if exit_reason is not None: row["exit_reason"] = exit_reason
    if pnl         is not None: row["pnl"]         = pnl
    if raw         is not None: row["raw"]         = raw
    _enqueue("trades", row)


def snapshot(account_id: str, balance: float | None = None,
             floor: float | None = None, floor_locked: bool | None = None,
             intraday_hwm: float | None = None, eod_hwm: float | None = None,
             passed: bool | None = None, cum_profit: float | None = None,
             open_position: dict | None = None,
             rules_snapshot: dict | None = None):
    row: dict[str, Any] = {"account_id": account_id}
    for k, v in (
        ("balance", balance), ("floor", floor), ("floor_locked", floor_locked),
        ("intraday_hwm", intraday_hwm), ("eod_hwm", eod_hwm),
        ("passed", passed), ("cum_profit", cum_profit),
        ("open_position", open_position), ("rules_snapshot", rules_snapshot),
    ):
        if v is not None:
            row[k] = v
    _enqueue("account_snapshots", row)


def pending_signal(account_id: str, strategy: str, instrument: str,
                   direction: str, qty: int,
                   entry: float | None = None, stop: float | None = None,
                   tp: float | None = None, rationale: str | None = None,
                   raw: dict | None = None):
    row: dict[str, Any] = {
        "account_id": account_id, "strategy": strategy,
        "instrument": instrument, "direction": direction, "qty": qty,
        "status": "pending",
    }
    if entry     is not None: row["entry"]     = entry
    if stop      is not None: row["stop"]      = stop
    if tp        is not None: row["tp"]        = tp
    if rationale is not None: row["rationale"] = rationale
    if raw       is not None: row["raw"]       = raw
    _enqueue("pending_signals", row)


# ── Status / debug ───────────────────────────────────────────

def status() -> dict:
    return {
        "enabled":     VO_ENABLED,
        "url_set":     bool(SUPABASE_URL),
        "key_set":     bool(SUPABASE_KEY),
        "queue_depth": _q.qsize(),
    }


# ============================================================
# HOOK GUIDE — add these calls inside bot_engine.py
# ============================================================
#
# 1)  At the top of bot_engine.py, after `load_dotenv(...)`:
#
#         import vo_client
#         vo_client.log_event("bot starting", level="info")
#
# 2)  Inside update_account_state(), after balance update:
#
#         vo_client.snapshot(
#             account_id=aid,
#             balance=s["balance"], floor=s["floor"],
#             floor_locked=s["floor_locked"],
#             intraday_hwm=s["intraday_hwm"], eod_hwm=s["eod_hwm"],
#             passed=s["passed"], cum_profit=s["cum_profit"],
#         )
#
# 3)  Wherever a fill/exit is recorded (executors layer):
#
#         vo_client.log_trade(
#             account_id=aid, strategy=strat, instrument=instr,
#             direction=direction, qty=qty,
#             entry=entry, stop=stop, tp=tp,
#             exit_price=exit_price, exit_reason=reason, pnl=pnl,
#         )
#
# 4)  Right BEFORE order submission (signal generated but not yet sent):
#
#         vo_client.pending_signal(
#             account_id=aid, strategy=strat, instrument=instr,
#             direction=direction, qty=qty,
#             entry=entry, stop=stop, tp=tp,
#             rationale="sweep above PDH, reversal close inside",
#         )
#
# 5)  In except blocks for trade execution errors:
#
#         vo_client.log_event(str(e), level="error",
#                             account_id=aid, payload={"trace": tb})
#
# ============================================================
