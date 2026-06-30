---
name: diagramador
description: Crea, interpreta y reproduce diagramas de arquitectura de sistemas en formato draw.io (diagrams.net) — AWS, modelo C4, flowcharts funcionales, máquinas de estado / Step Functions, tablas y bases de datos. Úsalo cuando el usuario pida crear, editar, interpretar o reproducir un diagrama, o cuando envíe un diagrama (imagen o archivo .drawio) como referencia. Aplica un estilo visual consistente (colores, tipografías, tamaños, espaciado) definido en referencias/estilo-base.md, parte de los snippets de referencias/snippets.md y valida el resultado con referencias/scripts/validate_drawio.py.
---

# Diagramador

Skill para interpretar diagramas de referencia y producir diagramas nuevos en
formato **draw.io / diagrams.net** (.drawio, XML mxGraph) que respeten un estilo
visual consistente: colores, textos, tamaños y formatos legibles. Está orientado
a **diagramas de arquitectura con componentes generales de AWS** (íconos aws4),
modelo C4, flowcharts funcionales y máquinas de estado / Step Functions.

## Objetivo

Cuando el usuario pida un diagrama, el resultado debe verse y comportarse como
los diagramas de referencia que ha enseñado, de modo que requiera **cambios
mínimos o ninguno** — y debe pasar `validate_drawio.py` sin errores.

## Cuándo este skill y cuándo el engine Python (puente)

En el repo conviven dos formas de generar diagramas. Elegí según el caso:

| Caso | Herramienta |
|------|-------------|
| **Diagrama AWS oficial del producto** que se versiona y se regenera de un spec (cambiás el spec → regenerás → diff limpio) | **Engine determinístico** en `context/<producto>/diagrams/` (`aws_drawio.py` + `build_<producto>.py`). Editás el `build_*.py`, nunca el XML. |
| **Todo lo demás**: C4, flowchart, Step Function, tablas, bases de datos, diagrama ad-hoc, **interpretar/reproducir** una imagen o `.drawio`, o **aprender estilo** de una referencia | **Este skill** — XML mxGraph guiado por `estilo-base.md` + `snippets.md`. |

Regla práctica: si el diagrama debe ser **reproducible desde código** → engine.
Si es **exploratorio, variado o único** → diagramador. Los dos comparten la misma
paleta AWS (colores por categoría), así que el resultado se ve consistente.
El engine es además la referencia de catálogo `aws4`: si dudás del `resIcon` de
un servicio, mirá su tabla `ICONS` en `aws_drawio.py`.

## Herramientas del skill

- `referencias/estilo-base.md` — **fuente de verdad del estilo**. Leer SIEMPRE primero.
- `referencias/snippets.md` — bloques XML copy-paste por tipo de diagrama. **Partir de acá**, no del XML en blanco.
- `referencias/iconos/` + `_uris.json` — librería de íconos de BD/EKS (data-URIs PNG listas).
- `referencias/scripts/add_icon.py` — agrega/regenera íconos con el data-URI en el formato que draw.io sí renderiza.
- `referencias/scripts/validate_drawio.py` — QA del `.drawio` generado (well-formed + legibilidad).
- `referencias/ejemplos/` — diagramas que el usuario enseña; refinan el estilo.

## Flujo de trabajo

### 1. Cuando el usuario ENVÍA un diagrama de referencia

El usuario puede compartir un diagrama de dos formas:

- **Como imagen** (PNG/JPG pegada o arrastrada al chat): obsérvala con máximo
  detalle. Identifica colores (intenta estimar el código hex), tipografías,
  tamaños relativos de cajas y texto, grosor y estilo de líneas/flechas,
  iconos, agrupaciones, leyendas y la lógica de la arquitectura.
- **Como archivo `.drawio`** (ruta a un archivo): léelo con la herramienta Read.
  Es la fuente más fiel porque trae los valores exactos (hex, geometría,
  fuentes, estilos). Guarda una copia en `referencias/ejemplos/`.

Tras estudiar un diagrama de referencia:
1. Resume al usuario qué características detectaste (colores, tamaños, patrón
   de arquitectura, convenciones).
2. **Actualiza `referencias/estilo-base.md`** con las reglas extraídas, sin
   duplicar reglas ya existentes. Si una nueva referencia contradice una regla
   previa, pregúntale al usuario cuál prevalece.
3. Conserva el ejemplo en `referencias/ejemplos/` con un nombre descriptivo y
   regístralo en el inventario (§8 de `estilo-base.md`).

### 2. Cuando el usuario PIDE un diagrama nuevo

1. Lee **`referencias/estilo-base.md`** — es el punto de partida del estilo.
2. ¿Es el **diagrama AWS oficial reproducible** del producto? → usá el engine
   (ver *puente* arriba) y salí de este flujo. Si no, seguí.
3. **Partí de un snippet** de `referencias/snippets.md` (esqueleto base + el tipo
   que toque). No armes el XML desde cero.
4. Si hay ejemplos similares en `referencias/ejemplos/`, úsalos como plantilla.
5. Para bases de datos y EKS, usá la **librería de íconos** (`_uris.json`) —
   ver §1.1c de `estilo-base.md`. Para un motor nuevo: `add_icon.py` (§ abajo).
6. Genera el archivo `.drawio` aplicando el estilo base.
7. **Validá**: `python3 referencias/scripts/validate_drawio.py <archivo>.drawio`.
   Corregí todo error y revisá los avisos (ver *Validación y QA*).
8. Entregá la ruta del archivo y un resumen de las decisiones de estilo.

## Validación y QA

Antes de dar un diagrama por terminado, corré el validador:

```
python3 referencias/scripts/validate_drawio.py ruta/al/diagrama.drawio
```

- **Errores** (exit 1, hay que corregir): XML mal formado · data-URI de imagen en
  formato roto (`;base64,` o `image/svg` — draw.io no lo renderiza).
- **Avisos** (revisar): `fontSize<7`, texto que desborda su caja, vértices que se
  solapan >50%, páginas con modelo comprimido.

Checklist manual que el script no cubre: contraste suficiente, flechas que no se
cruzan innecesariamente, espaciado uniforme, flujo legible (izq→der o arr→ab).

## Mantener la librería de íconos

La data-URI que draw.io necesita es `data:image/png,<base64>` — **con coma y SIN
`;base64`**. El formato `data:image/png;base64,…` se rompe porque draw.io separa
los estilos por `;`. No la armes a mano: usá el script.

```
# Agregar/actualizar un motor (acepta PNG o SVG; el SVG se rasteriza):
python3 referencias/scripts/add_icon.py clickhouse ruta/al/logo.svg

# Verificar que todas las URIs estén en el formato correcto:
python3 referencias/scripts/add_icon.py --check

# Regenerar _uris.json desde los PNG presentes en iconos/:
python3 referencias/scripts/add_icon.py --rebuild
```

## Notas sobre el formato draw.io

- Un `.drawio` es `<mxfile>` con uno o más `<diagram>` (páginas), cada uno con un
  `<mxGraphModel><root>…`. **Multipágina**: una página por nivel C4
  (Contexto → Contenedor → Componentes → Infra). Ver esqueleto en `snippets.md §0`.
- Estilos por celda van en el atributo `style` (ej:
  `rounded=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontSize=12;`).
- Geometría (posición y tamaño) en `<mxGeometry x y width height>`; en celdas hijas
  es **relativa** al `parent`.
- Guardá el `.drawio` **sin comprimir** (XML plano), si no el validador no puede
  auditar el contenido y los diffs en git son inútiles.
- El archivo abre directo en app.diagrams.net o en la extensión de draw.io para VSCode.
