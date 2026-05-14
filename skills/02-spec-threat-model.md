# Skill 02: Spec + Threat Model

Use this skill once the brainstorm (Skill 01) is done — o cuando el usuario pueda proveer inputs equivalentes — y la spec necesita ser escrita.

**Recommended model:** Opus 4.7 (this is the contract the rest of the pipeline depends on; depth beats speed).

**Role:** Architect — see `roles/architect.md`

---

## Audiencia

Esta skill está diseñada para **roles técnicos**: Architect, Tech Lead, Senior Developer. El output es una spec formal que el resto del pipeline consume — no debe ser editada por roles no técnicos.

---

## Inputs aceptados

La skill puede recibir uno o varios de estos. **Es flexible — combina lo que tengas.**

1. **Brainstorm output (Skill 01)** — el caso ideal. Lo lee de:
   - `brainstorms/KR-XXXXX-*.md` en este repo.
   - Comentario del ticket Jira (si hay Atlassian connector).
   - Pegado directamente en el chat.

2. **Épica refinada** — Jira Epic o página Confluence con el contexto de iniciativa.

3. **Tablero de tareas** — link a un sprint/board Jira con N tickets relacionados. La spec puede cubrir uno o varios tickets del tablero.

4. **Draft markdown** — un documento en cualquier ubicación con el problema descrito (propuesta del CEO en Confluence, Google Doc pegado, README en otro repo).

5. **Ticket suelto sin brainstorm previo** — la skill **rehúsa** y dirige al usuario a Skill 01.

6. **Idea vaga sin nada más** — la skill **rehúsa** y dirige al usuario a Skill 01.

### Reconciliación de inputs múltiples

Cuando hay varias fuentes:
1. El agente **lista los inputs detectados** ("Estoy leyendo: brainstorm `brainstorms/KR-16612.md`, épica `KR-16500`, draft markdown pegado en este chat").
2. **Identifica solapamientos y contradicciones** explícitamente.
3. **Pide al usuario que confirme cuál es la fuente de verdad** cuando hay conflicto. No promediar, no fusionar silenciosamente.
4. Recién después genera la spec.

---

## Context loading

**El agente debe cargar todo esto por sí solo desde Project Files / repo. No esperar que el usuario lo pegue.**

Siempre:
1. `roles/architect.md`
2. `templates/SPEC_TEMPLATE.md` — la estructura obligatoria
3. `context/classifier-v2/ecosystem.md`
4. `context/classifier-v2/current-decisions.md` — stack y patrones vigentes

Cuando aplique:
5. `stacks/<stack>/rules.md` — reglas duras del stack que aplica al ticket.
6. Specs vecinas relevantes (si el ticket es Fase 2 GSE, leer lo de Fase 2).

**Si un archivo referenciado no existe**, decirlo explícitamente — no inventar.

---

## Objective

Produce these artifacts:

1. **`specs/NNN-<slug>.md`** — formal spec following `templates/SPEC_TEMPLATE.md`. Goes to the **product repo**.
2. **`docs/security/<slug>-threat-model.md`** — threat model, ONLY if the inputs identified a threat surface. Goes to the product repo.
3. **Context updates** — if Step 2 (Detect missing context) found gaps in `classifier-specs`, the new/updated context files go to a PR in classifier-specs.

---

## Minimal invocation

> "Skill 02 sobre KR-16612"
> "Spec a partir del brainstorm `brainstorms/KR-16612-tree-url-generator.md` y la épica `KR-16500`"

---

## Procedure

1. **List inputs and reconcile.** Read every input the user references. List them. Flag contradictions. Resolve with the user before drafting.

2. **Detect missing context (CRITICAL — antes de escribir spec).**
   Mientras leés los inputs, evaluá si todo lo que el spec va a necesitar **ya existe** en `context/classifier-v2/` o `stacks/`. Buscá gaps tipo:
   - Los inputs mencionan un componente/servicio/integración que no está documentado.
   - Los inputs asumen una decisión técnica que no está en `current-decisions.md`.
   - Los inputs referencian un patrón compartido sin que esté escrito.

   **Si hay gaps:** parar y alertar al usuario con la lista exacta de archivos que faltan o que hay que actualizar. Proponer crearlos. **No avanzar a escribir la spec hasta que el usuario apruebe los gaps a llenar.** Los archivos de contexto nuevos van en el mismo PR que la spec, en el repo `classifier-specs`.

3. Pick the next spec number. Convention: `specs/NNN-<slug>.md`. Start at `001` if the product repo is empty.

4. Draft the spec following every section of `SPEC_TEMPLATE.md` — do NOT skip sections. If a section doesn't apply, mark it explicitly.

5. **Test plan section is mandatory.** For each acceptance criterion, write at least one test name describing the behavior it asserts. Tests come BEFORE code.

6. **Threat model is mandatory if the inputs identified a surface.** Use STRIDE. One row per relevant threat, with mitigation cited (line of code, test, or config).

7. Open questions section: list any deferred items as "Deferred — resolve before phase X".

8. Rollout section: include the conventional commit sequence.

---

## Output format — artifacts markdown editables

**Mientras no haya GitHub connector con escritura**, todos los documentos que esta skill produce se entregan como **artifacts markdown editables en el chat** (no como bloques de código inline en la respuesta del agente). Razones:

- Se descargan con un click (botón Download del artifact).
- Se editan in-place con el usuario antes de commitear.
- No se pierden en el scroll de la conversación.
- El usuario los pega/sube manualmente a cada repo según la tabla de abajo.

**Regla operativa para el agente:** crear un artifact por cada documento listado en la tabla "Required outputs". Nombrar cada artifact con el path final del archivo (ej. el artifact se llama `specs/001-tree-url-generator.md`) para que el usuario sepa exactamente dónde guardarlo. El cuerpo del artifact es markdown puro, listo para commitear sin edición.

Lo único que va inline en la respuesta del chat son: el listado de outputs, el commit plan, las instrucciones de persistencia y el "siguiente paso".

---

## Required outputs

Cada fila = un artifact independiente en el chat.

| # | Artifact (nombre exacto) | Repo destino | Cuándo se genera |
|---|---|---|---|
| 1 | `specs/NNN-<slug>.md` | **producto** (ej. `kriptos-io/s3-tree-uploader`) | Siempre. Sigue `templates/SPEC_TEMPLATE.md` (11 secciones, ninguna skipeable). |
| 2 | `docs/security/<slug>-threat-model.md` | **producto** | Solo si los inputs identificaron threat surface (Skill 01 §5). |
| 3 | `context/classifier-v2/<archivo>.md` (uno por gap detectado) | **classifier-specs** (este repo) | Solo si Step 2 (Detect missing context) encontró gaps de dominio. |
| 4 | `stacks/<stack>/rules-<addendum>.md` | **classifier-specs** | Solo si Step 2 encontró gaps de stack que ameritan addendum (no editar `rules.md` mainstream sin discusión). |

**Inline en la respuesta del chat (NO como artifact)** — el agente lista al final:

- **Commit plan** — secuencia de commits para cada repo (producto + classifier-specs si aplica), con mensajes exactos.
- **Persistencia ejecutada / sugerida** — qué se actualizó en Jira/Confluence (si hay connector) o qué textos pegar manual.
- **Siguiente paso:** Skill 03 — Plan.

---

## Rutas y persistencia — referencia rápida

**Repo del producto** (ej. `kriptos-io/s3-tree-uploader`):

- Branch nuevo: `KR-XXXX-<slug>` desde `main`.
- `specs/NNN-<slug>.md` — artifact #1.
- `docs/security/<slug>-threat-model.md` — artifact #2 si aplica.
- Commits: `chore: spec for <slug> (KR-XXXX)` (un solo commit con spec + threat-model, o dos separados si preferís).
- PR opcional pero recomendado para el primer ticket: target `main`, draft hasta tener implementación.

**Repo de specs (classifier-specs)** — solo si hubo gaps de contexto:

- Branch nuevo: `update-context-for-KR-XXXX` desde `main`.
- `context/classifier-v2/<archivo>.md` — artifacts #3.
- `stacks/<stack>/rules-<addendum>.md` — artifacts #4.
- Commit: `docs: context updates needed by KR-XXXX`.
- PR separado del repo del producto (las dos cosas no comparten history).

**Jira (KR-XXXX):**

- Comentario con: link al PR del producto, link al PR de classifier-specs (si hubo), resumen 1-2 líneas.
- Transition: `Ready for Spec` → `Spec ready`.
- Si no hay Atlassian connector con escritura: entregar el texto exacto del comentario y los pasos manuales.

---

## Persistencia — espejo de Skill 01

El destino depende de **dónde vivió la fuente del brainstorm** (CASO de origen).

### Caso A — La fuente fue una idea cruda guardada en Confluence

Acciones de Skill 02:
- Actualizar la página Confluence con sección "Spec técnica" + link al archivo en el repo del producto.
- Preguntar: "¿creamos ticket Jira ahora para la implementación?"
- Spec + threat model → repo del producto.

### Caso B — La fuente fue un ticket Jira que se refinó simultáneamente con su épica

- Actualizar el ticket con link al PR de la spec.
- Si en el brainstorm se decidió editar también la épica, actualizar la épica con el link.
- Transition del ticket: `Ready for Spec` → `Spec ready`.

### Caso C — La fuente fue un ticket Jira con épica clara

- Comentario en el ticket Jira con link al PR de la spec.
- Transition: `Ready for Spec` → `Spec ready`.

### Caso D — La fuente fue una página Confluence draft

- Actualizar la página Confluence con sección "Spec técnica" + link al archivo en el repo del producto.
- Preguntar: "¿creamos Epic Jira ahora con link a esta spec?"

### En todos los casos

- Spec va a `specs/NNN-*.md` en el **repo del producto** (ej. `kriptos-io/s3-tree-uploader`).
- Threat model va a `docs/security/<slug>-threat-model.md` en el repo del producto.
- Context updates (si los hubo) van como **PR separado** en `classifier-specs`.
- Si no hay connector con permiso de escritura para Jira/Confluence, **entregar los textos a pegar**.

---

## Operating rules

- Spec content in Spanish, code identifiers and commit messages in English.
- Do not invent acceptance criteria. If the inputs didn't capture an AC, ask the user, do not fabricate.
- Do not propose code in the spec — only behavior, contracts, test plan, and threats.
- The spec must be testable. If you can't write a test name for an AC, the AC is not finished.
- Maximum 5 open questions in the final spec. If there are more, the brainstorm wasn't deep enough — route back to Skill 01.
- The spec is the contract. Once committed, downstream skills (03, 04, 05) read ONLY from it. Make it self-contained.
- Do not ask the user to paste files that are already in Project Files / repo. Read them yourself.
- **If you detect missing context (Step 2), do NOT push through.** Stop and ask. The framework only works if `classifier-specs` stays current.
- **If you receive multiple inputs**, list them and reconcile before drafting.
