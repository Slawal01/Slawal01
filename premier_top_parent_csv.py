"""
Premier Top Parent CSV Import Generator
=========================================
Reads Premier complete data CSV and generates a STEP-compatible CSV
import file for Top Parent entities, filtered to the focus list.

Top Parent logic:
  GPO ID == Top Parent GPO ID AND Direct Parent GPO ID is blank
  One unique Top Parent per unique GPO ID.
  Name must match focus list (case-insensitive).

Output columns:
  <ID>                blank (STEP auto-assigns)
  <Name>              Top Parent Name 1
  <Parent ID>         GPO_Premier
  <Object Type>       GPO_Top_Parent
  gpo.GPO_Member_ID   GPO ID
  gpo.GPO_Entity_Key  Address ID
  gpo.Address_ID      Address ID

Usage:
  py premier_top_parent_csv.py
"""

import argparse
import csv

DEFAULT_INPUT  = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\Premier complete data.csv"
DEFAULT_FOCUS  = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\Focus_20260721_17.43.07.xlsx"
DEFAULT_OUTPUT = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\premier_top_parents_import.csv"

COL_ADDRESS_ID = "Address ID"
COL_GPO_ID     = "GPO ID"
COL_NAME1      = "Name 1"
COL_TOP_ID     = "Top Parent GPO ID"
COL_TOP_NAME   = "Top Parent Name 1"
COL_DIRECT_ID  = "Direct Parent GPO ID"

STEP_PARENT_ID   = "GPO_Premier"
STEP_OBJECT_TYPE = "GPO_Top_Parent"

OUT_FIELDS = [
    "<ID>",
    "<Name>",
    "<Parent ID>",
    "<Object Type>",
    "gpo.GPO_Member_ID",
    "gpo.GPO_Entity_Key",
    "gpo.Address_ID",
]


def name_matches_focus(premier_name, focus_names):
    """Return True if premier_name matches any focus list name.
    Handles cases like 'UPMC' (focus) matching 'UPMC Health System' (Premier).
    """
    p = premier_name.lower().strip()
    if p in focus_names:
        return True
    # Check if any focus name is a prefix of the Premier name
    for f in focus_names:
        if p.startswith(f) or f.startswith(p):
            return True
    return False


def load_focus_list(path):
    """Return set of target names (lower-cased) from focus list XLSX or CSV."""
    focus_names = set()
    if path.lower().endswith(".xlsx"):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
            ws = wb.active
            headers = None
            name_col = None
            for row in ws.iter_rows(values_only=True):
                if headers is None:
                    headers = [str(c).strip() if c else "" for c in row]
                    name_col = headers.index("<Name>") if "<Name>" in headers else None
                    continue
                if name_col is None:
                    break
                name = str(row[name_col]).strip() if row[name_col] else ""
                if name and name != "None":
                    focus_names.add(name.lower())
            wb.close()
        except ImportError:
            raise SystemExit("openpyxl not available — save the focus list as CSV and pass via --focus")
    else:
        with open(path, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                name = row.get("<Name>", "").strip()
                if name:
                    focus_names.add(name.lower())
    return focus_names


def main():
    parser = argparse.ArgumentParser(description="Generate Premier Top Parent CSV for STEP import")
    parser.add_argument("--input",  default=DEFAULT_INPUT,  help="Premier complete data CSV")
    parser.add_argument("--focus",  default=DEFAULT_FOCUS,  help="Focus list XLSX/CSV with target top parent names")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output CSV file path")
    args = parser.parse_args()

    # ── Load focus list ───────────────────────────────────────────────────────
    print(f"\nReading focus list: {args.focus}")
    focus_names = load_focus_list(args.focus)
    print(f"  Target top parents : {len(focus_names):,}")

    # ── Read Premier data and find top parents ────────────────────────────────
    print(f"\nReading: {args.input}")
    seen_ids    = set()
    top_parents = []
    total_rows  = 0
    rejected    = 0
    not_in_focus = 0

    with open(args.input, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            total_rows += 1
            address_id = row.get(COL_ADDRESS_ID, "").strip()
            gpo_id     = row.get(COL_GPO_ID,     "").strip()
            name1      = row.get(COL_TOP_NAME,   "").strip() or row.get(COL_NAME1, "").strip()
            top_id     = row.get(COL_TOP_ID,     "").strip()
            direct_id  = row.get(COL_DIRECT_ID,  "").strip()

            if not gpo_id or not top_id:
                continue

            # Top parent: GPO ID == Top Parent GPO ID AND Direct Parent GPO ID is blank
            if not (gpo_id == top_id and direct_id == ""):
                continue

            # Reject blank or NA names
            if not name1 or name1.upper() in ("NA", "N/A"):
                print(f"  REJECTED (no name): GPO ID {gpo_id}")
                rejected += 1
                continue

            # Filter to focus list (handles partial matches e.g. "UPMC" -> "UPMC Health System")
            if not name_matches_focus(name1, focus_names):
                not_in_focus += 1
                continue

            # Deduplicate by GPO ID
            if gpo_id in seen_ids:
                continue
            seen_ids.add(gpo_id)

            top_parents.append({
                "<ID>":               gpo_id,
                "<Name>":             name1,
                "<Parent ID>":        STEP_PARENT_ID,
                "<Object Type>":      STEP_OBJECT_TYPE,
                "gpo.GPO_Member_ID":  top_id,
                "gpo.GPO_Entity_Key": top_id,
                "gpo.Address_ID":     address_id,
            })

    print(f"  Total rows read    : {total_rows:,}")
    print(f"  Rejected (no name) : {rejected:,}")
    print(f"  Not in focus list  : {not_in_focus:,}")
    print(f"  Top parents found  : {len(top_parents):,}")

    with open(args.output, newline="", encoding="utf-8-sig", mode="w") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        writer.writeheader()
        writer.writerows(top_parents)

    print(f"\n  Output written     : {args.output}")
    print("Done.\n")


if __name__ == "__main__":
    main()
