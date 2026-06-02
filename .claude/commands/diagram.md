Generá o actualizá un diagrama de arquitectura AWS en draw.io. Objetivo / producto: $ARGUMENTS

> Skill **utilitaria**, fuera del flujo de 5 pasos. No reemplaza ningún paso del pipeline.

Pasos:
1. Leé `skills/diagram-aws.md` y `roles/architect.md` desde classifier-specs.
2. Leé la fuente de verdad de la arquitectura en `context/<producto>/` (ecosystem, tickets, decisiones).
   El diagrama refleja eso — no inventes servicios que no estén ahí.
3. Trabajá sobre el **spec declarativo**, nunca sobre el XML:
   - Engine genérico: `context/classifier-v2/diagrams/aws_drawio.py` (catálogo aws4 + estilos).
   - Spec del producto: `context/<producto>/diagrams/build_<producto>.py`.
   - Servicio nuevo → agregá su entrada a `ICONS` en `aws_drawio.py` (`resIcon` exacto de aws4 + categoría).
4. Reglas no negociables:
   - Servicios = íconos `mxgraph.aws4.resourceIcon` con color por categoría (nunca rectángulos).
   - Estado (deployed/WIP/blocked/RFC) = badge elipse, no color de relleno.
   - Actores fuera del `aws_cloud`; IA / terceros = caja dashed gris.
   - Edges: sólido gris = síncrono · dashed rosa = evento (EventBridge / DDB Stream / S3 / SQS).
5. Generá: `python3 build_<producto>.py`. Respaldá los `.drawio` previos en `diagrams/_legacy/` antes de reemplazar.
6. Validá: XML well-formed y `mxgraph.aws4.resourceIcon` > 0 en cada archivo.

Salida: los `.drawio` regenerados en `context/<producto>/` + el spec versionado (diagrama reproducible).
