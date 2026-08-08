"""
StockAlerts — Supabase database layer.
Uses the Supabase REST API (PostgREST) so no extra Postgres client is needed.
"""
from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
import uuid as uuid_lib

from config import settings

logger = logging.getLogger("db")


class SupabaseError(RuntimeError):
    pass


class DB:
    _url = settings.SUPABASE_URL
    _headers = {
        "apikey": settings.SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    @classmethod
    def _request(cls, method: str, path: str, params: dict | None = None, body=None, headers: dict | None = None):
        if not cls._url or not settings.SUPABASE_SERVICE_KEY:
            raise SupabaseError("SUPABASE_URL / SUPABASE_SERVICE_KEY not configured.")

        query = ""
        if params:
            query = "?" + urllib.parse.urlencode(params)
        url = f"{cls._url}/rest/v1/{path}{query}"

        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")

        hdrs = {**cls._headers}
        if headers:
            hdrs.update(headers)

        req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace")
            raise SupabaseError(f"Supabase {method} {path} -> {e.code}: {raw[:500]}") from e

    # ------------------------------------------------------------
    # Instruments
    # ------------------------------------------------------------
    @classmethod
    def upsert_instruments(cls, rows: list[dict]):
        """Upsert instruments by (country, asset_type, symbol)."""
        if not rows:
            return []
        hdrs = {
            "Prefer": "resolution=merge-duplicates,return=representation",
            "on_conflict": "country,asset_type,symbol",
        }
        return cls._request("POST", "instruments", body=rows, headers=hdrs)

    @classmethod
    def get_instruments(cls, country: str | None = None, asset_type: str | None = None, category: str | None = None):
        params = {"select": "*", "is_active": "eq.true", "order": "name.asc"}
        if country:
            params["country"] = f"eq.{country}"
        if asset_type:
            params["asset_type"] = f"eq.{asset_type}"
        if category:
            params["category"] = f"eq.{category}"
        return cls._request("GET", "instruments", params=params)

    # ------------------------------------------------------------
    # Market data
    # ------------------------------------------------------------
    @classmethod
    def insert_market_data(cls, rows: list[dict]):
        if not rows:
            return []
        return cls._request("POST", "market_data", body=rows)

    @classmethod
    def latest_market_data(cls, instrument_ids: list[str] | None = None):
        """
        Return the most recent market_data row per instrument.
        Since the table stores a snapshot every refresh, we fetch recent rows
        and keep the newest per instrument in the app layer.
        """
        params = {
            "select": "*",
            "order": "as_of.desc",
        }
        if instrument_ids:
            params["instrument_id"] = f"in.({','.join(instrument_ids)})"
        return cls._request("GET", "market_data", params=params)

    # ------------------------------------------------------------
    # Alerts
    # ------------------------------------------------------------
    @classmethod
    def insert_alert(cls, alert: dict) -> dict | None:
        res = cls._request("POST", "alerts", body=[alert])
        return res[0] if res else None

    @classmethod
    def update_alert(cls, alert_id: str, fields: dict):
        return cls._request("PATCH", f"alerts?id=eq.{alert_id}", body=fields)

    @classmethod
    def get_alert(cls, alert_id: str):
        rows = cls._request("GET", "alerts", params={"select": "*", "id": f"eq.{alert_id}"})
        return rows[0] if rows else None

    @classmethod
    def get_recent_alerts(cls, limit: int = 50):
        return cls._request(
            "GET", "alerts",
            params={"select": "*", "order": "detected_at.desc", "limit": str(limit)},
        )

    # ------------------------------------------------------------
    # News
    # ------------------------------------------------------------
    @classmethod
    def insert_news(cls, rows: list[dict]):
        if not rows:
            return []
        return cls._request("POST", "news_articles", body=rows)

    @classmethod
    def get_news_for_alert(cls, alert_id: str):
        return cls._request("GET", "news_articles", params={"select": "*", "alert_id": f"eq.{alert_id}"})


def new_uuid() -> str:
    return str(uuid_lib.uuid4())