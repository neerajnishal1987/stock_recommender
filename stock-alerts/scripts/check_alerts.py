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


def fetch_yfinance_context(symbol: str) -> dict:
    """Fetch rich context for the LLM: 52w range, fundamentals, shareholding,
    3y/5y returns, and top institutional holders. Defensive — never raises."""
    ctx = {}
    if yf is None:
        return ctx
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
        ctx["sector"] = info.get("sector")
        ctx["industry"] = info.get("industry")
        ctx["market_cap"] = info.get("marketCap")
        ctx["forward_pe"] = info.get("forwardPE")
        ctx["trailing_pe"] = info.get("trailingPE")
        ctx["pb_ratio"] = info.get("priceToBook")
        ctx["dividend_yield"] = info.get("dividendYield")
        ctx["52w_high"] = info.get("fiftyTwoWeekHigh")
        ctx["52w_low"] = info.get("fiftyTwoWeekLow")
        ctx["52w_change_pct"] = info.get("52WeekChange")
        # Promoter / institutional holding (where available)
        try:
            ph = ticker.get_promoter_holding()
            if ph is not None and not ph.empty:
                last = ph.iloc[-1]
                ctx["promoter_holding_pct"] = last.get("promoterHoldingPct")
        except Exception:
            pass
        # Top institutional holders
        try:
            holders = ticker.get_institutional_holders()
            if holders is not None and not holders.empty:
                ctx["top_institutional_holders"] = ", ".join(
                    str(h) for h in holders.head(5)["Holder"].tolist()
                )
        except Exception:
            pass
        # Explicitly note FII/DII/retail are not available from this data source
        ctx["fii_dii_retail_note"] = (
            "FII/DII and retail holding % are not available via the market-data source; "
            "only promoter holding and top institutional holders are fetched where the source provides them."
        )
        # 3y / 5y returns from price history
        try:
            hist = ticker.history(period="5y")
            if not hist.empty:
                first = hist["Close"].iloc[0]
                last = hist["Close"].iloc[-1]
                ctx["5y_return_pct"] = round((last - first) / first * 100, 2)
                h3 = ticker.history(period="3y")
                if not h3.empty:
                    f3 = h3["Close"].iloc[0]
                    ctx["3y_return_pct"] = round((last - f3) / f3 * 100, 2)
        except Exception:
            pass
    except Exception as e:
        log.warning("Could not fetch yfinance context for %s: %s", symbol, e)
    return {k: v for k, v in ctx.items() if v is not None}


def fetch_sector_peers(instruments, inst, top_n: int = 5) -> list[dict]:
    """Return peer instruments in the same sector/category (excluding the alerted one)."""
    peers = []
    for i in instruments:
        if i["id"] == inst["id"]:
            continue
        if i.get("asset_type") != inst.get("asset_type"):
            continue
        # match by sector-ish: same category for stock (largecap/midcap/smallcap) or same asset
        if inst.get("asset_type") == "stock" and i.get("category") != inst.get("category"):
            continue
        if inst.get("country") and i.get("country") != inst.get("country"):
            continue
        peers.append(i)
        if len(peers) >= top_n:
            break
    return peers


def build_context(symbol: str, instruments, inst, latest) -> dict:
    """Assemble the full context blob passed to the LLM."""
    ctx = fetch_yfinance_context(symbol)
    # peer day-moves from latest market data
    peers = fetch_sector_peers(instruments, inst)
    peer_moves = []
    for p in peers:
        row = latest.get(p["id"])
        if row:
            price = row.get("price"); high = row.get("day_high")
            off = None
            if price and high and float(high) > 0:
                off = round((float(high) - float(price)) / float(high) * 100, 2)
            peer_moves.append({
                "symbol": p["symbol"], "name": p["name"],
                "off_high_pct": off, "change_pct": row.get("change_pct"),
            })
    ctx["sector_peers"] = peer_moves
    return ctx


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

        # 4. Build rich context (sector peers, 3y/5y returns, shareholding,
        #    fundamentals) and analyze with LLM
        key_details = build_context(symbol, instruments, inst, latest)
        analysis = analyze_news(name, symbol, asset_type, country, off_high, price,
                                 day_high, news_items, key_details,
                                 concise=settings.CONCISE_MODE)
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