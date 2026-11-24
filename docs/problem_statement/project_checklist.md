# Supervity Auto Hackathon Master Checklist (Track A2)

## Phase 1: Environment & Systems Configuration
- [x] Sign in to Supervity Auto workspace.
- [x] Go to `More` -> `Integrations` and connect Airtable using Personal Access Token.
- [x] Connect Slack workspace and verify bot permissions for messaging and interactive block actions.
- [x] Confirm no Google integrations (Gmail, Sheets, Drive) are active or referenced in the workspace.
- [x] Create dedicated Slack channel: `#finance-escalations`.

## Phase 2: Airtable Data Base & Mock ERP Ingestion
- [x] Create Airtable Base: `Ashvaka_ERP_A2` (or `Supervity_A2_ERP`).
- [x] Build Table 1: `invoice_header` & `invoice_line` (with Status enum and quantities).
- [x] Build Table 2: `po_line` & `po_header` (with PEINH price unit, quantities, prices).
- [x] Build Table 3: `goods_receipt` (with movement types 101, 102, 122).
- [x] Build Table 4: `unit_conversion` (material-specific MARM factors).
- [x] Build Table 5: `approver_matrix` (with Slack IDs and seniority levels).
- [x] Populate tables with dataset records extracted from `setup_kit/csv_plain/`.
- [ ] Insert/Verify at least 1 "Clean Match" test invoice (`Status = Parked`).
- [ ] Insert/Verify at least 1 "Tolerance Escalation" test invoice (`Status = Parked`, e.g. `5105600035`).
- [ ] Insert/Verify at least 1 "Declared Exception / UOM Mismatch" test invoice (`Status = Parked`).

## Phase 3: Agent Orchestration & Workbench Construction
- [x] Open Supervity Auto main prompt window.
- [x] Input Master Prompt binding Airtable trigger, arithmetic nodes, and Slack routing.
- [x] Switch to Supervity `Workbench` to review the generated execution graph.
- [x] Configure Airtable Ingestion Step: Filter on `Invoices` table where `Status = 'Parked'`.
- [x] Configure Record Retrieval Steps: Pull related `PO_Lines`, sum `Goods_Receipts`, and load `Approver_Matrix`.
- [x] Configure Unit Conversion & Normalization block: Standardize units of measure.
- [x] Configure Arithmetic Engine: Compute Price Variance % and Quantity Variance % against net receipts.
- [x] Configure Branching / Policy Gate:
  - [x] Branch A: `PASS` path (updates Airtable directly to `Passed`).
  - [x] Branch B: `ESCALATE` path (routes to assigned manager on Slack).
  - [x] Branch C: `STOP` path (routes to Financial Controller on Slack).

## Phase 4: Declared Exception & Human-in-the-Loop Implementation
- [x] Implement Declared Exception rule: UOM discrepancy without a valid conversion factor.
- [x] Verify agent sets record to `STOP` with reason `Unit Conversion Failure` when tripped.
- [x] Build Slack interactive notification blocks containing:
  - [x] Invoice ID and PO Number.
  - [x] Computed Price Variance and Quantity Variance percentages.
  - [x] Exact policy rule violated.
  - [x] Action buttons: `Approve Override` and `Reject Invoice`.
- [x] Implement callback listener: Ensure user clicks in Slack resume the Supervity workflow and update Airtable with the final verdict and reviewer ID.

## Phase 5: Verification, Audit Trails & Demo Submission
- [x] Run end-to-end live test on "Clean Match" record and confirm autonomous pass in Airtable.
- [x] Run end-to-end live test on "Escalation" record and confirm Slack notification to manager (Verified with live Slack card!).
- [x] Test Human-in-the-Loop decision callback (Verified: Rejection properly handled, Workgraph reached End!).
- [x] Inspect Supervity `Audit Trails` / Workgraph execution (All nodes completed green!).
- [x] Fill out the official 1-page Round 1 Brief:
  - [x] Job definition.
  - [x] Trigger mechanism.
  - [x] Rules applied.
  - [x] Connected systems (Airtable, Slack).
  - [x] Declared exception.
  - [x] Human approval boundary.
  - [x] Evaluator reproduction instructions.
- [ ] Record 5-minute screen recording with voiceover showing live, autonomous execution without human assistance on standard paths.
- [ ] Submit workspace link, brief, and video demo before the Round 1 deadline.