# Reconciliation Scoring Strategy

## Overview

The reconciliation engine uses a **Weighted Scoring Model** to propose matches between invoices and bank transactions. This allows users to see "High Confidence" matches at the top, while still catching fuzzy matches that might indicate the same payment.

## Scoring Logic

### 1. Silver Bullet: Identifier Match (Score: 100)

If both the invoice `invoice_number` and transaction `external_id` are present, they are compared directly:

- **Exact Match**: `invoice_number == external_id` → **Score: 100**
- This is the highest confidence and short-circuits all other scoring logic.

**Example:**
- Invoice: invoice_number = "INV-500", external_id = null
- Transaction: external_id = "INV-500", description = "Payment"
- **Result**: Score 100 (Guaranteed match)

### 2. Amount Match (Mandatory, Score: 50)

The amount must match exactly between invoice and transaction.

- **Exact Match**: `invoice.amount == transaction.amount` → **+50 points**
- **No Match**: Different amounts → **Score 0** (No match possible)

**Rationale**: In reconciliation, amount mismatch is usually a deal-breaker. We return score 0 immediately.

### 3. Date Proximity (Optional, Score: 20 or 10)

Compares `invoice.invoice_date` with `transaction.posted_at`:

- **0–3 days apart**: **+20 points**
- **4–7 days apart**: **+10 points**
- **8+ days apart**: **0 points**

**Rationale**: Bank transactions typically post 1-3 days after invoice creation. This rewards close date matches.

### 4. Invoice Number Reference (Optional, Score: 25)

Checks if the invoice number appears in the transaction description/memo:

- **Found**: `invoice.invoice_number in transaction.description` → **+25 points**

**Example:**
- Invoice: invoice_number = "INV-500"
- Transaction: description = "Payment for INV-500 - thank you"
- **Result**: +25 points

### 5. Vendor Name Reference (Optional, Score: 15)

Checks if the vendor name appears in the transaction description (case-insensitive):

- **Found**: `vendor_name.lower() in transaction.description.lower()` → **+15 points**

### 6. Currency Mismatch Penalty (Score: -50)

If invoice and transaction currencies differ, apply a penalty:

- **Mismatch**: `invoice.currency != transaction.currency` → **-50 points**

**Rationale**: Currency differences usually indicate different transactions or currency conversion, which requires manual review.

## Score Ranges & Thresholds

| Score Range | Interpretation | User Action |
|-------------|-----------------|------------|
| **90–100** | High Confidence | Can auto-confirm or quick-confirm |
| **60–89** | Strong Suggestion | Review briefly before confirming |
| **0–59** | Potential Match (filtered out by default) | Requires manual investigation |

## Maximum Score Calculation

- **Identifier Match**: 100 (short-circuit, no other scoring)
- **Amount Match**: 50
- **Date Proximity**: 20
- **Invoice Reference**: 25
- **Vendor Reference**: 15
- **Total (without currency penalty)**: 110 → **capped at 100**

## Example Scenarios

### Scenario 1: High Confidence Match

```
Invoice: 
  - invoice_number: "INV-500"
  - amount: $1,200
  - invoice_date: Jan 1
  - currency: USD

Transaction:
  - external_id: "INV-500"
  - amount: $1,200
  - posted_at: Jan 1
  - currency: USD
  - description: "Payment for INV-500"

Scoring:
  1. Identifier match (INV-500 == INV-500) → Score = 100
  
Result: Score 100 (Immediate match - highest confidence)
```

### Scenario 2: Strong Match via Heuristics

```
Invoice:
  - invoice_number: "INV-500"
  - amount: $1,200
  - invoice_date: Jan 1
  - currency: USD

Transaction:
  - external_id: null
  - amount: $1,200
  - posted_at: Jan 2
  - currency: USD
  - description: "Customer payment INV-500"

Scoring:
  1. Amount match ($1,200 == $1,200) → +50
  2. Date proximity (1 day apart) → +20
  3. Invoice reference (INV-500 in description) → +25
  4. No currency mismatch → 0 penalty
  
Total: 50 + 20 + 25 = 95

Result: Score 95 (Strong confidence)
```

## Multi-Tenant Considerations

- Every query is scoped to `tenant_id`
- Scores are calculated independently per tenant
- No cross-tenant data leakage

## Algorithm Optimization

1. **Narrowing Phase**: Find invoices that are unmatched and transactions that are unconfirmed
2. **Scoring Phase**: Calculate scores only for these filtered subsets
3. **Storage Phase**: Store all scoring results as `MatchEntity` records with status="proposed"
4. **Ranking Phase**: Return top candidates by score descending
