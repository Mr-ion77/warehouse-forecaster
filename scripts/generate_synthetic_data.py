"""Regenerate data/synthetic_inventory.csv.

Usage: python scripts/generate_synthetic_data.py [--items 2500] [--days 730] [--out PATH] [--seed N]
"""

import argparse

import numpy as np

from warehouse_forecaster.constants import DEFAULT_INVENTORY_CSV
from warehouse_forecaster.data.synthetic import generate_synthetic_warehouse_data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--items", type=int, default=2500)
    parser.add_argument("--days", type=int, default=730)
    parser.add_argument("--out", default=str(DEFAULT_INVENTORY_CSV))
    parser.add_argument("--seed", type=int, default=None, help="NumPy seed for reproducible output")
    args = parser.parse_args()

    if args.seed is not None:
        np.random.seed(args.seed)
    generate_synthetic_warehouse_data(num_items=args.items, days=args.days, output_file=args.out)


if __name__ == "__main__":
    main()
