# classifier-specs

Framework de spec-driven development con agentes IA para el equipo de Kriptos. Esta carpeta es la maquinaria (skills, roles, templates, contexto del producto). Los repos de cada Lambda son los clientes que la usan.

> **Estado:** demo en construcción (2026-05-13). Stack inicial: Python (Lambda).

---

## Mapa rápido

```
classifier-specs/
├── CLAUDE.md                       contrato para Claude Code (cuando alguien abre este repo)
├── CLAUDE_PROJECT.md               instrucciones para pegar en un Proyecto de Claude Web
├── skills/                         las 5 skills del flujo (Brainstorm → Review)
├── roles/                          roles del pipeline (PM, Architect, Dev, Reviewer)
├── .claude/
│   └── commands/                   comandos invocables desde Claude Code (/brainstorm /spec ...)
├── templates/                      SPEC_TEMPLATE.md, ADR_TEMPLATE.md
├── stacks/
│   └── python-lambda/              reglas + bootstrap + settings.json para Python Lambdas
├── context/
│   └── classifier-v2/              contexto del producto (ecosystem, tickets, decisiones)
├── demo/
│   └── ticket-1-tree-url-generator/   outputs de la demo piloto
├── docs/
│   └── references/                 PDFs e imágenes de referencia (flujo 5 pasos, guía TDD+IA, etc.)
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

1. **Jira** — el ticket `KT-XXXXX` ya existe.
2. **Claude Web** — invoco Skill 01 (`/brainstorm`) sobre el ticket. Salgo con un resumen estructurado.
3. **Claude Web** — invoco Skill 02 (`/spec`) con el resumen del Paso 2. Salgo con `specs/NNN-*.md` y (si aplica) `docs/security/<slug>-threat-model.md`.
4. **Repo del producto** — committeo la spec en una branch de Jira y abro PR (opcional, sólo spec).
5. **Claude Web o Code** — invoco Skill 03 (`/plan`) sobre la spec. Salgo con `todo.md` con tareas atómicas TDD-friendly.
6. **Claude Code** — invoco Skill 04 (`/implement`) que corre el loop `chore: <behavior> (failing)` → `feat: <behavior> (passing)` → `refactor: <what>` por cada tarea del `todo.md`.
7. **Claude Code + CI** — invoco Skill 05 (`/review`) que valida coverage, Sonar, Snyk, evals si aplica.
8. **PR humano** — abro el PR final con todo verde.

Para la demo de esta noche: **solo Pasos 1-2** sobre Ticket 1. Pasos 3-5 son bonus.

---

## Cómo configuro Claude Web

1. Crear un Proyecto nuevo en claude.ai.
2. Pegar la sección "Descripción del proyecto" de `CLAUDE_PROJECT.md` en la descripción.
3. Pegar la sección "Instrucciones del proyecto" en las instrucciones del Proyecto.
4. Conectar al menos uno de estos MCPs para que el Proyecto lea las skills:
   - **Filesystem MCP** apuntando a este repo (más simple para la demo).
   - **GitHub MCP** apuntando a `kriptos/classifier-specs` (si se sube a GitHub).
5. Opcional: conectar Jira MCP para leer tickets `KT-XXXXX` directamente.

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
