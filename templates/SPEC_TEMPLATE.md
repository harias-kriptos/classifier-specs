# Spec NNN: <feature slug>

> Ticket: KR-XXXXX
> Author: <name>
> Status: draft | accepted | implemented | superseded
> Created: YYYY-MM-DD

---

## 1. Goal

One sentence. What changes about the system after this is shipped?

## 2. Non-goals

Bullet list. What this spec deliberately does **not** address.

- ...
- ...

## 3. User-visible behavior

What does someone using this Lambda / API / job observe? Concrete examples preferred over prose.

```
POST /v2/<endpoint>
Request:  { ... }
Response: { ... }
```

If the change is internal (refactor, adapter swap), say so explicitly.

## 4. Domain impact

Which Python modules / data classes are touched? New types? New invariants?

| Module / Class | Change | Invariant |
|---|---|---|
| `<module.path>` | <what changes> | <what must hold> |

## 5. Inputs and outputs

For Lambdas: what triggers it (API Gateway, S3 event, SQS, EventBridge), what payload it receives, what response or side effect it produces.

For libraries: function signatures.

```python
def handler(event: dict, context: LambdaContext) -> dict:
    """<one-line behavior>"""
```

## 6. Dependencies

AWS services, external APIs, internal libraries. Note any new dependency this introduces (with one-line justification).

- `boto3` for S3 pre-signed URLs — already in stack
- `pydantic` for body validation — NEW, justification: ...

## 7. Test plan

This is the section that turns this spec into a TDD plan. List every test you will write **before** any production code change.

```
[ ] test_<module>::test_<behavior_being_asserted>
[ ] test_<module>::test_<edge_case>
[ ] test_e2e::test_<end_to_end_behavior>
```

For each item, write one line describing what it asserts. If you cannot, the test is not yet specified — figure it out before writing code.

## 8. Eval impact

Does this change LLM behavior, classifier output, or anything else where a unit test is insufficient?

- [ ] No — skip this section.
- [ ] Yes — describe the corpus addition / task update below.

### New eval tasks

```jsonl
{"id":"<task-id>","fixture":"corpus/<topic>/<file>","expected":{...}}
```

### Expected delta against baseline

| Metric | Baseline | After this spec |
|---|---|---|
| <metric> on <corpus> | <current> | <target> |

## 9. Threat model delta

Skip if no new trust boundary is introduced. Otherwise, describe the STRIDE-relevant change. If significant, link to `docs/security/<slug>-threat-model.md`.

| STRIDE | Threat | Mitigation |
|---|---|---|
| <S/T/R/I/D/E> | <what could go wrong> | <what stops it — cite test or code> |

## 10. Open questions

Things not yet decided. If empty, double-check — there is almost always something.

- ...
- ...

## 11. Rollout

- [ ] Branch: `KR-XXXXX-<slug>`
- [ ] Spec committed: `chore: spec for <feature> (KR-XXXXX)`
- [ ] Failing test: `chore: <behavior> (failing)`
- [ ] Passing impl: `feat: <behavior> (passing)`
- [ ] Refactor (if any): `refactor: <what>`
- [ ] Eval run committed in `evals/results/` (if applicable)
- [ ] `pytest`, `ruff check`, `mypy` all green
- [ ] Coverage ≥ 80% (SonarCloud quality gate)
- [ ] Snyk + SonarCloud green in CI
- [ ] PR linked: `Implements specs/NNN-<slug>.md`
