# Spec — gse-sample-anonymizer-notifier

> Ticket: [KT-17030](https://kriptosteam.atlassian.net/browse/KT-17030)
> Status: accepted (Fase 2 cerrada 2026-05-23)
> Repo destino futuro: `kriptos-io/gse-sample-anonymizer-notifier`

---

## 1. Goal

Por cada sample anonimizado que el Anonymizer escribe en `gse-anonymized/`, incrementar `samples_anonymized` en la STATION row del DDB. **Sin notify externo** — la transición a `sample_anonymized` la dispara el DDB Stream consumido por KT-17032.

Es el Lambda más simple del backend.

## 2. Non-goals

- Notificaciones externas (KT-17032 maneja el cierre).
- Validación del contenido anonimizado.
- Transición de `sampling_status` (eso es KT-17032 cuando ve que counters cuadran).

## 3. User-visible behavior

Trigger: SQS `gse-sample-anonymizer-queue` ← EventBridge sobre PutObject suffix `.json` en `gse-anonymized`.

```
Input:  s3://gse-anonymized/{ent}/{sta}/{cycle}/{request_type}/sample_NNN.json
Side effect: UpdateItem STATION (mismo SK que Fase 1, ya existe):
  ADD samples_anonymized :one.
```

Sin response síncrono. Sin notify externo.

## 4. Domain impact

| Módulo / Clase | Cambio | Invariante |
|---|---|---|
| `src/domain/sample_key.py` | Misma lib compartida con KT-17029 (parser de 5-segment key con `.json`) | — |
| `src/application/ports/state_store.py` | Protocol con `increment_samples_anonymized` | Atomic ADD. |
| `src/application/usecases/notify_anonymized.py` | Use case mínimo | Idempotente con sobre-conteo aceptable. |

## 5. Inputs and outputs

```python
def handler(event: dict, context: LambdaContext) -> None:
    """SQS batch handler. Sin retorno."""
```

Sin payload externo (no notifica nada).

## 6. Dependencies

- `aws-lambda-powertools[tracer]`
- `boto3` — DDB
- `pydantic`

## 7. Test plan

```
[ ] test_sample_key::test_parses_5_segment_key (shared lib)
[ ] test_sample_key::test_rejects_wrong_extension
[ ] test_state_store::test_increment_anonymized_returns_new_value
[ ] test_state_store::test_station_not_found_returns_none
[ ] test_notify_anonymized::test_full_happy_path
[ ] test_notify_anonymized::test_station_not_found_logs_warn (race extremo)
[ ] test_notify_anonymized::test_duplicate_sqs_message_over_counts (aceptable)
[ ] test_handler::test_processes_batch_of_10
[ ] test_e2e::test_put_anonymized_increments_ddb_counter (moto)
```

## 8. Eval impact

No aplica.

## 9. Threat model delta

| STRIDE | Threat | Mitigación |
|---|---|---|
| Tampering | PUT en `gse-anonymized` por atacante (no es Anonymizer) | Bucket IAM permite PUT solo al principal del Anonymizer. Documentado en [KT-17017](https://kriptosteam.atlassian.net/browse/KT-17017). |
| DoS | Flood spurios | SQS retry + DLQ. Sobre-conteo aceptable. |

No hay surface significativa — Lambda interno mínimo.

## 10. Resolved decisions

- **Mismo SK que Fase 1**: la STATION row se reutiliza. UpdateItem agrega `samples_anonymized` al row existente.
- **Sin notify externo**: el cierre del CYCLE lo dispara el DDB Stream consumido por gse-station-status (KT-17032).
- **Idempotencia**: sobre-conteo aceptable porque el barrier final en KT-17032 usa `>=`.

## 11. Open questions deferidas

Ninguna específica a este Lambda.

## 12. Rollout

- Branch: `KT-17030-gse-sample-anonymizer-notifier`
- Spec + TDD commits
- Tests verdes; cobertura ≥ 80%
- PR a `main` con `Implements specs/001-gse-sample-anonymizer-notifier.md`

**Bloqueantes de deploy:** [KT-17020](https://kriptosteam.atlassian.net/browse/KT-17020) (Lambda + SQS) + [KT-17009](https://kriptosteam.atlassian.net/browse/KT-17009) (DDB) + [KT-17017](https://kriptosteam.atlassian.net/browse/KT-17017) (bucket gse-anonymized + SQS).
