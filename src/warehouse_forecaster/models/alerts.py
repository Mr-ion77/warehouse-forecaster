"""Bulk stockout alert reports across all items."""

from typing import Callable, Optional

import pandas as pd

from warehouse_forecaster.constants import COL_ITEM
from warehouse_forecaster.models.forecast import predict_stockout_for_item


def build_alert_table(df: pd.DataFrame, forecast_days: int = 30, items=None,
                      today: Optional[pd.Timestamp] = None,
                      progress: Optional[Callable[[int, int], None]] = None) -> pd.DataFrame:
    """Forecast every item and return the dashboard table, most urgent first.

    Columns: Referencia, Current Stock, Daily Burn Rate, Est. Stockout, Safety Margin.
    ``Safety Margin`` is days from ``today`` to stockout (``forecast_days`` when safe).
    ``progress(done, total)`` is called every 50 items and at the end.
    """
    if items is None:
        items = sorted(df[COL_ITEM].unique())
    if today is None:
        today = pd.Timestamp.today().normalize()

    results = []
    total_items = len(items)
    for i, item_id in enumerate(items):
        stockout_date, current_stock, burn_rate = predict_stockout_for_item(df[df[COL_ITEM] == item_id], forecast_days)
        days_left = (stockout_date - today).days if stockout_date else forecast_days
        results.append({
            'Referencia': item_id,
            'Current Stock': current_stock,
            'Daily Burn Rate': burn_rate,
            'Est. Stockout': stockout_date.strftime("%Y-%m-%d") if stockout_date else "Safe",
            'Safety Margin': days_left,
        })
        if progress is not None and (i % 50 == 0 or i == total_items - 1):
            progress(i + 1, total_items)

    return pd.DataFrame(results).sort_values(by=['Safety Margin', 'Current Stock'])


def generate_alert_report(df: pd.DataFrame, forecast_days: int = 30, verbose: bool = True) -> pd.DataFrame:
    """Items predicted to stock out within the horizon, sorted by stockout date.

    Columns: Referencia, Current_Stock, Est_Stockout_Date. Items are visited in
    order of first appearance.
    """
    results = []
    unique_items = df[COL_ITEM].unique()
    total_items = len(unique_items)
    if verbose:
        print(f"Analyzing {total_items} items...")

    for i, item_id in enumerate(unique_items):
        if verbose and i % 500 == 0 and i > 0:
            print(f"Processed {i}/{total_items}...")
        stockout_date, current_stock, _ = predict_stockout_for_item(df[df[COL_ITEM] == item_id], forecast_days)
        results.append({
            'Referencia': item_id,
            'Current_Stock': current_stock,
            'Est_Stockout_Date': stockout_date,
        })

    report_df = pd.DataFrame(results)
    urgent_df = report_df.dropna(subset=['Est_Stockout_Date']).sort_values('Est_Stockout_Date')

    if verbose:
        if urgent_df.empty:
            print("No stockouts predicted in the next 30 days.")
        else:
            print("\n--- ACTION REQUIRED: STOCKOUT ALERTS ---")
            print(urgent_df.head(15).to_string(index=False))
    return urgent_df
