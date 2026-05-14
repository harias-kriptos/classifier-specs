# Spec NNN: <feature slug>

> Ticket: <TICKET-XXXXX>
> Author: <name>
> Status: draft | accepted | implemented | superseded
> Created: YYYY-MM-DD

---

## 1. Goal

One sentence. What changes about the system after this is shipped? Resist the urge to write three sentences.

## 2. Non-goals

Bullet list. What this spec deliberately does **not** address. This is what stops scope creep later.

- ...
- ...

## 3. User-visible behavior

What does someone running the binary observe? Concrete examples preferred over prose.

```
$ <binary> <subcommand> <args>
<expected output>
```

If the change is internal (an adapter swap, a refactor), say so explicitly: *"No user-visible behavior change. This spec covers an internal port substitution."*

## 4. Domain impact

Which types in `src/domain/` are touched? New types? New invariants on existing types?

| Type | Change | Invariant |
|---|---|---|
| `<TypeName>` | <what changes> | <what must hold> |
| ... | ... | ... |

## 5. Ports affected

Which traits in `src/application/ports/` change? Show the new method signatures.

```rust
pub trait <PortName> {
    fn <method>(&self, /* args */) -> Result<<Output>, <Error>>;
}
```

If you are adding a new port, justify why it is a port and not a concrete struct in `application::usecases`.

## 6. Adapters

Which adapters need to change or be created? Note any external dependency this introduces.

- `adapters/<adapter>.rs` — <what changes>. <New crate dependency? state it here>.
- ...

## 7. Test plan

This is the section that turns this spec into a TDD plan. List every test you will write **before** any production code change.

```
[ ] domain::<module>::tests::<behavior_being_asserted>
[ ] application::<usecase>::tests::<behavior_being_asserted>
[ ] adapters::<adapter>::tests::<behavior_being_asserted>
[ ] e2e::tests::<end_to_end_behavior>
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

Skip if no new I/O surface is introduced. Otherwise, describe the STRIDE-relevant change and update `docs/security/threat-model.md` in the same PR.

| STRIDE | Threat | Mitigation |
|---|---|---|
| <S/T/R/I/D/E> | <what could go wrong> | <what stops it, citing the line of code or test> |

## 10. Open questions

Things you do not know yet and need to resolve before implementation. If this section is empty, double-check — there is almost always something.

- ...
- ...

## 11. Rollout

- [ ] Branch: `<TICKET>-<slug>`
- [ ] Failing test commit: `chore(failing): <behavior>`
- [ ] Passing impl: `feat(passing): <behavior>`
- [ ] Refactor (if any): `refactor: <what>`
- [ ] Eval run committed in `evals/results/` (if applicable)
- [ ] `cargo audit` + `cargo deny check` clean
- [ ] PR linked to this spec: `Implements specs/NNN-<slug>.md`
