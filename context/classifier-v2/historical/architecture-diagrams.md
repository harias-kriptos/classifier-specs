# Arquitectura del Sistema — Descripción de Diagramas de Producción

> Este archivo describe los diagramas de arquitectura reales del sistema en producción.
> Los agentes no pueden ver imágenes, así que este archivo traduce los diagramas
> a texto para que puedan razonar sobre la arquitectura real.
>
> Fuente: Diagramas de Miro/AWS compartidos por el equipo (abril 2025).

---

## 1. DIAGRAMA GENERAL — Tres grandes bloques

El sistema en producción se compone de 3 bloques principales:

1. **Clasificador Core** — Ingesta, validación, clasificación ML, persistencia
2. **Data Risk Management Pipe + LLM Pipeline** — Post-procesamiento con LLMs (solo algunos clientes)
3. **AI Risk Controller** — Persistencia final, contadores, sincronización a OpenSearch

---

## 2. CLASIFICADOR CORE — Flujo de ingesta y clasificación

### Entry Point
```
Windows Agent / Cloud Agent (Gsuite, OneDrive, Sharepoint)
    → Envía scan payload via HTTPS
    → Cloudflare (domain: classifier.kriptos.io)
    → API Gateway
        ├── /v1/batch    → Lambda "Classifier Add Scan Batch"
        ├── /v1/realtime → Lambda "Realtime Classifier"
        ├── /v1/unread   → Lambda "Classifier Unread (v2)"
        └── /v2/unread   → Lambda "Classifier Unread (v2)"
```

### Flujo Batch (Asíncrono)
```
API Gateway /v1/batch
    → Lambda "Classifier Add Scan Batch" (fan-out)
        → SQS "Classification Queue"
            → Lambda "Classifier Queue Reader" (worker ML)
                ← Consulta Redis (ElastiCache) para caché KEM
                ← Si falta en Redis → Lambdas auxiliares:
                    - "Station Lambda" (/station) → Aurora
                    - "Enterprise Lambda" (/enterprise) → Aurora
                → Ejecuta modelos ML (clasificación)
                → Lambda "Classifier Analysis Done"
                    → Conecta con Redis y DocumentDB
        → SQS "Isolation Classification Queue" (mensajes problemáticos)
```

### Flujo Realtime (Síncrono)
```
API Gateway /v1/realtime
    → Lambda "Realtime Classifier"
        ← Consulta Redis (ElastiCache)
        → Responde clasificación inmediata
```

### Flujo Unread (Consulta)
```
API Gateway /v1/unread o /v2/unread
    → Lambda "Classifier Unread (v2)"
        ← Consulta DocumentDB (MongoDB compatible) y DynamoDB
        → Responde al agente con resultados pendientes
```

### KEM (Kriptos Entity Manager)
```
Lambda "Enterprise Initial Setup"
    → App Runner "KEM API"
        → Amazon Aurora (Enterprise DB, GTM-5)
        ← AWS Secrets Manager (credenciales)
    → Amazon EventBridge "KEM Event Bridge"
        → Eventos con OP: insert, reglas: kem.rule
    → S3 Standard (almacenamiento)

Station Lambda (/station) → Aurora
Enterprise Lambda (/enterprise) → Aurora
Ambas alimentan → Redis (ElastiCache) como caché
```

---

## 3. CLASSIFIER STORAGE — Persistencia con isolation per customer

### Classifier Storage Broker
```
Resultado de clasificación (de Realtime Classifier o Classifier Queue Reader)
    → Amazon API Gateway (interno)
        → SQS "Classifier Storage Broker"
            ├── classifier-storage-{owner.enterprise.id}  (cola por cliente)
            ├── classifier-storage-{owner.enterprise.id}  (cola por cliente)
            └── classifier-storage-wildcard               (cola comodín)
                → Lambda "classifier-storage-writer"
                    → DynamoDB "kr-dat-ana-xxx-dydb"
                       (Database Isolation Per Customer: múltiples tablas por cliente)
```

### Desde DynamoDB se bifurcan 4 caminos:

```
DynamoDB "kr-dat-ana-xxx-dydb"
    │
    ├── DynamoDB Stream → Camino 1: User Behavior
    │       → Lambda "User Behavior"
    │           → DynamoDB "User Behavior"
    │
    ├── DynamoDB Stream → Camino 2: Counters Module
    │       → Lambda "user-summarizer" (usa Summaries Reusable Core)
    │       → Lambda "fileserver-summary" (usa Summaries Reusable Core)
    │       → Lambda "analysis-summary" (usa Summaries Reusable Core)
    │           → DynamoDB "Kriptos Summaries Database"
    │               → DynamoDB Stream
    │                   → EventBridge Pipes "Kriptos Summaries Events"
    │                       → Lambda "summaries-syncronizer"
    │                           → OpenSearch Cluster "summaries-opensearch"
    │
    ├── DynamoDB Stream → Camino 3: Analysis Synchronization
    │       → EventBridge Pipes "Kriptos Analysis Events"
    │           → SQS
    │               ├── analysis-synchronization-{owner.enterprise.id}
    │               ├── analysis-synchronization-{owner.enterprise.id}
    │               └── analysis-synchronization-dlq (Dead Letter Queue)
    │                   → Lambda "analysis-search-engine-synchronizer"
    │                       → OpenSearch Cluster "Analysis Search"
    │
    ├── DynamoDB Stream → Camino 4: Fileserver Owners
    │       → DynamoDB "Fileserver Owners"
    │           → DynamoDB Stream
    │
    └── Kinesis Data Streams → Camino 5: Historical Data Lake
            → EventBridge Pipes "Kriptos Analysis Events"
            → Lambda "Analysis Serializer"
                → Amazon Kinesis Data Firehose
                    → S3 "data-analysis-history-delivery" (Data Lake)
                        ← AWS Glue Data Catalog
                        ← Amazon Athena Query Service
                            ← AWS Glue Data Catalog
```

### OpenSearch → Web Platform
```
OpenSearch Cluster "summaries-opensearch"  ──┐
                                              ├── Kriptos Web Platform
OpenSearch Cluster "Analysis Search"  ────────┘    (HTTPS / GraphQL)
```

---

## 4. DATA RISK MANAGEMENT PIPE — Flujo hacia los LLMs

Este flujo se alimenta de DynamoDB Streams del clasificador.
NO todos los clientes pasan por aquí.

### 3 Stages
```
DynamoDB Stream (cambio en análisis)
    │
    ├── Filtering Stage
    │       → Amazon EventBridge Pipes
    │           Reglas de filtrado:
    │           - Omitir eventos REMOVE
    │           - Evaluar document_flow_exception en el payload
    │           - Comparar imágenes nuevas vs viejas para detectar cambios reales
    │
    ├── Enrichment Stage
    │       → Lambda "risk-management-encoder"
    │           Notas:
    │           - La versión de la estructura (lista de campos) debe acompañar
    │             la metadata a lo largo de todo el flujo
    │           - Se inserta como parte del payload en Dynamo
    │
    └── Target Stage
            → EventBridge Custom Event Bus "llm-execution-event-bus" (us-east-2)
                → EventBridge Rule "llm-execution-send-events-rule"
                    → Cross-region bus-to-bus connection
                        → EventBridge Custom Event Bus "llm-execution-event-bus-cross-region" (us-west-2)
                            → EventBridge Rule "llm-execution-rule-*"
                                → LLM Execution Service #1
```

Notas importantes de los diagramas:
- Puede haber una estructura diferente por cada enterprise
- El cross-region bus-to-bus permite enviar eventos de DynamoDB al llm-execution-service module
- La versión de la estructura usada para filtrar debe ser parte integral de la metadata

---

## 5. PIPELINE DE 3 LLMs (JUECES)

```
LLM Execution Service #1 (Clustering)
    → SQS "risk-management-clustering-task"
        → Lambda "risk-management-clustering-model-execution"
            Nota: "There will be one version of the clustering model per enterprise"
            │
            ↓
LLM Execution Service #2 (Clasificación)
    → Recibe output del clustering
    → Ejecuta clasificación con LLM
            │
            ↓
LLM Execution Service #3 (Judge / Validación)
    → Lambda "risk-management-judge-llm-invoker"
    → Este LLM Execution Service valida la decisión de los anteriores
            │
            ↓
    → SQS "risk-management-final-outcomes-publishing"
        → Lambda "risk-management-outcomes-publisher"

Nota: También existe SQS "risk-management-outcomes-publishing" con una
relación marcada como "Deleted relationship" (flujo anterior deprecado)
```

---

## 6. LLM EXECUTION SERVICE — Componente reutilizable (detalle)

Este es un componente que se instancia 3 veces en el pipeline de jueces.
Cada instancia sigue exactamente el mismo flujo interno. La diferencia
es el prompt de Bedrock y la cola de salida.

### Fase 1: Ingesta y Batching
```
SQS "llm-execution-tasks"
    (message attribute: llm-flow: "realtime")
    │
    → Lambda "llm-execution-batch-writer"
    │   - Escribe en EFS como archivos .jsonl
    │   - Max file size: X MB (env var, default 20 MB)
    │   - Max lines per file: 50,000
    │   - DEBE usar NFS file locking para escritura
    │   - Cuando alcanza el límite → mover a carpeta finish inmediatamente
    │
    → Amazon EFS Standard "llm-execution-task-batch-storage"
    │
    → EventBridge Scheduler "llm-execution-task-uploader-trigger" (periódico)
    │
    → Lambda "llm-execution-task-uploader"
    │   - Escanea archivos en EFS que necesitan subirse a S3
    │   - Archivos en carpeta finished O con más de X horas (env var, default 24)
    │   - DEBE usar NFS file locking
    │
    → S3 Bucket "llm-execution-jobs-storage"
    │
    → Lambda "llm-execution-job-recorder"
        - Registra el job en DynamoDB
        → DynamoDB "llm-execution-job-records-{enterprise_id}"
            PK: {JOB_ID}-{Record_Sequential_Number}
        → DynamoDB "llm-execution-jobs"
```

### Fase 2: Gestión de Jobs y Ejecución
```
EventBridge Scheduler "llm-execution-job-manager-trigger" (periódico)
    │
    → Lambda "llm-execution-job-manager"
        - Actualiza estados de jobs
        - Inicia jobs nuevos
        - Limpia jobs viejos
        │
        ├── Camino Batch (Step Functions):
        │       → AWS Step Functions "llm-execution-job-smasher"
        │           → SQS Target (*)
        │           Usa patrón ItemReader para JSON Lines
        │           (ref: docs.aws.amazon.com/step-functions/.../input-output-itemreader)
        │
        └── Camino directo:
                → Amazon Bedrock
```

### Fase 3: Resultados y Resolución
```
Amazon Bedrock
    → S3 Bucket "llm-execution-results-storage"
        ← EventBridge Rule "llm-execution-smashing-process"
            (captura eventos de CloudWatch/S3 para continuar el flujo)
            (ref: docs.aws.amazon.com/step-functions/.../tutorial-cloudwatch-events-s3)
    │
    → Lambda "llm-execution-sync-resolver"
        - Procesa resultados de Bedrock
        - Resuelve por enterprise
        │
        → SQS "llm-execution-sync-resolution-{owner.enterprise.id}"
            (de vuelta al flujo con aislamiento por cliente)
            (esta es la cola target definida en el input data del LLM Execution Service)
```

---

## 7. MULTI-REGION

| Región | Componentes |
|--------|-------------|
| **us-east-2** | Clasificador core, API Gateway, DynamoDB, Redis, DocumentDB, Aurora, OpenSearch, EventBridge bus principal, SQS queues, Kinesis |
| **us-west-2** | LLM Execution Services (Bedrock), EventBridge bus cross-region, Step Functions |

La conexión cross-region es via EventBridge bus-to-bus:
`llm-execution-event-bus` (us-east-2) → `llm-execution-event-bus-cross-region` (us-west-2)