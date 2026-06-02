# Onboarding — Reading Order & Getting Started

Welcome to Kriptos Classifier v2. This guide walks you through the codebase step-by-step.

---

## 1. Architecture Overview (15 min)

**Start here.** Read [`ARCHITECTURE.md`](ARCHITECTURE.md) to understand:
- The 6-step critical path (agent scans → matches → validates → collects → anonymizes → classifies)
- System actors (Agent, Client UI, Backend, Signal Handler, Anonymizer, LLM, KEM)
- Data foundation (single DDB table, stream-based coordination)
- Key decisions and trade-offs

---

## 2. State Machine (15 min)

**Next:** Read [`architecture/STATE-MACHINE.md`](architecture/STATE-MACHINE.md) to learn:
- CYCLE state transitions (scanning → stations_complete → confirmed → phase2_collecting → complete)
- STATION state transitions (Fase 1 scan, Fase 2 sampling)
- REQUEST state transitions (requested → sent)
- Which Lambda triggers each transition
- Idempotency patterns (barrier flags, conditional writes)
- Debugging queries for hung cycles

---

## 3. Data Model (15 min)

**Then:** Read [`architecture/DATA-MODEL.md`](architecture/DATA-MODEL.md) to understand:
- DDB schema (PK=enterprise_id, SK multi-prefix)
- Entity definitions (CYCLE, STATION, REQUEST)
- Fields per state (what's populated when?)
- Example keys and rows
- TTL & cleanup policy
- Billing estimates

---

## 4. External Integrations (10 min)

**Next:** Read [`architecture/INTEGRATIONS.md`](architecture/INTEGRATIONS.md) to see:
- Signal Handler contract (pushes cycle payload to agent)
- Anonymizer contract (reads gse-raw, writes gse-anonymized)
- LLM queue contract (consumes closed cycles)
- KEM API contract (returns active stations)
- Bedrock keywords integration
- Status of each integration (stub, existing, manual)
- Fallback behavior if integration fails

---

## 5. Design Decisions (20 min)

**Then:** Read [`DECISIONS.md`](DECISIONS.md) to see the "why" behind each architectural choice:
- Why single DDB table (not 3 separate)?
- Why 2 monorepos (not 15)?
- Why DDB + Stream + Pipes (not Step Functions)?
- Why EventBridge Pipes (decoupling)?
- Why validation phase (compliance + accuracy)?
- Why Python 3.11 + Container (flexibility)?
- Trade-offs and risks for each decision

---

## 6. Ticket Map & Implementation Plan (20 min)

**Finally:** Read [`TICKETS-MAP.md`](TICKETS-MAP.md) to see:
- All 28 tickets organized by monorepo
- Which Lambda each ticket owns
- Infra dependencies (what blocks what?)
- Critical path timelines (Alpha → Beta → GA)
- Owner assignments per team

---

## For Different Roles

### Backend Developer (Python Lambda)

1. ARCHITECTURE.md (5 min)
2. STATE-MACHINE.md (10 min)
3. Dive into specific Lambda spec: `/specs-staging/fase-1-scan-match/` or `/specs-staging/fase-2-gse/`
4. Read DECISIONS.md (idempotency patterns)
5. Start coding in `classifier-scan-match-backend` or `classifier-gse-backend`

**Recommended first ticket:** KT-17001 (tree-url-generator) — simplest, no external deps

### DevOps/Platform

1. ARCHITECTURE.md (5 min)
2. STATE-MACHINE.md (10 min)
3. INTEGRATIONS.md (10 min)
4. Dive into `/specs-staging/infra/` folder
5. Review TICKETS-MAP.md (KT-17009-19, KT-17020-23, KT-17082-87)

**Recommended first ticket:** KT-17009 (ECR + IAM) — foundation for all Lambdas

### Frontend/Client (UI + GraphQL)

1. ARCHITECTURE.md (focus: Client role, critical path steps 3-4)
2. STATE-MACHINE.md (focus: CYCLE confirmed state)
3. DATA-MODEL.md (focus: CYCLE fields)
4. Dive into `/specs-staging/fase-1-validacion/`

**Recommended first ticket:** KT-17024 (crown-validation-handler) — GraphQL mutations

### Product/PM

1. ARCHITECTURE.md (entire overview)
2. DECISIONS.md (why decisions, trade-offs)
3. TICKETS-MAP.md (timeline, dependencies, owner assignments)
4. CHANGELOG.md (what changed in consolidation)

---

## Quick Reference: Lambda Ownership Map

### In `classifier-scan-match-backend`

| Lambda | Fase | Role | Complexity |
|---|---|---|---|
| tree-url-generator | 1 Scan | Validate + sign presigned URL | ⭐ Easy |
| tree-uncompressor | 1 Scan | Decompress .jsonl.gz | ⭐ Easy |
| emr-job-trigger | 1 Scan | Invoke EMR Serverless | ⭐ Easy |
| joyas-priorizer | 1 Scan | Match tree against keywords | ⭐⭐ Medium (EMR output parsing) |
| crown-candidates-indexer | 1 Barrier | Bulk-index to OpenSearch | ⭐⭐ Medium (OpenSearch API) |
| crown-enterprise-barrier | 1 Barrier | Wait for all stations → transition CYCLE | ⭐⭐⭐ Hard (conditional writes, barriers) |
| crown-validation-handler | 1 Validación | Handle GraphQL mutations | ⭐⭐⭐ Hard (UI state sync) |
| crown-validation-confirm | 1 Validación | Freeze candidates + write manifest | ⭐⭐⭐ Hard (manifest schema, S3) |

### In `classifier-gse-backend`

| Lambda | Fase | Role | Complexity |
|---|---|---|---|
| gse-cycle-init | 2 Init | Create STATION (Fase 2) + notify Signal Handler | ⭐⭐ Medium |
| gse-sample-reception-notifier | 2 Collection | Count samples arriving in gse-raw | ⭐ Easy |
| gse-request-complete | 2 Collection | Agent marks request done | ⭐ Easy |
| gse-sample-anonymizer-notifier | 2 Anonymization | Count anonymized samples | ⭐ Easy |
| gse-station-status | 2 Barrier | Wait for barrier → close STATION | ⭐⭐⭐ Hard (exactly-once barrier logic) |
| gse-enterprise-status | 2 Barrier | All STATIONs closed → notify LLM → complete CYCLE | ⭐⭐⭐ Hard (LLM notif, TTL) |

---

## Getting Started Locally

1. **Clone both monorepos:**
   ```bash
   git clone https://kriptos-team@gitlab.com/kriptos/classifier-scan-match-backend.git
   git clone https://kriptos-team@gitlab.com/kriptos/classifier-gse-backend.git
   ```

2. **Set up Python environment:**
   ```bash
   cd classifier-scan-match-backend
   python3.11 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

3. **Run tests:**
   ```bash
   pytest -v
   ruff check .
   mypy lambdas/
   ```

4. **Review Lambda specs:**
   - Fase 1: `/specs-staging/fase-1-scan-match/`
   - Fase 2: `/specs-staging/fase-2-gse/`
   - Infra: `/specs-staging/infra/`

5. **Check for your ticket:**
   - Search TICKETS-MAP.md for your ticket number
   - Find linked spec in `/specs-staging/`
   - Start implementing

---

## When Stuck

1. **"Which Lambda do I work on?"**
   → Check TICKETS-MAP.md, find your ticket, see Lambda name

2. **"How does my Lambda fit in the flow?"**
   → Read ARCHITECTURE.md, look for your Lambda name

3. **"What state does my Lambda read/write?"**
   → Read STATE-MACHINE.md, find "Transition Triggers by Lambda" table

4. **"What does the DDB schema look like?"**
   → Read DATA-MODEL.md, find entity (CYCLE/STATION/REQUEST)

5. **"What if my Lambda fails?"**
   → See INTEGRATIONS.md, "Fallback Strategy"

6. **"How do I debug a stuck cycle?"**
   → See STATE-MACHINE.md, "Monitoring & Debugging" section

7. **"Where's the spec for my Lambda?"**
   → See TICKETS-MAP.md, find your ticket, look under "Specs" column

---

## Glossary

| Term | Definition |
|---|---|
| **CYCLE** | Full scan+validate+sample journey for one enterprise |
| **STATION** | One workstation (PC/Mac/cloud agent) within a CYCLE |
| **REQUEST** | Sampling request for a specific request type (pii, financial, etc.) |
| **Fase 1 Scan+Match** | Agent scans → backend matches against keywords → outputs candidates |
| **Fase 1 Validación** | Client reviews candidates in UI → approves/rejects/edits |
| **Fase 2 GSE** | Agent collects samples → Anonymizer processes → LLM classifies |
| **Crown Jewels** | Matched candidates (matched against keywords) |
| **Barrier** | Condition that gate a state transition (e.g., all STATIONs must report complete) |
| **DDB Stream** | Change data capture stream from DynamoDB (feeds state Lambdas) |
| **EventBridge Pipes** | Filtering + routing layer between DDB Stream and Lambdas |
| **TTL** | Time-to-live; DDB auto-deletes rows after this Unix timestamp |

---

## FAQ

**Q: Where do I start if this is my first time?**  
A: Read the 6 sections above (1-6) in order. Takes about 1.5 hours.

**Q: Can I skip DECISIONS.md?**  
A: Not recommended. It explains *why* decisions were made, which helps you avoid second-guessing them.

**Q: Which monorepo should I contribute to?**  
A: Depends on your ticket. Fase 1 = `classifier-scan-match-backend`. Fase 2 = `classifier-gse-backend`. See TICKETS-MAP.md.

**Q: Where's the spec for my Lambda?**  
A: In `/specs-staging/`. Search by Lambda name (e.g., `tree-url-generator.md`).

**Q: How do I run tests locally?**  
A: `pytest -v` in the monorepo root. Each monorepo has a `tests/` folder.

**Q: What if I break the state machine?**  
A: Conditional writes prevent most bugs. Read idempotency patterns in STATE-MACHINE.md before coding.

---

## Next Steps

- **To start coding:** Pick the "Recommended first ticket" for your role above
- **To understand infra:** Read `/specs-staging/infra/` specs
- **To learn the product:** Ask PM for customer use-case docs
- **To ask questions:** Ping @haroldo on Slack or open a discussion in the repo
