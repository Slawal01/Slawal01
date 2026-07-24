"""
HealthTrust Deduplication
==========================
Reads the raw HealthTrust CSV and removes duplicate rows caused by
multiple DEA numbers per entity. Keeps the first row per unique COID.

Usage:
  py healthtrust_deduplicate.py
"""

import argparse
import csv

DEFAULT_INPUT  = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\HealthTrust week 10.15.25.csv"
DEFAULT_OUTPUT = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\HealthTrust deduped.csv"


def main():
    parser = argparse.ArgumentParser(description="Deduplicate HealthTrust CSV by COID")
    parser.add_argument("--input",  default=DEFAULT_INPUT,  help="Raw HealthTrust CSV")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Deduplicated output CSV")
    args = parser.parse_args()

    print(f"\nReading: {args.input}")
    total   = 0
    kept    = 0
    skipped = 0
    seen    = set()
    rows    = []
    fieldnames = None

    with open(args.input, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            total += 1
            coid = row.get("COID", "").strip()
            if coid in seen:
                skipped += 1
                continue
            seen.add(coid)
            kept += 1
            rows.append(row)

    print(f"  Total rows before dedup : {total:,}")
    print(f"  Unique rows kept        : {kept:,}")
    print(f"  Duplicates removed      : {skipped:,}")

    with open(args.output, newline="", encoding="utf-8-sig", mode="w") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n  Output written: {args.output}")
    print("Done.\n")


if __name__ == "__main__":
    main()
