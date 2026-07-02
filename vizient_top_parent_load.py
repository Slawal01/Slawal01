"""
Vizient Top Parent STEPXML Generator
=====================================
Reads the Vizient source Excel file and generates a STEPXML file
containing only Top Parent entities for loading into Stibo STEP.

Top Parent Logic:
  System ID == Parent ID  (self-referencing rows)

Attributes loaded per top parent:
  - gpo.GPO_Member_ID  = System ID
  - gpo.GPO_Entity_Key = System ID  (same value)

IDs are NOT set — STEP auto-assigns them.

Usage:
  python vizient_top_parent_load.py
  python vizient_top_parent_load.py --input "path/to/file.xlsx" --output vizient_top_parents.xml
"""

import argparse
import csv
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime

# ── CONFIG ──────────────────────────────────────────────────────────────────
DEFAULT_INPUT  = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\Vizient week 10.15.2025.csv"
DEFAULT_OUTPUT = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\vizient_top_parents.xml"

# Vizient source column names
COL_MEMBER_ID   = "Member ID"
COL_SYSTEM_ID   = "System ID"
COL_SYSTEM_NAME = "System Name"
COL_PARENT_ID   = "Parent ID"

# STEP config
STEP_CONTEXT   = "Context1"
STEP_WORKSPACE = "Main"
STEP_PARENT    = "GPO_Vizient"       # Container node in STEP
STEP_TYPE      = "GPO_Top_Parent"    # Object Type ID
# ────────────────────────────────────────────────────────────────────────────


def build_xml(top_parents):
    root = ET.Element("STEP-ProductInformation")
    root.set("ExportTime",       datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    root.set("ContextID",        STEP_CONTEXT)
    root.set("WorkspaceID",      STEP_WORKSPACE)
    root.set("UseContextLocale", "false")

    entities_el = ET.SubElement(root, "Entities")

    for row in top_parents:
        system_id   = row[COL_SYSTEM_ID]
        system_name = row[COL_SYSTEM_NAME]

        el = ET.SubElement(entities_el, "Entity")
        # No ID attribute — STEP auto-assigns
        el.set("UserTypeID", STEP_TYPE)
        el.set("ParentID",   STEP_PARENT)

        ET.SubElement(el, "Name").text = system_name

        values_el = ET.SubElement(el, "Values")

        v1 = ET.SubElement(values_el, "Value")
        v1.set("AttributeID", "gpo.GPO_Member_ID")
        v1.text = system_id

        v2 = ET.SubElement(values_el, "Value")
        v2.set("AttributeID", "gpo.GPO_Entity_Key")
        v2.text = system_id

    # Pretty print using minidom (no lxml needed)
    xml_str = minidom.parseString(ET.tostring(root, encoding="unicode")).toprettyxml(indent="  ")
    return xml_str


def main():
    parser = argparse.ArgumentParser(description="Generate Vizient Top Parent STEPXML")
    parser.add_argument("--input",  default=DEFAULT_INPUT,  help="Path to Vizient source Excel file")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output STEPXML file path")
    args = parser.parse_args()

    print(f"\nReading: {args.input}")

    all_rows = []
    seen_ids = set()
    top_parents = []

    with open(args.input, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            all_rows.append(row)
            member_id   = row.get(COL_MEMBER_ID,   "").strip()
            system_id   = row.get(COL_SYSTEM_ID,   "").strip()
            parent_id   = row.get(COL_PARENT_ID,   "").strip()
            system_name = row.get(COL_SYSTEM_NAME, "").strip()

            # Top parent logic:
            #   System ID == Parent ID == Member ID  (all three match)
            #   OR System ID == Member ID            (Parent ID blank or same)
            is_top = (
                system_id and member_id and system_id == member_id and
                (parent_id == "" or parent_id == system_id)
            )

            if is_top and system_id not in seen_ids:
                # Reject blank or NA names
                if not system_name or system_name.upper() == "NA":
                    print(f"  REJECTED (no name): System ID {system_id}")
                    continue
                seen_ids.add(system_id)
                top_parents.append({COL_SYSTEM_ID: system_id, COL_SYSTEM_NAME: system_name})

    print(f"Total rows in file  : {len(all_rows):,}")
    print(f"Top parents found   : {len(top_parents):,}")

    xml_str = build_xml(top_parents)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(xml_str)

    print(f"Output written      : {args.output}")
    print(f"Done.\n")


if __name__ == "__main__":
    main()
