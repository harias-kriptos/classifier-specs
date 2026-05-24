# Brainstorm — Architecture Refresh Fase 1 + Fase 2

> Generado por Skill 01 (Brainstorm) en Claude Code · Opus 4.7.
> Roles activados: Product Manager + Tech Lead (modo arquitectónico).
> Input: refresh global de Fase 1 y Fase 2 con validación humana incluida en Fase 1.
> Fecha: 2026-05-19 (consolidado 2026-05-23).
> Épica padre Jira: **KT-16369** "2026-KT-PRJ-Agente Multiplataforma - BE 02 Priority Crown Jewel Detection & Prioritization".
> Tickets vivos relacionados: KT-16612 (done), KT-16613, KT-16614, KT-16616.

---

## ⚡ Consolidación 2026-05-23

Después de la primera iteración del refresh, simplificamos:

1. **No hay "Fase 1.5".** La validación humana es **el último paso de Fase 1**, no una fase aparte. Fase 1 = scan + match + validación. Cuando termina, su output es el input de Fase 2.
2. **Una sola DDB** (`classifier-cycles-state`) para el state machine completo (Fase 1 + Fase 2). Reemplaza a las 2 tablas planeadas inicialmente (`crown-validation-state` y `gse-cycles-samples`). Ver [KT-17009](https://kriptosteam.atlassian.net/browse/KT-17009); [KT-17016](https://kriptosteam.atlassian.net/browse/KT-17016) queda **superseded**.
3. **Validation mode** ∈ {`enterprise`, `station`}: el cliente puede confirmar el set completo del enterprise, o station por station. Esta es una nueva capability sobre la versión 2026-05-19.
4. **KEM = verdad absoluta** para `stations_expected` (mismo patrón en ambas fases).

El resto del brainstorm queda válido — sustituí mentalmente "Fase 1.5" por "última etapa de Fase 1" y las dos DDB por una sola al leer las secciones que siguen.

---

## 1. Resumen ejecutivo

El backend actual del Classifier dispara **Fase 2 por estación** apenas Fase 1 termina de matchear keywords sobre el árbol de archivos de esa estación. El cliente no participa: el LLM clasifica todo lo que matcheó.

El refresh introduce un **paso intermedio (Fase 1.5) de validación humana**:

1. Fase 1 ya **no dispara Fase 2 directo**. Sus matches por estación se acumulan como **candidatos** a nivel enterprise.
2. Cuando todas las estaciones activas (según KEM) del enterprise terminaron Fase 1, los candidatos se exponen al cliente vía Plataforma Web.
3. El cliente revisa, aprueba, rechaza o agrega rutas extra — agrupando por carpeta + keyword, con override por archivo. Las validaciones se hacen incrementalmente; **el "confirmar" final es uno solo**.
4. Al confirmar, el set validado dispara Fase 2 con `process_type=crown_validated`.

Adicionalmente, **`gse-cycle-init` se vuelve genérico**: la misma maquinaria (cycle/station/request, barriers, anonymizer notify, LLM notify) sirve para cualquier `process_type` futuro — bastará agregar un nuevo event source.

El cambio impacta poco en los 3 tickets vivos (KT-16613/14/16): el único afectado es **KT-16616** (`joyas-priorizer`), que renombra el bucket destino y ajusta el AC del barrier downstream.

---

## 2. Arquitectura propuesta

### 2.1 Diagrama end-to-end

```
┌─────────────────────── FASE 1 (existente, tweak menor) ────────────────────┐
│                                                                             │
│   Agent ─► POST /v2/tree/init (KT-16612, done)                              │
│              │                                                              │
│              ▼                                                              │
│        compressed_trees/{ent}/{sta}/{tree}.jsonl.gz                         │
│              │ EventBridge                                                  │
│              ▼                                                              │
│        tree-uncompressor (KT-16613) ──► decompressed_trees/                 │
│              │ EventBridge                                                  │
│              ▼                                                              │
│        emr-job-trigger (KT-16614) ──► EMR Serverless                        │
│              │                                                              │
│              ▼                                                              │
│        joyas-priorizer (KT-16616, AJUSTE de destino)                        │
│              │                                                              │
│              ▼                                                              │
│        crown_jewel_candidates/{ent}/{sta}/matches.jsonl                     │
│        (renombrado desde suspicious_crown_jewels/)                          │
│        El archivo se escribe siempre, incluso vacío.                        │
│              │ S3 PutObject                                                 │
└──────────────┼──────────────────────────────────────────────────────────────┘
               ▼
┌─────────────────────── FASE 1.5 — NUEVA: Validación humana ────────────────┐
│                                                                             │
│   λ crown-candidates-indexer (NUEVO)                                        │
│     1. Lee matches.jsonl de S3.                                             │
│     2. Bulk-indexa cada match en OpenSearch (índice                         │
│        `crown_jewel_candidates`), agregando:                                │
│           - validation_status="pending"                                     │
│           - candidate_id = sha256(ent+sta+path)                             │
│           - cycle_id de validación (get-or-create por enterprise)           │
│     3. UPDATE DDB (tabla crown-validation-state):                           │
│           - PHASE1_STATION#{ent}#{sta}#{cycle_id}.scan_status="complete"    │
│           - candidates_count = N                                            │
│     4. Idempotente: re-indexa con mismo candidate_id si llega 2 veces.      │
│                                                                             │
│   λ phase1-enterprise-barrier (NUEVO, EventBridge Pipe desde DDB Stream)    │
│     Filter: NewImage.SK begins_with "PHASE1_STATION#"                       │
│     Lógica:                                                                 │
│       1. Skip si STATION.scan_status != "complete".                         │
│       2. Conditional ADD: PHASE1_CYCLE.stations_completed += 1.             │
│          Condition: STATION.barrier_counted <> true.                        │
│          Y SET STATION.barrier_counted = true (exactly-once por station).   │
│       3. Si PHASE1_CYCLE.stations_completed >= stations_expected:           │
│          Conditional SET PHASE1_CYCLE.status="ready_for_validation".        │
│          Y NOTIFY plataforma web (canal TBD).                               │
│                                                                             │
│   λ kem-stations-resolver (NUEVO, se llama en get-or-create del CYCLE)      │
│     - Equivalente al de gse-cycle-init: query a KEM API por enterprise →    │
│       stations_expected.                                                    │
│     - Cacheable por enterprise+timestamp.                                   │
│                                                                             │
│   Plataforma Web (React + GraphQL existente — extensión)                    │
│     - Vista nueva: candidatos por enterprise, agrupados por carpeta +       │
│       keyword. Filtros, paginación, bulk-ops.                               │
│     - El backend GraphQL ya consume OpenSearch → reusa el patrón.           │
│     - GraphQL extensions:                                                   │
│         query crownJewelCandidates(enterpriseId, cycleId, filters)          │
│         mutation validateCandidateGroup(criteria, decision)                 │
│         mutation overrideCandidate(candidateId, decision)                   │
│         mutation addExtraPath(enterpriseId, stationId, path)                │
│         mutation confirmValidation(enterpriseId, cycleId)                   │
│                                                                             │
│   λ validation-mutation-handler (NUEVO)                                     │
│     - Detrás de cada GraphQL mutation (incremental, sin confirm).           │
│     - UPDATE OpenSearch: doc.validation_status ∈                            │
│       {pending, approved, rejected, manually_added}.                        │
│     - UPDATE DDB counters en PHASE1_CYCLE:                                  │
│         approved_count, rejected_count, manually_added_count.               │
│                                                                             │
│   λ validation-confirm (NUEVO, API GW POST /v2/validation/confirm)          │
│     1. Conditional check: PHASE1_CYCLE.status="ready_for_validation".       │
│     2. Lee de OpenSearch los candidatos con validation_status IN            │
│        ("approved","manually_added") filtrando por cycle_id.                │
│     3. Materializa en S3:                                                   │
│           validated_crown_jewels/{ent}/{cycle_id}/manifest.json             │
│           validated_crown_jewels/{ent}/{cycle_id}/station-{X}.jsonl         │
│           (un archivo por station con sus files validados)                  │
│        manifest.json incluye stations_with_files, total_files, ent, cycle.  │
│     4. SET PHASE1_CYCLE.status="phase2_triggered" (conditional).            │
│     5. El PutObject del manifest dispara Fase 2.                            │
│                                                                             │
└──────────────┼──────────────────────────────────────────────────────────────┘
               ▼
┌─────────────────────── FASE 2 (refactor multi-trigger) ────────────────────┐
│                                                                             │
│   λ gse-cycle-init (refactor)                                               │
│     - Event source: ahora viene de validated_crown_jewels/ vía              │
│       gse-validated-cycle-queue.fifo (en lugar de suspicious_crown_jewels). │
│     - process_type=crown_validated (env var por EventSourceArn).            │
│     - Lee manifest.json: stations_expected ya está adentro (no query KEM    │
│       en este caso, porque ya lo sabíamos al cerrar Fase 1.5).              │
│     - Resto del flujo idéntico: get-or-create CYCLE, PUT STATION/REQUEST,   │
│       NOTIFY Signal Handler.                                                │
│                                                                             │
│   El resto de Fase 2 (sample reception, anonymizer notifier,                │
│   station-status, enterprise-status, request-complete) NO cambia.           │
│                                                                             │
│   Futuro (mismo Lambda, distinto event source):                             │
│     - process_type=classification → trigger desde clasificación pendiente.  │
│     - process_type=manual_scan → trigger ad-hoc desde Plataforma Web.       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Storage — diseño híbrido

| Pieza | Storage | Por qué |
|---|---|---|
| Estado de Fase 1.5 (CYCLE / STATION counters, barriers) | **DDB** tabla `crown-validation-state`, single-table con stream | Conditional writes, atómico. Mismo patrón que `gse-cycles-samples`. |
| Corpus de candidatos (1 doc por match) | **OpenSearch** índice `crown_jewel_candidates` | Reusa el motor que ya alimenta a la Plataforma Web. Agregaciones por carpeta/keyword, paginación, faceted UI gratis. |
| Decisiones del cliente (approve/reject/add) | **OpenSearch** (`validation_status` por doc) + counters en **DDB** | OpenSearch hace lo que sabe (update por doc). DDB hace la barrera "validated_count >= candidates_count" cuando llegue el confirm. |
| Output validado (manifest + files por station) | **S3** `validated_crown_jewels/` | Mismo patrón que `compressed_trees`/`decompressed_trees`. PutObject dispara Fase 2. |
| Crudo de matches por station | **S3** `crown_jewel_candidates/` | Source-of-truth inmutable. Re-indexable si OpenSearch se rompe. |

### 2.3 DDB `crown-validation-state` — modelo

| Item type | PK | SK | Atributos clave |
|---|---|---|---|
| PHASE1_CYCLE | `{enterprise_id}` | `PHASE1_CYCLE#{cycle_id}` | `stations_expected`, `stations_completed`, `candidates_count`, `approved_count`, `rejected_count`, `manually_added_count`, `status` ∈ {scanning, ready_for_validation, validating, phase2_triggered}, `created_at`, `confirmed_at` |
| PHASE1_STATION | `{enterprise_id}` | `PHASE1_STATION#{station_id}#{cycle_id}` | `scan_status` ∈ {scanning, complete}, `candidates_count`, `barrier_counted` (boolean para exactly-once), `completed_at` |

Stream activo con `NEW_AND_OLD_IMAGES`.

### 2.4 OpenSearch — esquema del índice `crown_jewel_candidates`

```json
{
  "candidate_id": "sha256(ent|sta|path)",
  "enterprise_id": "ent-001",
  "station_id": "station-A",
  "cycle_id": "uuid",
  "path": "/Users/foo/Estratégico/Q1-Plan-2026.pdf",
  "path_normalized": "users foo estrategico q plan",
  "folder": "/Users/foo/Estratégico/",
  "name": "Q1-Plan-2026",
  "name_normalized": "q plan",
  "extension": "pdf",
  "size": 245780,
  "modified_date": "2026-04-14T09:15:22Z",
  "matched_patterns": [
    "plan estrategico quinquenal grupo pichincha"
  ],
  "matched_business_areas": ["estrategia planeacion"],
  "normalize_version": "1.0.0",
  "validation_status": "pending | approved | rejected | manually_added",
  "validation_actor": "user_id de la plataforma web",
  "validation_at": "ISO-8601",
  "indexed_at": "ISO-8601"
}
```

Aggregations naturales para la UI:
- por `folder` → cliente aprueba/rechaza toda la carpeta de un click.
- por `matched_patterns` → cliente filtra "muéstrame todo lo que matcheó 'plan estrategico quinquenal grupo pichincha'".
- por `matched_business_areas` → "solo lo de Cumplimiento / AML".
- por `extension` → "solo PDFs".

### 2.5 Formato de `keywords/{enterprise_id}.jsonl` y normalización

**Formato:** JSONL (una línea por patrón), no JSON. Confirmar rename en KT-16616.

Cada línea:
```jsonl
{"category":"plan estrategico quinquenal grupo pichincha","original_category":"Plan Estratégico Quinquenal Grupo Pichincha","business_area":"estrategia planeacion","original_business_area":"Estrategia & Planeación"}
```

**`category` está normalizado** con la función `normalize()` (ver `context/classifier-v2/components/phase-1/normalize_category.py`). Regla determinística:
1. lowercase
2. strip diacríticos (NFKD)
3. quitar dígitos
4. quitar todo lo que no sea `[a-z ]`
5. quitar tokens 100% romanos (`i, v, x, l, c, d, m`)
6. colapsar espacios

**Consecuencias para `joyas-priorizer` (KT-16616):**
- Los patrones son **frases multi-token** (3–8 tokens típico). El matcher **no** puede ser substring naïve sobre el nombre crudo.
- Los **nombres de archivo deben pasar por el mismo `normalize()`** antes del match. Sin esto, `Plan_Estratégico_2026.pdf` no matchea `"plan estrategico quinquenal"`.
- Algoritmo recomendado: **Aho-Corasick** sobre los `category` como diccionario (broadcast del automaton), aplicado al `path + name` normalizados de cada archivo. Coste O(N+M) vs O(N×M) para substring naïve.
- Implementación en Spark: **`pandas_udf` vectorizado** o nativo, **nunca** UDF Python row-by-row (overhead de serialización × millones de filas = inviable).
- El `normalize()` es **código compartido** entre keyword generator (equipo IA), `joyas-priorizer` (backend), y potencialmente el agente. Cualquier cambio rompe el match en silencio — necesita `normalize_version` + check explícito en el job.

**Performance esperado:**
- Enterprise chico (100k archivos × 2k patrones): segundos.
- Enterprise grande (10M archivos × 5k patrones): minutos con Aho-Corasick + pandas_udf.
- Enterprise grande con UDF naïve: horas. **No hacerlo así.**

---

## 3. Acceptance criteria por componente nuevo (borrador para abrir tickets)

### 3.1 `crown-candidates-indexer`

- **AC01:** Por cada PutObject en `crown_jewel_candidates/{ent}/{sta}/matches.jsonl`, todos los matches quedan indexados en OpenSearch con `validation_status="pending"`.
- **AC02:** STATION en DDB queda con `scan_status="complete"` y `candidates_count=N` (incluso si N=0).
- **AC03:** Re-procesar el mismo archivo es idempotente (mismo `candidate_id` → upsert en OpenSearch, no duplica).
- **AC04:** Si OpenSearch bulk falla parcial: registra error en logs, no marca STATION como complete (espera reintento del SQS).
- **AC05:** Logs estructurados con `enterprise_id, station_id, cycle_id, candidates_count, request_id`.

### 3.2 `phase1-enterprise-barrier`

- **AC01:** Cuando una STATION pasa a `scan_status="complete"`, suma +1 a `stations_completed` del CYCLE exactamente una vez (gracias a `barrier_counted` flag).
- **AC02:** Stream record duplicado del DDB → no double-counting (conditional check + flag).
- **AC03:** Cuando `stations_completed >= stations_expected`, CYCLE pasa a `ready_for_validation` y se publica una notificación al canal de la Plataforma Web.
- **AC04:** Si una STATION llega después del cierre del barrier (late arrival), se loguea WARN y se descarta (no se reabre el cycle — política: cliente valida lo que llegó a tiempo, las tardías se ignoran. Ver Q6).
- **AC05:** Records de tipo CYCLE no procesados (filter del Pipe).

### 3.3 `validation-mutation-handler`

- **AC01:** Mutation `validateCandidateGroup(criteria, decision)` actualiza OpenSearch en bulk para todos los docs que matchean el criterio (`folder=X` o `matched_keywords=Y`), y suma counters en DDB.
- **AC02:** Mutation `overrideCandidate(id, decision)` cambia un doc específico (sobrescribe la decisión grupal).
- **AC03:** Mutation `addExtraPath(ent, sta, path)` crea un nuevo doc en OpenSearch con `validation_status="manually_added"`.
- **AC04:** Todas las mutations son idempotentes por `candidate_id`.
- **AC05:** Counters en DDB son consistentes con el conteo en OpenSearch (reconciliable vía job batch, no estrictamente en tiempo real).

### 3.4 `validation-confirm`

- **AC01:** POST `/v2/validation/confirm` con `{enterprise_id, cycle_id}` materializa los candidatos aprobados + manualmente agregados en `validated_crown_jewels/{ent}/{cycle_id}/`.
- **AC02:** Solo se puede confirmar 1 vez por cycle (`status` debe ser `ready_for_validation`; al confirmar pasa a `phase2_triggered`; condicional rechaza segundo intento).
- **AC03:** Si no hay archivos aprobados (cliente rechaza todo), igual escribe un `manifest.json` con `total_files=0` y NO dispara Fase 2 (cycle se cierra como `phase2_skipped`).
- **AC04:** El manifest agrupa archivos por station; un PutObject del manifest dispara `gse-cycle-init` por SQS FIFO con `MessageGroupId=enterprise_id`.
- **AC05:** Logs incluyen `enterprise_id, cycle_id, approved_count, rejected_count, manually_added_count, request_id`.

### 3.5 `gse-cycle-init` (refactor)

- **AC01:** Acepta múltiples event sources mapeados a distinto `process_type` vía env var (`EVENT_SOURCE_ARN_TO_PROCESS_TYPE` JSON).
- **AC02:** Cuando `process_type=crown_validated`, lee `stations_expected` del `manifest.json` (no de KEM).
- **AC03:** Cuando `process_type=crown` (legacy, deprecated) o cualquier futuro, sigue el flujo original.
- **AC04:** No regresiones en AC vigentes del Lambda.
- **AC05:** Tests cubren ambos paths (crown_validated y legacy stub).

---

## 4. Impacto en tickets vivos (KT)

| Ticket | Cambio | Acción |
|---|---|---|
| **KT-16612** (tree-url-generator) | ninguno | dejar como está, ya está done. |
| **KT-16613** (tree-uncompressor) | ninguno | dejar como está, sigue siendo válido. |
| **KT-16614** (emr-job-trigger) | ninguno | dejar como está, sigue siendo válido. |
| **KT-16616** (joyas-priorizer) | (1) Bucket destino renombrado a `crown_jewel_candidates/`. (2) AC02 actualizado: "vacío también se escribe, pero el barrier downstream ya **no** es per-station — el archivo igual se indexa y cuenta como STATION completa". (3) **Formato de keywords es JSONL, no JSON** (ver sección 2.5). (4) **Matcher requiere normalizar filenames con `normalize_category.py`** + algoritmo Aho-Corasick (no substring naïve). (5) AC nuevo: cada match registra `matched_patterns` (lista de `category`) y `matched_business_areas`. | **Brainstorm separado** cuando llegues a este ticket — es donde se cierra el algoritmo de matching. Se actualiza AC + descripción + se documenta en la épica padre. |

---

## 5. Edge cases identificados

1. **Station llega tarde después del barrier.** El cliente ya está validando; una station rezagada termina Fase 1. Política: se loguea WARN y se descarta (no se reabre el cycle ni se actualiza el corpus). Cliente valida lo que llegó a tiempo. Tickets de Q6 pueden cambiar esto.
2. **Cliente nunca confirma.** El cycle queda en `ready_for_validation` indefinidamente. Necesitamos un Reaper / timeout policy (Q1).
3. **Cliente confirma con 0 archivos aprobados.** Cycle cierra como `phase2_skipped`; no se dispara Fase 2; se loguea para análisis.
4. **Cliente agrega `manually_added` path que apunta a una station no escaneada.** El manifest incluye una "station fantasma". `gse-cycle-init` debe tolerar que el agente correspondiente no responda al Signal Handler dentro del timeout — esa STATION queda con `samples_received=0` y eventualmente se cierra por timeout (Q3 sobre Reaper en Fase 2 ya existente).
5. **Misma enterprise dispara segundo scan estando uno abierto.** Decisión: dos PHASE1_CYCLEs activos en paralelo, distintos `cycle_id`. La UI muestra el más reciente; el viejo se puede confirmar o abandonar (Q5).
6. **OpenSearch indexer falla pero DDB STATION ya está `complete`.** Inconsistencia. Mitigación: el indexer escribe DDB **después** de confirmar el bulk OK en OpenSearch.
7. **Volumen alto: 200k+ matches en un enterprise.** El cliente no puede navegar archivo por archivo. La UI debe forzar agrupación por defecto. Por config: `MAX_INDIVIDUAL_OVERRIDES_PER_CYCLE` para evitar abuso.
8. **Tamaño del `manifest.json`.** Si hay 500k archivos validados, el manifest puede pesar mucho. Usar archivos por station + manifest liviano que solo apunta.
9. **Concurrent edits del cliente (dos sesiones simultáneas).** OpenSearch update sin optimistic locking → último gana. Aceptable porque el confirm final es 1 click y el último estado es el que se materializa.
10. **Reindexación / reprocesamiento.** Si hay que reindexar OpenSearch desde S3, el job es replayable (S3 inmutable + idempotent indexer).

---

## 6. Out of scope (explícito)

- **Retraining del modelo de keywords con la validación humana.** La validación se usa solo para definir el set de Fase 2 (curated set para LLM). Refinar las keywords de Bedrock o el matcher con feedback positivo/negativo es un ticket aparte (Q4).
- **UI design / UX exacto** de la vista de validación. Acá solo se define el contrato GraphQL + AC funcionales. Diseño visual lo lleva el equipo de Plataforma Web.
- **Versionado de la tabla de keywords** entre runs de Fase 1.
- **Manejo de scan incremental** (delta-scans desde el agente). Asumimos scans completos por ahora.
- **Notificación al cliente cuando "ready_for_validation"** (email, in-app, push). Canal a definir con Plataforma Web (Q2).
- **Threat surface / tenant isolation completo** — diferido a próxima iteración (sección 7).

---

## 7. Threat surface — DIFERIDO

> **Decisión:** definir threat model completo en próxima iteración (Skill 02 dedicada o ticket separado).

Nota: el aislamiento entre tenants **no lo enforza ni GraphQL ni OpenSearch**. La Plataforma Web filtra por `enterprise_id` del usuario autenticado antes de query/mutation. Cualquier endpoint nuevo (validation-confirm, addExtraPath, etc.) debe pasar por esa capa o agregar la suya propia.

Riesgos identificados a documentar luego:
- Path traversal vía `manually_added` path (`../../etc/passwd`).
- Cross-enterprise access vía cycle_id (atacante con sesión de cliente A pasa cycle_id de cliente B en el confirm).
- Información del filesystem (paths reales, no anonimizados) en OpenSearch — quién más puede leer ese índice.
- DoS del confirm endpoint (manifest gigante).
- Quién tiene el rol de "confirmar" — owner único de enterprise o cualquier user con permiso?

---

## 8. Open questions deferidas

| # | Pregunta | Dueño | Bloqueante para… |
|---|---|---|---|
| Q1 | Timeout / política de Reaper para cycles en `ready_for_validation` que el cliente nunca confirma | Haroldo + Producto | Spec de `validation-confirm` + alerting |
| Q2 | Canal de notificación al cliente cuando aparece "listo para validar" (email, in-app, webhook, push) | Plataforma Web + Producto | UX del flujo completo, no bloquea backend |
| Q3 | Storage decision final: tabla DDB nueva `crown-validation-state` vs reusar `gse-cycles-samples` con nuevos SK | Tech Lead (en Skill 02) | Spec de las 4 Lambdas nuevas |
| Q4 | Feedback loop al modelo de keywords con true/false positives validados | Equipo Bedrock + IA | Ticket separado, no afecta este refresh |
| Q5 | Política con N cycles activos por enterprise (paralelos, secuenciales, o exclusión mutua) | Producto | Spec de `crown-candidates-indexer` (get-or-create logic) |
| Q6 | Política de stations late-arrival (descartar, abrir nuevo cycle, mergear) | Producto | Spec de `phase1-enterprise-barrier` |
| Q7 | Threat surface completo (ver sección 7) | Haroldo (próxima iteración) | No bloquea spec funcional, sí deploy a prod |
| Q8 | Naming de buckets: confirmar rename `suspicious_crown_jewels` → `crown_jewel_candidates` y `validated_crown_jewels` | Haroldo | Spec de KT-16616 + tickets nuevos |
| Q9 | Algoritmo final de matching multi-token en `joyas-priorizer` (Aho-Corasick vs token-set overlap vs hybrid). Define recall/precision del pipeline | Tech Lead en Skill 02 de KT-16616 | Spec de KT-16616 |
| Q10 | Dónde se aplica `normalize()` a los filenames — en EMR (recomendado), en `tree-uncompressor`, o en el agente — y con qué primitiva (pandas_udf vs nativo). Define perf budget | Tech Lead en Skill 02 de KT-16616 | Spec + capacity planning de EMR |
| Q11 | Versionado y release management de `normalize_category.py` — código compartido entre agente, generador de keywords y EMR. Estrategia de bump + reprocesamiento cuando cambia | Arquitectura + equipo IA | Cualquier cambio futuro a la función |

---

## 9. Persistencia aplicada

- **Caso A** (idea cruda sin destino externo): se persiste solo en este repo.
- Archivo: `brainstorms/architecture-refresh-phase-1-2-2026-05-19.md` (este).
- **No** se actualiza Jira ni Confluence en esta pasada (decisión del usuario: "dejemos claro todo acá en este repo y dejemos claro los tickets").
- Cuando arranque los brainstorms ticket-por-ticket (KT-16613, 14, 16, y los 5 nuevos), cada uno generará su propio archivo `brainstorms/KT-XXXXX-<slug>.md` siguiendo el patrón de KR-16612.

---

## 10. Siguiente paso

Dos caminos válidos:

**Camino A — Por componente (recomendado):**
1. Abrir 5 tickets Jira nuevos bajo épica KT-16369 (o nueva épica) con la descripción base del componente y los AC borradores de la sección 3.
2. Brainstorm separado (Skill 01) por cada uno antes de Skill 02.
3. Actualizar KT-16616 con el cambio de bucket + AC02.
4. KT-16613 y KT-16614 quedan como están.

**Camino B — Como iniciativa:**
1. Crear página Confluence con este doc adaptado al `templates/CONFLUENCE_INITIATIVE.md`.
2. Crear Epic nueva (`KT-XXXXX — Crown Jewel Validation Workflow`) que liste los 5 tickets nuevos como hijos.
3. KT-16369 se vuelve "Fase 1 base"; la nueva épica se vuelve "Fase 1.5 + refactor Fase 2".

Tickets nuevos a abrir (resumen):

| Slug | Componente | Tipo | Estimación gruesa |
|---|---|---|---|
| `crown-candidates-indexer` | Lambda Python | Story | 3d |
| `phase1-enterprise-barrier` | Lambda Python | Story | 2d |
| `validation-mutation-handler` | Lambda Python + GraphQL extensions | Story | 5d (incluye coord con Plataforma Web) |
| `validation-confirm` | Lambda Python + API GW route | Story | 3d |
| `gse-cycle-init` refactor | Refactor del Lambda existente | Story | 2d |

Además, tickets DevOps:
- Nueva tabla DDB `crown-validation-state` + stream.
- Nuevo bucket S3 `crown_jewel_candidates` + EventBridge.
- Nuevo bucket S3 `validated_crown_jewels` + EventBridge.
- Nueva SQS FIFO `gse-validated-cycle-queue.fifo`.
- Nuevo índice OpenSearch `crown_jewel_candidates` + mappings.
- GraphQL schema extensions.

---

**Skill siguiente:** Skill 02 (Spec + Threat Model) — recomiendo arrancar por `crown-candidates-indexer` o `phase1-enterprise-barrier` (los más autocontenidos, sin dependencias externas), y dejar `validation-mutation-handler` para el final porque coordina con Plataforma Web.
