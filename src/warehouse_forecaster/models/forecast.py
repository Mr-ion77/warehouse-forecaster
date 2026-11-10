"""Seasonal-naive-plus-trend stockout forecaster.

For each future day ``d`` the predicted demand is::

    max(0, demand[d - 1 year] + trend_delta)

where ``trend_delta`` = mean demand over the last 30 days minus the mean demand
over the same 30-day window one year earlier. Stock is reconstructed from the
movement history with a min-zero baseline, then depleted by cumulative
predicted demand; the first day stock reaches <= 0 is the stockout date.
"""

from dataclasses import dataclass
from typing import Optional

import pandas as pd
from pandas.tseries.offsets import DateOffset

from warehouse_forecaster.constants import COL_QTY, COL_TIMELINE, COL_TYPE, DEMAND, RESTOCK

TREND_WINDOW_DAYS = 30


@dataclass
class ForecastResult:
    stockout_date: Optional[pd.Timestamp]
    current_stock: float
    burn_rate: float
    trend_delta: float
    demand: pd.DataFrame            # daily demand, gap-filled
    restock: pd.DataFrame           # daily restock, gap-filled
    stock_history: pd.Series        # reconstructed daily stock level
    stock_forecast: pd.Series       # projected stock over the forecast horizon


def build_daily_movements(item_df: pd.DataFrame):
    """Return gap-filled daily ``(demand, restock)`` frames, or None if there is no data."""
    df_daily = item_df.groupby([COL_TYPE, COL_TIMELINE], as_index=False)[COL_QTY].sum()
    if df_daily.empty:
        return None
    full_range = pd.date_range(start=df_daily[COL_TIMELINE].min(), end=df_daily[COL_TIMELINE].max(), freq='D')
    demand = df_daily[df_daily[COL_TYPE] == DEMAND].set_index(COL_TIMELINE).reindex(full_range).fillna(0)
    restock = df_daily[df_daily[COL_TYPE] == RESTOCK].set_index(COL_TIMELINE).reindex(full_range).fillna(0)
    return demand, restock


def reconstruct_stock_level(demand: pd.DataFrame, restock: pd.DataFrame) -> pd.Series:
    """Cumulative net movement, shifted up so the minimum stock level is zero."""
    cumulative_stock = (restock[COL_QTY] - demand[COL_QTY]).cumsum()
    initial_stock = abs(cumulative_stock.min()) if cumulative_stock.min() < 0 else 0
    return initial_stock + cumulative_stock


def compute_burn_rate_and_trend(demand: pd.DataFrame, last_date: pd.Timestamp):
    """Return ``(burn_rate, trend_delta)``.

    ``burn_rate`` is the mean daily demand over the last 30 days (0 if history is
    shorter); ``trend_delta`` is ``burn_rate`` minus the same window one year ago
    (0 if undefined).
    """
    recent_start = last_date - DateOffset(days=TREND_WINDOW_DAYS)
    burn_rate = demand.loc[recent_start:last_date, COL_QTY].mean() if recent_start in demand.index else 0

    last_year_start, last_year_end = recent_start - DateOffset(years=1), last_date - DateOffset(years=1)
    vol_last_year = demand.loc[last_year_start:last_year_end, COL_QTY].mean() if last_year_start in demand.index else 0
    trend_delta = 0 if pd.isna(burn_rate - vol_last_year) else (burn_rate - vol_last_year)
    return burn_rate, trend_delta


def forecast_daily_demand(demand: pd.DataFrame, last_date: pd.Timestamp, trend_delta, forecast_days: int) -> pd.Series:
    """Predicted demand per future day: last year's same-day demand plus the trend, floored at 0."""
    forecast_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=forecast_days, freq='D')
    predicted_demand = []
    for future_date in forecast_dates:
        date_last_year_now = future_date - DateOffset(years=1)
        base_value = demand.loc[date_last_year_now, COL_QTY] if date_last_year_now in demand.index else 0
        predicted_demand.append(max(0, base_value + trend_delta))
    return pd.Series(predicted_demand, index=forecast_dates)


def first_stockout(stock_forecast: pd.Series):
    """First date at which projected stock is <= 0, or None."""
    zero_crossings = stock_forecast[stock_forecast <= 0]
    return zero_crossings.index[0] if not zero_crossings.empty else None


def run_forecast(item_df: pd.DataFrame, forecast_days: int = 30) -> Optional[ForecastResult]:
    """Full forecast for a single item's movements (needs a daily ``Timeline`` column)."""
    movements = build_daily_movements(item_df)
    if movements is None:
        return None
    demand, restock = movements

    stock_history = reconstruct_stock_level(demand, restock)
    last_date = stock_history.index[-1]
    current_stock = stock_history.iloc[-1]

    burn_rate, trend_delta = compute_burn_rate_and_trend(demand, last_date)
    predicted = forecast_daily_demand(demand, last_date, trend_delta, forecast_days)
    stock_forecast = current_stock - predicted.cumsum()

    return ForecastResult(
        stockout_date=first_stockout(stock_forecast),
        current_stock=current_stock,
        burn_rate=burn_rate,
        trend_delta=trend_delta,
        demand=demand,
        restock=restock,
        stock_history=stock_history,
        stock_forecast=stock_forecast,
    )


def predict_stockout_for_item(item_df: pd.DataFrame, forecast_days: int = 30):
    """Return ``(stockout_date, current_stock, burn_rate)``; ``(None, 0, 0)`` with no data."""
    result = run_forecast(item_df, forecast_days)
    if result is None:
        return None, 0, 0
    return result.stockout_date, result.current_stock, result.burn_rate
