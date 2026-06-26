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


def get_file_columns(filepath):
    """Read just the header row to see what columns exist — no data loaded."""
    df_header = pd.read_excel(filepath, nrows=0)
    return list(df_header.columns)


def load_and_dedup(filepath):
    print(f"\nReading: {filepath}")

    # Step 1: check which of our required columns exist in the file
    all_cols    = get_file_columns(filepath)
    existing_cols = [c for c in HEALTHTRUST_COLUMNS if c in all_cols]
    missing_cols  = [c for c in HEALTHTRUST_COLUMNS if c not in all_cols]

    if missing_cols:
        print(f"  WARNING — expected columns not found in file:")
        for c in missing_cols:
            print(f"    - {c}")

    # Step 2: load ONLY the columns we need, all as strings to reduce memory
    # This avoids loading 50+ columns when we only need 17
    print(f"  Loading {len(existing_cols)} of {len(all_cols)} columns...")
    df = pd.read_excel(
        filepath,
        usecols=existing_cols,
        dtype=str,              # read everything as string — avoids type inference overhead
        engine="openpyxl",
    )

    # Strip whitespace from all cells
    df = df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)

    print(f"  Total rows in source:     {len(df)}")
    print(f"  Unique GPOIDs in source:  {df['GPOID'].nunique()}")

    duplicated_mask = df.duplicated(subset=["GPOID"], keep=False)
    dupe_count = duplicated_mask.sum()
    if dupe_count:
        print(f"  Rows causing duplicates:  {dupe_count} ({df[duplicated_mask]['GPOID'].nunique()} GPOIDs with multiple rows)")
    else:
        print(f"  No duplicates found on GPOID.")

    # Step 3: deduplicate — one row per GPOID (keep first occurrence)
    df_dedup = df.drop_duplicates(subset=["GPOID"], keep="first").reset_index(drop=True)
    print(f"  After deduplication:      {len(df_dedup)} unique members")

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
    parser.add_argument("--output", required=True, help="Output file path (.csv or .xlsx)")
    args = parser.parse_args()

    df_clean = load_and_dedup(args.input)
    show_hierarchy_summary(df_clean)

    if args.output.endswith(".xlsx"):
        df_clean.to_excel(args.output, index=False)
    else:
        df_clean.to_csv(args.output, index=False)

    print(f"\n  Clean file written: {args.output}")
    print(f"  Done.\n")


if __name__ == "__main__":
    main()
