# Spec — validation-mutation-handler

> Ticket: [KT-17026](https://kriptosteam.atlassian.net/browse/KT-17026)
> Status: accepted (Fase 1 cerrada 2026-05-23)
> Repo destino futuro: `kriptos-io/validation-mutation-handler`

---

## 1. Goal

Procesar las decisiones del cliente (approve/reject por grupo, override individual, agregar path manual) sobre los candidatos pre-validación, actualizando OpenSearch (`validation_status` por doc) y los contadores agregados en DDB. Invocado como **resolver de AWS AppSync** desde la Plataforma Web.

## 2. Non-goals

- Auth / tenant isolation — Plataforma Web upstream (Cognito + filter en queries).
- UI / UX — Plataforma Web.
- Confirmación final del cycle (eso es KT-17027).
- Reconciliación estricta DDB↔OS — solo eventual consistency.

## 3. User-visible behavior

Trigger: AppSync invoca el Lambda como resolver de 3 mutations distintas (ver `graphql-schema-appsync.md` para schema completo):

```graphql
mutation validateCandidateGroup(
  enterprise_id, cycle_id, criteria: CandidateFilters!,
  decision: ValidationStatus!, actor: String!
): ValidateResult!

mutation overrideCandidate(
  candidate_id, decision: ValidationStatus!, actor: String!
): Candidate!

mutation addExtraPath(
  enterprise_id, cycle_id, station_id, path: String!, actor: String!
): Candidate!
```

`criteria` (bulk approve/reject): `{folder, matched_pattern, matched_business_area, station_id, extension, validation_status}` — todos opcionales, AND lógico.

**Las mutations están permitidas en estados `scanning` y `stations_complete`**. El cliente puede aprobar/rechazar incrementalmente mientras otras stations todavía escanean (validación continua).

## 4. Domain impact

| Módulo / Clase | Cambio | Invariante |
|---|---|---|
| `src/domain/decision.py` | Enum `Decision = {approved, rejected, manually_added}` | Strict. |
| `src/domain/path.py` | `SafePath` que rechaza `..`, null bytes, no-UTF8 | Anti path traversal. |
| `src/domain/mutation_request.py` | Tagged union de 3 tipos de mutation (discriminado por `mutation_type` derivado del AppSync `info.fieldName`) | Validado por pydantic discriminator. |
| `src/application/ports/opensearch_mutator.py` | Protocol con `update_by_query`, `update_doc`, `index_doc` | Retorna `affected_count`. |
| `src/application/ports/state_store.py` | Protocol con `verify_cycle_status_is_validatable`, `adjust_counters` | Acepta `scanning` o `stations_complete`. |
| `src/application/usecases/handle_validate_group.py` | Build OS query + scripted update + DDB counter ADD | |
| `src/application/usecases/handle_override.py` | Update doc específico + DDB counter delta | Lee estado previo para calcular delta correcto. |
| `src/application/usecases/handle_add_path.py` | Index doc nuevo con `validation_status=manually_added` | Idempotent upsert por candidate_id. |
| `src/adapters/opensearch_mutator.py` | Cliente OS con `opensearch-py` + IAM SigV4 (`requests-aws4auth`) | Sin secrets. |

## 5. Inputs and outputs

AppSync resolver event shape:

```json
{
  "info": {"fieldName": "validateCandidateGroup", "parentTypeName": "Mutation"},
  "arguments": {
    "enterprise_id": "ent-001",
    "cycle_id": "uuid",
    "criteria": {"folder": "/Users/foo/Estratégico/"},
    "decision": "approved",
    "actor": "user-123"
  },
  "identity": {"sub": "cognito-user-sub", "username": "..."}
}
```

```python
def handler(event: dict, context: LambdaContext) -> dict:
    """AppSync resolver. Routing por event['info']['fieldName']."""
```

Response (devuelto a AppSync, AppSync lo mapea al return type del schema):

```json
{"ok": true, "affected_count": 47, "cycle_status": "scanning"}
```

Errores (AppSync convierte a GraphQL errors):
- `BadRequest` (decision unknown, path traversal): error con extension code `BAD_REQUEST`.
- `NotFound` (cycle_id no existe): error con code `NOT_FOUND`.
- `Conflict` (cycle no validatable, ej. ya `confirmed`): error con code `INVALID_STATE`.

## 6. Dependencies

- `aws-lambda-powertools[tracer]`
- `boto3` — DDB
- `opensearch-py` + `requests-aws4auth` — OS mutations con IAM SigV4
- `pydantic` — validación + discriminator

## 7. Test plan

```
[ ] test_decision::test_only_allowed_values
[ ] test_safe_path::test_rejects_path_traversal_dotdot
[ ] test_safe_path::test_rejects_null_byte
[ ] test_safe_path::test_rejects_non_utf8
[ ] test_safe_path::test_accepts_valid_path
[ ] test_mutation_request::test_discriminator_routes_by_fieldName
[ ] test_opensearch_mutator::test_uses_iam_sigv4_auth
[ ] test_opensearch_mutator::test_update_by_query_returns_affected_count
[ ] test_opensearch_mutator::test_update_doc_validates_id_exists
[ ] test_state_store::test_verify_cycle_validatable_accepts_scanning
[ ] test_state_store::test_verify_cycle_validatable_accepts_stations_complete
[ ] test_state_store::test_verify_cycle_validatable_rejects_confirmed
[ ] test_handle_validate_group::test_folder_criteria_updates_n_docs
[ ] test_handle_validate_group::test_station_scope_limits_to_one_station
[ ] test_handle_validate_group::test_counter_adjusts_by_affected_count
[ ] test_handle_override::test_changes_from_approved_to_rejected_adjusts_counters
[ ] test_handle_override::test_idempotent_on_repeated_same_decision
[ ] test_handle_add_path::test_creates_new_doc_with_manually_added_status
[ ] test_handle_add_path::test_existing_path_upserts_no_duplicate
[ ] test_handle_add_path::test_path_traversal_rejected
[ ] test_handler::test_appsync_event_shape_parsed_correctly
[ ] test_handler::test_cycle_not_found_throws_not_found_error
[ ] test_handler::test_cycle_in_confirmed_throws_invalid_state_error
[ ] test_e2e::test_full_validation_session_with_appsync_event_format
```

## 8. Eval impact

No aplica.

## 9. Threat model delta

| STRIDE | Threat | Mitigación |
|---|---|---|
| Spoofing | Mutation sobre cycle de otro enterprise (cross-tenant) | **Auth NO se valida acá** — Plataforma Web + AppSync auth (Cognito). Defensive: el Lambda valida que `enterprise_id` del argument matchea con `PK` del CYCLE en DDB. Test: `test_cross_enterprise_returns_not_found`. |
| Path traversal | `addExtraPath` con `../../etc/passwd` | `SafePath` rechaza. Test: `test_rejects_path_traversal_dotdot`. |
| DoS | `validateCandidateGroup` con criteria que matchea 1M+ docs → OS `UpdateByQuery` timeout | Configurar `UpdateByQuery` con `max_docs` cap + `wait_for_completion=false` para grupos enormes. MVP: hard cap 10k docs por mutation; UI debe forzar criteria más específicos. |
| Integrity (counters) | OS update succeeds pero DDB ADD falla → counters drift | Job batch de reconciliación recomputa counters desde OS (ticket separado, fuera de scope acá). |

## 10. Resolved decisions

- **Canal de invocación**: AWS AppSync resolver. El Lambda recibe AppSync event shape (no API GW event ni custom dict). Resource policy del Lambda permite a AppSync invocar.
- **Schema GraphQL**: definido en `specs-staging/graphql-schema-appsync.md` (entregable a Plataforma Web).
- **Queries de lectura**: NO van por este Lambda — AppSync las hace directo contra OpenSearch (resolver tipo "direct data source"). Este Lambda solo maneja las 3 mutations.
- **OS auth**: IAM SigV4 con `requests-aws4auth`.
- **Estados válidos para mutations**: `scanning` y `stations_complete`. Cualquier otro → 409 INVALID_STATE.

## 11. Open questions deferidas

| # | Pregunta | Owner | Cuándo cerrar |
|---|----------|-------|---------------|
| OQ1 | `UpdateByQuery` async strategy para grupos >10k docs | Tech Lead en Skill 04 | Performance test |

## 12. Rollout

- Branch: `KT-17026-validation-mutation-handler`
- Spec commit + TDD commits
- Quality gates verdes
- PR a `main` con `Implements specs/001-validation-mutation-handler.md`
- Deploy via reusable workflow

**Bloqueantes de deploy:** [KT-17014](https://kriptosteam.atlassian.net/browse/KT-17014) (Lambda + AppSync resolver + IAM) + [KT-17009](https://kriptosteam.atlassian.net/browse/KT-17009) (DDB) + [KT-17010](https://kriptosteam.atlassian.net/browse/KT-17010) (OS index) + AppSync schema configurado por Plataforma Web (usando `graphql-schema-appsync.md`).
