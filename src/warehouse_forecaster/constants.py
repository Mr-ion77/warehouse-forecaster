"""Shared column names and movement types used across the package."""

from pathlib import Path

# Movement types ("Tipo" column)
DEMAND = "Salida Almacén"      # outflow from the warehouse
RESTOCK = "Colocación Carro"   # inflow / replenishment

# Column names
COL_ITEM = "Referencia"
COL_TYPE = "Tipo"
COL_QTY = "Cantidad"
COL_DATE = "Fecha proceso"
COL_TIMELINE = "Timeline"

# Repository-relative data locations (resolved against the current working directory)
DATA_DIR = Path("data")
DEFAULT_INVENTORY_CSV = DATA_DIR / "synthetic_inventory.csv"
DEFAULT_MOVEMENTS_XLS = DATA_DIR / "ensaladilla.xls"
