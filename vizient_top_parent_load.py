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
import pandas as pd
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime

# ── CONFIG ──────────────────────────────────────────────────────────────────
DEFAULT_INPUT  = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\Vizient week 10.15.2025.xlsx"
DEFAULT_OUTPUT = "vizient_top_parents.xml"

# Vizient source column names
COL_SYSTEM_ID   = "System ID"
COL_SYSTEM_NAME = "System Name"
COL_PARENT_ID   = "Parent ID"

# STEP config
STEP_CONTEXT   = "Context1"
STEP_WORKSPACE = "Main"
STEP_PARENT    = "GPO_Vizient"       # Container node in STEP
STEP_TYPE      = "GPO_Top_Parent"    # Object Type ID
# ────────────────────────────────────────────────────────────────────────────


def build_xml(df_top):
    root = ET.Element("STEP-ProductInformation")
    root.set("ExportTime",       datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    root.set("ContextID",        STEP_CONTEXT)
    root.set("WorkspaceID",      STEP_WORKSPACE)
    root.set("UseContextLocale", "false")

    entities_el = ET.SubElement(root, "Entities")

    for _, row in df_top.iterrows():
        system_id   = str(row[COL_SYSTEM_ID]).strip()
        system_name = str(row[COL_SYSTEM_NAME]).strip()

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
    df = pd.read_excel(args.input, dtype=str)
    df = df.fillna("")

    # Normalize
    df[COL_SYSTEM_ID]  = df[COL_SYSTEM_ID].str.strip()
    df[COL_PARENT_ID]  = df[COL_PARENT_ID].str.strip()

    # Top parent logic: System ID == Parent ID
    df_top = df[df[COL_SYSTEM_ID] == df[COL_PARENT_ID]] \
               .drop_duplicates(subset=[COL_SYSTEM_ID]) \
               [[COL_SYSTEM_ID, COL_SYSTEM_NAME]]

    print(f"Total rows in file  : {len(df):,}")
    print(f"Top parents found   : {len(df_top):,}")

    xml_str = build_xml(df_top)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(xml_str)

    print(f"Output written      : {args.output}")
    print(f"Done.\n")


if __name__ == "__main__":
    main()
