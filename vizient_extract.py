"""
Vizient Data Extract
=====================
Filters the Vizient source CSV to only rows where System Name matches
the target customer list, and writes a new CSV with all original columns.

Usage:
  py vizient_extract.py
  py vizient_extract.py --vizient "path/to/vizient.csv" --filter-names "path/to/names.txt" --output "path/to/output.csv"
"""

import argparse
import csv

DEFAULT_VIZIENT     = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\Vizient week 10.15.2025.csv"
DEFAULT_FILTER      = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\vizient_target_systems.txt"
DEFAULT_OUTPUT      = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\vizient_customers_extract.csv"

COL_SYSTEM_NAME = "System Name"


def main():
    parser = argparse.ArgumentParser(description="Extract Vizient rows for target customers")
    parser.add_argument("--vizient",      default=DEFAULT_VIZIENT, help="Vizient source CSV")
    parser.add_argument("--filter-names", default=DEFAULT_FILTER,  help="Text file with one System Name per line")
    parser.add_argument("--output",       default=DEFAULT_OUTPUT,  help="Output CSV file path")
    args = parser.parse_args()

    # Load target names (case-insensitive)
    print(f"\nReading filter: {args.filter_names}")
    with open(args.filter_names, encoding="utf-8") as f:
        target_names = {line.strip().lower() for line in f if line.strip()}
    print(f"  Target systems: {len(target_names):,}")

    # Stream through source CSV and write matches
    print(f"\nReading: {args.vizient}")
    total_rows  = 0
    matched     = 0
    unmatched_systems = set()

    with open(args.vizient, newline="", encoding="utf-8-sig") as fin, \
         open(args.output,  newline="", encoding="utf-8-sig", mode="w") as fout:

        reader = csv.DictReader(fin)
        writer = csv.DictWriter(fout, fieldnames=reader.fieldnames, extrasaction="ignore")
        writer.writeheader()

        for row in reader:
            total_rows += 1
            system_name = row.get(COL_SYSTEM_NAME, "").strip()

            if system_name.lower() in target_names:
                writer.writerow(row)
                matched += 1
            else:
                if system_name:
                    unmatched_systems.add(system_name)

    print(f"  Total rows read : {total_rows:,}")
    print(f"  Rows extracted  : {matched:,}")
    print(f"  Output written  : {args.output}")

    if unmatched_systems:
        print(f"\n  Systems in file NOT in your target list: {len(unmatched_systems):,}")
        # Uncomment to see them all:
        # for name in sorted(unmatched_systems):
        #     print(f"    {name}")

    print("\nDone.\n")


if __name__ == "__main__":
    main()
