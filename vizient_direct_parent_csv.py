"""
Vizient Direct Parent CSV Import Generator
============================================
Reads vizient_customers_extract.csv and generates a STEP-compatible CSV
import file for Direct Parent entities.

Direct Parent logic:
  Parent ID != System ID  AND  Parent ID != Member ID
  One unique Direct Parent per unique Parent ID value.
  Parent ID in STEP = Top Parent's STEP entity ID (from step export).

Output columns:
  <ID>                blank (STEP auto-assigns)
  <Name>              Parent Name
  <Parent ID>         Top Parent STEP entity ID
  <Object Type>       GPO_Direct_Parent
  gpo.GPO_Member_ID   Parent ID
  gpo.GPO_Entity_Key  Parent ID

Usage:
  py vizient_direct_parent_csv.py
"""

import argparse
import csv

DEFAULT_EXTRACT     = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\vizient_customers_extract.csv"
DEFAULT_STEP_EXPORT = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\STEP Parent ID Vizient.csv"
DEFAULT_OUTPUT      = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\vizient_direct_parents_import.csv"

# Vizient extract columns
COL_MEMBER_ID   = "Member ID"
COL_SYSTEM_ID   = "System ID"
COL_SYSTEM_NAME = "System Name"
COL_PARENT_ID   = "Parent ID"
COL_PARENT_NAME = "Parent Name"

# STEP export columns
STEP_COL_ID   = "<ID>"
STEP_COL_NAME = "<Name>"

STEP_OBJECT_TYPE = "GPO_Direct_Parent"

OUT_FIELDS = [
    "<ID>",
    "<Name>",
    "<Parent ID>",
    "<Object Type>",
    "gpo.GPO_Member_ID",
    "gpo.GPO_Entity_Key",
]


def main():
    parser = argparse.ArgumentParser(description="Generate Vizient Direct Parent CSV for STEP import")
    parser.add_argument("--extract",     default=DEFAULT_EXTRACT,     help="vizient_customers_extract.csv")
    parser.add_argument("--step-export", default=DEFAULT_STEP_EXPORT, help="STEP export CSV with top parent IDs")
    parser.add_argument("--output",      default=DEFAULT_OUTPUT,      help="Output CSV file path")
    args = parser.parse_args()

    # ── Load STEP export: map System Name (lower) -> STEP ID ─────────────────
    print(f"\nReading STEP export: {args.step_export}")
    step_id_map = {}
    duplicates  = set()
    with open(args.step_export, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            step_id = row.get(STEP_COL_ID,   "").strip()
            name    = row.get(STEP_COL_NAME, "").strip().lower()
            if not step_id or not name:
                continue
            if name in step_id_map:
                duplicates.add(name)
            else:
                step_id_map[name] = step_id
    print(f"  Top parents mapped: {len(step_id_map):,}")
    if duplicates:
        print(f"  Duplicate names ({len(duplicates)}) — first STEP ID used:")
        for n in sorted(duplicates):
            print(f"    {n}")

    # ── Read extract and find unique direct parents ───────────────────────────
    print(f"\nReading extract: {args.extract}")
    seen_dp      = set()   # (system_id, parent_id) already emitted
    direct_parents = []
    total_rows   = 0
    no_step_id   = []

    with open(args.extract, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            member_id   = row.get(COL_MEMBER_ID,   "").strip()
            system_id   = row.get(COL_SYSTEM_ID,   "").strip()
            system_name = row.get(COL_SYSTEM_NAME, "").strip()
            parent_id   = row.get(COL_PARENT_ID,   "").strip()
            parent_name = row.get(COL_PARENT_NAME, "").strip()

            if not system_id or not parent_id:
                continue

            # Direct Parent: Parent ID != System ID AND Parent ID != Member ID
            is_dp = (parent_id != system_id and parent_id != member_id)
            if not is_dp:
                continue

            # Deduplicate per system + parent combination
            key = (system_id, parent_id)
            if key in seen_dp:
                continue
            seen_dp.add(key)

            step_id = step_id_map.get(system_name.lower())
            if not step_id:
                no_step_id.append(f"{system_id} / {system_name}")
                continue

            direct_parents.append({
                "<ID>":               "",
                "<Name>":             parent_name,
                "<Parent ID>":        step_id,
                "<Object Type>":      STEP_OBJECT_TYPE,
                "gpo.GPO_Member_ID":  parent_id,
                "gpo.GPO_Entity_Key": parent_id,
            })

    print(f"  Total rows read      : {total_rows:,}")
    print(f"  Direct parents found : {len(direct_parents):,}")
    if no_step_id:
        print(f"  No STEP ID found     : {len(no_step_id)}")
        for n in no_step_id[:10]:
            print(f"    {n}")
        if len(no_step_id) > 10:
            print(f"    ... and {len(no_step_id) - 10} more")

    # ── Write output CSV ──────────────────────────────────────────────────────
    with open(args.output, newline="", encoding="utf-8-sig", mode="w") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        writer.writeheader()
        writer.writerows(direct_parents)

    print(f"\n  Output written       : {args.output}")
    print("Done.\n")


if __name__ == "__main__":
    main()
