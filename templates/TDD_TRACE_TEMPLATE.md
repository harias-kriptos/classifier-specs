# TDD trace — {ticket-id} {slug}

> **Esto es el source of truth del ciclo TDD.** Skill 05 lo lee para verificar que cada slice tuvo RED → GREEN → REFACTOR registrado.
> Los commits son **opcionales** — squash, granular, o por slice, lo que el dev prefiera.
> Lo que NO es opcional es este archivo.
>
> Generado por Skill 04. Una entrada por slice del `todo.md`.
> Mantener cronológico — append-only.

---

## Resumen

- **Ticket:** {KR-XXXXX}
- **Spec:** `specs/NNN-<slug>.md`
- **Threat model:** `docs/security/<slug>-threat-model.md` (si aplica)
- **Plan:** `todo.md`
- **Modelo IA usado en Skill 04:** {ej. Sonnet 4.6 / Qwen 2.5 Coder vía OpenCode}
- **Started:** {YYYY-MM-DD HH:MM}
- **Completed:** {YYYY-MM-DD HH:MM o "in progress"}

---

## Slice 0: Project scaffold (no-TDD, excepción única)

**Started:** {timestamp}

### Setup

- Created `pyproject.toml` con deps mínimas.
- Created `src/{domain,application,adapters}/__init__.py`.
- Created `handler.py` con stub.
- Created `tests/__init__.py`.

### Verification

```
$ pytest
==================== 0 tests collected in 0.01s ====================
exit 0
```

**Slice complete:** {timestamp} ({duration})

---

## Slice 1: {behavior — ej. AC06 fail-fast on missing env var}

**Started:** {timestamp}

### RED

- **Test added:** `tests/unit/test_config.py::test_module_import_fails_when_bucket_env_var_missing`
- **pytest output (failing as expected):**

```
tests/unit/test_config.py::test_module_import_fails_when_bucket_env_var_missing FAILED
E   ImportError: COMPRESSED_TREES_BUCKET env var missing
==================== 1 failed in 0.05s ====================
```

- **✅ El test falla por la razón correcta.**

### GREEN

- **Implementation:** `src/application/config.py` (nuevo módulo + validation al import).
- **pytest output:**

```
tests/unit/test_config.py::test_module_import_fails_when_bucket_env_var_missing PASSED
==================== 1 passed in 0.04s ====================
```

- **ruff check:** clean
- **mypy --strict src:** clean

### REFACTOR

skipped (impl ya minimal)

**Slice complete:** {timestamp} ({duration})

---

## Slice N: ...

(replicar el bloque por cada slice del `todo.md`)

---

## Resumen final

> Llenar cuando todas las slices están `[x]`.

### Coverage final

```
$ pytest --cov=src --cov-report=term
============================= test session starts =============================
collected XX items

tests/...

Name                          Stmts   Miss  Cover
-------------------------------------------------
src/domain/models.py             XX      X    XX%
src/application/config.py        XX      X    XX%
src/application/usecases/...     XX      X    XX%
src/adapters/s3.py               XX      X    XX%
-------------------------------------------------
TOTAL                            XX      X    XX%

============================= XX passed in X.XXs ==============================
```

### Quality gates

- **pytest:** ✅ XX/XX passed
- **coverage:** ✅ XX% (gate ≥ 80%)
- **ruff check:** ✅ clean
- **ruff format --check:** ✅ clean
- **mypy --strict src:** ✅ clean
- **pip-audit:** ✅ no high/critical vulns

### Slices ejecutadas

- ✅ Slice 0 — Scaffold
- ✅ Slice 1 — {behavior}
- ✅ Slice 2 — {behavior}
- ✅ Slice 3 — {behavior}
- ...

### BLOCKED encountered

> Lista cualquier slice que terminó en BLOCKED durante la ejecución, con motivo.

(ninguna · o lista)

### Total duration

{HH:MM} desde scaffold hasta last slice complete.

### Ready for Skill 05

✅ Todos los slices `[x]`. Coverage ≥ 80%. Lint + types + security clean. Listo para review.
