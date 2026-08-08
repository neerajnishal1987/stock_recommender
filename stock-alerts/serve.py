#!/usr/bin/env python3
"""
StockAlerts — local dev server.
Serves the web dashboard and proxies Supabase reads through local /api endpoints
so the dashboard works locally without CORS or exposing keys to the browser.

Run:  python3 serve.py
Open: http://localhost:5050
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from flask import Flask, jsonify, send_from_directory  # noqa: E402
from db import DB, SupabaseError  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

app = Flask(__name__, static_folder="web", static_url_path="/")
WEB_DIR = Path(__file__).resolve().parent / "web"


@app.route("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(WEB_DIR, path)


@app.route("/api/health")
def health():
    try:
        inst = DB.get_instruments()
        return jsonify({"ok": True, "instruments": len(inst), "supabase_configured": True})
    except SupabaseError as e:
        return jsonify({"ok": False, "error": str(e), "supabase_configured": False}), 502


@app.route("/api/instruments")
def api_instruments():
    try:
        items = DB.get_instruments()
        return jsonify({"ok": True, "data": items})
    except SupabaseError as e:
        return jsonify({"ok": False, "error": str(e)}), 502


@app.route("/api/market_data")
def api_market_data():
    try:
        rows = DB.latest_market_data()
        return jsonify({"ok": True, "data": rows})
    except SupabaseError as e:
        return jsonify({"ok": False, "error": str(e)}), 502


@app.route("/api/alerts")
def api_alerts():
    try:
        rows = DB.get_recent_alerts(limit=20)
        return jsonify({"ok": True, "data": rows})
    except SupabaseError as e:
        return jsonify({"ok": False, "error": str(e)}), 502


if __name__ == "__main__":
    print("=" * 60)
    print("StockAlerts — local dev server")
    print("Open:  http://localhost:5050")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5050, debug=False)