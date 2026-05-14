# CLAUDE.md — Contrato para Claude Code en este repo

Este repo es la **maquinaria** del framework de IA de Kriptos: skills, roles, templates y contexto del producto. No es un repo de producto. Cuando trabajes acá, vas a estar editando *cómo* trabajan los agentes, no *qué* hace el clasificador.

---

## Qué editás en este repo

| Carpeta | Qué edita | Cuándo |
|---|---|---|
| `skills/` | Las 5 skills del flujo | Cuando se ajusta el procedimiento de un paso |
| `roles/` | Definición de roles del pipeline | Cuando cambian responsabilidades |
| `.claude/commands/` | Comandos invocables desde Claude Code | Cuando hay un nuevo verbo del flujo |
| `templates/` | SPEC_TEMPLATE, ADR_TEMPLATE | Cuando cambia la estructura de specs |
| `stacks/python-lambda/` | Reglas, settings, bootstrap | Cuando cambian convenciones del stack |
| `context/classifier-v2/` | Contexto del producto | Cuando cambia el producto |
| `brainstorms/` | Outputs reales de Skill 01 (uno por ticket o iniciativa) | Después de cada brainstorm |
| `docs/pilots/` | Resúmenes ejecutivos de iniciativas piloto del framework | Cuando una iniciativa cierra una fase |

---

## Qué NO editás

- `kriptos-rust-template/` — es referencia. Cuando creemos `stacks/python-lambda/`, lo traducimos desde acá pero no editamos el original.
- `docs/references/` — archivos cerrados (PDFs, imágenes, notas de reunión).

---

## Workflow

1. **Cambios chicos** (un párrafo, una sección): editar y commitear directo. Ejemplo: aclarar un paso de una skill.
2. **Cambios estructurales** (nueva skill, nuevo rol, cambio del flujo): abrir issue/discusión primero, después PR.

### Convención de commits

- Conventional commits en inglés:
  - `docs: <what>` para cambios de contenido
  - `feat: <what>` para nuevas skills / commands / templates
  - `chore: <what>` para infraestructura del repo (gitignore, hooks)
  - `refactor: <what>` cuando solo reorganizás

### Branches

- `main` es la rama protegida.
- Para cambios no triviales: `feat/<descripción-en-inglés>`, `docs/<descripción>`, etc.

---

## Para entender el flujo desde cero

1. Leé `README.md` — entry point del repo.
2. Mirá `docs/references/flow-5-steps.png` — el flujo visual.
3. Leé `skills/01-brainstorm.md` y `skills/02-spec-threat-model.md` — las dos primeras skills del flujo.
4. Leé `CLAUDE_PROJECT.md` — cómo se configura Claude Web para que use este repo.
5. Mirá `brainstorms/KR-16612-tree-url-generator.md` — primer output real del flujo y `docs/pilots/KR-16612-overview.md` — el contexto de iniciativa.

---

## Cosas a no inventar

- No inventes APIs, módulos o servicios del Classifier que no estén en `context/classifier-v2/`.
- No propongas cambios al flujo de 5 pasos sin consultar al usuario primero — está consensuado con el equipo.
- No agregues skills nuevas sin discutirlo. El número fijo (5) es deliberado.
- No mezcles este repo con repos del producto. Acá viven *reglas*; allá vive *código*.
