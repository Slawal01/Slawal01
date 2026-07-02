"""
Vizient Member Load - STEPXML Generator
========================================
Reads the Vizient source CSV and the STEP export CSV (containing top parent IDs),
then generates one STEPXML file per System ID for loading members into Stibo STEP.

Hierarchy logic:
  Top Parent   : Member ID == System ID (already in STEP — referenced by existing ID)
  Direct Parent: Parent ID != System ID AND Parent ID != Member ID
  Member       : Member ID != System ID AND (Parent ID == System ID OR Parent ID == Member ID)

Attributes loaded per member:
  gpo.GPO_Member_ID           = Member ID
  gpo.GPO_Entity_Key          = LIC if present, else Member ID
  gpo.LIC                     = LIC
  gpo.GLN                     = GLN
  gpo.HIN                     = HIN
  gpo.Membership_Eligible_Date = Member Date (DD-Mon-YYYY)
  gpo.Facility_Category       = Facility Category
  gpo.Facility_Type           = Facility Type
  gpo.Rx_Group                = Rx Group
  loc.Address_Country         = US

Usage:
  python vizient_member_load.py
  python vizient_member_load.py --vizient "path/to/vizient.csv" --step-export "path/to/export.csv" --output-dir "path/to/output"
"""

import argparse
import csv
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime

# ── CONFIG ───────────────────────────────────────────────────────────────────
DEFAULT_VIZIENT     = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\Vizient week 10.15.2025.csv"
DEFAULT_STEP_EXPORT = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\csv-2026-07-01_21.11.46.csv"
DEFAULT_OUTPUT_DIR  = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\vizient_members"
DEFAULT_OUTPUT_FILE = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\vizient_all_members.xml"

# Vizient source column names
COL_MEMBER_ID   = "Member ID"
COL_LIC         = "LIC"
COL_GLN         = "GLN"
COL_HIN         = "HIN"
COL_MEMBER_DATE = "Member Date"
COL_MEMBER_NAME = "Member Name"
COL_SYSTEM_ID   = "System ID"
COL_SYSTEM_NAME = "System Name"
COL_PARENT_ID   = "Parent ID"
COL_PARENT_NAME = "Parent Name"
COL_FAC_CAT     = "Facility Category"
COL_FAC_TYPE    = "Facility Type"
COL_RX_GROUP    = "Rx Group"

# STEP export column names
STEP_COL_ID        = "<ID>"
STEP_COL_MEMBER_ID = "GPO Member ID"

# STEP config
STEP_CONTEXT   = "Context1"
STEP_WORKSPACE = "Main"
STEP_PARENT    = "GPO_Vizient"
STEP_TYPE_TOP  = "GPO_Top_Parent"
STEP_TYPE_DP   = "GPO_Direct_Parent"
STEP_TYPE_MEM  = "GPO_Member"
# ─────────────────────────────────────────────────────────────────────────────


def safe(val):
    v = str(val).strip()
    return "" if v.lower() in ("nan", "none", "nat", "n/a", "na", "") else v


def safe_gln(val):
    """Handle GLN/HIN stored as float in scientific notation."""
    v = safe(val)
    if not v:
        return ""
    try:
        return str(int(float(v)))
    except (ValueError, OverflowError):
        return v


def parse_date(val):
    """Convert date to DD-Mon-YYYY (e.g. 12-Feb-2020)."""
    v = str(val).strip()
    if not v or v.lower() in ("nan", "none", "nat", ""):
        return ""
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%d-%b-%Y", "%d-%B-%Y", "%m-%d-%Y"):
        try:
            return datetime.strptime(v, fmt).strftime("%d-%b-%Y")
        except ValueError:
            pass
    return v


def add_value(values_el, attr_id, text):
    if text:
        v = ET.SubElement(values_el, "Value")
        v.set("AttributeID", attr_id)
        v.text = text


def add_member_values(values_el, row):
    member_id  = safe(row.get(COL_MEMBER_ID, ""))
    lic        = safe(row.get(COL_LIC, ""))
    entity_key = lic if lic else member_id

    add_value(values_el, "gpo.GPO_Member_ID",            member_id)
    add_value(values_el, "gpo.GPO_Entity_Key",           entity_key)
    add_value(values_el, "gpo.LIC",                      lic)
    add_value(values_el, "gpo.GLN",                      safe_gln(row.get(COL_GLN, "")))
    add_value(values_el, "gpo.HIN",                      safe_gln(row.get(COL_HIN, "")))
    add_value(values_el, "gpo.Membership_Eligible_Date", parse_date(row.get(COL_MEMBER_DATE, "")))
    add_value(values_el, "gpo.Facility_Category",        safe(row.get(COL_FAC_CAT, "")))
    add_value(values_el, "gpo.Facility_Type",            safe(row.get(COL_FAC_TYPE, "")))
    add_value(values_el, "gpo.Rx_Group",                 safe(row.get(COL_RX_GROUP, "")))
    add_value(values_el, "loc.Address_Country",          "US")


def build_system(entities_el, step_id, system_name, system_id, rows):
    """Add one system's top parent + members into an existing <Entities> element."""
    # Reference the existing top parent in STEP by its assigned ID
    top_el = ET.SubElement(entities_el, "Entity")
    top_el.set("ID",         step_id)
    top_el.set("UserTypeID", STEP_TYPE_TOP)
    top_el.set("ParentID",   STEP_PARENT)
    ET.SubElement(top_el, "Name").text = system_name

    # Bucket rows into direct parents vs. direct members
    direct_parents = {}   # parent_id -> {"name": str, "rows": []}
    direct_members = []

    for row in rows:
        member_id = safe(row.get(COL_MEMBER_ID, ""))
        parent_id = safe(row.get(COL_PARENT_ID, ""))

        # Skip the top parent row itself
        if member_id == system_id:
            continue

        is_dp = (
            parent_id != "" and
            parent_id != system_id and
            parent_id != member_id
        )

        if is_dp:
            if parent_id not in direct_parents:
                direct_parents[parent_id] = {
                    "name": safe(row.get(COL_PARENT_NAME, "")),
                    "rows": []
                }
            direct_parents[parent_id]["rows"].append(row)
        else:
            direct_members.append(row)

    # Emit direct parents with members nested inside
    for dp_id, dp_data in direct_parents.items():
        dp_el = ET.SubElement(top_el, "Entity")
        dp_el.set("UserTypeID", STEP_TYPE_DP)
        ET.SubElement(dp_el, "Name").text = dp_data["name"]

        dp_vals = ET.SubElement(dp_el, "Values")
        add_value(dp_vals, "gpo.GPO_Member_ID",  dp_id)
        add_value(dp_vals, "gpo.GPO_Entity_Key", dp_id)

        for row in dp_data["rows"]:
            mem_el = ET.SubElement(dp_el, "Entity")
            mem_el.set("UserTypeID", STEP_TYPE_MEM)
            ET.SubElement(mem_el, "Name").text = safe(row.get(COL_MEMBER_NAME, ""))
            mem_vals = ET.SubElement(mem_el, "Values")
            add_member_values(mem_vals, row)

    # Emit members that sit directly under the top parent
    for row in direct_members:
        mem_el = ET.SubElement(top_el, "Entity")
        mem_el.set("UserTypeID", STEP_TYPE_MEM)
        ET.SubElement(mem_el, "Name").text = safe(row.get(COL_MEMBER_NAME, ""))
        mem_vals = ET.SubElement(mem_el, "Values")
        add_member_values(mem_vals, row)


def main():
    parser = argparse.ArgumentParser(description="Generate Vizient Member STEPXML")
    parser.add_argument("--vizient",     default=DEFAULT_VIZIENT,     help="Vizient source CSV")
    parser.add_argument("--step-export", default=DEFAULT_STEP_EXPORT, help="STEP export CSV with top parent IDs")
    parser.add_argument("--output",      default=DEFAULT_OUTPUT_FILE, help="Output XML file path (single file mode)")
    parser.add_argument("--batches",     type=int, default=1,         help="Split output into N batch files (e.g. 5)")
    parser.add_argument("--system",      default=None,                help="Test mode: process only this System ID (e.g. 770471)")
    args = parser.parse_args()

    # ── Load STEP export: map System ID → STEP entity ID ────────────────────
    print(f"\nReading STEP export: {args.step_export}")
    step_id_map = {}
    with open(args.step_export, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            step_id   = row.get(STEP_COL_ID,        "").strip()
            member_id = row.get(STEP_COL_MEMBER_ID, "").strip()
            if step_id and member_id:
                step_id_map[member_id] = step_id
    print(f"  Top parents mapped: {len(step_id_map):,}")

    # ── Read Vizient CSV and group by System ID ──────────────────────────────
    print(f"\nReading Vizient CSV: {args.vizient}")
    systems    = {}   # system_id -> {"name": str, "rows": []}
    total_rows = 0
    skipped    = 0

    if args.system:
        print(f"  TEST MODE: filtering to System ID = {args.system}")

    with open(args.vizient, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            system_id   = row.get(COL_SYSTEM_ID,   "").strip()
            system_name = row.get(COL_SYSTEM_NAME, "").strip()

            if not system_id:
                skipped += 1
                continue

            if args.system and system_id != args.system:
                continue

            if system_id not in systems:
                systems[system_id] = {"name": system_name, "rows": []}
            systems[system_id]["rows"].append(row)

    print(f"  Total rows    : {total_rows:,}")
    print(f"  Skipped (no system ID): {skipped:,}")
    print(f"  Unique systems: {len(systems):,}")

    # ── Build list of (step_id, name, system_id, rows) to process ───────────
    no_step_id = []
    work_items = []

    for system_id, data in systems.items():
        step_id = step_id_map.get(system_id)
        if not step_id:
            no_step_id.append(system_id)
            continue
        work_items.append((step_id, data["name"], system_id, data["rows"]))

    total = len(work_items)
    print(f"\nSystems to write    : {total:,}")
    if no_step_id:
        print(f"Systems with no STEP ID ({len(no_step_id)}): "
              f"{no_step_id[:10]}{'...' if len(no_step_id) > 10 else ''}")
        print("  (These systems are not yet loaded as top parents in STEP)")

    # ── Split into batches and write ─────────────────────────────────────────
    n_batches   = max(1, args.batches)
    batch_size  = (total + n_batches - 1) // n_batches  # ceiling division
    base, ext   = os.path.splitext(args.output)

    for b in range(n_batches):
        chunk = work_items[b * batch_size : (b + 1) * batch_size]
        if not chunk:
            break

        root = ET.Element("STEP-ProductInformation")
        root.set("ExportTime",       datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        root.set("ContextID",        STEP_CONTEXT)
        root.set("WorkspaceID",      STEP_WORKSPACE)
        root.set("UseContextLocale", "false")
        entities_el = ET.SubElement(root, "Entities")

        for step_id, name, system_id, rows in chunk:
            build_system(entities_el, step_id, name, system_id, rows)

        if n_batches == 1:
            out_path = args.output
        else:
            out_path = f"{base}_batch{b + 1}{ext}"

        print(f"  Writing batch {b + 1}/{n_batches} ({len(chunk)} systems) → {os.path.basename(out_path)}")
        xml_str = minidom.parseString(ET.tostring(root, encoding="unicode")).toprettyxml(indent="  ")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(xml_str)

    print("Done.\n")


if __name__ == "__main__":
    main()
