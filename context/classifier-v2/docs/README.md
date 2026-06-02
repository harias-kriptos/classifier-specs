# Classifier v2 Documentation Index

**Complete architecture documentation for Kriptos Classifier backend.**

---

## Quick Start

1. **¿Qué está implementado hoy?** → [STATUS.md](../STATUS.md) (snapshot 2026-05-28)
2. **New to the project?** → Start with [ONBOARDING.md](ONBOARDING.md) (1.5 hour read)
3. **Need to understand the flow?** → Read [ARCHITECTURE.md](ARCHITECTURE.md) (15 min)
4. **Debugging an issue?** → Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
5. **Want design rationale?** → See [DECISIONS.md](DECISIONS.md) (20 min)

---

## Core Architecture

| Document | Focus | Audience | Time |
|---|---|---|---|
| [**ARCHITECTURE.md**](ARCHITECTURE.md) | 6-step flow, actors, data foundation, key decisions | Everyone | 15 min |
| [**STATE-MACHINE.md**](architecture/STATE-MACHINE.md) | CYCLE/STATION/REQUEST state transitions, Lambda triggers | Backend, DevOps | 15 min |
| [**DATA-MODEL.md**](architecture/DATA-MODEL.md) | DDB schema, entities, indexes, examples | Backend, DevOps | 15 min |
| [**INTEGRATIONS.md**](architecture/INTEGRATIONS.md) | External systems contracts (Signal Handler, Anonymizer, LLM, KEM) | Backend, Platform teams | 10 min |

---

## Design & Planning

| Document | Focus | Audience | Time |
|---|---|---|---|
| [**DECISIONS.md**](DECISIONS.md) | Architectural decisions with trade-offs (10 decisions) | Architects, PMs, Tech leads | 20 min |
| [**TICKETS-MAP.md**](TICKETS-MAP.md) | 28 tickets organized by monorepo, timeline, dependencies | PMs, Team leads | 20 min |

---

## Getting Started

| Document | Focus | Audience | Time |
|---|---|---|---|
| [**ONBOARDING.md**](ONBOARDING.md) | Reading order, role-specific paths, first steps | Everyone (new dev priority) | 1.5 hours |
| [**TROUBLESHOOTING.md**](TROUBLESHOOTING.md) | 12 common issues + solutions + queries | On-call, Backend | Ref only |

---

## Context & Organization

| Document | Location | Purpose |
|---|---|---|
| CONSOLIDATION-INDEX.md | `../CONSOLIDATION-INDEX.md` | Executive summary: 28 tickets, 2 monorepos, 3 phases |
| CHANGELOG.md | `../CHANGELOG.md` | Historical consolidation from 15 repos → 2 monorepos |
| AUDIT-UPDATE-NEEDED.md | `../AUDIT-UPDATE-NEEDED.md` | 14+ context files needing updates (cross-reference) |

---

## Implementation Specs

Detailed specs for each Lambda and infra component are in:

- `/specs-staging/fase-1-scan-match/` (8 Lambdas: scan, match, barrier, validation)
- `/specs-staging/fase-1-validacion/` (2 Lambdas: UI mutations, confirm)
- `/specs-staging/fase-2-gse/` (6 Lambdas: collection, anonymization, barrier)
- `/specs-staging/infra/` (15 infra tickets: ECR, DDB, S3, EventBridge, etc.)

---

## Navigation by Role

### Backend Developer

1. ARCHITECTURE.md
2. STATE-MACHINE.md
3. Pick your Lambda spec in `/specs-staging/fase-*/`
4. DECISIONS.md (idempotency patterns)

**First ticket:** KT-17001 (tree-url-generator)

### DevOps/Platform

1. ARCHITECTURE.md
2. STATE-MACHINE.md
3. INTEGRATIONS.md
4. Pick infra spec in `/specs-staging/infra/`

**First ticket:** KT-17009 (ECR + IAM)

### Frontend/Client

1. ARCHITECTURE.md (focus Client role)
2. STATE-MACHINE.md (focus CYCLE.confirmed)
3. DATA-MODEL.md (focus CYCLE fields)
4. `/specs-staging/fase-1-validacion/`

**First ticket:** KT-17024 (crown-validation-handler)

### Product/PM

1. ARCHITECTURE.md
2. DECISIONS.md
3. TICKETS-MAP.md
4. CHANGELOG.md (context)

---

## Monorepos & Ownership

### `classifier-scan-match-backend` (KT-17034)

**Fase 1:** Scan → Match → Barrier → Validation

- Lambdas: tree-url-generator, tree-uncompressor, emr-job-trigger, joyas-priorizer, crown-candidates-indexer, crown-enterprise-barrier, crown-validation-handler, crown-validation-confirm
- Owner: Backend team + Plataforma Web
- Infra: KT-17009-19

### `classifier-gse-backend` (KT-17134)

**Fase 2:** Init → Collection → Anonymization → Barrier

- Lambdas: gse-cycle-init, gse-sample-reception-notifier, gse-request-complete, gse-sample-anonymizer-notifier, gse-station-status, gse-enterprise-status
- Owner: Backend team + Plataforma IA
- Infra: KT-17020-23, KT-17082-87

---

## Key Concepts

| Term | Definition | Where |
|---|---|---|
| CYCLE | Full scan→validate→sample journey per enterprise | STATE-MACHINE.md |
| STATION | One machine/cloud agent within a CYCLE | STATE-MACHINE.md |
| REQUEST | Sampling request for a specific type (pii, financial) | STATE-MACHINE.md |
| Fase 1 Scan+Match | Agent scans, backend matches | ARCHITECTURE.md |
| Fase 1 Validación | Client approves/rejects in UI | ARCHITECTURE.md |
| Fase 2 GSE | Agent collects, Anonymizer processes, LLM classifies | ARCHITECTURE.md |
| Barrier | Gate condition for state transition | STATE-MACHINE.md |
| Crown Jewels | Matched candidates | DATA-MODEL.md |
| DDB Stream | Change capture from DynamoDB | STATE-MACHINE.md |
| EventBridge Pipes | Filtering layer between Stream and Lambdas | DECISIONS.md |

---

## Debugging Cheatsheet

**Cycle stuck in `scanning`?** → See TROUBLESHOOTING.md #1  
**Cycle stuck in `stations_complete`?** → See TROUBLESHOOTING.md #2  
**Cycle stuck in `phase2_collecting`?** → See TROUBLESHOOTING.md #3  
**Request stuck in `requested`?** → See TROUBLESHOOTING.md #4  
**OpenSearch has no results?** → See TROUBLESHOOTING.md #5  
**Lambda timeout?** → See TROUBLESHOOTING.md #6  

[Full troubleshooting guide](TROUBLESHOOTING.md)

---

## Document Structure

```
classifier-v2/
├── docs/
│   ├── README.md (this file)
│   ├── ARCHITECTURE.md (AC01)
│   ├── DECISIONS.md (AC06)
│   ├── ONBOARDING.md (AC08)
│   ├── TICKETS-MAP.md (AC07)
│   ├── TROUBLESHOOTING.md (AC10)
│   ├── architecture/
│   │   ├── STATE-MACHINE.md (AC02)
│   │   ├── DATA-MODEL.md (AC03)
│   │   └── INTEGRATIONS.md (AC04)
│   └── (AC05 Diagrams are deferred to end)
├── CONSOLIDATION-INDEX.md
├── CHANGELOG.md
├── AUDIT-UPDATE-NEEDED.md
└── /specs-staging/
    ├── fase-1-scan-match/
    ├── fase-1-validacion/
    ├── fase-2-gse/
    └── infra/
```

---

## Generated From

**KT-17135 — Documentation: Architecture Consolidada**

- AC01: ARCHITECTURE.md ✅
- AC02: STATE-MACHINE.md ✅
- AC03: DATA-MODEL.md ✅
- AC04: INTEGRATIONS.md ✅
- AC05: Diagrams (deferred to end)
- AC06: DECISIONS.md ✅
- AC07: TICKETS-MAP.md ✅
- AC08: ONBOARDING.md ✅
- AC09: README updates (this file) ✅
- AC10: TROUBLESHOOTING.md ✅

**Last updated:** 2026-05-28
