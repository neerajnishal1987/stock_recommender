"""
StockAlerts — multi-provider LLM analysis & email drafting.
Supports: Groq, Google Gemini (free), OpenRouter (free models).
Produces a structured summary: price movement, fundamentals, news reasons, recommendation,
plus key details (52-week range, key owners, sector momentum).
"""
from __future__ import annotations

import json
import logging
import smtplib
import urllib.request
import urllib.error
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import settings

log = logging.getLogger("analyzer")


class LLMError(RuntimeError):
    pass


# ==========================================================================
# Multi-provider LLM call
# ==========================================================================
def _groq_chat(system: str, user: str, temperature: float) -> str:
    if not settings.GROQ_API_KEY:
        raise LLMError("GROQ_API_KEY not configured.")
    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "User-Agent": settings.USER_AGENT,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise LLMError(f"Groq HTTP {e.code}: {e.read().decode()[:300]}") from e
    except Exception as e:
        raise LLMError(f"Groq request failed: {e}") from e
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError):
        raise LLMError("Groq returned an empty response")


def _gemini_chat(system: str, user: str, temperature: float) -> str:
    if not settings.GEMINI_API_KEY:
        raise LLMError("GEMINI_API_KEY not configured.")
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
    )
    payload = {
        "contents": [
            {"parts": [{"text": system + "\n\n" + user}]}
        ],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": 4096},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": settings.USER_AGENT},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise LLMError(f"Gemini HTTP {e.code}: {e.read().decode()[:300]}") from e
    except Exception as e:
        raise LLMError(f"Gemini request failed: {e}") from e
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError):
        raise LLMError("Gemini returned an empty response")


def _openrouter_chat(system: str, user: str, temperature: float) -> str:
    if not settings.OPENROUTER_API_KEY:
        raise LLMError("OPENROUTER_API_KEY not configured.")
    url = "https://openrouter.ai/api/v1/chat/completions"
    payload = {
        "model": settings.OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "User-Agent": settings.USER_AGENT,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise LLMError(f"OpenRouter HTTP {e.code}: {e.read().decode()[:300]}") from e
    except Exception as e:
        raise LLMError(f"OpenRouter request failed: {e}") from e
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError):
        raise LLMError("OpenRouter returned an empty response")


def llm_chat(system: str, user: str, temperature: float = 0.2, provider: str | None = None) -> str:
    """Call the configured (or specified) LLM provider."""
    provider = provider or settings.LLM_PROVIDER
    if provider == "gemini":
        return _gemini_chat(system, user, temperature)
    if provider == "openrouter":
        return _openrouter_chat(system, user, temperature)
    # default groq
    return _groq_chat(system, user, temperature)


# ==========================================================================
# Enhanced structured analysis
# ==========================================================================
LLM_SYSTEM_PROMPT = """You are an AI Financial Market Alert & Research Analyst.

Your job is to analyze the financial instrument provided to you and generate a concise but information-rich email alert.

The instrument may be: Individual Stock, Mutual Fund, ETF, or Commodity.

Your output will be embedded directly into an email, so make it: professional, easy to scan, visually attractive, data-driven, concise but sufficiently detailed, suitable for a retail investor, rich in Unicode icons/emojis, and free from unnecessary disclaimers or generic commentary.

IMPORTANT: Use ONLY the data provided to you. NEVER invent prices, returns, holdings, ownership percentages, FII/DII activity, fundamentals, reasons for price movement, or other financial data. If a required data point is unavailable, write "Data not available". Do not guess.

Produce the analysis in this order (adapt sections to the instrument type; skip irrelevant ones like promoter holding for commodities/MF, FII/DII for ETF):

1. EXECUTIVE ALERT — compact summary with 📌 name, 🏷️ type, 💰 price/NAV, 📉 today's movement, 🚨 alert reason, plus a 1-2 sentence executive summary.
2. PRICE MOVEMENT ANALYSIS — for stocks/ETFs: current price, prev close, abs/% change, day high/low, distance from high/low, 52w high/low, volume vs average. State clearly 🟢 Strongly Positive / 🟢 Positive / 🟡 Neutral / 🔴 Negative / 🔴 Strongly Negative. Explain the potential reason ONLY if supported by available news/data; else "ℹ️ No specific catalyst identified from the available data."
3. SECTOR / PEER ANALYSIS — sector check table (stock vs sector vs benchmark vs 3-5 peers using ▲/▼/➡️ and off-high %), then state UNDERPERFORMING/OUTPERFORMING/IN LINE and whether the move is 🔴 stock-specific / 🟠 sector-wide / 🟡 market-wide / 🟢 positive relative strength.
4. HISTORICAL PERFORMANCE — 1Y/3Y/5Y returns with a compact visual bar (e.g. 3Y ███████ +48% | 5Y █████████ +91%); compare with benchmark if available; state outperformance in points. For commodities use appropriate periods.
5. FUNDAMENTAL ANALYSIS (stocks) — compact snapshot: 💰 Market Cap, 📊 Revenue/growth, 💵 Net Profit/growth, 📊 EPS, P/E, P/B, ROE, ROCE, 💳 D/E, 📈 Dividend Yield, 📊 Promoter Holding; flag each 🟢/🟡/🔴 with industry context.
6. OWNERSHIP & INSTITUTIONAL ACTIVITY (stocks) — 👥 Promoter, 🏦 FII, 🏛️ DII, 👤 Retail with trend arrows; if unavailable write "Data not available". Never infer buy/sell from percentages alone.
7. TOP BUYERS / SELLERS — only if transaction-level data exists; else "ℹ️ Detailed top-buyer/seller data is not available." Never fabricate names.
8. MUTUAL FUND / ETF analysis — adapt: NAV, AUM, expense ratio, CAGR, rating, top holdings, sector allocation, benchmark tracking; flag 🟢/🟡/🔴.
9. COMMODITY analysis — price, daily move, high/low, 1Y/3Y/5Y, drivers (USD, rates, inflation, supply/demand, geopolitics) only if supported by data.
10. RISK ANALYSIS — 🟢 LOW / 🟡 MODERATE / 🟠 ELEVATED / 🔴 HIGH with top 2-3 risks.
11. FINAL INVESTMENT VIEW — 🟢 POSITIVE / 🟡 WATCH / 🟠 CAUTION / 🔴 NEGATIVE; 📌 overall view, 💡 what's working, ⚠️ what needs attention, 🎯 key levels/events.
12. ACTIONABLE SUMMARY — 🎯 INVESTOR TAKEAWAY with Trend/Sector/Valuation/Institutional/Long-term/Risk and ⭐ FINAL VIEW (BUY/ACCUMULATE/HOLD/WATCH/REDUCE/AVOID). Do NOT recommend buy/sell merely because price fell.
13. DATA QUALITY — mark items FACT / INFERENCE / UNKNOWN; never convert inference to fact; never fabricate.

FORMAT: Unicode icons, clear section headers (you MAY use ALL-CAPS headers like "📊 PRICE MOVEMENT ANALYSIS"), short paragraphs, bullets, compact tables, horizontal separators. No markdown code fences, no '**' bold. Keep key info near the top so the reader understands the event and recommendation within 30 seconds. This is an analytical view, not a guarantee of returns."""


def analyze_news(instrument_name: str, symbol: str, asset_type: str, country: str,
                 drop_pct: float, price: float, day_high: float,
                 news_items: list[dict], key_details: dict | None = None,
                 concise: bool = False) -> str:
    """Ask the LLM to produce the icon-rich analysis. Full 13-section report by
    default; a short Executive+Price+Sector+Returns+Final-View summary when concise."""
    if not news_items:
        news_blob = "No relevant news articles were found for this asset."
    else:
        news_blob = "\n".join(
            f"- [{n.get('source','')}] {n.get('title','')} :: {n.get('snippet','')}" for n in news_items
        )

    details_blob = ""
    if key_details:
        details_blob = "\n".join(f"- {k}: {v}" for k, v in key_details.items())

    asset_label = {
        "stock": "Individual Stock", "mutual_fund": "Mutual Fund",
        "etf": "ETF", "commodity": "Commodity", "crypto": "Crypto",
    }.get(asset_type, asset_type.title())

    user = (
        f"ASSET TO ANALYZE\n"
        f"Name: {instrument_name}\n"
        f"Symbol: {symbol}\n"
        f"Type: {asset_label}\n"
        f"Country: {country}\n"
        f"ALERT TRIGGER: dropped {drop_pct:.2f}% from the day's high\n"
        f"Day's high: {day_high} | Current price: {price}\n\n"
        f"DATA SUPPLIED BY APP:\n{details_blob}\n\n"
        f"NEWS SUPPLIED:\n{news_blob}\n\n"
    )

    if concise:
        user += (
            "Produce a CONCISE alert (5 short blocks only, rich Unicode icons, no long paragraphs):\n"
            "📌 EXECUTIVE ALERT — name, type, 💰 price, 📉 drop %, 1-line summary.\n"
            "🔍 PRICE MOVEMENT — day high/low, drop %, 🟢/🟡/🔴 direction; reason only if news supports it.\n"
            "📊 SECTOR & PEERS — sector vs 3-5 peers (▲/▼/➡️ with off-high %); UNDERPERFORM/OUTPERFORM/IN LINE.\n"
            "📈 3Y/5Y RETURNS — compact bar; benchmark if available.\n"
            "🎯 FINAL VIEW — ⭐ BUY/ACCUMULATE/HOLD/WATCH/REDUCE/AVOID + 1-2 line rationale. Sign off 'StockAlerts'."
        )
        prompt = LLM_SYSTEM_PROMPT
    else:
        user += "Generate the complete alert analysis now following all 13 sections of your instructions."
        prompt = LLM_SYSTEM_PROMPT

    try:
        result = llm_chat(prompt, user, temperature=0.2)
    except LLMError as e:
        log.error("LLM analysis failed: %s", e)
        result = f"Analysis unavailable: {e}"
    return result


# ==========================================================================
# Email drafting via LLM
# ==========================================================================
def draft_email(instrument_name: str, symbol: str, asset_type: str, country: str,
                 drop_pct: float, price: float, analysis: str) -> str:
    """The analysis from analyze_news is already a complete, icon-rich email body.
    This just ensures a consistent sign-off and a short subject-line-friendly header."""
    if analysis and analysis.strip():
        return analysis.strip() + "\n\n— StockAlerts"
    # Fallback if analysis is empty
    return (
        f"📉 DROP ALERT: {instrument_name} ({symbol}) dropped {drop_pct:.2f}% from day's high. "
        f"Current price {price}.\n\n— StockAlerts"
    )


# ==========================================================================
# Email sending (SMTP)
# ==========================================================================
def send_email(subject: str, body: str, to: str | None = None) -> bool:
    """Send an email via SMTP. Returns True on success."""
    to = to or settings.EMAIL_TO
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        log.warning("SMTP credentials not set; email not sent.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_FROM or settings.SMTP_USER
    msg["To"] = to
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        log.info("Email sent to %s", to)
        return True
    except Exception as e:
        log.error("Failed to send email: %s", e)
        return False