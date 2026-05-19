# Stack: Python Lambda — Reglas

Reglas duras (`MUST` / `NEVER`) y convenciones para repos de Lambdas Python del Classifier. Las skills cargan esto cuando la spec o el plan tocan código Python.

---

## MUST

- **MUST** usar Python 3.11 o superior.
- **MUST** estructurar como `src/{domain,application,adapters}` + `handler.py` que cablea.
- **MUST** validar input externo con `pydantic` antes de tocar dominio.
- **MUST** sanitizar todo ID que vaya a un path S3 con `^[a-zA-Z0-9\-_]+$`.
- **MUST** loguear con `aws_lambda_powertools.Logger` (JSON estructurado).
- **MUST** incluir `enterprise_id`, `station_id`, y un ID de correlación (`tree_id` / `cycle_id` / `request_id`) en cada log.
- **MUST** escribir tests con `pytest`. **MUST** mockear AWS con `moto`, nunca con mocks manuales.
- **MUST** alcanzar coverage ≥ 80% por módulo de `src/`.
- **MUST** mantener `tdd-trace.md` en raíz del repo actualizado por Skill 04. Es el source of truth del TDD que Skill 05 audita. Los commits son opcionales (squash, por slice, o granular — decisión del dev).

## NEVER

- **NEVER** usar `eval`, `exec`, `pickle` con datos no confiables.
- **NEVER** importar `boto3` ni nada de AWS desde `src/domain/`.
- **NEVER** hardcodear secretos. Leer desde Secrets Manager o variables `.env` (no commiteadas).
- **NEVER** atrapar `Exception` genérico sin re-raise o sin logging del traceback.
- **NEVER** usar `print()` en código productivo. Sólo el logger.
- **NEVER** modificar un test para hacerlo pasar — la responsabilidad es del código bajo test.
- **NEVER** mergear con `# type: ignore` o `# noqa` sin un comentario justificando por qué.

---

## Layout estándar

```
.
├── src/
│   ├── domain/             # tipos puros, validaciones, sin I/O
│   │   └── __init__.py
│   ├── application/        # use cases + Protocols
│   │   ├── ports/          # Protocols que adapters implementan
│   │   └── usecases/       # orquestación
│   └── adapters/           # S3, DDB, SQS, HTTP — implementaciones
├── tests/
│   ├── unit/               # tests rápidos por módulo
│   ├── integration/        # tests con moto / fakes
│   └── e2e/                # tests end-to-end (opcional)
├── handler.py              # entrypoint Lambda: cablea adapters → use cases
├── pyproject.toml          # deps + config ruff/mypy/pytest
├── .python-version         # 3.11.x
├── .gitignore
├── README.md
├── CLAUDE.md               # contrato para Claude Code en este repo
├── todo.md                 # plan TDD generado por Skill 03
├── tdd-trace.md            # source of truth del TDD (Skill 04 lo escribe, Skill 05 lo lee)
├── specs/                  # specs/NNN-*.md
├── docs/
│   ├── architecture/       # ADRs si aplican
│   └── security/           # threat models si aplican
├── evals/                  # SOLO si el repo tiene componente no-determinístico
└── .claude/
    ├── settings.json
    └── hooks/
```

---

## pyproject.toml mínimo

```toml
[project]
name = "<repo-name>"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
  "aws-lambda-powertools[tracer]>=2",  # logging estructurado, tracing
  "boto3>=1.34",                       # AWS SDK
  "pydantic>=2",                       # validación de input
]

[project.optional-dependencies]
dev = [
  "pytest>=8",
  "pytest-cov>=4",
  "pytest-asyncio>=0.23",
  "moto[s3,dynamodb,sqs]>=5",
  "ruff>=0.5",
  "mypy>=1.10",
  "types-boto3>=1.0",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "S", "A", "C4", "RET", "SIM"]
ignore = ["E501"]  # line length handled by formatter

[tool.mypy]
python_version = "3.11"
strict = true
warn_unused_configs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--cov=src --cov-report=term-missing --cov-fail-under=80"
```

---

## Commit policy (commitlint)

Tipos permitidos: `chore`, `feat`, `fix`, `refactor`, `docs`, `test`, `build`, `ci`, `style`, `perf`, `eval`.

Reglas adicionales que enforcamos:

- `chore:` con `(failing)` debe preceder a `feat:` con `(passing)` para el mismo behavior. Verificado por hook `enforce-tdd-trace.sh`.
- Mensajes en inglés.
- Body opcional pero recomendado para cambios no-triviales.

---

## CI

- Workflow `ci.yml` corre en push a cualquier rama y PR a `main`.
- Workflow `ci-prod.yml` corre solo en PR a `main` con gates más estrictos (coverage, Snyk, SonarCloud quality gate verde obligatorio para merge).

Jobs mínimos:

1. `lint` — ruff check + ruff format --check
2. `types` — mypy strict src
3. `test` — pytest con coverage; falla si < 80%
4. `security` — Snyk + pip-audit
5. `sonar` — SonarCloud scanner (quality gate verde obligatorio)
6. `commitlint` — verifica convención de commits

---

## Antipatrones específicos del Classifier

- **Saltar la sanitización de IDs** — abre path traversal. Siempre regex.
- **Cargar el `.jsonl.gz` completo en memoria** — algunos `tree.jsonl.gz` pesan GB. Usar streaming.
- **Asumir que existe `keywords/{enterprise}.json`** — puede no existir. EMR debe producir crown_jewels.jsonl vacío en ese caso.
- **No propagar headers `x-amz-meta-*`** — rompe la firma S3 cuando el objeto se descomprime.
- **Conditional writes débiles en DDB** — sin `attribute_not_exists` o `attribute_exists`, hay carreras.
