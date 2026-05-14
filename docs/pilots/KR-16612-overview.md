# Piloto KR-16612 — `tree-url-generator`

> Primera ejecución end-to-end del framework `classifier-specs` sobre un ticket real del Classifier de Kriptos.
> Fecha: 2026-05-13
> Owner: Haroldo Arias
> Estado: Skills 01-02 completadas. Skills 03-05 pendientes.

---

## 1. ¿Por qué este piloto?

Se eligió `tree-url-generator` (KR-16612, Fase 1 backend) como caso piloto del framework porque cumple los criterios mínimos para validar el flujo de 5 pasos sin sobrecargarlo:

- **Autocontenido:** no depende de cajas negras externas (Signal Handler, Anonymizer, LLM, KEM).
- **5 AC bien definidos** en el ticket original — suficientes para refinar con Skill 01 y formalizar con Skill 02.
- **Threat surface real:** API pública que firma URLs S3 → Skill 02 produce un threat model con valor real, no de juguete.
- **Stack canónico:** Python 3.11 + Lambda + pydantic + pytest + moto. Si funciona acá, el patrón replica a los otros 9 tickets del backend.
- **Tamaño correcto:** ni trivial ni épico. Un sprint de un dev.

---

## 2. Setup

| Item | Valor |
|---|---|
| Ticket | [KR-16612](https://kriptosteam.atlassian.net/browse/KR-16612) |
| Epic padre | [KR-16369](https://kriptosteam.atlassian.net/browse/KR-16369) — Fase 2 backend |
| Repo del producto | `kriptos-io/s3-tree-uploader` |
| Repo del framework | `harias-kriptos/classifier-specs` (este repo) |
| Sprint | KR-Sprint 2026-Q2-MAY-2 |
| Asignado | Haroldo Arias |
| Prioridad | P2 |
| Stack | Python 3.11 / AWS Lambda |

### MCPs conectados durante el piloto

- ✅ Atlassian (Jira + Confluence)
- ❌ GitHub — **no conectado**. El handoff al PR del producto se hizo manual con `git` + `gh` CLI.
- Otros conectados pero no usados: HubSpot, Vercel, Microsoft 365, Canva, Gamma, Miro, Figma, Webflow, Google Drive, Zoom, GoDaddy, Fathom, Apollo, Make, Brex.

---

## 3. Ejecución por skill

### Skill 01 — Brainstorm

| Atributo | Valor |
|---|---|
| Cliente | Claude Web (Proyecto Kriptos AI Delivery) |
| Modelo | Opus 4.7 |
| Rol | Product Manager (`roles/product-manager.md`) |
| Skill file | `skills/01-brainstorm.md` |
| Duración | ~30 min, 6 rondas de challenge dirigido |
| Output | Comment en KR-16612 con resumen estructurado (formato definido en Skill 01) |

**Cambios materiales que produjo Skill 01 vs ticket original:**

- AC04 enumerado exhaustivamente (12+ casos en lugar de "body inválido → 400" genérico).
- AC02/AC03 testeados a 2 niveles (unit + integración con `moto`) por separación de responsabilidad Lambda vs S3.
- AC05 reordenado: `tree_id` se genera **antes** de validar (correlación en logs de error).
- AC06 **nuevo:** fail-fast en cold start si `COMPRESSED_TREES_BUCKET` falta.
- **8 headers firmados** en lugar de 7 (incluye `x-amz-server-side-encryption: AES256` como belt-and-suspenders).
- **4 open questions** formalmente abiertas con owner y default temporal (Q1 bloqueante).
- **5 amenazas STRIDE** mapeadas en threat surface preliminar (T1 bloqueada hasta resolver auth).
- Validation engine con pydantic v2: reglas estructurales aplicadas, formatos específicos (`fingerprint`, `agent_version`) stubeados con defaults permisivos.

**Veredicto del checklist de salida:** ✅ los 4 ítems cumplidos antes de pasar a Skill 02.

---

### Skill 02 — Spec + Threat Model

| Atributo | Valor |
|---|---|
| Cliente | Claude Web (mismo Proyecto) |
| Modelo | Opus 4.7 |
| Rol | Architect (`roles/architect.md`) |
| Skill file | `skills/02-spec-threat-model.md` |
| Duración | ~10 min |
| Outputs | `specs/001-tree-url-generator.md` + `docs/security/tree-url-generator-threat-model.md` en repo del producto |

**Inputs leídos por la skill:**

1. `skills/02-spec-threat-model.md`
2. `roles/architect.md`
3. `templates/SPEC_TEMPLATE.md`
4. Comment del brainstorm de Skill 01 (en KR-16612)
5. Descripción del ticket KR-16612 (post-refinamiento)
6. `context/classifier-v2/ecosystem.md`
7. `context/classifier-v2/current-decisions.md`
8. `stacks/python-lambda/rules.md`

**Outputs producidos:**

- **Spec** — 11 secciones según `SPEC_TEMPLATE.md`. ~37 tests nombrados, ≥1 por AC. Plan de commits TDD definido.
- **Threat model** — 6 amenazas STRIDE (T1–T6), surfaces, assumptions, out-of-scope explícito, open security questions.

**Ajustes mid-flight:**

- Base branch corregida de `develop` a `main` por feedback del owner durante la sesión.
- Q1 reframeada: pasa de "bloquea deploy a prod" a "bloquea merge a main" — semántica más estricta y más simple de enforzar via branch protection.

---

### Skills 03–05 (pendientes)

| Skill | Estado | Notas |
|---|---|---|
| 03 — Plan + tareas atómicas | ⏳ pendiente | Se ejecuta cuando el PR de la spec esté abierto en el repo del producto. Output esperado: `todo.md` con ~9 vertical slices RED→GREEN→REFACTOR. Modelo: Sonnet 4.6. |
| 04 — TDD implementation | ⏳ pendiente | Se ejecuta en Claude Code dentro del repo del producto. Modelo barato (Qwen/DeepSeek vía OpenCode). |
| 05 — Review + evals | ⏳ pendiente | Claude Code o CI. Modelo: Sonnet 4.6. Sin componente de evals (la Lambda es determinística). |

---

## 4. Material producido

### En Jira

- Descripción de KR-16612 refinada y actualizada (versión post-brainstorm).
- Comment en KR-16612 con el resumen estructurado de Skill 01 — formato definido en `skills/01-brainstorm.md`.

### En el repo del producto (`kriptos-io/s3-tree-uploader`)

- Branch: `KR-16612-tree-url-generator` (desde `main`).
- Commit: `chore: spec for tree-url-generator (KR-16612)`.
- Archivos:
  - `specs/001-tree-url-generator.md`
  - `docs/security/tree-url-generator-threat-model.md`
- PR: _(completar URL cuando esté abierto)_

### En este repo (`harias-kriptos/classifier-specs`)

- `brainstorms/KR-16612-tree-url-generator.md` — output completo de Skill 01.
- `docs/pilots/KR-16612-overview.md` — este documento.

---

## 5. Hallazgos / Lessons learned para el framework

### ✅ Lo que funcionó bien

- **El brainstorm refina mucho** contra un ticket "razonable". El ticket original ya tenía 5 AC plausibles; Skill 01 produjo +1 AC nuevo, +12 sub-casos enumerados, +4 open questions, +5 amenazas STRIDE, +1 decisión clave (8 headers en lugar de 7). El valor es real, no cosmético.
- **La separación de roles ayuda al output.** Product Manager (Skill 01) hace preguntas, Architect (Skill 02) escribe el contrato. Distintos modos de pensamiento, distintos artifacts.
- **El template SPEC_TEMPLATE.md hace su trabajo.** La sección §7 (test plan) forzó nombrar 37 tests antes de tocar código — eso es exactamente el contrato TDD que Skill 04 va a ejecutar.
- **El threat model temprano descubre bloqueos reales.** Q1 (auth) hubiera salido eventualmente; salió ahora, antes de cualquier línea de código. Esto es lo que separa este flujo del flujo "JIRA → código".

### ⚠️ Fricciones detectadas

- **Falta GitHub MCP en Claude Web.** El handoff entre Skill 02 y el commit/PR es manual. No es bloqueador, pero suma 5 minutos de fricción al final del flujo. Acción: conectar GitHub MCP al Proyecto antes del próximo piloto.
- **Confusión sobre dónde viven los outputs.** En la sesión hubo ambigüedad sobre si los archivos de Skill 02 van al repo del producto o también al repo de specs. Acción: clarificar en `CLAUDE_PROJECT.md` y en el README principal: **los outputs técnicos (spec, threat model) van al repo del producto; este repo solo guarda evidencia del piloto y context updates si los hubo**.
- **El usuario quiso saltar pasos al menos una vez.** "¿Podés hacer los PRs?" — la skill empujó back correctamente y dio alternativas. Bien, pero documentar que esto va a pasar siempre y es esperado.

### 🔧 Ajustes propuestos al framework

| # | Ajuste | Donde aplica |
|---|---|---|
| 1 | Conectar GitHub MCP al Proyecto de Claude Web | `CLAUDE_PROJECT.md` — sección MCPs |
| 2 | Aclarar "outputs técnicos van al repo del producto, no a este repo" | `README.md` + `CLAUDE_PROJECT.md` |
| 3 | Documentar que el flujo Skill 02 → PR es manual sin GitHub MCP | `skills/02-spec-threat-model.md` — sección output (✅ ya hecho) |
| 4 | El template ya cubre §11 con `main` como base — confirmar que está así | `templates/SPEC_TEMPLATE.md` (✅ ya hecho) |

Ninguno de los ajustes es un cambio estructural al flujo. El flujo de 5 pasos no se modifica.

---

## 6. Métricas del piloto

| Métrica | Valor |
|---|---|
| Tiempo total (Skills 01-02) | ~40 min |
| AC en el ticket original | 5 |
| AC en la spec final | 6 (AC06 nuevo) |
| Sub-casos enumerados (AC04) | 19 |
| Tests nombrados en §7 | ~37 |
| Open questions formalizadas | 4 (1 bloqueante) |
| Amenazas STRIDE | 6 (T1–T6) |
| Líneas de código de producción escritas | 0 (correcto — Skill 02 no escribe código) |
| Decisiones técnicas que cambiaron por el brainstorm | 4 (8 headers, orden de tree_id, fail-fast, validation engine) |
| Modelos usados | Opus 4.7 (Skills 01-02) |
| Tokens estimados (Skills 01-02) | ~80k input + ~25k output |

---

## 7. Estado actual y siguiente paso

**Estado:** Skill 02 completada. PR pendiente de abrirse en `kriptos-io/s3-tree-uploader` por Haroldo (manualmente porque no hay GitHub MCP). Q1 sigue abierta — bloquea el merge a `main`.

**Siguiente paso del piloto:**

1. Haroldo abre el PR `chore: spec for tree-url-generator (KR-16612)` contra `main` en el repo del producto.
2. Una vez abierto el PR (aunque no esté mergeado todavía), se invoca **Skill 03 — Plan** para generar `todo.md` con las tareas atómicas TDD. Modelo: Sonnet 4.6.
3. Skill 04 y 05 corren en Claude Code adentro del repo del producto.
4. Una vez completadas todas las skills, este overview se actualiza con los resultados finales y el piloto se cierra.

**Siguiente piloto sugerido (cuando este cierre):** `gse-cycle-init` (Ticket 5). Razón: introduce DynamoDB, SQS FIFO e idempotencia — superficies que `tree-url-generator` no tocó. Validar que el framework escala a componentes con más cajas negras.

---

## 8. Anexos

### Anexo A — Stack confirmado por el piloto

- Python 3.11+ ✅
- AWS Lambda ✅
- Layout hexagonal (`src/{domain,application,adapters}` + `handler.py`) ✅
- pydantic v2 ✅
- aws-lambda-powertools ✅
- pytest + moto ✅
- ruff + mypy strict ✅
- Coverage ≥ 80% ✅

### Anexo B — Decisiones cerradas en el brainstorm

1. Bucket name por env var, no hardcode.
2. 8 headers firmados (no 7) por SSE belt-and-suspenders.
3. `tree_id` generado antes de validar.
4. Idempotencia y rate limiting fuera de scope.
5. Infra (API GW, IAM, bucket, WAF) ya existe — repo solo incluye código.

### Anexo C — Decisiones diferidas

| ID | Pregunta | Owner | Default temporal |
|---|---|---|---|
| Q1 | Auth del endpoint | Haroldo Arias | _(ninguno — bloquea merge)_ |
| Q2 | Formato de `fingerprint` | Equipo agente | string 1–128 chars |
| Q3 | Formato de `agent_version` | Equipo agente | string 1–32 chars |
| Q4 | Idempotencia global (`tree-state mechanism`) | Arquitectura | _(aceptada limitación; ticket aparte)_ |
