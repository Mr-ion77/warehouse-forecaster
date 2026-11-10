"""Shared fixtures for the legacy-vs-refactor equivalence suite."""

import ast
import json
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
LEGACY = REPO / "legacy_reference"
DATA = REPO / "data"

ATOL = RTOL = 1e-6

# name -> (n_comparisons, max |legacy - refactored|, description of inputs)
RESULTS = {}


def record(name, diff, inputs):
    n, worst, _ = RESULTS.get(name, (0, 0.0, inputs))
    RESULTS[name] = (n + 1, max(worst, float(diff)), inputs)


def pytest_terminal_summary(terminalreporter):
    if not RESULTS:
        return
    tr = terminalreporter
    tr.section("Equivalence report: max |legacy - refactored|")
    w = max(len(k) for k in RESULTS)
    for name, (n, worst, inputs) in sorted(RESULTS.items()):
        tr.write_line(f"{name:<{w}}  checks={n:<5d} max_abs_diff={worst:.3e}  inputs: {inputs}")


# --- isolated legacy loading -------------------------------------------------

def _exec_defs(source: str, filename: str, run_all: bool = False) -> dict:
    """Execute only imports and def/class statements (or everything) in a fresh namespace.

    Nothing is registered in ``sys.modules``, so legacy names (``data``, ``app``)
    can never shadow the refactored package.
    """
    tree = ast.parse(source, filename=filename)
    if not run_all:
        tree.body = [n for n in tree.body
                     if isinstance(n, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.ClassDef))]
    ns = {"__name__": f"legacy::{filename}"}
    exec(compile(tree, filename, "exec"), ns)
    return ns


def legacy_notebook_cells():
    nb = json.loads((LEGACY / "Linees_Pare.ipynb").read_text(encoding="utf-8"))
    return ["".join(c["source"]) for c in nb["cells"]]


@pytest.fixture(scope="session")
def legacy_app():
    return _exec_defs((LEGACY / "app.py").read_text(encoding="utf-8"), "legacy_app.py")


@pytest.fixture(scope="session")
def legacy_data_module():
    return _exec_defs((LEGACY / "data.py").read_text(encoding="utf-8"), "legacy_data.py")


@pytest.fixture(scope="session")
def legacy_nb():
    """Function definitions from the legacy notebook (cells 4, 7 and 8)."""
    cells = legacy_notebook_cells()
    return {
        "cell4": _exec_defs(cells[4], "nb_cell4"),
        "cell8": _exec_defs(cells[8], "nb_cell8"),
    }


def run_legacy_cell(idx: int, cwd: Path) -> dict:
    """Run a whole legacy notebook cell (script-style) inside ``cwd``."""
    src = legacy_notebook_cells()[idx]
    old = os.getcwd()
    os.chdir(cwd)
    try:
        return _exec_defs(src, f"nb_cell{idx}", run_all=True)
    finally:
        os.chdir(old)
        plt.close("all")


@pytest.fixture(autouse=True)
def _no_show(monkeypatch):
    monkeypatch.setattr(plt, "show", lambda *a, **k: None)
    yield
    plt.close("all")


# --- inputs -------------------------------------------------------------------

@pytest.fixture(scope="session")
def xls_workdir(tmp_path_factory):
    """Temp dir holding the real sample export under its original name."""
    d = tmp_path_factory.mktemp("xls")
    (d / "ensaladilla.xls").symlink_to(DATA / "ensaladilla.xls")
    return d


@pytest.fixture(scope="session")
def real_xls():
    return pd.read_excel(DATA / "ensaladilla.xls")


@pytest.fixture(scope="session")
def synthetic_subset():
    """Deterministic 40-item slice of the committed synthetic dataset (raw, uncleaned)."""
    df = pd.read_csv(DATA / "synthetic_inventory.csv", sep=";")
    items = sorted(df["Referencia"].unique())
    rng = np.random.RandomState(42)
    chosen = sorted(set(items[:10]) | set(rng.choice(items, 30, replace=False)))
    return df[df["Referencia"].isin(chosen)].reset_index(drop=True)


@pytest.fixture(scope="session")
def csv_datasets(tmp_path_factory, synthetic_subset, real_xls, legacy_data_module):
    """Named ``;``-CSV files covering several input shapes and edge cases."""
    d = tmp_path_factory.mktemp("csv")
    out = {}

    p = d / "synthetic_subset.csv"
    synthetic_subset.to_csv(p, sep=";", index=False)
    out["synthetic_subset(40 items, 730d)"] = p

    # Real export: decimal-comma strings, dd/mm/yyyy hh:mm:ss dates, extra movement types
    p = d / "real_export.csv"
    real_xls.to_csv(p, sep=";", index=False)
    out["real_export(ensaladilla, 1 item)"] = p

    gen = legacy_data_module["generate_synthetic_warehouse_data"]
    for n_items, days in [(15, 400), (12, 200), (8, 31)]:  # >1y, <1y and ~1 month history
        np.random.seed(42)
        p = d / f"gen_{n_items}_{days}.csv"
        gen(num_items=n_items, days=days, output_file=str(p))
        out[f"generated({n_items} items, {days}d)"] = p
    return out
