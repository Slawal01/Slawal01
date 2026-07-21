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
DEFAULT_FOCUS      = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\premier_top_parents_step.csv"
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


def name_matches(premier_name, focus_map):
    """Look up STEP ID for a top parent name using exact then prefix matching."""
    key = premier_name.lower().strip()
    if key in focus_map:
        return focus_map[key]
    for f, step_id in focus_map.items():
        if key.startswith(f) or f.startswith(key):
            return step_id
    return None


def load_focus_list(path):
    """Load STEP export: Top Parent Name (lower) -> STEP ID. Skips non-top-parent rows."""
    focus_map  = {}
    duplicates = set()

    if path.lower().endswith(".xlsx"):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
            ws = wb.active
            headers = None
            id_col = name_col = type_col = None
            for row in ws.iter_rows(values_only=True):
                if headers is None:
                    headers   = [str(c).strip() if c else "" for c in row]
                    id_col    = headers.index("<ID>")               if "<ID>"               in headers else None
                    name_col  = headers.index("<Name>")             if "<Name>"             in headers else None
                    type_col  = headers.index("<Object Type Name>") if "<Object Type Name>" in headers else None
                    continue
                if id_col is None or name_col is None:
                    break
                obj_type = str(row[type_col]).strip() if (type_col is not None and row[type_col]) else ""
                if obj_type and "top parent" not in obj_type.lower():
                    continue
                step_id = str(row[id_col]).strip()  if row[id_col]  else ""
                name    = str(row[name_col]).strip() if row[name_col] else ""
                if not step_id or not name or step_id == "None":
                    continue
                key = name.lower()
                if key in focus_map:
                    duplicates.add(name)
                else:
                    focus_map[key] = step_id
            wb.close()
        except ImportError:
            raise SystemExit("openpyxl not available — save the focus list as CSV and pass it via --focus")
    else:
        with open(path, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                obj_type = row.get("<Object Type Name>", "").strip()
                if obj_type and "top parent" not in obj_type.lower():
                    continue
                step_id = row.get("<ID>",   "").strip()
                name    = row.get("<Name>", "").strip()
                if not step_id or not name:
                    continue
                key = name.lower()
                if key in focus_map:
                    duplicates.add(name)
                else:
                    focus_map[key] = step_id

    return focus_map, duplicates


def main():
    parser = argparse.ArgumentParser(description="Generate Premier Direct Parent CSV for STEP import")
    parser.add_argument("--input",  default=DEFAULT_INPUT,  help="Premier complete data CSV")
    parser.add_argument("--focus",  default=DEFAULT_FOCUS,  help="Focus list XLSX/CSV with top parent CMDM IDs")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output CSV file path")
    args = parser.parse_args()

    # ── Load focus list ───────────────────────────────────────────────────────
    print(f"\nReading focus list: {args.focus}")
    focus_map, dupes = load_focus_list(args.focus)
    print(f"  Top parents in focus : {len(focus_map):,}")
    if dupes:
        print(f"  Duplicate names ({len(dupes)}) — first CMDM ID used:")
        for n in sorted(dupes):
            print(f"    {n}")

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
    seen_dp       = set()
    direct_parents = []
    total_rows    = 0
    no_focus      = []
    no_address    = []

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

            # Look up top parent STEP ID (fuzzy match)
            cmdm_id = name_matches(top_name, focus_map)
            if not cmdm_id:
                no_focus.append(f"{top_id} / {top_name}")
                continue

            # Look up direct parent's own Address ID
            dp_address_id = address_map.get(dp_id, "")
            if not dp_address_id:
                no_address.append(f"{dp_id} / {dp_name}")

            direct_parents.append({
                "<ID>":               "",
                "<Name>":             dp_name,
                "<Parent ID>":        cmdm_id,
                "<Object Type>":      STEP_OBJECT_TYPE,
                "gpo.GPO_Member_ID":  dp_id,
                "gpo.GPO_Entity_Key": dp_address_id,
                "gpo.Address_ID":     dp_address_id,
            })

    print(f"  Total rows read        : {total_rows:,}")
    print(f"  Direct parents found   : {len(direct_parents):,}")
    if no_focus:
        no_focus_uniq = sorted(set(no_focus))
        print(f"  Not in focus list      : {len(no_focus_uniq)}")
        for n in no_focus_uniq[:10]:
            print(f"    {n}")
        if len(no_focus_uniq) > 10:
            print(f"    ... and {len(no_focus_uniq) - 10} more")
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
