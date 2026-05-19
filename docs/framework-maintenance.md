# Framework `classifier-specs` — Mantenimiento y extensión

> Documento operacional. Cubre cómo se hace crecer el framework: agregar contexto del producto, aplicar el harness a repos nuevos, y propagar mejoras.

---

## 1. Modelo mental — dónde vive cada cosa

El framework tiene **dos repos** que cumplen funciones distintas y nunca se mezclan:

| Repo | Qué contiene | Quién lee |
|---|---|---|
| **`classifier-specs`** (este) | Maquinaria del framework + contexto del producto Classifier. Skills, roles, templates, reglas de stack, ecosystem, decisiones técnicas. | Claude Web (Skills 01-02) + Claude Code (Skills 03-05) vía GitHub MCP. |
| **`kriptos-io/<lambda-name>`** (repos del producto) | Una Lambda por repo. Spec local, threat model local, código, tests, infra de Claude Code (`.claude/`, hooks), CI (`.github/workflows/`). | Claude Code (Skills 03-05) + el dev humano. |

**Regla simple:**

```
¿Es info del PRODUCTO Classifier (qué hace, cómo, qué componentes tiene)?
  → vive en classifier-specs/context/classifier-v2/

¿Es info del FRAMEWORK (skills, roles, templates, reglas de stack)?
  → vive en classifier-specs/{skills,roles,templates,stacks}/

¿Es CÓDIGO o specs de UNA Lambda concreta?
  → vive en kriptos-io/<lambda-name>/
```

---

## 2. Cómo agregar más contexto a `classifier-specs`

### 2.1 Tipos de contexto y dónde van

| Tipo de contexto | Ubicación | Ejemplo |
|---|---|---|
| **Componente nuevo del producto** (Lambda, agent module, etc.) | `context/classifier-v2/components/{phase-1, phase-2, agent}/<componente>.md` | Una Lambda nueva en Phase 3 → `components/phase-3/<nueva-lambda>.md` |
| **Convención cross-cutting del producto** (cómo se loguea, cómo se nombran buckets, etc.) | `context/classifier-v2/ecosystem.md` § Convenciones cruzadas | Política de retención de S3 lifecycle |
| **Decisión técnica vigente** (qué stack, qué patrón, qué decidimos descartar) | `context/classifier-v2/current-decisions.md` | "Migramos de DynamoDB on-demand a provisioned con autoscaling" |
| **Regla del stack** (MUST/NEVER, layout, deps) | `stacks/<stack>/rules.md` | "MUST usar `tenacity` para retries con backoff" |
| **Nuevo stack** (Rust, TypeScript) | `stacks/<stack>/` (nuevo directorio con rules.md, settings.json, bootstrap.sh) | `stacks/rust-emr/` |
| **Plantilla nueva** (formato de salida para una skill) | `templates/<NOMBRE>.md` | `templates/RUNBOOK.md` para runbooks operacionales |
| **Histórico / referencia** (no se carga en skills, solo de consulta) | `context/classifier-v2/historical/` | Architecture diagrams viejos, master-doc legacy |

### 2.2 Workflow para agregar contexto

```
1. Detectar el gap
   ├── Skill 02 lo flaggea en su fase Detect missing context
   └── O el dev lo detecta a mano leyendo el repo

2. Crear branch en classifier-specs
   git checkout -b docs/add-<topic>-context

3. Agregar archivo(s) en la carpeta correspondiente
   (ver tabla 2.1)

4. Actualizar índices
   ├── context/classifier-v2/ecosystem.md         (si es un nuevo componente)
   ├── context/classifier-v2/components/README.md (si es un nuevo componente)
   └── context/classifier-v2/current-decisions.md (si es una nueva decisión)

5. Commit + PR
   git commit -m "docs: add <topic> context"
   gh pr create --title "docs: add <topic>" --base main

6. Después del merge, sincronizar Claude Web
   El GitHub connector del Project se actualiza automáticamente.
   Si tarda > 5 min, refrescar manualmente desde la UI del Project.
```

### 2.3 Cómo las skills consumen el contexto nuevo

Una vez en `main` y sincronizado:

- **Skill 01** lo carga automáticamente al leer `ecosystem.md` y seguir links a componentes.
- **Skill 02** lo carga durante la fase Detect missing context — si el ticket toca el componente, lee la spec.
- **Skill 03+** no consume contexto de dominio (solo lee la spec local del repo del producto).

No hay que tocar las skills — el contexto se carga **on-demand** por nombre de archivo. La regla `< 20 % context budget` evita que se cargue todo cada vez.

### 2.4 Convenciones para escribir contexto nuevo

- **Markdown puro**, sin HTML.
- **Encabezados claros** (#, ##, ###) — las skills extraen secciones por nombre.
- **Tablas para datos estructurados**, no listas de listas.
- **Code blocks con lenguaje declarado** (` ```python `, ` ```bash `).
- **Cross-references como links Markdown**: `[texto](../path/al/archivo.md)`. Evitar paths absolutos.
- **Tamaño:** un archivo por componente o concepto. Si pasa de 500 líneas, partirlo.
- **Tono:** descriptivo y operacional. Sin marketing.

---

## 3. Cómo aplicar el harness a un repo nuevo del producto

### 3.1 Qué es "el harness" en el repo del producto

El conjunto de archivos que hace que Claude Code corra disciplinadamente en un repo de Lambda:

```
<repo del producto>/
├── .claude/
│   ├── settings.json          permisos pre-aprobados + sandbox + hooks registrados
│   ├── hooks/
│   │   ├── block-main-branch.sh
│   │   ├── block-secrets.sh
│   │   ├── block-dangerous-commands.sh
│   │   ├── enforce-tdd-trace.sh
│   │   └── post-edit-python.sh
│   └── rules/
│       ├── tdd.md
│       ├── testing.md
│       ├── aws.md
│       ├── docker.md
│       ├── secrets.md
│       └── dependencies.md
├── .github/
│   ├── workflows/
│   │   ├── ci-cd-dev.yml      ruff + mypy + pytest + Snyk + Sonar
│   │   └── ci-cd-prod.yml     mismo + gates más estrictos
│   ├── pull_request_template.md
│   └── ISSUE_TEMPLATE/{bug,feature}.md
├── CLAUDE.md                  contrato del agente para este repo
├── AGENTS.md                  pointer a CLAUDE.md (Codex/Cursor/Aider)
├── CONTRIBUTING.md            guía humana (stack, branching, CI)
├── pyproject.toml             deps + config de ruff/mypy/pytest
├── .python-version            3.11.x
├── sonar-project.properties
├── Dockerfile
├── specs/_template.md         plantilla local de spec (mirror de SPEC_TEMPLATE.md)
└── docs/
    └── architecture/_adr_template.md
```

### 3.2 Workflow para provisionar un repo nuevo

**Opción A — Manual (lo que está hoy):**

1. Crear repo en GitHub: `gh repo create kriptos-io/<lambda-name> --private`.
2. Clonar y entrar.
3. Copiar el harness de un repo del producto que ya tenga la última versión:
   ```bash
   REF=/Users/harias25/Desktop/Fuentes/Kriptos/s3-tree-uploader
   cp -r $REF/.claude $REF/.github $REF/specs $REF/docs .
   cp $REF/{CLAUDE.md,AGENTS.md,CONTRIBUTING.md,pyproject.toml,.python-version,Dockerfile,sonar-project.properties,.gitignore} .
   ```
4. Editar `CLAUDE.md` con el ticket prefix y el slug del repo.
5. Editar `pyproject.toml` con el nombre del package.
6. Crear primera branch desde `main` siguiendo convención: `KR-XXXX-<slug>`.
7. Configurar variables en GitHub: `Settings → Secrets and variables → Actions → Variables` para `EMR_SERVERLESS_APPLICATION_ID_*`, `S3_BUCKET_NAME_*`, etc.
8. Habilitar branch protection en `main` (PR + 1 review aprobado).
9. Conectar SonarCloud (proyecto `kriptos-io_<lambda-name>`).
10. Crear teams `development-team` y `qa-team` con permisos push.

**Opción B — Template repo (recomendado, falta crear):**

Crear `kriptos-io/kriptos-python-template` como GitHub Template Repository. Cuando se necesite un repo nuevo:

1. `gh repo create kriptos-io/<lambda-name> --template kriptos-io/kriptos-python-template`.
2. Clonar.
3. Editar `CLAUDE.md` y `pyproject.toml`.
4. Crear branch.
5. Pasos 7-10 de Opción A.

**Opción C — Skill `repo-provisioning` (futuro, ver `docs/references/guia-desarrolladores-tdd-ia.pdf`):**

Una skill nueva que automatice todo lo anterior. Recibe nombre del repo + ticket + stack, y deja el repo listo. Por ahora **no existe** en este framework.

### 3.3 Qué cambia por repo

| Archivo | Editar al provisionar | Mantener idéntico |
|---|---|---|
| `CLAUDE.md` | Sí — descripción del Lambda, ticket prefix, slug | — |
| `pyproject.toml` | Sí — nombre del package | Las deps base sí |
| `sonar-project.properties` | Sí — proyecto SonarCloud | — |
| `.python-version` | No (3.11.x para todos) | Sí |
| `.claude/settings.json` | Quizás permisos específicos | Mayormente sí |
| `.claude/hooks/*` | No | Sí (vienen del template) |
| `.claude/rules/*` | No | Sí (vienen del template) |
| `.github/workflows/*` | No | Sí (vienen del template) |
| `specs/_template.md` | No | Sí |
| `Dockerfile` | Quizás (si Lambda usa container image) | Mayormente sí |

---

## 4. Cómo propagar mejoras del harness a repos existentes

Cuando se mejora el harness (ej. nuevo hook, regla actualizada, workflow CI nuevo), hay que propagarlo a todos los repos del producto. Hoy es manual; en el futuro vía la skill `repo-provisioning`.

### 4.1 Workflow manual

```
1. Hacer el cambio en kriptos-io/kriptos-python-template (cuando exista)
   o en classifier-specs/stacks/python-lambda/ + un repo de referencia.

2. Identificar todos los repos del producto afectados:
   gh repo list kriptos-io --json name --jq '.[] | select(.name | startswith("kr-") or .name | endswith("-lambda")) | .name'

3. Para cada repo:
   - Branch: KR-XXXX-update-harness
   - Aplicar el cambio (copiar archivo, actualizar workflow, etc.)
   - Commit: chore: update <piece> harness
   - PR

4. Mergear los PRs cuando CI verde.
```

### 4.2 Cuándo NO propagar

- Si el cambio es experimental (rule nueva no probada en al menos 1 repo piloto durante 1 sprint).
- Si rompe backwards compatibility (ej. nuevo hook que bloquea código que ya está en main de algunos repos).
- Si afecta CI de producción sin haber pasado por staging.

### 4.3 Versionado del harness

Cada cambio significativo al harness va en `CHANGELOG.md` de `classifier-specs` con:

- Versión semver: `harness-py-1.2.0`.
- Qué cambió.
- Cómo aplicar a repos existentes (diff o comando).
- Repos afectados (si solo aplica a algunos).

---

## 5. Quién hace qué

| Rol | Responsabilidad |
|---|---|
| **Tech Lead del framework** (Haroldo, por ahora) | Aprueba cambios a skills, roles, templates, stacks. Decide cuándo se propaga un cambio de harness. |
| **Architect** | Identifica gaps de contexto durante Skill 02 y propone agregarlos en classifier-specs. Mantiene `current-decisions.md` al día. |
| **Developer** | Detecta fricciones del harness en su trabajo y abre issues/PRs en classifier-specs. |
| **Cualquier dev** | Puede agregar contexto nuevo a `context/classifier-v2/` vía PR. |
| **CI / Reviewer** | Verifica que cambios al harness no rompan CI de repos del producto (probar en un repo piloto antes de propagar). |

---

## 6. Checklist al agregar contexto nuevo

Antes de mergear un PR que agrega contexto a `classifier-specs`:

- [ ] El archivo está en la carpeta correcta (ver § 2.1).
- [ ] Está linkeado desde el índice apropiado (`ecosystem.md`, `components/README.md`, `current-decisions.md`).
- [ ] Sigue las convenciones de escritura (§ 2.4).
- [ ] No duplica contenido de otro archivo.
- [ ] Si reemplaza algo, el archivo viejo está marcado como deprecated o eliminado.
- [ ] El Project de Claude Web se sincroniza después del merge (si no se sincroniza solo, refrescar Project Files manualmente).

---

## 7. Checklist al provisionar un repo nuevo

Antes de empezar a trabajar en un repo nuevo del producto:

- [ ] Repo creado en `kriptos-io/<lambda-name>`.
- [ ] `.claude/`, `.github/`, `specs/`, `docs/` copiados del template o repo de referencia.
- [ ] `CLAUDE.md` editado con descripción y ticket prefix.
- [ ] `pyproject.toml` editado con nombre del package.
- [ ] `sonar-project.properties` editado con la key SonarCloud.
- [ ] Branch protection en `main` activado.
- [ ] Variables de GitHub Actions configuradas.
- [ ] SonarCloud project creado y vinculado.
- [ ] Teams `development-team` y `qa-team` con permisos push.
- [ ] CI dummy (commit vacío en branch) verde antes de empezar feature work.

---

## Apéndice — Estructura de carpetas resumida

```
classifier-specs/
├── skills/                            5 skills del flujo (no editar a la ligera)
├── roles/                             5 roles (no editar a la ligera)
├── templates/                         plantillas de outputs (estables)
├── stacks/
│   └── python-lambda/                 reglas + bootstrap + settings.json
│                                        ← aquí se editan reglas del stack
├── context/
│   └── classifier-v2/
│       ├── ecosystem.md               ← overview del producto
│       ├── current-decisions.md       ← decisiones cerradas
│       ├── tickets-source.md          ← índice de tickets
│       ├── components/                ← UNA carpeta por área
│       │   ├── README.md              ← índice de components
│       │   ├── phase-1/               ← Lambdas de Phase 1
│       │   ├── phase-2/               ← Lambdas + infra de Phase 2
│       │   └── agent/                 ← specs del agente
│       └── historical/                ← referencia v1, no se carga
├── brainstorms/                       outputs de Skill 01 (uno por ticket)
├── docs/
│   ├── pilots/                        resúmenes ejecutivos de pilotos
│   ├── references/                    PDFs, imágenes, notas
│   ├── framework-overview.md          documento densamente referenciable
│   ├── framework-summary.md           resumen ejecutivo para slides
│   └── framework-maintenance.md       este documento
└── .claude/
    └── commands/                      comandos invocables desde Claude Code
```
