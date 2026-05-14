# Skill 01: Brainstorm

Primera etapa del pipeline. Toma una idea cruda o un ticket existente y lo desafía hasta que sea escribible como spec. Output: conversación que termina en un resumen estructurado y persistencia en el destino correcto (Jira / Confluence / repo).

**Recommended model:** Opus 4.7 (decide scope; depth beats speed).

**Role:** Product Manager — see `roles/product-manager.md`

---

## Audiencia

Esta skill está diseñada para que la use **gente no técnica** o **técnica** indistintamente:

- CEO / liderazgo trayendo una idea estratégica
- Product Manager refinando una iniciativa
- Comercial trayendo un pedido de cliente
- Tech Lead validando que un ticket Jira esté listo para implementación

No requiere vocabulario técnico para invocarla.

---

## Context loading (automático)

**El agente debe cargar todo esto por sí solo desde Project Files. No pedir al usuario que lo pegue.**

Siempre:
1. `roles/product-manager.md`
2. `context/classifier-v2/ecosystem.md`

Cuando aplique:
3. Si el ticket menciona un componente específico, leer el archivo más cercano bajo `context/classifier-v2/`.
4. Si el usuario referencia decisiones previas, consultar `context/classifier-v2/current-decisions.md`.

Templates que la skill puede entregar al final (según el caso de persistencia):
- `templates/JIRA_STORY.md`
- `templates/JIRA_EPIC.md`
- `templates/JIRA_BRAINSTORM_COMMENT.md`
- `templates/CONFLUENCE_INITIATIVE.md`

**Si un archivo referenciado no existe**, decir explícitamente — no inventar.

---

## Formatos de input aceptados

1. **Referencia a ticket Jira** (`KR-XXXXX`): si hay Atlassian connector, leer Jira directamente. Si no, pedir body.
2. **Idea cruda en lenguaje natural**: ej. *"Queremos que el cliente pueda exportar sus reportes en PDF"*.
3. **Link a página Confluence**: leer la página y usarla como punto de partida.
4. **Body de ticket pegado en chat**.

---

## Objective

Tomar una idea o ticket y **desafiarlo** hasta que la spec sea escribible. El agente NO escribe la idea — la trae el usuario. El agente refina.

Al final de esta skill el usuario debe tener:
- Open questions resueltas o explícitamente diferidas
- Acceptance criteria testables (cada uno mapea a al menos un test)
- Edge cases identificados
- Out-of-scope marcado
- Threat surface identificada (auth, network, untrusted input, secrets, PII)

---

## Minimal invocation

> "Brainstorm KR-16612"
> "Brainstorm idea: queremos que el cliente exporte sus reportes en PDF"
> "Brainstorm sobre el ticket: [body pegado]"
> "Brainstorm sobre esta página Confluence: [link]"

**No es necesario** explicarle al agente qué archivos leer ni qué rol activar — eso ya está en esta skill.

---

## Procedure

1. **Detectar el formato de input** y leerlo (Jira / texto / Confluence).
2. **Restatement**: en 2-3 frases, el agente reformula qué entendió. El usuario confirma o corrige.
3. **Pregunta de destino (al inicio, no al final)**: identificar el caso de persistencia A/B/C/D ANTES de empezar a refinar. Determina qué template se usa al final.
4. **Desafiar el ticket** en 6 dimensiones, **una a la vez** (no dumpear todas las preguntas juntas):

   **A. Scope clarity**
   - ¿Qué entrega esto que antes no existía?
   - ¿Es un behavior o varios? ¿Debe partirse?
   - ¿Qué NO está en scope?

   **B. Acceptance criteria**
   - Para cada AC: ¿es testable? ¿cómo verificarías que falló?
   - ¿Hay AC para el happy path Y para al menos un failure?

   **C. Edge cases**
   - ¿Qué inputs rompen esto? (vacío, oversized, malformado, unicode, race conditions)
   - ¿Qué estado externo puede causar falla? (red caída, S3 unavailable, IAM faltante)

   **D. Integration**
   - ¿De qué depende esto que otra persona/equipo posee?
   - ¿Qué depende de esto? (downstream consumers)

   **E. Threat surface**
   - ¿Input no confiable? ¿Path traversal?
   - ¿Secretos necesarios? ¿Dónde viven?
   - ¿API pública? ¿Auth / rate limiting?
   - ¿Datos persistidos? ¿PII?

   **F. Observability**
   - ¿Qué logs son requeridos? ¿Qué campos?
   - ¿Qué métrica indica que está funcionando en prod?

5. Pedirle al usuario que comprometa cada respuesta. El agente no decide — el usuario sí.
6. **Parar** cuando el exit checklist sea verdadero (abajo).

**Máximo 3 preguntas por respuesta.** Context window pequeño es mejor.

---

## Exit checklist

Parar cuando TODAS sean verdaderas:
- [ ] Cada AC es testable (el usuario confirma)
- [ ] Edge cases listados (al menos 3-5)
- [ ] Open questions resueltas o explícitamente deferidas
- [ ] Threat surface identificada (o "ninguna" stated explícitamente)

---

## Persistencia (CRÍTICO — antes de cerrar la conversación)

El agente determina el caso aplicable en el paso 3 del Procedure, y al final ejecuta la persistencia correspondiente. **En todos los casos el agente pregunta antes de escribir externamente — no decide solo.**

### Árbol de decisión

```
¿De dónde viene la idea?

  ──► Ya hay ticket Jira (KR-XXXXX):
        ¿El ticket tiene épica padre o documentación contextual?
          ├─ Sí, claramente               →  CASO C
          └─ No / no refinado             →  CASO B

  ──► Ya hay página Confluence draft:    →  CASO D

  ──► Idea cruda, sin destino:           →  CASO A
```

### Caso A — Idea cruda sin destino

El agente pregunta:

> *"¿Dónde guardo el output? Recomiendo Confluence. ¿Me podés pasar el link del espacio o página padre de Confluence donde crear la nueva página? Si no querés Confluence, opciones alternativas: crear Epic Jira directo, o guardar solo en classifier-specs/brainstorms."*

- Si el usuario pasa link Confluence → crear página nueva usando `templates/CONFLUENCE_INITIATIVE.md`.
- Si elige Epic Jira → crear Epic usando `templates/JIRA_EPIC.md`. Pedir board.
- Si elige solo repo → guardar en `brainstorms/<slug>.md`.

**Siempre** además: copia en `brainstorms/<slug>.md` para trazabilidad.

### Caso B — Ticket Jira existe pero sin contexto / no refinado

El agente NO crea épica automáticamente. Mantiene foco en el ticket. Pregunta:

> *"Este ticket no tiene épica padre clara ni doc de contexto. ¿Cómo procedemos?*
> *1. Solo editar este ticket con el resumen (no toco épica).*
> *2. Crear/editar la épica padre + editar este ticket. Para esto necesito link de Confluence o board Jira para la épica.*
> *3. Procedemos sin contexto adicional (queda como Caso C)."*

- Opción 1: solo `JIRA_STORY.md` + `JIRA_BRAINSTORM_COMMENT.md` en el ticket.
- Opción 2: lo mismo que opción 1 + crear/actualizar Epic (usando `JIRA_EPIC.md`) o página Confluence (usando `CONFLUENCE_INITIATIVE.md`) si el user da link.
- Opción 3: igual que Caso C.

**Siempre** además: copia en `brainstorms/KR-XXXXX-<slug>.md`.

### Caso C — Ticket Jira con épica / contexto claro

El agente sugiere ejecutar:

1. Actualizar **descripción del ticket** usando `templates/JIRA_STORY.md` (resumen + AC refinados + edge cases + threat + links).
2. Agregar **comentario nuevo** con el log completo usando `templates/JIRA_BRAINSTORM_COMMENT.md`.
3. **Transition status** del ticket: `Backlog` → `Ready for Spec` (o el equivalente).
4. **Copia** en `brainstorms/KR-XXXXX-<slug>.md`.

### Caso D — Página Confluence existente

El agente sugiere ejecutar:

1. Actualizar la **página Confluence** usando `templates/CONFLUENCE_INITIATIVE.md` (refinamiento del contenido existente).
2. Preguntar: *"¿Creamos un Epic Jira con link a esta página?"* — si sí, usar `templates/JIRA_EPIC.md`.
3. **Copia** en `brainstorms/<slug>.md`.

### Reglas generales de persistencia

- Si el Project tiene Atlassian connector con permiso de escritura, ofrecer ejecutar con confirmación del usuario.
- Si no hay connector con escritura, entregar los textos exactos listos para pegar + los links donde pegarlos.
- El agente nunca escribe en Jira/Confluence sin confirmación explícita del usuario.
- La copia en `brainstorms/` se commitea localmente con `chore: brainstorm for <ref>`.

---

## Required output structure (resumen markdown final)

Al final del brainstorm, el agente entrega un resumen markdown con estas secciones (el mismo que se persiste como comentario Jira si aplica):

1. **Resumen del ticket / idea** (2-3 frases)
2. **Acceptance criteria refinados** (lista testable)
3. **Edge cases identificados**
4. **Out of scope** (explícito)
5. **Threat surface** (o "ninguna")
6. **Open questions deferidas** (con dueño y bloqueante)
7. **Persistencia aplicada** (caso + acciones ejecutadas + textos listos para pegar)
8. **Siguiente paso:** Skill 02 — Spec + Threat Model

---

## Operating rules

- Máximo 3 preguntas por respuesta. Context window chico.
- Si el usuario empuja a saltarse al código, push back una vez explicando por qué (sin spec = sin contrato = mal código), después defer.
- Outputs en español. Identificadores y commits en inglés.
- **Nunca pedir al usuario que pegue archivos que ya están en Project Files.** Leerlos solo.
- **Nunca escribir en Jira / Confluence sin confirmación explícita.**
- Nunca escribir la spec en esta skill — esa es Skill 02.
