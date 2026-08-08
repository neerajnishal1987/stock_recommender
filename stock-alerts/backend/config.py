"""
StockAlerts — configuration
Loads settings from environment variables (also from a local .env file when present).
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass


def _get_float(name, default):
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


class Settings:
    # Supabase
    SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
    SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

    # Drop alert threshold: trigger when an asset drops this % from its day's high
    DROP_THRESHOLD_PCT = _get_float("DROP_THRESHOLD_PCT", 5.0)

    # YFinance / market data
    USER_AGENT = os.getenv("USER_AGENT", "StockAlerts/1.0")

    # News
    NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
    MEDIASTACK_KEY = os.getenv("MEDIASTACK_KEY", "")
    NEWS_SOURCES = os.getenv("NEWS_SOURCES", "bloomberg,reuters,cnbc,marketwatch,financialtimes,cnbc,associatedpress")
    MAX_NEWS_PER_ALERT = int(os.getenv("MAX_NEWS_PER_ALERT", "10"))

    # Groq
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    # Google Gemini (free)
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    # OpenRouter (free models)
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")

    # Preferred provider: groq | gemini | openrouter
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")

    # Email (SMTP)
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    EMAIL_TO = os.getenv("EMAIL_TO", "neerajnishal@gmail.com")
    EMAIL_FROM = os.getenv("EMAIL_FROM", os.getenv("SMTP_USER", ""))


settings = Settings()