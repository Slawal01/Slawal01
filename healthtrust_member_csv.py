"""
HealthTrust Member CSV Import Generator
=========================================
Reads HealthTrust deduped CSV and generates a STEP-compatible CSV
import file for GPO_Member entities.

Member logic:
  All rows. Parent resolved as:
  - If Direct Parent GPOID != blank AND != Top Parent GPOID AND != GPOID
      -> parent is Direct Parent STEP ID
  - Otherwise -> parent is Top Parent STEP ID

Output columns:
  <ID>                              blank (STEP auto-assigns)
  <Name>                            Name1
  <Parent ID>                       Top Parent or Direct Parent STEP ID
  <Object Type>                     GPO_Member
  gpo.GPO_Member_ID                 GPOID
  gpo.GPO_Entity_Key                COID
  gpo.Address_ID                    COID
  gpo.Address_Type                  Address Type
  gpo.GLN                           GLN
  gpo.HIN                           Health Industry Number (HIN)
  gpo.Membership_Eligible_Date      Membership Eligible Date
  gpo.Member_Status                 Member Status
  gpo.Class_of_Trade                Class of Trade
  gpo.Relationship_To_Top_Parent    Relationship to GPO
  gpo.Relationship_To_Direct_Parent Relationship to Direct Parent
  loc.PhoneNumber                   Phone
  loc.Address_Line_1                Address1
  loc.Address_Line_2                Address2
  loc.Address_Line_3                Address3
  loc.Address_City                  City
  loc.Address_State                 State/Province
  loc.Address_Postal_Code           Postal Code
  loc.Address_Country               Country

Usage:
  py healthtrust_member_csv.py
"""

import argparse
import csv
from datetime import datetime

DEFAULT_INPUT   = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\HealthTrust deduped.csv"
DEFAULT_PARENTS = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\HealthTrust STEP Parent id for level 1 and 2.csv"
DEFAULT_OUTPUT  = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\healthtrust_members_import.csv"

COL_GPOID    = "GPOID"
COL_COID     = "COID"
COL_NAME1    = " Name1"
COL_ADDR_TYPE= "Address Type"
COL_GLN      = "GLN"
COL_HIN      = "Health Industry Number (HIN)"
COL_MEM_DATE = "Membership Eligible Date"
COL_STATUS   = "Member Status"
COL_COT      = "Class of Trade"
COL_REL_TOP  = "Relationship to GPO "
COL_REL_DP   = "Relationship to Direct Parent"
COL_PHONE    = "Phone"
COL_ADDR1    = "Address1"
COL_ADDR2    = "Address2"
COL_ADDR3    = "Address3"
COL_CITY     = "City"
COL_STATE    = "State/Province"
COL_ZIP      = "Postal Code"
COL_COUNTRY  = "Country"
COL_TOP_ID   = "Top Parent GPOID"
COL_TOP_NAME = "Top Parent Name 1"
COL_DP_ID    = "Direct Parent GPOID"
COL_DP_NAME  = "Direct Parent Name1"

STEP_OBJECT_TYPE = "GPO_Member"

OUT_FIELDS = [
    "<ID>",
    "<Name>",
    "<Parent ID>",
    "<Object Type>",
    "gpo.GPO_Member_ID",
    "gpo.GPO_Entity_Key",
    "gpo.Address_ID",
    "gpo.Address_Type",
    "gpo.GLN",
    "gpo.HIN",
    "gpo.Membership_Eligible_Date",
    "gpo.Member_Status",
    "gpo.Class_of_Trade",
    "gpo.Relationship_To_Top_Parent",
    "gpo.Relationship_To_Direct_Parent",
    "loc.PhoneNumber",
    "loc.Address_Line_1",
    "loc.Address_Line_2",
    "loc.Address_Line_3",
    "loc.Address_City",
    "loc.Address_State",
    "loc.Address_Postal_Code",
    "loc.Address_Country",
]

COUNTRY_MAP = {
    "usa": "US", "united states": "US", "united states of america": "US", "u.s.a.": "US", "u.s.": "US",
    "can": "CA", "canada": "CA",
    "mex": "MX", "mexico": "MX",
    "gbr": "GB", "united kingdom": "GB", "uk": "GB",
    "aus": "AU", "australia": "AU",
    "deu": "DE", "germany": "DE",
    "fra": "FR", "france": "FR",
    "ind": "IN", "india": "IN",
    "chn": "CN", "china": "CN",
    "jpn": "JP", "japan": "JP",
    "bra": "BR", "brazil": "BR",
}


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


def normalize_country(val):
    v = safe(val)
    if not v:
        return ""
    return COUNTRY_MAP.get(v.lower().strip("."), v)


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


def load_parent_maps(path):
    """Load combined STEP export into tp_map and dp_map keyed by name (lower)."""
    tp_map = {}
    dp_map = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            obj_type = row.get("<Object Type Name>", "").strip().lower()
            step_id  = row.get("<ID>",   "").strip()
            name     = row.get("<Name>", "").strip()
            if not step_id or not name:
                continue
            key = name.lower()
            if "top parent" in obj_type:
                tp_map[key] = step_id
            elif "direct parent" in obj_type:
                dp_map[key] = step_id
    return tp_map, dp_map


def name_match(name, lookup_map):
    """Exact then prefix match."""
    key = name.lower().strip()
    if key in lookup_map:
        return lookup_map[key]
    for f, step_id in lookup_map.items():
        if key.startswith(f) or f.startswith(key):
            return step_id
    return None


def main():
    parser = argparse.ArgumentParser(description="Generate HealthTrust Member CSV for STEP import")
    parser.add_argument("--input",   default=DEFAULT_INPUT,   help="HealthTrust deduped CSV")
    parser.add_argument("--parents", default=DEFAULT_PARENTS, help="STEP export with level 1 and 2 IDs")
    parser.add_argument("--output",  default=DEFAULT_OUTPUT,  help="Output CSV file path")
    args = parser.parse_args()

    # ── Load parent maps ──────────────────────────────────────────────────────
    print(f"\nReading parent IDs: {args.parents}")
    tp_map, dp_map = load_parent_maps(args.parents)
    print(f"  Top parents mapped    : {len(tp_map):,}")
    print(f"  Direct parents mapped : {len(dp_map):,}")

    # ── Read data and build member rows ───────────────────────────────────────
    print(f"\nReading: {args.input}")
    members    = []
    total_rows = 0
    no_tp      = []
    no_dp      = []

    with open(args.input, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            total_rows += 1
            gpoid    = row.get(COL_GPOID,    "").strip()
            coid     = row.get(COL_COID,     "").strip()
            top_id   = row.get(COL_TOP_ID,   "").strip()
            top_name = row.get(COL_TOP_NAME, "").strip()
            dp_id    = row.get(COL_DP_ID,    "").strip()
            dp_name  = row.get(COL_DP_NAME,  "").strip()

            if not gpoid:
                continue

            # Determine <Parent ID>
            if dp_id and dp_id != top_id and dp_id != gpoid:
                step_parent_id = name_match(dp_name, dp_map)
                if not step_parent_id:
                    no_dp.append(f"{gpoid} / {dp_id} / {dp_name}")
                    continue
            else:
                step_parent_id = name_match(top_name, tp_map)
                if not step_parent_id:
                    no_tp.append(f"{gpoid} / {top_name}")
                    continue

            name = safe(row.get(COL_NAME1, ""))

            members.append({
                "<ID>":                           "",
                "<Name>":                         name,
                "<Parent ID>":                    step_parent_id,
                "<Object Type>":                  STEP_OBJECT_TYPE,
                "gpo.GPO_Member_ID":              gpoid,
                "gpo.GPO_Entity_Key":             coid,
                "gpo.Address_ID":                 coid,
                "gpo.Address_Type":               safe(row.get(COL_ADDR_TYPE, "")),
                "gpo.GLN":                        safe_gln(row.get(COL_GLN, "")),
                "gpo.HIN":                        safe(row.get(COL_HIN, "")),
                "gpo.Membership_Eligible_Date":   parse_date(row.get(COL_MEM_DATE, "")),
                "gpo.Member_Status":              safe(row.get(COL_STATUS, "")),
                "gpo.Class_of_Trade":             safe(row.get(COL_COT, "")),
                "gpo.Relationship_To_Top_Parent": safe(row.get(COL_REL_TOP, "")),
                "gpo.Relationship_To_Direct_Parent": safe(row.get(COL_REL_DP, "")),
                "loc.PhoneNumber":                safe(row.get(COL_PHONE, "")),
                "loc.Address_Line_1":             safe(row.get(COL_ADDR1, "")),
                "loc.Address_Line_2":             safe(row.get(COL_ADDR2, "")),
                "loc.Address_Line_3":             safe(row.get(COL_ADDR3, "")),
                "loc.Address_City":               safe(row.get(COL_CITY, "")),
                "loc.Address_State":              safe(row.get(COL_STATE, "")),
                "loc.Address_Postal_Code":        safe(row.get(COL_ZIP, "")),
                "loc.Address_Country":            normalize_country(row.get(COL_COUNTRY, "")),
            })

    print(f"  Total rows read    : {total_rows:,}")
    print(f"  Members to create  : {len(members):,}")
    if no_tp:
        no_tp_uniq = sorted(set(no_tp))
        print(f"  No top parent STEP ID ({len(no_tp_uniq)}):")
        for n in no_tp_uniq[:10]:
            print(f"    {n}")
        if len(no_tp_uniq) > 10:
            print(f"    ... and {len(no_tp_uniq) - 10} more")
    if no_dp:
        print(f"  No direct parent STEP ID ({len(no_dp)}):")
        for n in no_dp[:10]:
            print(f"    {n}")
        if len(no_dp) > 10:
            print(f"    ... and {len(no_dp) - 10} more")

    with open(args.output, newline="", encoding="utf-8-sig", mode="w") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        writer.writeheader()
        writer.writerows(members)

    print(f"\n  Output written     : {args.output}")
    print("Done.\n")


if __name__ == "__main__":
    main()
