#!/usr/bin/env python3
"""
Simple Polymarket Dashboard Example
Run: streamlit run dashboard_example.py

Install dependencies first:
    pip install streamlit py-clob-client pandas plotly
"""

import streamlit as st
from py_clob_client.client import ClobClient
import pandas as pd
import time
from datetime import datetime

# Page config
st.set_page_config(
    page_title="Polymarket Dashboard",
    page_icon="📊",
    layout="wide"
)

# Initialize client
@st.cache_resource
def get_client():
    return ClobClient("https://clob.polymarket.com")

client = get_client()

# Title
st.title("📊 Polymarket Live Dashboard")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Sidebar
st.sidebar.header("Filters")
limit = st.sidebar.slider("Number of markets to show", 10, 100, 25)
show_closed = st.sidebar.checkbox("Show closed markets", False)
min_volume = st.sidebar.number_input("Minimum volume ($)", 0, 1000000, 0, 1000)

# Auto-refresh
auto_refresh = st.sidebar.checkbox("Auto-refresh (30s)", False)

# Get markets
with st.spinner("Loading markets..."):
    markets_data = client.get_simplified_markets()
    markets = markets_data.get("data", [])

# Filter markets
filtered_markets = []
for market in markets:
    volume = float(market.get("volume", 0))
    is_closed = market.get("closed", False)
    
    # Apply filters
    if volume < min_volume:
        continue
    if is_closed and not show_closed:
        continue
    
    filtered_markets.append(market)

# Convert to DataFrame
df = pd.DataFrame(filtered_markets[:limit])

# Display metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Markets", len(filtered_markets))

with col2:
    total_volume = sum(float(m.get("volume", 0)) for m in filtered_markets)
    st.metric("Total Volume", f"${total_volume:,.0f}")

with col3:
    active_count = sum(1 for m in filtered_markets if m.get("active"))
    st.metric("Active Markets", active_count)

with col4:
    avg_volume = total_volume / len(filtered_markets) if filtered_markets else 0
    st.metric("Avg Volume", f"${avg_volume:,.0f}")

# Main table
st.subheader("Markets")

if not df.empty:
    # Select and format columns
    display_df = df[["question", "volume", "active", "closed"]].copy()
    display_df["volume"] = display_df["volume"].apply(lambda x: f"${float(x):,.2f}")
    display_df["active"] = display_df["active"].apply(lambda x: "✅" if x else "❌")
    display_df["closed"] = display_df["closed"].apply(lambda x: "🔒" if x else "🔓")
    
    # Rename columns
    display_df.columns = ["Question", "Volume", "Active", "Status"]
    
    st.dataframe(
        display_df,
        use_container_width=True,
        height=600
    )
else:
    st.warning("No markets found matching filters")

# Market details
st.subheader("Market Details")

if not df.empty:
    selected_market_idx = st.selectbox(
        "Select a market to view details:",
        range(len(filtered_markets[:limit])),
        format_func=lambda i: filtered_markets[i]["question"][:80]
    )
    
    selected_market = filtered_markets[selected_market_idx]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Market Information**")
        st.write(f"Question: {selected_market['question']}")
        st.write(f"Volume: ${float(selected_market.get('volume', 0)):,.2f}")
        st.write(f"Active: {selected_market.get('active')}")
        st.write(f"Closed: {selected_market.get('closed')}")
    
    with col2:
        st.write("**Price Data**")
        
        token_ids_str = selected_market.get("clobTokenIds", "")
        if token_ids_str:
            token_ids = token_ids_str.split(",")
            
            for i, token_id in enumerate(token_ids[:2]):  # Show first 2 outcomes
                try:
                    mid = client.get_midpoint(token_id)
                    buy = client.get_price(token_id, side="BUY")
                    sell = client.get_price(token_id, side="SELL")
                    
                    st.write(f"**Outcome {i+1}**")
                    st.write(f"Midpoint: ${mid:.4f}")
                    st.write(f"Buy: ${buy:.4f} | Sell: ${sell:.4f}")
                    st.write(f"Spread: ${abs(sell - buy):.4f}")
                    st.write("---")
                except Exception as e:
                    st.error(f"Error loading price: {e}")
        else:
            st.warning("No token IDs available for this market")

# Footer
st.divider()
st.caption("Data from Polymarket CLOB API - Read-only access, no authentication required")
st.caption("Built with py-clob-client | See POLYMARKET_DATA_ACCESS.md for more info")

# Auto-refresh logic
if auto_refresh:
    time.sleep(30)
    st.rerun()
