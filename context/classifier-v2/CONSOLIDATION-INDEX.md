# 📋 INDEX — Consolidación Backend Classifier v2

> **Estado:** Finalizado 2026-05-28  
> **Resultado:** 26 tickets, 2 monorepos, 1 DDB consolidada

---

## 🎯 Quick Links

- **CHANGELOG completo:** [`CHANGELOG.md`](./CHANGELOG.md) — cambios arquitectónicos, tickets, decisiones
- **Dashboard visual:** [`dashboard.html`](./dashboard.html) — matriz de tickets + estado
- **DevOps brief:** [`devops-reunion.html`](./devops-reunion.html) — inventario infra + repos
- **Dev tickets:** [`dev-tickets.md`](./dev-tickets.md) — source-of-truth código
- **DevOps tickets:** [`devops-tickets.md`](./devops-tickets.md) — source-of-truth infra

---

## 📊 Números finales

| Categoría | Cantidad | Distribución |
|---|---|---|
| **Tickets dev** | 11 | 4 scan+match + 4 validación + 3 gse |
| **Tickets DevOps** | 15 | 3 shared + 8 scan-match-backend + 1 storage + 6 gse-backend |
| **Tickets cleanup** | 1 | KT-17133 (4 repos legacy) |
| **Tickets documentación** | 1 | KT-17135 (maestro) |
| **Total** | **28** | — |
| **Monorepos** | 2 | `classifier-scan-match-backend` (8 Lambdas) + `classifier-gse-backend` (6 Lambdas) |
| **DynamoDB tables** | 1 | `classifier-cycles-state` (consolidada) |
| **Repos legacy a cleanup** | 4 | s3-tree-uploader, tree-uncompressor, emr-job-trigger, joyas-priorizer |

---

## 🗂️ Estructura de monorepos

### **Monorepo 1: `classifier-scan-match-backend` (KT-17034)**

```
8 Lambdas:
  • tree-url-generator (KT-16612) ✅ deployed
  • tree-uncompressor (KT-16613) 🟡 WIP
  • emr-job-trigger (KT-16614) 🟡 WIP
  • joyas-priorizer (KT-16616) 🟡 WIP + MOD

  • crown-candidates-indexer (KT-17024) 📋 RFC
  • crown-enterprise-barrier (KT-17025) 📋 RFC
  • crown-validation-handler (KT-17026) 📋 RFC
  • crown-validation-confirm (KT-17027) 📋 RFC

DevOps tickets:
  • KT-16725, KT-16726 (existentes, refactor)
  • KT-16728 (EMR infra, done)
  • KT-17078, 17079, 17080, 17081 (4 nuevos, dentro de monorepo)
```

### **Monorepo 2: `classifier-gse-backend` (KT-17134)**

```
6 Lambdas:
  • gse-cycle-init (KT-17028) 📋 RFC
  • gse-sample-reception-notifier (KT-17029) 📋 RFC
  • gse-sample-anonymizer-notifier (KT-17030) 📋 RFC
  • gse-request-complete (KT-17031) 📋 RFC
  • gse-station-status (KT-17032) 📋 RFC
  • gse-enterprise-status (KT-17033) 📋 RFC

DevOps tickets:
  • KT-17017 (Storage: buckets + SQS)
  • KT-17082, 17083, 17084, 17085, 17086, 17087 (6 nuevos, dentro de monorepo)
```

---

## 🔄 State Machine único (DDB `classifier-cycles-state` — KT-17009)

```
scanning
  ↓ (cuando todas las stations reportan scan_status=complete)
  
stations_complete
  ↓ (cliente valida en UI)
  
confirmed
  ↓ (crown-validation-confirm cuando cliente da OK)
  
phase2_collecting
  ↓ (gse-station-status cuando todas las stations completaron sampling)
  
complete
  ↓ (gse-enterprise-status notifica al LLM)
  
[cycle cerrado + LLM procesa]
```

---

## 📋 Tickets por categoría

### **Shared Infrastructure (3)**

| Ticket | Recurso |
|---|---|
| [KT-17009](https://kriptosteam.atlassian.net/browse/KT-17009) | DDB `classifier-cycles-state` + Stream |
| [KT-17010](https://kriptosteam.atlassian.net/browse/KT-17010) | OpenSearch `crown_jewel_candidates` |
| [KT-16729](https://kriptosteam.atlassian.net/browse/KT-16729) | SNS `kriptos-backend-alerts` |

### **Fase 1 — Scan & Match (4 dev + 4 infra)**

| Dev | DevOps |
|---|---|
| [KT-16612](https://kriptosteam.atlassian.net/browse/KT-16612) tree-url-gen | [KT-16725](https://kriptosteam.atlassian.net/browse/KT-16725) |
| [KT-16613](https://kriptosteam.atlassian.net/browse/KT-16613) tree-uncomp | [KT-16726](https://kriptosteam.atlassian.net/browse/KT-16726) BLOCKED |
| [KT-16614](https://kriptosteam.atlassian.net/browse/KT-16614) emr-trigger | [KT-16728](https://kriptosteam.atlassian.net/browse/KT-16728) ✅ |
| [KT-16616](https://kriptosteam.atlassian.net/browse/KT-16616) joyas-prior | [KT-17034](https://kriptosteam.atlassian.net/browse/KT-17034) **MONOREPO** |

### **Fase 1 — Validación (4 dev + 4 infra dentro de monorepo)**

| Dev | DevOps |
|---|---|
| [KT-17024](https://kriptosteam.atlassian.net/browse/KT-17024) candidates-indexer | [KT-17078](https://kriptosteam.atlassian.net/browse/KT-17078) |
| [KT-17025](https://kriptosteam.atlassian.net/browse/KT-17025) enterprise-barrier | [KT-17079](https://kriptosteam.atlassian.net/browse/KT-17079) |
| [KT-17026](https://kriptosteam.atlassian.net/browse/KT-17026) mutation-handler | [KT-17080](https://kriptosteam.atlassian.net/browse/KT-17080) |
| [KT-17027](https://kriptosteam.atlassian.net/browse/KT-17027) crown-validation-confirm | [KT-17081](https://kriptosteam.atlassian.net/browse/KT-17081) |

### **Fase 2 — GSE (6 dev + 6 infra dentro de monorepo + 1 storage)**

| Dev | DevOps |
|---|---|
| [KT-17028](https://kriptosteam.atlassian.net/browse/KT-17028) cycle-init | [KT-17017](https://kriptosteam.atlassian.net/browse/KT-17017) Storage |
| [KT-17029](https://kriptosteam.atlassian.net/browse/KT-17029) reception-notifier | [KT-17082](https://kriptosteam.atlassian.net/browse/KT-17082) |
| [KT-17030](https://kriptosteam.atlassian.net/browse/KT-17030) anonymizer-notifier | [KT-17083](https://kriptosteam.atlassian.net/browse/KT-17083) |
| [KT-17031](https://kriptosteam.atlassian.net/browse/KT-17031) request-complete | [KT-17084](https://kriptosteam.atlassian.net/browse/KT-17084) |
| [KT-17032](https://kriptosteam.atlassian.net/browse/KT-17032) station-status | [KT-17085](https://kriptosteam.atlassian.net/browse/KT-17085) |
| [KT-17033](https://kriptosteam.atlassian.net/browse/KT-17033) enterprise-status | [KT-17086](https://kriptosteam.atlassian.net/browse/KT-17086) |
| — | [KT-17087](https://kriptosteam.atlassian.net/browse/KT-17087) |
| — | [KT-17134](https://kriptosteam.atlassian.net/browse/KT-17134) **MONOREPO** |

### **Cleanup & Documentation (2)**

| Ticket | Propósito |
|---|---|
| [KT-17133](https://kriptosteam.atlassian.net/browse/KT-17133) | Cleanup — 4 repos legacy |
| [KT-17135](https://kriptosteam.atlassian.net/browse/KT-17135) | Documentación maestro |

---

## 🎯 Decisiones clave

| Decisión | Ticket | Rationale |
|---|---|---|
| **DDB única** `classifier-cycles-state` | KT-17009 | Unifica estado Fase 1 + 2, elimina sincronización manual |
| **2 monorepos** (no 15 repos) | KT-17034, KT-17134 | Reduce CI/CD complexity, permite cambios cross-Lambda coherentes |
| **State machine único** | KT-17009 | Transiciones CYCLE visibles end-to-end (scanning → complete) |
| **CloudFormation centralizado** | Dentro de cada monorepo (carpeta `cloudformation/`) | Versionamiento coherente de infra con código |
| **Cleanup de 4 repos legacy** | KT-17133 | Post-migración a monorepos, evita deuda técnica |

---

## 📚 Documentación

| Documento | Responsable | Ticket |
|---|---|---|
| CHANGELOG.md (este índice) | Consolidación final | KT-17135 |
| ARCHITECTURE.md | Overview 6 pasos | KT-17135 |
| STATE-MACHINE.md | Transiciones detalladas | KT-17135 |
| DATA-MODEL.md | Schema DDB + ejemplos | KT-17135 |
| INTEGRATIONS.md | Cajas negras externas | KT-17135 |
| DECISIONS.md | ADR — rationale de cada decisión | KT-17135 |
| TICKETS-MAP.md | Matriz de 26 tickets | KT-17135 |
| ONBOARDING.md | Guía para nuevos devs | KT-17135 |

---

## ✅ Qué cambió desde el refresh (2026-05-19)

| Aspecto | Antes (mayo 19) | Después (mayo 28) | Cambio |
|---|---|---|---|
| **Estructura repo** | 15 repos separados | 2 monorepos | Simplificación 87% |
| **DDB tables** | 3 propuestas (fragmentadas) | 1 única | Unificación |
| **Lambdas diseñados** | 1 deployed | 14 en pipeline (11 nuevos) | +13 |
| **Tickets infra** | 6 | 15 | +9 infra coordinados |
| **Tickets cleanup** | 0 | 1 | KT-17133 |
| **Documentación** | Dispersa | 1 maestro (KT-17135) | Centralizada |

---

**Status:** ✅ Consolidación completa — todos los tickets mapeados, documentación lista  
**Próximo:** Skill 02 (spec técnica) para KT-17024/25/26/27 + infra dev de KT-17009
