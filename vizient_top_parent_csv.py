"""
Vizient Top Parent CSV Import Generator
=========================================
Reads the Vizient source CSV, filters to top parents matching the target
customer list, and outputs a STEP-compatible CSV import file.

Top Parent logic:
  System ID == Parent ID == Member ID  (all three must be equal and non-blank)
  Rows with blank or NA System Name are rejected.
  System Name must match vizient_target_systems.txt (case-insensitive).

Output columns:
  <ID>                  blank (STEP auto-assigns)
  <Name>                System Name
  <Parent ID>           GPO_Vizient
  <Object Type>         GPO_Top_Parent
  gpo.GPO_Member_ID     System ID
  gpo.GPO_Entity_Key    LIC if present, else System ID

Usage:
  py vizient_top_parent_csv.py
  py vizient_top_parent_csv.py --vizient "path/to/file.csv" --filter-names "path/to/names.txt" --output "path/to/output.csv"
"""

import argparse
import csv

DEFAULT_VIZIENT     = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\vizient_customers_extract.csv"
DEFAULT_OUTPUT      = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\vizient_top_parents_import.csv"

# Vizient source columns
COL_MEMBER_ID   = "Member ID"
COL_SYSTEM_ID   = "System ID"
COL_SYSTEM_NAME = "System Name"
COL_PARENT_ID   = "Parent ID"

# STEP values
STEP_PARENT_ID  = "GPO_Vizient"
STEP_OBJECT_TYPE = "GPO_Top_Parent"

# Output CSV column headers
OUT_FIELDS = [
    "<ID>",
    "<Name>",
    "<Parent ID>",
    "<Object Type>",
    "gpo.GPO_Member_ID",
    "gpo.GPO_Entity_Key",
]


def main():
    parser = argparse.ArgumentParser(description="Generate Vizient Top Parent CSV for STEP import")
    parser.add_argument("--vizient", default=DEFAULT_VIZIENT, help="Vizient customer extract CSV")
    parser.add_argument("--output",  default=DEFAULT_OUTPUT,  help="Output CSV file path")
    args = parser.parse_args()

    # Read customer extract and find top parents
    print(f"\nReading: {args.vizient}")
    seen_ids    = set()
    top_parents = []
    total_rows  = 0
    rejected    = 0

    with open(args.vizient, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            member_id   = row.get(COL_MEMBER_ID,   "").strip()
            system_id   = row.get(COL_SYSTEM_ID,   "").strip()
            system_name = row.get(COL_SYSTEM_NAME, "").strip()
            parent_id   = row.get(COL_PARENT_ID,   "").strip()

            # Top parent logic:
            #   System ID == Member ID  AND  (Parent ID == System ID OR Parent ID is blank)
            is_top = (
                system_id and member_id and
                system_id == member_id and
                (parent_id == system_id or parent_id == "")
            )

            if not is_top:
                continue

            # Reject blank or NA names
            if not system_name or system_name.upper() == "NA":
                print(f"  REJECTED (no name): System ID {system_id}")
                rejected += 1
                continue

            # Deduplicate
            if system_id in seen_ids:
                continue
            seen_ids.add(system_id)

            # Entity Key for top parent = System ID (same as Member ID)
            top_parents.append({
                "<ID>":                 "",
                "<Name>":               system_name,
                "<Parent ID>":          STEP_PARENT_ID,
                "<Object Type>":        STEP_OBJECT_TYPE,
                "gpo.GPO_Member_ID":    system_id,
                "gpo.GPO_Entity_Key":   system_id,
            })

    print(f"  Total rows read  : {total_rows:,}")
    print(f"  Rejected (no name): {rejected:,}")
    print(f"  Top parents found : {len(top_parents):,}")

    # Write output CSV
    with open(args.output, newline="", encoding="utf-8-sig", mode="w") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        writer.writeheader()
        writer.writerows(top_parents)

    print(f"\n  Output written   : {args.output}")
    print("Done.\n")


if __name__ == "__main__":
    main()
