"""Diagnose Premier top parent logic — shows what Direct Parent GPO ID looks like
when GPO ID == Top Parent GPO ID, to help confirm the correct top parent rule."""

import csv

INPUT = r"C:\Users\S670847\OneDrive - Owens & Minor\Documents\GPO DATA\Premier complete data.csv"

COL_GPO_ID    = "GPO ID"
COL_TOP_ID    = "Top Parent GPO ID"
COL_TOP_NAME  = "Top Parent Name 1"
COL_DIRECT_ID = "Direct Parent GPO ID"
COL_ADDR_TYPE = "Address Type"
COL_TOP_FLAG  = "Top Parent Flag"

samples = []
total = 0

with open(INPUT, newline="", encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        total += 1
        gpo_id    = row.get(COL_GPO_ID,    "").strip()
        top_id    = row.get(COL_TOP_ID,    "").strip()
        top_name  = row.get(COL_TOP_NAME,  "").strip()
        direct_id = row.get(COL_DIRECT_ID, "").strip()
        addr_type = row.get(COL_ADDR_TYPE, "").strip()
        top_flag  = row.get(COL_TOP_FLAG,  "").strip()

        if gpo_id == top_id and len(samples) < 20:
            samples.append({
                "GPO ID":             gpo_id,
                "Top Parent GPO ID":  top_id,
                "Direct Parent GPO ID": direct_id,
                "Top Parent Name 1":  top_name,
                "Address Type":       addr_type,
                "Top Parent Flag":    top_flag,
            })

print(f"\nTotal rows: {total:,}")
print(f"Rows where GPO ID == Top Parent GPO ID: {len(samples)} (showing first 20)\n")
for s in samples:
    print(f"  GPO ID={s['GPO ID']:<12} TopID={s['Top Parent GPO ID']:<12} DirectID={s['Direct Parent GPO ID']:<12} Flag={s['Top Parent Flag']:<5} AddrType={s['Address Type']:<12} Name={s['Top Parent Name 1']}")
