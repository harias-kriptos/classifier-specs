# Ticket texts — Batch 1: KT-16616 MOD + Fase 1.5 (N1–N4)

> Generado por Skill 01 sobre el brainstorm [architecture-refresh-phase-1-2-2026-05-19.md](architecture-refresh-phase-1-2-2026-05-19.md).
> Listo para pegar en Jira / Notion / Miro.
> Fecha: 2026-05-19.

Cada bloque tiene la **descripción** lista para pegar, y debajo un **resumen DevOps/infra** que podés pegar como comentario o usar para abrir el ticket DevOps gemelo (los tickets de DevOps están en `orquestacion-backend.md` ampliados con D1–D8 en el brainstorm).

---

## ⚙️ KT-16616 (MOD) — Implementación: joyas-priorizer (PySpark)

### A. Comentario para agregar al ticket (traceability)

```markdown
Actualización del scope post-brainstorm de architecture-refresh (2026-05-19).

Cambios principales:
1. Bucket destino renombrado: `suspicious_crown_jewels/` → `crown_jewel_candidates/`.
2. Formato keywords es **JSONL** (no JSON). Ver `context/classifier-v2/components/phase-1/keywords-example.jsonl`.
3. Patrones son **frases multi-token** (ej. "plan estrategico quinquenal grupo bancario"), no palabras sueltas.
4. Matcher debe **normalizar nombres de archivo** con la función compartida `normalize_category.py` antes del match — misma normalización que el LLM aplicó al generar las keywords.
5. AC02 ajustado: el archivo vacío se sigue escribiendo pero **ya no dispara Fase 2 directo**. Dispara al nuevo `crown-candidates-indexer` que mantiene el barrier enterprise-level.
6. AC nuevo (AC06): cada match registra `matched_patterns` (lista de `category`) y `matched_business_areas`.

Brainstorm completo: `brainstorms/architecture-refresh-phase-1-2-2026-05-19.md`.
Decisiones de algoritmo (Aho-Corasick vs token-set, pandas_udf vs nativo) se cierran en Skill 02 de este ticket.
```

### B. Nueva descripción del ticket (reemplaza la actual)

```markdown
## 🎯 Objetivo

Implementar el componente `joyas-priorizer` (PySpark): cargar las keywords del enterprise (JSONL), normalizar nombres de archivo con la función compartida, hacer match multi-token contra el árbol descomprimido, y escribir `crown_jewel_candidates/{ent}/{sta}/matches.jsonl` (incluso vacío).

---

## 📋 Contexto

**Trigger:** invocado por `emr-job-trigger` con argumentos `<decompressed_bucket> <tree_key>`.

**Función:** matchear nombres de archivo contra patrones del enterprise (frases multi-token), aplicando la misma normalización determinística que el generador de keywords usó. Producir un archivo de candidatos por station — el barrier enterprise-level lo maneja el componente downstream `crown-candidates-indexer`.

**Formato de keywords:** JSONL, una línea por patrón:
```jsonl
{"category":"plan estrategico quinquenal grupo bancario","original_category":"Plan Estratégico Quinquenal Grupo Bancario","business_area":"estrategia planeacion","original_business_area":"Estrategia & Planeación"}
```

`category` y `business_area` ya están normalizados. `original_*` se preservan para mostrar en UI downstream (OpenSearch).

**Normalización compartida:** la función `normalize()` vive en `context/classifier-v2/components/phase-1/normalize_category.py` y debe aplicarse idéntica a:
- los nombres de keywords (responsabilidad del generador — equipo IA),
- los nombres de archivo y paths del árbol scaneado (responsabilidad de este Lambda).

Cualquier divergencia entre las dos puntas rompe el match en silencio.

**Lógica:**

1. Parsear `enterprise_id` y `station_id` desde `tree_key`.
2. Cargar `keywords/{enterprise_id}.jsonl` desde S3. Si no existe → escribir `matches.jsonl` vacío y salir con código 0 + log WARN.
3. Construir broadcast del set de patrones (categories + métadata original asociada).
4. Read NDJSON del árbol descomprimido → DataFrame Spark.
5. Aplicar `normalize()` a `name` y `path` de cada fila (idealmente vectorizado con `pandas_udf`, no UDF Python row-by-row).
6. Match multi-token: para cada fila, calcular `matched_patterns` (lista de categories cuyas tokens están todas presentes en el `path_normalized + " " + name_normalized` — o usar Aho-Corasick sobre el automaton broadcast).
7. Filter rows con `matched_patterns` no vacío.
8. Add columns: `path_normalized`, `name_normalized`, `matched_patterns`, `matched_business_areas`, `normalize_version`.
9. Coalesce a 1 partition.
10. Write JSON a `crown_jewel_candidates/{enterprise_id}/{station_id}/matches.jsonl` con `mode("overwrite")`. **Si no hay matches: escribir archivo vacío de todas formas** (señal para `crown-candidates-indexer`).

**Interacción con cajas negras (Equipo IA):**
- Lee `keywords/{enterprise_id}.jsonl` que el equipo IA deposita previamente. Si no existe → produce archivo vacío, no falla.
- El campo `original_category` y `original_business_area` se propagan tal cual desde el JSONL del IA al output — no se altera.

---

## ✅ Acceptance Criteria

- **AC01:** Tree con N matches → `matches.jsonl` con N filas, cada una con `matched_patterns` no vacío.
- **AC02:** Tree con 0 matches → `matches.jsonl` **vacío** (clave para que `crown-candidates-indexer` detecte la station como completa).
- **AC03:** Sin archivo de keywords → `matches.jsonl` vacío, exit code 0, log WARN.
- **AC04:** Mode overwrite — reprocesar el mismo tree reemplaza el output anterior.
- **AC05:** El `normalize()` aplicado a filenames es **bit-idéntico** al aplicado por el generador de keywords. Test específico: corpus de 100 nombres con tildes, eñe, dígitos, romanos → output esperado coincide con `normalize_category.py`.
- **AC06:** Cada match registra `matched_patterns` (lista de `category`) y `matched_business_areas` (lista deduplicada de `business_area`). `original_category` y `original_business_area` también se preservan para uso downstream.
- **AC07:** Performance — enterprise con 1M archivos × 2k patrones se procesa en < 5 min con la config de EMR del Ticket DevOps. (Métrica observable: `duration_ms` en logs del job.)

---

## ⚠️ Edge Cases

- Filename con tilde + dígito + Roman (ej. `Plan_Estratégico_V2_2026.pdf`) → normaliza correctamente a `"plan estrategico"`.
- Path con segmentos largos vs nombre corto (ej. `/Users/foo/Estratégico/Q1.pdf`) — el path normalizado contribuye al match igual que el name. Confirmar política con threat surface posterior.
- Patrón con 1 sola token después de normalizar (ej. `"financial"`) — se acepta pero produce alto recall. No es responsabilidad del matcher filtrar — es responsabilidad del generador de keywords no producirlos.
- Patrón vacío después de normalizar (todo era dígitos/romanos) → skip silencioso, log INFO.
- Archivo de keywords con líneas malformadas (JSON inválido en una línea) → skip esa línea con log WARN, no abortar.
- Tree con 0 archivos → exit code 0, archivo vacío, log INFO.

---

## ❌ Out of Scope

- Algoritmo final de matching (Aho-Corasick vs token-set vs hybrid) — decisión cerrada en Skill 02.
- Generación/refinamiento de las keywords — pertenece al equipo IA / Bedrock.
- Indexación de los matches a OpenSearch — responsabilidad de `crown-candidates-indexer` (ticket nuevo N1).
- Manejo del barrier enterprise-level — responsabilidad de `phase1-enterprise-barrier` (ticket nuevo N2).

---

## 🔒 Threat Surface

Diferido a próxima iteración. Notas:
- Patrones contienen nombres comerciales y categorías sensibles del cliente. El bucket `keywords/` debe tener acceso IAM restricto solo al EMR job y al equipo IA.
- El nombre `original_category` se va a propagar a OpenSearch y a la UI del cliente — sin sanitización adicional. Aceptable porque el cliente ve patrones de su propio enterprise.

---

## ❓ Open Questions

| # | Pregunta | Owner | Default temporal | Bloqueante para |
|---|----------|-------|------------------|-----------------|
| Q1 | Algoritmo final (Aho-Corasick vs token-set overlap). Aho-Corasick es lo recomendado | Tech Lead en Skill 02 | Aho-Corasick | Spec |
| Q2 | `path` contribuye o no al match (recall vs precision) | Producto + Tech Lead | sí contribuye | Spec |
| Q3 | Política con patrones de 1 token después de normalizar | Equipo IA | aceptar | Spec del generador (no este ticket) |

---

## 📎 Referencias

- **Brainstorm arquitectónico:** `brainstorms/architecture-refresh-phase-1-2-2026-05-19.md`
- **Función compartida:** `context/classifier-v2/components/phase-1/normalize_category.py`
- **Ejemplo de keywords JSONL:** `context/classifier-v2/components/phase-1/keywords-example.jsonl`
- **Épica:** KT-16369
- **Spec técnica:** TBD (Skill 02)
- **MR/PR de implementación:** TBD (Skill 04)
```

---

## 🟦 N1 (NUEVO) — Implementación: crown-candidates-indexer

### Descripción del ticket

```markdown
## 🎯 Objetivo

Indexar los matches de Fase 1 en OpenSearch para que el cliente pueda validarlos desde la Plataforma Web, y mantener el barrier enterprise-level en DDB (cuántas stations escanearon ya).

---

## 📋 Contexto

**Trigger:** S3 PutObject en `crown_jewel_candidates/{ent}/{sta}/matches.jsonl` → EventBridge → SQS → este Lambda.

**Función:**
1. Leer el `matches.jsonl` que escribió `joyas-priorizer`.
2. Get-or-create del `PHASE1_CYCLE` para el enterprise (query KEM si es CYCLE nuevo).
3. Bulk-indexar cada match en OpenSearch (índice `crown_jewel_candidates`) con `validation_status="pending"`.
4. Marcar la station como `scan_status="complete"` en DDB (`crown-validation-state`).
5. Idempotente: si el mismo archivo llega 2 veces, los docs de OpenSearch se upsertean por `candidate_id`, el contador de STATION no se duplica.

**Interacción con cajas negras / externos:**
- **KEM API:** query `GET /stations?enterprise_id={ent}` cuando hay que crear CYCLE nuevo. API key desde Secrets Manager.
- **OpenSearch:** bulk index al índice `crown_jewel_candidates`.
- **DDB:** put STATION + conditional create CYCLE.

**Lógica:**

1. Parsear mensaje SQS → S3 event → bucket + key. Derivar `enterprise_id`, `station_id` del key.
2. Get-or-create `PHASE1_CYCLE` en `crown-validation-state`:
   - Query DDB: `PK=enterprise_id, SK begins_with "PHASE1_CYCLE#"`, filter `status IN (scanning, ready_for_validation, validating)`.
   - Si existe → reusar `cycle_id`.
   - Si no existe → `cycle_id = uuid4()`, query KEM para `stations_expected`, PUT CYCLE con `ConditionExpression="attribute_not_exists(SK)"`.
3. GET del `matches.jsonl` desde S3, parsear NDJSON (puede ser archivo vacío → seguir).
4. Para cada match, construir el doc de OpenSearch:
   - `candidate_id = sha256(enterprise_id + "|" + station_id + "|" + path)`.
   - Aplicar `normalize()` a `path` y `name` si no vienen ya normalizados.
   - Preservar `matched_patterns`, `matched_business_areas`, `original_category`, `original_business_area`.
   - Setear `validation_status="pending"`, `normalize_version`, `indexed_at`.
5. Bulk index a OpenSearch en chunks de 1000 docs. Si la response tiene errores por doc → reintentar solo los fallidos hasta N veces, sino log ERROR.
6. PUT STATION en DDB:
   - `PK=enterprise_id, SK=PHASE1_STATION#{station_id}#{cycle_id}`.
   - `scan_status="complete"`, `candidates_count=N`, `completed_at=now`, `barrier_counted=false`.
   - Conditional `attribute_not_exists(SK) OR scan_status<>"complete"` (idempotencia ante mensaje duplicado).
7. Log INFO con counters.

---

## ✅ Acceptance Criteria

- **AC01 — Indexa OK:** Por cada PutObject en `crown_jewel_candidates/{ent}/{sta}/matches.jsonl`, todos los matches quedan indexados en OpenSearch con `validation_status="pending"`.
- **AC02 — STATION coherente:** STATION en DDB queda con `scan_status="complete"` y `candidates_count=N`, incluso si N=0.
- **AC03 — Idempotencia indexer:** Mismo archivo procesado 2 veces → `candidate_id` igual → upsert en OpenSearch (no duplica docs). Counter de STATION no se incrementa dos veces (conditional check).
- **AC04 — Idempotencia CYCLE:** Dos primeros eventos casi simultáneos del mismo enterprise → solo se crea 1 CYCLE (conditional create gana exactly-once).
- **AC05 — Resiliencia OS:** Si OpenSearch bulk responde con errores por doc → reintenta esos docs. Si el batch entero falla → log ERROR y SQS retry (eventual DLQ).
- **AC06 — KEM 404:** Si KEM responde 404 para el enterprise → mensaje a DLQ tras 3 reintentos + alarma SNS.
- **AC07 — Logs:** structured JSON con `enterprise_id, station_id, cycle_id, candidates_count, request_id`.

---

## ⚠️ Edge Cases

- `matches.jsonl` vacío (0 líneas) → STATION marca complete con `candidates_count=0`, no se indexa nada en OS.
- `matches.jsonl` con UNA línea malformada → skip esa línea con log WARN, continuar con el resto.
- Race entre dos eventos del mismo enterprise (primera vez) → conditional create gana exactly-once; el otro recibe `ConditionalCheckFailedException`, re-query y usa el cycle existente.
- OpenSearch down → SQS retry → eventual DLQ + alarma.
- DDB throttle → SQS retry.
- STATION ya existe con `scan_status="complete"` (reprocesamiento) → idempotente, no incrementa counter.

---

## ❌ Out of Scope

- El barrier "todas las stations cerraron" → responsabilidad de `phase1-enterprise-barrier` (N2).
- Notificación al cliente → responsabilidad de N2 cuando llegue al threshold.
- Validation mutations → responsabilidad de N3.

---

## 🔒 Threat Surface

Diferido. Notas:
- Bulk-write a OpenSearch — IAM restricto al rol del Lambda.
- KEM API key en Secrets Manager.
- `candidate_id` determinístico — si un atacante puede inferir paths, puede construir IDs. Aceptable porque los paths viven en S3 con encryption + IAM.

---

## ❓ Open Questions

| # | Pregunta | Owner | Default temporal | Bloqueante para |
|---|----------|-------|------------------|-----------------|
| Q1 | Decisión final: una tabla DDB nueva `crown-validation-state` vs reusar `gse-cycles-samples` con nuevos SK prefix | Tech Lead (Skill 02) | tabla nueva | Spec + DevOps |
| Q2 | Política con cycles cerrados que reciben late-arrival STATION (ver Q6 del brainstorm) | Producto | descartar con log WARN | Spec |

---

## 📎 Referencias

- **Brainstorm arquitectónico:** `brainstorms/architecture-refresh-phase-1-2-2026-05-19.md` (sección 2.1 paso 1, sección 3.1)
- **Función de normalización:** `context/classifier-v2/components/phase-1/normalize_category.py`
- **Épica:** TBD (nueva o KT-16369 ampliada)
```

### DevOps gemelo (texto para abrir D-N1)

```markdown
**Infraestructura requerida:**
- Lambda Python en repo nuevo `crown-candidates-indexer`. Mem 512 MB, timeout 300 s.
- SQS standard nueva `crown-candidates-indexer-queue` + DLQ (max receives 5).
- EventBridge Rule sobre `crown_jewel_candidates/` (suffix `matches.jsonl`) → SQS.
- Event Source Mapping SQS → Lambda (batch size 1, dado que cada archivo es independiente y puede ser grande).
- CloudWatch Log Group 30 días + alarma DLQ > 0.

**Permisos IAM:**
- `s3:GetObject`, `s3:HeadObject` sobre `crown_jewel_candidates/*`.
- `dynamodb:Query`, `PutItem`, `UpdateItem`, `GetItem` sobre `crown-validation-state`.
- `es:ESHttpPost`, `es:ESHttpPut` sobre el índice `crown_jewel_candidates`.
- `secretsmanager:GetSecretValue` sobre KEM API key.

**Dependencias:**
- D1 (tabla DDB `crown-validation-state`).
- D2 (bucket `crown_jewel_candidates` + EventBridge — depende del rename del KT-16616).
- D5 (índice OpenSearch + mappings).
```

---

## 🟦 N2 (NUEVO) — Implementación: phase1-enterprise-barrier

### Descripción del ticket

```markdown
## 🎯 Objetivo

Detectar cuándo todas las stations activas de un enterprise terminaron Fase 1, marcar el `PHASE1_CYCLE` como `ready_for_validation` y notificar a la Plataforma Web para que muestre los candidatos al cliente.

---

## 📋 Contexto

**Trigger:** EventBridge Pipe sobre DDB Stream de `crown-validation-state`, filtrado a items con `SK begins_with "PHASE1_STATION#"`.

**Función:** barrier exactly-once. Cuando una STATION pasa a `scan_status="complete"`, suma 1 al contador del CYCLE padre. Cuando el contador iguala `stations_expected`, marca el CYCLE como listo para validación humana y notifica externamente.

**Lógica (por cada stream record en el batch):**

1. Leer `NewImage` del record.
2. Skip rápido si `scan_status != "complete"` o `barrier_counted == true`.
3. Conditional update STATION: `SET barrier_counted=true IF barrier_counted<>true` — esto **gana exactly-once** la carrera contra records duplicados del stream.
4. Si la conditional pasó → `UpdateItem` en CYCLE: `ADD stations_completed=1`.
5. Re-leer (o usar return values) el `stations_completed` actualizado.
6. Si `stations_completed >= stations_expected` → conditional update CYCLE: `SET status="ready_for_validation", ready_at=now IF status="scanning"`.
7. Si la conditional pasó → **publicar notificación** al canal de Plataforma Web (canal TBD — ver Q1).

**Interacción con cajas negras:**
- Plataforma Web: recibe la notificación "cycle X de enterprise Y listo para validar". Canal a definir (SNS topic, GraphQL subscription, webhook).

---

## ✅ Acceptance Criteria

- **AC01 — Exactly-once barrier per STATION:** Cuando una STATION pasa a `complete`, se suma +1 a `stations_completed` del CYCLE exactamente una vez, incluso con stream records duplicados (gracias al flag `barrier_counted`).
- **AC02 — Exactly-once cierre de CYCLE:** El CYCLE pasa a `ready_for_validation` y la notificación se publica exactamente una vez (gracias al conditional `IF status="scanning"`).
- **AC03 — Notify resilience:** Si el publish a Plataforma Web falla después de cerrar el CYCLE → SQS retry del Pipe; eventual DLQ + alarma. (Riesgo conocido: CYCLE marcado pero notificación perdida. Mitigación: idempotencia del consumer en Plataforma Web por `cycle_id`.)
- **AC04 — Skip de records irrelevantes:** Records de tipo CYCLE o REQUEST no procesados (filter del Pipe los descarta, este Lambda igual hace defensive check).
- **AC05 — Logs estructurados:** JSON con `enterprise_id, station_id, cycle_id, stations_completed, stations_expected, request_id`.

---

## ⚠️ Edge Cases

- Stream record duplicado → `barrier_counted=true` ya está → skip silencioso.
- STATION que llega después del cierre del CYCLE (late arrival) → conditional update CYCLE fail (`status<>scanning`) → log WARN, no se reabre. Política diferida (Q6 del brainstorm).
- `stations_expected == 0` (caso degenerado de KEM) → CYCLE pasa a `ready_for_validation` al primer evento. Aceptable.
- Race entre dos updates a STATION (ej. el indexer reescribe) → solo el primero gana el `barrier_counted=true`.

---

## ❌ Out of Scope

- Decidir el canal de notificación a Plataforma Web (Q1).
- Reaper / timeout para CYCLEs que quedan en `ready_for_validation` indefinidos (Q1 del brainstorm).
- Manejo de late-arrival STATIONs distinto al actual "descartar" (Q6 del brainstorm).

---

## 🔒 Threat Surface

Diferido. Notas:
- Notificación a Plataforma Web debe llevar mínima info — solo `cycle_id` y `enterprise_id`. Plataforma Web hace la query a OpenSearch con su propia capa de auth.

---

## ❓ Open Questions

| # | Pregunta | Owner | Default temporal | Bloqueante para |
|---|----------|-------|------------------|-----------------|
| Q1 | Canal de notificación a Plataforma Web (SNS, GraphQL subscription, webhook, email) | Producto + Plataforma Web | stub que loguea | Integración real, no MVP |
| Q2 | Reaper para CYCLEs colgados en `ready_for_validation` | Producto | sin reaper inicialmente | Hardening (no MVP) |

---

## 📎 Referencias

- **Brainstorm arquitectónico:** `brainstorms/architecture-refresh-phase-1-2-2026-05-19.md` (sección 2.1 paso 2, sección 3.2)
- **Patrón de referencia:** `gse-station-status` (Ticket 9 de `tickets-implementacion.md`) — misma técnica de conditional barrier.
- **Épica:** TBD
```

### DevOps gemelo (texto para abrir D-N2)

```markdown
**Infraestructura requerida:**
- Lambda Python en repo nuevo `phase1-enterprise-barrier`. Mem 256 MB, timeout 30 s.
- EventBridge Pipe con:
  - Source: DDB Stream de `crown-validation-state`.
  - Filter: `eventName IN ["MODIFY","INSERT"]` AND `NewImage.SK begins_with "PHASE1_STATION#"`.
  - Target: este Lambda.
  - Batch size 10, batching window 5 s.
  - DLQ propio + alarma DLQ > 0.
- CloudWatch Log Group 30 días.
- SNS topic `phase1-ready-for-validation` (default temporal del canal — confirmar con Plataforma Web).

**Permisos IAM Lambda:**
- `dynamodb:UpdateItem`, `GetItem` sobre `crown-validation-state`.
- `sns:Publish` sobre `phase1-ready-for-validation` (stub temporal).

**Permisos IAM del Pipe (rol del Pipe):**
- `dynamodb:DescribeStream, GetShardIterator, GetRecords, ListStreams` sobre el stream de la tabla.
- `lambda:InvokeFunction` sobre este Lambda.

**Dependencias:** D1 (tabla DDB + Stream activo), D6 (Pipe), notification channel decision.
```

---

## 🟦 N3 (NUEVO) — Implementación: validation-mutation-handler

### Descripción del ticket

```markdown
## 🎯 Objetivo

Procesar las decisiones del cliente (approve, reject, override por archivo, agregar path manual) sobre los candidatos de Fase 1, actualizando OpenSearch y los contadores en DDB.

---

## 📋 Contexto

**Trigger:** invocado por la capa GraphQL de la Plataforma Web (vía AppSync resolver, Lambda direct invoke, o cualquier canal que defina Plataforma Web).

**Mutations soportadas:**

1. `validateCandidateGroup(criteria, decision, actor)` — bulk approve/reject sobre todos los docs que matchean un criterio (`folder` o `matched_pattern`).
2. `overrideCandidate(candidate_id, decision, actor)` — cambia un doc específico (sobrescribe decisión grupal).
3. `addExtraPath(enterprise_id, station_id, path, actor)` — crea un nuevo doc con `validation_status="manually_added"`.

**Lógica común a las 3:**

1. Validar input (`enterprise_id` y `station_id` con regex `^[a-zA-Z0-9\-_]+$`, `cycle_id` UUID, `decision` ∈ {approved, rejected}).
2. Verificar que `PHASE1_CYCLE.status="ready_for_validation"` (conditional read).
3. Aplicar mutation en OpenSearch:
   - **Group:** `UpdateByQuery` con script que setea `validation_status, validation_actor, validation_at`.
   - **Override:** `Update` por `candidate_id`.
   - **Add path:** `Index` doc nuevo con `validation_status="manually_added"`, `original_path = path`, `normalize_version`.
4. Actualizar counters en DDB CYCLE: `ADD approved_count, rejected_count, manually_added_count` según el tipo.
5. Return: cantidad de docs afectados.

---

## ✅ Acceptance Criteria

- **AC01 — Group validation:** `validateCandidateGroup({folder: X}, "approved")` actualiza todos los docs de esa carpeta + cycle_id correspondiente con `validation_status="approved"`. DDB counter `approved_count` se incrementa con la cantidad de docs afectados (eventual consistency aceptable).
- **AC02 — Override individual:** `overrideCandidate(id, "rejected")` cambia ese doc específico. Si antes era `approved` (por bulk) y ahora `rejected` (override): DDB counters se ajustan (`approved_count -= 1`, `rejected_count += 1`).
- **AC03 — Add path:** `addExtraPath` crea doc nuevo con `candidate_id` determinístico (`sha256(ent|sta|path)`). Si ya existe (re-add) → upsert idempotente, no cuenta dos veces.
- **AC04 — Cycle no listo:** Cualquier mutation sobre un CYCLE con `status != "ready_for_validation"` → 409 + log WARN.
- **AC05 — Path traversal en addExtraPath:** Rechaza paths con `..`, null bytes, o caracteres no UTF-8. Test específico.
- **AC06 — Reconciliación:** Job batch de reconciliación (otro ticket) puede recomputar counters desde OpenSearch. Este ticket no garantiza consistencia estricta DDB↔OS, solo eventual.
- **AC07 — Logs:** JSON con `enterprise_id, cycle_id, mutation_type, criteria, decision, affected_count, actor, request_id`.

---

## ⚠️ Edge Cases

- `validateCandidateGroup` con criteria que matchea 0 docs → return 0, log INFO, no toca DDB.
- Doble click rápido del cliente → mismas mutations idempotentes; counter eventualmente consistente.
- `addExtraPath` con path ya manualmente agregado → upsert, no duplica.
- Mutation con `cycle_id` inválido → 404.
- Mutation con `enterprise_id` que no le corresponde al actor → no se valida acá; Plataforma Web lo hace antes (Q7 del brainstorm).
- OpenSearch `UpdateByQuery` con timeout para grupos enormes → ejecutar con `wait_for_completion=false` y devolver task_id para que el cliente haga polling. Decisión de Skill 02.

---

## ❌ Out of Scope

- Auth / tenant isolation — responsabilidad de Plataforma Web (Q7 del brainstorm).
- UI / UX de la validación — responsabilidad del equipo de Plataforma Web.
- Reconciliación de counters DDB↔OpenSearch (ticket aparte).
- Versionado de decisiones (audit log de cada decisión por separado) — opcional, deferred.

---

## 🔒 Threat Surface

Diferido. Notas:
- **Path traversal en `addExtraPath`** (AC05) — validar agresivamente.
- **Cross-enterprise mutation** — el handler **NO valida** que el actor pertenezca al enterprise. Plataforma Web es responsable. Documentar contrato.
- **DoS por `UpdateByQuery` masivo** — rate limit y/o size cap en criteria.

---

## ❓ Open Questions

| # | Pregunta | Owner | Default temporal | Bloqueante para |
|---|----------|-------|------------------|-----------------|
| Q1 | Canal de invocación (AppSync direct, Lambda invoke, REST) | Plataforma Web + backend | Lambda invoke sync | Integración |
| Q2 | Schema GraphQL exacto de las 3 mutations | Plataforma Web | borrador de este ticket | Spec |
| Q3 | Reconciliación DDB↔OS (consistencia estricta o eventual) | Tech Lead | eventual | Spec |

---

## 📎 Referencias

- **Brainstorm arquitectónico:** `brainstorms/architecture-refresh-phase-1-2-2026-05-19.md` (sección 2.1 paso 3, sección 3.3)
- **Esquema OpenSearch:** sección 2.4 del brainstorm.
- **Épica:** TBD
```

### DevOps gemelo (texto para abrir D-N3)

```markdown
**Infraestructura requerida:**
- Lambda Python en repo nuevo `validation-mutation-handler`. Mem 512 MB, timeout 60 s.
- Permite invocación desde Plataforma Web (canal exacto TBD — Q1).
- CloudWatch Log Group 30 días.

**Permisos IAM:**
- `es:ESHttpPost` (UpdateByQuery), `es:ESHttpPut` (Update, Index) sobre índice `crown_jewel_candidates`.
- `dynamodb:UpdateItem, GetItem` sobre `crown-validation-state`.
- `lambda:InvokeFunction` para receivers (si AppSync no lo hace direct).

**Dependencias:** D1, D5, GraphQL schema extension (responsabilidad Plataforma Web).
```

---

## 🟦 N4 (NUEVO) — Implementación: validation-confirm

### Descripción del ticket

```markdown
## 🎯 Objetivo

Materializar las decisiones del cliente en archivos S3 que disparen Fase 2. Endpoint de "confirmar todo" — el cliente da OK final, leemos OpenSearch, escribimos manifest + station files, transicionamos el CYCLE.

---

## 📋 Contexto

**Trigger:** API Gateway `POST /v2/validation/confirm`.

**Body esperado:**
```json
{
  "enterprise_id": "ent-001",
  "cycle_id": "uuid",
  "actor": "user_id de plataforma web"
}
```

**Lógica:**

1. Validar body. Sanitizar IDs.
2. Conditional read del CYCLE: debe estar en `status="ready_for_validation"`.
3. Scroll OpenSearch (`index=crown_jewel_candidates, query={cycle_id, validation_status IN [approved, manually_added]}`) hasta agotar resultados (scroll API, no from/size).
4. Agrupar resultados por `station_id`.
5. Para cada station con files:
   - Escribir `validated_crown_jewels/{ent}/{cycle_id}/station-{X}.jsonl` con un JSON por línea (path, size, etc.).
6. Escribir `validated_crown_jewels/{ent}/{cycle_id}/manifest.json` con:
   ```json
   {
     "enterprise_id": "...",
     "cycle_id": "...",
     "process_type": "crown_validated",
     "stations": ["station-A", "station-B"],
     "stations_expected": 2,
     "total_files": 47,
     "confirmed_at": "ISO-8601",
     "confirmed_by": "actor"
   }
   ```
7. Conditional update DDB CYCLE: `SET status="phase2_triggered", confirmed_at=now IF status="ready_for_validation"`.
   - Si la conditional falla → 409 (doble click, status ya cambió).
8. Si `total_files == 0` → SET `status="phase2_skipped"` en lugar de `phase2_triggered`, escribir manifest pero no station files. Fase 2 no se dispara.
9. El PutObject del `manifest.json` dispara Fase 2 vía EventBridge → SQS FIFO → `gse-cycle-init` con `process_type=crown_validated`.

---

## ✅ Acceptance Criteria

- **AC01 — Happy path 200:** POST con body válido + CYCLE en `ready_for_validation` con N>0 approved → 200, escribe manifest + station files, CYCLE pasa a `phase2_triggered`, Fase 2 se dispara (verificable por mensaje en `gse-validated-cycle-queue`).
- **AC02 — Idempotencia (doble click):** Segunda llamada con mismo cycle_id mientras la primera está en curso o ya terminó → 409 con `current_status` en el body. No se reescriben archivos, no se duplica trigger de Fase 2.
- **AC03 — 0 approved:** Si no hay archivos aprobados → CYCLE pasa a `phase2_skipped`, manifest se escribe con `total_files=0`, Fase 2 NO se dispara (manifest se filtra por size o suffix downstream).
- **AC04 — Body inválido:** 400 con `{field, reason}`. Sin loguear el body crudo.
- **AC05 — CYCLE no existe:** 404.
- **AC06 — Scroll OS:** Manifest con 50k+ archivos se construye sin OOM (scroll API con batches de 1000, escritura streaming).
- **AC07 — Manifest size:** Si total_files > umbral (TBD, ej. 100k) → split en N manifest files con index, o usar S3 multipart. Decisión de Skill 02.
- **AC08 — Logs:** JSON con `enterprise_id, cycle_id, approved_count, rejected_count, manually_added_count, total_files, duration_ms, actor, request_id`.

---

## ⚠️ Edge Cases

- Cliente confirma con CYCLE que cambió de estado entre el page load y el click → 409.
- OpenSearch scroll timeout → reintentar; si persiste → 500 + DLQ.
- S3 PutObject falla a mitad del write de station files → CYCLE queda en `ready_for_validation` (no se actualizó aún) → cliente puede reintentar.
- Cliente actor con permisos insuficientes → no se valida acá; Plataforma Web es responsable. API GW debe tener API key + (opcional) WAF.
- Concurrent confirms del mismo cycle_id desde dos sesiones → conditional gana exactly-once.

---

## ❌ Out of Scope

- Auth fina por enterprise — responsabilidad Plataforma Web + API GW.
- Notificación de "Fase 2 arrancó" al cliente — responsabilidad de Plataforma Web (puede mostrar status del CYCLE).
- Reaper / cancelación post-confirm — no soportado en MVP.
- Re-validación después de confirm (segundo round con el mismo cycle) — fuera de scope; nuevos rounds = nuevo CYCLE.

---

## 🔒 Threat Surface

Diferido. Notas:
- API GW route pública (con API key) — debe agregar tenant validation en Plataforma Web upstream.
- Manifest contiene paths reales del filesystem del cliente — sensitive. Bucket `validated_crown_jewels` con IAM restricto.
- DoS por confirm con cycle_id que tiene millones de approved → AC07 limita tamaño del manifest.

---

## ❓ Open Questions

| # | Pregunta | Owner | Default temporal | Bloqueante para |
|---|----------|-------|------------------|-----------------|
| Q1 | Umbral exacto para split de manifest (50k? 100k?) | Tech Lead (Skill 02) | 100k | Spec |
| Q2 | Trigger downstream — directo S3 EventBridge → SQS FIFO, o llamada explícita | Tech Lead | EventBridge | Spec |
| Q3 | Política de retención de los archivos en `validated_crown_jewels/` | DevOps + Producto | 30 días | DevOps ticket |

---

## 📎 Referencias

- **Brainstorm arquitectónico:** `brainstorms/architecture-refresh-phase-1-2-2026-05-19.md` (sección 2.1 paso 4, sección 3.4)
- **Esquema manifest:** sección 2.5 del brainstorm.
- **Épica:** TBD
```

### DevOps gemelo (texto para abrir D-N4)

```markdown
**Infraestructura requerida:**
- Lambda Python en repo nuevo `validation-confirm`. Mem 1024 MB, timeout 300 s (por manifest grande).
- API GW route nueva `POST /v2/validation/confirm` integrada con este Lambda. Auth: API key.
- Bucket S3 `validated_crown_jewels` con encryption AES-256, public-access block, EventBridge notifications habilitado, lifecycle 30 días.
- EventBridge Rule sobre `validated_crown_jewels/` (suffix `manifest.json`) → SQS FIFO `gse-validated-cycle-queue.fifo`.
- SQS FIFO `gse-validated-cycle-queue.fifo` + DLQ.
- CloudWatch Log Group 30 días + alarma sobre 5xx.

**Permisos IAM Lambda:**
- `es:ESHttpPost` (scroll search) sobre índice `crown_jewel_candidates`.
- `dynamodb:UpdateItem, GetItem` sobre `crown-validation-state` (conditional).
- `s3:PutObject` sobre `validated_crown_jewels/*`.

**Dependencias:** D3 (bucket `validated_crown_jewels`), D4 (SQS FIFO), D5 (índice OS), D7 (API GW route).
```

---

## Resumen del batch

| # | Componente | Tipo | Bloquea a | Bloqueado por |
|---|---|---|---|---|
| KT-16616 MOD | joyas-priorizer | Edit ticket vivo | N1 | — |
| N1 | crown-candidates-indexer | New ticket | N2 | KT-16616, D1, D2, D5 |
| N2 | phase1-enterprise-barrier | New ticket | Plataforma Web | N1, D1, D6 |
| N3 | validation-mutation-handler | New ticket | N4 | Plataforma Web (schema), D1, D5 |
| N4 | validation-confirm | New ticket | Fase 2 | N3, D3, D4, D5, D7 |

**Siguiente batch sugerido:**
- N5–N10 (Fase 2 — texto ya existe en `tickets-implementacion.md`, solo necesita format de paste a Jira + refactor de N5 para multi-trigger).
- D1–D8 (DevOps — texto en `orquestacion-backend.md` + suma de D-N1 a D-N4 de arriba).
