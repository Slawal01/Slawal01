"""
Premier Member CSV Import Generator
=====================================
Reads Premier complete data CSV and generates a STEP-compatible CSV
import file for GPO_Member entities.

Member logic:
  All rows that are NOT top parents and NOT direct parents.
  - Top parent:    GPO ID == Top Parent GPO ID AND Direct Parent GPO ID blank
  - Direct parent: Direct Parent GPO ID != blank AND Direct Parent GPO ID != Top Parent GPO ID
                   AND Direct Parent GPO ID != GPO ID
  - Member:        everything else

Parent ID lookup:
  Top parents    : premier_top_parents_step.csv   (Name -> STEP ID)
  Direct parents : premier_direct_parents_step.csv (Name + Top Parent STEP ID -> STEP ID)

Output columns:
  <ID>                            blank (STEP auto-assigns)
  <Name>                          Name 1 (or Override Name if present)
  <Parent ID>                     Top Parent or Direct Parent STEP ID
  <Object Type>                   GPO_Member
  gpo.GPO_Member_ID               GPO ID
  gpo.GPO_Entity_Key              Address ID
  gpo.Address_ID                  Address ID
  gpo.GLN                         GLN
  gpo.HIN                         Health Industry Number (HIN)
  gpo.Membership_Eligible_Date    Membership Start Date
  gpo.Member_Status               Member Status
  gpo.Class_of_Trade              Class of Trade
  gpo.Relationship_To_Top_Parent  Relationship to Top Parent
  gpo.Relationship_To_Direct_Parent Relationship to Direct Parent
  gpo.Override_Name               Override Name
  gpo.Committed_Program_Eligibility Committed Program Eligibility
  gpo.Aggregation_Affiliation_1   Aggregation Affiliation 1
  gpo.Affiliation_Start_Date_1    Affiliation Start Date 1
  gpo.Affiliation_End_Date_1      Affiliation End Date 1
  gpo.Aggregation_Affiliation_2   Aggregation Affiliation 2
  gpo.Affiliation_Start_Date_2    Affiliation Start Date 2
  gpo.Affiliation_End_Date_2      Affiliation End Date 2
  gpo.Aggregation_Affiliation_3   Aggregation Affiliation 3
  gpo.Affiliation_Start_Date_3    Affiliation Start Date 3
  gpo.Affiliation_End_Date_3      Affiliation End Date 3
  loc.PhoneNumber                 Phone
  loc.Address_Line_1              Address 1
  loc.Address_Line_2              Address 2
  loc.Address_Line_3              Address 3
  loc.Address_City                City
  loc.Address_State               State/Province
  loc.Address_Postal_Code         Postal Code
  loc.Address_Country             Country

Usage:
  py premier_member_csv.py
"""

import argparse
import csv
from datetime import datetime

DEFAULT_INPUT     = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\Premier complete data.csv"
DEFAULT_PARENTS   = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\STEP Parent id for level 1 and 2.csv"
DEFAULT_OUTPUT    = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\premier_members_import.csv"

COL_GPO_ID       = "GPO ID"
COL_ADDRESS_ID   = "Address ID"
COL_ADDRESS_TYPE = "Address Type"
COL_NAME1        = "Name 1"
COL_OVERRIDE     = "Override Name"
COL_GLN          = "GLN"
COL_HIN          = "Health Industry Number (HIN)"
COL_MEM_DATE     = "Membership Start Date"
COL_MEM_STATUS   = "Member Status"
COL_COT          = "Class of Trade"
COL_REL_TOP      = "Relationship to Top Parent"
COL_REL_DP       = "Relationship to Direct Parent"
COL_PHONE        = "Phone"
COL_ADDR1        = "Address 1"
COL_ADDR2        = "Address 2"
COL_ADDR3        = "Address 3"
COL_CITY         = "City"
COL_STATE        = "State/Province"
COL_ZIP          = "Postal Code"
COL_COUNTRY      = "Country"
COL_TOP_ID       = "Top Parent GPO ID"
COL_TOP_NAME     = "Top Parent Name 1"
COL_DP_ID        = "Direct Parent GPO ID"
COL_DP_NAME      = "Direct Parent Name 1"
COL_COMMITTED    = "Committed Program Eligibility"
COL_AFF1         = "Aggregation Affiliation 1"
COL_AFF1_START   = "Affiliation Start Date 1"
COL_AFF1_END     = "Affiliation End Date 1"
COL_AFF2         = "Aggregation Affiliation 2"
COL_AFF2_START   = "Affiliation Start Date 2"
COL_AFF2_END     = "Affiliation End Date 2"
COL_AFF3         = "Aggregation Affiliation 3"
COL_AFF3_START   = "Affiliation Start Date 3"
COL_AFF3_END     = "Affiliation End Date 3"
COL_COMMITTED    = "Committed Program Eligibility"
COL_AFF1         = "Aggregation Affiliation 1"
COL_AFF1_START   = "Affiliation Start Date 1"
COL_AFF1_END     = "Affiliation End Date 1"
COL_AFF2         = "Aggregation Affiliation 2"
COL_AFF2_START   = "Affiliation Start Date 2"
COL_AFF2_END     = "Affiliation End Date 2"
COL_AFF3         = "Aggregation Affiliation 3"
COL_AFF3_START   = "Affiliation Start Date 3"
COL_AFF3_END     = "Affiliation End Date 3"

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
    "gpo.Override_Name",
    "gpo.Committed_Program_Eligibility",
    "gpo.Aggregation_Affiliation_1",
    "gpo.Affiliation_Start_Date_1",
    "gpo.Affiliation_End_Date_1",
    "gpo.Aggregation_Affiliation_2",
    "gpo.Affiliation_Start_Date_2",
    "gpo.Affiliation_End_Date_2",
    "gpo.Aggregation_Affiliation_3",
    "gpo.Affiliation_Start_Date_3",
    "gpo.Affiliation_End_Date_3",
    "loc.PhoneNumber",
    "loc.Address_Line_1",
    "loc.Address_Line_2",
    "loc.Address_Line_3",
    "loc.Address_City",
    "loc.Address_State",
    "loc.Address_Postal_Code",
    "loc.Address_Country",
]


def safe(val):
    v = str(val).strip()
    return "" if v.lower() in ("nan", "none", "nat", "n/a", "na") else v


COUNTRY_MAP = {
    "usa": "US", "united states": "US", "united states of america": "US", "u.s.a.": "US", "u.s.": "US",
    "can": "CA", "canada": "CA",
    "mex": "MX", "mexico": "MX",
    "gbr": "GB", "united kingdom": "GB", "uk": "GB", "great britain": "GB",
    "aus": "AU", "australia": "AU",
    "deu": "DE", "germany": "DE",
    "fra": "FR", "france": "FR",
    "ind": "IN", "india": "IN",
    "chn": "CN", "china": "CN",
    "jpn": "JP", "japan": "JP",
    "bra": "BR", "brazil": "BR",
}


def normalize_country(val):
    v = safe(val)
    if not v:
        return ""
    lookup = v.lower().strip(".")
    return COUNTRY_MAP.get(lookup, v)


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
    parser = argparse.ArgumentParser(description="Generate Premier Member CSV for STEP import")
    parser.add_argument("--input",   default=DEFAULT_INPUT,   help="Premier complete data CSV")
    parser.add_argument("--parents", default=DEFAULT_PARENTS, help="STEP export with level 1 and 2 IDs")
    parser.add_argument("--output",  default=DEFAULT_OUTPUT,  help="Output CSV file path")
    args = parser.parse_args()

    # ── Load parent maps ──────────────────────────────────────────────────────
    print(f"\nReading parent IDs: {args.parents}")
    tp_map, dp_map = load_parent_maps(args.parents)
    print(f"  Top parents mapped    : {len(tp_map):,}")
    print(f"  Direct parents mapped : {len(dp_map):,}")

    # ── Read Premier data and build member rows ───────────────────────────────
    print(f"\nReading: {args.input}")
    members      = []
    total_rows   = 0
    no_tp        = []
    no_dp        = []

    with open(args.input, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            total_rows += 1
            gpo_id     = row.get(COL_GPO_ID,  "").strip()
            top_id     = row.get(COL_TOP_ID,  "").strip()
            top_name   = row.get(COL_TOP_NAME,"").strip()
            dp_id      = row.get(COL_DP_ID,   "").strip()
            dp_name    = row.get(COL_DP_NAME, "").strip()
            address_id = row.get(COL_ADDRESS_ID, "").strip()

            if not gpo_id:
                continue

            # Skip top parents (they are level 1)
            if gpo_id == top_id and dp_id == "":
                continue

            # Determine <Parent ID>
            if dp_id and dp_id != top_id and dp_id != gpo_id:
                # Member sits under a direct parent (level 2)
                step_parent_id = name_match(dp_name, dp_map)
                if not step_parent_id:
                    no_dp.append(f"{gpo_id} / {dp_id} / {dp_name}")
                    continue
            else:
                # Member sits directly under top parent (level 1)
                step_parent_id = name_match(top_name, tp_map)
                if not step_parent_id:
                    no_tp.append(f"{gpo_id} / {top_name}")
                    continue

            override = safe(row.get(COL_OVERRIDE, ""))
            name     = override if override else safe(row.get(COL_NAME1, ""))

            members.append({
                "<ID>":                           "",
                "<Name>":                         name,
                "<Parent ID>":                    step_parent_id,
                "<Object Type>":                  STEP_OBJECT_TYPE,
                "gpo.GPO_Member_ID":              gpo_id,
                "gpo.GPO_Entity_Key":             address_id,
                "gpo.Address_ID":                 address_id,
                "gpo.Address_Type":               safe(row.get(COL_ADDRESS_TYPE, "")),
                "gpo.GLN":                        safe_gln(row.get(COL_GLN, "")),
                "gpo.HIN":                        safe(row.get(COL_HIN, "")),
                "gpo.Membership_Eligible_Date":   parse_date(row.get(COL_MEM_DATE, "")),
                "gpo.Member_Status":              safe(row.get(COL_MEM_STATUS, "")),
                "gpo.Class_of_Trade":             safe(row.get(COL_COT, "")),
                "gpo.Relationship_To_Top_Parent": safe(row.get(COL_REL_TOP, "")),
                "gpo.Relationship_To_Direct_Parent": safe(row.get(COL_REL_DP, "")),
                "gpo.Override_Name":              override,
                "gpo.Committed_Program_Eligibility": safe(row.get(COL_COMMITTED, "")),
                "gpo.Aggregation_Affiliation_1":  safe(row.get(COL_AFF1, "")),
                "gpo.Affiliation_Start_Date_1":   parse_date(row.get(COL_AFF1_START, "")),
                "gpo.Affiliation_End_Date_1":     parse_date(row.get(COL_AFF1_END, "")),
                "gpo.Aggregation_Affiliation_2":  safe(row.get(COL_AFF2, "")),
                "gpo.Affiliation_Start_Date_2":   parse_date(row.get(COL_AFF2_START, "")),
                "gpo.Affiliation_End_Date_2":     parse_date(row.get(COL_AFF2_END, "")),
                "gpo.Aggregation_Affiliation_3":  safe(row.get(COL_AFF3, "")),
                "gpo.Affiliation_Start_Date_3":   parse_date(row.get(COL_AFF3_START, "")),
                "gpo.Affiliation_End_Date_3":     parse_date(row.get(COL_AFF3_END, "")),
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

    # ── Write output CSV ──────────────────────────────────────────────────────
    with open(args.output, newline="", encoding="utf-8-sig", mode="w") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        writer.writeheader()
        writer.writerows(members)

    print(f"\n  Output written     : {args.output}")
    print("Done.\n")


if __name__ == "__main__":
    main()
