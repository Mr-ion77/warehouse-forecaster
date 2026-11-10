# Warehouse Forecaster

A Streamlit dashboard that reconstructs per-item warehouse stock levels from movement
logs and predicts when each item will run out.

## How the forecast works

For each item, movements are aggregated per day:

- **Demand** = `Salida Almacén` (warehouse outflow)
- **Restock** = `Colocación Carro` (inflow)

Stock is the cumulative net movement, shifted up so the lowest level in the history is
exactly zero. That is a min-zero baseline, because the exports carry no opening balance.
Future daily demand is

```
max(0, demand[same day last year] + trend_delta)
trend_delta = mean(demand, last 30 days) − mean(demand, same 30 days last year)
```

Projected stock is current stock minus cumulative predicted demand. The first day it hits ≤ 0
is the estimated stockout date.

## Layout

```
├── data/                     synthetic_inventory.csv (demo dataset), ensaladilla.xls (real sample export)
├── notebooks/exploration.ipynb   EDA and visualizations built on the package
├── scripts/
│   ├── streamlit_app.py      the dashboard
│   ├── generate_synthetic_data.py
│   └── stockout_report.py    CLI alert report
├── src/warehouse_forecaster/
│   ├── constants.py          column names, movement types, default paths
│   ├── data/io.py            loading & cleaning (decimal commas, dates)
│   ├── data/aggregation.py   hourly/daily/weekly aggregation, stock table
│   ├── data/synthetic.py     synthetic data generator
│   ├── models/forecast.py    the stockout forecaster (single source of truth)
│   ├── models/alerts.py      bulk alert tables
│   └── utils/plotting.py     plotly (app) and matplotlib (notebook) charts
```

## Usage

```bash
pip install -e ".[dev]"
streamlit run scripts/streamlit_app.py          # dashboard on :8501
python scripts/stockout_report.py --days 30     # text alert report
python scripts/generate_synthetic_data.py --seed 42
```

Run commands from the repository root: data paths are relative to it. You can override the
app's dataset with `WAREHOUSE_DATA_PATH=/path/to/file.csv`.

### Docker / Cloud Run

```bash
docker build -t warehouse-forecaster .
docker run -p 8080:8080 warehouse-forecaster
```

## Input format

A `;`-separated CSV (or Excel export) with columns
`Referencia; Descripción; Tipo; Cantidad; Fecha proceso`. Quantities may use decimal commas (`2,00`).

> Requires **pandas 2.x**. Under pandas 3 the text-column dtype changes and the decimal-comma
> cleaning step is silently skipped.
