![1795412442890](image/execution_guide/1795412442890.png)

# 🚀 PolicyGuard AP — Local Setup & Execution Guide

PolicyGuard AP is a production-grade, $0-cost Agentic AI and Deterministic Three-Way Matching Engine for Accounts Payable (Airtable + Slack + Gemini + SQLite + FastAPI + React Vite).

---

## 📌 Prerequisites

Before running the project, ensure you have the following installed on your machine:

- **Python**: `3.11+`
- **Node.js**: `v18+` or `v20+`
- **Package Manager**: `npm` or `pnpm`
- **Virtual Environment Tool**: `venv` (comes standard with Python)

---

## 🔐 1. Environment Configuration

Ensure your `backend/.env` file is populated with your API keys:

```env
# ── Airtable ──────────────────────────────────────────────────
AIRTABLE_API_KEY=pat_XXXXXXXXXXXXXXXXX
AIRTABLE_BASE_ID=appXXXXXXXXXXXXXXXX

# ── Slack ─────────────────────────────────────────────────────
SLACK_BOT_TOKEN=xoxb-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
SLACK_SIGNING_SECRET=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
SLACK_CHANNEL_ID=C0XXXXXXXXX

# ── Google Gemini (AI Studio Free Tier) ───────────────────────
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# ── App Settings ──────────────────────────────────────────────
BUSINESS_DATE=2026-10-09T18:00:00+05:30
LOG_LEVEL=INFO
```

---

## ⚙️ 2. Backend Setup & Execution

Open a terminal at the root of the repository (`Track_A2__Three_Way_Match`):

### Step 2.1: Navigate to backend

```bash
cd backend
```

### Step 2.2: Create and activate a Python virtual environment

**On Windows (PowerShell):**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

*(If PowerShell restricts script execution, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

**On macOS / Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 2.3: Install Python dependencies

```bash
pip install -r requirements.txt
```

### Step 2.4: Run the FastAPI backend server

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

- **Backend API**: `http://localhost:8000`
- **Interactive Swagger Docs**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/api/health`

---

## 💻 3. Frontend (Ops Console) Setup & Execution

Open a **second terminal** at the root of the repository (`Track_A2__Three_Way_Match`):

### Step 3.1: Navigate to frontend

```bash
cd frontend
```

### Step 3.2: Install Node dependencies

Using `pnpm`:

```bash
pnpm install
```

*(Or using `npm`: `npm install`)*

### Step 3.3: Start the Vite development server

```bash
pnpm dev
```

*(Or `npm run dev`)*

- **Ops Console Dashboard**: `http://localhost:5173`
- The frontend is pre-configured with a reverse proxy for all `/api` routes forwarding to `http://localhost:8000`.

---

## 🔔 4. Slack Interactivity Setup (Local Testing)

For Slack interactive cards (Approve / Reject buttons) to communicate back with your local server (`http://localhost:8000/api/slack/interact`), Slack requires a secure public HTTPS endpoint.

### Step 4.1: Expose local port 8000 using ngrok or cloudflared

In a separate terminal:

```bash
ngrok http 8000
```

You will get a public URL like `https://xxxx-xx-xx-xx.ngrok-free.app`.

### Step 4.2: Add Request URL to Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and select your **PolicyGuard AP** app.
2. In the left navigation, click **Interactivity & Shortcuts**.
3. Toggle Interactivity to **ON**.
4. In the **Request URL** field, enter:
   ```
   https://<your-ngrok-url>/api/slack/interact
   ```
5. Click **Save Changes**.

---

## 🧪 5. Testing & Verification Scenarios

Once both servers are running, test the core workflows via the Ops Console (`http://localhost:5173`) or curl/Swagger:

### Scenario A: Clean Match (Auto-Pass)

1. In Airtable `invoice_header`, ensure invoice `5105600001` has status `Parked`.
2. Go to Ops Console (`http://localhost:5173`) $\rightarrow$ Click **Match** on `5105600001` (or trigger `POST /api/invoices/process/5105600001`).
3. Verify status changes: `Parked` $\rightarrow$ `Processing` $\rightarrow$ `Passed`.
4. Check the **Audit Trail** tab to view the SQLite log entry.

### Scenario B: Golden Escalation (Slack Interactive Card)

1. Ensure invoice `5105600035` has status `Parked`.
2. Click **Match** in the Ops Console.
3. Verify:
   - Invoice status becomes `Escalated`.
   - An interactive Slack Block Kit card is posted to your Slack channel with:
     - Computed price & quantity variance percentages.
     - Violations cited (`QV-2` bulk quantity variance of 1.20%, exceeding 0.5% pass limit but within 2.0% stop limit).
     - Assigned approver name (Amit Fernandes / Procurement Head, materials).
     - **Approve** and **Reject** buttons.
4. Click **Approve** or **Reject** in Slack $\rightarrow$ verify status updates to `Passed` or `Stopped`, and the audit trail logs the human decision.

### Scenario C: Declared Exception / Auto-Stop (Deterministic Policy Guard)

This scenario demonstrates deterministic policy enforcement without human intervention: invoices that violate critical financial integrity rules are automatically stopped and held under policy `HOLD-1`.

#### Test Invoices for Auto-Stop:
- **`5105600103` (Closed / Deleted PO Line — Policy `CL-1`):**
  - **Context:** Vendor *Chitra Switchgear & Co* billed ₹5,63,568 against PO `4500010138` Line `20`.
  - **Violation:** PO Line 20 has deletion flag `LOEKZ = 'L'` and status `Closed`.
  - **Action:** Click **Match** on `5105600103`.
  - **Expected Outcome:** Immediately transitions: `Parked` $\rightarrow$ `Processing` $\rightarrow$ `Stopped` 🔴. An urgent stop alert is dispatched to the Financial Controller on Slack and logged to the SQLite audit trail.

- **`5105600025` (Zero Net Receipts — Policy `REC-2`):**
  - **Context:** Vendor *Anand Solar Systems & Co* billed ₹2,46,87,264 before any goods arrived.
  - **Violation:** Net received quantity is `0.000` (receipt document non-existent or reversed).
  - **Action:** Click **Match** on `5105600025`.
  - **Expected Outcome:** Autonomously transitions to `Stopped` 🔴 citing `REC-2: Net received quantity is 0.000 (zero or negative)`.

- **`5105600095` (Compounded Variance — Policies `BOTH-1` & `QV-3`):**
  - **Context:** Vendor *Uday Manpower Services Pvt Ltd* billed on service PO `4500010090`.
  - **Violation:** Both price variance (+1.20%) and quantity variance (+12 MANDAY on a zero-tolerance service category) are outside pass limits.
  - **Action:** Click **Match** on `5105600095`.
  - **Expected Outcome:** Autonomously transitions to `Stopped` 🔴 citing `BOTH-1` and `QV-3`.

### Scenario D: Scanned/Digital PDF Ingestion via Gemini 

1. Open the Ops Console $\rightarrow$ **Upload PDF** tab.
2. Upload any invoice from `dataset/documents/invoices/` (e.g. `Invoice_PQL-26-27-0682.pdf` or scanned photos like `scan_0096.pdf`).
3. Click **Upload & Process**.
4. Gemini Flash extracts header + line item JSON, and triggers the three-way match against ERP PO/GRN records.

---

## 📁 6. Future Deployment Notes

*(This section will be expanded with Docker / Cloud Run / Vercel configurations when transitioning to cloud hosting.)*
