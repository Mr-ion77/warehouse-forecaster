"""Streamlit UI for the Warehouse Forecaster.

Run from the repository root:  streamlit run scripts/streamlit_app.py
Data path can be overridden with the WAREHOUSE_DATA_PATH environment variable.
"""

import os

import pandas as pd
import streamlit as st

from warehouse_forecaster.constants import COL_ITEM, DEFAULT_INVENTORY_CSV
from warehouse_forecaster.data.io import load_inventory_csv
from warehouse_forecaster.models.alerts import build_alert_table
from warehouse_forecaster.utils.plotting import create_plotly_forecast, style_alert_table

DATA_PATH = os.environ.get("WAREHOUSE_DATA_PATH", str(DEFAULT_INVENTORY_CSV))

# --- PAGE CONFIG ---
st.set_page_config(page_title="Inventory Forecaster", page_icon="📦", layout="wide")

# Tighter metric cards
st.markdown("""
    <style>
    div[data-testid="metric-container"] {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        padding: 15px;
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)


@st.cache_data
def load_data(path: str = DATA_PATH):
    return load_inventory_csv(path)


# --- UI LAYOUT ---
st.title("📦 Warehouse Forecaster")
st.markdown("Predictive inventory depletion based on historical demand trends.")

df = load_data()
items = sorted(df[COL_ITEM].unique())

st.sidebar.title("Navigation")
view_mode = st.sidebar.radio("Select View:", ["Bulk Alert Dashboard", "Individual Item Deep-Dive"])
st.sidebar.markdown("---")
forecast_window = st.sidebar.slider("Forecast Horizon (Days)", 7, 90, 30)

if view_mode == "Bulk Alert Dashboard":
    st.header("🚨 Action Required: Stockout Alerts")
    top_n = st.sidebar.number_input("Items to display", min_value=1, max_value=100, value=15)

    if st.button("Run Bulk Analysis", type="primary"):
        progress_bar = st.progress(0)
        status_text = st.empty()

        def on_progress(done, total):
            progress_bar.progress(done / total)
            status_text.text(f"Crunching data: {done} / {total}...")

        report_df = build_alert_table(df, forecast_window, items=items, progress=on_progress).head(top_n)

        progress_bar.empty()
        status_text.empty()

        st.dataframe(
            style_alert_table(report_df, forecast_window),
            column_config={
                "Referencia": st.column_config.TextColumn("Product ID"),
                "Est. Stockout": st.column_config.TextColumn("Depletion Date"),
            },
            hide_index=True,
            use_container_width=True
        )

else:
    selected_item = st.sidebar.selectbox("Select an Item", items)

    if selected_item:
        item_df = df[df[COL_ITEM] == selected_item]
        fig, current_stock, stockout_date, burn_rate = create_plotly_forecast(item_df, selected_item, forecast_window)

        if fig:
            col1, col2, col3 = st.columns(3)
            col1.metric("Current Stock", f"{current_stock:.0f} units")
            col2.metric("30-Day Avg. Burn Rate", f"{burn_rate:.1f} units/day")

            if stockout_date:
                days_left = (stockout_date - pd.Timestamp.today().normalize()).days
                col3.metric("Urgency", f"{days_left} Days Left", delta="- Critical", delta_color="inverse")
            else:
                col3.metric("Urgency", "> 30 Days", delta="Safe", delta_color="normal")

            st.markdown("---")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Not enough data to forecast this item.")
