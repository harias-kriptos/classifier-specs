# Framework `classifier-specs` — Resumen ejecutivo

> Documento condensado para slides y comunicación al equipo.
> Cubre: distribución Web vs Code · ahorros · optimizaciones · qué hace cada actor.

---

## 1. TL;DR — Regla mental

```
┌─────────────────────────┬───────────────────────────────┐
│  Claude Web             │  Claude Code                  │
│  ─────────────────────  │  ─────────────────────────    │
│  Refinamiento           │  Ejecución                    │
│  Sin tocar código       │  Modifica archivos + git      │
│  Conversacional         │  CLI + sandbox + hooks        │
│  Skills 01 · 02         │  Skills 03 · 04 · 05          │
└─────────────────────────┴───────────────────────────────┘
```

**Heurística simple:**

- ¿Pensar? → Web.
- ¿Tocar código, ejecutar tests, abrir PRs? → Code.
- ¿En la frontera? (Skill 03 Plan) → Code recomendado, pero Web también vale.

---

## 2. Distribución por skill — vista compacta

| # | Skill | Cliente | Modelo | Actor humano | Actor IA | Output | Persistencia |
|---|-------|---------|--------|--------------|----------|--------|--------------|
| 01 | **Brainstorm** | Claude Web | Opus 4.7 | CEO / PM / Comercial / Tech Lead | Product Manager | Resumen estructurado | Jira ticket + `brainstorms/` |
| 02 | **Spec + Threat Model** | Claude Web | Opus 4.7 | Architect / Tech Lead | Architect | `specs/NNN-*.md` + `docs/security/*.md` | Repo del producto |
| 03 | **Plan** | Claude Code | Sonnet 4.6 | Tech Lead / Developer | Tech Lead | `todo.md` con slices TDD | Repo del producto |
| 04 | **TDD Implementation** | Claude Code | Modelo barato (Qwen / DeepSeek) | Developer | Developer | Branch + commits + PR draft | Repo del producto + Jira transition |
| 05 | **Review + evals** | Claude Code / CI | Sonnet 4.6 | Developer / CI bot | Reviewer | Review report READY/BLOCKED | Comment PR + Jira |

---

## 3. Skill 01 — Brainstorm (Claude Web)

### Qué hace

Refina una idea cruda o un ticket pobre hasta que sea escribible como spec. **El agente desafía; el usuario decide.**

### Actor humano

Cualquiera del equipo — no requiere vocabulario técnico.

### Actor IA

**Product Manager.** Hace preguntas en 6 dimensiones (scope, AC testables, edge cases, integración, threat surface, observabilidad). Máximo 3 preguntas por turno.

### Output

- Comentario estructurado en el ticket de Jira.
- Descripción del ticket actualizada (si aplica).
- Copia en `brainstorms/<slug>.md` para trazabilidad.

### Ahorro vs flujo tradicional

| Flujo tradicional | Con Skill 01 |
|---|---|
| Reunión de 1 hora con PM + Tech Lead + Dev | Conversación de 20–40 min, dev solo + agente |
| AC descubiertos en code review tarde | AC y edge cases capturados antes del código |
| Threat model "después" o nunca | Threat surface preliminar mapeada |
| Ticket avanza vago | Ticket con 4 ítems de exit checklist verdaderos |

**Ahorro estimado:** 30–45 min de reunión × 2–3 personas → ~1.5 h-persona por feature.

---

## 4. Skill 02 — Spec + Threat Model (Claude Web)

### Qué hace

Convierte el brainstorm en una spec formal (11 secciones obligatorias) + threat model STRIDE. **Cada AC mapea a al menos un test nombrado.**

### Actor humano

Architect, Tech Lead o Senior Developer.

### Actor IA

**Architect.** Lee inputs, detecta gaps de contexto, propone crearlos antes de escribir. Salida densa, contractual.

### Output (artifacts editables en el chat)

| Artifact | Repo destino |
|---|---|
| `specs/NNN-<slug>.md` | producto |
| `docs/security/<slug>-threat-model.md` | producto (si hay threat surface) |
| `context/classifier-v2/<archivo>.md` | classifier-specs (si hubo gaps de dominio) |

### Ahorro vs flujo tradicional

| Flujo tradicional | Con Skill 02 |
|---|---|
| Spec escrita por arquitecto en 2–4 h | Spec generada en 10–20 min con review humano |
| Test plan inventado durante code review | 1+ test nombrado por AC antes de tocar código |
| Threat model como ejercicio aparte (a veces ni se hace) | Threat model en el mismo artifact, mitigaciones citadas a línea de código o test |

**Ahorro estimado:** 1.5–3 h-persona por feature.

---

## 5. Skill 03 — Plan (Claude Code)

### Qué hace

Descompone la spec aprobada en `todo.md` con slices verticales TDD-ready. **Una tarea = RED + GREEN + REFACTOR = tres commits.**

### Por qué Claude Code (no Web)

- `todo.md` vive en el repo del producto — Claude Code lo escribe directo al disco.
- Lee la spec del filesystem local (sin copy-paste).
- Te deja listo para arrancar Skill 04 en la misma terminal.

### Actor humano

Tech Lead o Developer auto-descomponiendo.

### Actor IA

**Tech Lead.** Identifica slices verticales testables independientemente. Si una tarea pasa de 30 min, la parte.

### Output

- `todo.md` en la raíz del repo del producto.
- Comentario en Jira con resumen del plan.

### Ahorro vs flujo tradicional

| Flujo tradicional | Con Skill 03 |
|---|---|
| Dev empieza a codear sin plan | Plan atómico antes del primer test |
| "Voy a hacer todo junto" → PR gigante imposible de revisar | Slices verticales testables independientes |
| Refactors mezclados con features en el mismo commit | RED / GREEN / REFACTOR separados |

**Ahorro estimado:** 30 min de planificación + ~2 h de review humano más fluido por PR.

---

## 6. Skill 04 — TDD Implementation (Claude Code)

### Qué hace

Ejecuta `todo.md` tarea por tarea en ciclos TDD estrictos enforced por commits y commitlint:

```
chore: <behavior> (failing)  →  feat: <behavior> (passing)  →  refactor: <what>
```

Si 3 intentos fallan → **BLOCKED**. No improvisar. No editar tests para hacerlos pasar.

### Por qué Claude Code obligatorio

Necesita:
- **Sandbox** (red restringida, lecturas a `~/.ssh`, `~/.aws`, `.env` denegadas).
- **Hooks** (`block-main-branch`, `block-secrets`, `block-dangerous-commands`, `enforce-tdd-trace`, `post-edit-python`).
- Acceso a `git`, `pytest`, `ruff`, `mypy`.

### Actor humano

Developer (supervisa, no tipea código línea por línea).

### Actor IA

**Developer.** Mecánico, disciplinado. Una cosa a la vez. Respeta limits of autonomy.

### Output

- Branch `KR-XXXX-<slug>` con secuencia TDD limpia.
- Tests verdes, coverage ≥ 80%, ruff + mypy clean.
- PR draft con `templates/PR_DESCRIPTION.md`.
- Transition Jira a `In Review`.

### Optimización clave: routing a modelo barato

| Modelo | Costo input | Costo output | Costo por feature |
|---|---|---|---|
| Sonnet 4.6 (Claude) | $3 / M tokens | $15 / M | $1.50 – $4.50 |
| Qwen 2.5 Coder / DeepSeek V3 (vía OpenRouter) | ~$0.10 / M | ~$0.30 / M | **$0.05 – $0.20** |

**Ahorro:** ~95% en el paso que más tokens consume del pipeline.

### Ahorro vs flujo tradicional

| Flujo tradicional | Con Skill 04 |
|---|---|
| Dev escribe tests "cuando haya tiempo" | Tests antes del código siempre, enforced por commits |
| Bugs en review tarde por "olvidé el edge case" | Edge cases del spec ya tienen tests planeados |
| Wall-clock: 1–2 días para una Lambda chica | Wall-clock: 2–4 h supervisadas |

**Ahorro estimado:** 50–70% del tiempo wall-clock por feature.

---

## 7. Skill 05 — Review + evals (Claude Code / CI)

### Qué hace

Valida que la implementación matchea la spec **antes** del review humano. **Pre-flight check binario:** READY o BLOCKED.

### Por qué Claude Code o CI (no Web)

Necesita correr `pytest`, leer reportes de SonarCloud / Snyk, comparar git history. Eso no se hace en Web.

### Actor humano

Developer (corre antes de marcar el PR como "Ready for review"). Opcional: CI bot en cada push.

### Actor IA

**Reviewer.** Reporta problemas, no los fixea. Si algo está roto → vuelve a Skill 04.

### Checks (en orden)

1. Spec compliance — cada AC tiene ≥1 test.
2. TDD trace — cada `feat:` tiene un `chore: (failing)` previo.
3. Quality gates — pytest verde, coverage ≥ 80%, ruff + mypy + Snyk + Sonar verdes.
4. Threat model — cada mitigación STRIDE cita una línea de código o test que existe.
5. Evals — si aplica, comparar contra `evals/results/baseline.json`.

### Output

| Si READY | Si BLOCKED |
|---|---|
| Comment en PR + Jira | Comment en PR con qué falló y cómo arreglarlo |
| Transition Jira a `Ready to merge` | Sin cambios en Jira |
| PR pasa de draft a "Ready for review" | PR queda en draft |

### Ahorro vs flujo tradicional

| Flujo tradicional | Con Skill 05 |
|---|---|
| Reviewer humano descubre coverage bajo / tests faltantes / lint roto | Skill 05 los reporta antes de pedir review humano |
| 2–3 round-trips de review hasta que pasa el quality gate | 1 review humano sobre código ya verde |
| Threat model olvidado o no verificado | Cada mitigación STRIDE chequeada automáticamente |

**Ahorro estimado:** 1–2 h de review humano por PR.

---

## 8. Ahorros de tiempo — agregado por feature

Sumando los ahorros estimados de cada skill para un feature **tipo Lambda chica**:

| Concepto | Flujo tradicional | Con framework | Ahorro |
|---|---|---|---|
| Reunión de refinamiento | 1.5 h-persona | 0.5 h-persona | **1 h** |
| Escritura de spec + threat model | 2.5 h-arquitecto | 0.5 h-arquitecto | **2 h** |
| Planificación e implementación | 12 h-dev | 4 h-dev | **8 h** |
| Review humano (ciclos) | 3 h | 1 h | **2 h** |
| **Total por feature** | **19 h-persona** | **6 h-persona** | **13 h-persona (~68%)** |

### Proyección a 6 meses

| Hipótesis | Cálculo | Resultado |
|---|---|---|
| 4 features por dev por mes × 5 devs × 6 meses | 120 features | — |
| Ahorro por feature: 13 h-persona | 120 × 13 h | **1 560 h-persona ahorradas** |
| Equivalente en FTE (160 h/mes) | 1 560 / 960 | **~1.6 FTE liberadas en 6 meses** |

---

## 9. Optimizaciones técnicas aplicadas

### 9.1 Routing de modelos por skill

| Skill | Modelo | Razón |
|---|---|---|
| 01–02 | Opus 4.7 | Decisiones de scope y contrato — profundidad pesa más que velocidad. |
| 03 | Sonnet 4.6 | Descomposición estructural — no necesita Opus. |
| 04 | Qwen / DeepSeek (OSS) | Loop intensivo en tokens — modelo barato baja costo 95%. |
| 05 | Sonnet 4.6 | Reasoning, no creatividad. |

### 9.2 Prompt caching

- Skills 02–05 cargan los mismos archivos base (roles, templates, contexto, reglas) en cada invocación.
- Anthropic prompt caching: 5–10 min TTL. Si las invocaciones son seguidas, el costo cae al 10% del normal.
- **Recomendación operativa:** ejecutar Skills 03–05 en la misma sesión de Claude Code para maximizar caché.

### 9.3 Context budget < 20%

- Las skills cargan archivos **on-demand**, no upfront.
- Cada skill declara explícitamente qué leer y en qué orden.
- Si una skill se siente lenta o vaga → context window > 50% probable.

### 9.4 Paralelización con sub-agentes (futuro)

- Skill 04 puede dispatchar tareas independientes del `todo.md` a sub-agentes paralelos (`subagent-driven-development`).
- Cada sub-agente corre en su propio worktree → cero conflictos de archivos.
- Reduce wall-clock 30–50% en features con slices independientes.

### 9.5 Guardrails sin permission prompts

- Hooks en `pre-tool-use` bloquean automáticamente: edit en `main`, secrets, comandos peligrosos.
- Sandbox bloquea lecturas a paths sensibles.
- `--no-verify`, `--force`, `--force-with-lease` denegados.
- Resultado: dev autoriza menos prompts → flow no se rompe.

---

## 10. Mejoras sustanciales — cambio cultural

Más allá del tiempo, el framework cambia **cómo se trabaja**:

### 10.1 Spec antes que código — siempre

- No hay `feat:` sin `chore: spec for X` previo en el branch.
- Spec aprobada es contrato; downstream lo lee, no lo reinterpreta.

### 10.2 TDD enforced por convención, no por buena voluntad

- Commits `chore: (failing)` antes de `feat: (passing)` verificados por commitlint.
- Hook `enforce-tdd-trace` alerta al final de cada turno si rompiste el orden.

### 10.3 Threat model deja de ser opcional

- Si la spec identifica un threat surface, el threat model es parte del mismo PR.
- Mitigaciones citadas a líneas de código o tests — auditable.

### 10.4 Roles separados, no superpuestos

- Product Manager hace preguntas, Architect escribe contrato, Tech Lead descompone, Developer implementa, Reviewer audita.
- Cada uno tiene su skill, su rol IA, su mindset operativo.
- Resultado: outputs claros, no mezcla de "diseño + código + review" en un solo mensaje.

### 10.5 Persistencia múltiple, sin silos

- Brainstorm: Jira + `brainstorms/`.
- Spec: repo del producto + Jira link.
- Plan: repo del producto + Jira comment.
- Review: PR comment + Jira transition.
- **Cualquier persona puede reconstruir la historia leyendo Jira.**

### 10.6 Cost-aware desde el diseño

- El framework declara explícitamente qué modelo usar y por qué.
- Skill 04 con OSS = ahorro estructural, no truco.
- Si Opus se usa donde no hace falta, está mal configurado.

### 10.7 Auditable y reproducible

- Cada decisión queda en un commit, un comentario o un artifact.
- Outputs versionables — si la versión 2 de Skill 01 produce mejor output, se documenta.
- Pilotos (`docs/pilots/`) sirven de "evidencia de funcionamiento".

---

## 11. Comparativa rápida — antes vs ahora

| Dimensión | Antes | Con el framework |
|---|---|---|
| Tiempo refinamiento | Reunión 1 h × 3 personas | 30 min, dev solo |
| Tiempo spec | 2–4 h arquitecto | 10–20 min |
| Tests escritos | "Cuando haya tiempo" | Antes del código, siempre |
| Threat model | Opcional / nunca | Obligatorio si hay surface |
| Code review | Encuentra coverage bajo, lint roto | Llega ya con todo verde |
| Costo por feature | $0 directo (todo h-persona) | $1.80–$5.55 USD + 6 h-persona |
| Decisiones técnicas documentadas | En cabezas | En spec, ADR, threat model |
| Onboarding nuevo dev | Días | Horas (lee skills + templates + roles) |

---

## 12. Qué falta — agenda inmediata

1. **GitHub MCP con escritura en Claude Web** → Skill 02 commitea y abre PR sin intervención.
2. **Template `kriptos-python-template`** completo (hooks + settings + bootstrap + workflows).
3. **Cliente para modelos OSS** (OpenCode o Crush) integrado al loop de Skill 04.
4. **Sub-agent-driven-development** activado para paralelizar slices independientes.
5. **Dashboard de métricas** (puede ser una hoja de cálculo al principio).

---

## Referencias

- Detalle completo de cada skill: `framework-overview.md`
- Brainstorm real del piloto: `brainstorms/KR-16612-tree-url-generator.md`
- Lecciones del piloto KR-16612: `pilots/KR-16612-overview.md`
- Flujo visual de los 5 pasos: `references/flow-5-steps.png`
- Guía para desarrolladores TDD + IA: `references/guia-desarrolladores-tdd-ia.pdf`
