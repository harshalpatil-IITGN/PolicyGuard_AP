"""
ERP Client — Dual-mode data access layer for Ashvaka ERP.
Seamlessly switches between:
  1. "local": SQLite database (data/local_erp.db) populated directly from your downloaded Airtable CSVs (zero row limits, $0 cost, instant, offline-capable)
  2. "airtable": pyairtable live API connection

Every function returns identical Pydantic domain models.
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Optional

from pyairtable import Api

from config import (
    AIRTABLE_API_KEY,
    AIRTABLE_BASE_ID,
    ERP_DATA_SOURCE,
    LOCAL_ERP_DB_PATH,
    AT_INVOICE_HEADER,
    AT_INVOICE_LINE,
    AT_PO_HEADER,
    AT_PO_LINE,
    AT_GOODS_RECEIPT,
    AT_MATERIAL,
    AT_UNIT_CONVERSION,
    AT_APPROVER_MATRIX,
    AT_PRIOR_INVOICE,
)
from models.schemas import (
    InvoiceHeader,
    InvoiceLine,
    POHeader,
    POLine,
    GoodsReceipt,
    Material,
    UnitConversion,
    ApproverRule,
    PriorInvoice,
    InvoiceStatus,
)

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# Airtable client (lazy singleton)
# ═══════════════════════════════════════════════════════════════════════════

_api: Optional[Api] = None


def _get_api() -> Api:
    global _api
    if _api is None:
        _api = Api(AIRTABLE_API_KEY)
    return _api


def _table(name: str):
    return _get_api().table(AIRTABLE_BASE_ID, name)


# ═══════════════════════════════════════════════════════════════════════════
# Local SQLite client
# ═══════════════════════════════════════════════════════════════════════════

def _get_db():
    conn = sqlite3.connect(str(LOCAL_ERP_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _safe_float(val, default: float = 0.0) -> float:
    if val is None or val == "":
        return default
    if isinstance(val, (int, float)):
        return float(val)
    cleaned = str(val).replace(",", "").replace(" ", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return default


def _safe_int(val, default: int = 0) -> int:
    if val is None or val == "":
        return default
    try:
        return int(float(str(val).replace(",", "").strip()))
    except (ValueError, TypeError):
        return default


def _safe_str(val, default: str = "") -> str:
    if val is None:
        return default
    return str(val).strip()


# ═══════════════════════════════════════════════════════════════════════════
# Invoice Header
# ═══════════════════════════════════════════════════════════════════════════

def get_invoice_header(invoice_doc_number: str) -> Optional[InvoiceHeader]:
    """Fetch a single invoice header by its document number."""
    if ERP_DATA_SOURCE == "local":
        with _get_db() as conn:
            row = conn.execute(
                "SELECT * FROM invoice_header WHERE invoice_doc_number = ?",
                (str(invoice_doc_number),),
            ).fetchone()
            if not row:
                return None
            f = dict(row)
            return InvoiceHeader(
                record_id=f.get("record_id", f"rec_{invoice_doc_number}"),
                invoice_doc_number=_safe_str(f.get("invoice_doc_number")),
                fiscal_year=_safe_int(f.get("fiscal_year"), 2026),
                company_code=_safe_str(f.get("company_code")),
                vendor_id=_safe_str(f.get("vendor_id")),
                vendor_name=_safe_str(f.get("vendor_name")),
                vendor_gstin=_safe_str(f.get("vendor_gstin")),
                vendor_invoice_number=_safe_str(f.get("vendor_invoice_number")),
                invoice_date=_safe_str(f.get("invoice_date")),
                posting_date=_safe_str(f.get("posting_date")),
                parked_at=_safe_str(f.get("parked_at")),
                parked_by=_safe_str(f.get("parked_by")),
                po_numbers_quoted=_safe_str(f.get("po_numbers_quoted")),
                currency=_safe_str(f.get("currency"), "INR"),
                gross_amount=_safe_str(f.get("gross_amount")),
                gst_amount=_safe_float(f.get("gst_amount")),
                status=_safe_str(f.get("status"), "Parked"),
                invoice_pdf_path=_safe_str(f.get("invoice_pdf_path")),
            )
    else:
        records = _table(AT_INVOICE_HEADER).all(
            formula=f"{{invoice_doc_number}}='{invoice_doc_number}'"
        )
        if not records:
            return None
        r = records[0]
        f = r["fields"]
        return InvoiceHeader(
            record_id=r["id"],
            invoice_doc_number=_safe_str(f.get("invoice_doc_number")),
            fiscal_year=_safe_int(f.get("fiscal_year"), 2026),
            company_code=_safe_str(f.get("company_code")),
            vendor_id=_safe_str(f.get("vendor_id")),
            vendor_name=_safe_str(f.get("vendor_name")),
            vendor_gstin=_safe_str(f.get("vendor_gstin")),
            vendor_invoice_number=_safe_str(f.get("vendor_invoice_number")),
            invoice_date=_safe_str(f.get("invoice_date")),
            posting_date=_safe_str(f.get("posting_date")),
            parked_at=_safe_str(f.get("parked_at")),
            parked_by=_safe_str(f.get("parked_by")),
            po_numbers_quoted=_safe_str(f.get("po_numbers_quoted")),
            currency=_safe_str(f.get("currency"), "INR"),
            gross_amount=_safe_str(f.get("gross_amount")),
            gst_amount=_safe_float(f.get("gst_amount")),
            status=_safe_str(f.get("status"), "Parked"),
            invoice_pdf_path=_safe_str(f.get("invoice_pdf_path")),
        )


def get_all_invoices(status: Optional[str] = None) -> list[InvoiceHeader]:
    """Fetch all invoices, optionally filtered by status."""
    if ERP_DATA_SOURCE == "local":
        with _get_db() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM invoice_header WHERE lower(status) = lower(?)",
                    (status,),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM invoice_header").fetchall()

            results = []
            for r in rows:
                f = dict(r)
                results.append(InvoiceHeader(
                    record_id=f.get("record_id", f"rec_{f.get('invoice_doc_number')}"),
                    invoice_doc_number=_safe_str(f.get("invoice_doc_number")),
                    fiscal_year=_safe_int(f.get("fiscal_year"), 2026),
                    company_code=_safe_str(f.get("company_code")),
                    vendor_id=_safe_str(f.get("vendor_id")),
                    vendor_name=_safe_str(f.get("vendor_name")),
                    vendor_gstin=_safe_str(f.get("vendor_gstin")),
                    vendor_invoice_number=_safe_str(f.get("vendor_invoice_number")),
                    invoice_date=_safe_str(f.get("invoice_date")),
                    posting_date=_safe_str(f.get("posting_date")),
                    parked_at=_safe_str(f.get("parked_at")),
                    parked_by=_safe_str(f.get("parked_by")),
                    po_numbers_quoted=_safe_str(f.get("po_numbers_quoted")),
                    currency=_safe_str(f.get("currency"), "INR"),
                    gross_amount=_safe_str(f.get("gross_amount")),
                    gst_amount=_safe_float(f.get("gst_amount")),
                    status=_safe_str(f.get("status"), "Parked"),
                    invoice_pdf_path=_safe_str(f.get("invoice_pdf_path")),
                ))
            return results
    else:
        formula = f"{{status}}='{status}'" if status else None
        records = _table(AT_INVOICE_HEADER).all(formula=formula) if formula else _table(AT_INVOICE_HEADER).all()
        results = []
        for r in records:
            f = r["fields"]
            results.append(InvoiceHeader(
                record_id=r["id"],
                invoice_doc_number=_safe_str(f.get("invoice_doc_number")),
                fiscal_year=_safe_int(f.get("fiscal_year"), 2026),
                company_code=_safe_str(f.get("company_code")),
                vendor_id=_safe_str(f.get("vendor_id")),
                vendor_name=_safe_str(f.get("vendor_name")),
                vendor_gstin=_safe_str(f.get("vendor_gstin")),
                vendor_invoice_number=_safe_str(f.get("vendor_invoice_number")),
                invoice_date=_safe_str(f.get("invoice_date")),
                posting_date=_safe_str(f.get("posting_date")),
                parked_at=_safe_str(f.get("parked_at")),
                parked_by=_safe_str(f.get("parked_by")),
                po_numbers_quoted=_safe_str(f.get("po_numbers_quoted")),
                currency=_safe_str(f.get("currency"), "INR"),
                gross_amount=_safe_str(f.get("gross_amount")),
                gst_amount=_safe_float(f.get("gst_amount")),
                status=_safe_str(f.get("status"), "Parked"),
                invoice_pdf_path=_safe_str(f.get("invoice_pdf_path")),
            ))
        return results


def get_all_parked_invoices() -> list[InvoiceHeader]:
    return get_all_invoices(status="Parked")


def update_invoice_status(record_id: str, status: InvoiceStatus) -> None:
    """Update the status of an invoice_header record."""
    if ERP_DATA_SOURCE == "local":
        with _get_db() as conn:
            conn.execute(
                "UPDATE invoice_header SET status = ? WHERE record_id = ? OR invoice_doc_number = ?",
                (status.value, record_id, record_id),
            )
            conn.commit()
            logger.info(f"[LOCAL ERP] Updated invoice {record_id} status to {status.value}")
    else:
        _table(AT_INVOICE_HEADER).update(record_id, {"status": status.value})
        logger.info(f"[AIRTABLE] Updated invoice {record_id} status to {status.value}")


def reset_all_invoices(status: InvoiceStatus = InvoiceStatus.PARKED) -> int:
    """Reset status of all invoice_header records back to Parked."""
    if ERP_DATA_SOURCE == "local":
        with _get_db() as conn:
            cursor = conn.execute("UPDATE invoice_header SET status = ?", (status.value,))
            count = cursor.rowcount
            conn.commit()
            logger.info(f"[LOCAL ERP] Reset {count} invoices to {status.value}")
            return count
    else:
        records = _table(AT_INVOICE_HEADER).all()
        for r in records:
            _table(AT_INVOICE_HEADER).update(r["id"], {"status": status.value})
        return len(records)


# ═══════════════════════════════════════════════════════════════════════════
# Invoice Lines
# ═══════════════════════════════════════════════════════════════════════════

def get_invoice_lines(invoice_doc_number: str) -> list[InvoiceLine]:
    """Fetch all lines for a given invoice document number."""
    if ERP_DATA_SOURCE == "local":
        with _get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM invoice_line WHERE invoice_doc_number = ? ORDER BY CAST(invoice_line_number AS INTEGER)",
                (str(invoice_doc_number),),
            ).fetchall()
            lines = []
            for r in rows:
                f = dict(r)
                lines.append(InvoiceLine(
                    record_id=f.get("record_id", ""),
                    invoice_doc_number=_safe_str(f.get("invoice_doc_number")),
                    invoice_line_number=_safe_int(f.get("invoice_line_number"), 1),
                    po_number=_safe_str(f.get("po_number")),
                    po_item_quoted=_safe_str(f.get("po_item_quoted")),
                    material_id=_safe_str(f.get("material_id")),
                    item_text=_safe_str(f.get("item_text")),
                    hsn_sac_code=_safe_str(f.get("hsn_sac_code")),
                    billed_qty=_safe_float(f.get("billed_qty")),
                    billed_unit=_safe_str(f.get("billed_unit")),
                    unit_price=_safe_float(f.get("unit_price")),
                    line_net_amount=_safe_float(f.get("line_net_amount")),
                    gst_rate_pct=_safe_float(f.get("gst_rate_pct")),
                    gst_amount=_safe_float(f.get("gst_amount")),
                ))
            return lines
    else:
        records = _table(AT_INVOICE_LINE).all(
            formula=f"{{invoice_doc_number}}='{invoice_doc_number}'"
        )
        lines = []
        for r in records:
            f = r["fields"]
            lines.append(InvoiceLine(
                record_id=r["id"],
                invoice_doc_number=_safe_str(f.get("invoice_doc_number")),
                invoice_line_number=_safe_int(f.get("invoice_line_number"), 1),
                po_number=_safe_str(f.get("po_number")),
                po_item_quoted=_safe_str(f.get("po_item_quoted")),
                material_id=_safe_str(f.get("material_id")),
                item_text=_safe_str(f.get("item_text")),
                hsn_sac_code=_safe_str(f.get("hsn_sac_code")),
                billed_qty=_safe_float(f.get("billed_qty")),
                billed_unit=_safe_str(f.get("billed_unit")),
                unit_price=_safe_float(f.get("unit_price")),
                line_net_amount=_safe_float(f.get("line_net_amount")),
                gst_rate_pct=_safe_float(f.get("gst_rate_pct")),
                gst_amount=_safe_float(f.get("gst_amount")),
            ))
        lines.sort(key=lambda x: x.invoice_line_number)
        return lines


# ═══════════════════════════════════════════════════════════════════════════
# PO Header
# ═══════════════════════════════════════════════════════════════════════════

def get_po_header(po_number: str) -> Optional[POHeader]:
    """Fetch a PO header by its number."""
    if ERP_DATA_SOURCE == "local":
        with _get_db() as conn:
            row = conn.execute(
                "SELECT * FROM po_header WHERE po_number = ?",
                (str(po_number),),
            ).fetchone()
            if not row:
                return None
            f = dict(row)
            return POHeader(
                record_id=f.get("record_id", ""),
                po_number=_safe_str(f.get("po_number")),
                company_code=_safe_str(f.get("company_code")),
                po_type=_safe_str(f.get("po_type")),
                vendor_id=_safe_str(f.get("vendor_id")),
                vendor_name=_safe_str(f.get("vendor_name")),
                purchasing_org=_safe_str(f.get("purchasing_org")),
                buyer_group=_safe_str(f.get("buyer_group")),
                po_date=_safe_str(f.get("po_date")),
                currency=_safe_str(f.get("currency"), "INR"),
                po_net_value=_safe_float(f.get("po_net_value")),
                payment_terms=_safe_str(f.get("payment_terms")),
                line_count=_safe_int(f.get("line_count")),
            )
    else:
        records = _table(AT_PO_HEADER).all(
            formula=f"{{po_number}}='{po_number}'"
        )
        if not records:
            return None
        r = records[0]
        f = r["fields"]
        return POHeader(
            record_id=r["id"],
            po_number=_safe_str(f.get("po_number")),
            company_code=_safe_str(f.get("company_code")),
            po_type=_safe_str(f.get("po_type")),
            vendor_id=_safe_str(f.get("vendor_id")),
            vendor_name=_safe_str(f.get("vendor_name")),
            purchasing_org=_safe_str(f.get("purchasing_org")),
            buyer_group=_safe_str(f.get("buyer_group")),
            po_date=_safe_str(f.get("po_date")),
            currency=_safe_str(f.get("currency"), "INR"),
            po_net_value=_safe_float(f.get("po_net_value")),
            payment_terms=_safe_str(f.get("payment_terms")),
            line_count=_safe_int(f.get("line_count")),
        )


# ═══════════════════════════════════════════════════════════════════════════
# PO Lines
# ═══════════════════════════════════════════════════════════════════════════

def get_po_line(po_number: str, po_item: int) -> Optional[POLine]:
    """Fetch a single PO line."""
    if ERP_DATA_SOURCE == "local":
        with _get_db() as conn:
            row = conn.execute(
                "SELECT * FROM po_line WHERE po_number = ? AND CAST(po_item AS INTEGER) = ?",
                (str(po_number), int(po_item)),
            ).fetchone()
            if not row:
                return None
            return _parse_po_line_dict(dict(row))
    else:
        records = _table(AT_PO_LINE).all(
            formula=f"AND({{po_number}}='{po_number}', {{po_item}}={po_item})"
        )
        if not records:
            return None
        return _parse_po_line(records[0])


def get_po_lines_for_po(po_number: str) -> list[POLine]:
    """Fetch all lines for a PO."""
    if ERP_DATA_SOURCE == "local":
        with _get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM po_line WHERE po_number = ?",
                (str(po_number),),
            ).fetchall()
            return [_parse_po_line_dict(dict(r)) for r in rows]
    else:
        records = _table(AT_PO_LINE).all(
            formula=f"{{po_number}}='{po_number}'"
        )
        return [_parse_po_line(r) for r in records]


def _parse_po_line(r: dict) -> POLine:
    f = r["fields"]
    return POLine(
        record_id=r["id"],
        po_number=_safe_str(f.get("po_number")),
        po_item=_safe_int(f.get("po_item")),
        material_id=_safe_str(f.get("material_id")),
        item_text=_safe_str(f.get("item_text")),
        material_group=_safe_str(f.get("material_group")),
        plant_code=_safe_str(f.get("plant_code")),
        account_assignment=_safe_str(f.get("account_assignment")),
        item_category=_safe_str(f.get("item_category")),
        ordered_qty=_safe_float(f.get("ordered_qty")),
        order_unit=_safe_str(f.get("order_unit")),
        net_price=_safe_float(f.get("net_price")),
        price_unit=_safe_int(f.get("price_unit"), 1),
        line_net_value=_safe_float(f.get("line_net_value")),
        over_delivery_tolerance_pct=_safe_float(f.get("over_delivery_tolerance_pct")),
        delivery_completed_flag=_safe_str(f.get("delivery_completed_flag")),
        final_invoice_flag=_safe_str(f.get("final_invoice_flag")),
        deletion_flag=_safe_str(f.get("deletion_flag")),
        line_status=_safe_str(f.get("line_status")),
        delivery_date=_safe_str(f.get("delivery_date")),
        buyer_note=_safe_str(f.get("buyer_note")),
    )


def _parse_po_line_dict(f: dict) -> POLine:
    return POLine(
        record_id=f.get("record_id", ""),
        po_number=_safe_str(f.get("po_number")),
        po_item=_safe_int(f.get("po_item")),
        material_id=_safe_str(f.get("material_id")),
        item_text=_safe_str(f.get("item_text")),
        material_group=_safe_str(f.get("material_group")),
        plant_code=_safe_str(f.get("plant_code")),
        account_assignment=_safe_str(f.get("account_assignment")),
        item_category=_safe_str(f.get("item_category")),
        ordered_qty=_safe_float(f.get("ordered_qty")),
        order_unit=_safe_str(f.get("order_unit")),
        net_price=_safe_float(f.get("net_price")),
        price_unit=_safe_int(f.get("price_unit"), 1),
        line_net_value=_safe_float(f.get("line_net_value")),
        over_delivery_tolerance_pct=_safe_float(f.get("over_delivery_tolerance_pct")),
        delivery_completed_flag=_safe_str(f.get("delivery_completed_flag")),
        final_invoice_flag=_safe_str(f.get("final_invoice_flag")),
        deletion_flag=_safe_str(f.get("deletion_flag")),
        line_status=_safe_str(f.get("line_status")),
        delivery_date=_safe_str(f.get("delivery_date")),
        buyer_note=_safe_str(f.get("buyer_note")),
    )


# ═══════════════════════════════════════════════════════════════════════════
# Goods Receipts
# ═══════════════════════════════════════════════════════════════════════════

def get_goods_receipts(po_number: str, po_item: int) -> list[GoodsReceipt]:
    """Fetch all goods receipt rows for a specific PO line."""
    if ERP_DATA_SOURCE == "local":
        with _get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM goods_receipt WHERE po_number = ? AND CAST(po_item AS INTEGER) = ?",
                (str(po_number), int(po_item)),
            ).fetchall()
            receipts = []
            for r in rows:
                f = dict(r)
                receipts.append(GoodsReceipt(
                    record_id=f.get("record_id", ""),
                    receipt_doc_number=_safe_str(f.get("receipt_doc_number")),
                    receipt_doc_year=_safe_int(f.get("receipt_doc_year"), 2026),
                    receipt_doc_line=_safe_int(f.get("receipt_doc_line"), 1),
                    movement_type=_safe_int(f.get("movement_type")),
                    posting_date=_safe_str(f.get("posting_date")),
                    po_number=_safe_str(f.get("po_number")),
                    po_item=_safe_int(f.get("po_item")),
                    material_id=_safe_str(f.get("material_id")),
                    plant_code=_safe_str(f.get("plant_code")),
                    vendor_id=_safe_str(f.get("vendor_id")),
                    qty_entered=_safe_float(f.get("qty_entered")),
                    qty_unit_entered=_safe_str(f.get("qty_unit_entered")),
                    original_receipt_doc=_safe_str(f.get("original_receipt_doc")),
                    original_receipt_line=_safe_str(f.get("original_receipt_line")),
                    delivery_note_ref=_safe_str(f.get("delivery_note_ref")),
                    weighbridge_slip=_safe_str(f.get("weighbridge_slip")),
                    vehicle_number=_safe_str(f.get("vehicle_number")),
                    remark=_safe_str(f.get("remark")),
                ))
            return receipts
    else:
        records = _table(AT_GOODS_RECEIPT).all(
            formula=f"AND({{po_number}}='{po_number}', {{po_item}}={po_item})"
        )
        receipts = []
        for r in records:
            f = r["fields"]
            receipts.append(GoodsReceipt(
                record_id=r["id"],
                receipt_doc_number=_safe_str(f.get("receipt_doc_number")),
                receipt_doc_year=_safe_int(f.get("receipt_doc_year"), 2026),
                receipt_doc_line=_safe_int(f.get("receipt_doc_line"), 1),
                movement_type=_safe_int(f.get("movement_type")),
                posting_date=_safe_str(f.get("posting_date")),
                po_number=_safe_str(f.get("po_number")),
                po_item=_safe_int(f.get("po_item")),
                material_id=_safe_str(f.get("material_id")),
                plant_code=_safe_str(f.get("plant_code")),
                vendor_id=_safe_str(f.get("vendor_id")),
                qty_entered=_safe_float(f.get("qty_entered")),
                qty_unit_entered=_safe_str(f.get("qty_unit_entered")),
                original_receipt_doc=_safe_str(f.get("original_receipt_doc")),
                original_receipt_line=_safe_str(f.get("original_receipt_line")),
                delivery_note_ref=_safe_str(f.get("delivery_note_ref")),
                weighbridge_slip=_safe_str(f.get("weighbridge_slip")),
                vehicle_number=_safe_str(f.get("vehicle_number")),
                remark=_safe_str(f.get("remark")),
            ))
        return receipts


# ═══════════════════════════════════════════════════════════════════════════
# Material
# ═══════════════════════════════════════════════════════════════════════════

def get_material(material_id: str) -> Optional[Material]:
    """Fetch material master data."""
    if ERP_DATA_SOURCE == "local":
        with _get_db() as conn:
            row = conn.execute(
                "SELECT * FROM material WHERE material_id = ?",
                (str(material_id),),
            ).fetchone()
            if not row:
                return None
            f = dict(row)
            return Material(
                record_id=f.get("record_id", ""),
                material_id=_safe_str(f.get("material_id")),
                description=_safe_str(f.get("description")),
                material_type=_safe_str(f.get("material_type")),
                material_group=_safe_str(f.get("material_group")),
                material_group_text=_safe_str(f.get("material_group_text")),
                base_unit=_safe_str(f.get("base_unit")),
                usual_order_unit=_safe_str(f.get("usual_order_unit")),
                category=_safe_str(f.get("category")),
                hsn_sac_code=_safe_str(f.get("hsn_sac_code")),
                gst_rate_pct=_safe_float(f.get("gst_rate_pct")),
            )
    else:
        records = _table(AT_MATERIAL).all(
            formula=f"{{material_id}}='{material_id}'"
        )
        if not records:
            return None
        r = records[0]
        f = r["fields"]
        return Material(
            record_id=r["id"],
            material_id=_safe_str(f.get("material_id")),
            description=_safe_str(f.get("description")),
            material_type=_safe_str(f.get("material_type")),
            material_group=_safe_str(f.get("material_group")),
            material_group_text=_safe_str(f.get("material_group_text")),
            base_unit=_safe_str(f.get("base_unit")),
            usual_order_unit=_safe_str(f.get("usual_order_unit")),
            category=_safe_str(f.get("category")),
            hsn_sac_code=_safe_str(f.get("hsn_sac_code")),
            gst_rate_pct=_safe_float(f.get("gst_rate_pct")),
        )


# ═══════════════════════════════════════════════════════════════════════════
# Unit Conversion
# ═══════════════════════════════════════════════════════════════════════════

def get_unit_conversions(material_id: str) -> list[UnitConversion]:
    """Fetch all unit conversion rows for a material."""
    if ERP_DATA_SOURCE == "local":
        with _get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM unit_conversion WHERE material_id = ?",
                (str(material_id),),
            ).fetchall()
            conversions = []
            for r in rows:
                f = dict(r)
                conversions.append(UnitConversion(
                    record_id=f.get("record_id", ""),
                    material_id=_safe_str(f.get("material_id")),
                    description=_safe_str(f.get("description")),
                    alternative_unit=_safe_str(f.get("alternative_unit")),
                    base_units=_safe_float(f.get("base_units")),
                    alternative_units=_safe_float(f.get("alternative_units"), 1.0),
                    base_unit=_safe_str(f.get("base_unit")),
                    reads_as=_safe_str(f.get("reads_as")),
                ))
            return conversions
    else:
        records = _table(AT_UNIT_CONVERSION).all(
            formula=f"{{material_id}}='{material_id}'"
        )
        conversions = []
        for r in records:
            f = r["fields"]
            conversions.append(UnitConversion(
                record_id=r["id"],
                material_id=_safe_str(f.get("material_id")),
                description=_safe_str(f.get("description")),
                alternative_unit=_safe_str(f.get("alternative_unit")),
                base_units=_safe_float(f.get("base_units")),
                alternative_units=_safe_float(f.get("alternative_units"), 1.0),
                base_unit=_safe_str(f.get("base_unit")),
                reads_as=_safe_str(f.get("reads_as")),
            ))
        return conversions


# ═══════════════════════════════════════════════════════════════════════════
# Approver Matrix
# ═══════════════════════════════════════════════════════════════════════════

def get_approver_matrix() -> list[ApproverRule]:
    """Fetch the full approver matrix."""
    if ERP_DATA_SOURCE == "local":
        with _get_db() as conn:
            rows = conn.execute("SELECT * FROM approver_matrix").fetchall()
            rules = []
            for r in rows:
                f = dict(r)
                rules.append(ApproverRule(
                    record_id=f.get("record_id", ""),
                    rule_id=_safe_str(f.get("rule_id")),
                    trigger=_safe_str(f.get("trigger")),
                    value_band=_safe_str(f.get("value_band")),
                    categories=_safe_str(f.get("categories")),
                    plant_code=_safe_str(f.get("plant_code")),
                    approver_role=_safe_str(f.get("approver_role")),
                    approver_name=_safe_str(f.get("approver_name")),
                    approver_email=_safe_str(f.get("approver_email")),
                    seniority_level=_safe_int(f.get("seniority_level"), 0),
                ))
            return rules
    else:
        records = _table(AT_APPROVER_MATRIX).all()
        rules = []
        for r in records:
            f = r["fields"]
            rules.append(ApproverRule(
                record_id=r["id"],
                rule_id=_safe_str(f.get("rule_id")),
                trigger=_safe_str(f.get("trigger")),
                value_band=_safe_str(f.get("value_band")),
                categories=_safe_str(f.get("categories")),
                plant_code=_safe_str(f.get("plant_code")),
                approver_role=_safe_str(f.get("approver_role")),
                approver_name=_safe_str(f.get("approver_name")),
                approver_email=_safe_str(f.get("approver_email")),
                seniority_level=_safe_int(f.get("seniority_level"), 0),
            ))
        return rules


# ═══════════════════════════════════════════════════════════════════════════
# Prior Invoiced
# ═══════════════════════════════════════════════════════════════════════════

def get_prior_invoices(po_number: str, po_item: int) -> list[PriorInvoice]:
    """Fetch prior invoiced records for a specific PO line."""
    if ERP_DATA_SOURCE == "local":
        with _get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM prior_invoice WHERE po_number = ? AND CAST(po_item AS INTEGER) = ?",
                (str(po_number), int(po_item)),
            ).fetchall()
            priors = []
            for r in rows:
                f = dict(r)
                priors.append(PriorInvoice(
                    record_id=f.get("record_id", ""),
                    invoice_doc_number=_safe_str(f.get("invoice_doc_number")),
                    fiscal_year=_safe_int(f.get("fiscal_year"), 2026),
                    invoice_line_number=_safe_int(f.get("invoice_line_number"), 1),
                    vendor_id=_safe_str(f.get("vendor_id")),
                    vendor_invoice_number=_safe_str(f.get("vendor_invoice_number")),
                    invoice_date=_safe_str(f.get("invoice_date")),
                    posting_date=_safe_str(f.get("posting_date")),
                    po_number=_safe_str(f.get("po_number")),
                    po_item=_safe_int(f.get("po_item")),
                    material_id=_safe_str(f.get("material_id")),
                    invoiced_qty=_safe_float(f.get("invoiced_qty")),
                    order_unit=_safe_str(f.get("order_unit")),
                    unit_price=_safe_float(f.get("unit_price")),
                    net_amount=_safe_float(f.get("net_amount")),
                    final_invoice_flag=_safe_str(f.get("final_invoice_flag")),
                    status=_safe_str(f.get("status"), "Posted"),
                    reversal_date=_safe_str(f.get("reversal_date")),
                ))
            return priors
    else:
        records = _table(AT_PRIOR_INVOICE).all(
            formula=f"AND({{po_number}}='{po_number}', {{po_item}}={po_item})"
        )
        priors = []
        for r in records:
            f = r["fields"]
            priors.append(PriorInvoice(
                record_id=r["id"],
                invoice_doc_number=_safe_str(f.get("invoice_doc_number")),
                fiscal_year=_safe_int(f.get("fiscal_year"), 2026),
                invoice_line_number=_safe_int(f.get("invoice_line_number"), 1),
                vendor_id=_safe_str(f.get("vendor_id")),
                vendor_invoice_number=_safe_str(f.get("vendor_invoice_number")),
                invoice_date=_safe_str(f.get("invoice_date")),
                posting_date=_safe_str(f.get("posting_date")),
                po_number=_safe_str(f.get("po_number")),
                po_item=_safe_int(f.get("po_item")),
                material_id=_safe_str(f.get("material_id")),
                invoiced_qty=_safe_float(f.get("invoiced_qty")),
                order_unit=_safe_str(f.get("order_unit")),
                unit_price=_safe_float(f.get("unit_price")),
                net_amount=_safe_float(f.get("net_amount")),
                final_invoice_flag=_safe_str(f.get("final_invoice_flag")),
                status=_safe_str(f.get("status"), "Posted"),
                reversal_date=_safe_str(f.get("reversal_date")),
            ))
        return priors


def get_prior_invoices_for_po(po_number: str) -> list[PriorInvoice]:
    """Fetch ALL prior invoiced records for an entire PO (for CUM-1 check)."""
    if ERP_DATA_SOURCE == "local":
        with _get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM prior_invoice WHERE po_number = ?",
                (str(po_number),),
            ).fetchall()
            priors = []
            for r in rows:
                f = dict(r)
                priors.append(PriorInvoice(
                    record_id=f.get("record_id", ""),
                    invoice_doc_number=_safe_str(f.get("invoice_doc_number")),
                    fiscal_year=_safe_int(f.get("fiscal_year"), 2026),
                    invoice_line_number=_safe_int(f.get("invoice_line_number"), 1),
                    vendor_id=_safe_str(f.get("vendor_id")),
                    vendor_invoice_number=_safe_str(f.get("vendor_invoice_number")),
                    invoice_date=_safe_str(f.get("invoice_date")),
                    posting_date=_safe_str(f.get("posting_date")),
                    po_number=_safe_str(f.get("po_number")),
                    po_item=_safe_int(f.get("po_item")),
                    material_id=_safe_str(f.get("material_id")),
                    invoiced_qty=_safe_float(f.get("invoiced_qty")),
                    order_unit=_safe_str(f.get("order_unit")),
                    unit_price=_safe_float(f.get("unit_price")),
                    net_amount=_safe_float(f.get("net_amount")),
                    final_invoice_flag=_safe_str(f.get("final_invoice_flag")),
                    status=_safe_str(f.get("status"), "Posted"),
                    reversal_date=_safe_str(f.get("reversal_date")),
                ))
            return priors
    else:
        records = _table(AT_PRIOR_INVOICE).all(
            formula=f"{{po_number}}='{po_number}'"
        )
        priors = []
        for r in records:
            f = r["fields"]
            priors.append(PriorInvoice(
                record_id=r["id"],
                invoice_doc_number=_safe_str(f.get("invoice_doc_number")),
                fiscal_year=_safe_int(f.get("fiscal_year"), 2026),
                invoice_line_number=_safe_int(f.get("invoice_line_number"), 1),
                vendor_id=_safe_str(f.get("vendor_id")),
                vendor_invoice_number=_safe_str(f.get("vendor_invoice_number")),
                invoice_date=_safe_str(f.get("invoice_date")),
                posting_date=_safe_str(f.get("posting_date")),
                po_number=_safe_str(f.get("po_number")),
                po_item=_safe_int(f.get("po_item")),
                material_id=_safe_str(f.get("material_id")),
                invoiced_qty=_safe_float(f.get("invoiced_qty")),
                order_unit=_safe_str(f.get("order_unit")),
                unit_price=_safe_float(f.get("unit_price")),
                net_amount=_safe_float(f.get("net_amount")),
                final_invoice_flag=_safe_str(f.get("final_invoice_flag")),
                status=_safe_str(f.get("status"), "Posted"),
                reversal_date=_safe_str(f.get("reversal_date")),
            ))
        return priors
