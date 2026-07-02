"""
Vizient Top Parent Members CSV Import Generator
=================================================
For top parents that are also their own member, creates a GPO_Member record
nested under the top parent using the STEP-assigned top parent ID.

Logic:
  - Reads the STEP export CSV to map System Name -> STEP entity ID
  - Reads the vizient_customers_extract.csv
  - Finds rows where Member ID == System ID (top parent's own member row)
  - Creates one GPO_Member per row with ParentID = top parent STEP ID

Attributes per member:
  gpo.GPO_Member_ID            = Member ID
  gpo.GPO_Entity_Key           = LIC if present, else Member ID
  gpo.LIC                      = LIC
  gpo.GLN                      = GLN
  gpo.HIN                      = HIN
  gpo.Membership_Eligible_Date = Member Date (DD-Mon-YYYY)
  gpo.Facility_Category        = Facility Category
  gpo.Facility_Type            = Facility Type
  gpo.Rx_Group                 = Rx Group
  loc.Address_Country          = US

Usage:
  py vizient_top_parent_members_csv.py
"""

import argparse
import csv
from datetime import datetime

DEFAULT_EXTRACT     = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\vizient_customers_extract.csv"
DEFAULT_STEP_EXPORT = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\vizient_top_parents_step_export.csv"
DEFAULT_OUTPUT      = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\vizient_top_parent_members_import.csv"

# Vizient extract columns
COL_MEMBER_ID   = "Member ID"
COL_LIC         = "LIC"
COL_GLN         = "GLN"
COL_HIN         = "HIN"
COL_MEMBER_DATE = "Member Date"
COL_MEMBER_NAME = "Member Name"
COL_SYSTEM_ID   = "System ID"
COL_SYSTEM_NAME = "System Name"
COL_PARENT_ID   = "Parent ID"
COL_FAC_CAT     = "Facility Category"
COL_FAC_TYPE    = "Facility Type"
COL_RX_GROUP    = "Rx Group"

# STEP export columns
STEP_COL_ID   = "<ID>"
STEP_COL_NAME = "<Name>"

STEP_OBJECT_TYPE = "GPO_Member"

OUT_FIELDS = [
    "<ID>",
    "<Name>",
    "<Parent ID>",
    "<Object Type>",
    "gpo.GPO_Member_ID",
    "gpo.GPO_Entity_Key",
    "gpo.LIC",
    "gpo.GLN",
    "gpo.HIN",
    "gpo.Membership_Eligible_Date",
    "gpo.Facility_Category",
    "gpo.Facility_Type",
    "gpo.Rx_Group",
    "loc.Address_Country",
]


def safe(val):
    v = str(val).strip()
    return "" if v.lower() in ("nan", "none", "nat", "n/a", "na") else v


def safe_gln(val):
    v = safe(val)
    if not v:
        return ""
    try:
        return str(int(float(v)))
    except (ValueError, OverflowError):
        return v


def parse_date(val):
    v = str(val).strip()
    if not v or v.lower() in ("nan", "none", "nat", ""):
        return ""
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%d-%b-%Y", "%d-%B-%Y", "%m-%d-%Y"):
        try:
            return datetime.strptime(v, fmt).strftime("%d-%b-%Y")
        except ValueError:
            pass
    return v


def main():
    parser = argparse.ArgumentParser(description="Generate member CSV for top parent self-rows")
    parser.add_argument("--extract",     default=DEFAULT_EXTRACT,     help="vizient_customers_extract.csv")
    parser.add_argument("--step-export", default=DEFAULT_STEP_EXPORT, help="STEP export CSV with top parent IDs and names")
    parser.add_argument("--output",      default=DEFAULT_OUTPUT,      help="Output CSV file path")
    args = parser.parse_args()

    # ── Load STEP export: map System Name (lower) -> list of STEP IDs ────────
    print(f"\nReading STEP export: {args.step_export}")
    step_id_map = {}   # name_lower -> STEP ID (warn if duplicate)
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
    print(f"  Top parents mapped : {len(step_id_map):,}")
    if duplicates:
        print(f"  Duplicate names ({len(duplicates)}) — first STEP ID used for each:")
        for n in sorted(duplicates):
            print(f"    {n}")

    # ── Read extract and find top parent self-rows ────────────────────────────
    print(f"\nReading extract: {args.extract}")
    members       = []
    total_rows    = 0
    no_step_id    = []

    with open(args.extract, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            member_id   = row.get(COL_MEMBER_ID,   "").strip()
            system_id   = row.get(COL_SYSTEM_ID,   "").strip()
            system_name = row.get(COL_SYSTEM_NAME, "").strip()
            parent_id   = row.get(COL_PARENT_ID,   "").strip()

            # Only rows where Member ID == System ID (top parent self-row)
            if not (system_id and member_id and system_id == member_id):
                continue
            # Parent ID must be blank or equal to System ID
            if parent_id and parent_id != system_id:
                continue

            step_id = step_id_map.get(system_name.lower())
            if not step_id:
                no_step_id.append(f"{system_id} / {system_name}")
                continue

            lic        = safe(row.get(COL_LIC, ""))
            entity_key = lic if lic else member_id

            members.append({
                "<ID>":                        "",
                "<Name>":                      safe(row.get(COL_MEMBER_NAME, system_name)),
                "<Parent ID>":                 step_id,
                "<Object Type>":               STEP_OBJECT_TYPE,
                "gpo.GPO_Member_ID":           member_id,
                "gpo.GPO_Entity_Key":          entity_key,
                "gpo.LIC":                     lic,
                "gpo.GLN":                     safe_gln(row.get(COL_GLN, "")),
                "gpo.HIN":                     safe_gln(row.get(COL_HIN, "")),
                "gpo.Membership_Eligible_Date": parse_date(row.get(COL_MEMBER_DATE, "")),
                "gpo.Facility_Category":       safe(row.get(COL_FAC_CAT, "")),
                "gpo.Facility_Type":           safe(row.get(COL_FAC_TYPE, "")),
                "gpo.Rx_Group":                safe(row.get(COL_RX_GROUP, "")),
                "loc.Address_Country":         "US",
            })

    print(f"  Total rows read   : {total_rows:,}")
    print(f"  Members to create : {len(members):,}")
    if no_step_id:
        print(f"  No STEP ID found  : {len(no_step_id)}")
        for n in no_step_id[:10]:
            print(f"    {n}")
        if len(no_step_id) > 10:
            print(f"    ... and {len(no_step_id) - 10} more")

    # ── Write output CSV ──────────────────────────────────────────────────────
    with open(args.output, newline="", encoding="utf-8-sig", mode="w") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        writer.writeheader()
        writer.writerows(members)

    print(f"\n  Output written    : {args.output}")
    print("Done.\n")


if __name__ == "__main__":
    main()
