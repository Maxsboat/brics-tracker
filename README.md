# 🌏 BRICS Investment Tracker

A daily dashboard for small investors tracking BRICS-exposed assets — ETFs, stocks, commodities, currencies, and Buffett's BRICS-adjacent Berkshire holdings.

## Features

- **📊 Watchlist** — Live prices and daily % change for all tracked tickers
- **📈 Charts** — Candlestick + volume + moving averages (5-day and 20-day MA)
- **🚦 Signals** — Momentum signal (MA crossover + RSI) for every ticker
- **📰 News Feed** — BRICS-filtered headlines from Reuters, AP, Al Jazeera, Xinhua, TASS
- **🦁 Buffett Watch** — Berkshire's BRICS-adjacent holdings with signals and context

## Signal Logic

| Signal | Condition |
|--------|-----------|
| 🟢 Watch/Buy | 5-day MA > 20-day MA, RSI neutral (35–65) |
| 🔴 Hold/Wait | 5-day MA < 20-day MA |
| 🔵 Oversold | RSI < 35 — potential entry watch |
| 🟡 Overbought | RSI > 65 — consider trimming |

> ⚠️ Signals are mechanical indicators only. This is not investment advice.

## Stack

- [Streamlit](https://streamlit.io)
- [yfinance](https://github.com/ranaroussi/yfinance) — market data (free, no API key)
- [feedparser](https://feedparser.readthedocs.io) — RSS ingestion
- [Plotly](https://plotly.com) — charts
- [pandas](https://pandas.pydata.org) — MA/RSI calculations

## Local Setup

```bash
# Clone repo
git clone https://github.com/Maxsboat/brics-tracker.git
cd brics-tracker

# Install dependencies
python3.11 -m pip install -r requirements.txt

# Set password
cat > .streamlit/secrets.toml << 'EOF'
APP_PASSWORD = "your_password_here"
EOF

# Run
python3.11 -m streamlit run app.py
```

## Streamlit Cloud Deploy

1. Push to GitHub (private repo)
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect repo → set `app.py` as entry point
4. Add secret: `APP_PASSWORD = "your_password_here"`
5. Deploy

## Tracked Assets

**ETFs:** EEM, VWO, EWZ, MCHI, INDY, EZA  
**Stocks:** VALE, BABA, JD, BIDU, INFY, NIO  
**Commodities:** GC=F (gold), CL=F (crude), HG=F (copper), SI=F (silver)  
**Currencies:** CNY=X, BRL=X, INR=X, ZAR=X  
**Buffett Watch:** OXY, CVX, ITOCY, MARUY, MSBHY, SSUMY, BYDDY  

## Data Refresh

- Market data: cached 15 minutes (yfinance)
- News feed: cached 30 minutes (feedparser)
- Use the 🔄 Refresh button to force clear cache

## Notes

- Ruble (RUB) feed excluded — unreliable post-sanctions
- Buffett has no direct BRICS investments; holdings listed represent his commodity/EM proxy plays
- All data delayed per yfinance terms
