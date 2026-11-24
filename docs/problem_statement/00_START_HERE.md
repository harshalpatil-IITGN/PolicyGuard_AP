# Start here: A2

**Three-way matching across the purchase order, the invoice and the goods receipt**

## The story

Ashvaka Industries Group buys cement, steel, aggregates, cables, solar modules, manpower and equipment hire for its sites in Gujarat and Maharashtra, and its accounts payable team has 213 vendor invoices parked and waiting to be checked before anything is paid. Each invoice line has to agree with two other records: the purchase order line that fixed the price and quantity, and the goods receipts that show what actually reached the site. The three rarely line up on the first look, because a vendor may bill in kilograms or cubic metres what the weighbridge recorded in tonnes, charge a little above the agreed price, or bill more than was received. The group's written variance policy decides how much difference is acceptable, and the answer changes with the kind of material, the size of the line and what has already been invoiced on the order. The AI Employee matches every line, converts the units, works out the price and quantity difference, applies the policy to pass, escalate or stop it, and sends anything that needs a decision to the named approver with the evidence attached.

## Open these three files first

1. `dataset/reference/Variance_Policy.md`: The only source of tolerances, outcomes and approvers; start with sections 1, 4, 7, 8, 9, 11 and 12.
2. `dataset/csv/RSEG_Invoice_Item.csv`: The invoice lines to match, with the PO line quoted, the billed quantity, the vendor's unit and the line amount.
3. `dataset/csv/EKPO_PO_Item.csv`: The PO lines each invoice line is checked against: order unit, price, price unit, tolerance and whether the line is open.

## Words you will meet

| Term | Meaning |
|---|---|
| Three-way match | Checking each invoice line against the purchase order line (what was agreed) and the goods receipt (what arrived) before paying. It stops the company paying for goods it never received or at a price it never agreed. |
| Goods receipt (GRN) | The record a site makes when goods arrive, often called a goods receipt note. For services such as manpower or crane hire the same table holds a service entry, which records the days or hours actually delivered. |
| Movement type | A three digit code on each receipt row saying what happened: 101 = received, 102 = an earlier receipt cancelled, 122 = goods sent back to the vendor. The net received quantity is 101 minus 102 minus 122. |
| Parked invoice | An invoice that accounts payable has entered and saved but not yet posted to the books. It waits in the queue until the match decides whether it can be posted and paid. |
| Price unit | The number of units the PO price is quoted for, in column PEINH. A price of Rs 5,120 with a price unit of 100 means Rs 51.20 per metre, so always divide before comparing. |
| Unit of measure conversion | Turning a quantity in one unit into another, for example bags of cement into tonnes. The policy compares everything in the PO order unit, and factors for bags, boxes, drums, coils, pallets and cubic metres differ by material and come only from MARM_UoM_Conversion. |
| Tolerance | The amount of difference the policy accepts without asking anyone, set as a percentage and a rupee cap, whichever is lower. Above the pass limit a person must approve, and above the stop limit the line cannot be paid as billed. |
| Value band | A size bracket set by the invoice line amount before GST: Band 1 up to Rs 1,00,000, Band 2 up to Rs 10,00,000, Band 3 above that. The band sets the rupee caps and decides which approver receives an escalation. |
| Price variance and quantity variance | Price variance is how much more the line costs than the same quantity at the PO price. Quantity variance is how much more was billed than is still available to bill, after receipts and earlier invoices. |
| Over-delivery tolerance | The percentage above the ordered quantity a vendor may deliver on a PO line (column UEBTO, blank means zero). Receipts up to that allowance are accepted; beyond it a procurement head must decide. |
| Final invoice indicator | A flag (EREKZ = X) set when the last invoice on a PO line has been posted. Together with a Closed status or the deletion flag LOEKZ, it means the line cannot take any more invoices. |

## One record, end to end

**Invoice 5105600035: a unit conversion that escalates**

1. RBKP_Invoice_Header row 5105600035 is from Orbit Stone Crusher & Co (vendor 200282) on PO 4500010498, and RSEG_Invoice_Item line 1 bills 62.744 CUM of Coarse Aggregate 20 mm at Rs 1,620 per CUM, Rs 1,01,645.28 before GST.
2. EKPO_PO_Item line 4500010498/10 ordered 300 MT at Rs 1,080 per MT (price unit 1) for plant 1003, and MARA_Material puts material 11000301 in category bulk.
3. MSEG_Goods_Receipt has two 101 receipts on that line, 5000101029 for 28.234 MT and 5000101594 for 64.766 MT, so 93.000 MT has been received, and RSEG_Prior_Invoiced has nothing on the line.
4. MARM_UoM_Conversion says 1 CUM of this material is 1,500 KG, so the invoice is 94.116 MT: the price is exact (94.116 x Rs 1,080 = Rs 1,01,645.28) but 1.116 MT more was billed than received.
5. That quantity variance is 1.20% and Rs 1,205.28: inside the Band 2 rupee cap of Rs 10,000 but above the 0.5% bulk pass limit and below the 2.0% stop limit, so line 1 escalates.
6. Line 2 (107.831 MT of GSB Material) matches its single receipt and passes, so the invoice escalates, and Approver_Matrix row AM-10 (Band 2, bulk) names Amit Fernandes, Procurement head, materials.

**Outcome.** Escalate the whole invoice to Amit Fernandes (Procurement head, materials, amit.fernandes@ashvakagroup.in) with the PO, both receipts, the 1 CUM = 1,500 KG conversion and the working; it is not posted until he releases or rejects line 1.

**Why.** UOM-1 converts the 62.744 CUM into the PO's tonnes, and QV-2 lets bulk material be billed at most 0.5% above what was received, so 1.20% needs a person (APR-2) but is under the 2.0% stop limit. OUT-1 makes the invoice an escalation, and ESC-1 with ESC-3 send it to the Band 2 bulk approver because the line amount is just over Rs 1,00,000.

## What the Round 1 minimum needs

- Tables: `invoice_header` (RBKP_Invoice_Header), `invoice_line` (RSEG_Invoice_Item), `po_line` (EKPO_PO_Item), `goods_receipt` (MSEG_Goods_Receipt), `material` (MARA_Material), `unit_conversion` (MARM_UoM_Conversion), `approver_matrix` (Approver_Matrix)
- Staged replies: None. This pack has no mailbox. Put parked invoices in your own table, or send them to your own inbox, so a new invoice is the trigger.
- Watch for: Variances are on net amounts before GST. Some PO lines are priced per 100 units (PEINH), so divide before comparing.
- Ready-made tables: `setup_kit/` in this folder.
- Not needed: the rest of the pack.

## What the job costs by hand

213 invoices were parked between 12 Sep and 09 Oct 2026, about 230 a month. Do one by hand with a stopwatch before you build. Minutes per record times records per month is what your AI Employee gives back.
