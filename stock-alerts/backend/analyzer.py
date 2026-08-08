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
def analyze_news(instrument_name: str, symbol: str, drop_pct: float, price: float,
                 news_items: list[dict], key_details: dict | None = None) -> str:
    """Ask the LLM to produce a structured summary of the drop."""
    if not news_items:
        news_blob = "No relevant news articles were found for this asset."
    else:
        news_blob = "\n".join(
            f"- [{n.get('source','')}] {n.get('title','')} :: {n.get('snippet','')}" for n in news_items
        )

    details_blob = ""
    if key_details:
        details_blob = "\n".join(f"- {k}: {v}" for k, v in key_details.items())

    system = (
        "You are a senior market analyst. Produce a structured, professional analysis of a price drop. "
        "Use ONLY the information provided. Output in plain text with these exact numbered sections:\n"
        "1. PRICE MOVEMENT: state the drop from day's high (X to Y, -Z%).\n"
        "2. FUNDAMENTALS CHANGE: highlight any change in fundamentals (earnings, margins, valuation, guidance) if present in the data; if none, say 'No material fundamental change detected'.\n"
        "3. NEWS-BASED REASONS: list up to 10 distinct reasons from the news, each on its own '- ' bullet.\n"
        "4. RECOMMENDATION: give a clear bias (Buy/Hold/Sell) with a 1-2 sentence rationale based on the data.\n"
        "Do not use markdown headers or code fences."
    )
    user = (
        f"Asset: {instrument_name} ({symbol})\n"
        f"Price dropped {drop_pct:.2f}% from the day's high. Current price: {price}.\n"
        f"KEY DETAILS:\n{details_blob}\n\n"
        f"NEWS:\n{news_blob}\n\n"
        "Now produce the structured analysis:"
    )

    try:
        result = llm_chat(system, user, temperature=0.2)
    except LLMError as e:
        log.error("LLM analysis failed: %s", e)
        result = f"Analysis unavailable: {e}"
    return result


# ==========================================================================
# Email drafting via LLM
# ==========================================================================
def draft_email(instrument_name: str, symbol: str, asset_type: str, country: str,
                drop_pct: float, price: float, analysis: str) -> str:
    """Ask the LLM to draft the email body for the drop alert."""
    system = (
        "You are an automated investment alert assistant. Draft a clear, professional, plain-text email "
        "informing the recipient about a market drop. Keep it concise (under ~250 words). "
        "Use the exact numbers given. No markdown, no code fences, no emojis. "
        "Structure: greeting, alert summary, the key analysis points, quick action note, signature 'StockAlerts'."
    )
    user = (
        f"Asset: {instrument_name} ({symbol})\n"
        f"Type: {asset_type} | Country: {country}\n"
        f"Drop: {drop_pct:.2f}% from day's high | Current price: {price}\n\n"
        f"ANALYSIS:\n{analysis}\n\n"
        "Draft the alert email body:"
    )
    try:
        body = llm_chat(system, user, temperature=0.3)
    except LLMError as e:
        log.error("LLM email draft failed: %s", e)
        body = (
            f"ALERT: {instrument_name} ({symbol}) dropped {drop_pct:.2f}% from day's high. "
            f"Current price {price}. Please review.\n\n{analysis}\n\n— StockAlerts"
        )
    return body


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