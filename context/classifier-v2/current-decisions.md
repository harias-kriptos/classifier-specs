# Current Decisions — Classifier v2

Decisiones técnicas vigentes que las skills deben respetar. Cuando una skill genera una spec o un plan, **no debe contradecir esto** sin alertar al usuario primero.

---

## Stack

- **Lenguaje backend:** Python 3.11+
- **Runtime productivo:** AWS Lambda (no decidido aún para componentes con CPU/memoria altas — TBD si SAM o CDK).
- **Job framework:** EMR Serverless (PySpark) para `joyas-priorizer` y futuros jobs batch.
- **Storage operacional:** DynamoDB single-table (`gse-cycles-samples`) con stream `NEW_AND_OLD_IMAGES`.
- **Almacenamiento de archivos:** S3 (buckets con encryption AES-256, public-access block, EventBridge notifications).
- **Mensajería:** SQS FIFO para cycle init (idempotencia por `MessageGroupId`), SQS standard para los demás. Cada cola con DLQ.
- **Eventos:** EventBridge rules sobre PutObject; EventBridge Pipes desde DDB Streams.

## Testing

- **Framework:** `pytest` + `pytest-asyncio` cuando aplica.
- **Mocks:** `moto` para AWS (no mocks manuales). `pytest-httpx` / `responses` para HTTP externos.
- **Cobertura:** 80% línea, verificado por `pytest --cov` y SonarCloud quality gate.
- **TDD obligatorio:** orden de commits `chore: <behavior> (failing)` → `feat: <behavior> (passing)` → `refactor: <what>`.
- **Una aserción lógica por test.** Nombres descriptivos (`test_rejects_path_traversal_in_enterprise_id`, no `test_path_check`).

## Lint y tipos

- `ruff check` y `ruff format` — config en `pyproject.toml`.
- `mypy --strict` para todo código de dominio y application. Adapters pueden relajar (`mypy --strict-equality`) si una librería externa no tiene types.

## Arquitectura

Capas (similar a hexagonal):

```
src/
├── domain/         pure types, validaciones, sin I/O ni boto3
├── application/    use cases + ports (Protocols). depende de domain.
│   ├── ports/      Protocols que adapters implementan
│   └── usecases/   orchestración
└── adapters/       implementaciones concretas (S3, DDB, SQS). depende de application.
```

**Regla de dependencia:** `domain` no importa nada del workspace. `application` solo `domain`. `adapters` importan `application`. `handler.py` (Lambda entrypoint) cablea adapters → use cases.

`handler.py` no se testea directo — las use cases sí.

## Seguridad

- **Secretos nunca en código.** Variables `.env.example` documentan keys, `.env` está en `.gitignore` y bloqueado para lectura del agente.
- **No `eval`, no `exec`, no `pickle` con datos no confiables.**
- **Validación en bordes:** todo input externo (API Gateway body, S3 event, SQS message) pasa por validador (`pydantic`) antes de tocar lógica de dominio.
- **Sanitización de IDs:** regex `^[a-zA-Z0-9\-_]+$` para `enterprise_id`, `station_id`, `tree_id`, etc. (anti path-traversal).

## Observabilidad

- **Logs:** JSON estructurado vía `aws_lambda_powertools.Logger`. Siempre incluir `enterprise_id`, `station_id`, IDs de correlación (`tree_id`, `cycle_id`, `request_id`).
- **Métricas:** `aws_lambda_powertools.Metrics` o CloudWatch EMF directo.
- **Tracing:** AWS X-Ray habilitado en todas las Lambdas.

## CI/CD

- **GitHub Actions** para CI (no GitLab CI en este proyecto).
- **SonarCloud** quality gate verde obligatorio para merge.
- **Snyk** sin vulnerabilidades altas para merge.
- **Branch protection** en `main`: PR + 1 review aprobado.
- **Conventional commits** enforced por `commitlint`.

## Decisiones abiertas

- Framework de despliegue: SAM vs CDK vs Serverless Framework. **TBD.**
- Manejo de versiones de Lambdas (aliases vs publish nuevo): **TBD.**
- Estrategia de feature flags: **TBD.**

Cuando una de estas se cierre, actualizar este archivo y notificar al equipo.
