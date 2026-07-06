"""
Vizient Member CSV Import Generator
=====================================
Reads vizient_customers_extract.csv and generates a STEP-compatible CSV
import file for GPO_Member entities.

Member logic:
  Member ID != System ID
  If Parent ID == System ID  -> member sits under top parent
  If Parent ID != System ID  -> member sits under direct parent

Parent ID lookup:
  Top parent    : STEP Parent ID Vizient.csv        (Name -> STEP ID)
  Direct parent : Direct Parent ID in STEP.csv      (Name + Top Parent STEP ID -> STEP ID)

Output columns:
  <ID>                          blank (STEP auto-assigns)
  <Name>                        Member Name
  <Parent ID>                   Top Parent or Direct Parent STEP ID
  <Object Type>                 GPO_Member
  gpo.GPO_Member_ID             Member ID
  gpo.GPO_Entity_Key            LIC if present, else Member ID
  gpo.LIC                       LIC
  gpo.GLN                       GLN
  gpo.HIN                       HIN
  gpo.Membership_Eligible_Date  Member Date (DD-Mon-YYYY)
  gpo.Facility_Category         Facility Category
  gpo.Facility_Type             Facility Type
  gpo.Rx_Group                  Rx Group
  gpo.Supply_Program            Supply Program
  gpo.AMC_Tier_Pricing          AMC Tier Pricing
  gpo.Vizient_Group_1           Vizient Group 1
  gpo.Vizient_Group_2           Vizient Group 2
  gpo.Vizient_Group_3           Vizient Group 3
  loc.Address_Line_1            Address1
  loc.Address_Line_2            Address2
  loc.Address_City              City
  loc.Address_State             State
  loc.Address_Postal_Code       Zip Code
  loc.Address_Country           US

Usage:
  py vizient_member_csv.py
"""

import argparse
import csv
from datetime import datetime

DEFAULT_EXTRACT    = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\vizient_customers_extract.csv"
DEFAULT_TOP_EXPORT = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\STEP Parent ID Vizient.csv"
DEFAULT_DP_EXPORT  = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\Direct Parent ID in STEP.csv"
DEFAULT_OUTPUT     = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\vizient_members_import.csv"

# Vizient extract columns
COL_MEMBER_ID   = "Member ID"
COL_MEMBER_NAME = "Member Name"
COL_LIC         = "LIC"
COL_GLN         = "GLN"
COL_HIN         = "HIN"
COL_MEMBER_DATE = "Member Date"
COL_SYSTEM_ID   = "System ID"
COL_SYSTEM_NAME = "System Name"
COL_PARENT_ID   = "Parent ID"
COL_PARENT_NAME = "Parent Name"
COL_ADDRESS1    = "Address1"
COL_ADDRESS2    = "Address2"
COL_CITY        = "City"
COL_STATE       = "State"
COL_ZIP         = "Zip Code"
COL_FAC_CAT     = "Facility Category"
COL_FAC_TYPE    = "Facility Type"
COL_RX_GROUP    = "Rx Group"
COL_SUPPLY_PGM  = "Supply Program"
COL_AMC_TIER    = "AMC Tier Pricing"
COL_VIZ_GRP1    = "Vizient Group 1"
COL_VIZ_GRP2    = "Vizient Group 2"
COL_VIZ_GRP3    = "Vizient Group 3"

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
    "gpo.Supply_Program",
    "gpo.AMC_Tier_Pricing",
    "gpo.Vizient_Group_1",
    "gpo.Vizient_Group_2",
    "gpo.Vizient_Group_3",
    "loc.Address_Line_1",
    "loc.Address_Line_2",
    "loc.Address_City",
    "loc.Address_State",
    "loc.Address_Postal_Code",
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
    parser = argparse.ArgumentParser(description="Generate Vizient Member CSV for STEP import")
    parser.add_argument("--extract",    default=DEFAULT_EXTRACT,    help="vizient_customers_extract.csv")
    parser.add_argument("--top-export", default=DEFAULT_TOP_EXPORT, help="STEP export CSV with top parent IDs")
    parser.add_argument("--dp-export",  default=DEFAULT_DP_EXPORT,  help="STEP export CSV with direct parent IDs")
    parser.add_argument("--output",     default=DEFAULT_OUTPUT,     help="Output CSV file path")
    args = parser.parse_args()

    # ── Load top parent map: system_name (lower) -> STEP ID ──────────────────
    print(f"\nReading top parent export: {args.top_export}")
    top_map    = {}
    tp_dupes   = set()
    with open(args.top_export, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            step_id = row.get("<ID>",   "").strip()
            name    = row.get("<Name>", "").strip().lower()
            if not step_id or not name:
                continue
            if name in top_map:
                tp_dupes.add(name)
            else:
                top_map[name] = step_id
    print(f"  Top parents mapped : {len(top_map):,}")
    if tp_dupes:
        print(f"  Duplicate top parent names ({len(tp_dupes)}) — first ID used:")
        for n in sorted(tp_dupes):
            print(f"    {n}")

    # ── Load direct parent map: (name lower, top_parent_step_id) -> STEP ID ──
    print(f"\nReading direct parent export: {args.dp_export}")
    dp_map   = {}
    dp_dupes = set()
    with open(args.dp_export, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            step_id   = row.get("<ID>",        "").strip()
            name      = row.get("<Name>",      "").strip().lower()
            parent_id = row.get("<Parent ID>", "").strip()
            if not step_id or not name:
                continue
            key = (name, parent_id)
            if key in dp_map:
                dp_dupes.add(name)
            else:
                dp_map[key] = step_id
    print(f"  Direct parents mapped : {len(dp_map):,}")
    if dp_dupes:
        print(f"  Duplicate direct parent names ({len(dp_dupes)}) — first ID used:")
        for n in sorted(dp_dupes):
            print(f"    {n}")

    # ── Read extract and build member rows ────────────────────────────────────
    print(f"\nReading extract: {args.extract}")
    members        = []
    total_rows     = 0
    no_top_step    = []
    no_dp_step     = []

    with open(args.extract, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            total_rows += 1
            member_id   = row.get(COL_MEMBER_ID,   "").strip()
            system_id   = row.get(COL_SYSTEM_ID,   "").strip()
            system_name = row.get(COL_SYSTEM_NAME, "").strip()
            parent_id   = row.get(COL_PARENT_ID,   "").strip()
            parent_name = row.get(COL_PARENT_NAME, "").strip()

            if not member_id or not system_id:
                continue

            # Skip top parent self-rows (handled by vizient_top_parent_members_csv.py)
            if member_id == system_id:
                continue

            # Resolve top parent STEP ID
            top_step_id = top_map.get(system_name.lower())
            if not top_step_id:
                no_top_step.append(f"{system_id} / {system_name}")
                continue

            # Determine <Parent ID>
            if not parent_id or parent_id == system_id:
                # Member sits directly under top parent
                step_parent_id = top_step_id
            else:
                # Member sits under a direct parent
                dp_key = (parent_name.lower(), top_step_id)
                step_parent_id = dp_map.get(dp_key)
                if not step_parent_id:
                    no_dp_step.append(f"{member_id} / {parent_id} / {parent_name}")
                    continue

            lic        = safe(row.get(COL_LIC, ""))
            entity_key = lic if lic else member_id

            members.append({
                "<ID>":                         "",
                "<Name>":                       safe(row.get(COL_MEMBER_NAME, "")),
                "<Parent ID>":                  step_parent_id,
                "<Object Type>":                STEP_OBJECT_TYPE,
                "gpo.GPO_Member_ID":            member_id,
                "gpo.GPO_Entity_Key":           entity_key,
                "gpo.LIC":                      lic,
                "gpo.GLN":                      safe_gln(row.get(COL_GLN, "")),
                "gpo.HIN":                      safe_gln(row.get(COL_HIN, "")),
                "gpo.Membership_Eligible_Date": parse_date(row.get(COL_MEMBER_DATE, "")),
                "gpo.Facility_Category":        safe(row.get(COL_FAC_CAT, "")),
                "gpo.Facility_Type":            safe(row.get(COL_FAC_TYPE, "")),
                "gpo.Rx_Group":                 safe(row.get(COL_RX_GROUP, "")),
                "gpo.Supply_Program":           safe(row.get(COL_SUPPLY_PGM, "")),
                "gpo.AMC_Tier_Pricing":         safe(row.get(COL_AMC_TIER, "")),
                "gpo.Vizient_Group_1":          safe(row.get(COL_VIZ_GRP1, "")),
                "gpo.Vizient_Group_2":          safe(row.get(COL_VIZ_GRP2, "")),
                "gpo.Vizient_Group_3":          safe(row.get(COL_VIZ_GRP3, "")),
                "loc.Address_Line_1":           safe(row.get(COL_ADDRESS1, "")),
                "loc.Address_Line_2":           safe(row.get(COL_ADDRESS2, "")),
                "loc.Address_City":             safe(row.get(COL_CITY, "")),
                "loc.Address_State":            safe(row.get(COL_STATE, "")),
                "loc.Address_Postal_Code":      safe(row.get(COL_ZIP, "")),
                "loc.Address_Country":          "US",
            })

    print(f"  Total rows read    : {total_rows:,}")
    print(f"  Members to create  : {len(members):,}")
    if no_top_step:
        no_top_step_uniq = sorted(set(no_top_step))
        print(f"  No top parent STEP ID ({len(no_top_step_uniq)}):")
        for n in no_top_step_uniq[:10]:
            print(f"    {n}")
        if len(no_top_step_uniq) > 10:
            print(f"    ... and {len(no_top_step_uniq) - 10} more")
    if no_dp_step:
        print(f"  No direct parent STEP ID ({len(no_dp_step)}):")
        for n in no_dp_step[:10]:
            print(f"    {n}")
        if len(no_dp_step) > 10:
            print(f"    ... and {len(no_dp_step) - 10} more")

    # ── Write output CSV ──────────────────────────────────────────────────────
    with open(args.output, newline="", encoding="utf-8-sig", mode="w") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        writer.writeheader()
        writer.writerows(members)

    print(f"\n  Output written     : {args.output}")
    print("Done.\n")


if __name__ == "__main__":
    main()
