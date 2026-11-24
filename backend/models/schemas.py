"""
Pydantic models for internal domain objects and API responses.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────────

class InvoiceStatus(str, Enum):
    PARKED = "Parked"
    PROCESSING = "Processing"
    PASSED = "Passed"
    ESCALATED = "Escalated"
    STOPPED = "Stopped"


class MatchOutcome(str, Enum):
    PASS = "Pass"
    ESCALATE = "Escalate"
    STOP = "Stop"


class MaterialCategory(str, Enum):
    BULK = "bulk"
    MANUFACTURED = "manufactured"
    SERVICE = "service"
    CAPEX = "capex"


class ValueBand(str, Enum):
    BAND_1 = "Band 1"  # <= 1,00,000
    BAND_2 = "Band 2"  # <= 10,00,000
    BAND_3 = "Band 3"  # > 10,00,000


# ── Domain Models ────────────────────────────────────────────────────────

class InvoiceHeader(BaseModel):
    record_id: str = ""  # Airtable record ID
    invoice_doc_number: str
    fiscal_year: int = 2026
    company_code: str = ""
    vendor_id: str = ""
    vendor_name: str = ""
    vendor_gstin: str = ""
    vendor_invoice_number: str = ""
    invoice_date: str = ""
    posting_date: str = ""
    parked_at: str = ""
    parked_by: str = ""
    po_numbers_quoted: str = ""
    currency: str = "INR"
    gross_amount: str = ""  # kept as string — may contain Indian formatting
    gst_amount: float = 0.0
    status: str = "Parked"
    invoice_pdf_path: str = ""


class InvoiceLine(BaseModel):
    record_id: str = ""
    invoice_doc_number: str
    invoice_line_number: int
    po_number: str
    po_item_quoted: str  # may be "10", "10/20", "10 & 20", etc.
    material_id: str
    item_text: str = ""
    hsn_sac_code: str = ""
    billed_qty: float
    billed_unit: str
    unit_price: float
    line_net_amount: float
    gst_rate_pct: float = 0.0
    gst_amount: float = 0.0


class POLine(BaseModel):
    record_id: str = ""
    po_number: str
    po_item: int
    material_id: str
    item_text: str = ""
    material_group: str = ""
    plant_code: str = ""
    account_assignment: str = ""
    item_category: str = ""
    ordered_qty: float
    order_unit: str
    net_price: float
    price_unit: int = 1
    line_net_value: float = 0.0
    over_delivery_tolerance_pct: Optional[float] = 0.0
    delivery_completed_flag: str = ""
    final_invoice_flag: str = ""
    deletion_flag: str = ""
    line_status: str = ""
    delivery_date: str = ""
    buyer_note: str = ""


class POHeader(BaseModel):
    record_id: str = ""
    po_number: str
    company_code: str = ""
    po_type: str = ""
    vendor_id: str = ""
    vendor_name: str = ""
    purchasing_org: str = ""
    buyer_group: str = ""
    po_date: str = ""
    currency: str = "INR"
    po_net_value: float = 0.0
    payment_terms: str = ""
    line_count: int = 0


class GoodsReceipt(BaseModel):
    record_id: str = ""
    receipt_doc_number: str
    receipt_doc_year: int = 2026
    receipt_doc_line: int = 1
    movement_type: int  # 101, 102, 122
    posting_date: str = ""
    po_number: str
    po_item: int
    material_id: str = ""
    plant_code: str = ""
    vendor_id: str = ""
    qty_entered: float
    qty_unit_entered: str
    original_receipt_doc: str = ""
    original_receipt_line: str = ""
    delivery_note_ref: str = ""
    weighbridge_slip: str = ""
    vehicle_number: str = ""
    remark: str = ""


class Material(BaseModel):
    record_id: str = ""
    material_id: str
    description: str = ""
    material_type: str = ""
    material_group: str = ""
    material_group_text: str = ""
    base_unit: str
    usual_order_unit: str = ""
    category: str  # bulk, manufactured, service, capex
    hsn_sac_code: str = ""
    gst_rate_pct: float = 0.0


class UnitConversion(BaseModel):
    record_id: str = ""
    material_id: str
    description: str = ""
    alternative_unit: str
    base_units: float  # e.g. 1000 (KG per MT)
    alternative_units: float = 1.0
    base_unit: str
    reads_as: str = ""


class ApproverRule(BaseModel):
    record_id: str = ""
    rule_id: str
    trigger: str
    value_band: str
    categories: str  # semicolon-separated
    plant_code: str
    approver_role: str
    approver_name: str
    approver_email: str
    seniority_level: int


class PriorInvoice(BaseModel):
    record_id: str = ""
    invoice_doc_number: str
    fiscal_year: int = 2026
    invoice_line_number: int = 1
    vendor_id: str = ""
    vendor_invoice_number: str = ""
    invoice_date: str = ""
    posting_date: str = ""
    po_number: str
    po_item: int
    material_id: str = ""
    invoiced_qty: float
    order_unit: str = ""
    unit_price: float = 0.0
    net_amount: float = 0.0
    final_invoice_flag: str = ""
    status: str = "Posted"
    reversal_date: str = ""


# ── Line-level match result ──────────────────────────────────────────────

class LineMatchResult(BaseModel):
    invoice_doc_number: str
    invoice_line_number: int
    po_number: str
    po_items_matched: list[int] = Field(default_factory=list)
    material_id: str = ""
    category: str = ""  # bulk, manufactured, etc.
    value_band: str = ""  # Band 1, Band 2, Band 3

    # Quantities (all in PO order unit)
    billed_qty_converted: float = 0.0
    po_order_unit: str = ""
    net_received_qty: float = 0.0
    prior_invoiced_qty: float = 0.0
    available_qty: float = 0.0
    over_delivery_allowance: float = 0.0

    # Price
    po_price_per_unit: float = 0.0
    value_at_po_price: float = 0.0
    invoice_line_net_amount: float = 0.0

    # Variances
    price_variance_inr: float = 0.0
    price_variance_pct: float = 0.0
    qty_variance_qty: float = 0.0
    qty_variance_pct: float = 0.0
    qty_variance_inr: float = 0.0

    # Limits
    price_pass_limit_inr: float = 0.0
    price_stop_limit_inr: float = 0.0
    qty_pass_limit_pct: float = 0.0
    qty_stop_limit_pct: float = 0.0

    # Outcome
    outcome: MatchOutcome = MatchOutcome.PASS
    reasons: list[str] = Field(default_factory=list)
    clauses: list[str] = Field(default_factory=list)

    # Approver (populated if escalated)
    approver_rule_id: str = ""
    approver_name: str = ""
    approver_email: str = ""
    approver_role: str = ""
    approver_seniority: int = 0

    # UOM conversion used
    uom_conversion_used: str = ""


class InvoiceMatchResult(BaseModel):
    invoice_doc_number: str
    vendor_id: str = ""
    vendor_name: str = ""
    vendor_invoice_number: str = ""
    overall_outcome: MatchOutcome = MatchOutcome.PASS
    overall_reasons: list[str] = Field(default_factory=list)
    line_results: list[LineMatchResult] = Field(default_factory=list)

    # Overall approver (highest seniority from escalated lines)
    final_approver_name: str = ""
    final_approver_email: str = ""
    final_approver_role: str = ""

    # PO cumulative check
    po_cumulative_triggered: bool = False
    po_cumulative_details: dict = Field(default_factory=dict)

    matched_at: datetime = Field(default_factory=datetime.now)


# ── API response models ──────────────────────────────────────────────────

class ProcessInvoiceResponse(BaseModel):
    success: bool
    invoice_doc_number: str
    outcome: str
    message: str
    details: Optional[InvoiceMatchResult] = None


class AuditLogEntry(BaseModel):
    id: int = 0
    timestamp: str
    invoice_doc_number: str
    event_type: str
    outcome: str = ""
    actor: str = ""
    details: str = ""


class UploadPDFResponse(BaseModel):
    success: bool
    message: str
    extracted_data: Optional[dict] = None
    match_result: Optional[InvoiceMatchResult] = None
