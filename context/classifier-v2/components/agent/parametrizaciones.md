# Parametrizaciones — Agente v3

> Pestaña **Parametrizaciones** · [← Índice](README.md)
>
> Todos los parámetros del agente · **almacenados en KEM** · configurables desde plataforma.

---

## 🎯 Principio de diseño

> **Todos los parámetros viven en el KEM.**
>
> Ningún parámetro del agente debe estar hardcodeado en el binario.
> El **KEM es la fuente de verdad**.
>
> - La plataforma web permite configurar los parámetros marcados como `Plataforma + KEM`.
> - Los marcados como `KEM (auto)` o `KEM (interno)` se gestionan **programáticamente**.

## Taxonomía de fuentes de configuración

| Etiqueta | Significado |
|---|---|
| `Plataforma + KEM` | Configurable por el usuario desde la UI; persistido en KEM |
| `KEM (auto)` | Gestionado automáticamente por el backend; no editable por usuario |

---

## 1. Processing

| Parámetro | Descripción | Configurado desde |
|---|---|---|
| `chunk_size_kb` | Tamaño de cada chunk en megas o KB. Define cuánto contenido se extrae por iteración. | `Plataforma + KEM` |
| `max_chunks` | Cantidad máxima de chunks a extraer por archivo. Limita el contenido total procesado. | `Plataforma + KEM` |
| `big_file_threshold` | Límite de tamaño de archivo para clasificar como `big_file` y enrutar a cola separada. Permite escalado horizontal. | `Plataforma + KEM` |
| `ml_version` | Versión del modelo de ML usada por el tokenizador. Se incluye en el JSON de output. | `KEM (auto)` |

> Relación con [processing.md](processing.md). `ml_version` esquema de versionado pendiente — ver [definiciones.md](definiciones.md) (ítem #3: Versión de ML en tokenización).

## 2. Group Sample Engine (GSE)

| Parámetro | Descripción | Configurado desde |
|---|---|---|
| `sample_content_size` | Tamaño del contenido a extraer para cada sample enviado al back durante el proceso del GSE. | `Plataforma + KEM` |
| `gse_table_version` | Versión de la tabla GSE descargada localmente. Se usa para validar si hay una versión más nueva cuando no se encuentra grupo. | `KEM (auto)` |

> Relación con [gse.md](gse.md).

## 3. Scanner

| Parámetro | Descripción | Configurado desde |
|---|---|---|
| `fecha_modif` | Fecha de corte para el scan descendente por fecha. Archivos con modificación más antigua a esta fecha se escanean primero. Feature flag. | `Plataforma + KEM` |
| `excluded_paths` | Lista de paths excluidos del scan (Program Files, carpetas del sistema, carpetas públicas). | `Plataforma + KEM` |
| `fixed_classification_paths` | Paths con clasificación fija asignada. **No pasan por el classifier**, se etiquetan directamente. | `Plataforma + KEM` |
| `allowed_formats` | Lista de extensiones de archivo permitidas para **scan y filewatcher**. | `Plataforma + KEM` |

> Relación con [scanner.md](scanner.md) y [real-time.md](real-time.md). Lista default de paths excluidos/fijos pendiente — decisión interna del equipo de agente, no listada en las 6 definiciones oficiales del Confluence.

## 4. Infraestructura

| Parámetro | Descripción | Configurado desde |
|---|---|---|
| `max_threads` | Límite de hilos para el escalado horizontal del procesamiento de archivos. | `Plataforma + KEM` |

---

## Resumen por categoría

| Fuente | # parámetros |
|---|---|
| `Plataforma + KEM` | 9 (chunk_size_kb, max_chunks, big_file_threshold, sample_content_size, fecha_modif, excluded_paths, fixed_classification_paths, allowed_formats, max_threads) |
| `KEM (auto)` | 2 (ml_version, gse_table_version) |
| **Total** | **11 parámetros** |

## Resumen por módulo destino

| Módulo | # parámetros | Parámetros |
|---|---|---|
| [Processing](processing.md) | 4 | chunk_size_kb, max_chunks, big_file_threshold, ml_version |
| [GSE](gse.md) | 2 | sample_content_size, gse_table_version |
| [Scanner](scanner.md) + [Real-time](real-time.md) | 4 | fecha_modif, excluded_paths, fixed_classification_paths, allowed_formats |
| Infraestructura transversal | 1 | max_threads |

## Implicaciones de arquitectura

1. **Contrato KEM → Agente.** El agente debe saber consultar/recibir estos 11 parámetros al arrancar y ante cambios.
2. **Hot reload.** `fecha_modif` es feature flag → requiere aplicación en caliente sin reiniciar el agente.
3. **Validación.** El KEM debe validar rangos (ej. `max_chunks > 0`, `big_file_threshold > chunk_size_kb * max_chunks`).
4. **Versionado.** `ml_version` y `gse_table_version` están acoplados al ciclo de vida de modelos y tablas en backend — no los maneja el usuario.
5. **UI.** La plataforma web (pestaña Configuración del agente, ver [plataforma-web.md](plataforma-web.md#31-configuracion-de-parametrizaciones-desde-la-plataforma-nuevo)) expone 9 de los 11.

## TBDs

- **Defaults** de cada parámetro — el pizarrón no los lista.
- **Tipos y rangos válidos** — inferibles por nombre pero sin especificar.
- **Mecanismo de distribución** KEM → agente (push via EventBridge? pull periódico?).
- **Rollback** ante configuración inválida aplicada por error.
- **Auditoría** de cambios de parámetros (quién cambió qué, cuándo).
