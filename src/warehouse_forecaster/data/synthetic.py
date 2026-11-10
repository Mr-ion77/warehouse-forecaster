"""Synthetic warehouse movement generator (two-year timeline with a growth trend)."""

import numpy as np
import pandas as pd

from warehouse_forecaster.constants import DEFAULT_INVENTORY_CSV


def generate_synthetic_warehouse_data(num_items=2500, days=730, output_file=DEFAULT_INVENTORY_CSV):
    """Simulate sparse demand/restock events and save them as a ``;``-separated CSV.

    Pass ``output_file=None`` to skip writing to disk.
    """
    print(f"Generating synthetic data for {num_items} items over {days} days...")

    # 1. Items
    items = [f"ITEM_{str(i).zfill(4)}" for i in range(1, num_items + 1)]

    # 2. Timeline: last `days` days ending today
    end_date = pd.Timestamp.today().normalize()
    start_date = end_date - pd.Timedelta(days=days - 1)
    dates = pd.date_range(start=start_date, end=end_date)

    # 3. Sparse events: on average one event every 4 days per item
    num_events = (num_items * days) // 4
    random_dates = np.random.choice(dates, num_events)
    random_items = np.random.choice(items, num_events)

    # 4. Event type: 80% demand / 20% restock
    tipos = np.random.choice(['Salida Almacén', 'Colocación Carro'], num_events, p=[0.8, 0.2])

    # 5. Quantities: demand 1-14 units, restocks 30-149 units
    cantidades = np.where(tipos == 'Salida Almacén',
                          np.random.randint(1, 15, num_events),
                          np.random.randint(30, 150, num_events))

    # Trend: last year's demand is ~20% lower, simulating growth
    one_year_ago = end_date - pd.DateOffset(years=1)
    is_last_year = random_dates < one_year_ago
    cantidades = np.where(is_last_year & (tipos == 'Salida Almacén'),
                          np.maximum(1, cantidades * 0.8).astype(int),
                          cantidades)

    # 6. Assemble
    df = pd.DataFrame({
        'Referencia': random_items,
        'Descripción': 'PRODUCTO_SIMULADO',
        'Tipo': tipos,
        'Cantidad': cantidades,
        'Fecha proceso': random_dates
    })
    df = df.sort_values('Fecha proceso').reset_index(drop=True)

    # 7. Save (semicolon is safer for European locales)
    if output_file is not None:
        print(f"Saving {len(df)} rows to {output_file}...")
        df.to_csv(output_file, index=False, sep=';')
    print("Done!")

    return df
