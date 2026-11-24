# Invoice Variance Policy for Three-Way Matching

Ashvaka Industries Group, Finance Controls

## About this policy

Policy FIN-AP-07, version 3.2, effective 1 July 2026. Owner: CFO office, Ashvaka Industries Group. Applies to Ashvaka Infrastructure Limited (AI10), Ashvaka Cement and Building Materials Limited (AC20), Ashvaka Energy Limited (AE30) and Ashvaka Logistics and Warehousing Limited (AL40).

This policy decides what happens to each line of a vendor invoice that is matched against a purchase order (PO) line and the goods receipts or service entries posted against that line. Every line ends in one of three outcomes.

**Pass: the line can be posted and paid on its due date without further approval.**

**Escalate: the line needs the release of a named approver before the invoice is posted.**

**Stop: the line is not posted or paid in its present form. It is cleared by a revised invoice, a credit note, a goods receipt posting or a PO amendment, or released by the Financial controller, CFO office under clause APR-1.**

The policy covers the net value of the invoice before GST. GST, TDS and e-invoice checks are made separately by the tax team.

## 1. Terms used

- **PO line.** An item of a purchase order (EKPO). Its order unit (BSTME), net price (NETPR) and price unit (PEINH) come from the PO.
- **PO price per unit.** Net price divided by price unit. Rs 4,850 per 100 MTR is Rs 48.50 per MTR.
- **Net received quantity.** Receipts (movement 101) minus receipt reversals (102) minus returns to vendor (122) on the PO line, converted to the order unit.
- **Already invoiced quantity.** Quantity on posted invoices against the PO line (RSEG_Prior_Invoiced, status Posted), plus quantity taken by earlier invoices in the current queue (clause GEN-2). Invoices with status Reversed are ignored.
- **Available quantity.** Net received quantity, counted only up to the over-delivery allowance (clause OR-1), minus the already invoiced quantity.
- **Value at PO price.** Invoiced quantity in the order unit multiplied by the PO price per unit, rounded to the paisa.
- **Price variance.** Invoice line net amount minus the value at PO price. As a percentage, price variance divided by the value at PO price.
- **Quantity variance.** Invoiced quantity in the order unit minus the available quantity, when this is above zero. As a percentage, divided by the available quantity. Its value is the quantity variance multiplied by the PO price per unit.
- **Category.** bulk, manufactured, service or capex, as recorded for the material in MARA_Material.
- **Value band.** Set by the invoice line net amount as billed. Band 1: up to Rs 1,00,000. Band 2: above Rs 1,00,000 and up to Rs 10,00,000. Band 3: above Rs 10,00,000.

## 2. Order of work

GEN-1. Invoices are matched line by line. Each invoice line is matched to the PO line or lines it quotes.

GEN-2. When several invoices are waiting, they are matched in order of invoice document number (BELNR), lowest first. Quantity and price variance on an earlier invoice in the queue that did not stop count as already invoiced for later invoices on the same PO lines and the same PO.

GEN-3. A line's outcome is the most severe outcome reached under any clause. Stop is more severe than escalate, and escalate is more severe than pass. The reason given for a line names every clause that applies to it.

## 3. Checks before any variance is computed

DUP-1. If the same vendor has already submitted the same invoice number, the whole invoice stops. Numbers are compared ignoring capital and small letters, spaces and the characters - / . and _. The earlier submission can be a posted invoice that has not been reversed, or an invoice with a lower document number in the current queue. The same number from a different vendor is not a repeat. Numbers from the same vendor that still differ after this comparison, for example because the series prefix differs, are not repeats.

CL-1. If the invoice quotes a PO line that is closed, the line stops. A line is closed when its status is Closed, when the final invoice indicator (EREKZ) is set, or when the deletion indicator (LOEKZ) is set. The delivery completed indicator (ELIKZ) on its own does not close a line for invoicing.

REC-2. If the net received quantity on the quoted PO line is zero or less, the line stops. This covers invoices that arrive before any receipt and receipts that have been fully reversed or returned.

## 4. Units of measure

UOM-1. Before any comparison, convert the invoice quantity and every receipt quantity into the order unit of the PO line. Use the material's own conversions in MARM_UoM_Conversion first. Where the material has none for the pair of units, use the general conversions: 1 MT = 1,000 KG and 1 KM = 1,000 MTR. Conversions for bags, boxes, drums, coils, pallets and cubic metres of aggregate differ from material to material and exist only in MARM.

UOM-2. After conversion, round quantities to three decimal places. Units are read without regard to capitals, and the spellings in the table below mean the same unit. TON and TO always mean the metric tonne of 1,000 KG.

UOM-3. If an invoice quantity cannot be converted to the order unit, the line stops.

Because the price check works through the line amount, the unit the vendor priced in does not matter once the quantity has been converted.

| Unit | Also written as |
|---|---|
| MT | TON, TO, Tonne, M.T., MTS |
| KG | Kgs, KGS, kg |
| MTR | Mtr, M, RMT, Mtrs |
| KM | Km |
| EA | NOS, Nos, No., PCS |
| BAG | Bags, BAGS |
| CUM | M3, Cu.M, CBM |
| MANDAY | Man-days, MD, Man Day |
| MONTH | Month, MON, Months |
| TRIP | Trips, Trip |
| DAY | Days |
| SET | Set, Sets |
| SAMPLE | Samples |
| QTR | Quarter |
| HR | Hrs, Hours |
| PAIR | Pairs, PR |
| BOX | Box, Boxes |
| DRUM | Drums |
| COIL | Coils |
| PAL | Pallet, Pallets |
| PLATE | Plates |

## 5. Received quantity and receipts above the order

REC-1. Net received quantity includes every reversal and every return, including those posted after the invoice was parked. The match is made against the receipts as they stand when it is run.

OR-1. The over-delivery allowance of a PO line is the ordered quantity plus the line's over-delivery tolerance (UEBTO, a percentage of the ordered quantity; blank means zero). If the net received quantity is above the allowance, the line escalates to the Procurement head for the category, who decides between a PO amendment and a return. For the quantity check, the net received quantity counts only up to the allowance.

OR-2. If, on such a line, the quantity invoiced to date including this invoice is above the allowance, the line stops.

Receiving or invoicing more than the ordered quantity but not more than the allowance is accepted.

## 6. Invoice lines that cover more than one PO line

SPAN-1. An invoice line may quote two or more lines of the same PO for the same material. Allocate the invoiced quantity to the quoted lines in item number order, filling each up to its available quantity; anything left over goes to the last quoted line. The value at PO price is the sum of each allocated quantity at its own line's PO price. The price and quantity checks are then made once for the invoice line as a whole, against the combined available quantity. If any quoted line is closed, CL-1 applies. REC-2 applies when the quoted lines together have no net receipt.

## 7. Price variance

PV-1. An invoice price below the PO price is accepted and the invoice amount is paid. The reason records it.

PV-2. A price variance above zero is compared with two limits. The pass limit is the lower of the pass percentage of the value at PO price and the pass cap for the value band. The stop limit is the lower of the stop percentage and the stop cap. The line passes when the price variance is no more than the pass limit, stops when it is above the stop limit, and escalates in between. Limits are inclusive: a variance exactly equal to the pass limit passes.

| Category | Pass up to | Stop above |
|---|---|---|
| bulk | 2.0% | 5.0% |
| manufactured | 1.0% | 3.0% |
| service | 0.5% | 2.0% |
| capex | 0.25% | 1.5% |

| Value band | Pass cap | Stop cap |
|---|---|---|
| Band 1 (up to Rs 1,00,000) | Rs 1,500 | Rs 7,500 |
| Band 2 (up to Rs 10,00,000) | Rs 10,000 | Rs 50,000 |
| Band 3 (above Rs 10,00,000) | Rs 40,000 | Rs 2,00,000 |

## 8. Quantity variance

QV-1. Invoicing less than the available quantity is accepted as a partial invoice.

QV-2. Bulk materials may be invoiced slightly above the net received quantity, because vendor dispatch weights and site weighbridge weights differ. The line passes when the quantity variance is no more than 0.5% and its value is no more than the pass cap for the band. It stops when the quantity variance is above 2.0% or its value is above the stop cap for the band. In between, it escalates.

QV-3. Manufactured, service and capex lines have no quantity tolerance. Any quantity variance stops the line.

QV-4. If nothing is available because everything received has already been invoiced, any invoiced quantity is a quantity variance above the stop limit and the line stops.

## 9. Price and quantity variance on the same line

BOTH-1. If the price variance and the quantity variance are both outside their pass limits, the line stops, whatever each would have been on its own. If only one of them is outside its pass limit, the line takes that one's outcome.

## 10. PO cumulative limit

CUM-1. For each PO on the invoice, add up the price variance on that PO from posted invoices that have not been reversed, from earlier invoices in the queue that did not stop, and from this invoice. Only amounts above the PO price count; lines billed below the PO price do not reduce the total. For a posted invoice, the price variance is its amount minus its quantity at the PO price per unit.

The PO limit is the lower of 1.0% of the PO net value (NETWR_TOTAL in EKKO_PO_Header) and Rs 1,50,000. If the total is above the limit, every line of this invoice on that PO that would otherwise pass is escalated to the CFO office, even though each line is inside its own tolerance.

## 11. Invoice outcome

HOLD-1. If any line stops, the whole invoice is held and nothing on it is paid, including lines that pass. The hold notice lists every stopped line and what is needed to clear it, and goes to the Financial controller, CFO office for a decision under clause APR-1.

OUT-1. If no line stops and at least one line escalates, the invoice escalates. Otherwise the invoice passes.

## 12. Who receives an escalation

ESC-1. Price and quantity escalations go to the approver for the value band and category of the escalated line, as in the table below. The Plant accounts head is the one for the plant on the PO.

ESC-2. Escalations under OR-1 go to the Procurement head, services for service lines and to the Procurement head, materials for all other lines. Escalations under CUM-1 go to the CFO office.

ESC-3. Each escalated invoice goes to one approver: the most senior of the approvers for its escalated lines. The CFO office is senior to a Procurement head, who is senior to a Plant accounts head. Where two different approvers have the same seniority, the invoice goes to the approver of the escalated line with the higher invoice line net amount, and to the lower line number if the amounts are equal. Names and email addresses are in Approver_Matrix.

| Value band | bulk | manufactured | service | capex |
|---|---|---|---|---|
| Band 1 | Plant accounts head | Plant accounts head | Plant accounts head | Procurement head, materials |
| Band 2 | Procurement head, materials | Procurement head, materials | Procurement head, services | CFO office |
| Band 3 | CFO office | CFO office | CFO office | CFO office |

## 13. Evidence that travels with an escalation

EVD-1. Each escalation carries: the invoice record and its PDF where one exists; the PO header and every quoted PO line; every receipt, reversal and return on those lines; the posted invoices on those lines, and on the whole PO for CUM-1; the unit conversion used; the computed quantities, variances and limits; and the clause and reason for each line. The approver should be able to decide without opening another system.

## 14. What approvers can and cannot do

APR-1. An approver may release an escalated line or reject it. A rejected line is treated as a stop. A stopped invoice is not posted. It can be released only by the Financial controller, CFO office, named in Approver_Matrix, who must record the reason for the release on the invoice before it is posted. No other approver can release a stop, and a stop is never released automatically. Until the Financial controller records a release, or the stop is cleared by a revised invoice, a credit note, a goods receipt posting or a PO amendment, the whole invoice stays held under HOLD-1.

APR-2. Releasing anything above tolerance is always a decision for a person named in Approver_Matrix. Every change to this policy, including any limit in it, is approved in writing by the CFO office and applies from the effective date of the new version.

## 15. Worked examples (illustrative figures)

Example A. Bulk line, band 2. Value at PO price Rs 6,00,000; invoice Rs 6,09,000. Price variance Rs 9,000, which is 1.50%. Pass limit is the lower of 2.0% (Rs 12,000) and Rs 10,000, so Rs 10,000. The line passes.

Example B. The same 1.50% on Rs 8,00,000 is Rs 12,000, above the Rs 10,000 pass limit. The stop limit is the lower of 5.0% (Rs 40,000) and Rs 50,000, so Rs 40,000. The line escalates to the Procurement head, materials.

Example C. PO in MT at Rs 6,800 per MT. Receipt of 400 BAG, which MARM defines as 50 KG each for this cement, is 20.000 MT. Invoice of 20,000 KG at Rs 6.80 per KG is 20.000 MT and Rs 1,36,000, equal to the value at PO price. No variance.

Example D. PO net value Rs 40,00,000, so the PO limit is the lower of Rs 40,000 and Rs 1,50,000: Rs 40,000. Posted invoices carry Rs 36,500 of price variance and this invoice adds Rs 5,200 on a line that passes on its own. The total of Rs 41,700 is above the limit, so the line escalates to the CFO office.

## Version history

3.0, 1 April 2025: first version with value bands and rupee caps.

3.1, 1 October 2025: PO cumulative limit added.

3.2, 1 July 2026: capex pass tolerance reduced to 0.25%; band 3 caps revised.
