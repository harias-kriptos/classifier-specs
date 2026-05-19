# Processing — Agente v3

> Módulo 2 de 7 · [← Scanner](scanner.md) · [→ Classifier](classifier.md)

## Responsabilidad

Transformar archivos (entregados por Scanner o Filewatcher) en un payload
estructurado listo para el [Classifier](classifier.md): extracción por chunks,
enrutamiento big/small, tokenización, fuzzy hashing y embedding.

## Flujo interno

```
Archivo ─▶ Extracción por chunks ─┬─▶ Cola normal (small)   ─┐
                                   └─▶ Cola separada (big)   ─┤
                                         status=big_file      │
                                                              ▼
                          Tokenización + embeddings (no plugin)
                          Input: chunk, ext, nombre, tamaño,
                                 idioma, versión ML, path
                          Salida: fuzzy hash + embedding → JSON
                                                              │
                                                              ▼
                                                        Classifier
                                                              │
                                                              ▼
                                                         Scoring
                                                              │
                                                    ┌─────────┴─────────┐
                                                    ▼                   ▼
                                            status=pending    Envío JSON al back
                                                              Grupo +
                                                              classification_name
```

## Cambios vs. agente actual (7)

### 1. Separación de colas big / small files `[Nuevo]`

Dos colas independientes para que los archivos grandes no bloqueen los
pequeños. Todo se maneja por **chunk**. Escalado horizontal de hilos.

- Umbral `big_file_threshold` es **parametrizable**.
- El archivo grande lleva `status: big_file` en su trazabilidad.

### 2. Extracción — chunk fijo, no trim `[Modificar]`

Chunks de tamaño fijo **sin recorte (no trim)**. Sin plugin externo.

Parámetros:
- `chunk_size_kb` — tamaño del chunk (MB/KB) — parametrizable.
- `max_chunks` — cantidad máxima de chunks por archivo — parametrizable.

### 3. Tokenización — input extendido `[Modificar]`

El tokenizador recibe un input extendido por chunk:

| Campo | Descripción |
|---|---|
| `chunk` | contenido del chunk extraído |
| `extensión` | extensión del archivo |
| `nombre` | nombre del archivo |
| `tamaño` | tamaño del archivo |
| `idioma` | idioma detectado |
| `versión de ML` | versión del modelo ML (`ml_version`) |
| `path` | ruta completa |

Sin plugin. Incluye **fuzzy hashing** y **embedding** en la misma etapa.
Salida: JSON listo para Classifier.

### 4. Classifier — 4 ramas paralelas `[Nuevo]`

Reemplaza la lógica secuencial por 4 sub-clasificadores en paralelo. Detalle
completo en [classifier.md](classifier.md):

- **Regex** → `analysis_classification_name`
- **Grupos** (clustering `heads`) → `analysis_group_id`
- **PII** (algoritmo `Siege`) → `analysis_classification_name`
- **Joyas de la corona** → `analysis_classification_name` (⚑ desactivada por default, feature flag)

Todos alimentan al **Scoring**.

### 5. Scoring — resolución de etiqueta final `[Nuevo]`

Si múltiples clasificadores responden, el Scoring decide la etiqueta.

- Si **ninguna vía clasifica** → `status: pending`.
- El JSON de salida incluye el campo `analysis_classification_status`.

Posibles valores de `analysis_classification_status`:
- `pending` — ninguna vía clasificó
- `classified` — tiene grupo + clasificación
- `big_file` — archivo grande

> Detalle en [classifier.md](classifier.md#scoring).

### 6. Sincronización selectiva al backend `[Modificar]`

Enviar al back el documento con el `analysis_classification_status`.

Reglas:
- **Si el doc está `pending`**: no reenviar; actualizar únicamente el campo `pending_sincronization`.
- **Solo enviar al back cuando el documento tenga grupo + clasificación.**
- Estado final del doc puede ser: `pending`, `classified` o `big_file`.

> ⚠️ Nombre del campo: **`pending_sincronization`** (no "sincronizacion" con "ó" ni "ción" — así aparece en el pizarrón original).

### 7. Mecanismo de memoria SWAP en colas `[Nuevo]`

Mecanismo de memoria SWAP para manejar alta carga en las colas de
procesamiento sin perder trabajos pendientes.

> `[TBD]` diseño concreto (¿persistencia en disco? ¿mmap? ¿SQLite?).

## Input

- Desde **Scanner**: eventos de archivos priorizados (desde ambas columnas del scanner — ver [scanner.md](scanner.md)).
- Desde **Real-time / Filewatcher** → **cola high** (prioridad alta, ver [real-time.md](real-time.md)).

## Output

- **Hacia Classifier:** JSON por chunk con tokenización + fuzzy hash + embedding.
- **Hacia backend (sincronización selectiva):** sólo documentos con grupo + clasificación. Incluye `analysis_group_id`, `analysis_classification_name`, `analysis_classification_status`.
- **Estado local:** archivos sin clasificación quedan con `status: pending` y actualizan `pending_sincronization`.

## Configuración parametrizable

| Parámetro | Descripción |
|---|---|
| `chunk_size_kb` | Tamaño de chunk (extracción fija, no trim) |
| `max_chunks` | Tope por archivo |
| `big_file_threshold` | Tamaño que separa cola normal / cola separada |
| `ml_version` | Versión ML incluida en el JSON del tokenizador |
| `max_threads` | Hilos para escalado horizontal |

Ver lista completa en [parametrizaciones.md](parametrizaciones.md#1-processing).

## Colas

| Cola | Prioridad | Origen |
|---|---|---|
| Normal (small files) | Normal | Scanner |
| Separada (big files) | Normal | Scanner — archivos > `big_file_threshold` |
| High | Alta | Real-time / Filewatcher |

## Campos del JSON de salida

| Campo | Origen | Escrito por |
|---|---|---|
| `analysis_group_id` | rama Grupos (Classifier) | Classifier |
| `analysis_classification_name` | Regex / PII / Joyas resuelto por Scoring | Classifier + Scoring |
| `analysis_classification_status` | `pending` \| `classified` \| `big_file` | Scoring |
| `pending_sincronization` | bandera de sincronización de pending | Sincronización selectiva |

## TBDs / preguntas abiertas

- Diseño concreto del **SWAP en colas** (#7).
- **Umbral `big_file_threshold`** — valor default.
- **Política de backpressure** cuando las 3 colas están saturadas.
- **Comportamiento en caída del proceso** — ¿se retoman los chunks a medio procesar?
