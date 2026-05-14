# Skill 01: Brainstorm

Use this skill when a raw ticket (or rough idea) needs to be refined before writing a spec. This is **the first step** of the pipeline. Output is a conversation, not files.

**Recommended model:** Opus 4.7 (this step decides scope; depth beats speed).

**Role:** Product Manager — see `roles/product-manager.md`

---

## Context loading

Before starting, read:

1. `roles/product-manager.md`
2. `context/classifier-v2/ecosystem.md` — what the classifier is, the moving parts
3. The ticket body or the ticket reference the user provided
4. If the ticket mentions a specific component (a Lambda, EMR job, S3 path), read the closest match under `context/classifier-v2/`

---

## Objective

Take a raw ticket and **challenge it** until the spec is writable. The agent does NOT write the idea — the user brings it. The agent refines.

By the end of this skill, the user should have:
- All open questions resolved or explicitly deferred
- Acceptance criteria that are testable (each AC maps to at least one test)
- Edge cases identified
- Out-of-scope marked
- Threat surface identified (auth, network, untrusted input, secrets)

---

## Minimal invocation

> "Brainstorm sobre el Ticket 1 (`tree-url-generator`)"
> "Refina esta idea: [descripción]"

That's enough. Ask for the ticket body if it's a reference and you can't read it.

---

## Procedure

1. Read the ticket. If the user pasted only a reference, ask for the full body or its closest equivalent in the repo.
2. Restate the ticket in 2-3 sentences to confirm understanding before refining.
3. Challenge the ticket along these dimensions, **one at a time** (do not dump all questions at once):

   **A. Scope clarity**
   - What does this ship that wasn't there before?
   - Is this one behavior or several? Should it be split?
   - What's explicitly NOT in scope?

   **B. Acceptance criteria**
   - For each AC: is it testable? How would you verify it failed?
   - Is there an AC for the happy path AND for at least one failure?

   **C. Edge cases**
   - What inputs break this? (empty, oversized, malformed, unicode, race conditions)
   - What external state could cause failure? (network down, S3 unavailable, IAM role missing)

   **D. Integration**
   - What does this depend on that someone else owns?
   - What depends on this? (downstream consumers)

   **E. Threat surface**
   - Untrusted input? Path traversal risk?
   - Secrets needed? Where do they live?
   - Public API? Auth / rate limiting?
   - Persisted data? PII risk?

   **F. Observability**
   - What logs are required? What fields?
   - What metric tells you it's working in prod?

4. Ask the user to commit each answer. The agent does NOT decide — the user does.
5. Stop when the four-item exit checklist is true (below).

---

## Exit checklist

Stop when ALL are true:
- [ ] Every AC is testable (user agrees)
- [ ] Edge cases listed (at least 3-5)
- [ ] Open questions resolved OR explicitly deferred
- [ ] Threat surface identified (or "no surface" stated explicitly)

When the checklist is true, hand off to Skill 02 with the refined notes.

---

## Required output structure

At the end of the brainstorm, produce a short markdown summary the user can paste into Skill 02. Sections:

1. **Resumen del ticket** (2-3 frases)
2. **Acceptance criteria refinados** (lista, cada uno testable)
3. **Edge cases identificados**
4. **Out of scope** (explícito)
5. **Threat surface** (o "ninguna" si aplica)
6. **Open questions deferidas** (con quién resuelve cada una)
7. **Siguiente paso:** Skill 02 — Spec + Threat Model

---

## Operating rules

- Maximum 3 questions per response. Do not dump all questions at once — context window stays small.
- If the user pushes to skip ahead to writing code, push back once with the reason (no spec = no contract = bad code), then defer to them.
- Outputs in Spanish.
- Never write the spec in this skill — only the summary above. Spec writing is Skill 02.
