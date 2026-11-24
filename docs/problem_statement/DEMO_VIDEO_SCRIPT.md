# 🎙️ 1-Shot Demo Video Script (Simple & Conversational)

> **Instructions for Recording:**  
> Just read the text below out loud while following the simple on-screen instructions in `[brackets]`.  
> No complex math to memorize. Smooth, natural, and straight to the point!

---

### [START RECORDING]

`[Action: Start with Airtable open on screen, showing the invoice_header table with 'Parked' rows]`

"Hello everyone! Welcome to my demonstration of Problem Statement A2: Autonomous Three-Way Matching for Accounts Payable, built for Ashvaka Industries Group.

In construction and manufacturing, accounts payable teams deal with hundreds of parked vendor invoices every month. Before paying any invoice, the team must cross-check three separate records: what was ordered on the Purchase Order, what actually arrived at the site in the Goods Receipts, and what the vendor billed on the Invoice. Doing this manually takes 15 to 20 minutes per invoice and is prone to human error.

To automate this, we built an AI Employee using **Supervity Auto**, integrated with **Airtable** as our ERP database and **Slack** for human approvals—with zero reliance on Google integrations."

---

`[Action: Switch tab to Supervity Auto, showing the full Workgraph on canvas]`

"Here is our AI Employee inside Supervity Auto. 

Whenever an invoice arrives in Airtable with the status 'Parked', our workflow triggers automatically. 

First, it locks the record by updating its status to 'Processing' so no duplicate runs occur. Next, it pulls the matching Purchase Order and Goods Receipts, normalizes any unit differences, and calculates price and quantity variances. 

Based on Ashvaka’s company policy and material tolerances, our workflow branches into three clear outcomes:
1. **Auto-Pass** for clean invoices.
2. **Escalate to Slack** for variances that need human review.
3. **Auto-Stop** for policy violations or data errors."

---

`[Action: Point to or show the Auto-Pass execution, or switch to Airtable showing invoice 5105600001 as Passed]`

"Let's look at our first scenario: **The Auto-Pass**.

When an invoice matches the Purchase Order and Goods Receipts within tolerance, the AI Employee processes it straight through. As you can see here in Airtable, invoice 5105600001 was automatically evaluated and updated to 'Passed' in just a few seconds. No humans were disturbed, and the invoice is immediately ready for payment."

---

`[Action: Switch to Supervity showing the 'Human Discrepancy Review' node, then switch to Slack]`

"Next is our second scenario: **Human-in-the-Loop Escalation**.

Here we have invoice 5105600035. The vendor billed for aggregate where the delivery weight slightly exceeded our pass tolerance. 

Instead of stopping or passing it blindly, the AI Employee flags it as 'Escalated' and pauses execution. Over in our Slack channel, the assigned procurement manager instantly receives this interactive notification card. It highlights the invoice details, the variance, and includes a direct review link.

`[Action: Click the review form link, show the Approve button, and click Approve]`

The manager can review the discrepancy right here and click 'Approve'. As soon as that decision is submitted, Supervity receives the callback, resumes the workflow, and updates the invoice status in Airtable to 'Passed' with the approver's audit stamp."

---

`[Action: Switch back to Supervity Workgraph, pointing to the 'Update Status to Stopped' branch]`

"Now for our third scenario: **Auto-Stop and the Declared Exception**.

If an invoice contains a severe discrepancy, quotes a closed PO, or bills in an unsupported unit of measure that cannot be converted, the system trips our Declared Exception rule. 

The AI Employee immediately halts automated processing, marks the invoice as 'Stopped' in Airtable, and routes an urgent alert to the Financial Controller. This guarantees that unverified or high-risk invoices are never paid automatically."

---

`[Action: Click on the 'Audit Trail' tab in Supervity Auto and scroll through the logs]`

"Finally, here is the **Supervity Audit Trail**. 

Every single step—from Airtable lock, to variance checks, to Slack approvals and status updates—is permanently recorded with exact timestamps and data payloads for complete financial audit compliance.

To wrap up: this AI Employee eliminates over 230 manual spreadsheet checks a month, reduces invoice matching time from 20 minutes to seconds, and ensures 100% compliance with corporate policy. 

Thank you!"

### [STOP RECORDING]
