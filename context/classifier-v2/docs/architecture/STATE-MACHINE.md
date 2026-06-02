# State Machine — CYCLE, STATION, REQUEST

## CYCLE State Transitions

The CYCLE entity tracks the progress of an entire enterprise through Fase 1 and Fase 2.

```
scanning
  ↓ (crown-enterprise-barrier when all STATIONs report scan_status="complete")
stations_complete
  ↓ (crown-validation-handler allows mutations here)
confirmed
  ↓ (crown-validation-confirm when client confirms the set)
phase2_collecting
  ↓ (gse-enterprise-status when all STATIONs close in Fase 2)
complete
  ↓
[cycle archived, TTL triggers cleanup after 90d]

Alternative path:
confirmed → phase2_skipped
  ↓ (if crown-validation-confirm finds 0 approved candidates)
[Fase 2 does not trigger]
```

### Fields per CYCLE state

| State | Field | Value | Who sets |
|---|---|---|---|
| `scanning` | `status` | "scanning" | crown-candidates-indexer (on create) |
| | `stations_expected` | N (from KEM) | crown-candidates-indexer |
| | `stations_completed` | 0 | (incremented by crown-enterprise-barrier) |
| `stations_complete` | `status` | "stations_complete" | crown-enterprise-barrier |
| | `stations_completed` | = stations_expected | crown-enterprise-barrier |
| `confirmed` | `status` | "confirmed" | crown-validation-confirm |
| | `confirmed_at` | now() | crown-validation-confirm |
| | `approved_count` | N | (from OpenSearch) |
| `phase2_collecting` | `status` | "phase2_collecting" | gse-cycle-init |
| | `sampling_status` | "collecting" | (implicit) |
| `complete` | `status` | "complete" | gse-enterprise-status |
| | `completed_at` | now() | gse-enterprise-status |
| | `ttl` | now() + 90d | gse-enterprise-status |

---

## STATION State Transitions

Each STATION tracks the progress per enterprise+station pair across both phases.

```
Fase 1:
  requested
    ↓ (crown-candidates-indexer)
  scan_status: complete
    ↓ (implicit on creation)
  candidates_count: N

Fase 2:
  sampling_status: requested
    ↓ (gse-cycle-init)
  sampling_status: uploading
    ↓ (gse-sample-reception-notifier on first sample)
  sampling_status: sample_collected
    ↓ (implicit when all samples received)
  sampling_status: sample_anonymized
    ↓ (gse-sample-anonymizer-notifier when all anonymized)
  [gse-station-status closes STATION]
  status: complete
```

### Barrier logic (STATION close condition)

STATION closes when: `(samples_anonymized + samples_skipped) >= samples_expected`

Dispatcher: `gse-station-status` (Lambda on DDB Stream filter `STATION#` + Fase 2 status)

---

## REQUEST State Transitions

Each REQUEST tracks sampling progress for a specific request type (e.g., "pii", "financial").

```
requested
  ↓ (gse-cycle-init creates REQUEST per STATION)
sent
  ↓ (gse-request-complete when agent finishes uploading)
```

### Fields

| State | Field | Value | Who sets |
|---|---|---|---|
| `requested` | `status` | "requested" | gse-cycle-init |
| | `samples_expected` | len(files_to_sample) | gse-cycle-init |
| `sent` | `status` | "sent" | gse-request-complete |
| | `total_samples_uploaded` | N (from body) | gse-request-complete |
| | `samples_skipped` | N (from body) | gse-request-complete |
| | `sent_at` | now() | gse-request-complete |

---

## Transition Triggers by Lambda

| Lambda | Trigger | Transition | New status |
|---|---|---|---|
| **crown-candidates-indexer** | S3 PutObject `crown_jewels/{ent}/{sta}/matches.jsonl` | CYCLE created + STATION created (Fase 1) | scanning + scan_status=complete |
| **crown-enterprise-barrier** | DDB Stream STATION record + scan_status=complete | CYCLE stations_completed += 1, check if ready | stations_complete |
| **crown-validation-handler** | GraphQL mutation (client UI) | OpenSearch update + DDB counter update | (CYCLE stays confirmed) |
| **crown-validation-confirm** | HTTP POST `/v2/validation/confirm` | Freeze validation, write manifest, CYCLE → confirmed | confirmed or phase2_skipped |
| **gse-cycle-init** | S3 PutObject `validated_crown_jewels/{ent}/{cycle}/manifest.json` | CYCLE → phase2_collecting, create STATIONs (Fase 2) | phase2_collecting |
| **gse-sample-reception-notifier** | S3 PutObject `gse-raw/{ent}/{sta}/{cycle}/{req}/sample.json` | STATION sampling_status=uploading, samples_received += 1 | uploading |
| **gse-sample-anonymizer-notifier** | S3 PutObject `gse-anonymized/{ent}/{sta}/{cycle}/{req}/sample.json` | STATION samples_anonymized += 1 | (check barrier) |
| **gse-station-status** | DDB Stream STATION record + barrier met | Increment CYCLE stations_completed | STATION.status=complete |
| **gse-enterprise-status** | DDB Stream CYCLE record + all STATIONs complete | Notify LLM, set TTL, CYCLE → complete | complete |

---

## Idempotency & Exactly-Once Semantics

Each transition uses **conditional writes** to guarantee exactly-once:

- **crown-enterprise-barrier:** `SET barrier_counted=true IF barrier_counted<>true` (wins the race against duplicated Stream records)
- **crown-enterprise-barrier → CYCLE update:** `ADD stations_completed=1 IF status="scanning"`
- **gse-station-status:** `SET status="complete" IF (samples_anonymized + samples_skipped) >= expected`
- **gse-enterprise-status:** `SET status="complete" IF status="phase2_collecting"`

---

## Monitoring & Debugging

Use these queries to diagnose hangs:

```sql
-- CYCLE stuck in "scanning"
SELECT * FROM classifier-cycles-state 
WHERE pk = "ent-001" AND sk begins_with "CYCLE#" 
AND #status = "scanning" 
AND created_at < now() - 1 hour

-- STATION not reporting scan_status=complete
SELECT * FROM classifier-cycles-state 
WHERE pk = "ent-001" AND sk begins_with "STATION#" 
AND scan_status <> "complete"

-- REQUEST not marked as "sent" (agent didn't call /v2/gse/request-complete)
SELECT * FROM classifier-cycles-state 
WHERE pk = "ent-001" AND sk begins_with "REQUEST#" 
AND #status = "requested" 
AND created_at < now() - 30 min
```
