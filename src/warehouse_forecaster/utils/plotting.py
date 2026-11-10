"""Plotly (app) and matplotlib (notebook) visualizations.

Plotting libraries are imported lazily so the core package only needs pandas.
"""

import pandas as pd

from warehouse_forecaster.constants import COL_QTY, COL_TYPE, DEMAND, RESTOCK
from warehouse_forecaster.models.forecast import run_forecast

HISTORY_DAYS_SHOWN = 90


# --- Plotly (Streamlit app) -------------------------------------------------

def create_plotly_forecast(item_df: pd.DataFrame, item_id, forecast_days: int = 30):
    """Burn-down chart of the last 90 days of stock plus the forecast.

    Returns ``(fig, current_stock, stockout_date, burn_rate)``.
    """
    import plotly.graph_objects as go

    result = run_forecast(item_df, forecast_days)
    last_date = result.stock_history.index[-1]

    fig = go.Figure()
    plot_start = last_date - pd.Timedelta(days=HISTORY_DAYS_SHOWN)
    history_to_plot = result.stock_history.loc[plot_start:]

    fig.add_trace(go.Scatter(
        x=history_to_plot.index, y=history_to_plot.values,
        mode='lines', name='Histórico',
        line=dict(color="#626F7C", width=4, shape='hv'),
        fill='tozeroy', fillcolor='rgba(46, 64, 83, 0.1)'
    ))
    fig.add_trace(go.Scatter(
        x=result.stock_forecast.index, y=result.stock_forecast.values,
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
    return fig, result.current_stock, result.stockout_date, result.burn_rate


def style_alert_table(report_df: pd.DataFrame, forecast_days: int):
    """Red-to-green Safety Margin gradient and unit formatting for the alert table."""
    return report_df.style.background_gradient(
        subset=['Safety Margin'], cmap='RdYlGn', vmin=0, vmax=forecast_days
    ).format({
        "Current Stock": "{:.0f} units",
        "Daily Burn Rate": "{:.1f} / day",
        "Safety Margin": "{:.0f} days",
    })


# --- Matplotlib (notebooks) ---------------------------------------------------

def plot_quantities(df_long: pd.DataFrame, timeline_col: str, title: str, xlabel: str,
                    marker: str = '.', linestyle: str = '-'):
    """Line plot of quantity per movement type over time (long-format input)."""
    import matplotlib.pyplot as plt

    plt.figure(figsize=(14, 6))
    for tipo in df_long[COL_TYPE].unique():
        subset = df_long[df_long[COL_TYPE] == tipo]
        plt.plot(subset[timeline_col], subset[COL_QTY], label=tipo, marker=marker, linestyle=linestyle)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel('Total Quantity')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


def plot_stock_levels(df_pivot: pd.DataFrame, initial_stock, aggregate: str = "day"):
    """Step plot of reconstructed stock with inflow/outflow bars."""
    import matplotlib.pyplot as plt

    plt.figure(figsize=(14, 7))
    plt.step(df_pivot.index, df_pivot['Stock_Level'], where='post',
             label=f'Stock (Initial: {initial_stock})', color='black', linewidth=2)
    if RESTOCK in df_pivot.columns:
        plt.bar(df_pivot.index, df_pivot[RESTOCK], alpha=0.2, color='green', label='Inflow')
    if DEMAND in df_pivot.columns:
        plt.bar(df_pivot.index, -df_pivot[DEMAND], alpha=0.2, color='red', label='Outflow')
    plt.title(f'Inventory Levels (Min-Zero Normalized) - By {aggregate.capitalize()}')
    plt.axhline(0, color='red', linestyle='--', alpha=0.3, label='Zero Floor')
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


def plot_forecast(result, title: str = None):
    """History (last 90 days) and projected stock with the stockout date marked."""
    import matplotlib.pyplot as plt

    last_date = result.stock_history.index[-1]
    plt.figure(figsize=(14, 7))
    plot_start = last_date - pd.Timedelta(days=HISTORY_DAYS_SHOWN)
    plt.plot(result.stock_history.loc[plot_start:], label='Historical Stock', color='black', linewidth=2)
    plt.plot(result.stock_forecast, label='Predicted Stock', color='red', linestyle='--', linewidth=2)
    if result.stockout_date is not None:
        plt.axvline(result.stockout_date, color='orange', linestyle=':', linewidth=2)
        plt.text(result.stockout_date, plt.ylim()[1] * 0.5,
                 f' Stockout\n {result.stockout_date.strftime("%Y-%m-%d")}', color='orange', ha='right')
    plt.title(title or f'Stock Forecast (Next {len(result.stock_forecast)} Days)')
    plt.xlabel('Date')
    plt.ylabel('Stock Level')
    plt.axhline(0, color='grey', linewidth=0.8)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.show()
