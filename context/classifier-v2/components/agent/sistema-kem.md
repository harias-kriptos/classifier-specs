# Sistema / KEM / Infraestructura — Agente v3

> Módulo 7 de 7 · [← Real-time](real-time.md) · [Índice](README.md)

## Responsabilidad

Cambios transversales que no caen en un solo módulo de pipeline: esquema de
DynamoDB, UX del System Tray, integración con KEM, seguridad de LLMs y firma
del binario.

## Cambios (5)

### 1. DynamoDB — campo nuevo `id_grupo` `[Nuevo]`

Los análisis nuevos **ya no tendrán el estado de análisis clásico**. Se agrega
el campo `id_grupo` en DynamoDB.

- **Frontend** leerá la **sensibilidad desde la tabla de grupos** (no desde el análisis individual).
- Implicación: la UI depende de la disponibilidad/sincronización de la tabla de grupos.

> Este cambio afecta a la tabla `kr-dat-ana-{enterprise_id}-dydb` (ver [../../context/master-doc.md](../../../context/master-doc.md)) y al contrato hacia Web Platform.

`[TBD - imagen pendiente]` spec exacta del campo (tipo, índice, backfill para análisis existentes) — pestaña **Plataforma web** / **Definiciones**.

### 2. Notificación de desactivación en System Tray `[Nuevo]`

Notificación **visible en el system tray** cuando el agente es desactivado.

- UX: el usuario de la estación debe poder ver que el agente está inactivo.
- Complementa la señal de desactivación enviada por el KEM (cambio #3).

`[TBD - imagen pendiente]` copy, icono y acción al click.

### 3. Servicio del KEM — señal de desinstalación `[Nuevo]`

El KEM debe **enviar la señal de desinstalación por medio del endpoint de auth**
cuando el agente es removido.

- **Quién notifica:** KEM (backend).
- **Canal:** endpoint de auth.
- **Detona:** limpieza de estación, invalidación de caché Redis, etc.

> Relación con [../lambdas/classifier-station.md](../lambdas/classifier-station.md) y la invalidación de caché KEM existente.

### 4. Capa de seguridad contra prompt injection `[Nuevo]`

Implementar una **capa de seguridad en el backend** para los LLMs que proteja
contra ataques de **prompt injection** en el contexto del análisis de
documentos.

- **Dónde:** backend (no en el agente).
- **Motivación:** el agente envía samples con contenido de archivos del cliente al backend → pueden contener texto diseñado para inyectar instrucciones al LLM.
- **Relación con L0-Engine:** el **C4 Injection Scanner** del L0-Engine (ver [../../context/master-doc.md](../../../context/master-doc.md)) ya detecta 237 patrones regex / 25 técnicas / 12 idiomas. Este cambio muy probablemente **integra C4 como middleware** antes de invocar Bedrock.

`[TBD - imagen pendiente]` arquitectura concreta (¿C4 como Lambda layer? ¿Validación previa al LLM Execution Service?).

### 5. Validar firma del binario contra modificaciones `[Nuevo]`

Implementar **validación de firma del binario del agente** para detectar
modificaciones no autorizadas.

Extras mencionados en el mismo cambio:
- **CLI help** requerido.
- **Obsolescencia de logs** también requerida.

> Defensa contra agente alterado (reverse engineering, tampering) — refuerza los supuestos de confianza del backend, que actualmente dependen solo de HTTPS + API key (ver [../../context/master-doc.md](../../../context/master-doc.md) sección 7 — "Agente Antiguo requería desencriptación RSA... el nuevo confía en HTTPS de API Gateway").

`[TBD - imagen pendiente]` mecanismo:
- ¿Authenticode (Windows)?
- ¿Notarización (macOS)?
- ¿Self-check contra hash firmado?
- ¿Validación al arranque / periódica / ambas?

## Resumen de impacto por componente

| Componente | Impacto |
|---|---|
| DynamoDB `kr-dat-ana-{enterprise_id}-dydb` | Nuevo campo `id_grupo`; frontend lee sensibilidad de tabla de grupos |
| System Tray (UI local del agente) | Notificación de desactivación |
| KEM / `classifier-station` | Señal de desinstalación via endpoint auth |
| Backend LLM Execution (us-east-2 → Bedrock us-west-2) | Capa anti prompt injection (posible C4) |
| Binario del agente | Firma + verificación + CLI help + obsolescencia de logs |

## TBDs / preguntas abiertas

- **Backfill** de `id_grupo` para análisis existentes en DynamoDB (#1).
- **Contrato** de la señal de desinstalación KEM (#3) — payload exacto.
- **Integración C4** concreta para anti prompt injection (#4).
- **Tecnología de firma** y frecuencia de verificación (#5).
- **Gobernanza de logs** — "obsolescencia de logs" (#5) implica retention policy no definida aquí.
