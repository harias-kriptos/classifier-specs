Generá, editá, interpretá o reproducí un diagrama en draw.io. Objetivo / referencia: $ARGUMENTS

Usá el skill **diagramador** (`.claude/skills/diagramador/`). Resumen del procedimiento:

1. Leé `.claude/skills/diagramador/referencias/estilo-base.md` — fuente de verdad del estilo.
2. Elegí la herramienta según el caso (**puente**):
   - Diagrama AWS **oficial del producto, reproducible** (se versiona y se regenera de un spec) →
     engine determinístico `context/<producto>/diagrams/aws_drawio.py` + `build_<producto>.py`
     (editás el `build_*.py`, **nunca** el XML; regenerás con `python3 build_<producto>.py`).
   - C4, flowchart, Step Function, tabla, base de datos, diagrama ad-hoc, o **interpretar/reproducir**
     una imagen o `.drawio` → diagramador (XML mxGraph guiado por el estilo).
3. Partí de un snippet de `referencias/snippets.md` — **no armes el XML desde cero**.
4. Bases de datos / EKS → librería de íconos (`referencias/iconos/_uris.json`).
   Motor nuevo → `python3 .claude/skills/diagramador/referencias/scripts/add_icon.py <motor> <imagen>`.
5. Generá el `.drawio` y **validá**:
   `python3 .claude/skills/diagramador/referencias/scripts/validate_drawio.py <archivo>.drawio`.
   Corregí los errores (XML mal formado, data-URI rota) y revisá los avisos
   (texto que desborda, solapamientos, `fontSize<7`).
6. Si el usuario te enseñó un diagrama de referencia, extraé sus reglas a `estilo-base.md`
   (sin duplicar) y guardá el ejemplo en `referencias/ejemplos/`.

Salida: ruta del `.drawio` (abrible en app.diagrams.net o la extensión de draw.io para VSCode)
+ un resumen de las decisiones de estilo.
