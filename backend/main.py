"""
PolicyGuard AP — FastAPI Application

Endpoints:
  POST /api/invoices/process/{invoice_doc_number}  — Run 3-way match
  POST /api/invoices/upload-pdf                    — PDF extraction + match
  POST /api/slack/interact                         — Slack interactive callback
  GET  /api/audit-logs                             — Audit trail
  GET  /api/invoices/parked                        — List parked invoices
  GET  /api/health                                 — Health check
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from typing import Optional
from urllib.parse import parse_qs

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import config
from models.schemas import (
    AuditLogEntry,
    InvoiceMatchResult,
    InvoiceStatus,
    MatchOutcome,
    ProcessInvoiceResponse,
    UploadPDFResponse,
)
from services import airtable_client as at
from services import audit_logger as audit
from services import gemini_service as gemini
from services import matching_engine as engine
from services import slack_service as slack

# ── Logging ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
)
logger = logging.getLogger("policyguard")

# ── App ──────────────────────────────────────────────────────────────────
app = FastAPI(
    title="PolicyGuard AP",
    description="Agentic AI for Automated Three-Way Transaction Reconciliation",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════════════
# Health check
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "service": "PolicyGuard AP",
        "business_date": config.BUSINESS_DATE.isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════════════
# POST /api/invoices/process/{invoice_doc_number}
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/invoices/process/{invoice_doc_number}", response_model=ProcessInvoiceResponse)
async def process_invoice(invoice_doc_number: str):
    """Run the full three-way match for a parked Airtable invoice."""
    try:
        # Validate the invoice exists and is parked
        header = at.get_invoice_header(invoice_doc_number)
        if header is None:
            raise HTTPException(status_code=404, detail=f"Invoice {invoice_doc_number} not found")

        status_norm = header.status.strip().lower()
        if status_norm not in ("parked", "processing"):
            raise HTTPException(
                status_code=409,
                detail=f"Invoice {invoice_doc_number} has status '{header.status}' — only Parked invoices can be processed",
            )

        # Run the matching engine
        result: InvoiceMatchResult = engine.process_invoice(invoice_doc_number)

        # Send Slack notifications based on outcome
        if result.overall_outcome == MatchOutcome.ESCALATE:
            ts = slack.send_escalation_card(result)
            if ts:
                audit.log_event(
                    invoice_doc_number, "SLACK_ESCALATION_SENT", "Escalated",
                    "system", {"slack_ts": ts, "approver": result.final_approver_name}
                )

        elif result.overall_outcome == MatchOutcome.STOP:
            ts = slack.send_stop_alert(result)
            if ts:
                audit.log_event(
                    invoice_doc_number, "SLACK_STOP_ALERT_SENT", "Stopped",
                    "system", {"slack_ts": ts}
                )

        return ProcessInvoiceResponse(
            success=True,
            invoice_doc_number=invoice_doc_number,
            outcome=result.overall_outcome.value,
            message=f"Invoice {invoice_doc_number} → {result.overall_outcome.value}",
            details=result,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error processing invoice {invoice_doc_number}")
        audit.log_event(invoice_doc_number, "MATCH_ERROR", "Error", "system", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/invoices/{invoice_doc_number}/inspect")
async def inspect_invoice(invoice_doc_number: str):
    """
    Read-only inspection of full 3-way match calculation and evidence.
    Does NOT mutate invoice status or send Slack alerts.
    """
    try:
        header = at.get_invoice_header(invoice_doc_number)
        if not header:
            raise HTTPException(status_code=404, detail=f"Invoice {invoice_doc_number} not found")

        result = engine.process_invoice(invoice_doc_number, update_status=False)
        return {
            "success": True,
            "invoice_doc_number": invoice_doc_number,
            "current_status": header.status,
            "calculated_outcome": result.overall_outcome.value,
            "details": result,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error inspecting invoice {invoice_doc_number}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
# POST /api/invoices/upload-pdf
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/invoices/upload-pdf", response_model=UploadPDFResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """Accept a PDF, extract via Gemini, then run a live 3-way match."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    try:
        # Save uploaded file
        save_path = config.UPLOAD_DIR / file.filename
        content = await file.read()
        save_path.write_bytes(content)

        # Extract via Gemini
        extracted = await gemini.extract_invoice_from_pdf(save_path)
        if extracted is None:
            raise HTTPException(status_code=422, detail="Failed to extract invoice data from PDF")

        # Log extraction
        audit.log_event(
            extracted.get("header", {}).get("vendor_invoice_number", "UNKNOWN"),
            "PDF_EXTRACTED", "", "gemini", extracted
        )

        # Try to match against ERP if PO or Vendor Invoice Number was extracted
        match_result = None
        vendor_inv_num = extracted.get("header", {}).get("vendor_invoice_number")
        po_number = extracted.get("header", {}).get("po_number")

        matching_doc = None
        all_invs = at.get_all_invoices()

        if vendor_inv_num:
            clean_v_inv = engine.normalise_invoice_number(vendor_inv_num)
            for inv in all_invs:
                if engine.normalise_invoice_number(inv.vendor_invoice_number) == clean_v_inv:
                    matching_doc = inv.invoice_doc_number
                    break

        if not matching_doc and po_number:
            for inv in all_invs:
                if po_number in inv.po_numbers_quoted:
                    matching_doc = inv.invoice_doc_number
                    break

        if matching_doc:
            logger.info(f"Found corresponding ERP invoice document: {matching_doc}. Running 3-way match...")
            match_result = engine.process_invoice(matching_doc)

        return UploadPDFResponse(
            success=True,
            message=f"Successfully extracted invoice from {file.filename}" + (f" and matched ERP Doc {matching_doc}" if matching_doc else ""),
            extracted_data=extracted,
            match_result=match_result,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error processing uploaded PDF: {file.filename}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
# POST /api/slack/interact — Slack interactive callback
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/slack/interact")
async def slack_interact(request: Request):
    """
    Handle Slack interactive button callbacks (Approve / Reject).
    Slack sends application/x-www-form-urlencoded with a `payload` field.
    """
    body = await request.body()

    # Verify Slack signing secret (optional in dev, mandatory in production)
    if config.SLACK_SIGNING_SECRET:
        timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
        slack_sig = request.headers.get("X-Slack-Signature", "")
        if timestamp and slack_sig:
            if not _verify_slack_signature(body, timestamp, slack_sig):
                raise HTTPException(status_code=403, detail="Invalid Slack signature")

    # Parse payload
    form_data = parse_qs(body.decode("utf-8"))
    payload_str = form_data.get("payload", [""])[0]
    if not payload_str:
        raise HTTPException(status_code=400, detail="No payload")

    payload = json.loads(payload_str)
    actions = payload.get("actions", [])
    if not actions:
        return JSONResponse({"ok": True})

    action = actions[0]
    action_id = action.get("action_id", "")
    invoice_doc_number = action.get("value", "")
    user = payload.get("user", {})
    approver_name = user.get("real_name", user.get("username", "Unknown"))
    channel_id = payload.get("channel", {}).get("id", "")
    message_ts = payload.get("message", {}).get("ts", "")

    if action_id == "approve_invoice":
        # Approve → set status to Passed
        header = at.get_invoice_header(invoice_doc_number)
        if header:
            at.update_invoice_status(header.record_id, InvoiceStatus.PASSED)
            audit.log_event(
                invoice_doc_number, "APPROVER_ACTION", "Passed",
                approver_name, {"action": "approve", "channel": channel_id}
            )
            slack.send_approval_confirmation(
                channel_id, message_ts, invoice_doc_number, "approve", approver_name
            )

    elif action_id == "reject_invoice":
        # Reject → set status to Stopped
        header = at.get_invoice_header(invoice_doc_number)
        if header:
            at.update_invoice_status(header.record_id, InvoiceStatus.STOPPED)
            audit.log_event(
                invoice_doc_number, "APPROVER_ACTION", "Stopped",
                approver_name, {"action": "reject", "channel": channel_id}
            )
            slack.send_approval_confirmation(
                channel_id, message_ts, invoice_doc_number, "reject", approver_name
            )

    elif action_id == "release_stopped_invoice":
        # Financial Controller Release under Policy APR-1
        header = at.get_invoice_header(invoice_doc_number)
        if header:
            at.update_invoice_status(header.record_id, InvoiceStatus.PASSED)
            audit.log_event(
                invoice_doc_number, "FINANCIAL_CONTROLLER_RELEASE", "Passed",
                approver_name, {
                    "action": "release_stop",
                    "policy": "APR-1",
                    "reason": "Authorized release under clause APR-1 by Financial Controller",
                    "channel": channel_id
                }
            )
            slack.send_approval_confirmation(
                channel_id, message_ts, invoice_doc_number, "release (APR-1 Override)", approver_name
            )

    return JSONResponse({"ok": True})


def _verify_slack_signature(body: bytes, timestamp: str, signature: str) -> bool:
    """Verify the Slack request signature (HMAC-SHA256)."""
    try:
        if abs(time.time() - float(timestamp)) > 300:
            return False
        sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
        my_sig = "v0=" + hmac.new(
            config.SLACK_SIGNING_SECRET.encode("utf-8"),
            sig_basestring.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(my_sig, signature)
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════════
# GET /api/audit-logs
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/audit-logs")
async def get_audit_logs(
    invoice_doc_number: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """Return timestamped audit execution logs."""
    logs = audit.get_logs(invoice_doc_number=invoice_doc_number, limit=limit, offset=offset)
    total = audit.get_log_count(invoice_doc_number=invoice_doc_number)
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "logs": [log.model_dump() for log in logs],
    }


# ═══════════════════════════════════════════════════════════════════════════
# GET /api/invoices — list invoices (with optional status filter)
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/invoices")
async def list_invoices(status: Optional[str] = None):
    """List invoices from Airtable with optional status filter."""
    try:
        invoices = at.get_all_invoices(status=status)
        return {
            "count": len(invoices),
            "invoices": [inv.model_dump() for inv in invoices],
        }
    except Exception as e:
        logger.exception("Error fetching invoices")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
# PATCH /api/invoices/{invoice_doc_number}/status — manual status reset/update
# ═══════════════════════════════════════════════════════════════════════════

class UpdateStatusRequest(BaseModel):
    status: str


@app.patch("/api/invoices/{invoice_doc_number}/status")
async def update_invoice_status(invoice_doc_number: str, req: UpdateStatusRequest):
    """Manually update or reset an invoice's status (e.g. back to Parked)."""
    header = at.get_invoice_header(invoice_doc_number)
    if not header:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_doc_number} not found")
    
    status_val = req.status.strip().capitalize()
    # Normalize standard statuses
    valid_map = {"parked": InvoiceStatus.PARKED, "processing": InvoiceStatus.PROCESSING,
                 "passed": InvoiceStatus.PASSED, "escalated": InvoiceStatus.ESCALATED,
                 "stopped": InvoiceStatus.STOPPED}
    
    matched_status = valid_map.get(status_val.lower())
    if not matched_status:
        raise HTTPException(status_code=400, detail=f"Invalid status '{req.status}'. Must be one of: Parked, Processing, Passed, Escalated, Stopped")
    
    at.update_invoice_status(invoice_doc_number, matched_status)
    audit.log_event(invoice_doc_number, "STATUS_RESET", matched_status.value, "user", f"Status manually updated to {matched_status.value}")
    return {"success": True, "invoice_doc_number": invoice_doc_number, "status": matched_status.value}


class ReleaseStopRequest(BaseModel):
    reason: str = "Authorized release under clause APR-1 by Financial Controller"
    controller_name: str = "Kruti Jadeja (Financial Controller, CFO Office)"


@app.post("/api/invoices/{invoice_doc_number}/release")
async def release_stopped_invoice(invoice_doc_number: str, req: ReleaseStopRequest):
    """Release a stopped invoice under Policy APR-1 (Financial Controller Override)."""
    header = at.get_invoice_header(invoice_doc_number)
    if not header:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_doc_number} not found")

    at.update_invoice_status(invoice_doc_number, InvoiceStatus.PASSED)
    audit.log_event(
        invoice_doc_number,
        "FINANCIAL_CONTROLLER_RELEASE",
        "Passed",
        req.controller_name,
        {"policy": "APR-1", "reason": req.reason, "prior_status": header.status}
    )
    return {
        "success": True,
        "invoice_doc_number": invoice_doc_number,
        "status": "Passed",
        "message": f"Invoice {invoice_doc_number} released by {req.controller_name} under policy APR-1."
    }


# ═══════════════════════════════════════════════════════════════════════════
# POST /api/invoices/process-all — batch process all parked invoices
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/invoices/process-all")
async def process_all_parked():
    """Process all parked invoices in document number order (GEN-2)."""
    try:
        invoices = at.get_all_parked_invoices()
        # GEN-2: Sort by document number, lowest first
        invoices.sort(key=lambda x: x.invoice_doc_number)

        results = []
        for inv in invoices:
            try:
                result = engine.process_invoice(inv.invoice_doc_number)
                # Send Slack notifications
                if result.overall_outcome == MatchOutcome.ESCALATE:
                    slack.send_escalation_card(result)
                elif result.overall_outcome == MatchOutcome.STOP:
                    slack.send_stop_alert(result)
                results.append({
                    "invoice_doc_number": inv.invoice_doc_number,
                    "outcome": result.overall_outcome.value,
                    "lines": len(result.line_results),
                })
            except Exception as e:
                results.append({
                    "invoice_doc_number": inv.invoice_doc_number,
                    "outcome": "Error",
                    "error": str(e),
                })

        return {
            "processed": len(results),
            "results": results,
        }
    except Exception as e:
        logger.exception("Error in batch processing")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
# Startup
# ═══════════════════════════════════════════════════════════════════════════

@app.on_event("startup")
async def startup():
    logger.info("╔══════════════════════════════════════════════════════╗")
    logger.info("║   PolicyGuard AP — Three-Way Match Engine v1.0      ║")
    logger.info(f"║   Business Date: {config.BUSINESS_DATE.strftime('%Y-%m-%d %H:%M %Z')}         ║")
    logger.info("╚══════════════════════════════════════════════════════╝")
