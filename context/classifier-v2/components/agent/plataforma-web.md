# Plataforma web — Cambios por Agente v3

> Pestaña **Plataforma web** · [← Índice](README.md)

## Qué abarca

Vistas, flujos y datos que deben actualizarse en la plataforma web para
soportar la arquitectura v3 del agente (grupos, sensibilidad por tabla de
grupos, parametrización remota desde el KEM).

## 1. Documentos y grupos (3 cambios)

### 1.1 Vista de documentos en pending y grupos `[Nuevo]`

Mostrar en plataforma:
- Documentos en estado `pending`.
- Grupos detectados localmente por el agente.

Debe permitir **validación manual**: asignar un grupo a los documentos que
quedaron en estado `sin grupo asignado` después del proceso del
[GSE](gse.md).

### 1.2 Visualización de clusterización y criterios `[Nuevo]`

Mostrar:
- Clusters generados.
- Criterio de cada cluster.
- Documentos asignados a cada cluster.

El frontend debe leer la **sensibilidad desde la tabla de grupos**, no del
análisis mismo (ver cambio 4.1).

### 1.3 Tamaño del documento visible `[Nuevo]`

Nueva columna/campo **tamaño** en:
- Vistas de análisis.
- Explorador de archivos.

> Insumo: tamaño que ahora viaja en el payload del árbol del Scanner (ver [scanner.md](scanner.md#1-arbol-de-directorios-payload-ampliado-modificar)).

## 2. Observabilidad y monitoreo (3 cambios)

### 2.1 Observabilidad solo para big files `[Modificar]`

La vista de observabilidad del procesamiento debe **limitarse a archivos
`big_file`**.

Agregar separación visual entre agentes para diferenciar el estado de cada
uno.

### 2.2 Ajuste de contadores `[Modificar]`

Los contadores actuales deben actualizarse para reflejar el nuevo modelo de
grupos:

- Contar documentos **por grupo**.
- Contar **por estado**: `pending`, `classified`, `big_file`.
- **Separados por agente**.

> Relación con el módulo Counters del backend V1 (ver [../../context/master-doc.md](../../../context/master-doc.md)).

### 2.3 Uso del sistema de auth para fecha de última conexión `[Nuevo]`

Usar el sistema de auth existente para actualizar y mostrar la **fecha de
última conexión** de cada agente.

> No requiere pipeline nuevo: reutiliza metadata que el auth ya tiene.

## 3. Configuración del agente (2 cambios)

### 3.1 Configuración de parametrizaciones desde la plataforma `[Nuevo]`

Permitir configurar **desde la UI** los parámetros del agente que actualmente
están hardcodeados:

- Tamaño de chunk
- Cantidad de chunks
- Tamaño del sample para GSE
- Paths excluidos
- Paths de clasificación fija

**Todos los parámetros deben almacenarse en el KEM.**

> Lista completa y categorización (Plataforma+KEM / KEM auto / KEM interno) en [parametrizaciones.md](parametrizaciones.md).

### 3.2 Movimiento de archivos clasificados entre máquinas `[Nuevo]`

Contemplar en la plataforma el caso de movimiento de archivos **ya
clasificados** de una máquina a otra, incluyendo la **identificación del
formateo de máquina**.

> Relación con [scanner.md](scanner.md#3-identificacion-de-formatos-de-maquina-nuevo) — el agente detecta el evento de formateo; la plataforma debe tener la UX para que el operador valide/confirme.

## 4. Sensibilidad y análisis (1 cambio)

### 4.1 Frontend lee sensibilidad desde tabla de grupos `[Modificar]`

**El estado del análisis ya no se mostrará de la forma clásica.**

El frontend debe buscar la sensibilidad en la **tabla de grupos** usando el
campo `id_grupo` nuevo en DynamoDB.

Documentos sin grupo asignado deben indicarse **claramente para validación
manual**.

> Relación con [sistema-kem.md](sistema-kem.md#1-dynamodb--campo-nuevo-id_grupo-nuevo).

## Resumen por área de la plataforma

| Área | # cambios | Tipo |
|---|---|---|
| Documentos y grupos | 3 | Nuevo |
| Observabilidad y monitoreo | 3 | Modificar (×2), Nuevo (×1) |
| Configuración del agente | 2 | Nuevo |
| Sensibilidad y análisis | 1 | Modificar |
| **Total** | **9 cambios** | |

## TBDs / preguntas abiertas

- **UX del validación manual** (1.1) — ¿bulk assignment? ¿drag & drop? ¿por grupo?
- **Criterios de cluster** (1.2) — qué mostrar exactamente (features, centroide, heurística de `heads`).
- **Contrato de configuración KEM → agente** (3.1) — ¿push? ¿pull? ¿qué dispara la recarga en el agente?
- **Flujo de formateo entre máquinas** (3.2) — UX específica + backend.
- **Migración de datos existentes** (4.1) — qué pasa con los análisis que no tienen `id_grupo` (mostrar estado legacy vs. ocultar).
