"""
Premier Direct Parent CSV Import Generator
============================================
Reads Premier complete data CSV and generates a STEP-compatible CSV
import file for Direct Parent entities.

Direct Parent logic:
  Direct Parent GPO ID is not blank
  AND Direct Parent GPO ID != Top Parent GPO ID
  AND Direct Parent GPO ID != GPO ID (not self-referencing)
  One unique Direct Parent per unique Direct Parent GPO ID.

Parent ID lookup:
  Focus list CSV (Name -> CMDM STEP ID) matched on Top Parent Name 1.

Output columns:
  <ID>                blank (STEP auto-assigns)
  <Name>              Direct Parent Name 1
  <Parent ID>         Top Parent CMDM STEP ID
  <Object Type>       GPO_Direct_Parent
  gpo.GPO_Member_ID   Direct Parent GPO ID
  gpo.GPO_Entity_Key  Direct Parent Address ID
  gpo.Address_ID      Direct Parent Address ID

Usage:
  py premier_direct_parent_csv.py
"""

import argparse
import csv

DEFAULT_INPUT      = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\Premier complete data.csv"
DEFAULT_TP_IDS     = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\Parent id for newly created top parent.csv"
DEFAULT_OUTPUT     = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\premier_direct_parents_import.csv"

COL_GPO_ID       = "GPO ID"
COL_ADDRESS_ID   = "Address ID"
COL_ADDRESS_TYPE = "Address Type"
COL_NAME1        = "Name 1"
COL_TOP_ID       = "Top Parent GPO ID"
COL_TOP_NAME     = "Top Parent Name 1"
COL_DP_ID        = "Direct Parent GPO ID"
COL_DP_NAME      = "Direct Parent Name 1"

STEP_OBJECT_TYPE = "GPO_Direct_Parent"

OUT_FIELDS = [
    "<ID>",
    "<Name>",
    "<Parent ID>",
    "<Object Type>",
    "gpo.GPO_Member_ID",
    "gpo.GPO_Entity_Key",
    "gpo.Address_ID",
]


def load_tp_ids(path):
    """Load top parent STEP export: name (lower) -> <ID>."""
    tp_map = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            obj_type = row.get("<Object Type Name>", "").strip()
            if obj_type and "top parent" not in obj_type.lower():
                continue
            step_id = row.get("<ID>",   "").strip()
            name    = row.get("<Name>", "").strip()
            if step_id and name:
                tp_map[name.lower()] = step_id
    return tp_map


def name_matches_tp(top_name, tp_map):
    """Exact then prefix match on top parent name."""
    key = top_name.lower().strip()
    if key in tp_map:
        return tp_map[key]
    for f, step_id in tp_map.items():
        if key.startswith(f) or f.startswith(key):
            return step_id
    return None


def main():
    parser = argparse.ArgumentParser(description="Generate Premier Direct Parent CSV for STEP import")
    parser.add_argument("--input",   default=DEFAULT_INPUT,  help="Premier complete data CSV")
    parser.add_argument("--tp-ids",  default=DEFAULT_TP_IDS, help="Top parent STEP export CSV (for <Parent ID> lookup)")
    parser.add_argument("--output",  default=DEFAULT_OUTPUT, help="Output CSV file path")
    args = parser.parse_args()

    # ── Load top parent STEP IDs ──────────────────────────────────────────────
    print(f"\nReading top parent IDs: {args.tp_ids}")
    tp_map = load_tp_ids(args.tp_ids)
    print(f"  Top parents loaded   : {len(tp_map):,}")

    # ── First pass: build GPO ID -> Primary Address ID map ───────────────────
    print(f"\nReading Premier data (pass 1 — address map): {args.input}")
    address_map = {}   # gpo_id -> address_id (prefer Primary)
    with open(args.input, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            gpo_id     = row.get(COL_GPO_ID,       "").strip()
            address_id = row.get(COL_ADDRESS_ID,    "").strip()
            addr_type  = row.get(COL_ADDRESS_TYPE,  "").strip().lower()
            if not gpo_id or not address_id:
                continue
            if gpo_id not in address_map or addr_type == "primary":
                address_map[gpo_id] = address_id
    print(f"  GPO IDs mapped       : {len(address_map):,}")

    # ── Second pass: find unique direct parents ───────────────────────────────
    print(f"\nReading Premier data (pass 2 — direct parents):")
    seen_dp        = set()
    direct_parents = []
    total_rows     = 0
    no_address     = []
    no_tp          = []

    with open(args.input, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            total_rows += 1
            gpo_id   = row.get(COL_GPO_ID,  "").strip()
            top_id   = row.get(COL_TOP_ID,  "").strip()
            top_name = row.get(COL_TOP_NAME,"").strip()
            dp_id    = row.get(COL_DP_ID,   "").strip()
            dp_name  = row.get(COL_DP_NAME, "").strip()

            if not dp_id or not top_id:
                continue

            # Direct Parent: DP != Top Parent AND DP != self
            if dp_id == top_id or dp_id == gpo_id:
                continue

            if dp_id in seen_dp:
                continue
            seen_dp.add(dp_id)

            # Look up top parent STEP ID by name
            tp_step_id = name_matches_tp(top_name, tp_map)
            if not tp_step_id:
                no_tp.append(f"{top_id} / {top_name}")
                continue

            # Look up direct parent's own Address ID
            dp_address_id = address_map.get(dp_id, "")
            if not dp_address_id:
                no_address.append(f"{dp_id} / {dp_name}")

            direct_parents.append({
                "<ID>":               "",
                "<Name>":             dp_name,
                "<Parent ID>":        tp_step_id,
                "<Object Type>":      STEP_OBJECT_TYPE,
                "gpo.GPO_Member_ID":  dp_id,
                "gpo.GPO_Entity_Key": dp_id,
                "gpo.Address_ID":     dp_address_id,
            })

    print(f"  Total rows read        : {total_rows:,}")
    print(f"  Direct parents found   : {len(direct_parents):,}")
    if no_tp:
        print(f"  No top parent STEP ID  : {len(set(no_tp))} (skipped)")
    if no_address:
        print(f"  No Address ID found    : {len(no_address)}")
        for n in no_address[:10]:
            print(f"    {n}")

    # ── Write output CSV ──────────────────────────────────────────────────────
    with open(args.output, newline="", encoding="utf-8-sig", mode="w") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        writer.writeheader()
        writer.writerows(direct_parents)

    print(f"\n  Output written         : {args.output}")
    print("Done.\n")


if __name__ == "__main__":
    main()
