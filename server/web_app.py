"""
web_app.py
==========
Virtual Office — Flask web app.

Endpoints:
    GET  /                  → dashboard landing
    GET  /tree              → custom workflow tree visualizer
    GET  /api/health
    GET  /api/tree          → full workflow tree (nodes + edges + status + params)
    GET  /api/node/<id>
    GET  /api/events?limit=50&level=trade
    GET  /api/trades?limit=50
    GET  /api/snapshots?account_id=...&limit=20
    GET  /api/pending?status=pending
    POST /api/pending/<id>/decision   { "status": "approved"|"rejected", "by": "web" }

Deploy: Render Web Service, start command:
    gunicorn -w 2 -b 0.0.0.0:$PORT server.web_app:app
"""

import os
from flask import Flask, jsonify, render_template, request, abort

from . import vo_db


app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
)

# Buttons in the dashboard pending-signals panel are OFF by default.
# Set VO_ENABLE_SIGNAL_BUTTONS=1 in Render env to turn them on.
ENABLE_SIGNAL_BUTTONS = os.getenv("VO_ENABLE_SIGNAL_BUTTONS", "0") == "1"


# ── Pages ────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html",
                           enable_signal_buttons=ENABLE_SIGNAL_BUTTONS)


@app.route("/tree")
def tree_page():
    return render_template("workflow_tree.html")


# ── API ──────────────────────────────────────────────────────

@app.get("/api/health")
def api_health():
    return jsonify({
        "ok":    True,
        "db":    vo_db.health(),
        "flags": {"signal_buttons": ENABLE_SIGNAL_BUTTONS},
    })


@app.get("/api/tree")
def api_tree():
    nodes = vo_db.get_tree()
    # Flatten children/parents from view for easy client consumption.
    return jsonify({"nodes": nodes})


@app.get("/api/node/<nid>")
def api_node(nid):
    rows = vo_db.select("v_tree", {"id": f"eq.{nid}"})
    if not rows:
        abort(404)
    return jsonify(rows[0])


@app.get("/api/events")
def api_events():
    limit = min(int(request.args.get("limit", 50)), 500)
    level = request.args.get("level")
    params = {"order": "ts.desc", "limit": str(limit)}
    if level:
        params["level"] = f"eq.{level}"
    return jsonify(vo_db.select("events", params))


@app.get("/api/trades")
def api_trades():
    limit = min(int(request.args.get("limit", 50)), 500)
    return jsonify(vo_db.select("trades",
                                {"order": "ts.desc", "limit": str(limit)}))


@app.get("/api/snapshots")
def api_snapshots():
    limit = min(int(request.args.get("limit", 20)), 200)
    params = {"order": "ts.desc", "limit": str(limit)}
    acct = request.args.get("account_id")
    if acct:
        params["account_id"] = f"eq.{acct}"
    return jsonify(vo_db.select("account_snapshots", params))


@app.get("/api/pending")
def api_pending():
    status = request.args.get("status", "pending")
    limit = min(int(request.args.get("limit", 50)), 200)
    return jsonify(vo_db.select("pending_signals", {
        "order": "ts.desc",
        "limit": str(limit),
        "status": f"eq.{status}",
    }))


@app.post("/api/pending/<int:pid>/decision")
def api_pending_decide(pid):
    if not ENABLE_SIGNAL_BUTTONS:
        return jsonify({"error": "signal buttons disabled"}), 403
    data = request.get_json(force=True, silent=True) or {}
    status = data.get("status")
    by     = data.get("by", "web")
    if status not in ("approved", "rejected"):
        return jsonify({"error": "status must be approved|rejected"}), 400
    updated = vo_db.update("pending_signals", {"id": pid},
                           {"status": status, "decided_by": by,
                            "decided_at": "now()"})
    vo_db.log_event("web", f"pending_signal {pid} → {status}",
                    level="signal", payload={"id": pid, "by": by})
    return jsonify(updated[0] if updated else {})


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
