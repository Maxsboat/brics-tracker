import streamlit as st
import yfinance as yf
import feedparser
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="BRICS Investment Tracker",
    page_icon="🌏",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { max-width: 1200px; margin: 0 auto; }
    .metric-card {
        background: #1e2130;
        border-radius: 8px;
        padding: 12px 16px;
        margin: 4px 0;
        border-left: 4px solid #4a9eff;
    }
    .signal-buy  { color: #00c853; font-weight: 700; font-size: 1.1em; }
    .signal-wait { color: #ff5252; font-weight: 700; font-size: 1.1em; }
    .signal-over { color: #ffd600; font-weight: 700; font-size: 1.1em; }
    .signal-sold { color: #40c4ff; font-weight: 700; font-size: 1.1em; }
    .news-item {
        border-left: 3px solid #4a9eff;
        padding: 8px 12px;
        margin: 8px 0;
        background: #1e2130;
        border-radius: 0 6px 6px 0;
    }
    .news-source { font-size: 0.75em; color: #888; text-transform: uppercase; }
    .buffett-card {
        background: #1a2a1a;
        border-left: 4px solid #00c853;
        border-radius: 8px;
        padding: 12px 16px;
        margin: 4px 0;
    }
    h1 { font-size: 1.8em !important; }
    .stTabs [data-baseweb="tab"] { font-size: 0.95em; padding: 8px 16px; }
</style>
""", unsafe_allow_html=True)

# ─── Password Protection ───────────────────────────────────────────────────────
def check_password():
    if st.session_state.get("authenticated"):
        return True
    st.markdown("# 🌏 BRICS Investment Tracker")
    pwd = st.text_input("Password", type="password", key="pw_input")
    if st.button("Enter", key="pw_btn"):
        correct = st.secrets.get("APP_PASSWORD", "brics2024")
        if pwd == correct:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    return False

if not check_password():
    st.stop()

# ─── Ticker Definitions ────────────────────────────────────────────────────────
WATCHLIST = {
    "ETFs": {
        "EEM":  "iShares MSCI Emerging Markets",
        "VWO":  "Vanguard Emerging Markets",
        "EWZ":  "iShares Brazil",
        "MCHI": "iShares MSCI China",
        "INDA": "iShares MSCI India",
        "EZA":  "iShares South Africa",
    },
    "Stocks": {
        "VALE":  "Vale S.A. (Brazil — Iron Ore)",
        "BABA":  "Alibaba Group (China)",
        "JD":    "JD.com (China)",
        "BIDU":  "Baidu (China)",
        "INFY":  "Infosys (India — ADR)",
        "NIO":   "NIO Inc. (China — EV)",
        "BYDDY": "BYD Co. (China — EV/Battery ADR)",
    },
    "Commodities (ETFs — directly purchasable)": {
        "GLD":  "SPDR Gold Shares ETF",
        "USO":  "United States Oil Fund ETF",
        "CPER": "United States Copper Index ETF",
        "SLV":  "iShares Silver Trust ETF",
    },
    "Currencies (USD base)": {
        "CNY=X": "USD → Chinese Yuan",
        "BRL=X": "USD → Brazilian Real",
        "INR=X": "USD → Indian Rupee",
        "ZAR=X": "USD → S. African Rand",
    },
}

BUFFETT_WATCH = {
    "OXY":    {"name": "Occidental Petroleum",     "note": "Berkshire's largest energy bet; OXY has major Gulf/BRICS oil exposure"},
    "CVX":    {"name": "Chevron",                  "note": "Berkshire holds ~6.5% stake; deep ties to BRICS energy markets"},
    "ITOCY":  {"name": "Itochu Corp (Japan ADR)",  "note": "Japanese trading house; heavy commodity exposure across BRICS nations"},
    "MARUY":  {"name": "Marubeni Corp (Japan ADR)", "note": "Trading house with Brazil agri & energy; BRICS-linked commodities"},
    "MSBHY":  {"name": "Mitsubishi Corp (Japan ADR)","note": "Resources giant; iron ore, LNG, coal — largely BRICS-sourced"},
    "SSUMY":  {"name": "Sumitomo Corp (Japan ADR)", "note": "Infrastructure & metals; India and Brazil presence"},
    "BYDDY":  {"name": "BYD Co. (OTC ADR)",        "note": "Berkshire held for years; China's dominant EV/battery maker"},
}

RSS_FEEDS = [
    {"name": "Reuters Business", "url": "https://feeds.reuters.com/reuters/businessNews"},
    {"name": "AP Business",      "url": "https://feeds.apnews.com/rss/apf-business"},
    {"name": "Al Jazeera",       "url": "https://www.aljazeera.com/xml/rss/all.xml"},
    {"name": "Xinhua",           "url": "http://www.xinhuanet.com/english/rss/worldrss.xml"},
    {"name": "TASS",             "url": "https://tass.com/rss/v2.xml"},
    {"name": "MIT Tech Review",  "url": "https://www.technologyreview.com/feed/"},
    {"name": "Wired",            "url": "https://www.wired.com/feed/rss"},
]

BRICS_KEYWORDS = [
    "brics", "china", "india", "brazil", "russia", "south africa", "iran",
    "uae", "ethiopia", "egypt", "saudi", "yuan", "renminbi", "de-dollarization",
    "emerging market", "commodity", "oil", "gold", "copper", "trade",
    "sanctions", "mbridge", "buffett", "berkshire", "vale", "petrobras",
    "halos", "ai provenance", "ai accountability", "sbom", "cyclonedx",
    "software bill of materials", "ai transparency", "model provenance",
]

# ─── Data Functions ────────────────────────────────────────────────────────────
@st.cache_data(ttl=900)  # 15-minute cache
def fetch_ticker_data(ticker, period="3mo"):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period=period)
        if hist.empty:
            return None
        return hist
    except Exception:
        return None

@st.cache_data(ttl=900)
def fetch_quote(ticker):
    try:
        t = yf.Ticker(ticker)
        info = t.fast_info
        hist = t.history(period="2d")
        if hist.empty:
            return None
        close_today = hist["Close"].iloc[-1]
        close_prev  = hist["Close"].iloc[-2] if len(hist) > 1 else close_today
        pct_change  = ((close_today - close_prev) / close_prev) * 100
        return {
            "price":    round(close_today, 4),
            "change":   round(pct_change, 2),
            "prev":     round(close_prev, 4),
        }
    except Exception:
        return None

def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs  = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def get_signal(hist):
    if hist is None or len(hist) < 21:
        return "⬜ Insufficient data", None, None
    closes = hist["Close"]
    ma5  = closes.rolling(5).mean().iloc[-1]
    ma20 = closes.rolling(20).mean().iloc[-1]
    rsi  = calculate_rsi(closes).iloc[-1]

    if rsi < 35:
        sig = "🔵 Oversold — watch for entry"
        css = "signal-sold"
    elif rsi > 65:
        sig = "🟡 Overbought — consider trimming"
        css = "signal-over"
    elif ma5 > ma20:
        sig = "🟢 Momentum up — Watch/Buy"
        css = "signal-buy"
    else:
        sig = "🔴 Momentum down — Hold/Wait"
        css = "signal-wait"
    return sig, round(rsi, 1), css

@st.cache_data(ttl=1800)  # 30-minute cache for news
def fetch_news():
    articles = []
    for feed in RSS_FEEDS:
        try:
            parsed = feedparser.parse(feed["url"])
            for entry in parsed.entries[:20]:
                title   = getattr(entry, "title", "")
                summary = getattr(entry, "summary", "")
                link    = getattr(entry, "link", "#")
                pub     = getattr(entry, "published", "")
                text    = (title + " " + summary).lower()
                if any(kw in text for kw in BRICS_KEYWORDS):
                    articles.append({
                        "source":  feed["name"],
                        "title":   title,
                        "summary": summary[:200] + "..." if len(summary) > 200 else summary,
                        "link":    link,
                        "pub":     pub,
                    })
        except Exception:
            continue
    return articles

# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown("# 🌏 BRICS Investment Tracker")
col_ts, col_ref = st.columns([3, 1])
with col_ts:
    st.caption(f"Last loaded: {datetime.now().strftime('%B %d, %Y  %I:%M %p ET')} · Data delayed ~15 min · Not investment advice")
with col_ref:
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.divider()

# ─── Tabs ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Watchlist", "📈 Charts", "🚦 Signals", "📰 News", "🦁 Buffett Watch", "🔬 HALOS Watch"
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — WATCHLIST
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("### Daily Price & Change")
    st.caption("All prices in USD. Commodity prices are ETF share prices — directly purchasable like stocks. Currencies show how many local units buy 1 USD — higher = stronger USD.")

    for category, tickers in WATCHLIST.items():
        st.markdown(f"**{category}**")
        cols = st.columns(len(tickers))
        for col, (ticker, name) in zip(cols, tickers.items()):
            with col:
                data = fetch_quote(ticker)
                if data:
                    color = "#00c853" if data["change"] >= 0 else "#ff5252"
                    arrow = "▲" if data["change"] >= 0 else "▼"
                    st.markdown(f"""
<div class='metric-card' style='border-left-color:{color}'>
  <div style='font-size:0.75em;color:#aaa'>{ticker}</div>
  <div style='font-size:0.8em;color:#ddd'>{name}</div>
  <div style='font-size:1.4em;font-weight:700;color:#fff'>{data['price']:,.4g}</div>
  <div style='color:{color};font-size:1em'>{arrow} {abs(data['change']):.2f}%</div>
</div>
""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""
<div class='metric-card'>
  <div style='font-size:0.75em;color:#aaa'>{ticker}</div>
  <div style='font-size:0.8em;color:#555'>{name}</div>
  <div style='color:#555'>—</div>
</div>
""", unsafe_allow_html=True)
        st.markdown("")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — CHARTS
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### Price Charts")

    all_tickers = {}
    for cat, tickers in WATCHLIST.items():
        for tk, nm in tickers.items():
            all_tickers[f"{tk} — {nm}"] = tk
    for tk, info in BUFFETT_WATCH.items():
        all_tickers[f"{tk} — {info['name']} (Buffett)"] = tk

    selected_label = st.selectbox("Select ticker", list(all_tickers.keys()))
    selected_ticker = all_tickers[selected_label]
    period_choice = st.radio("Period", ["1mo", "3mo", "6mo", "1y"], horizontal=True, index=1)

    hist = fetch_ticker_data(selected_ticker, period=period_choice)
    if hist is not None and not hist.empty:
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            row_heights=[0.75, 0.25],
            vertical_spacing=0.03
        )

        # Candlestick
        fig.add_trace(go.Candlestick(
            x=hist.index,
            open=hist["Open"], high=hist["High"],
            low=hist["Low"],   close=hist["Close"],
            name=selected_ticker,
            increasing_line_color="#00c853",
            decreasing_line_color="#ff5252",
        ), row=1, col=1)

        # MAs
        if len(hist) >= 5:
            fig.add_trace(go.Scatter(
                x=hist.index, y=hist["Close"].rolling(5).mean(),
                line=dict(color="#4a9eff", width=1.5),
                name="5-day MA"
            ), row=1, col=1)
        if len(hist) >= 20:
            fig.add_trace(go.Scatter(
                x=hist.index, y=hist["Close"].rolling(20).mean(),
                line=dict(color="#ff9800", width=1.5),
                name="20-day MA"
            ), row=1, col=1)

        # Volume
        colors = ["#00c853" if c >= o else "#ff5252"
                  for c, o in zip(hist["Close"], hist["Open"])]
        fig.add_trace(go.Bar(
            x=hist.index, y=hist["Volume"],
            marker_color=colors, name="Volume", opacity=0.6
        ), row=2, col=1)

        fig.update_layout(
            height=520,
            paper_bgcolor="#0e1117",
            plot_bgcolor="#0e1117",
            font=dict(color="#ddd"),
            xaxis_rangeslider_visible=False,
            legend=dict(orientation="h", y=1.05),
            margin=dict(l=40, r=20, t=30, b=20),
        )
        fig.update_xaxes(gridcolor="#222", showgrid=True)
        fig.update_yaxes(gridcolor="#222", showgrid=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning(f"Could not retrieve chart data for {selected_ticker}.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — SIGNALS
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### Momentum Signals")
    st.caption("Signal logic: 5-day MA vs 20-day MA crossover + 14-period RSI. This is a mechanical indicator — not a recommendation.")

    st.markdown("""
| Signal | Meaning |
|--------|---------|
| 🟢 Momentum up — Watch/Buy | 5-day MA above 20-day MA, RSI neutral |
| 🔴 Momentum down — Hold/Wait | 5-day MA below 20-day MA |
| 🔵 Oversold (RSI < 35) | Potential entry point — watch for reversal |
| 🟡 Overbought (RSI > 65) | Extended — consider trimming or waiting |
""")
    st.divider()

    all_signal_tickers = {}
    for cat, tickers in WATCHLIST.items():
        for tk, nm in tickers.items():
            all_signal_tickers[tk] = (nm, cat)

    for category, tickers in WATCHLIST.items():
        st.markdown(f"**{category}**")
        rows = []
        for ticker, name in tickers.items():
            hist = fetch_ticker_data(ticker, period="3mo")
            quote = fetch_quote(ticker)
            sig, rsi_val, css = get_signal(hist)
            price  = f"{quote['price']:,.4g}" if quote else "—"
            change = f"{quote['change']:+.2f}%" if quote else "—"
            rows.append({
                "Ticker": ticker,
                "Name":   name,
                "Price":  price,
                "Day %":  change,
                "RSI":    rsi_val if rsi_val else "—",
                "Signal": sig,
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.markdown("")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — NEWS FEED
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("### BRICS News Feed")
    st.caption("Headlines filtered for BRICS-relevant content from Reuters, AP, Al Jazeera, Xinhua, TASS.")

    source_filter = st.multiselect(
        "Filter by source",
        options=[f["name"] for f in RSS_FEEDS],
        default=[f["name"] for f in RSS_FEEDS]
    )

    with st.spinner("Loading headlines..."):
        articles = fetch_news()

    filtered = [a for a in articles if a["source"] in source_filter]

    if filtered:
        st.caption(f"{len(filtered)} BRICS-relevant articles found.")
        for art in filtered:
            st.markdown(f"""
<div class='news-item'>
  <div class='news-source'>{art['source']} · {art['pub'][:25] if art['pub'] else ''}</div>
  <div style='font-weight:600;margin:4px 0'><a href='{art['link']}' target='_blank' style='color:#4a9eff;text-decoration:none'>{art['title']}</a></div>
  <div style='font-size:0.85em;color:#bbb'>{art['summary']}</div>
</div>
""", unsafe_allow_html=True)
    else:
        st.info("No BRICS-relevant articles found from selected sources right now. Try refreshing.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — BUFFETT WATCH
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown("### 🦁 Buffett Watch — Berkshire BRICS-Adjacent Holdings")
    st.caption(
        "Buffett doesn't invest directly in BRICS markets — but these Berkshire holdings have substantial "
        "revenue, commodity, or infrastructure exposure to BRICS economies. Watch them as a proxy."
    )
    st.divider()

    for ticker, info in BUFFETT_WATCH.items():
        quote = fetch_quote(ticker)
        hist  = fetch_ticker_data(ticker, period="3mo")
        sig, rsi_val, _ = get_signal(hist)

        if quote:
            color = "#00c853" if quote["change"] >= 0 else "#ff5252"
            arrow = "▲" if quote["change"] >= 0 else "▼"
            price_str  = f"${quote['price']:,.2f}"
            change_str = f"{arrow} {abs(quote['change']):.2f}%"
        else:
            color, price_str, change_str = "#888", "—", "—"

        st.markdown(f"""
<div class='buffett-card'>
  <div style='display:flex;justify-content:space-between;align-items:flex-start'>
    <div>
      <span style='font-size:1.2em;font-weight:700;color:#fff'>{ticker}</span>
      <span style='color:#aaa;margin-left:10px'>{info['name']}</span>
    </div>
    <div style='text-align:right'>
      <div style='font-size:1.3em;font-weight:700;color:#fff'>{price_str}</div>
      <div style='color:{color}'>{change_str}</div>
    </div>
  </div>
  <div style='color:#9e9;font-size:0.85em;margin-top:6px'>{info['note']}</div>
  <div style='font-size:0.85em;margin-top:4px'>{sig} · RSI: {rsi_val if rsi_val else "—"}</div>
</div>
""", unsafe_allow_html=True)
        st.markdown("")

    st.info(
        "**Why Japanese trading houses?** Buffett disclosed stakes in all five major Japanese "
        "sogo shosha in 2020 and has since increased them. These firms — Itochu, Marubeni, Mitsubishi, "
        "Mitsui, Sumitomo — are the world's largest commodity and resource traders, with deep BRICS-market "
        "supply chains. His move is widely read as a commodity/emerging markets play by proxy."
    )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — HALOS WATCH
# ══════════════════════════════════════════════════════════════════════════════
with tab6:
    st.markdown("### 🔬 HALOS Watch — AI Provenance & Accountability")
    st.caption("Monitoring developments in AI transparency, provenance, and accountability frameworks.")

    st.markdown("""
<div style='background:#1a1a2e;border-left:4px solid #7c4dff;border-radius:8px;padding:16px 20px;margin-bottom:16px'>
  <div style='font-size:1.1em;font-weight:700;color:#fff;margin-bottom:8px'>What is HALOS?</div>
  <div style='color:#ccc;font-size:0.9em;line-height:1.6'>
    HALOS (Hierarchical Accountability and Lineage for Open Systems) is an open-source AI provenance 
    and accountability framework developed in northern Michigan. It addresses a critical gap in AI 
    deployment: the ability to trace, verify, and audit the lineage of AI models, datasets, and 
    decisions across organizational boundaries.<br><br>
    Built on open standards including <strong>CycloneDX</strong>, <strong>SLSA</strong>, and 
    <strong>in-toto predicates</strong>, HALOS provides the infrastructure for AI accountability 
    that eight professional domains — law, medicine, journalism, finance, government, education, 
    research, and engineering — urgently need but currently lack.
  </div>
</div>
""", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
<div style='background:#1e2130;border-radius:8px;padding:16px;margin-bottom:12px'>
  <div style='font-weight:700;color:#7c4dff;margin-bottom:8px'>🏗️ Technical Foundation</div>
  <div style='color:#ccc;font-size:0.875em;line-height:1.8'>
    • <strong>CycloneDX</strong> — Software Bill of Materials (SBOM) standard<br>
    • <strong>SLSA</strong> — Supply chain security framework<br>
    • <strong>in-toto predicates</strong> — Cryptographic attestation<br>
    • <strong>Open source</strong> — Community governed<br>
    • <strong>Cross-domain</strong> — Built for interoperability
  </div>
</div>
""", unsafe_allow_html=True)

    with col2:
        st.markdown("""
<div style='background:#1e2130;border-radius:8px;padding:16px;margin-bottom:12px'>
  <div style='font-weight:700;color:#7c4dff;margin-bottom:8px'>🎯 Target Domains</div>
  <div style='color:#ccc;font-size:0.875em;line-height:1.8'>
    • Legal & compliance<br>
    • Medicine & clinical AI<br>
    • Journalism & media verification<br>
    • Financial services<br>
    • Government & regulation<br>
    • Education & research<br>
    • Engineering & infrastructure
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div style='background:#1e2130;border-radius:8px;padding:16px;margin-bottom:16px'>
  <div style='font-weight:700;color:#7c4dff;margin-bottom:8px'>🔗 Resources</div>
  <div style='color:#ccc;font-size:0.875em;line-height:2'>
    • <a href='https://github.com' target='_blank' style='color:#4a9eff'>HALOS GitHub Repository</a> — Source code and documentation<br>
    • <a href='https://cyclonedx.org' target='_blank' style='color:#4a9eff'>CycloneDX Standard</a> — SBOM specification<br>
    • <a href='https://slsa.dev' target='_blank' style='color:#4a9eff'>SLSA Framework</a> — Supply chain security levels<br>
    • <a href='https://in-toto.io' target='_blank' style='color:#4a9eff'>in-toto Project</a> — Software supply chain integrity
  </div>
</div>
""", unsafe_allow_html=True)

    st.divider()
    st.markdown("### 📡 AI Accountability News")
    st.caption("Headlines filtered for AI provenance, transparency, and accountability developments.")

    HALOS_KEYWORDS = [
        "ai provenance", "ai accountability", "ai transparency", "sbom",
        "software bill of materials", "model transparency", "ai audit",
        "algorithmic accountability", "ai governance", "ai regulation",
        "ai supply chain", "model lineage", "ai traceability", "cyclonedx",
        "ai ethics", "responsible ai", "ai compliance", "ai oversight",
    ]

    @st.cache_data(ttl=1800)
    def fetch_halos_news():
        articles = []
        halos_feeds = [
            {"name": "MIT Tech Review",  "url": "https://www.technologyreview.com/feed/"},
            {"name": "Wired",            "url": "https://www.wired.com/feed/rss"},
            {"name": "Reuters Tech",     "url": "https://feeds.reuters.com/reuters/technologyNews"},
            {"name": "AP Technology",    "url": "https://feeds.apnews.com/rss/apf-technology"},
        ]
        for feed in halos_feeds:
            try:
                parsed = feedparser.parse(feed["url"])
                for entry in parsed.entries[:25]:
                    title   = getattr(entry, "title", "")
                    summary = getattr(entry, "summary", "")
                    link    = getattr(entry, "link", "#")
                    pub     = getattr(entry, "published", "")
                    text    = (title + " " + summary).lower()
                    if any(kw in text for kw in HALOS_KEYWORDS):
                        articles.append({
                            "source":  feed["name"],
                            "title":   title,
                            "summary": summary[:200] + "..." if len(summary) > 200 else summary,
                            "link":    link,
                            "pub":     pub,
                        })
            except Exception:
                continue
        return articles

    with st.spinner("Loading AI accountability news..."):
        halos_articles = fetch_halos_news()

    if halos_articles:
        st.caption(f"{len(halos_articles)} relevant articles found.")
        for art in halos_articles:
            st.markdown(f"""
<div style='border-left:3px solid #7c4dff;padding:8px 12px;margin:8px 0;background:#1e2130;border-radius:0 6px 6px 0'>
  <div style='font-size:0.75em;color:#888;text-transform:uppercase'>{art['source']} · {art['pub'][:25] if art['pub'] else ''}</div>
  <div style='font-weight:600;margin:4px 0'><a href='{art['link']}' target='_blank' style='color:#7c4dff;text-decoration:none'>{art['title']}</a></div>
  <div style='font-size:0.85em;color:#bbb'>{art['summary']}</div>
</div>
""", unsafe_allow_html=True)
    else:
        st.info("No AI accountability articles found right now. Try refreshing.")

    st.divider()
    st.caption(
        "HALOS is an independent open-source project. This tab monitors the broader AI accountability "
        "ecosystem — regulatory developments, standards evolution, and deployment news relevant to "
        "the domains HALOS serves."
    )

# ─── Footer ───────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "⚠️ This tool displays publicly available market data and mechanical momentum indicators only. "
    "It is not investment advice. All investment decisions are yours alone. "
    "Past momentum is not predictive of future returns."
)
