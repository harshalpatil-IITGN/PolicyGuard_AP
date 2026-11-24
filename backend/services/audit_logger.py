"""
SQLite-backed immutable audit logger.

Every match run, status change, and approver action is logged here — NOT to
Airtable (free-tier row-limit protection).
"""

from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

from config import AUDIT_DB_PATH, IST
from models.schemas import AuditLogEntry

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# DB bootstrap
# ═══════════════════════════════════════════════════════════════════════════

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS audit_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT    NOT NULL,
    invoice_doc_number TEXT NOT NULL,
    event_type      TEXT    NOT NULL,
    outcome         TEXT    DEFAULT '',
    actor           TEXT    DEFAULT '',
    details         TEXT    DEFAULT ''
);
"""

_CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_audit_invoice
ON audit_log(invoice_doc_number);
"""


def _init_db() -> None:
    with _connect() as conn:
        conn.execute(_CREATE_TABLE)
        conn.execute(_CREATE_INDEX)
        conn.commit()


@contextmanager
def _connect():
    conn = sqlite3.connect(str(AUDIT_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# Run on import
_init_db()


# ═══════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════

def log_event(
    invoice_doc_number: str,
    event_type: str,
    outcome: str = "",
    actor: str = "system",
    details: str | dict = "",
) -> int:
    """Insert an immutable audit row. Returns the new row id."""
    now = datetime.now(IST).isoformat()
    if isinstance(details, dict):
        details = json.dumps(details, default=str)
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO audit_log (timestamp, invoice_doc_number, event_type, outcome, actor, details)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (now, invoice_doc_number, event_type, outcome, actor, details),
        )
        conn.commit()
        row_id = cur.lastrowid
    logger.info(
        f"Audit [{event_type}] invoice={invoice_doc_number} outcome={outcome} actor={actor}"
    )
    return row_id


def get_logs(
    invoice_doc_number: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
) -> list[AuditLogEntry]:
    """Query audit logs, optionally filtered by invoice."""
    with _connect() as conn:
        if invoice_doc_number:
            rows = conn.execute(
                "SELECT * FROM audit_log WHERE invoice_doc_number = ? ORDER BY id DESC LIMIT ? OFFSET ?",
                (invoice_doc_number, limit, offset),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM audit_log ORDER BY id DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
    return [
        AuditLogEntry(
            id=row["id"],
            timestamp=row["timestamp"],
            invoice_doc_number=row["invoice_doc_number"],
            event_type=row["event_type"],
            outcome=row["outcome"],
            actor=row["actor"],
            details=row["details"],
        )
        for row in rows
    ]


def get_log_count(invoice_doc_number: Optional[str] = None) -> int:
    with _connect() as conn:
        if invoice_doc_number:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM audit_log WHERE invoice_doc_number = ?",
                (invoice_doc_number,),
            ).fetchone()
        else:
            row = conn.execute("SELECT COUNT(*) as cnt FROM audit_log").fetchone()
    return row["cnt"]
