# Agente Multiplataforma v3 — Specs

> **Fuente de verdad:** [Confluence v3 — Flujo de proceso](https://kriptosteam.atlassian.net/wiki/spaces/AC/pages/2965078017/Flujo+de+proceso+v3)
> **Origen:** Pizarrones de diseño, documento interno Kriptos · v3 · 14 abril 2026
> **Estado:** Borrador completo — alineado con Confluence v3
> **Scope:** Cambios al agente de escritorio (Windows / FileServer / OneDrive / SharePoint / Google)

---

## Qué es esta carpeta

Specs del **nuevo agente multiplataforma v3**, reemplazo del agente legacy que
vectoriza archivos localmente. La v3 alinea el agente con la arquitectura
L0-Engine (V2) de Kriptos: procesamiento local por chunks, clustering por
grupos, tagging, y sincronización selectiva con el backend.

No incluye los "rieles" de nube (Lambdas, colas, LLM Execution Service) — esos
siguen en [../lambdas/](../lambdas/) y [../modules/](../modules/). Lo que aquí
se especifica es lo que corre **dentro del binario del agente** en la máquina
del cliente + los cambios que dispara en el backend y la plataforma web.

## Índice

### Pipeline del agente (orden de ejecución)

| # | Módulo | Spec | # cambios |
|---|---|---|---|
| 1 | **Scanner** — construcción del árbol, priorización, full scan | [scanner.md](scanner.md) | 4 |
| 2 | **Processing** — extracción por chunks, colas big/small, tokenización | [processing.md](processing.md) | 7 |
| 3 | **Classifier** — 4 ramas paralelas (Regex, Joyas, Grupos, PII) + Scoring | [classifier.md](classifier.md) | incluido en Processing #4–5 |
| 4 | **GSE** (Group Sample Engine) — muestreo por grupo + asignación local + **anonimización** | [gse.md](gse.md) | 6 pasos + 3 items |
| 5 | **Tagging** — escritura de tags en metadatos + sincronización | [tagging.md](tagging.md) | 4 |
| 6 | **Real-time / Filewatcher** — detección de cambios en caliente | [real-time.md](real-time.md) | 3 |
| 7 | **Sistema / KEM / Infraestructura** — System Tray, firma, prompt injection | [sistema-kem.md](sistema-kem.md) | 5 |

Flujo extremo a extremo: [flujo-general.md](flujo-general.md)

### Complemento

| Documento | Contenido |
|---|---|
| [plataforma-web.md](plataforma-web.md) | 9 cambios en la UI (documentos/grupos, observabilidad, config, sensibilidad) |
| [definiciones.md](definiciones.md) | **11 decisiones pendientes** — 4 críticas, 5 importantes, 2 menores |
| [parametrizaciones.md](parametrizaciones.md) | 11 parámetros del agente · todos en KEM · 9 configurables desde UI |

## Métricas del alcance

| Área | # items |
|---|---|
| Cambios en el agente (módulos 1–7) | **27 cambios** (GSE ahora 6 pasos) |
| Cambios en plataforma web | **9 cambios** |
| Decisiones de diseño pendientes | **6 definiciones** (alineadas con Confluence v3) |
| Parámetros de configuración | **11 parámetros** (alineados con Confluence v3) |
| **Total trabajo identificado** | **53 items** |

## Convenciones de estos specs

- Cada módulo lista: **Responsabilidad**, **Cambios vs. agente actual**, **Input / Output**, **Configuración parametrizable**, **TBDs**.
- Cada cambio se clasifica como `[Nuevo]`, `[Modificar]` o `[TBD]` (tal como aparece en los pizarrones).
- **No se inventan nombres de componentes.** Los nombres (`heads`, `Siege`, `id_grupo`, `pending_sincronizacion`, etc.) se transcriben literal del pizarrón.
- Las decisiones pendientes se centralizan en [definiciones.md](definiciones.md) con criticidad (🔴 crítico / 🟡 importante / 🟢 menor).

## Origen de los pizarrones

Documento interno Kriptos · **Agente Multiplataforma v3** · 14 abril 2026 · pestañas:

| Pestaña | Procesada en |
|---|---|
| **Flujo** | [flujo-general.md](flujo-general.md) |
| **Agente** (cambios por módulo) | scanner/processing/classifier/gse/tagging/real-time/sistema-kem |
| **Plataforma web** | [plataforma-web.md](plataforma-web.md) |
| **Definiciones** | [definiciones.md](definiciones.md) |
| **Parametrizaciones** | [parametrizaciones.md](parametrizaciones.md) |

## Principios de diseño transversales

1. **Todos los parámetros viven en el KEM** — nada hardcodeado en el binario.
2. **Sincronización selectiva** — solo viaja al backend lo que tiene grupo + clasificación.
3. **Procesamiento local primero** — el agente decide si enviar; la red solo para lo nuevo o sustancialmente distinto.
4. **Sensibilidad por grupo, no por documento** — el frontend lee sensibilidad de la tabla de grupos vía `id_grupo`.
5. **Sin alterar fecha de modificación** del archivo al taggear (requisito crítico para no interferir con el scanner).
6. **Samples del GSE van anonimizados** — nunca sale contenido sin lavar al backend/LLM.

## Siguientes pasos sugeridos

1. Resolver las **6 definiciones pendientes** ([definiciones.md](definiciones.md)) — tal como aparecen en Confluence v3.
2. Asignar owners a las **5 definiciones importantes**.
3. Definir **defaults** y **rangos válidos** para los 11 parámetros.
4. Consolidar contratos KEM ↔ Agente, Backend ↔ Agente (samples GSE), Frontend ↔ DynamoDB (campo `id_grupo`).
