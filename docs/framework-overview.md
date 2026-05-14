# Kriptos AI Delivery Framework

Spec-driven development con agentes IA para el equipo de Kriptos. Convierte ideas y tickets de Jira en código probado y mergeable, con disciplina TDD enforced y trazabilidad completa.

> **Documento base para presentación.** Cada sección está pensada como un slide.

---

## 1. TL;DR

| Antes | Con el framework |
|---|---|
| Idea → reunión → JIRA → código → bugs en code review | Idea → brainstorm dirigido → spec testable → plan atómico → TDD enforced → review pre-humano |
| Threat model "después" o nunca | Threat model **antes** del código, como parte de la spec |
| Tests "cuando haya tiempo" | Tests **antes** del código, enforced por commits |
| Decisiones técnicas en código review tarde | Decisiones cerradas o explícitamente diferidas antes de tocar código |
| Un solo modelo caro para todo | Routing: Opus para diseño, Sonnet para review, modelos baratos para TDD loop |

**Pilar central:** una skill = un paso = un rol = un artefacto. No se saltean pasos. No hay código sin spec.

---

## 2. El flujo en una vista

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  1. Brainstorm  │ -> │ 2. Spec + threat│ -> │     3. Plan     │
│   Claude Web    │    │   Claude Web    │    │  Claude Code    │
│   Opus 4.7      │    │   Opus 4.7      │    │  Sonnet 4.6     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                                                       v
                       ┌─────────────────┐    ┌─────────────────┐
                       │  5. Review +    │ <- │ 4. TDD Implement│
                       │     evals       │    │  Claude Code    │
                       │ Sonnet 4.6 + CI │    │ Qwen / DeepSeek │
                       └─────────────────┘    └─────────────────┘
```

| # | Skill | Cliente | Modelo | Quién la invoca |
|---|-------|---------|--------|-----------------|
| 1 | Brainstorm | Claude Web | Opus 4.7 | Cualquiera (CEO, PM, comercial, tech lead) |
| 2 | Spec + Threat Model | Claude Web | Opus 4.7 | Architect / Tech Lead |
| 3 | Plan + tareas atómicas | Claude Code (o Web) | Sonnet 4.6 | Tech Lead / Developer |
| 4 | TDD Implementation | Claude Code | Qwen / DeepSeek / Devstral | Developer |
| 5 | Review + evals | Claude Code o CI | Sonnet 4.6 | Developer / CI bot |

---

## 3. Skill 01 — Brainstorm

### Propósito

Refinar una idea cruda o un ticket pobre **hasta que sea escribible como spec**. El agente no decide; desafía.

### Enfoque (mindset)

> *"El agente trae las preguntas, vos traés las respuestas."*

Una sola conversación. Máximo 3 preguntas por turno (context window pequeño es mejor). Bifurca por modo:

- **Modo A — idea cruda:** persona no técnica describe en lenguaje natural → la skill refina hasta producir épica/ticket en Jira o página en Confluence.
- **Modo B — ticket Jira existente:** el agente lee el ticket → lo refina → actualiza el mismo ticket con AC testables y threat surface preliminar.

### Actores

| Rol | Caso de uso |
|---|---|
| CEO / liderazgo | Trae una idea estratégica para validar |
| Product Manager | Refina una iniciativa antes del sprint |
| Comercial | Captura un pedido de cliente |
| Tech Lead | Valida que un ticket esté listo para implementación |

No requiere vocabulario técnico para invocarla.

### Procedimiento (resumen)

1. Restatement — el agente confirma qué entendió en 2-3 frases.
2. Identifica el caso de persistencia (A / B / C / D) **antes** de empezar a refinar.
3. Desafía en 6 dimensiones, una a la vez: scope, AC testables, edge cases, integración, threat surface, observabilidad.
4. Para cuando el exit checklist es verdadero (4 ítems).

### Entregables

- Comentario estructurado en el ticket de Jira (formato definido en la skill).
- Descripción del ticket Jira actualizada (si aplica).
- Copia en `brainstorms/<slug>.md` del repo de specs (trazabilidad).
- Página Confluence creada o actualizada (si aplica).

### Persistencia (espejo en Skill 02)

```
¿De dónde vino la idea?
  -> Ticket Jira con épica clara          ->  Caso C: comentario + transition
  -> Ticket Jira sin épica                ->  Caso B: usuario elige editar épica o no
  -> Página Confluence draft              ->  Caso D: actualiza Confluence + opcional Epic
  -> Idea cruda sin nada                  ->  Caso A: usuario elige destino
```

---

## 4. Skill 02 — Spec + Threat Model

### Propósito

Convertir el brainstorm en una **spec formal** que sirve de contrato para el resto del pipeline. Identificar gaps de dominio y proponer crearlos.

### Enfoque

> *"Sin spec aprobada no hay código. Test plan antes del código."*

La spec sigue una plantilla rígida (11 secciones). Cada AC mapea a al menos un test nombrado. Si un AC no es testable, la AC no está terminada. Threat model con STRIDE estructurado, mitigaciones citadas a línea de código o test.

Antes de escribir la spec, el agente detecta gaps de contexto en `context/classifier-v2/` y propone crearlos como parte del mismo refinamiento.

### Actores

| Rol | Caso de uso |
|---|---|
| Architect | Diseña el contrato técnico |
| Tech Lead | Valida que el contrato sea implementable |
| Senior Developer | Revisa decisiones técnicas |

**No para roles no técnicos.** La output es densa y referencia el stack.

### Procedimiento (resumen)

1. Lista los inputs (brainstorm, épica, drafts) y los reconcilia. Si hay contradicciones, pregunta cuál es la fuente de verdad.
2. **Detect missing context** — busca gaps de dominio o stack. Si faltan, propone crearlos antes de escribir la spec.
3. Genera la spec completa siguiendo `SPEC_TEMPLATE.md` (sin skipear secciones).
4. Test plan obligatorio: 1+ test nombrado por AC.
5. Threat model con STRIDE si hay surface.

### Entregables

Cada entregable se entrega como **artifact markdown editable en el chat** (descargable, sin perderse en el scroll):

| Artifact | Repo destino |
|---|---|
| `specs/NNN-<slug>.md` | repo del producto |
| `docs/security/<slug>-threat-model.md` | repo del producto (si hay threat surface) |
| `context/classifier-v2/<archivo>.md` | repo de specs (si hubo gaps) |
| `stacks/<stack>/rules-<addendum>.md` | repo de specs (si hubo gaps de stack) |

Inline en el chat: commit plan + persistencia sugerida + siguiente paso.

### Persistencia

- Spec + threat model → repo del producto (branch `KR-XXXX-<slug>` desde `main`).
- Context updates → PR separado en repo de specs.
- Comentario en Jira con link al PR de la spec + transition a `Spec ready`.

---

## 5. Skill 03 — Plan + tareas atómicas

### Propósito

Descomponer la spec aprobada en un **`todo.md` con slices verticales TDD-friendly**. Cada tarea es un ciclo RED → GREEN → REFACTOR. Si no es atómica, partirla.

### Enfoque

> *"Una tarea = un ciclo TDD = tres commits. Ni más, ni menos."*

Slices verticales: cada tarea es testable independientemente, no depende de tareas posteriores. Máximo ~30 min por tarea. Máximo 10 slices por spec.

### Actores

| Rol | Caso de uso |
|---|---|
| Tech Lead | Descompone antes de delegar |
| Developer | Auto-descompone antes de implementar |

### Procedimiento (resumen)

1. Lee la spec aprobada.
2. Identifica slices verticales (testables end-to-end dentro de su scope).
3. Para cada slice, escribe 3 sub-pasos: RED (test name), GREEN (módulo a tocar), REFACTOR (opcional).
4. Ordena por dependencia.

### Entregables

- `todo.md` en la raíz del repo del producto.
- Comentario en Jira con link al plan (usando `JIRA_PLAN_COMMENT.md`).

### Dónde corre

Puede ser Claude Web o Claude Code. **Recomendado: Claude Code** para que `todo.md` se escriba directamente al disco y haya continuidad con Skill 04.

---

## 6. Skill 04 — TDD Implementation

### Propósito

Ejecutar `todo.md` tarea por tarea, en ciclos TDD estrictos enforced por commits.

### Enfoque

> *"RED antes que GREEN, siempre. Sin excepciones."*

Por cada tarea:

```
1. RED:      escribir test → pytest falla → commit  chore: <behavior> (failing)
2. GREEN:    impl mínima  → pytest pasa  → commit  feat: <behavior> (passing)
3. REFACTOR: cleanup       → pytest verde → commit  refactor: <what>
```

Si después de 3 intentos no pasa: reportar **BLOCKED**. No improvisar. No editar el test para hacerlo pasar.

### Actores

- Developer (humano o agente). El humano supervisa pero no escribe código línea por línea.

### Cliente y modelo

- **Cliente:** Claude Code (CLI dentro del repo del producto) **o** OpenCode / Crush para modelos baratos.
- **Modelo recomendado:** Qwen / DeepSeek / Devstral. Razón: este paso quema tokens en loop; Opus es desperdicio acá.

### Limits of autonomy (no negociables)

El agente NO debe sin aprobación explícita:

- Push directo a `main`.
- Merge de un PR.
- Instalar dependencia nueva.
- Modificar workflows de CI o branch protection.
- Disable de hook o scanner.
- Usar `--no-verify`, `--force`, `--force-with-lease`.
- Editar un test para hacerlo pasar.
- Decidir scope fuera de la spec.

### Entregables

- Branch `KR-XXXX-<slug>` con secuencia de commits TDD limpia.
- Tests pasando, coverage ≥ 80%, ruff + mypy clean.
- PR draft creado con `templates/PR_DESCRIPTION.md`.
- Transition Jira a `In Review`.

---

## 7. Skill 05 — Review + evals

### Propósito

Validar que la implementación matchea la spec y pasa todos los gates **antes** de pedir review humano.

### Enfoque

> *"La máquina hace lo verificable, el humano hace lo interpretable."*

Pre-flight check exhaustivo. Reporta READY o BLOCKED. Nunca arregla silenciosamente — si algo está roto, vuelve a Skill 04.

### Actores

- Developer (corre antes de marcar el PR como "Ready for review").
- CI bot (corre en cada push como gate adicional).

### Checks (en orden)

1. **Spec compliance:** cada AC tiene ≥1 test que lo cubre.
2. **TDD trace:** cada `feat:` tiene un `chore: (failing)` previo para el mismo behavior.
3. **Quality gates:** pytest verde, coverage ≥ 80%, ruff clean, mypy strict, Snyk + Sonar verdes.
4. **Threat model:** cada mitigación STRIDE citada existe en código o test.
5. **Evals (si aplica):** comparar contra `evals/results/baseline.json`. No subir baseline acá; eso va en un PR dedicado.

### Entregables

| Si READY | Si BLOCKED |
|---|---|
| Comentario en PR (`PR_REVIEW_REPORT.md`) | Comentario en PR con la lista exacta de qué falló |
| Comentario en Jira (`JIRA_MERGE_COMMENT.md`) | Sin cambios en Jira |
| Transition Jira `In Review` → `Ready to merge` | Ticket queda en `In Review` |
| PR pasa de draft a "Ready for review" | PR queda en draft |

---

## 8. Cómo se persisten los artefactos (resumen)

| Producto del skill | Vive en |
|---|---|
| Brainstorm log | Comment en Jira + copia en `brainstorms/<slug>.md` (repo de specs) |
| Spec técnica | `specs/NNN-<slug>.md` en **repo del producto** |
| Threat model | `docs/security/<slug>-threat-model.md` en **repo del producto** |
| Context updates de dominio | `context/classifier-v2/` o `stacks/` en **repo de specs** (PR separado) |
| `todo.md` (plan) | Root del **repo del producto** |
| Tests + código | `tests/` + `src/` del **repo del producto** |
| Review report | Comentario en el PR del producto |
| Trazabilidad / lessons learned | `docs/pilots/KR-XXXX-overview.md` en **repo de specs** |

**Regla:** outputs técnicos (spec, código, tests) viven con el código. Outputs de framework (brainstorms log, pilots, context) viven en el repo de specs.

---

## 9. Estado del framework hoy

### Lo que ya funciona

- 5 skills definidas con procedimientos y exit criteria.
- Roles y responsabilidades separadas (Product Manager, Architect, Tech Lead, Developer, Reviewer).
- Templates de output: SPEC, ADR, PR description, PR review report, comentarios Jira (brainstorm, plan, merge), Confluence initiative, Jira story / epic.
- Stack Python Lambda con reglas duras (`stacks/python-lambda/rules.md`).
- Convención de commits TDD + commitlint + hooks Claude Code (block-main, block-secrets, enforce-tdd-trace, sandbox).
- Setup de Claude Web Project funcional con GitHub MCP de lectura.
- Persistencia parcial vía Atlassian MCP (Jira + Confluence).
- Piloto KR-16612 ejecutado end-to-end Skills 01-02.

### Lo que falta — críticas

| # | Pieza faltante | Por qué importa |
|---|---|---|
| 1 | **GitHub MCP con escritura** en Claude Web | Skill 02 hoy entrega artifacts; usuario hace branch+commit+PR a mano. Suma fricción y permite errores de paste. |
| 2 | **Harness completo para Skills 04 y 05** en cada repo del producto | Sandbox, hooks, settings.json, bootstrap.sh, post-edit-python.sh — la versión Rust ya existe; falta traducir a Python. |
| 3 | **Cliente para modelos baratos** (OpenCode / Crush) integrado al flujo | Skill 04 corre Qwen/DeepSeek. Si se hace con Claude Code → costo no se reduce. |
| 4 | **Sub-agent-driven-development** activado en Skill 04 | Tareas paralelizables del `todo.md` corren simultáneas. Reduce wall-clock time. |
| 5 | **Integración con SonarCloud / Snyk APIs** para Skill 05 | Hoy Skill 05 lee los reportes de CI manualmente. Con API directo: corre antes del PR. |
| 6 | **Routing automático de modelos** según skill | Cada skill declara modelo recomendado; falta orquestación que lo enforce sin intervención manual. |
| 7 | **Evals reales del framework** | Cuánto cuesta cada skill, % de outputs aceptados sin cambios, tiempo total. Hoy se mide manual. |
| 8 | **Multi-stack** | Hoy solo `python-lambda`. Faltan `python-emr-pyspark` (para PySpark jobs), `node-typescript`, `react`. |
| 9 | **Versionado de skills** | Cuando cambia una skill, los outputs viejos referencian una versión que ya no existe. Falta semver. |

---

## 10. Costos esperados por skill

Estimaciones de orden de magnitud por **una feature típica de Lambda** (ej. KR-16612). Tokens son aproximados; varían con la profundidad del ticket. Precios reales de modelos al 2026-05-13.

| Skill | Modelo | Tokens in (típicos) | Tokens out (típicos) | $ in (por MTok) | $ out (por MTok) | **Costo por skill** |
|---|---|---|---|---|---|---|
| 01 Brainstorm | Opus 4.7 | 50k | 20k | $15 | $75 | **~$2.25** |
| 02 Spec + Threat | Opus 4.7 | 80k | 40k | $15 | $75 | **~$4.20** |
| 03 Plan | Sonnet 4.6 | 30k | 10k | $3 | $15 | **~$0.24** |
| 04 TDD (con OSS) | Qwen 32B Coder | 300k | 100k | $0.20 | $1.00 | **~$0.16** |
| 04 TDD (con Claude) | Opus 4.7 | 300k | 100k | $15 | $75 | ~$12.00 |
| 05 Review | Sonnet 4.6 | 50k | 10k | $3 | $15 | **~$0.30** |

### Total por feature, dos escenarios

| Escenario | Costo IA total | Notas |
|---|---|---|
| **Routing óptimo** (Opus 01-02, Sonnet 03+05, OSS 04) | **~$7.15** | Recomendado. Skill 04 a modelo barato es donde se ahorra. |
| **Sin routing** (todo Opus 4.7) | ~$30+ | Lo que pasa hoy si no cambiamos cliente para Skill 04. |
| **Ahorro** | **~75%** | Justificación de invertir en habilitar OpenCode/Crush. |

### Costo IA vs costo humano

Una feature mediana toma **~1.5 días-dev** humano puro. A tarifa interna de Kriptos (estimar internamente):

- Costo dev: 1.5 días × hora-dev = **alto**.
- Costo IA con framework: **~$7 USD**.
- Costo dev con framework: ~0.3 días × hora-dev = **bajo**.

> **Punto clave:** la IA no compite contra el código gratis. Compite contra horas de dev. Hasta $50–100 de tokens por feature es trivial si baja 1 día-dev a 2 horas.

---

## 11. Métricas a medir — KPIs del framework

Cómo sabemos si el framework está funcionando. Cada KPI incluye **cómo se mide concretamente** (fuente de datos + frecuencia).

| # | KPI | Definición | Cómo se mide | Frecuencia | Objetivo |
|---|-----|------------|--------------|------------|----------|
| 1 | **Tiempo wall-clock por feature** | Desde "abro Skill 01" hasta "merge a `main`". Excluye tiempo bloqueado esperando humanos. | Timestamp del primer mensaje en Claude Web (Atlassian comment al ticket) + timestamp del merge en GitHub. `time-active = time-total - time-en-Q-deferida - time-en-review-humano`. | Por feature | < 2 días para Lambda chica |
| 2 | **Costo en tokens por feature** | Suma de tokens input + output de todas las skills del ticket. | Anthropic Console API: filtrar por conversation/project. OpenCode/Crush: provider logs. Reportar agregado por `KR-XXXXX`. | Por feature | < $15 USD con routing |
| 3 | **AC capturados Skill 01 vs ticket original** | Cuántos AC nuevos / refinados sale del brainstorm respecto al ticket pre-refinamiento. | Conteo manual: AC en descripción Jira **antes** vs `brainstorms/KR-XXXX-*.md` **después**. Reportar `delta = (AC_post − AC_pre) / AC_pre`. | Por feature | +30% al menos |
| 4 | **% bugs cazados antes del merge** | Issues que Skill 05 marca BLOCKED o que el reviewer humano captura, dividido por bugs reales detectados post-merge. | Conteo: `(blocked_reports + comments_humanos_que_piden_cambio) / (bugs_pre_merge + bugs_post_merge_30d)`. SonarCloud + GitHub PR comments + bugs reabiertos en Jira. | Mensual | > 90% (≤ 10% leakage a producción) |
| 5 | **% outputs aceptados sin cambios** | Por skill: cuántas ejecuciones se commitean sin que el humano edite el output. | Diff entre artifact entregado y archivo commiteado. Si `diff == 0` → aceptado limpio. Por skill, % mensual. | Mensual, por skill | > 70% por skill |
| 6 | **Reproducibilidad sin owner** | Otro dev ejecuta el flujo end-to-end sin asistencia del propietario del framework (Haroldo). | Test manual con dev nuevo cada N semanas. Contar: (a) preguntas que tuvo que hacer fuera del framework, (b) pasos donde se atascó, (c) % flujo completado sin ayuda. | Trimestral | 100% del flujo sin ayuda externa |
| 7 | **Coverage promedio por PR** | Coverage de tests del PR final. | SonarCloud API: `measures/coverage` por proyecto. Tomar coverage del commit del merge. Promedio mensual. | Mensual | ≥ 85% (gate mínimo es 80) |
| 8 | **Open questions deferidas que bloquean merge** | Cuántas Qs identificadas en Skill 01-02 quedan abiertas y bloquean releases. | Listar todas las `Q1, Q2, …` en specs activas. Para cada una: tiempo desde que se identificó hasta que se cerró. Buscar "🔴 Bloqueante" en specs. | Semanal | Cierre promedio < 5 días |
| 9 | **Costo IA vs costo dev** | Ratio entre dólares en tokens y dólares de tiempo-dev por feature. | Costo IA (Anthropic Console + OSS provider) ÷ costo dev (horas × tarifa). | Por feature | IA < 5% del costo dev |
| 10 | **Tasa de BLOCKED en Skill 04** | % de tareas del `todo.md` que Skill 04 reporta como BLOCKED (no completables tras 3 intentos). | Contar `[ ] BLOCKED:` vs `[x]` en `todo.md` cerrados. Promedio mensual. | Mensual | < 15% (más alto → spec/plan fueron débiles) |

### Cómo recolectar las métricas (mínimo viable)

**Hoy, sin tooling extra** — manual pero funciona para los primeros pilotos:

1. **Spreadsheet por feature** con: ticket, fecha inicio, fecha fin, tokens por skill, AC pre/post, BLOCKED count, observaciones. Una fila por ticket.
2. **Anthropic Console** para tokens de Skills 01-03 y 05.
3. **OpenCode / Crush logs** para tokens de Skill 04.
4. **SonarCloud + GitHub APIs** para coverage y bugs post-merge.
5. **Jira filter** "skill-framework" para listar features pasadas por el flujo.

**A mediano plazo** — automatizar con un script `metrics-collector.py` que pegue Anthropic + Jira + GitHub + SonarCloud APIs y emita un JSON por feature.

**A largo plazo** — dashboard (Grafana / Metabase) sobre el JSON acumulado, con vistas por mes/equipo/tipo de feature.

### Definition of Success del framework (a 6 meses)

El framework se considera adoptado y maduro cuando, **simultáneamente**:

- KPI 1 (tiempo wall-clock) < 2 días para Lambda chica en > 80% de features.
- KPI 4 (bugs cazados antes del merge) > 90%.
- KPI 6 (reproducibilidad sin owner) = 100%.
- KPI 9 (costo IA < 5% del costo dev) sostenido por 3 meses.

Si alguno falla persistentemente: pausar adopción del framework y arreglarlo antes de seguir escalando.

---

## 12. Roadmap — cómo llegar a autonomía completa

### Fase A — Eliminar fricciones manuales (siguiente sprint)

1. **GitHub MCP de escritura conectado al Claude Web Project.**
   - Skill 02 puede crear branch, commitear archivos, abrir PR sin intervención.
   - Skill 01 (Caso A) puede crear repo nuevo de iniciativa si aplica.
   - Reduce ~10 min de fricción por ticket.

2. **Atlassian MCP de escritura plenamente operativo.**
   - Comentarios automáticos en Jira con confirmación.
   - Transitions automáticas (Backlog → Ready for Spec → Spec ready → In Review → Ready to merge → Done).
   - Hoy parcial; falta automatizar al 100%.

### Fase B — Harness completo para Skills 04 y 05 (1-2 sprints)

1. **Template `kriptos-python-template`** (análogo al `kriptos-rust-template` existente).
   - `.claude/settings.json` con sandbox + permisos pre-aprobados.
   - `.claude/hooks/` adaptados a Python: `post-edit-python.sh`, `block-secrets.sh`, `enforce-tdd-trace.sh`, `session-start-bootstrap-check.sh`.
   - `scripts/bootstrap.sh` con detección de superpowers + fallback.
   - `pyproject.toml` con ruff, mypy, pytest, moto, powertools preconfigurados.
   - `.github/workflows/` con `ci.yml` + `ci-prod.yml`.

2. **Resultado:** un dev clona el repo del producto, abre Claude Code, y arranca Skill 04 sin más setup. El harness garantiza que no se rompan reglas (no push a main, no edit a tests para pasar, no skipear el RED, etc.).

### Fase C — Modelos baratos para Skill 04 (paralelo a B)

1. **Decidir cliente:** OpenCode (vibe-coding) o Crush. Probar ambos con Ticket 5 (`gse-cycle-init`) como referencia.
2. **Probar Qwen 2.5 Coder 32B y DeepSeek Coder V2** en el loop TDD del piloto.
3. **Medir:** wall-clock time, % tareas en GREEN sin BLOCKED, costo total vs Claude Sonnet.
4. **Documentar en `stacks/python-lambda/`** qué modelo + cliente usar para Skill 04 según volumen de loop.

### Fase D — Autonomía orquestada (3+ sprints)

1. **Routing automático de modelos** por skill: el framework selecciona Opus/Sonnet/Qwen según la skill invocada, sin que el dev elija manualmente.
2. **Sub-agent-driven-development** en Skill 04: el agente identifica tareas paralelizables del `todo.md` y las dispara a sub-agentes simultáneos.
3. **Skill 05 auto-resuelve fallos menores** (no spec compliance): si ruff falla, intenta `ruff --fix`; si mypy falla en algo trivial, intenta resolverlo; si falla algo serio, sigue siendo BLOCKED.
4. **Memory layer persistente** entre sesiones: el framework recuerda decisiones técnicas del repo, no se las pregunta al dev cada vez.

### Fase E — Métricas y mejora continua

1. **Dashboard del framework:** tiempo por skill, % outputs aceptados sin cambios, costo por ticket, coverage promedio, tickets bloqueados por Q&A diferidas.
2. **Eval suite** para comparar versiones de skills (¿la nueva versión de Skill 01 produce mejores AC que la anterior?).
3. **Lessons learned automáticas:** cada piloto (`docs/pilots/`) alimenta una sección de "antipatrones detectados" en el repo de specs.

---

## 13. Visión a 6 meses

```
Día 1 del dev:
  - Abre Jira → invoca /brainstorm (Claude Web)
  - 20 min después: ticket refinado, spec lista, PR de spec abierto automáticamente
  - 5 min después: /plan en Claude Code → todo.md generado
  - El dev pone "go" → Skill 04 corre desatendida (modelo barato + sub-agents)
  - Al volver del café: PR listo, Skill 05 ya corrió, READY o BLOCKED claro
  - Dev hace review humano sobre lo que la máquina no puede juzgar
```

**Métrica de éxito:** tiempo de wall-clock desde *ticket en backlog* hasta *PR listo para merge humano* < 1 día para un Lambda chico, < 3 días para uno mediano.

---

## 12. Costos esperados por skill

Cuánto cuesta correr una feature end-to-end con el framework, en órdenes de magnitud.

### Tabla de referencia (por feature tamaño Lambda chico)

| Skill | Modelo | Tokens in | Tokens out | Precio in (USD/M) | Precio out (USD/M) | Costo orden de magnitud |
|---|---|---|---|---|---|---|
| 01 Brainstorm | Opus 4.7 | 30–80 k | 10–30 k | $15 | $75 | $0.50 – $1.50 |
| 02 Spec + Threat | Opus 4.7 | 50–100 k | 30–50 k | $15 | $75 | $1.00 – $3.00 |
| 03 Plan | Sonnet 4.6 | 20–50 k | 5–15 k | $3 | $15 | $0.10 – $0.40 |
| 04 TDD (Claude) | Sonnet 4.6 | 100–500 k | 50–200 k | $3 | $15 | $1.50 – $4.50 |
| 04 TDD (OSS) | Qwen / DeepSeek vía OpenRouter | 100–500 k | 50–200 k | ~$0.10 | ~$0.30 | $0.05 – $0.20 |
| 05 Review | Sonnet 4.6 | 30–80 k | 5–15 k | $3 | $15 | $0.15 – $0.45 |

> Precios USD/millón de tokens al cierre de mayo 2026. Verificar en https://www.anthropic.com/pricing y https://openrouter.ai/models antes de cada quarter.

### Costo total esperado por feature

| Configuración | Costo total |
|---|---|
| Todo Claude (Skill 04 con Sonnet) | **$3.25 – $9.85** por feature |
| Routing (Skill 04 con OSS) | **$1.80 – $5.55** por feature |
| Ahorro de routing | **~45 – 65 %** |

### Cómo se mide realmente

| Fuente | Cómo extraer | Frecuencia |
|---|---|---|
| Anthropic Console → Usage API | `GET /v1/organizations/{org_id}/usage_report` con filtro por workspace o por API key. Devuelve tokens in/out por modelo por día. | Diario, agregado semanal. |
| OpenRouter (si se usa para Skill 04) | Dashboard de billing per-key + endpoint `/api/v1/generation/{id}` para detalles por request. | Diario. |
| OpenCode / Crush (modelo local) | Configurar logging local que grabe `{skill, tokens_in, tokens_out, model, duration_ms}` por sesión en `~/.kriptos/usage.jsonl`. | Por sesión. |
| Jira custom fields | Agregar al ticket campos `[FW] Tokens In`, `[FW] Tokens Out`, `[FW] Costo USD`. El dev (o un script al cerrar el ticket) los llena con los totales. | Por ticket cerrado. |

### Instrumentación recomendada (un script semanal)

```bash
# scripts/weekly-cost-report.sh
# Junta usage de Anthropic + OpenRouter + logs locales para los tickets cerrados esta semana.

anthropic_usage --since 7d --workspace kriptos > /tmp/anthropic.json
openrouter_usage --since 7d --key kriptos > /tmp/openrouter.json
jq -s 'reduce .[] as $r ({}; .[$r.ticket] += $r.cost_usd)' /tmp/*.json > weekly-cost-per-ticket.json
```

Output va a un dashboard simple (Sheets o Metabase) — una columna por skill, una fila por feature.

---

## 13. Métricas del framework — cómo medir cada KPI

Cada KPI tiene que tener **fuente de datos + herramienta + frecuencia**. Si no la tiene, no se mide y no existe.

### 13.1 Métricas de velocidad

| KPI | Qué mide | Fuente | Cómo extraer | Objetivo |
|---|---|---|---|---|
| **Wall-clock por feature** | Tiempo desde Skill 01 hasta PR merge. | Jira API — historial de transitions. | `GET /rest/api/3/issue/{KR-XXXX}/changelog` → calcular delta entre `Backlog → Ready for Spec` y `Done`. | < 24 h para Lambda chico; < 72 h para mediano. |
| **Tiempo por skill** | Duración de cada paso. | Jira transitions + timestamps de commits en GitHub. | Para 01–02: delta entre transitions de Jira. Para 03–05: `git log --format='%cI' branch` head/tail. | Skill 01: < 40 min; Skill 02: < 20 min; Skill 03: < 10 min; Skill 04: < 4 h; Skill 05: < 15 min. |
| **Idle time entre skills** | Tiempo que el ticket queda esperando entre fases. | Diff entre fin de skill N y arranque de skill N+1 en Jira changelog. | Mismo endpoint. | < 30 % del wall-clock total. |
| **Tiempo de bootstrap por dev** | Cronómetro la primera vez que un dev usa el framework. | Manual la primera vez; después se promedia. | Encuesta + log de onboarding. | < 30 min para que un dev nuevo arranque Skill 01. |

### 13.2 Métricas de costo

| KPI | Qué mide | Fuente | Cómo extraer | Objetivo |
|---|---|---|---|---|
| **Costo total por feature** | USD por ticket cerrado. | Anthropic + OpenRouter Usage APIs, agregado por ticket. | Script `weekly-cost-report.sh` (§ 12). | < $6 por Lambda chico con routing; < $10 sin routing. |
| **Costo por skill** | USD desglosado por paso. | Misma fuente, agrupado por `skill_id` (vía API key separada por skill, o tag en metadata del request). | Cada skill debe usar una API key dedicada (o un header `x-skill: 01`). | Skill 04 < 50 % del costo total. |
| **Ratio Opus / Sonnet / OSS** | Distribución del gasto entre tiers de modelo. | Usage API agregado por modelo. | `jq` sobre el JSON de Anthropic + OpenRouter. | Ideal: ~30 % Opus / ~20 % Sonnet / ~50 % OSS. |

### 13.3 Métricas de calidad del output

| KPI | Qué mide | Fuente | Cómo extraer | Objetivo |
|---|---|---|---|---|
| **AC capturados por brainstorm vs ticket original** | Cuántos AC nuevos agrega Skill 01. | Diff entre la descripción inicial del ticket y el comentario de brainstorm. | Script Python que parsea el ticket Jira y cuenta items `^AC\d+` en cada versión. | +30 % al menos (4 → 5 o más en promedio). |
| **% AC con test asignado** | Cobertura de la spec con tests nombrados. | Parsear `specs/NNN-*.md` § 7 (test plan). | Contar items `[ ] test_*` y dividir por número de AC. | 100 %. Cualquier AC sin test es BLOCKED. |
| **Tests nombrados por spec** | Total de tests planeados antes de tocar código. | Mismo. | Conteo de items en § 7. | ≥ 5 tests por spec; típico 15–40. |
| **% outputs aceptados sin cambios** | Cuánto edita el humano el output del agente antes de commitear. | `git diff HEAD~1 HEAD` sobre el commit que mete el output. | Comparar bytes/líneas del artifact recibido vs el commit final. | > 80 % aceptado sin cambios estructurales. |
| **Bugs detectados antes del merge** | BLOCKED reportados por Skill 05 vs bugs encontrados después del merge. | Parsear comentarios del PR + post-mortems. | Contar Skill 05 BLOCKED y compararlos con issues abiertos en producción contra el mismo Lambda. | > 80 % de bugs capturados antes del merge. |
| **Coverage promedio por PR** | Cobertura de tests final. | SonarCloud API. | `GET /api/measures/component?component=<repo>&metricKeys=coverage` por PR. | ≥ 80 % siempre (gate); promedio del repo ≥ 85 %. |
| **Threat model: mitigaciones verificadas** | % de mitigaciones STRIDE con cita verificable. | Parsear `docs/security/*.md` + checar que la línea/test citada existe. | Script que grep cada cita y verifica que existe. | 100 %. |

### 13.4 Métricas de adopción del equipo

| KPI | Qué mide | Fuente | Cómo extraer | Objetivo |
|---|---|---|---|---|
| **% features que usan el framework** | Cuántos tickets pasaron por Skill 01 vs total cerrados. | Custom field Jira `[FW] Used framework: yes/no` + label `framework`. | JQL: `project = KR AND label = framework AND status = Done` / total Done. | Mes 1: 30 %, Mes 3: 70 %, Mes 6: 95 %. |
| **Devs que invocaron al menos 1 skill** | Adopción individual. | Logs de uso de Claude Web Project + commits con el prefijo del framework. | `git log --format='%ae' --grep='chore: spec for'` dedup. | Mes 3: 100 % del equipo backend. |
| **Reproducibilidad sin Haroldo** | Otro dev ejecuta el flujo solo. | Encuesta semanal después del Skill 05. Pregunta: "¿pediste ayuda a Haroldo en este ticket?" S/N. | Form anónimo en Slack. | < 20 % de tickets requieren ayuda externa. |
| **NPS interno del framework** | Satisfacción del equipo. | Encuesta mensual de 1 pregunta: "¿Recomendarías el framework a otro dev de Kriptos? (0-10)". | Slack poll. | NPS > 30 al cierre de Q3. |
| **Tasa de skill que termina en BLOCKED** | Robustez del framework. | Comentarios en Jira con tag `BLOCKED`. | JQL + parse de comentarios. | < 15 % de invocaciones terminan BLOCKED. |

### 13.5 Cómo arrancar las mediciones HOY (mínimo viable)

No hace falta dashboard. Una hoja de cálculo y un script bastan para arrancar.

1. **Crear custom fields en Jira:** `[FW] Used framework`, `[FW] Tokens In/Out`, `[FW] Costo USD`, `[FW] Skills BLOCKED`.
2. **Convención de labels:** todo ticket que pasa por Skill 01 lleva label `framework`. Si pasa por todas, agregar `framework-full`.
3. **Script semanal** (`scripts/weekly-metrics.sh`) que corre todos los lunes:
   - Junta tickets `framework` cerrados en la semana.
   - Extrae wall-clock, tokens, AC count, coverage final.
   - Genera tabla markdown que se publica en Confluence en una página "Framework — Weekly Metrics".
4. **Retrospectiva mensual** con esa tabla. Cada mes: ¿se cumplió cada objetivo? ¿qué falló?

### 13.6 Mediciones del piloto KR-16612 (snapshot inicial)

> Estos son los primeros datos reales. Sirven de baseline para los próximos pilotos.

| Métrica | Valor en KR-16612 | Objetivo |
|---|---|---|
| Tiempo Skill 01 | ~30 min | < 40 min ✅ |
| Tiempo Skill 02 | ~10 min | < 20 min ✅ |
| AC en ticket original | 5 | — |
| AC en spec final | 6 (+1 emergente) | +30 % ✅ |
| Sub-casos enumerados (AC04) | 19 | — |
| Tests nombrados en § 7 | 37 | ≥ 5 ✅ |
| Open questions formalizadas | 4 (1 bloqueante) | — |
| Amenazas STRIDE capturadas | 6 | ≥ 3 ✅ |
| Costo Skills 01-02 (estimado) | ~$2.50 | < $5 ✅ |
| Skills BLOCKED | 0 | < 15 % ✅ |

---

## Apéndice A — Glosario rápido

| Término | Qué es |
|---|---|
| **Skill** | Procedimiento documentado que un agente IA ejecuta. Una skill = un paso del pipeline. |
| **Rol** | Mindset y reglas operativas que el agente activa para una skill (Product Manager, Architect, etc.). |
| **Harness** | Conjunto de hooks + sandbox + permisos + bootstrap que limita y orquesta al agente IA dentro de un repo. |
| **Caso de persistencia** | A/B/C/D según de dónde vino la idea original (idea cruda, ticket sin contexto, ticket con épica, Confluence draft). Determina qué se actualiza en Jira/Confluence. |
| **Slice vertical** | Tarea atómica testable end-to-end dentro de su scope. Una slice = un ciclo TDD. |
| **TDD trace** | Secuencia de commits `chore: (failing)` → `feat: (passing)` → `refactor:` que enforza disciplina TDD vía commitlint. |
| **MCP** | Model Context Protocol — conector que da al agente acceso a sistemas externos (GitHub, Jira, Confluence, etc.). |

---

## Apéndice B — Estructura del repo de specs

```
classifier-specs/
├── CLAUDE.md                  contrato para Claude Code en este repo
├── CLAUDE_PROJECT.md          instrucciones para pegar en el Project de Claude Web
├── skills/                    las 5 skills del flujo
├── roles/                     5 roles (PM, Architect, Tech Lead, Developer, Reviewer)
├── .claude/commands/          comandos invocables desde Claude Code
├── templates/                 SPEC, ADR, PR descripcion, PR review report,
│                              JIRA epic/story/bug/comments, CONFLUENCE initiative
├── stacks/python-lambda/      reglas + settings.json + bootstrap.sh para Python Lambdas
├── context/classifier-v2/     contexto del producto (ecosystem, decisiones)
├── brainstorms/               outputs reales de Skill 01 (uno por ticket)
├── docs/
│   ├── references/            PDFs e imágenes (flujo, arquitectura)
│   ├── pilots/                resúmenes ejecutivos de pilotos del framework
│   └── framework-overview.md  este documento
└── kriptos-rust-template/     template para repos Rust (base estructural)
```

---

## Apéndice C — Referencias

- [Brainstorm real del piloto KR-16612](../brainstorms/KR-16612-tree-url-generator.md)
- [Resumen del piloto KR-16612](pilots/KR-16612-overview.md)
- [Flujo de 5 pasos (imagen)](references/flow-5-steps.png)
- [Guía de Desarrolladores — Repos con TDD + IA (PDF)](references/guia-desarrolladores-tdd-ia.pdf)
- [Arquitectura interna de Claude Code](references/claude-code-architecture.png)
