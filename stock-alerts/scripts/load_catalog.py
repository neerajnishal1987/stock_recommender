#!/usr/bin/env python3
"""
StockAlerts — load/seed the instrument catalog into Supabase.
Run:  python3 scripts/load_catalog.py
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from catalog import build_rows  # noqa: E402
from db import DB, SupabaseError  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("load_catalog")


def main():
    rows = build_rows()
    log.info("Built %d instrument rows", len(rows))

    # Avoid duplicate (country, asset_type, symbol) collisions by keeping last
    seen = {}
    for r in rows:
        key = (r["country"], r["asset_type"], r["symbol"])
        seen[key] = r
    rows = list(seen.values())
    log.info("After dedup: %d rows", len(rows))

    try:
        result = DB.upsert_instruments(rows)
        log.info("Upserted %d instruments into Supabase", len(result) if result else 0)
        # Break down by asset type
        counts = {}
        for r in rows:
            counts[r["asset_type"]] = counts.get(r["asset_type"], 0) + 1
        for k, v in sorted(counts.items()):
            log.info("  %-12s %d", k, v)
    except SupabaseError as e:
        log.error("Failed to upsert: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()