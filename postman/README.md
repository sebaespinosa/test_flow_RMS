# RMS API - Postman Collection for E2E Testing

This directory contains a comprehensive Postman collection for manual integration and end-to-end testing of the RMS (Reconciliation Management System) API.

## Files

- **RMS-API.postman_collection.json** - Complete API collection with 40+ requests organized by domain and workflow
- **RMS-API-Environment.postman_environment.json** - Environment variables for local development (base_url, tenant_id, etc.)

## Quick Start

### 1. Import Collection & Environment into Postman

1. Open **Postman** (web or desktop, v11+)
2. Click **Import** (top-left)
3. Select **RMS-API.postman_collection.json** → Import
4. Click **Import** again
5. Select **RMS-API-Environment.postman_environment.json** → Import
6. In the top-right dropdown, select **RMS API - Local Development** environment

### 2. Ensure API Server is Running

```bash
# From project root
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Start Testing

Navigate to any folder in the collection and use **Send** to execute requests.

---

## Collection Organization

### 📋 Seed Lifecycle Management
Essential for test data:
- **Seed Test Data** → Create fresh demo fixtures (tenants, invoices, transactions, matches)
- **Check Seed Status** → Inspect current dataset counts without mutation
- **Cleanup** → Delete all tenant-scoped data
- **Reseed** → Restore data after cleanup

**Typical flow:** Seed → Test → Cleanup → Reseed

### 👥 Tenants
Full CRUD operations:
- Create, List, Get, Update, Delete, Reactivate

**Environment capture:** Create Tenant response → manually copy `id` to `{{tenant_id}}`

### 📄 Invoices
Invoice management per tenant:
- Create, List, Get, Update, Delete

**Dependencies:** Requires `{{tenant_id}}` and valid `vendor_id`

### 🏦 Bank Transactions
Import with **idempotency** support:
- **Import (No Idempotency)** → First import without idempotency key
- **Import with Idempotency (First Attempt)** → Initial import with unique key (→ 201)
- **Retry Same Key** → Re-send identical payload (→ 200 cached)
- **Conflict: Same Key, Different Payload** → Attempt different payload with same key (→ 409)

**Idempotency testing:** Demonstrates retry safety and duplicate prevention

### 🔄 Reconciliation
Match proposals and confirmations:
- **Run Reconciliation** → Execute scoring algorithm, get top-N matches
- **Get AI Explanation** → Fetch Gemini-powered explanation (or heuristic fallback)
- **Confirm Match** → Mark match as confirmed, cascade status updates

### 📡 GraphQL Queries
GraphQL operations for alternative query interface:
- Get Tenant, List Invoices, Create Tenant, List Transactions

**Endpoint:** `POST /graphql` (excluded from OpenAPI schema per design)

### ❤️ System Health
System status:
- **Health Check** → DB connectivity verification
- **API Root Info** → Documentation links

---

## Workflows (Organized Test Scenarios)

### ✅ Workflow 1: Complete Reconciliation Flow
**End-to-end scenario:** Seed → Reconcile → Explain → Confirm

Steps:
1. **Seed Test Data** - Create demo fixtures
2. **Get Tenant ID** - Extract from seed status
3. **Run Reconciliation** - Find match candidates (captures first match_id)
4. **Get AI Explanation** - View match reasoning
5. **Confirm Match** - Finalize reconciliation

**Expected outcomes:**
- ✓ Matches found with scores ≥ 50
- ✓ AI explanation returned (or heuristic fallback)
- ✓ Match status changes to "confirmed"

---

### 🔐 Workflow 2: Idempotency Testing
**Idempotency guarantee verification**

Steps:
1. **Setup: Seed Data** - Fresh dataset
2. **First Import with Key** - Unique idempotency key (→ 201 Created)
3. **Retry Same Key** - Identical payload (→ 200 OK, cached response)
4. **Conflict Test** - Same key, different payload (→ 409 Conflict)

**Expected test results:**
- ✓ First request: 201 (new record created)
- ✓ Retry: 200 (returns cached response, no duplicate)
- ✓ Conflict: 409 (prevents duplicate with different data)

---

### 🔄 Workflow 3: Seed Lifecycle
**Seed data management and cleanup**

Steps:
1. **Seed Fresh Data** - Insert demo fixtures
2. **Inspect Before Cleanup** - Verify counts > 0
3. **Cleanup** - Delete all data
4. **Inspect After Cleanup** - Verify counts = 0
5. **Reseed** - Restore fixtures
6. **Final Status** - Confirm counts restored

**Expected state transitions:**
- After seed: Invoices, Transactions > 0
- After cleanup: All counts = 0
- After reseed: Counts restored

---

## Environment Variables

**Auto-populated during test execution:**

| Variable | Initial Value | Populated By | Used By |
|----------|---------------|--------------|---------|
| `base_url` | `http://localhost:8000` | Manual | All requests |
| `tenant_id` | `1` | Seed status, List Tenants | Tenant-scoped requests |
| `invoice_id` | `1` | List Invoices, Create Invoice | Invoice endpoints |
| `transaction_id` | `1` | List Transactions | Transaction endpoints |
| `match_id` | `1` | Reconciliation response | Match explanation, Confirm |
| `idempotency_key` | (empty) | Pre-request script | Bank transaction import |
| `test_idempotency_key` | (empty) | Idempotency workflow | Idempotency tests |

**Manual setup required:**
1. After seeding, update `{{tenant_id}}` from seed response (usually 1)
2. Update `{{invoice_id}}` after creating/listing invoices
3. Workflows auto-capture IDs via test scripts

---

## Test Scripts (Assertions)

Many requests include **Test** tabs with automated assertions:

### Idempotency Workflow
```javascript
// First import expects 201
pm.test('First import returns 201', function() {
  pm.response.to.have.status(201);
});

// Retry expects 200
pm.test('Retry returns 200 cached', function() {
  pm.response.to.have.status(200);
});

// Conflict expects 409
pm.test('Conflicting payload returns 409', function() {
  pm.response.to.have.status(409);
});
```

### Reconciliation Workflow
```javascript
// Capture match_id for later requests
const body = pm.response.json();
if (body.matches && body.matches.length > 0) {
  pm.environment.set('match_id', body.matches[0].id);
}
```

### Seed Lifecycle
```javascript
// Verify data present after seed
pm.test('Has data after seed', function() {
  pm.expect(body.total_invoices).to.be.greaterThan(0);
  pm.expect(body.total_transactions).to.be.greaterThan(0);
});

// Verify data deleted
pm.test('Data cleaned up', function() {
  pm.expect(body.total_invoices).to.equal(0);
});
```

---

## Pre-Request Scripts

Used to generate dynamic values before sending:

### Idempotency Key Generation
```javascript
const idempotencyKey = pm.environment.get('idempotency_key') || 'e2e-test-' + Date.now();
pm.environment.set('idempotency_key', idempotencyKey);
```

### Dynamic Timestamps
```javascript
// In request body: 
"invoice_date": "2026-01-{{$randomInt(1, 28)}}"
```

### Sample Transaction Generation
```javascript
const transactions = [
  {
    "posting_date": "2026-01-20",
    "description": "Payment E2E Test {{$timestamp}}",
    "amount": 1250.50,
    "transaction_type": "credit",
    "reference": "TXN-{{$randomInt(10000, 99999)}}"
  }
];
pm.environment.set('import_transactions', JSON.stringify(transactions));
```

---

## Common Testing Scenarios

### Scenario 1: Test Reconciliation with Fresh Seed
1. Go to **Seed Lifecycle Management** → Run all 4 requests in order
2. Go to **Reconciliation** → **Run Reconciliation** (uses seed data)
3. Copy `match_id` from response
4. **Get AI Explanation** (paste match_id in URL)
5. **Confirm Match** (paste match_id in URL)

### Scenario 2: Verify Idempotency Behavior
1. Go to **E2E Test Workflows** → **Idempotency Testing** (Run as collection)
2. Monitor test script results (3 assertions should pass)
3. Verify counts don't increase on retry

### Scenario 3: Full API Coverage
1. **Seed Data** (ensures consistent dataset)
2. **Tenants** → List, Get, Create, Update, Delete, Reactivate
3. **Invoices** → List, Get, Create, Update, Delete
4. **Bank Transactions** → Import, List, Get
5. **Reconciliation** → Reconcile, Explain, Confirm
6. **GraphQL Queries** → Run sample queries
7. **Cleanup** (optional, resets DB)

---

## Troubleshooting

### Issue: "Base URL not found"
**Solution:** Ensure `base_url` environment variable is set to `http://localhost:8000`

### Issue: Requests return 404
**Possible causes:**
- Server not running (check `poetry run uvicorn ...`)
- Wrong environment selected (top-right dropdown)
- Typo in path or variable placeholder

**Solution:** 
- Verify server is running on `:8000`
- Check environment is "RMS API - Local Development"
- Verify placeholders like `{{tenant_id}}` resolve correctly

### Issue: Seed endpoints return 403 Forbidden
**Reason:** `ENABLE_SEED_ENDPOINTS=true` not set in `.env`

**Solution:** 
```bash
# In .env
ENABLE_SEED_ENDPOINTS=true
```

### Issue: AI explanation returns 503
**Reason:** Gemini API key missing or invalid

**Solution:**
- Set `GEMINI_API_KEY` in `.env` (get from [Google AI Studio](https://aistudio.google.com/apikey))
- If not set, endpoint returns heuristic-based fallback (200 OK)

### Issue: Idempotency test shows 201 on retry (not 200)
**Possible causes:**
- Different payload sent (workflow auto-generates unique transactions)
- Idempotency key not persisting across requests

**Solution:** Manually copy `Idempotency-Key` header value from first response and paste into retry request

---

## Advanced Usage

### Run Collection as Test Suite
1. Click **...** (three dots) next to collection name
2. Select **Run collection**
3. All requests execute sequentially with test assertions
4. View summary at end (pass/fail counts)

### Export Results
1. After running collection, click **Export Results** button
2. Save as JSON for CI/CD integration or reporting

### Create Custom Folder
1. Right-click on collection → **Add Folder**
2. Name it (e.g., "Custom Tests")
3. Drag requests into folder
4. Run folder independently with **Run collection**

### Sync to Team
1. Click Postman logo (top-left) → **Workspace**
2. Create new workspace or join existing
3. Upload collection to workspace (auto-syncs)
4. Team members can import from workspace

---

## API Reference Quick Links

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **OpenAPI Schema:** [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)
- **GraphQL Introspection:** [http://localhost:8000/graphql](http://localhost:8000/graphql)
- **Health Check:** [http://localhost:8000/health](http://localhost:8000/health)

---

## Version History

- **v1.0** (2026-01-20) - Initial collection with 40+ requests, 3 workflows, idempotency testing, GraphQL operations

---

For questions or issues, refer to the project's main [README.md](../README.md) or [API documentation](../docs/Architecture.md).
