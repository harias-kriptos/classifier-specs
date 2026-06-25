# Dev Tickets — histórico del refresh (2026-05)

> ⚠️ **Estado actual del backend → [`STATUS.md`](STATUS.md).** El 2026-06-02 se reorganizó todo en **3 épicas** (🔍 Discovery KT-16369 · ⚙️ Máquina de Estados KT-17270 · 📦 GSE KT-16370) + 1 futura (Validación), con **un monorepo por módulo** e **infra dentro de cada entregable** (sin tickets DevOps sueltos). Los lambdas `gse-cycle-init/station-status/enterprise-status` se renombraron a `state-*`. Este documento conserva el detalle histórico del refresh; varios status/épicas de acá quedaron desactualizados.
>
> **Última actualización:** 2026-05-19.
> **Owner:** Haroldo Arias Molina.
> **Para:** futuras sesiones de Claude / cualquier persona que se sume al backend del Classifier.
>
> Esta es la vista consolidada de **tickets de CÓDIGO** del backend del Classifier. Para infra/DevOps, ver [devops-tickets.md](devops-tickets.md) (inventario activo con status existe / verificar / MOD / nuevo). El documento original [orquestacion-backend.md](orquestacion-backend.md) sigue siendo válido como descripción del POC original pero NO está actualizado con el refresh — usá `devops-tickets.md` como source-of-truth viva. Para el racional arquitectónico del rediseño post-2026-05-19, ver [brainstorms/architecture-refresh-phase-1-2-2026-05-19.md](../../brainstorms/architecture-refresh-phase-1-2-2026-05-19.md).
>
> **Actualizá este archivo cada vez que crees, modifiques o cierres un ticket.** Es el índice maestro — si se desincroniza, se pierde el hilo.

---

## 0. Stack y convenciones del proyecto (descubiertas en s3-tree-uploader)

Toda Lambda Python del backend del Classifier sigue el patrón establecido por KT-16612 / `s3-tree-uploader` (deployed). Cualquier ticket nuevo se implementa con la misma arquitectura.

### Stack productivo

| Pieza | Versión / herramienta |
|---|---|
| Lenguaje | **Python 3.11** (Dockerfile base: `public.ecr.aws/lambda/python:3.11`) |
| Runtime | **AWS Lambda Container Image** (no zip), build con `Dockerfile`, push a ECR |
| Repo naming | `{nombre-componente}` en GitHub, ECR repo `lambda-{nombre}`, Lambda name `lambda-{nombre}` |
| Dependencias runtime | `aws-lambda-powertools[tracer]>=2`, `boto3>=1.34`, `pydantic>=2` |
| Dependencias dev | `pytest>=8`, `pytest-cov>=4`, `moto[s3,server]>=5`, `ruff>=0.5`, `mypy>=1.10`, `types-boto3` |
| Lock file | **uv** (`uv.lock`) — package manager moderno |
| Lint | `ruff check` + `ruff format --check`, line-length 100, rules `[E, F, W, I, N, UP, B, S, A, C4, RET, SIM]` |
| Types | `mypy --strict src` |
| Tests | `pytest --cov=src --cov-fail-under=80` |
| Coverage gate | **80%** (forzado por pytest config + SonarCloud) |
| Diagramas / docs | Mermaid, OpenAPI 3.1 para APIs |

### Layout del repo (clean / hexagonal)

```
{repo}/
├── handler.py                       ← Lambda entrypoint, NO se testea directo
├── Dockerfile                       ← container Lambda
├── pyproject.toml                   ← deps + ruff + mypy + pytest config
├── uv.lock                          ← lock file (uv)
├── sonar-project.properties         ← apunta a org "kriptos-io"
├── README.md                        ← spec link, env vars, IAM perms, tests, deploy
├── CLAUDE.md                        ← workflow del repo (Spec-Driven + TDD)
├── AGENTS.md                        ← pointer a CLAUDE.md
├── CONTRIBUTING.md                  ← stack, CI/CD, branch strategy
├── .claude/
│   ├── settings.json                ← permisos + hooks
│   ├── hooks/                       ← block-main-branch, block-dangerous-commands
│   ├── rules/                       ← tdd, secrets, aws, testing, dependencies, docker
│   └── skills/security-review/      ← skill local
├── .github/
│   ├── workflows/ci-cd-dev.yml      ← commitlint → SonarCloud → Snyk → Docker → ECR → deploy dev
│   ├── workflows/ci-cd-prod.yml     ← QA gate → Docker → ECR → deploy prod (reusable wf from kriptos-io/unlockstack)
│   ├── pull_request_template.md
│   └── ISSUE_TEMPLATE/{bug,feature}.md
├── specs/
│   ├── _template.md
│   └── 001-{feature}.md             ← spec por feature, numerada
├── docs/
│   ├── architecture/{name}-adr.md   ← ADR para decisiones non-triviales
│   ├── architecture/diagrams/*.mermaid
│   └── security/{feature}-threat-model.md  ← lo genera /security-review
├── src/
│   ├── config.py                    ← env config con fail-fast en cold start
│   ├── domain/                      ← entities, value objects, eventos. ZERO external deps
│   ├── application/
│   │   ├── ports/                   ← Protocols que adapters implementan
│   │   └── usecases/                ← orquestación, depende solo de domain + ports
│   └── adapters/                    ← boto3 / DynamoDB / SQS / EventBridge / OpenSearch
└── tests/
    ├── conftest.py                  ← env defaults seguros (sin tocar AWS real)
    ├── unit/                        ← test_{module}.py por cada src/
    └── integration/                 ← test_e2e_*.py con moto
```

**Regla de dependencias:** flujo siempre hacia adentro. `domain` no importa nada. `application` solo importa `domain`. `adapters` importan `application`. `handler.py` cablea adapters → use cases.

### CI/CD

Pipelines en `.github/workflows/`, **reusable workflows** de `kriptos-io/unlockstack`:

- **`ci-cd-dev.yml`** — dispara en push a feature branches:
  1. commitlint (formato `tipo: <descripción>` + prefijo `KT-XXXX` en branch)
  2. Testing + coverage → SonarCloud
  3. Snyk (vulnerabilidades en deps)
  4. Docker build
  5. Push a ECR (dev)
  6. Deploy a dev environment
- **`ci-cd-prod.yml`** — dispara en merge a `main`:
  1. QA approval gate (GitHub Environments — bloqueante)
  2. Docker build (mismo commit mergeado)
  3. Push a ECR (prod)
  4. Deploy a prod
- **Trivy** corre a nivel organización en cada PR — bloquea si hay vulnerabilidades high/critical en imagen.

### Workflow obligatorio (spec-driven + TDD)

Cada feature en cada repo sigue:

1. **Spec draft** (humano) — copiar `specs/_template.md` → `specs/{NN}-{feature}.md`, rellenar Problem/Goals/comportamiento.
2. **Brainstorm** — `/superpowers:brainstorming` desafía la spec.
3. **Spec aprobada** — commit `chore: spec for <feature> (KT-XXXXX)`.
4. **Plan** — `/superpowers:writing-plans`.
5. **Execute** — `/superpowers:executing-plans` (o `:subagent-driven-development` para tareas paralelas).
6. **Verify** — `/superpowers:verification-before-completion` antes de declarar done.
7. **Security review** — `/security-review` para auth, APIs públicas, secrets, nuevas entidades de dominio.
8. **Code review** — `/superpowers:requesting-code-review`.
9. **PR** — título `feat:`/`fix:`/`refactor:`, body con `Implements specs/...` + link a `KT-XXXXX`.

**Commits TDD:**
```
chore: <comportamiento> (failing)    ← fase RED
feat: <comportamiento> (passing)     ← fase GREEN
refactor: <comportamiento>           ← cleanup
```

**Non-negotiables (forzados por hooks + CI):**
- Sin código sin test failing commiteado primero.
- Sin push directo a `main` (hook bloquea).
- Sin modificar tests para hacer pasar tests — corregir implementación.
- Sin ARNs / env vars inventados — usar placeholders.

### Repo provisioning (para cada repo nuevo)

Usar la skill `repo-provisioning` de Kriptos. Deja listo: `.claude/`, `.github/workflows/`, `pyproject.toml`, `Dockerfile`, `README.md`, `CONTRIBUTING.md`, layout `src/`/`tests/`, `sonar-project.properties`. Confirmar:

- Repo name según naming convention.
- ECR repo name + Lambda name (formato `lambda-{nombre}`).
- Org SonarCloud = `kriptos-io`.
- Secrets requeridos: `GH_TOKEN`, `AWS_ACCOUNT_ID_DEFAULT_DEV/PROD`, `AWS_REGION_*`, `AWS_OIDC_ROLE_*`, `DOCKERHUB_*`.

---

## 1. Estado de los tickets de código

### Fase 1 — Scan & File Discovery (4 lambdas)

| Ticket | Componente | Status | Repo | Brainstorm | Spec | Próximo paso |
|---|---|---|---|---|---|---|
| **KT-16612** | tree-url-generator | ✅ Deployed | `kriptos-io/s3-tree-uploader` | [brainstorms/KR-16612-tree-url-generator.md](../../brainstorms/KR-16612-tree-url-generator.md) | `specs/001-tree-url-generator.md` (en repo) | — (cerrado) |
| **KT-16613** | tree-uncompressor | 🟡 In Progress + 🔴 **DevOps blocked** | TBD | (en spec) | [**spec lista**](../../specs-staging/KT-16613-tree-uncompressor.md) | Listo Skill 02. Pasar a Skill 03/04 cuando DevOps [KT-16726](https://kriptosteam.atlassian.net/browse/KT-16726) destrabe. |
| **KT-16614** | emr-job-trigger | 🟡 In Progress + 🔴 **DevOps blocked** | TBD | (en spec) | [**spec lista**](../../specs-staging/KT-16614-emr-job-trigger.md) | Listo Skill 02. Mismo bloqueo: [KT-16726](https://kriptosteam.atlassian.net/browse/KT-16726). |
| **KT-16616** | joyas-priorizer (PySpark) | 🟡 In Progress + ⚠️ MOD pendiente | TBD (EMR Serverless) | (en spec) | [**spec lista**](../../specs-staging/KT-16616-joyas-priorizer.md) | Listo Skill 02 con Aho-Corasick + normalize compartido. Infra DevOps ✅ DONE ([KT-16728](https://kriptosteam.atlassian.net/browse/KT-16728)). Sync con Nelson ([KT-16920](https://kriptosteam.atlassian.net/browse/KT-16920)) antes de Skill 04. |

### Fase 1 — Validación humana (4 lambdas nuevas, parte de Fase 1 unificada)

> **Update 2026-05-23:** Fase 1.5 deja de existir como fase aparte. La validación humana es el último paso de Fase 1. Estos 4 Lambdas usan la **DDB consolidada** [KT-17009](https://kriptosteam.atlassian.net/browse/KT-17009) (`classifier-cycles-state`).

| Ticket | Componente | Detalle del texto | Bloqueado por | Próximo paso |
|---|---|---|---|---|
| [**KT-17024**](https://kriptosteam.atlassian.net/browse/KT-17024) | crown-candidates-indexer | 📋 RFC + spec lista | DevOps [KT-17012](https://kriptosteam.atlassian.net/browse/KT-17012) + [KT-17078](https://kriptosteam.atlassian.net/browse/KT-17078) → [KT-17009](https://kriptosteam.atlassian.net/browse/KT-17009) + [KT-17010](https://kriptosteam.atlassian.net/browse/KT-17010) | [**spec**](../../specs-staging/KT-17024-crown-candidates-indexer.md) lista. Próximo: Skill 03/04. |
| [**KT-17025**](https://kriptosteam.atlassian.net/browse/KT-17025) | crown-enterprise-barrier | 📋 RFC + spec lista | DevOps [KT-17013](https://kriptosteam.atlassian.net/browse/KT-17013) → [KT-17009](https://kriptosteam.atlassian.net/browse/KT-17009) | [**spec**](../../specs-staging/KT-17025-crown-enterprise-barrier.md) lista. Próximo: Skill 03/04. |
| [**KT-17026**](https://kriptosteam.atlassian.net/browse/KT-17026) | crown-validation-handler | 📋 RFC + spec lista | DevOps [KT-17014](https://kriptosteam.atlassian.net/browse/KT-17014) + GraphQL schema (Plataforma Web) | [**spec**](../../specs-staging/KT-17026-crown-validation-handler.md) lista. Sync Plataforma Web antes de Skill 04. |
| [**KT-17027**](https://kriptosteam.atlassian.net/browse/KT-17027) | crown-validation-confirm | 📋 RFC + spec lista | DevOps [KT-17015](https://kriptosteam.atlassian.net/browse/KT-17015) → [KT-17010](https://kriptosteam.atlassian.net/browse/KT-17010) | [**spec**](../../specs-staging/KT-17027-crown-validation-confirm.md) lista. Próximo: Skill 03/04. |

### Fase 2 — Priority Sample Collection / GSE (6 lambdas — TODAS NUEVAS, sin abrir en Jira)

Texto detallado en [tickets-implementacion.md](tickets-implementacion.md) (tickets 5–10).

| Ticket | Componente | Detalle del texto | Cambios del refresh | Próximo paso |
|---|---|---|---|---|
| [**KT-17028**](https://kriptosteam.atlassian.net/browse/KT-17028) | gse-cycle-init | 📋 RFC + spec lista | DevOps [KT-17018](https://kriptosteam.atlassian.net/browse/KT-17018) + [KT-17082](https://kriptosteam.atlassian.net/browse/KT-17082) → [KT-17009](https://kriptosteam.atlassian.net/browse/KT-17009) | [**spec**](../../specs-staging/KT-17028-gse-cycle-init.md) lista (multi-trigger desde inicio). |
| [**KT-17029**](https://kriptosteam.atlassian.net/browse/KT-17029) | gse-sample-reception-notifier | 📋 RFC + spec lista | DevOps [KT-17019](https://kriptosteam.atlassian.net/browse/KT-17019) → [KT-17009](https://kriptosteam.atlassian.net/browse/KT-17009) + [KT-17017](https://kriptosteam.atlassian.net/browse/KT-17017) | [**spec**](../../specs-staging/KT-17029-gse-sample-reception-notifier.md) lista. |
| [**KT-17030**](https://kriptosteam.atlassian.net/browse/KT-17030) | gse-sample-anonymizer-notifier | 📋 RFC + spec lista | DevOps [KT-17020](https://kriptosteam.atlassian.net/browse/KT-17020) → [KT-17009](https://kriptosteam.atlassian.net/browse/KT-17009) + [KT-17017](https://kriptosteam.atlassian.net/browse/KT-17017) | [**spec**](../../specs-staging/KT-17030-gse-sample-anonymizer-notifier.md) lista. El más simple. |
| [**KT-17031**](https://kriptosteam.atlassian.net/browse/KT-17031) | gse-request-complete | 📋 RFC + spec lista | DevOps [KT-17021](https://kriptosteam.atlassian.net/browse/KT-17021) → [KT-17009](https://kriptosteam.atlassian.net/browse/KT-17009) | [**spec**](../../specs-staging/KT-17031-gse-request-complete.md) lista. |
| [**KT-17032**](https://kriptosteam.atlassian.net/browse/KT-17032) | gse-station-status | 📋 RFC + spec lista | DevOps [KT-17022](https://kriptosteam.atlassian.net/browse/KT-17022) → [KT-17009](https://kriptosteam.atlassian.net/browse/KT-17009) | [**spec**](../../specs-staging/KT-17032-gse-station-status.md) lista. State lambda STATION. |
| [**KT-17033**](https://kriptosteam.atlassian.net/browse/KT-17033) | gse-enterprise-status | 📋 RFC + spec lista | DevOps [KT-17023](https://kriptosteam.atlassian.net/browse/KT-17023) → [KT-17009](https://kriptosteam.atlassian.net/browse/KT-17009) | [**spec**](../../specs-staging/KT-17033-gse-enterprise-status.md) lista. State lambda CYCLE + notify LLM. |

### Tickets pendientes de update por el refresh

| Documento | Update pendiente |
|---|---|
| `context/classifier-v2/tickets-implementacion.md` | Ticket 4 (joyas-priorizer): bucket `crown_jewels` → `crown_jewel_candidates`, JSONL en vez de JSON, AC ajustado por barrier downstream. Ticket 5 (gse-cycle-init): trigger desde `validated_crown_jewels`, `process_type=crown_validated`, multi-trigger. |
| `context/classifier-v2/orquestacion-backend.md` | Documento histórico del POC. **No actualizar** — usar [devops-tickets.md](devops-tickets.md) como source-of-truth viva (ya incluye el inventario consolidado con el refresh aplicado). |
| `context/classifier-v2/tareas-por-fase.md` y `plan-trabajo.md` | Agregar Fase 1.5 como área propia con sus tareas. |

---

## 2. Acción inmediata recomendada

### Hoy (Jira-only, sin código)

1. **KT-16616 — update del ticket.** Pegar comentario + nueva descripción desde [brainstorms/ticket-texts-fase-1-5-batch-1.md](../../brainstorms/ticket-texts-fase-1-5-batch-1.md) sección "KT-16616 (MOD)".
2. **Decidir épica para Fase 1.5.** Crear nueva (`2026-KT-PRJ - Crown Jewel Validation Workflow (Fase 1.5)`) o ampliar `KT-16369`.

### Esta semana (paralelo, no se bloquean)

3. **KT-16613 y KT-16614:** sin cambios del refresh. Brainstorm individual → Skill 02 → Skill 04 en cada uno.
4. **Crear N1–N4 en Jira** desde los textos del batch1.
5. **Sync con Plataforma Web:** canal de notificación (N2), schema GraphQL (N3), invocación de mutations.

### Próxima semana

6. **KT-16616 brainstorm** enfocado en algoritmo de match (cerrar Q9/Q10/Q11 del brainstorm grande: Aho-Corasick + dónde aplicar `pandas_udf` + versionado de `normalize()`).
7. **Crear N5–N10 en Jira** desde `tickets-implementacion.md`.
8. **Update de los DevOps docs** para reflejar el refresh (ver tabla en §1).

### Mes siguiente

9. Skill 02 por componente, orden sugerido por blocking: N1 → N2 → KT-16616 → N3 → N4 → (Fase 2).

---

## 3. Resumen visual del flujo end-to-end (post-refresh)

```
FASE 1 (per-station, existente con tweak)
  ┌─ KT-16612 tree-url-generator ✅
  ├─ KT-16613 tree-uncompressor
  ├─ KT-16614 emr-job-trigger
  └─ KT-16616 joyas-priorizer (MOD: nuevo bucket destino + JSONL + Aho-Corasick)
                  ↓ matches.jsonl
FASE 1.5 (per-enterprise, NUEVA)
  ┌─ N1 crown-candidates-indexer (S3 → OpenSearch + DDB STATION)
  ├─ N2 crown-enterprise-barrier (DDB Stream → "ready_for_validation" + notify Plataforma)
  ├─ N3 crown-validation-handler (GraphQL approve/reject/add — Plataforma Web)
  └─ N4 crown-validation-confirm (cliente OK → S3 manifest → dispara Fase 2)
                  ↓ manifest.json
FASE 2 (per-cycle, refactor a multi-trigger)
  ┌─ N5 gse-cycle-init (refactor: multi-trigger, process_type=crown_validated)
  ├─ N6 gse-sample-reception-notifier
  ├─ N7 gse-sample-anonymizer-notifier
  ├─ N8 gse-request-complete
  ├─ N9 gse-station-status
  └─ N10 gse-enterprise-status
                  ↓ notify
              LLM Process Queue (caja negra)
```

---

## 4. Cómo recuperar contexto en una sesión nueva

1. Leer este archivo (`context/classifier-v2/dev-tickets.md`) → vista general + status + próximo paso.
2. Si el target es un ticket específico, abrir su sección de "Detalle del texto" (link a brainstorms/tickets-implementacion).
3. Si el target es entender el rediseño, leer [brainstorms/architecture-refresh-phase-1-2-2026-05-19.md](../../brainstorms/architecture-refresh-phase-1-2-2026-05-19.md).
4. Si el target es replicar el patrón del repo, leer `s3-tree-uploader/CLAUDE.md` y `s3-tree-uploader/CONTRIBUTING.md` (en `/Users/harias25/Desktop/Fuentes/Kriptos/s3-tree-uploader/`).
5. Si el target es algo de matching/normalización, leer [context/classifier-v2/components/phase-1/normalize_category.py](components/phase-1/normalize_category.py) + [keywords-example.jsonl](components/phase-1/keywords-example.jsonl).

---

## 5. Decisiones cerradas vs abiertas (acumuladas)

### Cerradas

- Storage Fase 1.5: **híbrido DDB (state) + OpenSearch (corpus)**, reusa GraphQL existente de Plataforma Web.
- Validación humana: granularidad **por carpeta + keyword con override por archivo**.
- Confirmación: **un click final** (no rondas múltiples sobre el mismo cycle).
- KEM = verdad absoluta para `stations_expected` (mismo patrón que Fase 2 hoy).
- Algoritmo de match recomendado: **Aho-Corasick** + `pandas_udf` (decisión final en Skill 02 de KT-16616).
- Formato keywords: **JSONL** (no JSON), patrones multi-token normalizados.
- Stack productivo: Container Lambda Python 3.11 + uv + clean architecture (validado en s3-tree-uploader).

### Abiertas (ver brainstorm grande para detalle)

- Q1: Timeout / Reaper para cycles colgados en `ready_for_validation`.
- Q2: Canal exacto de notificación a Plataforma Web.
- Q3: Tabla DDB nueva vs reusar `gse-cycles-samples` con SK prefix.
- Q4: Feedback loop al modelo de keywords con validaciones del cliente.
- Q5: Cycles concurrentes por enterprise (paralelos vs secuenciales).
- Q6: Política de stations late-arrival.
- Q7: Threat surface completo (diferido — tenant isolation, path traversal, etc.).
- Q8: Confirmar rename de buckets.
- Q9: Algoritmo final de match (recomendación Aho-Corasick).
- Q10: Dónde aplicar `normalize()` a filenames (recomendación EMR + pandas_udf).
- Q11: Versionado y release management de `normalize_category.py`.

---

## 6. Histórico de cambios a este archivo

| Fecha | Cambio | Por |
|---|---|---|
| 2026-05-19 | Creación. Consolida arquitectura post-refresh + estado de KT-16612/13/14/16 + N1–N10. | Skill 01 (Claude) |
| 2026-05-19 | **10 dev tickets nuevos creados en Jira**: KT-17024–KT-17033 (4 Fase 1.5 + 6 Fase 2). KT-16616 MOD aplicado (descripción reemplazada + comentario). Todos los nuevos en status RFC esperando brainstorm individual (Skill 01) por componente. | Skill 01 (Claude) |
| 2026-05-23 | **Consolidación arquitectónica**: Fase 1.5 se fusiona conceptualmente con Fase 1 (la validación es el último paso, no fase aparte). DDB consolidada en una sola tabla `classifier-cycles-state` ([KT-17009](https://kriptosteam.atlassian.net/browse/KT-17009) absorbe a KT-17016, este último superseded). Nueva capability: `validation_mode` ∈ {enterprise, station}. Comentarios agregados a los 10 lambda tickets (KT-17024–17033). | Skill 01 (Claude) |
| 2026-05-23 | **13 specs (output Skill 02) creadas en `specs-staging/`** — una por ticket de código (KT-16613/14/16 + KT-17024–17033). Cada spec sigue `templates/SPEC_TEMPLATE.md` (11 secciones, threat model embebido en §9). Listas para Skill 03/04 cuando DevOps desbloquee infra. Migrar a `<product-repo>/specs/001-*.md` cuando los repos se provisionen. Índice en [`specs-staging/README.md`](../../specs-staging/README.md). | Skill 02 (Claude) |
| 2026-05-23 | **Fase 1 cerrada: 11 decisiones tomadas** (10 técnicas + 5 externas resueltas en sesión). Ver [`specs-staging/DECISIONS-FASE-1.md`](../../specs-staging/DECISIONS-FASE-1.md). Cambios derivados: drop SNS topic de KT-17011, canal AppSync confirmado para KT-17014/17026, estados del CYCLE renombrados (`scanning → stations_complete → confirmed → phase2_collecting → complete`), `station_id` opcional eliminado del confirm. GraphQL schema entregable a Plataforma Web en [`specs-staging/graphql-schema-appsync.md`](../../specs-staging/graphql-schema-appsync.md). Specs Fase 1 reescritas; 10 descripciones Jira actualizadas (no comentarios). | Skill 02 (Claude) |
| 2026-05-23 | **Fase 2 cerrada: 9 decisiones técnicas + 4 externas identificadas con stubs**. Ver [`specs-staging/DECISIONS-FASE-2.md`](../../specs-staging/DECISIONS-FASE-2.md). Cambios derivados: STATION row se reusa entre F1 y F2 (UPDATE en lugar de PUT), no se re-consulta KEM en F2, sub-estados Fase 2 (`sampling_status: requested → uploading → sample_recolected → sample_anonymized`), nuevo counter `CYCLE.stations_sample_anonymized`, filter del Pipe por atributo, publish-first al LLM con contrato de idempotencia, sample_id = filename NNN, samples son `.json` singular (no `.jsonl`), auth API key compartida con `/v2/tree/init`, anonymized_prefix = S3 URI completo, TTL 90d para cleanup. Specs F2 reescritas; 6 descripciones Jira actualizadas. Pendiente: canales finales con Equipo IA (Signal Handler, Anonymizer, LLM Process Queue) — todos los Lambdas funcionan con stubs mientras tanto. | Skill 02 (Claude) |
