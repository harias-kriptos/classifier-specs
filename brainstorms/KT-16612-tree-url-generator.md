# Brainstorm output — Ticket KT-16612 (`tree-url-generator`)

> Generado por Skill 01 (Brainstorm) en Claude Web con Opus 4.7.
> Rol activado: Product Manager.
> Input: Ticket 1 del Classifier v2 (`v2/tickets-implementacion.md`).
> Fecha: 2026-05-13.

---

## 1. Resumen del ticket

Lambda Python detrás de `POST /v2/tree/init` que valida estrictamente el body del agente (5 campos requeridos, sin extras), sanitiza IDs contra path traversal, genera un `tree_id = uuid4()` **antes de validar** para garantizar correlación en logs, y devuelve una pre-signed URL `s3:put_object` (expiración 3600 s) al bucket apuntado por env var `COMPRESSED_TREES_BUCKET` con **8 headers firmados**: los 7 `x-amz-meta-*` documentados + `x-amz-server-side-encryption: AES256` como belt-and-suspenders. Stateless: no toca DDB, no llama cajas negras. Idempotencia, rate limiting y auth se resuelven fuera de este Lambda.

## 2. Acceptance criteria refinados

- **AC01 — Happy path 200.** POST con body válido (5 campos requeridos, sin campos extra) devuelve 200 con `{tree_id, upload_url, headers, expires_in: 3600}`. `headers` es un objeto con los 8 header-name → value firmados.
  - Tests: `test_handler_returns_200_for_valid_body`, `test_response_contains_all_8_signed_headers`, `test_tree_id_is_valid_uuid4`.

- **AC02 — PUT contra URL firmada** aterriza el archivo en `compressed_trees/{enterprise_id}/{station_id}/{tree_id}.jsonl.gz`. Validado a dos niveles:
  - Unit: `test_signed_url_targets_correct_s3_key`, `test_signed_url_includes_8_named_headers`.
  - Integration (moto): `test_e2e_put_with_correct_headers_lands_in_bucket`.

- **AC03 — Header alterado o ausente en el PUT → 403 SignatureDoesNotMatch.** Validado en integración con moto.
  - Tests: `test_e2e_put_with_tampered_meta_header_returns_403`, `test_e2e_put_missing_sse_header_returns_403`.

- **AC04 — Body inválido → 400 con `{field, reason}`.** Casos cubiertos, uno por test:
  - Campo requerido faltante (5 tests, uno por campo).
  - Campo extra en el body (1 test).
  - Tipo equivocado (`total_lines: "abc"`).
  - `enterprise_id` o `station_id` con carácter prohibido o `len > 64` o `len 0`.
  - `total_lines ≤ 0` o `> 10⁹`.
  - `fingerprint` vacío (stub permisivo: sólo rechaza vacío hasta cerrar Q2).
  - `agent_version` vacío o `len > 32` (stub permisivo hasta cerrar Q3).
  - Body que no es JSON válido.

- **AC05 — Logs estructurados JSON.** Toda response (200 o 4xx) emite log con campos obligatorios `{enterprise_id, station_id, tree_id, request_id}`. `tree_id` se genera **antes** de la validación de campos para garantizar presencia en todas las trazas. Logs de error incluyen `{field, reason}`; **NO** incluyen el valor crudo del campo ofensivo ni el body completo.
  - Tests: `test_log_includes_all_required_fields_on_success`, `test_log_includes_tree_id_even_on_validation_failure`, `test_log_does_not_include_raw_request_body`.

- **AC06 (emergió del brainstorm) — Fail-fast en misconfiguración.** Si `COMPRESSED_TREES_BUCKET` está ausente o vacía al importar el módulo de config, el Lambda falla en cold start (no per-request 500).
  - Test: `test_module_import_fails_when_bucket_env_var_missing`.

## 3. Edge cases identificados

- `COMPRESSED_TREES_BUCKET` ausente o vacía → fail-fast en cold start (AC06).
- `enterprise_id` o `station_id` en bordes de longitud (1 char y 64 chars) → ambos aceptados; `len 0` y `len 65` rechazados.
- `total_lines` en bordes (1 y 10⁹) → aceptados; 0, -1, 10⁹+1 → 400.
- IDs con unicode (Ω), espacios, slashes, dots, null bytes (`\x00`) → 400 por regex.
- Body con campo extra (ej. `os: "linux"`) → 400 (sin forward-compat silencioso).
- Body que no es JSON parseable → 400.
- Múltiples POST idénticos del agente → generan `tree_ids` distintos (limitación conocida, ver §4).
- Reintento tras crash mid-upload → nuevo `tree_id`; el archivo previo queda huérfano hasta que el tree-state mechanism futuro lo limpie.

## 4. Out of scope (explícito)

- Rate limiting / throttling — se resuelve vía API Gateway usage plan + WAF (otro equipo).
- Idempotencia — deferida al futuro tree-state mechanism (global).
- CloudWatch metrics y alarmas — ticket global aparte.
- Versionado del Lambda (aliases) — fuera.
- Infra: API Gateway, IAM role, bucket policy, WAF — existen, otro equipo.
- Rescan a nivel station — el rescan es enterprise-wide, otro flujo.
- Cambios en el agente — no tocamos su código.
- Lógica de auth — la implementa API Gateway o authorizer aguas arriba; este Lambda asume que llega autenticado.

## 5. Threat surface

| # | STRIDE | Threat | Mitigación |
|---|--------|--------|------------|
| T1 | Spoofing + EoP | Sin auth, atacante declara `enterprise_id` arbitrario y escribe en path de otro enterprise | 🔴 Bloqueante para prod. Depende de Q1 (auth). Spec se escribe; deploy a prod requiere Q1 cerrada. |
| T2 | DoS | Flood-PUT vía pre-signed URLs masivas | Mitigado parcialmente por auth cuando se cierre. Residual risk: agente autenticado abusivo — aceptado, monitoreado por SOC. |
| T3 | Tampering | Agente altera `x-amz-meta-*` antes del PUT | ✅ SigV4 firma los 8 headers (AC03). Header alterado → 403. |
| T4 | Path traversal | `enterprise_id="../../etc"` | ✅ Regex `^[a-zA-Z0-9\-_]+$` + len cap 64 (AC04). |
| T5 | Info disclosure (logs) | CloudWatch leak de identificadores de cliente | Mitigación: CloudWatch con IAM restrictivo. `enterprise_id` asumido no-PII (revisable). No se loguea body crudo ni valores ofensivos. |

## 6. Open questions deferidas

| # | Pregunta | Owner | Default temporal | Bloqueante para… |
|---|----------|-------|------------------|------------------|
| Q1 | Mecanismo de auth del endpoint (API key, IAM, Cognito, mTLS, otro) | Haroldo 🔴 | ninguno — endpoint asumido autenticado por API GW | Deploy a prod (no para escribir spec) |
| Q2 | Formato exacto de `fingerprint` (SHA-256 hex, base64, otro) | Equipo agente | string no-vacío, len 1–128 | Endurecimiento de AC04, no bloqueante |
| Q3 | Formato exacto de `agent_version` (semver estricto, free-form) | Equipo agente | string no-vacío, len 1–32 | Endurecimiento de AC04, no bloqueante |
| Q4 | Tree-state mechanism para idempotencia (qué tabla, qué clave, qué flujo) | TBD (arquitectura) | ninguno — duplicados aceptados temporalmente | Ticket arquitectural separado |

## 7. Siguiente paso

**Skill 02 — Spec + Threat Model.** Recomendado: Opus 4.7 (la spec es el contrato del resto del pipeline; vale la profundidad).

Salidas esperadas de Skill 02:

- `specs/001-tree-url-generator.md` siguiendo `templates/SPEC_TEMPLATE.md` (las 11 secciones completas, incluyendo plan de tests mapeado 1:1 a los nombres listados arriba, rollout checks en §11 para WAF + IAM + bucket policy, y commit plan TDD).
- `docs/security/tree-url-generator-threat-model.md` con la tabla STRIDE expandida y mitigaciones citadas a nivel de línea de código / test.
- Plan de commits: `chore: spec for tree-url-generator (KT-16612)` → secuencia de `chore: <behavior> (failing)` / `feat: <behavior> (passing)` por cada AC.

Repositorio del producto: `kriptos-io/s3-tree-uploader`.
