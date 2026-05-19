# emr-job-trigger

**Type:** Lambda (Python 3.12)
**Trigger:** EventBridge — S3 PutObject on `decompressed_trees/`
**Purpose:** Intermediary between S3 events and EMR Serverless. Extracts `enterprise_id` and `station_id` from the S3 key, and starts an EMR Serverless Spark job with the correct parameters.

---

## Why This Lambda Exists

EventBridge cannot pass dynamic parameters (like the S3 key that triggered the event) directly to EMR Serverless `StartJobRun`. This Lambda bridges the gap: it receives the event, extracts the key, and starts the job with the right arguments.

## Input

**Source:** EventBridge event (S3 Object Created)

```json
{
  "source": "aws.s3",
  "detail-type": "Object Created",
  "detail": {
    "bucket": { "name": "kriptos-poc-harias-decompressed-trees" },
    "object": { "key": "ent-001/station-001/tree-id.jsonl" }
  }
}
```

**Event filter:** only `.jsonl` suffix (not `.jsonl.gz`).

## Output

**EMR Serverless job started.** Returns `jobRunId` for tracking.

```json
{
  "jobRunId": "00g4vqdmqeamuo0b"
}
```

## Processing Logic

```
1. Extract bucket + key from EventBridge event
2. Parse enterprise_id and station_id from the S3 key pattern
   Expected: {enterprise_id}/{station_id}/{tree_id}.jsonl
3. Call emr-serverless:StartJobRun with:
   - entryPoint: s3://{keywords_bucket}/emr/joyas-priorizer/job.py
   - entryPointArguments: [bucket, key]
   - sparkSubmitParameters: dynamic allocation off, 1g memory, 1 core
4. Log jobRunId
```

## Validations

### Input Validation

1. **Event structure:** `detail.bucket.name` and `detail.object.key` must be present.
2. **Key format:** must match pattern `{enterprise_id}/{station_id}/{tree_id}.jsonl`. If not, log WARN and skip.
3. **Key suffix:** must end with `.jsonl`. Reject `.jsonl.gz` (that belongs to `tree-uncompressor`).

### Business Validation (SHOULD implement)

4. **EMR application state:** before starting the job, optionally check if the EMR application is in `STARTED` or `CREATED` state. If `STOPPED`, the auto-start feature will handle it, but logging the state is useful for debugging.
5. **Duplicate job check:** optionally check if a job for the same `tree_id` is already running (prevents duplicate processing from EventBridge at-least-once delivery).

## Error Handling

| Scenario | Action | Log Level | Retry |
|---|---|---|---|
| Event missing bucket/key | Log and exit | ERROR | No |
| Invalid key format | Log and skip | WARN | No |
| EMR StartJobRun fails (ValidationException) | Log error, fail Lambda | ERROR | Yes (2x) |
| EMR application capacity exceeded | Log error, fail Lambda | ERROR | Yes (2x) — may succeed after current job finishes |
| Lambda timeout (60s) | Fail, auto-retry | ERROR | Yes (2x) |
| IAM permission error on StartJobRun | Log error, fail Lambda | ERROR | No — config issue |
| IAM PassRole error | Log error, fail Lambda | ERROR | No — config issue |

### DLQ

After 2 failed retries: `emr-job-trigger-dlq` (SQS). Retained 14 days.

## Logging

### Required log events

| Event | Level | Fields |
|---|---|---|
| Event received | INFO | bucket, key |
| Key parsed | INFO | enterprise_id, station_id, tree_id |
| EMR job started | INFO | jobRunId, enterprise_id, station_id |
| EMR StartJobRun failed | ERROR | exception, bucket, key |
| Invalid key format | WARN | key, expected_pattern |

### Log format

```json
{
  "level": "INFO",
  "timestamp": "2026-04-16T10:00:10Z",
  "lambda": "emr-job-trigger",
  "request_id": "abc-123",
  "enterprise_id": "ent-001",
  "station_id": "station-001",
  "tree_id": "0ce84cb1-...",
  "message": "EMR job started",
  "job_run_id": "00g4vqdmqeamuo0b"
}
```

## Configuration

| Env Variable | Value | Description |
|---|---|---|
| `EMR_APPLICATION_ID` | EMR Serverless app ID | Target application |
| `EMR_EXECUTION_ROLE_ARN` | IAM role ARN | Role that EMR job assumes |
| `JOB_SCRIPT_S3_PATH` | `s3://{keywords_bucket}/emr/joyas-priorizer/job.py` | Spark entry point |
| `KEYWORDS_BUCKET` | `kriptos-{env}-keywords` | Passed to Spark job via config |
| `CROWN_JEWELS_BUCKET` | `kriptos-{env}-crown-jewels` | Passed to Spark job via config |

## Spark Submit Parameters

```
--conf spark.dynamicAllocation.enabled=false
--conf spark.executor.instances=1
--conf spark.executor.memory=1g
--conf spark.executor.cores=1
--conf spark.driver.memory=1g
--conf spark.driver.cores=1
--conf spark.emr-serverless.driverEnv.KEYWORDS_BUCKET={keywords_bucket}
--conf spark.emr-serverless.driverEnv.CROWN_JEWELS_BUCKET={crown_jewels_bucket}
```

Dynamic allocation is OFF to keep EMR Serverless resource usage minimal and predictable.

## Performance

| Metric | Expected |
|---|---|
| Cold start | ~200ms |
| Warm execution | ~500ms (StartJobRun API call) |
| Memory | 256 MB |
| Timeout | 60 sec |

## Security Considerations

1. **IAM: StartJobRun only** — Lambda can only start jobs, not modify or delete the EMR application.
2. **IAM: PassRole** — Lambda needs `iam:PassRole` for the EMR execution role. Scoped to exactly that role ARN.
3. **No S3 access:** this Lambda does not read or write to S3. It only starts the EMR job — the EMR execution role handles S3 access.

## Dependencies

| Service | Operation | Why |
|---|---|---|
| EMR Serverless | `StartJobRun` | Start the Spark job |
| IAM | `PassRole` | Pass execution role to EMR |
| CloudWatch Logs | Write | Logging |

## Edge Cases

| Case | Behavior |
|---|---|
| Same event fires twice (at-least-once) | Two EMR jobs start for the same tree. Both produce the same output (overwrite). Harmless but wasteful. |
| EMR application in STOPPED state | Auto-start kicks in (~2-3 min). Job queues until app is ready. |
| EMR application at max capacity | `StartJobRun` succeeds but job stays in PENDING/SCHEDULED until capacity frees. |
| Keywords file doesn't exist for this enterprise | EMR job runs but finds no keywords → produces empty output. |
| Very long S3 key (> 1KB) | Lambda handles it — no truncation risk. |
