# Architecture — Backend Classifier v2

## Overview

The Classifier backend is a distributed, event-driven system that processes enterprise file systems end-to-end: scans machines/cloud sources, identifies sensitive files ("crown jewels"), collects samples, anonymizes them, and classifies via LLM.

**6-step flow:**
1. **Agent scans** filesystem → uploads tree to S3
2. **Backend matches** against keywords → outputs candidates
3. **Client validates** in web UI (approve/reject/override)
4. **Backend confirms** validation → materializes samples
5. **Agent collects** samples → uploads to S3
6. **LLM classifies** → final labels applied

---

## System Actors

| Actor | Role | Interface |
|---|---|---|
| **Agent (PC)** | Scans Windows/Mac/Linux/FileServer, extracts samples | HTTP `/v2/tree/init`, `/v2/gse/request-complete`, S3 PUT |
| **Agent (Cloud)** | Scans OneDrive/SharePoint/Google, same as PC but via cloud APIs | HTTP endpoints, S3 IAM role |
| **Client (Web UI)** | Validates candidates, approves/rejects, confirms Fase 2 | GraphQL (AppSync), OpenSearch queries |
| **Backend (Lambda + DDB)** | Orchestrates state machine, notifies external systems | SQS, EventBridge, DDB Stream |
| **External: Signal Handler** | Pushes cycle payload to agent | TBD channel (SNS/SQS/HTTP) |
| **External: Anonymizer** | Reads gse-raw, writes gse-anonymized | S3 buckets + SQS notifications |
| **External: LLM** | Consumes classified cycle, produces labels | TBD channel |
| **External: KEM** | Returns active stations per enterprise | HTTP `/v2/kem/stations` |

---

## Critical Path

```
Agent scans (1)
    ↓
tree-url-generator validates + signs presigned URL
    ↓
Agent uploads .jsonl.gz to S3 (compressed_trees)
    ↓
tree-uncompressor decompresses → decompressed_trees
    ↓
emr-job-trigger invokes EMR Serverless job
    ↓
joyas-priorizer matches keywords → crown_jewels.jsonl
    ↓
crown-candidates-indexer bulk-indexes to OpenSearch
    ↓
crown-enterprise-barrier counts stations → ready for validation
    ↓
Client validates in UI (crown-validation-handler mutations)
    ↓
crown-validation-confirm freezes set + writes manifest (validated_crown_jewels)
    ↓
gse-cycle-init receives manifest → transitionS CYCLE to phase2_collecting
    ↓
Signal Handler pushes payload to agent
    ↓
Agent extracts samples → uploads to gse-raw
    ↓
gse-sample-reception-notifier counts samples
    ↓
Anonymizer processes → writes gse-anonymized
    ↓
gse-sample-anonymizer-notifier counts anonymized
    ↓
gse-station-status closes STATION
    ↓
gse-enterprise-status closes CYCLE → notifies LLM
    ↓
LLM classifies → final labels
```

---

## Data Foundation

**Single DynamoDB table:** `classifier-cycles-state`
- **PK:** `enterprise_id` (String)
- **SK:** Multi-prefix (CYCLE#, STATION#, REQUEST#)
- **Stream:** `NEW_AND_OLD_IMAGES` feeds state lambdas

**Example keys:**
```
PK: ent-001, SK: CYCLE#uuid-1 → CYCLE entity (scanning → stations_complete → confirmed → phase2_collecting → complete)
PK: ent-001, SK: STATION#uuid-1#cycle-id → STATION entity (status, samples_expected, samples_received, etc.)
PK: ent-001, SK: REQUEST#uuid-1#cycle-id → REQUEST entity (status, samples_uploaded, samples_skipped)
```

---

## Key Decisions

| Decision | Trade-off | Why |
|---|---|---|
| **DDB single-table** | All state in one table, shared between Fase 1 & 2 | Unified state machine, no sync bottleneck between phases |
| **2 monorepos** (not 15) | Less granular, more cohesion | Reduces CI/CD complexity, enables cross-Lambda changes consistently |
| **State machine in DDB + DDB Stream** | No complex orchestration service (Step Functions) | Cost, simplicity, native AWS, latency < 1s |
| **EventBridge Pipes (not direct Lambda)** | Extra hop | Decouples Lambda from DDB Stream, allows filtering, retries, DLQ |
| **Validation phase** (not skipped) | Extra step before Fase 2 | Client knows what's being processed, can approve/reject/override |

---

## Repos & Deployment

| Repo | Lambdas | Owner |
|---|---|---|
| `classifier-scan-match-backend` | tree-url-gen, tree-uncomp, emr-trigger, joyas-prior, crown-candidates-indexer, crown-enterprise-barrier, crown-validation-handler, crown-validation-confirm | Backend team |
| `classifier-gse-backend` | gse-cycle-init, gse-sample-reception-notifier, gse-sample-anonymizer-notifier, gse-request-complete, gse-station-status, gse-enterprise-status | Backend team |

**Stack:** Python 3.11, Lambda Container Image, ECR, **CloudFormation**, pytest, ruff, mypy.

---

## For Deep Dives

- **State machine:** See `docs/architecture/STATE-MACHINE.md`
- **Data model:** See `docs/architecture/DATA-MODEL.md`
- **External integrations:** See `docs/architecture/INTEGRATIONS.md`
- **Design decisions:** See `docs/DECISIONS.md`
- **Ticket map:** See `docs/TICKETS-MAP.md`
- **Onboarding:** See `docs/ONBOARDING.md`
- **Troubleshooting:** See `docs/TROUBLESHOOTING.md`
