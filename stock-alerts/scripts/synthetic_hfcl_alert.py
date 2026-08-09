#!/usr/bin/env python3
"""
Synthetic HFCL (India) drop alert — end-to-end demo.

1. Ensures an `HFCL.NS` instrument exists (India, stock, smallcap).
2. Inserts a synthetic market_data row that is >=5% below the day's high
   (the trigger condition), so the alert pipeline fires.
3. Runs the real check_alerts pipeline: news fetch -> LLM analysis -> email draft.
4. Prints the generated email + analysis and writes them to a local file.
"""
import logging
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import settings
from db import DB, new_uuid

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("synthetic_hfcl")

HFCL = {
    "country": "IN",
    "asset_type": "stock",
    "category": "smallcap",
    "symbol": "HFCL.NS",
    "name": "HFCL Limited",
    "is_active": True,
}


def ensure_instrument():
    existing = DB.get_instruments(country="IN", asset_type="stock", category="smallcap")
    for i in existing:
        if i["symbol"] == HFCL["symbol"]:
            log.info("HFCL instrument already exists: %s", i["id"])
            return i["id"]
    created = DB.upsert_instruments([HFCL])
    iid = created[0]["id"]
    log.info("Created HFCL instrument: %s", iid)
    return iid


def insert_synthetic_market_data(instrument_id):
    # Synthetic snapshot: day high 98.50, current price 92.10 => ~6.50% drop
    day_high = 98.50
    price = 92.10
    off = round((day_high - price) / day_high * 100, 4)
    row = {
        "instrument_id": instrument_id,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "price": price,
        "day_high": day_high,
        "day_low": 91.40,
        "prev_close": 97.85,
        "day_open": 97.60,
        "change_pct": round((price - 97.85) / 97.85 * 100, 4),
        "volume": 4125000,
        "source": "synthetic-demo",
    }
    res = DB.insert_market_data([row])
    log.info("Inserted synthetic market data (off-high %.2f%%)", off)
    return off, price, day_high, res


def main():
    iid = ensure_instrument()
    off, price, day_high, _ = insert_synthetic_market_data(iid)

    # Run the actual alert pipeline for this instrument only.
    from news import fetch_news
    from analyzer import analyze_news, draft_email

    inst = DB.get_instruments(country="IN", asset_type="stock", category="smallcap")
    inst = next(i for i in inst if i["symbol"] == HFCL["symbol"])

    # 1. alert record
    alert = {
        "id": new_uuid(),
        "instrument_id": iid,
        "alert_type": "drop_from_high",
        "drop_pct": off,
        "price": price,
        "day_high": day_high,
        "moved_off_high": off,
        "status": "new",
    }
    created = DB.insert_alert(alert)
    alert_id = created["id"] if created else alert["id"]
    log.info("Alert record created: %s (drop %.2f%%)", alert_id, off)

    # 2. news
    news_items = fetch_news(HFCL["symbol"], instrument_name=HFCL["name"])
    log.info("Fetched %d news items", len(news_items))
    if news_items:
        news_rows = [{
            "alert_id": alert_id,
            "instrument_id": iid,
            "title": n.get("title"),
            "url": n.get("url"),
            "source": n.get("source"),
            "published_at": n.get("published_at"),
            "snippet": n.get("snippet"),
        } for n in news_items[:settings.MAX_NEWS_PER_ALERT]]
        DB.insert_news(news_rows)

    # 3. LLM analysis + email (use the SAME context builder as production)
    from check_alerts import build_context, latest_by_instrument
    mdata = DB.latest_market_data()
    latest = latest_by_instrument(mdata)
    key_details = build_context(inst["symbol"], [inst], inst, latest)
    analysis = analyze_news(inst["name"], inst["symbol"], inst["asset_type"], inst["country"],
                             off, price, day_high, news_items, key_details)
    subject = f"\u26a0\ufe0f Drop Alert: {inst['name']} ({inst['symbol']}) -{off:.2f}% [STOCK]"
    email_body = draft_email(inst["name"], inst["symbol"], inst["asset_type"], inst["country"], off, price, analysis)

    DB.update_alert(alert_id, {
        "status": "email_sent",
        "groq_analysis": analysis,
        "email_body": email_body,
    })
    log.info("Alert updated with analysis + email body.")

    out = f"SUBJECT: {subject}\n\n{email_body}\n\n===== LLM ANALYSIS =====\n{analysis}\n"
    Path("synthetic_hfcl_alert.txt").write_text(out)
    print("\n" + "=" * 70)
    print(out)
    print("=" * 70)
    print(f"\nSaved to synthetic_hfcl_alert.txt  | alert_id={alert_id}")


if __name__ == "__main__":
    main()
