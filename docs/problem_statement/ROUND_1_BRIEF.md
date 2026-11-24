# 📄 Supervity Auto Hackathon — Round 1 Submission Brief
**Domain A: Autonomous Finance & Accounts Payable**  
**Problem Statement A2:** Three-Way Matching Across Purchase Order, Invoice, and Goods Receipt  
**Team / Participant:** Harshal Patil (`Supervity_Proj_1`)  
**Target Enterprise:** Ashvaka Industries Group (Policy FIN-AP-07 v3.2)

---

## 1. Job Definition
Autonomous Accounts Payable AI Employee responsible for auditing and validating parked vendor invoices against corresponding Purchase Order (PO) lines and Goods Receipt Notes (GRN) prior to posting and financial disbursement. The AI Employee replaces manual invoice reconciliation by performing unit conversions, multi-point mathematical variance analysis, policy tolerance threshold checks, and conditional routing (Auto-Pass, Escalate to Manager, or Halt/Stop).

- **Current Manual Baseline:** ~230 invoices/month across Gujarat and Maharashtra project sites; ~15–20 minutes per manual match across ERP screens.
- **AI Employee Impact:** Autonomous end-to-end reconciliation in <10 seconds per invoice; 100% policy compliance, zero duplicate payments, and automated Human-in-the-Loop audit trails.

---

## 2. Trigger Mechanism
- **System:** Airtable Mock ERP (`Ashvaka_ERP_A2` base, `invoice_header` table).
- **Trigger Condition:** Identification of any invoice record where `status == "Parked"`.
- **State Machine & Concurrency Control:**
  1. Trigger fires upon new parked invoice detection or manual batch sweep.
  2. AI Employee immediately updates `invoice_header.status` $\rightarrow$ `"Processing"` to lock the record and prevent duplicate processing across concurrent workers.

---

## 3. Connected Systems (Strictly Non-Google)
1. **Primary Database & ERP State Engine:** **Airtable**
   - Tables: `invoice_header`, `invoice_line`, `po_line`, `goods_receipt`, `material`, `unit_conversion`, `approver_matrix`.
2. **Human-in-the-Loop & Exception System:** **Slack** (`Supervity_Proj_1` workspace)
   - Real-time interactive notification cards posted to dedicated escalation channels with audit breakdowns and one-click Review Forms.
3. **Orchestration & Decision Platform:** **Supervity Auto** (`auto.supervity.ai`)
   - Visual Workgraph orchestrator, variance calculation engine, and state coordinator.
   - *Zero Google Workspace services utilized* (strictly compliant with hackathon constraints).

---

## 4. Policy Rules Applied (FIN-AP-07 v3.2)
1. **Pre-Check Integrity Gates:**
   - `DUP-1`: Exact vendor + invoice number duplicate check across posted and queued records.
   - `CL-1`: Closed line check (PO line status Closed, `EREKZ == 'X'`, or deletion indicator `LOEKZ == 'X'`).
   - `REC-2`: Zero receipt check (Net Received Qty $\le 0$).
2. **Net Received Quantity Formula:**
   $$\text{Net Received Qty} = \sum (\text{Movement 101 Receipts}) - \sum (\text{Movement 102 Reversals}) - \sum (\text{Movement 122 Returns})$$
3. **UOM Normalization (`UOM-1`, `UOM-2`):**
   - Material-specific factors from `unit_conversion` (MARM) translate invoice units to PO order units (e.g., $1\text{ CUM} = 1,500\text{ KG} = 1.5\text{ MT}$). Fallback general ratios applied if specific factor absent ($1\text{ MT} = 1,000\text{ KG}$).
4. **Variance Computation:**
   - $\text{PO Price per Unit} = \text{NETPR} / \text{PEINH}$ (factoring price units).
   - $\text{Price Variance} = \text{Invoice Line Total} - (\text{Normalized Qty} \times \text{PO Price per Unit})$.
   - $\text{Quantity Variance} = \text{Normalized Qty} - \text{Available Net Qty}$.
5. **Tolerance Bands & Decision Matrix:**
   - Evaluated across Material Categories (`bulk`, `manufactured`, `service`, `capex`) and Value Bands (Band 1: $\le ₹1\text{L}$, Band 2: $\le ₹10\text{L}$, Band 3: $> ₹10\text{L}$).
   - Rule `BOTH-1`: If both price and quantity exceed pass limits $\rightarrow$ Immediate STOP.
   - Rule `QV-3`: Manufactured, service, and capex permit 0% quantity tolerance $\rightarrow$ Non-zero qty variance causes immediate STOP.

---

## 5. Declared Exception
- **Exception Scenario:** Unit of Measure (UOM) incompatibility or missing conversion factor (`UOM-3`).
- **Trigger Condition:** An invoice bills in a unit distinct from the PO order unit, and neither material-specific conversion factors in `unit_conversion` nor system standard conversions exist.
- **System Action:**
  1. Halt automated processing immediately.
  2. Set invoice status to `Stopped` with audit reason: `"UOM-3: Unit Conversion Failure / Incompatible UOM"`.
  3. Route urgent exception alert directly to the Financial Controller (`Kruti Jadeja`) on Slack.

---

## 6. Human Approval Boundary (Human-in-the-Loop)
- **Escalation Boundary:** Invoices with variances exceeding the base pass threshold but within the permissible escalation band (e.g., bulk aggregate over-billing between 0.5% and 2.0%).
- **Interactive Routing:** Routes an interactive evidence card to the designated approver's Slack ID (retrieved dynamically from `approver_matrix` based on value band and category seniority).
- **Callback Loop:**
  - Approver reviews the variance breakdown and clicks **Approve** or **Reject** in Slack / Review Form.
  - Supervity workflow resumes asynchronously upon receiving callback:
    - **Approved:** Status flips to `Passed`, unlocking the invoice for accounting.
    - **Rejected:** Status flips to `Stopped`, notifying stakeholders that the invoice cannot be posted as billed.

---

## 7. Evaluator Reproduction Instructions
1. **Airtable Setup:**
   - Access Airtable base `Ashvaka_ERP_A2`.
   - Data pre-loaded with CSVs from `setup_kit/csv_plain/`.
2. **Run Standard Clean Match (Auto-Pass):**
   - Ensure invoice `5105600001` has `status == "Parked"`.
   - Trigger the workflow in Supervity Auto $\rightarrow$ record autonomously transitions to `Processing` $\rightarrow$ `Passed`.
3. **Run Golden Escalation Match (Human-in-the-Loop):**
   - Ensure invoice `5105600035` (or `5105600038`) has `status == "Parked"`.
   - Trigger the workflow $\rightarrow$ system flags variance and sets status to `Escalated`.
   - Verify Slack message in `#finance-escalations` / `#new-channel`.
   - Click the Review Form link $\rightarrow$ submit decision (Approve / Reject) $\rightarrow$ verify Airtable status updates to `Passed` or `Stopped`.
4. **Audit Trail Verification:**
   - In Supervity Auto, navigate to **Audit Trail** to inspect complete timeline, input JSON payloads, variance math, and approver identity stamps.
