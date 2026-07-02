"""
GPO to STEPXML Generator
Reads GPO source Excel files and generates STEPXML for loading into Stibo STEP.
Processes hierarchy in correct order: Top Parents → Direct Parents → Members.

Usage:
    python gpo_to_stepxml.py --gpo healthtrust --input "Sample Health Trust Data.xlsx" --output ht_members.xml
    python gpo_to_stepxml.py --gpo premier     --input "Premier Data.xlsx"            --output premier_members.xml
    python gpo_to_stepxml.py --gpo vizient     --input "Vizient Data.xlsx"            --output vizient_members.xml
"""

import argparse
import pandas as pd
from lxml import etree
from datetime import datetime


# ============================================================
# STEP CONFIGURATION
# Adjust these to match your STEP object types and attribute IDs
# ============================================================

STEP_CONFIG = {
    "workspace_id":       "Main",
    "context_id":         "Context1",
    "type_top_parent":    "GPO_Top_Parent",      # Object type for top parent nodes
    "type_direct_parent": "GPO_Direct_Parent",   # Object type for direct parent nodes
    "type_member":        "GPO_Member",          # Object type for leaf members
}

# GPO-specific parent node IDs in STEP — top parents load under these
GPO_PARENT_NODES = {
    "healthtrust": "GPO_HealthTrust",
    "premier":     "GPO_Premier",
    "vizient":     "GPO_Vizient",
}

# Maps schema field → STEP Attribute ID
ATTRIBUTE_MAP = {
    # Address — existing loc.* attributes
    "address1":                      "loc.Address_Line_1",
    "address2":                      "loc.Address_Line_2",
    "address3":                      "loc.Address_Line_3",
    "city":                          "loc.Address_City",
    "state":                         "loc.Address_State",
    "postal_code":                   "loc.Address_Postal_Code",
    "country":                       "loc.Address_Country",
    # Common — to be created in STEP
    "name2":                         "gpo.Name_2",
    "member_status":                 "gpo.Member_Status",
    "membership_eligible_date":      "gpo.Membership_Eligible_Date",
    "comments":                      "gpo.Comments",
    # Premier-specific — to be created in STEP
    "address_type":                  "gpo.Address_Type",
    "override_name":                 "gpo.Override_Name",
    "premier_gpo_id":                "gpo.GPO_Member_ID",
    "relationship_to_top_parent":    "gpo.Relationship_To_Top_Parent",
    "relationship_to_direct_parent": "gpo.Relationship_To_Direct_Parent",
    "committed_program_eligibility": "gpo.Committed_Program_Eligibility",
    "affiliation_1":                 "gpo.Aggregation_Affiliation_1",
    "affiliation_1_start":           "gpo.Affiliation_Start_Date_1",
    "affiliation_1_end":             "gpo.Affiliation_End_Date_1",
    "affiliation_2":                 "gpo.Aggregation_Affiliation_2",
    "affiliation_2_start":           "gpo.Affiliation_Start_Date_2",
    "affiliation_2_end":             "gpo.Affiliation_End_Date_2",
    "affiliation_3":                 "gpo.Aggregation_Affiliation_3",
    "affiliation_3_start":           "gpo.Affiliation_Start_Date_3",
    "affiliation_3_end":             "gpo.Affiliation_End_Date_3",
    # Vizient-specific — to be created in STEP
    "vizient_member_id":             "gpo.GPO_Member_ID",
    "supply_program":                "gpo.Supply_Program",
    "amc_tier_pricing":              "gpo.AMC_Tier_Pricing",
    "group_1":                       "gpo.Vizient_Group_1",
    "group_2":                       "gpo.Vizient_Group_2",
    "group_3":                       "gpo.Vizient_Group_3",
}

# GPO-specific attribute overrides — added on top of ATTRIBUTE_MAP per GPO
GPO_ATTRIBUTE_MAP = {
    "healthtrust": {
        "native_member_id": "gpo.GPO_Member_ID",    # GPOID — exists in STEP
    },
    "premier": {
        "native_member_id": "gpo.Address_ID",       # Address ID — exists in STEP
    },
    "vizient": {
        "native_member_id": "gpo.LIC",              # LIC — exists in STEP
    },
}


# ============================================================
# GPO-SPECIFIC COLUMN MAPPINGS
# Maps source Excel column names → internal field names
# ============================================================

HEALTHTRUST_MAP = {
    "GPOID":                    "native_member_id",
    "Membership Eligible Date": "membership_eligible_date",
    "Name1":                    "name1",
    "Name2":                    "name2",
    "Address1":                 "address1",
    "Address2":                 "address2",
    "Address3":                 "address3",
    "City":                     "city",
    "State/Province":           "state",
    "Postal Code":              "postal_code",
    "Country":                  "country",
    "Direct Parent GPOID":      "direct_parent_id",
    "Direct Parent Name1":      "direct_parent_name",
    "Top Parent GPOID":         "top_parent_id",
    "Top Parent Name 1":        "top_parent_name",
    "Member Status":            "member_status",
    "Comments":                 "comments",
}

PREMIER_MAP = {
    "Address ID":                   "native_member_id",
    "GPO ID":                       "premier_gpo_id",
    "Membership Start Date":        "membership_eligible_date",
    "Name 1":                       "name1",
    "Name 2":                       "name2",
    "Override Name":                "override_name",
    "Address Type":                 "address_type",
    "Address 1":                    "address1",
    "Address 2":                    "address2",
    "Address 3":                    "address3",
    "City":                         "city",
    "State/Province":               "state",
    "Postal Code":                  "postal_code",
    "Country":                      "country",
    "Relationship to Top Parent":   "relationship_to_top_parent",
    "Relationship to Direct Parent":"relationship_to_direct_parent",
    "Direct Parent GPO ID":         "direct_parent_id",
    "Direct Parent Name 1":         "direct_parent_name",
    "Top Parent GPO ID":            "top_parent_id",
    "Top Parent Name 1":            "top_parent_name",
    "Member Status":                "member_status",
    "Committed Program Eligibility":"committed_program_eligibility",
    # Programs (loaded as child elements)
    "AscenDrive Start Date":        "ascendrive_start",
    "AscenDrive End Date":          "ascendrive_end",
    "KIINDO Start Date":            "kiindo_start",
    "KIINDO End Date":              "kiindo_end",
    "SURPASS Start Date":           "surpass_start",
    "SURPASS End Date":             "surpass_end",
    # Affiliations
    "Aggregation Affiliation 1":    "affiliation_1",
    "Affiliation Start Date 1":     "affiliation_1_start",
    "Affiliation End Date 1":       "affiliation_1_end",
    "Aggregation Affiliation 2":    "affiliation_2",
    "Affiliation Start Date 2":     "affiliation_2_start",
    "Affiliation End Date 2":       "affiliation_2_end",
    "Aggregation Affiliation 3":    "affiliation_3",
    "Affiliation Start Date 3":     "affiliation_3_start",
    "Affiliation End Date 3":       "affiliation_3_end",
}

VIZIENT_MAP = {
    "LIC":              "native_member_id",
    "Member ID":        "vizient_member_id",
    "Member Date":      "membership_eligible_date",
    "Member Name":      "name1",
    "Address1":         "address1",
    "Address2":         "address2",
    "City":             "city",
    "State":            "state",
    "Zip Code":         "postal_code",
    "System ID":        "top_parent_id",
    "System Name":      "top_parent_name",
    "Parent ID":        "direct_parent_id",
    "Parent Name":      "direct_parent_name",
    "Supply Program":   "supply_program",
    "AMC Tier Pricing": "amc_tier_pricing",
    "Vizient Group 1":  "group_1",
    "Vizient Group 2":  "group_2",
    "Vizient Group 3":  "group_3",
}

GPO_CONFIGS = {
    "healthtrust": {
        "code":             "HEALTHTRUST",
        "column_map":       HEALTHTRUST_MAP,
        "id_prefix":        "GPO_HealthTrust_",
        # GPOID is used for both native ID and hierarchy comparisons
        "hierarchy_id_field": "native_member_id",
    },
    "premier": {
        "code":             "PREMIER",
        "column_map":       PREMIER_MAP,
        "id_prefix":        "GPO_Premier_",
        # Hierarchy compares GPO ID (premier_gpo_id) against Top/Direct Parent GPO ID
        # native_member_id = Address ID lives in a different ID space
        "hierarchy_id_field": "premier_gpo_id",
    },
    "vizient": {
        "code":             "VIZIENT",
        "column_map":       VIZIENT_MAP,
        "id_prefix":        "GPO_Vizient_",
        # Hierarchy compares Member ID (vizient_member_id) against System ID / Parent ID
        # native_member_id = LIC lives in a different ID space
        "hierarchy_id_field": "vizient_member_id",
    },
}


# ============================================================
# HELPERS
# ============================================================

def make_step_id(prefix, native_id):
    """Build a STEP-safe object ID from GPO prefix + native member ID."""
    return f"{prefix}{str(native_id).strip().replace(' ', '_')}"


def format_date(val):
    """Normalize date values to ISO 8601 YYYY-MM-DD string."""
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d")
    s = str(val).strip()
    if not s or s.lower() == 'nat':
        return None
    # Try parsing common formats
    for fmt in ("%m/%d/%Y", "%d/%m/%Y", "%m-%d-%Y", "%d-%b-%Y"):
        try:
            from datetime import datetime as dt
            return dt.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return s


def add_value(parent_el, attr_id, value):
    """Add a <Value AttributeID="...">...</Value> element if value is not empty."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return
    val_str = str(value).strip()
    if val_str and val_str.lower() not in ("nan", "none", "nat"):
        v = etree.SubElement(parent_el, "Value")
        v.set("AttributeID", attr_id)
        v.text = val_str


# ============================================================
# STEPXML BUILDER
# ============================================================

def build_stepxml(df, gpo_key):
    """
    Build a STEPXML ElementTree using nested <Entities>/<Entity> format.

    Vizient hierarchy logic:
      Top Parent   : Member ID == System ID
      Direct Parent: Parent ID != System ID AND Parent ID != Member ID
      Member       : Member ID != System ID AND (Parent ID == System ID OR Parent ID == Member ID)

    gpo.GPO_Entity_Key = LIC if present, else Member ID (native_member_id)
    """
    cfg         = GPO_CONFIGS[gpo_key]
    gpo_node_id = GPO_PARENT_NODES[gpo_key]

    root = etree.Element("STEP-ProductInformation")
    root.set("ExportTime",       datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    root.set("ContextID",        STEP_CONFIG["context_id"])
    root.set("WorkspaceID",      STEP_CONFIG["workspace_id"])
    root.set("UseContextLocale", "false")

    entities_el = etree.SubElement(root, "Entities")

    def s(val):
        v = str(val).strip()
        return "" if v.lower() in ("nan", "none", "nat") else v

    hier_field = cfg["hierarchy_id_field"]  # vizient_member_id for Vizient

    # Group all rows by top_parent_id
    df["_top"]    = df["top_parent_id"].astype(str).str.strip()
    df["_direct"] = df["direct_parent_id"].astype(str).str.strip()
    df["_hier"]   = df[hier_field].astype(str).str.strip()

    for top_id, top_group in df.groupby("_top"):
        top_name = s(top_group["top_parent_name"].iloc[0])
        if not top_name or top_name.upper() == "NA":
            continue

        top_el = etree.SubElement(entities_el, "Entity")
        top_el.set("UserTypeID", STEP_CONFIG["type_top_parent"])
        top_el.set("ParentID",   gpo_node_id)
        etree.SubElement(top_el, "Name").text = top_name

        # Top parent own attributes (from its own row if it exists)
        top_rows = top_group[top_group["_hier"] == top_id]
        if not top_rows.empty:
            _add_common_values(top_el, top_rows.iloc[0], "", gpo_key)

        # Split members of this top parent into direct-parent groups vs direct members
        children = top_group[top_group["_hier"] != top_id]

        # Direct Parent: Parent ID != System ID AND Parent ID != Member ID
        has_direct_parent = children[
            (children["_direct"] != top_id) &
            (children["_direct"] != children["_hier"]) &
            (children["_direct"] != "") &
            (~children["_direct"].isin(["nan", "None", "NaN"]))
        ]

        # Member under Top Parent: Parent ID == System ID OR Parent ID == Member ID
        direct_members = children[
            (children["_direct"] == top_id) |
            (children["_direct"] == children["_hier"]) |
            (children["_direct"].isin(["", "nan", "None", "NaN"]))
        ]

        # Emit Direct Parents and their members
        emitted_direct = set()
        for _, row in has_direct_parent.iterrows():
            dp_id   = s(row["_direct"])
            dp_name = s(row.get("direct_parent_name", ""))

            if dp_id not in emitted_direct:
                emitted_direct.add(dp_id)
                dp_el = etree.SubElement(top_el, "Entity")
                dp_el.set("UserTypeID", STEP_CONFIG["type_direct_parent"])
                etree.SubElement(dp_el, "Name").text = dp_name
                dp_vals = etree.SubElement(dp_el, "Values")
                v = etree.SubElement(dp_vals, "Value")
                v.set("AttributeID", "gpo.GPO_Member_ID"); v.text = dp_id

            # Add member under its direct parent
            mem_el = etree.SubElement(dp_el, "Entity")
            mem_el.set("UserTypeID", STEP_CONFIG["type_member"])
            etree.SubElement(mem_el, "Name").text = s(row.get("name1", ""))
            _add_common_values(mem_el, row, "", gpo_key)
            _add_child_records(mem_el, row, gpo_key)

        # Emit direct members under top parent
        for _, row in direct_members.iterrows():
            mem_el = etree.SubElement(top_el, "Entity")
            mem_el.set("UserTypeID", STEP_CONFIG["type_member"])
            etree.SubElement(mem_el, "Name").text = s(row.get("name1", ""))
            _add_common_values(mem_el, row, "", gpo_key)
            _add_child_records(mem_el, row, gpo_key)

    return etree.ElementTree(root)


def _add_common_values(el, row, prefix, gpo_key):
    """Add <Values> block with all mapped attributes."""
    values_el = etree.SubElement(el, "Values")

    # Merge base map with any GPO-specific overrides
    attr_map = {**ATTRIBUTE_MAP, **GPO_ATTRIBUTE_MAP.get(gpo_key, {})}

    for field, attr_id in attr_map.items():
        if field in row.index:
            val = row[field]
            if "date" in field.lower():
                val = format_date(val)
            add_value(values_el, attr_id, val)

    # gpo.GPO_Entity_Key = LIC if present, else native_member_id (Member ID)
    lic_val    = row.get("native_member_id") if gpo_key == "vizient" else None
    member_val = row.get("vizient_member_id") if gpo_key == "vizient" else row.get("native_member_id")
    entity_key = lic_val if lic_val and str(lic_val).strip() not in ("", "nan") else member_val
    if entity_key:
        add_value(values_el, "gpo.GPO_Entity_Key", entity_key)


def _add_child_records(el, row, gpo_key):
    """Add program, group, and affiliation child elements."""

    # Premier: Programs
    if gpo_key == "premier":
        programs = [
            ("AscenDrive", "ascendrive_start", "ascendrive_end"),
            ("KIINDO",     "kiindo_start",     "kiindo_end"),
            ("SURPASS",    "surpass_start",    "surpass_end"),
        ]
        for prog_name, start_f, end_f in programs:
            start = format_date(row.get(start_f))
            if start:
                p = etree.SubElement(el, "CrossReference")
                p.set("Type",      "MemberProgram")
                p.set("Program",   prog_name)
                p.set("StartDate", start)
                end = format_date(row.get(end_f))
                if end:
                    p.set("EndDate", end)

        # Premier: Affiliations
        for i in range(1, 4):
            aff_val   = row.get(f"affiliation_{i}")
            aff_start = format_date(row.get(f"affiliation_{i}_start"))
            if aff_val and not pd.isna(aff_val):
                a = etree.SubElement(el, "CrossReference")
                a.set("Type",        "MemberAffiliation")
                a.set("Affiliation", str(aff_val).strip())
                if aff_start:
                    a.set("StartDate", aff_start)
                aff_end = format_date(row.get(f"affiliation_{i}_end"))
                if aff_end:
                    a.set("EndDate", aff_end)

    # Vizient: Groups
    if gpo_key == "vizient":
        for i in range(1, 4):
            grp = row.get(f"group_{i}")
            if grp and not pd.isna(grp):
                g = etree.SubElement(el, "CrossReference")
                g.set("Type",      "MemberGroup")
                g.set("GroupName", str(grp).strip())


# ============================================================
# LOAD & DEDUPLICATE
# ============================================================

def load_and_prepare(filepath, gpo_key):
    """Read Excel file, rename columns, deduplicate."""
    cfg        = GPO_CONFIGS[gpo_key]
    column_map = cfg["column_map"]

    df = pd.read_excel(filepath)

    # Keep only mapped columns that exist in the file
    existing = {k: v for k, v in column_map.items() if k in df.columns}
    df = df[list(existing.keys())].rename(columns=existing)

    # HealthTrust: deduplicate on native_member_id (one row per GPOID)
    if gpo_key == "healthtrust":
        before = len(df)
        df = df.drop_duplicates(subset=["native_member_id"])
        print(f"  HealthTrust deduplication: {before} rows → {len(df)} unique members")

    # Normalize IDs to string and strip whitespace
    for col in ["native_member_id", "top_parent_id", "direct_parent_id"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    return df


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Generate STEPXML from GPO Excel data")
    parser.add_argument("--gpo",    required=True, choices=["healthtrust", "premier", "vizient"])
    parser.add_argument("--input",  required=True, help="Path to source Excel file")
    parser.add_argument("--output", required=True, help="Output STEPXML file path")
    args = parser.parse_args()

    print(f"\n[{args.gpo.upper()}] Loading: {args.input}")
    df = load_and_prepare(args.input, args.gpo)

    # Count hierarchy levels
    top_p  = df[(df["top_parent_id"] == df["native_member_id"]) & (df["direct_parent_id"] == df["native_member_id"])]
    dir_p  = df[(df["top_parent_id"] == df["direct_parent_id"]) & (df["top_parent_id"] != df["native_member_id"])]
    leaves = df[df["top_parent_id"] != df["direct_parent_id"]]

    print(f"  Top Parents:    {len(top_p.drop_duplicates('top_parent_id'))}")
    print(f"  Direct Parents: {len(dir_p.drop_duplicates('direct_parent_id'))}")
    print(f"  Leaf Members:   {len(leaves)}")
    print(f"  Total rows:     {len(df)}")

    print(f"\n  Generating STEPXML...")
    tree = build_stepxml(df, args.gpo)

    tree.write(
        args.output,
        pretty_print=True,
        xml_declaration=True,
        encoding="UTF-8"
    )

    print(f"  Output written: {args.output}")
    print(f"  Done.\n")


if __name__ == "__main__":
    main()
