# Tagging — Agente v3

> Módulo 5 de 7 · [← GSE](gse.md) · [→ Real-time](real-time.md)

## Responsabilidad

Aplicar etiquetas (tags) en los metadatos de los archivos ya resueltos por
[GSE](gse.md), manteniendo la fecha de modificación intacta y sincronizando
el estado con el backend.

## Flujo interno

```
  GSE envía docs pending+etiqueta
            │
            ▼
  ┌──────────────────────────────────┐
  │ Cola de taggeo en tiempo real    │
  │ Procesa docs con status pending  │
  │ del grupo recibido               │
  └──────────────┬───────────────────┘
                 ▼
  ┌──────────────────────────────────┐
  │ Seteo de tags en metadatos       │
  │ Sin alterar fecha modificación   │
  │ Actualiza hashset deduplicación  │
  └──────────────┬───────────────────┘
                 ▼
  ┌──────────────────────────────────┐
  │ Señal al back                    │
  │ Actualiza BDD grupos + cache     │
  │ Sincroniza pending               │
  └──────────────────────────────────┘
```

## Cambios vs. agente actual (4)

### 1. Cola de taggeo en tiempo real `[Modificar]`

La cola de taggeo debe procesarse **en tiempo real** (no por lotes diferidos).

- **Criterio de elegibilidad:** solo se etiquetan documentos con `status: pending` del grupo recibido.
- No toca documentos ya clasificados.

### 2. Seteo de tags sin alterar fecha de modificación `[Modificar]`

Escribir los tags en los metadatos del archivo **sin modificar la fecha de
modificación** del archivo.

> Requisito **crítico** para no interferir con el flujo de Scanner (que se apoya en fecha de modificación para priorizar — ver `fecha_modif` en [scanner.md](scanner.md)).

`[TBD - imagen pendiente]` mecanismo técnico por OS:
- Windows: `SetFileTime` con preservación de `LastWriteTime`.
- macOS/Linux: `utime`/`utimensat` pre- y post-escritura.
- Detalle esperado en pestaña **Agente** / **Definiciones**.

### 3. Actualización de hashset de deduplicación `[Modificar]`

Actualizar el hashset de deduplicación **después** de cada taggeo, para
mantener consistencia en la detección de duplicados.

> El hashset se alimenta del fuzzy hash calculado en [processing.md](processing.md#3-tokenizacion-input-extendido-modificar).

### 4. Envío de señal de taggeo al backend `[Modificar]`

Notificar al backend que el taggeo fue completado para que actualice:

- La **BDD de grupos**
- Su **caché**

Esto cierra el ciclo iniciado por el GSE.

## Input

- **Desde GSE:** lista de docs pending por grupo con su etiqueta respectiva.

## Output

- **Al sistema de archivos local:** metadatos de cada archivo actualizados con su tag, sin tocar fecha de modificación.
- **Al hashset local:** entrada añadida/actualizada para deduplicación.
- **Al backend:** señal de taggeo completado → triggerea refresh de BDD de grupos + caché en backend.

## Invariantes

1. **Fecha de modificación del archivo no cambia** — requisito crítico (cambio #2).
2. **Solo documentos `pending` son tagueados** (cambio #1).
3. **Hashset se actualiza post-taggeo** (cambio #3).
4. **Señal al backend se emite al final del ciclo** (cambio #4).

## TBDs / preguntas abiertas

- **Dónde se escriben los tags físicamente:**
  - ¿Extended attributes / xattrs?
  - ¿Alternate Data Streams (Windows)?
  - ¿Archivo sidecar?
  - ¿Solo BDD local del agente (no tocar el archivo)?
- **Comportamiento en archivos read-only o en FS remotos** (SharePoint, OneDrive, Google).
- **Rollback**: si la señal al backend falla, ¿se reintenta? ¿se encola?
- **Contención con Filewatcher**: el propio agente escribiendo metadatos no debe disparar un evento del Filewatcher (ver [real-time.md](real-time.md)) — requiere filtro de self-writes.
