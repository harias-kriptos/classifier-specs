# GraphQL Schema — AppSync (validación humana Fase 1)

> Para entrega al equipo Plataforma Web. Define los types, queries, mutations y subscriptions que la UI de validación consume.
> Generado: 2026-05-23.
> Backend: AWS AppSync con resolvers a OpenSearch (queries) y Lambda (mutations).

---

## Setup

- **Auth**: Cognito o IAM (decisión Plataforma Web).
- **Data sources**:
  - **OpenSearch** domain — para queries de candidatos (sin Lambda intermedio).
  - **Lambda** `lambda-validation-mutation-handler` ([KT-17026](https://kriptosteam.atlassian.net/browse/KT-17026)) — para mutations `validateCandidateGroup`, `overrideCandidate`, `addExtraPath`.
  - **Lambda** `lambda-validation-confirm` ([KT-17027](https://kriptosteam.atlassian.net/browse/KT-17027)) — para mutation `confirmValidation`.
  - **DynamoDB** `classifier-cycles-state` — para query `cycleProgress`.

---

## Schema

```graphql
# ============================================================
# Types
# ============================================================

type Candidate {
  candidate_id: ID!
  enterprise_id: String!
  station_id: String!
  cycle_id: ID!

  # Path original (con tildes) y normalizado (para búsqueda)
  path: String!
  path_normalized: String!
  folder: String!

  # Name original y normalizado
  name: String!
  name_normalized: String!

  extension: String
  size: Int!
  modified_date: AWSDateTime

  # Matches encontrados
  matched_patterns: [String!]!         # categorías normalizadas que matchearon
  matched_business_areas: [String!]!   # áreas de negocio normalizadas
  original_category: [String!]!        # categorías con tildes (para UI)
  original_business_area: [String!]!   # áreas con tildes (para UI)

  # Estado de validación
  validation_status: ValidationStatus!
  validation_actor: String             # user_id que aprobó/rechazó
  validation_at: AWSDateTime

  # Versionado
  normalize_version: String!
  indexed_at: AWSDateTime!
}

type CycleProgress {
  cycle_id: ID!
  enterprise_id: String!
  status: CycleStatus!

  # Counters de stations
  stations_expected: Int!
  stations_completed: Int!
  stations_pending: Int!     # derived: expected - completed

  # Counters de candidatos
  candidates_count: Int!
  approved_count: Int!
  rejected_count: Int!
  manually_added_count: Int!

  # Timestamps
  created_at: AWSDateTime!
  ready_at: AWSDateTime      # cuando pasó a stations_complete
  confirmed_at: AWSDateTime
  confirmed_by: String
}

type CandidatesPage {
  items: [Candidate!]!
  total_count: Int!
  has_more: Boolean!
  next_offset: Int
}

type ValidateResult {
  ok: Boolean!
  affected_count: Int!
  cycle_status: CycleStatus!
}

type ConfirmResult {
  ok: Boolean!
  cycle_id: ID!
  total_files: Int!
  stations: [String!]!
  manifest_uri: String       # s3://...
}

# ============================================================
# Enums
# ============================================================

enum ValidationStatus {
  pending
  approved
  rejected
  manually_added
}

enum CycleStatus {
  scanning              # algunas/todas stations escaneando — validación incremental permitida
  stations_complete     # todas terminaron — habilita "Confirmar todo"
  confirmed             # cliente confirmó — Fase 2 arrancando
  phase2_collecting     # GSE en curso
  complete              # LLM clasificó — fin del cycle
}

# ============================================================
# Input types (queries + mutations)
# ============================================================

input CandidateFilters {
  folder: String
  matched_pattern: String          # ej. "plan estrategico quinquenal"
  matched_business_area: String    # ej. "estrategia planeacion"
  validation_status: ValidationStatus
  station_id: String               # filtra por una station específica
  extension: String                # ej. "pdf"
}

input Pagination {
  limit: Int = 50      # default 50 (UI paginator 10/50/100)
  offset: Int = 0
}

# ============================================================
# Query
# ============================================================

type Query {
  """
  Estado actual del CYCLE (para pantalla de progreso).
  Resolver: DynamoDB direct (classifier-cycles-state, PK=enterprise_id, SK=CYCLE#{cycle_id}).
  """
  cycleProgress(enterprise_id: String!, cycle_id: ID!): CycleProgress!

  """
  Lista paginada de candidatos del CYCLE, con filtros opcionales.
  Resolver: OpenSearch direct (índice crown_jewel_candidates).
  Cliente típicamente filtra por validation_status para mostrar "pending" o "approved".
  """
  crownJewelCandidates(
    enterprise_id: String!
    cycle_id: ID!
    filters: CandidateFilters
    pagination: Pagination
  ): CandidatesPage!
}

# ============================================================
# Mutations
# ============================================================

type Mutation {
  """
  Bulk approve/reject sobre todos los docs que matchean el criterio.
  Resolver: Lambda lambda-validation-mutation-handler.
  Restricción: solo permitido si CYCLE.status ∈ {scanning, stations_complete}.
  """
  validateCandidateGroup(
    enterprise_id: String!
    cycle_id: ID!
    criteria: CandidateFilters!
    decision: ValidationStatus!     # approved | rejected
    actor: String!
  ): ValidateResult!

  """
  Override individual sobre la decisión grupal.
  Resolver: Lambda lambda-validation-mutation-handler.
  """
  overrideCandidate(
    candidate_id: ID!
    decision: ValidationStatus!     # approved | rejected
    actor: String!
  ): Candidate!

  """
  Agrega un path manual que el match automático no detectó.
  Resolver: Lambda lambda-validation-mutation-handler.
  Valida path contra path traversal (rechaza `..`, null bytes, no-UTF8).
  """
  addExtraPath(
    enterprise_id: String!
    cycle_id: ID!
    station_id: String!
    path: String!
    actor: String!
  ): Candidate!

  """
  Confirmación final del cliente. Triggers Fase 2.
  Resolver: Lambda lambda-validation-confirm.
  Restricción: solo permitido si CYCLE.status = stations_complete.
  Idempotente: segundo call retorna 409.
  """
  confirmValidation(
    enterprise_id: String!
    cycle_id: ID!
    actor: String!
  ): ConfirmResult!
}

# ============================================================
# Subscriptions (para la pantalla de progreso en tiempo real)
# ============================================================

type Subscription {
  """
  Cliente se subscribe al cycle y recibe push cada vez que cambian los counters
  o el status. Útil para que la UI muestre progreso sin polling agresivo.
  """
  onCycleStatusChange(enterprise_id: String!, cycle_id: ID!): CycleProgress!
    @aws_subscribe(mutations: [
      "validateCandidateGroup",
      "overrideCandidate",
      "addExtraPath",
      "confirmValidation"
    ])
}
```

---

## Notas para Plataforma Web

### UX recomendada

1. **Pantalla de progreso** — query `cycleProgress` al cargar + subscription `onCycleStatusChange`. Muestra:
   - Barra de progreso: `stations_completed / stations_expected`
   - Contador candidatos detectados
   - Status del CYCLE (badge: "Escaneando" / "Listo para confirmar" / etc.)
   - Botón "Confirmar todo" **disabled** hasta que `status = stations_complete`.

2. **Pantalla de validación** — query `crownJewelCandidates` con filtros. Mostrar:
   - Lista paginada con filtros por folder, business_area, pattern, status, station.
   - Bulk action "Aprobar todos los de esta carpeta" → mutation `validateCandidateGroup({folder: X}, approved)`.
   - Click individual en cada row → mutation `overrideCandidate(id, approved/rejected)`.
   - Botón "Agregar path manual" → mutation `addExtraPath(...)`.

3. **Confirmación final** — botón aparece cuando `status = stations_complete`. Click → mutation `confirmValidation` → CYCLE pasa a `confirmed` → Fase 2 arranca → UI muestra "Procesando samples...".

### Errores comunes que la UI debe manejar

| Error | Causa | Cómo mostrarlo al cliente |
|---|---|---|
| `409 Conflict` en `confirmValidation` | Doble click o cycle ya confirmado | "Ya confirmaste este ciclo. Estado actual: {current_status}." |
| `400 Bad Request` en `addExtraPath` | Path traversal (`..`, null bytes) | "El path no es válido." |
| `404 Not Found` | cycle_id no existe | "Ciclo no encontrado." |
| `403 Forbidden` | Auth del actor no tiene permisos sobre la enterprise | (lo maneja Cognito/AppSync auth) |

### Permisos / Auth

- **Lectura** (`Query.crownJewelCandidates`, `Query.cycleProgress`): cualquier usuario con permiso sobre la enterprise.
- **Mutations** (validate / override / addExtraPath / confirmValidation): solo usuarios con rol de validador (TBD por Plataforma Web).
- Tenant isolation: el resolver debe agregar un filtro automático `enterprise_id = currentUserEnterprise` para evitar cross-tenant.

### Performance

- `crownJewelCandidates` retorna ≤100 docs por call. UI pagina con `offset`.
- Volumen esperado: 10k-100k candidatos por cycle para enterprises grandes. La UI debe forzar filtros (no listar todo).
- `validateCandidateGroup` con criteria que afecta a >10k docs → Lambda retorna en async (TBD task_id polling). Para MVP: limit a 10k afected_count por mutation.

---

## Open questions para Plataforma Web

| # | Pregunta | Default |
|---|---|---|
| PW1 | Auth: Cognito JWT vs IAM SigV4 | Cognito (asumido) |
| PW2 | Subscription real-time o polling? | Subscription (más responsive, AppSync managed) |
| PW3 | UI maneja paginación local o server-side? | Server-side (con `offset`/`limit`) |
| PW4 | Pantalla de "Histórico" de cycles cerrados | Fuera de scope MVP |
