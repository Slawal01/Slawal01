"""
HealthTrust Deduplication Script
Reads a HealthTrust Excel file, deduplicates on GPOID, and writes a clean output file.

Usage:
    python ht_dedup.py --input "Sample Health Trust Data.xlsx" --output ht_clean.xlsx
"""

import argparse
import pandas as pd


HEALTHTRUST_COLUMNS = [
    "GPOID",
    "Membership Eligible Date",
    "Name1",
    "Name2",
    "Address1",
    "Address2",
    "Address3",
    "City",
    "State/Province",
    "Postal Code",
    "Country",
    "Direct Parent GPOID",
    "Direct Parent Name1",
    "Top Parent GPOID",
    "Top Parent Name 1",
    "Member Status",
    "Comments",
]


def load_and_dedup(filepath):
    print(f"\nReading: {filepath}")
    df = pd.read_excel(filepath)

    print(f"  Total rows in source:     {len(df)}")
    print(f"  Unique GPOIDs in source:  {df['GPOID'].nunique()}")

    duplicated_mask = df.duplicated(subset=["GPOID"], keep=False)
    dupe_count = duplicated_mask.sum()
    if dupe_count:
        print(f"  Rows causing duplicates:  {dupe_count} ({df[duplicated_mask]['GPOID'].nunique()} GPOIDs with multiple rows)")
    else:
        print(f"  No duplicates found on GPOID.")

    # Keep only the columns we need
    existing_cols = [c for c in HEALTHTRUST_COLUMNS if c in df.columns]
    missing_cols  = [c for c in HEALTHTRUST_COLUMNS if c not in df.columns]
    if missing_cols:
        print(f"\n  WARNING — expected columns not found in file:")
        for c in missing_cols:
            print(f"    - {c}")

    df = df[existing_cols]

    # Deduplicate: one row per GPOID (keep first occurrence)
    df_dedup = df.drop_duplicates(subset=["GPOID"], keep="first")
    print(f"\n  After deduplication:      {len(df_dedup)} unique members")

    return df_dedup


def show_hierarchy_summary(df):
    """Show how many members fall into each hierarchy level."""
    df = df.copy()
    for col in ["GPOID", "Direct Parent GPOID", "Top Parent GPOID"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    top_parents = df[
        (df["GPOID"] == df["Direct Parent GPOID"]) &
        (df["GPOID"] == df["Top Parent GPOID"])
    ]

    two_level = df[
        (df["GPOID"] == df["Direct Parent GPOID"]) &
        (df["GPOID"] != df["Top Parent GPOID"])
    ]

    direct_parents = df[
        (df["Direct Parent GPOID"] == df["Top Parent GPOID"]) &
        (df["GPOID"] != df["Top Parent GPOID"])
    ]

    leaf_members = df[
        (df["Direct Parent GPOID"] != df["Top Parent GPOID"]) &
        (df["GPOID"] != df["Direct Parent GPOID"])
    ]

    print(f"\n  Hierarchy breakdown:")
    print(f"    Top Parents  (top=direct=self):            {len(top_parents)}")
    print(f"    2-level members (direct=self, top!=self):  {len(two_level)}")
    print(f"    Direct Parents (top=direct!=self):         {len(direct_parents)}")
    print(f"    3-level Leaf Members (top!=direct!=self):  {len(leaf_members)}")
    print(f"    Total:                                     {len(df)}")

    # Sanity check
    accounted = len(top_parents) + len(two_level) + len(direct_parents) + len(leaf_members)
    if accounted != len(df):
        print(f"\n  WARNING: {len(df) - accounted} rows did not match any hierarchy rule — check data.")


def main():
    parser = argparse.ArgumentParser(description="Deduplicate HealthTrust Excel data on GPOID")
    parser.add_argument("--input",  required=True, help="Path to HealthTrust Excel file")
    parser.add_argument("--output", required=True, help="Output Excel file for clean deduplicated data")
    args = parser.parse_args()

    df_clean = load_and_dedup(args.input)
    show_hierarchy_summary(df_clean)

    df_clean.to_excel(args.output, index=False)
    print(f"\n  Clean file written: {args.output}")
    print(f"  Done.\n")


if __name__ == "__main__":
    main()
