# Classifier — Agente v3

> Módulo 3 de 7 · [← Processing](processing.md) · [→ GSE](gse.md)
>
> ⚠️ **El "Classifier" de este archivo es el classifier LOCAL del agente**
> (las 4 ramas que corren dentro del binario). No confundir con el clasificador
> de nube de este proyecto, cuyas specs viven en [../lambdas/](../lambdas/).

## Responsabilidad

Recibir el JSON tokenizado/embedding de [Processing](processing.md) y pasarlo
por los sub-clasificadores. **Regex, Grupos y PII corren en paralelo. Joyas
corre después de Grupos y PII porque contempla el contenido ya procesado.**
El **Scoring** consolida los resultados y decide la etiqueta final.

## Diagrama

```
                ┌────────────────────┐
                │   JSON de entrada  │
                │   (chunk + feats)  │
                └──────────┬─────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │          (paralelo)
              ▼            ▼            ▼
        ┌─────────┐  ┌──────────┐  ┌─────────┐
        │  Regex  │  │  Grupos  │  │   PII   │
        │         │  │ (heads)  │  │ (Siege) │
        └────┬────┘  └────┬─────┘  └────┬────┘
             │            │             │
             │            └──────┬──────┘
             │                   │
             │                   ▼  (solo si feature flag activo)
             │            ┌──────────────┐
             │            │   Joyas ⚑    │
             │            │ disabled por │
             │            │  default     │
             │            └──────┬───────┘
             │                   │
         analysis_          analysis_       analysis_       analysis_
         classif.           group_id        classif.        classif.
          _name           (desde Grupos)     _name           _name
                                              (PII)          (Joyas)
             └─────────┬───────────┬───────────┬─────────────┘
                       ▼
                ┌──────────────┐
                │   Scoring    │
                └───┬──────┬───┘
         ninguna    │      │   alguna
          clasif.   ▼      ▼   clasif.
            ┌──────────────┐
            │status=pending│      JSON al back
            └──────────────┘      Grupo + classification_name
```

> **Nota de ordering:** el pizarrón "oficial" (Confluence v3) aclara que **Joyas corre después de Grupos y PII** porque su lógica necesita acceso al contenido que esas ramas ya procesaron. Regex sí es estrictamente paralelo a los otros.

## Outputs por rama

Cada rama del classifier contribuye a un **campo específico** del JSON:

| Rama | Campo de salida |
|---|---|
| Regex | `analysis_classification_name` |
| Grupos (clustering, algoritmo `heads`) | `analysis_group_id` |
| PII (algoritmo `Siege`) | `analysis_classification_name` |
| Joyas de la corona | `analysis_classification_name` |

Las 3 ramas que escriben en `analysis_classification_name` compiten entre sí —
es ahí donde el **Scoring** debe resolver (ver más abajo).

## Las 4 ramas

### Rama 1 — Regex

Clasificación determinística por patrones regex.

- **Output:** `analysis_classification_name`.
- **Uso típico:** identificación rápida por contenido estructurado.
- `[TBD]` qué patrones trae el agente vs. cuáles llegan desde backend (`config_LLM`).

### Rama 2 — Grupos (clustering, algoritmo **heads**)

Clustering local para agrupar documentos similares.

- **Output:** `analysis_group_id`.
- **Algoritmo:** `heads` (nombre tal cual aparece en el pizarrón).
- **Propósito:** producir el **grupo** del documento, base para el [GSE](gse.md).
- `[TBD]` definición del algoritmo heads — ver [definiciones.md](definiciones.md) (ítem #1: Algoritmo de asignación a grupo).

### Rama 3 — PII (algoritmo **Siege**)

Detección de información personal identificable.

- **Output:** `analysis_classification_name`.
- **Algoritmo:** `Siege`.
- `[TBD]` definición de Siege y categorías PII soportadas.

### Rama 4 — Joyas de la corona — **⚑ desactivada por default · corre después**

Clasificador que aplica reglas sobre la lista priorizada recibida por Scanner.

- **Output:** `analysis_classification_name`.
- **Estado:** *"Desactivado por default. Activa via feature flag con config. para identificarlas. **Corre después de Grupos y PII porque contempla el contenido.**"* (texto literal del Confluence v3)
- **Input externo:** lista "Joyas de la corona" entregada por backend.
- **Dependencia temporal:** se ejecuta después de Grupos y PII — no es estrictamente paralela a ellos.
- Cuando está activa y un archivo pertenece a la lista priorizada → etiqueta inmediata.

> La rama **se habilita via feature flag** cuando el cliente tiene configurada la lista de joyas.

## Scoring

Consolida los resultados de las 4 ramas y produce una **etiqueta final** +
`analysis_classification_status`.

Reglas conocidas (según pizarrón):

| Escenario | Resultado |
|---|---|
| Ninguna rama clasifica | `analysis_classification_status = pending` · no se envía al back |
| Una o más ramas responden | Scoring decide etiqueta final → JSON al back |

Campos emitidos en el JSON final:

- `analysis_group_id` (rama Grupos)
- `analysis_classification_name` (resultante del Scoring entre Regex, PII, Joyas)
- `analysis_classification_status` (`pending` | `classified` | `big_file`)

`[TBD]` política de prioridad/tie-break entre las 3 ramas que escriben
`analysis_classification_name` (Regex, PII, Joyas). Ver
[definiciones.md](definiciones.md) (ítem #4: Lógica de Scoring).

## Input

- JSON de [Processing](processing.md): `chunk`, `extensión`, `nombre`, `tamaño`, `idioma`, `versión ML`, `path`, `fuzzy hash`, `embedding`.
- Configuración: `config_LLM` entregada por Scanner desde backend.
- **Feature flag:** Joyas activa/inactiva.

## Output

- **Hacia sincronización selectiva:** JSON con `analysis_group_id` + `analysis_classification_name` (sólo si hubo clasificación).
- **Hacia estado local:** `analysis_classification_status = pending` si ninguna rama respondió.
- **Hacia GSE:** los documentos `pending` quedan disponibles para resolución por grupo (ver [gse.md](gse.md)).

## TBDs / preguntas abiertas

- **🔴 Lógica de Scoring** cuando Regex, PII y Joyas responden distinto sobre `analysis_classification_name`.
- Detalles del algoritmo **heads** (Grupos).
- Detalles del algoritmo **Siege** (PII).
- Patrones/diccionarios de **Regex** — ¿vienen con el binario o bajan del backend?
- **Trigger** para habilitar la rama Joyas (feature flag por cliente vs. global).
- Rendimiento — 4 ramas paralelas por chunk implica presupuesto de CPU por documento aún no definido.
