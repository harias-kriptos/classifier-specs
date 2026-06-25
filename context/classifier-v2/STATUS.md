# Estado Actual — Backend Classifier v2

> **Última actualización:** 2026-06-02 (reorganización en 3 épicas + modelo infra-en-entregable)
> **Source of truth** del estado del backend. Reemplaza la versión anterior (que usaba numeración de tickets ficticia).
> **Stack:** Python 3.11 · Lambda Container (ECR) · CloudFormation · pytest/ruff/mypy · uv.

---

## 1. Modelo: 3 épicas de backend (+ 1 futura)

Cada módulo = **una épica + un monorepo**. La infraestructura de cada lambda va **dentro de su ticket de implementación** (no hay tickets DevOps de infra suelta).

| # | Épica | Jira | Monorepo | Estado |
|---|---|---|---|---|
| 1 | **Discovery** (scan → match → candidatos) | [KT-16369](https://kriptosteam.atlassian.net/browse/KT-16369) | `classifier-v2-backend` ([KT-17132](https://kriptosteam.atlassian.net/browse/KT-17132) ✅) | In Progress |
| 2 | **Máquina de Estados** (ciclos/estaciones) | [KT-17270](https://kriptosteam.atlassian.net/browse/KT-17270) | `classifier-state-backend` ([KT-17271](https://kriptosteam.atlassian.net/browse/KT-17271)) | RFC |
| 3 | **GSE** (sample collection) | [KT-16370](https://kriptosteam.atlassian.net/browse/KT-16370) | `classifier-gse-backend` ([KT-17134](https://kriptosteam.atlassian.net/browse/KT-17134)) | RFC |
| 4 | **Validación** (humana, client-facing) | _futura — BE 07_ | TBD | No creada |

---

## 2. Diagrama end-to-end

```mermaid
flowchart TB
  subgraph DISC["🔍 Discovery · KT-16369 · classifier-v2-backend"]
    direction LR
    A1[tree-url-generator<br/>KT-16612 ✅] --> A2[tree-uncompressor<br/>KT-16613 ✅] --> A3[emr-job-trigger<br/>KT-16614 ✅] --> A4[joyas-priorizer<br/>KT-16616 ✅ · EMR]
    A4 -->|matches.jsonl| A5[crown-candidates-indexer<br/>KT-17024]
    A5 --> OS[(OpenSearch<br/>crown_jewel_candidates)]
  end

  subgraph STATE["⚙️ Máquina de Estados · KT-17270 · classifier-state-backend"]
    DDB[(DynamoDB<br/>classifier-cycles-state<br/>+ Stream)]
    S1[state-cycle-init<br/>KT-17028]
    S2[state-station-status<br/>KT-17032]
    S3[state-enterprise-status<br/>KT-17033]
    S1 --> DDB
    DDB -. stream .-> S2 --> DDB
    DDB -. stream .-> S3
  end

  subgraph GSE["📦 GSE · KT-16370 · classifier-gse-backend"]
    G1[gse-sample-reception-notifier<br/>KT-17029]
    G2[gse-sample-anonymizer-notifier<br/>KT-17030]
    G3[gse-request-complete<br/>KT-17031]
  end

  VAL{{"Validación humana<br/>futura · BE 07"}}

  A5 --> DDB
  OS --> VAL
  VAL -->|manifest.json| S1
  S1 -->|signal| AG([Agente Windows / Cloud])
  AG --> G1 --> DDB
  AG --> G3 --> DDB
  G1 -.->|sample| ANON[[Anonymizer · Equipo IA]]
  ANON --> G2 --> DDB
  S3 -->|notify| LLM[[LLM Process Queue · Equipo IA]]

  classDef done fill:#d3f9d8,stroke:#2b8a3e,color:#1b4332;
  classDef rfc fill:#fff3bf,stroke:#e67700,color:#663c00;
  classDef ext fill:#e7e7e7,stroke:#868e96,color:#212529,font-style:italic;
  classDef future fill:#e5dbff,stroke:#7048e8,color:#3b2a6b;
  class A1,A2,A3,A4 done;
  class A5,S1,S2,S3,G1,G2,G3 rfc;
  class AG,ANON,LLM ext;
  class VAL future;
```

**Lectura:** Discovery escanea y matchea → registra candidatos (OpenSearch) y estado de estación (DDB). La **Máquina de Estados** orquesta el ciclo de vida (CYCLE/STATION/REQUEST) sobre la DDB con Stream. La **Validación humana** (futura) cierra el set y dispara, vía `manifest.json`, el `state-cycle-init`. **GSE** recolecta y anonimiza muestras; los notifiers actualizan contadores en la DDB; cuando el ciclo cierra, `state-enterprise-status` notifica al **LLM Process Queue**.

---

## 3. Tickets por épica

### 🔍 Discovery — KT-16369

| Ticket | Componente | Estado |
|---|---|---|
| KT-16612 | tree-url-generator | ✅ Done |
| KT-16613 | tree-uncompressor | ✅ Done |
| KT-16614 | emr-job-trigger | ✅ Done |
| KT-16616 | joyas-priorizer (EMR) | ✅ Done |
| KT-17024 | crown-candidates-indexer (incluye índice OpenSearch) | 📋 RFC |
| KT-17247 | JDC — inclusión de `area_id` en metadata | 📋 RFC |
| KT-17132 | Monorepo `classifier-v2-backend` | ✅ Done |
| _parkeados (→ Validación)_ | KT-17026 validation-handler · KT-17027 validation-confirm | 📋 RFC |

### ⚙️ Máquina de Estados — KT-17270

| Ticket | Componente | Estado |
|---|---|---|
| KT-17028 | **state-cycle-init** (crea CYCLE/STATION/REQUEST, multi-trigger) | 📋 RFC |
| KT-17032 | **state-station-status** (cierre STATION) | 📋 RFC |
| KT-17033 | **state-enterprise-status** (cierre CYCLE + notify LLM) | 📋 RFC |
| KT-17271 | Monorepo `classifier-state-backend` (aloja la DDB `classifier-cycles-state`) | 📋 RFC |

### 📦 GSE — KT-16370

| Ticket | Componente | Estado |
|---|---|---|
| KT-17029 | gse-sample-reception-notifier (samples_received++) | 📋 RFC |
| KT-17030 | gse-sample-anonymizer-notifier (samples_anonymized++) | 📋 RFC |
| KT-17031 | gse-request-complete (status: sent) | 📋 RFC |
| KT-17134 | Monorepo `classifier-gse-backend` | 📋 RFC |

### 🟦 JDC (reunión 2026-06-02) — bajo KT-16369

| Ticket | Componente | Dueño |
|---|---|---|
| KAIM-6315 | Documento de casuísticas de cambios del cliente | Esteban Trujillo |
| KAIM-6316 | Formato estándar de Excel (tipo CESEM) | Esteban Trujillo |
| KT-17245 / KT-17246 | Seguimiento de los anteriores | Sofia Murillo |
| KT-17247 | Inclusión de `area_id` (ver Discovery) | Backend |

---

## 4. Modelo de infraestructura (decisión 2026-06-02)

- **Un monorepo por módulo** (CloudFormation + lambdas + pipeline).
- **La infra de cada lambda va dentro de su ticket de implementación** (su SQS, EventBridge rule/pipe, IAM, buckets). Ya **no** hay tickets DevOps de infra suelta.
- La **DDB `classifier-cycles-state`** (con Stream) es el store compartido — vive en el monorepo de Máquina de Estados; los demás módulos reciben grant IAM cross-stack.

**Tickets de infra suelta cancelados** (su contenido se absorbió en monorepos/implementaciones): KT-17009 (DDB→KT-17271), KT-17010 (OS index→KT-17024), KT-17017 (buckets GSE→KT-17134), KT-17011 y KT-17016 (ya estaban).

---

## 5. Limpieza realizada (2026-06-02)

- **Épica legacy KT-16370** (versión pre-refresh de GSE) → sus 12 hijos cancelados (KT-16617–16622 lambdas + KT-16730–16735 devops), superseded por KT-17028–17033. La épica se **reabrió** y reusa como la GSE vigente.
- **KT-17025** (phase1-enterprise-barrier) cancelado → pertenece a la futura épica de Validación; contexto preservado en `specs-staging/KT-17025-crown-enterprise-barrier.md`.
- Renombrados `gse-cycle-init/station-status/enterprise-status` → `state-*` (son maquinaria genérica de estados, no exclusiva de GSE).

---

## 6. Pendientes / gaps abiertos

| # | Pendiente | Owner |
|---|---|---|
| 1 | **Épica de Validación (BE 07)** — crear con KT-17026/27 + recrear KT-17025 | Producto + Backend |
| 2 | Gap **`signal-handler`** / **`url-generator`** (pre-signed URL Windows) — sin ticket | Equipo Agente / IA |
| 3 | **JDC — reportes Excel + loop de reprocesamiento** — esperan insumos de Esteban (KAIM-6315/6316) | Esteban → Backend |
| 4 | Canales finales con Equipo IA: Signal Handler, Anonymizer, LLM Process Queue (hoy stubs) | Equipo IA |

---

## 7. Diagrama

Ver [architecture.html](architecture.html) (render del diagrama de arriba). Los `.drawio` anteriores se eliminaron por estar desactualizados.
