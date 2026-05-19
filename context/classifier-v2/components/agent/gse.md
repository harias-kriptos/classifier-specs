# GSE — Group Sample Engine — Agente v3

> Módulo 4 de 7 · [← Classifier](classifier.md) · [→ Tagging](tagging.md)

## Responsabilidad

Resolver la clasificación de los documentos que quedaron `pending` (sin
etiqueta después del Classifier) mediante **muestreo por grupo**: por cada
grupo formado localmente, envía una muestra **anonimizada** representativa al
backend, recibe la etiqueta, y la propaga a todos los documentos del grupo.

Pieza **nueva** respecto al agente actual.

## Flujo del GSE — 6 pasos

```
   Señal backend
        │
        ▼
  ┌─────────────────────────────────────────────────┐
  │ 1 · Recibe señal del backend                    │
  │     Dispara el ciclo de colecta del GSE         │
  └────────────────────┬────────────────────────────┘
                       ▼
  ┌─────────────────────────────────────────────────┐
  │ 2 · Colecta y envía sample al back              │
  │     Extracción + envío de payloads              │
  │     (chunk + path por grupo)                    │
  │                                                 │
  │     ⚠  EL SAMPLE DEBE IR ANONIMIZADO             │
  │        antes de enviarse al back                │
  └────────────────────┬────────────────────────────┘
                       ▼
  ┌─────────────────────────────────────────────────┐
  │ 3 · Recibe tags de los samples                  │
  │     Back devuelve la etiqueta para cada grupo   │
  └────────────────────┬────────────────────────────┘
                       ▼
  ┌─────────────────────────────────────────────────┐
  │ 4 · Actualiza BDD de grupos y cache             │
  │     Persiste etiquetas recibidas localmente     │
  └────────────────────┬────────────────────────────┘
                       ▼
  ┌─────────────────────────────────────────────────┐
  │ 5 · Sincroniza archivos pending                 │
  │     Solo los que necesiten ser sincronizados    │
  │     (archivos modificados que no se han enviado)│
  └────────────────────┬────────────────────────────┘
                       ▼
  ┌─────────────────────────────────────────────────┐
  │ 6 · Llama a Tagging por grupo                   │
  │     Pone la etiqueta a cada doc del grupo       │
  │     Solo docs con estatus pending               │
  └─────────────────────────────────────────────────┘
```

## Requisito crítico — Anonimización

**El sample debe ir ANONIMIZADO antes de enviarse al back.**

Esto aplica al payload del paso 2 (chunk + path por grupo). Es un requisito
explícito del pizarrón y tiene implicaciones directas en:

- El **agente**: debe implementar la capa de anonimización antes del envío.
- El **backend**: la capa anti prompt injection (cambio #4 en [sistema-kem.md](sistema-kem.md#4-capa-de-seguridad-contra-prompt-injection-nuevo)) opera sobre contenido ya anonimizado — pero no depende de eso.
- El **LLM en Bedrock**: recibe texto sanitizado → menor superficie de riesgo, pero menor riqueza semántica.

> ⚠️ Detalle técnico pendiente: ¿qué tipo de anonimización? ¿Reemplazo de PII detectado localmente por placeholders (`[NAME]`, `[EMAIL]`, `[CREDIT_CARD]`)? ¿Hashing? ¿Redacción total? No está en las 6 definiciones oficiales del Confluence v3 — se decide en implementación del agente.

## Cambios vs. agente actual (4 nuevos)

### 1. Flujo completo del GSE — 6 pasos `[Nuevo]`

Ciclo descrito arriba. Los pasos 4, 5 y 6 consolidan lo que antes era
"items separados":

| # | Paso | Notas |
|---|---|---|
| 1 | Recibe señal del backend | Trigger del ciclo |
| 2 | Colecta + envía sample **anonimizado** | Payload: chunk + path por grupo |
| 3 | Recibe tags del back | Etiqueta por grupo |
| 4 | Actualiza BDD grupos + cache | Persistencia local |
| 5 | Sincroniza archivos pending | Solo los que lo necesiten |
| 6 | Llama a Tagging por grupo | Solo docs con `pending` |

### 2. Tabla GSE local + algoritmo de asignación `[Nuevo]`

El agente **descarga la tabla del módulo GSE** y busca localmente el grupo al
que debe asignar cada documento.

Lógica de decisión:

```
lookup_local(doc) ──┬── hit         → asigna grupo
                    │
                    └── miss        → verifica nueva versión en módulo GSE (backend)
                                       ├── hay versión nueva → actualiza tabla → reintenta
                                       └── no hay             → status: "sin grupo asignado"
                                                                (validación manual en plataforma)
```

### 3. Sincronización de archivos pending `[Nuevo]`

Paso **5** del flujo. Sincroniza archivos en estado `pending` que necesiten
ser sincronizados (típicamente archivos modificados que por eso no se habían
enviado).

> Relación con el campo `pending_sincronization` introducido en Processing (cambio #6 de [processing.md](processing.md)).

### 4. Actualización de BDD de grupos y cache `[Nuevo]`

Paso **4** del flujo. Persiste las etiquetas recibidas del back en la base de
datos local de grupos + su caché.

## Input

- **Señal de arranque** desde backend (trigger del ciclo).
- **Documentos locales** con:
  - `status: pending` (sin clasificación del Classifier)
  - documentos con `analysis_group_id` ya asignado por la rama **Grupos** del Classifier
- **Tabla GSE** descargada desde el módulo GSE del backend (con versión).

## Output

- **Hacia backend:** samples **anonimizados** por grupo (chunk + path).
- **Hacia Tagging (paso 6):** documentos pending con su etiqueta respectiva, por grupo.
- **Estado local:** actualización de BDD local de grupos + caché.
- **Estado especial:** `sin grupo asignado` para docs que no pudieron ser resueltos (quedan para validación manual en plataforma web).

## Persistencia local

| Estructura | Propósito |
|---|---|
| Tabla GSE local | Lookup `doc → grupo` (descargada del backend, versionada) |
| BDD de grupos | Estado local de grupos y sus etiquetas |
| Caché de grupos | Acceso rápido en el hot path |

`[TBD - imagen pendiente]` tecnología de persistencia (SQLite / archivos / mmap) — posiblemente en pestaña **Definiciones**.

## TBDs / preguntas abiertas

- **🔴 Anonimización del sample** — qué técnica exacta (placeholders, hashing, redacción), qué fidelidad semántica queda. Ver [definiciones.md](definiciones.md).
- **Frecuencia / trigger** de la señal desde el backend (¿cron? ¿volumen umbral? ¿manual?).
- **Formato de la tabla GSE** y estrategia de versionado (`gse_table_version` ya está como parámetro).
- **Tamaño de sample** por grupo — parámetro `sample_content_size` definido en [parametrizaciones.md](parametrizaciones.md).
- **Propagación:** se identifica "doc pending del mismo grupo" vía lookup por `analysis_group_id` en BDD local.
- **Conflictos:** qué pasa si el grupo recibe etiquetas distintas entre ciclos.
- **Estado `sin grupo asignado`** — UX de validación manual en plataforma web (ver [plataforma-web.md](plataforma-web.md#11-vista-de-documentos-en-pending-y-grupos-nuevo)).
