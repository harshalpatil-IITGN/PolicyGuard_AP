"""
Slack service — sends Block Kit escalation cards and handles interactive callbacks.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from config import SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
from models.schemas import InvoiceMatchResult, LineMatchResult, MatchOutcome

logger = logging.getLogger(__name__)


def _get_client() -> WebClient:
    return WebClient(token=SLACK_BOT_TOKEN)


# ═══════════════════════════════════════════════════════════════════════════
# Escalation card
# ═══════════════════════════════════════════════════════════════════════════

def send_escalation_card(
    result: InvoiceMatchResult,
    channel_id: Optional[str] = None,
) -> Optional[str]:
    """
    Post an interactive Block Kit card for an escalated invoice.
    Returns the Slack message timestamp (ts) on success, None on failure.
    """
    ch = channel_id or SLACK_CHANNEL_ID
    if not SLACK_BOT_TOKEN or not ch:
        logger.warning("Slack not configured — skipping escalation card")
        return None

    blocks = _build_escalation_blocks(result)
    text = f"🔶 Invoice {result.invoice_doc_number} requires approval from {result.final_approver_name}"

    try:
        client = _get_client()
        resp = client.chat_postMessage(
            channel=ch,
            text=text,
            blocks=blocks,
        )
        logger.info(f"Slack escalation sent for {result.invoice_doc_number}: ts={resp['ts']}")
        return resp["ts"]
    except SlackApiError as e:
        logger.error(f"Slack API error: {e.response['error']}")
        return None


def send_stop_alert(
    result: InvoiceMatchResult,
    channel_id: Optional[str] = None,
) -> Optional[str]:
    """Post an urgent alert for a stopped invoice."""
    ch = channel_id or SLACK_CHANNEL_ID
    if not SLACK_BOT_TOKEN or not ch:
        logger.warning("Slack not configured — skipping stop alert")
        return None

    blocks = _build_stop_blocks(result)
    text = f"🔴 Invoice {result.invoice_doc_number} has been STOPPED — Financial Controller review required"

    try:
        client = _get_client()
        resp = client.chat_postMessage(channel=ch, text=text, blocks=blocks)
        logger.info(f"Slack stop alert sent for {result.invoice_doc_number}: ts={resp['ts']}")
        return resp["ts"]
    except SlackApiError as e:
        logger.error(f"Slack API error: {e.response['error']}")
        return None


def send_approval_confirmation(
    channel_id: str,
    message_ts: str,
    invoice_doc_number: str,
    action: str,
    approver_name: str,
) -> None:
    """Update the original Slack message after an approver acts."""
    try:
        client = _get_client()
        emoji = "✅" if action == "approve" else "❌"
        new_text = (
            f"{emoji} Invoice {invoice_doc_number} was *{action.upper()}D* by {approver_name}"
        )
        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text=new_text,
            blocks=[
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": new_text},
                }
            ],
        )
    except SlackApiError as e:
        logger.error(f"Slack update error: {e.response['error']}")


# ═══════════════════════════════════════════════════════════════════════════
# Block builders
# ═══════════════════════════════════════════════════════════════════════════

def _fmt_inr(amount: float) -> str:
    """Format amount as ₹ with Indian comma grouping."""
    if amount < 0:
        return f"-₹{abs(amount):,.2f}"
    return f"₹{amount:,.2f}"


def _build_escalation_blocks(result: InvoiceMatchResult) -> list[dict]:
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🔶 Invoice Escalation: {result.invoice_doc_number}",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Vendor:*\n{result.vendor_name}"},
                {"type": "mrkdwn", "text": f"*Vendor Invoice:*\n{result.vendor_invoice_number}"},
                {"type": "mrkdwn", "text": f"*Approver:*\n{result.final_approver_name}"},
                {"type": "mrkdwn", "text": f"*Role:*\n{result.final_approver_role}"},
            ],
        },
        {"type": "divider"},
    ]

    # Add line-level variance details for escalated lines
    for lr in result.line_results:
        if lr.outcome != MatchOutcome.PASS:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*Line {lr.invoice_line_number}* — PO {lr.po_number} Item(s) {lr.po_items_matched}\n"
                        f"• Category: `{lr.category}` | Band: `{lr.value_band}`\n"
                        f"• Invoice Amount: {_fmt_inr(lr.invoice_line_net_amount)}\n"
                        f"• Value at PO Price: {_fmt_inr(lr.value_at_po_price)}\n"
                        f"• Price Variance: {_fmt_inr(lr.price_variance_inr)} ({lr.price_variance_pct:+.2f}%)\n"
                        f"• Qty Variance: {lr.qty_variance_qty:+.3f} {lr.po_order_unit} ({lr.qty_variance_pct:+.2f}%) = {_fmt_inr(lr.qty_variance_inr)}\n"
                        f"• *Outcome:* `{lr.outcome.value}` — {'; '.join(lr.reasons)}"
                    ),
                },
            })

    # Action buttons
    blocks.append({"type": "divider"})
    blocks.append({
        "type": "actions",
        "block_id": f"escalation_actions_{result.invoice_doc_number}",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "✅ Approve", "emoji": True},
                "style": "primary",
                "action_id": "approve_invoice",
                "value": result.invoice_doc_number,
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "❌ Reject", "emoji": True},
                "style": "danger",
                "action_id": "reject_invoice",
                "value": result.invoice_doc_number,
            },
        ],
    })
    return blocks


def _build_stop_blocks(result: InvoiceMatchResult) -> list[dict]:
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🔴 Invoice STOPPED: {result.invoice_doc_number}",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Vendor:*\n{result.vendor_name}"},
                {"type": "mrkdwn", "text": f"*Vendor Invoice:*\n{result.vendor_invoice_number}"},
            ],
        },
        {"type": "divider"},
    ]

    for lr in result.line_results:
        if lr.outcome == MatchOutcome.STOP:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*Line {lr.invoice_line_number}* — `STOPPED`\n"
                        f"Reasons: {'; '.join(lr.reasons)}\n"
                        f"Clauses: {', '.join(lr.clauses)}"
                    ),
                },
            })

    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": "⚠️ This invoice is held under HOLD-1. Only the Financial Controller (CFO office) can release it under APR-1.",
            }
        ],
    })
    blocks.append({"type": "divider"})
    blocks.append({
        "type": "actions",
        "block_id": f"stop_actions_{result.invoice_doc_number}",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "🔓 Release Stop (APR-1 Override)", "emoji": True},
                "style": "primary",
                "action_id": "release_stopped_invoice",
                "value": result.invoice_doc_number,
            }
        ],
    })
    return blocks
