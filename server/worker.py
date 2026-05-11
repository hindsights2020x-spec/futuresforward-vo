"""
worker.py
=========
Virtual Office — Telegram bot worker.

Long-polls Telegram for /commands and pushes alerts when new
events / trades / pending_signals appear in Supabase.

Pending-signal approve/reject inline buttons are OFF by default.
Set VO_ENABLE_SIGNAL_BUTTONS=1 to enable them.

Env vars:
    TELEGRAM_BOT_TOKEN          BotFather token (NEVER in code/git)
    TELEGRAM_CHAT_ID            your chat id (string or int)
    SUPABASE_URL
    SUPABASE_SERVICE_KEY
    VO_WEB_URL                  e.g. https://vo-web.onrender.com (used in links)
    VO_ENABLE_SIGNAL_BUTTONS    "1" to show approve/reject buttons

Deploy: Render Background Worker, start command:
    python -m server.worker
"""

import os
import time
import json
import traceback
from typing import Any

import requests

from . import vo_db


TG_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN", "")
TG_CHAT   = os.getenv("TELEGRAM_CHAT_ID", "")
VO_WEB    = os.getenv("VO_WEB_URL", "").rstrip("/")
ENABLE_SIGNAL_BUTTONS = os.getenv("VO_ENABLE_SIGNAL_BUTTONS", "0") == "1"

TG_API = f"https://api.telegram.org/bot{TG_TOKEN}"

POLL_INTERVAL_SEC   = 3
TG_UPDATE_TIMEOUT_S = 25


# ── Telegram I/O ─────────────────────────────────────────────

def tg(method: str, **payload) -> dict:
    if not TG_TOKEN:
        return {"ok": False, "error": "TELEGRAM_BOT_TOKEN not set"}
    try:
        r = requests.post(f"{TG_API}/{method}", json=payload, timeout=30)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}


def send(text: str, reply_markup: dict | None = None):
    if not TG_CHAT:
        print("[worker] TELEGRAM_CHAT_ID not set — skipping send")
        return
    payload: dict[str, Any] = {
        "chat_id":   TG_CHAT,
        "text":      text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    tg("sendMessage", **payload)


def answer_callback(callback_id: str, text: str = ""):
    tg("answerCallbackQuery", callback_query_id=callback_id, text=text)


# ── Formatting ───────────────────────────────────────────────

def fmt_trade(t: dict) -> str:
    pnl = t.get("pnl")
    pnl_s = f"  P&L <b>${pnl:,.2f}</b>" if pnl is not None else ""
    return (f"💱 <b>TRADE</b>  {t['direction']} {t['qty']}× {t['instrument']}\n"
            f"acct <code>{t['account_id']}</code>  strat <i>{t['strategy']}</i>{pnl_s}")


def fmt_event(e: dict) -> str:
    icon = {"error":"🔴", "warn":"⚠️", "trade":"💱",
            "signal":"📡", "info":"ℹ️"}.get(e.get("level"), "•")
    acct = f"  <code>{e['account_id']}</code>" if e.get("account_id") else ""
    return f"{icon} <b>{e['source']}</b>{acct}\n{e['message']}"


def fmt_signal(s: dict) -> str:
    return (f"📡 <b>PENDING SIGNAL #{s['id']}</b>\n"
            f"{s['direction']} {s['qty']}× {s['instrument']} on <code>{s['account_id']}</code>\n"
            f"strat <i>{s['strategy']}</i>\n"
            f"entry {s.get('entry')}  stop {s.get('stop')}  tp {s.get('tp')}\n"
            f"{s.get('rationale','')}")


def signal_buttons(signal_id: int) -> dict | None:
    if not ENABLE_SIGNAL_BUTTONS:
        return None
    return {"inline_keyboard": [[
        {"text": "✅ Approve", "callback_data": f"sig:{signal_id}:approved"},
        {"text": "❌ Reject",  "callback_data": f"sig:{signal_id}:rejected"},
    ]]}


# ── Watermarks (last-seen ids per stream) ────────────────────

_watermarks: dict[str, int] = {}


def newest_id(table: str) -> int:
    rows = vo_db.select(table, {"select": "id", "order": "id.desc", "limit": "1"})
    return int(rows[0]["id"]) if rows else 0


def init_watermarks():
    for tbl in ("events", "trades", "pending_signals"):
        _watermarks[tbl] = newest_id(tbl)
    print(f"[worker] watermarks initialised: {_watermarks}")


def poll_new_rows(table: str) -> list:
    last = _watermarks.get(table, 0)
    rows = vo_db.select(table, {
        "select": "*",
        "order":  "id.asc",
        "id":     f"gt.{last}",
        "limit":  "50",
    })
    if rows:
        _watermarks[table] = max(int(r["id"]) for r in rows)
    return rows


# ── Push loop ────────────────────────────────────────────────

def push_alerts_once():
    # New events (skip 'info' to avoid noise; surface warn/error/signal)
    for e in poll_new_rows("events"):
        if e.get("level") in ("info",):
            continue
        send(fmt_event(e))

    # New trades
    for t in poll_new_rows("trades"):
        send(fmt_trade(t))

    # New pending signals
    for s in poll_new_rows("pending_signals"):
        send(fmt_signal(s), reply_markup=signal_buttons(s["id"]))


# ── Telegram command loop ────────────────────────────────────

_last_update_id = 0


def handle_command(text: str) -> str:
    text = (text or "").strip().lower()
    if text in ("/start", "/help"):
        return ("FuturesForged Virtual Office — commands:\n"
                "/status — recent activity\n"
                "/pending — open pending signals\n"
                "/trades — last 5 trades\n"
                "/tree — workflow tree link\n"
                "/health — health check")
    if text == "/status":
        ev = vo_db.select("events", {"order":"ts.desc","limit":"5"})
        if not ev: return "no events yet"
        return "Recent events:\n" + "\n\n".join(fmt_event(e) for e in ev)
    if text == "/pending":
        ps = vo_db.select("pending_signals",
                          {"order":"ts.desc","limit":"5","status":"eq.pending"})
        if not ps: return "no pending signals"
        return "\n\n".join(fmt_signal(s) for s in ps)
    if text == "/trades":
        tr = vo_db.select("trades", {"order":"ts.desc","limit":"5"})
        if not tr: return "no trades yet"
        return "\n\n".join(fmt_trade(t) for t in tr)
    if text == "/tree":
        return f"Workflow tree: {VO_WEB}/tree" if VO_WEB else "VO_WEB_URL not set"
    if text == "/health":
        h = vo_db.health()
        return f"db: {h}  signal_buttons: {ENABLE_SIGNAL_BUTTONS}"
    return f"unknown command: {text}\nsend /help"


def handle_callback(data: str, callback_id: str):
    # data format "sig:<id>:approved|rejected"
    try:
        kind, pid, status = data.split(":")
    except ValueError:
        answer_callback(callback_id, "bad payload")
        return
    if kind != "sig" or status not in ("approved", "rejected"):
        answer_callback(callback_id, "unsupported")
        return
    if not ENABLE_SIGNAL_BUTTONS:
        answer_callback(callback_id, "buttons disabled")
        return
    vo_db.update("pending_signals", {"id": int(pid)},
                 {"status": status, "decided_by": "telegram",
                  "decided_at": "now()"})
    vo_db.log_event("worker", f"pending_signal {pid} → {status}",
                    level="signal", payload={"id": int(pid), "by": "telegram"})
    answer_callback(callback_id, f"signal {pid} {status}")
    send(f"📡 signal #{pid} marked <b>{status}</b>")


def poll_telegram_once():
    global _last_update_id
    if not TG_TOKEN:
        return
    params = {"timeout": TG_UPDATE_TIMEOUT_S, "offset": _last_update_id + 1}
    try:
        r = requests.get(f"{TG_API}/getUpdates", params=params, timeout=TG_UPDATE_TIMEOUT_S + 5)
        data = r.json()
    except Exception as e:
        print(f"[worker] getUpdates failed: {e}")
        time.sleep(5)
        return
    if not data.get("ok"):
        return
    for upd in data.get("result", []):
        _last_update_id = upd["update_id"]
        if "message" in upd and "text" in upd["message"]:
            text = upd["message"]["text"]
            reply = handle_command(text)
            send(reply)
        elif "callback_query" in upd:
            cb = upd["callback_query"]
            handle_callback(cb.get("data",""), cb["id"])


# ── Main loop ────────────────────────────────────────────────

def main():
    print("[worker] starting Virtual Office worker")
    print(f"[worker] signal buttons enabled: {ENABLE_SIGNAL_BUTTONS}")
    init_watermarks()
    vo_db.log_event("worker", "worker started", level="info",
                    payload={"signal_buttons": ENABLE_SIGNAL_BUTTONS})

    while True:
        try:
            push_alerts_once()
            poll_telegram_once()
        except KeyboardInterrupt:
            print("[worker] interrupted")
            break
        except Exception:
            traceback.print_exc()
        time.sleep(POLL_INTERVAL_SEC)


if __name__ == "__main__":
    main()
