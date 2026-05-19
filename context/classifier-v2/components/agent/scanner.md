# Scanner — Agente v3

> Módulo 1 de 7 · [← Índice](README.md) · [→ Processing](processing.md)

## Responsabilidad

Recorrer cíclicamente el disco/volumen asignado, construir el árbol de
directorios, enviarlo al backend para recibir lista de priorización, y
escanear archivos **en dos columnas paralelas**: una por fecha descendente
(lista priorizada) y otra de full scan, hasta converger.

Salida: eventos de archivos para el módulo [Processing](processing.md).

## Flujo interno — dos columnas paralelas

El Scanner **no** ejecuta una cadena lineal. Al activarse el agente arranca
**dos caminos en paralelo** (fuente: Confluence v3):

### Columna 1 — Flujo principal (4 pasos)

1. **Construcción del árbol** — recorrido cíclico del disco.
2. **Envío optimizado del árbol al back** — payload: árbol + tamaño + fecha creación.
3. **Recepción lista priorización + config. LLM** — "Joyas de la corona" priorizadas + `config_scan` + `fecha_modif` var conf.
4. **Scan fecha desc.** — archivos más recientes primero (feature flag).

### Columna 2 — Paralelo (arranca simultáneamente con col. 1, 2 pasos)

1. **Full scan paralelo** — hasta llegar la lista de priorización.
2. **Recepción lista priorización + config. LLM** — `config_LLM` + `config_scan` (sin joyas ni `fecha_modif`).

### Convergencia

Ambas columnas alimentan la siguiente etapa:

- **Honey pods (TBD)** — detección de comportamiento anómalo. Es la capa que sigue a las dos columnas antes de pasar el control a [Processing](processing.md).

## Cambios vs. agente actual (4)

### 1. Árbol de directorios — payload ampliado `[Modificar]`

Agregar al payload del árbol enviado al back:

- `tamaño del documento`
- `fecha de creación`

Hoy solo se envía la estructura. El cambio permite:
- Mostrar tamaño en la plataforma web.
- Mejorar la priorización por el backend (entrada a "Joyas de la corona").

### 2. Scanning por fecha descendente `[Modificar]`

Escanear primero los archivos con fecha de modificación más reciente, bajando
hasta la variable de configuración `fecha_modif` (feature flag). Aplica también
al **full scan**.

> `fecha_modif` llega desde el backend como parte de `config_scan`.

### 3. Identificación de formateo de máquina `[Nuevo]`

Detectar **si la máquina fue formateada** para manejar el caso de
**archivos ya clasificados que fueron migrados de una máquina a otra** (evita
reclasificar desde cero).

> **Ojo con el nombre:** es "formateo" (el evento de formatear), no "formato" (extensión/tipo). Se trata de detectar el acto de formateo del equipo.

> `[TBD]` qué heurística/identificador se usa para el fingerprint de máquina — decisión interna del equipo de agente, no listada en las 6 definiciones oficiales del Confluence.

### 4. Honey pods — detección de comportamiento anómalo `[TBD]`

Identificar archivos señuelo para detectar accesos sospechosos.

- **Arquitectura:** pendiente de definición.
- **Criterios de detección:** pendientes.
- **Ownership:** no definido (¿agente? ¿backend? ¿ambos?).

> Ver [definiciones.md](definiciones.md) (ítem #5: Honey pods).

## Input

- Configuración local del agente: raíces a escanear, credenciales, KEM station id.
- **Desde backend (llega vía las dos columnas):**
  - Lista priorizada ("Joyas de la corona") — columna 1
  - `config_LLM` — ambas columnas
  - `config_scan` — columna 2
  - `fecha_modif` — columna 2

## Output

- **Al backend:** payload del árbol (estructura + tamaño + fecha_creación por nodo) — columna 1, paso 2.
- **Hacia Processing:** eventos de archivo a procesar, emitidos por ambas columnas (fecha desc. + full scan).

## Configuración parametrizable

| Parámetro | Origen | Uso |
|---|---|---|
| `fecha_modif` | backend (config_scan) | fecha tope para scan descendente |
| `excluded_paths` | Plataforma + KEM | carpetas a ignorar |
| `fixed_classification_paths` | Plataforma + KEM | paths con clasificación fija (no pasan por classifier) |
| `allowed_formats` | Plataforma + KEM | extensiones permitidas |
| Joyas de la corona | backend | lista de prioridad que gana siempre |

Ver lista completa en [parametrizaciones.md](parametrizaciones.md#3-scanner).

## TBDs / preguntas abiertas

- **Honey pods:** arquitectura completa (#4).
- **Fingerprint de formateo de máquina:** mecanismo exacto (#3).
- **Convergencia entre las dos columnas:** cómo se deduplica cuando ambas alcanzan el mismo archivo.
- **Ciclicidad:** el pizarrón dice "recorrido cíclico del disco"; intervalo/condiciones de re-inicio no documentadas.
