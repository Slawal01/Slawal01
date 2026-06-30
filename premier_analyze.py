"""
Premier Data Analysis Script
Reads a Premier Excel file and shows hierarchy breakdown before STEPXML generation.

Usage:
    python premier_analyze.py --input "Premier Data.xlsx"
    python premier_analyze.py --input "Premier Data.xlsx" --output premier_top_parents.xlsx
"""

import argparse
import pandas as pd


PREMIER_COLUMNS = [
    "Address ID",
    "GPO ID",
    "Membership Start Date",
    "Name 1",
    "Name 2",
    "Override Name",
    "Address Type",
    "Address 1",
    "Address 2",
    "Address 3",
    "City",
    "State/Province",
    "Postal Code",
    "Country",
    "Relationship to Top Parent",
    "Relationship to Direct Parent",
    "Direct Parent GPO ID",
    "Direct Parent Name 1",
    "Top Parent GPO ID",
    "Top Parent Name 1",
    "Member Status",
    "Top Parent Flag",
]


def load_premier(filepath):
    print(f"\nReading: {filepath}")
    df = pd.read_excel(filepath, dtype=str)
    df.columns = df.columns.str.strip()

    existing  = [c for c in PREMIER_COLUMNS if c in df.columns]
    missing   = [c for c in PREMIER_COLUMNS if c not in df.columns]

    if missing:
        print(f"  WARNING — expected columns not found:")
        for c in missing:
            print(f"    - {c}")

    df = df[existing]
    df = df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)

    print(f"  Total rows:          {len(df)}")
    print(f"  Unique Address IDs:  {df['Address ID'].nunique()}")
    print(f"  Unique GPO IDs:      {df['GPO ID'].nunique()}")
    return df


def show_hierarchy_breakdown(df):
    gpo        = df["GPO ID"].astype(str).str.strip()
    top        = df["Top Parent GPO ID"].astype(str).str.strip()
    direct     = df["Direct Parent GPO ID"].astype(str).str.strip()
    direct_blank = direct.isin(["", "nan", "None", "NaN"])

    top_parents = df[
        (top == gpo) &
        ((direct == gpo) | direct_blank)
    ]

    direct_parents = df[
        (~direct_blank) &
        (top == direct) &
        (top != gpo)
    ]

    two_level = df[
        (~direct_blank) &
        (direct == gpo) &
        (top != gpo)
    ]

    three_level = df[
        (~direct_blank) &
        (top != direct) &
        (top != gpo) &
        (direct != gpo)
    ]

    print(f"\n  Hierarchy breakdown:")
    print(f"    Top Parents       (top=self, direct=blank or self):  {len(top_parents)}")
    print(f"    Direct Parents    (top=direct≠self):                 {len(direct_parents)}")
    print(f"    2-level Members   (direct=self, top≠self):           {len(two_level)}")
    print(f"    3-level Members   (top≠direct≠self):                 {len(three_level)}")
    total = len(top_parents) + len(direct_parents) + len(two_level) + len(three_level)
    print(f"    Total accounted:                                     {total}")
    if total != len(df):
        print(f"\n  WARNING: {len(df) - total} rows did not match any hierarchy rule — check data.")
        unmatched = df[
            ~df.index.isin(top_parents.index) &
            ~df.index.isin(direct_parents.index) &
            ~df.index.isin(two_level.index) &
            ~df.index.isin(three_level.index)
        ]
        print(f"\n  Sample unmatched rows (first 5):")
        print(unmatched[["Address ID", "GPO ID", "Top Parent GPO ID", "Direct Parent GPO ID"]].head())

    print(f"\n  Sample Top Parents (first 5):")
    cols = ["Address ID", "GPO ID", "Top Parent GPO ID", "Direct Parent GPO ID", "Name 1", "Address Type"]
    print(top_parents[[c for c in cols if c in top_parents.columns]].head().to_string(index=False))

    return top_parents, direct_parents


def main():
    parser = argparse.ArgumentParser(description="Analyze Premier hierarchy before STEPXML generation")
    parser.add_argument("--input",  required=True, help="Path to Premier Excel file")
    parser.add_argument("--output", required=False, help="Optional: save top parents to Excel/CSV")
    args = parser.parse_args()

    df = load_premier(args.input)
    top_parents, _ = show_hierarchy_breakdown(df)

    if args.output:
        if args.output.endswith(".xlsx"):
            top_parents.to_excel(args.output, index=False)
        else:
            top_parents.to_csv(args.output, index=False)
        print(f"\n  Top parents saved to: {args.output}")

    print(f"\n  Done.\n")


if __name__ == "__main__":
    main()
