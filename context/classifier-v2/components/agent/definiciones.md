# Definiciones pendientes — Agente v3

> Pestaña **Definiciones** · [← Índice](README.md)
>
> Decisiones de diseño, algoritmos y comportamientos que deben ser definidos
> **antes** de implementar.
>
> **Fuente de verdad:** [Confluence v3](https://kriptosteam.atlassian.net/wiki/spaces/AC/pages/2965078017/Flujo+de+proceso+v3).

---

## Lista oficial (6 ítems)

### 1 · Algoritmo de asignación a grupo (GSE)

¿Cómo decide el agente localmente a qué grupo pertenece un documento? El
Confluence menciona **Clustering (algoritmo heads)** y
**PII Classifier (algoritmo Siege)**. Debe definirse:

- Qué **features** usa.
- Cómo compara contra la **tabla local**.
- Cuál es el **umbral de confianza mínima** para asignar.

**Impacto:** [classifier.md](classifier.md#rama-2--grupos-clustering-algoritmo-heads), [gse.md](gse.md#2-tabla-gse-local--algoritmo-de-asignacion-nuevo).

---

### 2 · Estado "sin grupo asignado"

- ¿Qué **campo exacto** se usa en DynamoDB?
- ¿Qué **flujo** sigue en la plataforma web?
- ¿El operador lo puede **reasignar manualmente**?
- ¿Se **reintenta automáticamente** cuando llega una nueva versión de la tabla GSE?

**Pendiente:** definir el **ciclo de vida completo** de este estado.

**Impacto:** [gse.md](gse.md), [plataforma-web.md](plataforma-web.md#11-vista-de-documentos-en-pending-y-grupos-nuevo).

---

### 3 · Versión de ML en tokenización

- ¿Cómo se versiona el modelo? ¿String, hash, SemVer?
- ¿Cómo afecta el campo `version_ML` al **output del JSON**?
- ¿Cómo impacta la **cache de clasificación por grupo**?

**Pendiente:** definir **esquema de versionado** del modelo de ML por parte del agente.

**Impacto:** [processing.md](processing.md#3-tokenizacion-input-extendido-modificar), [parametrizaciones.md](parametrizaciones.md) (`ml_version`).

---

### 4 · Lógica de Scoring

**Escenario:** Cuando múltiples clasificadores (Regex, Grupos, PII, Joyas)
retornan resultado **simultáneamente**:

- ¿Cuál prevalece?
- ¿Hay **pesos** por clasificador?
- ¿Hay **jerarquía**?
- ¿**PII siempre gana**?

**Pendiente:** definir la **función de scoring** y los posibles empates.

**Nota:** Tres ramas escriben al mismo campo `analysis_classification_name`
(Regex, PII, Joyas). El Scoring debe resolver la colisión. La rama Grupos
escribe a `analysis_group_id` — campo distinto, no compite. Joyas corre
**después** de Grupos y PII (ver [classifier.md](classifier.md)).

**Impacto:** [classifier.md](classifier.md#scoring).

---

### 5 · Honey pods

**Arquitectura completa pendiente:**
- ¿Qué son los archivos señuelo?
- ¿Cómo se crean y gestionan?
- ¿Qué eventos disparan una alerta?
- ¿Se integran con el árbol de priorización o son una capa independiente?
- ¿Cuál es la **acción resultante** al detectar un acceso anómalo?

**Impacto:** [scanner.md](scanner.md#4-honey-pods--deteccion-de-comportamiento-anomalo-tbd).

---

### 6 · Capa de seguridad contra prompt injection

**Definir:**
- En qué **capa exacta** se implementa: ¿en el agente antes de enviar al LLM? ¿en el backend? ¿en ambas?
- Qué **técnicas** se usan: sanitización, delimitadores, instrucciones del sistema.
- Cómo se **testea**.

**Relación con L0-Engine:** existe el motor **C4 Injection Scanner** (237 patrones regex · 25 técnicas · 12 idiomas — ver [../../context/master-doc.md](../../../context/master-doc.md)). Probablemente parte de esta definición es integrarlo como middleware.

**Impacto:** [sistema-kem.md](sistema-kem.md#4-capa-de-seguridad-contra-prompt-injection-nuevo).

---

## Resumen

| # | Ítem | Área impactada |
|---|---|---|
| 1 | Algoritmo de asignación a grupo (GSE) | classifier, gse |
| 2 | Estado "sin grupo asignado" | gse, plataforma-web |
| 3 | Versión de ML en tokenización | processing, parametrizaciones |
| 4 | Lógica de Scoring | classifier |
| 5 | Honey pods | scanner |
| 6 | Capa de seguridad contra prompt injection | sistema-kem |

**Total:** 6 decisiones pendientes.

> Las 6 decisiones deben tener owner y fecha antes del kickoff de implementación. Este archivo es el tracker.
