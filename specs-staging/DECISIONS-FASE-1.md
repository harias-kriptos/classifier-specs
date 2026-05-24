# Decisiones cerradas — Fase 1

> Cerradas: **2026-05-23** en sesión con Haroldo.
> Aplican a las 7 specs de Fase 1: KT-16613, KT-16614, KT-16616, KT-17024, KT-17025, KT-17026, KT-17027.
> Las specs en `specs-staging/` deben leerse junto con este doc — las "Open questions" que aparecen ahí ya están resueltas acá.

---

## 1. Decisiones técnicas (internas)

| # | Pregunta | Decisión |
|---|---|---|
| D1 | KT-16616 — qué texto matchea Aho-Corasick | **Solo `name_normalized`** (no path). Mayor precision, menor recall. El `path_normalized` se sigue calculando y se guarda en OS para UX (filtros por folder), pero NO se incluye en el target del match. |
| D2 | KT-16616 — empaquetado de `pyahocorasick` | **venv archive `.tar.gz` en S3** referenciado con `--archives` en `sparkSubmitParameters`. Versión pineada. |
| D3 | KT-17024/26/27 — auth a OpenSearch | **IAM SigV4** con `requests-aws4auth`. Cada Lambda firma con su execution role. Sin secrets que rotar. |
| D4 | KT-17027/28 — modelo de cycles | **STATION es la unidad atómica de trabajo. CYCLE es el estado global agregado por enterprise.** Un solo `cycle_id` por iteración del pipeline para una enterprise; N STATIONs adentro corriendo independientes. |
| D5 | KT-17027 — validation mode | **Un solo confirm global por enterprise**. UI puede agrupar candidatos por bloque/station/keyword para UX, pero el `confirmValidation` mutation es uno y dispara Fase 2 per-station internamente. Se elimina el parámetro `station_id` opcional del confirm. |
| D6 | KT-17027 — umbral split de manifest | **50k files** por manifest single. Si excede, split en N chunks con index. |
| D7 | KT-17024 — bulk chunk size OpenSearch | **1000 docs default + env var `BULK_CHUNK_SIZE` override** para tunear sin redeploy. Independiente del paginador del UI (10/50/100). |
| D8 | KT-16614 — HeadObject pre-EMR | **No**. Confiamos en el evento EventBridge. Si el archivo no existe, EMR maneja el 404 downstream. Ahorra una llamada S3 por invocación. |
| D9 | KT-16613 — UTF-8 inválido en descompresión | **Log WARN y continuar**. Una línea mala no aborta el archivo completo. PySpark downstream salta JSON inválido también. |
| D10 | KT-17024 — cache de KEM | **Sin cache**. 1 llamada a KEM por cycle nuevo (cuando aterriza la primera matches.jsonl de la enterprise). Las siguientes N-1 stations reusan el CYCLE existente. Tráfico estimado: ~1-2 calls por enterprise por iteración. |

## 2. Decisiones de producto + UX (externas que se cerraron acá)

### D11 — Notificación a Plataforma Web: polling, NO push

**No hay SNS topic** de "ready_for_validation". La Plataforma Web tiene una pantalla de progreso que **consulta** el estado del CYCLE vía GraphQL (query directo a OS/DDB y/o subscription).

**Pantalla del cliente muestra:**
- Stations procesadas / pendientes (derivado de `stations_expected` − `stations_completed`)
- Candidatos detectados hasta ahora
- Estado global del CYCLE
- Cuando llega a `stations_complete` → **se habilita el botón "Confirmar todo"**

**Impacto en infra:** **drop el SNS topic `phase1-ready-for-validation`**.
- [KT-17011](https://kriptosteam.atlassian.net/browse/KT-17011) (DevOps shared) **simplifica** — queda solo el Secret KEM. No SNS topic.
- [KT-17025](https://kriptosteam.atlassian.net/browse/KT-17025) Lambda (`phase1-enterprise-barrier`) ya no publica a SNS — solo actualiza `CYCLE.status` en DDB.

### D12 — Estados del CYCLE renombrados (más descriptivos)

| Estado anterior | Estado final | Significado | Cliente puede... |
|---|---|---|---|
| `scanning` | `scanning` | Algunas o todas stations escaneando | Ver candidatos parcial. Aprobar/rechazar incrementalmente. **NO confirmar.** |
| `ready_for_validation` | **`stations_complete`** | Todas las stations escanearon + matchearon | Mismo + **habilita "Confirmar todo"** |
| `validating` | (eliminado) | — | No se usa. La validación es continua entre `scanning` y `stations_complete`. |
| `phase2_triggered` | **`confirmed`** | Cliente dio OK final | Solo lectura |
| (nuevo) | `phase2_collecting` | GSE en curso | Solo lectura, progreso visible |
| `complete` | `complete` | LLM clasificó, fin | Solo lectura, resultados |

Validación está permitida en `scanning` y `stations_complete`. Confirm solo en `stations_complete`.

### D13 — Invocación de validation-mutation-handler: AppSync resolver

[KT-17026](https://kriptosteam.atlassian.net/browse/KT-17026) se invoca como **resolver de AWS AppSync** (no API Gateway, no Lambda direct invoke).

**Impacto:**
- Event shape: AppSync resolver event (no API GW event ni custom dict).
- IAM: Lambda resource policy permite AppSync; AppSync invoca con su rol.
- Las queries (read) las maneja AppSync **directo contra OpenSearch** (sin Lambda intermedio) — más rápido y simple.

### D14 — GraphQL schema (predefinido)

Esquema completo en archivo aparte: **[`graphql-schema-appsync.md`](graphql-schema-appsync.md)**. Para entrega a Plataforma Web. Incluye:
- Type `Candidate` con 22 campos (mirror del doc OS)
- Enum `ValidationStatus` y `CycleStatus`
- Type `CycleProgress` (para la pantalla de progreso)
- Queries: `cycleProgress`, `crownJewelCandidates` (con filtros + paginación)
- Mutations: `validateCandidateGroup`, `overrideCandidate`, `addExtraPath`, `confirmValidation`
- Subscription: `onCycleStatusChange` (para la UI en tiempo real)

### D15 — Formato del tree NDJSON (confirmado, no requiere sync con Nelson)

5 campos por línea — coincide con el ejemplo provisto por Haroldo:

```jsonl
{"name": "backup-old-491", "path": "/Users/carla.vega/Documentos/RRHH-General/", "size": 6915320, "extension": "bak", "modified_date": "2024-08-20T12:00:00Z"}
```

**Se cierra la dependencia con [KT-16920](https://kriptosteam.atlassian.net/browse/KT-16920).**

### D16 — Late-arrival STATION: mergear si todavía no confirmado

Cuando una STATION termina su matches.jsonl después de que el CYCLE pasó a `stations_complete`:

| `CYCLE.status` actual | Acción |
|---|---|
| `scanning` | **Caso normal** — agregar STATION, barrier sigue contando |
| `stations_complete` | **Mergear**: `crown-candidates-indexer` detecta que la STATION es nueva (no estaba en `stations_expected`), incrementa `CYCLE.stations_expected += 1`, indexa candidatos, agrega STATION. Barrier re-evalúa en próximo stream event (puede volver a `scanning` momentáneamente si 5+1=6 > 5 stations_completed, hasta que la nueva termine de procesarse — UX: progress bar puede regresar de "5/5" a "5/6"). |
| `confirmed` / `phase2_collecting` / `complete` | **Descartar** con log WARN. Station entra al próximo cycle (re-escaneo). |

---

## 3. Open questions que aún quedan abiertas (no-bloqueantes para Skill 04)

| # | Pregunta | Owner | Default |
|---|---|---|---|
| OQ1 | Reaper para CYCLEs que el cliente nunca confirma (timeout) | Producto | Sin reaper en MVP |
| OQ2 | Auth del API GW `/v2/gse/request-complete`: API key vs JWT | Producto | API key MVP |
| OQ3 | Threat surface completo (tenant isolation cross-cutting) | Tech Lead | Mitigaciones puntuales en cada spec; análisis cross-cutting deferido |
| OQ4 | Versionado de `normalize_category.py` (bump policy) | Equipo IA | `1.0.0` inicial, sin migration plan |

Estas no bloquean implementación de Fase 1. Las dos primeras son políticas (defaults razonables), las dos últimas son hardening post-MVP.

---

## 4. Cambios derivados a aplicar

### En classifier-specs

- [x] Crear este doc (`DECISIONS-FASE-1.md`).
- [x] Crear `graphql-schema-appsync.md` con el schema completo.
- [ ] Actualizar [`KT-17011`](https://kriptosteam.atlassian.net/browse/KT-17011) DevOps: **drop SNS topic**, queda solo Secret KEM. Comentario en Jira.
- [ ] Actualizar [`KT-17014`](https://kriptosteam.atlassian.net/browse/KT-17014) DevOps: canal definitivo = AppSync resolver (no TBD). Comentario en Jira.
- [ ] Actualizar [`KT-17025`](https://kriptosteam.atlassian.net/browse/KT-17025) (código): drop publish a SNS. Solo update DDB con `status="stations_complete"`. Comentario en Jira.
- [ ] Actualizar [`KT-17026`](https://kriptosteam.atlassian.net/browse/KT-17026) (código): event shape = AppSync resolver. Mutations definidas en GraphQL schema. Comentario en Jira.
- [ ] Actualizar [`KT-17027`](https://kriptosteam.atlassian.net/browse/KT-17027) (código): drop `station_id` opcional del body. Conditional check usa `status="stations_complete"`. Comentario en Jira.
- [ ] Actualizar `dev-tickets.md` y `devops-tickets.md` con los cambios.
- [ ] Actualizar `dashboard.html` con los estados nuevos del CYCLE.

### En Jira (comentarios para handoff)

- KT-17011, KT-17014, KT-17025, KT-17026, KT-17027 reciben comentarios con el resumen de qué cambia.

---

## 5. Estado final de Fase 1

**11 decisiones cerradas. Las 4 open questions restantes no bloquean Skill 04.**

Las 7 specs de Fase 1 están listas para arrancar Skill 03 (Plan) → Skill 04 (TDD) apenas:
1. DevOps destrabe [KT-16726](https://kriptosteam.atlassian.net/browse/KT-16726) (bloqueo del sprint vivo).
2. DevOps cree los recursos shared: DDB ([KT-17009](https://kriptosteam.atlassian.net/browse/KT-17009)), OpenSearch index ([KT-17010](https://kriptosteam.atlassian.net/browse/KT-17010)), Secret KEM ([KT-17011](https://kriptosteam.atlassian.net/browse/KT-17011) sin SNS).
3. Equipo Plataforma Web acepte el GraphQL schema entregado y arme su AppSync.
