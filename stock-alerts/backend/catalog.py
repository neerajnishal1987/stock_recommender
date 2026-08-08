"""
StockAlerts — instrument catalog.
Defines the seed universe of assets across India & US for:
  stocks (large/mid/smallcap), mutual funds, ETFs, commodities, crypto.
These rows are upserted into Supabase by the load_catalog script.
"""

# ----------------------------------------------------------------------
# US stocks by cap
# ----------------------------------------------------------------------
US_STOCKS_LARGE = [
    {"symbol": "AAPL", "name": "Apple Inc."},
    {"symbol": "MSFT", "name": "Microsoft Corp."},
    {"symbol": "GOOGL", "name": "Alphabet Inc."},
    {"symbol": "AMZN", "name": "Amazon.com Inc."},
    {"symbol": "NVDA", "name": "NVIDIA Corp."},
    {"symbol": "META", "name": "Meta Platforms Inc."},
    {"symbol": "TSLA", "name": "Tesla Inc."},
    {"symbol": "JPM", "name": "JPMorgan Chase"},
    {"symbol": "V", "name": "Visa Inc."},
    {"symbol": "JNJ", "name": "Johnson & Johnson"},
]

US_STOCKS_MID = [
    {"symbol": "SQ", "name": "Block Inc."},
    {"symbol": "PLTR", "name": "Palantir Technologies"},
    {"symbol": "DOCU", "name": "DocuSign Inc."},
    {"symbol": "RBLX", "name": "Roblox Corp."},
    {"symbol": "DKNG", "name": "DraftKings Inc."},
    {"symbol": "SPOT", "name": "Spotify Technology"},
    {"symbol": "ZM", "name": "Zoom Video Comms."},
    {"symbol": "HOOD", "name": "Robinhood Markets"},
]

US_STOCKS_SMALL = [
    {"symbol": "PAYO", "name": "Payoneer Global"},
    {"symbol": "BBAI", "name": "BigBear.ai"},
    {"symbol": "SOFI", "name": "SoFi Technologies"},
    {"symbol": "LCID", "name": "Lucid Motors"},
    {"symbol": "RIVN", "name": "Rivian Automotive"},
    {"symbol": "OPEN", "name": "Opendoor Tech."},
]

# ----------------------------------------------------------------------
# India stocks by cap (Yahoo .NS/.BO suffixes)
# ----------------------------------------------------------------------
IN_STOCKS_LARGE = [
    {"symbol": "RELIANCE.NS", "name": "Reliance Industries"},
    {"symbol": "TCS.NS", "name": "Tata Consultancy Services"},
    {"symbol": "HDFCBANK.NS", "name": "HDFC Bank"},
    {"symbol": "INFY.NS", "name": "Infosys"},
    {"symbol": "ICICIBANK.NS", "name": "ICICI Bank"},
    {"symbol": "SBIN.NS", "name": "State Bank of India"},
    {"symbol": "BHARTIARTL.NS", "name": "Bharti Airtel"},
    {"symbol": "ITC.NS", "name": "ITC Ltd."},
    {"symbol": "LT.NS", "name": "Larsen & Toubro"},
    {"symbol": "HINDUNILVR.NS", "name": "Hindustan Unilever"},
]

IN_STOCKS_MID = [
    {"symbol": "TATAMOTORS.NS", "name": "Tata Motors"},
    {"symbol": "SUZLON.NS", "name": "Suzlon Energy"},
    {"symbol": "DLF.NS", "name": "DLF Ltd."},
    {"symbol": "DABUR.NS", "name": "Dabur India"},
    {"symbol": "MUTHOOTFIN.NS", "name": "Muthoot Finance"},
    {"symbol": "PERSISTENT.NS", "name": "Persistent Systems"},
]

IN_STOCKS_SMALL = [
    {"symbol": "IRFC.NS", "name": "IRFC"},
    {"symbol": "AARTIIND.NS", "name": "Aarti Industries"},
    {"symbol": "PRESTIGE.NS", "name": "Prestige Estates"},
    {"symbol": "ASHOKLEY.NS", "name": "Ashok Leyland"},
    {"symbol": "KAJARIACER.NS", "name": "Kajaria Ceramics"},
]

# ----------------------------------------------------------------------
# US & India ETF categories (macro proxies by category)
# ----------------------------------------------------------------------
US_ETF_GENERIC = [
    {"category": "index", "symbol": "SPY", "name": "SPDR S&P 500 ETF"},
    {"category": "index", "symbol": "QQQ", "name": "Invesco QQQ Trust"},
    {"category": "sector", "symbol": "XLF", "name": "Financial Select SPDR"},
    {"category": "sector", "symbol": "XLK", "name": "Technology Select SPDR"},
    {"category": "gold", "symbol": "GLD", "name": "SPDR Gold Shares"},
    {"category": "bond", "symbol": "TLT", "name": "iShares 20+ Year Treasury"},
    {"category": "growth", "symbol": "VUG", "name": "Vanguard Growth ETF"},
    {"category": "dividend", "symbol": "VYM", "name": "Vanguard High Dividend"},
]

IN_ETF_GENERIC = [
    {"category": "index", "symbol": "NIFTYBEES.NS", "name": "Nippon Nifty 50 BeES"},
    {"category": "index", "symbol": "BANKBEES.NS", "name": "Nippon Bank BeES"},
    {"category": "gold", "symbol": "GOLDBEES.NS", "name": "Nippon Gold BeES"},
    {"category": "index", "symbol": "JUNIORBEES.NS", "name": "Nippon Junior BeES"},
    {"category": "index", "symbol": "HNGSNGBEES.NS", "name": "HDFC Nifty 500"},
]

# ----------------------------------------------------------------------
# Mutual funds — NAV symbols vary by house; these are representative
# Yahoo symbols. Categories follow the requested list.
# ----------------------------------------------------------------------
US_MF = [
    {"category": "equity_large", "symbol": "VTSAX", "name": "Vanguard Total Stock Mkt Idx"},
    {"category": "equity_large", "symbol": "FXAIX", "name": "Fidelity 500 Index Fund"},
    {"category": "equity_small", "symbol": "VSMAX", "name": "Vanguard Small Cap Index"},
    {"category": "equity_mid", "symbol": "VIMAX", "name": "Vanguard Mid Cap Index"},
    {"category": "debt", "symbol": "VBTLX", "name": "Vanguard Total Bond Mkt Idx"},
    {"category": "liquid", "symbol": "VMFXX", "name": "Vanguard Federal Money Market"},
    {"category": "credit_risk", "symbol": "VWEHX", "name": "Vanguard High-Yield Corp"},
]

IN_MF = [
    {"category": "equity_large", "symbol": "0P0000YW1R.BO", "name": "HDFC Top 100 Growth"},
    {"category": "equity_large", "symbol": "0P00009VYW.BO", "name": "Mirae Asset Large Cap"},
    {"category": "equity_small", "symbol": "0P0000V0YL.BO", "name": "SBI Small Cap Fund"},
    {"category": "equity_mid", "symbol": "0P00009VYN.BO", "name": "HDFC Mid-Cap Opportunities"},
    {"category": "debt", "symbol": "0P0000NSE7.BO", "name": "ICICI Pru Corporate Bond"},
    {"category": "liquid", "symbol": "0P0000R8V4.BO", "name": "HDFC Liquid Fund"},
    {"category": "credit_risk", "symbol": "0P0000SEOX.BO", "name": "DSP Credit Risk Fund"},
]

# ----------------------------------------------------------------------
# Commodities (Yahoo futures symbols)
# ----------------------------------------------------------------------
COMMODITIES = [
    {"category": "Gold", "symbol": "GC=F", "name": "Gold Futures"},
    {"category": "Silver", "symbol": "SI=F", "name": "Silver Futures"},
    {"category": "Crude Oil (WTI)", "symbol": "CL=F", "name": "Crude Oil WTI Futures"},
    {"category": "Brent Crude", "symbol": "BZ=F", "name": "Brent Crude Futures"},
    {"category": "Natural Gas", "symbol": "NG=F", "name": "Natural Gas Futures"},
    {"category": "Copper", "symbol": "HG=F", "name": "Copper Futures"},
    {"category": "Corn", "symbol": "ZC=F", "name": "Corn Futures"},
    {"category": "Wheat", "symbol": "ZW=F", "name": "Wheat Futures"},
]

# ----------------------------------------------------------------------
# Crypto
# ----------------------------------------------------------------------
CRYPTO_ALT = [
    {"category": "ethereum", "symbol": "ETH-USD", "name": "Ethereum"},
    {"category": "solana", "symbol": "SOL-USD", "name": "Solana"},
]


def build_rows() -> list[dict]:
    """Return the full instrument seed list with country/asset_type/category."""
    rows = []

    for s in US_STOCKS_LARGE:
        rows.append({"country": "US", "asset_type": "stock", "category": "largecap", **s})
    for s in US_STOCKS_MID:
        rows.append({"country": "US", "asset_type": "stock", "category": "midcap", **s})
    for s in US_STOCKS_SMALL:
        rows.append({"country": "US", "asset_type": "stock", "category": "smallcap", **s})

    for s in IN_STOCKS_LARGE:
        rows.append({"country": "IN", "asset_type": "stock", "category": "largecap", **s})
    for s in IN_STOCKS_MID:
        rows.append({"country": "IN", "asset_type": "stock", "category": "midcap", **s})
    for s in IN_STOCKS_SMALL:
        rows.append({"country": "IN", "asset_type": "stock", "category": "smallcap", **s})

    for e in US_ETF_GENERIC:
        rows.append({"country": "US", "asset_type": "etf", "category": e["category"], "symbol": e["symbol"], "name": e["name"]})
    for e in IN_ETF_GENERIC:
        rows.append({"country": "IN", "asset_type": "etf", "category": e["category"], "symbol": e["symbol"], "name": e["name"]})

    for m in US_MF:
        rows.append({"country": "US", "asset_type": "mutual_fund", "category": m["category"], "symbol": m["symbol"], "name": m["name"]})
    for m in IN_MF:
        rows.append({"country": "IN", "asset_type": "mutual_fund", "category": m["category"], "symbol": m["symbol"], "name": m["name"]})

    for c in COMMODITIES:
        # Commodities are global (available in both IN & US). Add to both.
        rows.append({"country": "US", "asset_type": "commodity", "category": c["category"], "symbol": c["symbol"], "name": c["name"]})
        rows.append({"country": "IN", "asset_type": "commodity", "category": c["category"], "symbol": c["symbol"], "name": c["name"]})

    # Bitcoin (requested as its own asset filter)
    rows.append({"country": "US", "asset_type": "crypto", "category": "bitcoin", "symbol": "BTC-USD", "name": "Bitcoin"})
    rows.append({"country": "IN", "asset_type": "crypto", "category": "bitcoin", "symbol": "BTC-USD", "name": "Bitcoin"})

    for c in CRYPTO_ALT:
        rows.append({"country": "US", "asset_type": "crypto", "category": c["category"], "symbol": c["symbol"], "name": c["name"]})
        rows.append({"country": "IN", "asset_type": "crypto", "category": c["category"], "symbol": c["symbol"], "name": c["name"]})

    return rows
