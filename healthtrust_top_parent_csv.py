"""
HealthTrust Top Parent CSV Import Generator
=============================================
Reads HealthTrust deduped CSV and generates a STEP-compatible CSV
import file for Top Parent entities.

Top Parent logic:
  GPOID == Top Parent GPOID AND Direct Parent GPOID is blank
  One unique Top Parent per unique GPOID.

Output columns:
  <ID>                blank (STEP auto-assigns)
  <Name>              Top Parent Name 1
  <Parent ID>         GPO_HealthTrust
  <Object Type>       GPO_Top_Parent
  gpo.GPO_Member_ID   Top Parent GPOID
  gpo.GPO_Entity_Key  Top Parent GPOID
  gpo.Address_ID      COID

Usage:
  py healthtrust_top_parent_csv.py
"""

import argparse
import csv

DEFAULT_INPUT  = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\HealthTrust deduped.csv"
DEFAULT_OUTPUT = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\healthtrust_top_parents_import.csv"

COL_GPOID    = "GPOID"
COL_COID     = "COID"
COL_NAME1    = "Name1"
COL_TOP_ID   = "Top Parent GPOID"
COL_TOP_NAME = "Top Parent Name 1"
COL_DP_ID    = "Direct Parent GPOID"

STEP_PARENT_ID   = "GPO_HealthTrust"
STEP_OBJECT_TYPE = "GPO_Top_Parent"

OUT_FIELDS = [
    "<ID>",
    "<Name>",
    "<Parent ID>",
    "<Object Type>",
    "gpo.GPO_Member_ID",
    "gpo.GPO_Entity_Key",
    "gpo.Address_ID",
]


def main():
    parser = argparse.ArgumentParser(description="Generate HealthTrust Top Parent CSV for STEP import")
    parser.add_argument("--input",  default=DEFAULT_INPUT,  help="HealthTrust deduped CSV")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output CSV file path")
    args = parser.parse_args()

    print(f"\nReading: {args.input}")
    seen_ids    = set()
    top_parents = []
    total_rows  = 0
    rejected    = 0

    with open(args.input, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            total_rows += 1
            gpoid    = row.get(COL_GPOID,    "").strip()
            coid     = row.get(COL_COID,     "").strip()
            top_id   = row.get(COL_TOP_ID,   "").strip()
            top_name = row.get(COL_TOP_NAME, "").strip()
            dp_id    = row.get(COL_DP_ID,    "").strip()

            if not gpoid or not top_id:
                continue

            # Top parent: GPOID == Top Parent GPOID AND Direct Parent GPOID is blank
            if not (gpoid == top_id and dp_id == ""):
                continue

            if not top_name:
                rejected += 1
                continue

            if gpoid in seen_ids:
                continue
            seen_ids.add(gpoid)

            top_parents.append({
                "<ID>":               "",
                "<Name>":             top_name,
                "<Parent ID>":        STEP_PARENT_ID,
                "<Object Type>":      STEP_OBJECT_TYPE,
                "gpo.GPO_Member_ID":  top_id,
                "gpo.GPO_Entity_Key": top_id,
                "gpo.Address_ID":     coid,
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
