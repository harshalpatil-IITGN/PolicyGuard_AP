# Three-way match: dataset

Ashvaka Industries Group matches every PO-based vendor invoice against the purchase order line and the goods receipts or service entries posted on it before the invoice is paid. The accounts payable team has parked a queue of vendor invoices that now wait for that match. Each invoice line has to be matched, its price and quantity variance computed, and the group's variance policy applied to reach pass, escalate or stop, with a reason an approver can read and the right approver named for every escalation.

Data as of 09 Oct 2026, 18:00 IST. Organisation: Ashvaka Industries Group (fictional). Every record, document and email is synthetic.

## What is where

- `A2_three_way_match_export.xlsx`: the enterprise export as one workbook. `00_INDEX` describes it and `Field_Dictionary` explains every sheet.
- `csv/`: the same sheets as CSV files, one per sheet.
- `documents/invoices/`: PDF images of some of the parked invoices, as received from vendors
- `reference/`: the group's invoice variance policy

## The tables

`RBKP_Invoice_Header` and `RSEG_Invoice_Item` are the queue: one header row per parked invoice and one row per invoice line. `EKKO_PO_Header` and `EKPO_PO_Item` hold the purchase orders, `MSEG_Goods_Receipt` the receipts, reversals and returns, and `RSEG_Prior_Invoiced` the invoices already posted against the same PO lines. `MARA_Material` gives each material its category, and `MARM_UoM_Conversion` its unit conversions. `Approver_Matrix` names who receives an escalation and who may release a stopped invoice. `Vendor_Master_Extract` lists the vendors.

## The documents

`documents/invoices/` holds PDF images of 40 of the parked invoices, as vendors sent them. Their content agrees with the invoice tables, which are the system record. Some are phone photos or photocopies with no text layer. `RBKP_Invoice_Header.ATTACHMENT` links an invoice to its image.

## The policy

`reference/Variance_Policy.md` (and the same text as a PDF) is the group's written variance policy. It is written for finance staff and is the only source of tolerances, limits and approvers.

## Formats

Dates appear in more than one format, especially invoice dates as printed by vendors. Amounts in `RBKP_Invoice_Header.RMWWR` are sometimes text with digit grouping. Vendor names on invoices vary in spelling and legal suffix. Units on invoices use vendor spellings (TON, Nos, Man-days and so on).

## Ground rules

- Treat 09 Oct 2026, 18:00 IST as the current time, and keep the business date as a setting in your build.
- Send outbound mail only to mailboxes you control. Every address in this pack is fictional.

## Using the data

Load the tables into the systems you connect (a database, an Airtable base, a ticketing or CRM tool) or park the files in a document store, and let your AI Employee read them through those integrations. The data is deliberately messy: mixed date and amount formats, spelling variants, blanks, duplicates, and documents that are present but wrong. Handling that is part of the job. Do not hardcode to these records; build for the pattern.

Google integrations (Drive, Sheets, Gmail, Calendar) are in beta for this event and must not be used. Host and read the data through alternatives such as Airtable, Supabase, SharePoint, OneDrive, Box, Dropbox or Outlook.
