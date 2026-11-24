# 🛡️ PolicyGuard AP: Agentic AI for Automated Three-Way Transaction Reconciliation

> **Enterprise Accounts Payable AI Agent for Ashvaka Industries Group (Policy FIN-AP-07 v3.2)**  
> *Autonomous Straight-Through Processing, Multi-Modal PDF Ingestion, Human-in-the-Loop Slack Escalations & Zero-Leakage Audit Trails.*

---

## 📌 Executive Summary

**PolicyGuard AP** is a production-grade, full-stack AI-powered Three-Way Transaction Matching platform. It automates invoice reconciliation across **Purchase Orders (`EKPO`)**, **Goods Receipts (`MSEG`)**, and **Vendor Invoices (`RBKP/RSEG`)**, enforcing strict compliance with corporate finance policy `FIN-AP-07 v3.2`.

### The Core Philosophy: Strict Separation of AI Perception vs. Math
- **Sensory Perception (Gemini Multimodal AI):** Extracts unformatted header fields, multi-line billing tables, and tax details from digital/scanned PDFs.
- **Deterministic Verification Engine (Pure Python):** 100% mathematical precision for unit of measure conversions, price/quantity variance formulas, and tolerance checks with **zero AI hallucinations**.

---

## 🚀 Live Demo Scenarios

| Scenario | Target Document | Trigger / Condition | Business Outcome |
| :--- | :--- | :--- | :--- |
| **Story 1: Auto-Pass (STP)** | Invoice `5105600001` | Rates and quantities match agreed PO & GRN | **Auto-Passed (< 1.2s)** directly for payment clearance. |
| **Story 2: Slack Escalation** | Invoice `5105600035` | 1.2% weighbridge bulk aggregate variance | **Escalated** to Procurement Head via interactive Slack card. |
| **Story 3: Hard Stop & Leakage** | Invoice `5105600103` | Vendor billed against closed/deleted PO line (`CL-1`) | **Stopped (HOLD-1)** payment block; requires Controller override (`APR-1`). |
| **Story 4: Multimodal PDF Ingestion**| `SankalpElectric...pdf` | Raw scanned vendor invoice PDF uploaded | Extracted by **Gemini AI**, matched live against ERP. |

---

## 🛠️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             CLIENT DASHBOARD                                │
│        React 18 + Vite + Tailwind CSS (Executive Story Cards & Search)      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTP / REST
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                            FASTAPI BACKEND                                  │
│                      (Port 8000 / Render / Railway)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Concurrency Locking (Parked -> Processing)                               │
│  • Deterministic 3-Way Policy Engine (FIN-AP-07 v3.2)                        │
│  • Multimodal Gemini Vision Ingestion (gemini-flash-lite)                   │
│  • Interactive Slack Block Kit Webhooks (Approve / Reject / APR-1 Release)  │
│  • Immutable Audit Logger (SQLite audit.db)                                 │
└──────────────┬───────────────────────────────┬──────────────────────────────┘
               │                               │
┌──────────────▼─────────────┐   ┌─────────────▼──────────────────────────────┐
│    DUAL-MODE ERP LAYER     │   │              SLACK WORKSPACE               │
│ • SQLite ERP (local_erp.db)│   │ • Interactive Decision Cards               │
│ • Airtable API (pyairtable)│   │ • Real-time Mobile Approvals               │
└────────────────────────────┘   └────────────────────────────────────────────┘
```

---

## 📐 Policy Clauses Implemented

- **`CL-1`**: Closed / Deleted PO Line Detection (`LOEKZ=L`, `EREKZ=X`, `closed`).
- **`REC-1 / REC-2`**: Net Goods Received formula: $\sum \text{Movement 101} - \sum \text{Movement 102} - \sum \text{Movement 122}$. Auto-stop on zero receipt.
- **`UOM-1 / UOM-2 / UOM-3`**: 23+ unit aliases and 2-hop graph unit of measure conversions.
- **`PV-1 / PV-2`**: Price per unit normalization ($\text{NETPR} / \text{PEINH}$) and percentage price variance.
- **`QV-1 / QV-2 / QV-3 / QV-4`**: Available quantity calculation and over-delivery tolerance ceiling ($\text{UEBTO}$).
- **`BOTH-1`**: Hard stop if both price and quantity variances breach tolerance simultaneously.
- **`OR-1 / OR-2`**: Over-delivery cap and multiple partial invoice tracking.
- **`CUM-1`**: Cumulative PO value threshold check escalating breaches to the CFO Office.
- **`HOLD-1`**: Immediate payment block on stopped invoices.
- **`ESC-1 / ESC-2 / ESC-3`**: Seniority-based approver delegation (Plant Accounts Head $\to$ Procurement Head $\to$ CFO Office).
- **`APR-1`**: Financial Controller manual override with mandatory audit reasoning.

---

## 💻 Tech Stack

- **Frontend:** React 18, Vite, Tailwind CSS, Lucide Icons
- **Backend:** Python 3.10+, FastAPI, Uvicorn, Pydantic v2
- **AI / OCR:** Google Gemini API (`google-genai` SDK, `gemini-flash-lite-latest`)
- **Messaging:** Slack Interactive Block Kit (`slack-sdk`)
- **Storage / Database:** SQLite (Dual-mode ERP repository + immutable audit log) / Airtable
- **Deployment:** Vercel (Frontend), Render / Railway (Backend)

---

## ⚡ Quick Start (Local Development)

### 1. Prerequisites
- Python 3.10+
- Node.js 18+ & npm
- Git

### 2. Clone the Repository
```bash
git clone https://github.com/harshalpatil-IITGN/PolicyGuard_AP.git
cd PolicyGuard_AP
```

### 3. Backend Setup
```bash
cd backend
python -m venv venv

# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Fill in your GEMINI_API_KEY, SLACK credentials in backend/.env
```

Start the FastAPI backend:
```bash
uvicorn main:app --reload --port 8000
```
Backend API will be live at `http://localhost:8000` (Swagger docs at `/docs`).

### 4. Frontend Setup
In a new terminal:
```bash
cd frontend
npm install
npm run dev
```
Frontend will be live at `http://localhost:5173`.

---

## 🌐 Deployment Guide

### Option 1: Frontend on Vercel
1. Push this repository to GitHub.
2. Sign in to [Vercel](https://vercel.com) and click **"Add New Project"**.
3. Import `PolicyGuard_AP`.
4. In the project settings:
   - **Root Directory:** Select `frontend`
   - **Framework Preset:** Vite
   - **Environment Variables:**
     - `VITE_API_URL` = `https://<your-backend-domain>/api` (or leave empty if using Vercel rewrites).
5. Click **Deploy**.

### Option 2: Backend on Render / Railway
1. Create a **New Web Service** on [Render](https://render.com) or [Railway](https://railway.app).
2. Connect the `PolicyGuard_AP` GitHub repository.
3. Configure settings:
   - **Root Directory:** `backend`
   - **Environment:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add your Environment Variables (`GEMINI_API_KEY`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`, `ERP_DATA_SOURCE=local`).
5. Set the generated backend URL in your frontend's `VITE_API_URL` and in Slack's **Interactivity Request URL** (`https://<backend-url>/api/slack/interact`).

---

## 📁 Repository Directory Structure

```
PolicyGuard_AP/
├── backend/
│   ├── main.py                  # FastAPI application & REST endpoints
│   ├── config.py                # Centralized settings & environment loader
│   ├── requirements.txt         # Python dependencies
│   ├── Procfile                 # Cloud web service startup command
│   ├── .env.example             # Example environment template
│   ├── models/                  # Pydantic schemas (invoices, matching, audit)
│   ├── services/
│   │   ├── matching_engine.py   # Deterministic 3-way match engine (FIN-AP-07)
│   │   ├── airtable_client.py   # Dual-mode data layer (SQLite / Airtable)
│   │   ├── gemini_service.py    # Multimodal PDF extraction via Gemini Vision
│   │   ├── slack_service.py     # Interactive Block Kit cards & callbacks
│   │   └── audit_logger.py      # Immutable SQLite audit trail
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── vercel.json              # SPA routing rules for Vercel
│   ├── src/
│   │   ├── config.js            # Environment-aware API base configuration
│   │   ├── App.jsx              # Navigation and main layout
│   │   └── pages/
│   │       ├── Dashboard.jsx    # Executive Showcase & 4 Story Walkthrough
│   │       ├── UploadPDF.jsx    # Drag-and-drop PDF ingestion & live match
│   │       └── AuditLogs.jsx    # Searchable audit trail viewer
├── data/
│   ├── local_erp.db             # Full mock ERP database (2,028 records)
│   ├── audit.db                 # SQLite audit event store
│   └── uploads/                 # Test sample invoice PDFs
├── docs/
│   ├── architecture.md          # Technical pipeline & system architecture
│   ├── bu_exp.md                # Business explanation & Q&A for stakeholders
│   └── execution_guide.md       # Step-by-step testing & demo guide
├── seed_local_erp.py            # Automated ERP seeder script
├── .gitignore                   # Excludes .env, node_modules, venvs
└── README.md                    # Project documentation
```

---

## 👥 Contributors & Hackathon Track
- **Project:** PolicyGuard AP
- **Track:** Track A2 — Autonomous Three-Way Transaction Reconciliation
- **Organization:** Ashvaka Industries Group
