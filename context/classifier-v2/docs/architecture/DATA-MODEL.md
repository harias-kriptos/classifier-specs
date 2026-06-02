# Data Model — DynamoDB `classifier-cycles-state`

## Table Schema

| Attribute | Type | Description |
|---|---|---|
| **PK** (partition key) | String | `enterprise_id` — fixed for entire table |
| **SK** (sort key) | String | Multi-prefix: `CYCLE#`, `STATION#`, `REQUEST#` |
| `ttl` | Number | Unix timestamp for auto-delete (90d after completion) |
| `created_at` | String | ISO-8601 timestamp |
| `updated_at` | String | ISO-8601 timestamp |

---

## Entity: CYCLE

Represents a full scan+validate+sample cycle for an enterprise.

```
PK: ent-001
SK: CYCLE#{cycle_id}
Attributes:
  cycle_id: String                    # UUID
  enterprise_id: String               # (duplicate of PK, for GSI if needed)
  status: String                      # scanning|stations_complete|confirmed|phase2_collecting|phase2_skipped|complete
  process_type: String                # crown_validated | classification
  stations_expected: Number           # From KEM query
  stations_completed: Number          # Incremented by crown-enterprise-barrier
  approved_count: Number              # From OpenSearch at confirmation
  rejected_count: Number              # Idem
  manually_added_count: Number        # Idem
  created_at: String                  # When first station reported
  stations_complete_at: String        # When all stations completed Fase 1
  confirmed_at: String                # When client confirmed validation
  phase2_triggered_at: String         # When crown-validation-confirm materialized manifest
  completed_at: String                # When LLM finished
  ttl: Number                         # Expires 90d after completion
```

**Example row:**
```json
{
  "PK": "ent-001",
  "SK": "CYCLE#a1b2c3d4-e5f6",
  "cycle_id": "a1b2c3d4-e5f6",
  "enterprise_id": "ent-001",
  "status": "phase2_collecting",
  "process_type": "crown_validated",
  "stations_expected": 3,
  "stations_completed": 2,
  "approved_count": 247,
  "rejected_count": 12,
  "manually_added_count": 5,
  "created_at": "2026-05-28T10:00:00Z",
  "stations_complete_at": "2026-05-28T10:05:00Z",
  "confirmed_at": "2026-05-28T10:15:00Z",
  "phase2_triggered_at": "2026-05-28T10:16:00Z",
  "completed_at": null,
  "ttl": 1751683200
}
```

---

## Entity: STATION

Represents a single workstation/client within an enterprise cycle.

```
PK: ent-001
SK: STATION#{station_id}#{cycle_id}
Attributes:
  station_id: String                  # Machine/client identifier
  cycle_id: String                    # Parent CYCLE
  enterprise_id: String
  scan_status: String                 # requested | complete
  candidates_count: Number            # Matched by joyas-priorizer
  
  # Fase 2 only
  sampling_status: String             # requested | uploading | sample_collected | sample_anonymized | complete
  samples_expected: Number            # From crown_jewels.jsonl
  samples_received: Number            # Incremented by gse-sample-reception-notifier
  samples_anonymized: Number          # Incremented by gse-sample-anonymizer-notifier
  samples_skipped: Number             # From gse-request-complete body
  
  # Barrier flag for exactly-once
  barrier_counted: Boolean            # true once this STATION incremented CYCLE.stations_completed
  
  created_at: String
  scan_complete_at: String            # Phase 1
  sampling_complete_at: String        # Phase 2
  ttl: Number
```

**Example row (Fase 1 complete):**
```json
{
  "PK": "ent-001",
  "SK": "STATION#ws-machine-01#a1b2c3d4",
  "station_id": "ws-machine-01",
  "cycle_id": "a1b2c3d4-e5f6",
  "enterprise_id": "ent-001",
  "scan_status": "complete",
  "candidates_count": 127,
  "created_at": "2026-05-28T10:00:15Z",
  "scan_complete_at": "2026-05-28T10:03:00Z"
}
```

**Example row (Fase 2 in progress):**
```json
{
  "PK": "ent-001",
  "SK": "STATION#ws-machine-01#a1b2c3d4",
  "station_id": "ws-machine-01",
  "cycle_id": "a1b2c3d4-e5f6",
  "scan_status": "complete",
  "candidates_count": 127,
  "sampling_status": "uploading",
  "samples_expected": 47,
  "samples_received": 23,
  "samples_anonymized": 15,
  "samples_skipped": 9,
  "barrier_counted": false,
  "created_at": "2026-05-28T10:00:15Z",
  "scan_complete_at": "2026-05-28T10:03:00Z"
}
```

---

## Entity: REQUEST

Represents a sampling request for a specific request type (e.g., "pii", "financial").

```
PK: ent-001
SK: REQUEST#{request_id}#{cycle_id}
Attributes:
  request_id: String                  # UUID
  cycle_id: String                    # Parent CYCLE
  station_id: String                  # Which station
  enterprise_id: String
  request_type: String                # pii | financial | etc.
  status: String                      # requested | sent
  samples_expected: Number            # From cycle payload
  total_samples_uploaded: Number      # From gse-request-complete body
  samples_skipped: Number             # From gse-request-complete body
  skipped_reasons: List               # [{path, reason}]
  created_at: String
  sent_at: String                     # When agent called /v2/gse/request-complete
  ttl: Number
```

**Example row:**
```json
{
  "PK": "ent-001",
  "SK": "REQUEST#req-xyz#a1b2c3d4",
  "request_id": "req-xyz",
  "cycle_id": "a1b2c3d4-e5f6",
  "station_id": "ws-machine-01",
  "enterprise_id": "ent-001",
  "request_type": "pii",
  "status": "sent",
  "samples_expected": 25,
  "total_samples_uploaded": 22,
  "samples_skipped": 3,
  "skipped_reasons": [
    {"path": "/root/.ssh/id_rsa", "reason": "permission_denied"},
    {"path": "/var/log/auth.log", "reason": "locked_by_process"},
    {"path": "/home/user/temp.doc", "reason": "file_not_found"}
  ],
  "created_at": "2026-05-28T10:16:00Z",
  "sent_at": "2026-05-28T10:25:00Z"
}
```

---

## Indexes

### Implicit (on PK + SK)
- Queries like `PK = "ent-001" AND SK begins_with "CYCLE#"` are naturally fast

### Recommended GSI (if needed)
```
GSI: status-created-index
  PK: status (e.g., "phase2_collecting")
  SK: created_at
  → Fast queries like "all cycles stuck in phase2_collecting for 1+ hour"
```

---

## TTL & Cleanup

- **Default:** 90 days after `completed_at`
- **Computation:** `gse-enterprise-status` sets `ttl = now() + (90 * 86400)`
- **Auto-cleanup:** DynamoDB deletes rows when `ttl` is in the past (triggers every 6h by default)
- **Manual cleanup:** If needed, partition by month for easier manual retention tuning

---

## Billing & Capacity

- **Billing:** Pay-per-request (no provisioned capacity)
- **Estimated:** ~10-50 KB per cycle (3 entities × CYCLE + N STATIONs × STATION + N REQUESTs × REQUEST)
- **Write volume:** ~10-30 writes per cycle (depends on station count, sample count)
- **Stream:** ON (required for state lambdas)

---

## Example: Full cycle with 3 stations

```
PK: ent-001, SK: CYCLE#cycle-1 (rows: 1)
PK: ent-001, SK: STATION#ws-01#cycle-1 (rows: 1)
PK: ent-001, SK: STATION#ws-02#cycle-1 (rows: 1)
PK: ent-001, SK: STATION#ws-03#cycle-1 (rows: 1)
PK: ent-001, SK: REQUEST#req-1#cycle-1 (rows: 1)  [for ws-01, type=pii]
PK: ent-001, SK: REQUEST#req-2#cycle-1 (rows: 1)  [for ws-02, type=pii]
PK: ent-001, SK: REQUEST#req-3#cycle-1 (rows: 1)  [for ws-03, type=pii]

Total: 7 items (1 CYCLE + 3 STATIONs + 3 REQUESTs)
```
