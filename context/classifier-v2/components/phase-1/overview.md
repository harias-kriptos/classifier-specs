# Phase 1: Scan & File Discovery — Overview Spec

> **Status:** POC validated (April 2026). Pending production hardening.
> **Source of truth:** [Confluence v3](https://kriptosteam.atlassian.net/wiki/spaces/AC/pages/2965078017/Flujo+de+proceso+v3)
> **Infra:** [/infra/phase1-scan-file-discovery/](../../../../infra/phase1-scan-file-discovery/)

---

## Scope

Phase 1 covers everything from the agent scanning the filesystem to the backend producing a reduced tree of crown jewel matches. It ends when `s3_crown_jewels/{enterprise_id}/{station_id}/` has the output ready for Phase 2.

## Components

| # | Component | Type | Spec |
|---|---|---|---|
| 1 | [tree-url-generator](tree-url-generator.md) | Lambda (Python) | Generates pre-signed S3 PUT URL with signed metadata |
| 2 | [tree-uncompressor](tree-uncompressor.md) | Lambda (Python) | Stream decompresses .gz → .jsonl, propagates metadata |
| 3 | [emr-job-trigger](emr-job-trigger.md) | Lambda (Python) | Starts EMR Serverless job with dynamic S3 params |
| 4 | [joyas-priorizer](joyas-priorizer.md) | EMR Serverless (PySpark) | Keyword matching against file tree → crown jewel output |

## Data Flow

```
PC Agent                                Cloud Agent
    │                                       │
    │ POST /v2/tree/init                    │
    │ → tree-url-generator                  │
    │ → returns signed URL                  │
    │                                       │
    │ PUT signed URL (.jsonl.gz)            │ PUT direct (IAM, .jsonl)
    ▼                                       ▼
compressed_trees/                    decompressed_trees/
    │                                   ▲       │
    │ EventBridge                       │       │ EventBridge
    ▼                                   │       ▼
tree-uncompressor ──────────────────────┘   emr-job-trigger
                                                │
                                                ▼
                                        EMR Serverless
                                        (joyas-priorizer)
                                                │
                                         reads keywords/
                                        {enterprise_id}.json
                                                │
                                                ▼
                                        s3_crown_jewels/
                                        {ent}/{station}/
```

## S3 Buckets

| Bucket | Purpose | Writers | Readers |
|---|---|---|---|
| `compressed_trees` | Gzipped tree from PC Agent | PC Agent (via s3-uploader) | tree-uncompressor |
| `decompressed_trees` | Convergence point | tree-uncompressor, Cloud Agent | emr-job-trigger, joyas-priorizer |
| `keywords` | Enterprise keyword files + EMR scripts | Bedrock (other team), Terraform | joyas-priorizer |
| `crown_jewels` | Phase 1 output — matched documents | joyas-priorizer | Phase 2/3 downstream |

## S3 Object Metadata Contract

Every tree object (compressed and decompressed) carries these headers:

| Header | Type | Set by | Example |
|---|---|---|---|
| `x-amz-meta-enterprise-id` | UUID | tree-url-generator | `ent-001` |
| `x-amz-meta-station-id` | UUID | tree-url-generator | `station-001` |
| `x-amz-meta-total-lines` | number | tree-url-generator | `9823451` |
| `x-amz-meta-fingerprint` | hash | tree-url-generator | `abc123` |
| `x-amz-meta-uploaded-at` | ISO-8601 | tree-url-generator | `2026-04-16T10:00:00Z` |
| `x-amz-meta-agent-version` | semver | tree-url-generator | `3.0.1` |
| `x-amz-meta-tree-id` | UUID | tree-url-generator | `0ce84cb1-...` |

**tree-uncompressor** propagates ALL metadata to the decompressed object unchanged.

## JSON Formats

### Tree NDJSON (agent → S3)

One JSON object per line. No wrapping array. UTF-8 NFC encoding.

```jsonl
{"name":"Q1-Report","path":"/Users/foo/Finance/","size":245780,"extension":"pdf","modified_date":"2026-04-14T09:15:22Z"}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | yes | Filename without extension |
| `path` | string | yes | Directory path (UTF-8 NFC normalized) |
| `size` | number | yes | File size in bytes |
| `extension` | string | yes | File extension (without dot) |
| `modified_date` | string | yes | ISO-8601 UTC last modification date |

### Keywords JSON (Bedrock → S3)

One file per enterprise: `keywords/{enterprise_id}.json`

```json
{
  "enterprise_id": "ent-001",
  "version": "2026-04-16T10:00:00Z",
  "keywords": ["financial", "salary", "merger", "contract"]
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `enterprise_id` | string | yes | Must match the tree's enterprise |
| `version` | string | yes | ISO-8601 timestamp of generation |
| `keywords` | string[] | yes | 2K–5K keywords to match against `name` |

### Crown Jewels NDJSON (EMR → S3)

Same 5 fields as tree + `matched_keywords`:

```jsonl
{"name":"Q1-Report","path":"/Users/foo/Finance/","size":245780,"extension":"pdf","modified_date":"2026-04-14T09:15:22Z","matched_keywords":["financial"]}
```

## Cross-Cutting Concerns

### Logging Standard

All Lambdas MUST use structured JSON logging with these fields:

```json
{
  "level": "INFO|WARN|ERROR",
  "timestamp": "ISO-8601",
  "lambda": "tree-url-generator",
  "request_id": "Lambda request ID",
  "enterprise_id": "from request or S3 metadata",
  "station_id": "from request or S3 metadata",
  "tree_id": "if available",
  "message": "human-readable message",
  "error": "stack trace if ERROR level"
}
```

CloudWatch Log Groups: `/aws/lambda/{function-name}` with 30-day retention.

### Error Handling Strategy

| Error Type | Strategy | Alert |
|---|---|---|
| Invalid input (400) | Return error response to caller, log WARN | No |
| S3 access denied (403) | Log ERROR, fail Lambda, auto-retry (2x) | Yes — IAM misconfiguration |
| S3 object not found (404) | Log WARN, skip processing | No — expected race condition |
| Lambda timeout | Fail, auto-retry (2x), then DLQ | Yes — performance issue |
| EMR job failure | Log ERROR, no auto-retry | Yes — investigate manually |
| Throttling (429) | Automatic backoff by AWS SDK | No |

### Retry Policy

| Component | Max Retries | DLQ | DLQ Retention |
|---|---|---|---|
| tree-url-generator | N/A (synchronous API) | N/A | N/A |
| tree-uncompressor | 2 (EventBridge) | Yes: `tree-uncompressor-dlq` | 14 days |
| emr-job-trigger | 2 (EventBridge) | Yes: `emr-job-trigger-dlq` | 14 days |
| joyas-priorizer (EMR) | 0 (manual retry) | N/A | N/A |

### Monitoring & Alerting

| Metric | Source | Threshold | Action |
|---|---|---|---|
| tree-uncompressor errors | CloudWatch Lambda metrics | > 3 in 5 min | SNS alert |
| emr-job-trigger errors | CloudWatch Lambda metrics | > 3 in 5 min | SNS alert |
| EMR job FAILED state | EMR Serverless events | Any failure | SNS alert |
| DLQ message count > 0 | CloudWatch SQS metrics | > 0 | SNS alert |
| API Gateway 5xx | CloudWatch API GW metrics | > 5 in 5 min | SNS alert |
| Decompression latency | Custom metric in Lambda | > 120 sec | SNS alert |

### Security

| Concern | Mitigation |
|---|---|
| Pre-signed URL leakage | 1-hour expiration, single-use (PUT only), scoped to exact S3 key |
| S3 public access | All buckets have public access block enabled |
| Encryption at rest | AES-256 server-side encryption on all buckets |
| Encryption in transit | HTTPS enforced via API Gateway + S3 pre-signed URLs |
| IAM least privilege | Each Lambda has its own role with minimum required permissions |
| Agent authentication | API key on POST /v2/tree/init (TODO: implement in API Gateway) |
| Cross-enterprise access | EMR job reads `enterprise_id` from S3 metadata — cannot access other enterprises' keywords |

## Open Questions (from POC)

- **Matching semantics:** Substring literal matching misses hyphenated names (e.g., `"board minutes"` doesn't match `"Board-Minutes-March"`). Normalization strategy TBD.
- **API authentication:** API Gateway currently has no auth. Need to add API key or Cognito before production.
- **DLQs not provisioned:** Terraform doesn't yet create the DLQ SQS queues listed above.
- **CloudWatch alarms not provisioned:** Monitoring section is design only — needs Terraform implementation.
- **EMR log destination:** Job logs go to EMR default. Should configure S3 log bucket for persistence.
- **Idempotency:** If the same tree is uploaded twice, the full pipeline runs twice. Need dedup strategy (by `tree_id` or `fingerprint + station_id`).
- **Cloud Agent IAM role:** Not provisioned in Terraform — assumed to exist.
