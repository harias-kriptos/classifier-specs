# Implementation Status — Classifier Backend v2

> **Última actualización:** 2026-05-28
> **Source of truth para:** qué está implementado, qué está en spec, qué está en infra
> **Stack confirmado:** Python 3.11 + Lambda Container + ECR + **CloudFormation** + pytest/ruff/mypy

---

## Resumen

| Categoría | Total | Implemented | In progress | Spec only | % avance |
|---|---|---|---|---|---|
| **Dev tickets** (Lambdas) | 11 | **4** | 0 | 7 | 36% |
| **Infra tickets** | 15 | 0 | 0 | 15 | 0% |
| **Cleanup** | 1 | 0 | 0 | 1 | 0% |
| **Documentación** | 1 | 1 | 0 | 0 | 100% |
| **TOTAL** | 28 | 5 | 0 | 23 | 18% |

---

## ✅ Implementadas (4 Lambdas)

> Estas 4 Lambdas tienen código funcional. **Pendiente:** migrar a `classifier-scan-match-backend` monorepo (cleanup KT-17133).

| Ticket | Lambda | Repo actual | Estado | Pendiente |
|---|---|---|---|---|
| **KT-17001** | `tree-url-generator` | `kriptos-io/s3-tree-uploader` (legacy) | ✅ Funcional | Migrar a monorepo + CloudFormation |
| **KT-17002** | `tree-uncompressor` | `kriptos-io/tree-uncompressor` (legacy) | ✅ Funcional | Migrar a monorepo + CloudFormation |
| **KT-17003** | `emr-job-trigger` | `kriptos-io/emr-job-trigger` (legacy) | ✅ Funcional | Migrar a monorepo + CloudFormation |
| **KT-17004** | `joyas-priorizer` | (EMR Serverless, no Lambda) | ✅ Funcional | Migrar script + CloudFormation |

**Próximo paso:** Crear `classifier-scan-match-backend` (KT-17034) → migrar estas 4 → desactivar repos legacy (KT-17133).

---

## 📋 En Spec (sin código aún)

### Monorepo 1: `classifier-scan-match-backend`

| Ticket | Lambda | Status |
|---|---|---|
| KT-17005 | crown-candidates-indexer | 📋 Spec |
| KT-17006 | crown-enterprise-barrier | 📋 Spec |
| KT-17024 | crown-validation-handler | 📋 Spec |
| KT-17025 | crown-validation-confirm | 📋 Spec |

### Monorepo 2: `classifier-gse-backend`

| Ticket | Lambda | Status |
|---|---|---|
| KT-17028 | gse-cycle-init | 📋 Spec |
| KT-17029 | gse-sample-reception-notifier | 📋 Spec |
| KT-17030 | gse-request-complete | 📋 Spec |
| KT-17031 | gse-sample-anonymizer-notifier | 📋 Spec |
| KT-17032 | gse-station-status | 📋 Spec |
| KT-17033 | gse-enterprise-status | 📋 Spec |

---

## 🏗️ Infra (CloudFormation pendiente)

> Toda la infra de Fase 1 y Fase 2 está en spec. CloudFormation templates aún no creados.

### Fase 1 (KT-17009 a KT-17019)

| Ticket | Recurso | Status |
|---|---|---|
| KT-17009 | ECR + IAM Lambda execution role | 📋 Spec |
| KT-17010 | **DDB `classifier-cycles-state`** (crítico — bloqueador) | 📋 Spec |
| KT-17012 | OpenSearch cluster | 📋 Spec |
| KT-17013 | S3 buckets (compressed/decompressed/crown_jewels/validated) | 📋 Spec |
| KT-17014 | EMR Serverless app + IAM | 📋 Spec |
| KT-17015 | EventBridge Pipes (Stream filtering) | 📋 Spec |
| KT-17017 | GitLab CI/CD | 📋 Spec |
| KT-17018 | VPC + networking | 📋 Spec |
| KT-17019 | Secrets Manager (KEM API key) | 📋 Spec |

### Fase 2 (KT-17020 a KT-17023, KT-17082 a KT-17087)

| Ticket | Recurso | Status |
|---|---|---|
| KT-17020 | S3 buckets (gse-raw, gse-anonymized) | 📋 Spec |
| KT-17021 | SQS queues (reception → Anonymizer) | 📋 Spec |
| KT-17022 | EventBridge Pipes Fase 2 | 📋 Spec |
| KT-17023 | SNS Signal Handler integration | 📋 Spec |
| KT-17082 | S3 lifecycle policies (90d TTL) | 📋 Spec |
| KT-17083 | CloudWatch monitoring + alarms | 📋 Spec |
| KT-17084 | Lambda reserved concurrency | 📋 Spec |
| KT-17085 | DDB autoscaling | 📋 Spec |
| KT-17086 | VPC security groups Fase 2 | 📋 Spec |
| KT-17087 | mTLS certs para servicios externos | 📋 Spec |

---

## 🧹 Cleanup (KT-17133)

> **Bloqueado por:** migración de las 4 Lambdas funcionales al monorepo.

| Acción | Estado |
|---|---|
| Migrar código de `s3-tree-uploader` → monorepo | Pendiente |
| Migrar código de `tree-uncompressor` → monorepo | Pendiente |
| Migrar código de `emr-job-trigger` → monorepo | Pendiente |
| Migrar `joyas-priorizer` (EMR script) → monorepo | Pendiente |
| Archivar 4 repos legacy en GitLab | Pendiente |
| Actualizar CI/CD para apuntar al monorepo | Pendiente |
| Update referencias en specs viejas | Pendiente |

---

## 📚 Documentación (KT-17135) — ✅ COMPLETA

Documentos generados (2026-05-28):

| Documento | Path | Estado |
|---|---|---|
| Architecture overview | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | ✅ |
| State Machine detalle | [docs/architecture/STATE-MACHINE.md](docs/architecture/STATE-MACHINE.md) | ✅ |
| Data Model DDB | [docs/architecture/DATA-MODEL.md](docs/architecture/DATA-MODEL.md) | ✅ |
| Integraciones externas | [docs/architecture/INTEGRATIONS.md](docs/architecture/INTEGRATIONS.md) | ✅ |
| Decisiones (ADR) | [docs/DECISIONS.md](docs/DECISIONS.md) | ✅ |
| Mapa de tickets | [docs/TICKETS-MAP.md](docs/TICKETS-MAP.md) | ✅ |
| Onboarding | [docs/ONBOARDING.md](docs/ONBOARDING.md) | ✅ |
| Troubleshooting | [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | ✅ |
| Índice navegacional | [docs/README.md](docs/README.md) | ✅ |
| Diagrama global | [architecture-global.drawio](architecture-global.drawio) | ✅ |

---

## 🎯 Próximos hitos sugeridos

### Hito 1 — Foundation (bloqueador de todo)

**Objetivo:** crear infra mínima compartida + monorepo 1

1. **KT-17009** — Crear DDB `classifier-cycles-state` (CloudFormation)
2. **KT-17010** — Crear ECR + IAM execution role
3. **KT-17034** — Inicializar monorepo `classifier-scan-match-backend`
4. **Migrar las 4 Lambdas funcionales** al monorepo (cleanup KT-17133 parcial)

### Hito 2 — Fase 1 completa

5. KT-17005, KT-17006, KT-17024, KT-17025 → 4 Lambdas faltantes Fase 1
6. KT-17012-15, KT-17017-19 → infra Fase 1

### Hito 3 — Fase 2 completa

7. KT-17134 → inicializar monorepo 2
8. KT-17028-33 → 6 Lambdas Fase 2
9. KT-17020-23, KT-17082-87 → infra Fase 2

### Hito 4 — Cleanup final

10. KT-17133 — Cerrar repos legacy

---

## Notas

- **CloudFormation, no Terraform.** Confirmado 2026-05-28.
- **Python 3.11** confirmado para todas las Lambdas.
- **Container Image** (no ZIP) — ECR centralizado por monorepo.
- Las 4 Lambdas funcionales pueden seguir corriendo en producción mientras se migran; el cambio es transparente desde el punto de vista de S3/EventBridge.
