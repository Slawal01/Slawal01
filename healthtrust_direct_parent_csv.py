"""
HealthTrust Direct Parent CSV Import Generator
===============================================
Reads HealthTrust deduped CSV and generates a STEP-compatible CSV
import file for Direct Parent entities.

Direct Parent logic:
  Direct Parent GPOID != blank
  AND Direct Parent GPOID != Top Parent GPOID
  AND Direct Parent GPOID != GPOID
  One unique Direct Parent per unique Direct Parent GPOID.

Output columns:
  <ID>                blank (STEP auto-assigns)
  <Name>              Direct Parent Name1
  <Parent ID>         Top Parent STEP ID (from STEP export)
  <Object Type>       GPO_Direct_Parent
  gpo.GPO_Member_ID   Direct Parent GPOID
  gpo.GPO_Entity_Key  Direct Parent GPOID
  gpo.Address_ID      Direct Parent COID

Usage:
  py healthtrust_direct_parent_csv.py
"""

import argparse
import csv

DEFAULT_INPUT   = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\HealthTrust deduped.csv"
DEFAULT_TP_IDS  = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\HealthTrust Top parent in step.csv"
DEFAULT_OUTPUT  = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\healthtrust_direct_parents_import.csv"

COL_GPOID    = "GPOID"
COL_COID     = "COID"
COL_NAME1    = "Name1"
COL_TOP_ID   = "Top Parent GPOID"
COL_TOP_NAME = "Top Parent Name 1"
COL_DP_ID    = "Direct Parent GPOID"
COL_DP_NAME  = "Direct Parent Name1"

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
    parser = argparse.ArgumentParser(description="Generate HealthTrust Direct Parent CSV for STEP import")
    parser.add_argument("--input",  default=DEFAULT_INPUT,  help="HealthTrust deduped CSV")
    parser.add_argument("--tp-ids", default=DEFAULT_TP_IDS, help="Top parent STEP export CSV")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output CSV file path")
    args = parser.parse_args()

    # ── Load top parent STEP IDs ──────────────────────────────────────────────
    print(f"\nReading top parent IDs: {args.tp_ids}")
    tp_map = load_tp_ids(args.tp_ids)
    print(f"  Top parents loaded   : {len(tp_map):,}")

    # ── Build COID map for direct parents ─────────────────────────────────────
    print(f"\nReading HealthTrust data (pass 1 — COID map): {args.input}")
    coid_map = {}   # gpoid -> coid (prefer Primary)
    with open(args.input, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            gpoid     = row.get(COL_GPOID, "").strip()
            coid      = row.get(COL_COID,  "").strip()
            addr_type = row.get("Address Type", "").strip().lower()
            if not gpoid or not coid:
                continue
            if gpoid not in coid_map or addr_type == "primary":
                coid_map[gpoid] = coid
    print(f"  GPOIDs mapped        : {len(coid_map):,}")

    # ── Find unique direct parents ────────────────────────────────────────────
    print(f"\nReading HealthTrust data (pass 2 — direct parents):")
    seen_dp        = set()
    direct_parents = []
    total_rows     = 0
    no_tp          = []
    no_coid        = []

    with open(args.input, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            total_rows += 1
            gpoid    = row.get(COL_GPOID,    "").strip()
            top_id   = row.get(COL_TOP_ID,   "").strip()
            top_name = row.get(COL_TOP_NAME, "").strip()
            dp_id    = row.get(COL_DP_ID,    "").strip()
            dp_name  = row.get(COL_DP_NAME,  "").strip()

            if not dp_id or not top_id:
                continue

            if dp_id == top_id or dp_id == gpoid:
                continue

            if dp_id in seen_dp:
                continue
            seen_dp.add(dp_id)

            tp_step_id = name_matches_tp(top_name, tp_map)
            if not tp_step_id:
                no_tp.append(f"{top_id} / {top_name}")
                continue

            dp_coid = coid_map.get(dp_id, "")
            if not dp_coid:
                no_coid.append(f"{dp_id} / {dp_name}")

            direct_parents.append({
                "<ID>":               "",
                "<Name>":             dp_name,
                "<Parent ID>":        tp_step_id,
                "<Object Type>":      STEP_OBJECT_TYPE,
                "gpo.GPO_Member_ID":  dp_id,
                "gpo.GPO_Entity_Key": dp_id,
                "gpo.Address_ID":     dp_coid,
            })

    print(f"  Total rows read        : {total_rows:,}")
    print(f"  Direct parents found   : {len(direct_parents):,}")
    if no_tp:
        print(f"  No top parent STEP ID  : {len(set(no_tp))} (skipped)")
    if no_coid:
        print(f"  No COID found          : {len(no_coid)}")
        for n in no_coid[:10]:
            print(f"    {n}")

    with open(args.output, newline="", encoding="utf-8-sig", mode="w") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        writer.writeheader()
        writer.writerows(direct_parents)

    print(f"\n  Output written         : {args.output}")
    print("Done.\n")


if __name__ == "__main__":
    main()
