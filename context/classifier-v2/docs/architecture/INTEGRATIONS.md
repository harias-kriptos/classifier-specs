# External Integrations — Black Box Contracts

## Signal Handler

**Owned by:** Equipo plataforma agente / IoT  
**Role:** Push cycle payload to agent for Fase 2 sample collection  
**Trigger:** `gse-cycle-init` Lambda  
**Input contract:**
```json
{
  "cycle_id": "uuid",
  "process_type": "crown_validated",
  "enterprise_id": "ent-001",
  "station_id": "ws-machine-01",
  "requests": [
    {
      "type": "pii",
      "files": ["path/to/file1", "path/to/file2"],
      "sample_content_size": 8192
    }
  ]
}
```
**Output:** Agent receives payload (channel TBD: SNS/SQS/IoT/HTTP)  
**Status:** Stub (returns success immediately in dev)  
**Deadline:** Fase 2 alpha (blocking real integration in beta)

---

## Anonymizer

**Owned by:** Equipo seguridad / IA  
**Role:** Read `gse-raw`, apply privacy transformations, write `gse-anonymized`  
**Trigger:** S3 PutObject event on `gse-raw/` (via SQS)  
**Input contract:**
```
S3 path: gse-raw/{enterprise_id}/{station_id}/{cycle_id}/{request_type}/sample_{N}.json
File content: {"chunk": "...", "metadata": {...}}
```
**Output contract:**
```
S3 path: gse-anonymized/{enterprise_id}/{station_id}/{cycle_id}/{request_type}/sample_{N}.json
File content: {"chunk": "[anonymized]", "metadata": {...}}
```
**Idempotency:** By `sample_id` (path hash)  
**Status:** Stub (copies input to output unchanged)  
**Deadline:** Fase 2 beta (real impl required before prod)

---

## LLM Process Queue

**Owned by:** Equipo IA  
**Role:** Consume closed cycles, read samples from `gse-anonymized`, classify, write results to DDB  
**Trigger:** `gse-enterprise-status` Lambda (when CYCLE → complete)  
**Input contract:**
```json
{
  "cycle_id": "uuid",
  "enterprise_id": "ent-001",
  "s3_prefix": "s3://gse-anonymized/ent-001//{station_id}/{cycle_id}/**",
  "process_type": "crown_validated"
}
```
**Output contract:** Updates DDB table `analyses` with `classification_result` per document  
**Idempotency:** By `cycle_id` (skip if already processed)  
**Status:** Stub (receives but doesn't process)  
**Deadline:** Fase 2 beta

---

## KEM API

**Owned by:** Equipo backend (existing service)  
**Role:** Return active stations per enterprise  
**Endpoint:** `GET /v2/kem/stations?enterprise_id={ent_id}`  
**Response contract:**
```json
{
  "enterprise_id": "ent-001",
  "stations": [
    {"id": "ws-machine-01", "status": "active"},
    {"id": "ws-machine-02", "status": "active"}
  ],
  "total": 2
}
```
**Usage:** `crown-candidates-indexer` queries on CYCLE creation → sets `stations_expected`  
**Auth:** API key from Secrets Manager  
**Status:** Existing (no changes needed)

---

## Bedrock (Keywords Generation)

**Owned by:** Equipo data / IA  
**Role:** Generate keywords for matching  
**Trigger:** Manual (not automated)  
**Input:** Enterprise context, sector, country  
**Output:** JSONL file uploaded to `keywords/{enterprise_id}.json`  
**Format:**
```jsonl
{"category": "plan estrategico", "original_category": "Plan Estratégico", "business_area": "estrategia", "original_business_area": "Estrategia & Planeación"}
```
**Status:** Manual process (fixture data in test)  
**Deadline:** Before Fase 1 can match (blocking Fase 1 alpha for real customers)

---

## Integration Matrix

| Component | Trigger | Channel | Status | Required by |
|---|---|---|---|---|
| Signal Handler | gse-cycle-init publishes | TBD (SNS/SQS/HTTP) | Stub | Fase 2 beta |
| Anonymizer | SQS gse-sample-reception-queue | S3 notifications | Stub | Fase 2 beta |
| LLM | gse-enterprise-status publishes | TBD | Stub | Fase 2 beta |
| KEM API | crown-candidates-indexer queries | HTTP | Existing | Fase 1 alpha |
| Bedrock | Manual upload | S3 | Manual | Fase 1 alpha (if real data) |

---

## Fallback Strategy

| Black Box | Failure Mode | Backend behavior | Impact |
|---|---|---|---|
| Signal Handler offline | gse-cycle-init cannot notify | Log WARN, continue, SQS retry | Agent doesn't receive payload, manual retry needed |
| Anonymizer hangs | Samples stuck in gse-raw | DDB barrier waits, SQS retry | Cycle hangs in phase2_collecting, reaper closes it after 24h |
| LLM offline | gse-enterprise-status cannot publish | Log WARN, continue, manual notification | Cycle marked complete but LLM doesn't know, manual trigger |
| KEM 404 | crown-candidates-indexer cannot get stations_expected | Fail with 400, escalate to ops | Cycle cannot start, user must contact support |
| Bedrock no keywords | joyas-priorizer finds no matches | Writes empty crown_jewels.jsonl | Zero candidates → Fase 2 is skipped (valid) |
