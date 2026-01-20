# Using the AI Explanation Endpoint

## Quick Start

Get an explanation for why a match was proposed:

```bash
curl -X GET "http://localhost:8000/api/v1/tenants/1/matches/5/explain"
```

## Response Format

The endpoint returns a JSON object with both AI and heuristic explanations:

```json
{
  "ai_explanation": "The invoice of $1,500 and the bank transaction of $1,500 match well. Both occurred within 2 days of each other (January 15 vs January 16), and the amounts are identical. This is a strong match.",
  "ai_confidence": 95,
  "heuristic_reason": "Amount matches exactly, date within 2 days",
  "heuristic_score": 92,
  "source": "ai",
  "ai_error_message": null
}
```

## Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `ai_explanation` | string or null | Human-readable explanation from the AI (Claude/Gemini) |
| `ai_confidence` | int (0-100) or null | Confidence score for the AI explanation |
| `heuristic_reason` | string | Rule-based explanation from scoring algorithm |
| `heuristic_score` | int (0-100) | Score from heuristic matching logic |
| `source` | string | Source of explanation: "ai", "heuristic", or "fallback" |
| `ai_error_message` | string or null | Error message if AI service failed |

## Source Types

### "ai"
- AI service is enabled and returned a valid explanation
- Both `ai_explanation` and `ai_confidence` are populated
- Most detailed and nuanced explanation

### "heuristic"
- AI is disabled or was not used
- Only `heuristic_reason` and `heuristic_score` are populated
- Based on rule-based matching logic

### "fallback"
- AI service failed (timeout, API error, etc.)
- System fell back to heuristic explanation
- `ai_error_message` contains the error details

## Common Use Cases

### Get explanation after reconciliation
```python
import requests

# After running reconciliation, get candidates
response = requests.get("http://localhost:8000/api/v1/tenants/1/reconcile")
candidates = response.json()["candidates"]

# For each candidate, get detailed explanation
for candidate in candidates:
    match_id = candidate["id"]
    explanation = requests.get(
        f"http://localhost:8000/api/v1/tenants/1/matches/{match_id}/explain"
    ).json()
    
    print(f"Match {match_id}:")
    print(f"  AI Says: {explanation['ai_explanation']}")
    print(f"  Score: {explanation['heuristic_score']}")
    print(f"  Confidence: {explanation['ai_confidence']}")
```

### Build a UI with fallback explanations
```html
<div class="match-card">
  <h3>Match ID: {{ match.id }}</h3>
  
  <!-- Show AI explanation if available -->
  <div v-if="explanation.source === 'ai'" class="ai-explanation">
    <strong>AI Analysis ({{ explanation.ai_confidence }}% confident):</strong>
    <p>{{ explanation.ai_explanation }}</p>
  </div>
  
  <!-- Show heuristic if AI unavailable -->
  <div v-else class="heuristic-explanation">
    <strong>Automatic Analysis:</strong>
    <p>{{ explanation.heuristic_reason }}</p>
    <p>Score: {{ explanation.heuristic_score }}/100</p>
  </div>
  
  <!-- Show AI error if it occurred -->
  <div v-if="explanation.ai_error_message" class="error-info">
    <small>Note: AI service unavailable ({{ explanation.ai_error_message }})</small>
  </div>
</div>
```

## Error Responses

### 404 - Match Not Found
```json
{
  "detail": "Match 999 not found"
}
```

### 404 - Invoice Not Found
```json
{
  "detail": "Invoice 123 not found"
}
```

### 404 - Transaction Not Found
```json
{
  "detail": "Transaction 456 not found"
}
```

## Configuration

To control AI behavior, set these environment variables:

```bash
# Enable/disable AI explanations
AI_ENABLED=true

# Customize AI behavior
AI_TEMPERATURE=0.7              # 0 = deterministic, 1 = creative
AI_MAX_TOKENS=500               # Max response length

# Custom system prompt
AI_SYSTEM_PROMPT="You are a financial reconciliation expert..."
```

## Performance Considerations

### AI Service Timing
- First call: ~2-5 seconds (API call + processing)
- Retries: Up to 3 attempts with exponential backoff
- Timeout: 10 seconds max per attempt

### Optimization Tips
1. **Batch requests**: Get multiple explanations in parallel
2. **Cache results**: Store explanations if same match is queried multiple times
3. **Disable AI**: If latency is critical, set `AI_ENABLED=false` to use heuristics only
4. **Monitor failures**: Track `ai_error_message` to identify API issues

## Troubleshooting

### AI returning null explanation
**Check**:
- `AI_ENABLED=true` in environment
- `GEMINI_API_KEY` is set and valid
- Network connectivity to Google AI APIs

### Very low confidence scores
**Possible causes**:
- Unusual match (large amount difference, far apart dates)
- AI uncertainty about match quality
- Consider manual review for matches with confidence < 70%

### API errors in ai_error_message
**Common errors**:
- `"API timeout"` - Google AI API slow, consider disabling AI or increasing timeout
- `"Invalid API key"` - Check `GEMINI_API_KEY` environment variable
- `"Rate limited"` - Too many requests, implement backoff strategy

## Testing

Run the test suite:

```bash
pytest tests/ai/test_ai_explanation.py -v

# Test specific scenario
pytest tests/ai/test_ai_explanation.py::TestExplainMatch::test_explain_match_with_ai_success -v

# Run with detailed output
pytest tests/ai/test_ai_explanation.py -vv -s
```
