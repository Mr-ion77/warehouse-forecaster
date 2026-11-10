"""Loading and cleaning raw warehouse movement exports."""

import pandas as pd

from warehouse_forecaster.constants import COL_DATE, COL_QTY, COL_TIMELINE

def clean_quantities(df: pd.DataFrame) -> pd.DataFrame:
    """Convert European decimal-comma quantities ("2,00") to float, in place."""
    if df[COL_QTY].dtype == "object":
        df[COL_QTY] = df[COL_QTY].str.replace(",", ".").astype(float)
    return df


def parse_dates(df: pd.DataFrame, dayfirst: bool = False, date_format=None) -> pd.DataFrame:
    """Parse the ``Fecha proceso`` column to datetimes, in place.

    ``date_format=None`` is pandas' own default (format inference).
    """
    df[COL_DATE] = pd.to_datetime(df[COL_DATE], format=date_format, dayfirst=dayfirst)
    return df


def clean_movements(df: pd.DataFrame, dayfirst: bool = False, date_format=None,
                    add_daily_timeline: bool = True) -> pd.DataFrame:
    """Clean quantities, parse dates and (optionally) add a daily ``Timeline`` column."""
    clean_quantities(df)
    parse_dates(df, dayfirst=dayfirst, date_format=date_format)
    if add_daily_timeline:
        df[COL_TIMELINE] = df[COL_DATE].dt.normalize()
    return df


def load_inventory_csv(path, dayfirst: bool = True, date_format="mixed") -> pd.DataFrame:
    """Load a ``;``-separated inventory CSV ready for forecasting.

    Defaults match the Streamlit app (``format='mixed', dayfirst=True``).
    The notebook alert report historically used ``dayfirst=False`` with no format.
    """
    df = pd.read_csv(path, sep=";")
    return clean_movements(df, dayfirst=dayfirst, date_format=date_format)


def load_movements_excel(path) -> pd.DataFrame:
    """Load a raw Excel export (e.g. ``ensaladilla.xls``) without any cleaning."""
    return pd.read_excel(path)
