# tree-url-generator

**Type:** Lambda (Python 3.12)
**Trigger:** API Gateway HTTP — `POST /v2/tree/init`
**Purpose:** Generates a pre-signed S3 PUT URL with signed `x-amz-meta-*` headers. The agent uses this URL to upload its file tree directly to S3, bypassing the API Gateway 10MB limit.

---

## Input

**Source:** API Gateway HTTP POST

**Request body:**

```json
{
  "enterprise_id": "ent-001",
  "station_id": "station-001",
  "total_lines": 9823451,
  "fingerprint": "abc123",
  "agent_version": "3.0.1"
}
```

| Field | Type | Required | Validation |
|---|---|---|---|
| `enterprise_id` | string | yes | Non-empty, max 128 chars, UUID format recommended |
| `station_id` | string | yes | Non-empty, max 128 chars, UUID format recommended |
| `total_lines` | number | yes | > 0, integer |
| `fingerprint` | string | yes | Non-empty, max 256 chars |
| `agent_version` | string | yes | Non-empty, semver format recommended |

## Output

**Success (200):**

```json
{
  "tree_id": "0ce84cb1-0e1a-4b92-bf77-738b2f0a1b7f",
  "upload_url": "https://kriptos-poc-harias-compressed-trees.s3.amazonaws.com/ent-001/station-001/0ce84cb1...jsonl.gz?X-Amz-Algorithm=...",
  "headers": {
    "Content-Type": "application/gzip",
    "x-amz-meta-enterprise-id": "ent-001",
    "x-amz-meta-station-id": "station-001",
    "x-amz-meta-total-lines": "9823451",
    "x-amz-meta-fingerprint": "abc123",
    "x-amz-meta-uploaded-at": "2026-04-16T10:00:00Z",
    "x-amz-meta-agent-version": "3.0.1",
    "x-amz-meta-tree-id": "0ce84cb1-0e1a-4b92-bf77-738b2f0a1b7f"
  },
  "expires_in": 3600
}
```

The agent MUST send the exact `headers` in the PUT request. If any header differs from what was signed, S3 returns `403 SignatureDoesNotMatch`.

**Errors:**

| Status | Condition | Body |
|---|---|---|
| 400 | Invalid JSON body | `{"error": "Invalid JSON body"}` |
| 400 | Missing required fields | `{"error": "Missing fields: enterprise_id, station_id"}` |
| 400 | Invalid field values | `{"error": "total_lines must be a positive integer"}` |
| 500 | S3 pre-sign failure | `{"error": "Failed to generate upload URL"}` |

## S3 Key Pattern

```
{enterprise_id}/{station_id}/{tree_id}.jsonl.gz
```

Example: `ent-001/station-001/0ce84cb1-0e1a-4b92-bf77-738b2f0a1b7f.jsonl.gz`

## Validations

### Input Validation (MUST implement)

1. **JSON parse:** reject if body is not valid JSON.
2. **Required fields:** all 5 fields must be present.
3. **Type check:** `total_lines` must be a positive integer.
4. **Length limits:** no field exceeds 256 characters (prevents abuse of S3 metadata 2KB limit).
5. **Character sanitization:** `enterprise_id` and `station_id` must match `^[a-zA-Z0-9\-_]+$` — prevents S3 key injection (e.g., `../../` in enterprise_id).

### Business Validation (SHOULD implement)

6. **Enterprise exists:** validate `enterprise_id` against KEM (optional in POC, required in production).
7. **Station belongs to enterprise:** validate `station_id` is registered for this enterprise in KEM.
8. **Rate limit:** max N uploads per station per hour (prevents abuse of pre-signed URLs).

## Error Handling

| Scenario | Action | Log Level |
|---|---|---|
| Invalid JSON body | Return 400, log request | WARN |
| Missing required fields | Return 400, log field names | WARN |
| S3 key injection attempt (`../` in IDs) | Return 400, log full request | WARN |
| S3 `generate_presigned_url` fails | Return 500, log exception | ERROR |
| Lambda timeout (unlikely at 30s) | Auto-retry by API GW | ERROR |

## Logging

### Required log events

| Event | Level | Fields |
|---|---|---|
| Request received | INFO | enterprise_id, station_id, total_lines |
| Validation failed | WARN | enterprise_id, station_id, error_reason |
| Pre-signed URL generated | INFO | enterprise_id, station_id, tree_id, s3_key, expires_in |
| S3 error | ERROR | enterprise_id, station_id, exception |

### Log format

```json
{
  "level": "INFO",
  "timestamp": "2026-04-16T10:00:00Z",
  "lambda": "tree-url-generator",
  "request_id": "abc-123",
  "enterprise_id": "ent-001",
  "station_id": "station-001",
  "tree_id": "0ce84cb1-...",
  "message": "Pre-signed URL generated",
  "s3_key": "ent-001/station-001/0ce84cb1.jsonl.gz",
  "expires_in": 3600
}
```

## Configuration

| Env Variable | Value | Description |
|---|---|---|
| `BUCKET_NAME` | `kriptos-{env}-compressed-trees` | Target S3 bucket |
| `PRESIGNED_URL_EXPIRY` | `3600` | URL expiration in seconds |

## Performance

| Metric | Expected |
|---|---|
| Cold start | ~200ms |
| Warm execution | ~50ms |
| Memory | 256 MB (< 50 MB actual usage) |
| Timeout | 30 sec (actual < 1 sec) |

## Security Considerations

1. **Pre-signed URL is single-purpose:** signed for PUT to a specific S3 key with specific metadata. Cannot be reused for other keys or operations.
2. **1-hour expiration:** limits exposure window if URL is leaked.
3. **`uploaded_at` set by Lambda, not agent:** prevents timestamp manipulation.
4. **`tree_id` generated server-side (UUID v4):** prevents collision and predictability.
5. **TODO (production):** Add API key authentication on the API Gateway route. Currently open.
6. **TODO (production):** Add WAF on API Gateway for rate limiting and IP filtering.

## Dependencies

| Service | Operation | Why |
|---|---|---|
| S3 | `generate_presigned_url (put_object)` | Generate the signed upload URL |
| CloudWatch Logs | Write | Logging |

## Idempotency

Not idempotent by design. Each call generates a new `tree_id` and a new pre-signed URL. If the agent calls twice, it gets two different URLs. Only one should be used.

If the agent needs to retry (e.g., network error before receiving the response), it calls again and gets a fresh URL. The unused URL expires harmlessly.
