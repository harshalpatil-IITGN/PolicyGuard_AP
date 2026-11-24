"""
matching_engine.py — 100% Deterministic Three-Way Match Engine

Implements Ashvaka Industries Variance Policy FIN-AP-07 v3.2.
ALL math is pure Python — zero LLM involvement.

Public entry point: process_invoice(invoice_doc_number) -> InvoiceMatchResult
"""

from __future__ import annotations

import logging
import re
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from models.schemas import (
    ApproverRule,
    GoodsReceipt,
    InvoiceHeader,
    InvoiceLine,
    InvoiceMatchResult,
    InvoiceStatus,
    LineMatchResult,
    Material,
    MatchOutcome,
    POHeader,
    POLine,
    PriorInvoice,
    UnitConversion,
)
from services import airtable_client as at
from services import audit_logger as audit

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Constants — Variance Policy FIN-AP-07 v3.2
# ═══════════════════════════════════════════════════════════════════════════

# PV-2: Price variance pass/stop percentages by category
PRICE_TOLERANCE = {
    "bulk":         {"pass_pct": 2.0, "stop_pct": 5.0},
    "manufactured": {"pass_pct": 1.0, "stop_pct": 3.0},
    "service":      {"pass_pct": 0.5, "stop_pct": 2.0},
    "capex":        {"pass_pct": 0.25, "stop_pct": 1.5},
}

# PV-2: Pass cap and stop cap by value band
PRICE_CAPS = {
    "Band 1": {"pass_cap": 1_500.0,   "stop_cap": 7_500.0},
    "Band 2": {"pass_cap": 10_000.0,  "stop_cap": 50_000.0},
    "Band 3": {"pass_cap": 40_000.0,  "stop_cap": 200_000.0},
}

# QV-2: Bulk quantity tolerance
BULK_QTY_TOLERANCE = {
    "pass_pct": 0.5,
    "stop_pct": 2.0,
}

# CUM-1: PO cumulative limit
PO_CUM_LIMIT_PCT = 1.0
PO_CUM_LIMIT_CAP = 150_000.0

# UOM-1: General (fallback) conversions
GENERAL_CONVERSIONS = {
    ("MT", "KG"): 1000.0,  # 1 MT = 1000 KG
    ("KG", "MT"): 0.001,
    ("KM", "MTR"): 1000.0,
    ("MTR", "KM"): 0.001,
}

# UOM-2: Unit aliases (all mapped to canonical form, case-insensitive)
UNIT_ALIASES: dict[str, str] = {
    # MT
    "ton": "MT", "to": "MT", "tonne": "MT", "m.t.": "MT", "mts": "MT", "mt": "MT",
    # KG
    "kgs": "KG", "kg": "KG",
    # MTR
    "mtr": "MTR", "m": "MTR", "rmt": "MTR", "mtrs": "MTR",
    # KM
    "km": "KM",
    # EA
    "nos": "EA", "no.": "EA", "pcs": "EA", "ea": "EA",
    # BAG
    "bags": "BAG", "bag": "BAG",
    # CUM
    "m3": "CUM", "cu.m": "CUM", "cbm": "CUM", "cum": "CUM",
    # MANDAY
    "man-days": "MANDAY", "md": "MANDAY", "man day": "MANDAY", "manday": "MANDAY",
    # MONTH
    "month": "MONTH", "mon": "MONTH", "months": "MONTH",
    # TRIP
    "trips": "TRIP", "trip": "TRIP",
    # DAY
    "days": "DAY", "day": "DAY",
    # SET
    "set": "SET", "sets": "SET",
    # SAMPLE
    "samples": "SAMPLE", "sample": "SAMPLE",
    # QTR
    "quarter": "QTR", "qtr": "QTR",
    # HR
    "hrs": "HR", "hours": "HR", "hr": "HR",
    # PAIR
    "pairs": "PAIR", "pr": "PAIR", "pair": "PAIR",
    # BOX
    "box": "BOX", "boxes": "BOX",
    # DRUM
    "drums": "DRUM", "drum": "DRUM",
    # COIL
    "coils": "COIL", "coil": "COIL",
    # PAL
    "pallet": "PAL", "pallets": "PAL", "pal": "PAL",
    # PLATE
    "plates": "PLATE", "plate": "PLATE",
}

# ESC-1: Approver lookup by (value_band, category)
APPROVER_ROLE_MAP = {
    ("Band 1", "bulk"):         "Plant accounts head",
    ("Band 1", "manufactured"): "Plant accounts head",
    ("Band 1", "service"):      "Plant accounts head",
    ("Band 1", "capex"):        "Procurement head, materials",
    ("Band 2", "bulk"):         "Procurement head, materials",
    ("Band 2", "manufactured"): "Procurement head, materials",
    ("Band 2", "service"):      "Procurement head, services",
    ("Band 2", "capex"):        "CFO office",
    ("Band 3", "bulk"):         "CFO office",
    ("Band 3", "manufactured"): "CFO office",
    ("Band 3", "service"):      "CFO office",
    ("Band 3", "capex"):        "CFO office",
}

# Seniority: 1 = Plant accounts head, 2 = Procurement head, 3 = Financial controller
ROLE_SENIORITY = {
    "Plant accounts head": 1,
    "Procurement head, materials": 2,
    "Procurement head, services": 2,
    "Procurement head": 2,
    "CFO office": 3,
    "Financial controller": 3,
}


# ═══════════════════════════════════════════════════════════════════════════
# Unit normalisation helpers
# ═══════════════════════════════════════════════════════════════════════════

def normalise_unit(raw: str) -> str:
    """Normalise a unit string to its canonical form (UOM-2)."""
    cleaned = raw.strip()
    key = cleaned.lower()
    # Exact match first
    if key in UNIT_ALIASES:
        return UNIT_ALIASES[key]
    # Already canonical (uppercase)?
    if cleaned.upper() in {v for v in UNIT_ALIASES.values()}:
        return cleaned.upper()
    return cleaned.upper()


def convert_qty(
    qty: float,
    from_unit: str,
    to_unit: str,
    material_id: str,
    conversions: list[UnitConversion],
    base_unit: str,
) -> tuple[Optional[float], str]:
    """
    Convert qty from from_unit to to_unit using material-specific MARM first,
    then general conversions. Returns (converted_qty, description) or (None, reason).

    Strategy:
    1. If from_unit == to_unit → identity
    2. Try direct material conversion from MARM
    3. Try two-hop via base unit: from_unit → base → to_unit
    4. Try general conversions (MT↔KG, KM↔MTR)
    5. Fail with UOM-3
    """
    canon_from = normalise_unit(from_unit)
    canon_to = normalise_unit(to_unit)

    if canon_from == canon_to:
        return qty, f"Same unit ({canon_from})"

    # Build lookup: {alt_unit: (base_units_per_alt, base_unit)}
    marm: dict[str, tuple[float, float, str]] = {}
    for c in conversions:
        alt = normalise_unit(c.alternative_unit)
        marm[alt] = (c.base_units, c.alternative_units, normalise_unit(c.base_unit))

    canon_base = normalise_unit(base_unit)

    # --- Direct conversion in MARM ---
    # Case A: from_unit is an alt unit, to_unit is the base unit
    if canon_from in marm and canon_to == canon_base:
        base_units, alt_units, _ = marm[canon_from]
        result = qty * base_units / alt_units
        return round(result, 3), f"{alt_units} {canon_from} = {base_units} {canon_base}"

    # Case B: from_unit is the base unit, to_unit is an alt unit
    if canon_from == canon_base and canon_to in marm:
        base_units, alt_units, _ = marm[canon_to]
        result = qty * alt_units / base_units
        return round(result, 3), f"{alt_units} {canon_to} = {base_units} {canon_base}"

    # Case C: Both are alt units — go via base
    if canon_from in marm and canon_to in marm:
        bu_from, au_from, _ = marm[canon_from]
        bu_to, au_to, _ = marm[canon_to]
        in_base = qty * bu_from / au_from
        result = in_base * au_to / bu_to
        return round(result, 3), f"via {canon_base}: {canon_from}→{canon_base}→{canon_to}"

    # Case D: from_unit is alt, to_unit needs general conversion from base
    if canon_from in marm:
        bu, au, _ = marm[canon_from]
        in_base = qty * bu / au
        gen_key = (canon_base, canon_to)
        if gen_key in GENERAL_CONVERSIONS:
            result = in_base * GENERAL_CONVERSIONS[gen_key]
            return round(result, 3), f"{canon_from}→{canon_base}→{canon_to} (general)"

    # Case E: from_unit needs general conversion to base, then base → to_unit via MARM
    gen_to_base = (canon_from, canon_base)
    if gen_to_base in GENERAL_CONVERSIONS:
        in_base = qty * GENERAL_CONVERSIONS[gen_to_base]
        if canon_to == canon_base:
            return round(in_base, 3), f"{canon_from}→{canon_base} (general)"
        if canon_to in marm:
            bu_to, au_to, _ = marm[canon_to]
            result = in_base * au_to / bu_to
            return round(result, 3), f"{canon_from}→{canon_base} (general)→{canon_to}"

    # --- General conversions (direct) ---
    gen_key = (canon_from, canon_to)
    if gen_key in GENERAL_CONVERSIONS:
        result = qty * GENERAL_CONVERSIONS[gen_key]
        return round(result, 3), f"General: 1 {canon_from} = {GENERAL_CONVERSIONS[gen_key]} {canon_to}"

    # --- Fail: UOM-3 ---
    return None, f"UOM-3: Cannot convert {canon_from} to {canon_to} for material {material_id}"


# ═══════════════════════════════════════════════════════════════════════════
# Value band determination
# ═══════════════════════════════════════════════════════════════════════════

def get_value_band(line_net_amount: float) -> str:
    """Determine value band from invoice line net amount (before GST)."""
    if line_net_amount <= 100_000:
        return "Band 1"
    elif line_net_amount <= 1_000_000:
        return "Band 2"
    else:
        return "Band 3"


# ═══════════════════════════════════════════════════════════════════════════
# PO item parsing
# ═══════════════════════════════════════════════════════════════════════════

def parse_po_items(raw: str) -> list[int]:
    """
    Parse po_item_quoted which may be:
    "10", "00010", "10/20", "10 & 20", "10, 20", "10+20"
    Returns sorted list of integer item numbers.
    """
    # Split on common delimiters
    parts = re.split(r"[/&,+;]", raw)
    items = []
    for p in parts:
        p = p.strip()
        if p:
            try:
                items.append(int(p))
            except ValueError:
                continue
    return sorted(set(items))


# ═══════════════════════════════════════════════════════════════════════════
# Duplicate check helper (DUP-1)
# ═══════════════════════════════════════════════════════════════════════════

def normalise_invoice_number(raw: str) -> str:
    """Normalise vendor invoice number for duplicate comparison (DUP-1)."""
    return re.sub(r"[\s\-/._]", "", raw).lower()


# ═══════════════════════════════════════════════════════════════════════════
# Core matching logic
# ═══════════════════════════════════════════════════════════════════════════

def process_invoice(invoice_doc_number: str, update_status: bool = True) -> InvoiceMatchResult:
    """
    Run the full three-way match for a single invoice.
    This is the main entry point.
    If update_status is False, evaluates purely in read-only inspection mode.
    """
    logger.info(f"=== Starting match for invoice {invoice_doc_number} (update_status={update_status}) ===")

    # ── Step 0: Fetch invoice header ────────────────────────────────────
    header = at.get_invoice_header(invoice_doc_number)
    if header is None:
        raise ValueError(f"Invoice {invoice_doc_number} not found in Airtable")

    # ── Step 1: Lock — set status to Processing ─────────────────────────
    if update_status:
        at.update_invoice_status(header.record_id, InvoiceStatus.PROCESSING)
        audit.log_event(invoice_doc_number, "MATCH_STARTED", "Processing", "system",
                        {"vendor": header.vendor_name, "vendor_id": header.vendor_id})

    # ── Step 2: Fetch invoice lines ─────────────────────────────────────
    inv_lines = at.get_invoice_lines(invoice_doc_number)
    if not inv_lines:
        if update_status:
            at.update_invoice_status(header.record_id, InvoiceStatus.STOPPED)
            audit.log_event(invoice_doc_number, "MATCH_ERROR", "Stopped", "system",
                            "No invoice lines found")
        return InvoiceMatchResult(
            invoice_doc_number=invoice_doc_number,
            vendor_id=header.vendor_id,
            vendor_name=header.vendor_name,
            vendor_invoice_number=header.vendor_invoice_number,
            overall_outcome=MatchOutcome.STOP,
            overall_reasons=["No invoice lines found"],
        )

    # ── Step 3: Fetch approver matrix (once) ────────────────────────────
    approver_rules = at.get_approver_matrix()

    # ── Step 4: Process each line ───────────────────────────────────────
    line_results: list[LineMatchResult] = []

    for inv_line in inv_lines:
        lr = _match_single_line(inv_line, header, approver_rules)
        line_results.append(lr)

    # ── Step 5: BOTH-1 — if price AND qty both outside pass → Stop ─────
    for lr in line_results:
        # Already handled inside _match_single_line

        pass

    # ── Step 6: HOLD-1 / OUT-1 — determine overall outcome ────────────
    has_stop = any(lr.outcome == MatchOutcome.STOP for lr in line_results)
    has_escalate = any(lr.outcome == MatchOutcome.ESCALATE for lr in line_results)

    if has_stop:
        overall = MatchOutcome.STOP
    elif has_escalate:
        overall = MatchOutcome.ESCALATE
    else:
        overall = MatchOutcome.PASS

    # ── Step 7: CUM-1 — PO cumulative check ────────────────────────────
    po_cum_details = {}
    if overall != MatchOutcome.STOP:
        po_numbers_on_invoice = set(lr.po_number for lr in line_results)
        for po_num in po_numbers_on_invoice:
            cum_triggered, cum_info = _check_po_cumulative(
                po_num, line_results, invoice_doc_number
            )
            if cum_triggered:
                po_cum_details[po_num] = cum_info
                # Escalate all passing lines on this PO to CFO office
                for lr in line_results:
                    if lr.po_number == po_num and lr.outcome == MatchOutcome.PASS:
                        lr.outcome = MatchOutcome.ESCALATE
                        lr.reasons.append(f"CUM-1: PO cumulative variance ₹{cum_info['total_pv']:.2f} > limit ₹{cum_info['limit']:.2f}")
                        lr.clauses.append("CUM-1")
                        # Assign CFO office approver
                        cfo_rule = _find_approver_rule(approver_rules, "CUM-1", "", "", "")
                        if cfo_rule:
                            lr.approver_rule_id = cfo_rule.rule_id
                            lr.approver_name = cfo_rule.approver_name
                            lr.approver_email = cfo_rule.approver_email
                            lr.approver_role = cfo_rule.approver_role
                            lr.approver_seniority = cfo_rule.seniority_level

                has_escalate = True
                if not has_stop:
                    overall = MatchOutcome.ESCALATE

    # ── Step 8: ESC-3 — pick single approver (most senior) ─────────────
    final_approver_name = ""
    final_approver_email = ""
    final_approver_role = ""
    if overall == MatchOutcome.ESCALATE:
        final_approver_name, final_approver_email, final_approver_role = \
            _pick_final_approver(line_results)

    # ── Step 9: Update Airtable status ──────────────────────────────────
    if update_status:
        if overall == MatchOutcome.PASS:
            at.update_invoice_status(header.record_id, InvoiceStatus.PASSED)
        elif overall == MatchOutcome.ESCALATE:
            at.update_invoice_status(header.record_id, InvoiceStatus.ESCALATED)
        else:
            at.update_invoice_status(header.record_id, InvoiceStatus.STOPPED)

    # Build the result
    result = InvoiceMatchResult(
        invoice_doc_number=invoice_doc_number,
        vendor_id=header.vendor_id,
        vendor_name=header.vendor_name,
        vendor_invoice_number=header.vendor_invoice_number,
        overall_outcome=overall,
        overall_reasons=[r for lr in line_results for r in lr.reasons],
        line_results=line_results,
        final_approver_name=final_approver_name,
        final_approver_email=final_approver_email,
        final_approver_role=final_approver_role,
        po_cumulative_triggered=bool(po_cum_details),
        po_cumulative_details=po_cum_details,
    )

    # Audit
    if update_status:
        audit.log_event(
            invoice_doc_number, "MATCH_COMPLETED", overall.value, "system",
            {
                "outcome": overall.value,
                "lines": len(line_results),
                "approver": final_approver_name or "N/A",
                "stopped_lines": [lr.invoice_line_number for lr in line_results if lr.outcome == MatchOutcome.STOP],
                "escalated_lines": [lr.invoice_line_number for lr in line_results if lr.outcome == MatchOutcome.ESCALATE],
            }
        )

    logger.info(f"=== Match complete for {invoice_doc_number}: {overall.value} ===")
    return result


# ═══════════════════════════════════════════════════════════════════════════
# Single line matching
# ═══════════════════════════════════════════════════════════════════════════

def _match_single_line(
    inv_line: InvoiceLine,
    header: InvoiceHeader,
    approver_rules: list[ApproverRule],
) -> LineMatchResult:
    """Match a single invoice line against PO and GRN data."""
    lr = LineMatchResult(
        invoice_doc_number=inv_line.invoice_doc_number,
        invoice_line_number=inv_line.invoice_line_number,
        po_number=inv_line.po_number,
        material_id=inv_line.material_id,
        invoice_line_net_amount=inv_line.line_net_amount,
    )

    # Parse PO items (may be multi: "10/20", "10 & 20", etc.)
    po_items = parse_po_items(inv_line.po_item_quoted)
    lr.po_items_matched = po_items
    if not po_items:
        lr.outcome = MatchOutcome.STOP
        lr.reasons.append("No valid PO item number could be parsed")
        lr.clauses.append("PARSE_ERROR")
        return lr

    # Fetch PO lines
    po_lines: list[POLine] = []
    for item_num in po_items:
        pl = at.get_po_line(inv_line.po_number, item_num)
        if pl:
            po_lines.append(pl)

    if not po_lines:
        lr.outcome = MatchOutcome.STOP
        lr.reasons.append(f"PO line(s) {po_items} not found on PO {inv_line.po_number}")
        lr.clauses.append("PO_NOT_FOUND")
        return lr

    # ── CL-1: Closed/deleted PO check ──────────────────────────────────
    for pl in po_lines:
        status_norm = pl.line_status.strip().lower()
        if (pl.final_invoice_flag.strip().upper() == "X"
                or pl.deletion_flag.strip().upper() == "L"
                or status_norm == "closed"):
            lr.outcome = MatchOutcome.STOP
            lr.reasons.append(
                f"CL-1: PO line {pl.po_number}/{pl.po_item} is closed "
                f"(status={pl.line_status}, EREKZ={pl.final_invoice_flag}, LOEKZ={pl.deletion_flag})"
            )
            lr.clauses.append("CL-1")
            return lr

    # Use the first PO line for material info
    primary_pl = po_lines[0]
    lr.po_order_unit = primary_pl.order_unit

    # ── Fetch material info ─────────────────────────────────────────────
    material = at.get_material(inv_line.material_id)
    if material:
        lr.category = material.category.lower()
    else:
        lr.category = "manufactured"  # safe default
        lr.reasons.append(f"Material {inv_line.material_id} not found in master — defaulting to 'manufactured'")

    lr.value_band = get_value_band(inv_line.line_net_amount)

    # ── UOM-1: Convert invoice qty to PO order unit ────────────────────
    conversions = at.get_unit_conversions(inv_line.material_id)
    base_unit = material.base_unit if material else "KG"

    converted_qty, uom_desc = convert_qty(
        inv_line.billed_qty,
        inv_line.billed_unit,
        primary_pl.order_unit,
        inv_line.material_id,
        conversions,
        base_unit,
    )

    if converted_qty is None:
        # UOM-3: Stop
        lr.outcome = MatchOutcome.STOP
        lr.reasons.append(uom_desc)
        lr.clauses.append("UOM-3")
        return lr

    lr.billed_qty_converted = converted_qty
    lr.uom_conversion_used = uom_desc

    # ── SPAN-1: Handle multi-PO-line allocation ────────────────────────
    # Collect all GRN and prior invoice data for all matched PO lines
    total_net_received = 0.0
    total_prior_invoiced = 0.0
    total_ordered = 0.0
    total_over_delivery_allowance = 0.0
    weighted_po_price = 0.0  # For multi-line: weighted by allocated qty
    allocations: list[dict] = []

    for pl in po_lines:
        # Goods receipts for this PO line
        receipts = at.get_goods_receipts(pl.po_number, pl.po_item)
        gr_conversions = conversions  # Same material

        sum_101 = 0.0
        sum_102 = 0.0
        sum_122 = 0.0

        for gr in receipts:
            gr_qty_converted, _ = convert_qty(
                gr.qty_entered, gr.qty_unit_entered, pl.order_unit,
                inv_line.material_id, gr_conversions, base_unit,
            )
            if gr_qty_converted is None:
                gr_qty_converted = gr.qty_entered  # Fallback
            if gr.movement_type == 101:
                sum_101 += gr_qty_converted
            elif gr.movement_type == 102:
                sum_102 += gr_qty_converted
            elif gr.movement_type == 122:
                sum_122 += gr_qty_converted

        net_received = round(sum_101 - sum_102 - sum_122, 3)

        # Prior invoiced qty on this PO line (only "Posted", not "Reversed")
        priors = at.get_prior_invoices(pl.po_number, pl.po_item)
        prior_qty = sum(
            p.invoiced_qty for p in priors
            if p.status.strip().lower() == "posted"
        )

        # Over-delivery allowance
        uebto = pl.over_delivery_tolerance_pct or 0.0
        allowance = pl.ordered_qty * (1 + uebto / 100.0)

        # Clamp net received to allowance (OR-1)
        effective_received = min(net_received, allowance)
        available = max(effective_received - prior_qty, 0.0)

        po_price_per_unit = pl.net_price / pl.price_unit if pl.price_unit else pl.net_price

        allocations.append({
            "po_line": pl,
            "net_received": net_received,
            "effective_received": effective_received,
            "prior_invoiced": prior_qty,
            "available": available,
            "allowance": allowance,
            "po_price_per_unit": po_price_per_unit,
            "over_delivered": net_received > allowance,
        })

        total_net_received += net_received
        total_prior_invoiced += prior_qty
        total_ordered += pl.ordered_qty
        total_over_delivery_allowance += allowance

    # ── REC-2: Zero receipt check ───────────────────────────────────────
    if total_net_received <= 0:
        lr.outcome = MatchOutcome.STOP
        lr.net_received_qty = total_net_received
        lr.reasons.append(f"REC-2: Net received quantity is {total_net_received:.3f} (zero or negative)")
        lr.clauses.append("REC-2")
        return lr

    # ── SPAN-1: Allocate invoiced qty across PO lines (item order) ─────
    remaining_qty = converted_qty
    value_at_po_price = 0.0
    total_available = 0.0

    for alloc in allocations:
        avail = alloc["available"]
        total_available += avail
        alloc_qty = min(remaining_qty, avail) if remaining_qty > 0 else 0
        # Last line gets remainder (SPAN-1)
        if alloc is allocations[-1] and remaining_qty > 0:
            alloc_qty = remaining_qty
        remaining_qty -= alloc_qty
        remaining_qty = max(remaining_qty, 0)
        value_at_po_price += round(alloc_qty * alloc["po_price_per_unit"], 2)

    lr.net_received_qty = total_net_received
    lr.prior_invoiced_qty = total_prior_invoiced
    lr.available_qty = total_available
    lr.over_delivery_allowance = total_over_delivery_allowance

    # Use primary PO line's price for single-line cases
    primary_price_per_unit = allocations[0]["po_price_per_unit"] if allocations else 0
    lr.po_price_per_unit = primary_price_per_unit
    lr.value_at_po_price = round(value_at_po_price, 2)

    # ── OR-1 / OR-2: Over-delivery checks ──────────────────────────────
    for alloc in allocations:
        if alloc["over_delivered"]:
            # OR-1: Net received > allowance → escalate to Procurement head
            lr.reasons.append(
                f"OR-1: Net received {alloc['net_received']:.3f} > allowance {alloc['allowance']:.3f} "
                f"on PO {alloc['po_line'].po_number}/{alloc['po_line'].po_item}"
            )
            lr.clauses.append("OR-1")
            if lr.outcome != MatchOutcome.STOP:
                lr.outcome = MatchOutcome.ESCALATE

    # ── QV-4: Everything invoiced, nothing available ────────────────────
    if total_available <= 0:
        lr.outcome = MatchOutcome.STOP
        lr.reasons.append("QV-4: Available quantity is zero — all received has been invoiced")
        lr.clauses.append("QV-4")
        return lr

    # ── Price variance (PV-1, PV-2) ────────────────────────────────────
    price_variance_inr = round(inv_line.line_net_amount - value_at_po_price, 2)
    if value_at_po_price > 0:
        price_variance_pct = round((price_variance_inr / value_at_po_price) * 100, 2)
    else:
        price_variance_pct = 0.0

    lr.price_variance_inr = price_variance_inr
    lr.price_variance_pct = price_variance_pct

    # ── Quantity variance (QV-1 through QV-4) ──────────────────────────
    qty_variance_qty = round(converted_qty - total_available, 3)
    if total_available > 0:
        qty_variance_pct = round((qty_variance_qty / total_available) * 100, 2)
    else:
        qty_variance_pct = 0.0 if qty_variance_qty <= 0 else 100.0

    qty_variance_inr = round(qty_variance_qty * primary_price_per_unit, 2) if qty_variance_qty > 0 else 0.0

    lr.qty_variance_qty = qty_variance_qty
    lr.qty_variance_pct = qty_variance_pct
    lr.qty_variance_inr = qty_variance_inr

    # ── Evaluate price outcome ──────────────────────────────────────────
    price_outcome = MatchOutcome.PASS
    tol = PRICE_TOLERANCE.get(lr.category, PRICE_TOLERANCE["manufactured"])
    caps = PRICE_CAPS.get(lr.value_band, PRICE_CAPS["Band 1"])

    if price_variance_inr <= 0:
        # PV-1: Below PO price → pass
        price_outcome = MatchOutcome.PASS
        if price_variance_inr < 0:
            lr.reasons.append(f"PV-1: Price below PO price by ₹{abs(price_variance_inr):,.2f}")
            lr.clauses.append("PV-1")
    else:
        # PV-2: Compute limits
        pass_limit_pct_val = value_at_po_price * tol["pass_pct"] / 100
        pass_limit = min(pass_limit_pct_val, caps["pass_cap"])

        stop_limit_pct_val = value_at_po_price * tol["stop_pct"] / 100
        stop_limit = min(stop_limit_pct_val, caps["stop_cap"])

        lr.price_pass_limit_inr = round(pass_limit, 2)
        lr.price_stop_limit_inr = round(stop_limit, 2)

        if price_variance_inr <= pass_limit:
            price_outcome = MatchOutcome.PASS
        elif price_variance_inr > stop_limit:
            price_outcome = MatchOutcome.STOP
            lr.reasons.append(
                f"PV-2: Price variance ₹{price_variance_inr:,.2f} ({price_variance_pct:+.2f}%) "
                f"> stop limit ₹{stop_limit:,.2f}"
            )
            lr.clauses.append("PV-2")
        else:
            price_outcome = MatchOutcome.ESCALATE
            lr.reasons.append(
                f"PV-2: Price variance ₹{price_variance_inr:,.2f} ({price_variance_pct:+.2f}%) "
                f"between pass ₹{pass_limit:,.2f} and stop ₹{stop_limit:,.2f}"
            )
            lr.clauses.append("PV-2")

    # ── Evaluate quantity outcome ───────────────────────────────────────
    qty_outcome = MatchOutcome.PASS

    if qty_variance_qty <= 0:
        # QV-1: Partial invoice — accepted
        qty_outcome = MatchOutcome.PASS
    elif lr.category == "bulk":
        # QV-2: Bulk tolerance
        bulk_pass_cap = caps["pass_cap"]
        bulk_stop_cap = caps["stop_cap"]

        if qty_variance_pct <= BULK_QTY_TOLERANCE["pass_pct"] and qty_variance_inr <= bulk_pass_cap:
            qty_outcome = MatchOutcome.PASS
        elif qty_variance_pct > BULK_QTY_TOLERANCE["stop_pct"] or qty_variance_inr > bulk_stop_cap:
            qty_outcome = MatchOutcome.STOP
            lr.reasons.append(
                f"QV-2: Qty variance {qty_variance_pct:+.2f}% ({qty_variance_qty:+.3f} {lr.po_order_unit}) "
                f"= ₹{qty_variance_inr:,.2f} > stop limits"
            )
            lr.clauses.append("QV-2")
        else:
            qty_outcome = MatchOutcome.ESCALATE
            lr.reasons.append(
                f"QV-2: Qty variance {qty_variance_pct:+.2f}% ({qty_variance_qty:+.3f} {lr.po_order_unit}) "
                f"= ₹{qty_variance_inr:,.2f} in escalation band"
            )
            lr.clauses.append("QV-2")
    else:
        # QV-3: manufactured, service, capex — zero tolerance
        qty_outcome = MatchOutcome.STOP
        lr.reasons.append(
            f"QV-3: {lr.category} has zero quantity tolerance; "
            f"qty variance = {qty_variance_qty:+.3f} {lr.po_order_unit}"
        )
        lr.clauses.append("QV-3")

    lr.qty_pass_limit_pct = BULK_QTY_TOLERANCE["pass_pct"] if lr.category == "bulk" else 0.0
    lr.qty_stop_limit_pct = BULK_QTY_TOLERANCE["stop_pct"] if lr.category == "bulk" else 0.0

    # ── BOTH-1: If both outside pass → Stop ─────────────────────────────
    if price_outcome != MatchOutcome.PASS and qty_outcome != MatchOutcome.PASS:
        lr.outcome = MatchOutcome.STOP
        lr.reasons.append("BOTH-1: Both price and quantity outside pass limits → Stop")
        lr.clauses.append("BOTH-1")
    elif price_outcome == MatchOutcome.STOP or qty_outcome == MatchOutcome.STOP:
        lr.outcome = MatchOutcome.STOP
    elif price_outcome == MatchOutcome.ESCALATE or qty_outcome == MatchOutcome.ESCALATE:
        lr.outcome = MatchOutcome.ESCALATE
    else:
        lr.outcome = MatchOutcome.PASS

    # ── Assign approver if escalated ────────────────────────────────────
    if lr.outcome == MatchOutcome.ESCALATE:
        # Determine which escalation path
        if "OR-1" in lr.clauses:
            # ESC-2: Goes to Procurement head
            role = "Procurement head, services" if lr.category == "service" else "Procurement head, materials"
        else:
            # ESC-1: Use the (value_band, category) table
            role = APPROVER_ROLE_MAP.get((lr.value_band, lr.category), "CFO office")

        rule = _find_approver_rule(
            approver_rules,
            "Line price or quantity variance",
            lr.value_band,
            lr.category,
            primary_pl.plant_code,
            role_hint=role,
        )
        if rule:
            lr.approver_rule_id = rule.rule_id
            lr.approver_name = rule.approver_name
            lr.approver_email = rule.approver_email
            lr.approver_role = rule.approver_role
            lr.approver_seniority = rule.seniority_level

    return lr


# ═══════════════════════════════════════════════════════════════════════════
# PO cumulative check (CUM-1)
# ═══════════════════════════════════════════════════════════════════════════

def _check_po_cumulative(
    po_number: str,
    line_results: list[LineMatchResult],
    current_invoice: str,
) -> tuple[bool, dict]:
    """
    CUM-1: Check if total price variance across a PO exceeds the PO limit.
    Only counts positive price variance (above PO price).
    """
    po_header = at.get_po_header(po_number)
    if not po_header:
        return False, {}

    po_net_value = po_header.po_net_value
    limit = min(po_net_value * PO_CUM_LIMIT_PCT / 100, PO_CUM_LIMIT_CAP)

    # Sum positive PV from prior posted invoices (not reversed)
    prior_invoices = at.get_prior_invoices_for_po(po_number)
    prior_pv_total = 0.0
    for pi in prior_invoices:
        if pi.status.strip().lower() == "posted":
            # Price variance = net_amount - (invoiced_qty * po_price_per_unit)
            # We need the PO line's price — fetch it
            po_line = at.get_po_line(po_number, pi.po_item)
            if po_line:
                po_ppu = po_line.net_price / po_line.price_unit if po_line.price_unit else po_line.net_price
                val_at_po_price = pi.invoiced_qty * po_ppu
                pv = pi.net_amount - val_at_po_price
                if pv > 0:
                    prior_pv_total += pv

    # Sum positive PV from this invoice's lines on this PO
    this_invoice_pv = 0.0
    for lr in line_results:
        if lr.po_number == po_number and lr.outcome != MatchOutcome.STOP:
            if lr.price_variance_inr > 0:
                this_invoice_pv += lr.price_variance_inr

    total_pv = prior_pv_total + this_invoice_pv

    info = {
        "po_net_value": po_net_value,
        "limit": round(limit, 2),
        "prior_pv": round(prior_pv_total, 2),
        "this_invoice_pv": round(this_invoice_pv, 2),
        "total_pv": round(total_pv, 2),
        "triggered": total_pv > limit,
    }

    return total_pv > limit, info


# ═══════════════════════════════════════════════════════════════════════════
# Approver lookup
# ═══════════════════════════════════════════════════════════════════════════

def _find_approver_rule(
    rules: list[ApproverRule],
    trigger: str,
    value_band: str,
    category: str,
    plant_code: str,
    role_hint: str = "",
) -> Optional[ApproverRule]:
    """
    Find the best matching approver rule from the matrix.
    """
    # Special: CUM-1 trigger
    if trigger == "CUM-1":
        for r in rules:
            if "PO cumulative" in r.trigger.lower() or "CUM-1" in r.trigger:
                return r
        # Fallback: CFO office
        for r in rules:
            if r.seniority_level == 3:
                return r
        return None

    candidates = []
    for r in rules:
        # Match trigger
        if "variance" not in r.trigger.lower() and "line price" not in r.trigger.lower():
            continue

        # Match value band
        if r.value_band != "Any" and r.value_band != value_band:
            continue

        # Match category
        cats = [c.strip().lower() for c in r.categories.replace(";", ",").split(",")]
        if "all categories" not in r.categories.lower() and category.lower() not in cats:
            continue

        # Match plant
        if r.plant_code.strip().lower() != "all" and r.plant_code.strip() != plant_code:
            continue

        candidates.append(r)

    if not candidates:
        # Broaden: ignore plant
        for r in rules:
            if "variance" not in r.trigger.lower() and "line price" not in r.trigger.lower():
                continue
            if r.value_band != "Any" and r.value_band != value_band:
                continue
            cats = [c.strip().lower() for c in r.categories.replace(";", ",").split(",")]
            if "all categories" not in r.categories.lower() and category.lower() not in cats:
                continue
            candidates.append(r)

    if not candidates:
        return None

    # If role_hint provided, prefer matching role
    if role_hint:
        for c in candidates:
            if role_hint.lower() in c.approver_role.lower():
                return c

    # Return highest seniority
    candidates.sort(key=lambda r: r.seniority_level, reverse=True)
    return candidates[0]


def _pick_final_approver(
    line_results: list[LineMatchResult],
) -> tuple[str, str, str]:
    """
    ESC-3: Pick the single most senior approver across all escalated lines.
    If tied on seniority, pick the one with higher line_net_amount,
    then lower line number.
    """
    escalated = [
        lr for lr in line_results if lr.outcome == MatchOutcome.ESCALATE and lr.approver_name
    ]
    if not escalated:
        return "", "", ""

    # Sort by: seniority DESC, line_net_amount DESC, line_number ASC
    escalated.sort(
        key=lambda lr: (-lr.approver_seniority, -lr.invoice_line_net_amount, lr.invoice_line_number)
    )
    winner = escalated[0]
    return winner.approver_name, winner.approver_email, winner.approver_role
