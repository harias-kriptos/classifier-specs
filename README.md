# classifier-specs

Framework de spec-driven development con agentes IA para el equipo de Kriptos. Esta carpeta es la maquinaria (skills, roles, templates, contexto del producto). Los repos de cada Lambda son los clientes que la usan.

> **Estado:** en construcción. Stack inicial: Python (Lambda). Primer brainstorm real ejecutado sobre KR-16612 — ver `brainstorms/`.

---

## Mapa rápido

```
classifier-specs/
├── CLAUDE.md                       contrato para Claude Code (cuando alguien abre este repo)
├── CLAUDE_PROJECT.md               instrucciones para pegar en un Proyecto de Claude Web
├── skills/                         las 5 skills del flujo (Brainstorm → Review)
├── roles/                          roles del pipeline (PM, Architect, Tech Lead, Dev, Reviewer)
├── .claude/
│   ├── commands/                   comandos invocables desde Claude Code (/brainstorm /spec /diagram ...)
│   └── skills/                     skills ejecutables (diagramador: diagramas draw.io con auto-trigger)
├── templates/                      plantillas para outputs del pipeline
│   ├── SPEC_TEMPLATE.md                spec técnica (Skill 02, va al repo del producto)
│   ├── ADR_TEMPLATE.md                 decisión arquitectónica
│   ├── JIRA_STORY.md                   descripción de Story/Task (Skill 01 caso C)
│   ├── JIRA_EPIC.md                    descripción de Epic (Skill 01 casos A/D)
│   ├── JIRA_BUG.md                     descripción de Bug formal
│   ├── JIRA_BRAINSTORM_COMMENT.md      comentario con output completo de Skill 01
│   ├── JIRA_PLAN_COMMENT.md            comentario con output de Skill 03
│   ├── JIRA_MERGE_COMMENT.md           comentario final pre-merge (Skill 05 READY)
│   ├── CONFLUENCE_INITIATIVE.md        página estratégica de iniciativa
│   ├── PR_DESCRIPTION.md               descripción del PR de implementación (Skill 04)
│   └── PR_REVIEW_REPORT.md             review report pre-humano (Skill 05)
├── stacks/
│   └── python-lambda/              reglas + bootstrap + settings.json para Python Lambdas
├── context/
│   └── classifier-v2/              contexto del producto (ecosystem, tickets, decisiones)
├── brainstorms/                    outputs reales de Skill 01 (uno por ticket / iniciativa)
│   └── KR-16612-tree-url-generator.md  primer brainstorm ejecutado en Claude Web
├── docs/
│   ├── references/                 PDFs e imágenes (flujo 5 pasos, guía TDD+IA, etc.)
│   └── pilots/                     resúmenes de pilotos del framework
│       └── KR-16612-overview.md
└── kriptos-rust-template/          template para repos Rust (base estructural; piezas se traducen a Python)
```

---

## Por qué cada carpeta existe

El repo mezcla **4 funciones distintas**, cada una en su carpeta. Entender esto es clave para saber dónde va una cosa nueva.

```
1. MAQUINARIA del framework    → skills/, roles/, templates/, stacks/, .claude/
2. CONOCIMIENTO del producto   → context/classifier-v2/
3. EVIDENCIA de uso            → brainstorms/, docs/pilots/
4. DOCUMENTACIÓN para humanos  → docs/, README.md, CLAUDE*.md
```

### 1. Maquinaria del framework

| Carpeta | Por qué existe | Quién la lee |
|---|---|---|
| `skills/` | Define **qué hace cada paso del pipeline**. Una skill = un paso (Brainstorm, Spec, Plan, TDD, Review). | El agente IA al invocar la skill ("Brainstorm KR-XXXX"). |
| `roles/` | Define **cómo se comporta el agente** según el paso. Distintos mindsets: PM hace preguntas, Architect escribe contrato, Reviewer audita. | El agente IA al activar una skill. |
| `templates/` | **Plantillas de outputs estándar** — SPEC, threat model, PR description, comentarios Jira. Asegura outputs comparables entre tickets. | El agente al producir un output que se persiste. |
| `stacks/python-lambda/` | **Reglas duras (MUST/NEVER)** del stack tecnológico. Lo que NO cambia entre tickets pero SÍ entre stacks. Cuando agreguemos otro stack: `stacks/rust-emr/`, `stacks/typescript-react/`. | Skills 02-05 cuando el ticket toca código del stack. |
| `.claude/commands/` | **Atajos invocables desde Claude Code (CLI).** `/plan`, `/implement`, `/review`, `/diagram`. | Claude Code en el repo (no Web). |
| `.claude/skills/` | **Skills ejecutables con auto-trigger.** Hoy: `diagramador` (diagramas draw.io: AWS/C4/flowchart/Step Function/BD, con scripts de íconos y validación). | Claude Code cuando se pide un diagrama (o vía `/diagram`). |

### 2. Conocimiento del producto

| Carpeta | Por qué existe |
|---|---|
| `context/classifier-v2/` | El agente necesita saber **qué es el Classifier** para no inventar. Sin esto alucina: inventa buckets que no existen, decisiones que nunca tomamos. |
| `context/classifier-v2/components/` | Specs detalladas **por componente** (phase-1, phase-2, agent). La skill carga solo el componente del ticket, no todo. Mantiene context budget < 20%. |
| `context/classifier-v2/historical/` | Referencia histórica (master-doc v1, diagramas viejos). **No se carga en skills.** Solo para humanos que quieren entender la evolución. |

**Por qué está separado de `skills/`:** las skills son la maquinaria (cómo se hacen las cosas) y `context/` es el dominio (sobre qué cosas). Si los mezclás, el framework se vuelve específico del Classifier y no se puede reusar para otro producto.

### 3. Evidencia de uso

| Carpeta | Por qué existe |
|---|---|
| `brainstorms/` | Guardar el output de Skill 01 **por ticket** para trazabilidad. Si mañana alguien pregunta "¿cómo decidimos AC06 de KR-16612?", la conversación queda acá. |
| `docs/pilots/` | Resumen ejecutivo **por iniciativa piloto** del framework. Sirve como evidencia + lessons learned. Audiencia: leadership o devs nuevos onboardeándose. |

**Por qué dos carpetas y no una:** `brainstorms/` es output crudo del agente (denso, técnico). `pilots/` es contexto ejecutivo de la iniciativa (qué intentamos, qué aprendimos). Son audiencias distintas.

### 4. Documentación para humanos

| Carpeta / Archivo | Por qué existe |
|---|---|
| `docs/framework-overview.md` | **Detalle denso** de cada skill y del flujo. Documento de referencia. |
| `docs/framework-summary.md` | **Versión ejecutiva** del overview. Foco en ahorros, costos, optimizaciones. |
| `docs/framework-maintenance.md` | **Cómo se mantiene** y se extiende el repo (agregar contexto, provisionar repos). |
| `docs/presentation-deck.md` | **Deck listo para PPT** con 11 slides. |
| `docs/references/` | PDFs, imágenes, notas de reunión. Material que viene de afuera. |
| `README.md` | Entry point del repo. Lo primero que lee alguien que llega al repo en GitHub. |
| `CLAUDE.md` | **Contrato para Claude Code** cuando alguien abre este repo (vs el repo del producto). Le dice qué carpeta puede editar y qué no. |
| `CLAUDE_PROJECT.md` | **Instrucciones para Claude Web Project.** Se pega esto al crear el Project en claude.ai. |

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

---

## Flujo de 5 pasos

```
1. Brainstorm                Claude Web    Opus 4.7
2. Spec + threat model       Claude Web    Opus 4.7
3. Plan + tareas atómicas    Claude Web    Sonnet 4.6
4. TDD implementation        Claude Code   modelo barato (Qwen / DeepSeek vía OpenCode)
5. Review + evals            CI / Claude Code  Sonnet 4.6 + harness
```

Detalle visual: `docs/references/flow-5-steps.png`.

---

## Cómo arranco una feature nueva (flujo objetivo)

1. **Jira** — el ticket `KR-XXXXX` ya existe.
2. **Claude Web** — invoco Skill 01 (`/brainstorm`) sobre el ticket. Salgo con un resumen estructurado.
3. **Claude Web** — invoco Skill 02 (`/spec`) con el resumen del Paso 2. Salgo con `specs/NNN-*.md` y (si aplica) `docs/security/<slug>-threat-model.md`.
4. **Repo del producto** — committeo la spec en una branch de Jira y abro PR (opcional, sólo spec).
5. **Claude Web o Code** — invoco Skill 03 (`/plan`) sobre la spec. Salgo con `todo.md` con tareas atómicas TDD-friendly.
6. **Claude Code** — invoco Skill 04 (`/implement`) que corre el loop `chore: <behavior> (failing)` → `feat: <behavior> (passing)` → `refactor: <what>` por cada tarea del `todo.md`.
7. **Claude Code + CI** — invoco Skill 05 (`/review`) que valida coverage, Sonar, Snyk, evals si aplica.
8. **PR humano** — abro el PR final con todo verde.

Primer caso piloto del framework: **KR-16612 — `tree-url-generator`**. Esta noche se ejecutan Pasos 1-2 (brainstorm + spec). Pasos 3-5 vienen después.

---

## Cómo configuro Claude Web

1. Crear un Proyecto nuevo en claude.ai.
2. Pegar la sección "Descripción del proyecto" de `CLAUDE_PROJECT.md` en la descripción.
3. Pegar la sección "Instrucciones del proyecto" en las instrucciones del Proyecto.
4. Conectar al menos uno de estos MCPs para que el Proyecto lea las skills:
   - **Filesystem MCP** apuntando a este repo (más simple para empezar).
   - **GitHub MCP** apuntando a `kriptos/classifier-specs` (si se sube a GitHub).
5. Opcional: conectar Jira MCP para leer tickets `KR-XXXXX` directamente.

Detalle paso a paso: ver Paso 3 del plan de implementación.

---

## Cómo configuro Claude Code en el repo del producto

1. Aplicar el template del stack (ej. `stacks/python-lambda/`).
2. Copiar `.claude/settings.json` del template, ajustar permisos según el repo.
3. Instalar los hooks (block-main-branch, block-secrets, etc.).
4. Correr `./scripts/bootstrap.sh --check` para confirmar el estado del repo.
5. Empezar la feature con `/brainstorm` (si no se hizo en Web) o pasar directo a `/plan`.

---

## Instalar los comandos globalmente (una vez por dev)

Los comandos `/brainstorm`, `/spec`, `/plan`, `/implement`, `/review` se instalan **globalmente** en tu Claude Code — quedan disponibles en cualquier repo donde abras el cliente, sin que tengas que tocar ese repo.

```bash
git clone git@github.com:harias-kriptos/classifier-specs.git ~/classifier-specs
cd ~/classifier-specs && ./install.sh
```

Eso crea symlinks en `~/.claude/commands/` apuntando a los archivos del repo. Cuando hagas `git pull`, los comandos quedan actualizados solos.

| Comando | Cuándo usarlo |
|---|---|
| `/brainstorm <ticket>` | Skill 01 — refina una idea o ticket Jira |
| `/spec <ref>` | Skill 02 — genera spec + threat model |
| `/plan` | Skill 03 — descompone la spec en `todo.md` TDD-ready |
| `/implement` | Skill 04 — ejecuta el loop TDD escribiendo `tdd-trace.md` |
| `/review` | Skill 05 — valida gates y emite READY/BLOCKED |

**Importante:** los comandos leen las skills desde **este repo clonado localmente** (`~/classifier-specs`). Si el dev hace `git pull` periódicamente, recibe automáticamente las mejoras del framework sin tocar los repos del producto.

---

## TDD trace — source of truth del Skill 04

Cuando Skill 04 corre el loop RED → GREEN → REFACTOR, va escribiendo `tdd-trace.md` en la raíz del repo del producto. Cada slice del `todo.md` queda registrada con:

- El test que se escribió (RED) + output literal del pytest fallando.
- La implementación mínima (GREEN) + output del pytest pasando + ruff + mypy clean.
- El refactor (si aplica) o "skipped".

**`tdd-trace.md` es lo que Skill 05 audita** para confirmar que el ciclo se respetó. Los commits son **opcionales** — el dev decide squash, por slice, o granular. Ver `templates/TDD_TRACE_TEMPLATE.md` para el formato.

---

## Convenciones cruzadas

- **Specs intra-repo**: cada spec vive en el repo del producto bajo `specs/NNN-<slug>.md`.
- **Commits en inglés**, conventional commits (`chore: spec for <feature>`, `chore: <behavior> (failing)`, `feat: <behavior> (passing)`, `refactor: <what>`).
- **Outputs de las skills en español**, código en inglés.
- **TDD obligatorio**: no se mergea código sin un commit fallando previo.
- **Coverage ≥ 80%**, SonarCloud quality gate verde, Snyk sin vulnerabilidades altas.
- **Context budget**: las skills cargan archivos on-demand. Objetivo: < 20% del context window por turno.

---

## Referencias

- `docs/references/flow-5-steps.png` — flujo visual de los 5 pasos con modelos por paso
- `docs/references/claude-code-architecture.png` — arquitectura interna de Claude Code (informativo)
- `docs/references/guia-desarrolladores-tdd-ia.pdf` — guía completa para devs
- `docs/references/template-changes.png` — cambios al template estructural (referencia)
- `docs/references/team-meeting-notes.txt` — notas de la reunión donde se definió el approach
