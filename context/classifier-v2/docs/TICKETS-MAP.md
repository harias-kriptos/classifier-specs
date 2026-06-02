# Tickets Map — 28 Consolidados en 2 Monorepos

## Total: 28 tickets (11 dev + 15 infra + 1 cleanup + 1 docs)

> **Implementation Status (2026-05-28):** 5/28 done (18%). Ver [STATUS.md](../STATUS.md) para detalle.
>
> | Status | Cuenta | Tickets |
> |---|---|---|
> | ✅ Implemented | 5 | KT-17001, 17002, 17003, 17004 (Lambdas en legacy) + KT-17135 (docs) |
> | 📋 Spec | 23 | Todo lo demás (dev + infra + cleanup) |

---

## Monorepo 1: `classifier-scan-match-backend` (KT-17034)

### Fase 1 Scan+Match (Lambdas 1-3)

| Ticket | Lambda | Role | Status |
|---|---|---|---|
| KT-17001 | tree-url-generator | Validates agent request, signs presigned URL | ✅ **Implemented** (legacy repo · pending migration) |
| KT-17002 | tree-uncompressor | Decompresses .jsonl.gz, writes to decompressed_trees | ✅ **Implemented** (legacy repo · pending migration) |
| KT-17003 | emr-job-trigger | Invokes EMR Serverless job | ✅ **Implemented** (legacy repo · pending migration) |

### Fase 1 Match (Lambda 4)

| Ticket | Lambda | Role | Status |
|---|---|---|---|
| KT-17004 | joyas-priorizer | Matches tree against keywords, outputs crown_jewels.jsonl | ✅ **Implemented** (EMR script · pending migration) |

### Fase 1 Enterprise Barrier (Lambdas 5-6)

| Ticket | Lambda | Role | Status |
|---|---|---|---|
| KT-17005 | crown-candidates-indexer | Bulk-indexes candidates to OpenSearch, creates CYCLE+STATION | Ready |
| KT-17006 | crown-enterprise-barrier | Waits for all stations to report scan_status=complete, transitions CYCLE | Ready |

### Fase 1 Validación (Lambdas 7-8)

| Ticket | Lambda | Role | Status |
|---|---|---|---|
| KT-17024 | crown-validation-handler | Handles GraphQL mutations (approve/reject/override) | Dev |
| KT-17025 | crown-validation-confirm | Freezes validation, writes manifest, transitions CYCLE | Dev |

### Infra (Fase 1)

| Ticket | Component | Role | Status |
|---|---|---|---|
| KT-17009 | ECR + IAM | Lambda execution role + container registry | Infra |
| KT-17010 | DDB `classifier-cycles-state` | Single state table | Infra |
| KT-17012 | OpenSearch cluster | Candidate index (test fixture) | Infra |
| KT-17013 | S3 buckets | compressed_trees, decompressed_trees, crown_jewels, validated_crown_jewels | Infra |
| KT-17014 | EMR Serverless | Job cluster + IAM role | Infra |
| KT-17015 | EventBridge Pipes | STATION Stream filter → crown-enterprise-barrier | Infra |
| KT-17017 | GitLab CI/CD | Build, test, deploy (monorepo) | Infra |
| KT-17018 | VPC + networking | Lambda → OpenSearch, Lambda → EMR, Lambda → KEM | Infra |
| KT-17019 | Secrets Manager | KEM API key, Anonymizer endpoint | Infra |

---

## Monorepo 2: `classifier-gse-backend` (KT-17134)

### Fase 2 Collection (Lambdas 1-3)

| Ticket | Lambda | Role | Status |
|---|---|---|---|
| KT-17028 | gse-cycle-init | Reads manifest, creates STATION (Fase 2), notifies Signal Handler | Dev |
| KT-17029 | gse-sample-reception-notifier | Counts incoming samples in gse-raw | Dev |
| KT-17030 | gse-request-complete | Agent calls endpoint to mark request done | Dev |

### Fase 2 Anonymization (Lambda 4)

| Ticket | Lambda | Role | Status |
|---|---|---|---|
| KT-17031 | gse-sample-anonymizer-notifier | Counts anonymized samples in gse-anonymized | Dev |

### Fase 2 Enterprise Barrier (Lambdas 5-6)

| Ticket | Lambda | Role | Status |
|---|---|---|---|
| KT-17032 | gse-station-status | Waits for barrier (samples_anonymized + samples_skipped >= expected), closes STATION | Dev |
| KT-17033 | gse-enterprise-status | When all STATION closed, notifies LLM, sets TTL, transitions CYCLE → complete | Dev |

### Infra (Fase 2)

| Ticket | Component | Role | Status |
|---|---|---|---|
| KT-17020 | S3 buckets | gse-raw, gse-anonymized (phase 2) | Infra |
| KT-17021 | SQS queues | gse-sample-reception-queue (Anonymizer notifications) | Infra |
| KT-17022 | EventBridge Pipes | STATION Stream filter → gse-station-status, gse-sample-anonymizer-notifier | Infra |
| KT-17023 | SNS topics | Signal Handler integration (TBD channel) | Infra |
| KT-17082 | Lifecycle policies | S3 delete after 90d | Infra |
| KT-17083 | CloudWatch monitoring | Cycle metrics, stuck detection | Infra |
| KT-17084 | Lambda reserved concurrency | Per-Lambda | Infra |
| KT-17085 | DDB autoscaling | If throughput spikes | Infra |
| KT-17086 | VPC security groups | Phase 2 Lambda → Anonymizer, → Signal Handler | Infra |
| KT-17087 | Certificate management | mTLS to external services | Infra |

---

## Cross-cutting

| Ticket | Item | Status |
|---|---|---|
| **KT-17133** | **Cleanup:** Update legacy context, consolidate tickets, organize folder structure | **Admin** |
| **KT-17135** | **Documentation:** Architecture (AC01-AC10), ADRs, onboarding, troubleshooting | **Docs** |

---

## Ticket Dependencies

### Critical Path (Fase 1)

```
KT-17001 (tree-url-gen)
  ↓
KT-17002 (tree-uncomp)
  ↓
KT-17003 (emr-trigger)
  ↓
KT-17004 (joyas-priorizer)
  ↓
KT-17005 (crown-candidates-indexer)
  ↓
KT-17006 (crown-enterprise-barrier)
  ↓
KT-17024 (crown-validation-handler)
KT-17025 (crown-validation-confirm)
```

### Critical Path (Fase 2)

```
KT-17025 (crown-validation-confirm)
  ↓
KT-17028 (gse-cycle-init)
  ↓
KT-17029 (gse-sample-reception-notifier)
  ↓
KT-17031 (gse-sample-anonymizer-notifier)
  ↓
KT-17032 (gse-station-status)
  ↓
KT-17033 (gse-enterprise-status)
```

### Infra Blockers

| Phase | Blocker | Blocked by |
|---|---|---|
| Fase 1 | All Lambdas | KT-17009 (ECR), KT-17010 (DDB) |
| Fase 1 Validation | crown-validation-confirm | KT-17013 (S3 manifest bucket) |
| Fase 2 | All Lambdas | KT-17020 (S3 gse-raw/anonymized), KT-17021 (SQS) |
| Monitoring | Alerts | KT-17083 (CloudWatch) |

---

## Timeline (Estimated)

### Alpha (Fase 1 only)

| Phase | Start | Duration | Tickets |
|---|---|---|---|
| Week 1-2 | 2026-06-02 | 2w | Monorepo setup (KT-17034), basic Lambdas (KT-17001-06) |
| Week 3 | 2026-06-16 | 1w | Validación (KT-17024-25), infra (KT-17009-19) |
| **Alpha ready** | 2026-06-23 | — | Fase 1 on staging with test data |

### Beta (Fase 2)

| Phase | Start | Duration | Tickets |
|---|---|---|---|
| Week 4-5 | 2026-06-30 | 2w | Monorepo setup (KT-17134), Lambdas (KT-17028-33), infra (KT-17020-23, KT-17082-87) |
| Week 6 | 2026-07-14 | 1w | Integration tests, Signal Handler stub, Anonymizer stub |
| **Beta ready** | 2026-07-21 | — | Fase 1+2 on staging; integration with Signal Handler + Anonymizer |

### Production

| Phase | Start | Blocker |
|---|---|---|
| Fase 1 GA | 2026-08-01 | Compliance review, load testing |
| Fase 2 GA | 2026-09-01 | Signal Handler + Anonymizer production-ready |

---

## Ticket Details (Linked to Specs)

Each ticket maps to one or more spec files:

| Ticket | Specs |
|---|---|
| KT-17001-03 | `/specs-staging/fase-1-scan-match/tree-*.md` |
| KT-17004 | `/specs-staging/fase-1-scan-match/joyas-priorizer.md` |
| KT-17005-06 | `/specs-staging/fase-1-scan-match/barrier-*.md` |
| KT-17024-25 | `/specs-staging/fase-1-validacion/*.md` |
| KT-17009-19 | `/specs-staging/infra/fase-1-*.md` |
| KT-17028-33 | `/specs-staging/fase-2-gse/*.md` |
| KT-17020-23, 82-87 | `/specs-staging/infra/fase-2-*.md` |
| KT-17133 | `CONSOLIDATION-INDEX.md`, `CHANGELOG.md`, `AUDIT-UPDATE-NEEDED.md` |
| KT-17135 | `ARCHITECTURE.md`, `STATE-MACHINE.md`, `DATA-MODEL.md`, `INTEGRATIONS.md`, `DECISIONS.md`, `ONBOARDING.md`, `TROUBLESHOOTING.md` |

---

## Owner Assignments

### Fase 1 Scan+Match (`classifier-scan-match-backend`)

| Owner | Tickets |
|---|---|
| Backend team | KT-17001-06 (Lambdas) |
| Plataforma Web | KT-17024-25 (Validación UI + GraphQL) |
| DevOps | KT-17009-19 (Infra) |

### Fase 2 GSE (`classifier-gse-backend`)

| Owner | Tickets |
|---|---|
| Backend team | KT-17028-33 (Lambdas) |
| Plataforma IA | KT-17031 (Anonymizer integration) |
| DevOps | KT-17020-23, 82-87 (Infra) |

### Admin

| Owner | Tickets |
|---|---|
| Haroldo | KT-17133 (Cleanup), KT-17135 (Docs) |
