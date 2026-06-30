# Diagrama Global — Classifier Backend v2

> **Actualizado:** 2026-06-30 — cierre de Fase 1 por **Excel manual** (sin front): barrier de enterprise → consolidador → validación offline del cliente → ingest-confirm → Fase 2. OpenSearch y la validación web (KT-17026/17027) quedan **diferidos** a la épica de Validación (BE 07).

Diagrama único que muestra **las dos fases convergiendo al State Machine compartido** (DDB `classifier-cycles-state`). La base de Fase 1 (árbol por estación) es el flujo real de scan & match: agentes → árboles → EMR → joyas por estación.

---

## Cómo verlo

1. **Mermaid Live Editor**: https://mermaid.live → pegar → exportar SVG/PNG
2. **VS Code**: extensión "Markdown Preview Mermaid Support" → preview de este archivo
3. **GitHub/GitLab**: se renderiza automáticamente

---

## Vista global

```mermaid
flowchart TB
    %% ============ ACTORS ============
    subgraph ACTORS [" 👥 ACTORES EXTERNOS "]
        direction LR
        WinAgent["💻 Windows Agent<br/>(red local del cliente)"]:::actor
        CloudAgent["☁️ Cloud Agent<br/>(GSuite / OneDrive / SharePoint)"]:::actor
        Client["👤 Cliente<br/>(valida el Excel · offline)"]:::actor
        KEM["📋 KEM API<br/>(stations_expected)"]:::actor
        JDLC["🧠 JDLC — detector agentic<br/>(keywords por enterprise · KT-16859)"]:::external
    end

    %% ============ FASE 1 — SCAN & MATCH (árbol por estación) ============
    subgraph F1SM [" 🔍 FASE 1 — Scan & Match (por estación) "]
        direction TB
        TreeURL("λ tree-url-generator<br/>/trees · KT-16612"):::lambda
        S3Comp[("S3 compressed_trees<br/>{ent}/{sta}.jsonl.gz")]:::s3
        TreeUncomp("λ tree-uncompressor<br/>KT-16613"):::lambda
        S3Decomp[("S3 decompressed_trees<br/>{ent}/{sta}.jsonl · NDJSON")]:::s3
        EMRTrigger("λ emr-job-trigger<br/>KT-16614"):::lambda
        EB1{{"⬡ EventBridge"}}:::eventbridge
        S3Keywords[("S3 search_engine<br/>{ent}.jsonl · 2K-5K keywords")]:::s3
        EMRJob["⚡ EMR Serverless · joyas-priorizer<br/>KT-16616<br/>broadcast keywords → match nombres → reduce"]:::emr
        S3Crown[("S3 crown_jewels<br/>{ent}/{sta}/crown_jewels.json")]:::s3
        S3Rollup[("S3 crown_jewels<br/>{ent}/{sta}/rollup.json · KT-17588<br/>categoría · count · area_histogram")]:::s3

        TreeURL -. "pre-signed PUT URL" .-> WinAgent
        WinAgent == "PUT signed URL" ==> S3Comp
        S3Comp -. "s3 event" .-> TreeUncomp
        TreeUncomp --> S3Decomp
        CloudAgent == "PUT directo (IAM) · sin gzip" ==> S3Decomp
        S3Decomp -. "s3 event" .-> EMRTrigger
        EMRTrigger --> EB1 --> EMRJob
        JDLC -. "keywords.jsonl" .-> S3Keywords
        S3Keywords -. "loads (broadcast)" .-> EMRJob
        EMRJob --> S3Crown
        EMRJob --> S3Rollup
    end

    %% ============ ⭐ STATE MACHINE (CENTRO) ============
    subgraph SM [" ⭐ STATE MACHINE (compartido) · classifier-state-backend "]
        direction TB
        StateInit("λ state-enterprise-init · KT-17370"):::lambda
        StateBarrier("λ state-exploration-barrier · KT-17371"):::lambda
        DDB[("🗄️ DDB classifier-cycles-state<br/>━━━━━━━━━━━━━━━━━━<br/>PK enterprise_id · SK CYCLE#/STATION#/REQUEST#<br/>━━━━━━━━━━━━━━━━━━<br/>initialized → scanning → ready →<br/>awaiting_validation → confirmed →<br/>phase2_collecting → complete")]:::ddb
        Stream(["📡 DDB Stream"]):::stream
        Pipes{{"⬡ EventBridge Pipes<br/>filter CYCLE# / STATION#"}}:::eventbridge

        StateInit == "✏️ CYCLE+STATIONs · initialized" ==> DDB
        StateBarrier == "✏️ STATION scan_complete<br/>barrier → CYCLE ready" ==> DDB
        DDB --> Stream --> Pipes
    end

    %% ============ FASE 1 — CIERRE POR EXCEL (manual, sin front) ============
    subgraph F1V [" 📊 FASE 1 — Cierre por Excel (manual) "]
        direction TB
        Consolidator("λ crown-report-consolidator<br/>KT-17586 · openpyxl"):::lambda
        S3Pending[("S3 crown-reports-pending<br/>{ent}/{cycle}/assessment.xlsx")]:::s3
        S3Validated[("S3 crown-reports-validated<br/>{ent}/{cycle}/assessment.xlsx")]:::s3
        IngestConfirm("λ crown-excel-ingest-confirm<br/>KT-17587"):::lambda
        S3Manifest[("S3 validated_crown_jewels<br/>manifest.json + station-{X}.jsonl")]:::s3

        Consolidator --> S3Pending
        S3Pending -. "📧 descarga" .-> Client
        Client == "📤 sube Excel validado" ==> S3Validated
        S3Validated -. "s3 event" .-> IngestConfirm
        IngestConfirm --> S3Manifest
    end

    %% ============ FASE 2 — GSE ============
    subgraph F2 [" 📥 FASE 2 — Sample Collection (GSE) · classifier-gse-backend "]
        direction TB
        GSEInit("λ state-cycle-init · KT-17028"):::lambda
        S3Raw[("S3 gse-raw")]:::s3
        S3Anon[("S3 gse-anonymized")]:::s3
        GSEReception("λ gse-sample-reception-notifier · KT-17029"):::lambda
        GSEAnonNotif("λ gse-sample-anonymizer-notifier · KT-17030"):::lambda
        GSERequestC("λ gse-request-complete · KT-17031"):::lambda
        GSEStation("λ state-station-status · KT-17032"):::lambda
        GSEEnt("λ state-enterprise-status · KT-17033"):::lambda

        GSEInit --> S3Raw
        S3Raw -. "s3 event" .-> GSEReception
        S3Raw -. "sqs" .-> S3Anon
        S3Anon -. "s3 event" .-> GSEAnonNotif
    end

    %% ============ EXTERNAL ============
    subgraph EXT [" ⬛ SISTEMAS EXTERNOS (cajas negras) "]
        direction LR
        SignalHandler["📨 Signal Handler"]:::external
        Anonymizer["🔒 Anonymizer"]:::external
        LLM["🧠 LLM Process Queue"]:::external
    end

    %% ============ INICIO EXPLORACIÓN → STATE ============
    WinAgent -. "inicia exploración" .-> StateInit
    CloudAgent -. "inicia exploración" .-> StateInit
    KEM -. "stations_expected" .-> StateInit
    WinAgent -. "POST /trees" .-> TreeURL

    %% ============ FASE 1 → BARRIER ============
    S3Rollup -. "s3 event (fin de estación)" .-> StateBarrier

    %% ============ BARRIER ready → CONSOLIDADOR ============
    Pipes -. "CYCLE# status=ready" .-> Consolidator
    S3Rollup -. "lee rollups" .-> Consolidator
    Consolidator == "✏️ CYCLE awaiting_validation" ==> DDB

    %% ============ INGEST-CONFIRM → STATE ============
    IngestConfirm -. "expande paths aprobados" .-> S3Crown
    IngestConfirm == "✏️ CYCLE confirmed / phase2_skipped" ==> DDB

    %% ============ MANIFEST → FASE 2 ============
    S3Manifest -. "s3 event" .-> GSEInit
    GSEInit == "✏️ CYCLE phase2_collecting" ==> DDB
    GSEInit --> SignalHandler
    SignalHandler -. "payload" .-> WinAgent
    SignalHandler -. "payload" .-> CloudAgent

    %% ============ FASE 2 → STATE ============
    WinAgent -- "upload" --> S3Raw
    CloudAgent -- "upload" --> S3Raw
    WinAgent -- "/v2/gse/request-complete" --> GSERequestC
    Anonymizer -- "write" --> S3Anon
    S3Raw -. "sqs" .-> Anonymizer
    GSEReception == "✏️ samples_received++" ==> DDB
    GSERequestC == "✏️ REQUEST sent" ==> DDB
    GSEAnonNotif == "✏️ samples_anonymized++" ==> DDB
    Pipes -. "STATION# barrier" .-> GSEStation
    GSEStation == "✏️ STATION complete" ==> DDB
    Pipes -. "CYCLE# all done" .-> GSEEnt
    GSEEnt == "✏️ CYCLE complete + TTL" ==> DDB
    GSEEnt --> LLM

    %% ============ STYLING ============
    classDef lambda fill:#FF9900,stroke:#CC7A00,color:#fff,stroke-width:2px,font-weight:bold
    classDef s3 fill:#7AA116,stroke:#3F6E0E,color:#fff,stroke-width:2px
    classDef ddb fill:#3334B9,stroke:#1A1A8C,color:#fff,stroke-width:4px,font-weight:bold
    classDef stream fill:#C925D1,stroke:#8B1A91,color:#fff,stroke-width:2px
    classDef eventbridge fill:#FF4F8B,stroke:#A6225E,color:#fff,stroke-width:2px
    classDef emr fill:#7D2AE8,stroke:#5719A8,color:#fff,stroke-width:2px
    classDef external fill:#52525B,stroke:#27272A,color:#fff,stroke-width:2px,stroke-dasharray:5 5
    classDef actor fill:#3F3F46,stroke:#18181B,color:#fff,stroke-width:2px

    style ACTORS fill:#F4F4F5,stroke:#71717A,stroke-width:2px,color:#18181B
    style F1SM fill:#EFF6FF,stroke:#1D4ED8,stroke-width:2px,color:#1E3A8A
    style SM fill:#FEF3C7,stroke:#D97706,stroke-width:4px,color:#78350F
    style F1V fill:#F0FDF4,stroke:#15803D,stroke-width:2px,color:#14532D
    style F2 fill:#FCE7F3,stroke:#BE185D,stroke-width:2px,color:#831843
    style EXT fill:#F4F4F5,stroke:#52525B,stroke-width:2px,stroke-dasharray:8 4,color:#27272A
```

---

## Convenciones visuales

| Color | Significado |
|---|---|
| 🟧 Naranja `#FF9900` | AWS Lambda |
| 🟩 Verde `#7AA116` | S3 bucket |
| 🟦 Azul oscuro `#3334B9` | **DynamoDB (State Machine)** |
| 🟪 Morado `#C925D1` | DDB Stream |
| 🟥 Rosa `#FF4F8B` | EventBridge / Pipes |
| 🟣 Morado `#7D2AE8` | EMR Serverless |
| ⬛ Gris oscuro `#52525B` | Sistemas externos / detector agentic (caja negra) |
| ⬜ Gris claro `#3F3F46` | Actores externos (agentes, cliente, KEM) |

### Tipos de flecha

| Flecha | Significado |
|---|---|
| `──→` sólida | Llamada síncrona / invocación directa |
| `╌╌→` punteada | Evento asíncrono (S3 event, DDB Stream, SQS) |
| `══→` doble | **Escritura al State Machine (DDB)** o PUT clave del flujo — destacado |

---

## Lectura del diagrama

1. **Arriba:** actores (Windows/Cloud Agent, Cliente, KEM) y el detector agentic JDLC.
2. **Fase 1 Scan & Match (azul):** el árbol por estación — agentes → `compressed/decompressed_trees` → EMR `joyas-priorizer` (con keywords de JDLC) → `crown_jewels.json` **+ `rollup.json`** por estación.
3. **Centro (amarillo):** **State Machine**. `state-enterprise-init` da de alta el CYCLE; `state-exploration-barrier` marca cada STATION `scan_complete` y, cuando están todas, `CYCLE → ready`.
4. **Fase 1 Cierre por Excel (verde):** `ready` dispara `crown-report-consolidator` → **un Excel por enterprise** (suma de `rollup.json`, formato KAIM-6316) → `awaiting_validation`. El cliente lo valida **offline** y lo sube → `crown-excel-ingest-confirm` materializa `manifest.json` → `confirmed`.
5. **Fase 2 GSE (rosa):** el `manifest.json` dispara `state-cycle-init` y arranca el muestreo.
6. **Abajo:** sistemas externos (Signal Handler, Anonymizer, LLM Process Queue).

**Lo importante:** las flechas dobles `══→` muestran que **todas las fases convergen en el DDB**. El cierre de Fase 1 ya **no usa front ni OpenSearch**: es un round-trip de Excel a nivel enterprise, gobernado por los estados `ready → awaiting_validation → confirmed`.

---

## Qué cambió respecto a la versión anterior (pre-2026-06-30)

| Antes | Ahora |
|---|---|
| `crown-candidates-indexer` creaba el CYCLE + indexaba cada archivo en OpenSearch | CYCLE lo crea `state-enterprise-init` (KT-17370); el rollup lo hace EMR (KT-17588). OpenSearch fuera del camino crítico |
| `crown-enterprise-barrier` (pieza aparte) | absorbido en `state-exploration-barrier` (KT-17371) |
| Validación web: `crown-validation-handler` + `crown-validation-confirm` (GraphQL/AppSync + Cliente UI Web) | **Excel manual**: `crown-report-consolidator` (KT-17586) + `crown-excel-ingest-confirm` (KT-17587). La variante web (KT-17026/17027) → diferida a BE 07 |
| Estados `scanning → stations_complete → confirmed` | `initialized → scanning → ready → awaiting_validation → confirmed` |

---

## Diagramas relacionados

- **STATE-MACHINE.md** — transiciones de estado CYCLE / STATION / REQUEST (detalle de campos y triggers).
- Specs de cada Lambda: `specs-staging/KT-173XX-*.md`.

> Los generadores `diagrams/build_classifier.py` y `diagrams/aws_drawio.py` quedaron desactualizados (modelo web/OpenSearch). Si se necesita el `.drawio`, regenerar desde este Mermaid.
