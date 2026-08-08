"""
StockAlerts — news fetching.
Uses NewsAPI, MediaStack, or Google News RSS fallback.
"""
from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request

from config import settings

log = logging.getLogger("news")


def _fetch_url(url: str, timeout: int = 20) -> str | None:
    req = urllib.request.Request(url, headers={"User-Agent": settings.USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        log.warning("News fetch failed for %s: %s", url, e)
        return None


def fetch_news_via_newsapi(query: str, max_results: int = 10) -> list[dict]:
    params = {
        "q": query,
        "language": "en",
        "pageSize": str(max_results),
        "sortBy": "publishedAt",
    }
    if settings.NEWS_SOURCES:
        params["sources"] = settings.NEWS_SOURCES
    url = "https://newsapi.org/v2/everything?" + urllib.parse.urlencode(params) + f"&apiKey={settings.NEWSAPI_KEY}"
    raw = _fetch_url(url)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except Exception:
        return []
    articles = data.get("articles", []) if data.get("status") == "ok" else []
    results = []
    for a in articles:
        results.append({
            "title": a.get("title") or "",
            "url": a.get("url") or "",
            "source": (a.get("source") or {}).get("name") or "",
            "published_at": a.get("publishedAt"),
            "snippet": (a.get("description") or "")[:500],
        })
    return results


def fetch_news_via_mediastack(query: str, max_results: int = 10) -> list[dict]:
    params = {
        "access_key": settings.MEDIASTACK_KEY,
        "keywords": query,
        "languages": "en",
        "limit": str(max_results),
        "sort": "published_desc",
    }
    url = "http://api.mediastack.com/v1/news?" + urllib.parse.urlencode(params)
    raw = _fetch_url(url)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except Exception:
        return []
    results = []
    for a in data.get("data", []):
        snippet = (a.get("description") or a.get("snippet") or "")[:500]
        results.append({
            "title": a.get("title") or "",
            "url": a.get("url") or "",
            "source": a.get("source") or "",
            "published_at": a.get("published_at"),
            "snippet": snippet,
        })
    return results


def fetch_news_via_google_rss(query: str, max_results: int = 10) -> list[dict]:
    """Fallback: Google News RSS for a text query (no API key required)."""
    import html
    import re

    q = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
    raw = _fetch_url(url)
    if not raw:
        return []
    items = re.findall(r"<item>(.*?)</item>", raw, re.S)
    results = []
    for it in items[:max_results]:
        title_m = re.search(r"<title>(.*?)</title>", it, re.S)
        link_m = re.search(r"<link>(.*?)</link>", it, re.S)
        desc_m = re.search(r"<description>(.*?)</description>", it, re.S)
        title = html.unescape(title_m.group(1)) if title_m else ""
        link = html.unescape(link_m.group(1)) if link_m else ""
        snippet = html.unescape(re.sub(r"<.*?>", "", desc_m.group(1)))[:500] if desc_m else ""
        results.append({
            "title": title,
            "url": link,
            "source": "Google News",
            "published_at": None,
            "snippet": snippet,
        })
    return results


def fetch_news(query: str, max_results: int | None = None, instrument_name: str = "") -> list[dict]:
    """Fetch news for an alert, trying providers in order of availability."""
    max_results = max_results or settings.MAX_NEWS_PER_ALERT

    search_query = query
    if instrument_name and instrument_name.lower() not in search_query.lower():
        search_query = f"{instrument_name} {search_query}"

    if settings.NEWSAPI_KEY:
        articles = fetch_news_via_newsapi(search_query, max_results)
        if articles:
            return articles
    if settings.MEDIASTACK_KEY:
        articles = fetch_news_via_mediastack(search_query, max_results)
        if articles:
            return articles

    # Fallback to Google News RSS (works without any API key)
    try:
        articles = fetch_news_via_google_rss(search_query, max_results)
        if articles:
            return articles
    except Exception as e:
        log.warning("Google RSS fallback failed: %s", e)

    log.info("No news provider available. Set NEWSAPI_KEY or MEDIASTACK_KEY for richer results.")
    return []
