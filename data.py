import pandas as pd
import numpy as np

def generate_synthetic_warehouse_data(num_items=2500, days=730, output_file='synthetic_inventory.csv'):
    print(f"Generating synthetic data for {num_items} items over {days} days...")
    
    # 1. Setup items
    items = [f"ITEM_{str(i).zfill(4)}" for i in range(1, num_items + 1)]
    
    # 2. Create the timeline (Last 2 years ending today)
    end_date = pd.Timestamp.today().normalize()
    start_date = end_date - pd.Timedelta(days=days-1)
    dates = pd.date_range(start=start_date, end=end_date)
    
    # 3. Simulate Sparse Events
    # We don't want every item moving every day. Let's average 1 event every 4 days per item.
    num_events = (num_items * days) // 4 
    
    # Randomly assign dates and items to these events
    random_dates = np.random.choice(dates, num_events)
    random_items = np.random.choice(items, num_events)
    
    # 4. Determine Event Type (80% Demand / Salida, 20% Restock / Colocación)
    tipos = np.random.choice(['Salida Almacén', 'Colocación Carro'], num_events, p=[0.8, 0.2])
    
    # 5. Generate Quantities
    # Base logic: Demand is 1 to 10 units. Restocks are bulkier (20 to 100 units).
    cantidades = np.where(tipos == 'Salida Almacén', 
                          np.random.randint(1, 15, num_events), 
                          np.random.randint(30, 150, num_events))
    
    # --- The Trend Simulation ---
    # To test your formula (ThisYear - LastYear), we make Last Year's demand slightly lower
    one_year_ago = end_date - pd.DateOffset(years=1)
    is_last_year = random_dates < one_year_ago
    
    # Reduce 'Salida' quantities by ~20% for the previous year to simulate a growing trend
    cantidades = np.where(is_last_year & (tipos == 'Salida Almacén'), 
                          np.maximum(1, cantidades * 0.8).astype(int), 
                          cantidades)

    # 6. Build the DataFrame
    df = pd.DataFrame({
        'Referencia': random_items,
        'Descripción': 'PRODUCTO_SIMULADO',
        'Tipo': tipos,
        'Cantidad': cantidades,
        'Fecha proceso': random_dates
    })
    
    # Sort chronologically for realism
    df = df.sort_values('Fecha proceso').reset_index(drop=True)
    
    # 7. Save to CSV
    print(f"Saving {len(df)} rows to {output_file}...")
    df.to_csv(output_file, index=False, sep=';') # Semicolon is safer for European locales
    print("Done!")
    
    return df

# Run it
# df_synthetic = generate_synthetic_warehouse_data()