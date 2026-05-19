# Kriptos Classifier — Documento Técnico Maestro
## Contexto para Agentes de IA: Sistema Legacy (V1) + L0-Engine (V2) + Guía de Construcción

> **Fuentes:**
> - Consolidación de 10 sesiones de Knowledge Sharing de Nelson Garzón (V1/Legacy).
> - Presentación del L0-Engine y Blueprint técnico del sprint presencial Ecuador (V2).
> - Este documento unifica y deduplica la información para servir como contexto único y autoritativo.

---

## 0. CONTEXTO DEL PROYECTO Y ROL DEL EQUIPO

### 0.1 Los dos sistemas coexisten
El sistema Legacy (V1) sigue operando en producción. El L0-Engine (V2) es un
rediseño que se integrará en paralelo. Ambos deben convivir.

### 0.2 División de responsabilidades

| Equipo | Responsabilidad |
|--------|----------------|
| **Equipo de IA** | Construyen el L0-Engine local (motores C1-C4), los prompts del LLM, la lógica de clasificación por taxonomía y el AutoResearch Loop. Entregan código funcional (POC). |
| **Equipo de Plataforma (TÚ)** | Tomas el POC del equipo de IA y lo llevas a producción: Lambdas, colas, mensajería, persistencia, escalabilidad, resiliencia, monitoreo, integración con el sistema legacy y con el LLM en Bedrock. Construyes el "Orquestador AWS". |

### 0.3 Qué cambia del V1 al V2

| Aspecto | V1 (Legacy) | V2 (L0-Engine) |
|---------|-------------|-----------------|
| **Input a la nube** | Vector numérico (conteo de palabras) | Muestra representativa del documento (5-10% del contenido) |
| **Motor de IA** | Modelos ML propios (scikit-learn/numpy) en Lambda | LLM en Amazon Bedrock |
| **Procesamiento local** | Vectorización simple | L0-Engine: PII Detection (C1), Taxonomía (C2), AI Authorship (C3), Injection Scanner (C4) + Fuzzy Hashing |
| **Output** | 1 de 4 niveles de sensibilidad + DP/TC booleano | Metadata multidimensional: 6 aristas de impacto |
| **Decisión de envío** | Todo se envía a la nube | Muestreo inteligente: solo lo nuevo o con cambio sustancial |
| **Personalización** | Remapeo manual de niveles por empresa | Matriz de Política generada automáticamente por LLM desde la política del cliente |
| **Explicabilidad** | Ninguna | El LLM justifica POR QUÉ clasificó así |

---

## 1. VISIÓN GENERAL DEL SISTEMA

### 1.1 Sistema Legacy (V1)

El Classifier V1 es un sistema distribuido, event-driven y multi-tenant que clasifica
documentos empresariales según su nivel de sensibilidad. Opera sobre una arquitectura
serverless en AWS, procesando más de **100 millones de registros** de metadata.

El agente (Windows, File Servers, OneDrive/SharePoint/Google) escanea archivos, extrae
texto y lo vectoriza localmente (conteo de palabras clave). Envía esa metadata vectorizada
a la nube donde el Classifier ejecuta modelos ML para asignar:

- **Nivel de Confidencialidad:** Confidencial, Restringido, Uso Interno, Público.
- **Presencia de Datos Personales:** Booleano/Probabilidad.
- **Presencia de Tarjetas de Crédito:** Booleano/Probabilidad.

### 1.2 L0-Engine (V2) — El Nuevo Sistema

El L0-Engine separa **Discovery** de **Clasificación** en 6 fases:

| Fase | Nombre | Dónde corre | Qué hace |
|------|--------|-------------|----------|
| **F1** | Discovery Inteligente | LOCAL (Agente) | Escanear, generar hash, agrupar similares, detectar DP/TC |
| **F2** | Detección DP/TC | LOCAL (Agente) | Motores C1 (PII) y parcialmente C2 |
| **F3** | Matriz de Política | NUBE (Bedrock) | LLM analiza política del cliente → genera reglas de clasificación |
| **F4** | Clasificación LLM | NUBE (Bedrock) | Clasifica solo muestra representativa, propaga al grupo |
| **F5** | Monitoreo Inteligente | LOCAL + NUBE | Compara hashes, decide si reclasificar |
| **F6** | Metadata Personalizada | NUBE | Genera objeto de metadata con 6 aristas |

### 1.3 L0-Engine: Los 4 Motores Locales (Responsabilidad del equipo de IA)

| Motor | Función | Performance | Detalle |
|-------|---------|-------------|---------|
| **C1** PII Detection | Detectar 58 tipos de datos personales en 5 idiomas | F1=1.000, 2.3ms/doc | Gazetteer Aho-Corasick (500K+ nombres) → Regex + Dígito de Control → NER ONNX DistilBERT INT8 fallback |
| **C2** Classification | Clasificar tipo de documento (taxonomía) | 97% Top-1, 7ms/doc | Title Overrides → Keywords ponderadas → Section Headers → TF-IDF+LinearSVC fallback. 52 tipos, 7 industrias |
| **C3** AI Authorship | Detectar contenido generado por IA | Combined 0.863 | En afinación |
| **C4** Injection Scanner | Detectar prompt injection/jailbreak | 92.6% detección | 237 patrones regex, 25 técnicas, 12 idiomas, 9+ encoding techniques |

### 1.4 Principio de Seguridad

**V1:** Solo viajan contadores numéricos no reversibles.
**V2:** Solo viaja el 5-10% de la muestra representativa, y solo si es nuevo o cambio sustancial. El agente decide localmente si enviar o no.

### 1.5 Lógica de Decisión de Envío (Bridge Agente → Nube)

```
Documento modificado → Generar nuevo hash

  ¿Similar + ya clasificado + Sin DP/TC?
    → NO enviar (mantener clasificación local, ahorro de costos)

  ¿Nuevo o cambio sustancial?
    → SÍ enviar muestra representativa al LLM en nube

  ¿Similar + Con DP/TC?
    → Redetectar DP/TC (actualizar conteos), no reclasificar
```

### 1.6 Metadata Multidimensional de Salida (V2)

El output del V2 NO es una etiqueta simple. Es un objeto con 6 aristas:

1. **Joya de la Corona:** ¿Es crítico para el negocio del cliente?
2. **Criticidad PII:** Nivel de riesgo por datos personales (umbrales configurables).
3. **Puede/No Salir:** ¿El documento puede circular fuera de la organización?
4. **Nivel de Sensibilidad:** Según la política específica del cliente.
5. **Insider Threat:** Metadata de riesgo interno.
6. **Cumplimiento Regulatorio:** Alineación con normativas.

### 1.7 Modelo Operativo Legacy (V1)

| Modo | Endpoint | Flujo | Uso |
|------|----------|-------|-----|
| **Batch (Asíncrono)** | `/v1/batch` | API Gateway → Lambda `Classifier Add Scan Batch` → SQS `Classification Queue` → Lambda `Classifier Queue Reader` | Escaneos masivos. Picos de hasta 80k msg/min. |
| **Real-Time (Síncrono)** | `/v1/realtime` | API Gateway → Lambda `Realtime Classifier` → Redis → Response | Feedback inmediato al editar/crear un archivo. |
| **Unread (Consulta)** | `/v1/unread` | API Gateway → Lambda `Classifier Unread (v2)` → DocumentDB | El agente recupera resultados pendientes. |
| **Unread V2** | `/v2/unread` | Lambda `Classifier Unread (v2)` → DynamoDB + DocumentDB | Versión nueva del endpoint de recuperación. |

### 1.8 Qué hace el Clasificador V1 en esencia (4 pasos)

El agente extrae texto del documento y lo convierte en un vector numérico
(conteo de palabras clave según un diccionario). Eso pasa en la máquina del cliente.
El clasificador en la nube recibe ese vector y ejecuta 4 pasos:

**Paso 1 — Valida:**
- ¿La empresa existe en el KEM? ¿La estación está activa?
- ¿El vector tiene el tamaño correcto para la versión del modelo?
- ¿Ya procesé este documento antes? (idempotencia por modification_date)
- ¿Está en la blacklist?
- Si algo falla → se descarta silenciosamente o se mueve a Isolation Queue.

**Paso 2 — Clasifica:**
- Pasa el vector por 3 modelos ML:
  - Nivel de Confidencialidad (Público / Uso Interno / Restringido / Confidencial)
  - Presencia de Datos Personales (booleano/probabilidad)
  - Presencia de Tarjetas de Crédito (booleano/probabilidad)
- Si el vector está vacío → clasifica por el nombre del archivo (ej: "passwords.pdf" → Confidencial)
- Los modelos se cargan por Reflection (importlib) desde classifier-py

**Paso 3 — Enriquece:**
- Calcula `document_obsolescence_date` (creation_date + años configurados por empresa)
- Calcula `leak_value` (riesgo financiero, solo si clasificación es Restringido o Confidencial)
- Sanitiza el owner (no confía en el agente, cruza con KEM)
- Remapea niveles según configuración de la empresa (`get_label_for_classification_number`)
- Si clasificación nula → number=None, label="Unknown"

**Paso 4 — Distribuye:**
- Guarda en DynamoDB (aislado por cliente via classifier-storage-writer)
- Sincroniza a OpenSearch (para el dashboard, via analysis-search-engine-synchronizer)
- Alimenta los contadores/resúmenes (Counters Module: user-summarizer, analysis-summary)
- Manda al Data Lake histórico (Kinesis Firehose → S3 → Glue → Athena)
- El agente recupera resultados via endpoint /v1/unread o /v2/unread

> **El 80% de la complejidad en los diagramas es el Paso 4 (distribución y persistencia),
> no la clasificación en sí.**

**Opcional — Risk Manager (solo algunos clientes):**
Después de los 4 pasos, el DynamoDB Stream dispara el Data Risk Management Pipe
que pasa el resultado por un pipeline de 3 LLMs (clustering → clasificación → juez)
para agregar metadata adicional de riesgo.

### 1.9 Qué cambia del V1 al V2 (L0-Engine): Elimina / Mantiene / Crea

**LO QUE SE ELIMINA (el cerebro ML):**
- Todo el motor de clasificación ML: modelos scikit-learn/numpy
- La validación de vectores, vector scrubbing (-1.0 → 0.0)
- La selección de modelo por idioma (spa/eng)
- La carga reflectiva con importlib y classifier-py con sus binarios
- El diccionario de features y el problema de mismatch de versiones
- El fan-out en Go (add-scan-batch) para despedazar arrays de vectores
- Básicamente todo el `classifier-core` y la lógica de los 10 videos de Nelson

**LO QUE SE MANTIENE (el cuerpo de distribución):**
- classifier-storage-writer con Database Isolation Per Customer
- DynamoDB con tablas por enterprise_id
- DynamoDB Streams como trigger de eventos
- Counters Module (summaries, user behavior, analysis-summary)
- Sincronización a OpenSearch (analysis-search-engine-synchronizer, summaries-syncronizer)
- Data Lake con Kinesis Firehose / S3 / Glue / Athena
- Endpoint unread para que el agente recupere resultados
- KEM con App Runner / Aurora / Redis
- EventBridge Pipes para routing de eventos
- Kriptos Web Platform consultando OpenSearch via GraphQL

**LO QUE SE CREA (el nuevo cerebro LLM):**
- Nuevo core de orquestación: recibe muestra del L0-Engine, prepara y envía al LLM
- Nuevo pipeline de LLM (probablemente reutilizando el patrón del LLM Execution Service
  que ya existe en el Risk Manager: batch-writer → EFS → uploader → S3 → Bedrock → sync-resolver)
- Lógica de propagación de grupo: cuando el LLM clasifica un doc representativo,
  esa clasificación se aplica a todo el grupo de documentos similares
- Motor de metadata multidimensional (6 aristas en vez de 1 nivel)
- Integración con los resultados del L0-Engine local (C1 PII, C2 Taxonomía, C4 Injection)

> **No se construye todo de cero. Se reemplaza el cerebro (ML → LLM)
> y se reutiliza el cuerpo (persistencia, distribución, monitoreo).**

### 1.10 El V1 tiene DOS módulos que coexisten hoy

**Módulo 1 — Clasificador ML (Legacy Core):**
El flujo original de clasificación con modelos ML. Todos los clientes pasan por aquí.

**Módulo 2 — Risk Manager (LLM):**
Post-procesador que se alimenta de DynamoDB Streams del clasificador.
Aplica un pipeline de 3 LLMs (clustering → clasificación → judge) para
agregar metadata de riesgo adicional. **NO todos los clientes pasan por aquí.**
Usa Amazon Bedrock y corre en us-west-2 (cross-region desde us-east-2).

### 1.9 El V2 (L0-Engine) — Pendiente de definir integración

El L0-Engine se construirá durante el sprint presencial en Ecuador.
**La forma exacta en que se integra a la arquitectura V1 aún no está definida.**
Las posibilidades incluyen: reemplazar el clasificador ML, agregarse como
tercer módulo paralelo, o reutilizar la infraestructura del Risk Manager.
Esto se definirá en la semana del 12-17 de abril.

---

## 2. MAPA DE REPOSITORIOS Y COMPONENTES

### 2.1 Librerías Compartidas (No son servicios, se importan)

#### `kriptos_kernel` — La Fundación
- **Versión conocida:** 1.5.3 (en producción), 0.1.9 (referenciada en otros contextos).
- **Propósito:** Abstracción de infraestructura de bajo nivel. Si mañana cambian DynamoDB por Aurora, solo se toca este repo.
- **Estructura interna:**
  - `base.domain`: Abstract Base Classes (ABC). Todos los repositorios nuevos deben heredar de aquí.
  - `infrastructure.repositories`: Implementaciones concretas (`MongoRepository`, `DynamoRepository`, `RedisRepository`).
  - `infrastructure.inject`: Contenedor de Dependency Injection (usa la librería `inject`).
  - `redis_source.py`: Driver para ElastiCache.
  - `dynamo.py`: Lógica de persistencia en DynamoDB.
  - `setup.py`: Dependencias por "aristas" (ej: `pip install kriptos_kernel[mongo]` solo instala drivers de Mongo).
- **Librerías críticas:** `aiobotocore` (AWS Async), `motor` (Mongo Async), `aioredis`.
- **Regla de oro:** Siempre congelar la versión en `requirements.txt` o `Dockerfile` (ej: `kriptos_kernel==0.1.9`).
- **Es agnóstica:** No contiene lógica de negocio del clasificador. Puede usarse en cualquier proyecto de la empresa.

#### `classifier-core` (también referenciado como `kriptos_classifier_core` o `classifier-core-package`)  — El Cerebro
- **Alojamiento:** AWS CodeArtifact.
- **Propósito:** Contiene el algoritmo de clasificación, definiciones de objetos, validaciones de esquemas de Analysis Payloads y la lógica pura de clasificación.
- **Dependencia:** Importa `kriptos_kernel`.
- **Consumido por:** Todos los servicios de ejecución (Batch, Realtime, Script).
- **Estructura interna clave:**
  - `application.orchestrators.classification_orchestrator.py` → Clase `ClassificationOrchestratorAggregator` (orquestador principal).
  - `application.subscribers.classification_subscriber.py` → Patrón Observer: acciones secundarias (notificaciones, logs, contadores).
  - `domain.commands.classification_command.py` → `RunClassificationCommand`: acción pura de clasificar. No interactúa con servicios externos.
  - `configuration.constants.py` → Define `EMPTY_VECTOR_EXCEPTION_TERM` (valores como `-1.0`), rutas de modelos, idioma por defecto.
- **Tests:** Son tan críticos que se reutilizan en el pipeline de despliegue de los modelos de IA.
- **Obligatorio:** Todas las Lambdas deben importar este paquete para garantizar consistencia.

#### `classifier-py` (también `models-storage`) — El Motor de IA
- **Propósito:** Binarios de los modelos de IA + script ejecutor.
- **Estructura por versión:**
  - `model_conf`: Modelo de Confidencialidad.
  - `model_dp`: Modelo de Datos Personales.
  - `model_cc`: Modelo de Tarjetas de Crédito.
  - `classifier.py`: Script ejecutor que interpreta los binarios.
- **Integración:** Vía **Reflexión de Python** (`importlib`). El Core no importa directamente `classifier-py`; lo carga dinámicamente usando strings de configuración. Esto desacopla Backend de Data Science.
- **Clase clave:** `Executor` — encargada de la importación reflectiva de modelos al espacio de memoria de la Lambda.

### 2.2 Servicios de Ejecución (Microservicios / Lambdas)

| Servicio | Lenguaje | Función |
|----------|----------|---------|
| `add-scan-batch` | **Go** | Lambda de pre-procesamiento. Recibe el JSON masivo del agente, lo valida y lo "despedaza" (fan-out) en mensajes individuales para SQS. **Go es crítico aquí por su manejo superior de concurrencia.** |
| `classifier-service` / `KR-classifier-script-batch-prod` | Python | Worker principal. Escucha SQS, ejecuta el modelo de IA. Memoria: 1 GB RAM. Latencia: ~790ms por cada 10 análisis. |
| `realtime-classifier` | Python + FastAPI | Endpoint síncrono para clasificación en tiempo real. |
| `kafka-payload-publisher` | **Java** | Bridge para inyectar resultados en Kafka MSK Serverless con autenticación IAM. Java se eligió exclusivamente por la necesidad de un driver robusto para MSK Serverless. |
| `classifier-current-analysis-consumer` / `mongo-consumer` | Python 3.9 | Consumidor más robusto. Procesa mensajes de Kafka y persiste en la base de datos operativa (DynamoDB/MongoDB). |
| `lightweight-etl-consumer` | Python | Transformaciones rápidas y de bajo cómputo. Usa Redis para deduplicación. |
| `deleted-document-consumer` | Python | Lógica de purga y consistencia cuando se elimina un documento. |
| `fileserver-owners` | Python | Resolución de propietarios de archivos en servidores de red. |
| `analysis-history-synchronizer` | Python | Sincroniza estados entre base operativa e histórico. |
| `classifier-unread-analysis` | Python | Endpoint para que agentes recuperen resultados (V2 en GitHub/DynamoDB, V1 antigua en Bitbucket/MongoDB). |
| `KR-classifier-enterprises-service-prod` | Python | Microservicio para consultar metadatos de empresa. |
| `KR-classifier-stations-service-prod` | Python | Microservicio para consultar datos de estación. |

### 2.3 Otros Componentes

- `kr-analysis-history-event-ids`: Identificadores de eventos para rastreo en el Data Lake.
- `django-signals`: El backend usa señales de Django para disparar eventos ante cambios de estado.
- `Dynamo-S3-Synchronizer-POC`: Script de PySpark para el Job ETL de Glue (exportación histórica).

---

## 3. ARQUITECTURA HEXAGONAL (PATRÓN GENERAL)

El sistema sigue estrictamente Arquitectura Hexagonal (Puertos y Adaptadores). Esta separación fue la clave para migrar de MongoDB a DynamoDB sin tocar la lógica de clasificación.

### 3.1 Capa de Dominio (Core / Inner)
- **No tiene dependencias externas.** No sabe que existe AWS, Redis, Kafka ni MongoDB.
- **Contenido:** Entidades (`Analysis`, `Document`, `NivelDeSensibilidad`), Value Objects (`DocumentStatus`), reglas de obsolescencia, reglas de clasificación.
- **Clase central:** `Analysis` con su `mandatory_scheme` (campos obligatorios: `enterprise_id`, `classifier_version`, etc.).

### 3.2 Capa de Aplicación
- **Orquestadores/Aggregators:** Coordinan el flujo end-to-end (`RunClassificationAggregator`).
- **Commands:** Encapsulan acciones puras (`RunClassificationCommand`).
- **Subscribers:** Patrón Observer para acciones secundarias.
- **Use Cases:** `ProcessBatchScan`, `RespondRealTimeClassification`, `ClassifyDocument`, `SyncHistoryData`.
- **Patrón CQRS:** Separa operaciones de lectura (queries) de escritura (commands).

### 3.3 Capa de Infraestructura (Adapters)
- **No es una capa externa; los Adapters forman parte de esta capa** (aclaración explícita de Nelson).
- **Adaptadores de Entrada (Inbound):** Handlers de Lambda para SQS, MSK, API Gateway.
- **Adaptadores de Salida (Outbound):** `MongoRepository`, `DynamoRepository`, `RedisRepository`, `AnalysisBrokerRepository` (Kafka vía REST), clientes de Kinesis.

### 3.4 Patrones de Diseño Implementados

| Patrón | Uso |
|--------|-----|
| **Dependency Injection** | Patrón principal. El orquestador recibe interfaces, no clases concretas. Librería: `inject`. |
| **Factory** | Para instanciar repositorios de `kriptos_kernel`. |
| **Command** | Encapsula la acción de clasificar. |
| **Observer/Subscriber** | Acciones secundarias post-clasificación. |
| **CQRS** | Separación de lecturas y escrituras en la capa de aplicación. |
| **Reflection** | Carga dinámica de modelos de IA vía `importlib`. |

### 3.5 Inyección de Dependencias: Flujo

```
Lambda Handler (Infrastructure)
  → llama a Aggregator (Application)
    → usa Command (Application) que llama al modelo
    → usa Repository (interface en Domain, implementación en Infrastructure)
      → Repository usa kriptos_kernel (Infrastructure de bajo nivel)
```

En **producción:** `self.repository.save()` usa un adaptador de MongoDB/DynamoDB.  
En **tests:** `self.repository.save()` usa un adaptador `InMemory`.

---

## 4. FLUJO DE DATOS COMPLETO (END-TO-END)

### 4.1 Ingesta y Pre-procesamiento

```
Agente (Win/FileServer/Cloud)
  → Extrae texto → Vectoriza localmente (conteo de palabras clave)
  → Envía JSON masivo vía HTTPS a API Gateway

API Gateway (VTL Validation):
  - Valida presencia de API-KEY en headers
  - Valida estructura mínima del JSON: {configuration, partition, payload}
  - Si falla → 400 Bad Request SIN disparar Lambda (ahorro de costos)

Lambda add-scan-batch (Go):
  - Recibe array de documentos
  - Fan-out: publica UN mensaje por documento en SQS
  - Evita que un documento pesado bloquee a los demás
```

### 4.2 Clasificación (Worker)

```
SQS (Classification Queue) → Trigger → Lambda Classifier (Python)

1. VALIDACIÓN DE ESTACIÓN
   - Consulta station_id en Redis (cache de KEM)
   - Si estación "Inactiva" → ABORTA (ahorro de cómputo)
   - Si no está en Redis → consulta Lambdas auxiliares → Aurora SQL

2. ENRIQUECIMIENTO (Data Sanitization)
   - NO confiar en owner_name del agente (puede estar alterado)
   - Cruzar ID en KEM → sobrescribir owner con data oficial

3. BLACKLIST CHECK
   - Consulta BlacklistRepository
   - Si document_id en lista negra → DESCARTAR

4. IDEMPOTENCIA
   - Consulta último modification_date guardado
   - Si modification_date del mensaje ≤ al guardado → TERMINA (no reprocesar)

5. VALIDACIÓN DE VECTORES (Vector Scrubbing)
   - Buscar EMPTY_VECTOR_EXCEPTION_TERM (-1.0) → reemplazar por 0.0
   - Si suma de todas las posiciones = 0 → marcar como "vacío"
   - Validar que tamaño del vector coincida con la versión del modelo activo

6. SELECCIÓN DE MODELO
   - Evaluar campo `lang` (spa / eng)
   - Seleccionar modelo correspondiente
   - Cargar vía Reflection (importlib)

7. EJECUCIÓN TRIPLE
   - model_conf → Nivel de Confidencialidad (integer)
   - model_dp → Datos Personales (float/probabilidad)
   - model_cc → Tarjetas de Crédito (float/probabilidad)

8. POST-PROCESAMIENTO
   - Normalización de tipos (isinstance validations)
   - Remapeo de niveles: get_label_for_classification_number()
     (una empresa puede eliminar "Nivel 3" y que todo sea "Nivel 2")
   - Si clasificación nula → number=None, label="Unknown"
   - Cálculo de obsolescencia: creation_date + años_empresa = document_obsolescence_date
   - Cálculo de leak_value: solo si clasificación es 2 (Restricted) o 3 (Confidential)
     Valor base en env var DOCUMENT_LEAK_VALUE

9. PUBLICACIÓN
   - NO escribe a DB directamente
   - Envía resultado a Kafka vía kafka-payload-publisher (API REST intermedio)
   - Particionamiento por Hash(station_id)
```

### 4.3 Vectores Vacíos (Caso Especial)

Si `empty_vector = true` (archivo sin texto, solo imágenes sin OCR, o vacío):
- Se aplica lógica basada en el **nombre del archivo**.
- Ejemplo: si se llama `"passwords.pdf"` → se clasifica como Confidencial por política.
- Si no hay señales → se asigna nivel de confidencialidad predefinido por la empresa (usualmente bajo).

### 4.4 Broadcast Pattern (Post-Clasificación)

```
Lambda Classifier → kafka-payload-publisher (REST) → Amazon MSK (Kafka)
                                                         ↓
                                              Tópico: classifier-storage / classifier-analysis
                                                         ↓
                               ┌─────────────────────────┼─────────────────────────┐
                               ↓                         ↓                         ↓
                    mongo-consumer              lightweight-etl         analysis-summary-lambda
                    (DynamoDB/Mongo)            (Redis dedup)          (recalcula % globales)
                               ↓                         ↓                         ↓
                    deleted-doc-consumer      fileserver-owners      history-synchronizer
                               ↓
                    search-engine-sync → OpenSearch (Dashboard)
```

**Regla de oro:** La ingesta NUNCA debe detenerse, incluso si la base de datos está caída. Kafka actúa como amortiguador.

### 4.5 Data Lake (Histórico)

```
Clasificación → Kinesis Data Firehose (buffer: 15 min o 150MB)
  → S3 (formato Parquet, compresión Snappy, particionado por enterprise_id)
  → AWS Glue Catalog
  → Amazon Athena (consultas SQL serverless)
```

### 4.6 Recuperación por el Agente (Unread V2)

- El servidor es **stateless**. El agente es quien sabe qué fue lo último que leyó.
- El agente envía su `station_id` + `enterprise_id` + token de paginación (Base64 del `LastEvaluatedKey` de DynamoDB).
- Batching: 200 registros por petición.
- **Reintentos seguros:** si pierde conexión, reenvía el mismo token y obtiene la misma página.

---

## 5. INFRAESTRUCTURA AWS (CONFIRMADA POR DIAGRAMAS DE PRODUCCIÓN)

> **NOTA:** Esta sección fue actualizada con los diagramas reales de producción.
> Los videos de Nelson mencionaban Kafka/MSK como broadcast; en los diagramas
> actuales se usa EventBridge Pipes + SQS con isolation por enterprise_id.

### 5.1 Dominio y Entry Point
- **Dominio:** `classifier.kriptos.io`
- **CDN/Proxy:** Cloudflare
- **API Gateway:** 4 endpoints: `/v1/batch`, `/v1/realtime`, `/v1/unread`, `/v2/unread`

### 5.2 Scan Payload Structure (Confirmada)
```json
{
  "owner": {
    "enterprise": { "name": "string", "id": "uuid" },
    "agent": {
      "id": "uuid",
      "name": "HOSTNAME o EMAIL_ACCOUNT",
      "type": "windows | onedrive | gsuite | fileserver",
      "version": "2.0.45"
    },
    "area": { "id": "uuid", "name": "AREA NAME" }
  },
  "ml_version": "string",
  "document": [{
    "name": "string",
    "path": "C:\\path\\to\\file.docx",
    "modification_date": "ISO8601",
    "vector": [1, 1, 1, 0.3, 0, 0.0, 0, 0],
    "owner": "string",
    "id": "string",
    "drive_id": "string",
    "scan_date": "ISO8601",
    "lang": "spa | eng",
    "ml_version": "100",
    "file_server": { "area": "string" }
  }]
}
```

Campos de fecha normalizados en el procesamiento:
- `document.modification_date` (string)
- `document.modification_date_normalized` (timestamp)
- `document.modification_date_time_zone` (string)
- `document.modification_day` (string)
- `document.modification_hour` (number)

### 5.3 Mensajería (Actualizado — sin Kafka en diagrama actual)

#### SQS (Clasificador)
- `Classification Queue` — Cola principal batch
- `Isolation Classification Queue` — Mensajes problemáticos

#### SQS (Classifier Storage Broker)
- `classifier-storage-{owner.enterprise.id}` — Colas aisladas por cliente
- `classifier-storage-wildcard` — Cola comodín

#### SQS (Risk Manager / LLM)
- `risk-management-clustering-task`
- `risk-management-outcomes-publishing`
- `risk-management-final-outcomes-publishing`
- `llm-execution-tasks` (message attribute: `llm-flow: "realtime"`)
- `llm-execution-sync-resolution-{owner.enterprise.id}`

#### SQS (Analysis Synchronization)
- `analysis-synchronization-{owner.enterprise.id}`
- `analysis-synchronization-dlq` (Dead Letter Queue)

#### EventBridge
- EventBridge Pipes: `Kriptos Analysis Events`, `Kriptos Summaries Events`
- Custom Event Bus: `llm-execution-event-bus` (us-east-2)
- Custom Event Bus: `llm-execution-event-bus-cross-region` (us-west-2)
- Rules: `llm-execution-send-events-rule`, `llm-execution-rule-*`
- Rule: `llm-execution-smashing-process`
- Schedulers: `llm-execution-task-uploader-trigger`, `llm-execution-job-manager-trigger`
- `KEM Event Bridge` (eventos del KEM API)

### 5.4 Almacenamiento (Confirmado)

#### DynamoDB
- `kr-dat-ana-xxx-dydb` — **Database Isolation Per Customer** (múltiples tablas por cliente)
- `llm-execution-jobs` — Tracking de jobs de LLM
- `llm-execution-job-records-{enterprise_id}` — PK: `{JOB_ID}-{Record_Sequential_Number}`
- `Kriptos Summaries Database` — Contadores y resúmenes
- `User Behavior` — Comportamiento de usuario
- `Fileserver Owners` — Propietarios de archivos en fileservers

#### Amazon DocumentDB (MongoDB compatible — SIGUE ACTIVO)
- Usado por: `Classifier Unread (v2)`, `Classifier Analysis Done`
- **Los videos decían que MongoDB estaba en deprecación, pero los diagramas muestran que DocumentDB sigue activo**

#### Amazon Aurora (PostgreSQL/MySQL)
- `Enterprise DB` — GTM-5, gtm-5
- Backend del KEM
- Consultada por `Station Lambda` y `Enterprise Lambda`

#### ElastiCache for Redis
- Cache del clasificador: metadata de empresas/estaciones del KEM
- Usado por: `Realtime Classifier`, `Classifier Analysis Done`

#### S3 Buckets
- `llm-execution-task-batch-storage` — En realidad es EFS Standard
- `llm-execution-jobs-storage` — Jobs para Bedrock
- `llm-execution-results-storage` — Resultados de Bedrock
- `data-analysis-history-delivery` — Data Lake histórico

#### EFS (Elastic File System)
- `llm-execution-task-batch-storage` — EFS Standard para batching de tasks LLM

### 5.5 Compute (Lambdas confirmadas)

#### Clasificador Core
| Lambda | Función |
|--------|---------|
| `Classifier Add Scan Batch` | Fan-out: recibe batch del agente, publica en Classification Queue |
| `Classifier Queue Reader` | Worker: lee de SQS, ejecuta modelo ML |
| `Realtime Classifier` | Clasificación síncrona, usa Redis |
| `Classifier Analysis Done` | Post-procesamiento, conecta con Redis y DocumentDB |
| `Classifier Unread (v2)` | Endpoint de recuperación para agentes |

#### KEM y Metadata
| Lambda | Función |
|--------|---------|
| `Station Lambda` | Consulta datos de estación (`/station`) → Aurora |
| `Enterprise Lambda` | Consulta datos de empresa (`/enterprise`) → Aurora |
| `Enterprise Initial Setup` | Crea recursos para nueva empresa → App Runner KEM API → Aurora |

#### Classifier Storage (Persistencia)
| Lambda | Función |
|--------|---------|
| `classifier-storage-writer` | Escribe en DynamoDB con isolation per customer |

#### Risk Manager (LLM Pipeline)
| Lambda | Función |
|--------|---------|
| `risk-management-encoder` | Enrichment Stage: prepara payload para LLM |
| `risk-management-clustering-model-execution` | Ejecuta modelo de clustering (1 versión por enterprise) |
| `risk-management-judge-llm-invoker` | LLM Juez: valida decisión final |
| `risk-management-outcomes-publisher` | Publica resultados finales |

#### LLM Execution Service (Componente reutilizable)
| Lambda | Función |
|--------|---------|
| `llm-execution-batch-writer` | Escribe tasks en EFS como .jsonl (max 50K líneas, max 20MB, NFS locking) |
| `llm-execution-task-uploader` | Sube archivos de EFS a S3 (archivos finished o > 24h) |
| `llm-execution-job-recorder` | Registra job en DynamoDB |
| `llm-execution-job-manager` | Actualiza estados, inicia jobs nuevos, limpia jobs viejos |
| `llm-execution-sync-resolver` | Procesa resultados de Bedrock, resuelve por enterprise |

#### Counters Module
| Lambda | Función |
|--------|---------|
| `User Behavior` | Procesa DynamoDB Stream → tabla User Behavior |
| `user-summarizer` | Usa Summaries Reusable Core → Kriptos Summaries Database |
| `fileserver-summary` | Usa Summaries Reusable Core → Kriptos Summaries Database |
| `analysis-summary` | Usa Summaries Reusable Core → Kriptos Summaries Database |

#### Synchronization
| Lambda | Función |
|--------|---------|
| `summaries-syncronizer` | Kriptos Summaries Database → OpenSearch (summaries) |
| `analysis-search-engine-synchronizer` | Analysis data → OpenSearch (Analysis Search) |
| `Analysis Serializer` | Data Lake: DynamoDB → Kinesis Firehose → S3 |

### 5.6 Otros servicios

- **App Runner:** KEM API
- **AWS Step Functions:** `llm-execution-job-smasher` (procesa jobs batch contra Bedrock)
- **Amazon Bedrock:** LLM execution (us-west-2)
- **AWS Glue Data Catalog:** Catalogación del Data Lake
- **Amazon Athena:** Query Service sobre el Data Lake
- **Kinesis Data Firehose:** Serialización hacia Data Lake
- **Kinesis Data Streams:** Flujo hacia EventBridge Pipes
- **OpenSearch (Provisioned Cluster):** `Analysis Search` y `summaries-opensearch`
- **Kriptos Web Platform:** UI que consulta OpenSearch vía HTTPS/GraphQL

### 5.7 Multi-region
- **us-east-2:** Clasificador core, EventBridge bus principal
- **us-west-2:** LLM Execution Services (Bedrock), EventBridge bus cross-region

### 5.8 KEM (Kriptos Entity Manager) — Arquitectura confirmada
- **Backend:** Amazon Aurora (GTM-5)
- **API:** App Runner (`KEM API`)
- **Cache:** ElastiCache for Redis
- **Eventos:** EventBridge (`KEM Event Bridge`) con reglas `kem.rule`
- **Setup:** Lambda `Enterprise Initial Setup` crea recursos y configura
- **Secretos:** AWS Secrets Manager

---

## 6. LÓGICA DE NEGOCIO (REGLAS CORE)

### 6.1 Niveles de Clasificación
- **Público** (0/1)
- **Uso Interno** (1)
- **Restringido** (2)
- **Confidencial** (3)
- **Configurable por empresa:** Una empresa puede eliminar niveles y remapear (`get_label_for_classification_number`).

### 6.2 Obsolescencia
- **Regla:** `document_obsolescence_date = creation_date + años_configurados` (default 5 años, configurable: 5, 7, 10).
- **Monitoreo:** Un sistema "hermano" revisa la base diariamente y marca registros como obsoletos.
- **Otra regla:** Si las reglas del KEM cambian significativamente post-procesamiento → el análisis se marca como obsoleto.
- **Campo:** `document_status` = `CURRENT` | `OBSOLETE`.

### 6.3 Leak Value (Riesgo Financiero)
- Solo se calcula si clasificación es 2 (Restricted) o 3 (Confidential).
- Valor base definido en env var `DOCUMENT_LEAK_VALUE`.

### 6.4 Idempotencia
- **Requisito no funcional crítico.**
- El clasificador debe poder ejecutarse N veces con el mismo mensaje y producir el mismo resultado.
- Basado en: ID del análisis + `modification_date` guardado vs. recibido.
- Evita alterar contadores estadísticos por reintentos automáticos del agente.

### 6.5 Multitenancy
- **Database Isolation Per Customer** en DynamoDB.
- No se consultan tablas globales sin contexto de `enterprise_id`.
- En S3, prefijos por `enterprise_id` para aislamiento.

### 6.6 Identificación de Archivos por Tipo de Cliente

| Cliente | Cómo se identifica el archivo |
|---------|-------------------------------|
| Windows Agent | SHA256 del path completo |
| Fileserver | SHA256 del path + owner |
| Cloud (OneDrive/SharePoint/Google) | Drive ID único |

### 6.7 Formatos Soportados
`.doc`, `.docx`, `.xls`, `.xlsx`, `.pps`, `.ppsx`, `.pdf`.

**Bug conocido:** Archivos con extensiones no estándar (`.xlsm`, `.tmp`, `.dot`) pueden fallar porque la detección de formato se basa excesivamente en la extensión del path.

### 6.8 Esquema Obligatorio (`mandatory_scheme`)
En la clase `Analysis`, si el payload no trae estos campos mínimos, el mensaje se rechaza:
- `enterprise_id`
- `classifier_version`
- (Otros campos definidos en el Domain)

---

## 7. MONITOREO, RESILIENCIA Y DEVOPS

### 7.1 Métrica Rey: Offset Lag
- **Alarma en CloudWatch** para `Sum of Offset Lag`.
- Si crece → el sistema es más lento que la ingesta.

### 7.2 Reserved Concurrency (Freno de Emergencia)
- Si la DB sufre → limitar concurrencia de Lambda a un número bajo (ej: 50).
- Para mantenimiento sin perder datos → concurrencia = 0. Kafka retiene los mensajes.

### 7.3 Comportamiento de Error en Lambda
- Si la Lambda tiene exceptions, AWS **detiene el auto-escalamiento** para evitar inundar logs.
- Primero corregir el bug, luego escalar.

### 7.4 Escalamiento Gradual
- Empezar con pocas particiones de Kafka (2-3) e ir subiendo monitoreando costos y carga downstream.

### 7.5 Mensajes Malformados
- Se registran en **Base64 dentro de CloudWatch** para decodificación y depuración manual.
- Existe una **Isolation Queue** para aislar mensajes problemáticos.

### 7.6 CI/CD
- **Bitbucket Pipelines:** Tests unitarios al hacer push.
- **Dockerfile.verifier:** Imagen Docker específica para pruebas.
- **test_cases.json:** Casos de prueba por versión del modelo (archivo de prueba, clasificación esperada, tamaño de vector, idioma).
- **Integración con IA:** Cuando Data Science actualiza un modelo, el pipeline de `classifier-core` se dispara automáticamente para verificar compatibilidad.

---

## 8. PROBLEMAS CONOCIDOS Y DEUDA TÉCNICA

1. **Mismatch de vectores:** El error #1. El agente y el clasificador pueden tener versiones diferentes del diccionario de features. Vector esperado de tamaño X pero recibido de tamaño Y.
2. **Detección de formato frágil:** Se basa excesivamente en la extensión del archivo.
3. **MongoDB en deprecación:** Se está migrando a DynamoDB.
4. **Kafka Publisher sin batching:** Actualmente envía un mensaje a la vez; se identifica como oportunidad de mejora.
5. **Acoplamiento vía API Gateway:** El clasificador llega a Kafka a través de API Gateway como proxy; se propone cliente directo.
6. **Agente Antiguo:** Requería desencriptación RSA con llave asimétrica en Lambda. El nuevo confía en HTTPS de API Gateway.
7. **Validación por hostname:** Propenso a duplicados entre empresas. Se propone migrar a `station_id` único global.
8. **Limpieza del Data Catalog:** Se necesita borrar Crawlers y tablas temporales post-transformación.
9. **Cold Start de Lambda:** Modelos de IA pesados causan latencia en primer arranque.

---

## 9. GUÍA DE CONSTRUCCIÓN: TU ALCANCE COMO INGENIERO DE PLATAFORMA

### 9.0 Tu rol clarificado

El equipo de IA te entrega código funcional (POC). Tú lo conviertes en sistema de
producción. No construyes la IA, construyes los rieles por donde corre.

**Lo que SÍ haces:**
- Recibir la muestra representativa del agente (endpoint de ingesta)
- Orquestar la llamada al LLM en Amazon Bedrock
- Gestionar la Matriz de Política por cliente (almacenamiento, caché, versionamiento)
- Propagar la clasificación del representativo a todo el grupo
- Persistir la metadata multidimensional (6 aristas) en DynamoDB/OpenSearch
- Broadcast de resultados vía Kafka/MSK
- Integrar con el sistema legacy (V1 sigue vivo)
- Monitoreo, resiliencia, escalabilidad y control de costos

**Lo que NO haces:**
- No construyes los motores C1-C4 (equipo de IA)
- No entrenas modelos ni ajustas prompts
- No tocas el agente local

### 9.1 Componentes nuevos que debes construir (V2)

| Componente | Función | Notas |
|------------|---------|-------|
| **Ingesta V2 (Lambda/API)** | Recibe la muestra representativa del agente L0 | Diferente al add_scan del V1: ya no es un vector, es contenido parcial + metadata de grupo + resultados C1/C2/C4 |
| **Orquestador de Clasificación** | Coordina: validar → preparar prompt → llamar Bedrock → post-procesar → propagar | El corazón del V2. Equivale al classifier-service del V1 pero para LLM |
| **Gestor de Matriz de Política** | Almacena y sirve la matriz generada por el LLM para cada cliente | Cache en Redis, persistencia en DynamoDB. Versionado por cliente |
| **Propagador de Grupo** | Toma la clasificación del doc representativo y la aplica a todo el grupo | Necesita conocer la agrupación (fuzzy hash + taxonomía C2 del agente) |
| **Motor de Metadata V2** | Genera el objeto de 6 aristas a partir del output del LLM + resultados C1/C2/C4 | Nuevo: no existe en V1 |
| **Bridge V1↔V2** | Permite que ambos sistemas coexistan, compartan data y no se pisen | Crítico durante la transición |
| **Consumer de Metadata V2** | Persiste la metadata multidimensional y la indexa en OpenSearch | Evolución del mongo-consumer/current-analysis-consumer del V1 |

### 9.2 Contratos de interfaz con el equipo de IA

Estos son los puntos de integración que debes definir con ellos:

```
AGENTE (L0-Engine) → TU SISTEMA (Nube)
  Input que recibes:
  {
    group_id: string,              // Identificador del grupo de docs similares
    representative_sample: string, // 5-10% del contenido del doc representativo
    taxonomy_type: string,         // Tipo de documento según C2 (52 tipos)
    pii_results: {                 // Resultados de C1
      types_found: [...],
      count_by_type: {...},
      confidence: float
    },
    injection_scan: {              // Resultados de C4
      is_safe: boolean,
      threats_detected: [...]
    },
    fuzzy_hash: string,            // Hash comparable del documento
    group_size: int,               // Cuántos docs hay en el grupo
    station_id: string,
    enterprise_id: string,
    lang: string,
    metadata: {...}                // Path, extension, owner, dates, etc.
  }

TU SISTEMA → LLM (Bedrock)
  - Prompt construido con: muestra + política del cliente + tipo de taxonomía
  - Output esperado: clasificación multidimensional + explicación

TU SISTEMA → AGENTE
  - Clasificación propagada al grupo completo
  - Metadata de 6 aristas por documento
```

### 9.3 Orden de prioridades para V2

1. **Definir contratos con equipo de IA** — qué te envían exactamente, en qué formato
2. **Construir ingesta V2** — endpoint que recibe la muestra del agente L0
3. **Integrar con Bedrock** — orquestar la llamada al LLM con la política del cliente
4. **Construir propagación de grupo** — aplicar clasificación a todos los docs del grupo
5. **Motor de metadata V2** — generar las 6 aristas
6. **Bridge V1↔V2** — hacer que ambos sistemas coexistan
7. **Monitoreo de costos** — alertas de gasto en Bedrock (esto es crítico)

### 9.4 Riesgos específicos del V2

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| **Costo de Bedrock** | Cada llamada al LLM cuesta dinero. Si el muestreo falla y envía demasiado → costos se disparan | Monitoreo de llamadas/día por cliente. Alarmas en CloudWatch. Rate limiting por enterprise_id |
| **Latencia del LLM** | Bedrock puede tardar segundos vs. los ~790ms del V1 | Batch async obligatorio. No intentar real-time con LLM para volumen |
| **Calidad de propagación** | Si el doc representativo no es representativo → todo el grupo se clasifica mal | Validar con equipo de IA la lógica de selección de representativo |
| **Matriz de Política desactualizada** | Si la política del cliente cambia y la matriz no se regenera → clasificaciones desalineadas | Versionamiento + webhook de invalidación. Similar al problema de caché Redis del V1 |
| **Coexistencia V1+V2** | Dos sistemas clasificando los mismos documentos pueden producir resultados conflictivos | Definir cuál tiene prioridad. Flag en metadata indicando fuente (V1/V2) |

### 9.5 Lo que se mantiene del V1

Estos componentes del V1 siguen siendo relevantes para el V2:

- **Arquitectura Hexagonal** — misma separación Domain/Application/Infrastructure
- **kriptos_kernel** — sigue siendo la librería base para persistencia
- **Kafka/MSK como broadcast** — los resultados del V2 también deben ir a Kafka
- **DynamoDB + OpenSearch** — misma estrategia de persistencia + búsqueda
- **Multitenancy por enterprise_id** — no cambia
- **Idempotencia** — sigue siendo obligatoria
- **Warm starts en Lambda** — sigue siendo crítico
- **Unread endpoint** — el agente sigue necesitando recuperar resultados

### 9.6 Prioridades del Legacy (V1) en paralelo

1. Importar Classifier Core para mantener compatibilidad.
2. Importar kriptos_kernel para conectarse a las bases de datos.
3. Mantener MSK Serverless con factor de replicación 3.
4. Mantener Publisher con validación estricta de esquema.
5. Monitorear Offset Lag.

### 9.7 Mejoras propuestas (aplican a ambos sistemas)

| Mejora | Detalle |
|--------|---------|
| **Aislamiento del Modelo IA** | En V2 ya está resuelto: Bedrock es el servicio dedicado. |
| **Orquestador en Rust/Go** | Para el fan-out y la orquestación de alta concurrencia. |
| **VPC Link** | Tráfico interno para Kafka y Bedrock. |
| **Observabilidad** | Trace ID único end-to-end. Redis para tracking de estado. |
| **Batch Processing en Kafka** | Agrupar resultados. |
| **Monitoreo de costos Bedrock** | Nuevo y crítico: alertas por cliente, rate limiting. |

### 9.8 Estructura de proyecto sugerida

```
kriptos-classifier-v2/
├── domain/
│   ├── entities/          # Analysis, Document, PolicyMatrix, MetadataResult
│   ├── commands/          # ClassifyGroupCommand, PropagateCommand
│   ├── value_objects/     # DocumentStatus, TaxonomyType, MetadataArista
│   └── interfaces/        # Repository ABCs, LLMPort, BrokerPort
├── application/
│   ├── orchestrators/     # ClassificationOrchestrator (coordina Bedrock + propagación)
│   ├── subscribers/       # Observer pattern para acciones post-clasificación
│   └── use_cases/         # ProcessL0Sample, GeneratePolicyMatrix, PropagateToGroup
├── infrastructure/
│   ├── adapters/
│   │   ├── inbound/       # API Gateway Handler, SQS Handler
│   │   └── outbound/      # BedrockClient, DynamoRepo, KafkaPublisher, RedisCache
│   ├── injection/         # Configuración de DI
│   └── bridge/            # Integración V1 ↔ V2
├── configuration/
│   └── constants.py       # Umbrales, aristas habilitadas por cliente, etc.
├── tests/
│   ├── test_cases.json
│   └── Dockerfile.verifier
└── handler.py             # Entry point Lambda
```

### 9.9 Instrucción para Agentes de IA

> **Contexto obligatorio para cualquier agente que trabaje sobre este proyecto:**
> - **Existen DOS sistemas coexistiendo:** Legacy (V1) y L0-Engine (V2). Preguntar siempre para cuál se está trabajando.
> - El equipo de IA entrega POCs. Nuestro trabajo es llevarlo a producción con Lambdas, colas y persistencia.
> - El LLM corre en **Amazon Bedrock**, no en Lambda. Nunca proponer cargar un LLM en memoria de Lambda.
> - La metadata de salida del V2 tiene **6 aristas**, no 1 nivel. Toda persistencia debe soportar este esquema.
> - Respetar la Arquitectura Hexagonal: el Domain NO importa `boto3`, `pymongo`, `redis`, ni el SDK de Bedrock.
> - Todo repositorio nuevo hereda de las ABCs de `kriptos_kernel.base.domain`.
> - La limpieza de estado (`results.clear()`) es obligatoria en Lambda.
> - **Monitoreo de costos de Bedrock es OBLIGATORIO** en toda implementación.
> - El **muestreo inteligente** (solo 5-10% del doc, solo si es nuevo) es la pieza clave de ahorro. Nunca proponer enviar documentos completos al LLM.
> - El sistema debe manejar **propagación de clasificación a grupos**: un representativo clasifica a todo el grupo.
> - Multitenancy por `enterprise_id` en toda capa.
> - Idempotencia obligatoria.
> - Para el Legacy (V1): NumPy para vectores, `importlib` para modelos, `mandatory_scheme` obligatorio.

---

## 10. GLOSARIO

| Término | Definición |
|---------|------------|
| **KEM** | Kriptos Entity Manager. Base de datos de reglas de negocio (empresas, estaciones, sensibilidad). |
| **Agente** | Software instalado en la máquina del cliente que escanea y vectoriza archivos. |
| **Vectorización** | Conteo de palabras clave según diccionario provisto por IA. Produce un vector numérico no reversible. |
| **Fan-out** | Proceso de romper un batch en mensajes individuales (add-scan-batch en Go). |
| **Offset Lag** | Diferencia entre el último mensaje producido y el último consumido en Kafka. Métrica principal de salud. |
| **Warm Start** | Reutilización de un contenedor Lambda ya inicializado. Crítico para performance. |
| **Cold Start** | Primera invocación de Lambda donde se cargan modelos, secretos y conexiones. |
| **Isolation Queue** | Cola SQS separada para mensajes problemáticos que no deben bloquear la cola principal. |
| **DynamoJSON** | Formato nativo de exportación de DynamoDB donde cada valor es `{"S": "valor"}`. Requiere aplanamiento. |
| **flatdict** | Librería Python para convertir JSON anidados en rutas planas para DynamoDB. |
| **MSK Serverless** | Amazon Managed Streaming for Apache Kafka en modo serverless. |
| **VTL** | Velocity Mapping Templates. Usado en API Gateway para validaciones antes de disparar Lambda. |