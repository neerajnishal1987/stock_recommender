#!/usr/bin/env python3
"""
StockAlerts — realtime drop alert pipeline.
Scans the latest market data for any instrument that has dropped >= threshold
from its day's high, then for stocks/ETFs/commodities/crypto:
  1. Records an alert
  2. Fetches up to 10-20 relevant news articles
  3. Uses the configured LLM (Groq / Gemini / OpenRouter) to analyze & summarize the likely reasons
  4. Uses the LLM to draft an email and sends it (subject includes asset + % drop)

Run:  python3 scripts/check_alerts.py
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from config import settings  # noqa: E402
from db import DB, SupabaseError, new_uuid  # noqa: E402
from news import fetch_news  # noqa: E402
from analyzer import analyze_news, draft_email, send_email  # noqa: E402

try:
    import yfinance as yf
except ImportError:
    yf = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("check_alerts")


def fetch_key_details(symbol: str) -> dict:
    """Fetch key details: 52-week range, sector, key owners, and basic fundamentals."""
    details = {}
    if yf is None:
        return details
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
        details["52-Week High"] = info.get("fiftyTwoWeekHigh")
        details["52-Week Low"] = info.get("fiftyTwoWeekLow")
        details["Sector"] = info.get("sector")
        details["Industry"] = info.get("industry")
        details["Market Cap"] = info.get("marketCap")
        details["Forward P/E"] = info.get("forwardPE")
        details["52-Week Change %"] = info.get("52WeekChange")
        # Key institutional holders (top 3)
        try:
            holders = ticker.get_institutional_holders()
            if holders is not None and not holders.empty:
                top = holders.head(3)
                names = ", ".join(str(h) for h in top["Holder"].tolist())
                details["Key Owners"] = names
        except Exception:
            pass
    except Exception as e:
        log.warning("Could not fetch key details for %s: %s", symbol, e)
    return {k: v for k, v in details.items() if v is not None}


def compute_off_high(price, day_high):
    """Return % drop from day's high, or None if unavailable."""
    try:
        price = float(price)
        day_high = float(day_high)
        if day_high <= 0:
            return None
        return round((day_high - price) / day_high * 100, 4)
    except (TypeError, ValueError):
        return None


def latest_by_instrument(rows):
    """Given market_data rows, return the newest row per instrument_id."""
    newest = {}
    for r in rows:
        rid = r.get("instrument_id")
        if rid in newest:
            # as_of is ISO string; compare lexicographically works for ISO UTC
            if (r.get("as_of") or "") > (newest[rid].get("as_of") or ""):
                newest[rid] = r
        else:
            newest[rid] = r
    return newest


def main():
    threshold = settings.DROP_THRESHOLD_PCT

    try:
        instruments = DB.get_instruments()
    except SupabaseError as e:
        log.error("Could not load instruments: %s", e)
        sys.exit(1)

    # Build lookup id -> instrument
    inst_by_id = {i["id"]: i for i in instruments}

    try:
        mdata = DB.latest_market_data()
    except SupabaseError as e:
        log.error("Could not load market data: %s", e)
        sys.exit(1)

    latest = latest_by_instrument(mdata)
    log.info("Loaded %d instruments with latest market data", len(latest))

    alerts_triggered = 0
    for inst_id, row in latest.items():
        inst = inst_by_id.get(inst_id)
        if not inst:
            continue

        price = row.get("price")
        day_high = row.get("day_high")
        off_high = compute_off_high(price, day_high)
        if off_high is None or off_high < threshold:
            continue

        symbol = inst["symbol"]
        name = inst["name"]
        asset_type = inst["asset_type"]
        country = inst["country"]

        log.info(
            "ALERT TRIGGERED: %s (%s) off-high %.2f%% price=%s day_high=%s",
            name, symbol, off_high, price, day_high,
        )

        # 1. Create alert record
        alert = {
            "id": new_uuid(),
            "instrument_id": inst_id,
            "alert_type": "drop_from_high",
            "drop_pct": off_high,
            "price": price,
            "day_high": day_high,
            "moved_off_high": off_high,
            "status": "new",
        }
        try:
            created = DB.insert_alert(alert)
        except SupabaseError as e:
            log.error("Failed to insert alert for %s: %s", symbol, e)
            continue
        alert_id = created["id"] if created else alert["id"]

        # 2. Fetch news (query by symbol + name)
        news_items = fetch_news(symbol, instrument_name=name)
        log.info("Fetched %d news items for %s", len(news_items), symbol)

        # 3. Persist news
        if news_items:
            news_rows = []
            for n in news_items[:settings.MAX_NEWS_PER_ALERT]:
                news_rows.append({
                    "alert_id": alert_id,
                    "instrument_id": inst_id,
                    "title": n.get("title"),
                    "url": n.get("url"),
                    "source": n.get("source"),
                    "published_at": n.get("published_at"),
                    "snippet": n.get("snippet"),
                })
            try:
                DB.insert_news(news_rows)
            except SupabaseError as e:
                log.error("Failed to insert news for %s: %s", symbol, e)

        # 4. Fetch key details (52-week, owners, sector) and analyze with LLM
        key_details = fetch_key_details(symbol)
        analysis = analyze_news(name, symbol, off_high, price, news_items, key_details)
        log.info("LLM analysis (%s) for %s: %.120s…", settings.LLM_PROVIDER, symbol, analysis.replace("\n", " "))

        # 5. Draft email + send
        subject = (
            f"⚠️ Drop Alert: {name} ({symbol}) -{off_high:.2f}% "
            f"[{asset_type.upper()}]"
        )
        email_body = draft_email(name, symbol, asset_type, country, off_high, price, analysis)

        sent = send_email(subject, email_body)
        status = "email_sent" if sent else "analyzed"
        try:
            DB.update_alert(alert_id, {
                "status": status,
                "groq_analysis": analysis,
                "email_body": email_body,
            })
        except SupabaseError as e:
            log.error("Failed to update alert %s: %s", alert_id, e)

        alerts_triggered += 1

    log.info("Done. Triggered %d alerts.", alerts_triggered)


if __name__ == "__main__":
    main()