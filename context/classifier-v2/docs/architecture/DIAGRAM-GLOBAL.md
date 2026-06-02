# Diagrama Global — Classifier Backend v2

Diagrama único que muestra **las 3 fases convergiendo al State Machine compartido** (DDB `classifier-cycles-state`).

---

## Cómo verlo

1. **Mermaid Live Editor** (recomendado): https://mermaid.live → pegar el código → exportar como SVG/PNG
2. **Miro**: Insert → Diagram → Mermaid → pegar el código
3. **VS Code**: instalar extensión "Markdown Preview Mermaid Support" → preview de este archivo
4. **GitHub/GitLab**: este archivo se renderiza automáticamente

---

## Vista global

```mermaid
flowchart TB
    %% ============ ACTORS ============
    subgraph ACTORS [" 👥 EXTERNAL ACTORS "]
        direction LR
        WinAgent["💻 Windows<br/>Agent"]
        CloudAgent["☁️ Cloud<br/>Agent"]
        Client["👤 Client<br/>UI (Web)"]
        KEM["📋 KEM API"]
    end

    %% ============ FASE 1 — SCAN & MATCH ============
    subgraph F1SM [" 🔍 FASE 1 — Scan & Match "]
        direction LR
        TreeURL("λ tree-url-generator"):::lambda
        S3Comp[("S3<br/>compressed_trees")]:::s3
        TreeUncomp("λ tree-uncompressor"):::lambda
        S3Decomp[("S3<br/>decompressed_trees")]:::s3
        EMRTrigger("λ emr-job-trigger"):::lambda
        JoyasPriorizer["⚡ EMR Serverless<br/>joyas-priorizer"]:::emr
        S3Crown[("S3<br/>crown_jewels")]:::s3
        CrownIndexer("λ crown-candidates-indexer"):::lambda
        OpenSearch[("🔍 OpenSearch")]:::opensearch
        CrownBarrier("λ crown-enterprise-barrier"):::lambda

        TreeURL --> S3Comp
        S3Comp -.s3 event.-> TreeUncomp
        TreeUncomp --> S3Decomp
        S3Decomp -.s3 event.-> EMRTrigger
        EMRTrigger --> JoyasPriorizer
        JoyasPriorizer --> S3Crown
        S3Crown -.s3 event.-> CrownIndexer
        CrownIndexer --> OpenSearch
    end

    %% ============ FASE 1 — VALIDACIÓN ============
    subgraph F1V [" ✅ FASE 1 — Validación humana "]
        direction LR
        ValMutation("λ crown-validation-handler"):::lambda
        ValConfirm("λ crown-validation-confirm"):::lambda
        S3Manifest[("S3<br/>validated_crown_jewels")]:::s3

        ValMutation --> OpenSearch
        ValConfirm --> S3Manifest
    end

    %% ============ ⭐ STATE MACHINE (CENTRO) ============
    subgraph SM [" ⭐ STATE MACHINE (compartido por las 3 fases) "]
        direction TB
        DDB[("🗄️ DDB classifier-cycles-state<br/>━━━━━━━━━━━━━━━━━━━━━━━━<br/>PK: enterprise_id<br/>SK: CYCLE# · STATION# · REQUEST#<br/>━━━━━━━━━━━━━━━━━━━━━━━━<br/>scanning → stations_complete →<br/>confirmed → phase2_collecting →<br/>complete")]:::ddb
        Stream(["📡 DDB Stream<br/>NEW_AND_OLD_IMAGES"]):::stream
        Pipes{{"⬡ EventBridge Pipes<br/>filter: CYCLE# / STATION# / REQUEST#"}}:::eventbridge

        DDB --> Stream
        Stream --> Pipes
    end

    %% ============ FASE 2 — GSE ============
    subgraph F2 [" 📥 FASE 2 — Priority Sample Collection (GSE) "]
        direction LR
        GSEInit("λ gse-cycle-init"):::lambda
        GSEReception("λ gse-sample-reception-notifier"):::lambda
        GSERequestC("λ gse-request-complete"):::lambda
        S3Raw[("S3<br/>gse-raw")]:::s3
        S3Anon[("S3<br/>gse-anonymized")]:::s3
        GSEAnonNotif("λ gse-sample-anonymizer-notifier"):::lambda
        GSEStation("λ gse-station-status"):::lambda
        GSEEnt("λ gse-enterprise-status"):::lambda

        GSEInit --> S3Raw
        S3Raw -.s3 event.-> GSEReception
        S3Raw -.sqs.-> S3Anon
        S3Anon -.s3 event.-> GSEAnonNotif
    end

    %% ============ EXTERNAL SYSTEMS ============
    subgraph EXT [" ⬛ EXTERNAL SYSTEMS (black boxes) "]
        direction LR
        Bedrock["🤖 Bedrock<br/>keywords"]:::external
        SignalHandler["📨 Signal Handler"]:::external
        Anonymizer["🔒 Anonymizer"]:::external
        LLM["🧠 LLM Process Queue"]:::external
    end

    %% ============ AGENT FLOWS ============
    WinAgent -- "POST /v2/tree/init" --> TreeURL
    WinAgent -- "PUT presigned URL" --> S3Comp
    CloudAgent -- "PUT direct (IAM)" --> S3Decomp
    Bedrock -. "keywords.json" .-> JoyasPriorizer

    %% ============ KEM INTEGRATION ============
    KEM -. "stations_expected" .-> CrownIndexer

    %% ============ CLIENT FLOWS ============
    Client -- "GraphQL mutations" --> ValMutation
    Client -- "POST /v2/validation/confirm" --> ValConfirm

    %% ============ FASE 1 → STATE MACHINE ============
    CrownIndexer == "✏️ CYCLE + STATION created<br/>status: scanning" ==> DDB
    Pipes -. "STATION#" .-> CrownBarrier
    CrownBarrier == "✏️ status: stations_complete" ==> DDB
    ValConfirm == "✏️ status: confirmed" ==> DDB

    %% ============ STATE MACHINE → FASE 2 ============
    S3Manifest -. "s3 event" .-> GSEInit
    GSEInit == "✏️ status: phase2_collecting" ==> DDB
    GSEInit --> SignalHandler
    SignalHandler -. "payload" .-> WinAgent
    SignalHandler -. "payload" .-> CloudAgent

    %% ============ FASE 2 → STATE MACHINE ============
    WinAgent -- "upload" --> S3Raw
    CloudAgent -- "upload" --> S3Raw
    WinAgent -- "/v2/gse/request-complete" --> GSERequestC
    Anonymizer -- "write" --> S3Anon
    S3Raw -. "sqs" .-> Anonymizer

    GSEReception == "✏️ samples_received++" ==> DDB
    GSERequestC == "✏️ REQUEST status: sent" ==> DDB
    GSEAnonNotif == "✏️ samples_anonymized++" ==> DDB

    Pipes -. "STATION# barrier" .-> GSEStation
    GSEStation == "✏️ STATION: complete" ==> DDB

    Pipes -. "CYCLE# all done" .-> GSEEnt
    GSEEnt == "✏️ status: complete + TTL" ==> DDB
    GSEEnt --> LLM

    %% ============ STYLING ============
    classDef lambda fill:#FF9900,stroke:#CC7A00,color:#fff,stroke-width:2px,font-weight:bold
    classDef s3 fill:#7AA116,stroke:#3F6E0E,color:#fff,stroke-width:2px
    classDef ddb fill:#3334B9,stroke:#1A1A8C,color:#fff,stroke-width:4px,font-weight:bold
    classDef stream fill:#C925D1,stroke:#8B1A91,color:#fff,stroke-width:2px
    classDef eventbridge fill:#FF4F8B,stroke:#A6225E,color:#fff,stroke-width:2px
    classDef opensearch fill:#005EB8,stroke:#003D7A,color:#fff,stroke-width:2px
    classDef emr fill:#7D2AE8,stroke:#5719A8,color:#fff,stroke-width:2px
    classDef external fill:#52525B,stroke:#27272A,color:#fff,stroke-width:2px,stroke-dasharray:5 5
    classDef actor fill:#3F3F46,stroke:#18181B,color:#fff,stroke-width:2px

    class WinAgent,CloudAgent,Client,KEM actor

    %% Subgraph styling
    style ACTORS fill:#F4F4F5,stroke:#71717A,stroke-width:2px,color:#18181B
    style F1SM fill:#EFF6FF,stroke:#1D4ED8,stroke-width:2px,color:#1E3A8A
    style F1V fill:#F0FDF4,stroke:#15803D,stroke-width:2px,color:#14532D
    style SM fill:#FEF3C7,stroke:#D97706,stroke-width:4px,color:#78350F
    style F2 fill:#FCE7F3,stroke:#BE185D,stroke-width:2px,color:#831843
    style EXT fill:#F4F4F5,stroke:#52525B,stroke-width:2px,stroke-dasharray:8 4,color:#27272A
```

---

## Convenciones visuales

| Elemento | Color | Significado |
|---|---|---|
| 🟧 Naranja | `#FF9900` | AWS Lambda |
| 🟩 Verde | `#7AA116` | S3 bucket |
| 🟦 Azul oscuro | `#3334B9` | **DynamoDB (State Machine)** |
| 🟪 Morado claro | `#C925D1` | DDB Stream |
| 🟥 Rosa | `#FF4F8B` | EventBridge Pipes |
| 🔵 Azul | `#005EB8` | OpenSearch |
| 🟣 Morado | `#7D2AE8` | EMR Serverless |
| ⬛ Gris oscuro | `#52525B` | Sistemas externos (black box) |
| ⬜ Gris claro | `#3F3F46` | Actores externos (agentes, cliente) |

### Tipos de flecha

| Flecha | Significado |
|---|---|
| `──→` línea sólida | Llamada síncrona / invocación directa |
| `╌╌→` línea punteada | Evento asíncrono (S3 event, DDB Stream, SQS) |
| `══→` doble línea | **Escritura al State Machine (DDB)** — visualmente destacado |

---

## Lectura del diagrama

1. **Top:** Actores externos disparan el flujo
2. **Centro (amarillo):** **State Machine compartido** — todas las fases leen/escriben aquí
3. **Izquierda:** Fase 1 Scan&Match (azul)
4. **Centro-izq:** Fase 1 Validación (verde)
5. **Derecha:** Fase 2 GSE (rosa)
6. **Bottom:** Sistemas externos (Signal Handler, Anonymizer, LLM, Bedrock)

**Lo importante:** las flechas dobles `══→` muestran que **TODAS las fases convergen en el DDB**. El State Machine es el único punto de verdad.

---

## Si querés iconos AWS oficiales

Mermaid no soporta iconos AWS nativos. Opciones:

1. **Renderizar a SVG** desde Mermaid Live Editor → editar en Figma/Miro y reemplazar nodos por iconos AWS oficiales
2. **Crear en draw.io** importando `architecture.drawio` (ya existe) y limpiándolo
3. **Crear directamente en Miro** copiando este flujo como referencia (los componentes AWS oficiales están en la librería de Miro)

---

## Variantes (si necesitás más detalle)

Si este diagrama es demasiado denso, puedo separarlo en:
- **STATE-MACHINE.md** — transiciones de estado (CYCLE → STATION → REQUEST)
- **F1-SCAN-MATCH.md** — solo Fase 1 con más detalle
- **F2-GSE.md** — solo Fase 2 con más detalle

Indicame qué prefieres.
