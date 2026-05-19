# Deck — `classifier-specs` para el equipo de Kriptos

> 11 slides. ~15-20 minutos de presentación.
> 9 sobre cómo funciona el repo y cómo lo vamos a usar todos.
> 2 sobre el caso real (Ticket KR-16612).
>
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
- 5 skills que un agente IA ejecuta — cada una es un paso del flujo.
- 2 herramientas: Claude Web (para pensar) + Claude Code (para ejecutar).
- Disciplina: spec antes que código, TDD enforced, threat model obligatorio.

### Decir

*"Hoy les muestro un repo que ya está vivo y que va a ser parte del día a día de cada dev del clasificador. La idea no es agregarles trabajo — es cambiar la forma en que arrancamos cada ticket para que el agente IA haga el grueso del trabajo repetitivo."*

---

## Slide 2 — Qué hay dentro del repo

### Contenido

```
classifier-specs/
├── skills/                   las 5 skills del flujo
├── roles/                    PM · Architect · Tech Lead · Developer · Reviewer
├── templates/                SPEC, threat model, PR description, Jira comments
├── stacks/python-lambda/     reglas + bootstrap + settings para repos Python
├── context/classifier-v2/    contexto del producto Classifier
│   ├── ecosystem.md            overview del sistema
│   ├── current-decisions.md    decisiones técnicas vigentes
│   ├── components/             specs por componente
│   │   ├── phase-1/              tree-url-generator, tree-uncompressor, etc.
│   │   ├── phase-2/              gse-cycle-init, gse-station-status, etc.
│   │   └── agent/                scanner, classifier, tagging, etc.
│   └── tickets-implementacion.md  catálogo de tickets
├── brainstorms/              outputs reales de Skill 01 (uno por ticket)
└── docs/                     overview, summary, maintenance, deck
```

**Total hoy:**
- 5 skills · 5 roles · 13 templates
- 30+ archivos de contexto del Classifier listos para usar
- Stack Python Lambda configurado con sandbox + hooks

### Decir

*"No es teoría. Hoy el repo ya tiene los 5 skills definidos, los roles, las plantillas, y el contexto del Classifier indexado para que el agente lea sin que se lo pidamos. Está listo para usar."*

---

## Slide 3 — Por qué cada carpeta existe

### Contenido

El repo mezcla **4 funciones distintas**, cada una en su carpeta:

```
1. MAQUINARIA del framework    → skills/, roles/, templates/, stacks/, .claude/
2. CONOCIMIENTO del producto   → context/classifier-v2/
3. EVIDENCIA de uso            → brainstorms/, docs/pilots/
4. DOCUMENTACIÓN para humanos  → docs/, README.md, CLAUDE*.md
```

| Carpeta | Por qué existe |
|---|---|
| `skills/` | Define **qué hace cada paso del pipeline**. Una skill = un paso. Lee el agente cuando vos invocás "Brainstorm KR-XXXX". |
| `roles/` | Define **cómo se comporta el agente** según el paso (PM, Architect, Tech Lead, Developer, Reviewer). Distintos mindsets. |
| `templates/` | **Plantillas de outputs estándar** — SPEC, threat model, PR description, Jira comments. Asegura outputs comparables entre tickets. |
| `stacks/python-lambda/` | **Reglas duras (MUST/NEVER)** del stack. Lo que NO cambia entre tickets pero SÍ entre stacks. |
| `.claude/commands/` | Atajos invocables desde Claude Code (`/plan`, `/implement`, `/review`). |
| `context/classifier-v2/` | **Conocimiento del producto** — qué es el Classifier, qué Lambdas existen, qué decisiones técnicas tomamos. Sin esto, el agente alucina. |
| `context/classifier-v2/components/` | Specs detalladas **por componente** (phase-1, phase-2, agent). El agente carga solo lo del ticket, no todo. |
| `context/classifier-v2/historical/` | Referencia v1 (master-doc, diagramas viejos). **No se carga en skills.** Solo para humanos. |
| `brainstorms/` | Output de Skill 01 **por ticket** para trazabilidad. Si mañana preguntan "¿cómo decidimos AC06?", está acá. |
| `docs/pilots/` | **Resumen ejecutivo por iniciativa piloto** (lessons learned). Audiencia: leadership / nuevos devs. |
| `docs/` | Documentación para **humanos** sobre el framework (overview, summary, maintenance, deck). |
| `docs/references/` | Material externo (PDFs, imágenes, notas de reunión). Inmutable. |

### Regla mental para saber dónde va una cosa nueva

```
¿Es una skill nueva o cambio a existente?      → skills/
¿Es un rol nuevo (Designer, DBA, etc.)?        → roles/
¿Es un template de output nuevo?               → templates/
¿Es un stack nuevo (Rust, TS, Java)?           → stacks/<stack>/
¿Es info del Classifier (componente/decisión)? → context/classifier-v2/
¿Es output de un ticket ejecutado?             → brainstorms/ o docs/pilots/
¿Es doc para humanos sobre el framework?       → docs/
¿Es material externo (PDF, imagen)?            → docs/references/
```

### Decir

*"Esta separación es clave para que el framework escale. La **maquinaria** (skills/roles/templates) define cómo trabaja el agente; el **conocimiento** (context/) le dice sobre qué trabaja; la **evidencia** (brainstorms/pilots) muestra qué se hizo; la **documentación** (docs/) es para nosotros. Si las mezclamos, el framework se vuelve específico del Classifier y no se puede reusar para otro producto."*

---

## Slide 4 — Los 5 skills en una vista

### Contenido

| # | Skill | Cliente | Modelo | Quién la invoca | Output |
|---|-------|---------|--------|-----------------|--------|
| 01 | Brainstorm | Claude Web | Opus 4.7 | Cualquiera (CEO, PM, comercial, tech lead) | Comentario refinado en Jira |
| 02 | Spec + Threat Model | Claude Web | Opus 4.7 | Architect / Tech Lead | `specs/NNN-*.md` + threat model en el repo del producto |
| 03 | Plan | Claude Code | Sonnet 4.6 | Tech Lead / Developer | `todo.md` con slices TDD |
| 04 | TDD Implementation | Claude Code | Modelo barato (OSS) | Developer | Branch + commits TDD + PR draft |
| 05 | Review + evals | Claude Code / CI | Sonnet 4.6 | Developer / CI | READY / BLOCKED |

**Regla mental:** Web para pensar · Code para ejecutar.

### Decir

*"Cada paso tiene un rol claro, un modelo recomendado y un output concreto. No es 'Claude hace todo' — es un pipeline con guardrails. Y noten que el paso 1 lo puede invocar cualquiera, hasta el CEO. No requiere vocabulario técnico."*

---

## Slide 5 — Cómo va a funcionar: end-to-end de un ticket

### Contenido

```
JIRA KR-XXXXX
    │
    ▼
1. BRAINSTORM (Claude Web · 30 min)
    El agente desafía el ticket: AC testables, edge cases, threat surface.
    → Comentario refinado en Jira + copia en brainstorms/
    │
    ▼
2. SPEC + THREAT MODEL (Claude Web · 15 min)
    El agente escribe el contrato: 11 secciones, 1+ test por AC, STRIDE.
    → specs/NNN-*.md y threat-model.md → repo del producto
    │
    ▼
3. PLAN (Claude Code · 5 min)
    El agente descompone en slices TDD-ready.
    → todo.md con RED · GREEN · REFACTOR por slice
    │
    ▼
4. TDD IMPLEMENTATION (Claude Code · 2-4 h)
    El agente ejecuta el loop con commits separados.
    → Branch + commits + tests + impl + PR draft
    │
    ▼
5. REVIEW (Claude Code / CI · 10 min)
    El agente valida coverage, lint, types, threat model.
    → READY / BLOCKED
    │
    ▼
Human review + merge a main
```

### Decir

*"En este flujo, el humano sigue siendo dueño de las decisiones — scope, aprobación de spec, merge final. Lo que se le quita al humano es lo repetitivo: tipear tests, escribir código de plumbing, chequear si pasó el linter."*

---

## Slide 6 — Cómo vamos a documentar specs y agregar contexto

### Contenido

**Cuando hay un componente nuevo del Classifier:**

```
1. Detectar gap
   El agente en Skill 02 dice "falta documentar X" o un dev lo nota.
2. Branch en classifier-specs
   git checkout -b docs/add-<componente>
3. Crear archivo en context/classifier-v2/components/<phase>/
4. Actualizar el índice components/README.md
5. PR → merge
6. El Project de Claude Web lo ve automáticamente (GitHub connector).
```

**Cuando cambia una decisión técnica:**

→ Actualizar `context/classifier-v2/current-decisions.md` con un PR.

**Cuando hay una regla nueva del stack:**

→ Actualizar `stacks/python-lambda/rules.md`.

**Las skills cargan on-demand.** No hay que tocar las skills cuando se agrega contexto — solo agregar archivos en la carpeta correcta.

**Quién puede hacer PRs:** cualquier dev. Tech Lead aprueba.

Detalle: `docs/framework-maintenance.md`.

### Decir

*"El framework no es propiedad de una persona. Cualquiera puede mejorar el contexto o las reglas. La única regla: PR + review del Tech Lead. Esto evita que el repo se desincronice de la realidad del producto."*

---

## Slide 7 — Cómo arranca el equipo a usarlo

### Contenido

**Setup por dev (15 min, una sola vez):**

1. Pedir acceso al Project de Claude Web `Kriptos AI Delivery` — ya está creado.
2. Tener Claude Code instalado en tu máquina.
3. Clonar los repos del producto a los que vas a contribuir (ej. `kriptos-io/s3-tree-uploader`).

**Tu próximo ticket:**

1. **Abrí Claude Web** del Project → conversación nueva.
2. Pegá: *"Brainstorm KR-XXXXX"* (con tu número de ticket).
3. Conversá con el agente, respondé sus preguntas. **20-40 min.**
4. Cuando el resumen esté listo, pegámelo y pasamos a Skill 02.
5. Después abrís Claude Code en el repo del producto y arrancás `/plan`.

**Si te trabás en cualquier paso → BLOCKED.** El agente lo dice solo y vos pedís ayuda.

### Decir

*"No tenés que aprender ningún comando nuevo más allá de 'Brainstorm KR-XXXXX'. El agente sabe qué leer, qué preguntar, qué generar. Vos sos el dueño de las respuestas."*

---

## Slide 8 — Provisionar repos nuevos del producto

### Contenido

**Cuando arranca una Lambda nueva** (`gse-cycle-init`, `tree-uncompressor`, etc.):

| Opción | Cuándo |
|---|---|
| **Manual** (copy desde repo de referencia) | Hoy. ~10 min. |
| **GitHub Template Repository** (`kriptos-python-template`) | Próximo paso. 1 comando. |
| **Skill `repo-provisioning`** | Futuro. Automática. |

**Qué se copia (`s3-tree-uploader` como referencia):**

```
.claude/          settings.json + hooks + rules
.github/          workflows ci-cd-dev.yml + ci-cd-prod.yml + templates
pyproject.toml    deps + config ruff/mypy/pytest
sonar-project.properties
Dockerfile
CLAUDE.md         contrato del agente (editar descripción)
specs/_template.md
```

**Antes del primer commit:**

- Branch protection en `main` (PR + 1 review).
- Variables en GitHub Actions.
- SonarCloud vinculado.

Detalle: `docs/framework-maintenance.md` § 3.

### Decir

*"Cada Lambda es su propio repo. El harness (hooks + sandbox + workflows) se copia de un repo ya configurado. Cuando tengamos el template repo en GitHub, va a ser un comando."*

---

## Slide 9 — Qué pedimos del equipo

### Contenido

**Para que el framework funcione, lo que necesitamos de cada uno:**

1. **Próximo ticket nuevo del clasificador → pasa por Skill 01.** No excepciones. Si te toca uno chico, igual lo refinás 15 minutos.
2. **Si encontrás fricción → abrí issue en `classifier-specs`.** No la sufras en silencio. El framework mejora con feedback.
3. **Si detectás contexto faltante → PR.** Cualquier dev puede agregar archivos en `context/classifier-v2/`. Lo aprobamos rápido.
4. **Documentá las decisiones técnicas en `current-decisions.md`.** Si decidimos algo importante en un standup, queda en el repo.
5. **No skipees Skill 05.** El review pre-humano es lo que evita que el reviewer humano pierda tiempo en lint y coverage.

**Métrica de éxito a 3 meses:**
- 70% de features pasaron por el framework.
- Todo el equipo backend invocó al menos 1 skill.
- Ningún ticket llegó a `main` sin spec aprobada.

### Decir

*"Esto no es opcional pero tampoco es ceremonia. La idea es que en 3 meses esto se sienta natural, como hoy se siente abrir un PR. Si lo usamos todos, el costo de mantenerlo lo cubre el ahorro de tiempo en cada feature."*

---

## Slide 10 — Caso real: Ticket KR-16612 `tree-url-generator`

### Contenido

**Ticket original (qué teníamos):**

- Lambda detrás de `POST /v2/tree/init`.
- 5 acceptance criteria definidos a mano.
- Sin threat model.
- Sin plan de tests.

**Qué hicimos esta semana:**

| Skill | Tiempo | Modelo | Output |
|---|---|---|---|
| 01 Brainstorm | ~30 min | Opus 4.7 | Comentario refinado en KR-16612 |
| 02 Spec | ~10 min | Opus 4.7 | `specs/001-tree-url-generator.md` + `docs/security/tree-url-generator-threat-model.md` |

**Costo:** ~$2.50 USD en tokens. **Total:** 40 min de mi tiempo.

**Repo del producto:** `kriptos-io/s3-tree-uploader` con la spec y el threat model commiteados en la branch `KR-16612-tree-url-generator`.

### Decir

*"Esto no es teoría. El piloto ya está hecho. Mostrar el comentario en Jira si tienen acceso. La spec generada está en el repo del producto, mergeable cuando lo decidamos."*

---

## Slide 11 — Lo que descubrió el piloto KR-16612

### Contenido

**El brainstorm encontró cosas que NO estaban en el ticket original:**

| Hallazgo | Por qué importa |
|---|---|
| **AC06 nuevo:** fail-fast en cold start si `COMPRESSED_TREES_BUCKET` falta | Bug que se descubriría en producción |
| `tree_id` se genera **antes** de validar el body | Correlación en logs de error |
| Body validation **estricta** (rechaza campos extra) | Decisión arquitectónica explícita |
| **8 headers firmados** en lugar de 7 (SSE belt-and-suspenders) | Defensa adicional |
| **Q1 abierta:** auth del endpoint marcada como bloqueante de merge a main | Bloqueador explícito, no implícito |
| **5 amenazas STRIDE** capturadas con mitigación | Threat model real, no de juguete |

**Comparativa concreta:**

| Métrica | Ticket original | Después del framework |
|---|---|---|
| Acceptance criteria | 5 | 6 (+1 emergente) |
| Sub-casos del AC04 enumerados | "body inválido" genérico | **19 sub-casos explícitos** |
| Tests planeados | 0 | **37** |
| Open questions formalizadas | 0 | **4** (1 bloqueante) |
| Threat model | nada | **6 amenazas STRIDE mitigadas** |

**Próximo paso:** Skills 03-05 sobre este mismo ticket en `s3-tree-uploader`.

### Decir

*"Estos hallazgos son los que el framework agrega valor. AC06 hubiera salido en code review tarde o, peor, en producción. Las 19 sub-casos del AC04 son el equivalente a 19 bugs prevenidos. 37 tests planeados antes de tocar código es lo que define la disciplina TDD."*

*"Si el equipo aprueba, en la próxima sprint cualquier ticket nuevo del clasificador pasa por el flujo. Lo extendemos según lo que vayamos aprendiendo."*

---

## Apéndice — Cómo armar el deck visualmente

**Herramienta recomendada:** Gamma (gamma.app). Pegás el contenido de las 10 slides y te arma el deck con diseño coherente en 5 minutos.

**Pasos:**

1. gamma.app → New Gamma → "Generate from text".
2. Pegá todo el contenido de las 10 slides (los bloques **Contenido**, sin las **Decir**).
3. Elegí tema coherente con la imagen de Kriptos.
4. Las notas "Decir" van en el panel de notas de cada slide.
5. Para la slide 4 (flujo end-to-end), reemplazar el ASCII por un diagrama visual del flujo de 5 pasos (usar `docs/references/flow-5-steps.png` como referencia).

**Tiempo total esperado:** 30 min para armar el deck visualmente.

**Bloque de agenda sugerido:** 30 min (20 min presentación + 10 min Q&A).

---

## Apéndice — Q&A esperado

| Pregunta | Respuesta corta |
|---|---|
| "¿Esto reemplaza a los devs?" | No. El humano sigue decidiendo scope, aprobando specs, haciendo merge final. La máquina hace lo verificable. |
| "¿Y si el agente alucina?" | Por eso TDD strict + Skill 05 como gate. Si el código no pasa los tests del spec, BLOCKED automático. |
| "¿Cuánto cuesta empezar?" | $0. Usamos Claude Web y Code que ya pagamos. Inversión real: ~1 semana de pulir las skills. |
| "¿Por qué no Copilot directo?" | Copilot completa línea por línea sin contrato. Acá hay spec (contrato) + TDD (disciplina) + Skill 05 (auditoría). |
| "¿Cuánto tarda en pagarse?" | Estimado: 8 features. Después es ahorro neto. |
| "¿Qué pasa si Claude Web está caído?" | Skills 01-02 quedan bloqueadas. 03-05 corren local. Resiliente parcial. |
| "¿Cómo le explicamos esto al CEO?" | "Reducimos 68% del tiempo-persona por feature manteniendo disciplina de tests y seguridad." |

---

## Referencias para tener abiertas durante la presentación

- `framework-overview.md` — detalle de cada skill (por si preguntan).
- `framework-summary.md` — tabla de ahorros y costos.
- `framework-maintenance.md` — cómo se extiende.
- `brainstorms/KR-16612-tree-url-generator.md` — output real del piloto.
- `context/classifier-v2/components/README.md` — índice del contexto cargado.
