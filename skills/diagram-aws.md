# Skill (utilitaria): Diagramas AWS en draw.io

> **No es un paso del flujo de 5.** Las skills `01`–`05` (Brainstorm → Review) son el pipeline.
> Esta es una skill **de soporte**: se invoca cuando hay que dibujar o actualizar la
> arquitectura de un producto en draw.io. No tiene número y no cambia el flujo.

**Recommended model:** Sonnet 4.6 (es generación determinística + layout, no necesita Opus).

**Role:** Architect — see `roles/architect.md`

---

## Por qué existe

Los `.drawio` escritos a mano (o pedidos en prosa) salían como **cajas de colores genéricas**:
0 íconos AWS, decenas de rectángulos `rounded`. Parecían un diagrama de cajas, no una
arquitectura AWS. La diferencia entre "feo" y "pro" **no es maña de layout**: es usar la
librería oficial `mxgraph.aws4` (los mismos shapes que salen al arrastrar un servicio desde
el panel *AWS* de draw.io) con colores por categoría y contenedores de grupo.

Esta skill no genera XML a mano. Usa un **engine determinístico** + un **spec declarativo**:

- `context/classifier-v2/diagrams/aws_drawio.py` — engine genérico (catálogo + estilos).
- `context/classifier-v2/diagrams/build_classifier.py` — spec del producto (nodos/edges/grupos).

> Hoy el engine vive bajo `context/classifier-v2/diagrams/` porque el Classifier es su único
> consumidor. Cuando un segundo producto necesite diagramas, copiá `aws_drawio.py` a un
> `tools/` compartido y dejá solo los `build_*.py` por producto.

---

## Reglas de estilo (las que hacían falta)

### 1. Siempre íconos `aws4`, nunca rectángulos para servicios
Cada servicio AWS = `shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.<servicio>` con el
`fillColor` de su **categoría**. El engine ya lo encapsula en `Diagram.node(id, icon, ...)`.

### 2. Colores por categoría (paleta oficial 2023+)
| Categoría | Color | Servicios |
|---|---|---|
| Compute | `#ED7100` | Lambda |
| Storage | `#7AA116` | S3 |
| Database | `#C925D1` | DynamoDB |
| App Integration | `#E7157B` | API Gateway, SQS, EventBridge, AppSync |
| Analytics | `#8C4FFF` | EMR, OpenSearch |
| Security | `#DD344C` | Secrets Manager, Cognito |
| ML | `#01A88D` | Bedrock |

### 3. Contenedores de grupo
- `aws_cloud` → frame navy `#232F3E` con ícono de nube. Todo lo AWS va adentro.
- `region` / `vpc` → cuando aplique (teal dashed / morado).
- `phase` → frame **lógico** (no es AWS) para agrupar por fase. Borde gris dashed.

### 4. Actores y cajas negras NO son íconos AWS
- Actores externos (agentes, web, usuario) → `Diagram.actor(...)` (figura de persona/servidor),
  **fuera** del `aws_cloud`.
- Servicios de terceros / IA caja negra → `Diagram.box(..., dashed=True, fill="#ECECEC")`.

### 5. Estado por **badge**, no por color de relleno
El ícono mantiene el color de su categoría. El estado (deployed / WIP / blocked / RFC) va en
una **elipse arriba-derecha** (`status=` en `node(...)`) + leyenda con `Diagram.legend(...)`.
Nunca pintar el servicio entero de verde/rojo: pierde la categoría AWS.

### 6. Edges: síncrono vs evento
- `kind="sync"` → línea sólida gris, flecha llena (invocación directa / PUT / read).
- `kind="async"` → línea **dashed rosa**, flecha abierta (EventBridge / DDB Stream / S3 PutObject / SQS).

### 7. Layout
Flujo **izquierda → derecha**. Actores a la izquierda fuera del cloud, cajas negras a la
derecha. Estado compartido (DDB) prominente y centrado. Una banda (`phase`) por fase.
Posiciones por grilla (`C(i)` + filas con nombre) para que no haya solapamientos.

---

## Procedimiento

1. **Cargar contexto.** Leer la fuente de verdad de la arquitectura en `context/<producto>/`
   (ecosystem, tickets, decisiones). El diagrama refleja eso; no inventa servicios.
2. **Editar el spec, no el XML.** Para un cambio: tocá el `build_*.py` (agregar/mover un nodo,
   un edge, una nota). Nunca editar el `.drawio` a mano — se regenera y perdés el cambio.
3. **¿Servicio nuevo?** Agregá una entrada a `ICONS` en `aws_drawio.py`:
   `"servicio": ("mxgraph.aws4.<resIcon>", CAT["<categoria>"])`. El `resIcon` es el nombre
   exacto del shape en la librería aws4 de draw.io.
4. **Generar.** `python3 build_<producto>.py`. Escribe los `.drawio` en `context/<producto>/`.
5. **Validar.** Confirmar XML well-formed y que `mxgraph.aws4.resourceIcon` > 0:
   ```
   python3 -c "import xml.etree.ElementTree as ET,sys; ET.parse(sys.argv[1]); print('ok')" archivo.drawio
   ```
6. **Backup.** Si reemplazás diagramas existentes, respaldá los previos en `diagrams/_legacy/`.

---

## Output

- Uno o más `.drawio` en `context/<producto>/`, abribles en app.diagrams.net o el plugin de VSCode.
- El spec (`build_*.py`) queda versionado: **el diagrama es reproducible**, no un artefacto suelto.

---

## Operating rules

- **No editar el `.drawio` a mano.** Si algo está mal, se arregla en el spec y se regenera.
- **No inventar servicios** que no estén en `context/<producto>/`. El diagrama es un reflejo, no una propuesta.
- **No pintar servicios por estado** — el estado es badge, el color es categoría AWS.
- Mantener el spec fiel a la fuente: si la arquitectura cambia, primero cambia el contexto, después el diagrama.
- Validar well-formedness antes de dar por hecho el diagrama.

**Relación con el flujo:** esta skill alimenta a `context/`, que es input de Skill 01/02.
No reemplaza ningún paso del pipeline.
