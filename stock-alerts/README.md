# StockAlerts — Market Drop Monitor

A local web app + automated pipeline that monitors **India & US** markets across **stocks, mutual funds, ETFs, commodities, and bitcoin**, stores data in **Supabase (PostgreSQL)**, and emails **neerajnishal@gmail.com** when any asset drops **≥5% from its day's high** — with the likely reasons analyzed by an **LLM** (Groq / Gemini / OpenRouter) from fetched news.

## Features

1. **Country filter** — India (IN) or United States (US).
2. **Asset-type filters** — Direct Stock, Mutual Fund, ETF, Commodities, Bitcoin/Crypto.
3. **Stock cap filter** — Large Cap, Mid Cap, Small Cap.
4. **Mutual Fund / ETF category filter** — Equity (large/small/mid), Debt, Liquid, Credit Risk, plus ETF categories (Index, Sector, Gold, Bond, Growth, Dividend).
5. **Commodity filter** — Gold, Silver, Crude Oil, Brent, Natural Gas, Copper, Corn, Wheat.
6. **Crypto filter** — Bitcoin, Ethereum, Solana.
7. **Supabase PostgreSQL database** — stores instruments, daily market data, alerts, and news. Data refreshed daily.
8. **Realtime drop pipeline** — for stocks, ETFs, commodities & crypto: if an asset drops ≥5% from its day's high, it fetches up to 10–20 news articles, uses the configured **LLM** to summarize the likely reasons, and emails the alert.
9. **Multi-provider LLM** — **Groq** (default), **Google Gemini** (free), and **OpenRouter** (free models). Switch via `LLM_PROVIDER` env var.
10. **Enhanced AI summary** — each alert email includes: (1) Price Movement (X→Y, -Z%), (2) Fundamentals Change, (3) News-Based Reasons, (4) LLM Recommendation (Buy/Hold/Sell).
11. **Key details** — 52-week high/low, key owners (institutional holders), sector, market cap, forward P/E, sector momentum.
12. **GitHub Actions** — scheduled workflows run the refresh and alert checks automatically.
13. **Free static hosting** — dashboard can be hosted on Vercel/Netlify/GitHub Pages with a custom domain (reads Supabase directly via anon key).

## Architecture

```
Stock_Recommender/stock-alerts/
├── supabase/schema.sql          # PostgreSQL schema (run in Supabase)
├── backend/
│   ├── config.py                # Env config (Supabase, LLM providers, SMTP)
│   ├── db.py                    # Supabase REST (PostgREST) client
│   ├── catalog.py               # Instrument universe (IN/US, all asset classes)
│   ├── news.py                  # News fetcher (NewsAPI / MediaStack / Google RSS)
│   └── analyzer.py              # Multi-provider LLM (Groq/Gemini/OpenRouter) + email
├── scripts/
│   ├── load_catalog.py          # Seed instruments into Supabase
│   ├── refresh_data.py          # Daily market data refresh (yfinance)
│   └── check_alerts.py          # Drop detection → news → LLM → email
├── web/                         # Static dashboard (Vercel/Netlify/GitHub Pages ready)
│   ├── index.html
│   ├── styles.css
│   ├── app.js                   # auto-detects local API vs direct Supabase read
│   └── config.js                # ← Supabase URL + anon key (for static hosting)
├── serve.py                     # Local Flask dev server (port 5050)
├── vercel.json                  # Vercel deploy config
├── netlify.toml                 # Netlify deploy config
├── .github/workflows/
│   ├── daily-refresh.yml        # Scheduled data refresh
│   └── alerts.yml               # Scheduled drop-alert checks
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

### 1. Supabase (PostgreSQL)

1. Create a project at [supabase.com](https://supabase.com).
2. Open **SQL Editor** and run the contents of `supabase/schema.sql`.
3. Copy your **Project URL**, **anon key**, and **service_role key** from **Settings → API**.

### 2. Local environment

```bash
cd Stock_Recommender/stock-alerts
cp .env.example .env
# fill in .env with your keys
pip install -r requirements.txt

# Seed the instrument catalog
python3 scripts/load_catalog.py

# Refresh market data (daily)
python3 scripts/refresh_data.py

# Run the drop-alert pipeline
python3 scripts/check_alerts.py

# Run the local dashboard
python3 serve.py        # then open http://localhost:5050
```

### 3. Web dashboard

**Local:** `python3 serve.py` → open http://localhost:5050 (uses local `/api/*` proxy).

**Static hosting (Vercel/Netlify/GitHub Pages):** the dashboard reads Supabase directly via the anon key in `web/config.js`. Set your URL + anon key there, then deploy the `web/` folder.

### 4. GitHub Actions (automation)

Push this folder to a GitHub repo, then add these **repository secrets** (Settings → Secrets → Actions):

| Secret | Purpose |
|--------|---------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Service role key (pipeline writes) |
| `SUPABASE_ANON_KEY` | Anon key (dashboard reads) |
| `GROQ_API_KEY` | Groq LLM (default) |
| `GEMINI_API_KEY` | Google Gemini (free) |
| `OPENROUTER_API_KEY` | OpenRouter (free models) |
| `LLM_PROVIDER` | `groq` / `gemini` / `openrouter` |
| `NEWSAPI_KEY` / `MEDIASTACK_KEY` | News providers (optional; falls back to Google RSS) |
| `SMTP_USER` / `SMTP_PASSWORD` | Gmail App Password (NOT your normal password) |
| `EMAIL_TO` | Defaults to `neerajnishal@gmail.com` |
| `DROP_THRESHOLD_PCT` | Defaults to `5` |

The workflows run on a schedule:
- **daily-refresh.yml** — every 4 hours (loads catalog + refreshes market data).
- **alerts.yml** — every 15 minutes (checks for ≥5% drops from day's high, fetches news, analyzes with LLM, emails).

You can also trigger both manually from the **Actions** tab.

## LLM providers

| Provider | Free tier | Notes |
|----------|-----------|-------|
| **Groq** | ✅ Free tier (6k tokens/min) | Fastest; default. `LLM_PROVIDER=groq` |
| **Google Gemini** | ✅ Free (1000 req/day) | `gemini-2.0-flash`. `LLM_PROVIDER=gemini` |
| **OpenRouter** | ✅ Free models | e.g. `meta-llama/llama-3.3-70b-instruct:free`. `LLM_PROVIDER=openrouter` |

## Email alert format

- **Subject:** `⚠️ Drop Alert: <Name> (<Symbol>) -<X.XX>% [<TYPE>]`
- **Body** (LLM-drafted):
  1. **Price Movement** — dropped from X to Y (-Z%)
  2. **Fundamentals Change** — any change in earnings/margins/valuation
  3. **News-Based Reasons** — up to 10 reasons from fetched articles
  4. **Recommendation** — Buy/Hold/Sell with rationale
  - **Key Details** — 52-week high/low, key owners, sector, market cap, forward P/E

## Free hosting with custom domain (investorspider.com)

The dashboard is a static site that reads Supabase directly (via the anon key in `web/config.js`), so it can be hosted **100% free** on GitHub Pages with your custom domain. The alert pipeline runs via GitHub Actions (no server needed).

### Option A: GitHub Pages (recommended — fully automated)

A deploy workflow (`.github/workflows/deploy-pages.yml`) auto-deploys the `web/` folder to GitHub Pages on every push to `main`.

1. **Register the domain** `investorspider.com` (e.g. via Namecheap/Porkbun — ~$10/yr). The domain itself is not free, but GitHub Pages hosting is.
2. **Push to `main`** — the workflow copies `stock-alerts/web/*` and deploys it.
3. **Enable GitHub Pages** in your repo: Settings → Pages → set source to "GitHub Actions" (the workflow handles the rest).
4. **Point DNS** at GitHub: create a **CNAME** record for `investorspider.com` (and `www`) pointing to `neerajnishal1987.github.io`.
5. **Add repo secrets** (Settings → Secrets → Actions): `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `GROQ_API_KEY`, `GEMINI_API_KEY`, `NEWSAPI_KEY`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_TO`, `DROP_THRESHOLD_PCT`, `LLM_PROVIDER`.

### Option B: Vercel / Netlify

- **Vercel**: import the repo → set `stock-alerts/web/` as the root → add custom domain in the dashboard.
- **Netlify**: drag-and-drop the `web/` folder → add custom domain in Site settings.
- Point DNS at the host's nameservers.

## Notes

- Market data uses **yfinance** (Yahoo Finance). Some mutual-fund NAV symbols may not resolve; adjust `catalog.py` symbols as needed.
- The dashboard reads via the anon key (read-only). The pipeline uses the service role key.
- For production, tighten the RLS policies in `schema.sql` (the included ones allow public reads for the dashboard).
- Gmail SMTP requires an **App Password** (not your normal password) with 2-Step Verification enabled.
