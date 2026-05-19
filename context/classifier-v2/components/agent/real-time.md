# Real-time / Filewatcher — Agente v3

> Módulo 6 de 7 · [← Tagging](tagging.md) · [→ Sistema / KEM](sistema-kem.md)

## Responsabilidad

Detectar cambios en archivos **en caliente** (creación, modificación, borrado)
y enviarlos inmediatamente a la **cola de alta prioridad** del módulo
[Processing](processing.md). Es el camino "rápido" que complementa el recorrido
cíclico del [Scanner](scanner.md).

## Flujo

```
  Evento del FS (create/modify/delete)
            │
            ▼
  ┌──────────────────────────────────┐
  │ Filewatcher                      │
  │ Filtrado por formatos permitidos │
  └──────────────┬───────────────────┘
                 ▼
  ┌──────────────────────────────────┐
  │ Debounce                         │
  │ Evita que un evento se encole    │
  │ múltiples veces                  │
  └──────────────┬───────────────────┘
                 ▼
  ┌──────────────────────────────────┐
  │ Cola high de processing          │
  │ Procesamiento inmediato          │
  └──────────────┬───────────────────┘
                 │
                 ▼
       loop back a "Extracción por chunks"
       (entra directo a processing, no al scanner)
```

> **Destino del loop:** el evento reingresa al pipeline de Processing en el
> paso de **Extracción por chunks**, no por el inicio del Scanner. Esto evita
> reconstruir el árbol completo solo porque un archivo cambió.

## Cambios vs. agente actual (3)

### 1. Filtrado por formatos permitidos `[Modificar]`

El Filewatcher monitorea **solo formatos de archivo permitidos** para los
eventos:

- `creation`
- `modification`
- `deletion`

Estrategia adicional sugerida en el pizarrón:
- **POC de validación de recurso** para ver si el filewatcher puede cubrir el árbol completo.
- Si no es viable, **configurar el filewatcher sólo en las carpetas más importantes del árbol de priorización** (las "Joyas de la corona" recibidas del backend — ver [scanner.md](scanner.md)).

### 2. Debounce para evitar duplicidad `[Modificar]`

Implementar **debounce** en los eventos del filewatcher para evitar que un
mismo evento se encole múltiples veces.

> Típico en editores que hacen "save temporal → rename" generando múltiples eventos por un solo save.

`[TBD - imagen pendiente]` ventana de debounce (¿100ms? ¿500ms? ¿1s?).

### 3. Envío a cola high del processing `[Modificar]`

Los eventos del filewatcher deben enrutarse a la **cola de alta prioridad**
del módulo Processing, **directo al paso de Extracción por chunks**, para
garantizar procesamiento inmediato (vs. la cola normal que alimenta el
Scanner).

> Cola high definida en [processing.md](processing.md#colas).
>
> El loop no pasa por Scanner (construcción del árbol) — solo revisita el
> pipeline de Processing desde la extracción.

## Input

- Eventos del sistema de archivos del OS:
  - Windows: `ReadDirectoryChangesW` / ETW
  - macOS: `FSEvents`
  - Linux: `inotify`
- Configuración:
  - Lista de formatos permitidos
  - Raíces a monitorear (o subset si aplica estrategia de "solo carpetas prioritarias")

## Output

- **Hacia Processing (cola high):** eventos de archivo con su metadata mínima (path, tipo de evento).

## Interacción con otros módulos

- **Scanner**: Filewatcher cubre cambios **en caliente**; Scanner cubre el recorrido completo/cíclico.
- **Tagging**: el propio agente escribe metadatos en [tagging.md](tagging.md). El Filewatcher **no debe disparar** un evento de processing por un self-write → filtro de self-writes (ver TBD en Tagging).

## TBDs / preguntas abiertas

- **Ventana de debounce** (#2) — valor default.
- **Resolución del POC**: ¿se monitorea todo el árbol, o solo carpetas prioritarias? — decisión abierta.
- **Lista de formatos permitidos** — pendiente (pestaña **Parametrizaciones**).
- **Self-writes del agente**: filtro para ignorar los cambios de metadatos que produce el módulo Tagging.
- **Renombrados / movimientos**: ¿se tratan como create+delete o como un evento dedicado?
- **Borrado**: ¿qué hace el agente con un archivo eliminado ya clasificado? (cleanup en BDD local, notificar al back).
