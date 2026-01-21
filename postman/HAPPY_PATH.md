# Happy Path: Reconciliation & AI Testing

A simple, step-by-step workflow to test reconciliation and AI explanation endpoints using pre-seeded data.

## Prerequisites

✓ Server running: `poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`  
✓ `.env` has `ENABLE_SEED_ENDPOINTS=true`  
✓ `.env` has valid `GEMINI_API_KEY` (or AI will use heuristic fallback)  
✓ Postman collection imported with environment selected

---

## Happy Path Workflow (5 minutes)

### Step 1: Seed Fresh Data
**Request:** Seed Lifecycle Management → **1. Seed Test Data**

**Action:** Click **Send**

**Expected Response:**
```json
{
  "status": "success",
  "tenant_id": 1,
  "invoices_created": 5,
  "transactions_created": 5,
  "matches_created": 3,
  "message": "Seed completed"
}
```

**What happened:** System created demo tenant with invoices and bank transactions pre-loaded.

---

### Step 2: Verify Seeded Data
**Request:** Seed Lifecycle Management → **2. Check Seed Status (Before)**

**Action:** Click **Send**

**Expected Response:**
```json
{
  "total_invoices": 5,
  "total_transactions": 5,
  "total_matches": 3,
  "date_range": {
    "earliest": "2025-12-20",
    "latest": "2026-01-20"
  }
}
```

**What this shows:** You have invoices and transactions ready to reconcile.

---

### Step 3: Run Reconciliation
**Request:** Reconciliation → **Run Reconciliation**

**Action:** Click **Send**

**Expected Response:**
```json
{
  "tenant_id": 1,
  "matches": [
    {
      "id": 12,
      "invoice_id": 3,
      "bank_transaction_id": 5,
      "score": 95.2500,
      "status": "proposed",
      "reason": "Amount match with date proximity"
    },
    {
      "id": 13,
      "invoice_id": 4,
      "bank_transaction_id": 6,
      "score": 87.5000,
      "status": "proposed",
      "reason": "Amount match"
    },
    // ... more matches
  ],
  "total_matches": 3,
  "reconciliation_summary": {
    "processed_invoices": 5,
    "matched_invoices": 3
  }
}
```

**What this shows:**
- System scored all invoice-transaction pairs
- Top matches returned with confidence scores
- `match_id` (first one: `12`) auto-captured for next step

---

### Step 4: Get AI Explanation (Happy Path)
**Request:** Reconciliation → **Get AI Explanation for Match**

**Pre-check:** Ensure `match_id` is set (from previous response). The collection auto-captures it; verify in:
- **Postman:** Environments → RMS API - Local Development → `match_id` should show a number

**Action:** Click **Send**

**Expected Response (with AI enabled):**
```json
{
  "match_id": 12,
  "invoice_id": 3,
  "bank_transaction_id": 5,
  "explanation": "The invoice amount of $1,250.00 matches the transaction amount exactly, and the posting date (2026-01-15) aligns closely with the invoice date (2026-01-15). This is a highly confident match.",
  "confidence": 95,
  "source": "gemini",
  "processing_time_ms": 342
}
```

**Or (fallback, if AI disabled):**
```json
{
  "match_id": 12,
  "invoice_id": 3,
  "bank_transaction_id": 5,
  "explanation": "Amount match: exact match on amount ($1,250.00). Date proximity: within 0 days.",
  "confidence": 95,
  "source": "heuristic",
  "processing_time_ms": 2
}
```

**What this shows:**
- AI (or heuristic) explains why the match was proposed
- Confidence score aligns with reconciliation score
- You can trust this match for confirmation

---

### Step 5: Confirm the Match
**Request:** Reconciliation → **Confirm Match**

**Action:** Click **Send**

**Expected Response:**
```json
{
  "id": 12,
  "invoice_id": 3,
  "bank_transaction_id": 5,
  "status": "confirmed",
  "confirmed_at": "2026-01-20T14:32:15Z",
  "score": 95.2500,
  "reason": "Amount match with date proximity"
}
```

**Side effects (automatic):**
- Match status: `proposed` → `confirmed`
- Invoice status: `pending` → `matched`
- Any other proposed matches for invoice #3 are rejected

---

### Step 6: Inspect Results (Optional)
**Request:** Reconciliation → **List Matches for Invoice**

**Pre-check:** Replace `{{invoice_id}}` with `3` (from step 4)

**Action:** Click **Send**

**Expected Response:**
```json
{
  "invoice_id": 3,
  "tenant_id": 1,
  "matches": [
    {
      "id": 12,
      "bank_transaction_id": 5,
      "status": "confirmed",  // ← Changed from "proposed"
      "score": 95.2500,
      "confirmed_at": "2026-01-20T14:32:15Z"
    }
  ]
}
```

**What this shows:** Confirmed match persisted in the system.

---

## Summary: What You Tested

| Step | Endpoint | Result |
|------|----------|--------|
| 1 | `POST /api/v1/seed` | ✅ Demo data created |
| 2 | `GET /api/v1/seed/status` | ✅ Verified 5 invoices, 5 transactions |
| 3 | `POST /api/v1/tenants/1/reconcile?top=5&min_score=50` | ✅ Generated matches with scores |
| 4 | `GET /api/v1/tenants/1/matches/12/explain` | ✅ AI explanation retrieved |
| 5 | `POST /api/v1/tenants/1/matches/12/confirm` | ✅ Match confirmed, statuses updated |
| 6 | `GET /api/v1/tenants/1/invoices/3/matches` | ✅ Confirmed match visible |

---

## Common Variations

### Test Multiple Matches
After step 3 (Reconciliation), instead of confirming only one:

1. Note the `id` of the **second** match (e.g., `13`)
2. In the Postman environment, update `match_id` to `13`
3. Run step 4 (Explain) for match #13
4. Run step 5 (Confirm) for match #13
5. Repeat for more matches

### Test With Minimum Score Filter
In **Step 3 (Run Reconciliation)**, edit the URL query params:
```
?top=10&min_score=75    # Only high-confidence matches
?top=20&min_score=50    # More lenient, more matches
```

### Test Without AI Explanation
If you want to skip AI and use heuristic:
1. Temporarily comment out `GEMINI_API_KEY` in `.env` (or set empty)
2. Restart server
3. Re-run Step 4 (Explain)
4. Response will use `"source": "heuristic"` instead

### Cleanup & Reseed
After testing, to reset:
1. Seed Lifecycle Management → **3. Cleanup**
2. Seed Lifecycle Management → **1. Seed Test Data** (repeat happy path)

---

## Troubleshooting This Workflow

| Problem | Cause | Solution |
|---------|-------|----------|
| Step 1 returns 403 | `ENABLE_SEED_ENDPOINTS=false` | Set to `true` in `.env`, restart server |
| Step 3 returns no matches | Seed data empty | Run Step 1 first |
| Step 4 returns 404 | `match_id` not set correctly | Verify in environment that `match_id` is a number (e.g., 12) |
| Step 4 returns 503 | Gemini API key invalid | Check `GEMINI_API_KEY` in `.env`, or leave empty for heuristic fallback |
| Step 5 returns 409 | Match already confirmed | Reconcile again (Step 3) to get new matches |

---

## Next: Manual Testing Variations

Once comfortable with happy path, try:
1. **Import custom transactions** - Use Bank Transactions → Import endpoint
2. **Create custom invoices** - Use Invoices → Create endpoint
3. **Test idempotency** - Use Bank Transactions workflows with Idempotency-Key
4. **GraphQL queries** - Use GraphQL Queries folder for alternative interface

---

## Request Checklist

Before each run:
- ✓ Server running on `:8000`
- ✓ `ENABLE_SEED_ENDPOINTS=true`
- ✓ Environment set to "RMS API - Local Development"
- ✓ Base URL is `http://localhost:8000`

**Ready?** Click **1. Seed Test Data** → **Send** 🚀
