# tree-uncompressor

**Type:** Lambda (Python 3.12)
**Trigger:** EventBridge — S3 PutObject on `compressed_trees/`
**Purpose:** Stream decompresses a `.jsonl.gz` file and writes a `.jsonl` to `decompressed_trees/`, propagating all `x-amz-meta-*` headers from the source object.

---

## Input

**Source:** EventBridge event (S3 Object Created)

```json
{
  "source": "aws.s3",
  "detail-type": "Object Created",
  "detail": {
    "bucket": { "name": "kriptos-poc-harias-compressed-trees" },
    "object": { "key": "ent-001/station-001/tree-id.jsonl.gz" }
  }
}
```

**Event filter:** only `.jsonl.gz` suffix (configured in EventBridge rule).

## Output

**S3 object in `decompressed_trees/`:**

- Key: same as source but without `.gz` suffix
  - Input: `ent-001/station-001/tree-id.jsonl.gz`
  - Output: `ent-001/station-001/tree-id.jsonl`
- Content-Type: `application/x-ndjson`
- Metadata: ALL `x-amz-meta-*` headers from source propagated unchanged

## Processing Logic

```
1. Extract bucket + key from EventBridge event
2. HEAD source object → read x-amz-meta-* headers
3. Compute destination key (strip .gz)
4. Start S3 multipart upload on destination bucket (with metadata)
5. Stream: GET source → gzip decompress → upload parts (8MB chunks)
6. Complete multipart upload
7. Log success with enterprise_id, station_id, tree_id, part count
```

## Validations

### Input Validation

1. **Event structure:** `detail.bucket.name` and `detail.object.key` must be present.
2. **Key suffix:** must end with `.jsonl.gz`. If not, log WARN and skip (should not happen due to EventBridge filter, but defensive).
3. **Source object exists:** `HeadObject` may return 404 if object was deleted between event and Lambda execution. Log WARN and exit gracefully.

### Data Integrity Validation (SHOULD implement)

4. **Gzip integrity:** if `gzip.GzipFile` raises `BadGzipFile` or `EOFError`, the upload was truncated. Abort multipart upload, log ERROR.
5. **Line count validation:** after decompression, count lines and compare to `x-amz-meta-total-lines`. If mismatch > 1%, log WARN (the file may have been truncated or appended to).
6. **UTF-8 validation:** if a line fails to decode as UTF-8, log WARN with line number and continue (don't fail the entire job for one bad line).

## Error Handling

| Scenario | Action | Log Level | Retry |
|---|---|---|---|
| Event missing bucket/key | Log and exit | ERROR | No |
| Source object not found (404) | Log and exit gracefully | WARN | No |
| Source object access denied (403) | Fail Lambda, auto-retry | ERROR | Yes (2x) |
| Bad gzip file (corrupt) | Abort multipart, log error | ERROR | No — file is corrupt, retry won't help |
| Destination write fails | Abort multipart, fail Lambda | ERROR | Yes (2x) |
| Lambda timeout (300s) | Abort multipart (handled by except block) | ERROR | Yes (2x) |
| Multipart upload orphaned | S3 lifecycle rule cleans up after 7 days | — | — |

### DLQ

After 2 failed retries, EventBridge sends the event to `tree-uncompressor-dlq` (SQS). Messages retained for 14 days for manual investigation.

**DLQ alert:** CloudWatch alarm on `ApproximateNumberOfMessagesVisible > 0` → SNS notification.

## Logging

### Required log events

| Event | Level | Fields |
|---|---|---|
| Processing started | INFO | enterprise_id, station_id, tree_id, source_key, source_size |
| Metadata read | DEBUG | all x-amz-meta-* headers |
| Multipart upload started | INFO | destination_key, upload_id |
| Part uploaded | DEBUG | part_number, part_size |
| Decompression complete | INFO | enterprise_id, station_id, tree_id, destination_key, total_parts, duration_ms |
| Bad gzip file | ERROR | source_key, exception |
| Multipart aborted | ERROR | destination_key, upload_id, exception |
| Source not found | WARN | source_key |

### Log format

```json
{
  "level": "INFO",
  "timestamp": "2026-04-16T10:00:05Z",
  "lambda": "tree-uncompressor",
  "request_id": "abc-123",
  "enterprise_id": "ent-001",
  "station_id": "station-001",
  "tree_id": "0ce84cb1-...",
  "message": "Decompression complete",
  "source_key": "ent-001/station-001/0ce84cb1.jsonl.gz",
  "destination_key": "ent-001/station-001/0ce84cb1.jsonl",
  "total_parts": 3,
  "duration_ms": 12500
}
```

## Configuration

| Env Variable | Value | Description |
|---|---|---|
| `DESTINATION_BUCKET` | `kriptos-{env}-decompressed-trees` | Target bucket for decompressed files |

## Performance

| Metric | Expected (300 MB .gz → ~1.5 GB .jsonl) |
|---|---|
| Duration | 30–120 sec |
| Memory | 1024 MB (actual ~200–500 MB due to streaming) |
| Timeout | 300 sec |
| Chunk size | 8 MB per multipart part |
| Parts for 1.5 GB file | ~190 parts |

### Scaling Considerations

- Each S3 PutObject triggers one Lambda invocation → naturally parallel across stations.
- 100 stations uploading simultaneously → 100 concurrent Lambdas (within default account limit of 1000).
- If decompression of a very large file (> 5 GB uncompressed) approaches the 300s timeout, increase Lambda timeout to 900s or consider ECS Fargate.

## Security Considerations

1. **Read-only on source bucket:** Lambda role has `s3:GetObject` + `s3:HeadObject` only — cannot modify or delete source files.
2. **Write-only on destination bucket:** Lambda role has `s3:PutObject` only (plus multipart operations).
3. **No cross-enterprise data access:** Lambda processes whatever S3 event it receives. Isolation is enforced by S3 key pattern (`{enterprise_id}/...`) and EventBridge rule scope.
4. **Abort on failure:** if decompression fails mid-stream, the multipart upload is aborted — no partial/corrupt files left in the destination bucket.

## Dependencies

| Service | Operation | Why |
|---|---|---|
| S3 (compressed_trees) | `HeadObject`, `GetObject` | Read source + metadata |
| S3 (decompressed_trees) | `CreateMultipartUpload`, `UploadPart`, `CompleteMultipartUpload`, `AbortMultipartUpload` | Write decompressed output |
| CloudWatch Logs | Write | Logging |

## Edge Cases

| Case | Behavior |
|---|---|
| Same file uploaded twice | Processed twice — two decompressed files with different tree_ids (by design, tree_id is unique) |
| Zero-byte .gz file | `gzip.GzipFile` raises error → abort, log ERROR |
| .gz file that decompresses to 0 lines | Produces empty .jsonl file — downstream EMR job handles gracefully (0 matches) |
| File deleted from compressed_trees between event and Lambda | `HeadObject` returns 404 → log WARN, exit gracefully |
| Cloud Agent uploads directly to decompressed_trees | This Lambda is NOT triggered (different bucket). Cloud Agent path bypasses decompression entirely. |

## Idempotency

**Not idempotent.** If the same event fires twice (EventBridge at-least-once delivery), the Lambda decompresses and writes twice. The second write overwrites the first (same destination key). This is safe because the content is identical.

If true idempotency is needed: check if destination key already exists (`HeadObject`) before starting decompression. Skip if exists and metadata matches.
