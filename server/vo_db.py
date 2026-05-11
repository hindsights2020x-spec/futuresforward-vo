"""
vo_db.py
========
Thin Supabase REST wrapper. Used by the web app and the Telegram worker.
Service-role key is required (bypasses RLS).

Env vars:
    SUPABASE_URL          https://xxxxx.supabase.co
    SUPABASE_SERVICE_KEY  service_role JWT (NOT anon)
"""

import os
import json
import time
from typing import Any, Iterable

import requests


SUPABASE_URL  = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY  = os.getenv("SUPABASE_SERVICE_KEY", "")

_HEADERS = {
    "apikey":        SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type":  "application/json",
    "Prefer":        "return=representation",
}


def _check():
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")


def insert(table: str, row: dict) -> dict | None:
    _check()
    r = requests.post(f"{SUPABASE_URL}/rest/v1/{table}",
                      headers=_HEADERS, json=row, timeout=15)
    if r.status_code >= 300:
        print(f"[vo_db] insert {table} failed {r.status_code}: {r.text[:200]}")
        return None
    data = r.json()
    return data[0] if isinstance(data, list) and data else None


def select(table: str, params: dict | None = None) -> list:
    _check()
    r = requests.get(f"{SUPABASE_URL}/rest/v1/{table}",
                     headers=_HEADERS, params=params or {}, timeout=15)
    if r.status_code >= 300:
        print(f"[vo_db] select {table} failed {r.status_code}: {r.text[:200]}")
        return []
    return r.json()


def update(table: str, match: dict, patch: dict) -> list:
    _check()
    params = {k: f"eq.{v}" for k, v in match.items()}
    r = requests.patch(f"{SUPABASE_URL}/rest/v1/{table}",
                       headers=_HEADERS, params=params, json=patch, timeout=15)
    if r.status_code >= 300:
        print(f"[vo_db] update {table} failed {r.status_code}: {r.text[:200]}")
        return []
    return r.json()


# ── Convenience helpers ─────────────────────────────────────

def log_event(source: str, message: str, level: str = "info",
              account_id: str | None = None, payload: dict | None = None):
    return insert("events", {
        "source": source, "level": level, "account_id": account_id,
        "message": message, "payload": payload or {},
    })


def log_trade(account_id: str, strategy: str, instrument: str,
              direction: str, qty: int, **kw):
    row = {"account_id": account_id, "strategy": strategy,
           "instrument": instrument, "direction": direction, "qty": qty}
    row.update({k: v for k, v in kw.items() if v is not None})
    return insert("trades", row)


def snapshot_account(account_id: str, **fields):
    fields["account_id"] = account_id
    return insert("account_snapshots", fields)


def add_pending_signal(account_id: str, strategy: str, instrument: str,
                       direction: str, qty: int, **kw):
    row = {"account_id": account_id, "strategy": strategy,
           "instrument": instrument, "direction": direction, "qty": qty,
           "status": "pending"}
    row.update({k: v for k, v in kw.items() if v is not None})
    return insert("pending_signals", row)


def get_tree() -> list:
    return select("v_tree", {"select": "*"})


def health() -> dict:
    """Quick reachability check used by /api/health."""
    try:
        r = requests.get(f"{SUPABASE_URL}/rest/v1/events?select=id&limit=1",
                         headers=_HEADERS, timeout=5)
        return {"ok": r.ok, "status": r.status_code}
    except Exception as e:
        return {"ok": False, "error": str(e)}
