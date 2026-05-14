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
│   └── commands/                   comandos invocables desde Claude Code (/brainstorm /spec ...)
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
