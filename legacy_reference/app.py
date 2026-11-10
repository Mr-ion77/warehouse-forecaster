import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from pandas.tseries.offsets import DateOffset

# --- PAGE CONFIG ---
st.set_page_config(page_title="Inventory Forecaster", page_icon="📦", layout="wide")

# Custom CSS to make the metrics look tighter
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

# --- CORE FUNCTIONS ---
@st.cache_data
def load_data():
    df = pd.read_csv('synthetic_inventory.csv', sep=';')
    if df['Cantidad'].dtype == 'object':
        df['Cantidad'] = df['Cantidad'].str.replace(',', '.').astype(float)
    df['Fecha proceso'] = pd.to_datetime(df['Fecha proceso'], format='mixed', dayfirst=True)
    df['Timeline'] = df['Fecha proceso'].dt.normalize()
    return df

def predict_stockout_for_item(item_df, forecast_days=30):
    df_daily = item_df.groupby(['Tipo', 'Timeline'], as_index=False)['Cantidad'].sum()
    if df_daily.empty: return None, 0, 0
        
    full_range = pd.date_range(start=df_daily['Timeline'].min(), end=df_daily['Timeline'].max(), freq='D')
    demand = df_daily[df_daily['Tipo'] == 'Salida Almacén'].set_index('Timeline').reindex(full_range).fillna(0)
    restock = df_daily[df_daily['Tipo'] == 'Colocación Carro'].set_index('Timeline').reindex(full_range).fillna(0)
    
    cumulative_stock = (restock['Cantidad'] - demand['Cantidad']).cumsum()
    initial_stock = abs(cumulative_stock.min()) if cumulative_stock.min() < 0 else 0
    current_stock_level = initial_stock + cumulative_stock
    
    last_date = current_stock_level.index[-1]
    current_stock_val = current_stock_level.iloc[-1]
    
    # Calculate Burn Rate (Average daily demand over last 30 days)
    recent_start = last_date - DateOffset(days=30)
    burn_rate = demand.loc[recent_start:last_date, 'Cantidad'].mean() if recent_start in demand.index else 0

    forecast_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=forecast_days, freq='D')
    predicted_demand = []

    last_year_start, last_year_end = recent_start - DateOffset(years=1), last_date - DateOffset(years=1)
    vol_recent = burn_rate
    vol_last_year = demand.loc[last_year_start:last_year_end, 'Cantidad'].mean() if last_year_start in demand.index else 0
    trend_delta = 0 if pd.isna(vol_recent - vol_last_year) else (vol_recent - vol_last_year)

    for future_date in forecast_dates:
        date_last_year_now = future_date - DateOffset(years=1)
        base_value = demand.loc[date_last_year_now, 'Cantidad'] if date_last_year_now in demand.index else 0
        predicted_demand.append(max(0, base_value + trend_delta))

    future_stock_series = current_stock_val - pd.Series(predicted_demand, index=forecast_dates).cumsum()
    zero_crossings = future_stock_series[future_stock_series <= 0]
    
    return zero_crossings.index[0] if not zero_crossings.empty else None, current_stock_val, burn_rate

def create_plotly_forecast(item_df, item_id, forecast_days=30):
    stockout_date, current_stock_val, burn_rate = predict_stockout_for_item(item_df, forecast_days)
    
    # Rebuilding series for plot (duplicating light logic here for rendering)
    df_daily = item_df.groupby(['Tipo', 'Timeline'], as_index=False)['Cantidad'].sum()
    full_range = pd.date_range(start=df_daily['Timeline'].min(), end=df_daily['Timeline'].max(), freq='D')
    demand = df_daily[df_daily['Tipo'] == 'Salida Almacén'].set_index('Timeline').reindex(full_range).fillna(0)
    restock = df_daily[df_daily['Tipo'] == 'Colocación Carro'].set_index('Timeline').reindex(full_range).fillna(0)
    cumulative_stock = (restock['Cantidad'] - demand['Cantidad']).cumsum()
    current_stock_level = (abs(cumulative_stock.min()) if cumulative_stock.min() < 0 else 0) + cumulative_stock
    last_date = current_stock_level.index[-1]

    forecast_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=forecast_days, freq='D')
    predicted_demand = []
    
    recent_start = last_date - DateOffset(days=30)
    last_year_start = recent_start - DateOffset(years=1)
    vol_recent = demand.loc[recent_start:last_date, 'Cantidad'].mean() if recent_start in demand.index else 0
    vol_last_year = demand.loc[last_year_start:last_date - DateOffset(years=1), 'Cantidad'].mean() if last_year_start in demand.index else 0
    trend_delta = 0 if pd.isna(vol_recent - vol_last_year) else (vol_recent - vol_last_year)

    for future_date in forecast_dates:
        date_last_year_now = future_date - DateOffset(years=1)
        base_value = demand.loc[date_last_year_now, 'Cantidad'] if date_last_year_now in demand.index else 0
        predicted_demand.append(max(0, base_value + trend_delta))

    future_stock_series = current_stock_val - pd.Series(predicted_demand, index=forecast_dates).cumsum()

    # --- ENHANCED PLOTLY GRAPHIC ---
    fig = go.Figure()
    plot_start = last_date - pd.Timedelta(days=90)
    history_to_plot = current_stock_level.loc[plot_start:]
    
    # Solid area for history
    fig.add_trace(go.Scatter(
        x=history_to_plot.index, y=history_to_plot.values, 
        mode='lines', name='Histórico', 
        line=dict(color="#626F7C", width=4, shape='hv'),
        fill='tozeroy', fillcolor='rgba(46, 64, 83, 0.1)'
    ))
    
    # Dashed area for forecast
    fig.add_trace(go.Scatter(
        x=future_stock_series.index, y=future_stock_series.values, 
        mode='lines', name='Predicho', 
        line=dict(color="#E78F3C", width=4, dash='dash'),
    ))
    
    fig.add_hline(y=0, line_width=2, line_dash="solid", line_color="#E74C3C")

    fig.update_layout(
        title=f'<b>{item_id}</b>: Inventory Burn Down',
        xaxis_title='',
        yaxis_title='Units in Stock',
        hovermode="x unified",
        template="plotly_white",
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig, current_stock_val, stockout_date, burn_rate


# --- UI LAYOUT ---
st.title("📦 Warehouse Forecaster")
st.markdown("Predictive inventory depletion based on historical demand trends.")

df = load_data()
items = sorted(df['Referencia'].unique())

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
        
        results = []
        total_items = len(items)
        
        for i, item_id in enumerate(items):
            stockout_date, current_stock, burn_rate = predict_stockout_for_item(df[df['Referencia'] == item_id], forecast_window)
            
            days_left = (stockout_date - pd.Timestamp.today().normalize()).days if stockout_date else forecast_window
            
            results.append({
                'Referencia': item_id,
                'Current Stock': current_stock,
                'Daily Burn Rate': burn_rate,
                'Est. Stockout': stockout_date.strftime("%Y-%m-%d") if stockout_date else "Safe",
                'Safety Margin': days_left
            })
                
            if i % 50 == 0 or i == total_items - 1:
                progress_bar.progress((i + 1) / total_items)
                status_text.text(f"Crunching data: {i + 1} / {total_items}...")

        progress_bar.empty()
        status_text.empty()
        
        report_df = pd.DataFrame(results).sort_values(by=['Safety Margin', 'Current Stock']).head(top_n)
        styled_df = report_df.style.background_gradient(
            subset=['Safety Margin'], 
            cmap='RdYlGn',  # RdYlGn = Red to Yellow to Green
            vmin=0, 
            vmax=forecast_window
        ).format({
            "Current Stock": "{:.0f} units",
            "Daily Burn Rate": "{:.1f} / day",
            "Safety Margin": "{:.0f} days"
        })
        
        # --- PRETTY DATAFRAME CONFIG ---
        st.dataframe(
            styled_df,
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
        item_df = df[df['Referencia'] == selected_item]
        fig, current_stock, stockout_date, burn_rate = create_plotly_forecast(item_df, selected_item, forecast_window)
        
        if fig:
            # --- KPI ROW ---
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