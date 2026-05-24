# Spec — gse-request-complete

> Ticket: [KT-17031](https://kriptosteam.atlassian.net/browse/KT-17031)
> Status: accepted (Fase 2 cerrada 2026-05-23)
> Repo destino futuro: `kriptos-io/gse-request-complete`

---

## 1. Goal

Endpoint HTTP que el agente llama cuando termina de subir todos los samples de una request. Marca la REQUEST como `sent` y suma `samples_skipped` a la STATION padre, atómicamente vía TransactWriteItems.

## 2. Non-goals

- Verificar el conteo real de samples en S3 (confía en lo que el agente reporta).
- Cierre de STATION (eso es KT-17032 cuando detecta que counters cuadran).
- Retry de samples skipped — fuera de scope MVP.

## 3. User-visible behavior

Trigger: API Gateway `POST /v2/gse/request-complete`.

**Auth**: API key compartida con `/v2/tree/init` (KT-16612). El agente reusa la misma key.

Body:

```json
{
  "enterprise_id": "ent-001",
  "station_id": "station-A",
  "cycle_id": "cycle-uuid",
  "request_type": "crown_jewels",
  "total_samples_uploaded": 47,
  "samples_skipped": 3,
  "skipped_reasons": [{"path": "/Users/foo/locked.pdf", "reason": "locked_by_other_process"}]
}
```

Side effect: TransactWriteItems atómico:
- UPDATE REQUEST: SET status="sent", total_samples_uploaded, samples_skipped, skipped_reasons, request_complete_at=now. Conditional `attribute_exists(SK) AND status="requested"`.
- UPDATE STATION: ADD samples_skipped = N (se acumula al counter del row existente).

Response:

```json
{"ok": true, "request_status": "sent", "samples_expected": 50, "samples_received": 47, "samples_anonymized": 30, "samples_skipped": 3}
```

Códigos HTTP:
- 200: ok
- 400: body inválido
- 401: API key inválida (manejado por API GW)
- 404: REQUEST no existe
- 409: REQUEST ya `sent` (idempotencia tolerada)

## 4. Domain impact

| Módulo / Clase | Cambio | Invariante |
|---|---|---|
| `src/domain/request_complete_body.py` | Pydantic strict | `samples_skipped >= 0`, `total_samples_uploaded >= 0`. |
| `src/domain/request_type.py` | Enum con whitelist (env var) | Rechaza tipos no permitidos. |
| `src/application/ports/state_store.py` | Protocol con `transact_close_request` | Atomic dos updates. |
| `src/application/usecases/close_request.py` | Use case principal | Idempotente vía conditional status. |

## 5. Inputs and outputs

```python
def handler(event: dict, context: LambdaContext) -> dict:
    """API GW handler. Retorna body dict serializable a JSON."""
```

## 6. Dependencies

- `aws-lambda-powertools[tracer]`
- `boto3` — DDB (TransactWriteItems)
- `pydantic`

## 7. Test plan

```
[ ] test_body::test_validates_required_fields
[ ] test_body::test_rejects_negative_samples
[ ] test_body::test_rejects_unknown_request_type
[ ] test_state_store::test_transact_close_request_succeeds_when_requested
[ ] test_state_store::test_transact_close_request_fails_if_already_sent
[ ] test_state_store::test_transact_atomicity_both_or_none
[ ] test_state_store::test_station_samples_skipped_accumulates_in_existing_row
[ ] test_close_request::test_happy_path_returns_200_with_counters
[ ] test_close_request::test_duplicate_returns_409_with_current_status
[ ] test_close_request::test_unknown_request_returns_404
[ ] test_handler::test_invalid_body_400
[ ] test_handler::test_logs_include_correlation_ids
[ ] test_e2e::test_close_request_updates_both_records_atomically (moto)
```

## 8. Eval impact

No aplica.

## 9. Threat model delta

| STRIDE | Threat | Mitigación |
|---|---|---|
| Spoofing | Agente reporta `samples_skipped=N` falsos (infla o reduce) | Aceptable en MVP — no podemos verificar sin contar S3. Auditable via S3 logs si surge sospecha. API GW con API key (compartida con /v2/tree/init). |
| Tampering | Race de 2 close-requests | Conditional `status="requested"`; segundo recibe 409. |
| DoS | Spam de calls | API GW rate limit nativo. WAF post-MVP. |
| Repudiation | No traza de quién cerró | API GW logs + Lambda logs incluyen request_id; el body incluye actor implícito vía API key. |

## 10. Resolved decisions

- **Auth = API key compartida con `/v2/tree/init`** (KT-16612). El agente reusa la misma key configurada. Simple, consistente, ya validado en KT-16612.
- **TransactWriteItems**: REQUEST update + STATION ADD se aplican atómicamente. Sin posibilidad de drift entre los dos counters.
- **STATION row preserva campos Fase 1**: el `ADD samples_skipped :n` solo modifica ese counter, no toca `scan_status`, `candidates_count`, ni otros campos.

## 11. Open questions deferidas

| # | Pregunta | Owner | Cuándo cerrar |
|---|----------|-------|---------------|
| OQ1 | WAF rules contra abuse | DevOps | Hardening post-MVP |
| OQ2 | Migración futura de API key → JWT per-station | Producto | Post-MVP cuando KEM emita JWTs |

## 12. Rollout

- Branch: `KT-17031-gse-request-complete`
- Spec + TDD commits
- Tests verdes; cobertura ≥ 80%
- PR a `main` con `Implements specs/001-gse-request-complete.md`

**Bloqueantes de deploy:** [KT-17021](https://kriptosteam.atlassian.net/browse/KT-17021) (Lambda + API GW route + IAM) + [KT-17009](https://kriptosteam.atlassian.net/browse/KT-17009) (DDB).
