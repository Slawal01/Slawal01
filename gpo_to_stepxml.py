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
    "context_id":         "Content",
    "root_node_id":       "GPOHierarchy",       # GPO Hierarchy Root node in STEP
    "type_top_parent":    "GPO_Top_Parent",      # Object type for top parent nodes
    "type_direct_parent": "GPO_Direct_Parent",   # Object type for direct parent nodes
    "type_member":        "GPO_Member",          # Object type for leaf members
}

# Maps schema field → STEP Attribute ID
ATTRIBUTE_MAP = {
    "name2":                        "Name2",
    "address_type":                 "AddressType",
    "address1":                     "Address1",
    "address2":                     "Address2",
    "address3":                     "Address3",
    "city":                         "City",
    "state":                        "State",
    "postal_code":                  "PostalCode",
    "country":                      "Country",
    "member_status":                "MemberStatus",
    "membership_eligible_date":     "MembershipEligibleDate",
    "comments":                     "Comments",
    # Premier-specific
    "override_name":                "OverrideName",
    "relationship_to_top_parent":   "RelationshipToTopParent",
    "relationship_to_direct_parent":"RelationshipToDirectParent",
    "committed_program_eligibility":"CommittedProgramEligibility",
    "premier_gpo_id":               "PremierGPOID",
    # Vizient-specific
    "vizient_member_id":            "VizientMemberID",
    "supply_program":               "SupplyProgram",
    "amc_tier_pricing":             "AMCTierPricing",
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
        "id_prefix":        "HT_",
        # GPOID is used for both native ID and hierarchy comparisons
        "hierarchy_id_field": "native_member_id",
    },
    "premier": {
        "code":             "PREMIER",
        "column_map":       PREMIER_MAP,
        "id_prefix":        "PR_",
        # Hierarchy compares GPO ID (premier_gpo_id) against Top/Direct Parent GPO ID
        # native_member_id = Address ID lives in a different ID space
        "hierarchy_id_field": "premier_gpo_id",
    },
    "vizient": {
        "code":             "VIZIENT",
        "column_map":       VIZIENT_MAP,
        "id_prefix":        "VZ_",
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
    """Normalize date values to YYYY-MM-DD string."""
    if pd.isna(val) or val is None:
        return None
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d")
    return str(val).strip()


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
    Build a STEPXML ElementTree from a deduplicated DataFrame.
    Processes in 3 passes: Top Parents → Direct Parents → Members.
    """
    cfg        = GPO_CONFIGS[gpo_key]
    prefix     = cfg["id_prefix"]
    hier_field = cfg["hierarchy_id_field"]  # field in same ID space as top/direct parent IDs

    root = etree.Element("STEP-ProductInformation")
    root.set("WorkspaceID", STEP_CONFIG["workspace_id"])
    root.set("ContextID",   STEP_CONFIG["context_id"])
    root.set("xmlns:xsi",   "http://www.w3.org/2001/XMLSchema-instance")

    products_el = etree.SubElement(root, "Products")

    emitted_ids = set()

    def emit_top_parent(step_id, name, row=None):
        if step_id in emitted_ids:
            return
        emitted_ids.add(step_id)
        el = etree.SubElement(products_el, "Product")
        el.set("ID",         step_id)
        el.set("ParentID",   STEP_CONFIG["root_node_id"])
        el.set("UserTypeID", STEP_CONFIG["type_top_parent"])
        name_el = etree.SubElement(el, "Name")
        name_el.text = name
        if row is not None:
            _add_common_values(el, row, prefix, gpo_key)

    # ---- PASS 1: Top Parents ----
    # Rule: top_parent_id = direct_parent_id = member's own hierarchy ID
    top_parents = df[
        (df["top_parent_id"].astype(str).str.strip() == df[hier_field].astype(str).str.strip()) &
        (df["direct_parent_id"].astype(str).str.strip() == df[hier_field].astype(str).str.strip())
    ].drop_duplicates(subset=["top_parent_id"])

    for _, row in top_parents.iterrows():
        step_id = make_step_id(prefix, row["top_parent_id"])
        emit_top_parent(step_id, str(row.get("top_parent_name", "")).strip(), row)

    # ---- PASS 1b: Implied Top Parents ----
    # Top parent IDs referenced by child rows but with no standalone own-row in Pass 1.
    # Synthesize them from the top_parent_name column so children have a valid parent.
    all_top_ids = df[["top_parent_id", "top_parent_name"]].drop_duplicates(subset=["top_parent_id"])
    for _, row in all_top_ids.iterrows():
        step_id = make_step_id(prefix, row["top_parent_id"])
        if step_id not in emitted_ids:
            emit_top_parent(step_id, str(row.get("top_parent_name", "")).strip())

    # ---- PASS 2: Direct Parents ----
    # Rule: top_parent_id = direct_parent_id != member's own hierarchy ID
    direct_parents = df[
        (df["top_parent_id"].astype(str).str.strip() == df["direct_parent_id"].astype(str).str.strip()) &
        (df["top_parent_id"].astype(str).str.strip() != df[hier_field].astype(str).str.strip())
    ].drop_duplicates(subset=["direct_parent_id"])

    for _, row in direct_parents.iterrows():
        step_id        = make_step_id(prefix, row["direct_parent_id"])
        parent_step_id = make_step_id(prefix, row["top_parent_id"])

        if step_id in emitted_ids:
            continue
        emitted_ids.add(step_id)

        el = etree.SubElement(products_el, "Product")
        el.set("ID",         step_id)
        el.set("ParentID",   parent_step_id)
        el.set("UserTypeID", STEP_CONFIG["type_direct_parent"])

        name_el = etree.SubElement(el, "Name")
        name_el.text = str(row.get("direct_parent_name", "")).strip()

        _add_common_values(el, row, prefix, gpo_key)

    # ---- PASS 3: Members ----
    # Includes two sub-cases:
    #   a) direct_parent_id = own hierarchy ID, top ≠ self  → 2-level: parent under top
    #   b) top_parent_id != direct_parent_id != self        → 3-level: parent under direct
    members = df[
        df["top_parent_id"].astype(str).str.strip() != df["direct_parent_id"].astype(str).str.strip()
    ]

    for _, row in members.iterrows():
        step_id = make_step_id(prefix, row["native_member_id"])

        # 2-level: member references itself as direct parent → sit under top parent
        if str(row["direct_parent_id"]).strip() == str(row[hier_field]).strip():
            parent_step_id = make_step_id(prefix, row["top_parent_id"])
        else:
            parent_step_id = make_step_id(prefix, row["direct_parent_id"])

        el = etree.SubElement(products_el, "Product")
        el.set("ID",         step_id)
        el.set("ParentID",   parent_step_id)
        el.set("UserTypeID", STEP_CONFIG["type_member"])

        name_el = etree.SubElement(el, "Name")
        name_el.text = str(row.get("name1", "")).strip()

        _add_common_values(el, row, prefix, gpo_key)
        _add_child_records(el, row, gpo_key)

    return etree.ElementTree(root)


def _add_common_values(el, row, prefix, gpo_key):
    """Add <Values> block with all mapped attributes."""
    values_el = etree.SubElement(el, "Values")

    for field, attr_id in ATTRIBUTE_MAP.items():
        if field in row.index:
            val = row[field]
            if "date" in field.lower():
                val = format_date(val)
            add_value(values_el, attr_id, val)


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
