# Skill: diagramador

Skill de Claude para **interpretar y generar diagramas de arquitectura**
en formato draw.io (diagrams.net) — AWS, C4, flowcharts, Step Functions, tablas
y bases de datos — con un estilo visual consistente.

- `SKILL.md` — definición, flujo de trabajo y puente con el engine Python del repo.
- `referencias/estilo-base.md` — guía de estilo (paletas, tipografía, conectores,
  convenciones AWS/C4/flowchart/Step Function, formato de imágenes embebidas).
- `referencias/snippets.md` — bloques XML copy-paste por tipo de diagrama.
- `referencias/iconos/` — librería de íconos de bases de datos y cómputo
  (SVG + PNG embebibles, paleta `iconos-bd.drawio`, URIs en `_uris.json`).
- `referencias/scripts/add_icon.py` — agrega/regenera íconos con el data-URI correcto.
- `referencias/scripts/validate_drawio.py` — QA del `.drawio` (well-formed + legibilidad).
- `referencias/ejemplos/` — diagramas de referencia que el usuario enseñe y que
  van definiendo/refinando el estilo (vacío por defecto).

> Para enseñarle estilo al skill, comparte un diagrama (imagen o `.drawio`); el
> skill extraerá sus reglas a `estilo-base.md` y guardará el ejemplo en
> `referencias/ejemplos/`.

> Relación con `skills/diagram-aws.md`: este skill **reemplaza** esa guía. El
> engine determinístico (`context/<producto>/diagrams/aws_drawio.py`) sigue vivo
> como el modo "diagrama AWS reproducible"; ver el puente en `SKILL.md`.
