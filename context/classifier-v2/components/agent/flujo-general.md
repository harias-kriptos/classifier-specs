# Agente v3 — Flujo general de proceso

> Fuente: pizarrón "Flujo" · v3 · 14 abril 2026.
> Arquitectura completa del agente, fiel a las pizarras de diseño.

---

## Diagrama end-to-end

```
                          ┌────────────────────┐
                          │  Inicio / agente   │
                          │       activo       │
                          └──────────┬─────────┘
                                     │
                      ┌──────────────┴──────────────┐
                      │                             │
┌─────────────────────┼─────────────────────────────┼────────────────────────┐
│ SCANNER             ▼ Col 1 (4 pasos)             ▼ Col 2 (2 pasos)        │
│          ┌─────────────────────┐       ┌──────────────────────────┐        │
│          │ 1 · Construcción    │       │ 1 · Full scan paralelo   │        │
│          │     del árbol       │       │    Hasta llegar          │        │
│          │ Recorrido cíclico   │       │    priorización          │        │
│          └──────────┬──────────┘       └──────────┬───────────────┘        │
│                     │                             │                        │
│                     ▼                             ▼                        │
│          ┌─────────────────────┐       ┌──────────────────────────┐        │
│          │ 2 · Envío optimizado│       │ 2 · Recepción lista      │        │
│          │   árbol + tamaño    │       │   priorización +         │        │
│          │   + fecha creación  │       │   config.LLM + config.   │        │
│          │                     │       │   scan  (sin joyas)      │        │
│          └──────────┬──────────┘       └──────────┬───────────────┘        │
│                     │                             │                        │
│                     ▼                             │                        │
│          ┌─────────────────────┐                  │                        │
│          │ 3 · Recepción lista │                  │                        │
│          │   priorización +    │                  │                        │
│          │   config LLM +      │                  │                        │
│          │   joyas + fecha_modif│                  │                        │
│          └──────────┬──────────┘                  │                        │
│                     │                             │                        │
│                     ▼                             │                        │
│          ┌─────────────────────┐                  │                        │
│          │ 4 · Scan fecha desc.│                  │                        │
│          │   Recientes primero │                  │                        │
│          │   (feature flag)    │                  │                        │
│          └──────────┬──────────┘                  │                        │
│                     │                             │                        │
│                     └──────────────┬──────────────┘                        │
│                                    ▼                                       │
│             ┌─────────────────────────────────────────┐                    │
│             │  Honey pods (TBD)                       │                    │
│             │  detección comportamiento anómalo       │                    │
│             └──────────────┬──────────────────────────┘                    │
└────────────────────────────┼───────────────────────────────────────────────┘
                             │
┌────────────────────────────┼───────────────────────────────────────────────┐
│ PROCESSING                 ▼                                               │
│             ┌────────────────────────────────────────┐                     │
│             │  Extracción por chunks                 │                     │
│             │  Chunk fijo · no trim · sin plugin     │                     │
│             └───────┬──────────────────────┬─────────┘                     │
│                     │                      │                               │
│                     ▼                      ▼                               │
│         ┌──────────────────┐   ┌──────────────────┐                        │
│         │ Archivos pequeños│   │ Archivos grandes │                        │
│         │ Cola normal      │   │ Cola separada    │                        │
│         │                  │   │ status=big_file  │                        │
│         └────────┬─────────┘   └────────┬─────────┘                        │
│                  └──────────┬───────────┘                                  │
│                             ▼                                              │
│        ┌──────────────────────────────────────────────┐                    │
│        │  Tokenización + embeddings — no plugin       │                    │
│        │  Input: chunk, ext, nombre, tamaño,          │                    │
│        │         idioma, ML version, path             │                    │
│        │  Salida: fuzzy hash + embedding → JSON       │                    │
│        └──────────────────┬───────────────────────────┘                    │
│                           ▼                                                │
│                    ┌────────────────┐                                      │
│                    │   Classifier   │                                      │
│                    └───┬──┬──┬───────┘                                      │
│        ┌───────────────┘  │  │     (paralelo Regex · Grupos · PII)          │
│        ▼                  ▼  ▼                                              │
│   ┌────────┐        ┌────────┐ ┌─────────┐                                  │
│   │ Regex  │        │ Grupos │ │   PII   │                                  │
│   │        │        │ (heads)│ │ (Siege) │                                  │
│   └───┬────┘        └────┬───┘ └────┬────┘                                  │
│       │                  │          │                                       │
│       │                  └────┬─────┘                                       │
│       │                       ▼  (después · solo si feature flag)          │
│       │                ┌──────────────┐                                     │
│       │                │  Joyas ⚑    │                                      │
│       │                │ disabled def.│                                      │
│       │                └──────┬───────┘                                     │
│       │                       │                                             │
│   analysis_           analysis_   analysis_    analysis_                    │
│   classif.            group_id    classif.     classif.                     │
│   _name              (Grupos)     _name (PII)  _name (Joyas)                │
│        └──────────┬────────┬──────────┬─────────┘                           │
│                    ▼                                                        │
│                ┌──────────┐                                                │
│                │ Scoring  │                                                │
│                └───┬───┬──┘                                                │
│      sin clasif.  │   │  clasificado                                       │
│                   ▼   ▼                                                    │
│   ┌──────────────────┐    ┌─────────────────────────────┐                  │
│   │ Status: pending  │    │ Envío JSON al back          │                  │
│   │ Ninguna vía      │    │ Grupo + classification_name │                  │
│   └────────┬─────────┘    └──────────┬──────────────────┘                  │
│            └──────────┬──────────────┘                                     │
│                       ▼                                                    │
│  ┌─────────────────────────────────────────────────────────┐               │
│  │  Sincronización con backend                             │               │
│  │  Enviar con analysis_classification_status              │               │
│  │  Si pending → no reenviar, actualizar                   │               │
│  │              pending_sincronization                     │               │
│  │  Solo enviar cuando ya tenga grupo + clasificación      │               │
│  └─────────────────────────┬───────────────────────────────┘               │
└────────────────────────────┼───────────────────────────────────────────────┘
                             │
┌────────────────────────────┼───────────────────────────────────────────────┐
│ GROUP SAMPLE ENGINE (GSE)  ▼                                               │
│         ┌───────────────────────────────────────────┐                      │
│         │ 1 · Recibe señal del backend              │                      │
│         │     Dispara el ciclo de colecta           │                      │
│         └──────────────────┬────────────────────────┘                      │
│                            ▼                                               │
│         ┌───────────────────────────────────────────┐                      │
│         │ 2 · Colecta y envía sample al back        │                      │
│         │     Extracción + payload (chunk + path)   │                      │
│         │     ⚠  DEBE IR ANONIMIZADO                 │                      │
│         └──────────────────┬────────────────────────┘                      │
│                            ▼                                               │
│         ┌───────────────────────────────────────────┐                      │
│         │ 3 · Recibe tags de los samples            │                      │
│         │     Back devuelve etiqueta por grupo      │                      │
│         └──────────────────┬────────────────────────┘                      │
│                            ▼                                               │
│         ┌───────────────────────────────────────────┐                      │
│         │ 4 · Actualizar BDD de grupos + cache      │                      │
│         │     Persistir etiquetas localmente        │                      │
│         └──────────────────┬────────────────────────┘                      │
│                            ▼                                               │
│         ┌───────────────────────────────────────────┐                      │
│         │ 5 · Sincronizar archivos pending          │                      │
│         │     Solo los que necesiten sincronización │                      │
│         └──────────────────┬────────────────────────┘                      │
│                            ▼                                               │
│         ┌───────────────────────────────────────────┐                      │
│         │ 6 · Llama a Tagging por grupo             │                      │
│         │     Solo docs con estatus pending         │                      │
│         └──────────────────┬────────────────────────┘                      │
└────────────────────────────┼───────────────────────────────────────────────┘
                             │
┌────────────────────────────┼───────────────────────────────────────────────┐
│ TAGGING                    ▼                                               │
│        ┌──────────────────────────────────────────┐                        │
│        │  Cola de taggeo en tiempo real           │                        │
│        │  Procesa docs del grupo con status pend. │                        │
│        └─────────────────┬────────────────────────┘                        │
│                          ▼                                                 │
│        ┌──────────────────────────────────────────┐                        │
│        │  Seteo de tags en metadatos              │                        │
│        │  Sin alterar fecha mod · upd hashset dedup                        │
│        └─────────────────┬────────────────────────┘                        │
│                          ▼                                                 │
│        ┌──────────────────────────────────────────┐                        │
│        │  Señal al back · BDD grupos + cache      │                        │
│        └─────────────────┬────────────────────────┘                        │
└──────────────────────────┼─────────────────────────────────────────────────┘
                           │
┌──────────────────────────┼─────────────────────────────────────────────────┐
│ REAL-TIME                ▼                                                 │
│        ┌──────────────────┐     ┌──────────────────────┐                   │
│        │  Filewatcher     │────▶│  Debounce + cola high│─────┐             │
│        │  creación/mod/   │     │  Evita duplicidad    │     │             │
│        │  borrado         │     │  processing prio.    │     │             │
│        └──────────────────┘     └──────────────────────┘     │             │
│                                                              │             │
│                         loop back a "Extracción por chunks"  │             │
│                         ◄────────────────────────────────────┘             │
└────────────────────────────────────────────────────────────────────────────┘
                                            │
                                            ▼
                              ┌──────────────────────────┐
                              │     Ciclo continuo       │
                              └──────────────────────────┘
```

## Legend (pizarrón)

- **Scanner** — construcción de árbol, priorización de escaneo (dos columnas paralelas)
- **Processing** — extracción, tokenización, colas, classifier 4-ramas, scoring, sincronización
- **Classifier** — 4 sub-clasificadores paralelos (Regex, Grupos, PII, Joyas)
- **GSE** — Group Sample Engine (6 pasos con anonimización)
- **Tagging** — escritura de metadatos + señal al back
- **Real-time** — detección de cambios en caliente (loop de regreso a Processing)
- **Soporte / TBD** — Honey pods u otras piezas sin definición final

## Campos JSON del agente (confirmados por el pizarrón)

| Campo | Origen | Descripción |
|---|---|---|
| `analysis_group_id` | rama Grupos | Id del grupo asignado por clustering `heads` |
| `analysis_classification_name` | ramas Regex / PII / Joyas (resuelto por Scoring) | Etiqueta de clasificación |
| `analysis_classification_status` | Scoring | `pending` \| `classified` \| `big_file` |
| `pending_sincronization` | Sincronización selectiva | Se actualiza cuando un pending ya fue sincronizado |

## Estados del análisis

| Estado | Descripción |
|---|---|
| `pending` | Ninguna vía clasificó el documento → queda a la espera de GSE/Tagging |
| `classified` | Tiene grupo + clasificación, listo para sincronización selectiva |
| `big_file` | Archivo grande enrutado a cola separada |
| `sin grupo asignado` | GSE no encontró grupo local ni en servidor → validación manual |

## Canales de cola en processing

| Cola | Prioridad | Origen |
|---|---|---|
| Cola normal (small files) | Normal | Scanner |
| Cola separada (big_file) | Normal | Scanner (archivos > umbral parametrizable) |
| Cola high | Alta | Real-time / Filewatcher |

> Umbral `big_file_threshold` parametrizable. Ver [processing.md](processing.md) y [parametrizaciones.md](parametrizaciones.md).

## Requisito crítico — Anonimización GSE

El paso **2 del GSE** (envío de sample al back) exige anonimización del
contenido antes del envío. Esto NO es un "nice to have" — el pizarrón lo
marca explícitamente. Ver [gse.md](gse.md#requisito-critico--anonimizacion) y
[definiciones.md](definiciones.md).
