"""
Centralised configuration loaded from .env or environment variables.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

from dotenv import load_dotenv

# Load .env from backend/ directory
_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(_ENV_PATH)


# ── Airtable ────────────────────────────────────────────────────────────
AIRTABLE_API_KEY: str = os.environ.get("AIRTABLE_API_KEY", "")
AIRTABLE_BASE_ID: str = os.environ.get("AIRTABLE_BASE_ID", "")

# Airtable table names (plain names matching csv_plain/ headers)
AT_INVOICE_HEADER = "invoice_header"
AT_INVOICE_LINE = "invoice_line"
AT_PO_HEADER = "po_header"
AT_PO_LINE = "po_line"
AT_GOODS_RECEIPT = "goods_receipt"
AT_MATERIAL = "material"
AT_UNIT_CONVERSION = "unit_conversion"
AT_APPROVER_MATRIX = "approver_matrix"
AT_PRIOR_INVOICE = "prior_invoice"
AT_VENDOR = "vendor"

# ── Slack ────────────────────────────────────────────────────────────────
SLACK_BOT_TOKEN: str = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_SIGNING_SECRET: str = os.environ.get("SLACK_SIGNING_SECRET", "")
SLACK_CHANNEL_ID: str = os.environ.get("SLACK_CHANNEL_ID", "")

# ── Gemini ───────────────────────────────────────────────────────────────
GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest")

# ── Business date ────────────────────────────────────────────────────────
IST = timezone(timedelta(hours=5, minutes=30))
_raw_biz_date = os.environ.get("BUSINESS_DATE", "2026-10-09T18:00:00+05:30")
BUSINESS_DATE: datetime = datetime.fromisoformat(_raw_biz_date)

# ── Data Source Mode: "airtable" or "local" (SQLite mock ERP when Airtable limits hit) ──
ERP_DATA_SOURCE: str = os.environ.get("ERP_DATA_SOURCE", "local")

# ── Paths ────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Robust DATA_DIR resolution (supports both root-repo and backend-only deployment)
_custom_data_dir = os.environ.get("DATA_DIR")
if _custom_data_dir:
    DATA_DIR = Path(_custom_data_dir).resolve()
elif (PROJECT_ROOT / "data").exists():
    DATA_DIR = PROJECT_ROOT / "data"
elif (Path(__file__).resolve().parent / "data").exists():
    DATA_DIR = Path(__file__).resolve().parent / "data"
else:
    DATA_DIR = PROJECT_ROOT / "data"

LOCAL_ERP_DB_PATH = DATA_DIR / "local_erp.db"
AUDIT_DB_PATH = DATA_DIR / "audit.db"
VARIANCE_POLICY_PATH = DATA_DIR / "Variance_Policy.md"
VENDOR_MASTER_PATH = DATA_DIR / "vendor_master.csv"
PRIOR_INVOICED_PATH = DATA_DIR / "RSEG_Prior_Invoiced.csv"
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
