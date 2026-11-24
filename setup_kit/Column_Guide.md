# A2 column guide

Every table and column in the pack, with the plain name used in `csv_plain/` and `supabase_seed.sql`. The pack keeps the enterprise names because that is what you meet on the job.

## approver_matrix (`Approver_Matrix`)

One rule saying who receives an escalation or a stopped invoice, by trigger, value band, category and plant.

| Plain name | In the pack | Meaning |
|---|---|---|
| rule_id | MATRIX_ID | Row id of the approver rule, AM-01 to AM-17. |
| trigger | TRIGGER | What sends an invoice to this person: a line price or quantity variance, a receipt above the ordered quantity (OR-1), the PO cumulative limit (CUM-1), or the release of a stopped invoice (APR-1). |
| value_band | VALUE_BAND | Band 1 (line up to Rs 1,00,000), Band 2 (up to Rs 10,00,000), Band 3 (above Rs 10,00,000), or Any. |
| categories | CATEGORY | Material categories the rule covers, separated by semicolons (bulk; manufactured; service; capex), or 'all categories'. |
| plant_code | WERKS | Plant the rule applies to, or All; plant codes match po_line.plant_code. |
| approver_role | APPROVER_ROLE | Job title of the approver, for example Plant accounts head for one site, Procurement head, or Financial controller in the CFO office. |
| approver_name | APPROVER_NAME | Name of the person who receives the escalation. |
| approver_email | APPROVER_EMAIL | Approver's email address (fictional; send test mail only to mailboxes you control). |
| seniority_level | LEVEL | Seniority: 1 = Plant accounts head, 2 = Procurement head, 3 = Financial controller, CFO office (most senior). |

## po_header (`EKKO_PO_Header`)

One purchase order: who it was placed with, by which group company, when, and its total net value.

| Plain name | In the pack | Meaning |
|---|---|---|
| po_number | EBELN | Purchase order number, 10 digits starting 45. |
| company_code | BUKRS | Group company that placed the PO: AI10 Ashvaka Infrastructure, AC20 Ashvaka Cement and Building Materials, AE30 Ashvaka Energy, AL40 Ashvaka Logistics and Warehousing. |
| po_type | BSART | Purchase order type; NB = standard purchase order (the only type here). |
| vendor_id | LIFNR | Vendor number; links to vendor.vendor_id. |
| vendor_name | VENDOR_NAME | Vendor name as held on the PO. |
| purchasing_org | EKORG | Purchasing organisation that owns the PO; AS01 is the group's single buying organisation. |
| buyer_group | EKGRP | Purchasing group, the buyer team that raised the PO (P10 to P40). |
| po_date | BEDAT | Date the PO was created, dd.mm.yyyy. |
| currency | WAERS | Currency of the PO; always INR. |
| po_net_value | NETWR_TOTAL | Total net value of the PO in rupees before GST, the sum of its lines excluding deleted lines; used for the PO cumulative limit. |
| payment_terms | ZTERM | Payment terms code: NT30, NT45, NT60 = pay within 30, 45 or 60 days; MSME45 = 45 days for a registered MSME supplier. |
| line_count | LINE_COUNT | Number of lines on the PO. |

## po_line (`EKPO_PO_Item`)

One line of a purchase order: what was ordered, how much, in which unit, at what price, and whether the line is still open.

| Plain name | In the pack | Meaning |
|---|---|---|
| po_number | EBELN | Purchase order number; links to po_header. |
| po_item | EBELP | Line number on the PO: 10, 20, 30 or 40. |
| material_id | MATNR | Material or service number; links to material. |
| item_text | TXZ01 | Short description of what was ordered. |
| material_group | MATKL | Material group code, for example AGG01 aggregates, CEM01 cement, SRV01 manpower. |
| plant_code | WERKS | Site that ordered and receives the item: 1001 Ahmedabad Head Office, 1002 Sanand Industrial Park Project, 1003 Dahej Terminal Expansion Project, 1004 Vadodara Ring Road Package 3, 2001 Vadodara Grinding Unit, 2002 Rajkot RMC Plant, 3001 Bhuj Solar Park Phase 2, 4001 Bhiwandi Distribution Centre. |
| account_assignment | KNTTP | Where the cost is booked: P = project, K = cost centre, A = fixed asset, blank = bought into stock with no direct booking. |
| item_category | PSTYP | Item category: 0 = standard goods item, D = service item. |
| ordered_qty | MENGE | Quantity ordered, in the order unit (order_unit). |
| order_unit | BSTME | Order unit of the line (MT, KG, EA, MTR, CUM, MANDAY, MONTH, TRIP, DAY, SET and so on); all comparisons are made in this unit. |
| net_price | NETPR | Agreed net price before GST for the number of units in price_unit. |
| price_unit | PEINH | How many units net_price is for: 1 or 100. Price per unit = net_price divided by price_unit, so 4,850 with price unit 100 is Rs 48.50 per unit. |
| line_net_value | NETWR | Net value of the line in rupees: ordered_qty x net_price / price_unit. |
| over_delivery_tolerance_pct | UEBTO | Over-delivery tolerance as a percentage of the ordered quantity (2, 3, 5 or 10); blank means 0%. |
| delivery_completed_flag | ELIKZ | X = the buyer marked deliveries on this line as complete; blank otherwise. Under policy CL-1 this flag alone does not close the line. |
| final_invoice_flag | EREKZ | Final invoice indicator: X = a final invoice has been posted and the line is closed for further invoicing; blank otherwise. |
| deletion_flag | LOEKZ | Deletion indicator: L = the line has been deleted; blank otherwise. |
| line_status | STATUS | Open or Closed; capitalisation varies (Open, OPEN, open) and some values carry a trailing space. |
| delivery_date | EINDT | Scheduled delivery date, dd.mm.yyyy. |
| buyer_note | CHANGE_NOTE | Last note from the buyer about the line, usually blank. |

## material (`MARA_Material`)

One material or service the group buys, with its policy category, base unit and GST code.

| Plain name | In the pack | Meaning |
|---|---|---|
| material_id | MATNR | Material or service number. |
| description | MAKTX | Name of the material or service. |
| material_type | MTART | Material type: ROH = raw material, HAWA = traded goods, NLAG = non-stock item, DIEN = service. |
| material_group | MATKL | Material group code. |
| material_group_text | MATKL_TEXT | Plain name of the material group, for example Aggregates or Manpower supply. |
| base_unit | MEINS | Base unit the material is counted in (KG, EA, MTR, CUM, MANDAY and so on); unit_conversion factors are stated in this unit. |
| usual_order_unit | BSTME_DEFAULT | Unit the material is usually ordered in; the actual order unit of a PO line is po_line.order_unit. |
| category | CATEGORY | Policy category: bulk, manufactured, service or capex; it sets the price and quantity tolerances. |
| hsn_sac_code | HSN_SAC | GST classification code: HSN for goods, SAC (starting 99) for services. |
| gst_rate_pct | GST_PCT | GST rate in percent: 5, 12 or 18. |

## unit_conversion (`MARM_UoM_Conversion`)

One unit conversion for one material, for example 1 BAG of this cement = 50 KG.

| Plain name | In the pack | Meaning |
|---|---|---|
| material_id | MATNR | Material the conversion belongs to; links to material. |
| description | MAKTX | Name of the material. |
| alternative_unit | MEINH | The other unit, for example MT, BAG, CUM, KM, DRUM, BOX, COIL or PAL. |
| base_units | UMREZ | Number of base units in the conversion (for example 50 in '1 BAG = 50 KG'). |
| alternative_units | UMREN | Number of alternative units in the conversion; always 1 here. |
| base_unit | MEINS | Base unit of the material (KG, MTR or EA). |
| reads_as | READS_AS | The conversion written out, for example '1 BAG = 50 KG'; factors are specific to each material. |

## goods_receipt (`MSEG_Goods_Receipt`)

One receipt of goods or services at a site against a PO line, or a reversal or return of an earlier receipt.

| Plain name | In the pack | Meaning |
|---|---|---|
| receipt_doc_number | MBLNR | Material document number of the receipt, reversal or return. |
| receipt_doc_year | MJAHR | Year of the material document; always 2026. |
| receipt_doc_line | ZEILE | Line within the material document, usually 1. |
| movement_type | BWART | Movement type: 101 = goods or service received, 102 = a 101 reversed (cancelled), 122 = goods returned to the vendor. Quantities are always positive, so 102 and 122 must be subtracted. |
| posting_date | BUDAT | Date the movement was posted; mostly dd.mm.yyyy, some yyyy-mm-dd. |
| po_number | EBELN | PO the receipt was posted against. |
| po_item | EBELP | PO line the receipt was posted against. |
| material_id | MATNR | Material or service received. |
| plant_code | WERKS | Site that received it. |
| vendor_id | LIFNR | Vendor who delivered. |
| qty_entered | ERFMG | Quantity as entered at the gate or site, in qty_unit_entered. |
| qty_unit_entered | ERFME | Unit as entered at the gate or site (MT, KG, BAG, BOX, DRUM, KM, CUM, COIL, PAL, EA, MANDAY and so on); it can differ from the PO order unit. |
| original_receipt_doc | REF_MBLNR | For a 102 or 122: the receipt document it cancels or returns against; blank for 101. |
| original_receipt_line | REF_ZEILE | For a 102 or 122: the line of that original receipt; blank for 101. |
| delivery_note_ref | DELIVERY_NOTE | Vendor's delivery challan or delivery note number, or the service entry sheet number (SES) for services; written in several styles. |
| weighbridge_slip | WB_SLIP | Weighbridge slip number for bulk loads weighed at the site; blank otherwise. |
| vehicle_number | VEHICLE_NO | Registration number of the truck that delivered; blank for services. |
| remark | SGTXT | Free text note from the storekeeper, mainly on reversals and returns; usually blank. |

## invoice_header (`RBKP_Invoice_Header`)

One parked vendor invoice waiting for the match: the trigger.

| Plain name | In the pack | Meaning |
|---|---|---|
| invoice_doc_number | BELNR | Internal document number of the parked invoice, 5105600001 onwards; the queue is worked in this order. |
| fiscal_year | GJAHR | Year of the invoice document; always 2026. |
| company_code | BUKRS | Group company being billed: AI10 Ashvaka Infrastructure, AC20 Ashvaka Cement and Building Materials, AE30 Ashvaka Energy, AL40 Ashvaka Logistics and Warehousing. |
| vendor_id | LIFNR | Vendor number; links to vendor.vendor_id. |
| vendor_name | VENDOR_NAME | Vendor name as printed on the invoice; spelling and legal suffix vary from the vendor master. |
| vendor_gstin | VENDOR_GSTIN | Vendor's 15 character GST number; the first two digits are the state code. |
| vendor_invoice_number | XBLNR | The vendor's own invoice number as printed, in many styles (for example PQL/26-27/0682 or 000531). |
| invoice_date | BLDAT | Invoice date as printed by the vendor, in several formats (07-09-2026, 11-09-26, 11/09/2026, Sep 7, 2026, 2026-09-07 and others). |
| posting_date | BUDAT | Accounting posting date, dd.mm.yyyy. |
| parked_at | PARKED_ON | When accounts payable parked the invoice: yyyy-mm-dd hh:mm:ss in IST, or with a T and Z meaning UTC. |
| parked_by | PARKED_BY | User id of the accounts payable clerk who parked it. |
| po_numbers_quoted | REF_PO | PO number or numbers quoted by the vendor; several are separated by a comma, semicolon or slash. |
| currency | WAERS | Currency; always INR. |
| gross_amount | RMWWR | Invoice total in rupees including GST; usually a plain number, sometimes text with digit grouping in Indian (25,60,630.58) or international (2,687,756.80) style. |
| gst_amount | WMWST1 | Total GST on the invoice in rupees. |
| status | STATUS | Parked, meaning saved and waiting for the match before it can be posted. |
| invoice_pdf_path | ATTACHMENT | Path to the PDF image of the invoice as received, when there is one (40 of 213); some are phone photos or scans with no text layer. |

## invoice_line (`RSEG_Invoice_Item`)

One line of a parked vendor invoice, as the vendor billed it.

| Plain name | In the pack | Meaning |
|---|---|---|
| invoice_doc_number | BELNR | Parked invoice this line belongs to; links to invoice_header. |
| invoice_line_number | BUZEI | Line number on the invoice, 1 to 6. |
| po_number | EBELN | PO number the vendor quoted for this line. |
| po_item_quoted | EBELP | PO line or lines quoted: usually 10, 20, 30, sometimes with leading zeros (00010) or two items in one value (10/20, 10 & 20, 10, 20, 10+20). |
| material_id | MATNR | Material or service billed; links to material. |
| item_text | ITEM_TEXT | Description as printed by the vendor. |
| hsn_sac_code | HSN_SAC | GST classification code printed on the line. |
| billed_qty | MENGE | Quantity billed, in billed_unit. |
| billed_unit | MEINS | Unit as written by the vendor, including spellings such as TON, Tonne, M.T., KGS, Nos, PCS, Man-days, Bags or Hrs; the policy unit table maps them. |
| unit_price | UNIT_PRICE | Price per billed unit in rupees before GST. |
| line_net_amount | WRBTR | Line amount in rupees before GST; this sets the value band and is compared with the value at PO price. |
| gst_rate_pct | TAX_PCT | GST rate on the line: 5, 12 or 18. |
| gst_amount | TAX_AMT | GST on the line in rupees. |

## prior_invoice (`RSEG_Prior_Invoiced`)

One earlier invoice line already posted (or posted and reversed) against a PO line in this pack.

| Plain name | In the pack | Meaning |
|---|---|---|
| invoice_doc_number | BELNR | Document number of an earlier invoice already posted on the same PO lines (5105500101 onwards). |
| fiscal_year | GJAHR | Year of the document; always 2026. |
| invoice_line_number | BUZEI | Line of that earlier invoice; always 1 here. |
| vendor_id | LIFNR | Vendor who sent it. |
| vendor_invoice_number | XBLNR | Vendor's own invoice number on the earlier invoice. |
| invoice_date | BLDAT | Date on the earlier invoice, dd.mm.yyyy. |
| posting_date | BUDAT | Date it was posted, dd.mm.yyyy. |
| po_number | EBELN | PO it was posted against. |
| po_item | EBELP | PO line it was posted against. |
| material_id | MATNR | Material or service invoiced. |
| invoiced_qty | MENGE | Quantity invoiced, already in the PO order unit. |
| order_unit | BSTME | PO order unit of that quantity. |
| unit_price | UNIT_PRICE | Price per order unit in rupees before GST. |
| net_amount | WRBTR | Net amount in rupees before GST. |
| final_invoice_flag | FINAL_INVOICE | X when the vendor marked this as the final invoice for the line; blank otherwise. |
| status | STATUS | Posted, or Reversed (a reversed invoice was cancelled and takes no quantity). |
| reversal_date | REVERSAL_DATE | Date the invoice was reversed, dd.mm.yyyy; blank if still posted. |

## vendor (`Vendor_Master_Extract`)

One vendor, with address, tax ids, MSME status and contacts.

| Plain name | In the pack | Meaning |
|---|---|---|
| vendor_id | LIFNR | Vendor number. |
| legal_name | NAME1 | Vendor's registered name. |
| supplies | CATEGORY_LABEL | What the vendor supplies, for example Cement, Cables or Manpower supply. |
| street | STREET | Street address. |
| city | CITY | City. |
| state | STATE | State. |
| gst_state_code | STATE_CODE | Two digit GST state code: 24 Gujarat, 27 Maharashtra, 29 Karnataka, 08 Rajasthan, 33 Tamil Nadu, 07 Delhi, 23 Madhya Pradesh. |
| pin_code | PSTLZ | Six digit postal PIN code. |
| pan | PAN | Vendor's 10 character income tax PAN. |
| gstin | GSTIN | Vendor's registered 15 character GST number. |
| is_msme | MSME | Y if the vendor is a registered micro, small or medium enterprise, N if not. |
| udyam_number | UDYAM_NO | MSME registration number (UDYAM-...); blank for non-MSME vendors. |
| contact_name | CONTACT_NAME | Vendor's sales contact. |
| contact_email | CONTACT_EMAIL | Contact's email (fictional). |
| accounts_email | ACCOUNTS_EMAIL | Vendor's accounts team email (fictional). |
| phone | PHONE | Vendor phone number (fictional). |
| payment_terms | ZTERM | Payment terms code: NT30, NT45, NT60 = 30, 45 or 60 days; MSME45 = 45 days for an MSME. |
