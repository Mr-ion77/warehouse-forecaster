"""Time aggregation of movements and min-zero stock level reconstruction."""

import pandas as pd

from warehouse_forecaster.constants import COL_DATE, COL_QTY, COL_TIMELINE, COL_TYPE, DEMAND, RESTOCK

FREQ_MAP = {"hour": "h", "day": "D", "week": "W", "month": "MS"}
DEFAULT_TYPES = (DEMAND, RESTOCK)


def resolve_freq(aggregate: str) -> str:
    """Map a human aggregation name ('hour', 'day', 'week', 'month') to a pandas freq."""
    return FREQ_MAP.get(aggregate.lower(), "D")


def add_period_timeline(df: pd.DataFrame, freq: str, column: str = COL_TIMELINE) -> pd.DataFrame:
    """Add a period-start timestamp column (floor for hours, period start otherwise)."""
    if freq == "h":
        df[column] = df[COL_DATE].dt.floor(freq)
    else:
        df[column] = df[COL_DATE].dt.to_period(freq).dt.to_timestamp()
    return df


def aggregate_by_date_and_hour(df: pd.DataFrame):
    """Sum quantities per (Tipo, date, hour) and per (Tipo, date).

    Adds ``Fecha`` and ``Hora_Slot`` helper columns to ``df`` in place.
    Returns ``(df_aggregated_hour, df_aggregated_day)``.
    """
    df["Fecha"] = df[COL_DATE].dt.date
    df["Hora_Slot"] = df[COL_DATE].dt.hour
    by_hour = df.groupby([COL_TYPE, "Fecha", "Hora_Slot"], as_index=False)[COL_QTY].sum()
    by_hour = by_hour.sort_values(by=["Fecha", "Hora_Slot"])
    by_day = by_hour.groupby([COL_TYPE, "Fecha"], as_index=False)[COL_QTY].sum().sort_values(by=["Fecha"])
    return by_hour, by_day


def fill_movement_gaps(df: pd.DataFrame, freq: str, tipos=DEFAULT_TYPES,
                       timeline_col: str = COL_TIMELINE) -> pd.DataFrame:
    """Aggregate by (Tipo, timeline) and reindex every type onto a full, gap-free range.

    ``df`` must already contain ``timeline_col``. Returns a long dataframe with
    columns ``[timeline_col, Tipo, Cantidad]`` where missing periods are 0.
    """
    raw = df.groupby([COL_TYPE, timeline_col], as_index=False)[COL_QTY].sum()
    full_range = pd.date_range(start=raw[timeline_col].min(), end=raw[timeline_col].max(), freq=freq)

    parts = []
    for tipo in tipos:
        subset = raw[raw[COL_TYPE] == tipo].set_index(timeline_col)
        subset = subset.reindex(full_range).fillna(0)
        subset[COL_TYPE] = tipo
        parts.append(subset.reset_index().rename(columns={"index": timeline_col}))
    return pd.concat(parts)


def filter_window(df: pd.DataFrame, start, end, column: str = COL_TIMELINE) -> pd.DataFrame:
    """Keep rows whose ``column`` lies in ``[start, end]``."""
    mask = (df[column] >= start) & (df[column] <= end)
    return df.loc[mask]


def compute_stock_table(df: pd.DataFrame, aggregate: str = "day", time_window=None,
                        info=DEFAULT_TYPES, initial_stock=None, verbose: bool = True):
    """Pivot movements per period and reconstruct the stock level.

    ``df`` must be cleaned (quantities numeric, dates parsed). If ``initial_stock``
    is None it is chosen so that the lowest stock level is exactly zero.
    Returns ``(df_pivot, initial_stock)`` where ``df_pivot`` has one column per
    movement type plus ``Stock_Level``.
    """
    freq = resolve_freq(aggregate)
    add_period_timeline(df, freq)
    df_final = fill_movement_gaps(df, freq, tipos=info)

    df_pivot = df_final.pivot(index=COL_TIMELINE, columns=COL_TYPE, values=COL_QTY).fillna(0)
    net_movement = df_pivot.get(RESTOCK, 0) - df_pivot.get(DEMAND, 0)
    cumulative_changes = net_movement.cumsum()

    if initial_stock is None:
        min_point = cumulative_changes.min()
        initial_stock = abs(min_point) if min_point < 0 else 0
        if verbose:
            print(f"Auto-calculated Initial Stock: {initial_stock}")

    df_pivot["Stock_Level"] = initial_stock + cumulative_changes

    if time_window:
        start_date, end_date = pd.to_datetime(time_window[0]), pd.to_datetime(time_window[1])
        df_pivot = df_pivot.loc[start_date:end_date]

    return df_pivot, initial_stock
