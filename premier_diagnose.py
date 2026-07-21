"""Diagnose Premier top parent name mismatches against the focus list."""

import argparse
import csv

INPUT      = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\Premier complete data.csv"
FOCUS      = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\Focus -2026-07-21_17.43.07.csv"
MISMATCH_OUT = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\premier_name_mismatches.csv"

COL_GPO_ID    = "GPO ID"
COL_TOP_ID    = "Top Parent GPO ID"
COL_TOP_NAME  = "Top Parent Name 1"
COL_DIRECT_ID = "Direct Parent GPO ID"

parser = argparse.ArgumentParser()
parser.add_argument("--focus", default=FOCUS)
args = parser.parse_args()

# Load focus list names
focus_names = set()
with open(args.focus, newline="", encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        name = row.get("<Name>", "").strip()
        if name:
            focus_names.add(name.lower())
print(f"\nFocus list names: {len(focus_names):,}")

# Find unique top parents in Premier data
premier_top_parents = {}   # gpo_id -> top_name
with open(INPUT, newline="", encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        gpo_id    = row.get(COL_GPO_ID,    "").strip()
        top_id    = row.get(COL_TOP_ID,    "").strip()
        top_name  = row.get(COL_TOP_NAME,  "").strip()
        direct_id = row.get(COL_DIRECT_ID, "").strip()
        if gpo_id == top_id and direct_id == "" and gpo_id not in premier_top_parents:
            premier_top_parents[gpo_id] = top_name

print(f"Unique top parents in Premier data: {len(premier_top_parents):,}")

matched   = [(gid, name) for gid, name in premier_top_parents.items() if name.lower() in focus_names]
unmatched = [(gid, name) for gid, name in premier_top_parents.items() if name.lower() not in focus_names]

print(f"Matched to focus list  : {len(matched):,}")
print(f"NOT in focus list      : {len(unmatched):,}")

print(f"\nAll Premier top parent names NOT in focus list:")
for gid, name in sorted(unmatched, key=lambda x: x[1]):
    print(f"  {gid:<12} {name}")

# Write full mismatch list to CSV
with open(MISMATCH_OUT, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["GPO ID", "Premier Top Parent Name", "In Focus List"])
    for gid, name in sorted(premier_top_parents.items(), key=lambda x: x[1]):
        w.writerow([gid, name, "Yes" if name.lower() in focus_names else "No"])

print(f"\nFull list written to: {MISMATCH_OUT}")
