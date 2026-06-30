# Skill (utilitaria): Diagramas AWS — reemplazada por el skill `diagramador`

> **Reemplazada.** La skill de diagramas del repo ahora es **`diagramador`**
> (`.claude/skills/diagramador/`): cubre AWS + C4 + flowchart + Step Function +
> tablas + bases de datos, parte de snippets (`referencias/snippets.md`) y **valida**
> el `.drawio` (`referencias/scripts/validate_drawio.py`). Se invoca con `/diagram`
> o pidiendo un diagrama en lenguaje natural (tiene auto-trigger).
>
> Este archivo queda como referencia del **modo AWS reproducible** — el engine
> determinístico que el diagramador usa de puente para el diagrama oficial del producto.

> **No es un paso del flujo de 5.** Las skills `01`–`05` (Brainstorm → Review) son el pipeline.
> Diagramar es soporte: alimenta `context/`, que es input de Skill 01/02. No cambia el flujo.

---

## Modo AWS reproducible (engine determinístico)

**Cuándo:** el diagrama AWS **oficial del producto** que se versiona y se regenera de un
spec — cambiás el spec, regenerás, y el diff queda limpio. Para todo lo demás (C4,
flowchart, Step Function, BD, ad-hoc, interpretar/reproducir una imagen) usá el
diagramador con XML guiado por estilo.

Este modo no genera XML a mano: usa un **engine genérico** + un **spec declarativo**.

- `context/<producto>/diagrams/aws_drawio.py` — engine genérico (catálogo aws4 + estilos).
- `context/classifier-v2/diagrams/build_classifier.py` — spec del producto (nodos/edges/grupos).

> Hoy el engine vive bajo `context/classifier-v2/diagrams/` porque el Classifier es su
> único consumidor. Cuando un segundo producto lo necesite, copiá `aws_drawio.py` a un
> `tools/` compartido y dejá solo los `build_*.py` por producto.

### Procedimiento

1. **Cargar contexto.** Leé la fuente de verdad de la arquitectura en `context/<producto>/`
   (ecosystem, tickets, decisiones). El diagrama refleja eso; no inventa servicios.
2. **Editar el spec, no el XML.** Para un cambio tocás el `build_*.py` (agregar/mover un
   nodo, un edge, una nota). Nunca el `.drawio` a mano — se regenera y perdés el cambio.
3. **¿Servicio nuevo?** Agregá una entrada a `ICONS` en `aws_drawio.py`:
   `"servicio": ("mxgraph.aws4.<resIcon>", CAT["<categoria>"])` (el `resIcon` exacto de aws4).
4. **Generar.** `python3 build_<producto>.py` escribe los `.drawio` en `context/<producto>/`.
5. **Validar.** Confirmá XML well-formed y `mxgraph.aws4.resourceIcon > 0`. También podés
   correr el validador del diagramador:
   `python3 .claude/skills/diagramador/referencias/scripts/validate_drawio.py archivo.drawio`.
6. **Backup.** Si reemplazás diagramas existentes, respaldá los previos en `diagrams/_legacy/`.

### Reglas no negociables del engine

- Servicios = íconos `mxgraph.aws4.resourceIcon` con **color por categoría**, nunca rectángulos.
- **Estado por badge** (elipse arriba-derecha) + leyenda, no por color de relleno — el color es categoría.
- Actores externos **fuera** del `aws_cloud`; IA / terceros = caja dashed gris.
- Edges: sólido gris = síncrono · **dashed rosa = evento** (EventBridge / DDB Stream / S3 / SQS).
- Layout izquierda → derecha; estado compartido (DDB) centrado; una banda (`phase`) por fase.

El detalle de estilo (paletas, tipografía, conectores, C4, flowchart, Step Function) vive
ahora en `.claude/skills/diagramador/referencias/estilo-base.md`.

---

**Relación con el flujo:** este modo alimenta `context/`, input de Skill 01/02.
No reemplaza ningún paso del pipeline.
