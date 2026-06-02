# Troubleshooting — Common Issues & Solutions

---

## 1. CYCLE stuck in `scanning` for > 1 hour

### Symptoms
```
CYCLE status: scanning
CYCLE created_at: 2h ago
All STATIONs missing (scan_status never reported)
```

### Root Causes

**A) Agent never uploaded tree**
- Check S3 `compressed_trees/` — no objects for this cycle?
- Check Agent logs: did `tree-url-generator` return presigned URL successfully?

**B) tree-uncompressor crashed**
- Check CloudWatch logs for `tree-uncompressor` Lambda
- Check if `.jsonl.gz` file is valid (not truncated)
- Look for decompression errors (bad gzip header)

**C) EMR job failed**
- Check CloudWatch for `emr-job-trigger` logs
- SSH to EMR cluster (if still alive) and check `/var/log/emr/` for joyas-priorizer errors
- Check EMR Spark job UI (if running)

**D) crown-candidates-indexer crashed**
- Check CloudWatch for `crown-candidates-indexer`
- Look for OpenSearch connectivity errors (VPC misconfiguration?)
- Check if OpenSearch cluster is up (`aws opensearch describe-domain`)

### Resolution

1. **Check Agent:**
   ```bash
   # Did Agent get presigned URL?
   aws logs tail /aws/lambda/tree-url-generator --follow
   # Look for: "presigned_url": "s3://..." or error
   ```

2. **Check S3:**
   ```bash
   aws s3 ls s3://compressed_trees/ent-001/{cycle_id}/ --recursive
   # Should see: {cycle_id}/tree.jsonl.gz
   ```

3. **Check Lambda chain:**
   ```bash
   # Check tree-uncompressor
   aws logs tail /aws/lambda/tree-uncompressor --follow
   # Check emr-job-trigger
   aws logs tail /aws/lambda/emr-job-trigger --follow
   # Check crown-candidates-indexer
   aws logs tail /aws/lambda/crown-candidates-indexer --follow
   ```

4. **If EMR stuck:**
   - Terminate the job: `aws emr terminate-job-flow --cluster-id j-xxxxx`
   - Restart the cycle (manual trigger or wait for reaper Lambda)

5. **If OpenSearch down:**
   - Check cluster status: `aws opensearch describe-domain --domain-name classifier`
   - If red, contact DevOps

---

## 2. CYCLE stuck in `stations_complete` for > 30 min

### Symptoms
```
CYCLE status: stations_complete
All STATIONs have scan_status: complete
But CYCLE has not transitioned to confirmed
Client UI shows "Waiting for system..."
```

### Root Causes

**A) crown-validation-handler is down/crashing**
- Check CloudWatch for errors

**B) Client never submitted confirmation**
- Check Client UI logs: did user click "Confirm"?
- Check DDB for OpenSearch query results (approved_count, rejected_count)

**C) crown-validation-confirm crash**
- Check CloudWatch for `crown-validation-confirm` errors
- Check S3 `validated_crown_jewels/` — is manifest there?

### Resolution

1. **Check Client UI:**
   ```bash
   # In browser dev tools:
   # Did /v2/validation/confirm POST succeed?
   # Look for network tab, status 200?
   ```

2. **Check DDB OpenSearch counts:**
   ```bash
   # Did approval/rejection counts get written?
   aws dynamodb get-item \
     --table-name classifier-cycles-state \
     --key '{"PK": {"S": "ent-001"}, "SK": {"S": "CYCLE#cycle-id"}}' \
     | jq '.Item | {status, approved_count, rejected_count}'
   # Should see non-null approved_count
   ```

3. **Manual trigger:**
   - If counts are there, manually invoke `crown-validation-confirm`:
   ```bash
   aws lambda invoke \
     --function-name crown-validation-confirm \
     --payload '{"cycle_id": "...", "enterprise_id": "ent-001"}' \
     /tmp/response.json
   ```

---

## 3. CYCLE stuck in `phase2_collecting` for > 2 hours

### Symptoms
```
CYCLE status: phase2_collecting
STATIONs have sampling_status: uploading or sample_collected
But samples never reach sample_anonymized status
OR gse-station-status never fires
```

### Root Causes

**A) Anonymizer is down or slow**
- Check if `gse-anonymized/` bucket has files
- Check Anonymizer team's deployment status

**B) gse-sample-reception-notifier crashed**
- Check CloudWatch for DDB Stream errors
- Check if S3 `gse-raw/` has objects (if not, Agent never uploaded)

**C) gse-sample-anonymizer-notifier crashed**
- Check CloudWatch for DDB Stream reading errors
- Check if Anonymizer output is being written to `gse-anonymized/`

**D) Barrier condition is unreachable**
- `samples_anonymized + samples_skipped` never reaches `samples_expected`
- Check gse-request-complete — did Agent call with correct skip counts?

### Resolution

1. **Check Agent uploads:**
   ```bash
   aws s3 ls s3://gse-raw/ent-001/{station}/ --recursive
   # Should see: {cycle_id}/{request_type}/sample_*.json
   ```

2. **Check Anonymizer output:**
   ```bash
   aws s3 ls s3://gse-anonymized/ent-001/{station}/ --recursive
   # Should see matching structure
   ```

3. **Check DDB STATION record:**
   ```bash
   aws dynamodb get-item \
     --table-name classifier-cycles-state \
     --key '{"PK": {"S": "ent-001"}, "SK": {"S": "STATION#station-id#cycle-id"}}' \
     | jq '.Item | {sampling_status, samples_expected, samples_received, samples_anonymized, samples_skipped}'
   # Verify: samples_anonymized + samples_skipped >= samples_expected ?
   ```

4. **Check gse-request-complete call:**
   ```bash
   # Did Agent call with correct counts?
   aws logs tail /aws/lambda/gse-request-complete --follow
   # Look for: "total_samples_uploaded": N, "samples_skipped": M
   # And verify N + M = samples_expected
   ```

5. **Manual barrier trigger:**
   - If counts are correct, manually invoke `gse-station-status`:
   ```bash
   aws lambda invoke \
     --function-name gse-station-status \
     --payload '{"station_id": "...", "cycle_id": "..."}' \
     /tmp/response.json
   ```

---

## 4. REQUEST stuck in `requested` state

### Symptoms
```
REQUEST status: requested (never transitions to sent)
Request created 30+ min ago
gse-request-complete never called
```

### Root Causes

**A) Agent crashed while collecting samples**
- Check Agent logs for errors

**B) Samples failed to upload to S3**
- Check S3 `gse-raw/` — are there ANY files for this request?
- Check Agent logs for S3 upload errors (permissions? network?)

**C) Agent didn't call gse-request-complete endpoint**
- Manual check: Did Agent have the endpoint URL?
- Check gse-request-complete CloudWatch for incoming calls

### Resolution

1. **Check Agent logs for upload errors:**
   ```bash
   # Contact Agent team for logs
   # Look for: S3 PutObject errors, permission denied, network timeouts
   ```

2. **Check DDB REQUEST record:**
   ```bash
   aws dynamodb get-item \
     --table-name classifier-cycles-state \
     --key '{"PK": {"S": "ent-001"}, "SK": {"S": "REQUEST#request-id#cycle-id"}}' \
     | jq '.Item | {status, samples_expected, total_samples_uploaded}'
   ```

3. **Check if endpoint is reachable:**
   ```bash
   curl -X POST https://api.example.com/v2/gse/request-complete \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"request_id": "...", "total_samples_uploaded": 10}' \
     -v
   # Should see 200 OK
   ```

---

## 5. OpenSearch queries returning no results

### Symptoms
```
Client UI shows "0 candidates matched"
But manually verifying with keywords, there SHOULD be matches
```

### Root Causes

**A) Keywords were never uploaded to S3**
- Check S3 `keywords/` — is `{enterprise_id}.json` there?
- If not, needs manual Bedrock generation

**B) joyas-priorizer crashed or didn't match**
- Check EMR Spark job logs for errors
- Check if keywords are in correct JSONL format

**C) crown-candidates-indexer failed to index**
- Check CloudWatch for `crown-candidates-indexer`
- Check OpenSearch cluster health: `curl localhost:9200/_cluster/health`

**D) OpenSearch query syntax is wrong**
- Manual test:
   ```bash
   curl -X GET "localhost:9200/crown_jewels-ent-001/_search" \
     -H 'Content-Type: application/json' \
     -d '{"query": {"match": {"path": "plan estrategico"}}}'
   # Check if results are there
   ```

### Resolution

1. **Check keywords file:**
   ```bash
   aws s3 cp s3://keywords/ent-001.json - | head -5
   # Should see: {"category": "...", "original_category": "..."}
   ```

2. **Check OpenSearch index:**
   ```bash
   curl -X GET "localhost:9200/_cat/indices" | grep crown_jewels
   # Should see: crown_jewels-ent-001 with non-zero doc count
   ```

3. **Reindex if needed:**
   ```bash
   # Manually re-trigger crown-candidates-indexer
   aws lambda invoke \
     --function-name crown-candidates-indexer \
     --payload '{"cycle_id": "...", "enterprise_id": "ent-001"}' \
     /tmp/response.json
   ```

---

## 6. Lambda execution timeout (15 min default)

### Symptoms
```
Lambda "tree-uncompressor" timed out after 15 minutes
CloudWatch shows: "Task timed out after 900.xx seconds"
```

### Root Causes

**A) Input is too large**
- `.jsonl.gz` file is huge (> 1GB uncompressed)
- Decompression takes > 15 min

**B) Network latency to S3**
- S3 GetObject or PutObject is slow
- Check VPC route to S3 (should use VPC endpoint)

**C) Lambda memory too low**
- Lambda allocated < 512 MB
- Decompression/processing is CPU-bound

### Resolution

1. **Increase Lambda timeout:**
   ```bash
   aws lambda update-function-configuration \
     --function-name tree-uncompressor \
     --timeout 900 \
     # (increase from 900 to 1800, etc.)
   ```

2. **Increase Lambda memory:**
   ```bash
   aws lambda update-function-configuration \
     --function-name tree-uncompressor \
     --memory-size 1024 \
     # (increases CPU too)
   ```

3. **Add S3 VPC endpoint (if missing):**
   ```bash
   # Check: VPC → Endpoints → is there an S3 endpoint?
   # If not, create one (DevOps should do this)
   ```

4. **Stream decompression instead of buffering:**
   - If file is > 500MB, refactor to stream .gz instead of loading all at once

---

## 7. KEM API returns 404 or empty stations

### Symptoms
```
crown-candidates-indexer receives: {"stations": []}
CYCLE created with stations_expected: 0
Fase 2 is skipped (no stations to sample)
```

### Root Causes

**A) Enterprise ID doesn't exist in KEM**
- KEM API has no active stations for this enterprise

**B) KEM API is down**
- Check KEM service status

**C) Wrong enterprise ID passed**
- Check CYCLE.enterprise_id matches KEM query param

### Resolution

1. **Manually query KEM:**
   ```bash
   curl -H "Authorization: Bearer $KEM_API_KEY" \
     https://kem.example.com/v2/kem/stations?enterprise_id=ent-001
   # Should see: {"stations": [{"id": "ws-01"}, ...]}
   ```

2. **If 404:**
   - Contact KEM team: is this enterprise provisioned?

3. **If 500:**
   - Wait for KEM to recover, retry manually via re-triggering `crown-candidates-indexer`

---

## 8. Signal Handler stub is blocking Fase 2

### Symptoms
```
gse-cycle-init completes
But Agent never receives sampling request
Signal Handler is in stub mode (returns success but doesn't actually notify)
```

### Resolution

**This is expected in alpha/beta.** Signal Handler integration is planned for 2026-07-14 (Beta phase).

For now:
1. **Manual workaround:** Ops team can directly invoke Agent with cycle payload (temporary)
2. **Use SNS for testing:** Configure Signal Handler to publish to SNS instead of real channel

See INTEGRATIONS.md for Signal Handler contract.

---

## 9. Anonymizer is down (samples stuck in gse-raw)

### Symptoms
```
gse-raw/ has 100 files
gse-anonymized/ has 0 files
Cycle stuck in phase2_collecting for > 6 hours
```

### Root Causes

Anonymizer service is offline or processing is very slow.

### Resolution

1. **Check Anonymizer status:**
   - Contact Plataforma IA team

2. **Manual workaround (temporary):**
   ```bash
   # Copy gse-raw to gse-anonymized without processing (TEST ONLY)
   aws s3 cp s3://gse-raw/ent-001/ s3://gse-anonymized/ent-001/ --recursive
   # Then manually trigger gse-sample-anonymizer-notifier for each file
   ```

3. **Retry policy:**
   - SQS queue has retry policy; if Anonymizer recovers, it will retry automatically

---

## 10. DDB Stream lag is high

### Symptoms
```
EventBridge Pipes shows: "HighestEventAge": 3600000 (1 hour old)
Lambdas are processing events from an hour ago
CYCLE is slow to transition
```

### Root Causes

**A) Too many write requests to DDB**
- Concurrent cycles exhausting DDB write capacity

**B) Lambda concurrency is too low**
- EventBridge Pipes backed up because target Lambda is full

**C) Lambda has high error rate**
- Retries are backing up the queue

### Resolution

1. **Check DDB metrics:**
   ```bash
   # CloudWatch → DynamoDB → classifier-cycles-state
   # Look for: ConsumedWriteCapacityUnits spike
   ```

2. **Increase Lambda reserved concurrency:**
   ```bash
   aws lambda put-function-concurrency \
     --function-name gse-station-status \
     --reserved-concurrent-executions 100 \
     # (increase from current)
   ```

3. **Check Lambda error rate:**
   ```bash
   # CloudWatch → Logs → search for errors in gse-station-status
   ```

4. **Flush old events in Pipes:**
   - EventBridge Pipes doesn't have manual flush; wait for SQS retention to expire (14 days default)
   - Or increase Lambda concurrency to process faster

---

## 11. Conditional write failed (exactly-once barrier)

### Symptoms
```
Lambda logs: "Conditional write failed: barrier_counted=true already set"
STATION.barrier_counted: true (already counted once)
No error returned, but request counted twice?
```

### Root Causes

**This is correct behavior.** Duplicate DDB Stream record arrived, second conditional write lost the race.

### Resolution

This is **not a bug**, it's the idempotency mechanism working. DDB Stream can deliver the same record twice; conditional writes ensure only the first one increments the counter.

**Check logs:**
```bash
# Normal log pattern:
# "Attempt 1: SET barrier_counted=true WHERE barrier_counted<>true → SUCCESS, stations_completed += 1"
# "Attempt 2 (duplicate): SET barrier_counted=true WHERE barrier_counted<>true → FAIL (already true) → IGNORED"
```

---

## 12. Manual Cycle triggering / Reaper Lambda

### How to manually re-trigger a stuck cycle?

If you've fixed the root cause and want to retry:

```bash
# 1. Update CYCLE status back to "scanning" (if stuck there)
aws dynamodb update-item \
  --table-name classifier-cycles-state \
  --key '{"PK": {"S": "ent-001"}, "SK": {"S": "CYCLE#cycle-id"}}' \
  --update-expression "SET #s = :v" \
  --expression-attribute-names '{"#s": "status"}' \
  --expression-attribute-values '{":v": {"S": "scanning"}}'

# 2. Manually invoke the next Lambda in the flow (e.g., crown-candidates-indexer)
aws lambda invoke \
  --function-name crown-candidates-indexer \
  --payload '{"cycle_id": "cycle-id", "enterprise_id": "ent-001"}' \
  /tmp/response.json
```

### Reaper Lambda (cleanup stuck cycles)

A background Lambda runs every 6 hours to detect stuck cycles and close them:

- **Stuck criteria:** CYCLE in `phase2_collecting` for > 24 hours
- **Action:** Transitions to `phase2_skipped` (marks Fase 2 as abandoned)
- **Owner:** DevOps (KT-17083)

---

## Escalation Checklist

**When to reach out to team leads:**

| Symptom | Owner | Action |
|---|---|---|
| CloudWatch shows Lambda is crashing | Backend | Open issue, provide error logs |
| OpenSearch or DDB metrics are red | DevOps | Infrastructure alert |
| Agent never uploaded files | Agent Platform | Check Agent logs |
| Anonymizer is down for > 1h | Plataforma IA | Escalate to on-call |
| KEM returns 404 for enterprise | KEM Team | Verify enterprise is provisioned |
| Signal Handler not delivering payloads | IoT/Signal team | TBD; blocking beta |

---

## Quick Reference: Common Queries

### Find all stuck cycles

```bash
aws dynamodb query \
  --table-name classifier-cycles-state \
  --key-condition-expression "PK = :pk AND begins_with(SK, :sk)" \
  --expression-attribute-values '{":pk": {"S": "ent-001"}, ":sk": {"S": "CYCLE#"}}' \
  --filter-expression "#s = :status AND created_at < :age" \
  --expression-attribute-names '{"#s": "status"}' \
  --expression-attribute-values '{":status": {"S": "scanning"}, ":age": {"N": "'$(date +%s -d '1 hour ago')'"}}'
```

### Find all stations that haven't reported scan_status

```bash
aws dynamodb query \
  --table-name classifier-cycles-state \
  --key-condition-expression "PK = :pk AND begins_with(SK, :sk)" \
  --expression-attribute-values '{":pk": {"S": "ent-001"}, ":sk": {"S": "STATION#"}}' \
  --filter-expression "attribute_not_exists(scan_status)"
```

### Count total samples in gse-raw

```bash
aws s3 ls s3://gse-raw/ent-001/ --recursive --summarize | tail -2
```
