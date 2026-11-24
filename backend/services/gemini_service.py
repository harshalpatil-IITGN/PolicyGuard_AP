"""
Gemini service — PDF invoice extraction via multimodal Gemini Flash & Flash-Lite.

Uses google-genai SDK (free tier from AI Studio).
Strictly used for:
  1. Extracting structured JSON from PDF invoices (digital + scanned)
  2. Generating human-readable variance explanations for Slack
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Optional

from PyPDF2 import PdfReader
from google import genai
from google.genai import types

from config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)

# Fallback sequence of active models
MODELS_TO_TRY = [
    GEMINI_MODEL,
    "gemini-flash-lite-latest",
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-flash-latest",
]

_client: Optional[genai.Client] = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


EXTRACTION_PROMPT = """You are an expert accounts payable document processor for Ashvaka Industries Group.
Extract the following from this vendor invoice PDF into strict JSON. Handle both digital and scanned/photographed invoices.

Return ONLY valid JSON with this exact structure (no markdown, no commentary):
{
  "header": {
    "vendor_name": "string",
    "vendor_gstin": "string (15 char)",
    "vendor_invoice_number": "string",
    "invoice_date": "string (dd-mm-yyyy)",
    "po_number": "string",
    "gross_amount": number,
    "gst_amount": number,
    "net_amount_before_gst": number
  },
  "lines": [
    {
      "line_number": integer,
      "po_item": "string (e.g. '10', '20')",
      "material_description": "string",
      "hsn_sac_code": "string",
      "quantity": number,
      "unit": "string",
      "unit_price": number,
      "line_net_amount": number,
      "gst_rate_pct": number,
      "gst_amount": number
    }
  ]
}

Rules:
- All amounts are in INR before GST unless marked otherwise.
- Quantities and prices should be numbers, not strings.
- If a field cannot be determined, use null.
- PO numbers are 10-digit numbers starting with 45.
- Units may be in vendor spellings: TON, Tonne, M.T., KGS, Nos, PCS, Man-days, Bags, Hrs, etc.
- Dates may be in various formats — normalise to dd-mm-yyyy.
"""


def _extract_text_via_pypdf2(pdf_path: Path) -> str:
    """Extract raw text from PDF using PyPDF2 if text layer exists."""
    try:
        reader = PdfReader(str(pdf_path))
        text = "\n".join([page.extract_text() or "" for page in reader.pages]).strip()
        return text
    except Exception as e:
        logger.warning(f"PyPDF2 text extraction error: {e}")
        return ""


def _fallback_parse_digital_pdf(text: str, pdf_name: str) -> Optional[dict]:
    """
    Zero-fail heuristic fallback for digital invoices when Gemini API is
    temporarily unavailable or experiencing 503 high-demand spikes.
    """
    if not text or len(text) < 50:
        return None

    try:
        # 1. PO Number (10 digits starting with 45)
        po_match = re.search(r"\b(45\d{8})\b", text)
        po_number = po_match.group(1) if po_match else None

        # 2. GSTIN (15 characters)
        gstin_match = re.search(r"\b(\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1})\b", text)
        vendor_gstin = gstin_match.group(1) if gstin_match else ""

        # 3. Vendor Invoice Number
        inv_match = re.search(r"Invoice\s*No\.?\s*[:\n]\s*([A-Za-z0-9/\-_]+)", text, re.IGNORECASE)
        invoice_number = inv_match.group(1).strip() if inv_match else pdf_name.replace(".pdf", "")

        # 4. Total Amount
        total_match = re.search(r"(?:Invoice\s*total|Total\s*amount|Grand\s*total)\s*[:\n]?\s*([0-9,.]+)", text, re.IGNORECASE)
        gross_amount = 0.0
        if total_match:
            try:
                gross_amount = float(total_match.group(1).replace(",", "").strip())
            except ValueError:
                pass

        # 5. Vendor Name (first lines of invoice)
        lines_clean = [l.strip() for l in text.split("\n") if l.strip() and not l.strip().isdigit()]
        vendor_name = lines_clean[1] if len(lines_clean) > 1 and len(lines_clean[0]) <= 3 else lines_clean[0]

        # 6. Line Items Extraction
        extracted_lines = []
        pattern = r"(\d+)\s*\n([^\n]+(?:\(PO\s*item\s*\d+\))?)\s*\n(\d{4,8})\s*\n([0-9,.]+)\s*\n([A-Za-z]+)\s*\n([0-9,.]+)\s*\n([0-9,.]+)"
        for m in re.finditer(pattern, text):
            po_item_match = re.search(r"PO\s*item\s*(\d+)", m.group(2), re.IGNORECASE)
            po_item = po_item_match.group(1) if po_item_match else str(int(m.group(1)) * 10)
            extracted_lines.append({
                "line_number": int(m.group(1)),
                "po_item": po_item,
                "material_description": m.group(2).strip(),
                "hsn_sac_code": m.group(3),
                "quantity": float(m.group(4).replace(",", "")),
                "unit": m.group(5),
                "unit_price": float(m.group(6).replace(",", "")),
                "line_net_amount": float(m.group(7).replace(",", "")),
                "gst_rate_pct": 18.0,
                "gst_amount": round(float(m.group(7).replace(",", "")) * 0.18, 2)
            })

        return {
            "header": {
                "vendor_name": vendor_name,
                "vendor_gstin": vendor_gstin,
                "vendor_invoice_number": invoice_number,
                "invoice_date": "",
                "po_number": po_number,
                "gross_amount": gross_amount,
                "gst_amount": round(gross_amount * 0.18 / 1.18, 2),
                "net_amount_before_gst": round(gross_amount / 1.18, 2),
            },
            "lines": extracted_lines,
            "_source": "digital_extractor"
        }
    except Exception as e:
        logger.error(f"Fallback parse failed: {e}")
        return None


async def extract_invoice_from_pdf(pdf_path: str | Path) -> Optional[dict]:
    """
    Send a PDF to Gemini for multimodal extraction.
    Uses inline bytes (never files.upload) and supports fast text pre-parsing.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        logger.error(f"PDF not found: {pdf_path}")
        return None

    pdf_bytes = pdf_path.read_bytes()
    text_content = _extract_text_via_pypdf2(pdf_path)

    # 1. Attempt Gemini extraction across fallback models
    client = _get_client()

    for model_name in MODELS_TO_TRY:
        try:
            logger.info(f"Attempting Gemini extraction on {pdf_path.name} using model {model_name}...")

            # If digital text exists, pass text + prompt (very fast & reliable)
            if text_content and len(text_content) > 100:
                contents = [f"{EXTRACTION_PROMPT}\n\nVendor Invoice Document Content:\n{text_content}"]
            else:
                # Scanned image PDF: pass inline binary bytes
                contents = [
                    types.Content(
                        parts=[
                            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                            types.Part.from_text(text=EXTRACTION_PROMPT),
                        ]
                    )
                ]

            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=4096,
                ),
            )

            raw_text = response.text.strip()
            if raw_text.startswith("```"):
                raw_text = raw_text.split("\n", 1)[1]
                if raw_text.endswith("```"):
                    raw_text = raw_text[:-3].strip()

            result = json.loads(raw_text)
            logger.info(f"✅ Extracted invoice from PDF ({pdf_path.name}) using {model_name}")
            return result

        except json.JSONDecodeError as e:
            logger.warning(f"Model {model_name} JSON decode error: {e}")
            continue
        except Exception as e:
            logger.warning(f"Model {model_name} failed: {e}")
            continue

    # 2. Heuristic fallback for digital invoices if Gemini is temporarily down
    logger.info("Attempting heuristic parser fallback...")
    fallback_res = _fallback_parse_digital_pdf(text_content, pdf_path.name)
    if fallback_res:
        logger.info(f"✅ Fallback parser extracted basic invoice data from {pdf_path.name}")
        return fallback_res

    logger.error(f"All extraction attempts failed for {pdf_path.name}")
    return None


EXPLANATION_PROMPT = """You are a finance analyst at Ashvaka Industries Group. Write a concise, human-readable
explanation (2-4 sentences) for why this invoice line was {outcome}. Use plain business language.

Invoice: {invoice_doc_number}, Line {line_number}
Vendor: {vendor_name}
Material: {material_id} ({category})
Value Band: {value_band}
Invoice Amount: ₹{invoice_amount:,.2f}
Value at PO Price: ₹{value_at_po_price:,.2f}
Price Variance: ₹{price_var_inr:,.2f} ({price_var_pct:+.2f}%)
Quantity Variance: {qty_var_qty:+.3f} {unit} ({qty_var_pct:+.2f}%) = ₹{qty_var_inr:,.2f}
Clauses triggered: {clauses}
Reasons: {reasons}
"""


async def generate_variance_explanation(
    invoice_doc_number: str,
    line_number: int,
    vendor_name: str,
    material_id: str,
    category: str,
    value_band: str,
    outcome: str,
    invoice_amount: float,
    value_at_po_price: float,
    price_var_inr: float,
    price_var_pct: float,
    qty_var_qty: float,
    qty_var_pct: float,
    qty_var_inr: float,
    unit: str,
    clauses: list[str],
    reasons: list[str],
) -> str:
    """Generate a human-readable variance explanation using Gemini."""
    prompt = EXPLANATION_PROMPT.format(
        outcome=outcome,
        invoice_doc_number=invoice_doc_number,
        line_number=line_number,
        vendor_name=vendor_name,
        material_id=material_id,
        category=category,
        value_band=value_band,
        invoice_amount=invoice_amount,
        value_at_po_price=value_at_po_price,
        price_var_inr=price_var_inr,
        price_var_pct=price_var_pct,
        qty_var_qty=qty_var_qty,
        qty_var_pct=qty_var_pct,
        qty_var_inr=qty_var_inr,
        unit=unit,
        clauses=", ".join(clauses),
        reasons="; ".join(reasons),
    )

    client = _get_client()
    for model_name in MODELS_TO_TRY:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=256,
                ),
            )
            return response.text.strip()
        except Exception:
            continue

    return "; ".join(reasons)
