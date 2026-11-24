"""
Seed script to populate data/local_erp.db from uploaded Airtable CSVs and reference data.
"""
import sqlite3
import csv
import os
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
DB_PATH = DATA_DIR / "local_erp.db"

if DB_PATH.exists():
    DB_PATH.unlink()

conn = sqlite3.connect(str(DB_PATH))
cur = conn.cursor()

files = {
    'approver_matrix': DATA_DIR / "uploads/approver_matrix-Grid view.csv",
    'goods_receipt': DATA_DIR / "uploads/goods_receipt-Grid view.csv",
    'invoice_header': DATA_DIR / "uploads/invoice_header-Grid view.csv",
    'invoice_line': DATA_DIR / "uploads/invoice_line-Grid view.csv",
    'material': DATA_DIR / "uploads/material-Grid view.csv",
    'po_line': DATA_DIR / "uploads/po_line-Grid view.csv",
    'unit_conversion': DATA_DIR / "uploads/unit_conversion-Grid view.csv",
    'po_header': Path("setup_kit/csv_plain/po_header.csv"),
    'prior_invoice': DATA_DIR / "RSEG_Prior_Invoiced.csv",
    'vendor': DATA_DIR / "vendor_master.csv",
}

header_map = {
    'BELNR': 'invoice_doc_number', 'GJAHR': 'fiscal_year', 'BUZEI': 'invoice_line_number',
    'LIFNR': 'vendor_id', 'XBLNR': 'vendor_invoice_number', 'BLDAT': 'invoice_date',
    'BUDAT': 'posting_date', 'EBELN': 'po_number', 'EBELP': 'po_item', 'MATNR': 'material_id',
    'MENGE': 'invoiced_qty', 'BSTME': 'order_unit', 'UNIT_PRICE': 'unit_price',
    'WRBTR': 'net_amount', 'FINAL_INVOICE': 'final_invoice_flag', 'STATUS': 'status',
    'REVERSAL_DATE': 'reversal_date'
}

for tbl, path in files.items():
    if not path.exists():
        print(f"Skipping {tbl}, path not found: {path}")
        continue
    with open(path, encoding="utf-8-sig", errors="ignore") as fp:
        reader = csv.reader(fp)
        raw_headers = next(reader)
        headers = [header_map.get(h.strip(), h.strip()) for h in raw_headers]
        
        cols = ", ".join([f'"{h}" TEXT' for h in headers])
        cur.execute(f'CREATE TABLE IF NOT EXISTS {tbl} (record_id TEXT PRIMARY KEY, {cols})')
        
        qmarks = ", ".join(["?"] * (len(headers) + 1))
        col_list = ", ".join([f'"{h}"' for h in headers])
        insert_sql = f'INSERT INTO {tbl} (record_id, {col_list}) VALUES ({qmarks})'
        
        for idx, row in enumerate(reader, start=1):
            rec_id = f"rec_{tbl}_{idx:05d}"
            row_data = (row + [""] * len(headers))[:len(headers)]
            cur.execute(insert_sql, [rec_id] + row_data)
            
    cur.execute(f"SELECT count(*) FROM {tbl}")
    count = cur.fetchone()[0]
    print(f"✅ {tbl}: {count} records loaded")

conn.commit()
conn.close()
print("Local ERP DB seeded successfully at", DB_PATH)
