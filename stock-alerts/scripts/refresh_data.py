#!/usr/bin/env python3
"""
StockAlerts — daily market data refresh.
Fetches live quotes from Yahoo Finance (yfinance) for every active instrument
and inserts a market_data snapshot row per instrument into Supabase.

Run:  python3 scripts/refresh_data.py
"""
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from config import settings  # noqa: E402
from db import DB, SupabaseError  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("refresh")

try:
    import yfinance as yf
except ImportError:
    yf = None


def fetch_quote(symbol: str):
    """Return a dict with price, day_high, etc. from yfinance, or None."""
    if yf is None:
        log.error("yfinance not installed (pip install yfinance).")
        return None
    try:
        ticker = yf.Ticker(symbol)
        fast = ticker.fast_info
        price = getattr(fast, "last_price", None)
        day_high = getattr(fast, "day_high", None)
        day_low = getattr(fast, "day_low", None)
        prev_close = getattr(fast, "previous_close", None)
        open_price = getattr(fast, "open", None)
        volume = getattr(fast, "last_volume", None)
    except Exception as e:
        log.warning("Failed to fetch %s: %s", symbol, e)
        return None

    if price is None:
        log.warning("No price for %s", symbol)
        return None

    return {
        "price": price,
        "day_high": day_high,
        "day_low": day_low,
        "prev_close": prev_close,
        "day_open": open_price,
        "volume": volume,
    }


def to_num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def main():
    try:
        instruments = DB.get_instruments()
    except SupabaseError as e:
        log.error("Could not load instruments: %s", e)
        sys.exit(1)

    log.info("Found %d active instruments", len(instruments))

    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for inst in instruments:
        q = fetch_quote(inst["symbol"])
        if not q:
            continue
        price = to_num(q.get("price"))
        day_high = to_num(q.get("day_high"))
        day_low = to_num(q.get("day_low"))
        prev_close = to_num(q.get("prev_close"))
        day_open = to_num(q.get("day_open"))
        volume = to_num(q.get("volume"))

        change_pct = None
        if price is not None and prev_close:
            change_pct = round((price - prev_close) / prev_close * 100, 4)

        rows.append({
            "instrument_id": inst["id"],
            "as_of": now,
            "price": price,
            "day_high": day_high,
            "day_low": day_low,
            "prev_close": prev_close,
            "day_open": day_open,
            "change_pct": change_pct,
            "volume": volume,
            "source": "yfinance",
        })

    if not rows:
        log.warning("No market data rows were produced (check network / symbols).")
        sys.exit(1)

    try:
        DB.insert_market_data(rows)
    except SupabaseError as e:
        log.error("Failed to insert market data: %s", e)
        sys.exit(1)

    log.info("Inserted %d market data rows at %s", len(rows), now)


if __name__ == "__main__":
    main()
