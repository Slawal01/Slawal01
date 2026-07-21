"""
Premier Top Parent CSV Import Generator
=========================================
Reads Premier complete data CSV and generates a STEP-compatible CSV
import file for Top Parent entities.

Top Parent logic:
  GPO ID == Top Parent GPO ID
  AND (Direct Parent GPO ID == GPO ID OR Direct Parent GPO ID is blank)
  One unique Top Parent per unique GPO ID.

Output columns:
  <ID>                blank (STEP auto-assigns)
  <Name>              Top Parent Name 1
  <Parent ID>         GPO_Premier
  <Object Type>       GPO_Top_Parent
  gpo.GPO_Member_ID   Address ID
  gpo.GPO_Entity_Key  Address ID

Usage:
  py premier_top_parent_csv.py
"""

import argparse
import csv

DEFAULT_INPUT  = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\Premier complete data.csv"
DEFAULT_OUTPUT = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\premier_top_parents_import.csv"

COL_ADDRESS_ID    = "Address ID"
COL_GPO_ID        = "GPO ID"
COL_NAME1         = "Name 1"
COL_TOP_PARENT_ID = "Top Parent GPO ID"
COL_TOP_NAME1     = "Top Parent Name 1"
COL_DIRECT_ID     = "Direct Parent GPO ID"

STEP_PARENT_ID   = "GPO_Premier"
STEP_OBJECT_TYPE = "GPO_Top_Parent"

OUT_FIELDS = [
    "<ID>",
    "<Name>",
    "<Parent ID>",
    "<Object Type>",
    "gpo.GPO_Member_ID",
    "gpo.GPO_Entity_Key",
]


def main():
    parser = argparse.ArgumentParser(description="Generate Premier Top Parent CSV for STEP import")
    parser.add_argument("--input",  default=DEFAULT_INPUT,  help="Premier complete data CSV")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output CSV file path")
    args = parser.parse_args()

    print(f"\nReading: {args.input}")
    seen_ids    = set()
    top_parents = []
    total_rows  = 0
    rejected    = 0

    with open(args.input, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            address_id = row.get(COL_ADDRESS_ID,    "").strip()
            gpo_id     = row.get(COL_GPO_ID,        "").strip()
            name1      = row.get(COL_TOP_NAME1,     "").strip() or row.get(COL_NAME1, "").strip()
            top_id     = row.get(COL_TOP_PARENT_ID, "").strip()
            direct_id  = row.get(COL_DIRECT_ID,     "").strip()

            if not gpo_id or not top_id:
                continue

            # Top parent: GPO ID == Top Parent GPO ID
            # AND Direct Parent GPO ID == GPO ID or blank
            is_top = (
                gpo_id == top_id and
                (direct_id == "" or direct_id == gpo_id)
            )
            if not is_top:
                continue

            # Reject blank or NA names
            if not name1 or name1.upper() in ("NA", "N/A"):
                print(f"  REJECTED (no name): GPO ID {gpo_id} / Address ID {address_id}")
                rejected += 1
                continue

            # Deduplicate by GPO ID
            if gpo_id in seen_ids:
                continue
            seen_ids.add(gpo_id)

            top_parents.append({
                "<ID>":               "",
                "<Name>":             name1,
                "<Parent ID>":        STEP_PARENT_ID,
                "<Object Type>":      STEP_OBJECT_TYPE,
                "gpo.GPO_Member_ID":  address_id,
                "gpo.GPO_Entity_Key": address_id,
            })

    print(f"  Total rows read    : {total_rows:,}")
    print(f"  Rejected (no name) : {rejected:,}")
    print(f"  Top parents found  : {len(top_parents):,}")

    with open(args.output, newline="", encoding="utf-8-sig", mode="w") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        writer.writeheader()
        writer.writerows(top_parents)

    print(f"\n  Output written     : {args.output}")
    print("Done.\n")


if __name__ == "__main__":
    main()
