"""Print the stockout alert report for an inventory CSV.

Usage: python scripts/stockout_report.py [--data PATH] [--days 30]
"""

import argparse

from warehouse_forecaster.constants import DEFAULT_INVENTORY_CSV
from warehouse_forecaster.data.io import load_inventory_csv
from warehouse_forecaster.models.alerts import generate_alert_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default=str(DEFAULT_INVENTORY_CSV))
    parser.add_argument("--days", type=int, default=30, help="Forecast horizon in days")
    args = parser.parse_args()

    df = load_inventory_csv(args.data)
    generate_alert_report(df, forecast_days=args.days)


if __name__ == "__main__":
    main()
