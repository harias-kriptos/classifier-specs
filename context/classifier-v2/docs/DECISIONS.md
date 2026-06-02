# Architectural Decisions — Design Rationale (ADR-style)

## Decision 1: Single DynamoDB table (`classifier-cycles-state`)

### Problem
How to store state for CYCLE, STATION, and REQUEST entities across Fase 1 and Fase 2 without complex sync or separate data stores?

### Decision
**Single table with multi-prefix SK pattern**
- PK: `enterprise_id`
- SK: `CYCLE#{id}` | `STATION#{id}#{cycle_id}` | `REQUEST#{id}#{cycle_id}`

### Rationale
- **Unified state:** No sync bottleneck between Fase 1 and 2 — both phases read/write same table
- **Single Stream:** One DDB Stream feeds all state lambdas
- **Cost:** Pay-per-request mode is cheaper than provisioned for bursty workloads
- **Exactly-once:** DDB conditional writes provide idempotency without distributed locks

### Trade-off
- Less granular than 3 separate tables (one per entity type)
- Single-table GSI queries can be expensive if SK cardinality is high

### Status
✅ Implemented

---

## Decision 2: Two monorepos (not 15)

### Problem
15 separate Lambda repos (tree-url-gen, tree-uncomp, joyas-priorizer, etc.) lead to:
- CI/CD overhead (15 separate pipelines)
- Cross-Lambda changes require 15 PRs
- Inconsistent testing/linting/versioning

### Decision
**Two monorepos:**
- `classifier-scan-match-backend` (8 Lambdas: Fase 1)
- `classifier-gse-backend` (6 Lambdas: Fase 2)

### Rationale
- **Cohesion:** Lambdas within a monorepo share event patterns (same DDB table, same Stream)
- **Consistency:** Single pytest/ruff/mypy config per monorepo
- **Agility:** Cross-Lambda changes land in 1 PR instead of 8
- **Autonomy retained:** Two repos = clear Fase 1 vs Fase 2 boundary

### Trade-off
- Less granular dependency management (all Lambdas in a monorepo share transitive deps)
- Larger CI builds (but parallelizable per Lambda)

### Status
✅ Implemented (KT-17034, KT-17134)

---

## Decision 3: State machine in DDB + DDB Stream (not Step Functions)

### Problem
Complex multi-phase orchestration (Fase 1 → Validación → Fase 2) requires state transitions, but Step Functions adds:
- API calls (expensive, ~0.25-1ms latency)
- Separate billing
- Operational overhead (SFN logs, debuggability)

### Decision
**Use DDB + DDB Stream + EventBridge Pipes**
- State lives in DDB (CYCLE.status, STATION.sampling_status, etc.)
- DDB Stream captures all state changes
- Pipes filter on patterns → trigger Lambda

### Rationale
- **Latency:** < 1s end-to-end (DDB write → Stream → EventBridge → Lambda invoke)
- **Cost:** No per-transition billing
- **Simplicity:** State is visible in DDB queries; no SFN execution history to debug
- **Idempotency:** Conditional writes + barrier flags prevent duplicate processing

### Trade-off
- No visual SFN diagram; instead, read STATE-MACHINE.md
- Requires careful handling of Stream ordering (mitigated by idempotency)

### Status
✅ Implemented

---

## Decision 4: EventBridge Pipes (not direct Lambda subscription to DDB Stream)

### Problem
Direct Lambda → DDB Stream subscriptions:
- No filtering (all records → all Lambdas)
- No retry policy (one failure kills the consumer group)
- No DLQ
- No batching control

### Decision
**Use EventBridge Pipes with DDB Stream as source**
- Pipes filter on SK prefix (CYCLE#, STATION#, REQUEST#)
- Dead-Letter Queue for failed events
- Configurable retry + max-age
- Clear architecture diagram (source → filter → enrichment → target)

### Rationale
- **Decoupling:** Stream filtering is separate from Lambda logic
- **Resilience:** DLQ catches failed invokes; ops can replay
- **Observability:** Pipes metrics in CloudWatch
- **Scalability:** One Pipe per entity type (CYCLE, STATION, REQUEST) keeps matchers simple

### Trade-off
- Extra hop (Stream → Pipe → Lambda) adds ~10-50ms latency (acceptable for this use case)
- EventBridge quota limits (if ever hitting 1000s events/sec, need quota adjustment)

### Status
✅ Design (infra in KT-17017-23)

---

## Decision 5: Validation phase (not skipped)

### Problem
Fase 1 (scan+match) outputs candidates automatically. Should Fase 2 (sampling) start immediately, or let the client review first?

### Decision
**Fase 1 → Validación (human review) → Fase 2**

Three states:
- `stations_complete` → CYCLE ready for approval
- `confirmed` → Client approved candidates (or edited them)
- `phase2_collecting` → Sampling starts

### Rationale
- **Compliance:** Enterprise knows exactly what's being sampled
- **Accuracy:** Manual override catches keyword false positives
- **Trust:** Client UI feedback loop before sampling (privacy-critical)
- **Flexibility:** Can skip Fase 2 if zero candidates approved

### Trade-off
- Extra latency (2-10 min validation window)
- UI must implement mutation handler (GraphQL)

### Status
✅ Implemented (crown-validation-handler, crown-validation-confirm)

---

## Decision 6: Python 3.11 + Lambda Container Image + ECR

### Problem
Cold start, package size, dependency management for 14 separate Lambdas.

### Decision
**Python 3.11, Container Image (not ZIP), shared ECR repo**

### Rationale
- **Cold start:** Container image ~200-500ms (vs ZIP which is faster but less flexible)
- **Dependencies:** Single Dockerfile per monorepo, all Lambdas inherit base layers
- **Size:** ECR image reuse across Lambda versions
- **Tooling:** ruff, mypy, pytest in container; no local config drift

### Trade-off
- Slightly slower cold start than ZIP (mitigated by reserved concurrency)
- Container build time (but cached between deployments)

### Status
✅ Implemented (stacks/python-lambda/)

---

## Decision 7: Exactly-once semantics with conditional DDB writes

### Problem
DDB Stream can deliver the same record twice (at-least-once guarantee). How to prevent double-counting (e.g., STATION being counted twice by barrier)?

### Decision
**Barrier flags + conditional writes**
- STATION.barrier_counted (boolean, default false)
- crown-enterprise-barrier: `SET barrier_counted=true IF barrier_counted<>true` (atomic compare-and-set)
- Only the first writer increments CYCLE.stations_completed

### Rationale
- **Simple:** No distributed locks or consensus; DDB atomic operation
- **Idempotent:** Duplicate Stream records are safe (second write fails condition, is ignored)
- **Observable:** Can query barrier_counted=false to find stuck stations

### Trade-off
- Requires careful write condition per state (not a blanket solution)
- If condition fails, error is silent (logged but not retried) — OK because condition failure = already processed

### Status
✅ Implemented

---

## Decision 8: Multi-phase naming (Fase 1 Scan+Match, Fase 1 Validación, Fase 2 GSE)

### Problem
Fase 1 and Fase 2 are both "Fase 1" in colloquial usage (confusing). Are they the same phase or two?

### Decision
**Three phases:**
- **Fase 1 Scan+Match:** Agent scans → backend matches (fully automated)
- **Fase 1 Validación:** Client validates candidates in UI (human-in-the-loop)
- **Fase 2 GSE:** Agent collects samples → Anonymizer → LLM classifies (automated + external)

### Rationale
- **Clarity:** Three distinct workflows with different actors
- **Tickets:** 11 dev tickets map cleanly to phases (8 Fase 1 Scan+Match + 4 Fase 1 Validación + 6 Fase 2 GSE, minus overlaps)
- **Documentation:** Easier to say "Validación is phase 1.5" than "Fase 1b"

### Trade-off
- Terminology is new (internal, not customer-facing)
- Requires updating all docs (CONSOLIDATION-INDEX, ARCHITECTURE, etc.)

### Status
✅ Documented (CONSOLIDATION-INDEX.md)

---

## Decision 9: KEM API for station count (not self-managed)

### Problem
How does Classifier know how many workstations an enterprise has?

### Decision
**Query KEM API at CYCLE start**
- crown-candidates-indexer calls `GET /v2/kem/stations?enterprise_id={ent_id}`
- Stores response in CYCLE.stations_expected

### Rationale
- **Single source of truth:** KEM owns device inventory; Classifier doesn't replicate it
- **Consistency:** If station goes offline mid-cycle, KEM doesn't change expected count (expected count is immutable)
- **Simplicity:** No Classifier-owned device table

### Trade-off
- Dependency on KEM availability (if KEM is down, CYCLE creation fails)
- If KEM returns stale data, Classifier waits for non-existent stations

### Status
✅ Implemented

---

## Decision 10: S3 for sample storage (not EBS, DDB)

### Problem
Samples are large (100s MB per station). Store in DDB or S3?

### Decision
**S3 with multi-stage folders**
- `gse-raw/{ent}/{sta}/{cycle}/{req}/sample.json` (agent uploads here)
- `gse-anonymized/{ent}/{sta}/{cycle}/{req}/sample.json` (Anonymizer outputs here)
- TTL lifecycle rules to delete after 90d

### Rationale
- **Cost:** S3 << DDB for large blobs
- **Scalability:** No DDB throughput limits on large samples
- **Audit trail:** Three bucket versions (raw, anonymized, final) are visible

### Trade-off
- Requires S3 → SQS → Lambda workflows (extra infrastructure)
- Cross-account access complexity (if Anonymizer is in different account)

### Status
✅ Designed (bucket names TBD in infra)

---

## Summary Table

| Decision | Trade-off | Risk |
|---|---|---|
| 1. Single DDB table | Less granular queries | High cardinality SK → expensive GSI |
| 2. Two monorepos | Less granular deps | Larger deploys |
| 3. DDB + Stream + Pipes | Extra latency | Stream ordering edge cases |
| 4. EventBridge Pipes | Extra hop | Quota limits (unlikely) |
| 5. Validation phase | Latency | Manual step required |
| 6. Python 3.11 Container | Cold start | Can be mitigated with reserved concurrency |
| 7. Conditional writes | Per-entity config | Silent failures if condition not written correctly |
| 8. Three phases naming | Internal confusion | Docs must be kept in sync |
| 9. KEM dependency | External failure | Fallback: skip CYCLE if KEM offline |
| 10. S3 samples | Infrastructure | Cross-account complexity |
