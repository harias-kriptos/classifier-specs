# Deck — `classifier-specs` para el equipo de Kriptos

> 10 slides. ~25-30 minutos de presentación.
> El corazón del deck son las slides 4 y 5: cómo se arma el plan y qué gates lo aseguran.
> Cada slide tiene **Contenido** (lo que va en la slide) y **Decir** (lo que decís de viva voz).

---

## Slide 1 — Qué es esto y para qué sirve

### Contenido

```
classifier-specs
Cómo todos vamos a entregar features del Classifier
con la ayuda de agentes IA

Haroldo Arias · Mayo 2026
```

**Lo central:**

- Un repo (`classifier-specs`) que **todos vamos a usar** para refinar, especificar e implementar tickets del Classifier.
- **5 skills** que un agente IA ejecuta — cada una es un paso del flujo.
- **2 herramientas:** Claude Web (para pensar) + Claude Code (para ejecutar).
- **Disciplina:** spec antes que código · TDD enforced · threat model obligatorio · coverage 80%.

### Decir

*"Hoy les muestro un repo que ya está vivo y que va a ser parte del día a día de cada dev del clasificador. La idea no es agregarles trabajo — es cambiar la forma en que arrancamos cada ticket para que el agente IA haga el grueso del trabajo repetitivo, manteniendo calidad y disciplina enforced por gates duros."*

---

## Slide 2 — Estructura del repo y por qué cada carpeta existe

### Contenido

El repo mezcla **4 funciones distintas**, cada una en su carpeta:

```
1. MAQUINARIA del framework    → skills/, roles/, templates/, stacks/, .claude/
2. CONOCIMIENTO del producto   → context/classifier-v2/
3. EVIDENCIA de uso            → brainstorms/, docs/pilots/
4. DOCUMENTACIÓN para humanos  → docs/, README.md, CLAUDE*.md
```

| Carpeta | Para qué |
|---|---|
| `skills/` | Define **qué hace cada paso** (5 skills: Brainstorm → Review). |
| `roles/` | Define **cómo se comporta el agente** según el paso (PM, Architect, Tech Lead, Dev, Reviewer). |
| `templates/` | Plantillas de outputs estándar (SPEC, threat model, PR description, Jira comments). |
| `stacks/python-lambda/` | Reglas duras (MUST/NEVER) del stack. Futuros: `stacks/rust-emr/`, `stacks/typescript-react/`. |
| `context/classifier-v2/` | **30+ archivos** del Classifier indexados (ecosystem, decisions, components por fase). El agente lee on-demand. |
| `brainstorms/` | Output de Skill 01 por ticket (trazabilidad: "¿cómo decidimos AC06 de KR-16612?"). |
| `docs/pilots/` | Resumen ejecutivo por iniciativa piloto (lessons learned). |
| `docs/` | Documentación humana del framework (overview, summary, maintenance, deck). |

### Decir

*"Esta separación es deliberada. La **maquinaria** (skills/roles/templates) define cómo trabaja el agente; el **conocimiento** le dice sobre qué trabaja; la **evidencia** muestra qué se hizo; la **documentación** es para nosotros. Si las mezclamos, el framework se vuelve específico del Classifier y no se puede reusar."*

---

## Slide 3 — Los 5 skills y el flujo end-to-end

### Contenido

| # | Skill | Cliente | Modelo | Quién la invoca | Output |
|---|-------|---------|--------|-----------------|--------|
| 01 | Brainstorm | Claude Web | Opus 4.7 | Cualquiera (CEO/PM/comercial/dev) | Comentario refinado en Jira |
| 02 | Spec + Threat Model | Claude Web | Opus 4.7 | Architect / Tech Lead | `specs/NNN-*.md` + threat model |
| 03 | Plan | Claude Code | Sonnet 4.6 | Tech Lead / Developer | `todo.md` con slices TDD |
| 04 | TDD Implementation | Claude Code | Modelo barato (OSS) | Developer | Branch + commits TDD + PR draft |
| 05 | Review + evals | Claude Code / CI | Sonnet 4.6 | Developer / CI | READY / BLOCKED |

**Flujo end-to-end de un ticket:**

```
Jira KR-XXXXX
   │  (1) Brainstorm   Web · Opus · 30 min   → resumen en Jira + brainstorms/
   ▼
Refinamiento listo
   │  (2) Spec+Threat  Web · Opus · 15 min   → spec + threat-model en repo del producto
   ▼
Contrato listo
   │  (3) Plan         Code · Sonnet · 5 min → todo.md con slices TDD
   ▼
Plan listo
   │  (4) TDD          Code · OSS · 2-4 h    → branch + commits + PR draft
   ▼
Implementación lista
   │  (5) Review       Code/CI · Sonnet · 10 min → READY / BLOCKED
   ▼
Human review + merge a main
```

**Regla mental:** Web para pensar · Code para ejecutar.

### Decir

*"5 pasos, 5 roles, 5 modelos distintos. El paso 4 — TDD — es donde se consumen más tokens, por eso usamos modelos OSS más baratos. Los demás siguen con Claude porque ahí la calidad importa más que el costo."*

---

## Slide 4 — ★ El corazón: cómo Skill 03 arma el plan automáticamente

### Contenido

Skill 03 no inventa. Usa **4 inputs determinísticos** y produce el `todo.md`.

**Inputs:**

| # | Input | Para qué |
|---|---|---|
| 1 | `specs/NNN-*.md` (la spec aprobada) | Fuente principal. Cada AC → 1+ slice. |
| 2 | `docs/security/<slug>-threat-model.md` | Algunas slices vienen de mitigar STRIDE. |
| 3 | Estado del repo (bootstrap detection) | Si falta `pyproject.toml`/`src/`/`tests/` → agrega Slice 0. |
| 4 | `stacks/python-lambda/rules.md` | Layout hexagonal, deps mínimas, convenciones. |

**Metodología (deterministica):**

```
1. Lee spec → restate goal en 1 frase
2. Bootstrap detection:
   pyproject.toml? src/__init__.py x 3? handler.py? tests/__init__.py?
   → si falta cualquiera → Slice 0 al inicio (excepción única al TDD strict)
3. 1 slice por AC (más si el AC tiene 5+ sub-casos)
4. Cada slice tiene RED · GREEN · REFACTOR
5. Orden: validación primero → happy path → error paths
6. Si una slice estima > 30 min → partirla
7. Si > 10 slices totales → la spec es muy grande, volver a Skill 02
```

**Aplicado a KR-16612 (tree-url-generator):**

```
Slice 0:  Scaffold (no-TDD)                           1 commit chore: scaffold
Slice 1:  AC06 — Fail-fast on missing env var         RED → GREEN
Slice 2:  AC04 — Campos requeridos del body           5 tests por campo faltante
Slice 3:  AC04 — Rechazar campo extra                 RED → GREEN
Slice 4:  AC04 — Sanitización IDs (T4 path traversal) 4 tests (regex)
Slice 5:  AC04 — Boundaries de longitud               4 tests (0, 1, 64, 65)
Slice 6:  AC04 — total_lines en rango                 4 tests
Slice 7:  AC01 — Happy path 200                       RED → GREEN
Slice 8:  AC02 — Pre-signed URL                       RED → GREEN + REFACTOR
Slice 9:  AC03 — Header alterado → 403 (moto)         RED → GREEN
Slice 10: AC05 — Logs estructurados                   3 tests

= 10 slices · 37 tests planeados · ~3-4 h de Skill 04
```

### Decir

*"Esto es lo que diferencia el framework de 'pedirle a Copilot que codée'. La spec define el qué; el plan define el orden de los commits. Cada slice es testable independientemente. Cuando Skill 04 arranque, va a tener un mapa exacto de qué commit hacer primero, segundo, tercero. No hay improvisación."*

---

## Slide 5 — ★ El corazón: gates duros que enforcamos desde día 1

### Contenido

Los gates **no se negocian.** Están enforcedos por harness + CI + commitlint. Si fallan, no se mergea a `main`.

### Calidad del código

| Gate | Threshold | Enforcado por |
|---|---|---|
| Coverage de tests | ≥ 80% por módulo de `src/` | `pyproject.toml` + SonarCloud |
| Lint clean | 0 errores | `ruff check` en CI |
| Types clean | mypy strict sin errores | `mypy --strict src` en CI |
| Sin vulnerabilidades altas | 0 highs/criticals | `pip-audit` + Snyk en CI |
| SonarCloud quality gate | Verde obligatorio | SonarCloud scanner |

### Disciplina TDD

| Gate | Enforcado por |
|---|---|
| **`tdd-trace.md` registra RED → GREEN por slice** | Skill 04 lo escribe en runtime · Skill 05 lo audita |
| 1+ test nombrado por cada AC del spec | Skill 02 § 7 + verificado por Skill 05 |
| 3 intentos max en RED → GREEN, después BLOCKED | Skill 04 limit |
| Spec antes que código (sin spec aprobada no hay `feat:`) | Convención + Skill 05 |
| Commits son **opcionales** (squash / por slice / granular) | Decisión del dev — `tdd-trace.md` es el source of truth |

**Por qué `tdd-trace.md` y no git history:** lo escribe el agente mientras ejecuta el loop (no se reconstruye después), captura el output literal del pytest fallando y pasando, y no depende de la disciplina del dev en separar commits. Es **evidencia primaria**, no proxy.

### Seguridad / autonomía

| Regla | Enforcado por |
|---|---|
| No push directo a `main` | Branch protection + hook `block-main-branch` |
| No `--no-verify`, `--force`, `--force-with-lease` | Hook `block-dangerous-commands` |
| No edit a tests para hacerlos pasar | Limit of autonomy + verificado por Skill 05 |
| No deps nuevas sin justificación | Limit of autonomy |
| No lectura de `~/.ssh`, `~/.aws`, `.env` | Sandbox deny list |
| No edits a `.github/workflows/` ni branch protection | Permisos `ask` en `.claude/settings.json` |

**La cadena completa de defensas:**

```
spec con tests planeados  →  TDD trace enforced por commits  →  hooks bloquean atajos
       →  CI corre todos los gates  →  Skill 05 audita antes de review humano
              →  Human review final  →  Merge a main
```

### Decir

*"Esto es lo que hace que el framework no sea solo 'pedirle al agente que codée'. Cada gate captura una clase de bug. Coverage 80% atrapa código sin tests. TDD trace atrapa el atajo de 'escribo el código y después un test que valida lo que ya hice'. Threat model atrapa vulnerabilidades antes de producción. Las decisiones de scope quedan en el spec, no en cabezas."*

---

## Slide 6 — Cómo arranca cada dev a usarlo

### Contenido

**Setup por dev (15 min, una sola vez):**

1. Pedir acceso al Project de Claude Web `Kriptos AI Delivery` — ya está creado.
2. Tener Claude Code instalado.
3. Clonar los repos del producto a los que vas a contribuir (`kriptos-io/s3-tree-uploader`, etc.).

**Tu próximo ticket — flujo paso a paso:**

| Paso | Dónde | Qué hacés | Tiempo |
|---|---|---|---|
| 1 | Claude Web | Conversación nueva → "Brainstorm KR-XXXXX" | 30 min |
| 2 | Claude Web | Conversación nueva → "Skill 02 sobre el brainstorm" | 15 min |
| 3 | Claude Code en repo del producto | `/plan` | 5 min |
| 4 | Claude Code en repo del producto | `/implement` (loop autónomo, vos supervisás) | 2-4 h |
| 5 | Claude Code o CI | `/review` | 10 min |
| 6 | GitHub | Aprobar PR (review humano final) | 15 min |

**Si te trabás → BLOCKED.** El agente lo dice solo y vos pedís ayuda. No improvisa.

### Decir

*"No tenés que aprender ningún comando nuevo más allá de 'Brainstorm KR-XXXXX'. El agente sabe qué leer, qué preguntar, qué generar. Vos sos el dueño de las respuestas y de las decisiones de scope."*

---

## Slide 7 — Cómo agregamos contexto y extendemos el framework

### Contenido

**Cuando aparece un componente nuevo del Classifier:**

```
1. Branch en classifier-specs:
   git checkout -b docs/add-<componente>
2. Crear archivo en context/classifier-v2/components/<phase>/
3. Actualizar índice components/README.md
4. PR → merge → GitHub connector resincroniza Project automáticamente
```

**Cuando cambia una decisión técnica** → actualizar `context/classifier-v2/current-decisions.md` con PR.

**Cuando hay regla nueva del stack** → actualizar `stacks/python-lambda/rules.md` con PR.

**Las skills cargan on-demand** — no hay que tocarlas cuando se agrega contexto.

**Provisionar un repo nuevo del producto** (cuando arranca una Lambda nueva):

| Opción | Cuándo |
|---|---|
| **Manual** (`cp -r` de `s3-tree-uploader`) | Hoy. ~10 min. |
| **GitHub Template Repository** | Próximo paso. 1 comando. |
| **Skill `repo-provisioning`** | Futuro. Automática. |

**Quién puede contribuir:**

| Rol | Qué puede hacer |
|---|---|
| Tech Lead framework | Aprueba cambios estructurales (skills, roles, stacks). |
| Architect | Identifica gaps en Skill 02 y propone agregarlos. |
| Cualquier dev | PRs para agregar contexto. |

> *El framework no es propiedad de una persona — cualquier dev puede mejorarlo abriendo PR.*

Detalle: `docs/framework-maintenance.md`.

### Decir

*"Esto evita el antipatrón 'el framework lo mantiene Haroldo y nadie más sabe'. Es un activo del equipo, con proceso documentado. Si encontrás una fricción, abrís PR. Si encontrás un componente sin documentar, abrís PR."*

---

## Slide 8 — Qué pedimos del equipo

### Contenido

**Para que el framework funcione, lo que necesitamos:**

1. **Próximo ticket nuevo del clasificador → pasa por Skill 01.** No excepciones.
2. **Si encontrás fricción → abrí issue.** No la sufras en silencio.
3. **Si detectás contexto faltante → PR.** Cualquier dev puede agregar archivos en `context/classifier-v2/`.
4. **Documentá decisiones técnicas en `current-decisions.md`.** Si decidimos algo en un standup, queda en el repo.
5. **No skipees Skill 05.** El review pre-humano es lo que evita que el reviewer humano pierda tiempo en lint y coverage.

**Métrica de éxito a 3 meses:**

| KPI | Objetivo |
|---|---|
| % features que pasaron por el framework | 70% |
| Devs que invocaron al menos 1 skill | 100% del equipo backend |
| Tickets a `main` sin spec aprobada | 0 |
| Wall-clock por Lambda chica | < 24 h |
| Coverage promedio | ≥ 85% (gate 80%) |

**Métrica de éxito a 6 meses:**

| KPI | Objetivo |
|---|---|
| % features que pasaron por el framework | 95% |
| Skill 04 con modelo OSS | Operativo |
| Métricas en dashboard | Confluence page actualizada semanal |
| FTE liberadas (estimado) | ~1.6 |

### Decir

*"Esto no es opcional pero tampoco es ceremonia. La idea es que en 3 meses esto se sienta natural, como hoy se siente abrir un PR. Si lo usamos todos, el costo de mantenerlo lo cubre el ahorro de tiempo en cada feature."*

---

## Slide 9 — Caso real: KR-16612 `tree-url-generator`

### Contenido

**Ticket original (qué teníamos):**

- Lambda detrás de `POST /v2/tree/init`.
- 5 acceptance criteria definidos a mano.
- Sin threat model.
- Sin plan de tests.

**Qué hicimos:**

| Skill | Tiempo | Modelo | Output |
|---|---|---|---|
| 01 Brainstorm | ~30 min | Opus 4.7 | Comentario refinado en KR-16612 + `brainstorms/KR-16612-tree-url-generator.md` |
| 02 Spec | ~10 min | Opus 4.7 | `specs/001-tree-url-generator.md` (11 secciones, 37 tests planeados) + `docs/security/tree-url-generator-threat-model.md` (6 amenazas STRIDE) |

**Métricas concretas:**

| Métrica | Valor |
|---|---|
| Tiempo total Skills 01-02 | ~40 min |
| Costo en tokens | ~$2.50 USD |
| Skills 03-05 (pendiente) | esta semana |
| Repo del producto | `kriptos-io/s3-tree-uploader` (branch `KR-16612-tree-url-generator`) |

### Decir

*"Esto no es teoría. El piloto ya está hecho. La spec está commiteada en el repo del producto, el threat model también. En esta semana ejecutamos Skills 03-05 y cerramos el primer feature end-to-end con el framework."*

---

## Slide 10 — Caso real KR-16612: hallazgos + próximos pasos

### Contenido

**El brainstorm encontró cosas que NO estaban en el ticket original:**

| Hallazgo | Por qué importa |
|---|---|
| **AC06 nuevo:** fail-fast en cold start si `COMPRESSED_TREES_BUCKET` falta | Bug que se descubriría en producción |
| `tree_id` se genera **antes** de validar el body | Correlación en logs de error desde el primer momento |
| Body validation **estricta** (rechaza campos extra) | Decisión arquitectónica explícita, no implícita |
| **8 headers firmados** en lugar de 7 (SSE belt-and-suspenders) | Defensa adicional contra tampering |
| **Q1 abierta:** auth del endpoint marcada como bloqueante de merge a main | Bloqueador explícito documentado |
| **5 amenazas STRIDE** capturadas con mitigación a línea de código | Threat model real |

**Comparativa concreta:**

| Métrica | Ticket original | Después del framework |
|---|---|---|
| Acceptance criteria | 5 | **6** (+1 emergente) |
| Sub-casos enumerados (AC04) | "body inválido" genérico | **19 sub-casos explícitos** |
| Tests planeados | 0 | **37** |
| Open questions formalizadas | 0 | **4** (1 bloqueante) |
| Threat model | nada | **6 STRIDE mitigadas** |

**Próximos pasos:**

| Cuándo | Qué |
|---|---|
| **Esta semana** | Skills 03-05 sobre KR-16612 → cerrar el piloto end-to-end |
| **Próximo sprint** | Cualquier ticket nuevo del backend del Classifier pasa por el framework |
| **Q3 2026** | Template `kriptos-python-template` + modelos OSS para Skill 04 |
| **Q4 2026** | Sub-agent paralelización + Skill 05 como GitHub Action automática |

### Decir

*"AC06 hubiera salido en code review tarde o, peor, en producción. Las 19 sub-casos del AC04 son el equivalente a 19 bugs prevenidos. 37 tests planeados antes de tocar código es la disciplina TDD funcionando. Si el equipo aprueba, en la próxima sprint cualquier ticket nuevo del clasificador pasa por el flujo."*

*"Preguntas?"*

---

## Apéndice — Cómo armar el deck en Gamma

**Pasos en Gamma (free, 10 cards max):**

1. gamma.app → New Gamma → "Generate from text" o "Create blank".
2. Pegá el **Contenido** (no las "Decir") de cada slide en cada card.
3. Para slides 4 y 5 (las del corazón), pedile a Gamma "make this card denser" si recorta tablas.
4. Tema: oscuro o corporativo de Kriptos.
5. Las notas "Decir" van al panel de notas (botón abajo).

**Recursos visuales sugeridos:**

| Slide | Imagen / diagrama |
|---|---|
| 3 | Usar `docs/references/flow-5-steps.png` (ya está en el repo) |
| 4 | Diagrama ASCII está bien; o convertir las slices a una tabla visual |
| 5 | Lista vertical de gates con íconos check |
| 9-10 | Captura del comentario de Jira con el resumen del brainstorm |

**Tiempo total estimado para armarlo:** 30-45 min.

**Bloque de agenda:** 30 min (25 presentación + 5 Q&A) o 45 min (30 + 15).

---

## Apéndice — Q&A esperado

| Pregunta | Respuesta corta |
|---|---|
| "¿Esto reemplaza a los devs?" | No. Decisiones de scope, aprobación de spec, merge final → humano. La máquina hace lo verificable. |
| "¿Y si el agente alucina?" | TDD strict + Skill 05 como gate. Si el código no pasa los tests del spec → BLOCKED automático. |
| "¿Cuánto cuesta empezar?" | $0. Claude Web y Code que ya pagamos. Inversión real: ~1 semana de pulir las skills. |
| "¿Por qué no Copilot directo?" | Copilot completa línea por línea sin contrato. Acá hay spec (contrato) + TDD (disciplina) + Skill 05 (auditoría). |
| "¿Qué pasa con tickets viejos en el backlog?" | Pasan por Skill 01 cuando los retomamos. Solo el flujo nuevo es obligatorio. |
| "¿Cómo lo explicamos al CEO?" | Reducimos ~68% del tiempo-persona por feature manteniendo disciplina de tests y seguridad. Estimado: 1.6 FTE liberadas a 6 meses. |
| "¿Quién mantiene esto?" | Es de todo el equipo. Tech Lead aprueba PRs estructurales; cualquier dev puede agregar contexto. |

---

## Si querés más profundidad, los docs complementarios

- **`docs/framework-overview.md`** — detalle de cada skill (denso).
- **`docs/framework-summary.md`** — versión ejecutiva con tablas de costos y métricas.
- **`docs/framework-maintenance.md`** — cómo se agregan specs y se provisiona repos nuevos.
- **`brainstorms/KR-16612-tree-url-generator.md`** — output real del piloto.
- **`docs/pilots/KR-16612-overview.md`** — resumen ejecutivo del piloto.
