-- ============================================================
-- StockAlerts — Supabase PostgreSQL schema
-- Run this in the Supabase SQL Editor or via `supabase db push`
-- ============================================================

-- Extended pgcrypto for gen_random_uuid()
create extension if not exists pgcrypto;

-- ------------------------------------------------------------
-- instruments : catalog of tradable assets
-- ------------------------------------------------------------
create table if not exists public.instruments (
    id           uuid primary key default gen_random_uuid(),
    country      text not null check (country in ('IN','US')),
    asset_type   text not null check (asset_type in ('stock','mutual_fund','etf','commodity','crypto')),
    category     text,               -- largecap/midcap/smallcap (stock); equity_large/equity_small/equity_mid/debt/liquid/credit_risk (mf/etf); commodity name; 'bitcoin' for crypto
    symbol       text not null,      -- Yahoo symbol, e.g. RELIANCE.NS, AAPL, GLD, GC=F, BTC-USD
    name         text not null,
    is_active    boolean default true,
    created_at   timestamptz default now(),
    unique (country, asset_type, symbol)
);

-- ------------------------------------------------------------
-- market_data : daily market snapshot per instrument
-- ------------------------------------------------------------
create table if not exists public.market_data (
    id            bigint generated always as identity primary key,
    instrument_id uuid not null references public.instruments(id) on delete cascade,
    as_of         timestamptz not null,
    price         numeric(18,6),
    day_high      numeric(18,6),
    day_low       numeric(18,6),
    prev_close    numeric(18,6),
    day_open      numeric(18,6),
    change_pct    numeric(10,4),     -- vs prev close
    volume        numeric(24,0),
    source        text default 'yfinance',
    created_at    timestamptz default now()
);
create index if not exists idx_market_data_instrument_time on public.market_data (instrument_id, as_of desc);

-- ------------------------------------------------------------
-- alerts : detected drops (>= threshold from day's high)
-- ------------------------------------------------------------
create table if not exists public.alerts (
    id              uuid primary key default gen_random_uuid(),
    instrument_id   uuid not null references public.instruments(id) on delete cascade,
    alert_type      text not null check (alert_type in ('drop_from_high')),
    drop_pct        numeric(10,4) not null,   -- % below day's high
    price           numeric(18,6),
    day_high        numeric(18,6),
    moved_off_high  numeric(10,4),            -- % off day's high
    detected_at     timestamptz default now(),
    news_summary    text,
    status          text default 'new' check (status in ('new','analyzed','email_sent','failed')),
    groq_analysis   text,
    email_body      text
);
create index if not exists idx_alerts_instrument on public.alerts (instrument_id, detected_at desc);
create index if not exists idx_alerts_status on public.alerts (status);

-- ------------------------------------------------------------
-- news_articles : fetched news linked to an alert
-- ------------------------------------------------------------
create table if not exists public.news_articles (
    id            bigint generated always as identity primary key,
    alert_id      uuid references public.alerts(id) on delete cascade,
    instrument_id uuid references public.instruments(id) on delete cascade,
    title         text,
    url           text,
    source        text,
    published_at  timestamptz,
    snippet       text,
    created_at    timestamptz default now()
);
create index if not exists idx_news_alert on public.news_articles (alert_id);

-- ------------------------------------------------------------
-- RLS : allow authenticated/app reads; writes via service role only
-- Modify to your own RLS policy (e.g. allow anon SELECT for the dashboard)
-- ------------------------------------------------------------
alter table public.instruments  enable row level security;
alter table public.market_data  enable row level security;
alter table public.alerts       enable row level security;
alter table public.news_articles enable row level security;

-- Allow anonymous read (for the GitHub Pages dashboard using the anon key)
-- OPTIONAL: tighten as needed for production.
create policy instruments_select on public.instruments  for select using (true);
create policy market_data_select on public.market_data  for select using (true);
create policy alerts_select      on public.alerts       for select using (true);
create policy news_select        on public.news_articles for select using (true);

-- WARNING: the below allow all writes via any key.
-- For a public dashboard you should instead use the service role key in the pipeline
-- and keep anon key read-only. These policies are for demo convenience.
create policy market_data_insert on public.market_data for insert with check (true);
create policy alerts_insert      on public.alerts      for insert with check (true);
create policy news_insert        on public.news_articles for insert with check (true);