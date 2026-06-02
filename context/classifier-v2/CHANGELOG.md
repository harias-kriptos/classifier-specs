# CHANGELOG — Backend Classifier v2 Consolidation

> **Período:** 2026-05-19 (architecture refresh) → 2026-05-28 (final consolidation)  
> **Owner:** Haroldo Arias Molina  
> **Resultado:** 2 monorepos consolidados, 15 tickets DevOps, 1 DDB compartida

---

## 📊 Resumen ejecutivo

| Métrica | Antes | Después | Cambio |
|---|---|---|---|
| **Repos GitHub** | 4 existentes (s3-tree-uploader, tree-uncompressor, emr-job-trigger, unlockstack) | 2 nuevos monorepos (classifier-scan-match-backend, classifier-gse-backend) | ➕ 2 monorepos, 4 repos legacy marcados para cleanup |
| **Lambdas** | 1 deployed (tree-url-generator) | 14 totales en diseño (4 scan+match, 4 validación, 6 gse) | ➕ 13 nuevos en pipeline |
| **DynamoDB tables** | Múltiples propuestas (crown-validation-state, gse-cycles-samples) | 1 única: `classifier-cycles-state` | ➖ Consolidación — eliminó fragmentación |
| **DevOps tickets** | 6 existentes (KT-16725 a 16729 + KT-17034) | 15 nuevos (KT-17009 + 17010 + 17012-15 + 17017-23 + 17082-87) + 1 cleanup (KT-17133) | ➕ 16 tickets infra activos |
| **Monorepo structure** | Repos separados por componente | 2 monorepos + **CloudFormation** compartido | ✅ Simplificación — menos repos, más coherencia |
| **State machine** | Fragmentado (Fase 1, Fase 1.5, Fase 2 separadas) | Único CYCLE state machine (scanning → stations_complete → confirmed → phase2_collecting → complete) | ✅ Unificación — visibilidad end-to-end |

---

## 🎯 Decisiones clave (Hitos)

### **2026-05-19 — Architecture Refresh**
- **Decisión:** Unificar Fase 1 (scan + match + validación) en una sola DDB
- **Razón:** El estado de validación afecta a Fase 2; mantenerlo separado = sincronización manual
- **Resultado:** DDB única `classifier-cycles-state` con PK=enterprise_id, SK multi-prefix (CYCLE#, STATION#, REQUEST#)
- **Ticket:** KT-17009

### **2026-05-22 — Monorepo Strategy**
- **Decisión:** 2 monorepos en lugar de 15 repos separados
  - Monorepo 1: `classifier-scan-match-backend` (8 Lambdas: 4 scan+match + 4 validación)
  - Monorepo 2: `classifier-gse-backend` (6 Lambdas GSE + storage config)
- **Razón:** 
  - Reduce complejidad de CI/CD (2 pipelines vs 15)
  - Facilita cambios cross-Lambda (validación afecta a GSE)
  - **CloudFormation** + deps compartidas en un lugar
  - Desacoplamiento entre Fase 1 y Fase 2 sigue siendo posible (2 repos ≠ 1 repo)
- **Tickets:** KT-17034 (scan-match-backend), KT-17134 (gse-backend)

### **2026-05-28 — Cleanup & Documentation**
- **Decisión:** Marcar 4 repos legacy para cleanup post-migration
  - `kriptos-io/s3-tree-uploader` → código migrará a classifier-scan-match-backend
  - `kriptos-io/tree-uncompressor` → idem
  - `kriptos-io/emr-job-trigger` → idem
  - `kriptos-io/joyas-priorizer` → idem (follow-up KT-17034)
- **Ticket:** KT-17133
- **Documentación maestro:** KT-17135 (ARCHITECTURE.md, STATE-MACHINE.md, DATA-MODEL.md, etc.)

---

## 📋 Tickets creados / modificados

### **Shared Infrastructure**

| Ticket | Recurso | Status | Cambio desde ref anterior |
|---|---|---|---|
| [KT-17009](https://kriptosteam.atlassian.net/browse/KT-17009) | DDB `classifier-cycles-state` + Stream | 📋 RFC | ⭐ NUEVO — consolida `crown-validation-state` + `gse-cycles-samples` |
| [KT-17010](https://kriptosteam.atlassian.net/browse/KT-17010) | OpenSearch índice `crown_jewel_candidates` | 📋 RFC | ⭐ NUEVO |
| [KT-16729](https://kriptosteam.atlassian.net/browse/KT-16729) | SNS `kriptos-backend-alerts` | 📋 RFC | Existente, sin cambios |

### **Fase 1 — Monorepo `classifier-scan-match-backend` (KT-17034)**

| Ticket | Componente | Type | Status | Cambio |
|---|---|---|---|---|
| KT-16612 | tree-url-generator | Dev | ✅ DEPLOYED | Existente, será incluido en monorepo |
| KT-16613 | tree-uncompressor | Dev | 🟡 WIP | Existente, será incluido en monorepo |
| KT-16614 | emr-job-trigger | Dev | 🟡 WIP | Existente, será incluido en monorepo |
| KT-16616 | joyas-priorizer | Dev | 🟡 WIP + MOD | Existente + MOD aplicado (JSONL, Aho-Corasick) |
| [KT-17024](https://kriptosteam.atlassian.net/browse/KT-17024) | crown-candidates-indexer | Dev | 📋 RFC | ⭐ NUEVO — validación Fase 1 |
| [KT-17025](https://kriptosteam.atlassian.net/browse/KT-17025) | crown-enterprise-barrier | Dev | 📋 RFC | ⭐ NUEVO — state lambda validación |
| [KT-17026](https://kriptosteam.atlassian.net/browse/KT-17026) | crown-validation-handler | Dev | 📋 RFC | ⭐ NUEVO — AppSync mutations |
| [KT-17027](https://kriptosteam.atlassian.net/browse/KT-17027) | crown-validation-confirm | Dev | 📋 RFC | ⭐ NUEVO — freeze validación + dispara Fase 2 |
| [KT-16725](https://kriptosteam.atlassian.net/browse/KT-16725) | tree-url-generator infra | DevOps | 🟡 WIP | Existente, refactorizado dentro de monorepo |
| [KT-16726](https://kriptosteam.atlassian.net/browse/KT-16726) | tree-uncompressor + emr-job-trigger infra | DevOps | 🔴 BLOCKED | Existente, refactorizado dentro de monorepo |
| [KT-16728](https://kriptosteam.atlassian.net/browse/KT-16728) | joyas-priorizer infra (EMR) | DevOps | ✅ DONE | Existente, repo pendiente en KT-17034 |
| [KT-17034](https://kriptosteam.atlassian.net/browse/KT-17034) | **Monorepo scan-match-backend** | DevOps | 📋 RFC | ⭐ NUEVO — consolida 4 repos en 1 monorepo |
| [KT-17078](https://kriptosteam.atlassian.net/browse/KT-17078) | crown-candidates-indexer infra | DevOps | 📋 RFC | ⭐ NUEVO — dentro de monorepo |
| [KT-17079](https://kriptosteam.atlassian.net/browse/KT-17079) | crown-enterprise-barrier infra | DevOps | 📋 RFC | ⭐ NUEVO — dentro de monorepo |
| [KT-17080](https://kriptosteam.atlassian.net/browse/KT-17080) | crown-validation-handler infra | DevOps | 📋 RFC | ⭐ NUEVO — dentro de monorepo |
| [KT-17081](https://kriptosteam.atlassian.net/browse/KT-17081) | crown-validation-confirm infra | DevOps | 📋 RFC | ⭐ NUEVO — dentro de monorepo |

### **Fase 2 — Monorepo `classifier-gse-backend` (KT-17134)**

| Ticket | Componente | Type | Status | Cambio |
|---|---|---|---|---|
| [KT-17017](https://kriptosteam.atlassian.net/browse/KT-17017) | Storage (buckets + SQS) | DevOps | 📋 RFC | ⭐ NUEVO — gse-raw, gse-anonymized |
| [KT-17028](https://kriptosteam.atlassian.net/browse/KT-17028) | gse-cycle-init | Dev | 📋 RFC | ⭐ NUEVO |
| [KT-17029](https://kriptosteam.atlassian.net/browse/KT-17029) | gse-sample-reception-notifier | Dev | 📋 RFC | ⭐ NUEVO |
| [KT-17030](https://kriptosteam.atlassian.net/browse/KT-17030) | gse-sample-anonymizer-notifier | Dev | 📋 RFC | ⭐ NUEVO |
| [KT-17031](https://kriptosteam.atlassian.net/browse/KT-17031) | gse-request-complete | Dev | 📋 RFC | ⭐ NUEVO |
| [KT-17032](https://kriptosteam.atlassian.net/browse/KT-17032) | gse-station-status | Dev | 📋 RFC | ⭐ NUEVO |
| [KT-17033](https://kriptosteam.atlassian.net/browse/KT-17033) | gse-enterprise-status | Dev | 📋 RFC | ⭐ NUEVO |
| [KT-17082](https://kriptosteam.atlassian.net/browse/KT-17082) | gse-cycle-init infra | DevOps | 📋 RFC | ⭐ NUEVO — dentro de monorepo |
| [KT-17083](https://kriptosteam.atlassian.net/browse/KT-17083) | gse-sample-reception-notifier infra | DevOps | 📋 RFC | ⭐ NUEVO — dentro de monorepo |
| [KT-17084](https://kriptosteam.atlassian.net/browse/KT-17084) | gse-sample-anonymizer-notifier infra | DevOps | 📋 RFC | ⭐ NUEVO — dentro de monorepo |
| [KT-17085](https://kriptosteam.atlassian.net/browse/KT-17085) | gse-request-complete infra | DevOps | 📋 RFC | ⭐ NUEVO — dentro de monorepo |
| [KT-17086](https://kriptosteam.atlassian.net/browse/KT-17086) | gse-station-status infra | DevOps | 📋 RFC | ⭐ NUEVO — dentro de monorepo |
| [KT-17087](https://kriptosteam.atlassian.net/browse/KT-17087) | gse-enterprise-status infra | DevOps | 📋 RFC | ⭐ NUEVO — dentro de monorepo |
| [KT-17134](https://kriptosteam.atlassian.net/browse/KT-17134) | **Monorepo gse-backend** | DevOps | 📋 RFC | ⭐ NUEVO — consolida 6 Lambdas + storage en 1 monorepo |

### **Cleanup & Documentation**

| Ticket | Componente | Type | Status | Cambio |
|---|---|---|---|---|
| [KT-17133](https://kriptosteam.atlassian.net/browse/KT-17133) | Cleanup — Borrar repos legacy | DevOps | 📋 RFC | ⭐ NUEVO — s3-tree-uploader, tree-uncompressor, emr-job-trigger, joyas-priorizer |
| [KT-17135](https://kriptosteam.atlassian.net/browse/KT-17135) | **Documentación maestro** | Docs | 📋 RFC | ⭐ NUEVO — ARCHITECTURE.md, STATE-MACHINE.md, DATA-MODEL.md, etc. |

---

## 🎨 Archivos contexto actualizados

| Archivo | Cambios | Fecha |
|---|---|---|
| `context/classifier-v2/dashboard.html` | Agregados KT-17024/25/26/27 (validación) + KT-17017/28-33 (Fase 2) + KT-17009 (DDB) + KT-17133 (cleanup) + KT-17135 (docs) | 2026-05-28 |
| `context/classifier-v2/devops-reunion.html` | Agregados 15 tickets DevOps nuevos + consolidación en 2 monorepos | 2026-05-28 |
| `context/classifier-v2/dev-tickets.md` | Agregados 11 tickets dev nuevos (validación + GSE) | 2026-05-28 |
| `context/classifier-v2/devops-tickets.md` | Agregados 16 tickets DevOps nuevos + refactorización de AC01 (crear repo → monorepo) | 2026-05-28 |
| `memory/project_kriptos_classifier_tickets_status.md` | Consolidado estado actual (Fase 1 cleanup + dev/infra, Fase 2 11 tickets) | 2026-05-28 |

---

## 🔄 Cambios arquitectónicos

### **De:** Múltiples repos + fragmentación de estado
```
repos/
├── s3-tree-uploader/ (KT-16612)
├── tree-uncompressor/ (KT-16613)
├── emr-job-trigger/ (KT-16614)
├── joyas-priorizer/ (KT-16616)
├── crown-candidates-indexer/ (KT-17024)
├── crown-enterprise-barrier/ (KT-17025)
├── crown-validation-handler/ (KT-17026)
├── crown-validation-confirm/ (KT-17027)
├── gse-cycle-init/ (KT-17028)
├── gse-sample-reception-notifier/ (KT-17029)
├── gse-sample-anonymizer-notifier/ (KT-17030)
├── gse-request-complete/ (KT-17031)
├── gse-station-status/ (KT-17032)
└── gse-enterprise-status/ (KT-17033)

ddb/
├── crown-validation-state (Fase 1 validación)
└── gse-cycles-samples (Fase 2)
```

### **A:** 2 monorepos + DDB única
```
repos/
├── classifier-scan-match-backend/ (KT-17034)
│   ├── lambdas/tree-url-generator/
│   ├── lambdas/tree-uncompressor/
│   ├── lambdas/emr-job-trigger/
│   ├── lambdas/joyas-priorizer/
│   ├── lambdas/crown-candidates-indexer/
│   ├── lambdas/crown-enterprise-barrier/
│   ├── lambdas/crown-validation-handler/
│   ├── lambdas/crown-validation-confirm/
│   ├── src/domain/
│   ├── src/adapters/
│   └── cloudformation/
│
└── classifier-gse-backend/ (KT-17134)
    ├── lambdas/gse-cycle-init/
    ├── lambdas/gse-sample-reception-notifier/
    ├── lambdas/gse-sample-anonymizer-notifier/
    ├── lambdas/gse-request-complete/
    ├── lambdas/gse-station-status/
    ├── lambdas/gse-enterprise-status/
    ├── src/domain/
    ├── src/adapters/
    └── cloudformation/

ddb/
└── classifier-cycles-state (Fase 1 + 2 compartida)
```

---

## 📈 Impacto

### ✅ Ganancia

| Aspecto | Antes | Después | Beneficio |
|---|---|---|---|
| **Repos a mantener** | 15 | 2 + cleanup de 4 legacy | ➖ 87% menos repos en vuelo |
| **Dependencias compartidas** | Esparcidas (cada repo su pyproject.toml) | Centralizadas (1 pyproject.toml por monorepo) | ✅ Versionamiento coherente |
| **CloudFormation** | Esparcido (14 repos con su `cloudformation/`) | Centralizado (1 `cloudformation/` por monorepo) | ✅ Auditoría simplificada |
| **Cambios cross-Lambda** | 15 PRs separadas | 1 PR por monorepo | ✅ Coherencia garantizada |
| **CI/CD pipelines** | 15 workflows | 2 workflows (dev + prod reutilizable) | ✅ Mantenimiento simplificado |
| **State machine visibilidad** | Fragmentada (CYCLE en Fase 1, STATION en Fase 2) | Única DDB, transiciones claras | ✅ Debugging simplificado |

### ⚠️ Trade-off

| Aspecto | Trade-off |
|---|---|
| **Desacoplamiento** | 2 monorepos ≠ 1 repo. Aún se puede trabajar independientemente, pero cambios a DDB requieren coord |
| **Deploy granular** | No se puede deployar solo 1 Lambda sin el resto del monorepo. Mitigación: múltiples Dockerfiles, deploy por Lambda en CloudFormation nested stacks |
| **Repo size** | 8 Lambdas + 1 repo = más grandes que repos separados. Mitigación: es manageable (comparable a AWS SAM projects) |

---

## 📚 Documentación generada

| Documento | Propósito | Ticket |
|---|---|---|
| `context/classifier-v2/CHANGELOG.md` | Este documento | KT-17135 |
| `docs/ARCHITECTURE.md` | Overview del sistema (6 pasos) | KT-17135 |
| `docs/architecture/STATE-MACHINE.md` | Transiciones de CYCLE, STATION, REQUEST | KT-17135 |
| `docs/architecture/DATA-MODEL.md` | Schema DDB + ejemplos | KT-17135 |
| `docs/architecture/INTEGRATIONS.md` | Cajas negras (Signal Handler, Anonymizer, LLM, KEM) | KT-17135 |
| `docs/DECISIONS.md` | ADR: por qué cada decisión arquitectónica | KT-17135 |
| `docs/TICKETS-MAP.md` | Matriz de 26 tickets (dev + infra) | KT-17135 |
| `docs/ONBOARDING.md` | Guía para nuevos desarrolladores | KT-17135 |
| `docs/TROUBLESHOOTING.md` | Q&A comunes | KT-17135 |

---

## ✅ Próximos pasos

1. **Sprint dev:** Skill 02 (spec detallada) + Skill 03 (plan técnico) para KT-17024/25/26/27 en paralelo
2. **Sprint infra:** KT-17009 (DDB) → KT-17034 (monorepo scan-match) en paralelo
3. **Monorepo 2:** KT-17134 (monorepo gse) cuando Monorepo 1 esté deployado en dev
4. **Cleanup:** KT-17133 después de que código migrara a monorepos
5. **Documentación:** KT-17135 en paralelo o al cierre de Monorepo 1

---

**Generado por:** Consolidación arquitectónica 2026-05-28  
**Owner:** Haroldo Arias Molina  
**Épica padre:** [KT-16369](https://kriptosteam.atlassian.net/browse/KT-16369)
