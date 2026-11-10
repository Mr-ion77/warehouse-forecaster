"""Legacy (``legacy_reference/``) vs refactored (``warehouse_forecaster``) equivalence.

Every check asserts max |legacy - refactored| <= 1e-6 (and exact equality for
dates, labels and indexes).
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from conftest import ATOL, RTOL, record, run_legacy_cell

from warehouse_forecaster.data import aggregation, io, synthetic
from warehouse_forecaster.models import alerts, forecast
from warehouse_forecaster.utils import plotting

HORIZONS = [7, 30, 90]


# --- helpers -----------------------------------------------------------------

def max_frame_diff(a: pd.DataFrame, b: pd.DataFrame) -> float:
    """Assert identical structure; return max abs diff over numeric columns."""
    assert list(a.columns) == list(b.columns)
    pd.testing.assert_index_equal(a.index, b.index)
    worst = 0.0
    for col in a.columns:
        x, y = a[col], b[col]
        if pd.api.types.is_numeric_dtype(x) and pd.api.types.is_numeric_dtype(y):
            xv, yv = x.to_numpy(float), y.to_numpy(float)
            assert np.allclose(xv, yv, atol=ATOL, rtol=RTOL, equal_nan=True), col
            if len(xv):
                worst = max(worst, float(np.nanmax(np.abs(xv - yv))) if not np.all(np.isnan(xv)) else 0.0)
        else:
            assert x.astype(str).tolist() == y.astype(str).tolist(), col
    return worst


def num_diff(a, b) -> float:
    a, b = float(a), float(b)
    assert np.allclose(a, b, atol=ATOL, rtol=RTOL, equal_nan=True)
    return 0.0 if (np.isnan(a) and np.isnan(b)) else abs(a - b)


def app_loaded(path: Path, legacy_app, tmp_path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load ``path`` through the legacy app's hard-coded loader and the refactored loader."""
    (tmp_path / "synthetic_inventory.csv").write_bytes(path.read_bytes())
    old = os.getcwd()
    os.chdir(tmp_path)
    try:
        legacy_df = legacy_app["load_data"].__wrapped__()
    finally:
        os.chdir(old)
    return legacy_df, io.load_inventory_csv(path)


# --- data loading ----------------------------------------------------------

def test_load_data(csv_datasets, legacy_app, tmp_path):
    for name, path in csv_datasets.items():
        legacy_df, new_df = app_loaded(path, legacy_app, tmp_path)
        record("io.load_inventory_csv vs app.load_data", max_frame_diff(legacy_df, new_df),
               "5 CSVs: synthetic slice, real export, generated 31/200/400 days")


# --- core forecaster -----------------------------------------------------------

@pytest.mark.parametrize("horizon", HORIZONS)
def test_predict_stockout_app(csv_datasets, legacy_app, tmp_path, horizon):
    legacy_fn = legacy_app["predict_stockout_for_item"]
    for name, path in csv_datasets.items():
        legacy_df, new_df = app_loaded(path, legacy_app, tmp_path)
        for item in sorted(legacy_df["Referencia"].unique()):
            l_date, l_stock, l_burn = legacy_fn(legacy_df[legacy_df["Referencia"] == item], horizon)
            n_date, n_stock, n_burn = forecast.predict_stockout_for_item(new_df[new_df["Referencia"] == item], horizon)
            assert l_date == n_date, (name, item)
            d = max(num_diff(l_stock, n_stock), num_diff(l_burn, n_burn))
            record("forecast.predict_stockout_for_item vs app", d,
                   "every item of 5 datasets x horizons 7/30/90")


def test_predict_stockout_empty(legacy_app):
    empty = pd.DataFrame({"Tipo": pd.Series(dtype=str), "Timeline": pd.Series(dtype="datetime64[ns]"),
                          "Cantidad": pd.Series(dtype=float)})
    assert legacy_app["predict_stockout_for_item"](empty) == forecast.predict_stockout_for_item(empty)
    record("forecast.predict_stockout_for_item (empty input)", 0.0, "zero-row frame")


def test_predict_stockout_notebook(csv_datasets, legacy_nb):
    """Notebook cell 8 variant returned (date, stock); refactor returns a superset."""
    legacy_fn = legacy_nb["cell8"]["predict_stockout_for_item"]
    for name, path in csv_datasets.items():
        df = io.clean_movements(pd.read_csv(path, sep=";"), dayfirst=False)
        for item in df["Referencia"].unique():
            sub = df[df["Referencia"] == item]
            for horizon in HORIZONS:
                l_date, l_stock = legacy_fn(sub, horizon)
                n_date, n_stock, _ = forecast.predict_stockout_for_item(sub, horizon)
                assert l_date == n_date
                record("forecast.predict_stockout_for_item vs notebook cell 8",
                       num_diff(l_stock, n_stock), "every item of 5 datasets x horizons 7/30/90")


def test_plotly_forecast(csv_datasets, legacy_app, tmp_path):
    legacy_fn = legacy_app["create_plotly_forecast"]
    for name, path in csv_datasets.items():
        legacy_df, new_df = app_loaded(path, legacy_app, tmp_path)
        for item in sorted(legacy_df["Referencia"].unique())[:8]:
            for horizon in (7, 30):
                lf, ls, ld, lb = legacy_fn(legacy_df[legacy_df["Referencia"] == item], item, horizon)
                nf, ns, nd, nb = plotting.create_plotly_forecast(new_df[new_df["Referencia"] == item], item, horizon)
                assert ld == nd
                d = max(num_diff(ls, ns), num_diff(lb, nb))
                assert lf.layout.to_plotly_json() == nf.layout.to_plotly_json()
                assert len(lf.data) == len(nf.data)
                for lt, nt in zip(lf.data, nf.data):
                    strip = lambda t: {k: v for k, v in t.to_plotly_json().items() if k not in ("x", "y")}
                    assert strip(lt) == strip(nt)
                    assert list(pd.to_datetime(lt.x)) == list(pd.to_datetime(nt.x))
                    ly, ny = np.asarray(lt.y, float), np.asarray(nt.y, float)
                    assert np.allclose(ly, ny, atol=ATOL, rtol=RTOL)
                    d = max(d, float(np.max(np.abs(ly - ny))) if len(ly) else 0.0)
                record("plotting.create_plotly_forecast vs app", d,
                       "8 items/dataset x horizons 7/30, full figure dict")


# --- alert reports -----------------------------------------------------------

def test_generate_alert_report(csv_datasets, legacy_nb, capsys):
    legacy_fn = legacy_nb["cell8"]["generate_alert_report"]
    for name, path in csv_datasets.items():
        for horizon in (30, 90):
            l = legacy_fn(str(path), forecast_days=horizon)
            n = alerts.generate_alert_report(io.clean_movements(pd.read_csv(path, sep=";"), dayfirst=False),
                                             forecast_days=horizon)
            record("alerts.generate_alert_report vs notebook cell 8", max_frame_diff(l, n),
                   "5 datasets x horizons 30/90")


def _legacy_bulk_table(predict, df, items, forecast_window, today):
    """Verbatim body of the legacy app's 'Run Bulk Analysis' loop (minus Streamlit widgets)."""
    results = []
    for item_id in items:
        stockout_date, current_stock, burn_rate = predict(df[df['Referencia'] == item_id], forecast_window)
        days_left = (stockout_date - today).days if stockout_date else forecast_window
        results.append({
            'Referencia': item_id,
            'Current Stock': current_stock,
            'Daily Burn Rate': burn_rate,
            'Est. Stockout': stockout_date.strftime("%Y-%m-%d") if stockout_date else "Safe",
            'Safety Margin': days_left
        })
    return pd.DataFrame(results).sort_values(by=['Safety Margin', 'Current Stock'])


def test_bulk_alert_table(csv_datasets, legacy_app, tmp_path):
    today = pd.Timestamp.today().normalize()
    for name, path in csv_datasets.items():
        legacy_df, new_df = app_loaded(path, legacy_app, tmp_path)
        items = sorted(legacy_df["Referencia"].unique())
        for horizon in HORIZONS:
            l = _legacy_bulk_table(legacy_app["predict_stockout_for_item"], legacy_df, items, horizon, today)
            n = alerts.build_alert_table(new_df, horizon, items=items, today=today)
            record("alerts.build_alert_table vs app bulk loop", max_frame_diff(l, n),
                   "5 datasets x horizons 7/30/90")


# --- streamlit end-to-end ------------------------------------------------------

@pytest.fixture(scope="module")
def apptest_csv(csv_datasets):
    return csv_datasets["synthetic_subset(40 items, 730d)"]


def _run_apps(apptest_csv, tmp_path, monkeypatch, configure):
    from streamlit.testing.v1 import AppTest

    root = Path(__file__).resolve().parents[1]
    (tmp_path / "synthetic_inventory.csv").write_bytes(apptest_csv.read_bytes())
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("WAREHOUSE_DATA_PATH", str(apptest_csv))
    out = []
    for script in (root / "legacy_reference" / "app.py", root / "scripts" / "streamlit_app.py"):
        at = AppTest.from_file(str(script), default_timeout=300).run()
        assert not at.exception
        configure(at)
        assert not at.exception
        out.append(at)
    return out


def test_streamlit_bulk_dashboard(apptest_csv, tmp_path, monkeypatch):
    def configure(at):
        at.number_input[0].set_value(40).run()
        at.button[0].click().run()

    legacy, new = _run_apps(apptest_csv, tmp_path, monkeypatch, configure)
    l, n = legacy.dataframe[0].value, new.dataframe[0].value
    record("streamlit app: bulk dashboard table", max_frame_diff(l.reset_index(drop=True), n.reset_index(drop=True)),
           "AppTest, 40-item slice, top 40, horizon 30")


def test_streamlit_item_view(apptest_csv, tmp_path, monkeypatch):
    def configure(at):
        at.sidebar.radio[0].set_value("Individual Item Deep-Dive").run()
        at.sidebar.slider[0].set_value(60).run()

    legacy, new = _run_apps(apptest_csv, tmp_path, monkeypatch, configure)
    assert [(m.label, m.value, m.delta) for m in legacy.metric] == [(m.label, m.value, m.delta) for m in new.metric]
    l_spec = legacy.get("plotly_chart")[0].proto.spec
    n_spec = new.get("plotly_chart")[0].proto.spec
    assert l_spec == n_spec
    record("streamlit app: item deep-dive (metrics + chart JSON)", 0.0, "AppTest, first item, horizon 60")


# --- notebook aggregation pipelines ----------------------------------------------

@pytest.mark.parametrize("aggregate", ["hour", "day", "week", "month"])
@pytest.mark.parametrize("time_window,initial_stock", [(None, None), (("2025-03-01", "2025-09-30"), None),
                                                       (None, 500)])
def test_stock_table(legacy_nb, xls_workdir, aggregate, time_window, initial_stock, capsys):
    legacy_fn = legacy_nb["cell4"]["process_and_plot_logistics"]
    df = io.clean_movements(io.load_movements_excel(xls_workdir / "ensaladilla.xls"), add_daily_timeline=False)
    old = os.getcwd()
    os.chdir(xls_workdir)
    try:
        if aggregate == "month":
            # Pre-existing bug kept on purpose: pandas >= 2.2 rejects 'MS' as a period
            # frequency. Both implementations must fail identically.
            with pytest.raises(ValueError, match="MS is not supported") as l_err:
                legacy_fn("ensaladilla.xls", aggregate=aggregate, time_window=time_window, initial_stock=initial_stock)
            with pytest.raises(ValueError) as n_err:
                aggregation.compute_stock_table(df, aggregate=aggregate, time_window=time_window,
                                                initial_stock=initial_stock)
            assert str(l_err.value) == str(n_err.value)
            record("aggregation.compute_stock_table vs notebook cell 4 (month: same ValueError)", 0.0,
                   "real export x month")
            return
        l = legacy_fn("ensaladilla.xls", aggregate=aggregate, time_window=time_window, initial_stock=initial_stock)
    finally:
        os.chdir(old)
    n, init = aggregation.compute_stock_table(df, aggregate=aggregate, time_window=time_window,
                                              initial_stock=initial_stock)
    aggregation_plot = plotting.plot_stock_levels(n, init, aggregate)  # must not raise
    assert aggregation_plot is None
    record("aggregation.compute_stock_table vs notebook cell 4", max_frame_diff(l, n),
           "real export x hour/day/week x {full, window, initial_stock=500}")


def test_hour_and_day_aggregates(xls_workdir, capsys):
    ns = run_legacy_cell(0, xls_workdir)
    df = io.load_movements_excel(xls_workdir / "ensaladilla.xls")
    io.clean_quantities(df)
    io.parse_dates(df, dayfirst=True)
    by_hour, by_day = aggregation.aggregate_by_date_and_hour(df)
    d = max(max_frame_diff(ns["df_aggregated_hour"], by_hour), max_frame_diff(ns["df_aggregated_day"], by_day))
    record("aggregation.aggregate_by_date_and_hour vs notebook cell 0", d, "real export")


@pytest.mark.parametrize("cell,freq,tipos,col,window", [
    (2, "h", ["Salida Almacén"], "Timeline", ("2025-01-01", "2025-02-01")),
    (3, "D", ["Salida Almacén", "Colocación Carro"], "Timeline_Day", ("2025-01-01", "2025-08-01")),
])
def test_gap_filled_series(xls_workdir, cell, freq, tipos, col, window):
    ns = run_legacy_cell(cell, xls_workdir)
    df = io.clean_movements(io.load_movements_excel(xls_workdir / "ensaladilla.xls"), add_daily_timeline=False)
    if freq == "h":
        aggregation.add_period_timeline(df, freq, column=col)
    else:
        df[col] = df["Fecha proceso"].dt.normalize()
    filled = aggregation.fill_movement_gaps(df, freq, tipos=tipos, timeline_col=col)
    filtered = aggregation.filter_window(filled, *window, column=col)
    legacy_full = ns["df_final"] if cell == 2 else ns["df_final_day"]
    legacy_filt = ns["df_filtered"] if cell == 2 else ns["df_filtered_day"]
    d = max(max_frame_diff(legacy_full, filled), max_frame_diff(legacy_filt, filtered))
    record(f"aggregation.fill_movement_gaps vs notebook cell {cell}", d, f"real export, freq={freq}")


# --- synthetic generator -------------------------------------------------------

@pytest.mark.parametrize("num_items,days", [(5, 30), (50, 365), (200, 730)])
def test_synthetic_generator(legacy_data_module, tmp_path, num_items, days, capsys):
    np.random.seed(42)
    l = legacy_data_module["generate_synthetic_warehouse_data"](num_items, days, str(tmp_path / "l.csv"))
    np.random.seed(42)
    n = synthetic.generate_synthetic_warehouse_data(num_items, days, str(tmp_path / "n.csv"))
    d = max_frame_diff(l, n)
    assert (tmp_path / "l.csv").read_bytes() == (tmp_path / "n.csv").read_bytes()
    record("synthetic.generate_synthetic_warehouse_data vs data.py", d,
           "seed 42 x (5,30)/(50,365)/(200,730) items/days, CSV byte-identical")
